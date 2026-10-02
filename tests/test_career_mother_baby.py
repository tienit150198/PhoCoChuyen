"""Tiệm Mây Nhỏ care loop (game/careers/mother_baby.py): regular families whose
babies grow, subscription pickups, the diaper & formula shelf with lots, recalls
and expiry, the baby-shower registry and honest advice."""
import copy
import json
import unittest

from game import giftshop as gs
from game.careers import mother_baby as mb
from game.engine import GameError, apply_action, public_state, validate_state
from tests.helpers import Journey

# giftshop.py ends with `_care.install(globals())`; installing again is a no-op.
mb.install(vars(gs))


def journey(days=1):
    """A shop that has reached day 1 + days (the corner opens on day 2)."""
    j = Journey('mother_baby')
    for _ in range(days):
        j.act('end_day', carry_event=True)
        j.act('start_day')
    return j


def cr(j):
    return mb.raw(j.c)


def pub(j):
    return public_state(j.state)['careers']['mother_baby']['data']['gift']['care']


def to_day(j, day):
    while j.c['day'] < day:
        j.act('end_day', carry_event=True)
        j.act('start_day')


def unchanged(test, j, action, **payload):
    before = copy.deepcopy(j.state)
    with test.assertRaises(GameError):
        j.act(action, **payload)
    test.assertEqual(j.state, before)


def fam_pub(j, fid):
    return next(f for f in pub(j)['fam'] if f['id'] == fid)


