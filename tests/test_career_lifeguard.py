"""Nhân viên cứu hộ hồ bơi (game/careers/lifeguard.py): opening the pool, the timed scan and the quiet signs of drowning,
the rescue (reach or throw before going in, never without a tube, never upside down), the gate, the children's class,
first aid, thunder (thirty minutes after the last one), anh Hải's first catches, the awkward people of the pool
(air_odd engine), the end-of-shift log, hiring, and saves (old data, forged tasks, hidden facts)."""
import copy
import json
import re
import unittest

from tests.helpers import Journey
from game.careers import PLUGINS, air_odd as ao, kit
from game.engine import GameError, new_state, apply_action, public_state, validate_state

L = PLUGINS.get('lifeguard')
if L is not None:
    from game.careers import lifeguard_content as LC

ROUGH = re.compile(r'\b(địt|đụ|đéo|lồn|cặc|buồi|đĩ)\b', re.I)
DOSE = re.compile(r'\d+([.,]\d+)?\s*(mg|mcg|ml|µg|ui|iu|đơn vị|viên/|lần/ngày|giọt|ppm)\b', re.I)


class Clock:
    """kit.clock for the scan: seconds that only move when a test says so."""
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def quiet(j):
    """No encounter and no desk surprise for the rest of today."""
    d = j.c['ext']['data']
    ao.ensure(d).update(day=j.c['day'], plan=[], fired=0, ev=None)
    d['desk'].update(day=j.c['day'], plan=[], fired=0, ev=None)


_WHERE = {}


def where(case, kind):
    """The first (day, slot) whose generated task is `case` of `kind` (tasks are pure: a test plays the real one)."""
    if (case, kind) not in _WHERE:
        _WHERE[(case, kind)] = next((d, s) for d in range(1, 400) for s in range(1, 9)
                                    if L.task_kind(d, s) == kind and (case is None or L.make_task(d, s, 1)['_v'].get('case') == case))
    return _WHERE[(case, kind)]


def at(case, kind, learned=True):
    """A journey whose active task is the generated task `case` of `kind`, shift open; anh Hải gone when `learned`."""
    day, slot = where(case, kind)
    j = Journey('lifeguard', slot=slot, day=day)
    j.act('hb_intro')
    quiet(j)
    if learned:
        j.c['ext']['data']['learn']['n'] = L.LEARN
    return j


def known(j, t):
    if not t['known']:
        j.act('ask', task=t['id'])
    return j.get(t['id'])


def codes(t):
    return {x['code'] for x in t.get('slips') or []}


def solve(j, t):
    """The careful way through one task."""
    tid = t['id']
    k = t['kind']
    t = known(j, t)
    if k == 'open':
        faults = L._faults(t)
        for w in L.CHECK_IDS:
            j.act('hb_check', task=tid, what=w)
        st = L._strip(t)
        j.act('hb_log', task=tid, cl=st['cl'], ph=st['ph'])
        for w, f in faults.items():
            if LC.FAULTS[f]['fix']:
                j.act('hb_fix', task=tid, what=w)
            j.act('hb_rep', task=tid, what=w, to=LC.FAULTS[f]['to'][0])
        stop = any(LC.FAULTS[f]['stop'] for f in faults.values())
        return j.act('hb_open', task=tid, decision='delay' if stop else 'open')
    if k == 'watch':
        j.act('hb_scan', task=tid)
        for z in L.ZONE_IDS:
            j.act('hb_look', task=tid, zone=z)
        t = j.get(tid)
        for z in L.ZONE_IDS:
            kind = L._zone(t, z)[0]
            if kind in LC.RULES:
                j.act('hb_whistle', task=tid, zone=z, rule=kind)
            elif kind in L.DROWNING:
                res = L._rescue(t)
                j.act('hb_alarm', task=tid, zone=z)
                j.act('hb_backup', task=tid, how='team')
                m = next(m for m, g in LC.METHOD_GRADE[res['where']].items() if g == 'good')
                j.act('hb_method', task=tid, method=m)
                j.act('hb_assess', task=tid)
                c = next(c for c, g in LC.CARE_GRADE[res['state']].items() if g == 'good')
                j.act('hb_care', task=tid, care=c)
        return j.act('hb_round', task=tid)
    if k == 'gate':
        for i, case in enumerate(t['_v']['cases']):
            j.act('hb_gq', task=tid, i=i, what='look')
            j.act('hb_gq', task=tid, i=i, what='ask')
            j.act('hb_verdict', task=tid, i=i, verdict=LC.GATE[case]['best'])
        return j.act('hb_gate', task=tid)
    if k == 'lesson':
        x = LC.LESSONS[t['_v']['case']]
        j.act('hb_sheet', task=tid)
        for kid in x['kids']:
            if LC.KIDS[kid].get('away'):
                j.act('hb_call', task=tid, kid=kid)
            j.act('hb_test', task=tid, kid=kid)
            j.act('hb_band', task=tid, kid=kid, band=LC.KIDS[kid]['band'])
        for tp in x['topics']:
            j.act('hb_teach', task=tid, topic=tp)
        j.act('hb_count', task=tid)
        return j.act('hb_lesson', task=tid)
    if k == 'aid':
        x = LC.AID[t['_v']['case']]
        j.act('hb_aidask', task=tid)
        j.act('hb_gloves', task=tid)
        good = next(o[0] for o in x['options'] if o[2] == 'good')
        return j.act('hb_aid', task=tid, choice=good)
    if k == 'storm':
        ev = LC.STORMS[t['_v']['case']]['events']
        j.act('hb_sky', task=tid)
        for i in range(len(ev)):
            t = j.get(tid)
            if ev[t['step']][2] and 'shelter' not in t['marks']:
                j.act('hb_shelter', task=tid, where='hall')
                j.act('hb_count', task=tid)
            if ev[t['step']][1] == 'push':
                j.act('hb_reply', task=tid, say='rule')
            if t['step'] < len(ev) - 1:
                j.act('hb_wait', task=tid)
        return j.act('hb_reopen', task=tid)
    raise AssertionError(k)


