"""📸 Buồng chụp ảnh hội chợ together (owner 03/10: "photoboth thì rủ bạn bè tới chụp với nhau ở trong hội chợ nhé, vào đó
nhập cái mã phòng, 2 chế độ là … người lạ và bạn bè"): a short-lived room where up to CAP players see each other's
characters on the booth's backdrop, pick a frame (the host) and a pose and a prop each, get ready and shoot. The
photos are drawn in each browser from the room's state (public/js/v4/fair-booth.js): no image ever passes through
here, nothing is stored (memory only, never the database), a room is gone when its last player leaves or after
IDLE_SECS without a word. On with the fairground's crowd (Feature flag 'fair'); the welcome's flags get `booth`
(clients only offer the shared booth when it is there: an older service has no such flag, so they shoot alone).

Two ways in
* Bạn bè: `booth_make` opens a room with a code of CODE_LEN characters (CODE_CHARS: no 0/O, 1/I/L), shared by word of
  mouth; `booth_join {code}` enters it. A wrong code, a closed room and a room holding someone blocked either way all
  answer the same 'nocode' (a block is never revealed); a room of CAP is 'full'; the host may send someone out
  (`booth_kick`), who cannot come back into that room.
* Người lạ: `booth_find` puts the player in the queue (`booth_wait {secs}`); the first waiter not blocked either way
  is paired with them at once (a room of 2, no code, the earlier waiter hosts), else after WAIT_SECS `booth_none
  {why: 'timeout'}`; `booth_cancel` leaves the queue.

In a room
* The host picks the frame and the backdrop (`booth_set {frame, bg}`; public/js/v4/photo-frames.js FRAMES, BACKDROPS); everyone picks their own pose and prop (`booth_set {pose, prop}`);
  ids are short lowercase words (ID), the list is the client's (an id a client does not know is drawn as the default).
* `booth_ready`: the player has paid their ticket (fair_photo on the game server; the client sends this after it).
  `booth_go` (the host, when everyone is ready): `booth_shoot {n, gap, id}` to all, each client counts down and
  shoots n photos gap ms apart; the readies are used up (the next shoot is paid again).
* `booth_out` leaves; the host leaving passes the room to the one who came in first after them. One room or queue
  per player: a second tab coming in takes the first one out (`booth_left {why: 'other'}`).
* Blocks: a block made in a room sends the one who came in later out (`booth_left {why: 'blocked'}`).
Nothing but a display name and the look the client draws (live/street.py clean_look) is shared.

Frames (client → server; replies in brackets)
  booth_make {look, g}         [booth_room {room, code, mode, host, me, frame, bg, cap, people: [{pid, name, lk, g, pose,
                                prop, ready}], shooting}]
  booth_join {code, look, g}   [booth_room]          booth_find {look, g}   [booth_wait {secs}] or [booth_room]
  booth_set {frame?, bg?, pose?, prop?}  booth_ready {}  booth_go {}  booth_kick {pid}
  booth_cancel {} [booth_left {why: 'cancel'}]      booth_out {} [booth_left {why: 'out'}]
Server pushes: booth_room (after every change, to everyone in it), booth_shoot {n, gap, id}, booth_none {why},
booth_left {why: other | kick | blocked | idle}.
"""
from __future__ import annotations

import re
import secrets
import time

from .protocol import Feature, LiveError, on
from .street import clean_look

PREFIX = 'booth:'
CAP = 4                    # players in a friends' room
PAIR = 2                   # a strangers' room
ROOMS_MAX = 2000
QUEUE_MAX = 500
WAIT_SECS = 60             # a stranger waits this long at most
IDLE_SECS = 15 * 60        # a room nobody touched for this long closes
SHOTS, GAP_MS = 4, 3200    # a shoot: SHOTS photos, a 3-2-1 countdown each
CODE_LEN = 4
CODE_CHARS = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
ID = re.compile(r'[a-z0-9_]{1,16}')
NOCODE = 'Không thấy phòng mã này, kiểm tra lại mã nha.'


def clean_id(v, default: str) -> str:
    """A frame / pose / prop id: a short lowercase word; anything else is the default (never refused)."""
    return v if isinstance(v, str) and ID.fullmatch(v) else default


def clean_code(v) -> str | None:
    """A room code as typed (any case, spaces around): the code, or None when it cannot be one."""
    if not isinstance(v, str):
        return None
    c = v.strip().upper()
    return c if len(c) == CODE_LEN and all(ch in CODE_CHARS for ch in c) else None


