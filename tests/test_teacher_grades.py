"""Teacher lớp 2–5 (feedback #304): content, answer keys, unlocks, a full grade period, save safety.

Set MNL_OLD_TREE to an extracted older release (git archive rel-1.9.37 | tar -x -C DIR) to also check that
the older build's validate_state accepts a save carrying the new keys (homeroom, grade_room)."""
import copy
import itertools
import json
import os
import re
import subprocess
import sys
import unittest
from fractions import Fraction

from game import classroom as C
from game import teach_grades as TG
from game import teach_lesson as TL
from game.engine import GameError, normalize, public_state, validate_state
from game.extra_content import LESSONS as V1_LESSONS, make_task
from tests.helpers import Journey

GOOD_ROLL = {'here': 'present', 'sick': 'excused', 'late': 'let_in', 'missing': 'report'}
BEST_CALL = {x['id']: max(x['options'], key=lambda o: (not o['mistake'], sum(o['trust'].values()), o['focus']))['id'] for x in TL.INCIDENTS}

# Each lesson's key worked out again here, by plain arithmetic, from the numbers in its prompt.
F = Fraction
MATHS = {
    'Cộng có nhớ: hạc giấy': 38 + 25,
    'Trừ có nhớ: tủ truyện': 52 - 17,
    'Bảng nhân 2: đôi đũa': 2 * 6,
    'Bảng chia 5: chia kẹo': 20 // 5,
    'Xem đồng hồ': '3 giờ 30 phút',   # minute hand on 6: 6 × 5 = 30 minutes; hour hand past 3
    'Bảng nhân 6: hộp bánh': 6 * 7,
    'Chia có dư: xếp bàn': f'{25 // 4} bàn, dư {25 % 4} bạn',
    'Chu vi vườn rau': (8 + 5) * 2,
    'Diện tích tờ giấy': 6 * 6,
    'Một phần tư chiếc bánh': 'Một phần tư',
    'Trung bình cộng chiều cao': (130 + 134 + 135) // 3,
    'Tổng và hiệu: góp vở': (90 + 10) // 2,
    'Rút gọn phân số': '{0.numerator}/{0.denominator}'.format(F(6, 8)),
    'Cộng phân số cùng mẫu': '{0.numerator}/{0.denominator}'.format(F(1, 5) + F(2, 5)),
    'Cộng số thập phân': '{:.2f}'.format(F('32.5') + F('18.75')).replace('.', ','),
    'Phần trăm đi xe đạp': f'{int(F(10, 40) * 100)}%',
    'Lá cờ tam giác': f'{6 * 4 // 2} dm²',
    'Vận tốc xe đạp': f'{24 // 2} km/giờ',
    'Bể cá nhà Khoa': 5 * 3 * 4,
}
EXACT = {'Trung bình cộng chiều cao': (130 + 134 + 135) % 3 == 0, 'Tổng và hiệu: góp vở': (90 + 10) % 2 == 0,
         'Bảng chia 5: chia kẹo': 20 % 5 == 0, 'Vận tốc xe đạp': 24 % 2 == 0, 'Lá cờ tam giác': 6 * 4 % 2 == 0}


def room(j, tid):
    return TL.room_of(j.get(tid))


def best_plan(r):
    ok = [p for p in itertools.permutations(r['hand'], 3) if TL.plan_error(p) is None]
    return list(max(ok, key=lambda p: TL._stars(p, r['cond'], TL.need_styles(r))[0]))


def play_to_ready(j, tid):
    j.act('lesson_roll', task=tid, kid='all')
    for k in room(j, tid)['kids']:
        if k['id'] not in room(j, tid)['roll']:
            j.act('lesson_roll', task=tid, kid=k['id'], choice=GOOD_ROLL[k['status']])
    j.act('lesson_plan', task=tid, steps=best_plan(room(j, tid)))
    for ph in range(3):
        r = room(j, tid)
        for ev in r['events']:
            if ev['phase'] == ph:
                j.act('lesson_call', task=tid, event=ev['id'], option=BEST_CALL[ev['id']])
        r = room(j, tid)
        for kid in r['lost']:
            if kid not in r['helped'] and r['flags'].get(kid) != 'miss':
                j.act('lesson_help', task=tid, kid=kid, method=TL.KID[kid]['style'])
        j.act('lesson_next', task=tid)
    for kid, tk in room(j, tid)['tickets'].items():
        j.act('lesson_mark', task=tid, kid=kid, mark=TL.MARK_FOR[tk['kind']])


