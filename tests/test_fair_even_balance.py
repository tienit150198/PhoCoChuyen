import json
import random
import unittest
from unittest.mock import patch

from game import fair as fh
from game.engine import GameError, validate_state
from tests.test_fair import FairBase, Dice, OPEN, story


class EvenRates(unittest.TestCase):
    """Owner 07/10: about 50% of luck rounds are won, whatever the price, time or net (a long run of one stall cools)."""
    def test_every_price_time_and_net_has_the_same_base_rate(self):
        for game in fh.CHANCE_GAMES:
            want = fh.XD_BASE if game == 'xd' else fh.LUCK_BASE
            for i in range(100):
                for price in (2, 10, 50, 500, 1000):
                    self.assertEqual(fh.chance_rate(game, OPEN + i*1800, price, 100000), want)
                    j = {}   # the first round of a run
                    self.assertEqual(fh.luck_p(j, None, game, OPEN+i, stake=price), want)

    def test_no_sure_win_after_losses(self):
        # 07/10: the sure win after four losses is gone (bet small four times, then big): a bad stream loses on.
        j = {}
        with patch.object(fh, '_rng', Dice(draws=[.999]*100)):
            results = [fh._draw_luck(j, 'xs', fh.LUCK_BASE) for _ in range(50)]
        self.assertFalse(any(results))
        self.assertEqual(j['fair_balance']['xs'], -4)   # still within the older validator's bound
        with patch.object(fh, '_rng', Dice(draws=[fh.LUCK_BASE - .001])):
            self.assertTrue(fh._draw_luck(j, 'xs', fh.LUCK_BASE))   # a draw under the rate still wins

    def test_a_winning_streak_cools_to_the_floor_never_below(self):
        j = {}
        with patch.object(fh, '_rng', Dice(draws=[fh.WIN_P_LOW - .001]*20 + [fh.WIN_P_LOW + .001])):
            results = [fh._draw_luck(j, 'bc', fh.LUCK_BASE) for _ in range(21)]
        self.assertTrue(all(results[:20]))       # a draw under 50% still wins after any streak
        self.assertFalse(results[20])            # the cooled-off rate is exactly the floor
        self.assertEqual(j['fair_balance']['bc'], -1)

    def test_long_run_is_50_and_each_game_has_its_own_history(self):
        j = {}
        with patch.object(fh, '_rng', random.Random(92026)):
            results = [fh._draw_luck(j, 'bc', fh.LUCK_BASE) for _ in range(100000)]
        self.assertAlmostEqual(sum(results)/len(results), fh.WIN_P, delta=.005)
        self.assertNotIn('xs', j['fair_balance'])
        self.assertTrue(all(-4 <= v <= 4 for v in j['fair_balance'].values()))   # the older validator's bound
        j = json.loads(json.dumps(j))
        with patch.object(fh, '_rng', Dice(draws=[.999])):
            self.assertFalse(fh._draw_luck(j, 'xs', fh.LUCK_BASE))


class EvenCommands(FairBase):
    def test_bau_cua_dice_are_honest_no_sure_win_after_losses(self):
        # Owner 06/10: honest dice for bầu cua. Ten crab bets on dice without a crab all lose (no streak rescue),
        # and dice with crabs win whatever the past rounds were.
        s = story(10000)
        for i in range(10):
            self.dice(Dice(faces=['bau', 'tom', 'ga'], draws=[.999]))
            s, result = self.act(s, 'fair_bc', bets={'cua': 10})
            self.assertEqual(result['fair']['dice'], ['bau', 'tom', 'ga'])
            self.assertLess(result['fair']['net'], 0)
            s = json.loads(json.dumps(s)); validate_state(s)
        self.dice(Dice(faces=['cua', 'cua', 'nai'], draws=[.999]))
        s, result = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertEqual(result['fair']['net'], 20)

    def test_invalid_streaks_and_skill_keys_are_rejected(self):
        for invalid in ({'bc': 5}, {'xs': -5}, {'ring': True}, {'kn': 1}):
            s=story(100);s['journey']['fair_balance']=invalid
            with self.assertRaises(GameError):validate_state(s)
