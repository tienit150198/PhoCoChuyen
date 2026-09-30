"""🎓 Certificates and 🚪 the back door (v0.9, story mode): two more ways into a job
after a failed interview, plus the standalone "Thi chứng chỉ" centre."""
import copy
import os
import unittest
from unittest.mock import patch

from game import certificates as ct
from game import employment as emp
from game import journey as jr
from game.content import CAREERS
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state

CID = 'delivery'          # a Chapter 1 workplace that hires (cv → trial)
POST = 'dl-rider'         # no reference check, no unsafe option
UNSAFE = 'dl-evening'     # has an unsafe trial step (dl_flood → ride)
GID = 'work_safety'


def here(cid):
    if cid not in CAREERS:
        raise unittest.SkipTest(cid + ' is filtered out by MNL_CAREERS')
    return cid


def story(seed=12345, wallet=None):
    s = new_state()
    jr.enable_story(s, seed)
    s['journey']['gender'] = 'female'
    if wallet is not None:
        s['journey']['wallet'] = wallet
    validate_state(s)
    return s


def act(s, where, action, **p):
    return apply_action(s, where, action, p)


def post_of(cid, pid):
    return next(p for p in emp.postings(cid) if p['id'] == pid)


def worst(cid, qid):
    """The lowest-scoring safe answer: a clear fail that a certificate may still rescue."""
    opts = [o for o in emp.question(cid, qid)['options'] if not o.get('fatal')]
    return min(opts, key=lambda o: o['score'])['id']


def unsafe(cid, qid):
    return next((o['id'] for o in emp.question(cid, qid)['options'] if o.get('fatal')), None) or worst(cid, qid)


def interview(s, cid=CID, pid=POST, pick=worst):
    """Apply (no lucky boss offer) and answer every step with `pick`. Returns (state, last result)."""
    post = post_of(cid, pid)
    with patch.object(emp, '_boss_chance', return_value=0):
        s, _ = act(s, cid, 'job_apply', posting=pid)
    r = None
    for _ in range(40):
        job = s['careers'][cid]['job']
        if job['status'] != 'applying':
            return s, r
        a = job['application']
        if a['stage'] == 'cv':
            off = [x for x in emp.STRENGTH_IDS if x not in post['wants']][:2]
            s, r = act(s, cid, 'job_cv', strengths=off, claims=['fresh'])
            continue
        q = next(x for x in emp.stage_steps(post, a['stage']) if x not in a['answers'])
        s, r = act(s, cid, 'job_answer', question=q, option=pick(cid, q))
    raise AssertionError('interview did not finish')


def next_life_day(s, cid='milk_tea'):
    """Live one day somewhere (the story clock moves on end_day)."""
    s, _ = act(s, cid, 'select_career')
    s, _ = act(s, cid, 'start_day')
    s, _ = act(s, cid, 'end_day', carry_event=True)
    return s


def sit(s, gid=GID, right=True):
    """Answer the open exam paper: all right, all wrong, or exactly `right` (an int) right answers."""
    qs = list(s['journey']['study']['paper']['qs'])
    r = None
    for i, q in enumerate(qs):
        good = ct.KEY[gid][q]['answer']
        ok = right if isinstance(right, bool) else i < right
        opt = good if ok else next(o['id'] for o in ct.KEY[gid][q]['options'] if o['id'] != good)
        s, r = act(s, None, 'jr_cert_answer', question=q, option=opt)
    return s, r


def certified(s, gid=GID, mode='self'):
    """Enrol, wait out the course on the life clock, pass the exam."""
    s, _ = act(s, None, 'jr_cert_enrol', cert=gid, mode=mode)
    while not public_state(s)['journey']['study']['ready_now']:
        s = next_life_day(s)
    s, r = sit(s, gid, True)
    return s, r


