import copy
import json
import unittest

from game.careers import PLUGINS
from game.engine import GameError, validate_state, public_state
from tests.helpers import Journey


def solve(j, wrong=False):
    tid=j.task['id'];j.act('ask',task=tid);key=j.get(tid)['_key']
    for field in ('layout','palette','medium'):
        value=key[field]
        if wrong and field=='palette':value=next(k for k in PLUGINS['art_studio'].OPTIONS[field] if k!=value)
        j.act('art_plan',task=tid,field=field,value=value)
    j.act('art_begin',task=tid)
    for layer in key['layers']:j.act('art_layer',task=tid,layer=layer)
    j.act('art_proof',task=tid,checks=['brief','surface','signature'])
    result=j.act('art_deliver',task=tid,recipient=j.get(tid)['needs']['recipient'])
    return tid,result


class ArtStudio(unittest.TestCase):
    def test_registered(self):
        self.assertIn('art_studio',PLUGINS)

    def test_correct_and_incorrect_jobs_balance_and_one_payment(self):
        for day in (1,4,10,20,40,45,60):
            for wrong in (False,True):
                j=Journey('art_studio',day=day,slot=1)
                tid,result=solve(j,wrong)
                self.assertEqual(j.get(tid)['status'],'completed')
                self.assertEqual(result['cost'],j.get(tid)['needs']['cost'])
                self.assertEqual(result['net'],result['gross']-result['cost'])
                self.assertEqual(j.c['ext']['data']['stats']['good'],int(not wrong))
                before=copy.deepcopy(j.state)
                with self.assertRaises(GameError):j.act('art_deliver',task=tid,recipient='anything')
                self.assertEqual(j.state,before)
                validate_state(json.loads(json.dumps(j.state)))

    def test_reload_between_layers_and_hidden_answers(self):
        j=Journey('art_studio',day=20,slot=2);tid=j.task['id']
        self.assertIsNone(public_state(j.state)['careers']['art_studio']['tasks'][0]['needs'])
        j.act('ask',task=tid)
        for f in ('layout','palette','medium'):j.act('art_plan',task=tid,field=f,value=j.get(tid)['_key'][f])
        j.act('art_begin',task=tid);j.act('art_layer',task=tid,layer=j.get(tid)['_key']['layers'][0])
        j.state=json.loads(json.dumps(j.state));validate_state(j.state)
        view=public_state(j.state)['careers']['art_studio']['tasks'][0]
        self.assertNotIn('_key',view)
        for layer in j.get(tid)['_key']['layers'][1:]:j.act('art_layer',task=tid,layer=layer)
        j.act('art_proof',task=tid,checks=['brief','surface','signature'])
        j.act('art_deliver',task=tid,recipient=j.get(tid)['needs']['recipient'])

    def test_invalid_actions_and_forged_facts(self):
        j=Journey('art_studio',slot=0);tid=j.task['id']
        for action,p in [('art_begin',{}),('art_layer',{'layer':'background'}),('art_deliver',{'recipient':'x'}),('art_plan',{'field':'layout','value':'x'})]:
            before=copy.deepcopy(j.state)
            with self.assertRaises(GameError):j.act(action,task=tid,**p)
            self.assertEqual(before,j.state)
        forged=copy.deepcopy(j.state);forged['careers']['art_studio']['tasks'][0]['needs']['gross']=99999
        with self.assertRaises(GameError):validate_state(forged)

    def test_forged_progress_and_receipt_rejected(self):
        j=Journey('art_studio',slot=0);tid,_=solve(j)
        for change in (lambda t:t.update(status='working'),lambda t:t.update(stage='paint',result=None,checked=[]),lambda t:t['result'].update(gross=t['result']['gross']-1,net=t['result']['net']-1)):
            forged=copy.deepcopy(j.state);change(forged['careers']['art_studio']['tasks'][0])
            with self.assertRaises(GameError):validate_state(forged)

    def test_generation_progression_and_no_empty_mastery(self):
        m=PLUGINS['art_studio'];variants=set()
        for day in range(1,61):
            for slot in range(12):
                t=m.make_task(day,slot,1);self.assertEqual(t,json.loads(json.dumps(t)));m.validate_task(t,t)
                self.assertLessEqual(m.COMMISSIONS[t['needs']['commission']]['day'],day);variants.add(t['needs']['commission'])
        self.assertEqual(variants,set(m.COMMISSIONS))
        j=Journey('art_studio',day=60,slot=0);d=j.c['ext']['data']
        m.on_close(j.state,j.c);m.on_close(j.state,j.c)
        self.assertEqual(d['stats']['active_days'],0)
        self.assertFalse(m.public_data(j.c)['milestones'][-1]['done'])

    def test_delivery_from_empty_fund_receives_gross_before_materials(self):
        j=Journey('art_studio',slot=0)
        j.c['money']=0;j.c['day_start_money']=0
        j.c['ops']['finance']['opening_balance']=0
        validate_state(j.state)
        tid,result=solve(j)
        rows=[r for r in j.c['ops']['finance']['ledger'] if r.get('ref')==tid]
        self.assertEqual([r['amount'] for r in rows],[result['gross'],-result['cost']])
        self.assertEqual(j.c['money'],result['net'])
        before=copy.deepcopy(j.state)
        with self.assertRaises(GameError):j.act('art_deliver',task=tid,recipient=j.get(tid)['needs']['recipient'])
        self.assertEqual(before,j.state)

    def test_save_cannot_erase_plan_or_layer_mistakes(self):
        m=PLUGINS['art_studio']
        for bad_plan in (False,True):
            j=Journey('art_studio',slot=1);tid=j.task['id'];j.act('ask',task=tid)
            key=j.task['_key']
            for f in ('layout','palette','medium'):
                v=next(k for k in m.OPTIONS[f] if k!=key[f]) if bad_plan and f=='palette' else key[f]
                j.act('art_plan',task=tid,field=f,value=v)
            j.act('art_begin',task=tid)
            if not bad_plan:j.act('art_layer',task=tid,layer=key['layers'][1])
            self.assertEqual(j.task['mistakes'],1)
            forged=copy.deepcopy(j.state);forged['careers']['art_studio']['tasks'][0]['mistakes']=0
            with self.assertRaises(GameError):validate_state(forged)
            # Abandonment keeps the incomplete stage and plan, and must remain loadable.
            j.task['status']='cancelled';j.c['active_task']=None
            validate_state(json.loads(json.dumps(j.state)))

    def test_exhibition_requires_clean_work_from_final_tier(self):
        m=PLUGINS['art_studio'];j=Journey('art_studio',day=44,slot=0)
        stats=j.c['ext']['data']['stats'];stats.update(jobs=140,good=140,active_days=35,last_good_day=44)
        j.c['day']=45
        self.assertFalse(m.public_data(j.c)['milestones'][-1]['done'])
        # Advancing calendar alone is insufficient, even with all earlier volume met.
        j.c['day']=60
        self.assertFalse(m.public_data(j.c)['milestones'][-1]['done'])
        stats['last_good_day']=45
        self.assertTrue(m.public_data(j.c)['milestones'][-1]['done'])

    def test_sixty_days_keep_real_progress_through_shift_and_save_boundaries(self):
        m=PLUGINS['art_studio'];j=Journey('art_studio')
        jobs=net=0;earned_on=None;seen=set()
        for day in range(1,61):
            self.assertEqual(j.c['day'],day)
            for _ in range(m.daily_task_count(day)):
                seen.add(j.task['needs']['commission'])
                _,result=solve(j)
                jobs+=1;net+=result['net']
            j.act('end_day',carry_event=True)
            d=j.c['ext']['data']
            self.assertEqual(d['stats']['jobs'],jobs)
            self.assertEqual(d['stats']['good'],jobs)
            self.assertEqual(d['stats']['net'],net)
            self.assertEqual(d['stats']['active_days'],day)
            self.assertEqual(d['stats']['last_good_day'],day)
            if m.public_data(j.c)['milestones'][-1]['done'] and earned_on is None:earned_on=day
            j.state=json.loads(json.dumps(j.state));validate_state(j.state)
            if day<60:j.act('start_day')
        self.assertEqual(jobs,231)
        self.assertEqual(earned_on,45)
        self.assertTrue({'opening','exhibition'}<=seen)
        self.assertEqual(len(j.c['ext']['data']['portfolio']),12)

    def test_carried_old_commission_cannot_unlock_a_new_tier(self):
        m=PLUGINS['art_studio'];j=Journey('art_studio',day=44,slot=0)
        d=j.c['ext']['data'];d['stats'].update(jobs=140,good=140,active_days=35,last_good_day=44)
        j.c['day']=45
        solve(j)
        self.assertEqual(j.c['ext']['data']['stats']['last_good_day'],44)
        self.assertFalse(m.public_data(j.c)['milestones'][-1]['done'])


if __name__=='__main__':unittest.main()
