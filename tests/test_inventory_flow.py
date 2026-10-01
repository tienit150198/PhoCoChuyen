"""Buying and stocking, end to end through the reducer (v0.4 inventory).

order → arrive (on the shop clock) → count and receive → shelve → sell, plus the guard rails:
no overdraw, no over-capacity orders, no double receipt, one claim and one
rating per order, expiry at closing and a bounded order book that never
forgets goods still on the way.
"""
import copy
import unittest

import game.careers.kit as kit
from game import inventory
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def empty(c, item):
    c['ext']['inv']['lots'] = [l for l in c['ext']['inv']['lots'] if l['item'] != item]


def set_money(c, amount):
    # Keep the wallet identity (opening balance + ledger == money) intact.
    c['ops']['finance']['opening_balance'] += amount - c['money']
    c['money'] = amount


def public_inv(j):
    return public_state(j.state)['careers'][j.career]['inventory']


def wait_until_ready(j, oid, limit=120):
    """Let shop time pass (20 minutes a wait, a new day when the shop has
    closed) until the order is at the door. Returns how many waits it took."""
    for n in range(limit):
        pub = public_inv(j)
        if next(x for x in pub['orders'] if x['id'] == oid)['ready_now']:
            return n
        clk = pub['clock']
        if clk['is_open'] and clk['minute'] < clk['close']:
            j.act('inv_wait')
        else:
            if clk['is_open']:
                j.act('end_day', carry_event=True)
            j.act('start_day')
    raise AssertionError(f'order {oid} never arrived')


