"""Spam rounds (owner 11/10, night): past 50 rounds of 50k+ in one day the police come far more often. The golden-days
odds that lived here went with the event (removed 23/10, tests/test_fair_golden_days_gone.py)."""
import unittest

from tests.test_fair import OPEN


class SpamRounds(unittest.TestCase):
    """Owner 11/10 (night): past 50 rounds of 50k+ in one day the police come far more often; smaller rounds don't count."""

    def test_counter_counts_only_big_rounds_and_resets_daily(self):
        from game import fair_bm as bm
        j = {}
        self.assertEqual(bm.count_big(j, OPEN, 49_999), 0)
        self.assertNotIn(bm.SPAM_KEY, j)
        for n in range(1, 4):
            self.assertEqual(bm.count_big(j, OPEN, 50_000), n)
        self.assertEqual(bm.count_big(j, OPEN + 86400, 50_000), 1)
        bm.validate(j)

    def test_odds_jump_after_the_fiftieth(self):
        from game import fair_bm as bm
        base = bm.arrest_p({'net': 0}, 50_000)
        self.assertEqual(bm.arrest_p({'net': 0}, 50_000, 50), base)
        self.assertAlmostEqual(bm.arrest_p({'net': 0}, 50_000, 51), base + .20)
        self.assertAlmostEqual(bm.arrest_p({'net': 0}, 50_000, 61), base + .30)
        self.assertEqual(bm.arrest_p({'net': 0}, 50_000, 10**6), bm.ARREST_CAP)
