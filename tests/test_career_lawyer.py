import copy
import json
import unittest
from game.careers import lawyer as lw
from game.engine import GameError, validate_state
from tests.helpers import Journey


def step(j, wrong=None):
    t=j.task
    st=t['needs']['steps'][t['at']]
    return j.act('lw_submit',task=t['id'],step=st['id'],value=copy.deepcopy(t['_key'][st['id']]) if wrong is None else wrong)


def solve(j):
    tid=j.task['id']
    if not j.task['known']:j.act('ask',task=tid)
    count=0
    while j.get(tid)['status']!='completed':
        step(j);count+=1
    return count


class LawyerTests(unittest.TestCase):
    def test_correct_recovery_and_duplicate(self):
        j=Journey('lawyer',slot=1)
        tid=j.task['id']
        with self.assertRaises(GameError):step(j)
        j.act('ask',task=tid)
        st=j.task['needs']['steps'][0]
        wrong=['signed','claim']
        result=step(j,wrong)
        self.assertFalse(result['correct'])
        self.assertEqual(j.task['at'],0)
        self.assertEqual(solve(j),5)
        self.assertGreater(j.get(tid)['mistakes'],0)
        before=copy.deepcopy(j.state)
        with self.assertRaises(GameError):j.act('lw_submit',task=tid,step='filing',value='a')
        self.assertEqual(before,j.state)
        self.assertEqual(j.c['ext']['data']['qualified'],0)

    def test_invalid_atomic_roundtrip_and_hidden_key(self):
        j=Journey('lawyer',slot=2,day=40);j.act('ask')
        before=copy.deepcopy(j.state)
        for payload in ({'step':'amount','value':20},{'step':'evidence','value':{}},{'step':'evidence','value':['fake']}, {'step':'evidence','value':['d1','d1']}):
            with self.assertRaises(GameError):j.act('lw_submit',**payload)
            self.assertEqual(before,j.state)
        step(j);step(j)
        j.state=json.loads(json.dumps(j.state));validate_state(j.state)
        self.assertNotIn('_key',lw.public_task(j.task))
        corrupted=copy.deepcopy(j.state)
        corrupted['careers']['lawyer']['tasks'][0]['needs']['rule']='forged'
        with self.assertRaises(GameError):validate_state(corrupted)
        corrupted=copy.deepcopy(j.state)
        corrupted['careers']['lawyer']['tasks'][0]['_key']['amount']=9999
        with self.assertRaises(GameError):validate_state(corrupted)
        solve(j)
        validate_state(j.state)

    def test_days_balance_and_progress(self):
        variants=set();steps=set();bonuses=[]
        for day in range(1,61):
            j=Journey('lawyer',slot=1,day=day)
            variants.add(j.task['needs']['variant'])
            steps.add(solve(j));bonuses.append(j.c['ext']['data']['earned'])
            self.assertEqual(j.c['ext']['data']['active_days'],1)
            self.assertEqual(j.c['ext']['data']['qualified'],1)
        self.assertEqual(steps,{5,6,7,8})
        self.assertGreaterEqual(len(variants),12)
        self.assertTrue(all(4<=x<=10 for x in bonuses))
        d=lw.initial();c={'day':60,'ext':{'data':d}}
        for day in range(1,61):
            c['day']=day;lw.on_start({},c);lw.on_close({},c)
        self.assertEqual(d['active_days'],0)
        self.assertFalse(lw.public_data(c)['milestone']['earned'])

    def test_task_determinism(self):
        for day in (1,4,10,20,40,60):
            a=lw.make_task(day,2,3);b=lw.make_task(day,2,90)
            for field in lw.FIXED:self.assertEqual(a[field],b[field])
            lw.validate_task(json.loads(json.dumps(a)),a)

    def test_milestone_needs_final_tier_and_active_days(self):
        j=Journey('lawyer',slot=1,day=39)
        d=j.c['ext']['data'];d.update(jobs=120,qualified=120,active_days=30,last_active_day=38)
        solve(j)
        self.assertFalse(lw.public_data(j.c)['milestone']['earned'])
        j=Journey('lawyer',slot=1,day=40)
        d=j.c['ext']['data'];d.update(jobs=119,qualified=119,active_days=29,last_active_day=39)
        solve(j)
        self.assertTrue(lw.public_data(j.c)['milestone']['earned'])

    def test_wrong_amount_retries_reduce_pay_only_once(self):
        clean=Journey('lawyer',slot=1);solve(clean)
        j=Journey('lawyer',slot=1);j.act('ask')
        for _ in range(3):step(j)
        for _ in range(3):step(j,0)
        self.assertEqual(j.task['mistakes'],1)
        self.assertEqual(j.task['at'],3)
        j.state=json.loads(json.dumps(j.state));validate_state(j.state)
        solve(j)
        self.assertEqual(clean.c['ext']['data']['earned']-j.c['ext']['data']['earned'],1)

    def test_each_step_save_and_invalid_scalar(self):
        j=Journey('lawyer',slot=1,day=40);j.act('ask')
        tid=j.task['id']
        while j.get(tid)['status']!='completed':
            t=j.task;st=t['needs']['steps'][t['at']]
            before=copy.deepcopy(j.state)
            for bad in (None,True,{},['fake']):
                with self.assertRaises(GameError):j.act('lw_submit',step=st['id'],value=bad)
                self.assertEqual(before,j.state)
            step(j)
            j.state=json.loads(json.dumps(j.state));validate_state(j.state)

    def test_cannot_claim_completed_without_finishing(self):
        j=Journey('lawyer',slot=1)
        j.task['status']='completed'
        with self.assertRaises(GameError):validate_state(j.state)

    def test_two_cases_one_day_counts_one_active_day(self):
        j=Journey('lawyer');solve(j)
        solve(j)
        self.assertEqual(j.c['ext']['data']['jobs'],2)
        self.assertEqual(j.c['ext']['data']['qualified'],2)
        self.assertEqual(j.c['ext']['data']['active_days'],1)
        self.assertFalse(any(row.get('category')=='salary' for row in j.c['ops']['finance']['ledger']))

