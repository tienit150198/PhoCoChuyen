"""Tour guide v2 trip ("Chuyến đi"): group wishes, weather and closures,
route order, fund, story angles, on-the-road situations and save safety."""
import copy
import itertools
import json
import math
import unittest

from game import tour_trip as TT
from game.content import make_task
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey


def roll(day, slot):
    t = make_task('tour_guide', day, slot, 1)
    return TT.roll(day, TT.slot_of(t), t['weather'])


def routes(trip, sizes=(3, 4, 5)):
    """Every allowed route (one allowed order per set of places)."""
    out = []
    for n in sizes:
        for combo in itertools.combinations(TT.PLACE_IDS, n):
            order = next((list(o) for o in itertools.permutations(combo) if TT.check_route(trip, list(o)) is None), None)
            if order:
                out.append(order)
    return out


def best_route(trip):
    return max(routes(trip), key=lambda r: (len(TT.happy(trip, r)), -TT.route_minutes(r)))


def find(pred, days=range(1, 60), slots=range(4)):
    for d in days:
        for s in slots:
            if pred(roll(d, s)):
                return d, s
    raise AssertionError('no matching trip rolled')


def good(eid):
    return TT.INCIDENT[eid]['options'][0]['id']


def fans(trip, angle):
    return sum(TT.MEMBER[m]['angle'] == angle for m in trip['members'])


def start(j, tid, route=None, late='call'):
    trip = TT.ensure(copy.deepcopy(j.get(tid)))
    j.act('tour_plan', task=tid, route=route or best_route(trip), v=2)
    if j.get(tid)['trip']['late']:
        j.act('tour_call', task=tid, event='late', option=late)
    j.act('tour_depart', task=tid)


def walk(j, tid, pick=good, until=None):
    """Handle each stop (situations, then the angle most of the group likes) until `until` or the end."""
    while j.get(tid)['trip']['stage'] == 'stop' and (until is None or j.get(tid)['trip']['at'] < until):
        t = j.get(tid)['trip']
        for ev in TT.events_at(t, t['at']):
            j.act('tour_call', task=tid, event=ev['id'], option=pick(ev['id']))
        j.act('tour_tell', task=tid, angle=max(TT.ANGLE_IDS, key=lambda a: fans(t, a)))
        j.act('tour_next', task=tid)


def play(j, tid, pick=good, route=None):
    start(j, tid, route, late=pick('late'))
    walk(j, tid, pick)
    return j.act('tour_complete', task=tid, confirm=True)


def pub_task(j, tid):
    return next(t for t in public_state(j.state)['careers']['tour_guide']['tasks'] if t['id'] == tid)


def task_in(state, tid):
    return next(x for x in state['careers']['tour_guide']['tasks'] if x['id'] == tid)


def pricey(trip):
    """An allowed route whose tickets leave less than a taxi ride (12 xu) in the fund."""
    return next((r for r in sorted(routes(trip), key=TT.route_fee, reverse=True) if TT.route_fee(r) + 12 > trip['fund']), None)


