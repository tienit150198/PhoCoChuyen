"""Milk-tea counter UX (0.9.5 player feedback): the pinned order ticket agrees with the referee,
the menu can stop selling items, and patience is fairer on long orders."""
import copy
import random
import unittest
from unittest import mock

from game import boba
from game import patience as pt
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey


def st(j):
    return j.c['ext']['data']['boba']


def unchanged(test, j, action, **payload):
    before = copy.deepcopy(j.state)
    with test.assertRaises(GameError):
        j.act(action, **payload)
    test.assertEqual(j.state, before)


def fix_order(j, t, needs):
    t['changes'] = []
    t['usual'] = False
    t['src'] = dict(fixed=copy.deepcopy(needs))
    t['needs'] = boba.derive(t)
    t['quoted_price'] = boba.price(j.c, t['needs'])


def public_task(j, tid):
    return next(x for x in public_state(j.state)['careers']['milk_tea']['tasks'] if x['id'] == tid)


# Which ticket rows stand for each mismatch the referee (_diff) reports.
ROWS_FOR = {'size': {'size'}, 'base': {'base'}, 'flavor': {'flavor', 'extra'}, 'toppings': {'topping', 'extra'},
            'sugar': {'sugar'}, 'ice': {'ice'}}
STEP_OF = {'tea_cup': 'size', 'tea_ice': 'ice', 'tea_sugar': 'sugar', 'tea_seal': 'seal'}


class TicketMatchesReferee(unittest.TestCase):
    def random_cup(self, r, n):
        pool = lambda g: [k for k, v in boba.ING.items() if v['group'] == g]
        items = []
        if r.random() < 0.8:
            items.append(r.choice([n['base']] * 3 + pool('base')))
        if items and r.random() < 0.5:
            items.append(r.choice(([n['flavor']] * 3 if n['flavor'] else []) + pool('flavor')))
        if items:
            tops = list(dict.fromkeys(r.sample(n['toppings'] + pool('topping'), r.randint(0, 3))))[:3]
            items += tops
        placed = bool(items) or r.random() < 0.6
        return dict(placed=placed, size=r.choice([n['size'], 'M', 'L']), items=items,
                    sugar=r.choice([None, n['sugar'], *boba.SUGARS]), ice=r.choice([None, n['ice'], *boba.ICES]),
                    sealed=bool(items) and r.random() < 0.3, checked=False, cost=0)

    def test_every_mismatch_is_a_row_and_all_ok_means_a_right_cup(self):
        r = random.Random(95)
        for i in range(3000):
            n = boba.gen_needs(f'mt-{i}', r.randint(1, 9), r.choice(['', 'heat', 'rain', 'students']), [], 'young')
            cup = self.random_cup(r, n)
            rows = boba.ticket(n, cup)
            diff = boba._diff(cup, n)
            open_keys = {x['k'] for x in rows if x['ok'] is not True}
            for d in diff:
                self.assertTrue(ROWS_FOR[d] & open_keys, (d, n, cup, rows))
            order_rows = [x for x in rows if x['k'] != 'seal']
            self.assertEqual(all(x['ok'] is True for x in order_rows), not diff, (n, cup, rows))
            # Wrong things are marked wrong (✗), never as "not done yet".
            for x in rows:
                if x['k'] == 'extra':
                    self.assertIs(x['ok'], False)

    def test_rows_follow_the_making_order(self):
        j = Journey('milk_tea')
        t = j.task
        fix_order(j, t, dict(base='milk', flavor='peach', toppings=['pearls', 'jelly'], size='L', sugar=50, ice='little'))
        j.act('ask', task=t['id'])
        rows = public_task(j, t['id'])['ticket']
        self.assertEqual([x['k'] for x in rows], ['size', 'base', 'flavor', 'topping', 'topping', 'ice', 'sugar', 'seal'])
        steps = []
        for action, payload in boba.solution(j.get(t['id'])):
            if action == 'tea_add':
                steps.append(boba.ING[payload['item']]['group'])
            elif action in STEP_OF:
                steps.append(STEP_OF[action])
        self.assertEqual(steps, [x['k'] for x in rows])

    def test_following_the_ticket_makes_a_perfect_cup(self):
        j = Journey('milk_tea')
        t = j.task
        tid = t['id']
        fix_order(j, t, dict(base='black', flavor=None, toppings=['pearls', 'foam'], size='M', sugar=70, ice='normal'))
        j.act('ask', task=tid)
        for _ in range(20):
            rows = public_task(j, tid)['ticket']
            nxt = next((x for x in rows if x['ok'] is not True), None)
            if not nxt:
                break
            k = nxt['k']
            if k == 'size':
                j.act('tea_cup', task=tid, size=nxt['want'])
            elif k in ('base', 'flavor', 'topping'):
                j.act('tea_add', task=tid, item=nxt['want'])
            elif k in ('ice', 'sugar'):
                j.act('tea_' + k, task=tid, level=nxt['want'])
            elif k == 'seal':
                j.act('tea_seal', task=tid)
            else:
                self.fail(rows)
        self.assertTrue(all(x['ok'] is True for x in public_task(j, tid)['ticket']))
        r = j.act('tea_serve', task=tid, confirm=True)
        self.assertIn('hoàn hảo', r['message'])

    def test_extra_and_wrong_items_are_marked_wrong(self):
        j = Journey('milk_tea')
        t = j.task
        tid = t['id']
        fix_order(j, t, dict(base='milk', flavor='peach', toppings=['jelly'], size='M', sugar=50, ice='little'))
        j.act('ask', task=tid)
        j.act('tea_cup', task=tid, size='M')
        j.act('tea_add', task=tid, item='milk')
        j.act('tea_add', task=tid, item='lychee')
        j.act('tea_add', task=tid, item='pearls')
        j.act('tea_ice', task=tid, level='normal')
        rows = {(x['k'], x.get('want') or x.get('got')): x['ok'] for x in public_task(j, tid)['ticket']}
        self.assertIs(rows[('flavor', 'peach')], False)
        self.assertIs(rows[('extra', 'pearls')], False)
        self.assertIsNone(rows[('topping', 'jelly')])
        self.assertIs(rows[('ice', 'little')], False)
        self.assertIsNone(rows[('sugar', 50)])

    def test_ticket_hidden_until_the_order_is_heard(self):
        j = Journey('milk_tea')
        self.assertNotIn('ticket', public_task(j, j.task['id']))
        j.act('ask', task=j.task['id'])
        self.assertTrue(public_task(j, j.task['id'])['ticket'])


