"""🛵 Đi xe quanh phố (public/js/v4/ride.js): a player who owns a road vehicle rides it on the town walk, the fair and
the strolls. The choice itself (owned, not broken, the garage's main one first, the toggle remembered) is checked with
node (tests/ride.mjs). Here: the lists stay in step with game/garage.py, the live presence (`r`, optional) is cleaned
and never refused, and old clients (no `r`) get exactly the frames they always did. Riding costs nothing and never
touches the save: no game file changes, no new action."""
import asyncio
import re
import shutil
import subprocess
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from live.fair import Goer
from live.street import GEO, RIDE_FAST, RIDES, SPEED, Walker, clean_ride, pos_at
from tests.live_support import HAVE_WS, LiveCase

ROOT = Path(__file__).resolve().parents[1]
LOOK = dict(hair='toc_bob', shade='mau_hong', skin='da_trung', top='ao_hoodie', bottom='quan_jean', shoes='giay_trang', acc='kinh_tron')


class Lists(unittest.TestCase):
    def test_two_wheelers_are_the_garage_bikes(self):
        from game.garage import VEHICLES
        self.assertEqual(RIDES, {k for k, v in VEHICLES.items() if v['group'] == 'bike'})

    def test_every_road_vehicle_has_a_drawing(self):
        from game.garage import VEHICLES
        src = (ROOT / 'public/js/v4/ride.js').read_text(encoding='utf-8')
        kinds = dict(re.findall(r"(\w+):'(\w+)'", re.search(r'export const KINDS=\{([^}]*)\}', src).group(1)))
        road = {k for k, v in VEHICLES.items() if v['group'] in ('bike', 'car')}
        self.assertEqual(set(kinds), road, 'a new road vehicle needs its look in ride.js (KINDS, ART)')
        two = set(re.findall(r"'(\w+)'", re.search(r'export const TWO=new Set\(\[([^\]]*)\]\)', src).group(1)))
        self.assertEqual({k for k, v in kinds.items() if v in two}, set(RIDES), 'the fair and the strolls: two wheels')
        for kind in set(kinds.values()):
            self.assertRegex(src, rf'\n  {kind}:\{{', kind)

    def test_no_cost_and_no_save_change(self):
        src = (ROOT / 'public/js/v4/ride.js').read_text(encoding='utf-8')
        self.assertNotIn('api.act', src)
        self.assertNotRegex(src, r"\bfetch\(|/api/")
        for f in ('town-walk.js', 'fair-walk.js', 'walk.js'):
            self.assertIn("from './ride.js'", (ROOT / 'public/js/v4' / f).read_text(encoding='utf-8'), f)

    def test_words_have_english(self):
        import json
        en = json.loads((ROOT / 'public/i18n/en.json').read_text(encoding='utf-8'))
        strings = en.get('strings', en)
        for vi in ('🚶 Đi bộ', 'Đi bộ', 'Mua xe để chạy quanh phố', '🛵 Đi xe', '🚗 Đi xe'):
            self.assertIn(vi, strings, vi)


