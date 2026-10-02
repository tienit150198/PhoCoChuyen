"""🗡️ Phóng dao at the fair (game/fair_knife.py, game/fair.py fair_kn_*), in the 🎯 phi tiêu's place: the ladder and
its return, the board drawn from a seed, the throws judged on the server, Dừng / Chơi tiếp / thua hết, the 🔥 x2
levels, a level left too long, a choice left until the next day, the wallet as the only limit, today's heat, the
Sổ ví row and the Bảng vàng, the public view and the saves both ways (an older server, an older client's phi tiêu)."""
import copy
import json
import random
import sys
import unittest
from pathlib import Path

from game import fair as fh
from game import fair_knife as kn
from game.engine import GameError, public_state, validate_state

from tests.test_fair import AFTER, Dice, FairBase, story

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


def safe_taps(sc, n, start=300, taps=()):
    """n more throws (after `taps`) that stick: the first moments whose landing is clear of every knife."""
    taps = list(taps)
    t = max(start, taps[-1] + kn.MIN_TAP) if taps else start
    while len(taps) < n:
        stuck, hit = kn.judge(sc, taps)
        assert hit < 0
        a = kn.lands(sc, t)
        if all(kn.dist(a, b) >= kn.GAP + 1 for b in sc['pre'] + stuck):
            taps.append(t)
            t += kn.MIN_TAP
        else:
            t += 5
        assert t < kn.LEVEL_MS
    return taps


def crash_tap(sc, taps):
    """A throw after `taps` that lands on a knife already stuck."""
    stuck, _ = kn.judge(sc, taps)
    t = taps[-1] + kn.MIN_TAP if taps else 0
    while True:
        a = kn.lands(sc, t)
        if any(kn.dist(a, b) < kn.GAP / 2 for b in sc['pre'] + stuck):
            return t
        t += 5


class Ladder(unittest.TestCase):
    def test_the_ladder(self):
        self.assertEqual(len(kn.LADDER), kn.LEVELS)
        self.assertEqual(list(kn.LADDER), sorted(set(kn.LADDER)))
        steps = [b - a for a, b in zip(kn.LADDER, kn.LADDER[1:])]
        self.assertEqual(steps[2:], sorted(steps[2:]))                      # the steps grow (the board gets harder)
        self.assertEqual([kn.prize(20, k) for k in range(0, 11)], [0, 22, 24, 32, 42, 56, 78, 108, 160, 240, 380])
        self.assertEqual((kn.prize(2, 1), kn.prize(5, 1), kn.prize(10, 1)), (2, 6, 11))   # rounded half up
        self.assertEqual(kn.x2_bonus(10, 4), kn.prize(10, 4) - kn.prize(10, 3))
        self.assertEqual(kn.prize(10, 4, 7), kn.prize(10, 4) + 7)

    def test_heat(self):
        self.assertEqual([kn.heat(n) for n in (-500, 0, 2000, 2001, 3000, 3001, 4000, 4001, 10**6)], [0, 0, 0, 1, 1, 2, 2, 3, 3])
        self.assertEqual(max(kn.DIFF), kn.LEVELS + kn.HEAT_MAX)

    def test_the_return_per_xu_with_the_documented_clear_rates(self):
        import sim_fair_knife as sim                                        # the docstring's table (scripts/)
        avg = [.85, .82, .78, .77, .73, .71, .69, .66, .63, .60]
        for k in (1, 3, 5, 8):
            self.assertTrue(.83 <= sim.returns(avg, 8000, lambda c, x, r, k=k: c >= k) <= 1.0, k)
        sensible = sim.returns(avg, 8000, lambda c, x, r: c >= r.randint(2, 5) and not x)
        self.assertTrue(.88 <= sensible <= 1.0, sensible)


