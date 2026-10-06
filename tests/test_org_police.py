"""Chức vụ & cấp bậc (game/org.py, org_content.py), police first: grades and posts as two tracks, courses and
appointments, ⚠️ warnings (4th demotes one grade, decay, cleared by an excellent period), an accepted bribe (an
immediate demotion and a permanent mark; owning up the same shift), stepping down a post, suspension at the entry
grade, lazy migration of existing officers, the commander's office (NPCs only) and the Trợ lý's inspection, the
beat overlay's envelopes, and saves (validation, a rollback to a build without org)."""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from game import org as ORG
from game import org_content as OC
from game import promotion as pm
from game import promotion_office as OF
from game.engine import GameError, apply_action, public_state, validate_state
from tests.helpers import Journey
from tests.test_promotion import day

O = OC.ORGS['cand']


def gi(gid):
    return next(i for i, g in enumerate(O['grades']) if g['id'] == gid)


def officer(post='to_vien', grade='binh_nhi', learned=True):
    j = Journey('police')
    rec = pm.record(j.state, 'police', True)
    pm._sync(rec, j.c)
    rec['worked'] = 0
    j.act('end_day', carry_event=True)
    j.act('start_day')
    x = org(j)
    x['p'], x['g'] = post, gi(grade)
    if learned:
        j.c['ext']['data']['learn']['n'] = 99
    return j


def org(j):
    return pm.record(j.state, 'police')['org']


def view(j):
    return public_state(j.state)['careers']['police']['promo']


def best(qid):
    return max(OC.QUESTION_INDEX[qid]['options'], key=lambda o: o['score'])['id']


def worst(qid):
    return min(OC.QUESTION_INDEX[qid]['options'], key=lambda o: o['score'])['id']


def answer_due(j, good=True):
    r = None
    for q in list(org(j)['due']['qs']):
        r = j.act('pm_answer', question=q, option=best(q) if good else worst(q))
    return r


class Ladder(unittest.TestCase):
    def test_new_hire_starts_at_the_entry(self):
        j = Journey('police')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        x = org(j)
        self.assertEqual((x['p'], O['grades'][x['g']]['id']), ('to_vien', 'binh_nhi'))
        v = view(j)
        self.assertEqual(v['title'], 'Binh nhì · Tổ viên')
        self.assertEqual(v['org']['grade']['ins'], dict(base='red', v=1))
        self.assertEqual(v['org']['warns'], [])
        validate_state(j.state)

    def test_part_time_keeps_the_plain_ladder(self):
        from game.employment import hired_record
        j = Journey('police')
        j.c['job'] = hired_record('police', 'cap-td')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertNotIn('org', pm.record(j.state, 'police') or {})
        self.assertNotIn('org', view(j))

    def test_grades_rise_with_days_then_a_course_then_the_ceiling(self):
        j = officer()
        for _ in range(60):
            day(j)
            x = org(j)
            if x['due']:
                self.assertEqual(x['due']['k'], 'course')
                self.assertEqual(O['grades'][x['g']]['id'], 'thuong_si')
                break
        else:
            self.fail('no course')
        r = answer_due(j)
        self.assertIn('Đạt', r['message'])
        day(j)
        self.assertEqual(O['grades'][org(j)['g']]['id'], 'thieu_uy')   # Tổ viên's ceiling
        for _ in range(12):
            if org(j)['due']:
                break
            day(j)
        x = org(j)
        self.assertEqual((x['due']['k'], x['due']['to']), ('post', 'to_pho'))
        self.assertEqual(O['grades'][x['g']]['id'], 'thieu_uy')   # never past the post's ceiling meanwhile
        r = answer_due(j)
        self.assertIn('bổ nhiệm', r['message'])
        x = org(j)
        self.assertEqual((x['p'], O['grades'][x['g']]['id']), ('to_pho', 'trung_uy'))   # promoted on appointment
        self.assertEqual(pm.record(j.state, 'police')['rank'], 2)   # the plain step follows the post
        validate_state(j.state)

    def test_a_failed_interview_waits(self):
        j = officer('to_vien', 'thieu_uy')
        x = org(j)
        x['st'] = [45] * 10
        x['vac'] = 0
        for _ in range(3):
            day(j)
            if org(j)['due']:
                break
        r = answer_due(j, good=False)
        self.assertTrue(r['later'])
        self.assertEqual(org(j)['wait'], ORG.RETRY)
        self.assertEqual(org(j)['p'], 'to_vien')

    def test_pay_follows_grade_and_post(self):
        j = officer('to_truong', 'thuong_uy')
        pct = pm.raise_pct(j.state, j.c, 'police')
        self.assertEqual(pct, round(100 * 5.0 / 3.2 * 1.05) - 100)
        org(j)['p'], org(j)['g'] = 'pgd', gi('dai_ta')
        self.assertEqual(pm.raise_pct(j.state, j.c, 'police'), 200)


