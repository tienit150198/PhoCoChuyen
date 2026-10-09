"""Private home presence, authorized by marriage or accepted home invitations.

No positions, gestures or room ids are persisted. Up to twelve occupants, one
controlling tab each. Every action and periodic tick rechecks current access.

home_in {r,host?,look?,g?,x?,y?} -> home_room {room,r,host,me,people,cap:12}
home_mv {p:[[x,y],[x,y]],ms}; home_emote {kind:hug|kiss|heart,to:pid}
home_reply {id,answer:accept|shy|sulk|decline|cancel}; offers expire after 15 seconds.
home_out -> home_left {why:out}; takeover/revocation: home_left {why:other|changed}
home {room,ev:[{k:in,...person}|{k:mv,pid,p,ms}|{k:out,pid}|
    {k:emote,id,pid,to,kind,ttl}|{k:reaction,id,pid,to,kind,answer}|{k:ended,id,why}]}
home_changed is a furniture invalidation only: clients refetch their authorized view.
"""
from __future__ import annotations

import hashlib
import math
import secrets
import time

from game import deco, deco_mate
from . import jsonx
from .auth import pid_of
from .db import Error as DbError
from .fair import clean_point
from .protocol import Feature, LiveError, on
from .street import clean_look

PREFIX = 'home:'
CAP = 12
CHECK_EVERY = 2.0
MAX_MS = 3000
EMOTES = frozenset(('hug', 'kiss', 'heart'))
REPLIES = frozenset(('accept', 'shy', 'sulk', 'decline', 'cancel'))
OFFER_TTL = 15
NEAR = .32

# One statement sees the relationship, both homes and both kinds of blocks in the
# same PostgreSQL snapshot. sha256(bytea) is built into supported PostgreSQL 16.
PAIR_SQL = """
SELECT c.id, c.a, c.b, sa.state AS state_a, sb.state AS state_b
FROM marriage_bonds m JOIN couples c ON c.id=m.couple
JOIN marriage_bonds ma ON ma.sid=c.a AND ma.couple=c.id
JOIN marriage_bonds mb ON mb.sid=c.b AND mb.couple=c.id
JOIN sessions sa ON sa.sid=c.a JOIN sessions sb ON sb.sid=c.b
WHERE m.sid=? AND (c.a=m.sid OR c.b=m.sid) AND c.a<>c.b AND c.status='married'
AND NOT EXISTS (SELECT 1 FROM marriage_blocks z
                WHERE (z.sid=c.a AND z.target=c.b) OR (z.sid=c.b AND z.target=c.a))
AND NOT EXISTS (SELECT 1 FROM blocks z WHERE
 (z.pid=substring(encode(sha256(convert_to('pid:' || c.a,'UTF8')),'hex'),1,16)
  AND z.target=substring(encode(sha256(convert_to('pid:' || c.b,'UTF8')),'hex'),1,16)) OR
 (z.pid=substring(encode(sha256(convert_to('pid:' || c.b,'UTF8')),'hex'),1,16)
  AND z.target=substring(encode(sha256(convert_to('pid:' || c.a,'UTF8')),'hex'),1,16)))
"""

OWN_SQL = 'SELECT state FROM sessions WHERE sid=?'
BLOCK_SQL = """SELECT 1 AS blocked WHERE
EXISTS (SELECT 1 FROM marriage_blocks WHERE (sid=? AND target=?) OR (sid=? AND target=?))
OR EXISTS (SELECT 1 FROM blocks WHERE (pid=? AND target=?) OR (pid=? AND target=?))"""


def owned_access(owner, state, mode='owner'):
    try:
        journey = jsonx.loads(state)['journey']
        place = deco.place(journey)
        # 🏰 'estate': a villa bought in Mua sắm that its owner lives in (game/estates.py, game/home_guests.py _own).
        if not journey.get('story') or (place['where'] not in ('own', 'estate') and not (place['where'] == 'lease' and mode == 'owner')):
            return None
        base = PREFIX + hashlib.sha256(f"{owner}:{place['key']}".encode()).hexdigest()[:32]
        return dict(base=base, owner=owner, rooms={r['id'] for r in deco.rooms_of(place['key']) or []}, mode=mode)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def access_of(row):
    """The canonical home and permitted physical rooms, or None for stale/bad saves."""
    if not row:
        return None
    try:
        a, b = jsonx.loads(row['state_a']), jsonx.loads(row['state_b'])
        ja, jb = a['journey'], b['journey']
        if not ja.get('story') or not jb.get('story') or not deco_mate.same_home(ja, jb, row['id']):
            return None
        owner, journey = (row['a'], ja) if deco.place(ja)['where'] == 'own' else (row['b'], jb)
        access = owned_access(owner, jsonx.dumps(dict(journey=journey)), 'pair')
        if access:
            access['sids'] = frozenset((row['a'], row['b']))
        return access
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


