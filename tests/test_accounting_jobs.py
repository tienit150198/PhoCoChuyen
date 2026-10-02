"""💼 Việc làm kế toán (game/accounting_jobs.py): exam gate, grandfathering, entry check, referral, ×3/×5 pay."""
import copy
import datetime
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from game import accounting_jobs as aj
from game import accounting_school as school
from game import employment as emp
from game import journey as jr
from game import x3_week as x3
from game.engine import GameError, apply_action, new_state, public_state, validate_state

VN = datetime.timezone(datetime.timedelta(hours=7))
SEED = 7


def at(day, hour=10):
    """A timestamp at `hour` o'clock VN time on 'YYYY-MM-DD'."""
    d = datetime.date.fromisoformat(day)
    return datetime.datetime(d.year, d.month, d.day, hour, tzinfo=VN).timestamp()


def answer(q):
    if q['kind'] == 'entry':
        return [dict(debit=d, credit=c, amount=v) for d, c, v in q['_key']]
    return copy.deepcopy(q['_key'])


def wrong(q):
    if q['kind'] == 'choice':
        return next(o['id'] for o in q['options'] if o['id'] != q['_key'])
    return q['_key'] + 1


def story(chapter=1):
    s = new_state()
    jr.enable_story(s, SEED)
    j = s['journey']
    j.update(gender='female', intro=True, chapter=chapter, done=list(range(1, chapter)))
    for n in range(1, chapter + 1):
        jr._unlock_chapter(j, n)
    return s


_SCHOOL = {}


def certified_block(courses):
    """The school block of a save (seed SEED) that passed `courses`, made once through the real reducer."""
    key = tuple(courses)
    if key not in _SCHOOL:
        s = story()
        for cid in courses:
            for ch in school.course(cid)['chapters']:
                for lesson in ch['lessons']:
                    school.action(s, 'as_open', {'lesson': lesson['id']})
                    for q in lesson['questions']:
                        school.action(s, 'as_answer', {'lesson': lesson['id'], 'question': q['id'], 'answer': answer(q)})
            school.action(s, 'as_exam_start', {'course': cid})
            for qid in list(s['accounting_school']['active_exam']['qs']):
                out = school.action(s, 'as_exam_answer', {'question': qid, 'answer': answer(school.exam_question(cid, qid))})
            assert out['exam']['passed'], out
            _SCHOOL.setdefault(('line', cid), out['message'])
        s['accounting_school']['selected'] = None
        _SCHOOL[key] = s['accounting_school']
    return copy.deepcopy(_SCHOOL[key])


def with_certs(s, courses):
    s['accounting_school'] = certified_block(courses)
    return s


def hire(s, career='corp_accounting', posting=None):
    s['careers'][career]['job'] = emp.hired_record(career, posting)
    return s


def bank(career):
    return {q['id']: q for q in aj._bank(career)}


def kept(s):
    """What an entry check could have written to."""
    c = s['careers']['corp_accounting']
    return copy.deepcopy([s.get('accounting_school'), s['journey'], {k: c[k] for k in ('open', 'started', 'day', 'job', 'money', 'tasks')}])


def paper(s, career, attempt=0, right=True):
    b = bank(career)
    qids = aj.draw(s, career, s['careers'][career]['day'], attempt)
    return dict(attempt=attempt, answers={q: answer(b[q]) if right else wrong(b[q]) for q in qids})


