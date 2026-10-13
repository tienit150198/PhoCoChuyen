import copy
import unittest
import tempfile
from pathlib import Path

from game.content import UPGRADES
from game.engine import new_state, apply_action, validate_state, public_state, GameError
from tests.helpers import Journey


def upgrade(cid, group, tier):
    return f'warehouse_{group}_{cid}_{tier}'


def fund(c, amount=400_000_000):
    c['money'] = amount
    c['ops']['finance']['opening_balance'] = amount


class WarehouseConvenienceTests(unittest.TestCase):
    def test_registry_aside_reserves_room_and_returns_without_truncation(self):
        from tests.test_career_mother_baby import Registry, to_day, cr
        from game.careers import mother_baby as mb
        case=Registry();case.setUp();j=case.j;to_day(j,5);fund(j.c)
        j.c['upgrades']=[upgrade(j.career,'logistics',n) for n in range(1,11)]
        j.c['stock']['towel']=600;j.act('gift_care_aside',line='r1')
        self.assertEqual(j.c['stock']['towel'],598)
        with self.assertRaises(GameError):j.act('order_stock',item='towel',qty=1)
        self.assertEqual(public_state(j.state)['careers'][j.career]['warehouse']['reserved']['towel'],2)
        mb._shower_failed(j.state,j.c,cr(j),j.c['day'])
        self.assertEqual(j.c['stock']['towel'],600)
        validate_state(j.state)

    def test_recovery_uses_paid_room_including_pending_orders(self):
        from game.happenings import _stock_give
        j=Journey('mother_baby');fund(j.c)
        j.c['upgrades']=[upgrade(j.career,'logistics',n) for n in range(1,11)]
        j.c['stock']['bunny']=590;j.act('order_stock',item='bunny',qty=8)
        self.assertEqual(_stock_give(j.state,j.c,j.career,'bunny',5,36),2)
        self.assertEqual(j.c['stock']['bunny'],592)

    def test_pharmacy_live_batches_never_drop_expiry_identity(self):
        from game.engine import _ph_fresh, _ph_batch, _ph_sync, _ph_validate
        j=Journey('pharmacy'); care=_ph_fresh(j.c['day'])
        for item in j.c['stock']: j.c['stock'][item]=0
        j.c['stock']['P-01-A']=100
        for n in range(100): _ph_batch(care,'P-01-A',1,n+2,1)
        before=copy.deepcopy(care['batches'])
        _ph_sync(j.c,care)
        self.assertEqual(care['batches'],before)
        _ph_validate(care)

    def test_legacy_return_and_rejected_sale_preserve_large_stock(self):
        from tests.test_mother_baby import Returns, find
        from game import giftshop
        from unittest.mock import patch
        j,tid=Returns().journey(lambda f:f['gift']['ret']['_tag']=='ours' and f['gift']['ret']['_cond']=='new' and f['gift']['ret']['_found'])
        item=j.task['gift']['ret']['item'];j.c['stock'][item]=100;fund(j.c)
        j.act('gift_resolve',task=tid,choice='refund',confirm=True)
        self.assertEqual(j.c['stock'][item],101)
        day,slot=find('simple');j=Journey('mother_baby',slot=slot,day=day)
        j.task['basket']={'bunny':2};j.c['stock']['bunny']=100
        with patch('game.consequences.react',return_value={'kind':'refuse','message':''}):giftshop.after_task(j.state,j.c,j.task)
        self.assertEqual(j.c['stock']['bunny'],102)

    def test_event_stock_purchase_counts_existing_and_incoming(self):
        from tests.test_mother_baby import force_event
        from game import convenience
        j=Journey('mother_baby',slot=0,day=3);fund(j.c)
        j.c['upgrades']=[upgrade(j.career,'logistics',n) for n in range(1,11)]
        j.c['stock']['bear']=100
        force_event(j,'fake',dict(seller='Anh Tâm',item='bear',qty=6,unit=20,_fake=True,inspected=False))
        j.act('gift_event',choice='buy')
        self.assertEqual(j.c['stock']['bear'],106)
        j.act('gift_event_ok');j.c['stock']['bear']=594
        j.act('order_stock',item='bear',qty=6)
        force_event(j,'fake',dict(seller='Anh Tâm',item='bear',qty=6,unit=20,_fake=True,inspected=False))
        before=copy.deepcopy(j.state)
        with self.assertRaises(GameError):j.act('gift_event',choice='buy')
        self.assertEqual(j.state,before)

    def test_refund_reserves_room_for_already_paid_shipments(self):
        from tests.test_mother_baby import Returns
        j,tid=Returns().journey(lambda f:f['gift']['ret']['_tag']=='ours' and f['gift']['ret']['_cond']=='new' and f['gift']['ret']['_found'])
        item=j.task['gift']['ret']['item'];j.c['stock'][item]=599;fund(j.c)
        j.c['upgrades']=[upgrade(j.career,'logistics',n) for n in range(1,11)]
        j.act('order_stock',item=item,qty=1)
        before=copy.deepcopy(j.state)
        with self.assertRaises(GameError):j.act('gift_resolve',task=tid,choice='refund',confirm=True)
        self.assertEqual(j.state,before)

    def test_count_applies_to_each_stocked_career_without_changing_common_shelves(self):
        from game import inventory, convenience, work_gear, income_gear
        from game.content import CAREERS
        s=new_state()
        for cid in CAREERS:
            before=inventory.capacity(cid)
            rows=[u for u in UPGRADES if u.get('gear_group')=='warehouse_count' and cid in u['careers']]
            self.assertEqual(len(rows),10 if convenience.countable(cid) else 0,cid)
            if not rows: continue
            c=s['careers'][cid]; c['upgrades']=[u['id'] for u in rows]
            self.assertEqual(convenience.public(c,cid)['count_step'],100)
            self.assertEqual(inventory.capacity(cid),before)
            self.assertEqual(work_gear.factor(c),1)
            self.assertEqual(income_gear.effects(c),dict(demand=0,quality=0,online=0))
        self.assertFalse(convenience.countable('pagoda'))
        validate_state(s)

    def test_base_limits_and_legacy_shelf_are_preserved(self):
        from game import convenience
        j=Journey('mother_baby'); fund(j.c)
        self.assertEqual(convenience.public(j.c,j.career)['line_max'],6)
        with self.assertRaises(GameError): j.act('order_stock',item='bunny',qty=7)
        j.c['upgrades'].append('shelf')
        self.assertEqual(convenience.capacity(j.c,j.career),24)
        j.act('buy_upgrade',item=upgrade(j.career,'logistics',1))
        self.assertEqual(convenience.capacity(j.c,j.career),24)
        j.act('order_stock',item='bunny',qty=8)
        with self.assertRaises(GameError): j.act('order_stock',item='bunny',qty=9)

    def test_ownership_validation_and_max_tier(self):
        s=new_state(); c=s['careers']['mother_baby']; fund(c)
        for tier in range(1,11): s,_=apply_action(s,'mother_baby','buy_upgrade',{'item':upgrade('mother_baby','count',tier)})
        self.assertEqual(s['careers']['mother_baby']['money'],400_000_000-152_692_000)
        with self.assertRaises(GameError): apply_action(s,'mother_baby','buy_upgrade',{'item':upgrade('mother_baby','count',11)})
        s['careers']['mother_baby']['upgrades'].remove(upgrade('mother_baby','count',4))
        with self.assertRaises(GameError): validate_state(s)
        s=new_state(); s['careers']['pharmacy']['upgrades']=[upgrade('mother_baby','count',1)]
        with self.assertRaises(GameError): validate_state(s)

    def test_store_purchase_replay_and_reload_preserve_ownership(self):
        from game.storage import Store
        from game.marriage import _mutate
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            store=Store(Path(tmp)/'warehouse.db')
            try:
                token,_,_=store.session()
                _mutate(store,{store.key(token):lambda s:fund(s['careers']['mother_baby'])})
                rev=store.read(token)[1]
                args=(token,'warehouse-buy-0001',rev,'mother_baby','buy_upgrade',{'item':upgrade('mother_baby','count',1)})
                first=store.command(*args); again=store.command(*args)
                self.assertTrue(again['replayed'])
                self.assertEqual(first['state'],again['state'])
                saved=store.read(token)[0]['careers']['mother_baby']
                self.assertEqual(saved['money'],400_000_000-3000)
                self.assertIn(upgrade('mother_baby','count',1),saved['upgrades'])
            finally: store.close_pool()

    def test_count_catalogue_and_prices(self):
        rows = [u for u in UPGRADES if u.get('gear_group') == 'warehouse_count' and 'mother_baby' in u['careers']]
        self.assertEqual(len(rows), 10)
        self.assertEqual([u['effect_units'] for u in rows], [2,3,5,8,12,20,30,45,65,100])
        self.assertEqual(rows[0]['price'], 3000)
        self.assertEqual(rows[-1]['price'], 100_000_000)

    def test_sequential_buy_atomic_and_wrong_career(self):
        s = new_state(); c = s['careers']['mother_baby']; fund(c)
        first = upgrade('mother_baby', 'count', 1)
        with self.assertRaises(GameError): apply_action(s, 'mother_baby', 'buy_upgrade', {'item':upgrade('mother_baby','count',2)})
        out, _ = apply_action(s, 'mother_baby', 'buy_upgrade', {'item':first})
        self.assertEqual(out['careers']['mother_baby']['money'], c['money'] - 3000)
        self.assertNotIn(first, c['upgrades'])
        with self.assertRaises(GameError): apply_action(out, 'mother_baby', 'buy_upgrade', {'item':first})
        with self.assertRaises(GameError): apply_action(s, 'pharmacy', 'buy_upgrade', {'item':first})
        fund(c, 2999); before=copy.deepcopy(s)
        with self.assertRaises(GameError): apply_action(s, 'mother_baby', 'buy_upgrade', {'item':first})
        self.assertEqual(s, before)

    def test_highest_logistics_orders_receive_and_pending_capacity(self):
        for cid, item in [('mother_baby','blocks'), ('pharmacy','P-01-A')]:
            with self.subTest(cid=cid):
                j=Journey(cid); fund(j.c)
                for tier in range(1,11): j.act('buy_upgrade',item=upgrade(cid,'logistics',tier))
                view=public_state(j.state)['careers'][cid]
                self.assertEqual(view['warehouse']['line_max'],200)
                self.assertEqual(view['warehouse']['capacity'],600)
                with self.assertRaises(GameError): j.act('order_stock',item=item,qty=201)
                for qty in [200,200,194]: j.act('order_stock',item=item,qty=qty)
                self.assertEqual(j.c['stock'][item],6)
                with self.assertRaises(GameError): j.act('order_stock',item=item,qty=1)
                for shipment in list(j.c['shipments']):
                    j.c['turn'] += 10
                    j.act('receive_stock',shipment=shipment['id'],count=shipment['actual'])
                    with self.assertRaises(GameError): j.act('receive_stock',shipment=shipment['id'],count=shipment['actual'])
                self.assertEqual(j.c['stock'][item],600)
                validate_state(j.state)


if __name__ == '__main__': unittest.main()
