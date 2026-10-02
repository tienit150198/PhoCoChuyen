"""🎟️ Vé số cào at the fair (game/fair_scratch.py, game/fair.py fair_xs): the prize table and its odds, the grid under
the silver always reading the same as the result, the purchase paying at once, the wallet as the only limit, the run
of tickets in its own key (journey['fair_run2']), nothing new in journey['fair'], the public view."""
import json
import random
import unittest

from game import fair as fh
from game import fair_scratch as xs
from game.engine import GameError, public_state, validate_state

from tests.test_fair import AFTER, OPEN, FairBase, story


class Draws(random.Random):
    """A seeded random source whose random() (the win draw) comes from a list."""
    def __new__(cls, draws=(), seed=7):   # Python 3.12's Random.__new__ takes one argument at most
        return super().__new__(cls, seed)

    def __init__(self, draws=(), seed=7):
        super().__init__(seed)
        self.draws = list(draws)

    def random(self):
        return self.draws.pop(0) if self.draws else super().random()


class Table(unittest.TestCase):
    def ev(self, p):
        total = sum(w for _, w in xs.PRIZES)
        return p * sum(m * w for m, w in xs.PRIZES) / total

    def test_wins_feel_winnable_and_the_return_stays_near_even(self):
        # owner 03/10: "có cảm giác thắng thua, không lỗ quá hoặc không quá lời"
        for p in (xs.P_HI, xs.P_LO):
            self.assertTrue(.35 <= p <= .45, p)
            self.assertTrue(.95 <= self.ev(p) <= 1.05, (p, self.ev(p)))
        self.assertGreater(xs.P_HI, xs.P_LO)
        self.assertEqual(xs.MULTS[0], 1)                                  # hoàn vé
        self.assertEqual(sorted(xs.MULTS), list(xs.MULTS))
        self.assertEqual(len(set(xs.MULTS)), len(xs.MULTS))

    def test_the_taper(self):
        self.assertEqual(xs.win_p(0), xs.P_HI)
        self.assertEqual(xs.win_p(fh.TAPER_FROM), xs.P_HI)
        self.assertAlmostEqual(xs.win_p((fh.TAPER_FROM + fh.TAPER_TO) // 2), (xs.P_HI + xs.P_LO) / 2)
        self.assertEqual(xs.win_p(10**6), xs.P_LO)

    def test_prize_draws_follow_the_weights(self):
        rng = random.Random(4)
        n = 200_000
        seen = {m: 0 for m in xs.MULTS}
        for _ in range(n):
            seen[xs.prize_mult(rng)] += 1
        total = sum(w for _, w in xs.PRIZES)
        for m, w in xs.PRIZES:
            self.assertAlmostEqual(seen[m] / n, w / total, delta=.006, msg=m)

    def test_the_grid_reads_the_same_as_the_result(self):
        rng = random.Random(9)
        for i in range(20000):
            price = xs.TIERS[i % len(xs.TIERS)]
            mult = 0 if i % 3 else xs.prize_mult(rng)
            cells = xs.layout(price, mult, rng)
            self.assertEqual(len(cells), xs.CELLS)
            self.assertEqual(xs.read(cells), mult * price, cells)
            for v in set(cells):
                self.assertIn(v // price, xs.MULTS)
                self.assertEqual(v % price, 0)
                self.assertLessEqual(cells.count(v), xs.MATCH if v == mult * price else xs.MATCH - 1, cells)
            if mult:
                self.assertEqual(cells.count(mult * price), xs.MATCH)


class Scratch(FairBase):
    def buy(self, s, price=5, draws=(), seed=7, **p):
        self.dice(Draws(draws, seed))
        return self.act(s, 'fair_xs', price=price, **p)

    def test_a_losing_and_a_winning_ticket(self):
        s = story(100)
        s, r = self.buy(s, 10, [.99])
        x = r['fair']
        self.assertEqual((x['game'], x['price'], x['prize'], x['mult'], x['net'], x['hits']), ('xs', 10, 0, 0, -10, []))
        self.assertEqual(xs.read(x['cells']), 0)
        self.assertEqual(r['message'], '')                         # the result shows once the silver is scratched off
        self.assertEqual(s['journey']['wallet'], 90)
        s, r = self.buy(s, 10, [.01])
        x = r['fair']
        self.assertGreater(x['mult'], 0)
        self.assertEqual((x['prize'], x['net']), (10 * x['mult'], 10 * x['mult'] - 10))
        self.assertEqual(xs.read(x['cells']), x['prize'])
        self.assertEqual(len(x['hits']), xs.MATCH)
        self.assertTrue(all(x['cells'][i] == x['prize'] for i in x['hits']))
        self.assertEqual(s['journey']['wallet'], 90 + x['prize'] - 10)
        self.assertEqual(x['name'], xs.NAMES[10])
        row = s['journey']['history'][-1]                          # one Sổ ví row for the day's tickets
        self.assertEqual((row['kind'], row['amount'], row['label']), ('fair', x['prize'] - 20, f'{fh.LABELS["xs"]} · 2 vé'))
        self.assertEqual(fh.today_xu(s['journey'])['xs'], x['prize'] - 20)
        self.assertEqual(s['journey']['fair']['net'], x['prize'] - 20)
        validate_state(s)

    def test_nothing_new_in_the_fair_save(self):
        s = story(100)
        s, _ = self.buy(s, 2, [.99])
        self.assertEqual(set(s['journey']['fair']), set(fh.KEYS))   # older validators reject unknown keys there
        self.assertNotIn('fair_run', s['journey'])                  # 1.4.17's validator knows only its stalls there
        self.assertEqual(s['journey']['fair_run2']['g'], 'xs')
        self.assertNotIn('xs', fh.RUN_GAMES)

    def test_the_odds_follow_todays_net(self):
        s = story(100)
        s['journey']['fair'] = fh.initial()
        s['journey']['fair']['date'] = fh.vn_date(self.clock.t + 2)
        s['journey']['fair']['net'] = 3500                          # halfway down the taper: 40.5 %
        s, r = self.buy(s, 2, [.41])
        self.assertEqual(r['fair']['mult'], 0)
        s, r = self.buy(s, 2, [.40])
        self.assertGreater(r['fair']['mult'], 0)
        s['journey']['fair']['net'] = 9000                          # far ahead: P_LO
        s, r = self.buy(s, 2, [xs.P_LO + .005])
        self.assertEqual(r['fair']['mult'], 0)
        s['journey']['fair']['net'] = -400                          # behind: P_HI
        s, r = self.buy(s, 2, [xs.P_HI - .005])
        self.assertGreater(r['fair']['mult'], 0)

    def test_a_long_run_of_tickets_cools_to_the_floor(self):
        j, f = {}, dict(fh.initial(), date=fh.vn_date(OPEN))
        ps = [fh.luck_p(j, f, 'xs', OPEN + 5 * i, xs.P_HI, xs.P_LO) for i in range(40)]
        self.assertEqual(ps[:fh.RUN_FREE], [xs.P_HI] * fh.RUN_FREE)
        self.assertAlmostEqual(ps[fh.RUN_FREE], xs.P_HI - xs.RUN_STEP)
        self.assertEqual(ps[-1], xs.P_LO)
        self.assertEqual(ps, sorted(ps, reverse=True))
        self.assertEqual(set(j), {'fair_run2'})
        fh.luck_p(j, f, 'bc', OPEN + 300)                           # another stall: one run at a time
        self.assertEqual(set(j), {'fair_run'})
        self.assertEqual(fh.luck_p(j, f, 'xs', OPEN + 305, xs.P_HI, xs.P_LO), xs.P_HI)
        self.assertEqual(set(j), {'fair_run2'})
        s = story(100)
        s['journey']['fair_run2'] = dict(g='xs', n=3, at=1)
        validate_state(s)
        for bad in (dict(g='bc', n=3, at=1), dict(g='xs', n=-1, at=1), dict(g='xs', n=1), [1]):
            s['journey']['fair_run2'] = bad
            with self.assertRaises(GameError, msg=bad):
                validate_state(s)
        s['journey'].pop('fair_run2')
        s['journey']['fair_run'] = dict(g='xs', n=3, at=1)          # never written there: the old key keeps its stalls
        with self.assertRaises(GameError):
            validate_state(s)

    def test_win_rate_and_return_over_many_tickets(self):
        s = story(10**6)
        self.dice(random.Random(11))
        wins = paid = back = 0
        for i in range(1200):
            s['journey'].setdefault('fair', fh.initial())['net'] = 0   # the generous odds
            s['journey'].pop('fair_run2', None)                       # not one long run
            s, r = self.act(s, 'fair_xs', price=2)
            wins += r['fair']['mult'] > 0
            paid += 2
            back += r['fair']['prize']
        self.assertTrue(.37 < wins / 1200 < .47, wins)
        self.assertTrue(.8 < back / paid < 1.3, back / paid)

    def test_prices_and_bad_payloads(self):
        s = story(100)
        for p in (dict(price=3), dict(price='5'), dict(price=5.0), dict(price=True), dict(price=50), dict(price=5, extra=1), dict()):
            with self.assertRaises(GameError, msg=p):
                self.dice(Draws([.1]))
                self.act(s, 'fair_xs', **p)

    def test_no_loans_and_never_below_zero(self):
        s = story(4)
        with self.assertRaises(GameError) as e:
            self.buy(s, 5, [.99])
        self.assertEqual(e.exception.code, 'fair_wallet')
        s, _ = self.buy(s, 2, [.99])
        s, _ = self.buy(s, 2, [.99])
        self.assertEqual(s['journey']['wallet'], 0)
        with self.assertRaises(GameError):
            self.buy(s, 2, [.99])

    def test_no_daily_money_or_ticket_limit(self):
        s = story(1000)
        s['journey']['fair'] = fh.initial()
        s['journey']['fair'].update(date=fh.vn_date(self.clock.t + 2), net=-(fh.DAY_CAP + 300), rounds=fh.ROUNDS_DAY)
        s, r = self.buy(s, 20, [.99])
        self.assertEqual(r['fair']['net'], -20)
        validate_state(s)

    def test_too_fast(self):
        s = story(100)
        s, _ = self.buy(s, 2, [.99])
        self.clock.t -= 2 - 0.3                                      # 0.3 s after the last ticket
        with self.assertRaises(GameError) as e:
            self.buy(s, 2, [.99])
        self.assertEqual(e.exception.code, 'fair_slow')

    def test_no_points_for_the_stall(self):
        s = story(100)
        s['journey']['fair'] = fh.initial()
        today = fh.vn_date(self.clock.t + 2)
        s['journey']['fair'].update(date=today, ed=fh.edition(), pday=today, pts=7)   # the day's visit already counted
        s, r = self.buy(s, 2, [.01])
        self.assertNotIn('points', r['fair'])   # the board counts xu since 03/10
        self.assertEqual(s['journey']['fair']['pts'], 7)

    def test_the_row_count_survives_a_long_day(self):
        s = story(10**5)
        s['journey']['history'].append(dict(day=s['journey']['life_day'], kind='fair', amount=-30, career=None,
                                            label=f'{fh.LABELS["xs"]} · 41 vé'))
        s, _ = self.buy(s, 2, [.99])
        self.assertEqual(s['journey']['history'][-1]['label'], f'{fh.LABELS["xs"]} · 42 vé')
        self.assertEqual(fh._row_count(None), 0)
        self.assertEqual(fh._row_count(dict(label='x · y vé')), 0)

    def test_closed_after_the_fair(self):
        s = story(100)
        self.clock.t = AFTER
        with self.assertRaises(GameError) as e:
            self.buy(s, 2, [.1])
        self.assertEqual(e.exception.code, 'fair_closed')

    def test_public(self):
        s = story(100)
        v = public_state(s)['fair']['scratch']
        self.assertEqual((v['tiers'], v['cells'], v['match'], v['mults']), (list(xs.TIERS), xs.CELLS, xs.MATCH, list(xs.MULTS)))
        self.assertEqual(v['names']['20'], xs.NAMES[20])
        json.dumps(v)


if __name__ == '__main__':
    unittest.main()
