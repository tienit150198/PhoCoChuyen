"""🏦 Ngân hàng — giao dịch viên (game/careers/teller.py): Quầy số 3 of the Bến Chợ office of Ngân hàng Phố.
Hiring inside the branch (three lessons → the three-part practical exam → the name badge → two training shifts), the
float count at opening and the handover at closing, five steps per customer (the tray rules, two same-name recipients,
savings plans, the ATM), Bà Lựu's tea-cart arc, the oái oăm desk scripts with lasting marks and the service record, the
four promotion branches and their reviews, strict saves, and the dormant record an untouched bank leaves out. The
counter's money never touches the player's own wallet or bank account."""
import copy
import json
import unittest
from unittest import mock

from tests.helpers import Journey
from game import journey as jr
from game.careers import ORDER, PLUGINS
from game.engine import DORMANT, GameError, dormant_out, initial_career, new_state, public_state, validate_state, wake

T = PLUGINS.get('teller')
if T is not None:
    from game.careers import teller_content as TC
    from game.careers import kit


def data(j):
    return j.c['ext']['data']


def answer(st, want):
    return T.tray_answer(want) if st['type'] == 'tray' else want


def wrong(st, want):
    """A value of the right shape that is not the answer."""
    typ = st['type']
    if typ in ('choice', 'pick'):
        return next(o['id'] for o in st['options'] if o['id'] != want)
    if typ == 'number':
        return want + 10
    if typ == 'tray':
        t = T.tray_answer(want)
        return dict(t, **{'10': t.get('10', 0) + 1})
    ids = sorted(o['id'] for o in st['options'])
    return [] if want == ids else ids


def clear_desk(j, pick='good'):
    ev = data(j)['desk']['ev']
    if ev:
        x = next(x for x in TC.DESK if x['id'] == ev['script'])
        opt = next((o for o in x['options'] if o.get('good')), x['options'][0]) if pick == 'good' else x['options'][-1]
        j.act('tl_desk', option=opt['id'])


def learn(j):
    for les in TC.LESSONS:
        j.act('tl_learn', lesson=les['id'], answer=les['answer'])


def pass_exam(j):
    learn(j)
    j.act('tl_exam', start=True)
    ex = data(j)['exam']
    parts, key = T.exam_parts(ex['attempt'], ex['day'])
    for st in parts:
        j.act('tl_exam', step=st['id'], value=answer(st, key[st['id']]))


def teller(j):
    """A save past the hiring: badge and training done."""
    d = data(j)
    d.update(stage='teller', learned=[x['id'] for x in TC.LESSONS], badge=dict(day=1, fast=False, clean=False, secs=99), training=TC.TRAINING)
    validate_state(j.state)


def open_float(j):
    d = data(j)
    steps, key = T.shift_steps(j.c['day'], 'open')
    for st in steps[d['today']['open_at'] if d['today']['day'] == j.c['day'] else 0:]:
        j.act('tl_shift', part='open', step=st['id'], value=key[st['id']])


def handover(j):
    d = data(j)
    steps, key = T.shift_steps(j.c['day'], 'close', d['today']['mgr'])
    for st in steps[d['today']['close_at']:]:
        clear_desk(j)
        j.act('tl_shift', part='close', step=st['id'], value=key[st['id']])


def solve(j, tid=None, limit=30):
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    for _ in range(limit):
        clear_desk(j)
        t = j.get(tid)
        if t['status'] == 'completed':
            return t
        _, steps, key = T._active(t)
        st = steps[t['at']]
        j.act('tl_step', task=tid, step=st['id'], value=answer(st, key[st['id']]))
    raise AssertionError('teller task did not finish')