class Board(unittest.TestCase):
    def test_a_level_from_its_seed(self):
        a, b = kn.schedule(77, 3), kn.schedule(77, 3)
        self.assertEqual(kn.public_schedule(a), kn.public_schedule(b))
        self.assertNotEqual(kn.public_schedule(a), kn.public_schedule(kn.schedule(78, 3)))
        self.assertNotEqual(kn.public_schedule(a)['segs'], kn.public_schedule(kn.schedule(77, 3, 1))['segs'])
        for seed in range(60):
            for lv in range(1, kn.LEVELS + 1):
                for hot in (0, kn.HEAT_MAX):
                    sc = kn.schedule(seed, lv, hot)
                    need, n_pre, *_ = kn.DIFF[lv + hot]
                    self.assertEqual((sc['need'], len(sc['pre']), sc['d']), (need, n_pre, lv + hot))
                    self.assertGreaterEqual(sum(x[0] for x in sc['segs']), kn.LEVEL_MS + kn.SLACK)
                    for i, x in enumerate(sc['pre']):
                        self.assertTrue(all(kn.dist(x, y) >= kn.PRE_SEP for y in sc['pre'][i + 1:]))
                    json.dumps(kn.public_schedule(sc))

    def test_the_turning_is_smooth_and_gets_livelier(self):
        for seed in range(30):
            sc = kn.schedule(seed, 9)
            t = 0
            for ms, _, _ in sc['segs'][:-1]:
                t += ms
                self.assertLess(abs(kn.angle_at(sc, t - .001) - kn.angle_at(sc, t)), .01)   # no jumps between stretches
        def turns(lv):
            n = 0
            for seed in range(80):
                w = [x[1] for x in kn.schedule(seed, lv)['segs']]
                n += sum(a * b < 0 for a, b in zip(w, w[1:]))
            return n
        self.assertEqual(turns(1), 0)                                       # level 1: one way, one speed
        self.assertLess(turns(3), turns(6))
        self.assertLess(turns(6), turns(10))
        self.assertEqual(kn.speed_at(kn.schedule(5, 1), 1000) * 1000, kn.schedule(5, 1)['segs'][0][1])

    def test_judging_the_throws(self):
        sc = kn.schedule(11, 1)
        v = abs(sc['segs'][0][1]) / 1000                                     # steady: degrees a ms
        taps = safe_taps(sc, 3)
        stuck, hit = kn.judge(sc, taps)
        self.assertEqual((len(stuck), hit), (3, -1))
        round_trip = round(360 / v)                                          # a full turn later: the same spot
        stuck, hit = kn.judge(sc, taps + [taps[-1] + round_trip])
        self.assertEqual(hit, 3)
        stuck, hit = kn.judge(sc, safe_taps(sc, sc['need']) + [10**5])      # throws past the level's need do not count
        self.assertEqual((len(stuck), hit), (sc['need'], -1))
        pre = kn.schedule(3, 6)                                              # a knife already in the board
        t = 0
        while kn.dist(kn.lands(pre, t), pre['pre'][0]) > 2:
            t += 1
        self.assertEqual(kn.judge(pre, [t])[1], 0)

    def test_throw_times(self):
        ok = [0, 120, 400, 5000]
        self.assertTrue(kn.taps_ok(ok, 7, 2000))                             # the network: SLACK ms ahead of the server
        self.assertTrue(kn.taps_ok([kn.LEVEL_MS], 7, kn.LEVEL_MS))
        for bad, need, el in (([], 7, 9000), (ok, 3, 9000), ([0, 119], 7, 9000), ([200, 100], 7, 9000), ([-1], 7, 9000),
                              ([0, 1.5e3], 7, 9000), ([True], 7, 9000), (['10'], 7, 9000), ((0, 200), 7, 9000),
                              ([7000], 7, 2000), ([kn.LEVEL_MS + 1], 7, 10**6), (None, 7, 9000), (list(range(0, 1200, 150)), 7, 9000)):
            self.assertFalse(kn.taps_ok(bad, need, el), bad)


