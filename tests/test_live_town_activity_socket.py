"""Real authenticated outdoor presence with private state and DB isolation checks."""
import asyncio
import json
import time

from tests import test_live_town_socket as town_sockets
from tests.live_support import LiveCase
from tests.test_live_town_activity import pose


class ActivitySockets(LiveCase):
    cfg_extra = dict(town=True)
    enter = town_sockets.TownSockets.enter
    event = town_sockets.TownSockets.event

    async def test_public_activity_snapshot_motion_and_clear_are_memory_only(self):
        a, b = await self.enter('Lan'), await self.enter('Minh')
        # Drain the ordinary joins before observing cosmetic updates.
        await asyncio.sleep(.12)
        a.frames.clear()
        b.frames.clear()
        calls, original = [], self.app.db._run
        async def track(sql, *args, **kw):
            calls.append(sql)
            return await original(sql, *args, **kw)
        self.app.db._run = track
        try:
            await a.send(t='town_mv', x=6, y=6, activity={**pose(), 'round': {'id': 'private-round'}, 'reward': 10000})
            event = await self.event(b, 'mv', a.pid)
            self.assertEqual(event['activity'], pose())
            self.assertNotIn('private-round', json.dumps(event))
            await asyncio.sleep(.27)
            await a.send(t='town_mv', x=6, y=6, activity={**pose(), 'x': 90, 'action': 'cast'})
            event = await self.event(b, 'mv', a.pid)
            self.assertEqual(event['activity']['x'], 90)
            self.assertEqual(event['activity']['action'], 'cast')
            await asyncio.sleep(.27)
            await a.send(t='town_mv', x=6, y=6, activity={**pose(), 'x': 310})
            self.assertEqual((await a.expect('error', ref='town_mv'))['code'], 'speed')
            await asyncio.sleep(.27)
            await a.send(t='town_mv', x=6, y=6, activity=None)
            self.assertIsNone((await self.event(b, 'mv', a.pid))['activity'])
            self.assertEqual(calls, [], 'public outdoor movement never touches PostgreSQL or game saves')
        finally:
            self.app.db._run = original
        await asyncio.sleep(.27)
        await a.send(t='town_mv', x=6, y=6, activity=pose('pool'))
        await self.event(b, 'mv', a.pid)
        c = await self.enter('Hoa')
        self.assertEqual(next(p for p in c.room['people'] if p['pid'] == a.pid)['activity'], pose('pool'))

    async def test_outdoor_block_filter_and_new_tab_reset_keep_room_isolation(self):
        token = self.guest('Lan')[0]
        a, b = await self.enter('Lan', token), await self.enter('Minh')
        await a.send(t='town_mv', x=6, y=6, activity=pose())
        self.assertEqual((await self.event(b, 'mv', a.pid))['activity']['kind'], 'fishing')
        another = await self.enter('Lan again', token)
        self.assertEqual((await a.expect('town_left'))['why'], 'other')
        room = self.app.hub.rooms[another.room['room']]
        self.assertNotIn('activity', room.data['people'][a.pid].public())
        with self.store.connect() as db:
            db.execute('INSERT INTO blocks(pid,target,at) VALUES(?,?,?)', (a.pid, b.pid, time.time()))
        town = self.app.by_name['town']
        town._blocks_at = 0
        await town.tick(time.monotonic())
        await self.event(another, 'out', b.pid)
        await self.event(b, 'out', a.pid)
        b.frames.clear()
        await another.send(t='town_mv', x=6, y=6, activity=pose('boat'))
        await asyncio.sleep(.2)
        self.assertFalse(any(e.get('pid') == a.pid for f in b.frames if f['t']=='town' for e in f['ev']))
        await a.call('town_out', 'town_left')
        self.assertIn(a.pid, room.data['people'])
        await another.close()
        await asyncio.sleep(.1)
        self.assertNotIn(a.pid, room.data['people'])
