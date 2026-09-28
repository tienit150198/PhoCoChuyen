import copy
import json
import unittest

import game.careers.kit as kit
from game.engine import GameError, public_state, validate_state
from game.careers import delivery as D
from tests.helpers import Journey


def slot_of(key, day):
    for slot in range(12):                       # the engine allows 12 orders per day
        if D.make_task(day, slot, 1)['needs']['order'] == key:
            return slot
    return None


def journey(*keys, rain=None):
    """One Journey holding exactly the given orders (all accepted)."""
    for day in range(max(D.ORDER_INDEX[k]['min_day'] for k in keys), 60):
        if rain is not None and (D.weather(day) == 'rain') != rain:
            continue
        slots = [slot_of(k, day) for k in keys]
        if None not in slots and len(set(slots)) == len(slots):
            break
    else:
        raise AssertionError(keys)
    j = Journey('delivery', slot=slots[0], day=day)
    for s in slots[1:]:
        j.c['tasks'].append(D.make_task(day, s, 1))
    validate_state(j.state)
    ids = [t['id'] for t in j.c['tasks']]
    for tid in ids:
        j.act('ask', task=tid)
    return (j, *ids)


def data(j):
    return j.c['ext']['data']


def wait_until(j, minute):
    while data(j)['clock'] < minute:
        j.act('dl_wait')


def ride(j, *route):
    j.act('dl_plan', route=list(route))
    for _ in route:
        j.act('dl_ride')


def review(j, tid):
    return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['feedback']['task'] == tid)


def crit(post):
    return {x['key']: x['score'] for x in post['feedback']['criteria']}