class Menu(unittest.TestCase):
    def test_all_on_by_default_and_old_saves_load(self):
        j = Journey('milk_tea')
        st(j).pop('menu_off', None)
        validate_state(j.state)
        pub = public_state(j.state)['careers']['milk_tea']['data']['boba']
        self.assertEqual(pub['menu_off'], [])
        self.assertTrue(all(s['on'] for s in pub['stations']))

    def test_switch_off_and_on_without_a_beat(self):
        j = Journey('milk_tea')
        turn = j.c['turn']
        r = j.act('tea_menu', item='pearls', on=False)
        self.assertIn('ngừng bán', r['message'])
        self.assertEqual(st(j)['menu_off'], ['pearls'])
        self.assertEqual(j.c['turn'], turn)
        j.act('tea_menu', item='lychee', on=False)
        self.assertEqual(st(j)['menu_off'], ['lychee', 'pearls'])
        j.act('tea_menu', item='pearls', on=True)
        self.assertEqual(st(j)['menu_off'], ['lychee'])
        validate_state(j.state)

    def test_works_before_opening(self):
        j = Journey('milk_tea')
        j.c['open'] = False
        j.act('tea_menu', item='jelly', on=False)
        self.assertEqual(st(j)['menu_off'], ['jelly'])

    def test_bad_requests_change_nothing(self):
        j = Journey('milk_tea')
        unchanged(self, j, 'tea_menu', item='nope', on=False)
        unchanged(self, j, 'tea_menu', item='pearls', on='off')
        unchanged(self, j, 'tea_menu', item='pearls')
        unchanged(self, j, 'tea_menu', item='thai', on=False)  # locked at skill level 1

    def test_at_least_one_tea_stays_on(self):
        j = Journey('milk_tea')
        j.act('tea_menu', item='milk', on=False)
        j.act('tea_menu', item='black', on=False)
        unchanged(self, j, 'tea_menu', item='matcha', on=False)
        # A tea that unlocks later does not count at level 1.
        self.assertFalse(boba.menu_ok(j.c, {'milk', 'black', 'matcha'}))

    def test_tampered_menu_is_rejected(self):
        for bad in (['pearls', 'pearls'], ['nope'], 'pearls', ['milk', 'black', 'matcha']):
            j = Journey('milk_tea')
            st(j)['menu_off'] = bad
            with self.assertRaises(GameError):
                validate_state(j.state)

    def test_new_orders_never_use_items_that_are_off(self):
        off = {'pearls', 'milk', 'jelly', 'lychee', 'foam', 'q3', 'pudding'}
        for total in (0, 12, 40, 95):
            j = Journey('milk_tea')
            b = st(j)
            b['total'] = total
            b['menu_off'] = [x for x in boba.ING if x in off and boba.unlocked(j.c, x)]
            validate_state(j.state)
            base = j.task
            for i in range(160):
                t = copy.deepcopy(base)
                t['id'] = f'milk_tea-0001-{i % 12:02d}-{total}-{i}'
                t['changes'] = []
                t['usual'] = False
                if i % 3 == 0:
                    t['walkin'] = None
                    t['npc'] = f'milk_tea_npc_{i % 3 + 1:02d}'
                    b['notebook'][t['npc']] = dict(usual=dict(base='milk', flavor='lychee', toppings=['pearls', 'jelly'], size='L', sugar=50, ice='normal'), visits=4, day=1)
                else:
                    t['walkin'] = dict(boba.WALKINS[i % len(boba.WALKINS)])
                boba.setup_task(j.state, j.c, t)
                n = t['needs']
                used = {n['base'], n['flavor'], *n['toppings']} - {None}
                self.assertFalse(used & set(b['menu_off']), (total, n))
                self.assertEqual(t['needs'], boba.derive(t))

    def test_set_cups_from_surprises_follow_the_menu(self):
        j = Journey('milk_tea')
        j.act('tea_menu', item='pearls', on=False)
        j.act('tea_menu', item='milk', on=False)
        t = boba.spawn(j.state, j.c, fixed=dict(base='milk', flavor=None, toppings=['pearls'], size='M', sugar=50, ice='normal'), count_quota=False)
        self.assertNotEqual(t['needs']['base'], 'milk')
        self.assertEqual(t['needs']['toppings'], [])
        validate_state(j.state)

    def test_order_already_taken_stays_valid(self):
        j = Journey('milk_tea')
        t = j.task
        tid = t['id']
        fix_order(j, t, dict(base='milk', flavor=None, toppings=['pearls'], size='M', sugar=50, ice='little'))
        j.act('ask', task=tid)
        j.act('tea_menu', item='pearls', on=False)
        validate_state(j.state)
        self.assertEqual(j.get(tid)['needs']['toppings'], ['pearls'])
        for action, payload in boba.solution(j.get(tid))[:-1]:
            j.act(action, **payload)
        r = j.act('tea_serve', task=tid, confirm=True)
        self.assertIn('nhận ly', r['message'])

    def test_off_items_are_not_needed_in_stock(self):
        j = Journey('milk_tea')
        for l in j.c['life']['pantry']:
            if l['item'] in ('pearls', 'matcha'):
                l['qty'] = 0
        ids = lambda: {w['id'] for w in boba.warnings(j.c)}
        care = lambda: ' '.join(r['text'] for r in boba.care(j.c))
        self.assertIn('pearls', ids())
        self.assertIn('Matcha', care())
        j.act('tea_menu', item='pearls', on=False)
        j.act('tea_menu', item='matcha', on=False)
        self.assertNotIn('pearls', ids())
        self.assertNotIn('Matcha', ' '.join(w['text'] for w in boba.warnings(j.c)))
        self.assertNotIn('Trân châu đen: chưa nấu', care())

    def test_swap_offers_only_items_on_the_menu(self):
        j = Journey('milk_tea')
        t = j.task
        fix_order(j, t, dict(base='milk', flavor=None, toppings=['popping'], size='M', sugar=50, ice='little'))
        for x in ('jelly', 'pearls', 'foam'):
            j.act('tea_menu', item=x, on=False)
        self.assertIsNone(boba.swap_to(j.c, t, 'popping'))


