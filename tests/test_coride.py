"""💑 Vợ chồng chung xe (live/coride.py, owner feedback #136): a married couple share their vehicles on the strolls and
at the fair. First come drives (the other is told, never both), only the spouse may ride your vehicle or sit behind
you, the passenger goes where the driver goes and gets off safely when the driver gets off, sits, plays a stall,
leaves or drops. Older clients send none of it and see the same frames as before (plus keys they ignore).
The game side: GET /api/garage/spouse (game/couple.py spouse_cars) lists the spouse's vehicles, read-only."""
import asyncio
import time
import unittest
from unittest import mock

from live.street import RIDE_FAST, SPEED, clean_ride
from tests.live_support import HAVE_WS, LiveCase

LOOK = dict(hair='toc_bob', shade='mau_hong', skin='da_trung', top='ao_hoodie', bottom='quan_jean', shoes='giay_trang', acc='kinh_tron')
SCOOTER = {'v': 'xe_ga', 'c': 'hong'}


class Wire(unittest.TestCase):
    def test_owner_is_kept_only_when_it_is_a_pid(self):
        self.assertEqual(clean_ride({'v': 'xe_ga', 'c': 'hong', 'o': '0123456789abcdef'}), {'v': 'xe_ga', 'c': 'hong', 'o': '0123456789abcdef'})
        for odd in ('x', 5, None, '0123456789ABCDEF', '0123456789abcdef0', ['a'], {'a': 1}):
            self.assertEqual(clean_ride({'v': 'xe_ga', 'c': 'hong', 'o': odd}), SCOOTER, odd)


def marry(store, a: str, b: str, status: str = 'married') -> None:
    def go(db):
        cur = db.execute("INSERT INTO couples(a, b, status, since) VALUES(?, ?, ?, ?) RETURNING id", (a, b, status, time.time()))
        cid = cur.fetchone()[0]
        db.execute('INSERT INTO marriage_bonds(sid, couple) VALUES(?, ?)', (a, cid))
        db.execute('INSERT INTO marriage_bonds(sid, couple) VALUES(?, ?)', (b, cid))
    store.transaction(go)


class Couple(LiveCase):
    cfg_extra = dict(street=True, fair=True)

    def setUp(self):
        super().setUp()
        from game import couple
        couple._SPOUSE_CARS.clear()

    def pair(self, status='married'):
        (ta, sa), (tb, sb) = self.account('Minh Khang'), self.account('Lan Anh')
        marry(self.store, sa, sb, status)
        return (ta, sa), (tb, sb)

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

    def walker(self, c):
        return self.app.hub.rooms.get(c.room['room']).data['people'][c.pid]

    async def stroll(self, token, **extra):
        c = await self.connect(token)
        c.room = await c.call('walk_in', 'walk_room', place='boho', look=LOOK, g='female', title=None, **extra)
        c.pid = c.welcome['me']['pid']
        return c

    async def goer(self, token, **extra):
        c = await self.connect(token)
        c.room = await c.call('fair_in', 'fair_room', look=LOOK, g='female', x=0.2, y=0.9, **extra)
        c.pid = c.welcome['me']['pid']
        return c


