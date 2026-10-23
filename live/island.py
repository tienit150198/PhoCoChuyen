"""🏝️ Đảo riêng together (switch LIVE_HOME, like the homes): the owner and the friends aboard one trip walk the island
together, see each other, talk in bubbles and wave (game/island_trips.py keeps the trips and the seats).

Who may be there is the database's answer (island_trips.ACCESS_SQL: the trip is open (no time limit since 19/10; a
trip an older build started keeps its hour), this player is its owner or holds an 'aboard' seat, still a mutual friend
of the owner, nobody blocked — or 🌍 the owner opened it to everyone and this player is visiting it): checked on entry,
every CHECK_EVERY seconds and at once when the game server says something changed (NOTIFY {op:'island', sid, why,
trip}). The room's cap is the trip's seats, so it never holds more people than the vehicle carried, and
island_content.PUBLIC_CAP while it is open to everyone (island_trips.cap_for, read again on every check). Visitors
walk, wave and use the spots (the buildings' too: game/island_build.py) like everyone; nothing here touches the
database per movement frame. Two guests who
block each other share the island without seeing or hearing each other (Player.hidden, like the street).
Positions, gestures and bubbles are memory only; a bubble goes through the chat's store_message (filters, mutes,
kept like all chat) in the channel 'isl:<trip>' (chat.route: delete, report, admin hide).

Frames (client → server; replies in brackets)
  isl_in {trip, look, g, x?, y?}     [isl_room {room, trip, me, owner, island, kind, vehicle, seats, ends, people}]
  isl_out {}                         [isl_left {why: out}]
  isl_mv {p: [[x, y], [x, y]], ms}   positions are fractions of the island's map (0..1), clamped
  isl_emote {e}  isl_say {text}  isl_do {s}   (s: a spot of the map, public/js/island-layout.js)
Server pushes: isl {room, ev: [{k: in | mv | out | emote | said | do, ...}]}, isl_left {why: other | changed | ended |
time}, island_ping {why, trip} (a card to refresh: invite, seat, start, ended, left, removed). The welcome carries
`isl_inv` (pending invitations) when there are some. An older client ignores all of it.
"""
from __future__ import annotations

import math
import re
import time

from game.island_trips import ACCESS_SQL, ACCESS_SQL_FRIENDS, INVITED_SQL, access_for, cap_for

FRIENDS_ONLY_RETRY = 60.0   # seconds before the full check (island_public, island_visitors) is tried again
from .auth import pid_of
from . import fish_carry
from .db import Error as DbError, log
from .fair import clean_point
from .protocol import Feature, LiveError, on
from .street import clean_look

PREFIX = 'isl:'
TRIP_RE = re.compile(r'[0-9a-f]{16}')
SPOT_RE = re.compile(r'[a-z_]{1,16}')
SID_RE = re.compile(r'[0-9a-f]{64}')
EMOTES = frozenset(('wave', 'heart', 'laugh', 'wow', 'dance', 'cheers'))
SAY_LEN = 120
CHECK_EVERY = 5.0
MAX_MS = 6000
WHYS = frozenset(('invite', 'seat', 'start', 'ended', 'left', 'removed'))
RECHECK = frozenset(('ended', 'left', 'removed'))
OFF_SECS = 60.0