class Migration(unittest.TestCase):
    def test_existing_officers_are_placed_from_their_step_never_lower(self):
        for step, (post, grade) in enumerate(O['migrate']):
            j = Journey('police')
            rec = pm.record(j.state, 'police', True)
            pm._sync(rec, j.c)
            rec['rank'], rec['worked'], rec['extra'] = step, 30, 4 if step else 0
            rec.pop('org', None)   # an officer from before the ladder
            old = pm.EMP_STEPS[step]['pct'] + 4 if step else 0
            money = j.c['money']
            j.act('end_day', carry_event=True)
            self.assertEqual(j.c['money'], money)   # no money moved by the migration itself
            x = org(j)
            self.assertEqual((x['p'], O['grades'][x['g']]['id']), (post, grade))
            self.assertGreaterEqual(pm.raise_pct(j.state, j.c, 'police'), old)
            self.assertEqual(pm.record(j.state, 'police')['rank'], step)   # untouched until the post changes
            validate_state(j.state)


class Warnings(unittest.TestCase):
    def test_fourth_warning_demotes_one_grade_and_resets(self):
        j = officer('to_vien', 'trung_si')
        for i in range(3):
            line = pm.violation(j.state, j.c, 'police', 'skip_step', f't{i}')
            self.assertIn(f'{i + 1}/3', line)
        self.assertEqual(len(view(j)['org']['warns']), 3)
        line = pm.violation(j.state, j.c, 'police', 'skip_step', 't3')
        self.assertIn('Hạ 1 bậc hàm', line)
        x = org(j)
        self.assertEqual(O['grades'][x['g']]['id'], 'ha_si')
        self.assertEqual(x['warns'], [])
        validate_state(j.state)

    def test_one_warning_per_key_a_day_and_grace(self):
        j = officer()
        pm.violation(j.state, j.c, 'police', 'skip_step', 'same')
        self.assertEqual(pm.violation(j.state, j.c, 'police', 'skip_step', 'same'), '')
        line = pm.violation(j.state, j.c, 'police', 'threat', 'other', grace=True)
        self.assertIn('chưa tính', line)
        self.assertEqual(len(org(j)['warns']), 1)

    def test_demotion_below_the_post_steps_down(self):
        j = officer('truong_ca', 'trung_ta')
        org(j)['warns'] = [dict(d=1, c='skip_step')] * 3
        line = pm.violation(j.state, j.c, 'police', 'skip_step', 'x')
        x = org(j)
        self.assertEqual((x['p'], O['grades'][x['g']]['id']), ('pho_truong_ca', 'thieu_ta'))
        self.assertIn('nhận ghế', line)
        self.assertEqual(pm.record(j.state, 'police')['rank'], 4)
        j2 = officer('to_pho', 'trung_uy')
        org(j2)['warns'] = [dict(d=1, c='skip_step')] * 3
        pm.violation(j2.state, j2.c, 'police', 'skip_step', 'x')
        self.assertEqual(org(j2)['p'], 'to_vien')
        self.assertEqual(pm.record(j2.state, 'police')['rank'], 0)

    def test_warnings_decay_after_clean_days_and_an_excellent_period_clears_one(self):
        j = officer('to_vien', 'binh_nhi')
        pm.violation(j.state, j.c, 'police', 'skip_step', 'a')
        pm.violation(j.state, j.c, 'police', 'skip_step', 'b')
        day(j)   # the violation day itself is not clean
        for _ in range(O['decay_days']):
            day(j)
        self.assertEqual(len(org(j)['warns']), 1)
        x = org(j)
        x['st'] = [48] * 10
        x['evn'] = O['eval_window'] - 1
        x['clean'] = 0
        r = day(j)
        self.assertEqual(org(j)['warns'], [])
        self.assertIn('xuất sắc', ' '.join(r['summary']['promo']['org']).lower())

    def test_fourth_warning_at_the_entry_grade_suspends_without_salary(self):
        j = officer('to_vien', 'binh_nhi')
        org(j)['warns'] = [dict(d=1, c='skip_step')] * 3
        line = pm.violation(j.state, j.c, 'police', 'skip_step', 'x')
        self.assertIn('đình chỉ', line)
        self.assertEqual(org(j)['susp'], O['susp_days'])
        money = j.c['money']
        r = day(j)
        self.assertEqual(r['summary']['job']['salary'], 0)
        self.assertEqual(j.c['money'], money)
        for _ in range(O['susp_days']):
            day(j)
        self.assertEqual(org(j)['susp'], 0)
        r = day(j)
        self.assertGreater(r['summary']['job']['salary'], 0)


