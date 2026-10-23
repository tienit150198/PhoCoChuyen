"""🏝️ Thiết kế đảo (game/island_design.py): bigger islands on a free grid, 🌊 lấn biển, decorations placed anywhere and the
buildings moved. Old islands load at the new base size with every building where it stood (and their points on the
🏝️ Đảo đẹp board never lower); placement is checked on the server (bounds, land / sea / coast, the island's own
features, overlaps, ownership, prices, limits); the kho keeps what was bought; island_layout follows the save; visitors,
the open-island list and the board read it; an older release keeps journey.isld untouched."""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from game import island as isl
from game import island_build as ib
from game import island_build_content as BC
from game import island_design as D
from game import island_design_content as C
from game.engine import GameError, validate_state
from tests.test_bank import act
from tests.test_island import buy, rich

ROOT = Path(__file__).resolve().parents[1]
T0 = 1_800_000_000.0
H = 3600


def err(test, s, name, code=None, **p):
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    if code:
        test.assertEqual(cm.exception.code, code, cm.exception.message)
    return cm.exception.message


def free_spot(s, iid, kind, r=0, where=None, skip=()):
    """The first (x, y) where `kind` fits on the island now (scanning the grid)."""
    d = D.isle_of(s, iid)
    w, h, wh = D.foot_of(kind)
    taken = D.occupied(s, iid, d)
    for y in range(C.G):
        for x in range(C.G):
            if (x, y) in skip:
                continue
            if not D.fits(D.LOOK_OF[iid], d['t'], w, h, where or wh, x, y, r, taken):
                return x, y
    raise AssertionError(f'no place for {kind}')


def place(s, kind, iid='dao_dua', r=0, at=None, **extra):
    x, y = at or free_spot(s, iid, kind, r)
    return act(s, 'jr_isle_place', island=iid, kind=kind, x=x, y=y, r=r, confirm=True, **extra)


