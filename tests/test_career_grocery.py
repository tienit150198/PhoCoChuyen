import copy
import json
import unittest

import game.careers.kit as kit
from game import inventory
from game.engine import GameError, public_state, validate_state
from game.careers import grocery as G
from tests.helpers import Journey


_MADE = {}


def find(pred, days=range(1, 41), slots=range(8)):
    for day in days:
        for slot in slots:
            if (day, slot) not in _MADE:
                _MADE[day, slot] = G.make_task(day, slot, 1)
            if pred(_MADE[day, slot]):
                return day, slot
    raise AssertionError('no matching grocery task')


def restock(j):
    # Tests jump straight to later days: put fresh stock on the shelves, as a player would.
    for it in G.ITEMS:
        inventory.add_lot(j.c, it['id'], 20, it['cost'], it.get('life') or 999, 'partner')


def journey(title=None, kind=None, haggle=False):
    # By default pick a basket where nobody brings up the Mây Mart flyer (haggles have their own tests).
    day, slot = find(lambda t: (title is None or t['title'] == title) and (kind is None or t['kind'] == kind)
                     and (not isinstance(t['needs'], dict) or ('_haggle' in t['needs']) == haggle))
    j = Journey('grocery', slot=slot, day=day)
    restock(j)
    return j


def scan_all(j, promos=True, skip=()):
    t = j.task
    lines = t['needs']['lines']
    for i, line in enumerate(lines):
        if line.get('weighed') and line['item'] not in skip:
            j.act('gr_weigh', line=i, plu=line['item'], tare=True)
    if any(line['item'] in G.AGE_LIMITED for line in lines):
        j.act('gr_id')
    units = {}
    for line in lines:
        if not line.get('weighed'):
            units[line['item']] = units.get(line['item'], 0) + line['qty']
    for item, q in units.items():
        if item in skip or (item in G.AGE_LIMITED and j.task['age'] < 18):
            continue
        j.act('gr_scan', item=item, qty=q)
    if promos:
        for p in G.PROMOS:
            if G._discount(p, j.task['scanned'].get(p['item'], 0), G.PRICES[p['item']]) > 0:
                j.act('gr_promo', promo=p['id'])


def ledger_mark(j):
    return len(j.c['ops']['finance']['ledger'])


def paid(j, since, tid):
    """Money this task moved (tips and unrelated street events left out)."""
    return sum(e['amount'] for e in j.c['ops']['finance']['ledger'][since:] if e['ref'] == tid and e['category'] != 'tip')


def give_change(j, amount):
    for d in G._greedy(amount):
        j.act('gr_change', denom=d)


def roundtrip(j):
    validate_state(json.loads(json.dumps(j.state)))