class Knife(FairBase):
    def start(self, s, stake=10):
        return self.act(s, 'fair_kn_start', stake=stake)

    def board(self, s):
        run = s['journey']['fair_kn']['run']
        return kn.schedule(run['sd'], run['lv'], run['hot'])

    def clear(self, s):
        """Throw the level clean (the clock moved on enough for every throw)."""
        sc = self.board(s)
        taps = safe_taps(sc, sc['need'])
        self.clock.t += taps[-1] / 1000
        return self.act(s, 'fair_kn_throw', lv=s['journey']['fair_kn']['run']['lv'], taps=taps)

    def lose(self, s):
        sc = self.board(s)
        taps = safe_taps(sc, 2)
        taps.append(crash_tap(sc, taps))
        self.clock.t += taps[-1] / 1000
        return self.act(s, 'fair_kn_throw', lv=s['journey']['fair_kn']['run']['lv'], taps=taps)

    def test_stake_clear_and_stop(self):
        s = story(100)
        s, r = self.start(s, 10)
        run = r['fair']['run']
        self.assertEqual((run['lv'], run['stage'], run['prize'], run['win']), (1, 'play', 0, kn.prize(10, 1)))
        self.assertEqual(run['board']['need'], kn.DIFF[1][0])
        self.assertEqual(s['journey']['wallet'], 90)
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount'], row['label']), ('fair', -10, f'{fh.LABELS["kn"]} · 1 lượt'))
        s, r = self.clear(s)
        x = r['fair']
        self.assertEqual((x['cleared'], x['hit'], len(x['stuck'])), (True, -1, kn.DIFF[1][0]))
        self.assertEqual((x['run']['stage'], x['run']['prize'], x['run']['win']), ('choice', 11, kn.prize(10, 2)))
        self.assertEqual(s['journey']['wallet'], 90)                         # paid only on Dừng
        s, r = self.act(s, 'fair_kn_stop')
        self.assertEqual((r['fair']['prize'], r['fair']['run']['stage'], r['fair']['run']['paid']), (11, 'done', 11))
        self.assertEqual(s['journey']['wallet'], 101)
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['label']), (1, f'{fh.LABELS["kn"]} · 1 lượt'))   # one row, one run
        self.assertEqual(fh.today_xu(s['journey'])['kn'], 1)
        self.assertEqual(fh.money_of(s['journey'])[0], 1)                   # the Bảng vàng: xu won
        k = s['journey']['fair_kn']
        self.assertEqual((k['n'], k['w'], k['b'], k['top']), (1, 1, 1, 11))
        s, r = self.act(s, 'fair_kn_stop')                                   # again: nothing more
        self.assertEqual((r['fair']['again'], s['journey']['wallet']), (True, 101))
        s, r = self.start(s, 5)                                              # a new run, the same Sổ ví row
        self.assertEqual(s['journey']['history'][-1]['label'], f'{fh.LABELS["kn"]} · 2 lượt')
        validate_state(s)

    def test_play_on_and_lose_everything(self):
        s = story(100)
        s, _ = self.start(s, 20)
        s, _ = self.clear(s)
        s, _ = self.act(s, 'fair_kn_next')
        run = s['journey']['fair_kn']['run']
        self.assertEqual((run['lv'], run['sg'], run['tp']), (2, 'play', []))
        s, _ = self.clear(s)
        s, _ = self.act(s, 'fair_kn_next')
        self.assertEqual(public_state(s)['fair']['knife']['run']['prize'], kn.prize(20, 2))   # at stake now
        s, r = self.lose(s)
        x = r['fair']
        self.assertEqual((x['lost'], x['hit'], x['run']['stage'], x['run']['prize']), (True, 2, 'lost', 0))
        self.assertEqual(x['run']['gone'], kn.prize(20, 2))
        self.assertEqual(s['journey']['wallet'], 80)                         # the stake and the prize so far: gone
        self.assertEqual(fh.money_of(s['journey'])[0], -20)
        self.assertEqual(s['journey']['fair_kn']['b'], 2)
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_kn_stop')
        self.assertEqual(e.exception.code, 'fair_kn_over')
        s, _ = self.start(s, 2)                                              # a new run
        validate_state(s)

    def test_x2_levels(self):
        s = story(500)
        self.dice(Dice(draws=[.1]))                                         # clearing level 1: the next is 🔥 x2
        s, _ = self.start(s, 10)
        s, r = self.clear(s)
        self.assertTrue(r['fair']['run']['nx'])
        self.assertEqual(r['fair']['run']['win'], kn.prize(10, 2) + kn.x2_bonus(10, 2))
        s, r = self.act(s, 'fair_kn_next')
        self.assertTrue(r['fair']['run']['x2'])
        self.dice(Dice(draws=[.0]))                                         # never two in a row
        s, r = self.clear(s)
        self.assertFalse(r['fair']['run']['nx'])
        bonus = kn.x2_bonus(10, 2)
        self.assertEqual((r['fair']['run']['prize'], s['journey']['fair_kn']['run']['bn']), (kn.prize(10, 2) + bonus, bonus))
        s, _ = self.act(s, 'fair_kn_next')
        self.dice(Dice(draws=[.2]))                                         # after a plain level it may come again
        s, r = self.clear(s)
        self.assertTrue(r['fair']['run']['nx'])
        s, r = self.act(s, 'fair_kn_stop')
        self.assertEqual(r['fair']['prize'], kn.prize(10, 3) + bonus)

    def test_all_ten_levels_pay_by_themselves(self):
        s = story(100)
        s, _ = self.start(s, 5)
        for lv in range(1, kn.LEVELS + 1):
            s, r = self.clear(s)
            if lv < kn.LEVELS:
                s, _ = self.act(s, 'fair_kn_next')
        x = r['fair']
        self.assertEqual((x['all'], x['paid'], x['run']['stage']), (True, kn.prize(5, kn.LEVELS), 'done'))
        self.assertEqual(s['journey']['wallet'], 95 + kn.prize(5, kn.LEVELS))
        self.assertIn('Phá đảo', r['message'])
        validate_state(s)

    def test_throws_the_server_refuses(self):
        s = story(100)
        s, _ = self.start(s, 10)
        sc = self.board(s)
        taps = safe_taps(sc, sc['need'])
        for p, code in ((dict(lv=2, taps=taps), 'fair_kn_over'), (dict(lv=1, taps=taps[::-1]), 'fair_kn_bad'),
                        (dict(lv=1, taps=[taps[0], taps[0] + 50]), 'fair_kn_bad'), (dict(lv=1, taps=[50_000]), 'fair_kn_bad'),
                        (dict(lv=1, taps=taps + [taps[-1] + 500]), 'fair_kn_bad'), (dict(lv='1', taps=taps), None),
                        (dict(lv=1), None), (dict(lv=1, taps=taps, won=True), None)):
            with self.assertRaises(GameError, msg=p) as e:
                self.act(s, 'fair_kn_throw', **p)
            if code:
                self.assertEqual(e.exception.code, code, p)
        for p in (dict(stake=3), dict(stake='10'), dict(stake=10, extra=1), dict()):
            with self.assertRaises(GameError, msg=p):
                self.act(story(100), 'fair_kn_start', **p)
        with self.assertRaises(GameError):
            self.act(s, 'fair_kn_next', lv=1)

    def test_throws_sent_in_parts(self):
        s = story(100)
        s, _ = self.start(s, 10)
        sc = self.board(s)
        taps = safe_taps(sc, sc['need'])
        self.clock.t += taps[-1] / 1000
        s, r = self.act(s, 'fair_kn_throw', lv=1, taps=taps[:3])
        self.assertEqual((r['fair']['run']['stage'], r['fair']['run']['tp'], len(r['fair']['stuck'])), ('play', taps[:3], 3))
        with self.assertRaises(GameError) as e:                              # the throws taken stay taken
            self.act(s, 'fair_kn_throw', lv=1, taps=[taps[0] + 1] + taps[1:])
        self.assertEqual(e.exception.code, 'fair_kn_bad')
        s, r = self.act(s, 'fair_kn_throw', lv=1, taps=taps)
        self.assertTrue(r['fair']['cleared'])

    def test_a_level_left_too_long_is_lost(self):
        s = story(100)
        s, _ = self.start(s, 10)
        sc = self.board(s)
        taps = safe_taps(sc, sc['need'])
        self.clock.t += (kn.LEVEL_MS + kn.SLACK) / 1000 + 1
        self.assertEqual(public_state(s)['fair']['knife']['run']['stage'], 'lost')
        s, r = self.act(s, 'fair_kn_throw', lv=1, taps=taps)
        self.assertEqual((r['fair']['lost'], r['fair']['late']), (True, True))
        self.assertEqual(s['journey']['wallet'], 90)
        s, _ = self.start(s, 10)                                             # a new run straight away
        validate_state(s)

    def test_one_run_at_a_time(self):
        s = story(100)
        s, _ = self.start(s, 10)
        with self.assertRaises(GameError) as e:
            self.start(s, 10)
        self.assertEqual(e.exception.code, 'fair_kn_busy')
        s, _ = self.clear(s)
        with self.assertRaises(GameError) as e:                              # a prize waiting: Dừng or Chơi tiếp first
            self.start(s, 10)
        self.assertEqual(e.exception.code, 'fair_kn_busy')
        with self.assertRaises(GameError):
            self.act(story(100), 'fair_kn_next')

    def test_a_choice_left_until_the_next_day_is_paid(self):
        s = story(100)
        s, _ = self.start(s, 20)
        s, _ = self.clear(s)
        s, _ = self.act(s, 'fair_kn_next')
        s, _ = self.clear(s)
        self.clock.t += 86400                                                # the next Vietnam day
        v = public_state(s)['fair']['knife']['run']
        self.assertEqual((v['stage'], v['late'], v['prize']), ('choice', True, kn.prize(20, 2)))
        s, r = self.act(s, 'fair_kn_stop')                                   # any command pays it first
        self.assertEqual((r['fair']['prize'], r['fair']['again']), (kn.prize(20, 2), True))
        self.assertEqual(s['journey']['wallet'], 80 + kn.prize(20, 2))
        s2 = story(100)
        s2, _ = self.start(s2, 20)
        s2, _ = self.clear(s2)
        self.clock.t += 86400
        s2, _ = self.act(s2, 'fair_bc', bets={'cua': 1})                    # another stall's command
        self.assertEqual(s2['journey']['fair_kn']['run']['sg'], 'done')
        self.assertEqual(s2['journey']['fair_kn']['run']['pz'], kn.prize(20, 1))
        validate_state(s2)

    def test_after_the_close(self):
        s = story(100)
        s, _ = self.start(s, 10)
        sc = self.board(s)
        taps = safe_taps(sc, sc['need'])
        self.clock.t = fh.window()[1] - 5                                    # the level began just before the close
        s['journey']['fair_kn']['run']['at'] = int(self.clock.t * 1000) - taps[-1] - 100
        s, r = self.act(s, 'fair_kn_throw', lv=1, taps=taps)                 # may still be finished
        self.assertTrue(r['fair']['cleared'])
        with self.assertRaises(GameError) as e:                              # but not played on
            self.act(s, 'fair_kn_next')
        self.assertEqual(e.exception.code, 'fair_closed')
        s, r = self.act(s, 'fair_kn_stop')                                   # the prize is still paid
        self.assertEqual(r['fair']['prize'], kn.prize(10, 1))
        self.clock.t = AFTER
        with self.assertRaises(GameError) as e:
            self.start(s, 10)
        self.assertEqual(e.exception.code, 'fair_closed')

    def test_no_loans_and_no_daily_limit(self):
        s = story(4)
        with self.assertRaises(GameError) as e:
            self.start(s, 5)
        self.assertEqual(e.exception.code, 'fair_wallet')
        s, _ = self.start(s, 2)
        s, _ = self.lose(s)
        s, _ = self.start(s, 2)
        s, _ = self.lose(s)
        self.assertEqual(s['journey']['wallet'], 0)
        with self.assertRaises(GameError):
            self.start(s, 2)
        s = story(1000)
        s['journey']['fair'] = fh.initial()
        s['journey']['fair'].update(date=fh.vn_date(self.clock.t + 2), net=-(fh.DAY_CAP + 300), rounds=fh.ROUNDS_DAY)
        s, _ = self.start(s, 20)
        self.assertEqual(s['journey']['wallet'], 980)

    def test_a_hot_day_makes_the_board_harder(self):
        s = story(100)
        s['journey']['fair'] = fh.initial()
        s['journey']['fair'].update(date=fh.vn_date(self.clock.t + 2), net=3500)
        s, r = self.start(s, 10)
        self.assertEqual(s['journey']['fair_kn']['run']['hot'], 2)
        self.assertEqual(self.board(s)['d'], 3)
        self.assertEqual(r['fair']['run']['board']['need'], kn.DIFF[3][0])
        self.assertEqual(public_state(s)['fair']['knife']['hot'], 2)

    def test_the_phi_tieu_is_gone(self):
        s = story(100)
        with self.assertRaises(GameError) as e:                              # an older client that still shows it
            self.act(s, 'fair_dart', stake=5, aim=[0, 0])
        self.assertEqual(e.exception.code, 'fair_dart_gone')
        f = public_state(s)['fair']
        self.assertNotIn('darts', f)                                         # so an older client leaves it out
        self.assertEqual(f['knife']['stakes'], list(kn.STAKES))
        self.assertIsNone(f['knife']['run'])
        s['journey']['fair'] = fh.initial()                                  # a save with phi tiêu throws loads as it was
        s['journey']['fair']['dt'] = dict(n=12, w=6, b=1)
        validate_state(s)


