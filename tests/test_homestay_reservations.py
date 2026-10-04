"""Phone reservations, held rooms and pending OTA must use the same calendar."""
import unittest

from game.careers import homestay as H
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey
from tests.test_career_homestay import find, counted


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.day, self.slot = find('booking', lambda t: counted(t['needs']['adults'], t['needs']['kids']) <= 2
                                  and t['needs']['start'] > t['day'])
        self.j = Journey('homestay', slot=self.slot, day=self.day)
        self.j.act('ask')
        self.data['bookings'] = []
        self.data['ota'] = []

    @property
    def data(self):
        return self.j.c['ext']['data']

    def ota(self, start=None, nights=None):
        n = self.j.task['needs']
        self.data['ota'].append(dict(id='ota-test', ota='Mây Travel', name='Khách OTA', room='thong',
                                    start=n['start'] if start is None else start, nights=n['nights'] if nights is None else nights,
                                    guests=2, total=60, net=51, status='new', rooms=[], day=self.day))

    def test_pending_ota_blocks_phone_hold(self):
        self.ota()
        with self.assertRaises(GameError):
            self.j.act('hs_hold', rooms=['thong'])
        self.assertEqual(self.j.task['hold'], [])

    def test_new_ota_is_rechecked_before_taking_deposit(self):
        self.j.act('hs_hold', rooms=['thong'])
        self.ota()
        before = self.j.c['money']
        with self.assertRaises(GameError):
            self.j.act('hs_book', confirm=True)
        self.assertEqual(self.j.c['money'], before)
        self.assertEqual(self.data['bookings'], [])

    def test_another_phone_hold_blocks_same_nights(self):
        self.j.act('hs_hold', rooms=['thong'])
        n = self.j.task['needs']
        second = next(t for slot in range(100) if slot != self.slot
                      for t in [H.make_task(self.day, slot, 2)]
                      if t['job'] == 'booking' and counted(t['needs']['adults'], t['needs']['kids']) <= 2
                      and H._overlap(n['start'], n['nights'], t['needs']['start'], t['needs']['nights']))
        self.j.c['tasks'].append(second)
        self.j.act('ask', task=second['id'])
        with self.assertRaises(GameError):
            self.j.act('hs_hold', task=second['id'], rooms=['thong'])
        self.assertEqual(self.j.get(second['id'])['hold'], [])

    def test_hold_is_visible_and_own_confirmation_still_works(self):
        self.j.act('hs_hold', rooms=['thong'])
        data = public_state(self.j.state)['careers']['homestay']['data']
        self.assertTrue(data.get('holds'))
        self.j.act('hs_book', confirm=True)
        self.assertEqual(len(self.data['bookings']), 1)
        validate_state(self.j.state)

    def test_adjacent_ota_nights_do_not_block_phone_reservation(self):
        n = self.j.task['needs']
        self.ota(start=n['start'] + n['nights'], nights=1)
        self.j.act('hs_hold', rooms=['thong'])
        self.j.act('hs_book', confirm=True)
        self.assertEqual(len(self.data['bookings']), 1)

    def test_ota_can_sync_itself(self):
        self.ota()
        self.j.act('hs_sync', order='ota-test', rooms=['thong'])
        self.assertEqual(self.data['ota'][0]['status'], 'synced')
        self.assertEqual(self.data['bookings'][0]['rooms'], ['thong'])

    def test_ota_cannot_sync_onto_another_hold(self):
        self.j.act('hs_hold', rooms=['thong'])
        self.ota()
        with self.assertRaises(GameError):
            self.j.act('hs_sync', order='ota-test', rooms=['thong'])
        self.j.act('hs_sync', order='ota-test', rooms=['suong'])
        self.assertEqual(self.data['bookings'][0]['rooms'], ['suong'])

    def test_releasing_hold_frees_room_for_ota(self):
        self.j.act('hs_hold', rooms=['thong'])
        self.ota()
        self.j.act('hs_release')
        self.j.act('hs_sync', order='ota-test', rooms=['thong'])
        self.assertEqual(self.data['bookings'][0]['rooms'], ['thong'])

    def test_anniversary_does_not_overwrite_pending_ota(self):
        self.j.c['day'] = H.ANNIV_FIRST - H.ANNIV_LEAD
        self.data['ota'] = []
        self.ota(start=H.ANNIV_FIRST, nights=H.ANNIV_NIGHTS)
        H._anniv_call(self.j.state, self.j.c)
        b = next(b for b in self.data['bookings'] if b.get('anniv'))
        self.assertNotIn('thong', b['rooms'])


if __name__ == '__main__':
    unittest.main()
