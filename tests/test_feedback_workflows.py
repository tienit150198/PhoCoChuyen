"""Player feedback #138/#157/#158/#161/#164: stock and visible work controls."""
import copy
import json
import subprocess
import unittest
from pathlib import Path

from game import inventory
from game.careers import cafe_bakery as cb, clothing
from game.content import public_content
from game.engine import GameError, money, public_state, validate_state
from tests.helpers import Journey
from tests import test_coffee_passport as coffee_tests


class CafeSpeedFeedback(unittest.TestCase):
    setUp = coffee_tests.CoffeePace.setUp
    tearDown = coffee_tests.CoffeePace.tearDown
    journey = coffee_tests.CoffeePace.journey
    stock_up = coffee_tests.CoffeePace.stock_up
    prepare = coffee_tests.CoffeePace.prepare

    def test_four_times_shot_and_steam_preserve_quality(self):
        j, n = self.prepare()
        j.act('cb_pace', pace=4)
        j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull')
        self.clock.t += 27 / 4
        j.act('cb_stop')
        self.assertEqual(j.task['drink']['shots'][-1]['x'], 'balanced')
        self.assertEqual(j.task['drink']['shots'][-1]['sec'], 27)
        j.act('cb_milk', milk=n['milk'], mode='steam', foam=n['foam'])
        self.clock.t += 13 / 4
        j.act('cb_milk_stop')
        self.assertEqual(j.task['drink']['milk']['tex'], 'silky')
        validate_state(j.state)

    def test_oven_uses_pace_at_load_even_after_a_speed_change_and_save(self):
        for pace in (2, 4):
            with self.subTest(pace=pace):
                j, _ = self.prepare()
                j.act('cb_pace', pace=pace)
                j.act('cb_bake', item='cookie')
                rack = j.c['ext']['data']['oven'][0]
                self.assertEqual(rack.get('pace'), pace)
                self.assertEqual(public_state(j.state)['careers']['cafe_bakery']['data']['oven'][0]['pace'], pace)
                j.act('cb_pace', pace=1)
                j.state = json.loads(json.dumps(j.state))
                self.clock.t += 10 / pace
                j.act('cb_unload', rack=rack['id'])
                newest = j.c['ext']['data']['case'][-1]
                self.assertEqual(newest['item'], 'cookie')
                self.assertEqual(newest['q'], 'golden')
                validate_state(j.state)

    def test_older_running_oven_keeps_normal_speed(self):
        j, _ = self.prepare()
        j.act('cb_bake', item='cookie')
        rack = j.c['ext']['data']['oven'][0]
        rack.pop('pace', None)
        j.act('cb_pace', pace=2)
        self.clock.t += 10
        j.act('cb_unload', rack=rack['id'])
        self.assertEqual(j.c['ext']['data']['case'][-1]['q'], 'golden')


class ClothingStockSize(unittest.TestCase):
    def setUp(self):
        self.j = Journey('clothing')
        money(self.j.state, self.j.c, 10000 - self.j.c['money'], 'Test grant', category='grant')

    def receive(self, order):
        clk = inventory.clock(self.j.c, 'clothing')
        order.update(at=clk['abs'], lo=clk['abs'], hi=clk['abs'], late=None)
        self.j.act('inv_receive', order=order['id'], count=order['actual'])

    def test_selected_size_receives_actual_units_and_survives_save(self):
        before = copy.deepcopy(self.j.c['ext']['data']['grid']['tee'])
        self.j.act('inv_order', item='tee', qty=6, size='XL', supplier='partner', confirm=True)
        order = self.j.c['ext']['inv']['orders'][-1]
        self.assertEqual(order.get('size'), 'XL')
        order['actual'] = 4  # a short delivery: do not create the two missing pieces
        self.j.state = json.loads(json.dumps(self.j.state))
        order = self.j.c['ext']['inv']['orders'][-1]
        self.receive(order)
        after = self.j.c['ext']['data']['grid']['tee']
        self.assertEqual(after, {s: n + (order['actual'] if s == 'XL' else 0) for s, n in before.items()})
        self.assertEqual(sum(after.values()), inventory.count(self.j.c, 'tee'))
        validate_state(self.j.state)

    def test_draft_size_is_public_and_preserved_through_group_delivery(self):
        self.j.act('inv_cart', op='add', item='shirt', qty=4, size='S', supplier='partner')
        view = public_state(self.j.state)['careers']['clothing']['inventory']['carts'][0]
        self.assertEqual(view['lines'][0].get('size'), 'S')
        before = copy.deepcopy(self.j.c['ext']['data']['grid']['shirt'])
        self.j.act('inv_order_cart', supplier='partner', confirm=True)
        order = self.j.c['ext']['inv']['orders'][-1]
        self.assertEqual(order.get('size'), 'S')
        clk = inventory.clock(self.j.c, 'clothing')
        order.update(at=clk['abs'], lo=clk['abs'], hi=clk['abs'], late=None)
        self.j.act('inv_receive', group=order['group'], counts={order['id']: order['actual']})
        self.assertEqual(self.j.c['ext']['data']['grid']['shirt'],
                         {s: n + (order['actual'] if s == 'S' else 0) for s, n in before.items()})
        validate_state(self.j.state)

    def test_invalid_size_and_different_size_in_same_draft_do_not_charge(self):
        before = copy.deepcopy(self.j.state)
        with self.assertRaises(GameError):
            self.j.act('inv_order', item='tee', qty=4, size='XXL', supplier='partner', confirm=True)
        self.assertEqual(self.j.state, before)
        self.j.act('inv_cart', op='add', item='tee', qty=4, size='XL', supplier='partner')
        before = copy.deepcopy(self.j.state)
        with self.assertRaises(GameError):
            self.j.act('inv_cart', op='add', item='tee', qty=2, size='S', supplier='partner')
        self.assertEqual(self.j.state, before)

    def test_unselected_size_keeps_automatic_distribution(self):
        self.j.act('inv_order', item='tee', qty=8, supplier='partner', confirm=True)
        order = self.j.c['ext']['inv']['orders'][-1]
        self.receive(order)
        self.assertEqual(sum(self.j.c['ext']['data']['grid']['tee'].values()), inventory.count(self.j.c, 'tee'))

    def test_forged_saved_size_is_rejected(self):
        self.j.act('inv_order', item='tee', qty=2, size='S', supplier='partner', confirm=True)
        self.j.c['ext']['inv']['orders'][-1]['size'] = 'XXL'
        with self.assertRaises(GameError):
            validate_state(self.j.state)

    def test_adding_from_a_bulk_shortcut_keeps_an_existing_draft_size(self):
        self.j.act('inv_cart', op='add', item='tee', qty=2, size='XL', supplier='partner')
        self.j.act('inv_cart', op='add', supplier='partner', lines=[dict(item='tee', qty=2)], fit=True)
        row = self.j.c['ext']['inv']['cart']['partner']['lines'][0]
        self.assertEqual(row['qty'], 4)
        self.assertEqual(row['size'], 'XL')


class FeedbackControls(unittest.TestCase):
    def test_rendered_controls_and_meter_boundaries(self):
        cafe = Journey('cafe_bakery', day=8, slot=0)
        cafe.act('ask')
        stock = Journey('clothing')
        tea = Journey('milk_tea')
        payload = dict(cafe=public_state(cafe.state), clothing=public_state(stock.state),
                       tea=public_state(tea.state), content=public_content())
        proc = subprocess.run(['node', str(Path(__file__).with_suffix('.mjs'))], input=json.dumps(payload),
                              text=True, encoding='utf-8', capture_output=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == '__main__':
    unittest.main()