class InventoryFlow(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock
        self.j = Journey('restaurant')

    def tearDown(self):
        kit.clock = self.old

    def order(self, item='noodle', qty=6, supplier='partner'):
        self.j.act('inv_order', item=item, qty=qty, supplier=supplier, confirm=True)
        return self.j.c['ext']['inv']['orders'][-1]

    def test_order_arrive_receive_shelve_sell(self):
        j = self.j
        empty(j.c, 'noodle')
        money = j.c['money']
        o = self.order('noodle', 6)
        # Goods plus the supplier's shipping fee (0.9.20: one fee per order, free above a line).
        self.assertEqual(j.c['money'], money - o['cost'] - o['ship'])
        self.assertEqual(kit.stock(j.c, 'noodle'), 0, 'paid goods are not on the shelf before counting')
        pub = public_inv(j)
        self.assertEqual(pub['arriving']['noodle'], 6)
        po = next(x for x in pub['orders'] if x['id'] == o['id'])
        self.assertFalse(po['ready_now'])
        self.assertIsNone(po['count_hint'])
        self.assertNotIn('actual', po, 'the real count stays hidden until the box is opened')
        self.assertTrue(po['eta_label'] and po['window'] and po['left_label'])
        self.assertNotIn('at', po, 'the real arrival stays hidden until it happens')
        # Straight after ordering the distributor's van has not come.
        with self.assertRaises(GameError) as err:
            j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertIn('Dự kiến', str(err.exception))
        self.assertNotIn('nhịp', str(err.exception))
        self.assertGreater(wait_until_ready(j, o['id']), 0)
        po = next(x for x in public_inv(j)['orders'] if x['id'] == o['id'])
        self.assertTrue(po['ready_now'])
        self.assertNotIn('actual', po)
        # A wrong count is rejected and changes nothing.
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('inv_receive', order=o['id'], count=o['actual'] + 1)
        self.assertEqual(j.state, before)
        j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertEqual(kit.stock(j.c, 'noodle'), o['actual'])
        self.assertEqual(j.c['ext']['inv']['orders'][-1]['status'], 'received')
        pub = public_inv(j)
        self.assertEqual(pub['arriving']['noodle'], 0)
        self.assertEqual(pub['stock']['noodle'], o['actual'])
        lot = next(l for l in j.c['ext']['inv']['lots'] if l['item'] == 'noodle')
        self.assertEqual(lot['unit_cost'], o['unit_cost'])
        # No double receipt.
        with self.assertRaises(GameError):
            j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertEqual(kit.stock(j.c, 'noodle'), o['actual'])
        # Selling a bowl uses one portion from the shelf.
        j.act('ask')
        j.act('rs_container', kind='bowl')
        j.act('rs_boil')
        self.assertEqual(kit.stock(j.c, 'noodle'), o['actual'] - 1)
        validate_state(j.state)

    def test_taking_more_than_stock_is_rejected(self):
        c = self.j.c
        empty(c, 'noodle')
        inventory.add_lot(c, 'noodle', 2, 1, 3, 'partner')
        with self.assertRaises(GameError):
            inventory.take(c, 'noodle', 3)
        self.assertEqual(kit.stock(c, 'noodle'), 2)
        self.assertEqual(inventory.take(c, 'noodle', 2), 2)
        self.assertEqual(kit.stock(c, 'noodle'), 0)
        with self.assertRaises(GameError):
            self.j.act('rs_container', kind='bowl') or self.j.act('rs_boil')

    def test_order_without_money_is_rejected(self):
        j = self.j
        set_money(j.c, 3)
        validate_state(j.state)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError) as err:
            self.order('noodle', 10)
        self.assertIn('Chưa đủ xu', str(err.exception))
        self.assertEqual(j.state, before)

    def test_order_needs_confirmation(self):
        j = self.j
        with self.assertRaises(GameError):
            j.act('inv_order', item='noodle', qty=2, supplier='partner')
        with self.assertRaises(GameError):
            j.act('inv_order', item='noodle', qty=2, supplier='nobody', confirm=True)
        with self.assertRaises(GameError):
            j.act('inv_order', item='noodle', qty=0, supplier='partner', confirm=True)

    def test_over_capacity_counts_goods_on_the_way(self):
        j = self.j
        cap = inventory.capacity('restaurant')
        empty(j.c, 'noodle')
        inventory.add_lot(j.c, 'noodle', cap - 12, 1, 3, 'partner')
        self.order('noodle', 10)
        self.assertEqual(public_inv(j)['room']['noodle'], 2)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError) as err:
            self.order('noodle', 3)
        self.assertIn('đang giao', str(err.exception))
        self.assertEqual(j.state, before)
        self.order('noodle', 2)
        self.assertEqual(public_inv(j)['room']['noodle'], 0)

    def test_receive_when_shelf_filled_meanwhile_says_why(self):
        j = self.j
        cap = inventory.capacity('restaurant')
        empty(j.c, 'noodle')
        o = self.order('noodle', 5)
        # Goods bought elsewhere (market, gifts) filled the shelf meanwhile.
        inventory.add_lot(j.c, 'noodle', cap - 1, 1, 3, 'market')
        wait_until_ready(j, o['id'])
        with self.assertRaises(GameError) as err:
            j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertIn('chỉ còn chỗ cho 1', str(err.exception))
        inventory.take(j.c, 'noodle', cap - 1)
        j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertEqual(kit.stock(j.c, 'noodle'), o['actual'])

    def test_express_arrives_within_the_hour(self):
        j = self.j
        empty(j.c, 'egg')
        o = self.order('egg', 4, 'express')
        po = next(x for x in public_inv(j)['orders'] if x['id'] == o['id'])
        self.assertFalse(po['ready_now'])
        self.assertIn('phút', po['left_label'])
        # 30–60 minutes (a late courier adds at most 30): a few 20-minute waits.
        waits = wait_until_ready(j, o['id'])
        self.assertGreaterEqual(waits, 1)
        self.assertLessEqual(waits, 5)
        j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertEqual(kit.stock(j.c, 'egg'), 4)

    def test_short_delivery_claim_and_rating_once(self):
        j = self.j
        x = j.c['ext']['inv']
        empty(j.c, 'noodle')
        # Pick the next order number that the market packs short (deterministic).
        base = j.c['day'] * 37 + sum(map(ord, 'noodle'))
        x['seq'] = next(n for n in range(x['seq'], x['seq'] + 200) if (base + (n + 1) * 11) % 100 < 22)
        money = j.c['money']
        o = self.order('noodle', 8, 'market')
        self.assertLess(o['actual'], o['qty'])
        with self.assertRaises(GameError):
            j.act('inv_claim', order=o['id'])
        # The market delivers tomorrow before opening.
        wait_until_ready(j, o['id'])
        with self.assertRaises(GameError):
            j.act('inv_receive', order=o['id'], count=o['qty'])
        got = j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertEqual(kit.stock(j.c, 'noodle'), o['actual'])
        missing = o['qty'] - o['actual']
        # The receipt says where the claim is and what it gives back (player feedback: "khiếu nại ở đâu?").
        self.assertIn('Khiếu nại phần thiếu', got['message'])
        self.assertEqual(got['short'], dict(order=o['id'], missing=missing, refund=got['short']['refund']))
        paid = money - j.c['money']
        j.act('inv_claim', order=o['id'])
        refund = j.c['money'] - (money - paid)
        self.assertEqual(refund, got['short']['refund'])
        self.assertIn(f'{refund} xu', got['message'])
        self.assertGreater(refund, 0)
        self.assertLessEqual(refund, round(paid * missing / o['qty']) + 1)
        self.assertLess(refund, paid)
        with self.assertRaises(GameError):
            j.act('inv_claim', order=o['id'])
        j.act('inv_rate', order=o['id'], stars=2, note='Thiếu hàng')
        with self.assertRaises(GameError):
            j.act('inv_rate', order=o['id'], stars=5)
        sup = next(s for s in public_inv(j)['suppliers'] if s['id'] == 'market')
        self.assertEqual(sup['rating'], 2.0)
        validate_state(j.state)

    def test_full_delivery_cannot_be_claimed(self):
        j = self.j
        o = self.order('egg', 3, 'express')
        wait_until_ready(j, o['id'])
        got = j.act('inv_receive', order=o['id'], count=o['actual'])
        if o['actual'] == o['qty']:
            self.assertNotIn('short', got)
            self.assertNotIn('Khiếu nại', got['message'])
            with self.assertRaises(GameError):
                j.act('inv_claim', order=o['id'])

    def test_expiry_at_closing_records_waste(self):
        j = self.j
        empty(j.c, 'beef')
        life = inventory.item('restaurant', 'beef')['life']
        o = self.order('beef', 3, 'express')
        wait_until_ready(j, o['id'])
        j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertEqual(public_inv(j)['days_left']['beef'], life)
        for n in range(life):
            self.assertEqual(kit.stock(j.c, 'beef'), 3, f'still fresh on day {n + 1} of {life}')
            if n == life - 1:
                self.assertEqual(public_inv(j)['expiring']['beef'], 3)
            r = j.act('end_day', carry_event=True)
            if n < life - 1:
                self.assertEqual(r['summary']['expired_value'], 0)
                j.act('start_day')
        self.assertEqual(kit.stock(j.c, 'beef'), 0)
        self.assertEqual(r['summary']['expired_value'], 3 * o['unit_cost'])
        waste = [w for w in j.c['life']['waste'] if w['item'] == 'beef']
        self.assertEqual(waste[-1]['qty'], 3)
        self.assertEqual(waste[-1]['reason'], 'Hết hạn sử dụng')
        self.assertFalse(any(l['item'] == 'beef' for l in j.c['ext']['inv']['lots']))
        validate_state(j.state)

    def test_discard_records_waste_once(self):
        j = self.j
        lot = inventory.add_lot(j.c, 'noodle', 2, 3, 3, 'partner')
        with self.assertRaises(GameError):
            j.act('inv_discard', lot=lot['id'])
        j.act('inv_discard', lot=lot['id'], confirm=True)
        self.assertFalse(any(l['id'] == lot['id'] for l in j.c['ext']['inv']['lots']))
        with self.assertRaises(GameError):
            j.act('inv_discard', lot=lot['id'], confirm=True)

    def test_order_book_never_drops_goods_on_the_way(self):
        j = self.j
        empty(j.c, 'noodle')
        old = self.order('noodle', 1)
        x = j.c['ext']['inv']
        filler = [dict(old, id=f'po-old-{i}', status='received') for i in range(39)]
        x['orders'] = [old] + filler
        validate_state(j.state)
        new = self.order('egg', 1)
        ids = [o['id'] for o in j.c['ext']['inv']['orders']]
        self.assertEqual(len(ids), 40)
        self.assertIn(old['id'], ids, 'an unreceived paid order is kept')
        self.assertIn(new['id'], ids)
        self.assertNotIn('po-old-0', ids)
        wait_until_ready(j, old['id'])
        j.act('inv_receive', order=old['id'], count=old['actual'])
        validate_state(j.state)

    def test_shipments_cap_is_shown_before_it_refuses(self):
        # 01/10 logs: "Đang có nhiều đơn chờ giao" ×210. The stock screens read the cap from the view
        # (transit_cap) and count the orders on the way, so the order buttons turn into "receive first".
        j = self.j
        cap = public_inv(j)['transit_cap']
        set_money(j.c, 5000)
        open_ids = [i['id'] for i in inventory.catalogue('restaurant') if i.get('unlock', 1) <= kit.level(j.c)]
        for k in range(cap):
            self.order(open_ids[k % len(open_ids)], 1)
        self.assertEqual(sum(o['status'] == 'in_transit' for o in public_inv(j)['orders']), cap)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError) as err:
            self.order(open_ids[0], 1)
        self.assertIn('nhiều đơn chờ giao', str(err.exception))
        self.assertEqual(j.state, before)

    def test_locked_items_cannot_be_ordered(self):
        j = self.j
        locked = [i for i in inventory.catalogue('restaurant') if i.get('unlock', 1) > kit.level(j.c)]
        if not locked:
            self.skipTest('no locked restaurant items')
        with self.assertRaises(GameError):
            self.order(locked[0]['id'], 1)
        self.assertIn(locked[0]['id'], public_inv(j)['locked'])