class DeliveryTests(unittest.TestCase):
    def test_happy_shift_three_orders_and_settlement(self):
        j = Journey('delivery')
        P2, F1, P1 = [t['id'] for t in j.c['tasks']]
        self.assertEqual([j.get(x)['needs']['order'] for x in (P2, F1, P1)], ['P2', 'F1', 'P1'])
        for tid in (P2, F1, P1):
            j.act('ask', task=tid)
        j.act('dl_check', task=P2)
        j.act('dl_check', task=P1)
        stock = kit.stock(j.c, 'bubble')
        j.act('dl_pack', task=P1, item='bubble')
        self.assertEqual(kit.stock(j.c, 'bubble'), stock - 1)
        j.act('dl_load', task=P1)
        j.act('dl_load', task=P2)
        turn = j.c['turn']
        j.act('dl_plan', route=['com', 'office', 'villa', 'apt', 'hub'])
        self.assertEqual(j.c['turn'], turn)                      # planning is free
        j.act('dl_ride')
        j.act('dl_check', task=F1)
        self.assertEqual(j.get(F1)['run']['missing'], '2 bịch canh rong biển')
        j.act('dl_load', task=F1)
        j.act('dl_ride')
        earned = j.c['earnings']
        j.act('dl_deliver', task=F1)
        self.assertEqual(j.c['earnings'] - earned, 8 + 2 * 10 + D.SPEC['tip'])
        j.act('dl_ride')
        j.act('dl_deliver', task=P1)
        j.act('dl_ride')
        j.act('dl_call', task=P2)
        self.assertEqual(j.get(P2)['run']['unit'], 'Phòng 504 — lầu 5')
        j.act('dl_deliver', task=P2, change=63)
        d = data(j)
        self.assertEqual((d['owed'], d['bag']), (137, 137))
        j.act('dl_ride')
        with self.assertRaises(GameError):
            j.act('dl_settle', amount=130, confirm=True)
        money = j.c['money']
        j.act('dl_settle', amount=137, confirm=True)
        self.assertEqual(j.c['money'], money)
        d = data(j)
        self.assertEqual((d['owed'], d['bag'], d['cod']), (0, 0, []))
        for tid in (P2, F1, P1):
            post = review(j, tid)
            self.assertEqual(post['feedback']['fair'], 5, crit(post))
            self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(d['delivered'], 3)
        validate_state(json.loads(json.dumps(j.state)))
        summary = j.act('end_day')['summary']['career']
        self.assertEqual((summary['delivered'], summary['km']), (3, 26))

    def test_hidden_until_accepted(self):
        j = Journey('delivery')
        view = public_state(j.state)['careers']['delivery']['tasks'][0]
        self.assertIsNone(view['needs'])
        self.assertEqual(set(view['preview']), {'pickup', 'dest', 'kind', 'emoji'})
        dump = json.dumps(view, ensure_ascii=False)
        for secret in ('_w', '_seam', '_unit', '_away', '_missing', '_broken', '_value'):
            self.assertNotIn(secret, dump)
        with self.assertRaises(GameError):
            j.act('dl_check', task=view['id'])
        j.act('ask', task=view['id'])
        view = public_state(j.state)['careers']['delivery']['tasks'][0]
        self.assertIsNotNone(view['needs'])
        self.assertNotIn('_away', json.dumps(view))
        self.assertIsNone(view['run']['unit'])

    def test_actions_need_the_right_place(self):
        j, p1 = journey('P1')
        with self.assertRaises(GameError):
            j.act('dl_deliver', task=p1)                 # at the hub, not the villa
        j.act('dl_check', task=p1)
        with self.assertRaises(GameError):
            j.act('dl_check', task=p1)                   # already weighed
        ride(j, 'market')
        with self.assertRaises(GameError):
            j.act('dl_load', task=p1)                    # the parcel is at the hub
        with self.assertRaises(GameError):
            j.act('dl_pack', task=p1, item='bubble')

    def test_parcel_must_be_weighed_and_food_must_be_ready(self):
        j, p3 = journey('P3')
        with self.assertRaises(GameError):
            j.act('dl_load', task=p3)
        j, f1 = journey('F1', rain=False)
        ride(j, 'com')                                   # 9 minutes, ready after 8
        j.act('dl_check', task=f1)
        j, f3 = journey('F3', rain=False)
        ride(j, 'bun')                                   # 12 minutes, prep 15
        with self.assertRaises(GameError) as ctx:
            j.act('dl_load', task=f3)
        self.assertEqual(ctx.exception.code, 'not_ready')
        with self.assertRaises(GameError):
            j.act('dl_pack', task=f3, item='bubble')     # food rides in the thermal box
        j.act('dl_wait')
        j.act('dl_load', task=f3)                        # loaded without checking the bill
        ride(j, 'vet')
        r = j.act('dl_deliver', task=f3, change=26)
        self.assertIn('thiếu bịch rau sống', r['message'])
        t = j.get(f3)
        self.assertEqual(t['mistakes'], 1)
        self.assertLess(crit(review(j, f3))['condition'], 5)

    def test_weight_mismatch_report_and_refusal(self):
        j, p3 = journey('P3')
        r = j.act('dl_check', task=p3)
        self.assertIn('8 kg', r['message'])
        j.act('dl_load', task=p3, report=True)
        self.assertTrue(j.get(p3)['run']['reported'])
        ride(j, 'alley')
        before = j.c['earnings']
        j.act('dl_deliver', task=p3, change=5)
        self.assertEqual(j.c['earnings'] - before, 10 + 2 * 2 + 3 + D.SPEC['tip'])
        self.assertEqual(crit(review(j, p3))['accuracy'], 5)
        # Not reporting is a mistake.
        j, p3 = journey('P3')
        j.act('dl_check', task=p3)
        j.act('dl_load', task=p3)
        self.assertEqual(j.get(p3)['mistakes'], 1)
        # 26 kg of fertiliser does not go on a motorbike.
        j, p6 = journey('P6')
        with self.assertRaises(GameError):
            j.act('dl_refuse', task=p6, confirm=True)    # weigh first
        j.act('dl_check', task=p6)
        with self.assertRaises(GameError):
            j.act('dl_load', task=p6)
        j.act('dl_refuse', task=p6, confirm=True)
        t = j.get(p6)
        self.assertEqual((t['status'], t['run']['outcome']), ('referred', 'refused'))
        self.assertGreaterEqual(review(j, p6)['feedback']['fair'], 4)
        # A normal parcel cannot be refused.
        j, p1 = journey('P1')
        j.act('dl_check', task=p1)
        with self.assertRaises(GameError):
            j.act('dl_refuse', task=p1, confirm=True)

    def test_bulky_needs_strap_which_unlocks_at_level_two(self):
        j, p11 = journey('P11')
        j.act('dl_check', task=p11)
        with self.assertRaises(GameError):
            j.act('dl_pack', task=p11, item='strap')     # level 1
        with self.assertRaises(GameError):
            j.act('dl_load', task=p11)
        j.act('dl_refuse', task=p11, confirm=True)       # honest: no strap, no ride
        j, p11 = journey('P11')
        j.c['xp'] = 100
        j.act('dl_check', task=p11)
        j.act('dl_pack', task=p11, item='strap')
        j.act('dl_pack', task=p11, item='rainbag')       # day 3 is a rainy day
        j.act('dl_load', task=p11)
        with self.assertRaises(GameError):
            j.act('dl_refuse', task=p11, confirm=True)

    def test_unpadded_fragile_breaks_and_courier_pays_half(self):
        j, p1 = journey('P1')
        j.act('dl_check', task=p1)
        j.act('dl_load', task=p1)
        ride(j, 'villa')
        self.assertNotIn('_broken', json.dumps(public_state(j.state)['careers']['delivery']['tasks'][0]))
        r = j.act('dl_deliver', task=p1)
        self.assertIn('từ chối', r['message'])
        self.assertTrue(j.get(p1)['run']['broken_seen'])
        with self.assertRaises(GameError):
            j.act('dl_deliver', task=p1)
        with self.assertRaises(GameError):
            j.act('dl_fail', task=p1)                    # confirm required
        money = j.c['money']
        j.act('dl_fail', task=p1, confirm=True)
        t = j.get(p1)
        self.assertEqual((t['status'], t['run']['comp']), ('cancelled', 20))
        self.assertEqual(j.c['money'], money - 20)
        self.assertLessEqual(review(j, p1)['stars'], 2)

    def test_rain_soaks_unbagged_parcels_and_ruins_paper(self):
        j, p7, p8 = journey('P7', 'P8', rain=True)
        self.assertEqual(D.weather(j.c['day']), 'rain')
        j.act('dl_check', task=p7)
        j.act('dl_load', task=p7)
        ride(j, 'office')
        r = j.act('dl_call', task=p7)
        self.assertIn('Phòng kế hoạch', r['message'])
        r = j.act('dl_deliver', task=p7)
        self.assertIn('ướt', r['message'])
        # A rain bag can still be pulled over a loaded parcel on the road.
        ride(j, 'market')
        j.act('dl_check', task=p8)
        j.act('dl_pack', task=p8, item='bubble')
        j.act('dl_load', task=p8)
        j.act('dl_pack', task=p8, item='rainbag')
        with self.assertRaises(GameError):
            j.act('dl_pack', task=p8, item='tape')       # already strapped on the bike
        ride(j, 'villa')
        j.act('dl_deliver', task=p8)
        self.assertEqual(j.get(p8)['mistakes'], 0)

    def test_seam_bursts_without_tape_and_safe_drop_rules(self):
        j, p4, p13 = journey('P4', 'P13')
        j.act('dl_check', task=p4)
        self.assertTrue(j.get(p4)['run']['seam'])
        j.act('dl_load', task=p4)
        j.act('dl_check', task=p13)
        j.act('dl_load', task=p13)
        ride(j, 'villa')
        with self.assertRaises(GameError):
            j.act('dl_safedrop', task=p13, confirm=True)  # registered mail: signature only
        j.act('dl_safedrop', task=p4, confirm=True)
        t = j.get(p4)
        self.assertEqual((t['status'], t['run']['outcome']), ('completed', 'safedrop'))
        self.assertEqual(t['mistakes'], 1)                # seam burst on the road
        j.act('dl_deliver', task=p13)

    def test_unit_call_and_customer_away(self):
        j, p2 = journey('P2')
        j.act('dl_check', task=p2)
        j.act('dl_load', task=p2)
        ride(j, 'apt')                                   # 17:18, customer back 17:40
        j.act('dl_call', task=p2)
        self.assertEqual(j.get(p2)['run']['back'], 40)
        r = j.act('dl_deliver', task=p2, change=63)
        self.assertIn('không ai mở', r['message'])
        self.assertEqual(j.get(p2)['run']['knocks'], 1)
        wait_until(j, 40)
        j.act('dl_deliver', task=p2, change=63)
        self.assertEqual(crit(review(j, p2))['contact'], 4)
        # Giving up at the door without ever calling is a mistake and earns nothing.
        j, p10 = journey('P10')
        j.act('dl_check', task=p10)
        j.act('dl_pack', task=p10, item='tape')
        j.act('dl_pack', task=p10, item='rainbag')
        j.act('dl_load', task=p10)
        ride(j, 'villa')
        with self.assertRaises(GameError):
            j.act('dl_fail', task=p10, confirm=True)     # nobody has knocked yet
        j.act('dl_deliver', task=p10, change=80)
        earned = j.c['earnings']
        j.act('dl_fail', task=p10, confirm=True)
        t = j.get(p10)
        self.assertEqual((t['status'], t['mistakes'], j.c['earnings'] - earned), ('cancelled', 1, 0))
        self.assertEqual(crit(review(j, p10))['contact'], 2)

    def test_change_mistakes_and_settlement_shortage(self):
        j, p2 = journey('P2')
        j.act('dl_check', task=p2)
        j.act('dl_load', task=p2)
        ride(j, 'apt')
        j.act('dl_call', task=p2)
        wait_until(j, 40)
        with self.assertRaises(GameError):
            j.act('dl_deliver', task=p2)                 # COD needs a change count
        r = j.act('dl_deliver', task=p2, change=73)      # 10 too many
        self.assertIn('thối dư 10', r['message'])
        d = data(j)
        self.assertEqual((d['owed'], d['bag']), (137, 127))
        self.assertEqual(crit(review(j, p2))['cash'], 4)
        with self.assertRaises(GameError):
            j.act('dl_settle', amount=137, confirm=True)  # not at the hub
        ride(j, 'hub')
        money = j.c['money']
        j.act('dl_settle', amount=137, confirm=True)
        self.assertEqual(j.c['money'], money - 10)
        # Short change: the customer notices and the courier hands over the rest.
        j, f4 = journey('F4')
        ride(j, 'com')
        wait_until(j, 10)
        j.act('dl_check', task=f4)
        j.act('dl_load', task=f4)
        ride(j, 'alley')
        r = j.act('dl_deliver', task=f4, change=0)
        self.assertIn('Thối thiếu 2', r['message'])
        self.assertEqual(j.get(f4)['run']['change'], 2)
        self.assertEqual(data(j)['bag'], 18)

    def test_cod_cap_forces_handing_in_cash(self):
        j, p2, p10 = journey('P2', 'P10')
        d = data(j)
        d['owed'] = d['bag'] = 200
        d['cod'] = [dict(task='x', item='Đơn trước', cod=200, day=j.c['day'])]
        validate_state(j.state)
        j.act('dl_check', task=p2)
        j.act('dl_load', task=p2)
        ride(j, 'apt')
        j.act('dl_call', task=p2)
        wait_until(j, 45)
        with self.assertRaises(GameError):
            j.act('dl_deliver', task=p2, change=63)
        ride(j, 'hub')
        j.act('dl_settle', amount=200, confirm=True)
        ride(j, 'apt')
        j.act('dl_deliver', task=p2, change=63)
        self.assertEqual(data(j)['owed'], 137)

    def test_food_expires_when_far_too_late(self):
        j, f1 = journey('F1', rain=False)
        ride(j, 'com')
        j.act('dl_load', task=f1)
        data(j)['clock'] = 200
        ride(j, 'office')
        r = j.act('dl_deliver', task=f1)
        self.assertIn('hủy', r['message'])
        with self.assertRaises(GameError):
            j.act('dl_deliver', task=f1)
        waste = len(j.c['life']['waste'])
        j.act('dl_fail', task=f1, confirm=True)
        self.assertEqual(j.get(f1)['status'], 'cancelled')
        self.assertEqual(j.c['life']['waste'][-1]['item'], 'food')
        self.assertEqual(len(j.c['life']['waste']), waste + 1)
        self.assertEqual(review(j, f1)['stars'], 1)

    def test_late_food_loses_fee_but_is_delivered(self):
        j, f1 = journey('F1', rain=False)
        ride(j, 'com')
        j.act('dl_check', task=f1)
        j.act('dl_load', task=f1)
        data(j)['clock'] = 40                           # due 55; the ride takes 30 minutes
        ride(j, 'office')
        earned = j.c['earnings']
        j.act('dl_deliver', task=f1)
        t = j.get(f1)
        self.assertEqual(t['run']['late'], 15)
        # The flat late deduction, or the customer's own cut when they complain (never both).
        cut = t['reaction']['cut']
        self.assertEqual(j.c['earnings'] - earned, (8 + 20 - cut if cut else 8 + 20 - D.LATE_FEE) + D.SPEC['tip'])
        self.assertEqual(t['slips'][0]['code'], 'late')
        self.assertEqual(crit(review(j, f1))['time'], 3)

    def test_fuel_and_refuel(self):
        j, p1 = journey('P1', rain=False)
        data(j)['fuel'] = 5
        j.act('dl_plan', route=['villa'])
        with self.assertRaises(GameError) as ctx:
            j.act('dl_ride')
        self.assertEqual(ctx.exception.code, 'fuel')
        with self.assertRaises(GameError):
            j.act('dl_refuel', amount=30, confirm=True)   # bottles: 20% max
        with self.assertRaises(GameError):
            j.act('dl_refuel', amount=7, confirm=True)
        money = j.c['money']
        j.act('dl_refuel', amount=10, confirm=True)
        self.assertEqual((data(j)['fuel'], j.c['money']), (15, money - 4))
        j.act('dl_plan', route=['gas'])
        j.act('dl_ride')
        money = j.c['money']
        j.act('dl_refuel', amount=40, confirm=True)
        self.assertEqual(j.c['money'], money - 8)
        with self.assertRaises(GameError):
            j.act('dl_refuel', amount=60, confirm=True)   # tank is not that big

    def test_load_limit(self):
        j, p3, p11, p1 = journey('P3', 'P11', 'P1')
        j.c['xp'] = 100
        j.act('dl_check', task=p11)
        j.act('dl_pack', task=p11, item='strap')
        j.act('dl_load', task=p11)
        j.act('dl_check', task=p3)
        j.act('dl_load', task=p3, report=True)
        self.assertEqual(public_state(j.state)['careers']['delivery']['data']['load'], 200)
        j.act('dl_check', task=p1)
        with self.assertRaises(GameError):
            j.act('dl_load', task=p1)                    # 12 + 8 + 3 kg > 20 kg

    def test_plan_validation(self):
        j = Journey('delivery')
        for bad in ([], ['hub'], ['com', 'com'], ['moon'], 'com', ['com'] * 11):
            with self.assertRaises(GameError):
                j.act('dl_plan', route=bad)
        j.act('dl_plan', route=['com', 'hub'])
        self.assertEqual([r['node'] for r in public_state(j.state)['careers']['delivery']['data']['eta']], ['com', 'hub'])
        with self.assertRaises(GameError):
            Journey('delivery').act('dl_ride')           # no route yet

    def test_tampering_rejected(self):
        j, p3 = journey('P3')
        j.act('dl_check', task=p3)
        for mutate in (lambda t, d: t.__setitem__('_w', 50), lambda t, d: t['needs'].__setitem__('cod', 1),
                       lambda t, d: t['run'].__setitem__('w', 50), lambda t, d: t['run'].__setitem__('unit', 'Phòng 1'),
                       lambda t, d: t['run'].__setitem__('packed', ['gold']), lambda t, d: d.__setitem__('bag', 5),
                       lambda t, d: d.__setitem__('fuel', 120), lambda t, d: d.__setitem__('at', 'moon'),
                       lambda t, d: t['run'].__setitem__('outcome', 'delivered')):
            s = copy.deepcopy(j.state)
            c = s['careers']['delivery']
            mutate(next(t for t in c['tasks'] if t['id'] == p3), c['ext']['data'])
            with self.assertRaises(GameError):
                validate_state(s)
        validate_state(json.loads(json.dumps(j.state)))

    def test_food_windows_are_fair_from_the_hub(self):
        for day in range(1, 13):
            mpu = D.MPU[D.weather(day)]
            for slot in range(24):
                t = D.make_task(day, slot, 1)
                n = t['needs']
                if n['kind'] != 'food':
                    continue
                arrive = max(n['prep'], D.dist('hub', n['pickup']) * mpu) + 3 + 1
                done = arrive + D.dist(n['pickup'], n['dest']) * mpu + D.STAIRS.get(n['dest'], 0)
                self.assertLessEqual(done, n['window'], (day, slot, n['order']))

    def test_deterministic_and_varied(self):
        for day in range(1, 8):
            rows = [D.make_task(day, s, 1) for s in range(12)]
            self.assertEqual(rows, [D.make_task(day, s, 1) for s in range(12)])
            self.assertEqual(len({r['needs']['order'] for r in rows[:3]}), 3)

    def test_close_auto_settles_and_cancels_cold_food_then_new_day_resets(self):
        j = Journey('delivery')
        P2, F1, P1 = [t['id'] for t in j.c['tasks']]
        for tid in (P2, F1, P1):
            j.act('ask', task=tid)
        d = data(j)
        d['owed'], d['bag'] = 50, 40
        d['cod'] = [dict(task='x', item='Đơn cũ', cod=50, day=1)]
        ride(j, 'com')
        j.act('dl_load', task=F1)
        money = j.c['money']
        summary = j.act('end_day')['summary']['career']
        self.assertEqual((summary['settled_at_close'], summary['food_cancelled']), (50, 1))
        self.assertEqual(j.c['money'], money - 10)
        self.assertTrue(j.get(F1)['run']['expired'])
        j.act('start_day')
        d = data(j)
        self.assertEqual((d['clock'], d['at'], d['route'], d['owed']), (0, 'hub', [], 0))
        with self.assertRaises(GameError):
            j.act('dl_deliver', task=F1)
        j.act('dl_fail', task=F1, confirm=True)
        validate_state(json.loads(json.dumps(j.state)))

    def test_assist_roles(self):
        j, p2, p1 = journey('P2', 'P1')
        j.c['active_task'] = p2
        note = D.assist(j.state, j.c, dict(role='support'), j.get(p2))
        self.assertIn('Phòng 504', note)
        self.assertTrue(j.get(p2)['run']['called'])
        j.act('dl_check', task=p1)
        note = D.assist(j.state, j.c, dict(role='packer'), j.get(p1))
        self.assertIn('màng xốp hơi', note)
        self.assertIn('bubble', j.get(p1)['run']['packed'])
        self.assertIn('phân loại', D.assist(j.state, j.c, dict(role='sorter'), None))
        j.act('dl_load', task=p1)
        self.assertIn('Nhà vườn Sứ Trắng', D.assist(j.state, j.c, dict(role='sorter'), None))
        validate_state(j.state)

    def test_all_situations_playable(self):
        j = Journey('delivery')
        self.assertTrue(5 <= len(D.SITUATIONS) <= 8)
        for x in D.SITUATIONS:
            for opt in x['options']:
                self.assertGreaterEqual(len(opt['perspectives']), 2, (x['id'], opt['id']))
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_content_and_inventory(self):
        c = D.content()
        self.assertEqual(set(c['nodes']), set(D.NODES))
        pub = public_state(Journey('delivery').state)['careers']['delivery']
        self.assertEqual(pub['inventory']['stock']['bubble'], 6)
        self.assertIn('strap', pub['inventory']['locked'])


