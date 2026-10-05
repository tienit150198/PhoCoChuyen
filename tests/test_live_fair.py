"""🏮 Đi hội chợ cùng nhau (live/fair.py): instances, positions as fractions of the floor (clamped, validated, rate
limited, batched, never in the database), blocks, a second tab, the switch, and no notification of any kind. Real
sockets against a real game database (PostgreSQL with TEST_DATABASE_URL)."""
import asyncio
import math
import time
import unittest

from live.config import from_env
from live.fair import CAP, MAX_POINTS, clean_point, clean_stall
from live.protocol import LiveError
from tests.live_support import HAVE_WS, LiveCase

LOOK = dict(hair='toc_bob', shade='mau_hong', skin='da_trung', top='ao_hoodie', bottom='quan_jean', shoes='giay_trang', acc='kinh_tron')


class Units(unittest.TestCase):
    def test_points_are_clamped_fractions(self):
        self.assertEqual(clean_point([0.25, 0.5]), [0.25, 0.5])
        self.assertEqual(clean_point([-3, 7]), [0.0, 1.0])
        self.assertEqual(clean_point((0.12345, 0.98765)), [0.123, 0.988])
        for bad in (None, 'x', [1], [1, 2, 3], ['1', 2], [float('nan'), 0], [0, float('inf')], [True, 0]):
            with self.assertRaises(LiveError):
                clean_point(bad)

    def test_stall_ids_are_short_words_or_none(self):
        for ok in ('lt', 'bc', 'ring', 'candy', 'oaq'):
            self.assertEqual(clean_stall(ok), ok)
        for odd in (None, '', 'LT', 'lô', 'toolongid', 'a b', '../x', 5, ['lt'], True):
            self.assertIsNone(clean_stall(odd), odd)

    def test_switch_follows_the_street_unless_set(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {'LIVE_STREET': '1', 'DATABASE_URL': 'postgresql://config-only@127.0.0.1:1/fixture'}, clear=False):
            os.environ.pop('LIVE_FAIR', None)
            self.assertTrue(from_env([]).flags()['fair'])
            os.environ['LIVE_FAIR'] = '0'
            self.assertFalse(from_env([]).flags()['fair'])
        with mock.patch.dict(os.environ, {'LIVE_STREET': '0', 'DATABASE_URL': 'postgresql://config-only@127.0.0.1:1/fixture'}, clear=False):
            os.environ.pop('LIVE_FAIR', None)
            self.assertFalse(from_env([]).flags()['fair'])
            os.environ['LIVE_FAIR'] = '1'
            self.assertTrue(from_env([]).flags()['fair'])


