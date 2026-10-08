"""F#248 (08/10): "Thêm mấy món trà đào cam sả với trà thạch đào nữa… và bánh đào nướng".

* 🏪 Quầy của bạn: Trà đào cam sả and Trà thạch đào on the milk tea board, Bánh đào nướng on the bakery board. A board
  saved before keeps what it sells (the new dishes start off, Menu turns them on); a new counter sells the whole trade.
* 🥐 Tiệm Bánh Sớm Mai: Bánh đào nướng is a real bake (vỏ bơ, đào ngâm from the Kho), cấp 2, sold from the case.
* ☕ Đi quán: Trà thạch đào at Trà sữa Mây, Bánh đào nướng at Cà phê Cô Lan.
Old saves and tasks already made still validate: no new save keys, the order book is untouched."""
import copy
import json
import unittest
from unittest.mock import patch

from game import inventory, quay_self as qs
from game.careers import cafe_bakery as CB, kit
from game.engine import validate_state
from tests.helpers import Journey
from tests.test_quay import ST, act, opened

NEW_TEA = ('tra_dao_cam_sa', 'tra_thach_dao')


class QuayBoard(unittest.TestCase):
    def test_new_dishes_are_on_the_trades(self):
        tea = {d[0]: d for d in qs.MENUS['milk_tea']}
        self.assertEqual(tea['tra_dao_cam_sa'][2], 'Trà đào cam sả')
        self.assertEqual(tea['tra_thach_dao'][2], 'Trà thạch đào')
        self.assertEqual({d[0]: d for d in qs.MENUS['cafe_bakery']}['banh_dao_nuong'][2], 'Bánh đào nướng')
        for trade in ('milk_tea', 'cafe_bakery'):
            ids = [d[0] for d in qs.MENUS[trade]]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertLessEqual(len(ids), qs.MENU_MAX)
            self.assertEqual(ids[:6], [d[0] for d in qs.MENUS[trade][:6]])
        self.assertEqual([d[0] for d in qs.MENUS['milk_tea'][:3]], ['ts_tran_chau', 'hong_tra', 'tra_dao'])   # old default

    def test_a_new_counter_sells_them_and_an_old_board_keeps_its_dishes(self):
        s = opened('kiot', wallet=20000)
        st = ST(s)
        for d in NEW_TEA:
            self.assertIn(d, st['menu']['on'])
        validate_state(s)
        # A board saved before 1.9.20: the new dishes are off until the owner turns them on.
        old = [d[0] for d in qs.MENUS['milk_tea'] if d[0] not in NEW_TEA]
        st['menu'] = dict(on=old, p={'tra_dao': 15})
        validate_state(json.loads(json.dumps(s)))
        self.assertNotIn('tra_thach_dao', qs.menu(st)['on'])
        s, _ = act(s, 'jr_quay_menu', stall=st['id'], on=old + ['tra_thach_dao'], p={'tra_dao': 15})
        m = ST(s)['menu']
        self.assertIn('tra_thach_dao', m['on'])
        self.assertNotIn('tra_dao_cam_sa', m['on'])
        self.assertEqual(m['p'], {'tra_dao': 15})
        validate_state(s)


class BakeryPeachTart(unittest.TestCase):
    def journey(self, day):
        j = Journey('cafe_bakery', day=day, slot=0)
        for item in CB.ITEMS:
            inventory.add_lot(j.c, item['id'], 8, 2, 30, 'partner')
        j.c['xp'] = max(j.c['xp'], 90)   # cấp 2
        j.act('ask')
        return j

    def test_data(self):
        b = CB.BAKES['peach_tart']
        self.assertEqual((b['name'], b['unlock'], b['proof']), ('Bánh đào nướng', 2, False))
        self.assertIn('peach_tart', CB.CASE_ITEMS)
        self.assertTrue(set(b['recipe']) <= set(CB.ITEM_INDEX))
        self.assertIn('peach', CB.ITEM_INDEX)
        self.assertGreater(CB.SPEC['prices']['peach_tart'], 0)
        self.assertIn('peach_tart', CB.BUYER_WANTS)
        self.assertTrue(any(inventory.sells(sp, 'peach') for sp in inventory.suppliers('cafe_bakery')))

    def test_bake_uses_the_recipe_and_the_case_sells_it(self):
        with patch.object(kit, 'clock', return_value=1000.0) as clock:
            j = self.journey(9)
            recipe = CB.BAKES['peach_tart']['recipe']
            before = {k: kit.stock(j.c, k) for k in recipe}
            j.act('cb_bake', item='peach_tart')
            for k, qty in recipe.items():
                self.assertEqual(kit.stock(j.c, k), before[k] - qty)
            rack = next(r for r in j.c['ext']['data']['oven'] if r['item'] == 'peach_tart')
            clock.return_value += sum(CB.BAKES['peach_tart']['window'][:2]) / 2
            j.act('cb_unload', rack=rack['id'])
            lot = next(x for x in j.c['ext']['data']['case'] if x['item'] == 'peach_tart')
            self.assertEqual((lot['q'], lot['qty']), ('golden', 6))
            validate_state(json.loads(json.dumps(j.state)))

    def test_no_peaches_no_bake(self):
        j = Journey('cafe_bakery', day=9, slot=0)
        for item in CB.ITEMS:
            if item['id'] != 'peach':
                inventory.add_lot(j.c, item['id'], 8, 2, 30, 'partner')
        j.c['xp'] = max(j.c['xp'], 90)
        j.act('ask')
        before = copy.deepcopy(j.state)
        with self.assertRaises(Exception):
            j.act('cb_bake', item='peach_tart')
        self.assertEqual(j.state, before)

    def test_locked_before_level_two(self):
        j = Journey('cafe_bakery', day=9, slot=0)
        for item in CB.ITEMS:
            inventory.add_lot(j.c, item['id'], 8, 2, 30, 'partner')
        j.c['xp'] = 0
        j.act('ask')
        with self.assertRaises(Exception) as e:
            j.act('cb_bake', item='peach_tart')
        self.assertIn('mở ở cấp 2', str(e.exception))

    def test_order_book_is_unchanged(self):
        # Saved tasks are regenerated and compared (scripts/check_task_compat.py): the peach tart is never ordered.
        for day in range(1, 41):
            for slot in range(12):
                n = CB.make_task(day, slot, 1)['needs']
                self.assertNotIn('peach_tart', (n.get('items') or {}))
                self.assertNotIn('peach_tart', (n.get('pastry') or {}))


class Quan(unittest.TestCase):
    def test_new_items_at_the_street_shops(self):
        from game import spend
        from tests.test_bank import story
        s = story(200)
        for shop, item in (('tra_sua_may', 'tra_thach_dao'), ('co_lan', 'banh_dao_nuong')):
            s, _ = act(s, 'jr_spend_eat', shop=shop, item=item)
            self.assertEqual(spend.ITEMS[item][0], shop)
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
