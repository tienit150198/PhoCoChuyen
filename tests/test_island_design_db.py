"""🏝️ Thiết kế đảo on real PostgreSQL rows: island_layout follows the save (place, move, lấn biển, sale, reset, erase),
visitors read the island's size, decorations and every building's place from it (never a sid), and the 🏝️ Đảo đẹp board
adds its points to the buildings' — an island with decorations and no building is on the board too."""
import json

from game import island_build as ib
from game import island_design as D
from game import island_lb as ilb
from tests.test_island_build_db import Isle, H


class Layout(Isle):
    def layout(self, sid=None):
        with self.store.connect() as db:
            return {r['island']: dict(tier=int(r['tier']), data=json.loads(r['data']), pts=int(r['pts']), status=r['status'])
                    for r in db.execute('SELECT * FROM island_layout WHERE owner=?', (sid or self.sid(self.a),)).fetchall()}

    def spot(self, kind, token=None):
        s = self.state(token or self.a)
        d = D.isle_of(s, 'dao_dua')
        w, h, where = D.foot_of(kind)
        taken = D.occupied(s, 'dao_dua', d)
        for y in range(10, 50):
            for x in range(10, 50):
                if not D.fits('dua', d['t'], w, h, where, x, y, 0, taken):
                    return x, y
        raise AssertionError(kind)

    def place(self, kind, token=None):
        x, y = self.spot(kind, token)
        self.command(token or self.a, 'jr_isle_place', island='dao_dua', kind=kind, x=x, y=y, r=0, confirm=True)
        return x, y

    def score(self):
        with self.store.connect() as db:
            return ib.row_score(ib.island_rows(db, self.sid(self.a), 'dao_dua'), self.clock.t)

    def test_rows_follow_the_save(self):
        self.assertEqual(self.layout(), {})                                     # nothing designed: no row
        self.place('cay_dua')
        row = self.layout()['dao_dua']
        self.assertEqual((row['tier'], row['status']), (0, 'up'))
        self.assertEqual([v[1] for v in row['data']['d']], ['cay_dua'])
        self.assertEqual(row['pts'], D.decor_pts(['cay_dua']))
        x, y = self.spot('ghe_dai')
        self.command(self.a, 'jr_isle_dmove', island='dao_dua', id=1, x=x, y=y, r=0)
        self.assertEqual(self.layout()['dao_dua']['data']['d'][0][2:4], [x, y])
        self.command(self.a, 'jr_isle_expand', island='dao_dua', confirm=True)
        row = self.layout()['dao_dua']
        self.assertEqual(row['tier'], 1)
        self.assertEqual(row['pts'], D.decor_pts(['cay_dua']) + D.tier_pts(1))
        self.command(self.a, 'jr_isle_store', island='dao_dua', id=1)
        self.assertEqual(self.layout()['dao_dua']['pts'], D.tier_pts(1))         # the size keeps its points
        self.command(self.a, 'jr_island_sell', id='dao_dua', confirm=True)
        self.assertEqual(self.layout()['dao_dua']['status'], 'gone')
        self.command(self.a, 'jr_island_buy', id='dao_dua', confirm=True)
        self.assertEqual((self.layout()['dao_dua']['status'], self.layout()['dao_dua']['tier']), ('up', 1))   # bought again: its size

    def test_buildings_get_their_places_and_reset_and_erase(self):
        self.build(0, 'nha_san')
        self.assertEqual(self.layout(), {})                                     # an old-style building alone: no row (visitors
        self.place('cay_dua')                                                   # get its place from with_places)
        row = self.layout()['dao_dua']
        self.assertEqual(row['data']['b'], {'0': list(D.default_pos('dao_dua', 0, 0))})
        self.assertEqual(row['pts'], D.decor_pts(['cay_dua']))                  # the building's points stay on island_builds
        self.command(self.a, 'reset_all', confirm='BAT DAU LAI')
        self.assertEqual(self.layout()['dao_dua']['status'], 'gone')
        b = self.user('chudao3', 80_000_000)
        self.command(b, 'jr_island_buy', id='dao_dua', confirm=True)
        self.place('cay_dua', b)
        sid = self.sid(b)
        self.assertIn('dao_dua', self.layout(sid))
        self.store.delete(b)
        self.assertEqual(self.layout(sid), {})

    def test_visitors_see_the_design_and_every_building_place(self):
        self.build(0, 'nha_san')
        self.clock.t += 6 * H
        x, y = self.spot('ho_dai')
        self.command(self.a, 'jr_isle_build', island='dao_dua', kind='biet_thu', x=x, y=y, r=0, confirm=True)
        self.place('cay_dua')
        self.command(self.a, 'jr_isle_expand', island='dao_dua', confirm=True)
        trip = self.post(self.a, 'start', island='dao_dua', vehicle='')['trip']
        design = trip['design']
        self.assertEqual(design['t'], 1)
        self.assertEqual([v[1] for v in design['d']], ['cay_dua'])
        plots = sorted(int(b['p']) for b in trip['builds'])
        self.assertEqual(sorted(int(p) for p in design['b']), plots)            # each building has its place
        self.assertEqual(design['b'][str(plots[-1])], [x, y, 0])                 # the one placed on the grid where it was put
        self.assertEqual(trip['score'], self.score() + design['pts'])
        self.post(self.a, 'public', trip=trip['id'], open=True)
        seen = self.post(self.x[0], 'visit', trip=trip['id'])
        v = seen['visiting'][0]
        self.assertEqual(v['design']['d'], design['d'])
        self.assertEqual(v['design']['b'], design['b'])
        self.assertNotIn(self.sid(self.a), json.dumps(seen))

    def test_the_board_adds_design_points_never_less(self):
        self.build(0, 'nha_san')
        self.clock.t += 6 * H
        with self.store.connect() as db:
            before = ilb._ranked(ilb._rows(db, False), self.clock.t, ilb._lays(db, False))
        mine = {c[0]: c[1] for c in before}
        self.assertEqual(mine[self.sid(self.a)], self.score())                  # the buildings' points, as before
        self.place('cay_dua')
        self.place('hoa_giay')
        with self.store.connect() as db:
            after = {c[0]: c[1] for c in ilb._ranked(ilb._rows(db, False), self.clock.t, ilb._lays(db, False))}
        self.assertEqual(after[self.sid(self.a)], mine[self.sid(self.a)] + D.decor_pts(['cay_dua', 'hoa_giay']))
        # an island with decorations and no building is on the board
        b = self.user('chudao4', 80_000_000)
        self.command(b, 'jr_island_buy', id='dao_dua', confirm=True)
        self.place('ho_dai', b)
        ilb.clear_cache()
        with self.store.connect() as db:
            ranked = ilb._ranked(ilb._rows(db, False), self.clock.t, ilb._lays(db, False))
        row = next(c for c in ranked if c[0] == self.sid(b))
        self.assertEqual((row[1], row[2], row[3]), (D.decor_pts(['ho_dai']), 'dao_dua', 0))
        self.assertEqual(ilb._public_row(row)['island']['id'], 'dao_dua')
