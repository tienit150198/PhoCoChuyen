"""Tour guide care loop: multi-day groups (energy, sickness), local partners, the
place notebook, the kit, booking-page reviews and old saves."""
import copy
import json
import unittest

from game import tour_trip as TT
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.helpers import Journey
from tests.test_tour_trip import good, roll, routes


def first_group(pred=lambda g, crew: True):
    for d in range(TT.FIRST_GROUP, 400):
        g = TT.group_of(d)
        if g and g['leg'] == 0 and pred(g, TT.crew(d)):
            return g
    raise AssertionError('no matching group')


def goto(j, day):
    """Open `day` with no carried jobs, so slot 0 (a group's leg on a group day) is made at the morning."""
    if j.c['open']:
        j.act('end_day', carry_event=True)
    c = j.c
    c['day'] = day
    c['tasks'] = [t for t in c['tasks'] if t['status'] in TT.DONE]
    c['active_task'] = None
    j.act('start_day')


def leg_id(day):
    return f'tour_guide-{day:04d}-00'


def G(j):
    return j.c['life']['tour']['group']


def gentle(trip):
    return min(routes(trip), key=lambda r: (TT.hard(trip, r), -len(TT.happy(trip, r)), TT.route_minutes(r)))


def steep(trip):
    return max(routes(trip), key=lambda r: (TT.hard(trip, r), 'hill' in r, TT.route_minutes(r)))


def best_angle(trip):
    return max(TT.ANGLE_IDS, key=lambda a: TT._tell_delta(trip, trip['at'], a))


def run(j, tid, pick=gentle, care='rest', until='done'):
    trip = TT.ensure(j.get(tid), j.c)
    if trip.get('care') and trip['care']['sick'] and not trip['care']['call']:
        j.act('tour_care', task=tid, option=care)
    j.act('tour_plan', task=tid, route=pick(j.get(tid)['trip']), v=2)
    for ev in TT.events_at(j.get(tid)['trip'], None):
        j.act('tour_call', task=tid, event=ev['id'], option=good(ev['id']))
    if until == 'gather':
        return None
    j.act('tour_depart', task=tid)
    while j.get(tid)['trip']['stage'] == 'stop':
        trip = j.get(tid)['trip']
        for ev in TT.events_at(trip, trip['at']):
            j.act('tour_call', task=tid, event=ev['id'], option=good(ev['id']))
        j.act('tour_tell', task=tid, angle=best_angle(trip))
        j.act('tour_next', task=tid)
    return j.act('tour_complete', task=tid, confirm=True)


def sick_morning(j, g, who):
    """Leg 2 of `g` with `who` worn out overnight (energy below 30 means sick for sure)."""
    goto(j, g['start'])
    G(j)['energy'][who] = 5
    goto(j, g['start'] + 1)
    return leg_id(g['start'] + 1)


class CalendarTests(unittest.TestCase):
    def test_calendar_is_seeded_and_legs_share_the_same_people(self):
        self.assertIsNone(TT.group_of(1))
        self.assertIsNone(TT.group_of(2))
        seen = 0
        for d in range(1, 90):
            g = TT.group_of(d)
            self.assertEqual(g, TT.group_of(d))
            if not g:
                continue
            self.assertIn(g['days'], (2, 3))
            self.assertTrue(0 <= g['leg'] < g['days'])
            leg = roll(d, 0)
            self.assertEqual(leg['group'], g)
            self.assertEqual(leg['members'], list(TT.crew(g['start'])))
            self.assertEqual(leg['members'][0], 'linh')
            self.assertTrue(TT._perfect(leg), d)
            self.assertIsNone(roll(d, 1)['group'])
            seen += g['leg'] == 0
        self.assertGreater(seen, 15)

    def test_non_leg_rolls_match_the_old_roll(self):
        for d in range(1, 40):
            for slot in range(4):
                new, old = roll(d, slot), TT.roll(d, slot, _v1(d), legacy=True)
                if new['group'] is None:
                    self.assertEqual({k: v for k, v in new.items() if k != 'group'}, old)


def _v1(day):
    from game import extra_content as data
    return data.WEATHERS[(day - 1) % 3]['id']


