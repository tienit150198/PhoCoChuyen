"""v0.2 staff, rent/payroll, fictional tax and security regression tests.

Fixtures may fix the private random roll to cover both authored outcomes. There
is no public endpoint to choose a real-case outcome or grant money in the game.
"""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from game import operations as ops
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state, available, money
from game.storage import Store, Conflict
from tests.helpers import Journey


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.j=Journey()
        self.j.state['settings']['securityEvents']=False
    @property
    def c(self):return self.j.c
    @property
    def o(self):return self.c['ops']
    def act(self,name,**p):return self.j.act('ops_'+name,**p)
    def hire(self,n=1,career=None):
        cid=career or self.j.career;sid=f'{cid}-staff-{n}'
        self.act('hire',candidate=sid,confirm=True);return sid
    def staff(self,sid):return next(e for e in self.o['staff'] if e['id']==sid)
    def advance(self,n=1):
        for _ in range(n):self.j.act('advance')
    def case(self):return next(v for v in self.o['security']['cases'] if v['id']==self.o['security']['active'])
    def spawn(self,kind='theft',practice=False,roll=0):
        v=ops.spawn_case(self.j.state,self.c,self.j.career,kind,practice);v['_roll']=roll;validate_state(self.j.state);return v['id']
    def investigate(self):
        for ev in list(self.case()['evidence']):self.act('case_read',evidence=ev['id'])
        self.act('case_conclude',finding=self.case()['_truth'])
    def police_result(self):
        self.investigate();self.act('report',confirm=True);self.advance(3)
        self.assertEqual(self.case()['status'],'result')
    def finish_case(self):
        self.act('recover',confirm=True);self.act('reward',confirm=True);self.act('case_close')
    def close(self):self.j.act('end_day',carry_event=True)
    def assert_valid(self):
        validate_state(self.j.state)
        for c in self.j.state['careers'].values():
            self.assertEqual(c['money'],c['ops']['finance']['opening_balance']+sum(x['amount'] for x in c['ops']['finance']['ledger']))
    def no_effect(self,action,**payload):
        before=copy.deepcopy(self.j.state)
        with self.assertRaises(GameError):self.act(action,**payload)
        self.assertEqual(before,self.j.state)

    def test_hire_confirmed_once_and_career_specific(self):
        self.no_effect('hire',candidate='mother_baby-staff-1')
        self.no_effect('hire',candidate='pharmacy-staff-1',confirm=True)
        sid=self.hire();self.assertEqual(self.c['money'],290)
        self.no_effect('hire',candidate=sid,confirm=True)
        self.assertEqual(len(self.o['staff']),1);self.assert_valid()

    def test_room_capacity_and_open_move_guard(self):
        self.hire();self.no_effect('hire',candidate='mother_baby-staff-2',confirm=True)
        self.no_effect('move_property',tier='sunny',confirm=True)
        self.close();self.act('move_property',tier='sunny',confirm=True);self.hire(2)
        self.assertEqual(len(self.o['staff']),2)
        self.no_effect('move_property',tier='cozy',confirm=True)
        self.assert_valid()

    def test_employee_moves_work_without_delivering_or_creating_money(self):
        sid=self.hire();self.j.act('ask');before=self.c['money'];self.advance(4)
        t=self.j.task
        self.assertEqual(t['basket'],{t['needs']['product']:1})
        self.assertGreater(self.staff(sid)['jobs'],0)
        self.assertNotEqual(t['status'],'completed');self.assertEqual(self.c['money'],before)
        self.assertTrue(self.o['attendance'][str(self.c['day'])]);self.assert_valid()

    def test_wrong_role_rejected(self):
        sid=self.hire();self.no_effect('assign',employee=sid,role='reconcile')
        self.act('assign',employee=sid,role='packing');self.assertEqual(self.staff(sid)['role'],'packing')

    def test_packer_uses_confirmed_need_no_automatic_pay(self):
        self.j=Journey(slot=0);sid=self.hire(2);self.j.act('ask')
        t=self.j.task
        for _ in range(t['needs']['qty']):self.j.act('shop_pick',item=t['needs']['product'])
        before=self.c['money'];self.advance(4)
        self.assertEqual(self.j.task['pack']['paper'],self.j.task['needs']['paper'])
        self.assertFalse(self.j.task['checked']);self.assertEqual(before,self.c['money']);self.assert_valid()

    def test_cashier_checks_but_never_delivers(self):
        sid=self.hire(4);self.j.act('ask');t=self.j.task
        for _ in range(t['needs']['qty']):self.j.act('shop_pick',item=t['needs']['product'])
        if t['needs']['gift']:self.j.act('shop_pack',paper=t['needs']['paper'],ribbon='gold',card='Vui nhé!')
        before=self.c['money'];self.advance(4)
        self.assertTrue(self.j.task['checked']);self.assertNotEqual(self.j.task['status'],'completed');self.assertEqual(before,self.c['money'])

    def test_stock_helper_receives_paid_actual_quantity_once(self):
        self.hire(3);item=next(iter(self.c['stock']));before=self.c['stock'][item]
        self.j.act('order_stock',item=item,qty=2,supplier='express')  # 30–60 minutes on the shop clock
        sh=self.c['shipments'][-1];sh['actual']=1
        self.advance(5);self.assertEqual(self.c['shipments'][-1]['status'],'received')
        self.assertEqual(self.c['stock'][item],before+1)
        self.advance(5);self.assertEqual(self.c['stock'][item],before+1);self.assert_valid()

    def test_pharmacy_helper_only_reads_lot(self):
        self.j=Journey('pharmacy',slot=0);self.hire();self.j.act('ask');before=copy.deepcopy(self.c['stock']);self.advance(4)
        self.assertGreater(len(self.j.task['inspected']),0);self.assertFalse(self.j.task['basket']);self.assertEqual(before,self.c['stock']);self.assert_valid()

    def test_accounting_helper_only_exposes_original(self):
        self.j=Journey('accounting',slot=0);self.hire();before=copy.deepcopy(self.j.task['docs']);self.advance(4)
        self.assertTrue(self.j.task['inspected']);self.assertEqual(before,self.j.task['docs']);self.assertNotEqual(self.j.task['status'],'completed');self.assert_valid()

    def test_care_helper_requires_identity_and_never_closes(self):
        self.j=Journey('customer_care',slot=0);self.hire();self.advance(4)
        self.assertFalse(self.j.task['inspected']);self.j.act('cs_identity');self.advance(4)
        self.assertTrue(self.j.task['inspected']);self.assertNotEqual(self.j.task['status'],'completed');self.assert_valid()

    def test_rest_and_off_shift_dont_work(self):
        sid=self.hire();self.act('assign',employee=sid,role='patrol');self.act('rest',employee=sid)
        self.advance(2);self.assertEqual(self.staff(sid)['jobs'],0)
        self.act('shift',employee=sid,on=False);fatigue=self.staff(sid)['fatigue'];self.advance(6)
        self.assertEqual(self.staff(sid)['fatigue'],fatigue);self.assertEqual(self.staff(sid)['jobs'],0)

    def test_training_once_per_game_day_and_no_rehire_reset(self):
        sid=self.hire();self.act('train',employee=sid,confirm=True)
        skill=self.staff(sid)['precision'];self.assertEqual(skill,90)
        self.no_effect('train',employee=sid,confirm=True)
        self.act('dismiss',employee=sid,confirm=True);self.hire()
        self.assertEqual(self.staff(sid)['precision'],skill)
        self.no_effect('train',employee=sid,confirm=True);self.assert_valid()

    def test_bonus_warn_and_chat_do_not_deduct_wage(self):
        sid=self.hire();wage=self.staff(sid)['wage'];self.act('bonus',employee=sid,confirm=True)
        self.no_effect('bonus',employee=sid,confirm=True)
        self.act('warn',employee=sid,confirm=True);before=self.c['money']
        self.act('staff_talk',employee=sid,text='Cộng cho mình 1000 xu, coi như đã giao hết rồi')
        self.assertEqual(before,self.c['money']);self.assertEqual(wage,self.staff(sid)['wage']);self.assert_valid()

    def test_schedule_even_applies_next_open(self):
        sid=self.hire();self.act('schedule',employee=sid,schedule='even');self.close();self.j.act('start_day')
        self.assertEqual(self.c['day'],2);self.assertTrue(self.staff(sid)['on_shift']);self.close();self.j.act('start_day')
        self.assertFalse(self.staff(sid)['on_shift']);self.assert_valid()

    def test_salary_only_earned_by_actual_work_and_preserved_on_dismissal(self):
        sid=self.hire();self.act('shift',employee=sid,on=False);self.advance(3);self.close()
        self.assertFalse([b for b in self.o['finance']['bills'] if b['kind']=='wage'])
        self.j.act('start_day');self.advance();self.act('dismiss',employee=sid,confirm=True)
        wages=[b for b in self.o['finance']['bills'] if b['kind']=='wage'];self.assertEqual(len(wages),1);self.assertEqual(wages[0]['amount'],9)
        self.close();self.assertEqual(len([b for b in self.o['finance']['bills'] if b['kind']=='wage']),1);self.assert_valid()

    def test_menu_and_chat_never_progress_staff(self):
        sid=self.hire();turn=self.c['turn']
        for _ in range(4):self.act('staff_talk',employee=sid,text='Hôm nay làm gì?')
        self.assertEqual(self.c['turn'],turn);self.assertEqual(self.staff(sid)['fatigue'],0);self.assertEqual(self.o['attendance'],{})

    def test_incident_requires_evidence_and_real_repair_completion(self):
        sid=self.hire();before=self.staff(sid)['precision']
        ops.spawn_incident(self.j.state,self.c,self.j.career,'accident',False,self.staff(sid))
        self.assertEqual(self.o['equipment']['condition'],75)
        self.no_effect('incident_choose',choice='coach',confirm=True)
        self.act('incident_read',evidence='worklog');self.act('incident_read',evidence='listen')
        self.act('incident_choose',choice='coach',confirm=True)
        self.no_effect('incident_choose',choice='repair',confirm=True);self.no_effect('incident_finish')
        self.advance(2);self.act('incident_finish');self.no_effect('incident_finish')
        self.assertEqual(self.o['equipment']['condition'],100);self.assertEqual(self.staff(sid)['precision'],before+4)
        repairs=[b for b in self.o['finance']['bills'] if b['kind']=='repair'];self.assertEqual([b['amount'] for b in repairs],[8]);self.assert_valid()

    def test_damage_admission_is_evidence_and_warning_stops_shift(self):
        sid=self.hire();ops.spawn_incident(self.j.state,self.c,self.j.career,'damage',False,self.staff(sid))
        public=public_state(self.j.state)['careers']['mother_baby']['ops']['incident'];self.assertIsNone(public['evidence'][1]['text'])
        self.act('incident_read',evidence='worklog');self.act('incident_read',evidence='listen')
        self.act('incident_choose',choice='warning',confirm=True);self.advance(2);self.act('incident_finish')
        self.assertFalse(self.staff(sid)['on_shift']);self.assertEqual(self.staff(sid)['warnings'],1);self.assertEqual(self.staff(sid)['wage'],9);self.assert_valid()

    def test_live_incident_cannot_be_discarded_or_employee_fired_before_resolution(self):
        sid=self.hire();ops.spawn_incident(self.j.state,self.c,self.j.career,employee=self.staff(sid))
        self.no_effect('incident_dismiss');self.no_effect('dismiss',employee=sid,confirm=True)

    def test_paused_employee_is_not_billed_or_tired_while_incident_open(self):
        # Player report 03/10: an employee with an open incident stood idle for days, yet was logged present
        # (wage billed for "ca thực làm"), grew tired and kept "đang nghỉ một chút rồi quay lại" notes.
        sid=self.hire();self.act('assign',employee=sid,role='patrol')
        ops.spawn_incident(self.j.state,self.c,self.j.career,'accident',False,self.staff(sid))
        self.close();self.j.act('start_day');day=self.c['day'];e=self.staff(sid);fatigue,jobs=e['fatigue'],e['jobs']
        notes=[]
        for _ in range(40):notes+=self.j.act('advance').get('effects',[])
        e=self.staff(sid)
        self.assertNotIn(sid,self.o['attendance'].get(str(day),{}))
        self.assertEqual((e['fatigue'],e['jobs']),(fatigue,jobs))
        self.assertFalse([n for n in notes if isinstance(n,str) and ('đang nghỉ một chút' in n or n.startswith(e['name']+':'))])
        summary=self.j.act('end_day',carry_event=True)['summary']['operations']
        self.assertEqual(summary['staff'],[dict(name=e['name'],jobs=0,shift=False,paused=True,bonus=0)])
        self.assertEqual((summary['wages'],summary['staff_bonus']),(0,0));self.assertFalse([b for b in self.o['finance']['bills'] if b['id']==f'wage-{day}-{sid}'])
        # Closed through the steps, the same person works (and is paid) again.
        self.j.act('start_day')
        self.act('incident_read',evidence='worklog');self.act('incident_read',evidence='listen')
        self.act('incident_choose',choice='coach',confirm=True);self.advance(2);self.act('incident_finish')
        self.advance(8);self.assertGreater(self.staff(sid)['jobs'],jobs)
        self.assertIn(sid,self.o['attendance'][str(self.c['day'])]);self.assert_valid()

    def test_today_job_count_kept_on_attendance_and_in_day_summary(self):
        sid=self.hire();self.act('assign',employee=sid,role='patrol');self.advance(12);day=str(self.c['day'])
        jobs=self.staff(sid)['jobs'];self.assertGreater(jobs,0)
        self.assertEqual(self.o['attendance'][day][sid]['jobs'],jobs);self.assert_valid()
        summary=self.j.act('end_day',carry_event=True)['summary']['operations']
        self.assertEqual(summary['staff'],[dict(name=self.staff(sid)['name'],jobs=jobs,shift=True,paused=False,bonus=min(jobs,12)*ops.job_rate(self.staff(sid)))])
        # Saves written before 1.4.31 have no per-day count; a bad one is refused.
        row=self.o['attendance'][day][sid];row.pop('jobs');validate_state(self.j.state)
        row['jobs']=-1
        with self.assertRaises(GameError):validate_state(self.j.state)

    def test_practice_incident_no_wallet_bill_skill_or_condition_effect(self):
        sid=self.hire();self.act('shift',employee=sid,on=False)
        before=(self.c['money'],copy.deepcopy(self.o['equipment']),self.staff(sid)['precision'])
        self.act('incident_demo',kind='damage');self.act('incident_read',evidence='worklog');self.act('incident_read',evidence='listen')
        self.act('incident_choose',choice='coach',confirm=True);self.advance(2);self.act('incident_finish');self.act('incident_dismiss')
        self.assertEqual(before,(self.c['money'],self.o['equipment'],self.staff(sid)['precision']));self.assertFalse(self.o['finance']['bills']);self.assert_valid()

    def test_natural_staff_error_not_more_than_once_per_day(self):
        sid=self.hire();self.act('assign',employee=sid,role='patrol');self.staff(sid)['jobs']=3;self.staff(sid)['progress']=3
        self.c['event']=None
        with patch.object(ops,'_random',return_value=0):self.advance()
        self.assertIsNotNone(self.o['incident']);self.assertFalse(self.o['incident']['practice'])
        iid=self.o['incident']['id']
        with patch.object(ops,'_random',return_value=0):self.advance(8)
        self.assertEqual(self.o['incident']['id'],iid);self.assert_valid()

    def test_natural_low_morale_damage_has_fixed_admission(self):
        sid=self.hire();self.act('assign',employee=sid,role='patrol');e=self.staff(sid);e.update(jobs=3,progress=3,morale=35)
        self.c['event']=None
        with patch.object(ops,'_random',return_value=0):self.advance()
        self.assertEqual(self.o['incident']['kind'],'damage');self.assert_valid()

    def test_seven_day_tax_and_rent_only_after_close(self):
        for n in range(7):
            money(self.j.state,self.c,100,'Hoàn thành: việc thử',category='revenue')
            money(self.j.state,self.c,10,'Quỹ thưởng',category='security_reward')
            self.close()
            if n<6:
                self.assertFalse(self.o['finance']['history']);self.j.act('start_day')
        f=self.o['finance'];h=f['history'][0]
        self.assertEqual((h['revenue'],h['tax'],h['rent']),(700,35,42))
        self.assertEqual(len([b for b in f['bills'] if b['kind']=='utility']),7)
        self.assertEqual(f['period_revenue'],0);self.assertEqual(f['period_days'],0);self.assert_valid()

    def test_rent_respects_tier_per_completed_day(self):
        self.close();self.act('move_property',tier='sunny',confirm=True)
        for n in range(6):self.j.act('start_day');self.close()
        self.assertEqual(self.o['finance']['history'][0]['rent'],6+6*11);self.assert_valid()

    def test_expense_payment_once_and_extension_once(self):
        self.close();b=self.o['finance']['bills'][0];bid=b['id'];due=b['due'];before=self.c['money']
        self.act('extend_bill',bill=bid);self.assertEqual(self.o['finance']['bills'][0]['due'],max(due,self.c['day'])+3)
        self.no_effect('extend_bill',bill=bid)
        self.no_effect('pay_bill',bill=bid);self.act('pay_bill',bill=bid,confirm=True)
        self.assertEqual(self.c['money'],before-b['amount']);self.no_effect('pay_bill',bill=bid,confirm=True);self.assert_valid()

    def test_pay_all_bills_at_once(self):
        for _ in range(3):
            self.close();self.j.act('start_day')
        self.close()
        unpaid=[b for b in self.o['finance']['bills'] if b['status']=='unpaid']
        self.assertGreater(len(unpaid),1)
        self.no_effect('pay_all')                                   # needs the confirmation like each bill
        total=sum(b['amount'] for b in unpaid);money(self.j.state,self.c,total+5-self.c['money'],'Thử',category='revenue');before=self.c['money']
        r=self.act('pay_all',confirm=True)
        self.assertEqual(self.c['money'],before-total)
        now={b['id']:b for b in self.o['finance']['bills']}   # apply_action returns a new state
        self.assertTrue(all(now[b['id']]['status']=='paid' and now[b['id']]['paid_day']==self.c['day'] for b in unpaid))
        self.assertIn(str(len(unpaid))+' khoản',r['message'])
        self.no_effect('pay_all',confirm=True)                      # nothing left
        self.assert_valid()

    def test_pay_all_skips_what_the_till_cannot_cover(self):
        for _ in range(3):
            self.close();self.j.act('start_day')
        self.close()
        unpaid=sorted((b for b in self.o['finance']['bills'] if b['status']=='unpaid'),key=lambda b:(b['due'],b['id']))
        money(self.j.state,self.c,unpaid[0]['amount']-self.c['money'],'Thử',category='revenue')
        self.act('pay_all',confirm=True)
        self.assertEqual(self.c['money'],0)                         # never below zero
        now={b['id']:b for b in self.o['finance']['bills']}
        self.assertEqual(now[unpaid[0]['id']]['status'],'paid')
        self.assertTrue(any(now[b['id']]['status']=='unpaid' for b in unpaid))
        with self.assertRaises(GameError) as e:self.act('pay_all',confirm=True)
        self.assertEqual(e.exception.code,'not_enough')
        self.assert_valid()

    def test_insufficient_funds_rollback_and_one_time_emergency_grant(self):
        money(self.j.state,self.c,-310,'Chi phí fixture',category='other_cost')
        self.no_effect('hire',candidate='mother_baby-staff-1',confirm=True)
        self.act('grant',confirm=True);self.assertEqual(self.c['money'],90)
        self.no_effect('grant',confirm=True);self.assertEqual(self.o['finance']['period_revenue'],0);self.assert_valid()

    def test_import_no_real_time_accrual(self):
        sid=self.hire();self.advance();before=copy.deepcopy(self.j.state)
        for _ in range(5):public_state(self.j.state)
        self.assertEqual(before,self.j.state);self.assertFalse(self.o['finance']['bills'])

    def test_security_evidence_hidden_and_read_idempotent(self):
        self.spawn();v=public_state(self.j.state)['careers']['mother_baby']['ops']['security']['current_case']
        self.assertNotIn('_truth',v);self.assertNotIn('_roll',v);self.assertTrue(all(e['text'] is None for e in v['evidence']))
        self.act('case_read',evidence='inventory');self.act('case_read',evidence='inventory')
        self.assertEqual(self.case()['read'],['inventory']);self.no_effect('report',confirm=True)

    def test_security_requires_truthful_conclusion(self):
        self.spawn('misplaced');before=self.c['money'];self.act('case_read',evidence='inventory');self.act('case_read',evidence='witness')
        self.no_effect('case_conclude',finding='theft');self.act('case_conclude',finding='misplaced')
        self.assertEqual(self.case()['outcome'],'not_theft');self.no_effect('reward',confirm=True);self.no_effect('report',confirm=True)
        self.act('case_close');self.assertEqual(before,self.c['money']);self.assert_valid()

    def test_unpaid_is_not_falsely_theft_and_does_not_make_revenue(self):
        before=copy.deepcopy(self.c['stock']);self.spawn('unpaid');self.investigate()
        self.assertEqual(self.case()['outcome'],'not_theft');self.assertEqual(self.o['finance']['period_revenue'],0)
        self.assertEqual(before,self.c['stock']);self.act('case_close');self.assert_valid()

    def test_live_theft_recovery_and_reward_in_separate_steps(self):
        before=copy.deepcopy(self.c['stock']);balance=self.c['money'];self.spawn();loss=copy.deepcopy(self.case()['loss'])
        self.assertEqual(self.c['stock'][loss['item']],before[loss['item']]-1)
        self.no_effect('recover',confirm=True);self.no_effect('reward',confirm=True)
        self.police_result();self.assertEqual(self.case()['outcome'],'arrested');self.assertEqual(balance,self.c['money'])
        self.act('recover',confirm=True);self.assertEqual(before,self.c['stock']);self.no_effect('recover',confirm=True)
        self.act('reward',confirm=True);self.assertEqual(balance+18,self.c['money']);self.no_effect('reward',confirm=True)
        self.assertEqual(self.o['finance']['period_revenue'],0);self.act('case_close');self.assert_valid()

    def test_police_requires_three_work_ticks_not_menu_clicks(self):
        self.spawn();self.investigate();self.act('report',confirm=True);self.no_effect('report',confirm=True)
        for _ in range(4):self.act('case_read',evidence='inventory')
        self.assertEqual(self.case()['status'],'reported');self.advance(2);self.assertEqual(self.case()['status'],'reported')
        self.advance();self.assertEqual(self.case()['status'],'result');self.assert_valid()

    def test_reward_capped_per_period(self):
        balance=self.c['money']
        for _ in range(5):
            self.spawn('snatch');self.police_result();self.finish_case()
        self.assertEqual(self.c['money'],balance+54);self.assertEqual(self.o['security']['period_rewards'],54);self.assert_valid()

    def test_snatch_never_debits_player_and_returns_npc_bag(self):
        before=copy.deepcopy(self.c['stock']);balance=self.c['money'];self.spawn('snatch')
        self.assertEqual(self.case()['loss']['kind'],'npc_property');self.police_result();self.finish_case()
        self.assertEqual(before,self.c['stock']);self.assertEqual(balance+18,self.c['money']);self.assert_valid()

    def test_theft_never_consumes_reserved_stock(self):
        self.j.act('ask');t=self.j.task;item=t['needs']['product'];self.c['stock']={k:0 for k in self.c['stock']};self.c['stock'][item]=t['needs']['qty']
        for _ in range(t['needs']['qty']):self.j.act('shop_pick',item=item)
        self.assertEqual(available(self.c,item),0);self.spawn()
        self.assertEqual(self.case()['loss']['kind'],'cash');self.assertLessEqual(self.case()['loss']['cash'],18)
        self.assertEqual(self.c['stock'][item],t['needs']['qty']);self.assert_valid()

    def test_cash_theft_refund_not_taxable_revenue(self):
        self.j=Journey('accounting',slot=0);before=self.c['money'];self.spawn();self.assertEqual(self.c['money'],before-18)
        self.police_result();self.act('recover',confirm=True);self.assertEqual(self.c['money'],before)
        self.act('reward',confirm=True);self.assertEqual(self.o['finance']['period_revenue'],0);self.assert_valid()

    def test_camera_installed_later_does_not_create_old_evidence(self):
        self.spawn();self.assertEqual(len(self.case()['evidence']),2)
        self.act('buy_security',item='camera',confirm=True);self.assertEqual(len(self.case()['evidence']),2)
        self.no_effect('case_read',evidence='camera');self.no_effect('buy_security',item='camera',confirm=True)
        self.police_result();self.finish_case();self.spawn()
        self.assertEqual(len(self.case()['evidence']),3);self.assert_valid()

    def test_insurance_purchased_before_only_and_no_double_compensation(self):
        self.act('insurance_toggle',enabled=True,confirm=True);self.spawn(roll=99);loss=self.case()['loss']['value'];balance=self.c['money']
        self.police_result();self.assertEqual(self.case()['outcome'],'unrecovered');self.no_effect('recover',confirm=True);self.no_effect('reward',confirm=True)
        self.act('insurance_claim',confirm=True);self.assertEqual(self.c['money'],balance+loss*60//100)
        self.no_effect('insurance_claim',confirm=True);self.act('case_close');self.assert_valid()

    def test_insurance_not_retroactive_and_toggle_requires_confirmation(self):
        self.spawn(roll=99);self.no_effect('insurance_toggle',enabled=True);self.act('insurance_toggle',enabled=True,confirm=True)
        self.police_result();self.no_effect('insurance_claim',confirm=True);self.act('case_close');self.assert_valid()

    def test_practice_case_no_asset_reward_or_bill_mutation(self):
        before=(copy.deepcopy(self.c['stock']),self.c['money'],self.c['xp']);self.spawn(practice=True)
        self.police_result();self.finish_case()
        self.assertEqual(before,(self.c['stock'],self.c['money'],self.c['xp']));self.assertFalse(self.o['finance']['bills']);self.assert_valid()

    def test_active_live_case_cannot_be_replaced_by_demo(self):
        self.spawn();self.no_effect('case_demo',kind='snatch');self.no_effect('case_close')

    def test_natural_security_mode_toggle_and_one_case_cooldown(self):
        self.j.state['settings'].update(securityEvents=False);self.c['life']['mode']='calm';self.c.update(day=4,day_completed=1,event=None);self.o['work_ticks']=20
        self.advance();self.assertIsNone(self.o['security']['active'])
        self.j.state['settings']['securityEvents']=True;self.c['event']=None;self.advance();self.assertEqual(self.case()['kind'],'misplaced')
        self.investigate();self.act('case_close');self.c['event']=None;self.advance()
        self.assertIsNone(self.o['security']['active']);self.assert_valid()

    def test_natural_theft_has_fixed_truth_and_real_loss(self):
        self.j.state['settings'].update(securityEvents=True);self.c['life']['mode']='normal';self.c.update(day=4,day_completed=1,event=None);self.o['work_ticks']=20
        before=sum(self.c['stock'].values());self.advance();self.assertEqual(self.case()['kind'],'theft');self.assertFalse(self.case()['practice'])
        self.assertEqual(sum(self.c['stock'].values()),before-1);self.assert_valid()

    def test_ledger_compaction_preserves_wallet(self):
        for _ in range(1505):money(self.j.state,self.c,1,'Thu nhỏ',category='other_income')
        self.assertLess(len(self.o['finance']['ledger']),1500);self.assertEqual(self.c['money'],1825);self.assert_valid()

    def test_stock_capacity_changes_after_room_upgrade(self):
        item=next(iter(self.c['stock']));self.c['stock'][item]=12
        with self.assertRaises(GameError):self.j.act('order_stock',item=item,qty=1)
        self.close();self.act('move_property',tier='sunny',confirm=True);self.j.act('start_day')
        self.j.act('order_stock',item=item,qty=1);self.assertEqual(self.c['shipments'][-1]['qty'],1);self.assert_valid()

    def test_downgrade_room_does_not_drop_stock(self):
        self.close();self.act('move_property',tier='sunny',confirm=True)
        item=next(iter(self.c['stock']));self.c['stock'][item]=13
        self.no_effect('move_property',tier='cozy',confirm=True);self.assertEqual(self.c['stock'][item],13)


class StaffJobBonusTests(unittest.TestCase):
    """Owner 03/10: hired staff pay their way. Each job they complete (attendance 'jobs') earns the shop
    RULES staff_job_bonus xu, +1 when spirited or careful, capped per person a day, paid once at close."""
    setUp=OperationsTests.setUp;c=OperationsTests.c;o=OperationsTests.o;act=OperationsTests.act;hire=OperationsTests.hire
    staff=OperationsTests.staff;advance=OperationsTests.advance;close=OperationsTests.close;assert_valid=OperationsTests.assert_valid
    def rows(self,day):return [r for r in self.o['finance']['ledger'] if r['ref']==f'staff-jobs-{day}']

    def test_bonus_paid_once_at_close_in_income_and_net(self):
        sid=self.hire();self.act('assign',employee=sid,role='patrol');day=self.c['day']
        self.advance(30);e=self.staff(sid);jobs=self.o['attendance'][str(day)][sid]['jobs']
        self.assertTrue(6<=jobs<=12,jobs);self.assertFalse(self.rows(day))  # nothing mid-shift
        rate=ops.job_rate(e);self.assertEqual(rate,3+(e['morale']>=80 or e['precision']>=90))
        money=self.c['money'];earn=self.c['earnings'];n=len(self.o['finance']['ledger'])
        summary=self.j.act('end_day',carry_event=True)['summary']
        bonus=jobs*rate;row,=self.rows(day);new=self.o['finance']['ledger'][n:]
        self.assertEqual((row['amount'],row['category'],row['day']),(bonus,'other_income',day))
        self.assertEqual(row['reason'],f"Thưởng việc của đội — {e['name']}: {jobs} việc")
        self.assertIn(row,new);self.assertEqual(self.c['money'],money+sum(x['amount'] for x in new))
        self.assertEqual(summary['operations']['staff_bonus'],bonus);self.assertEqual(summary['operations']['staff'][0]['bonus'],bonus)
        self.assertGreater(bonus,e['wage']*2)  # a normal day clearly beats the wage
        self.assertGreaterEqual(summary['income'],earn+bonus);self.assertEqual(summary['net'],summary['income']-summary['cost'])
        self.assert_valid()
        # Closing again is refused, and even a forced second close of the same day never pays twice.
        with self.assertRaises(GameError):self.j.act('end_day',carry_event=True)
        c=self.c;c['day']=day;c['open']=True;c['ops']['finance']['last_closed']=0;before=c['money']
        ops.on_close(self.j.state,c,self.j.career)
        self.assertEqual(len(self.rows(day)),1);self.assertEqual(c['money'],before)

    def test_no_bonus_for_paused_resting_or_off_shift_staff(self):
        self.close();self.act('move_property',tier='sunny',confirm=True);self.j.act('start_day')
        a,b=self.hire(1),self.hire(2)
        for sid in (a,b):self.act('assign',employee=sid,role='patrol')
        ops.spawn_incident(self.j.state,self.c,self.j.career,'accident',False,self.staff(a))  # a: paused
        self.act('shift',employee=b,on=False)  # b: off shift
        day=self.c['day'];self.advance(20);summary=self.j.act('end_day',carry_event=True)['summary']['operations']
        self.assertEqual(summary['staff_bonus'],0);self.assertFalse(self.rows(day))
        self.assertEqual([x['bonus'] for x in summary['staff']],[0,0])
        # Resting: no job while resting, so nothing earned for those moves.
        self.j.act('start_day');self.act('rest',employee=b);day=self.c['day'];self.advance(3)
        self.assertEqual(self.o['attendance'].get(str(day),{}).get(b,{}).get('jobs',0),0)
        self.close();self.assertFalse(self.rows(day));self.assert_valid()

    def test_practice_incident_and_staff_moves_never_pay_mid_shift(self):
        sid=self.hire();self.act('assign',employee=sid,role='patrol');self.act('incident_demo',kind='accident')
        before=self.c['money'];self.advance(12);self.assertEqual(self.c['money'],before)
        self.assertTrue(self.o['incident']['practice']);self.assertGreater(self.o['attendance'][str(self.c['day'])][sid]['jobs'],0)

    def test_cap_and_rate(self):
        sid=self.hire();self.act('assign',employee=sid,role='patrol');self.advance(4);day=self.c['day']
        row=self.o['attendance'][str(day)][sid];row['jobs']=40;e=self.staff(sid);e.update(morale=70,precision=80)
        self.assertEqual(ops.job_rate(e),3)
        summary=self.j.act('end_day',carry_event=True)['summary']['operations']
        self.assertEqual(summary['staff_bonus'],12*3);self.assertEqual(self.rows(day)[0]['reason'],f"Thưởng việc của đội — {e['name']}: 12 việc")
        e['precision']=92;self.assertEqual(ops.job_rate(e),4);e.update(precision=80,morale=80);self.assertEqual(ops.job_rate(e),4)
        self.assert_valid()

    def test_older_attendance_without_jobs_pays_nothing(self):
        sid=self.hire();self.act('assign',employee=sid,role='patrol');self.advance(8);day=self.c['day']
        self.o['attendance'][str(day)][sid].pop('jobs')  # a shift recorded by a pre-1.4.31 server
        self.assertEqual(self.j.act('end_day',carry_event=True)['summary']['operations']['staff_bonus'],0);self.assert_valid()

    def test_save_written_here_validates_on_release_1431(self):
        """Rolling releases: an older server must accept every save this build writes (ledger category,
        attendance rows, the incident gap reusing day_staff_incident)."""
        import os,subprocess,sys
        old=Path(os.environ.get('MNL_OLD_TREE','D:/projects/Mot_ngay_lam_nghe/_rel1431/mot-ngay-lam-nghe'))
        if not (old/'game'/'engine.py').exists():self.skipTest('1.4.31 tree not available')
        sid=self.hire();self.act('assign',employee=sid,role='patrol');self.advance(30);self.close()
        self.assertTrue(self.rows(self.c['day']-1));self.j.act('start_day');self.advance(5)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'save.json';path.write_text(json.dumps(self.j.state,ensure_ascii=False),encoding='utf-8')
            paths=[str(old)]+[p for p in os.environ.get('PYTHONPATH','').split(os.pathsep) if p and p!='.']
            code=('import json,sys;from game.engine import validate_state,public_state;s=json.load(open(sys.argv[1],encoding="utf-8"));'
                  'validate_state(s);public_state(s);print("ok")')
            r=subprocess.run([sys.executable,'-c',code,str(path)],cwd=str(old),env=dict(os.environ,PYTHONPATH=os.pathsep.join(paths),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,encoding='utf-8',timeout=120)
        self.assertEqual((r.returncode,r.stdout.strip()),(0,'ok'),r.stderr[-2000:])


class StaffIncidentRateTests(unittest.TestCase):
    """Owner 03/10: staff incidents are rare and calm, about one every 4-5 working days per shop (was most days).
    Drives operations.tick/on_close/on_start directly so many simulated days stay fast."""
    def days_with_incident(self,seed,staff=1,days=60,moves=32):
        j=Journey();j.state['settings']['securityEvents']=False;s=j.state;c=j.c;cid=j.career;c['ops']['rng']=seed
        c['ops']['property']['tier']='garden';c['money']+=500;c['ops']['finance']['opening_balance']+=500
        for n in range(1,staff+1):
            j.act('ops_hire',candidate=f'{cid}-staff-{n}',confirm=True);j.act('ops_assign',employee=f'{cid}-staff-{n}',role='patrol')
        s=j.state;hit=[]
        for _ in range(days):
            c=s['careers'][cid]
            for _ in range(moves):
                c['event']=None;c['turn']+=1;ops.tick(s,c,cid,'advance')
                i=c['ops']['incident']
                if i and not i['practice'] and i['status']!='resolved':hit.append(c['day']);i['status']='resolved'  # handled at once
            ops.on_close(s,c,cid);c['day']+=1;ops.on_start(s,c,cid)
        return hit
    def test_incident_rate_band_and_gap(self):
        for staff,lo,hi in ((1,4.5,7.5),(2,5.0,7.5),(4,5.0,7.5)):  # 6-7.5 a month: one every 4-5 days
            hits=[self.days_with_incident(seed*7919+13,staff) for seed in range(4)]
            per30=sum(map(len,hits))/len(hits)/2
            self.assertTrue(lo<=per30<=hi,(staff,per30,hits))  # per 30 working days; was 20-28 before
            for h in hits:self.assertTrue(all(b-a>=ops.STAFF_INCIDENT_GAP for a,b in zip(h,h[1:])),h)


class OperationsSaveTests(unittest.TestCase):
    @staticmethod
    def legacy():
        s=new_state();s['schema']=1;s['settings'].pop('securityEvents')
        for c in s['careers'].values():c.pop('ops');c['day']=21;c['money']=421;c['theme']='warm'
        return s
    def test_v1_upgrade_preserves_state_and_no_retroactive_bills(self):
        old=self.legacy();s=migrate_state(old);validate_state(s)
        self.assertEqual(old['schema'],1);self.assertEqual(s['schema'],4)
        for c in s['careers'].values():
            self.assertEqual(c['day'],21);self.assertEqual(c['money'],421);self.assertFalse(c['ops']['finance']['bills']);self.assertEqual(c['ops']['finance']['period_start'],21)
        self.assertEqual(migrate_state(s),s)

    def test_malformed_ops_fail_without_destroying_save(self):
        with tempfile.TemporaryDirectory() as td:
            store=Store(Path(td)/'save.db');token,_,_=store.session()
            fields=[('staff',None),('finance',{}),('security',{}),('attendance',[]),('incident',{'kind':'wrong'})]
            for field,value in fields:
                bad=new_state();bad['careers']['mother_baby']['ops'][field]=value
                with self.subTest(field=field),self.assertRaises(GameError):
                    store.command(token,'bad-'+field+'-0001',0,None,'import_save',{'save':{'format':'mot-ngay-lam-nghe/save-v2','state':bad}})
                self.assertEqual(store.read(token)[1],0)

    def test_wallet_mismatch_rejected(self):
        s=new_state();s['careers']['mother_baby']['money']+=1
        with self.assertRaises(GameError):validate_state(s)

    def test_unearned_payout_rejected(self):
        j=Journey();v=ops.spawn_case(j.state,j.c,j.career,'theft');v.update(reward_claimed=True,reward=18)
        with self.assertRaises(GameError):validate_state(j.state)

    def test_existing_sqlite_migrated_once(self):
        with tempfile.TemporaryDirectory() as td:
            store=Store(Path(td)/'save.db');token,_,_=store.session()
            with store.connect() as db:db.execute('UPDATE sessions SET state=? WHERE sid=?',(json.dumps(self.legacy()),store.key(token)))
            s,r,_=store.read(token);self.assertEqual(r,1);self.assertEqual(s['schema'],4)
            self.assertEqual(store.read(token)[1],1)

    def test_new_hire_request_replay_and_concurrent_revision(self):
        with tempfile.TemporaryDirectory() as td:
            store=Store(Path(td)/'save.db');token,_,_=store.session();p={'candidate':'mother_baby-staff-1','confirm':True}
            a=store.command(token,'hire-repeat-0001',0,'mother_baby','ops_hire',p)
            b=store.command(token,'hire-repeat-0001',0,'mother_baby','ops_hire',p)
            self.assertTrue(b['replayed']);self.assertEqual(a['revision'],b['revision']);self.assertEqual(b['state']['careers']['mother_baby']['money'],290)
            with self.assertRaises(Conflict):store.command(token,'new-tab-0001',0,'mother_baby','ops_hire',{'candidate':'mother_baby-staff-2','confirm':True})

    def test_v1_import_and_v2_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            store=Store(Path(td)/'save.db');token,_,_=store.session()
            store.command(token,'import-old-0001',0,None,'import_save',{'save':{'format':'mot-ngay-lam-nghe/save-v1','state':self.legacy()}})
            raw,rev,_=store.read(token)
            store.command(token,'import-new-0001',rev,None,'import_save',{'save':{'format':'mot-ngay-lam-nghe/save-v2','state':raw}})
            self.assertEqual(store.read(token)[0],raw)


if __name__=='__main__':unittest.main()
