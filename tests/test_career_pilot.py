"""Phi công Cánh Cò (plugin career pilot): the briefing and the fuel plan, fog waited out on
the ground, the walk-around and its defects, the before-start checklist, the passenger
announcement, decisions on the way, holding and the alternate, the two approach gates and
the go-around, the pay, hidden information, determinism, save validation and old saves."""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests.helpers import Journey
from game.careers import kit, PLUGINS
from game.content import make_task
from game.engine import GameError, migrate_state, new_state, public_state, validate_state

PL = PLUGINS.get('pilot')


def settle_odd(j, command, scripts, answer=None):
    """Answer an open encounter the way a careful crew member does, round after round."""
    from game.careers import air_odd as ao
    for _ in range(4 * ao.MAX_ROUNDS):             # answering one may bring the next one due
        ev = j.c['ext']['data']['odd']['ev']
        if not ev:
            return
        x = ao.script(scripts, ev['script'])
        j.act(command, **(answer or best_answer)(x))


def quiet(j):
    """No encounter planned for the rest of today."""
    from game.careers import air_odd as ao
    odd = ao.ensure(j.c['ext']['data'])
    odd.update(day=j.c['day'], plan=[], fired=0, ev=None)


def best_answer(x):
    k = x['kind']
    if k == 'bargain':
        return dict(tone='firm', say=['rule', 'alt'], to='company', n=x['limit'])
    say = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'corner': ['speak', 'rule'], 'demand': ['rule', 'alt']}[k]
    to = 'company' if k in ('charm', 'harass', 'corner') else 'self' if x['rank'] == 'kin' else 'crew'
    return dict(tone='firm', say=say, to=to)


def sky_answer(sk):
    add = 0 if sk['gust'] < 10 else 5 if sk['gust'] < 16 else 10
    return dict(wipers=True, brake='med' if sk['brake'] != 'poor' else 'max', add=add,
                dodge={'left': 'right', 'right': 'left', None: 'keep'}[sk['cell']], go='divert' if sk['brake'] == 'poor' else 'land')


def find(pick, days=range(2, 80), slots=range(0, 6)):
    """The first (day, slot) whose generated hop passes `pick`."""
    return next((d, s) for d in days for s in slots if pick(PL.make_task(d, s, 1)))


class Base(unittest.TestCase):
    def setUp(self):
        if PL is None:
            raise unittest.SkipTest('pilot is filtered out by MNL_CAREERS')
        self.j = Journey('pilot')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, pick):
        day, slot = find(pick)
        j = Journey('pilot', slot=slot, day=day)
        quiet(j)                                   # these tests look at one job: no encounters today
        return j

    def brief(self, j, tid, kg=None):
        j.act('ask', task=tid)
        n = j.get(tid)['needs']
        j.act('pl_fuel', task=tid, kg=n['fuel']['need'] if kg is None else kg)
        if n['wx'] == 'fog':
            j.act('pl_fog', task=tid, wait=True)

    def walk(self, j, tid):
        for pt in PL.POINTS:
            j.act('pl_check', task=tid, point=pt['id'])
            t = j.get(tid)
            if t['found'] and not t['handled']:
                j.act('pl_defect', task=tid, how='fix' if PL.DEFECTS[t['found']]['own'] else 'report')

    def start(self, j, tid):
        for sid in PL.ORDER:
            j.act('pl_switch', task=tid, id=sid)
        if j.get(tid)['delay']:
            j.act('pl_pa', task=tid, option='clear')
        j.act('pl_takeoff', task=tid)

    def land(self, j, tid):
        t = j.get(tid)
        if t['stage'] == 'cruise':
            ev = t['needs']['event']
            j.act('pl_decide', task=tid, option={'turb': 'belts', 'cell': 'deviate', 'medical': ev.get('want')}[ev['kind']])
        t = j.get(tid)
        if PL._arrival_problem(t):
            j.act('pl_arrive', task=tid, how='hold' if t['fuel'] >= t['needs']['fuel']['plan'] + PL.HOLD else 'divert')
        sk = j.c['ext']['data'].get('sky')
        if sk and sk['task'] == tid and sk['set'] is None:
            j.act('pl_sky', task=tid, **sky_answer(sk))
        for _ in range(8):
            t = j.get(tid)
            if t['stage'] != 'approach':
                break
            j.act('pl_gate' if PL._current_gate(t)['stable'] else 'pl_around', task=tid)
        return j.act('pl_park', task=tid)

    def fly(self, j, tid):
        self.settle_desk(j)
        self.brief(j, tid)
        self.walk(j, tid)
        self.start(j, tid)
        return self.land(j, tid)

    def settle_desk(self, j):
        ev = j.c['ext']['data']['desk']['ev']
        if ev:
            j.act('pl_desk', option=kit.desk_script(PL.DESK, ev['script'])['default'])
        settle_odd(j, 'pl_odd', PL.ODD)


