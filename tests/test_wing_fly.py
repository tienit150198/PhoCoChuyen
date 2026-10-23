"""🪽 Bay (owner 24/10 "bay được k nhỉ, sẽ có tăng tốc độ như xe ấy, nếu sử dụng cánh thì k lái xe được"): a player wearing
wings flies on the walk maps, faster by the tier (game/wings_content.py FLY_FAST, the vehicles' scale of
public/js/v4/ride.js FAST), never while riding. The server keeps it: only wings it read itself (live/wings.py), never on
a vehicle (taking off sends it home, riding lands), never where vehicles are not (a café, a wedding, a site, an activity).
No database: the wing cache is filled as if live/wings.py had just read it."""
import json
import re
import shutil
import subprocess
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from game.wings_content import FLY_FAST, TIERS
from live import wings
from live.config import Config
from live.hub import Conn, Hub
from live.protocol import LiveError
from live.street import GEO, SPEED as STREET_SPEED, RIDE_FAST, StreetFeature
from live.town import MAP_ID, RIDE_MAX, SPEED as TOWN_SPEED, TownFeature, budget, road
from live.wings import WingFeature

ROOT = Path(__file__).resolve().parents[1]
HT = len(TIERS) - 1


def wear(app, pid, k='rong', r=4):
    """As if live/wings.py had just read the wing this player wears (None: none)."""
    wings.of_app(app).rows.put(pid, (time.monotonic(), dict(k=k, r=r) if r is not None else None))


class Speeds(unittest.TestCase):
    def test_one_table_for_server_and_client(self):
        src = (ROOT / 'public/js/v4/wings-art.js').read_text(encoding='utf-8')
        js = [float(x) for x in re.search(r'export const WING_FLY_FAST=Object\.freeze\(\[([^\]]*)\]\)', src).group(1).split(',')]
        self.assertEqual(tuple(js), FLY_FAST)
        self.assertEqual(len(FLY_FAST), len(TIERS))

    def test_faster_by_tier_on_the_vehicles_scale(self):
        self.assertEqual(list(FLY_FAST), sorted(set(FLY_FAST)), 'each tier faster than the one below')
        src = (ROOT / 'public/js/v4/ride.js').read_text(encoding='utf-8')
        fast = {k: float(v) for k, v in re.findall(r"(\w+):([\d.]+)", re.search(r'export const FAST=\{([^}]*)\}', src).group(1))}
        self.assertEqual(FLY_FAST[0], fast['bicycle'], 'D: a bicycle')
        self.assertEqual(FLY_FAST[4], fast['scooter'], 'S: a motorbike')
        self.assertEqual(FLY_FAST[HT], max(fast.values()), 'Huyền thoại: the fastest car')
        self.assertGreater(FLY_FAST[0], 1)

    def test_town_budget_grows_past_the_fastest_ride(self):
        self.assertEqual(budget(None), TOWN_SPEED)
        for r, f in enumerate(FLY_FAST):
            self.assertEqual(budget(r), TOWN_SPEED * max(1.0, f / RIDE_MAX))
        self.assertGreater(budget(HT), budget(None))
        self.assertTrue(road({'v': 'xe_ga'}) and road({'v': 'o_to_suv'}))
        self.assertFalse(road(None) or road({'v': 'du_thuyen'}) or road({'v': 'nope'}))


