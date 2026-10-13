"""Room admission remains bounded across the treasure lease write await."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from live.config import Config
from live.hub import Conn, Hub, Room
from live.protocol import LiveError
from live.scale_sites import SITE_CAP, SITE_PREFIX
from live.town import TownFeature


class SiteCapacity(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cfg = Config(town=True)
        self.hub = Hub(self.cfg)
        self.hub.write = lambda sockets, raw, **kw: None
        self.app = SimpleNamespace(cfg=self.cfg, hub=self.hub, db=None, chat=None, by_name={})
        self.town = TownFeature(self.app)
        async def read(owner, career, site):
            return dict(cid=career, site=dict(id=site, name='Test', public=True), resources=[])
        self.town._site_read = read
        self.key = dict(owner='0123456789abcdef', career='grocery', site='base')

    async def asyncTearDown(self):
        for room in list(self.hub.rooms.values()):
            self.town._empty(room)

    def player(self, n):
        ident = SimpleNamespace(pid=f'{n:016x}', sid=f'test-{n}', name=f'Player {n}', av='🌸',
                                account=False, muted_until=0, old=True, since=0, online=True)
        conn = Conn(object(), self.hub.player(ident), 'test', self.cfg)
        conn.ready = True
        self.hub.add(conn)
        return conn

    def barrier(self):
        arrived, release = 0, asyncio.Event()
        async def leave(conn):
            nonlocal arrived
            arrived += 1
            if arrived == 2:
                release.set()
            await release.wait()
        self.app.by_name['treasure'] = SimpleNamespace(enabled=lambda: True, leave=leave)

    async def test_two_joiners_at_29_cannot_create_a_ghost_walker(self):
        for n in range(1, SITE_CAP):
            await self.town.site_in(self.player(n), self.key)
        a, b = self.player(100), self.player(101)
        self.barrier()
        results = await asyncio.wait_for(asyncio.gather(
            self.town.site_in(a, self.key), self.town.site_in(b, self.key), return_exceptions=True), 2)
        refused = [i for i, result in enumerate(results) if isinstance(result, LiveError)]
        self.assertEqual(len(refused), 1)
        self.assertEqual(results[refused[0]].code, 'full')
        room = self.hub.rooms_with_prefix(SITE_PREFIX)[0]
        self.assertEqual(len(room.data['people']), SITE_CAP)
        self.assertEqual(len(room.conns), SITE_CAP)
        self.assertEqual(set(room.data['people']), {c.player.pid for c in room.conns})
        denied = (a, b)[refused[0]]
        self.assertNotIn('town', denied.ext)
        self.assertNotIn('town', denied.player.ext)

    async def test_simultaneous_new_sites_obey_global_room_limit(self):
        a, b = self.player(100), self.player(101)
        self.barrier()
        with patch('live.scale_sites.SITE_ROOMS_MAX', 1):
            results = await asyncio.wait_for(asyncio.gather(
                self.town.site_in(a, self.key),
                self.town.site_in(b, dict(self.key, site='branch-1')), return_exceptions=True), 2)
        self.assertEqual(sum(isinstance(result, LiveError) and result.code == 'full' for result in results), 1)
        rooms = self.hub.rooms_with_prefix(SITE_PREFIX)
        self.assertEqual(len(rooms), 1)
        self.assertEqual(sum(len(room.conns) for room in rooms), 1)
        self.assertTrue(all(room.data['people'] for room in rooms))

    async def test_room_add_refusal_cannot_publish_a_walker_or_keep_empty_room(self):
        player = self.player(1)
        with patch.object(Room, 'add', return_value=False):
            with self.assertRaises(LiveError) as caught:
                await self.town.site_in(player, self.key)
        self.assertEqual(caught.exception.code, 'full')
        self.assertEqual(self.hub.rooms_with_prefix(SITE_PREFIX), [])
        self.assertNotIn('town', player.ext)
        self.assertNotIn('town', player.player.ext)
