import copy
import hashlib
import json
import unittest

from game import inventory
from game.careers import cafe_bakery as CB, kit
from game.engine import GameError, validate_state
from unittest.mock import patch
from tests.helpers import Journey


class CafeMenuExpansionTests(unittest.TestCase):
    def journey(self, day):
        j = Journey('cafe_bakery', day=day, slot=0)
        for item in CB.ITEMS:
            inventory.add_lot(j.c, item['id'], 8, 2, 30, 'partner')
        j.act('ask')
        return j

    def base(self, j):
        n = j.task['needs']
        j.act('cb_cup', kind='paper' if n['takeaway'] else 'glass', size=n['size'])
        j.act('cb_ice')
        j.act('cb_mix', base=CB.DRINKS[n['drink']]['base'])
        j.act('cb_milk', milk=n['milk'], mode='cold')

    def test_bounded_new_menu_and_legacy_generator(self):
        self.assertEqual({CB.make_task(day, 0, 1)['needs'].get('drink') for day in range(6, 9)},
                         {'matcha_latte', 'matcha_blend', 'cacao_blend'})
        for day in range(1, 20):
            for slot in range(12):
                t = CB.make_task(day, slot, 1, legacy=True)
                self.assertEqual(t['gen'], 2)
                self.assertNotIn(t['needs'].get('drink'), ('matcha_latte', 'matcha_blend', 'cacao_blend'))
        for item in ('matcha_cookie', 'cacao_muffin'):
            self.assertIn(item, CB.CASE_ITEMS)
            self.assertTrue(set(CB.BAKES[item]['recipe']) <= set(CB.ITEM_INDEX))

    def test_release179_orders_frozen_and_all_validate(self):
        # Digest captured from the actual release179 module, not the new generator.
        tasks = [CB.make_task(day, slot, 1, legacy=True) for day in range(1, 41) for slot in range(12)]
        self.assertEqual(hashlib.sha256(json.dumps(tasks, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                         'b88344b2ea041dc0f4e22d4b6a33f9b878607800356d3f31a0a1caa37dcaecb2')
        for day in range(1, 41):
            j = Journey('cafe_bakery', day=day, slot=0)
            j.c['tasks'] = copy.deepcopy(tasks[(day - 1) * 12:day * 12])
            j.c['active_task'] = j.c['tasks'][0]['id']
            validate_state(json.loads(json.dumps(j.state)))

    def test_new_pastries_bake_recipe_and_can_be_sold(self):
        for day, item in ((9, 'matcha_cookie'), (10, 'cacao_muffin')):
            with self.subTest(item=item), patch.object(kit, 'clock', return_value=1000.0) as clock:
                j = self.journey(day)
                tid = j.task['id']
                recipe = CB.BAKES[item]['recipe']
                before = {k: kit.stock(j.c, k) for k in recipe}
                j.act('cb_bake', item=item)
                for k, qty in recipe.items():
                    self.assertEqual(kit.stock(j.c, k), before[k] - qty)
                rack = j.c['ext']['data']['oven'][0]
                clock.return_value += sum(CB.BAKES[item]['window'][:2]) / 2
                j.act('cb_unload', rack=rack['id'])
                lot = next(x for x in j.c['ext']['data']['case'] if x['item'] == item)
                self.assertEqual(lot['q'], 'golden')
                for _ in range(2):
                    j.act('cb_pick', lot=lot['id'])
                j.act('cb_bag')
                j.act('cb_serve', confirm=True)
                self.assertEqual(j.get(tid)['status'], 'completed')
                validate_state(j.state)

    def test_empty_powder_and_wrong_base_never_produce_revenue(self):
        j = Journey('cafe_bakery', day=6, slot=0)
        j.act('ask')
        j.act('cb_cup', kind='paper', size='L')
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('cb_mix', base='matcha')
        self.assertEqual(j.state, before)
        inventory.add_lot(j.c, 'cacao', 1, 3, 30, 'partner')
        j.act('cb_mix', base='cacao')
        money = j.c['money']
        self.assertTrue(j.act('cb_serve', confirm=True).get('refused'))
        self.assertEqual(j.c['money'], money)
        self.assertEqual(kit.stock(j.c, 'cacao'), 0)

    def test_new_drinks_consume_real_stock_and_complete_without_coffee(self):
        for day in (6, 7, 8):
            with self.subTest(day=day):
                j = self.journey(day)
                n, spec = j.task['needs'], CB.DRINKS[j.task['needs']['drink']]
                tid = j.task['id']
                before = {k: kit.stock(j.c, k) for k in ('matcha', 'cacao', 'jelly', 'beans_house')}
                self.base(j)
                if spec.get('blend'):
                    j.act('cb_blend')
                if spec.get('jelly'):
                    j.act('cb_jelly')
                if n['takeaway']:
                    j.act('cb_lid')
                price = j.task['quoted_price']
                j.act('cb_serve', confirm=True)
                self.assertEqual(j.get(tid)['status'], 'completed')
                self.assertEqual(j.get(tid)['mistakes'], 0)
                self.assertEqual(kit.stock(j.c, spec['base']), before[spec['base']] - 1)
                self.assertEqual(kit.stock(j.c, 'beans_house'), before['beans_house'])
                self.assertEqual(kit.stock(j.c, 'jelly'), before['jelly'] - bool(spec.get('jelly')))
                self.assertGreater(price, 0)
                validate_state(json.loads(json.dumps(j.state)))

    def test_preparation_repeats_and_missing_blend_or_jelly_do_not_pay(self):
        j = self.journey(8)
        tid = j.task['id']
        self.base(j)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('cb_mix', base='cacao')
        self.assertEqual(before, j.state)
        j.act('cb_lid')
        money = j.c['money']
        self.assertTrue(j.act('cb_serve', confirm=True).get('refused'))
        self.assertEqual(j.c['money'], money)
        j.act('cb_blend')
        self.assertTrue(j.act('cb_serve', confirm=True).get('refused'))
        j.act('cb_jelly')
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('cb_jelly')
        self.assertEqual(before, j.state)
        j.act('cb_serve', confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_saved_gen2_order_and_work_remain_exact(self):
        j = Journey('cafe_bakery', day=6, slot=0)
        t = CB.make_task(6, 0, 1, legacy=True)
        j.c['tasks'] = [t]
        j.c['active_task'] = t['id']
        CB.on_task(j.state, j.c, t)
        j.act('ask')
        n = j.task['needs']
        if n['kind'] == 'drink':
            j.act('cb_cup', kind='paper' if n['takeaway'] else 'glass' if n['iced'] else 'mug', size=n['size'])
        snapshot = copy.deepcopy(j.task)
        CB.on_start(j.state, j.c)
        self.assertEqual(j.task, snapshot)
        validate_state(json.loads(json.dumps(j.state)))

    def test_legacy_active_shot_survives_projection_and_migration(self):
        with patch.object(kit, 'clock', return_value=1000.0) as clock:
            j = Journey('cafe_bakery', day=2, slot=0)
            t = CB.make_task(2, 0, 1, legacy=True)
            j.c['tasks'] = [t]
            j.c['active_task'] = t['id']
            CB.on_task(j.state, j.c, t)
            j.act('ask')
            n = j.task['needs']
            self.assertEqual(n['kind'], 'drink')
            j.act('cb_cup', kind='paper' if n['takeaway'] else 'glass' if n['iced'] else 'mug', size=n['size'])
            j.act('cb_dose', beans=n['beans'], grind='fine', grams=18)
            j.act('cb_pull')
            saved = copy.deepcopy(j.task)
            self.assertEqual(CB.public_task(j.task)['drink'], saved['drink'])
            CB.on_start(j.state, j.c)
            self.assertEqual(j.task, saved)
            validate_state(json.loads(json.dumps(j.state)))
            clock.return_value = 1027.0
            j.act('cb_stop')
            self.assertEqual(j.task['gen'], 2)
            self.assertEqual(j.task['needs'], saved['needs'])
            self.assertEqual(j.task['drink']['shots'][0]['sec'], 27.0)
            self.assertEqual(j.task['drink']['shots'][0]['x'], 'balanced')
            self.assertEqual(j.task['drink']['cost'], saved['drink']['cost'])


if __name__ == '__main__':
    unittest.main()
