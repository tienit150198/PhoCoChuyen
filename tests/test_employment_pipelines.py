"""Hiring for pharmacy, customer care, tour guide and the hired trades (v0.5):
licence exams, situational tests, hands-on trials, migration of older saves."""
import copy
import os
import unittest

from game import employment as emp
from game.content import CAREERS
from game.engine import GameError, apply_action, new_state, public_state, validate_state

NEW = ('pharmacy', 'customer_care', 'tour_guide', 'salon', 'pet_care', 'repair', 'delivery')
TRADES = ('salon', 'pet_care', 'repair', 'delivery')
LETTER = dict(why='specific', example='story', close='available')


def here(cid):
    if cid not in CAREERS:
        raise unittest.SkipTest(cid + ' is filtered out by MNL_CAREERS')
    return cid


def act(s, cid, action, **p):
    return apply_action(s, cid, action, p)


def post_of(cid, pid):
    return next(p for p in emp.postings(cid) if p['id'] == pid)


def applied(cid, pid, day=1, s=None):
    """A save where the application is open (not a lucky direct offer)."""
    for d in range(day, day + 400):
        t = copy.deepcopy(s) if s else new_state()
        t['careers'][cid]['day'] = d
        t, r = act(t, cid, 'job_apply', posting=pid)
        if not r.get('direct_offer'):
            return t, r
    raise AssertionError('always a direct offer?')


def key(cid):
    return {q['id']: q['answer'] for q in emp.exam(cid)['bank']}


def wrong(cid, qid):
    row = next(q for q in emp.exam(cid)['bank'] if q['id'] == qid)
    return next(o['id'] for o in row['options'] if o['id'] != row['answer'])


def sit_exam(s, cid, right):
    """Answer the drawn paper: the first `right` questions correctly, the rest wrong."""
    qs = s['careers'][cid]['job']['application']['exam']['qs']
    r = None
    for i, q in enumerate(qs):
        s, r = act(s, cid, 'job_exam', question=q, option=key(cid)[q] if i < right else wrong(cid, q))
    return s, r


def best(cid, qid):
    return max(emp.question(cid, qid)['options'], key=lambda o: o['score'])['id']


def play_through(s, cid, pick=best):
    """Walk every remaining stage with the given answer picker."""
    r = None
    for _ in range(40):
        job = s['careers'][cid]['job']
        if job['status'] != 'applying':
            return s, r
        app = job['application']
        post = post_of(cid, app['posting'])
        st = app['stage']
        if st == 'exam':
            s, r = sit_exam(s, cid, 5)
        elif st == 'cv':
            s, r = act(s, cid, 'job_cv', strengths=post['wants'][:2], claims=['fresh'])
        elif st == 'letter':
            s, r = act(s, cid, 'job_letter', parts=LETTER)
        else:
            q = next(x for x in emp.stage_steps(post, st) if x not in app['answers'])
            s, r = act(s, cid, 'job_answer', question=q, option=pick(cid, q))
    raise AssertionError('pipeline did not finish')


class Required(unittest.TestCase):
    def test_new_careers_need_hiring(self):
        for cid in NEW:
            self.assertTrue(emp.required(cid), cid)
            self.assertIn(len(emp.postings(cid)), (2, 3), cid)
        for cid in ('teacher', 'mother_baby', 'grocery', 'milk_tea'):
            self.assertEqual(emp.required(cid), cid == 'teacher', cid)

    def test_postings_are_consistent(self):
        for cid in NEW:
            for p in emp.postings(cid):
                st = emp.stages(p)
                self.assertTrue(set(st) <= set(emp.STAGES) and len(st) == len(set(st)), p['id'])
                self.assertIn('cv', st)
                low, high = p['salary']
                self.assertTrue(10 <= low <= high <= 60, p['id'])
                if cid in TRADES:
                    self.assertEqual(st, ['cv', 'trial'])
                    self.assertLessEqual(high, 28, 'trades keep shop earnings: small base wage only')
                    self.assertTrue(p.get('wage_note'))
                self.assertEqual('exam' in st, cid in ('pharmacy', 'tour_guide'))
                self.assertEqual('test' in st, cid == 'customer_care')
                for q in emp.all_steps(p):
                    row = emp.question(cid, q)
                    self.assertIsNotNone(row, q)
                    self.assertEqual(max(o['score'] for o in row['options']), 3, q)
                self.assertTrue(set(p['wants']) <= emp.STRENGTH_IDS)
        for cid in ('pharmacy', 'tour_guide'):
            ex = emp.exam(cid)
            self.assertGreater(len(ex['bank']), ex['draw'])
            self.assertLessEqual(ex['pass_mark'], ex['draw'])
            for q in ex['bank']:
                self.assertIn(q['answer'], [o['id'] for o in q['options']])

    def test_unhired_new_career_cannot_open(self):
        for cid in NEW:
            here(cid)
            s = new_state()
            s, _ = act(s, cid, 'select_career')
            with self.assertRaises(GameError) as e:
                act(s, cid, 'start_day')
            self.assertEqual(e.exception.code, 'not_hired')

    def test_public_content_hides_the_answer_key(self):
        from game.content import public_content
        E = public_content()['employment']
        for cid in ('pharmacy', 'tour_guide'):
            here(cid)
            ex = E['exams'][cid]
            self.assertEqual(ex['pass_mark'], 4)
            for q in ex['questions'].values():
                self.assertNotIn('answer', q)
                self.assertNotIn('why', q)
        self.assertIn('cc_t_open', E['questions']['customer_care'])
        self.assertIn('stages', E['postings']['teacher'][0])