def settle(j):
    """Answer a desk surprise or an encounter the careful way."""
    for _ in range(10):
        d = j.c['ext']['data']
        if d['desk']['ev']:
            x = next(s for s in LC.DESK if s['id'] == d['desk']['ev']['script'])
            good = next((o['id'] for o in x['options'] if o.get('good') is True), x['options'][0]['id'])
            j.act('hb_desk', option=good)
            continue
        if d['odd']['ev']:
            x = next(s for s in LC.ODD if s['id'] == d['odd']['ev']['script'])
            if x['kind'] == 'bargain':
                j.act('hb_odd', tone='firm', say=['rule'] if 'rule' in ao.WORDS['bargain'] else ['paper'], to='company', n=0)
            else:
                w = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'demand': ['rule', 'alt'], 'corner': ['speak', 'rule']}[x['kind']]
                to = 'self' if x['rank'] == 'kin' else 'company' if x['kind'] in ('harass', 'corner') else 'self'
                j.act('hb_odd', tone='firm', say=w, to=to)
            continue
        break


def play_days(days):
    j = Journey('lifeguard')
    j.act('hb_intro')
    for _ in range(days):
        for _ in range(7):
            settle(j)
            open_ = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred')]
            if not open_:
                if j.c['day_completed'] >= 5:
                    break
                j.act('more_work')
                continue
            solve(j, open_[0])
        settle(j)
        facts = j.c['ext']['data']['today']['facts']
        if facts:
            j.act('hb_report', lines=[f['id'] for f in facts if f['true']])
        j.act('end_day', carry_event=True)
        j.act('start_day')
        validate_state(json.loads(json.dumps(j.state)))
    return j


