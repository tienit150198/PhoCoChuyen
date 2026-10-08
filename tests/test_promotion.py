"""🎖️ Thăng tiến and 🧑‍💼 Ca quản lý (game/promotion.py).

The old-tree test runs the previous release's validate_state on saves this build writes (MNL_OLD_TREE, else
../_rel1431/mot-ngay-lam-nghe when it is there): journey['promo'] is a new optional key it must ignore."""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from game import promotion as pm
from game import promotion_content as PC
from game.engine import GameError, apply_action, public_state, validate_state
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]


def story(j, chapter=6):
    jr = j.state['journey']
    jr['story'] = True
    jr['chapter'] = chapter
    jr['done'] = list(range(1, chapter))
    from game.journey import CH_UNLOCKS
    for n in range(1, chapter + 1):
        for cid in CH_UNLOCKS.get(n, ()):
            if cid in j.state['careers'] and cid not in jr['unlocked']:
                jr['unlocked'].append(cid)


def day(j, done=2, **start):
    """One worked day: open (unless open), `done` jobs counted, close."""
    if not j.c['open']:
        j.act('start_day', **start)
    j.c['day_completed'] = max(j.c['day_completed'], done)
    return j.act('end_day', carry_event=True)


def best(qid):
    return max(PC.QUESTION_INDEX[qid]['options'], key=lambda o: o['score'])['id']


def worst(qid):
    return min(PC.QUESTION_INDEX[qid]['options'], key=lambda o: o['score'])['id']


def until_due(j, cap=40):
    for _ in range(cap):
        r = day(j)
        if pm.record(j.state, j.career)['due']:
            return r
    raise AssertionError('no review came')


def pass_review(j, ask='base'):
    rec = pm.record(j.state, j.career)
    for q in list(rec['due']['qs']):
        r = j.act('pm_answer', question=q, option=best(q))
    if pm.track(j.career) == 'emp':
        r = j.act('pm_ask', ask=ask)
    return r


def climb(j, to):
    while pm.record(j.state, j.career) is None or pm.record(j.state, j.career)['rank'] < to:
        until_due(j)
        pass_review(j)


def employee(cid='delivery'):
    j = Journey(cid)
    story(j)
    j.c['metrics']['served'] = 200
    return j


def owner(cid='pho'):
    j = Journey(cid)
    story(j)
    j.c['metrics']['served'] = 200
    return j


def run_board(j, accept_flawed=False):
    """Play a manager shift to the end the careful way (or accepting whatever comes back)."""
    for _ in range(pm.MAX_MOVES):
        v = j.c and public_state(j.state)['careers'][j.career]['promo']['shift']
        if v.get('esc'):
            j.act('pm_fix', option='a')
            continue
        done = [t for t in v['tasks'] if t['st'] == 'd']
        if done:
            j.act('pm_check', task=done[0]['i'], ok=accept_flawed or not done[0]['bad'])
            continue
        queue = [t for t in v['tasks'] if t['st'] == 'q']
        free = [m for m in v['team'] if not m['busy'] and not m['off']]
        if queue and free:
            t = queue[0]
            m = next((m for m in free if m['s'] == t['kind']), free[0])
            j.act('pm_assign', task=t['i'], mate=m['i'])
            continue
        if any(t['st'] == 'w' for t in v['tasks']):
            j.act('pm_wait')
            continue
        break
    return j.act('pm_close')


