import json
import random
import unittest
from unittest.mock import patch

from game import fair as fh
from game.engine import GameError, validate_state
from tests.test_fair import FairBase, Dice, OPEN, story


class EvenRates(unittest.TestCase):
    def test_every_price_time_net_and_repeat_has_half_base_rate(self):
        for game in fh.CHANCE_GAMES:
            j = {}
            for i in range(100):
                for price in (2, 10, 50, 500):
                    self.assertEqual(fh.chance_rate(game, OPEN + i*1800, price, 100000), .5)
                    self.assertEqual(fh.luck_p(j, None, game, OPEN+i, stake=price), .5)

    def test_bad_random_stream_cannot_produce_five_consecutive_losses(self):
        self.assertTrue(hasattr(fh, '_draw_luck'))
        for value in (.001, .999):
            j = {}
            with patch.object(fh, '_rng', Dice(draws=[value]*100)):
                results = [fh._draw_luck(j, 'xs', .5) for _ in range(50)]
            self.assertFalse(any(len(set(results[i:i+5])) == 1 for i in range(46)))

    def test_long_run_is_balanced_and_each_game_has_its_own_history(self):
        self.assertTrue(hasattr(fh, '_draw_luck'))
        j = {}
        with patch.object(fh, '_rng', random.Random(92026)):
            results = [fh._draw_luck(j, 'bc', .5) for _ in range(100000)]
        self.assertAlmostEqual(sum(results)/len(results), .5, delta=.005)
        self.assertNotIn('xs', j['fair_balance'])
        j = json.loads(json.dumps(j))
        with patch.object(fh, '_rng', Dice(draws=[.999])):
            self.assertFalse(fh._draw_luck(j, 'xs', .5))


class EvenCommands(FairBase):
    def test_actual_dice_rounds_keep_streak_after_reload(self):
        s = story(10000)
        for i in range(10):
            self.dice(Dice(draws=[.999]))
            s, result = self.act(s, 'fair_bc', bets={'cua': 10})
            self.assertEqual(result['fair']['net'] > 0, i in (4, 9))
            s = json.loads(json.dumps(s)); validate_state(s)

    def test_invalid_streaks_and_skill_keys_are_rejected(self):
        for invalid in ({'bc': 5}, {'xs': -5}, {'ring': True}, {'kn': 1}):
            s=story(100);s['journey']['fair_balance']=invalid
            with self.assertRaises(GameError):validate_state(s)
