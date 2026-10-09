"""🗡️ Phóng dao is a skill game (owner 09/10: "phóng dao, ô ăn quan thì chơi hệ kĩ năng", "giới hạn 1k/1 lần", "phóng
dao mà level cao thì tăng tốc lên nhé, mỗi level tăng 5% tốc độ"): the silent daily cap of 08/10 is gone (a clean
board always clears, the ladder pays in full, the legacy 'dpts' is left alone), stakes go up to 1,000 xu, the board of
level n turns faster with telegraphed turn-backs (the twist board: at least the owner's 1 + 5 % × (n − 1)) on the
server and in what the client draws, and a level started before (1.9.31 soft, 1.9.32 ramp) keeps its board."""
import json
import random
import shutil
import subprocess
import unittest
from pathlib import Path

from game import fair as fh
from game import fair_knife as kn
from game.engine import GameError, public_state, validate_state

from tests.test_fair import FairBase, story
from tests import test_fair_knife as tk


class NoCap(FairBase):
    start, board, clear, lose = tk.Knife.start, tk.Knife.board, tk.Knife.clear, tk.Knife.lose   # its helpers, not its tests

    def setUp(self):
        super().setUp()
        self.dice(random.Random(20261009))

    def perfect_run(self, s, stake, stop):
        """Start at `stake`, throw every level clean up to `stop`, take the prize: (s, paid)."""
        s, r = self.start(s, stake)
        for lv in range(1, stop + 1):
            s, r = self.clear(s)
            x = r['fair']
            self.assertFalse(x.get('lost'), f'level {lv}: a clean board always clears')
            if lv < stop:
                s, r = self.act(s, 'fair_kn_next')
        if r['fair'].get('all'):
            return s, r['fair']['paid']
        s, r = self.act(s, 'fair_kn_stop')
        return s, r['fair']['prize']

    def test_the_cap_and_its_helpers_are_gone(self):
        # 09/10 (exploit audit): a net-winnings cap came back, fair.KN_DAY_CAP a Vietnam day (tests/test_exploit_fixes.py)
        for name in ('KN_CAP_UNIT', 'kn_cap_left', '_kn_over'):
            self.assertFalse(hasattr(fh, name), name)

    def test_a_perfect_thumb_is_paid_the_ladder_all_day(self):
        s = story(10**6)
        rng = random.Random(9)
        net = 0
        for _ in range(40):
            stake, stop = rng.choice(kn.STAKES), rng.randint(1, 4)
            s, paid = self.perfect_run(s, stake, stop)
            run = s['journey']['fair_kn']['run']
            self.assertEqual(paid, kn.prize(stake, stop, run['bn']))
            net += paid - stake
            self.clock.t += 20
        self.assertGreater(net, 5 * 300)                                 # far past the old 300 xu a day
        self.assertEqual(s['journey']['fair']['dpts'], 0)                # the legacy counter is left alone
        validate_state(s)

    def test_the_top_stake_clears_every_level(self):
        s = story(5000)
        s, paid = self.perfect_run(s, 1000, kn.LEVELS)
        self.assertGreaterEqual(paid, kn.prize(1000, kn.LEVELS))
        self.assertEqual(s['journey']['wallet'], 5000 - 1000 + paid)
        validate_state(s)

    def test_heat_is_todays_net_only(self):
        s = story(5000)
        s, r = self.start(s, 1000)
        self.assertEqual(s['journey']['fair_kn']['run']['hot'], kn.heat(s['journey']['fair']['net']))

    def test_a_choice_left_overnight_is_paid_in_full(self):
        s = story(5000)
        s, _ = self.start(s, 100)
        for lv in range(1, 6):
            s, r = self.clear(s)
            if lv < 5:
                s, _ = self.act(s, 'fair_kn_next')
        shown = r['fair']['run']['prize']
        self.clock.t += 86400
        s, r = self.act(s, 'fair_kn_stop')
        self.assertEqual(r['fair']['prize'], shown)
        validate_state(s)


class Stakes(FairBase):
    def test_at_most_1000_xu_a_run(self):
        self.assertEqual(max(kn.STAKES), 1000)
        s = story(10**6)
        for bad in (1001, 2000, 5000, 10**6):
            with self.assertRaises(GameError):
                self.act(s, 'fair_kn_start', stake=bad)
        s, r = self.act(s, 'fair_kn_start', stake=1000)
        self.assertEqual(s['journey']['wallet'], 10**6 - 1000)

    def test_the_client_offers_the_same_stakes(self):
        k = public_state(story(10**6))['fair']['knife']
        self.assertEqual(max(k['stakes']), 1000)


