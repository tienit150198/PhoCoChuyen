"""🛃 Hải quan cửa khẩu Bến Mây (owner spec 14/10, I.; game/careers/customs.py, game/gov_rules.py, game/org_content.py
'hq', game/npc_complaints.py, employment EXAMS['customs']): who may apply (3 chapters, Hạ sĩ of Công an, at most 3
violations, never expelled), the owner's eight exam questions verbatim, the ladder, the four kinds of work (evidence
steps, final decisions, temptations found out by the thanh tra), the complaints after a shift, strict saves, and the
dormant record a never-used customs career leaves out of the stored text (older builds still read the save)."""
import copy
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import Journey
from game import employment as emp
from game import gov_rules as gr
from game import npc_complaints as NC
from game import org as ORG
from game import org_content as OC
from game import promotion as pm
from game.careers import PLUGINS
from game.engine import (DORMANT, GameError, apply_action, dormant_out, initial_career, make_task, migrate_state, new_state,
                         public_state, validate_state, wake)

P = PLUGINS.get('customs')
if P is not None:
    from game.careers import customs_content as CC

ROOT = Path(__file__).resolve().parents[1]
POLICE = OC.ORGS['cand']['grades']


def gi_police(gid):
    return next(i for i, g in enumerate(POLICE) if g['id'] == gid)


def gi(gid):
    return next(i for i, g in enumerate(OC.HQ_GRADES) if g['id'] == gid)


def where(kind, tempt=None):
    """The first (day, slot) whose generated task is of `kind` (and carries the temptation `tempt`, or none when False)."""
    for d in range(1, 300):
        for s in range(1, 9):
            t = P.make_task(d, s, 1)
            tp = t['needs'].get('tempt')
            if t['kind'] != kind:
                continue
            if tempt is False and tp:
                continue
            if tempt and (not tp or tp['kind'] != tempt):
                continue
            return d, s
    raise AssertionError((kind, tempt))


def at(kind, tempt=False):
    d, s = where(kind, tempt)
    j = Journey('customs', slot=s, day=d)
    j.act('hq_intro')
    j.tid = j.task['id']
    return j


def cur(j):
    """The task being played (the active task moves on once it closes)."""
    return j.get(j.tid)


def step(j, value=None):
    t = cur(j)
    st = t['needs']['steps'][t['at']]
    return j.act('hq_step', task=t['id'], step=st['id'], value=t['_key'][st['id']] if value is None else value)


def play(j, upto=None):
    """Answer every step right (until the step `upto`)."""
    tid = j.tid
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    r = None
    for _ in range(12):
        t = j.get(tid)
        if t['status'] == 'completed' or (upto and t['needs']['steps'][t['at']]['id'] == upto):
            return r
        r = step(j)
    raise AssertionError('task never closed')


def wrong(t, sid):
    st = next(x for x in t['needs']['steps'] if x['id'] == sid)
    right = t['_key'][sid]
    if 'options' in st:
        return next(o['id'] for o in st['options'] if o['id'] != right)
    return right + 1


def officer(post='hq_ktv', grade='ktv_1'):
    """A customs officer on the ladder (hired, one close done), shift open."""
    j = Journey('customs')
    rec = pm.record(j.state, 'customs', True)
    pm._sync(rec, j.c)
    rec['worked'] = 0
    j.act('end_day', carry_event=True)
    j.act('start_day')
    x = org(j)
    x['p'], x['g'] = post, gi(grade)
    j.act('hq_intro')
    return j


def org(j):
    return pm.record(j.state, 'customs')['org']


