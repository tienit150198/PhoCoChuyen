"""🎣 Câu cá (game/fishing.py, game/fishing_content.py; owner 24/10): the content (122 species in 7 rarities, rods at the
owner's prices, baits, baskets), a round decided by the server at the cast (power × range × spread, tangling, zones, the
bite wait, junk and rỉa mồi), the hook window (per rod and bait, judged on the client's own measure so lag never costs
the fish; nibble taps keep the round), the reel's minimum time and the fated snap, receipts, no daily cap, the
🐟 Chợ cá (price, haggling: accept / bargain / decline, no re-roll by declining), the bag (keep, release, carry, tranh cá,
bể cá), 📖 Sổ cá milestones (xu once, earned titles and frame), the old leisure keepsakes moved into Sổ cá, saves of a
newer build (rollback), the public view (never the open round's fish) and the island cast checked at commit."""
import copy
import json
import random
import unittest
from unittest import mock

from game import fishing as F
from game import fishing_content as C
from game.engine import GameError, validate_state
from tests.test_bank import act, story

T0 = 1_790_000_000.0   # a fixed clock (VN afternoon is irrelevant: conditions are read from it)


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t


def run(s, name, clock, rng=None, **p):
    """One command through the engine at `clock` (seeded `rng` for the server's dice)."""
    with mock.patch.object(F, 'now', clock), mock.patch.object(F.secrets, 'SystemRandom', lambda: rng or random.Random(7)):
        return act(s, name, **p)


def put_round(s, kind='fish', sp='ca_chep', g=2500, at=T0, bite=T0 + 10, reel=4.0, snap=0, rod='tre', spot='ho', trip='', win=None):
    """A round as jr_fish_cast leaves it (to test hook / land without dice); `win` None: a round cast on 2.6.2 (no `win`)."""
    d = F.ensure(s)
    d['act'] = dict(id='a' * 32, at=at, spot=spot, trip=trip, rod=rod, dist=12.0, zone=0, kind=kind, sp=sp if kind != 'none' else '',
                    g=g if kind == 'fish' else 0, bite=bite, hook=0.0, reel=reel, snap=snap, nib=[])
    if win is not None:
        d['act']['win'] = win
    validate_state(s)
    return s


