import copy
import importlib.util
import unittest
from unittest.mock import patch

from game import operations as ops, workplace_business as wb
from game.engine import GameError, new_state


class StaffLife(unittest.TestCase):
    def double_event(self, api, s, c, e):
        c['money']+=1000000;ops.record_money(c,1000000,'Vốn thử nghiệm','test-capital','other_income')
        api.tick_career(s,c,'accounting')
        state=c['ops']['staff_life']; state['raises'][e['id']]=e['wage']
        for _ in range(120):
            c['ops']['work_ticks']=state['next'];api.tick_career(s,c,'accounting')
            p=state['pending']
            if p['kind']=='raise_double':return p
            api.choose_career(s,c,'accounting',dict(event=p['id'],choice='retain' if p['kind']=='quit' else 'decline',confirm=True))
        self.fail('Rare double-effective-wage event missing')

    def test_double_effective_wage_requires_approval_and_roundtrips_next_payroll(self):
        api=self.api();s,c,e=self.sample();p=self.double_event(api,s,c,e)
        old=api.wage(c['ops'],e);money=c['money'];snapshot=copy.deepcopy(c)
        self.assertFalse(api.tick_career(s,c,'accounting'));self.assertEqual(c,snapshot)
        self.assertIn(str(old*2),api.public(c)['pending']['choices'][0]['effect'])
        payload=dict(event=p['id'],choice='approve',confirm=True)
        with self.assertRaises(GameError):api.choose_career(s,c,'accounting',dict(payload,confirm=False))
        api.choose_career(s,c,'accounting',payload)
        self.assertEqual(api.wage(c['ops'],e),old*2);self.assertEqual(c['money'],money)
        self.assertIn(str(old*2),api.public(c)['recent'][-1]['text'])
        with self.assertRaises(GameError):api.choose_career(s,c,'accounting',payload)
        ops._attendance(c,e);ops.validate(c,'accounting')
        self.assertEqual(c['ops']['attendance'][str(c['day'])][e['id']]['raise_amount'],old*2-e['wage'])

    def test_double_wage_capped_at10000_and_never_selected_for_humans(self):
        api=self.api();s,c,e=self.sample();p=self.double_event(api,s,c,e)
        state=c['ops']['staff_life'];state['raises'][e['id']]=6000-e['wage']
        p.update(wage=6000,raise_by=4000)
        api.validate(c['ops'],'accounting')
        api.choose_career(s,c,'accounting',dict(event=p['id'],choice='approve',confirm=True))
        self.assertEqual(api.wage(c['ops'],e),10000);ops.validate(c,'accounting')
        for _ in range(40):
            c['ops']['work_ticks']=state['next'];api.tick_career(s,c,'accounting');p=state['pending']
            self.assertNotEqual(p['kind'],'raise_double')
            api.choose_career(s,c,'accounting',dict(event=p['id'],choice='retain' if p['kind']=='quit' else 'decline',confirm=True))
        human=dict(id='q-human',staff=[],fund=100,till=0,business=dict(sold=10000),shift={'employee':'human'})
        self.assertFalse(api.tick_quay(s,human));self.assertNotIn('staff_life',human)

    def test_legacy_raise_after_double_never_reduces_effective_wage(self):
        api=self.api();s,c,e=self.sample();p=self.event(api,s,c,'raise')
        state=c['ops']['staff_life'];state['raises'][e['id']]=e['wage']*3
        p['wage']=api.wage(c['ops'],e)
        self.assertIn(str(p['wage']),api.public(c)['pending']['choices'][0]['effect'])
        snapshot=copy.deepcopy(c)
        with self.assertRaises(GameError):api.choose_career(s,c,'accounting',dict(event=p['id'],choice='approve',confirm=True))
        self.assertEqual(c,snapshot)
        api.choose_career(s,c,'accounting',dict(event=p['id'],choice='decline',confirm=True))
        self.assertEqual(api.wage(c['ops'],e),e['wage']*4)

    def test_manual_quay_wage_change_updates_pending_double_quote_and_approval(self):
        api=self.api()
        from tests.test_quay import act,opened,ST
        with patch('time.time',return_value=2000000000):s=opened('xe')
        st=ST(s)
        e=st['staff'][0];api.tick_quay(s,st)
        state=st['staff_life'];state.update(seq=1,pending=dict(id='staff-q1-1',kind='raise_double',employee=e['id'],name=e['name'],wage=e['wage']*2,raise_by=e['wage']*2))
        state['raises'][e['id']]=e['wage']
        new=e['wage']+1
        with patch('time.time',return_value=2000000000):
            s,_=act(s,'jr_quay_wage',stall=st['id'],staff=e['id'],wage=new)
        st=s['journey']['quay']['stalls'][0];e=st['staff'][0]
        p=api.public(st,True)['pending']
        self.assertEqual(p['wage'],new);self.assertIn(f'Lương mới {new*2} xu',p['choices'][0]['effect'])
        api.choose_quay(s,st,dict(event=p['id'],choice='approve',confirm=True))
        self.assertEqual(api.wage(st,e),new*2)

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('game.staff_life'), 'NPC staff life module missing')
        from game import staff_life
        return staff_life

    def sample(self):
        s=new_state();c=s['careers']['accounting'];c.update(started=True,open=True)
        with patch('time.time',return_value=2000000000):
            ops.action(s,c,'accounting','ops_hire',dict(candidate='accounting-staff-1',confirm=True))
            wb.settle(s)
        return s,c,c['ops']['staff'][0]

    def event(self,api,s,c,kind):
        api.tick_career(s,c,'accounting')
        for _ in range(4):
            c['ops']['work_ticks']=c['ops']['staff_life']['next']
            api.tick_career(s,c,'accounting')
            p=c['ops']['staff_life']['pending']
            if p['kind']==kind:return p
            api.choose_career(s,c,'accounting',dict(event=p['id'],choice='decline' if p['kind']!='quit' else 'retain',confirm=True))
        self.fail('Event cycle missing '+kind)

    def test_lazy_legacy_tick_does_not_backfill_or_charge_and_reload_stable(self):
        api=self.api();s,c,e=self.sample();c['ops'].pop('staff_life',None)
        c['ops']['work_ticks']=100000;before=c['money']
        self.assertTrue(api.tick_career(s,c,'accounting'))
        self.assertIsNone(api.public(c)['pending'])
        c['ops']['work_ticks']+=api.GAP
        self.assertTrue(api.tick_career(s,c,'accounting'))
        snap=copy.deepcopy(c);self.assertFalse(api.tick_career(s,c,'accounting'))
        self.assertEqual(c,snap);self.assertEqual(c['money'],before)
        ops.validate(c,'accounting')

    def test_raise_changes_future_paid_orders_and_does_not_mutate_candidate(self):
        api=self.api();s,c,e=self.sample();p=self.event(api,s,c,'raise')
        base=e['wage'];money=c['money']
        result=ops.action(s,c,'accounting','ops_staff_event',dict(event=p['id'],choice='approve',confirm=True))
        self.assertGreater(api.wage(c['ops'],e),base);self.assertEqual(e['wage'],base)
        self.assertEqual(c['money'],money);self.assertIn('message',result)
        wb.refresh(c,'accounting',2000000100)
        wb.settle(s,min(x['at'] for x in c['ops']['business']['pending'].values()))
        self.assertEqual(c['ops']['business']['recent'][-1]['wage'],(api.wage(c['ops'],e)+3)//4)
        ops.validate(c,'accounting')

    def test_wedding_cost_cannot_overdraw_and_repeat_cannot_charge_twice(self):
        api=self.api();s,c,e=self.sample();p=self.event(api,s,c,'wedding')
        payload=dict(event=p['id'],choice='gift',confirm=True)
        old=c['money'];c['money']=0
        with self.assertRaises(GameError):api.choose_career(s,c,'accounting',payload)
        self.assertEqual(c['money'],0);self.assertEqual(c['ops']['staff_life']['pending']['id'],p['id'])
        c['money']=old;api.choose_career(s,c,'accounting',payload);after=c['money']
        self.assertLess(after,old)
        with self.assertRaises(GameError):api.choose_career(s,c,'accounting',payload)
        self.assertEqual(after,c['money'])
        self.assertEqual(c['money'],c['ops']['finance']['opening_balance']+sum(x['amount'] for x in c['ops']['finance']['ledger']))

    def test_quit_stops_future_orders_and_keeps_earned_wages(self):
        api=self.api();s,c,e=self.sample();p=self.event(api,s,c,'quit')
        ops._attendance(c,e)
        api.choose_career(s,c,'accounting',dict(event=p['id'],choice='release',confirm=True))
        self.assertEqual(e['status'],'former');self.assertFalse(e['on_shift'])
        self.assertNotIn(e['id'],c['ops']['business']['pending'])
        self.assertTrue(any(b['source']==e['id'] for b in c['ops']['finance']['bills']))
        wb.settle(s,2000009999);self.assertEqual(c['ops']['business']['served'],0)
        ops.validate(c,'accounting')

    def test_quit_waits_for_accepted_visitor(self):
        api=self.api();s,c,e=self.sample();p=self.event(api,s,c,'quit')
        c['player_service_jobs']=[dict(staff=e['id'],status='queued')]
        with self.assertRaises(GameError):api.choose_career(s,c,'accounting',dict(event=p['id'],choice='release',confirm=True))
        self.assertEqual(e['status'],'hired')

    def test_deterministic_quality_has_bad_and_good_reviews_and_staff_attribution(self):
        api=self.api();s,c,e=self.sample();bad=dict(e,precision=15,morale=10,jobs=0);good=dict(e,precision=99,morale=100,jobs=3000)
        poor=[api.quality(bad,i,'accounting') for i in range(80)]
        great=[api.quality(good,i,'accounting') for i in range(80)]
        self.assertTrue(all(x['stars']<=2 for x in poor));self.assertTrue(all(x['stars']>=4 for x in great))
        self.assertTrue(all(x['employee']==e['id'] and x['name']==e['name'] and x['text'] for x in poor+great))
        self.assertEqual(poor,[api.quality(bad,i,'accounting') for i in range(80)])
        e.update(precision=15,morale=10)
        wb.refresh(c,'accounting',2000000000)
        wb.settle(s,min(x['at'] for x in c['ops']['business']['pending'].values()))
        review=wb.public(c)['recent'][-1]
        self.assertLessEqual(review['stars'],2);self.assertTrue(review['review'])

    def test_quay_events_only_npcs_and_block_last_staff_quit_with_visitors(self):
        api=self.api();s=new_state();st=dict(id='q1',staff=[],fund=100,till=0,business=dict(sold=0))
        self.assertFalse(api.tick_quay(s,st));self.assertNotIn('staff_life',st)
        st['staff']=[dict(id='npc1',name='An',wage=15,mo=60,g=False,d=0)]
        api.tick_quay(s,st)
        for _ in range(4):
            st['business']['sold']=st['staff_life']['next'];api.tick_quay(s,st)
            p=st['staff_life']['pending']
            if p['kind']=='quit':break
            api.choose_quay(s,st,dict(stall='q1',event=p['id'],choice='decline',confirm=True))
        st['business']['visitor_orders']=[dict(status='queued')]
        with self.assertRaises(GameError):api.choose_quay(s,st,dict(event=p['id'],choice='release',confirm=True))
        self.assertEqual(len(st['staff']),1)

    def test_validate_rejects_forged_event_and_unbounded_raise(self):
        api=self.api();s,c,e=self.sample();self.event(api,s,c,'raise')
        bad=copy.deepcopy(c['ops']);bad['staff_life']['pending']['employee']='human-player'
        with self.assertRaises(GameError):api.validate(bad,'accounting')
        bad=copy.deepcopy(c['ops']);bad['staff_life']['raises'][e['id']]=10**12
        with self.assertRaises(GameError):api.validate(bad,'accounting')

    def test_raise_keeps_existing_shift_pay_and_applies_to_next_shift(self):
        api=self.api();s,c,e=self.sample()
        # An attendance row from an older release has no supplement field.
        c['ops']['attendance'][str(c['day'])]={e['id']:dict(name=e['name'],wage=e['wage'],role=e['role'])}
        p=self.event(api,s,c,'raise')
        api.choose_career(s,c,'accounting',dict(event=p['id'],choice='approve',confirm=True))
        ops._attendance(c,e);ops._payroll(c,c['day'])
        self.assertEqual(c['ops']['finance']['bills'][-1]['amount'],e['wage'])
        c['day']+=1;ops._attendance(c,e);ops._payroll(c,c['day'])
        self.assertEqual(c['ops']['finance']['bills'][-1]['amount'],api.wage(c['ops'],e))

    def test_customer_review_projection_has_shared_ui_text_and_aggregate(self):
        api=self.api();s,c,e=self.sample()
        wb.settle(s,min(x['at'] for x in c['ops']['business']['pending'].values()))
        out=wb.public(c)
        self.assertEqual(out['recent'][-1]['text'],api.REVIEWS[out['recent'][-1]['stars']])
        self.assertEqual(out['review_count'],len(out['recent']))
        self.assertEqual(out['rating_average'],out['recent'][-1]['stars'])

    def test_quay_wedding_cost_is_accounted_once_without_touching_human_shift(self):
        api=self.api()
        from tests.test_quay_business import fixture
        s,st=fixture();st['staff']=[dict(id='npc1',name='An',wage=15,ask=15,mo=60,g=False,d=0)]
        from game import quay_business as qb
        qb.initialize(s,st,now=2000000000)
        st['business']['income_tax']=dict(loss=0)
        s['journey']['quay']['shift']={'human':'unchanged'}
        api.tick_quay(s,st)
        for _ in range(4):
            st['business']['sold']=st['staff_life']['next'];api.tick_quay(s,st);p=st['staff_life']['pending']
            if p['kind']=='wedding':break
            api.choose_quay(s,st,dict(event=p['id'],choice='decline' if p['kind']=='raise' else 'retain',confirm=True))
        before=st['fund']+st['till'];loss=st['business']['expenses']['loss']
        cost=next(row['cost'] for row in api.public(st,quay=True)['pending']['choices'] if row['id']=='gift')
        payload=dict(event=p['id'],choice='gift',confirm=True)
        api.choose_quay(s,st,payload)
        self.assertEqual(st['fund']+st['till'],before-cost)
        self.assertEqual(st['business']['expenses']['loss'],loss+cost)
        self.assertGreaterEqual(st['business']['income_tax']['loss'],cost)
        self.assertEqual(s['journey']['quay']['shift'],{'human':'unchanged'})
        with self.assertRaises(GameError):api.choose_quay(s,st,payload)
        self.assertEqual(st['fund']+st['till'],before-cost)

    def test_dismiss_clears_pending_and_rehire_does_not_restore_old_raise(self):
        api=self.api();s,c,e=self.sample();p=self.event(api,s,c,'raise')
        api.choose_career(s,c,'accounting',dict(event=p['id'],choice='approve',confirm=True))
        self.event(api,s,c,'wedding')
        ops.action(s,c,'accounting','ops_dismiss',dict(employee=e['id'],confirm=True))
        self.assertIsNone(api.public(c)['pending'])
        self.assertNotIn(e['id'],c['ops']['staff_life']['raises'])