class Catalogue(unittest.TestCase):
    def test_prices_points_and_shapes(self):
        ids = [d['id'] for d in C.DECOR]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 50)
        self.assertFalse(set(ids) & set(ib.BUILD))                         # never mistaken for a building
        cats = {c for c, _ in C.CATS}
        for d in C.DECOR:
            self.assertRegex(d['id'], r'^[a-z_]{1,16}$')                     # live/island.py spot ids: 'd_' + id
            self.assertIn(d['cat'], cats)
            self.assertIn(d['where'], ('land', 'coast', 'pier', 'sea', 'any'))
            self.assertTrue(1 <= d['w'] <= 6 and 1 <= d['h'] <= 6)
            self.assertTrue(30_000 <= d['price'] <= 50_000_000, d['id'])   # players hold 30–300M
            self.assertEqual(d['pts'], C.pts_for(d['price']))
            self.assertLessEqual(d['pts'], max(1, round(2.5 * d['price'] / 1e6)))   # no cheaper a point than the buildings
            self.assertGreaterEqual(d['max'], 1)
            self.assertTrue(d['name'] and d['emoji'] and d['desc'])
        for cat in cats:
            self.assertTrue(any(d['cat'] == cat for d in C.DECOR))
        # what the owner asked for is there: pools of several sizes, houses, trees, piers, rocks, water, a lighthouse…
        for k in ('ho_nho', 'ho_dai', 'ho_lon', 'ho_tran', 'nha_go', 'resort', 'bungalow_nuoc', 'choi_la', 'cau_tau',
                  'ghe_dai', 'o_du', 'den_vuon', 'rao_go', 'loi_da', 'vuon_hoa', 'cay_dua', 'cay_phuong', 'cay_co',
                  'hoa_giay', 'khom_tre', 'da_lon', 'thac_nuoc', 'suoi_da', 'khu_bbq', 'san_choi', 'du_thuyen'):
            self.assertIn(k, ids)
        for k in ('hai_dang', 'biet_thu', 'ben_thuyen', 'ho_boi'):           # 🗼 the lighthouse, villas, the marina: buildings
            self.assertIn(k, ib.BUILD)

    def test_points_curve(self):
        self.assertEqual(C.pts_for(199_999), 0)
        self.assertEqual(C.pts_for(200_000), 1)
        prev = 0
        for m in (1, 2, 5, 10, 20, 45):
            p = C.pts_for(m * 1_000_000)
            self.assertGreater(p, prev)
            prev = p
        self.assertLess(C.pts_for(45_000_000), ib.BUILD['lau_dai']['pts'] * 2)

    def test_expansion_prices(self):
        for i in isl.C.ISLANDS:
            prices = [D.expand_price(i['id'], t) for t in range(1, len(C.TIERS))]
            self.assertEqual(prices, [i['price'] * p // 100 for p in C.EXPAND_PCT])
            self.assertEqual(prices, sorted(prices))
        self.assertEqual(D.expand_price('dao_dua', 1), 6_000_000)
        self.assertEqual(D.expand_price('dao_hoang_hon', 4), 100_000_000)
        self.assertEqual(D.expand_price('dao_dua', len(C.TIERS)), 0)
        self.assertEqual(len(C.EXPAND_PTS), len(C.TIERS) - 1)

    def test_catalogue_view(self):
        c = isl.catalogue()['build']['design'] if 'build' in isl.catalogue() else None
        self.assertIsNotNone(c)
        self.assertEqual(c['g'], C.G)
        self.assertEqual(len(c['decor']), len(C.DECOR))
        self.assertEqual(c['expand']['dao_dua'][0], 6_000_000)
        json.dumps(c)


class Grid(unittest.TestCase):
    def test_every_island_grows_and_tier_0_is_bigger_than_the_old_map(self):
        for look in C.SHAPES:
            sizes = [sum(D.cells(look, t)[0]) for t in range(len(C.TIERS))]
            self.assertEqual(sizes, sorted(sizes))
            self.assertGreater(sizes[-1], sizes[0] * 1.6)
            old = D.blob(*C.SHAPES[look][:5])
            g = C.G
            land = D.cells(look, 0)[0]
            n_old = sum(1 for j in range(g) for i in range(g) if D.in_poly(old, D.cell_x(i), D.cell_x(j)))
            self.assertGreater(sizes[0], n_old * 1.25)                      # tier 0: 15 % wider = 32 % more land
            for j in range(g):                                              # the old island is all inside the new one
                for i in range(g):
                    if D.in_poly(old, D.cell_x(i), D.cell_x(j)):
                        self.assertTrue(land[j * g + i], (look, i, j))
            # the grid holds the biggest island with sea all round
            big = D.cells(look, len(C.TIERS) - 1)[0]
            for k in range(g):
                for c in (k, (g - 1) * g + k, k * g, k * g + g - 1):
                    self.assertFalse(big[c])

    def test_old_plots_stand_where_they_stood_at_every_size(self):
        for iid, spots in BC.PLOTS.items():
            look = D.LOOK_OF[iid]
            for t in range(len(C.TIERS)):
                land, coast, fixed = D.cells(look, t)
                seen = set()
                for n, (x, y, by_sea) in enumerate(spots):
                    pos = D.default_pos(iid, n, t)
                    cs = D.footprint(C.BUILD_FOOT, C.BUILD_FOOT, *pos)
                    self.assertTrue(all(land[c] for c in cs), (iid, n, t))
                    self.assertFalse(any(c in fixed for c in cs), (iid, n, t))
                    self.assertFalse(seen & set(cs), (iid, n, t))           # never on one another
                    seen |= set(cs)
                    if by_sea:
                        self.assertTrue(any(coast[c] for c in cs), (iid, n, t))
                    else:                                                   # a plot inland: the very same middle
                        mx = C.X0 + (pos[0] + 1.5) * C.CELL
                        my = C.X0 + (pos[1] + 1.5) * C.CELL
                        self.assertLess(abs(mx - x), C.CELL * .51)
                        self.assertLess(abs(my - y), C.CELL * .51)
        self.assertIsNone(D.default_pos('dao_dua', 40, 0))

    def test_footprints_turn(self):
        self.assertEqual(len(D.footprint(3, 2, 0, 0, 0)), 6)
        self.assertEqual(D.footprint(3, 1, 5, 5, 1), [5 * C.G + 5, 6 * C.G + 5, 7 * C.G + 5])
        self.assertTrue(D.rotatable('ho_dai'))
        self.assertFalse(D.rotatable('lau_dai'))                            # the first eight never turn
        self.assertTrue(D.rotatable('pho_hoi_an'))                         # 🏡 a house style does


class Placing(unittest.TestCase):
    def setUp(self):
        p = patch('game.island_build.now', lambda: T0)
        p.start()
        self.addCleanup(p.stop)
        s = rich(150_000_000)
        self.s, _ = buy(s, 'dao_dua')

    def test_buy_place_move_turn_store_and_place_again_free(self):
        s = self.s
        w0 = s['journey']['wallet']
        x, y = free_spot(s, 'dao_dua', 'ho_dai')
        s, out = act(s, 'jr_isle_place', island='dao_dua', kind='ho_dai', x=x, y=y, r=0, confirm=True)
        self.assertEqual(s['journey']['wallet'], w0 - 5_000_000)
        validate_state(s)
        b = s['journey']['isld']
        self.assertEqual(b['i']['dao_dua']['d'], {'1': ['ho_dai', x, y, 0]})
        self.assertEqual(b['st']['xu'], 5_000_000)
        pub = s['journey'].get('isld')
        self.assertTrue(pub)
        x2, y2 = free_spot(s, 'dao_dua', 'ho_dai', r=1)
        s, _ = act(s, 'jr_isle_dmove', island='dao_dua', id=1, x=x2, y=y2, r=1)
        self.assertEqual(s['journey']['isld']['i']['dao_dua']['d']['1'], ['ho_dai', x2, y2, 1])
        s, _ = act(s, 'jr_isle_store', island='dao_dua', id=1)
        self.assertEqual(s['journey']['isld']['inv'], {'ho_dai': 1})
        self.assertEqual(s['journey']['isld']['i']['dao_dua']['d'], {})
        w1 = s['journey']['wallet']
        s, out = act(s, 'jr_isle_place', island='dao_dua', kind='ho_dai', x=x, y=y, r=0)   # from the kho: no confirm, free
        self.assertEqual(s['journey']['wallet'], w1)
        self.assertEqual(s['journey']['isld']['inv'], {})
        self.assertIn('từ kho', out['message'] if isinstance(out, dict) and 'message' in out else json.dumps(out, ensure_ascii=False))
        validate_state(s)

    def test_rules(self):
        s = self.s
        ex, ey = free_spot(s, 'dao_dua', 'ho_dai')
        err(self, s, 'jr_isle_place', island='dao_dua', kind='ho_dai', x=ex, y=ey, r=0)                    # confirm
        err(self, s, 'jr_isle_place', 'not_owned', island='dao_san_ho', kind='ho_dai', x=ex, y=ey, confirm=True)
        err(self, s, 'jr_isle_place', island='dao_dua', kind='khong_co', x=ex, y=ey, confirm=True)
        err(self, s, 'jr_isle_place', 'place', island='dao_dua', kind='ho_dai', x=0, y=0, confirm=True)     # the sea
        err(self, s, 'jr_isle_place', 'place', island='dao_dua', kind='ho_dai', x=C.G - 1, y=ey, confirm=True)  # off the grid
        err(self, s, 'jr_isle_place', island='dao_dua', kind='ho_dai', x=-1, y=ey, confirm=True)
        err(self, s, 'jr_isle_place', island='dao_dua', kind='ho_dai', x=1.5, y=ey, confirm=True)
        err(self, s, 'jr_isle_place', island='dao_dua', kind='ho_dai', x=ex, y=ey, r=4, confirm=True)
        err(self, s, 'jr_isle_place', island='dao_dua', kind='ho_dai', x=ex, y=ey, hack=1, confirm=True)
        # the villa (the island's own features): x .5, y .36 → cells around (30, 24)
        vx, vy = int((.5 - C.X0) / C.CELL), int((.36 - C.X0) / C.CELL)
        msg = err(self, s, 'jr_isle_place', 'place', island='dao_dua', kind='bui_hoa', x=vx, y=vy, confirm=True)
        self.assertIn('công trình sẵn', msg)
        s, _ = act(s, 'jr_isle_place', island='dao_dua', kind='ho_dai', x=ex, y=ey, r=0, confirm=True)
        msg = err(self, s, 'jr_isle_place', 'place', island='dao_dua', kind='bui_hoa', x=ex + 1, y=ey + 1, confirm=True)
        self.assertIn('đồ khác', msg)
        # where: a sea one on land, a coast one inland, a pier all on land
        err(self, s, 'jr_isle_place', 'place', island='dao_dua', kind='phao_boi', x=ex, y=ey + 3, confirm=True)
        lx, ly = free_spot(s, 'dao_dua', 'ho_dai', where='land')
        land, coast, _ = D.cells('dua', 0)
        inland = next((x, y) for y in range(C.G) for x in range(C.G)
                      if not D.fits('dua', 0, 5, 3, 'land', x, y, 0, D.occupied(s, 'dao_dua'))
                      and not any(coast[c] for c in D.footprint(5, 3, x, y, 0)))
        err(self, s, 'jr_isle_place', 'place', island='dao_dua', kind='ho_tran', x=inland[0], y=inland[1], confirm=True)
        err(self, s, 'jr_isle_place', 'place', island='dao_dua', kind='cau_tau', x=inland[0], y=inland[1], confirm=True)
        # where they do fit
        for kind in ('phao_boi', 'ho_tran', 'cau_tau', 'kayak', 'nha_thuyen', 'du_thuyen', 'bungalow_nuoc', 'da_lon'):
            s, _ = place(s, kind)
        validate_state(s)
        # a building on the grid never turns when it is one of the first eight
        x, y = free_spot(s, 'dao_dua', 'nha_san')
        err(self, s, 'jr_isle_build', island='dao_dua', kind='nha_san', x=x, y=y, r=1, confirm=True)

    def test_limits_and_money(self):
        s = self.s
        s, _ = place(s, 'resort')
        err(self, s, 'jr_isle_place', 'limit', island='dao_dua', kind='resort', x=1, y=1, confirm=True)
        poor = copy.deepcopy(s)
        poor['journey']['wallet'] = 1000
        x, y = free_spot(poor, 'dao_dua', 'ho_dai')
        err(self, poor, 'jr_isle_place', 'not_enough', island='dao_dua', kind='ho_dai', x=x, y=y, confirm=True)
        self.assertEqual(poor['journey']['wallet'], 1000)

    def test_a_save_with_a_broken_block_is_refused_and_extra_fields_are_dropped(self):
        s, _ = place(self.s, 'cay_dua')
        bad = copy.deepcopy(s)
        bad['journey']['isld']['i']['dao_dua']['d']['1'][1] = -3
        with self.assertRaises(GameError):
            validate_state(bad)
        j = copy.deepcopy(s['journey'])
        j['isld']['zz'] = 1
        j['isld']['i']['dao_dua']['d']['9'] = ['cay_dua', 'x', 1, 0]
        D.upgrade(j)
        self.assertEqual(j['isld']['i']['dao_dua']['d'], s['journey']['isld']['i']['dao_dua']['d'])
        self.assertNotIn('zz', j['isld'])
        j = copy.deepcopy(s['journey'])
        j['isld']['i']['dao_dua']['d']['2'] = ['cay_moi_cua_ban_sau', 3, 3, 0]   # a kind a newer build added: kept
        D.upgrade(j)
        self.assertIn('2', j['isld']['i']['dao_dua']['d'])
        self.assertEqual(D.decor_pts(v[0] for v in j['isld']['i']['dao_dua']['d'].values()), D.decor_pts(['cay_dua']))


class Buildings(unittest.TestCase):
    """The buildings of journey.islb on the grid: old plots stay, new ones go anywhere, they move and turn."""

    def setUp(self):
        self.t = [T0]
        p = patch('game.island_build.now', lambda: self.t[0])
        p.start()
        self.addCleanup(p.stop)
        s = rich(300_000_000)
        self.s, _ = buy(s, 'dao_dua')

    def test_an_old_island_loads_with_every_building_in_place_and_the_same_points(self):
        s = self.s
        s, _ = act(s, 'jr_isle_build', island='dao_dua', plot=0, kind='nha_san', confirm=True)   # the old command
        s, _ = act(s, 'jr_isle_build', island='dao_dua', plot=5, kind='ben_thuyen', confirm=True)
        self.t[0] += 48 * H
        self.assertNotIn('isld', s['journey'])                       # nothing written for an old island
        before = ib.score(list(s['journey']['islb']['p']['dao_dua'].values()), self.t[0])
        pub = D.public(s)
        places = pub['i']['dao_dua']['b']
        self.assertEqual(places, {'0': list(D.default_pos('dao_dua', 0, 0)), '5': list(D.default_pos('dao_dua', 5, 0))})
        self.assertEqual(pub['i']['dao_dua']['t'], 0)
        self.assertEqual(pub['i']['dao_dua']['pts'], 0)               # points: the buildings' as before, plus nothing
        s, _ = place(s, 'cay_dua')
        self.assertEqual(D.design_pts(s['journey']['isld']['i']['dao_dua']), C.pts_for(300_000) + C.VARIETY)
        self.assertEqual(ib.score(list(s['journey']['islb']['p']['dao_dua'].values()), self.t[0]), before)
        validate_state(s)

    def test_built_on_the_grid_moved_turned_razed(self):
        s = self.s
        x, y = free_spot(s, 'dao_dua', 'pho_hoi_an', r=1)
        s, _ = act(s, 'jr_isle_build', island='dao_dua', kind='pho_hoi_an', x=x, y=y, r=1, confirm=True)
        plots = s['journey']['islb']['p']['dao_dua']
        self.assertEqual(list(plots), [str(len(BC.PLOTS['dao_dua']))])   # a plot index past the old ones
        n = int(next(iter(plots)))
        self.assertEqual(s['journey']['isld']['i']['dao_dua']['b'], {str(n): [x, y, 1]})
        err(self, s, 'jr_isle_place', 'place', island='dao_dua', kind='bui_hoa', x=x + 1, y=y + 1, confirm=True)
        x2, y2 = free_spot(s, 'dao_dua', 'pho_hoi_an')
        s, _ = act(s, 'jr_isle_bmove', island='dao_dua', plot=n, x=x2, y=y2, r=0)
        self.assertEqual(s['journey']['isld']['i']['dao_dua']['b'][str(n)], [x2, y2, 0])
        s, _ = act(s, 'jr_isle_build', island='dao_dua', plot=0, kind='nha_san', confirm=True)   # an old plot still works
        p0 = D.default_pos('dao_dua', 0, 0)
        err(self, s, 'jr_isle_bmove', 'no_turn', island='dao_dua', plot=0, x=p0[0], y=p0[1], r=1)
        free = free_spot(s, 'dao_dua', 'nha_san')
        s, _ = act(s, 'jr_isle_bmove', island='dao_dua', plot=0, x=free[0], y=free[1], r=0)
        # the old plot 0's cells are free now: a decoration may go there, and an old client building on plot 0 is refused
        s, _ = act(s, 'jr_isle_raze', island='dao_dua', plot=0, confirm=True)
        self.assertNotIn('0', s['journey']['isld']['i']['dao_dua']['b'])
        s, _ = place(s, 'bui_hoa', at=(p0[0] + 1, p0[1] + 1))
        msg = err(self, s, 'jr_isle_build', 'taken', island='dao_dua', plot=0, kind='nha_san', confirm=True)
        self.assertIn('trang trí', msg)
        validate_state(s)

    def test_a_grid_build_needs_its_place(self):
        s = self.s
        err(self, s, 'jr_isle_build', 'place', island='dao_dua', kind='nha_san', x=0, y=0, confirm=True)
        err(self, s, 'jr_isle_build', island='dao_dua', kind='nha_san', x=1, confirm=True)
        err(self, s, 'jr_isle_build', island='dao_dua', kind='nha_san', plot=0, x=1, y=1, confirm=True)
        inland = next((x, y) for y in range(C.G) for x in range(C.G)
                      if not D.fits('dua', 0, 3, 3, 'land', x, y, 0, D.occupied(s, 'dao_dua'))
                      and D.fits('dua', 0, 3, 3, 'coast', x, y, 0, D.occupied(s, 'dao_dua')))
        msg = err(self, s, 'jr_isle_build', 'place', island='dao_dua', kind='ben_thuyen', x=inland[0], y=inland[1], confirm=True)
        self.assertIn('bờ biển', msg)


class Expanding(unittest.TestCase):
    def setUp(self):
        p = patch('game.island_build.now', lambda: T0)
        p.start()
        self.addCleanup(p.stop)
        s = rich(250_000_000)
        self.s, _ = buy(s, 'dao_dua')

    def test_lan_bien_tiers_price_points_and_the_sea_items(self):
        s = self.s
        err(self, s, 'jr_isle_expand', island='dao_dua')                                   # confirm
        # a buoy on the water that tier 1 turns into beach goes back into the kho
        land1 = D.cells('dua', 1)[0]
        land0 = D.cells('dua', 0)[0]
        g = C.G
        x, y = next((i, j) for j in range(g) for i in range(g)
                    if land1[j * g + i] and not land0[j * g + i]
                    and not D.fits('dua', 0, 1, 1, 'sea', i, j, 0, {}))
        s, _ = act(s, 'jr_isle_place', island='dao_dua', kind='phao_boi', x=x, y=y, r=0, confirm=True)
        s, _ = place(s, 'ho_dai')
        w = s['journey']['wallet']
        s, out = act(s, 'jr_isle_expand', island='dao_dua', confirm=True)
        self.assertEqual(s['journey']['wallet'], w - 6_000_000)
        d = s['journey']['isld']['i']['dao_dua']
        self.assertEqual(d['t'], 1)
        self.assertEqual([v[0] for v in d['d'].values()], ['ho_dai'])                     # the pool stays
        self.assertEqual(s['journey']['isld']['inv'], {'phao_boi': 1})                    # the buoy: in the kho
        self.assertEqual(D.design_pts(d), D.decor_pts(['ho_dai']) + C.EXPAND_PTS[0])
        self.assertEqual(s['journey']['isld']['st']['exp'], 6_000_000)
        for t in range(2, len(C.TIERS)):
            s, _ = act(s, 'jr_isle_expand', island='dao_dua', confirm=True)
        self.assertEqual(s['journey']['isld']['i']['dao_dua']['t'], len(C.TIERS) - 1)
        err(self, s, 'jr_isle_expand', 'max', island='dao_dua', confirm=True)
        self.assertEqual(s['journey']['isld']['st']['exp'], sum(D.expand_price('dao_dua', t) for t in range(1, len(C.TIERS))))
        validate_state(s)

    def test_a_building_in_the_way_refuses(self):
        s = self.s
        # the old marina plot (5) moves out with the coast at tier 1: a building on the cells it goes to refuses
        s, _ = act(s, 'jr_isle_build', island='dao_dua', plot=5, kind='ben_thuyen', confirm=True)
        self.assertEqual(D.default_pos('dao_dua', 5, 1), (40, 40, 0))
        s2, _ = act(s, 'jr_isle_build', island='dao_dua', kind='nha_san', x=41, y=38, r=0, confirm=True)
        msg = err(self, s2, 'jr_isle_expand', 'blocked', island='dao_dua', confirm=True)
        self.assertIn('Nhà sàn', msg)
        s, _ = act(s, 'jr_isle_expand', island='dao_dua', confirm=True)   # without it: the marina goes to the new beach
        self.assertEqual(D.public(s)['i']['dao_dua']['b']['5'], [40, 40, 0])

    def test_poor(self):
        s = copy.deepcopy(self.s)
        s['journey']['wallet'] = 10
        err(self, s, 'jr_isle_expand', 'not_enough', island='dao_dua', confirm=True)


class Selling(unittest.TestCase):
    def test_sold_decorations_go_to_the_kho_and_the_size_stays(self):
        with patch('game.island_build.now', lambda: T0):
            s = rich(250_000_000)
            s, _ = buy(s, 'dao_dua')
            s, _ = place(s, 'ho_dai')
            s, _ = place(s, 'cay_dua')
            s, _ = act(s, 'jr_isle_expand', island='dao_dua', confirm=True)
            s, out = act(s, 'jr_island_sell', id='dao_dua', confirm=True)
            self.assertEqual(s['journey']['isld']['inv'], {'ho_dai': 1, 'cay_dua': 1})
            self.assertNotIn('dao_dua', D.public(s)['i'])
            validate_state(s)
            s, _ = buy(s, 'dao_dua')
            self.assertEqual(D.public(s)['i']['dao_dua']['t'], 1)
            s, _ = act(s, 'jr_isle_place', island='dao_dua', kind='ho_dai', x=free_spot(s, 'dao_dua', 'ho_dai')[0],
                       y=free_spot(s, 'dao_dua', 'ho_dai')[1], r=0)
            self.assertEqual(s['journey']['isld']['inv'], {'cay_dua': 1})


class JsMatchesPython(unittest.TestCase):
    """public/js/island-layout.js draws the same coasts, sizes and features the server checks against."""

    def test_shapes_fixed_and_cells(self):
        prog = ("import('./public/js/island-layout.js').then(m=>{const out={};for(const look of Object.keys(m.LOOKS)){"
                "out[look]=[];for(let t=0;t<" + str(len(C.TIERS)) + ";t++){const c=m.gridCells(look,t);"
                "out[look].push([Array.from(c.land).join(''),Array.from(c.coast).join(''),[...c.fixed].sort((a,b)=>a-b)])}}"
                "console.log(JSON.stringify({out,G:m.GRID.G,X0:m.GRID.X0,CELL:m.GRID.CELL,"
                "tiers:m.GRID.TIERS,decor:m.DECOR_META}))})")
        r = subprocess.run(['node', '--input-type=module', '-e', prog], cwd=ROOT, capture_output=True, text=True,
                           encoding='utf-8', timeout=120)
        if r.returncode and 'not found' in (r.stderr or '').lower():
            self.skipTest('no node')
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        js = json.loads(r.stdout)
        self.assertEqual((js['G'], js['X0'], js['CELL']), (C.G, C.X0, C.CELL))
        self.assertEqual(tuple(js['tiers']), C.TIERS)
        self.assertEqual(set(js['out']), set(C.SHAPES))
        for look, tiers in js['out'].items():
            for t, (land, coast, fixed) in enumerate(tiers):
                pl, pc, pf = D.cells(look, t)
                self.assertEqual(land, ''.join(map(str, pl)), (look, t))
                self.assertEqual(coast, ''.join(map(str, pc)), (look, t))
                self.assertEqual(fixed, sorted(pf), (look, t))
        self.assertEqual(set(js['decor']), {d['id'] for d in C.DECOR})
        for d in C.DECOR:
            w, h, where, solid, pose, cat, emoji, name = js['decor'][d['id']]
            self.assertEqual((w, h, where, bool(solid), pose, cat, emoji, name),
                             (d['w'], d['h'], d['where'], d['solid'], d['pose'], d['cat'], d['emoji'], d['name']), d['id'])


RELEASE = '8dc9ed9e'   # 2.5.9.1: the release before this one

PROG = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action
out=[]
for s in json.load(sys.stdin):
    validate_state(s);s=migrate_state(s);validate_state(s)
    before=json.dumps(s['journey'].get('isld'),sort_keys=True)
    s['journey']['life_day']+=3
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([before,json.dumps(s['journey'].get('isld'),sort_keys=True),json.dumps(s['journey'].get('islb'),sort_keys=True)])
print(json.dumps(out))
'''


class Rollback(unittest.TestCase):
    """2.5.9.1 (production before this) keeps journey.isld and the buildings placed on the grid untouched."""

    def test_saves_play_on_the_release_before(self):
        import io
        import shutil
        import tarfile
        import tempfile
        tmp = tempfile.mkdtemp(prefix='mnl-isld-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {RELEASE}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        with patch('game.island_build.now', lambda: T0):
            s = rich(300_000_000)
            s, _ = buy(s, 'dao_dua')
            s, _ = act(s, 'jr_isle_build', island='dao_dua', plot=0, kind='nha_san', confirm=True)
            x, y = free_spot(s, 'dao_dua', 'pho_hoi_an', r=1)
            s, _ = act(s, 'jr_isle_build', island='dao_dua', kind='pho_hoi_an', x=x, y=y, r=1, confirm=True)   # plot 6
            s, _ = place(s, 'ho_dai')
            s, _ = place(s, 'cay_dua')
            s, _ = act(s, 'jr_isle_expand', island='dao_dua', confirm=True)
            validate_state(s)
        env = dict(os.environ, PYTHONPATH=tmp, PYTHONUTF8='1')
        r = subprocess.run([sys.executable, '-c', PROG], input=json.dumps([s]), capture_output=True, text=True, cwd=tmp,
                           env=env, encoding='utf-8', timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        (before, after, islb), = json.loads(r.stdout)
        mine = json.dumps(s['journey']['isld'], sort_keys=True)
        self.assertEqual(before, mine)
        self.assertEqual(after, mine)
        self.assertEqual(islb, json.dumps(s['journey']['islb'], sort_keys=True))   # the grid building (plot 6) kept


if __name__ == '__main__':
    unittest.main()