class Chance(unittest.TestCase):
    def test_boost_is_plus_fifty_points_capped_at_95(self):
        self.assertEqual(ct.CERT_BONUS_PP, 50)
        self.assertEqual(ct.CERT_CAP_PCT, 95)
        self.assertEqual(ct.boosted(0), 50)
        self.assertEqual(ct.boosted(20), 70)
        self.assertEqual(ct.boosted(45), 95)
        self.assertEqual(ct.boosted(60), 95)
        self.assertEqual(ct.boosted(99), 99)      # never lowers a chance
        self.assertEqual(ct.boosted(100), 100)    # a sure hire stays sure
        self.assertEqual(ct.boosted(-5), 50)

    def test_hire_chance_matches_the_deterministic_interview(self):
        self.assertEqual(emp.hire_chance(emp.PASS_SCORE, False), 100)
        self.assertEqual(emp.hire_chance(emp.PASS_SCORE, True), 100)
        self.assertEqual(emp.hire_chance(emp.PASS_SCORE - 1, False), 0)
        self.assertEqual(emp.hire_chance(0, True), ct.CERT_BONUS_PP)

    def test_groups_cover_every_hired_job_once(self):
        hired = {cid for cid in CAREERS if emp.required(cid)}
        self.assertEqual(hired, set(ct.BY_CAREER) & set(CAREERS))
        for g in ct.GROUPS:
            self.assertGreaterEqual(len(g['bank']), ct.DRAW + 4, g['id'])
            self.assertGreaterEqual(len(g['practice']), 3, g['id'])
            for q in g['bank'] + g['practice']:
                self.assertIn(q['answer'], [o['id'] for o in q['options']], q['text'])
                self.assertTrue(q['why'])
        self.assertTrue(6 <= ct.DRAW <= 10 and ct.PASS_MARK < ct.DRAW)


class GentleExam(unittest.TestCase):
    def test_every_question_has_a_hint_that_never_hides_the_answer(self):
        for g in ct.GROUPS:
            view = next(x for x in ct.content()['groups'] if x['id'] == g['id'])
            for q in g['bank']:
                h = view['questions'][q['id']]['hint']
                self.assertNotEqual(h['off'], q['answer'], q['id'])
                self.assertIn(h['off'], [o['id'] for o in q['options']])
                self.assertTrue(0 <= h['note'] < len(g['notes']))
                self.assertNotIn('answer', view['questions'][q['id']])

    def test_short_paper_and_a_low_bar(self):
        self.assertLessEqual(ct.DRAW, 6)
        self.assertLessEqual(ct.PASS_MARK / ct.DRAW, 0.7)
        self.assertLessEqual(ct.SELF_DAYS, 1)