class Speed(FairBase):
    start, board, clear = tk.Knife.start, tk.Knife.board, tk.Knife.clear

    def setUp(self):
        super().setUp()
        self.dice(random.Random(5))

    def test_five_percent_a_level(self):
        self.assertEqual([kn.speed_up(n) for n in (1, 2, 5, 10)], [1, 1.05, 1.2, 1.45])
        for lv in range(1, kn.LEVELS + 1):
            for hot in (0, 2):
                base = kn.schedule(77, lv, hot, kn.SOFT_DIFFICULTY)
                fast = kn.schedule(77, lv, hot, kn.SOFT_DIFFICULTY, True)
                self.assertEqual({k: v for k, v in base.items() if k != 'segs'}, {k: v for k, v in fast.items() if k != 'segs'})
                for a, b in zip(base['segs'], fast['segs']):
                    self.assertEqual((a[0], a[2]), (b[0], b[2]))
                    self.assertAlmostEqual(b[1], a[1] * (1 + .05 * (lv - 1)), places=9)
        self.assertEqual(kn.schedule(3, 1, 0, kn.SOFT_DIFFICULTY), kn.schedule(3, 1, 0, kn.SOFT_DIFFICULTY, True))

    def test_the_twist_board_keeps_the_owners_floor(self):
        """Owner 09/10: "mỗi level tăng 5% tốc độ" stays the floor: the board's cruising speed at level n is at least the
        soft board's × (1 + 5% × (n − 1)), and so is its average speed over a level."""
        for n in range(1, kn.LEVELS + 1):
            self.assertGreaterEqual(kn.twist_up(n), 1 + .05 * (n - 1))
            base = kn.DIFF[n][2] * kn.SOFT_DIFFICULTY / 100
            floor = base * (1 + .05 * (n - 1))
            means = []
            for seed in range(60):
                sc = kn.twist_schedule(seed, n, 0)
                self.assertGreaterEqual(abs(sc['segs'][0][1]), .95 * base * kn.twist_up(n) - .1)   # it starts cruising
                means.append(sum(abs(kn.speed_at(sc, t)) for t in range(0, kn.LEVEL_MS, 50)) * 1000 / (kn.LEVEL_MS / 50))
            self.assertGreaterEqual(sum(means) / len(means), floor, n)

    def test_turn_backs_are_telegraphed(self):
        """Every turn-back comes after a visible slow-down to a near stop and a rest, never as a jerk."""
        for n in range(1, kn.LEVELS + 1):
            for hot in (0, kn.HEAT_MAX):
                for seed in range(40):
                    sc = kn.twist_schedule(seed, n, hot)
                    v = kn.DIFF[sc['d']][2] * kn.SOFT_DIFFICULTY / 100 * kn.twist_up(n)
                    for stop, nxt in zip(sc['segs'], sc['segs'][1:]):
                        if stop[1] * nxt[1] < 0:   # it turns back here
                            self.assertLessEqual(abs(stop[1]), kn.TWIST_REST * v + .1)
                            self.assertGreaterEqual(stop[2], kn.TWIST_BRAKE[1][0])             # slowing down, visibly
                            self.assertGreaterEqual(stop[0] - stop[2], kn.TWIST_DWELL[1][0])   # then resting
                            self.assertGreaterEqual(nxt[2], kn.TWIST_ACCEL[0])                 # then speeding up
                    last = kn.speed_at(sc, 0)   # sampled: the speed changes sign only through a near stop
                    for t in range(10, 20000, 10):
                        w = kn.speed_at(sc, t)
                        if w * last < 0:
                            self.assertLess(max(abs(w), abs(last)) * 1000, .2 * v)
                        last = w

    def test_harder_each_level(self):
        def turns(n):
            out = 0
            for seed in range(200):
                segs = kn.twist_schedule(seed, n, 0)['segs']
                t = 0
                for a, b in zip(segs, segs[1:]):
                    t += a[0]
                    if t > 20000:
                        break
                    out += a[1] * b[1] < 0
            return out / 200
        counts = [turns(n) for n in (1, 4, 7, 10)]
        self.assertEqual(counts, sorted(counts))
        self.assertGreater(counts[-1], 1.8 * counts[0])
        self.assertEqual(kn.twist_schedule(9, 4, 1), kn.twist_schedule(9, 4, 1))   # all from the seed

    def test_new_levels_play_the_twist_board_and_the_client_draws_the_same(self):
        s = story(5000)
        s, r = self.start(s, 10)
        for lv in range(1, 5):
            j = s['journey']
            run = j['fair_kn']['run']
            self.assertEqual(j[fh.KN_TWIST_KEY], {'at': run['at'], 'seed': run['sd']})
            self.assertNotIn(fh.KN_RAMP_KEY, j)
            want = kn.twist_schedule(run['sd'], lv, run['hot'])
            self.assertEqual(fh._kn_sched(run, j)['segs'], want['segs'])
            board = public_state(s)['fair']['knife']['run']['board']
            self.assertEqual(board, json.loads(json.dumps(kn.public_schedule(want))))   # what the client turns by
            s, r = self.clear(s)
            self.assertTrue(r['fair']['cleared'])
            s['journey']['fair_kn']['run']['nx'] = 0
            s, r = self.act(s, 'fair_kn_next')

    def test_levels_started_on_older_boards_keep_them_and_settle(self):
        for mark, board in ((fh.KN_RAMP_KEY, lambda sd, hot: kn.schedule(sd, 2, hot, kn.SOFT_DIFFICULTY, True)),   # 1.9.32
                            (None, lambda sd, hot: kn.schedule(sd, 2, hot, kn.SOFT_DIFFICULTY))):              # 1.9.31
            with self.subTest(mark=mark):
                s = story(5000)
                s, r = self.start(s, 10)
                s, r = self.clear(s)
                s['journey']['fair_kn']['run']['nx'] = 0
                s, r = self.act(s, 'fair_kn_next')
                j = s['journey']
                run = j['fair_kn']['run']
                del j[fh.KN_TWIST_KEY]                                    # as the older build started it
                if mark:
                    j[mark] = {'at': run['at'], 'seed': run['sd']}
                old = board(run['sd'], run['hot'])
                self.assertEqual(fh._kn_sched(run, j)['segs'], old['segs'])
                validate_state(s)
                s, r = self.clear(s)                                      # thrown on the board it was shown
                self.assertTrue(r['fair']['cleared'])
                s, r = self.act(s, 'fair_kn_stop')
                self.assertEqual(r['fair']['prize'], kn.prize(10, 2))

    def test_the_marks_are_checked(self):
        s = story(5000)
        s, _ = self.start(s, 10)
        for key in (fh.KN_RAMP_KEY, fh.KN_TWIST_KEY):
            for bad in ({'at': 1}, {'at': 1, 'seed': -1}, {'at': 1, 'seed': 2, 'x': 3}, [1, 2], {'at': '1', 'seed': 2}):
                t = json.loads(json.dumps(s))
                t['journey'][key] = bad
                with self.assertRaises(GameError):
                    validate_state(t)