class Saves(FairBase):
    def test_the_save_both_ways(self):
        s = story(100)
        s, _ = self.act(s, 'fair_kn_start', stake=10)
        j = s['journey']
        self.assertEqual(set(j['fair']), set(fh.KEYS))                      # nothing new where 1.4.20 checks the keys
        self.assertNotIn('fair_run', j)                                      # nor in the luck stalls' runs
        self.assertNotIn('fair_run2', j)
        self.assertEqual(set(j['fair_kn']), set(fh.KN_KEYS))
        validate_state(s)
        good = json.loads(json.dumps(s))
        for path, v in ((('fair_kn',), []), (('fair_kn', 'n'), -1), (('fair_kn', 'run', 'st'), 3), (('fair_kn', 'run', 'lv'), 11),
                        (('fair_kn', 'run', 'sg'), 'won'), (('fair_kn', 'run', 'x2'), True), (('fair_kn', 'run', 'tp'), [1.5]),
                        (('fair_kn', 'run', 'tp'), [10**6]), (('fair_kn', 'run', 'hot'), 9), (('fair_kn', 'run', 'extra'), 1),
                        (('fair_kn', 'run', 'day'), 5)):
            bad = copy.deepcopy(good)
            box = bad['journey']
            for k in path[:-1]:
                box = box[k]
            box[path[-1]] = v
            with self.assertRaises(GameError, msg=path):
                validate_state(bad)
        older = copy.deepcopy(good)                                          # a save from before the stall
        older['journey'].pop('fair_kn')
        validate_state(older)
        self.assertIsNone(public_state(older)['fair']['knife']['run'])
        empty = copy.deepcopy(good)
        empty['journey']['fair_kn']['run'] = None
        validate_state(empty)

    def test_public_view_is_json_and_hides_the_next_level(self):
        s = story(100)
        s, _ = self.act(s, 'fair_kn_start', stake=10)
        v = public_state(s)['fair']['knife']
        json.dumps(v)
        self.assertEqual(set(v['run']['board']), {'lv', 'need', 'pre', 'th0', 'segs'})
        self.assertEqual(v['ladder'], list(kn.LADDER))
        self.assertNotIn('sd', json.dumps(v['run']))


if __name__ == '__main__':
    unittest.main()