def pub_task(j, tid):
    return next(t for t in public_state(j.state)['careers']['teacher']['tasks'] if t['id'] == tid)


def teacher(xp=0, grade=None):
    j = Journey('teacher')
    j.c['xp'] = xp
    if grade:
        j.act('cl_homeroom', grade=grade)
    return j


def find_slot(grade, want_demand=True, day=1):
    for slot in range(12):
        if (TG.demand_roll(grade, day, slot) is not None) == want_demand:
            return slot
    raise AssertionError('no slot')


class GradeContentTests(unittest.TestCase):
    def test_every_grade_has_full_lessons(self):
        v1 = {x['title'] for x in V1_LESSONS}
        titles = []
        for g in (2, 3, 4, 5):
            rows = TG.LESSONS[g]
            self.assertGreaterEqual(len(rows), 8, g)
            self.assertEqual({x['subject'] for x in rows}, {'math', 'read', 'think'}, g)
            for x in rows:
                titles.append(x['title'])
                self.assertIn(x['answer'], x['choices'], x['title'])
                self.assertEqual(len(x['choices']), 3, x['title'])
                self.assertEqual(len({str(v) for v in x['choices']}), 3, x['title'])
                self.assertIn(x['subject'], C.SUBJECT_IDS)
                self.assertLessEqual(len(x['prompt'].split()), 24, x['title'])
                self.assertLessEqual(len(x['fact'].split()), 30, x['title'])
                self.assertTrue(x['topic'] and x['fact'])
                q = x['q']
                self.assertTrue(q['text'].endswith('?') or q['text'].endswith('ạ?'), x['title'])
                self.assertEqual([a[0] for a in q['answers']], ['good', 'ok', 'poor'])
                for k in q['keys']:
                    self.assertEqual(re.sub(r'[^a-z0-9]+', ' ', normalize(k)).strip(), k, (x['title'], k))
                # The scripted good answer is judged good by the rules too (it names the reason).
                self.assertEqual(TL.judge_answer(TL.say({}, q['answers'][0][1]), q, 'vy')[0], 'good', x['title'])
        self.assertEqual(len(titles), len(set(titles)))
        self.assertFalse(v1 & set(titles))
        for t in titles:
            self.assertIn(t, TL.QUESTIONS)

    def test_maths_answer_keys(self):
        math = [x for g in (2, 3, 4, 5) for x in TG.LESSONS[g] if x['subject'] == 'math']
        self.assertEqual({x['title'] for x in math}, set(MATHS))
        for x in math:
            self.assertEqual(x['answer'], MATHS[x['title']], x['title'])
            self.assertEqual([v for v in x['choices'] if v == x['answer']], [x['answer']], x['title'])
        self.assertTrue(all(EXACT.values()))
        # The worked line on the key agrees with the answer.
        for x in math:
            self.assertIn(str(x['answer']).split(' ')[0].replace('%', '').lower(), x['fact'].lower(), x['title'])

    def test_lesson_is_rebuilt_not_saved(self):
        a, b = TG.lesson(3, 5, 1), TG.lesson(3, 5, 1)
        self.assertEqual(a, b)
        self.assertEqual(a['grade'], 3)
        self.assertNotIn('q', a)
        seen = {TG.lesson(2, d, s)['title'] for d in range(1, 4) for s in range(3)}
        self.assertEqual(len(seen), 8)

    def test_demands_are_fixed_and_fit_the_grade(self):
        for g in (2, 3, 4, 5):
            hits = 0
            for day in range(1, 30):
                for slot in range(3):
                    d = TG.demand_roll(g, day, slot)
                    self.assertEqual(d, TG.demand_roll(g, day, slot))
                    if d:
                        hits += 1
                        self.assertIn(g, TG.DEMAND[d['id']]['grades'])
            self.assertTrue(40 <= hits <= 75, (g, hits))
        for x in TG.DEMANDS:
            self.assertEqual([o['good'] for o in x['options']], [True, False, False])
            self.assertEqual(len({o['id'] for o in x['options']}), 3)
            for o in x['options']:
                self.assertLessEqual(len(o['label'].split()), 11, o['label'])
                if not o['good']:
                    self.assertIn(o['sev'], (1, 2, 3))
                    self.assertLessEqual(len(o['slip']), 200)
            self.assertLessEqual(len(x['text'].split()), 26, x['id'])


