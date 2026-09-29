"""Milk-tea care loop (game/boba.py, docs/superpowers/specs/2026-09-29-milk-tea-care-design.md):
the shop clock, tea pots and pearl batches that go stale, supplier orders with real delivery
windows, the heat sealer's upkeep, the regulars' card, swaps when something runs out,
tomorrow's forecast, old saves and strict validation."""
import copy
import json
import unittest

from game import boba, inventory
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.helpers import Journey


def st(j):
    return j.c['ext']['data']['boba']


def pub(j):
    return public_state(j.state)['careers']['milk_tea']['data']['boba']


def unchanged(test, j, action, **payload):
    before = copy.deepcopy(j.state)
    with test.assertRaises(GameError):
        j.act(action, **payload)
    test.assertEqual(j.state, before)


def wait_until(j, minute):
    """Let shop time pass (one beat = one wait) until the clock reads `minute` or later."""
    for _ in range(400):
        if boba.now_abs(j.c) >= minute:
            return
        j.act('tea_wait')
    raise AssertionError('clock never got there')


def fresh_lots(j, item):
    return [l for l in j.c['life']['pantry'] if l['item'] == item and l['qty'] > 0]


class ShopClock(unittest.TestCase):
    def test_clock_starts_at_opening_and_never_runs_backwards(self):
        j = Journey('milk_tea')
        self.assertEqual(boba.clock(j.c), '08:00')
        span = st(j)['span']
        self.assertEqual(span, max(30, st(j)['quota'] * 12))
        seen = []
        for _ in range(span + 10):
            j.act('tea_wait')
            seen.append(boba.clock_minutes(j.c))
            st(j)['quota'] += 1  # more guests later in the day must not pull the clock back
        self.assertEqual(seen, sorted(seen))
        self.assertGreater(seen[-1], boba.CLOSE_MIN)  # a busy day runs into overtime
        self.assertLessEqual(seen[-1], boba.LATE_MIN)

    def test_same_hours_as_the_shared_inventory_clock(self):
        # Supplier windows come from game/inventory.py: its hours for this shop must match the counter's clock.
        self.assertEqual(inventory.hours(boba.CAREER), (boba.OPEN_MIN, boba.CLOSE_MIN))

    def test_closed_shop_reads_the_evening_before(self):
        j = Journey('milk_tea')
        j.act('end_day', carry_event=True)
        self.assertEqual(boba.now_abs(j.c), (j.c['day'] - 1) * boba.DAY_MIN + boba.CLOSE_MIN)


