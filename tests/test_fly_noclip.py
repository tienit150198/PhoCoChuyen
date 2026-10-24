"""🪽 Owner 24/10 "bay bị mắc nhà, đi khó chịu quá, sửa lại đi bay cứ vướng vướng": in the air nothing on the ground is in
the way. The live service accepts a flyer's position over a house, a tree or the water (inside the map's bounds, within the
FLY_FAST budget), still refuses it on foot, and landing over something solid puts the walker on the nearest walkable point
(live/town.py land, live/street.py Geo.route from a point off the walkable ground). tests/fly-noclip.mjs: the clients.
No database: the wing cache is filled as if live/wings.py had just read it."""
import json
import math
import shutil
import subprocess
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from live import wings
from live.config import Config
from live.hub import Conn, Hub
from live.protocol import LiveError
from live.street import GEO, StreetFeature
from live.town import (BOUNDS, MAP_ID, OBSTACLES, TownFeature, budget, clean_point, land, nearest_walkable,
                       walkable)
from live.wings import WingFeature

ROOT = Path(__file__).resolve().parents[1]
HOUSE = (1, 1, 5.2, 5.2)          # game/town_layout.json: the lot next to the spawn point (6, 6)
ROOF = (3.1, 3.1)                 # its middle


def wear(app, pid, k='rong', r=4):
    wings.of_app(app).rows.put(pid, (time.monotonic(), dict(k=k, r=r) if r is not None else None))


