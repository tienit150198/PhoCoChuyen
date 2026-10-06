"""Điều dưỡng khoa Nội (game/careers/nurse.py): the handover, vital signs, medication, call bells, triage, procedures,
going home, chị Hoa's first catches, the awkward people of the ward (air_odd engine), the end-of-shift handover notes,
hiring, and saves (old data, forged tasks, hidden facts). Content is procedural only: no dose ever appears."""
import copy
import json
import re
import unittest

from tests.helpers import Journey
from game.careers import PLUGINS, air_odd as ao
from game.engine import GameError, new_state, apply_action, public_state, validate_state

N = PLUGINS.get('nurse')
if N is not None:
    from game.careers import nurse_content as NC

ROUGH = re.compile(r'\b(địt|đụ|đéo|lồn|cặc|buồi|đĩ)\b', re.I)
DOSE = re.compile(r'\d+([.,]\d+)?\s*(mg|mcg|ml|µg|ui|iu|đơn vị|viên/|lần/ngày|giọt)\b', re.I)


def quiet(j):
    """No encounter and no desk surprise for the rest of today."""
    d = j.c['ext']['data']
    ao.ensure(d).update(day=j.c['day'], plan=[], fired=0, ev=None)
    d['desk'].update(day=j.c['day'], plan=[], fired=0, ev=None)


_WHERE = {}


def where(case, kind):
    """The first (day, slot) whose generated task is `case` (tasks are pure: a test plays the real one)."""
    if (case, kind) not in _WHERE:
        _WHERE[(case, kind)] = next((d, s) for d in range(2, 400) for s in range(1, 9)
                                    if N.task_kind(d, s) == kind and (case is None or N.make_task(d, s, 1)['_v'].get('case') == case))
    return _WHERE[(case, kind)]


def at(case, kind, learned=True):
    """A journey whose active task is the generated task `case` of `kind`, shift open; chị Hoa gone when `learned`."""
    day, slot = where(case, kind)
    j = Journey('nurse', slot=slot, day=day)
    j.act('dd_intro')
    quiet(j)
    if learned:
        j.c['ext']['data']['learn']['n'] = N.LEARN
    return j


def force(j, case):
    """The active task (kept for readability at the call sites: `at` already built the right case)."""
    t = j.task
    assert case is None or t['_v'].get('case') == case, (case, t['_v'])
    return t


def bedside(j, t):
    if not t['known']:
        j.act('ask', task=t['id'])
    j.act('dd_wash', task=t['id'])
    j.act('dd_id', task=t['id'], how='open')


