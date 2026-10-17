"""📅 Đơn hẹn giờ: scheduled parcels in the courier career (game/careers/delivery.py, APPT_*)."""
import copy
import json
import unittest

from game import courier
from game.engine import GameError, public_state, validate_state
from game.careers import delivery as D
from tests.helpers import Journey


def plain(t, day):
    """A scheduled parcel with nothing else going on (no dog, refusal, move, COD, rain, wrong weight)."""
    return (D.appt_eligible(t) and D.appt_chosen(t['id']) and day >= D.APPT_MIN_DAY and not t['_dog'] and not t['_bomb']
            and not t['needs']['cod'] and not t['needs']['unit_missing'] and t['_w'] == t['needs']['w']
            and D.weather(day) == 'sun' and t['needs']['size'] == 'S')


def find(pred, days=range(2, 120)):
    for day in days:
        for slot in range(12):
            t = D.make_task(day, slot, 1)
            if pred(t, day):
                return day, slot
    raise AssertionError('no matching task')


def journey(pred=plain, days=range(2, 120)):
    day, slot = find(pred, days)
    j = Journey('delivery', slot=slot, day=day)
    data(j)['desk'].update(day=day, plan=[], fired=0)        # no random surprise
    tid = j.task['id']
    j.act('ask', task=tid)
    return j, tid


def data(j):
    return j.c['ext']['data']


def ride(j, *route):
    j.act('dl_plan', route=list(route))
    for _ in route:
        j.act('dl_ride')


def to_door(j, tid):
    """Weigh, pack and load at the pick-up, then ride to the customer's door."""
    t = j.get(tid)
    n = t['needs']
    if data(j)['at'] != n['pickup']:
        ride(j, n['pickup'])
    j.act('dl_check', task=tid)
    for item in D._needs_pack(j.get(tid), j.c['day']):
        j.act('dl_pack', task=tid, item=item)
    j.act('dl_load', task=tid)
    ride(j, n['dest'])


def wait_until(j, minute):
    while data(j)['clock'] < minute:
        j.act('dl_wait')


def appt(j, tid):
    return j.get(tid)['appt']


def review(j, tid):
    return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['feedback']['task'] == tid)


class WindowGeneration(unittest.TestCase):
    def test_window_is_deterministic_rounded_and_sized(self):
        t = D.make_task(5, 1, 1)
        a = D.appt_window(t['id'], 5, 12, t['needs'])
        self.assertEqual(a, D.appt_window(t['id'], 5, 12, copy.deepcopy(t['needs'])))
        for day in (2, 6, 9, 10, 25):
            for slot in range(6):
                t = D.make_task(day, slot, 1)
                n = t['needs']
                start, end = D.appt_window(t['id'], day, 7, n)
                self.assertEqual(start % 5, 0)
                self.assertEqual(end - start, 20 if day >= 10 else 30)
                ride = (D.dist('hub', n['pickup']) + D.dist(n['pickup'], n['dest'])) * D.MPU[D.weather(day)]
                self.assertGreaterEqual(start, 7 + ride + D.APPT_SLACK)
                self.assertLessEqual(start, 7 + ride + D.STAIRS.get(n['dest'], 0) + D.APPT_SLACK + 5 * D.APPT_SPREAD + 5)
        # The answer on the phone and the choice to book a time are fixed per order.
        t = D.make_task(9, 3, 1)
        self.assertEqual(D.appt_answer(t, 9), D.appt_answer(copy.deepcopy(t), 9))
        self.assertEqual(D.appt_chosen(t['id']), D.appt_chosen(t['id']))

    def test_share_of_orders(self):
        total = eligible = booked = 0
        for day in range(2, 200):
            for slot in range(4):
                t = D.make_task(day, slot, 1)
                total += 1
                if D.appt_eligible(t):
                    eligible += 1
                    booked += D.appt_chosen(t['id'])
        self.assertTrue(0.35 <= booked / eligible <= 0.55, booked / eligible)
        self.assertTrue(0.12 <= booked / total <= 0.3, booked / total)

    def test_only_eligible_orders_from_day_two(self):
        day, slot = find(lambda t, d: D.appt_eligible(t) and D.appt_chosen(t['id']), days=range(2, 120))
        t = D.make_task(day, slot, 1)
        D._appt_plan(dict(day=1), t)
        self.assertNotIn('appt', t, 'no booked times on the first day')
        D._appt_plan(dict(day=day), t)
        self.assertIn('appt', t)
        for day in range(2, 30):
            for slot in range(4):
                t = D.make_task(day, slot, 1)
                n = t['needs']
                if n['kind'] == 'food' or n['by'] or t['_away'] or n['safe_drop']:
                    self.assertFalse(D.appt_eligible(t))
        j, tid = journey()
        a = appt(j, tid)
        self.assertEqual((a['day'], a['base'], a['call'], a['done'], a['late'], a['waited']), (j.c['day'], 0, None, None, 0, 0))
        self.assertEqual((a['start'], a['end']), D.appt_window(tid, j.c['day'], 0, j.get(tid)['needs']))

    def test_window_visible_before_accept_and_in_the_order_text(self):
        day, slot = find(plain)
        j = Journey('delivery', slot=slot, day=day)
        view = public_state(j.state)['careers']['delivery']['tasks'][0]
        self.assertIsNone(view['needs'])
        self.assertEqual(view['appt']['start'], j.task['appt']['start'])
        j.act('ask', task=j.task['id'])
        self.assertIn('📅 Khách hẹn nhận ' + D.appt_text(j.task['appt']), D.known_request(j.c, j.task))


