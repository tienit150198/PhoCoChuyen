"""Paid fair games accept 1,000 xu while preserving the combined round ceiling."""
import json
import random
from game import fair as fair, fair_knife as knife, fair_scratch as scratch
from game.engine import GameError, validate_state
from tests.test_fair import Dice, FairBase, story


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

    def test_bau_cua_and_chieu_trong_take_any_stake_the_wallet_holds(self):   # owner 08/10
        self.dice(random.Random(2))
        for command, args in (('fair_bc', dict(bets={'cua': 5000, 'ca': 2501})), ('fair_xd', dict(side='chan', stake=7777))):
            with self.subTest(command=command):
                state, _ = self.act(story(10**5), command, **args)
                validate_state(json.loads(json.dumps(state)))
        for command, args in (('fair_bc', dict(bets={'cua': fair.STAKE_MAX, 'ca': 1})),
                              ('fair_xd', dict(side='chan', stake=fair.STAKE_MAX + 1))):
            with self.subTest(command=command), self.assertRaises(GameError) as e:
                self.act(story(10**7), command, **args)
            self.assertEqual(e.exception.code, 'fair_big')

    def test_fixed_menus_keep_their_saved_bounds(self):   # their stakes are saved and checked by older servers
        for command, args in (
            ('fair_kn_start', dict(stake=1001)),
            ('fair_xs', dict(price=1001)),
            ('fair_loto_buy', dict(tier='nghin', n=1, cl=['chan', 2])),
        ):
            with self.subTest(command=command), self.assertRaises(GameError):
                self.act(story(10000), command, **args)

    def test_catalogues_include_old_prices_and_new_ceiling(self):
        self.assertEqual((fair.BC_MAX, fair.XD_MAX, fair.ROUND_MAX), (fair.STAKE_MAX, fair.STAKE_MAX, 1000))
        self.assertEqual(fair.LOTO_TIERS['dac_biet'], 500)
        self.assertEqual(fair.LOTO_TIERS['nghin'], 1000)
        for choices in (knife.STAKES, scratch.TIERS, *fair.STAKE_TIERS.values()):
            self.assertIn(500, choices)
            self.assertEqual(max(choices), 1000)


class TenMillionStake(FairBase):
    """Owner 11/10 (later) "mức cược 1 ván không giới hạn, có thể hơn 1 triệu": up to STAKE_MAX = 10,000,000 a round;
    a payout moves Sổ ví rows of at most 10**7 xu (fair._pay_big), the saves' own bound; NET_SAFE / WALLET_SAFE keep
    today's net and the wallet far from theirs."""

    def fair_rows(self, state):
        return [row['amount'] for row in state['journey']['history'] if row['kind'] == 'fair']

    def test_the_bounds(self):
        self.assertEqual((fair.STAKE_MAX, fair.NET_SAFE, fair.WALLET_SAFE), (10**7, 5 * 10**8, 9 * 10**8))

    def test_five_million_xoc_dia_wins_split_into_valid_rows(self):
        state = story(3 * 10**7)
        for n in range(1, 4):
            self.dice(Dice(draws=[.99, 0]))   # no dẹp chiếu (a big stake is watched), then a won round
            state, result = self.act(state, 'fair_xd', side='chan', stake=5 * 10**6)
            self.assertEqual(result['fair']['net'], 5 * 10**6)
            self.assertEqual(state['journey']['wallet'], 3 * 10**7 + n * 5 * 10**6)
            rows = self.fair_rows(state)
            self.assertEqual(sum(rows), n * 5 * 10**6)
            self.assertTrue(all(abs(a) <= 10**7 for a in rows), rows)
            validate_state(json.loads(json.dumps(state)))
        self.assertEqual(self.fair_rows(state), [10**7, 5 * 10**6])   # the row fills up to 10**7, then a new one
        self.assertEqual(state['journey']['fair']['net'], 15 * 10**6)

    def test_a_bao_on_a_big_stake_takes_several_rows(self):
        state = story(3 * 10**7)
        self.dice(Dice(faces=['cua'] * 3))
        state, result = self.act(state, 'fair_bc', bets={'cua': 2 * 10**6})
        delta = fair.BAO * 2 * 10**6
        self.assertEqual(state['journey']['wallet'], 3 * 10**7 + delta)
        rows = self.fair_rows(state)
        self.assertEqual(sum(rows), delta)
        self.assertEqual(rows, [10**7] * (delta // 10**7))
        validate_state(json.loads(json.dumps(state)))

    def test_ten_million_is_the_most_a_round_takes(self):
        self.dice(Dice(draws=[.99, .99]))
        state, result = self.act(story(2 * 10**7), 'fair_xd', side='chan', stake=10**7)
        self.assertEqual(result['fair']['net'], -10**7)
        validate_state(json.loads(json.dumps(state)))
        with self.assertRaises(GameError) as e:
            self.act(story(2 * 10**7), 'fair_xd', side='chan', stake=10**7 + 1)
        self.assertEqual(e.exception.code, 'fair_big')

    def test_a_wallet_near_its_bound_is_told_enough(self):
        rich = 89 * 10**7
        with self.assertRaises(GameError) as e:   # 890M + 1M × BAO reaches WALLET_SAFE
            self.act(story(rich), 'fair_xd', side='chan', stake=10**6)
        self.assertEqual((e.exception.code, str(e.exception)), ('fair_enough', fair.ENOUGH))
        self.dice(Dice(draws=[.99, .99]))
        state, _ = self.act(story(rich), 'fair_xd', side='chan', stake=10**5)
        validate_state(json.loads(json.dumps(state)))