def solve(j, t):
    """The careful way through one task."""
    tid = t['id']
    k = t['kind']
    if k != 'shift' and not t['known']:
        j.act('ask', task=tid)
    t = j.get(tid)
    if k == 'shift':
        for b in N.BED_IDS:
            j.act('dd_read', task=tid, bed=b)
        return j.act('dd_round', task=tid, first=t['_v']['first'])
    if k == 'triage':
        for i in range(3):
            j.act('dd_tq', task=tid, i=i, what='ask')
            j.act('dd_color', task=tid, i=i, color=NC.TRIAGE[t['_v']['cases'][i]]['best'])
        return j.act('dd_triage', task=tid)
    j.act('dd_wash', task=tid)
    j.act('dd_id', task=tid, how='open')
    x = N._case_of(t)
    if k == 'vitals':
        for s in N.SIGN_IDS:
            j.act('dd_measure', task=tid, sign=s)
        if 'recheck' in x:
            j.act('dd_recheck', task=tid, sign='spo2')
        t = j.get(tid)
        j.act('dd_chart', task=tid, vals=N._vals(t))
        bad = N._abn(j.get(tid))
        if bad:
            j.act('dd_call', task=tid, signs=bad)
        return j.act('dd_done', task=tid)
    if k == 'med':
        for w in ('allergy', 'label') + (('sugar',) if x['drug'] == 'pen' else ()):
            j.act('dd_check', task=tid, what=w)
        v = x['variant']
        if v == 'refuse':
            j.act('dd_give', task=tid)
            j.act('dd_explain', task=tid)
            if j.get(tid)['said'] == 'yes':
                return j.act('dd_give', task=tid)
            return j.act('dd_hold', task=tid, reason='refuse')
        if v == 'ok':
            return j.act('dd_give', task=tid)
        return j.act('dd_hold', task=tid, reason=N.HOLD_NEED[v])
    if k == 'bell':
        good = next(o[0] for o in x['options'] if o[2] == 'good')
        return j.act('dd_bell', task=tid, choice=good)
    if k == 'proc':
        for w in N.PROC_KEYS:
            j.act('dd_check', task=tid, what=w)
        v = x['variant']
        if v == 'ate':
            return j.act('dd_hold', task=tid, reason='ate')
        if v == 'refuse':
            j.act('dd_explain', task=tid)
            return j.act('dd_hold', task=tid, reason='refuse')
        if v == 'unsigned':
            j.act('dd_call', task=tid, reason='consent')
        if x['jewel']:
            j.act('dd_jewel', task=tid)
        return j.act('dd_send', task=tid)
    if k == 'discharge':
        for w in N.DIS_CHECKS:
            j.act('dd_check', task=tid, what=w)
        if x['paper'] == 'unsigned':
            j.act('dd_call', task=tid, reason='paper')
        if x['cannula']:
            j.act('dd_cannula', task=tid)
        for tp in x['topics']:
            j.act('dd_teach', task=tid, topic=tp)
        j.act('dd_teachback', task=tid)
        return j.act('dd_discharge', task=tid)


def settle(j):
    """Answer a desk surprise or an encounter the careful way."""
    for _ in range(10):
        d = j.c['ext']['data']
        if d['desk']['ev']:
            x = next(s for s in NC.DESK if s['id'] == d['desk']['ev']['script'])
            good = next((o['id'] for o in x['options'] if o.get('good') is True), x['options'][0]['id'])
            j.act('dd_desk', option=good)
            continue
        if d['odd']['ev']:
            x = next(s for s in NC.ODD if s['id'] == d['odd']['ev']['script'])
            if x['kind'] == 'bargain':
                j.act('dd_odd', tone='firm', say=['rule'], to='company', n=0)
            else:
                w = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'demand': ['rule', 'alt'], 'corner': ['speak', 'rule']}[x['kind']]
                to = 'self' if x['rank'] == 'kin' else 'company' if x['kind'] in ('harass', 'corner') else 'self'
                j.act('dd_odd', tone='firm', say=w, to=to)
            continue
        break




def play_days(days):
    j = Journey('nurse')
    j.act('dd_intro')
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
            j.act('dd_report', lines=[f['id'] for f in facts if f['true']])
        j.act('end_day', carry_event=True)
        j.act('start_day')
        validate_state(json.loads(json.dumps(j.state)))
    return j


def codes(t):
    return {x['code'] for x in t.get('slips') or []}


