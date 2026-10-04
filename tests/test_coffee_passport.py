"""Feedback #150/#151: quicker bar timers and the real path to the fair badge."""
import copy
import json
import subprocess
import unittest
from game.engine import GameError, public_state, validate_state
from game.content import public_content
from tests.helpers import Journey, solve_activity
from tests import test_career_cafe_bakery as cbt


class CoffeePace(unittest.TestCase):
    setUp = cbt.CafeBakeryTests.setUp
    tearDown = cbt.CafeBakeryTests.tearDown
    journey = cbt.CafeBakeryTests.journey
    stock_up = cbt.CafeBakeryTests.stock_up

    def prepare(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] and not n['iced'], days=range(8, 15))
        j.act('ask')
        n = j.task['needs']
        j.act('cb_cup', kind='paper' if n['takeaway'] else 'mug', size=n['size'])
        return j, n

    def test_double_pace_preserves_shot_and_milk_results_and_survives_save(self):
        j, n = self.prepare()
        turn = j.c['turn']
        j.act('cb_pace', pace=2)
        self.assertEqual(j.c['turn'], turn)
        j.state = json.loads(json.dumps(j.state))
        validate_state(j.state)
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull')
        self.clock.t += 13.5
        pub = public_state(j.state)['careers']['cafe_bakery']['data']
        self.assertEqual(pub['groups'][0]['flow'], 2)
        j.act('cb_stop')
        self.assertEqual(j.task['drink']['shots'][0]['sec'], 27)
        self.assertEqual(j.task['drink']['shots'][0]['x'], 'balanced')
        j.act('cb_milk', milk=n['milk'], mode='steam', foam=n['foam'])
        self.clock.t += 6.5
        j.act('cb_milk_stop')
        self.assertAlmostEqual(j.task['drink']['milk']['temp'], 59.6)
        self.assertEqual(j.task['drink']['milk']['tex'], 'silky')

    def test_running_timers_and_invalid_paces_cannot_change_pace(self):
        j, n = self.prepare()
        for pace in (0, 3, True, '2', [], None):
            with self.subTest(pace=pace), self.assertRaises(GameError):
                j.act('cb_pace', pace=pace)
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull')
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('cb_pace', pace=2)
        self.assertEqual(j.state, before)
        self.clock.t += 27
        j.act('cb_stop')
        j.act('cb_milk', milk=n['milk'], mode='steam', foam=n['foam'])
        with self.assertRaises(GameError):
            j.act('cb_pace', pace=2)

    def test_fast_pace_still_penalizes_late_stop(self):
        j, n = self.prepare()
        j.act('cb_pace', pace=2)
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull')
        self.clock.t += 20
        j.act('cb_stop')
        self.assertEqual(j.task['drink']['shots'][0]['x'], 'bitter')
        self.assertGreater(j.task['mistakes'], 0)

    def test_old_save_defaults_to_normal_pace(self):
        j, n = self.prepare()
        j.c['ext']['data'].pop('bar_pace', None)
        validate_state(j.state)
        self.assertEqual(j.c['ext']['data']['bar_pace'], 1)
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull')
        self.clock.t += 27
        j.act('cb_stop')
        self.assertEqual(j.task['drink']['shots'][0]['sec'], 27)


class FestivalPassport(unittest.TestCase):
    def test_festival_and_badge_are_two_explicit_claims(self):
        j = Journey()
        j.c['life']['festival'] = True
        j.c['life']['mode'] = 'festival'
        for _ in range(3):
            j.solve()
            pending = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred')]
            if pending:
                j.act('task_select', task=pending[0]['id'])
        solve_activity(j, 'mother_baby-sort')
        self.assertNotIn('fair', j.c['life']['badges'])
        j.act('life_festival')
        self.assertEqual(j.c['metrics']['festivals'], 1)
        j.act('life_badge', badge='fair')
        self.assertIn('fair', j.c['life']['badges'])
        with self.assertRaises(GameError):
            j.act('life_festival')
        validate_state(j.state)

    def test_passport_renders_actionable_festival_steps(self):
        j = Journey()
        day, slot = cbt.find_slot(lambda n: n['kind'] == 'drink', days=[8])
        coffee = Journey('cafe_bakery', day=day, slot=slot)
        coffee.act('ask')
        payload = dict(state=public_state(j.state), coffee=public_state(coffee.state), content=public_content())
        proc = subprocess.run(['node', 'tests/coffee_passport.mjs'], input=json.dumps(payload), text=True,
                              encoding='utf-8', capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == '__main__':
    unittest.main()