class TourTripTests(unittest.TestCase):
    def test_rolls_are_deterministic_and_always_have_a_happy_route(self):
        for day in range(1, 61):
            for slot in range(6):
                a, b = roll(day, slot), roll(day, slot)
                self.assertEqual(a, b)
                self.assertTrue(TT._perfect(a), (day, slot))
                self.assertEqual(a['members'][0], 'linh')
                self.assertEqual(len(a['events']), a['tier'])
                for ev in a['events']:
                    inc = TT.INCIDENT[ev['id']]
                    self.assertTrue(not inc['who'] or ev['who'] in a['members'])
                    self.assertTrue(not inc.get('weather') or a['weather'] in inc['weather'])
                    self.assertLessEqual(inc.get('tier', 1), a['tier'])

    def test_difficulty_grows_with_day(self):
        easy, hard = roll(1, 0), roll(8, 1)
        self.assertEqual((easy['tier'], len(easy['members']), len(easy['events']), easy['late']), (1, 4, 1, None))
        self.assertEqual((hard['tier'], len(hard['members']), len(hard['events'])), (3, 7, 3))
        self.assertIsNotNone(hard['late'])
        self.assertTrue(any(x['reason'] != 'Tạm đóng vì thời tiết' for x in hard['closed']))
        self.assertLess(hard['fund'], easy['fund'])
        self.assertLess(hard['limit'], easy['limit'])

    def test_full_trip_pays_fee_saving_and_tips(self):
        j = Journey('tour_guide')
        tid = j.task['id']
        money = j.c['money']
        r = play(j, tid)
        t = j.get(tid)
        trip = t['trip']
        self.assertEqual((t['status'], t['mistakes']), ('completed', 0))
        self.assertEqual(trip['reward'], TT.BASE_FEE + TT.saving(trip))
        self.assertEqual(trip['tips'], len(trip['members']))
        led = [x for x in j.c['ops']['finance']['ledger'] if x['ref'] == tid]
        self.assertTrue(any(x['category'] == 'revenue' and x['amount'] == trip['reward'] for x in led))
        self.assertTrue(any(x['category'] == 'tip' and x['amount'] == trip['tips'] for x in led))
        self.assertEqual(j.c['money'], money + sum(x['amount'] for x in led))
        self.assertEqual(trip['stamps'], trip['route'])
        self.assertIn('Khép chuyến', r['message'])
        validate_state(json.loads(json.dumps(j.state)))
        with self.assertRaises(GameError):
            j.act('tour_complete', task=tid, confirm=True)

    def test_route_rules(self):
        d, s = find(lambda r: r['weather'] == 'rain')
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        before = copy.deepcopy(j.state)
        for route in (['river', 'cafe', 'museum'], ['museum', 'market'], ['museum', 'museum', 'cafe'], ['museum', 'market', 'craft'],
                      ['museum', 'garden', 'market', 'cafe', 'craft', 'food'], ['gate', 'cafe', 'museum'], 'cafe', None):
            with self.assertRaises(GameError, msg=route):
                j.act('tour_plan', task=tid, route=route, v=2)
            self.assertEqual(j.state, before)
        trip = dict(roll(1, 0), weather='heat', closed=[])
        self.assertIn('Nắng gắt', TT.check_route(trip, ['garden', 'river', 'hill', 'cafe']))
        self.assertIsNone(TT.check_route(dict(trip, weather='sun'), ['garden', 'river', 'hill', 'cafe']))
        trip = dict(roll(1, 0), weather='sun', closed=[])
        self.assertIn('quỹ', TT.check_route(dict(trip, fund=5), ['museum', 'craft', 'cafe']))
        self.assertIn('phút', TT.check_route(dict(trip, limit=60), ['hill', 'temple', 'river']))
        self.assertIn('nghỉ chân', TT.check_route(trip, ['museum', 'market', 'craft']))

    def test_route_order_changes_walking_time(self):
        self.assertNotEqual(TT.route_minutes(['hill', 'temple', 'market']), TT.route_minutes(['temple', 'hill', 'market']))
        self.assertEqual(TT.leg('museum', 'garden'), TT.leg('garden', 'museum'))
        trip = dict(roll(1, 0), weather='sun', closed=[], limit=100)
        self.assertIsNone(TT.check_route(trip, ['temple', 'museum', 'garden', 'hill']))
        self.assertIn('phút', TT.check_route(trip, ['hill', 'temple', 'garden', 'museum']))

    def test_wishes_set_the_starting_mood(self):
        trip = dict(roll(1, 0), weather='sun', closed=[])
        bad_r = next(r for r in routes(trip) if len(TT.happy(trip, r)) < len(trip['members']))
        self.assertGreater(TT.mood_base(trip, best_route(trip)), TT.mood_base(trip, bad_r))
        elders = dict(trip, members=['linh', 'binh', 'sau', 'na'])
        self.assertLess(TT.mood_base(elders, ['hill', 'cafe', 'market']), TT.mood_base(elders, ['temple', 'cafe', 'market']))

    def test_hidden_until_it_happens(self):
        d, s = find(lambda r: r['tier'] == 3 and any(e['stop'] == 0 for e in r['events']))
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        view = pub_task(j, tid)['trip']
        self.assertEqual((view['stage'], view['events'], view['log']), ('plan', [], []))
        text = json.dumps(view, ensure_ascii=False)
        trip = TT.ensure(copy.deepcopy(j.get(tid)))
        for ev in trip['events'] + [trip['late']]:
            self.assertNotIn(TT.INCIDENT[ev['id']]['title'], text)
        self.assertNotIn('lines', text)
        j.act('tour_plan', task=tid, route=best_route(trip), v=2)
        view = pub_task(j, tid)['trip']
        self.assertEqual([e['id'] for e in view['events']], ['late'])
        self.assertTrue(all(set(o) == {'id', 'label', 'cost'} for o in view['events'][0]['options']))
        self.assertNotIn('outcome', view['events'][0])
        j.act('tour_call', task=tid, event='late', option='call')
        self.assertEqual(pub_task(j, tid)['trip']['log'][0]['chosen'], 'call')
        j.act('tour_depart', task=tid)
        view = pub_task(j, tid)['trip']
        now = {e['id'] for e in TT.events_at(j.get(tid)['trip'], 0)}
        self.assertEqual({e['id'] for e in view['events']}, now)
        later = {e['id'] for e in j.get(tid)['trip']['events'] if e['stop'] > 0} - now
        for eid in later:
            self.assertNotIn(TT.INCIDENT[eid]['title'], json.dumps(view, ensure_ascii=False))
        self.assertIsNone(view['here']['line'])

    def test_order_of_actions_is_enforced(self):
        d, s = find(lambda r: r['late'] is not None and any(e['stop'] == 0 for e in r['events']))
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        for action, payload in (('tour_depart', {}), ('tour_call', dict(event='late', option='call')), ('tour_tell', dict(angle='fun')),
                                ('tour_next', {}), ('tour_complete', dict(confirm=True))):
            with self.assertRaises(GameError, msg=action):
                j.act(action, task=tid, **payload)
        trip = TT.ensure(copy.deepcopy(j.get(tid)))
        j.act('tour_plan', task=tid, route=best_route(trip), v=2)
        before = copy.deepcopy(j.state)
        for action, payload in (('tour_plan', dict(route=best_route(trip), v=2)), ('tour_depart', {}), ('tour_tell', dict(angle='fun')),
                                ('tour_count', dict(visitor='linh')), ('tour_photo', dict(object='cat')),
                                ('tour_call', dict(event='late', option='hack')), ('tour_call', dict(event='bus', option='walk'))):
            with self.assertRaises(GameError, msg=action):
                j.act(action, task=tid, **payload)
            self.assertEqual(j.state, before)
        r = j.act('tour_call', task=tid, event='late', option='leave')
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['mistakes'], 1)
        with self.assertRaises(GameError):
            j.act('tour_call', task=tid, event='late', option='call')
        j.act('tour_depart', task=tid)
        with self.assertRaises(GameError):
            j.act('tour_next', task=tid)
        j.act('tour_tell', task=tid, angle='fun')
        with self.assertRaises(GameError):
            j.act('tour_tell', task=tid, angle='photo')
        with self.assertRaises(GameError):
            j.act('tour_next', task=tid)
        with self.assertRaises(GameError):
            j.act('tour_complete', task=tid, confirm=True)

    def test_commission_pays_but_costs_trust(self):
        d, s = find(lambda r: any(e['id'] == 'commission' for e in r['events']))
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        play(j, tid, pick=lambda eid: 'push' if eid == 'commission' else good(eid))
        t = j.get(tid)
        self.assertEqual(t['trip']['commission'], 15)
        self.assertEqual(t['mistakes'], 1)
        self.assertIn('commission', t['trip']['notes'])
        led = [x for x in j.c['ops']['finance']['ledger'] if x['ref'] == tid and x['category'] == 'commission']
        self.assertEqual([x['amount'] for x in led], [15])
        validate_state(json.loads(json.dumps(j.state)))
        j2 = Journey('tour_guide', slot=s, day=d)
        play(j2, j2.task['id'])
        self.assertEqual(j2.get(tid)['trip']['commission'], 0)
        self.assertIn('honest', j2.get(tid)['trip']['notes'])
        self.assertGreater(j2.get(tid)['patience'], t['patience'])

    def test_fund_overspend_comes_from_wallet(self):
        d, s = find(lambda r: any(e['id'] == 'bus' for e in r['events']) and pricey(r))
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        route = pricey(TT.ensure(copy.deepcopy(j.get(tid))))
        money = j.c['money']
        play(j, tid, pick=lambda eid: 'taxi' if eid == 'bus' else good(eid), route=route)
        trip = j.get(tid)['trip']
        over = TT.route_fee(route) + trip['spent'] - trip['fund']
        self.assertGreater(over, 0)
        led = [x for x in j.c['ops']['finance']['ledger'] if x['ref'] == tid]
        self.assertEqual(sum(-x['amount'] for x in led if x['category'] == 'tour_cost'), over)
        self.assertEqual((trip['wallet'], trip['fund_left'], TT.saving(trip)), (over, 0, 0))
        self.assertEqual(j.c['money'], money + sum(x['amount'] for x in led))

    def test_broke_guide_cannot_pay_extra(self):
        d, s = find(lambda r: any(e['id'] == 'bus' for e in r['events']) and pricey(r))
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        start(j, tid, pricey(TT.ensure(copy.deepcopy(j.get(tid)))))
        stop = next(e['stop'] for e in j.get(tid)['trip']['events'] if e['id'] == 'bus')
        walk(j, tid, until=stop)
        j.c['ops']['finance']['opening_balance'] -= j.c['money']
        j.c['money'] = 0
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('tour_call', task=tid, event='bus', option='taxi')
        self.assertEqual(j.state, before)
        self.assertTrue(j.act('tour_call', task=tid, event='bus', option='walk')['correct'])

    def test_temple_dress_check_only_on_temple_routes(self):
        d, s = find(lambda r: r['dress'] and 'temple' not in TT.closed_ids(r))
        trip = roll(d, s)
        with_temple = next(r for r in routes(trip) if 'temple' in r)
        without = next(r for r in routes(trip) if 'temple' not in r)
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        play(j, tid, route=with_temple)
        self.assertEqual(j.get(tid)['trip']['calls'].get('dress'), 'scarf')
        s2 = copy.deepcopy(j.state)
        del task_in(s2, tid)['trip']['calls']['dress']
        with self.assertRaises(GameError):
            validate_state(s2)
        j = Journey('tour_guide', slot=s, day=d)
        play(j, tid, route=without)
        self.assertNotIn('dress', j.get(tid)['trip']['calls'])

    def test_angle_choice_moves_mood(self):
        j = Journey('tour_guide')
        tid = j.task['id']
        start(j, tid)
        t = j.get(tid)
        trip = t['trip']
        t['patience'] = 60
        place = TT.PLACE[trip['route'][0]]
        worst = min(TT.ANGLE_IDS, key=lambda a: fans(trip, a))
        fit = any(TT.BEST_ANGLE[tag] == worst for tag in place['tags'])
        expect = 3 * fans(trip, worst) - (len(trip['members']) - fans(trip, worst)) + (2 if fit else 0)
        r = j.act('tour_tell', task=tid, angle=worst)
        self.assertEqual(j.get(tid)['patience'], 60 + expect)
        self.assertEqual(r['correct'], expect > 0)
        self.assertIn(place['lines'][worst], r['message'])

    def test_running_late_lowers_mood(self):
        d, s = find(lambda r: r['late'] is not None and any(e['id'] == 'bus' for e in r['events']))
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        trip = TT.ensure(copy.deepcopy(j.get(tid)))
        route = max(routes(trip), key=TT.route_minutes)
        start(j, tid, route, late='wait')
        pick = lambda eid: 'wait' if eid == 'bus' else good(eid)  # noqa: E731
        walk(j, tid, pick, until=len(route) - 1)
        t = j.get(tid)['trip']
        for ev in TT.events_at(t, t['at']):
            j.act('tour_call', task=tid, event=ev['id'], option=pick(ev['id']))
        j.act('tour_tell', task=tid, angle=max(TT.ANGLE_IDS, key=lambda a: fans(t, a)))
        mood = j.get(tid)['patience']
        over = j.get(tid)['trip']['clock'] - t['limit']
        self.assertGreater(over, 0)
        r = j.act('tour_next', task=tid)
        self.assertIn(f'Trễ {over} phút', r['message'])
        self.assertEqual(j.get(tid)['patience'], max(25, mood - 2 * math.ceil(over / 5)))
        self.assertEqual(pub_task(j, tid)['trip']['over'], over)

    def test_tamper_is_rejected(self):
        j = Journey('tour_guide', slot=1, day=6)
        tid = j.task['id']
        trip = TT.ensure(copy.deepcopy(j.get(tid)))
        j.act('tour_plan', task=tid, route=best_route(trip), v=2)
        edits = [lambda t: t.update(members=t['members'][:-1]), lambda t: t.update(fund=99), lambda t: t.update(closed=[]),
                 lambda t: t.update(route=[TT.closed_ids(t)[0]] + t['route'][1:]), lambda t: t.update(base=t['base'] - 1),
                 lambda t: t.update(stage='ready'), lambda t: t['calls'].update(bus='walk'), lambda t: t.update(fund_left=t['fund_left'] + 5),
                 lambda t: t['notes'].append('fake'), lambda t: t['notes'].append('honest'), lambda t: t.update(events=[]),
                 lambda t: t.update(clock=t['clock'] + 30), lambda t: t.update(reward=80), lambda t: t.update(commission=15)]
        for i, edit in enumerate(edits):
            s = copy.deepcopy(j.state)
            edit(task_in(s, tid)['trip'])
            with self.assertRaises(GameError, msg=i):
                validate_state(s)
        s = copy.deepcopy(j.state)
        task_in(s, tid)['route'] = ['museum', 'market', 'cafe']
        with self.assertRaises(GameError):
            validate_state(s)

    def test_v1_route_without_flag_keeps_v1_rules(self):
        j = Journey('tour_guide')
        tid = j.task['id']
        self.assertEqual(pub_task(j, tid)['trip']['stage'], 'plan')
        j.solve(tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertNotIn('trip', t)
        self.assertNotIn('trip', pub_task(j, tid))
        validate_state(j.state)

    def test_v2_blocks_v1_actions(self):
        j = Journey('tour_guide')
        tid = j.task['id']
        trip = TT.ensure(copy.deepcopy(j.get(tid)))
        j.act('tour_plan', task=tid, route=best_route(trip), v=2)
        before = copy.deepcopy(j.state)
        for action, payload in (('tour_count', dict(visitor='linh')), ('tour_locate', dict(location='info')), ('tour_photo', dict(object='cat'))):
            with self.assertRaises(GameError):
                j.act(action, task=tid, **payload)
            self.assertEqual(j.state, before)

    def test_every_situation_has_tradeoffs(self):
        self.assertGreaterEqual(len(TT.INCIDENTS), 12)
        for inc in TT.INCIDENTS:
            self.assertEqual(len(inc['options']), 3, inc['id'])
            self.assertFalse(inc['options'][0]['mistake'], inc['id'])
            self.assertTrue(any(o['mistake'] or o['mood'] < 0 for o in inc['options'][1:]), inc['id'])
            self.assertEqual(len({(o['mood'], o['minutes'], o['cost'], o['mistake'], o['commission']) for o in inc['options']}), 3, inc['id'])
            for o in inc['options']:
                self.assertTrue(o['note'] is None or o['note'] in TT.NOTES)


class TourConsequenceTests(unittest.TestCase):
    """What went wrong on the road reaches the group leader's reaction, the review and the pay."""

    def trip(self, pred=lambda r: True, picks=None, route=None):
        d, s = find(pred)
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        picks = picks or {}
        pick = lambda eid: picks.get(eid, good(eid))
        trip = TT.ensure(copy.deepcopy(j.get(tid)))
        start(j, tid, route(trip) if route else None, late=pick('late'))
        walk(j, tid, pick)
        money = j.c['money']
        r = j.act('tour_complete', task=tid, confirm=True)
        t = j.get(tid)
        review = next(f for f in j.c['feed'] if f.get('source') == tid and f.get('kind') == 'review')
        return j, t, review, j.c['money'] - money, r

    def test_good_trip_full_pay(self):
        j, t, review, delta, r = self.trip()
        self.assertFalse(t.get('slips'))
        self.assertGreaterEqual(review['stars'], 4)
        self.assertGreaterEqual(delta, t['trip']['reward'] + t['trip']['tips'])

    def test_commission_push_costs_pay_and_tips(self):
        has = lambda r: any(e['id'] == 'commission' for e in r['events'])
        j, t, review, delta, r = self.trip(has, dict(commission='push'))
        self.assertEqual([x['code'] for x in t['slips']], ['commission'])
        self.assertLessEqual(review['stars'], 3)
        self.assertIn('tiệm lưu niệm', review['text'])
        self.assertIn(t['reaction']['kind'], ('grumble', 'discount', 'refund'))
        cut = t['reaction']['cut']
        self.assertEqual(t['trip']['tips'], 0)
        self.assertEqual(delta, t['trip']['reward'] - cut)
        self.assertIn('Trưởng đoàn Linh', r['message'])
        from game import consequences as cq
        before = j.c['money']
        cq.react(j.state, j.c, t, t['trip']['reward'])
        self.assertEqual(j.c['money'], before)
        validate_state(json.loads(json.dumps(j.state)))

    def test_severity_scales(self):
        has = lambda eid: (lambda r: any(e['id'] == eid for e in r['events']))
        _, small, r1, _, _ = self.trip(has('commission'), dict(commission='quiet'))
        _, big, r2, _, _ = self.trip(has('commission'), dict(commission='push'))
        self.assertEqual([x['sev'] for x in small['slips']], [1])
        self.assertEqual([x['sev'] for x in big['slips']], [2])
        self.assertGreater(r1['stars'], r2['stars'])

    def test_lost_guest_left_alone_is_a_safety_case(self):
        j, t, review, delta, r = self.trip(lambda r: any(e['id'] == 'lost' for e in r['events']), dict(lost='go'))
        self.assertTrue(t['slips'][0]['safety'])
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(review['stars'], 1)
        self.assertEqual(delta, 0)
        self.assertTrue(any(f.get('report') and f.get('source') == t['id'] for f in j.c['feed']))
        self.assertTrue(any(x['src'] == t['id'] and x['script'] == 'slip_safety_inspect' for x in j.c['incidents']['follow']))
        validate_state(json.loads(json.dumps(j.state)))

    def test_late_return_and_missed_wishes(self):
        slow = lambda trip: max(routes(trip), key=TT.route_minutes)
        j, t, review, delta, r = self.trip(lambda r: any(e['id'] == 'bus' for e in r['events']), dict(bus='wait', late='wait'), slow)
        over = t['trip']['clock'] - t['trip']['limit']
        if over > 0:
            self.assertIn('late_return', [x['code'] for x in t['slips']])
            self.assertIn(f'trễ {over} phút', review['text'])
        dull = lambda trip: min(routes(trip), key=lambda x: (len(TT.happy(trip, x)), TT.route_minutes(x)))
        j, t, review, delta, r = self.trip(lambda r: r['tier'] >= 2, route=dull)
        self.assertIn('wishes', [x['code'] for x in t['slips']])
        self.assertLessEqual(review['stars'], 4)


if __name__ == '__main__':
    unittest.main()
