"""Tiệm ảnh Tách Tách (plugin career photobooth): the morning (lens, test shot, ink roll), the booth set up
for the order, the shutter at the moment the group holds the pose (a stop tap), the customers' choice,
stickers / date / colour, printing (a reprint wastes the sheet), trimming, cash through the shared till,
chị Lam's apprenticeship, surprises, determinism, save validation, old saves (and the 1aba75d release)."""
import copy
import json
import os
import re
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

PB = PLUGINS.get('photobooth')
ROOT = Path(__file__).resolve().parents[1]


class Clock:
    def __init__(self):
        self.t = 9000.0

    def __call__(self):
        return self.t


def find(title=None, days=range(1, 40), slots=range(1, 6), pred=None):
    for day in days:
        for slot in slots:
            t = make_task('photobooth', day, slot, 1)
            if t['kind'] == 'serve' and (title is None or t['title'] == title) and (pred is None or pred(t)):
                return day, slot
    raise AssertionError(f'no task {title}')


class Base(unittest.TestCase):
    def setUp(self):
        if PB is None:
            raise unittest.SkipTest('photobooth is filtered out by MNL_CAREERS')
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, day, slot, learning=False):
        """A customer on its own, the shop already set up (lens clean, a full ink roll)."""
        self.j = Journey('photobooth', slot=slot, day=day)
        d = PB._data(self.j.c)
        d['intro'] = True
        d['booth'].update(day=day, open=True, lens=True, tested=True, fog=False)
        d['ribbon'] = PB.RIBBON
        d['learn']['done'] = not learning
        for x in PB.ITEMS:
            kit.add_lot(self.j.c, x['id'], 6, x['cost'], 30, 'test')
        return self.j.task

    def settle_desk(self):
        ev = self.d['desk']['ev']
        if ev:
            self.j.act('pb_desk', option=kit.desk_script(PB.DESK, ev['script'])['default'])

    def snap(self, tid, where='good'):
        """One shot at a chosen moment of the countdown ('good', 'early', 'blink', 'late')."""
        t = self.j.get(tid)
        if t['cam'] is None:
            self.j.act('pb_shoot', task=tid)
            t = self.j.get(tid)
        lead, hold = PB.hold_of(t, self.j.c['day'])
        start = t['cam']['start']
        el = {'good': PB.COUNT + lead + hold / 2, 'early': PB.COUNT / 2, 'blink': PB.COUNT + lead + hold + PB.BLINK_AFTER / 2,
              'late': PB.COUNT + lead + hold + PB.BLINK_AFTER + 1.0}[where]
        self.clock.t = start + el
        r = self.j.act('pb_snap', task=tid, tap_at=self.clock.t)
        self.clock.t += 0.3
        return r

    def set_up(self, tid, **wrong):
        n = self.j.get(tid)['needs']
        self.j.act('pb_pkg', task=tid, pkg=wrong.get('pkg', n['pkg']))
        self.j.act('pb_frame', task=tid, frame=wrong.get('frame', n['frames'][0]))
        self.j.act('pb_bd', task=tid, bd=wrong.get('bd', n['bd'][0]))
        self.j.act('pb_light', task=tid, light=wrong.get('light', n['light']))
        for p in wrong.get('props', n['props']):
            self.j.act('pb_prop', task=tid, prop=p)

    def shoot(self, tid, good=None):
        k = PB.PKGS[self.j.get(tid)['needs']['pkg']]['shots']
        for _ in range(good or k):
            self.snap(tid)

    def decorate(self, tid, **wrong):
        n = self.j.get(tid)['needs']
        for s in wrong.get('st', n['st']):
            self.j.act('pb_sticker', task=tid, st=s)
        self.j.act('pb_date', task=tid, on=wrong.get('date', n['date']))
        self.j.act('pb_filter', task=tid, flt=wrong.get('flt', n['flt']))

    def make(self, tid, **wrong):
        if not self.j.get(tid)['known']:
            self.j.act('ask', task=tid)
        self.set_up(tid, **wrong)
        self.shoot(tid)
        self.j.act('pb_show', task=tid)
        for i in self.j.get(tid)['want']:
            self.j.act('pb_pick', task=tid, i=i)
        self.decorate(tid, **wrong)
        self.j.act('pb_print', task=tid)
        self.j.act('pb_trim', task=tid)

    def serve_pay(self, tid):
        r = self.j.act('pb_serve', task=tid)
        t = self.j.get(tid)
        self.assertEqual(t['stage'], 'pay', r)
        return self.j.act('pb_pay', task=tid, change=till.greedy(max(0, till.due(t['cash']))))

    def codes(self, tid):
        return {x['code'] for x in self.j.get(tid).get('slips') or []}


