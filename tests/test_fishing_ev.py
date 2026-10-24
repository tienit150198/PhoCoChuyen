"""🎣 Câu cá's economy (owner 24/10: "cần có giá tí để người ta câu cá kiếm tiền"; coordinator: no daily cap, EV per hour,
rods at 0 / 30.000 / 200.000 / 1.500.000 / 8.000.000 / 20.000.000 / 50.000.000, payback about 20–60 hours of fishing).

* game/fishing_content.expected integrates the model (power, the cast's distance over the rod's reach, the rod's zones, rỉa mồi, junk, rarity, species, weight, the
  bite wait, the reel, snaps, the haggled price) for decent play: each rod's xu per hour at its best public spot is within
  ±30 % of EV_TARGET_HOUR. Each rod pays itself back from the income it adds over the rod before it (2.6.4: 20–60 hours;
  2.6.5: AFTER_265, from ≈39 h for Cần trúc down to ≈3 h for Long Vương; a better rod never pays back slower).
* The server's own dice (game/fishing._cast) agree with the model: a Monte Carlo of real casts lands within 20 % of the
  integrated xu per cast for the everyday rods.
* Bait meant for a rod is about even to a small edge there (−10 % … +20 % of the hour), never a money sink or a second income.
* 2.6.4 (owner 24/10: casting easy and random, 15–80 m up to 2 km; the hook back to 1–1,5 s; an easy reel): each rod
  lands in each zone as often as on 2.6.3, and the luck of the better rods came down as much as the easy reel lands
  more of their rare fish, so each rod's xu per hour stayed within 2 % of 2.6.3's (BEFORE_264: now the zone shares only).
* 2.6.5 (owner 24/10 "mua đồ xịn nhất rồi mà câu ra mấy cá dở quá … tỷ lệ cá to nhiều chứ, hoặc cá cổ đại"; his choice:
  "giá cá giảm 5% của cá lớn, tỷ lệ cá lớn ra cao hơn"): each rod's own odds per rarity in its farthest zone (ODDS), closer
  zones poorer, a better rod's fish a little heavier within each rarity, 🟣 Hiếm and up × 0,95 in price. The income of the
  better rods rises a lot (the owner's choice): AFTER_265 locks each rod's xu per hour and payback hours within 2 %.
* The reel (public/js/v4/fish-reel.js, tests/fishing-reel.mjs): a player who never looks at the needle (holds, lets go,
  at random) still lands ≥ 90 % of the common fish and ≥ 70 % of the 🔴 Cổ đại ones; one who watches lands at least
  SIM_REEL; nobody lands sooner than the server's REEL_MIN_SHARE of the fight."""
import functools
import json
import shutil
import subprocess
from pathlib import Path
import random
import unittest
from unittest import mock

from game import fishing as F
from game import fishing_content as C
from tests.test_bank import story


ROOT = Path(__file__).resolve().parents[1]

# 2.6.3 (power × 20–110 m × spread, decent play at 0.70–0.95 power): each rod's zone shares and xu per hour at its best spot.
BEFORE_264 = dict(tre=((0.911, 0.089, 0, 0), 5_144), truc=((0.545, 0.455, 0, 0), 5_893), carbon=((0, 0.911, 0.089, 0), 9_983),
                  bien=((0, 0.095, 0.891, 0.014), 41_595), vang=((0, 0, 0.646, 0.354), 210_776),
                  bach_kim=((0, 0, 0.217, 0.783), 635_372), long_vuong=((0, 0, 0.009, 0.991), 1_695_480))

# 2.6.5: each rod's xu per hour at its best public spot and the hours it pays itself back in (2.6.4: 5.111, 5.880 / 39,0 h,
# 9.992 / 48,6 h, 41.805 / 47,2 h, 211.101 / 47,3 h, 636.506 / 47,0 h, 1.690.655 / 47,4 h).
AFTER_265 = dict(tre=(5_103, None), truc=(5_865, 39.36), carbon=(12_200, 31.57), bien=(191_370, 8.37), vang=(1_164_677, 8.22),
                 bach_kim=(5_492_961, 4.62), long_vuong=(22_461_818, 2.95))
# 2.6.5: % per rarity (⚪ 🟢 🔵 🟣 🟠 🟡 🔴) each rod hooks in its farthest zone, spot and bait aside (fishing_content.rod_odds,
# what the 🎣 rod stall shows). 2.6.4: Long Vương in Sâu ≈ 49,6 / 29 / 14,1 / 5,4 / 1,4 / 0,32 / 0,08.
ODDS = dict(tre=(94.8, 4.74, 0.43, 0.03, 0, 0, 0), truc=(94.8, 4.74, 0.43, 0.03, 0, 0, 0),
            carbon=(80.99, 14.58, 3.5, 0.77, 0.15, 0.02, 0), bien=(34.97, 28.39, 20.0, 10.91, 4.51, 1.2, 0.01),
            vang=(22.11, 26.0, 24.43, 16.98, 7.96, 2.48, 0.03), bach_kim=(14.98, 23.07, 25.32, 19.77, 11.91, 3.95, 1.0),
            long_vuong=(10.11, 19.81, 24.96, 21.83, 15.16, 6.14, 2.0))


