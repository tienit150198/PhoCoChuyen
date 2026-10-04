import copy
import unittest
from game import garage as gr,rui
from game.engine import validate_state,migrate_state
from tests.test_rui import grown,own_car,R,days
from tests.test_bank import act

class ParkedAircraft(unittest.TestCase):
    def test_unused_equipped_and_stored_aircraft_never_get_breakdown_candidates(self):
        s=grown(50000)
        for vid in ('may_bay_nho','phan_luc','o_to_mini'):own_car(s,vid)
        for day in range(31,91):
            s['journey']['life_day']=day
            self.assertFalse([c for c in rui.candidates(s,R(s),day) if c[1] in ('xe','phat')])

    def test_real_trip_exposes_only_that_vehicle_once_on_next_day(self):
        s=grown(50000);own_car(s,'may_bay_nho');own_car(s,'phan_luc')
        s,_=act(s,'jr_garage_trip',id='may_bay_nho')
        day=s['journey']['life_day']
        self.assertEqual(s['journey']['garage_trips'],{'may_bay_nho':day})
        self.assertFalse([c for c in rui.candidates(s,R(s),day) if c[1]=='xe'])
        self.assertEqual([c[3] for c in rui.candidates(s,R(s),day+1) if c[1]=='xe'],['may_bay_nho'])
        self.assertFalse([c for c in rui.candidates(s,R(s),day+2) if c[1]=='xe'])
        validate_state(s)
        upgraded=migrate_state(copy.deepcopy(s));self.assertEqual(upgraded['journey']['garage_trips'],s['journey']['garage_trips'])

    def test_cosmetic_equipping_and_painting_do_not_record_use(self):
        s=grown(50000);own_car(s,'may_bay_nho')
        s,_=act(s,'jr_garage_ride',id='may_bay_nho')
        s,_=act(s,'jr_garage_paint',id='may_bay_nho',color='do')
        self.assertNotIn('garage_trips',s['journey'])

    def test_selling_clears_usage_and_rebuy_does_not_inherit_it(self):
        s=grown(100000);own_car(s,'may_bay_nho')
        s,_=act(s,'jr_garage_trip',id='may_bay_nho')
        s,_=act(s,'jr_garage_sell',id='may_bay_nho',confirm=True)
        self.assertNotIn('may_bay_nho',s['journey']['garage_trips'])
        s,_=act(s,'jr_garage_buy',id='may_bay_nho',confirm=True)
        self.assertFalse([c for c in rui.candidates(s,R(s),s['journey']['life_day']+1) if c[1]=='xe'])
