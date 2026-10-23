"""🏫 Trường học (game/school.py): Đại học Phố Mây with many majors, ✈️ du học một học kỳ (#315 Trung Quốc, #322)."""
import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import abroad as ab
from game import employment as emp
from game import pay_boost as pb
from game import promotion as pm
from game import school as sc
from game import school_content as SC
from game.engine import GameError, apply_action, public_state, validate_state
from game.school_q import check, questions
from tests.test_promotion import day, employee

ROOT = Path(__file__).resolve().parents[1]


def jr(j, name, **p):
    j.state, r = apply_action(j.state, None, name, p)
    return r


def student(cid='delivery', wallet=20000):
    j = employee(cid)
    day(j)
    j.state['journey']['wallet'] = wallet
    return j


def cur(j):
    return j.state['journey']['school']['cur']


def answers(j, kind, sid, right=True):
    """Answers for the quiz the server shows next (right ones, or all wrong)."""
    quiz = jr(j, 'jr_sch_view', view={'open': kind, 'subject': sid})['school']['quiz']
    assert quiz is None or '"ok"' not in json.dumps(quiz), quiz   # the keys stay on the server
    bank = questions(sc.SUBJECTS[sid])
    out = []
    for qi in sc._draw(j.state, cur(j), sid, kind):
        q = bank[qi]
        if q['k'] == 'c':
            out.append(q['ok'] if right else (q['ok'] + 1) % len(q['options']))
        elif q['k'] == 't':
            out.append(q['ok'] if right else not q['ok'])
        elif q['k'] == 'o':
            n = len(q['items'])
            out.append(list(range(n)) if right else list(reversed(range(n))))
        else:
            out.append(q['ok'] if right else q['ok'] + 1)
    return out


def attend_all_today(j):
    """Every class open today, answered right."""
    got = 0
    while True:
        v = jr(j, 'jr_sch_view')['school']['cur']
        if not v['avail']:
            return got
        sid = v['avail'][0]
        jr(j, 'jr_sch_class', subject=sid, answers=answers(j, 'class', sid))
        got += 1


def finish_semester(j, exam_right=True):
    """Classes, homework and exams of the semester running, day after day."""
    for _ in range(30):
        attend_all_today(j)
        c = cur(j)
        if c is None or c['ph'] != 'study':
            return
        for sid in list(c['sub']):
            if c['ph'] != 'study':
                break
            v = next(x for x in jr(j, 'jr_sch_view')['school']['cur']['subjects'] if x['id'] == sid)
            if v['can_hw'] and c['sub'][sid]['hw'] < 0:
                jr(j, 'jr_sch_hw', subject=sid, answers=answers(j, 'hw', sid))
            v = next(x for x in jr(j, 'jr_sch_view')['school']['cur']['subjects'] if x['id'] == sid)
            if v['can_exam']:
                jr(j, 'jr_sch_exam', subject=sid, answers=answers(j, 'exam', sid, exam_right))
                c = cur(j)
                if c is None:
                    return
        if c['ph'] != 'study':
            return
        day(j)
    raise AssertionError('the semester never ended')


class Banks(unittest.TestCase):
    def test_every_subject_is_complete_and_varied(self):
        self.assertEqual(check(SC.SUBJECTS), [])
        used = [sid for p in sc.PROGRAMS.values() for sem in p['sems'] for sid in sem]
        self.assertEqual(sorted(used), sorted(set(used)), 'a subject belongs to one program')
        self.assertEqual(set(used), set(SC.SUBJECTS))
        self.assertGreaterEqual(len(SC.MAJORS), 12)
        self.assertIn('dh_trung_quoc', sc.PROGRAMS)   # #315
        for p in sc.PROGRAMS.values():
            n = sum(len(questions(SC.SUBJECTS[sid])) for sem in p['sems'] for sid in sem)
            self.assertGreaterEqual(n, 30, p['id'])
            from game.content import CAREERS
            self.assertTrue(set(p['careers']) <= set(CAREERS), p['id'])

    def test_terms_have_their_own_life(self):
        for t in SC.TERMS:
            self.assertEqual(len(t['events']), 3, t['id'])
            self.assertEqual(len(t['jobs']), 3, t['id'])
            self.assertEqual(len(t['fly']), 4, t['id'])
            for job in t['jobs']:
                self.assertLess(job['ok'], len(job['options']))
            self.assertLess(t['visa_q'][2], len(t['visa_q'][1]))
            self.assertTrue(t['id'].startswith('dh_'))