class Spec(Base):
    def test_spec_shape(self):
        s = PB.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('photobooth', 'pb_', 'service'))
        self.assertTrue(5 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertIn('photobooth', jr.CH_UNLOCKS[2])
        for name in PB.ACTIONS:
            self.assertTrue(name.startswith('pb_'))
        for name in (*PB.NO_TICK, *PB.PHYSICAL, *PB.FREE):
            self.assertTrue(name in PB.ACTIONS or name in ('pb_intro', 'pb_desk'), name)

    def test_ids_match_the_shared_frames_module(self):
        """The server's frames, backdrops, props, stickers, filters and packages are the ones photo-frames.js draws."""
        js = (ROOT / 'public' / 'js' / 'v4' / 'photo-frames.js').read_text(encoding='utf-8')

        def ids(name):
            block = re.search(r'export const ' + name + r'=\[(.*?)\n\];', js, re.S)
            self.assertIsNotNone(block, name)
            return set(re.findall(r"(?:\{id:|^  F\()'([a-z_]+)'", block.group(1), re.M))
        self.assertEqual(set(PB.FRAMES), ids('FRAMES'))
        self.assertEqual(set(PB.BACKDROPS), ids('BACKDROPS'))
        self.assertEqual(set(PB.PROPS), ids('PROPS'))
        self.assertEqual(set(PB.STICKERS), ids('STICKERS'))
        self.assertEqual(set(PB.FILTERS), ids('FILTERS'))
        layouts = re.search(r'export const LAYOUTS=\{(.*?)\n\};', js, re.S).group(1)
        self.assertEqual(set(PB.PKGS), set(re.findall(r'^\s*([a-z]+):\{', layouts, re.M)))
        self.assertGreaterEqual(len(PB.FRAMES), 12)

    def test_orders_use_known_ids_and_looks(self):
        for o in PB.ORDERS:
            n = o[3]
            self.assertIn(n['pkg'], PB.PKGS)
            self.assertTrue(set(n['frames']) <= set(PB.FRAMES) and n['frames'])
            self.assertTrue(set(n['bd']) <= set(PB.BACKDROPS) and n['bd'])
            self.assertTrue(set(n['props']) <= set(PB.PROPS))
            self.assertTrue(set(n['st']) <= set(PB.STICKERS))
            self.assertIn(n['flt'], PB.FILTERS)
            self.assertIn(n['light'], PB.LIGHTS)
            self.assertIn(n['look'], PB.LOOKS)
            self.assertTrue(0 <= o[0] < len(PB.PEOPLE))

    def test_tasks_are_deterministic(self):
        kinds = set()
        for day in range(1, 25):
            for slot in range(0, 5):
                a, b = make_task('photobooth', day, slot, 3), make_task('photobooth', day, slot, 3)
                self.assertEqual(a, b)
                kinds.add(a['kind'])
        self.assertEqual(kinds, set(PB.KINDS))

    def test_desk_scripts_and_situations_are_well_formed(self):
        for x in PB.DESK:
            self.assertIn(x['default'], {o['id'] for o in x['options']})
        ids = [s['id'] for s in PB.SITUATIONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_prices_stay_in_line_with_the_street_shops(self):
        """A photobooth customer pays like a nail set or a few scoops of ice cream, not like a salon colour."""
        self.assertLessEqual(max(PB.PRICES.values()), 30)
        cost = {x['id']: x['cost'] for x in PB.ITEMS}
        for k, pk in PB.PKGS.items():
            spent = cost[pk['paper']] + pk['sleeves'] * cost['bao'] + (cost[pk['frame']] if pk['frame'] else 0)
            self.assertGreater(PB.PRICES[k] - spent, 5, k)


class Morning(Base):
    def test_first_morning_teaches_lens_test_and_ink(self):
        self.j = Journey('photobooth')
        self.j.act('pb_intro')
        setup = self.j.task
        self.assertEqual(setup['kind'], 'setup')
        self.assertEqual(self.d['ribbon'], 3)
        self.assertFalse(self.d['booth']['lens'])
        with self.assertRaises(GameError):
            self.j.act('pb_pkg', task=setup['id'], pkg='strip')
        self.j.act('pb_lens')
        r = self.j.act('pb_test')
        self.assertIn('còn 3 tấm', r['message'])
        muc = kit.stock(self.j.c, 'muc')
        self.j.act('pb_ribbon')
        self.assertEqual(self.d['ribbon'], PB.RIBBON)
        self.assertEqual(kit.stock(self.j.c, 'muc'), muc - 1)
        r = self.j.act('pb_open', task=setup['id'])
        self.assertTrue(r.get('celebrate'))
        self.assertEqual(self.j.get(setup['id'])['status'], 'completed')
        self.assertFalse(self.j.get(setup['id']).get('slips'))

    def test_skipping_the_morning_is_named(self):
        self.j = Journey('photobooth')
        self.j.act('pb_intro')
        setup = self.j.task
        self.j.act('pb_open', task=setup['id'])
        self.assertEqual({x['code'] for x in self.j.get(setup['id'])['slips']}, {'lens', 'no_test', 'ribbon'})

    def test_a_dirty_lens_fogs_every_shot(self):
        t = self.at(*find())
        self.d['booth']['lens'] = False
        self.j.act('ask', task=t['id'])
        self.set_up(t['id'])
        r = self.snap(t['id'])
        self.assertIn('mờ', r['message'])
        self.assertTrue(self.j.get(t['id'])['shots'][0]['haze'])
        self.j.act('pb_lens')
        self.snap(t['id'])
        self.assertFalse(self.j.get(t['id'])['shots'][1]['haze'])


class Shutter(Base):
    def test_the_moment_decides_the_shot(self):
        t = self.at(*find())
        self.j.act('ask', task=t['id'])
        self.set_up(t['id'])
        for where in ('early', 'good', 'blink', 'late'):
            self.snap(t['id'], where)
        self.assertEqual([s['q'] for s in self.j.get(t['id'])['shots']], ['early', 'good', 'blink', 'late'])
        self.assertEqual(self.d['today']['shots'], 4)
        self.assertEqual(self.d['today']['good'], 1)

    def test_toddlers_hold_shorter_grandparents_later_and_longer(self):
        kid = make_task('photobooth', *find(pred=lambda t: t['needs']['kid'], days=range(2, 40)), 1)
        old = make_task('photobooth', *find(pred=lambda t: t['needs']['old']), 1)
        plain = make_task('photobooth', *find(pred=lambda t: not t['needs']['kid'] and not t['needs']['old']), 1)
        self.assertLess(PB.hold_of(kid, 9)[1], PB.hold_of(plain, 9)[1])
        self.assertGreater(PB.hold_of(old, 9)[1], PB.hold_of(plain, 9)[1])
        self.assertGreater(PB.hold_of(old, 9)[0], 0.6)
        self.assertGreater(PB.hold_of(plain, 1)[1], PB.hold_of(plain, 9)[1])     # the first days are kinder

    def test_a_tap_is_counted_when_the_finger_came_down_within_bounds(self):
        t = self.at(*find())
        self.j.act('ask', task=t['id'])
        self.set_up(t['id'])
        self.j.act('pb_shoot', task=t['id'])
        start = self.j.get(t['id'])['cam']['start']
        lead, hold = PB.hold_of(self.j.get(t['id']), self.j.c['day'])
        self.clock.t = start + PB.COUNT + lead + hold + 2.0          # the command arrives late…
        self.j.act('pb_snap', task=t['id'], tap_at=start + PB.COUNT + lead + hold / 2)   # …the finger was on time
        self.assertEqual(self.j.get(t['id'])['shots'][0]['q'], 'good')
        nxt = self.j.get(t['id'])['cam']['start']
        self.clock.t = nxt + 60
        self.j.act('pb_snap', task=t['id'], tap_at=nxt - 500)        # a forged stamp is clamped to the arrival
        self.assertEqual(self.j.get(t['id'])['shots'][1]['q'], 'late')

    def test_eight_shots_a_round_then_redo(self):
        t = self.at(*find())
        self.j.act('ask', task=t['id'])
        self.set_up(t['id'])
        for _ in range(PB.MAX_SHOTS):
            self.snap(t['id'], 'early')
        self.assertIsNone(self.j.get(t['id'])['cam'])
        with self.assertRaises(GameError):
            self.j.act('pb_shoot', task=t['id'])
        r = self.j.act('pb_show', task=t['id'])
        self.assertIsNone(self.j.get(t['id'])['want'])
        self.assertIn('xóa chụp lại', r['message'])
        self.j.act('pb_redo', task=t['id'])
        self.assertEqual(self.j.get(t['id'])['shots'], [])

    def test_snap_needs_a_running_countdown_and_a_set_booth(self):
        t = self.at(*find())
        self.j.act('ask', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('pb_snap', task=t['id'])
        with self.assertRaises(GameError):
            self.j.act('pb_shoot', task=t['id'])                    # no backdrop, no light yet


class Serving(Base):
    def test_a_clean_strip_end_to_end(self):
        t = self.at(*find('Hội bạn 11A1 tan học'))
        tid = t['id']
        money = self.j.c['money']
        paper, sleeves = kit.stock(self.j.c, 'giay_dai'), kit.stock(self.j.c, 'bao')
        self.make(tid)
        self.assertEqual(kit.stock(self.j.c, 'giay_dai'), paper - 1)
        self.assertEqual(kit.stock(self.j.c, 'bao'), sleeves - 1)
        self.assertEqual(self.d['ribbon'], PB.RIBBON - 1)
        r = self.serve_pay(tid)
        self.assertEqual(self.j.get(tid)['status'], 'completed')
        self.assertEqual(self.codes(tid), set())
        self.assertEqual(self.j.get(tid)['price'], PB.PRICES['strip'])
        self.assertGreaterEqual(self.j.c['money'], money + PB.PRICES['strip'])
        self.assertIn('Bé Nhi', r['message'])

    def test_big_frame_uses_a_wooden_frame_and_double_two_sleeves(self):
        t = self.at(*find('Ông bà Chín kỷ niệm 50 năm'))
        k = kit.stock(self.j.c, 'khung')
        self.make(t['id'])
        self.assertEqual(kit.stock(self.j.c, 'khung'), k - 1)
        self.serve_pay(t['id'])
        self.assertEqual(self.codes(t['id']), set())
        t = self.at(*find('Anh Khôi chị Vy hẹn hò'))
        b = kit.stock(self.j.c, 'bao')
        self.make(t['id'])
        self.assertEqual(kit.stock(self.j.c, 'bao'), b - 2)
        self.serve_pay(t['id'])
        self.assertEqual(self.j.get(t['id'])['price'], PB.PRICES['double'])

    def test_wrong_frame_backdrop_light_and_props_are_named(self):
        t = self.at(*find('Hội bạn 11A1 tan học'))
        self.make(t['id'], frame='tet', bd='den', light='diu', props=['non_la'])
        self.j.act('pb_serve', task=t['id'])
        self.assertTrue({'frame', 'backdrop', 'light', 'props'} <= self.codes(t['id']))

    def test_a_closed_eye_in_the_print_is_the_first_thing_they_see(self):
        t = self.at(*find('Anh Khôi chị Vy hẹn hò'))
        tid = t['id']
        self.j.act('ask', task=tid)
        self.set_up(tid)
        self.snap(tid, 'blink')
        self.shoot(tid)
        self.j.act('pb_show', task=tid)
        for i in [0] + self.j.get(tid)['want'][:3]:
            self.j.act('pb_pick', task=tid, i=i)
        self.decorate(tid)
        self.j.act('pb_print', task=tid)
        self.j.act('pb_trim', task=tid)
        self.j.act('pb_serve', task=tid)
        slip = next(x for x in self.j.get(tid)['slips'] if x['code'] == 'bad_shot')
        self.assertEqual(slip['sev'], 3)                     # chị Vy checks every eye

    def test_printing_without_letting_them_choose(self):
        t = self.at(*find('Hội bạn 11A1 tan học'))
        tid = t['id']
        self.j.act('ask', task=tid)
        self.set_up(tid)
        self.shoot(tid)
        for i in range(4):
            self.j.act('pb_pick', task=tid, i=i)
        self.decorate(tid)
        self.j.act('pb_print', task=tid)
        self.j.act('pb_trim', task=tid)
        self.j.act('pb_serve', task=tid)
        self.assertIn('no_choice', self.codes(tid))

    def test_stickers_date_and_colour_follow_the_words(self):
        t = self.at(*find('Ông bà Chín kỷ niệm 50 năm'))     # no stickers, a date, sepia
        self.make(t['id'], st=['tim'], date=False, flt='none')
        self.j.act('pb_serve', task=t['id'])
        self.assertTrue({'sticker', 'date', 'filter'} <= self.codes(t['id']))
        t = self.at(*find('Hội bạn 11A1 tan học'))           # free stickers: extras are welcome
        self.make(t['id'], st=['tim', 'sao', 'meo', 'tho'])
        self.j.act('pb_serve', task=t['id'])
        self.assertNotIn('sticker', self.codes(t['id']))

    def test_wrong_package_is_charged_at_the_cheaper_one(self):
        t = self.at(*find('Anh Khôi chị Vy hẹn hò'))           # double
        self.make(t['id'], pkg='strip')
        self.j.act('pb_serve', task=t['id'])
        self.assertIn('pkg', self.codes(t['id']))
        self.assertEqual(self.j.get(t['id'])['price'], PB.PRICES['strip'])

    def test_a_reprint_bins_the_first_sheet(self):
        t = self.at(*find('Hội bạn 11A1 tan học'))
        tid = t['id']
        self.make(tid, flt='den_trang')
        paper = kit.stock(self.j.c, 'giay_dai')
        self.assertTrue(self.j.get(tid)['trim'])
        with self.assertRaises(GameError):
            self.j.act('pb_filter', task=tid, flt='none')           # trimmed: too late
        t = self.at(*find('Hội bạn 11A1 tan học'))
        tid = t['id']
        self.j.act('ask', task=tid)
        self.set_up(tid)
        self.shoot(tid)
        self.j.act('pb_show', task=tid)
        for i in self.j.get(tid)['want']:
            self.j.act('pb_pick', task=tid, i=i)
        self.decorate(tid, flt='den_trang')
        self.j.act('pb_print', task=tid)
        paper = kit.stock(self.j.c, 'giay_dai')
        self.j.act('pb_filter', task=tid, flt='none')
        self.j.act('pb_print', task=tid)
        self.assertEqual(kit.stock(self.j.c, 'giay_dai'), paper - 1)
        self.assertEqual(self.d['today']['reprints'], 1)
        self.assertEqual(self.j.get(tid)['prints'], 2)
        self.j.act('pb_trim', task=tid)
        self.serve_pay(tid)
        self.assertEqual(self.codes(tid), set())

    def test_pick_and_print_limits(self):
        t = self.at(*find('Ông bà Chín kỷ niệm 50 năm'))       # big: one shot
        tid = t['id']
        self.j.act('ask', task=tid)
        self.set_up(tid)
        self.shoot(tid, good=2)
        self.j.act('pb_pick', task=tid, i=0)
        with self.assertRaises(GameError):
            self.j.act('pb_pick', task=tid, i=1)
        self.j.act('pb_pick', task=tid, i=0)
        with self.assertRaises(GameError):
            self.j.act('pb_print', task=tid)                       # nothing picked
        with self.assertRaises(GameError):
            self.j.act('pb_serve', task=tid)

    def test_out_of_paper_is_said_honestly(self):
        t = self.at(*find('Ông bà Chín kỷ niệm 50 năm'))
        kit.take(self.j.c, 'giay_lon', kit.stock(self.j.c, 'giay_lon'))
        self.j.act('ask', task=t['id'])
        self.set_up(t['id'])
        self.shoot(t['id'])
        self.j.act('pb_show', task=t['id'])
        self.j.act('pb_pick', task=t['id'], i=self.j.get(t['id'])['want'][0])
        self.decorate(t['id'])
        with self.assertRaises(GameError):
            self.j.act('pb_print', task=t['id'])
        money = self.j.c['money']
        self.j.act('pb_decline', task=t['id'])
        self.assertEqual(self.j.get(t['id'])['status'], 'completed')
        self.assertEqual(self.j.c['money'], money)

    def test_short_pay_and_wallet_never_below_zero(self):
        t = self.at(*find('Hội bạn 11A1 tan học'))
        self.make(t['id'])
        self.j.act('pb_serve', task=t['id'])
        rec = self.j.get(t['id'])['cash']
        self.j.act('pb_pay', task=t['id'], change=till.greedy(max(0, till.due(rec))) + [500])   # far too much change back
        self.assertGreaterEqual(self.j.c['money'], 0)
        with self.assertRaises(GameError):
            self.j.act('pb_pay', task=t['id'], change=[])


class Apprenticeship(Base):
    def test_chi_lam_stops_a_wrong_frame_once_before_it_is_printed(self):
        t = self.at(*find('Hội bạn 11A1 tan học'), learning=True)
        tid = t['id']
        self.j.act('ask', task=tid)
        self.set_up(tid, frame='tet')
        self.shoot(tid)
        self.j.act('pb_show', task=tid)
        for i in self.j.get(tid)['want']:
            self.j.act('pb_pick', task=tid, i=i)
        self.decorate(tid)
        paper = kit.stock(self.j.c, 'giay_dai')
        r = self.j.act('pb_print', task=tid)
        self.assertIn('Chị Lam', r['message'])
        self.assertEqual(r.get('lesson'), 'frame')
        self.assertIsNone(self.j.get(tid)['printed'])
        self.assertEqual(kit.stock(self.j.c, 'giay_dai'), paper)
        self.j.act('pb_print', task=tid)                          # the same mistake again goes through
        self.assertIsNotNone(self.j.get(tid)['printed'])

    def test_three_customers_and_she_lets_you_stand_alone(self):
        t = self.at(*find('Hội bạn 11A1 tan học'), learning=True)
        self.assertTrue(PB.public_data(self.j.c)['learn']['on'])
        for n in range(PB.APPRENTICE):
            if n:
                t = make_task('photobooth', 2, n + 1, 1)
                self.j.c['tasks'].append(t)
                PB.on_task(self.j.state, self.j.c, t)
                self.j.c['active_task'] = t['id']
            r = None
            self.make(t['id'])
            r = self.serve_pay(t['id'])
        self.assertIn('Học nghề xong', r['message'])
        self.assertTrue(self.d['learn']['done'])
        self.assertFalse(PB.public_data(self.j.c)['learn']['on'])


class Days(Base):
    def play_day(self):
        self.settle_desk()
        for t in [t for t in self.j.c['tasks'] if t['status'] not in ('completed', 'cancelled')]:
            self.settle_desk()
            if t['kind'] == 'setup':
                self.j.act('pb_lens')
                self.j.act('pb_test')
                if self.d['ribbon'] < 10:
                    self.j.act('pb_ribbon')
                self.j.act('pb_open', task=t['id'])
                continue
            self.make(t['id'])
            self.settle_desk()
            if self.d['booth']['fog']:
                self.j.act('pb_lens')
            self.serve_pay(t['id'])
        self.settle_desk()
        r = self.j.act('end_day', carry_event=True)
        self.j.act('start_day')
        validate_state(self.j.state)
        return r

    def test_ten_days_of_play_stay_valid(self):
        self.j = Journey('photobooth')
        self.j.act('pb_intro')
        for _ in range(10):
            for x in PB.ITEMS:
                if kit.stock(self.j.c, x['id']) < 6:
                    kit.add_lot(self.j.c, x['id'], 8, x['cost'], 30, 'test')
            r = self.play_day()
            car = r['summary']['career']
            self.assertIn('lines', car)
            self.assertIn('tomorrow', car)
        self.assertGreater(self.d['stats']['customers'], 10)
        self.assertGreater(self.d['stats']['good'], 0)
        v = public_state(self.j.state)
        json.dumps(v['careers']['photobooth'])

    def test_public_task_hides_the_order_until_asked(self):
        t = self.at(*find())
        v = PB.public_task(t)
        self.assertIsNone(v['needs'])
        self.j.act('ask', task=t['id'])
        v = PB.public_task(self.j.get(t['id']))
        self.assertEqual(v['needs']['pkg'], t['needs']['pkg'])
        self.assertEqual(set(v['beat']), {'count', 'lead', 'hold', 'blink', 'recharge'})

    def test_validator_rejects_tampering(self):
        t = self.at(*find('Hội bạn 11A1 tan học'))
        self.j.act('ask', task=t['id'])
        self.set_up(t['id'])
        self.snap(t['id'])
        validate_state(self.j.state)
        task = lambda s: next(x for x in s['careers']['photobooth']['tasks'] if x['id'] == t['id'])
        for mutate in (lambda s: task(s)['shots'][0].update(q='perfect'),
                       lambda s: task(s)['shots'].extend([dict(task(s)['shots'][0])] * 9),
                       lambda s: task(s)['set'].update(frame='disco'),
                       lambda s: task(s).update(pick=[7]),
                       lambda s: task(s)['deco'].update(st=['tim', 'tim']),
                       lambda s: s['careers']['photobooth']['ext']['data'].update(ribbon=99),
                       lambda s: s['careers']['photobooth']['ext']['data']['booth'].update(lens='yes'),
                       lambda s: task(s)['needs'].update(pkg='big')):
            bad = copy.deepcopy(self.j.state)
            mutate(bad)
            with self.assertRaises(GameError):
                validate_state(bad)


class OldSaves(Base):
    def story_save(self):
        s = new_state()
        jr.enable_story(s, 77)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        s, _ = apply_action(s, 'milk_tea', 'start_day', {})
        return s

    def test_a_save_without_the_shop_gains_it_fresh_and_nothing_else_moves(self):
        s = self.story_save()
        s['careers'].pop('photobooth')
        s['journey']['chapter'] = 3
        s['journey']['unlocked'] = [cid for n in range(1, 4) for cid in jr.CH_UNLOCKS[n] if cid in s['careers']]
        s['journey']['done'] = [1, 2]
        before = {cid: json.dumps(c, sort_keys=True, ensure_ascii=False) for cid, c in s['careers'].items()}
        m = migrate_state(json.loads(json.dumps(s)))
        validate_state(m)
        self.assertEqual(json.dumps(m['careers']['photobooth'], sort_keys=True), json.dumps(initial_career('photobooth'), sort_keys=True))
        for cid, raw in before.items():
            self.assertEqual(json.dumps(m['careers'][cid], sort_keys=True, ensure_ascii=False), raw, cid)
        self.assertIn('photobooth', m['journey']['unlocked'])

    def test_data_from_an_older_build_fills_in(self):
        t = self.at(*find())
        for k in ('learn', 'regulars', 'stats'):
            self.d.pop(k)
        self.d['booth'].pop('fog')
        self.j.act('ask', task=t['id'])
        validate_state(self.j.state)


# Careers this release adds next to the photo shop (the old tree knows none of them): a rollback takes them all out.
ADDED = ('pho', 'com', 'photobooth', 'giupviec', 'naucom', 'babysitter', 'library', 'oil', 'railway', 'nurse', 'rescue')
OLD_TREE = os.environ.get('MNL_OLD_TREE')     # a 1aba75d checkout (git archive 1aba75d game | tar -x -C DIR)
OLD_CHECK = r'''
import json, sys
from game.engine import migrate_state, validate_state, GameError
s = json.load(open(sys.argv[1], encoding='utf-8'))
try:
    validate_state(migrate_state(s))
    print('ok')
except GameError as e:
    print('rejected:', e)
'''


@unittest.skipUnless(OLD_TREE and Path(OLD_TREE, 'game', 'engine.py').exists(), 'set MNL_OLD_TREE to a 1aba75d tree')
class Release1aba75d(Base):
    """Saves across the rolling release: 1aba75d → here, and here → 1aba75d (a rollback)."""

    def run_old(self, state):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp, 's.json')
            p.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
            env = dict(os.environ, PYTHONPATH=OLD_TREE)
            env.pop('MNL_CAREERS', None)
            out = subprocess.run([sys.executable, '-c', OLD_CHECK, str(p)], cwd=OLD_TREE, env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            return out.stdout.strip().splitlines()[-1]

    def old_save(self):
        """A save made by 1aba75d itself: a story player one day into milk tea."""
        code = r'''
import json
from game import journey as jr
from game.engine import new_state, apply_action
s = new_state(); jr.enable_story(s, 77)
s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
s, _ = apply_action(s, 'milk_tea', 'select_career', {})
s, _ = apply_action(s, 'milk_tea', 'start_day', {})
print(json.dumps(s, ensure_ascii=False))
'''
        env = dict(os.environ, PYTHONPATH=OLD_TREE)
        env.pop('MNL_CAREERS', None)
        out = subprocess.run([sys.executable, '-c', code], cwd=OLD_TREE, env=env, capture_output=True, text=True, timeout=120, encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        return json.loads(out.stdout)

    def test_a_1aba75d_save_loads_here(self):
        s = self.old_save()
        self.assertNotIn('photobooth', s['careers'])
        m = migrate_state(s)
        validate_state(m)
        self.assertIn('photobooth', m['careers'])
        for cid in s['careers']:
            self.assertIn(cid, m['careers'])
        for cid in ADDED:
            self.assertNotIn(cid, s['careers'])
            self.assertIn(cid, m['careers'])

    def test_a_save_from_here_goes_back_without_the_new_shop(self):
        """1aba75d rejects a save that names a career it does not know (the same for every career added since:
        ice cream, nail, pagoda; docs/DEPLOY_ROLLING.md "Two versions at once"): only a rollback meets it.
        Everything else in a save played here, the photobooth block taken out, still loads there."""
        s = OldSaves.story_save(self)                       # a milk tea player on this build
        self.assertIn('photobooth', s['careers'])
        self.assertTrue(self.run_old(s).startswith('rejected'))
        for cid in ADDED:
            s['careers'].pop(cid)
        self.assertEqual(self.run_old(s), 'ok')
        self.j = Journey('photobooth')                     # someone standing in the photo shop has no way back
        self.j.act('pb_intro')
        self.assertTrue(self.run_old(json.loads(json.dumps(self.j.state))).startswith('rejected'))


if __name__ == '__main__':
    unittest.main()