# ======================================================================== v0.5
def find_v2(pred, days=range(1, 80)):
    for day in days:
        for slot in range(12):
            t = D.make_task(day, slot, 1)
            if pred(t, day):
                return day, slot
    raise AssertionError('no matching task')


def v2_journey(pred, days=range(1, 80)):
    day, slot = find_v2(pred, days)
    j = Journey('delivery', slot=slot, day=day)
    data(j)['desk'].update(day=day, plan=[], fired=0)        # no random surprise unless a test asks
    tid = j.task['id']
    j.act('ask', task=tid)
    return j, tid


def live_day(j, mod=None):
    """Behave as if the shift was opened under v0.5 (road board and daily target live)."""
    d = data(j)
    d['today'] = dict(day=j.c['day'], mod=mod or D.mod_of(j.c['day'])['id'])
    goal, bonus = D._goal(j.c['day'])
    d['quest'] = dict(day=j.c['day'], goal=goal, done=0, paid=False, bonus=bonus)


def load(j, tid):
    """Pick an order up the careful way (weigh, pack what it needs, report weight)."""
    t = j.get(tid)
    n = t['needs']
    if data(j)['at'] != n['pickup']:
        ride(j, n['pickup'])
    if n['kind'] == 'food':
        wait_until(j, j.get(tid)['run']['t0'] + n['prep'])
        j.act('dl_check', task=tid)
        j.act('dl_load', task=tid)
        return
    j.act('dl_check', task=tid)
    for item in D._needs_pack(j.get(tid), j.c['day']):
        j.act('dl_pack', task=tid, item=item)
    j.act('dl_load', task=tid, report=j.get(tid)['_w'] != n['w'])