class CertificateCourse(unittest.TestCase):
    def setUp(self):
        here(CID)

    def test_paid_class_debits_once_and_opens_the_exam_today(self):
        s = story()
        w = s['journey']['wallet']
        s, r = act(s, None, 'jr_cert_enrol', cert=GID, mode='class')
        j = s['journey']
        self.assertEqual(j['wallet'], w - ct.tuition(GID))
        rows = [h for h in j['history'] if h['kind'] == 'study']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['amount'], -ct.tuition(GID))
        self.assertEqual(j['study']['ready'], j['life_day'] + ct.CLASS_DAYS)
        with self.assertRaises(GameError):          # one course at a time, no second charge
            act(s, None, 'jr_cert_enrol', cert=GID, mode='class')
        self.assertEqual(s['journey']['wallet'], w - ct.tuition(GID))
        q = j['study']['paper']['qs'][0]
        self.assertEqual(ct.CLASS_DAYS, 0)          # crash class: sit the exam the same day
        s, _ = act(s, None, 'jr_cert_answer', question=q, option=ct.KEY[GID][q]['answer'])
        self.assertEqual(len([h for h in s['journey']['history'] if h['kind'] == 'study']), 1)

    def test_free_self_study_works_with_an_empty_wallet(self):
        s = story(wallet=0)
        with self.assertRaises(GameError):
            act(s, None, 'jr_cert_enrol', cert=GID, mode='class')
        s, _ = act(s, None, 'jr_cert_enrol', cert=GID, mode='self')
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['study']['ready'], s['journey']['life_day'] + ct.SELF_DAYS)
        s['journey']['wallet'] = 500       # keep the living costs from pausing the test story
        for _ in range(ct.SELF_DAYS):
            s = next_life_day(s)
        s, r = sit(s, GID, True)
        self.assertTrue(r['cert']['passed'])
        self.assertFalse([h for h in s['journey']['history'] if h['kind'] == 'study'])

    def test_pass_records_the_stable_shape(self):
        s = story()
        s, r = certified(s)
        rec = s['journey']['certificates'][GID]
        self.assertEqual(set(rec), {'score', 'best', 'earned_day', 'attempts'})
        self.assertEqual(rec, dict(score=100, best=100, earned_day=s['journey']['life_day'], attempts=1))
        self.assertTrue(r['cert']['earned_now'] and r['celebrate'])
        self.assertIsNone(s['journey']['study'])
        self.assertTrue(s['journey']['cert_paper']['passed'])
        pub = public_state(s)['journey']
        self.assertEqual(pub['certificates'][GID]['best'], 100)
        self.assertEqual(len(pub['cert_paper']['review']), ct.DRAW)
        with self.assertRaises(GameError):          # nothing left to improve
            act(s, None, 'jr_cert_enrol', cert=GID, mode='self')

    def test_fail_then_retake_with_a_new_paper_and_half_fee(self):
        s = story()
        s, _ = act(s, None, 'jr_cert_enrol', cert=GID, mode='class')
        first = list(s['journey']['study']['paper']['qs'])
        s = next_life_day(s)
        s, r = sit(s, GID, ct.PASS_MARK - 1)
        rec = s['journey']['certificates'][GID]
        self.assertFalse(r['cert']['passed'])
        self.assertEqual(rec['earned_day'], None)
        self.assertEqual(rec['attempts'], 1)
        self.assertEqual(rec['score'], ct.points(ct.PASS_MARK - 1))
        self.assertIsNone(ct.held_for(s, CID))
        w = s['journey']['wallet']
        s, _ = act(s, None, 'jr_cert_enrol', cert=GID, mode='class')
        self.assertEqual(s['journey']['wallet'], w - ct.retake_fee(GID))
        self.assertLess(ct.retake_fee(GID), ct.tuition(GID))
        self.assertNotEqual(s['journey']['study']['paper']['qs'], first)
        self.assertEqual(s['journey']['study']['paper']['attempt'], 2)
        s = next_life_day(s)
        s, r = sit(s, GID, ct.PASS_MARK)
        rec = s['journey']['certificates'][GID]
        self.assertTrue(r['cert']['passed'])
        self.assertEqual(rec['attempts'], 2)
        self.assertEqual(rec['score'], ct.PASS_POINTS)
        self.assertEqual(rec['best'], ct.PASS_POINTS)
        self.assertEqual(rec['earned_day'], s['journey']['life_day'])
        self.assertEqual(ct.held_for(s, CID), GID)

    def test_a_lower_retry_keeps_best_and_earned_day(self):
        s = story(wallet=500)
        s, _ = act(s, None, 'jr_cert_enrol', cert=GID, mode='self')
        for _ in range(ct.SELF_DAYS):
            s = next_life_day(s)
        s, _ = sit(s, GID, ct.DRAW - 1)
        day = s['journey']['certificates'][GID]['earned_day']
        s, _ = act(s, None, 'jr_cert_enrol', cert=GID, mode='self')
        for _ in range(ct.SELF_DAYS):
            s = next_life_day(s)
        s, _ = sit(s, GID, ct.PASS_MARK - 2)
        rec = s['journey']['certificates'][GID]
        self.assertEqual((rec['earned_day'], rec['best'], rec['attempts']), (day, ct.points(ct.DRAW - 1), 2))
        self.assertEqual(rec['score'], ct.points(ct.PASS_MARK - 2))

    def test_drop_needs_confirm_and_has_no_refund(self):
        s = story()
        s, _ = act(s, None, 'jr_cert_enrol', cert=GID, mode='class')
        w = s['journey']['wallet']
        with self.assertRaises(GameError):
            act(s, None, 'jr_cert_drop')
        s, _ = act(s, None, 'jr_cert_drop', confirm=True)
        self.assertIsNone(s['journey']['study'])
        self.assertEqual(s['journey']['wallet'], w)

    def test_sandbox_has_no_certificates(self):
        s = new_state()
        with self.assertRaises(GameError):
            act(s, None, 'jr_cert_enrol', cert=GID, mode='self')

    def test_paper_is_seeded(self):
        a, _ = act(story(), None, 'jr_cert_enrol', cert=GID, mode='self')
        b, _ = act(story(), None, 'jr_cert_enrol', cert=GID, mode='self')
        c, _ = act(story(seed=999), None, 'jr_cert_enrol', cert=GID, mode='self')
        self.assertEqual(a['journey']['study']['paper']['qs'], b['journey']['study']['paper']['qs'])
        self.assertNotEqual(a['journey']['study']['paper']['qs'], c['journey']['study']['paper']['qs'])

    def test_content_hides_the_exam_key(self):
        g = next(x for x in ct.content()['groups'] if x['id'] == GID)
        for q in g['questions'].values():
            self.assertNotIn('answer', q)
            self.assertNotIn('why', q)


