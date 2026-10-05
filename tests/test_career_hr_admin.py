import copy
import unittest

from game.careers import hr_admin as M
from tests.office_desk_cases import DeskCases


class HrAdminTests(DeskCases, unittest.TestCase):
    M = M

    def changed_task(self,form,key):
        for day in range(2,80):
            for slot in range(8):
                t=M.make_task(day,slot,1);tw=t['work'].get('_twist')
                if t.get('form')==form and tw and tw.get(key) is not None:
                    t['known']=True
                    return t
        self.fail('No supplemental document fixture')

    def test_approved_supplement_appears_in_timesheet_documents_without_mutation(self):
        from game.careers import office_work as ow
        from tests.office_desk_cases import perfect
        t=self.changed_task('timesheet','seg');tw=t['work']['_twist'];t['ans']=perfect(t)
        self.assertFalse(ow.grade(t)['errors'])
        t['tw']='fired';before=copy.deepcopy(t);v=M.public_task(t)
        notes=next(p for p in v['papers'] if p['id']=='notes')['lines']
        self.assertTrue(any(tw['note'] in line for line in notes))
        self.assertEqual(t,before)
        self.assertTrue(ow.grade(t)['errors']);t['ans']=perfect(t);self.assertFalse(ow.grade(t)['errors'])

    def test_bhxh_supplement_is_on_card_and_correct_grading_uses_current_evidence(self):
        from game.careers import office_work as ow
        from tests.office_desk_cases import perfect
        t=self.changed_task('cv','item')
        # Find an actual BHXH supplement rather than the other withdrawal twist.
        for day in range(2,80):
            found=False
            for slot in range(8):
                row=M.make_task(day,slot,1);tw=row['work'].get('_twist')
                if row.get('form')=='cv' and tw and tw.get('bin')=='invite':t=row;found=True;break
            if found:break
        t['known']=True;tw=t['work']['_twist'];t['ans']=perfect(t)
        self.assertEqual(t['ans'][tw['item']],'verify');self.assertFalse(ow.grade(t)['errors'])
        t['tw']='fired';before=copy.deepcopy(t);v=M.public_task(t)
        card=next(r for r in v['work']['items'] if r['id']==tw['item'])
        self.assertIn(tw['note'],card['lines'][0]);self.assertEqual(t,before)
        t['ans']=perfect(t);self.assertEqual(t['ans'][tw['item']],'invite');self.assertFalse(ow.grade(t)['errors'])


if __name__ == '__main__':
    unittest.main()
