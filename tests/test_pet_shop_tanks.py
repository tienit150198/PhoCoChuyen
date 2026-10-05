"""Separate customer aquariums must stay separate through checkout and saves."""
import copy
import unittest

from game.engine import GameError, validate_state
from tests.test_career_pet_shop import PS, at, tid, t_of, ring, pay, codes


class SeparateTanks(unittest.TestCase):
    def put(self, j, tank, size, fish, filter=False):
        j.act('ps_tank', task=tid(j), tank=tank, size=size)
        for key, qty in {**fish, 'conditioner': 1, **({'filter': 1} if filter else {})}.items():
            j.act('ps_cart', task=tid(j), tank=tank, key=key, qty=qty)

    def finish(self, j):
        j.act('ps_advice', task=tid(j), tips=['float', 'part', 'pinch'])
        ring(j)
        pay(j)

    def test_two_bettas_in_two_tanks_score_full_setup_and_charge_both(self):
        j = at('hai_bettas')
        stock = PS.kit.stock(j.c, 'tank_10')
        self.put(j, 0, 'tank_10', {'betta': 1})
        self.put(j, 1, 'tank_10', {'betta': 1})
        self.assertEqual(t_of(j)['cart']['betta'], 2)
        self.assertEqual(t_of(j)['cart']['tank_10'], 2)
        self.finish(j)
        self.assertFalse(codes(t_of(j)))
        self.assertEqual(j.c['feed'][0]['feedback']['fair'], 5)
        self.assertEqual(PS.kit.stock(j.c, 'tank_10'), stock - 2)
        self.assertEqual(t_of(j)['cash']['price'], sum(t_of(j)['units'][k] * q for k, q in t_of(j)['cart'].items()))

    def test_goldfish_and_tropical_fish_in_separate_tanks(self):
        j = at('quan_office')
        self.put(j, 0, 'tank_30', {'guppy': 6}, filter=True)
        self.put(j, 1, 'tank_30', {'goldfish': 2}, filter=True)
        self.finish(j)
        self.assertFalse(codes(t_of(j)))
        self.assertEqual(j.c['feed'][0]['feedback']['fair'], 5)

    def test_crowding_and_filter_are_checked_per_tank(self):
        j = at('quan_office')
        self.put(j, 0, 'tank_60', {'guppy': 6}, filter=True)
        self.put(j, 1, 'tank_10', {'goldfish': 2})
        self.finish(j)
        self.assertTrue({'crowded', 'no_filter'} <= codes(t_of(j)))
        self.assertNotIn('temp_mix', codes(t_of(j)))

    def test_move_fish_resize_and_round_trip_keep_other_tank(self):
        j = at('hai_bettas')
        self.put(j, 0, 'tank_10', {'betta': 2})
        self.put(j, 1, 'tank_30', {})
        j.act('ps_cart', task=tid(j), tank=0, key='betta', qty=1)
        j.act('ps_cart', task=tid(j), tank=1, key='betta', qty=1)
        j.act('ps_tank', task=tid(j), tank=1, size='tank_10')
        validate_state(copy.deepcopy(j.state))
        rows = PS.public_task(t_of(j))['tanks']
        self.assertEqual([r['cart']['betta'] for r in rows], [1, 1])
        self.assertEqual([r['load']['size'] for r in rows], [10, 10])
        self.finish(j)
        with self.assertRaises(GameError):
            j.act('ps_tank', task=tid(j), tank=1, size='tank_30')

    def test_stock_is_checked_across_tanks(self):
        j = at('hai_bettas')
        for i in range(PS.kit.stock(j.c, 'tank_10')):
            self.put(j, i, 'tank_10', {})
        with self.assertRaises(GameError):
            j.act('ps_tank', task=tid(j), tank=4, size='tank_10')

    def test_tampered_assignment_cannot_hide_fish_or_gear(self):
        j = at('hai_bettas')
        self.put(j, 0, 'tank_10', {'betta': 1})
        bad = copy.deepcopy(j.state)
        bad['careers']['pet_shop']['tasks'][-1]['tanks'][0]['betta'] = 2
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_remove_empty_tank_keeps_other_fish(self):
        j = at('hai_bettas')
        self.put(j, 0, 'tank_10', {'betta': 1})
        self.put(j, 1, 'tank_30', {})
        with self.assertRaises(GameError):
            j.act('ps_tank_remove', task=tid(j), tank=0)
        j.act('ps_tank_remove', task=tid(j), tank=1)
        self.assertEqual(t_of(j)['cart'], {'tank_10': 1, 'betta': 1, 'conditioner': 1})

    def test_old_single_tank_save_still_loads_and_can_add_another(self):
        j = at('hai_bettas')
        t_of(j)['cart'] = {'tank_10': 1, 'betta': 1, 'conditioner': 1}
        self.assertNotIn('tanks', t_of(j))
        validate_state(j.state)
        self.put(j, 1, 'tank_10', {'betta': 1})
        self.assertEqual(t_of(j)['cart']['betta'], 2)


if __name__ == '__main__':
    unittest.main()