class Content(unittest.TestCase):
    def test_species_rarities_and_prices(self):
        self.assertGreaterEqual(len(C.SPECIES), 120)
        counts = [len(C.by_rarity(r)) for r in range(C.NR)]
        self.assertEqual(counts, [28, 24, 20, 18, 14, 10, 8])
        self.assertEqual(len({x['name'] for x in C.SPECIES.values()}), len(C.SPECIES), 'names are unique')
        for sp in C.SPECIES.values():
            self.assertRegex(sp['id'], F.SP_RE)
            self.assertTrue(sp['spots'] and set(sp['spots']) <= set(C.SPOTS), sp['id'])
            lo, hi = sp['w']
            self.assertLess(0, lo)
            self.assertLessEqual(lo, hi)
            band = C.RARITIES[sp['r']]['price']
            for g in (C.grams(lo), C.grams(hi)):
                self.assertTrue(band[0] * 0.99 <= C.price(sp['id'], g) <= band[1] * 1.01, (sp['id'], g, C.price(sp['id'], g)))
        for spot in C.SPOTS:
            for r in range(C.NR):
                self.assertTrue(C.pool(spot, r, dict(night=False, rain=False, month=6)) or r >= 5 or spot == 'dao', (spot, r))
        for sp in C.LEGACY:
            self.assertIn(sp, C.SPECIES)

    def test_rods_baits_baskets(self):
        self.assertEqual({r['id']: r['price'] for r in C.RODS},
                         dict(tre=0, truc=30_000, carbon=200_000, bien=1_500_000, vang=8_000_000, bach_kim=20_000_000, long_vuong=50_000_000))
        prev = None
        for r in C.RODS:   # every step up reaches further, holds more and is luckier
            if prev:
                self.assertGreater(r['range'], prev['range'])
                self.assertGreater(r['line'], prev['line'])
                self.assertGreaterEqual(r['luck'], prev['luck'])
            prev = r
        self.assertEqual([r['id'] for r in C.RODS if r['ancient']], ['bach_kim', 'long_vuong'])
        self.assertEqual(C.BASKETS[0]['price'], 0)
        self.assertTrue(all(b['price'] > 0 and b['n'] > 0 for b in C.BAITS))

    def test_hook_window_per_rod_and_bait(self):
        """Owner 24/10 "giật dễ hơn": 3 s on the bamboo rod, longer on every better rod, about 4 s on Long Vương; a bait may add."""
        wins = [C.hook_window(r['id']) for r in C.RODS]
        self.assertEqual(wins[0], 3.0)
        self.assertEqual(wins[-1], 4.0)
        self.assertEqual(wins, sorted(set(wins)), 'each rod up holds the bite longer')
        self.assertEqual(C.HOOK_WINDOW, 3.0)
        self.assertEqual(C.hook_window('tre', 'giun'), 3.0)
        self.assertEqual(C.hook_window('long_vuong', 'huyen_thoai'), 4.3)
        self.assertTrue(all(0 <= b.get('hook', 0) <= 0.5 for b in C.BAITS))
        self.assertEqual(C.hook_window('a_newer_rod'), C.HOOK_WINDOW)
        cat = F.catalogue()
        self.assertEqual([r['hook'] for r in cat['rods']], wins)
        self.assertEqual(cat['hook_scare'], C.HOOK_SCARE)
        self.assertTrue(0.94 <= C.sim_hook('tre') < C.sim_hook('long_vuong') < 1)

    def test_catalogue_is_static_json(self):
        cat = F.catalogue()
        json.dumps(cat)
        self.assertEqual(len(cat['species']), len(C.SPECIES))
        self.assertEqual([r['price'] for r in cat['rods']], [r['price'] for r in C.RODS])

    def test_waits_reel_and_snap(self):
        for r, (lo, hi) in enumerate(C.WAIT):
            self.assertEqual(C.wait_of(r, 0, 0), lo)
            self.assertEqual(C.wait_of(r, 1, 1), hi)
            self.assertLess(C.wait_of(r, 0.1, 0.5), C.wait_of(r, 0.9, 0.5), 'a longer wait: a heavier fish')
        self.assertEqual(C.WAIT[0], (5, 15))
        self.assertEqual(C.WAIT[-1][1], 45)
        self.assertEqual(C.snap_chance(5, 'tre'), 0.0)
        self.assertGreater(C.snap_chance(12, 'tre'), C.snap_chance(7, 'tre'))
        self.assertEqual(C.snap_chance(1000, 'tre'), 1.0)


    def test_art_in_node(self):
        """Every species draws (public/js/v4/fish-art.js), in the hands, as tranh cá and in the aquarium: tests/fishing-art.mjs."""
        import shutil
        import subprocess
        from pathlib import Path
        node = shutil.which('node')
        if not node:
            self.skipTest('node is not installed')
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run([node, str(root / 'tests' / 'fishing-art.mjs')], input=json.dumps(F.catalogue()['species'], ensure_ascii=False),
                             cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])


