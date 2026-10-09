"""Đơn gộp: a per-supplier draft placed as ONE order (game/inventory.py, 0.9.20).

The draft (add, change a quantity, remove, clear), one shipping fee per order and the free-shipping
line, wholesale tiers on a line, one payment and one row in the books, one van and one crate,
short or late merged deliveries and their claims, the suppliers' push-back (minimum order, a line
out of stock, a merged load that rides a later van), the player's own "xin bớt" answered from
hidden traits (deterministic), and orders placed before all this (no `ship`, no `group`) left
exactly as they were.
"""
import copy
import unittest
from unittest.mock import patch

import game.careers.kit as kit
from game import inventory as I
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey
from tests.test_inventory_flow import empty, public_inv, set_money, wait_until_ready
from tests.helpers import Journey  # noqa: F811


def cart(j, sid='partner'):
    return next((k for k in public_inv(j)['carts'] if k['supplier'] == sid), None)


def add(j, sid, item, qty):
    return j.act('inv_cart', supplier=sid, op='add', item=item, qty=qty)


def group_lines(j, gid):
    return [o for o in j.c['ext']['inv']['orders'] if o.get('group') == gid]


def books(j, ref):
    return [r for r in j.c['ops']['finance']['ledger'] if r['ref'] == ref]


def fresh(career='restaurant', items=('noodle', 'egg', 'beef', 'sausage', 'mushroom'), money=2000):
    j = Journey(career)
    for i in items:
        empty(j.c, i)
    set_money(j.c, money)
    return j


def receive_all(j, gid):
    lines = [o for o in group_lines(j, gid) if o['status'] == 'in_transit']
    return j.act('inv_receive', group=gid, counts={o['id']: o['actual'] for o in lines})


def place(j, sid='partner'):
    r = j.act('inv_order_cart', supplier=sid, confirm=True)
    return r, r['eta']['group']


class Draft(unittest.TestCase):
    def test_add_change_remove_clear(self):
        j = fresh()
        turn = j.c['turn']
        add(j, 'partner', 'noodle', 6)
        add(j, 'partner', 'egg', 4)
        add(j, 'partner', 'noodle', 2)  # the same item again: one line, more units
        k = cart(j)
        self.assertEqual([(l['item'], l['qty']) for l in k['lines']], [('noodle', 8), ('egg', 4)])
        self.assertEqual(j.c['turn'], turn, 'editing a draft takes no shop time')
        j.act('inv_cart', supplier='partner', op='set', item='egg', qty=7)
        self.assertEqual(cart(j)['lines'][1]['qty'], 7)
        j.act('inv_cart', supplier='partner', op='remove', item='noodle')
        self.assertEqual([l['item'] for l in cart(j)['lines']], ['egg'])
        j.act('inv_cart', supplier='partner', op='set', item='egg', qty=0)  # 0 removes the last line
        self.assertIsNone(cart(j))
        self.assertNotIn('cart', j.c['ext']['inv'], 'an empty draft leaves nothing behind in the save')
        add(j, 'market', 'egg', 3)
        j.act('inv_cart', supplier='market', op='clear')
        self.assertEqual(public_inv(j)['carts'], [])
        validate_state(j.state)

    def test_one_draft_per_supplier_and_the_raw_draft_stays_inside(self):
        j = fresh()
        add(j, 'partner', 'noodle', 5)
        add(j, 'market', 'egg', 5)
        pub = public_inv(j)
        self.assertEqual({k['supplier'] for k in pub['carts']}, {'partner', 'market'})
        self.assertNotIn('cart', pub)
        self.assertNotIn('haggle', pub)

    @patch.object(I, 'CART_LINES', 8)  # the full-draft rules, at the size the restaurant catalogue fills
    def test_guard_rails(self):
        j = fresh()
        with self.assertRaises(GameError):
            add(j, 'dalat', 'noodle', 2)  # not this career's supplier
        with self.assertRaises(GameError):
            add(j, 'import', 'egg', 2)  # the importer does not sell eggs
        with self.assertRaises(GameError):
            add(j, 'partner', 'noodle', 31)
        add(j, 'partner', 'noodle', 25)
        with self.assertRaises(GameError):
            add(j, 'partner', 'noodle', 6)  # 31 on one line
        cap = I.capacity('restaurant')
        kit.add_lot(j.c, 'egg', cap - 3, 1, 9, 'test')
        with self.assertRaises(GameError) as e:
            add(j, 'partner', 'egg', 4)
        self.assertIn('chỉ còn chỗ cho 3', e.exception.message)
        r = j.act('inv_cart', supplier='partner', op='add', lines=[dict(item='egg', qty=10), dict(item='sausage', qty=4)], fit=True)
        self.assertIn('3 món', r['message'])
        self.assertEqual({l['item']: l['qty'] for l in cart(j)['lines']}['egg'], 3, '`fit` trims to the room left')
        items = [i['id'] for i in I.catalogue('restaurant') if i.get('unlock', 1) <= 1 and i['id'] not in ('noodle', 'egg', 'sausage')]
        for i in items[:I.CART_LINES - 3]:
            add(j, 'partner', i, 1)
        self.assertEqual(len(cart(j)['lines']), I.CART_LINES)
        with self.assertRaises(GameError):
            add(j, 'partner', items[I.CART_LINES - 3], 1)
        with self.assertRaises(GameError):
            j.act('inv_order_cart', supplier='partner')  # not confirmed
        validate_state(j.state)