class FairCase(LiveCase):
    cfg_extra = dict(fair=True)

    async def goer(self, name, x=0.2, y=0.9, token=None, look=LOOK, g='female'):
        tok = token or self.guest(name)[0]
        c = await self.connect(tok)
        c.room = await c.call('fair_in', 'fair_room', look=look, g=g, x=x, y=y)
        c.pid = c.welcome['me']['pid']
        return c

    @staticmethod
    async def ev(c, k, timeout=3.0, **match):
        """The first queued diff event of kind k (and fields equal to `match`), removed from its frame."""
        end = time.monotonic() + timeout
        while True:
            for f in c.frames:
                if f.get('t') == 'fair':
                    for e in f['ev']:
                        if e.get('k') == k and all(e.get(x) == v for x, v in match.items()):
                            f['ev'].remove(e)
                            return e
            if time.monotonic() > end:
                raise AssertionError(f'no {k} {match} in {[f for f in c.frames if f.get("t") == "fair"]}')
            await asyncio.sleep(0.02)

    def room(self, rid):
        return self.app.hub.rooms.get(rid)


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Rooms(FairCase):
    async def test_join_snapshot_others_and_leaving(self):
        a = await self.goer('Lan Anh', x=0.3, y=0.8)
        self.assertEqual((a.room['room'], a.room['me'], a.room['people'], a.room['cap']), ('fair:1', a.pid, [], CAP))
        b = await self.goer('Minh Tú', x=5, y=-1, g='male')          # outside the floor: clamped into it
        self.assertEqual(b.room['room'], 'fair:1')
        seen = b.room['people']
        self.assertEqual([(p['pid'], p['name'], p['x'], p['y'], p['lk']['top'], p['g']) for p in seen],
                         [(a.pid, 'Lan Anh', 0.3, 0.8, 'ao_hoodie', 'female')])
        came = await self.ev(a, 'in', pid=b.pid)
        self.assertEqual((came['name'], came['x'], came['y'], came['g']), ('Minh Tú', 1.0, 0.0, 'male'))
        await b.call('fair_out', 'fair_left')
        self.assertEqual((await self.ev(a, 'out'))['pid'], b.pid)
        self.assertEqual(list(self.room('fair:1').data['people']), [a.pid])
        await b.close()
        await a.close()
        await asyncio.sleep(0.1)
        self.assertEqual([r for r in self.app.hub.rooms if r.startswith('fair:')], [], 'empty rooms are dropped')

    async def test_a_closed_socket_walks_out(self):
        a = await self.goer('Lan Anh')
        b = await self.goer('Minh Tú')
        await b.close()
        self.assertEqual((await self.ev(a, 'out'))['pid'], b.pid)

    async def test_no_notification_of_any_kind(self):
        a = await self.goer('Lan Anh')
        a.frames.clear()
        b = await self.goer('Minh Tú')
        await b.send(t='fair_mv', p=[[0.2, 0.9], [0.5, 0.5]], ms=600)
        await b.call('fair_out', 'fair_left')
        await asyncio.sleep(0.4)
        self.assertEqual({f['t'] for f in a.frames}, {'fair'}, 'only the silent diffs: no toast, chat or presence frame')
        self.assertEqual({e['k'] for f in a.frames for e in f['ev']}, {'in', 'mv', 'out'})

    async def test_capacity_and_the_fullest_instance(self):
        clients = [await self.goer(f'Người {i}') for i in range(CAP)]
        self.assertTrue(all(c.room['room'] == 'fair:1' for c in clients))
        self.assertEqual(len(clients[-1].room['people']), CAP - 1)
        extra = await self.goer('Người thứ 31')
        self.assertEqual((extra.room['room'], extra.room['people']), ('fair:2', []))
        await clients[0].call('fair_out', 'fair_left')
        late = await self.goer('Người đến sau')   # room 1 has 29, room 2 has 1: the fullest with room
        self.assertEqual(late.room['room'], 'fair:1')

    async def test_a_second_tab_takes_the_first_out(self):
        tok, _ = self.guest('Hai Tab')
        a = await self.goer('Hai Tab', token=tok)
        w = await self.goer('Người xem')
        b = await self.connect(tok)
        r = await b.call('fair_in', 'fair_room', look=LOOK, x=0.5, y=0.5)
        self.assertEqual((await a.expect('fair_left'))['why'], 'other')
        self.assertEqual(r['room'], 'fair:1')
        self.assertEqual(list(self.room('fair:1').data['people']), [w.pid, a.pid])
        self.assertEqual((await a.call('fair_mv', 'error', p=[[0.1, 0.1]], ms=100))['code'], 'not_in')
        await b.send(t='fair_mv', p=[[0.5, 0.5], [0.6, 0.6]], ms=200)
        self.assertEqual((await self.ev(w, 'mv', pid=a.pid))['p'][-1], [0.6, 0.6])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Walks(FairCase):
    async def test_validated_batched_and_rate_limited(self):
        a = await self.goer('Lan Anh')
        b = await self.goer('Minh Tú')
        await self.ev(a, 'in')
        await a.send(t='fair_mv', p=[[0.2, 0.9], [0.4, 1.7], [-1, 0.5]], ms=99999)
        mv = await self.ev(b, 'mv', pid=a.pid)
        self.assertEqual((mv['p'], mv['ms']), ([[0.2, 0.9], [0.4, 1.0], [0.0, 0.5]], 3000))
        self.assertEqual((self.room('fair:1').data['people'][a.pid].x, self.room('fair:1').data['people'][a.pid].y), (0.0, 0.5))
        await asyncio.sleep(1.05)
        await a.send(t='fair_mv', p=[[0.7, 0.7]], ms=300)     # one point: from where they stood
        self.assertEqual((await self.ev(b, 'mv', pid=a.pid))['p'], [[0.0, 0.5], [0.7, 0.7]])
        await asyncio.sleep(1.05)
        for x in (0.1, 0.2, 0.3, 0.4):                          # four walks inside one flush window: only the last
            await a.send(t='fair_mv', p=[[0.5, 0.5], [x, 0.5]], ms=100)
        await asyncio.sleep(0.4)
        last = [e for f in b.frames if f.get('t') == 'fair' for e in f['ev'] if e['k'] == 'mv' and e['pid'] == a.pid]
        self.assertEqual(last[-1]['p'][-1], [0.4, 0.5])
        self.assertLessEqual(len(last), 2)
        self.assertEqual((await a.call('fair_mv', 'error', p=[[0.1, 0.1]], ms=1))['code'], 'slow')   # 4 per second
        for bad in (dict(p=[[0.1, 0.1]] * (MAX_POINTS + 1), ms=1), dict(p=[], ms=1), dict(p='x', ms=1), dict(p=[[0.1, 0.1]]),
                    dict(p=[[0.1, 0.1], ['a', 0.1]], ms=1), dict(p=[[0.1, 0.1]], ms='9')):
            await asyncio.sleep(1.05)
            self.assertEqual((await a.call('fair_mv', 'error', **bad))['code'], 'bad', bad)
        self.assertEqual((await a.call('fair_in', 'error', look='x'))['code'], 'bad')

    async def test_walks_never_touch_the_database_and_diffs_stay_under_10_per_second(self):
        clients = [await self.goer(f'Đi {i}') for i in range(6)]
        watcher = clients[0]
        await asyncio.sleep(0.3)
        db = self.app.db
        calls = []
        orig_run, orig_tx = db._run, db.transaction

        async def run(*a, **k):
            calls.append(a[0])
            return await orig_run(*a, **k)

        async def tx(*a, **k):
            calls.append('tx')
            return await orig_tx(*a, **k)
        db._run, db.transaction = run, tx
        watcher.frames.clear()
        t0 = time.monotonic()
        for step in range(8):                                    # 5 players × 4 walks per second for 2 s
            for i, c in enumerate(clients[1:]):
                await c.send(t='fair_mv', p=[[0.1, 0.5], [0.1 + step * 0.1, 0.5 + i * 0.05]], ms=250)
            await asyncio.sleep(0.25)
        await asyncio.sleep(0.2)
        span = time.monotonic() - t0
        db._run, db.transaction = orig_run, orig_tx
        self.assertEqual(calls, [], 'walks never touch the database')
        diffs = [f for f in watcher.frames if f.get('t') == 'fair']
        self.assertGreater(len(diffs), 5)
        self.assertLessEqual(len(diffs), math.ceil(span * 10) + 1, f'{len(diffs)} diffs in {span:.2f}s')
        self.assertFalse([f for f in watcher.frames if f.get('t') == 'error'])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Stalls(FairCase):
    """Owner, 03/10: someone playing a stall is seen standing at it (never gone), with which stall it is."""
    async def test_playing_a_stall_travels_with_walks_and_snapshots(self):
        a = await self.goer('Lan Anh')
        b = await self.goer('Minh Tú')
        await self.ev(a, 'in', pid=b.pid)
        self.assertNotIn('s', b.room['people'][0], 'nothing new while nobody plays: old clients see the same frames')
        await a.send(t='fair_mv', p=[[0.2, 0.9], [0.14, 0.08]], ms=500, s='lt')
        mv = await self.ev(b, 'mv', pid=a.pid)
        self.assertEqual((mv['p'][-1], mv['s']), ([0.14, 0.08], 'lt'))
        self.assertEqual(self.room('fair:1').data['people'][a.pid].s, 'lt')
        c = await self.goer('Hà Vy')                                  # comes in later: sees her at the lô tô
        self.assertEqual({p['pid']: p.get('s') for p in c.room['people']}, {a.pid: 'lt', b.pid: None})
        await asyncio.sleep(0.3)
        await a.send(t='fair_mv', p=[[0.14, 0.08], [0.14, 0.08]], ms=0)   # back on the walk: no `s`, no badge
        mv = await self.ev(b, 'mv', pid=a.pid)
        self.assertNotIn('s', mv)
        self.assertIsNone(self.room('fair:1').data['people'][a.pid].s)
        await asyncio.sleep(0.3)
        await a.send(t='fair_mv', p=[[0.14, 0.08], [0.5, 0.5]], ms=300, s='NOPE!')   # odd: a plain walk, never an error
        self.assertNotIn('s', await self.ev(b, 'mv', pid=a.pid))
        self.assertFalse([f for f in a.frames if f.get('t') == 'error'])

    async def test_coming_in_at_a_stall_and_staying_while_playing(self):
        a = await self.goer('Lan Anh')
        tok, _ = self.guest('Minh Tú')
        b = await self.connect(tok)
        r = await b.call('fair_in', 'fair_room', look=LOOK, g='male', x=0.45, y=0.1, s='bc')   # a reconnect on the bầu cua page
        came = await self.ev(a, 'in', pid=r['me'])
        self.assertEqual((came['x'], came['y'], came['s']), (0.45, 0.1, 'bc'))
        a.frames.clear()
        await asyncio.sleep(1.2)                                       # a while at the stall, no walk: still there
        await self.app.by_name['fair'].tick(time.time())
        self.assertIn(r['me'], self.room('fair:1').data['people'])
        self.assertFalse([e for f in a.frames for e in f.get('ev', []) if e.get('k') == 'out'])
        await b.close()
        self.assertEqual((await self.ev(a, 'out'))['pid'], r['me'])   # leaving the fair still walks out


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Blocks(FairCase):
    async def test_block_at_the_fair_and_new_instances(self):
        a = await self.goer('Lan Anh')
        b = await self.goer('Minh Tú')
        c = await self.goer('Hà Vy')
        await a.call('block', 'blocked', pid=b.pid)
        await self.app.by_name['fair'].tick(time.time())
        self.assertEqual((await self.ev(a, 'out', pid=b.pid))['pid'], b.pid)
        self.assertEqual((await self.ev(b, 'out', pid=a.pid))['pid'], a.pid)
        a.frames.clear()
        await b.send(t='fair_mv', p=[[0.2, 0.9], [0.8, 0.6]], ms=500)
        await self.ev(c, 'mv', pid=b.pid)
        await asyncio.sleep(0.3)
        self.assertFalse([e for f in a.frames for e in f.get('ev', []) if e.get('pid') == b.pid])
        # out and back in: never the same instance again, and not in each other's snapshot
        await b.call('fair_out', 'fair_left')
        b2 = await b.call('fair_in', 'fair_room', look=LOOK, x=0.5, y=0.5)
        self.assertEqual(b2['room'], 'fair:2')
        self.assertNotIn(a.pid, [p['pid'] for p in b2['people']])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Switch(LiveCase):
    async def test_fair_off(self):
        c = await self.connect(self.guest('Lan Anh')[0])
        self.assertFalse(c.welcome['flags']['fair'])
        self.assertEqual((await c.call('fair_in', 'error', look=LOOK, x=0.5, y=0.5))['code'], 'off')


if __name__ == '__main__':
    unittest.main()