@unittest.skipIf(P is None, 'customs filtered out')
class Exam(unittest.TestCase):
    """1.1.1 Bài kiểm tra sát hạch: the owner's eight questions, answers B A B D C C B C, pass at 6/8."""

    def test_the_owners_questions_and_answers(self):
        ex = emp.exam('customs')
        self.assertEqual((ex['pass_mark'], ex['draw'], len(ex['bank'])), (6, 8, 8))
        self.assertEqual([q['answer'] for q in ex['bank']], list('babdccbc'))
        q1 = ex['bank'][0]
        self.assertIn('ngoại tệ vượt quá định mức', q1['text'])
        self.assertEqual([o['label'] for o in q1['options']], ['Cửa miễn khai báo (luồng xanh)', 'Cửa báo Hải quan (luồng đỏ)',
                                                               'Không cần đi qua cửa nào, có thể đi thẳng ra ngoài', 'Cửa ưu tiên dành cho phi hành đoàn'])
        q8 = ex['bank'][7]
        self.assertIn('em gửi sếp tí bỉm sữa cho con cháu', q8['options'][0]['label'])

    def eligible(self):
        s = new_state()
        s['journey'][ORG.SVC_KEY] = dict(v=1, top={'police': gi_police('ha_si')})
        validate_state(s)
        return s

    def apply(self, s, right_n):
        s, _ = apply_action(s, 'customs', 'job_apply', dict(posting='hq-ktv'))
        a = s['careers']['customs']['job']['application']
        self.assertEqual(a['stage'], 'exam')
        key = {q['id']: q['answer'] for q in emp.exam('customs')['bank']}
        r = None
        for i, q in enumerate(a['exam']['qs']):
            opt = key[q] if i < right_n else next(o['id'] for o in next(x for x in emp.exam('customs')['bank'] if x['id'] == q)['options'] if o['id'] != key[q])
            s, r = apply_action(s, 'customs', 'job_exam', dict(question=q, option=opt))
        return s, r

    def test_six_right_pass_five_fail_and_wait_a_day(self):
        s, r = self.apply(self.eligible(), 6)
        self.assertTrue(r['exam']['passed'])
        self.assertEqual(s['careers']['customs']['job']['application']['stage'], 'cv')
        s, r = self.apply(self.eligible(), 5)
        self.assertFalse(r['exam']['passed'])
        job = s['careers']['customs']['job']
        self.assertEqual(job['status'], 'rejected')
        with self.assertRaises(GameError) as e:
            apply_action(s, 'customs', 'job_apply', dict(posting='hq-ktv'))
        self.assertEqual(e.exception.code, 'retry_later')


@unittest.skipIf(P is None, 'customs filtered out')
class Entry(unittest.TestCase):
    """Who may apply: each condition shown, met or not, and enforced by the server."""

    def rows(self, s):
        return {r['id']: r for r in gr.entry_rows(s)}

    def test_no_police_past_is_refused_and_shown(self):
        s = new_state()
        rows = self.rows(s)
        self.assertTrue(rows['chapters']['met'])           # no story: nothing to wait for
        self.assertFalse(rows['police']['met'])
        self.assertIn('chưa từng làm Công an', rows['police']['label'])
        self.assertEqual(public_state(s, 'customs')['careers']['customs']['job']['entry'], gr.entry_rows(s))
        with self.assertRaises(GameError) as e:
            apply_action(s, 'customs', 'job_apply', dict(posting='hq-ktv'))
        self.assertEqual(e.exception.code, 'entry_rules')
        self.assertIn('Hạ sĩ', str(e.exception))

    def test_binh_nhat_is_not_enough_ha_si_is(self):
        s = new_state()
        s['journey'][ORG.SVC_KEY] = dict(v=1, top={'police': gi_police('binh_nhat')})
        self.assertFalse(self.rows(s)['police']['met'])
        s['journey'][ORG.SVC_KEY]['top']['police'] = gi_police('ha_si')
        self.assertTrue(all(r['met'] for r in gr.entry_rows(s)))
        self.assertIsNone(gr.entry_block(s))

    def test_a_police_grade_held_now_counts(self):
        from tests.test_org_police import officer as cop
        j = cop('to_vien', 'ha_si')
        self.assertTrue(self.rows(j.state)['police']['met'])

    def test_more_than_three_violations_or_a_ban_bar_the_door(self):
        s = new_state()
        s['journey'][ORG.SVC_KEY] = dict(v=1, police=4, top={'police': gi_police('thuong_si')})
        rows = self.rows(s)
        self.assertFalse(rows['viol']['met'])
        self.assertIn('đang có 4', rows['viol']['label'])
        s['journey'][ORG.SVC_KEY]['police'] = 3
        self.assertTrue(self.rows(s)['viol']['met'])
        s['journey'][pm.BAN_KEY] = dict(career='police', why='x', at=1)
        self.assertFalse(self.rows(s)['ban']['met'])

    def test_three_chapters_open_the_door_in_the_story(self):
        from game import journey as jr
        s = new_state()
        jr.enable_story(s, 7)
        s['journey']['done'] = ['c1', 'c2']
        self.assertFalse(jr.is_unlocked(s, 'customs'))
        self.assertFalse(self.rows(s)['chapters']['met'])
        self.assertIn('(2/3)', self.rows(s)['chapters']['label'])
        s['journey']['done'] = ['c1', 'c2', 'c3']
        self.assertTrue(gr.opens(s, 'customs'))
        self.assertTrue(self.rows(s)['chapters']['met'])

    def test_luck_never_skips_the_entry_rules(self):
        s = new_state()
        self.assertIsNotNone(emp.entry_block(s, 'customs'))
        for name in ('job_quick', 'job_backdoor'):
            with self.assertRaises(GameError):
                apply_action(copy.deepcopy(s), 'customs', name, dict(posting='hq-ktv'))


