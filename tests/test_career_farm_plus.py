"""🌟 Trang trại (game/careers/farm_plus.py): wall-clock garden, pens, buyers, upgrades, and the all-beds chores."""
import copy
import json
import unittest

import game.careers.kit as kit
from game.careers import farm_plus as fp
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey

T0 = 1_800_000_000.0


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self._old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self._old

    def wait(self, sec):
        self.clock.t += sec

    def farm(self, **over):
        j = Journey('farm')
        j.act('fa_v_open')
        g = self.g(j)
        for k, v in over.items():
            g[k] = v
        return j

    @staticmethod
    def g(j):
        return j.c['ext'][fp.KEY]

    @staticmethod
    def roundtrip(j):
        validate_state(json.loads(json.dumps(j.state)))

    def view(self, j):
        return public_state(j.state)['careers']['farm']['data']['plus']

    def grow(self, j, i, care=True):
        """Wait until plot i is ripe, doing each need as it comes up (care=True)."""
        pl = self.g(j)['plots'][i]
        end = pl['at'] + pl['dur']
        while self.clock.t < end:
            self.wait(15)
            pl = self.g(j)['plots'][i]
            for k in fp._due(pl, int(self.clock.t)) if care else []:
                j.act('fa_v_care', plot=i, need=k)


class OpenAndSaves(Base):
    def test_saves_without_the_garden_still_load(self):
        j = Journey('farm')
        self.assertNotIn(fp.KEY, j.c['ext'])
        self.roundtrip(j)
        self.assertEqual(self.view(j), dict(open=False, now=int(T0)))

    def test_open_once_and_roundtrip(self):
        j = self.farm()
        g = self.g(j)
        self.assertEqual(len(g['plots']), fp.START_PLOTS)
        self.assertGreaterEqual(len(g['orders']), 2)       # one buyer each; a new farm sells ớt and lúa only
        self.roundtrip(j)
        with self.assertRaises(GameError):
            j.act('fa_v_open')

    def test_garden_actions_take_no_beat_and_need_the_garden(self):
        j = Journey('farm')
        with self.assertRaises(GameError):
            j.act('fa_v_plant', plot=0, crop='ot')
        j.act('fa_v_open')
        turn = j.c['turn']
        j.act('fa_v_plant', plot=0, crop='ot')
        self.assertEqual(j.c['turn'], turn)

    def test_view_hides_the_buyers_trait(self):
        j = self.farm()
        for o in self.view(j)['orders']:
            self.assertNotIn('trait', o)
        self.assertNotIn('trait', json.dumps(self.view(j)))

    def test_corrupt_garden_is_refused(self):
        j = self.farm()
        bad = copy.deepcopy(j.state)
        bad['careers']['farm']['ext'][fp.KEY]['plots'] = [None] * 9
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(j.state)
        bad['careers']['farm']['ext'][fp.KEY]['ups'] = ['drip', 'drip']
        with self.assertRaises(GameError):
            validate_state(bad)


