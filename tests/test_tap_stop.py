"""Stop taps on a running meter are judged at the moment the player pressed stop (payload `tap_at`,
game/careers/kit.py tap_now), not when the command reaches the server: player feedback #100 ("bấm dừng rồi
nó vẫn cứ chạy lố" on the milk-tea sealer and the pet bath). The moment stays within honest bounds, and an
older page that sends no `tap_at` is judged on arrival as before (rolling release)."""
import copy
import math
import unittest

import game.careers.kit as kit
from game.engine import apply_action, validate_state
from game.careers import pet_care as P
from tests.helpers import Journey
from tests.test_milk_tea import make_cup
from tests.test_career_cafe_bakery import find_slot
from tests.test_career_pet_care import find as pet_find


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t


class TapStopTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def stop(self, j, action, at, arrive, tap=True, **payload):
        """A copy of the journey's save gets the stop command arriving at `arrive`, tapped at `at`."""
        state = copy.deepcopy(j.state)
        self.clock.t = arrive
        if tap:
            payload['tap_at'] = at
        state, result = apply_action(state, j.career, action, payload)
        validate_state(state)
        return state, result

    def twin(self, j, action, at, lag, pick, **payload):
        """Tapped at `at`, arriving `lag` seconds later = arriving at once; arriving late without `tap_at`
        is judged later (the old way). Returns the three picked outcomes."""
        s0, r0 = self.stop(j, action, at, at, tap=False, **payload)
        s1, r1 = self.stop(j, action, at, at + lag, **payload)
        s2, _ = self.stop(j, action, at, at + lag, tap=False, **payload)
        c = j.career
        self.assertEqual(pick(s1['careers'][c]), pick(s0['careers'][c]))
        self.assertEqual(r1.get('message'), r0.get('message'))
        return pick(s0['careers'][c]), pick(s1['careers'][c]), pick(s2['careers'][c])


class TapNowTests(TapStopTest):
    def test_bounds(self):
        self.clock.t = 100.0
        self.assertEqual(kit.tap_now({}), 100.0)
        self.assertEqual(kit.tap_now(None), 100.0)
        self.assertEqual(kit.tap_now({'tap_at': 99.2}), 99.2)            # a 0.8 s trip: the moment of the tap
        self.assertEqual(kit.tap_now({'tap_at': 100.1}), 100.1)          # the page's clock a little fast
        self.assertEqual(kit.tap_now({'tap_at': 101.0}), 100.0 + kit.TAP_AHEAD)
        self.assertEqual(kit.tap_now({'tap_at': 10.0}), 100.0 - kit.TAP_LAG)
        self.assertEqual(kit.tap_now({'tap_at': 97}), 97.0)              # an int is a number too
        for bad in ('99', True, None, math.nan, math.inf, -math.inf, [99], {'t': 99}):
            self.assertEqual(kit.tap_now({'tap_at': bad}), 100.0, bad)


