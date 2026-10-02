"""🏮 Đi hội chợ cùng nhau (switch LIVE_FAIR, by default as LIVE_STREET): players walking the fairground of the
hội chợ (public/js/v4/fair-walk.js) see each other walk around it. Nothing else: no names called out, no
"X vừa vào hội", no chat. The stall pages are not shared (the games stay each player's own).

Rooms and positions (memory only, never the database)
* Instances `fair:<n>` of at most CAP = 30 players; `fair_in` picks the fullest one with room that holds nobody
  blocked either way, else opens the next one. One room per player (all their tabs): a second tab coming in takes
  the first one out (`fair_left {why: 'other'}`, the client just stops drawing the others).
* The fairground has a landscape and a portrait layout (scenes/fair-place.js), so positions travel as fractions
  of its floor: x, y in [0, 1] (rounded to 0.001). Anything outside is clamped; a wrong shape is refused.
* `fair_mv {p: [[x, y], ...], ms}`: the path the player's client walks (2..MAX_POINTS points, the first one where
  they stand) and how long that walk takes there (≤ MAX_MS); the others replay it. At most 4 per second per player.
* Diffs (comings and goings, walks) are queued and sent as one `fair` frame at most every FLUSH = 0.1 s per room;
  several walks of one player in that window send only the last (a player's own events come back too: ignored).
* Playing a stall (owner, 03/10: "chơi trò gì thì bên ngoài thấy người ta đứng trò đó"): a player on a stall page stays
  in the room, standing at that stall's stand point; `fair_mv` / `fair_in` may carry `s`, the id of the stall they play
  (a short lowercase word: 'lt', 'bc', 'candy'…; anything else counts as none). Every walk sets it anew (a walk
  without `s` is a walk away), it travels on `mv` / `in` events and in the snapshot only while set. The others draw the
  player at their own fairground's stand of that stall with the stall's badge over them. Older peers ignore `s`.
* Blocks: blocked players are never put in the same instance; a block made at the fair makes both invisible to
  each other at once (an `out` for each), and no frame from one reaches the other.

Frames (client → server; replies in brackets)
  fair_in {look, g, x, y, s?}  [fair_room {room, me, people: [{pid, name, lk, g, x, y, s?}], cap}]
  fair_mv {p, ms, s?}          fair_out {}  [fair_left {why: 'out'}]
Server pushes: fair {ev: [{k: in|mv|out, ...}]}, fair_left {why: 'other'}.
A live service without this file answers `fair_in` with error 'unknown'; clients only send it when the welcome's
flags have `fair` (an older service has no such flag: nobody else is drawn, the fairground works as before).
"""
from __future__ import annotations

import asyncio
import math
import random
import re
import time

from .protocol import Feature, LiveError, on
from .street import clean_look

PREFIX = 'fair:'
CAP = 30                  # players per instance (also the most a client draws)
INSTANCES_MAX = 400       # 12,000 walkers at most (far more than the sockets anyway)
FLUSH = 0.1               # seconds between two room diffs (≤ 10 per second)
EVENTS_MAX = 300          # queued diff events per room before an early flush
MAX_POINTS = 16           # points of one walk
MAX_MS = 3000             # the longest walk a client replays (the fairground's walks take under a second)
STALL = re.compile(r'[a-z]{1,8}')   # a stall id (`s`): the stalls of scenes/fair-place.js and the food carts


def _num(v) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def _frac(v) -> float:
    return round(min(1.0, max(0.0, float(v))), 3)


def clean_point(pt) -> list:
    """[x, y] as fractions of the floor, clamped into it; anything else is refused."""
    if not isinstance(pt, (list, tuple)) or len(pt) != 2 or not (_num(pt[0]) and _num(pt[1])):
        raise LiveError('bad', 'Vị trí không hợp lệ.')
    return [_frac(pt[0]), _frac(pt[1])]


def clean_stall(v) -> str | None:
    """The stall a player plays (`s`), or None: never refused, an odd value just counts as none."""
    return v if isinstance(v, str) and STALL.fullmatch(v) else None