class Patience(unittest.TestCase):
    """The counter's own fairness (par, half speed while building, the bell), measured with
    PATIENCE_FACTOR at 1.0 so the exact points show; FactorComposes checks the real factor on top."""
    def setUp(self):
        p = mock.patch.object(pt, 'PATIENCE_FACTOR', 1.0)
        p.start()
        self.addCleanup(p.stop)

    def queue(self):
        j = Journey('milk_tea')
        j.c['life']['mode'] = 'normal'
        st(j)['mod'] = 'students'  # 2 points a beat for the queue
        self.assertEqual(boba.rate(j.c), 2)
        tid = j.task['id']
        other = next(t for t in j.c['tasks'] if t['id'] != tid and t['status'] == 'new' and not t.get('group'))
        other['patience'] = 90
        j.act('ask', task=tid)
        return j, tid, other['id']

    def test_longer_cups_get_more_beats(self):
        short = dict(base='milk', flavor=None, toppings=[], size='M', sugar=50, ice='normal')
        long = dict(base='milk', flavor='peach', toppings=['pearls', 'jelly', 'foam'], size='L', sugar=50, ice='normal')
        self.assertEqual(boba.par(short), 8)
        self.assertEqual(boba.par(long), 16)
        # Still a challenge: a few spare beats over the fewest taps a cup needs.
        taps = lambda n: 6 + len(n['toppings']) + (1 if n['flavor'] else 0)
        self.assertLessEqual(boba.par(long) - taps(long), 6)

    def test_queue_drains_at_half_speed_while_building(self):
        j, tid, oid = self.queue()
        n = j.get(tid)['needs']
        j.act('tea_cup', task=tid, size=n['size'])  # not building yet: full speed
        self.assertEqual(j.get(oid)['patience'], 88)
        j.act('tea_add', task=tid, item=n['base'])  # hands-on step on a cup on the counter
        self.assertEqual(j.get(oid)['patience'], 87)
        j.act('tea_ice', task=tid, level=n['ice'])
        self.assertEqual(j.get(oid)['patience'], 86)
        j.act('tea_wait')  # standing around: full speed again
        self.assertEqual(j.get(oid)['patience'], 84)

    def test_guest_at_the_counter_loses_half_as_fast_past_par_while_building(self):
        j, tid, _ = self.queue()
        t = j.get(tid)
        n = t['needs']
        j.act('tea_cup', task=tid, size=n['size'])
        t = j.get(tid)
        t['beats'] = boba.par(n)
        t['patience'] = 80
        levels = ['little', 'normal', 'extra', 'none']
        seen = []
        for lv in levels:
            j.act('tea_ice', task=tid, level=lv)
            seen.append(j.get(tid)['patience'])
        self.assertEqual(seen, [80, 79, 79, 78])
        j.act('tea_wait')
        self.assertEqual(j.get(tid)['patience'], 77)

    def test_bell_and_building_stack_but_never_stop_the_clock(self):
        j, tid, oid = self.queue()
        st(j)['upgrades'].append('bell')
        n = j.get(tid)['needs']
        j.act('tea_cup', task=tid, size=n['size'])
        start = j.get(oid)['patience']
        for lv in ['little', 'normal', 'extra', 'none']:
            j.act('tea_ice', task=tid, level=lv)
        self.assertEqual(start - j.get(oid)['patience'], 2)  # 4 beats × 2 points ÷ 4

    def test_calm_mode_still_waits_for_nobody(self):
        j = Journey('milk_tea')
        j.c['life']['mode'] = 'calm'
        tid = j.task['id']
        j.act('ask', task=tid)
        before = {t['id']: t.get('patience', 100) for t in j.c['tasks']}
        n = j.get(tid)['needs']
        j.act('tea_cup', task=tid, size=n['size'])
        j.act('tea_add', task=tid, item=n['base'])
        self.assertEqual({t['id']: t.get('patience', 100) for t in j.c['tasks']}, before)



