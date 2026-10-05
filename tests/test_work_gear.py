import copy
import unittest
from game import work_gear as gear
from game.content import CAREERS
from game.engine import new_state, apply_action, validate_state, GameError


class WorkGearTests(unittest.TestCase):
    def test_every_career_has_three_real_speed_tiers(self):
        self.assertEqual(set(gear.NAMES), set(CAREERS))
        for cid in CAREERS:
            c={'upgrades':[]}
            self.assertEqual(gear.factor(c),1)
            for tier in range(1,4):
                c['upgrades'].append(gear.item_id(cid,tier))
                self.assertEqual(gear.factor(c),gear.RATES[tier]/100)

    def test_purchase_charges_once_and_requires_previous_tier(self):
        s=new_state(); c=s['careers']['delivery']; c['money']=2000; c['ops']['finance']['opening_balance']=2000; c['xp']=900
        with self.assertRaises(GameError):
            apply_action(s,'delivery','buy_upgrade',{'item':gear.item_id('delivery',2)})
        out,_=apply_action(s,'delivery','buy_upgrade',{'item':gear.item_id('delivery',1)})
        self.assertEqual(out['careers']['delivery']['money'],2000-gear.PRICES[1])
        self.assertEqual(gear.factor(s['careers']['delivery']),1)
        with self.assertRaises(GameError):
            apply_action(out,'delivery','buy_upgrade',{'item':gear.item_id('delivery',1)})

    def test_foreign_equipment_is_rejected_in_purchase_and_save(self):
        s=new_state(); s['careers']['delivery']['money']=2000
        s['careers']['delivery']['ops']['finance']['opening_balance']=2000
        with self.assertRaises(GameError):
            apply_action(s,'delivery','buy_upgrade',{'item':gear.item_id('salon',1)})
        s['careers']['delivery']['upgrades'].append(gear.item_id('salon',1))
        with self.assertRaises(GameError): validate_state(s)

    def test_public_effect_does_not_mutate_old_save(self):
        c={'upgrades':[]}; before=copy.deepcopy(c)
        self.assertEqual(gear.public(c)['factor'],1)
        self.assertEqual(c,before)

    def test_purchase_sets_private_staff_rate_at_purchase_boundary(self):
        from tests.test_quay import opened,ST
        from unittest.mock import patch
        with patch('game.business.time.time',return_value=2000000000):
            s=opened()
            arrivals=copy.deepcopy(ST(s)['business']['arrivals'])
            out,_=apply_action(s,'milk_tea','buy_upgrade',{'item':gear.item_id('milk_tea',1)})
        self.assertEqual(ST(out)['business']['speed_factor'],1.15)
        self.assertEqual(ST(out)['business']['arrivals'],arrivals)

    def test_delivery_upgrade_reduces_server_route_time_preserves_cost(self):
        from tests.helpers import Journey
        from game.careers import delivery as D
        j=Journey('delivery');c=j.c
        baseline=D._leg(c,'hub','villa',0)
        c['upgrades']=[gear.item_id('delivery',tier) for tier in range(1,4)]
        improved=D._leg(c,'hub','villa',0)
        self.assertLess(improved['minutes'],baseline['minutes'])
        self.assertEqual(improved['fuel'],baseline['fuel'])
        self.assertEqual(D.public_data(c)['drive_factor'],1.6)

if __name__=='__main__': unittest.main()
