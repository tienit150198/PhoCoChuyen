"""Milk-tea counter (game/boba.py): stations, grading, queue, groups, app orders,
the timed sealer, daily modifiers, surprises and save compatibility."""
import copy
import json
import unittest

from game import boba
from game.careers import kit
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from tests.helpers import Journey


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def state_of(j):
    return j.c['ext']['data']['boba']


def open_task(j):
    return next(t for t in j.c['tasks'] if t['id'] == j.c['active_task'])


def unchanged(test, j, action, **payload):
    before = copy.deepcopy(j.state)
    with test.assertRaises(GameError):
        j.act(action, **payload)
    test.assertEqual(j.state, before)


def make_cup(j, tid, skip_seal=False):
    t = j.get(tid)
    for action, payload in boba.solution(t):
        if skip_seal and action in ('tea_seal', 'tea_serve'):
            continue
        if action == 'tea_add' and boba.stock(j.c)[payload['item']] == 0:
            j.act('tea_prepare', item=payload['item'], qty=5, confirm=True)
        if action == 'tea_serve':
            break
        j.act(action, **payload)


def force_event(j, kind, facts=None, task=None):
    b = state_of(j)
    facts = facts if facts is not None else boba.EVENTS[kind]['check'](j.state, j.c, b)
    b['event'] = dict(id=f'tea-ev-{j.c["day"]}-99', kind=kind, day=j.c['day'], turn=j.c['turn'], stage='open', facts=facts,
                      task=task or facts.get('task'), choice=None, result=None, effects=[])
    validate_state(j.state)
    return b['event']


