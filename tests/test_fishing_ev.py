"""🎣 Câu cá's economy (owner 24/10: "cần có giá tí để người ta câu cá kiếm tiền"; coordinator: no daily cap, EV per hour,
rods at 0 / 30.000 / 200.000 / 1.500.000 / 8.000.000 / 20.000.000 / 50.000.000, payback about 20–60 hours of fishing).

* game/fishing_content.expected integrates the model (power, the cast's distance over the rod's reach, the rod's zones, rỉa mồi, junk, rarity, species, weight, the
  bite wait, the reel, snaps, the haggled price) for decent play: each rod's xu per hour at its best public spot is within
  ±30 % of EV_TARGET_HOUR, and each rod pays itself back from the income it adds over the rod before it in 20–60 hours.
* The server's own dice (game/fishing._cast) agree with the model: a Monte Carlo of real casts lands within 20 % of the
  integrated xu per cast for the everyday rods.
* Bait meant for a rod is about even to a small edge there (−10 % … +20 % of the hour), never a money sink or a second income.
* 2.6.4 (owner 24/10: casting easy and random, 15–80 m up to 2 km; the hook back to 1–1,5 s; an easy reel): each rod
  lands in each zone as often as on 2.6.3, and the luck of the better rods came down as much as the easy reel lands
  more of their rare fish, so each rod's xu per hour stayed within 2 % of 2.6.3's (BEFORE_264).
* The reel (public/js/v4/fish-reel.js, tests/fishing-reel.mjs): a player who never looks at the needle (holds, lets go,
  at random) still lands ≥ 90 % of the common fish and ≥ 70 % of the 🔴 Cổ đại ones; one who watches lands at least
  SIM_REEL; nobody lands sooner than the server's REEL_MIN_SHARE of the fight."""
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


def report():
    rows, prev = [], None
    for r in C.RODS:
        hour, spot = C.best_hour(r['id'])
        e = C.expected(r['id'], spot)
        pay = r['price'] / (hour - prev) if prev is not None and hour > prev else None
        rows.append((r['id'], r['price'], spot, round(hour), round(e['cast'], 1), round(e['casts']), pay))
        prev = hour
    return rows


class EV(unittest.TestCase):
    def test_per_hour_targets(self):
        for rod, price, spot, hour, cast, casts, pay in report():
            target = C.EV_TARGET_HOUR[rod]
            self.assertTrue(0.7 * target <= hour <= 1.3 * target, f'{rod}: {hour} xu/h at {spot} vs {target}')
            self.assertTrue(120 <= casts <= 300, f'{rod}: {casts} casts an hour (15–30 s a round)')

    def test_easy_random_casting_kept_the_economy(self):
        for rod, (zones, hour) in BEFORE_264.items():
            now, spot = C.best_hour(rod)
            got = C.expected(rod, spot)['zones']
            for a, b in zip(got, zones):
                self.assertAlmostEqual(a, b, delta=0.01, msg=(rod, got, zones))
            self.assertTrue(0.98 * hour <= now <= 1.02 * hour, f'{rod}: {now:.0f} xu/h vs {hour} on 2.6.3')

    def test_payback_hours(self):
        for rod, price, spot, hour, cast, casts, pay in report():
            if price:
                self.assertTrue(20 <= pay <= 60, f'{rod}: pays back in {pay:.1f} h')

    def test_every_rod_earns_more_than_the_one_before(self):
        hours = [C.best_hour(r['id'])[0] for r in C.RODS]
        self.assertEqual(hours, sorted(hours))

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