class Presence(unittest.TestCase):
    def test_clean_ride(self):
        self.assertEqual(clean_ride({'v': 'xe_ga', 'c': 'hong'}), {'v': 'xe_ga', 'c': 'hong'})
        self.assertEqual(clean_ride({'v': 'xe_dap'}), {'v': 'xe_dap', 'c': ''})
        self.assertEqual(clean_ride({'v': 'xe_so', 'c': '../x'}), {'v': 'xe_so', 'c': ''})
        self.assertEqual(clean_ride({'v': 'xe_so', 'c': 'x' * 40}), {'v': 'xe_so', 'c': ''})
        self.assertEqual(clean_ride({'v': 'xe_ga', 'c': 'hong', 'plate': 'MÂY 01', 'big': 'x' * 999}), {'v': 'xe_ga', 'c': 'hong'})
        for odd in (None, '', 'xe_ga', 5, [], {}, {'v': 'o_to_suv'}, {'v': 'du_thuyen'}, {'v': 'XE_GA'}, {'v': ['xe_ga']},
                    {'v': None}, {'v': '__proto__'}, True):
            self.assertIsNone(clean_ride(odd), odd)

    def test_walker_speed_and_public(self):
        pl = SimpleNamespace(pid='p1', name='Lan')
        w = Walker(pl, LOOK, 'female', None, (100.0, 100.0), 10.0)
        self.assertEqual(w.speed, SPEED)
        self.assertNotIn('r', w.public())
        self.assertNotIn('v', w.public())
        w.ride = {'v': 'xe_ga', 'c': 'hong'}
        self.assertEqual(w.speed, SPEED * RIDE_FAST)
        self.assertEqual((w.public()['r'], w.public()['v']), ({'v': 'xe_ga', 'c': 'hong'}, SPEED * RIDE_FAST))
        w.path, w.t0 = [[0, 0], [1000, 0]], 10.0
        self.assertEqual(w.at(11.0), (SPEED * RIDE_FAST, 0.0))
        self.assertEqual(pos_at([[0, 0], [1000, 0]], 10.0, 11.0), (SPEED, 0.0))

    def test_fair_goer_public(self):
        pl = SimpleNamespace(pid='p1', name='Lan')
        self.assertNotIn('r', Goer(pl, LOOK, 'female', [0.2, 0.9]).public())
        self.assertEqual(Goer(pl, LOOK, 'female', [0.2, 0.9], None, {'v': 'xe_dap', 'c': ''}).public()['r'], {'v': 'xe_dap', 'c': ''})