@unittest.skipIf(L is None, 'lifeguard filtered out')
class Content(unittest.TestCase):
    def test_spec_and_registration(self):
        self.assertEqual(L.SPEC['prefix'], 'hb_')
        prefixes = [m.SPEC['prefix'] for cid, m in PLUGINS.items() if cid != 'lifeguard']
        self.assertNotIn('hb_', prefixes)
        self.assertTrue(5 <= len(L.PEOPLE) <= 8)
        self.assertEqual(len(L.SPEC['staff']), 4)
        self.assertEqual(len(L.SPEC['stories']), 3)
        self.assertTrue(5 <= len(L.SPEC['situations']) <= 8)
        from game.journey import CH_UNLOCKS
        self.assertIn('lifeguard', CH_UNLOCKS[4])
        from game import certificates as ct
        self.assertEqual(ct.group_of('lifeguard'), 'pool_rescue')
        from game.promotion_content import EMP_TITLES
        self.assertEqual(len(EMP_TITLES['lifeguard']), 4)

    def test_many_awkward_people(self):
        ids = [x['id'] for x in LC.ODD]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(LC.ODD), 50)
        self.assertGreaterEqual(len(LC.DESK), 12)
        self.assertLessEqual({'charm', 'harass', 'demand', 'corner', 'bargain'}, {x['kind'] for x in LC.ODD})
        self.assertLessEqual({'pax', 'crew', 'boss', 'kin'}, {x['rank'] for x in LC.ODD})
        marks = {x['follow'] for x in LC.ODD if x.get('follow')}
        for x in LC.ODD:
            self.assertIn(x['kind'], ao.KINDS, x['id'])
            self.assertIn(x['rank'], ao.RANKS, x['id'])
            self.assertGreaterEqual(len(x['push']), 2, x['id'])
            self.assertLessEqual(set(x.get('words', {})), set(ao.WORDS[x['kind']]), x['id'])
            if x.get('need_mark'):
                self.assertIn(x['need_mark'], marks, x['id'])
            if x['kind'] == 'bargain':
                self.assertTrue(0 <= x['limit'] < x['ask'] and x['unit'], x['id'])
            if x.get('npc') is not None:
                self.assertLess(x['npc'], len(L.PEOPLE))
        # The owner's list of annoying people is all there.
        for sid in ('hb-momphone', 'hb-flip', 'hb-cap', 'hb-film', 'hb-couple', 'hb-viplane', 'hb-aerobic', 'hb-pee', 'hb-liar',
                    'hb-rain', 'hb-private', 'hb-zalo'):
            self.assertIn(sid, ids)

    def test_words_stay_pg13_and_never_give_a_dose(self):
        def walk(o):
            if isinstance(o, str):
                yield o
            elif isinstance(o, dict):
                for v in o.values():
                    yield from walk(v)
            elif isinstance(o, (list, tuple)):
                for v in o:
                    yield from walk(v)
        texts = list(walk([LC.ODD, LC.DESK, LC.SITUATIONS, LC.WATCH, LC.GATE, LC.KIDS, LC.AID, LC.STORMS, LC.FAULTS, LC.CARE, LC.INTRO, L.SPEC]))
        self.assertGreater(len(texts), 600)
        for s in texts:
            self.assertFalse(ROUGH.search(s), s)
            self.assertFalse(DOSE.search(s), s)

    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 15):
            for slot in range(0, 7):
                a, b = L.make_task(day, slot, 1), L.make_task(day, slot, 99)
                self.assertEqual({k: a[k] for k in L.FIXED}, {k: b[k] for k in L.FIXED})
                self.assertEqual(a['kind'], b['kind'])
        self.assertEqual(L.task_kind(5, 0), 'open')
        self.assertEqual(L.task_kind(5, 1), 'watch')
        self.assertEqual(L.make_task(1, 3, 1)['_v']['case'], LC.WATCH_DAY1)
        seen = {L.task_kind(d, s) for d in range(1, 60) for s in range(0, 7)}
        self.assertEqual(seen, set(L.KINDS))
        storm_days = [d for d in range(2, 60) if L.mod_of(d)['id'] == 'storm']
        self.assertTrue(storm_days)
        for d in storm_days:
            self.assertEqual(L.task_kind(d, 2), 'storm')

    def test_every_case_comes_up(self):
        cases, faults = set(), set()
        for day in range(1, 301):
            faults.update(L.faults_of(day))
            for slot in range(0, 7):
                t = L.make_task(day, slot, 1)
                cases.add(t['_v'].get('case') or t['kind'])
                for g in t['_v'].get('cases') or ():
                    cases.add(g)
        for rows in (LC.WATCH, LC.LESSONS, LC.AID, LC.STORMS, LC.GATE):
            self.assertLessEqual(set(rows), cases)
        self.assertEqual(faults, set(LC.FAULTS))

    def test_the_water_card(self):
        self.assertTrue(L.on_card('cl', '2'))
        self.assertFalse(L.on_card('cl', '0,5'))
        self.assertFalse(L.on_card('cl', '5'))
        self.assertTrue(L.on_card('ph', '7,4'))
        self.assertFalse(L.on_card('ph', '8,2'))
        self.assertEqual(L._num('7.4'), L._num('7,4'))
        self.assertEqual(L._num('2,0'), '2')

    def test_every_drowning_is_quiet(self):
        """The quiet signs: nobody in trouble shouts; the loud splashing child is fine."""
        for cid, x in LC.WATCH.items():
            kinds = [z[0] for z in x['zones'].values()]
            self.assertEqual(set(x['zones']), set(L.ZONE_IDS), cid)
            self.assertLessEqual(sum(k in L.DROWNING for k in kinds), 1, cid)
            self.assertEqual(any(k in L.DROWNING for k in kinds), bool(x.get('rescue')), cid)
            for kind, text, _ in x['zones'].values():
                if kind in L.DROWNING:
                    self.assertNotIn('Cứu!', text)


