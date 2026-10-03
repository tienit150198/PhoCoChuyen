"""Cơm tấm Dì Bảy (plugin career com): the morning (two pots and their water line, the bowl of nước mắm
tasted and fixed, the charcoal, the trays), the grill (sườn turned once, raw / good / charred / burnt),
plates and boxes (rice by the ladle from the right pot, dishes from the case, the rack and the pan,
mỡ hành, nước mắm, soy sauce for vegetarians, soup), cash through the shared till, the evening waste,
surprises, determinism, save validation and old saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game.careers import kit, till, PLUGINS
from game.content import CAREERS
from game.content import initial_career, make_task
from game.engine import GameError, migrate_state, public_state, validate_state

KM = PLUGINS.get('com')


class Clock:
    def __init__(self):
        self.t = 9000.0

    def __call__(self):
        return self.t


def find(kind=None, title=None, days=range(1, 40), slots=range(1, 5)):
    for day in days:
        for slot in slots:
            t = make_task('com', day, slot, 1)
            if (kind is None or t['kind'] == kind) and (title is None or t['title'] == title):
                return day, slot
    raise AssertionError(f'no {kind} {title}')


class Base(unittest.TestCase):
    def setUp(self):
        if KM is None:
            raise unittest.SkipTest('com is filtered out by MNL_CAREERS')
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, day, slot, opened=True):
        """A customer on its own, the stall already set up (two good pots, a good bowl, fire lit, full trays)."""
        self.j = Journey('com', slot=slot, day=day)
        d = KM._data(self.j.c)
        d['intro'] = True
        d['shop']['open'] = opened
        d['mam'] = dict(q='ok', tasted=True)
        d['grill'] = dict(lit=True, b=None)
        for r in KM.RICE:
            d['pots'][r] = dict(va=KM.POT_VA, q='ok', at=0.0, c=4)
        for k in KM.TRAYS:
            d['trays'][k] = dict(n=8, c=8)
        for x in KM.ITEMS:
            kit.add_lot(self.j.c, x['id'], 6, x['cost'], 30, 'test')
        return self.j.task

    def settle_desk(self):
        ev = self.d['desk']['ev']
        if ev:
            self.j.act('com_desk', option=kit.desk_script(KM.DESK, ev['script'])['default'])

    def grill(self, n=2, side1=12, side2=12):
        self.j.act('com_grill', n=n)
        self.clock.t += side1
        self.j.act('com_flip')
        self.clock.t += side2
        return self.j.act('com_lift')

    def make(self, tid, mam=None):
        """Build exactly what was ordered, the right way."""
        t = self.j.get(tid)
        box = t['needs']['togo']
        for ln in t['needs']['lines']:
            self.j.act('com_plate', task=tid, v='hop' if box else 'dia')
            for _ in range(ln['va']):
                self.j.act('com_rice', task=tid, r=ln['r'])
            for k in ln['it']:
                if k.startswith('trung_'):
                    self.j.act('com_egg', task=tid, how=k[6:])
                elif k == 'suon':
                    if not any(pc['q'] == 'ok' for pc in self.d['rack']):
                        self.grill(4)
                    i = next(i for i, pc in enumerate(self.d['rack']) if pc['q'] == 'ok')
                    self.j.act('com_pick', task=tid, item='suon', i=i)
                else:
                    self.j.act('com_pick', task=tid, item=k)
            self.j.act('com_mo', task=tid, on=ln['mo'] and not ln['chay'])
            want = 'tuong' if ln['mam'] == 'tuong' else 'rieng' if box else ln['mam']
            self.j.act('com_mam', task=tid, m=mam or want)
            self.j.act('com_canh', task=tid, on=ln['canh'])

    def serve_pay(self, tid):
        r = self.j.act('com_serve', task=tid)
        t = self.j.get(tid)
        self.assertEqual(t['stage'], 'pay', r)
        rec = t['cash']
        return self.j.act('com_pay', task=tid, change=till.greedy(max(0, till.due(rec))))

    def codes(self, tid):
        return {x['code'] for x in self.j.get(tid).get('slips') or []}


class Spec(Base):
    def test_spec_shape(self):
        s = KM.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('com', 'com_', 'food'))
        self.assertTrue(5 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertIn('com', jr.CH_UNLOCKS[3])
        self.assertIn('com', CAREERS)
        for name in KM.ACTIONS:
            self.assertTrue(name.startswith('com_'))
        for name in (*KM.NO_TICK, *KM.PHYSICAL, *KM.FREE):
            self.assertTrue(name in KM.ACTIONS or name in ('com_intro', 'com_desk'), name)

    def test_tasks_are_deterministic_and_cover_every_kind(self):
        kinds = set()
        for day in range(1, 25):
            for slot in range(0, 5):
                a, b = make_task('com', day, slot, 3), make_task('com', day, slot, 3)
                self.assertEqual(a, b)
                kinds.add(a['kind'])
        self.assertEqual(kinds, set(KM.KINDS))

    def test_scripts_are_well_formed(self):
        for x in KM.DESK:
            self.assertIn(x['default'], {o['id'] for o in x['options']})
        ids = [s['id'] for s in KM.SITUATIONS]
        self.assertEqual(len(ids), len(set(ids)))
        for o in KM.ORDERS:
            for ln in o[4]:
                KM._vline(ln)

    def test_prices_stay_in_line_with_the_street_food_stalls(self):
        # A plate of cơm tấm sườn is about a cone and a half of ice cream; the dearest order of the day
        # (sườn bì chả, a box) stays under twenty.
        plate = lambda ln, v='dia': KM.plate_price({'life': {'prices': {}}}, dict(r=ln['r'], va=ln['va'], it=ln['it'], v=v))
        self.assertEqual(plate(KM._l('tam', 2, ['suon'])), 10)
        self.assertLess(plate(KM._h('tam', 3, ['suon', 'bi', 'cha', 'trung_dao']), 'hop'), 20)


class Morning(Base):
    def test_first_morning_teaches_water_taste_fire_and_trays(self):
        self.j = Journey('com')
        setup = self.j.task
        self.assertEqual(setup['kind'], 'setup')
        self.assertEqual(self.d['mam']['q'], 'man')
        self.j.act('com_intro')
        self.j.act('com_cook', r='tam', water='lung')
        self.j.act('com_cook', r='trang', water='mot')
        self.assertIn('mặn', self.j.act('com_taste')['message'])
        self.j.act('com_fix', add='nuoc')
        self.assertEqual(self.d['mam']['q'], 'ok')
        self.j.act('com_fire')
        for k in ('bi', 'cha', 'rau'):
            self.j.act('com_tray', item=k)
        r = self.j.act('com_open', task=setup['id'])
        self.assertTrue(r.get('celebrate'))
        self.assertFalse(self.j.get(setup['id']).get('slips'))
        self.assertTrue(self.d['shop']['open'])

    def test_skipping_the_morning_is_named(self):
        self.j = Journey('com')
        self.j.act('com_intro')
        setup = self.j.task
        self.j.act('com_open', task=setup['id'])
        self.assertEqual(self.codes(setup['id']), {'no_rice', 'no_taste', 'no_fire', 'no_tray'})

    def test_wrong_water_spoils_the_pot_and_every_plate_from_it(self):
        self.j = Journey('com')
        self.j.act('com_intro')
        self.j.act('com_cook', r='tam', water='mot')
        self.assertEqual(self.d['pots']['tam']['q'], 'nhao')
        self.j.act('com_cook', r='trang', water='lung')
        self.assertEqual(self.d['pots']['trang']['q'], 'suong')
        with self.assertRaises(GameError):
            self.j.act('com_cook', r='tam', water='lung')        # a pot with rice in it is not cooked again
        self.j.act('com_open', task=self.j.task['id'])
        self.assertIn('rice_water', self.codes(self.j.task['id']) if self.j.task['kind'] == 'setup' else
                      self.codes(next(t['id'] for t in self.j.c['tasks'] if t['kind'] == 'setup')))

    def test_a_spoonful_into_a_good_bowl_spoils_it(self):
        self.j = Journey('com')
        self.d['mam'] = dict(q='ok', tasted=False)
        with self.assertRaises(GameError):
            self.j.act('com_fix', add='mam')                    # taste first
        self.j.act('com_taste')
        self.j.act('com_fix', add='mam')
        self.assertEqual(self.d['mam']['q'], 'man')
        self.j.act('com_fix', add='chanh')                       # the wrong fix: still salty
        self.assertEqual(self.d['mam']['q'], 'man')
        self.j.act('com_fix', add='nuoc')
        self.assertEqual(self.d['mam']['q'], 'ok')

    def test_rice_is_not_ready_before_it_cooks(self):
        day, slot = find('serve', 'Chú Bình ăn sáng')
        t = self.at(day, slot)
        self.d['pots']['tam'] = dict(va=0, q='ok', at=0.0, c=0)
        self.j.act('com_cook', r='tam', water='lung')
        self.j.act('ask', task=t['id'])
        self.j.act('com_plate', task=t['id'], v='dia')
        with self.assertRaises(GameError):
            self.j.act('com_rice', task=t['id'], r='tam')
        self.clock.t += KM.COOK_S
        self.j.act('com_rice', task=t['id'], r='tam')


class Grill(Base):
    def test_sides_decide_the_piece(self):
        self.assertEqual(KM.grill_q(12, 12), 'ok')
        self.assertEqual(KM.grill_q(4, 12), 'song')
        self.assertEqual(KM.grill_q(12, 20), 'xem')
        self.assertEqual(KM.grill_q(30, 12), 'khet')
        day, slot = find('serve', 'Chú Bình ăn sáng')
        self.at(day, slot)
        self.grill(2, 12, 12)
        self.assertEqual([pc['q'] for pc in self.d['rack']], ['ok', 'ok'])
        self.grill(1, 3, 12)
        self.assertEqual(self.d['rack'][-1]['q'], 'song')
        self.j.act('com_grill', n=1)
        self.clock.t += 12
        self.j.act('com_lift')                                   # never turned: one side raw
        self.assertEqual(self.d['rack'][-1]['q'], 'song')

    def test_a_stop_tap_counts_when_the_finger_came_down(self):
        day, slot = find('serve', 'Chú Bình ăn sáng')
        self.at(day, slot)
        self.j.act('com_grill', n=1)
        start = self.d['grill']['b']['start']
        self.clock.t += 13
        self.j.act('com_flip', tap_at=start + 11)
        self.assertAlmostEqual(self.d['grill']['b']['flip'] - start, 11, places=2)

    def test_raw_pork_on_a_plate_is_a_safety_mistake(self):
        day, slot = find('serve', 'Chú Bình ăn sáng')
        t = self.at(day, slot)
        self.grill(1, 3, 3)
        self.j.act('ask', task=t['id'])
        self.j.act('com_plate', task=t['id'], v='dia')
        self.j.act('com_rice', task=t['id'], r='tam')
        self.j.act('com_rice', task=t['id'], r='tam')
        self.j.act('com_pick', task=t['id'], item='suon', i=0)
        self.j.act('com_mo', task=t['id'], on=True)
        self.j.act('com_mam', task=t['id'], m='ruoi')
        self.j.act('com_canh', task=t['id'], on=True)
        self.j.act('com_serve', task=t['id'])
        slip = next(x for x in self.j.get(t['id'])['slips'] if x['code'] == 'raw')
        self.assertTrue(slip['safety'])
        self.assertEqual(slip['sev'], 3)

    def test_tossing_a_burnt_piece_books_waste(self):
        day, slot = find('serve', 'Chú Bình ăn sáng')
        self.at(day, slot)
        self.grill(1, 30, 30)
        self.assertEqual(self.d['rack'][0]['q'], 'khet')
        self.j.act('com_toss', i=0)
        self.assertEqual(self.d['rack'], [])
        self.assertEqual(self.j.c['life']['waste'][-1]['item'], 'suon')


class Serving(Base):
    def test_a_clean_plate_for_chu_binh(self):
        day, slot = find('serve', 'Chú Bình ăn sáng')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        money = self.j.c['money']
        r = self.serve_pay(t['id'])
        t = self.j.get(t['id'])
        self.assertEqual(t['status'], 'completed', r)
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['cash']['price'], KM.PRICES['com_tam'] + KM.PRICES['suon'])
        self.assertGreaterEqual(self.j.c['money'], money + t['cash']['price'])
        self.assertEqual(self.d['regulars']['1']['visits'], 1)

    def test_take_away_boxes_with_the_sauce_on_the_side(self):
        day, slot = find('serve', 'Chị Ngân mua hai hộp')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        boxes = KM.kit.stock(self.j.c, 'hop')
        self.make(t['id'])
        self.assertEqual(KM.kit.stock(self.j.c, 'hop'), boxes - 2)
        self.serve_pay(t['id'])
        self.assertFalse(self.j.get(t['id']).get('slips'))

    def test_sauce_poured_into_a_box_goes_soggy(self):
        day, slot = find('serve', 'Chị Ngân mua hai hộp')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.make(t['id'], mam='ruoi')
        self.j.act('com_serve', task=t['id'])
        self.assertTrue(any(c.startswith('soggy_') for c in self.codes(t['id'])))

    def test_a_dish_for_here_in_a_box_and_the_wrong_pot(self):
        day, slot = find('serve', 'Chú Bình ăn sáng')
        t = self.at(day, slot)
        self.grill(2)
        self.j.act('ask', task=t['id'])
        self.j.act('com_plate', task=t['id'], v='hop')
        self.j.act('com_rice', task=t['id'], r='trang')
        self.j.act('com_rice', task=t['id'], r='trang')
        self.j.act('com_pick', task=t['id'], item='suon', i=0)
        self.j.act('com_mo', task=t['id'], on=True)
        self.j.act('com_mam', task=t['id'], m='ruoi')
        self.j.act('com_canh', task=t['id'], on=True)
        self.j.act('com_serve', task=t['id'])
        codes = self.codes(t['id'])
        self.assertIn('vessel', codes)
        self.assertIn('pot_0', codes)

    def test_short_ladles_for_anh_manh_are_a_clear_mistake(self):
        day, slot = find('serve', 'Anh Mạnh ăn khỏe')
        t = self.at(day, slot)
        self.grill(2)
        self.j.act('ask', task=t['id'])
        self.j.act('com_plate', task=t['id'], v='dia')
        for _ in range(2):
            self.j.act('com_rice', task=t['id'], r='tam')
        self.j.act('com_pick', task=t['id'], item='suon', i=0)
        self.j.act('com_egg', task=t['id'], how='chin')
        self.j.act('com_mo', task=t['id'], on=True)
        self.j.act('com_mam', task=t['id'], m='ruoi')
        self.j.act('com_canh', task=t['id'], on=True)
        self.j.act('com_serve', task=t['id'])
        slip = next(x for x in self.j.get(t['id'])['slips'] if x['code'] == 'less_0')
        self.assertEqual(slip['sev'], 2)

    def test_lard_for_a_vegetarian_is_named(self):
        day, slot = find('serve', 'Bà Sương ăn chay')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.j.act('com_mo', task=t['id'], on=True)
        self.j.act('com_serve', task=t['id'])
        self.assertIn('chay', self.codes(t['id']))

    def test_a_clean_vegetarian_plate(self):
        day, slot = find('serve', 'Bà Sương ăn chay')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.serve_pay(t['id'])
        self.assertFalse(self.j.get(t['id']).get('slips'))

    def test_the_office_order_of_four_boxes(self):
        day, slot = find('office')
        t = self.at(day, slot)
        self.assertEqual(len(t['needs']['lines']), 4)
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        r = self.serve_pay(t['id'])
        self.assertFalse(self.j.get(t['id']).get('slips'), r)

    def test_wrong_dishes_are_missing_and_a_redo_takes_the_plate_off(self):
        day, slot = find('serve', 'Nhi ăn cơm phần')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.j.act('com_plate', task=t['id'], v='dia')
        self.j.act('com_rice', task=t['id'], r='trang')
        self.j.act('com_pick', task=t['id'], item='ca_kho')
        cost = self.j.get(t['id'])['cost']
        self.assertGreater(cost, 0)
        self.j.act('com_drop', task=t['id'])
        self.assertEqual(self.j.get(t['id'])['plates'], [])
        self.assertEqual(self.j.get(t['id'])['cost'], 0)
        self.j.act('com_plate', task=t['id'], v='dia')
        self.j.act('com_rice', task=t['id'], r='trang')
        self.j.act('com_pick', task=t['id'], item='ca_kho')
        self.j.act('com_mam', task=t['id'], m='ruoi')
        self.j.act('com_serve', task=t['id'])
        self.assertIn('missing', self.codes(t['id']))

    def test_empty_trays_refuse_and_declining_is_honest(self):
        day, slot = find('serve', 'Nhi ăn cơm phần')
        t = self.at(day, slot)
        self.d['trays']['thit_kho'] = dict(n=0, c=0)
        self.j.act('ask', task=t['id'])
        self.j.act('com_plate', task=t['id'], v='dia')
        with self.assertRaises(GameError):
            self.j.act('com_pick', task=t['id'], item='thit_kho')
        self.j.act('com_decline', task=t['id'])
        t = self.j.get(t['id'])
        self.assertEqual((t['status'], t['choice']), ('completed', 'decline'))

    def test_steps_need_an_open_stall_and_a_known_order(self):
        day, slot = find('serve', 'Chú Bình ăn sáng')
        t = self.at(day, slot, opened=False)
        self.j.act('ask', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('com_plate', task=t['id'], v='dia')
        self.d['shop']['open'] = True
        t2 = self.at(day, slot)
        with self.assertRaises(GameError):
            self.j.act('com_plate', task=t2['id'], v='dia')       # not asked yet

    def test_short_change_is_caught_by_the_till(self):
        day, slot = find('serve', 'Chú Bình ăn sáng')
        t = self.at(day, slot)
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.j.act('com_serve', task=t['id'])
        rec = self.j.get(t['id'])['cash']
        due = till.due(rec)
        if due <= 0:
            self.skipTest('exact money this time')
        self.j.act('com_pay', task=t['id'], change=[])
        t = self.j.get(t['id'])
        self.assertTrue(t['status'] == 'completed' and t['cash']['outcome'] == 'missed' or t['cash']['asked'])


class Days(Base):
    def full_day(self):
        self.settle_desk()
        self.j.act('com_intro')
        setup = self.j.task
        self.j.act('com_cook', r='tam', water='lung')
        self.j.act('com_cook', r='trang', water='mot')
        self.j.act('com_taste')
        q = self.d['mam']['q']
        if q != 'ok':
            self.j.act('com_fix', add={'man': 'nuoc', 'lat': 'mam', 'ngot': 'chanh', 'chua': 'duong'}[q])
        self.j.act('com_fire')
        for k in KM.TRAYS:
            if kit.stock(self.j.c, k):
                self.j.act('com_tray', item=k)
        self.j.act('com_open', task=setup['id'])
        self.clock.t += KM.COOK_S
        self.settle_desk()
        served = 0
        for _ in range(8):
            self.settle_desk()
            t = next((t for t in self.j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred') and t['day'] == self.j.c['day']), None)
            if t is None:
                break
            self.j.act('ask', task=t['id'])
            try:
                self.make(t['id'])
            except GameError:
                self.j.act('com_decline', task=t['id'])
                continue
            self.serve_pay(t['id'])
            served += 1
        self.settle_desk()
        return served

    def test_ten_days_stay_valid(self):
        self.j = Journey('com')
        for x in KM.ITEMS:
            kit.add_lot(self.j.c, x['id'], 30, x['cost'], 40, 'test')
        for day in range(1, 11):
            self.assertGreaterEqual(self.full_day(), 1, day)
            validate_state(self.j.state)
            json.dumps(public_state(self.j.state))
            r = self.j.act('end_day', carry_event=True)
            car = r['summary']['career']
            self.assertTrue(car['lines'][0].startswith('🍚'))
            self.assertIn('tomorrow', car)
            self.assertEqual(self.d['rack'], [])                 # cooked food does not keep
            self.assertTrue(all(tr['n'] == 0 for tr in self.d['trays'].values()))
            self.j.act('start_day')
            validate_state(self.j.state)
        self.assertGreater(self.d['stats']['customers'], 10)

    def test_leftovers_are_thrown_out_at_closing(self):
        self.j = Journey('com')
        self.full_day()
        self.d['trays']['bi'] = dict(n=5, c=4)
        waste = len(self.j.c['life']['waste'])
        r = self.j.act('end_day', carry_event=True)
        car = r['summary']['career']
        self.assertTrue(any(x['id'] == 'bi' for x in car['dumped']))
        self.assertGreater(len(self.j.c['life']['waste']), waste)

    def test_validator_rejects_tampering(self):
        self.j = Journey('com')
        self.full_day()
        validate_state(self.j.state)
        for bad in (lambda d: d['pots']['tam'].update(va=99), lambda d: d['mam'].update(q='great'),
                    lambda d: d['rack'].append(dict(q='perfect', c=1)), lambda d: d['trays']['bi'].update(n=99),
                    lambda d: d['grill'].update(b=dict(n=9, start=1, flip=None, c=0))):
            s = copy.deepcopy(self.j.state)
            bad(s['careers']['com']['ext']['data'])
            with self.assertRaises(GameError):
                validate_state(s)

    def test_task_tampering_is_refused(self):
        day, slot = find('serve', 'Chú Bình ăn sáng')
        t = self.at(day, slot)
        s = copy.deepcopy(self.j.state)
        tt = next(x for x in s['careers']['com']['tasks'] if x['id'] == t['id'])
        tt['plates'] = [dict(v='dia', r='tam', va=9, it=['suon'], x=[], mo=True, mam='ruoi', canh=True, c=0)]
        with self.assertRaises(GameError):
            validate_state(s)


class OldSaves(Base):
    def test_old_save_without_com_gains_it_fresh(self):
        self.j = Journey('ice_cream')
        s = copy.deepcopy(self.j.state)
        s['careers'].pop('com')
        s = migrate_state(s)
        self.assertIn('com', s['careers'])
        validate_state(s)
        self.assertEqual(s['careers']['com'], json.loads(json.dumps(s['careers']['com'])))

    def test_a_block_missing_new_keys_is_upgraded(self):
        self.j = Journey('com')
        d = self.d
        for k in ('regulars', 'desk', 'stats'):
            d.pop(k)
        KM._data(self.j.c)
        validate_state(self.j.state)

    def test_initial_block_is_plain_json(self):
        c = initial_career('com')
        json.dumps(c)


if __name__ == '__main__':
    unittest.main()