class Spec(Base):
    def test_spec_shape(self):
        s = PL.SPEC
        self.assertEqual((s['id'], s['prefix']), ('pilot', 'pl_'))
        self.assertTrue(5 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertEqual(len(s['staff']), 4)
        self.assertEqual(len(s['stories']), 3)
        self.assertEqual(len(s['review_asides']), 4)
        self.assertTrue(5 <= len(s['situations']) <= 8)
        for x in s['situations']:
            for opt in x['options']:
                self.assertTrue(2 <= len(opt['perspectives']) <= 3, opt['id'])
        for k in s['no_tick'] + s['free_actions'] + tuple(PL.ACTIONS):
            self.assertTrue(k.startswith('pl_'), k)
        self.assertTrue(s['employment']['postings'])
        for post in s['employment']['postings']:
            for q in post['questions']:
                self.assertTrue(q in s['employment']['questions'] or q in ('mistake', 'conflict', 'weakness'), q)

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'mô phỏng lại', 'giả lập', 'nhiệm vụ')
        blob = json.dumps([PL.DESK, PL.SITUATIONS, PL.REG_STORY, PL.ARC, PL.INTRO, PL.SPEC['meta'], PL.EVENTS, PL.WX], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_registered(self):
        from game.content import CAREERS
        self.assertIn('pilot', CAREERS)
        from game import employment as emp
        self.assertTrue(emp.required('pilot'))


class Determinism(Base):
    def test_hops_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 20):
            for slot in range(0, 8):
                a, b = PL.make_task(day, slot, 1), PL.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                # Only lists and dicts: a stored task still equals its regenerated original after JSON.
                self.assertEqual(json.loads(json.dumps(a['needs'])), a['needs'])
                self.assertEqual(make_task('pilot', day, slot, 1)['id'], f'pilot-{day:04d}-{slot:02d}')

    def test_first_day_is_gentle(self):
        kinds = [PL.make_task(1, s, 1)['kind'] for s in range(3)]
        self.assertEqual(kinds, ['flight', 'flight', 'tech'])
        t = PL.make_task(1, 0, 1)
        self.assertEqual((t['needs']['wx'], t['needs']['defect'], t['needs']['event']), ('clear', 'cover', None))
        self.assertTrue(all(g['stable'] for g in t['needs']['gates'][0]))
        self.assertEqual(PL.make_task(1, 1, 1)['needs']['gates'][0][0]['bad'], 'fast')

    def test_second_approach_is_always_stable_and_fuel_options_make_sense(self):
        for day in range(1, 60):
            for slot in range(0, 6):
                n = PL.make_task(day, slot, 1)['needs']
                self.assertTrue(all(g['stable'] for g in n['gates'][1]))
                self.assertLessEqual(sum(not g['stable'] for g in n['gates'][0]), 1)
                f = n['fuel']
                self.assertEqual(f['options'], sorted(set(f['options'])))
                self.assertIn(f['need'], f['options'])
                self.assertLess(f['options'][0], f['plan'])

    def test_days_mix_the_weather(self):
        kinds = {PL.make_task(d, s, 1)['kind'] for d in range(2, 40) for s in range(6)}
        self.assertEqual(kinds, set(PL.KINDS))
        self.assertTrue({PL.mod_of(d)['id'] for d in range(2, 40)} >= {'storms', 'fog', 'wind'})


