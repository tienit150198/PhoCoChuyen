import copy
import unittest
from unittest.mock import patch

from game import quay_business as qb, quay_self as qs, quay
from game.engine import GameError
from tests.test_quay_business import fixture
from tests.test_quay import opened, ST, act


class ProfitBoost(unittest.TestCase):
    def shop(self):
        s, st = fixture(staff=False)
        qb.settle(s, now=1000)
        st['business']['stock']['hong_tra'] = 50
        return s, st

    def test_bonus_is_forty_percent_of_profit_not_revenue(self):
        s, st = self.shop()
        st['menu'] = dict(on=['hong_tra'], p={'hong_tra':100})
        before = st['till'] + st['fund']
        cost = qb.unit_cost(st, 'hong_tra')
        qb.sale(st, ['hong_tra'], 1000000)
        tax = (100 - cost) * 7 // 100
        expected = (100 - cost - tax) * 40 // 100
        self.assertEqual(st['business']['profit_boost']['total'], expected)
        self.assertEqual(st['business']['revenue'], 100)
        self.assertEqual(st['till'] + st['fund'] - before, 100 - tax + expected)
        self.assertEqual(qs.price(st, 'hong_tra'), 100)
        self.assertEqual(qb.public(st)['profit_bonus'], expected)

    def test_fractional_small_profits_are_carried(self):
        _, st = self.shop()
        cost = qb.unit_cost(st, 'hong_tra')
        for _ in range(5):
            qb.sale(st, ['hong_tra'], 1000000, total=cost + 1)
        tax = st['business']['expenses']['income_tax']
        self.assertEqual(st['business']['profit_boost']['total'], (5-tax)*40//100)

    def test_operating_cost_and_overchange_reduce_bonus_basis(self):
        _, st = self.shop()
        qb._charge(st, qb.DEN)
        overhead = sum(qb._rates(st).values())
        cost = qb.unit_cost(st, 'hong_tra')
        qb.sale(st, ['hong_tra'], 1600000, total=100, extra_loss=10)
        tax = (100-cost-overhead-10)*7//100
        self.assertEqual(st['business']['profit_boost']['total'], (100-cost-tax-overhead-10)*40//100)
        self.assertEqual(st['business']['expenses']['loss'], 10)

    def test_loss_and_unpaid_fine_are_not_rewarded(self):
        _, st = self.shop()
        st['fund'] = st['till'] = 0
        qb.assess_fine(st, 200)
        qb.sale(st, ['hong_tra'], 1000000, total=100)
        self.assertEqual(st['business']['profit_boost']['total'], 0)
        self.assertGreater(st['business']['unpaid_fines'], 0)

    def test_funding_and_buying_unsold_goods_earn_nothing(self):
        s = opened(staff=False); sid = ST(s)['id']
        s, _ = act(s, 'jr_quay_fund', stall=sid, amount=100)
        s, _ = act(s, 'jr_quay_restock', stall=sid, items={'hong_tra':2})
        self.assertEqual(ST(s)['business']['profit_boost']['total'], 0)

    def test_loss_is_recovered_before_later_sales_earn_bonus(self):
        _, st = self.shop()
        cost = qb.unit_cost(st, 'hong_tra')
        qb.sale(st, ['hong_tra'], 1000000, total=1)
        self.assertEqual(st['business']['profit_boost']['total'], 0)
        qb.sale(st, ['hong_tra'], 1000000, total=100)
        tax = st['business']['expenses']['income_tax']
        self.assertEqual(st['business']['profit_boost']['total'], (101-2*cost-tax)*40//100)

    def test_polling_and_offline_bonuses_match(self):
        s, st = fixture(); qb.settle(s, now=1000)
        before = copy.deepcopy(s)
        for at in range(1001, 2201): qb.settle(s, now=at)
        qb.settle(before, now=2200)
        self.assertEqual(s, before)


class ContinuousCounter(unittest.TestCase):
    def test_legacy_pause_remains_closed_without_sales_for_stopped_time(self):
        s, st = fixture(); qb.settle(s, now=1000)
        st['business'].pop('profit_boost', None)
        st['business']['paused'] = True
        self.assertTrue(qb.due(s, now=2000))
        qb.settle(s, now=2000)
        self.assertTrue(st['business']['paused'])
        self.assertEqual(st['business']['sold'], 0)
        self.assertTrue(all(at > 2000000 for at in st['business']['arrivals'].values()))

    def test_pause_control_stops_new_orders(self):
        s, st = fixture(); qb.settle(s, now=1000)
        qb.action(s, st, 'jr_quay_pause', {'stall':st['id'], 'on':True})
        self.assertTrue(st['business']['paused'])

    def test_legacy_paused_customer_order_keeps_accepted_preparation(self):
        from game import player_service_tasks as pst
        from tests.test_player_service_tasks import BUYER
        s, st = fixture(); qb.settle(s, now=1000)
        dish = next(iter(st['business']['stock']))
        pst.accept_visit(s, st['id'], dict(id='paused-guest',offer_id=dish,
            items=[dish],price=qs.price(st,dish),buyer=BUYER,note=''),now=1000)
        st['business']['paused'] = True
        st['business'].pop('profit_boost')
        qb.settle(s, now=2000)
        qb.settle(s, now=2001)
        row = st['business']['visitor_orders'][0]
        self.assertEqual(row['status'], 'completed')
        self.assertLess(row['due_at'], 2001000)
        self.assertEqual(st['business']['revenue'], 0)

    def test_next_customer_arrives_while_owner_is_serving(self):
        s = opened(staff=False);sid=ST(s)['id']
        s, _ = act(s,'jr_quay_start',stall=sid)
        due = ST(s)['run']['next_at']/1000
        c = qs.customer(s, ST(s), ST(s)['run'], 0)
        with patch.object(qb.time,'time',return_value=due+60):
            s, _ = act(s,'jr_quay_serve',stall=sid,items=c['items'],change=c['pay']-c['total'],smile=True)
        st=ST(s)
        self.assertLessEqual(st['run']['next_at'], st['business']['cursor'])
        self.assertIsNotNone(qs.run_view(s, st)['cust'])
