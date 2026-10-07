"""UI wave 5 (docs/UI_KIT.md "Disabled with a reason"): the homestay's pre-checks the page dims buttons with.

- data.can.hs_assign[task][room]: the same rule as hs_assign's room check (_blocked). The audit's top homestay refusal
  (220 + 67) was a room an app order still waits to sync into ("Phòng … có đơn … chờ đồng bộ"): the calendar does not
  show such an order, so the tile looked free. The tile is now dimmed with those words, and a fix opens the board;
- t.can.hs_pick: a fourth place ("Gợi ý tối đa 3 nơi", 158 refusals).
Both are view fields: computed in public_data / public_task, never saved."""
import unittest

from game.careers import homestay as H
from game.careers import kit
from game.engine import GameError, public_state
from tests.helpers import Journey
from tests.test_career_homestay import counted, find


def checkin_to_rooms():
    """A check-in counted and decided, waiting for its room (no booking in the way, every room clean)."""
    day, slot = find('checkin', lambda t: t['_x']['adults'] == t['needs']['adults'] and t['_x']['kids'] == t['needs']['kids'])
    j = Journey('homestay', slot=slot, day=day)
    d = j.c['ext']['data']
    d['bookings'], d['ota'] = [], []
    for rid in ('thong', 'suong', 'gac', 'quy'):
        d['rooms'][rid].update(status='clean', q=5, guest=None, task=None, until=0, hk=None)
    tid = j.task['id']
    j.act('ask', task=tid)
    j.act('hs_verify', task=tid, entry=j.get(tid)['_x']['match'])
    j.act('hs_ids', task=tid, mode='look')
    j.act('hs_count', task=tid)
    if j.get(tid)['ci']['extra'] is None:
        j.act('hs_extra', task=tid, choice='surcharge')
    return j, tid


class AssignCan(unittest.TestCase):
    def setUp(self):
        self.j, self.tid = checkin_to_rooms()
        self.data = self.j.c['ext']['data']

    def can(self):
        return public_state(self.j.state)['careers']['homestay']['data']['can']['hs_assign'][self.tid]

    def pending_order(self, room):
        self.data['ota'].append(dict(id='ota-w5', ota='Đi Đâu', name='Khách app', room=room, start=self.j.c['day'], nights=1,
                                     guests=2, total=60, net=51, status='new', rooms=[], day=self.j.c['day']))

    def test_free_rooms_can_go(self):
        can = self.can()
        self.assertIs(can['thong'], True)
        locked = [r['id'] for r in H.ROOMS if r['unlock'] > kit.level(self.j.c)]
        self.assertFalse(set(locked) & set(can), 'a locked room is not offered at all')

    def test_room_with_an_order_waiting_to_sync_says_why_and_points_at_the_orders(self):
        self.pending_order('suong')
        can = self.can()['suong']
        self.assertIn('chờ đồng bộ', can['why'])
        self.assertEqual(can['fix'], H.OTA_FIX)
        self.assertIs(self.can()['thong'], True)

    def test_same_words_as_the_refusal(self):
        self.pending_order('suong')
        why = self.can()['suong']['why']
        with self.assertRaises(GameError) as err:
            self.j.act('hs_assign', task=self.tid, rooms=['suong'])
        self.assertEqual(str(err.exception), why)
        self.assertEqual(self.j.get(self.tid)['ci']['rooms'], [])

    def test_a_booked_room_has_no_fix(self):
        self.data['bookings'].append(dict(id='bk-w5', rooms=['quy'], start=self.j.c['day'], nights=1, guests=2, name='Khách X',
                                          total=48, deposit=15, task=None))
        can = self.can()['quy']
        self.assertIn('đã có khách đặt', can['why'])
        self.assertIsNone(can['fix'])

    def test_view_only_and_gone_once_assigned(self):
        before = repr(self.data)
        self.can()
        self.assertEqual(repr(self.data), before, 'the pre-check never writes the save')
        need = max(counted(self.j.get(self.tid)['_x']['adults'], self.j.get(self.tid)['_x']['kids']), self.j.get(self.tid)['needs']['size'])
        room = next(r['id'] for r in H.ROOMS if r['cap'] >= need and r['unlock'] == 1)
        self.j.act('hs_assign', task=self.tid, rooms=[room])
        self.assertNotIn(self.tid, public_state(self.j.state)['careers']['homestay']['data']['can']['hs_assign'])
        self.assertNotIn('can', self.j.c['ext']['data'])


class PickCan(unittest.TestCase):
    def test_fourth_place_says_why(self):
        self.assertIs(kit.check(H._pick_more_rules, ['a', 'b']), True)
        can = kit.check(H._pick_more_rules, ['a', 'b', 'c'])
        self.assertEqual(can['why'], 'Gợi ý tối đa 3 nơi thôi, nhiều quá khách rối.')
        self.assertEqual(can['fix']['sel'], '.hs-place.selected')

    def test_the_command_refuses_with_the_same_words_and_the_view_carries_it(self):
        day, slot = find('recommend')
        j = Journey('homestay', slot=slot, day=day)
        tid = j.task['id']
        j.act('ask', task=tid)
        places = [p['id'] for p in H.PLACES]
        view = lambda: next(t for t in public_state(j.state)['careers']['homestay']['tasks'] if t['id'] == tid)
        self.assertIs(view()['can']['hs_pick'], True)
        for p in places[:3]:
            j.act('hs_pick', task=tid, place=p)
        why = view()['can']['hs_pick']['why']
        with self.assertRaises(GameError) as err:
            j.act('hs_pick', task=tid, place=places[3])
        self.assertEqual(str(err.exception), why)
        j.act('hs_pick', task=tid, place=places[0])      # a picked place still comes off
        self.assertIs(view()['can']['hs_pick'], True)
        self.assertNotIn('can', j.get(tid))


if __name__ == '__main__':
    unittest.main()
