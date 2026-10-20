"""🔑 Lễ tân Khách sạn Hoa Sứ (game/careers/reception.py): the front desk of a six-room hotel. Six kinds of work rotate
(check-in on the room board, check-out, the cleaning plan, tomorrow's services, complaints, lost things); the room and
luggage steps are graded by rule; a three-part ca thử việc keeps the parts passed; 24 desk situations with lasting
consequences (relations, marks, the hotel's cost, keepsakes); branches after the second promotion; exams by step;
hiring with cv → interview → trial; the dormant record and the rollback strip to 2.4.66."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import Journey
from game import journey as jr
from game import promotion as pm
from game import promotion_content as PC
from game import employment as emp
from game.careers import ORDER, PLUGINS, kit
from game.engine import DORMANT, GameError, apply_action, dormant_out, initial_career, new_state, public_state, validate_state, migrate_state

R = PLUGINS.get('reception')
if R is not None:
    from game.careers import reception_content as RC


def slot_of(kind, day=3):
    return next(s for s in range(8) if R.kind_of(day, s) == kind)


def answer(t, st, key):
    return R._expected_keys(t) if st['id'] == 'arrival.keys' else key[st['id']]


def wrong_value(t, st, key):
    right = answer(t, st, key)
    typ = st['type']
    if typ == 'choice':
        return next(o['id'] for o in st['options'] if o['id'] != right)
    if typ == 'number':
        return right + 1
    if typ == 'order':
        return list(reversed(right))
    if typ == 'multi':
        ids = sorted(o['id'] for o in st['options'])
        return [] if right == ids else ids
    if typ == 'times':
        k = next(iter(right))
        return dict(right, **{k: right[k] + st['every'] if right[k] < st['high'] else right[k] - st['every']})
    if st['id'] == 'arrival.cart':
        heavy = next((k for k in right if RC.LUGGAGE_INDEX[k][1] in ('heavy', 'fragile', 'tall')), None)
        if heavy:
            return dict(right, **{heavy: 'frame' if right[heavy] != 'frame' else 'top'})
        return {k: 'frame' for k in right}
    # rooms: a busy room for the first card
    board = t['needs']['board'] if t.get('trial') == 'none' else R._active(t)[0]['board']
    busy = next((b['no'] for b in board if b['status'] == 'busy'), None)
    first = next(iter(right))
    return dict(right, **{first: busy or next(b['no'] for b in board if b['no'] not in right.values() and b['status'] != 'clean')})


def clear_desk(j, good=True):
    ev = j.c['ext']['data']['desk']['ev']
    if ev:
        x = next(x for x in RC.DESK if x['id'] == ev['script'])
        opt = next(o for o in x['options'] if (o.get('good') is True) == good) if good else x['options'][-1]
        return j.act('rc_desk', option=opt['id'])
    return None


def solve(j, tid=None, limit=40):
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    for _ in range(limit):
        clear_desk(j)
        t = j.get(tid)
        if t['status'] == 'completed':
            return t
        _, steps, key = R._active(t)
        st = steps[t['at']]
        r = j.act('rc_step', task=tid, step=st['id'], value=answer(t, st, key))
        assert not r['message'].startswith('Chưa đúng'), r
    raise AssertionError('reception task did not finish')


def roundtrip(j):
    j.state = json.loads(json.dumps(j.state))
    validate_state(j.state)


def D(j):
    return j.c['ext']['data']


def pass_trial(j):
    d = D(j)
    d['trial'].update(normal=1, early=1, group=1, done=1)


def normal(career='reception', day=3, slot=0):
    """A desk clerk past the trial with a job of (day, slot)."""
    j = Journey(career, day=day, slot=slot)
    pass_trial(j)
    t = j.task
    t['trial'] = 'none'
    validate_state(j.state)
    return j


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_last_dormant_salaried_late_unlock(self):
        from game import operations
        from game.career_voice import salaried_set
        self.assertEqual(tuple(ORDER[-7:]), ('reception', 'teller', 'restore', 'research', 'radio', 'moto', 'vet'))   # 🏦 teller, 🧰 restore, 🔬 research, 📻 radio, 🏍️ moto and 🩺 vet registered after it
        self.assertIn('reception', DORMANT)
        self.assertIn('reception', salaried_set())
        self.assertIn('reception', operations.SALARIED)
        self.assertEqual(jr.LATE_UNLOCKS['reception'], 3)
        post = R.SPEC['employment']['postings'][0]
        self.assertEqual((post['org'], post['stages']), ('Khách sạn Hoa Sứ', ['cv', 'interview', 'trial']))
        for qid in post['trial'] + post['questions']:
            self.assertIsNotNone(emp.question('reception', qid), qid)

    def test_the_shift_rotates_through_all_six_kinds_and_is_deterministic(self):
        for day in range(1, 9):
            self.assertEqual({R.kind_of(day, s) for s in range(8)}, set(RC.KINDS))
        self.assertEqual(R.make_task(5, 2, 1), R.make_task(5, 2, 1))
        for tid in RC.TRIAL_IDS:
            self.assertEqual(R.trial_brief(4, 1, tid), R.trial_brief(4, 1, tid))

    def test_every_generated_job_is_solvable_by_its_own_key(self):
        for day in range(1, 30):
            for slot in range(12):
                t = R.make_task(day, slot, 1)
                briefs = [(t['needs'], t['needs']['steps'], t['_key'])] + [R.trial_brief(day, slot, x) for x in RC.TRIAL_IDS]
                for brief, steps, key in briefs:
                    probe = dict(t, work={})
                    for st in steps:
                        v = R._expected_keys(probe) if st['id'] == 'arrival.keys' else key[st['id']]
                        self.assertEqual(R._value(st, v), v, (day, slot, st['id']))
                        self.assertEqual(R._check(probe, brief, key, st, v), [], (day, slot, st['id']))
                        probe['work'][st['id']] = v

    def test_journey_opens_the_desk_from_chapter_three_without_listing_it(self):
        s = new_state()
        jr.enable_story(s, 12345)
        s['journey']['chapter'] = 1
        self.assertFalse(jr.is_unlocked(s, 'reception'))
        s['journey']['chapter'] = 3
        self.assertTrue(jr.is_unlocked(s, 'reception'))
        self.assertNotIn('reception', s['journey']['unlocked'])
        self.assertIn('reception', public_state(s)['journey']['unlocked'])


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Jobs(unittest.TestCase):
    def test_each_kind_end_to_end_with_a_mistake_fixed_in_place(self):
        for kind in RC.KINDS:
            with self.subTest(kind=kind):
                j = normal(slot=slot_of(kind))
                tid = j.task['id']
                self.assertEqual(j.task['kind'], kind)
                j.act('ask', task=tid)
                t = j.get(tid)
                _, steps, key = R._active(t)
                st = steps[0]
                r = j.act('rc_step', task=tid, step=st['id'], value=wrong_value(t, st, key))
                self.assertFalse(r['correct'])
                self.assertNotIn('Chị Quyên chỉ', r['message'])            # the first slip: how to work it out
                t = j.get(tid)
                self.assertEqual((t['at'], t['wrong'], t['errors'], t['quality']), (0, 1, [st['id']], 94))
                r = j.act('rc_step', task=tid, step=st['id'], value=wrong_value(t, st, key))
                self.assertIn('Chị Quyên chỉ', r['message'])                 # the second: the answer
                roundtrip(j)
                t = solve(j, tid)
                self.assertEqual(t['status'], 'completed')
                self.assertEqual(t['quality'], 88)
                self.assertEqual(t['paid'], max(3, round(RC.BONUS[kind] * 88 / 100)))
                roundtrip(j)

    def test_any_room_assignment_that_fits_passes_and_the_rules_are_named(self):
        day = next(d for d in range(3, 40) if R.make_task(d, slot_of('arrival', d), 1)['needs']['variant'] == 'normal'
                   and len([b for b in R.make_task(d, slot_of('arrival', d), 1)['needs']['board'] if b['status'] == 'clean']) >= 2)
        j = normal(day=day, slot=slot_of('arrival', day))
        tid = j.task['id']
        j.act('ask', task=tid)
        t = j.get(tid)
        needs, steps, key = R._active(t)
        card = needs['cards'][0]
        j.act('rc_step', task=tid, step='arrival.need', value=key['arrival.need'])
        fits = [b['no'] for b in needs['board'] if not R.rooms_problems(needs, {card['id']: b['no']})]
        self.assertIn(key['arrival.rooms'][card['id']], fits)
        bad = [b for b in needs['board'] if R.rooms_problems(needs, {card['id']: b['no']})]
        self.assertTrue(bad)
        r = j.act('rc_step', task=tid, step='arrival.rooms', value={card['id']: bad[0]['no']})
        self.assertFalse(r['correct'])
        codes = [c for c, _ in R.rooms_problems(needs, {card['id']: bad[0]['no']})]
        self.assertTrue(set(codes) <= set(j.get(tid)['broke']))
        pick = fits[-1]
        r = j.act('rc_step', task=tid, step='arrival.rooms', value={card['id']: pick})
        self.assertTrue(r['correct'])
        # the keys follow the room actually given, not the reference answer
        t = j.get(tid)
        self.assertEqual(R._expected_keys(t), [f'k{pick}'])
        roundtrip(j)

    def test_rooms_rules(self):
        needs = dict(variant='group', board=[dict(no=r['no'], status='clean') for r in RC.ROOMS], cards=[
            dict(id='g1', name='A', people=3, tags=['near', 'street']), dict(id='g2', name='B', people=1, tags=['near'])])
        self.assertEqual(R.rooms_problems(needs, {'g1': '103', 'g2': '102'}), [])
        self.assertIn('cap', [c for c, _ in R.rooms_problems(needs, {'g1': '201', 'g2': '202'})])
        self.assertIn('near', [c for c, _ in R.rooms_problems(needs, {'g1': '103', 'g2': '101'})])
        self.assertIn('same', [c for c, _ in R.rooms_problems(needs, {'g1': '103', 'g2': '103'})])
        needs['board'][2]['status'] = 'dirty'
        self.assertIn('dirty', [c for c, _ in R.rooms_problems(needs, {'g1': '103', 'g2': '102'})])
        needs['variant'] = 'early'
        self.assertEqual(R.rooms_problems(needs, {'g1': '103', 'g2': '102'}), [])   # an early guest: it is cleaned first
        needs['board'][2]['status'] = 'busy'
        self.assertIn('busy', [c for c, _ in R.rooms_problems(needs, {'g1': '103', 'g2': '102'})])

    def test_cart_rules(self):
        self.assertEqual(R.cart_problems({}, {'vali': 'bottom', 'gom': 'top', 'golf': 'frame', 'balo': 'top'}), [])
        self.assertIn('shelf', [c for c, _ in R.cart_problems({}, {'vali': 'top', 'gom': 'top'})])
        self.assertIn('full', [c for c, _ in R.cart_problems({}, {'balo': 'frame', 'tui': 'frame', 'non': 'frame'})])

    def test_tampered_jobs_are_refused(self):
        j = normal(slot=slot_of('arrival'))
        t = j.task
        for k, v in (('_key', {}), ('needs', dict(t['needs'], board=[])), ('trial', 'night'), ('branch', 'boss'), ('paid', 9), ('broke', ['magic'])):
            s = copy.deepcopy(j.state)
            s['careers']['reception']['tasks'][0][k] = v
            with self.assertRaises(GameError, msg=k):
                validate_state(s)

    def test_a_rule_step_saved_with_a_wrong_room_is_refused(self):
        j = normal(slot=slot_of('arrival'))
        tid = j.task['id']
        j.act('ask', task=tid)
        t = j.get(tid)
        needs, steps, key = R._active(t)
        j.act('rc_step', task=tid, step='arrival.need', value=key['arrival.need'])
        j.act('rc_step', task=tid, step='arrival.rooms', value=key['arrival.rooms'])
        s = copy.deepcopy(j.state)
        busy = next((b['no'] for b in needs['board'] if b['status'] == 'busy'), None)
        if busy:
            s['careers']['reception']['tasks'][0]['work']['arrival.rooms'] = {next(iter(key['arrival.rooms'])): busy}
            with self.assertRaises(GameError):
                validate_state(s)


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Trial(unittest.TestCase):
    def test_a_new_clerk_gets_the_three_trial_parts_and_keeps_what_passed(self):
        j = Journey('reception')
        j.act('rc_intro')
        parts = sorted(t['trial'] for t in j.c['tasks'])
        self.assertEqual(parts, sorted(RC.TRIAL_IDS))
        by = {t['trial']: t['id'] for t in j.c['tasks']}
        # pass 'normal'
        r = solve_trial(j, by['normal'])
        self.assertEqual(D(j)['trial']['normal'], j.c['day'])
        self.assertIn('giữ kết quả', r)
        # fail 'early' on capacity at the rooms step
        tid = by['early']
        j.act('ask', task=tid)
        t = j.get(tid)
        needs, steps, key = R._active(t)
        self.assertEqual(needs['variant'], 'early')
        j.act('rc_step', task=tid, step='arrival.need', value=key['arrival.need'])
        card = needs['cards'][0]
        small = next((rm['no'] for rm in RC.ROOMS if rm['cap'] < card['people']), None)
        if small is None:   # a party of one: an occupied room breaks the "needs" part instead
            small = next(b['no'] for b in needs['board'] if b['status'] == 'busy')
        j.act('rc_step', task=tid, step='arrival.rooms', value={card['id']: small})
        msg = solve_trial(j, tid)
        self.assertIn('chưa đạt', msg)
        self.assertIn('Giữ phần đã đạt', msg)
        self.assertEqual(D(j)['trial']['early'], 0)
        self.assertTrue(D(j)['trial']['last'])
        self.assertTrue(public_state(j.state)['careers']['reception']['data']['trial_view']['practise'])
        solve_trial(j, by['group'])
        self.assertEqual(D(j)['trial']['done'], 0)
        clear_desk(j)
        j.act('end_day')
        j.act('start_day')
        again = [t for t in j.c['tasks'] if t['status'] != 'completed']
        self.assertEqual([t['trial'] for t in again].count('early'), 1)   # only the part not passed comes again
        self.assertNotIn('normal', [t['trial'] for t in again])
        tid = next(t['id'] for t in again if t['trial'] == 'early')
        msg = solve_trial(j, tid)
        self.assertEqual(D(j)['trial']['done'], j.c['day'])
        self.assertIn('Qua thử việc', msg)
        roundtrip(j)
        # after the trial: ordinary jobs
        clear_desk(j)
        j.act('end_day')
        j.act('start_day')
        self.assertTrue(all(t['trial'] == 'none' for t in j.c['tasks'] if t['status'] == 'new'))

    def test_a_done_trial_needs_every_part(self):
        j = Journey('reception')
        j.c['ext']['data']['trial'].update(done=3, normal=3)
        with self.assertRaises(GameError):
            validate_state(j.state)

    def test_the_handover_part_fails_on_a_wrong_note(self):
        j = Journey('reception')
        tid = next(t['id'] for t in j.c['tasks'] if t['trial'] == 'normal')
        j.act('ask', task=tid)
        for _ in range(12):
            clear_desk(j)
            t = j.get(tid)
            _, steps, key = R._active(t)
            st = steps[t['at']]
            if st['id'] == 'arrival.note':
                j.act('rc_step', task=tid, step=st['id'], value=wrong_value(t, st, key))
            r = j.act('rc_step', task=tid, step=st['id'], value=answer(t, st, key))
            if j.get(tid)['status'] == 'completed':
                break
        self.assertEqual(R.trial_misses(j.get(tid)), ['note'])
        self.assertEqual(j.c['ext']['data']['trial']['last'], ['note'])
        self.assertIn(RC.PRACTICE['note'], r['message'])


def solve_trial(j, tid):
    j.act('ask', task=tid)
    r = None
    for _ in range(20):
        clear_desk(j)
        t = j.get(tid)
        if t['status'] == 'completed':
            return r['message']
        _, steps, key = R._active(t)
        st = steps[t['at']]
        r = j.act('rc_step', task=tid, step=st['id'], value=answer(t, st, key))
    raise AssertionError('trial job did not finish')


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Situations(unittest.TestCase):
    def test_at_least_fifteen_awkward_situations_each_with_choices(self):
        ids = [x['id'] for x in RC.DESK]
        self.assertGreaterEqual(len(ids), 15)
        self.assertEqual(len(ids), len(set(ids)))
        for x in RC.DESK:
            self.assertGreaterEqual(len(x['options']), 2, x['id'])
            self.assertIn(x['default'], [o['id'] for o in x['options']])
            self.assertTrue(any(o.get('good') is True for o in x['options']), x['id'])
            for o in x['options']:
                for k in o['effects']:
                    self.assertIn(k, ('review', 'xp', 'patience', 'money', 'mark', 'unmark', 'rel', 'house', 'keep'), (x['id'], k))
                for who in o['effects'].get('rel', {}):
                    self.assertIn(who, RC.CAST)
                if 'keep' in o['effects']:
                    self.assertIn(o['effects']['keep'], RC.KEEPS)
        for sid in ('overbook', 'rehearsal', 'crowd', 'plant', 'demands', 'towels', 'threat', 'teddy', 'surprise', 'cat',
                    'passport', 'blackout', 'drunk', 'early4h', 'switch3', 'vip', 'suitcase', 'credit', 'rookie'):
            self.assertIn(sid, ids)

    def fire(self, j, sid):
        d = D(j)['desk']
        d['seq'] += 1
        d['ev'] = dict(id=f'desk-{d["seq"]}', script=sid, day=j.c['day'], at='between')

    def test_choices_carry_over_relations_marks_cost_and_keepsakes(self):
        j = normal()
        self.fire(j, 'overbook')
        j.act('rc_desk', option='partner')
        self.assertIn('partner', D(j)['desk']['marks'])
        self.assertEqual(D(j)['today']['house'], 35)
        self.assertIn('partner_bill', [x['id'] for x in R._scripts(D(j)) if x.get('need_mark') in D(j)['desk']['marks']])
        self.fire(j, 'partner_bill')
        j.act('rc_desk', option='help')
        self.assertNotIn('partner', D(j)['desk']['marks'])
        before = D(j)['rel']['lai']
        self.fire(j, 'towels')
        j.act('rc_desk', option='report')
        self.assertEqual(D(j)['rel']['lai'], before - 12)
        self.fire(j, 'teddy')
        r = j.act('rc_desk', option='route')
        self.assertIn('gau_drawing', D(j)['keeps'])
        self.assertIn('Sổ nghề', r['message'])
        view = public_state(j.state)['careers']['reception']['data']
        self.assertIn('Tranh cảm ơn của bé Su', [k['name'] for k in view['keepsakes']])
        self.assertEqual({p['id'] for p in view['cast']}, set(RC.CAST))
        roundtrip(j)

    def test_relation_gates_open_and_close_situations(self):
        j = normal()
        self.assertNotIn('lai_off', [x['id'] for x in R._scripts(D(j))])
        D(j)['rel']['lai'] = 30
        self.assertIn('lai_off', [x['id'] for x in R._scripts(D(j))])
        self.assertNotIn('tu_photo', [x['id'] for x in R._scripts(D(j))])
        D(j)['rel']['tu'] = 60
        self.fire(j, 'tu_room')
        j.act('rc_desk', option='swap')                                    # ông Tư +12 → 72, mark tu_happy
        self.assertIn('tu_happy', D(j)['desk']['marks'])
        self.assertIn('tu_photo', [x['id'] for x in R._scripts(D(j))])
        self.fire(j, 'tu_photo')
        j.act('rc_desk', option='take')
        self.assertIn('tu_photo', D(j)['keeps'])
        roundtrip(j)

    def test_a_costly_day_upsets_the_shift_lead(self):
        j = normal()
        self.fire(j, 'threat')
        j.act('rc_desk', option='free')
        self.fire(j, 'vip')
        j.act('rc_desk', option='discount')
        self.assertEqual(D(j)['today']['house'], 65)
        q = D(j)['rel']['quyen']
        r = j.act('end_day')
        self.assertLess(D(j)['rel']['quyen'], q)
        self.assertIn('65 xu', ' '.join(r['summary']['career']['lines']))
        self.assertIn('freeloader', D(j)['desk']['marks'])
        self.assertIn('freeloader_back', [x['id'] for x in RC.DESK if x.get('need_mark') == 'freeloader'])

    def test_every_mark_a_situation_waits_for_is_set_by_an_earlier_choice(self):
        set_by = {}
        for x in RC.DESK:
            for o in x['options']:
                m = o['effects'].get('mark')
                for name in ([m] if isinstance(m, str) else m or []):
                    set_by.setdefault(name, []).append((x['id'], o['id']))
        for x in RC.DESK:
            if x.get('need_mark'):
                self.assertIn(x['need_mark'], set_by, x['id'])
        for mark in ('diem_angry', 'diem_ok', 'crowd_ok', 'credit_silent', 'freeloader', 'partner', 'tu_happy', 'tu_sad'):
            self.assertIn(mark, [x.get('need_mark') for x in RC.DESK], mark)   # every remembered choice comes back

    def test_a_broken_promise_comes_back_and_can_be_mended(self):
        j = normal()
        self.fire(j, 'demands')
        j.act('rc_desk', option='promise')
        self.assertIn('diem_angry', D(j)['desk']['marks'])
        self.assertIn('diem_back', [x['id'] for x in RC.DESK if x.get('need_mark') in D(j)['desk']['marks']])
        self.fire(j, 'diem_back')
        j.act('rc_desk', option='fix')
        self.assertNotIn('diem_angry', D(j)['desk']['marks'])
        self.assertIn('diem_ok', D(j)['desk']['marks'])
        self.fire(j, 'credit')
        j.act('rc_desk', option='silent')
        k = D(j)['rel']['khoa']
        self.fire(j, 'credit_again')
        j.act('rc_desk', option='book')
        self.assertEqual(D(j)['rel']['khoa'], k - 6)
        self.assertIn('quyen_note', D(j)['keeps'])
        roundtrip(j)

    def test_the_review_names_the_exam_of_its_step(self):
        self.assertEqual(PC.EXAM_NAME['reception'], ('Kỳ thi đón đoàn', 'Kỳ thi trực ca tối', 'Kỳ thi điều phối sự kiện'))

    def test_an_undecided_situation_takes_its_default_at_closing(self):
        j = normal()
        self.fire(j, 'drunk')
        j.act('end_day')
        d = D(j)
        self.assertIsNone(d['desk']['ev'])
        self.assertEqual(d['desk']['last']['choice'], 'master')


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Ladder(unittest.TestCase):
    def test_exams_by_step_and_titles(self):
        self.assertEqual(PC.STEP_BANK['reception'], ('rc_group', 'rc_night', 'rc_event'))
        j = normal()
        s, c = j.state, j.c
        for n, bank in enumerate(PC.STEP_BANK['reception']):
            rec = dict(pm.new_record(), rank=n)
            qs = pm._draw_qs(s, 'reception', rec, 5)
            self.assertTrue(set(qs) <= {q['id'] for q in PC.QUESTIONS[bank]}, (n, qs))
        self.assertEqual(PC.EMP_TITLES['reception'][:3], ('Lễ tân đón đoàn', 'Lễ tân trực ca tối', 'Điều phối sự kiện Hoa Sứ'))
        self.assertEqual(len(PC.EMP_TITLES['reception']), 7)
        self.assertEqual(pm.group('reception'), 'desk')
        self.assertEqual(len({q['id'] for q in PC.QUESTIONS['desk']}), 18)

    def test_a_branch_after_the_second_step_pays_its_own_jobs_more(self):
        j = normal(slot=slot_of('complaint'))
        with self.assertRaises(GameError):
            j.act('rc_branch', branch='care')                      # step 0: not yet
        rec = pm._live(j.state, j.c, 'reception', create=True)   # the ladder of this contract
        rec['rank'] = 2
        self.assertEqual(pm.rank(j.state, j.c, 'reception'), 2)
        j.act('rc_branch', branch='care')
        self.assertEqual(D(j)['branch'], 'care')
        with self.assertRaises(GameError):
            j.act('rc_branch', branch='ops')                       # change after 7 days only
        r = j.act('more_work')
        t = j.task
        self.assertEqual(t['branch'], 'care')
        if R.active_kind(t) in RC.BRANCHES['care'][4]:
            done = solve(j, t['id'])
            self.assertEqual(done['paid'], round(max(3, RC.BONUS[R.active_kind(t)]) * 1.25))
        roundtrip(j)
        self.assertEqual(public_state(j.state)['careers']['reception']['data']['branch_view']['info']['label'], 'Chăm sóc khách')


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Hiring(unittest.TestCase):
    def test_apply_cv_interview_trial_then_hired_and_the_trial_shifts_start(self):
        s = new_state()
        s, _ = apply_action(s, 'reception', 'select_career', {})
        self.assertEqual(s['careers']['reception']['job']['status'], 'none')
        with self.assertRaises(GameError):
            apply_action(s, 'reception', 'start_day', {})              # hired first
        post = R.SPEC['employment']['postings'][0]
        s, r = apply_action(s, 'reception', 'job_apply', {'posting': post['id']})
        job = s['careers']['reception']['job']
        if job['status'] == 'applying':                                 # (a seeded lucky meeting can skip the pipeline)
            self.assertEqual(job['application']['stage'], 'cv')
            s, _ = apply_action(s, 'reception', 'job_cv', {'strengths': ['communication', 'careful', 'calm'], 'claims': ['fresh']})
            for _ in range(8):
                job = s['careers']['reception']['job']
                app = job.get('application')
                if job['status'] != 'applying' or not app:
                    break
                stage = app['stage']
                self.assertIn(stage, ('interview', 'trial'))
                q = next(qid for qid in emp.stage_steps(post, stage) if qid not in app['answers'])
                best = max(emp.question('reception', q)['options'], key=lambda o: o['score'])
                s, _ = apply_action(s, 'reception', 'job_answer', {'question': q, 'option': best['id']})
            self.assertEqual(s['careers']['reception']['job']['status'], 'offer')
        if s['careers']['reception']['job']['status'] == 'offer':
            s, _ = apply_action(s, 'reception', 'job_accept', {'confirm': True})
        job = s['careers']['reception']['job']
        self.assertEqual((job['status'], job['employer']), ('hired', 'rc-hoasu'))
        self.assertTrue(job['probation'])
        s, _ = apply_action(s, 'reception', 'start_day', {})
        c = s['careers']['reception']
        self.assertEqual(sorted(t['trial'] for t in c['tasks']), sorted(RC.TRIAL_IDS))   # the ca thử việc at the desk
        validate_state(json.loads(json.dumps(s)))

    def test_an_unsafe_trial_answer_stops_the_trial(self):
        q = emp.question('reception', 'rc_tr_normal')
        self.assertTrue(any(o.get('fatal') for o in q['options']))


ROOT = Path(__file__).resolve().parents[1]
BASE_REF = 'fe504023'   # 2.4.71 (live), a release without the reception desk (2.4.67 5ba2e147, 2.4.66 a808cb79 neither)
OLD_LOAD = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action;'
            's=migrate_state(json.load(sys.stdin));validate_state(s);'
            's,_=apply_action(s,"milk_tea","select_career",{});s,_=apply_action(s,"milk_tea","start_day",{});'
            's,_=apply_action(s,"milk_tea","end_day",{"carry_event":True});validate_state(s);print(json.dumps(s,ensure_ascii=False))')


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Rollback(unittest.TestCase):
    """2.4.66 requires exactly its own careers: an untouched desk stays out of the stored text (engine.DORMANT), a
    worked one is stripped before a rollback (scripts/strip_new_careers.py strip --careers reception) and restored
    after rolling forward."""
    tree = None

    @classmethod
    def setUpClass(cls):
        old = os.environ.get('MNL_OLD_TREE')
        if old:
            cls.tree = old
            return
        if not shutil.which('git') or not (ROOT / '.git').exists():
            raise unittest.SkipTest('needs a git checkout or MNL_OLD_TREE')
        if subprocess.run(['git', 'cat-file', '-e', BASE_REF + '^{commit}'], cwd=ROOT, capture_output=True).returncode:
            raise unittest.SkipTest(f'{BASE_REF} is not in this clone')
        cls._tmp = tempfile.TemporaryDirectory(prefix='rc-base-')
        archive = subprocess.run(['git', 'archive', BASE_REF, 'game', 'reference', 'i18n'], cwd=ROOT, capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', cls._tmp.name], input=archive, check=True)
        cls.tree = cls._tmp.name

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, '_tmp', None):
            cls._tmp.cleanup()

    def old(self, save):
        env = dict(os.environ, PYTHONPATH=self.tree)
        return subprocess.run([sys.executable, '-c', OLD_LOAD], input=json.dumps(save, ensure_ascii=False), capture_output=True, text=True,
                              encoding='utf-8', cwd=self.tree, env=env, timeout=300)

    def test_an_untouched_desk_is_left_out_and_the_save_plays_on_2_4_66(self):
        j = Journey('milk_tea')
        j.act('end_day', carry_event=True)
        stored = dormant_out(j.state)
        self.assertNotIn('reception', stored['careers'])
        out = self.old(stored)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = migrate_state(json.loads(out.stdout))     # forward again: the desk comes back fresh
        validate_state(back)
        self.assertEqual(back['careers']['reception'], initial_career('reception'))

    def test_a_worked_desk_is_stripped_for_2_4_66_and_restored_byte_for_byte(self):
        sys.path.insert(0, str(ROOT))
        from scripts.strip_new_careers import strip, restore
        s = new_state()
        jr.enable_story(s, 4242)
        s['journey']['gender'] = 'female'
        s['journey']['chapter'] = 3
        s['journey']['done'] = [1, 2]
        s['careers']['reception']['job'] = emp.hired_record('reception')
        j = Journey.__new__(Journey)
        j.career, j.state = 'reception', s
        j.act('select_career')
        j.act('start_day')
        j.act('rc_intro')
        solve_trial(j, next(t['id'] for t in j.c['tasks'] if t['trial'] == 'normal'))
        clear_desk(j)
        j.act('end_day')
        played = json.loads(json.dumps(j.state))
        played['journey'].setdefault('certificates', {})['reception_service'] = dict(score=100, best=100, earned_day=1, attempts=1)   # 🎓 its certificate goes out with it
        refused = self.old(played)
        self.assertNotEqual(refused.returncode, 0, 'the old build refuses a worked desk as it is')
        stripped, removed = strip(played, ['reception'])
        self.assertIn('reception', removed)
        out = self.old(dormant_out(stripped))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = json.loads(out.stdout)
        self.assertEqual(back['careers']['milk_tea']['day'], 2)        # a day played on 2.4.66
        again, problems = restore(migrate_state(back), removed)
        self.assertEqual(problems, [])
        again = migrate_state(again)
        validate_state(again)
        self.assertEqual(json.dumps(again['careers']['reception'], sort_keys=True), json.dumps(played['careers']['reception'], sort_keys=True))
        self.assertEqual(again['journey']['certificates']['reception_service'], played['journey']['certificates']['reception_service'])


if __name__ == '__main__':
    unittest.main()
