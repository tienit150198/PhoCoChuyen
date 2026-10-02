"""🎯 Phóng phi tiêu at the fair (game/fair_darts.py, game/fair.py fair_dart): the odds by today's net, the stake
rules, the wallet as the only limit, the landing point, the points, the title and the save."""
import json
import math
import random
import unittest

from game import fair as fh
from game import fair_darts as darts
from game.engine import GameError, public_state, validate_state

from tests.test_fair import AFTER, FairBase, story


class Draws(random.Random):
    """A seeded random source whose random() (the win draw) comes from a list."""
    def __new__(cls, draws=(), seed=7):   # Python 3.12's Random.__new__ takes one argument at most
        return super().__new__(cls, seed)

    def __init__(self, draws=(), seed=7):
        super().__init__(seed)
        self.draws = list(draws)

    def random(self):
        return self.draws.pop(0) if self.draws else super().random()


class Odds(unittest.TestCase):
    def test_the_taper(self):
        self.assertEqual(darts.win_p(-5000), 0.70)
        self.assertEqual(darts.win_p(0), 0.70)
        self.assertEqual(darts.win_p(1999), 0.70)
        self.assertAlmostEqual(darts.win_p(3500), 0.575)
        self.assertEqual(darts.win_p(5000), 0.45)
        self.assertEqual(darts.win_p(10**6), 0.45)
        xs = [darts.win_p(n) for n in range(1500, 5600, 50)]
        self.assertEqual(xs, sorted(xs, reverse=True))

    def test_the_landing_matches_the_result(self):
        rng = random.Random(3)
        for i in range(4000):
            aim = [rng.randint(-120, 120), rng.randint(-120, 120)]
            win = rng.random() < .5
            x, y = darts.land(aim, win, rng)
            ring = darts.ring_of(x, y)
            self.assertEqual(ring <= 3, win, (aim, win, x, y))
            self.assertLessEqual(math.hypot(x, y), darts.OFF_R + .5)

    def test_aim(self):
        for ok in ([0, 0], [-120, 120]):
            self.assertTrue(darts.aim_ok(ok))
        for bad in ([0], [0, 0, 0], [0.5, 0], ['0', 0], [121, 0], None, (0, 0), [True, 0]):
            self.assertFalse(darts.aim_ok(bad), bad)


