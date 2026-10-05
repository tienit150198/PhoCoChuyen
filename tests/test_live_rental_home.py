import json
import unittest
from live.home import owned_access


class RentalHomeAccess(unittest.TestCase):
    def state(self, day=1):
        return json.dumps({'journey': {'story': True, 'life_day': day,
            'home': {'own': None, 'shared': None, 'rent': None},
            'rental': {'id': 'rent-'+'a'*24, 'kind': 'tap_the', 'rent': 30, 'start_day': 1, 'end_day': 6}}})

    def test_private_rental_room_is_scoped_to_tenant_and_lease(self):
        a=owned_access('tenant-a', self.state())
        b=owned_access('tenant-b', self.state())
        self.assertIsNotNone(a)
        self.assertTrue(a['rooms'])
        self.assertNotEqual(a['base'], b['base'])
        self.assertIsNone(owned_access('tenant-a', self.state(), 'stay'))
        self.assertIsNone(owned_access('tenant-a', self.state(), 'pair'))

    def test_expired_lease_does_not_grant_room(self):
        self.assertIsNone(owned_access('tenant-a', self.state(6)))