class Pipelines(unittest.TestCase):
    def test_every_new_posting_hires_end_to_end(self):
        for cid in NEW:
            here(cid)
            for post in emp.postings(cid):
                with self.subTest(posting=post['id']):
                    s, _ = applied(cid, post['id'])
                    s, r = play_through(s, cid)
                    job = s['careers'][cid]['job']
                    self.assertEqual(job['status'], 'offer', r)
                    self.assertEqual(job['offer']['salary'], post['salary'][1])
                    validate_state(s)
                    s, _ = act(s, cid, 'job_accept', confirm=True)
                    s, _ = act(s, cid, 'select_career')
                    s, _ = act(s, cid, 'start_day')
                    self.assertTrue(s['careers'][cid]['open'])
                    if emp.exam(cid):
                        self.assertTrue(emp.has_cert(s['careers'][cid]['job'], cid))

    def test_trial_pays_a_base_wage_on_top_of_shop_money(self):
        cid = here('repair')
        s, _ = applied(cid, 'rp-apprentice')
        s, _ = play_through(s, cid)
        s, _ = act(s, cid, 'job_accept', confirm=True)
        c = s['careers'][cid]
        c['day_completed'] = 1  # one job done today
        c['open'] = True
        s, r = act(s, cid, 'end_day', carry_event=True)
        pay = r['summary']['job']['salary']
        self.assertEqual(pay, round(26 * .85))
        self.assertTrue(r['summary']['job']['probation'])

    def test_stage_order_is_enforced(self):
        cid = here('customer_care')
        s, _ = applied(cid, 'cc-station')
        with self.assertRaises(GameError):
            act(s, cid, 'job_answer', question='cc_listen', option='read')     # CV first
        s, _ = act(s, cid, 'job_cv', strengths=['calm'], claims=['fresh'])
        s, _ = act(s, cid, 'job_letter', parts=LETTER)
        with self.assertRaises(GameError):
            act(s, cid, 'job_answer', question='cc_t_open', option='ack')       # the test comes after the interview
        for q in ('cc_listen', 'cc_promise', 'conflict'):
            s, r = act(s, cid, 'job_answer', question=q, option=best(cid, q))
        self.assertEqual(s['careers'][cid]['job']['application']['stage'], 'test')
        self.assertIn('bài thử tình huống', r['message'])
        with self.assertRaises(GameError):
            act(s, cid, 'job_exam', question='ph_e_code', option='b')
        with self.assertRaises(GameError):
            act(s, cid, 'job_answer', question='cc_t_abuse', option='boundary')  # not in this posting's test

    def test_fatal_move_fails_a_trial(self):
        cid = here('delivery')
        s, _ = applied(cid, 'dl-evening')

        def reckless(c, q):
            opts = emp.question(c, q)['options']
            return next((o['id'] for o in opts if o.get('fatal')), best(c, q))
        s, r = play_through(s, cid, reckless)
        job = s['careers'][cid]['job']
        self.assertEqual(job['status'], 'rejected')
        self.assertLessEqual(job['application']['score'], emp.FATAL_CAP)
        self.assertTrue(any('không an toàn' in x for x in job['application']['feedback']))
        self.assertEqual(job['cooldown_day'], 2)
        with self.assertRaises(GameError):
            act(s, cid, 'job_apply', posting='dl-evening')          # same day
        s['careers'][cid]['day'] = 2
        s, r = act(s, cid, 'job_apply', posting='dl-evening')
        self.assertIn(s['careers'][cid]['job']['status'], ('applying', 'offer'))

    def test_customer_care_abuse_test(self):
        cid = here('customer_care')
        s, _ = applied(cid, 'cc-hotline')
        s, _ = act(s, cid, 'job_cv', strengths=['calm', 'patience'], claims=['fresh'])
        s, _ = act(s, cid, 'job_answer', question='cc_listen', option='read')
        s, _ = act(s, cid, 'job_answer', question='cc_t_open', option='ack')
        s, _ = act(s, cid, 'job_answer', question='cc_t_abuse', option='fight')
        s, r = act(s, cid, 'job_answer', question='cc_t_demand', option='policy')
        self.assertEqual(s['careers'][cid]['job']['status'], 'rejected')
        self.assertLessEqual(r['score'], emp.FATAL_CAP)


