"""🏗️ Xây trên đảo (game/island_build.py, game/island_build_content.py; owner 19/10 "công trình trên đảo k kiếm tiền, xây
dựng nơi riêng, nhà này kia thôi"): the plots of every island, the catalogue, building in real hours (scaffolding, then
standing), upgrading, phá dỡ, selling the island with its buildings, payments split like the island's (wallet then
bank, never a loan, wallet rows ≤ 10M), no income anywhere, the daily tinh thần of the leisure buildings, the save
block's shape, the 💰 board and the phí giữ tài sản lớn."""
import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from game import island as isl
from game import island_build as ib
from game import island_build_content as C
from game import island_content as IC
from game import journey as jr
from game import wealth, wealth_fee
from game.engine import GameError, public_state, validate_state
from tests.test_bank import act
from tests.test_island import buy, money, next_day, refused, rich

ROOT = Path(__file__).resolve().parents[1]
ROW = 10_000_000
T0 = 1_800_000_000.0
H = 3600


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


def B(s):
    return s['journey']['islb']


class Timed(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        p = patch('game.island_build.now', self.clock)
        p.start()
        self.addCleanup(p.stop)

    def owner(self, iid='dao_dua', wallet=100_000_000, bank=0):
        s = rich(wallet + IC.ISLANDS[[i['id'] for i in IC.ISLANDS].index(iid)]['price'], bank=bank)
        s, _ = buy(s, iid)
        return s

    def build(self, s, plot, kind, iid='dao_dua'):
        return act(s, 'jr_isle_build', island=iid, plot=plot, kind=kind, confirm=True)


class Catalogue(unittest.TestCase):
    def test_plots_per_island_tier(self):
        self.assertEqual({i: len(p) for i, p in C.PLOTS.items()},
                         dict(dao_dua=6, dao_san_ho=10, dao_may_da=16, dao_hoang_hon=24))
        self.assertEqual(set(C.PLOTS), set(isl.ISLAND))
        for iid, plots in C.PLOTS.items():
            self.assertTrue(any(c for _, _, c in plots), iid)            # a marina fits on every island
            for i, (x, y, c) in enumerate(plots):
                self.assertTrue(0 < x < 1 and 0 < y < 1 and c in (0, 1), (iid, i))
                for x2, y2, _ in plots[i + 1:]:                           # plots never overlap (.072 wide)
                    self.assertTrue(abs(x - x2) >= .08 or abs(y - y2) >= .08, (iid, i))

    def test_plots_match_the_map_both_interfaces_draw(self):
        if not shutil.which('node'):
            self.skipTest('node is not installed')
        prog = ("import('./public/js/island-layout.js').then(m=>{const o={};for(const [k,L] of Object.entries(m.LOOKS))"
                "o[k]=L.plots;console.log(JSON.stringify(o));})")
        out = subprocess.run(['node', '--input-type=module', '-e', prog], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        js = json.loads(out.stdout)
        for i in IC.ISLANDS:
            self.assertEqual([list(p) for p in C.PLOTS[i['id']]], js[i['look']], i['id'])

    def test_buildings_cost_and_take_real_hours(self):
        ids = [b['id'] for b in C.BUILDINGS]
        first = ['nha_san', 'biet_thu', 'lau_dai', 'cong_vien', 'ho_boi', 'golf', 'cam_trai', 'ben_thuyen']
        styles = [h['id'] for h in C.HOUSES]
        self.assertEqual(ids, first + styles)                                    # 🏡 20/10: the styles after the first eight
        self.assertTrue(12 <= len(styles) <= 20)
        self.assertEqual({b['cat'] for b in C.BUILDINGS}, {'home', 'fun'})
        for b in C.BUILDINGS:
            self.assertTrue(ib._id(b['id']))
            self.assertTrue(2 <= len(b['levels']) <= 3 and len(b['lv']) == len(b['levels']), b['id'])
            prices = [p for p, _ in b['levels']]
            hours = [h for _, h in b['levels']]
            self.assertEqual(prices, sorted(prices))
            self.assertTrue(all(6 <= h <= 48 for h in hours), b['id'])
            self.assertTrue(all(10**6 <= p <= 80 * 10**6 for p in prices), b['id'])
            self.assertTrue(b['pts'] > 0)
        homes = {b['id'] for b in C.BUILDINGS if b['cat'] == 'home'}
        self.assertEqual(homes, {'nha_san', 'biet_thu', 'lau_dai', *styles})
        castle = ib.BUILD['lau_dai']
        self.assertGreater(sum(p for p, _ in castle['levels']), sum(p for p, _ in ib.BUILD['nha_san']['levels']) * 5)
        cat = jr.content()['island']['build']
        self.assertEqual(len(cat['buildings']), 8 + len(styles))
        self.assertEqual([t for t, _ in cat['tiers']], [1, 2, 3, 4])
        by = {b['id']: b for b in cat['buildings']}
        self.assertEqual((by['nha_san']['tier'], by['lau_dai']['tier'], by['ho_boi'].get('tier')), (1, 4, None))
        self.assertEqual((len(by['pho_hoi_an']['looks']), by['pho_hoi_an']['paint']), (3, 600_000))
        self.assertEqual(cat['plots']['dao_hoang_hon'][23], [.88, .5, 1])
        self.assertEqual(cat['salvage_pct'], C.SALVAGE_PCT)

    def test_no_building_earns_anything(self):
        """Owner 19/10: no income, ever. Nothing in the catalogue or the module mentions rent, income or a payout."""
        src = (ROOT / 'game' / 'island_build.py').read_text(encoding='utf-8')
        for word in ('income', 'rent', 'salary', 'thu nhập', 'tiền thuê'):
            self.assertNotIn(word, json.dumps(C.BUILDINGS, ensure_ascii=False).lower())
        # the only wallet credits: the salvage of a phá dỡ / a sale
        self.assertEqual(src.count('_wallet_rows(') - src.count('def _wallet_rows('), 2)
        self.assertEqual(src.count('_take('), 3)   # build, upgrade, 🎨 paint


class Building(Timed):
    def test_build_then_scaffolding_then_it_stands(self):
        s = self.owner()
        w = money(s)
        s, r = self.build(s, 0, 'nha_san')
        price, hours = ib.BUILD['nha_san']['levels'][0]
        self.assertEqual(w - money(s), price)
        self.assertIn(f'{hours} giờ', r['message'])
        e = B(s)['p']['dao_dua']['0']
        self.assertEqual((e['k'], e['l'], e['b'], e['t'], e['x']), ('nha_san', 0, 1, int(T0 + hours * H), price))
        self.assertTrue(ib.building(e, self.clock()))
        self.assertEqual(ib.standing(e, self.clock()), 0)
        pub = public_state(s)['journey']['islb']
        self.assertEqual(pub['p']['dao_dua']['0']['b'], 1)
        self.clock.t += hours * H - 1
        self.assertTrue(ib.building(e, self.clock()))
        self.clock.t += 1
        self.assertFalse(ib.building(e, self.clock()))
        self.assertEqual(ib.standing(e, self.clock()), 1)
        validate_state(s)
        # the next command settles it in the save
        s, r = self.build(s, 1, 'cong_vien')
        e = B(s)['p']['dao_dua']['0']
        self.assertEqual((e['l'], e['b'], e['t']), (1, 0, 0))
        self.assertTrue(any('xây xong' in x for x in r.get('effects', [])))
        validate_state(s)

    def test_upgrade_levels_and_their_hours(self):
        s = self.owner()
        s, _ = self.build(s, 2, 'ho_boi')
        lv = ib.BUILD['ho_boi']['levels']
        refused(self, s, 'jr_isle_up', 'busy', island='dao_dua', plot=2, confirm=True)          # still scaffolding
        self.clock.t += lv[0][1] * H
        w = money(s)
        s, r = act(s, 'jr_isle_up', island='dao_dua', plot=2, confirm=True)
        self.assertEqual(w - money(s), lv[1][0])
        e = B(s)['p']['dao_dua']['2']
        self.assertEqual((e['l'], e['b'], e['x']), (1, 2, lv[0][0] + lv[1][0]))
        self.assertEqual(ib.standing(e, self.clock()), 1)       # the old level stands while the crew works
        self.clock.t += lv[1][1] * H
        s, _ = act(s, 'jr_isle_up', island='dao_dua', plot=2, confirm=True)
        self.clock.t += lv[2][1] * H
        self.assertEqual(ib.standing(B(s)['p']['dao_dua']['2'], self.clock()), 3)
        refused(self, s, 'jr_isle_up', 'max', island='dao_dua', plot=2, confirm=True)
        refused(self, s, 'jr_isle_up', 'empty', island='dao_dua', plot=3, confirm=True)
        self.assertEqual(B(s)['n']['up'], 2)
        validate_state(s)

    def test_rules_of_the_plots(self):
        s = self.owner('dao_san_ho', wallet=200_000_000)
        refused(self, s, 'jr_isle_build', 'not_owned', island='dao_dua', plot=0, kind='nha_san', confirm=True)
        refused(self, s, 'jr_isle_build', island='dao_san_ho', plot=10, kind='nha_san', confirm=True)      # only 10 plots
        refused(self, s, 'jr_isle_build', island='dao_san_ho', plot='1', kind='nha_san', confirm=True)
        refused(self, s, 'jr_isle_build', island='dao_san_ho', plot=0, kind='thap_moi', confirm=True)
        refused(self, s, 'jr_isle_build', island='dao_san_ho', plot=0, kind='nha_san')                      # no confirm
        refused(self, s, 'jr_isle_build', 'coast', island='dao_san_ho', plot=0, kind='ben_thuyen', confirm=True)
        refused(self, s, 'jr_isle_build', 'small', island='dao_san_ho', plot=0, kind='lau_dai', confirm=True)
        s, _ = self.build(s, 9, 'ben_thuyen', 'dao_san_ho')                                               # the coast plot
        s, _ = self.build(s, 0, 'golf', 'dao_san_ho')
        refused(self, s, 'jr_isle_build', 'busy', island='dao_san_ho', plot=1, kind='cam_trai', confirm=True)   # two crews
        refused(self, s, 'jr_isle_build', 'taken', island='dao_san_ho', plot=0, kind='cam_trai', confirm=True)
        self.clock.t += 12 * H
        refused(self, s, 'jr_isle_build', 'limit', island='dao_san_ho', plot=1, kind='golf', confirm=True)      # one golf
        s, _ = self.build(s, 1, 'cam_trai', 'dao_san_ho')
        s, r = self.build(s, 1, 'cam_trai', 'dao_san_ho')                                                  # a second tap
        self.assertTrue(r.get('duplicate'))
        big = self.owner('dao_hoang_hon', wallet=100_000_000)
        big, _ = self.build(big, 5, 'lau_dai', 'dao_hoang_hon')
        self.assertEqual(B(big)['p']['dao_hoang_hon']['5']['k'], 'lau_dai')

    def test_paid_wallet_then_bank_in_rows_of_ten_million_never_a_loan(self):
        s = self.owner('dao_hoang_hon', wallet=12_000_000, bank=20_000_000)
        self.assertEqual(s['journey']['wallet'], 12_000_000)
        n = len(s['journey']['history'])
        s, r = self.build(s, 0, 'lau_dai', 'dao_hoang_hon')                       # 25M: 12M cash, 13M from the account
        self.assertEqual((s['journey']['wallet'], s['journey']['bank']['balance']), (0, 7_000_000))
        rows = s['journey']['history'][n:]
        self.assertEqual(sum(h['amount'] for h in rows), -12_000_000)
        self.assertTrue(all(-ROW <= h['amount'] < 0 and h['kind'] == 'life' for h in rows))
        self.assertEqual(len(rows), 2)
        self.assertIn('tài khoản', r['message'])
        validate_state(s)
        refused(self, s, 'jr_isle_build', 'not_enough', island='dao_hoang_hon', plot=1, kind='biet_thu', confirm=True)
        debt = self.owner(wallet=50_000_000)
        debt['journey']['wallet'] = -5
        why = refused(self, debt, 'jr_isle_build', 'not_enough', island='dao_dua', plot=0, kind='nha_san', confirm=True)
        self.assertIn('nợ', why)

    def test_big_cash_charge_split_in_rows(self):
        s = self.owner('dao_hoang_hon', wallet=100_000_000)
        s, _ = self.build(s, 0, 'lau_dai', 'dao_hoang_hon')
        rows = [h for h in s['journey']['history'] if 'Lâu đài' in h['label']]
        self.assertEqual(sum(h['amount'] for h in rows), -25_000_000)
        self.assertEqual(sorted(h['amount'] for h in rows), [-10_000_000, -10_000_000, -5_000_000])
        validate_state(s)


class Razing(Timed):
    def test_raze_gives_back_a_fifth_construction_included(self):
        s = self.owner()
        s, _ = self.build(s, 0, 'nha_san')
        self.clock.t += 6 * H
        s, _ = act(s, 'jr_isle_up', island='dao_dua', plot=0, confirm=True)              # 2M + 4M paid, level 2 building
        paid = B(s)['p']['dao_dua']['0']['x']
        self.assertEqual(paid, 6_000_000)
        w = s['journey']['wallet']
        refused(self, s, 'jr_isle_raze', island='dao_dua', plot=0)                       # no confirm
        s, r = act(s, 'jr_isle_raze', island='dao_dua', plot=0, confirm=True)
        self.assertEqual(s['journey']['wallet'] - w, paid * C.SALVAGE_PCT // 100)
        self.assertNotIn('0', B(s)['p']['dao_dua'])
        self.assertIn('Thu hồi', r['message'])
        refused(self, s, 'jr_isle_raze', 'empty', island='dao_dua', plot=0, confirm=True)
        s, _ = self.build(s, 0, 'cam_trai')                                              # the plot is free again
        validate_state(s)

    def test_selling_the_island_razes_its_buildings(self):
        s = self.owner('dao_san_ho', wallet=60_000_000)
        s, _ = self.build(s, 0, 'nha_san', 'dao_san_ho')
        s, _ = self.build(s, 9, 'ben_thuyen', 'dao_san_ho')
        w = s['journey']['wallet']
        s, r = act(s, 'jr_island_sell', id='dao_san_ho', confirm=True)
        self.assertEqual(s['journey']['wallet'] - w, isl.sell_price(60_000_000) + (2_000_000 + 5_000_000) // 5)
        self.assertNotIn('dao_san_ho', B(s)['p'])
        self.assertIn('thu hồi vật liệu', r['message'])
        validate_state(s)
        s, _ = buy(s, 'dao_san_ho')                                                      # bought again: empty plots
        self.assertEqual(ib.public(s)['p'].get('dao_san_ho', {}), {})


class NoIncome(Timed):
    def test_months_with_buildings_only_cost_the_islands_fee(self):
        s = self.owner('dao_san_ho', wallet=80_000_000)
        for plot, kind in ((0, 'ho_boi'), (1, 'nha_san')):
            s, _ = self.build(s, plot, kind, 'dao_san_ho')
        self.clock.t += 48 * H
        for plot, kind in ((2, 'golf'), (9, 'ben_thuyen')):
            s, _ = self.build(s, plot, kind, 'dao_san_ho')
        self.clock.t += 48 * H
        bare = copy.deepcopy(s)
        del bare['journey']['islb']                                                      # the same save without its buildings
        w, wb = money(s), money(bare)
        s, bare = next_day(s, 60), next_day(bare, 60)
        credits = [h for h in s['journey']['history'][-200:] if h['amount'] > 0 and ('đảo' in h['label'].lower() or '🏗️' in h['label'])]
        self.assertEqual(credits, [])
        self.assertEqual(w - money(s), wb - money(bare))                                 # two months: not one xu more or less
        self.assertGreater(w - money(s), 0)
        validate_state(s)


class Use(Timed):
    def test_spirit_three_times_a_day(self):
        s = self.owner()
        L = s['journey']['life']
        L['spirit'] = 50
        trip = 'ab' * 8
        w = s['journey']['wallet']
        for i in range(C.USE_MAX):
            s, r = act(s, 'jr_isle_use', trip=trip, plot=0)
            self.assertEqual(r['isle_use']['left'], C.USE_MAX - i - 1)
        self.assertEqual(s['journey']['life']['spirit'], 50 + C.USE_MAX * C.USE_SPIRIT)
        self.assertEqual(s['journey']['wallet'], w)                                     # never money
        refused(self, s, 'jr_isle_use', 'limit', trip=trip, plot=0)
        refused(self, s, 'jr_isle_use', trip='nope', plot=0)
        self.assertEqual(public_state(s)['journey']['islb']['used'], 3)
        self.clock.t += 86400
        s, _ = act(s, 'jr_isle_use', trip=trip, plot=0)
        self.assertEqual(B(s)['u']['n'], 1)
        validate_state(s)


class SaveBlock(Timed):
    def test_strict_shape(self):
        s = self.owner()
        s, _ = self.build(s, 0, 'nha_san')
        validate_state(s)
        for bad in ({'v': 2}, {'x': 1}, {'u': {'d': 1}}, {'n': {'zz': 1}},
                    {'p': {'dao_dua': {'0': {'k': 'nha_san', 'l': 0, 'b': 0, 't': 0, 'x': 5}}}},     # nothing standing, nothing built
                    {'p': {'dao_dua': {'0': {'k': 'nha_san', 'l': 1, 'b': 3, 't': 5, 'x': 5}}}},     # skips a level
                    {'p': {'dao_dua': {'a': {'k': 'nha_san', 'l': 1, 'b': 0, 't': 0, 'x': 5}}}}):
            t = copy.deepcopy(s)
            B(t).update(bad)
            with self.assertRaises(GameError):
                validate_state(t)

    def test_newer_fields_and_unknown_kinds_are_kept_by_shape(self):
        s = self.owner()
        s, _ = self.build(s, 0, 'nha_san')
        B(s)['p']['dao_dua']['1'] = dict(k='thap_nuoc', l=1, b=0, t=0, x=9_000_000, extra=1)
        B(s)['later'] = True
        jr.upgrade(s['journey'])
        self.assertNotIn('later', B(s))
        self.assertEqual(B(s)['p']['dao_dua']['1'], dict(k='thap_nuoc', l=1, b=0, t=0, x=9_000_000))
        validate_state(s)
        self.assertNotIn('1', ib.public(s)['p']['dao_dua'])

    def test_absent_until_the_first_building(self):
        s = self.owner()
        self.assertNotIn('islb', s['journey'])
        self.assertNotIn('islb', public_state(s)['journey'])
        validate_state(s)


class Wealth(Timed):
    def test_board_and_fee_count_islands_and_buildings_at_their_buy_back(self):
        s = self.owner('dao_hoang_hon', wallet=60_000_000)
        before_board = wealth.worth(s)[1]
        before_fee = wealth_fee.assets(s)
        s, _ = self.build(s, 0, 'lau_dai', 'dao_hoang_hon')      # 25M paid
        salvage = 25_000_000 * C.SALVAGE_PCT // 100
        self.assertEqual(ib.worth(s['journey']), salvage)
        self.assertEqual(before_board - wealth.worth(s)[1], 25_000_000 - salvage)
        self.assertEqual(before_fee - wealth_fee.assets(s), 25_000_000 - salvage)
        self.assertEqual(wealth_fee.islands(s), isl.sell_price(200_000_000) + salvage)
        bare = copy.deepcopy(s)
        del bare['journey']['island'], bare['journey']['islb']
        self.assertEqual(wealth_fee.assets(s) - wealth_fee.assets(bare), 120_000_000 + salvage)
        self.assertGreater(wealth_fee.daily(wealth_fee.assets(s)), wealth_fee.daily(wealth_fee.assets(bare)))
        # a plot of an island no longer owned (sold on an older build) is not counted
        del s['journey']['island']['own']['dao_hoang_hon']
        self.assertEqual(ib.worth(s['journey']), 0)


if __name__ == '__main__':
    unittest.main()
