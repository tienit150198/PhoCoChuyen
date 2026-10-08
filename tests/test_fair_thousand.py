"""Paid fair games accept 1,000 xu while preserving the combined round ceiling."""
import json
import random
from game import fair as fair, fair_knife as knife, fair_scratch as scratch
from game.engine import GameError, validate_state
from tests.test_fair import FairBase, story


class ThousandStake(FairBase):
    def test_all_paid_games_accept_ceiling_and_save(self):
        self.dice(random.Random(1))
        for command, args in (
            ('fair_bc', dict(bets={'cua': 500, 'ca': 500})),
            ('fair_xd', dict(side='chan', stake=1000)),
            ('fair_kn_start', dict(stake=1000)),
            ('fair_xs', dict(price=1000)),
            ('fair_loto_buy', dict(tier='nghin', n=1)),
            ('fair_loto_buy', dict(tier='dac_biet', n=2)),   # 2 × 500 (no side bets since 08/10: SIDE_OPEN)
        ):
            with self.subTest(command=command, args=args):
                state, _ = self.act(story(10000), command, **args)
                validate_state(json.loads(json.dumps(state)))

    def test_ceiling_is_total_not_per_selection(self):
        for command, args in (
            ('fair_bc', dict(bets={'cua': 500, 'ca': 501})),
            ('fair_xd', dict(side='chan', stake=1001)),
            ('fair_kn_start', dict(stake=1001)),
            ('fair_xs', dict(price=1001)),
            ('fair_loto_buy', dict(tier='nghin', n=1, cl=['chan', 2])),
        ):
            with self.subTest(command=command), self.assertRaises(GameError):
                self.act(story(10000), command, **args)

    def test_catalogues_include_old_prices_and_new_ceiling(self):
        self.assertEqual((fair.BC_MAX, fair.XD_MAX, fair.ROUND_MAX), (1000, 1000, 1000))
        self.assertEqual(fair.LOTO_TIERS['dac_biet'], 500)
        self.assertEqual(fair.LOTO_TIERS['nghin'], 1000)
        for choices in (knife.STAKES, scratch.TIERS, *fair.STAKE_TIERS.values()):
            self.assertIn(500, choices)
            self.assertEqual(max(choices), 1000)
