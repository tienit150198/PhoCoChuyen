import copy
import unittest
from game import career_scale_inventory as inv
from game.career_scale_content import profile
from game.content import initial_career
from game.engine import GameError


class ScaleInventoryTests(unittest.TestCase):
    def setUp(self):
        self.c = initial_career('grocery')
        self.c['money'] = self.c['ops']['finance']['opening_balance'] = 10**8
        self.c['scale'] = {'tier': 1, 'sites': [{'id': 'base'}, {'id': 'branch-1'}]}
        self.s = {'seq': 0, 'careers': {'grocery': self.c}, 'journey': {}}
        self.code = profile('grocery').materials[0].code

    def buy(self, qty=1):
        return inv.action(self.s,self.c,'grocery','scale_stock_buy',{'site':'base','code':self.code,'quantity':qty})

    def receive(self, order):
        inv.action(self.s,self.c,'grocery','scale_stock_receive',{'order':order['order'],'count':order['quantity']})

    def test_transit_storage_and_per_order_are_separate(self):
        with self.assertRaises(GameError): self.buy(81)
        first = self.buy(80)
        with self.assertRaises(GameError): self.buy(1)
        self.receive(first)
        self.assertEqual(inv.space(self.c,'grocery',self.code)['room'],0)
        before = self.c['money']
        with self.assertRaises(GameError): self.receive(first)
        self.assertEqual(self.c['money'],before)

    def test_paid_rights_global_across_sites(self):
        self.c['upgrades'] += ['warehouse_storage_grocery_5','warehouse_order_grocery_1']
        self.buy(120)
        self.assertEqual(inv.space(self.c,'grocery',self.code)['capacity'],550)
        self.assertEqual(inv.space(self.c,'grocery',self.code)['room'],430)
        with self.assertRaises(GameError): self.buy(121)

    def test_movement_and_consumption_keep_units_cost_basis_once(self):
        order = self.buy(2);self.receive(order)
        total = inv.units(self.c,self.code)
        inv.reserve(self.c,'grocery','grocery-1','base',self.code,100)
        with self.assertRaises(GameError):
            inv.action(self.s,self.c,'grocery','scale_stock_move',{'source':'base','site':'branch-1','code':self.code,'units':total})
        inv.action(self.s,self.c,'grocery','scale_stock_move',{'source':'base','site':'branch-1','code':self.code,'units':total-100})
        self.assertEqual(inv.units(self.c,self.code),total)
        result=inv.consume(self.c,'grocery-1')
        self.assertEqual(result,{'units':100,'cost':100})
        self.assertEqual(inv.consume(self.c,'grocery-1'),{'units':0,'cost':0})
        self.assertEqual(inv.units(self.c,self.code),total-100)
        inv.validate(self.c,'grocery')

    def test_whole_lot_transfer_at_row_cap_does_not_need_extra_rows(self):
        self.c[inv.KEY]=dict(v=1,seq=400,orders=[],lots=[dict(id=f'lot-{i+1}',code=self.code,site='base',units=1,unit_cost=1,reserved={}) for i in range(400)])
        inv.action(self.s,self.c,'grocery','scale_stock_move',dict(source='base',site='branch-1',code=self.code,units=1))
        self.assertEqual(len(self.c[inv.KEY]['lots']),400)
        self.assertEqual(inv.units(self.c,self.code,'branch-1'),1)
        inv.validate(self.c,'grocery')

    def test_cancel_releases_identical_stock_and_no_money(self):
        order=self.buy();self.receive(order)
        before=copy.deepcopy(self.c)
        inv.reserve(self.c,'grocery','grocery-1','base',self.code,123)
        inv.release(self.c,'grocery-1')
        self.assertEqual(self.c,before)

    def test_wrong_count_or_payload_and_bool_reject_before_debit(self):
        before=copy.deepcopy(self.c)
        for quantity in (True,0,-1,1.5,'10'):
            with self.assertRaises(GameError):self.buy(quantity)
            self.assertEqual(self.c,before)
        order=self.buy()
        before=copy.deepcopy(self.c)
        with self.assertRaises(GameError):
            inv.action(self.s,self.c,'grocery','scale_stock_receive',{'order':order['order'],'count':2})
        self.assertEqual(self.c,before)


if __name__=='__main__':unittest.main()
