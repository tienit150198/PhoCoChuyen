"""Gift shop from day 2 (game/giftshop.py): age labels, safety advice, first-time
parents, returns without receipts, baby-shower orders and counter surprises."""
import copy
import json
import unittest

from game import giftshop as gs
from game.content import PRODUCT_INDEX, make_task
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from game import operations as ops
from tests.helpers import Journey


def find(kind, pred=lambda f: True, start=2):
    for day in range(start, 200):
        for slot in range(12):
            f = gs.make_fields(day, slot)
            if f['gift_kind'] == kind and pred(f):
                return day, slot
    raise AssertionError('no fixture for ' + kind)


def unchanged(test, j, action, **payload):
    before = copy.deepcopy(j.state)
    with test.assertRaises(GameError):
        j.act(action, **payload)
    test.assertEqual(j.state, before)


def gift_state(j):
    return j.c['ext']['data'].setdefault('gift', gs.fresh())


def force_event(j, kind, facts):
    b = gift_state(j)
    b['event'] = dict(id=f'gift-ev-{j.c["day"]}-9', kind=kind, day=j.c['day'], turn=j.c['turn'], stage='open', facts=facts,
                      task=facts.get('task'), choice=None, result=None, effects=[], good=False)
    validate_state(j.state)


def pub_task(j):
    return next(t for t in public_state(j.state)['careers']['mother_baby']['tasks'] if t['id'] == j.task['id'])


class Schedule(unittest.TestCase):
    def test_day_one_keeps_classic_orders(self):
        j = Journey()
        self.assertTrue(all(not t.get('gen') for t in j.c['tasks']))

    def test_first_days_introduce_each_kind(self):
        kinds = {(d, s): gs.make_fields(d, s)['gift_kind'] for d, s in [(2, 0), (2, 1), (3, 0), (3, 1), (4, 0)]}
        self.assertEqual(list(kinds.values()), ['occasion', 'safety', 'kit', 'return', 'bulk'])

    def test_orders_are_deterministic_and_validated(self):
        self.assertEqual(gs.make_fields(5, 3), gs.make_fields(5, 3))
        j = Journey('mother_baby', slot=1, day=2)
        bad = copy.deepcopy(j.state)
        bad['careers']['mother_baby']['tasks'][0]['gift']['age'] = 40
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_old_day_two_order_still_loads(self):
        j = Journey('mother_baby', slot=0, day=2)
        old = copy.deepcopy(j.state)
        c = old['careers']['mother_baby']
        c['tasks'] = [make_task('mother_baby', 2, 0, 1, True)]
        c['active_task'] = c['tasks'][0]['id']
        for k in ('rattle', 'teether', 'bottle', 'bib', 'socks', 'book', 'blanket', 'lixi'):
            c['stock'].pop(k)
        new = migrate_state(old)
        validate_state(new)
        self.assertEqual(new['careers']['mother_baby']['stock']['rattle'], 4)
        s, _ = apply_action(new, 'mother_baby', 'ask', {})
        validate_state(s)

    def test_modifiers(self):
        self.assertEqual(gs.roll_mod(1), 'normal')
        self.assertTrue({'tet', 'fair', 'weekend'} <= {gs.roll_mod(d) for d in range(2, 60)})
        for day in range(2, 40):
            for slot in range(6):
                f = gs.make_fields(day, slot)
                self.assertIn(f['gift']['mod'], [m['id'] for m in gs.MODS])
                if f['gift_kind'] in ('simple', 'safety'):
                    self.assertGreaterEqual(f['needs']['budget'], PRODUCT_INDEX[f['needs']['product']]['price'] * f['needs']['qty'])