class Opening(unittest.TestCase):
    def test_day_one_has_no_corner_then_it_opens(self):
        j = Journey('mother_baby')
        self.assertFalse(pub(j)['ready'])
        self.assertIsNone(cr(j))
        to_day(j, 2)
        self.assertTrue(pub(j)['ready'])
        self.assertEqual(cr(j)['start'], 2)
        self.assertEqual(cr(j)['day'], 2)

    def test_install_is_idempotent_and_keeps_old_commands(self):
        mb.install(vars(gs))
        j = journey(2)
        t = next(t for t in j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled'))
        self.assertEqual(j.solve(t['id'])['status'], 'completed')
        validate_state(j.state)

    def test_old_save_at_a_later_day_starts_its_own_timeline(self):
        j = journey(1)
        c = j.c
        c['ext']['data']['gift'].pop('care')
        validate_state(j.state)
        self.assertFalse(pub(j)['ready'])
        c['day'] = 20
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertEqual(cr(j)['start'], 21)
        hoa = fam_pub(j, 'hoa')
        self.assertEqual(hoa['weeks'], 3)
        validate_state(json.loads(json.dumps(j.state)))

    def test_old_save_mid_shift_waits_for_the_next_day(self):
        j = journey(2)
        j.c['ext']['data']['gift'].pop('care')
        validate_state(j.state)
        unchanged(self, j, 'gift_care_order', item='S', qty=1, confirm=True)
        self.assertEqual(pub(j)['opens'], j.c['day'] + 1)

    def test_closed_shop_refuses_care_actions(self):
        j = journey(2)
        j.act('end_day', carry_event=True)
        unchanged(self, j, 'gift_care_ask', family='hoa')


class Growth(unittest.TestCase):
    def test_sizes_and_stage_follow_weight_and_weeks(self):
        self.assertEqual([mb.size_for(k) for k in (31, 49, 50, 69, 70, 99, 100)], ['NB', 'NB', 'S', 'S', 'M', 'M', 'L'])
        self.assertEqual((mb.stage_for(25), mb.stage_for(26)), (1, 2))
        f = mb.FAM['hoa']
        kg = [mb.weight(f, w) for w in range(0, 30)]
        self.assertEqual(kg, sorted(kg))

    def test_babies_outgrow_their_size_during_play(self):
        cr0 = mb.fresh(2)
        changes = {}
        for f in mb.FAMILIES:
            sizes = [mb.size_for(mb.weight(f, mb.weeks(cr0, f, d))) for d in range(2 + f['first'], 2 + 16)]
            changes[f['id']] = len(set(sizes))
        self.assertTrue(all(n >= 2 for fid, n in changes.items() if fid != 'ly'), changes)
        dieu = mb.FAM['dieu']
        self.assertEqual(mb.product_for(dieu, mb.weeks(cr0, dieu, 4)), 'mx1')
        self.assertEqual(mb.product_for(dieu, mb.weeks(cr0, dieu, 8)), 'mx2')

    def test_expecting_family_is_born_later(self):
        j = journey(1)
        ly = fam_pub(j, 'ly')
        self.assertEqual(ly['status'], 'expecting')
        self.assertIsNone(ly['weeks'])
        to_day(j, 2 + 7)
        self.assertEqual(fam_pub(j, 'ly')['weeks'], 0)


class Pickups(unittest.TestCase):
    def setUp(self):
        self.j = journey(2)          # day 3 = start + 1: Chị Hoa and Anh Tuấn are due
        self.day = self.j.c['day']

    def test_perfect_pickup(self):
        j = self.j
        self.assertTrue(fam_pub(j, 'tuan')['due'])
        p = mb.best_hand(j.c, 'tuan')
        money = j.c['money']
        lot = lambda: next(x for x in cr(j)['lots'] if x['id'] == p['lot'])
        qty = lot()['qty']
        size_before = cr(j)['diapers'][p['size']]
        r = j.act('gift_care_hand', **p)
        self.assertTrue(r['celebrate'])
        fam = cr(j)['fam']['tuan']
        self.assertGreaterEqual(fam['trust'], 1)
        self.assertEqual(fam['next'], self.day + 5)
        self.assertEqual(fam['visits'], 1)
        self.assertEqual(lot()['qty'], qty - 1)
        self.assertEqual(cr(j)['diapers'][p['size']], size_before - 1)
        self.assertGreaterEqual(j.c['money'], money + mb.DIAPER['price'] + mb.FORMULA['price'])
        self.assertFalse(fam_pub(j, 'tuan')['due'])
        unchanged(self, j, 'gift_care_hand', **p)   # once per cycle

    def test_fifo_lot_expires_and_must_be_pulled(self):
        j = self.j
        self.assertEqual(mb.best_hand(j.c, 'tuan')['lot'], 'SM1-02')   # the earliest safe lot first
        to_day(j, 5)
        lot = next(x for x in cr(j)['lots'] if x['id'] == 'SM1-02')
        self.assertTrue(mb.expired(lot, j.c['day']))
        self.assertTrue(next(x for x in pub(j)['lots'] if x['id'] == 'SM1-02')['expired'])
        waste = cr(j)['waste']
        j.act('gift_care_pull', lot='SM1-02')
        self.assertEqual(cr(j)['waste'], waste + 2 * mb.FORMULA['cost'])
        self.assertFalse(any(x['id'] == 'SM1-02' for x in cr(j)['lots']))

    def test_wrong_size_costs_trust_and_a_review(self):
        j = self.j
        p = mb.best_hand(j.c, 'tuan')
        p['size'] = 'NB' if p['size'] != 'NB' else 'S'
        feed = len(j.c['feed'])
        r = j.act('gift_care_hand', **p)
        self.assertFalse(r['correct'])
        self.assertEqual(j.c['feed'][0]['stars'], 3)
        self.assertEqual(j.c['feed'][0]['author'], 'Anh Tuấn')
        self.assertGreater(len(j.c['feed']), feed)
        self.assertEqual(cr(j)['fam']['tuan']['trust'], 0)

    def test_expired_can_is_refunded_and_hurts(self):
        j = self.j
        lot = next(x for x in cr(j)['lots'] if x['id'] == 'SM1-02')
        lot['exp'] = j.c['day'] - 1
        validate_state(j.state)
        p = mb.best_hand(j.c, 'tuan')
        p['lot'] = 'SM1-02'
        money = j.c['money']
        r = j.act('gift_care_hand', **p)
        self.assertFalse(r['correct'])
        self.assertEqual(j.c['feed'][0]['stars'], 1)
        self.assertEqual(j.c['money'], money + mb.DIAPER['price'])   # the can was refunded
        self.assertEqual(j.c['metrics'].get('safety_miss'), 1)
        self.assertEqual(cr(j)['today']['safety'], 1)

    def test_no_fitting_can_hands_diapers_only(self):
        j = self.j
        p = mb.best_hand(j.c, 'tuan')
        p['lot'] = None
        r = j.act('gift_care_hand', **p)
        self.assertFalse(r['correct'])
        self.assertIn('thiếu sữa', r['message'])

    def test_breastfed_baby_takes_no_formula(self):
        j = self.j
        p = mb.best_hand(j.c, 'hoa')
        self.assertIsNone(p['lot'])
        unchanged(self, j, 'gift_care_hand', **dict(p, lot='MX1-01'))

    def test_ask_reveals_weight_once_and_trust_volunteers_it(self):
        j = self.j
        self.assertIsNone(fam_pub(j, 'hoa')['kg'])
        r = j.act('gift_care_ask', family='hoa')
        self.assertIn('kg', r['message'])
        self.assertEqual(fam_pub(j, 'hoa')['kg'], mb.weight(mb.FAM['hoa'], 4))
        unchanged(self, j, 'gift_care_ask', family='hoa')
        cr(j)['fam']['tuan']['trust'] = mb.TELLS_WEIGHT
        self.assertIsNotNone(fam_pub(j, 'tuan')['kg'])
        unchanged(self, j, 'gift_care_ask', family='tuan')

    def test_missed_window_moves_on_with_less_trust(self):
        j = self.j
        cr(j)['fam']['hoa']['trust'] = 2
        to_day(j, self.day + 2)
        fam = cr(j)['fam']['hoa']
        self.assertEqual(fam['next'], self.day + 4)
        self.assertEqual(fam['missed'], 1)
        self.assertEqual(fam['trust'], 1)

    def test_late_day_still_counts(self):
        j = self.j
        to_day(j, self.day + 1)
        self.assertTrue(fam_pub(j, 'hoa')['late'])
        j.act('gift_care_hand', **mb.best_hand(j.c, 'hoa'))
        self.assertEqual(cr(j)['fam']['hoa']['missed'], 0)

    def test_validation_errors_leave_state_unchanged(self):
        j = self.j
        good = mb.best_hand(j.c, 'tuan')
        for bad in (dict(good, family='nobody'), dict(good, family='dieu'), dict(good, size='XL'), dict(good, size=None),
                    dict(good, lot='MX9-01'), dict(good, lot=5), dict(good, confirm=False), dict(good, advice='zz'),
                    {k: v for k, v in good.items() if k != 'confirm'}):
            unchanged(self, j, 'gift_care_hand', **bad)
        unchanged(self, j, 'gift_care_nope')
        unchanged(self, j, 'gift_care_ask', family=['hoa'])
        cr(j)['diapers'][good['size']] = 0
        unchanged(self, j, 'gift_care_hand', **good)


class Advice(unittest.TestCase):
    def setUp(self):
        self.j = journey(2)
        cr(self.j)['fam']['tuan']['q'] = 'gainer'
        validate_state(self.j.state)

    def test_question_is_public_without_the_answer(self):
        q = fam_pub(self.j, 'tuan')['question']
        self.assertEqual({o['id'] for o in q['options']}, {'a', 'b'})
        self.assertTrue(all(set(o) == {'id', 'label'} for o in q['options']))
        text = json.dumps(pub(self.j), ensure_ascii=False)
        for secret in [o['regret'] for q in mb.QUESTIONS.values() for o in q['options'] if 'regret' in o] + ['"kind"', '"gain"', '"sell"']:
            self.assertNotIn(secret, text)

    def test_answer_is_required(self):
        p = mb.best_hand(self.j.c, 'tuan')
        unchanged(self, self.j, 'gift_care_hand', **dict(p, advice=None))

    def test_honest_answer_builds_trust(self):
        j = self.j
        p = mb.best_hand(j.c, 'tuan')
        j.act('gift_care_hand', **p)
        self.assertEqual(cr(j)['fam']['tuan']['trust'], 2)
        self.assertEqual(cr(j)['fam']['tuan']['asked'], ['gainer'])
        self.assertEqual(cr(j)['today']['honest'], 1)

    def test_upsell_pays_now_and_regrets_tomorrow(self):
        j = self.j
        p = mb.best_hand(j.c, 'tuan')
        p['advice'] = next(o['id'] for o in mb.QUESTIONS['gainer']['options'] if o['kind'] == 'upsell')
        money = j.c['money']
        j.act('gift_care_hand', **p)
        self.assertEqual(j.c['money'], money + mb.DIAPER['price'] + mb.FORMULA['price'] + 50)
        self.assertEqual(cr(j)['fam']['tuan']['trust'], 0)
        feed = len(j.c['feed'])
        to_day(j, j.c['day'] + 1)
        regret = [f for f in j.c['feed'] if f.get('source', '').endswith('-regret')]
        self.assertEqual(len(regret), 1)
        self.assertEqual(regret[0]['stars'], 2)
        self.assertGreater(len(j.c['feed']), feed)

    def test_honest_answer_can_still_sell_the_one_thing_needed(self):
        j = self.j
        cr(j)['fam']['tuan']['q'] = 'teeth'
        p = mb.best_hand(j.c, 'tuan')
        stock = j.c['stock']['teether']
        j.act('gift_care_hand', **p)
        self.assertEqual(j.c['stock']['teether'], stock - 1)

    def test_trust_three_tips(self):
        j = self.j
        cr(j)['fam']['tuan']['trust'] = mb.TIPS_FROM
        r = j.act('gift_care_hand', **mb.best_hand(j.c, 'tuan'))
        self.assertIn('bồi dưỡng', r['message'])

    def test_questions_roll_deterministically(self):
        a, b = journey(2), journey(2)
        self.assertEqual(cr(a)['fam'], cr(b)['fam'])


class Shelf(unittest.TestCase):
    def test_order_arrives_next_morning(self):
        j = journey(1)
        money = j.c['money']
        j.act('gift_care_order', item='L', qty=2, confirm=True)
        self.assertEqual(j.c['money'], money - 2 * mb.DIAPER['cost'])
        self.assertEqual(cr(j)['diapers']['L'], 1)
        self.assertEqual(pub(j)['orders'][0]['qty'], 2)
        j.act('gift_care_order', item='mx2', qty=1, confirm=True)
        to_day(j, 3)
        self.assertEqual(cr(j)['diapers']['L'], 3)
        new = [x for x in cr(j)['lots'] if x['got'] == 3]
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]['p'], 'mx2')
        self.assertGreater(new[0]['exp'], 3 + 7)
        self.assertEqual(cr(j)['orders'], [])

    def test_order_limits(self):
        j = journey(1)
        for bad in (dict(item='XL', qty=1, confirm=True), dict(item='L', qty=0, confirm=True), dict(item='L', qty=5, confirm=True),
                    dict(item='L', qty=1), dict(item='L', qty='2', confirm=True), dict(item=None, qty=1, confirm=True)):
            unchanged(self, j, 'gift_care_order', **bad)
        cr(j)['diapers']['L'] = mb.DIAPER['cap']
        unchanged(self, j, 'gift_care_order', item='L', qty=1, confirm=True)
        j.c['money'] = 10
        unchanged(self, j, 'gift_care_order', item='NB', qty=1, confirm=True)

    def test_recall_notice_and_pull(self):
        j = journey(1)
        to_day(j, 2 + 4)
        notices = pub(j)['notices']
        self.assertEqual(len(notices), 1)
        lid = notices[0]['lot']
        self.assertTrue(next(x for x in pub(j)['lots'] if x['id'] == lid)['recalled'])
        good = next(x for x in cr(j)['lots'] if mb.safe_lot(x, j.c['day']))
        unchanged(self, j, 'gift_care_pull', lot=good['id'])
        unchanged(self, j, 'gift_care_pull', lot='SM9-99')
        qty = next(x for x in cr(j)['lots'] if x['id'] == lid)['qty']
        money = j.c['money']
        j.act('gift_care_pull', lot=lid)
        self.assertEqual(j.c['money'], money + qty * mb.FORMULA['cost'])

    def test_recalls_are_deterministic(self):
        a, b = journey(1), journey(1)
        to_day(a, 6)
        to_day(b, 6)
        self.assertEqual(cr(a)['notices'], cr(b)['notices'])