class Garden(Base):
    def test_grow_on_the_wall_clock_with_care_gives_grade_a(self):
        j = self.farm()
        money = j.c['money']
        j.act('fa_v_plant', plot=0, crop='ot')
        self.assertEqual(j.c['money'], money - fp.CROP['ot']['seed'])
        with self.assertRaises(GameError):
            j.act('fa_v_harvest', plot=0)            # not ripe yet
        self.grow(j, 0)
        self.assertEqual(self.view(j)['plots'][0]['stage'], 'ripe')
        xp = self.g(j)['xp']
        j.act('fa_v_harvest', plot=0)
        a, b = self.g(j)['store']['ot']
        self.assertEqual(b, 0)
        self.assertGreaterEqual(a, fp.CROP['ot']['qty'])
        self.assertGreater(self.g(j)['xp'], xp)
        self.assertIsNone(self.g(j)['plots'][0])
        self.roundtrip(j)

    def test_missed_needs_cost_yield_and_grade(self):
        j = self.farm()
        j.act('fa_v_plant', plot=0, crop='lua')
        self.grow(j, 0, care=False)
        j.act('fa_v_harvest', plot=0)
        a, b = self.g(j)['store']['lua']
        self.assertEqual(a, 0)
        self.assertLess(b, fp.CROP['lua']['qty'])

    def test_care_only_when_the_need_has_come_up(self):
        j = self.farm()
        j.act('fa_v_plant', plot=0, crop='lua')
        kind = self.g(j)['plots'][0]['needs'][0][0]
        with self.assertRaises(GameError):
            j.act('fa_v_care', plot=0, need=kind)
        self.wait(self.g(j)['plots'][0]['dur'])
        j.act('fa_v_care', plot=0, need=kind)
        with self.assertRaises(GameError):
            j.act('fa_v_care', plot=0, need=kind)    # once

    def test_left_too_long_goes_over_and_drops_to_b(self):
        j = self.farm()
        j.act('fa_v_plant', plot=0, crop='ot')
        self.grow(j, 0)
        pl = self.g(j)['plots'][0]
        self.wait(fp._keep(pl) + 60)
        self.assertEqual(self.view(j)['plots'][0]['stage'], 'over')
        j.act('fa_v_harvest', plot=0)
        self.assertEqual(self.g(j)['store']['ot'][0], 0)

    def test_locked_crops(self):
        j = self.farm()
        with self.assertRaises(GameError):
            j.act('fa_v_plant', plot=0, crop='cafe')        # level 5
        with self.assertRaises(GameError):
            j.act('fa_v_plant', plot=0, crop='dau')         # greenhouse
        self.g(j)['ups'].append('green')
        j.act('fa_v_plant', plot=0, crop='dau')
        self.assertEqual(self.g(j)['plots'][0]['dur'], fp.CROP['dau']['mins'] * 60 * fp.GREEN_SPEED // 100)

    def test_level_up_and_title(self):
        j = self.farm(xp=fp.LEVELS[4] - 1)
        j.act('fa_v_plant', plot=0, crop='ot')
        self.grow(j, 0)
        r = j.act('fa_v_harvest', plot=0)
        self.assertIn('lên cấp 5', r['message'])
        self.assertIn('Nông dân giỏi', self.view(j)['title'])

    def test_needs_are_fixed_at_sowing(self):
        g = fp.initial(0)
        a = fp._needs_for(g, fp.CROP['tl'], 7, 'rain')
        self.assertEqual(a, fp._needs_for(g, fp.CROP['tl'], 7, 'rain'))
        g['ups'] = ['drip', 'green']
        kinds = {k for k, _ in fp._needs_for(g, fp.CROP['tl'], 7, 'rain')} | {k for k, _ in fp._needs_for(g, fp.CROP['tl'], 7, 'hot')}
        self.assertFalse(kinds & {'water', 'cover'})


class Market(Base):
    def test_price_slips_then_recovers_on_the_clock(self):
        j = self.farm()
        self.g(j)['store'] = dict(lua=[30, 0])
        m = j.c['money']
        j.act('fa_v_sell', item='lua', grade='A', qty=8)
        first = j.c['money'] - m
        self.assertEqual(first, 8 * fp.PRODUCTS['lua']['price'])
        m = j.c['money']
        j.act('fa_v_sell', item='lua', grade='A', qty=8)
        self.assertLess(j.c['money'] - m, first)                 # the chợ is full of lúa
        self.wait(fp.ABSORB * 16)
        m = j.c['money']
        j.act('fa_v_sell', item='lua', grade='A', qty=8)
        self.assertEqual(j.c['money'] - m, first)                # absorbed again
        self.roundtrip(j)

    def test_depth_caps_what_the_market_holds(self):
        j = self.farm()
        self.g(j)['store'] = dict(lua=[fp.DEPTH + 10, 0])
        j.act('fa_v_sell', item='lua', grade='A', qty=fp.DEPTH + 10)
        self.assertEqual(self.g(j)['store']['lua'][0], 10)
        with self.assertRaises(GameError):
            j.act('fa_v_sell', item='lua', grade='A', qty=1)

    def test_grade_b_vietgap_and_festival_prices(self):
        j = self.farm()
        g = self.g(j)
        self.assertEqual(fp._unit_tenths(j.c, g, 'lua', 'B'), 20 * fp.B_PCT // 100)
        g['ups'].append('gap')
        self.assertEqual(fp._unit_tenths(j.c, g, 'lua', 'A'), 20 * fp.GAP_PCT // 100)


class Orders(Base):
    def order(self, j, trait, buyer='comtam', items=None):
        g = self.g(j)
        o = dict(id='D99', buyer=buyer, items=items or {'lua': 4}, pay=20, until=int(self.clock.t) + 3600, line=0, trait=trait, asked=False)
        g['orders'] = [o]
        g['store'] = {k: [q, 0] for k, q in o['items'].items()}
        return o

    def test_fair_buyer_pays_and_takes_the_goods(self):
        j = self.farm()
        self.order(j, 'fair')
        m = j.c['money']
        j.act('fa_v_deliver', order='D99')
        self.assertEqual(j.c['money'] - m, 20)
        self.assertNotIn('lua', self.g(j)['store'])
        self.assertEqual(self.g(j)['stats']['orders'], 1)
        self.roundtrip(j)

    def test_grade_a_buyer_refuses_grade_b(self):
        j = self.farm()
        self.order(j, 'fair', buyer='boba', items={'sua': 4})
        self.g(j)['store'] = dict(sua=[0, 4])
        with self.assertRaises(GameError):
            j.act('fa_v_deliver', order='D99')

    def test_haggle_firm_walks_away_when_you_hold(self):
        j = self.farm()
        self.order(j, 'haggle_firm')
        r = j.act('fa_v_deliver', order='D99')
        self.assertTrue(r.get('haggle'))
        m = j.c['money']
        r = j.act('fa_v_deliver', order='D99', deal='no')
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.c['money'], m)
        self.assertEqual(self.g(j)['store']['lua'], [4, 0])      # goods kept

    def test_haggle_bluff_pays_full_and_a_deal_pays_less(self):
        j = self.farm()
        self.order(j, 'haggle_bluff')
        j.act('fa_v_deliver', order='D99')
        m = j.c['money']
        j.act('fa_v_deliver', order='D99', deal='no')
        self.assertEqual(j.c['money'] - m, 20)
        self.order(j, 'haggle_firm')
        j.act('fa_v_deliver', order='D99')
        m = j.c['money']
        j.act('fa_v_deliver', order='D99', deal='yes')
        self.assertEqual(j.c['money'] - m, 20 * fp.HAGGLE_PCT // 100)

    def test_orders_expire_and_refill(self):
        j = self.farm()
        ids = {o['id'] for o in self.g(j)['orders']}
        self.wait(91 * 60)
        j.act('fa_v_plant', plot=0, crop='ot')
        self.assertFalse(ids & {o['id'] for o in self.g(j)['orders']})
        self.assertGreaterEqual(len(self.g(j)['orders']), 2)

    def test_vietgap_buyer_only_with_the_stamp(self):
        j = self.farm()
        for _ in range(30):
            j.act('fa_v_skip', order=self.g(j)['orders'][0]['id'])
            self.assertNotIn('chay', {o['buyer'] for o in self.g(j)['orders']})


class Upgrades(Base):
    def test_plots_cost_more_each_time_up_to_six(self):
        j = self.farm()
        m = j.c['money']
        j.act('fa_v_buy', up='plot', confirm=True)
        j.act('fa_v_buy', up='plot', confirm=True)
        self.assertEqual(len(self.g(j)['plots']), 4)
        self.assertEqual(m - j.c['money'], fp.PLOT_COST[0] + fp.PLOT_COST[1])
        if j.c['money'] < fp.PLOT_COST[2]:
            with self.assertRaises(GameError):
                j.act('fa_v_buy', up='plot', confirm=True)       # not enough xu
        self.g(j)['plots'] = [None] * fp.MAX_PLOTS
        with self.assertRaises(GameError):
            j.act('fa_v_buy', up='plot', confirm=True)           # six at most
        self.roundtrip(j)

    def test_buy_upgrade_and_gate_vietgap(self):
        j = self.farm()
        m = j.c['money']
        j.act('fa_v_buy', up='drip', confirm=True)
        self.assertEqual(m - j.c['money'], fp.UPGRADE['drip']['cost'])
        with self.assertRaises(GameError):
            j.act('fa_v_buy', up='drip', confirm=True)
        with self.assertRaises(GameError):
            j.act('fa_v_buy', up='gap', confirm=True)            # needs 15 grade-A harvests

    def test_drip_keeps_the_six_beds_watered(self):
        j = self.farm()
        beds = j.c['ext']['data']['plots']
        for p in beds:
            p['moisture'] = 20
        j.act('fa_scout', plot='all')
        self.assertTrue(any(p['moisture'] < 40 for p in j.c['ext']['data']['plots'] if p['crop']))   # no drip yet
        self.g(j)['ups'].append('drip')
        j.act('fa_scout', plot='all')
        self.assertTrue(all(p['moisture'] >= 40 for p in j.c['ext']['data']['plots'] if p['crop']))

    def test_tractor_does_the_whole_garden(self):
        j = self.farm(plots=[None] * 4)
        with self.assertRaises(GameError):
            j.act('fa_v_all', what='plant', crop='ot')
        self.g(j)['ups'].append('tractor')
        j.act('fa_v_all', what='plant', crop='ot')
        self.assertTrue(all(p and p['crop'] == 'ot' for p in self.g(j)['plots']))
        end = self.g(j)['plots'][0]['at'] + self.g(j)['plots'][0]['dur']
        while self.clock.t < end:
            self.wait(20)
            if any(fp._due(p, int(self.clock.t)) for p in self.g(j)['plots']):
                j.act('fa_v_all', what='care')
        j.act('fa_v_all', what='harvest')
        self.assertTrue(all(p is None for p in self.g(j)['plots']))
        self.assertEqual(self.g(j)['stats']['harvests'], 4)
        self.roundtrip(j)


class Pens(Base):
    def test_duck_feed_then_collect(self):
        j = self.farm()
        j.act('fa_v_animal', animal='duck', confirm=True)
        with self.assertRaises(GameError):
            j.act('fa_v_collect', animal='duck')
        j.act('fa_v_feed', animal='duck')
        with self.assertRaises(GameError):
            j.act('fa_v_collect', animal='duck')
        self.wait(fp.ANIMAL['duck']['mins'] * 60)
        j.act('fa_v_collect', animal='duck')
        self.assertEqual(self.g(j)['store']['trung_vit'], [fp.ANIMAL['duck']['qty'], 0])
        self.roundtrip(j)

    def test_barn_gate_and_pig_cycle(self):
        j = self.farm()
        with self.assertRaises(GameError):
            j.act('fa_v_animal', animal='pig', confirm=True)
        self.g(j)['ups'].append('barn')
        j.act('fa_v_animal', animal='pig', confirm=True)
        for k in range(fp.ANIMAL['pig']['feeds']):
            j.act('fa_v_feed', animal='pig')
            with self.assertRaises(GameError):
                j.act('fa_v_feed' if k < 3 else 'fa_v_collect', animal='pig')     # still full
            self.wait(fp.ANIMAL['pig']['mins'] * 60)
        m = j.c['money']
        j.act('fa_v_collect', animal='pig')
        self.assertEqual(j.c['money'] - m, fp.ANIMAL['pig']['sell'])
        self.assertNotIn('pig', self.g(j)['pens'])
        self.roundtrip(j)


class Beds(Base):
    def test_weed_and_scout_all_beds_in_one_beat(self):
        j = Journey('farm')
        beds = j.c['ext']['data']['plots']
        for p in beds:
            p['weeds'] = 2
        turn = j.c['turn']
        j.act('fa_weed', plot='all')
        self.assertEqual(j.c['turn'], turn + 1)
        self.assertTrue(all(p['weeds'] == 0 for p in j.c['ext']['data']['plots']))
        with self.assertRaises(GameError):
            j.act('fa_weed', plot='all')
        j.c['ext']['data']['plots'][1]['pests'] = 2
        r = j.act('fa_scout', plot='all')
        self.assertIn('P2', r['message'])
        planted = [p for p in j.c['ext']['data']['plots'] if p['crop']]
        self.assertTrue(all(p['scouted'] == j.c['turn'] for p in planted))


class Income(Base):
    """Keep the garden in line with the other careers (scripts measured 10/2026: farm orders ≈170 xu a
    player-day; milk tea ≈420, florist ≈770). A bot checking every minute with every upgrade bought must stay
    under 300 xu an hour net, and a new garden under 80."""

    def bot(self, plots, ups, xp, pens, minutes=60):
        j = self.farm(plots=[None] * plots, ups=list(ups), xp=xp)
        for a in pens:
            self.g(j)['pens'][a] = dict(fed=0, n=0)
        m0 = j.c['money']
        end = self.clock.t + minutes * 60
        while self.clock.t < end:
            g, now = self.g(j), int(self.clock.t)
            for i, pl in enumerate(g['plots']):
                if pl:
                    for k in fp._due(pl, now):
                        j.act('fa_v_care', plot=i, need=k)
                    if fp._stage(pl, now) in ('ripe', 'over'):
                        j.act('fa_v_harvest', plot=i)
            for i, pl in enumerate(g['plots']):
                if pl is None:
                    best = max((c for c in fp.CROPS if fp._unlocked(g, c) is None),
                               key=lambda c: ((c['qty'] * c['price'] - c['seed']) * 60 / fp._dur(g, c), c['id']))
                    j.act('fa_v_plant', plot=i, crop=best['id'])
            for a in list(g['pens']):
                A, pen = fp.ANIMAL[a], g['pens'][a]
                ready = pen['fed'] and now >= pen['fed'] + A['mins'] * 60
                if ready and (a != 'pig' or pen['n'] >= A['feeds']):
                    j.act('fa_v_collect', animal=a)
                elif not pen['fed'] or (a == 'pig' and ready):
                    j.act('fa_v_feed', animal=a)
            for o in list(g['orders']):
                if fp._fits(g, o) is None:
                    if j.act('fa_v_deliver', order=o['id']).get('haggle'):
                        j.act('fa_v_deliver', order=o['id'], deal='yes')
            for pid, (a, b) in list(g['store'].items()):
                for grade, have in (('A', a), ('B', b)):
                    if have:
                        try:
                            j.act('fa_v_sell', item=pid, grade=grade, qty=have)
                        except GameError:
                            pass
            self.wait(60)
        g = self.g(j)
        stock = sum(fp.PRODUCTS[k]['price'] * (a + b) for k, (a, b) in g['store'].items())
        return j.c['money'] - m0 + stock

    def test_new_garden_income_is_modest(self):
        self.assertLess(self.bot(2, [], 0, []), 80)

    def test_full_farm_income_stays_in_line(self):
        net = self.bot(6, ['drip', 'tractor', 'barn', 'green', 'gap'], 400, ['duck', 'cow'])
        self.assertGreater(net, 60)
        self.assertLess(net, 300)


if __name__ == '__main__':
    unittest.main()
