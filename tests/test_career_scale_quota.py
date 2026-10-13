import copy
import unittest

from game import career_scale_quota as q
from game.engine import GameError


class ScaleQuotaTests(unittest.TestCase):
    def setUp(self):
        self.s = {'journey': {}}
        self.at = 1791907200

    def test_initial_preview_is_pure_and_first_reservation_gets_one(self):
        before = copy.deepcopy(self.s)
        self.assertEqual(q.public(self.s, self.at)['available'], 1)
        self.assertEqual(self.s, before)
        q.reserve(self.s, 'grocery-1', self.at)
        self.assertEqual(q.public(self.s, self.at)['available'], 0)
        q.start(self.s, 'grocery-1', self.at)
        with self.assertRaises(GameError):
            q.reserve(self.s, 'salon-1', self.at)

    def test_bangkok_midnight_catchup_and_cap(self):
        midnight = (self.at // 86400) * 86400 + 17 * 3600
        q.reserve(self.s, 'grocery-1', midnight - 1)
        q.start(self.s, 'grocery-1', midnight - 1)
        self.assertEqual(q.public(self.s, midnight)['available'], 4)
        self.assertEqual(q.public(self.s, midnight + 10 * 86400)['available'], 12)

    def test_reserved_token_counts_towards_cap_and_cancel_cannot_overfill(self):
        q.reserve(self.s, 'grocery-1', self.at)
        self.assertEqual(q.public(self.s, self.at + 20 * 86400)['available'], 11)
        q.cancel(self.s, 'grocery-1', self.at + 20 * 86400)
        self.assertEqual(q.public(self.s, self.at + 20 * 86400)['available'], 12)

    def test_cross_career_conflict_replays_and_wrong_ids_reject(self):
        q.reserve(self.s, 'grocery-1', self.at)
        for fn, ref in ((q.reserve, 'grocery-1'), (q.reserve, 'salon-1'),
                        (q.start, 'salon-1'), (q.cancel, 'salon-1')):
            before = copy.deepcopy(self.s)
            with self.assertRaises(GameError):
                fn(self.s, ref, self.at)
            self.assertEqual(self.s, before)
        q.cancel(self.s, 'grocery-1', self.at)
        self.assertEqual(q.public(self.s, self.at)['available'], 1)

    def test_clock_back_does_not_reissue_and_career_days_irrelevant(self):
        q.reserve(self.s, 'grocery-1', self.at)
        q.start(self.s, 'grocery-1', self.at)
        self.s['journey']['life_day'] = 99999
        self.assertEqual(q.public(self.s, self.at - 86400)['available'], 0)

    def test_validator_rejects_bool_extra_keys_and_over_cap(self):
        q.reserve(self.s, 'grocery-1', self.at)
        q.validate(self.s)
        for key, value in [('day', True), ('tokens', 12), ('v', False),
                           ('reserved', 'x' * 100), ('unknown', 1)]:
            s = copy.deepcopy(self.s)
            s['journey'][q.KEY][key] = value
            with self.assertRaises(GameError):
                q.validate(s)

    def test_resets_keep_spent_allowance_and_only_refund_discarded_reservation(self):
        q.reserve(self.s, 'grocery-1', self.at)
        fresh = {'journey': {}}
        q.carry_reset(self.s, fresh, 'salon')
        self.assertEqual(fresh['journey'][q.KEY], self.s['journey'][q.KEY])
        q.carry_reset(self.s, fresh, 'grocery')
        self.assertEqual(q.public(fresh, self.at)['available'], 1)
        self.assertIsNone(q.public(fresh, self.at)['reserved'])
        q.start(self.s, 'grocery-1', self.at)
        q.carry_reset(self.s, fresh)
        self.assertEqual(q.public(fresh, self.at)['available'], 0)


if __name__ == '__main__':
    unittest.main()
