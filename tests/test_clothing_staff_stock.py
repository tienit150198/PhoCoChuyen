"""Clothing staff rotate products without losing stock or changing visitor contracts."""
import copy
import unittest
from unittest.mock import patch

from game import inventory, workplace_business as wb, operations, player_service_tasks as pst
from game.careers import clothing as a
from game.engine import GameError
from tests.test_player_service_tasks import BUYER


class ClothingStaffStockTests(unittest.TestCase):
    def sample(self):
        from tests.test_workplace_business import WorkplaceBusinessTests
        s,c,e=WorkplaceBusinessTests().sample('clothing');a._sync(c)
        return s,c,e

    def next(self,c):return min(p['at'] for p in c['ops']['business']['pending'].values())

    def test_ten_receipts_sell_ten_different_products_exactly_once(self):
        s,c,e=self.sample();before={i:inventory.count(c,i) for i in a.ITEM}
        # The 1.7.16 goods start unstocked (a.LEGACY is what a new shop holds): the staff skip them.
        for _ in range(len(a.LEGACY)):wb.settle(s,self.next(c))
        rows=c['ops']['business_clothing_receipts']
        self.assertEqual([next(iter(r['items'])) for r in rows],list(a.LEGACY))
        for r in rows:
            item=next(iter(r['items']))
            self.assertEqual(r['items'],{item:1});self.assertIn(a.ITEM[item]['name'],r['label'])
            self.assertEqual(r['revenue'],a.PRICES[item]*(80+r['stars']*4)//100)
            self.assertEqual(inventory.count(c,item),before[item]-1)
            self.assertEqual(sum(c['ext']['data']['grid'][item].values()),before[item]-1)
        before=copy.deepcopy(s);wb.settle(s,self.next(c)-1);self.assertEqual(s,before)
        operations.validate(c,'clothing')

    def test_empty_or_reserved_tee_does_not_stop_other_products_or_get_sold(self):
        for empty in (False,True):
            with self.subTest(empty=empty):
                s,c,e=self.sample();tee=inventory.count(c,'tee');row=c['ext']['data']['grid']['tee']
                if empty:inventory.take(c,'tee',tee);a._sync(c)
                else:c['tasks']=[dict(id='manual',career='clothing',status='waiting',picks=[dict(item='tee',size=size) for size,qty in row.items() for _ in range(qty)])]
                before=copy.deepcopy(s);self.assertEqual(pst.staff_offers(s,'clothing'),[]);self.assertEqual(s,before)
                wb.settle(s,self.next(c))
                self.assertEqual(c['ops']['business_clothing_receipts'][-1]['items'],{'shirt':1})
                self.assertEqual(inventory.count(c,'tee'),0 if empty else tee)

    def test_fefo_cost_and_grid_drop_only_one_selected_item(self):
        s,c,e=self.sample();c['ops']['business']['served']=1
        c['ext']['inv']['lots']=[r for r in c['ext']['inv']['lots'] if r['item']!='shirt']
        inventory.add_lot(c,'shirt',2,100,30,'market');inventory.add_lot(c,'shirt',1,80,10,'market');a._sync(c)
        wb.settle(s,self.next(c));r=c['ops']['business_clothing_receipts'][-1]
        self.assertEqual(r['items'],{'shirt':1});self.assertEqual(r['goods'],80)
        self.assertEqual(inventory.count(c,'shirt'),2);self.assertEqual(sum(c['ext']['data']['grid']['shirt'].values()),2)
        self.assertEqual(inventory.count(c,'tee'),16)

    def test_rotation_is_same_when_polled_offline_or_replayed(self):
        s,c,e=self.sample();other=copy.deepcopy(s);first=self.next(c);step=wb._seconds(c,e)
        for at in range(first,first+step*20,step):wb.settle(s,at)
        wb.settle(other,first+step*19);self.assertEqual(s,other)
        before=copy.deepcopy(other);wb.settle(other,first+step*19);self.assertEqual(other,before)

    def test_accepted_visitor_keeps_tee_quote_and_consumes_only_at_acceptance(self):
        s,c,e=self.sample();c['ops']['business']['served']=7
        offer=pst.staff_offers(s,'clothing')[0];self.assertEqual(offer['price'],115)
        before=inventory.count(c,'tee')
        with patch('time.time',return_value=2000000000):
            pst.accept(s,'clothing',dict(id='clothing-visitor',offer_id=offer['offer_id'],buyer=BUYER,note='',price=offer['price']))
        r=c['player_service_jobs'][0];self.assertEqual(r['inputs'],{'tee':1});self.assertEqual(r['price'],115)
        self.assertEqual(inventory.count(c,'tee'),before-1)
        wb.settle(s,r['due_at']);self.assertEqual(inventory.count(c,'tee'),before-1)
        self.assertEqual(r['status'],'completed');pst.validate_staff(c,'clothing')

    def test_old_tee_receipt_still_valid_and_unknown_product_rejected(self):
        s,c,e=self.sample();wb.settle(s,self.next(c));r=c['ops']['business_clothing_receipts'][0]
        r['label']=wb.ORDERS['clothing'][0];c['ops']['business']['recent']=[r];del c['ops']['business_clothing_receipts'];operations.validate(c,'clothing')
        r['items']={'unknown':1}
        with self.assertRaises(GameError):operations.validate(c,'clothing')

    def test_four_staff_stop_only_when_all_unreserved_stock_is_used(self):
        s,c,e=self.sample();c['ops']['finance']['opening_balance']+=10000-c['money'];c['money']=10000
        c['ops']['property']['tier']=next(p['id'] for p in operations.PROPERTIES if p['staff_cap']>=4)
        with patch('time.time',return_value=2000000000):
            for i in range(2,5):operations.action(s,c,'clothing','ops_hire',{'candidate':'clothing-staff-'+str(i),'confirm':True})
        initial=sum(inventory.count(c,i) for i in a.ITEM);c['open']=False
        wb.settle(s,2000100000)
        self.assertEqual(c['ops']['business']['served'],initial)
        self.assertEqual(c['ops']['business']['reason'],'stock')
        for item in a.ITEM:
            self.assertEqual(inventory.count(c,item),0)
            self.assertEqual(sum(c['ext']['data']['grid'].get(item,{}).values()),0)
        before=copy.deepcopy(s);wb.settle(s,2000200000);self.assertEqual(s,before)
        inventory.add_lot(c,'shirt',1,100,999,'market')
        wb.settle(s,2000200000);self.assertEqual(c['ops']['business']['served'],initial)
        self.assertGreater(self.next(c),2000200000)
        wb.settle(s,self.next(c));self.assertEqual(c['ops']['business']['served'],initial+1)
        self.assertEqual(c['ops']['business_clothing_receipts'][-1]['items'],{'shirt':1})
        operations.validate(c,'clothing')

    def test_catalogue_selection_is_read_only_and_timer_is_preserved(self):
        s,c,e=self.sample();before=copy.deepcopy(s);at=self.next(c)
        for _ in range(3):a.staff_order(c,0);wb.due(s,at-1);pst.staff_offers(s,'clothing')
        self.assertEqual(s,before)
        wb.settle(s,at-1);self.assertEqual(self.next(c),at)

    def test_actual_receipts_use_sidecar_and_public_bonus_keeps_receipt_ids(self):
        s,c,e=self.sample();wb.settle(s,self.next(c));first=c['ops']['business_clothing_receipts'][0]
        c['ops']['business']['recent']=[dict(first,label=wb.ORDERS['clothing'][0])]
        del c['ops']['business_clothing_receipts']
        for _ in range(14):wb.settle(s,self.next(c))
        self.assertEqual(c['ops']['business']['recent'],[])
        rows=c['ops']['business_clothing_receipts'];self.assertEqual(len(rows),12)
        self.assertEqual(set(c['ops']['business_profit']['recent']),{r['id'] for r in rows})
        shown=wb.public(c)['recent'];self.assertEqual([r['items'] for r in shown],[r['items'] for r in rows])
        self.assertTrue(all(r['profit_bonus']>0 for r in shown))
        operations.validate(c,'clothing')

    def test_older_server_can_append_legacy_receipt_between_new_server_sales(self):
        s,c,e=self.sample()
        for _ in range(2):wb.settle(s,self.next(c))
        with patch.object(wb,'_order',return_value=wb.ORDERS['clothing']):
            wb.settle(s,self.next(c))
        legacy=c['ops']['business_clothing_receipts'].pop()
        c['ops']['business']['recent']=[legacy]
        operations.validate(c,'clothing')
        self.assertEqual(len(wb.public(c)['recent']),3)
        wb.settle(s,self.next(c))
        self.assertEqual(c['ops']['business']['recent'],[])
        self.assertEqual(len(wb.public(c)['recent']),4)
        operations.validate(c,'clothing')