class Member:
    __slots__ = ('pid', 'player', 'conn', 'name', 'look', 'g', 'pose', 'prop', 'ready', 'n')

    def __init__(self, conn, look: dict, g, n: int):
        self.conn, self.player, self.pid = conn, conn.player, conn.player.pid
        self.name = conn.player.name or ''
        self.look, self.g = look, g
        self.pose, self.prop, self.ready, self.n = 'dung', 'none', False, n

    def public(self) -> dict:
        return dict(pid=self.pid, name=self.name, lk=self.look, g=self.g, pose=self.pose, prop=self.prop, ready=self.ready)


class Waiter:
    __slots__ = ('conn', 'look', 'g', 'since')

    def __init__(self, conn, look, g, since):
        self.conn, self.look, self.g, self.since = conn, look, g, since


class BoothFeature(Feature):
    name, flag = 'booth', 'fair'

    def __init__(self, app):
        super().__init__(app)
        self.queue: dict = {}      # pid -> Waiter (insertion order: who waits longest first)
        self.seq = 0               # rooms made (ids of the strangers' rooms, shoot ids)
        self.made = self.paired = self.shoots = 0

    async def start(self):
        if self.cfg.fair:   # clients offer the shared booth only when the welcome says so
            self.cfg.flags_extra['booth'] = True

    # ---- rooms ----------------------------------------------------------------------------------------------
    def _rooms(self) -> list:
        return self.hub.rooms_with_prefix(PREFIX)

    def _new_room(self, mode: str):
        if len(self._rooms()) >= ROOMS_MAX:
            raise LiveError('full', 'Buồng chụp đông quá, lát quay lại nhé.')
        self.seq += 1
        code = None
        if mode == 'friends':
            for _ in range(50):
                c = ''.join(secrets.choice(CODE_CHARS) for _ in range(CODE_LEN))
                if PREFIX + c not in self.hub.rooms:
                    code = c
                    break
            if code is None:
                raise LiveError('full', 'Buồng chụp đông quá, lát quay lại nhé.')
        rid = PREFIX + (code or f'~{self.seq}')
        room = self.hub.room(rid, cap=CAP if mode == 'friends' else PAIR, on_empty=self._empty)
        room.data.update(code=code or '', mode=mode, host=None, people={}, frame='dem_hoi', bg='kem', last=time.monotonic(),
                         shoot_until=0.0, n=0, banned=set(), shot=0)
        self.made += 1
        return room

    def _empty(self, room) -> None:
        self.hub.drop_room(room.id)

    def _add(self, room, conn, look, g) -> Member:
        d = room.data
        d['n'] += 1
        m = Member(conn, look, g, d['n'])
        room.add(conn)
        d['people'][m.pid] = m
        if d['host'] is None:
            d['host'] = m.pid
        conn.ext['booth'] = room.id
        conn.player.ext['booth'] = room.id
        d['last'] = time.monotonic()
        return m

    def snapshot(self, room) -> dict:
        d = room.data
        return dict(t='booth_room', room=room.id[len(PREFIX):], code=d['code'], mode=d['mode'], host=d['host'],
                    frame=d['frame'], bg=d['bg'], cap=room.cap, shooting=d['shoot_until'] > time.monotonic(),
                    people=[m.public() for m in d['people'].values()])

    def _tell(self, room) -> None:
        """The room as it is now, to everyone in it (each told who they are)."""
        snap = self.snapshot(room)
        for m in room.data['people'].values():
            self.hub.send(m.conn, dict(snap, me=m.pid))

    def _remove(self, room, pid: str, why: str | None = None) -> None:
        """Take player pid out of the room (`why`: tell their socket so), hand the room on, tell the rest."""
        d = room.data
        m = d['people'].pop(pid, None)
        if m is None:
            return
        m.conn.ext.pop('booth', None)
        if m.player.ext.get('booth') == room.id:
            m.player.ext.pop('booth', None)
        if why:
            self.hub.send(m.conn, dict(t='booth_left', why=why))
        if d['host'] == pid:
            d['host'] = min(d['people'].values(), key=lambda x: x.n).pid if d['people'] else None
        d['last'] = time.monotonic()
        alive = self.hub.rooms.get(room.id) is room
        room.remove(m.conn)   # the last one out drops the room (on_empty)
        if alive and d['people']:
            self._tell(room)

    def _leave(self, p, why: str | None = None, keep=None) -> None:
        """Take player p out of their room or the queue (`why`: told to their socket unless it is `keep`)."""
        w = self.queue.pop(p.pid, None)
        if w is not None and why and w.conn is not keep:
            self.hub.send(w.conn, dict(t='booth_left', why=why))
        rid = p.ext.get('booth')
        room = self.hub.rooms.get(rid) if rid else None
        if room is None:
            p.ext.pop('booth', None)
            return
        m = room.data['people'].get(p.pid)
        self._remove(room, p.pid, why if m is not None and m.conn is not keep else None)

    def _mine(self, conn):
        rid = conn.ext.get('booth')
        room = self.hub.rooms.get(rid) if rid else None
        m = room.data['people'].get(conn.player.pid) if room is not None else None
        if m is None or m.conn is not conn:
            raise LiveError('not_in', 'Bạn chưa vào buồng chụp.')
        return room, m

    def _blocked(self, p, others) -> bool:
        return any(q in p.hidden or p.pid in o.player.hidden or self.hub.blocked(p.pid, q) for q, o in others)

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

    async def _who(self, conn, f):
        look, g = clean_look(f.get('look'), f.get('g'))
        await self._ensure_loaded(conn.player)
        return look, g

    # ---- the ways in --------------------------------------------------------------------------------------------
    @on('booth_make', rate=(6, 60))
    async def booth_make(self, conn, f):
        look, g = await self._who(conn, f)
        self._leave(conn.player, 'other', keep=conn)
        room = self._new_room('friends')
        self._add(room, conn, look, g)
        return dict(self.snapshot(room), me=conn.player.pid)

    @on('booth_join', rate=(10, 60))
    async def booth_join(self, conn, f):
        code = clean_code(f.get('code'))
        if code is None:
            raise LiveError('nocode', f'Mã phòng có {CODE_LEN} ký tự, gồm chữ và số nha.')
        look, g = await self._who(conn, f)
        p = conn.player
        room = self.hub.rooms.get(PREFIX + code)
        if room is None or room.data['mode'] != 'friends' or p.pid in room.data['banned'] or \
                self._blocked(p, [(q, m) for q, m in room.data['people'].items() if q != p.pid]):
            raise LiveError('nocode', NOCODE)
        m = room.data['people'].get(p.pid)
        if m is not None:   # already in (this tab, or another one of mine: this one takes my place)
            if m.conn is not conn:
                old, m.conn = m.conn, conn
                w = self.queue.pop(p.pid, None)
                if w is not None and w.conn is not conn:
                    self.hub.send(w.conn, dict(t='booth_left', why='other'))
                room.add(conn)
                conn.ext['booth'] = room.id
                old.ext.pop('booth', None)
                self.hub.send(old, dict(t='booth_left', why='other'))
                room.remove(old)
            return dict(self.snapshot(room), me=p.pid)
        if len(room.data['people']) >= room.cap:
            raise LiveError('full', f'Phòng đủ {room.cap} người rồi.')
        self._leave(p, 'other', keep=conn)
        self._add(room, conn, look, g)
        self._tell(room)
        return None

    @on('booth_find', rate=(10, 60))
    async def booth_find(self, conn, f):
        look, g = await self._who(conn, f)
        p = conn.player
        self._leave(p, 'other', keep=conn)
        now = time.monotonic()
        for q, w in list(self.queue.items()):
            if w.conn.closing or w.conn not in self.hub.conns:
                self.queue.pop(q, None)
                continue
            if q == p.pid or self._blocked(p, [(q, w.conn)]):
                continue
            self.queue.pop(q, None)
            room = self._new_room('stranger')
            self._add(room, w.conn, w.look, w.g)
            self._add(room, conn, look, g)
            self.paired += 1
            self._tell(room)
            return None
        if len(self.queue) >= QUEUE_MAX:
            raise LiveError('full', 'Buồng chụp đông quá, lát quay lại nhé.')
        self.queue[p.pid] = Waiter(conn, look, g, now)
        return dict(t='booth_wait', secs=WAIT_SECS)

    @on('booth_cancel', rate=(20, 60))
    async def booth_cancel(self, conn, f):
        self._leave(conn.player, 'other', keep=conn)
        return dict(t='booth_left', why='cancel')

    @on('booth_out', rate=(20, 60))
    async def booth_out(self, conn, f):
        self._leave(conn.player, 'other', keep=conn)
        return dict(t='booth_left', why='out')

    # ---- in the room ------------------------------------------------------------------------------------------
    @on('booth_set', rate=(20, 10))
    async def booth_set(self, conn, f):
        room, m = self._mine(conn)
        d = room.data
        if 'frame' in f or 'bg' in f:
            if d['host'] != m.pid:
                raise LiveError('host', 'Chủ phòng chọn khung nha.')
            if 'frame' in f:
                d['frame'] = clean_id(f.get('frame'), 'dem_hoi')
            if 'bg' in f:
                d['bg'] = clean_id(f.get('bg'), 'kem')
        if 'pose' in f:
            m.pose = clean_id(f.get('pose'), 'dung')
        if 'prop' in f:
            m.prop = clean_id(f.get('prop'), 'none')
        d['last'] = time.monotonic()
        self._tell(room)
        return None

    @on('booth_ready', rate=(20, 60))
    async def booth_ready(self, conn, f):
        room, m = self._mine(conn)
        m.ready = True
        room.data['last'] = time.monotonic()
        self._tell(room)
        return None

    @on('booth_go', rate=(6, 60))
    async def booth_go(self, conn, f):
        room, m = self._mine(conn)
        d = room.data
        now = time.monotonic()
        if d['host'] != m.pid:
            raise LiveError('host', 'Chủ phòng bấm chụp nha.')
        if d['shoot_until'] > now:
            raise LiveError('busy', 'Đang chụp rồi nè.')
        if not all(x.ready for x in d['people'].values()):
            raise LiveError('not_ready', 'Chờ mọi người sẵn sàng đã nha.')
        d['shoot_until'] = now + SHOTS * GAP_MS / 1000 + 1.5
        d['last'] = now
        d['shot'] += 1
        self.shoots += 1
        for x in d['people'].values():
            x.ready = False
        self.hub.send_many([x.conn for x in d['people'].values()], dict(t='booth_shoot', n=SHOTS, gap=GAP_MS, id=d['shot']))
        self._tell(room)
        return None

    @on('booth_kick', rate=(10, 60))
    async def booth_kick(self, conn, f):
        room, m = self._mine(conn)
        d = room.data
        pid = f.get('pid')
        if d['host'] != m.pid:
            raise LiveError('host', 'Chỉ chủ phòng mời người khác ra được.')
        if not isinstance(pid, str) or pid == m.pid or pid not in d['people']:
            raise LiveError('bad', 'Người này không còn trong phòng.')
        d['banned'].add(pid)
        self._remove(room, pid, 'kick')
        return None

    # ---- every second: the queue's time, idle rooms, a block made in a room ------------------------------------------
    async def tick(self, now: float):
        mono = time.monotonic()
        for q, w in list(self.queue.items()):
            if mono - w.since >= WAIT_SECS:
                self.queue.pop(q, None)
                self.hub.send(w.conn, dict(t='booth_none', why='timeout'))
        for room in self._rooms():
            d = room.data
            if mono - d['last'] >= IDLE_SECS and d['shoot_until'] <= mono:
                for pid in list(d['people']):
                    self._remove(room, pid, 'idle')
                continue
            people = d['people']
            if len(people) < 2:
                continue
            for m in sorted(people.values(), key=lambda x: -x.n):   # the later one goes
                if m.pid in people and self._blocked(m.player, [(q, o) for q, o in people.items() if q != m.pid]):
                    self._remove(room, m.pid, 'blocked')

    async def on_close(self, conn):
        p = conn.player
        w = self.queue.get(p.pid)
        if w is not None and w.conn is conn:
            self.queue.pop(p.pid, None)
        rid = conn.ext.pop('booth', None)
        room = self.hub.rooms.get(rid) if rid else None
        if room is not None:
            m = room.data['people'].get(p.pid)
            if m is not None and m.conn is conn:
                self._remove(room, p.pid)
        elif rid and p.ext.get('booth') == rid:   # the room went with this socket (it was the last one in it)
            p.ext.pop('booth', None)

    def stats(self) -> dict:
        rooms = self._rooms()
        return dict(booth_rooms=len(rooms), booth_people=sum(len(r.data['people']) for r in rooms), booth_waiting=len(self.queue),
                    booth_made=self.made, booth_paired=self.paired, booth_shoots=self.shoots)