class Cast(unittest.TestCase):
    def test_distance_zone_and_view(self):
        rods = {'tre': 20}
        for seed in range(40):
            s = story(wallet=1000)
            s, r = run(s, 'jr_fish_cast', Clock(), random.Random(seed), spot='ho', power=0.8)
            c = r['cast']
            if c.get('tangle'):
                self.fail('no tangling at 0.8')
            self.assertTrue(0.8 * 0.8 * rods['tre'] - 0.01 <= c['dist'] <= 0.8 * 1.2 * rods['tre'] + 0.01, c['dist'])
            self.assertEqual(c['zone'], C.zone_of(c['dist']))
            self.assertEqual(c['splash'], T0 + C.CAST_SECONDS)
            a = s['journey']['fish']['act']
            self.assertNotIn('sp', c)
            self.assertNotIn('g', c)
            self.assertEqual(c['window'], C.hook_window('tre'))
            self.assertEqual(s['journey']['fish']['act']['win'], c['window'])
            if a['kind'] == 'none':
                self.assertIn('gone', c)
                self.assertNotIn('bite', c)
            else:
                self.assertIn('bite', c)
                lo, hi = (C.JUNK_WAIT if a['kind'] == 'junk' else C.WAIT[C.SPECIES[a['sp']]['r']])
                self.assertTrue(lo * 0.85 - 0.01 <= a['bite'] - c['splash'] <= hi + 0.01, (a['kind'], a['bite'] - c['splash']))
            for n in c['nib']:
                self.assertLess(n, a['bite'])
            pub = F.public(s)
            self.assertNotIn('act', pub)
            self.assertNotIn(a['sp'] or 'x', json.dumps(pub['bag']))

    def test_overpower_tangles_sometimes_and_never_below_sweet(self):
        tangles = 0
        for seed in range(60):
            s, r = run(story(wallet=1000), 'jr_fish_cast', Clock(), random.Random(seed), spot='ho', power=1)
            tangles += bool(r['cast'].get('tangle'))
            if r['cast'].get('tangle'):
                self.assertIsNone(s['journey']['fish']['act'])
        self.assertTrue(10 < tangles < 40, tangles)

    def test_bad_payloads_and_island(self):
        s = story(wallet=1000)
        for p in (dict(spot='ho', power=1.5), dict(spot='ho', power=-0.1), dict(spot='mars', power=0.5), dict(spot='ho', power='1'),
                  dict(spot='ho', power=0.5, x=1), dict(spot='dao', power=0.5), dict(spot='ho', power=0.5, trip='0' * 16),
                  dict(spot='ho', power=float('nan'))):
            with self.assertRaises(GameError):
                run(s, 'jr_fish_cast', Clock(), **p)
        s, r = run(s, 'jr_fish_cast', Clock(), spot='dao', power=0.5, trip='ab' * 8)
        self.assertEqual(s['journey']['fish']['act']['trip'], 'ab' * 8)

    def test_no_daily_cap_bag_full_and_bait(self):
        s = story(wallet=10**6)
        clock = Clock()
        for i in range(120):   # far beyond any old daily cap
            clock.t += 30
            s, _ = run(s, 'jr_fish_cast', clock, random.Random(i), spot='ho', power=0.5)
        self.assertEqual(s['journey']['fish']['tot']['cast'], 120)
        d = s['journey']['fish']
        d['bag'] = [dict(i=k + 1, s='ca_ro', g=100, d=1, p=0, k=0, o=0, od=0) for k in range(20)]
        d['seq'] = 20
        with self.assertRaises(GameError) as e:
            run(s, 'jr_fish_cast', clock, spot='ho', power=0.5)
        self.assertEqual(e.exception.code, 'bag_full')
        d['bag'] = []
        s, r = run(s, 'jr_fish_buy', clock, kind='bait', item='giun')
        self.assertEqual(s['journey']['fish']['bait'], {'giun': C.BAIT['giun']['n']})
        self.assertEqual(s['journey']['fish']['use'], 'giun')
        s, r = run(s, 'jr_fish_cast', clock, spot='ho', power=0.5)
        self.assertEqual(s['journey']['fish']['bait'], {'giun': C.BAIT['giun']['n'] - 1})


