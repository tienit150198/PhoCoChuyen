"""Paid shelf capacity is real ownership, separate from count speed and batch size."""
import copy
import unittest
from game import capacity_progression as cp
from game.content import CAREERS, UPGRADES
from game.engine import apply_action, new_state, validate_state, GameError
from game import inventory

class CapacityCatalogue(unittest.TestCase):
    def test_all_existing_shared_stock_and_boba_have_ten_tiers(self):
        from game.career_scale_content import PROFILES
        eligible={c for c in CAREERS if inventory.catalogue(c)} | {'milk_tea'} | {c for c,p in PROFILES.items() if p.kind=='business'}
        rows=[u for u in UPGRADES if u.get('gear_group')=='warehouse_storage']
        self.assertEqual(len(eligible),36)
        self.assertEqual(len(rows),360)
        self.assertEqual({u['careers'][0] for u in rows},eligible)
        for cid in eligible:
            group=[u for u in rows if u['careers']==[cid]]
            self.assertEqual([u['price'] for u in group],[3000,9000,30000,100000,350000,1200000,4000000,12000000,35000000,100000000])
            self.assertTrue(all(u['effect_units']>u['effect_previous'] for u in group))
        self.assertNotIn('pagoda',eligible)
        self.assertIn('lawyer',eligible)

    def test_paid_capacity_requires_real_purchase_and_preserves_stock(self):
        for cid,base,maximum in [('clothing',80,4000),('com',120,6000),('milk_tea',60,3000)]:
            with self.subTest(career=cid):
                s=new_state();c=s['careers'][cid]
                c['ops']['finance']['opening_balance']+=200_000_000-c['money'];c['money']=200_000_000
                before=copy.deepcopy(c)
                with self.assertRaises(GameError):
                    apply_action(s,cid,'buy_upgrade',{'item':cp.item_id(cid,2)})
                self.assertEqual(c,before)
                for tier in range(1,11):
                    s,_=apply_action(s,cid,'buy_upgrade',{'item':cp.item_id(cid,tier)})
                c=s['careers'][cid]
                self.assertEqual(c['money'],200_000_000-152_692_000)
                self.assertEqual(cp.limit(c,cid,base),maximum)
                self.assertEqual(cp.limit({},cid,base),base)
                with self.assertRaises(GameError):
                    apply_action(s,cid,'buy_upgrade',{'item':cp.item_id(cid,10)})
                self.assertEqual(c.get('stock'),before.get('stock'))
                validate_state(s)

if __name__=='__main__':unittest.main()
