"""Waiting guests in the assembly careers (0.9.5, player feedback #11 / #29): while the
player keeps working one order the queue waits at half speed, a bigger order waits
longer, and several stems / toppings go in with one tap (one beat of waiting)."""
import unittest

import game.careers.kit as kit
from game import inventory
from game.careers import clothing as AO
from game.careers import florist as FL
from game.careers import food_service as FS
from game.careers import repair as RP
from game.careers import restaurant as RS
from game.engine import validate_state
from tests.helpers import Journey


def fake_c(turn=10, n=3):
    tasks = [dict(id=f'x-{i}', career='x', status='new', patience=100, deferred=False) for i in range(n)]
    return dict(open=True, life=dict(mode='normal'), turn=turn, tasks=tasks, ext=dict(data={}))


class HelperTests(unittest.TestCase):
    def test_size_factor_is_modest_and_capped(self):
        self.assertEqual(kit.size_factor(3, 7), 1.0)
        self.assertEqual(kit.size_factor(7, 7), 1.0)
        self.assertAlmostEqual(kit.size_factor(11, 7), 1.2)
        self.assertEqual(kit.size_factor(99, 7), kit.SIZE_CAP)
        self.assertLessEqual(kit.SIZE_CAP, 1.5)

    def test_busy_only_right_after_working_the_same_order(self):
        c = fake_c()
        self.assertFalse(kit.busy(c, 'x-0'))
        kit.worked(c, 'x-0')
        self.assertTrue(kit.busy(c, 'x-0'))
        self.assertFalse(kit.busy(c, 'x-1'))
        c['turn'] += kit.BUSY_TURNS
        self.assertTrue(kit.busy(c, 'x-0'))
        c['turn'] += 1
        self.assertFalse(kit.busy(c, 'x-0'))  # stepped away: the queue waits at full speed again

    def test_queue_drains_at_half_speed_while_busy(self):
        idle, busy = fake_c(), fake_c()
        for _ in range(8):
            for c in (idle, busy):
                c['turn'] += 1
                kit.wait_tick(c, 'x', 'x-0', lambda t: 1)
            kit.worked(busy, 'x-0')
        self.assertEqual(idle['tasks'][1]['patience'], 92)
        # The first tick is at full speed (nothing worked yet), the next seven at half: 1 + 3.5.
        self.assertEqual(busy['tasks'][1]['patience'], 96)
        self.assertEqual(busy['tasks'][0]['patience'], 100)  # the guest being served never waits
        self.assertLess(busy['ext']['data']['wait']['carry']['x-1'], 1)

    def test_bigger_order_waits_longer(self):
        c = fake_c()
        size = {'x-1': 7, 'x-2': 15}
        for _ in range(20):
            c['turn'] += 1
            kit.wait_tick(c, 'x', 'x-0', lambda t: 1, lambda t: kit.size_factor(size[t['id']], 7))
        small, big = c['tasks'][1]['patience'], c['tasks'][2]['patience']
        self.assertEqual(small, 80)
        self.assertEqual(big, 100 - int(20 / 1.4 + 1e-9))
        self.assertGreater(big, small)

    def test_gain_floor_calm_and_deferred(self):
        c = fake_c()
        c['tasks'][1]['patience'] = 99
        kit.wait_tick(c, 'x', 'x-0', lambda t: -1)  # a quiet day with a chatty guest: waiting feels shorter
        self.assertEqual(c['tasks'][1]['patience'], 100)
        c['tasks'][1]['patience'] = 25
        c['tasks'][2]['deferred'] = True
        kit.wait_tick(c, 'x', 'x-0', lambda t: 5)
        self.assertEqual(c['tasks'][1]['patience'], 25)
        self.assertEqual(c['tasks'][2]['patience'], 100)
        c['life']['mode'] = 'calm'
        c['tasks'][1]['patience'] = 90
        kit.wait_tick(c, 'x', 'x-0', lambda t: 5)
        self.assertEqual(c['tasks'][1]['patience'], 90)

    def test_bad_wait_data_is_refused(self):
        c = fake_c()
        kit.wait_validate(c)
        kit.worked(c, 'x-0')
        c['ext']['data']['wait']['carry']['x-1'] = 0.5
        kit.wait_validate(c)
        c['ext']['data']['wait']['carry']['x-1'] = 3
        with self.assertRaises(Exception):
            kit.wait_validate(c)