@unittest.skipIf(L is None, 'lifeguard filtered out')
class Hiring(unittest.TestCase):
    def test_start_day_needs_a_contract(self):
        s = new_state()
        s, _ = apply_action(s, 'lifeguard', 'select_career', {})
        with self.assertRaises(GameError) as e:
            apply_action(s, 'lifeguard', 'start_day', {})
        self.assertEqual(e.exception.code, 'not_hired')

    def test_every_posting_hires(self):
        from tests.test_employment_pipelines import applied, play_through
        for post in L.SPEC['employment']['postings']:
            s, _ = applied('lifeguard', post['id'])
            s, _ = play_through(s, 'lifeguard')
            self.assertEqual(s['careers']['lifeguard']['job']['status'], 'offer')
            validate_state(s)


@unittest.skipIf(L is None, 'lifeguard filtered out')
class Opening(unittest.TestCase):
    def test_day_one_opens_on_the_checklist_and_hides_faults(self):
        j = Journey('lifeguard')
        self.assertEqual(j.task['kind'], 'open')
        self.assertTrue(j.task['known'])
        pub = next(x for x in public_state(j.state)['careers']['lifeguard']['tasks'] if x['kind'] == 'open')
        self.assertTrue(all(r['state'] is None and r['text'] is None for r in pub['needs']['checks']))
        self.assertNotIn('_v', pub)

    def test_careful_opening_with_each_fault(self):
        for f, x in LC.FAULTS.items():
            day = next(d for d in range(2, 400) if f in L.faults_of(d))
            with self.subTest(fault=f):
                j = Journey('lifeguard', slot=0, day=day)
                j.act('hb_intro')
                quiet(j)
                r = solve(j, j.task)
                t = next(t for t in j.c['tasks'] if t['kind'] == 'open')
                self.assertEqual(t['status'], 'completed')
                self.assertFalse(t.get('slips'), (f, t.get('slips')))
                self.assertEqual(t['result'], 'delay' if any(LC.FAULTS[g]['stop'] for g in L.faults_of(day)) else 'open', r['message'])

    def test_opening_a_stopped_pool_is_a_safety_mistake(self):
        day = next(d for d in range(2, 400) if 'drain_loose' in L.faults_of(d))
        for learned in (False, True):
            j = Journey('lifeguard', slot=0, day=day)
            j.act('hb_intro')
            quiet(j)
            if learned:
                j.c['ext']['data']['learn']['n'] = L.LEARN
            t = j.task
            for w in L.CHECK_IDS:
                j.act('hb_check', task=t['id'], what=w)
            r = j.act('hb_open', task=t['id'], decision='open')
            if not learned:
                self.assertIn('Anh Hải', r['message'])
                continue
            t = j.get(t['id'])
            self.assertEqual(t['status'], 'completed')
            self.assertIn('drain_loose', codes(t))
            self.assertTrue(any(s['safety'] for s in t['slips']))
            self.assertIs(r['correct'], False)

    def test_wrong_log_numbers_and_skipped_checks(self):
        j = Journey('lifeguard')
        j.act('hb_intro')
        quiet(j)
        j.c['ext']['data']['learn']['n'] = L.LEARN
        t = j.task
        j.act('hb_check', task=t['id'], what='strip')
        with self.assertRaises(GameError):
            j.act('hb_log', task=t['id'], cl='', ph='7')
        j.act('hb_log', task=t['id'], cl='9', ph='9')
        j.act('hb_open', task=t['id'], decision='open')
        self.assertLessEqual({'log', 'skip'}, codes(j.get(t['id'])))
        with self.assertRaises(GameError):
            j.act('hb_open', task=t['id'], decision='open')

    def test_reporting_needs_a_fault_and_a_known_channel(self):
        j = Journey('lifeguard')
        j.act('hb_intro')
        quiet(j)
        t = j.task
        f = L.faults_of(1)[0]
        check = LC.FAULTS[f]['check']
        ok = next(w for w in L.CHECK_IDS if w != check)
        j.act('hb_check', task=t['id'], what=ok)
        with self.assertRaises(GameError):
            j.act('hb_rep', task=t['id'], what=ok, to='book')
        with self.assertRaises(GameError):
            j.act('hb_rep', task=t['id'], what=check, to='book')          # not checked yet
        j.act('hb_check', task=t['id'], what=check)
        with self.assertRaises(GameError):
            j.act('hb_rep', task=t['id'], what=check, to='police')
        with self.assertRaises(GameError):
            j.act('hb_fix', task=t['id'], what=ok)