@functools.lru_cache(maxsize=None)
def report():
    rows, prev = [], None
    for r in C.RODS:
        hour, spot = C.best_hour(r['id'])
        e = C.expected(r['id'], spot)
        pay = r['price'] / (hour - prev) if prev is not None and hour > prev else None
        rows.append((r['id'], r['price'], spot, round(hour), round(e['cast'], 1), round(e['casts']), pay, tuple(e['zones'])))
        prev = hour
    return tuple(rows)


class EV(unittest.TestCase):
    def test_per_hour_targets(self):
        for rod, price, spot, hour, cast, casts, pay, zones in report():
            target = C.EV_TARGET_HOUR[rod]
            self.assertTrue(0.7 * target <= hour <= 1.3 * target, f'{rod}: {hour} xu/h at {spot} vs {target}')
            self.assertTrue(120 <= casts <= 300, f'{rod}: {casts} casts an hour (15–30 s a round)')

    def test_easy_random_casting_kept_the_zones(self):
        rows = {x[0]: x for x in report()}
        for rod, (zones, hour) in BEFORE_264.items():
            got = rows[rod][-1]
            for a, b in zip(got, zones):
                self.assertAlmostEqual(a, b, delta=0.01, msg=(rod, got, zones))

    def test_better_odds_set_the_new_economy(self):
        prev = None
        for rod, price, spot, hour, cast, casts, pay, zones in report():
            want, want_pay = AFTER_265[rod]
            self.assertTrue(0.98 * want <= hour <= 1.02 * want, f'{rod}: {hour} xu/h vs {want} on 2.6.5')
            if want_pay is None:
                continue
            self.assertTrue(0.98 * want_pay <= pay <= 1.02 * want_pay, f'{rod}: pays back in {pay:.2f} h vs {want_pay}')
            self.assertTrue(prev is None or pay <= prev, f'{rod}: a better rod pays back no slower ({pay:.1f} h vs {prev} h)')
            prev = pay

    def test_every_rod_earns_more_than_the_one_before(self):
        hours = [x[3] for x in report()]
        self.assertEqual(hours, sorted(hours))

    def test_rod_odds(self):
        for rod, want in ODDS.items():
            got = C.rod_odds(rod)
            self.assertAlmostEqual(sum(got), 100, places=6)
            for r, (a, b) in enumerate(zip(got, want)):
                self.assertAlmostEqual(a, b, delta=0.02 + 0.01 * b, msg=(rod, r, [round(x, 2) for x in got]))
        lv = C.rod_odds('long_vuong')   # the owner's "cá to nhiều": about a quarter of Long Vương's fish 🟠 Sử thi or better
        self.assertGreater(sum(lv[4:]), 22)
        self.assertLessEqual(lv[0], 11)
        for r in C.RODS:   # closer zones stay poorer for the same rod; 🔴 only with `ancient` (else × ANCIENT_GATE)
            big = [sum(C.rod_odds(r['id'], z)[3:]) for z in range(len(C.ZONES))]
            self.assertEqual(big, sorted(big), r['id'])
            if not r['ancient']:
                self.assertLess(C.rod_odds(r['id'])[-1], 0.05, r['id'])
        cat = {x['id']: x for x in F.catalogue()['rods']}
        for r in C.RODS:   # the 🎣 rod stall shows exactly these
            self.assertEqual(cat[r['id']]['odds'], [round(x, 2) for x in C.rod_odds(r['id'])])
            self.assertEqual(cat[r['id']]['far'], C.far_zone(r['id']))

    def test_better_rods_land_heavier_fish(self):
        # within a rarity a better rod leans to heavier fish (owner "cá to nhiều"), modestly: f = u ** skew_of, E[f] = 1 / (1 + skew)
        mean_f = lambda rod, z: 1 / (1 + C.skew_of(z, rod))   # noqa: E731
        sau = len(C.ZONES) - 1
        means = [mean_f(r['id'], sau) for r in C.RODS]
        self.assertEqual(means, sorted(means))
        self.assertTrue(0.05 <= means[-1] - means[0] <= 0.1, means)
        for r in C.RODS:   # still: farther zones, heavier fish
            fs = [mean_f(r['id'], z) for z in range(len(C.ZONES))]
            self.assertEqual(fs, sorted(fs), r['id'])

    def test_big_fish_price_cut(self):
        old = ((10, 150), (150, 600), (800, 3_000), (5_000, 20_000), (40_000, 150_000), (400_000, 1_500_000), (3_000_000, 10_000_000))
        for r, (band, was) in enumerate(zip((x['price'] for x in C.RARITIES), old)):
            k = 0.95 if r >= 3 else 1.0
            self.assertEqual(band, (round(was[0] * k), round(was[1] * k)), r)

    def test_bait_pays_for_itself_on_its_rod(self):
        for rod, bait in (('tre', 'giun'), ('carbon', 'tom'), ('bien', 'moi_gia'), ('vang', 'phat_sang'), ('long_vuong', 'huyen_thoai')):
            spot = C.best_hour(rod)[1]
            plain, used = C.expected(rod, spot), C.expected(rod, spot, bait)
            net = used['hour'] - used['bait'] - plain['hour']
            self.assertGreaterEqual(net, -0.1 * plain['hour'], (rod, bait, net))   # giun: faster bites, about even
            self.assertLessEqual(net, 0.2 * plain['hour'], (rod, bait, net))      # an edge, not a second income

    def test_the_server_rolls_like_the_model(self):
        """Real casts (game/fishing._cast), decent play as the model's SIM_*: hook sim_hook(rod), land SIM_REEL[r] unless fated to snap."""
        cond = dict(night=False, rain=False, month=6)
        for rod in ('tre', 'truc', 'carbon'):
            spot = C.best_hour(rod)[1]
            rng = random.Random(11)
            s = story(wallet=0)
            d = F.ensure(s)
            d['rods'] = list(C.ROD_IDS)
            d['rod'] = rod
            total, n = 0.0, 20_000
            with mock.patch.object(F.secrets, 'SystemRandom', lambda: rng), mock.patch.object(C, 'conditions', lambda t: cond):
                for _ in range(n):
                    power = rng.uniform(*C.SIM_POWER)
                    F._cast(s, d, dict(spot=spot, power=power), 1_790_000_000.0)
                    a = d['act']
                    if a and a['kind'] == 'fish' and not a['snap'] and rng.random() < C.sim_hook(rod) * C.SIM_REEL[C.SPECIES[a['sp']]['r']]:
                        total += C.price(a['sp'], a['g']) * C.HAGGLE_EV
            mc, model = total / n, C.expected(rod, spot)['cast']
            self.assertTrue(0.8 * model <= mc <= 1.2 * model, f'{rod} at {spot}: {mc:.1f} vs model {model:.1f} xu/cast')