def at_job(job, day=3, stage='teller'):
    slot = next(s for s in range(10) if T.job_of(day, s) == job and not T.luu_slot(day, s))
    j = Journey('teller', day=day, slot=slot)
    if stage == 'teller':
        teller(j)
    elif stage == 'training':
        d = data(j)
        d.update(stage='training', learned=[x['id'] for x in TC.LESSONS], badge=dict(day=1, fast=False, clean=False, secs=99))
    j.task['rk'] = 0
    open_float(j)
    return j


def roundtrip(j):
    j.state = json.loads(json.dumps(j.state))
    validate_state(j.state)


@unittest.skipUnless(T, 'teller filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_dormant_salaried_and_not_the_players_bank(self):
        from game import operations
        from game.career_voice import salaried_set
        self.assertIn('teller', ORDER)
        self.assertIn('teller', DORMANT)
        self.assertIn('teller', operations.SALARIED)
        self.assertIn('teller', salaried_set())
        self.assertEqual(T.SPEC['prefix'], 'tl_')
        self.assertEqual(T.SPEC['tip'], 0)
        post = T.SPEC['employment']['postings'][0]
        self.assertEqual((post['salary'], post['probation_days'], post['stages']), ((56, 70), 3, ['cv', 'interview']))
        # The career never touches game/bank.py: the counter's cash is the bank's, in nghìn đồng.
        src = open(T.__file__, encoding='utf-8').read()
        self.assertNotIn('from .. import bank', src)
        self.assertNotIn('from ..bank', src)
        self.assertNotIn('import bank', src)

    def test_journey_opens_the_bank_from_chapter_three_without_listing_it(self):
        s = new_state()
        jr.enable_story(s, 12345)
        s['journey']['chapter'] = 2
        self.assertFalse(jr.is_unlocked(s, 'teller'))
        s['journey']['chapter'] = 3
        self.assertTrue(jr.is_unlocked(s, 'teller'))
        self.assertNotIn('teller', s['journey']['unlocked'])
        self.assertIn('teller', public_state(s)['journey']['unlocked'])
        self.assertEqual(jr.content()['unlock_chapter']['teller'], 3)

    def test_an_untouched_bank_stays_out_of_the_stored_save(self):
        s = new_state()
        out = dormant_out(s)
        self.assertNotIn('teller', out['careers'])
        back = json.loads(json.dumps(out))
        self.assertTrue(wake(back))
        self.assertEqual(back['careers']['teller'], initial_career('teller'))
        j = at_job('withdraw')
        solve(j)
        self.assertIn('teller', dormant_out(j.state)['careers'])


@unittest.skipUnless(T, 'teller filtered out by MNL_CAREERS')
class Content(unittest.TestCase):
    def test_every_generated_step_has_a_reachable_answer(self):
        for day in range(1, 61):
            for slot in range(10):
                job = T.job_of(day, slot)
                arcs = [-1] + list(range(TC.ARC_N + 1)) if T.luu_slot(day, slot) else [-1]
                for arc in arcs:
                    for rk in (0, 1):
                        b, steps, key, title, opening = T.brief(day, slot, job, arc, rk)
                        self.assertEqual(set(key), {st['id'] for st in steps})
                        for st in steps:
                            want = key[st['id']]
                            if st['type'] == 'tray':
                                tray = T.tray_answer(want)
                                self.assertIsNone(T.tray_problem(tray, want), (day, slot, job, want))
                                self.assertEqual(T.tray_total(tray), st['target'])
                                if want.get('fewest'):
                                    self.assertEqual(T.tray_count(tray), T.fewest_notes(want['total'], want))
                            elif st['type'] in ('choice', 'pick'):
                                self.assertIn(want, [o['id'] for o in st['options']])
                            elif st['type'] == 'multi':
                                self.assertLessEqual(set(want), {o['id'] for o in st['options']})
                            else:
                                self.assertIsInstance(want, int)
        self.assertEqual(T.make_task(5, 2, 1), T.make_task(5, 2, 1))
        self.assertEqual([T.job_of(1, s) for s in range(3)], ['withdraw', 'transfer', 'change'])   # an easy first day

    def test_two_customers_share_the_recipients_name(self):
        for day in range(2, 30):
            for slot in range(10):
                if T.job_of(day, slot) != 'transfer':
                    continue
                b, steps, key, *_ = T.brief(day, slot, 'transfer')
                cards = steps[0]['options']
                right = next(c for c in cards if c['id'] == key['transfer.who'])
                same = [c for c in cards if c['name'] == right['name']]
                self.assertGreaterEqual(len(same), 3)   # the twin, the other job, and the right one
                self.assertEqual([c for c in cards if (c['name'], c['face'], c['detail']) == (b['name'], b['photo'], b['detail'])], [right])

    def test_oai_oam_scripts_are_many_with_lasting_marks(self):
        self.assertGreaterEqual(len(TC.DESK), 12)
        ids = {x['id'] for x in TC.DESK}
        self.assertEqual(len(ids), len(TC.DESK))
        set_marks = {m for x in TC.DESK for o in x['options'] for m in [o.get('effects', {}).get('mark')] + [
            (o.get('luck') or {}).get(k, {}).get('effects', {}).get('mark') for k in ('win', 'lose')] if m}
        needed = {x['need_mark'] for x in TC.DESK if x.get('need_mark')}
        self.assertGreaterEqual(len(needed), 6)
        self.assertLessEqual(needed, set_marks, 'every follow-up can be reached')
        for x in TC.DESK:
            self.assertGreaterEqual(len(x['options']), 2, x['id'])
            self.assertIn(x['default'], [o['id'] for o in x['options']], x['id'])
            self.assertTrue(any(o.get('good') is True for o in x['options']), x['id'])
            for o in x['options']:
                for k in (o.get('effects') or {}).get('record', {}):
                    self.assertIn(k, TC.RECORD_KEYS)


@unittest.skipUnless(T, 'teller filtered out by MNL_CAREERS')
class Hiring(unittest.TestCase):
    def test_the_job_application_goes_through_the_bank_questions(self):
        from game.engine import apply_action
        from game.employment import question

        class J:
            state = new_state()

            def act(self, name, **p):
                self.state, r = apply_action(self.state, 'teller', name, p)
                return r

            @property
            def c(self):
                return self.state['careers']['teller']
        j = J()
        j.act('select_career')
        with self.assertRaises(GameError):
            j.act('start_day')   # not hired yet
        j.act('job_apply', posting='teller-benchu')
        j.act('job_cv', strengths=['careful', 'numbers'], claims=['fresh'])
        post = T.SPEC['employment']['postings'][0]
        qs = T.SPEC['employment']['questions']
        for qid in post['questions']:
            best = max((qs[qid] if qid in qs else question('teller', qid))['options'], key=lambda o: o['score'])
            r = j.act('job_answer', question=qid, option=best['id'])
        self.assertEqual(j.c['job']['status'], 'offer', r)
        j.act('job_accept', confirm=True)
        self.assertEqual(j.c['job']['status'], 'hired')
        validate_state(j.state)

    def test_lessons_then_exam_then_badge(self):
        j = Journey('teller', day=1, slot=0)
        tid = j.task['id']
        j.act('ask', task=tid)
        with self.assertRaises(GameError) as e:
            j.act('tl_step', task=tid, step='withdraw.check', value='ok')
        self.assertEqual(e.exception.code, 'teller_learn')
        les = TC.LESSONS[0]
        bad = next(o[0] for o in les['options'] if o[0] != les['answer'])
        r = j.act('tl_learn', lesson=les['id'], answer=bad)
        self.assertFalse(r['correct'])
        self.assertEqual(data(j)['learned'], [])
        learn(j)
        self.assertEqual(data(j)['stage'], 'exam')
        with self.assertRaises(GameError) as e:
            j.act('tl_step', task=tid, step='withdraw.check', value='ok')
        self.assertEqual(e.exception.code, 'teller_exam')
        with mock.patch.object(kit, 'clock', return_value=1000.0):
            j.act('tl_exam', start=True)
        view = public_state(j.state)['careers']['teller']['data']['exam_view']
        self.assertNotIn('exam', json.dumps(view.get('key', {})))
        ex = data(j)['exam']
        parts, key = T.exam_parts(ex['attempt'], ex['day'])
        with mock.patch.object(kit, 'clock', return_value=1060.0):
            for st in parts:
                j.act('tl_exam', step=st['id'], value=answer(st, key[st['id']]))
        d = data(j)
        self.assertEqual(d['stage'], 'training')
        self.assertEqual(d['badge'], dict(day=1, fast=True, clean=True, secs=60))
        roundtrip(j)

    def test_a_hint_costs_the_clean_mark_and_a_slow_exam_the_fast_one(self):
        j = Journey('teller', day=1, slot=0)
        learn(j)
        with mock.patch.object(kit, 'clock', return_value=0.0):
            j.act('tl_exam', start=True)
            self.assertIn('💡', j.act('tl_exam_hint')['message'])
        ex = data(j)['exam']
        parts, key = T.exam_parts(ex['attempt'], ex['day'])
        with mock.patch.object(kit, 'clock', return_value=float(TC.EXAM_FAST + 30)):
            for st in parts:
                j.act('tl_exam', step=st['id'], value=answer(st, key[st['id']]))
        self.assertEqual((data(j)['badge']['fast'], data(j)['badge']['clean']), (False, False))

    def test_a_failed_part_means_a_retake_tomorrow_and_the_mentor_serves_meanwhile(self):
        j = Journey('teller', day=1, slot=0)
        learn(j)
        j.act('tl_exam', start=True)
        ex = data(j)['exam']
        parts, key = T.exam_parts(ex['attempt'], ex['day'])
        j.act('tl_exam', step=parts[0]['id'], value=answer(parts[0], key[parts[0]['id']]))
        j.act('tl_exam', step=parts[1]['id'], value=wrong(parts[1], key[parts[1]['id']]))   # the twin
        r = j.act('tl_exam', step=parts[2]['id'], value='slip')
        self.assertEqual(r['exam'], 'fail')
        self.assertIn('đúng người nhận', r['message'])
        self.assertEqual(data(j)['stage'], 'exam')
        with self.assertRaises(GameError) as e:
            j.act('tl_exam', start=True)
        self.assertEqual(e.exception.code, 'teller_retry')
        r = j.act('tl_shadow', task=j.task['id'])
        t = j.c['tasks'][0]
        self.assertEqual((t['status'], t['paid'], t['shadow']), ('referred', 0, True))
        roundtrip(j)
        j.c['day'] += 1
        j.act('tl_exam', start=True)
        self.assertEqual(data(j)['exam']['attempt'], 2)

    def test_two_good_training_shifts_make_a_teller(self):
        j = Journey('teller')
        pass_exam(j)
        for _ in range(TC.TRAINING):
            open_float(j)
            for t in list(j.c['tasks']):
                if t['status'] not in ('completed', 'referred', 'cancelled'):
                    solve(j, t['id'])
            handover(j)
            r = j.act('end_day')
            j.act('start_day')
        self.assertEqual(data(j)['stage'], 'teller')
        self.assertIn('Tập sự', ' '.join(r['summary']['career']['lines']))
        roundtrip(j)


@unittest.skipUnless(T, 'teller filtered out by MNL_CAREERS')
class Counter(unittest.TestCase):
    def test_no_customer_before_the_float_is_counted(self):
        slot = next(s for s in range(10) if T.job_of(3, s) == 'withdraw')
        j = Journey('teller', day=3, slot=slot)
        teller(j)
        j.act('ask', task=j.task['id'])
        with self.assertRaises(GameError) as e:
            j.act('tl_step', task=j.task['id'], step='withdraw.check', value='ok')
        self.assertEqual(e.exception.code, 'teller_float')

    def test_a_short_handover_is_reported_not_signed(self):
        day = next(d for d in range(2, 30) if T.short_day(d))
        steps, key = T.shift_steps(day, 'open')
        self.assertEqual(key['open.sign'], 'report')
        self.assertEqual(T.shift_steps(day + 1, 'open')[1]['open.sign'], 'sign')

    def test_every_job_solves_with_a_review_and_a_bonus(self):
        for job in TC.JOB_IDS:
            with self.subTest(job=job):
                j = at_job(job)
                before = j.c['money']
                t = solve(j)
                self.assertEqual(t['status'], 'completed')
                self.assertEqual(t['quality'], 100)
                self.assertGreater(t['paid'], 0)
                self.assertGreaterEqual(j.c['money'], before)
                self.assertTrue(any(f.get('source') == t['id'] and f.get('stars') for f in j.c['feed']))
                roundtrip(j)

    def test_a_wrong_step_stays_open_and_costs_quality(self):
        j = at_job('withdraw')
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = T._active(j.get(tid))
        st = steps[0]
        r = j.act('tl_step', task=tid, step=st['id'], value=wrong(st, key[st['id']]))
        self.assertFalse(r['correct'])
        t = j.get(tid)
        self.assertEqual((t['at'], t['wrong'], t['quality']), (0, 1, 100 - TC.WRONG_COST))
        r = j.act('tl_step', task=tid, step=st['id'], value=wrong(st, key[st['id']]))
        self.assertIn('Chị Hạnh chỉ', r['message'])   # the second slip shows the answer
        roundtrip(j)
        t = solve(j, tid)
        self.assertEqual(t['quality'], 100 - 2 * TC.WRONG_COST)

    def test_the_tray_checks_total_wishes_and_empty_slots(self):
        rule = dict(total=700, max={'500': 0})
        self.assertIn('phiếu cần', T.tray_problem({'200': 3}, rule))
        self.assertIsNotNone(T.tray_problem({'500': 1, '200': 1}, rule))
        self.assertIsNone(T.tray_problem({'200': 3, '100': 1}, rule))
        few = dict(total=700, fewest=True)
        self.assertIn('ít tờ nhất', T.tray_problem({'100': 7}, few))
        self.assertIsNone(T.tray_problem({'500': 1, '200': 1}, few))
        lixi = dict(total=700, min={'50': 5})
        self.assertIn('ít nhất 5', T.tray_problem({'500': 1, '200': 1}, lixi))
        with self.assertRaises(GameError):
            T.tray_norm({'1000': 1})
        with self.assertRaises(GameError):
            T.tray_norm({'500': -1})
        self.assertEqual(T.tray_norm({'10': 0, '50': 2}), {'50': 2})

    def test_the_answer_key_is_never_public(self):
        j = at_job('transfer')
        tid = j.task['id']
        view = public_state(j.state)['careers']['teller']
        t = next(x for x in view['tasks'] if x['id'] == tid)
        self.assertIsNone(t['needs'])
        j.act('ask', task=tid)
        view = public_state(j.state)['careers']['teller']
        t = next(x for x in view['tasks'] if x['id'] == tid)
        self.assertNotIn('_key', t)
        _, _, key = T._active(j.get(tid))
        self.assertNotIn(json.dumps({'transfer.who': key['transfer.who']}), json.dumps(t))

    def test_forged_tasks_and_data_are_rejected(self):
        j = at_job('change')
        solve(j)
        for path, value in ((('job',), 'atm'), (('paid',), 999), (('quality',), 100 - 1), (('arc',), 3), (('pct',), 999)):
            s = copy.deepcopy(j.state)
            t = s['careers']['teller']['tasks'][0]
            t[path[0]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)
        for key, value in (('stage', 'boss'), ('training', 9), ('branch', 'quan_ly')):
            s = copy.deepcopy(j.state)
            s['careers']['teller']['ext']['data'][key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_handover_waits_for_the_last_customer_and_pays_a_small_bonus(self):
        j = at_job('withdraw')
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = T._active(j.get(tid))
        j.act('tl_step', task=tid, step=steps[0]['id'], value=key[steps[0]['id']])
        steps_c, key_c = T.shift_steps(j.c['day'], 'close')
        with self.assertRaises(GameError):
            j.act('tl_shift', part='close', step=steps_c[0]['id'], value=key_c[steps_c[0]['id']])
        solve(j, tid)
        money = j.c['money']
        handover(j)
        self.assertEqual(j.c['money'], money + TC.HANDOVER_BONUS)
        with self.assertRaises(GameError):
            j.act('tl_step', task=tid, step='x', value='y')

    def test_leaving_without_a_handover_costs_a_review(self):
        j = at_job('withdraw')
        solve(j)
        r = j.act('end_day')
        self.assertIn('Chưa bàn giao', ' '.join(r['summary']['career']['lines']))
        self.assertTrue(any(f.get('stars') == 2 and 'bàn giao' in f.get('text', '') for f in j.c['feed']))

    def test_a_branch_rank_adds_its_own_step(self):
        day = 3
        slot = next(s for s in range(10) if T.job_of(day, s) == 'atm')
        _, base, _, _, _ = T.brief(day, slot, 'atm', -1, 0)
        _, ranked, key, _, _ = T.brief(day, slot, 'atm', -1, 1)
        self.assertEqual(len(ranked), len(base) + 1)
        self.assertIn('atm.journal', key)


@unittest.skipUnless(T, 'teller filtered out by MNL_CAREERS')
class Situations(unittest.TestCase):
    def test_every_desk_option_plays_and_marks_follow(self):
        for x in TC.DESK:
            for opt in x['options']:
                with self.subTest(script=x['id'], option=opt['id']):
                    j = at_job('withdraw')
                    d = data(j)
                    d['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at=x.get('at', 'between'))
                    if x.get('need_mark'):
                        d['desk']['marks'][x['need_mark']] = j.c['day']
                    validate_state(j.state)
                    j.act('tl_desk', option=opt['id'])
                    eff = opt.get('effects', {})
                    if eff.get('mark'):
                        self.assertIn(eff['mark'], data(j)['desk']['marks'])
                    if eff.get('unmark'):
                        self.assertNotIn(eff['unmark'], data(j)['desk']['marks'])
                    for k, n in eff.get('record', {}).items():
                        self.assertGreaterEqual(data(j)['record'][k], n)
                    roundtrip(j)

    def test_situations_are_playable(self):
        j = at_job('withdraw')
        for x in T.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)


@unittest.skipUnless(T, 'teller filtered out by MNL_CAREERS')
class Promotion(unittest.TestCase):
    def test_a_plain_step_comes_at_closing_and_a_key_step_needs_the_review(self):
        j = at_job('withdraw')
        d = data(j)
        d['prog']['giao_dich'] = TC.RANK_NEEDS[('giao_dich', 1)][0]
        handover(j)
        r = j.act('end_day')
        self.assertEqual(data(j)['ranks']['giao_dich'], 1)
        self.assertIn('Giao dịch viên cao cấp', ' '.join(r['summary']['career']['lines']))
        data(j)['prog']['giao_dich'] = TC.RANK_NEEDS[('giao_dich', 2)][0]
        validate_state(j.state)
        self.assertTrue(public_state(j.state)['careers']['teller']['data']['review_ready'])
        j.act('tl_review', start=True)
        rv = data(j)['review']
        parts, key = T.review_parts(rv['branch'], rv['to'], rv['day'], data(j)['record'])
        for st in parts:
            j.act('tl_review', step=st['id'], value=answer(st, key[st['id']]))
        self.assertEqual(data(j)['ranks']['giao_dich'], 2)
        self.assertEqual(T.title_of(data(j)), 'Trưởng quầy')
        j.act('tl_branch', branch='quan_ly')   # Quản lý opens from Trưởng quầy
        roundtrip(j)

    def test_quan_ly_needs_truong_quay_and_branches_need_a_teller(self):
        j = at_job('withdraw', stage='training')
        with self.assertRaises(GameError):
            j.act('tl_branch', branch='tu_van')
        teller(j)
        with self.assertRaises(GameError):
            j.act('tl_branch', branch='quan_ly')
        j.act('tl_branch', branch='tu_van')
        self.assertEqual(T.title_of(data(j)), 'Giao dịch viên')

    def test_an_honest_record_answers_the_quota_question(self):
        j = at_job('withdraw')
        d = data(j)
        d.update(branch='tu_van')
        d['ranks']['tu_van'] = 1
        d['prog']['tu_van'] = TC.RANK_NEEDS[('tu_van', 2)][0]
        d['record']['honest'] = 2
        r = j.act('tl_review', start=True)
        self.assertIn('Sổ tư vấn', r['message'])
        rv = data(j)['review']
        parts, key = T.review_parts(rv['branch'], rv['to'], rv['day'], data(j)['record'])
        st = parts[0]
        j.act('tl_review', step=st['id'], value=key[st['id']])
        self.assertEqual(data(j)['ranks']['tu_van'], 2)   # the honesty part came from the record

    def test_a_failed_review_waits_a_day(self):
        j = at_job('withdraw')
        d = data(j)
        d['ranks']['giao_dich'] = 1
        d['prog']['giao_dich'] = 99
        j.act('tl_review', start=True)
        rv = data(j)['review']
        parts, key = T.review_parts(rv['branch'], rv['to'], rv['day'], data(j)['record'])
        for st in parts:
            j.act('tl_review', step=st['id'], value=wrong(st, key[st['id']]))
        self.assertEqual(data(j)['ranks']['giao_dich'], 1)
        with self.assertRaises(GameError) as e:
            j.act('tl_review', start=True)
        self.assertEqual(e.exception.code, 'teller_retry')
        roundtrip(j)


@unittest.skipUnless(T, 'teller filtered out by MNL_CAREERS')
class Arc(unittest.TestCase):
    def test_ba_luu_saves_for_her_new_tea_cart(self):
        days = [d for d in range(2, 60) if any(T.luu_slot(d, s) for s in range(10))]
        self.assertGreaterEqual(len(days), TC.ARC_N)
        j = None
        for n, day in enumerate(days[:TC.ARC_N]):
            slot = next(s for s in range(10) if T.luu_slot(day, s))
            j = Journey('teller', day=day, slot=slot) if j is None else j
            if n == 0:
                teller(j)
            else:
                c = j.c
                c['day'] = day
                t = T.make_task(day, slot, c['turn'])
                c['tasks'].append(t)
                T.on_task(j.state, c, t)
                c['active_task'] = t['id']
            data(j)['today'] = T._today(day)
            open_float(j)
            t = j.task
            self.assertEqual(t['arc'], n)
            self.assertEqual(t['npc'], kit.npc_id('teller', TC.LUU))
            r = solve(j, t['id'])
        self.assertEqual(data(j)['arc']['stage'], TC.ARC_N)
        self.assertTrue(any(f.get('stars') == 5 and 'xe trà' in f.get('text', '').lower() for f in j.c['feed']))
        self.assertTrue(public_state(j.state)['careers']['teller']['data']['arc_view']['done'])
        self.assertIs(public_state(j.state)['journey'].get('tea_cart'), True)   # the cart parks in the 2.5D street
        self.assertIn('ly trà', j.act('tl_seen')['message'])
        with self.assertRaises(GameError):
            j.act('tl_seen')
        roundtrip(j)


if __name__ == '__main__':
    unittest.main()
