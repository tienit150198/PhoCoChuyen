"""Bigger shelves (player #277, owner 09/10: "nâng tổng kho ... lên 60 hoặc 80", "đặt tối đa 30 lên 60-80").

Shipped in two releases so a rollback never strands a save: the first only ACCEPTS saves holding up to
SAVE_STOCK units of an item and order or draft lines of up to SAVE_LINE units (and receives such a crate),
while its own orders keep LINE_MAX and capacity(); the second raises the limits themselves.
"""
import copy
import unittest

from game import inventory as I
from game.engine import GameError, validate_state
from tests.test_inventory_cart import fresh, add
from tests.test_inventory_flow import wait_until_ready


def big_order(j, item, qty, short=0):
    """An order line written by the release with bigger shelves: a real order, scaled up."""
    oid = j.act('inv_order', item=item, qty=1, supplier='express', confirm=True)['eta']['order']
    o = next(o for o in j.c['ext']['inv']['orders'] if o['id'] == oid)
    o.update(qty=qty, actual=qty - short)
    return oid


def fill(j, item, qty):
    """`qty` units of `item` on the shelf, one lot."""
    x = j.c['ext']['inv']
    x['lots'] = [l for l in x['lots'] if l['item'] != item]
    x['seq'] += 1
    x['lots'].append(dict(id=f'lot-{x["seq"]}', item=item, qty=qty, unit_cost=3, expires=j.c['day'] + 5,
                          received=j.c['day'], supplier='partner'))


class SaveLimits(unittest.TestCase):
    def test_saves_hold_bigger_stock_orders_and_drafts(self):
        self.assertGreaterEqual(I.SAVE_STOCK, 80)
        self.assertGreaterEqual(I.SAVE_LINE, 80)
        for career in ('restaurant', 'clothing', 'grocery', 'garbage', 'drain', 'com'):
            self.assertGreaterEqual(I.stock_limit(career), max(80, I.capacity(career)), career)
        j = fresh()
        fill(j, 'noodle', I.stock_limit('restaurant'))
        big_order(j, 'egg', I.SAVE_LINE, short=2)
        add(j, 'partner', 'beef', 5)
        j.c['ext']['inv']['cart']['partner']['lines'][0]['qty'] = I.SAVE_LINE
        validate_state(j.state)
        for bad in ('stock', 'order', 'draft'):
            s = copy.deepcopy(j.state)
            x = s['careers']['restaurant']['ext']['inv']
            if bad == 'stock':
                next(l for l in x['lots'] if l['item'] == 'noodle')['qty'] += 1
            elif bad == 'order':
                next(o for o in x['orders'] if o['item'] == 'egg')['qty'] = I.SAVE_LINE + 1
            else:
                x['cart']['partner']['lines'][0]['qty'] = I.SAVE_LINE + 1
            with self.assertRaises(GameError, msg=bad):
                validate_state(s)

    def test_a_whole_big_lot_wasted_is_a_valid_row(self):
        j = fresh()
        j.c['life']['waste'].append(dict(day=j.c['day'], item='noodle', qty=120, value=120 * 310, reason='Bỏ lô không đạt'))
        validate_state(j.state)

    def test_orders_keep_this_release_line_max(self):
        j = fresh(money=50000)
        with self.assertRaises(GameError):
            j.act('inv_order', item='noodle', qty=I.LINE_MAX + 1, supplier='partner', confirm=True)
        with self.assertRaises(GameError):
            add(j, 'partner', 'noodle', I.LINE_MAX + 1)
        add(j, 'partner', 'noodle', I.LINE_MAX)
        with self.assertRaises(GameError):
            add(j, 'partner', 'noodle', 1)


class BigCrate(unittest.TestCase):
    """A crate bigger than LINE_MAX can only come from the release with bigger shelves (a rollback): it is
    counted and received like any other, against stock_limit(), never stranded at the door."""

    def test_big_crate_is_received(self):
        j = fresh()
        qty = I.SAVE_LINE
        oid = big_order(j, 'noodle', qty, short=1)
        wait_until_ready(j, oid)
        with self.assertRaises(GameError):
            j.act('inv_receive', order=oid, count=qty)  # the slip, not what is in the crate
        j.act('inv_receive', order=oid, count=qty - 1)
        self.assertEqual(I.count(j.c, 'noodle'), qty - 1)
        validate_state(j.state)


if __name__ == '__main__':
    unittest.main()