class GroceryCheckoutTests(unittest.TestCase):
    def test_happy_cash_checkout_with_id_check(self):
        j = journey('Chú Bảy mua mồi chiều')
        tid = j.task['id']
        j.act('ask')
        before, beer = j.c['money'], kit.stock(j.c, 'beer')
        scan_all(j)
        j.act('gr_total')
        t = j.task
        self.assertEqual(t['stage'], 'pay')
        self.assertEqual(t['total'], 6 * 15 + 2 * 7 + 2 * 10)
        self.assertIn('Tiền thật', j.act('gr_check_note')['message'])
        give_change(j, sum(t['pay']['tender']) - t['total'])
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        self.assertGreaterEqual(j.c['money'], before + t['total'])
        self.assertEqual(kit.stock(j.c, 'beer'), beer - 6)
        post = next(p for p in j.c['feed'] if p.get('source') == tid)
        self.assertGreaterEqual(post['stars'], 4)
        roundtrip(j)

    def test_needs_and_secrets_hidden(self):
        j = Journey('grocery')
        view = public_state(j.state)['careers']['grocery']
        self.assertTrue(all(t['needs'] is None for t in view['tasks']))
        j.act('ask')
        view = public_state(j.state)['careers']['grocery']
        text = json.dumps(view, ensure_ascii=False)
        for secret in ('_grams', '_age', '_fake', '_transfer', '_exps', '_tag_error'):
            self.assertNotIn(secret, text)
        active = next(t for t in view['tasks'] if t['id'] == j.c['active_task'])
        self.assertIsNotNone(active['needs'])
        if active['kind'] == 'checkout':
            self.assertEqual(active['pay']['tender'], [])
        self.assertIn('ledger_view', view['data'])

    def test_minor_cannot_buy_beer(self):
        j = journey('Tí đi mua giùm ba')
        tid = j.task['id']
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('gr_total')   # empty bill
        j.act('gr_id')
        self.assertEqual(j.task['flags']['minor_refused'], 1)
        with self.assertRaises(GameError):
            j.act('gr_scan', item='beer', qty=2)
        j.act('gr_scan', item='snack', qty=1)
        j.act('gr_scan', item='soda', qty=1)
        j.act('gr_total')
        t = j.task
        self.assertEqual(t['total'], 7 + 10)
        give_change(j, sum(t['pay']['tender']) - t['total'])
        beer = kit.stock(j.c, 'beer')
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(kit.stock(j.c, 'beer'), beer)
        post = next(p for p in j.c['feed'] if p.get('source') == tid)
        self.assertIn('rules', json.dumps(post['feedback'], ensure_ascii=False))

    def test_adult_beer_without_id_is_sold_quietly(self):
        # No till lock any more: skipping the ID check only matters when the buyer is a minor.
        j = journey('Chú Bảy mua mồi chiều')
        tid = j.task['id']
        j.act('ask')
        for item, q in (('beer', 6), ('snack', 2), ('soda', 2)):
            j.act('gr_scan', item=item, qty=q)
        j.act('gr_total')
        t = j.task
        give_change(j, sum(t['pay']['tender']) - t['total'])
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t.get('slips') or [], [])

    def test_overcharge_refused_then_fixed(self):
        j = journey('Chú Bảy mua mồi chiều')
        j.act('ask')
        scan_all(j)
        j.act('gr_scan', item='snack', qty=1)
        r = j.act('gr_total')
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['stage'], 'basket')
        self.assertEqual(j.task['mistakes'], 1)
        j.act('gr_void', item='snack')
        j.act('gr_scan', item='snack', qty=2)
        j.act('gr_total')
        self.assertEqual(j.task['stage'], 'pay')

    def test_undercharge_honest_vs_quiet_customer(self):
        j = journey('Chú Bảy mua mồi chiều')
        j.act('ask')
        scan_all(j, skip=('snack',))
        self.assertTrue(j.act('gr_total').get('refused'))
        j2 = journey('Tí mua quà vặt sau giờ học')
        tid = j2.task['id']
        j2.act('ask')
        snack = kit.stock(j2.c, 'snack')
        scan_all(j2, skip=('snack',))
        j2.act('gr_total')
        t = j2.task
        self.assertEqual(t['stage'], 'pay')
        give_change(j2, sum(t['pay']['tender']) - t['total'])
        j2.act('gr_pay', confirm=True)
        self.assertEqual(kit.stock(j2.c, 'snack'), snack - 3)
        self.assertTrue(any('Quét sót' in w['reason'] for w in j2.c['life']['waste']))
        self.assertEqual(j2.get(tid)['status'], 'completed')

    def test_promo_must_be_applied(self):
        j = journey('Bữa sáng mang đi')
        tid = j.task['id']
        j.act('ask')
        scan_all(j, promos=False)
        r = j.act('gr_total')
        self.assertTrue(r.get('refused'))
        self.assertIn('khuyến mãi', r['message'])
        with self.assertRaises(GameError):
            j.act('gr_promo', promo='soda6')
        j.act('gr_promo', promo='milk4')
        j.act('gr_total')
        self.assertEqual(j.task['total'], 4 * 8 - 4 + 2 * 5)
        j.act('gr_verify')
        self.assertEqual(j.task['pay']['bank'], j.task['total'])
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 1)

    def test_transfer_without_checking_is_a_mistake(self):
        j = journey('Bữa sáng mang đi')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        self.assertEqual(j.task['pay']['screen']['status'], 'success')
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['flags']['unverified'], 1)
        self.assertEqual(t['mistakes'], 1)

    def test_transfer_typo_loss_and_fix(self):
        j = journey('Quán cơm nhập gấp')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        screen = j.task['pay']['screen']['amount']
        self.assertLess(screen, j.task['total'])
        before = ledger_mark(j)
        j.act('gr_verify')
        self.assertEqual(j.task['pay']['bank'], screen)
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['result']['loss'], t['total'] - screen)
        self.assertEqual(paid(j, before, tid), screen)
        j = journey('Quán cơm nhập gấp')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        with self.assertRaises(GameError):
            j.act('gr_transfer_fix')
        j.act('gr_verify')
        j.act('gr_transfer_fix')
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(t['result']['loss'], 0)

    def test_pending_transfer_arrives_later(self):
        j = journey('Đồ cho buổi họp nhóm')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        j.act('gr_verify')
        self.assertEqual(j.task['pay']['bank'], 0)
        j.act('gr_verify')
        self.assertEqual(j.task['pay']['bank'], j.task['total'])
        j.act('gr_pay', confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], 0)

    def test_short_change_refused_and_excess_change(self):
        j = journey('Chú Bảy mua mồi chiều')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        t = j.task
        due = sum(t['pay']['tender']) - t['total']
        give_change(j, due - 1)
        r = j.act('gr_pay', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertNotEqual(j.get(tid)['status'], 'completed')
        before = ledger_mark(j)
        j.act('gr_change', denom=5)   # 4 xu too much: honest Chú Bảy gives it back
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['result']['loss'], 0)
        self.assertEqual(t['flags']['excess'], 4)
        self.assertEqual(paid(j, before, tid), t['total'])
        j = journey('Sữa cho hai đứa nhỏ')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        t = j.task
        give_change(j, sum(t['pay']['tender']) - t['total'] + 10)
        before = ledger_mark(j)
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['result']['loss'], 10)
        self.assertEqual(paid(j, before, tid), t['total'] - 10)

    def test_fake_note_checked_or_lost(self):
        j = journey('Chú Bảy trả bằng tờ 200')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        t = j.task
        self.assertEqual(max(t['pay']['tender']), 200)
        with self.assertRaises(GameError):
            j.act('gr_reject_note')
        self.assertIn('giả', j.act('gr_check_note')['message'])
        j.act('gr_reject_note')
        give_change(j, 200 - t['total'])
        j.act('gr_pay', confirm=True)
        self.assertEqual(j.get(tid)['result']['loss'], 0)
        self.assertEqual(j.get(tid)['mistakes'], 0)
        j = journey('Chú Bảy trả bằng tờ 200')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        total = j.task['total']
        give_change(j, 200 - total)
        before = ledger_mark(j)
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['result']['loss'], 200)
        self.assertEqual(paid(j, before, tid), total - 200)
        roundtrip(j)

    def test_weighing_tare_and_plu(self):
        j = journey('Bà Sáu đi chợ sáng')
        tid = j.task['id']
        j.act('ask')
        lines = j.task['needs']['lines']
        j.act('gr_weigh', line=0, plu='greens', tare=False)
        self.assertEqual(j.task['weighed']['0']['grams'], lines[0]['_grams'] + 150)
        j.act('gr_weigh', line=1, plu='greens', tare=True)
        j.act('gr_scan', item='egg', qty=10)
        r = j.act('gr_total')
        self.assertTrue(r.get('refused'))
        self.assertIn('rổ', r['message'])
        j.act('gr_void', line=0)
        j.act('gr_void', line=1)
        j.act('gr_weigh', line=0, plu='greens', tare=True)
        j.act('gr_weigh', line=1, plu='tomato', tare=True)
        j.act('gr_total')
        t = j.task
        expect = G._weighed_amount(30, lines[0]['_grams']) + G._weighed_amount(25, lines[1]['_grams']) + 30
        self.assertEqual(t['total'], expect)
        greens = kit.stock(j.c, 'greens')
        give_change(j, sum(t['pay']['tender']) - t['total'])
        j.act('gr_pay', confirm=True)
        self.assertEqual(kit.stock(j.c, 'greens'), greens - G._units('greens', lines[0]['_grams']))
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_out_of_stock_basket(self):
        j = journey('Bà Sáu đi chợ sáng')
        tid = j.task['id']
        for lot in j.c['ext']['inv']['lots']:
            if lot['item'] == 'egg':
                lot['qty'] = 0
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('gr_scan', item='egg', qty=10)
        scan_all(j, skip=('egg',))
        j.act('gr_total')
        t = j.task
        self.assertEqual(t['flags']['out'], 10)
        give_change(j, sum(t['pay']['tender']) - t['total'])
        j.act('gr_pay', confirm=True)
        post = next(p for p in j.c['feed'] if p.get('source') == tid)
        self.assertIn('stock', json.dumps(post['feedback']))


class GroceryCreditTests(unittest.TestCase):
    def test_credit_within_limit(self):
        j = journey('Bà Sáu ghi sổ bó rau')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        before = ledger_mark(j)
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(t['flags']['credit_ok'], 1)
        self.assertEqual(j.c['ext']['data']['ledger']['4']['balance'], t['total'])
        self.assertLessEqual(paid(j, before, tid), 5)   # at most a tip, never the bill
        roundtrip(j)

    def test_credit_over_limit_is_risky_or_declined(self):
        j = journey('Chú Bảy ghi sổ thêm')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['flags']['credit_risky'], 1)
        self.assertEqual(t['mistakes'], 1)
        self.assertEqual(j.c['ext']['data']['ledger']['1']['balance'], 90 + t['total'])
        j = journey('Chú Bảy ghi sổ thêm')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        j.act('gr_decline_credit')
        t = j.task
        self.assertEqual(t['flags']['credit_ok'], 1)
        give_change(j, sum(t['pay']['tender']) - t['total'])
        before = ledger_mark(j)
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(t['result']['method'], 'cash')
        self.assertGreaterEqual(paid(j, before, tid), t['total'])
        self.assertEqual(j.c['ext']['data']['ledger']['1']['balance'], 90)

    def test_declining_good_credit_is_harsh(self):
        j = journey('Bà Sáu ghi sổ bó rau')
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        j.act('gr_decline_credit')
        self.assertEqual(j.task['flags']['credit_harsh'], 1)

    def test_reminder_brings_repayment_next_morning(self):
        j = Journey('grocery')
        with self.assertRaises(GameError):
            j.act('gr_remind', npc='grocery_npc_05')   # Bà Sáu owes nothing
        with self.assertRaises(GameError):
            j.act('gr_remind', npc='grocery_npc_09')
        j.act('gr_remind', npc='grocery_npc_02')
        with self.assertRaises(GameError):
            j.act('gr_remind', npc='grocery_npc_02')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        row = j.c['ext']['data']['ledger']['1']
        self.assertEqual(row['paid'], 45)
        self.assertEqual(row['balance'], 45)
        roundtrip(j)

    def test_payday_repayment(self):
        j = Journey('grocery')
        c = j.c
        c['day'] = 6
        G.on_start(j.state, c)
        self.assertEqual(c['ext']['data']['ledger']['2']['balance'], 0)
        self.assertEqual(c['ext']['data']['ledger']['2']['paid'], 60)


