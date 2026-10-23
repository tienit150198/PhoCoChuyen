"""🎪 The Chợ đen golden days (11–13/10, game/fair_golden_days.py) were removed 23/10: no read per round, no public field.
Saves played during the event still hold its display marker `journey['fair_golden_days']`: they keep validating."""
import importlib.util
import json
import unittest

from game import fair as fh
from game.engine import apply_action, public_state, validate_state
from tests.test_fair import OPEN, Dice, FairBase, story


class GoldenDaysGone(FairBase):
    def saved(self):
        s = story(1000)
        s['journey']['fair_golden_days'] = dict(id='fair_golden_days_20261011', starts=int(OPEN))   # as 2.4.x wrote it
        return json.loads(json.dumps(s))

    def test_a_save_with_the_old_marker_still_validates_and_plays(self):
        s = self.saved()
        validate_state(s)
        self.dice(Dice(draws=[.99]))
        s, result = apply_action(s, None, 'fair_xd', dict(side='chan', stake=10))
        validate_state(s)
        self.assertIn('fair_golden_days', s['journey'])   # kept as it was, never read
        self.assertNotIn('golden_days', public_state(s)['fair'])

    def test_the_ordinary_draw_only(self):
        self.assertEqual(fh.luck_p(self.saved()['journey'], None, 'xd', OPEN, stake=20), fh.BASES['xd'])

    def test_the_module_is_gone(self):
        self.assertIsNone(importlib.util.find_spec('game.fair_golden_days'))
        self.assertFalse(hasattr(fh, 'golden'))


if __name__ == '__main__':
    unittest.main()
