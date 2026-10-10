"""Real walkers on the shared career map. LIVE_TOWN enables this independently of chat.

Only public identity, sanitized wardrobe slots and ground coordinates leave this feature.
Private workplaces, tasks and saves stay in the existing HTTP game API. Rooms, movement
budgets and positions live in one service process's memory; movement performs no DB reads.

town_in {map:'iso-town-v1',x,y,direction,look,g} -> town_room {map,room,me,people,cap}
town_mv {x,y,direction,activity?}; town_out -> town_left {why:'out'}
activity is a cosmetic 320x200 outdoor pose, or null to return to town. It never
authorizes a leisure round, checkpoint, catch or reward; those remain HTTP-owned.
town {room,ev:[{k:'in'|'mv'|'out',...}]} batches changes at most 10 times/second.
One player's second tab takes over and sends town_left {why:'other'} to the first.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from pathlib import Path

from game.content import CAREERS
from . import faces
from .auth import pid_of
from .protocol import Feature, LiveError, on
from .street import clean_look

MAP_ID = 'iso-town-v1'
PREFIX = MAP_ID + ':'
CAP = 30
INSTANCES_MAX = 200
FLUSH = .1
EVENTS_MAX = 300
SPEED = 8.0                     # grid units/s; model walk/joystick <= 6 units/s
JITTER = .7                    # finite distance credit, not extra credit on every frame
MAX_CREDIT = SPEED * 1.5 + JITTER
DIRECTIONS = frozenset(('se', 'sw', 'ne', 'nw'))
RESIDENTIAL_ACTIVITIES = frozenset(('homes-rent', 'homes-apartment', 'homes-townhouse', 'homes-villa'))
ACTIVITY_PHASES = {'fishing': frozenset(('walk', 'waiting', 'bite')),
                   'boat': frozenset(('walk', 'boat', 'return')),
                   'pool': frozenset(('walk', 'pool', 'return')),
                   **{kind: frozenset(('idle', 'walk')) for kind in RESIDENTIAL_ACTIVITIES}}
ACTIVITY_ACTIONS = {'fishing': frozenset(('cast', 'reel', 'caught')),
                    'boat': frozenset(('board', 'exit')),
                    'pool': frozenset(('board', 'exit')),
                    **{kind: frozenset() for kind in RESIDENTIAL_ACTIVITIES}}
ACTIVITY_SPEED, ACTIVITY_JITTER = 88.0, 12.0  # local walk/swim/boat speed <= 72 px/s
ACTIVITY_MAX_CREDIT = ACTIVITY_SPEED * 1.5 + ACTIVITY_JITTER
ACTIVITY_ENTRY = {'boat': (104, 150), 'pool': (86, 142)}
BLOCK_REFRESH = 10.0            # REST blocks have no live event; background, never on movement
BLOCK_BATCH = 250


_LAYOUT = json.loads((Path(__file__).resolve().parent.parent / 'game' / 'town_layout.json').read_text(encoding='utf-8'))


def town_geometry(count=len(CAREERS)):
    """Open courtyards share bounds with the client; physical obstacles stay solid."""
    keys = ('x0', 'y0', 'x1', 'y1')
    return tuple(_LAYOUT['bounds'][k] for k in keys), tuple(tuple(r[k] for k in keys) for r in _LAYOUT['openGround'])


def town_obstacles(count=len(CAREERS)):
    keys = ('x0', 'y0', 'x1', 'y1')
    props = (_LAYOUT['lots'][:count] + _LAYOUT['commons'] + _LAYOUT['planting'] + _LAYOUT['shopLots']
             + [p for p in _LAYOUT['amenities'] if p.get('footprint')])
    return tuple(tuple(p['footprint'][k] for k in keys) for p in props)


BOUNDS, ROADS = town_geometry()
OBSTACLES = town_obstacles()
CLEARANCE = .14


def clean_point(x, y):
    if not all(type(v) in (int, float) and math.isfinite(v) for v in (x, y)):
        raise LiveError('bad', 'Vị trí không hợp lệ.')
    if not (BOUNDS[0] <= x <= BOUNDS[2] and BOUNDS[1] <= y <= BOUNDS[3]) or not any(
            x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in ROADS) or any(
            x0 - CLEARANCE <= x <= x1 + CLEARANCE and y0 - CLEARANCE <= y <= y1 + CLEARANCE
            for x0, y0, x1, y1 in OBSTACLES):
        raise LiveError('bad', 'Vị trí này có công trình, cây hoặc mặt nước.')
    return round(float(x), 3), round(float(y), 3)


def clean_direction(value):
    return value if isinstance(value, str) and value in DIRECTIONS else 'se'


def clean_activity(value):
    """A fresh, tightly whitelisted public pose; ignore private/unknown fields."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise LiveError('bad', 'Hoạt động không hợp lệ.')
    kind, phase, direction, action = (value.get(k) for k in ('kind', 'phase', 'direction', 'action'))
    x, y, moving = value.get('x'), value.get('y'), value.get('moving', False)
    residential = isinstance(kind, str) and kind in RESIDENTIAL_ACTIVITIES
    xmin, ymin, xmax, ymax = (-20, -20, 20, 20) if residential else (0, 0, 320, 200)
    if (not isinstance(kind, str) or kind not in ACTIVITY_PHASES or
            not isinstance(phase, str) or phase not in ACTIVITY_PHASES[kind] or
            not isinstance(direction, str) or direction not in DIRECTIONS or
            (action is not None and (not isinstance(action, str) or action not in ACTIVITY_ACTIONS[kind])) or
            type(moving) is not bool or
            not all(type(v) in (int, float) and math.isfinite(v) for v in (x, y)) or
            not (xmin <= x <= xmax and ymin <= y <= ymax)):
        raise LiveError('bad', 'Tư thế hoạt động không hợp lệ.')
    return dict(kind=kind, x=round(float(x), 2), y=round(float(y), 2), direction=direction,
                phase=phase, action=action, moving=moving)