class Registry(unittest.TestCase):
    def setUp(self):
        self.j = journey(1)
        to_day(self.j, 2 + 2)
        for k in ('towel', 'socks', 'bottle', 'blanket', 'bear', 'bunny'):
            self.j.c['stock'][k] = 10
        validate_state(self.j.state)

    def aside_all(self):
        j = self.j
        for lid, item, qty, n in mb.REGISTRY['lines']:
            if j.c['day'] >= 2 + n and not cr(j)['reg']['lines'][lid]['aside']:
                j.act('gift_care_aside', line=lid)

    def test_open_and_swap_only_unsafe_lines(self):
        j = self.j
        self.assertEqual(pub(j)['reg']['state'], 'open')
        unchanged(self, j, 'gift_care_swap', line='r1', item='bunny')     # towels are 0+
        unchanged(self, j, 'gift_care_swap', line='r2', item='blocks')    # 3+ is not a fix
        unchanged(self, j, 'gift_care_swap', line='r2', item='card')
        r = j.act('gift_care_swap', line='r2', item='bunny')
        self.assertTrue(r['celebrate'])
        self.assertEqual(cr(j)['fam']['ly']['trust'], 1)
        unchanged(self, j, 'gift_care_swap', line='r2', item='book')

    def test_public_fits_mirrors_the_swap_rule(self):
        # The client answers a swap on a line that already suits a newborn itself (no error round trip):
        # `fits` must say exactly which lines gift_care_swap refuses as "không cần đổi".
        j = self.j
        lines = pub(j)['reg']['lines']
        self.assertEqual({l['id']: l['fits'] for l in lines}, {lid: gs.suits(item, 0) for lid, item, qty, n in mb.REGISTRY['lines']})
        self.assertEqual([l['id'] for l in lines if not l['fits']], ['r2'])
        for l in lines:
            target = pub(j)['reg']['swaps'][l['orig']][0]
            if l['fits']:
                before = copy.deepcopy(j.state)
                with self.assertRaises(GameError) as e:
                    j.act('gift_care_swap', line=l['id'], item=target)
                self.assertIn('không cần đổi', e.exception.message)
                self.assertEqual(j.state, before)
            else:
                self.assertTrue(j.act('gift_care_swap', line=l['id'], item=target)['celebrate'])

    def test_aside_needs_a_buyer_and_stock(self):
        j = self.j
        unchanged(self, j, 'gift_care_aside', line='r1')                 # bought tomorrow
        to_day(j, 2 + 3)
        j.c['stock']['towel'] = 1
        unchanged(self, j, 'gift_care_aside', line='r1')
        j.c['stock']['towel'] = 5
        money = j.c['money']
        j.act('gift_care_aside', line='r1')
        self.assertEqual(j.c['stock']['towel'], 3)
        self.assertEqual(j.c['money'], money + 2 * 35)
        unchanged(self, j, 'gift_care_aside', line='r1')

    def test_shower_success_after_swap(self):
        j = self.j
        j.act('gift_care_swap', line='r2', item='bunny')
        to_day(j, 2 + 5)
        self.aside_all()
        r = j.act('gift_care_shower', confirm=True)
        self.assertTrue(r['celebrate'])
        self.assertEqual(pub(j)['reg']['state'], 'done')
        self.assertEqual(j.c['feed'][0]['stars'], 5)
        self.assertEqual(cr(j)['fam']['ly']['trust'], 2)

    def test_shower_with_unsafe_item_is_noticed(self):
        j = self.j
        to_day(j, 2 + 5)
        self.aside_all()
        j.act('gift_care_shower', confirm=True)
        self.assertEqual(j.c['feed'][0]['stars'], 3)

    def test_shower_too_early_or_empty(self):
        j = self.j
        unchanged(self, j, 'gift_care_shower', confirm=True)
        to_day(j, 2 + 5)
        unchanged(self, j, 'gift_care_shower', confirm=True)             # nothing set aside yet

    def test_partial_box_costs_trust(self):
        j = self.j
        to_day(j, 2 + 5)
        j.act('gift_care_aside', line='r1')
        r = j.act('gift_care_shower', confirm=True)
        self.assertIn('thiếu', r['message'])
        self.assertEqual(j.c['feed'][0]['stars'], 3)

    def test_missed_shower_refunds_friends(self):
        j = self.j
        to_day(j, 2 + 3)
        j.act('gift_care_aside', line='r1')
        money = j.c['money']
        stock = j.c['stock']['towel']
        to_day(j, 2 + 7)
        self.assertEqual(cr(j)['reg']['state'], 'failed')
        self.assertEqual(j.c['stock']['towel'], stock + 2)
        self.assertEqual(j.c['feed'][0]['stars'] if j.c['feed'][0]['source'] == 'care-reg' else
                         next(f for f in j.c['feed'] if f['source'] == 'care-reg')['stars'], 1)
        self.assertLess(j.c['money'] - money, 1000)