class Client(unittest.TestCase):
    def test_choice_toggle_and_drawing(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'ride.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


class LiveRide(LiveCase):
    cfg_extra = dict(street=True, fair=True)

    @staticmethod
    async def ev(c, t, k, timeout=3.0, **match):
        end = time.monotonic() + timeout
        while True:
            for f in c.frames:
                if f.get('t') == t:
                    for e in f['ev']:
                        if e.get('k') == k and all(e.get(x) == v for x, v in match.items()):
                            f['ev'].remove(e)
                            return e
            if time.monotonic() > end:
                raise AssertionError(f'no {k} {match} in {[f for f in c.frames if f.get("t") == t]}')
            await asyncio.sleep(0.02)

    def walker(self, rid, pid):
        return self.app.hub.rooms.get(rid).data['people'][pid]


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Strolls(LiveRide):
    async def stroll(self, name, **extra):
        c = await self.connect(self.account(name)[0])
        c.room = await c.call('walk_in', 'walk_room', place='boho', look=LOOK, g='female', title=None, **extra)
        c.pid = c.welcome['me']['pid']
        return c

    async def test_riding_in_and_seen_by_others(self):
        a = await self.stroll('Lan Anh', r={'v': 'xe_ga', 'c': 'hong'})
        me = a.room['people'][0]
        self.assertEqual((me['r'], me['v']), ({'v': 'xe_ga', 'c': 'hong'}, SPEED * RIDE_FAST))
        b = await self.stroll('Minh Tú')                          # on foot: the same entry as before riding existed
        them = {p['pid']: p for p in b.room['people']}
        self.assertEqual(them[a.pid]['r'], {'v': 'xe_ga', 'c': 'hong'})
        self.assertNotIn('r', them[b.pid])
        self.assertNotIn('v', them[b.pid])
        came = await self.ev(a, 'walk', 'in', pid=b.pid)
        self.assertNotIn('r', came)

    async def test_ride_frame_on_and_off(self):
        a = await self.stroll('Lan Anh')
        b = await self.stroll('Minh Tú')
        await self.ev(a, 'walk', 'in', pid=b.pid)
        rid = a.room['room']
        await a.send(t='move', x=500, y=600)
        await self.ev(b, 'walk', 'mv', pid=a.pid)
        await a.send(t='ride', r={'v': 'xe_dap', 'c': 'xanh_la'})
        rd = await self.ev(b, 'walk', 'rd', pid=a.pid)
        self.assertEqual((rd['r'], rd['v']), ({'v': 'xe_dap', 'c': 'xanh_la'}, SPEED * RIDE_FAST))
        self.assertEqual(rd['p'][-1], self.walker(rid, a.pid).path[-1])
        self.assertTrue(GEO['boho'].inside(*rd['p'][0]))
        await a.send(t='ride', r={'v': 'xe_dap', 'c': 'xanh_la'})    # the same again: nothing to tell
        await asyncio.sleep(0.3)
        self.assertFalse([e for f in b.frames if f.get('t') == 'walk' for e in f['ev'] if e.get('k') == 'rd'])
        await a.send(t='ride', r=None)                                 # on foot again
        rd = await self.ev(b, 'walk', 'rd', pid=a.pid)
        self.assertEqual((rd['r'], rd['v']), (None, SPEED))
        self.assertIsNone(self.walker(rid, a.pid).ride)

    async def test_odd_rides_are_on_foot_never_an_error(self):
        a = await self.stroll('Lan Anh', r={'v': 'o_to_suv', 'c': 'bac'})   # a car stays outside
        self.assertNotIn('r', a.room['people'][0])
        b = await self.stroll('Minh Tú', r='xe_ga')
        self.assertNotIn('r', [p for p in b.room['people'] if p['pid'] == b.pid][0])
        for odd in ({'v': 'sieu_xe'}, {'v': 5}, {'v': ['xe_ga']}, 'x', [1]):
            await a.send(t='ride', r=odd)
        await asyncio.sleep(0.3)
        self.assertFalse([f for f in a.frames if f.get('t') == 'error'])
        self.assertIsNone(self.walker(a.room['room'], a.pid).ride)
        await a.send(t='ride', r={'v': 'xe_ga', 'c': {'a': 1}})       # an odd paint: the vehicle in its own colour
        await asyncio.sleep(0.2)
        self.assertEqual(self.walker(a.room['room'], a.pid).ride, {'v': 'xe_ga', 'c': ''})


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Fair(LiveRide):
    async def goer(self, name, **extra):
        c = await self.connect(self.guest(name)[0])
        c.room = await c.call('fair_in', 'fair_room', look=LOOK, g='female', x=0.2, y=0.9, **extra)
        c.pid = c.welcome['me']['pid']
        return c

    async def test_riding_travels_with_walks_and_snapshots(self):
        a = await self.goer('Lan Anh', r={'v': 'xe_ga', 'c': 'hong'})
        b = await self.goer('Minh Tú')
        self.assertEqual([p['r'] for p in b.room['people']], [{'v': 'xe_ga', 'c': 'hong'}])
        came = await self.ev(a, 'fair', 'in', pid=b.pid)   # on foot: the same entry as before
        self.assertNotIn('r', came)
        await a.send(t='fair_mv', p=[[0.2, 0.9], [0.5, 0.5]], ms=400, r={'v': 'xe_ga', 'c': 'hong'})
        self.assertEqual((await self.ev(b, 'fair', 'mv', pid=a.pid))['r'], {'v': 'xe_ga', 'c': 'hong'})
        await asyncio.sleep(0.3)
        await a.send(t='fair_mv', p=[[0.5, 0.5], [0.6, 0.5]], ms=200)    # off the vehicle: no `r`
        self.assertNotIn('r', await self.ev(b, 'fair', 'mv', pid=a.pid))
        await asyncio.sleep(0.3)
        await a.send(t='fair_mv', p=[[0.6, 0.5], [0.6, 0.6]], ms=200, r={'v': 'mui_tran'})   # a car: on foot
        self.assertNotIn('r', await self.ev(b, 'fair', 'mv', pid=a.pid))
        self.assertFalse([f for f in a.frames if f.get('t') == 'error'])


if __name__ == '__main__':
    unittest.main()
