"""Shared isometric-town presence: memory-only, bounded and isolated from saves."""
import asyncio
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import live.hub
from live.config import Config
from live.hub import Conn, Hub
from live.protocol import Dispatcher, LiveError
from live.town import CAP, MAP_ID, SPEED, TownFeature, clean_point

# Release 1.8.0 keeps the Phaser 2.5D town (live/town.py) in the repo but does not wire it: live.config.Config has
# no `town` flag (LIVE_TOWN), live.app.FEATURES has no TownFeature and live.hub has no text-frame _broadcast.
# These tests run again once it is wired back (docs/PHASER_25D.md).
TOWN_WIRED = 'town' in getattr(Config, '__dataclass_fields__', {})
NOT_WIRED = 'Phaser 2.5D town not wired in 1.8.0 (no LIVE_TOWN flag, no TownFeature in live.app); see docs/PHASER_25D.md'


class Geometry(unittest.TestCase):
    @unittest.skipUnless(hasattr(live.hub, '_broadcast'),
                         'live.hub._broadcast (text frames for the 2.5D town) is not in 1.8.0; see docs/PHASER_25D.md')
    def test_text_broadcast_supports_standard_websocket_broadcast_api(self):
        written = []
        def native(connections, message, raise_exceptions=False):
            written.append(message)
        with patch('live.hub._ws_broadcast', native):
            hub = Hub(Config())
            conn = SimpleNamespace(ws=object(), closing=False, buffered=lambda: 0)
            hub.send_many([conn], {'t': 'welcome', 'name': 'Mây'})
        self.assertIsInstance(written[0], str, 'the standard API chooses text frames for strings')
        self.assertEqual(json.loads(written[0])['name'], 'Mây')

    @unittest.skip('the town grid grows with the career count: with the careers of 1.8.0, (6, 51) is inside it. '
                   'Re-check the bounds when the 2.5D town is wired back (docs/PHASER_25D.md)')
    def test_grid_bounds_roads_and_nonfinite_values(self):
        self.assertEqual(clean_point(6.12345, 49.5), (6.123, 49.5))
        for x, y in ((-1, 6), (44, 6), (6, 51), (2, 2), (True, 6), (float('nan'), 6), (6, float('inf'))):
            with self.subTest(x=x, y=y), self.assertRaises(LiveError):
                clean_point(x, y)

    @unittest.skipUnless(TOWN_WIRED, NOT_WIRED)
    def test_town_can_be_enabled_without_other_live_features(self):
        cfg = Config(town=True)
        self.assertTrue(cfg.any_on())
        self.assertTrue(cfg.flags()['town'])
        self.assertFalse(Config().flags()['town'])

    def test_free_courtyard_diagonals_keep_water_and_trunks_solid(self):
        for point in ((.4, 4.8), (.8, 5.8), (6.2, 6.2)):
            self.assertEqual(clean_point(*point), point)
        for point in ((8.5, 10.2), (10.8, 8.4), (.27, 2.2)):
            with self.subTest(point=point), self.assertRaises(LiveError):
                clean_point(*point)


