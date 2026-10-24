"""🎣 Câu cá's economy (owner 24/10: "cần có giá tí để người ta câu cá kiếm tiền"; coordinator: no daily cap, EV per hour,
rods at 0 / 30.000 / 200.000 / 1.500.000 / 8.000.000 / 20.000.000 / 50.000.000, payback about 20–60 hours of fishing).

* game/fishing_content.expected integrates the model (power, spread, zones, rỉa mồi, junk, rarity, species, weight, the
  bite wait, the reel, snaps, the haggled price) for decent play: each rod's xu per hour at its best public spot is within
  ±30 % of EV_TARGET_HOUR, and each rod pays itself back from the income it adds over the rod before it in 20–60 hours.
* The server's own dice (game/fishing._cast) agree with the model: a Monte Carlo of real casts lands within 20 % of the
  integrated xu per cast for the everyday rods.
* Bait meant for a rod is about even to a small edge there (−10 % … +20 % of the hour), never a money sink or a second income."""
import random
import unittest
from unittest import mock

from game import fishing as F
from game import fishing_content as C
from tests.test_bank import story


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


if __name__ == '__main__':
    for row in report():
        print(row)
    unittest.main()
