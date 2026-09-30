"""Tiền đền: the one compensation factor (game/compensation.py) lowers what the player pays out."""
import unittest
from unittest import mock

from game import abandon as ab
from game import compensation as cf
from game.compensation import comp
from game.guide_content import GROUPS
from game.incident_content import INDEX as INCIDENTS
from game.careers import farm, homestay, repair, delivery
from tests.test_abandon import open_place, start_first, story
from tests.test_happenings import fire, open_day


class Helper(unittest.TestCase):
    def test_rounding(self):
        self.assertLess(cf.COMPENSATION_FACTOR, 1)
        self.assertEqual([comp(x) for x in (-5, 0, 1, 2, 5, 10, 12, 15, 20, 25, 120)], [0, 0, 1, 2, 4, 8, 10, 12, 16, 20, 96])
        for x in range(1, 500):
            self.assertTrue(1 <= comp(x) <= x and comp(x) <= comp(x + 1), x)

    def test_factor_one_changes_nothing(self):
        with mock.patch.object(cf, 'COMPENSATION_FACTOR', 1.0):
            self.assertEqual([comp(x) for x in (1, 7, 40, 120)], [1, 7, 40, 120])


class Applied(unittest.TestCase):
    def test_happening_you_must_pay(self):
        def facts(factor):
            with mock.patch.object(cf, 'COMPENSATION_FACTOR', factor):
                return fire(open_day('salon'), 'salon', 'dye_stain')['facts']['comp']
        full = facts(1.0)
        self.assertGreater(full, 1)
        self.assertEqual(facts(0.8), comp(full))

    def test_abandon_fine(self):
        def fine(factor):
            s = open_place(story(), 'grocery')
            start_first(s, 'grocery')
            with mock.patch.object(cf, 'COMPENSATION_FACTOR', factor):
                return ab.assess(s, 'grocery')['fine']
        full = fine(1.0)
        self.assertGreater(full, 1)
        self.assertEqual(fine(0.8), comp(full))

    def test_incident_lines_and_hints(self):
        pays = {o['id']: o['pay'] for o in INCIDENTS['dye_allergy']['options']}
        self.assertEqual(pays['care'], [('fund', -comp(25), 'compensation')])
        self.assertEqual(pays['pay_all'], [('fund', -comp(90), 'compensation')])
        hint = next(o['hint'] for o in INCIDENTS['dye_allergy']['options'] if o['id'] == 'pay_all')
        self.assertEqual(hint, f'Quỹ −{comp(90)} xu')
        # Other categories keep their amounts (a fine is not đền); an extortion payoff keeps the demanded 100 xu.
        self.assertIn(('wallet', -30, 'fine'), next(o for o in INCIDENTS['defamation']['options'] if o['id'] == 'refuse')['pay'])
        self.assertEqual(next(o for o in INCIDENTS['extortion_bug']['options'] if o['id'] == 'pay')['pay'], [('fund', -100, 'compensation')])

    def test_career_den_and_texts(self):
        self.assertEqual(farm.BEE_FINE, comp(15))
        own = next(o for x in homestay.DESK if x['id'] == 'lostwrong' for o in x['options'] if o['id'] == 'own')
        self.assertEqual((own['effects']['money'], own['hint']), (-comp(25), f'−{comp(25)} xu'))
        leak = next(o for x in repair.DESK if x['id'] == 'leak_found' for o in x['options'] if o['id'] == 'apologize')
        self.assertEqual((leak['effects']['money'], leak['hint']), (-comp(20), f'{comp(20)} xu'))
        bump = next(o for x in delivery.EVENTS if x['id'] == 'DE-BUMP' for o in x['options'] if o['id'] == 'pay')
        self.assertEqual(bump['effects']['money'], -comp(12))
        self.assertIn(f'{comp(12)} xu', bump['label'])
        guide = ' '.join(p for g in GROUPS for t in g['topics'] if t['id'] == 'abandon' for p in t['points'])
        self.assertIn(f'tối đa {comp(ab.FINE_MAX)} xu', guide)
        self.assertIn(f'ít nhất {comp(ab.FINE_MIN)} xu', guide)


if __name__ == '__main__':
    unittest.main()