class Reel(unittest.TestCase):
    def test_green_zone_is_wide(self):
        for sp in C.SPECIES.values():
            for rod in C.RODS:
                kg = C.weight_of(sp, 0.5)
                g = C.fight_of(sp['r'], kg, rod['id'])['green']
                self.assertGreaterEqual(g, C.GREEN_MIN)
                if sp['r'] == 0 and kg <= rod['line'] / 2:
                    self.assertTrue(0.45 <= g <= 0.55, (sp['id'], rod['id'], g))

    def test_landing_rates(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node is not installed')
        cases = []
        for sp in C.SPECIES.values():   # a mid-weight fish of each species on the first rod whose line holds it
            r, kg = sp['r'], C.weight_of(sp, 0.5)
            rod = next(x for x in C.RODS if x['line'] >= kg and (r < C.NR - 1 or x['ancient']))
            cases.append(dict(r=r, h=dict(C.fight_of(r, kg, rod['id']), secs=round(C.reel_of(r, 0.5, rod['id']), 2))))
        out = subprocess.run([node, str(ROOT / 'tests' / 'fishing-reel.mjs')], input=json.dumps(cases), cwd=ROOT, capture_output=True,
                             text=True, encoding='utf-8', timeout=300, env=dict(__import__('os').environ, REEL_N='120'))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        got = json.loads(out.stdout)
        casual, decent = got['casual'], got['decent']
        self.assertGreaterEqual(min(casual[:2]), 0.9, casual)
        self.assertGreaterEqual(casual[-1], 0.7, casual)
        self.assertEqual(casual, sorted(casual, reverse=True), 'rarer fish stay a bit harder')
        for r in range(C.NR):
            self.assertGreaterEqual(decent[r], C.SIM_REEL[r], (r, decent))
        self.assertGreaterEqual(got['fastest'], C.REEL_MIN_SHARE, 'the server never refuses a fair landing as too early')


if __name__ == '__main__':
    for row in report():
        print(row)
    unittest.main()