@unittest.skipIf(N is None, 'nurse filtered out')
class Content(unittest.TestCase):
    def test_spec_and_registration(self):
        self.assertEqual(N.SPEC['prefix'], 'dd_')
        prefixes = [m.SPEC['prefix'] for cid, m in PLUGINS.items() if cid != 'nurse']
        self.assertNotIn('dd_', prefixes)
        self.assertTrue(5 <= len(N.PEOPLE) <= 8)
        self.assertEqual(len(N.SPEC['staff']), 4)
        self.assertEqual(len(N.SPEC['stories']), 3)
        self.assertTrue(5 <= len(N.SPEC['situations']) <= 8)
        from game.journey import CH_UNLOCKS
        self.assertIn('nurse', CH_UNLOCKS[4])
        from game import certificates as ct
        self.assertEqual(ct.group_of('nurse'), 'patient_safety')

    def test_many_awkward_people(self):
        ids = [x['id'] for x in NC.ODD]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(NC.ODD), 40)
        self.assertGreaterEqual(len(NC.DESK), 12)
        kinds = {x['kind'] for x in NC.ODD}
        self.assertLessEqual({'charm', 'harass', 'demand', 'corner', 'bargain'}, kinds)
        self.assertLessEqual({'pax', 'crew', 'boss', 'kin'}, {x['rank'] for x in NC.ODD})
        marks = {x['follow'] for x in NC.ODD if x.get('follow')}
        for x in NC.ODD:
            self.assertIn(x['kind'], ao.KINDS, x['id'])
            self.assertIn(x['rank'], ao.RANKS, x['id'])
            self.assertGreaterEqual(len(x['push']), 2, x['id'])
            self.assertLessEqual(set(x.get('words', {})), set(ao.WORDS[x['kind']]), x['id'])
            if x.get('need_mark'):
                self.assertIn(x['need_mark'], marks, x['id'])
            if x['kind'] == 'bargain':
                self.assertTrue(0 <= x['limit'] < x['ask'] and x['unit'], x['id'])
            if x.get('npc') is not None:
                self.assertLess(x['npc'], len(N.PEOPLE))

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
        texts = list(walk([NC.ODD, NC.DESK, NC.SITUATIONS, NC.BELLS, NC.MEDS, NC.TRIAGE, NC.PROCS, NC.DISCHARGES, NC.NOTES, NC.INTRO, N.SPEC]))
        self.assertGreater(len(texts), 500)
        for s in texts:
            self.assertFalse(ROUGH.search(s), s)
            self.assertFalse(DOSE.search(s), s)

    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 15):
            for slot in range(0, 7):
                a, b = N.make_task(day, slot, 1), N.make_task(day, slot, 99)
                self.assertEqual({k: a[k] for k in N.FIXED}, {k: b[k] for k in N.FIXED})
                self.assertEqual(a['kind'], b['kind'])
        self.assertEqual(N.task_kind(5, 0), 'shift')
        self.assertEqual(N.task_kind(5, 1), 'vitals')
        self.assertEqual(N.make_task(5, 1, 1)['_v']['case'], NC.FLAG_VITALS[N.flag_bed(5)])
        seen = {N.task_kind(d, s) for d in range(1, 30) for s in range(0, 7)}
        self.assertEqual(seen, set(N.KINDS))

    def test_every_case_kind_comes_up(self):
        cases = set()
        for day in range(1, 201):
            for slot in range(0, 7):
                t = N.make_task(day, slot, 1)
                cases.add(t['_v'].get('case') or t['kind'])
        for rows in (NC.MEDS, NC.BELLS, NC.VITALS, NC.PROCS, NC.DISCHARGES):
            self.assertLessEqual(set(rows), cases)

    def test_alarm_card(self):
        self.assertTrue(N.abnormal('temp', '38,9'))
        self.assertFalse(N.abnormal('temp', '37,2'))
        self.assertTrue(N.abnormal('bp', '86/52'))
        self.assertTrue(N.abnormal('spo2', '89'))
        self.assertFalse(N.abnormal('spo2', '96'))
        self.assertTrue(N.abnormal('pain', '8'))
        self.assertEqual(N._num('38.9'), N._num('38,9'))
        self.assertEqual(N._num('118 / 76'), '118/76')
        self.assertEqual(N._num('37,0'), '37')


@unittest.skipIf(N is None, 'nurse filtered out')
class Hiring(unittest.TestCase):
    def test_start_day_needs_a_contract(self):
        s = new_state()
        s, _ = apply_action(s, 'nurse', 'select_career', {})
        with self.assertRaises(GameError) as e:
            apply_action(s, 'nurse', 'start_day', {})
        self.assertEqual(e.exception.code, 'not_hired')

    def test_every_posting_hires(self):
        from tests.test_employment_pipelines import applied, play_through
        for post in N.SPEC['employment']['postings']:
            s, _ = applied('nurse', post['id'])
            s, _ = play_through(s, 'nurse')
            self.assertEqual(s['careers']['nurse']['job']['status'], 'offer')
            validate_state(s)