class FactorComposes(unittest.TestCase):
    """PATIENCE_FACTOR (game/patience.py) thins the counter's drain once, on top of its fairness:
    never replaced by it, never applied twice."""
    def lost(self, factor, build):
        with mock.patch.object(pt, 'PATIENCE_FACTOR', factor):
            j = Journey('milk_tea')
            j.c['life']['mode'] = 'normal'
            st(j)['mod'] = 'students'
            tid = j.task['id']
            other = next(t for t in j.c['tasks'] if t['id'] != tid and t['status'] == 'new' and not t.get('group'))
            j.act('ask', task=tid)
            n = j.get(tid)['needs']
            j.act('tea_cup', task=tid, size=n['size'])
            total = 0
            for i in range(120):
                o = j.get(other['id'])
                o['patience'] = 100
                j.act('tea_ice', task=tid, level=boba.ICES[i % 4]) if build else j.act('tea_wait')
                total += 100 - j.get(other['id'])['patience']
            return total

    def test_factor_thins_the_fair_drain_once(self):
        for build in (False, True):
            plain, factor = self.lost(1.0, build), self.lost(pt.PATIENCE_FACTOR, build)
            self.assertLess(factor, plain)
            ratio = plain / factor
            self.assertTrue(1.1 <= ratio <= 1.35, (build, plain, factor))  # about ×1.2, not ×1.44
        self.assertEqual(self.lost(1.0, False), 2 * self.lost(1.0, True))  # building halves it


if __name__ == '__main__':
    unittest.main()