class University(unittest.TestCase):
    def test_enrol_pays_the_semester_and_shows_the_timetable(self):
        j = student()
        w0 = j.state['journey']['wallet']
        r = jr(j, 'jr_sch_enrol', program='kinh_te')
        self.assertTrue(r['celebrate'])
        self.assertEqual(j.state['journey']['wallet'], w0 - sc.tuition('kinh_te'))
        self.assertEqual(j.state['journey']['history'][-1]['kind'], 'study')
        v = r['school']['cur']
        self.assertEqual((v['wd_label'], v['sem'], v['sems'], v['ph']), ('Thứ 2', 0, 2, 'study'))
        self.assertEqual(v['avail'], ['kt_vimo', 'kt_marketing'])
        self.assertEqual(len(v['week']), 7)
        self.assertEqual(v['week'][6]['subjects'], [])
        self.assertEqual(public_state(j.state)['journey']['school']['cur']['todo'], 2)
        with self.assertRaises(GameError):   # one program at a time
            jr(j, 'jr_sch_enrol', program='luat')
        with self.assertRaises(GameError):   # a term abroad goes through the application
            jr(j, 'jr_sch_enrol', program='dh_phap')
        validate_state(j.state)

    def test_a_class_is_a_short_lesson_two_a_day_one_per_subject(self):
        j = student()
        jr(j, 'jr_sch_enrol', program='cntt')
        quiz = jr(j, 'jr_sch_view', view={'open': 'class', 'subject': 'it_maytinh'})['school']['quiz']
        self.assertEqual((quiz['kind'], quiz['n'], len(quiz['qs'])), ('class', 1, 3))
        self.assertTrue(quiz['points'])
        self.assertNotIn('"ok"', json.dumps(quiz))   # keys stay on the server
        wrong = answers(j, 'class', 'it_maytinh', right=False)
        r = jr(j, 'jr_sch_class', subject='it_maytinh', answers=wrong)
        self.assertEqual(r['quiz']['right'], 0)
        self.assertTrue(all(row['why'] and row['right'] for row in r['quiz']['rows']))
        self.assertEqual(cur(j)['sub']['it_maytinh']['a'], 1)   # attendance counts: a wrong answer only teaches
        with self.assertRaises(GameError):   # the same subject once a day
            jr(j, 'jr_sch_class', subject='it_maytinh', answers=answers(j, 'class', 'it_maytinh'))
        with self.assertRaises(GameError):   # not on today's timetable
            jr(j, 'jr_sch_class', subject='it_mang', answers=[0, 0, 0])
        jr(j, 'jr_sch_class', subject='it_laptrinh', answers=answers(j, 'class', 'it_laptrinh'))
        self.assertEqual(jr(j, 'jr_sch_view')['school']['cur']['avail'], [])   # two classes a day
        with self.assertRaises(GameError):
            jr(j, 'jr_sch_class', subject='it_mang', answers=[0, 0, 0])
        with self.assertRaises(GameError):   # a bad shape is refused, nothing counted
            jr(j, 'jr_sch_class', subject='it_laptrinh', answers=['x'])
        day(j)
        self.assertEqual(jr(j, 'jr_sch_view')['school']['cur']['avail'], ['it_mang', 'it_maytinh'])   # Thứ 3: C, A
        validate_state(j.state)

    def test_sunday_has_no_class_and_a_finished_subject_frees_its_slot(self):
        j = student()
        jr(j, 'jr_sch_enrol', program='luat')
        c = cur(j)
        c['sub']['lu_daicuong']['a'] = 3
        v = jr(j, 'jr_sch_view')['school']['cur']
        self.assertEqual(v['avail'], ['lu_hopdong', 'lu_laodong'])   # Thứ 2: A (done) is a free slot
        j.state['journey']['life_day'] += 6   # today is Chủ nhật
        v = jr(j, 'jr_sch_view')['school']['cur']
        self.assertEqual((v['wd_label'], v['avail']), ('Chủ nhật', []))
        with self.assertRaises(GameError) as e:
            jr(j, 'jr_sch_class', subject='lu_hopdong', answers=answers(j, 'class', 'lu_hopdong'))
        self.assertIn('Chủ nhật', str(e.exception))

    def test_homework_and_exam_retake_next_day(self):
        j = student()
        jr(j, 'jr_sch_enrol', program='su_pham')
        c = cur(j)
        c['sub']['sp_tamly'].update(a=1, cs=3)
        with self.assertRaises(GameError):   # homework after two classes
            jr(j, 'jr_sch_hw', subject='sp_tamly', answers=[0, 0, 0])
        c['sub']['sp_tamly'].update(a=3, cs=9)
        with self.assertRaises(GameError):   # the exam after the homework
            jr(j, 'jr_sch_exam', subject='sp_tamly', answers=[0] * 5)
        r = jr(j, 'jr_sch_hw', subject='sp_tamly', answers=answers(j, 'hw', 'sp_tamly'))
        self.assertEqual(cur(j)['sub']['sp_tamly']['hw'], 3)
        self.assertIn('thi', r['message'])
        r = jr(j, 'jr_sch_exam', subject='sp_tamly', answers=answers(j, 'exam', 'sp_tamly', right=False))
        self.assertFalse(r['quiz']['passed'])
        self.assertIn('mai thi lại', r['message'])
        self.assertNotIn('sp_tamly', cur(j)['marks'])
        with self.assertRaises(GameError):   # one sitting a life day
            jr(j, 'jr_sch_exam', subject='sp_tamly', answers=answers(j, 'exam', 'sp_tamly'))
        first = sc._draw(j.state, cur(j), 'sp_tamly', 'exam')
        day(j)
        r = jr(j, 'jr_sch_exam', subject='sp_tamly', answers=answers(j, 'exam', 'sp_tamly'))
        self.assertTrue(r['quiz']['passed'])
        self.assertEqual(cur(j)['sub']['sp_tamly']['tries'], 2)
        m = cur(j)['marks']['sp_tamly']
        self.assertEqual(m, sc.mark(cur(j)['sub']['sp_tamly']))
        self.assertEqual(m, 100)   # 3 classes, 9/9, 3/3, 5/5
        self.assertEqual(r['quiz']['letter'], 'A')
        self.assertEqual(len(first), 5)
        validate_state(j.state)

    def test_marks_letters_and_gpa(self):
        self.assertEqual(sc.mark(dict(a=3, cs=9, hw=3, ex=5)), 100)
        self.assertEqual(sc.mark(dict(a=3, cs=0, hw=0, ex=3)), 40)
        self.assertEqual(sc.mark(dict(a=3, cs=6, hw=2, ex=4)), 77)   # 10 + 13.3 + 13.3 + 40
        self.assertEqual(sc.letter(77), ('B', 300))
        self.assertEqual(sc.letter(85), ('A', 400))
        self.assertEqual(sc.gpa({'a': 100, 'b': 77}), 350)
        self.assertEqual(sc.class_of(350), 'gioi')
        self.assertEqual(sc.class_of(360), 'xuat_sac')
        self.assertEqual(sc.fmt_gpa(305), '3,05')

    def test_two_semesters_to_a_degree_and_its_perks(self):
        j = student('delivery')
        w0 = j.state['journey']['wallet']
        jr(j, 'jr_sch_enrol', program='kinh_te')
        finish_semester(j)
        c = cur(j)
        self.assertEqual(c['ph'], 'break')
        self.assertEqual(len(c['marks']), 3)
        with self.assertRaises(GameError):
            jr(j, 'jr_sch_class', subject='kt_vimo', answers=[0, 0, 0])
        r = jr(j, 'jr_sch_next')
        self.assertEqual((cur(j)['sem'], cur(j)['ph']), (1, 'study'))
        self.assertEqual(set(cur(j)['sub']), {'kt_taichinh', 'kt_khoinghiep', 'kt_tmdt'})
        validate_state(j.state)
        finish_semester(j)
        b = j.state['journey']['school']
        self.assertIsNone(b['cur'])
        deg = b['deg']['kinh_te']
        self.assertEqual((deg['g'], deg['gpa']), ('xuat_sac', 400))
        self.assertTrue(deg['serial'].startswith('PCC-'))
        J = j.state['journey']
        self.assertIn('h_bachelor', J['titles'])
        self.assertIn('h_top', J['titles'])
        paid = 2 * sc.tuition('kinh_te')
        self.assertTrue(any(h['label'].startswith('Học bổng xuất sắc') and h['amount'] == paid * sc.SCHOLAR_PCT // 100 for h in J['history']))
        # 🎓 the perks: +15 % at the major's workplaces (game/pay_boost.py), early opening, the hire roll, not elsewhere
        self.assertEqual(sc.pay_pct(j.state, 'grocery'), 15)
        self.assertEqual(sc.pay_pct(j.state, 'delivery'), 0)
        self.assertEqual(pb.pcts(j.state, 'teller')['degree'], 15)
        self.assertEqual(pb.pcts(j.state, 'delivery')['degree'], 0)
        self.assertTrue(sc.opens(j.state, 'teller'))
        pub = public_state(j.state)['journey']
        self.assertIn('teller', pub['unlocked'])
        self.assertEqual(pub['school']['deg'], ['kinh_te'])
        validate_state(j.state)
        self.assertLess(j.state['journey']['wallet'], w0)

    def test_a_second_major_after_the_first(self):
        j = student()
        b = {'v': 1, 'cur': None, 'kept': {},
             'deg': {'luat': dict(d=1, g='kha', gpa=280, date='2026-10-23', serial='PCC-L-AAAAAA', ev=0)}}
        j.state['journey']['school'] = b
        validate_state(j.state)
        with self.assertRaises(GameError):   # a degree is earned once
            jr(j, 'jr_sch_enrol', program='luat')
        jr(j, 'jr_sch_enrol', program='ke_toan')
        self.assertEqual(cur(j)['p'], 'ke_toan')
        self.assertEqual(sc.pay_pct(j.state, 'lawyer'), 10)
        b = j.state['journey']['school']
        b['deg']['ke_toan'] = dict(d=2, g='tb', gpa=200, date='2026-10-23', serial='PCC-KT-AAAAAA', ev=0)
        b['cur'] = None
        self.assertEqual(sc.pay_pct(j.state, 'accounting'), 8)

    def test_drop_refunds_half_of_the_classes_left_and_keeps_finished_semesters(self):
        j = student()
        jr(j, 'jr_sch_enrol', program='nong_nghiep')
        finish_semester(j)
        jr(j, 'jr_sch_next')
        fee = cur(j)['fee']
        jr(j, 'jr_sch_class', subject='nn_sauhai', answers=answers(j, 'class', 'nn_sauhai'))
        w = j.state['journey']['wallet']
        with self.assertRaises(GameError):
            jr(j, 'jr_sch_drop')
        r = jr(j, 'jr_sch_drop', confirm=True)
        self.assertEqual(j.state['journey']['wallet'], w + fee * 8 // 9 // 2)
        self.assertIn('bảo lưu', r['message'])
        b = j.state['journey']['school']
        self.assertIsNone(b['cur'])
        self.assertEqual(set(b['kept']['nong_nghiep']), {'nn_trongtrot', 'nn_dat', 'nn_channuoi'})
        validate_state(j.state)
        r = jr(j, 'jr_sch_enrol', program='nong_nghiep')
        self.assertIn('bảo lưu', r['message'])
        self.assertEqual((cur(j)['sem'], len(cur(j)['marks'])), (1, 3))
        self.assertNotIn('nong_nghiep', j.state['journey']['school']['kept'])
        validate_state(j.state)

    def test_school_events_one_a_day(self):
        j = student()
        jr(j, 'jr_sch_enrol', program='du_lich')
        v = jr(j, 'jr_sch_view')['school']['cur']
        self.assertTrue(v['can_event'])
        ev = v['events'][0]
        r = jr(j, 'jr_sch_event', event=ev['id'], option=1)
        self.assertTrue(r['message'])
        with self.assertRaises(GameError):
            jr(j, 'jr_sch_event', event=v['events'][1]['id'], option=0)
        with self.assertRaises(GameError):   # a part-time job is for terms abroad
            jr(j, 'jr_sch_job', option=0)
        day(j)
        with self.assertRaises(GameError):   # each event once
            jr(j, 'jr_sch_event', event=ev['id'], option=0)
        jr(j, 'jr_sch_event', event=v['events'][1]['id'], option=0)
        validate_state(j.state)

    def test_thin_wallet_is_refused_cleanly(self):
        j = student(wallet=3)
        with self.assertRaises(GameError):
            jr(j, 'jr_sch_enrol', program='kinh_te')
        self.assertEqual(j.state['journey']['wallet'], 3)
        self.assertNotIn('school', public_state(j.state)['journey'])


class Abroad(unittest.TestCase):
    def apply(self, j, pid='dh_trung_quoc'):
        docs = [d for d, _, ok in SC.DOCS if ok]
        jr(j, 'jr_sch_apply', program=pid, docs=docs)
        jr(j, 'jr_sch_visa', option=sc.PROGRAMS[pid]['visa_q'][2])
        return jr(j, 'jr_sch_fly')

    def test_papers_visa_flight_then_a_term_in_china(self):
        j = student()
        w0 = j.state['journey']['wallet']
        with self.assertRaises(GameError) as e:   # wrong papers cost nothing, the message says what is off
            jr(j, 'jr_sch_apply', program='dh_trung_quoc', docs=['passport', 'cat'])
        self.assertIn('còn thiếu', str(e.exception))
        self.assertIn('Ảnh mèo cưng', str(e.exception))
        self.assertEqual(j.state['journey']['wallet'], w0)
        docs = [d for d, _, ok in SC.DOCS if ok]
        jr(j, 'jr_sch_apply', program='dh_trung_quoc', docs=docs)
        cost = sc.tuition('dh_trung_quoc') + sc.visa_fee('dh_trung_quoc')
        self.assertEqual(j.state['journey']['wallet'], w0 - cost)
        v = jr(j, 'jr_sch_view')['school']['cur']
        self.assertEqual(v['ph'], 'visa')
        self.assertEqual(v['avail'], [])
        self.assertIn('Trung Quốc', v['visa']['q'])
        ok = sc.PROGRAMS['dh_trung_quoc']['visa_q'][2]
        with self.assertRaises(GameError):   # a silly answer: try again, nothing lost
            jr(j, 'jr_sch_visa', option=(ok + 1) % 3)
        with self.assertRaises(GameError):
            jr(j, 'jr_sch_fly')
        jr(j, 'jr_sch_visa', option=ok)
        validate_state(j.state)
        r = jr(j, 'jr_sch_fly')
        self.assertEqual(len(r['lines']), 4)
        v = r['school']['cur']
        self.assertEqual((v['ph'], v['wd_label'], v['avail']), ('study', 'Thứ 2', ['dh_cn_ngu', 'dh_cn_vh']))
        self.assertTrue(v['job']['can'])
        # the part-time job: once a life day
        quiz = jr(j, 'jr_sch_view', view={'open': 'job'})['school']['quiz']
        self.assertEqual(quiz['kind'], 'job')
        w = j.state['journey']['wallet']
        job = sc.PROGRAMS['dh_trung_quoc']['jobs'][0]
        r = jr(j, 'jr_sch_job', option=job['ok'])
        self.assertEqual(j.state['journey']['wallet'], w + sc.JOB_PAY[1])
        with self.assertRaises(GameError):
            jr(j, 'jr_sch_job', option=0)
        validate_state(j.state)
        self.assertEqual(ab.degrees(j.state), 0)
        finish_semester(j)
        b = j.state['journey']['school']
        self.assertIsNone(b['cur'])
        self.assertIn('dh_trung_quoc', b['deg'])
        self.assertIn('h_overseas', j.state['journey']['titles'])
        self.assertNotIn('h_bachelor', j.state['journey']['titles'])
        # ✈️ it counts as a degree of Du học (by country): hired pay +10 %
        self.assertEqual(ab.degrees(j.state), 1)
        self.assertEqual(ab.degree_pct(j.state), 10)
        self.assertEqual(sc.pay_pct(j.state, 'customs'), 15)
        self.assertEqual(pb.pcts(j.state, 'delivery')['degree'], 15)
        validate_state(j.state)

    def test_a_term_and_a_short_course_of_one_country_count_once(self):
        j = student()
        j.state['journey']['abroad'] = dict(ab.initial(), deg={'han_quoc': dict(d=1, g='gioi')})
        self.assertEqual(ab.degrees(j.state), 1)
        j.state['journey']['school'] = {'v': 1, 'cur': None, 'kept': {}, 'deg': {
            'dh_han_quoc': dict(d=2, g='kha', gpa=300, date='2026-10-23', serial='PCC-DHQ-AAAAAA', ev=1),
            'dh_phap': dict(d=3, g='kha', gpa=300, date='2026-10-23', serial='PCC-DP-AAAAAA', ev=1)}}
        validate_state(j.state)
        self.assertEqual(ab.degrees(j.state), 2)
        self.assertEqual(ab.degree_pct(j.state), 15)

    def test_a_term_abroad_needs_no_shut_workplace_and_drop_flies_home(self):
        j = student()
        self.apply(j, 'dh_phap')
        day(j)   # a shift at home still closes the life day
        self.assertEqual(cur(j)['ph'], 'study')
        fee = cur(j)['fee']
        w = j.state['journey']['wallet']
        r = jr(j, 'jr_sch_drop', confirm=True)
        self.assertIn('bay về', r['message'])
        self.assertEqual(j.state['journey']['wallet'], w + fee // 2)
        self.assertEqual(j.state['journey']['school']['kept'], {})


class Hiring(unittest.TestCase):
    def test_the_degree_rolls_like_the_certificate(self):
        j = student('delivery')
        from game import certificates as ct
        gid = ct.group_of('nurse')
        self.assertIsNotNone(gid)
        self.assertIsNone(emp._cert_roll(j.state, j.state['careers']['nurse'], 'nurse', {'id': 'x'}, False, False))
        j.state['journey']['school'] = {'v': 1, 'cur': None, 'kept': {}, 'deg': {
            'y_duoc': dict(d=2, g='gioi', gpa=330, date='2026-10-23', serial='PCC-YD-AAAAAA', ev=0)}}
        chance = emp._cert_roll(j.state, j.state['careers']['nurse'], 'nurse', {'id': 'x'}, False, False)
        self.assertEqual(chance['cert'], gid)   # stored as the place's certificate: older builds validate it
        self.assertIn('Y dược', emp._chance_line(chance, j.state, 'nurse'))

    def test_the_degree_counts_for_the_third_promotion_step(self):
        j = student('delivery')
        j.c['metrics']['served'] = 0
        rec = pm.record(j.state, 'delivery', True)
        pm._sync(rec, j.c)
        rec['rank'] = 2
        row = lambda: next(r for r in pm._gates(j.state, j.c, 'delivery', rec) if r['id'] == 'certificate_or_served')['met']
        self.assertFalse(row())
        j.state['journey']['school'] = {'v': 1, 'cur': None, 'kept': {}, 'deg': {
            'dh_trung_quoc': dict(d=2, g='kha', gpa=300, date='2026-10-23', serial='PCC-DTQ-AAAAAA', ev=0)}}
        self.assertTrue(row())


class Saves(unittest.TestCase):
    def test_an_old_save_without_school_is_untouched(self):
        j = student()
        before = copy.deepcopy(j.state['journey'])
        pub = public_state(j.state)['journey']
        self.assertNotIn('school', pub)
        self.assertNotIn('school', j.state['journey'])
        r = jr(j, 'jr_sch_view')   # looking stores nothing
        self.assertIsNone(r['school']['cur'])
        self.assertNotIn('school', j.state['journey'])
        self.assertEqual(before['wallet'], j.state['journey']['wallet'])
        self.assertTrue(public_state(j.state)['content'] if 'content' in public_state(j.state) else True)

    def test_a_student_mid_course_in_the_short_course_keeps_going(self):
        j = student()
        from game import abroad_content as AC
        jr(j, 'jr_abroad_enrol', program='nhat_ban')
        jr(j, 'jr_abroad_lesson', option=AC.PROGRAMS['nhat_ban']['lessons'][0]['ok'])
        jr(j, 'jr_sch_enrol', program='kien_truc')   # both at once is fine
        day(j)
        jr(j, 'jr_abroad_lesson', option=AC.PROGRAMS['nhat_ban']['lessons'][1]['ok'])
        self.assertEqual(j.state['journey']['abroad']['study']['n'], 2)
        validate_state(j.state)

    def test_a_bad_block_is_refused_and_unknown_programs_are_kept(self):
        j = student()
        jr(j, 'jr_sch_enrol', program='thoi_trang')
        s = copy.deepcopy(j.state)
        s['journey']['school']['cur']['sub']['tt_hinhhoa']['a'] = 9
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['journey']['school']['cur']['marks']['tt_hinhhoa'] = 90   # passed without an exam
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['journey']['school']['deg']['future_major'] = dict(d=1, g='zz', gpa=0, date='x', serial='', ev=0)
        s['journey']['school']['later'] = {}   # a key a newer build adds
        validate_state(s)
        self.assertNotIn('future_major', [d['p'] for d in sc.view(s)['deg']])

    def test_catalogue_has_no_keys(self):
        cat = public_state(student().state).get('content') or {}
        K = sc.catalogue()
        text = json.dumps(K, ensure_ascii=False)
        self.assertNotIn('"ok"', text)
        self.assertEqual(len(K['majors']), len(SC.MAJORS))
        self.assertTrue(all('fee' in m and m['sems'] for m in K['majors']))
        self.assertEqual({d['id'] for d in K['docs']}, {d for d, _, _ in SC.DOCS})
        self.assertNotIn('True', text)
        self.assertIsInstance(cat, dict)
        from game import journey
        self.assertEqual(journey.content()['school'], K)   # bootstrap content


class Earnings(unittest.TestCase):
    def test_a_hired_day_at_a_linked_place_pays_the_degree_percent(self):
        j = student('delivery')
        base = day(j)['summary']['job']['salary']
        rows = lambda: [r for r in j.c['ops']['finance']['ledger'] if str(r.get('reason', '')).startswith(pb.PREFIX)]
        self.assertEqual(rows(), [])   # tests run with MNL_PAYBOOST_OFF: no 💰 row without a degree
        j.state['journey']['school'] = {'v': 1, 'cur': None, 'kept': {}, 'deg': {
            'dh_trung_quoc': dict(d=2, g='kha', gpa=300, date='2026-10-23', serial='PCC-DTQ-AAAAAA', ev=0)}}
        r = day(j)
        got = rows()
        self.assertEqual(len(got), 1)
        self.assertIn('🎓 có bằng', got[0]['reason'])
        self.assertIn(got[0]['amount'], (base * 10 // 100, base * 10 // 100 + 1))   # +10 % (Khá), rounded by a hash
        self.assertEqual(r['payboost']['degree'], got[0]['amount'])


@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class ClientRenders(unittest.TestCase):
    def test_the_page_renders_real_views(self):
        views = []
        j = student()
        views.append(jr(j, 'jr_sch_view')['school'])
        jr(j, 'jr_sch_enrol', program='y_duoc')
        views.append(jr(j, 'jr_sch_view', view={'open': 'class', 'subject': 'yd_cothe'})['school'])
        finish_semester(j)
        views.append(jr(j, 'jr_sch_view')['school'])   # break
        jr(j, 'jr_sch_next')
        for sid in ('yd_duoc', 'yd_dinhduong', 'yd_giaotiep'):
            cur(j)['sub'][sid].update(a=3, cs=5, hw=1, hwn=1, hwd=1)
        for sid in ('yd_duoc', 'yd_dinhduong', 'yd_giaotiep'):
            views.append(jr(j, 'jr_sch_view', view={'open': 'exam', 'subject': sid})['school'])
        jr(j, 'jr_sch_drop', confirm=True)
        docs = [d for d, _, ok in SC.DOCS if ok]
        jr(j, 'jr_sch_apply', program='dh_han_quoc', docs=docs)
        views.append(jr(j, 'jr_sch_view')['school'])
        jr(j, 'jr_sch_visa', option=sc.PROGRAMS['dh_han_quoc']['visa_q'][2])
        views.append(jr(j, 'jr_sch_view')['school'])
        jr(j, 'jr_sch_fly')
        views.append(jr(j, 'jr_sch_view', view={'open': 'job'})['school'])
        finish_semester(j)
        views.append(jr(j, 'jr_sch_view')['school'])
        self.assertTrue(views[-1]['deg'])
        kinds = {q['k'] for v in views if v.get('quiz') for q in v['quiz'].get('qs', [])}
        self.assertTrue({'c', 't'} <= kinds, kinds)
        K = public_state(j.state)['content']['journey']['school'] if 'content' in public_state(j.state) else sc.catalogue()
        out = subprocess.run(['node', str(ROOT / 'tests' / 'school.mjs')], cwd=ROOT, text=True, encoding='utf-8',
                             input=json.dumps(dict(K=K, views=views), ensure_ascii=False), capture_output=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        self.assertEqual(out.stdout, 'ok')


if __name__ == '__main__':
    unittest.main()
