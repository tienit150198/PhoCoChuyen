"""Cash by hand (game/careers/till.py): the customer's notes, the change the player counts and
what the customer does about it — delivery COD at the door and the homestay checkout bill."""
import copy
import json
import unittest
from unittest import mock

import game.careers.kit as kit
from game.engine import GameError, public_state, validate_state
from game.careers import delivery as D
from game.careers import homestay as H
from game.careers import till
from tests.helpers import Journey


def ledger(j, tid, category=None):
    rows = [r for r in j.c['ops']['finance']['ledger'] if r['ref'] == tid]
    return [r for r in rows if category is None or r['category'] == category]


def review(j, tid):
    return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)


def crit(post, key):
    return next(x['score'] for x in post['feedback']['criteria'] if x['key'] == key)


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t


class TillTests(unittest.TestCase):
    def test_tender_covers_the_price_from_real_notes_and_never_rerolls(self):
        for price in range(1, 620):
            for seed in ('homestay-0003-02', 'delivery-0010-05', f'x{price}'):
                notes = till.tender(price, seed)
                self.assertGreaterEqual(sum(notes), price)
                self.assertTrue(1 <= len(notes) <= 20 and all(n in till.DENOMS for n in notes))
                self.assertEqual(notes, till.tender(price, seed))
                self.assertLess(sum(notes) - price, max(price, 500))        # nobody pays 30 xu with 1000

    def test_greedy_change_is_exact(self):
        for amount in range(0, 1200):
            self.assertEqual(sum(till.greedy(amount)), amount)

    def test_record_validates_and_rejects_bad_trays(self):
        rec = till.new(37, 'homestay-0003-02')
        till.validate(rec)
        with self.assertRaises(GameError):
            till.notes([3])
        with self.assertRaises(GameError):
            till.notes([1] * 41)
        bad = dict(rec, tender=[1])
        with self.assertRaises(GameError):
            till.validate(bad)


# ---------------------------------------------------------------- homestay checkout
def cash_checkout(pred=lambda t, due: True):
    """A plain checkout guest who pays cash, a bill above 0 and change to count."""
    for day in range(1, 60):
        for slot in range(12):
            t = H.make_task(day, slot, 1)
            if t['job'] != 'checkout' or t['_x'].get('case') or t['_x']['lost'] or not H._pays_cash(t):
                continue
            total = H._bill_total(H._truth_bill(t))
            if total and pred(t, sum(till.tender(total, t['id'])) - total):
                return day, slot
    raise AssertionError('no cash checkout')


class HomestayCashTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def start(self, pred=lambda t, due: due > 0, bill=0):
        day, slot = cash_checkout(pred)
        j = Journey('homestay', slot=slot, day=day)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('hs_inspect', task=tid)
        truth = H._truth_bill(j.task)
        for k, q in truth.items():
            for _ in range(q):
                j.act('hs_line', task=tid, line=k, delta=1)
        for _ in range(bill):
            j.act('hs_line', task=tid, line='damage' if not truth['damage'] else 'late' if not truth['late'] else 'laundry', delta=1)
        return j, tid

    def view(self, j, tid):
        return next(t for t in public_state(j.state)['careers']['homestay']['tasks'] if t['id'] == tid)

    def test_the_guest_notes_are_shown_and_follow_the_bill(self):
        j, tid = self.start()
        v = self.view(j, tid)
        total = H._bill_total(j.task['bill'])
        self.assertEqual((v['pay'], v['cash']['price']), ('cash', total))
        self.assertEqual(v['cash']['tender'], till.tender(total, tid))
        self.assertEqual(v['cash']['due'], sum(v['cash']['tender']) - total)
        j.act('hs_line', task=tid, line='late', delta=1 if not j.task['bill']['late'] else -1)
        self.assertEqual(self.view(j, tid)['cash']['price'], H._bill_total(j.task['bill']))

    def test_sweep_every_cash_bill_can_be_paid_back_from_the_tray(self):
        n = 0
        for day in range(1, 40):
            for slot in range(12):
                t = H.make_task(day, slot, 1)
                if t['job'] != 'checkout':
                    continue
                total = H._bill_total(H._truth_bill(t))
                if not total or not H._pays_cash(t):
                    continue
                due = sum(till.tender(total, t['id'])) - total
                self.assertGreaterEqual(due, 0)
                self.assertEqual(sum(till.greedy(due)), due)
                n += 1
        self.assertGreater(n, 20)

    def test_right_change_books_the_bill_once(self):
        j, tid = self.start()
        cash = self.view(j, tid)['cash']
        with mock.patch.object(till, 'waves_off', return_value=False):
            r = j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due']))
        t = j.get(tid)
        self.assertEqual((t['status'], t['cash']['outcome'], t['cash']['tip']), ('completed', 'exact', 0))
        self.assertIn('tiền mặt', r['message'])
        self.assertEqual(sum(x['amount'] for x in ledger(j, tid, 'revenue')), cash['price'])
        self.assertEqual(t.get('slips') or [], [])
        self.assertEqual(crit(review(j, tid), 'cash'), 5)
        with self.assertRaises(GameError):
            j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due']))
        validate_state(json.loads(json.dumps(j.state)))

    def test_keep_the_change_is_a_tip_paid_once(self):
        j, tid = self.start(lambda t, due: 0 < due <= till.KEEP_MAX)
        cash = self.view(j, tid)['cash']
        with mock.patch.object(till, 'waves_off', return_value=True):
            r = j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due']))
        t = j.get(tid)
        self.assertIn('Khỏi thối', r['message'])
        self.assertEqual((t['tip_given'], t['cash']['outcome'], t['cash']['tip']), (cash['due'], 'keep', cash['due']))
        tips = [x for x in ledger(j, tid, 'tip') if x['reason'].startswith('Khách cho giữ tiền thối')]
        self.assertEqual([x['amount'] for x in tips], [cash['due']])
        self.assertEqual(sum(x['amount'] for x in ledger(j, tid, 'revenue')), cash['price'])
        money = j.c['money']
        with self.assertRaises(GameError):
            j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due']))
        self.assertEqual(j.c['money'], money)
        validate_state(json.loads(json.dumps(j.state)))

    def test_short_change_a_careful_guest_asks_for_the_rest(self):
        j, tid = self.start(lambda t, due: due >= 2)
        cash = self.view(j, tid)['cash']
        money = j.c['money']
        short = till.greedy(cash['due'] - 1)
        with mock.patch.object(till, 'careful', return_value=True):
            r = j.act('hs_settle', task=tid, confirm=True, change=short)
        self.assertTrue(r.get('refused'))
        self.assertIn('Thối thiếu 1 xu', r['message'])
        t = j.get(tid)
        self.assertEqual((t['status'], t['cash']['asked'], j.c['money']), ('in_progress', 1, money))
        self.assertEqual(self.view(j, tid)['cash']['asked'], 1)
        # Still short: once they caught it, they count every time (whatever the dice say).
        with mock.patch.object(till, 'careful', return_value=False):
            self.assertTrue(j.act('hs_settle', task=tid, confirm=True, change=short).get('refused'))
        j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due']))
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual([(x['code'], x['sev']) for x in t['slips']], [('change_short', 1)])
        self.assertEqual((t['reaction']['kind'], t['reaction']['cut']), ('accept', 0))     # complained once, no money off
        self.assertEqual(sum(x['amount'] for x in ledger(j, tid, 'revenue')), cash['price'])
        post = review(j, tid)
        self.assertLessEqual(post['stars'], 4)
        self.assertEqual(crit(post, 'cash'), 4)
        self.assertIn('Thối thiếu', post['text'])
        self.assertFalse(t.get('tip_given'))
        validate_state(json.loads(json.dumps(j.state)))

    def test_short_change_nobody_counts_is_found_at_home(self):
        j, tid = self.start(lambda t, due: due >= 2)
        cash = self.view(j, tid)['cash']
        with mock.patch.object(till, 'careful', return_value=False):
            j.act('hs_settle', task=tid, confirm=True, change=[])
        t = j.get(tid)
        self.assertEqual((t['status'], t['cash']['outcome'], t['cash']['short']), ('completed', 'missed', cash['due']))
        self.assertEqual([(x['code'], x['sev']) for x in t['slips']], [('change_home', 3)])
        self.assertEqual(t['reaction']['kind'], 'accept')       # they left happy, then counted at home
        post = review(j, tid)
        self.assertLessEqual(post['stars'], 2)
        self.assertIn('thối thiếu', post['text'])
        self.assertEqual(crit(post, 'cash'), 2)
        self.assertEqual(sum(x['amount'] for x in ledger(j, tid, 'tip')), 0)
        validate_state(json.loads(json.dumps(j.state)))

    def test_missed_short_change_can_bring_a_report(self):
        j, tid = self.start(lambda t, due: due >= 20)
        with mock.patch.object(till, 'careful', return_value=False):
            r = j.act('hs_settle', task=tid, confirm=True, change=[])
        self.assertIn('báo cáo', r['message'])
        self.assertTrue(any(p.get('report') for p in j.c['feed']))

    def test_excess_change_honest_guest_gives_it_back(self):
        j, tid = self.start()
        cash = self.view(j, tid)['cash']
        with mock.patch.object(till, 'honest', return_value=True):
            r = j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due'] + 5))
        t = j.get(tid)
        self.assertEqual((t['cash']['outcome'], t['cash']['over'], t['cash']['loss']), ('returned', 5, 0))
        self.assertIn('trả lại 5 xu', r['message'])
        self.assertEqual(sum(x['amount'] for x in ledger(j, tid, 'revenue')), cash['price'])
        self.assertEqual(t.get('slips') or [], [])

    def test_excess_change_kept_is_the_house_loss(self):
        j, tid = self.start()
        cash = self.view(j, tid)['cash']
        with mock.patch.object(till, 'honest', return_value=False):
            r = j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due'] + 5))
        t = j.get(tid)
        self.assertEqual((t['cash']['outcome'], t['cash']['loss']), ('kept', 5))
        self.assertIn('thối dư 5 xu', r['message'])
        self.assertEqual(sum(x['amount'] for x in ledger(j, tid, 'revenue')), cash['price'] - 5)
        self.assertEqual(crit(review(j, tid), 'cash'), 4)
        validate_state(json.loads(json.dumps(j.state)))

    def test_overcharge_nobody_reads_is_paid_back_and_reviewed(self):
        j, tid = self.start(bill=1)
        truth = H._bill_total(H._truth_bill(j.task))
        total = H._bill_total(j.task['bill'])
        cash = self.view(j, tid)['cash']
        with mock.patch.object(till, 'careful', return_value=False):
            r = j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due']))
        t = j.get(tid)
        self.assertEqual((t['status'], t['overpaid']), ('completed', total - truth))
        self.assertIn('tính dư', r['message'])
        self.assertEqual([x['amount'] for x in ledger(j, tid, 'refund')], [-(total - truth)])
        self.assertIn('overcharge_home', [x['code'] for x in t['slips']])
        post = review(j, tid)
        self.assertLessEqual(post['stars'], 3)
        self.assertEqual(crit(post, 'bill'), 2)
        validate_state(json.loads(json.dumps(j.state)))

    def test_overcharge_caught_is_named_but_takes_no_money_off_the_fixed_bill(self):
        j, tid = self.start(bill=1)
        with mock.patch.object(till, 'careful', return_value=True):
            self.assertTrue(j.act('hs_settle', task=tid, confirm=True).get('refused'))
        truth = H._truth_bill(j.task)
        for k, q in truth.items():
            while j.task['bill'][k] > q:
                j.act('hs_line', task=tid, line=k, delta=-1)
        cash = self.view(j, tid)['cash']
        j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due']))
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual([x['code'] for x in t['slips']], ['overcharge'])
        self.assertEqual(t['reaction']['cut'], 0)
        self.assertEqual(sum(x['amount'] for x in ledger(j, tid, 'revenue')), H._bill_total(truth))
        self.assertIn('tính dư', review(j, tid)['text'])

    def test_transfer_guest_needs_no_change(self):
        for day in range(1, 60):
            hit = next((s for s in range(12) if (lambda t: t['job'] == 'checkout' and not t['_x'].get('case') and not t['_x']['lost']
                                                 and not H._pays_cash(t) and H._bill_total(H._truth_bill(t)))(H.make_task(day, s, 1))), None)
            if hit is not None:
                break
        j = Journey('homestay', slot=hit, day=day)
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('hs_inspect', task=tid)
        for k, q in H._truth_bill(j.task).items():
            for _ in range(q):
                j.act('hs_line', task=tid, line=k, delta=1)
        v = next(t for t in public_state(j.state)['careers']['homestay']['tasks'] if t['id'] == tid)
        self.assertEqual((v['pay'], v['cash']), ('transfer', None))
        r = j.act('hs_settle', task=tid, confirm=True)
        self.assertIn('chuyển khoản', r['message'])
        self.assertIsNone(j.get(tid).get('cash'))

    def test_old_checkout_save_without_cash_fields_loads(self):
        j, tid = self.start()
        cash = self.view(j, tid)['cash']
        j.act('hs_settle', task=tid, confirm=True, change=till.greedy(cash['due']))
        state = json.loads(json.dumps(j.state))
        for t in state['careers']['homestay']['tasks']:
            for k in ('cash', 'overpaid', 'tip_given'):
                t.pop(k, None)
        validate_state(state)
        state['careers']['homestay']['tasks'][0]['cash'] = dict(till.new(cash['price'], 'someone-else'), outcome='exact')
        state['careers']['homestay']['tasks'][0]['cash']['tender'] = [1] * (cash['price'] + 1) if cash['price'] < 19 else [500, 500]
        with self.assertRaises(GameError):
            validate_state(state)


