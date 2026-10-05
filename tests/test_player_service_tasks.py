import copy
import unittest

from game import engine as e
from game import player_service_tasks as pst
from tests.helpers import Journey


BUYER = dict(name='Khách thật', code='VISITOR1', fc='')


def bound(t, oid='order-test'):
    t['player_order'] = dict(v=1, id=oid, buyer=dict(BUYER), note='Theo đúng phiếu.', price=30)


class PlayerServiceTasks(unittest.TestCase):
    def test_old_quay_snapshot_acceptance_does_not_require_new_expense_carries(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb
        s,st=fixture();qb.settle(s,now=1000)
        b=st['business']
        for key in ('environment','protection'):b['carry'].pop(key)
        for key in ('income_tax','protection','market_epoch'):b.pop(key)
        before=copy.deepcopy(st)
        self.assertTrue(pst.can_accept_visit(st))
        self.assertEqual(st,before)

    def test_all_careers_offer_canonical_service_without_mutating_state(self):
        for cid in e.new_state()['careers']:
            with self.subTest(career=cid):
                j=Journey(cid);before=copy.deepcopy(j.state)
                offers=pst.offers(j.state,cid)
                shadow=copy.deepcopy(j.state)
                task=pst._candidate(shadow,cid)
                reference=[pst._offer(task)] if task else []
                staff=pst._staff_offer(shadow,cid)
                if staff:reference.append(staff)
                self.assertEqual(offers,reference)
                self.assertTrue(offers)
                self.assertEqual(j.state,before)
                offer=offers[0]
                self.assertNotIn('needs',offer)
                self.assertNotIn('solution',offer)
                self.assertGreater(offer['price'],0)
                tid=pst.accept(j.state,cid,dict(id='visit-'+cid,offer_id=offer['offer_id'],buyer=BUYER,note='',price=offer['price']))
                self.assertEqual(j.c['active_task'],before['careers'][cid]['active_task'])
                self.assertEqual(j.c['tasks'][:-1],before['careers'][cid]['tasks'])
                self.assertNotEqual(j.get(tid)['kind'],'setup')
                e.validate_state(j.state)

    def test_accept_rejects_stale_offer_price_and_closed_career(self):
        j=Journey('mother_baby');offer=pst.offers(j.state,j.career)[0]
        order=dict(id='visit-1',offer_id=offer['offer_id'],buyer=BUYER,note='',price=offer['price']+1)
        with self.assertRaises(e.GameError):pst.accept(j.state,j.career,order)
        order['price']=offer['price'];j.c['open']=False
        self.assertFalse(pst.offers(j.state,j.career))
        with self.assertRaises(e.GameError):pst.accept(j.state,j.career,order)

    def test_authentic_gift_task_completes_without_npc_money_review_or_tip(self):
        j=Journey('mother_baby',slot=0);bound(j.task)
        before=copy.deepcopy(j.state);cash=j.c['money'];tid=j.task['id']
        j.solve(tid)
        self.assertEqual(j.get(tid)['status'],'completed')
        self.assertLessEqual(j.c['money'],cash)
        self.assertFalse([r for r in j.c['feed'] if r['source']==tid and r['kind']=='review'])
        self.assertNotIn('tip_roll',j.get(tid))
        self.assertEqual(pst.transitions(before,j.state,j.career,'shop_deliver',{}),[dict(id='order-test',status='completed')])
        self.assertEqual(pst.transitions(j.state,j.state,j.career,'shop_deliver',{}),[])
        self.assertEqual(pst.transitions(before,j.state,j.career,'import_save',{}),[])

    def test_metadata_validated_and_projected_without_changing_canonical_npc(self):
        j=Journey('mother_baby',slot=0);bound(j.task);npc=j.task['npc']
        view=e.task_view(j.task)
        self.assertEqual(view['player_order']['buyer']['name'],BUYER['name'])
        self.assertEqual(j.task['npc'],npc)
        view['player_order']['buyer']['name']='Changed'
        self.assertEqual(j.task['player_order']['buyer']['name'],BUYER['name'])
        j.task['player_order']['price']=True
        with self.assertRaises(e.GameError):e.validate_state(j.state)

    def test_money_scope_keeps_costs_other_npc_and_restores_after_failure(self):
        j=Journey('mother_baby');t=j.task;bound(t)
        other=next(x for x in j.c['tasks'] if x is not t);cash=j.c['money']
        with pst.command(j.state,j.career,'shop_deliver',{'task':t['id']}):
            e.money(j.state,j.c,80,'NPC reward',t['id'])
            e.money(j.state,j.c,20,'Linked tip','booking-id','tip')
            e.money(j.state,j.c,-3,'Materials',t['id'])
            e.money(j.state,j.c,5,'Other customer',other['id'])
        self.assertEqual(j.c['money'],cash+2)
        e.money(j.state,j.c,7,'Ordinary income')
        self.assertEqual(j.c['money'],cash+9)

    def test_abandon_is_cancelled_and_not_fulfilled(self):
        from game import abandon
        j=Journey('mother_baby',slot=0);bound(j.task);before=copy.deepcopy(j.state)
        abandon._cancel(j.state,j.c,j.task)
        self.assertEqual(pst.transitions(before,j.state,j.career,'select_career',{}),[dict(id='order-test',status='cancelled')])

    def test_cafe_real_drink_and_early_mood_tip_never_create_npc_income(self):
        import tests.test_career_cafe_bakery as cbtests
        helper=cbtests.CafeBakeryTests();helper.setUp();self.addCleanup(helper.tearDown)
        j=helper.journey(lambda n:n['kind']=='drink',style='mood');bound(j.task)
        tid=j.task['id'];cash=j.c['money'];j.act('ask',task=tid)
        j.act('cb_guess',task=tid,drink=j.get(tid)['needs']['drink'])
        self.assertEqual(j.c['money'],cash)
        helper.drink(tid);j.act('cb_serve',task=tid,confirm=True)
        self.assertEqual(j.get(tid)['status'],'completed')
        self.assertLessEqual(j.c['money'],cash)
        self.assertFalse([r for r in j.c['feed'] if r['source']==tid and r['kind']=='review'])

    def test_homestay_real_checkin_no_npc_payment(self):
        import tests.test_career_homestay as htests
        helper=htests.HomestayTests();helper.setUp();self.addCleanup(helper.tearDown)
        j=helper.journey('checkin',lambda t:t['_x']['adults']==t['needs']['adults'] and t['_x']['kids']==t['needs']['kids'])
        helper.clear_bookings(j);helper.make_clean(j,'thong','suong','gac','quy');bound(j.task)
        cash=j.c['money'];tid=helper.do_checkin(j)
        j.act('hs_welcome',task=tid,confirm=True)
        self.assertEqual(j.get(tid)['status'],'completed')
        self.assertLessEqual(j.c['money'],cash)
        self.assertFalse([r for r in j.c['feed'] if r['source']==tid and r['kind']=='review'])

    def test_delivery_real_handover_no_fee_or_regular_tip(self):
        import tests.test_career_delivery as dtests
        j,tid=dtests.journey('F1',rain=False);bound(j.get(tid))
        cash=j.c['money'];dtests.ride(j,'com');j.act('dl_check',task=tid);j.act('dl_load',task=tid)
        dtests.ride(j,'office');j.act('dl_deliver',task=tid)
        self.assertEqual(j.get(tid)['status'],'completed')
        self.assertLessEqual(j.c['money'],cash)
        self.assertFalse([r for r in j.c['feed'] if r['source']==tid and r['kind']=='review'])

    def test_quay_manual_reserves_stock_preserves_run_and_waits_for_real_payment(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb,quay_self as qs
        s,st=fixture(staff=False);qb.settle(s,now=1000)
        qs.action(s,'jr_quay_start',{'stall':'q1'},st);run=copy.deepcopy(st['run'])
        dish=next(iter(st['business']['stock']));stock=st['business']['stock'][dish]
        oid=pst.accept_visit(s,'q1',dict(id='visit-quay',offer_id=dish,items=[dish],price=qs.price(st,dish),buyer=BUYER,note=''),now=1000)
        self.assertEqual(st['business']['stock'][dish],stock-1)
        before=copy.deepcopy(s);cash=st['till']+st['fund']
        qs.action(s,'jr_quay_serve',dict(stall='q1',visitor_id=oid,items=[dish],change=0,smile=True),st)
        self.assertEqual(st['run'],run)
        self.assertEqual(st['fund']+st['till'],cash)
        self.assertEqual(pst.transitions(before,s,None,'jr_quay_serve',{}),[dict(id=oid,status='completed')])

    def test_quay_staff_needs_real_time_cash_and_reserved_goods(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb,quay_self as qs
        s,st=fixture();qb.settle(s,now=1000)
        dish=next(iter(st['business']['stock']))
        pst.accept_visit(s,'q1',dict(id='visit-staff',offer_id=dish,items=[dish],price=qs.price(st,dish),buyer=BUYER,note=''),now=1000)
        row=st['business']['visitor_orders'][0];at=row['due_at']
        st['business']['stock']={};cash=st['fund']+st['till']
        qb.settle(s,now=(at-1)/1000);self.assertEqual(row['status'],'queued')
        qb.settle(s,now=at/1000);self.assertEqual(row['status'],'completed')
        self.assertGreater(st['business']['expenses']['wages']+st['business']['carry']['wages'],0)
        self.assertEqual(st['business']['revenue'],0)
        snap=copy.deepcopy(s);qb.settle(s,now=at/1000);self.assertEqual(s,snap)

    def test_staff_visitors_all_41_use_actual_materials_and_wages_without_npc_pay(self):
        from tests.test_workplace_business import WorkplaceBusinessTests
        from game import workplace_business as wb
        for cid in e.new_state()['careers']:
            with self.subTest(career=cid):
                s,c,employee=WorkplaceBusinessTests().sample(cid);s['current']=cid
                offers=pst.offers(s,cid);offer=next(x for x in offers if x.get('staffed'))
                old=copy.deepcopy(c['tasks']);cash=c['money']
                with unittest.mock.patch.object(wb.time,'time',return_value=2000000000):
                    oid=pst.accept(s,cid,dict(id='staff-'+cid,offer_id=offer['offer_id'],buyer=BUYER,note='',price=offer['price']))
                row=c['player_service_jobs'][0]
                self.assertLess(c['money'],cash)
                self.assertEqual(c['tasks'],old)
                before=copy.deepcopy(s);at=row['due_at']
                wb.settle(s,at-1);self.assertEqual(row['status'],'queued')
                cash=c['money'];wb.settle(s,at)
                self.assertEqual(row['status'],'completed');self.assertEqual(c['money'],cash)
                self.assertEqual(pst.transitions(before,s,cid,'business_sync',{}),[dict(id=oid,status='completed')])
                self.assertEqual(c['ops']['business']['served'],0)
                e.validate_career(c,cid)

    def test_staff_pause_resume_has_no_backpay_and_does_not_poll_write(self):
        from tests.test_workplace_business import WorkplaceBusinessTests
        from game import workplace_business as wb
        s,c,employee=WorkplaceBusinessTests().sample();s['current']='mother_baby'
        before=copy.deepcopy(s);offer=pst.staff_offers(s,'accounting')[0];self.assertEqual(s,before)
        with unittest.mock.patch.object(wb.time,'time',return_value=2000000000):
            pst.accept(s,'accounting',dict(id='pause-staff',offer_id=offer['offer_id'],buyer=BUYER,note='',price=offer['price']))
        row=c['player_service_jobs'][0];employee['on_shift']=False
        wb.settle(s,2000010000);self.assertEqual(row['status'],'queued');self.assertIsNone(row['due_at'])
        self.assertFalse(wb.due(s,2000010001))
        employee['on_shift']=True;wb.settle(s,2000020000)
        self.assertGreater(row['due_at'],2000020000)
        wb.settle(s,row['due_at']);self.assertEqual(row['status'],'completed')
        pst.acknowledge(s,row['id']);self.assertTrue(row['settled'])

    def test_career_staff_accepts_and_serves_player_after_owner_closes(self):
        from tests.test_workplace_business import WorkplaceBusinessTests
        from game import workplace_business as wb
        s,c,employee=WorkplaceBusinessTests().sample();s['current']='mother_baby';c['open']=False
        before=copy.deepcopy(s);offers=pst.staff_offers(s,'accounting');self.assertEqual(s,before);self.assertTrue(offers)
        offer=offers[0]
        with unittest.mock.patch.object(wb.time,'time',return_value=2000000000):
            pst.accept(s,'accounting',dict(id='closed-staff',offer_id=offer['offer_id'],buyer=BUYER,note='',price=offer['price']))
        row=c['player_service_jobs'][0];cash=c['money'];at=row['due_at']
        self.assertTrue(pst.staff_working(c));self.assertTrue(pst.staff_due(c,at))
        wb.settle(s,at);self.assertEqual(row['status'],'completed');self.assertEqual(c['money'],cash,'fulfillment does not mint customer payment')
        self.assertEqual(row['price'],offer['price']);self.assertEqual(c['ops']['business']['served'],0)

    def test_paid_staff_bonus_uses_exact_costs_once_and_rejects_unfinished(self):
        from tests.test_workplace_business import WorkplaceBusinessTests
        from game import workplace_business as wb
        s,c,employee=WorkplaceBusinessTests().sample('mother_baby');offer=pst.staff_offers(s,'mother_baby')[0]
        with unittest.mock.patch.object(wb.time,'time',return_value=2000000000):
            pst.accept(s,'mother_baby',dict(id='paid-staff',offer_id=offer['offer_id'],buyer=BUYER,note='',price=offer['price']))
        row=c['player_service_jobs'][0];before=copy.deepcopy(s)
        with self.assertRaises(e.GameError):pst.credit_staff_bonus(s,'mother_baby',row['id'],row['price'])
        self.assertEqual(s,before)
        wb.settle(s,row['due_at']);cash=c['money'];stock=copy.deepcopy(c['stock']);revenue=c['ops']['finance']['period_revenue']
        margin=max(0,row['price']-row['wage']-row['materials']-row['goods']);bonus=margin*40//100
        self.assertGreater(row['goods'],0)
        self.assertEqual(pst.credit_staff_bonus(s,'mother_baby',row['id'],row['price']),bonus)
        self.assertEqual(c['money'],cash+bonus);self.assertEqual(c['stock'],stock)
        self.assertEqual(c['ops']['finance']['period_revenue'],revenue)
        self.assertEqual(wb.public(c)['profit_bonus'],0);self.assertEqual(wb.public(c)['visitor_profit_bonus'],bonus)
        before=copy.deepcopy(s);self.assertEqual(pst.credit_staff_bonus(s,'mother_baby',row['id'],row['price']),0);self.assertEqual(s,before)
        pst.acknowledge(s,row['id']);before=copy.deepcopy(s)
        self.assertEqual(pst.credit_staff_bonus(s,'mother_baby',row['id'],row['price']),0);self.assertEqual(s,before)
        e.validate_career(c,'mother_baby')
        row['settled']=False;row['status']='cancelled'
        with self.assertRaises(e.GameError):pst.credit_staff_bonus(s,'mother_baby',row['id'],row['price'])

    def test_legacy_closed_career_staff_job_reanchors_before_fulfillment(self):
        from tests.test_workplace_business import WorkplaceBusinessTests
        from game import workplace_business as wb
        s,c,employee=WorkplaceBusinessTests().sample();s['current']='mother_baby';offer=pst.staff_offers(s,'accounting')[0]
        with unittest.mock.patch.object(wb.time,'time',return_value=2000000000):
            pst.accept(s,'accounting',dict(id='legacy-staff',offer_id=offer['offer_id'],buyer=BUYER,note='',price=offer['price']))
        c['open']=False;c['ops'].pop('business_profit',None);c['ops']['business']['reason']='closed'
        row=c['player_service_jobs'][0];now=2000010000
        pst.settle_staff(c,'accounting',now)
        self.assertEqual(row['status'],'queued');self.assertGreater(row['due_at'],now)

    def test_quay_real_payment_once_tax_and_no_double_stock(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb,quay_self as qs
        s,st=fixture(staff=False);qb.settle(s,now=1000);dish=next(iter(st['business']['stock']))
        price=qs.price(st,dish);pst.accept_visit(s,'q1',dict(id='pay-quay',offer_id=dish,items=[dish],price=price,buyer=BUYER,note=''),now=1000)
        pst.serve_visit(st,dict(stall='q1',visitor_id='pay-quay',items=[dish],change=0,smile=True))
        stock=copy.deepcopy(st['business']['stock']);cash=st['till']+st['fund']
        net=pst.credit_visit(s,'q1','pay-quay',price)
        bonus=(net-qb.unit_cost(st,dish))*40//100
        self.assertEqual(st['business']['profit_boost']['total'],bonus)
        self.assertEqual(st['fund']+st['till'],cash+net+bonus)
        self.assertEqual(st['business']['stock'],stock)
        self.assertEqual(st['business']['sold'],1)
        with self.assertRaises(e.GameError):pst.credit_visit(s,'q1','pay-quay',price)
        qb.validate(st,lambda ok,*args:e.need(ok,'invalid'),lambda v,lo,hi:type(v)is int and lo<=v<=hi)

    def test_quay_no_cash_cannot_complete_reserved_visitor_order(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb,quay_self as qs
        s,st=fixture();qb.settle(s,now=1000);dish=next(iter(st['business']['stock']))
        pst.accept_visit(s,'q1',dict(id='poor-quay',offer_id=dish,items=[dish],price=qs.price(st,dish),buyer=BUYER,note=''),now=1000)
        st['fund']=st['till']=0;qb.settle(s,now=100000)
        row=st['business']['visitor_orders'][0]
        self.assertEqual(row['status'],'queued');self.assertIsNone(row['due_at'])
        st['fund']=100;qb.settle(s,now=100001)
        self.assertGreater(row['due_at'],100001000)

    def test_refused_task_completion_cancels_player_payment(self):
        j=Journey('mother_baby',slot=0);bound(j.task);before=copy.deepcopy(j.state)
        j.task.update(status='completed',reaction=dict(kind='walkout',cut=30,line='',day=1))
        self.assertEqual(pst.transitions(before,j.state,j.career,'shop_deliver',{}),[dict(id='order-test',status='cancelled')])

    def test_homestay_catalog_avoids_future_npc_booking_receipts(self):
        from game.careers import homestay
        j=Journey('homestay');offer=pst.offers(j.state,j.career)[0]
        task=homestay.make_task(offer['day'],offer['slot'],j.c['turn'])
        self.assertNotEqual(task['job'],'booking')

    def test_quay_visitor_does_not_rewind_cursor_on_clock_rollback(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb,quay_self as qs
        s,st=fixture();qb.settle(s,now=3000);dish=next(iter(st['business']['stock']))
        pst.accept_visit(s,'q1',dict(id='clock-quay',offer_id=dish,items=[dish],price=qs.price(st,dish),buyer=BUYER,note=''),now=3000)
        before=copy.deepcopy(s);self.assertFalse(qb.settle(s,now=2900));self.assertEqual(s,before)

    def test_import_scrubs_service_claims_without_minting_inventory_or_money(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb,quay_self as qs
        j=Journey('mother_baby',slot=0);bound(j.task)
        j.c['player_service_jobs']=[{'id':'old-imported-claim'}]
        s,st=fixture(staff=False);qb.settle(s,now=1000);dish=next(iter(st['business']['stock']))
        pst.accept_visit(s,'q1',dict(id='import-quay',offer_id=dish,items=[dish],price=qs.price(st,dish),buyer=BUYER,note=''),now=1000)
        j.state['journey']['quay']=s['journey']['quay'];stock=copy.deepcopy(st['business']['stock']);cash=j.c['money']
        pst.scrub_import(j.state)
        self.assertNotIn('player_order',j.task);self.assertNotIn('player_service_jobs',j.c)
        self.assertNotIn('visitor_orders',st['business'])
        self.assertEqual(st['business']['stock'],stock);self.assertEqual(j.c['money'],cash)
        self.assertFalse(pst.scrub_import(j.state))

    def test_refund_ack_restores_only_unserved_quay_reservation_once(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb,quay_self as qs
        s,st=fixture(staff=False);qb.settle(s,now=1000);dish=next(iter(st['business']['stock']));qty=st['business']['stock'][dish]
        pst.accept_visit(s,'q1',dict(id='cancel-quay',offer_id=dish,items=[dish],price=qs.price(st,dish),buyer=BUYER,note=''),now=1000)
        pst.acknowledge(s,'cancel-quay',outcome='cancelled')
        self.assertEqual(st['business']['stock'][dish],qty)
        row=st['business']['visitor_orders'][0];self.assertEqual(row['status'],'cancelled');self.assertTrue(row['settled'])
        pst.acknowledge(s,'cancel-quay',outcome='cancelled');self.assertEqual(st['business']['stock'][dish],qty)

    def test_optional_visitor_avatar_is_valid_and_public(self):
        j=Journey('mother_baby',slot=0);bound(j.task);j.task['player_order']['buyer']['av']='🐱'
        e.validate_state(j.state)
        self.assertEqual(e.task_view(j.task)['player_order']['buyer']['av'],'🐱')

    def test_staffed_quay_needs_local_funds_before_reserving_customer_goods(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb,quay_self as qs
        s,st=fixture();qb.settle(s,now=1000);dish=next(iter(st['business']['stock']))
        st['fund']=st['till']=0;stock=copy.deepcopy(st['business']['stock'])
        order=dict(id='cannot-prep',offer_id=dish,items=[dish],price=qs.price(st,dish),buyer=BUYER,note='')
        with self.assertRaises(e.GameError):pst.accept_visit(s,'q1',order,now=1000)
        self.assertEqual(st['business']['stock'],stock)
        st['staff']=[];pst.accept_visit(s,'q1',order,now=1000)
        self.assertEqual(st['business']['stock'][dish],stock[dish]-1)