@unittest.skipIf(N is None, 'nurse filtered out')
class Shift(unittest.TestCase):
    def test_day_one_opens_on_the_handover(self):
        j = Journey('nurse')
        self.assertEqual(j.task['kind'], 'shift')
        self.assertTrue(j.task['known'])
        pub = public_state(j.state)['careers']['nurse']
        t = next(x for x in pub['tasks'] if x['kind'] == 'shift')
        self.assertTrue(all(n['text'] is None for n in t['needs']['notes']))
        self.assertNotIn('_v', t)
        self.assertNotIn('first', t)

    def test_read_and_start_from_the_flagged_bed(self):
        j = Journey('nurse')
        j.act('dd_intro')
        quiet(j)
        t = j.task
        for b in N.BED_IDS:
            j.act('dd_read', task=t['id'], bed=b)
        r = j.act('dd_round', task=t['id'], first=t['_v']['first'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertTrue(r['celebrate'])

    def test_the_wrong_first_bed_is_caught_then_counted(self):
        j = Journey('nurse')
        j.act('dd_intro')
        quiet(j)
        t = j.task
        wrong = next(b for b in N.BED_IDS if b != t['_v']['first'])
        r = j.act('dd_round', task=t['id'], first=wrong)
        self.assertIn('Chị Hoa', r['message'])
        self.assertEqual(j.get(t['id'])['status'], 'understood')
        j.act('dd_round', task=t['id'], first=wrong)
        self.assertEqual(codes(j.get(t['id'])), {'priority', 'skim'})


@unittest.skipIf(N is None, 'nurse filtered out')
class Vitals(unittest.TestCase):
    def play(self, case, chart=None, call=True, recheck=False):
        j = at(case, 'vitals')
        t = force(j, case)
        bedside(j, t)
        for k in NC.SIGN_IDS:
            j.act('dd_measure', task=t['id'], sign=k)
        if recheck:
            j.act('dd_recheck', task=t['id'], sign='spo2')
        vals = chart or N._vals(j.get(t['id']))
        j.act('dd_chart', task=t['id'], vals=vals)
        bad = N._abn(j.get(t['id']))
        if call and bad:
            j.act('dd_call', task=t['id'], signs=bad)
        j.act('dd_done', task=t['id'])
        return j, j.get(t['id'])

    def test_fever_reported_is_clean(self):
        j, t = self.play('v-tu-fever')
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['called'], ['temp'])

    def test_not_reporting_an_abnormal_sign_is_a_safety_slip(self):
        j, t = self.play('v-bay-lowbp', call=False)
        self.assertIn('missed', codes(t))
        self.assertTrue(any(x['safety'] for x in t['slips']))

    def test_a_typo_in_the_chart(self):
        vals = dict(NC.VITALS['v-tuan-ok']['vals'], pulse='67')
        j, t = self.play('v-tuan-ok', chart=vals)
        self.assertIn('chart', codes(t))

    def test_a_loose_probe_is_measured_again(self):
        j, t = self.play('v-lien-probe', recheck=True)
        self.assertFalse(t.get('slips'))
        self.assertEqual(N._abn(t), [])
        j, t = self.play('v-lien-probe', recheck=False)
        self.assertEqual(t['called'], ['spo2'])
        self.assertFalse(t.get('slips'))

    def test_chart_needs_every_sign_and_hands_are_washed_first(self):
        j = at('v-tu-ok', 'vitals', learned=False)
        t = force(j, 'v-tu-ok')
        j.act('ask', task=t['id'])
        r = j.act('dd_measure', task=t['id'], sign='temp')
        self.assertIn('Chị Hoa', r['message'])            # first time: chị Hoa catches the unwashed hands
        self.assertNotIn('temp', j.get(t['id'])['seen'])
        j.act('dd_measure', task=t['id'], sign='temp')   # second time: it counts
        self.assertIn('hands', codes(j.get(t['id'])))
        with self.assertRaises(GameError):
            j.act('dd_chart', task=t['id'], vals={'temp': '37,0'})

    def test_hidden_until_measured(self):
        j = at('v-tu-fever', 'vitals')
        t = force(j, 'v-tu-fever')
        pub = next(x for x in public_state(j.state)['careers']['nurse']['tasks'] if x['id'] == t['id'])
        self.assertIsNone(pub['needs'])
        bedside(j, t)
        j.act('dd_measure', task=t['id'], sign='pulse')
        pub = next(x for x in public_state(j.state)['careers']['nurse']['tasks'] if x['id'] == t['id'])
        self.assertEqual(set(pub['needs']['vals']), {'pulse'})
        self.assertNotIn('_v', pub)


@unittest.skipIf(N is None, 'nurse filtered out')
class Medication(unittest.TestCase):
    def med(self, case, learned=True):
        j = at(case, 'med', learned=learned)
        t = force(j, case)
        bedside(j, t)
        return j, t

    def checks(self, j, t):
        for w in ('allergy', 'label') + (('sugar',) if NC.MEDS[t['_v']['case']]['drug'] == 'pen' else ()):
            j.act('dd_check', task=t['id'], what=w)

    def test_a_clean_dose(self):
        j, t = self.med('m-tu-ok')
        self.checks(j, t)
        money = j.c['money']
        r = j.act('dd_give', task=t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertEqual(j.c['money'] - money, N.BONUS)
        self.assertTrue(r['celebrate'])

    def test_allergy_hold_and_give(self):
        j, t = self.med('m-tu-allergy')
        self.checks(j, t)
        j.act('dd_hold', task=t['id'], reason='allergy')
        t = j.get(t['id'])
        self.assertEqual((t['status'], t['result']), ('completed', 'allergy'))
        self.assertFalse(t.get('slips'))
        j, t = self.med('m-tu-allergy')
        self.checks(j, t)
        money = j.c['money']
        j.act('dd_give', task=t['id'])
        t = j.get(t['id'])
        self.assertIn('allergy', codes(t))
        self.assertEqual(j.c['money'], money)             # a safety slip earns nothing

    def test_wrong_patient_needs_the_open_question(self):
        j = at('m-tu-wrongpt', 'med')
        t = force(j, 'm-tu-wrongpt')
        j.act('ask', task=t['id'])
        j.act('dd_wash', task=t['id'])
        j.act('dd_id', task=t['id'], how='name')
        self.checks(j, t)
        j.act('dd_give', task=t['id'])
        self.assertIn('wrong_patient', codes(j.get(t['id'])))

    def test_tray_label_and_sugar_and_nil_by_mouth(self):
        for case, reason in (('m-tuan-label', 'label'), ('m-bay-pen-low', 'lowsugar'), ('m-lien-npo', 'npo')):
            j, t = self.med(case)
            self.checks(j, t)
            j.act('dd_hold', task=t['id'], reason=reason)
            self.assertFalse(j.get(t['id']).get('slips'), case)
        j, t = self.med('m-bay-pen-low')
        j.act('dd_check', task=t['id'], what='allergy')
        j.act('dd_check', task=t['id'], what='label')
        j.act('dd_give', task=t['id'])
        self.assertLessEqual({'low_sugar'}, codes(j.get(t['id'])))

    def test_holding_a_clean_dose_or_for_the_wrong_reason(self):
        j, t = self.med('m-tu-ok')
        self.checks(j, t)
        r = j.act('dd_hold', task=t['id'], reason='unsure')
        self.assertNotEqual(j.get(t['id'])['status'], 'completed')        # asking the doctor is never refused
        self.assertIn('Y lệnh đúng', r['message'])
        j.act('dd_hold', task=t['id'], reason='allergy')
        self.assertIn('needless', codes(j.get(t['id'])))
        j, t = self.med('m-tuan-label')
        self.checks(j, t)
        j.act('dd_hold', task=t['id'], reason='npo')
        self.assertIn('reason', codes(j.get(t['id'])))

    def test_a_refusal_is_respected(self):
        j, t = self.med('m-bay-refuse')
        self.checks(j, t)
        r = j.act('dd_give', task=t['id'])
        self.assertEqual(j.get(t['id'])['said'], 'refused')
        self.assertEqual(j.get(t['id'])['status'], 'in_progress')
        j.act('dd_explain', task=t['id'])
        said = j.get(t['id'])['said']
        self.assertIn(said, ('yes', 'no'))
        if said == 'no':
            with self.assertRaises(GameError):
                j.act('dd_give', task=t['id'])
            j.act('dd_hold', task=t['id'], reason='refuse')
        else:
            j.act('dd_give', task=t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))

    def test_pushing_a_patient_is_a_mistake(self):
        j, t = self.med('m-tuan-refuse')
        self.checks(j, t)
        j.act('dd_give', task=t['id'])
        j.act('dd_push', task=t['id'])
        j.act('dd_give', task=t['id'])
        self.assertIn('pressure', codes(j.get(t['id'])))

    def test_hidden_facts(self):
        j, t = self.med('m-tuan-label')
        pub = next(x for x in public_state(j.state)['careers']['nurse']['tasks'] if x['id'] == t['id'])
        self.assertIsNone(pub['needs']['tray'])
        self.assertIsNone(pub['needs']['allergy'])
        self.assertNotIn('_v', pub)
        j.act('dd_check', task=t['id'], what='label')
        pub = next(x for x in public_state(j.state)['careers']['nurse']['tasks'] if x['id'] == t['id'])
        self.assertEqual(pub['needs']['tray'], NC.DRUGS['penila']['name'])

    def test_chi_hoa_catches_each_mistake_once(self):
        j, t = self.med('m-tu-allergy', learned=False)
        r = j.act('dd_give', task=t['id'])
        self.assertIn('Chị Hoa', r['message'])
        self.assertEqual(j.get(t['id'])['status'], 'in_progress')
        self.assertFalse(j.get(t['id']).get('slips'))


@unittest.skipIf(N is None, 'nurse filtered out')
class Others(unittest.TestCase):
    def test_bells(self):
        for case, x in NC.BELLS.items():
            for oid, label, grade, outcome, touch in x['options']:
                j = at(case, 'bell')
                t = force(j, case)
                bedside(j, t)
                r = j.act('dd_bell', task=t['id'], choice=oid)
                t = j.get(t['id'])
                self.assertEqual(t['status'], 'completed', (case, oid))
                self.assertEqual(bool(t.get('slips')), grade != 'good', (case, oid))
                self.assertEqual(any(s['safety'] for s in t.get('slips') or []), grade == 'unsafe', (case, oid))

    def test_triage(self):
        j = at(None, 'triage')
        t = j.task
        j.act('ask', task=t['id'])
        for i, k in enumerate(t['_v']['cases']):
            j.act('dd_tq', task=t['id'], i=i, what='quick')
            j.act('dd_color', task=t['id'], i=i, color=NC.TRIAGE[k]['best'])
        j.act('dd_triage', task=t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        pub = next(x for x in public_state(j.state)['careers']['nurse']['tasks'] if x['id'] == t['id'])
        self.assertTrue(all(q['best'] for q in pub['needs']['queue']))

    def test_the_loud_one_first_is_a_safety_slip(self):
        j = at(None, 'triage')
        t = j.task
        j.act('ask', task=t['id'])
        for i, k in enumerate(t['_v']['cases']):
            j.act('dd_tq', task=t['id'], i=i, what='ask')
            j.act('dd_color', task=t['id'], i=i, color='xanh' if NC.TRIAGE[k]['best'] in ('do', 'cam') else 'do')
        pub = next(x for x in public_state(j.state)['careers']['nurse']['tasks'] if x['id'] == t['id'])
        self.assertTrue(all(q['best'] is None for q in pub['needs']['queue']))
        j.act('dd_triage', task=t['id'])
        t = j.get(t['id'])
        self.assertTrue(codes(t) & {'under', 'under_red'})
        self.assertIn('over', codes(t))

    def test_procedures(self):
        for case, x in NC.PROCS.items():
            j = at(case, 'proc')
            t = force(j, case)
            bedside(j, t)
            for w in N.PROC_KEYS:
                j.act('dd_check', task=t['id'], what=w)
            v = x['variant']
            if v == 'ate':
                j.act('dd_hold', task=t['id'], reason='ate')
            elif v == 'refuse':
                with self.assertRaises(GameError):
                    j.act('dd_send', task=t['id'])
                j.act('dd_call', task=t['id'], reason='consent')
                j.act('dd_hold', task=t['id'], reason='refuse')
            else:
                if v == 'unsigned':
                    j.act('dd_call', task=t['id'], reason='consent')
                if x['jewel']:
                    j.act('dd_jewel', task=t['id'])
                j.act('dd_send', task=t['id'])
            t = j.get(t['id'])
            self.assertEqual(t['status'], 'completed', case)
            self.assertFalse(t.get('slips'), (case, t.get('slips')))

    def test_an_unsigned_consent_is_not_sent(self):
        j = at('p-lien-scared', 'proc')
        t = force(j, 'p-lien-scared')
        bedside(j, t)
        for w in N.PROC_KEYS:
            j.act('dd_check', task=t['id'], what=w)
        j.act('dd_send', task=t['id'])
        self.assertIn('consent', codes(j.get(t['id'])))

    def test_discharges(self):
        for case, x in NC.DISCHARGES.items():
            j = at(case, 'discharge')
            t = force(j, case)
            bedside(j, t)
            for w in N.DIS_CHECKS:
                j.act('dd_check', task=t['id'], what=w)
            if x['paper'] == 'unsigned':
                j.act('dd_call', task=t['id'], reason='paper')
            if x['cannula']:
                j.act('dd_cannula', task=t['id'])
            for k in x['topics']:
                j.act('dd_teach', task=t['id'], topic=k)
            j.act('dd_teachback', task=t['id'])
            j.act('dd_discharge', task=t['id'])
            t = j.get(t['id'])
            self.assertEqual(t['status'], 'completed', case)
            self.assertFalse(t.get('slips'), (case, t.get('slips')))
        j = at('d-bay', 'discharge')
        t = force(j, 'd-bay')
        bedside(j, t)
        j.act('dd_discharge', task=t['id'])
        self.assertLessEqual({'cannula', 'teach', 'no_teachback'}, codes(j.get(t['id'])))


@unittest.skipIf(N is None, 'nurse filtered out')
class Around(unittest.TestCase):
    def test_every_surprise_option_is_playable(self):
        for x in NC.DESK:
            for o in x['options']:
                j = Journey('nurse')
                j.act('dd_intro')
                quiet(j)
                j.c['money'] += 50
                j.c['ops']['finance']['opening_balance'] += 50
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('dd_read', task=j.task['id'], bed='g3')
                self.assertTrue(j.act('dd_desk', option=o['id'])['message'], (x['id'], o['id']))
                validate_state(json.loads(json.dumps(j.state)))

    def test_every_encounter_answers(self):
        for x in NC.ODD:
            j = Journey('nurse', slot=0, day=4)
            j.act('dd_intro')
            quiet(j)
            odd = ao.ensure(j.c['ext']['data'])
            odd['seq'] += 1
            odd['ev'] = dict(id=f'odd-{odd["seq"]}', script=x['id'], day=j.c['day'], at='between', said=[])
            pub = public_state(j.state)['careers']['nurse']['data']['odd']['ev']
            self.assertEqual(pub['script'], x['id'])
            if x['kind'] == 'charm':
                self.assertNotIn('ca bay', ' '.join(w['label'] for w in pub['words']))
            if x['kind'] == 'bargain':
                p = dict(tone='firm', say=['rule'], to='company', n=x['limit'])
            else:
                say = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'corner': ['speak', 'rule'], 'demand': ['rule', 'alt']}[x['kind']]
                p = dict(tone='firm', say=say, to='self' if x['rank'] == 'kin' else 'company' if x['kind'] in ('harass', 'corner', 'charm') else 'crew')
            for _ in range(3):
                if odd['ev'] is None:
                    break
                j.act('dd_odd', **p)
                odd = j.c['ext']['data']['odd']
            self.assertIsNone(odd['ev'], x['id'])
            self.assertNotEqual(odd['last']['how'], 'give', x['id'])
            validate_state(json.loads(json.dumps(j.state)))

    def test_giving_in_to_a_bribe_costs_conduct(self):
        x = next(s for s in NC.ODD if s['id'] == 'dd-bribe')
        j = Journey('nurse', slot=0, day=4)
        quiet(j)
        odd = ao.ensure(j.c['ext']['data'])
        odd['ev'] = dict(id='odd-1', script=x['id'], day=j.c['day'], at='between', said=[])
        j.act('dd_odd', tone='soft', say=['yes'], to='self')
        odd = j.c['ext']['data']['odd']
        self.assertEqual(odd['last']['how'], 'give')
        self.assertFalse(odd['last']['good'])
        self.assertGreaterEqual(odd['conduct']['points'], x['breach'])

    def test_situations_are_playable(self):
        j = Journey('nurse')
        for x in N.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_handover_notes_honest_and_with_a_lie(self):
        for honest in (True, False):
            j = at('v-bay-lowbp', 'vitals')
            t = force(j, 'v-bay-lowbp')
            bedside(j, t)
            for k in NC.SIGN_IDS:
                j.act('dd_measure', task=t['id'], sign=k)
            j.act('dd_chart', task=t['id'], vals=N._vals(j.get(t['id'])))
            j.act('dd_done', task=t['id'])                  # not reported: a slip, so a tempting false line is offered too
            facts = j.c['ext']['data']['today']['facts']
            self.assertTrue(any(not f['true'] for f in facts))
            pub = public_state(j.state)['careers']['nurse']['data']['today']['facts']
            self.assertTrue(all(set(f) == {'id', 'text'} for f in pub))
            pick = [f['id'] for f in facts if f['true'] or not honest]
            before = j.c['ext']['data']['odd']['conduct']['points']
            r = j.act('dd_report', lines=pick)
            today = j.c['ext']['data']['today']
            self.assertEqual(today['report'], 'ok' if honest else 'false', r['message'])
            self.assertEqual(j.c['ext']['data']['odd']['conduct']['points'] > before, not honest)
            with self.assertRaises(GameError):
                j.act('dd_report', lines=pick)


@unittest.skipIf(N is None, 'nurse filtered out')
class Saves(unittest.TestCase):
    def test_round_trip_and_a_few_days(self):
        j = play_days(5)
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        self.assertGreater(j.c['ext']['data']['stats']['tasks'], 8)

    def test_validate_rejects_broken_data(self):
        j = Journey('nurse')
        for path, value in ((('learn', 'n'), -1), (('today', 'report'), 'maybe'), (('today', 'facts'), [dict(id='x', text='y', key=1, true=True)]),
                            (('intro',), 'yes'), (('stats', 'tasks'), 'many')):
            s = copy.deepcopy(j.state)
            node = s['careers']['nurse']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        j = at('m-tu-ok', 'med')
        for key, value in (('_v', dict(case='m-tu-allergy')), ('seen', ['allergy', 'ghost']), ('idm', 'guess'), ('colors', {'5': 'do'}),
                           ('chart', dict(temp='37')), ('said', 'maybe')):
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['nurse']['tasks'] if x['id'] == j.task['id'])
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_old_data_without_the_ward_book_loads(self):
        j = Journey('nurse')
        s = copy.deepcopy(j.state)
        d = s['careers']['nurse']['ext']['data']
        for k in ('odd', 'learn', 'regulars', 'desk'):
            d.pop(k, None)
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