class Rounds(unittest.TestCase):
    def setUp(self):
        self.s = put_round(story(wallet=1000))

    def test_early_late_and_none(self):
        """An older client ({round} alone): judged by the receipt, with the 3 s window."""
        s, r = run(self.s, 'jr_fish_hook', Clock(T0 + 5), round='a' * 32)
        self.assertEqual(r['hook'], dict(lost='early'))
        self.assertIsNone(s['journey']['fish']['act'])
        s, r = run(self.s, 'jr_fish_hook', Clock(T0 + 10 + 3.0 + C.HOOK_LATE + 0.1), round='a' * 32)
        self.assertEqual(r['hook'], dict(lost='late'))
        s, r = run(self.s, 'jr_fish_hook', Clock(T0 + 10 + 3.0 + C.HOOK_LATE - 0.1), round='a' * 32)
        self.assertIn('secs', r['hook'])
        s, r = run(self.s, 'jr_fish_hook', Clock(T0 + 10 - C.HOOK_EARLY + 0.05), round='a' * 32)
        self.assertIn('secs', r['hook'])
        for p in (dict(), dict(ms=800), dict(early=True)):   # rỉa mồi: a tap ends it as before, whatever it says
            s, r = run(put_round(story(wallet=1000), kind='none'), 'jr_fish_hook', Clock(T0 + 10), round='a' * 32, **p)
            self.assertEqual(r['hook'], dict(lost='none'))
            self.assertEqual(s['journey']['fish']['tot']['miss'], 1)
        with self.assertRaises(GameError):
            run(self.s, 'jr_fish_hook', Clock(T0 + 10), round='b' * 32)

    def test_the_window_is_the_rods(self):
        s = put_round(story(wallet=1000), rod='long_vuong', win=4.3)
        _, r = run(s, 'jr_fish_hook', Clock(T0 + 14), round='a' * 32, ms=4200)
        self.assertIn('secs', r['hook'])
        _, r = run(s, 'jr_fish_hook', Clock(T0 + 14), round='a' * 32, ms=4301)
        self.assertEqual(r['hook'], dict(lost='late'))
        s = put_round(story(wallet=1000), rod='long_vuong')   # cast on 2.6.2: no `win`, the rod's own
        self.assertEqual(F.window_of(s['journey']['fish']['act']), 4.0)
        _, r = run(s, 'jr_fish_hook', Clock(T0 + 14), round='a' * 32, ms=3990)
        self.assertIn('secs', r['hook'])

    def test_a_tap_during_the_nibbles_keeps_the_round(self):
        """Owner 24/10: tapping while the fish only nibbles no longer loses it. A tap the server receives before the bite could
        have shown is ignored (the round stays open, nothing counted); the client's own HOOK_SCARE taps run out: `early`."""
        s, r = run(self.s, 'jr_fish_hook', Clock(T0 + 5), round='a' * 32, ms=0)
        self.assertEqual(r['hook'], dict(wait=True))
        self.assertIn('Chưa cắn', r['message'])
        a = s['journey']['fish']['act']
        self.assertEqual((a['id'], a['hook']), ('a' * 32, 0))
        self.assertEqual(s['journey']['fish']['tot']['miss'], 0)
        s, r = run(s, 'jr_fish_hook', Clock(T0 + 10 - C.HOOK_EARLY + 0.01), round='a' * 32, ms=300)   # the slack
        self.assertIn('secs', r['hook'])
        s, r = run(self.s, 'jr_fish_hook', Clock(T0 + 6), round='a' * 32, early=True)
        self.assertEqual(r['hook'], dict(lost='early'))
        self.assertIsNone(s['journey']['fish']['act'])
        self.assertEqual(s['journey']['fish']['tot']['miss'], 1)
        self.assertEqual(C.HOOK_SCARE, 3)

    def test_lag_never_costs_the_fish(self):
        """[slow-cmd] 1628 ms jr_fish_hook … save=12127KB: the cast's answer and the tap each lose 1–2 s. The client's own
        measure from the bite it drew decides; the receipt only has to be after the bite and within window + HOOK_LAG."""
        win = C.hook_window('tre')
        for late_by, ms in ((win + 2.5, 900), (win + 5, 2900), (win + C.HOOK_LAG - 0.1, 3000)):
            s, r = run(self.s, 'jr_fish_hook', Clock(T0 + 10 + late_by), round='a' * 32, ms=ms)
            self.assertIn('secs', r['hook'], (late_by, ms))
        hooked_at = T0 + 10 + win + C.HOOK_LAG - 0.1
        self.assertEqual(s['journey']['fish']['act']['hook'], hooked_at)
        # the landing counts from the hook's receipt: a slow save on the hook only adds to the fight's time
        with self.assertRaises(GameError) as e:
            run(s, 'jr_fish_land', Clock(hooked_at + 4.0 * C.REEL_MIN_SHARE - 0.2), round='a' * 32, ok=True)
        self.assertEqual(e.exception.code, 'too_early')
        _, r = run(s, 'jr_fish_land', Clock(hooked_at + 4.0 * C.REEL_MIN_SHARE), round='a' * 32, ok=True)
        self.assertEqual(r['land']['res'], 'fish')
        # out of bounds: the claim past the window, the receipt past window + lag
        s, r = run(self.s, 'jr_fish_hook', Clock(T0 + 11), round='a' * 32, ms=win * 1000 + 1)
        self.assertEqual(r['hook'], dict(lost='late'))
        s, r = run(self.s, 'jr_fish_hook', Clock(T0 + 10 + win + C.HOOK_LAG + 0.1), round='a' * 32, ms=200)
        self.assertEqual(r['hook'], dict(lost='late'))

    def test_bad_hook_payloads(self):
        for p in (dict(ms=-1), dict(ms='800'), dict(ms=float('nan')), dict(ms=float('inf')), dict(ms=10**9), dict(ms=True),
                  dict(early=False), dict(early=1), dict(ms=100, early=True), dict(ms=100, x=1)):
            with self.assertRaises(GameError, msg=p) as e:
                run(self.s, 'jr_fish_hook', Clock(T0 + 11), round='a' * 32, **p)
            self.assertEqual(e.exception.code, 'bad_round', p)

    def hooked(self, **kw):
        s = put_round(story(wallet=1000), **kw)
        s, r = run(s, 'jr_fish_hook', Clock(T0 + 10.3), round='a' * 32)
        return s, r['hook']

    def test_land_needs_the_reel_time_and_counts_once(self):
        s, h = self.hooked()
        self.assertEqual(h['secs'], 4.0)
        self.assertFalse(h['heavy'])
        self.assertIsNone(h['snap_at'])
        with self.assertRaises(GameError) as e:
            run(s, 'jr_fish_land', Clock(T0 + 10.3 + 1.0), round='a' * 32, ok=True)
        self.assertEqual(e.exception.code, 'too_early')
        s2, r = run(s, 'jr_fish_land', Clock(T0 + 10.3 + 2.5), round='a' * 32, ok=True)
        c = r['land']['catch']
        self.assertEqual((r['land']['res'], c['s'], c['g'], c['new']), ('fish', 'ca_chep', 2500, True))
        self.assertEqual(c['price'], C.price('ca_chep', 2500))
        d = s2['journey']['fish']
        self.assertEqual([(f['s'], f['g']) for f in d['bag']], [('ca_chep', 2500)])
        self.assertEqual(d['dex']['ca_chep'][:2], [1, 2500])
        s3, r = run(s2, 'jr_fish_land', Clock(T0 + 14), round='a' * 32, ok=True)   # a retried request: the receipt
        self.assertTrue(r['duplicate'])
        self.assertEqual(len(s3['journey']['fish']['bag']), 1)

    def test_a_lost_fight_may_end_early_and_expired_rounds_close(self):
        s, _ = self.hooked()
        s2, r = run(s, 'jr_fish_land', Clock(T0 + 11), round='a' * 32, ok=False)
        self.assertEqual(r['land']['res'], 'miss')
        self.assertFalse(s2['journey']['fish']['bag'])
        with self.assertRaises(GameError) as e:
            run(s, 'jr_fish_land', Clock(T0 + C.ROUND_TTL + 1), round='a' * 32, ok=True)
        self.assertEqual(e.exception.code, 'expired')

    def test_a_fish_too_heavy_snaps(self):
        s, h = self.hooked(sp='ca_tram', g=9000, snap=1)
        self.assertTrue(h['heavy'])
        self.assertIsNotNone(h['snap_at'])
        s2, r = run(s, 'jr_fish_land', Clock(T0 + 12), round='a' * 32, ok=True)   # a fated snap: early is fine, ok or not
        self.assertEqual(r['land'], dict(res='snap', heavy=True))
        self.assertFalse(s2['journey']['fish']['bag'])

    def test_junk(self):
        s, h = self.hooked(kind='junk', sp='dep', reel=2.0)
        s2, r = run(s, 'jr_fish_land', Clock(T0 + 12), round='a' * 32, ok=True)
        self.assertEqual(r['land'], dict(res='junk', junk='dep'))
        self.assertFalse(s2['journey']['fish']['bag'])


