"""Quán phở Cây Si (plugin career pho): the morning pot (fire, scum, tasting, yesterday's bánh), the bowl by
hand (counted dips, cuts, onions, the egg before the broth), the ladle stopped at the customer's line
(kit.tap_now), the three broths (clear, fatty, the small pot without MSG), take-away bags, the hot clock,
the pot running low and the top-up, cash through the shared till, the apprenticeship, surprises,
determinism, save validation and old saves."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import Journey
from game import journey as jr
from game.careers import kit, till, PLUGINS
from game.content import initial_career, make_task
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state

PH = PLUGINS.get('pho')


class Clock:
    def __init__(self):
        self.t = 9000.0

    def __call__(self):
        return self.t


def find(kind=None, title=None, days=range(1, 40), slots=range(1, 5)):
    for day in days:
        for slot in slots:
            t = make_task('pho', day, slot, 1)
            if (kind is None or t['kind'] == kind) and (title is None or t['title'] == title):
                return day, slot
    raise AssertionError(f'no {kind} {title}')


class Base(unittest.TestCase):
    def setUp(self):
        if PH is None:
            raise unittest.SkipTest('pho is filtered out by MNL_CAREERS')
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, day, slot, opened=True):
        """A customer on its own, the shop already set up (pot simmering, tasted, skimmed)."""
        self.j = Journey('pho', slot=slot, day=day)
        d = PH._data(self.j.c)
        d['intro'] = True
        d['shop'].update(open=opened, tasted=True, sniffed=True)
        d['pot'].update(level=100, heat=97, fire='vua', foam=0, cloud=0, salt=0, tasted=True)
        d['sour'] = False
        d['learn']['done'] = True            # past the apprenticeship (tested on its own below)
        self.j.c['ext']['inv']['lots'] = []      # no free opening stock: every bowl has its cost
        for x in PH.ITEMS:
            kit.add_lot(self.j.c, x['id'], 8, x['cost'], 30, 'test')
        return self.j.task

    def settle_desk(self):
        ev = self.d['desk']['ev']
        if ev:
            self.j.act('pho_desk', option=kit.desk_script(PH.DESK, ev['script'])['default'])

    def pour_to(self, tid, level, src='trong'):
        """Ladle and stop when the broth stands at `level` (real seconds on the test clock)."""
        b = self.j.get(tid)['bowls'][-1]
        self.j.act('pho_pour', task=tid, src=src)
        rate = PH.VESSELS[b['v']]['rate']
        self.clock.t += max(0.0, (level - b['lvl'] + 0.5) / rate)
        return self.j.act('pho_stop', task=tid)

    def make(self, tid, skip=()):
        """Build exactly what was ordered."""
        t = self.j.get(tid)
        for ln in t['needs']['lines']:
            self.j.act('pho_bowl', task=tid, v=ln['v'])
            for _ in range(3):
                self.j.act('pho_dip', task=tid)
            for m in ln['meat']:
                self.j.act('pho_meat', task=tid, m=m, side=bool(ln['rieng'] and m == 'tai'))
            if 'onion' not in skip:
                for _ in range({'khong': 0, 'vua': 1, 'nhieu': 2}[ln['hanh']]):
                    self.j.act('pho_onion', task=tid)
            if ln['egg']:
                self.j.act('pho_egg', task=tid)
            lo, hi = PH.band(ln)
            self.pour_to(tid, (lo + hi) // 2, src=ln['src'])
            if ln['v'] == 'hop':
                self.j.act('pho_tie', task=tid)
            self.clock.t += 1
        n = t['needs']
        for _ in range(n.get('quay', 0)):
            self.j.act('pho_side', task=tid, item='quay')
        if n.get('rau'):
            self.j.act('pho_side', task=tid, item='rau')

    def serve_pay(self, tid):
        r = self.j.act('pho_serve', task=tid)
        t = self.j.get(tid)
        self.assertEqual(t['stage'], 'pay', r)
        rec = t['cash']
        return self.j.act('pho_pay', task=tid, change=till.greedy(max(0, till.due(rec))))

    def codes(self, tid):
        return {x['code'] for x in self.j.get(tid).get('slips') or []}


class Spec(Base):
    def test_spec_shape(self):
        s = PH.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('pho', 'pho_', 'food'))
        self.assertTrue(5 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertIn('pho', jr.CH_UNLOCKS[3])
        for name in PH.ACTIONS:
            self.assertTrue(name.startswith('pho_'))
        for name in (*PH.NO_TICK, *PH.PHYSICAL, *PH.FREE):
            self.assertTrue(name in PH.ACTIONS or name in ('pho_intro', 'pho_desk'), name)

    def test_tasks_are_deterministic_and_cover_every_kind(self):
        kinds = set()
        for day in range(1, 25):
            for slot in range(0, 5):
                a, b = make_task('pho', day, slot, 1), make_task('pho', day, slot, 1)
                self.assertEqual(a, b)
                kinds.add(a['kind'])
                if a['kind'] != 'setup':
                    for ln in a['needs']['lines']:
                        self.assertIn(ln['v'], PH.VESSELS)
                        self.assertTrue(set(ln['meat']) <= set(PH.MEATS))
                        self.assertIn(ln['nuoc'], PH.NUOC_LABEL)
                        self.assertIn(ln['src'], PH.SOURCES)
                        self.assertIn(ln['hanh'], PH.HANH)
                        self.assertTrue(not ln['rieng'] or 'tai' in ln['meat'])
        self.assertEqual(kinds, set(PH.KINDS))

    def test_bands_fit_inside_the_bowl(self):
        for k, bands in PH.BANDS.items():
            last = 0
            for nuoc in ('it', 'vua', 'nhieu'):
                lo, hi = bands[nuoc]
                self.assertLess(lo, hi)
                self.assertGreaterEqual(lo, last)
                last = hi
            self.assertLess(last, PH.SPILL[k])

    def test_desk_scripts_and_situations_are_well_formed(self):
        for x in PH.DESK:
            self.assertIn(x['default'], [o['id'] for o in x['options']])
            for o in x['options']:
                self.assertTrue(set(o['effects']) <= {'money', 'review', 'patience', 'xp', 'stock', 'heat', 'pot'}, o['effects'])
        for s in PH.SITUATIONS:
            ids = {f['id'] for f in s['facts']}
            for o in s['options']:
                self.assertTrue(set(o.get('requires', [])) <= ids)


class Morning(Base):
    def test_first_morning_fire_skim_taste_season_open(self):
        self.j = Journey('pho')
        self.j.act('pho_intro')
        t = self.j.task
        self.assertEqual(t['kind'], 'setup')
        self.assertEqual(self.d['pot']['fire'], 'nho')
        self.assertEqual(self.d['pot']['salt'], -1)             # the first morning teaches the spoon
        with self.assertRaises(GameError):
            self.j.act('pho_bowl', task=t['id'], v='to')         # not open yet
        self.j.act('pho_fire', fire='vua')
        while self.d['pot']['foam']:
            self.j.act('pho_skim')
        r = self.j.act('pho_taste')
        self.assertIn('hơi nhạt', r['message'])
        self.j.act('pho_season', what='mam')
        self.assertFalse(self.d['pot']['tasted'])
        self.j.act('pho_taste')
        self.j.act('pho_sniff')
        r = self.j.act('pho_open', task=t['id'])
        self.assertTrue(r.get('celebrate'), r)
        self.assertEqual(self.codes(t['id']), set())
        self.assertTrue(self.d['shop']['open'])

    def test_skipping_the_morning_is_named(self):
        self.j = Journey('pho')
        self.j.act('pho_intro')
        t = self.j.task
        self.j.act('pho_open', task=t['id'])
        self.assertTrue({'fire', 'no_taste', 'salt', 'foam'} <= self.codes(t['id']))

    def test_a_hard_boil_clouds_the_broth_and_the_bowl(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_fire', fire='lon')
        for _ in range(8):
            self.j.act('pho_skim') if self.d['pot']['foam'] else self.j.act('pho_fire', fire='lon')
        self.assertGreaterEqual(self.d['pot']['cloud'], PH.CLOUD_AT)
        self.make(t['id'])
        self.serve_pay(t['id'])
        self.assertIn('cloudy', self.codes(t['id']))

    def test_sour_banh_from_yesterday_is_found_and_thrown_out(self):
        self.j = Journey('pho')
        self.j.act('pho_intro')
        self.d['learn']['done'] = True
        for day in range(2, 12):
            c = self.j.c
            c['day'] = day
            if PH.kit.rng(PH.ID, 'sour', day).randrange(100) < 45:
                break
        else:
            self.fail('no sour morning')
        c = self.j.c
        PH.on_start(self.j.state, c)
        self.assertTrue(self.d['sour'])
        old = PH._old_banh(c)
        self.assertGreater(old, 0)
        r = self.j.act('pho_sniff')
        self.assertIn('chua', r['message'])
        self.j.act('pho_toss')
        self.assertEqual(PH._old_banh(self.j.c), 0)
        self.assertFalse(self.d['sour'])
        self.assertTrue(any(w['reason'] == 'Bánh phở chua' for w in self.j.c['life']['waste']))

    def test_sour_banh_sold_is_a_safety_slip(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca', days=range(2, 40)))
        c = self.j.c
        c['ext']['inv']['lots'] = [l for l in c['ext']['inv']['lots'] if l['item'] != 'banh']
        kit.add_lot(c, 'banh', 4, 2, 2, 'test')
        c['ext']['inv']['lots'][-1]['received'] = c['day'] - 1
        self.d['sour'] = True
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.serve_pay(t['id'])
        slip = next(x for x in self.j.get(t['id'])['slips'] if x['code'] == 'sour')
        self.assertTrue(slip.get('safety'))


class Bowl(Base):
    def test_a_clean_bowl_for_anh_tuan(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        money = self.j.c['money']
        self.make(t['id'])
        r = self.serve_pay(t['id'])
        self.assertEqual(self.codes(t['id']), set(), r)
        self.assertEqual(self.j.get(t['id'])['status'], 'completed')
        self.assertEqual(self.j.get(t['id'])['price'], PH.PRICES['to_lon'])
        self.assertGreaterEqual(self.j.c['money'], money + PH.PRICES['to_lon'])

    def test_dips_count(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        self.j.act('pho_dip', task=t['id'])
        for m in ('tai', 'chin'):
            self.j.act('pho_meat', task=t['id'], m=m)
        self.j.act('pho_onion', task=t['id'])
        self.pour_to(t['id'], 80)
        self.serve_pay(t['id'])
        self.assertIn('stiff', self.codes(t['id']))
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        for _ in range(6):
            self.j.act('pho_dip', task=t['id'])
        for m in ('tai', 'chin'):
            self.j.act('pho_meat', task=t['id'], m=m)
        self.j.act('pho_onion', task=t['id'])
        self.pour_to(t['id'], 80)
        self.serve_pay(t['id'])
        self.assertIn('soggy', self.codes(t['id']))

    def test_the_order_of_the_steps_is_enforced(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('pho_dip', task=t['id'])                  # no bowl yet
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        with self.assertRaises(GameError):
            self.j.act('pho_meat', task=t['id'], m='tai')        # meat before the noodles
        with self.assertRaises(GameError):
            self.j.act('pho_pour', task=t['id'])                 # broth on an empty bowl
        self.j.act('pho_dip', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('pho_meat', task=t['id'], m='chin', side=True)   # only tái goes on the side
        self.j.act('pho_meat', task=t['id'], m='tai')
        with self.assertRaises(GameError):
            self.j.act('pho_meat', task=t['id'], m='tai')        # twice
        self.j.act('pho_pour', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('pho_serve', task=t['id'])                # the ladle still in the air
        with self.assertRaises(GameError):
            self.j.act('pho_dip', task=t['id'])
        self.clock.t += 7
        self.j.act('pho_stop', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('pho_meat', task=t['id'], m='chin')       # meat after the broth
        with self.assertRaises(GameError):
            self.j.act('pho_stop', task=t['id'])                 # nothing to stop

    def test_wrong_cut_is_missing_and_extra(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        for _ in range(3):
            self.j.act('pho_dip', task=t['id'])
        self.j.act('pho_meat', task=t['id'], m='nam')
        self.j.act('pho_onion', task=t['id'])
        self.pour_to(t['id'], 80)
        self.serve_pay(t['id'])
        self.assertTrue({'missing', 'extra'} <= self.codes(t['id']))

    def test_drop_puts_the_bowl_in_the_waste(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        self.j.act('pho_dip', task=t['id'])
        self.j.act('pho_meat', task=t['id'], m='tai')
        self.assertGreater(self.j.get(t['id'])['cost'], 0)
        self.j.act('pho_drop', task=t['id'])
        self.assertEqual(self.j.get(t['id'])['bowls'], [])
        self.assertEqual(self.j.get(t['id'])['cost'], 0)
        self.assertTrue(any(w['reason'] == 'Tô phở làm lại' for w in self.j.c['life']['waste']))

    def test_egg_after_the_broth_stays_raw(self):
        t = self.at(*find('serve', 'Anh Sáu ăn kiểu Sài Gòn'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to')
        for _ in range(3):
            self.j.act('pho_dip', task=t['id'])
        for m in ('tai', 'gau'):
            self.j.act('pho_meat', task=t['id'], m=m)
        self.j.act('pho_onion', task=t['id'])
        self.pour_to(t['id'], 80)
        self.j.act('pho_egg', task=t['id'])
        self.j.act('pho_side', task=t['id'], item='rau')
        self.serve_pay(t['id'])
        self.assertIn('egg_raw_0', self.codes(t['id']))

    def test_onion_wishes(self):
        t = self.at(*find('serve', 'Chị Hạnh cho bé Bống'))
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.serve_pay(t['id'])
        self.assertEqual(self.codes(t['id']), set())
        t = self.at(*find('serve', 'Chị Hạnh cho bé Bống'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to')
        for _ in range(3):
            self.j.act('pho_dip', task=t['id'])
        self.j.act('pho_meat', task=t['id'], m='chin')
        self.j.act('pho_onion', task=t['id'])                     # "không hành"
        self.pour_to(t['id'], 60)
        self.serve_pay(t['id'])
        self.assertIn('onion_0', self.codes(t['id']))
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.make(t['id'], skip=('onion',))
        self.serve_pay(t['id'])
        self.assertIn('no_onion_0', self.codes(t['id']))


class Ladle(Base):
    def test_the_stop_tap_sets_the_level_from_the_tap_moment(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        self.j.act('pho_dip', task=t['id'])
        self.j.act('pho_pour', task=t['id'])
        start = self.clock.t
        self.clock.t += 9                                         # the command arrives late…
        self.j.act('pho_stop', task=t['id'], tap_at=start + 7)    # …but the finger came down at 7 s
        self.assertEqual(self.j.get(t['id'])['bowls'][-1]['lvl'], int(7 * PH.VESSELS['to_lon']['rate']))

    def test_tap_at_is_kept_honest(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        self.j.act('pho_dip', task=t['id'])
        self.j.act('pho_pour', task=t['id'])
        self.clock.t += kit.TAP_LAG + 5
        self.j.act('pho_stop', task=t['id'], tap_at=self.clock.t - kit.TAP_LAG - 60)   # an old tap is clamped to TAP_LAG back
        self.assertEqual(self.j.get(t['id'])['bowls'][-1]['lvl'], int(5 * PH.VESSELS['to_lon']['rate']))

    def test_too_little_too_much_and_spilled(self):
        for level, code in ((50, 'little_0'), (94, 'much_0'), (104, 'spill')):
            t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
            self.j.act('ask', task=t['id'])
            self.j.act('pho_bowl', task=t['id'], v='to_lon')
            for _ in range(3):
                self.j.act('pho_dip', task=t['id'])
            for m in ('tai', 'chin'):
                self.j.act('pho_meat', task=t['id'], m=m)
            self.j.act('pho_onion', task=t['id'])
            self.pour_to(t['id'], level)
            self.serve_pay(t['id'])
            self.assertIn(code, self.codes(t['id']), level)

    def test_a_second_ladle_tops_up(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        for _ in range(3):
            self.j.act('pho_dip', task=t['id'])
        for m in ('tai', 'chin'):
            self.j.act('pho_meat', task=t['id'], m=m)
        self.j.act('pho_onion', task=t['id'])
        self.pour_to(t['id'], 55)
        self.pour_to(t['id'], 80)
        self.assertEqual(self.j.get(t['id'])['bowls'][-1]['lvl'], 80)
        self.serve_pay(t['id'])
        self.assertEqual(self.codes(t['id']), set())

    def test_no_msg_needs_the_small_pot_only(self):
        t = self.at(*find('serve', 'Ông giáo Thụ đọc báo'))
        self.j.act('ask', task=t['id'])
        small = self.d['small']
        self.make(t['id'])
        self.assertLess(self.d['small'], small)
        self.serve_pay(t['id'])
        self.assertEqual(self.codes(t['id']), set())
        t = self.at(*find('serve', 'Ông giáo Thụ đọc báo'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to')
        for _ in range(3):
            self.j.act('pho_dip', task=t['id'])
        for m in ('tai', 'chin'):
            self.j.act('pho_meat', task=t['id'], m=m)
        self.j.act('pho_onion', task=t['id'])
        self.j.act('pho_onion', task=t['id'])
        self.pour_to(t['id'], 80, src='trong')
        self.serve_pay(t['id'])
        self.assertIn('msg', self.codes(t['id']))

    def test_fatty_broth_is_remembered(self):
        t = self.at(*find('serve', 'Chị Nguyệt ăn sáng'))
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.serve_pay(t['id'])
        self.assertEqual(self.codes(t['id']), set())
        t = self.at(*find('serve', 'Chị Nguyệt ăn sáng'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to')
        for _ in range(3):
            self.j.act('pho_dip', task=t['id'])
        for m in ('tai', 'nam'):
            self.j.act('pho_meat', task=t['id'], m=m)
        self.j.act('pho_onion', task=t['id'])
        self.pour_to(t['id'], 80, src='trong')
        self.j.act('pho_side', task=t['id'], item='quay')
        self.j.act('pho_side', task=t['id'], item='quay')
        self.serve_pay(t['id'])
        self.assertIn('not_fatty_0', self.codes(t['id']))

    def test_a_cold_pot_leaves_the_tai_red(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.d['pot'].update(heat=86, fire='nho')
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.serve_pay(t['id'])
        self.assertIn('tai_raw', self.codes(t['id']))


class TakeAway(Base):
    def test_take_away_with_tai_on_the_side_and_a_tied_bag(self):
        t = self.at(*find('take', 'Cô Linh mua mang về'))
        self.j.act('ask', task=t['id'])
        hop = kit.stock(self.j.c, 'hop')
        self.make(t['id'])
        self.assertEqual(kit.stock(self.j.c, 'hop'), hop - 1)
        self.serve_pay(t['id'])
        self.assertEqual(self.codes(t['id']), set())
        self.assertIsNone(self.j.get(t['id'])['hot'])                  # a bag does not cool at the counter

    def test_tai_in_the_box_and_an_untied_bag(self):
        t = self.at(*find('take', 'Cô Linh mua mang về'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='hop')
        for _ in range(3):
            self.j.act('pho_dip', task=t['id'])
        for m in ('tai', 'nam'):
            self.j.act('pho_meat', task=t['id'], m=m)
        self.j.act('pho_onion', task=t['id'])
        self.pour_to(t['id'], 50)
        self.serve_pay(t['id'])
        self.assertTrue({'tai_mixed_0', 'untied_0'} <= self.codes(t['id']))

    def test_the_crew_order(self):
        t = self.at(*find('crew'))
        self.j.act('ask', task=t['id'])
        for x in PH.ITEMS:
            kit.add_lot(self.j.c, x['id'], 8, x['cost'], 30, 'test')
        self.make(t['id'])
        self.serve_pay(t['id'])
        self.assertEqual(self.codes(t['id']), set())
        self.assertEqual(len(self.j.get(t['id'])['bowls']), 4)


class Hot(Base):
    def test_slow_service_cools_then_goes_cold(self):
        for wait, code in ((60, 'cooling'), (200, 'cold')):
            t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
            self.j.act('ask', task=t['id'])
            self.make(t['id'])
            self.clock.t += wait
            self.serve_pay(t['id'])
            self.assertIn(code, self.codes(t['id']))

    def test_public_task_carries_the_hot_clock(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        v = public_state(self.j.state)
        pt = next(x for x in v['careers']['pho']['tasks'] if x['id'] == t['id'])
        self.assertEqual(set(pt['hot']), {'start', 'limit', 'end'})


class Pot(Base):
    def test_the_pot_runs_low_and_is_topped_up(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.d['pot']['level'] = 20
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        self.j.act('pho_dip', task=t['id'])
        self.j.act('pho_pour', task=t['id'])
        self.clock.t += 7
        self.j.act('pho_stop', task=t['id'])
        self.assertLess(self.d['pot']['level'], 20)
        lvl = self.d['pot']['level']
        if lvl >= PH.VESSELS['to_lon']['vol']:
            self.d['pot']['level'] = 5
        with self.assertRaises(GameError):
            self.j.act('pho_pour', task=t['id'])
        xuong = kit.stock(self.j.c, 'xuong')
        self.j.act('pho_topup')
        self.assertEqual(kit.stock(self.j.c, 'xuong'), xuong - 1)
        pot = self.d['pot']
        self.assertGreater(pot['level'], 40)
        self.assertLess(pot['heat'], 95)
        self.assertFalse(pot['tasted'])
        self.j.act('pho_topup')                                       # still low: a second batch
        self.assertEqual(self.d['pot']['level'], 100)
        with self.assertRaises(GameError):
            self.j.act('pho_topup')                                   # full enough now

    def test_heat_follows_the_fire(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.d['pot'].update(heat=80)
        self.j.act('ask', task=t['id'])
        for _ in range(12):
            self.j.act('pho_fire', fire='vua')
        self.assertEqual(self.d['pot']['heat'], 97)
        self.assertEqual(self.d['pot']['cloud'], 0)


class Learning(Base):
    def test_bac_lam_catches_each_mistake_once(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.d['learn']['done'] = False
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        self.j.act('pho_dip', task=t['id'])
        for m in ('tai', 'chin'):
            self.j.act('pho_meat', task=t['id'], m=m)
        self.j.act('pho_onion', task=t['id'])
        self.pour_to(t['id'], 80)
        r = self.j.act('pho_serve', task=t['id'])
        self.assertEqual(r.get('lesson'), 'stiff')
        self.assertEqual(self.j.get(t['id'])['stage'], 'prep')
        r = self.j.act('pho_serve', task=t['id'])                    # the same mistake goes through
        self.assertEqual(self.j.get(t['id'])['stage'], 'pay', r)


class Money(Base):
    def test_extras_are_charged_and_costs_stay_below_the_price(self):
        t = self.at(*find('serve', 'Anh Tuấn ăn tô đặc biệt'))
        self.j.act('ask', task=t['id'])
        self.make(t['id'])
        self.serve_pay(t['id'])
        tt = self.j.get(t['id'])
        self.assertEqual(tt['price'], PH.PRICES['to_lon'] + 2 * PH.PRICES['them'] + 2 * PH.PRICES['quay'])
        self.assertEqual(self.codes(t['id']), set())
        for title in ('Anh Tuấn trước giờ vào ca', 'Chị Nguyệt ăn sáng', 'Cô Linh mua mang về'):
            t = self.at(*find(None, title))
            self.j.act('ask', task=t['id'])
            self.make(t['id'])
            self.serve_pay(t['id'])
            tt = self.j.get(t['id'])
            self.assertLess(tt['cost'], tt['price'] * 0.6, title)

    def test_decline_when_out_of_stock(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.c['ext']['inv']['lots'] = [l for l in self.j.c['ext']['inv']['lots'] if l['item'] != 'tai']
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        self.j.act('pho_dip', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('pho_meat', task=t['id'], m='tai')
        self.j.act('pho_decline', task=t['id'])
        self.assertEqual(self.j.get(t['id'])['status'], 'completed')
        self.assertEqual(self.j.get(t['id'])['choice'], 'decline')


class Days(Base):
    def play_day(self):
        self.settle_desk()
        for t in [t for t in self.j.c['tasks'] if t['status'] not in ('completed', 'cancelled')]:
            self.settle_desk()
            if t['kind'] == 'setup':
                self.j.act('pho_fire', fire='vua')
                while self.d['pot']['foam']:
                    self.j.act('pho_skim')
                self.j.act('pho_taste')
                while self.d['pot']['salt']:
                    self.j.act('pho_season', what='mam' if self.d['pot']['salt'] < 0 else 'nuoc')
                self.j.act('pho_taste')
                self.j.act('pho_sniff')
                if self.d['sour'] and PH._old_banh(self.j.c):
                    self.j.act('pho_toss')
                for x in PH.ITEMS:
                    if kit.stock(self.j.c, x['id']) < 8:
                        kit.add_lot(self.j.c, x['id'], 8, x['cost'], x.get('life') or 30, 'test')
                self.j.act('pho_open', task=t['id'])
                self.assertEqual(self.codes(t['id']), set())
                continue
            if not t['known']:
                self.j.act('ask', task=t['id'])
            if self.d['pot']['level'] <= PH.TOPUP_AT:
                self.j.act('pho_topup')
                for _ in range(8):
                    self.j.act('pho_skim') if self.d['pot']['foam'] else self.j.act('pho_fire', fire='vua')
                self.j.act('pho_taste')
                while self.d['pot']['salt']:
                    self.j.act('pho_season', what='mam' if self.d['pot']['salt'] < 0 else 'nuoc')
            self.make(t['id'])
            self.settle_desk()
            self.serve_pay(t['id'])
        self.settle_desk()
        r = self.j.act('end_day', carry_event=True)
        self.j.act('start_day')
        validate_state(self.j.state)
        return r

    def test_ten_days_of_play_stay_valid(self):
        self.j = Journey('pho')
        self.j.act('pho_intro')
        for _ in range(10):
            r = self.play_day()
            self.assertIn('lines', r['summary']['career'])
        self.assertGreater(self.d['stats']['customers'], 10)
        v = public_state(self.j.state)
        json.dumps(v['careers']['pho'])

    def test_end_of_day_mentions_tomorrow_when_banh_is_left(self):
        self.j = Journey('pho')
        self.j.act('pho_intro')
        r = self.play_day()
        lines = r['summary']['career']['lines']
        self.assertTrue(any(x.startswith('🌅 Ngày mai') for x in lines), lines)

    def test_validator_rejects_tampering(self):
        t = self.at(*find('serve', 'Anh Tuấn trước giờ vào ca'))
        self.j.act('ask', task=t['id'])
        self.j.act('pho_bowl', task=t['id'], v='to_lon')
        self.j.act('pho_dip', task=t['id'])
        self.j.act('pho_pour', task=t['id'])
        validate_state(self.j.state)
        for mutate in (lambda s: s['careers']['pho']['tasks'][0]['bowls'][0].update(lvl=500),
                       lambda s: s['careers']['pho']['tasks'][0]['bowls'][0].update(v='noi'),
                       lambda s: s['careers']['pho']['tasks'][0]['bowls'][0].update(meat=['ca']),
                       lambda s: s['careers']['pho']['tasks'][0]['pour'].update(rate=999),
                       lambda s: s['careers']['pho']['ext']['data']['pot'].update(fire='max'),
                       lambda s: s['careers']['pho']['ext']['data']['pot'].update(salt=7),
                       lambda s: s['careers']['pho']['tasks'][0]['needs'].update(lines=[])):
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
        s['careers'].pop('pho')
        s['journey']['chapter'] = 4
        s['journey']['unlocked'] = [cid for n in range(1, 5) for cid in jr.CH_UNLOCKS[n] if cid in s['careers']]
        s['journey']['done'] = [1, 2, 3]
        before = {cid: json.dumps(c, sort_keys=True, ensure_ascii=False) for cid, c in s['careers'].items()}
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        self.assertEqual(json.dumps(m['careers']['pho'], sort_keys=True), json.dumps(initial_career('pho'), sort_keys=True))
        for cid, raw in before.items():
            self.assertEqual(json.dumps(m['careers'][cid], sort_keys=True, ensure_ascii=False), raw, cid)
        self.assertIn('pho', m['journey']['unlocked'])


# The release this branch starts from: saves must cross to it and back (rolling release, rollback).
BASE_REF = '1aba75d'
ROOT = Path(__file__).resolve().parents[1]
OLD_SAVE = ('import json,sys;from game.engine import new_state,apply_action,validate_state;'
            's=new_state();s,_=apply_action(s,"milk_tea","select_career",{});s,_=apply_action(s,"milk_tea","start_day",{});'
            'validate_state(s);print(json.dumps(s))')
OLD_LOAD = ('import json,sys;from game.engine import validate_state,migrate_state;'
            's=migrate_state(json.load(sys.stdin));validate_state(s);print(json.dumps(s))')


# Careers this release adds next to the shop (the base tree knows none of them): a rollback strips them all.
ADDED = ('pho', 'com', 'photobooth', 'giupviec')


def rollback_strip(s):
    """What a rollback to a tree without the shop needs: the career block gone, the id and the shop's NPCs and
    story beats out of every list and key (the same for every career added with it)."""
    s = copy.deepcopy(s)
    for cid in ADDED:
        s['careers'].pop(cid, None)
    if s.get('current') in ADDED:
        s['current'] = next(iter(s['careers']))

    def ours(v):
        return isinstance(v, str) and any(v == cid or v.startswith(cid + '_') for cid in ADDED)

    def scrub(o):
        if isinstance(o, dict):
            for k in [k for k in o if ours(k)]:
                del o[k]
            for v in o.values():
                scrub(v)
        elif isinstance(o, list):
            # 'pho', and records about the shop: story queue entries, the shop's NPCs in the closeness log
            o[:] = [v for v in o if not ours(v) and not (isinstance(v, dict) and any(ours(x) for x in v.values()))]
            for v in o:
                scrub(v)
    for k, v in s.items():
        if k != 'careers':
            scrub(v)
    return s


class OldTree(Base):
    """Both ways across the base release, each tree in its own process."""
    tree = None
    play_day = Days.play_day

    @classmethod
    def setUpClass(cls):
        old = os.environ.get('MNL_OLD_TREE')
        if old:
            cls.tree = old
            return
        if not shutil.which('git') or not (ROOT / '.git').exists():
            raise unittest.SkipTest('needs a git checkout or MNL_OLD_TREE')
        if subprocess.run(['git', 'cat-file', '-e', BASE_REF + '^{commit}'], cwd=ROOT, capture_output=True).returncode:
            raise unittest.SkipTest(f'{BASE_REF} is not in this clone')
        cls._tmp = tempfile.TemporaryDirectory(prefix='base-')
        archive = subprocess.run(['git', 'archive', BASE_REF, 'game', 'reference', 'i18n'], cwd=ROOT, capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', cls._tmp.name], input=archive, check=True)
        cls.tree = cls._tmp.name

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, '_tmp', None):
            cls._tmp.cleanup()

    def in_base(self, prog, data=None):
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(p for p in (self.tree, os.environ.get('PYTHONPATH')) if p))
        out = subprocess.run([sys.executable, '-c', prog], input=data, capture_output=True, text=True, encoding='utf-8',
                             cwd=self.tree, env=env, timeout=300)
        return out

    def test_an_old_save_gains_the_shop_and_a_played_save_goes_back_after_the_strip(self):
        out = self.in_base(OLD_SAVE)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        s = migrate_state(json.loads(out.stdout))
        validate_state(s)
        self.assertEqual(json.dumps(s['careers']['pho'], sort_keys=True), json.dumps(initial_career('pho'), sort_keys=True))
        # Played here for two days, then rolled back.
        self.j = Journey('pho')
        self.j.act('pho_intro')
        for _ in range(2):
            self.play_day()
        played = json.dumps(self.j.state, ensure_ascii=False)
        back = self.in_base(OLD_LOAD, played)
        self.assertNotEqual(back.returncode, 0, 'the base tree is expected to refuse an unknown career as is')
        back = self.in_base(OLD_LOAD, json.dumps(rollback_strip(self.j.state), ensure_ascii=False))
        self.assertEqual(back.returncode, 0, back.stderr[-2000:])
        again = migrate_state(json.loads(back.stdout))   # and forward once more: the shop comes back fresh
        validate_state(again)
        self.assertEqual(json.dumps(again['careers']['pho'], sort_keys=True), json.dumps(initial_career('pho'), sort_keys=True))
        for cid in again['careers']:
            if cid not in ADDED:
                self.assertEqual(again['careers'][cid]['tasks'], self.j.state['careers'][cid]['tasks'], cid)


if __name__ == '__main__':
    unittest.main()