class Brief(Base):
    def test_hidden_until_the_briefing(self):
        j = self.j
        tid = j.c['active_task']
        view = next(t for t in public_state(j.state)['careers']['pilot']['tasks'] if t['id'] == tid)
        self.assertIsNone(view['needs'])
        j.act('ask', task=tid)
        view = next(t for t in public_state(j.state)['careers']['pilot']['tasks'] if t['id'] == tid)
        n = view['needs']
        self.assertNotIn('need', n['fuel'])
        self.assertIsNone(n['defect'])          # the pitot cover is found on the walk, not in the briefing
        self.assertTrue(all(g is None for row in n['gates'] for g in row))
        self.assertNotIn('stable', json.dumps(view))

    def test_too_little_fuel_is_refused(self):
        j = self.j
        tid = j.c['active_task']
        j.act('ask', task=tid)
        f = j.get(tid)['needs']['fuel']
        r = j.act('pl_fuel', task=tid, kg=f['options'][0])
        self.assertFalse(r['correct'])
        t = j.get(tid)
        self.assertIsNone(t['fuel'])
        self.assertEqual(t['mistakes'], 1)
        self.assertEqual(t['slips'][0]['code'], 'fuel_low')
        j.act('pl_fuel', task=tid, kg=f['need'])
        self.assertEqual(j.get(tid)['stage'], 'walk')

    def test_full_tanks_on_a_full_aircraft_are_over_weight(self):
        j = self.at(lambda t: t['needs']['full'] and t['needs']['wx'] != 'fog')
        tid = j.c['active_task']
        j.act('ask', task=tid)
        r = j.act('pl_fuel', task=tid, kg=PL.TANKS)
        self.assertFalse(r['correct'])
        self.assertIsNone(j.get(tid)['fuel'])

    def test_full_tanks_on_a_light_hop_are_accepted_but_wasteful(self):
        j = self.at(lambda t: not t['needs']['full'] and t['needs']['wx'] in ('clear', 'cloud'))
        tid = j.c['active_task']
        j.act('ask', task=tid)
        j.act('pl_fuel', task=tid, kg=PL.TANKS)
        t = j.get(tid)
        self.assertEqual(t['fuel'], PL.TANKS)
        self.assertEqual(t['slips'][0]['code'], 'heavy')

    def test_extra_holding_fuel_on_a_fine_day_is_no_mistake(self):
        j = self.at(lambda t: t['needs']['wx'] == 'clear' and not t['needs']['full'])
        tid = j.c['active_task']
        j.act('ask', task=tid)
        f = j.get(tid)['needs']['fuel']
        j.act('pl_fuel', task=tid, kg=f['plan'] + PL.HOLD)
        t = j.get(tid)
        self.assertTrue(t['extra'])
        self.assertEqual(t['mistakes'], 0)

    def test_fog_is_waited_out_on_the_ground(self):
        j = self.at(lambda t: t['kind'] == 'fog')
        tid = j.c['active_task']
        self.brief(j, tid)
        t = j.get(tid)
        self.assertEqual((t['fog'], t['delay'], t['stage']), ('wait', PL.DELAY['fog'], 'walk'))
        self.assertIsNone(PL._arrival_problem(dict(t, stage='approach')))

    def test_fog_rushed_must_hold_or_divert(self):
        j = self.at(lambda t: t['kind'] == 'fog')
        tid = j.c['active_task']
        j.act('ask', task=tid)
        j.act('pl_fuel', task=tid, kg=j.get(tid)['needs']['fuel']['plan'])
        j.act('pl_fog', task=tid, wait=False)
        self.walk(j, tid)
        for sid in PL.ORDER:
            j.act('pl_switch', task=tid, id=sid)
        if j.get(tid)['delay']:
            j.act('pl_pa', task=tid, option='clear')
        j.act('pl_takeoff', task=tid)
        t = j.get(tid)
        if t['stage'] == 'cruise':
            j.act('pl_decide', task=tid, option=t['needs']['event'].get('want') or EV_GOOD[t['needs']['event']['kind']])
        with self.assertRaises(GameError):
            j.act('pl_gate', task=tid)
        with self.assertRaises(GameError):       # no holding fuel was loaded
            j.act('pl_arrive', task=tid, how='hold')
        j.act('pl_arrive', task=tid, how='divert')
        self.assertEqual(j.get(tid)['at'], j.get(tid)['needs']['leg']['alt'])
        self.assertIn('rush', {x['code'] for x in j.get(tid)['slips']})


EV_GOOD = {'turb': 'belts', 'cell': 'deviate'}


class Walk(Base):
    def test_pitot_cover_found_and_removed(self):
        j = self.j
        tid = j.c['active_task']
        self.brief(j, tid)
        r = j.act('pl_check', task=tid, point='wing')
        self.assertIn('pitot', r['message'])
        self.assertEqual(j.get(tid)['found'], 'cover')
        view = next(t for t in public_state(j.state)['careers']['pilot']['tasks'] if t['id'] == tid)
        self.assertEqual(view['needs']['defect']['id'], 'cover')
        for pt in ('gear', 'engine', 'hold'):
            j.act('pl_check', task=tid, point=pt)
        self.assertEqual(j.get(tid)['stage'], 'walk')    # not done while the cover is still on
        j.act('pl_defect', task=tid, how='fix')
        t = j.get(tid)
        self.assertEqual((t['stage'], t['delay'], t['mistakes']), ('start', 0, 0))

    def test_ignoring_a_defect_is_a_safety_slip_the_captain_catches(self):
        j = self.j
        tid = j.c['active_task']
        self.brief(j, tid)
        j.act('pl_check', task=tid, point='wing')
        j.act('pl_defect', task=tid, how='ignore')
        t = j.get(tid)
        self.assertEqual(t['handled'], 'caught')
        self.assertTrue(t['slips'][0]['safety'])
        self.assertGreater(t['delay'], 0)

    def test_the_engineers_defect_means_a_delay_and_an_announcement(self):
        j = self.j
        tid = next(t['id'] for t in j.c['tasks'] if t['kind'] == 'tech')
        self.brief(j, tid)
        j.act('pl_check', task=tid, point='gear')
        with self.assertRaises(GameError):
            j.act('pl_defect', task=tid, how='fix')
        j.act('pl_defect', task=tid, how='report')
        for pt in ('engine', 'wing', 'hold'):
            j.act('pl_check', task=tid, point=pt)
        for sid in PL.ORDER:
            j.act('pl_switch', task=tid, id=sid)
        with self.assertRaises(GameError):
            j.act('pl_takeoff', task=tid)
        j.act('pl_pa', task=tid, option='clear')
        j.act('pl_takeoff', task=tid)
        t = j.get(tid)
        self.assertEqual(t['delay'], PL.DELAY['tech'])
        self.assertEqual(t['patience'], 95)
        self.assertEqual(t['mistakes'], 0)