class Market(unittest.TestCase):
    def bagged(self, *fish):
        s = story(wallet=1000)
        d = F.ensure(s)
        d['bag'] = [dict(i=k + 1, s=sp, g=g, d=1, p=0, k=0, o=0, od=0) for k, (sp, g) in enumerate(fish)]
        d['seq'] = len(fish)
        validate_state(s)
        return s

    def roll(self, *values):
        r = mock.Mock()
        r.random.side_effect = list(values)
        r.randint.side_effect = lambda a, b: 80
        return r

    def test_plain_sale(self):
        s = self.bagged(('ca_chep', 2000), ('ca_ro', 300))
        full = C.price('ca_chep', 2000) + C.price('ca_ro', 300)
        s2, r = run(s, 'jr_fish_sell', Clock(), self.roll(0.9), ids=[1, 2])
        self.assertEqual(r['sold'], dict(n=2, xu=full))
        self.assertEqual(s2['journey']['wallet'], 1000 + full)
        self.assertFalse(s2['journey']['fish']['bag'])

    def test_haggle_accept_decline_bargain(self):
        s = self.bagged(('ca_chep', 2000))
        full = C.price('ca_chep', 2000)
        s, r = run(s, 'jr_fish_sell', Clock(), self.roll(0.01), ids=[1])
        self.assertEqual(r['deal'], dict(ids=[1], full=full, offer=full * 80 // 100, pct=round(100 * (full * 80 // 100) / full)))
        self.assertEqual(s['journey']['wallet'], 1000)
        # decline: kept; selling again the same day gets the same offer (no re-roll by declining)
        s, r = run(s, 'jr_fish_deal', Clock(), pick='decline')
        self.assertEqual(len(s['journey']['fish']['bag']), 1)
        s, r = run(s, 'jr_fish_sell', Clock(T0 + 5), self.roll(0.9), ids=[1])
        self.assertEqual(r['deal']['offer'], full * 80 // 100)
        s2, r = run(s, 'jr_fish_deal', Clock(T0 + 6), pick='accept')
        self.assertEqual(s2['journey']['wallet'], 1000 + full * 80 // 100)
        # bargain: full / bonus / refused
        s3, r = run(s, 'jr_fish_deal', Clock(T0 + 6), self.roll(0.2), pick='bargain')
        self.assertEqual(s3['journey']['wallet'], 1000 + full)
        s3, r = run(s, 'jr_fish_deal', Clock(T0 + 6), self.roll(0.5), pick='bargain')
        self.assertEqual(s3['journey']['wallet'], 1000 + full * 108 // 100)
        s3, r = run(s, 'jr_fish_deal', Clock(T0 + 6), self.roll(0.9), pick='bargain')
        self.assertEqual(r['bargain'], 'refused')
        self.assertEqual(s3['journey']['wallet'], 1000)
        self.assertEqual(s3['journey']['fish']['bag'][0]['o'], -1)
        with self.assertRaises(GameError) as e:   # refused for the rest of the day
            run(s3, 'jr_fish_sell', Clock(T0 + 7), self.roll(0.9), ids=[1])
        self.assertEqual(e.exception.code, 'refused')
        s4, r = run(s3, 'jr_fish_sell', Clock(T0 + 86400 * 2), self.roll(0.9), ids=[1])   # another day
        self.assertEqual(r['sold']['xu'], full)

    def test_offer_expires(self):
        s = self.bagged(('ca_chep', 2000))
        s, r = run(s, 'jr_fish_sell', Clock(), self.roll(0.01), ids=[1])
        with self.assertRaises(GameError):
            run(s, 'jr_fish_deal', Clock(T0 + C.DEAL_TTL + 1), pick='accept')

    def test_bag_actions(self):
        s = self.bagged(('ca_chep', 2000), (C.by_rarity(3)[0]['id'], 5000), ('ca_ro', 200), ('ca_ro', 250))
        s, r = run(s, 'jr_fish_keep', Clock(), id=1, on=True)
        self.assertEqual(s['journey']['fish']['bag'][0]['k'], 1)
        with self.assertRaises(GameError):
            run(s, 'jr_fish_carry', Clock(), id=1)   # ⚪ too small to carry
        s, r = run(s, 'jr_fish_carry', Clock(), id=2)
        x = C.by_rarity(3)[0]
        self.assertEqual(F.carried(s), dict(sp=x['id'], r=3, kg=5.0, fam=x['fam'], body=x['body'], belly=x['belly'], fin=x['fin'], pat=x['pat']))
        from live import fish_carry
        self.assertEqual(fish_carry.clean(dict(sp=x['id'], kg=5.0)) if x['w'][0] <= 5 <= x['w'][1] else F.carried(s), F.carried(s))
        s, r = run(s, 'jr_fish_aqua', Clock(), id=2)
        self.assertEqual(s['journey']['fish']['carry'], 0)
        self.assertEqual(s['journey']['fish']['aq'], [[C.by_rarity(3)[0]['id'], 5000]])
        s, r = run(s, 'jr_fish_aqua', Clock(), out=0)
        self.assertEqual(len(s['journey']['fish']['bag']), 4)
        s, r = run(s, 'jr_fish_mount', Clock(), id=1)
        uid, = s['journey']['fish']['tro']
        self.assertTrue(any(x['id'] == uid and x['k'] == 'tranh_ca' for x in s['journey']['reno']['items']))
        s, r = run(s, 'jr_fish_release', Clock(), ids=[3, 4])
        self.assertEqual([f['s'] for f in s['journey']['fish']['bag']], [C.by_rarity(3)[0]['id']])   # back from the aquarium
        self.assertEqual(s['journey']['fish']['rel'][1], 2)

    def test_buy_rods_and_equip(self):
        s = story(wallet=250_000)
        s, r = run(s, 'jr_fish_buy', Clock(), kind='rod', item='carbon')
        self.assertEqual((s['journey']['wallet'], s['journey']['fish']['rod']), (50_000, 'carbon'))
        with self.assertRaises(GameError):
            run(s, 'jr_fish_buy', Clock(), kind='rod', item='bien')   # not enough
        with self.assertRaises(GameError):
            run(s, 'jr_fish_buy', Clock(), kind='rod', item='carbon')   # owned
        s, r = run(s, 'jr_fish_equip', Clock(), rod='tre')
        self.assertEqual(s['journey']['fish']['rod'], 'tre')
        with self.assertRaises(GameError):
            run(s, 'jr_fish_equip', Clock(), rod='vang')


class Collection(unittest.TestCase):
    def test_milestones_pay_once_with_titles(self):
        s = story(wallet=1000)
        d = F.ensure(s)
        last = C.by_rarity(3)
        for sp in last[:-1]:
            d['dex'][sp['id']] = [1, 1000, 1]
        s = put_round(s, sp=last[-1]['id'], g=C.grams(last[-1]['w'][0]))
        s, _ = run(s, 'jr_fish_hook', Clock(T0 + 10.3), round='a' * 32)
        s, r = run(s, 'jr_fish_land', Clock(T0 + 30), round='a' * 32, ok=True)
        self.assertIn('r3', s['journey']['fish']['ms'])
        self.assertEqual(s['journey']['wallet'], 1000 + C.TIER_REWARD[3])
        self.assertIn('t_ca_hiem', s['journey']['spend']['own'])
        self.assertTrue(any('Danh hiệu mới' in x for x in r['effects']))
        validate_state(s)

    def test_style_items_are_earned_not_sold(self):
        from game.spend_content import FRAMES, TITLES
        ids = {t['id'] for t in TITLES} | {f['id'] for f in FRAMES}
        for t in C.STYLE_TITLES + C.STYLE_FRAMES:
            self.assertIn(t['id'], ids)
            self.assertEqual(t['price'], 0)
            self.assertTrue(t['earn'])
            self.assertLessEqual(len(t['id']), 24)


class Saves(unittest.TestCase):
    def test_leisure_keepsakes_move_into_the_book(self):
        s = story(wallet=1000)
        s['journey'].setdefault('leisure', {})
        s['journey']['leisure']['fish'] = dict(ca_ro=3, ca_chep=1, ca_tram=0)
        pub = F.public(s)
        self.assertTrue(pub['fresh'])
        self.assertEqual(pub['dex']['ca_ro'][0], 3)
        d = F.ensure(s)
        self.assertEqual((d['dex']['ca_ro'][0], d['dex']['ca_chep'][0]), (3, 1))
        self.assertNotIn('ca_tram', d['dex'])
        F._migrate(s['journey'], d)   # once
        self.assertEqual(d['dex']['ca_ro'][0], 3)
        F.legacy_catch(s, 'ca_ro')
        self.assertEqual(d['dex']['ca_ro'][0], 4)

    def test_a_newer_build_s_save_still_loads(self):
        s = story(wallet=1000)
        d = F.ensure(s)
        d['rods'] = ['tre', 'can_moi_2027']
        d['rod'] = 'can_moi_2027'
        d['bait'] = {'moi_moi': 5}
        d['use'] = 'moi_moi'
        d['gio'] = 9
        d['dex']['ca_moi_2027'] = [1, 500, 1]
        d['seq'] = 1
        d['bag'] = [dict(i=1, s='ca_moi_2027', g=500, d=1, p=0, k=0, o=0, od=0)]
        d['extra_key'] = {'later': True}
        validate_state(s)
        s, r = run(s, 'jr_fish_cast', Clock(), spot='ho', power=0.5)   # the bamboo rod's numbers, no crash
        pub = F.public(s)
        self.assertEqual(pub['bag'], [])   # an unknown species is not shown (kept in the save)
        self.assertEqual(len(s['journey']['fish']['bag']), 1)

    def test_tampered_saves_are_refused(self):
        for bad in (lambda d: d.__setitem__('seq', -1), lambda d: d['bag'].append(dict(i=99, s='ca_ro', g=1, d=1, p=0, k=0, o=0, od=0)),
                    lambda d: d.__setitem__('rods', ['carbon']), lambda d: d.__setitem__('carry', 5),
                    lambda d: d.__setitem__('aq', [['ca_ro', 1]] * 9)):
            s = story(wallet=1000)
            bad(F.ensure(s))
            with self.assertRaises(GameError):
                validate_state(s)

    def test_upgrade_drops_a_broken_round_only(self):
        s = story(wallet=1000)
        d = F.ensure(s)
        d['act'] = dict(id='zz')
        d['bag'] = [dict(i=1, s='ca_ro', g=100, d=1, p=0, k=0, o=0, od=0)]
        d['seq'] = 1
        F.upgrade(s['journey'])
        self.assertIsNone(d['act'])
        self.assertEqual(len(d['bag']), 1)
        validate_state(s)

    def test_public_and_wear(self):
        s = put_round(story(wallet=1000), sp='ca_chep')
        pub = F.public(s)
        self.assertNotIn('act', pub)
        self.assertNotIn('ca_chep', json.dumps(pub))
        self.assertIn('cond', pub)
        from game.engine import public_state
        j = public_state(copy.deepcopy(s))['journey']
        self.assertIn('fish', j)
        self.assertIsNone(j['fish']['wear'])


class Carry(unittest.TestCase):
    """live/fish_carry.py: the fish a walker shows is a known species of 🟣 Hiếm+, its weight in band, of a rarity this
    player has in their 📖 collection; the drawing comes from this build's catalogue."""

    class Db:
        def __init__(self, rows, fail=False):
            self.rows, self.fail, self.calls = rows, fail, 0

        async def fetch(self, sql, args):
            self.calls += 1
            if self.fail:
                raise RuntimeError('busy')
            return self.rows

    class Player:
        def __init__(self):
            self.sid, self.ext = 'a' * 64, {}

    def test_clean(self):
        from live import fish_carry
        x = next(s for s in C.SPECIES.values() if s['r'] == 4)
        lo, hi = x['w']
        got = fish_carry.clean(dict(sp=x['id'], kg=lo))
        self.assertEqual(got, dict(sp=x['id'], r=4, kg=round(lo, 2), fam=x['fam'], body=x['body'], belly=x['belly'], fin=x['fin'], pat=x['pat']))
        low = next(s for s in C.SPECIES.values() if s['r'] < C.CARRY_MIN)
        for bad in (None, 'x', dict(sp=x['id']), dict(sp=x['id'], kg=hi * 2), dict(sp=x['id'], kg=float('nan')), dict(sp='nope', kg=1),
                    dict(sp=low['id'], kg=low['w'][0]), dict(sp=x['id'], kg=lo, fam='hack'), dict(sp=x['id'], kg=True)):
            self.assertIsNone(fish_carry.clean(bad), bad)

    def test_keep_needs_the_rarity_caught(self):
        import asyncio
        from live import fish_carry
        x = next(s for s in C.SPECIES.values() if s['r'] == 4)
        fh = fish_carry.clean(dict(sp=x['id'], kg=x['w'][0]))
        run = asyncio.run
        db, p = self.Db([dict(rc=json.dumps([5, 2, 1, 1, 0, 0, 0])), dict(rc='bad')]), self.Player()
        self.assertIsNone(run(fish_carry.keep(db, p, fh)))          # rarest caught: 🟣 3 < 🟠 4
        db2, p2 = self.Db([dict(rc=json.dumps([1, 0, 0, 0, 2, 0, 0]))]), self.Player()
        self.assertEqual(run(fish_carry.keep(db2, p2, fh)), fh)
        run(fish_carry.keep(db2, p2, fh))
        self.assertEqual(db2.calls, 1)                               # cached on the player
        self.assertIsNone(run(fish_carry.keep(self.Db([], fail=True), self.Player(), fh)))   # a busy database: no fish, no error
        self.assertIsNone(run(fish_carry.keep(None, self.Player(), fh)))
        self.assertIsNone(run(fish_carry.keep(db2, p2, None)))


if __name__ == '__main__':
    unittest.main()