class CounterStations(unittest.TestCase):
    def test_cup_first_then_base(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        unchanged(self, j, 'tea_add', task=tid, item='milk')
        m = state_of(j)['cups']['M']
        j.act('tea_cup', task=tid, size='M')
        self.assertEqual(state_of(j)['cups']['M'], m - 1)
        unchanged(self, j, 'tea_add', task=tid, item='pearls')  # base first
        j.act('tea_add', task=tid, item='milk')
        unchanged(self, j, 'tea_add', task=tid, item='black')  # one base only
        unchanged(self, j, 'tea_cup', task=tid, size='L')  # cannot resize a cup with tea

    def test_swap_empty_cup_returns_it_to_stack(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        cups = dict(state_of(j)['cups'])
        j.act('tea_cup', task=tid, size='M')
        j.act('tea_cup', task=tid, size='L')
        self.assertEqual(state_of(j)['cups'], dict(M=cups['M'], L=cups['L'] - 1))

    def test_locked_items_need_skill(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tea_cup', task=tid, size='M')
        self.assertEqual(boba.level(j.c), 1)
        unchanged(self, j, 'tea_add', task=tid, item='green')
        unchanged(self, j, 'tea_prepare', item='cheese', qty=3, confirm=True)
        state_of(j)['total'] = 18
        self.assertEqual(boba.level(j.c), 4)
        j.act('tea_prepare', item='green', qty=3, confirm=True)
        j.act('tea_add', task=tid, item='green')

    def test_topping_limit_and_duplicates(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tea_cup', task=tid, size='M')
        j.act('tea_add', task=tid, item='milk')
        for item in ('pearls', 'jelly', 'foam'):
            j.act('tea_add', task=tid, item=item)
        unchanged(self, j, 'tea_add', task=tid, item='popping')
        unchanged(self, j, 'tea_add', task=tid, item='jelly')

    def test_seal_needs_sugar_and_ice(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tea_cup', task=tid, size='M')
        j.act('tea_add', task=tid, item='milk')
        unchanged(self, j, 'tea_seal', task=tid)
        j.act('tea_sugar', task=tid, level=50)
        unchanged(self, j, 'tea_seal', task=tid)
        unchanged(self, j, 'tea_sugar', task=tid, level=40)
        unchanged(self, j, 'tea_ice', task=tid, level='frozen')
        j.act('tea_ice', task=tid, level='little')
        j.act('tea_seal', task=tid)
        self.assertEqual(j.get(tid)['cup']['seal_q'], 'ok')
        unchanged(self, j, 'tea_add', task=tid, item='jelly')


class Sealer(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def ready(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        make_cup(j, tid, skip_seal=True)
        return j, tid

    def test_perfect_zone(self):
        j, tid = self.ready()
        turn = j.c['turn']
        j.act('tea_seal_start', task=tid)
        self.assertEqual(j.c['turn'], turn)  # pressing the lever is free
        self.clock.t += 2.0
        r = j.act('tea_seal', task=tid)
        self.assertEqual(r['seal'], 'perfect')
        cash = j.c['money']
        j.act('tea_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(j.get(tid)['mistakes'], 0)
        self.assertTrue(any(x['reason'] == 'Nắp dán đẹp, khách thưởng thêm' for x in j.c['ops']['finance']['ledger']))
        self.assertGreater(j.c['money'], cash)

    def test_loose_and_burnt(self):
        j, tid = self.ready()
        j.act('tea_seal_start', task=tid)
        self.clock.t += 0.3
        j.act('tea_seal', task=tid)
        self.assertFalse(j.get(tid)['cup']['sealed'])
        j.act('tea_seal_start', task=tid)
        self.clock.t += 6
        r = j.act('tea_seal', task=tid)
        self.assertEqual(r['seal'], 'burnt')
        j.act('tea_serve', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], 1)  # accepted, but noticed

    def test_seal_time_is_validated(self):
        j, tid = self.ready()
        j.act('tea_seal_start', task=tid)
        bad = copy.deepcopy(j.state)
        t = next(x for x in bad['careers']['milk_tea']['tasks'] if x['id'] == tid)
        t['cup']['seal_t'] = 'soon'
        with self.assertRaises(GameError):
            validate_state(bad)
        t['cup']['seal_t'] = None
        t['cup']['seal_q'] = 'perfect'
        with self.assertRaises(GameError):
            validate_state(bad)  # unsealed cups carry no seal quality


class Grading(unittest.TestCase):
    def test_wrong_base_returns_the_cup(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.get(tid)['needs']
        wrong = next(x for x in ('milk', 'black', 'matcha') if x != n['base'])
        j.act('tea_cup', task=tid, size=n['size'])
        j.act('tea_add', task=tid, item=wrong)
        j.act('tea_ice', task=tid, level=n['ice'])
        j.act('tea_sugar', task=tid, level=n['sugar'])
        j.act('tea_seal', task=tid)
        r = j.act('tea_serve', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'] != 'completed', True)
        self.assertEqual(t['mistakes'], 1)
        self.assertFalse(t['cup']['placed'])
        self.assertEqual(state_of(j)['returned'], 1)
        self.assertIn('trả ly', r['message'])
        self.assertTrue(any(w['reason'] == 'Khách trả ly' for w in j.c['life']['waste']))

    def test_minor_sugar_miss_is_accepted(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        make_cup(j, tid, skip_seal=True)
        n = j.get(tid)['needs']
        j.act('tea_sugar', task=tid, level=next(x for x in boba.SUGARS if x != n['sugar']))
        j.act('tea_seal', task=tid)
        cash = j.c['money']
        j.act('tea_serve', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual((t['status'], t['mistakes']), ('completed', 1))
        self.assertEqual(j.c['money'], cash + t['quoted_price'])

    def test_serve_needs_seal_and_confirm(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        make_cup(j, tid, skip_seal=True)
        unchanged(self, j, 'tea_serve', task=tid, confirm=True)
        j.act('tea_seal', task=tid)
        unchanged(self, j, 'tea_serve', task=tid)

    def test_order_hidden_until_asked_and_usual_stays_hidden(self):
        j = Journey('milk_tea')
        v = public_state(j.state)['careers']['milk_tea']
        t = v['tasks'][0]
        self.assertIsNone(t['needs'])
        self.assertIsNone(t['order_text'])
        self.assertNotIn('src', t)
        j.act('ask')
        t = public_state(j.state)['careers']['milk_tea']['tasks'][0]
        self.assertTrue(t['order_text'])
        raw = j.task
        raw['usual'] = True
        t = public_state(j.state)['careers']['milk_tea']['tasks'][0]
        self.assertIsNone(t['needs'])
        self.assertIn('Như mọi khi', t['order_text'])

    def test_tampered_order_is_rejected(self):
        j = Journey('milk_tea')
        bad = copy.deepcopy(j.state)
        t = bad['careers']['milk_tea']['tasks'][0]
        t['needs']['size'] = 'L' if t['needs']['size'] == 'M' else 'M'
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_orders_are_deterministic(self):
        self.assertEqual(boba.task_fields(3, 2), boba.task_fields(3, 2))
        a, b = Journey('milk_tea'), Journey('milk_tea')
        self.assertEqual(a.c['tasks'], b.c['tasks'])

    def test_natural_order_text(self):
        t = boba.task_fields(2, 1)
        t['id'] = 'milk_tea-0002-01'
        t['needs'] = dict(base='black', flavor=None, toppings=['q3'], size='M', sugar=100, ice='little')
        t['walkin'] = dict(boba.WALKIN_INDEX['nam'])
        text = boba.order_text(t)
        self.assertEqual(text, 'Cháu ơi, cho bà 1 ly hồng trà size M, thạch 3Q, 100% đường và ít đá nha.')
        t['group'] = dict(id='g', n=3, i=2)
        self.assertTrue(boba.order_text(t).startswith('Cháu ơi, cho bà 3 ly, ly 2 là hồng trà'))


class Queue(unittest.TestCase):
    def test_waiting_customers_lose_patience_and_walk_out(self):
        j = Journey('milk_tea')
        j.c['life']['mode'] = 'normal'
        state_of(j)['mod'] = 'students'
        active = j.task['id']
        other = next(t for t in j.c['tasks'] if t['id'] != active and t['status'] == 'new')
        other['patience'] = 27
        j.act('ask', task=active)
        j.act('tea_cup', task=active, size='M')
        self.assertEqual(other['id'], j.get(other['id'])['id'])
        o = j.get(other['id'])
        self.assertEqual(o['status'], 'cancelled')
        self.assertEqual(state_of(j)['walkouts'], 1)
        post = next(f for f in j.c['feed'] if f['source'] == o['id'])
        self.assertEqual(post['stars'], 2)
        validate_state(j.state)

    def test_calm_day_has_no_waiting(self):
        j = Journey('milk_tea')
        j.c['life']['mode'] = 'calm'
        tid = j.task['id']
        others = {t['id']: t.get('patience', 100) for t in j.c['tasks'] if t['id'] != tid}
        j.act('ask', task=tid)
        j.act('tea_cup', task=tid, size='M')
        self.assertEqual({t['id']: t.get('patience', 100) for t in j.c['tasks'] if t['id'] != tid}, others)

    def test_more_customers_arrive_after_serving(self):
        j = Journey('milk_tea')
        b = state_of(j)
        self.assertEqual(b['arrived'], len(j.c['tasks']))
        self.assertLessEqual(len(j.c['tasks']), 3)
        j.solve()
        self.assertGreaterEqual(b['arrived'], len([t for t in j.c['tasks']]))

    def test_same_person_never_waits_twice(self):
        for day in range(2, 7):
            j = Journey('milk_tea', day=day)
            for _ in range(8):
                t = next((x for x in j.c['tasks'] if x['status'] not in ('completed', 'cancelled')), None)
                if not t:
                    break
                waiting = {(x.get('group') or {}).get('id') or x['id']: (x.get('walkin') or {}).get('id') or x['npc'] for x in j.c['tasks']
                           if x['status'] not in ('completed', 'referred', 'cancelled') and not x.get('app')}
                keys = list(waiting.values())
                self.assertEqual(len(keys), len(set(keys)), keys)
                j.solve(t['id'])

    def test_group_order_single_review(self):
        j = Journey('milk_tea')
        made = boba.spawn_group(j.state, j.c, 3)
        self.assertEqual([t['group']['i'] for t in made], [1, 2, 3])
        self.assertEqual(len({t['walkin']['id'] for t in made}), 1)
        self.assertTrue(all('ly' in t['title'] for t in made))
        validate_state(j.state)
        for t in made:
            j.c['active_task'] = t['id']
            j.solve(t['id'])
        reviews = [f for f in j.c['feed'] if f.get('kind') == 'review' and f['source'] in {t['id'] for t in made}]
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]['author'], made[0]['walkin']['name'])
        validate_state(j.state)

    def test_group_walkout_takes_every_cup(self):
        j = Journey('milk_tea')
        made = boba.spawn_group(j.state, j.c, 2)
        j.c['life']['mode'] = 'normal'
        for t in made:
            t['patience'] = 26
        j.act('ask', task=j.task['id'])
        j.act('tea_cup', task=j.task['id'], size='M')
        self.assertTrue(all(j.get(t['id'])['status'] == 'cancelled' for t in made))
        validate_state(j.state)

    def test_app_order_fee_and_deadline(self):
        j = Journey('milk_tea')
        j.c['life']['mode'] = 'normal'
        t = boba.spawn(j.state, j.c, app=True)
        self.assertTrue(t['known'])
        self.assertTrue(t['title'].startswith('Đơn app #'))
        validate_state(j.state)
        j.c['active_task'] = t['id']
        cash = j.c['money']
        make_cup(j, t['id'])
        j.act('tea_serve', task=t['id'], confirm=True)
        fee = round(t['quoted_price'] * boba.APP_FEE_PCT / 100)
        self.assertEqual(j.get(t['id'])['status'], 'completed')
        self.assertGreaterEqual(j.c['money'] - cash, t['quoted_price'] - fee)

    def test_late_app_order_is_cancelled(self):
        j = Journey('milk_tea')
        j.c['life']['mode'] = 'normal'
        j.c['turn'] += 30
        t = boba.spawn(j.state, j.c, app=True)
        t['app']['deadline'] = j.c['turn'] - 11
        tid = next(x['id'] for x in j.c['tasks'] if x['id'] != t['id'])
        j.act('ask', task=tid)
        j.act('tea_cup', task=tid, size='M')
        self.assertEqual(j.get(t['id'])['status'], 'cancelled')
        self.assertTrue(any('app' in f['text'] for f in j.c['feed'] if f['source'] == t['id']))


class DayAndUpgrades(unittest.TestCase):
    def test_modifier_is_seeded(self):
        self.assertEqual(boba.roll_mod(1), 'quiet')
        self.assertEqual([boba.roll_mod(d) for d in range(2, 12)], [boba.roll_mod(d) for d in range(2, 12)])
        self.assertGreater(len({boba.roll_mod(d) for d in range(2, 30)}), 3)

    def test_upgrade_needs_skill_money_and_confirm(self):
        j = Journey('milk_tea')
        unchanged(self, j, 'tea_upgrade', id='bell', confirm=True)
        state_of(j)['total'] = 4
        unchanged(self, j, 'tea_upgrade', id='bell')
        cash = j.c['money']
        j.act('tea_upgrade', id='bell', confirm=True)
        self.assertEqual(j.c['money'], cash - 60)
        unchanged(self, j, 'tea_upgrade', id='bell', confirm=True)

    def test_auto_sealer_is_free_and_perfect(self):
        j = Journey('milk_tea')
        b = state_of(j)
        b['upgrades'].append('sealer')
        tid = j.task['id']
        j.act('ask', task=tid)
        make_cup(j, tid, skip_seal=True)
        turn = j.c['turn']
        r = j.act('tea_seal', task=tid)
        self.assertEqual((j.c['turn'], r['seal']), (turn, 'perfect'))

    def test_buy_cups(self):
        j = Journey('milk_tea')
        cups = state_of(j)['cups']['L']
        unchanged(self, j, 'tea_cups', size='L')
        j.act('tea_cups', size='L', confirm=True)
        self.assertEqual(state_of(j)['cups']['L'], cups + boba.CUP_PACK['qty'])

    def test_warning_when_pearls_are_not_cooked(self):
        j = Journey('milk_tea')
        for lot in j.c['life']['pantry']:
            if lot['item'] == 'pearls':
                lot['qty'] = 0
        self.assertIn('pearls', [w['id'] for w in public_state(j.state)['careers']['milk_tea']['data']['boba']['warnings']])

    def test_close_keeps_history(self):
        j = Journey('milk_tea')
        j.solve()
        j.act('end_day', carry_event=True)
        h = state_of(j)['history'][-1]
        self.assertEqual((h['day'], h['served']), (1, 1))
        self.assertIsNotNone(j.c['life']['recap']['counter'])


class Surprises(unittest.TestCase):
    def day2(self):
        j = Journey('milk_tea')
        j.solve()
        j.act('end_day', carry_event=True)
        j.act('start_day')
        j.solve()
        state_of(j)['event'] = None
        return j

    def test_inspection_on_dirty_counter_fines(self):
        j = self.day2()
        state_of(j)['mess'] = 3
        force_event(j, 'inspection', dict(team='x'))
        cash = j.c['money']
        j.act('tea_event', choice='open')
        self.assertEqual(j.c['money'], cash - 40)
        self.assertEqual(state_of(j)['event']['stage'], 'done')
        j.act('tea_event_ok')
        self.assertIsNone(state_of(j)['event'])

    def test_inspection_envelope_is_worse(self):
        j = self.day2()
        force_event(j, 'inspection', dict(team='x'))
        cash = j.c['money']
        j.act('tea_event', choice='envelope')
        self.assertEqual(j.c['money'], cash - 80)

    def test_invalid_choice_changes_nothing(self):
        j = self.day2()
        force_event(j, 'inspection', dict(team='x'))
        unchanged(self, j, 'tea_event', choice='run')
        state_of(j)['event'] = None
        unchanged(self, j, 'tea_event', choice='open')

    def test_pearls_out_swap_changes_orders(self):
        j = self.day2()
        t = j.task
        t['changes'] = []
        t['src'] = dict(fixed=dict(base='milk', flavor=None, toppings=['pearls'], size='M', sugar=50, ice='normal'))
        t['needs'] = boba.derive(t)
        force_event(j, 'pearls_out', dict(tasks=[t['id']], left=0))
        j.act('tea_event', choice='swap')
        self.assertNotIn('pearls', j.get(t['id'])['needs']['toppings'])
        validate_state(j.state)

    def test_pearls_out_cook_costs_and_restocks(self):
        j = self.day2()
        force_event(j, 'pearls_out', dict(tasks=[], left=0))
        before = boba.stock(j.c)['pearls']
        cash = j.c['money']
        j.act('tea_event', choice='cook')
        self.assertEqual((boba.stock(j.c)['pearls'], j.c['money']), (before + 8, cash - 16))

    def test_rush_menu_adds_combo_students(self):
        j = self.day2()
        force_event(j, 'rush', dict(count=2))
        n = len(j.c['tasks'])
        j.act('tea_event', choice='menu')
        new = j.c['tasks'][n:]
        self.assertEqual(len(new), 2)
        self.assertTrue(all(t['combo'] and t['walkin']['kind'] == 'student' for t in new))
        validate_state(j.state)

    def test_regular_story_three_steps(self):
        j = self.day2()
        force_event(j, 'regular', dict(step=0))
        j.act('tea_event', choice='less')
        st = state_of(j)['story']
        self.assertEqual(st['step'], 1)
        force_event(j, 'regular', dict(step=1))
        cash = j.c['money']
        j.act('tea_event', choice='treat')
        self.assertEqual(j.c['money'], cash - 25)
        force_event(j, 'regular', dict(step=2))
        j.act('tea_event', choice='serve')
        self.assertEqual(state_of(j)['story']['step'], 3)
        self.assertTrue(any(t.get('walkin') and t['walkin']['name'] == 'Ngân' for t in j.c['tasks']))
        self.assertTrue(any(x['id'] == 'tea-story-tu' for x in j.c['life']['stickers']))

    def test_change_mind_accept_updates_order_and_price(self):
        j = self.day2()
        t = j.task
        j.act('ask', task=t['id'])
        j.act('tea_cup', task=t['id'], size=t['needs']['size'])
        j.act('tea_add', task=t['id'], item=j.get(t['id'])['needs']['base'])
        state_of(j)['event'] = None
        ev = force_event(j, 'change_mind', dict(task=t['id'], change=dict(set='sugar', to=70)), task=t['id'])
        unchanged(self, j, 'tea_serve', task=t['id'], confirm=True)
        j.act('tea_event', choice='accept')
        self.assertEqual(j.get(t['id'])['needs']['sugar'], 70)
        validate_state(j.state)

    def test_office_group_bonus_on_time(self):
        j = self.day2()
        force_event(j, 'office', dict(count=3, bonus=15))
        j.act('tea_event', choice='accept')
        cups = [t for t in j.c['tasks'] if t.get('office')]
        self.assertEqual(len(cups), 3)
        self.assertEqual(len({t['group']['id'] for t in cups}), 1)
        state_of(j)['event'] = None
        for t in cups:
            j.c['active_task'] = t['id']
            j.solve(t['id'])
        self.assertTrue(any(x['reason'] == 'Đơn văn phòng giao đúng hẹn' for x in j.c['ops']['finance']['ledger']))

    def test_spill_wastes_cup(self):
        j = self.day2()
        t = j.task
        j.act('ask', task=t['id'])
        make_cup(j, t['id'])
        state_of(j)['event'] = None
        b = state_of(j)
        facts = boba._check_spill(j.state, j.c, b)
        # Trigger path: spill empties the sealed cup and dirties the counter.
        b['ev_seq'] += 1
        force_event(j, 'spill', facts)
        boba._waste_cup(j.c, j.get(t['id']), 'Ly bị đổ')
        b['mess'] = 2
        j.act('tea_event', choice='pay')
        self.assertEqual(state_of(j)['mess'], 0)
        self.assertFalse(j.get(t['id'])['cup']['sealed'])

    def test_short_delivery_sign_promise_next_day(self):
        j = self.day2()
        force_event(j, 'short_delivery', dict(item='milk', billed=10, got=7, cost=4, _honest=True))
        view = public_state(j.state)['careers']['milk_tea']['data']['boba']['event']
        self.assertNotIn('_honest', json.dumps(view))
        before = boba.stock(j.c)['milk']
        j.act('tea_event', choice='sign')
        self.assertEqual(boba.stock(j.c)['milk'], before + 7)
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertTrue(any(l['item'] == 'milk' and l['qty'] == 3 and l['unit_cost'] == 0 for l in j.c['life']['pantry']))

    def test_power_cut_dome(self):
        j = self.day2()
        t = j.task
        j.act('ask', task=t['id'])
        make_cup(j, t['id'], skip_seal=True)
        state_of(j)['event'] = None
        state_of(j)['sealer_off'] = j.c['turn'] + 5
        force_event(j, 'power_cut', dict(beats=4))
        unchanged(self, j, 'tea_seal', task=t['id'])
        j.act('tea_event', choice='dome')
        cash = j.c['money']
        j.act('tea_seal', task=t['id'])
        self.assertTrue(j.get(t['id'])['cup']['dome'])
        self.assertEqual(j.c['money'], cash - 1)

    def test_short_money_trust_repaid(self):
        j = self.day2()
        t = j.task
        j.act('ask', task=t['id'])
        force_event(j, 'short_money', dict(task=t['id'], short=5, size='M', _honest=True))
        j.act('tea_event', choice='trust')
        self.assertEqual(j.get(t['id'])['discount'], 5)
        j.solve(t['id'])
        j.act('end_day', carry_event=True)
        cash = j.c['money']
        j.act('start_day')
        self.assertTrue(any(x['reason'] == 'Khách trả tiền còn nợ hôm trước' for x in j.c['ops']['finance']['ledger']))

    def test_vip_perfect_cup_promotion(self):
        j = self.day2()
        force_event(j, 'vip', dict(guest='Hân'))
        j.act('tea_event', choice='accept')
        t = next(t for t in j.c['tasks'] if t.get('vip'))
        state_of(j)['event'] = None
        j.c['active_task'] = t['id']
        j.solve(t['id'])
        self.assertTrue(any(x['reason'] == 'Video của Hân giới thiệu quán' for x in j.c['ops']['finance']['ledger']))

    def test_events_start_only_after_first_cup(self):
        j = Journey('milk_tea')
        b = state_of(j)
        for _ in range(10):
            boba._maybe_event(j.state, j.c, b)
        self.assertIsNone(b['event'])


class Compatibility(unittest.TestCase):
    def test_old_task_upgrades_on_load(self):
        j = Journey('milk_tea')
        old = copy.deepcopy(j.state)
        for t in old['careers']['milk_tea']['tasks']:
            for k in ('walkin', 'changes', 'usual', 'beats', 'discount', 'vip', 'office', 'combo', 'group', 'app', 'src'):
                t.pop(k, None)
            for k in ('placed', 'dome', 'seal_t', 'seal_q'):
                t['cup'].pop(k, None)
        del old['careers']['milk_tea']['ext']['data']['boba']
        new = migrate_state(old)
        validate_state(new)
        s, _ = apply_action(new, 'milk_tea', 'ask', {})
        validate_state(s)

    def test_public_hides_rolls(self):
        j = Journey('milk_tea')
        text = json.dumps(public_state(j.state)['careers']['milk_tea'], ensure_ascii=False)
        self.assertNotIn('"src"', text)
        self.assertNotIn('_honest', text)

    def test_no_gendered_player_address(self):
        texts = []
        for day in range(1, 6):
            for slot in range(12):
                t = boba.task_fields(day, slot)
                t['id'] = f'milk_tea-{day:04d}-{slot:02d}'
                texts += [t['title'], t['opening'], boba.order_text(t)]
        j = Journey('milk_tea')
        for kind in boba.EVENTS:
            ev = dict(kind=kind, facts=dict(step=0, left=1, tasks=[], count=2, change=dict(set='size', to='L'), bonus=15, item='milk', billed=10, got=7,
                                            cost=4, short=5, size='L', guest='Hân', team='x', beats=4), task=None)
            texts.append(boba.event_text(j.c, ev))
            texts += [o['label'] for o in boba.event_choices(j.c, ev)]
        blob = ' '.join(texts).lower()
        for bad in ('chị chủ', 'anh chủ', 'cô chủ', 'npc', 'trong game'):
            self.assertNotIn(bad, blob)


class WrongOrderCosts(unittest.TestCase):
    """Owner report: "dặn ít đá, đưa nhiều đá mà vẫn được đánh giá tốt"."""

    def order(self, j, idx, **over):
        t = [x for x in j.c['tasks'] if x['status'] not in ('completed', 'cancelled')][idx]
        boba.setup_task(j.state, j.c, t, fixed=dict(t['needs'], **over))
        j.act('ask', task=t['id'])
        return t['id']

    def serve(self, j, tid, **cup):
        make_cup(j, tid, skip_seal=True)
        for k, v in cup.items():
            j.act('tea_' + k, task=tid, level=v)
        j.act('tea_seal', task=tid)
        cash = j.c['money']
        r = j.act('tea_serve', task=tid, confirm=True)
        return r, j.c['money'] - cash

    def review(self, j, tid):
        return next((p for p in j.c['feed'] if p.get('source') == tid and p.get('kind') == 'review'), None)

    def test_right_order_still_five_stars(self):
        j = Journey('milk_tea')
        tid = self.order(j, 0, ice='little', sugar=30)
        r, paid = self.serve(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertGreaterEqual(paid, t['quoted_price'])   # full price (plus any tip)
        self.assertEqual(self.review(j, tid)['stars'], 5)

    def test_little_ice_given_extra_ice_is_named_and_costs(self):
        j = Journey('milk_tea')
        tid = self.order(j, 0, ice='little', sugar=30)   # warm regular: grumbles or accepts, never a 5★
        r, paid = self.serve(j, tid, ice='extra')
        t = j.get(tid)
        self.assertEqual(t['slips'][0]['code'], 'ice')
        self.assertEqual(t['slips'][0]['sev'], 2)
        self.assertIn('Dặn ít đá mà đưa nhiều đá', r['message'])
        post = self.review(j, tid)
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('Dặn ít đá mà đưa nhiều đá', post['text'])
        self.assertEqual(paid, t['quoted_price'] - t['reaction']['cut'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_one_notch_is_a_small_slip(self):
        j = Journey('milk_tea')
        tid = self.order(j, 0, ice='little', sugar=30)
        r, paid = self.serve(j, tid, ice='normal')
        t = j.get(tid)
        self.assertEqual((t['slips'][0]['sev'], t['status']), (1, 'completed'))
        self.assertEqual(self.review(j, tid)['stars'], 4)
        self.assertIn('hơi nhiều đá', self.review(j, tid)['text'])

    def test_strict_customer_sends_it_back_or_takes_money_off(self):
        j = Journey('milk_tea')
        tid = self.order(j, 1, ice='none', sugar=50)     # picky walk-in
        waste = len(j.c['life']['waste'])
        r, paid = self.serve(j, tid, ice='extra')
        t = j.get(tid)
        if r.get('reaction') == 'remake':
            self.assertNotEqual(t['status'], 'completed')
            self.assertEqual(paid, 0)
            self.assertEqual(len(j.c['life']['waste']), waste + 1)
            self.assertEqual([x['code'] for x in t['slips']], ['returned'])
            r, paid = self.serve(j, tid)                  # the redo is right: only the wait is left
            t = j.get(tid)
            self.assertEqual(t['status'], 'completed')
            self.assertEqual(self.review(j, tid)['stars'], 4)
            self.assertIn(t['reaction']['kind'], ('accept', 'grumble'))
        else:
            self.assertIn(t['reaction']['kind'], ('discount', 'refund'))
            self.assertLess(paid, t['quoted_price'])
            self.assertLessEqual(self.review(j, tid)['stars'], 3)

    def test_two_clear_mistakes_escalate_to_a_report(self):
        j = Journey('milk_tea')
        tid = self.order(j, 1, ice='none', sugar=0)
        r, paid = self.serve(j, tid, ice='extra', sugar=100)
        t = j.get(tid)
        if r.get('reaction') == 'remake':
            r, paid = self.serve(j, tid, ice='extra', sugar=100)   # same mistakes twice
            t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertIn(t['reaction']['kind'], ('refund', 'walkout'))
        self.assertEqual(paid, t['quoted_price'] - t['reaction']['cut'])
        self.assertLessEqual(self.review(j, tid)['stars'], 2)
        self.assertTrue(any(p.get('report') and p['source'] == tid for p in j.c['feed']))
        self.assertEqual(j.c['slipbook']['reports'], 1)
        # A replayed reaction never moves money again.
        from game import consequences as cq
        cash = j.c['money']
        again = cq.react(j.state, j.c, t, t['quoted_price'])
        self.assertEqual((j.c['money'], again['cut']), (cash, t['reaction']['cut']))
        validate_state(json.loads(json.dumps(j.state)))


if __name__ == '__main__':
    unittest.main()
