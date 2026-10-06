"""Outdoor poses use town's existing rate/batching and never carry private rounds."""
import json
import unittest

from live.protocol import LiveError
from tests import test_live_town as town_tests


def pose(kind='fishing', **fields):
    return dict(kind=kind, x=84, y=180, direction='ne', phase='walk', action=None,
                moving=False, **fields)


@unittest.skipUnless(town_tests.TOWN_WIRED, town_tests.NOT_WIRED)
class ActivityCase(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = town_tests.TownCase.asyncSetUp
    asyncTearDown = town_tests.TownCase.asyncTearDown
    player = town_tests.TownCase.player
    tab = town_tests.TownCase.tab
    join = town_tests.TownCase.join
    flush = town_tests.TownCase.flush

    async def test_pose_in_snapshot_and_batched_moves_contains_only_public_fields(self):
        a, b = self.player('a'), self.player('b')
        await self.join(a)
        sample = {**pose(), 'round': {'id': 'secret'}, 'stats': {'fish': 999}, 'reward': 900}
        await self.town.town_mv(a, dict(x=6, y=6, activity=sample))
        snapshot = await self.join(b)
        self.assertEqual(snapshot['people'][0]['activity'], pose())
        self.flush(a)
        await self.town.town_mv(a, dict(x=6, y=6, activity={**pose(), 'action': 'cast'}))
        room = self.flush(a)
        event = self.frames[b.ws][-1]['ev'][0]
        self.assertEqual(event['activity']['action'], 'cast')
        self.assertNotIn('secret', json.dumps(event))
        self.assertNotIn('reward', json.dumps(room.data['people']['a'].public()))
        await self.town.town_mv(a, dict(x=6, y=6, activity=None))
        self.flush(a)
        self.assertIsNone(self.frames[b.ws][-1]['ev'][0]['activity'])
        self.assertNotIn('activity', room.data['people']['a'].public())

    async def test_invalid_samples_reject_atomically_without_changing_town_position(self):
        a = self.player('a')
        await self.join(a)
        await self.town.town_mv(a, dict(x=6, y=6, activity=pose()))
        walker = self.hub.rooms[a.ext['town']].data['people']['a']
        for fields in ({'x': -1}, {'x': 321}, {'y': 201}, {'x': True}, {'y': float('nan')},
                       {'x': float('inf')}, {'kind': 'work'}, {'phase': 'boat'},
                       {'direction': 'north'}, {'action': 'reward'}, {'moving': 'yes'}):
            with self.subTest(fields=fields), self.assertRaises(LiveError):
                await self.town.town_mv(a, dict(x=6, y=6.1, activity={**pose(), **fields}))
            self.assertEqual(walker.y, 6)
            self.assertEqual(walker.public()['activity'], pose())

    async def test_activity_motion_budget_and_finite_board_exit_resets(self):
        a = self.player('a')
        await self.join(a)
        await self.town.town_mv(a, dict(x=6, y=6, activity=pose('boat')))
        room = self.hub.rooms[a.ext['town']]
        walker = room.data['people']['a']
        with self.assertRaises(LiveError) as bad:
            await self.town.town_mv(a, dict(x=6, y=6, activity={**pose('boat'), 'x': 280}))
        self.assertEqual(bad.exception.code, 'speed')
        walker.activity_last -= 1
        await self.town.town_mv(a, dict(x=6, y=6, activity={**pose('boat'), 'y': 154}))
        await self.town.town_mv(a, dict(x=6, y=6, activity={**pose('boat'), 'phase': 'boat', 'x': 104, 'y': 150, 'action': 'board'}))
        # Repeating board while already afloat does not grant teleport credit.
        with self.assertRaises(LiveError):
            await self.town.town_mv(a, dict(x=6, y=6, activity={**pose('boat'), 'phase': 'boat', 'x': 280, 'y': 50, 'action': 'board'}))
        await self.town.town_mv(a, dict(x=6, y=6, activity={**pose('boat'), 'phase': 'return', 'x': 104, 'y': 150}))
        await self.town.town_mv(a, dict(x=6, y=6, activity={**pose('boat'), 'y': 174, 'action': 'exit'}))
        self.assertEqual(walker.public()['activity']['y'], 174)

    async def test_town_and_activity_share_one_four_hz_budget(self):
        a = self.player('a')
        await self.join(a)
        for i in range(5):
            await self.dispatcher.dispatch(a, dict(t='town_mv', x=6, y=6, activity=pose() if i % 2 else None))
        errors = [f for f in self.frames[a.ws] if f['t'] == 'error']
        self.assertEqual([e['code'] for e in errors], ['slow'])

    async def test_blocked_activity_diffs_and_takeover_keep_existing_isolation(self):
        a, b = self.player('a'), self.player('b')
        await self.join(a)
        await self.join(b)
        self.flush(a)
        self.frames[b.ws].clear()
        b.player.hidden.add('a')
        await self.town.town_mv(a, dict(x=6, y=6, activity=pose()))
        self.flush(a)
        self.assertFalse(self.frames[b.ws])
        new = self.tab(a.player)
        await self.join(new)
        await self.town.town_out(a, {})
        self.assertNotIn('activity', self.hub.rooms[new.ext['town']].data['people']['a'].public())

    async def test_join_can_restore_a_valid_public_pose_after_disconnect(self):
        a, b = self.player('a'), self.player('b')
        await self.join(a, activity={**pose('pool'), 'phase': 'pool', 'x': 150, 'y': 100})
        snapshot = await self.join(b)
        self.assertEqual(snapshot['people'][0]['activity']['x'], 150)

    async def test_activity_leave_survives_coalescing_with_an_ordinary_town_move(self):
        a, b = self.player('a'), self.player('b')
        await self.join(a, activity=pose())
        await self.join(b)
        self.flush(a)
        await self.town.town_mv(a, dict(x=6, y=6, activity=None))
        await self.town.town_mv(a, dict(x=6, y=6.1))
        self.flush(a)
        event = self.frames[b.ws][-1]['ev'][0]
        self.assertIn('activity', event)
        self.assertIsNone(event['activity'])
        self.assertEqual(event['y'], 6.1)

    async def test_pool_dock_transition_uses_real_public_entry_coordinates(self):
        a = self.player('a')
        await self.join(a, activity={**pose('pool'), 'y': 154})
        await self.town.town_mv(a, dict(x=6, y=6, activity={**pose('pool'), 'phase': 'pool', 'x': 86, 'y': 142, 'action': 'board'}))
        await self.town.town_mv(a, dict(x=6, y=6, activity={**pose('pool'), 'phase': 'return', 'x': 86, 'y': 142}))
        await self.town.town_mv(a, dict(x=6, y=6, activity={**pose('pool'), 'y': 174, 'action': 'exit'}))
        self.assertEqual(self.hub.rooms[a.ext['town']].data['people']['a'].public()['activity']['y'], 174)
