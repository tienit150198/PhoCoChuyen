"""Commit hooks use a detached, small before-image, not a second locked save read."""
import unittest
from unittest.mock import patch
from tests.test_scaling import Base
from game import storage, player_service_tasks, home_guests


class SnapshotTests(unittest.TestCase):
    def test_before_image_keeps_hook_inputs_without_aliases(self):
        before = dict(name='Old', journey=dict(story=True, life_day=17,
            home=dict(own=dict(id='home-1', kind='tap_the')),
            quay=dict(stalls=[dict(business=dict(visitor_orders=[dict(id='q1', status='queued')]))])),
            careers=dict(test=dict(tasks=[dict(id='t1', career='test', status='working',
                player_order=dict(id='p1')), dict(id='npc', body='large unused text')],
                player_service_jobs=[dict(id='s1', status='queued')], feed=['unused'])))
        snap = storage._commit_before(before)
        after = storage.tree_copy(before)
        after['careers']['test']['tasks'][0]['status'] = 'completed'
        after['careers']['test']['player_service_jobs'][0]['status'] = 'completed'
        after['journey']['quay']['stalls'][0]['business']['visitor_orders'][0]['status'] = 'completed'
        self.assertEqual(player_service_tasks.transitions(snap, after, 'test', 'finish', {}),
                         [dict(id=k, status='completed') for k in ('p1', 'q1', 's1')])
        self.assertEqual(player_service_tasks.transitions(before, after, 'test', 'finish', {}),
                         player_service_tasks.transitions(snap, after, 'test', 'finish', {}))
        self.assertEqual(home_guests._own(before), home_guests._own(snap))
        self.assertIsNotNone(home_guests._own(snap))
        before['name'] = 'New'
        before['journey']['home']['own']['id'] = 'home-2'
        before['careers']['test']['tasks'][0]['player_order']['id'] = 'changed'
        self.assertEqual(snap['name'], 'Old')
        self.assertEqual(snap['journey']['life_day'], 17)
        self.assertEqual(snap['journey']['home']['own']['id'], 'home-1')
        self.assertEqual(snap['careers']['test']['tasks'][0]['player_order']['id'], 'p1')
        self.assertNotIn('feed', snap['careers']['test'])
        self.assertEqual(len(snap['careers']['test']['tasks']), 1)

    def test_before_image_keeps_the_villa_lived_in(self):
        # 🏰 a villa bought in Mua sắm is the home friends are invited to (home_guests._own): the before-image must
        # name the same home, or every command of its owner would look like a move.
        lux = dict(v=1, own={'bt_kinh': dict(d=4, p=500000), 'bt_vuon_da_lat': dict(d=9, p=150000)}, live='bt_kinh',
                   album=['large unused'])
        before = dict(journey=dict(story=True, life_day=17, home=dict(own=dict(id='h1', kind='tap_the')), lux=lux))
        snap = storage._commit_before(before)
        self.assertEqual(home_guests._own(snap), dict(id='estate:bt_kinh:4', kind='bt_kinh'))
        self.assertEqual(home_guests._own(before), home_guests._own(snap))
        self.assertEqual(snap['journey']['lux'], dict(live='bt_kinh', own={'bt_kinh': dict(d=4)}))
        lux['live'] = None
        snap = storage._commit_before(before)
        self.assertEqual(home_guests._own(snap), dict(id='h1', kind='tap_the'))
        self.assertEqual(home_guests._own(before)['id'], 'h1')
        for bad in ('x', dict(live='bt_kinh', own=[]), dict(live=3, own={}), dict(live='gone', own={})):
            before['journey']['lux'] = bad
            self.assertEqual(home_guests._own(storage._commit_before(before))['id'], 'h1')


class CommitReadTests(Base):
    def test_successful_command_parses_save_once(self):
        with patch.object(self.store, 'parse_state', wraps=self.store.parse_state) as parse:
            out = self.cmd('single-parse-01', 0, 'start_day')
        self.assertEqual(out['revision'], 1)
        self.assertEqual(parse.call_count, 1)

    def test_locked_fallback_parses_save_once(self):
        with patch.object(storage, 'OPTIMISTIC_TRIES', 0), patch.object(
                self.store, 'parse_state', wraps=self.store.parse_state) as parse:
            out = self.cmd('locked-parse-01', 0, 'start_day')
        self.assertEqual(out['revision'], 1)
        self.assertEqual(parse.call_count, 1)


if __name__ == '__main__':
    unittest.main()
