import copy
import unittest
from unittest.mock import patch
from game import traffic
from game.careers import kit
from game.engine import GameError
from tests.helpers import Journey


class Traffic(unittest.TestCase):
    def setUp(self):
        self.old=kit.clock;self.time=1001.0;kit.clock=lambda:self.time
    def tearDown(self):kit.clock=self.old

    def test_approach_and_wait_are_free_red_cross_is_once(self):
        d=traffic.fresh()
        ch=traffic.issue(d,'leg-1:3,2',0,'y')
        self.assertEqual(traffic.signal(ch),'red')
        self.assertEqual(d['receipts'],[])
        receipt=traffic.cross(d,ch['token'])
        self.assertEqual(receipt['fine'],12)
        self.assertTrue(traffic.cross(d,ch['token'])['duplicate'])
        self.assertEqual(len(d['receipts']),1)
        traffic.validate(d)

    def test_green_and_yellow_cross_no_fine(self):
        for sec in (1008,1014):
            self.time=sec;d=traffic.fresh();ch=traffic.issue(d,'leg-1',0,'y')
            self.assertEqual(traffic.cross(d,ch['token'])['fine'],0)

    def test_client_cannot_choose_signal_time_amount_or_replay_old_token(self):
        d=traffic.fresh();ch=traffic.issue(d,'one',0,'y');old=ch['token']
        with self.assertRaises(GameError):traffic.cross(d,'forged')
        traffic.issue(d,'two',0,'x')
        with self.assertRaises(GameError):traffic.cross(d,old)
        self.assertEqual(d['receipts'],[])

    def test_server_clock_changes_signal_while_stopped(self):
        d=traffic.fresh();ch=traffic.issue(d,'one',0,'y')
        self.time=1008
        self.assertEqual(traffic.signal(ch),'green')
        self.assertEqual(traffic.cross(d,ch['token'])['fine'],0)

    def test_same_crossing_cannot_fine_again_after_another_signal(self):
        d=traffic.fresh();ch=traffic.issue(d,'one',0,'y');traffic.cross(d,ch['token'])
        traffic.issue(d,'two',0,'y')
        ch=traffic.issue(d,'one',0,'y')
        self.assertTrue(traffic.cross(d,ch['token'])['duplicate'])
        self.assertEqual(sum(x['fine'] for x in d['receipts']),12)

    def test_server_red_boundary_grace_is_one_second_and_receipted(self):
        for axis,red_at in [('y',1000),('x',1008)]:
            for delta,expected in [(0,0),(.999,0),(1,12),(7.9,12)]:
                self.time=red_at+delta;d=traffic.fresh();ch=traffic.issue(d,'light',0,axis)
                r=traffic.cross(d,ch['token'])
                self.assertEqual(r['fine'],expected)
                self.assertEqual(r['grace'],delta<1)
                traffic.validate(d)

    def test_delivery_zero_or_partial_funds_become_one_traffic_invoice(self):
        from game.engine import validate_state
        for available in (0,5):
            j=Journey('delivery')
            kit.money(j.state,j.c,available-j.c['money'],'Test balance')
            wallet=j.state['journey']['wallet']
            r=j.act('dl_signal',target='gas',i=3,j=2,axis='y')
            token=r['traffic']['challenge']['token'];self.time=1056+10-11
            r=j.act('dl_cross',target='gas',token=token)
            self.assertEqual(j.c['money'],0)
            self.assertEqual(j.state['journey']['wallet'],wallet)
            bills=[b for b in j.c['ops']['finance']['bills'] if b['source']==token]
            self.assertEqual(len(bills),1);self.assertEqual(bills[0]['amount'],12-available)
            self.assertEqual(bills[0]['kind'],'fine')
            self.assertIn('Vượt đèn đỏ',bills[0]['label'])
            j.act('dl_cross',target='gas',token=token)
            self.assertEqual(len([b for b in j.c['ops']['finance']['bills'] if b['source']==token]),1)
            kit.money(j.state,j.c,12-available,'Test refill')
            j.act('ops_pay_bill',bill=bills[0]['id'],confirm=True)
            fine_rows=[r for r in j.c['ops']['finance']['ledger'] if r['category']=='fine']
            self.assertEqual(-sum(r['amount'] for r in fine_rows),12)
            self.assertEqual(j.c['money'],0)
            with self.assertRaises(GameError):j.act('ops_pay_bill',bill=bills[0]['id'],confirm=True)
            validate_state(j.state)

    def test_delivery_validates_leg_and_posts_one_fine_receipt(self):
        from game.careers import delivery as dl
        j=Journey('delivery')
        # Choose a leg whose valid corridor contains a real lit intersection.
        start=dl.NODES[j.c['ext']['data']['at']]
        target=next(k for k,n in dl.NODES.items() if k!=j.c['ext']['data']['at'] and
                    abs(start['x']-3)+abs(start['y']-2)+abs(n['x']-3)+abs(n['y']-2)<=abs(start['x']-n['x'])+abs(start['y']-n['y'])+2)
        with self.assertRaises(GameError):j.act('dl_cross',target=target,token='fake',fine=0)
        turn=j.c['turn'];money=j.c['money']
        r=j.act('dl_signal',target=target,i=3,j=2,axis='y')
        self.assertEqual(j.c['turn'],turn)
        self.assertEqual(j.c['money'],money)
        token=r['traffic']['challenge']['token'];offset=(3*7+2*3)%16
        self.time=1024+9-offset
        r=j.act('dl_cross',target=target,token=token)
        self.assertEqual(j.c['money'],money-12)
        self.assertEqual(r['receipt']['signal'],'red')
        j.act('dl_cross',target=target,token=token)
        self.assertEqual(j.c['money'],money-12)
        rows=[x for x in j.c['ops']['finance']['ledger'] if x['ref']=='traffic-'+token]
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['category'],'fine')

    def test_counter_closing_before_first_delivery_keeps_traffic_receipt(self):
        from tests.test_quay import opened,ST,act
        s=opened('xe',staff=False);sid=ST(s)['id'];wallet=s['journey']['wallet']
        s,_=act(s,'jr_quay_online',stall=sid,on=True)
        s,_=act(s,'jr_quay_start',stall=sid)
        clock_patch=patch('game.quay_business.time.time',return_value=ST(s)['run']['order_data']['0']['available_at']/1000)
        clock_patch.start();self.addCleanup(clock_patch.stop)
        s,r=act(s,'jr_quay_signal',stall=sid,order=0)
        ch=r['traffic']['challenge'];self.time=1120+10-ch['offset']
        s,_=act(s,'jr_quay_cross',stall=sid,order=0,turn='S',token=ch['token'])
        paid=ST(s)['business']['expenses']['loss']
        self.assertEqual(paid,12)
        s,_=act(s,'jr_quay_close',stall=sid)
        self.assertIsNotNone(ST(s)['run'])
        self.assertTrue(ST(s)['run']['x'])
        self.assertEqual(ST(s)['run']['rides']['0']['traffic']['receipts'][0]['fine'],12)
        self.assertEqual(s['journey']['wallet'],wallet)
        self.assertEqual(ST(s)['business']['expenses']['loss'],paid)
        self.assertEqual(ST(s)['run']['sum']['auto'],0)

    def test_counter_crossings_are_ordered_resume_and_charge_shift_once(self):
        from tests.test_quay import opened,ST,act
        from game import quay_self as qs
        s=opened('xe',staff=False);sid=ST(s)['id']
        s,_=act(s,'jr_quay_online',stall=sid,on=True)
        s,_=act(s,'jr_quay_start',stall=sid)
        run=ST(s)['run'];order=qs.order(s,ST(s),run,0);cost=run['m']
        clock_patch=patch('game.quay_business.time.time',return_value=order['available_at']/1000)
        clock_patch.start();self.addCleanup(clock_patch.stop)
        with self.assertRaises(GameError):act(s,'jr_quay_cross',stall=sid,order=0,turn='L',token='fake')
        for step,turn in enumerate(order['route']):
            s,r=act(s,'jr_quay_signal',stall=sid,order=0)
            ch=r['traffic']['challenge'];self.time=1104+9-ch['offset']
            s,r=act(s,'jr_quay_cross',stall=sid,order=0,turn=turn,token=ch['token'])
            self.assertEqual(len(r['picks']),step+1)
            s,r=act(s,'jr_quay_cross',stall=sid,order=0,turn=turn,token=ch['token'])
            self.assertTrue(r['receipt']['duplicate'])
        self.assertEqual(ST(s)['run']['m'],cost-36)
        s,r=act(s,'jr_quay_signal',stall=sid,order=0)
        self.assertEqual(r['picks'],order['route'])
        s,_=act(s,'jr_quay_ship',stall=sid,order=0,items=order['items'],seal=True,tool=order['tool'],note=order['sticker'],way='self',route=r['picks'])
        self.assertEqual(ST(s)['business']['sold'],1)
        self.assertNotEqual(qs.order(s,ST(s),ST(s)['run'],0)['id'],order['id'])
        self.assertEqual(ST(s)['run']['on'][0],0)

    def test_counter_unpaid_fine_survives_close_and_uses_sales_then_local_funding(self):
        from tests.test_quay import opened,ST,act
        from tests.test_quay_self import serve_well
        s=opened('xe',staff=False);sid=ST(s)['id'];wallet=s['journey']['wallet']
        s,_=act(s,'jr_quay_online',stall=sid,on=True)
        s,_=act(s,'jr_quay_start',stall=sid)
        ST(s)['fund']=ST(s)['till']=0
        clock_patch=patch('game.quay_business.time.time',return_value=ST(s)['run']['order_data']['0']['available_at']/1000)
        clock_patch.start();self.addCleanup(clock_patch.stop)
        s,r=act(s,'jr_quay_signal',stall=sid,order=0)
        ch=r['traffic']['challenge'];self.time=1120+10-ch['offset']
        s,_=act(s,'jr_quay_cross',stall=sid,order=0,turn='S',token=ch['token'])
        self.assertEqual(ST(s)['business'].get('unpaid_fines'),12)
        from game import quay as qy, quay_business as qb
        self.assertEqual(qy.sell_back(ST(s)),qy.PLACES['xe']['price']//2-12)
        self.assertEqual(qb.public(ST(s))['unpaid_fines'],12)
        s,_=serve_well(s)
        unpaid=ST(s)['business']['unpaid_fines']
        self.assertGreater(unpaid,0)
        self.assertEqual(ST(s)['till']+ST(s)['fund'],0)
        self.assertEqual(ST(s)['business']['expenses']['loss']+unpaid,12)
        s,_=act(s,'jr_quay_close',stall=sid)
        self.assertEqual(ST(s)['business']['unpaid_fines'],unpaid)
        self.assertEqual(s['journey']['wallet'],wallet)
        s,_=act(s,'jr_quay_fund',stall=sid,amount=20)
        self.assertEqual(ST(s)['business']['unpaid_fines'],0)
        self.assertEqual(ST(s)['business']['expenses']['loss'],12)
        self.assertEqual(ST(s)['fund']+ST(s)['till'],20-unpaid)
        s,_=act(s,'jr_quay_fund',stall=sid,amount=10)
        self.assertEqual(ST(s)['business']['expenses']['loss'],12)


if __name__=='__main__':unittest.main()
