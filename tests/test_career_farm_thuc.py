"""Nông trại: phân bón lá thúc (fa_boost) — the cap, the price, the wallet, the money it makes, saves."""
import copy
import json
import unittest

import game.careers.kit as kit
from game.engine import GameError, public_state, validate_state
from game.careers import farm as F
from tests.helpers import Journey

NEUTRAL = dict(muong=6, lettuce=10, tomato=2, cucumber=2, herbs=2)   # a day whose season neither helps nor hurts the crop
SEASON_DAY = (2, 6, 10, 14)                                         # spring, summer, autumn, winter


def data(j):
    return j.c['ext']['data']


def plot(j, pid):
    return data(j)['plots'][F.PLOT_IDS.index(pid)]


def view(j, pid):
    return next(p for p in public_state(j.state)['careers']['farm']['data']['plots'] if p['id'] == pid)


def roundtrip(j):
    validate_state(json.loads(json.dumps(j.state)))


def sow(j, pid='P6', crop='muong'):
    data(j)['desk'].update(day=j.c['day'], plan=[], fired=0)       # no surprise unless asked for
    if plot(j, pid)['crop']:
        j.act('fa_clear', plot=pid, confirm=True)
    plot(j, pid).update(soil=60, prev=None, moisture=60)
    j.act('fa_plant', plot=pid, crop=crop)
    return plot(j, pid)


def cycle(crop, day, sow_beat=1, pct=0, compost=False, npk=False, boost_at=0):
    """Game-clock hours from sowing to ripe with full care, with the game's own beats and nights;
    pct% thúc sprayed boost_at beats after sowing (the floor counted as fa_boost counts it)."""
    plots = [F._plot(pid) for pid in F.PLOT_IDS]
    p = plots[0]
    p.update(crop=crop, growth=F.CROP_INDEX[crop]['start'], planted=day, compost=compost, soil=60, moisture=60)
    if npk:
        p.update(npk=True, growth=p['growth'] + 15, organic=False)
    turn, beat, cur, waited = sow_beat, sow_beat, day, 0
    d = dict(plots=plots, market=dict(day=day, start=0))
    c = dict(day=day, turn=turn, ext={})
    while cur < day + 8:
        if pct and waited >= boost_at and F.THUC_KEY not in c['ext']:
            c.update(day=cur, turn=turn)
            now = F._clock(cur, beat)
            floor = now + (F._ripe_at(c, d, p) - now) * (100 - F.THUC_MAX) // 100
            c['ext'][F.THUC_KEY] = {'P1': dict(crop=crop, day=day, pct=pct, floor=floor)}
        if p['growth'] >= F.RIPE:
            return ((cur - day) * 24 * 60 + (beat - sow_beat) * F.BEAT_MIN) / 60
        if beat < F.SHIFT_BEATS:
            p.update(moisture=60, weeds=0, pests=0)
            turn, beat, waited = turn + 1, beat + 1, waited + 1
            F._step(d, turn, F.WEATHER[0], cur, F._fed(c, d))
            continue
        c['day'] = cur
        p.update(moisture=60, pests=0)
        F._night(c, d, F.WEATHER[0])
        cur, beat = cur + 1, 0
        d['market'].update(day=cur, start=turn)
    return None