class Ladder(unittest.TestCase):
    def test_every_career_has_a_ladder(self):
        from game.engine import CAREERS
        for cid in CAREERS:
            tr = pm.track(cid)
            if tr == 'emp':
                self.assertIn(cid, PC.EMP_TITLES, cid)
            names = [pm.title({'journey': {'gender': g}}, {'job': {'title': 'X'}}, cid, n) for g in ('male', 'female', None) for n in range(1, 5)]
            self.assertTrue(all(names) and not any('{' in x for x in names), cid)

    def test_good_days_bring_a_review_and_no_sooner(self):
        j = employee()
        for _ in range(4):
            r = day(j)
            self.assertNotIn('due', r['summary']['promo'])
        r = day(j)
        self.assertIn('Sếp hẹn gặp', r['summary']['promo']['line'])
        self.assertEqual(pm.record(j.state, 'delivery')['due']['to'], 1)

    def test_weak_days_pause_and_never_go_down(self):
        j = employee()
        for _ in range(3):
            day(j)
        day(j, done=1)   # one job only: worked, not good
        rec = pm.record(j.state, 'delivery')
        self.assertEqual((rec['good'], rec['worked']), (3, 4))
        day(j, done=0)   # nothing done: not even a worked day
        self.assertEqual((rec['good'], rec['worked']), (3, 4))
        self.assertEqual(pm.record(j.state, 'delivery')['rank'], 0)

    def test_ratio_gate_of_the_first_step(self):
        j = employee()
        for _ in range(4):
            day(j, done=1)
        for _ in range(5):
            day(j)
        rec = pm.record(j.state, 'delivery')
        self.assertIsNone(rec['due'])   # 5 good of 9 worked < 70 %
        for _ in range(6):
            day(j)
        self.assertIsNotNone(pm.record(j.state, 'delivery')['due'])

    def test_probation_and_served_and_chapter_gates(self):
        j = employee()
        j.c['job']['probation'] = True
        j.c['job']['probation_left'] = 99
        self.assertEqual(pm.gate(j.state, j.c, 'delivery', pm.new_record()), 'Hết thử việc trước đã')
        j = employee()
        rec = pm.record(j.state, 'delivery', True)
        pm._sync(rec, j.c)
        rec['rank'] = 2
        j.c['metrics']['served'] = 10
        self.assertIn('40', pm.gate(j.state, j.c, 'delivery', rec))
        j.state['journey']['certificates']['work_safety'] = {'earned_day': 1}
        self.assertIsNone(pm.gate(j.state, j.c, 'delivery', rec))
        rec['rank'] = 3
        j.c['metrics']['served'] = 200
        story(j, chapter=4)
        self.assertEqual(pm.gate(j.state, j.c, 'delivery', rec), 'Tới chương 5')

    def test_accounting_follows_its_care_track(self):
        j = employee('corp_accounting')
        rec = pm.record(j.state, 'corp_accounting', True)
        pm._sync(rec, j.c)
        self.assertIn('bậc 2', pm.gate(j.state, j.c, 'corp_accounting', rec))
        j.c['ext']['data'].setdefault('care', {})['rank'] = 2
        self.assertIsNone(pm.gate(j.state, j.c, 'corp_accounting', rec))


