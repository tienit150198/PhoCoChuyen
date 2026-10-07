import copy
import unittest
from game import quay, quay_self
from tests.test_quay import bare


def fixture(place='xe', trade='milk_tea', staff=True):
    s, st = bare(place, trade)
    s['journey']['quay'] = dict(v=1, seq=1, stalls=[st], shift=None, out=[])
    if not staff:
        st['staff'] = []
    return s, st


class ContinuousBusiness(unittest.TestCase):
    def test_polling_equals_offline_and_idempotent(self):
        from game import quay_business as b
        s, st = fixture()
        b.settle(s, now=1000)
        other = copy.deepcopy(s)
        for t in range(1001, 4601):
            b.settle(s, now=t)
        b.settle(other, now=4600)
        self.assertEqual(s, other)
        self.assertFalse(b.settle(s, now=4600))

    def test_no_staff_no_auto_sales(self):
        from game import quay_business as b
        s, st = fixture(staff=False)
        b.settle(s, now=1000)
        cash = st['fund'] + st['till']
        b.settle(s, now=100000)
        self.assertEqual(st['business']['sold'], 0)
        self.assertEqual(st['fund'] + st['till'], cash)

    def test_stock_finite_and_no_life_day_double_pay(self):
        from game import quay_business as b
        s, st = fixture()
        b.settle(s, now=1000)
        stock = sum(st['business']['stock'].values())
        b.settle(s, now=100000000)
        self.assertLessEqual(st['business']['sold'], stock)
        cash = st['till'] + st['fund']
        s['journey']['life_day'] += 1
        quay.on_life_day(s)
        self.assertEqual(st['till'] + st['fund'], cash)

    def test_full_catalogue_and_extreme_price_demand(self):
        from game import quay_business as b
        for trade in quay.TRADE_IDS:
            self.assertGreaterEqual(len(quay_self.MENUS[trade]), 12)
            s, st = fixture(trade=trade)
            dish = quay_self.MENUS[trade][0][0]
            base = quay_self.DISH[trade][dish]['base']
            self.assertGreater(b.demand(base, base), b.demand(base, base * 3))
            self.assertLess(b.demand(base, 1000000) * 1000000, b.demand(base, base) * base)

    def test_manual_close_books_no_unserved_sales(self):
        from tests.test_quay import opened, ST, act
        s = opened(staff=False)
        sid = ST(s)['id']
        s, _ = act(s, 'jr_quay_start', stall=sid)
        st = ST(s)
        c = quay_self.customer(s, st, st['run'], 0)
        s, _ = act(s, 'jr_quay_serve', stall=sid, items=c['items'], change=c['pay']-c['total'], smile=True)
        sold = ST(s)['business']['sold']
        cash = ST(s)['fund'] + ST(s)['till']
        s, _ = act(s, 'jr_quay_close', stall=sid)
        self.assertEqual(ST(s)['business']['sold'], sold)
        self.assertEqual(ST(s)['fund'] + ST(s)['till'], cash)
        self.assertEqual(ST(s)['run']['sum']['auto'], 0)
        s, _ = act(s, 'jr_quay_start', stall=sid)
        self.assertFalse(ST(s)['run']['x'])

    def test_low_funds_polling_matches_offline_and_refill(self):
        from game import quay_business as b
        s, st = fixture()
        b.settle(s, now=1000)
        st['fund'], st['till'] = 2, 0
        other = copy.deepcopy(s)
        for t in range(1001, 1101):
            b.settle(s, now=t)
        b.settle(other, now=1100)
        self.assertEqual(s, other)

    def test_manual_reopen_cannot_bypass_arrivals(self):
        from tests.test_quay import opened, ST, act
        from game.engine import GameError
        s = opened(staff=False)
        sid = ST(s)['id']
        s, _ = act(s, 'jr_quay_start', stall=sid)
        st = ST(s)
        c = quay_self.customer(s, st, st['run'], 0)
        s, _ = act(s, 'jr_quay_serve', stall=sid, items=c['items'], change=c['pay']-c['total'], smile=True)
        s, _ = act(s, 'jr_quay_close', stall=sid)
        s, _ = act(s, 'jr_quay_start', stall=sid)
        c = quay_self.customer(s, ST(s), ST(s)['run'], 0)
        with self.assertRaises(GameError):
            act(s, 'jr_quay_serve', stall=sid, items=c['items'], change=c['pay']-c['total'], smile=True)

    def test_all_trades_places_price_calibration(self):
        from game import quay_business as b
        for place in quay.PLACE_IDS:
            for trade in quay.TRADE_IDS:
                volumes, margins, ratings = [], [], []
                for pct in (75, 100, 200):
                    s, st = fixture(place, trade)
                    board = quay_self.menu(st)
                    st['menu'] = dict(on=board['on'], p={d:max(1,round(quay_self.DISH[trade][d]['base']*pct/100)) for d in board['on']})
                    b.settle(s, now=1000)
                    st['business']['stock'] = {d:1000 for d in board['on']}
                    b.settle(s, now=7000)
                    volumes.append(st['business']['sold'])
                    margins.append(sum(quay_self.price(st,d)-b.unit_cost(st,d) for d in board['on']) / len(board['on']))
                    ratings.append(quay_self.rating(st)[1])
                    self.assertGreaterEqual(st['fund'], 0)
                    self.assertGreaterEqual(st['till'], 0)
                self.assertGreater(volumes[0], volumes[1], (place,trade,volumes))
                self.assertGreater(volumes[1], volumes[2], (place,trade,volumes))
                self.assertLess(margins[0], margins[1], (place,trade,margins))
                self.assertGreater(ratings[0], ratings[2], (place,trade,ratings))

    def test_old_config_is_settled_before_price_change(self):
        from game import quay_business as b
        from unittest.mock import patch
        s, st = fixture()
        b.settle(s, now=1000)
        expected = copy.deepcopy(s)
        b.settle(expected, now=1500)
        with patch.object(b.time, 'time', return_value=1500):
            quay.action(s,'jr_quay_menu',dict(stall='q1',on=quay_self.menu(st)['on'],p={'hong_tra':1000000}))
        self.assertEqual(st['business']['revenue'], expected['journey']['quay']['stalls'][0]['business']['revenue'])

    def test_public_projection_does_not_settle_or_mutate(self):
        from game import quay_business as b
        s, st = fixture()
        b.settle(s, now=1000)
        before = copy.deepcopy(s)
        view = b.public(st)
        view['expenses']['wages'] += 100
        self.assertEqual(s, before)

    def test_income_estimate_matches_a_real_day_and_is_read_only(self):
        """#19: the stall card's 'lãi 1 ngày' is what 24 h of settle() really books (stock and money to spare)."""
        from game import quay_business as b
        s, st = fixture('sap')
        b.settle(s, now=1000)
        bz = st['business']
        for d in b.qs.menu(st)['on']:
            bz['stock'][d] = 5000
        st['fund'] = 10**6
        bz['signature'] = ''
        b._schedule(st, bz['cursor'])
        snap = copy.deepcopy(s)
        inc = b.public(st)['income']
        self.assertEqual(s, snap)
        v0 = b.public(st)
        b.settle(s, now=bz['cursor'] // 1000 + 86400)
        v1 = b.public(st)
        goods = sum(b.unit_cost(st, d) * (5000 - bz['stock'][d]) for d in b.qs.menu(st)['on'])   # the shelf was free here
        self.assertAlmostEqual(inc['day']['sold'], v1['sold'] - v0['sold'], delta=0.02 * inc['day']['sold'] + 2)
        self.assertAlmostEqual(inc['day']['net'], v1['net'] - v0['net'] - goods, delta=0.02 * abs(inc['day']['net']) + 20)
        self.assertGreater(inc['hour']['sold'], 0)
        st['staff'] = []
        self.assertIsNone(b.public(st)['income'])

    def test_manual_customers_continue_past_six_and_save_stays_bounded(self):
        from tests.test_quay import opened, ST, act
        from tests.test_quay_self import serve_well
        from game import quay_business as b
        from unittest.mock import patch
        s = opened(staff=False)
        sid = ST(s)['id']
        s, _ = act(s,'jr_quay_fund',stall=sid,amount=400)
        s, _ = act(s,'jr_quay_restock',stall=sid,items={'ts_tran_chau':20,'hong_tra':20,'tra_dao':20})
        s, _ = act(s,'jr_quay_start',stall=sid)
        for _ in range(12):
            with patch.object(b.time,'time',return_value=ST(s)['run']['next_at']/1000):
                s, _ = serve_well(s)
        self.assertEqual(ST(s)['business']['sold'],12)
        self.assertEqual(ST(s)['run']['i'],12)
        self.assertLessEqual(len(ST(s)['business']['recent']),12)

    def test_extreme_manual_price_cannot_get_immediate_first_sale(self):
        from tests.test_quay import opened, ST, act
        from game.engine import GameError
        s=opened(staff=False);sid=ST(s)['id']
        s,_=act(s,'jr_quay_menu',stall=sid,on=['hong_tra'],p={'hong_tra':1000000})
        s,_=act(s,'jr_quay_start',stall=sid)
        c=quay_self.customer(s,ST(s),ST(s)['run'],0)
        with self.assertRaises(GameError):
            act(s,'jr_quay_serve',stall=sid,items=c['items'],change=0,smile=True)

    def test_restock_only_uses_business_cash_and_paused_time_never_replayed(self):
        from game import quay_business as b
        from unittest.mock import patch
        s,st=fixture()
        b.settle(s,now=1000)
        wallet=s['journey']['wallet'];cash=st['fund']+st['till']
        with patch.object(b.time,'time',return_value=1000):
            quay.action(s,'jr_quay_restock',dict(stall='q1',items={'hong_tra':10}))
            # Legacy saved pause resumes at migration time, with no backpay.
            st['business']['paused'] = True
            st['business'].pop('profit_boost', None)
        self.assertEqual(s['journey']['wallet'],wallet)
        self.assertEqual(st['fund']+st['till'],cash-10*b.unit_cost(st,'hong_tra'))
        b.settle(s,now=100000)
        self.assertEqual(st['business']['sold'],0)
        with patch.object(b.time,'time',return_value=100000):
            quay.action(s,'jr_quay_pause',dict(stall='q1',on=False))
        b.settle(s,now=100001)
        self.assertEqual(st['business']['sold'],0)

    def test_menu_removal_retains_stock_and_selling_never_liquidates_it_as_sales(self):
        from game import quay_business as b
        from unittest.mock import patch
        s,st=fixture()
        b.settle(s,now=1000)
        paid=copy.deepcopy(st['business']['stock'])
        with patch.object(b.time,'time',return_value=1000):
            quay.action(s,'jr_quay_menu',dict(stall='q1',on=['matcha']))
        b.settle(s,now=10000)
        self.assertEqual(st['business']['stock'],paid)
        self.assertEqual(st['business']['sold'],0)
        cash=st['fund']+st['till']
        self.assertEqual(quay.sell_back(st),quay.PLACES[st['place']]['price']//2+cash)
        with patch.object(b.time,'time',return_value=10000):
            quay.action(s,'jr_quay_menu',dict(stall='q1',on=list(paid)))
        b.settle(s,now=10600)
        self.assertGreater(st['business']['sold'],0)

    def test_wage_change_and_funding_resume_use_current_cursor(self):
        from game import quay_business as b
        from unittest.mock import patch
        s,st=fixture();b.settle(s,now=1000)
        st['fund'],st['till']=1,0
        b.settle(s,now=10000)
        self.assertEqual(b.status(st),'no_funds')
        before=st['business']['sold']
        with patch.object(b.time,'time',return_value=10000):
            quay.action(s,'jr_quay_fund',dict(stall='q1',amount=100))
        b.settle(s,now=10001)
        self.assertEqual(st['business']['sold'],before)
        self.assertEqual(b.status(st),'running')

    def test_delivery_gear_shortens_next_trip_cooldown_and_snapshots_current_order(self):
        from tests.test_quay import opened, ST, act
        from game import quay_business as b
        from unittest.mock import patch
        waits=[]
        for tier in (0,3):
            s=opened(staff=False);sid=ST(s)['id']
            s['careers']['delivery']['upgrades'] += [f'workgear_delivery_{n}' for n in range(1,tier+1)]
            s,_=act(s,'jr_quay_online',stall=sid,on=True)
            s,_=act(s,'jr_quay_start',stall=sid)
            st=ST(s);o=quay_self.order(s,st,st['run'],0)
            self.assertEqual(o['drive_factor'],1.6 if tier else 1)
            if tier == 0:
                s['careers']['delivery']['upgrades'] += [f'workgear_delivery_{n}' for n in range(1,4)]
                self.assertEqual(quay_self.order(s,st,st['run'],0)['drive_factor'],1)
            at=o['available_at']
            with patch.object(b.time,'time',return_value=at/1000):
                s,_=act(s,'jr_quay_ship',stall=sid,order=0,order_id=o['id'],items=o['items'],seal=True,tool=o['tool'],note=o['sticker'],way='self',route=o['route'])
            waits.append(quay_self.order(s,ST(s),ST(s)['run'],0)['available_at']-at)
        self.assertLess(waits[1],waits[0])
        self.assertAlmostEqual(waits[0]/waits[1],1.6,places=2)

    def test_npc_gear_reconcile_preserves_pending_arrival_and_no_backdating(self):
        from game import quay_business as b
        s,st=fixture()
        b.settle(s,now=1000)
        st['business']['stock']={d:1000 for d in quay_self.menu(st)['on']}
        b.settle(s,now=1030)  # settle old throughput at the purchase boundary
        slow=copy.deepcopy(s)
        pending=copy.deepcopy(st['business']['arrivals'])
        before=copy.deepcopy(st['business'])
        s['careers'][st['trade']]={'upgrades':['workgear_milk_tea_1','workgear_milk_tea_2','workgear_milk_tea_3']}
        self.assertTrue(b.reconcile(s))
        self.assertFalse(b.reconcile(s))
        self.assertEqual(st['business']['arrivals'],pending)
        self.assertEqual(st['business']['revenue'],before['revenue'])
        self.assertEqual(st['business']['cursor'],before['cursor'])
        first=min(pending.values())/1000
        b.settle(s,now=first-.001)
        self.assertEqual(st['business']['sold'],before['sold'])
        b.settle(s,now=first)
        self.assertEqual(st['business']['sold'],1)   # staggered first arrivals (_fresh): one dish at a time
        upgraded_poll=copy.deepcopy(s)
        for at in range(int(first)+1,7001):
            b.settle(upgraded_poll,now=at)
        b.settle(s,now=7000)
        b.settle(slow,now=7000)
        self.assertEqual(s,upgraded_poll)
        self.assertGreater(st['business']['sold'],slow['journey']['quay']['stalls'][0]['business']['sold'])
        self.assertEqual(b.public(st)['speed_factor'],1.6)

    def test_external_refund_cannot_finance_elapsed_bankrupt_time(self):
        from game import quay_business as b
        from unittest.mock import patch
        s,st=fixture();b.settle(s,now=1000)
        st['fund']=st['till']=0
        with patch.object(b.time,'time',return_value=10000):
            quay.credit(s,'q1','back',100,'Escrow refund')
            b.settle(s)
        self.assertEqual(st['business']['sold'],0)
        self.assertEqual(st['fund']+st['till'],100)
        self.assertEqual(st['business']['cursor'],10000000)

    def test_external_refund_pays_local_fine_without_backpaying_operation(self):
        from game import quay_business as b
        from unittest.mock import patch
        s,st=fixture();b.settle(s,now=1000)
        st['fund']=st['till']=0
        b.assess_fine(st,12)
        with patch.object(b.time,'time',return_value=10000):
            quay.credit(s,'q1','back',100,'Escrow refund')
            b.settle(s)
        self.assertEqual(st['business']['sold'],0)
        self.assertEqual(st['business']['unpaid_fines'],0)
        self.assertEqual(st['business']['expenses']['loss'],12)
        self.assertEqual(st['fund']+st['till'],88)
