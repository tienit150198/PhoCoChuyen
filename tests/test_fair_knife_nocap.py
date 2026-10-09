"""🗡️ Phóng dao is a skill game (owner 09/10: "phóng dao, ô ăn quan thì chơi hệ kĩ năng", "giới hạn 1k/1 lần", "phóng
dao mà level cao thì tăng tốc lên nhé, mỗi level tăng 5% tốc độ"): the silent daily cap of 08/10 is gone (a clean
board always clears, the ladder pays in full, the legacy 'dpts' is left alone), stakes go up to 1,000 xu, the board of
level n turns 1 + 5 % × (n − 1) faster on the server and in what the client draws, and a level started before keeps
its board (in-progress runs settle both ways)."""
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
        for name in ('KN_DAY_CAP', 'KN_CAP_UNIT', 'kn_cap_left', '_kn_over'):
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

    def test_new_levels_turn_faster_and_the_client_draws_the_same(self):
        s = story(5000)
        s, r = self.start(s, 10)
        for lv in range(1, 5):
            j = s['journey']
            run = j['fair_kn']['run']
            self.assertEqual(j[fh.KN_RAMP_KEY], {'at': run['at'], 'seed': run['sd']})
            sc = fh._kn_sched(run, j)
            want = kn.schedule(run['sd'], lv, run['hot'], kn.SOFT_DIFFICULTY, True)
            self.assertEqual(sc['segs'], want['segs'])
            board = public_state(s)['fair']['knife']['run']['board']
            self.assertEqual(board['segs'], json.loads(json.dumps(want['segs'])))   # the numbers the client turns by
            s, r = self.clear(s)
            self.assertTrue(r['fair']['cleared'])
            s['journey']['fair_kn']['run']['nx'] = 0
            s, r = self.act(s, 'fair_kn_next')

    def test_a_level_started_before_keeps_its_board_and_settles(self):
        s = story(5000)
        s, r = self.start(s, 10)
        s, r = self.clear(s)
        s['journey']['fair_kn']['run']['nx'] = 0
        s, r = self.act(s, 'fair_kn_next')                                # level 2: × 1.05 on this build
        j = s['journey']
        del j[fh.KN_RAMP_KEY]                                             # as an older build started it
        run = j['fair_kn']['run']
        old = kn.schedule(run['sd'], 2, run['hot'], kn.SOFT_DIFFICULTY)
        self.assertEqual(fh._kn_sched(run, j)['segs'], old['segs'])
        validate_state(s)
        s, r = self.clear(s)                                              # thrown on the board it was shown
        self.assertTrue(r['fair']['cleared'])
        s, r = self.act(s, 'fair_kn_stop')
        self.assertEqual(r['fair']['prize'], kn.prize(10, 2))

    def test_the_ramp_mark_is_checked(self):
        s = story(5000)
        s, _ = self.start(s, 10)
        for bad in ({'at': 1}, {'at': 1, 'seed': -1}, {'at': 1, 'seed': 2, 'x': 3}, [1, 2], {'at': '1', 'seed': 2}):
            t = json.loads(json.dumps(s))
            t['journey'][fh.KN_RAMP_KEY] = bad
            with self.assertRaises(GameError):
                validate_state(t)


class ClientParity(unittest.TestCase):
    """public/js/v4/fair-knife.js turns a ramped board exactly as the server judges it (angleAt, judge)."""

    def test_the_client_draws_and_judges_the_ramped_board_the_same(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('no node')
        rng = random.Random(3)
        cases = []
        for lv in range(1, kn.LEVELS + 1):
            sc = kn.public_schedule(kn.schedule(rng.getrandbits(31), lv, rng.randint(0, 1), kn.SOFT_DIFFICULTY, True))
            ts = sorted(rng.uniform(0, kn.LEVEL_MS) for _ in range(40))
            taps = sorted({rng.randrange(0, 20000) for _ in range(12)})
            stuck, hit = kn.judge(dict(sc), taps)
            cases.append(dict(b=sc, ts=ts, want=[kn.angle_at(dict(sc), t) for t in ts], taps=taps, stuck=stuck, hit=hit))
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
