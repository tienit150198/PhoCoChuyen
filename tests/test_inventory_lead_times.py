"""Supplier lead times on the shop clock (docs/superpowers/specs/2026-09-29-supplier-lead-times.md).

Every supplier promises a window in time of day, suppliers differ, deliveries
due before the next opening are at the door when the day starts, a late van is
announced once its promise has passed and never loses goods, and saves from
the beat-based days keep working.
"""
import copy
import re
import unittest
from pathlib import Path

from game import inventory
from game.engine import GameError, public_state, validate_state
from game.careers import PLUGINS
from tests.helpers import Journey
from tests.test_inventory_flow import empty, public_inv, wait_until_ready

ROOT = Path(__file__).resolve().parent.parent
STOCKED = [cid for cid, mod in PLUGINS.items() if mod.SPEC.get('inventory')]


def order(j, item, qty, supplier):
    r = j.act('inv_order', item=item, qty=qty, supplier=supplier, confirm=True)
    return j.c['ext']['inv']['orders'][-1], r


def pub_order(j, oid):
    return next(x for x in public_inv(j)['orders'] if x['id'] == oid)


class Clock(unittest.TestCase):
    def test_turns_become_minutes_from_opening_to_closing(self):
        j = Journey('restaurant')
        op, cl = inventory.hours('restaurant')
        clk = public_inv(j)['clock']
        self.assertTrue(clk['is_open'])
        self.assertEqual(clk['minute'], op)
        self.assertEqual(clk['time'], '10:00')
        j.act('inv_wait')
        j.act('advance')
        self.assertEqual(public_inv(j)['clock']['minute'], op + 2 * inventory.STEP)
        # Work never runs the clock past closing time.
        for _ in range((cl - op) // inventory.STEP + 5):
            j.act('advance')
        self.assertEqual(public_inv(j)['clock']['minute'], cl)
        j.act('end_day', carry_event=True)
        # Closed: the evening of the day that just closed.
        clk = public_inv(j)['clock']
        self.assertFalse(clk['is_open'])
        self.assertEqual((clk['day'], clk['minute']), (1, cl))
        self.assertIn('mở lại 10:00 ngày 2', clk['label'])
        j.act('start_day')
        self.assertEqual(public_inv(j)['clock']['minute'], op)
        self.assertEqual(public_inv(j)['clock']['day'], 2)

    def test_every_stocked_career_has_hours(self):
        for cid in STOCKED:
            op, cl = inventory.hours(cid)
            self.assertLess(op, cl, cid)
            self.assertGreaterEqual((cl - op) // inventory.STEP, 18, f'{cid}: a working day holds enough actions')


class Suppliers(unittest.TestCase):
    def test_two_to_five_real_choices_per_career(self):
        for cid in STOCKED:
            with self.subTest(career=cid):
                sups = inventory.suppliers(cid)
                ids = [s['id'] for s in sups]
                self.assertTrue(2 <= len(sups) <= 5)
                self.assertEqual(len(ids), len(set(ids)))
                # Other code sends these two ids for every stocked career.
                self.assertIn('partner', ids)
                self.assertIn('express', ids)
                catalogue = {i['id'] for i in inventory.catalogue(cid)}
                for s in sups:
                    self.assertTrue(set(s.get('items') or catalogue) <= catalogue, s['id'])
                    self.assertTrue(s['note'] and s['voice'].get('late'), s['id'])
                # Every item can be bought from at least two suppliers.
                for i in catalogue:
                    self.assertGreaterEqual(sum(inventory.sells(s, i) for s in sups), 2, i)
                # A real trade-off: different windows and different prices.
                self.assertGreaterEqual(len({s['kind'] for s in sups}), 2)
                self.assertGreaterEqual(len({s['factor'] for s in sups}), 2)
                self.assertEqual(max(sups, key=lambda s: s['factor'])['kind'], 'rush', 'the fastest costs the most')

    def test_suppliers_promise_different_waits(self):
        j = Journey('restaurant')
        promised = {}
        for sid, item in (('express', 'egg'), ('partner', 'egg'), ('market', 'egg'), ('import', 'pack_kimchi')):
            o, r = order(j, item, 2, sid)
            promised[sid] = o['lo']
            self.assertNotIn('nhịp', r['message'])
            self.assertEqual(r['eta']['order'], o['id'])
        self.assertLess(promised['express'], promised['partner'])
        self.assertLess(promised['partner'], promised['market'])
        self.assertLess(promised['market'], promised['import'])
        now = public_inv(j)['clock']['abs']
        self.assertLessEqual(promised['express'] - now, 60)
        self.assertEqual(promised['market'] // inventory.DAY_MIN, 2, 'the market comes tomorrow')
        self.assertGreaterEqual(promised['import'] // inventory.DAY_MIN, 3, 'imports take 2–3 days')

    def test_quote_matches_the_order_placed_next(self):
        j = Journey('florist')
        for sid in [s['id'] for s in inventory.suppliers('florist')]:
            sup = inventory.supplier('florist', sid)
            item = next(i['id'] for i in inventory.catalogue('florist') if inventory.sells(sup, i['id']))
            q = next(s for s in public_inv(j)['suppliers'] if s['id'] == sid)['quote']
            o, _ = order(j, item, 1, sid)
            if sup['kind'] == 'days':
                self.assertTrue(q['lo'] // inventory.DAY_MIN <= o['lo'] // inventory.DAY_MIN <= q['hi'] // inventory.DAY_MIN)
            else:
                self.assertEqual((o['lo'], o['hi']), (q['lo'], q['hi']), sid)

    def test_supplier_must_sell_the_item(self):
        j = Journey('restaurant')
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError) as err:
            order(j, 'box', 2, 'market')
        self.assertIn('không bán', str(err.exception))
        self.assertEqual(j.state, before)
        with self.assertRaises(GameError):
            order(j, 'noodle', 2, 'dalat')  # a florist supplier

    def test_dalat_flowers_stay_fresh_a_day_longer(self):
        j = Journey('florist')
        empty(j.c, 'rose_red')
        empty(j.c, 'rose_pink')
        life = inventory.item('florist', 'rose_red')['life']
        a, _ = order(j, 'rose_red', 3, 'dalat')
        b, _ = order(j, 'rose_pink', 3, 'partner')
        wait_until_ready(j, a['id'])
        wait_until_ready(j, b['id'])
        j.act('inv_receive', order=a['id'], count=a['actual'])
        j.act('inv_receive', order=b['id'], count=b['actual'])
        days = public_inv(j)['days_left']
        self.assertEqual(days['rose_red'], life + 1)
        self.assertEqual(days['rose_pink'], inventory.item('florist', 'rose_pink')['life'])


class Arrival(unittest.TestCase):
    def test_market_cut_off_and_morning_drop_at_start_day(self):
        j = Journey('restaurant')
        empty(j.c, 'beef')
        early, _ = order(j, 'beef', 2, 'market')
        # Work on until the 17:00 cut-off has passed.
        while public_inv(j)['clock']['minute'] < 17 * 60:
            j.act('advance')
        late, _ = order(j, 'beef', 2, 'market')
        self.assertEqual(early['lo'] // inventory.DAY_MIN, 2)
        self.assertEqual(late['lo'] // inventory.DAY_MIN, 3, 'after the cut-off: the day after tomorrow')
        self.assertIn('ngày kia', pub_order(j, late['id'])['eta_label'])
        j.act('end_day', carry_event=True)
        # Closed for the night: tomorrow's drop is not at the door yet.
        po = pub_order(j, early['id'])
        self.assertFalse(po['ready_now'])
        self.assertIn('mở cửa', po['left_label'])
        with self.assertRaises(GameError):
            j.act('inv_receive', order=early['id'], count=early['actual'])
        j.act('start_day')
        if not early['late']:
            self.assertTrue(pub_order(j, early['id'])['ready_now'], 'the morning drop is there when the day opens')
        wait_until_ready(j, early['id'])
        j.act('inv_receive', order=early['id'], count=early['actual'])
        self.assertFalse(pub_order(j, late['id'])['ready_now'])
        validate_state(j.state)

    def test_goods_due_this_evening_wait_at_the_door_after_closing(self):
        j = Journey('restaurant')
        o, _ = order(j, 'noodle', 2, 'partner')
        self.assertFalse(pub_order(j, o['id'])['ready_now'])
        j.act('end_day', carry_event=True)
        if not o['late']:
            self.assertTrue(pub_order(j, o['id'])['ready_now'])
            j.act('inv_receive', order=o['id'], count=o['actual'])

    def test_express_after_closing_comes_before_next_opening(self):
        j = Journey('restaurant')
        j.act('end_day', carry_event=True)
        o, r = order(j, 'egg', 2, 'express')
        op = inventory.hours('restaurant')[0]
        self.assertEqual(o['lo'], 2 * inventory.DAY_MIN + op - inventory.EARLY)
        self.assertIn('mai', r['message'])

    def test_a_late_van_is_announced_after_the_promise_and_never_loses_goods(self):
        old = inventory.EXPRESS['late']
        inventory.EXPRESS['late'] = 100
        try:
            j = Journey('restaurant')
            empty(j.c, 'egg')
            o, _ = order(j, 'egg', 4, 'express')
        finally:
            inventory.EXPRESS['late'] = old
        self.assertTrue(o['late'])
        self.assertGreater(o['at'], o['hi'])
        po = pub_order(j, o['id'])
        self.assertIsNone(po['late_note'], 'no spoiler before the promised time')
        self.assertNotIn('late', po)
        self.assertNotIn('at', po)
        while public_inv(j)['clock']['abs'] < o['hi']:
            j.act('inv_wait')
        po = pub_order(j, o['id'])
        if not po['ready_now']:
            self.assertEqual(po['late_note'], inventory.EXPRESS['voice']['late'])
            self.assertEqual(po['arrives_time'], inventory.hm(o['at'] % inventory.DAY_MIN))
        wait_until_ready(j, o['id'])
        j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertEqual(sum(l['qty'] for l in j.c['ext']['inv']['lots'] if l['item'] == 'egg'), o['actual'])
        validate_state(j.state)

    def test_reliability_is_seeded(self):
        a, b = Journey('grocery'), Journey('grocery')
        for j in (a, b):
            for sid in ('market', 'partner', 'express', 'wholesale'):
                order(j, 'noodle' if sid == 'wholesale' else 'egg', 2, sid)
        strip = lambda j: [{k: o[k] for k in ('lo', 'hi', 'at', 'late', 'actual')} for o in j.c['ext']['inv']['orders']]
        self.assertEqual(strip(a), strip(b))

    def test_wait_needs_an_open_shop(self):
        j = Journey('restaurant')
        j.act('end_day', carry_event=True)
        with self.assertRaises(GameError):
            j.act('inv_wait')


class Wording(unittest.TestCase):
    def test_no_beats_in_the_ordering_flow(self):
        j = Journey('restaurant')
        texts = []
        o, r = order(j, 'noodle', 3, 'partner')
        texts.append(r['message'])
        try:
            j.act('inv_receive', order=o['id'], count=o['actual'])
        except GameError as err:
            texts.append(str(err))
        texts.append(j.act('inv_wait')['message'])
        pub = public_inv(j)
        texts += [pub['clock']['label']]
        for s in pub['suppliers']:
            texts += [s['note'], s['window'], s['quote']['label'], *s['voice'].values()]
        for x in pub['orders']:
            texts += [x['eta_label'], x['window'], x['left_label']]
        for cid in STOCKED:
            for s in inventory.suppliers(cid):
                texts += [s['note'], s['name'], inventory._window_label(s, cid)]
        self.assertFalse([t for t in texts if 'nhịp' in t.lower()])

    def test_stock_sheet_has_no_beats(self):
        src = (ROOT / 'public/js/v4/views.js').read_text(encoding='utf-8')
        sheet = src[src.index('/* ---------------------------------------------------------------- Stock'):src.index('/* ------------------------------------------------------------ Feedback')]
        self.assertFalse(re.findall(r'nhịp', sheet, re.I))


class OldSaves(unittest.TestCase):
    def legacy(self, j, wait):
        o, _ = order(j, 'noodle', 2, 'partner')
        for k in ('placed', 'lo', 'hi', 'at', 'late'):
            o.pop(k)
        o['ready'] = j.c['turn'] + wait
        return o

    def test_beat_orders_become_clock_orders(self):
        j = Journey('restaurant')
        o = self.legacy(j, 2)
        validate_state(j.state)  # a save from before this change still loads
        po = pub_order(j, o['id'])
        self.assertFalse(po['ready_now'])
        self.assertEqual(po['left_label'], 'còn ~40 phút')
        # The next inventory action upgrades the stored order.
        j.act('inv_wait')
        stored = j.c['ext']['inv']['orders'][-1]
        self.assertNotIn('ready', stored)
        self.assertEqual(stored['lo'], stored['hi'])
        validate_state(j.state)
        j.act('inv_wait')
        self.assertTrue(pub_order(j, o['id'])['ready_now'])
        j.act('inv_receive', order=o['id'], count=o['actual'])

    def test_migrate_hook_and_already_due_orders(self):
        j = Journey('restaurant')
        due = self.legacy(j, 0)
        done = self.legacy(j, 1)
        done['status'] = 'received'
        inventory.migrate(j.state)
        self.assertTrue(all('ready' not in o and 'at' in o for o in j.c['ext']['inv']['orders']))
        validate_state(j.state)
        self.assertTrue(pub_order(j, due['id'])['ready_now'])

    def test_validate_stays_strict(self):
        j = Journey('restaurant')
        o, _ = order(j, 'noodle', 2, 'partner')
        for bad in (dict(ready=5), dict(at=o['lo'] - 5), dict(hi=o['lo'] - 5), dict(late='Trễ'), dict(late=None, at=o['hi'] + 60),
                    dict(supplier='dalat'), dict(placed='x')):
            s = copy.deepcopy(j.state)
            s['careers']['restaurant']['ext']['inv']['orders'][-1].update(bad)
            with self.assertRaises(GameError, msg=str(bad)):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['restaurant']['ext']['inv']['opened'] = dict(day=1, turn=10**6)
        with self.assertRaises(GameError):
            validate_state(s)

    def test_content_keeps_the_shared_supplier_list(self):
        from game.content import public_content
        inv = public_content()['inventory']
        self.assertEqual([s['id'] for s in inv['suppliers']], ['market', 'partner', 'express'])
        self.assertTrue(all(isinstance(s['lead'], int) and s['window'] for s in inv['suppliers']))
        self.assertEqual(set(inv['by_career']), set(STOCKED))


if __name__ == '__main__':
    unittest.main()