class CertifiedInterview(unittest.TestCase):
    def setUp(self):
        here(CID)

    def test_failed_interview_without_certificate_has_no_roll(self):
        s, r = interview(story())
        job = s['careers'][CID]['job']
        self.assertEqual(job['status'], 'rejected')
        self.assertNotIn('chance', job['application'])
        self.assertNotIn('chance', r)

    def test_certificate_roll_is_stored_and_deterministic(self):
        base, _ = certified(story(wallet=500))
        a, ra = interview(copy.deepcopy(base))
        b, rb = interview(copy.deepcopy(base))
        ch = a['careers'][CID]['job']['application']['chance']
        self.assertEqual(ch, b['careers'][CID]['job']['application']['chance'])
        self.assertEqual(ch['pct'], ct.boosted(0))
        self.assertIsNone(ch['blocked'])
        self.assertEqual(ch['hired'], ch['roll'] < ch['pct'])
        self.assertEqual(a['careers'][CID]['job']['status'], 'offer' if ch['hired'] else 'rejected')
        self.assertEqual(ra['chance'], ch)
        self.assertIn(f'{ch["pct"]}%', ' '.join(a['careers'][CID]['job']['application']['feedback']))

    def test_hire_rate_over_many_seeds_is_about_half(self):
        hits = n = 0
        base, _ = certified(story(wallet=500))
        for seed in range(60):
            s = copy.deepcopy(base)
            s['journey']['seed'] = seed
            s, _ = interview(s)
            hits += s['careers'][CID]['job']['application']['chance']['hired']
            n += 1
        self.assertTrue(18 <= hits <= 42, hits)

    def test_lucky_hire_gets_an_offer_at_the_starting_wage(self):
        base, _ = certified(story(wallet=500))
        for seed in range(40):
            s = copy.deepcopy(base)
            s['journey']['seed'] = seed
            s, r = interview(s)
            if s['careers'][CID]['job']['application']['chance']['hired']:
                break
        else:
            self.fail('no lucky seed')
        job = s['careers'][CID]['job']
        self.assertEqual(job['status'], 'offer')
        self.assertEqual(job['offer']['salary'], post_of(CID, POST)['salary'][0])
        self.assertTrue(r['celebrate'])
        s, _ = act(s, CID, 'job_accept', confirm=True)
        self.assertEqual(s['careers'][CID]['job']['status'], 'hired')

    def test_an_unsafe_step_is_never_rescued(self):
        base, _ = certified(story(wallet=500))
        for seed in range(12):
            s = copy.deepcopy(base)
            s['journey']['seed'] = seed
            s, _ = interview(s, pid=UNSAFE, pick=unsafe)
            ch = s['careers'][CID]['job']['application']['chance']
            self.assertEqual((ch['blocked'], ch['pct'], ch['hired']), ('fatal', 0, False))
            self.assertEqual(s['careers'][CID]['job']['status'], 'rejected')

    def test_story_cooldown_counts_life_days(self):
        s, _ = interview(story())
        with self.assertRaises(GameError):
            act(s, CID, 'job_apply', posting=POST)
        s = next_life_day(s)
        with patch.object(emp, '_boss_chance', return_value=0):
            s, _ = act(s, CID, 'job_apply', posting=POST)     # used to be refused forever
        self.assertEqual(s['careers'][CID]['job']['status'], 'applying')