class Checklist(Base):
    def ready(self):
        j = self.j
        tid = j.c['active_task']
        self.brief(j, tid)
        self.walk(j, tid)
        return j, tid

    def test_out_of_order_is_stopped(self):
        j, tid = self.ready()
        r = j.act('pl_switch', task=tid, id='brake')
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['switches'], [])
        self.assertEqual(j.get(tid)['slips'][0]['code'], 'order')
        with self.assertRaises(GameError):
            j.act('pl_takeoff', task=tid)
        for sid in PL.ORDER:
            j.act('pl_switch', task=tid, id=sid)
        j.act('pl_takeoff', task=tid)
        self.assertEqual(j.get(tid)['stage'], 'approach')

    def test_no_announcement_needed_when_on_time(self):
        j, tid = self.ready()
        for sid in PL.ORDER:
            j.act('pl_switch', task=tid, id=sid)
        with self.assertRaises(GameError):
            j.act('pl_pa', task=tid, option='clear')

    def test_an_untrue_announcement_costs_patience_and_the_review(self):
        j = self.j
        tid = next(t['id'] for t in j.c['tasks'] if t['kind'] == 'tech')
        self.brief(j, tid)
        self.walk(j, tid)
        for sid in PL.ORDER:
            j.act('pl_switch', task=tid, id=sid)
        j.act('pl_pa', task=tid, option='hide')
        j.act('pl_takeoff', task=tid)
        t = j.get(tid)
        self.assertEqual(t['patience'], 100 - 25 - 4)   # the untrue announcement, and the mistake
        self.assertEqual(t['slips'][-1]['code'], 'untrue')
        self.land(j, tid)
        crit = {x['key']: x['score'] for x in PL.feedback(j.c, j.get(tid))['criteria']}
        self.assertEqual(crit['pax'], 2)


class Approach(Base):
    def to_approach(self, pick):
        j = self.at(pick)
        tid = j.c['active_task']
        self.brief(j, tid)
        self.walk(j, tid)
        self.start(j, tid)
        t = j.get(tid)
        if t['stage'] == 'cruise':
            ev = t['needs']['event']
            j.act('pl_decide', task=tid, option=ev.get('want') or EV_GOOD[ev['kind']])
        j.c['ext']['data']['sky'] = None          # these tests read the gates: no rain today (the sky has its own tests)
        return j, tid

    def test_going_around_when_unstable_is_right(self):
        j, tid = self.to_approach(lambda t: t['needs']['gates'][0][0]['bad'] and t['kind'] == 'flight')
        view = next(t for t in public_state(j.state)['careers']['pilot']['tasks'] if t['id'] == tid)
        self.assertEqual(len(view['needs']['gates'][0][0]['rows'][0]), 3)   # label, value, limit: never the verdict
        r = j.act('pl_around', task=tid)
        self.assertTrue(r.get('celebrate'))
        t = j.get(tid)
        self.assertEqual((t['ap'], t['gate'], t['arounds'], t['mistakes']), (1, 0, 1, 0))
        j.act('pl_gate', task=tid)
        j.act('pl_gate', task=tid)
        self.assertEqual(j.get(tid)['stage'], 'landed')
        r = j.act('pl_park', task=tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertIn(f'{j.get(tid)["flight_bonus"]} xu', r['message'])

    def test_landing_unstable_is_a_mistake(self):
        j, tid = self.to_approach(lambda t: t['needs']['gates'][0][0]['bad'] and t['kind'] == 'flight')
        r = j.act('pl_gate', task=tid)
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['slips'][-1]['code'], 'unstable')

    def test_no_runway_at_minimums_is_a_safety_slip(self):
        j, tid = self.to_approach(lambda t: t['needs']['gates'][0][1]['bad'] == 'no_rwy')
        j.act('pl_gate', task=tid)
        j.act('pl_gate', task=tid)
        t = j.get(tid)
        self.assertTrue(t['slips'][-1]['safety'])
        r = j.act('pl_park', task=tid)
        self.assertNotIn('Thưởng', r['message'])

    def test_needless_go_around_is_a_gentle_slip(self):
        j, tid = self.to_approach(lambda t: t['kind'] == 'flight' and all(g['stable'] for g in t['needs']['gates'][0]))
        j.act('pl_around', task=tid)
        self.assertEqual(j.get(tid)['slips'][-1]['code'], 'needless')
        self.assertEqual(j.get(tid)['slips'][-1]['sev'], 1)

    def test_two_go_arounds_then_the_alternate(self):
        j, tid = self.to_approach(lambda t: t['kind'] == 'flight')
        for _ in range(PL.MAX_AROUNDS):
            j.act('pl_around', task=tid)
        j.act('pl_around', task=tid)
        t = j.get(tid)
        self.assertEqual(t['at'], t['needs']['leg']['alt'])
        with self.assertRaises(GameError):          # no fuel for circling at the alternate
            j.act('pl_around', task=tid)
        j.act('pl_gate', task=tid)
        j.act('pl_gate', task=tid)
        self.assertEqual(j.get(tid)['stage'], 'landed')
        validate_state(json.loads(json.dumps(j.state)))

    def test_storm_hold_with_holding_fuel(self):
        j, tid = self.to_approach(lambda t: t['kind'] == 'storm')
        self.assertEqual(PL._arrival_problem(j.get(tid)), 'storm')
        j.act('pl_arrive', task=tid, how='hold')
        t = j.get(tid)
        self.assertEqual((t['arrive'], t['air_late']), ('hold', PL.DELAY['hold']))
        self.land(j, tid)
        self.assertEqual(j.get(tid)['mistakes'], 0)

    def test_landing_into_a_storm_is_unsafe(self):
        j, tid = self.to_approach(lambda t: t['kind'] == 'storm')
        j.act('pl_arrive', task=tid, how='land')
        self.assertTrue(j.get(tid)['slips'][-1]['safety'])


