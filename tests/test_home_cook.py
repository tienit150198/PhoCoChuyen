"""🍳 Nấu cơm tối ở nhà (game/home_cook.py, feedback #485): where and when, the score, the reward, once an evening,
the dinner it becomes, money, the spouse, older saves and validation."""
import copy
import json
import unittest

from game import home_cook as hc
from game import housing as hs
from game import needs as nd
from game.engine import GameError, public_state, validate_state
from tests.test_needs import N, close, jr_act, opened, spirit, until

RENTED = next(k for k in hs.RENT if k != hs.DORM)


def evening(wallet=100, home=RENTED):
    s = opened(wallet)
    s, _ = until(s, 15 * 60)
    s, _ = close(s)
    s['journey']['wallet'] = wallet
    if home:
        s['journey']['wallet'] = 500
        hs.apply(s, 'jr_home_rent', dict(kind=home, confirm=True))
        s['journey']['wallet'] = wallet
    return s


def cook(s, dish='trung', heat=None, spices=None):
    x = hc.DISHES[dish]
    heat = (x['heat'][0] + x['heat'][1]) // 2 if heat is None else heat
    return jr_act(s, 'jr_cook_done', dish=dish, heat=heat, spices=list(x['spices']) if spices is None else spices)


class CookTests(unittest.TestCase):
    def test_score(self):
        self.assertEqual(hc.score('trung', 40, ['mam', 'tieu']), (2, 2, 3))
        self.assertEqual(hc.score('trung', 30, ['tieu', 'mam']), (1, 2, 2))      # near the zone, order does not matter
        self.assertEqual(hc.score('trung', 90, ['mam']), (0, 1, 1))
        self.assertEqual(hc.score('kho', 99, ['ot', 'me']), (0, 0, 1))
        self.assertEqual(hc.score('rau', 70, ['muoi', 'duong', 'ot']), (2, 1, 2))
        for k, x in hc.DISHES.items():
            self.assertTrue(set(x['spices']) <= set(hc.SPICES), k)
            self.assertTrue(0 <= x['heat'][0] < x['heat'][1] <= 100, k)

    def test_kitchen_only_in_the_evening_at_a_home_with_one(self):
        s = opened(100)
        self.assertNotIn('evening', [k for k, v in public_state(s)['needs'].items() if v])
        with self.assertRaises(GameError) as e:
            cook(s)
        self.assertEqual(e.exception.code, 'not_now')
        s = evening(home=None)                                   # Bà Tám's attic: she cooks
        v = public_state(s)['needs']['evening']['cook']
        self.assertEqual((v['ok'], v['why']), (False, hc.NO_KITCHEN))
        with self.assertRaises(GameError) as e:
            cook(s)
        self.assertEqual(e.exception.code, 'no_kitchen')
        s = evening(home=hs.DORM)
        self.assertEqual(public_state(s)['needs']['evening']['cook']['why'], hc.NO_KITCHEN)
        s = evening()
        v = public_state(s)['needs']['evening']['cook']
        self.assertTrue(v['ok'])
        self.assertEqual([d['id'] for d in v['dishes']], list(hc.DISHES))
        self.assertEqual(len(v['spices']), len(hc.SPICES))

    def test_cooking_pays_feeds_and_cheers_once_an_evening(self):
        s = evening(50)
        wallet, sp, full = s['journey']['wallet'], spirit(s), N(s)['full']
        s, r = cook(s, 'kho')
        x = hc.DISHES['kho']
        self.assertEqual(r['cook']['stars'], 3)
        self.assertEqual(s['journey']['wallet'], wallet - x['price'])
        self.assertEqual(N(s)['full'], min(100, full + x['full'] * 115 // 100))
        self.assertEqual(spirit(s), sp + 2)
        self.assertEqual(s['journey']['cook']['best'], {'kho': 3})
        before = copy.deepcopy(s['journey'])
        t, r = cook(s, 'kho')                                     # the same tap again: nothing more
        self.assertEqual(t['journey'], before)
        with self.assertRaises(GameError) as e:
            cook(s, 'trung')
        self.assertEqual(e.exception.code, 'already_done')
        # tonight's dinner is the cooked tray: nothing more to eat, the paid meals are off
        rows = {m['id']: m for m in nd.meals(s)}
        self.assertEqual((rows['nha']['full'], rows['nha']['price']), (0, 0))
        self.assertIn('Thịt kho trứng', rows['nha']['name'])
        self.assertFalse(rows['bua_ngon']['ok'])
        s, _ = jr_act(s, 'jr_needs_eve', meal='nha', bed=23 * 60)
        validate_state(json.loads(json.dumps(s)))
        self.assertEqual(public_state(s)['needs']['evening']['chosen']['name'], rows['nha']['name'])

    def test_a_poor_cook_still_eats(self):
        s = evening()
        sp, full = spirit(s), N(s)['full']
        s, r = cook(s, 'rau', heat=0, spices=['ot'])
        self.assertEqual(r['cook']['stars'], 1)
        self.assertEqual(spirit(s), sp)
        self.assertEqual(N(s)['full'], min(100, full + hc.DISHES['rau']['full'] * 85 // 100))

    def test_no_money_no_market_and_nothing_changes(self):
        s = evening(1)
        before = copy.deepcopy(s['journey'])
        with self.assertRaises(GameError) as e:
            cook(s, 'kho')
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(s['journey'], before)
        self.assertFalse(next(d for d in public_state(s)['needs']['evening']['cook']['dishes'] if d['id'] == 'kho')['ok'])

    def test_after_dinner_was_chosen_the_kitchen_is_closed(self):
        s = evening()
        s, _ = jr_act(s, 'jr_needs_eve', meal='nha', bed=23 * 60)
        with self.assertRaises(GameError) as e:
            cook(s)
        self.assertEqual(e.exception.code, 'already_done')

    def test_cooking_for_a_spouse(self):
        s = evening()
        s['marriage'] = dict(v=1, applied=[], spouse=dict(name='Bình', status='married', since=1, wed=1, date=None),
                             sticker=True, weddings=1)
        sp = spirit(s)
        s, r = cook(s, 'canh')
        self.assertIn('Bình', r['message'])
        self.assertEqual(spirit(s), sp + 3)

    def test_next_evening_cooks_again(self):
        s = evening()
        s, _ = cook(s, 'trung')
        s, _ = jr_act(s, 'jr_needs_eve', meal='nha', bed=23 * 60)
        from tests.test_needs import act
        s, _ = act(s, 'start_day')
        self.assertIsNone(hc.tonight(s))
        self.assertEqual(public_state(s)['needs']['evening'], None)
        s, _ = until(s, 15 * 60)
        s, _ = close(s)
        s['journey']['wallet'] = 100
        s, r = cook(s, 'rau')
        self.assertEqual(s['journey']['cook']['n'], 2)
        self.assertEqual(set(s['journey']['cook']['best']), {'trung', 'rau'})

    def test_bad_payloads_and_saves(self):
        s = evening()
        for p in (dict(dish='pizza', heat=50, spices=[]), dict(dish='trung', heat=101, spices=[]),
                  dict(dish='trung', heat='50', spices=[]), dict(dish='trung', heat=50, spices=['mam', 'mam']),
                  dict(dish='trung', heat=50, spices=['vang']), dict(dish='trung', heat=50)):
            with self.assertRaises(GameError, msg=str(p)):
                jr_act(s, 'jr_cook_done', **p)
        s, _ = cook(s)
        validate_state(s)
        for change in (dict(stars=4), dict(dish='pizza'), dict(v=2), dict(best={}), dict(extra=1)):
            bad = copy.deepcopy(s)
            bad['journey']['cook'].update(change)
            with self.assertRaises(GameError, msg=str(change)):
                validate_state(bad)


if __name__ == '__main__':
    unittest.main()