@unittest.skipIf(L is None, 'lifeguard filtered out')
class Watch(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self._old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self._old

    def test_careful_scan_of_every_case(self):
        for case in LC.WATCH:
            with self.subTest(case=case):
                j = at(case, 'watch')
                t = j.task
                solve(j, t)
                t = j.get(t['id'])
                self.assertEqual(t['status'], 'completed')
                self.assertFalse(t.get('slips'), (case, t.get('slips')))
                validate_state(json.loads(json.dumps(j.state)))

    def test_zones_hidden_until_looked_and_no_kind_ever_shown(self):
        j = at('w-edge', 'watch')
        t = known(j, j.task)
        pub = next(x for x in public_state(j.state)['careers']['lifeguard']['tasks'] if x['id'] == t['id'])
        self.assertTrue(all(z['text'] is None for z in pub['needs']['zones']))
        with self.assertRaises(GameError):
            j.act('hb_look', task=t['id'], zone='bo')        # the scan has not started
        j.act('hb_scan', task=t['id'])
        j.act('hb_look', task=t['id'], zone='cham')
        pub = next(x for x in public_state(j.state)['careers']['lifeguard']['tasks'] if x['id'] == t['id'])
        z = next(z for z in pub['needs']['zones'] if z['id'] == 'cham')
        self.assertIn('Bon', z['text'])
        self.assertNotIn('distress', json.dumps(pub))
        self.assertNotIn('rescue', pub['needs'])

    def test_missing_the_quiet_drowning_is_a_safety_mistake(self):
        j = at('w-deepkid', 'watch')
        t = known(j, j.task)
        j.act('hb_scan', task=t['id'])
        for z in L.ZONE_IDS:
            j.act('hb_look', task=t['id'], zone=z)
        j.act('hb_whistle', task=t['id'], zone='bo', rule='film')
        j.act('hb_round', task=t['id'])
        t = j.get(t['id'])
        self.assertIn('missed', codes(t))
        self.assertTrue(any(s['safety'] for s in t['slips']))

    def test_the_slow_sweep_and_the_late_alarm(self):
        j = at('w-mid', 'watch')
        t = known(j, j.task)
        j.act('hb_scan', task=t['id'])
        self.clock.t += L.SWEEP_S + 5
        for z in L.ZONE_IDS:
            j.act('hb_look', task=t['id'], zone=z)
        self.clock.t += L.ALARM_S
        j.act('hb_alarm', task=t['id'], zone='nhanh')
        self.assertLessEqual({'slow', 'late'}, codes(j.get(t['id'])))

    def test_a_tap_stamp_counts_not_the_network(self):
        j = at('w-run', 'watch')
        t = known(j, j.task)
        j.act('hb_scan', task=t['id'], tap_at=self.clock.t)
        self.clock.t += L.SWEEP_S + 10          # a slow network: the last look arrives late, pressed in time
        for z in L.ZONE_IDS:
            j.act('hb_look', task=t['id'], zone=z, tap_at=self.clock.t - 20)
        self.assertNotIn('slow', codes(j.get(t['id'])))

    def test_no_surprise_while_the_clock_runs(self):
        j = at('w-run', 'watch')
        t = known(j, j.task)
        d = j.c['ext']['data']
        ao.ensure(d).update(day=j.c['day'], plan=['open', 1], fired=0, ev=None)
        j.act('hb_scan', task=t['id'])
        j.act('hb_look', task=t['id'], zone='bo')
        self.assertIsNone(j.c['ext']['data']['odd']['ev'])

    def test_wrong_whistles_and_a_false_alarm(self):
        j = at('w-run', 'watch')
        t = known(j, j.task)
        j.act('hb_scan', task=t['id'])
        for z in L.ZONE_IDS:
            j.act('hb_look', task=t['id'], zone=z)
        j.act('hb_whistle', task=t['id'], zone='can', rule='prank')      # splashing children are only playing
        j.act('hb_whistle', task=t['id'], zone='bo', rule='glass')       # wrong rule for the runners
        j.act('hb_alarm', task=t['id'], zone='can')
        with self.assertRaises(GameError):
            j.act('hb_whistle', task=t['id'], zone='bo', rule='run')
        j.act('hb_round', task=t['id'])
        self.assertLessEqual({'nag', 'wrong_rule', 'false_alarm', 'missed_rule'}, codes(j.get(t['id'])))

    def test_reach_cannot_get_someone_on_the_bottom_and_upside_down_is_never_right(self):
        j = at('w-bottom', 'watch')
        t = known(j, j.task)
        j.act('hb_scan', task=t['id'])
        for z in L.ZONE_IDS:
            j.act('hb_look', task=t['id'], zone=z)
        j.act('hb_whistle', task=t['id'], zone='can', rule='adult')
        j.act('hb_alarm', task=t['id'], zone='sau')
        with self.assertRaises(GameError):
            j.act('hb_round', task=t['id'])                                 # still in the water
        r = j.act('hb_method', task=t['id'], method='reach')
        self.assertIs(r['correct'], False)
        with self.assertRaises(GameError):
            j.act('hb_method', task=t['id'], method='reach')               # tried already
        j.act('hb_method', task=t['id'], method='bare')
        j.act('hb_care', task=t['id'], care='upside')
        j.act('hb_round', task=t['id'])
        t = j.get(t['id'])
        self.assertLessEqual({'delay', 'bare', 'care', 'blind', 'alone'}, codes(t))
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['reward'] if 'reward' in t else 0, 0)

    def test_first_tasks_are_caught_by_anh_hai(self):
        j = at('w-edge', 'watch', learned=False)
        t = known(j, j.task)
        j.act('hb_scan', task=t['id'])
        for z in L.ZONE_IDS:
            j.act('hb_look', task=t['id'], zone=z)
        r = j.act('hb_round', task=t['id'])
        self.assertIn('Anh Hải', r['message'])
        self.assertEqual(j.get(t['id'])['status'], 'in_progress')
        r = j.act('hb_whistle', task=t['id'], zone='cham', rule='adult')
        self.assertIn('Anh Hải', r['message'])
        self.assertNotIn('w:cham', j.get(t['id'])['marks'])