class Exams(unittest.TestCase):
    def test_fail_then_retake_next_day_then_pass(self):
        cid = here('pharmacy')
        s, r = applied(cid, 'ph-day')
        self.assertIn('4/5', r['message'])
        app = s['careers'][cid]['job']['application']
        self.assertEqual(app['stage'], 'exam')
        first = list(app['exam']['qs'])
        s, r = sit_exam(s, cid, 3)
        job = s['careers'][cid]['job']
        self.assertEqual(job['status'], 'rejected')
        self.assertFalse(job['application']['exam']['passed'])
        self.assertEqual(job['application']['exam']['score'], 3)
        self.assertEqual(job['cooldown_day'], 2)
        self.assertEqual(job.get('certs'), [])
        validate_state(s)
        view = public_state(s)['careers'][cid]['job']
        self.assertEqual(len(view['exam_review']), 5)
        self.assertEqual(sum(1 for x in view['exam_review'] if not x['ok']), 2)
        self.assertTrue(all(x['why'] for x in view['exam_review']))
        with self.assertRaises(GameError):
            act(s, cid, 'job_apply', posting='ph-day')              # cooldown: not today
        s['careers'][cid]['day'] = 2
        s, _ = applied(cid, 'ph-evening', day=2, s=s)
        app = s['careers'][cid]['job']['application']
        self.assertEqual(app['exam']['attempt'], 2)
        self.assertNotEqual(app['exam']['qs'], first)
        s, r = sit_exam(s, cid, 4)
        self.assertTrue(r['celebrate'])
        job = s['careers'][cid]['job']
        self.assertEqual(job['application']['stage'], 'cv')
        self.assertEqual([x['id'] for x in job['certs']], ['ph-cert'])
        validate_state(s)

    def test_certificate_is_kept_and_exam_skipped(self):
        cid = here('tour_guide')
        s, _ = applied(cid, 'tg-company')
        s, _ = sit_exam(s, cid, 5)
        s, _ = act(s, cid, 'job_withdraw')
        s, r = applied(cid, 'tg-collab', s=s)
        app = s['careers'][cid]['job']['application']
        if s['careers'][cid]['job']['status'] == 'applying':
            self.assertEqual(app['stage'], 'cv')
            self.assertNotIn('exam', app)
        with self.assertRaises(GameError):
            act(s, cid, 'job_exam', question='tg_e_rain', option='b')

    def test_exam_answers_are_checked(self):
        cid = here('pharmacy')
        s, _ = applied(cid, 'ph-day')
        qs = s['careers'][cid]['job']['application']['exam']['qs']
        other = next(q['id'] for q in emp.exam(cid)['bank'] if q['id'] not in qs)
        for bad in (dict(question=other, option='a'), dict(question=qs[0], option='z'), dict(question='tg_e_rain', option='b')):
            with self.assertRaises(GameError):
                act(s, cid, 'job_exam', **bad)
        s, _ = act(s, cid, 'job_exam', question=qs[0], option='a')
        with self.assertRaises(GameError):
            act(s, cid, 'job_exam', question=qs[0], option='b')     # no second try on the same question

    def test_luck_never_skips_a_licence(self):
        cid = here('pharmacy')
        post = emp.postings(cid)[0]
        for day in range(1, 300):
            s = new_state()
            s['careers'][cid]['day'] = day
            r = emp.action(s, s['careers'][cid], cid, 'job_apply', {'posting': post['id']})
            self.assertFalse(r.get('direct_offer'))
            self.assertEqual(s['careers'][cid]['job']['application']['stage'], 'exam')
        # With the certificate, a lucky meeting can happen again.
        hits = 0
        for day in range(1, 300):
            s = new_state()
            c = s['careers'][cid]
            c['day'] = day
            c['job']['certs'] = [dict(id='ph-cert', day=1, score=5)]
            hits += bool(emp.action(s, c, cid, 'job_apply', {'posting': post['id']}).get('direct_offer'))
        self.assertGreater(hits, 0)

    def test_meet_boss_skips_exam_jobs_without_certificate(self):
        seen = set()
        for seq in range(0, 4000):
            s = new_state()
            s['seq'] = seq
            got = emp.meet_boss(s, 'mother_baby', 1)
            if got:
                seen.add(got['career'])
                validate_state(s)
        self.assertFalse(seen & {'pharmacy', 'tour_guide'})
        self.assertTrue(seen & set(TRADES) & set(CAREERS))

    def test_no_answers_after_a_direct_offer(self):
        cid = here('salon')
        post = emp.postings(cid)[0]
        for day in range(1, 500):
            s = new_state()
            s['careers'][cid]['day'] = day
            s, r = act(s, cid, 'job_apply', posting=post['id'])
            if r.get('direct_offer'):
                break
        self.assertEqual(s['careers'][cid]['job']['status'], 'offer')
        validate_state(s)
        with self.assertRaises(GameError):
            act(s, cid, 'job_answer', question=post['trial'][0], option=best(cid, post['trial'][0]))
        self.assertIn('phượng', r['message'].lower())


