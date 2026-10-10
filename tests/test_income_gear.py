import copy
import unittest
from unittest.mock import patch

from game import content, work_gear, income_gear, workplace_business as wb, quay_business as qb, quay_self as qs
from game.engine import new_state, apply_action, validate_state, GameError, task_done
from tests.test_workplace_business import WorkplaceBusinessTests
from tests.test_quay_business import fixture as base_fixture


def fixture():
    s,st=base_fixture()
    s['careers']['milk_tea']={'upgrades':[]}
    return s,st


def equip(c, group, tier=3, career='accounting'):
    c['upgrades'] += [f'incomegear_{career}_{group}_{n}' for n in range(1, tier+1)]


class IncomeGearTests(unittest.TestCase):
    def test_catalogue_purchase_prerequisites_funds_and_no_speed_confusion(self):
        key='incomegear_accounting_quality_1'
        self.assertTrue(key in content.UPGRADE_INDEX, 'Missing income equipment catalogue')
        s=new_state();c=s['careers']['accounting'];c['money']=2000;c['ops']['finance']['opening_balance']=2000
        with self.assertRaises(GameError):apply_action(s,'accounting','buy_upgrade',{'item':'incomegear_accounting_quality_2'})
        out,_=apply_action(s,'accounting','buy_upgrade',{'item':key})
        self.assertEqual(out['careers']['accounting']['money'],1900)
        self.assertEqual(work_gear.factor(out['careers']['accounting']),1)
        validate_state(out)
        with self.assertRaises(GameError):apply_action(out,'accounting','buy_upgrade',{'item':key})
        with self.assertRaises(GameError):apply_action(s,'accounting','buy_upgrade',{'item':'incomegear_milk_tea_online_1'})
        c['money']=0;c['ops']['finance']['opening_balance']=0
        with self.assertRaises(GameError):apply_action(s,'accounting','buy_upgrade',{'item':key})

    def test_staff_quality_pays_more_for_same_stock_and_costs(self):
        sample=WorkplaceBusinessTests();s,c,e=sample.sample();other=copy.deepcopy(s)
        equip(other['careers']['accounting'],'quality')
        at=sample.next(c);wb.settle(s,at);wb.settle(other,at)
        improved=other['careers']['accounting'];a=wb._recent(c)[-1];b=wb._recent(improved)[-1]
        self.assertGreater(b['net'],a['net'])
        self.assertEqual(b['expenses'],a['expenses']);self.assertEqual(b['items'],a['items'])
        self.assertGreater(improved['money'],c['money'])
        wb.validate(improved,'accounting')
        before=copy.deepcopy(other);wb.settle(other,at);self.assertEqual(other,before)
        self.assertEqual(improved['money'],improved['ops']['finance']['opening_balance']+sum(x['amount'] for x in improved['ops']['finance']['ledger']))

    def test_staff_demand_preserves_pending_then_speeds_next_order(self):
        sample=WorkplaceBusinessTests();s,c,e=sample.sample();old=copy.deepcopy(c['ops']['business']['pending'])
        equip(c,'demand');wb.refresh(c,'accounting',2000000000)
        self.assertEqual(c['ops']['business']['pending'],old)
        before=next(iter(old.values()))['seconds'];wb.settle(s,sample.next(c))
        self.assertLess(next(iter(c['ops']['business']['pending'].values()))['seconds'],before)

    def test_quay_online_only_when_enabled_and_manual_wait(self):
        s,st=fixture();qb.initialize(s,st,1000)
        base=qb._intervals(st);c=s['careers']['milk_tea'];equip(c,'online',career='milk_tea');qb.reconcile(s)
        self.assertEqual(qb._intervals(st),base)
        st['online']=True;plain=copy.deepcopy(st);plain['business'].pop('income_gear',None)
        self.assertLess(next(iter(qb._intervals(st).values())),next(iter(qb._intervals(plain).values())))
        self.assertLess(qs._online_wait(st,s),qs._manual_wait(st,s))

    def test_quay_quality_increases_profit_without_changing_customer_bill(self):
        s,st=fixture();qb.initialize(s,st,1000);plain=copy.deepcopy(st)
        equip(s['careers']['milk_tea'],'quality',career='milk_tea');qb.reconcile(s)
        dish=next(iter(st['business']['stock']));st['business']['stock'][dish]=plain['business']['stock'][dish]=20
        for n in range(10):
            qb.sale(st,[dish],1000000+n);qb.sale(plain,[dish],1000000+n)
        self.assertEqual(st['business']['revenue'],plain['business']['revenue'])
        self.assertEqual(st['business']['stock'],plain['business']['stock'])
        self.assertGreater(st['business']['profit_boost']['total'],plain['business']['profit_boost']['total'])

    def test_equipped_quay_polling_equals_offline_and_never_oversells(self):
        s,st=fixture();st['online']=True
        for group in ('demand','quality','online'):equip(s['careers']['milk_tea'],group,career='milk_tea')
        qb.settle(s,1000);initial=sum(st['business']['stock'].values());other=copy.deepcopy(s)
        for at in range(1001,1601):qb.settle(s,at)
        qb.settle(other,1600);self.assertEqual(s,other)
        self.assertLessEqual(st['business']['sold'],initial)
        before=copy.deepcopy(s);qb.settle(s,1600);self.assertEqual(s,before)

    def test_completed_manual_work_gets_quality_bonus_once(self):
        s=new_state();c=s['careers']['mother_baby'];equip(c,'quality',career='mother_baby')
        t=dict(id='test-income',career='mother_baby',npc='mai',title='Đơn kiểm thử',mistakes=0)
        before=c['money']
        with patch('game.engine.fbk.make_review',return_value={'text':'OK','stars':4,'feedback':{},'aside':False}),patch('game.engine.life.after_task'),patch('game.engine.ovt.on_job'):
            task_done(s,c,t,100,'Hoàn thành')
            self.assertEqual(c['money']-before,130)
            with self.assertRaises(GameError):task_done(s,c,t,100,'Hoàn thành')

    def test_tiers_replace_lower_tiers_and_reads_are_pure(self):
        c={'upgrades':[]};self.assertEqual(income_gear.effects(c),dict(demand=0,quality=0,online=0))
        equip(c,'quality');equip(c,'demand')
        before=copy.deepcopy(c)
        self.assertEqual(income_gear.effects(c),dict(demand=50,quality=30,online=0))
        self.assertEqual(c,before)
        self.assertEqual(income_gear.improved_revenue(c,10,12),10,'A loss never earns a quality bonus')

    def test_first_quality_tier_already_helps_small_completed_orders(self):
        c={'upgrades':[]};equip(c,'quality',tier=1)
        self.assertEqual(income_gear.improved_revenue(c,15,7),16)

    def test_pharmacy_refill_bonus_uses_real_terminal_action_and_cannot_repeat(self):
        from tests.helpers import Journey
        from tests.test_desk_care import next_day
        j=Journey('pharmacy');equip(j.c,'quality',career='pharmacy')
        next_day(j);j.act('ph_care_call',who='nam');next_day(j)
        before=j.c['money'];stock=j.c['stock']['P-02-A']
        result=j.act('ph_care_hand',who='nam',confirm=True)
        self.assertEqual(j.c['money']-before,35+11)
        self.assertEqual(result.get('income_gear_bonus'),11)
        self.assertIn('11 xu nhờ thiết bị',result['message'])
        self.assertEqual(j.c['stock']['P-02-A'],stock-1)
        with self.assertRaises(GameError):j.act('ph_care_hand',who='nam',confirm=True)
        validate_state(j.state)

    def test_monthly_book_completion_gets_bonus_once(self):
        from tests.test_desk_care import BookkeepingCareTests,care
        from game import engine
        case=BookkeepingCareTests();case.setUp();j=case.j;equip(j.c,'quality',career='accounting')
        j.act('ac_book_open',client='hoa');spec=engine._ac_case(engine.AC_CLIENT['hoa'],0)
        before=j.c['money']
        result=j.act('ac_book_close',client='hoa',note='missing_note' if spec['missing'] else 'full',confirm=True)
        fee=care(j)['clients']['hoa']['months'][-1]['closed']['fee']
        self.assertEqual(j.c['money']-before,fee+(fee*30+99)//100)
        self.assertEqual(result['income_gear_bonus'],(fee*30+99)//100)
        with self.assertRaises(GameError):j.act('ac_book_close',client='hoa',confirm=True)

    def test_office_bakery_box_earns_bonus_but_bank_announces_only_customer_payment(self):
        from tests.test_career_cafe_bakery import CafeBakeryTests
        from game.careers import cafe_bakery as cb
        case=CafeBakeryTests();case.setUp();self.addCleanup(case.tearDown)
        j=case.journey(lambda n:n['kind']=='drink',days=[3]);equip(j.c,'quality',career='cafe_bakery')
        case.open_event('box_order');j.act('cb_event',event='box_order',choice='half')
        box=cb._plan(j.c)['rules']['box'];case.ensure_case(j,'croissant',4)
        before=j.c['money'];pay=box['goal']*box['pay'];result=j.act('cb_box_send')
        self.assertEqual(result['bank'],[pay])
        self.assertEqual(result['income_gear_bonus'],(pay*30+99)//100)
        self.assertEqual(j.c['money']-before,pay+result['income_gear_bonus'])
        with self.assertRaises(GameError):j.act('cb_box_send')

    def test_bonus_note_does_not_leak_to_next_command(self):
        s=new_state();c=s['careers']['accounting'];equip(c,'quality')
        def paid():
            income_gear.completion_bonus(s,c,35,'Đơn','ref')
            return s,dict(message='Xong')
        _,result=income_gear.collect(paid)
        self.assertEqual(result['income_gear_bonus'],11)
        _,clean=income_gear.collect(lambda:(s,dict(message='Đã xem')))
        self.assertNotIn('income_gear_bonus',clean)

    def test_online_channel_mix_matches_extra_online_orders(self):
        s,st=fixture();st['online']=True;qb.initialize(s,st,1000)
        self.assertEqual([income_gear.channel(st,n) for n in range(3)],['counter','counter','online'])
        equip(s['careers']['milk_tea'],'online',career='milk_tea');qb.reconcile(s)
        self.assertEqual(sum(income_gear.channel(st,n)=='online' for n in range(100)),50)
        st['online']=False
        self.assertTrue(all(income_gear.channel(st,n)=='counter' for n in range(100)))

    def test_equipped_staff_polling_matches_offline_and_empty_stock_stops(self):
        sample=WorkplaceBusinessTests();s,c,e=sample.sample('grocery')
        equip(c,'quality',career='grocery');equip(c,'demand',career='grocery')
        other=copy.deepcopy(s);at=sample.next(c)
        for now in range(at,at+301):wb.settle(s,now)
        wb.settle(other,at+300);self.assertEqual(s,other)
        c['ext']['inv']['lots']=[];wb.settle(s,at+1000)
        before=c['ops']['business']['served'];wb.settle(s,at+2000)
        self.assertEqual(c['ops']['business']['served'],before)
        wb.validate(c,'grocery')

    def test_quay_public_bonus_matches_settlement_and_is_read_only(self):
        s,st=fixture();qb.initialize(s,st,1000)
        equip(s['careers']['milk_tea'],'quality',career='milk_tea');qb.reconcile(s)
        before=copy.deepcopy(st);view=qb.public(st)
        self.assertEqual(view['bonus_percent'],82)
        self.assertEqual(view['staff_bonus_percent'],173)
        self.assertEqual(st,before)

    def test_online_not_offered_without_an_online_counter(self):
        for cid in content.CAREERS:
            items=[u for u in income_gear.ITEMS.values() if u['careers']==[cid]]
            self.assertEqual(len(items),9 if cid in income_gear.ONLINE_CAREERS else 6)

    def test_referred_work_does_not_get_quality_bonus(self):
        s=new_state();c=s['careers']['pharmacy'];equip(c,'quality',career='pharmacy')
        t=dict(id='test-referred',career='pharmacy',npc='mai',title='Chuyển người phụ trách',mistakes=0)
        before=c['money']
        with patch('game.engine.fbk.make_review',return_value={'text':'OK','stars':4,'feedback':{},'aside':False}),patch('game.engine.life.after_task'),patch('game.engine.ovt.on_job'):
            task_done(s,c,t,25,'Chuyển','referred')
        self.assertEqual(c['money']-before,25)

    def test_purchase_cannot_upgrade_unsettled_historical_orders(self):
        sample=WorkplaceBusinessTests();s,c,e=sample.sample()
        c['ops']['finance']['opening_balance']+=2000-c['money'];c['money']=2000
        before=copy.deepcopy(s)
        with patch('game.business.time.time',return_value=2000000300),patch.object(wb,'MAX_ORDERS',1):
            with self.assertRaisesRegex(GameError,'đồng bộ'):
                apply_action(s,'accounting','buy_upgrade',{'item':'incomegear_accounting_quality_1'})
        self.assertEqual(s,before)
        with patch('game.business.time.time',return_value=2000000300):
            synced,_=apply_action(s,None,'business_sync',{},internal=True)
            pending=copy.deepcopy(synced['careers']['accounting']['ops']['business']['pending'])
            bought,_=apply_action(synced,'accounting','buy_upgrade',{'item':'incomegear_accounting_quality_1'})
        self.assertEqual(bought['careers']['accounting']['ops']['business']['pending'],pending)


if __name__=='__main__':unittest.main()
