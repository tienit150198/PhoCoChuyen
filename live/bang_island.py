"""⚔️ Đảo bang together (switch MNL_BANG_ISLAND, welcome flag `bisle`): the members of a bang, and the guests it lets
in, walk its island together (game/bang_island.py), see each other, talk in bubbles, gesture and stop at facilities.

Who may be there is the Bang branch's answer through the contract (game.bang_island.provider().access_live(db, sid,
bang)): asked on entry, again every CHECK_EVERY seconds per player from tick() (a few at a time), and at once when
the game server says something changed (NOTIFY {op: 'bang_island', sid?, bang?, why}). Never per movement frame:
positions, gestures and bubbles are memory only; a frame is checked against the room the socket is in. One room per
bang ('bisl:<bang id>'), at most CAP people. Two players who block each other share the island without seeing or
hearing each other (Player.hidden, like the street). A bubble goes through the chat's store_message (filters, mutes,
kept like all chat) in the channel 'bisl:<bang>' (chat.route: delete, report, admin hide).

Frames (client → server; replies in brackets)
  bisl_in {bang, look, g, x?, y?}     [bisl_room {room, bang, me, kind, role, cap, people}]
  bisl_out {}                         [bisl_left {why: out}]
  bisl_mv {p: [[x, y], [x, y]], ms}   positions are fractions of the island's map (0..1), clamped
  bisl_emote {e}  bisl_say {text}  bisl_do {s}   (s: a facility or a spot of public/js/bang-island-layout.js)
Server pushes: bisl {room, ev: [{k: in | mv | out | emote | said | do | view, ...}]} (a person: pid, name, lk, g, x, y,
kd: member | guest, r: role; view: the bang's facilities changed, fetch GET /api/bang-island again),
bisl_left {why: other | changed | ended}. An older client ignores it all.
"""
from __future__ import annotations

import math
import time

from game import bang_island as BI
from .db import Error as DbError, log
from .fair import clean_point
from .protocol import Feature, LiveError, on
from .street import clean_look

PREFIX = 'bisl:'
EMOTES = frozenset(('wave', 'heart', 'laugh', 'wow', 'bow', 'cheers', 'fight'))
SPOTS = frozenset((*BI.FACILITY_IDS, *BI.SPOTS))
SAY_LEN = 120
CHECK_EVERY = 10.0           # seconds between two access checks of one player
CHECKS_PER_TICK = 200        # at most this many checks per second (the rest wait for the next tick)
MAX_MS = 6000
WHYS = frozenset(('join', 'left', 'kicked', 'role', 'guest', 'view', 'disband'))
SID_LEN = 64