class PotsAndPearls(unittest.TestCase):
    def test_bought_goods_cannot_be_conjured_at_the_counter(self):
        j = Journey('milk_tea')
        unchanged(self, j, 'tea_prepare', item='lychee', qty=5, confirm=True)
        unchanged(self, j, 'tea_prepare', item='jelly', qty=5, confirm=True)

    def test_cooking_takes_twenty_minutes_while_open_and_none_before_opening(self):
        j = Journey('milk_tea')
        turn = j.c['turn']
        r = j.act('tea_prepare', item='pearls', qty=5, confirm=True)
        self.assertEqual(j.c['turn'], turn + 1)
        self.assertIn('dẻo tới', r['message'])
        turn = j.c['turn']
        j.act('tea_prepare', item='foam', qty=2, confirm=True)  # whipping foam is quick
        self.assertEqual(j.c['turn'], turn)
        j.act('end_day', carry_event=True)
        turn = j.c['turn']
        j.act('tea_prepare', item='milk', qty=5, confirm=True)  # the evening before: brewed at opening
        self.assertEqual(j.c['turn'], turn)
        lot = fresh_lots(j, 'milk')[-1]
        self.assertEqual(lot['made'], j.c['day'] * boba.DAY_MIN + boba.OPEN_MIN)
        j.act('start_day')
        self.assertEqual(fresh_lots(j, 'milk')[-1]['qty'], 5)  # still there, fresh
        self.assertEqual(boba.band(j.c, fresh_lots(j, 'milk')[-1]), 'fresh')

    def test_pearls_go_tired_then_stale(self):
        j = Journey('milk_tea')
        for l in fresh_lots(j, 'pearls'):
            l['qty'] = 0
        j.act('tea_prepare', item='pearls', qty=4, confirm=True)
        lot = fresh_lots(j, 'pearls')[0]
        good, ok = boba.FRESH['pearls']
        wait_until(j, lot['made'] + good + 1)
        self.assertEqual(boba.band(j.c, lot), 'tired')
        self.assertEqual(pub(j)['stations'][[s['id'] for s in pub(j)['stations']].index('pearls')]['tired'], 4)
        waste = len(j.c['life']['waste'])
        wait_until(j, lot['made'] + ok + 1)
        self.assertEqual(boba.stock(j.c)['pearls'], 0)
        self.assertEqual(len(j.c['life']['waste']), waste + 1)
        self.assertEqual(j.c['life']['waste'][-1]['item'], 'pearls')
        validate_state(j.state)

    def test_warming_pot_keeps_pearls_soft_longer(self):
        j = Journey('milk_tea')
        base = boba.fresh_window(j.c, 'pearls')
        st(j)['upgrades'].append('pot')
        self.assertEqual(boba.fresh_window(j.c, 'pearls'), (base[0] + boba.POT_BONUS, base[1] + boba.POT_BONUS))

    def test_tired_pearls_are_a_small_slip_and_can_be_poured_out(self):
        j = Journey('milk_tea')
        t = j.task
        t['changes'] = []
        t['src'] = dict(fixed=dict(base='milk', flavor=None, toppings=['pearls'], size='M', sugar=50, ice='normal'))
        t['needs'] = boba.derive(t)
        t['patience'] = 100
        for l in fresh_lots(j, 'pearls'):
            l['made'] = boba.now_abs(j.c) - boba.FRESH['pearls'][0] - 10
        self.assertEqual(boba.band(j.c, fresh_lots(j, 'pearls')[0]), 'tired')
        j.act('ask', task=t['id'])
        j.act('tea_cup', task=t['id'], size='M')
        j.act('tea_add', task=t['id'], item='milk')
        r = j.act('tea_add', task=t['id'], item='pearls')
        self.assertIn('hơi cứng', r['message'])
        self.assertEqual(j.get(t['id'])['cup']['tired'], ['pearls'])
        validate_state(j.state)
        for a, p in (('tea_ice', dict(level='normal')), ('tea_sugar', dict(level=50)), ('tea_seal', {})):
            j.act(a, task=t['id'], **p)
        j.act('tea_serve', task=t['id'], confirm=True)
        done = j.get(t['id'])
        self.assertIn('tired', [x['code'] for x in done.get('slips') or []])
        self.assertTrue(all(x['sev'] == 1 for x in done['slips'] if x['code'] == 'tired'))
        # Pouring out the old batch: only tired batches, logged as waste once.
        unchanged(self, j, 'tea_toss', item='milk')
        if not boba.stock(j.c)['pearls']:
            j.act('tea_prepare', item='pearls', qty=3, confirm=True)
        for l in fresh_lots(j, 'pearls'):
            l['made'] = boba.now_abs(j.c) - boba.FRESH['pearls'][0] - 5
        n = boba.stock(j.c)['pearls']
        self.assertGreater(n, 0)
        j.act('tea_toss', item='pearls')
        self.assertEqual(boba.stock(j.c)['pearls'], 0)
        self.assertEqual(j.c['life']['waste'][-1]['qty'], n)
        unchanged(self, j, 'tea_toss', item='pearls')

    def test_close_throws_out_tea_and_pearls_but_not_bought_goods(self):
        j = Journey('milk_tea')
        tea = boba.stock(j.c)['milk']
        jelly = boba.stock(j.c)['jelly']
        j.act('end_day', carry_event=True)
        self.assertEqual(boba.held(j.c)['milk'], 0)
        self.assertEqual(boba.held(j.c)['jelly'], jelly)
        rows = [w for w in j.c['life']['waste'] if w['item'] == 'milk']
        self.assertEqual(sum(w['qty'] for w in rows), tea)
        counter = j.c['life']['recap']['counter']
        self.assertGreater(counter['dumped'], 0)
        self.assertTrue(st(j)['night'])
        validate_state(j.state)


