import copy
import importlib.util
import unittest

from game import employment as emp
from game.engine import GameError, apply_action, new_state, public_state, validate_state


class AccountingSchoolTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('game.accounting_school'), 'Accounting school is not implemented')
        from game import accounting_school as school
        from game import accounting_content as content
        self.school, self.content = school, content
        self.s = new_state()
        school.migrate(self.s)

    def learn(self, course):
        for chapter in self.school.course(course)['chapters']:
            for lesson in chapter['lessons']:
                self.school.action(self.s, 'as_open', {'lesson': lesson['id']})
                for q in lesson['questions']:
                    self.school.action(self.s, 'as_answer', {'lesson': lesson['id'], 'question': q['id'], 'answer': self.answer(q)})

    def answer(self, q):
        if q['kind']=='entry': return [dict(debit=d,credit=c,amount=v) for d,c,v in q['_key']]
        return copy.deepcopy(q['_key'])

    def sit(self, course, correct=True):
        self.school.action(self.s, 'as_exam_start', {'course': course})
        sheet = self.s['accounting_school']['active_exam']
        for qid in list(sheet['qs']):
            q = self.school.exam_question(course, qid)
            answer = self.answer(q)
            if not correct:
                if q['kind'] == 'choice': answer = next(o['id'] for o in q['options'] if o['id'] != answer)
                elif q['kind'] == 'number': answer += 1
                elif q['kind'] == 'entry': answer[0]['amount'] += 1
                elif q['kind'] == 'fields':
                    fid=next(iter(answer));answer[fid]+=1
                elif q['kind'] == 'order': answer[0],answer[1]=answer[1],answer[0]
                elif q['kind'] == 'multi':
                    wrong=next((o['id'] for o in q['options'] if o['id'] not in answer),None)
                    if wrong:answer.append(wrong)
                    elif len(answer)>1:answer.pop()
                elif q['kind'] == 'match':
                    fid=next(iter(answer));answer[fid]=next(o['id'] for o in q['right'] if o['id']!=answer[fid])
            out = self.school.action(self.s, 'as_exam_answer', {'question': qid, 'answer': answer})
        return out

    def certify(self):
        for course in ('basic', 'vn_business'):
            self.learn(course)
            self.sit(course)

    def test_cannot_finish_by_reading_or_start_exam_without_exercises(self):
        lesson = self.school.course('basic')['chapters'][0]['lessons'][0]
        self.school.action(self.s, 'as_open', {'lesson': lesson['id']})
        self.assertFalse(self.school.lesson_done(self.s, lesson['id']))
        with self.assertRaises(GameError): self.school.action(self.s, 'as_exam_start', {'course': 'basic'})

    def test_wrong_answer_retries_and_unopened_submission_rejected(self):
        lesson = self.school.course('basic')['chapters'][0]['lessons'][0]
        q = next(q for q in lesson['questions'] if q['kind'] == 'choice')
        with self.assertRaises(GameError): self.school.action(self.s, 'as_answer', {'lesson': lesson['id'], 'question': q['id'], 'answer': q['_key']})
        self.school.action(self.s, 'as_open', {'lesson': lesson['id']})
        wrong = next(o['id'] for o in q['options'] if o['id'] != q['_key'])
        self.assertFalse(self.school.action(self.s, 'as_answer', {'lesson': lesson['id'], 'question': q['id'], 'answer': wrong})['correct'])
        self.assertTrue(self.school.action(self.s, 'as_answer', {'lesson': lesson['id'], 'question': q['id'], 'answer': q['_key']})['correct'])

    def test_exam_pass_fail_retake_and_bonus_never_stacks(self):
        self.learn('basic')
        self.assertFalse(self.sit('basic',False)['exam']['passed'])
        self.assertFalse(self.school.certified(self.s,'basic'))
        validate_state(self.s)
        self.assertTrue(self.sit('basic')['exam']['passed'])
        self.assertEqual(self.school.salary_multiplier(self.s, 'corp_accounting'), 1)
        self.learn('vn_business')
        self.assertTrue(self.sit('vn_business')['exam']['passed'])
        certificate = copy.deepcopy(self.s['accounting_school']['exams']['vn_business']['certificate'])
        self.assertEqual(self.school.salary_multiplier(self.s, 'corp_accounting'), 3)
        self.sit('vn_business')
        self.assertEqual(self.school.salary_multiplier(self.s, 'corp_accounting'), 3)
        self.assertEqual(certificate, self.s['accounting_school']['exams']['vn_business']['certificate'])
        self.assertEqual(self.school.salary_multiplier(self.s, 'teacher'), 1)
        validate_state(self.s)

    def test_enterprise_salary_requires_exam_and_full_book_and_pays_once(self):
        from game import accounting_company as company
        from game import journey
        journey.enable_story(self.s)
        with self.assertRaises(GameError):self.school.action(self.s,'as_company_join',{})
        self.certify()
        self.school.action(self.s,'as_company_join',{})
        book=self.s['accounting_school']['company']
        with self.assertRaises(GameError):self.school.action(self.s,'as_company_finish',{})
        for task in company.tasks(book):
            self.school.action(self.s,'as_company_inspect',{'task':task['id']})
            self.school.action(self.s,'as_company_answer',{'task':task['id'],'answer':copy.deepcopy(task['_key'])})
        wallet=self.s['journey']['wallet'];fund=self.s['careers']['corp_accounting']['money'];day=self.s['journey']['life_day']
        result=self.school.action(self.s,'as_company_finish',{})
        self.assertEqual(result['salary'],self.s['careers']['corp_accounting']['job']['salary']*3)
        self.assertEqual(self.s['journey']['wallet'],wallet+result['salary'])
        self.assertEqual(self.s['journey']['stats']['salary'],result['salary'])
        self.assertEqual(self.s['journey']['life_day'],day)
        self.assertEqual(self.s['careers']['corp_accounting']['money'],fund)
        with self.assertRaises(GameError):self.school.action(self.s,'as_company_finish',{})
        self.school.action(self.s,'as_company_next',{})
        self.assertEqual(book['period'],2)
        self.assertEqual(book['at'],0)
        validate_state(self.s)

    def test_public_projection_hides_unsolved_and_active_exam_keys(self):
        lesson = self.school.course('basic')['chapters'][0]['lessons'][0]
        self.school.action(self.s, 'as_open', {'lesson': lesson['id']})
        view = self.school.public(self.s)
        self.assertNotIn('_key', repr(view))
        self.assertNotIn('explain', view['lesson']['questions'][0])
        self.learn('basic')
        self.school.action(self.s, 'as_exam_start', {'course': 'basic'})
        self.assertNotIn('_key', repr(self.school.public(self.s)['active_exam']))
        self.assertNotIn('explain', repr(self.school.public(self.s)['active_exam']))

    def test_actual_daily_pay_is_three_times_including_probation(self):
        self.certify()
        c = self.s['careers']['corp_accounting']
        c['job'] = emp.hired_record('corp_accounting', 'ca-hq')
        c['day_completed'] = 1
        self.assertEqual(emp.public(c, 'corp_accounting', self.s)['salary'], c['job']['salary'] * 3)
        note = emp.on_close(self.s, c, 'corp_accounting')
        self.assertEqual(note['salary'], c['job']['salary'] * 3)
        c['day'] += 1
        c['job']['probation'] = True
        c['job']['probation_left'] = 2
        note = emp.on_close(self.s, c, 'corp_accounting')
        self.assertEqual(note['salary'], round(c['job']['salary'] * .85) * 3)

    def test_old_save_migration_and_engine_dispatch(self):
        self.s.pop('accounting_school', None)
        lesson = self.school.course('basic')['chapters'][0]['lessons'][0]
        s, result = apply_action(self.s, None, 'as_open', {'lesson': lesson['id']})
        self.assertIn('accounting_school', s)
        self.assertEqual(result['accounting_view']['lesson']['id'], lesson['id'])
        self.assertNotIn('courses', public_state(s)['accounting_school'])  # public_state only carries the summary
        validate_state(s)
        self.assertNotIn('accounting_school', self.s)

    def test_tampered_certificate_without_exam_proof_rejected(self):
        self.s['accounting_school']['exams']['vn_business'] = {'attempts': 1, 'score': 100, 'best': 100, 'certificate': {'id': 'vn_business', 'score': 100}}
        with self.assertRaises(GameError): self.school.validate(self.s)

    def test_empty_exam_and_altered_draw_rejected_on_import(self):
        for value in ({},[],False):
            self.s['accounting_school']['active_exam']=value
            with self.assertRaises(GameError):self.school.validate(self.s)
        self.s['accounting_school']['active_exam']=None
        self.learn('basic')
        self.school.action(self.s,'as_exam_start',{'course':'basic'})
        paper=self.s['accounting_school']['active_exam']
        paper['qs'][0],paper['qs'][1]=paper['qs'][1],paper['qs'][0]
        with self.assertRaises(GameError):self.school.validate(self.s)

    def test_arbitrary_entry_metadata_rejected_and_failed_action_is_atomic(self):
        lesson=next(l for l in self.content.LESSONS.values() if any(q['kind']=='entry' for q in l['questions']))
        q=next(q for q in lesson['questions'] if q['kind']=='entry')
        self.school.action(self.s,'as_open',{'lesson':lesson['id']})
        before=copy.deepcopy(self.s)
        answer=self.answer(q);answer[0]['ignored']='x'*200_000
        with self.assertRaises(GameError):apply_action(self.s,None,'as_answer',{'lesson':lesson['id'],'question':q['id'],'answer':answer})
        self.assertEqual(before,self.s)
        self.s['accounting_school']['progress'][lesson['id']]['answers'][q['id']]=answer
        with self.assertRaises(GameError):self.school.validate(self.s)


if __name__ == '__main__': unittest.main()