class Review(unittest.TestCase):
    def test_raise_paid_salary_field_untouched(self):
        j = employee()
        base = j.c['job']['salary']
        until_due(j)
        r = pass_review(j)
        self.assertTrue(r['celebrate'])
        self.assertEqual(j.c['job']['salary'], base)
        r = day(j)
        self.assertEqual(r['summary']['job']['salary'], round(base * 1.08))
        self.assertEqual(public_state(j.state)['careers']['delivery']['job']['salary'], round(base * 1.08))
        validate_state(j.state)

    def test_fair_ask_adds_points_only_with_best_answers(self):
        j = employee()
        until_due(j)
        pass_review(j, ask='fair')
        self.assertEqual(pm.raise_pct(j.state, j.c, 'delivery'), 10)
        j2 = employee()
        until_due(j2)
        rec = pm.record(j2.state, 'delivery')
        q1, q2 = rec['due']['qs']
        ok = next(o['id'] for o in PC.QUESTION_INDEX[q2]['options'] if o['score'] == 1)
        j2.act('pm_answer', question=q1, option=best(q1))
        j2.act('pm_answer', question=q2, option=ok)
        j2.act('pm_ask', ask='fair')
        self.assertEqual(pm.raise_pct(j2.state, j2.c, 'delivery'), 8)

    def test_high_ask_without_best_answers_waits_three_days(self):
        j = employee()
        until_due(j)
        rec = pm.record(j.state, 'delivery')
        q1, q2 = rec['due']['qs']
        ok = next(o['id'] for o in PC.QUESTION_INDEX[q1]['options'] if o['score'] == 1)
        j.act('pm_answer', question=q1, option=ok)
        j.act('pm_answer', question=q2, option=best(q2))
        r = j.act('pm_ask', ask='high')
        self.assertTrue(r['later'])
        rec = pm.record(j.state, 'delivery')
        self.assertEqual((rec['rank'], rec['wait'], rec['due']), (0, pm.RETRY, None))
        for _ in range(pm.RETRY - 1):
            day(j)
        self.assertIsNone(pm.record(j.state, 'delivery')['due'])
        day(j)
        self.assertIsNotNone(pm.record(j.state, 'delivery')['due'])

    def test_a_zero_answer_is_a_later_not_a_fall(self):
        j = employee()
        until_due(j)
        rec = pm.record(j.state, 'delivery')
        q1, q2 = rec['due']['qs']
        j.act('pm_answer', question=q1, option=worst(q1))
        r = j.act('pm_answer', question=q2, option=best(q2))
        self.assertTrue(r['later'])
        self.assertEqual(pm.record(j.state, 'delivery')['rank'], 0)
        with self.assertRaises(GameError):
            j.act('pm_ask', ask='base')
        # #11: the reason and the next try are said, not left to guess
        q = PC.QUESTION_INDEX[q1]
        bad = next(o['label'] for o in q['options'] if o['score'] == 0)
        self.assertIn(q['text'], r['message'])
        self.assertIn(bad, r['message'])
        self.assertIn(f'{pm.RETRY} ngày làm', r['message'])
        self.assertEqual((r['review']['why'], r['review']['wait']), ('zero', pm.RETRY))
        self.assertEqual([x['score'] for x in r['review']['rows']], [0, 2])

    def test_high_ask_says_which_answer_was_short(self):
        j = employee()
        until_due(j)
        q1, q2 = pm.record(j.state, 'delivery')['due']['qs']
        ok = next(o['id'] for o in PC.QUESTION_INDEX[q1]['options'] if o['score'] == 1)
        j.act('pm_answer', question=q1, option=ok)
        j.act('pm_answer', question=q2, option=best(q2))
        r = j.act('pm_ask', ask='high')
        self.assertIn(PC.QUESTION_INDEX[q1]['text'], r['message'])
        self.assertIn('Xin hợp lý', r['message'])
        self.assertEqual(r['review']['why'], 'high')
        validate_state(j.state)

    def test_answers_in_order_and_once(self):
        j = employee()
        until_due(j)
        q1, q2 = pm.record(j.state, 'delivery')['due']['qs']
        with self.assertRaises(GameError):
            j.act('pm_answer', question=q2, option='a')
        with self.assertRaises(GameError):
            j.act('pm_answer', question=q1, option='z')
        with self.assertRaises(GameError):
            j.act('pm_ask', ask='base')

    def test_probation_rate_and_x3_and_cap(self):
        j = employee('corp_accounting')
        rec = pm.record(j.state, 'corp_accounting', True)
        pm._sync(rec, j.c)
        rec['rank'] = 4
        base = j.c['job']['salary']
        with mock.patch('game.accounting_school.salary_multiplier', return_value=3):
            r = day(j)
        self.assertEqual(r['summary']['job']['salary'], min(600, round(base * 1.55) * 3))
        j.c['job']['probation'] = True
        j.c['job']['probation_left'] = 5
        r = day(j)
        self.assertEqual(r['summary']['job']['salary'], round(base * 1.55 * .85))
        with mock.patch('game.accounting_school.salary_multiplier', return_value=5):
            j.c['job']['probation'] = False
            r = day(j)
        self.assertEqual(r['summary']['job']['salary'], 600)

    def test_quitting_starts_the_ladder_again(self):
        j = employee()
        climb(j, 1)
        log = list(pm.record(j.state, 'delivery')['log'])
        j.act('job_quit', confirm=True)
        self.assertIsNone(pm.public(j.state, j.c, 'delivery'))
        self.assertEqual(pm.raise_pct(j.state, j.c, 'delivery'), 0)
        from game.employment import hired_record
        j.c['job'] = hired_record('delivery', None, j.c['day'])
        j.c['job']['history'] = [{'day': 1, 'event': 'hired', 'posting': 'dl-rider'}]
        self.assertEqual(pm.public(j.state, j.c, 'delivery')['rank'], 0)
        day(j)
        rec = pm.record(j.state, 'delivery')
        self.assertEqual((rec['rank'], rec['log']), (0, log))

    def test_owner_review_has_no_pay_ask_and_tips_follow(self):
        j = owner()
        until_due(j)
        r = pass_review(j)
        self.assertIn('boa thêm 3%', r['message'])
        with self.assertRaises(GameError):
            j.act('pm_ask', ask='base')
        j.act('start_day')
        j.c['day_completed'] = 2
        from game import engine
        engine.money(j.state, j.c, 200, 'Hoàn thành: test', None, 'revenue')
        r = j.act('end_day', carry_event=True)
        self.assertEqual(r['summary']['promo']['tip'], 6)
        self.assertEqual(r['summary']['net'], 206)

    def test_owner_rating_gate(self):
        j = owner()
        rec = pm.record(j.state, 'pho', True)
        rec['rank'] = 1
        j.c['feed'].append(dict(j.c['feed'][0], stars=2, kind='review') if j.c['feed'] else
                           dict(id='post-x', npc='player', author='x', text='x', day=1, source='x', stars=2, kind='review', comments=[], liked=False))
        self.assertIn('★4.0', pm.gate(j.state, j.c, 'pho', rec) or '')

    def test_reset_career_forgets(self):
        j = owner()
        climb(j, 1)
        j.act('reset_career', confirm='BAT DAU LAI')
        self.assertIsNone(pm.record(j.state, 'pho'))


