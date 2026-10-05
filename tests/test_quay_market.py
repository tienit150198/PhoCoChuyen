import copy
import unittest
from unittest.mock import patch

from game import quay_business as qb, quay_self as qs, quay
from game.engine import GameError
from tests.test_quay_business import fixture


class MarketEconomy(unittest.TestCase):
    def test_closed_persists_and_reopen_does_not_replay(self):
        s, st = fixture(); qb.settle(s, now=1000)
        qb.action(s, st, 'jr_quay_pause', dict(on=True))
        old = copy.deepcopy(st['business'])
        qb.settle(s, now=50000)
        self.assertTrue(st['business']['paused'])
        self.assertEqual(st['business']['sold'], old['sold'])
        self.assertEqual(st['business']['expenses'], old['expenses'])
        qb.action(s, st, 'jr_quay_pause', dict(on=False))
        qb.settle(s, now=50001)
        self.assertEqual(st['business']['sold'], old['sold'])

    def test_epoch_polling_matches_offline_with_protection(self):
        s, st = fixture(); qb.settle(s, now=1000)
        st['business']['stock'] = {d:1000 for d in qs.menu(st)['on']}
        qb.action(s, st, 'jr_quay_protection', dict(level='premium'))
        offline = copy.deepcopy(s)
        for at in range(1001, 12001, 17): qb.settle(s, now=at)
        qb.settle(s, now=12000); qb.settle(offline, now=12000)
        self.assertEqual(s, offline)
        self.assertGreater(st['business']['expenses']['environment'], 0)
        self.assertGreater(st['business']['expenses']['protection'], 0)

    def test_market_has_severe_downturn_and_boom_and_keeps_price(self):
        from game import quay_market as market
        factors = [market.snapshot(n * market.EPOCH_MS)['demand_factor'] for n in range(100)]
        self.assertTrue(any(.25 <= f <= .5 for f in factors))
        self.assertTrue(any(1.5 <= f <= 1.8 for f in factors))
        s, st = fixture(); st['menu'] = dict(on=['hong_tra'], p={'hong_tra':19})
        qb.settle(s, now=1000); qb.settle(s, now=20000)
        self.assertEqual(qs.price(st, 'hong_tra'), 19)

    def test_income_tax_uses_positive_margin_and_keeps_legacy_tax(self):
        s, st = fixture(staff=False); qb.settle(s, now=1000)
        st['business']['stock']['hong_tra'] = 20
        st['business']['expenses']['tax'] = 13
        cost = qb.unit_cost(st, 'hong_tra')
        qb.sale(st, ['hong_tra'], 1000000, total=cost - 1)
        self.assertEqual(st['business']['expenses']['income_tax'], 0)
        qb.sale(st, ['hong_tra'], 1000000, total=cost + 101)
        self.assertEqual(st['business']['expenses']['income_tax'], 7)
        self.assertEqual(st['business']['expenses']['tax'], 13)

    def test_closed_accepted_visitor_finishes_but_new_visit_rejected(self):
        from game import player_service_tasks as pst
        from tests.test_player_service_tasks import BUYER
        s, st = fixture(); qb.settle(s, now=1000)
        dish = next(iter(st['business']['stock']))
        order = dict(id='first', offer_id=dish, items=[dish], price=qs.price(st,dish), buyer=BUYER, note='')
        pst.accept_visit(s, st['id'], order, now=1000)
        qb.action(s, st, 'jr_quay_pause', dict(on=True))
        qb.settle(s, now=1040)
        self.assertEqual(st['business']['visitor_orders'][0]['status'], 'completed')
        self.assertEqual(st['business']['sold'], 0)
        with self.assertRaises(GameError): pst.accept_visit(s, st['id'], dict(order, id='second'), now=1040)

    def test_legacy_expense_shape_migrates_without_unpausing_or_recharging(self):
        s, st = fixture(); qb.settle(s, now=1000)
        b = st['business']; b['paused'] = True
        for k in ('income_tax','environment','protection'): b['expenses'].pop(k, None); b['carry'].pop(k, None)
        for k in ('income_tax','protection','market_epoch'): b.pop(k, None)
        before = st['fund'] + st['till']
        qb.settle(s, now=3000)
        self.assertTrue(b['paused'])
        self.assertEqual(st['fund'] + st['till'], before)
        self.assertIn('income_tax', b['expenses'])

    def test_boom_produces_materially_more_real_receipts(self):
        from game import quay_market as market
        epochs = [market.snapshot(i * market.EPOCH_MS) for i in range(100)]
        volumes = []
        for state in ('downturn', 'boom'):
            epoch = next(e for e in epochs if e['state'] == state)
            s, st = fixture(); start = epoch['starts_at'] + 1
            qb.settle(s, now=start)
            st['business']['stock'] = {d:1000 for d in qs.menu(st)['on']}
            qb.settle(s, now=start + 600)
            volumes.append(st['business']['sold'])
        self.assertGreater(volumes[1], volumes[0] * 2)

    def test_manual_closed_queue_drains_then_reopens_without_new_backlog(self):
        from tests.test_quay import opened, ST, act
        from game.engine import validate_state
        with patch.object(qb.time, 'time', return_value=1000):
            s=opened(staff=False); st=ST(s)
            st['business']['stock']={d:100 for d in qs.menu(st)['on']}
            s,_=act(s,'jr_quay_start',stall=st['id'])
        st=ST(s); qb.settle(s,now=1030)
        qb.action(s,st,'jr_quay_pause',dict(on=True))
        before=copy.deepcopy(st['run']['crowd'])
        qb.settle(s,now=50000)
        self.assertEqual(st['run']['crowd'],before)
        self.assertFalse(qb.due(s,now=50001))
        accepted=1+len(before['waiting'])
        for _ in range(accepted):
            c=qs.run_view(s,st)['cust']
            qs.action(s,'jr_quay_serve',dict(items=c['items'],change=c['pay']-c['total'],smile=True),st)
        self.assertNotIn('cust',qs.run_view(s,st))
        c=st['run']['current']
        with self.assertRaises(GameError):
            qs.action(s,'jr_quay_serve',dict(items=c['items'],change=c['pay']-c['total'],smile=True),st)
        qb.action(s,st,'jr_quay_pause',dict(on=False))
        self.assertGreater(st['run']['next_at'],st['business']['cursor'])
        validate_state(s)

    def test_small_expense_carry_survives_close_and_plan_switch(self):
        s,st=fixture(staff=False); s['journey']['wallet']=0; st.update(fund=1000,till=0); qb.settle(s,now=1000)
        qb.action(s,st,'jr_quay_protection',dict(level='premium'))
        wallet=s['journey']['wallet']
        qb._charge(st, qb.DEN//14)
        carry=st['business']['carry']['protection']
        qb.action(s,st,'jr_quay_pause',dict(on=True))
        qb.action(s,st,'jr_quay_protection',dict(level='none'))
        qb.settle(s,now=20000)
        self.assertEqual(st['business']['carry']['protection'],carry)
        qb.action(s,st,'jr_quay_pause',dict(on=False))
        qb.action(s,st,'jr_quay_protection',dict(level='premium'))
        qb._charge(st, qb.DEN//14+1)
        self.assertEqual(st['business']['expenses']['protection'],1)
        self.assertEqual(s['journey']['wallet'],wallet)

    def test_accepted_quote_keeps_price_and_tax_receipt_is_once(self):
        from game import player_service_tasks as pst
        from tests.test_player_service_tasks import BUYER
        s,st=fixture(staff=False); qb.settle(s,now=1000)
        dish='hong_tra'; price=100
        st['menu']=dict(on=[dish],p={dish:price})
        pst.accept_visit(s,st['id'],dict(id='quote',offer_id=dish,items=[dish],price=price,buyer=BUYER,note=''),now=1000)
        st['menu']['p'][dish]=1000
        qb.action(s,st,'jr_quay_pause',dict(on=True))
        pst.serve_visit(st,dict(visitor_id='quote',items=[dish],change=0,smile=True))
        with patch.object(qb.time,'time',return_value=1000):
            pst.credit_visit(s,st['id'],'quote',price)
            tax=st['business']['expenses']['income_tax']
            self.assertEqual(tax,(price-qb.unit_cost(st,dish))*7//100)
            self.assertEqual(st['business']['expenses']['tax'],0)
            with self.assertRaises(GameError):pst.credit_visit(s,st['id'],'quote',price)
            self.assertEqual(st['business']['expenses']['income_tax'],tax)

    def test_npc_review_names_server_and_public_does_not_mutate(self):
        s,st=fixture();qb.settle(s,now=1000);qb.settle(s,now=1600)
        rows=st['business']['recent'];self.assertTrue(rows)
        self.assertTrue(all(r['employee']==st['staff'][0]['id'] and r['name']==st['staff'][0]['name'] and r['text'] for r in rows))
        snapshot=copy.deepcopy(s);qb.public(st)
        self.assertEqual(s,snapshot)

    def test_extreme_price_large_fund_offline_skips_empty_epochs(self):
        s,st=fixture();st['fund']=quay.MONEY_MAX
        st['menu']=dict(on=['hong_tra'],p={'hong_tra':1000000})
        qb.settle(s,now=1000)
        original=qb._intervals; calls=[]
        def counted(stall):
            calls.append(1)
            self.assertLess(len(calls),100,'Empty market epochs must be skipped arithmetically')
            return original(stall)
        with patch.object(qb,'_intervals',side_effect=counted):qb.settle(s,now=1000+10**10)
        self.assertEqual(st['business']['sold'],0)
        self.assertGreaterEqual(st['fund'],0)

    def test_market_calendar_inverse_matches_each_boundary_and_large_gap(self):
        from game import quay_market as market
        for start in (0, market.EPOCH_MS-1, market.EPOCH_MS, 47*market.EPOCH_MS+1, 10**14):
            for delay in (1, 1001, market.EPOCH_MS, 10**18):
                target=market.demand_clock(start)+delay*100
                end=market.advance(start,delay)
                self.assertGreaterEqual(market.demand_clock(end),target)
                self.assertLess(market.demand_clock(end-1),target)
        expected=sum(round(market.snapshot(i*market.EPOCH_MS)['demand_factor']*100)*market.EPOCH_MS for i in range(120))
        self.assertEqual(market.demand_clock(120*market.EPOCH_MS),expected)