class GroupTests(unittest.TestCase):
    def setUp(self):
        self.g = first_group(lambda g, crew: g['days'] == 3 and any(TT.MEMBER[m].get('elder') for m in crew))
        self.elder = next(m for m in TT.crew(self.g['start']) if TT.MEMBER[m].get('elder'))
        self.j = Journey('tour_guide')

    def test_group_arrives_with_energy_and_leg_is_ready_in_the_morning(self):
        j, g = self.j, self.g
        goto(j, g['start'])
        grp = G(j)
        self.assertEqual((grp['start'], grp['days'], grp['members']), (g['start'], g['days'], list(TT.crew(g['start']))))
        self.assertEqual(grp['energy'][self.elder], 75)
        self.assertEqual(grp['energy']['linh'], 90)
        t = j.get(leg_id(g['start']))
        self.assertEqual(t['trip']['care'], dict(sick=None, call=None))
        view = public_state(j.state)['careers']['tour_guide']
        pub = next(x for x in view['tasks'] if x['id'] == t['id'])['trip']
        self.assertEqual(pub['group'], g)
        care = view['life']['tour']
        self.assertTrue(care['group']['active'])
        self.assertEqual(care['group']['leg'], 0)
        self.assertEqual(care['forecast']['id'], TT.leg_weather(g['start'] + 1))
        validate_state(json.loads(json.dumps(j.state)))

    def test_hard_days_tire_and_the_worn_out_guest_wakes_up_sick(self):
        j, g = self.j, self.g
        goto(j, g['start'])
        run(j, leg_id(g['start']), steep)
        after = dict(G(j)['energy'])
        trip = j.get(leg_id(g['start']))['trip']
        self.assertEqual(after[self.elder], 75 - TT.leg_cost(trip, self.elder))
        self.assertLess(after[self.elder], after['linh'])
        j.act('tour_partner', partner='homestay')
        goto(j, g['start'] + 1)
        self.assertEqual(G(j)['energy']['linh'], min(100, after['linh'] + 6 + 6))
        # The morning is rolled once a day: opening the same day again changes nothing.
        before = copy.deepcopy(G(j))
        TT.on_start(j.state, j.c)
        self.assertEqual(G(j), before)

    def test_sick_guest_needs_a_decision_before_the_route(self):
        j, g = self.j, self.g
        tid = sick_morning(j, g, self.elder)
        self.assertEqual((G(j)['sick'], G(j)['sick_day']), (self.elder, g['start'] + 1))
        t = j.get(tid)
        self.assertEqual(t['trip']['care'], dict(sick=self.elder, call=None))
        pub = next(x for x in public_state(j.state)['careers']['tour_guide']['tasks'] if x['id'] == tid)['trip']
        self.assertEqual([o['id'] for o in pub['care']['options']], ['rest', 'clinic', 'push'])
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('tour_plan', task=tid, route=gentle(t['trip']), v=2)
        self.assertEqual(j.state, before)
        with self.assertRaises(GameError):
            j.act('tour_care', task=tid, option='ignore')
        aid, energy = j.c['life']['tour']['kit']['aid'], G(j)['energy'][self.elder]
        self.assertEqual(energy, 5 + 6 - 4)  # the homestay was not called last night
        r = j.act('tour_care', task=tid, option='rest')
        self.assertTrue(r['correct'])
        self.assertEqual(j.c['life']['tour']['kit']['aid'], aid - 1)
        with self.assertRaises(GameError):
            j.act('tour_care', task=tid, option='clinic')
        trip = j.get(tid)['trip']
        self.assertEqual(TT.away(trip), self.elder)
        self.assertNotIn(self.elder, TT.present(trip))
        self.assertTrue(all(e['who'] != self.elder for s in range(3) for e in TT.events_at(trip, s)))
        run(j, tid)
        trip = j.get(tid)['trip']
        self.assertLessEqual(trip['tips'], len(trip['members']) - 1)
        self.assertEqual(G(j)['energy'][self.elder], energy + 30)
        self.assertEqual(G(j)['cared'], 1)
        self.assertFalse(j.get(tid).get('slips'))
        validate_state(json.loads(json.dumps(j.state)))
        goto(j, g['start'] + 2)
        self.assertNotEqual(G(j)['sick'], self.elder)

    def test_empty_first_aid_bag_means_buying_medicine(self):
        j, g = self.j, self.g
        tid = sick_morning(j, g, self.elder)
        j.c['life']['tour']['kit']['aid'] = 0
        money = j.c['money']
        r = j.act('tour_care', task=tid, option='rest')
        self.assertEqual(j.c['money'], money - 3)
        self.assertIn('3 xu', r['message'])

    def test_clinic_costs_and_keeps_the_guest_along(self):
        j, g = self.j, self.g
        tid = sick_morning(j, g, self.elder)
        money = j.c['money']
        j.act('tour_care', task=tid, option='clinic')
        self.assertEqual(j.c['money'], money - 4)
        self.assertIn(self.elder, TT.present(j.get(tid)['trip']))
        run(j, tid)
        self.assertFalse(j.get(tid).get('slips'))

    def test_pushing_a_sick_guest_is_a_safety_slip_and_they_stay_sick(self):
        j, g = self.j, self.g
        tid = sick_morning(j, g, self.elder)
        r = j.act('tour_care', task=tid, option='push')
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['mistakes'], 1)
        run(j, tid)
        t = j.get(tid)
        self.assertIn('sick_push', [x['code'] for x in t['slips']])
        self.assertTrue(any(x['safety'] for x in t['slips']))
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(t['trip']['tips'], 0)
        goto(j, g['start'] + 2)
        self.assertEqual((G(j)['sick'], G(j)['sick_day']), (self.elder, g['start'] + 2))
        self.assertEqual(j.get(leg_id(g['start'] + 2))['trip']['care']['sick'], self.elder)

    def test_tired_guests_make_a_hard_route_cost_mood(self):
        j, g = self.j, self.g
        goto(j, g['start'])
        tid = leg_id(g['start'])
        trip = j.get(tid)['trip']
        tired = [m for m in trip['members'][:2]]
        for m in tired:
            G(j)['energy'][m] = 46
        hard = next(r for r in sorted(routes(trip), key=TT.route_minutes, reverse=True) if TT.hard(trip, r))
        r = j.act('tour_plan', task=tid, route=hard, v=2)
        self.assertEqual(j.get(tid)['patience'], max(25, TT.mood_base(trip, hard) - 5 * len(tired)))
        self.assertIn('đang mệt', r['message'])

    def test_group_review_is_posted_when_the_group_leaves(self):
        j, g = self.j, self.g
        for i in range(g['days']):
            goto(j, g['start'] + i)
            j.act('tour_partner', partner='restaurant')
            if i < g['days'] - 1:
                j.act('tour_partner', partner='homestay')
            r = run(j, leg_id(g['start'] + i))
        self.assertIn('chia tay', r['message'])
        post = next(f for f in j.c['feed'] if f['source'] == f'tour-group-{g["start"]}')
        self.assertEqual(post['kind'], 'review')
        self.assertGreaterEqual(post['stars'], 4)
        self.assertTrue(G(j)['reviewed'])
        self.assertEqual(j.c['life']['tour']['reviews'][-1], post['stars'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_skipped_leg_and_uncalled_nights_lower_the_group_review(self):
        j, g = self.j, self.g
        goto(j, g['start'])
        run(j, leg_id(g['start']))
        goto(j, g['start'] + 1)  # no homestay call last night; today's leg is left undone
        goto(j, g['start'] + 2)
        j.act('end_day', carry_event=True)
        post = next(f for f in j.c['feed'] if f['source'] == f'tour-group-{g["start"]}')
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('không ai dẫn đi', post['text'])
        self.assertIn('chờ dọn phòng', post['text'])


class PartnerTests(unittest.TestCase):
    def setUp(self):
        self.g = first_group(lambda g, crew: g['days'] == 3 and TT.leg_weather(g['start'] + 1) not in ('rain', 'wind'))
        self.j = Journey('tour_guide')
        goto(self.j, self.g['start'])
        self.x = lambda: self.j.c['life']['tour']

    def test_homestay_call_speeds_recovery_and_builds_trust(self):
        j, g = self.j, self.g
        j.act('tour_partner', partner='homestay')
        with self.assertRaises(GameError):
            j.act('tour_partner', partner='homestay')
        for m in G(j)['members']:
            G(j)['energy'][m] = 50
        goto(j, g['start'] + 1)
        self.assertEqual(self.x()['partners']['homestay'], 1)
        self.assertEqual(G(j)['energy']['linh'], 50 + 6 + 6)
        for m in G(j)['members']:
            G(j)['energy'][m] = 60
        goto(j, g['start'] + 2)  # not called last night
        self.assertEqual(self.x()['partners']['homestay'], 0)
        self.assertEqual(G(j)['energy']['linh'], 60 + 6 - 4)
        with self.assertRaises(GameError):
            j.act('tour_partner', partner='homestay')  # last day: the group leaves tonight

    def test_lunch_booking_lifts_departure(self):
        j, g = self.j, self.g
        tid = leg_id(g['start'])
        j.act('tour_partner', partner='restaurant')
        run(j, tid, until='gather')
        mood = j.get(tid)['patience']
        r = j.act('tour_depart', task=tid)
        self.assertIn('Dì Năm', r['message'])
        self.assertEqual(j.get(tid)['patience'], min(100, mood + 3))
        self.assertEqual(self.x()['partners']['restaurant'], 1)
        with self.assertRaises(GameError):
            j.act('tour_partner', partner='restaurant')

    def test_no_lunch_booked_means_waiting_for_a_table(self):
        j, g = self.j, self.g
        tid = leg_id(g['start'])
        run(j, tid, until='gather')
        mood = j.get(tid)['patience']
        j.act('tour_depart', task=tid)
        self.assertEqual(j.get(tid)['patience'], max(25, mood - 4))
        with self.assertRaises(GameError):
            j.act('tour_partner', partner='restaurant')  # already left

    def test_boat_rules_price_and_ride(self):
        j, g = self.j, self.g
        with self.assertRaises(GameError):
            j.act('tour_partner', partner='boat', when='today')  # same day only for trusted partners
        with self.assertRaises(GameError):
            j.act('tour_partner', partner='boat', when='soon')
        money = j.c['money']
        j.act('tour_partner', partner='boat')
        self.assertEqual(j.c['money'], money - 8)
        self.assertEqual(G(j)['boat'], [g['start'] + 1])
        with self.assertRaises(GameError):
            j.act('tour_partner', partner='boat')
        goto(j, g['start'] + 1)
        tid = leg_id(g['start'] + 1)
        run(j, tid, until='gather')
        mood = j.get(tid)['patience']
        r = j.act('tour_depart', task=tid)
        self.assertIn('đò', r['message'])
        self.assertEqual(j.get(tid)['patience'], min(100, mood - 4 + TT.BOAT_MOOD))
        self.assertEqual(self.x()['partners']['boat'], 1)
        self.x()['partners']['boat'] = 6
        self.assertEqual(TT.boat_price(self.x()), 5)

    def test_boat_refused_in_rain_and_no_show_costs_trust(self):
        j = self.j
        wet = first_group(lambda g, crew: g['days'] >= 2 and TT.leg_weather(g['start'] + 1) in ('rain', 'wind'))
        goto(j, wet['start'])
        with self.assertRaises(GameError):
            j.act('tour_partner', partner='boat')
        dry = self.g
        j = self.j = Journey('tour_guide')
        goto(j, dry['start'])
        j.act('tour_partner', partner='boat')
        goto(j, dry['start'] + 1)  # the leg is never played
        j.act('end_day', carry_event=True)
        self.assertEqual(self.x()['partners']['boat'], 0)
        self.assertIn('ông Bảy chờ', ' '.join(G(j)['diary']))

    def test_partner_calls_need_a_group_day_and_an_open_shift(self):
        j = Journey('tour_guide')
        before = copy.deepcopy(j.state)
        for partner in ('homestay', 'restaurant', 'boat'):
            with self.assertRaises(GameError):
                j.act('tour_partner', partner=partner)
        with self.assertRaises(GameError):
            j.act('tour_partner', partner='taxi')
        self.assertEqual(j.state, before)
        j.act('end_day', carry_event=True)
        with self.assertRaises(GameError):
            j.act('tour_kit', item='aid')


class KitAndNotebookTests(unittest.TestCase):
    def test_loudspeaker_battery_and_overnight_charge(self):
        j = Journey('tour_guide')
        kit = j.c['life']['tour']['kit']
        with self.assertRaises(GameError):
            j.act('tour_kit', item='mic')  # full
        tid = j.task['id']
        run(j, tid, until='gather')
        j.act('tour_depart', task=tid)
        trip = j.get(tid)['trip']
        j.act('tour_tell', task=tid, angle=best_angle(trip))
        self.assertEqual(kit['mic'] if kit is j.c['life']['tour']['kit'] else j.c['life']['tour']['kit']['mic'], 100 - TT.MIC_USE)
        j.act('tour_next', task=tid)
        j.c['life']['tour']['kit']['mic'] = 4
        trip = j.get(tid)['trip']
        mood = j.get(tid)['patience']
        r = j.act('tour_tell', task=tid, angle=best_angle(trip))
        self.assertIn('Loa hết pin', r['message'])
        self.assertEqual(j.get(tid)['patience'], max(25, min(100, mood + TT._tell_delta(trip, trip['at'], best_angle(trip))) - 4))
        j.act('tour_kit', item='mic')
        with self.assertRaises(GameError):
            j.act('tour_kit', item='mic')
        self.assertEqual(j.c['life']['tour']['kit']['mic'], 4)
        j.act('end_day', carry_event=True)
        self.assertEqual(j.c['life']['tour']['kit'], dict(j.c['life']['tour']['kit'], mic=100, charging=False))

    def test_first_aid_bag_refill_and_flag_mending(self):
        j = Journey('tour_guide')
        kit = lambda: j.c['life']['tour']['kit']  # noqa: E731
        money = j.c['money']
        j.act('tour_kit', item='aid')
        self.assertEqual((kit()['aid'], j.c['money']), (6, money - 2 * TT.AID_PRICE))
        with self.assertRaises(GameError):
            j.act('tour_kit', item='aid')
        with self.assertRaises(GameError):
            j.act('tour_kit', item='flag')
        run(j, j.task['id'])
        self.assertEqual(kit()['flag'], 100 - 10)
        kit()['flag'] = 20
        tid = next(t['id'] for t in j.c['tasks'] if t['status'] not in TT.DONE)
        run(j, tid, until='gather')
        mood = j.get(tid)['patience']
        r = j.act('tour_depart', task=tid)
        self.assertIn('Cờ dẫn đoàn', r['message'])
        self.assertEqual(j.get(tid)['patience'], max(25, mood - 4))
        money = j.c['money']
        j.act('tour_kit', item='flag')
        self.assertEqual((kit()['flag'], j.c['money']), (100, money - TT.FLAG_FIX))
        with self.assertRaises(GameError):
            j.act('tour_kit', item='rope')

    def test_heat_care_uses_the_first_aid_bag(self):
        d, s = next((d, s) for d in range(3, 80) for s in range(1, 4)
                    if any(e['id'] == 'heat' for e in roll(d, s)['events']))
        j = Journey('tour_guide', slot=s, day=d)
        tid = j.task['id']
        kit = j.c['life']['tour']['kit']
        kit['aid'] = 1
        run(j, tid)
        self.assertEqual(j.c['life']['tour']['kit']['aid'], 0)

    def test_notebook_opens_a_story_then_a_hidden_spot(self):
        j = Journey('tour_guide')
        tid = j.task['id']
        run(j, tid, until='gather')
        j.act('tour_depart', task=tid)
        trip = j.get(tid)['trip']
        pid = trip['route'][0]
        know = j.c['life']['tour']['know']
        know[pid] = TT.KNOW_AT[0]
        mood = j.get(tid)['patience']
        angle = best_angle(trip)
        delta = TT._tell_delta(trip, 0, angle)
        self.assertGreater(delta, 0)
        r = j.act('tour_tell', task=tid, angle=angle)
        self.assertIn(TT.KNOW[pid][0], r['message'])
        self.assertEqual(j.get(tid)['patience'], min(100, mood + delta + 2) if mood + delta <= 100 else 100)
        self.assertEqual(j.c['life']['tour']['know'][pid], TT.KNOW_AT[0] + 1)
        j.act('tour_next', task=tid)
        trip = j.get(tid)['trip']
        pid2 = trip['route'][1]
        j.c['life']['tour']['know'][pid2] = TT.KNOW_AT[1]
        angle = best_angle(trip)
        if TT._tell_delta(trip, 1, angle) > 0:
            r = j.act('tour_tell', task=tid, angle=angle)
            self.assertIn(TT.KNOW[pid2][1], r['message'])
        view = public_state(j.state)['careers']['tour_guide']['life']['tour']['know']
        self.assertEqual(next(k for k in view if k['id'] == pid)['level'], 1)

    def test_a_dull_telling_teaches_nothing(self):
        j = Journey('tour_guide')
        tid = j.task['id']
        run(j, tid, until='gather')
        j.act('tour_depart', task=tid)
        trip = j.get(tid)['trip']
        worst = min(TT.ANGLE_IDS, key=lambda a: TT._tell_delta(trip, 0, a))
        if TT._tell_delta(trip, 0, worst) <= 0:
            j.act('tour_tell', task=tid, angle=worst)
            self.assertNotIn(trip['route'][0], j.c['life']['tour']['know'])


class ReviewTests(unittest.TestCase):
    def test_finished_trips_feed_the_booking_page(self):
        j = Journey('tour_guide')
        tid = j.task['id']
        run(j, tid)
        post = next(f for f in j.c['feed'] if f.get('source') == tid and f['kind'] == 'review')
        self.assertEqual(j.c['life']['tour']['reviews'], [post['stars']])

    def test_a_featured_guide_gets_one_extra_booking(self):
        j = Journey('tour_guide')
        j.c['life']['tour']['reviews'] = [5, 5, 5, 4, 5]
        goto(j, 20)
        today = [t for t in j.c['tasks'] if t['day'] == 20]
        self.assertEqual(j.c['life']['tour']['featured'], 20)
        pace = {'calm': 2, 'festival': 4}.get(j.c['life']['mode'], 3)
        self.assertEqual(len(today), min(4, pace + 1))
        self.assertTrue(public_state(j.state)['careers']['tour_guide']['life']['tour']['rating']['featured'])
        validate_state(json.loads(json.dumps(j.state)))
        j2 = Journey('tour_guide')
        j2.c['life']['tour']['reviews'] = [5, 3, 4, 3, 5]
        goto(j2, 20)
        self.assertEqual(j2.c['life']['tour']['featured'], 0)


class SaveTests(unittest.TestCase):
    def test_old_save_gets_a_care_record_and_old_trips_keep_their_roll(self):
        g = first_group(lambda g, crew: g['days'] >= 2)
        j = Journey('tour_guide', slot=0, day=g['start'] + 1)
        tid = j.task['id']
        legacy = TT.roll(j.task['day'], 0, j.task['weather'], legacy=True)
        self.assertNotEqual(legacy['members'], roll(j.task['day'], 0)['members'])
        trip = dict(legacy, stage='plan', route=[], at=-1, told={}, calls={}, clock=0, spent=0, fund_left=legacy['fund'], wallet=0,
                    commission=0, base=0, stamps=[], notes=[], reward=0, tips=0)
        j.get(tid)['trip'] = trip
        s = copy.deepcopy(j.state)
        del s['careers']['tour_guide']['life']['tour']
        with self.assertRaises(GameError):
            validate_state(copy.deepcopy(s))
        s = migrate_state(s)
        validate_state(s)
        j.state = s
        self.assertEqual(j.c['life']['tour'], TT.fresh_care())
        run(j, tid, pick=lambda trip: max(routes(trip), key=lambda r: len(TT.happy(trip, r))))
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertNotIn('care', j.get(tid)['trip'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_tampering_is_rejected(self):
        g = first_group(lambda g, crew: g['days'] == 3 and any(TT.MEMBER[m].get('elder') for m in crew))
        j = Journey('tour_guide')
        tid = sick_morning(j, g, next(m for m in TT.crew(g['start']) if TT.MEMBER[m].get('elder')))
        j.act('tour_partner', partner='homestay')
        validate_state(json.loads(json.dumps(j.state)))
        tour = lambda s: s['careers']['tour_guide']['life']['tour']  # noqa: E731
        trip = lambda s: next(t for t in s['careers']['tour_guide']['tasks'] if t['id'] == tid)['trip']  # noqa: E731
        edits = [lambda s: tour(s)['kit'].update(mic=101), lambda s: tour(s)['kit'].update(charging='yes'),
                 lambda s: tour(s)['partners'].update(boat=11), lambda s: tour(s)['partners'].update(taxi=1),
                 lambda s: tour(s)['know'].update(moon=1), lambda s: tour(s).update(reviews=[6]),
                 lambda s: tour(s).update(extra=1), lambda s: tour(s)['group'].update(start=g['start'] + 1),
                 lambda s: tour(s)['group']['members'].append('tom' if 'tom' not in tour(s)['group']['members'] else 'nam'),
                 lambda s: tour(s)['group']['energy'].update(linh=150), lambda s: tour(s)['group'].update(sick='linh'),
                 lambda s: tour(s)['group'].update(call='hug'), lambda s: tour(s)['group']['called'].append(g['start'] + 2),
                 lambda s: tour(s)['group']['legs'].append(g['start'] + 1), lambda s: tour(s)['group']['rode'].append(g['start']),
                 lambda s: trip(s).update(care=None), lambda s: trip(s)['care'].update(sick='linh'),
                 lambda s: trip(s)['care'].update(call='hug'), lambda s: trip(s).update(stage='gather'),
                 lambda s: trip(s).update(group=None)]
        for i, edit in enumerate(edits):
            s = json.loads(json.dumps(j.state))
            edit(s)
            with self.assertRaises(GameError, msg=i):
                validate_state(s)


if __name__ == '__main__':
    unittest.main()