class BackDoor(unittest.TestCase):
    def setUp(self):
        here(CID)

    def rejected(self, **kw):
        s, _ = interview(story(**kw))
        self.assertEqual(s['careers'][CID]['job']['status'], 'rejected')
        return s

    def test_debits_once_and_hires_once(self):
        s = self.rejected()
        fee = emp.backdoor_fee(post_of(CID, POST))
        w = s['journey']['wallet']
        with self.assertRaises(GameError):
            act(s, CID, 'job_backdoor')                       # needs confirm
        s, r = act(s, CID, 'job_backdoor', confirm=True)
        job = s['careers'][CID]['job']
        self.assertTrue(r['backdoor'])
        self.assertEqual(job['status'], 'hired')
        self.assertEqual(job['salary'], post_of(CID, POST)['salary'][0])
        self.assertTrue(job['probation'])
        self.assertEqual(s['journey']['wallet'], w - fee)
        rows = [h for h in s['journey']['history'] if h['kind'] == 'backdoor']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['amount'], -fee)
        self.assertTrue(rows[0]['label'].startswith('Đi cửa sau'))
        with self.assertRaises(GameError):
            act(s, CID, 'job_backdoor', confirm=True)
        self.assertEqual(s['journey']['wallet'], w - fee)
        self.assertEqual(sum(1 for h in job['history'] if h['event'] == 'backdoor'), 1)
        self.assertEqual(s['careers'][CID]['metrics'].get('backdoor_hires'), 1)

    def test_once_per_workplace_even_after_quitting(self):
        s = self.rejected()
        s, _ = act(s, CID, 'job_backdoor', confirm=True)
        s, _ = act(s, CID, 'select_career')
        s, _ = act(s, CID, 'job_quit', confirm=True)
        self.assertEqual(s['careers'][CID]['job']['backdoor']['posting'], POST)
        s = next_life_day(s)
        s, _ = interview(s)
        with self.assertRaises(GameError):
            act(s, CID, 'job_backdoor', confirm=True)

    def test_needs_the_fee_and_a_rejection(self):
        s = story()
        with self.assertRaises(GameError):
            act(s, CID, 'job_backdoor', confirm=True)
        s = self.rejected(wallet=3)
        with self.assertRaises(GameError):
            act(s, CID, 'job_backdoor', confirm=True)
        self.assertEqual(s['careers'][CID]['job']['status'], 'rejected')
        self.assertEqual(s['journey']['wallet'], 3)

    def test_sandbox_has_no_back_door(self):
        s = new_state()
        with patch.object(emp, '_boss_chance', return_value=0):
            s, _ = act(s, CID, 'job_apply', posting=POST)
        post = post_of(CID, POST)
        s, _ = act(s, CID, 'job_cv', strengths=['calm'], claims=['fresh'])
        for q in emp.stage_steps(post, 'trial'):
            s, _ = act(s, CID, 'job_answer', question=q, option=worst(CID, q))
        self.assertEqual(s['careers'][CID]['job']['status'], 'rejected')
        with self.assertRaises(GameError):
            act(s, CID, 'job_backdoor', confirm=True)

    def test_no_back_door_for_a_licence_exam(self):
        cid = here('pharmacy')
        s = story()
        j = s['journey']
        j.update(chapter=4, done=[1, 2, 3])
        j['unlocked'] += [x for n in (2, 3, 4) for x in jr.CH_UNLOCKS[n] if x in CAREERS and x not in j['unlocked']]
        validate_state(s)
        with patch.object(emp, '_boss_chance', return_value=0):
            s, _ = act(s, cid, 'job_apply', posting='ph-evening')
        ex = emp.exam(cid)
        for q in list(s['careers'][cid]['job']['application']['exam']['qs']):
            good = next(x['answer'] for x in ex['bank'] if x['id'] == q)
            wrong = next(o['id'] for o in next(x for x in ex['bank'] if x['id'] == q)['options'] if o['id'] != good)
            s, _ = act(s, cid, 'job_exam', question=q, option=wrong)
        self.assertEqual(s['careers'][cid]['job']['status'], 'rejected')
        with self.assertRaises(GameError):
            act(s, cid, 'job_backdoor', confirm=True)

    def test_day_one_remark_is_logged_once(self):
        s = self.rejected()
        s, _ = act(s, CID, 'job_backdoor', confirm=True)
        s, _ = act(s, CID, 'select_career')
        s, r = act(s, CID, 'start_day')
        line = s['careers'][CID]['job']['backdoor']
        self.assertTrue(line['said'])
        said = [x for x in r.get('effects', []) if x in emp.BACKDOOR_REMARKS]
        self.assertEqual(len(said), 1)
        self.assertIn(said[0], [x['text'] for x in s['careers'][CID]['journal']])
        s, _ = act(s, CID, 'end_day', carry_event=True)
        s, r = act(s, CID, 'start_day')
        self.assertFalse([x for x in r.get('effects', []) if x in emp.BACKDOOR_REMARKS])

    def test_posting_content_lists_fee_and_helper(self):
        p = next(x for x in emp.content([CID])['postings'][CID] if x['id'] == POST)
        self.assertEqual(p['backdoor']['fee'], emp.backdoor_fee(post_of(CID, POST)))
        self.assertEqual(p['backdoor']['helper'], emp.backdoor_helper(post_of(CID, POST)))
        for line in emp.BACKDOOR_HELPERS:
            self.assertIn('“lo giúp”', line)


