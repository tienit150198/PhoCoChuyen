"""Business settlement: real ledger changes, aggregate tax, compliant checks and no counter cap."""
import copy
import unittest
from unittest.mock import patch
from game import quay as qy
from game import quay_economy as qe
from tests.test_quay import bare, owner, act, Q


class Economy(unittest.TestCase):
    def sample(self, place='xe', trade='milk_tea'):
        s, st = bare(place, trade)
        qy.ensure(s)['stalls'].append(st)
        return s, st

    def test_unlimited_open_and_large_sequence(self):
        s = owner(100000)
        for _ in range(14):
            s, _ = act(s, 'jr_quay_open', trade='milk_tea', place='xe', confirm=True)
        self.assertEqual(len(Q(s)['stalls']), 14)
        Q(s)['seq'] = 1000001
        s, _ = act(s, 'jr_quay_open', trade='milk_tea', place='xe', confirm=True)
        self.assertEqual(Q(s)['stalls'][-1]['id'], 'q1000002')
        qy.validate(s)

    def test_settlement_matches_cash_and_is_idempotent(self):
        s, st = self.sample()
        before = st['fund'] + st['till']
        with patch.object(qe, '_event', return_value=None):
            qy._sell(s, st, 1)
        self.assertEqual(st['fund'] + st['till'] - before, st['hist'][-1]['net'])
        snapshot = copy.deepcopy(s)
        qe.settle(s, st, 1)
        self.assertEqual(s, snapshot)
        self.assertGreater(st['hist'][-1]['costs']['rent'], 0)

    def test_idle_counter_has_no_charges(self):
        s, st = self.sample()
        st['staff'] = []
        before = st['fund'] + st['till']
        for day in range(1, 20): qy.run_day(s, st, day)
        self.assertEqual(before, st['fund'] + st['till'])
        self.assertEqual(st['due'], 0)

    def test_old_save_migration_does_not_replay_or_tax_old_days(self):
        s,st=self.sample();st['due']=30
        s['journey']['life_day']=10
        before=st['till']+st['fund']
        qy.on_life_day(s)
        self.assertEqual(st['day'],9)
        self.assertEqual(st['due'],30)
        self.assertEqual(before,st['till']+st['fund'])
        self.assertEqual(st['hist'],[])
        self.assertNotIn('economy',Q(s))

    def test_old_save_first_prepare_still_anchors_backlog(self):
        s,st=self.sample();s['journey']['life_day']=10
        before=st['fund']+st['till']
        qe.action(s,st,'jr_quay_prepare',dict(stall=st['id'],kind='invoices',enabled=True))
        qy.on_life_day(s)
        self.assertEqual(st['day'],9)
        self.assertEqual(st['hist'],[])
        self.assertEqual(before,st['fund']+st['till'])

    def test_forged_refund_credit_rejected_even_without_counters(self):
        from game.engine import GameError
        s=owner();q=qy.ensure(s)
        for stalls in ([],self.sample()[1:]):
            q['stalls']=list(stalls)
            q['economy']=dict(period=0,revenue=0,profit=0,vat=0,income=100000)
            with self.assertRaises(GameError):qy.validate(s)

    def test_owner_allowance_is_shared_across_counters(self):
        s, st = self.sample()
        second = copy.deepcopy(st); second['id'] = 'q2'
        Q(s)['stalls'].append(second)
        for counter in (st, second):
            counter['hist'] = [dict(d=1,n=1,rev=800,net=300,w='am',p='normal')]
            counter['till'] = 800
            with patch.object(qe, '_event', return_value=None): qe.settle(s,counter,1)
        self.assertEqual(st['hist'][-1]['costs']['vat'], 0)
        self.assertGreater(second['hist'][-1]['costs']['vat'], 0)
        self.assertEqual(Q(s)['economy']['revenue'], 1600)

    def test_checks_are_free_when_compliant_and_losses_are_local(self):
        for event in ('food_check', 'police_check'):
            s,st=self.sample()
            with patch.object(qe, '_event', return_value=event): qy._sell(s,st,1)
            self.assertEqual(st['hist'][-1]['costs']['incident'],0)
        s,st=self.sample(); st['till']=500
        wallet=s['journey']['wallet']
        with patch.object(qe, '_event', return_value='robbery'): qy._sell(s,st,1)
        self.assertLess(st['hist'][-1]['net'],0)
        self.assertEqual(wallet,s['journey']['wallet'])
        self.assertGreater(st['hist'][-1]['costs']['incident'],0)

    def test_food_violation_pause_repair_and_extortion_report(self):
        s,st=self.sample();qe.config(st)['hygiene']=False
        with patch.object(qe, '_event', return_value='food_check'): qy._sell(s,st,1)
        self.assertTrue(qe.config(st)['paused'])
        qe.action(s,st,'jr_quay_prepare',{'stall':'q1','kind':'hygiene','enabled':True})
        self.assertFalse(qe.config(st)['paused'])
        with patch.object(qe, '_event', return_value='extortion'): qy._sell(s,st,2)
        before=st['till']+st['fund']
        qe.action(s,st,'jr_quay_incident',{'stall':'q1','choice':'report'})
        self.assertEqual(before,st['till']+st['fund'])
        self.assertEqual(qe.config(st)['incident']['status'],'reported')

    def test_chain_has_at_most_one_event_per_day(self):
        s,st=self.sample()
        Q(s)['stalls']=[dict(copy.deepcopy(st),id=f'q{i}') for i in range(1,101)]
        hits=0
        for day in range(10,110):
            events=[qe._event(s,x,day) for x in Q(s)['stalls']]
            count=sum(x is not None for x in events)
            self.assertLessEqual(count,1)
            hits+=count
        self.assertGreater(hits,0)

    def test_changed_stall_list_cannot_trigger_second_incident_same_day(self):
        s,st=self.sample();st['till']=500
        with patch.object(qe,'_event',return_value='robbery'):qy._sell(s,st,10)
        second=copy.deepcopy(st);second['id']='q2';second['hist']=[];second['till']=500
        Q(s)['stalls']=[second]
        with patch.object(qe,'_event',return_value='robbery'):qy._sell(s,second,10)
        self.assertEqual(second['hist'][-1]['costs']['incident'],0)

    def test_loss_refunds_only_previously_paid_income_tax(self):
        s,st=self.sample()
        vat,income=qe._tax(s,1,2000,1000)
        self.assertGreater(income,0)
        nextvat,refund=qe._tax(s,2,0,-2000)
        self.assertEqual(nextvat,0)
        self.assertEqual(refund,-income)
        self.assertEqual(qe._tax(s,3,0,-2000)[1],0)

    def test_recovery_on_idle_day_has_positive_ledger_without_rent(self):
        s,st=self.sample();st['till']=40
        qe.recovery(s,st,4,40)
        h=st['hist'][-1]
        self.assertEqual(h['net'],40)
        self.assertEqual(h['costs']['incident'],-40)
        self.assertEqual(h['costs']['rent'],0)

    def test_hired_receipt_keeps_sales_row_and_does_not_debit_wage_twice(self):
        s,st=self.sample()
        with patch.object(qe,'_event',return_value=None):qy._sell(s,st,1)
        hist=copy.deepcopy(st['hist']);cash=st['till'];wallet=s['journey']['wallet']
        qy.credit(s,st['id'],'shift',60,'Hired shift',wage=30,source='cash')
        r=Q(s)['receipts'][-1]
        self.assertEqual((r['rev'],r['wage'],r['net'],r['cash_net']),(60,30,30,60))
        self.assertEqual(st['till'],cash+60)
        self.assertEqual(st['hist'],hist)
        self.assertEqual(wallet,s['journey']['wallet'])

    def test_hired_receipt_after_sale_and_monotonic_tax_period(self):
        s,st=self.sample();s['journey']['life_day']=31;Q(s)['stalls']=[]
        before=s['journey']['wallet']
        qy.credit(s,st['id'],'shift',60,'Sold counter shift',wage=30,source='joint')
        self.assertEqual(s['journey']['wallet'],before+60)
        self.assertEqual(Q(s)['receipts'][-1]['pocket'],'wallet')
        qe._tax(s,30,60,30)
        self.assertEqual(Q(s)['economy']['period'],1)
        self.assertEqual(Q(s)['economy']['revenue'],120)

    def test_legacy_shift_without_metadata_keeps_legacy_credit(self):
        s,st=self.sample();before=st['till']
        qy.credit(s,st['id'],'shift',60,'Legacy shift')
        self.assertEqual(st['till'],before+60)
        self.assertNotIn('receipts',Q(s))
