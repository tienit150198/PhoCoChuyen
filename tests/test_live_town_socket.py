"""Real authenticated sockets on a disposable PostgreSQL schema (TEST_DATABASE_URL)."""
import asyncio
import time
import unittest

from live.town import MAP_ID
from tests.live_support import LiveCase
from tests.test_live_town import NOT_WIRED, TOWN_WIRED


@unittest.skipUnless(TOWN_WIRED, NOT_WIRED)
class TownSockets(LiveCase):
    cfg_extra = dict(town=True)

    async def enter(self, name, token=None):
        token = token or self.guest(name)[0]
        c = await self.connect(token)
        c.room = await c.call('town_in', 'town_room', map=MAP_ID, x=6, y=6, direction='se',
                              look={'top': 'ao_hoodie'}, g='female', name='Spoof',
                              task={'private': True}, save={'secret': 1}, cid='join-'+name)
        c.pid = c.room['me']
        return c

    async def event(self, c, kind, pid):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            frame = await c.expect('town', timeout=max(.01, deadline-time.monotonic()))
            for ev in frame['ev']:
                if ev['k'] == kind and ev['pid'] == pid:
                    return ev
        self.fail(f'no {kind} for {pid}')

    async def test_town_only_real_identity_movement_and_no_game_state_broadcast(self):
        # Disabling chat before hello exercises the independent town flag / welcome.
        self.cfg.chat = False
        a, b = await self.enter('Lan'), await self.enter('Minh')
        self.assertFalse(a.welcome['flags']['chat'])
        self.assertTrue(a.welcome['flags']['town'])
        self.assertEqual(a.welcome['me']['pid'], a.pid)
        peer = b.room['people'][0]
        self.assertEqual(peer['name'], 'Lan')
        self.assertEqual(set(peer), {'pid', 'name', 'lk', 'g', 'fc', 'x', 'y', 'direction'})
        self.assertEqual(b.room['cid'], 'join-Minh')
        calls, original = [], self.app.db._run
        async def track(sql, *args, **kw):
            calls.append(sql)
            return await original(sql, *args, **kw)
        self.app.db._run = track
        try:
            await asyncio.sleep(.3)
            await a.send(t='town_mv', x=6, y=6.5, direction='sw', save={'secret': 7})
            ev = await self.event(b, 'mv', a.pid)
            self.assertEqual((ev['x'], ev['y'], ev['direction']), (6, 6.5, 'sw'))
            self.assertEqual(set(ev), {'k', 'pid', 'x', 'y', 'direction'})
            await a.send(t='town_mv', x=6, y=49)
            error = await a.expect('error', ref='town_mv')
            self.assertEqual(error['code'], 'speed')
            self.assertEqual(calls, [], 'walking reads/writes no database or private save')
        finally:
            self.app.db._run = original
        await a.call('town_out', 'town_left')
        await self.event(b, 'out', a.pid)

    async def test_two_tabs_takeover_disconnect_and_block_filter(self):
        token = self.guest('Lan')[0]
        a, b = await self.enter('Lan', token), await self.enter('Minh')
        another = await self.enter('Lan again', token)
        self.assertEqual((await a.expect('town_left'))['why'], 'other')
        await a.call('town_out', 'town_left')
        room = self.app.hub.rooms[another.room['room']]
        self.assertIn(a.pid, room.data['people'], 'stale first tab cannot remove second tab')
        # Social REST stores this same row without notifying live; the bounded refresh sees it.
        with self.store.connect() as db:
            db.execute('INSERT INTO blocks(pid,target,at) VALUES(?,?,?)', (a.pid, b.pid, time.time()))
        self.app.by_name['town']._blocks_at = 0
        await self.app.by_name['town'].tick(time.monotonic())
        await self.event(another, 'out', b.pid)
        await self.event(b, 'out', a.pid)
        b.frames.clear()
        await another.send(t='town_mv', x=6, y=6.1, direction='ne')
        await asyncio.sleep(.25)
        self.assertFalse(any(e.get('pid') == a.pid for f in b.frames if f['t']=='town' for e in f['ev']))
        await another.close()
        await asyncio.sleep(.1)
        self.assertNotIn(a.pid, room.data['people'])