class IslandFeature(Feature):
    name, flag = 'island', 'home'

    def __init__(self, app):
        super().__init__(app)
        self.check_at = 0.0
        self.off_until = 0.0         # the tables are missing (an older game server): no invitation count until then

    async def start(self):
        if self.app.chat:
            self.app.chat.route(PREFIX, audience=self._audience, can_read=self._can_read)

    def _audience(self, ch: str) -> list:
        r = self.hub.rooms.get(ch)
        return [r] if r is not None else []

    def _can_read(self, player, ch: str) -> bool:
        return ch in player.ext.get('isl_seen', ())

    # ---- the welcome: invitations waiting --------------------------------------------------------------------
    async def on_hello(self, conn):
        if self.off_until > time.time():
            return
        try:
            n = await self.db.fetchval(INVITED_SQL, (conn.player.sid, time.time()))
        except DbError as e:
            log('island tables:', type(e).__name__)
            self.off_until = time.time() + OFF_SECS
            return
        if n:
            conn.ext['isl_inv'] = int(n)

    def welcome(self, conn) -> dict:
        n = conn.ext.pop('isl_inv', 0)
        return {'isl_inv': n} if n else {}

    # ---- rooms --------------------------------------------------------------------------------------------------
    def _empty(self, room):
        self.hub.drop_room(room.id)

    def _current(self, conn):
        rid = conn.ext.get('isl')
        room = self.hub.rooms.get(rid) if rid else None
        if room is None or conn.player.ext.get('isl_conn') is not conn or conn not in room.conns:
            return None
        return room

    def _detach(self, conn, why=None, broadcast=True):
        rid = conn.ext.pop('isl', None)
        room = self.hub.rooms.get(rid) if rid else None
        p = conn.player
        if p.ext.get('isl_conn') is conn:
            p.ext.pop('isl_conn', None)
            if room is not None:
                room.data['people'].pop(p.pid, None)
                if broadcast:   # every peer clears the avatar, also one who blocked this player since
                    room.send(dict(t='isl', room=room.id, ev=[dict(k='out', pid=p.pid)]), skip=conn)
        if room is not None:
            room.remove(conn)
        if why:
            self.hub.send(conn, dict(t='isl_left', why=why))

    def _close_room(self, room, why: str) -> None:
        for c in list(room.conns):
            self._detach(c, why, broadcast=False)

    async def _access(self, sid: str, trip: str):
        mono = time.monotonic()
        old = getattr(self, '_friends_only', 0.0)
        if not old or mono - old >= FRIENDS_ONLY_RETRY:
            try:
                row = await self.db.fetchrow(ACCESS_SQL, (sid, trip))
                self._friends_only = 0.0
                return row, access_for(row, sid, time.time())
            except DbError as e:
                if getattr(e, 'sqlstate', None) != '42P01':   # anything but a missing table: as before
                    raise
                if not old:
                    log('island access: island_public / island_visitors missing (the game server has not migrated yet): friends only')
                self._friends_only = mono
        # 🛟 deploy-order safety: the database is older than SCHEMA_VERSION 56: the friends-only check of 2.4.60
        row = await self.db.fetchrow(ACCESS_SQL_FRIENDS, (sid, trip))
        return row, access_for(row, sid, time.time())

    async def _check(self, conn):
        room = self._current(conn)
        if room is None:
            raise LiveError('no_island', 'Bạn chưa ở trên đảo.')
        try:
            row, kind = await self._access(conn.player.sid, room.data['trip'])
        except DbError:
            raise
        if self._current(conn) is not room:   # removed while the query yielded: never revive it
            raise LiveError('no_island', 'Chuyến ra đảo đã thay đổi.')
        if not kind:
            ended = not row or row['status'] != 'open' or float(row['ends']) <= time.time()
            if ended:
                self._close_room(room, 'time' if row and row['status'] == 'open' else 'ended')
            else:
                self._detach(conn, 'changed')
            raise LiveError('no_island', 'Chuyến ra đảo đã kết thúc.' if ended else 'Bạn không còn chỗ trên chuyến này.')
        room.data['ends'] = float(row['ends'])
        room.cap = cap_for(row)
        return room

    def _visible(self, a, b) -> bool:
        return b.pid not in a.hidden and a.pid not in b.hidden

    @on('isl_in', rate=(20, 60))
    async def isl_in(self, conn, f):
        trip = f.get('trip')
        if not isinstance(trip, str) or not TRIP_RE.fullmatch(trip):
            raise LiveError('bad', 'Chuyến đi không hợp lệ.')
        look, gender = clean_look(f.get('look'), f.get('g'))
        point = clean_point([f.get('x'), f.get('y')]) if 'x' in f or 'y' in f else [.5, .75]
        p = conn.player
        fh = await fish_carry.keep(self.db, p, fish_carry.clean(f.get('fh')))   # 🎣 the fish carried (live/fish_carry.py)
        ticket = object()
        p.ext['isl_join'] = ticket
        row, kind = await self._access(p.sid, trip)
        if p.ext.get('isl_join') is not ticket or conn.closing or conn not in p.conns:
            return None
        if not kind:
            if self._current(conn) is not None:
                self._detach(conn, 'changed')
            raise LiveError('no_island', 'Bạn chưa có chỗ trên chuyến ra đảo này.')
        old = p.ext.get('isl_conn')
        if old is not None:
            self._detach(old, 'other' if old is not conn else None)
        rid = PREFIX + trip
        room = self.hub.room(rid, cap=cap_for(row), on_empty=self._empty)
        room.cap = cap_for(row)   # opened to everyone (or closed) since the room was made
        if not room.data:
            room.data.update(trip=trip, owner=pid_of(row['owner']), island=row['island'], kind=row['kind'], vehicle=row['vehicle'],
                             seats=int(row['seats']), ends=float(row['ends']), people={})
        room.data['ends'] = float(row['ends'])
        if not room.add(conn):
            raise LiveError('full', 'Đảo đã đủ người của chuyến này.')
        person = dict(pid=p.pid, name=p.name, lk=look, g=gender, x=point[0], y=point[1], o=kind == 'owner', **({'fh': fh} if fh else {}))
        others = {c.player.pid: c.player for c in room.conns}
        people = [x for pid, x in room.data['people'].items() if pid != p.pid and pid in others and self._visible(p, others[pid])]
        room.data['people'][p.pid] = person
        conn.ext['isl'] = rid
        p.ext['isl_conn'] = conn
        seen = p.ext.setdefault('isl_seen', set())
        if len(seen) > 32:
            seen.clear()
        seen.add(rid)
        room.send(dict(t='isl', room=rid, ev=[dict(k='in', **person)]), sender=p, skip=conn)
        d = room.data
        return dict(t='isl_room', room=rid, trip=trip, me=p.pid, owner=d['owner'], island=d['island'], kind=d['kind'],
                    vehicle=d['vehicle'], seats=d['seats'], ends=d['ends'], people=people)

    @on('isl_out', rate=(20, 60))
    async def isl_out(self, conn, f):
        conn.player.ext.pop('isl_join', None)
        self._detach(conn)
        return dict(t='isl_left', why='out')

    @on('isl_mv', rate=(4, 1.0))
    async def isl_mv(self, conn, f):
        path, ms = f.get('p'), f.get('ms')
        if not isinstance(path, list) or len(path) != 2 or type(ms) not in (int, float) or not math.isfinite(ms):
            raise LiveError('bad', 'Vị trí không hợp lệ.')
        path = [clean_point(point) for point in path]
        room = await self._check(conn)
        person = room.data['people'][conn.player.pid]
        person['x'], person['y'] = path[-1]
        room.send(dict(t='isl', room=room.id, ev=[dict(k='mv', pid=conn.player.pid, p=path, ms=int(min(MAX_MS, max(0, ms))))]),
                  sender=conn.player, skip=conn)

    @on('isl_emote', rate=(6, 10))
    async def isl_emote(self, conn, f):
        e = f.get('e')
        if not isinstance(e, str) or e not in EMOTES:
            raise LiveError('bad', 'Không có biểu cảm này.')
        room = await self._check(conn)
        room.send(dict(t='isl', room=room.id, ev=[dict(k='emote', pid=conn.player.pid, e=e)]), sender=conn.player)

    @on('isl_do', rate=(6, 10))
    async def isl_do(self, conn, f):
        s = f.get('s')
        if not isinstance(s, str) or not SPOT_RE.fullmatch(s):
            raise LiveError('bad', 'Chỗ này không có trên đảo.')
        room = await self._check(conn)
        room.send(dict(t='isl', room=room.id, ev=[dict(k='do', pid=conn.player.pid, s=s)]), sender=conn.player, skip=conn)

    @on('isl_say', rate=(5, 10))
    async def isl_say(self, conn, f):
        room = await self._check(conn)
        p = conn.player
        if not self.app.chat:
            raise LiveError('off', 'Trò chuyện đang tắt.')
        frame = await self.app.chat.store_message(p, room.id, f.get('text'), SAY_LEN, 2)
        if self.hub.rooms.get(room.id) is room and p.pid in room.data['people']:
            room.send(dict(t='isl', room=room.id, ev=[dict(k='said', pid=p.pid, id=frame['id'], text=frame['text'])]), sender=p)

    # ---- lifecycle ----------------------------------------------------------------------------------------------
    async def on_close(self, conn):
        self._detach(conn)

    async def tick(self, now):
        rooms = list(self.hub.rooms_with_prefix(PREFIX))
        for room in rooms:
            if room.data.get('ends', math.inf) <= now:
                self._close_room(room, 'time')
        if now < self.check_at:
            return
        self.check_at = now + CHECK_EVERY
        for room in list(self.hub.rooms_with_prefix(PREFIX)):
            for conn in list(room.conns):
                try:
                    await self._check(conn)
                except (LiveError, *DbError):
                    pass

    async def on_notify(self, event):
        if not self.enabled() or event.get('op') != 'island':
            return
        sid, why, trip = event.get('sid'), event.get('why'), event.get('trip')
        if not isinstance(sid, str) or not SID_RE.fullmatch(sid) or why not in WHYS:
            return
        trip = trip if isinstance(trip, str) and TRIP_RE.fullmatch(trip) else ''
        player = self.hub.players.get(pid_of(sid))
        if player is None or player.sid != sid:
            return
        self.hub.send_many(self.hub.conns_of(player.pid), dict(t='island_ping', why=why, trip=trip))
        conn = player.ext.get('isl_conn')
        if why in RECHECK and conn is not None:
            try:
                await self._check(conn)
            except (LiveError, *DbError):
                pass