class Manager(unittest.TestCase):
    def test_not_before_step_three(self):
        j = employee()
        with self.assertRaises(GameError):
            j.act('start_day', manager=True)
        self.assertFalse(public_state(j.state)['careers']['delivery']['promo']['mgr'])

    def test_employee_shift(self):
        j = employee()
        climb(j, 3)
        before = j.c['money']
        r = j.act('start_day', manager=True)
        self.assertIn('Ca quản lý', r['message'])
        self.assertFalse([t for t in j.c['tasks'] if t['day'] == j.c['day']])
        with self.assertRaises(GameError):
            j.act('more_work')
        v = public_state(j.state)['careers']['delivery']['promo']['shift']
        self.assertEqual((len(v['tasks']), len(v['team'])), (6, 2))
        self.assertTrue(all(t['t'] for t in v['tasks']))
        r = run_board(j)
        self.assertEqual(r['manager']['good'], 6)
        self.assertEqual(r['manager']['bonus'], 60)
        with self.assertRaises(GameError):
            j.act('pm_wait')
        r = j.act('end_day')
        s = r['summary']
        self.assertTrue(s['promo']['good'])
        self.assertGreater(s['job']['salary'], 0)
        self.assertEqual(s['net'], 60 + s['job']['salary'])
        self.assertIsNone(pm.record(j.state, 'delivery')['shift'])
        self.assertGreater(j.c['money'] + s['job']['salary'], before)   # the salary went on to the wallet
        validate_state(j.state)

    def test_owner_shift_team_is_staff_plus_helpers(self):
        j = owner('pho')
        climb(j, 3)
        from game import operations as ops
        cand = ops.CANDIDATE_INDEX['pho-staff-1']
        j.act('ops_hire', candidate=cand['id'], confirm=True)
        j.act('start_day', manager=True)
        team = pm.record(j.state, 'pho')['shift']['team']
        self.assertEqual([m['tmp'] for m in team], [False, True])
        self.assertEqual(team[0]['name'], cand['name'])
        r = run_board(j)
        self.assertEqual(r['manager']['wage'], pm.HELPER_WAGE)
        ledger = j.c['ops']['finance']['ledger']
        self.assertTrue(any(x['category'] == 'revenue' and x['reason'].startswith('🧑‍💼') for x in ledger))
        validate_state(j.state)
        j.act('end_day')

    def test_catching_mistakes_pays_and_lazy_checks_pay_less(self):
        j1, j2 = employee(), employee()
        climb(j1, 3)
        climb(j2, 3)
        j1.act('start_day', manager=True)
        j2.act('start_day', manager=True)
        careful = run_board(j1)['manager']
        lazy = run_board(j2, accept_flawed=True)['manager']
        self.assertGreaterEqual(careful['pts'], lazy['pts'])
        self.assertGreaterEqual(careful['good'], lazy['good'])

    def test_close_by_end_day_still_pays(self):
        j = employee()
        climb(j, 3)
        j.act('start_day', manager=True)
        v = public_state(j.state)['careers']['delivery']['promo']['shift']
        j.act('pm_assign', task=0, mate=0)
        for _ in range(3):
            v = public_state(j.state)['careers']['delivery']['promo']['shift']
            if v['tasks'][0]['st'] == 'd' or v.get('esc'):
                break
            j.act('pm_wait')
        if v.get('esc'):
            j.act('pm_fix', option='b')
        v = public_state(j.state)['careers']['delivery']['promo']['shift']
        if v['tasks'][0]['st'] != 'd':
            j.act('pm_wait')
        j.act('pm_check', task=0, ok=True)
        r = j.act('end_day')
        self.assertEqual(r['summary']['promo']['manager']['done'], 1)
        self.assertGreater(r['summary']['job']['salary'], 0)
        self.assertFalse(r['summary']['promo']['good'])   # 1 of 6: only less bonus, nothing else

    def test_board_rules(self):
        j = employee()
        climb(j, 3)
        j.act('start_day', manager=True)
        j.act('pm_assign', task=0, mate=0)
        with self.assertRaises(GameError):
            j.act('pm_assign', task=1, mate=0)   # busy
        with self.assertRaises(GameError):
            j.act('pm_assign', task=0, mate=1)   # already given
        with self.assertRaises(GameError):
            j.act('pm_check', task=1, ok=True)   # not done
        with self.assertRaises(GameError):
            j.act('pm_assign', task=99, mate=1)
        with self.assertRaises(GameError):
            j.act('pm_assign', task='0', mate=1)

    def test_escalation_blocks_until_settled(self):
        j = employee()
        climb(j, 3)
        j.act('start_day', manager=True)
        sh = pm.record(j.state, 'delivery')['shift']
        first = sh['esc'][0]['at']
        j.act('pm_assign', task=0, mate=0)
        j.act('pm_assign', task=1, mate=1)
        while sh['n'] < first:
            v = public_state(j.state)['careers']['delivery']['promo']['shift']
            done = [t for t in v['tasks'] if t['st'] == 'd']
            if done:
                j.act('pm_check', task=done[0]['i'], ok=True)
            else:
                j.act('pm_wait')
            sh = pm.record(j.state, 'delivery')['shift']
        v = public_state(j.state)['careers']['delivery']['promo']['shift']
        self.assertIn('esc', v)
        self.assertNotIn('{', v['esc']['text'])
        with self.assertRaises(GameError):
            j.act('pm_close')
        j.act('pm_fix', option='a')
        self.assertNotIn('esc', public_state(j.state)['careers']['delivery']['promo']['shift'])

    def test_every_career_can_run_a_board(self):
        from game.engine import CAREERS
        for cid in CAREERS:
            with self.subTest(cid):
                try:
                    j = Journey(cid)
                except unittest.SkipTest:
                    continue
                story(j)
                if j.c['open']:
                    j.act('end_day', carry_event=True)
                rec = pm.record(j.state, cid, True)
                if pm.track(cid) == 'emp':
                    pm._sync(rec, j.c)
                rec['rank'] = 3
                try:
                    j.act('start_day', manager=True)
                except GameError as e:
                    if getattr(e, 'code', '') in ('need_cert', 'acct_check', 'locked'):
                        continue   # this career's own morning gate (exam, check) comes first
                    raise
                r = run_board(j)
                self.assertEqual(r['manager']['done'], r['manager']['size'])
                validate_state(j.state)
                r = j.act('end_day', carry_event=True)
                self.assertIn('manager', r['summary']['promo'])

    def test_certified_accountant_check_and_manager_ride_together(self):
        """💼 The entry check comes first; the client resends start_day with the paper and {manager: true}."""
        from tests import test_accounting_jobs as ta
        cid = 'corp_accounting'
        s = ta.hire(ta.with_certs(ta.story(1), ['basic']), cid)
        rec = pm.new_record()
        rec.update(emp=s['careers'][cid]['job']['employer'], hd=s['careers'][cid]['job']['hired_day'], rank=3)
        s['journey']['promo'] = {cid: rec}
        with mock.patch.dict(os.environ, {'MNL_HOLIDAY_OFF': '1'}):
            s, _ = apply_action(s, cid, 'select_career')
            with self.assertRaises(GameError) as e:
                apply_action(s, cid, 'start_day', {'manager': True})
            self.assertEqual(e.exception.code, 'acct_check')
            s, _ = apply_action(s, cid, 'start_day', {'acct_check': ta.paper(s, cid), 'manager': True})
        self.assertTrue(pm.managing(s, s['careers'][cid], cid))
        self.assertEqual(public_state(s)['careers'][cid]['more_gate']['why'], 'manager')
        validate_state(s)