@unittest.skipIf(L is None, 'lifeguard filtered out')
class GateLessonAidStorm(unittest.TestCase):
    def test_careful_gate(self):
        j = at(None, 'gate')
        t = j.task
        solve(j, t)
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        pub = next(x for x in public_state(j.state)['careers']['lifeguard']['tasks'] if x['id'] == t['id'])
        self.assertTrue(all(q['best'] for q in pub['needs']['queue']))

    def test_letting_the_beer_in_is_a_safety_mistake(self):
        day, slot = next((d, s) for d in range(2, 400) for s in range(1, 8) if L.task_kind(d, s) == 'gate' and 'g-beer' in L.make_task(d, s, 1)['_v']['cases'])
        j = Journey('lifeguard', slot=slot, day=day)
        j.act('hb_intro')
        quiet(j)
        j.c['ext']['data']['learn']['n'] = L.LEARN
        t = known(j, j.task)
        pub = next(x for x in public_state(j.state)['careers']['lifeguard']['tasks'] if x['id'] == t['id'])
        self.assertTrue(all(q['ask'] is None and q['look'] is None and q['best'] is None for q in pub['needs']['queue']))
        for i in range(3):
            j.act('hb_verdict', task=t['id'], i=i, verdict='in')
        j.act('hb_gate', task=t['id'])
        t = j.get(t['id'])
        self.assertIn('let_in_unsafe', codes(t))
        self.assertIn('blind', codes(t))

    def test_careful_lessons(self):
        for case in LC.LESSONS:
            with self.subTest(case=case):
                j = at(case, 'lesson')
                t = j.task
                solve(j, t)
                t = j.get(t['id'])
                self.assertEqual(t['status'], 'completed')
                self.assertFalse(t.get('slips'), (case, t.get('slips')))

    def test_the_liar_with_a_green_band(self):
        j = at('l-bon', 'lesson')
        t = known(j, j.task)
        for kid in ('bon', 'na', 'ti'):
            j.act('hb_band', task=t['id'], kid=kid, band='xanh')
        j.act('hb_lesson', task=t['id'])
        t = j.get(t['id'])
        self.assertLessEqual({'over_band', 'over_band2', 'untested', 'topics', 'nocount'}, codes(t))
        self.assertTrue(any(s['safety'] for s in t['slips']))

    def test_careful_first_aid_and_the_myths(self):
        for case, x in LC.AID.items():
            with self.subTest(case=case):
                j = at(case, 'aid')
                solve(j, j.task)
                t = next(t for t in j.c['tasks'] if t['_v'].get('case') == case)
                self.assertEqual(t['status'], 'completed')
                self.assertFalse(t.get('slips'))
        j = at('a-swallow', 'aid')
        t = known(j, j.task)
        j.act('hb_aid', task=t['id'], choice='upside')
        t = j.get(t['id'])
        self.assertIn('unsafe', codes(t))
        self.assertIn('gloves', codes(t))

    def test_careful_storms(self):
        for case in LC.STORMS:
            with self.subTest(case=case):
                j = at(case, 'storm')
                t = j.task
                solve(j, t)
                t = j.get(t['id'])
                self.assertEqual(t['status'], 'completed')
                self.assertFalse(t.get('slips'), (case, t.get('slips')))

    def test_reopening_early_or_swimming_through_thunder(self):
        j = at('s-river', 'storm')
        t = known(j, j.task)
        with self.assertRaises(GameError):
            j.act('hb_reopen', task=t['id'])     # no storm yet: nothing to reopen
        j.act('hb_wait', task=t['id'])           # 14:56: thunder, nobody out yet
        j.act('hb_wait', task=t['id'])           # still in the water: a safety slip
        j.act('hb_shelter', task=t['id'], where='tree')
        j.act('hb_wait', task=t['id'])           # 15:20 sun
        j.act('hb_reopen', task=t['id'])         # fifteen minutes after the last thunder
        t = j.get(t['id'])
        self.assertLessEqual({'late_clear', 'tree', 'early', 'straggler'}, codes(t))

    def test_caving_to_the_boss_costs_conduct(self):
        j = at('s-river', 'storm')
        t = known(j, j.task)
        j.act('hb_wait', task=t['id'])
        j.act('hb_shelter', task=t['id'], where='hall')
        j.act('hb_count', task=t['id'])
        for _ in range(3):
            j.act('hb_wait', task=t['id'])
        self.assertEqual(LC.STORMS['s-river']['events'][j.get(t['id'])['step']][1], 'push')
        before = j.c['ext']['data']['odd']['conduct']['points']
        j.act('hb_reply', task=t['id'], say='cave')
        t = j.get(t['id'])
        self.assertEqual(t['result'], 'cave')
        self.assertIn('early', codes(t))
        self.assertGreater(j.c['ext']['data']['odd']['conduct']['points'], before)


