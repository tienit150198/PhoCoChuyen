"""🐕 Đua chó at the Chợ đen (game/fair_dog.py, game/fair.py fair_dg; owner 09/10: "trò đua chó", a betting stall where
the player only watches and cheers): the lineups, a race won and lost (wallet, Sổ ví row, today's net, the Bảng
vàng), an outsider's big payout in valid rows, every bad input refused with nothing changed, the bảo kê gate, the
police and the trại tạm giữ, no chance on the client, a retried request paid once, the house edge, and saves after a
race (won, lost, caught) that the releases this one may be rolled back to (1.9.31, 1.9.30) still validate."""
import io
import json
import os
import random
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import fair as fh
from game import fair_bm as bm
from game import fair_dog as dg
from game import jail as jl
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_black_market import OPEN, BlackMarketBase, story
from tests.test_fair import StoreBase

ROOT = Path(__file__).resolve().parents[1]
OLD = (('e4ea7eba', '1.9.31'), ('65dafa3b', '1.9.30'))   # the releases this one may be rolled back to


class DogBase(BlackMarketBase):
    def setUp(self):
        super().setUp()
        self.caught(False)   # the police's other checks wait out the session's quiet start (fair.GRACE_ROUNDS)

    def caught(self, on=True):
        p = mock.patch.object(bm, '_arrest_roll', lambda *a: on)
        p.start()
        self.addCleanup(p.stop)

    def inside(self, wallet=50000):
        s = story(wallet)
        p = mock.patch.object(bm, 'asked', lambda j, t: False)   # the đàn em do not ask: straight in
        p.start()
        self.addCleanup(p.stop)
        return s

    def race(self):
        return dg.race(self.clock.t + 6)   # the clock steps 6 s a call

    def lane_of(self, cls, n=None):
        lanes = dg.lineup(self.race() if n is None else n)
        return next(i for i, (_, k) in enumerate(lanes) if k == cls)

    def bet(self, s, lane, stake, first=None, **extra):
        """A race on `lane`; first: the lane that wins (None: the real draw)."""
        p = dict(race=self.race(), lane=lane, stake=stake, **extra)
        if first is None:
            return self.act(s, 'fair_dg', **p)
        order = [first] + [i for i in range(dg.LANES) if i != first]
        with mock.patch.object(dg, 'draw', lambda lanes, rng: list(order)):
            return self.act(s, 'fair_dg', **p)


class Lineups(unittest.TestCase):
    def test_a_race_is_the_same_everywhere_and_holds_every_class(self):
        for n in (0, 1, 14930310, 10**7 + 3):
            lanes = dg.lineup(n)
            self.assertEqual(lanes, dg.lineup(n))
            self.assertEqual(sorted(k for _, k in lanes), list(range(dg.LANES)))
            self.assertEqual(len({d for d, _ in lanes}), dg.LANES)
            self.assertTrue(all(0 <= d < len(dg.RACERS) for d, _ in lanes))
        self.assertNotEqual([dg.lineup(n) for n in range(5)], [dg.lineup(0)] * 5)

    def test_every_racer_is_a_pet_breed(self):
        from game import pets_content as pc
        for name, breed, coat in dg.RACERS:
            self.assertEqual(pc.BREEDS[breed]['kind'], 'dog', name)
            self.assertLess(coat, len(pc.BREEDS[breed]['coats']))

    def test_the_draw_follows_the_weights(self):
        rng = random.Random(3)
        lanes = dg.lineup(77)
        wins = [0] * dg.LANES
        for _ in range(60000):
            order = dg.draw(lanes, rng)
            self.assertEqual(sorted(order), list(range(dg.LANES)))
            wins[lanes[order[0]][1]] += 1
        for k, (w, _) in enumerate(dg.CLASSES):
            self.assertAlmostEqual(wins[k] / 60000, w / 1000, delta=.008)