def force(j, script, task=None):
    desk = data(j)['desk']
    desk['seq'] += 1
    desk['ev'] = dict(id=f'desk-{desk["seq"]}', script=script, day=j.c['day'], at='between')
    if task:
        desk['ev']['task'] = task


class DeliveryRoadTests(unittest.TestCase):
    def test_generators_old_and_new(self):
        old = D.make_task(5, 2, kit.LEGACY_TURN + 7)
        new = D.make_task(5, 2, 7)
        self.assertNotIn('gen', old)
        for k in ('_dog', '_bomb', '_moved'):
            self.assertNotIn(k, old)
            self.assertIn(k, new)
        self.assertNotIn('soup', old['needs'])
        self.assertEqual(new['gen'], D.GEN)
        self.assertEqual(old['needs']['order'], new['needs']['order'])   # the same order on the same slot
        self.assertEqual(dict(D.make_task(5, 2, 7), created_turn=0), dict(D.make_task(5, 2, 99), created_turn=0))

    def test_day_conditions_are_fixed_and_follow_the_weather(self):
        self.assertEqual(D.mod_of(1)['id'], 'normal')
        for day in range(1, 60):
            m = D.mod_of(day)
            self.assertEqual(m, D.mod_of(day))
            self.assertEqual(D.hazards(day), D.hazards(day))
            if D.weather(day) == 'rain':
                self.assertIn(m['id'], ('rain', 'storm'))
            else:
                self.assertIn(m['id'], [x['id'] for x in D.MODS])
            h = D.hazards(day)
            self.assertEqual(bool(h['jams']), m['id'] in ('school', 'market'))
            self.assertEqual(h['works'] is not None, m['id'] == 'works')
            self.assertEqual(bool(h['flood']), m['id'] == 'storm')
            self.assertNotIn('{', D._mod_text(day))
        seen = {D.mod_of(d)['id'] for d in range(1, 60)}
        self.assertTrue({'normal', 'school', 'market', 'works', 'sale', 'rain', 'storm'} <= seen, seen)

    def test_school_jam_doubles_the_main_road_but_not_the_alley(self):
        day = next(d for d in range(2, 60) if D.mod_of(d)['id'] == 'school')
        j = Journey('delivery', slot=0, day=day)
        c = j.c
        self.assertEqual(D._leg(c, 'hub', 'school', 5)['minutes'], D.dist('hub', 'school') * D.MPU['sun'])   # not live yet
        live_day(j)
        main = D._leg(c, 'hub', 'school', 5)
        self.assertEqual(main['minutes'], 2 * D.dist('hub', 'school') * D.MPU['sun'])
        self.assertTrue(main['notes'])
        late = D._leg(c, 'hub', 'school', 45)            # the jam is over at 17:40
        self.assertEqual(late['minutes'], D.dist('hub', 'school') * D.MPU['sun'])
        short = D._leg(c, 'hub', 'school', 5, 'short')
        self.assertEqual(short['minutes'], (D.dist('hub', 'school') - 1) * D.MPU['sun'])
        self.assertEqual(short['wear'], 2 * short['blocks'])
        view = public_state(j.state)['careers']['delivery']['data']
        self.assertTrue(view['road']['live'])
        self.assertEqual(view['road']['signs'][0]['kind'], 'jam')

    def test_works_detour_and_flooded_alley(self):
        day = next(d for d in range(3, 80) if D.mod_of(d)['id'] == 'works')
        j = Journey('delivery', slot=0, day=day)
        live_day(j)
        node = D.hazards(day)['works']
        a = 'hub' if node != 'hub' else 'gas'
        main = D._leg(j.c, a, node, 0)
        self.assertEqual(main['blocks'], D.dist(a, node) + 2)
        if D.dist(a, node) >= 2:
            self.assertEqual(D._leg(j.c, a, node, 0, 'short')['blocks'], D.dist(a, node) - 1)
        day = next(d for d in range(3, 80) if D.mod_of(d)['id'] == 'storm')
        j = Journey('delivery', slot=0, day=day)
        live_day(j)
        main = D._leg(j.c, 'hub', 'alley', 0)
        short = D._leg(j.c, 'hub', 'alley', 0, 'short')
        self.assertEqual(main['minutes'], D.dist('hub', 'alley') * D.MPU['rain'] + 3)
        self.assertFalse(main['stall'])
        self.assertTrue(short['stall'])
        self.assertGreater(short['fuel'], main['fuel'])

    def test_stalling_in_a_flooded_alley_soaks_unbagged_parcels(self):
        j, tid = v2_journey(lambda t, d: D.mod_of(d)['id'] == 'storm' and t['needs']['order'] == 'P3'
                            and not (t['_dog'] or t['_bomb'] or t['_moved']))
        live_day(j)
        j.act('dl_check', task=tid)
        j.act('dl_load', task=tid, report=True)            # no rain bag on purpose
        j.act('dl_plan', route=['alley'])
        clock = data(j)['clock']
        r = j.act('dl_ride', way='short')
        self.assertIn('chết máy', r['message'])
        self.assertTrue(j.get(tid)['run']['wet'])
        self.assertGreaterEqual(data(j)['clock'] - clock, 15)
        self.assertEqual(data(j)['stats']['stalls'], 1)

    def test_shortcut_spills_broth_and_needs_a_long_leg(self):
        j, tid = v2_journey(lambda t, d: t['needs'].get('soup') and not (t['_dog'] or t['_moved']) and D.weather(d) == 'sun'
                            and D.dist(t['needs']['pickup'], t['needs']['dest']) >= 2)
        load(j, tid)
        dest = j.get(tid)['needs']['dest']
        j.act('dl_plan', route=[dest])
        with self.assertRaises(GameError):
            j.act('dl_ride', way='sideways')
        r = j.act('dl_ride', way='short')
        self.assertIn('nước lèo', r['message'])
        t = j.get(tid)
        self.assertTrue(t['run']['spilled'])
        n = t['needs']
        j.act('dl_deliver', task=tid, change=(n['cash'] - n['cod']) if n['cod'] else None) if n['cod'] else j.act('dl_deliver', task=tid)
        self.assertLess(crit(review(j, tid))['condition'], 5)
        self.assertEqual(data(j)['streak'], 0)
        # A one-block hop has no alley to cut through.
        j.act('dl_plan', route=['hub' if dest != 'hub' else 'gas'])
        if D.dist(dest, data(j)['route'][0]) < 2:
            with self.assertRaises(GameError):
                j.act('dl_ride', way='short')

    def test_worn_tyre_goes_flat_blocks_work_until_decided_then_service(self):
        j, tid = v2_journey(lambda t, d: t['needs']['order'] == 'P3' and not (t['_dog'] or t['_bomb'] or t['_moved']))
        data(j)['tyre'] = 1
        j.act('dl_plan', route=['gas'])
        r = j.act('dl_ride')
        self.assertIn('xẹp', r['message'])
        d = data(j)
        self.assertEqual(d['desk']['ev']['script'], 'DE-FLAT')
        self.assertEqual(d['stats']['flats'], 1)
        with self.assertRaises(GameError) as ctx:
            j.act('dl_wait')
        self.assertEqual(ctx.exception.code, 'surprise_open')
        j.act('dl_plan', route=['hub'])                    # planning is still free
        money, clock = j.c['money'], d['clock']
        j.act('dl_decide', option='patch')
        d = data(j)
        self.assertEqual((d['tyre'], j.c['money'], d['clock']), (60, money - 6, clock + 15))
        self.assertIs(d['desk']['last']['good'], True)
        money = j.c['money']
        with self.assertRaises(GameError):
            j.act('dl_service')                            # confirm first
        j.act('dl_service', confirm=True)
        self.assertEqual((data(j)['tyre'], j.c['money']), (100, money - D.SERVICE_COST))
        with self.assertRaises(GameError):
            j.act('dl_service', confirm=True)              # nothing to fix
        validate_state(json.loads(json.dumps(j.state)))

    def test_riding_flat_bends_the_rim_and_shakes_fragile_goods(self):
        j, tid = v2_journey(lambda t, d: t['needs']['order'] in ('P1', 'P8') and D.weather(d) == 'sun'
                            and not (t['_dog'] or t['_moved']))
        load(j, tid)                                       # bubble wrap on
        data(j)['tyre'] = 0
        j.act('dl_plan', route=['gas', 'villa'])
        j.act('dl_ride')
        self.assertEqual(data(j)['desk']['ev']['script'], 'DE-FLAT')
        j.act('dl_decide', option='ride')
        d = data(j)
        self.assertIn('rim', d['desk']['marks'])
        self.assertTrue(j.get(tid)['run']['_broken'])
        pub = public_state(j.state)['careers']['delivery']['data']['bike']
        self.assertEqual(pub['service'], D.SERVICE_COST + D.RIM_COST)
        money = j.c['money']
        j.act('dl_service', confirm=True)
        self.assertEqual(j.c['money'], money - D.SERVICE_COST - D.RIM_COST)
        self.assertNotIn('rim', data(j)['desk']['marks'])

    def test_dog_at_the_gate(self):
        j, tid = v2_journey(lambda t, d: t['_dog'] and t['needs']['kind'] == 'parcel' and not t['needs']['cod']
                            and t['needs']['size'] == 'S' and t['_w'] <= D.LOAD_LIMIT and D.weather(d) == 'sun')
        load(j, tid)
        ride(j, j.get(tid)['needs']['dest'])
        r = j.act('dl_deliver', task=tid)
        self.assertIn('chó', r['message'])
        ev = public_state(j.state)['careers']['delivery']['data']['desk']['ev']
        self.assertEqual((ev['script'], ev['task']), ('DE-DOG', tid))
        self.assertNotEqual(j.get(tid)['status'], 'completed')
        j.act('dl_decide', option='call')
        self.assertEqual(j.get(tid)['run']['dog'], 'ok')
        j.act('dl_deliver', task=tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(data(j)['stats']['dogs'], 1)

    def test_bomb_return_or_discount_from_own_pocket(self):
        pred = lambda t, d: t['_bomb'] and t['needs']['size'] == 'S' and t['_w'] <= D.LOAD_LIMIT and not t['needs']['fragile'] and D.weather(d) == 'sun'
        j, tid = v2_journey(pred)
        load(j, tid)
        ride(j, j.get(tid)['needs']['dest'])
        n = j.get(tid)['needs']
        if n['unit_missing']:
            j.act('dl_call', task=tid)
        wait_until(j, j.get(tid)['run']['t0'] + j.get(tid)['_away'])
        r = j.act('dl_deliver', task=tid, change=n['cash'] - n['cod'])
        self.assertIn('không nhận', r['message'])
        earned = j.c['earnings']
        j.act('dl_decide', option='return')
        t = j.get(tid)
        self.assertEqual((t['status'], t['run']['outcome'], t['run']['bomb']), ('cancelled', 'failed', 'return'))
        self.assertGreaterEqual(j.c['earnings'] - earned, 4)
        self.assertGreaterEqual(review(j, tid)['stars'], 3)
        self.assertEqual(data(j)['owed'], 0)
        # Same parcel, another courier: pay the discount yourself.
        j, tid = v2_journey(pred)
        load(j, tid)
        ride(j, j.get(tid)['needs']['dest'])
        n = j.get(tid)['needs']
        if n['unit_missing']:
            j.act('dl_call', task=tid)
        wait_until(j, j.get(tid)['run']['t0'] + j.get(tid)['_away'])
        j.act('dl_deliver', task=tid, change=n['cash'] - n['cod'])
        j.act('dl_decide', option='discount')
        j.act('dl_deliver', task=tid, change=n['cash'] - n['cod'])
        d = data(j)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(d['owed'] - d['bag'], D.DISCOUNT)
        ride(j, 'hub')
        money = j.c['money']
        j.act('dl_settle', amount=d['owed'], confirm=True)
        self.assertEqual(j.c['money'], money - D.DISCOUNT)
        validate_state(json.loads(json.dumps(j.state)))

    def test_moved_address_found_by_calling(self):
        j, tid = v2_journey(lambda t, d: t['_moved'] and t['needs']['kind'] == 'parcel' and not t['needs']['cod']
                            and t['needs']['size'] == 'S' and t['_w'] <= D.LOAD_LIMIT and not t['needs']['fragile'] and D.weather(d) == 'sun')
        t = j.get(tid)
        new = t['_moved']
        self.assertNotIn(new, json.dumps(public_state(j.state)['careers']['delivery']['tasks'][0]['run']))
        r = j.act('dl_call', task=tid)
        self.assertIn(D.NODES[new]['name'], r['message'])
        ev = public_state(j.state)['careers']['delivery']['data']['desk']['ev']
        self.assertEqual(ev['script'], 'DE-MOVED')
        self.assertIn(D.NODES[new]['name'], ev['text'])
        j.act('dl_decide', option='accept')
        t = j.get(tid)
        self.assertEqual((t['run']['dest'], t['run']['moved']), (new, 'accept'))
        self.assertEqual(public_state(j.state)['careers']['delivery']['tasks'][0]['dest'], new)
        load(j, tid)
        ride(j, new)
        before = j.c['earnings']
        j.act('dl_deliver', task=tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(j.get(tid)['run']['fee'], D._fee(j.c, dict(j.get(tid), run=dict(j.get(tid)['run'], moved=None))) + D.REDIRECT_FEE)
        validate_state(json.loads(json.dumps(j.state)))

    def test_moved_address_found_at_the_door_and_refused(self):
        j, tid = v2_journey(lambda t, d: t['_moved'] and t['needs']['kind'] == 'parcel' and not t['needs']['cod']
                            and not t['needs']['unit_missing'] and t['needs']['size'] == 'S' and t['_w'] <= D.LOAD_LIMIT and not t['needs']['fragile']
                            and D.weather(d) == 'sun')
        load(j, tid)
        ride(j, j.get(tid)['needs']['dest'])
        r = j.act('dl_deliver', task=tid)
        self.assertIn('chuyển', r['message'])
        j.act('dl_decide', option='refuse')
        t = j.get(tid)
        self.assertEqual((t['status'], t['run']['moved']), ('cancelled', 'refuse'))
        self.assertLessEqual(review(j, tid)['stars'], 2)

    def test_clean_streak_and_daily_target_bonuses(self):
        j = Journey('delivery')                            # day 1: P2, F1, P1
        live_day(j)
        data(j)['quest'].update(goal=2, bonus=12)
        data(j)['desk'].update(day=1, plan=[], fired=0)
        P2, F1, P1 = [t['id'] for t in j.c['tasks']]
        for tid in (P2, F1, P1):
            j.act('ask', task=tid)
        j.act('dl_check', task=P2)
        j.act('dl_check', task=P1)
        j.act('dl_pack', task=P1, item='bubble')
        j.act('dl_load', task=P1)
        j.act('dl_load', task=P2)
        j.act('dl_plan', route=['com', 'office', 'villa', 'apt'])
        j.act('dl_ride')
        j.act('dl_check', task=F1)
        j.act('dl_load', task=F1)
        j.act('dl_ride')
        j.act('dl_deliver', task=F1)
        self.assertEqual(data(j)['streak'], 1)
        j.act('dl_ride')
        before = j.c['money']
        r = j.act('dl_deliver', task=P1)
        self.assertIn('Đạt mốc', r['message'])
        self.assertTrue(data(j)['quest']['paid'])
        self.assertGreaterEqual(j.c['money'] - before, 12)
        j.act('dl_call', task=P2)
        j.act('dl_ride')
        wait_until(j, 40)
        r = j.act('dl_deliver', task=P2, change=63)
        d = data(j)
        self.assertEqual(d['streak'], 3)
        self.assertIn('Chuỗi 3', r['message'])
        self.assertEqual(d['stats']['streak_bonus'], D.STREAK_BONUS)
        self.assertEqual(len(d['stars']), 3)
        score = public_state(j.state)['careers']['delivery']['data']['score']
        self.assertIsNone(score['rating'])                 # a few more orders before it counts
        self.assertNotIn('stars', public_state(j.state)['careers']['delivery']['data'])

    def test_top_rating_adds_a_priority_bonus_to_new_orders(self):
        j, tid = v2_journey(lambda t, d: t['needs']['order'] == 'P3' and not (t['_dog'] or t['_bomb'] or t['_moved']))
        base = D._fee(j.c, j.get(tid))
        data(j)['stars'] = [5, 5, 5, 4, 5]
        self.assertEqual(D.rating(data(j)), 48)
        self.assertEqual(D._fee(j.c, j.get(tid)), base + D.TOP_BONUS)
        legacy = dict(j.get(tid))
        legacy.pop('gen')
        self.assertEqual(D._fee(j.c, legacy), base)       # old orders keep their price

    def test_every_road_surprise_and_option_is_playable(self):
        generic = [x for x in D.EVENTS if x.get('need_mark') != 'ctx']
        self.assertGreaterEqual(len(D.EVENTS), 12)
        for x in generic:
            for opt in x['options']:
                j = Journey('delivery', slot=0, day=6)
                j.c['money'] = j.c['money']
                force(j, x['id'])
                view = public_state(j.state)['careers']['delivery']['data']['desk']['ev']
                self.assertEqual(view['script'], x['id'])
                j.act('dl_decide', option=opt['id'])
                self.assertIsNone(data(j)['desk']['ev'])
                self.assertTrue(data(j)['desk']['last']['outcome'], (x['id'], opt['id']))
                validate_state(json.loads(json.dumps(j.state)))
        for x in D.EVENTS:
            self.assertIn(x.get('default', x['options'][-1]['id']), [o['id'] for o in x['options']])
            for opt in x['options']:
                self.assertTrue(opt['label'])
                blob = json.dumps(opt, ensure_ascii=False)
                for word in ('NPC', 'người chơi', 'trong game', 'anh/chị', 'chị chủ', 'anh chủ', 'cô chủ'):
                    self.assertNotIn(word, blob)

    def test_power_cut_blocks_the_pump_until_six(self):
        j, tid = v2_journey(lambda t, d: t['needs']['order'] == 'P3' and not (t['_dog'] or t['_bomb'] or t['_moved']))
        force(j, 'DE-NOGAS')
        j.act('dl_decide', option='wait')
        ride(j, 'gas')
        with self.assertRaises(GameError):
            j.act('dl_refuel', amount=10, confirm=True)
        wait_until(j, 60)
        j.act('dl_refuel', amount=10, confirm=True)

    def test_storm_wrap_uses_rain_bags_or_soaks(self):
        j, tid = v2_journey(lambda t, d: t['needs']['order'] == 'P7' and D.weather(d) == 'sun' and not (t['_dog'] or t['_moved']))
        load(j, tid)
        force(j, 'DE-STORM')
        stock = kit.stock(j.c, 'rainbag')
        j.act('dl_decide', option='wrap')
        self.assertIn('rainbag', j.get(tid)['run']['packed'])
        self.assertEqual(kit.stock(j.c, 'rainbag'), stock - 1)
        j, tid = v2_journey(lambda t, d: t['needs']['order'] == 'P7' and D.weather(d) == 'sun' and not (t['_dog'] or t['_moved']))
        load(j, tid)
        force(j, 'DE-STORM')
        j.act('dl_decide', option='go')
        self.assertTrue(j.get(tid)['run']['_broken'])     # the original tender papers are soaked

    def test_close_takes_the_default_and_reports_the_day(self):
        j, tid = v2_journey(lambda t, d: t['needs']['order'] == 'P3' and not (t['_dog'] or t['_bomb'] or t['_moved']))
        live_day(j)
        force(j, 'DE-POLICE')
        out = j.act('end_day', carry_event=True)['summary']['career']
        self.assertIn('Chốt kiểm tra', out['surprise'])
        self.assertTrue(any('Mốc ca' in x for x in out['lines']))
        self.assertIsNone(data(j)['desk']['ev'])
        j.act('start_day')
        d = data(j)
        self.assertEqual(d['today']['day'], j.c['day'])
        self.assertEqual(d['quest']['day'], j.c['day'])

    def test_old_save_gets_new_data_and_keeps_old_orders(self):
        j, tid = v2_journey(lambda t, d: t['needs']['order'] == 'P3' and not (t['_dog'] or t['_bomb'] or t['_moved']))
        state = json.loads(json.dumps(j.state))
        c = state['careers']['delivery']
        d = c['ext']['data']
        for k in ('desk', 'today', 'tyre', 'streak', 'best', 'stars', 'quest', 'stats'):
            d.pop(k)
        # An order saved by the previous version: v1 generator, run without the new keys.
        old = D.make_task(c['day'], 5, kit.LEGACY_TURN + 3)
        old['created_turn'] = 3
        for k in D.RUN_V2:
            old['run'].pop(k)
        c['tasks'].append(old)
        validate_state(state)
        d = state['careers']['delivery']['ext']['data']
        self.assertEqual(d['tyre'], 100)
        self.assertEqual(d['desk'], kit.desk_initial())
        moved = next(t for t in state['careers']['delivery']['tasks'] if t['id'] == old['id'])
        self.assertGreaterEqual(moved['created_turn'], kit.LEGACY_TURN)
        self.assertIn('dog', moved['run'])
        pub = public_state(state)['careers']['delivery']
        self.assertIn('road', pub['data'])
        for t in pub['tasks']:
            for secret in ('_dog', '_bomb', '_moved'):
                self.assertNotIn(secret, t)

    def test_tampering_with_new_facts_is_rejected(self):
        j, tid = v2_journey(lambda t, d: t['_bomb'])
        for key, value in (('_bomb', False), ('_dog', True), ('_moved', 'hub')):
            state = json.loads(json.dumps(j.state))
            t = next(x for x in state['careers']['delivery']['tasks'] if x['id'] == tid)
            t[key] = value
            with self.assertRaises(GameError):
                validate_state(state)
        state = json.loads(json.dumps(j.state))
        next(x for x in state['careers']['delivery']['tasks'] if x['id'] == tid)['run']['dest'] = 'vet'
        with self.assertRaises(GameError):
            validate_state(state)
        state = json.loads(json.dumps(j.state))
        state['careers']['delivery']['ext']['data']['tyre'] = 140
        with self.assertRaises(GameError):
            validate_state(state)


class DeliveryConsequenceTests(unittest.TestCase):
    """A sloppy delivery costs the courier, in proportion (game.consequences)."""

    def _food(self, key, change=None, way='main', check=True, late=0):
        j, tid = journey(key, rain=False)
        n = j.get(tid)['needs']
        ride(j, n['pickup'])
        wait_until(j, j.get(tid)['run']['t0'] + n['prep'])
        if check:
            j.act('dl_check', task=tid)
        j.act('dl_load', task=tid)
        data(j)['clock'] += late
        j.act('dl_plan', route=[n['dest']])
        j.act('dl_ride', way=way)
        earned = j.c['earnings']
        r = j.act('dl_deliver', task=tid, **({} if change is None else dict(change=change)))
        return j, tid, j.c['earnings'] - earned - D.SPEC['tip'], r

    def test_right_delivery_full_fee_no_slips(self):
        j, tid, got, _ = self._food('F4', change=2)
        t = j.get(tid)
        self.assertEqual(t.get('slips') or [], [])
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertEqual(got, t['run']['fee'])
        self.assertEqual(got, D._fee(j.c, t))
        self.assertGreaterEqual(review(j, tid)['stars'], 4)

    def test_short_change_and_spilled_soup_are_named_in_the_review(self):
        j, tid, _, _ = self._food('F4', change=0)
        t = j.get(tid)
        self.assertEqual([s['code'] for s in t['slips']], ['short_change'])
        post = review(j, tid)
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('thối thiếu', post['text'])
        self.assertIn(t['reaction']['kind'], ('accept', 'grumble', 'discount', 'refund'))
        j, tid, _, _ = self._food('F4', change=2, way='short')
        t = j.get(tid)
        self.assertEqual([s['code'] for s in t['slips']], ['spilled'])
        self.assertIn('Nước lèo', review(j, tid)['text'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_severity_scales_the_stars(self):
        j1, t1, _, _ = self._food('F1', late=20)                      # a bit late: a small slip
        j2, t2, _, _ = self._food('F1', check=False)                  # soup bags missing: a clear one
        self.assertEqual(j1.get(t1)['slips'][0]['sev'], 1)
        self.assertEqual(j2.get(t2)['slips'][0]['sev'], 2)
        self.assertGreater(review(j1, t1)['stars'], review(j2, t2)['stars'])

    def test_late_cut_replaces_the_flat_deduction_and_is_paid_once(self):
        from game import consequences as cq
        j, tid, got, _ = self._food('F1', late=25)
        t = j.get(tid)
        cut = t['reaction']['cut']
        late, t['run']['late'] = t['run']['late'], 0
        base = D._fee(j.c, t)
        t['run']['late'] = late
        self.assertEqual(got, base - cut if cut else base - D.LATE_FEE)
        money = j.c['money']
        again = cq.react(j.state, j.c, t, base, who='Anh Tùng')
        self.assertEqual((again['cut'], j.c['money']), (cut, money))
        validate_state(json.loads(json.dumps(j.state)))

    def test_no_room_number_still_delivers_with_a_slip(self):
        j, p2 = journey('P2')
        j.act('dl_check', task=p2)
        j.act('dl_load', task=p2)
        ride(j, 'apt')
        wait_until(j, 45)
        clock = data(j)['clock']
        j.act('dl_deliver', task=p2, change=63)
        t = j.get(p2)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['slips'][0]['code'], 'no_room')
        self.assertGreaterEqual(data(j)['clock'], clock + 8)
        self.assertLessEqual(review(j, p2)['stars'], 3)
        validate_state(json.loads(json.dumps(j.state)))

    def test_parcel_left_with_someone_else_without_permission(self):
        j, p1 = journey('P1', rain=False)
        j.act('dl_check', task=p1)
        j.act('dl_pack', task=p1, item='bubble')
        j.act('dl_load', task=p1)
        ride(j, 'villa')
        j.act('dl_safedrop', task=p1, confirm=True)
        t = j.get(p1)
        self.assertEqual(t['run']['outcome'], 'safedrop')
        self.assertEqual(t['slips'][0]['code'], 'handed_over')
        self.assertLessEqual(review(j, p1)['stars'], 3)

    def test_broken_parcel_is_reported_without_a_second_charge(self):
        j, p1 = journey('P1', rain=False)
        j.act('dl_check', task=p1)
        j.act('dl_load', task=p1)
        ride(j, 'villa')
        j.act('dl_deliver', task=p1)
        money = j.c['money']
        j.act('dl_fail', task=p1, confirm=True)
        t = j.get(p1)
        self.assertEqual(t['slips'][0]['code'], 'broken')
        self.assertEqual(j.c['money'], money - t['run']['comp'])       # only the half-value compensation
        self.assertTrue(any(p.get('report') and p.get('source') == p1 for p in j.c['feed']))
        validate_state(json.loads(json.dumps(j.state)))


if __name__ == '__main__':
    unittest.main()