class Validation(unittest.TestCase):
    def setUp(self):
        here(CID)
        self.s, _ = certified(story(wallet=500))

    def bad(self, change):
        s = copy.deepcopy(self.s)
        change(s)
        with self.assertRaises(GameError):
            validate_state(s)

    def test_rejects_junk_certificates(self):
        validate_state(self.s)
        rec = lambda s: s['journey']['certificates'][GID]
        self.bad(lambda s: s['journey']['certificates'].update(nope=dict(score=1, best=1, earned_day=None, attempts=1)))
        self.bad(lambda s: rec(s).update(best=101))
        self.bad(lambda s: rec(s).update(best=10, score=50))
        self.bad(lambda s: rec(s).update(attempts=0))
        self.bad(lambda s: rec(s).update(earned_day=10**5))
        self.bad(lambda s: rec(s).update(best=ct.PASS_POINTS - 1, score=0))
        self.bad(lambda s: rec(s).update(extra=1))
        self.bad(lambda s: s['journey'].update(certificates=[]))

    def test_rejects_junk_study_and_papers(self):
        s = copy.deepcopy(self.s)
        s['journey']['certificates'].clear()
        s['journey']['cert_paper'] = None
        s, _ = act(s, None, 'jr_cert_enrol', cert=GID, mode='self')
        self.s = s
        st = lambda s: s['journey']['study']
        self.bad(lambda s: st(s).update(fee=5))                     # self-study is free
        self.bad(lambda s: st(s).update(ready=st(s)['start']))      # no shortcut
        self.bad(lambda s: st(s).update(cert='nope'))
        self.bad(lambda s: st(s)['paper'].update(qs=st(s)['paper']['qs'][:3]))
        self.bad(lambda s: st(s)['paper']['answers'].update(x='a'))

    def test_rejects_a_forged_graded_paper(self):
        self.bad(lambda s: s['journey']['cert_paper'].update(right=ct.DRAW - 1))
        self.bad(lambda s: s['journey']['cert_paper'].update(passed=False))
        self.bad(lambda s: s['journey']['cert_paper'].update(cert='teaching'))

    def test_rejects_forged_chance_and_back_door(self):
        s, _ = interview(copy.deepcopy(self.s))
        self.s = s
        ch = lambda s: s['careers'][CID]['job']['application']['chance']
        self.bad(lambda s: ch(s).update(pct=100))
        self.bad(lambda s: ch(s).update(hired=not ch(s)['hired']))
        self.bad(lambda s: ch(s).update(cert='teaching'))
        self.bad(lambda s: ch(s).update(blocked='fatal'))
        if s['careers'][CID]['job']['status'] == 'rejected':
            s, _ = act(s, CID, 'job_backdoor', confirm=True)
            self.s = s
            self.bad(lambda s: s['careers'][CID]['job']['backdoor'].update(posting='nope'))
            self.bad(lambda s: s['careers'][CID]['job']['backdoor'].update(said='yes'))


class OldSaves(unittest.TestCase):
    def test_journey_without_the_new_keys_loads(self):
        s = story()
        for k in ('certificates', 'study', 'cert_paper'):
            del s['journey'][k]
        for c in s['careers'].values():
            if isinstance(c.get('job'), dict):
                c['job'].pop('backdoor', None)
        s = migrate_state(s)
        validate_state(s)
        self.assertEqual(s['journey']['certificates'], {})
        self.assertIsNone(s['journey']['study'])


class DevQuickHire(unittest.TestCase):
    def setUp(self):
        here(CID)
        self.old = os.environ.get('MNL_DEV')

    def tearDown(self):
        if self.old is None:
            os.environ.pop('MNL_DEV', None)
        else:
            os.environ['MNL_DEV'] = self.old

    def test_job_quick_is_unchanged(self):
        os.environ.pop('MNL_DEV', None)
        s = story()
        with self.assertRaises(GameError):
            act(s, CID, 'job_quick', posting=POST, confirm=True)
        os.environ['MNL_DEV'] = '1'
        s, _ = act(s, CID, 'job_quick', posting=POST, confirm=True)
        job = s['careers'][CID]['job']
        self.assertEqual((job['status'], job['salary'], job['probation_left']),
                         ('hired', post_of(CID, POST)['salary'][0], post_of(CID, POST)['probation_days'] + 1))
        self.assertIsNone(job['backdoor'])
        self.assertFalse([h for h in s['journey']['history'] if h['kind'] in ('backdoor', 'study')])


if __name__ == '__main__':
    unittest.main()