class Geometry(unittest.TestCase):
    def test_the_house_is_solid_and_the_spawn_open(self):
        self.assertIn(HOUSE, OBSTACLES)
        self.assertFalse(walkable(*ROOF))
        self.assertTrue(walkable(6, 6))

    def test_clean_point_on_foot_and_in_the_air(self):
        with self.assertRaises(LiveError):
            clean_point(*ROOF)
        self.assertEqual(clean_point(*ROOF, fly=True), ROOF)
        self.assertEqual(clean_point(BOUNDS[0] + .5, BOUNDS[1] + .5, fly=True), (BOUNDS[0] + .5, BOUNDS[1] + .5),
                         'over the water, still on the map')
        for x, y in ((BOUNDS[2] + 1, 6), (6, BOUNDS[1] - .5), (math.nan, 6)):
            with self.assertRaises(LiveError):
                clean_point(x, y, fly=True)

    def test_nearest_walkable_from_every_obstacle(self):
        for o in OBSTACLES:
            x, y = (o[0] + o[2]) / 2, (o[1] + o[3]) / 2
            if walkable(x, y):
                continue
            p = nearest_walkable(x, y) or nearest_walkable(x, y, reach=math.inf)
            self.assertIsNotNone(p, o)
            self.assertTrue(walkable(*p), (o, p))
        self.assertEqual(nearest_walkable(6, 6), (6, 6))

    def test_land_moves_only_when_over_something_solid(self):
        w = SimpleNamespace(x=6.0, y=6.0)
        self.assertFalse(land(w))
        self.assertEqual((w.x, w.y), (6.0, 6.0))
        w = SimpleNamespace(x=ROOF[0], y=ROOF[1])
        self.assertTrue(land(w))
        self.assertTrue(walkable(w.x, w.y))
        self.assertAlmostEqual(math.hypot(w.x - ROOF[0], w.y - ROOF[1]), 5.2 - 3.1 + .15, delta=.02,
                               msg='the nearest side of the house, just clear of it')


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

    async def join(self, conn, x=6, y=6, **extra):
        return await self.town.town_in(conn, dict(map=MAP_ID, x=x, y=y, direction='se', look={}, **extra))

    def me(self, conn):
        return self.hub.rooms[conn.ext['town']].data['people'][conn.player.pid]

    async def mv(self, conn, x, y, **f):
        w = self.me(conn)
        w.credit, w.last = 0.0, time.monotonic() - 1   # one second of budget
        await self.town.town_mv(conn, dict(x=x, y=y, direction='nw', **f))
        return w

    def seen(self, conn, pid):
        room = self.hub.rooms[conn.ext['town']]
        if room.data['h']:
            room.data['h'].cancel()
        self.town._flush(room)
        out = [e for f in self.frames[conn.ws] if f['t'] == 'town' for e in f.get('ev', [])
               if e['k'] == 'mv' and e.get('pid') == pid]
        self.frames[conn.ws].clear()
        return out

    async def test_a_flyer_over_a_house_is_accepted_a_walker_is_not(self):
        a, b = self.player('a'), self.player('b')
        wear(self.app, a.player.pid, r=3)
        await self.join(a, fl=True)
        await self.join(b)
        w = await self.mv(a, *ROOF)
        self.assertEqual((w.x, w.y, w.fl), (*ROOF, 3), 'over the roof')
        with self.assertRaises(LiveError) as e:
            await self.mv(b, *ROOF)
        self.assertEqual(e.exception.code, 'bad')
        self.assertEqual((self.me(b).x, self.me(b).y), (6, 6), 'on foot: still outside the house')
        moves = self.seen(b, a.player.pid)
        self.assertEqual((moves[-1]['x'], moves[-1]['y']), ROOF, 'the others see the flyer over the roof')

    async def test_the_air_still_has_bounds_and_a_speed_limit(self):
        a = self.player('a')
        wear(self.app, a.player.pid, r=7)
        await self.join(a, fl=True)
        with self.assertRaises(LiveError):
            await self.mv(a, BOUNDS[2] + 3, 6)   # off the map
        far = budget(7) + 2                      # more than a second of the fastest wings
        with self.assertRaises(LiveError) as e:
            await self.mv(a, 6 + far, 6)
        self.assertEqual(e.exception.code, 'speed')
        self.assertEqual((self.me(a).x, self.me(a).y), (6, 6))

    async def test_landing_over_a_house_snaps_to_open_ground(self):
        a, b = self.player('a'), self.player('b')
        wear(self.app, a.player.pid, r=2)
        await self.join(a, fl=True)
        await self.join(b)
        await self.mv(a, *ROOF)
        self.seen(b, a.player.pid)
        w = await self.mv(a, *ROOF, fl=False)   # Hạ cánh over the roof
        self.assertIsNone(w.fl)
        self.assertTrue(walkable(w.x, w.y), (w.x, w.y))
        self.assertLess(math.hypot(w.x - ROOF[0], w.y - ROOF[1]), 2.5)
        last = self.seen(b, a.player.pid)[-1]
        self.assertEqual((last['x'], last['y'], last['fl']), (w.x, w.y, None), 'the others see them land beside it')
        with self.assertRaises(LiveError):
            await self.mv(a, *ROOF)   # on foot now: the house is solid again

    async def test_a_road_vehicle_or_an_activity_lands_too(self):
        a = self.player('a')
        wear(self.app, a.player.pid, r=2)
        await self.join(a, fl=True)
        await self.mv(a, *ROOF)
        w = await self.mv(a, *ROOF, r={'v': 'xe_ga', 'c': 'hong'})
        self.assertIsNone(w.fl)
        self.assertTrue(walkable(w.x, w.y))
        await self.mv(a, w.x, w.y, fl=True)
        await self.mv(a, *ROOF)
        w = await self.mv(a, *ROOF, activity=dict(kind='fishing', x=84, y=180, direction='ne', phase='walk', action=None,
                                                   moving=False))
        self.assertIsNone(w.fl)
        self.assertTrue(walkable(w.x, w.y))

    async def test_joining_in_the_air_over_a_house(self):
        a, b = self.player('a'), self.player('b')
        wear(self.app, a.player.pid, r=4)
        snap = await self.join(a, *ROOF, fl=True)
        self.assertEqual((self.me(a).x, self.me(a).y, self.me(a).fl), (*ROOF, 4))
        self.assertNotIn('snap', snap)
        snap = await self.join(b, *ROOF, fl=True)   # no wings: on foot, put beside the house, told where
        self.assertIsNone(self.me(b).fl)
        self.assertTrue(walkable(self.me(b).x, self.me(b).y))
        self.assertEqual((snap['x'], snap['y'], snap['snap']), (self.me(b).x, self.me(b).y, True))
        with self.assertRaises(LiveError):
            await self.join(self.player('c'), *ROOF)   # on foot over a house: refused as before

    async def test_wings_taken_off_over_a_house_land_beside_it(self):
        a = self.player('a')
        wear(self.app, a.player.pid, r=5)
        await self.join(a, fl=True)
        await self.mv(a, *ROOF)
        feature = WingFeature(self.app)
        wings.of_app(self.app).forget = lambda pid: None
        wear(self.app, a.player.pid, r=None)
        await feature.on_notify(dict(op='wing', pids=[a.player.pid]))
        w = self.me(a)
        self.assertIsNone(w.fl)
        self.assertTrue(walkable(w.x, w.y))
        last = self.seen(a, a.player.pid)[-1]
        self.assertEqual((last['x'], last['y'], last['fl']), (w.x, w.y, None))


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
    """Công viên: walkable x 20..300 everywhere, x 300..580 only below y 400 (the lake above)."""
    LAKE = (450.0, 200.0)

    async def asyncSetUp(self):
        self.cfg = Config(street=True)
        self.hub = Hub(self.cfg)
        self.hub.write = lambda sockets, raw, **kw: None
        self.app = SimpleNamespace(cfg=self.cfg, hub=self.hub, db=FakeDb(), chat=None, by_name={})
        self.street = StreetFeature(self.app)
        self.app.by_name['street'] = self.street
        self.g = GEO['congvien']

    async def asyncTearDown(self):
        for room in list(self.hub.rooms.values()):
            self.street._empty(room)

    def player(self, pid):
        pid = (pid * 16)[:16]
        ident = SimpleNamespace(pid=pid, sid='s-' + pid, name='Tên ' + pid, av='🌸', account=False,
                                muted_until=0, old=True, since=0, online=True)
        c = Conn(object(), self.hub.player(ident), 'test', self.cfg)
        c.ready = True
        self.hub.add(c)
        return c

    async def walker(self, fly):
        a = self.player('f' if fly else 'w')
        wear(self.app, a.player.pid, r=3)
        await self.street.walk_in(a, dict(place='congvien', look={}, g='f', fl=fly))
        room, w = self.street._me(a)
        w.path, w.t0 = [[150.0, 300.0], [150.0, 300.0]], time.time() - 60   # standing on the path by the lake
        return a, room, w

    def assertWalkable(self, path):
        g = self.g
        for a, b in zip(path, path[1:]):
            self.assertTrue(g.seg_ok(a, b), (a, b, path))

    def test_the_lake_is_not_walkable(self):
        self.assertFalse(self.g.inside(*self.LAKE))
        self.assertEqual(self.g.air((150, 300), self.LAKE), [[150.0, 300.0], list(self.LAKE)])
        self.assertEqual(self.g.air((150, 300), (900, -40)), [[150.0, 300.0], [600.0, 0.0]], 'kept in the place')

    async def test_a_flyer_goes_straight_over_the_lake(self):
        a, room, w = await self.walker(True)
        self.assertEqual(w.fl, 3)
        await self.street.move(a, dict(x=self.LAKE[0], y=self.LAKE[1]))
        self.assertEqual(len(w.path), 2, 'a straight line')
        self.assertEqual(w.path[-1], list(self.LAKE), 'over the water')

    async def test_a_walker_goes_round(self):
        a, room, w = await self.walker(False)
        self.assertIsNone(w.fl)
        await self.street.move(a, dict(x=self.LAKE[0], y=self.LAKE[1]))
        self.assertTrue(self.g.inside(*w.path[-1]), 'clamped to the shore')
        self.assertWalkable(w.path)

    async def test_landing_over_the_lake_comes_ashore_first(self):
        a, room, w = await self.walker(True)
        w.path, w.t0 = [list(self.LAKE), list(self.LAKE)], time.time() - 60   # hovering over the water
        await self.street.fly(a, dict(on=False))
        self.assertIsNone(w.fl)
        self.assertEqual(w.path[0], list(self.LAKE), 'from where they are')
        self.assertTrue(self.g.inside(*w.path[1]), 'the nearest shore first')
        self.assertEqual(tuple(w.path[1]), self.g.clamp(*self.LAKE))
        self.assertWalkable(w.path[1:])
        # moving on afterwards goes round on foot
        w.t0 = time.time() - 60
        await self.street.move(a, dict(x=150, y=200))
        self.assertWalkable(w.path)

    async def test_taking_off_keeps_going_straight(self):
        a, room, w = await self.walker(False)
        await self.street.fly(a, dict(on=False))
        await self.street.move(a, dict(x=500, y=600))
        await self.street.fly(a, dict(on=True))
        self.assertEqual(w.fl, 3)
        self.assertEqual(len(w.path), 2)


class Client(unittest.TestCase):
    def test_node_movement_helpers(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, '--test', str(ROOT / 'tests' / 'fly-noclip.mjs')], cwd=ROOT, capture_output=True,
                             text=True, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