class Darts(FairBase):
    def throw(self, s, stake=10, draws=(), seed=7, **p):
        self.dice(Draws(draws, seed))
        return self.act(s, 'fair_dart', stake=stake, **p)

    def test_a_hit_pays_one_to_one_and_a_miss_loses_the_stake(self):
        s = story(100)
        s, r = self.throw(s, 10, [.1], aim=[0, 0])
        x = r['fair']
        self.assertEqual((x['win'], x['net'], x['stake']), (True, 10, 10))
        self.assertLessEqual(x['ring'], 3)
        self.assertEqual(s['journey']['wallet'], 110)
        s, r = self.throw(s, 20, [.99], aim=[0, 0])
        self.assertEqual((r['fair']['win'], r['fair']['net']), (False, -20))
        self.assertGreaterEqual(r['fair']['ring'], 4)
        self.assertEqual(s['journey']['wallet'], 90)
        f = s['journey']['fair']
        self.assertEqual((f['dt']['n'], f['dt']['w'], f['net']), (2, 1, -10))
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount']), ('fair', -10))   # one Sổ ví row for the day's darts
        self.assertTrue(row['label'].startswith(fh.LABELS['dt']))
        validate_state(s)

    def test_the_odds_follow_todays_net(self):
        s = story(100)
        s['journey']['fair'] = fh.initial()
        s['journey']['fair']['date'] = fh.vn_date(self.clock.t + 2)
        s['journey']['fair']['net'] = 3500           # odds 57.5 %: a draw of .6 misses, .57 hits
        s, r = self.throw(s, 5, [.6])
        self.assertFalse(r['fair']['win'])
        s, r = self.throw(s, 5, [.57])
        self.assertTrue(r['fair']['win'])
        s['journey']['fair']['net'] = 9000           # far ahead: 45 %
        s, r = self.throw(s, 5, [.46])
        self.assertFalse(r['fair']['win'])
        s['journey']['fair']['net'] = -400           # behind: 70 %
        s, r = self.throw(s, 5, [.69])
        self.assertTrue(r['fair']['win'])

    def test_win_rate_over_many_throws(self):
        s = story(10**6)
        self.dice(random.Random(11))
        wins = 0
        for _ in range(1500):
            s['journey']['fair'] = s['journey']['fair'] if 'fair' in s['journey'] else fh.initial()
            s['journey']['fair']['net'] = 0          # keep the generous odds
            s, r = self.act(s, 'fair_dart', stake=2)
            wins += r['fair']['win']
        self.assertTrue(0.64 < wins / 1500 < 0.76, wins)

    def test_stakes_and_bad_payloads(self):
        s = story(100)
        for p in (dict(stake=3), dict(stake='10'), dict(stake=100), dict(stake=10, aim=[0]), dict(stake=10, aim=[500, 0]),
                  dict(stake=10, extra=1), dict()):
            with self.assertRaises(GameError, msg=p):
                self.throw(s, draws=[.1], **p) if 'stake' in p else self.act(s, 'fair_dart', **p)

    def test_no_loans_and_never_below_zero(self):
        s = story(4)
        with self.assertRaises(GameError) as e:
            self.throw(s, 5, [.99])
        self.assertEqual(e.exception.code, 'fair_wallet')
        s, r = self.throw(s, 2, [.99])
        s, r = self.throw(s, 2, [.99])
        self.assertEqual(s['journey']['wallet'], 0)
        with self.assertRaises(GameError):
            self.throw(s, 2, [.99])

    def test_no_daily_money_or_round_limit(self):
        s = story(1000)
        s['journey']['fair'] = fh.initial()
        f = s['journey']['fair']
        f.update(date=fh.vn_date(self.clock.t + 2), net=-(fh.DAY_CAP + 300), rounds=fh.ROUNDS_DAY)
        s, r = self.throw(s, 50, [.99])
        self.assertEqual(r['fair']['net'], -50)
        self.assertEqual(s['journey']['fair']['rounds'], fh.ROUNDS_DAY)
        validate_state(s)

    def test_too_fast(self):
        s = story(100)
        s, _ = self.throw(s, 2, [.1])
        self.clock.t -= 2 - 0.3                      # 0.3 s after the last throw
        with self.assertRaises(GameError) as e:
            self.throw(s, 2, [.1])
        self.assertEqual(e.exception.code, 'fair_slow')

    def test_points_a_hit_and_no_daily_max(self):
        s = story(100)
        s['journey']['fair'] = fh.initial()
        f = s['journey']['fair']
        f.update(date=fh.vn_date(self.clock.t + 2), ed=fh.edition(), pday=fh.vn_date(self.clock.t + 2),
                 dpts=fh.POINTS_DAY, pts=40)
        s, r = self.throw(s, 2, [.1])
        self.assertEqual(r['fair']['points'], darts.PT_HIT)
        self.assertEqual((s['journey']['fair']['pts'], s['journey']['fair']['dpts']), (41, fh.POINTS_DAY))
        s, r = self.throw(s, 2, [.99])
        self.assertEqual(r['fair']['points'], 0)
        validate_state(s)

    def test_bullseye_title(self):
        s = story(100)
        for i in range(400):
            s, r = self.throw(s, 2, [.1], seed=i, aim=[0, 0])
            if r['fair']['ring'] == 0:
                break
        self.assertEqual(r['fair']['ring'], 0)
        self.assertIn('f_dart', s['journey']['titles'])
        self.assertEqual(s['journey']['fair']['dt']['b'], 1)

    def test_closed_after_the_fair(self):
        s = story(100)
        self.clock.t = AFTER
        with self.assertRaises(GameError) as e:
            self.throw(s, 2, [.1])
        self.assertEqual(e.exception.code, 'fair_closed')

    def test_public_and_saves(self):
        s = story(100)
        v = public_state(s)['fair']['darts']
        self.assertEqual((v['stakes'], v['n'], v['w']), (list(darts.STAKES), 0, 0))
        s, _ = self.throw(s, 2, [.1])
        v = public_state(s)['fair']['darts']
        self.assertEqual((v['n'], v['w']), (1, 1))
        for bad_dt in ({'n': 1}, dict(n=-1, w=0, b=0), dict(n='1', w=0, b=0), [1, 2, 3]):
            bad = json.loads(json.dumps(s))
            bad['journey']['fair']['dt'] = bad_dt
            with self.assertRaises(GameError, msg=bad_dt):
                validate_state(bad)
        old = json.loads(json.dumps(s))              # a save from before the darts
        old['journey']['fair'].pop('dt')
        validate_state(old)


if __name__ == '__main__':
    unittest.main()