class Bribe(unittest.TestCase):
    def test_bribe_demotes_at_once_marks_for_good_and_owning_up_turns_it_into_a_warning(self):
        j = officer('truong_ca', 'trung_ta')
        org(j)['warns'] = [dict(d=1, c='threat')]
        line = pm.bribe(j.state, j.c, 'police', 'k')
        x = org(j)
        self.assertIn('liêm chính', line)
        self.assertEqual((x['p'], O['grades'][x['g']]['id']), ('pho_truong_ca', 'thieu_ta'))
        self.assertEqual(len(x['warns']), 1)   # kept, not reset
        self.assertIsNotNone(x['mark']['b'])
        self.assertTrue(view(j)['org']['own'])
        r = j.act('pm_org_own')
        x = org(j)
        self.assertEqual((x['p'], O['grades'][x['g']]['id']), ('truong_ca', 'trung_ta'))
        self.assertEqual(len(x['warns']), 2)
        self.assertTrue(x['mark']['s'])
        self.assertIn('tự giác', r['message'])
        with self.assertRaises(GameError):
            j.act('pm_org_own')
        validate_state(j.state)

    def test_owning_up_only_the_same_shift(self):
        j = officer('to_truong', 'thuong_uy')
        pm.bribe(j.state, j.c, 'police', 'k')
        day(j)
        j.act('start_day')
        with self.assertRaises(GameError):
            j.act('pm_org_own')

    def test_the_mark_bars_the_aide_the_deputy_director_and_colonel(self):
        j = officer('truong_phong', 'thuong_ta')
        x = org(j)
        self.assertEqual(ORG._aims(x), ['pgd', 'tro_ly'])
        x['mark'] = dict(b=3, s=True)
        self.assertEqual(ORG._aims(x), [])
        x['p'] = 'pgd'
        x['tig'], x['st'] = 99, [50] * 10
        ng = ORG.next_grade(x)
        self.assertFalse(next(r for r in ng['rows'] if r['id'] == 'mark')['met'])