class Saves(unittest.TestCase):
    def test_tampering_is_refused(self):
        j = employee()
        climb(j, 3)
        j.act('start_day', manager=True)
        for path, value in ((('rank',), 9), (('extra',), 99), (('due',), {'to': 1}), (('shift', 'tasks', 0, 'st'), 'x'),
                            (('shift', 'team', 0, 's'), 'magic'), (('shift', 'size'), 99), (('log',), [{}])):
            s = copy.deepcopy(j.state)
            o = s['journey']['promo']['delivery']
            for k in path[:-1]:
                o = o[k]
            o[path[-1]] = value
            with self.assertRaises(GameError, msg=repr(path)):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['journey']['promo']['nowhere'] = pm.new_record()
        with self.assertRaises(GameError):
            validate_state(s)

    def test_older_save_without_the_key(self):
        j = employee()
        self.assertNotIn('promo', j.state['journey'])
        validate_state(j.state)
        self.assertEqual(pm.public(j.state, j.c, 'delivery')['rank'], 0)

    def test_journey_view_does_not_grow(self):
        j = employee()
        climb(j, 3)
        j.act('start_day', manager=True)
        v = public_state(j.state)
        self.assertNotIn('promo', v['journey'])
        bare = copy.deepcopy(j.state)
        del bare['journey']['promo']
        flat = lambda x: json.dumps({k: y for k, y in x.items() if k != 'abroad'}, ensure_ascii=False)   # 🌏 quotes the raised day pay
        self.assertEqual(flat(v['journey']), flat(public_state(bare)['journey']))
        self.assertLess(len(json.dumps(v['careers']['delivery']['promo'], ensure_ascii=False)), 2600)
        self.assertNotIn('promo', v['careers']['pho'])   # careers not on screen: summary stubs only

    def old_tree(self):
        old = os.environ.get('MNL_OLD_TREE') or str(ROOT.parent / '_rel1431' / 'mot-ngay-lam-nghe')
        if not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no 1.4.31 tree (MNL_OLD_TREE)')
        return old

    def run_old(self, old, prog, s):
        env = dict(os.environ, PYTHONPATH=old + os.pathsep + os.environ.get('PYTHONPATH', ''))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        return json.loads(out.stdout)

    def test_saves_cross_the_previous_build(self):
        old = self.old_tree()
        from tests.test_career_pho import rollback_strip
        prog = ('import json,sys\nfrom game.engine import validate_state,apply_action\n'
                's=json.load(sys.stdin)\nvalidate_state(s)\n'
                'c=s["careers"][s["current"]]\n'
                'if c["open"]:\n s,_=apply_action(s,s["current"],"end_day",{"carry_event":True})\n'
                's,_=apply_action(s,s["current"],"start_day",{})\n'
                'print(json.dumps(s))')
        saves = []
        j = employee()
        climb(j, 3)
        until_due(j)                       # a review waiting, one answer given
        q = pm.record(j.state, 'delivery')['due']['qs'][0]
        j.act('pm_answer', question=q, option=best(q))
        saves.append(copy.deepcopy(j.state))
        j.act('start_day', manager=True)  # a manager board half played
        j.act('pm_assign', task=0, mate=0)
        saves.append(copy.deepcopy(j.state))
        o = owner('tra_da')
        climb(o, 3)
        o.act('start_day', manager=True)
        run_board(o)
        saves.append(copy.deepcopy(o.state))
        for s in saves:
            validate_state(s)
            back = self.run_old(old, prog, rollback_strip(s))
            self.assertIn('promo', back['journey'])
            # ...and what the old build wrote comes back here: a stale board is dropped, the ladder is kept.
            from tests.test_career_pho import ADDED
            for cid in ADDED:
                back['careers'][cid] = copy.deepcopy(s['careers'][cid])
            validate_state(back)
            cur = back['current']
            rec = back['journey']['promo'][cur]
            self.assertGreaterEqual(rec['rank'], 3)
            back, _ = apply_action(back, cur, 'end_day', {'carry_event': True})
            self.assertIsNone(back['journey']['promo'][cur]['shift'])
            validate_state(back)


if __name__ == '__main__':
    unittest.main()