class Goer:
    __slots__ = ('pid', 'player', 'name', 'look', 'g', 'x', 'y', 's')

    def __init__(self, player, look: dict, g, at: list, s: str | None = None):
        self.pid, self.player = player.pid, player
        self.name = player.name or ''
        self.look, self.g = look, g
        self.x, self.y = at
        self.s = s

    def public(self) -> dict:
        d = dict(pid=self.pid, name=self.name, lk=self.look, g=self.g, x=self.x, y=self.y)
        if self.s:
            d['s'] = self.s
        return d


class FairFeature(Feature):
    name, flag = 'fair', 'fair'

    def __init__(self, app):
        super().__init__(app)
        self.flushes = 0               # diff frames sent (stats)

    # ---- rooms ----------------------------------------------------------------------------------------
    def _pick(self, p):
        rooms = self.hub.rooms_with_prefix(PREFIX)
        ok = [r for r in rooms if len(r.data['people']) < CAP and
              not any(q in p.hidden or p.pid in w.player.hidden for q, w in r.data['people'].items())]
        if ok:
            return max(ok, key=lambda r: (len(r.data['people']), -int(r.id[len(PREFIX):])))
        if len(rooms) >= INSTANCES_MAX:
            raise LiveError('full', 'Hội chợ đông quá, lát quay lại nhé.')
        used = {r.id for r in rooms}
        n = 1
        while f'{PREFIX}{n}' in used:
            n += 1
        room = self.hub.room(f'{PREFIX}{n}', cap=CAP, on_empty=self._empty)
        room.data.update(people={}, ev=[], mvi={}, h=None, last=0.0, hidden_seen=set())
        return room

    def _empty(self, room) -> None:
        h = room.data.get('h')
        if h is not None:
            h.cancel()
        self.hub.drop_room(room.id)

    def _leave_player(self, p, why: str | None = None, keep=None) -> None:
        """Take every socket of player p out of their fair room (`keep`: the socket that asked)."""
        rid = p.ext.pop('fair', None)
        room = self.hub.rooms.get(rid) if rid else None
        if room is None:
            return
        mine = [c for c in room.conns if c.player is p]
        for c in mine:
            c.ext.pop('fair', None)
            if why and c is not keep:
                self.hub.send(c, dict(t='fair_left', why=why))
        if room.data['people'].pop(p.pid, None) is not None:
            self._queue(room, p.pid, dict(k='out', pid=p.pid))
        for c in mine:
            room.remove(c)

    def _me(self, conn):
        rid = conn.ext.get('fair')
        room = self.hub.rooms.get(rid) if rid else None
        w = room.data['people'].get(conn.player.pid) if room is not None else None
        if w is None:
            raise LiveError('not_in', 'Bạn chưa vào hội chợ.')
        return room, w

    async def _ensure_loaded(self, p) -> None:
        chat = self.app.chat
        if chat is None:
            return
        if not p.loaded:   # the chat is off: its hello did not load friends and blocks
            await chat.load_friends(p)
            await chat.load_hidden(p)
            p.loaded = True
        if not p.name:
            await chat.refresh(p)

    # ---- the diff queue (≤ 10 frames per second per room; as live/street.py) ------------------------------
    def _queue(self, room, sender: str, ev: dict) -> None:
        d = room.data
        if ev['k'] == 'mv' and sender in d['mvi']:
            d['ev'][d['mvi'][sender]] = (sender, ev)
        else:
            if ev['k'] == 'mv':
                d['mvi'][sender] = len(d['ev'])
            else:   # out and back in within one window: a later walk comes after them
                d['mvi'].pop(sender, None)
            d['ev'].append((sender, ev))
        if len(d['ev']) >= EVENTS_MAX:
            if d['h'] is not None:
                d['h'].cancel()
            self._flush(room)
            return
        if d['h'] is None:
            delay = max(0.0, d['last'] + FLUSH - time.monotonic())
            d['h'] = asyncio.get_running_loop().call_later(delay, self._flush, room)

    def _flush(self, room) -> None:
        d = room.data
        d['h'] = None
        evs, d['ev'], d['mvi'], d['last'] = d['ev'], [], {}, time.monotonic()
        if not evs or self.hub.rooms.get(room.id) is not room:
            return
        self.flushes += 1
        conns = [c for c in room.conns if c.ready]
        pids = {c.player.pid for c in conns}
        if not any(c.player.hidden & pids for c in conns):
            self.hub.send_many(conns, dict(t='fair', ev=[e for _, e in evs]))
            return
        senders = {s for s, _ in evs}
        groups: dict = {}
        for c in conns:
            me = c.player
            ex = frozenset(s for s in senders if s in me.hidden or self.hub.blocked(me.pid, s))
            groups.setdefault(ex, []).append(c)
        for ex, cs in groups.items():
            out = [e for s, e in evs if s not in ex]
            if out:
                self.hub.send_many(cs, dict(t='fair', ev=out))

    # ---- handlers -----------------------------------------------------------------------------------------
    @on('fair_in', rate=(20, 60))
    async def fair_in(self, conn, f):
        look, g = clean_look(f.get('look'), f.get('g'))
        x, y = f.get('x'), f.get('y')
        at = clean_point([x, y]) if x is not None or y is not None else [round(random.uniform(.1, .3), 3), .97]
        p = conn.player
        await self._ensure_loaded(p)
        self._leave_player(p, 'other', keep=conn)
        room = self._pick(p)
        room.add(conn)
        w = Goer(p, look, g, at, clean_stall(f.get('s')))
        room.data['people'][p.pid] = w
        p.ext['fair'] = room.id
        conn.ext['fair'] = room.id
        self._queue(room, p.pid, dict(k='in', **w.public()))
        people = [o.public() for q, o in room.data['people'].items()
                  if q != p.pid and not (q in p.hidden or p.pid in o.player.hidden)]
        return dict(t='fair_room', room=room.id, me=p.pid, people=people, cap=CAP)

    @on('fair_out', rate=(20, 60))
    async def fair_out(self, conn, f):
        self._leave_player(conn.player, 'out', keep=conn)
        return dict(t='fair_left', why='out')

    @on('fair_mv', rate=(4, 1.0))
    async def fair_mv(self, conn, f):
        room, w = self._me(conn)
        pts, ms = f.get('p'), f.get('ms')
        if not isinstance(pts, list) or not 1 <= len(pts) <= MAX_POINTS or not _num(ms):
            raise LiveError('bad', 'Vị trí không hợp lệ.')
        path = [clean_point(pt) for pt in pts]
        if len(path) == 1:
            path.insert(0, [w.x, w.y])
        w.x, w.y = path[-1]
        w.s = clean_stall(f.get('s'))
        ev = dict(k='mv', pid=w.pid, p=path, ms=int(min(MAX_MS, max(0, ms))))
        if w.s:
            ev['s'] = w.s
        self._queue(room, w.pid, ev)
        return None

    # ---- every second: a block made at the fair --------------------------------------------------------------
    async def tick(self, now: float):
        for room in self.hub.rooms_with_prefix(PREFIX):
            d = room.data
            people = d['people']
            if len(people) < 2:
                continue
            for pid, w in list(people.items()):
                for q in w.player.hidden & people.keys():
                    pair = frozenset((pid, q))
                    if pair in d['hidden_seen']:
                        continue
                    d['hidden_seen'].add(pair)
                    for a, b in ((pid, q), (q, pid)):
                        pa = people.get(a)
                        if pa is not None:
                            self.hub.send_many([c for c in room.conns if c.player is pa.player], dict(t='fair', ev=[dict(k='out', pid=b)]))

    async def on_close(self, conn):
        rid = conn.ext.pop('fair', None)
        if not rid:
            return
        p = conn.player
        room = self.hub.rooms.get(rid)
        if room is not None and not any(c.player is p for c in room.conns):
            if room.data['people'].pop(p.pid, None) is not None:
                self._queue(room, p.pid, dict(k='out', pid=p.pid))
        if p.ext.get('fair') == rid and (room is None or not any(c.player is p for c in room.conns)):
            p.ext.pop('fair', None)

    def stats(self) -> dict:
        rooms = self.hub.rooms_with_prefix(PREFIX)
        return dict(fair_rooms=len(rooms), fairgoers=sum(len(r.data['people']) for r in rooms), fair_flushes=self.flushes)
