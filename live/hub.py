"""Who is connected, the rooms they are in, and getting frames out without ever blocking the loop.

* Conn: one socket (a tab). Player: one person (pid), shared by their tabs. Room: a set of sockets with an
  optional cap and ring buffer (Cả phố now; street instances, café tables and dates in phases 2 and 3).
* Sending: a frame is serialized once and written to every socket at once (websockets.broadcast, no awaits).
  A socket whose unsent bytes are over `slow_bytes` (256 KB) is cut off instead: one slow phone never
  holds memory for everyone.
* Presence: a player is online while one of their sockets is open (and pinging); friends see the green dot
  only when both show themselves online ("hiện online"). A reconnect within `presence_grace` seconds does
  not flicker it.
* Blocks (`blocks` by pid, `marriage_blocks` by sid, either direction) live in Player.hidden.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque

from . import jsonx
from .limits import Bucket, Window

try:
    from websockets.asyncio.connection import broadcast as _ws_broadcast
except ImportError:  # pragma: no cover - the service cannot run without it; tests skip
    _ws_broadcast = None


def _broadcast(connections, message, *, text=False):
    """Standard websockets selects text frames from str, without a text kwarg."""
    if text and isinstance(message, (bytes, bytearray)):
        message = message.decode('utf-8')
    return _ws_broadcast(connections, message)


class Player:
    def __init__(self, ident):
        self.pid, self.sid = ident.pid, ident.sid
        self.conns: set = set()
        self.friends: dict = {}        # pid -> dict(sid, name, av)
        self.hidden: set = set()       # pids blocked either way
        self.rates: dict = {}          # frame type -> Window
        self.recent: deque = deque(maxlen=6)   # (channel, fingerprint, time) of my last messages
        self.town_next = 0.0           # Cả phố slow mode: next time I may post there
        self.loaded = False            # friends / blocks / chats read from the database
        self.announced = False         # friends were told I am online
        self.gone_task = None
        self.ext: dict = {}            # per-player state of phase 2/3 features
        self.fc = None                 # 🙂 the face code shown next to my messages (live/faces.py), None: my emoji
        self.update(ident)

    def update(self, ident) -> None:
        self.name, self.av, self.account = ident.name, ident.av, ident.account
        self.muted_until = ident.muted_until
        self.old, self.since = ident.old, ident.since
        self.username = getattr(ident, 'username', '')   # admin or not: ChatFeature.is_admin (cfg.admins)
        if not self.conns:   # "hiện online" changes through prefs while connected
            self.show_online = ident.online

    def card(self) -> dict:
        return dict(pid=self.pid, name=self.name, av=self.av)


class Conn:
    _seq = 0

    def __init__(self, ws, player: Player, ip: str, cfg):
        Conn._seq += 1
        self.id = Conn._seq
        self.ws, self.player, self.ip = ws, player, ip
        self.rooms: set = set()
        self.last = time.monotonic()
        self.bucket = Bucket(rate=8.0, burst=30.0)   # frames from this socket
        self.ready = False                             # hello done
        self.closing = False
        self.ext: dict = {}

    def buffered(self) -> int:
        t = getattr(self.ws, 'transport', None)
        try:
            return t.get_write_buffer_size() if t is not None else 0
        except Exception:  # noqa: BLE001 - a transport already gone
            return 0


class Room:
    """Sockets that receive the same frames. cap 0 = no cap; buffer n = keep the last n stored frames."""

    def __init__(self, hub, rid: str, cap: int = 0, buffer: int = 0, on_empty=None):
        self.hub, self.id, self.cap = hub, rid, cap
        self.conns: set = set()
        self.buffer: deque | None = deque(maxlen=buffer) if buffer else None
        self.on_empty = on_empty
        self.data: dict = {}           # feature state of this room (phase 2: positions, tables...)

    def full(self) -> bool:
        return bool(self.cap) and len({c.player.pid for c in self.conns}) >= self.cap

    def add(self, conn) -> bool:
        if conn in self.conns:
            return True
        if self.full() and not any(c.player is conn.player for c in self.conns):
            return False
        self.conns.add(conn)
        conn.rooms.add(self)
        return True

    def remove(self, conn) -> None:
        self.conns.discard(conn)
        conn.rooms.discard(self)
        if not self.conns and self.on_empty:
            self.on_empty(self)

    def players(self) -> set:
        return {c.player for c in self.conns}

    def send(self, frame, sender: Player | None = None, skip=None) -> int:
        """To every socket here, except `skip` (a Conn) and anyone hidden from / hiding `sender`."""
        if sender is None:
            targets = [c for c in self.conns if c is not skip]
        else:
            hid, pid = sender.hidden, sender.pid
            targets = [c for c in self.conns if c is not skip and c.player.pid not in hid and pid not in c.player.hidden]
        return self.hub.send_many(targets, frame)


class Hub:
    def __init__(self, cfg):
        self.cfg = cfg
        self.conns: set = set()
        self.players: dict = {}
        self.rooms: dict = {}
        self.by_ip: dict = {}
        self.sent = 0           # frames written (stats)
        self.cut = 0            # slow clients cut off
        self.write = _broadcast

    # ---- sockets ----------------------------------------------------------------------------------
    def add(self, conn: Conn) -> None:
        self.conns.add(conn)
        self.by_ip[conn.ip] = self.by_ip.get(conn.ip, 0) + 1
        conn.player.conns.add(conn)

    def remove(self, conn: Conn) -> bool:
        """Forget a socket; True when it was its player's last one."""
        if conn not in self.conns:
            return False
        self.conns.discard(conn)
        n = self.by_ip.get(conn.ip, 1) - 1
        if n > 0:
            self.by_ip[conn.ip] = n
        else:
            self.by_ip.pop(conn.ip, None)
        for room in list(conn.rooms):
            room.remove(conn)
        p = conn.player
        p.conns.discard(conn)
        return not p.conns

    def player(self, ident) -> Player:
        p = self.players.get(ident.pid)
        if p is None:
            p = self.players[ident.pid] = Player(ident)
        else:
            p.update(ident)
            if p.gone_task:
                p.gone_task.cancel()
                p.gone_task = None
        return p

    def conns_of(self, pid: str) -> set:
        p = self.players.get(pid)
        return {c for c in p.conns if c.ready} if p else set()

    def online(self, pid: str) -> bool:
        return bool(self.conns_of(pid))

    def visible(self, pid: str) -> bool:
        p = self.players.get(pid)
        return bool(p and p.show_online and p.announced and any(c.ready for c in p.conns))

    def blocked(self, a: str, b: str) -> bool:
        pa, pb = self.players.get(a), self.players.get(b)
        return bool((pa and b in pa.hidden) or (pb and a in pb.hidden))

    # ---- rooms --------------------------------------------------------------------------------------
    def room(self, rid: str, cap: int = 0, buffer: int = 0, on_empty=None, create: bool = True) -> Room | None:
        r = self.rooms.get(rid)
        if r is None and create:
            r = self.rooms[rid] = Room(self, rid, cap, buffer, on_empty)
        return r

    def drop_room(self, rid: str) -> None:
        r = self.rooms.pop(rid, None)
        if r:
            for c in list(r.conns):
                r.conns.discard(c)
                c.rooms.discard(r)

    def rooms_with_prefix(self, prefix: str) -> list:
        return [r for k, r in self.rooms.items() if k.startswith(prefix)]

    # ---- sending ------------------------------------------------------------------------------------
    def encode(self, frame) -> bytes:
        return frame if isinstance(frame, (bytes, bytearray)) else jsonx.dumps(frame)

    def send(self, conn: Conn, frame) -> int:
        return self.send_many((conn,), frame)

    def send_many(self, conns, frame) -> int:
        ok = []
        limit = self.cfg.slow_bytes
        for c in conns:
            if c.closing:
                continue
            if c.buffered() > limit:
                self.cut_off(c)
                continue
            ok.append(c)
        if ok:
            data = self.encode(frame)
            self.write([c.ws for c in ok], data, text=True)
            self.sent += len(ok)
        return len(ok)

    def to_pids(self, pids, frame, sender: Player | None = None, skip=None) -> int:
        targets = []
        for pid in pids:
            p = self.players.get(pid)
            if not p or (sender and (pid in sender.hidden or sender.pid in p.hidden)):
                continue
            targets.extend(c for c in p.conns if c.ready and c is not skip)
        return self.send_many(targets, frame)

    def cut_off(self, conn: Conn) -> None:
        """A client that does not read: drop the connection now (its unsent bytes go with it)."""
        conn.closing = True
        self.cut += 1
        t = getattr(conn.ws, 'transport', None)
        if t is not None:
            t.abort()

    # ---- presence -----------------------------------------------------------------------------------
    def announce(self, p: Player, on: bool) -> None:
        p.announced = on
        frame = jsonx.dumps(dict(t='presence', pid=p.pid, on=on))
        targets = []
        for fpid in p.friends:
            f = self.players.get(fpid)
            if f and f.show_online and p.pid in f.friends and fpid not in p.hidden and p.pid not in f.hidden:
                targets.extend(c for c in f.conns if c.ready)
        self.send_many(targets, frame)

    def came_online(self, p: Player) -> None:
        if p.gone_task:
            p.gone_task.cancel()
            p.gone_task = None
        if p.show_online and not p.announced:
            self.announce(p, True)

    def went_offline(self, p: Player, on_gone=None) -> None:
        """The last socket closed: after the grace period, tell friends and forget the player."""
        async def later():
            try:
                await asyncio.sleep(self.cfg.presence_grace)
            except asyncio.CancelledError:
                return
            if p.conns:
                return
            p.gone_task = None
            if p.announced:
                self.announce(p, False)
            if self.players.get(p.pid) is p:
                del self.players[p.pid]
            if on_gone:
                on_gone(p)
        if p.gone_task:
            p.gone_task.cancel()
        p.gone_task = asyncio.ensure_future(later())

    def set_visible(self, p: Player, on: bool) -> None:
        p.show_online = on
        if on and not p.announced and p.conns:
            self.announce(p, True)
        elif not on and p.announced:
            self.announce(p, False)

    # ---- limits ---------------------------------------------------------------------------------------
    def rate(self, p: Player, key: str, limit: int, seconds: float) -> Window:
        w = p.rates.get(key)
        if w is None:
            w = p.rates[key] = Window(limit, seconds)
        return w

    def stats(self) -> dict:
        return dict(conns=len(self.conns), players=len(self.players), rooms=len(self.rooms), sent=self.sent, cut=self.cut)
