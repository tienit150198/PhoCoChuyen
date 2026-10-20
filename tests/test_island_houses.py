"""🏡 Kiểu nhà trên đảo (owner 20/10 "coi hướng đảo có thể xây nhà các kiểu đẹp và nhiều hơn"): the house styles of
game/island_build_content.py HOUSES in four tiers, their colours stored in the kind ('<style>__<n>': no new save key,
no column), 🎨 sơn lại (jr_isle_paint), the limits counted by style whatever the colour, the board counting a style
once, and the same list, tiers and colour names as the art (public/js/house-art.js) both interfaces draw."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import island_build as ib
from game import island_build_content as C
from game.engine import validate_state
from tests.test_bank import act
from tests.test_island import money, refused
from tests.test_island_build import B, H, Timed

ROOT = Path(__file__).resolve().parents[1]
M = 1_000_000


class Styles(unittest.TestCase):
    def test_tiers_prices_and_points(self):
        last = {}
        for h in C.HOUSES:
            self.assertIn(h['tier'], (1, 2, 3, 4), h['id'])
            self.assertEqual(len(h['looks']), C.LOOKS)
            self.assertEqual(len(h['levels']), 3)
            self.assertTrue(len(h['id']) + 3 <= 24, h['id'])                   # '<id>__2' fits the kind's 24 characters
            l1 = h['levels'][0][0]
            self.assertTrue({1: (1 * M, 5 * M), 2: (5 * M, 9 * M), 3: (10 * M, 20 * M), 4: (25 * M, 40 * M)}[h['tier']][0] <= l1
                            <= {1: 5 * M, 2: 9 * M, 3: 20 * M, 4: 40 * M}[h['tier']], h['id'])
            self.assertLessEqual(sum(p for p, _ in h['levels']), 200 * M)       # never beyond the dearest island
            last.setdefault(h['tier'], []).append(l1)
            if h['tier'] == 4:
                self.assertTrue(h.get('big') and h.get('max') == 1, h['id'])
        self.assertLess(max(last[1]), min(last[3]))
        self.assertLess(max(last[3]), min(last[4]))
        self.assertEqual(ib.paint_price(ib.BUILD['nha_tranh']), C.PAINT_MIN)
        self.assertEqual(ib.paint_price(ib.BUILD['hoang_cung']), 3_500_000)

    def test_kinds_split(self):
        self.assertEqual(ib.split('pho_hoi_an__2'), ('pho_hoi_an', 2))
        self.assertEqual(ib.split('pho_hoi_an'), ('pho_hoi_an', 0))
        self.assertEqual(ib.split('pho_hoi_an__3'), ('pho_hoi_an__3', 0))       # more colours than it has: unknown
        self.assertEqual(ib.split('ho_boi__1'), ('ho_boi__1', 0))               # no colours: unknown
        self.assertEqual(ib.split('thap_moi__1'), ('thap_moi__1', 0))
        self.assertIsNone(ib.known('thap_moi__1'))
        self.assertEqual(ib.known('hanok__1')['id'], 'hanok')
        self.assertEqual(ib.kind_of('hanok', 0), 'hanok')

    def test_the_art_has_the_same_styles(self):
        if not shutil.which('node'):
            self.skipTest('node is not installed')
        prog = ("import('./public/js/house-art.js').then(m=>{const o={};for(const [k,h] of Object.entries(m.HOUSES)){"
                "const out=[];for(let lv=1;lv<=3;lv++)for(let v=0;v<3;v++){const x=m.houseModel(k,lv,v);out.push([x.parts.length,Math.round(x.top)]);}"
                "o[k]={tier:h.tier,pals:h.pals.map(p=>p.name),emoji:h.emoji,name:h.name,m:out};}console.log(JSON.stringify(o));})")
        out = subprocess.run(['node', '--input-type=module', '-e', prog], cwd=ROOT, capture_output=True, text=True, timeout=60, encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr)
        js = json.loads(out.stdout)
        self.assertEqual(list(js), [h['id'] for h in C.HOUSES])
        for h in C.HOUSES:
            a = js[h['id']]
            self.assertEqual((a['tier'], a['pals'], a['emoji'], a['name']), (h['tier'], list(h['looks']), h['emoji'], h['name']), h['id'])
            tops = [t for _, t in a['m']]
            self.assertTrue(all(n > 0 for n, _ in a['m']), h['id'])             # every level and colour draws something
            self.assertLessEqual(tops[0], tops[-1], h['id'])                    # a level never shrinks the house


class Painting(Timed):
    def test_build_in_a_colour_then_paint(self):
        s = self.owner('dao_dua', wallet=60 * M)
        refused(self, s, 'jr_isle_build', island='dao_dua', plot=0, kind='pho_hoi_an', look=3, confirm=True)
        refused(self, s, 'jr_isle_build', island='dao_dua', plot=0, kind='ho_boi', look=1, confirm=True)   # one colour only
        w = money(s)
        s, _ = act(s, 'jr_isle_build', island='dao_dua', plot=0, kind='pho_hoi_an', look=2, confirm=True)
        self.assertEqual(B(s)['p']['dao_dua']['0']['k'], 'pho_hoi_an__2')
        self.assertEqual(w - money(s), 6 * M)                                   # the colour is free when building
        s, r = act(s, 'jr_isle_build', island='dao_dua', plot=0, kind='pho_hoi_an', confirm=True)
        self.assertTrue(r.get('duplicate'))                                     # a second tap pays nothing
        # paint while it is still being built: allowed, paid at once, the work goes on
        refused(self, s, 'jr_isle_paint', island='dao_dua', plot=0, look=1)    # asks for confirmation
        refused(self, s, 'jr_isle_paint', island='dao_dua', plot=1, look=1, confirm=True)
        refused(self, s, 'jr_isle_paint', island='dao_dua', plot=0, look=1, kind='hanok', confirm=True)
        w = money(s)
        s, r = act(s, 'jr_isle_paint', island='dao_dua', plot=0, look=1, confirm=True)
        e = B(s)['p']['dao_dua']['0']
        self.assertEqual((e['k'], e['b'], w - money(s)), ('pho_hoi_an__1', 1, 600_000))
        self.assertEqual(e['x'], 6 * M + 600_000)                               # what it cost so far (the salvage counts it)
        s, r = act(s, 'jr_isle_paint', island='dao_dua', plot=0, look=1, confirm=True)
        self.assertTrue(r.get('duplicate'))
        s, _ = act(s, 'jr_isle_paint', island='dao_dua', plot=0, look=0, confirm=True)
        self.assertEqual(B(s)['p']['dao_dua']['0']['k'], 'pho_hoi_an')
        self.clock.t += 12 * H
        s, _ = act(s, 'jr_isle_up', island='dao_dua', plot=0, confirm=True)
        self.assertEqual(B(s)['p']['dao_dua']['0']['k'], 'pho_hoi_an')
        validate_state(s)
        s, _ = act(s, 'jr_isle_build', island='dao_dua', plot=1, kind='ho_boi', confirm=True)
        refused(self, s, 'jr_isle_paint', island='dao_dua', plot=1, look=1, confirm=True)   # a pool has one colour

    def test_limits_count_the_style_whatever_its_colour(self):
        s = self.owner('dao_hoang_hon', wallet=200 * M)
        s, _ = act(s, 'jr_isle_build', island='dao_hoang_hon', plot=0, kind='hoang_cung', look=1, confirm=True)
        refused(self, s, 'jr_isle_build', 'limit', island='dao_hoang_hon', plot=1, kind='hoang_cung', confirm=True)
        small = self.owner('dao_dua', wallet=60 * M)
        refused(self, small, 'jr_isle_build', 'small', island='dao_dua', plot=0, kind='dinh_thu', confirm=True)
        plots = [dict(k='hanok', l=1, b=0, t=0, x=0), dict(k='hanok__2', l=2, b=0, t=0, x=0)]
        self.assertEqual(ib.score(plots, self.clock.t), ib.BUILD['hanok']['pts'] * 3 + C.VARIETY)      # one style: variety once
        self.assertEqual(ib.score(plots + [dict(k='thap_moi__1', l=3, b=0, t=0, x=0)], self.clock.t), ib.BUILD['hanok']['pts'] * 3 + C.VARIETY)


if __name__ == '__main__':
    unittest.main()
