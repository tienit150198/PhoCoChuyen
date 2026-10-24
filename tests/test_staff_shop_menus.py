"""#523: shop staff sell what is actually on the shelf (đại lý xe, tiệm vàng, căn tin, văn phòng phẩm), at the
owner's own prices, never a loss and never more than the owner's own sale of the same goods."""
import unittest
from unittest.mock import patch

from game import inventory as inv
from game import operations as ops
from game import staff_market
from game import staff_orders as so
from game import workplace_business as wb
from game.careers import car_dealer, jewelry
from game.careers import car_dealer_content as CD
from game.careers import jewelry_content as JW
from game.engine import new_state


def sample(career):
    s = new_state(); c = s['careers'][career]; c.update(open=True, started=True)
    with patch.object(wb.time, 'time', return_value=2000000000):
        ops.action(s, c, career, 'ops_hire', {'candidate': f'{career}-staff-1', 'confirm': True})
        wb.settle(s)
    c['ops']['finance']['opening_balance'] += 100000 - c['money']; c['money'] = 100000
    return s, c, c['ops']['staff'][0]


def shelf(c, career):
    return {x['id']: inv.count(c, x['id']) for x in inv.catalogue(career)}


def empty(c, career, keep=()):
    for lot in c['ext']['inv']['lots']:
        if lot['item'] not in keep:
            lot['qty'] = 0


def run(s, c, orders=None):
    first = min(x['at'] for x in c['ops']['business']['pending'].values())
    wb.settle(s, first + (100000 if orders is None else 3000 * orders))
    return wb._recent(c)