def activity_credit(w, activity, now):
    """Bound ordinary motion; explicit dock transitions may reset local coordinates.

    A new activity (including reconnect) is an independent coordinate space. Neither
    entering it nor leaving it resets the separate town movement budget.
    """
    old = w.activity
    if activity is None or old is None or activity['kind'] != old['kind']:
        return ACTIVITY_JITTER
    entry = ACTIVITY_ENTRY.get(activity['kind'])
    near = lambda p, at, radius: math.hypot(p['x'] - at[0], p['y'] - at[1]) <= radius
    if entry and ((old['phase'] == 'walk' and activity['phase'] == activity['kind'] and
                   activity['action'] == 'board' and near(old, (84, 154), 24) and near(activity, entry, 3)) or
                  (old['phase'] == 'return' and activity['phase'] == 'walk' and
                   activity['action'] == 'exit' and near(old, entry, 24) and near(activity, (84, 174), 3))):
        return ACTIVITY_JITTER
    credit = min(ACTIVITY_MAX_CREDIT, w.activity_credit + max(0.0, now - w.activity_last) * ACTIVITY_SPEED)
    distance = math.hypot(activity['x'] - old['x'], activity['y'] - old['y'])
    if distance > credit + .03:
        raise LiveError('speed', 'Bước đi ngoài trời quá xa.')
    return max(0.0, credit - distance)


class Walker:
    def __init__(self, player, look, gender, point, direction, activity=None):
        self.player, self.pid = player, player.pid
        self.look, self.gender = look, gender
        self.x, self.y = point
        self.direction = direction
        self.last, self.credit = time.monotonic(), JITTER
        self.activity = activity
        self.activity_last, self.activity_credit = self.last, ACTIVITY_JITTER

    def public(self):
        out = dict(pid=self.pid, name=self.player.name or 'Mây', lk=self.look, g=self.gender,
                   fc=self.player.fc or '', x=self.x, y=self.y, direction=self.direction)
        if self.activity is not None:
            out['activity'] = dict(self.activity)
        return out