class SupplierOrders(unittest.TestCase):
    def test_express_arrives_on_the_shop_clock_not_instantly(self):
        j = Journey('milk_tea')
        cash = j.c['money']
        before = boba.stock(j.c)['lychee']
        r = j.act('tea_order', item='lychee', qty=5, supplier='express', confirm=True)
        cost = round(5 * boba.ING['lychee']['cost'] * boba.SUP_INDEX['express']['factor'])
        self.assertEqual(j.c['money'], cash - cost)
        self.assertEqual(boba.stock(j.c)['lychee'], before)
        o = st(j)['orders'][0]
        self.assertTrue(o['lo'] - o['placed'] >= 30 and o['hi'] - o['placed'] <= 60)
        self.assertIn('hôm nay', r['eta']['eta_label'])
        self.assertIn('phút', r['eta']['left_label'])
        self.assertNotIn('nhịp', json.dumps(r, ensure_ascii=False))
        wait_until(j, o['lo'] - 5)
        if boba.now_abs(j.c) < o['at']:
            self.assertEqual(boba.stock(j.c)['lychee'], before)
        wait_until(j, o['at'])
        j.act('tea_wait')
        self.assertEqual(boba.stock(j.c)['lychee'], before + 5)
        self.assertEqual(st(j)['orders'], [])
        validate_state(j.state)

    def test_market_before_cutoff_is_waiting_at_the_door_tomorrow(self):
        j = Journey('milk_tea')
        j.act('tea_order', item='peach', qty=10, supplier='market', confirm=True)
        o = st(j)['orders'][0]
        self.assertEqual(o['lo'] // boba.DAY_MIN, j.c['day'] + 1)
        self.assertLess(o['hi'] % boba.DAY_MIN, boba.OPEN_MIN)
        self.assertIn('Sáng mai', pub(j)['orders'][0]['eta_label'])
        have = boba.held(j.c)['peach']
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertEqual(boba.held(j.c)['peach'], have + 10 if o['late'] is None else have)

    def test_market_after_cutoff_is_the_day_after_tomorrow(self):
        j = Journey('milk_tea')
        j.act('end_day', carry_event=True)  # evening, after 17:00
        j.act('tea_order', item='peach', qty=5, supplier='market', confirm=True)
        o = st(j)['orders'][0]
        self.assertEqual(o['lo'] // boba.DAY_MIN, j.c['day'] + 1)  # c['day'] is already tomorrow

    def test_supplier_windows_and_rules(self):
        j = Journey('milk_tea')
        view = {s['id']: s for s in pub(j)['suppliers']}
        self.assertEqual(view['express']['window'], '30–60 phút')
        self.assertIn('Sáng mai', view['market']['window'])
        self.assertEqual(view['factory']['window'], '2–3 ngày')
        self.assertIn('nay', view['partner']['quote']['label'])  # "Trưa nay ~13:30"
        text = json.dumps(pub(j)['suppliers'], ensure_ascii=False)
        self.assertNotIn('nhịp', text)
        unchanged(self, j, 'tea_order', item='lychee', qty=5, supplier='express')  # confirm
        unchanged(self, j, 'tea_order', item='pudding', qty=5, supplier='market', confirm=True)  # market has no pudding (and it is locked)
        unchanged(self, j, 'tea_order', item='popping', qty=5, supplier='market', confirm=True)  # market does not sell it
        unchanged(self, j, 'tea_order', item='pearls', qty=5, supplier='express', confirm=True)  # cooked at the counter
        unchanged(self, j, 'tea_order', item='lychee', qty=0, supplier='express', confirm=True)
        unchanged(self, j, 'tea_order', item='lychee', qty=5, supplier='nobody', confirm=True)
        j.act('tea_order', item='cup_L', qty=2, supplier='factory', confirm=True)
        o = st(j)['orders'][-1]
        self.assertIn(o['lo'] // boba.DAY_MIN - j.c['day'], (2, 3))

    def test_shelf_limit_counts_goods_on_the_way(self):
        j = Journey('milk_tea')
        room = 60 - boba.held(j.c)['jelly']
        j.act('tea_order', item='jelly', qty=min(20, room), supplier='partner', confirm=True)
        room -= min(20, room)
        while room >= 20:
            j.act('tea_order', item='jelly', qty=20, supplier='partner', confirm=True)
            room -= 20
        unchanged(self, j, 'tea_order', item='jelly', qty=room + 1, supplier='partner', confirm=True)

    def test_late_delivery_keeps_the_promise_hidden_until_due(self):
        j = Journey('milk_tea')
        j.act('tea_order', item='lychee', qty=5, supplier='express', confirm=True)
        o = st(j)['orders'][0]
        text = json.dumps(pub(j)['orders'], ensure_ascii=False)
        self.assertNotIn('"at"', text)
        self.assertNotIn('"late"', text)
        o['late'] = 'Tài xế phải vòng tránh đoạn đường ngập.'
        o['at'] = o['hi'] + 90
        validate_state(j.state)
        self.assertIsNone(pub(j)['orders'][0]['late_note'])
        wait_until(j, o['hi'] + 1)
        self.assertIn('vòng tránh', pub(j)['orders'][0]['late_note'])
        wait_until(j, o['at'])
        j.act('tea_wait')
        self.assertEqual(st(j)['orders'], [])

    def test_tampered_orders_are_rejected(self):
        j = Journey('milk_tea')
        j.act('tea_order', item='lychee', qty=5, supplier='express', confirm=True)
        for key, bad in (('at', 0), ('supplier', 'thief'), ('qty', 99), ('item', 'gold'), ('cost', -1)):
            s = copy.deepcopy(j.state)
            s['careers']['milk_tea']['ext']['data']['boba']['orders'][0][key] = bad
            with self.assertRaises(GameError, msg=key):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['milk_tea']['ext']['data']['boba']['orders'][0]['secret'] = 1
        with self.assertRaises(GameError):
            validate_state(s)

    def test_cups_are_ordered_too(self):
        j = Journey('milk_tea')
        r = j.act('tea_cups', size='M', confirm=True)
        self.assertEqual(st(j)['orders'][0]['item'], 'cup_M')
        self.assertNotIn('nhịp', r['message'])

    def test_refused_short_box_is_reordered_with_a_real_window(self):
        j = Journey('milk_tea')
        b = st(j)
        b['event'] = dict(id='tea-ev-1-99', kind='short_delivery', day=1, turn=j.c['turn'], stage='open',
                          facts=dict(item='milk', billed=10, got=7, cost=4, _honest=True), task=None, choice=None, result=None, effects=[])
        cash = j.c['money']
        j.act('tea_event', choice='refuse')
        self.assertEqual(j.c['money'], cash - 40)
        self.assertEqual(st(j)['orders'][0]['supplier'], 'partner')
        validate_state(j.state)


class Upkeep(unittest.TestCase):
    def test_sealer_gets_sticky_and_cleaning_takes_a_beat(self):
        j = Journey('milk_tea')
        b = st(j)
        self.assertEqual(boba.seal_zones(b)['good_lo'], boba.SEAL['good_lo'])
        b['sealer_wear'] = boba.SEALER_STICKY
        z = boba.seal_zones(b)
        self.assertGreater(z['good_lo'], boba.SEAL['good_lo'])
        self.assertLess(z['good_hi'], boba.SEAL['good_hi'])
        self.assertEqual(pub(j)['seal'], z)  # the gauge the player sees is the real one
        b['sealer_wear'] = boba.SEALER_DIRTY
        self.assertIn('sealer', [w['id'] for w in pub(j)['warnings']])
        turn = j.c['turn']
        j.act('tea_clean')
        self.assertEqual((st(j)['sealer_wear'], j.c['turn']), (0, turn + 1))
        unchanged(self, j, 'tea_clean')

    def test_each_seal_wears_the_plate_and_dirty_auto_sealer_is_only_ok(self):
        j = Journey('milk_tea')
        b = st(j)
        b['upgrades'].append('sealer')
        b['sealer_wear'] = boba.SEALER_DIRTY
        t = j.task
        j.act('ask', task=t['id'])
        for action, payload in boba.solution(j.get(t['id'])):
            if action == 'tea_serve':
                break
            if action == 'tea_add' and not boba.stock(j.c)[payload['item']]:
                j.act('tea_prepare', item=payload['item'], qty=3, confirm=True)
            r = j.act(action, **payload)
        self.assertEqual(r['seal'], 'ok')
        self.assertEqual(st(j)['sealer_wear'], boba.SEALER_DIRTY + 1)


class Regulars(unittest.TestCase):
    def test_notes_are_learned_by_visits_and_greeting_helps(self):
        j = Journey('milk_tea')
        t = j.task
        self.assertFalse(t.get('walkin'))
        npc = t['npc']
        self.assertEqual(boba.notes_for(st(j), npc), [])
        j.act('ask', task=t['id'])
        unchanged(self, j, 'tea_greet', task=t['id'])  # nothing learned yet
        r = j.solve(t['id'])
        self.assertEqual(r['status'], 'completed')
        notes = boba.notes_for(st(j), npc)
        self.assertEqual(len(notes), 1)
        row = next(x for x in pub(j)['notebook'] if x['npc'] == npc)
        self.assertEqual(row['notes'][0]['id'], boba.NOTES[npc][0][0])
        self.assertEqual(row['next_note'], 3)
        # Second note after the third visit; unlearned notes never leave the server.
        self.assertNotIn(boba.NOTES[npc][1][2], json.dumps(pub(j), ensure_ascii=False))
        st(j)['notebook'][npc]['visits'] = 3
        self.assertEqual(len(boba.notes_for(st(j), npc)), 2)

    def test_greet_once_adds_patience_without_a_beat(self):
        j = Journey('milk_tea')
        t = j.task
        st(j)['notebook'][t['npc']] = dict(usual=copy.deepcopy(t['needs']), visits=1, day=1)
        t['patience'] = 80
        turn = j.c['turn']
        j.act('tea_greet', task=t['id'])
        self.assertEqual((j.get(t['id'])['patience'], j.c['turn']), (88, turn))
        self.assertTrue(j.get(t['id'])['greeted'])
        unchanged(self, j, 'tea_greet', task=t['id'])
        validate_state(j.state)


class Swaps(unittest.TestCase):
    def fixed(self, j, needs):
        t = j.task
        t['changes'] = []
        t['src'] = dict(fixed=needs)
        t['needs'] = boba.derive(t)
        t['quoted_price'] = boba.price(j.c, t['needs'])
        j.act('ask', task=t['id'])
        return t['id']

    def test_out_of_topping_guest_takes_another(self):
        j = Journey('milk_tea')
        tid = self.fixed(j, dict(base='milk', flavor='peach', toppings=['popping'], size='M', sugar=50, ice='normal'))
        unchanged(self, j, 'tea_swap', task=tid, item='popping')  # still in stock
        for l in j.c['life']['pantry']:
            if l['item'] in ('popping', 'peach'):
                l['qty'] = 0
        turn = j.c['turn']
        j.act('tea_swap', task=tid, item='popping')
        j.act('tea_swap', task=tid, item='peach')
        n = j.get(tid)['needs']
        self.assertNotIn('popping', n['toppings'])
        self.assertNotEqual(n['flavor'], 'peach')
        self.assertEqual(j.c['turn'], turn)
        self.assertEqual(j.get(tid)['quoted_price'], boba.price(j.c, n))
        validate_state(j.state)
        self.assertEqual(j.solve(tid)['status'], 'completed')

    def test_out_of_cup_size_is_a_free_upgrade(self):
        j = Journey('milk_tea')
        tid = self.fixed(j, dict(base='milk', flavor=None, toppings=[], size='M', sugar=50, ice='normal'))
        price = j.get(tid)['quoted_price']
        st(j)['cups']['M'] = 0
        j.act('tea_swap', task=tid, item='cup_M')
        t = j.get(tid)
        self.assertEqual(t['needs']['size'], 'L')
        self.assertEqual(t['quoted_price'] - t['discount'], price)
        validate_state(j.state)

    def test_walk_ins_do_not_order_what_the_board_marks_out(self):
        j = Journey('milk_tea')
        for l in j.c['life']['pantry']:
            if l['item'] in ('jelly', 'popping', 'lychee', 'strawberry'):
                l['qty'] = 0
        avoid = boba._avoid(j.c, st(j))
        for x in ('jelly', 'popping', 'lychee', 'strawberry'):
            self.assertIn(x, avoid)
        self.assertNotIn('pearls', avoid)  # cooked at the counter, never off the menu


class ForecastAndCare(unittest.TestCase):
    def test_tomorrow_is_tomorrows_real_modifier(self):
        j = Journey('milk_tea')
        f = boba.forecast(j.c)
        self.assertEqual(f['id'], boba.roll_mod(j.c['day'] + 1))
        j.act('end_day', carry_event=True)
        self.assertEqual(boba.forecast(j.c)['id'], f['id'])
        self.assertEqual(j.c['life']['recap']['counter']['tomorrow']['title'], f['title'])
        j.act('start_day')
        self.assertEqual(st(j)['mod'], f['id'])

    def test_care_list_names_what_needs_doing(self):
        j = Journey('milk_tea')
        for l in j.c['life']['pantry']:
            if l['item'] == 'pearls':
                l['qty'] = 0
        rows = {r['id']: r for r in pub(j)['care']}
        self.assertEqual(rows['pot-pearls']['tone'], 'danger')
        self.assertIn('sealer', rows)
        self.assertNotIn('tomorrow', rows)  # the forecast shows from the afternoon
        wait_until(j, j.c['day'] * boba.DAY_MIN + 14 * 60)
        self.assertIn('tomorrow', {r['id'] for r in pub(j)['care']})


class OldSaves(unittest.TestCase):
    def test_counter_state_from_before_the_care_loop_loads_and_plays(self):
        j = Journey('milk_tea')
        old = copy.deepcopy(j.state)
        b = old['careers']['milk_tea']['ext']['data']['boba']
        for k in ('span', 'orders', 'order_seq', 'sealer_wear', 'cleaned', 'night'):
            b.pop(k, None)
        for l in old['careers']['milk_tea']['life']['pantry']:
            l.pop('made', None)
        for t in old['careers']['milk_tea']['tasks']:
            t['cup'].pop('tired', None)
            t.pop('greeted', None)
        new = migrate_state(old)
        validate_state(new)
        j.state = new
        self.assertTrue(all(boba.band(j.c, l) == 'fresh' for l in j.c['life']['pantry']))
        j.act('tea_order', item='lychee', qty=5, supplier='express', confirm=True)
        self.assertEqual(j.solve()['status'], 'completed')
        validate_state(j.state)

    def test_strict_validation_of_new_fields(self):
        j = Journey('milk_tea')
        bad = copy.deepcopy(j.state)
        lot = next(l for l in bad['careers']['milk_tea']['life']['pantry'] if l['item'] == 'jelly')
        lot['made'] = 500  # only brewed tea and cooked pearls carry a time
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(j.state)
        bad['careers']['milk_tea']['tasks'][0]['cup']['tired'] = ['pearls']  # not in the cup
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(j.state)
        bad['careers']['milk_tea']['ext']['data']['boba']['sealer_wear'] = -1
        with self.assertRaises(GameError):
            validate_state(bad)


if __name__ == '__main__':
    unittest.main()