@unittest.skipIf(P is None, 'customs filtered out')
class Ladder(unittest.TestCase):
    def test_posts_and_grades_follow_the_spec(self):
        self.assertEqual([p['short'] for p in OC.HQ_POSTS],
                         ['Tập sự', 'Kiểm tra viên', 'Kiểm tra viên chính', 'Đội trưởng', 'Chi cục trưởng', 'Cục trưởng', 'Tổng cục trưởng'])
        self.assertEqual(OC.HQ_POSTS[0]['name'], 'Người tập sự công chức Hải quan')
        self.assertEqual(OC.ORGS['hq']['start'], ('hq_ts', 'tap_su'))
        self.assertEqual(OC.CAREER_ORG['customs'], ('hq', ('hq-ktv',)))

    def test_a_new_hire_starts_as_tap_su(self):
        j = Journey('customs')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        x = org(j)
        self.assertEqual((x['org'], x['p'], OC.HQ_GRADES[x['g']]['id']), ('hq', 'hq_ts', 'tap_su'))
        validate_state(j.state)

    def test_every_grade_has_its_board_on_the_page_and_the_street(self):
        js = (ROOT / 'public/js/v4/insignia.js').read_text(encoding='utf-8')
        m = re.search(r'GRADES\.hq=\{(.*?)\};', js, re.S)
        self.assertIsNotNone(m)
        ids = re.findall(r'([a-z_0-9]+):\{', m.group(1))
        self.assertEqual(ids, [g['id'] for g in OC.HQ_GRADES])
        from live import street_data
        self.assertEqual(tuple(street_data.ORG_GRADES['hq']), tuple(g['id'] for g in OC.HQ_GRADES))

    def test_the_customs_career_reads_its_rules(self):
        rules = P.content()['rules']
        self.assertEqual([r['id'] for r in rules], ['lane', 'collude', 'falsify', 'abuse', 'inspect', 'svc'])
        self.assertIn('giáng 1 bậc, kỷ luật 10 ngày', rules[1]['text'])
        self.assertIn('kỷ luật 15 ngày', rules[2]['text'])
        self.assertIn('khai trừ', rules[3]['text'])