class Holidays(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'MNL_HOLIDAY_OFF': '0'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_vietnamese_public_holidays_2026_2028(self):
        days = ['2026-01-01', '2026-02-16', '2026-02-17', '2026-02-20', '2026-04-26', '2026-04-30', '2026-05-01',
                '2026-09-01', '2026-09-02', '2027-01-01', '2027-02-05', '2027-02-09', '2027-04-16', '2027-09-02',
                '2027-09-03', '2028-01-25', '2028-01-29', '2028-04-04', '2028-09-01', '2028-09-02']
        for d in days:
            self.assertTrue(aj.holiday(at(d)), d)
        for d in ('2026-10-03', '2026-02-15', '2026-02-21', '2026-04-27', '2026-09-03', '2027-09-01', '2028-01-30', '2026-12-31'):
            self.assertIsNone(aj.holiday(at(d)), d)
        self.assertEqual(aj.holiday(at('2027-02-06')), 'Tết Nguyên đán')
        self.assertEqual(aj.holiday(at('2027-04-16')), 'Giỗ Tổ Hùng Vương')

    def test_vn_time_and_the_switch(self):
        eve = datetime.datetime(2026, 4, 29, 17, 30, tzinfo=datetime.timezone.utc).timestamp()   # 00:30 on 30/4 in VN
        self.assertTrue(aj.holiday(eve))
        self.assertIsNone(aj.holiday(eve - 3600))
        with mock.patch.dict(os.environ, {'MNL_HOLIDAY_OFF': '1'}):
            self.assertIsNone(aj.holiday(eve))


class Gate(unittest.TestCase):
    def test_uncertified_newcomer_is_refused_with_the_reason(self):
        s = story(5)   # corp_accounting is open by its chapter
        self.assertIn('corp_accounting', s['journey']['unlocked'])
        for action, p in (('select_career', {}), ('job_apply', {'posting': 'ca-hq'}), ('start_day', {})):
            with self.assertRaises(GameError) as e:
                apply_action(s, 'corp_accounting', action, p)
            self.assertEqual(e.exception.code, 'need_cert')
            self.assertIn('Kế toán cơ bản', e.exception.message)
        self.assertFalse(jr.is_unlocked(s, 'corp_accounting'))
        v = public_state(s)['accounting_school']['jobs']['places']
        self.assertEqual(v['corp_accounting'], [0, 1, 0])
        apply_action(s, 'grocery', 'select_career')   # the rest of the town is untouched

    def test_boss_luck_skips_a_place_that_needs_its_exam(self):
        s = story(6)
        for day in range(1, 400):
            boss = emp.meet_boss(s, 'grocery', day)
            if boss:
                self.assertNotIn(boss['career'], aj.JOBS)
                s = story(6)

    def test_certificate_opens_the_place_early_and_only_its_own(self):
        s = with_certs(story(1), ['basic'])
        self.assertNotIn('corp_accounting', s['journey']['unlocked'])
        self.assertIn('corp_accounting', public_state(s)['journey']['unlocked'])
        self.assertTrue(jr.is_unlocked(s, 'corp_accounting'))
        s, r = apply_action(s, 'corp_accounting', 'select_career')
        s, r = apply_action(s, 'corp_accounting', 'job_apply', {'posting': 'ca-workshop'})
        self.assertNotIn('corp_accounting', s['journey']['unlocked'])   # nothing stored until a shift there
        validate_state(s)
        with self.assertRaises(GameError) as e:
            apply_action(s, 'group_accounting', 'select_career')
        self.assertEqual(e.exception.code, 'locked')
        s7 = with_certs(story(6), ['basic'])
        with self.assertRaises(GameError) as e:
            apply_action(s7, 'group_accounting', 'select_career')
        self.assertEqual(e.exception.code, 'need_cert')
        s7 = with_certs(story(6), ['basic', 'vn_business'])
        apply_action(s7, 'group_accounting', 'select_career')

    def test_sandbox_and_plugin_tests_have_no_gate(self):
        s = new_state()
        s, _ = apply_action(s, 'corp_accounting', 'select_career')
        hire(s)
        s, _ = apply_action(s, 'corp_accounting', 'start_day')
        self.assertTrue(s['careers']['corp_accounting']['open'])


class Grandfathered(unittest.TestCase):
    def test_existing_accountants_keep_their_place_without_the_exam(self):
        for setup in (lambda c: c.update(started=True), lambda c: c['job'].update(status='hired'),
                      lambda c: c['metrics'].update(served=4), lambda c: c['job'].update(status='applying')):
            s = story(5)
            setup(s['careers']['corp_accounting'])
            self.assertTrue(aj.can_work(s, 'corp_accounting')[0])
            self.assertTrue(aj.grandfathered(s, 'corp_accounting'))
        s = hire(story(5))
        s, _ = apply_action(s, 'corp_accounting', 'select_career')
        s, _ = apply_action(s, 'corp_accounting', 'start_day')   # no check: they never sat the course
        c = s['careers']['corp_accounting']
        self.assertTrue(c['open'])
        self.assertEqual(aj.multiplier(s, 'corp_accounting'), 1)
        c['day_completed'] = 1
        wallet = s['journey']['wallet']
        s, r = apply_action(s, 'corp_accounting', 'end_day', {'carry_event': True})
        self.assertEqual(r['summary']['job']['salary'], c['job']['salary'])
        self.assertNotIn('multiplier', r['summary']['job'])
        self.assertGreater(s['journey']['wallet'], wallet)
        validate_state(s)

    def test_a_job_quit_after_working_there_stays_open(self):
        s = hire(story(5))
        s['careers']['corp_accounting']['started'] = True
        s, _ = apply_action(s, 'corp_accounting', 'job_quit', {'confirm': True})
        self.assertEqual(s['careers']['corp_accounting']['job']['status'], 'none')
        apply_action(s, 'corp_accounting', 'job_apply', {'posting': 'ca-hq'})


class EntryCheck(unittest.TestCase):
    def setUp(self):
        self.s = hire(with_certs(story(1), ['basic']))
        self.s, _ = apply_action(self.s, 'corp_accounting', 'select_career')

    def test_start_needs_the_check_and_old_clients_get_a_clean_refusal(self):
        with self.assertRaises(GameError) as e:
            apply_action(self.s, 'corp_accounting', 'start_day')
        self.assertEqual(e.exception.code, 'acct_check')
        self.assertIn('kiểm tra kiến thức', e.exception.message)
        self.assertEqual(public_state(self.s)['accounting_school']['jobs']['places']['corp_accounting'], [1, 3, 1])

    def test_questions_carry_no_key_and_come_from_the_course_bank(self):
        s0 = copy.deepcopy(self.s)
        s, r = apply_action(self.s, None, 'as_job_check', {'career': 'corp_accounting', 'attempt': 0})
        self.assertEqual(kept(s), kept(s0))   # nothing stored
        v = r['acct_check']
        self.assertEqual(len(v['questions']), aj.CHECK_N)
        self.assertNotIn('_key', json.dumps(v))
        self.assertNotIn('explain', json.dumps(v))
        self.assertNotIn('accounting_view', r)
        b = bank('corp_accounting')
        self.assertTrue(all(q['id'] in b and q['id'].startswith('basic_') for q in v['questions']))
        self.assertEqual(len({b[q['id']]['chapter_id'] for q in v['questions']}), aj.CHECK_N)
        draws = {tuple(aj.draw(self.s, 'corp_accounting', 1, n)) for n in range(6)}
        self.assertGreater(len(draws), 3)   # another attempt, other questions
        self.assertEqual(aj.draw(self.s, 'corp_accounting', 1, 2), aj.draw(self.s, 'corp_accounting', 1, 2))

    def test_failed_check_points_to_lessons_costs_nothing_and_retries(self):
        bad = paper(self.s, 'corp_accounting', 0, right=False)
        s0 = copy.deepcopy(self.s)
        s, r = apply_action(self.s, None, 'as_job_grade', dict(career='corp_accounting', **bad))
        g = r['acct_grade']
        self.assertFalse(g['passed'])
        self.assertEqual(g['right'], 0)
        self.assertTrue(g['review'] and all(x['lesson'] in school._content().LESSONS for x in g['review']))
        self.assertNotIn('_key', json.dumps(r))
        self.assertEqual(kept(s), kept(s0))
        with self.assertRaises(GameError) as e:
            apply_action(self.s, 'corp_accounting', 'start_day', {'acct_check': bad})
        self.assertEqual(e.exception.code, 'acct_check')
        two = paper(self.s, 'corp_accounting', 1)
        first = next(iter(two['answers']))
        two['answers'][first] = wrong(bank('corp_accounting')[first])   # 2 of 3 is a pass
        s, r = apply_action(self.s, None, 'as_job_grade', dict(career='corp_accounting', **two))
        self.assertTrue(r['acct_grade']['passed'])
        s, r = apply_action(self.s, 'corp_accounting', 'start_day', {'acct_check': two})
        self.assertTrue(s['careers']['corp_accounting']['open'])
        self.assertEqual(s['journey']['wallet'], s0['journey']['wallet'])
        self.assertIn('corp_accounting', s['journey']['unlocked'])   # worked there: kept like any started place
        validate_state(s)

    def test_a_paper_for_another_day_or_shape_is_refused(self):
        p = paper(self.s, 'corp_accounting', 0)
        for bad in ({'attempt': 0}, dict(p, attempt=5), dict(p, attempt=-1), dict(p, extra=1), 'x',
                    dict(p, answers=dict(p['answers'], zzz='o1'))):
            with self.assertRaises(GameError):
                apply_action(self.s, 'corp_accounting', 'start_day', {'acct_check': bad})
        c = self.s['careers']['corp_accounting']
        c['day'] += 1
        if aj.draw(self.s, 'corp_accounting', c['day'], 0) != list(p['answers']):
            with self.assertRaises(GameError):
                apply_action(self.s, 'corp_accounting', 'start_day', {'acct_check': p})

    def test_check_commands_refuse_where_no_check_is_due(self):
        for s, career in ((story(5), 'corp_accounting'), (self.s, 'grocery'), (self.s, 'group_accounting')):
            with self.assertRaises(GameError):
                apply_action(s, None, 'as_job_check', {'career': career})


class Pay(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'MNL_HOLIDAY_OFF': '0'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def shift(self, when, career='corp_accounting', courses=('basic',), posting=None, base=None):
        s = hire(with_certs(story(6 if career == 'group_accounting' else 1), list(courses)), career, posting)
        if base:
            s['careers'][career]['job']['salary'] = base
        with mock.patch.object(aj, 'now', return_value=at(when)):
            s, _ = apply_action(s, career, 'select_career')
            s, _ = apply_action(s, career, 'start_day', {'acct_check': paper(s, career)})
            s['careers'][career]['day_completed'] = 1
            wallet = s['journey']['wallet']
            s, r = apply_action(s, career, 'end_day', {'carry_event': True})
        row = next(h for h in reversed(s['journey']['history']) if h['kind'] == 'salary')
        validate_state(s)
        return s, r, row, wallet

    def test_x3_on_a_normal_day_x5_on_a_holiday(self):
        s, r, row, _ = self.shift('2026-10-03')
        base = s['careers']['corp_accounting']['job']['salary']
        self.assertEqual(r['summary']['job']['salary'], base * 3)
        self.assertEqual(row['amount'], base * 3)
        self.assertTrue(row['label'].endswith('· x3'), row['label'])
        s, r, row, _ = self.shift('2026-04-30')
        self.assertEqual(row['amount'], base * 5)
        self.assertTrue(row['label'].endswith('· x5'), row['label'])
        self.assertTrue(any('x5 ngày lễ' in n for n in r['effects']))
        s, r, row, _ = self.shift('2027-02-07', 'group_accounting', ('basic', 'vn_business'), 'ga-holding')
        self.assertEqual(row['amount'], 120 * 5)

    def test_probation_rate_first_and_the_cap(self):
        s = hire(with_certs(story(1), ['basic']))
        c = s['careers']['corp_accounting']
        c['job'].update(probation=True, probation_left=2, salary=75)
        c['day_completed'] = 1
        with mock.patch.object(aj, 'now', return_value=at('2026-01-01')):
            self.assertEqual(emp.on_close(s, c, 'corp_accounting')['salary'], round(75 * .85) * 5)
            c['job'].update(probation=False, salary=200)
            self.assertEqual(emp.on_close(s, c, 'corp_accounting')['salary'], aj.PAY_CAP)
            self.assertEqual(emp.public(c, 'corp_accounting', s)['salary'], aj.PAY_CAP)
        self.assertEqual(aj.pay(100, 1), 100)

    def test_weekly_x3_stays_on_the_shift_net_not_the_salary(self):
        with mock.patch.dict(os.environ, {'MNL_X3_OFF': '0'}), mock.patch.object(x3, 'today', return_value=['corp_accounting']):
            s, r, row, wallet = self.shift('2026-10-03')
        salary = r['summary']['job']['salary']
        bonus = next((h for h in s['journey']['history'] if h['label'].startswith('🔥')), None)
        net = r['summary']['net']
        self.assertEqual(bonus['amount'] if bonus else 0, x3.bonus(net))
        self.assertEqual(salary, s['careers']['corp_accounting']['job']['salary'] * 3)
        self.assertEqual(r['summary']['journey']['salary'], salary)   # the salary row stays its own, ×3 once

    def test_practice_company_follows_the_same_rate(self):
        self.assertEqual(school.salary_multiplier(with_certs(story(1), ['basic']), 'corp_accounting'), 3)
        with mock.patch.object(aj, 'now', return_value=at('2026-09-02')):
            self.assertEqual(school.salary_multiplier(with_certs(story(1), ['basic']), 'corp_accounting'), 5)
            self.assertEqual(public_state(with_certs(story(1), ['basic']))['accounting_school']['jobs']['holiday'], 'Quốc khánh 2/9')
        self.assertEqual(school.salary_multiplier(with_certs(story(1), ['basic']), 'teacher'), 1)


class Referral(unittest.TestCase):
    def test_exam_pass_names_the_places_and_the_view_lists_them(self):
        certified_block(['basic', 'vn_business'])
        self.assertIn('Công ty CP Mây Tre Xanh', _SCHOOL[('line', 'basic')])
        self.assertIn('Sông Hồng Group', _SCHOOL[('line', 'vn_business')])
        s = with_certs(story(1), ['basic'])
        rows = {r['career']: r for r in school.view(s)['referral']}
        corp, group = rows['corp_accounting'], rows['group_accounting']
        self.assertTrue(corp['certified'] and corp['open'] and corp['x'] == 3)
        self.assertFalse(group['certified'] or group['open'])
        self.assertEqual(group['course'], 'vn_business')
        orgs = [p['org'] for p in corp['postings']]
        self.assertIn('Công ty CP Mây Tre Xanh · Văn phòng chính', orgs)
        hq = next(p for p in corp['postings'] if p['id'] == 'ca-hq')
        self.assertEqual(hq['paid'], [75 * 3, 100 * 3])
        self.assertEqual(hq['holiday'], [75 * 5, 100 * 5])


class Saves(unittest.TestCase):
    def new_build_save(self):
        """A save with everything this feature touches: certificates, an early place worked once."""
        s = hire(with_certs(story(1), ['basic']))
        s, _ = apply_action(s, 'corp_accounting', 'select_career')
        s, _ = apply_action(s, 'corp_accounting', 'start_day', {'acct_check': paper(s, 'corp_accounting')})
        s['careers']['corp_accounting']['day_completed'] = 1
        s, _ = apply_action(s, 'corp_accounting', 'end_day', {'carry_event': True})
        return s

    def test_no_new_keys_and_old_unlock_rule_holds(self):
        s = self.new_build_save()
        validate_state(s)
        self.assertEqual(set(s['accounting_school']), set(school.initial()))
        self.assertFalse([k for k in list(s) + list(s['journey']) if 'acct' in k or k.startswith('accounting_j')])
        j = s['journey']
        allowed = {cid for n in range(1, j['chapter'] + 1) for cid in jr.CH_UNLOCKS[n]}
        allowed |= {cid for cid, c in s['careers'].items() if c.get('started')}
        self.assertLessEqual(set(j['unlocked']), allowed)   # what a 1.4.20 validator checks
        self.assertNotIn('acct_check', json.dumps(s))

    def test_saves_cross_the_old_build_both_ways(self):
        old = os.environ.get('MNL_OLD_TREE')
        if not old:
            self.skipTest('MNL_OLD_TREE (a checkout of 9b72d27) not set')
        s = self.new_build_save()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action;'
                's=json.load(sys.stdin);validate_state(migrate_state(s));'
                's,_=apply_action(s,"grocery","select_career");print(json.dumps(s))')
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True,
                             cwd=old, env=dict(os.environ, PYTHONPATH=old + os.pathsep + os.environ.get('PYTHONPATH', '')))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = json.loads(out.stdout)
        validate_state(back)   # and this build loads what the old one wrote
        self.assertTrue(aj.certified(back, 'corp_accounting'))


if __name__ == '__main__':
    unittest.main()