class MilkTeaSealTests(TapStopTest):
    def ready(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        make_cup(j, tid, skip_seal=True)
        self.clock.t += 1
        j.act('tea_seal_start', task=tid)
        t0 = next(t for t in j.c['tasks'] if t['id'] == tid)['cup']['seal_t']
        return j, tid, t0

    def quality(self, c, tid):
        return next(t for t in c['tasks'] if t['id'] == tid)['cup']['seal_q']

    def test_released_in_the_green_zone_on_a_slow_network(self):
        j, tid, t0 = self.ready()
        now, tapped, late = self.twin(j, 'tea_seal', t0 + 2.0, 1.2, lambda c: self.quality(c, tid), task=tid)
        self.assertEqual((now, tapped, late), ('perfect', 'perfect', 'ok'))   # 3.2 s on arrival: past the green zone
        s, r = self.stop(j, 'tea_seal', t0 + 2.0, t0 + 2.4, task=tid)
        self.assertEqual(r['held'], 2.0)                                        # the seconds graded, for the page's checks

    def test_a_moment_too_old_or_in_the_future_is_bounded(self):
        j, tid, t0 = self.ready()
        # "Tapped at 2.0 s" arriving at 6 s: judged at 3.0 s (6 - TAP_LAG), not perfect, not burnt.
        s, r = self.stop(j, 'tea_seal', t0 + 2.0, t0 + 6.0, task=tid)
        self.assertEqual(r['seal'], 'ok')
        # "Tapped at 2.0 s" arriving at 1.0 s: at most TAP_AHEAD later, still short of the green zone.
        s, r = self.stop(j, 'tea_seal', t0 + 2.0, t0 + 1.0, task=tid)
        self.assertEqual(r['seal'], 'ok')
        # Before the press (or a negative number): never less than nothing, the film does not stick.
        s, r = self.stop(j, 'tea_seal', t0 - 5, t0 + 0.5, task=tid)
        self.assertFalse(next(t for t in s['careers']['milk_tea']['tasks'] if t['id'] == tid)['cup']['sealed'])

    def test_a_plain_seal_ignores_the_moment(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        make_cup(j, tid, skip_seal=True)
        r = j.act('tea_seal', task=tid, tap_at=1.0)
        self.assertEqual(r['seal'], 'ok')


class PetBathTests(TapStopTest):
    def bathed(self):
        day, slot = pet_find('groom', 'Bông')
        j = Journey('pet_care', slot=slot, day=day)
        j.act('ask', task=j.task['id'])
        j.act('pc_brush', tool='brush')
        j.act('pc_bath', shampoo='normal', temp=37)
        return j

    def test_rinse_counts_the_seconds_seen(self):
        j = self.bathed()
        j.act('pc_rinse', mode='start')
        t0 = j.task['g']['rinse']
        now, tapped, late = self.twin(j, 'pc_rinse', t0 + 7.5, 1.0, lambda c: c['tasks'][0]['g']['rinse_s'], mode='stop')
        self.assertEqual((now, tapped, late), (7.5, 7.5, 8.5))

    def test_dryer_turned_off_in_time_is_not_overdried(self):
        j = self.bathed()
        j.act('pc_rinse', mode='start')
        self.clock.t += P.RINSE_MIN + 1
        j.act('pc_rinse', mode='stop')
        j.act('pc_dry', mode='start', heat='warm')
        t0 = j.task['g']['dry']
        need = P.DRY_NEED[j.task['needs']['coat']] * (1.5 if j.task['needs'].get('humid') else 1)
        at = t0 + need * P.DRY_OVER - 0.3
        pick = lambda c: (c['tasks'][0]['g']['overdry'], c['tasks'][0]['g']['dry_pct'])
        now, tapped, late = self.twin(j, 'pc_dry', at, 1.5, pick, mode='stop')
        self.assertFalse(tapped[0])
        self.assertTrue(late[0])
        self.assertGreaterEqual(tapped[1], 100)


class OtherMetersTests(TapStopTest):
    """The same rule on every stop-on-tap meter: espresso, steamed milk, the oven, the sewing machine, the
    homestay egg pan and window, the noodle basket, the dye timer."""

    def test_espresso_shot(self):
        day, slot = find_slot(lambda n: n['kind'] == 'drink' and n['drink'] == 'espresso' and n['shots'] == 1, days=[1])
        j = Journey('cafe_bakery', slot=slot, day=day)
        j.act('ask')
        j.act('cb_cup', kind='mug', size='S')
        j.act('cb_dose', beans='house', grind='fine', grams=18)
        j.act('cb_pull')
        t0 = j.task['drink']['pulling']
        pick = lambda c: c['tasks'][0]['drink']['shots'][-1]['x']
        now, tapped, late = self.twin(j, 'cb_stop', t0 + 29, 2.5, pick)
        self.assertEqual((tapped, late), ('balanced', 'strong'))

    def test_noodle_basket(self):
        from game.careers import restaurant as R
        j = Journey('restaurant')
        j.act('ask')
        j.act('rs_container', kind='box' if j.task['needs']['takeaway'] else 'bowl')
        j.act('rs_boil')
        t0 = j.task['bowl']['boiling']
        shift = R.WEAK_FIRE if R._plan(j.c)['rules'].get('weak_fire') else 0
        at = t0 + R.BOIL['perfect'] + shift - 0.5
        now, tapped, late = self.twin(j, 'rs_drain', at, 2.0, lambda c: c['tasks'][0]['bowl']['noodles'])
        self.assertEqual(tapped, ['perfect'])
        self.assertEqual(late, ['soft'])

    def test_dye_timer(self):
        from tests.test_career_salon import SalonTests
        helper = SalonTests('test_office_full_service_five_stars')
        helper.clock = self.clock
        j = helper.office_to_plan()
        j.act('sl_mix', kind='color', shade='dye_6_1', dev=20, ratio='1:1')
        j.act('sl_apply')
        t0 = j.task['timer']['start']
        w = j.task['timer']
        from game.careers import salon as S
        ideal = S._window(w['kind'], w['fragile'], w.get('fast', False))['ideal']
        pick = lambda c: c['tasks'][0]['results']['color']['zone']
        now, tapped, late = self.twin(j, 'sl_rinse', t0 + ideal - 0.4, 1.5, pick)
        self.assertEqual(tapped, 'ideal')
        self.assertNotEqual(late, 'ideal')

    def test_sewing_machine(self):
        from game.careers import clothing as A
        from tests.test_career_clothing import job
        j = job('alter', days=range(3, 40))
        tid = j.task['id']
        j.act('ao_measure', task=tid)
        j.act('ao_alter_self', task=tid, cm=j.task['needs']['_cm'])
        self.clock.t += 1
        j.act('ao_sew_start', task=tid)
        t0 = j.get(tid)['alt']['start']
        hi = (A.SEW_ZONE_EASY if kit.tier(j.c['day']) == 0 else A.SEW_ZONE)[1]
        pick = lambda c: next(t for t in c['tasks'] if t['id'] == tid)['alt']['seam']
        now, tapped, late = self.twin(j, 'ao_sew_stop', t0 + A.SEW_SECONDS * hi - 0.1, 1.0, pick, task=tid)
        self.assertEqual(tapped, 'good')
        self.assertEqual(late, 'crooked')

    def test_homestay_egg(self):
        from game.careers import homestay as H
        from tests.test_career_homestay import find
        day, slot = find('breakfast', lambda t: t['needs']['eggs']['runny'] + t['needs']['eggs']['well'] > 0)
        j = Journey('homestay', slot=slot, day=day)
        j.act('ask')
        j.act('hs_egg')
        t0 = j.task['tray']['pan']
        now, tapped, late = self.twin(j, 'hs_plate', t0 + H.EGG['raw'] - 0.3, 1.0, lambda c: c['tasks'][0]['tray']['eggs'])
        self.assertEqual(tapped, ['raw'])
        self.assertNotEqual(late, ['raw'])


if __name__ == '__main__':
    unittest.main()