class Occasion(unittest.TestCase):
    def test_card_must_match_the_occasion(self):
        day, slot = find('occasion', lambda f: f['gift']['pick'] == 'named')
        j = Journey('mother_baby', slot=slot, day=day)
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.task['needs']
        for _ in range(n['qty']):
            j.act('shop_pick', task=tid, item=n['product'])
        right = j.task['gift']['tag']
        wrong = next(x for x in gs.TAG_IDS if x != right)
        j.act('shop_pack', task=tid, paper=n['paper'], ribbon='gold', card='Chúc bé', tag=wrong)
        self.assertEqual(j.task['mistakes'], 1)
        # The check no longer refuses a wrong basket (it can be handed over, the customer
        # reacts at the counter); it must not record or reveal anything before the hand-off.
        j.act('shop_check', task=tid)
        self.assertFalse(j.get(tid).get('slips'))
        self.assertNotIn('slips', pub_task(j))
        unchanged(self, j, 'shop_pack', task=tid, paper=n['paper'], ribbon='gold', card='x', tag='party')
        j.act('shop_pack', task=tid, paper=n['paper'], ribbon='gold', card='Chúc bé', tag=right)
        j.act('shop_check', task=tid)
        j.act('shop_deliver', task=tid)
        self.assertEqual(j.task['status'] if j.c['active_task'] else j.get(tid)['status'], 'completed')

    def test_open_choice_accepts_any_fitting_gift(self):
        day, slot = find('occasion', lambda f: f['gift']['pick'] == 'open' and f['gift']['age'] == 1)
        j = Journey('mother_baby', slot=slot, day=day)
        tid = j.task['id']
        j.act('ask', task=tid)
        self.assertIsNotNone(pub_task(j)['gift']['request'])
        j.act('shop_pick', task=tid, item='blocks')  # 3+ for a one-month baby
        self.assertEqual(j.task['mistakes'], 1)
        # The check no longer refuses a wrong basket (it can be handed over, the customer
        # reacts at the counter); it must not record or reveal anything before the hand-off.
        j.act('shop_check', task=tid)
        self.assertFalse(j.get(tid).get('slips'))
        self.assertNotIn('slips', pub_task(j))
        j.act('basket_remove', task=tid, item='blocks')
        opt = next(k for k in j.task['gift']['options'] if PRODUCT_INDEX[k]['price'] <= j.task['needs']['budget'])
        j.act('shop_pick', task=tid, item=opt)
        j.solve(tid)
        self.assertEqual(j.get(tid)['status'], 'completed')


    def test_open_choice_without_age_names_the_ideas(self):
        day, slot = find('occasion', lambda f: f['gift']['pick'] == 'open' and f['gift']['age'] is None)
        j = Journey('mother_baby', slot=slot, day=day)
        j.act('ask', task=j.task['id'])
        text = pub_task(j)['gift']['request']
        for k in j.task['gift']['options']:
            self.assertIn(PRODUCT_INDEX[k]['name'][1:], text)


class Safety(unittest.TestCase):
    def setUp(self):
        self.j = Journey('mother_baby', slot=1, day=2)
        self.tid = self.j.task['id']
        self.j.act('ask', task=self.tid)

    def test_advise_rejects_unsafe_or_same(self):
        j, tid = self.j, self.tid
        n = j.task['needs']
        unchanged(self, j, 'gift_advise', task=tid, item=n['product'])
        unchanged(self, j, 'gift_advise', task=tid, item='bear' if n['product'] != 'bear' else 'blocks')
        unchanged(self, j, 'gift_advise', task=tid, item='card')

    def test_advise_then_sell_safe_gift(self):
        j, tid = self.j, self.tid
        item = gs.safe_swap(j.c, j.task)
        j.act('gift_advise', task=tid, item=item)
        self.assertEqual(j.task['gs']['swap'], item)
        unchanged(self, j, 'gift_advise', task=tid, item=item)
        j.solve(tid)
        t = j.get(tid)
        self.assertEqual((t['status'], t['mistakes']), ('completed', 0))
        self.assertEqual(gift_state(j)['followups'], [])

    def test_selling_the_unsafe_toy_has_consequences(self):
        j, tid = self.j, self.tid
        n = j.task['needs']
        j.act('shop_pick', task=tid, item=n['product'])
        self.assertEqual(j.task['mistakes'], 1)
        if n['gift']:
            j.act('shop_pack', task=tid, paper=n['paper'], ribbon='gold', card='x')
        j.act('shop_check', task=tid)
        money = j.c['money']
        j.act('shop_deliver', task=tid)
        t = j.get(tid)
        # The label is read at the counter: safety slip, the customer refuses and gets the money back.
        self.assertEqual([x['code'] for x in t['slips']], ['age_unsafe'])
        self.assertEqual(t['reaction']['kind'], 'refuse')
        review = next(f for f in j.c['feed'] if f.get('source') == tid and f.get('kind') == 'review')
        self.assertEqual(review['stars'], 1)
        self.assertIn(gs.LABELS[n['product']]['label'], review['text'])
        self.assertEqual(j.c['money'], money - (5 if n['gift'] else 0))
        self.assertTrue(any(f.get('report') for f in j.c['feed']))
        self.assertEqual(gift_state(j)['followups'], [])
        validate_state(json.loads(json.dumps(j.state)))


