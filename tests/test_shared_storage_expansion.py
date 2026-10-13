import copy
import unittest

from game import inventory
from game.careers import clothing, kit
from game.engine import GameError, validate_state
from tests.helpers import Journey
from tests.test_inventory_flow import empty, set_money, wait_until_ready, public_inv


def expand(c, career, tier=10):
    c['upgrades'] += [f'warehouse_storage_{career}_{n}' for n in range(1, tier + 1)]


class SharedStorageExpansion(unittest.TestCase):
    def test_capacity_is_owned_and_static_catalogue_stays_compatible(self):
        for career, expected in [('restaurant', 4000), ('com', 6000), ('clothing', 4000)]:
            j = Journey(career)
            base = inventory.capacity(career)
            self.assertEqual(inventory.capacity(career, j.c), base)
            expand(j.c, career)
            self.assertEqual(inventory.capacity(career, j.c), expected)
            self.assertEqual(inventory.stock_limit(career, j.c), expected)
            self.assertEqual(inventory.capacity(career), base)

    def test_paid_stock_orders_cart_receipt_and_public_share_limit(self):
        j = Journey('restaurant'); expand(j.c, j.career); set_money(j.c, 1000000)
        empty(j.c, 'noodle'); inventory.add_lot(j.c, 'noodle', 100, 1, 999, 'test')
        j.act('inv_cart', supplier='express', item='noodle', qty=80)
        self.assertEqual(public_inv(j)['capacity'], 4000)
        self.assertEqual(public_inv(j)['carts'][0]['lines'][0]['room'], 3900)
        j.act('inv_order', supplier='express', item='noodle', qty=80, confirm=True)
        order = j.c['ext']['inv']['orders'][-1]
        wait_until_ready(j, order['id'])
        j.act('inv_receive', order=order['id'], count=order['actual'])
        self.assertEqual(inventory.count(j.c, 'noodle'), 180)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('inv_order', supplier='express', item='noodle', qty=81, confirm=True)
        self.assertEqual(j.state, before)
        validate_state(j.state)

    def test_validator_preserves_many_lots_and_rejects_unpaid_large_stock(self):
        j = Journey('restaurant'); expand(j.c, j.career)
        empty(j.c, 'noodle')
        for n in range(350): inventory.add_lot(j.c, 'noodle', 1, 1, 999, 'test')
        inventory.add_lot(j.c, 'noodle', 1500, 1, 999, 'test')
        inventory.validate(j.c, j.career)
        self.assertEqual(inventory.count(j.c, 'noodle'), 1850)
        j.c['upgrades'] = []
        with self.assertRaises(GameError): inventory.validate(j.c, j.career)

    def test_recovered_and_event_goods_respect_incoming_paid_room(self):
        from game.happenings import _stock_give
        j = Journey('restaurant'); expand(j.c, j.career); set_money(j.c, 1000000)
        empty(j.c, 'noodle'); inventory.add_lot(j.c, 'noodle', 3990, 1, 999, 'test')
        j.act('inv_order', supplier='express', item='noodle', qty=8, confirm=True)
        self.assertEqual(_stock_give(j.state, j.c, j.career, 'noodle', 5, 1), 2)
        kit._apply_effects(j.state, j.c, j.career, {}, {'title': 'test'}, {'stock': {'noodle': 5}}, 'test')
        self.assertEqual(inventory.count(j.c, 'noodle'), 3992)
        validate_state(j.state)

    def test_clothing_return_uses_owned_room_and_reserves_pending_orders(self):
        j = Journey('clothing'); expand(j.c, j.career); set_money(j.c, 1000000)
        empty(j.c, 'tee'); inventory.add_lot(j.c, 'tee', 100, 80, 999, 'test')
        clothing._sync(j.c)
        clothing._restock_one(j.c, 'tee', 'M')
        self.assertEqual(inventory.count(j.c, 'tee'), 101)
        empty(j.c, 'tee'); inventory.add_lot(j.c, 'tee', 3999, 80, 999, 'test')
        clothing._sync(j.c)
        j.act('inv_order', supplier='express', item='tee', qty=1, confirm=True)
        with self.assertRaises(GameError): clothing._restock_one(j.c, 'tee', 'M')
        self.assertEqual(inventory.count(j.c, 'tee'), 3999)
        validate_state(j.state)

    def test_detached_fruit_and_snacks_reserve_room_but_clothing_does_not(self):
        self.assertEqual(inventory.reserved({"tasks": []}, "clothing", "tee"), 0)
        for career, item, field in [('fruit', 'cam', 'bag'), ('tra_da', 'thuoc_la', 'snacks')]:
            j = Journey(career); expand(j.c, career)
            empty(j.c, item); inventory.add_lot(j.c, item, 3999, 1, 999, 'test')
            task = dict(career=career, status='in_progress', stage='prep')
            task[field] = [dict(i=item, e=j.c['day'], b=False)] if field == 'bag' else {item: 1}
            j.c['tasks'].append(task)
            self.assertEqual(inventory.room(j.c, career, item), 0)
            with self.assertRaises(GameError):
                inventory.action(j.state, j.c, career, 'inv_order', dict(item=item, qty=1, supplier='express', confirm=True))
            self.assertEqual(inventory.public(j.c, career)['room'][item], 0)
        j = Journey('clothing'); expand(j.c, 'clothing')
        empty(j.c, 'tee'); inventory.add_lot(j.c, 'tee', 3999, 80, 999, 'test')
        j.c['tasks'].append(dict(career='clothing', status='in_progress', picks=[dict(item='tee', size='M')]))
        self.assertEqual(inventory.room(j.c, 'clothing', 'tee'), 1)

    def test_merged_order_and_social_purchase_use_paid_room(self):
        from game.social import apply_internal
        j = Journey('restaurant'); expand(j.c, j.career); set_money(j.c, 1000000)
        empty(j.c, 'noodle'); inventory.add_lot(j.c, 'noodle', 100, 1, 999, 'test')
        j.act('inv_cart', supplier='express', item='noodle', qty=20)
        j.act('inv_order_cart', supplier='express', confirm=True)
        order = j.c['ext']['inv']['orders'][-1]
        wait_until_ready(j, order['id'])
        j.act('inv_receive', group=order['group'], counts={order['id']: order['actual']})
        apply_internal(j.state, j.c, j.career, 'soc_buy', dict(item='noodle', qty=5, total=5, life_left=5))
        self.assertEqual(inventory.count(j.c, 'noodle'), 125)
        validate_state(j.state)
        empty(j.c, 'noodle'); inventory.add_lot(j.c, 'noodle', 3999, 1, 999, 'test')
        j.act('inv_order', supplier='express', item='noodle', qty=1, confirm=True)
        with self.assertRaises(GameError):
            apply_internal(j.state, j.c, j.career, 'soc_buy', dict(item='noodle', qty=1, total=1, life_left=5))

    def test_large_clothing_size_lot_receives_without_double_counting_sizes(self):
        j = Journey('clothing'); expand(j.c, j.career); set_money(j.c, 1000000)
        empty(j.c, 'tee'); inventory.add_lot(j.c, 'tee', 3919, 80, 999, 'test'); clothing._sync(j.c)
        j.act('inv_order', supplier='express', item='tee', qty=80, size='M', confirm=True)
        order = j.c['ext']['inv']['orders'][-1]; wait_until_ready(j, order['id'])
        j.act('inv_receive', order=order['id'], count=order['actual'])
        self.assertEqual(sum(j.c['ext']['data']['grid']['tee'].values()), 3999)
        clothing._restock_one(j.c, 'tee', 'S')
        self.assertEqual(sum(j.c['ext']['data']['grid']['tee'].values()), 4000)
        validate_state(j.state)

    def test_close_preserves_live_lots_and_records_exact_large_waste(self):
        j = Journey('restaurant'); expand(j.c, j.career)
        empty(j.c, 'noodle')
        for n in range(350): inventory.add_lot(j.c, 'noodle', 1, 1, 999, 'test')
        live_ids = [lot['id'] for lot in j.c['ext']['inv']['lots']]
        inventory.add_lot(j.c, 'noodle', 1500, 1000, 1, 'test')
        inventory.on_close(j.state, j.c, j.career)
        self.assertEqual([lot['id'] for lot in j.c['ext']['inv']['lots']], live_ids)
        self.assertEqual(j.c['life']['waste'][-1]['qty'], 1500)
        self.assertEqual(j.c['life']['waste'][-1]['value'], 1500000)
        validate_state(j.state)
        lot = inventory.add_lot(j.c, 'noodle', 1500, 1000, 999, 'test')
        j.act('inv_discard', lot=lot['id'], confirm=True)
        self.assertEqual(j.c['life']['waste'][-1]['qty'], 1500)
        validate_state(j.state)

    def test_com_maximum_expiry_value_and_waste_quantity_validation(self):
        from game import experiences
        j = Journey('com'); expand(j.c, j.career)
        item = inventory.catalogue(j.career)[0]['id']
        empty(j.c, item)
        inventory.add_lot(j.c, item, 6000, 10000, 1, 'test')
        inventory.on_close(j.state, j.c, j.career)
        self.assertEqual(j.c['life']['waste'][-1]['qty'], 6000)
        self.assertEqual(j.c['life']['waste'][-1]['value'], 60000000)
        validate_state(j.state)
        j.c['life']['waste'][-1]['qty'] = 6001
        with self.assertRaises(GameError): experiences.validate(j.c, j.career)

    def test_grocery_inspection_keeps_all_large_stock_references_and_waste(self):
        from game.careers import grocery
        j = Journey('grocery'); expand(j.c, j.career)
        j.c['ext']['inv']['lots'] = []
        for n in range(301): inventory.add_lot(j.c, 'milk', 1, 1, 1, 'test')
        large = inventory.add_lot(j.c, 'milk', 1500, 1000, 1, 'test')
        grocery._inspect(j.state, j.c, {})
        self.assertEqual(len(j.c['ext']['data']['fine']['lots']), 302)
        validate_state(j.state)
        grocery._destroy(j.c, [large['id']], 'Test discard')
        self.assertEqual(j.c['life']['waste'][-1]['qty'], 1500)
        self.assertEqual(j.c['life']['waste'][-1]['value'], 1500000)
        j.c['ext']['inv']['lots'] = []
        validate_state(j.state)  # The fine keeps references even after the goods are gone.
