"""Tiệm kem Góc Phượng (plugin career ice_cream): the morning (thermometer, knob, a tub frozen again,
the scoop well), the freezer lid and its temperature, scooping by weight, cups / cones / coconut
shells / take-away boxes / sticks, toppings and allergies, the melt clock, the birthday tray, cash
through the shared till (Bé Chíp's coins), surprises, determinism, save validation and old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game.careers import kit, till, PLUGINS
from game.content import initial_career, make_task
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state

KM = PLUGINS.get('ice_cream')


class Clock:
    def __init__(self):
        self.t = 9000.0

    def __call__(self):
        return self.t


def find(kind=None, title=None, days=range(1, 40), slots=range(1, 5)):
    for day in days:
        for slot in slots:
            t = make_task('ice_cream', day, slot, 1)
            if (kind is None or t['kind'] == kind) and (title is None or t['title'] == title):
                return day, slot
    raise AssertionError(f'no {kind} {title}')


class Base(unittest.TestCase):
    def setUp(self):
        if KM is None:
            raise unittest.SkipTest('ice_cream is filtered out by MNL_CAREERS')
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, day, slot, opened=True):
        """A customer on its own, the shop already set up (freezer at −18 °C, fresh well)."""
        self.j = Journey('ice_cream', slot=slot, day=day)
        d = KM._data(self.j.c)
        d['intro'] = True
        d['shop']['open'] = opened
        d['fz'].update(temp=-18, knob=4, lid=False, read=True)
        d['well'] = dict(n=0, fresh=True)
        d['refrozen'] = None
        d['learn']['done'] = True            # past the apprenticeship (tested on its own below)
        for x in KM.ITEMS:
            kit.add_lot(self.j.c, x['id'], 6, x['cost'], 30, 'test')
        return self.j.task

    def settle_desk(self):
        ev = self.d['desk']['ev']
        if ev:
            self.j.act('kem_desk', option=kit.desk_script(KM.DESK, ev['script'])['default'])

    def scoop(self, tid, f, press='vua', fix=True):
        self.j.act('kem_scoop', task=tid, f=f, press=press)
        if fix:
            for _ in range(3):
                g = self.j.get(tid)['cups'][-1]['sc'][-1]['g']
                if g < 60:
                    self.j.act('kem_adjust', task=tid, delta=1)
                elif g > 70:
                    self.j.act('kem_adjust', task=tid, delta=-1)
        return self.j.get(tid)['cups'][-1]['sc'][-1]

    def make(self, tid, avoid=None):
        """Build exactly what was ordered, closing the lid after each cup."""
        t = self.j.get(tid)
        for ln in t['needs']['lines']:
            if ln['v'] == 'que':
                self.j.act('kem_que', task=tid)
            elif ln['v'] == 'hop':
                self.j.act('kem_vessel', task=tid, v='hop')
                self.j.act('kem_tare', task=tid)
                def left():
                    return ln['g'] - sum(x['g'] for x in self.j.get(tid)['cups'][-1]['sc'])
                while left() > 80:
                    self.j.act('kem_scoop', task=tid, f=ln['f'][0], press='vua')
                    self.j.act('kem_lid', open=False)
                while left() > 30:
                    self.j.act('kem_scoop', task=tid, f=ln['f'][0], press='nhe')
                    self.j.act('kem_lid', open=False)
                while left() > 0:
                    if self.j.get(tid)['cups'][-1]['sc'][-1]['a'] >= 3:
                        self.j.act('kem_scoop', task=tid, f=ln['f'][0], press='nhe')
                    else:
                        self.j.act('kem_adjust', task=tid, delta=1)
            else:
                self.j.act('kem_vessel', task=tid, v=ln['v'])
                for f in ln['f']:
                    self.scoop(tid, f)
                if ln['top']:
                    self.j.act('kem_top', task=tid, top=next(x for x in ln['top'] if x != t['needs'].get('allergy')))
            self.j.act('kem_lid', open=False)
        if t['kind'] == 'tray':
            self.j.act('kem_pack', task=tid, pack='xop')

    def serve_pay(self, tid):
        self.j.act('kem_lid', open=False)
        r = self.j.act('kem_serve', task=tid)
        t = self.j.get(tid)
        self.assertEqual(t['stage'], 'pay', r)
        rec = t['cash']
        return self.j.act('kem_pay', task=tid, change=till.greedy(max(0, till.due(rec))))

    def codes(self, tid):
        return {x['code'] for x in self.j.get(tid).get('slips') or []}


class Spec(Base):
    def test_spec_shape(self):
        s = KM.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('ice_cream', 'kem_', 'food'))
        self.assertTrue(5 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertIn('ice_cream', jr.CH_UNLOCKS[3])
        for name in KM.ACTIONS:
            self.assertTrue(name.startswith('kem_'))
        for name in (*KM.NO_TICK, *KM.PHYSICAL, *KM.FREE):
            self.assertTrue(name in KM.ACTIONS or name in ('kem_intro', 'kem_lid', 'kem_desk'), name)

    def test_tasks_are_deterministic_and_cover_every_kind(self):
        kinds = set()
        for day in range(1, 25):
            for slot in range(0, 5):
                a, b = make_task('ice_cream', day, slot, 3), make_task('ice_cream', day, slot, 3)
                self.assertEqual(a, b)
                kinds.add(a['kind'])
        self.assertEqual(kinds, set(KM.KINDS))

    def test_desk_scripts_and_situations_are_well_formed(self):
        for x in KM.DESK:
            self.assertIn(x['default'], {o['id'] for o in x['options']})
        ids = [s['id'] for s in KM.SITUATIONS]
        self.assertEqual(len(ids), len(set(ids)))


class Morning(Base):
    def test_first_morning_teaches_the_knob_thermometer_and_well(self):
        self.j = Journey('ice_cream')
        fz = self.d['fz']
        self.assertEqual(fz['knob'], 2)
        self.assertGreaterEqual(fz['temp'], KM.SOFT_AT)       # soft: the thermometer has something to say
        setup = self.j.task
        self.assertEqual(setup['kind'], 'setup')
        self.j.act('kem_intro')
        self.assertIn('số 2', self.j.act('kem_thermo')['message'])
        self.j.act('kem_knob', knob=4)
        self.j.act('kem_check')
        self.j.act('kem_well')
        r = self.j.act('kem_open', task=setup['id'])
        self.assertTrue(r.get('celebrate'))
        self.assertFalse(self.j.get(setup['id']).get('slips'))
        self.assertTrue(self.d['shop']['open'])
        # The freezer cools towards the knob with every move at the counter.
        t = next(t for t in self.j.c['tasks'] if t['kind'] != 'setup')
        before = self.d['fz']['temp']
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v=t['needs']['lines'][0]['v'] if t['needs']['lines'][0]['v'] != 'que' else 'ly')
        self.assertLess(self.d['fz']['temp'], before)

    def test_skipping_the_morning_is_named(self):
        self.j = Journey('ice_cream')
        self.j.act('kem_intro')
        setup = self.j.task
        self.j.act('kem_open', task=setup['id'])
        self.assertEqual(self.codes(setup['id']), {'no_thermo', 'knob', 'well_old'})

    def test_a_refrozen_tub_is_found_and_thrown_out_or_sold_with_a_safety_slip(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        d = self.d
        d['tubs']['dua'] = dict(g=1000, c=16, day=day, rf=True)
        d['refrozen'] = 'dua'
        d['shop']['checked'] = True
        self.assertEqual(public_state(self.j.state)['careers']['ice_cream']['data']['refrozen'], 'dua')
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.assertIn('lạo xạo', self.j.act('kem_scoop', task=t['id'], f='dua')['message'])
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        self.assertIn('refrozen', self.codes(t['id']))
        self.assertTrue(any(x['safety'] for x in self.j.get(t['id'])['slips']))

    def test_discarding_the_refrozen_tub_books_the_waste(self):
        self.j = Journey('ice_cream')
        d = self.d
        d['tubs']['dau'] = dict(g=900, c=15, day=1, rf=True)
        d['refrozen'] = 'dau'
        self.j.act('kem_check')
        self.j.act('kem_discard')
        self.assertIsNone(self.d['refrozen'])
        self.assertNotIn('dau', self.d['tubs'])
        self.assertEqual(self.j.c['life']['waste'][-1]['reason'], 'Kem chảy rồi đông lại')

    def test_a_warm_afternoon_leaves_a_tub_frozen_again(self):
        self.j = Journey('ice_cream')
        self.j.act('kem_intro')
        setup = self.j.task
        for a in ('kem_thermo', 'kem_check', 'kem_well'):
            self.j.act(a)
        self.j.act('kem_knob', knob=4)
        self.j.act('kem_open', task=setup['id'])
        self.d['tubs']['vani'] = dict(g=800, c=14, day=1, rf=False)
        self.d['today']['peak'] = -6
        self.settle_desk()
        self.j.act('end_day', carry_event=True)
        self.assertTrue(self.d['warm_night'])
        self.j.act('start_day')
        self.assertIsNotNone(self.d['refrozen'])
        self.assertTrue(self.d['tubs'][self.d['refrozen']]['rf'])
        validate_state(self.j.state)


class Freezer(Base):
    def test_open_lid_warms_closed_lid_cools(self):
        day, slot = find('serve', 'Bé Chíp mua ốc quế')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='oc')
        self.j.act('kem_scoop', task=t['id'], f='dau')
        self.assertTrue(self.d['fz']['lid'])
        self.assertEqual(self.d['fz']['temp'], -17)          # a freshly opened lid
        self.j.act('kem_scoop', task=t['id'], f='dau')
        self.assertEqual(self.d['fz']['temp'], -15)          # a lid left open costs twice
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        self.assertEqual(self.d['fz']['temp'], -17)

    def test_warm_freezer_gives_heavy_scoops_cold_gives_small(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.d['fz']['temp'] = -10
        warm = KM.scoop_grams(self.d, t, 'vani', 'vua')
        self.d['fz']['temp'] = -24
        cold = KM.scoop_grams(self.d, t, 'vani', 'vua')
        self.d['fz']['temp'] = -18
        ok = KM.scoop_grams(self.d, t, 'vani', 'vua')
        self.assertGreater(warm, ok)
        self.assertLess(cold, ok)
        self.assertTrue(56 <= ok <= 72)

    def test_serving_with_the_lid_open_is_named(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.scoop(t['id'], 'dua')
        self.j.act('kem_serve', task=t['id'])
        self.assertIn('lid_open', self.codes(t['id']))

    def test_mushy_scoops_from_a_warm_freezer(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.d['fz']['temp'] = -6
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.scoop(t['id'], 'dua', press='nhe')
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        self.assertIn('mushy', self.codes(t['id']))


class Serving(Base):
    def test_a_clean_cone_with_coins(self):
        day, slot = find('serve', 'Bé Chíp mua ốc quế')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        money = self.j.c['money']
        self.j.act('kem_serve', task=t['id'])
        rec = self.j.get(t['id'])['cash']
        self.assertTrue(all(x in (1, 2, 5) for x in rec['tender']))
        self.assertGreaterEqual(sum(rec['tender']), rec['price'])
        self.assertEqual(rec['price'], KM.PRICES['vien'] + KM.PRICES['oc'])
        r = self.j.act('kem_pay', task=t['id'], change=till.greedy(till.due(rec)))
        t = self.j.get(t['id'])
        self.assertEqual(t['status'], 'completed', r)
        self.assertFalse(t.get('slips'))
        self.assertGreaterEqual(self.j.c['money'], money + rec['price'])
        self.assertEqual(self.d['regulars']['1']['visits'], 1)

    def test_thin_scoop_for_ong_tam_is_a_clear_mistake(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.d['fz']['temp'] = -24
        self.d['fz']['knob'] = 6
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        sc = self.scoop(t['id'], 'dua', press='nhe', fix=False)
        self.assertLess(sc['g'], KM.THIN)
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        slip = next(x for x in self.j.get(t['id'])['slips'] if x['code'] == 'thin')
        self.assertEqual(slip['sev'], 2)

    def test_adjusting_moves_ten_grams_three_times_at_most(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        g = self.scoop(t['id'], 'dua', fix=False)['g']
        tub = self.d['tubs']['dua']['g']
        self.j.act('kem_adjust', task=t['id'], delta=1)
        self.assertEqual(self.j.get(t['id'])['cups'][-1]['sc'][-1]['g'], g + 10)
        self.assertEqual(self.d['tubs']['dua']['g'], tub - 10)
        self.j.act('kem_adjust', task=t['id'], delta=-1)
        self.j.act('kem_adjust', task=t['id'], delta=-1)
        with self.assertRaises(GameError):
            self.j.act('kem_adjust', task=t['id'], delta=1)

    def test_overscooping_is_cohien_s_evening_note(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.j.act('kem_scoop', task=t['id'], f='dua', press='day')
        self.j.act('kem_adjust', task=t['id'], delta=1)
        self.serve_pay(t['id'])
        self.assertGreater(self.d['today']['over_g'], 0)
        summary = KM.on_close(self.j.state, self.j.c)
        self.assertTrue(any('múc dư' in x for x in summary['lines']))

    def test_peanuts_for_an_allergic_customer_is_a_safety_mistake(self):
        day, slot = find('serve', 'Tú với Mít chia ly kem')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.assertIn('Dị ứng đậu phộng', KM.known_request(self.j.c, self.j.get(t['id'])))
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.scoop(t['id'], 'socola')
        self.scoop(t['id'], 'bo')
        self.j.act('kem_top', task=t['id'], top='dau_phong')
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        slip = next(x for x in self.j.get(t['id'])['slips'] if x['code'] == 'allergy')
        self.assertTrue(slip['safety'])
        self.assertEqual(slip['sev'], 3)
        r = self.j.act('kem_pay', task=t['id'], change=[])
        self.assertEqual(self.j.get(t['id'])['reaction']['kind'], 'refuse', r)

    def test_the_right_crunchy_topping_is_clean(self):
        day, slot = find('serve', 'Tú với Mít chia ly kem')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.serve_pay(t['id'])
        self.assertFalse(self.j.get(t['id']).get('slips'))

    def test_wrong_flavour_is_missing_and_extra(self):
        day, slot = find('serve', 'Bé Chíp mua ốc quế')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='oc')
        self.scoop(t['id'], 'vani')
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        self.assertTrue({'missing', 'extra'} <= self.codes(t['id']))

    def test_a_cone_takes_two_scoops_at_most(self):
        day, slot = find('serve', 'Bé Chíp mua ốc quế')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='oc')
        self.j.act('kem_scoop', task=t['id'], f='dau')
        self.j.act('kem_scoop', task=t['id'], f='dau')
        with self.assertRaises(GameError):
            self.j.act('kem_scoop', task=t['id'], f='dau')

    def test_drop_puts_the_cup_in_the_waste(self):
        day, slot = find('serve', 'Bé Chíp mua ốc quế')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='oc')
        self.j.act('kem_scoop', task=t['id'], f='vani')
        self.j.act('kem_drop', task=t['id'])
        self.assertEqual(self.j.get(t['id'])['cups'], [])
        self.make(t['id'])
        self.serve_pay(t['id'])
        self.assertFalse(self.j.get(t['id']).get('slips'))

    def test_sticks_from_the_drawer(self):
        day, slot = find('serve', 'Anh Khang mua kem que')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        n = kit.stock(self.j.c, 'que')
        self.make(t['id'])
        self.assertEqual(kit.stock(self.j.c, 'que'), n - 2)
        self.serve_pay(t['id'])
        t = self.j.get(t['id'])
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['price'], 2 * KM.PRICES['que'])


class Melt(Base):
    def test_slow_service_melts(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.scoop(t['id'], 'dua')
        limit = self.j.get(t['id'])['melt']['limit']
        self.clock.t += limit + 1
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        self.assertIn('melting', self.codes(t['id']))

    def test_very_slow_service_melts_all_over(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.scoop(t['id'], 'dua')
        self.clock.t += self.j.get(t['id'])['melt']['limit'] * 2
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        self.assertIn('melted', self.codes(t['id']))
        self.assertEqual(self.d['today']['melted'], 1)

    def test_public_task_carries_the_melt_clock(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.j.act('kem_scoop', task=t['id'], f='dua')
        v = public_state(self.j.state)['careers']['ice_cream']
        pt = next(x for x in v['tasks'] if x['id'] == t['id'])
        self.assertEqual(pt['melt']['start'], self.clock.t)


class TakeAwayAndTray(Base):
    def test_take_away_box_by_weight_with_tare(self):
        day, slot = find('hop', 'Ông Tám mua kem về cho bà')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.serve_pay(t['id'])
        t = self.j.get(t['id'])
        self.assertFalse(t.get('slips'))
        g = sum(x['g'] for x in t['cups'][0]['sc'])
        self.assertEqual(t['price'], (g * KM.PRICES['hop'] + 50) // 100)

    def test_box_without_tare_for_a_careful_customer(self):
        day, slot = find('hop', 'Ông Tám mua kem về cho bà')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='hop')
        while sum(x['g'] for x in self.j.get(t['id'])['cups'][-1]['sc']) < 480:
            self.j.act('kem_scoop', task=t['id'], f='dua', press='vua')
        with self.assertRaises(GameError):
            self.j.act('kem_tare', task=t['id'])          # too late: the ice cream is in the box
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        self.assertIn('cheat_tare', self.codes(t['id']))

    def test_box_far_too_heavy_is_sent_back(self):
        day, slot = find('hop', 'Ông Tám mua kem về cho bà')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='hop')
        self.j.act('kem_tare', task=t['id'])
        for _ in range(9):
            self.j.act('kem_scoop', task=t['id'], f='dua', press='day')
        self.j.act('kem_lid', open=False)
        r = self.j.act('kem_serve', task=t['id'])
        self.assertFalse(r.get('correct', True))
        self.assertEqual(self.j.get(t['id'])['stage'], 'prep')

    def test_birthday_tray_needs_packing(self):
        day, slot = find('tray')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        for ln in t['needs']['lines']:
            self.j.act('kem_vessel', task=t['id'], v='ly')
            self.scoop(t['id'], ln['f'][0])
            self.j.act('kem_lid', open=False)
        with self.assertRaises(GameError):
            self.j.act('kem_serve', task=t['id'])
        self.j.act('kem_pack', task=t['id'], pack='xop')
        self.clock.t += 600                             # the box keeps it cold on the way
        self.serve_pay(t['id'])
        self.assertFalse(self.j.get(t['id']).get('slips'))

    def test_dry_ice_in_the_tray_is_a_safety_mistake(self):
        day, slot = find('tray')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        for ln in t['needs']['lines']:
            self.j.act('kem_vessel', task=t['id'], v='ly')
            self.scoop(t['id'], ln['f'][0])
            self.j.act('kem_lid', open=False)
        self.j.act('kem_pack', task=t['id'], pack='da_kho')
        self.j.act('kem_serve', task=t['id'])
        self.assertIn('dry_ice', self.codes(t['id']))


class Days(Base):
    def play_day(self):
        self.settle_desk()
        for t in [t for t in self.j.c['tasks'] if t['status'] not in ('completed', 'cancelled')]:
            self.settle_desk()
            if t['kind'] == 'setup':
                for a in ('kem_thermo', 'kem_check', 'kem_well'):
                    self.j.act(a)
                if self.d['refrozen']:
                    self.j.act('kem_discard')
                self.j.act('kem_knob', knob=4)
                self.j.act('kem_open', task=t['id'])
                continue
            if not t['known']:
                self.j.act('ask', task=t['id'])
            self.make(t['id'])
            self.settle_desk()
            self.serve_pay(t['id'])
        self.settle_desk()
        r = self.j.act('end_day', carry_event=True)
        self.j.act('start_day')
        validate_state(self.j.state)
        return r

    def test_ten_days_of_play_stay_valid(self):
        self.j = Journey('ice_cream')
        self.j.act('kem_intro')
        for _ in range(10):
            for x in KM.ITEMS:
                if kit.stock(self.j.c, x['id']) < 4:
                    kit.add_lot(self.j.c, x['id'], 6, x['cost'], x['life'], 'test')
            r = self.play_day()
            self.assertIn('lines', r['summary']['career'])
        self.assertGreater(self.d['stats']['customers'], 10)
        v = public_state(self.j.state)
        json.dumps(v['careers']['ice_cream'])
        self.assertNotIn('rf', json.dumps(v['careers']['ice_cream']['data']['tubs']))

    def test_validator_rejects_tampering(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.j.act('kem_scoop', task=t['id'], f='dua')
        validate_state(self.j.state)
        for mutate in (lambda s: s['careers']['ice_cream']['tasks'][0]['cups'][0]['sc'][0].update(g=5000),
                       lambda s: s['careers']['ice_cream']['tasks'][0]['cups'][0].update(v='xo'),
                       lambda s: s['careers']['ice_cream']['ext']['data']['fz'].update(knob=9),
                       lambda s: s['careers']['ice_cream']['ext']['data'].update(refrozen='sau_rieng'),
                       lambda s: s['careers']['ice_cream']['tasks'][0]['needs'].update(lines=[])):
            bad = copy.deepcopy(self.j.state)
            mutate(bad)
            with self.assertRaises(GameError):
                validate_state(bad)


class OldSaves(Base):
    def test_a_save_without_the_shop_gains_it_fresh_and_nothing_else_moves(self):
        s = new_state()
        jr.enable_story(s, 77)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        s['careers'].pop('ice_cream')
        s['journey']['chapter'] = 4
        s['journey']['unlocked'] = [cid for n in range(1, 5) for cid in jr.CH_UNLOCKS[n] if cid in s['careers']]
        s['journey']['done'] = [1, 2, 3]
        before = {cid: json.dumps(c, sort_keys=True, ensure_ascii=False) for cid, c in s['careers'].items()}
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        self.assertEqual(json.dumps(m['careers']['ice_cream'], sort_keys=True), json.dumps(initial_career('ice_cream'), sort_keys=True))
        for cid, raw in before.items():
            self.assertEqual(json.dumps(m['careers'][cid], sort_keys=True, ensure_ascii=False), raw, cid)
        self.assertIn('ice_cream', m['journey']['unlocked'])


class HouseBatch(Base):
    """Kem nhà làm: measure, cook, cool, churn, freeze; the tub sells the next day."""

    def morning(self):
        self.j = Journey('ice_cream')
        self.j.act('kem_intro')
        self.d['learn']['done'] = True

    def measure(self, f, wrong=None):
        for x in KM.RECIPES[f]['ings']:
            amt = x['right']
            if wrong and x['id'] == wrong[0]:
                amt = wrong[1]
            self.j.act('kem_mk_add', ing=x['id'], amt=amt)
        self.j.act('kem_mk_next')

    def cook(self, stop_at=80):
        goal = stop_at if stop_at > KM.COOK_OK[1] else min(stop_at, KM.COOK_OK[1])
        while self.d['batch']['temp'] < KM.COOK_OK[0] or (stop_at > KM.COOK_OK[1] and self.d['batch']['temp'] < stop_at):
            fire = 'lon' if self.d['batch']['temp'] + 16 < goal else 'nho'
            self.j.act('kem_mk_heat', fire=fire)
            if 'burnt' in self.d['batch']['q']:
                return
        self.j.act('kem_mk_next')

    def cool(self):
        while self.d['batch']['temp'] > KM.COOL_OK:
            self.j.act('kem_mk_cool')
        self.j.act('kem_mk_next')

    def coconut(self, wrong=None, churn=30, stop_at=80, cooled=True):
        money = self.j.c['money']
        self.j.act('kem_mk_start', f='dua')
        self.assertEqual(self.j.c['money'], money - KM.RECIPES['dua']['cost'])
        self.measure('dua', wrong)
        self.cook(stop_at)
        if 'burnt' in self.d['batch']['q']:
            return
        if cooled:
            self.cool()
        else:
            self.j.act('kem_mk_next')
        self.j.act('kem_mk_churn', min=churn)
        return self.j.act('kem_mk_freeze')

    def test_a_good_coconut_batch_freezes_overnight_and_sells_higher(self):
        self.morning()
        r = self.coconut()
        self.assertTrue(r.get('celebrate'), r)
        self.assertEqual(self.d['home'], [dict(f='dua', q='ok', day=1, c=KM.RECIPES['dua']['cost'])])
        self.assertIsNone(self.d['batch'])
        with self.assertRaises(GameError):
            self.j.act('kem_mk_start', f='bo')        # one batch a day
        validate_state(self.j.state)
        # Tomorrow: the house tub opens first and every scoop is worth a little more.
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện', days=range(2, 40))
        home = copy.deepcopy(self.d['home'])
        t = self.at(day, slot)
        self.d['home'] = [dict(h, day=day - 1) for h in home]
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        msg = self.j.act('kem_scoop', task=t['id'], f='dua', press='vua')['message']
        self.assertIn('nhà làm', msg)
        self.assertEqual(self.d['tubs']['dua']['hm'], 'ok')
        self.assertEqual(self.d['home'], [])
        g = self.j.get(t['id'])['cups'][0]['sc'][0]['g']
        while g < 60 or g > 70:
            self.j.act('kem_adjust', task=t['id'], delta=1 if g < 60 else -1)
            g = self.j.get(t['id'])['cups'][0]['sc'][0]['g']
        self.j.act('kem_lid', open=False)
        r = self.j.act('kem_serve', task=t['id'])
        self.assertIn('Kem nhà làm', r['message'])
        self.assertEqual(self.j.get(t['id'])['price'], KM.PRICES['vien'] + KM.HOME_PLUS)
        self.assertFalse(self.j.get(t['id']).get('slips'))
        fb = KM.feedback(self.j.c, self.j.get(t['id']))
        self.assertIn('home', [x['key'] for x in fb['criteria']])

    def test_the_tub_is_not_for_sale_the_same_day(self):
        self.morning()
        self.coconut()
        self.assertFalse(KM.has_tub(self.j.c, self.d, 'dua') and not kit.stock(self.j.c, 'dua')
                         and not self.d['tubs'].get('dua'))
        self.assertEqual(public_state(self.j.state)['careers']['ice_cream']['data']['home'][0]['ready'], False)

    def test_mistakes_give_soft_icy_grainy_tubs(self):
        cases = [(dict(wrong=('duong', 60)), 'icy'), (dict(wrong=('duong', 160)), 'soft'), (dict(churn=15), 'soft'),
                 (dict(churn=45), 'grainy'), (dict(stop_at=KM.BOIL_AT), 'grainy'), (dict(cooled=False), 'soft'),
                 (dict(wrong=('bot', 30)), 'grainy')]
        for kw, q in cases:
            with self.subTest(**{k: str(v) for k, v in kw.items()}):
                self.morning()
                r = self.coconut(**kw)
                self.assertEqual(self.d['home'][0]['q'], q, r)
                self.assertIn('Cô Hiền nếm thử', r['message'])
                self.j.act('kem_mk_toss', i=0)
                self.assertEqual(self.d['home'], [])
                self.assertEqual(self.j.c['life']['waste'][-1]['reason'], 'Hộp kem nhà làm không đạt')

    def test_a_scorched_pot_must_be_poured_away(self):
        self.morning()
        self.j.act('kem_mk_start', f='dua')
        self.measure('dua')
        for _ in range(8):
            self.j.act('kem_mk_heat', fire='lon')
            if 'burnt' in self.d['batch']['q']:
                break
        self.assertIn('burnt', self.d['batch']['q'])
        self.assertTrue(public_state(self.j.state)['careers']['ice_cream']['data']['batch']['burnt'])
        for a in ('kem_mk_next', 'kem_mk_cool', 'kem_mk_heat'):
            with self.assertRaises(GameError):
                self.j.act(a)
        self.j.act('kem_mk_bin')
        self.assertIsNone(self.d['batch'])
        self.assertEqual(self.j.c['life']['waste'][-1]['reason'], 'Mẻ kem nhà làm hỏng')

    def test_icy_house_tub_draws_a_complaint(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.d['home'] = [dict(f='dua', q='icy', day=day - 1, c=7)]
        for _ in range(6):
            kit.take(self.j.c, 'dua', 1) if kit.stock(self.j.c, 'dua') else None
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.scoop(t['id'], 'dua')
        self.j.act('kem_lid', open=False)
        self.j.act('kem_serve', task=t['id'])
        self.assertIn('icy', self.codes(t['id']))
        self.assertEqual(self.j.get(t['id'])['price'], KM.PRICES['vien'])

    def test_avocado_is_blended_not_cooked(self):
        self.morning()
        self.j.act('kem_mk_start', f='bo')
        self.measure('bo')
        with self.assertRaises(GameError):
            self.j.act('kem_mk_heat', fire='nho')
        self.j.act('kem_mk_blend')
        self.j.act('kem_mk_next')                    # one turn only: lumps of avocado left
        self.j.act('kem_mk_churn', min=25)
        self.j.act('kem_mk_freeze')
        self.assertEqual(self.d['home'][0]['q'], 'grainy')

    def test_taro_needs_the_certificate_in_the_story(self):
        story = dict(journey=dict(story=True, certificates={}))
        c = dict(day=9)
        self.assertFalse(KM.recipe_open(story, c, 'khoai_mon'))
        self.assertTrue(KM.recipe_open(story, c, 'dua'))
        story['journey']['certificates'][KM.CERT_ID] = dict(score=83, best=83, earned_day=4, attempts=1)
        self.assertTrue(KM.recipe_open(story, c, 'khoai_mon'))
        self.assertFalse(KM.recipe_open(dict(), dict(day=KM.CERT_FREE_DAY - 1), 'khoai_mon'))
        self.assertTrue(KM.recipe_open(dict(), dict(day=KM.CERT_FREE_DAY), 'khoai_mon'))
        self.morning()
        with self.assertRaises(GameError):
            self.j.act('kem_mk_start', f='khoai_mon')

    def test_taro_is_steamed_first(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện', days=range(KM.CERT_FREE_DAY, 40))
        self.at(day, slot)
        self.j.act('kem_mk_start', f='khoai_mon')
        for _ in range(KM.RECIPES['khoai_mon']['steam']):
            self.j.act('kem_mk_steam')
        self.j.act('kem_mk_next')
        self.measure('khoai_mon')
        self.cook()
        self.cool()
        self.j.act('kem_mk_churn', min=30)
        self.j.act('kem_mk_freeze')
        self.assertEqual(self.d['home'][0], dict(f='khoai_mon', q='ok', day=day, c=KM.RECIPES['khoai_mon']['cost']))

    def test_an_unfinished_batch_is_poured_away_at_close(self):
        self.morning()
        setup = self.j.task
        for a in ('kem_thermo', 'kem_check', 'kem_well'):
            self.j.act(a)
        self.j.act('kem_knob', knob=4)
        if self.d['refrozen']:
            self.j.act('kem_discard')
        self.j.act('kem_open', task=setup['id'])
        self.j.act('kem_mk_start', f='dua')
        self.settle_desk()
        r = self.j.act('end_day', carry_event=True)
        self.assertTrue(any('làm dở' in x for x in r['summary']['career']['lines']))
        self.assertIsNone(self.d['batch'])
        self.assertEqual(self.d['today']['batches'], 1)
        self.j.act('start_day')
        self.assertEqual(self.d['today']['batches'], 0)
        validate_state(self.j.state)

    def test_validator_rejects_a_forged_batch(self):
        self.morning()
        self.j.act('kem_mk_start', f='dua')
        validate_state(self.j.state)
        for mutate in (lambda d: d['batch'].update(f='sau_rieng'), lambda d: d['batch']['ing'].update(duong=999),
                       lambda d: d['batch'].update(q=['tasty']), lambda d: d.update(home=[dict(f='dua', q='burnt', day=1, c=7)]),
                       lambda d: d.update(home=[dict(f='dua', q='ok', day=1, c=7)] * 4),
                       lambda d: d['learn'].update(codes=['nap']), lambda d: d['tubs'].update(dua=dict(g=10, c=1, day=1, rf=False, hm='wow'))):
            bad = copy.deepcopy(self.j.state)
            mutate(bad['careers']['ice_cream']['ext']['data'])
            with self.assertRaises(GameError):
                validate_state(bad)


class Apprenticeship(Base):
    """Học nghề: the first three customers with cô Hiền at your side."""

    def test_cohien_catches_a_thin_scoop_once_and_teaches(self):
        day, slot = find('serve', 'Ông Tám ngồi kể chuyện')
        t = self.at(day, slot)
        self.d['learn']['done'] = False
        self.assertTrue(public_state(self.j.state)['careers']['ice_cream']['data']['learn']['on'])
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.scoop(t['id'], 'dua', press='nhe', fix=False)
        self.j.act('kem_lid', open=False)
        sc = self.j.get(t['id'])['cups'][0]['sc'][0]
        if sc['g'] >= 60:
            self.skipTest('the light scoop came out full')
        r = self.j.act('kem_serve', task=t['id'])
        self.assertFalse(r['correct'])
        self.assertIn('Cô Hiền', r['message'])
        self.assertEqual(self.j.get(t['id'])['stage'], 'prep')
        self.assertFalse(self.j.get(t['id']).get('slips'))
        # The same mistake again goes through (she taught it once).
        self.j.act('kem_serve', task=t['id'])
        self.assertIn('thin', self.codes(t['id']))

    def test_allergy_is_caught_before_it_reaches_the_customer(self):
        day, slot = find('serve', 'Tú với Mít chia ly kem')
        t = self.at(day, slot)
        self.d['learn']['done'] = False
        self.j.act('ask', task=t['id'])
        self.j.act('kem_vessel', task=t['id'], v='ly')
        self.scoop(t['id'], 'socola')
        self.scoop(t['id'], 'bo')
        self.j.act('kem_top', task=t['id'], top='dau_phong')
        self.j.act('kem_lid', open=False)
        r = self.j.act('kem_serve', task=t['id'])
        self.assertIn('dị ứng', r['message'])
        self.j.act('kem_top', task=t['id'], top='banh_que')
        self.serve_pay(t['id'])
        self.assertFalse(self.j.get(t['id']).get('slips'))

    def test_three_customers_and_she_lets_you_stand_alone(self):
        self.j = Journey('ice_cream')
        self.j.act('kem_intro')
        setup = self.j.task
        for a in ('kem_thermo', 'kem_check', 'kem_well'):
            self.j.act(a)
        self.j.act('kem_knob', knob=4)
        self.j.act('kem_open', task=setup['id'])
        self.assertEqual(self.d['desk']['fired'], 0)
        last = None
        for _ in range(KM.APPRENTICE):
            t = next(t for t in self.j.c['tasks'] if t['kind'] != 'setup' and t['status'] not in ('completed', 'cancelled'))
            if not t['known']:
                self.j.act('ask', task=t['id'])
            self.make(t['id'])
            last = self.serve_pay(t['id'])
            if self.d['stats']['customers'] < KM.APPRENTICE and not any(
                    x['status'] not in ('completed', 'cancelled') and x['kind'] != 'setup' for x in self.j.c['tasks']):
                self.j.act('more_work')
        self.assertIn('Học nghề xong', last['message'])
        self.assertTrue(self.d['learn']['done'])
        self.assertFalse(public_state(self.j.state)['careers']['ice_cream']['data']['learn']['on'])
        validate_state(self.j.state)


class Certificate(unittest.TestCase):
    def test_ice_cream_certificate_is_a_craft_certificate(self):
        from game import certificates as ct
        g = ct.INDEX[KM.CERT_ID]
        self.assertEqual(g['careers'], ('ice_cream',))
        self.assertFalse(g['hire'])
        self.assertTrue(g['perk'])
        self.assertNotIn('ice_cream', ct.BY_CAREER)          # no hire bonus: the shop has no interview
        self.assertGreaterEqual(len(g['bank']), ct.DRAW + 4)
        view = next(x for x in ct.content()['groups'] if x['id'] == KM.CERT_ID)
        self.assertEqual(view['perk'], g['perk'])
        self.assertFalse(view['hire'])


if __name__ == '__main__':
    unittest.main()