class FirstTimeParent(unittest.TestCase):
    def setUp(self):
        self.j = Journey('mother_baby', slot=0, day=3)
        self.tid = self.j.task['id']
        self.j.act('ask', task=self.tid)

    def test_answers_are_hidden_until_asked(self):
        j, tid = self.j, self.tid
        v = pub_task(j)
        self.assertIsNone(v['needs']['budget'])
        self.assertIsNone(v['needs']['product'])
        self.assertIsNone(v['gift']['age'])
        self.assertEqual(v['gift']['kit']['answers'], [])
        self.assertNotIn('wants', json.dumps(v))
        j.act('gift_ask', task=tid, topic='need')
        v = pub_task(j)
        self.assertEqual(len(v['gift']['kit']['answers']), 1)
        unchanged(self, j, 'gift_ask', task=tid, topic='need')
        unchanged(self, j, 'gift_ask', task=tid, topic='salary')
        j.act('gift_ask', task=tid, topic='budget')
        self.assertEqual(pub_task(j)['needs']['budget'], j.task['needs']['budget'])

    def test_kit_must_cover_the_worries(self):
        j, tid = self.j, self.tid
        wants = j.task['gift']['kit']['wants']
        other = next(u for u in ('sleep', 'bath', 'feed', 'play', 'wear') if u not in wants)
        item = min((k for k, v in gs.LABELS.items() if v['use'] == other and gs.suits(k, j.task['gift']['age'])), key=lambda k: PRODUCT_INDEX[k]['price'])
        j.act('shop_pick', task=tid, item=item)
        # The check no longer refuses a wrong basket (it can be handed over, the customer
        # reacts at the counter); it must not record or reveal anything before the hand-off.
        j.act('shop_check', task=tid)
        self.assertFalse(j.get(tid).get('slips'))
        self.assertNotIn('slips', pub_task(j))
        j.act('basket_remove', task=tid, item=item)
        j.solve(tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(gift_state(j)['followups'][-1]['kind'], 'thanks')

    def test_unsuitable_item_is_a_mistake(self):
        j, tid = self.j, self.tid
        j.act('shop_pick', task=tid, item='bib')  # 6 months+, the baby is a few weeks old
        self.assertEqual(j.task['mistakes'], 1)


class Returns(unittest.TestCase):
    def journey(self, pred):
        day, slot = find('return', pred, start=3)
        j = Journey('mother_baby', slot=slot, day=day)
        j.act('ask', task=j.task['id'])
        return j, j.task['id']

    def test_truth_hidden_until_checked(self):
        j, tid = self.journey(lambda f: True)
        v = pub_task(j)
        text = json.dumps(v, ensure_ascii=False)
        for k in ('_tag', '_cond', '_found'):
            self.assertNotIn(k, text)
        self.assertIsNone(v['gift']['ret']['book'])
        self.assertIsNone(v['gift']['ret']['tag'])
        j.act('gift_book', task=tid)
        j.act('gift_inspect', task=tid, part='tag')
        v = pub_task(j)
        self.assertTrue(v['gift']['ret']['book'])
        self.assertTrue(v['gift']['ret']['tag'])
        unchanged(self, j, 'gift_inspect', task=tid, part='tag')
        unchanged(self, j, 'gift_inspect', task=tid, part='box')
        unchanged(self, j, 'shop_pick', task=tid, item='bunny')

    def test_other_shop_tag_decline_is_fair(self):
        j, tid = self.journey(lambda f: f['gift']['ret']['_tag'] == 'other')
        j.act('gift_inspect', task=tid, part='tag')
        j.act('gift_inspect', task=tid, part='item')
        unchanged(self, j, 'gift_resolve', task=tid, choice='decline')
        cash = j.c['money']
        j.act('gift_resolve', task=tid, choice='decline', confirm=True)
        t = j.get(tid)
        self.assertEqual((t['status'], t['mistakes']), ('completed', 0))
        self.assertGreaterEqual(j.c['money'], cash)

    def test_refund_of_new_item_restocks(self):
        j, tid = self.journey(lambda f: f['gift']['ret']['_tag'] == 'ours' and f['gift']['ret']['_cond'] == 'new' and f['gift']['ret']['_found'])
        item = j.task['gift']['ret']['item']
        stock = j.c['stock'][item]
        cash = j.c['money']
        j.act('gift_book', task=tid)
        j.act('gift_inspect', task=tid, part='tag')
        j.act('gift_inspect', task=tid, part='item')
        j.act('gift_resolve', task=tid, choice='refund', confirm=True)
        self.assertEqual(j.c['stock'][item], stock + 1)
        self.assertEqual(j.get(tid)['mistakes'], 0)
        self.assertTrue(any(x['category'] == 'refund' and x['amount'] == -PRODUCT_INDEX[item]['price'] for x in j.c['ops']['finance']['ledger']))
        self.assertLessEqual(j.c['money'], cash)

    def test_refund_without_record_is_a_mistake(self):
        j, tid = self.journey(lambda f: f['gift']['ret']['_tag'] == 'ours' and f['gift']['ret']['_cond'] == 'new' and not f['gift']['ret']['_found'])
        j.act('gift_inspect', task=tid, part='tag')
        j.act('gift_inspect', task=tid, part='item')
        j.act('gift_resolve', task=tid, choice='refund', confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], 1)

    def test_deciding_blind_costs_a_mistake(self):
        j, tid = self.journey(lambda f: f['gift']['ret']['_cond'] == 'defect')
        item = j.task['gift']['ret']['item']
        stock = j.c['stock'][item]
        j.act('gift_resolve', task=tid, choice='exchange', confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertEqual(j.c['stock'][item], stock - 1)

    def test_deliver_is_not_the_way(self):
        j, tid = self.journey(lambda f: True)
        unchanged(self, j, 'shop_check', task=tid)


class BabyShower(unittest.TestCase):
    def test_bulk_order(self):
        j = Journey('mother_baby', slot=0, day=4)
        tid = j.task['id']
        j.act('ask', task=tid)
        items = j.task['gift']['items']
        self.assertEqual(gs.basket_cap(j.task), 12)
        first = next(iter(items))
        for _ in range(items[first]):
            j.act('shop_pick', task=tid, item=first)
        # The check no longer refuses a wrong basket (it can be handed over, the customer
        # reacts at the counter); it must not record or reveal anything before the hand-off.
        j.act('shop_check', task=tid)
        self.assertFalse(j.get(tid).get('slips'))
        self.assertNotIn('slips', pub_task(j))
        j.solve(tid)
        t = j.get(tid)
        self.assertEqual((t['status'], t['mistakes']), ('completed', 0))
        self.assertEqual(t['pack']['tag'], 'born')

    def test_staff_leave_judgement_orders_alone(self):
        j = Journey('mother_baby', slot=1, day=2)
        j.act('ask', task=j.task['id'])
        for role in ('sales', 'wrap', 'cashier'):
            self.assertIsNone(ops._assist(j.state, j.c, 'mother_baby', dict(role=role, name='Lan')))
        self.assertEqual(j.task['basket'], {})


class Surprises(unittest.TestCase):
    def setUp(self):
        self.j = Journey('mother_baby', slot=0, day=4)
        self.j.c['day_completed'] = 1

    def test_formula_check(self):
        j = self.j
        b = gift_state(j)
        facts = gs._check_formula(j.c, b)
        force_event(j, 'formula', facts)
        old = [x['id'] for x in facts['cans'] if x['exp'] < j.c['day']]
        v = public_state(j.state)['careers']['mother_baby']['data']['gift']['event']
        self.assertNotIn('exp', json.dumps(v['facts']))
        unchanged(self, j, 'gift_event', can='can-9')
        turn = j.c['turn']
        for cid in old:
            j.act('gift_event', can=cid)
        self.assertEqual(j.c['turn'], turn)
        j.act('gift_event', choice='done')
        ev = gift_state(j)['event']
        self.assertTrue(ev['good'])
        self.assertEqual(gift_state(j)['expired_left'], 0)

    def test_missed_expired_cans_are_found_by_inspection(self):
        j = self.j
        b = gift_state(j)
        force_event(j, 'formula', gs._check_formula(j.c, b))
        j.act('gift_event', choice='done')
        self.assertGreater(gift_state(j)['expired_left'], 0)
        self.assertTrue(any('quá hạn' in f['text'] for f in j.c['feed']))
        j.act('gift_event_ok')
        force_event(j, 'inspection', dict(team='x'))
        cash = j.c['money']
        j.act('gift_event', choice='show')
        self.assertEqual(j.c['money'], cash - 60)

    def test_counterfeit_supplier(self):
        j = self.j
        force_event(j, 'fake', dict(seller='Anh Tâm', item='bear', qty=6, unit=20, _fake=True, inspected=False))
        v = public_state(j.state)['careers']['mother_baby']['data']['gift']['event']
        self.assertNotIn('_fake', json.dumps(v))
        self.assertEqual(v['facts']['labels'], [])
        j.act('gift_event', choice='inspect')
        v = public_state(j.state)['careers']['mother_baby']['data']['gift']['event']
        self.assertIn('Không có tem hợp quy CR', v['facts']['labels'])
        self.assertIn('report', [o['id'] for o in v['choices']])
        bears = j.c['stock']['bear']
        j.act('gift_event', choice='buy')
        self.assertEqual((j.c['stock']['bear'], gift_state(j)['fake']), (bears + 6, 6))
        j.act('gift_event_ok')
        force_event(j, 'inspection', dict(team='x'))
        j.act('gift_event', choice='hide')
        self.assertEqual((gift_state(j)['fake'], j.c['stock']['bear']), (0, bears))

    def test_fake_bear_sale_comes_back(self):
        day, slot = find('simple', lambda f: f['needs']['product'] == 'bear')
        j = Journey('mother_baby', slot=slot, day=day)
        gift_state(j)['fake'] = 3
        j.solve(j.task['id'])
        self.assertEqual(gift_state(j)['followups'][-1]['kind'], 'fake')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertTrue(any(f['stars'] == 1 for f in j.c['feed'] if f.get('kind') == 'review'))

    def test_lost_child_leaving_counter(self):
        j = self.j
        t = make_task('mother_baby', 4, 5, 1)
        j.c['tasks'].append(t)
        force_event(j, 'lost', dict(age=4))
        j.act('gift_event', choice='outside')
        self.assertEqual(j.get(t['id'])['patience'], 88)

    def test_haggle_discount_applied_at_checkout(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        items = j.task['gift']['items']
        for k, q in items.items():
            for _ in range(q):
                j.act('shop_pick', task=tid, item=k)
        force_event(j, 'haggle', dict(task=tid, total=100, ask=10))
        j.act('gift_event', choice='discount')
        self.assertEqual(j.task['gs']['discount'], 10)
        j.solve(tid)
        self.assertTrue(any(x['category'] == 'discount' and x['amount'] == -10 for x in j.c['ops']['finance']['ledger']))

    def test_tet_rush_adds_customers(self):
        j = self.j
        n = len(j.c['tasks'])
        force_event(j, 'tet', dict(extra=2))
        cash = j.c['money']
        j.act('gift_event', choice='helper')
        self.assertEqual((len(j.c['tasks']), j.c['money']), (n + 2, cash - 30))
        validate_state(j.state)

    def test_donation_goods(self):
        j = self.j
        towel, socks = j.c['stock']['towel'], j.c['stock']['socks']
        force_event(j, 'donation', dict(org='x'))
        j.act('gift_event', choice='goods')
        self.assertEqual((j.c['stock']['towel'], j.c['stock']['socks']), (towel - 2, socks - 1))

    def test_events_wait_for_first_sale(self):
        j = Journey('mother_baby', slot=0, day=4)
        for _ in range(20):
            gs.after_action(j.state, j.c, 'shop_pick')
        self.assertIsNone(gift_state(j)['event'])

    def roll(self, story_day):
        from game.events import instantiate
        j = Journey('mother_baby', slot=0, day=4)
        j.c['day_completed'] = 1
        j.c['event'] = instantiate('MB-E01', 1, story_day)
        for turn in range(2, 60):
            j.c['turn'] = turn
            gs.after_action(j.state, j.c, 'shop_pick')
            if gift_state(j)['event']:
                break
        return gift_state(j)['event']

    def test_story_from_today_goes_first(self):
        self.assertIsNone(self.roll(4))

    def test_story_carried_from_yesterday_does_not_block_surprises(self):
        self.assertIsNotNone(self.roll(3))


class Restock(unittest.TestCase):
    def test_parcel_cannot_be_received_before_it_shows_as_arrived(self):
        j = Journey()
        j.act('order_stock', item='socks', qty=2, supplier='express')  # 30–60 minutes on the shop clock
        ship = j.c['shipments'][-1]
        j.act('advance')
        self.assertFalse(next(x for x in public_state(j.state)['careers']['mother_baby']['shipments'] if x['id'] == ship['id'])['ready_now'])
        unchanged(self, j, 'receive_stock', shipment=ship['id'], count=2)
        for _ in range(3):
            j.act('advance')
        self.assertTrue(next(x for x in public_state(j.state)['careers']['mother_baby']['shipments'] if x['id'] == ship['id'])['ready_now'])
        j.act('receive_stock', shipment=ship['id'], count=2)


class Texts(unittest.TestCase):
    def test_no_gendered_player_address(self):
        texts = []
        for day in range(2, 30):
            for slot in range(8):
                f = gs.make_fields(day, slot)
                t = dict(f, id=f'mother_baby-{day:04d}-{slot:02d}', day=day, known=True, career='mother_baby')
                texts += [f['title'], f['opening'], gs.request_text(None, t)]
        j = Journey('mother_baby', slot=0, day=4)
        for kind in gs.EVENTS:
            ev = dict(kind=kind, facts=dict(cans=[], today='01/03', pulled=[], seller='x', item='bear', qty=6, unit=20, _fake=True, total=100, ask=10, extra=2))
            texts.append(gs.event_text(j.c, ev))
            texts += [o['label'] for o in gs.event_choices(j.c, ev)]
        blob = ' '.join(texts).lower()
        for bad in ('chị chủ', 'anh chủ', 'cô chủ', 'npc', 'trong game'):
            self.assertNotIn(bad, blob)

    def test_public_state_has_no_hidden_keys(self):
        j = Journey('mother_baby', slot=1, day=3)
        j.act('ask', task=j.task['id'])
        text = json.dumps(public_state(j.state)['careers']['mother_baby'], ensure_ascii=False)
        self.assertNotIn('"_', text)


class Consequences(unittest.TestCase):
    """A wrong gift can be handed over; the customer reacts in proportion (game/consequences.py)."""

    def deliver(self, kind, pred, basket=None, paper='right', tag='right'):
        day, slot = find(kind, pred)
        j = Journey('mother_baby', slot=slot, day=day)
        for k in j.c['stock']:
            j.c['stock'][k] = 20
        tid = j.task['id']
        j.act('ask', task=tid)
        t = j.task
        n = t['needs']
        for k, q in (basket(t) if basket else gs.best_basket(j.c, t)).items():
            for _ in range(q):
                j.act('shop_pick', task=tid, item=k)
        if n['gift'] and paper is not None:
            want_tag = t['gift'].get('tag')
            got_tag = want_tag if tag == 'right' else tag
            j.act('shop_pack', task=tid, paper=n['paper'] if paper == 'right' else paper, ribbon='gold', card='Chúc bé',
                  **({'tag': got_tag} if got_tag else {}))
        j.act('shop_check', task=tid)
        money = j.c['money']
        j.act('shop_deliver', task=tid)
        t = j.get(tid)
        review = next(f for f in j.c['feed'] if f.get('source') == tid and f.get('kind') == 'review')
        sale = sum(PRODUCT_INDEX[k]['price'] * q for k, q in t['basket'].items())
        return j, t, review, j.c['money'] - money, sale

    def test_right_gift_full_pay_no_slips(self):
        j, t, review, delta, sale = self.deliver('simple', lambda f: f['needs']['gift'])
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertGreaterEqual(review['stars'], 4)
        self.assertGreaterEqual(delta, sale - 5)

    def test_wrong_main_item_costs_money_and_stars(self):
        swap = lambda t: {('towel' if t['needs']['product'] != 'towel' else 'socks'): t['needs']['qty']}
        j, t, review, delta, sale = self.deliver('simple', lambda f: f['needs']['gift'] and f['needs']['product'] not in ('cloud_shirt', 'rose_shirt'), swap)
        self.assertEqual([x['code'] for x in t['slips']], ['wrong_item'])
        self.assertLessEqual(review['stars'], 3)
        self.assertIn('sai hẳn món', review['text'])
        self.assertIn(t['reaction']['kind'], ('discount', 'refund', 'walkout'))
        cut = t['reaction']['cut']
        self.assertGreater(cut, 0)
        # Exactly the sale minus what the customer took back, minus the wrapping.
        self.assertEqual(delta, sale - cut - 5)
        # Replaying the reaction never moves money again.
        from game import consequences as cq
        before = j.c['money']
        again = cq.react(j.state, j.c, t, sale, prepaid=True)
        self.assertEqual((j.c['money'], again['pay']), (before, 0))
        validate_state(json.loads(json.dumps(j.state)))

    def test_severity_scales(self):
        pick = lambda f: f['needs']['gift'] and f['needs']['paper'] != 'cream' and f['needs']['product'] not in ('cloud_shirt', 'rose_shirt')
        _, small, r1, _, _ = self.deliver('simple', pick, paper='cream')
        _, big, r3, _, _ = self.deliver('simple', pick, lambda t: {('towel' if t['needs']['product'] != 'towel' else 'socks'): t['needs']['qty']})
        self.assertEqual([x['sev'] for x in small['slips']], [1])
        self.assertIn('giấy', r1['text'])
        self.assertGreater(r1['stars'], r3['stars'])
        self.assertLessEqual(small['reaction']['cut'], big['reaction']['cut'])

    def test_wrong_card_and_missing_wrap_are_clear_mistakes(self):
        occ = lambda f: f['gift']['pick'] == 'named'
        _, t, review, _, _ = self.deliver('occasion', occ, tag='bday' if gs.make_fields(*find('occasion', occ))['gift']['tag'] != 'bday' else 'born')
        self.assertEqual([x['code'] for x in t['slips']], ['card'])
        self.assertLessEqual(review['stars'], 3)
        _, t, review, _, _ = self.deliver('simple', lambda f: f['needs']['gift'], paper=None)
        self.assertEqual([x['code'] for x in t['slips']], ['no_wrap'])
        self.assertLessEqual(review['stars'], 3)

    def test_unsafe_for_age_is_refused_and_inspected(self):
        j, t, review, delta, sale = self.deliver('occasion', lambda f: f['gift']['pick'] == 'open' and f['gift']['age'] == 1, lambda t: {'blocks': 1})
        self.assertTrue(t['slips'][0]['safety'])
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(review['stars'], 1)
        self.assertEqual(delta, -5)
        self.assertTrue(any(f.get('report') and f.get('source') == t['id'] for f in j.c['feed']))
        self.assertTrue(any(x['src'] == t['id'] and x['script'] == 'slip_safety_inspect' for x in j.c['incidents']['follow']))
        # The toy went back on the shelf.
        self.assertEqual(j.c['stock']['blocks'], 20)
        validate_state(json.loads(json.dumps(j.state)))

    def test_over_budget_and_short_quantity(self):
        _, t, review, _, _ = self.deliver('simple', lambda f: f['needs']['qty'] == 2, lambda t: {t['needs']['product']: 1})
        self.assertEqual([x['code'] for x in t['slips']], ['qty_short'])
        self.assertIn('chỉ giao 1', review['text'])
        extra = lambda t: {t['needs']['product']: t['needs']['qty'], ('socks' if t['needs']['product'] != 'socks' else 'towel'): 1}
        _, t, review, _, _ = self.deliver('simple', lambda f: f['needs']['budget'] - gs._price_of(f['needs']['product']) * f['needs']['qty'] < 25, extra)
        self.assertIn('budget', [x['code'] for x in t['slips']])
        self.assertLessEqual(review['stars'], 3)


if __name__ == '__main__':
    unittest.main()
