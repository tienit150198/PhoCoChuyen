import copy
import importlib.util
import unittest
from unittest.mock import patch

from game import quay_business as qb, shop_events as events
from tests.test_quay_business import fixture


class WealthSecurity(unittest.TestCase):
    def pricing(self):
        self.assertIsNotNone(importlib.util.find_spec('game.wealth_pricing'))
        from game import wealth_pricing
        return wealth_pricing

    def test_progressive_prices_and_free_choices(self):
        p = self.pricing()
        self.assertEqual([p.cost(3, w) for w in (0, 10000, 100000, 1000000)], [3, 3, 6, 33])
        self.assertEqual([p.cost(7, w) for w in (10000, 100000, 1000000)], [7, 14, 77])
        self.assertEqual(p.cost(0, 10**14), 0)
        self.assertLessEqual(p.cost(80, 10**14), 80000)

    def test_rich_counter_protection_quote_and_charge_match(self):
        fees = []
        for wallet in (0, 1000000):
            s, st = fixture(staff=False)
            s['journey']['wallet'] = wallet
            qb.settle(s, now=1000)
            qb.action(s, st, 'jr_quay_protection', {'level': 'premium'})
            quote = qb.public(st)
            fee = quote['rates']['protection']
            self.assertEqual(quote['protection']['period_cost'], fee)
            st.update(fund=100000, till=0)
            before = st['fund']
            qb._charge(st, qb.DEN)
            self.assertEqual(st['business']['expenses']['protection'], fee)
            self.assertEqual(before - st['fund'], sum(quote['rates'].values()))
            fees.append(fee)
        self.assertGreater(fees[1], fees[0])

    def test_rich_shop_event_captures_price_and_matches_payment(self):
        quotes = []
        for wallet in (0, 1000000):
            s, st = fixture(staff=False)
            s['journey']['wallet'] = wallet
            qb.settle(s, now=1000)
            st.update(fund=1000000, till=0)
            st['business']['sold'] = events.GAP
            with patch.object(events, 'select_kind', return_value='theft'):
                events.tick_quay(s, st)
            q = events.public(st, True)['pending']
            choice = next(x for x in q['choices'] if x['id'] == 'record')
            s['journey']['wallet'] = 0
            self.assertEqual(events.public(st, True)['pending'], q)
            before = st['fund'] + st['till']
            events.choose_quay(s, st, dict(event=q['id'], choice='record', confirm=True))
            self.assertEqual(before - st['fund'] - st['till'], choice['cost'])
            events.validate(st, st['id'], st['trade'], st['place'])
            quotes.append(choice['cost'])
        self.assertGreater(quotes[1], quotes[0])

    def test_asset_sources_are_owned_and_valuation_is_read_only(self):
        p = self.pricing()
        from game import garage, housing
        s, st = fixture(staff=False)
        j = s['journey']
        j.update(wallet=100, bank=dict(balance=200, demand=300, terms=[dict(amount=400)]),
                 invest=dict(saving=dict(balance=500), coin=dict(units=1)),
                 garage=dict(cars={'vehicle': dict(p=1000)}))
        house=dict(id='own-house',kind=next(iter(housing.HOMES)),price=10000,day=1)
        j['home']=dict(own=house,props=[dict(house)])
        s['careers']={}
        before=copy.deepcopy(s)
        with patch('game.invest.value',return_value=600), patch('game.vang.value',return_value=700):
            expected=2800+garage.sell_price(1000)+housing.value_of(house,j['life_day'])+st['fund']+st['till']
            self.assertEqual(p.total(s),expected)
        self.assertEqual(s,before)

    def test_daily_fee_renews_after_elapsed_service_and_reads_do_not_reprice(self):
        s, st = fixture(staff=False);s['journey']['wallet']=0
        qb.settle(s,now=1000)
        qb.action(s,st,'jr_quay_protection',dict(level='basic'))
        old=qb.public(st)['rates']['protection']
        s['journey']['wallet']=1000000
        qb.settle(s,now=1600)
        self.assertEqual(qb.public(st)['rates']['protection'],old)
        s['journey']['life_day']+=1
        qb.settle(s,now=2200)
        self.assertGreater(qb.public(st)['rates']['protection'],old)
        self.assertEqual(st['business']['expenses']['protection'],0)  # no staff, no manual shift
        after=copy.deepcopy(s)
        self.assertFalse(qb.settle(s,now=2200))
        self.assertEqual(s,after)

    def test_rich_offline_and_polling_settle_identically(self):
        s,st=fixture();s['journey']['wallet']=1000000
        qb.settle(s,now=1000)
        qb.action(s,st,'jr_quay_protection',dict(level='premium'))
        offline=copy.deepcopy(s)
        for at in range(1001,2201,7):qb.settle(s,now=at)
        qb.settle(s,now=2200);qb.settle(offline,now=2200)
        self.assertEqual(s,offline)

    def test_new_day_does_not_rebill_offline_time_at_new_rate(self):
        s,st=fixture();s['journey']['wallet']=0
        qb.settle(s,now=1000)
        qb.action(s,st,'jr_quay_protection',dict(level='basic'))
        control=copy.deepcopy(s)
        s['journey']['life_day']+=1;s['journey']['wallet']=1000000
        qb.settle(s,now=1600);qb.settle(control,now=1600)
        self.assertEqual(st['business']['expenses'],control['journey']['quay']['stalls'][0]['business']['expenses'])
        self.assertGreater(qb.public(st)['rates']['protection'],qb.public(control['journey']['quay']['stalls'][0])['rates']['protection'])

    def test_racket_quote_and_payment_scale_together(self):
        from tests.test_incidents import open_day,fire,choose
        from game import incidents
        s=open_day('milk_tea');s['journey']['wallet']=1000000
        fire(s,'milk_tea','racket');c=s['careers']['milk_tea']
        view=incidents.public(c,'milk_tea',s)['active']
        opt=next(x for x in view['options'] if x['id']=='pay')
        quoted=-sum(x['amount'] for x in opt['stakes'])
        self.assertGreater(quoted,40)
        self.assertIn(str(quoted),opt['label'])
        from game.engine import money
        money(s,c,quoted,'Test capital',category='other_income')
        before=c['money']
        s,_=choose(s,'milk_tea','pay')
        self.assertEqual(before-s['careers']['milk_tea']['money'],quoted)

    def test_insurance_next_shift_scales_and_personal_risk_counts_property(self):
        from tests.helpers import Journey
        from game import operations,rui,housing
        j=Journey();j.state['journey']['wallet']=1000000
        operations.on_start(j.state,j.c,j.career)
        j.c['ops']['security']['insurance']=True
        operations.on_close(j.state,j.c,j.career)
        invoice=next(x for x in j.c['ops']['finance']['bills'] if x['kind']=='insurance')
        self.assertGreater(invoice['amount'],2)
        j.state['journey']['wallet']=1000
        j.state['journey']['home']=dict(own=dict(id='big',kind=next(iter(housing.HOMES)),price=2000000,day=1),props=[])
        self.assertEqual(rui.wealth_risk(j.state)['odds_pct'],300)