class GroceryShelfTests(unittest.TestCase):
    def _shelf(self):
        j = journey(kind='shelf')
        j.act('ask')
        return j

    def test_perfect_shelf_rotation(self):
        j = self._shelf()
        tid = j.task['id']
        t = j.task
        for lot in t['shelf']['order'] + t['shelf']['cart']:
            j.act('gr_check', lot=lot)
        view = public_state(j.state)['careers']['grocery']['tasks']
        v = next(x for x in view if x['id'] == tid)
        self.assertTrue(all(l['exp'] is not None for l in v['lots']))
        left = lambda lot: G._left(j.c, j.task, lot)
        for lot in list(j.task['shelf']['order']):
            if left(lot) <= 0:
                j.act('gr_pull', lot=lot)
        for lot in j.task['shelf']['order'] + j.task['shelf']['cart']:
            if 1 <= left(lot) <= 2:
                j.act('gr_mark', lot=lot)
        order = sorted(j.task['shelf']['order'] + j.task['shelf']['cart'], key=lambda x: j.task['needs']['_exps'][x])
        j.act('gr_place', order=order)
        if j.task['shelf']['tag'] != G.PRICES[j.task['needs']['item']]:
            j.act('gr_retag')
        else:
            with self.assertRaises(GameError):
                j.act('gr_retag')
        before = ledger_mark(j)
        j.act('gr_shelf_done', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        self.assertGreaterEqual(paid(j, before, tid), G.SHELF_PAY)
        roundtrip(j)

    def test_sloppy_shelf_is_scored(self):
        j = self._shelf()
        tid = j.task['id']
        lot = j.task['shelf']['order'][0]
        with self.assertRaises(GameError):
            j.act('gr_pull', lot=lot)   # must read the date first
        with self.assertRaises(GameError):
            j.act('gr_shelf_done', confirm=True)   # new stock still in the cart
        with self.assertRaises(GameError):
            j.act('gr_place', order=['N'])
        j.act('gr_place', order=j.task['shelf']['order'] + j.task['shelf']['cart'])
        j.act('gr_shelf_done', confirm=True)
        t = j.get(tid)
        self.assertGreaterEqual(t['mistakes'], 1)
        self.assertTrue(t['result']['fifo'])

    def test_pulling_good_stock_is_waste(self):
        j = self._shelf()
        t = j.task
        lot = max(t['shelf']['order'], key=lambda x: t['needs']['_exps'][x])
        j.act('gr_check', lot=lot)
        j.act('gr_pull', lot=lot)
        self.assertEqual(j.task['mistakes'], 1)
        self.assertTrue(any('nhầm' in w['reason'] for w in j.c['life']['waste']))


class GroceryValidationTests(unittest.TestCase):
    def test_invalid_payloads(self):
        j = journey('Bà Sáu đi chợ sáng')
        with self.assertRaises(GameError):
            j.act('gr_scan', item='egg')   # not asked yet
        j.act('ask')
        bad = [('gr_scan', dict(item='caviar')), ('gr_scan', dict(item='egg', qty=0)), ('gr_scan', dict(item='egg', qty='3')),
               ('gr_scan', dict(item='greens')), ('gr_weigh', dict(line=0, plu='pork', tare=True)),
               ('gr_weigh', dict(line=0, plu='greens', tare='yes')), ('gr_weigh', dict(line=2, plu='greens', tare=True)),
               ('gr_weigh', dict(line=9, plu='greens', tare=True)), ('gr_void', dict(item='egg')), ('gr_promo', dict(promo='free_all')),
               ('gr_id', {}), ('gr_total', {}), ('gr_change', dict(denom=10)), ('gr_pay', dict(confirm=True)),
               ('gr_place', dict(order=['A'])), ('gr_remind', dict(npc=5))]
        for action, payload in bad:
            with self.assertRaises(GameError, msg=action):
                j.act(action, **payload)
        scan_all(j)
        j.act('gr_total')
        for action, payload in [('gr_scan', dict(item='egg')), ('gr_change', dict(denom=3)), ('gr_change', dict(denom='10')),
                                ('gr_change', dict(denom=True)), ('gr_pay', {}), ('gr_verify', {}), ('gr_decline_credit', {})]:
            with self.assertRaises(GameError, msg=action):
                j.act(action, **payload)
        # A client-sent total is ignored: money comes from the cart on the server.
        t = j.task
        give_change(j, sum(t['pay']['tender']) - t['total'])
        before = j.c['money']
        j.act('gr_pay', confirm=True, total=99999, amount=99999)
        self.assertLess(j.c['money'] - before, 1000)

    def test_tampered_fixed_fields_rejected(self):
        j = journey('Tí đi mua giùm ba')
        j.act('ask')
        s = copy.deepcopy(j.state)
        s['careers']['grocery']['tasks'][0]['needs']['_age'] = 30
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['grocery']['tasks'][0]['age'] = 30
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['grocery']['tasks'][0]['scanned'] = {'rice': 2}
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['grocery']['ext']['data']['ledger']['1']['limit'] = 9999
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['grocery']['tasks'][0]['pay']['change'] = [7]
        with self.assertRaises(GameError):
            validate_state(s)

    def test_all_situations_playable(self):
        j = Journey('grocery')
        for x in G.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_full_day_cycle(self):
        j = Journey('grocery')
        summary = j.act('end_day', carry_event=True)['summary']
        self.assertIn('ledger_total', summary['career'])
        j.act('start_day')
        roundtrip(j)
        self.assertTrue(public_state(j.state)['careers']['grocery']['data']['prices'])


# ---------------------------------------------------------------- v0.5 helpers
def set_money(j, amount):
    from game import engine
    engine.money(j.state, j.c, amount - j.c['money'], 'Kiểm két thử', None, 'other_income' if amount >= j.c['money'] else 'other_cost')


def force_event(j, script):
    desk = j.c['ext']['data']['desk']
    desk['seq'] += 1
    desk['ev'] = dict(id=f'desk-{desk["seq"]}', script=script, day=j.c['day'], at='between')


def top_up(j, item, qty):
    have = kit.stock(j.c, item)
    if have < qty:
        inventory.add_lot(j.c, item, qty - have, G.ITEM_INDEX[item]['cost'], 999, 'partner')


def set_stock(j, item, qty):
    have = kit.stock(j.c, item)
    if have > qty:
        kit.take(j.c, item, have - qty)
    top_up(j, item, qty)


def serve_rush(j, wrong_first=False):
    tid = j.task['id']
    while j.get(tid)['status'] != 'completed':
        t = j.get(tid)
        r = t['rush']
        q = t['needs']['queue'][r['i']]
        if any(i in G.AGE_LIMITED for i, _ in q['items']) and str(r['i']) not in r['ages']:
            j.act('gr_rush_id', task=tid)
            continue
        o = j.get(tid)['rush']['offer']
        correct = sum(G._price(j.c, k) * v for k, v in o['units'].items())
        pick = correct
        if wrong_first and r['i'] == 0:
            pick = next(x for x in o['totals'] if x > correct)
        j.act('gr_rush_total', task=tid, total=pick)
        t = j.get(tid)
        if t['status'] == 'completed':
            break
        o = t['rush']['offer']
        if o and o['charged'] is not None and o['changes']:
            j.act('gr_rush_change', task=tid, change=sum(o['tender']) - o['charged'])
    return j.get(tid)


def second_task(j, pred):
    """Add another task of the same day that matches pred (as if it had walked in)."""
    day = j.c['day']
    used = {int(t['id'].rsplit('-', 1)[1]) for t in j.c['tasks']}
    for s in range(12):
        if s in used:
            continue
        t = G.make_task(day, s, 1)
        if pred(t):
            j.c['tasks'].append(t)
            G.on_task(j.state, j.c, t)
            return t
    return None


class GroceryDayLuckTests(unittest.TestCase):
    def test_one_day_never_repeats_a_customer_or_a_shelf(self):
        for day in range(1, 31):
            seen = {}
            for slot in range(9):   # a busy day: the three dealt tasks plus six more
                t = G.make_task(day, slot, day * 100 + slot)
                if t['kind'] in ('checkout', 'shelf', 'rush'):
                    key = (t['kind'], t['title'])
                    self.assertNotIn(key, seen, f'day {day}: “{t["title"]}” twice (slots {seen.get(key)} and {slot})')
                    seen[key] = slot

    def test_mood_and_flyer_are_fixed_by_the_day(self):
        for day in range(1, 30):
            self.assertEqual(G.mod_of(day), G.mod_of(day))
            self.assertEqual(G.rival(day), G.rival(day))
            for item, price in G.rival(day).items():
                self.assertIn(item, G.RIVAL_ITEMS)
                self.assertGreaterEqual(price, G._floor_price(item))
                self.assertLess(price, G.PRICES[item])
        self.assertEqual(G.mod_of(1)['id'], 'normal')
        self.assertEqual(G.rival(1), {})
        self.assertEqual(G.rival(G.RIVAL_DAY - 1), {})
        for day in range(2, 60):   # the same special day never repeats back to back
            a, b = G.mod_of(day - 1)['id'], G.mod_of(day)['id']
            self.assertFalse(a == b != 'normal', day)
        kinds = {G.make_task(d, s, 1)['kind'] for d in range(1, 30) for s in range(6)}
        self.assertEqual(kinds, {'checkout', 'shelf', 'rush', 'bulk'})
        self.assertEqual(G.make_task(7, 2, 1), G.make_task(7, 2, 1))

    def test_start_day_posts_mood_and_flyer(self):
        j = Journey('grocery')
        j.act('end_day', carry_event=True)
        j.c['day'] = 4
        j.act('start_day')
        view = public_state(j.state)['careers']['grocery']['data']
        self.assertEqual(view['today_view']['mod']['id'], G.mod_of(4)['id'])
        self.assertEqual({r['item'] for r in view['today_view']['rival']}, set(G.rival(4)))
        self.assertEqual(j.c['ext']['data']['today']['day'], 4)
        roundtrip(j)

    def test_generator_two_is_gender_neutral(self):
        texts = []
        for d in range(1, 40):
            for s in range(8):
                t = G.make_task(d, s, 1)
                texts += [t['opening'], t['title'], json.dumps(t['needs'], ensure_ascii=False)]
        blob = ' '.join(texts)
        for bad in ('Chị ơi em mua', 'chị chủ', 'cô chủ', 'anh chủ'):
            self.assertNotIn(bad, blob)
        s01 = next(x for x in G.SITUATIONS if x['id'] == 'GR-S01')
        self.assertNotIn('Chị bán hàng', json.dumps(s01, ensure_ascii=False))


class GroceryPriceWarTests(unittest.TestCase):
    def test_price_tags_during_the_shift(self):
        j = journey()
        j.act('gr_tag', item='beer', price=13)
        self.assertEqual(j.c['life']['prices']['beer'], 13)
        self.assertEqual(j.c['life']['price_history'][-1], dict(day=j.c['day'], item='beer', price=13))
        before = copy.deepcopy(j.state)
        for bad in (dict(item='beer', price=5), dict(item='beer', price=30), dict(item='beer', price=13),
                    dict(item='caviar', price=10), dict(item='beer', price='12')):
            with self.assertRaises(GameError, msg=str(bad)):
                j.act('gr_tag', **bad)
        self.assertEqual(j.state, before)

    def _haggler(self, loyal):
        day, slot = find(lambda t: t['kind'] == 'checkout' and t['needs'].get('_haggle') and t['needs'].get('_loyal') == loyal
                         and t['needs']['pay'] == 'cash')
        j = Journey('grocery', slot=slot, day=day)
        restock(j)
        j.act('ask')
        return j, j.task['needs']['_haggle']

    def test_haggle_match_uses_the_flyer_price(self):
        j, item = self._haggler(loyal=False)
        tid = j.task['id']
        theirs = G.rival(j.c['day'])[item]
        r = j.act('gr_scan', item=item, qty=1)
        self.assertIn('Mây Mart', r['message'])
        self.assertEqual(j.task['haggle']['state'], 'ask')
        j.act('gr_void', item=item)
        scan_all(j)
        with self.assertRaises(GameError):
            j.act('gr_total')
        j.act('gr_haggle', answer='match')
        self.assertEqual(G._unit(j.c, j.task, item), theirs)
        # promos may now qualify at the matched price
        for p in G.PROMOS:
            if p['id'] not in j.task['promos'] and G._discount(p, j.task['scanned'].get(p['item'], 0), G._unit(j.c, j.task, p['item'])) > 0:
                j.act('gr_promo', promo=p['id'])
        j.act('gr_total')
        t = j.get(tid)
        units = t['scanned'][item]
        full = sum(G._price(j.c, k) * q for k, q in t['scanned'].items()) + sum(G._weighed_amount(G._price(j.c, w['plu']), w['grams']) for w in t['weighed'].values())
        promos = sum(G._discount(G.PROMO_INDEX[p], t['scanned'].get(G.PROMO_INDEX[p]['item'], 0), G._unit(j.c, t, G.PROMO_INDEX[p]['item'])) for p in t['promos'])
        self.assertEqual(t['total'], full - promos - (G._price(j.c, item) - theirs) * units)
        view = json.dumps(public_state(j.state)['careers']['grocery'], ensure_ascii=False)
        for secret in ('_haggle', '_loyal', '_max'):
            self.assertNotIn(secret, view)
        roundtrip(j)

    def test_holding_the_price_loses_a_picky_customer(self):
        j, item = self._haggler(loyal=False)
        stock = kit.stock(j.c, item)
        j.act('gr_scan', item=item, qty=1)
        j.act('gr_haggle', answer='hold')
        self.assertEqual(j.task['haggle']['state'], 'dropped')
        self.assertNotIn(item, j.task['scanned'])
        with self.assertRaises(GameError):
            j.act('gr_scan', item=item, qty=1)
        scan_all(j, skip=(item,))
        j.act('gr_total')
        t = j.task
        give_change(j, sum(t['pay']['tender']) - t['total'])
        tid = t['id']
        j.act('gr_pay', confirm=True)
        self.assertEqual(kit.stock(j.c, item), stock)   # the dropped item stays on the shelf
        post = next(p for p in j.c['feed'] if p.get('source') == tid)
        self.assertIn('price', json.dumps(post['feedback'], ensure_ascii=False))

    def test_loyal_customer_buys_anyway_and_fair_price_needs_no_haggle(self):
        j, item = self._haggler(loyal=True)
        j.act('gr_scan', item=item, qty=1)
        j.act('gr_haggle', answer='hold')
        self.assertEqual(j.task['haggle']['state'], 'hold')
        self.assertEqual(G._unit(j.c, j.task, item), G._price(j.c, item))
        j2, item2 = self._haggler(loyal=True)
        j2.act('gr_tag', item=item2, price=G.rival(j2.c['day'])[item2])
        j2.act('gr_scan', item=item2, qty=1)
        self.assertEqual(j2.task['haggle']['state'], 'fair')
        with self.assertRaises(GameError):
            j2.act('gr_haggle', answer='match')


class GroceryStockTests(unittest.TestCase):
    def test_opening_stock_survives_the_first_evening(self):
        j = Journey('grocery')
        lots = [l for l in j.c['ext']['inv']['lots'] if l['qty'] > 0]
        self.assertTrue(lots)
        self.assertTrue(all(l['expires'] >= 2 for l in lots), [(l['item'], l['expires']) for l in lots if l['expires'] < 2])
        j.act('end_day', carry_event=True)
        self.assertFalse(any('hết hạn' in w['reason'].lower() and w['day'] == 1 for w in j.c['life']['waste']))

    def test_second_bill_cannot_sell_reserved_units(self):
        j = journey('Bà Sáu đi chợ sáng')
        t1 = j.task
        t2 = second_task(j, lambda t: t['kind'] == 'checkout' and any(not l.get('weighed') and l['item'] == 'egg' for l in t['needs']['lines']))
        if t2 is None:
            self.skipTest('no second egg basket on this day')
        set_stock(j, 'egg', 10)
        j.act('ask', task=t1['id'])
        j.act('gr_scan', task=t1['id'], item='egg', qty=10)
        self.assertEqual(G._available(j.c, 'egg', None), 0)
        j.act('ask', task=t2['id'])
        with self.assertRaises(GameError):
            j.act('gr_scan', task=t2['id'], item='egg', qty=1)
        roundtrip(j)

    def test_bill_reopens_when_goods_vanish_before_payment(self):
        j = journey('Bà Sáu đi chợ sáng')
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        t = j.task
        for lot in [l for l in j.c['ext']['inv']['lots'] if l['item'] == 'egg']:
            j.act('inv_discard', lot=lot['id'], confirm=True)
        give_change(j, sum(t['pay']['tender']) - t['total'])
        money = j.c['money']
        r = j.act('gr_pay', confirm=True)
        self.assertTrue(r.get('refused'))
        t = j.task
        self.assertEqual(t['stage'], 'basket')
        self.assertNotIn('egg', t['scanned'])
        self.assertEqual(j.c['money'], money)
        roundtrip(j)

    def test_pull_expired_then_clear_near_date(self):
        j = journey('Bà Sáu đi chợ sáng')
        day = j.c['day']
        inventory.add_lot(j.c, 'milk', 3, 6, 1, 'partner')     # expires today
        inventory.add_lot(j.c, 'milk', 6, 6, 2, 'partner')     # expires tomorrow
        with self.assertRaises(GameError):
            j.act('gr_clear', item='milk')                      # expired stock first
        with self.assertRaises(GameError):
            j.act('gr_pull_today', item='milk')                 # needs confirm
        j.act('gr_pull_today', item='milk', confirm=True)
        self.assertFalse([l for l in j.c['ext']['inv']['lots'] if l['item'] == 'milk' and l['expires'] <= day])
        money, stock = j.c['money'], kit.stock(j.c, 'milk')
        near = G._near_units(j.c, 'milk')
        r = j.act('gr_clear', item='milk')
        sold = min(near, 12)
        each = -(-G._price(j.c, 'milk') * G.CLEAR_PERCENT // 100)
        self.assertEqual(j.c['money'] - money, sold * each)
        self.assertEqual(kit.stock(j.c, 'milk'), stock - sold)
        self.assertTrue(r['celebrate'])
        with self.assertRaises(GameError):
            j.act('gr_clear', item='milk')                      # once per item per day
        with self.assertRaises(GameError):
            j.act('gr_clear', item='soap')                      # nothing near date
        roundtrip(j)


class GroceryRushTests(unittest.TestCase):
    def _rush(self, pred=lambda t: True):
        day, slot = find(lambda t: t['kind'] == 'rush' and pred(t))
        j = Journey('grocery', slot=slot, day=day)
        restock(j)
        return j

    def test_clean_rush_pays_every_customer(self):
        j = self._rush()
        tid = j.task['id']
        with self.assertRaises(GameError):
            j.act('gr_rush_total', total=1)                     # queue not opened yet
        j.act('ask')
        self.assertIsNotNone(j.task['rush']['start'])
        money = j.c['money']
        t = serve_rush(j)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(t['rush']['left'], 0)
        self.assertGreater(t['rush']['cash'], 0)
        self.assertGreaterEqual(j.c['money'] - money, t['rush']['cash'])
        post = next(p for p in j.c['feed'] if p.get('source') == tid)
        self.assertGreaterEqual(post['stars'], 4)
        roundtrip(j)

    def test_wrong_total_is_caught_and_counted(self):
        j = self._rush()
        j.act('ask')
        t = serve_rush(j, wrong_first=True)
        self.assertEqual(t['rush']['flags']['over'], 1)
        self.assertEqual(t['mistakes'], 1)
        with self.assertRaises(GameError):
            j.act('gr_rush_total', task=t['id'], total=10)      # finished task

    def test_minor_beer_needs_id_and_is_left_on_the_shelf(self):
        j = self._rush(lambda t: any(q['npc'] == 3 and any(i == 'beer' for i, _ in q['items']) for q in t['needs']['queue']))
        j.act('ask')
        tid = j.task['id']
        beer = kit.stock(j.c, 'beer')
        sold_beer = 0
        while j.get(tid)['status'] != 'completed':
            t = j.get(tid)
            r = t['rush']
            q = t['needs']['queue'][r['i']]
            has_beer = any(i == 'beer' for i, _ in q['items'])
            if has_beer and str(r['i']) not in r['ages']:
                j.act('gr_rush_id', task=tid)
                if q['npc'] != 3:
                    sold_beer += dict(q['items'])['beer']
                continue
            o = r['offer']
            if q['npc'] == 3 and has_beer:
                self.assertNotIn('beer', o['units'])
            correct = sum(G._price(j.c, k) * v for k, v in o['units'].items())
            j.act('gr_rush_total', task=tid, total=correct)
            t = j.get(tid)
            if t['status'] != 'completed' and t['rush']['offer'] and t['rush']['offer']['changes']:
                o = t['rush']['offer']
                j.act('gr_rush_change', task=tid, change=sum(o['tender']) - o['charged'])
        t = j.get(tid)
        self.assertEqual(t['rush']['flags']['minor'], 1)
        self.assertEqual(kit.stock(j.c, 'beer'), beer - sold_beer)

    def test_customers_walk_out_when_left_waiting(self):
        j = self._rush()
        j.act('ask')
        n = len(j.task['needs']['queue'])
        j.c['turn'] += 50                                      # the queue waited while you did other things
        o = j.task['rush']['offer']
        r = j.act('gr_rush_total', total=o['totals'][0])
        t = next(x for x in j.c['tasks'] if x['kind'] == 'rush')
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['rush']['left'], n)
        self.assertIn('bỏ về', r['message'])

    def test_closing_sends_the_queue_home(self):
        j = self._rush()
        j.act('ask')
        summary = j.act('end_day', carry_event=True)['summary']
        t = next(x for x in j.c['tasks'] if x['kind'] == 'rush')
        self.assertEqual(t['status'], 'completed')
        self.assertIn('hàng chờ', summary['career']['note'])


class GroceryBulkTests(unittest.TestCase):
    def _bulk(self):
        day, slot = find(lambda t: t['kind'] == 'bulk')
        j = Journey('grocery', slot=slot, day=day)
        restock(j)
        j.act('ask')
        return j

    def test_quote_deposit_restock_deliver(self):
        j = self._bulk()
        tid = j.task['id']
        money = j.c['money']
        with self.assertRaises(GameError):
            j.act('gr_bulk_quote', off=7)
        j.act('gr_bulk_quote', off=15)                          # 85% is always acceptable
        t = j.task
        self.assertEqual(t['bulk']['stage'], 'deliver')
        self.assertEqual(j.c['money'] - money, t['bulk']['deposit'])
        self.assertEqual(t['bulk']['deposit'], -(-t['bulk']['price'] * 30 // 100))
        for x in t['needs']['lines']:
            set_stock(j, x['item'], max(0, x['qty'] - 1))
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('gr_bulk_deliver', confirm=True)              # not enough stock: nothing changes
        self.assertEqual(j.state, before)
        for x in t['needs']['lines']:
            top_up(j, x['item'], x['qty'])
        stock = {x['item']: kit.stock(j.c, x['item']) for x in t['needs']['lines']}
        money = j.c['money']
        j.act('gr_bulk_deliver', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertGreaterEqual(j.c['money'] - money, t['bulk']['price'] - t['bulk']['deposit'])
        for x in t['needs']['lines']:
            self.assertEqual(kit.stock(j.c, x['item']), stock[x['item']] - x['qty'])
        roundtrip(j)

    def test_partial_delivery_refunds_the_gap(self):
        j = self._bulk()
        j.act('gr_bulk_quote', off=15)
        t = j.task
        first = t['needs']['lines'][0]
        for x in t['needs']['lines']:
            top_up(j, x['item'], x['qty'])
        set_stock(j, first['item'], first['qty'] // 2)
        j.act('gr_bulk_deliver', confirm=True, partial=True)
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 1)
        self.assertLess(t['result']['price'], t['bulk']['price'])
        self.assertEqual(t['bulk']['delivered'][first['item']], first['qty'] // 2)

    def test_high_prices_lose_the_order(self):
        j = self._bulk()
        for x in j.task['needs']['lines']:
            if G._price(j.c, x['item']) != G._cap_price(x['item']):
                j.act('gr_tag', item=x['item'], price=G._cap_price(x['item']))
        r = j.act('gr_bulk_quote', off=0)
        self.assertTrue(r['refused'])
        with self.assertRaises(GameError):
            j.act('gr_bulk_quote', off=0)                       # must come down
        j.act('gr_bulk_quote', off=5)
        t = next(x for x in j.c['tasks'] if x['kind'] == 'bulk')
        self.assertEqual(t['bulk']['stage'], 'lost')
        self.assertEqual(t['status'], 'completed')

    def test_undelivered_order_is_refunded_at_closing(self):
        j = self._bulk()
        j.act('gr_bulk_quote', off=15)
        summary = j.act('end_day', carry_event=True)['summary']
        t = next(x for x in j.c['tasks'] if x['kind'] == 'bulk')
        self.assertEqual(t['status'], 'cancelled')
        self.assertEqual(t['bulk']['stage'], 'cancelled')
        self.assertEqual(t['result']['refund'], t['bulk']['deposit'])
        self.assertIn('hoàn cọc', summary['career']['note'])
        roundtrip(j)


class GrocerySurpriseTests(unittest.TestCase):
    def _j(self):
        j = journey('Bà Sáu đi chợ sáng')
        set_money(j, 500)
        j.c['ext']['inv']['lots'] = [l for l in j.c['ext']['inv']['lots'] if l['expires'] > j.c['day']]
        return j

    def test_every_option_of_every_surprise_is_playable(self):
        for x in G.EVENTS:
            for opt in x['options']:
                j = self._j()
                if x['id'] == 'GE-FINE':
                    j.c['ext']['data']['fine'] = dict(amount=40, lines=['thử'], lots=[])
                force_event(j, x['id'])
                view = public_state(j.state)['careers']['grocery']['data']['desk']['ev']
                self.assertEqual(view['script'], x['id'])
                self.assertNotIn('luck', json.dumps(view))
                r = j.act('gr_decide', option=opt['id'])
                self.assertTrue(r['message'], (x['id'], opt['id']))
                d = j.c['ext']['data']
                self.assertTrue(d['desk']['ev'] is None or d['desk']['ev']['script'] == 'GE-FINE', (x['id'], opt['id']))
                roundtrip(j)

    def test_open_surprise_blocks_the_counter_until_decided(self):
        j = self._j()
        j.act('ask')
        force_event(j, 'GE-RETURN')
        with self.assertRaises(GameError) as e:
            j.act('gr_scan', item='egg', qty=1)
        self.assertEqual(e.exception.code, 'surprise_open')
        with self.assertRaises(GameError):
            j.act('gr_decide', option='nope')
        j.act('gr_decide', option='swap')
        j.act('gr_scan', item='egg', qty=1)

    def test_clean_inspection_earns_praise(self):
        j = self._j()
        force_event(j, 'GE-INSPECT')
        money = j.c['money']
        j.act('gr_decide', option='open')
        d = j.c['ext']['data']
        self.assertIsNone(d['desk']['ev'])
        self.assertIsNone(d['fine'])
        self.assertIs(d['desk']['last']['good'], True)
        self.assertEqual(j.c['money'], money)

    def test_counterfeit_goods_lead_to_a_fine_decision(self):
        j = self._j()
        force_event(j, 'GE-FAKE')
        money = j.c['money']
        j.act('gr_decide', option='buy')
        self.assertEqual(money - j.c['money'], 130)
        self.assertEqual(sum(l['qty'] for l in j.c['ext']['inv']['lots'] if l['supplier'] == 'noinvoice'), 10)
        inventory.add_lot(j.c, 'bread', 2, 3, 1, 'partner')     # and bread that expires today
        force_event(j, 'GE-INSPECT')
        j.act('gr_decide', option='open')
        d = j.c['ext']['data']
        self.assertEqual(d['desk']['ev']['script'], 'GE-FINE')
        self.assertEqual(d['fine']['amount'], 60)
        view = public_state(j.state)['careers']['grocery']['data']['desk']['ev']
        self.assertIn('60', view['options'][0]['label'])
        self.assertEqual(view['options'][0]['cost'], 60)
        with self.assertRaises(GameError):
            j.act('gr_scan', item='egg', qty=1)
        money = j.c['money']
        j.act('gr_decide', option='pay')
        self.assertEqual(money - j.c['money'], 60)
        self.assertFalse([l for l in j.c['ext']['inv']['lots'] if l['supplier'] == 'noinvoice'])
        self.assertIn('fined', j.c['ext']['data']['desk']['marks'])
        self.assertIsNone(j.c['ext']['data']['fine'])
        roundtrip(j)

    def test_fine_appeal_only_works_the_first_time(self):
        j = self._j()
        inventory.add_lot(j.c, 'bread', 2, 3, 1, 'partner')
        force_event(j, 'GE-INSPECT')
        j.act('gr_decide', option='open')
        money = j.c['money']
        j.act('gr_decide', option='appeal')
        self.assertEqual(j.c['money'], money)
        self.assertIn('warned', j.c['ext']['data']['desk']['marks'])
        inventory.add_lot(j.c, 'bread', 2, 3, 1, 'partner')
        force_event(j, 'GE-INSPECT')
        j.act('gr_decide', option='open')
        money = j.c['money']
        j.act('gr_decide', option='appeal')
        self.assertEqual(money - j.c['money'], 30)

    def test_half_fine_brings_a_reinspection(self):
        j = self._j()
        inventory.add_lot(j.c, 'bread', 2, 3, 1, 'partner')
        force_event(j, 'GE-INSPECT')
        j.act('gr_decide', option='open')
        money = j.c['money']
        j.act('gr_decide', option='half')
        self.assertEqual(money - j.c['money'], 10)
        marks = j.c['ext']['data']['desk']['marks']
        self.assertIn('reinspect', marks)
        later = dict(copy.deepcopy(j.c), day=max(j.c['day'], 3))
        pool = [x['id'] for x in kit._desk_pool(G.ID, later, later['ext']['data']['desk'], G.EVENTS, 'between', 'normal')]
        self.assertIn('GE-REINSPECT', pool)
        force_event(j, 'GE-REINSPECT')
        j.act('gr_decide', option='open')
        self.assertNotIn('reinspect', j.c['ext']['data']['desk']['marks'])

    def test_cannot_afford_a_fine_pick_another_way(self):
        j = self._j()
        inventory.add_lot(j.c, 'bread', 2, 3, 1, 'partner')
        force_event(j, 'GE-INSPECT')
        j.act('gr_decide', option='open')
        set_money(j, 5)
        with self.assertRaises(GameError):
            j.act('gr_decide', option='pay')
        j.act('gr_decide', option='appeal')                     # first time: only a warning
        self.assertIsNone(j.c['ext']['data']['desk']['ev'])

    def test_wholesale_deal_respects_room_and_cash(self):
        j = self._j()
        set_stock(j, 'beer', 60)
        force_event(j, 'GE-DEAL-BEER')
        with self.assertRaises(GameError):
            j.act('gr_decide', option='all')                    # no room
        set_stock(j, 'beer', 50)
        money = j.c['money']
        j.act('gr_decide', option='all')
        self.assertEqual(kit.stock(j.c, 'beer'), 60)
        self.assertEqual(money - j.c['money'], 80)
        j2 = self._j()
        set_money(j2, 10)
        force_event(j2, 'GE-DEAL-MILK')
        with self.assertRaises(GameError):
            j2.act('gr_decide', option='all')
        j2.act('gr_decide', option='no')

    def test_fridge_and_rats_hit_real_stock(self):
        j = self._j()
        milk, egg = kit.stock(j.c, 'milk'), kit.stock(j.c, 'egg')
        force_event(j, 'GE-FRIDGE')
        j.act('gr_decide', option='wait')
        self.assertEqual(kit.stock(j.c, 'milk'), milk - milk * 50 // 100)
        self.assertEqual(kit.stock(j.c, 'egg'), egg - egg * 30 // 100)
        force_event(j, 'GE-RATS')
        rice = kit.stock(j.c, 'rice')
        j.act('gr_decide', option='ignore')
        self.assertEqual(kit.stock(j.c, 'rice'), rice - 3)
        self.assertIn('rats', j.c['ext']['data']['desk']['marks'])
        force_event(j, 'GE-INSPECT')
        j.act('gr_decide', option='open')
        self.assertIn('chuột', ' '.join(j.c['ext']['data']['fine']['lines']))

    def test_funeral_credit_goes_in_the_ledger(self):
        j = self._j()
        before = j.c['ext']['data']['ledger']['6']['balance']
        force_event(j, 'GE-FUNERAL')
        j.act('gr_decide', option='credit')
        self.assertEqual(j.c['ext']['data']['ledger']['6']['balance'] - before, 12 * G._price(j.c, 'soda') + 10 * G._price(j.c, 'noodle'))
        roundtrip(j)

    def test_rival_match_retags_the_flyer_items(self):
        day = next(d for d in range(3, 60) if G.mod_of(d)['id'] == 'sale')
        j = self._j()
        j.c['day'] = day
        force_event(j, 'GE-RIVAL')
        j.act('gr_decide', option='match')
        for item, theirs in G.rival(day).items():
            self.assertLessEqual(G._price(j.c, item), theirs)

    def test_closing_takes_the_default_and_pays_what_it_can(self):
        j = self._j()
        inventory.add_lot(j.c, 'bread', 2, 3, 1, 'partner')
        j.c['ext']['data']['desk']['marks']['fined'] = 1
        force_event(j, 'GE-FAKE')
        j.act('gr_decide', option='buy')
        force_event(j, 'GE-INSPECT')
        set_money(j, 20)
        j.act('end_day', carry_event=True)
        d = j.c['ext']['data']
        self.assertIsNone(d['desk']['ev'])
        self.assertIsNone(d['fine'])
        self.assertEqual(j.c['money'], 0)
        roundtrip(j)


class GroceryOldSaveTests(unittest.TestCase):
    def test_old_save_loads_and_keeps_generator_one(self):
        j = journey('Bà Sáu đi chợ sáng')
        day = j.c['day']
        slot = int(j.task['id'].rsplit('-', 1)[1])
        old = G._make_v1(day, slot, 1)
        self.assertNotIn('gen', old)
        G.on_task(j.state, j.c, old)
        j.c['tasks'] = [old]
        j.c['active_task'] = old['id']
        data = j.c['ext']['data']
        for k in ('desk', 'today', 'fine', 'cleared', 'stats'):
            data.pop(k)
        validate_state(j.state)                                 # migrates in place
        self.assertEqual(old['created_turn'], 1 + G.LEGACY)
        self.assertIn('desk', data)
        self.assertEqual(G.make_task(day, slot, old['created_turn'])['title'], old['title'])
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        roundtrip(j)


class GroceryConsequenceTests(unittest.TestCase):
    """Doing the till wrong costs you, in proportion (game.consequences)."""

    def _review(self, j, tid):
        return next(p for p in j.c['feed'] if p.get('source') == tid and p.get('kind') == 'review')

    def _pay(self, j, extra=0):
        t = j.task
        give_change(j, sum(t['pay']['tender']) - t['total'] + extra)
        return j.act('gr_pay', confirm=True)

    def test_right_order_full_pay_no_slips(self):
        j = journey('Chú Bảy mua mồi chiều')
        tid = j.task['id']
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        before = ledger_mark(j)
        self._pay(j)
        t = j.get(tid)
        self.assertEqual(t.get('slips') or [], [])
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertEqual(paid(j, before, tid), t['total'])
        self.assertGreaterEqual(self._review(j, tid)['stars'], 4)

    def _short_change(self, j):
        scan_all(j)
        j.act('gr_total')
        t = j.task
        give_change(j, sum(t['pay']['tender']) - t['total'] - 5)
        self.assertTrue(j.act('gr_pay', confirm=True).get('refused'))   # the customer counts it at the counter
        j.act('gr_change', denom=5)
        return j.act('gr_pay', confirm=True)

    def test_short_change_is_remembered_in_the_review(self):
        j = journey('Chú Bảy mua mồi chiều')
        tid = j.task['id']
        j.act('ask')
        self._short_change(j)
        t = j.get(tid)
        self.assertEqual([s['code'] for s in t['slips']], ['short_change'])
        self.assertIn(t['reaction']['kind'], ('accept', 'grumble', 'discount', 'refund'))
        post = self._review(j, tid)
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('Thối thiếu', post['text'])
        roundtrip(j)

    def test_severity_scales_the_stars(self):
        def run(extra):
            j = journey('Chú Bảy mua mồi chiều')
            tid = j.task['id']
            j.act('ask')
            extra(j)
            return j.get(tid), self._review(j, tid)['stars']

        def extra_item(j):   # one bill fix, caught before paying: a small slip
            scan_all(j)
            j.act('gr_scan', item='soap', qty=1)
            self.assertTrue(j.act('gr_total').get('refused'))
            j.act('gr_void', item='soap')
            j.act('gr_total')
            self._pay(j)

        small, s1 = run(extra_item)
        clear, s2 = run(self._short_change)
        self.assertEqual(small['slips'][0]['sev'], 1)
        self.assertEqual(clear['slips'][0]['sev'], 2)
        self.assertGreater(s1, s2)

    def test_beer_to_a_minor_without_id_is_refused_and_reported(self):
        j = journey('Tí đi mua giùm ba')
        tid = j.task['id']
        j.act('ask')
        beer = kit.stock(j.c, 'beer')
        for item, q in (('snack', 1), ('beer', 2), ('soda', 1)):
            j.act('gr_scan', item=item, qty=q)                     # nobody asked for ID
        j.act('gr_total')
        before = ledger_mark(j)
        r = self._pay(j)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertTrue(t['slips'][0]['safety'])
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(paid(j, before, tid), 0)                   # the basket stays on the counter
        self.assertEqual(kit.stock(j.c, 'beer'), beer)
        self.assertEqual(self._review(j, tid)['stars'], 1)
        self.assertTrue(any(p.get('report') and p.get('source') == tid for p in j.c['feed']))
        self.assertTrue(any(f['src'] == tid and f['script'] == 'slip_food_inspect' for f in j.c['incidents']['follow']))
        self.assertIn('kiểm tra', r['message'])
        roundtrip(j)

    def test_milk_dated_today_is_a_safety_mistake(self):
        j = journey('Bữa sáng mang đi')
        tid = j.task['id']
        for lot in j.c['ext']['inv']['lots']:
            if lot['item'] == 'milk':
                lot['expires'] = max(lot['expires'], j.c['day'] + 2)
        inventory.add_lot(j.c, 'milk', 4, 6, 1, 'partner')          # dated today, sold first (FIFO)
        j.act('ask')
        scan_all(j)
        j.act('gr_total')
        j.act('gr_verify')
        j.act('gr_pay', confirm=True)
        t = j.get(tid)
        self.assertEqual([s['code'] for s in t['slips']], ['expired'])
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(self._review(j, tid)['stars'], 1)
        roundtrip(j)

    def test_cut_is_paid_once(self):
        from game import consequences as cq
        j = journey('Bà Sáu đi chợ sáng')                         # a strict customer
        tid = j.task['id']
        j.act('ask')
        lines = j.task['needs']['lines']
        j.act('gr_weigh', line=0, plu='greens', tare=False)         # her own basket on the scale
        j.act('gr_weigh', line=1, plu='tomato', tare=True)
        j.act('gr_scan', item='egg', qty=10)
        self.assertTrue(j.act('gr_total').get('refused'))
        j.act('gr_void', line=0)
        j.act('gr_weigh', line=0, plu='greens', tare=True)
        j.act('gr_total')
        before = ledger_mark(j)
        self._pay(j)
        t = j.get(tid)
        cut = t['reaction']['cut']
        self.assertEqual(paid(j, before, tid), t['total'] - cut)
        money = j.c['money']
        again = cq.react(j.state, j.c, t, t['total'], who='Bà Sáu')
        self.assertEqual(again['cut'], cut)
        self.assertEqual(j.c['money'], money)
        roundtrip(j)

    def test_rush_beer_to_a_minor_without_id(self):
        day, slot = find(lambda t: t['kind'] == 'rush' and any(q['npc'] == 3 and any(i == 'beer' for i, _ in q['items']) for q in t['needs']['queue']))
        j = Journey('grocery', slot=slot, day=day)
        restock(j)
        tid = j.task['id']
        j.act('ask')
        while j.get(tid)['status'] != 'completed':
            t = j.get(tid)
            r = t['rush']
            q = t['needs']['queue'][r['i']]
            if any(i == 'beer' for i, _ in q['items']) and str(r['i']) not in r['ages'] and q['npc'] != 3:
                j.act('gr_rush_id', task=tid)
                continue
            o = r['offer']
            j.act('gr_rush_total', task=tid, total=sum(G._price(j.c, k) * v for k, v in o['units'].items()))
            t = j.get(tid)
            if t['status'] != 'completed' and t['rush']['offer'] and t['rush']['offer']['changes']:
                o = t['rush']['offer']
                j.act('gr_rush_change', task=tid, change=sum(o['tender']) - o['charged'])
        t = j.get(tid)
        self.assertEqual(t['slips'][0]['code'], 'minor_beer')
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertLess(t['reaction']['cut'], t['rush']['cash'])    # one customer's worth, not the whole queue
        self.assertEqual(self._review(j, tid)['stars'], 1)
        roundtrip(j)

    def test_short_bulk_delivery_is_a_slip(self):
        day, slot = find(lambda t: t['kind'] == 'bulk')
        j = Journey('grocery', slot=slot, day=day)
        restock(j)
        tid = j.task['id']
        j.act('ask')
        j.act('gr_bulk_quote', off=15)
        t = j.task
        for x in t['needs']['lines']:
            top_up(j, x['item'], x['qty'])
        set_stock(j, t['needs']['lines'][0]['item'], 0)
        j.act('gr_bulk_deliver', confirm=True, partial=True)
        t = j.get(tid)
        self.assertEqual(t['slips'][0]['code'], 'short')
        self.assertLessEqual(self._review(j, tid)['stars'], 3)
        roundtrip(j)


if __name__ == '__main__':
    unittest.main()