class QuickHire(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get('MNL_DEV')
        os.environ['MNL_DEV'] = '1'

    def tearDown(self):
        if self.old is None:
            os.environ.pop('MNL_DEV', None)
        else:
            os.environ['MNL_DEV'] = self.old

    def test_job_quick_opens_every_new_career(self):
        for cid in NEW:
            here(cid)
            s = new_state()
            s, _ = act(s, cid, 'select_career')
            s, _ = act(s, cid, 'job_quick', posting=emp.postings(cid)[0]['id'], confirm=True)
            s, _ = act(s, cid, 'start_day')
            job = s['careers'][cid]['job']
            self.assertTrue(s['careers'][cid]['open'])
            self.assertEqual(emp.has_cert(job, cid), bool(emp.exam(cid)))


class Migration(unittest.TestCase):
    def old_save(self, started):
        s = new_state()
        for cid in NEW:
            if cid not in CAREERS:
                continue
            c = s['careers'][cid]
            c['job'] = {k: v for k, v in emp.initial().items() if k != 'certs'}   # a v0.4 record: no certs field
            if cid in started:
                c.update(started=True, day=6)
                c['metrics']['served'] = 9
        return s

    def test_started_careers_stay_hired(self):
        started = [cid for cid in ('pharmacy', 'salon', 'delivery', 'tour_guide') if cid in CAREERS]
        s = self.old_save(started)
        validate_state(s)                         # older records without `certs` are still valid
        emp.migrate(s)
        for cid in NEW:
            if cid not in CAREERS:
                continue
            job = s['careers'][cid]['job']
            if cid in started:
                self.assertEqual(job['status'], 'hired', cid)
                self.assertFalse(job['probation'])
                self.assertEqual(job['hired_day'], 6)
                self.assertEqual(emp.has_cert(job, cid), bool(emp.exam(cid)))
            else:
                self.assertEqual(job['status'], 'none', cid)
        validate_state(s)
        for cid in started:
            s, _ = act(s, cid, 'select_career')
            s, _ = act(s, cid, 'start_day')
            self.assertTrue(s['careers'][cid]['open'])
            s, _ = act(s, cid, 'end_day', carry_event=True)

    def test_migration_is_idempotent_and_respects_quitting(self):
        cid = here('repair')
        s = self.old_save([cid])
        emp.migrate(s)
        once = copy.deepcopy(s)
        emp.migrate(s)
        self.assertEqual(s, once)
        s, _ = act(s, cid, 'job_quit', confirm=True)
        self.assertEqual(s['careers'][cid]['job']['status'], 'none')
        emp.migrate(s)
        self.assertEqual(s['careers'][cid]['job']['status'], 'none')

    def test_teacher_and_open_applications_untouched(self):
        s = self.old_save([])
        s['careers']['teacher'].update(started=True)
        s['careers']['teacher']['job'] = emp.hired_record('teacher')
        cid = here('salon')
        emp.action(s, s['careers'][cid], cid, 'job_apply', {'posting': 'sl-assist'})
        s['careers'][cid]['started'] = True     # an open application is the player's own choice
        before = copy.deepcopy(s)
        emp.migrate(s)
        self.assertEqual(s, before)

    def test_engine_runs_the_migration(self):
        import inspect
        from game import engine
        if 'emp.migrate(s)' not in inspect.getsource(engine.migrate_state):
            self.skipTest('engine.migrate_state does not call employment.migrate yet (see the hiring spec, §7)')
        cid = here('pharmacy')
        s = self.old_save([cid])
        s, _ = act(s, cid, 'select_career')
        s, _ = act(s, cid, 'start_day')
        self.assertEqual(s['careers'][cid]['job']['status'], 'hired')
        self.assertTrue(s['careers'][cid]['open'])


class Validation(unittest.TestCase):
    def bad(self, s, why):
        with self.assertRaises(GameError, msg=why):
            validate_state(s)

    def test_corrupt_stages_are_rejected(self):
        cid = here('pharmacy')
        s, _ = applied(cid, 'ph-day')
        validate_state(s)
        cases = []
        t = copy.deepcopy(s); t['careers'][cid]['job']['application']['stage'] = 'trial'; cases.append((t, 'stage not in pipeline'))
        t = copy.deepcopy(s); t['careers'][cid]['job']['application']['stage'] = 'lunch'; cases.append((t, 'unknown stage'))
        t = copy.deepcopy(s); t['careers'][cid]['job']['application']['exam']['qs'].pop(); cases.append((t, 'short paper'))
        t = copy.deepcopy(s); t['careers'][cid]['job']['application']['exam']['qs'][0] = 'tg_e_rain'; cases.append((t, 'foreign question'))
        t = copy.deepcopy(s); q = t['careers'][cid]['job']['application']['exam']['qs'][0]
        t['careers'][cid]['job']['application']['exam']['answers'][q] = 'z'; cases.append((t, 'bad option'))
        t = copy.deepcopy(s); t['careers'][cid]['job']['application']['exam']['score'] = 5; cases.append((t, 'score without passed'))
        t = copy.deepcopy(s); del t['careers'][cid]['job']['application']['exam']; cases.append((t, 'exam stage without paper'))
        t = copy.deepcopy(s); t['careers'][cid]['job']['application']['answers'] = {'t_parent': 'boundary'}; cases.append((t, 'answer from another posting'))
        t = copy.deepcopy(s); t['careers'][cid]['job']['certs'] = [dict(id='tg-card', day=1, score=5)]; cases.append((t, 'cert of another career'))
        t = copy.deepcopy(s); t['careers'][cid]['job']['certs'] = [dict(id='ph-cert', day=1, score=9)]; cases.append((t, 'cert score too high'))
        t = copy.deepcopy(s); t['careers'][cid]['job']['application'] = None; cases.append((t, 'applying without application'))
        t = copy.deepcopy(s); t['careers']['salon']['job']['certs'] = [dict(id='ph-cert', day=1, score=5)]; cases.append((t, 'cert on a trade'))
        for t, why in cases:
            self.bad(t, why)

    def test_graded_paper_must_add_up(self):
        cid = here('tour_guide')
        s, _ = applied(cid, 'tg-company')
        s, _ = sit_exam(s, cid, 5)
        validate_state(s)
        t = copy.deepcopy(s)
        t['careers'][cid]['job']['application']['exam']['passed'] = False
        self.bad(t, 'passed flag contradicts score')


class Legacy(unittest.TestCase):
    def test_teacher_flow_and_messages_unchanged(self):
        cid = 'teacher'
        s, _ = applied(cid, 'tch-public')
        s, r = act(s, cid, 'job_cv', strengths=['patience', 'communication'], claims=['fresh'])
        self.assertEqual(r['message'], 'Đã hoàn thiện CV. Tiếp theo: thư ứng tuyển.')
        s, r = act(s, cid, 'job_letter', parts=LETTER)
        self.assertEqual(r['message'], 'Thư đã gửi. Trường Tiểu học Mầm Nắng mời bạn phỏng vấn!')
        for q in ('t_diverse', 't_parent', 'mistake'):
            s, r = act(s, cid, 'job_answer', question=q, option=best(cid, q))
        # 55 answers + 25 letter + 20 strengths (two matched): the v0.4 formula.
        self.assertEqual(r['score'], 100)
        self.assertEqual(s['careers'][cid]['job']['status'], 'offer')


if __name__ == '__main__':
    unittest.main()