class TownFeature(Feature):
    name, flag = 'town', 'town'

    def __init__(self, app):
        super().__init__(app)
        self.flushes = 0
        self._blocks_at = time.monotonic() + BLOCK_REFRESH

    async def on_hello(self, conn):
        # Chat normally canonicalizes hello's public face. Also support town alone.
        p = conn.player
        if not self.cfg.chat:
            if self.app.chat is not None:
                await self.app.chat.load_hidden(p)
            fc = faces.clean(conn.ext.pop('fc', None), p.av)
            if fc is not None:
                p.fc = fc or None

    def welcome(self, conn):
        if self.cfg.chat:
            return {}
        return dict(me=dict(**conn.player.card(), fc=conn.player.fc or '', account=conn.player.account))

    async def _ensure_loaded(self, p):
        if self.app.chat is not None and not p.loaded:
            await self.app.chat.load_friends(p)
            await self.app.chat.load_hidden(p)
            p.loaded = True

    def _pick(self, p):
        rooms = self.hub.rooms_with_prefix(PREFIX)
        choices = [r for r in rooms if len(r.data['people']) < CAP and
                   not any(self.hub.blocked(p.pid, pid) for pid in r.data['people'])]
        if choices:
            return max(choices, key=lambda r: (len(r.data['people']), -int(r.id[len(PREFIX):])))
        if len(rooms) >= INSTANCES_MAX:
            raise LiveError('full', 'Khu phố đang đông, lát quay lại nhé.', wait=10)
        used, n = {r.id for r in rooms}, 1
        while f'{PREFIX}{n}' in used:
            n += 1
        room = self.hub.room(f'{PREFIX}{n}', cap=CAP, on_empty=self._empty)
        room.data.update(people={}, ev=[], mvi={}, h=None, last=0.0, hidden_seen=set())
        return room

    def _empty(self, room):
        if room.data.get('h') is not None:
            room.data['h'].cancel()
        self.hub.drop_room(room.id)

    def _me(self, conn):
        rid = conn.ext.get('town')
        room = self.hub.rooms.get(rid)
        w = room.data['people'].get(conn.player.pid) if room else None
        if w is None or conn not in room.conns:
            raise LiveError('not_in', 'Bạn chưa vào khu phố.')
        return room, w

    def _remove(self, room, pid):
        if room.data['people'].pop(pid, None) is not None:
            self._queue(room, pid, dict(k='out', pid=pid))

    def _leave(self, conn, why='out', takeover=False):
        p = conn.player
        # A stale first tab must never remove the new tab's presence.
        rid = p.ext.get('town') if takeover else conn.ext.get('town')
        room = self.hub.rooms.get(rid)
        if room is None:
            conn.ext.pop('town', None)
            return
        mine = [c for c in room.conns if c.player is p] if takeover else [conn]
        for c in mine:
            c.ext.pop('town', None)
            if takeover and c is not conn:
                self.hub.send(c, dict(t='town_left', why=why))
        self._remove(room, p.pid)
        for c in mine:
            room.remove(c)
        if p.ext.get('town') == rid:
            p.ext.pop('town', None)

    def _queue(self, room, pid, ev):
        d = room.data
        if ev['k'] == 'mv' and pid in d['mvi']:
            # A following legacy position-only move must not erase activity:null.
            previous = d['ev'][d['mvi'][pid]][1]
            d['ev'][d['mvi'][pid]] = (pid, {**previous, **ev})
        else:
            if ev['k'] == 'mv':
                d['mvi'][pid] = len(d['ev'])
            else:
                d['mvi'].pop(pid, None)
            d['ev'].append((pid, ev))
        if len(d['ev']) >= EVENTS_MAX:
            if d['h'] is not None:
                d['h'].cancel()
            self._flush(room)
        elif d['h'] is None:
            d['h'] = asyncio.get_running_loop().call_later(
                max(0.0, d['last'] + FLUSH - time.monotonic()), self._flush, room)

    def _flush(self, room):
        d = room.data
        d['h'] = None
        ev, d['ev'], d['mvi'], d['last'] = d['ev'], [], {}, time.monotonic()
        if not ev or self.hub.rooms.get(room.id) is not room:
            return
        self.flushes += 1
        # Serialize once for each distinct block-filtered audience, like FairFeature.
        senders, groups = {pid for pid, _ in ev}, {}
        for c in room.conns:
            if c.ready:
                excluded = frozenset(pid for pid in senders if self.hub.blocked(c.player.pid, pid))
                groups.setdefault(excluded, []).append(c)
        for excluded, conns in groups.items():
            events = [e for pid, e in ev if pid not in excluded]
            if events:
                self.hub.send_many(conns, dict(t='town', room=room.id, ev=events))

    @on('town_in', rate=(20, 60))
    async def town_in(self, conn, f):
        if f.get('map') != MAP_ID:
            raise LiveError('bad', 'Bản đồ không hợp lệ.')
        point = clean_point(f.get('x'), f.get('y'))
        activity = clean_activity(f.get('activity'))
        look, gender = clean_look(f.get('look'), f.get('g'))
        await self._ensure_loaded(conn.player)
        treasure = getattr(self.app, 'by_name', {}).get('treasure')
        if treasure is not None and treasure.enabled():
            point = await treasure.enter(conn) or point
        self._leave(conn, 'other', takeover=True)
        room = self._pick(conn.player)
        room.add(conn)
        w = Walker(conn.player, look, gender, point, clean_direction(f.get('direction')), activity)
        room.data['people'][w.pid] = w
        conn.ext['town'] = conn.player.ext['town'] = room.id
        self._queue(room, w.pid, dict(k='in', **w.public()))
        peers = [o.public() for pid, o in room.data['people'].items()
                 if pid != w.pid and not self.hub.blocked(w.pid, pid)]
        out = dict(t='town_room', map=MAP_ID, room=room.id, me=w.pid, people=peers, cap=CAP)
        if treasure is not None and treasure.enabled():
            out.update(x=w.x, y=w.y)
        if isinstance(f.get('cid'), str) and len(f['cid']) <= 40:
            out['cid'] = f['cid']
        return out

    @on('town_out', rate=(20, 60))
    async def town_out(self, conn, f):
        treasure = getattr(self.app, 'by_name', {}).get('treasure')
        if treasure is not None and treasure.enabled():
            await treasure.leave(conn)
        self._leave(conn)
        out = dict(t='town_left', why='out')
        if isinstance(f.get('cid'), str) and len(f['cid']) <= 40:
            out['cid'] = f['cid']
        return out

    @on('town_mv', rate=(4, 1.0))
    async def town_mv(self, conn, f):
        room, w = self._me(conn)
        x, y = clean_point(f.get('x'), f.get('y'))
        now = time.monotonic()
        credit = min(MAX_CREDIT, w.credit + max(0.0, now - w.last) * SPEED)
        distance = math.hypot(x - w.x, y - w.y)
        if distance > credit + .003:
            raise LiveError('speed', 'Bước đi quá xa.', x=w.x, y=w.y)
        activity = clean_activity(f['activity']) if 'activity' in f else w.activity
        remaining = activity_credit(w, activity, now)
        appearance = clean_look(f.get('look', w.look), f.get('g', w.gender)) if 'look' in f or 'g' in f else None
        w.credit, w.last = max(0.0, credit - distance), now
        w.x, w.y, w.direction = x, y, clean_direction(f.get('direction'))
        changed_activity = activity is not None or w.activity is not None or 'activity' in f
        w.activity, w.activity_credit, w.activity_last = activity, remaining, now
        event = dict(k='mv', pid=w.pid, x=x, y=y, direction=w.direction)
        if appearance is not None:
            w.look, w.gender = appearance
            event.update(lk=w.look, g=w.gender)
        if changed_activity:
            event['activity'] = dict(activity) if activity is not None else None
        self._queue(room, w.pid, event)

    async def _refresh_blocks(self):
        """Bounded bulk read of both existing block systems for current walkers only."""
        if self.db is None or time.monotonic() < self._blocks_at:
            return
        self._blocks_at = time.monotonic() + BLOCK_REFRESH
        players = {w.pid: w.player for room in self.hub.rooms_with_prefix(PREFIX)
                   for w in room.data['people'].values()}
        people = list(players.values())
        hidden = {p.pid: set() for p in people}
        for offset in range(0, len(people), BLOCK_BATCH):
            group = people[offset:offset + BLOCK_BATCH]
            pids, sids = [p.pid for p in group], [p.sid for p in group]
            slots = ','.join('?' for _ in group)
            blocks = await self.db.fetch(f'SELECT pid, target FROM blocks WHERE pid IN ({slots}) OR target IN ({slots})', pids + pids)
            married = await self.db.fetch(f'SELECT sid, target FROM marriage_blocks WHERE sid IN ({slots}) OR target IN ({slots})', sids + sids)
            for a, b in [(r['pid'], r['target']) for r in blocks] + [(pid_of(r['sid']), pid_of(r['target'])) for r in married]:
                if a in hidden:
                    hidden[a].add(b)
                if b in hidden:
                    hidden[b].add(a)
        for pid, p in players.items():
            p.hidden = hidden[pid]

    async def tick(self, now):
        await self._refresh_blocks()
        for room in self.hub.rooms_with_prefix(PREFIX):
            d, people = room.data, room.data['people']
            for pid, w in list(people.items()):
                for q in w.player.hidden & people.keys():
                    pair = frozenset((pid, q))
                    if pair not in d['hidden_seen']:
                        d['hidden_seen'].add(pair)
                        for a, b in ((pid, q), (q, pid)):
                            self.hub.send_many([c for c in room.conns if c.player.pid == a],
                                               dict(t='town', room=room.id, ev=[dict(k='out', pid=b)]))

    async def on_close(self, conn):
        rid = conn.ext.pop('town', None)
        if not rid:
            return
        room = self.hub.rooms.get(rid)
        if room is not None and not any(c.player is conn.player for c in room.conns):
            self._remove(room, conn.player.pid)
        if conn.player.ext.get('town') == rid:
            conn.player.ext.pop('town', None)

    def stats(self):
        rooms = self.hub.rooms_with_prefix(PREFIX)
        return dict(town_rooms=len(rooms), town_walkers=sum(len(r.data['people']) for r in rooms), town_flushes=self.flushes)