class StaffRevenue(unittest.TestCase):
    def test_fixed_part_passes_whole_and_zero_changes_nothing(self):
        for stars in range(1, 6):
            self.assertEqual(staff_market.staff_revenue(100, stars, 5, 60), staff_market.staff_revenue(100, stars, 5, 60, 100, 0))
        # A 330 xu vehicle with a 15 xu fee at a 1-star service: the vehicle is never sold under its list price.
        low = staff_market.staff_revenue(345, 1, 4, 313, 100, 330, True)
        self.assertGreaterEqual(low, 330 + 15 * 84 // 100)
        self.assertLess(staff_market.staff_revenue(345, 1, 4, 313), 313)   # without it, a loss (the old reason to skip cars)
        self.assertLessEqual(staff_market.staff_revenue(345, 5, 4, 330, 100, 330, True), 345)   # capped at the owner's sale


class CarDealerStaff(unittest.TestCase):
    def test_sells_the_stocked_vehicles_not_only_helmets(self):
        s, c, e = sample('car_dealer')
        empty(c, 'car_dealer', keep=('dx_mu',))
        for k in ('dx_xe_dien', 'dx_xe_so', 'dx_xe_ga'):
            inv.add_lot(c, k, 6, car_dealer.ITEM[k]['cost'], 999, 'test')
        before = shelf(c, 'car_dealer')
        wb.refresh(c, 'car_dealer', 2000000001)
        rows = run(s, c, 12)
        sold = {}
        for r in rows:
            for i, q in r['items'].items():
                sold[i] = sold.get(i, 0) + q
        self.assertGreaterEqual(len([i for i in sold if i in CD.MODELS]), 2, rows)
        after = shelf(c, 'car_dealer')
        self.assertGreaterEqual(c['ops']['business']['served'], 12)
        for r in rows:
            (item, qty), = r['items'].items()
            self.assertLessEqual(qty, before[item])
            if item in CD.MODELS:
                m = CD.MODELS[item]
                fee = car_dealer.PRICES['dv_dang_ky_xm' if m['kind'] == 'xm' else 'dv_dang_ky_ot']
                self.assertEqual(qty, 1)
                self.assertGreater(r['revenue'] - r['expenses'], 0, r)            # never a loss
                self.assertLessEqual(r['revenue'], m['price'] + fee, r)            # never above the owner's own sale
                self.assertTrue(r['label'].startswith('Đơn riêng: '), r)
        used = c['ops']['business_used']   # every unit the staff sold left the shelf, nothing else did
        self.assertEqual({i: before[i] - after[i] for i in before if before[i] != after[i]}, used)
        ops.validate(c, 'car_dealer')

    def test_never_sells_what_is_not_on_the_shelf(self):
        s, c, e = sample('car_dealer')
        empty(c, 'car_dealer')
        inv.add_lot(c, 'dx_xe_so', 2, car_dealer.ITEM['dx_xe_so']['cost'], 999, 'test')
        wb.refresh(c, 'car_dealer', 2000000001)
        rows = run(s, c)
        self.assertEqual([r['items'] for r in rows], [{'dx_xe_so': 1}, {'dx_xe_so': 1}])
        self.assertEqual(inv.count(c, 'dx_xe_so'), 0)
        self.assertEqual(c['ops']['business']['reason'], 'stock')
        ops.validate(c, 'car_dealer')

    def test_next_order_shows_a_vehicle_at_its_list_price(self):
        s, c, e = sample('car_dealer')
        empty(c, 'car_dealer')
        inv.add_lot(c, 'dx_xe_ga', 1, car_dealer.ITEM['dx_xe_ga']['cost'], 999, 'test')
        wb.refresh(c, 'car_dealer', 2000000001)
        nxt = wb.public(c, 2000000001)['next_order']
        self.assertIn('xe tay ga', nxt['label'])
        self.assertGreater(nxt['revenue_low'], nxt['goods'] + nxt['wage'] + nxt['materials'])   # never a loss
        self.assertLessEqual(nxt['revenue'], CD.MODELS['dx_xe_ga']['price'] + car_dealer.PRICES['dv_dang_ky_xm'])
        self.assertGreater(nxt['margin'], 0)


class JewelryStaff(unittest.TestCase):
    def test_sells_every_stocked_piece_at_the_board_price(self):
        s, c, e = sample('jewelry')
        before = shelf(c, 'jewelry')
        rows = run(s, c)
        self.assertGreater(c['ops']['business']['served'], 3)
        sold = {i for r in rows for i in r['items']}
        self.assertGreater(len(sold), 3, sold)
        self.assertNotEqual(sold, {'vg_lac_bac'})
        for r in rows:
            (item, qty), = r['items'].items()
            self.assertEqual(qty, 1)
            self.assertLessEqual(qty, before[item])
            x = JW.PIECES[item]
            owner = so._piece_value(c, item) + jewelry.PRICES[x['cong']]
            cost = jewelry.ITEM[item]['cost']   # the opening shelf is free: count what the piece costs to buy again
            self.assertGreater(r['revenue'] - r['cash_expenses'] - cost, 0, r)
            self.assertLessEqual(r['revenue'], owner, r)   # never above the owner's own sale (gold + stone + tiền công)
        ops.validate(c, 'jewelry')


class CounterShopsStaff(unittest.TestCase):
    def test_canteen_and_stationery_sell_across_the_counter(self):
        for career, material in (('canteen', set()), ('stationery', {'vp_giay_boc', 'vp_nhan', 'vp_a4'})):
            with self.subTest(career=career):
                s, c, e = sample(career)
                before = shelf(c, career)
                rows = run(s, c, 12)
                sold = {i for r in rows for i in r['items']}
                self.assertGreater(len(sold), 3, sold)
                self.assertFalse(sold & material)   # the owner's bọc vở / photo materials stay
                cost = so.costs(career)
                for r in rows:
                    (item, qty), = r['items'].items()
                    price = inv.item(career, item)['price']
                    profit = r['revenue'] - r['cash_expenses'] - cost[item] * qty
                    self.assertGreater(profit, 0, r)
                    self.assertLessEqual(profit, (price - cost[item]) * qty, r)   # ≤ the owner's own margin on that basket
                after = shelf(c, career)
                for item in sold:
                    self.assertLess(after[item], before[item])
                ops.validate(c, career)


if __name__ == '__main__':
    unittest.main()