class HomeFeature(Feature):
    name, flag = 'home', 'home'

    def __init__(self, app):
        super().__init__(app)
        self.check_at = 0.0

    def _empty(self, room):
        self.hub.drop_room(room.id)

    def _end_offer(self, room, why, broadcast=True):
        offer=room.data.pop('offer',None)
        if offer and broadcast:
            room.send(dict(t='home',room=room.id,ev=[dict(k='ended',id=offer['id'],why=why)]))

    def _expire_offer(self, room, now=None):
        offer=room.data.get('offer')
        if offer and offer['until'] <= (time.time() if now is None else now):
            self._end_offer(room,'expired')

    @staticmethod
    def _near(room, sender, target):
        a,b=room.data['people'].get(sender),room.data['people'].get(target)
        return bool(a and b and math.hypot(a['x']-b['x'],a['y']-b['y']) <= NEAR)

    def _current(self, conn):
        rid = conn.ext.get('home')
        room = self.hub.rooms.get(rid) if rid else None
        if room is None or conn.player.ext.get('home_conn') is not conn or conn not in room.conns:
            return None
        return room

    def _detach(self, conn, why=None, broadcast=True):
        rid = conn.ext.pop('home', None)
        room = self.hub.rooms.get(rid) if rid else None
        p = conn.player
        if p.ext.get('home_conn') is conn:
            p.ext.pop('home_conn', None)
            if room is not None:
                offer = room.data.get('offer')
                if offer and p.pid in (offer['pid'], offer['to']):
                    self._end_offer(room,'left',broadcast=broadcast)
                room.data['people'].pop(p.pid, None)
                if broadcast:
                    # Removal must clear an already-visible avatar even when a
                    # fresh block now filters this player's ordinary events.
                    room.send(dict(t='home', room=room.id, ev=[dict(k='out', pid=p.pid)]), skip=conn)
        if room is not None:
            room.remove(conn)
        if why:
            self.hub.send(conn, dict(t='home_left', why=why))

    def _revoke(self, base):
        # Includes a spouse standing in another physical room of this home. No
        # peer event is sent after access changed; each tab clears its whole view.
        for room in list(self.hub.rooms_with_prefix(base + ':')):
            for c in list(room.conns):
                self._detach(c, 'changed', broadcast=False)

    def _revoke_pair(self, base):
        for room in list(self.hub.rooms_with_prefix(base + ':')):
            departed = []
            offer = room.data.get('offer')
            for c in list(room.conns):
                if c.ext.get('home_mode') == 'pair':
                    departed.append(c.player.pid)
                    self._detach(c, 'changed', broadcast=False)
            if room.conns:
                if offer and not room.data.get('offer'):
                    room.send(dict(t='home', room=room.id, ev=[dict(k='ended', id=offer['id'], why='left')]))
                for pid in departed:
                    room.send(dict(t='home', room=room.id, ev=[dict(k='out', pid=pid)]))

    async def _access(self, sid, host='', mode=None):
        if host:
            from game.home_guests import ACCESS_SQL, access_from_row
            row = await self.db.fetchrow(ACCESS_SQL, (sid, host))
            grant = access_from_row(row)
            return owned_access(grant['owner_sid'], row['owner_state'], grant['kind']) if grant else None
        pair = access_of(await self.db.fetchrow(PAIR_SQL, (sid,)))
        if pair or mode == 'pair':
            return pair
        # Ownership authorizes a fresh entry even when a spouse lives elsewhere,
        # is blocked, or has stale shared-home data. Existing pair sessions above
        # still lose their joint access when that relationship changes.
        row = await self.db.fetchrow(OWN_SQL, (sid,))
        return owned_access(sid, row['state']) if row else None

    async def _blocked(self, a, b):
        return bool(await self.db.fetchrow(BLOCK_SQL, (a.sid, b.sid, b.sid, a.sid,
                                                       a.pid, b.pid, b.pid, a.pid)))

    async def _validate(self, conn, room):
        access = await self._access(conn.player.sid, conn.ext.get('home_host', ''), conn.ext.get('home_mode'))
        if self._current(conn) is not room:
            return False
        if access and access['base'] == room.data['base'] and room.data['r'] in access['rooms']:
            return True
        # A sold/moved home closes every room. A revoked invitation removes only
        # its guest; legacy pair sessions keep their existing joint invalidation.
        owner = await self.db.fetchrow('SELECT state FROM sessions WHERE sid=?', (room.data['owner'],))
        current = owned_access(room.data['owner'], owner['state']) if owner else None
        if not current or current['base'] != room.data['base']:
            self._revoke(room.data['base'])
        elif conn.ext.get('home_mode') == 'pair':
            self._revoke_pair(room.data['base'])
        else:
            self._detach(conn, 'changed')
        return False

    async def _check(self, conn):
        room = self._current(conn)
        if room is None:
            raise LiveError('no_home', 'Bạn chưa ở trong phòng nhà chung.')
        try:
            valid = await self._validate(conn, room)
            if valid:
                for peer in list(room.conns):
                    if peer is conn:
                        continue
                    if await self._validate(peer, room) and await self._blocked(conn.player, peer.player):
                        # Prefer keeping the owner; otherwise eject the actor.
                        victim = peer if conn.player.sid == room.data['owner'] else conn
                        self._detach(victim, 'changed')
        except DbError:
            self._revoke(room.data['base'])
            raise
        # Another tab, a notification, or the ticker may have removed this
        # presence while the database query yielded. Never revive it here.
        if self._current(conn) is not room:
            raise LiveError('no_home', 'Phòng nhà đã thay đổi.')
        if not valid:
            raise LiveError('no_home', 'Bạn không còn quyền ở căn nhà này.')
        return room

    @on('home_in', rate=(20, 60))
    async def home_in(self, conn, f):
        physical = f.get('r')
        host = f.get('host', '')
        if not isinstance(host, str) or len(host) > 32:
            raise LiveError('bad', 'Mã chủ nhà không hợp lệ.')
        if not isinstance(physical, str) or not 1 <= len(physical) <= 32:
            raise LiveError('bad', 'Phòng không hợp lệ.')
        look, gender = clean_look(f.get('look'), f.get('g'))
        point = clean_point([f.get('x'), f.get('y')]) if 'x' in f or 'y' in f else [.5, .8]
        # A late join result from an older tab cannot win over a newer request.
        p = conn.player
        ticket = object()
        p.ext['home_join'] = ticket
        conn.ext['home_join'] = ticket
        access = await self._access(p.sid, host)
        if p.ext.get('home_join') is not ticket or conn.closing or conn not in p.conns:
            return None
        if access is None:
            old = self._current(conn)
            if old is not None:
                self._detach(conn, 'changed')
            raise LiveError('no_home', 'Bạn chưa có quyền vào căn nhà này.')
        if physical not in access['rooms']:
            raise LiveError('bad', 'Phòng không có trong căn nhà này.')
        rid = access['base'] + ':' + physical
        existing = self.hub.rooms.get(rid)
        if existing:
            for peer in list(existing.conns):
                if peer.player is not p and await self._validate(peer, existing) and await self._blocked(p, peer.player):
                    raise LiveError('no_home', 'Chưa thể vào phòng này.')
            # Invitation or house changes can commit while peer checks yield.
            # Re-read the actor before exposing the room's people snapshot.
            fresh = await self._access(p.sid, host)
            if p.ext.get('home_join') is not ticket or conn.closing or conn not in p.conns:
                return None
            if not fresh or fresh['base'] != access['base'] or physical not in fresh['rooms']:
                if self._current(conn) is not None:
                    self._detach(conn, 'changed')
                raise LiveError('no_home', 'Bạn không còn quyền vào căn nhà này.')
            access = fresh
        if p.ext.get('home_join') is not ticket or conn.closing or conn not in p.conns:
            return None
        old = p.ext.get('home_conn')
        if old is not None:
            self._detach(old, 'other' if old is not conn else None)
        room = self.hub.room(rid, cap=CAP, on_empty=self._empty)
        if not room.data:
            room.data.update(base=access['base'], owner=access['owner'], r=physical, people={})
        if not room.add(conn):
            raise LiveError('full', 'Phòng đang bận, thử lại nhé.')
        person = dict(pid=p.pid, name=p.name, lk=look, g=gender, x=point[0], y=point[1])
        people = list(room.data['people'].values())
        room.data['people'][p.pid] = person
        conn.ext['home'] = rid
        conn.ext['home_host'] = host
        conn.ext['home_mode'] = access['mode']
        p.ext['home_conn'] = conn
        room.send(dict(t='home', room=room.id, ev=[dict(k='in', **person)]), sender=p, skip=conn)
        return dict(t='home_room', room=rid, r=physical, host=host, me=p.pid, people=people, cap=CAP)

    @on('home_out', rate=(20, 60))
    async def home_out(self, conn, f):
        ticket = conn.ext.pop('home_join', None)
        if conn.player.ext.get('home_join') is ticket:
            conn.player.ext.pop('home_join', None)
        self._detach(conn)
        return dict(t='home_left', why='out')

    @on('home_mv', rate=(4, 1.0))
    async def home_mv(self, conn, f):
        path, ms = f.get('p'), f.get('ms')
        if not isinstance(path, list) or len(path) != 2 or type(ms) not in (int, float) or not math.isfinite(ms):
            raise LiveError('bad', 'Vị trí không hợp lệ.')
        path = [clean_point(point) for point in path]
        room = await self._check(conn)
        offer = room.data.get('offer')
        if offer and conn.player.pid in (offer['pid'], offer['to']):
            self._end_offer(room,'moved')
        person = room.data['people'][conn.player.pid]
        person['x'], person['y'] = path[-1]
        room.send(dict(t='home', room=room.id, ev=[dict(k='mv', pid=conn.player.pid, p=path,
                                        ms=int(min(MAX_MS, max(0, ms))))]), sender=conn.player)

    @on('home_emote', rate=(6, 10))
    async def home_emote(self, conn, f):
        kind, target = f.get('kind'), f.get('to')
        if not isinstance(kind, str) or kind not in EMOTES or not isinstance(target, str):
            raise LiveError('bad', 'Cử chỉ không hợp lệ.')
        room = await self._check(conn)
        if target == conn.player.pid or target not in room.data['people']:
            raise LiveError('no_home', 'Người ấy chưa ở cùng phòng.')
        self._expire_offer(room)
        if room.data.get('offer'):
            raise LiveError('busy','Đang chờ một lời đáp. Đợi chút hoặc hủy lời đang gửi nhé.')
        if not self._near(room,conn.player.pid,target):
            raise LiveError('too_far','Người ấy đã đi ra xa. Bước lại gần rồi thử nhé.')
        offer=dict(id=secrets.token_hex(8),pid=conn.player.pid,to=target,kind=kind,until=time.time()+OFFER_TTL)
        room.data['offer']=offer
        room.send(dict(t='home',room=room.id,ev=[dict(k='emote',id=offer['id'],pid=offer['pid'],to=target,kind=kind,ttl=OFFER_TTL)]),sender=conn.player)

    @on('home_reply', rate=(8, 10))
    async def home_reply(self, conn, f):
        ident,answer=f.get('id'),f.get('answer')
        if not isinstance(ident,str) or len(ident)!=16 or not isinstance(answer,str) or answer not in REPLIES:
            raise LiveError('bad','Chọn cách đáp lại hợp lệ nhé.')
        room=await self._check(conn)
        self._expire_offer(room)
        offer=room.data.get('offer')
        if not offer or offer['id']!=ident:
            raise LiveError('stale','Cử chỉ này đã kết thúc. Hai bạn có thể bắt đầu lại.')
        who=offer['pid'] if answer=='cancel' else offer['to']
        if conn.player.pid!=who:
            raise LiveError('not_yours','Chỉ người nhận mới chọn cách đáp lại; người gửi có thể hủy.')
        if answer in ('decline','cancel'):
            self._end_offer(room,'declined' if answer=='decline' else 'cancelled')
            return
        if not self._near(room,offer['pid'],offer['to']):
            self._end_offer(room,'moved')
            raise LiveError('too_far','Hai bạn đã đi xa nhau. Bước lại gần để tương tác nhé.')
        room.data.pop('offer',None)
        room.send(dict(t='home',room=room.id,ev=[dict(k='reaction',id=ident,pid=offer['to'],to=offer['pid'],kind=offer['kind'],answer=answer)]),sender=conn.player)

    async def on_close(self, conn):
        self._detach(conn)

    async def tick(self, now):
        for room in list(self.hub.rooms_with_prefix(PREFIX)):
            self._expire_offer(room,now)
        if now < self.check_at:
            return
        self.check_at = now + CHECK_EVERY
        # Every occupant needs fresh invitation/expiry/block checks, including
        # guests in another physical room and homes whose owner is offline.
        for room in list(self.hub.rooms_with_prefix(PREFIX)):
            for conn in list(room.conns):
                try:
                    await self._check(conn)
                except (LiveError, *DbError):
                    pass

    async def on_notify(self, event):
        if not self.enabled() or event.get('t') != 'home_changed' or not isinstance(event.get('sid'), str):
            return
        sid = event['sid']
        if len(sid) != 64:
            return
        row = await self.db.fetchrow(PAIR_SQL, (sid,))
        recipients = {sid}
        if row:
            recipients.update((row['a'], row['b']))
        for room in list(self.hub.rooms_with_prefix(PREFIX)):
            if room.data['owner'] == sid or any(c.player.sid == sid for c in room.conns):
                recipients.update(c.player.sid for c in room.conns)
        for target in recipients:
            player = self.hub.players.get(pid_of(target))
            if player is None or player.sid != target:
                continue
            conn = player.ext.get('home_conn')
            if conn is not None:
                try:
                    await self._check(conn)
                except (LiveError, *DbError):
                    pass
            self.hub.send_many(self.hub.conns_of(player.pid), dict(t='home_changed'))
