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
        self.assertLessEqual(promised['express'] - now, 30, 'express: 15–30 minutes')
        self.assertLessEqual(promised['partner'] - now, 3 * 60, 'the next of four van runs')
        self.assertEqual(promised['market'] // inventory.DAY_MIN, 1, 'ordered before 13:00: the market comes this afternoon')
        self.assertEqual(promised['market'] % inventory.DAY_MIN, 15 * 60)
        self.assertIn(promised['import'] // inventory.DAY_MIN, (2, 3), 'imports take 1–2 days')

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
    def test_market_afternoon_run_then_morning_drop_at_start_day(self):
        j = Journey('restaurant')
        empty(j.c, 'beef')
        early, _ = order(j, 'beef', 2, 'market')
        self.assertEqual(divmod(early['lo'], inventory.DAY_MIN), (1, 15 * 60), 'ordered before 13:00: this afternoon')
        self.assertIn('nay', pub_order(j, early['id'])['eta_label'].lower())
        # Work on until the 13:00 cut-off of the afternoon run has passed.
        while public_inv(j)['clock']['minute'] < 13 * 60:
            j.act('advance')
        late, _ = order(j, 'beef', 2, 'market')
        op = inventory.hours('restaurant')[0]
        self.assertEqual(late['lo'], 2 * inventory.DAY_MIN + op - 75, 'after it: the night run, before opening tomorrow')
        self.assertIn('mai', pub_order(j, late['id'])['eta_label'])
        wait_until_ready(j, early['id'])
        self.assertEqual(j.c['day'], 1, 'the afternoon run comes the same day')
        j.act('inv_receive', order=early['id'], count=early['actual'])
        j.act('end_day', carry_event=True)
        # Closed for the night: tomorrow's drop is not at the door yet.
        po = pub_order(j, late['id'])
        self.assertFalse(po['ready_now'])
        self.assertIn('mở cửa', po['left_label'])
        with self.assertRaises(GameError):
            j.act('inv_receive', order=late['id'], count=late['actual'])
        j.act('start_day')
        if not late['late']:
            self.assertTrue(pub_order(j, late['id'])['ready_now'], 'the morning drop is there when the day opens')
        wait_until_ready(j, late['id'])
        j.act('inv_receive', order=late['id'], count=late['actual'])
        validate_state(j.state)

    def test_an_evening_cut_off_still_means_the_day_after_tomorrow(self):
        # Suppliers may still close their night run early (the pharmacy depot, older tables).
        sup = dict(kind='next', cutoff=17 * 60, at=(-75, -35))
        op = inventory.hours('restaurant')[0]
        day = 4 * inventory.DAY_MIN
        self.assertEqual(inventory._promise(sup, 'restaurant', day + 16 * 60)[0], day + inventory.DAY_MIN + op - 75)
        self.assertEqual(inventory._promise(sup, 'restaurant', day + 17 * 60)[0], day + 2 * inventory.DAY_MIN + op - 75)
        self.assertEqual(inventory._window_label(sup, 'restaurant'), 'Sáng mai · đặt trước 17:00')

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

    def test_orders_placed_before_the_halving_keep_their_promise(self):
        """In-flight orders keep the window they were promised: never re-promised,
        never stranded, delivered once."""
        j = Journey('restaurant')
        empty(j.c, 'beef')
        o, _ = order(j, 'beef', 2, 'import')
        day, op = j.c['day'], inventory.hours('restaurant')[0]
        # What the old import table (2–3 days, 11:00–13:00) promised this morning's order.
        old_at = (day + 3) * inventory.DAY_MIN + op + 120
        o.update(lo=old_at - 60, hi=old_at + 60, at=old_at, late=None)
        p, _ = order(j, 'noodle', 2, 'partner')
        # The old van's afternoon run: 16:30–17:30 today.
        p.update(lo=day * inventory.DAY_MIN + 990, hi=day * inventory.DAY_MIN + 1050, at=day * inventory.DAY_MIN + 1020, late=None)
        validate_state(j.state)
        po = pub_order(j, o['id'])
        self.assertEqual(po['window'], f'11:00–13:00 · ngày {day + 3}')
        self.assertEqual(po['left_label'], 'còn 3 ngày')
        wait_until_ready(j, p['id'])
        self.assertEqual(public_inv(j)['clock']['abs'] // inventory.DAY_MIN, day)
        self.assertGreaterEqual(public_inv(j)['clock']['abs'], p['at'])
        j.act('inv_receive', order=p['id'], count=p['actual'])
        wait_until_ready(j, o['id'], limit=200)
        self.assertEqual(j.c['day'], day + 3, 'arrives on the promised day, not earlier or later')
        self.assertEqual(j.c['ext']['inv']['orders'][0]['at'], old_at, 'the stored window is kept')
        j.act('inv_receive', order=o['id'], count=o['actual'])
        with self.assertRaises(GameError):
            j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertEqual(sum(l['qty'] for l in j.c['ext']['inv']['lots'] if l['item'] == 'beef'), o['actual'])
        validate_state(j.state)


# ------------------------------------------------------------ waits halved (2026-09-29)
# A frozen copy of the supplier timing before the owner asked for half the wait.
OLD_MARKET = dict(kind='next', cutoff=17 * 60, at=(-75, -35), late=10)
OLD_PARTNER = dict(kind='runs', runs=((660, 780, 840), (900, 990, 1050)), late=8)
OLD_EXPRESS = dict(kind='rush', mins=(30, 60), late=12)


def _old_days(days, at, late):
    return dict(kind='days', days=days, at=at, late=late)


OLD_TABLE = {
    'restaurant': {'market': OLD_MARKET, 'partner': OLD_PARTNER, 'express': OLD_EXPRESS,
                   'import': _old_days((2, 3), (60, 180), 15)},
    'cafe_bakery': {'market': OLD_MARKET, 'partner': OLD_PARTNER, 'express': OLD_EXPRESS,
                    'roaster': dict(kind='next', cutoff=18 * 60, at=(180, 240), late=8)},
    'florist': {'market': dict(OLD_MARKET, cutoff=22 * 60), 'dalat': dict(kind='next', cutoff=15 * 60, at=(60, 150), late=15),
                'partner': OLD_PARTNER, 'express': OLD_EXPRESS},
    'grocery': {'market': OLD_MARKET, 'partner': OLD_PARTNER, 'express': OLD_EXPRESS,
                'wholesale': _old_days((1, 2), (120, 240), 10)},
    'repair': {'market': dict(OLD_MARKET, cutoff=16 * 60), 'partner': OLD_PARTNER, 'express': OLD_EXPRESS,
               'genuine': _old_days((2, 3), (60, 240), 15)},
    'farm': {'coop': dict(kind='next', cutoff=16 * 60, at=(60, 120), late=8), 'partner': OLD_PARTNER, 'express': OLD_EXPRESS,
             'nursery': _old_days((2, 3), (90, 240), 12)},
    'delivery': {'market': dict(OLD_MARKET, cutoff=23 * 60 + 30, at=(-240, -120)),
                 'partner': dict(kind='rush', mins=(120, 240), late=8), 'express': OLD_EXPRESS},
    'homestay': {'market': OLD_MARKET, 'partner': OLD_PARTNER, 'express': OLD_EXPRESS,
                 'textile': _old_days((2, 3), (120, 300), 10)},
    'pet_care': {'wholesale': OLD_MARKET, 'partner': OLD_PARTNER, 'express': OLD_EXPRESS,
                 'import': _old_days((2, 3), (60, 240), 15)},
    'salon': {'market': OLD_MARKET, 'partner': OLD_PARTNER, 'express': OLD_EXPRESS,
              'brand': _old_days((2, 3), (60, 240), 12)},
}


def old_arrival(sup, career, now, seed):
    """The arrival the old rules picked (frozen copy of the old _promise + _schedule)."""
    import random
    day_min, r5 = inventory.DAY_MIN, inventory._r5
    rnd = random.Random(seed)
    op, cl = inventory.hours(career)
    day, minute = divmod(now, day_min)
    k = sup['kind']
    if k == 'days':
        d = day + rnd.randint(*sup['days'])
        lo, hi = r5(d * day_min + op + sup['at'][0]), r5(d * day_min + op + sup['at'][1])
    else:
        if k == 'rush':
            lo, hi = now + sup['mins'][0], now + sup['mins'][1]
        elif k == 'runs':
            run = next((r for r in sup['runs'] if minute < r[0]), None)
            d = day if run else day + 1
            run = run or sup['runs'][0]
            lo, hi = d * day_min + run[1], d * day_min + run[2]
        else:
            d = day + (1 if minute < sup['cutoff'] else 2)
            lo, hi = d * day_min + op + sup['at'][0], d * day_min + op + sup['at'][1]
        lo, hi = r5(lo), r5(hi)
        if k == 'rush' and hi > day * day_min + cl:
            lo = hi = (day + 1) * day_min + op - inventory.EARLY
        elif hi % day_min > cl and hi // day_min == lo // day_min:
            lo = hi = inventory._after_hours(hi, career)
    at = min(hi, max(lo, r5(rnd.randint(lo, hi))))
    if rnd.randrange(100) < sup['late']:
        extra = day_min if k == 'days' else rnd.randint(15, 30) if k == 'rush' else rnd.randint(60, 120)
        return max(inventory._after_hours(r5(hi + extra), career), hi + 5)
    return at


def working_minutes(career, now, at):
    """Opening-hours minutes between an order and its arrival: the time the player
    works through while waiting (the night passes with one tap)."""
    day_min = inventory.DAY_MIN
    op, cl = inventory.hours(career)
    d0, d1 = now // day_min, at // day_min
    clip = lambda m: max(op, min(cl, m))
    if d0 == d1:
        return max(0, clip(at % day_min) - clip(now % day_min))
    return (cl - clip(now % day_min)) + (d1 - d0 - 1) * (cl - op) + (clip(at % day_min) - op)


def mean_waits(pick, seeds=20):
    """Average wait per supplier kind for orders placed every STEP of a working day."""
    work, clock = {}, {}
    for cid, old in OLD_TABLE.items():
        op, cl = inventory.hours(cid)
        for sid in old:
            sup = inventory.supplier(cid, sid)
            w, c = [], []
            for m in range(op, cl + 1, inventory.STEP):
                now = 5 * inventory.DAY_MIN + m
                for k in range(seeds):
                    at = pick(cid, sid, old[sid], sup, now, f'{cid}:{sid}:{m}:{k}')
                    w.append(working_minutes(cid, now, at))
                    c.append(at - now)
            work.setdefault(sup['kind'], []).append(sum(w) / len(w))
            clock.setdefault(sup['kind'], []).append(sum(c) / len(c))
    avg = lambda d: {k: sum(v) / len(v) for k, v in d.items()}
    return avg(work), avg(clock)


class HalfWait(unittest.TestCase):
    """Owner, 2026-09-29: restocking felt slow; every supplier kind now waits about half as long."""

    @classmethod
    def setUpClass(cls):
        cls.old = mean_waits(lambda cid, sid, old, sup, now, seed: old_arrival(old, cid, now, seed))
        cls.new = mean_waits(lambda cid, sid, old, sup, now, seed: inventory._schedule(sup, cid, now, seed)['at'])

    def test_every_kind_waits_about_half_as_long(self):
        old_work, old_clock = self.old
        new_work, new_clock = self.new
        self.assertEqual(set(old_work), {'rush', 'runs', 'next', 'days'})
        for kind in old_work:
            with self.subTest(kind=kind):
                # Working time waited: 50 % ± 10 % of the old wait.
                self.assertTrue(0.45 <= new_work[kind] / old_work[kind] <= 0.55,
                                f'{kind}: {old_work[kind]:.0f} → {new_work[kind]:.0f} working minutes')
                # Clock time (nights included) about halves too.
                self.assertTrue(0.40 <= new_clock[kind] / old_clock[kind] <= 0.60,
                                f'{kind}: {old_clock[kind]:.0f} → {new_clock[kind]:.0f} clock minutes')

    def test_the_frozen_table_matches_the_live_suppliers(self):
        for cid, old in OLD_TABLE.items():
            live = {s['id']: s for s in inventory.suppliers(cid)}
            self.assertEqual(set(old), set(live), cid)
            for sid, sup in old.items():
                self.assertEqual(sup['kind'], live[sid]['kind'], f'{cid}/{sid}')
                # Same chance of a late delivery as before; the delay itself is shorter.
                self.assertEqual(sup['late'], live[sid]['late'], f'{cid}/{sid}')

    def test_late_deliveries_are_shorter_not_rarer(self):
        old_extra = {'rush': 30, 'runs': 120, 'next': 120, 'days': inventory.DAY_MIN}
        for cid in STOCKED:
            for sup in inventory.suppliers(cid):
                with self.subTest(career=cid, supplier=sup['id']):
                    a, b = sup['delay']
                    self.assertLessEqual(b, old_extra[sup['kind']] / 2, 'at most half the old delay')
                    self.assertTrue(0 < a <= b)

    def test_minimum_waits(self):
        for cid in STOCKED:
            for sup in inventory.suppliers(cid):
                if sup['kind'] == 'rush':
                    self.assertGreaterEqual(sup['mins'][0], 15)
                if sup['kind'] == 'days':
                    self.assertGreaterEqual(sup['days'][0], 1, 'special goods come the next day at the earliest')
        # An express order is never at the door in the same action: at least one step passes.
        j = Journey('grocery')
        o, _ = order(j, 'egg', 2, 'express')
        with self.assertRaises(GameError):
            j.act('inv_receive', order=o['id'], count=o['actual'])
        self.assertLessEqual(wait_until_ready(j, o['id']), 3)

    def test_labels_tell_the_new_numbers(self):
        self.assertEqual(inventory._window_label(inventory.EXPRESS, 'restaurant'), '15–30 phút')
        self.assertEqual(inventory._window_label(inventory.PARTNER, 'restaurant'), 'Bốn chuyến/ngày · 10:00, 13:00, 16:00 & 19:00')
        self.assertEqual(inventory._window_label(inventory.MARKET, 'restaurant'), 'Chiều nay nếu đặt trước 13:00, sau đó sáng mai')
        self.assertEqual(inventory._window_label(inventory.supplier('restaurant', 'import'), 'restaurant'), '1–2 ngày')
        self.assertEqual(inventory._window_label(inventory.supplier('grocery', 'wholesale'), 'grocery'), '1 ngày')
        self.assertEqual(inventory._window_label(inventory.supplier('delivery', 'partner'), 'delivery'), '1–2 giờ')
        self.assertEqual(inventory._window_label(inventory.supplier('delivery', 'market'), 'delivery'),
                         'Tối nay nếu đặt trước 20:00, sau đó chiều mai')
        old = ('30–60', '2–3 ngày', '2–4 giờ', 'Hai chuyến', 'hai chuyến', 'trước 17:00', 'trễ một ngày', 'trễ vài')
        for cid in STOCKED:
            for sup in inventory.suppliers(cid):
                with self.subTest(career=cid, supplier=sup['id']):
                    texts = [sup['note'], inventory._window_label(sup, cid), *sup['voice'].values()]
                    self.assertFalse([t for t in texts for o in old if o in t])
                    k = sup['kind']
                    if k == 'rush':
                        self.assertIn(inventory._window_label(sup, cid), sup['note'])
                    elif k == 'days' and sup['days'][0] != sup['days'][1]:
                        self.assertIn(f'{sup["days"][0]}–{sup["days"][1]} ngày', sup['note'])
                    elif k == 'next':
                        self.assertIn(f'trước {inventory.hm(sup["day_run"][0])}', sup['note'])
                    elif k == 'runs':
                        self.assertIn('bốn chuyến', sup['note'])
                        for r in sup['runs']:
                            self.assertIn(inventory.hm(r[0]), sup['note'])
        # The live quote on a supplier card, in the stock room of a phone player.
        j = Journey('grocery')
        cards = {s['id']: s for s in public_inv(j)['suppliers']}
        self.assertIn('phút · tới ~', cards['express']['quote']['label'])
        self.assertEqual(cards['wholesale']['quote']['label'], f'1 ngày · ngày {j.c["day"] + 1}')
        self.assertEqual(cards['wholesale']['quote']['eta_label'], f'Ngày {j.c["day"] + 1}')
        self.assertTrue(cards['market']['quote']['label'].startswith('Chiều nay'))


if __name__ == '__main__':
    unittest.main()