@unittest.skipUnless(HAVE_WS, "needs websockets")
class SpouseCars(Couple):
    """GET /api/garage/spouse: the husband's / wife's road vehicles (not one in for repairs), read-only."""
    async def test_married_only(self):
        from game import couple, marriage as mr
        (ta, sa), (tb, sb) = self.pair()
        save = {'journey': {'garage': {'cars': {'xe_ga': {'c': 'hong', 'n': 'MÂY 01', 'd': 1, 'p': 100},
                                                'o_to_suv': {'c': 'bac', 'n': '', 'd': 2, 'p': 900},
                                                'du_thuyen': {'c': 'navy', 'n': '', 'd': 3, 'p': 9000}}, 'ride': 'xe_ga'}}}
        with mock.patch.object(mr, '_read_state', return_value=(save, 1)) as read, \
                mock.patch('game.rui.is_broken', side_effect=lambda s, k, vid: vid == 'o_to_suv'):
            out = couple.spouse_cars(self.store, ta)
            again = couple.spouse_cars(self.store, ta)
        self.assertEqual(out['spouse']['pid'], self.pid(sb))
        self.assertEqual(out['spouse']['name'], 'Lan Anh')
        self.assertEqual(out['spouse']['cars'], [{'id': 'xe_ga', 'color': 'hong', 'plate': 'MÂY 01'}], 'no boat, none in repair')
        self.assertEqual(out['spouse']['ride'], 'xe_ga')
        self.assertIs(again, out)
        self.assertEqual(read.call_count, 1, 'a save read at most once a minute')
        self.assertEqual(couple.spouse_cars(self.store, self.guest('Khách')[0]), {'spouse': None})
        (tc, _), _ = self.pair('engaged')
        self.assertEqual(couple.spouse_cars(self.store, tc), {'spouse': None}, 'engaged: not yet')


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class FirstComeDrives(Couple):
    async def test_on_a_stroll(self):
        (ta, sa), (tb, sb) = self.pair()
        pa, pb = self.pid(sa), self.pid(sb)
        wife = await self.stroll(tb, r={**SCOOTER, 'o': pa})              # she takes his scooter first
        me = [p for p in wife.room['people'] if p['pid'] == pb][0]
        self.assertEqual(me['r'], {**SCOOTER, 'o': pa})
        husband = await self.stroll(ta, r=SCOOTER)                          # his own scooter: taken
        self.assertEqual(husband.room['taken'], {'t': 'walk_taken', 'by': pb, 'name': 'Lan Anh'})
        self.assertNotIn('r', [p for p in husband.room['people'] if p['pid'] == pa][0])
        got = await husband.call('ride', 'walk_taken', r=SCOOTER)
        self.assertEqual(got['by'], pb)
        self.assertIsNone(self.walker(husband).ride)
        await husband.send(t='ride', r={'v': 'xe_dap', 'c': 'xanh_la'})    # one each: they ride apart
        rd = await self.ev(wife, 'walk', 'rd', pid=pa)
        self.assertEqual(rd['r'], {'v': 'xe_dap', 'c': 'xanh_la'})
        await wife.send(t='ride', r=None)                                   # she gets off: his scooter is free
        await self.ev(husband, 'walk', 'rd', pid=pb)
        await husband.send(t='ride', r=SCOOTER)
        self.assertEqual((await self.ev(wife, 'walk', 'rd', pid=pa))['r'], SCOOTER)

    async def test_at_the_fair(self):
        (ta, sa), (tb, sb) = self.pair()
        pa = self.pid(sa)
        await self.goer(ta, r=SCOOTER)
        wife = await self.goer(tb, r={**SCOOTER, 'o': pa})
        self.assertEqual(wife.room['taken']['by'], pa)
        self.assertIsNone(self.app.hub.rooms.get(wife.room['room']).data['people'][wife.pid].r)
        await wife.send(t='fair_mv', p=[[0.2, 0.9], [0.4, 0.5]], ms=300, r={**SCOOTER, 'o': pa})
        self.assertEqual((await wife.expect('fair_taken'))['by'], pa)

    async def test_not_your_spouse(self):
        (ta, sa), _ = self.pair()
        tc, sc = self.account('Người Lạ')
        other = await self.stroll(tc, r={**SCOOTER, 'o': self.pid(sa)})    # someone else's vehicle: on foot
        self.assertNotIn('r', [p for p in other.room['people'] if p['pid'] == other.pid][0])
        husband = await self.stroll(ta, r=SCOOTER)
        self.assertEqual(self.walker(husband).ride, SCOOTER, 'nothing taken by a stranger')
        err = await other.call('back', 'error', to=husband.pid)
        self.assertEqual(err['code'], 'no_back')
        self.assertIsNone(self.walker(other).back)


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class SittingBehind(Couple):
    async def test_passenger_follows_and_gets_off(self):
        (ta, sa), (tb, sb) = self.pair()
        husband = await self.stroll(ta, r=SCOOTER)
        wife = await self.stroll(tb)
        tc, _ = self.account('Hà Vy')
        friend = await self.stroll(tc)                                       # an older client: plain frames
        await wife.send(t='back', to=husband.pid)
        mv = await self.ev(friend, 'walk', 'mv', pid=wife.pid)
        self.assertEqual((mv['b'], mv['v']), (husband.pid, SPEED * RIDE_FAST))
        w = self.walker(wife)
        self.assertEqual((w.back, self.walker(husband).pill), (husband.pid, wife.pid))
        err = await friend.call('back', 'error', to=husband.pid)            # the seat is not theirs
        self.assertEqual(err['code'], 'no_back')
        await asyncio.sleep(0.3)
        await husband.send(t='move', x=500, y=600)
        mv_h = await self.ev(friend, 'walk', 'mv', pid=husband.pid)
        mv_w = await self.ev(friend, 'walk', 'mv', pid=wife.pid)
        self.assertEqual((mv_w['p'], mv_w['at'], mv_w['b']), (mv_h['p'], mv_h['at'], husband.pid))
        await asyncio.sleep(0.3)
        await wife.send(t='move', x=100, y=100)                              # her own taps: the driver drives
        await asyncio.sleep(0.3)
        self.assertEqual(self.walker(wife).path, self.walker(husband).path)
        await wife.send(t='back', to=None)                                   # "Xuống xe"
        off = await self.ev(friend, 'walk', 'mv', pid=wife.pid)
        self.assertNotIn('b', off)
        self.assertEqual(off['p'][0], off['p'][-1])
        self.assertIsNone(self.walker(husband).pill)
        await asyncio.sleep(0.3)
        await wife.send(t='move', x=300, y=600)                               # walking on her own again
        self.assertNotIn('b', await self.ev(friend, 'walk', 'mv', pid=wife.pid))

    async def test_driver_off_the_vehicle_or_at_a_table(self):
        (ta, sa), (tb, sb) = self.pair()
        husband = await self.stroll(ta, r=SCOOTER)
        wife = await self.stroll(tb)
        await wife.send(t='back', to=husband.pid)
        await self.ev(husband, 'walk', 'mv', pid=wife.pid)
        await husband.send(t='ride', r=None)
        self.assertNotIn('b', await self.ev(husband, 'walk', 'mv', pid=wife.pid))
        self.assertIsNone(self.walker(wife).back)
        await husband.send(t='ride', r=SCOOTER)
        await self.ev(wife, 'walk', 'rd', pid=husband.pid)
        await wife.send(t='back', to=husband.pid)
        self.assertEqual((await self.ev(husband, 'walk', 'mv', pid=wife.pid))['b'], husband.pid)
        await husband.send(t='sit', table=0)                                 # parks to sit: she gets off too
        self.assertNotIn('b', await self.ev(husband, 'walk', 'mv', pid=wife.pid))

    async def test_driver_drops_passenger_lands_on_foot(self):
        (ta, sa), (tb, sb) = self.pair()
        husband = await self.stroll(ta, r=SCOOTER)
        wife = await self.stroll(tb)
        await wife.send(t='back', to=husband.pid)
        await self.ev(wife, 'walk', 'mv', pid=wife.pid)
        await husband.send(t='move', x=500, y=600)
        await self.ev(wife, 'walk', 'mv', pid=husband.pid)
        await self.ev(wife, 'walk', 'mv', pid=wife.pid, b=husband.pid)       # carried along
        await asyncio.sleep(0.4)                                             # half way there
        await husband.close()                                                # the driver's phone drops
        off = await self.ev(wife, 'walk', 'mv', pid=wife.pid)
        self.assertNotIn('b', off)
        self.assertEqual((await self.ev(wife, 'walk', 'out'))['pid'], husband.pid)
        w = self.walker(wife)
        self.assertIsNone(w.back)
        self.assertEqual(w.speed, SPEED)
        from live.street import GEO
        self.assertTrue(GEO['boho'].inside(*w.path[-1]))

    async def test_fair_passenger(self):
        (ta, sa), (tb, sb) = self.pair()
        husband = await self.goer(ta, r=SCOOTER)
        wife = await self.goer(tb)
        tc, _ = self.account('Hà Vy')
        friend = await self.goer(tc)
        await wife.send(t='fair_back', to=husband.pid)
        mv = await self.ev(friend, 'fair', 'mv', pid=wife.pid)
        self.assertEqual(mv['b'], husband.pid)
        await husband.send(t='fair_mv', p=[[0.2, 0.9], [0.5, 0.5]], ms=400, r=SCOOTER)
        await self.ev(friend, 'fair', 'mv', pid=husband.pid)
        mv = await self.ev(friend, 'fair', 'mv', pid=wife.pid)
        self.assertEqual((mv['p'], mv['ms'], mv['b']), ([[0.2, 0.9], [0.5, 0.5]], 400, husband.pid))
        await asyncio.sleep(0.3)
        await wife.send(t='fair_mv', p=[[0.5, 0.5], [0.1, 0.1]], ms=300)     # ignored while behind
        await asyncio.sleep(0.3)
        self.assertFalse([e for f in friend.frames if f.get('t') == 'fair' for e in f['ev'] if e.get('pid') == wife.pid and e.get('p', [[0]])[-1] == [0.1, 0.1]])
        await husband.send(t='fair_mv', p=[[0.5, 0.5], [0.14, 0.08]], ms=400, s='lt', r=SCOOTER)   # parks at the lô tô
        off = await self.ev(friend, 'fair', 'mv', pid=wife.pid)
        self.assertNotIn('b', off)
        self.assertEqual(off['p'][-1], [0.14, 0.08], 'she walks in with him')
        await wife.send(t='fair_back', to=husband.pid)                        # playing a stall: no seat behind
        self.assertEqual((await wife.expect('error'))['code'], 'no_back')
        await asyncio.sleep(0.3)
        await husband.send(t='fair_mv', p=[[0.14, 0.08], [0.3, 0.6]], ms=300, r=SCOOTER)
        await wife.send(t='fair_back', to=husband.pid)
        await self.ev(friend, 'fair', 'mv', pid=wife.pid, b=husband.pid)
        await husband.call('fair_out', 'fair_left')                          # he leaves: she stays, on foot
        off = await self.ev(friend, 'fair', 'mv', pid=wife.pid)
        self.assertNotIn('b', off)
        self.assertIsNone(self.app.hub.rooms.get(wife.room['room']).data['people'][wife.pid].b)


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class OlderClients(Couple):
    async def test_same_frames_when_nobody_shares(self):
        """A 1.6.0 client (r without `o`, no `back`) gets what it always got: no `b`, no `taken`, no new frame."""
        (ta, sa), (tb, sb) = self.pair()
        a = await self.stroll(ta, r=SCOOTER)
        b = await self.stroll(tb, r={'v': 'xe_dap', 'c': ''})
        self.assertTrue(a.welcome['flags']['coride'], 'newer clients show "Ngồi sau" only with this flag')
        self.assertNotIn('taken', a.room)
        self.assertNotIn('taken', b.room)
        await a.send(t='move', x=500, y=600)
        mv = await self.ev(b, 'walk', 'mv', pid=a.pid)
        self.assertEqual(set(mv), {'k', 'pid', 'p', 'at'})
        for p in b.room['people']:
            self.assertNotIn('b', p)
        g1 = await self.goer(ta, r=SCOOTER)
        g2 = await self.goer(tb)
        self.assertNotIn('taken', g1.room)
        await g1.send(t='fair_mv', p=[[0.2, 0.9], [0.5, 0.5]], ms=300, r=SCOOTER)
        mv = await self.ev(g2, 'fair', 'mv', pid=g1.pid)
        self.assertEqual(set(mv), {'k', 'pid', 'p', 'ms', 'r'})
        self.assertFalse([f for c in (a, b, g1, g2) for f in c.frames if f.get('t') in ('error', 'walk_taken', 'fair_taken')])


if __name__ == '__main__':
    unittest.main()
