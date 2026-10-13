"""Paid order limits remain independent of shelf capacity and receipt counts."""
import copy
import json
import unittest

from game import inventory as I
from game.content import CAREERS, UPGRADES
from game.engine import GameError, validate_state
from tests.helpers import Journey
from tests.test_inventory_flow import empty, public_inv, set_money, wait_until_ready


def buy(j, group, tier):
    for n in range(1, tier + 1):
        j.act('buy_upgrade', item=f'warehouse_{group}_{j.career}_{n}')


def fresh(career='clothing', storage=5, order=0):
    j = Journey(career)
    set_money(j.c, 900_000_000)
    buy(j, 'storage', storage)
    buy(j, 'order', order)
    if career == 'clothing':
        from game.careers import clothing
        I.add_lot(j.c, 'tee', 6, 0, 999, 'opening')
        clothing.on_stock(j.state, j.c, 'inv_receive')
    return j


class OrderProgression(unittest.TestCase):
    def test_catalogue_exact_scope_prices_and_progression(self):
        from game.career_scale_content import PROFILES
        eligible = {cid for cid in CAREERS if I.catalogue(cid)} | {c for c,p in PROFILES.items() if p.kind=='business'}
        rows = [u for u in UPGRADES if u.get('gear_group') == 'warehouse_order']
        self.assertEqual(len(eligible), 36)
        self.assertEqual(len(rows), 360)
        self.assertEqual({u['careers'][0] for u in rows}, eligible)
        limits = (80, 120, 200, 350, 550, 800, 1200, 1800, 2500, 3200, 4000)
        prices = (3000, 9000, 30000, 100000, 350000, 1200000, 4000000, 12000000, 35000000, 100000000)
        for cid in eligible:
            from game.capacity_progression import units
            group = [u for u in rows if u['careers'] == [cid]]
            self.assertEqual(tuple(u['price'] for u in group), prices)
            self.assertEqual(tuple(u['effect_units'] for u in group), limits[1:])
            self.assertEqual(tuple(u['effect_previous'] for u in group), limits[:-1])
            self.assertTrue(all(u['effect_units'] <= units(I.capacity(cid) if I.catalogue(cid) else 80, 10) for u in group))
            for n, u in enumerate(group, 1):
                self.assertEqual(u['id'], f'warehouse_order_{cid}_{n}')
                self.assertEqual(u['requires'], f'warehouse_order_{cid}_{n-1}' if n > 1 else None)
                self.assertEqual((u['min_level'], u['total_price']), (1, sum(prices)))

    def test_purchase_exact_money_prerequisites_and_independence(self):
        j = fresh(storage=0)
        before = copy.deepcopy(j.state)
        for item in ('warehouse_order_clothing_2', 'warehouse_order_restaurant_1'):
            with self.assertRaises(GameError):
                j.act('buy_upgrade', item=item)
            self.assertEqual(j.state, before)
        buy(j, 'order', 10)
        self.assertEqual(j.c['money'], 900_000_000 - 152_692_000)
        self.assertEqual(public_inv(j)['line_cap'], 4000)
        self.assertEqual(I.public(j.state['careers']['restaurant'], 'restaurant')['line_cap'], 80)
        self.assertEqual(I.capacity('clothing', j.c), 80)
        dto = public_inv(j)['order_upgrade']
        self.assertEqual((dto['tier'], dto['max_tier'], dto['next_id']), (10, 10, None))
        with self.assertRaises(GameError):
            j.act('inv_order', item='tee', qty=81, supplier='partner', confirm=True)
        with self.assertRaises(GameError):
            j.act('buy_upgrade', item='warehouse_order_clothing_10')
        validate_state(json.loads(json.dumps(j.state)))

    def test_storage550_stock22_direct528_requires_order_tier4(self):
        j = fresh()
        self.assertEqual(I.capacity('clothing', j.c), 550)
        self.assertEqual(I.count(j.c, 'tee'), 22)
        self.assertEqual(public_inv(j)['line_cap'], 80)
        for n in range(4):
            with self.assertRaises(GameError):
                j.act('inv_order', item='tee', qty=528, supplier='partner', confirm=True, line_cap=8000)
            if n < 3:
                j.act('buy_upgrade', item=f'warehouse_order_clothing_{n+1}')
        before = j.c['money']
        j.act('buy_upgrade', item='warehouse_order_clothing_4')
        self.assertEqual(j.c['money'], before - 100000)
        dto = public_inv(j)['order_upgrade']
        self.assertEqual((dto['tier'], dto['next_id'], dto['next_limit'], dto['next_price']),
                         (4, 'warehouse_order_clothing_5', 800, 350000))
        grid = copy.deepcopy(j.c['ext']['data']['grid']['tee'])
        j.act('inv_order', item='tee', size='M', qty=528, supplier='partner', confirm=True)
        order = j.c['ext']['inv']['orders'][-1]
        validate_state(json.loads(json.dumps(j.state)))
        with self.assertRaises(GameError):
            j.act('inv_order', item='tee', qty=1, supplier='partner', confirm=True)
        wait_until_ready(j, order['id'])
        with self.assertRaises(GameError):
            j.act('inv_receive', order=order['id'], count=order['actual'] - 1)
        j.act('inv_receive', order=order['id'], count=order['actual'])
        self.assertEqual(I.count(j.c, 'tee'), 22 + order['actual'])
        self.assertEqual(j.c['ext']['data']['grid']['tee']['M'], grid['M'] + order['actual'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_cart_set_bulk_limits_and_roundtrip(self):
        j = fresh(storage=10, order=6)
        j.act('inv_cart', supplier='partner', item='tee', qty=1000)
        j.act('inv_cart', supplier='partner', op='set', item='tee', qty=1200)
        for params in (dict(item='tee', qty=1), dict(op='set', item='tee', qty=1201),
                       dict(lines=[dict(item='jeans', qty=1201)], fit=True)):
            with self.assertRaises(GameError):
                j.act('inv_cart', supplier='partner', **params)
        j.act('inv_cart', supplier='partner', lines=[dict(item='shirt', qty=1100), dict(item='jeans', qty=1050)], fit=True)
        validate_state(json.loads(json.dumps(j.state)))
        j.act('inv_haggle', supplier='partner', pct=5)
        result = j.act('inv_order_cart', supplier='partner', confirm=True)
        orders = [o for o in j.c['ext']['inv']['orders'] if o.get('group') == result['eta']['group']]
        for order in orders:
            wait_until_ready(j, order['id'])
        j.act('inv_receive', group=result['eta']['group'], counts={o['id']: o['actual'] for o in orders})
        validate_state(json.loads(json.dumps(j.state)))

    def test_unowned_limits_rejected_in_saved_order_and_draft(self):
        j = fresh(order=1)
        j.act('inv_order', item='tee', qty=100, supplier='partner', confirm=True)
        j.act('inv_cart', supplier='partner', item='shirt', qty=100)
        validate_state(j.state)
        for kind in ('order', 'draft'):
            s = copy.deepcopy(j.state)
            x = s['careers']['clothing']['ext']['inv']
            row = x['orders'][0] if kind == 'order' else x['cart']['partner']['lines'][0]
            row['qty'] = 121
            with self.assertRaises(GameError):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['clothing']['upgrades'].remove('warehouse_order_clothing_1')
        with self.assertRaises(GameError):
            validate_state(s)

    def test_all_drafts_reserve_space_for_direct_cart_and_placement(self):
        j = fresh(order=4)
        j.act('inv_cart', supplier='partner', item='tee', qty=300)
        with self.assertRaises(GameError):
            j.act('inv_cart', supplier='market', item='tee', qty=229)
        with self.assertRaises(GameError):
            j.act('inv_order', supplier='market', item='tee', qty=229, confirm=True)
        j.act('inv_cart', supplier='market', item='tee', qty=228)
        partner = next(row for row in public_inv(j)['carts'] if row['supplier'] == 'partner')
        self.assertEqual(partner['lines'][0]['room'], 300)
        market = next(row for row in public_inv(j)['carts'] if row['supplier'] == 'market')
        self.assertEqual(market['lines'][0]['room'], 228)
        j.act('inv_order_cart', supplier='partner', confirm=True)
        j.act('inv_order_cart', supplier='market', confirm=True)
        self.assertEqual(sum(o['qty'] for o in j.c['ext']['inv']['orders']), 528)
        validate_state(j.state)

    def test_large_haggled_cart_exact_payment_and_legacy_save_limits(self):
        j = fresh(storage=10, order=10)
        j.c['xp'] = 9000
        lines = [dict(item=it['id'], qty=4000) for it in I.catalogue('clothing')]
        for row in lines:
            empty(j.c, row['item'])
        j.act('inv_cart', supplier='market', lines=lines)
        j.act('inv_haggle', supplier='market', pct=15)
        dto = next(row for row in public_inv(j)['carts'] if row['supplier'] == 'market')
        self.assertGreater(dto['goods'], 1_000_000)
        validate_state(json.loads(json.dumps(j.state)))
        before = j.c['money']
        result = j.act('inv_order_cart', supplier='market', confirm=True)
        orders = [o for o in j.c['ext']['inv']['orders'] if o.get('group') == result['eta']['group']]
        self.assertEqual(before - j.c['money'], sum(o['cost'] + o.get('ship', 0) for o in orders))
        validate_state(json.loads(json.dumps(j.state)))
        self.assertGreater(orders[0].get('off', 0), 1_000_000)
        # An existing base-size draft still loads without purchasing equipment.
        old = fresh(storage=0)
        empty(old.c, 'tee')
        old.act('inv_cart', supplier='partner', item='tee', qty=80)
        validate_state(json.loads(json.dumps(old.state)))
        with self.assertRaises(GameError):
            old.act('inv_cart', supplier='partner', item='shirt', qty=81)

    def test_group_placement_checks_live_ownership_even_for_stale_draft(self):
        j = fresh(order=1)
        j.act('inv_cart', supplier='partner', item='tee', qty=100)
        j.c['upgrades'].remove('warehouse_order_clothing_1')
        # Exercise the action-level guard directly, independent of save validation.
        with self.assertRaises(GameError):
            I.action(j.state, j.c, j.career, 'inv_order_cart', dict(supplier='partner', confirm=True))

    def test_group_placement_reserves_held_sizes_from_own_draft(self):
        j = fresh(order=4)
        j.act('inv_cart', supplier='partner', lines=[dict(item='tee', size='M', qty=250),
                                                    dict(item='tee', size='L', qty=250)])
        I._draft(j.c['ext']['inv'], 'partner')[0]['oos'] = j.c['day']
        I.add_lot(j.c, 'tee', 100, 0, 999, 'opening')
        self.assertEqual(I.count(j.c, 'tee'), 122)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('inv_order_cart', supplier='partner', confirm=True)
        self.assertEqual(j.state, before)

    def test_large_direct_receipt_refund_and_derived_money_bounds(self):
        j = fresh(storage=10, order=10)
        empty(j.c, 'aodai')
        j.act('inv_order', supplier='partner', item='aodai', qty=4000, confirm=True)
        order = j.c['ext']['inv']['orders'][-1]
        self.assertGreater(order['cost'], 1_000_000)
        # Model a short shipment while retaining all actual payment/accounting fields.
        order['actual'] -= 3
        wait_until_ready(j, order['id'])
        j.act('inv_receive', order=order['id'], count=order['actual'])
        before = j.c['money']
        j.act('inv_claim', order=order['id'])
        self.assertEqual(j.c['money'], before + I._refund(order))
        with self.assertRaises(GameError):
            j.act('inv_claim', order=order['id'])
        validate_state(json.loads(json.dumps(j.state)))


if __name__ == '__main__':
    unittest.main()