class GradeUnlockTests(unittest.TestCase):
    def test_unlock_by_level(self):
        for xp, top in ((0, 1), (89, 1), (90, 2), (269, 2), (270, 3), (450, 4), (630, 5), (5000, 5)):
            self.assertEqual(TG.unlocked(dict(xp=xp)), top, xp)

    def test_new_teacher_stays_in_class_1(self):
        j = Journey('teacher')
        hr = public_state(j.state)['careers']['teacher']['classroom']['homeroom']
        self.assertEqual((hr['g'], hr['offer'], hr['top']), (1, None, 1))
        self.assertNotIn('homeroom', j.c['ext']['data'])
        tv = pub_task(j, j.task['id'])
        self.assertNotIn('grade', tv['room'])
        self.assertEqual(tv['lesson']['title'], j.task['lesson']['title'])
        with self.assertRaises(GameError):
            j.act('cl_homeroom', grade=2)

    def test_offer_take_stay_and_switch(self):
        j = teacher(xp=95)
        hr = public_state(j.state)['careers']['teacher']['classroom']['homeroom']
        self.assertEqual(hr['offer']['g'], 2)
        self.assertIn('lớp 2A', hr['offer']['text'])
        j.act('cl_homeroom', grade=1)   # stay
        hr = public_state(j.state)['careers']['teacher']['classroom']['homeroom']
        self.assertEqual((hr['g'], hr['offer']), (1, None))
        self.assertEqual(j.c['ext']['data']['homeroom'], dict(g=1, seen=2, day=0))
        j.act('cl_homeroom', grade=2)   # switch later from the planner
        self.assertEqual(TG.homeroom(j.c), 2)
        with self.assertRaises(GameError):
            j.act('cl_homeroom', grade=1)   # once a day
        with self.assertRaises(GameError):
            j.act('cl_homeroom', grade=3)   # locked
        j.c['xp'] = 300
        self.assertEqual(public_state(j.state)['careers']['teacher']['classroom']['homeroom']['offer']['g'], 3)
        j.act('cl_homeroom', grade=3)   # a new offer can be taken the same day
        self.assertEqual(TG.homeroom(j.c), 3)
        validate_state(j.state)

    def test_bad_homeroom_rejected(self):
        j = teacher(xp=95, grade=2)
        for bad in (dict(g=6, seen=2, day=1), dict(g=2, seen=2), dict(g=2, seen=2, day=1, x=1), 'lop2'):
            s = copy.deepcopy(j.state)
            s['careers']['teacher']['ext']['data']['homeroom'] = bad
            with self.assertRaises(GameError):
                validate_state(s)