class PoliceTasks(unittest.TestCase):
    def test_a_patrol_skipping_danger_is_a_warning(self):
        from tests.test_career_police import at, P, PC
        j = at(None, 'patrol')
        pm.record(j.state, 'police', True)
        j.act('end_day', carry_event=True)
        j = at(None, 'patrol')
        jj = j
        t = jj.task
        jj.act('ask', task=t['id'])
        sid = None
        for i, k in enumerate(t['_v']['scenes']):
            sc = PC.SCENES[k]
            bad = next((o for o in sc['options'] if o[2] == 'unsafe'), None)
            if bad:
                sid = (i, bad[0])
                break
        if sid is None:
            self.skipTest('no unsafe option in this patrol')
        r = jj.act('cap_act', task=t['id'], i=sid[0], choice=sid[1])
        self.assertIn('Cảnh cáo 1/3', r['message'])
        self.assertEqual(org(jj)['warns'][0]['c'], 'skip_step')

    def test_the_duty_books_false_line_is_a_warning(self):
        from tests.test_career_police import at, solve
        j = at(None, 'desk')
        solve(j, j.task)
        rows = j.c['ext']['data']['today']['facts']
        lie = next((r for r in rows if not r['true']), None)
        if lie is None:
            self.skipTest('no tempting line today')
        r = j.act('cap_log', lines=[lie['id']])
        self.assertIn('ghi khống', r['message'].lower())
        self.assertEqual(org(j)['warns'][-1]['c'], 'false_log')

    def test_envelopes_roll_from_the_task_and_report_or_take(self):
        from game.careers import police_beat as BT
        from tests.test_career_police import where, quiet
        from game.content import make_task
        found = None
        for d in range(2, 200):
            for sl in range(1, 9):
                t = make_task('police', d, sl, 1)
                if t['kind'] in BT.OFFERS and BT.roll(t):
                    found = (d, sl)
                    break
            if found:
                break
        self.assertIsNotNone(found)
        for choice in ('report', 'take'):
            j = Journey('police', slot=found[1], day=found[0])
            j.act('cap_intro')
            quiet(j)
            j.c['ext']['data']['learn']['n'] = 99
            t = j.task
            j.act('ask', task=t['id'])
            k = t['kind']
            first = {'lost': ('cap_count', {}), 'dispute': ('cap_hear', dict(side='a')), 'patrol': ('cap_look', dict(i=0))}[k]
            r = j.act(first[0], task=t['id'], **first[1])
            self.assertEqual(r.get('beat'), BT.roll(t))
            offers = public_state(j.state)['careers']['police']['data']['beat']['offers']
            self.assertEqual(offers[0]['t'], t['id'])
            g0 = org(j)['g']
            r = j.act('cap_beat', task=t['id'], choice=choice)
            if choice == 'report':
                self.assertEqual(org(j)['liem'], 1)
                self.assertEqual(org(j)['g'], g0)
            else:
                self.assertIsNotNone(org(j)['mark']['b'])
                self.assertTrue(org(j)['susp'] or org(j)['g'] < g0)
            with self.assertRaises(GameError):
                j.act('cap_beat', task=t['id'], choice='refuse')
            validate_state(j.state)


class Office(unittest.TestCase):
    def test_no_office_below_the_team_leader(self):
        j = officer('to_pho', 'trung_uy')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertNotIn('office', view(j))
        with self.assertRaises(GameError):
            j.act('pm_of_hr', mate=0, act='talk')

    def test_team_leader_office_grows_with_the_post_and_powers_by_level(self):
        j = officer('to_truong', 'thuong_uy')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        of = view(j)['office']
        self.assertEqual(len(of['staff']), 4)
        self.assertEqual([a['id'] for a in of['acts']], ['talk', 'praise', 'remind'])
        with self.assertRaises(GameError):
            j.act('pm_of_hr', mate=0, act='demote')
        org(j)['p'], org(j)['g'] = 'pgd', gi('thuong_ta')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        of = view(j)['office']
        self.assertEqual(len(of['staff']), 12)
        self.assertIn('reprimand', [a['id'] for a in of['acts']])
        validate_state(j.state)

    def test_unjust_discipline_is_noted_against_the_player(self):
        j = officer('truong_ca', 'trung_ta')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        off = org(j)['office']
        i = next(k for k, st in enumerate(off['staff']) if st['iss'] is None and st['mk'] == 0)
        r = j.act('pm_of_hr', mate=i, act='review')
        self.assertFalse(r['just'])
        self.assertEqual(org(j)['warns'][-1]['c'], 'wrong_discipline')

    def test_inspection_workflow_of_the_aide(self):
        j = officer('tro_ly', 'trung_ta')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        ins = view(j)['org']['insp']
        self.assertEqual(len(ins['units']), 4)
        for u in ins['units'][:2]:
            j.act('pm_of_insp', op='pick', unit=u['i'])
        with self.assertRaises(GameError):
            j.act('pm_of_insp', op='send')
        x = org(j)
        for i, rw in enumerate(x['insp']['rows']):
            for a in range(3):
                j.act('pm_of_insp', op='mark', row=i, a=a, v=rw['bad'][a])
            j.act('pm_of_insp', op='grade', row=i, g=ORG._truth_grade(rw)[0])
        r = j.act('pm_of_insp', op='send')
        self.assertIn('100%', r['message'])
        self.assertTrue(org(j)['office']['me'])
        validate_state(j.state)

    def test_pilot_office_is_unchanged(self):
        self.assertNotIn('ig', OF.new_office('pilot', 7, 3)['staff'][0])
        self.assertEqual(OF.OFFICE['pilot']['powers'][6], OF.FULL)