class EveryStockedCareer(unittest.TestCase):
    """Each career with a stock room can order, wait, count and shelve."""

    def test_round_trip(self):
        from game.careers import PLUGINS
        for cid, mod in PLUGINS.items():
            if not mod.SPEC.get('inventory'):
                continue
            with self.subTest(career=cid):
                j = Journey(cid)
                level = kit.level(j.c)
                it = min((i for i in inventory.catalogue(cid) if i.get('unlock', 1) <= level),
                         key=lambda i: kit.stock(j.c, i['id']))
                stock = kit.stock(j.c, it['id'])
                qty = min(4, inventory.capacity(cid) - stock)
                self.assertGreater(qty, 0)
                j.act('inv_order', item=it['id'], qty=qty, supplier='partner', confirm=True)
                o = j.c['ext']['inv']['orders'][-1]
                with self.assertRaises(GameError):
                    j.act('inv_receive', order=o['id'], count=o['actual'])
                wait_until_ready(j, o['id'])
                stock = kit.stock(j.c, it['id'])  # a closing on the way may have expired old lots
                j.act('inv_receive', order=o['id'], count=o['actual'])
                self.assertEqual(kit.stock(j.c, it['id']), stock + o['actual'])
                with self.assertRaises(GameError):
                    j.act('inv_receive', order=o['id'], count=o['actual'])
                validate_state(j.state)


if __name__ == '__main__':
    unittest.main()