class GradePeriodTests(unittest.TestCase):
    def test_class_1_period_is_unchanged(self):
        j = Journey('teacher')
        tid = j.task['id']
        before = copy.deepcopy(j.task)
        play_to_ready(j, tid)
        t = j.get(tid)
        self.assertIn('room', t)
        self.assertNotIn('grade_room', t)
        self.assertNotIn('grade', t['room'])
        self.assertEqual(t['lesson'], before['lesson'])
        self.assertTrue(all(v['answer'] in t['lesson']['choices'] for v in t['room']['tickets'].values()))

    def test_task_generation_ignores_the_homeroom(self):
        a = make_task('teacher', 4, 1, 7)
        j = teacher(xp=700, grade=5)
        self.assertEqual(make_task('teacher', 4, 1, 7), a)
        self.assertEqual(TL.roll(4, 1), TL.roll(4, 1))

    def test_full_grade_period_with_demand(self):
        j = teacher(xp=300, grade=3)
        tid = j.task['id']
        v1 = copy.deepcopy(j.task)
        tv = pub_task(j, tid)
        lesson = TG.lesson(3, j.task['day'], TL.slot_of(j.task))
        self.assertEqual((tv['lesson']['title'], tv['title'], tv['room']['grade_label']), (lesson['title'], lesson['title'], 'Lớp 3A'))
        self.assertNotIn('answer', tv['lesson'])
        self.assertNotIn('grade_room', j.task)   # view only until the roll call
        play_to_ready(j, tid)
        t = j.get(tid)
        self.assertNotIn('room', t)
        r = t['grade_room']
        self.assertEqual(r['grade'], 3)
        for k in ('lesson', 'students', 'title', 'opening', 'npc'):
            self.assertEqual(t[k], v1[k], k)
        for tk in r['tickets'].values():
            self.assertIn(tk['answer'], lesson['choices'])
        if r.get('ask'):
            self.assertEqual(r['ask']['q'], lesson['title'])
        validate_state(j.state)
        if r['demand']:
            with self.assertRaises(GameError):
                j.act('lesson_complete', task=tid, confirm=True)
            view = pub_task(j, tid)['room']['demand']
            self.assertEqual(len(view['options']), 3)
            j.act('lesson_demand', task=tid, option=TG.DEMAND[r['demand']['id']]['options'][0]['id'])
            with self.assertRaises(GameError):
                j.act('lesson_demand', task=tid, option=TG.DEMAND[r['demand']['id']]['options'][1]['id'])
        money = j.c['money']
        j.act('lesson_complete', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertGreaterEqual(t['grade_room']['reward'], 45 + 2 * TG.PAY_STEP)
        self.assertGreater(j.c['money'], money)
        validate_state(j.state)

    def test_bad_demand_answer_reaches_the_parents(self):
        day = 1
        slot = find_slot(2, True, day)
        j = Journey('teacher', slot=slot, day=day)
        j.c['xp'] = 95
        j.act('cl_homeroom', grade=2)
        tid = j.task['id']
        play_to_ready(j, tid)
        dm = room(j, tid)['demand']
        bad = TG.DEMAND[dm['id']]['options'][1]
        mistakes = j.get(tid)['mistakes']
        j.act('lesson_demand', task=tid, option=bad['id'])
        self.assertEqual(j.get(tid)['mistakes'], mistakes + 1)
        out = j.act('lesson_complete', task=tid, confirm=True)
        self.assertIn('dm_' + dm['id'], [x['code'] for x in j.get(tid)['slips']])
        self.assertIn('Phụ huynh', out['message'])
        validate_state(j.state)

    def test_saved_grade_room_cannot_be_forged(self):
        slot = find_slot(4, True)
        j = Journey('teacher', slot=slot, day=1)
        j.c['xp'] = 500
        j.act('cl_homeroom', grade=4)
        tid = j.task['id']
        j.act('lesson_roll', task=tid, kid='all')
        good = copy.deepcopy(j.state)
        for mutate in (lambda r: r.update(grade=5), lambda r: r.update(grade=1), lambda r: r.update(demand=None),
                       lambda r: r['demand'].update(id='party' if r['demand']['id'] != 'party' else 'zalo'),
                       lambda r: r['demand'].update(pick='meet'), lambda r: r.update(extra=1)):
            s = copy.deepcopy(good)
            t = next(x for x in s['careers']['teacher']['tasks'] if x['id'] == tid)
            mutate(t['grade_room'])
            with self.assertRaises(GameError):
                validate_state(s)

    def test_period_started_keeps_its_grade(self):
        j = teacher(xp=300, grade=2)
        tid = j.task['id']
        j.act('lesson_roll', task=tid, kid='all')
        j.c['ext']['data']['homeroom']['day'] = 0
        j.act('cl_homeroom', grade=3)
        self.assertEqual(room(j, tid)['grade'], 2)
        self.assertEqual(pub_task(j, tid)['room']['grade'], 2)
        other = next(t for t in j.c['tasks'] if t['id'] != tid)
        self.assertEqual(pub_task(j, other['id'])['room']['grade'], 3)


@unittest.skipUnless(os.environ.get('MNL_OLD_TREE'), 'set MNL_OLD_TREE to an extracted older release')
class OlderBuildAcceptsTests(unittest.TestCase):
    """Rollback safety: the older build's validate_state passes a save with the new keys."""

    def _old_validate(self, state):
        tree = os.environ['MNL_OLD_TREE']
        code = ('import json,sys; sys.path.insert(0, sys.argv[1]); from game.engine import validate_state; '
                's=json.load(sys.stdin); validate_state(s); print("OK", s["careers"]["teacher"]["ext"]["data"].get("homeroom"))')
        p = subprocess.run([sys.executable, '-I', '-c', code, tree], input=json.dumps(state, ensure_ascii=False),
                           capture_output=True, text=True, cwd=tree)
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        self.assertTrue(p.stdout.startswith('OK'))

    def test_old_build_accepts_homeroom_and_grade_rooms(self):
        slot = find_slot(5, True)
        j = Journey('teacher', slot=slot, day=1)
        j.c['xp'] = 700
        j.act('cl_homeroom', grade=5)
        tid = j.task['id']
        self._old_validate(j.state)                     # homeroom only
        play_to_ready(j, tid)
        self.assertIn('grade_room', j.get(tid))
        self._old_validate(j.state)                     # a grade period in progress (tickets marked)
        r = room(j, tid)
        j.act('lesson_demand', task=tid, option=TG.DEMAND[r['demand']['id']]['options'][2]['id'])
        j.act('lesson_complete', task=tid, confirm=True)
        self._old_validate(j.state)                     # a finished grade period with slips


if __name__ == '__main__':
    unittest.main()
