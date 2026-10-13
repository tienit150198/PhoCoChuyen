"""Mastery reducer hooks, real service completion and reward accounting."""
import copy
import json
import unittest
from unittest.mock import patch
from game import engine as E, career_mastery as CM, journey as JR, x3_week
from tests.helpers import Journey
from tests.test_career_laundry import solve


class MasteryEngine(unittest.TestCase):
    def seed(self, j, passed=False):
        from tests.test_career_mastery import CareerMastery
        fixture=CareerMastery();fixture.setUp()
        c=fixture.eligible('laundry')
        if passed:fixture.exam(c,'laundry')
        j.c['mastery']=copy.deepcopy(c['mastery'])
        j.c['xp']=c['xp']
        j.c['day']=c['day']
        j.c['metrics']['served']=c['metrics']['served']
        j.c['tasks']=[];j.c['active_task']=None;j.c['open']=False
        E.validate_state(j.state)

    def test_real_task_hook_close_and_duplicate_payment(self):
        j=Journey('laundry');self.seed(j,True)
        j.act('start_day')
        for task in list(j.c['tasks']):solve(j,task['id'])
        self.assertEqual(CM.public(j.c,'laundry')['today']['clean'],3)
        result=j.act('end_day',carry_event=True)
        self.assertEqual(result['summary']['mastery']['bonus'],6)
        rows=[r for r in j.c['ops']['finance']['ledger'] if r.get('ref')=='mastery-16']
        self.assertEqual([r['amount'] for r in rows],[6])
        before=copy.deepcopy(j.state)
        with self.assertRaises(E.GameError):j.act('end_day',carry_event=True)
        self.assertEqual(j.state,before)
        E.validate_state(json.loads(json.dumps(j.state)))

    def test_exam_commands_do_not_tick_and_public_hides_saved_answers(self):
        j=Journey('laundry');self.seed(j)
        turn=j.c['turn'];j.act('mastery_start')
        for _ in range(4):
            paper=j.c['mastery']['exam']
            q=CM._paper('laundry',paper)[len(paper['answers'])]
            j.act('mastery_answer',option=next(o['id'] for o in q['options'] if o['score']==2))
            view=E.public_state(j.state)['careers']['laundry']['mastery']
            self.assertNotIn('answers',json.dumps(view));self.assertNotIn('awards',view)
            self.assertEqual(j.c['turn'],turn)
        j.act('mastery_finish')
        self.assertEqual(j.c['mastery']['tier'],1)
        self.assertEqual(j.c['turn'],turn)
        other=E.public_state(j.state,full='mother_baby')['careers']['laundry']
        self.assertNotIn('mastery',other)

    def test_unpaid_day_has_no_mastery_payment(self):
        j=Journey('laundry');self.seed(j,True);j.act('start_day')
        for task in list(j.c['tasks']):solve(j,task['id'])
        with patch('game.interest_clock.day_paid',return_value=False):
            result=j.act('end_day',carry_event=True)
        self.assertTrue(result['summary']['mastery']['qualified'])
        self.assertEqual(result['summary']['mastery']['bonus'],0)

    def test_mastery_bonus_is_not_multiplied_by_weekly_x3(self):
        s=E.new_state();JR.enable_story(s,4242)
        s['journey'].update(gender='female',intro=True)
        res={'summary':{'net':46,'job':{},'mastery':{'bonus':6}}}
        with patch.object(x3_week,'on',return_value=True):JR._end_of_day(s,'grocery',res)
        rows=[r['amount'] for r in s['journey']['history'] if r['label'].startswith('🔥')]
        self.assertEqual(rows,[80])