class FullDraft(unittest.TestCase):
    """A draft holds CART_LINES lines: the client is told (`cart_lines`), and a "gộp N món thiếu" batch (`fit`)
    adds what fits and says what stayed out instead of refusing the whole batch (player data: inv_cart 47% refused)."""

    def setUp(self):
        # The full-draft rules at the size these catalogues can fill (CART_LINES is 20 since 1.7.16).
        p = patch.object(I, 'CART_LINES', 8)
        p.start()
        self.addCleanup(p.stop)


    def items(self, n, skip=()):
        out = [i['id'] for i in I.catalogue('restaurant') if i.get('unlock', 1) <= 1 and i['id'] not in skip]
        self.assertGreaterEqual(len(out), n)
        return out[:n]

    def test_public_says_how_many_lines_a_draft_holds(self):
        j = fresh()
        self.assertEqual(public_inv(j)['cart_lines'], I.CART_LINES)

    def test_fit_batch_into_a_nearly_full_draft(self):
        j = fresh(money=50000)
        ids = self.items(I.CART_LINES + 2)
        for i in ids[:I.CART_LINES - 1]:
            add(j, 'partner', i, 1)
        rest = ids[I.CART_LINES - 1:]
        r = j.act('inv_cart', supplier='partner', op='add', lines=[dict(item=i, qty=1) for i in rest], fit=True)
        self.assertEqual(len(cart(j)['lines']), I.CART_LINES)
        self.assertIn(f'còn {len(rest) - 1} món chưa thêm', r['message'])
        self.assertEqual([l['item'] for l in cart(j)['lines']], ids[:I.CART_LINES])
        validate_state(j.state)
        # A line already in the full draft still grows; only new lines are left out.
        r = j.act('inv_cart', supplier='partner', op='add', lines=[dict(item=ids[0], qty=1), dict(item=rest[-1], qty=1)], fit=True)
        self.assertEqual({l['item']: l['qty'] for l in cart(j)['lines']}[ids[0]], 2)
        self.assertIn('còn 1 món chưa thêm', r['message'])

    def test_full_draft_refuses_with_the_next_step(self):
        j = fresh(money=50000)
        ids = self.items(I.CART_LINES + 1)
        for i in ids[:I.CART_LINES]:
            add(j, 'partner', i, 1)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError) as e:
            j.act('inv_cart', supplier='partner', op='add', lines=[dict(item=ids[-1], qty=1)], fit=True)
        self.assertIn(f'đủ {I.CART_LINES} món', e.exception.message)
        self.assertEqual(j.state, before)
        with self.assertRaises(GameError) as e:
            add(j, 'partner', ids[-1], 1)  # a single line without `fit` is refused as before
        self.assertIn(f'tối đa {I.CART_LINES} món', e.exception.message)
        self.assertEqual(j.state, before)


class LongBatch(unittest.TestCase):
    """The nail shop opens with 20 items low and the stock room's "🛒 Gộp N món" step listed them all:
    inv_cart refused the whole batch ("Danh sách hàng không hợp lệ."). A `fit` batch longer than a draft
    now fills the draft and says what stayed out; without `fit` the old limit stands."""

    def setUp(self):
        # The full-draft rules at the size these catalogues can fill (CART_LINES is 20 since 1.7.16).
        p = patch.object(I, 'CART_LINES', 8)
        p.start()
        self.addCleanup(p.stop)


    def low(self, j):
        inv = public_inv(j)
        return [i['id'] for i in I.catalogue('nail') if inv['stock'].get(i['id'], 0) <= 6]

    def test_nail_shop_twenty_low_items(self):
        j = Journey('nail')
        low = self.low(j)
        self.assertGreater(len(low), I.CART_LINES)
        r = j.act('inv_cart', supplier='partner', op='add', lines=[dict(item=i, qty=10) for i in low], fit=True)
        self.assertEqual([l['item'] for l in cart(j)['lines']], low[:I.CART_LINES])
        self.assertIn(f'còn {len(low) - I.CART_LINES} món chưa thêm', r['message'])
        validate_state(j.state)

    def test_guide_sized_draft_is_placed(self):
        # What views.js fillGo now sends for a fresh nail shop (restock.js fitDraft, 320 xu in the fund).
        j = Journey('nail')
        lines = [dict(item=i, qty=6) for i in self.low(j)[:I.CART_LINES]]
        lines[0]['qty'] = 5
        j.act('inv_cart', supplier='partner', op='add', lines=lines, fit=True)
        k = cart(j)
        self.assertEqual((k['n'], k['short']), (I.CART_LINES, 0))
        money = j.c['money']
        r, _ = place(j)
        self.assertEqual(j.c['money'], money - k['total'])
        validate_state(j.state)

    def test_limits_without_fit_and_too_long(self):
        j = Journey('nail')
        low = self.low(j)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('inv_cart', supplier='partner', op='add', lines=[dict(item=i, qty=1) for i in low[:I.CART_LINES + 1]])
        with self.assertRaises(GameError):
            j.act('inv_cart', supplier='partner', op='add', lines=[dict(item=low[0], qty=1)] * (I.FIT_LINES + 1), fit=True)
        self.assertEqual(j.state, before)


