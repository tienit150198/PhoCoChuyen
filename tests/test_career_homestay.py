import copy
import json
import re
import unittest

import game.careers.kit as kit
from game.engine import GameError, public_state, validate_state
from game.careers import homestay as H
from tests.helpers import Journey
from game import consequences as cq


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t


def find(job, pred=lambda t: True, days=range(1, 40)):
    """A plain ticket of this job (v0.5 special cases have their own tests below)."""
    for day in days:
        for slot in range(12):
            t = H.make_task(day, slot, 1)
            if t['job'] == job and not t['_x'].get('case') and pred(t):
                return day, slot
    raise AssertionError('no task for ' + job)


def counted(adults, kids):
    return adults + sum(1 for k in kids if k >= H.KID_FREE_AGE)


class HomestayTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def journey(self, job, pred=lambda t: True):
        day, slot = find(job, pred)
        return Journey('homestay', slot=slot, day=day)

    def review(self, j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def rooms(self, j):
        return j.c['ext']['data']['rooms']

    def make_clean(self, j, *rids):
        for rid in rids:
            self.rooms(j)[rid].update(status='clean', q=5, guest=None, task=None, until=0, hk=None)

    def clear_bookings(self, j):
        j.c['ext']['data']['bookings'] = []

    # ------------------------------------------------------------ check-in
    def do_checkin(self, j, rooms=None, extra='surcharge', heater=True):
        t = j.task
        tid = t['id']
        j.act('ask', task=tid)
        j.act('hs_verify', task=tid, entry=j.get(tid)['_x']['match'])
        j.act('hs_ids', task=tid, mode='look')
        j.act('hs_count', task=tid)
        t = j.get(tid)
        if t['ci']['extra'] is None:
            j.act('hs_extra', task=tid, choice=extra)
        staying = counted(t['_x']['adults'], t['_x']['kids']) if extra == 'surcharge' else counted(t['needs']['adults'], t['needs']['kids'])
        if rooms is None:
            # The booked room type counts too: a family that booked a 4-bed room is not squeezed into a 3-bed one.
            need = max(staying, t['needs']['size'])
            rooms = [next(r['id'] for r in H.ROOMS if r['cap'] >= need and r['unlock'] == 1 and self.rooms(j)[r['id']]['status'] == 'clean')]
        j.act('hs_assign', task=tid, rooms=rooms)
        if t['needs']['cold'] and heater:
            j.act('hs_heater', task=tid)
        return tid

    def test_checkin_happy_path_money_room_review(self):
        j = self.journey('checkin', lambda t: t['_x']['adults'] == t['needs']['adults'] and t['_x']['kids'] == t['needs']['kids'])
        self.clear_bookings(j)
        self.make_clean(j, 'thong', 'suong', 'gac', 'quy')
        money = j.c['money']
        gas = kit.stock(j.c, 'heater_gas')
        tid = self.do_checkin(j)
        t = j.get(tid)
        n = t['needs']
        j.act('hs_welcome', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        due = n['rate'] * n['nights'] - n['paid']
        self.assertEqual(t['ci']['paid'], due)
        self.assertGreaterEqual(j.c['money'], money + due)
        room = self.rooms(j)[t['ci']['rooms'][0]]
        self.assertEqual(room['status'], 'occupied')
        self.assertEqual(room['until'], j.c['day'] + n['nights'])
        if n['cold']:
            self.assertEqual(kit.stock(j.c, 'heater_gas'), gas - 1)
        post = self.review(j, tid)
        self.assertEqual(post['stars'] if not post['feedback'].get('unfair') else post['feedback']['fair'], 5)
        validate_state(json.loads(json.dumps(j.state)))

    def test_checkin_needs_hidden_and_privacy(self):
        j = self.journey('checkin')
        view = public_state(j.state)['careers']['homestay']['tasks'][0]
        self.assertIsNone(view['needs'])
        self.assertNotIn('_x', view)
        with self.assertRaises(GameError):
            j.act('hs_verify', entry='A')
        j.act('ask')
        view = public_state(j.state)['careers']['homestay']['tasks'][0]
        self.assertIn('list', view['needs'])
        self.assertNotIn('arrived', view)
        self.assertNotIn('match', json.dumps(view))
        j.act('hs_verify', entry=j.task['_x']['match'])
        r = j.act('hs_ids', mode='photo')
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['mistakes'], 1)
        self.assertFalse(j.task['ci']['ids'])
        j.act('hs_ids', mode='look')
        view = public_state(j.state)['careers']['homestay']['tasks'][0]
        self.assertIn('id_status', view)

    def test_checkin_wrong_entry_is_a_mistake(self):
        j = self.journey('checkin')
        j.act('ask')
        wrong = next(e['id'] for e in j.task['needs']['list'] if e['id'] != j.task['_x']['match'])
        r = j.act('hs_verify', entry=wrong)
        self.assertTrue(r.get('refused'))
        self.assertFalse(j.task['ci']['verified'])
        self.assertEqual(j.task['mistakes'], 1)
        with self.assertRaises(GameError):
            j.act('hs_verify', entry='Z')

    def test_checkin_room_rules(self):
        j = self.journey('checkin', lambda t: t['needs']['nights'] >= 2)
        self.clear_bookings(j)
        self.make_clean(j, 'thong', 'quy')
        self.rooms(j)['gac'].update(status='dirty', hk=None)
        tid = j.task['id']
        j.act('ask')
        j.act('hs_verify', entry=j.task['_x']['match'])
        j.act('hs_ids')
        j.act('hs_count')
        if j.task['ci']['extra'] is None:
            j.act('hs_extra', choice='surcharge')
        # A dirty room can be handed over now (the guest complains at the counter, see the consequences tests).
        with self.assertRaises(GameError):      # locked / maintenance
            j.act('hs_assign', rooms=['ho'])
        with self.assertRaises(GameError):      # bad payload
            j.act('hs_assign', rooms='quy')
        j.c['ext']['data']['bookings'].append(dict(id='bk-x', rooms=['quy'], start=j.c['day'] + 1, nights=1, guests=2, name='Khách X',
                                                   total=48, deposit=15, task=None))
        with self.assertRaises(GameError):      # overlaps a booking tomorrow night
            j.act('hs_assign', rooms=['quy'])
        with self.assertRaises(GameError):      # cannot welcome before assigning
            j.act('hs_welcome', confirm=True)
        self.assertNotIn(j.get(tid)['status'], ('completed', 'referred'))

    def test_extra_guest_surcharge_and_refuse(self):
        pred = lambda t: counted(t['_x']['adults'], t['_x']['kids']) > counted(t['needs']['adults'], t['needs']['kids'])
        j = self.journey('checkin', pred)
        self.clear_bookings(j)
        self.make_clean(j, 'thong', 'suong', 'gac', 'quy')
        n = j.task['needs']
        extra = counted(j.task['_x']['adults'], j.task['_x']['kids']) - counted(n['adults'], n['kids'])
        tid = self.do_checkin(j, extra='surcharge')
        small = next(r['id'] for r in H.ROOMS if r['cap'] < counted(j.task['_x']['adults'], j.task['_x']['kids']))
        with self.assertRaises(GameError):
            j.act('hs_assign', task=tid, rooms=[small])
        j.act('hs_welcome', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['ci']['paid'], n['rate'] * n['nights'] - n['paid'] + H.EXTRA_GUEST * extra * n['nights'])
        j2 = self.journey('checkin', pred)
        self.clear_bookings(j2)
        self.make_clean(j2, 'thong', 'suong', 'gac', 'quy')
        tid2 = self.do_checkin(j2, extra='refuse')
        j2.act('hs_welcome', task=tid2, confirm=True)
        t2 = j2.get(tid2)
        self.assertEqual(t2['ci']['extra'], 'refuse')
        self.assertTrue(t2['ci']['could_fit'])
        fair = next(x for x in self.review(j2, tid2)['feedback']['criteria'] if x['key'] == 'fair')
        self.assertEqual(fair['score'], 3)

    def test_cold_night_without_heater_lowers_review(self):
        j = self.journey('checkin', lambda t: t['needs']['cold'] and t['_x']['adults'] == t['needs']['adults'] and t['_x']['kids'] == t['needs']['kids'])
        self.clear_bookings(j)
        self.make_clean(j, 'thong', 'suong', 'gac', 'quy')
        tid = self.do_checkin(j, heater=False)
        j.act('hs_welcome', task=tid, confirm=True)
        warmth = next(x for x in self.review(j, tid)['feedback']['criteria'] if x['key'] == 'warmth')
        self.assertEqual(warmth['score'], 2)

    # ------------------------------------------------------------ check-out
    def test_checkout_bill_overcharge_refused_then_exact(self):
        j = self.journey('checkout', lambda t: t['_x']['lost'] and t['_x']['water'] > H.FREE_WATER)
        tid = j.task['id']
        j.act('ask')
        with self.assertRaises(GameError):      # bill before inspecting the room
            j.act('hs_line', line='water', delta=1)
        view = public_state(j.state)['careers']['homestay']['tasks'][0]
        self.assertNotIn('check', view)
        j.act('hs_inspect')
        self.assertTrue(j.task['bound'])
        view = public_state(j.state)['careers']['homestay']['tasks'][0]
        self.assertIn('check', view)
        x = j.task['_x']
        for _ in range(x['water']):             # charges the two free bottles too
            j.act('hs_line', line='water', delta=1)
        r = j.act('hs_settle', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['disputes'], 1)
        for _ in range(H.FREE_WATER):
            j.act('hs_line', line='water', delta=-1)
        truth = H._truth_bill(j.task)
        for k, q in truth.items():
            for _ in range(q - j.task['bill'][k]):
                j.act('hs_line', line=k, delta=1)
        with self.assertRaises(GameError):
            j.act('hs_line', line='water', delta=5)
        with self.assertRaises(GameError):
            j.act('hs_line', line='minibar', delta=1)
        j.act('hs_return')
        money = j.c['money']
        room = j.task['room']
        j.act('hs_settle', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertGreaterEqual(j.c['money'], money + H._bill_total(truth))
        if room:
            self.assertEqual(self.rooms(j)[room]['status'], 'dirty')
        care = next(x for x in self.review(j, tid)['feedback']['criteria'] if x['key'] == 'care')
        self.assertEqual(care['score'], 5)
        validate_state(json.loads(json.dumps(j.state)))

    def test_checkout_undercharge_and_forgotten_item(self):
        j = self.journey('checkout', lambda t: t['_x']['lost'] and (t['_x']['noodles'] or t['needs']['laundry']))
        j.act('ask')
        j.act('hs_inspect')
        lost = len(j.c['ext']['data']['lost'])
        tid = j.task['id']
        j.act('hs_settle', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertGreaterEqual(t['mistakes'], 2)
        self.assertEqual(len(j.c['ext']['data']['lost']), lost + 1)

    # ------------------------------------------------------------ housekeeping
    def test_turnover_in_order_consumes_stock_and_scores(self):
        j = Journey('homestay')
        d = j.c['ext']['data']
        self.assertEqual(d['rooms']['gac']['status'], 'dirty')
        linen, towel = kit.stock(j.c, 'linen'), kit.stock(j.c, 'towel')
        with self.assertRaises(GameError):
            j.act('hs_clean', room='gac', step='bath')     # windows/strip first
        with self.assertRaises(GameError):
            j.act('hs_clean', room='thong', step='strip')  # already clean
        j.act('hs_clean', room='gac', step='strip')
        with self.assertRaises(GameError):
            j.act('hs_clean', room='gac', step='ready')
        for step in ('bath', 'bed', 'amenity', 'inspect'):
            j.act('hs_clean', room='gac', step=step)
        self.clock.t += 30
        r = j.act('hs_clean', room='gac', step='ready')
        room = j.c['ext']['data']['rooms']['gac']
        self.assertEqual(room['status'], 'clean')
        self.assertEqual(room['q'], 5)
        self.assertEqual(kit.stock(j.c, 'linen'), linen - 1)
        self.assertEqual(kit.stock(j.c, 'towel'), towel - 2)
        self.assertIn('5/5', r['message'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_turnover_wrong_order_and_bad_airing(self):
        j = Journey('homestay')
        soap = kit.stock(j.c, 'soap_kit')
        waste = len(j.c['life']['waste'])
        j.act('hs_clean', room='gac', step='strip')
        j.act('hs_clean', room='gac', step='amenity')     # before bathroom: soap kit gets wet
        self.assertEqual(kit.stock(j.c, 'soap_kit'), soap - 2)
        self.assertEqual(len(j.c['life']['waste']), waste + 1)
        for step in ('bath', 'bed', 'inspect'):
            j.act('hs_clean', room='gac', step=step)
        self.clock.t += 3                                 # windows barely opened
        j.act('hs_clean', room='gac', step='ready')
        self.assertLessEqual(j.c['ext']['data']['rooms']['gac']['q'], 3)

    def test_turnover_runs_out_of_linen(self):
        j = Journey('homestay')
        for lot in j.c['ext']['inv']['lots']:
            if lot['item'] == 'linen':
                lot['qty'] = 0
        j.act('hs_clean', room='gac', step='strip')
        j.act('hs_clean', room='gac', step='bath')
        with self.assertRaises(GameError):
            j.act('hs_clean', room='gac', step='bed')

    def test_repair_room(self):
        j = Journey('homestay')
        with self.assertRaises(GameError):          # Ban Công Hồ opens at level 3
            j.act('hs_repair', room='ho', confirm=True)
        d = j.c['ext']['data']
        d['rooms']['suong'].update(status='maintenance', note='Vòi sen rỉ nước', task=None, guest=None)
        with self.assertRaises(GameError):
            j.act('hs_repair', room='suong')
        money = j.c['money']
        j.act('hs_repair', room='suong', confirm=True)
        self.assertEqual(j.c['ext']['data']['rooms']['suong']['status'], 'dirty')
        self.assertLessEqual(j.c['money'], money - H.REPAIR_COST + 3)

    # ------------------------------------------------------------ breakfast
    def cook(self, j, egg_seconds=None):
        t = j.task
        n = t['needs']
        j.act('ask')
        for style, count in n['eggs'].items():
            for _ in range(count):
                j.act('hs_egg')
                self.clock.t += egg_seconds or (8 if style == 'runny' else 14)
                j.act('hs_plate')
        for key, action in (('bread', 'hs_bread'), ('milk', 'hs_milk'), ('coffee', 'hs_coffee')):
            for _ in range(n[key]):
                j.act(action)

    def test_breakfast_happy_path(self):
        j = self.journey('breakfast', lambda t: not t['needs']['allergy'])
        eggs = kit.stock(j.c, 'egg')
        self.cook(j)
        tid = j.task['id']
        n = j.task['needs']
        self.assertEqual(kit.stock(j.c, 'egg'), eggs - n['eggs']['runny'] - n['eggs']['well'])
        money = j.c['money']
        j.act('hs_serve', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['quoted_price'], H.SPEC['prices']['breakfast'] * n['people'])
        self.assertGreaterEqual(j.c['money'], money + t['quoted_price'])
        self.assertEqual(self.review(j, tid)['feedback']['criteria'][0]['score'], 5)

    def test_breakfast_raw_egg_refused_and_toss_logs_waste(self):
        j = self.journey('breakfast', lambda t: t['needs']['eggs']['runny'] + t['needs']['eggs']['well'] > 0)
        j.act('ask')
        j.act('hs_egg')
        self.clock.t += 2
        j.act('hs_plate')
        self.assertEqual(j.task['tray']['eggs'], ['raw'])
        j.act('hs_bread')
        r = j.act('hs_serve', confirm=True)
        self.assertTrue(r.get('refused'))
        waste = len(j.c['life']['waste'])
        j.act('hs_toss', confirm=True)
        self.assertEqual(len(j.c['life']['waste']), waste + 1)
        self.assertEqual(j.task['tray']['eggs'], [])
        validate_state(j.state)

    def test_breakfast_egg_allergy_refused(self):
        j = self.journey('breakfast', lambda t: t['needs']['allergy'] == 'egg')
        self.cook(j)
        j.act('hs_egg')
        self.clock.t += 8
        j.act('hs_plate')
        r = j.act('hs_serve', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn('dị ứng', r['message'])

    def test_breakfast_burnt_egg_lowers_taste(self):
        j = self.journey('breakfast', lambda t: not t['needs']['allergy'] and t['needs']['eggs']['well'])
        self.cook(j, egg_seconds=40)
        tid = j.task['id']
        j.act('hs_serve', confirm=True)
        self.assertEqual(self.review(j, tid)['feedback']['criteria'][0]['score'], 2)

    # ------------------------------------------------------------ booking
    def test_booking_hold_rules_deposit_and_arrival(self):
        j = self.journey('booking', lambda t: t['needs']['start'] > t['day'] and counted(t['needs']['adults'], t['needs']['kids']) <= 2 and t['needs']['stairs_ok'])
        self.clear_bookings(j)
        self.make_clean(j, 'thong', 'suong', 'gac', 'quy')
        j.act('ask')
        n = j.task['needs']
        with self.assertRaises(GameError):
            j.act('hs_hold', rooms=['ho'])                  # locked
        with self.assertRaises(GameError):
            j.act('hs_hold', rooms=['thong', 'thong'])      # duplicates
        j.c['ext']['data']['bookings'].append(dict(id='bk-x', rooms=['thong'], start=n['start'], nights=1, guests=2, name='X', total=30, deposit=9, task=None))
        with self.assertRaises(GameError):
            j.act('hs_hold', rooms=['thong'])               # overbooking
        with self.assertRaises(GameError):
            j.act('hs_book', confirm=True)                  # nothing held
        j.act('hs_hold', rooms=['suong'])
        quote = j.task['quote']
        self.assertEqual(quote['total'], H.SPEC['prices']['suong'] * n['nights'])
        self.assertEqual(quote['deposit'], -(-quote['total'] * 30 // 100))
        money = j.c['money']
        tid = j.task['id']
        j.act('hs_book', confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertGreaterEqual(j.c['money'], money + quote['deposit'])
        booking = next(b for b in j.c['ext']['data']['bookings'] if b['task'] == tid)
        self.assertEqual(booking['rooms'], ['suong'])
        grid = public_state(j.state)['careers']['homestay']['data']['grid']['suong']
        self.assertTrue(any(cell['kind'] == 'book' for cell in grid))
        # Close days until the guest arrives: the room is clean, so they check in and pay the balance.
        while j.c['day'] < n['start']:
            j.act('end_day')
            j.act('start_day')
        before = j.c['money']
        j.act('end_day')
        self.assertEqual(j.c['ext']['data']['rooms']['suong']['status'], 'occupied')
        self.assertTrue(any(x['kind'] == 'money' for x in j.c['journal']))
        self.assertGreaterEqual(j.c['money'], before - 200)
        validate_state(json.loads(json.dumps(j.state)))

    def test_booking_capacity_needs_two_rooms(self):
        j = self.journey('booking', lambda t: counted(t['needs']['adults'], t['needs']['kids']) >= 5)
        self.clear_bookings(j)
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('hs_hold', rooms=['quy'])
        j.act('hs_hold', rooms=['quy', 'gac'])
        self.assertEqual(len(j.task['hold']), 2)
        j.act('hs_release')
        self.assertEqual(j.task['hold'], [])

    def test_booking_elderly_stairs_is_a_mistake_and_decline(self):
        j = self.journey('booking', lambda t: not t['needs']['stairs_ok'] and t['needs']['start'] > t['day'])
        self.clear_bookings(j)
        j.act('ask')
        j.act('hs_hold', rooms=['gac'])
        tid = j.task['id']
        j.act('hs_book', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['mistakes'], 1)
        fit = next(x for x in self.review(j, tid)['feedback']['criteria'] if x['key'] == 'fit')
        self.assertEqual(fit['score'], 3)
        # Declining while rooms are free is an honest-status mistake.
        j2 = self.journey('booking', lambda t: t['needs']['start'] > t['day'])
        self.clear_bookings(j2)
        j2.act('ask')
        tid2 = j2.task['id']
        j2.act('hs_decline', confirm=True)
        t2 = j2.get(tid2)
        self.assertEqual(t2['status'], 'referred')
        self.assertFalse(t2['decline_ok'])
        self.assertEqual(t2['mistakes'], 1)

    def test_arrival_with_dirty_room_is_walked(self):
        j = Journey('homestay')
        d = j.c['ext']['data']
        d['bookings'] = [dict(id='bk-t', rooms=['gac'], start=j.c['day'], nights=1, guests=3, name='Đoàn thử', total=36, deposit=11, task=None)]
        for rid in ('thong', 'quy'):
            d['rooms'][rid].update(status='dirty')
        money = j.c['money']
        j.act('end_day')
        self.assertEqual(j.c['ext']['data']['walked'], 1)
        self.assertEqual(j.c['ext']['data']['bookings'], [])
        self.assertLessEqual(j.c['money'], money)

    def test_arrival_moves_to_other_clean_room(self):
        j = Journey('homestay')
        d = j.c['ext']['data']
        d['bookings'] = [dict(id='bk-t', rooms=['gac'], start=j.c['day'], nights=2, guests=3, name='Đoàn thử', total=72, deposit=22, task=None)]
        j.act('end_day')
        self.assertEqual(j.c['ext']['data']['rooms']['quy']['status'], 'occupied')
        self.assertEqual(j.c['ext']['data']['arrivals'], 1)

    def test_departures_leave_rooms_dirty(self):
        j = Journey('homestay')
        d = j.c['ext']['data']
        d['rooms']['thong'].update(status='occupied', guest='Khách A', task=None, until=j.c['day'] + 1)
        j.act('end_day')
        j.act('start_day')
        self.assertEqual(j.c['ext']['data']['rooms']['thong']['status'], 'dirty')

    # ------------------------------------------------------------ recommendations
    def test_recommend_probe_and_fit(self):
        j = self.journey('recommend', lambda t: any(p['avoid'] for p in t['_x']['probes'].values()))
        j.act('ask')
        view = public_state(j.state)['careers']['homestay']['tasks'][0]
        self.assertEqual(view['answers'], {})
        probes = j.task['_x']['probes']
        hidden_q = next(q for q, p in probes.items() if p['avoid'])
        j.act('hs_probe', q=hidden_q)
        view = public_state(j.state)['careers']['homestay']['tasks'][0]
        self.assertIn(hidden_q, view['answers'])
        with self.assertRaises(GameError):
            j.act('hs_probe', q=hidden_q)
        with self.assertRaises(GameError):
            j.act('hs_probe', q='salary')
        avoid = set(probes[hidden_q]['avoid'])
        bad = next(p['id'] for p in H.PLACES if avoid & set(p['tags']))
        j.act('hs_pick', place=bad)
        j.act('hs_pick', place=bad)          # toggles off
        self.assertEqual(j.task['picks'], [])
        n = j.task['needs']
        all_avoid = set(n['avoid']) | {a for p in probes.values() for a in p['avoid']}
        wants = set(n['wants']) | {w for p in probes.values() for w in p['want']}
        good = [p['id'] for p in H.PLACES if not (set(p['tags']) & all_avoid)]
        good.sort(key=lambda pid: -len(wants & set(H.PLACE_INDEX[pid]['tags'])))
        for pid in good[:3]:
            j.act('hs_pick', place=pid)
        for q in probes:
            if q not in j.task['inspected']:
                j.act('hs_probe', q=q)
        tid = j.task['id']
        j.act('hs_advise', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        fit = next(x for x in self.review(j, tid)['feedback']['criteria'] if x['key'] == 'fit')
        self.assertEqual(fit['score'], 5)

    def test_recommend_violation_counts(self):
        j = self.journey('recommend', lambda t: any(p['avoid'] for p in t['_x']['probes'].values()))
        j.act('ask')
        probes = j.task['_x']['probes']
        avoid = {a for p in probes.values() for a in p['avoid']}
        bad = [p['id'] for p in H.PLACES if avoid & set(p['tags'])][:2]
        for pid in bad:
            j.act('hs_pick', place=pid)
        with self.assertRaises(GameError):
            j.act('hs_advise')
        tid = j.task['id']
        j.act('hs_advise', confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], len(bad))

    # ------------------------------------------------------------ validation & content
    def test_wrong_job_action_rejected(self):
        j = self.journey('breakfast')
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('hs_inspect')
        with self.assertRaises(GameError):
            j.act('hs_fly')

    def test_tampered_fixed_and_data_rejected(self):
        j = Journey('homestay')
        s = copy.deepcopy(j.state)
        s['careers']['homestay']['tasks'][0]['_x']['adults'] = 9 if s['careers']['homestay']['tasks'][0]['job'] == 'checkin' else 1
        s['careers']['homestay']['tasks'][0]['needs'] = {'hack': 1}
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['homestay']['ext']['data']['rooms']['thong']['status'] = 'palace'
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['homestay']['ext']['data']['bookings'][0]['deposit'] = 10**6
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        t = next(x for x in s['careers']['homestay']['tasks'] if x['job'] == 'checkout')
        t['bill']['water'] = 99
        with self.assertRaises(GameError):
            validate_state(s)

    def test_days_generate_valid_tasks(self):
        for day in range(1, 15):
            for slot in range(12):
                t = H.make_task(day, slot, 3)
                self.assertEqual(t, H.make_task(day, slot, 3))
                self.assertEqual(json.loads(json.dumps(t)), t)
                self.assertIn(t['job'], H.JOB_NAMES)

    def test_staff_assist(self):
        j = Journey('homestay')
        e = dict(role='housekeeping')
        msg = H.assist(j.state, j.c, e, j.task)
        self.assertIn('Gác Mái', msg)
        self.assertIsNotNone(j.c['ext']['data']['rooms']['gac']['hk'])
        validate_state(j.state)

    def test_all_situations_playable(self):
        j = Journey('homestay')
        self.assertTrue(5 <= len(H.SPEC['situations']) <= 8)
        for x in H.SPEC['situations']:
            for opt in x['options']:
                self.assertGreaterEqual(len(opt['perspectives']), 2)
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_full_day_with_real_situation(self):
        j = Journey('homestay')
        tid = j.task['id']
        j.act('ask', task=tid)
        # finish the breakfast task for a real completion, then a situation opens
        bid = next(t['id'] for t in j.c['tasks'] if t['job'] == 'breakfast')
        j.act('task_select', task=bid)
        self.cook(j)
        j.act('hs_serve', confirm=True)
        self.assertIsNotNone(j.c['ext']['situation'])
        validate_state(json.loads(json.dumps(j.state)))


def pick(pred, days=range(1, 60), slots=range(12)):
    for day in days:
        for slot in slots:
            t = H.make_task(day, slot, 1)
            if pred(t):
                return day, slot
    raise AssertionError('no matching task')


class HomestayV2Tests(unittest.TestCase):
    """v0.5: day markets, app orders and double bookings, seasonal rates, bank checks, packages, hidden allergies,
    lost-and-found calls, counter surprises."""

    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def at(self, day, slot, ask=True):
        j = Journey('homestay', slot=slot, day=day)
        self.fund(j)
        if ask:
            j.act('ask', task=j.task['id'])
        return j

    def fund(self, j, target=500):
        if j.c['money'] < target:
            kit.money(j.state, j.c, target - j.c['money'], 'Vốn đầu mùa', None, 'event_income')

    def gen(self, pred, days=range(1, 60), ask=True):
        return self.at(*pick(pred, days), ask=ask)

    def data(self, j):
        return j.c['ext']['data']

    def pub(self, j):
        return public_state(j.state)['careers']['homestay']

    def view(self, j):
        return next(v for v in self.pub(j)['tasks'] if v['id'] == j.task['id'])

    def review(self, j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def crit(self, j, tid, key):
        return next(x for x in self.review(j, tid)['feedback']['criteria'] if x['key'] == key)

    def ok(self, j):
        validate_state(json.loads(json.dumps(j.state)))

    def free_rooms(self, j):
        d = self.data(j)
        d['bookings'] = []
        for rid in ('thong', 'suong', 'gac', 'quy'):
            d['rooms'][rid].update(status='clean', q=5, guest=None, task=None, until=0, hk=None)

    def order(self, j, room, start=None, nights=1, guests=2, oid='ota-t1'):
        o = dict(id=oid, ota='Mây Travel', name='Lý Gia Hân', room=room, start=j.c['day'] if start is None else start, nights=nights,
                 guests=guests, total=30, net=25, status='new', rooms=[], day=j.c['day'])
        self.data(j)['ota'].append(o)
        return o

    def ota(self, j, oid='ota-t1'):
        return next(o for o in self.data(j)['ota'] if o['id'] == oid)

    # ------------------------------------------------------------ day, difficulty, generator
    def test_daily_modifier_is_deterministic_and_never_repeats(self):
        self.assertEqual(H.today(1)['id'], 'steady')
        seen = set()
        for d in range(1, 80):
            m = H.today(d)
            self.assertEqual(m, H.today(d))
            self.assertNotEqual(m['id'], H.today(d + 1)['id'])
            self.assertLessEqual(m.get('min_day', 1), d)
            seen.add(m['id'])
        self.assertEqual(seen, {x['id'] for x in H.TODAY})

    def test_new_tasks_are_marked_and_old_serials_use_the_old_generator(self):
        t = H.make_task(3, 2, 7)
        self.assertEqual(t['gen'], H.GEN)
        old = H.make_task(3, 2, kit.LEGACY_TURN + 7)
        self.assertNotIn('gen', old)
        self.assertEqual(old, H._make_v1(3, 2, kit.LEGACY_TURN + 7))

    def test_same_guest_never_twice_in_one_day(self):
        for d in range(1, 120):
            tasks = [H.make_task(d, sl, 1) for sl in range(4)]
            people = [t['npc'] for t in tasks]
            self.assertEqual(len(people), len(set(people)), (d, people))
            if d > 1:      # and nobody checks out (or books, or calls) two mornings in a row
                before = {(t['job'], t['npc']) for t in (H.make_task(d - 1, sl, 1) for sl in range(4))}
                self.assertFalse(before & {(t['job'], t['npc']) for t in tasks}, d)

    def test_difficulty_grows_with_the_day(self):
        j = self.gen(lambda t: t['needs']['today'] == 'steady', range(12, 60), ask=False)
        self.assertEqual(j.task['patience'], 88)
        j = self.gen(lambda t: t['needs']['today'] == 'festival', range(12, 60), ask=False)
        self.assertEqual(j.task['patience'], 82)
        j = self.gen(lambda t: t['day'] == 1, range(1, 2), ask=False)
        self.assertEqual(j.task['patience'], 100)
        specials = lambda days: sum(1 for d in days for sl in range(1, 6) if H.make_task(d, sl, 1)['_x'].get('case') not in (None, 'claim'))
        self.assertLess(specials(range(1, 4)), specials(range(12, 15)))
        early = H.make_task(*pick(lambda t: t['job'] == 'checkin', range(1, 6)), 1)
        late = H.make_task(*pick(lambda t: t['job'] == 'checkin', range(10, 30)), 1)
        self.assertEqual(sum(1 for e in early['needs']['list'] if e['start'] == early['day']), 2)
        self.assertEqual(sum(1 for e in late['needs']['list'] if e['start'] == late['day']), 3)   # the look-alike code arrives today too

    # ------------------------------------------------------------ app orders (OTA)
    def test_morning_brings_app_orders(self):
        j = Journey('homestay')
        self.assertEqual(self.data(j)['ota'], [])
        j.act('end_day')
        j.act('start_day')
        orders = [o for o in self.data(j)['ota'] if o['status'] == 'new']
        self.assertGreaterEqual(len(orders), 1)
        for o in orders:
            self.assertEqual(o['net'], o['total'] - -(-o['total'] * H.OTA_COMMISSION // 100))
            self.assertGreaterEqual(o['start'], j.c['day'])
        self.assertTrue(any('đơn OTA mới' in x['text'] for x in j.c['journal']))
        self.assertEqual([o['id'] for o in self.pub(j)['data']['ota'] if o['status'] == 'new'], [o['id'] for o in orders])
        self.ok(j)

    def test_warned_channel_sends_fewer_orders(self):
        j = self.at(*pick(lambda t: t['needs']['today'] == 'festival', range(3, 30)), ask=False)
        base = copy.deepcopy(j.state)
        H._ota_new(j.state, j.c, 'festival')
        normal = len(self.data(j)['ota'])
        j.state = copy.deepcopy(base)
        self.data(j)['desk']['marks']['ota_warn'] = j.c['day']
        H._ota_new(j.state, j.c, 'festival')
        self.assertEqual(len(self.data(j)['ota']), normal - 1)

    def test_sync_order_into_its_room(self):
        j = self.at(3, 0, ask=False)
        self.free_rooms(j)
        self.order(j, 'thong', start=4, nights=2)
        money = j.c['money']
        r = j.act('hs_sync', order='ota-t1', rooms=['thong'])
        self.assertTrue(r.get('celebrate'))
        self.assertEqual(self.ota(j)['status'], 'synced')
        b = next(b for b in self.data(j)['bookings'] if b['id'] == 'ota-t1')
        self.assertEqual((b['rooms'], b['start'], b['nights'], b['ota'], b['deposit']), (['thong'], 4, 2, 'Mây Travel', 0))
        self.assertEqual(j.c['money'], money)
        with self.assertRaises(GameError):
            j.act('hs_sync', order='ota-t1', rooms=['thong'])      # already handled
        with self.assertRaises(GameError):
            j.act('hs_sync', order='ota-zz', rooms=['suong'])
        self.assertEqual(self.data(j)['synced'], 1)
        self.ok(j)

    def test_double_booking_must_be_rehoused(self):
        j = self.at(3, 0, ask=False)
        self.free_rooms(j)
        self.data(j)['bookings'].append(dict(id='bk-x', rooms=['thong'], start=3, nights=2, guests=2, name='X', total=60, deposit=18, task=None))
        self.order(j, 'thong', start=4, nights=1, guests=2)
        with self.assertRaises(GameError):
            j.act('hs_sync', order='ota-t1', rooms=['thong'])       # sold twice
        with self.assertRaises(GameError):
            j.act('hs_sync', order='ota-t1', rooms=['ho'])          # locked
        with self.assertRaises(GameError):
            j.act('hs_sync', order='ota-t1', rooms=[])
        self.assertEqual(self.ota(j)['status'], 'new')
        money = j.c['money']
        r = j.act('hs_sync', order='ota-t1', rooms=['quy'])         # bigger room: free upgrade
        self.assertIn('nâng hạng', r['message'])
        self.assertEqual(j.c['money'], money)
        self.assertEqual(self.ota(j)['rooms'], ['quy'])
        # A cheaper room means the difference goes back to the guest (after the platform's cut).
        self.order(j, 'gac', start=5, nights=2, guests=2, oid='ota-t2')
        self.data(j)['bookings'].append(dict(id='bk-y', rooms=['gac'], start=5, nights=1, guests=2, name='Y', total=36, deposit=11, task=None))
        with self.assertRaises(GameError):
            j.act('hs_sync', order='ota-t2', rooms=['gac'])
        money = j.c['money']
        j.act('hs_sync', order='ota-t2', rooms=['suong'])
        refund = -(-(36 - 28) * 2 * (100 - H.OTA_COMMISSION) // 100)
        self.assertEqual(j.c['money'], money - refund)
        self.ok(j)

    def test_sync_checks_capacity(self):
        j = self.at(3, 0, ask=False)
        self.free_rooms(j)
        self.order(j, 'quy', start=4, guests=4)
        with self.assertRaises(GameError):
            j.act('hs_sync', order='ota-t1', rooms=['suong'])
        j.act('hs_sync', order='ota-t1', rooms=['suong', 'thong'])
        self.assertEqual(self.ota(j)['rooms'], ['suong', 'thong'])

    def test_walk_to_the_neighbour_needs_confirm_and_counts_a_strike_when_rooms_were_free(self):
        j = self.at(3, 0, ask=False)
        self.free_rooms(j)
        self.order(j, 'thong', start=4)
        with self.assertRaises(GameError):
            j.act('hs_walk', order='ota-t1')
        money = j.c['money']
        r = j.act('hs_walk', order='ota-t1', confirm=True)
        self.assertIn('vẫn còn phòng', r['message'])
        d = self.data(j)
        self.assertEqual((self.ota(j)['status'], d['strikes'], d['ota_walked'], j.c['money']), ('walked', 1, 1, money - H.WALK_FEE))
        self.assertIn('ota_walk', d['desk']['marks'])
        self.assertFalse(any(p['kind'] == 'review' and p['source'] == 'ota-t1' for p in j.c['feed']))   # arranged: no angry review
        # When every room is really taken, sending the guest next door is the right call.
        j = self.at(3, 0, ask=False)
        d = self.data(j)
        d['bookings'] = [dict(id=f'bk-{r}', rooms=[r], start=4, nights=1, guests=2, name='X', total=30, deposit=9, task=None)
                         for r in ('thong', 'suong', 'gac', 'quy')]
        self.order(j, 'thong', start=4)
        j.act('hs_walk', order='ota-t1', confirm=True)
        self.assertEqual(self.data(j)['strikes'], 0)
        self.ok(j)

    def test_unsynced_orders_at_closing(self):
        j = Journey('homestay')
        self.fund(j)
        self.order(j, 'thong')
        j.act('end_day')
        self.assertEqual(self.ota(j)['status'], 'auto')
        self.assertEqual(self.data(j)['rooms']['thong']['status'], 'occupied')
        self.assertTrue(any('may mà phòng' in x for x in j.c['shift_summary']['career']['lines']))
        # Sold twice and nobody noticed: the guest is walked at night and writes 1 star.
        j = Journey('homestay')
        self.fund(j)
        self.data(j)['bookings'].append(dict(id='bk-x', rooms=['thong'], start=1, nights=1, guests=2, name='X', total=30, deposit=9, task=None))
        self.order(j, 'thong')
        j.act('end_day')
        d = self.data(j)
        self.assertEqual((self.ota(j)['status'], d['strikes'], d['ota_walked']), ('walked', 1, 1))
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == 'ota-t1')
        self.assertEqual(post['stars'], 1)
        self.assertTrue(any('Nhà Gỗ Cô Ba' in x for x in j.c['shift_summary']['career']['lines']))
        self.assertIn('otacall', [x['id'] for x in kit._desk_pool('homestay', dict(j.c, day=4), d['desk'], H.DESK, 'between', 'steady')])
        self.ok(j)

    def test_room_of_a_guest_leaving_today_can_be_sold_from_tomorrow(self):
        j = self.at(3, 0, ask=False)
        self.free_rooms(j)
        self.data(j)['rooms']['gac'].update(status='occupied', guest='Khách X', task=j.task['id'], until=3)
        self.order(j, 'gac', start=3, oid='ota-a')
        self.order(j, 'gac', start=4, oid='ota-b')
        with self.assertRaises(GameError):
            j.act('hs_sync', order='ota-a', rooms=['gac'])        # still in the room tonight
        j.act('hs_sync', order='ota-b', rooms=['gac'])
        grid = self.pub(j)['data']['grid']['gac']
        self.assertEqual((grid[0]['kind'], grid[1]['kind']), ('occ', 'book'))

    def test_receptionist_syncs_only_easy_orders(self):
        j = self.at(3, 0, ask=False)
        self.free_rooms(j)
        self.data(j)['bookings'].append(dict(id='bk-x', rooms=['thong'], start=4, nights=1, guests=2, name='X', total=30, deposit=9, task=None))
        self.order(j, 'thong', start=4)
        self.assertIsNone(H.assist(j.state, j.c, dict(role='reception'), None))
        self.order(j, 'suong', start=4, oid='ota-t2')
        msg = H.assist(j.state, j.c, dict(role='reception'), None)
        self.assertIn('Sương', msg)
        self.assertEqual((self.ota(j)['status'], self.ota(j, 'ota-t2')['status']), ('new', 'synced'))

    # ------------------------------------------------------------ rates
    def booking(self, budget, mod):
        return self.gen(lambda t: t['job'] == 'booking' and t['_x']['budget'] == budget and t['needs']['today'] == mod
                        and t['needs']['start'] > t['day'] and counted(t['needs']['adults'], t['needs']['kids']) <= 2)

    def test_tight_budget_on_a_quiet_day_needs_the_low_rate(self):
        j = self.booking('tight', 'low')
        self.free_rooms(j)
        tid = j.task['id']
        with self.assertRaises(GameError):
            j.act('hs_rate', rate='low')                       # nothing held yet
        j.act('hs_hold', rooms=['suong'])
        self.assertEqual(j.task['rate'], 'std')
        with self.assertRaises(GameError):
            j.act('hs_rate', rate='std')                       # already quoted
        with self.assertRaises(GameError):
            j.act('hs_rate', rate='vip')
        r = j.act('hs_book', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertEqual((j.task['haggles'], j.get(tid)['status'] in ('completed', 'referred')), (1, False))
        turn = j.c['turn']
        j.act('hs_rate', rate='low')
        self.assertEqual(j.c['turn'], turn)
        n = j.task['needs']
        self.assertEqual(j.task['quote']['total'], -(-H.SPEC['prices']['suong'] * n['nights'] * 85 // 100))
        j.act('hs_book', confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(self.crit(j, tid, 'price')['score'], 4)
        self.ok(j)

    def festival_booking(self):
        return self.gen(lambda t: t['job'] == 'booking' and t['needs']['today'] == 'festival' and t['_x']['budget'] in ('normal', 'flex')
                        and t['needs']['start'] > t['day'] and counted(t['needs']['adults'], t['needs']['kids']) <= 2)

    def test_festival_guests_accept_the_festival_rate(self):
        j = self.festival_booking()
        self.free_rooms(j)
        tid = j.task['id']
        j.act('hs_hold', rooms=['thong'], rate='peak')
        n = j.task['needs']
        self.assertEqual(j.task['quote']['total'], -(-30 * n['nights'] * 130 // 100))
        j.act('hs_book', confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(self.crit(j, tid, 'price')['score'], 5)
        # Selling the festival week at the plain price leaves money on the table.
        j = self.festival_booking()
        self.free_rooms(j)
        tid = j.task['id']
        j.act('hs_hold', rooms=['thong'])
        j.act('hs_book', confirm=True)
        self.assertEqual(self.crit(j, tid, 'price')['score'], 4)

    def test_plain_day_guest_refuses_the_festival_rate(self):
        j = self.booking('normal', 'steady')
        self.free_rooms(j)
        j.act('hs_hold', rooms=['thong'], rate='peak')
        r = j.act('hs_book', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn(H.PUSHBACK['normal'], r['message'])

    def test_budget_is_hidden_until_asked(self):
        j = self.booking('tight', 'low')
        self.assertNotIn('budget_say', self.view(j))
        self.assertNotIn('tight', json.dumps(self.view(j), ensure_ascii=False))
        r = j.act('hs_budget')
        self.assertIn(j.task['_x']['say'], r['message'])
        self.assertEqual(self.view(j)['budget_say'], j.task['_x']['say'])
        with self.assertRaises(GameError):
            j.act('hs_budget')

    # ------------------------------------------------------------ check-in deposits
    def transfer(self, received):
        j = self.gen(lambda t: t['job'] == 'checkin' and t['_x']['case'] == 'transfer' and t['_x']['received'] is received)
        self.free_rooms(j)
        tid = j.task['id']
        j.act('hs_verify', task=tid, entry=j.task['_x']['match'])
        j.act('hs_ids', task=tid, mode='look')
        j.act('hs_count', task=tid)
        if j.task['ci']['extra'] is None:
            j.act('hs_extra', task=tid, choice='surcharge')
        j.act('hs_assign', task=tid, rooms=['quy'])
        if j.task['needs']['cold']:
            j.act('hs_heater', task=tid)
        return j, tid

    def test_bank_app_catches_a_deposit_that_never_arrived(self):
        j, tid = self.transfer(False)
        n = j.task['needs']
        self.assertEqual(n['proof'], 'bank')
        self.assertNotIn('received', json.dumps(self.view(j)))
        r = j.act('hs_bank')
        self.assertIn('không có khoản', r['message'])
        with self.assertRaises(GameError):
            j.act('hs_bank')
        j.act('hs_welcome', confirm=True)
        t = j.get(tid)
        self.assertEqual((t['status'], t['mistakes'], t['ci']['paid']), ('completed', 0, n['rate'] * n['nights']))
        self.assertEqual(self.crit(j, tid, 'deposit')['score'], 5)
        self.assertEqual(self.data(j)['lost_deposit'], 0)
        self.ok(j)

    def test_trusting_the_screenshot_loses_the_deposit(self):
        j, tid = self.transfer(False)
        n = j.task['needs']
        j.act('hs_welcome', confirm=True)
        t = j.get(tid)
        self.assertEqual((t['mistakes'], t['ci']['paid']), (1, n['rate'] * n['nights'] - n['paid']))
        self.assertEqual(self.data(j)['lost_deposit'], n['paid'])
        self.assertEqual(self.crit(j, tid, 'deposit')['score'], 1)

    def test_bank_app_confirms_a_real_deposit(self):
        j, tid = self.transfer(True)
        n = j.task['needs']
        r = j.act('hs_bank')
        self.assertIn('đã nhận đủ cọc', r['message'])
        j.act('hs_welcome', confirm=True)
        self.assertEqual(j.get(tid)['ci']['paid'], n['rate'] * n['nights'] - n['paid'])
        app = self.gen(lambda t: t['job'] == 'checkin' and t['needs']['proof'] == 'app')
        with self.assertRaises(GameError):
            app.act('hs_bank')

    # ------------------------------------------------------------ a confirmed guest and a full house
    def counted_checkin(self):
        j = self.gen(lambda t: t['job'] == 'checkin' and t['needs'].get('proof') == 'app')
        self.free_rooms(j)
        tid = j.task['id']
        j.act('hs_verify', task=tid, entry=j.task['_x']['match'])
        j.act('hs_count', task=tid)
        if j.task['ci']['extra'] is None:
            j.act('hs_extra', task=tid, choice='refuse')
        return j, tid

    def fill(self, j, **room):
        for r in self.data(j)['rooms'].values():
            if r['status'] != 'maintenance':
                r.update(dict(status='occupied', guest='Khách ở dài', task=None, until=j.c['day'] + 9, hk=None), **room)

    def test_full_house_moves_a_confirmed_guest_next_door(self):
        j, tid = self.counted_checkin()
        n = j.task['needs']
        with self.assertRaises(GameError):
            j.act('hs_relocate')                                  # needs the confirm dialog
        money, before = j.c['money'], copy.deepcopy(j.get(tid))
        r = j.act('hs_relocate', confirm=True)                    # clean rooms are free: refused, nothing paid
        self.assertTrue(r.get('refused'))
        self.assertIn('vẫn nhận được', r['message'])
        t = j.get(tid)
        self.assertEqual((t['status'], t['mistakes'], j.c['money']), (before['status'], before['mistakes'] + 1, money))
        self.fill(j)
        walked = self.data(j)['walked']
        r = j.act('hs_relocate', confirm=True)
        self.assertIn('Cô Ba', r['message'])
        t = j.get(tid)
        self.assertEqual(t['status'], 'referred')
        self.assertEqual(j.c['money'], money - H.WALK_FEE - n['paid'])
        self.assertEqual(self.data(j)['walked'], walked + 1)
        self.assertEqual(self.crit(j, tid, 'promise')['score'], 2)
        self.assertEqual(self.crit(j, tid, 'recover')['score'], 4)
        self.assertEqual(sum(1 for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid), 1)
        with self.assertRaises(GameError):
            j.act('hs_relocate', task=tid, confirm=True)
        self.ok(j)

    def test_relocate_waits_for_the_count_and_for_rooms_leaving_today(self):
        j = self.gen(lambda t: t['job'] == 'checkin' and t['needs'].get('proof') == 'app')
        self.fill(j)
        tid = j.task['id']
        with self.assertRaises(GameError):
            j.act('hs_relocate', confirm=True)                    # not matched or counted yet
        j.act('hs_verify', task=tid, entry=j.task['_x']['match'])
        with self.assertRaises(GameError):
            j.act('hs_relocate', confirm=True)
        j.act('hs_count', task=tid)
        if j.task['ci']['extra'] is None:
            j.act('hs_extra', task=tid, choice='refuse')
        # A guest checking out today frees a room tonight — no need to send anyone away yet.
        self.data(j)['rooms']['quy'].update(task='homestay-leaving', until=j.c['day'])
        r = j.act('hs_relocate', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn('Dã Quỳ', r['message'])
        self.assertEqual(j.get(tid)['status'], 'in_progress')

    # ------------------------------------------------------------ packages & allergies
    def test_package_lines_are_not_charged(self):
        j = self.gen(lambda t: t['job'] == 'checkout' and (t['needs']['package'] or {}).get('free'))
        tid = j.task['id']
        j.act('hs_inspect')
        truth = H._truth_bill(j.task)
        for k in j.task['needs']['package']['free']:
            self.assertEqual(truth[k], 0)
        self.assertEqual(self.view(j)['truth_hint']['free_water'], H.FREE_WATER)
        j.act('hs_line', line='laundry', delta=1)
        r = j.act('hs_settle', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn(j.task['needs']['package']['name'], r['message'])
        j.act('hs_line', line='laundry', delta=-1)
        for k, q in truth.items():
            for _ in range(q):
                j.act('hs_line', line=k, delta=1)
        if j.task['_x']['lost']:
            j.act('hs_return')
        j.act('hs_settle', confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_family_package_gives_more_free_water(self):
        j = self.gen(lambda t: t['job'] == 'checkout' and (t['needs']['package'] or {}).get('water_free'))
        j.act('hs_inspect')
        self.assertEqual(H._truth_bill(j.task)['water'], max(0, j.task['_x']['water'] - 8))
        self.assertEqual(self.view(j)['truth_hint']['free_water'], 8)

    def cook(self, j, eggs):
        for item in ('egg', 'bread', 'milk', 'coffee'):
            if kit.stock(j.c, item) < 10:
                kit.add_lot(j.c, item, 10, 0, 5, 'test')
        for style, count in eggs.items():
            for _ in range(count):
                j.act('hs_egg')
                self.clock.t += 8 if style == 'runny' else 14
                j.act('hs_plate')
        n = j.task['needs']
        for key, action in (('bread', 'hs_bread'), ('milk', 'hs_milk'), ('coffee', 'hs_coffee')):
            for _ in range(n[key] - j.task['tray'][key]):
                j.act(action)

    def test_hidden_allergy_sends_the_tray_back(self):
        j = self.gen(lambda t: t['job'] == 'breakfast' and t['_x']['case'] == 'allergy')
        tid = j.task['id']
        self.assertNotIn('diet_say', self.view(j))
        self.cook(j, j.task['needs']['eggs'])
        r = j.act('hs_serve', confirm=True)
        self.assertTrue(r.get('refused'))
        self.assertIn('dị ứng', r['message'])
        self.assertEqual(self.view(j)['eggs_fix'], j.task['_x']['fix'])
        j.act('hs_toss', confirm=True)
        self.cook(j, j.task['_x']['fix'])
        j.act('hs_serve', confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(self.crit(j, tid, 'care')['score'], 2)
        # The tray was right the second time, but nobody asked about allergies first: the guest remembers.
        self.assertEqual([x['code'] for x in j.get(tid)['slips']], ['no_ask_allergy'])
        self.assertEqual(self.crit(j, tid, 'accuracy')['score'], 3)

    def test_asking_about_diet_first(self):
        j = self.gen(lambda t: t['job'] == 'breakfast' and t['_x']['case'] == 'allergy')
        tid = j.task['id']
        r = j.act('hs_diet')
        self.assertIn('dị ứng', r['message'])
        with self.assertRaises(GameError):
            j.act('hs_diet')
        self.assertIn('diet_say', self.view(j))
        self.cook(j, j.task['_x']['fix'])
        j.act('hs_serve', confirm=True)
        self.assertEqual((self.crit(j, tid, 'care')['score'], self.crit(j, tid, 'accuracy')['score'], j.get(tid)['mistakes']), (5, 5, 0))
        plain = self.gen(lambda t: t['job'] == 'breakfast' and not t['_x']['case'])
        self.assertIn(H.DIET_NONE, plain.act('hs_diet')['message'])

    # ------------------------------------------------------------ weather of the day
    def turnover(self, day, seconds):
        j = self.at(day, 0, ask=False)
        j.act('hs_clean', room='gac', step='strip')
        for step in ('bath', 'bed', 'amenity', 'inspect'):
            j.act('hs_clean', room='gac', step=step)
        self.clock.t += seconds
        j.act('hs_clean', room='gac', step='ready')
        return self.data(j)['rooms']['gac']['q']

    def test_rain_day_needs_longer_airing(self):
        rain = next(d for d in range(2, 30) if H.today(d)['id'] == 'rain')
        self.assertEqual(self.turnover(1, 20), 5)
        self.assertEqual(self.turnover(rain, 20), 4)
        self.assertEqual(self.turnover(rain, 30), 5)
        self.assertEqual(self.pub(self.at(rain, 0, ask=False))['data']['air'], H.AIR_RAIN)

    def test_cold_day_every_guest_needs_the_heater(self):
        days = [d for d in range(3, 40) if H.today(d)['id'] == 'cold']
        self.assertTrue(days)
        for d in days:
            for sl in range(6):
                t = H.make_task(d, sl, 1)
                if t['job'] == 'checkin':
                    self.assertTrue(t['needs']['cold'])

    def test_recommendations_follow_the_weather(self):
        t = H.make_task(*pick(lambda t: t['job'] == 'recommend' and t['needs']['today'] == 'rain'), 1)
        self.assertIn('slope', t['_x']['probes']['weather']['avoid'])
        t = H.make_task(*pick(lambda t: t['job'] == 'recommend' and t['needs']['today'] == 'festival'), 1)
        self.assertIn('crowd', t['_x']['probes']['ride']['avoid'])

    # ------------------------------------------------------------ lost-and-found calls
    def claim(self, kind):
        return self.gen(lambda t: t['job'] == 'claim' and t['_x']['kind'] == kind)

    def test_claim_answers_only_after_asking(self):
        j = self.claim('imposter')
        v = self.view(j)
        self.assertEqual(v['answers'], {})
        self.assertNotIn('imposter', json.dumps(v))
        self.assertIn('detail', v['needs']['entry'])
        j.act('hs_quiz', q='describe')
        self.assertEqual(list(self.view(j)['answers']), ['describe'])
        with self.assertRaises(GameError):
            j.act('hs_quiz', q='describe')
        with self.assertRaises(GameError):
            j.act('hs_quiz', q='salary')
        with self.assertRaises(GameError):
            j.act('hs_claim', choice='deny')
        with self.assertRaises(GameError):
            j.act('hs_claim', choice='burn', confirm=True)
        with self.assertRaises(GameError):
            j.act('hs_inspect')

    def test_claim_owner_gets_the_item(self):
        j = self.claim('owner')
        tid = j.task['id']
        for q in ('describe', 'room', 'booking'):
            j.act('hs_quiz', q=q)
        r = j.act('hs_claim', choice='give', confirm=True)
        self.assertTrue(r.get('celebrate'))
        t = j.get(tid)
        self.assertEqual((t['status'], t['mistakes'], self.data(j)['claims_ok']), ('completed', 0, 1))
        self.assertEqual(self.crit(j, tid, 'verify')['score'], 5)
        self.assertEqual(self.data(j)['lost'][-1]['status'], 'returned')
        self.ok(j)

    def test_claim_imposter_gets_nothing(self):
        j = self.claim('imposter')
        j.act('hs_quiz', q='describe')
        r = j.act('hs_claim', choice='deny', confirm=True)
        self.assertTrue(r.get('celebrate'))
        self.assertEqual(self.data(j)['lost'][-1]['status'], 'kept')
        j = self.claim('imposter')
        tid = j.task['id']
        j.act('hs_quiz', q='describe')
        r = j.act('hs_claim', choice='give', confirm=True)
        self.assertFalse(r.get('celebrate'))
        d = self.data(j)
        self.assertEqual((j.get(tid)['mistakes'], d['claims_bad']), (1, 1))
        self.assertEqual(self.review(j, tid)['stars'], 1)
        self.assertIn('lost_wrong', d['desk']['marks'])
        self.assertIn('lostwrong', [x['id'] for x in kit._desk_pool('homestay', j.c, d['desk'], H.DESK, 'between', 'steady')])
        self.ok(j)

    def test_claim_friend_needs_the_booker_to_confirm(self):
        j = self.claim('friend')
        j.act('hs_quiz', q='booking')
        self.assertIn('bạn đi cùng', self.view(j)['answers']['booking'])
        r = j.act('hs_claim', choice='channel', confirm=True)
        self.assertTrue(r.get('celebrate'))
        j = self.claim('friend')
        tid = j.task['id']
        j.act('hs_claim', choice='give', confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], 2)                 # wrong person and never asked to describe it

    # ------------------------------------------------------------ safety log & counter surprises
    def desk_day(self):
        day, slot = pick(lambda t: t['job'] == 'breakfast' and not t['_x']['case'], range(2, 4))
        self.assertEqual(kit.desk_plan('homestay', day), [2])
        return self.at(day, slot)

    def test_safety_log_once_a_day(self):
        j = self.at(3, 0, ask=False)
        self.assertFalse(self.pub(j)['data']['safe_today'])
        j.act('hs_safety')
        with self.assertRaises(GameError):
            j.act('hs_safety')
        self.assertTrue(self.pub(j)['data']['safe_today'])
        self.ok(j)

    def test_desk_surprise_blocks_work_until_decided(self):
        self.assertEqual(kit.desk_plan('homestay', 1), [])
        j = self.desk_day()
        j.act('hs_egg')
        j.c['day_completed'] = 2
        r = j.act('hs_bread')
        self.assertTrue(r.get('surprise'), r)
        desk = self.data(j)['desk']
        with self.assertRaises(GameError) as ctx:
            j.act('hs_coffee')
        self.assertEqual(ctx.exception.code, 'surprise_open')
        with self.assertRaises(GameError):
            j.act('hs_safety')
        self.clock.t += 8
        j.act('hs_plate')                                           # the egg in the pan can still be lifted out
        view = self.pub(j)['data']['desk']
        self.assertEqual(view['ev']['script'], desk['ev']['script'])
        for leak in ('luck', 'effects', 'good', 'outcome'):
            self.assertNotIn(leak, json.dumps(view['ev']))
        with self.assertRaises(GameError):
            j.act('hs_desk', option='nope')
        turn = j.c['turn']
        j.act('hs_desk', option=kit.desk_script(H.DESK, desk['ev']['script'])['default'])
        self.assertEqual(j.c['turn'], turn)
        self.assertIsNone(self.data(j)['desk']['ev'])
        j.act('hs_coffee')
        self.ok(j)

    def test_desk_options_are_shown_in_a_shuffled_order(self):
        j = self.desk_day()
        spots = set()
        for x in H.DESK:
            self.data(j)['desk']['ev'] = dict(id='desk-99', script=x['id'], day=j.c['day'], at='between')
            shown = self.pub(j)['data']['desk']['ev']['options']
            self.assertEqual(sorted(o['id'] for o in shown), sorted(o['id'] for o in x['options']), x['id'])
            self.assertEqual([o['id'] for o in shown], [o['id'] for o in self.pub(j)['data']['desk']['ev']['options']], x['id'])
            good = [o['id'] for o in x['options'] if o.get('good')]
            if good:
                spots.add([o['id'] for o in shown].index(good[0]))
        self.assertGreater(len(spots), 1, 'the careful answer always sits in the same place')
        self.data(j)['desk']['ev'] = None

    def test_every_desk_option_applies_cleanly(self):
        j = self.desk_day()
        base = j.state
        self.assertGreaterEqual(len(H.DESK), 8)
        for x in H.DESK:
            self.assertGreaterEqual(len(x['options']), 2, x['id'])
            self.assertIn(x['default'], [o['id'] for o in x['options']])
            self.assertNotEqual(next(o for o in x['options'] if o['id'] == x['default']).get('good'), True, x['id'])
            self.assertTrue(any(o.get('good') or (o.get('luck') and o['luck']['win'].get('good')) for o in x['options']), x['id'])
            for o in x['options']:
                j.state = copy.deepcopy(base)
                self.data(j)['desk']['ev'] = dict(id='desk-99', script=x['id'], day=j.c['day'], at='between')
                validate_state(j.state)
                r = j.act('hs_desk', option=o['id'])
                self.assertTrue(r['message'], (x['id'], o['id']))
                self.ok(j)
        j.state = base

    def test_inspection_reads_the_safety_log(self):
        j = self.desk_day()
        base = copy.deepcopy(j.state)
        ev = lambda: dict(id='desk-99', script='inspect', day=j.c['day'], at='between')
        self.data(j)['desk']['ev'] = ev()
        money = j.c['money']
        r = j.act('hs_desk', option='log')
        self.assertIn('phạt 15', r['message'])
        self.assertEqual(j.c['money'], money - 15)
        j.state = copy.deepcopy(base)
        j.act('hs_safety')
        self.data(j)['desk']['ev'] = ev()
        xp, money = j.c['xp'], j.c['money']
        r = j.act('hs_desk', option='log')
        self.assertIn('đạt', r['message'])
        self.assertEqual((j.c['xp'] - xp, j.c['money']), (10, money))
        j.state = copy.deepcopy(base)
        self.data(j)['desk']['ev'] = ev()
        patience = j.task['patience']
        r = j.act('hs_desk', option='rush')
        self.assertIn('đạt', r['message'])
        self.assertEqual(self.data(j)['safety_day'], j.c['day'])
        self.assertEqual(j.task['patience'], max(25, patience - 12))

    def test_desk_choices_leave_marks_that_bring_follow_ups(self):
        j = self.desk_day()
        j.c['day'] = 3
        pool = lambda mod='steady': [x['id'] for x in kit._desk_pool('homestay', j.c, self.data(j)['desk'], H.DESK, 'between', mod)]
        self.assertNotIn('copycat', pool())
        self.assertNotIn('otacall', pool())
        self.assertNotIn('bus', pool())
        self.assertIn('bus', pool('festival'))
        self.assertNotIn('fog', pool())
        self.assertIn('fog', pool('rain'))
        self.data(j)['desk']['ev'] = dict(id='desk-98', script='blackmail', day=j.c['day'], at='between')
        j.act('hs_desk', option='pay')
        self.assertIn('copycat', pool())
        self.assertNotIn('blackmail', pool())
        self.data(j)['desk']['ev'] = dict(id='desk-99', script='copycat', day=j.c['day'], at='between')
        j.act('hs_desk', option='policy')
        self.assertNotIn('copycat', pool())

    def test_festival_day_plans_an_extra_surprise(self):
        fest = next(d for d in range(2, 30) if H.today(d)['id'] == 'festival')
        j = Journey('homestay')
        while j.c['day'] < fest:
            j.act('end_day')
            j.act('start_day')
        self.assertEqual(self.data(j)['desk']['plan'], kit.desk_plan('homestay', fest, True))
        self.assertIn(5, self.data(j)['desk']['plan'])
        self.ok(j)

    # ------------------------------------------------------------ saves, close, text
    def test_old_save_keeps_old_tickets_and_gains_new_fields(self):
        j = self.at(1, 0, ask=False)
        s = copy.deepcopy(j.state)
        c = s['careers']['homestay']
        old = H._make_v1(1, 0, 5)
        c['tasks'] = [old]
        c['active_task'] = old['id']
        d = c['ext']['data']
        for k in list(H.DATA_V2) + ['desk']:
            d.pop(k)
        validate_state(s)
        t = c['tasks'][0]
        self.assertGreaterEqual(t['created_turn'], kit.LEGACY_TURN)
        self.assertNotIn('gen', t)
        self.assertEqual(H.make_task(1, 0, t['created_turn']), H._make_v1(1, 0, t['created_turn']))
        self.assertIn('desk', d)
        self.assertEqual(d['ota'], [])
        validate_state(json.loads(json.dumps(s)))
        j.state = s
        j.act('ask', task=old['id'])
        self.assertIn('desk', self.pub(j)['data'])

    def test_tampered_new_fields_are_rejected(self):
        j = self.booking('tight', 'low')
        bad = [lambda s: s['careers']['homestay']['tasks'][0].update(rate='free'),
               lambda s: s['careers']['homestay']['tasks'][0].update(haggles=-1),
               lambda s: s['careers']['homestay']['ext']['data'].update(strikes='x'),
               lambda s: s['careers']['homestay']['ext']['data']['ota'].append(dict(id='o', status='new'))]
        for fn in bad:
            s = copy.deepcopy(j.state)
            fn(s)
            with self.assertRaises(GameError):
                validate_state(s)
        j = self.claim('owner')
        s = copy.deepcopy(j.state)
        s['careers']['homestay']['tasks'][0]['choice'] = 'sell'
        with self.assertRaises(GameError):
            validate_state(s)

    def test_close_summary_lists_the_day(self):
        j = Journey('homestay')
        j.act('end_day')
        lines = j.c['shift_summary']['career']['lines']
        self.assertIn('Hôm nay xong 0 việc.', lines)
        self.assertTrue(any(x.startswith('Dự báo ngày mai') for x in lines))
        self.assertEqual(self.data(j)['day_synced'], 0)

    def test_public_data_shows_the_day(self):
        j = self.desk_day()
        d = self.pub(j)['data']
        self.assertEqual(d['mod']['id'], H.today(j.c['day'])['id'])
        self.assertEqual(d['tomorrow']['id'], H.today(j.c['day'] + 1)['id'])
        self.assertEqual(d['tier'], kit.tier(j.c['day']))
        self.assertEqual(d['score'], 4.6)
        for k in ('ev', 'last', 'marks'):
            self.assertIn(k, d['desk'])
        self.assertIsInstance(d['ota'], list)
        self.assertEqual(H.content()['walk_fee'], H.WALK_FEE)

    def test_text_never_assumes_the_hosts_gender(self):
        texts = json.dumps([H.CHECKINS2, H.CHECKOUTS2, H.BREAKFASTS2, H.BOOKINGS2, H.RECOMMENDS2, H.CLAIMS, H.DESK, H.TODAY, H.HOUSE_RULES,
                            H.SPEC['situations'], H.RATES, H.PUSHBACK], ensure_ascii=False, default=str)
        for bad in ('Chị chủ', 'chị chủ', 'anh chủ', 'Anh chủ', 'cô chủ', 'nha anh', 'không anh?', 'thôi anh', 'Anh ơi', 'con bé', 'các anh'):
            self.assertNotIn(bad, texts)
        self.assertFalse(re.search(r'trong game|của game|người chơi|NPC|mô phỏng|giả lập', texts))
        for d in range(1, 15):
            for sl in range(6):
                t = H.make_task(d, sl, 1)
                self.assertFalse(re.search(r'\b(anh|chị) ơi\b', t['opening'] + t['needs'].get('note', '')), t['opening'])


class HomestayConsequenceTests(unittest.TestCase):
    """Doing the job wrong costs you, in proportion: slips at the hand-off, the guest's reaction, the review, reports."""

    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def at(self, pred):
        j = Journey('homestay', slot=pick(pred)[1], day=pick(pred)[0])
        if j.c['money'] < 500:
            kit.money(j.state, j.c, 500 - j.c['money'], 'Vốn đầu mùa', None, 'event_income')
        for item in ('egg', 'bread', 'milk', 'coffee', 'heater_gas'):
            if kit.stock(j.c, item) < 10:
                kit.add_lot(j.c, item, 10, 0, 5, 'test')
        j.act('ask', task=j.task['id'])
        return j

    def review(self, j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def earned(self, j, tid, n0):
        """What the job itself paid (tips and unrelated events left out)."""
        return sum(int(e['text'].split(' xu')[0]) for e in j.c['journal'][n0:]
                   if e['kind'] == 'money' and e.get('ref') == tid and 'Tip' not in e['text'])

    EXACT = staticmethod(lambda t: t['job'] == 'checkin' and not t['_x'].get('case') and t['needs']['size'] == 2
                         and t['_x']['adults'] == t['needs']['adults'] and t['_x']['kids'] == t['needs']['kids'] and t['npc'] != 'homestay_npc_03')

    def checkin(self, j, room='thong', q=5, dirty=False, heater=True):
        d = j.c['ext']['data']
        d['bookings'] = []
        for rid in ('thong', 'suong', 'gac', 'quy'):
            d['rooms'][rid].update(status='clean', q=q, guest=None, task=None, until=0, hk=None)
        if dirty:
            d['rooms'][room].update(status='dirty')
        tid = j.task['id']
        j.act('hs_verify', task=tid, entry=j.task['_x']['match'])
        j.act('hs_ids', task=tid, mode='look')
        j.act('hs_count', task=tid)
        j.act('hs_assign', task=tid, rooms=[room])
        if j.task['needs']['cold'] and heater:
            j.act('hs_heater', task=tid)
        n0 = len(j.c['journal'])
        r = j.act('hs_welcome', task=tid, confirm=True)
        t = j.get(tid)
        return t, r, self.earned(j, tid, n0), t['needs']['rate'] * t['needs']['nights'] - t['needs']['paid']

    def test_right_checkin_pays_in_full_and_earns_five_stars(self):
        j = self.at(self.EXACT)
        t, r, paid, due = self.checkin(j)
        self.assertEqual((t['status'], t.get('slips') or [], t['reaction']['kind'], paid, t['ci']['paid']), ('completed', [], 'accept', due, due))
        post = self.review(j, t['id'])
        self.assertGreaterEqual(post['stars'] if not post['feedback'].get('unfair') else post['feedback']['fair'], 4)
        self.assertTrue(r.get('celebrate'))

    def test_dirty_room_is_allowed_but_costs_money_stars_and_a_report(self):
        j = self.at(self.EXACT)
        feed = {p['id'] for p in j.c['feed']}
        t, r, paid, due = self.checkin(j, dirty=True)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual([x['code'] for x in t['slips']], ['dirty_room'])
        self.assertIn(t['reaction']['kind'], ('discount', 'refund', 'walkout'))
        self.assertEqual(paid, due - t['reaction']['cut'])
        self.assertLess(paid, due)
        post = self.review(j, t['id'])
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('chưa dọn', post['text'])
        self.assertIn('chưa dọn', r['message'])
        self.assertEqual(j.c['ext']['data']['rooms']['thong']['status'], 'occupied')
        self.assertTrue(any(p.get('report') for p in j.c['feed'] if p['id'] not in feed))
        validate_state(json.loads(json.dumps(j.state)))

    def test_severity_scales_the_stars(self):
        stars = {}
        for label, kw in (('damp', dict(q=3)), ('sloppy', dict(q=2)), ('dirty', dict(dirty=True))):
            j = self.at(self.EXACT)
            t, _, _, _ = self.checkin(j, **kw)
            stars[label] = self.review(j, t['id'])['stars']
        self.assertGreater(stars['damp'], stars['dirty'])
        self.assertGreaterEqual(stars['damp'], stars['sloppy'])
        self.assertGreaterEqual(stars['sloppy'], stars['dirty'])
        self.assertLessEqual(stars['dirty'], 2)

    def test_booked_room_type_and_heater_are_remembered(self):
        j = self.at(lambda t: t['job'] == 'checkin' and not t['_x'].get('case') and t['needs']['size'] == 4 and t['needs']['cold']
                    and t['_x']['adults'] == t['needs']['adults'] and t['_x']['kids'] == t['needs']['kids'])
        t, r, paid, due = self.checkin(j, room='gac', heater=False)
        self.assertEqual({x['code'] for x in t['slips']}, {'small_room', 'no_heater'})
        self.assertLessEqual(self.review(j, t['id'])['stars'], 2)
        self.assertLess(paid, due)

    def test_known_allergy_ignored_is_a_safety_failure(self):
        j = self.at(lambda t: t['job'] == 'breakfast' and t['needs']['allergy'] == 'egg')
        tid = j.task['id']
        feed = {p['id'] for p in j.c['feed']}
        follow = len(j.c['incidents']['follow'])
        for _ in range(sum(j.task['needs']['eggs'].values()) + 1):     # one egg too many
            j.act('hs_egg', task=tid)
            self.clock.t += 8
            j.act('hs_plate', task=tid)
        for key, action in (('bread', 'hs_bread'), ('milk', 'hs_milk'), ('coffee', 'hs_coffee')):
            for _ in range(j.task['needs'][key]):
                j.act(action, task=tid)
        n0 = len(j.c['journal'])
        r = j.act('hs_serve', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual((t['status'], t['reaction']['kind'], self.earned(j, tid, n0)), ('completed', 'refuse', 0))
        self.assertTrue(t['slips'][0]['safety'])
        self.assertIn('dị ứng', r['message'])
        post = self.review(j, tid)
        self.assertEqual(post['stars'], 1)
        self.assertIn('dị ứng trứng', post['text'])
        self.assertTrue(any(p.get('report') for p in j.c['feed'] if p['id'] not in feed))
        self.assertGreater(len(j.c['incidents']['follow']), follow)
        validate_state(json.loads(json.dumps(j.state)))

    def test_wrong_eggs_are_sent_back_then_a_small_slip_remains(self):
        j = self.at(lambda t: t['job'] == 'breakfast' and not t['_x'].get('case') and not t['needs']['allergy']
                    and t['needs']['eggs']['runny'] >= 2 and not t['needs']['eggs']['well'])
        tid = j.task['id']
        want = j.task['needs']['eggs']

        def cook(style_secs):
            for _ in range(want['runny']):
                j.act('hs_egg', task=tid)
                self.clock.t += style_secs
                j.act('hs_plate', task=tid)
            for key, action in (('bread', 'hs_bread'), ('milk', 'hs_milk'), ('coffee', 'hs_coffee')):
                for _ in range(j.task['needs'][key] - j.task['tray'][key]):
                    j.act(action, task=tid)
        cook(14)                                            # well done instead of runny
        waste = len(j.c['life']['waste'])
        r = j.act('hs_serve', task=tid, confirm=True)
        t = j.get(tid)
        if t['status'] != 'completed':                      # this guest sends it back
            self.assertEqual(t['reaction']['kind'], 'remake')
            self.assertTrue(r.get('refused'))
            self.assertEqual((t['tray']['eggs'], len(j.c['life']['waste'])), ([], waste + 1))
            cook(8)
            j.act('hs_serve', task=tid, confirm=True)
            t = j.get(tid)
            self.assertEqual([(x['code'], x['sev']) for x in t['slips']], [('returned', 1)])
        else:
            self.assertEqual(t['slips'][0]['code'], 'doneness')
        post = self.review(j, tid)
        self.assertLessEqual(post['stars'], 4)
        self.assertIn('lòng đào', post['text'])

    def test_overcharge_caught_at_the_counter_is_remembered_but_undercharge_is_only_the_house_loss(self):
        pred = lambda t: t['job'] == 'checkout' and not t['_x'].get('case') and t['_x']['water'] > H.FREE_WATER and not t['_x']['lost']
        j = self.at(pred)
        tid = j.task['id']
        j.act('hs_inspect', task=tid)
        truth = H._truth_bill(j.task)
        for _ in range(truth['water'] + 1):
            j.act('hs_line', task=tid, line='water', delta=1)
        self.assertTrue(j.act('hs_settle', task=tid, confirm=True).get('refused'))
        j.act('hs_line', task=tid, line='water', delta=-1)
        for k, q in truth.items():
            for _ in range(q - j.task['bill'][k]):
                j.act('hs_line', task=tid, line=k, delta=1)
        n0 = len(j.c['journal'])
        j.act('hs_settle', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual([x['code'] for x in t['slips']], ['overcharge'])
        self.assertEqual(self.earned(j, tid, n0), H._bill_total(truth) - t['reaction']['cut'])
        self.assertIn('tính dư', self.review(j, tid)['text'])
        # Charging too little: no complaint, the house simply earns less.
        j2 = self.at(pred)
        tid2 = j2.task['id']
        j2.act('hs_inspect', task=tid2)
        j2.act('hs_settle', task=tid2, confirm=True)
        t2 = j2.get(tid2)
        self.assertEqual((t2.get('slips') or [], t2['reaction']['kind']), ([], 'accept'))
        self.assertGreaterEqual(t2['mistakes'], 1)

    def test_no_double_charge_on_replay(self):
        j = self.at(self.EXACT)
        t, _, paid, due = self.checkin(j, q=2)
        money = j.c['money']
        again = cq.react(j.state, j.c, j.get(t['id']), due)
        self.assertEqual((j.c['money'], again['pay'], again['kind']), (money, paid, t['reaction']['kind']))
        with self.assertRaises(GameError):
            j.act('hs_welcome', task=t['id'], confirm=True)
        self.assertEqual(j.c['money'], money)

    def test_booking_upstairs_for_elders_and_saying_full_while_free(self):
        pred = lambda t: (t['job'] == 'booking' and not t['_x'].get('case') and not t['needs']['stairs_ok'] and t['needs']['start'] > t['day']
                          and counted(t['needs']['adults'], t['needs']['kids']) <= 3)
        j = self.at(pred)
        j.c['ext']['data']['bookings'] = []
        tid = j.task['id']
        j.act('hs_hold', task=tid, rooms=['gac'], rate='std')
        dep = j.task['quote']['deposit']
        total = j.task['quote']['total']
        r = j.act('hs_book', task=tid, confirm=True)
        if r.get('refused'):
            j.act('hs_rate', task=tid, rate='low')
            dep, total = j.task['quote']['deposit'], j.task['quote']['total']
            j.act('hs_book', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['slips'][0]['code'], 'stairs')
        self.assertLessEqual(self.review(j, tid)['stars'], 3)
        b = next(b for b in j.c['ext']['data']['bookings'] if b['task'] == tid)
        cut = t['reaction']['cut']
        self.assertEqual((b['deposit'], b['total']), (dep - cut, total - cut))     # the balance due on arrival is unchanged
        j2 = self.at(lambda t: t['job'] == 'booking' and not t['_x'].get('case') and t['needs']['start'] > t['day'])
        j2.c['ext']['data']['bookings'] = []
        tid2 = j2.task['id']
        r2 = j2.act('hs_decline', task=tid2, confirm=True)
        t2 = j2.get(tid2)
        self.assertEqual((t2['status'], t2['slips'][0]['code']), ('referred', 'said_full'))
        self.assertIn('còn phòng', r2['message'])
        self.assertLessEqual(self.review(j2, tid2)['stars'], 3)
        validate_state(json.loads(json.dumps(j2.state)))

    def test_unsuitable_place_and_imposter_claim(self):
        j = self.at(lambda t: t['job'] == 'recommend' and not t['_x'].get('case') and any(p['avoid'] for p in t['_x']['probes'].values()))
        tid = j.task['id']
        probes = j.task['_x']['probes']
        for q in probes:
            j.act('hs_probe', task=tid, q=q)
        avoid = {a for p in probes.values() for a in p['avoid']} | set(j.task['needs']['avoid'])
        bad = next(p['id'] for p in H.PLACES if avoid & set(p['tags']))
        good = [p['id'] for p in H.PLACES if not avoid & set(p['tags'])][:2]
        for pid in [bad] + good:
            j.act('hs_pick', task=tid, place=pid)
        n0 = len(j.c['journal'])
        j.act('hs_advise', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual((t['slips'][0]['code'], t['slips'][0]['sev']), ('unsuitable', 2))
        self.assertIn(H.PLACE_INDEX[bad]['name'], self.review(j, tid)['text'])
        self.assertLessEqual(self.review(j, tid)['stars'], 3)
        self.assertEqual(self.earned(j, tid, n0), H.SPEC['prices']['guide'] - t['reaction']['cut'])
        j2 = self.at(lambda t: t['job'] == 'claim' and t['_x']['kind'] == 'imposter')
        tid2 = j2.task['id']
        feed = {p['id'] for p in j2.c['feed']}
        money = j2.c['money']
        j2.act('hs_claim', task=tid2, choice='give', confirm=True)
        t2 = j2.get(tid2)
        self.assertEqual((t2['slips'][0]['code'], self.review(j2, tid2)['stars']), ('wrong_person', 1))
        self.assertTrue(any(p.get('report') for p in j2.c['feed'] if p['id'] not in feed))
        self.assertLessEqual(j2.c['money'], money + H.SPEC['tip'])     # nothing to pay back on a free call
        validate_state(json.loads(json.dumps(j2.state)))


if __name__ == '__main__':
    unittest.main()