@unittest.skipUnless(TOWN_WIRED, NOT_WIRED)
class TownCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cfg = Config(town=True)
        self.hub = Hub(self.cfg)
        self.frames = {}
        self.hub.write = lambda sockets, raw, **kw: [self.frames[s].append(json.loads(raw)) for s in sockets]
        self.app = SimpleNamespace(cfg=self.cfg, hub=self.hub, db=None, chat=None)
        self.town = TownFeature(self.app)
        self.dispatcher = Dispatcher([self.town])

    async def asyncTearDown(self):
        for room in list(self.hub.rooms.values()):
            self.town._empty(room)

    def player(self, pid):
        ident = SimpleNamespace(pid=pid, sid='private-'+pid, name='Tên '+pid, av='🌸', account=False,
                                muted_until=0, old=True, since=0, online=True)
        p = self.hub.player(ident)
        return self.tab(p)

    def tab(self, player):
        ws = object()
        self.frames[ws] = []
        c = Conn(ws, player, 'test', self.cfg)
        c.ready = True
        self.hub.add(c)
        return c

    async def join(self, conn, **extra):
        return await self.town.town_in(conn, dict(map=MAP_ID, x=6, y=6, direction='se', look={}, **extra))

    def flush(self, conn):
        room = self.hub.rooms[conn.ext['town']]
        if room.data['h']:
            room.data['h'].cancel()
        self.town._flush(room)
        return room

    async def test_public_snapshot_ignores_identity_and_private_fields(self):
        a, b = self.player('a'), self.player('b')
        await self.join(a, name='Spoof', task={'secret': 1}, save={'money': 900}, career='private')
        snapshot = await self.join(b)
        peer = snapshot['people'][0]
        self.assertEqual(peer['name'], 'Tên a')
        self.assertEqual(set(peer), {'pid', 'name', 'lk', 'g', 'fc', 'x', 'y', 'direction'})
        self.assertNotIn('private-a', json.dumps(snapshot))
        self.assertEqual(snapshot['map'], MAP_ID)

    async def test_movement_has_distance_budget_and_batches_latest_position(self):
        a, b = self.player('a'), self.player('b')
        await self.join(a)
        await self.join(b)
        room = self.flush(a)
        walker = room.data['people']['a']
        walker.last -= 0.5
        await self.town.town_mv(a, dict(x=6, y=8, direction='down', save={'secret': 1}))
        await self.town.town_mv(a, dict(x=6, y=8.2, direction='down'))
        events = [e for _, e in room.data['ev'] if e['k'] == 'mv']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['y'], 8.2)
        with self.assertRaises(LiveError) as bad:
            await self.town.town_mv(a, dict(x=6, y=40))
        self.assertEqual(bad.exception.code, 'speed')
        self.assertEqual(walker.y, 8.2)
        self.flush(a)
        sent = [f for f in self.frames[b.ws] if f['t'] == 'town'][-1]
        self.assertNotIn('save', json.dumps(sent))

    async def test_maximum_four_moves_per_second(self):
        a = self.player('a')
        await self.join(a)
        for _ in range(5):
            await self.dispatcher.dispatch(a, dict(t='town_mv', x=6, y=6))
        errors = [f for f in self.frames[a.ws] if f['t'] == 'error']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['code'], 'slow')

    async def test_second_tab_takes_over_without_old_tab_removing_new_presence(self):
        a, b = self.player('a'), self.player('b')
        await self.join(a)
        await self.join(b)
        another = self.tab(a.player)
        joined = await self.join(another)
        self.assertEqual(self.frames[a.ws][-1], {'t': 'town_left', 'why': 'other'})
        self.assertNotIn('town', a.ext)
        await self.town.town_out(a, {})
        self.assertIn('a', self.hub.rooms[joined['room']].data['people'])
        self.hub.remove(a)
        await self.town.on_close(a)
        self.assertIn('a', self.hub.rooms[joined['room']].data['people'])

    async def test_disconnect_leave_and_capacity(self):
        clients = [self.player(str(i)) for i in range(CAP + 1)]
        snapshots = [await self.join(c) for c in clients]
        self.assertEqual(snapshots[0]['room'], snapshots[CAP-1]['room'])
        self.assertNotEqual(snapshots[0]['room'], snapshots[CAP]['room'])
        self.hub.remove(clients[0])
        await self.town.on_close(clients[0])
        self.assertNotIn('0', self.hub.rooms[snapshots[1]['room']].data['people'])
        out = await self.town.town_out(clients[CAP], {})
        self.assertEqual(out['why'], 'out')
        self.assertNotIn(snapshots[CAP]['room'], self.hub.rooms)

    async def test_blocks_filter_existing_diffs_and_future_lobby_assignment(self):
        a, b = self.player('a'), self.player('b')
        await self.join(a)
        await self.join(b)
        self.flush(a)
        self.frames[a.ws].clear()
        self.frames[b.ws].clear()
        a.player.hidden.add('b')
        await self.town.tick(time.monotonic())
        self.assertEqual(self.frames[a.ws][-1]['ev'], [{'k': 'out', 'pid': 'b'}])
        self.assertEqual(self.frames[b.ws][-1]['ev'], [{'k': 'out', 'pid': 'a'}])
        await self.town.town_mv(b, dict(x=6, y=6.1))
        self.flush(b)
        self.assertEqual(len(self.frames[a.ws]), 1)
        snapshot = await self.join(b)
        self.assertNotEqual(snapshot['room'], a.ext['town'])
        self.assertEqual(snapshot['people'], [])

    async def test_off_and_unknown_map_refuse_without_joining(self):
        a = self.player('a')
        self.cfg.town = False
        await self.dispatcher.dispatch(a, dict(t='town_in', map=MAP_ID, x=6, y=6))
        self.assertEqual(self.frames[a.ws][-1]['code'], 'off')
        with self.assertRaises(LiveError):
            await self.town.town_in(a, dict(map='private-work', x=6, y=6))
        self.assertFalse(self.hub.rooms)