class ClientParity(unittest.TestCase):
    """public/js/v4/fair-knife.js turns the 1.9.32 ramp board and the twist board exactly as the server judges them
    (angleAt, judge)."""

    def test_the_client_draws_and_judges_the_boards_the_same(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('no node')
        rng = random.Random(3)
        cases = []
        boards = [kn.schedule(rng.getrandbits(31), lv, rng.randint(0, 1), kn.SOFT_DIFFICULTY, True) for lv in range(1, 11)]
        boards += [kn.twist_schedule(rng.getrandbits(31), lv, hot) for lv in range(1, 11) for hot in (0, 3)]
        for full in boards:
            sc = kn.public_schedule(full)
            ts = sorted(rng.uniform(0, kn.LEVEL_MS) for _ in range(60))
            for taps in (sorted({rng.randrange(0, 20000) for _ in range(12)}),       # mostly a knife on a knife
                         tk.safe_taps(dict(sc), sc['need'], start=rng.randint(200, 3000))):   # a clean level
                stuck, hit = kn.judge(dict(sc), taps)
                cases.append(dict(b=sc, ts=ts, want=[kn.angle_at(dict(sc), t) for t in ts], taps=taps, stuck=stuck, hit=hit))
            self.assertEqual(cases[-1]['hit'], -1)
        root = Path(__file__).resolve().parents[1]
        url = (root / 'public/js/v4/fair-knife.js').as_uri()
        prog = (f"import {{angleAt,judge}} from {json.dumps(url)};let d='';process.stdin.on('data',x=>d+=x);"
                "process.stdin.on('end',()=>{const K={fly:%d,impact:%r,gap:%r};const out=JSON.parse(d).map(c=>{"
                "const a=c.ts.map(t=>angleAt(c.b,t)),j=judge(c.b,K,c.taps);return {a,stuck:j.stuck.map(x=>Math.round(x*100)/100),hit:j.hit};});"
                "process.stdout.write(JSON.stringify(out));});") % (kn.FLY_MS, kn.IMPACT, kn.GAP)
        out = subprocess.run([node, '--input-type=module', '-e', prog], input=json.dumps(cases), capture_output=True,
                             text=True, encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        for c, got in zip(cases, json.loads(out.stdout)):
            for want, a in zip(c['want'], got['a']):
                self.assertAlmostEqual(want, a, places=6)
            self.assertEqual(got['hit'], c['hit'])
            self.assertEqual(len(got['stuck']), len(c['stuck']))
            for x, y in zip(got['stuck'], c['stuck']):
                self.assertAlmostEqual(x, y, places=1)


if __name__ == '__main__':
    unittest.main()