@unittest.skipIf(L is None, 'lifeguard filtered out')
class Around(unittest.TestCase):
    def test_every_surprise_option_is_playable(self):
        for x in LC.DESK:
            for o in x['options']:
                j = Journey('lifeguard')
                j.act('hb_intro')
                quiet(j)
                j.c['money'] += 50
                j.c['ops']['finance']['opening_balance'] += 50
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('hb_check', task=j.task['id'], what='clear')
                self.assertTrue(j.act('hb_desk', option=o['id'])['message'], (x['id'], o['id']))
                validate_state(json.loads(json.dumps(j.state)))

    def test_every_encounter_answers(self):
        for x in LC.ODD:
            j = Journey('lifeguard', slot=0, day=4)
            j.act('hb_intro')
            quiet(j)
            odd = ao.ensure(j.c['ext']['data'])
            odd['seq'] += 1
            odd['ev'] = dict(id=f'odd-{odd["seq"]}', script=x['id'], day=j.c['day'], at='between', said=[])
            pub = public_state(j.state)['careers']['lifeguard']['data']['odd']['ev']
            self.assertEqual(pub['script'], x['id'])
            if x['kind'] == 'charm':
                self.assertNotIn('ca bay', ' '.join(w['label'] for w in pub['words']))
            if x['kind'] == 'bargain':
                p = dict(tone='firm', say=['paper' if 'paper' in x.get('words', {}) else 'rule'], to='company', n=x['limit'])
            else:
                say = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'corner': ['speak', 'rule'], 'demand': ['rule', 'alt']}[x['kind']]
                p = dict(tone='firm', say=say, to='self' if x['rank'] == 'kin' else 'company' if x['kind'] in ('harass', 'corner', 'charm') else 'crew')
            for _ in range(3):
                if odd['ev'] is None:
                    break
                j.act('hb_odd', **p)
                odd = j.c['ext']['data']['odd']
            self.assertIsNone(odd['ev'], x['id'])
            self.assertNotEqual(odd['last']['how'], 'give', x['id'])
            validate_state(json.loads(json.dumps(j.state)))

    def test_giving_in_to_the_rain_boss_costs_conduct(self):
        x = next(s for s in LC.ODD if s['id'] == 'hb-rain')
        j = Journey('lifeguard', slot=0, day=4)
        quiet(j)
        odd = ao.ensure(j.c['ext']['data'])
        odd['ev'] = dict(id='odd-1', script=x['id'], day=j.c['day'], at='between', said=[])
        j.act('hb_odd', tone='soft', say=['yes'], to='self')
        odd = j.c['ext']['data']['odd']
        self.assertEqual(odd['last']['how'], 'give')
        self.assertFalse(odd['last']['good'])
        self.assertGreaterEqual(odd['conduct']['points'], x['breach'])

    def test_situations_are_playable(self):
        j = Journey('lifeguard')
        for x in L.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_the_log_honest_and_with_a_lie(self):
        for honest in (True, False):
            j = at('w-deepkid', 'watch')
            t = known(j, j.task)
            j.act('hb_scan', task=t['id'])
            for z in L.ZONE_IDS:
                j.act('hb_look', task=t['id'], zone=z)
            j.act('hb_whistle', task=t['id'], zone='bo', rule='film')
            j.act('hb_round', task=t['id'])                    # the drowning missed: a tempting false line is offered too
            facts = j.c['ext']['data']['today']['facts']
            self.assertTrue(any(not f['true'] for f in facts))
            pub = public_state(j.state)['careers']['lifeguard']['data']['today']['facts']
            self.assertTrue(all(set(f) == {'id', 'text'} for f in pub))
            pick = [f['id'] for f in facts if f['true'] or not honest]
            before = j.c['ext']['data']['odd']['conduct']['points']
            r = j.act('hb_report', lines=pick)
            today = j.c['ext']['data']['today']
            self.assertEqual(today['report'], 'ok' if honest else 'false', r['message'])
            self.assertEqual(j.c['ext']['data']['odd']['conduct']['points'] > before, not honest)
            with self.assertRaises(GameError):
                j.act('hb_report', lines=pick)


