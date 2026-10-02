"""Milk-tea counter (1.4.4, player confusion: 1,616 "Chưa đủ xu" refusals on tea_prepare in three days):
a paid tap the server must refuse is drawn disabled with its reason instead of being sent. The client's
rules (milk_tea.js prepPlan, orderWhy) read only the public view; these tests mirror them in Python over
boba.public() and check every verdict against the server itself."""
import copy
import unittest

from game import boba
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey


def pub(j):
    return public_state(j.state)['careers']['milk_tea']['data']['boba']


def money(j):
    return public_state(j.state)['careers']['milk_tea']['money']


def set_fund(j, cash):
    """The shop fund at `cash` xu, its ledger kept in step (operations.validate)."""
    j.c['ops']['finance']['opening_balance'] += cash - j.c['money']
    j.c['money'] = cash


def station(p, item):
    return next(s for s in p['stations'] if s['id'] == item)


def prep_plan(j, item):
    """milk_tea.js prepPlan: (qty, why). Five, or as many as the fund pays and the shelf takes."""
    p, cash = pub(j), money(j)
    unit, cap, held = boba.ING[item]['cost'], p['shelf_cap'], station(p, item)['held']
    room = max(0, cap - held)
    if not room:
        return 0, f'Kho đầy {held}/{cap}'
    qty = min(5, room, cash // unit if unit else 5)
    if qty < 1:
        return 0, f'Thiếu {unit - cash} xu'
    return qty, ''


def order_why(j, item, qty, supplier):
    """milk_tea.js orderWhy over the public view ('' when the order goes through)."""
    p, cash = pub(j), money(j)
    sup = next(s for s in p['suppliers'] if s['id'] == supplier)
    pending = p['pending'].get(item, 0)
    if len(p['orders']) >= p['max_orders']:
        return f"Đang chờ {len(p['orders'])}/{p['max_orders']} đơn"
    if item.startswith('cup_'):
        base, pack, cap = p['cup_pack']['cost'], p['cup_pack']['qty'], p['cup_cap']
        have = p['cups'][item[4:]] + pending * pack
        if have + qty * pack > cap:
            return 'Chồng ly'
    else:
        base, cap = boba.ING[item]['cost'], p['shelf_cap']
        have = station(p, item)['held'] + pending
        if have + qty > cap:
            return 'Kho'
    cost = max(1, round(qty * base * sup['factor']))
    return f'Thiếu {cost - cash} xu' if cost > cash else ''


class Refused(unittest.TestCase):
    def assertRefused(self, j, action, **payload):
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act(action, **payload)
        self.assertEqual(j.state, before)


class PublicLimits(Refused):
    def test_the_view_carries_the_limits_and_what_counts_against_the_shelf(self):
        j = Journey('milk_tea')
        p = pub(j)
        self.assertEqual((p['shelf_cap'], p['max_orders'], p['cup_cap']), (boba.SHELF_CAP, boba.MAX_ORDERS, boba.CUP_CAP))
        held = boba.held(j.c)
        for s in p['stations']:
            self.assertEqual(s['held'], held[s['id']])
        self.assertEqual(money(j), j.c['money'])


class PreparePlan(Refused):
    def test_short_fund_offers_what_it_can_pay_and_refuses_none(self):
        j = Journey('milk_tea')
        unit = boba.ING['pearls']['cost']
        set_fund(j, unit * 2 + 1)
        self.assertEqual(prep_plan(j, 'pearls'), (2, ''))
        self.assertRefused(j, 'tea_prepare', item='pearls', qty=3, confirm=True)   # the full +5 would be refused
        j.act('tea_prepare', item='pearls', qty=2, confirm=True)                   # the offered +2 goes through
        self.assertEqual(j.c['money'], 1)
        qty, why = prep_plan(j, 'pearls')
        self.assertEqual((qty, why), (0, f'Thiếu {unit - 1} xu'))
        self.assertRefused(j, 'tea_prepare', item='pearls', qty=1, confirm=True)
        validate_state(j.state)

    def test_a_full_shelf_is_named_and_refused(self):
        j = Journey('milk_tea')
        set_fund(j, 10_000)
        cap = boba.SHELF_CAP
        held = boba.held(j.c)['foam']
        boba.add_lot(j.state, j.c, 'foam', cap - held - 2, boba.ING['foam']['cost'])
        self.assertEqual(prep_plan(j, 'foam'), (2, ''))
        self.assertRefused(j, 'tea_prepare', item='foam', qty=3, confirm=True)
        j.act('tea_prepare', item='foam', qty=2, confirm=True)
        self.assertEqual(prep_plan(j, 'foam'), (0, f'Kho đầy {cap}/{cap}'))
        self.assertRefused(j, 'tea_prepare', item='foam', qty=1, confirm=True)

    def test_every_made_item_the_plan_allows_goes_through(self):
        for cash in (0, 3, 9, 14, 200):
            j = Journey('milk_tea')
            set_fund(j, cash)
            for s in pub(j)['stations']:
                if not (s['made'] and s['unlocked']):
                    continue
                qty, why = prep_plan(j, s['id'])
                if why:
                    self.assertRefused(j, 'tea_prepare', item=s['id'], qty=1, confirm=True)
                else:
                    before = j.c['money']
                    j.act('tea_prepare', item=s['id'], qty=qty, confirm=True)
                    self.assertEqual(j.c['money'], before - qty * boba.ING[s['id']]['cost'])


class OrderWhy(Refused):
    def test_orders_waiting_shelf_and_fund(self):
        j = Journey('milk_tea')
        set_fund(j, 10_000)
        items = [i for i in boba.BOUGHT if boba.unlocked(j.c, i)]
        n = 0
        while len(st_orders(j)) < boba.MAX_ORDERS:
            item = items[n % len(items)]
            self.assertEqual(order_why(j, item, 1, 'express'), '')
            j.act('tea_order', item=item, qty=1, supplier='express', confirm=True)
            n += 1
        why = order_why(j, items[0], 1, 'express')
        self.assertEqual(why, f'Đang chờ {boba.MAX_ORDERS}/{boba.MAX_ORDERS} đơn')
        self.assertRefused(j, 'tea_order', item=items[0], qty=1, supplier='express', confirm=True)

    def test_shelf_counts_what_is_on_the_way(self):
        j = Journey('milk_tea')
        set_fund(j, 10_000)
        held = boba.held(j.c)['lychee']
        boba.add_lot(j.state, j.c, 'lychee', boba.SHELF_CAP - held - 6, boba.ING['lychee']['cost'])
        j.act('tea_order', item='lychee', qty=5, supplier='express', confirm=True)
        self.assertEqual(order_why(j, 'lychee', 1, 'express'), '')
        self.assertTrue(order_why(j, 'lychee', 2, 'express').startswith('Kho'))
        self.assertRefused(j, 'tea_order', item='lychee', qty=2, supplier='express', confirm=True)
        j.act('tea_order', item='lychee', qty=1, supplier='express', confirm=True)

    def test_short_fund(self):
        j = Journey('milk_tea')
        set_fund(j, 5)
        why = order_why(j, 'lychee', 5, 'express')
        cost = max(1, round(5 * boba.ING['lychee']['cost'] * boba.SUP_INDEX['express']['factor']))
        self.assertEqual(why, f'Thiếu {cost - 5} xu')
        self.assertRefused(j, 'tea_order', item='lychee', qty=5, supplier='express', confirm=True)
        set_fund(j, cost)
        self.assertEqual(order_why(j, 'lychee', 5, 'express'), '')
        j.act('tea_order', item='lychee', qty=5, supplier='express', confirm=True)
        self.assertEqual(j.c['money'], 0)


def st_orders(j):
    return j.c['ext']['data']['boba']['orders']


if __name__ == '__main__':
    unittest.main()