class Race(DogBase):
    def test_a_won_race_pays_the_price_on_the_board(self):
        s = self.inside()
        lane = self.lane_of(2)   # ×5.2
        s, r = self.bet(s, lane, 1000, first=lane)
        x = r['fair']
        self.assertEqual((x['game'], x['won'], x['lane'], x['stake'], x['mult'], x['back'], x['net']),
                         ('dg', True, lane, 1000, 52, 5200, 4200))
        self.assertEqual(x['order'][0], lane)
        self.assertEqual(s['journey']['wallet'], 50000 + 4200)
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['kind'], row['label']), (4200, 'fair', '🐕 Đua chó chợ đen · 1 lượt'))
        f = s['journey']['fair']
        self.assertEqual((f['net'], f['stats']['won'], f['rounds']), (4200, 4200, 1))
        self.assertEqual(fh.money_of(s['journey'])[0], 4200)   # the Bảng vàng
        self.assertEqual(fh.public(s)['today_xu']['dg'], 4200)
        self.assertIn('về nhất', r['message'])
        self.assertIn('4.200', r['message'])
        validate_state(s)

    def test_a_lost_race_takes_the_stake_on_the_same_row(self):
        s = self.inside()
        lane = self.lane_of(0)
        s, _ = self.bet(s, lane, 300, first=lane)                  # +570
        s, r = self.bet(s, lane, 500, first=(lane + 1) % dg.LANES)  # −500
        self.assertFalse(r['fair']['won'])
        self.assertEqual((r['fair']['back'], r['fair']['net']), (0, -500))
        self.assertEqual(s['journey']['wallet'], 50000 + 570 - 500)
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['label']), (70, '🐕 Đua chó chợ đen · 2 lượt'))
        f = s['journey']['fair']
        self.assertEqual((f['net'], f['stats']['won'], f['stats']['lost']), (70, 570, 500))
        self.assertIn('Thua 500 xu', r['message'])
        validate_state(s)

    def test_the_payout_rounds_down(self):
        s = self.inside()
        lane = self.lane_of(0)   # ×2.9
        s, r = self.bet(s, lane, 15, first=lane)
        self.assertEqual(r['fair']['back'], 43)   # 43.5
        self.assertEqual(s['journey']['wallet'], 50000 + 28)

    def test_an_outsider_on_the_biggest_stake_is_paid_in_valid_rows(self):
        s = self.inside(fh.STAKE_MAX + 5)
        lane = self.lane_of(dg.LANES - 1)   # ×19
        s, r = self.bet(s, lane, fh.STAKE_MAX, first=lane)
        self.assertEqual(r['fair']['net'], 18 * fh.STAKE_MAX)
        self.assertEqual(s['journey']['wallet'], 19 * fh.STAKE_MAX + 5)
        rows = [x for x in s['journey']['history'] if x['label'].startswith(dg.RACE_LABEL)]
        self.assertEqual(sum(x['amount'] for x in rows), 18 * fh.STAKE_MAX)
        self.assertTrue(all(abs(x['amount']) <= bm.ROW_MAX for x in rows), rows)
        self.assertTrue(all(x['label'].endswith('· 1 lượt') for x in rows), rows)   # one race, counted once
        validate_state(s)

    def test_the_real_draw_and_the_cheer_change_nothing_on_the_server(self):
        s = self.inside(10**6)
        with mock.patch.object(fh, '_rng', random.Random(11)):
            for i in range(60):
                s, r = self.bet(s, i % dg.LANES, 100)
                self.assertEqual(sorted(r['fair']['order']), list(range(dg.LANES)))
        validate_state(s)
        self.refused(s, 'fair_dg', 'invalid_action', race=self.race(), lane=0, stake=100, cheer=5)

    def test_bad_input_is_refused_and_changes_nothing(self):
        s = self.inside(5000)
        before = json.dumps(s, sort_keys=True)
        n = self.race()
        bad = [dict(race=n, lane=6, stake=100), dict(race=n, lane=-1, stake=100), dict(race=n, lane='1', stake=100),
               dict(race=n, lane=True, stake=100), dict(race=n, lane=0), dict(lane=0, stake=100),
               dict(race=str(n), lane=0, stake=100), dict(race=n, lane=0, stake=0), dict(race=n, lane=0, stake=-50),
               dict(race=n, lane=0, stake=9), dict(race=n, lane=0, stake='100'), dict(race=n, lane=0, stake=100.0),
               dict(race=n, lane=0, stake=True)]
        for p in bad:
            with self.subTest(p=p), self.assertRaises(GameError):
                fh.action(json.loads(before), 'fair_dg', p)
        for p, code in ((dict(race=n, lane=0, stake=5001), 'fair_wallet'),
                        (dict(race=n, lane=0, stake=fh.STAKE_MAX + 1), 'fair_big'),
                        (dict(race=n - 3, lane=0, stake=100), 'fair_dg_race'),
                        (dict(race=n + 3, lane=0, stake=100), 'fair_dg_race')):
            with self.subTest(code=code):
                self.refused(json.loads(before), 'fair_dg', code, **p)
        self.assertEqual(json.dumps(s, sort_keys=True), before)

    def test_the_race_before_and_after_are_taken(self):
        s = self.inside()
        for d in (-1, 0, 1):
            with self.subTest(d=d):
                n = self.race() + d
                lanes = dg.lineup(n)
                lane = next(i for i, (_, k) in enumerate(lanes) if k == 1)
                with mock.patch.object(dg, 'draw', lambda ls, rng: [lane] + [i for i in range(dg.LANES) if i != lane]):
                    s, r = self.act(s, 'fair_dg', race=n, lane=lane, stake=100)
                self.assertEqual((r['fair']['race'], r['fair']['mult']), (n, 39))

    def test_never_cools_and_saves_nothing_of_its_own(self):
        s = self.inside(10**6)
        with mock.patch.object(fh, '_rng', random.Random(5)):
            for i in range(40):
                s, _ = self.bet(s, 0, 100)
        j = s['journey']
        self.assertNotIn('dg', j.get('fair_cool', {}))
        self.assertNotIn('dg', j.get('fair_balance', {}))
        self.assertNotIn('fair_run', j)
        self.assertNotIn('dg', j['fair']['stats'])
        self.assertIsNone(fh.cold(j, self.clock.t))

    def test_it_counts_as_a_switch_for_a_cooled_stall(self):
        s = self.inside(10**6)
        with mock.patch.object(fh, '_rng', random.Random(5)):
            for _ in range(fh.RUN_FREE + 2):
                s, _ = self.act(s, 'fair_xs', price=100)
            self.assertEqual(fh.cold(s['journey'], self.clock.t)['game'], 'xs')
            for _ in range(fh.SWITCH_ROUNDS):
                s, _ = self.bet(s, 0, 100)
        self.assertIsNone(fh.cold(s['journey'], self.clock.t))