# ---------------------------------------------------------------- delivery COD
def cod_journey(key):
    from tests.test_career_delivery import journey
    return journey(key)


class DeliveryCashTests(unittest.TestCase):
    def door(self, key='F4'):
        from tests.test_career_delivery import ride, wait_until
        j, tid = cod_journey(key)
        n = j.get(tid)['needs']
        ride(j, n['pickup'])
        wait_until(j, j.get(tid)['run']['t0'] + n['prep'])
        j.act('dl_check', task=tid)
        j.act('dl_load', task=tid)
        j.act('dl_plan', route=[n['dest']])
        j.act('dl_ride', way='main')
        return j, tid

    def test_every_cod_order_has_change_the_courier_can_count(self):
        notes = D.content().get('notes') or [50, 20, 10, 5, 2, 1]
        for o in D.ORDERS:
            if not o['cod']:
                continue
            right = o['cash'] - o['cod']
            self.assertGreaterEqual(right, 0, o['key'])
            left = right
            for v in notes:
                left -= left // v * v
            self.assertEqual(left, 0, o['key'])
            self.assertGreaterEqual(right + D.DISCOUNT if o['cod'] >= D.DISCOUNT else right, right)

    def test_keep_the_change_is_the_couriers_tip_once(self):
        j, tid = self.door()
        n = j.get(tid)['needs']
        right = n['cash'] - n['cod']
        with mock.patch.object(till, 'waves_off', return_value=True):
            r = j.act('dl_deliver', task=tid, change=right)
        t = j.get(tid)
        self.assertIn('Khỏi thối', r['message'])
        self.assertEqual((t['tip_given'], t['run']['tip'], t['run']['change']), (right, right, 0))
        tips = [x for x in ledger(j, tid, 'tip') if x['reason'].startswith('Khách cho giữ tiền thối')]
        self.assertEqual([x['amount'] for x in tips], [right])
        self.assertEqual(j.c['ext']['data']['bag'], n['cod'])        # the post office's money is all there
        with self.assertRaises(GameError):
            j.act('dl_deliver', task=tid, change=right)
        validate_state(json.loads(json.dumps(j.state)))

    def test_excess_change_given_back_by_an_honest_customer(self):
        j, tid = self.door()
        n = j.get(tid)['needs']
        with mock.patch.object(till, 'honest', return_value=True):
            r = j.act('dl_deliver', task=tid, change=n['cash'] - n['cod'] + 10)
        t = j.get(tid)
        self.assertIn('trả lại 10 xu', r['message'])
        self.assertEqual((t['run']['returned'], t['run']['over'], j.c['ext']['data']['bag']), (True, 10, n['cod']))
        self.assertEqual(t.get('slips') or [], [])
        validate_state(json.loads(json.dumps(j.state)))

    def test_careful_customer_stops_the_hand_over_without_moving_the_clock(self):
        j, tid = self.door()
        d = j.c['ext']['data']
        with mock.patch.object(till, 'careful', return_value=True):
            j.act('dl_deliver', task=tid, change=0)
        clock, mistakes = d['clock'], j.get(tid)['mistakes']
        j.act('dl_deliver', task=tid, change=0)
        self.assertEqual((j.c['ext']['data']['clock'], j.get(tid)['run']['asked']), (clock, 2))
        self.assertEqual(j.get(tid)['mistakes'], mistakes + 1)
        self.assertEqual(j.get(tid).get('slips') or [], [])      # named in the review once it is handed over

    def test_old_run_without_cash_fields_loads(self):
        j, tid = self.door()
        state = json.loads(json.dumps(j.state))
        for t in state['careers']['delivery']['tasks']:
            for k in D.RUN_V4:
                t['run'].pop(k, None)
        validate_state(state)
        self.assertTrue(all(set(D.RUN_V4) <= set(t['run']) for t in state['careers']['delivery']['tasks']))


