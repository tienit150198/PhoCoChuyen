"""Public district presence is a bounded cosmetic pose in town's existing feed."""
import unittest

from live.protocol import LiveError
from live.town import clean_activity


class ResidentialActivity(unittest.TestCase):
    def test_four_public_district_kinds_accept_signed_local_ground(self):
        for kind in ('homes-rent','homes-apartment','homes-townhouse','homes-villa'):
            sample=dict(kind=kind,x=-19.5,y=20,direction='nw',phase='walk',moving=True,action=None)
            with self.subTest(kind=kind):
                self.assertEqual(clean_activity({**sample,'sid':'secret','furniture':{'private':1}}),sample)
                self.assertEqual(clean_activity({**sample,'phase':'idle'})['phase'],'idle')

    def test_bounds_types_actions_and_phases_stay_strict(self):
        sample=dict(kind='homes-rent',x=0,y=0,direction='nw',phase='idle',moving=False,action=None)
        for fields in (dict(x=-20.01),dict(y=20.01),dict(x=True),dict(y=float('nan')),
                       dict(action='reward'),dict(phase='private'),dict(kind='home-other')):
            with self.subTest(fields=fields), self.assertRaises(LiveError):clean_activity({**sample,**fields})
