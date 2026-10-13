import copy
import unittest
from unittest.mock import patch
from game import career_scale_contracts as contracts
from game import career_scale_inventory as inv
from game import career_scale_quota as quota
from game.career_scale_content import PROFILES, profile, stage
from game.content import initial_career
from game.engine import GameError


class ScaleContractsTests(unittest.TestCase):
    def fixture(self,cid='grocery',tier=3,count=None):
        c=initial_career(cid);c['money']=c['ops']['finance']['opening_balance']=10**9
        n=count or stage(cid,tier).resources
        c['scale']={'tier':tier,'revision':0,'sites':[{'id':'base','name':'Gốc'}],
          'crew':[{'id':f'p{i}','role':profile(cid).roles[i%len(profile(cid).roles)],'name':f'NPC {i}'} for i in range(n)],
          'resources':[{'id':f'r{i+1}','site':'base','crew':f'p{i}','condition':100,'busy':None,'label':f'Vị trí {i+1}'} for i in range(n)]}
        s={'seq':0,'careers':{cid:c},'journey':{'seed':1,'life':{'spirit':50}}}
        return s,c

    def act(self,s,c,cid,name,p=None):
        return contracts.action(s,c,cid,name,p or {},now=1791907200)

    def complete(self,s,c,cid='grocery',bad=False,demand=100,historical=False):
        self.act(s,c,cid,'scale_offer')
        o=c[contracts.KEY]['offer'];o['demand']=demand
        # Demand is server generated. Deterministic test replaces the whole quote
        # before any binding/cash operation, never through a player payload.
        o['quote']=contracts.project_quote(cid,o['tier'],demand,len(o['resources']))
        good=lambda phase:min(getattr(profile(cid).scenario,phase),key=lambda x:x.score).id if bad else max(getattr(profile(cid).scenario,phase),key=lambda x:x.score).id
        self.act(s,c,cid,'scale_plan',{'id':o['id'],'option':good('planning')})
        for row in contracts.requirements(c,cid,o):
            if profile(cid).kind=='business':
                room=inv.space(c,cid,row['code']);qty=(row['units']+room['carton_units']-1)//room['carton_units']
                while qty:
                    n=min(qty,room['order']);r=inv.action(s,c,cid,'scale_stock_buy',{'site':row['site'],'code':row['code'],'quantity':n})
                    inv.action(s,c,cid,'scale_stock_receive',{'order':r['order'],'count':n});qty-=n
                    if historical:c[inv.KEY]['lots'][-1]['unit_cost']=2
            self.act(s,c,cid,'scale_allocate',{'id':o['id'],'site':row['site'],'code':row['code'],'units':row['units']})
        for r in o['resources']:
            self.act(s,c,cid,'scale_schedule',{'id':o['id'],'resource':r['id'],'role':r['role']})
        self.act(s,c,cid,'scale_start',{'id':o['id'],'option':good('allocation')})
        for site in sorted({r['site'] for r in o['resources']}):
            self.act(s,c,cid,'scale_resolve',{'id':o['id'],'site':site,'option':good('exception')})
            self.act(s,c,cid,'scale_accept',{'id':o['id'],'site':site,'option':good('acceptance')})
        with patch('game.career_scale.accepted'):
            result=self.act(s,c,cid,'scale_settle',{'id':o['id']})
        return o,result

    def test_full_low_demand_and_failed_receipts_reconcile_cash_plus_stock(self):
        for demand in (100,80,60):
            for bad in (False,True):
                s,c=self.fixture();initial=c['money']
                o,result=self.complete(s,c,bad=bad,demand=demand)
                stock=sum(x['units']*x['unit_cost'] for x in c[inv.KEY]['lots'])
                receipt=result['receipt']
                self.assertEqual(c['money']+stock-initial,receipt['net'])
                self.assertEqual(receipt['net'],receipt['revenue']-sum(receipt[k] for k in ('materials','wages','premises','loss','tax')))
                self.assertEqual(c['earnings'],0);self.assertEqual(c['costs'],0)
                self.assertEqual(c['ops']['finance']['period_revenue'],0)
                if not bad:self.assertEqual(receipt['net'],{100:12000,80:8160,60:4320}[demand])
                else:self.assertLessEqual(receipt['revenue'],o['quote']['revenue'])
                before=copy.deepcopy(c)
                with self.assertRaises(GameError):self.act(s,c,'grocery','scale_settle',{'id':o['id']})
                self.assertEqual(c,before)

    def test_historical_lot_cost_is_consumed_and_receipted_without_locking_ca(self):
        s,c=self.fixture()
        o,result=self.complete(s,c,historical=True)
        receipt=result['receipt']
        self.assertEqual(receipt['materials'],2*o['quote']['materials'])
        self.assertEqual(receipt['net'],o['quote']['net']-o['quote']['materials'])
        self.assertFalse(any(x['busy'] for x in c['scale']['resources']))

    def test_cancel_offer_keeps_id_quote_and_returns_quota(self):
        s,c=self.fixture();self.act(s,c,'grocery','scale_offer');before=copy.deepcopy(c[contracts.KEY]['offer'])
        self.act(s,c,'grocery','scale_cancel',{'id':before['id']})
        self.assertEqual(quota.public(s,1791907200)['available'],1)
        self.act(s,c,'grocery','scale_offer')
        self.assertEqual(c[contracts.KEY]['offer'],before)
        self.assertEqual(quota.public(s,1791907200)['available'],0)

    def test_agency_and_community_never_withdraw_organization_budget(self):
        for cid in ('police','post_office','pagoda'):
            s,c=self.fixture(cid);initial=c['money'];o,result=self.complete(s,c,cid)
            self.assertEqual(c['money']-initial,stage(cid,3).net)
            self.assertNotIn(inv.KEY,c)
            self.assertEqual(result['receipt']['materials'],0)

    def test_public_does_not_reveal_answers_or_mutate_and_payload_is_strict(self):
        s,c=self.fixture();before=copy.deepcopy(s);contracts.public(s,c,'grocery',now=1791907200);self.assertEqual(s,before)
        with self.assertRaises(GameError):self.act(s,c,'grocery','scale_offer',{'demand':100})
        self.act(s,c,'grocery','scale_offer')
        dto=contracts.public(s,c,'grocery',now=1791907200)
        self.assertNotIn('score',str(dto));self.assertNotIn('choices',dto['contract'])

    def test_all_profiles_and_stages_capacity_demand_quotes_have_exact_ledgers(self):
        for cid in PROFILES:
            for tier in range(1,9):
                for demand in (100,80,60):
                    for count in (1,stage(cid,tier).resources):
                        q=contracts.project_quote(cid,tier,demand,count)
                        self.assertEqual(q['net'],q['revenue']-q['cost_total'])
                        self.assertEqual(q['resources'],count)


if __name__=='__main__':unittest.main()
