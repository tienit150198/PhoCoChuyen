"""📸 Buồng chụp ảnh hội chợ together (live/booth.py): a friends' room by code (any case, wrong code, full, the host's
frame, poses and props, ready and shoot, the host leaving, sending someone out, a second tab, a closed socket, idle
rooms), the strangers' queue (paired, timed out, cancelled, never with someone blocked) and blocks (never revealed,
a block made in the room). Real sockets against a real game database; nothing is written to it."""
import asyncio
import time
import unittest
from unittest import mock

from live import booth as bt
from tests.live_support import HAVE_WS, LiveCase

LOOK = dict(hair='toc_bob', shade='mau_hong', skin='da_trung', top='ao_hoodie', bottom='quan_jean', shoes='giay_trang', acc='kinh_tron')


class Units(unittest.TestCase):
    def test_codes(self):
        self.assertEqual(bt.clean_code('a7k2'), 'A7K2')
        self.assertEqual(bt.clean_code('  b3cd '), 'B3CD')
        for bad in (None, 5, '', 'A7K', 'A7K22', 'A0K2', 'AIK2', 'L1OO', 'A K2', ['A7K2']):
            self.assertIsNone(bt.clean_code(bad), bad)
        self.assertFalse(set('01ILO') & set(bt.CODE_CHARS))

    def test_ids_never_refused(self):
        self.assertEqual(bt.clean_id('tet', 'dem_hoi'), 'tet')
        self.assertEqual(bt.clean_id('mu_tiec2', 'none'), 'mu_tiec2')
        for odd in (None, '', 'TET', 'tết', 'x' * 17, '../a', 5, ['tet']):
            self.assertEqual(bt.clean_id(odd, 'dung'), 'dung')