class Gate(DogBase):
    def test_nothing_before_the_bao_ke(self):
        s = story()
        self.refused(s, 'fair_dg', 'fair_bm_gate', race=self.race(), lane=0, stake=100)
        s, _ = self.act(s, 'fair_bm_pay')
        s, r = self.bet(s, 0, 100)
        self.assertEqual(r['fair']['game'], 'dg')


class Police(DogBase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        p = mock.patch.object(jl, 'now', lambda: self.clock.t)
        p.start()
        self.addCleanup(p.stop)

    def test_an_arrest_takes_the_stake_fines_and_jails(self):
        s = self.inside(100000)
        s, _ = self.bet(s, 0, 100, first=1)
        self.rich(s)
        self.caught(True)
        s, r = self.bet(s, 0, 2000)
        a = r['fair']['arrest']
        fine = (100000 - 100 - 2000) * 30 // 100
        self.assertEqual((r['fair']['game'], a['stake'], a['fine'], a['jail']), ('dg', 2000, fine, bm.JAIL_DAYS))
        self.assertNotIn('order', r['fair'])   # no race
        h = s['journey']['history']
        self.assertEqual((h[-1]['amount'], h[-1]['label']), (-fine, bm.FINE_LABEL))
        self.assertEqual((h[-2]['amount'], h[-2]['label']), (-2100, '🐕 Đua chó chợ đen · 2 lượt'))
        self.assertEqual(s['journey']['jail']['why'], 'bm')
        self.assertIn('f_raid', s['journey']['titles'])
        validate_state(s)
        with self.assertRaises(GameError) as e:   # from the cell: no race (the engine's gate)
            apply_action(s, None, 'fair_dg', dict(race=self.race(), lane=0, stake=100))
        self.assertEqual(e.exception.code, 'jailed')

    def test_not_rich_not_raided(self):
        s = self.inside(100000)
        self.caught(True)
        s, r = self.bet(s, 0, 100)
        self.assertIn('order', r['fair'])
        self.assertNotIn('jail', s['journey'])

    def test_the_wealth_check_runs_after_a_race(self):
        s = self.inside(500000)
        s, _ = self.bet(s, 0, 100, first=1)
        self.rich(s, bm.ARREST_FROM)   # the arrest roll stays off; above the wealth check's threshold
        with mock.patch.object(fh, 'WEALTH_RAID_P', 1.0), mock.patch.object(fh, 'GRACE_S', 0),                 mock.patch.object(fh, 'GRACE_ROUNDS', 0):
            s, r = self.bet(s, 0, 100, first=1)
        self.assertIn('wealth_raid', r['fair'])


class NothingShown(DogBase):
    def test_the_board_shows_prices_only(self):
        s = self.inside()
        f = fh.public(s)
        d = f['dog']
        self.assertEqual(set(d), {'min', 'max', 'slot', 'dogs', 'races'})
        for n, lanes in d['races']:
            self.assertEqual(len(lanes), dg.LANES)
            self.assertEqual(sorted(m for _, m in lanes), sorted(m for _, m in dg.CLASSES))
            self.assertEqual(lanes, [[di, dg.pay(k)] for di, k in dg.lineup(n)])
        self.assertEqual(set(d['dogs'][0]), {'name', 'breed', 'shape', 'size', 'b', 'm', 'l', 'e'})
        blob = json.dumps(dict(d, slot=None), ensure_ascii=False)   # (the seconds a lineup lasts: a clock, not a chance)
        for w, _ in dg.CLASSES:   # no weight (the chances) anywhere in the stall's block
            self.assertNotRegex(blob, rf'(?<![\d.#a-f]){w}(?![\d])', w)
        for k in ('weight', 'chance', 'odds', 'prob', 'phong_do', 'pct'):
            self.assertNotIn(k, json.dumps(d))
        self.assertFalse({k for k in f['rules'] if 'dg' in k or 'dog' in k})

    def test_the_receipt_has_no_chance(self):
        s = self.inside()
        s, r = self.bet(s, 0, 100)
        self.assertEqual(set(r['fair']), {'game', 'race', 'lane', 'stake', 'order', 'won', 'mult', 'back', 'net', 'photo',
                                          'seed'})
        self.assertNotIn('%', r['message'])


class HouseEdge(unittest.TestCase):
    def test_no_dog_returns_its_stake(self):
        for w, m in dg.CLASSES:
            self.assertLessEqual(w * m, 9500)
        self.assertEqual(sum(w for w, _ in dg.CLASSES), 1000)
        rows = [(w / 1000, m / 10) for w, m in dg.CLASSES]
        best = max(p * b for p, b in rows)
        self.assertAlmostEqual(best, .95)
        with_loc = max(p * (b + fh.LOC_P * max(0, fh.LOC_MULT - (b - 1))) for p, b in rows)
        self.assertLess(with_loc, .951)


class Idempotent(StoreBase):
    def test_a_retried_race_is_paid_once(self):
        tok = self.player('Lan', wallet=5000)
        rev = self.store.read(tok)[1]
        self.dice(random.Random(9))
        p = dict(race=dg.race(fh.now() + 2), lane=0, stake=100)
        a = self.store.command(tok, 'fair-dg-0001', rev, None, 'fair_dg', p)
        b = self.store.command(tok, 'fair-dg-0001', rev, None, 'fair_dg', p)
        self.assertTrue(b['replayed'])
        self.assertEqual(a['result'], b['result'])
        self.assertEqual(self.store.read(tok)[0]['journey']['wallet'], 5000 + a['result']['fair']['net'])
        with self.assertRaises(GameError):   # the same id, another race
            self.store.command(tok, 'fair-dg-0001', rev, None, 'fair_dg', dict(p, lane=1))


class OldServer(DogBase):
    """A save written after a race (won, lost, caught by the police) validates and loads on 1.9.31 and 1.9.30."""

    def old_tree(self, rev):
        tmp = tempfile.mkdtemp(prefix=f'mnl-{rev}-')
        self.addCleanup(__import__('shutil').rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', rev, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {rev}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def saves(self):
        env = mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        p = mock.patch.object(jl, 'now', lambda: self.clock.t)
        p.start()
        self.addCleanup(p.stop)
        s = self.inside(3 * fh.STAKE_MAX)
        lane = self.lane_of(dg.LANES - 1)
        s, _ = self.bet(s, lane, fh.STAKE_MAX, first=lane)            # won: an outsider on the biggest stake
        won = json.loads(json.dumps(s))
        s, _ = self.bet(s, 0, 777, first=1)                            # lost
        lost = json.loads(json.dumps(s))
        self.caught(True)
        s, r = self.bet(s, 0, 500)
        self.assertIn('arrest', r['fair'])
        caught = json.loads(json.dumps(s))
        self.assertIn('jail', caught['journey'])
        return [won, lost, caught]

    def test_saves_after_a_race_validate_on_older_releases(self):
        saves = self.saves()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state;'
                'out=[]\nfor s in json.load(sys.stdin):\n validate_state(s);s=migrate_state(s);validate_state(s);'
                'public_state(s);out.append(s["journey"]["wallet"])\nprint(json.dumps(out))')
        for rev, name in OLD:
            with self.subTest(release=name):
                old = self.old_tree(rev)
                env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
                out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(saves), capture_output=True, text=True,
                                     cwd=old, env=env, encoding='utf-8', timeout=300)
                self.assertEqual(out.returncode, 0, out.stderr[-3000:])
                self.assertEqual(json.loads(out.stdout), [x['journey']['wallet'] for x in saves])


if __name__ == '__main__':
    unittest.main()