class Outcomes(unittest.TestCase):
    def test_on_time_pays_the_bonus_and_a_happy_line(self):
        j, tid = journey()
        to_door(j, tid)
        a = appt(j, tid)
        self.assertLess(data(j)['clock'], a['start'], 'the shortest ride arrives before the window')
        door = data(j)['clock']
        j.act('dl_appt', task=tid, how='wait')
        stairs = D.STAIRS.get(j.get(tid)['needs']['dest'], 0)
        self.assertEqual(data(j)['clock'] + stairs, a['start'], 'waits until the window opens at the flat door')
        self.assertEqual(appt(j, tid)['waited'], data(j)['clock'] - door)
        base = D._fee(j.c, j.get(tid))
        money = j.c['money']
        r = j.act('dl_deliver', task=tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['appt']['done'], 'on_time')
        self.assertEqual(t['run']['fee'], base + D.APPT_BONUS)
        self.assertGreaterEqual(j.c['money'], money + base + D.APPT_BONUS)
        self.assertIn('📅 Đúng khung hẹn', r['message'])
        self.assertIn(f'+{D.APPT_BONUS} xu', r['message'])
        self.assertEqual(j.c['metrics'].get('deliveries_on_appt'), 1)
        crit = {x['key']: x['score'] for x in review(j, tid)['feedback']['criteria']}
        self.assertEqual(crit['time'], 5)
        validate_state(json.loads(json.dumps(j.state)))

    def test_early_door_is_refused_and_costs_a_minute(self):
        j, tid = journey()
        to_door(j, tid)
        before = data(j)['clock']
        r = j.act('dl_deliver', task=tid)
        self.assertTrue(r.get('early'))
        self.assertIn('Bấm chuông không ai mở', r['message'])
        self.assertEqual(data(j)['clock'], before + 1)
        self.assertNotEqual(j.get(tid)['status'], 'completed')
        self.assertIsNone(appt(j, tid)['done'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_wait_is_bounded_and_only_at_the_door(self):
        j, tid = journey()
        n = j.get(tid)['needs']
        if data(j)['at'] != n['pickup']:
            ride(j, n['pickup'])
        j.act('dl_check', task=tid)
        for item in D._needs_pack(j.get(tid), j.c['day']):
            j.act('dl_pack', task=tid, item=item)
        j.act('dl_load', task=tid)
        with self.assertRaises(GameError):
            j.act('dl_appt', task=tid, how='wait')          # not at the customer's door
        ride(j, n['dest'])
        a = appt(j, tid)
        data(j)['clock'] = a['start'] - D.STAIRS.get(n['dest'], 0) - D.APPT_WAIT_MAX - 5
        with self.assertRaises(GameError):
            j.act('dl_appt', task=tid, how='wait')          # too long: deliver something else first
        with self.assertRaises(GameError):
            j.act('dl_appt', task=tid, how='sleep')

    def test_calling_ahead_answers(self):
        seen = set()
        for answer in D.APPT_CALLS:
            pred = (lambda ans: lambda t, d: plain(t, d) and D.appt_answer(t, d) == ans)(answer)
            try:
                j, tid = journey(pred)
            except AssertionError:
                continue
            seen.add(answer)
            j.act('dl_appt', task=tid, how='call')                 # from anywhere, before the window
            self.assertEqual(appt(j, tid)['call'], answer)
            with self.assertRaises(GameError):
                j.act('dl_appt', task=tid, how='call')             # once
            to_door(j, tid)
            if answer == 'early':
                base = D._fee(j.c, j.get(tid))
                r = j.act('dl_deliver', task=tid)
                t = j.get(tid)
                self.assertEqual((t['status'], t['appt']['done']), ('completed', 'early'))
                self.assertEqual(t['run']['fee'], base, 'early with permission: no on-time bonus, no deduction')
                self.assertIn('không có thưởng đúng hẹn', r['message'])
            elif answer == 'neighbour':
                self.assertTrue(j.act('dl_deliver', task=tid).get('early'))
                j.act('dl_safedrop', task=tid, confirm=True)
                t = j.get(tid)
                self.assertEqual((t['status'], t['appt']['done']), ('completed', 'drop'))
                self.assertNotIn('handed_over', [x['code'] for x in t.get('slips', [])])
                self.assertEqual(t['mistakes'], 0)
            else:
                self.assertTrue(j.act('dl_deliver', task=tid).get('early'))
            validate_state(json.loads(json.dumps(j.state)))
        self.assertLessEqual({'early', 'later'}, seen)

    def test_plain_call_before_the_window_asks_to_come_early(self):
        j, tid = journey()
        r = j.act('dl_call', task=tid)
        a = appt(j, tid)
        self.assertEqual(a['call'], D.appt_answer(j.get(tid), a['day']))
        self.assertNotIn('Có nhà, cứ tới nha', r['message'])
        with self.assertRaises(GameError):
            j.act('dl_appt', task=tid, how='call')
        validate_state(json.loads(json.dumps(j.state)))

    def test_late_deduction_is_bounded_and_explained(self):
        for over, cut in ((5, D.APPT_LATE), (D.APPT_LATE_STEP + 10, D.APPT_LATE_MORE)):
            j, tid = journey()
            to_door(j, tid)
            a = appt(j, tid)
            wait_until(j, a['end'] + over - D.STAIRS.get(j.get(tid)['needs']['dest'], 0))
            base = D._fee(j.c, j.get(tid))
            money = j.c['money']
            r = j.act('dl_deliver', task=tid)
            t = j.get(tid)
            self.assertEqual(t['appt']['done'], 'late')
            self.assertGreaterEqual(t['appt']['late'], over)
            self.assertIn('late', [x['code'] for x in t.get('slips', [])])
            # Either the flat deduction or the customer's cut, never below 0 and never out of the wallet.
            if t['reaction']['cut']:
                self.assertEqual(t['run']['fee'], base - t['reaction']['cut'])
            else:
                self.assertEqual(t['run']['fee'], max(4, base - cut))
                self.assertIn(f'−{cut} xu phí ship', r['message'])
            self.assertGreaterEqual(t['run']['fee'], 0)
            self.assertGreaterEqual(j.c['money'], money)
            crit = {x['key']: x['score'] for x in review(j, tid)['feedback']['criteria']}
            self.assertLessEqual(crit['time'], 4)
            validate_state(json.loads(json.dumps(j.state)))
        # The order text warns about it before it can happen.
        j, tid = journey()
        self.assertIn(f'trễ thì phí ship −{D.APPT_LATE} xu', D.known_request(j.c, j.get(tid)))
        self.assertEqual(D.content()['appt']['late_more'], D.APPT_LATE_MORE)

    def test_client_cannot_send_times_or_amounts(self):
        j, tid = journey()
        to_door(j, tid)
        a = copy.deepcopy(appt(j, tid))
        j.act('dl_appt', task=tid, how='wait', start=0, end=2000, minutes=1, bonus=999)
        self.assertEqual((appt(j, tid)['start'], appt(j, tid)['end']), (a['start'], a['end']))
        base = D._fee(j.c, j.get(tid))
        j.act('dl_deliver', task=tid, bonus=999, fee=999, appt={'done': 'on_time'})
        self.assertEqual(j.get(tid)['run']['fee'], base + D.APPT_BONUS)
        # A save whose window was moved is refused.
        j, tid = journey()
        bad = copy.deepcopy(j.state)
        t = next(x for x in bad['careers']['delivery']['tasks'] if x['id'] == tid)
        t['appt']['start'] -= 5
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(j.state)
        t = next(x for x in bad['careers']['delivery']['tasks'] if x['id'] == tid)
        t['appt']['done'] = 'on_time'
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_route_estimate_marks_the_window(self):
        j, tid = journey()
        n = j.get(tid)['needs']
        j.act('dl_plan', route=[n['pickup'], n['dest']] if n['pickup'] != 'hub' else [n['dest']])
        rows = public_state(j.state)['careers']['delivery']['data']['eta']
        mark = rows[-1]['appt'][0]
        self.assertEqual((mark['task'], mark['start'], mark['end']), (tid, appt(j, tid)['start'], appt(j, tid)['end']))
        self.assertEqual(mark['state'], 'early')
        self.assertGreater(mark['by'], 0)

    def test_carry_over_books_a_new_time(self):
        j, tid = journey()
        old = copy.deepcopy(appt(j, tid))
        j.act('end_day')
        j.act('start_day')
        a = appt(j, tid)
        self.assertEqual((a['day'], a['base'], a['call'], a['done']), (old['day'] + 1, 0, None, None))
        self.assertEqual((a['start'], a['end']), D.appt_window(tid, a['day'], 0, j.get(tid)['needs']))
        validate_state(json.loads(json.dumps(j.state)))


class OldSaves(unittest.TestCase):
    def test_tasks_without_a_window_play_as_before(self):
        j, tid = journey()
        del j.get(tid)['appt']                       # an order made by an older build
        validate_state(json.loads(json.dumps(j.state)))
        to_door(j, tid)
        r = j.act('dl_deliver', task=tid)
        self.assertNotIn('early', r)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertNotIn('appt', j.get(tid))

    def test_old_carried_order_is_not_given_a_window(self):
        j, tid = journey()
        del j.get(tid)['appt']
        j.act('end_day')
        j.act('start_day')
        self.assertNotIn('appt', j.get(tid))

    def test_window_left_by_an_older_build_shift_is_ignored_until_rebooked(self):
        """Rolled back and forward: an older build opened the next shift without booking a new time."""
        j, tid = journey()
        to_door(j, tid)
        j.get(tid)['run']['day'] += 1                 # what the older build's on_start did
        validate_state(json.loads(json.dumps(j.state)))
        r = j.act('dl_deliver', task=tid)
        self.assertNotIn('early', r)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertIsNone(t['appt']['done'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_window_stays_outside_what_older_builds_check(self):
        """An older build compares run keys, needs and FIXED with the regenerated order and checks the data keys:
        the window is in none of them, so a save that used it still loads there."""
        j, tid = journey()
        t = j.get(tid)
        self.assertEqual(set(t['run']), set(D._empty_run()))
        self.assertEqual(t['needs'], D.make_task(t['day'], int(tid.rsplit('-', 1)[1]), t['created_turn'])['needs'])
        self.assertNotIn('appt', D.FIXED)
        self.assertFalse(any(k.startswith('appt') for k in data(j)['stats']))
        self.assertLessEqual(set(data(j)), set(D._extend(D.initial())) | {'drive'})


class CourierContract(unittest.TestCase):
    def setUp(self):
        from tests.test_bank import story
        self.s = story(200)
        self.s['journey']['unlocked'].append('delivery')

    def deliver(self, seq, appt=None, kind='parcel'):
        c = self.s['careers']['delivery']
        c['metrics']['deliveries_done'] = seq
        t = dict(id='parcel', status='completed', needs=dict(kind=kind), run=dict(outcome='delivered', late=0), mistakes=0)
        if appt:
            t['appt'] = dict(done=appt, late=12 if appt == 'late' else 0)
        c['tasks'] = [t]
        courier.on_action(self.s, 'delivery', 'dl_deliver', {'task': 'parcel'}, {})

    def test_on_time_scheduled_counts_twice_for_express(self):
        self.s['journey']['courier'] = dict(v=1, seq=3, completed=3, delivered=9, earned=60, gear=[], active=None,
                                            history=[dict(seq=i, kind='local', day=1, fee=24, deduction=4, bonus=20, cost=3)
                                                     for i in (1, 2, 3)])
        courier.action(self.s, 'jr_ship_accept', dict(kind='express', confirm=True, pay='cash'))
        self.deliver(1, 'on_time')
        self.assertEqual(courier.public(self.s)['active']['done'], 2)
        self.deliver(2, 'late')
        a = courier.public(self.s)['active']
        self.assertEqual((a['done'], a['bad']), (3, 1))
        self.deliver(3, 'on_time')
        self.deliver(4, 'on_time')                     # capped at the target
        self.assertEqual(courier.public(self.s)['active']['done'], 5)
        courier.validate(self.s)

    def test_other_contracts_count_once(self):
        courier.action(self.s, 'jr_ship_accept', dict(kind='local', confirm=True, pay='cash'))
        self.deliver(1, 'on_time')
        self.assertEqual(courier.public(self.s)['active']['done'], 1)
        courier.validate(self.s)


if __name__ == '__main__':
    unittest.main()