class BoothCase(LiveCase):
    cfg_extra = dict(fair=True)

    async def player(self, name):
        c = await self.connect(self.guest(name)[0])
        c.pid = c.welcome['me']['pid']
        return c

    async def make(self, c):
        await c.send(t='booth_make', look=LOOK, g='female')
        return await c.expect('booth_room')

    async def join(self, c, code, n=None):
        await c.send(t='booth_join', code=code, look=LOOK, g='male')
        r = await c.expect('booth_room')
        if n is not None:
            while len(r['people']) != n:
                r = await c.expect('booth_room')
        return r

    @staticmethod
    async def last(c, t='booth_room', wait=0.25):
        """The newest frame of type t that arrived (after a short wait), all of them removed."""
        await asyncio.sleep(wait)
        got = [f for f in c.frames if f.get('t') == t]
        c.frames[:] = [f for f in c.frames if f.get('t') != t]
        return got[-1] if got else None

    def feat(self):
        return self.app.by_name['booth']


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Friends(BoothCase):
    async def test_flag_make_and_join_by_code(self):
        a = await self.player('Lan Anh')
        self.assertTrue(a.welcome['flags']['booth'])
        r = await self.make(a)
        code = r['code']
        self.assertEqual(len(code), bt.CODE_LEN)
        self.assertTrue(set(code) <= set(bt.CODE_CHARS))
        self.assertEqual((r['mode'], r['host'], r['me'], r['cap'], r['frame'], r['bg'], r['shooting']), ('friends', a.pid, a.pid, bt.CAP, 'dem_hoi', 'kem', False))
        self.assertEqual([p['pid'] for p in r['people']], [a.pid])
        self.assertEqual(r['people'][0]['name'], 'Lan Anh')
        self.assertEqual(r['people'][0]['lk']['hair'], 'toc_bob')
        self.assertEqual(set(r['people'][0]), {'pid', 'name', 'lk', 'g', 'pose', 'prop', 'ready'})   # nothing else of anyone
        b = await self.player('Minh Tú')
        rb = await self.join(b, f'  {code.lower()} ')
        self.assertEqual((rb['me'], rb['host'], [p['pid'] for p in rb['people']]), (b.pid, a.pid, [a.pid, b.pid]))
        ra = await a.expect('booth_room')
        self.assertEqual((ra['me'], len(ra['people'])), (a.pid, 2))
        self.assertEqual(self.app.hub.rooms[bt.PREFIX + code].data['people'][b.pid].g, 'male')

    async def test_wrong_code_full_room_and_bad_codes(self):
        a = await self.player('Lan Anh')
        code = (await self.make(a))['code']
        x = await self.player('Người Lạ')
        other = next(c for c in ('ABCD', 'WXYZ', 'HJKM') if c != code)
        e = await x.call('booth_join', 'error', code=other, look=LOOK)
        self.assertEqual((e['code'], e['msg']), ('nocode', bt.NOCODE))
        for bad in ('A7', 'O0O0', 42, None):
            self.assertEqual((await x.call('booth_join', 'error', code=bad, look=LOOK))['code'], 'nocode')
        for name in ('Minh Tú', 'Hà Vy', 'Bảo Ngọc'):
            await self.join(await self.player(name), code)
        e = await x.call('booth_join', 'error', code=code, look=LOOK)
        self.assertEqual(e['code'], 'full')
        self.assertEqual(len(self.app.hub.rooms[bt.PREFIX + code].data['people']), bt.CAP)

    async def test_frame_poses_ready_and_shoot(self):
        a = await self.player('Lan Anh')
        code = (await self.make(a))['code']
        b = await self.player('Minh Tú')
        await self.join(b, code)
        await a.expect('booth_room')
        await a.send(t='booth_set', frame='tet')
        self.assertEqual((await b.expect('booth_room'))['frame'], 'tet')
        e = await b.call('booth_set', 'error', frame='bien')
        self.assertEqual(e['code'], 'host')
        self.assertEqual((await b.call('booth_set', 'error', bg='hoa'))['code'], 'host')
        await a.send(t='booth_set', bg='kim_tuyen')
        self.assertEqual((await self.last(b))['bg'], 'kim_tuyen')
        await b.send(t='booth_set', pose='vay', prop='bong_bay')
        r = await self.last(a)
        me = {p['pid']: p for p in r['people']}[b.pid]
        self.assertEqual((me['pose'], me['prop'], r['frame']), ('vay', 'bong_bay', 'tet'))
        await b.send(t='booth_set', pose='<b>', prop=['x'])   # odd ids: the defaults, never an error
        r = await self.last(a)
        me = {p['pid']: p for p in r['people']}[b.pid]
        self.assertEqual((me['pose'], me['prop']), ('dung', 'none'))
        self.assertEqual((await b.call('booth_go', 'error'))['code'], 'host')
        await a.send(t='booth_ready')
        self.assertEqual((await a.call('booth_go', 'error'))['code'], 'not_ready')
        await b.send(t='booth_ready')
        r = await self.last(a)
        self.assertTrue(all(p['ready'] for p in r['people']))
        await a.send(t='booth_go')
        for c in (a, b):
            s = await c.expect('booth_shoot')
            self.assertEqual((s['n'], s['gap'], s['id']), (bt.SHOTS, bt.GAP_MS, 1))
        r = await self.last(b)
        self.assertTrue(r['shooting'])
        self.assertFalse(any(p['ready'] for p in r['people']))   # the next shoot is paid again
        self.assertEqual((await a.call('booth_go', 'error'))['code'], 'busy')
        b.frames.clear()
        await b.send(t='booth_set', pose='tim')   # poses change between the shots
        self.assertEqual({p['pid']: p for p in (await self.last(a))['people']}[b.pid]['pose'], 'tim')
        self.app.hub.rooms[bt.PREFIX + code].data['shoot_until'] = time.monotonic() - 1   # the shoot's time is over
        await self.feat().tick(time.time())
        self.assertFalse((await self.last(b))['shooting'])   # told at once: the frame and the ready button come back

    async def test_leaving_the_host_leaving_and_the_last_one_out(self):
        a = await self.player('Lan Anh')
        code = (await self.make(a))['code']
        b, c = await self.player('Minh Tú'), await self.player('Hà Vy')
        await self.join(b, code)
        await self.join(c, code)
        await self.last(b)
        self.assertEqual((await a.call('booth_out', 'booth_left'))['why'], 'out')
        r = await b.expect('booth_room')
        self.assertEqual((r['host'], [p['pid'] for p in r['people']]), (b.pid, [b.pid, c.pid]))   # who came in first after the host
        await c.send(t='booth_set', frame='bien')
        self.assertEqual((await c.expect('error'))['code'], 'host')
        await b.send(t='booth_set', frame='bien')
        self.assertEqual((await self.last(c))['frame'], 'bien')
        self.assertEqual((await a.call('booth_set', 'error', pose='vay'))['code'], 'not_in')
        await b.call('booth_out', 'booth_left')
        await self.last(c)
        await c.call('booth_out', 'booth_left')
        self.assertNotIn(bt.PREFIX + code, self.app.hub.rooms)
        e = await a.call('booth_join', 'error', code=code, look=LOOK)
        self.assertEqual(e['code'], 'nocode')

    async def test_kick_second_tab_closed_socket_and_idle(self):
        tok_a = self.guest('Lan Anh')[0]
        a = await self.connect(tok_a)
        a.pid = a.welcome['me']['pid']
        code = (await self.make(a))['code']
        b = await self.player('Minh Tú')
        await self.join(b, code)
        await self.last(a)
        await a.send(t='booth_kick', pid=b.pid)
        self.assertEqual((await b.expect('booth_left'))['why'], 'kick')
        self.assertEqual(len((await a.expect('booth_room'))['people']), 1)
        self.assertEqual((await b.call('booth_join', 'error', code=code, look=LOOK))['code'], 'nocode')   # not back in
        # a second tab of the host opens another room: the first tab is out
        a2 = await self.connect(tok_a)
        code2 = (await self.make(a2))['code']
        self.assertEqual((await a.expect('booth_left'))['why'], 'other')
        self.assertNotIn(bt.PREFIX + code, self.app.hub.rooms)
        c = await self.player('Hà Vy')
        await self.join(c, code2)
        await self.last(a2)
        await a2.close()                                   # the host's socket goes: the room is c's
        r = await c.expect('booth_room')
        self.assertEqual((r['host'], len(r['people'])), (c.pid, 1))
        with mock.patch.object(bt, 'IDLE_SECS', 0):
            await self.feat().tick(time.time())
        self.assertEqual((await c.expect('booth_left'))['why'], 'idle')
        self.assertNotIn(bt.PREFIX + code2, self.app.hub.rooms)


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Strangers(BoothCase):
    async def test_paired_with_the_first_waiter(self):
        a, b = await self.player('Lan Anh'), await self.player('Minh Tú')
        w = await a.call('booth_find', 'booth_wait', look=LOOK, g='female')
        self.assertEqual(w['secs'], bt.WAIT_SECS)
        await b.send(t='booth_find', look=LOOK, g='male')
        rb, ra = await b.expect('booth_room'), await a.expect('booth_room')
        for r, me in ((ra, a.pid), (rb, b.pid)):
            self.assertEqual((r['mode'], r['code'], r['host'], r['me'], r['cap']), ('stranger', '', a.pid, me, bt.PAIR))
            self.assertEqual([p['pid'] for p in r['people']], [a.pid, b.pid])
        self.assertFalse(self.feat().queue)
        c = await self.player('Hà Vy')   # the next one waits on their own (a strangers' room takes no one else)
        self.assertEqual((await c.call('booth_find', 'booth_wait', look=LOOK))['secs'], bt.WAIT_SECS)
        self.assertEqual((await c.call('booth_join', 'error', code=ra['room'], look=LOOK))['code'], 'nocode')

    async def test_timeout_and_cancel(self):
        a, b = await self.player('Lan Anh'), await self.player('Minh Tú')
        await a.call('booth_find', 'booth_wait', look=LOOK)
        with mock.patch.object(bt, 'WAIT_SECS', 0):
            await self.feat().tick(time.time())
        self.assertEqual((await a.expect('booth_none'))['why'], 'timeout')
        self.assertFalse(self.feat().queue)
        await b.call('booth_find', 'booth_wait', look=LOOK)   # a is not waiting any more: b waits
        self.assertEqual((await b.call('booth_cancel', 'booth_left'))['why'], 'cancel')
        await a.call('booth_find', 'booth_wait', look=LOOK)   # b cancelled: a waits
        self.assertEqual(list(self.feat().queue), [a.pid])
        await a.close()                                       # a closed socket leaves the queue
        await asyncio.sleep(0.2)
        self.assertFalse(self.feat().queue)

    async def test_never_paired_with_someone_blocked(self):
        a, b, c = await self.player('Lan Anh'), await self.player('Minh Tú'), await self.player('Hà Vy')
        await a.call('block', 'blocked', pid=b.pid)
        await a.call('booth_find', 'booth_wait', look=LOOK)
        await b.call('booth_find', 'booth_wait', look=LOOK)   # a is waiting, but blocked: b waits too
        self.assertEqual(list(self.feat().queue), [a.pid, b.pid])
        await c.send(t='booth_find', look=LOOK)
        r = await c.expect('booth_room')
        self.assertEqual([p['pid'] for p in r['people']], [a.pid, c.pid])
        self.assertEqual(list(self.feat().queue), [b.pid])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Blocks(BoothCase):
    async def test_blocked_cannot_join_and_a_block_in_the_room(self):
        a, b, c = await self.player('Lan Anh'), await self.player('Minh Tú'), await self.player('Hà Vy')
        await b.call('block', 'blocked', pid=a.pid)            # b blocks the host: the code looks wrong to b
        code = (await self.make(a))['code']
        e = await b.call('booth_join', 'error', code=code, look=LOOK)
        self.assertEqual((e['code'], e['msg']), ('nocode', bt.NOCODE))
        await self.join(c, code)
        await self.last(a)
        await c.call('block', 'blocked', pid=a.pid)            # a block made in the room: the later one goes
        await self.feat().tick(time.time())
        self.assertEqual((await c.expect('booth_left'))['why'], 'blocked')
        r = await self.last(a)
        self.assertEqual([p['pid'] for p in r['people']], [a.pid])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Switch(LiveCase):
    async def test_booth_off_with_the_fair(self):
        c = await self.connect(self.guest('Lan Anh')[0])
        self.assertNotIn('booth', c.welcome['flags'])
        self.assertEqual((await c.call('booth_make', 'error', look=LOOK))['code'], 'off')


if __name__ == '__main__':
    unittest.main()