class Client(unittest.TestCase):
    def test_art_speed_and_toggles(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'wing-fly.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


class Town(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cfg = Config(town=True)
        self.hub = Hub(self.cfg)
        self.frames = {}
        self.hub.write = lambda sockets, raw, **kw: [self.frames[s].append(json.loads(raw)) for s in sockets]
        self.app = SimpleNamespace(cfg=self.cfg, hub=self.hub, db=None, chat=None, by_name={})
        self.town = TownFeature(self.app)
        self.app.by_name['town'] = self.town

    async def asyncTearDown(self):
        for room in list(self.hub.rooms.values()):
            self.town._empty(room)

    def player(self, pid):
        pid = (pid * 16)[:16]
        ident = SimpleNamespace(pid=pid, sid='private-' + pid, name='Tên ' + pid, av='🌸', account=False,
                                muted_until=0, old=True, since=0, online=True)
        ws = object()
        self.frames[ws] = []
        c = Conn(ws, self.hub.player(ident), 'test', self.cfg)
        c.ready = True
        self.hub.add(c)
        return c

    async def join(self, conn, **extra):
        return await self.town.town_in(conn, dict(map=MAP_ID, x=6, y=6, direction='se', look={}, **extra))

    def me(self, conn):
        return self.hub.rooms[conn.ext['town']].data['people'][conn.player.pid]

    async def mv(self, conn, **f):
        w = self.me(conn)
        w.last -= 1
        await self.town.town_mv(conn, dict(x=w.x, y=w.y + .1, direction='se', **f))
        return w

    async def test_flag_and_only_with_wings(self):
        self.assertTrue(self.cfg.flags_extra.get('fly'))
        a, b = self.player('a'), self.player('b')
        wear(self.app, a.player.pid, r=6)
        await self.join(a, fl=True)
        snap = await self.join(b, fl=True)   # no wings: on foot
        people = {p['pid']: p for p in snap['people']}
        self.assertEqual(people[a.player.pid]['fl'], 6)
        self.assertIsNone(self.me(b).fl)
        self.assertNotIn('fl', self.me(b).public())

    async def test_take_off_sends_a_road_vehicle_home_and_riding_lands(self):
        a = self.player('a')
        wear(self.app, a.player.pid, r=2)
        await self.join(a, fl=True, r={'v': 'xe_ga', 'c': 'hong'})
        w = self.me(a)
        self.assertEqual((w.fl, w.ride), (2, None), 'arriving in flight: the scooter stays home')
        await self.mv(a, r={'v': 'xe_ga', 'c': 'hong'})   # riding (no `fl`): landed
        self.assertEqual((w.fl, w.ride['v']), (None, 'xe_ga'))
        await self.mv(a, fl=True)   # taking off: the vehicle goes home
        self.assertEqual((w.fl, w.ride), (2, None))
        await self.mv(a, fl=True, r={'v': 'o_to_suv', 'c': 'bac'})   # both asked: flying wins, never both
        self.assertEqual((w.fl, w.ride), (2, None))
        await self.mv(a)   # nothing said: still flying
        self.assertEqual(w.fl, 2)
        await self.mv(a, fl=False)
        self.assertIsNone(w.fl)
        room = self.hub.rooms[a.ext['town']]
        if room.data['h']:
            room.data['h'].cancel()
        self.town._flush(room)
        moves = [e for f in self.frames[a.ws] if f['t'] == 'town' for e in f.get('ev', []) if e['k'] == 'mv']
        self.assertIsNone(moves[-1]['fl'])

    async def test_a_yacht_waits_at_its_harbour_while_flying(self):
        a = self.player('a')
        wear(self.app, a.player.pid, r=1)
        await self.join(a, r={'v': 'du_thuyen'})
        await self.mv(a, fl=True)
        w = self.me(a)
        self.assertEqual(w.fl, 1)
        self.assertEqual((w.ride or {}).get('v'), 'du_thuyen')

    async def test_an_activity_lands(self):
        a = self.player('a')
        wear(self.app, a.player.pid, r=3)
        await self.join(a, fl=True)
        w = await self.mv(a, fl=True, activity=dict(kind='fishing', x=84, y=180, direction='ne', phase='walk', action=None, moving=False))
        self.assertIsNone(w.fl)

    async def test_a_flyer_covers_more_ground(self):
        a, b = self.player('a'), self.player('b')
        wear(self.app, a.player.pid, r=HT)
        await self.join(a, fl=True)
        await self.join(b)
        far = TOWN_SPEED * 1.15   # one second: more than a walker may, less than a Huyền thoại flyer may
        self.assertLess(far, budget(HT))
        for c in (a, b):
            w = self.me(c)
            w.credit, w.last = 0.0, time.monotonic() - 1
        await self.town.town_mv(a, dict(x=6 + far, y=6, direction='se'))
        self.assertAlmostEqual(self.me(a).x, 6 + far, places=2)
        with self.assertRaises(LiveError):
            await self.town.town_mv(b, dict(x=6 + far, y=6, direction='se'))

    async def test_wings_taken_off_land(self):
        a = self.player('a')
        wear(self.app, a.player.pid, r=5)
        await self.join(a, fl=True)
        feature = WingFeature(self.app)
        cache = wings.of_app(self.app)
        cache.forget = lambda pid: None   # no database here: keep the rows filled below
        wear(self.app, a.player.pid, r=7)   # forged up: the new tier's speed
        await feature.on_notify(dict(op='wing', pids=[a.player.pid]))
        self.assertEqual(self.me(a).fl, 7)
        wear(self.app, a.player.pid, r=None)   # taken off: landed
        await feature.on_notify(dict(op='wing', pids=[a.player.pid]))
        self.assertIsNone(self.me(a).fl)
        self.assertIsNone(self.me(a).wg)


class FakeDb:
    async def fetch(self, *a, **k):
        return []

    async def fetchrow(self, *a, **k):
        return None

    async def fetchval(self, *a, **k):
        return None

    async def execute(self, *a, **k):
        return None


class Street(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cfg = Config(street=True)
        self.hub = Hub(self.cfg)
        self.frames = {}
        self.hub.write = lambda sockets, raw, **kw: [self.frames[s].append(json.loads(raw)) for s in sockets]
        self.app = SimpleNamespace(cfg=self.cfg, hub=self.hub, db=FakeDb(), chat=None, by_name={})
        self.street = StreetFeature(self.app)
        self.app.by_name['street'] = self.street

    async def asyncTearDown(self):
        for room in list(self.hub.rooms.values()):
            self.street._empty(room)

    def player(self, pid):
        pid = (pid * 16)[:16]
        ident = SimpleNamespace(pid=pid, sid='s-' + pid, name='Tên ' + pid, av='🌸', account=False,
                                muted_until=0, old=True, since=0, online=True)
        ws = object()
        self.frames[ws] = []
        c = Conn(ws, self.hub.player(ident), 'test', self.cfg)
        c.ready = True
        self.hub.add(c)
        return c

    async def join(self, conn, **extra):
        return await self.street.walk_in(conn, dict(place='congvien', look={}, g='f', **extra))

    def me(self, conn):
        return self.street._me(conn)

    def rd(self, room):
        return [e for _, e in room.data['ev'] if e.get('k') == 'rd']

    async def test_flying_is_faster_by_tier_and_never_riding(self):
        self.assertTrue(self.cfg.flags_extra.get('fly'))
        a = self.player('a')
        wear(self.app, a.player.pid, r=4)
        snap = await self.join(a, fl=True, r={'v': 'xe_ga', 'c': 'hong'})
        room, w = self.me(a)
        self.assertEqual((w.fl, w.ride), (4, None), 'arriving in flight: the scooter stays home')
        self.assertEqual(w.speed, STREET_SPEED * FLY_FAST[4])
        mine = [p for p in snap['people'] if p['pid'] == a.player.pid] if 'people' in snap else []
        for p in mine:
            self.assertEqual((p['fl'], p['v']), (4, w.speed))
        await self.street.ride(a, dict(r={'v': 'xe_ga', 'c': 'hong'}))   # riding lands
        self.assertEqual((w.fl, w.ride['v']), (None, 'xe_ga'))
        self.assertEqual(w.speed, STREET_SPEED * RIDE_FAST)
        self.assertIsNone(self.rd(room)[-1]['fl'])
        await self.street.fly(a, dict(on=True))   # taking off: the vehicle goes home
        self.assertEqual((w.fl, w.ride), (4, None))
        last = self.rd(room)[-1]
        self.assertEqual((last['fl'], last['r'], last['v']), (4, None, STREET_SPEED * FLY_FAST[4]))
        n = len(self.rd(room))
        await self.street.fly(a, dict(on=True))   # already up: no news
        self.assertEqual(len(self.rd(room)), n)
        await self.street.fly(a, dict(on=False))
        self.assertIsNone(w.fl)
        self.assertEqual(w.speed, STREET_SPEED)
        self.assertIsNone(self.rd(room)[-1]['fl'])
        self.assertNotIn('fl', w.public())

    async def test_no_wings_no_flight(self):
        a = self.player('a')
        await self.join(a, fl=True)
        room, w = self.me(a)
        self.assertIsNone(w.fl)
        with self.assertRaises(LiveError) as e:
            await self.street.fly(a, dict(on=True))
        self.assertEqual(e.exception.code, 'no_fly')

    async def test_on_foot_where_vehicles_are_not(self):
        self.assertTrue(GEO['cafe'].private and GEO['wedding'].private)
        a = self.player('a')
        wear(self.app, a.player.pid, r=2)
        await self.join(a)
        room, w = self.me(a)
        cafe = self.street._new_room('walk:cafe:t1', 'cafe')
        room.data['people'].pop(w.pid)
        cafe.data['people'][w.pid] = w
        a.ext['walk'] = cafe.id
        with self.assertRaises(LiveError):
            await self.street.fly(a, dict(on=True))
        self.assertIsNone(w.fl)

    async def test_a_new_tier_changes_the_speed_and_wings_off_land(self):
        a = self.player('a')
        wear(self.app, a.player.pid, r=1)
        await self.join(a, fl=True)
        room, w = self.me(a)
        now = time.time()
        self.assertTrue(self.street._set_fly(room, w, HT, now))
        self.assertEqual(w.speed, STREET_SPEED * FLY_FAST[HT])
        self.assertTrue(self.street._set_fly(room, w, None, now))
        self.assertEqual(w.speed, STREET_SPEED)
        self.assertFalse(self.street._set_fly(room, w, None, now))