class BangIslandFeature(Feature):
    name, flag = 'bang_island', 'bisle'
    check_every = CHECK_EVERY

    async def start(self):
        if self.app.chat:
            self.app.chat.route(PREFIX, audience=self._audience, can_read=self._can_read)

    def _audience(self, ch: str) -> list:
        r = self.hub.rooms.get(ch)
        return [r] if r is not None else []

    def _can_read(self, player, ch: str) -> bool:
        return ch in player.ext.get('bisl_seen', ())

    # ---- rooms --------------------------------------------------------------------------------------------------
    def _empty(self, room):
        self.hub.drop_room(room.id)

    def _current(self, conn):
        rid = conn.ext.get('bisl')
        room = self.hub.rooms.get(rid) if rid else None
        if room is None or conn.player.ext.get('bisl_conn') is not conn or conn not in room.conns:
            return None
        return room

    def _room_of(self, conn):
        """The room this socket is in (memory only: what every frame but bisl_in uses)."""
        room = self._current(conn)
        if room is None:
            raise LiveError('no_bang_island', 'Bạn chưa ở trên đảo bang.')
        return room

    def _detach(self, conn, why=None, broadcast=True):
        rid = conn.ext.pop('bisl', None)
        conn.ext.pop('bisl_at', None)
        room = self.hub.rooms.get(rid) if rid else None
        p = conn.player
        if p.ext.get('bisl_conn') is conn:
            p.ext.pop('bisl_conn', None)
            if room is not None:
                room.data['people'].pop(p.pid, None)
                if broadcast:
                    room.send(dict(t='bisl', room=room.id, ev=[dict(k='out', pid=p.pid)]), skip=conn)
        if room is not None:
            room.remove(conn)
        if why:
            self.hub.send(conn, dict(t='bisl_left', why=why))

    def _close_room(self, room, why: str) -> None:
        for c in list(room.conns):
            self._detach(c, why, broadcast=False)

    async def _access(self, sid: str, bang: str):
        prov = BI.provider()
        if prov is None:
            return None
        acc = await prov.access_live(self.db, sid, bang)
        return acc if isinstance(acc, dict) and acc.get('kind') in ('member', 'guest') else None

    async def _recheck(self, conn) -> bool:
        """Ask the contract again whether this socket's player may stay; detach it if not. True: still there."""
        room = self._current(conn)
        if room is None:
            return False
        conn.ext['bisl_at'] = time.monotonic()
        acc = await self._access(conn.player.sid, room.data['bang'])
        if self._current(conn) is not room:   # moved or left while the check yielded
            return False
        if not acc:
            self._detach(conn, 'changed')
            return False
        person = room.data['people'].get(conn.player.pid)
        if person is not None:
            person['kd'], person['r'] = acc['kind'], acc.get('role') if acc['kind'] == 'member' else None
        return True

    def _visible(self, a, b) -> bool:
        return b.pid not in a.hidden and a.pid not in b.hidden

    @on('bisl_in', rate=(20, 60))
    async def bisl_in(self, conn, f):
        bang = f.get('bang')
        if not isinstance(bang, str) or not BI.BANG_ID.fullmatch(bang):
            raise LiveError('bad', 'Bang không hợp lệ.')
        look, gender = clean_look(f.get('look'), f.get('g'))
        point = clean_point([f.get('x'), f.get('y')]) if 'x' in f or 'y' in f else [.85, .85]
        p = conn.player
        ticket = object()
        p.ext['bisl_join'] = ticket
        try:
            acc = await self._access(p.sid, bang)
        except Exception as e:   # the database or the provider: refuse this once, never break the socket
            log('bang island join:', type(e).__name__)
            raise LiveError('busy', 'Đảo bang đang bận, thử lại sau nhé.')
        if p.ext.get('bisl_join') is not ticket or conn.closing or conn not in p.conns:
            return None
        if not acc:
            if self._current(conn) is not None:
                self._detach(conn, 'changed')
            raise LiveError('no_bang_island', 'Bạn không phải thành viên hay khách của bang này.')
        old = p.ext.get('bisl_conn')
        if old is not None:
            self._detach(old, 'other' if old is not conn else None)
        rid = PREFIX + bang
        room = self.hub.room(rid, cap=BI.CAP, on_empty=self._empty)
        if not room.data:
            room.data.update(bang=bang, people={})
        if not room.add(conn):
            raise LiveError('full', 'Đảo bang đang đông quá, chờ chút nhé.')
        role = acc.get('role') if acc['kind'] == 'member' else None
        person = dict(pid=p.pid, name=p.name, lk=look, g=gender, x=point[0], y=point[1], kd=acc['kind'], r=role if role in BI.ROLES else None)
        others = {c.player.pid: c.player for c in room.conns}
        people = [x for pid, x in room.data['people'].items() if pid != p.pid and pid in others and self._visible(p, others[pid])]
        room.data['people'][p.pid] = person
        conn.ext['bisl'] = rid
        conn.ext['bisl_at'] = time.monotonic()
        p.ext['bisl_conn'] = conn
        seen = p.ext.setdefault('bisl_seen', set())
        if len(seen) > 16:
            seen.clear()
        seen.add(rid)
        room.send(dict(t='bisl', room=rid, ev=[dict(k='in', **person)]), sender=p, skip=conn)
        return dict(t='bisl_room', room=rid, bang=bang, me=p.pid, kind=acc['kind'], role=person['r'], cap=BI.CAP, people=people)

    @on('bisl_out', rate=(20, 60))
    async def bisl_out(self, conn, f):
        conn.player.ext.pop('bisl_join', None)
        self._detach(conn)
        return dict(t='bisl_left', why='out')

    @on('bisl_mv', rate=(4, 1.0))
    async def bisl_mv(self, conn, f):
        path, ms = f.get('p'), f.get('ms')
        if not isinstance(path, list) or len(path) != 2 or type(ms) not in (int, float) or not math.isfinite(ms):
            raise LiveError('bad', 'Vị trí không hợp lệ.')
        path = [clean_point(point) for point in path]
        room = self._room_of(conn)
        person = room.data['people'][conn.player.pid]
        person['x'], person['y'] = path[-1]
        room.send(dict(t='bisl', room=room.id, ev=[dict(k='mv', pid=conn.player.pid, p=path, ms=int(min(MAX_MS, max(0, ms))))]),
                  sender=conn.player, skip=conn)

    @on('bisl_emote', rate=(6, 10))
    async def bisl_emote(self, conn, f):
        e = f.get('e')
        if not isinstance(e, str) or e not in EMOTES:
            raise LiveError('bad', 'Không có biểu cảm này.')
        room = self._room_of(conn)
        room.send(dict(t='bisl', room=room.id, ev=[dict(k='emote', pid=conn.player.pid, e=e)]), sender=conn.player)

    @on('bisl_do', rate=(6, 10))
    async def bisl_do(self, conn, f):
        s = f.get('s')
        if not isinstance(s, str) or s not in SPOTS:
            raise LiveError('bad', 'Chỗ này không có trên đảo.')
        room = self._room_of(conn)
        room.send(dict(t='bisl', room=room.id, ev=[dict(k='do', pid=conn.player.pid, s=s)]), sender=conn.player, skip=conn)

    @on('bisl_say', rate=(5, 10))
    async def bisl_say(self, conn, f):
        room = self._room_of(conn)
        p = conn.player
        if not self.app.chat:
            raise LiveError('off', 'Trò chuyện đang tắt.')
        frame = await self.app.chat.store_message(p, room.id, f.get('text'), SAY_LEN, 2)
        if self.hub.rooms.get(room.id) is room and p.pid in room.data['people']:
            room.send(dict(t='bisl', room=room.id, ev=[dict(k='said', pid=p.pid, id=frame['id'], text=frame['text'])]), sender=p)

    # ---- lifecycle ----------------------------------------------------------------------------------------------
    async def on_close(self, conn):
        self._detach(conn)

    async def tick(self, now):
        """Re-check access: every player about every check_every seconds, at most CHECKS_PER_TICK per tick."""
        due, mono = [], time.monotonic()
        for room in list(self.hub.rooms_with_prefix(PREFIX)):
            for conn in list(room.conns):
                if mono - conn.ext.get('bisl_at', 0) >= self.check_every:
                    due.append(conn)
                    if len(due) >= CHECKS_PER_TICK:
                        break
        for conn in due:
            try:
                await self._recheck(conn)
            except DbError as e:
                log('bang island access:', type(e).__name__)
                conn.ext['bisl_at'] = time.monotonic()   # keep them; try again next round
            except Exception as e:   # a provider bug must never stop the live service's tick
                log('bang island provider:', type(e).__name__, str(e)[:120])
                conn.ext['bisl_at'] = time.monotonic()

    async def on_notify(self, event):
        """{op: 'bang_island', why, sid?, bang?}: re-check that player now (left, kicked, role, guest), tell a room its
        facilities changed (view), or close a disbanded bang's island (disband)."""
        if not self.enabled() or event.get('op') != 'bang_island':
            return
        why, sid, bang = event.get('why'), event.get('sid'), event.get('bang')
        if why not in WHYS:
            return
        bang = bang if isinstance(bang, str) and BI.BANG_ID.fullmatch(bang) else None
        room = self.hub.rooms.get(PREFIX + bang) if bang else None
        if why == 'view' and room is not None:
            room.send(dict(t='bisl', room=room.id, ev=[dict(k='view')]))
            return
        if why == 'disband' and room is not None:
            self._close_room(room, 'ended')
            return
        if isinstance(sid, str) and 0 < len(sid) <= SID_LEN:
            from .auth import pid_of
            player = self.hub.players.get(pid_of(sid))
            conn = player.ext.get('bisl_conn') if player is not None and player.sid == sid else None
            if conn is not None:
                try:
                    await self._recheck(conn)
                except Exception as e:
                    log('bang island notify:', type(e).__name__)