class Prices(unittest.TestCase):
    def test_bulk_tiers_on_a_line(self):
        sup = I.supplier('restaurant', 'partner')
        it = I.item('restaurant', 'noodle')
        p9, p10, p20 = (I.line_price(it, q, sup) for q in (9, 10, 20))
        self.assertEqual(p9['bulk'], 0)
        self.assertEqual(p9['cost'], max(1, -(-it['cost'] * 9 * sup['factor'] // 1)), 'below a tier: the old price')
        self.assertEqual(p9['next_tier'], [10, 4])
        self.assertEqual((p10['bulk'], p20['bulk']), (4, 8))
        self.assertLess(p10['cost'], p10['full'])
        self.assertLess(p20['cost'] / 20, p10['cost'] / 10, 'more units, cheaper per unit')
        self.assertIsNone(p20['next_tier'])
        for cid in ('restaurant', 'grocery', 'florist', 'cafe_bakery', 'salon', 'fruit', 'clothing'):
            for s in I.suppliers(cid):
                with self.subTest(career=cid, supplier=s['id']):
                    self.assertTrue(s['bulk'] and s['ship'] > 0 and s['free_from'] > s['ship'])
                    for i in I.catalogue(cid):
                        for q in (1, 5, 10, 20, 30):
                            p = I.line_price(i, q, s)
                            self.assertTrue(1 <= p['cost'] <= p['full'])
                            self.assertEqual(p['full'] - p['cost'] > 0, p['bulk'] > 0)

    def test_a_single_order_gets_the_tier_and_pays_its_fee(self):
        j = fresh()
        money = j.c['money']
        j.act('inv_order', item='noodle', qty=10, supplier='partner', confirm=True)
        o = j.c['ext']['inv']['orders'][-1]
        p = I.line_price(I.item('restaurant', 'noodle'), 10, I.supplier('restaurant', 'partner'))
        self.assertEqual(o['cost'], p['cost'])
        self.assertEqual(o['ship'], I.ship_fee(I.supplier('restaurant', 'partner'), p['cost']))
        self.assertEqual(j.c['money'], money - o['cost'] - o['ship'])
        self.assertNotIn('group', o)

    def test_one_fee_for_a_merged_order_instead_of_one_per_line(self):
        lines = (('noodle', 4), ('egg', 4), ('sausage', 3))
        a = fresh()
        money = a.c['money']
        for i, q in lines:
            a.act('inv_order', item=i, qty=q, supplier='partner', confirm=True)
        singles = money - a.c['money']
        fees = sum(o['ship'] for o in a.c['ext']['inv']['orders'][-3:])
        b = fresh()
        for i, q in lines:
            add(b, 'partner', i, q)
        k = cart(b)
        self.assertGreater(k['ship'], 0, 'a small draft still pays shipping')
        money = b.c['money']
        r, gid = place(b)
        self.assertEqual(money - b.c['money'], k['total'])
        self.assertEqual(singles - fees + k['ship'], k['total'], 'same goods, one fee instead of three')
        self.assertEqual(len(books(b, gid)), 1, 'one row in the books')
        self.assertEqual(books(b, gid)[0]['amount'], -k['total'])
        ls = group_lines(b, gid)
        self.assertEqual(len(ls), 3)
        self.assertEqual(sum(o.get('ship', 0) for o in ls), k['ship'], 'the fee is kept once, on the first line')
        self.assertEqual(len({(o['lo'], o['hi'], o['at'], o['late']) for o in ls}), 1, 'one van')
        self.assertIsNone(cart(b), 'a placed draft is gone')
        validate_state(b.state)

    def test_free_shipping_from_the_line(self):
        j = fresh()
        sup = I.supplier('restaurant', 'partner')
        add(j, 'partner', 'beef', 4)
        k = cart(j)
        self.assertEqual(k['ship'], sup['ship'])
        self.assertEqual(k['to_free'], sup['free_from'] - k['goods'])
        add(j, 'partner', 'noodle', 10)
        add(j, 'partner', 'egg', 10)
        k = cart(j)
        self.assertGreaterEqual(k['goods'], sup['free_from'])
        self.assertEqual((k['ship'], k['to_free']), (0, 0))
        self.assertEqual(k['total'], k['goods'])
        self.assertGreater(k['bulk_off'], 0)
        self.assertEqual(k['full'] - k['bulk_off'], k['goods'])

    def test_what_the_fund_lacks(self):
        j = fresh(money=10)
        add(j, 'partner', 'beef', 6)
        k = cart(j)
        self.assertEqual(k['short'], k['total'] - 10)
        with self.assertRaises(GameError) as e:
            place(j)
        self.assertIn(f'Thiếu {k["short"]} xu', e.exception.message)
        self.assertEqual(j.c['money'], 10)


class Delivery(unittest.TestCase):
    def test_one_crate_counted_and_received_together(self):
        j = fresh()
        for i, q in (('noodle', 6), ('egg', 5), ('sausage', 4)):
            add(j, 'partner', i, q)
        _, gid = place(j)
        pub = public_inv(j)
        self.assertEqual({o['id'] for o in pub['orders'] if o.get('group') == gid}, {f'{gid}-1', f'{gid}-2', f'{gid}-3'})
        with self.assertRaises(GameError):
            receive_all(j, gid)  # not here yet
        wait_until_ready(j, f'{gid}-1')
        lines = group_lines(j, gid)
        self.assertTrue(all(o['ready_now'] for o in public_inv(j)['orders'] if o.get('group') == gid), 'all lines arrive together')
        bad = {o['id']: o['actual'] for o in lines}
        bad[lines[1]['id']] += 1
        with self.assertRaises(GameError) as e:
            j.act('inv_receive', group=gid, counts=bad)
        self.assertIn(I.item('restaurant', lines[1]['item'])['name'], e.exception.message, 'says which line to count again')
        self.assertTrue(all(o['status'] == 'in_transit' for o in group_lines(j, gid)), 'nothing half-received')
        receive_all(j, gid)
        for o in group_lines(j, gid):
            self.assertEqual(o['status'], 'received')
            self.assertEqual(kit.stock(j.c, o['item']), o['actual'])
        stars = j.act('inv_rate', group=gid, stars=5)
        self.assertIn('Hạt Nắng', stars['message'])
        self.assertEqual(j.c['ext']['inv']['supplier_ratings']['partner']['count'], 1, 'one merged order, one rating')
        with self.assertRaises(GameError):
            j.act('inv_rate', group=gid, stars=4)
        validate_state(j.state)

    def _find(self, want, career='restaurant', sid='market', items=('noodle', 'egg', 'sausage', 'mushroom'), tries=40):
        """Place merged orders until one shows `want` (deterministic: same ids, same outcome)."""
        j = fresh(career, items)
        for _ in range(tries):
            for i in items:
                add(j, sid, i, 6)
            r, gid = place(j, sid)
            if want(j, r, gid):
                return j, r, gid
            for o in group_lines(j, gid):  # make room for the next try
                o['status'] = 'received'
            for i in items:
                empty(j.c, i)
            j.c['ext']['inv'].pop('cart', None)
        self.fail('no merged order showed it')

    def test_short_merged_delivery_and_one_claim(self):
        j, r, gid = self._find(lambda j, r, gid: any(o['actual'] < o['qty'] for o in group_lines(j, gid)))
        wait_until_ready(j, f'{gid}-1')
        got = receive_all(j, gid)
        short = [o for o in group_lines(j, gid) if o['actual'] < o['qty']]
        refund = sum(I._refund(o) for o in short)
        self.assertEqual(got['short']['refund'], refund)
        self.assertEqual(got['short']['group'], gid)
        money = j.c['money']
        j.act('inv_claim', group=gid)
        self.assertEqual(j.c['money'], money + refund)
        self.assertEqual(len([x for x in books(j, gid) if x['amount'] > 0]), 1, 'one refund row')
        with self.assertRaises(GameError):
            j.act('inv_claim', group=gid)
        with self.assertRaises(GameError):
            j.act('inv_claim', order=short[0]['id'])  # nor line by line afterwards
        self.assertLessEqual(refund, sum(o['cost'] for o in short), 'never more than was paid for the missing goods')
        validate_state(j.state)

    def test_a_line_of_a_merged_order_can_still_be_claimed_alone(self):
        j, r, gid = self._find(lambda j, r, gid: any(o['actual'] < o['qty'] for o in group_lines(j, gid)))
        wait_until_ready(j, f'{gid}-1')
        receive_all(j, gid)
        o = next(o for o in group_lines(j, gid) if o['actual'] < o['qty'])
        money = j.c['money']
        j.act('inv_claim', order=o['id'])
        self.assertEqual(j.c['money'], money + I._refund(o))

    def test_late_merged_delivery(self):
        j, r, gid = self._find(lambda j, r, gid: group_lines(j, gid)[0]['late'] is not None, sid='partner', tries=80)
        ls = group_lines(j, gid)
        self.assertTrue(all(o['late'] == ls[0]['late'] and o['at'] == ls[0]['at'] for o in ls))
        po = next(o for o in public_inv(j)['orders'] if o['id'] == ls[0]['id'])
        self.assertNotIn('late', po)
        self.assertIsNone(po['late_note'], 'a delay is discovered when it happens')
        wait_until_ready(j, ls[0]['id'])
        receive_all(j, gid)
        validate_state(j.state)


class PushBack(unittest.TestCase):
    def test_minimum_order_at_the_wholesaler(self):
        j = fresh(items=('pack_kimchi', 'cheese_slice'))
        sup = I.supplier('restaurant', 'import')
        add(j, 'import', 'cheese_slice', 2)
        k = cart(j, 'import')
        self.assertEqual(k['min_order'], sup['min_order'])
        self.assertGreater(k['below_min'], 0)
        money = j.c['money']
        with self.assertRaises(GameError) as e:
            place(j, 'import')
        self.assertIn(str(sup['min_order']), e.exception.message)
        self.assertEqual(j.c['money'], money)
        # A single order from the same importer is unchanged: no minimum there.
        j.act('inv_order', item='pack_kimchi', qty=2, supplier='import', confirm=True)
        add(j, 'import', 'cheese_slice', 20)
        self.assertEqual(cart(j, 'import')['below_min'], 0)
        place(j, 'import')

    def test_one_line_out_of_stock(self):
        j, r, gid = Delivery._find(Delivery(), lambda j, r, gid: r.get('oos'))
        gone = r['oos']
        self.assertNotIn(gone, {o['item'] for o in group_lines(j, gid)}, 'not shipped')
        self.assertIn('Không tính tiền', r['message'])
        k = cart(j, 'market')
        self.assertEqual([(l['item'], l['oos']) for l in k['lines']], [(gone, True)], 'stays in the draft, flagged')
        self.assertEqual(k['n'], 0)
        paid = -books(j, gid)[0]['amount']
        self.assertEqual(paid, sum(o['cost'] for o in group_lines(j, gid)) + group_lines(j, gid)[0]['ship'])
        with self.assertRaises(GameError) as e:
            place(j, 'market')
        self.assertIn('hết', e.exception.message)
        # Tomorrow the stall has it again.
        j.act('end_day', carry_event=True)
        j.act('start_day')
        k = cart(j, 'market')
        self.assertFalse(k['lines'][0]['oos'])
        validate_state(j.state)

    def test_a_merged_load_can_ride_a_later_van(self):
        j, r, gid = Delivery._find(Delivery(), lambda j, r, gid: r.get('later'), sid='partner', tries=80)
        o = group_lines(j, gid)[0]
        self.assertIn('mới giao được', r['message'])
        self.assertLess(o['placed'], o['lo'])
        quoted = I.quote(I.supplier('restaurant', 'partner'), 'restaurant', o['placed'])
        self.assertGreater(o['lo'], quoted['lo'], 'later than the van it would have caught')
        validate_state(j.state)

    def test_push_back_is_deterministic(self):
        def run():
            j = fresh()
            out = []
            for _ in range(6):
                for i in ('noodle', 'egg', 'sausage'):
                    add(j, 'market', i, 5)
                r, gid = place(j, 'market')
                out.append((r['message'], [(o['item'], o['actual'], o['at'], o['late']) for o in group_lines(j, gid)]))
                for o in group_lines(j, gid):
                    o['status'] = 'received'
                for i in ('noodle', 'egg', 'sausage'):
                    empty(j.c, i)
                j.c['ext']['inv'].pop('cart', None)
            return out
        self.assertEqual(run(), run())


class Haggle(unittest.TestCase):
    def test_answers_come_from_hidden_traits_and_are_deterministic(self):
        for cid in ('restaurant', 'grocery', 'florist', 'salon'):
            for sup in I.suppliers(cid):
                for day in (1, 2, 7):
                    for goods in (30, 200):
                        answers = [I.haggle(cid, sup, day, ask, goods) for ask in I.ASKS]
                        with self.subTest(career=cid, supplier=sup['id'], day=day, goods=goods):
                            self.assertEqual(answers, [I.haggle(cid, sup, day, ask, goods) for ask in I.ASKS])
                            for ask, d in zip(I.ASKS, answers):
                                self.assertLessEqual(d['pct'], ask, 'never more than asked')
                                self.assertIn(d['mood'], ('ok', 'counter', 'ship', 'no', 'sour'))
                                self.assertEqual(d['mood'] == 'ok', d['pct'] == ask)
                                self.assertTrue(d['said'])
                            ok = [d['mood'] == 'ok' for d in answers]
                            self.assertEqual(ok, sorted(ok, reverse=True), 'a smaller ask is never refused when a bigger one is accepted')
        market = I.supplier('restaurant', 'market')
        self.assertEqual(I.haggle('restaurant', market, 3, 5, 200)['mood'], 'ok', 'the market haggles')

    def test_haggle_then_place(self):
        j = fresh()
        for i, q in (('noodle', 10), ('egg', 10), ('beef', 6)):
            add(j, 'market', i, q)
        k = cart(j, 'market')
        self.assertTrue(k['can_haggle'])
        r = j.act('inv_haggle', supplier='market', pct=5)
        deal = I.haggle('restaurant', I.supplier('restaurant', 'market'), j.c['day'], 5, k['goods'])
        self.assertIn(deal['said'], r['message'])
        k = cart(j, 'market')
        self.assertEqual((k['pct'], k['deal']['said']), (deal['pct'], deal['said']))
        self.assertFalse(k['can_haggle'])
        self.assertEqual(k['off'], k['goods'] * deal['pct'] // 100)
        with self.assertRaises(GameError):
            j.act('inv_haggle', supplier='market', pct=10)  # one answer a day
        money = j.c['money']
        _, gid = place(j, 'market')
        ls = group_lines(j, gid)
        self.assertEqual(money - j.c['money'], k['total'])
        self.assertEqual(sum(o['cost'] for o in ls), k['goods'] - k['off'], 'the discount is shared over the lines')
        self.assertEqual(ls[0]['off'], k['off'])
        validate_state(j.state)

    def test_a_smaller_draft_loses_the_haggled_price(self):
        j = fresh()
        for i, q in (('noodle', 10), ('egg', 10), ('beef', 6)):
            add(j, 'market', i, q)
        j.act('inv_haggle', supplier='market', pct=5)
        if not cart(j, 'market')['pct']:
            self.skipTest('the stall said no today')
        j.act('inv_cart', supplier='market', op='remove', item='beef')
        k = cart(j, 'market')
        self.assertEqual(k['pct'], 0)
        self.assertTrue(k['deal']['lost'])
        add(j, 'market', 'beef', 6)
        self.assertEqual(cart(j, 'market')['pct'], 5, 'back to the size it was agreed on')

    def test_small_drafts_and_empty_drafts(self):
        j = fresh()
        with self.assertRaises(GameError):
            j.act('inv_haggle', supplier='market', pct=5)
        add(j, 'market', 'egg', 2)
        self.assertFalse(cart(j, 'market')['can_haggle'])
        with self.assertRaises(GameError) as e:
            j.act('inv_haggle', supplier='market', pct=5)
        self.assertIn('xin bớt', e.exception.message)
        self.assertNotIn('haggle', j.c['ext']['inv'], 'a refused small ask does not use the day\'s answer')
        with self.assertRaises(GameError):
            j.act('inv_haggle', supplier='market', pct=7)  # only the offered asks


class OldSaves(unittest.TestCase):
    LIVE_ORDER = dict(id='po-3', item='noodle', qty=6, actual=5, supplier='partner', cost=18, unit_cost=3,
                      status='in_transit', day=1, claimed=False, rating=None, reply=None)

    def test_an_open_single_order_from_before_keeps_working(self):
        j = fresh()
        x = j.c['ext']['inv']
        clk = I.clock(j.c, 'restaurant')
        x['seq'] = 3
        x['orders'].append(dict(self.LIVE_ORDER, placed=clk['abs'], lo=clk['abs'] + 40, hi=clk['abs'] + 60,
                                at=clk['abs'] + 50, late=None))
        before = copy.deepcopy(x['orders'][-1])
        validate_state(j.state)
        add(j, 'partner', 'egg', 4)  # a draft beside it changes nothing in it
        place(j)
        self.assertEqual(x['orders'][0], before)
        wait_until_ready(j, 'po-3')
        money = j.c['money']
        r = j.act('inv_receive', order='po-3', count=5)
        self.assertEqual(r['short']['refund'], I._refund(before))
        j.act('inv_claim', order='po-3')
        self.assertEqual(j.c['money'], money + I._refund(before), 'refund exactly as before: no fee was paid, none is refunded')
        o = next(o for o in j.c['ext']['inv']['orders'] if o['id'] == 'po-3')
        self.assertNotIn('ship', o)
        self.assertNotIn('group', o)
        validate_state(j.state)

    def test_shipments_count_vans_not_lines(self):
        j = fresh()
        for _ in range(3):
            for i in ('noodle', 'egg', 'sausage'):
                add(j, 'express', i, 1)
            place(j, 'express')
        self.assertEqual(I._shipments(j.c['ext']['inv']), 3)
        self.assertEqual(I._transit_lines(j.c['ext']['inv']), 9)


class Validation(unittest.TestCase):
    def test_bad_drafts_are_rejected(self):
        j = fresh()
        add(j, 'partner', 'noodle', 4)
        validate_state(j.state)
        bad = [
            lambda x: x['cart'].update(nobody=dict(lines=[dict(item='egg', qty=1)])),
            lambda x: x['cart']['partner']['lines'].append(dict(item='egg', qty=0)),
            lambda x: x['cart']['partner']['lines'].append(dict(item='lamp', qty=1)),
            lambda x: x['cart']['partner']['lines'].append(dict(item='noodle', qty=1)),
            lambda x: x['cart']['partner'].update(lines=[]),
            lambda x: x['cart']['partner'].update(deal=dict(day=1)),
            lambda x: x['cart']['partner'].update(extra=1),
            lambda x: x.update(haggle=dict(partner='today')),
            lambda x: x['orders'].append(dict(I.inv(j.c)['orders'][0] if I.inv(j.c)['orders'] else {}, group=5)),
        ]
        for k, spoil in enumerate(bad):
            s = copy.deepcopy(j.state)
            x = s['careers']['restaurant']['ext']['inv']
            with self.subTest(case=k):
                spoil(x)
                with self.assertRaises(GameError):
                    validate_state(s)

    def test_public_view_of_a_save_without_drafts(self):
        j = fresh()
        self.assertEqual(public_state(j.state)['careers']['restaurant']['inventory']['carts'], [])
        sups = public_inv(j)['suppliers']
        self.assertTrue(all('ship' in s and 'bulk' in s and 'free_from' in s for s in sups))


class WideDraft(unittest.TestCase):
    """F#198: 20 lines a draft, several sizes of one item, 12 orders on the way; a draft is still
    saved so a release before 1.7.16 (8 lines, one per item in inv['cart']) loads it."""

    def old_rules_hold(self, j):
        for sid, k in (j.c['ext']['inv'].get('cart') or {}).items():
            self.assertLessEqual(len(k['lines']), 8)
            self.assertEqual(len({l['item'] for l in k['lines']}), len(k['lines']))

    def test_twenty_lines_one_order(self):
        j = Journey('nail')
        set_money(j.c, 50000)
        inv = public_inv(j)
        self.assertEqual((inv['cart_lines'], inv['transit_cap']), (20, 12))
        ids = [i['id'] for i in I.catalogue('nail') if inv['room'][i['id']] >= 2][:20]
        self.assertEqual(len(ids), 20)
        j.act('inv_cart', supplier='partner', op='add', lines=[dict(item=i, qty=2) for i in ids])
        self.assertEqual(len(cart(j)['lines']), 20)
        self.assertEqual(len(j.c['ext']['inv']['cart']['partner']['lines']), 8)
        self.assertEqual(len(j.c['ext']['inv']['cart_more']['partner']), 12)
        self.old_rules_hold(j)
        validate_state(j.state)
        self.assertNotIn('cart_more', public_inv(j))
        # Change and drop a line kept in the overflow.
        j.act('inv_cart', supplier='partner', op='set', item=ids[15], qty=3)
        j.act('inv_cart', supplier='partner', op='remove', item=ids[19])
        self.assertEqual({l['item']: l['qty'] for l in cart(j)['lines']}[ids[15]], 3)
        self.assertEqual(len(cart(j)['lines']), 19)
        money, k = j.c['money'], cart(j)
        r, gid = place(j)
        self.assertEqual(len(group_lines(j, gid)), 19)
        self.assertEqual(j.c['money'], money - k['total'])
        self.assertEqual(len(books(j, gid)), 1)
        self.assertNotIn('cart', j.c['ext']['inv']); self.assertNotIn('cart_more', j.c['ext']['inv'])
        validate_state(j.state)
        with self.assertRaises(GameError):
            j.act('inv_cart', supplier='partner', op='add', lines=[dict(item=i, qty=1) for i in [*ids, ids[0]]][:21])

    def test_several_sizes_of_one_item(self):
        j = Journey('clothing')
        set_money(j.c, 50000)
        for size, qty in (('S', 2), ('M', 3), ('L', 1)):
            j.act('inv_cart', supplier='partner', op='add', item='tee', qty=qty, size=size)
        j.act('inv_cart', supplier='partner', op='add', item='tee', qty=1, size='M')
        rows = {(l['item'], l.get('size')): l['qty'] for l in cart(j)['lines']}
        self.assertEqual(rows, {('tee', 'S'): 2, ('tee', 'M'): 4, ('tee', 'L'): 1})
        self.old_rules_hold(j)
        validate_state(j.state)
        with self.assertRaises(GameError) as e:
            j.act('inv_cart', supplier='partner', op='set', item='tee', qty=2)
        self.assertIn('nhiều size', e.exception.message)
        j.act('inv_cart', supplier='partner', op='set', item='tee', size='L', qty=2)
        j.act('inv_cart', supplier='partner', op='remove', item='tee', size='S')
        rows = {(l['item'], l.get('size')): l['qty'] for l in cart(j)['lines']}
        self.assertEqual(rows, {('tee', 'M'): 4, ('tee', 'L'): 2})
        # The shelf counts every size of the item together.
        room = public_inv(j)['room']['tee']
        with self.assertRaises(GameError) as e:
            j.act('inv_cart', supplier='partner', op='add', item='tee', qty=room - 5, size='XL')
        self.assertIn('chỉ còn chỗ', e.exception.message)
        r, gid = place(j)
        held = [(l['size'], l['qty']) for l in (cart(j) or {}).get('lines', [])]  # a line out of stock today stays
        self.assertEqual(sorted([(o['size'], o['qty']) for o in group_lines(j, gid)] + held), [('L', 2), ('M', 4)])
        validate_state(j.state)

    def test_twelve_orders_on_the_way(self):
        j = fresh(money=50000)
        for n in range(I.TRANSIT_CAP):
            j.act('inv_order', item='egg' if n % 2 else 'noodle', qty=1, supplier='partner', confirm=True)
        with self.assertRaises(GameError):
            j.act('inv_order', item='beef', qty=1, supplier='partner', confirm=True)
        self.assertEqual(I.TRANSIT_CAP, 12)
        validate_state(j.state)

    def test_old_saves_and_orphan_overflow_load(self):
        j = fresh(money=50000)
        add(j, 'partner', 'noodle', 2)
        x = j.c['ext']['inv']
        # A release before 1.7.16 placed the first lines and left the overflow behind.
        x['cart_more'] = {'partner': [dict(item='egg', qty=2)]}
        x.pop('cart')
        validate_state(j.state)
        self.assertEqual([(l['item'], l['qty']) for l in cart(j)['lines']], [('egg', 2)])
        r = j.act('inv_haggle', supplier='partner', pct=5) if cart(j)['can_haggle'] else None
        add(j, 'partner', 'beef', 1)
        self.assertEqual([l['item'] for l in j.c['ext']['inv']['cart']['partner']['lines']], ['egg', 'beef'])
        self.assertNotIn('cart_more', j.c['ext']['inv'])
        validate_state(j.state)
        bad = copy.deepcopy(j.state)
        bad['careers']['restaurant']['ext']['inv']['cart']['partner']['lines'].append(dict(item='egg', qty=1))
        with self.assertRaises(GameError):
            validate_state(bad)


class Cancel(unittest.TestCase):
    """Player #276 "thêm dòng hủy hàng đang đặt": an order still on the road can be called off (inv_cancel),
    goods and shipping back once, no shop time; not once the crate is at the door; the order leaves the
    book, so a save written after a cancel still loads on the release this one may roll back to."""

    def test_single_order_full_refund_and_gone(self):
        j = fresh()
        money, turn = j.c['money'], j.c['turn']
        r = j.act('inv_order', item='noodle', qty=5, supplier='partner', confirm=True)
        oid = r['eta']['order']
        o = next(o for o in j.c['ext']['inv']['orders'] if o['id'] == oid)
        paid = o['cost'] + o.get('ship', 0)
        self.assertEqual(money - j.c['money'], paid)
        self.assertEqual(public_inv(j)['arriving']['noodle'], 5)
        turn = j.c['turn']
        with self.assertRaises(GameError):
            j.act('inv_cancel', order=oid)  # asks first
        r = j.act('inv_cancel', order=oid, confirm=True)
        self.assertEqual(r['refund'], paid)
        self.assertEqual(j.c['money'], money)
        self.assertEqual(j.c['turn'], turn, 'a phone call takes no shop time')
        self.assertFalse(any(o['id'] == oid for o in j.c['ext']['inv']['orders']))
        self.assertEqual(public_inv(j)['arriving']['noodle'], 0)
        self.assertEqual([x['category'] for x in books(j, oid)], ['stock', 'refund'])
        with self.assertRaises(GameError):
            j.act('inv_cancel', order=oid, confirm=True)  # never twice
        validate_state(j.state)

    def test_merged_order_cancels_whole_with_shipping(self):
        j = fresh()
        add(j, 'partner', 'noodle', 3)
        add(j, 'partner', 'egg', 2)
        money = j.c['money']
        _, gid = place(j)
        lines = group_lines(j, gid)
        self.assertTrue(lines[0].get('ship'), 'a small merged order pays shipping')
        with self.assertRaises(GameError) as e:
            j.act('inv_cancel', order=lines[0]['id'], confirm=True)
        self.assertIn('đơn gộp', e.exception.message)
        r = j.act('inv_cancel', group=gid, confirm=True)
        self.assertEqual(j.c['money'], money)
        self.assertEqual(r['refund'], sum(o['cost'] + o.get('ship', 0) for o in lines))
        self.assertIn('ship', r['message'])
        self.assertEqual(group_lines(j, gid), [])
        self.assertEqual(I._shipments(j.c['ext']['inv']), 0)
        validate_state(j.state)

    def test_not_once_it_is_at_the_door_nor_after_receiving(self):
        j = fresh()
        oid = j.act('inv_order', item='egg', qty=4, supplier='express', confirm=True)['eta']['order']
        wait_until_ready(j, oid)
        money = j.c['money']
        with self.assertRaises(GameError) as e:
            j.act('inv_cancel', order=oid, confirm=True)
        self.assertIn('tới cửa', e.exception.message)
        o = next(o for o in j.c['ext']['inv']['orders'] if o['id'] == oid)
        j.act('inv_receive', order=oid, count=o['actual'])
        with self.assertRaises(GameError):
            j.act('inv_cancel', order=oid, confirm=True)
        self.assertEqual(j.c['money'], money)
        with self.assertRaises(GameError):
            j.act('inv_cancel', group='po-999', confirm=True)

    def test_grocery_order_cancels(self):
        j = Journey('grocery')
        empty(j.c, 'egg')
        set_money(j.c, 2000)
        oid = j.act('inv_order', item='egg', qty=6, supplier='partner', confirm=True)['eta']['order']
        j.act('inv_cancel', order=oid, confirm=True)
        self.assertEqual(j.c['money'], 2000)
        validate_state(j.state)

    def test_saves_after_a_cancel_load_on_the_rollback_release(self):
        import io, json, os, subprocess, sys, tarfile, tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        j = fresh()
        oid = j.act('inv_order', item='noodle', qty=5, supplier='partner', confirm=True)['eta']['order']
        add(j, 'partner', 'egg', 3)
        add(j, 'partner', 'beef', 2)
        _, gid = place(j)
        j.act('inv_order', item='mushroom', qty=2, supplier='market', confirm=True)  # one stays on the way
        j.act('inv_cancel', order=oid, confirm=True)
        j.act('inv_cancel', group=gid, confirm=True)
        validate_state(j.state)
        old = os.environ.get('MNL_OLD_TREE')
        if not old:
            try:
                data = subprocess.run(['git', 'archive', ROLLBACK, 'game', 'reference'], cwd=root, capture_output=True,
                                      timeout=120, check=True).stdout
            except (OSError, subprocess.SubprocessError):
                self.skipTest(f'no git tree with {ROLLBACK} (MNL_OLD_TREE)')
            old = tempfile.mkdtemp(prefix='mnl-1927-')
            with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                tar.extractall(old, filter='data')
        prog = ('import json,sys;from game.engine import validate_state,migrate_state;'
                's=json.load(sys.stdin);validate_state(s);s=migrate_state(s);validate_state(s);'
                'print(len(s["careers"]["restaurant"]["ext"]["inv"]["orders"]))')
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(j.state), capture_output=True, text=True,
                             cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        self.assertEqual(int(out.stdout.strip()), len(j.c['ext']['inv']['orders']))


ROLLBACK = '4533ee17'   # 1.9.27, the release this one may be rolled back to

if __name__ == '__main__':
    unittest.main()