class Insignia(unittest.TestCase):
    def test_client_and_live_copies_match_the_content(self):
        import re
        root = Path(__file__).resolve().parents[1]
        js = (root / 'public/js/v4/insignia.js').read_text(encoding='utf-8')
        body = re.search(r'GRADES=\{cand:\{(.*?)\}\};', js, re.S).group(1)
        rows = dict(re.findall(r'(\w+):(\{[^}]*\})', body))
        for g in O['grades']:
            self.assertIn(g['id'], rows)
            got = json.loads(re.sub(r'(\w+):', r'"\1":', rows[g['id']]).replace("'", '"'))
            self.assertEqual(got, g['ins'], g['id'])
        from live.street_data import ORG_GRADES
        self.assertEqual(ORG_GRADES['cand'], tuple(g['id'] for g in O['grades'][:-1]))   # never the NPC-only general

    def test_live_keeps_a_known_rank_and_drops_anything_else(self):
        from live.street import clean_rank
        self.assertEqual(clean_rank({'o': 'cand', 'g': 'dai_uy'}), {'o': 'cand', 'g': 'dai_uy'})
        for bad in (None, 'x', {'o': 'cand', 'g': 'thieu_tuong'}, {'o': 'x', 'g': 'dai_uy'}, {'o': 'cand', 'g': 'dai_uy', 'z': 1}):
            self.assertIsNone(clean_rank(bad))


class Saves(unittest.TestCase):
    def test_tampered_org_is_refused(self):
        j = officer('to_truong', 'thuong_uy')
        for bad in (dict(g=13), dict(p='giam_doc'), dict(warns=[dict(d=1, c='x')]), dict(liem=-1), dict(susp=9), dict(extra=1)):
            s = copy.deepcopy(j.state)
            s['journey']['promo']['police']['org'].update(bad)
            with self.assertRaises(GameError, msg=str(bad)):
                validate_state(s)

    def old_tree(self):
        old = os.environ.get('MNL_LIVE_TREE')
        if not old or not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no live tree (MNL_LIVE_TREE)')
        return old

    def test_saves_cross_a_build_without_org(self):
        """A rollback: the build without org reads saves made here (rank, office, warnings, envelopes, a course due),
        plays a day, and this build reads what it wrote."""
        old = self.old_tree()
        prog = ('import json,sys\nfrom game.engine import validate_state,apply_action,public_state\n'
                's=json.load(sys.stdin)\nvalidate_state(s)\ncur=s["current"]\npublic_state(s)\n'
                'c=s["careers"][cur]\n'
                'if c["open"]:\n s,_=apply_action(s,cur,"end_day",{"carry_event":True})\n'
                's,_=apply_action(s,cur,"start_day",{})\npublic_state(s)\n'
                'print(json.dumps(s))')
        saves = []
        j = officer('truong_ca', 'trung_ta')
        j.act('end_day', carry_event=True)
        j.act('start_day')
        pm.violation(j.state, j.c, 'police', 'skip_step', 'a')
        pm.bribe(j.state, j.c, 'police', 'b')
        saves.append(copy.deepcopy(j.state))
        a = officer('tro_ly', 'trung_ta')
        a.act('end_day', carry_event=True)
        a.act('start_day')
        u = view(a)['org']['insp']['units'][0]['i']
        a.act('pm_of_insp', op='pick', unit=u)
        saves.append(copy.deepcopy(a.state))
        b = officer('to_vien', 'thuong_si')
        org(b)['st'], org(b)['tig'] = [45] * 10, 9
        day(b)
        self.assertEqual(org(b)['due']['k'], 'course')
        saves.append(copy.deepcopy(b.state))
        for s in saves:
            validate_state(s)
            env = dict(os.environ, PYTHONPATH=old)
            out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                                 encoding='utf-8')
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            back = json.loads(out.stdout)
            validate_state(back)
            self.assertEqual(back['journey']['promo']['police']['org']['g'], s['journey']['promo']['police']['org']['g'])
            back, _ = apply_action(back, 'police', 'end_day', {'carry_event': True})
            back, _ = apply_action(back, 'police', 'start_day', {})
            validate_state(back)


if __name__ == '__main__':
    unittest.main()
