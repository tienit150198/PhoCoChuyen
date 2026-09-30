"""Tổ thu gom phường Mây (plugin career garbage): the start of the shift (gear used up from the
storeroom, the cart), a lane of bags (what shows from outside, opening, hazards into the red box,
wrapping glass, the right compartment, reminders), the collection time, the collection point and
the ve chai money, residents' complaints, surprises, determinism, save validation and old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game.careers import kit, PLUGINS
from game.content import make_task
from game.engine import GameError, migrate_state, new_state, public_state, validate_state

GB = PLUGINS.get('garbage')


class Base(unittest.TestCase):
    def setUp(self):
        if GB is None:
            raise unittest.SkipTest('garbage is filtered out by MNL_CAREERS')
        self.j = Journey('garbage')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def kind(self, kind, j=None):
        j = j or self.j
        return next(t for t in j.c['tasks'] if t['kind'] == kind and t['status'] not in ('completed', 'cancelled'))

    def settle_desk(self, j=None):
        j = j or self.j
        ev = j.c['ext']['data']['desk']['ev']
        if ev:
            j.act('rac_desk', option=kit.desk_script(GB.DESK, ev['script'])['default'])
        tb = j.c['ext']['data'].get('trouble')
        if tb and tb['ev']:
            j.act('rac_trouble', choice='photo' if tb['ev']['kind'] == 'vandal' else 'tidy')

    def start_shift(self, j=None, gear=None, cart=True):
        j = j or self.j
        self.settle_desk(j)
        t = self.kind('setup', j)
        for g in (t['needs']['gear'] if gear is None else gear):
            j.act('rac_gear', item=g)
        if cart:
            j.act('rac_cart')
        j.act('rac_open', task=t['id'])
        return j.get(t['id'])

    def on_shift(self, j):
        """A journey started on a given day and slot has no setup job: the crew is already out."""
        d = j.c['ext']['data']
        d.update(shift=True, cart_ok=True, gear=['gang_tay', 'khau_trang', 'ao', 'ung'])

    def at(self, pick):
        day, slot = next((d, s) for d in range(2, 200) for s in range(1, 6) if pick(GB.make_task(d, s, 1)))
        j = Journey('garbage', slot=slot, day=day)
        self.on_shift(j)
        return j

    def calm(self, j, tid):
        """Someone on the lane steps in (a 0.9.16 twist): answer the patient way."""
        t = j.get(tid)
        st = t.get('tw')
        if st and st['state'] == 'on':
            kind = t['twist']['kind']
            j.act({'sharp': 'rac_hurt', 'pile': 'rac_pile', 'grump': 'rac_grump'}[kind], task=tid,
                  choice={'sharp': 'clinic', 'pile': 'trips', 'grump': 'take'}[kind])

    def round(self, tid, j=None, careful=True, note=True):
        """Work a lane the careful way (or load every bag by its colour without looking)."""
        j = j or self.j
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        j.act('rac_go', task=tid)
        t = j.get(tid)
        if t['late']:
            j.act('rac_sweep', task=tid)
            t = j.get(tid)
        self.calm(j, tid)
        for si, st in enumerate(t['needs']['stops']):
            for b in st['bags']:
                if careful and (not GB._sorted_ok(b) or GB._hazards(b) or GB._glass(b)):
                    j.act('rac_peek', task=tid, bag=b['id'])
                    for i in GB._hazards(b):
                        j.act('rac_pull', task=tid, bag=b['id'], item=i)
                    if GB._glass(b):
                        j.act('rac_wrap', task=tid, bag=b['id'])
                    if note and si not in j.get(tid)['noted'] and not GB._sorted_ok(b):
                        j.act('rac_note', task=tid, stop=si)
                bin_ = GB.bag_bin(b) if careful else GB.COLOR_BIN[b['color']]
                if j.c['ext']['data']['cart'][bin_]['n'] >= GB.CART[bin_]:
                    j.act('rac_dump')
                j.act('rac_load', task=tid, bag=b['id'], bin=bin_)
                self.calm(j, tid)
            if si < len(t['needs']['stops']) - 1:
                j.act('rac_next', task=tid)
                self.calm(j, tid)
        r = j.act('rac_finish', task=tid)
        if j.get(tid)['status'] != 'completed':
            self.calm(j, tid)
            r = j.act('rac_finish', task=tid)
        return r


class Spec(Base):
    def test_spec_shape(self):
        s = GB.SPEC
        self.assertEqual((s['id'], s['prefix']), ('garbage', 'rac_'))
        self.assertTrue(6 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertEqual(len(s['staff']), 4)
        self.assertEqual(len(s['stories']), 3)
        self.assertTrue(5 <= len(s['situations']) <= 8)
        for x in s['situations']:
            for opt in x['options']:
                self.assertTrue(2 <= len(opt['perspectives']) <= 3, opt['id'])
        for k in s['no_tick'] + s['free_actions'] + tuple(GB.ACTIONS):
            self.assertTrue(k.startswith('rac_'), k)
        for x in GB.CASES:
            self.assertTrue(any(o['q'] == 'good' for o in x['options']), x['id'])
            facts = {f['id'] for f in x['facts']}
            for o in x['options']:
                self.assertTrue(set(o.get('requires', ())) <= facts, o['id'])

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'mô phỏng', 'giả lập', 'nhiệm vụ', 'anh/chị')
        blob = json.dumps([GB.CASES, GB.DESK, GB.SITUATIONS, GB.REG_STORY, GB.INTRO, GB.SPEC['meta'], GB.CLUE], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_an_evening_shift(self):
        from game import inventory
        self.assertEqual(inventory.hours('garbage'), (17 * 60, 23 * 60))


class Determinism(Base):
    def test_tasks_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 20):
            for slot in range(0, 8):
                a, b = GB.make_task(day, slot, 1), GB.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                self.assertEqual(make_task('garbage', day, slot, 1)['id'], f'garbage-{day:04d}-{slot:02d}')

    def test_first_evening_is_gentle(self):
        self.assertEqual([GB.make_task(1, s, 1)['kind'] for s in range(3)], ['setup', 'route', 'route'])
        r = GB.make_task(1, 1, 1)['needs']
        bags = [b for st in r['stops'] for b in st['bags']]
        self.assertEqual(len(r['stops']), 3)
        self.assertEqual(sum(not GB._sorted_ok(b) for b in bags), 1)
        self.assertFalse(any(GB._hazards(b) for b in bags))

    def test_later_lanes_bring_hazards_and_complaints(self):
        kinds, hazards, glass = set(), 0, 0
        for d in range(2, 30):
            for s in range(1, 5):
                t = GB.make_task(d, s, 1)
                kinds.add(t['kind'])
                if t['kind'] == 'route':
                    for st in t['needs']['stops']:
                        for b in st['bags']:
                            hazards += bool(GB._hazards(b))
                            glass += GB._glass(b)
        self.assertIn('complaint', kinds)
        self.assertGreater(hazards, 5)
        self.assertGreater(glass, 2)

    def test_where_a_bag_belongs(self):
        self.assertEqual(GB.bag_bin(dict(items=['vo_trai', 'rau_ua'])), 'huu_co')
        self.assertEqual(GB.bag_bin(dict(items=['lon', 'giay'])), 'tai_che')
        self.assertEqual(GB.bag_bin(dict(items=['giay', 'com_thua'])), 'con_lai')   # food spoils the recyclables
        self.assertEqual(GB.bag_bin(dict(items=['vo_trai', 'pin'])), 'huu_co')       # once the battery is out


class Shift(Base):
    def test_start_right_uses_gloves_and_masks(self):
        j = self.j
        gloves, masks = kit.stock(j.c, 'gang_tay'), kit.stock(j.c, 'khau_trang')
        t = self.start_shift()
        self.assertFalse(t.get('slips'))
        self.assertEqual(kit.stock(j.c, 'gang_tay'), gloves - 1)
        self.assertEqual(kit.stock(j.c, 'khau_trang'), masks - 1)
        with self.assertRaises(GameError):
            j.act('rac_gear', item='gang_tay')      # a used pair is not taken off and worn again

    def test_start_without_gear(self):
        t = self.start_shift(gear=[], cart=False)
        codes = {x['code'] for x in t['slips']}
        self.assertTrue({'no_gloves', 'no_vest', 'cart'} <= codes, codes)

    def test_no_gloves_left_in_the_storeroom(self):
        j = self.j
        n = kit.stock(j.c, 'gang_tay')
        kit.take(j.c, 'gang_tay', n)
        with self.assertRaises(GameError):
            j.act('rac_gear', item='gang_tay')

    def test_cannot_round_before_the_shift(self):
        t = self.kind('route')
        self.j.act('ask', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('rac_go', task=t['id'])


class Round(Base):
    def test_a_careful_round_pays_and_reads_well(self):
        j = self.j
        self.start_shift()
        t = self.kind('route')
        money = j.c['money']
        r = self.round(t['id'])
        t = j.get(t['id'])
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'), r)
        self.assertEqual(j.c['money'] - money, GB.ROUTE_PAY + GB.STOP_PAY * len(t['needs']['stops']))
        self.assertEqual(t['noted'], [1])
        validate_state(json.loads(json.dumps(j.state)))

    def test_loading_by_colour_without_looking(self):
        j = self.j
        self.start_shift()
        t = self.kind('route')
        self.round(t['id'], careful=False, note=False)
        self.assertIn('bin', {x['code'] for x in j.get(t['id'])['slips']})
        self.assertEqual(self.d['today']['wrong'], 1)

    def test_what_a_bag_shows_before_and_after_opening(self):
        j = self.j
        self.start_shift()
        t = self.kind('route')
        j.act('ask', task=t['id'])
        j.act('rac_go', task=t['id'])
        view = next(x for x in public_state(j.state)['careers']['garbage']['tasks'] if x['id'] == t['id'])
        bag = view['needs']['stops'][0]['bags'][0]
        self.assertIsNone(bag['items'])
        self.assertTrue(bag['clue'])
        j.act('rac_peek', task=t['id'], bag=bag['id'])
        view = next(x for x in public_state(j.state)['careers']['garbage']['tasks'] if x['id'] == t['id'])
        self.assertTrue(view['needs']['stops'][0]['bags'][0]['items'])

    def test_a_needle_with_bare_hands_is_a_safety_slip(self):
        j = self.at(lambda t: t['kind'] == 'route' and any('kim_tiem' in b['items'] for b in t['needs']['stops'][0]['bags']))
        j.c['ext']['data']['gear'] = ['ao']
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('rac_go', task=tid)
        b = next(b for b in j.get(tid)['needs']['stops'][0]['bags'] if 'kim_tiem' in b['items'])
        j.act('rac_peek', task=tid, bag=b['id'])
        r = j.act('rac_pull', task=tid, bag=b['id'], item='kim_tiem')
        self.assertFalse(r['correct'])
        t = j.get(tid)
        self.assertTrue(t['hurt'])
        self.assertTrue(any(x['safety'] for x in t['slips']))

    def test_a_hazard_left_in_the_bag(self):
        j = self.at(lambda t: t['kind'] == 'route' and any(GB._hazards(b) for st in t['needs']['stops'] for b in st['bags']))
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('rac_go', task=tid)
        t = j.get(tid)
        for si, st in enumerate(t['needs']['stops']):
            for b in st['bags']:
                if j.c['ext']['data']['cart'][GB.bag_bin(b)]['n'] >= GB.CART[GB.bag_bin(b)]:
                    j.act('rac_dump')
                if GB._glass(b):
                    j.act('rac_peek', task=tid, bag=b['id'])
                    j.act('rac_wrap', task=tid, bag=b['id'])
                j.act('rac_load', task=tid, bag=b['id'], bin=GB.bag_bin(b))
            if si < len(t['needs']['stops']) - 1:
                j.act('rac_next', task=tid)
        j.act('rac_finish', task=tid)
        self.assertIn('hazard', {x['code'] for x in j.get(tid)['slips']})

    def test_glass_without_gloves_cuts(self):
        j = self.at(lambda t: t['kind'] == 'route' and any(GB._glass(b) for b in t['needs']['stops'][0]['bags']))
        j.c['ext']['data']['gear'] = ['ao']
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('rac_go', task=tid)
        b = next(b for b in j.get(tid)['needs']['stops'][0]['bags'] if GB._glass(b))
        for i in GB._hazards(b):
            j.act('rac_peek', task=tid, bag=b['id'])
            j.act('rac_pull', task=tid, bag=b['id'], item=i)
        r = j.act('rac_load', task=tid, bag=b['id'], bin=GB.bag_bin(b))
        self.assertFalse(r['correct'])
        self.assertIn('cut', {x['code'] for x in j.get(tid)['slips']})

    def test_missed_bags_and_nagging_the_wrong_house(self):
        j = self.j
        self.start_shift()
        t = self.kind('route')
        j.act('ask', task=t['id'])
        j.act('rac_go', task=t['id'])
        j.act('rac_note', task=t['id'], stop=0)
        for _ in range(len(t['needs']['stops']) - 1):
            j.act('rac_next', task=t['id'])
        j.act('rac_finish', task=t['id'])
        codes = {x['code'] for x in j.get(t['id'])['slips']}
        self.assertTrue({'missed', 'nag'} <= codes, codes)

    def test_late_means_sweeping_first(self):
        j = self.j
        self.start_shift()
        t = self.kind('route')
        j.act('ask', task=t['id'])
        for _ in range(8):      # the clock runs 20 minutes a turn from 17:40: past 19:30
            j.act('advance')
        r = j.act('rac_go', task=t['id'])
        self.assertTrue(j.get(t['id'])['late'], r)
        b = t['needs']['stops'][0]['bags'][0]
        with self.assertRaises(GameError):
            j.act('rac_load', task=t['id'], bag=b['id'], bin='con_lai')
        j.act('rac_sweep', task=t['id'])
        j.act('rac_load', task=t['id'], bag=b['id'], bin=GB.bag_bin(b))

    def test_a_full_compartment_must_be_emptied(self):
        j = self.j
        self.start_shift()
        self.d['cart']['con_lai'] = dict(n=GB.CART['con_lai'], bad=0)
        t = self.kind('route')
        j.act('ask', task=t['id'])
        j.act('rac_go', task=t['id'])
        b = t['needs']['stops'][0]['bags'][0]
        with self.assertRaises(GameError):
            j.act('rac_load', task=t['id'], bag=b['id'], bin='con_lai')


class Point(Base):
    def test_clean_recyclables_pay_dirty_ones_do_not(self):
        j = self.j
        self.start_shift()
        self.d['cart'].update(tai_che=dict(n=5, bad=2), huu_co=dict(n=3, bad=0))
        self.d['haz'] = ['pin']
        money = j.c['money']
        r = j.act('rac_dump')
        self.assertEqual(j.c['money'] - money, 3 * GB.VE_CHAI)
        self.assertIn('Cô Tám lắc đầu', r['message'])
        self.assertEqual(GB.cart_load(self.d), 0)
        self.assertEqual(self.d['haz'], [])
        with self.assertRaises(GameError):
            j.act('rac_dump')

    def test_rubbish_left_on_the_cart_at_closing(self):
        j = self.j
        self.start_shift()
        self.d['cart']['con_lai'] = dict(n=2, bad=0)
        s = j.act('end_day')['summary']['career']
        self.assertEqual(s['overnight'], 2)
        self.assertEqual(GB.cart_load(self.d), 0)


class Complaints(Base):
    def test_every_answer(self):
        for x in GB.CASES:
            for o in x['options']:
                j = self.at(lambda t, cid=x['id']: t['kind'] == 'complaint' and t['needs']['case'] == cid)
                tid = j.task['id']
                j.act('ask', task=tid)
                if o.get('requires'):
                    with self.assertRaises(GameError):
                        j.act('rac_reply', task=tid, option=o['id'])
                for f in x['facts']:
                    j.act('rac_read', task=tid, fact=f['id'])
                money = j.c['money']
                j.act('rac_reply', task=tid, option=o['id'])
                t = j.get(tid)
                self.assertEqual(t['status'], 'completed')
                codes = {s['code'] for s in t.get('slips', [])}
                self.assertEqual(not codes, o['q'] == 'good', (x['id'], o['id'], codes))
                if o['q'] == 'good':
                    self.assertEqual(j.c['money'] - money, GB.CASE_PAY)
                validate_state(json.loads(json.dumps(j.state)))


class Days(Base):
    def test_a_week_of_play_keeps_the_save_valid(self):
        j = self.j
        for day in range(1, 8):
            self.assertEqual(j.c['day'], day)
            for g in GB.USED:
                if kit.stock(j.c, g) < 2:
                    kit.add_lot(j.c, g, 6, 1, 90, 'test')
            if kit.stock(j.c, 'bao') < 4:
                kit.add_lot(j.c, 'bao', 8, 1, 90, 'test')
            self.start_shift()
            for t in [x for x in j.c['tasks'] if x['kind'] != 'setup' and x['status'] not in ('completed', 'cancelled')]:
                self.settle_desk()
                if t['kind'] == 'route':
                    self.round(t['id'])
                else:
                    x = GB.CASE[t['needs']['case']]
                    j.act('ask', task=t['id'])
                    for f in x['facts']:
                        j.act('rac_read', task=t['id'], fact=f['id'])
                    j.act('rac_reply', task=t['id'], option=next(o['id'] for o in x['options'] if o['q'] == 'good'))
            self.settle_desk()
            if GB.cart_load(self.d) or self.d['haz']:
                j.act('rac_dump')
            validate_state(json.loads(json.dumps(j.state)))
            self.settle_desk()
            j.act('end_day')
            j.act('start_day')
            self.assertEqual(j.task['kind'], 'setup')
        self.assertGreater(self.d['stats']['routes'], 7)


class Surprises(Base):
    def test_every_surprise_option_is_playable(self):
        for x in GB.DESK:
            for o in x['options']:
                j = Journey('garbage')
                self.start_shift(j)
                j.c['money'] += 100
                j.c['ops']['finance']['opening_balance'] += 100
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('rac_dump')
                self.assertTrue(j.act('rac_desk', option=o['id'])['message'], (x['id'], o['id']))
                validate_state(json.loads(json.dumps(j.state)))

    def test_situations_are_playable(self):
        j = self.j
        for x in GB.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)


class Saves(Base):
    def test_validate_rejects_broken_data(self):
        for path, value in ((('cart', 'huu_co', 'n'), 99), (('gear',), ['cape']), (('haz',), ['diamond']), (('shift',), 1)):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['garbage']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_validate_rejects_a_forged_task(self):
        for key, value in (('loaded', {'b99': 'huu_co'}), ('at', 9), ('stage', 'free')):
            s = copy.deepcopy(self.j.state)
            t = next(x for x in s['careers']['garbage']['tasks'] if x['kind'] == 'route')
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)
        s = copy.deepcopy(self.j.state)
        t = next(x for x in s['careers']['garbage']['tasks'] if x['kind'] == 'route')
        t['needs']['stops'][0]['bags'][0]['items'] = ['vo_trai']
        with self.assertRaises(GameError):
            validate_state(s)

    def test_old_save_without_the_crew_loads(self):
        s = new_state()
        s['careers'].pop('garbage', None)
        s = migrate_state(s)
        validate_state(s)
        self.assertIn('garbage', s['careers'])

    def test_public_view_is_json(self):
        self.start_shift()
        view = public_state(self.j.state)['careers']['garbage']
        json.dumps(view)
        for k in ('cart', 'cap', 'haz', 'gear', 'mod', 'desk', 'clock'):
            self.assertIn(k, view['data'])
        self.assertEqual(view['data']['clock'], 17 * 60 + 40)


if __name__ == '__main__':
    unittest.main()