class TraceableTotalsTests(unittest.TestCase):
    """The money a job pays can be worked out from what the player is shown."""

    def test_farm_bill_line_math_adds_up_to_the_pay(self):
        import itertools
        import re
        from game.careers import farm as F
        c = Journey('farm').c
        crops = [x['id'] for x in F.CROPS][:3]
        seen = 0
        for kind, organic, label in itertools.product(('market', 'shop'), (False, True), ('organic', 'plain')):
            for want, a, b in itertools.product((1, 3), (0, 1, 2, 4), (0, 1, 3)):
                items = {crops[0]: want, crops[1]: 2}
                crate = [dict(crop=crops[0], grade='A', qty=a, day=c['day'], expires=c['day'] + 3),
                         dict(crop=crops[0], grade='B', qty=b, day=c['day'], expires=c['day'] + 3),
                         dict(crop=crops[1], grade='A', qty=1, day=c['day'], expires=c['day'] + 3)]
                t = dict(needs=dict(items=items, kind=kind, organic=organic), crate=[x for x in crate if x['qty']], label=label)
                pay = F._evaluate(c, t)['pay']
                text = F._bill(c, t)
                m = re.fullmatch(r'\((.*)\) × (\d+)% nhãn hữu cơ', text)
                inner = m.group(1) if m else text
                total = sum(int(q) * int(p) for q, p in re.findall(r'(\d+) [^×+]*?× (\d+)', inner))
                if m:
                    total = total * int(m.group(2)) // 100
                self.assertEqual(total, pay, text)
                seen += 1
        self.assertGreater(seen, 100)

    def test_repair_comeback_fee_uses_the_price_board_labor(self):
        from game.careers import repair as R
        c = Journey('repair').c
        dev = 'phone'
        fault = R.FAULTS[dev][0]
        row = dict(device=dev, fault=fault['id'], grade=next(iter(fault['parts'])))
        base = R._back_fee(c, row)[1]
        with mock.patch.object(R.kit, 'price', side_effect=lambda c, k, v: v * 2 if k == dev else v):
            dear = R._back_fee(c, row)[1]
        self.assertGreater(dear, base)


if __name__ == '__main__':
    unittest.main()