@unittest.skipIf(P is None, 'customs filtered out')
class Work(unittest.TestCase):
    def test_each_kind_plays_through_clean(self):
        for kind in P.KINDS:
            with self.subTest(kind=kind):
                j = at(kind)
                r = play(j)
                t = cur(j)
                self.assertEqual((t['status'], t['outcome'], t['mistakes']), ('completed', 'clean', 0), r)
                validate_state(j.state)
                d = j.c['ext']['data']
                self.assertEqual((d['today']['jobs'], d['today']['clean']), (1, 1))

    def test_a_slip_on_evidence_is_answered_again_once_counted(self):
        j = at('tax')
        play(j, upto='duty')
        t = cur(j)
        r = step(j, wrong(t, 'duty'))
        self.assertFalse(r['correct'])
        step(j, wrong(t, 'duty') + 1)
        self.assertEqual(cur(j)['mistakes'], 1)
        play(j)
        self.assertEqual(cur(j)['outcome'], 'slip')
        self.assertEqual(j.c['ext']['data']['slips'][0]['k'], 'duty')

    def test_tax_numbers_follow_the_notebook(self):
        j = at('tax')
        t = cur(j)
        if t['_key']['policy'] == 'collect':
            v, rate = t['needs']['value'], int(t['_key']['rate'])
            self.assertEqual(t['_key']['duty'], v * rate // 100)
            self.assertEqual(t['_key']['vat'], (v + t['_key']['duty']) * CC.VAT // 100)
        play(j)
        self.assertEqual(j.c['ext']['data']['today']['duty'], t['needs']['due'])

    def test_a_red_lane_handled_as_green_is_a_warning(self):
        for d in range(1, 200):
            for s in range(1, 9):
                t = P.make_task(d, s, 1)
                if t['kind'] == 'lane' and t['_key']['route'] == 'red' and not t['needs']['pax']:
                    j = Journey('customs', slot=s, day=d)
                    j.act('hq_intro')
                    j.tid = j.task['id']
                    j.act('ask', task=j.tid)
                    r = step(j, 'green')
                    self.assertFalse(r['correct'])
                    self.assertIn('hq_skip', json.dumps(pm.record(j.state, 'customs'), ensure_ascii=False))
                    return
        self.fail('no red lane')

    def test_contraband_released_is_a_warning_and_a_complaint(self):
        for d in range(1, 200):
            for s in range(1, 9):
                t = P.make_task(d, s, 1)
                if t['kind'] == 'smuggle' and t['_key']['decide'] in ('hold', 'handover') and not t['needs'].get('tempt'):
                    j = Journey('customs', slot=s, day=d)
                    j.act('hq_intro')
                    j.tid = j.task['id']
                    play(j, upto='decide')
                    r = step(j, 'release')
                    self.assertFalse(r['correct'])
                    self.assertEqual(cur(j)['mistakes'], 2)
                    self.assertIn('hq_release', json.dumps(pm.record(j.state, 'customs'), ensure_ascii=False))
                    return
        self.fail('no contraband case')

    def test_the_answers_never_reach_the_page(self):
        j = at('lane')
        v = public_state(j.state)['careers']['customs']
        task = next(t for t in v['tasks'] if t['id'] == j.tid)
        self.assertNotIn('_key', task)
        self.assertIsNone(task['needs'])          # unknown until the file is read
        j.act('ask', task=j.tid)
        v = public_state(j.state)['careers']['customs']
        task = next(t for t in v['tasks'] if t['id'] == j.tid)
        self.assertNotIn('_key', json.dumps(task))
        self.assertNotIn('due', task['needs'])

    def test_a_forged_step_or_value_is_refused(self):
        j = at('tax')
        tid = j.tid
        j.act('ask', task=tid)
        for p in (dict(step='policy', value='collect'), dict(step='rate', value='99'), dict(step='rate', value=None)):
            with self.assertRaises(GameError):
                j.act('hq_step', task=tid, **p)
        play(j, upto='duty')
        for v in ('100', 1.5, -1, True):
            with self.assertRaises(GameError):
                j.act('hq_step', task=tid, step='duty', value=v)

    def test_a_tampered_save_is_refused(self):
        j = at('smuggle')
        play(j, upto='decide')
        for mutate in (lambda t: t['_key'].update(decide='release'), lambda t: t['work'].update(scan='x'),
                       lambda t: t.update(at=0), lambda t: t.update(outcome='tempt'), lambda t: t['needs'].update(bonus=99)):
            s = copy.deepcopy(j.state)
            t = next(x for x in s['careers']['customs']['tasks'] if x['id'] == j.tid)
            mutate(t)
            with self.assertRaises(GameError):
                validate_state(s)
        for mutate in (lambda d: d['today'].update(clean=9), lambda d: d.update(cmp_seq=-1),
                       lambda d: d['audit'].append(dict(code='hq_x', key='k', found=True, amount=0, d=1)),
                       lambda d: d['slips'].append(dict(npc=99, k='duty'))):
            s = copy.deepcopy(j.state)
            mutate(s['careers']['customs']['ext']['data'])
            with self.assertRaises(GameError):
                validate_state(s)


@unittest.skipIf(P is None, 'customs filtered out')
class Temptation(unittest.TestCase):
    """2. Vi phạm trong ngành: refusing is right; going along is found by the thanh tra (rolled at once, applied at the
    close): thông đồng giáng 1 bậc + kỷ luật 10 ngày, sai lệch hồ sơ kỷ luật 15 ngày, phong bì / giữ hàng khai trừ."""

    def setUp(self):
        self.found = True
        p = mock.patch.object(gr, '_hq_roll', lambda key, prob: self.found)
        p.start()
        self.addCleanup(p.stop)

    def on_ladder(self, kind, post='hq_ktvc', grade='ktvc_2'):
        """An officer whose current task carries the temptation `kind`."""
        j = officer(post, grade)
        for d in range(2, 300):
            for s in range(1, 9):
                t = P.make_task(d, s, 1)
                tp = t['needs'].get('tempt')
                if tp and tp['kind'] == kind:
                    c = j.c
                    c['day'] = d
                    c['tasks'] = [t]
                    c['active_task'] = j.tid = t['id']
                    validate_state(j.state)
                    return j
        raise AssertionError(kind)

    def test_refusing_is_right(self):
        j = self.on_ladder('bribe')
        play(j)
        self.assertEqual(cur(j)['outcome'], 'clean')
        self.assertEqual(cur(j)['work']['offer'], 'refuse')
        self.assertEqual(j.c['ext']['data']['audit'], [])

    def take(self, j):
        play(j, upto='offer')
        return step(j, 'take')

    def test_collusion_found_giang_1_bac_ky_luat_10_ngay(self):
        j = self.on_ladder('collude')
        g = org(j)['g']
        self.take(j)
        self.assertEqual(cur(j)['outcome'], 'tempt')
        self.assertEqual(j.c['ext']['data']['audit'][0]['code'], 'hq_collude')
        validate_state(j.state)
        r = j.act('end_day', carry_event=True)
        x = org(j)
        self.assertEqual(x['g'], g - 1)
        self.assertIn('Thanh tra phát hiện', json.dumps(r, ensure_ascii=False))
        self.assertEqual(j.c['ext']['data']['audit'], [])
        self.assertEqual(ORG.svc_count(j.state, 'customs'), 1)

    def test_falsifying_found_ky_luat_15_ngay(self):
        j = self.on_ladder('falsify')
        g = org(j)['g']
        self.take(j)
        r = j.act('end_day', carry_event=True)
        self.assertEqual(org(j)['g'], g)                                 # no grade lost
        self.assertGreaterEqual(pm.record(j.state, 'customs')['cx']['hold'], 14)   # the grade held 15 worked days
        self.assertEqual(ORG.svc_count(j.state, 'customs'), 1)
        self.assertIn('Kỷ luật 15 ngày', json.dumps(r, ensure_ascii=False))

    def test_an_envelope_found_expels_and_confiscates(self):
        j = self.on_ladder('bribe')
        w0 = j.state['journey']['wallet']
        self.take(j)
        amount = j.c['ext']['data']['audit'][0]['amount']
        self.assertEqual(j.state['journey']['wallet'], w0 + amount)
        j.act('end_day', carry_event=True)
        self.assertEqual(j.state['journey']['wallet'], w0)
        self.assertTrue(pm.banned(j.state, 'customs'))
        self.assertTrue(pm.banned(j.state, 'police'))       # gov_ban: every state career
        validate_state(j.state)

    def test_not_found_nothing_happens(self):
        self.found = False
        j = self.on_ladder('collude')
        g = org(j)['g']
        self.take(j)
        j.act('end_day', carry_event=True)
        self.assertEqual(org(j)['g'], g)
        self.assertEqual(len(j.c['ext']['data']['audit']), 1)


@unittest.skipIf(P is None, 'customs filtered out')
class Complaints(unittest.TestCase):
    """1.1.3 After the shift: a real complaint is accepted; an unreasonable one dismissed or sent to CATP."""

    def with_rows(self, kinds):
        j = officer()
        d = j.c['ext']['data']
        d['cmp'] = [dict(id=i + 1, k=k, npc=0, text='Phản ánh', d=j.c['day'], st='open', out='') for i, k in enumerate(kinds)]
        d['cmp_seq'] = len(kinds)
        validate_state(j.state)
        return j

    def test_each_answer(self):
        j = self.with_rows(['real', 'bocphot', 'offtopic', 'real'])
        adj = org(j)['adj']
        self.assertTrue(j.act('hq_cmp', id=1, op='accept')['correct'])
        self.assertTrue(j.act('hq_cmp', id=2, op='sue')['correct'])
        self.assertTrue(j.act('hq_cmp', id=3, op='dismiss')['correct'])
        self.assertEqual(org(j)['adj'], adj + 2)
        r = j.act('hq_cmp', id=4, op='dismiss')
        self.assertFalse(r['correct'])
        self.assertIn('hq_dismiss', json.dumps(pm.record(j.state, 'customs'), ensure_ascii=False))
        with self.assertRaises(GameError):
            j.act('hq_cmp', id=4, op='accept')
        validate_state(j.state)
        v = public_state(j.state)['careers']['customs']['data']['cmp']
        self.assertEqual({r['id']: r.get('kind') for r in v}[2], NC.KINDS['bocphot'])

    def test_kind_hidden_until_decided(self):
        j = self.with_rows(['demand'])
        v = public_state(j.state)['careers']['customs']['data']['cmp'][0]
        self.assertNotIn('kind', v)
        self.assertNotIn('k', v)

    def test_a_shift_with_slips_brings_real_complaints(self):
        j = at('tax')
        play(j, upto='duty')
        step(j, wrong(cur(j), 'duty'))
        play(j)
        j.act('end_day', carry_event=True)
        rows = j.c['ext']['data']['cmp']
        self.assertTrue(any(r['k'] == 'real' and r['text'] == CC.REAL_LINES['duty'] for r in rows))


@unittest.skipIf(P is None, 'customs filtered out')
class Dormant(unittest.TestCase):
    """💤 A customs record nobody touched is left out of the stored text; a used one is kept."""

    def test_untouched_is_left_out_and_woken(self):
        from game.storage import serialize
        self.assertIn('customs', DORMANT)
        s = new_state()
        text = serialize(copy.deepcopy(s), None, True)
        raw = json.loads(text)
        self.assertNotIn('customs', raw['careers'])
        self.assertIn('customs', raw['check']['careers'])
        self.assertTrue(wake(raw))
        self.assertEqual(raw['careers']['customs'], initial_career('customs'))
        validate_state(migrate_state(json.loads(text)))
        self.assertNotIn('customs', dormant_out(s)['careers'])
        self.assertIn('customs', s['careers'])      # a copy: the state itself keeps it

    def test_used_is_kept(self):
        from game.storage import serialize
        j = at('lane')
        raw = json.loads(serialize(copy.deepcopy(j.state), None, True))
        self.assertIn('customs', raw['careers'])
        self.assertIn('customs', dormant_out(j.state)['careers'])


OLD_PROG = ('import json,sys\nfrom game.engine import validate_state,apply_action,public_state,migrate_state\n'
            's=migrate_state(json.load(sys.stdin))\nvalidate_state(s)\ncur=s["current"]\npublic_state(s)\n'
            'c=s["careers"][cur]\n'
            'if c["open"]:\n s,_=apply_action(s,cur,"end_day",{"carry_event":True})\n'
            's,_=apply_action(s,cur,"start_day",{})\npublic_state(s)\nprint(json.dumps(s))')


def old_tree():
    old = os.environ.get('MNL_LIVE_TREE')
    return old if old and (Path(old) / 'game' / 'engine.py').is_file() else None


@unittest.skipIf(P is None, 'customs filtered out')
class Rollback(unittest.TestCase):
    """A rollback (MNL_LIVE_TREE: the build before, 2.4.24): a save that never used customs, stored by this build, loads
    there, plays a day and comes back here with customs woken; one that used it is refused there (never roll back below
    this build once customs is used)."""

    def run_old(self, text):
        old = old_tree()
        return subprocess.run([sys.executable, '-c', OLD_PROG], input=text, capture_output=True, text=True, cwd=old,
                              env=dict(os.environ, PYTHONPATH=old, PYTHONUTF8='1'), encoding='utf-8')

    def test_an_untouched_save_crosses_the_build_before(self):
        if not old_tree():
            self.skipTest('no live tree (MNL_LIVE_TREE)')
        from game.storage import serialize
        j = Journey('mother_baby')
        j.solve()
        text = serialize(copy.deepcopy(j.state), None, True)
        out = self.run_old(text)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = migrate_state(json.loads(out.stdout))
        validate_state(back)
        self.assertEqual(back['careers']['customs'], initial_career('customs'))

    def test_a_used_customs_record_is_refused_by_the_build_before(self):
        if not old_tree():
            self.skipTest('no live tree (MNL_LIVE_TREE)')
        from game.storage import serialize
        j = at('lane')
        out = self.run_old(serialize(copy.deepcopy(j.state), None, True))
        self.assertNotEqual(out.returncode, 0)


if __name__ == '__main__':
    unittest.main()