class CareerTests(unittest.TestCase):
    def setUp(self):
        self.old = kit.clock
        kit.clock = lambda: 5000.0

    def tearDown(self):
        kit.clock = self.old

    def journey(self, career):
        j = Journey(career)
        j.c['life']['mode'] = 'normal'
        for t in j.c['tasks']:
            t['patience'] = 100
        return j

    @staticmethod
    def beat(t):
        """One beat of waiting for this guest on a plain day (food_service personalities)."""
        kind = (t.get('guest') or {}).get('kind')
        return 1 + (2 if kind == 'rush' else 0) - (1 if kind in ('chatty', 'elder') else 0)

    def florist(self):
        j = self.journey('florist')
        for it in FL.ITEMS:
            room = 40 - kit.stock(j.c, it['id'])
            if room > 0:
                inventory.add_lot(j.c, it['id'], min(20, room), 1, 4, 'partner')
        j.act('ask')
        return j

    def test_florist_picking_one_order_halves_the_queue_drain(self):
        j = self.florist()
        tid = j.task['id']
        other = next(t['id'] for t in j.c['tasks'] if t['id'] != tid)
        factor = kit.size_factor(FL._units(j.get(other)), FL.SIZE_BASE)
        for _ in range(8):
            j.act('fl_pick', task=tid, item='rose_white')
        # Before 0.9.5: 8 taps = 8 beats (the engine's flat -1 each). Now the first tap starts the work at full
        # speed and the next seven are "busy" (half speed), slowed again by the waiting guest's own order size.
        beat = self.beat(j.get(other))
        lost = int((1 + 7 * kit.BUSY_RATE) * beat / factor + 1e-9) if beat > 0 else 0
        self.assertEqual(j.get(other)['patience'], 100 - lost)
        self.assertLess(lost, 8 * max(beat, 1))
        validate_state(j.state)

    def test_florist_takes_several_stems_in_one_tap(self):
        j = self.florist()
        tid = j.task['id']
        other = next(t['id'] for t in j.c['tasks'] if t['id'] != tid)
        turn = j.c['turn']
        r = j.act('fl_pick', task=tid, item='rose_white', n=5)
        self.assertIn('5 cành', r['message'])
        self.assertEqual(sum(1 for s in j.get(tid)['work']['stems'] if s['i'] == 'rose_white'), 5)
        self.assertEqual(j.c['turn'], turn + 1)  # one beat of the day, not five
        self.assertGreaterEqual(j.get(other)['patience'], 100 - self.beat(j.get(other)))
        j.act('fl_remove', task=tid, item='rose_white', n=3)
        self.assertEqual(len(j.get(tid)['work']['stems']), 2)
        self.assertEqual(len(j.c['ext']['data']['spare']), 3)  # uncut stems go back to the bucket
        with self.assertRaises(Exception):
            j.act('fl_pick', task=tid, item='rose_white', n=FL.MAX_PICK + 1)
        with self.assertRaises(Exception):
            j.act('fl_remove', task=tid, item='rose_white', n=3)  # only 2 on the bench
        validate_state(j.state)

    def test_restaurant_scoops_several_portions_in_one_tap(self):
        j = self.journey('restaurant')
        j.act('ask')
        tid = j.task['id']
        item, q = next(iter(RS._specs(j.task['needs'])[0]['toppings'].items()))
        room = 40 - kit.stock(j.c, item)
        if room > 0:
            inventory.add_lot(j.c, item, min(10, room), 1, 4, 'partner')
        j.act('rs_container', task=tid, kind='box' if j.task['needs']['takeaway'] else 'bowl')
        m0, turn = j.task['mistakes'], j.c['turn']
        j.act('rs_topping', task=tid, item=item, n=q)
        self.assertEqual(j.get(tid)['bowl']['toppings'][item], q)
        self.assertEqual(j.get(tid)['mistakes'], m0)
        self.assertEqual(j.c['turn'], turn + 1)
        j.act('rs_topping', task=tid, item=item, n=2)  # two more than asked: two mistakes, as two taps would be
        self.assertEqual(j.get(tid)['mistakes'], m0 + 2)
        validate_state(j.state)

    def test_repair_queue_waits_calmer_while_working_one_device(self):
        j = self.journey('repair')
        tid = j.task['id']
        other = next(t['id'] for t in j.c['tasks'] if t['id'] != tid)
        before = j.get(other)['patience']
        j.act('ask', task=tid)
        kit.worked(j.c, tid)
        c = j.c
        for _ in range(4):
            c['turn'] += 1
            kit.wait_tick(c, 'repair', tid, lambda t: 1, lambda t: kit.size_factor(RP._units(t), RP.SIZE_BASE))
            kit.worked(c, tid)
        self.assertEqual(j.get(other)['patience'], before - int(4 * kit.BUSY_RATE / kit.size_factor(RP._units(j.get(other)), RP.SIZE_BASE) + 1e-9))
        self.assertTrue(RP.SPEC.get('wait') and FL.SPEC.get('wait') and RS.SPEC.get('wait') and AO.SPEC.get('wait'))

    # ---- clothing: the fitting room and the queue
    def clothing_fit(self):
        j = self.journey('clothing')  # day 1 opens on a one-shirt fit, two more customers queue
        j.act('ask', task=j.task['id'])
        self.assertEqual((j.task['kind'], len(j.task['needs']['lines'])), ('fit', 1))
        self.assertIn(j.task['needs']['lines'][0]['item'], ('tee', 'shirt'))
        for t in j.c['tasks']:
            t['patience'] = 100
        return j

    def test_clothing_fitting_costs_less_while_working_the_customer(self):
        j = self.clothing_fit()
        tid, ln = j.task['id'], j.task['needs']['lines'][0]
        sizes = AO.SIZES[ln['item']]
        j.act('ao_pick', task=tid, item=ln['item'], size=ln['_size'], colour=ln['colour'])
        j.act('ao_pick', task=tid, item=ln['item'], size=sizes[(sizes.index(ln['_size']) + 1) % len(sizes)], colour=ln['colour'])
        j.act('ao_try', task=tid, index=0)  # right after picking: you are there with them
        self.assertEqual(j.get(tid)['patience'], 100 - AO.TRY_COST_BUSY)
        j.c['ext']['data']['wait']['turn'] -= 10  # stepped away to other work, then back to the curtain
        j.act('ao_try', task=tid, index=1)
        self.assertEqual(j.get(tid)['patience'], 100 - AO.TRY_COST_BUSY - AO.TRY_COST)
        self.assertLess(AO.TRY_COST_BUSY, AO.TRY_COST)
        validate_state(j.state)

    def test_clothing_queue_waits_calmer_while_picking(self):
        j = self.clothing_fit()
        tid, ln = j.task['id'], j.task['needs']['lines'][0]
        other = next(t['id'] for t in j.c['tasks'] if t['id'] != tid and t['career'] == 'clothing' and not t.get('deferred'))
        factor = kit.size_factor(AO._units(j.get(other)), AO.SIZE_BASE)
        for _ in range(4):
            j.act('ao_pick', task=tid, item=ln['item'], size=ln['_size'], colour=ln['colour'])
        # Before 0.9.5: 4 picks = 4 points. Now the first at full speed, the next three at half.
        self.assertEqual(j.get(other)['patience'], 100 - int((1 + 3 * kit.BUSY_RATE) / factor + 1e-9))
        validate_state(j.state)

    def test_clothing_order_lines_carry_a_short_size_clue(self):
        seen = set()
        for day in range(1, 30):
            for slot in range(12):
                t = AO.make_task(day, slot, 1)
                for ln in (t['needs'].get('lines') or []) if t['kind'] == 'fit' else []:
                    seen.add(ln['clue'])
                    self.assertTrue(ln['ask'] and len(ln['ask']) <= 40)
                    # Only a size the customer named themselves is on the card to check against.
                    self.assertEqual(ln['told'], ln['_size'] if ln['clue'] == 'label' else None)
                    if ln['clue'] == 'body':  # the numbers the customer said, never the size to work out
                        self.assertNotIn('size', ln['ask'])
                        for v in ln['ask'].replace('·', ' ').split():
                            if v.isdigit():
                                self.assertIn(v, ln['say'])
                    if ln['clue'] == 'brand':
                        self.assertNotIn(ln['_size'], ln['ask'].split()[-1])
        self.assertTrue({'label', 'body', 'waist'} <= seen)
        self.assertEqual(AO._units(dict(kind='outfit', needs=dict(occasion='beach'))), 3)
        occ = AO.content()['occasions']['beach']
        self.assertEqual(occ['need'], ['hat'])


if __name__ == '__main__':
    unittest.main()