class Cruise(Base):
    def cruise(self, kind):
        j = self.at(lambda t: (t['needs']['event'] or {}).get('kind') == kind)
        tid = j.c['active_task']
        self.brief(j, tid)
        self.walk(j, tid)
        self.start(j, tid)
        self.assertEqual(j.get(tid)['stage'], 'cruise')
        return j, tid

    def test_event_is_hidden_until_the_cruise(self):
        j = self.at(lambda t: t['needs']['event'] is not None)
        tid = j.c['active_task']
        self.brief(j, tid)
        view = next(t for t in public_state(j.state)['careers']['pilot']['tasks'] if t['id'] == tid)
        self.assertIsNone(view['needs']['event'])

    def test_storm_cell_through_is_unsafe(self):
        j, tid = self.cruise('cell')
        j.act('pl_decide', task=tid, option='through')
        self.assertTrue(j.get(tid)['slips'][-1]['safety'])

    def test_turbulence_warning(self):
        j, tid = self.cruise('turb')
        j.act('pl_decide', task=tid, option='belts')
        self.assertEqual(j.get(tid)['mistakes'], 0)
        j2, tid2 = self.cruise('turb')
        j2.act('pl_decide', task=tid2, option='ignore')
        self.assertEqual(j2.get(tid2)['slips'][-1]['code'], 'turb')

    def test_medical_far_from_the_destination_diverts(self):
        j = self.at(lambda t: (t['needs']['event'] or {}).get('want') == 'divert')
        tid = j.c['active_task']
        self.brief(j, tid)
        self.walk(j, tid)
        self.start(j, tid)
        view = next(t for t in public_state(j.state)['careers']['pilot']['tasks'] if t['id'] == tid)
        self.assertIn('35 phút', view['needs']['event']['text'])
        j.act('pl_decide', task=tid, option='divert')
        t = j.get(tid)
        self.assertEqual(t['at'], t['needs']['event']['near'])
        self.land(j, tid)
        self.assertEqual(j.get(tid)['mistakes'], 0)

    def test_medical_continue_when_far_is_unsafe(self):
        j = self.at(lambda t: (t['needs']['event'] or {}).get('want') == 'divert')
        tid = j.c['active_task']
        self.brief(j, tid)
        self.walk(j, tid)
        self.start(j, tid)
        j.act('pl_decide', task=tid, option='continue')
        self.assertTrue(j.get(tid)['slips'][-1]['safety'])