def wholesale(crop, qty):
    """What the wholesale market pays for a crop's yield on a day of usual prices (index 100), with the slip."""
    v = F.PRICES[crop] * 100 * F.WHOLESALE // 1000
    return max(1, (sum(max(1, v * max(50, 100 - 10 * (i // F.SLIP)) // 100) for i in range(qty)) + 5) // 10)


class ThucDoseTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey('farm')
        self.assertEqual(F._weather(self.j.c['day'])['id'], 'sun')

    def test_a_dose_costs_xu_and_soil_keeps_organic_and_is_logged(self):
        j = self.j
        p = sow(j)
        money, soil = j.c['money'], p['soil']
        r = j.act('fa_boost', plot='P6', pct=30, confirm=True)
        self.assertEqual(j.c['money'], money - F._thuc_cost(0, 30))
        self.assertEqual(F._thuc_cost(0, 30), sum(F.THUC_COST[:3]))
        self.assertEqual(plot(j, 'P6')['soil'], soil - 3 * F.THUC_SOIL)
        self.assertTrue(plot(j, 'P6')['organic'])
        rec = j.c['ext'][F.THUC_KEY]['P6']
        self.assertEqual((rec['crop'], rec['day'], rec['pct']), ('muong', j.c['day'], 30))
        self.assertIn('thời gian lớn còn 70%', r['message'])
        self.assertIn('thúc', data(j)['diary'][-1]['text'])
        self.assertEqual(j.c['metrics'].get('fa_boosted'), 1)
        # a second dose costs the next doses in the price list, the floor stays the first one's
        floor = rec['floor']
        j.act('fa_boost', plot='P6', pct=20, confirm=True)
        self.assertEqual(j.c['money'], money - F._thuc_cost(0, 50))
        self.assertEqual(j.c['ext'][F.THUC_KEY]['P6']['pct'], 50)
        self.assertEqual(j.c['ext'][F.THUC_KEY]['P6']['floor'], floor)
        roundtrip(j)

    def test_prices_rise_dose_by_dose(self):
        self.assertEqual(len(F.THUC_COST), F.THUC_MAX // F.THUC_STEP)
        self.assertEqual(list(F.THUC_COST), sorted(F.THUC_COST))
        self.assertEqual(F._thuc_cost(40, 30), sum(F.THUC_COST[4:7]))
        self.assertEqual(F._thuc_cost(0, 70), sum(F.THUC_COST))

    def test_never_beyond_70_percent(self):
        j = self.j
        sow(j)
        j.act('fa_boost', plot='P6', pct=50, confirm=True)
        for pct in (30, 80):
            with self.assertRaises(GameError):
                j.act('fa_boost', plot='P6', pct=pct, confirm=True)
        j.act('fa_boost', plot='P6', pct=20, confirm=True)
        self.assertEqual(j.c['ext'][F.THUC_KEY]['P6']['pct'], F.THUC_MAX)
        with self.assertRaises(GameError) as e:
            j.act('fa_boost', plot='P6', pct=10, confirm=True)
        self.assertIn('70%', str(e.exception))
        v = view(j, 'P6')['thuc']
        self.assertEqual((v['pct'], v['room'], v['options']), (70, 0, []))
        self.assertIn('70%', v['why'])
        # the pace: exactly the dose off the growing time, and never more than 70%
        for pct in range(0, F.THUC_MAX + 1, F.THUC_STEP):
            self.assertGreaterEqual(100 / F._speed(pct), (100 - pct) / 100)          # rounding only ever cuts less
            self.assertAlmostEqual(100 / F._speed(pct), (100 - pct) / 100, delta=0.005)
        self.assertGreaterEqual(100 / F._speed(F.THUC_MAX), 0.3)

    def test_doses_must_be_whole_and_confirmed(self):
        j = self.j
        sow(j)
        for bad in (dict(pct=15, confirm=True), dict(pct=0, confirm=True), dict(pct='x', confirm=True), dict(pct=10)):
            with self.assertRaises(GameError):
                j.act('fa_boost', plot='P6', **bad)
        with self.assertRaises(GameError):
            j.act('fa_boost', plot='P9', pct=10, confirm=True)
        self.assertNotIn(F.THUC_KEY, j.c['ext'])

    def test_refusals_say_why_and_the_view_disables_the_doses(self):
        j = self.j
        sow(j)
        # an empty bed
        j.act('fa_clear', plot='P6', confirm=True)
        with self.assertRaises(GameError) as e:
            j.act('fa_boost', plot='P6', pct=10, confirm=True)
        self.assertIn('Luống trống', str(e.exception))
        self.assertIsNone(view(j, 'P6')['thuc'])
        # a ripe bed
        with self.assertRaises(GameError) as e:
            j.act('fa_boost', plot='P1', pct=10, confirm=True)
        self.assertIn('tới lứa', str(e.exception))
        self.assertFalse(any(o['ok'] for o in view(j, 'P1')['thuc']['options']))
        # a dry bed
        p = sow(j)
        p['moisture'] = F.MOIST_DRY - 5
        v = view(j, 'P6')['thuc']
        self.assertIn('tưới trước', v['why'])
        self.assertTrue(v['options'] and not any(o['ok'] for o in v['options']))
        with self.assertRaises(GameError):
            j.act('fa_boost', plot='P6', pct=10, confirm=True)
        # a short wallet: nothing taken, the dear dose disabled, the cheap one still there
        p['moisture'] = 60
        kit.money(j.state, j.c, F._thuc_cost(0, 10) - j.c['money'], 'Chi tiêu khác', None, 'stock')
        v = view(j, 'P6')['thuc']
        ok = {o['pct']: o['ok'] for o in v['options']}
        self.assertEqual(ok, {10: True, 30: False, 70: False})
        self.assertIn('Ví chưa đủ', next(o['why'] for o in v['options'] if not o['ok']))
        with self.assertRaises(GameError) as e:
            j.act('fa_boost', plot='P6', pct=30, confirm=True)
        self.assertIn('xu', str(e.exception))
        self.assertEqual(j.c['money'], F._thuc_cost(0, 10))
        j.act('fa_boost', plot='P6', pct=10, confirm=True)
        self.assertEqual(j.c['money'], 0)                       # the wallet never goes below zero
        self.assertFalse(any(o['ok'] for o in view(j, 'P6')['thuc']['options']))

    def test_no_spraying_in_the_rain(self):
        j = self.j
        sow(j)
        rainy = next(d for d in range(2, 80) if F._weather(d)['id'] == 'rain')
        j.c['day'] = rainy
        self.assertIn('mưa', F._thuc_why(j.c, plot(j, 'P6'), 0))
        with self.assertRaises(GameError) as e:
            j.act('fa_boost', plot='P6', pct=10, confirm=True)
        self.assertIn('mưa', str(e.exception))

    def test_view_offers_three_amounts_with_price_and_harvest_day(self):
        j = self.j
        sow(j)
        v = view(j, 'P6')
        self.assertEqual((v['eta'], v['thuc']['pct'], v['thuc']['room']), (2, 0, 70))
        opts = {o['pct']: o for o in v['thuc']['options']}
        self.assertEqual(sorted(opts), [10, 30, 70])
        self.assertEqual({k: o['cost'] for k, o in opts.items()}, {k: F._thuc_cost(0, k) for k in opts})
        self.assertEqual((opts[10]['eta'], opts[30]['eta'], opts[70]['eta']), (2, 1, 1))
        self.assertTrue(all(o['ok'] and o['why'] is None for o in opts.values()))
        j.act('fa_boost', plot='P6', pct=30, confirm=True)
        v = view(j, 'P6')
        self.assertEqual((v['eta'], v['thuc']['pct'], v['thuc']['room']), (1, 30, 40))
        self.assertEqual(sorted(o['pct'] for o in v['thuc']['options']), [10, 30, 40])
        self.assertEqual(v['cap'], F.CROP_INDEX['muong']['cap'] * F._speed(30) // 100)   # the day's budget shows the pace

    def test_offered_harvest_day_is_the_one_the_dose_gives(self):
        """The beds the farm starts with (and later ones): each option's harvest day is what
        fa_boost then reports, counted from the beat the dose is sprayed in."""
        for warm in (0, 5):
            for pid in F.PLOT_IDS:
                for want in (10, 30, 70):
                    j = Journey('farm')
                    j.act('ask', task=j.task['id'])
                    for _ in range(warm):
                        j.act('fa_scout', plot='P1')
                    v = view(j, pid)
                    if not v['thuc'] or v['thuc']['why']:
                        continue
                    o = next((o for o in v['thuc']['options'] if o['pct'] == want), None)
                    if not o:
                        continue
                    msg = j.act('fa_boost', plot=pid, pct=want, confirm=True)['message']
                    got = view(j, pid)['eta']
                    with self.subTest(warm=warm, plot=pid, pct=want):
                        self.assertEqual(o['eta'], got)
                        if got is not None:
                            self.assertIn('hôm nay' if got == 0 else f'{got} ngày nữa', msg)

    def test_fed_bed_is_ripe_the_next_morning_not_the_same_day(self):
        j = self.j
        sow(j)
        j.act('fa_boost', plot='P6', pct=50, confirm=True)
        for _ in range(F.SHIFT_BEATS):
            plot(j, 'P6').update(moisture=60, weeds=0)
            j.act('fa_scout', plot='P6')
        self.assertLess(plot(j, 'P6')['growth'], F.YOUNG)      # cannot be picked on the day it was sown
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertGreaterEqual(plot(j, 'P6')['growth'], F.RIPE)
        self.assertLess(plot(j, 'P6')['growth'], F.OVER)      # the boost stops at ripeness: no over-ripe morning
        data(j)['desk']['ev'] = None
        plot(j, 'P6').update(pests=0, stress=0, weeds=0)
        j.act('fa_harvest', plot='P6', confirm=True)
        lot = data(j)['cold'][-1]
        self.assertEqual((lot['crop'], lot['grade'], lot['qty'], lot['organic']), ('muong', 'A', 8, True))
        self.assertNotIn(F.THUC_KEY, j.c['ext'])                # the doses went with the crop
        roundtrip(j)

    def test_doses_belong_to_the_crop(self):
        j = self.j
        sow(j)
        j.act('fa_boost', plot='P6', pct=30, confirm=True)
        j.act('fa_clear', plot='P6', confirm=True)
        self.assertNotIn(F.THUC_KEY, j.c['ext'])
        sow(j)
        self.assertEqual(view(j, 'P6')['thuc']['pct'], 0)
        # a record left behind (an older server harvested and sowed again) counts for nothing
        j.c['ext'][F.THUC_KEY] = {'P6': dict(crop='tomato', day=j.c['day'], pct=70, floor=0)}
        self.assertEqual((F._thuc(j.c, plot(j, 'P6')), F._fed(j.c, data(j))), (0, {}))
        roundtrip(j)


class ThucCapTests(unittest.TestCase):
    def test_clock_time_cut_never_beyond_70_percent(self):
        """Every crop, season, sowing time, compost/NPK and moment of spraying: a fed bed needs at least
        30% of the game-clock time the same bed needs without thúc."""
        worst = 1.0
        for crop in F.CROP_INDEX:
            for day in SEASON_DAY:
                for sow_beat in (0, 12, 30, 34, 36):
                    for compost, npk in ((False, False), (True, False), (True, True)):
                        base = cycle(crop, day, sow_beat, 0, compost, npk)
                        for at in (0, 20):
                            for pct in (20, 50, 70):
                                h = cycle(crop, day, sow_beat, pct, compost, npk, at)
                                self.assertIsNotNone(h)
                                self.assertLessEqual(h, base)
                                worst = min(worst, h / base)
        self.assertGreaterEqual(worst, 0.3 - 1e-9)

    def test_ripe_produce_ages_at_its_own_pace(self):
        p = F._plot('P1', 'muong', F.RIPE + 5, 60, soil=60)
        self.assertEqual(F._cap(p, F._speed(70)), F._cap(p))
        self.assertEqual(F._night_growth(p, 2, F._speed(70)), F._night_growth(p, 2))
        q = F._plot('P1', 'muong', 95, 60, soil=60)
        self.assertEqual(q['growth'] + F._night_growth(q, 2, F._speed(70)), q['growth'] + F.NIGHT_GROWTH)   # no jump past ripe


class ThucMoneyTests(unittest.TestCase):
    """At the usual prices: a fed crop earns less per crop but at least as much per day, never a loss."""

    def test_profitable_for_every_crop(self):
        for crop, day in NEUTRAL.items():
            x = F.CROP_INDEX[crop]
            seed = next(i['cost'] for i in F.ITEMS if i['id'] == x['seed'])
            soil_xu = F.THUC_SOIL * (F.THUC_MAX // F.THUC_STEP) * 4 / F.SOIL_ADD['compost']   # soil bought back with compost
            base_h = cycle(crop, day)
            for price in (wholesale(crop, x['yield_']), F.PRICES[crop] * x['yield_']):
                base = price - seed
                with self.subTest(crop=crop, price=price):
                    for pct in range(F.THUC_STEP, F.THUC_MAX + 1, F.THUC_STEP):
                        h = cycle(crop, day, pct=pct)
                        profit = base - F._thuc_cost(0, pct) - soil_xu * pct / F.THUC_MAX
                        self.assertGreater(profit, 0)                         # never a loss
                        self.assertLess(profit, base)                         # each crop earns a bit less
                    top = base - F._thuc_cost(0, F.THUC_MAX) - soil_xu
                    self.assertGreaterEqual(top / cycle(crop, day, pct=F.THUC_MAX), base / base_h * 0.98)   # per day: as much or more
                    best = max((base - F._thuc_cost(0, k)) / cycle(crop, day, pct=k) for k in range(10, 71, 10))
                    self.assertGreater(best, base / base_h * 1.3)            # the right dose pays clearly


class ThucSaveTests(unittest.TestCase):
    def test_round_trip_and_tampering(self):
        j = Journey('farm')
        sow(j)
        j.act('fa_boost', plot='P6', pct=30, confirm=True)
        roundtrip(j)
        # the farm's own data keeps the exact shape older servers check key by key
        d = data(j)
        self.assertEqual(set(d), {'turn', 'seq', 'plots', 'cold', 'coop', 'diary', 'stats', 'desk', 'market', 'pledge'})
        self.assertEqual(set(d['plots'][5]), set(F._plot('P1')))
        for bad in ({'P6': dict(crop='muong', day=1, pct=75, floor=0)}, {'P6': dict(crop='muong', day=1, pct=80, floor=0)},
                    {'P6': dict(crop='rice', day=1, pct=30, floor=0)}, {'P9': dict(crop='muong', day=1, pct=30, floor=0)},
                    {'P6': dict(crop='muong', day=1, pct=30)}, {'P6': dict(crop='muong', day=0, pct=30, floor=0)}, []):
            s = copy.deepcopy(j.state)
            s['careers']['farm']['ext'][F.THUC_KEY] = bad
            with self.subTest(bad=bad), self.assertRaises(GameError):
                validate_state(json.loads(json.dumps(s)))

    def test_old_save_without_doses_loads_and_plays(self):
        j = Journey('farm')
        j.c['ext'].pop(F.THUC_KEY, None)
        roundtrip(j)
        self.assertTrue(all(p['thuc'] is None or p['thuc']['pct'] == 0 for p in public_state(j.state)['careers']['farm']['data']['plots']))
        sow(j)
        j.act('fa_boost', plot='P6', pct=10, confirm=True)
        roundtrip(j)


if __name__ == '__main__':
    unittest.main()