@unittest.skipIf(L is None, 'lifeguard filtered out')
class Saves(unittest.TestCase):
    def test_round_trip_and_a_few_days(self):
        j = play_days(6)
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        self.assertGreater(j.c['ext']['data']['stats']['tasks'], 10)

    def test_validate_rejects_broken_data(self):
        j = Journey('lifeguard')
        for path, value in ((('learn', 'n'), -1), (('today', 'report'), 'maybe'), (('today', 'facts'), [dict(id='x', text='y', key=1, true=True)]),
                            (('intro',), 'yes'), (('stats', 'tasks'), 'many')):
            s = copy.deepcopy(j.state)
            node = s['careers']['lifeguard']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        j = at('w-edge', 'watch')
        for key, value in (('_v', dict(case='w-run')), ('seen', ['z:bo', 'ghost']), ('marks', {'alarm': 'roof'}), ('marks', {'w:bo': 'dance'}),
                           ('step', 5), ('sweep', 'soon'), ('washed', 'yes'), ('needs', dict(zones=['bo']))):
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['lifeguard']['tasks'] if x['id'] == j.task['id'])
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_old_data_without_the_pool_book_loads(self):
        j = Journey('lifeguard')
        s = copy.deepcopy(j.state)
        d = s['careers']['lifeguard']['ext']['data']
        for k in ('odd', 'learn', 'regulars', 'desk'):
            d.pop(k, None)
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