class Day(Base):
    def test_a_full_first_day_by_the_book(self):
        j = self.j
        j.act('pl_intro')
        money = j.c['money']
        tids = [t['id'] for t in j.c['tasks']]
        quoted = [PL.public_task(t)['expected_bonus'] for t in j.c['tasks']]
        self.assertEqual(len(tids), 3)
        for tid in tids:
            self.fly(j, tid)
            self.assertEqual(j.get(tid)['status'], 'completed')
            self.assertEqual(j.get(tid)['mistakes'], 0)
        paid = [r['amount'] for r in j.c['ops']['finance']['ledger'] if r.get('ref') in tids and r.get('category') == 'revenue']
        self.assertEqual(paid, quoted)
        stars = [f['stars'] for f in j.c['feed'] if f.get('kind') == 'review']
        self.assertTrue(stars and min(stars) >= 4)
        self.assertEqual(self.d['logbook']['flights'], 3)
        r = j.act('end_day')
        self.assertEqual(r['summary']['job']['salary'], j.c['job']['salary'])
        self.assertEqual(r['summary']['career']['flights'], 3)
        salary = [r['amount'] for r in j.c['ops']['finance']['ledger'] if r.get('category') == 'salary']
        self.assertEqual(salary, [j.c['job']['salary']])
        self.assertGreaterEqual(j.c['money'], money + sum(quoted) + j.c['job']['salary'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_hours_are_the_crew_day(self):
        from game import dayclock as dc
        j = self.j
        self.assertEqual(dc.hours(j.c, 'pilot'), (5 * 60 + 30, 19 * 60 + 30))

    def test_a_week_keeps_the_save_valid(self):
        j = self.j
        for day in range(1, 8):
            self.assertEqual(j.c['day'], day)
            for t in [x for x in j.c['tasks'] if x['status'] not in ('completed', 'cancelled')]:
                self.fly(j, t['id'])
            validate_state(json.loads(json.dumps(j.state)))
            j.act('end_day')
            j.act('start_day')
        self.assertGreaterEqual(self.d['logbook']['flights'], 14)
        self.assertEqual(self.d['logbook']['safe'], self.d['logbook']['flights'])

    def test_story_and_regulars(self):
        j = self.j
        self.assertIsNone(self.d['arc']['due'])          # the first badge comes after the first landing
        j.act('pl_intro')
        tid = j.c['active_task']
        r = self.fly(j, tid)
        self.assertEqual(self.d['arc']['due'], 'badge')
        j.act('pl_arc')
        self.assertEqual(self.d['arc']['seen'], ['badge'])
        self.assertIn(PL.REG_STORY[PL.CAPTAIN][0], r['message'])
        self.assertEqual(self.d['regulars'][str(PL.CAPTAIN)]['visits'], 1)

    def test_every_surprise_option_is_playable(self):
        for x in PL.DESK:
            for o in x['options']:
                j = Journey('pilot')
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('pl_fuel', task=j.c['active_task'], kg=1)
                r = j.act('pl_desk', option=o['id'])
                self.assertTrue(r['message'])
                self.assertIsNone(j.c['ext']['data']['desk']['ev'])
                validate_state(json.loads(json.dumps(j.state)))

    def test_situations_are_playable(self):
        j = self.j
        for x in PL.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)


class Saves(Base):
    def test_forged_needs_are_rejected(self):
        s = copy.deepcopy(self.j.state)
        t = s['careers']['pilot']['tasks'][0]
        t['needs']['fuel']['need'] = 1
        with self.assertRaises(GameError):
            validate_state(s)

    def test_broken_task_fields_are_rejected(self):
        j = self.j
        tid = j.c['active_task']
        self.brief(j, tid)
        for key, value in (('fuel', 7), ('switches', ['brake']), ('stage', 'moon'), ('ap', 3), ('found', 'oil'),
                           ('gates_log', [dict(ap=0, g='g9', go='land')]), ('delay', -1), ('checked', ['gear', 'gear'])):
            s = copy.deepcopy(j.state)
            next(x for x in s['careers']['pilot']['tasks'] if x['id'] == tid)[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_broken_data_is_rejected(self):
        for path, value in ((('logbook', 'flights'), -2), (('arc', 'due'), 'dragon'), (('intro',), 'yes'), (('regulars',), {'9': {'visits': 1}})):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['pilot']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_old_save_without_the_airline_gains_it_and_nothing_else_changes(self):
        s = new_state()
        old = copy.deepcopy(s)
        old['careers'].pop('pilot')
        old['careers'].pop('flight_attendant', None)
        a, b = migrate_state(old), migrate_state(copy.deepcopy(s))
        for cid in b['careers']:
            if cid not in ('pilot', 'flight_attendant'):
                self.assertEqual(a['careers'][cid], b['careers'][cid], cid)
        validate_state(a)
        self.assertIn('pilot', a['careers'])
        self.assertEqual(a['careers']['pilot']['job']['status'], 'none')   # nobody is hired without applying

    def test_story_players_past_chapter_four_find_the_airline_open(self):
        from game import journey as jr
        j = jr.initial(True, 5)
        j['chapter'] = 5
        j['unlocked'] = [c for n in range(1, 6) for c in jr.CH_UNLOCKS[n] if c not in ('pilot', 'flight_attendant')]
        old = list(j['unlocked'])
        jr.upgrade(j)
        self.assertEqual(j['unlocked'][:len(old)], old)          # only added, nothing removed or reordered
        self.assertTrue({'pilot', 'flight_attendant'} <= set(j['unlocked']))
        young = jr.initial(True, 5)
        jr.upgrade(young)
        self.assertNotIn('pilot', young['unlocked'])              # chapter 1: not yet

    def test_old_data_gains_new_fields(self):
        j = self.j
        d = j.c['ext']['data']
        for k in ('intro', 'arc', 'regulars', 'today', 'log'):
            d.pop(k)
        d['logbook'].pop('holds')
        s = migrate_state(json.loads(json.dumps(j.state)))
        validate_state(s)
        j.state = s
        self.fly(j, j.c['active_task'])
        validate_state(j.state)

    def test_mid_flight_save_round_trip(self):
        j = self.j
        tid = j.c['active_task']
        self.brief(j, tid)
        self.walk(j, tid)
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        j.state = s
        self.start(j, tid)
        self.land(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_public_view_is_json(self):
        view = public_state(self.j.state)['careers']['pilot']
        json.dumps(view)
        for k in ('logbook', 'mod', 'desk', 'arc', 'intro'):
            self.assertIn(k, view['data'])


class Shell(Base):
    """The crew's own shell: airline words on duty, a departures board line per hop, passenger reviews."""
    def test_reporting_for_duty_and_another_hop_have_airline_words(self):
        j = self.j
        j.act('pl_intro')
        for t in list(j.c['tasks']):
            self.fly(j, t['id'])
        j.act('end_day')
        self.assertEqual(j.act('start_day')['message'], PL.SPEC['open_line'])
        self.settle_desk(j)
        self.assertEqual(j.act('more_work')['message'], PL.SPEC['more_line'])

    def test_every_hop_has_a_departure_time_and_a_gate(self):
        for day in range(1, 12):
            for slot in range(5):
                leg = PL.make_task(day, slot, 1)['needs']['leg']
                self.assertRegex(leg['dep'], r'^\d\d:\d\d$')
                self.assertIn(leg['gate'], range(1, 7))
                self.assertEqual(leg, PL.make_task(day, slot, 9)['needs']['leg'])

    def test_the_board_line_is_public_before_the_briefing(self):
        j = self.j
        tid = j.c['active_task']
        view = next(t for t in public_state(j.state)['careers']['pilot']['tasks'] if t['id'] == tid)
        self.assertFalse(view['known'])
        self.assertEqual(view['leg'], j.get(tid)['needs']['leg'])
        self.assertIsNone(view['needs'])

    def test_reviews_are_passengers_and_the_captain_never_a_shop(self):
        from game import feedback as fbm
        j = self.j
        j.act('pl_intro')
        for t in list(j.c['tasks']):
            self.fly(j, t['id'])
        posts = [f for f in j.c['feed'] if f.get('kind') == 'review']
        self.assertTrue(posts)
        for p in posts:
            fb = p['feedback']
            self.assertTrue(fb['own'])
            self.assertEqual(fb['status'], 'closed')
            self.assertNotRegex(p['text'].lower(), r'quán|tiệm|ly |món')
            self.assertFalse(fbm.public_post(p)['feedback']['can_report'])
        self.assertIsNone(fbm._own_voice('milk_tea'))
        validate_state(json.loads(json.dumps(j.state)))

    def test_a_bad_hop_reads_as_a_bad_hop(self):
        said = {1: set(), 5: set()}
        t = PL.make_task(3, 1, 1)
        for i in PL.VOICES:
            for s in said:
                text = PL.review_text(None, dict(t, npc=f'pilot_npc_{i + 1:02d}', slips=[]), 'regular', s, [], 7)
                self.assertTrue(text)
                self.assertNotIn('quán', text)
                said[s].add(text)
        self.assertTrue(said[1].isdisjoint(said[5]))


class Flown(Base):
    """✈️ Tự bay: the page flies the approach and sends `flown`; the gates' weather stays the server's."""
    to_approach = Approach.to_approach

    def view(self, j, tid):
        return next(t for t in public_state(j.state)['careers']['pilot']['tasks'] if t['id'] == tid)

    def test_the_cockpit_reads_the_approach_but_never_the_verdict(self):
        j, tid = self.to_approach(lambda t: t['needs']['gates'][0][0]['bad'] == 'fast' and t['kind'] == 'flight')
        fly = self.view(j, tid)['fly']
        self.assertEqual(set(fly), {'kt', 'dots', 'sink', 'wind', 'rwy'})
        self.assertGreater(fly['kt'], 120)
        self.assertTrue(fly['rwy'])
        self.assertNotIn('fly', self.view(self.j, self.j.c['active_task']))          # only once the approach is in hand
        j2, tid2 = self.to_approach(lambda t: t['needs']['gates'][0][1]['bad'] == 'no_rwy')
        self.assertFalse(self.view(j2, tid2)['fly']['rwy'])
        j3, tid3 = self.to_approach(lambda t: t['needs']['gates'][0][1]['bad'] == 'gust')
        self.assertGreater(self.view(j3, tid3)['fly']['wind'], 28)

    def test_flown_stable_out_of_a_fast_handover_is_no_mistake(self):
        j, tid = self.to_approach(lambda t: t['needs']['gates'][0][0]['bad'] == 'fast' and t['kind'] == 'flight')
        r = j.act('pl_gate', task=tid, flown=dict(stable=True))
        self.assertNotEqual(r.get('correct'), False)
        r = j.act('pl_gate', task=tid, flown=dict(stable=True, touch='soft'))
        self.assertIn('êm ru', r['message'])
        t = j.get(tid)
        self.assertEqual((t['stage'], t['mistakes'], t.get('slips') or []), ('landed', 0, []))
        r = j.act('pl_park', task=tid)
        self.assertIn(f'{j.get(tid)["flight_bonus"]} xu', r['message'])

    def test_flown_unstable_and_landed_is_the_unstable_slip(self):
        j, tid = self.to_approach(lambda t: t['kind'] == 'flight' and all(g['stable'] for g in t['needs']['gates'][0]))
        j.act('pl_gate', task=tid, flown=dict(stable=True))
        r = j.act('pl_gate', task=tid, flown=dict(stable=False, touch='firm'))
        self.assertFalse(r['correct'])
        self.assertEqual([x['code'] for x in j.get(tid)['slips']], ['unstable'])
        self.assertEqual(PL.feedback(j.c, j.get(tid))['criteria'][2]['score'], 3)

    def test_flown_unstable_go_around_is_the_right_call(self):
        j, tid = self.to_approach(lambda t: t['kind'] == 'flight' and all(g['stable'] for g in t['needs']['gates'][0]))
        r = j.act('pl_around', task=tid, flown=dict(stable=False))
        self.assertTrue(r.get('celebrate'))
        self.assertEqual((j.get(tid)['mistakes'], j.get(tid)['arounds']), (0, 1))

    def test_flown_stable_go_around_is_still_needless(self):
        j, tid = self.to_approach(lambda t: t['needs']['gates'][0][0]['bad'] == 'fast' and t['kind'] == 'flight')
        j.act('pl_around', task=tid, flown=dict(stable=True))
        self.assertEqual(j.get(tid)['slips'][-1]['code'], 'needless')

    def test_the_weather_at_the_gate_is_not_flown_away(self):
        j, tid = self.to_approach(lambda t: t['needs']['gates'][0][1]['bad'] == 'no_rwy')
        j.act('pl_gate', task=tid, flown=dict(stable=True))
        j.act('pl_gate', task=tid, flown=dict(stable=True, touch='soft'))
        self.assertEqual(j.get(tid)['slips'][-1]['code'], 'minima')
        j, tid = self.to_approach(lambda t: t['needs']['gates'][0][1]['bad'] == 'gust')
        j.act('pl_gate', task=tid, flown=dict(stable=True))
        r = j.act('pl_around', task=tid, flown=dict(stable=True))
        self.assertTrue(r.get('celebrate'))                         # 32 kt across: going around is right however it was flown
        j.act('pl_gate', task=tid, flown=dict(stable=True))
        j.act('pl_gate', task=tid, flown=dict(stable=True))
        self.assertEqual(j.get(tid)['mistakes'], 0)

    def test_firm_and_long_landings_are_remarks_not_slips(self):
        for touch, word in (('firm', 'hơi mạnh'), ('long', 'hơi xa')):
            j, tid = self.to_approach(lambda t: t['kind'] == 'flight' and all(g['stable'] for g in t['needs']['gates'][0]))
            j.act('pl_gate', task=tid, flown=dict(stable=True))
            r = j.act('pl_gate', task=tid, flown=dict(stable=True, touch=touch))
            self.assertIn(word, r['message'])
            self.assertEqual(j.get(tid).get('slips') or [], [])

    def test_anything_else_reads_as_an_older_page(self):
        for junk in ('yes', 1, [True], dict(stable='true'), dict(stable=1), dict(touch='soft'), None):
            j, tid = self.to_approach(lambda t: t['needs']['gates'][0][0]['bad'] == 'fast' and t['kind'] == 'flight')
            r = j.act('pl_gate', task=tid, flown=junk)
            self.assertFalse(r['correct'], junk)                     # judged on the rolled readings
            self.assertEqual(j.get(tid)['slips'][-1]['code'], 'unstable')
        j, tid = self.to_approach(lambda t: t['kind'] == 'flight' and all(g['stable'] for g in t['needs']['gates'][0]))
        j.act('pl_gate', task=tid, flown=dict(stable=True, touch='bounced', extra='x' * 5000))
        r = j.act('pl_gate', task=tid, flown=dict(stable=True, touch='bounced'))
        self.assertIn('êm ru', r['message'])
        validate_state(json.loads(json.dumps(j.state)))


class OldServer(Base):
    """Flown-hop state crosses 1.5.1; this is not a whole-save rollback guarantee for unrelated menus."""
    to_approach = Approach.to_approach

    def test_flown_saves_cross_the_151_build(self):
        old = os.environ.get('MNL_OLD_TREE') or str(Path(__file__).resolve().parents[2] / '_rel151' / 'mot-ngay-lam-nghe')
        if not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no 1.5.1 tree (MNL_OLD_TREE)')
        j, tid = self.to_approach(lambda t: t['needs']['gates'][0][0]['bad'] == 'fast' and t['kind'] == 'flight')
        j.act('pl_around', task=tid, flown=dict(stable=False))
        j.act('pl_gate', task=tid, flown=dict(stable=True))          # mid-approach: the old build takes it from here
        cafe = j.state['careers']['cafe_bakery']
        self.assertEqual((cafe['day'], cafe['open'], cafe['tasks'], cafe['active_task'], cafe['metrics']),
                         (1, False, [], None, {}))
        # Only the untouched cafe uses historical menu defaults; retain every pilot field/task.
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,new_state,apply_action;s=json.load(sys.stdin);'
                's["careers"]["cafe_bakery"]=new_state()["careers"]["cafe_bakery"];'
                's=migrate_state(s);validate_state(s);tid=s["careers"]["pilot"]["active_task"];'
                's,_=apply_action(s,"pilot","pl_gate",{"task":tid,"flown":{"stable":True,"touch":"firm"}});'
                's,_=apply_action(s,"pilot","pl_park",{"task":tid});validate_state(s);print(json.dumps(s))')
        env = dict(os.environ, PYTHONPATH=old + os.pathsep + os.environ.get('PYTHONPATH', ''))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(j.state), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        back = migrate_state(json.loads(out.stdout))
        validate_state(back)
        self.assertEqual(next(t for t in back['careers']['pilot']['tasks'] if t['id'] == tid)['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
