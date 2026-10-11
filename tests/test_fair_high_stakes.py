"""Golden-days odds depend on this round's stake, never wallet or past profit."""
import random
from unittest import mock

from game import engine, fair as fh, fair_golden_days as golden
from tests.test_fair import OPEN, Dice, FairBase, story


class GoldenHighStakes(FairBase):
    def setUp(self):
        super().setUp()
        golden._starts.set(int(OPEN))
        self.addCleanup(golden.clear)

    def test_threshold_starts_at_300000_per_round(self):
        for stake, expected in [(10, .70), (299000, .70), (299999, .70), (300000, .40),
                                (300001, .40), (1000000, .40)]:
            with self.subTest(stake=stake):
                self.assertEqual(fh.luck_p({}, None, 'xd', OPEN, stake=stake), expected)

    @mock.patch.object(fh, 'GRACE_ROUNDS', 1000)
    def test_alternating_stakes_and_large_wallet_do_not_carry_the_boost(self):
        s = story(10000000)
        for stake, won in [(299999, True), (300000, False), (10, True), (1000000, False)]:
            self.dice(Dice(draws=[.99, .50]))  # No raid; the same draw straddles the two rates.
            before = s['journey']['wallet']
            s, result = self.act(s, 'fair_xd', side='chan', stake=stake)
            self.assertEqual(result['fair']['net'], stake if won else -stake)
            self.assertEqual(s['journey']['wallet'], before + result['fair']['net'])
            engine.validate_state(s)

    def test_large_stake_draw_boundary_survives_existing_streak_and_spam(self):
        j = dict(fair_balance={'xd': fh.STREAK})
        for n in range(40):
            p = fh.luck_p(j, None, 'xd', OPEN + n, stake=300001)
            self.assertEqual(p, .40)
            with mock.patch.object(fh, '_rng', Dice(draws=[.399999, .40])):
                self.assertTrue(fh._draw_luck(j, 'xd', p))
                self.assertFalse(fh._draw_luck(j, 'xd', p))

    def test_expired_event_retains_ordinary_rules(self):
        t = OPEN + golden.DURATION
        self.assertEqual(fh.luck_p({}, None, 'xd', t, stake=1000000), fh.BASES['xd'])

    def test_large_stake_seeded_distribution_is_40_percent(self):
        self.dice(random.Random(301001))
        j = {}
        wins = sum(fh._draw_luck(j, 'xd', fh.luck_p(j, None, 'xd', OPEN + n / 100, stake=1000000))
                   for n in range(20000))
        self.assertAlmostEqual(wins / 20000, .40, delta=.015)
