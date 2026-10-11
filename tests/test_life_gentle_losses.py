"""Life-story scams respect the same liquid-wallet ceiling as other theft."""
import unittest

from game import life as lf
from game.loss_limits import bounded_loss
from tests.test_life import L, state


class LifeScamLosses(unittest.TestCase):
    def test_every_authored_scam_preserves_reserve_and_actual_receipt(self):
        for story in lf.HARD:
            if story['cat'] != 'lua' or not story['loss']:
                continue
            for wallet in (0, 1, 99, 100, 101, 999, 10000, 10000000):
                with self.subTest(story=story['id'], wallet=wallet):
                    s = state(wallet=wallet)
                    expected = bounded_loss(wallet, story['loss'])
                    card = lf._fire_hard(s, L(s), story, 6, 'teacher')
                    self.assertEqual(s['journey']['wallet'], wallet - expected)
                    self.assertEqual(card['loss'], expected)
                    self.assertEqual(card['money'], -expected)

    def test_non_scam_story_cost_is_unchanged(self):
        story = next(x for x in lf.HARD if x['cat'] == 'xui' and x['loss'])
        s = state(wallet=1000)
        card = lf._fire_hard(s, L(s), story, 6, 'teacher')
        self.assertEqual(card['loss'], story['loss'])
        self.assertEqual(s['journey']['wallet'], 1000 - story['loss'])


if __name__ == '__main__':
    unittest.main()