class Saves(unittest.TestCase):
    def test_round_trip_and_tampering(self):
        j = journey(3)
        j.act('gift_care_order', item='S', qty=1, confirm=True)
        state = json.loads(json.dumps(j.state))
        validate_state(state)
        care = lambda s: s['careers']['mother_baby']['ext']['data']['gift']['care']
        tampers = [
            lambda c: c['fam']['hoa'].update(trust=9),
            lambda c: c['fam'].update(zed=dict(c['fam']['hoa'])),
            lambda c: c['fam']['hoa'].update(size='XXL'),
            lambda c: c['fam']['hoa'].update(prod='mx1'),                    # Na is breastfed
            lambda c: c['fam']['tuan'].update(q='nope'),
            lambda c: c['fam']['tuan'].update(asked=['teeth', 'teeth']),
            lambda c: c['diapers'].update(NB=99),
            lambda c: c['diapers'].pop('L'),
            lambda c: c['lots'][0].update(id='XX1-01'),
            lambda c: c['lots'][0].update(p='sm2'),
            lambda c: c['lots'][0].update(qty=-1),
            lambda c: c['lots'].append(dict(c['lots'][0])),
            lambda c: c['orders'][0].update(qty=40),
            lambda c: c['reg']['lines']['r2'].update(swap='blocks'),
            lambda c: c['reg'].update(state='maybe'),
            lambda c: c['today'].update(pickups=-3),
            lambda c: c.update(v=7),
            lambda c: c.pop('lots'),
        ]
        for i, tamper in enumerate(tampers):
            bad = copy.deepcopy(state)
            tamper(care(bad))
            with self.assertRaises(GameError, msg=i):
                validate_state(bad)

    def test_hidden_rolls_never_leave_the_server(self):
        j = journey(2)
        data = public_state(j.state)['careers']['mother_baby']['data']
        care = data['gift']['care']
        self.assertTrue(care['ready'])
        self.assertTrue(all(set(f) >= {'id', 'trust', 'due'} and 'q' not in f and 'asked' not in f for f in care['fam']))
        self.assertNotIn('b10', json.dumps(data, ensure_ascii=False))

    def test_a_week_of_play_stays_valid(self):
        j = journey(1)
        for _ in range(9):
            day = j.c['day']
            for f in mb.FAMILIES:
                if mb.due(cr(j), f['id'], day):
                    p = mb.best_hand(j.c, f['id'])
                    if cr(j)['diapers'][p['size']] and (p['lot'] or not f['milk']):
                        j.act('gift_care_hand', **p)
            for lot in list(cr(j)['lots']):
                if not mb.safe_lot(lot, day):
                    j.act('gift_care_pull', lot=lot['id'])
            r = j.act('end_day', carry_event=True)
            self.assertIsInstance(r['summary']['experiences']['counter'], dict)
            j.act('start_day')
        validate_state(json.loads(json.dumps(j.state)))
        self.assertGreater(j.c['metrics'].get('care_pickups', 0), 4)


if __name__ == '__main__':
    unittest.main()
