"""🕶️ Chợ đen rebalance (owner 16/10: "tỷ lệ là 55 - 60% thôi … đừng cho lỗ nhưng đừng cho lãi nhiều", "phải tính cả
trường hợp người ta cheat, hoặc chơi kiểu ít tiền thua sau đó chơi tiền lớn, hoặc cheat spam ăn nhiều", "đừng giới hạn
600 ván … cho spam 1 game nhanh quá thì thua cao hơn"): the ledger-based draw, the pace penalty and its save key, the
new payouts (chiếu trong 0.75×, lô tô 1.8×, vé cào 1.775×, bão 20 / 10, đua chó +5%), the cold() hint."""
import json
import unittest
from unittest import mock

from game import fair as fh
from game import fair_dog as dog
from game import fair_scratch as xs
from game.engine import GameError, public_state, validate_state
from tests.test_fair import OPEN, Dice, FairBase, story
from tests.test_fair_scratch import Draws

T = int(OPEN)


def today(net: int, t: float = T) -> dict:
    return dict(fh.initial(), date=fh.vn_date(t), net=net)


class Bands(unittest.TestCase):
    """Today's Chợ đen net (before the round) sets the draw of xd/lt/xs."""
    def p(self, net, stake, game='xd', f=None):
        return fh.luck_p({}, today(net) if f is None else f, game, T, stake=stake)

    def test_each_band(self):
        for net, stake, want in ((0, 1000, .57), (30_000, 1000, .57), (30_001, 1000, .52), (99_999, 1000, .52),
                                 (100_000, 1000, .45), (10**6, 10, .45), (-1, 1, .60), (0, 1, .57)):
            for game in fh.DRAWN:
                with self.subTest(net=net, stake=stake, game=game):
                    self.assertEqual(self.p(net, stake, game), want)

    def test_winning_back_is_for_small_stakes_only(self):
        """A stake of at most min(−net, 5,000): losing a little then betting big gains nothing."""
        for net, stake, want in ((-3000, 3000, .60), (-3000, 3001, .57), (-10_000, 5000, .60), (-10_000, 5001, .57),
                                 (-10**6, 5000, .60), (-10**6, 45_000, .57), (-10**6, 49_999, .57), (-10, 45_000, .57)):
            with self.subTest(net=net, stake=stake):
                self.assertEqual(self.p(net, stake), want)

    def test_yesterday_and_no_state_count_as_zero(self):
        old = dict(fh.initial(), date=fh.vn_date(T - 86400), net=10**6)
        self.assertEqual(self.p(0, 1000, f=old), .57)
        self.assertEqual(fh.luck_p({}, None, 'xd', T, stake=1000), .57)

    def test_big_stakes_stay_at_40(self):
        for net in (-10**6, 0, 50_000, 10**6):
            for game in fh.DRAWN:
                self.assertEqual(self.p(net, 50_000, game), fh.BIG_WIN_P)
        self.assertEqual(self.p(0, 49_999), .57)

    def test_never_below_40(self):
        j, f = {}, today(10**6)
        ps = [fh.luck_p(j, f, 'xd', T + i, stake=10) for i in range(30)]
        self.assertEqual(ps[:10], [.45] * 10)
        self.assertEqual(ps[10:15], [.40] * 5)   # .45 − .05
        self.assertEqual(ps[15:], [.40] * 15)    # .45 − .12 = .33 → the floor
        self.assertEqual(min(ps), fh.P_MIN)

    def test_ring_is_unchanged(self):
        j = {}
        self.assertEqual([fh.luck_p(j, today(-500), 'ring', T + i) for i in range(12)],
                         [fh.run_rate('ring', n) for n in range(1, 13)])
        self.assertEqual(fh.run_rate('ring', 1), .503)
        self.assertNotIn(fh.PACE_KEY, j)

    def test_the_streak_cool_off_still_holds_at_60(self):
        j = {'fair_balance': {'xd': fh.STREAK}}
        with mock.patch.object(fh, '_rng', Dice(draws=[.449])):
            self.assertTrue(fh._draw_luck(j, 'xd', fh.P_BACK))
        with mock.patch.object(fh, '_rng', Dice(draws=[.45])):
            self.assertFalse(fh._draw_luck(j, 'xd', fh.P_BACK))
        j = {}
        with mock.patch.object(fh, '_rng', Dice(draws=[.5999])):
            self.assertTrue(fh._draw_luck(j, 'xd', fh.P_BACK))
        self.assertEqual(j['fair_balance']['xd'], 1)


class Pace(unittest.TestCase):
    def test_10_11_16_rounds_in_a_minute(self):
        j, f = {}, today(0)
        ps = [fh.luck_p(j, f, 'xd', T + 3 * i, stake=1000) for i in range(20)]
        self.assertEqual(ps[:10], [.57] * 10)
        self.assertEqual(ps[10:15], [.52] * 5)
        self.assertEqual(ps[15:], [.45] * 5)
        self.assertEqual(fh.pace_cut(10), 0)
        self.assertEqual(fh.pace_cut(11), .05)
        self.assertEqual(fh.pace_cut(15), .05)
        self.assertEqual(fh.pace_cut(16), .12)

    def test_per_stall(self):
        j, f = {}, today(0)
        for i in range(15):
            fh.luck_p(j, f, 'xd', T + i, stake=100)
        self.assertEqual(fh.luck_p(j, f, 'lt', T + 15, stake=100), .57)
        self.assertEqual(fh.luck_p(j, f, 'xs', T + 15, stake=100), .57)
        self.assertEqual(fh.luck_p(j, f, 'xd', T + 15, stake=100), .45)   # the xd's 16th

    def test_a_minute_away_warms_it_up_and_old_times_are_pruned(self):
        j, f = {}, today(0)
        for i in range(25):
            fh.luck_p(j, f, 'xd', T + i, stake=100)
        self.assertEqual(len(j[fh.PACE_KEY]['xd']), fh.PACE_KEEP)
        self.assertEqual(fh.pace_now(j, 'xd', T + 24), 20)
        self.assertEqual(fh.pace_now(j, 'xd', T + 24 + 60), 0)
        self.assertEqual(fh.luck_p(j, f, 'xd', T + 84, stake=100), .57)
        self.assertEqual(j[fh.PACE_KEY]['xd'], [T + 84])
        fh.luck_p(j, f, 'lt', T + 200, stake=100)   # the other stalls' stale times go
        self.assertEqual(j[fh.PACE_KEY], {'lt': [T + 200]})

    def test_the_window_edge(self):
        j, f = {}, today(0)
        for i in range(10):
            fh.luck_p(j, f, 'xs', T + i, stake=10)
        self.assertEqual(fh.luck_p(j, f, 'xs', T + 59, stake=10), .52)    # T+0 is 59 s old: still inside
        j2 = {fh.PACE_KEY: {'xs': [T + i for i in range(10)]}}
        self.assertEqual(fh.luck_p(j2, f, 'xs', T + 60, stake=10), .57)   # T+0 is 60 s old: gone

    def test_bao_and_dog_prices_slow_down_from_11(self):
        f = today(0)
        self.assertEqual(fh.bc_bao(f, 10, T), fh.BAO)
        self.assertEqual(fh.bc_bao(f, 11, T), fh.BAO_LOW)
        self.assertEqual(fh.bc_bao(today(99_999), 1, T), fh.BAO)
        self.assertEqual(fh.bc_bao(today(100_000), 1, T), fh.BAO_LOW)
        self.assertFalse(fh.slow_odds(f, 10, T))
        self.assertTrue(fh.slow_odds(f, 11, T))
        self.assertTrue(fh.slow_odds(today(100_000), 1, T))
        self.assertFalse(fh.slow_odds(None, 1, T))


class Cold(unittest.TestCase):
    def test_the_hint_says_the_next_round_is_slowed(self):
        j, f = {}, today(0)
        for i in range(9):
            fh.luck_p(j, f, 'xd', T + i, stake=10)
        self.assertIsNone(fh.cold(j, T + 9))   # the next round is the 10th: not slowed
        fh.luck_p(j, f, 'xd', T + 9, stake=10)
        self.assertEqual(fh.cold(j, T + 9), dict(game='xd', pace=True, n=10, gap=1))
        self.assertIsNone(fh.cold(j, T + 69))   # a minute later
        self.assertIsNone(fh.cold({}, T))

    def test_the_latest_stall_and_honest_stalls_too(self):
        j = {fh.PACE_KEY: {'xd': [T + i for i in range(12)], 'bc': [T + 20 + i for i in range(10)],
                           'dg': [T + i for i in range(3)]}}
        self.assertEqual(fh.cold(j, T + 30)['game'], 'bc')
        j[fh.PACE_KEY]['dg'] = [T + 25 + i for i in range(11)]
        self.assertEqual(fh.cold(j, T + 40), dict(game='dg', pace=True, n=11, gap=1))

    def test_no_rate_in_the_hint(self):
        j = {fh.PACE_KEY: {'lt': [T + i for i in range(15)]}}
        text = json.dumps(fh.cold(j, T + 15))
        for word in ('.5', '.4', 'p', 'switch', 'min'):
            self.assertNotIn(f'"{word}"', text)
        self.assertEqual(set(fh.cold(j, T + 15)), {'game', 'pace', 'n', 'gap'})


class Saves(unittest.TestCase):
    def test_good_saves(self):
        s = story(100)
        for good in ({}, {'xd': []}, {'xd': [T]}, {g: [T + i for i in range(fh.PACE_KEEP)] for g in fh.PACE_GAMES},
                     {'bc': [0, 10**11]}):
            with self.subTest(good=good):
                s['journey'][fh.PACE_KEY] = good
                validate_state(s)

    def test_forged_saves_are_refused(self):
        s = story(100)
        for bad in ([], 'x', None, {'ring': [T]}, {'kn': []}, {'xd': [T] * (fh.PACE_KEEP + 1)}, {'xd': T},
                    {'xd': [str(T)]}, {'xd': [T + .5]}, {'xd': [True]}, {'xd': [-1]}, {'xd': [10**11 + 1]},
                    {'xd': {'0': T}}, {'xd': [[T]]}):
            with self.subTest(bad=bad):
                s['journey'][fh.PACE_KEY] = bad
                with self.assertRaises(GameError):
                    validate_state(s)

    def test_old_cool_data_stays_readable(self):
        s = story(100)
        s['journey'][fh.COOL_KEY] = {'xd': dict(n=30, at=T, sw=0, st=100)}
        validate_state(s)


class Payouts(unittest.TestCase):
    def test_chieu_trong_pays_three_quarters(self):
        self.assertEqual([fh.xd_win(x) for x in (10, 11, 20, 1000, 1001, 49_999, 10**7)],
                         [7, 8, 15, 750, 750, 37_499, 7_500_000])

    def test_loto_pays_18_tenths(self):
        self.assertEqual(set(fh.LOTO_PAY.values()), {18})
        self.assertEqual(fh.prize_of('thuong', 100, 1), 180)
        self.assertEqual(fh.prize_of('dem', 1000, 3), 5400)
        self.assertEqual(fh.prize_of('doi', 2, 1), 3)
        self.assertEqual(fh.prize_of('nguoc', 5, 1), 9)
        self.assertEqual(fh.LOTO_PRIZE, fh.prize_of('thuong', fh.LOTO_PRICE, 1))

    def test_scratch_table(self):
        self.assertEqual(xs.PRIZES, ((1.5, 800), (2, 140), (3, 40), (5, 15), (20, 5)))
        total = sum(w for _, w in xs.PRIZES)
        self.assertEqual(total, 1000)
        self.assertAlmostEqual(sum(m * w for m, w in xs.PRIZES) / total, 1.775)
        self.assertNotIn(1, xs.MULTS)
        self.assertEqual(xs.amount(2, 1.5), 3)
        self.assertEqual(xs.amount(5, 1.5), 7)
        self.assertEqual(xs.amount(1000, 20), 20_000)
        self.assertEqual(xs.amount(10, 0), 0)
        for price in xs.TIERS:   # every prize of a ticket is a profit and a distinct amount
            amounts = [xs.amount(price, m) for m in xs.MULTS]
            self.assertEqual(len(set(amounts)), len(amounts))
            self.assertGreater(min(amounts), price)

    def test_scratch_draw_matches_the_weights(self):
        rng = Draws(seed=11)
        n = 200_000
        counts = {}
        for _ in range(n):
            m = xs.prize_mult(rng)
            counts[m] = counts.get(m, 0) + 1
        mean = sum(m * c for m, c in counts.items()) / n
        self.assertAlmostEqual(mean, 1.775, delta=.02)
        for m, w in xs.PRIZES:
            self.assertAlmostEqual(counts[m] / n, w / 1000, delta=.005)

    def test_scratch_layout_reads_its_prize(self):
        rng = Draws(seed=3)
        for price in xs.TIERS:
            for m in (0,) + xs.MULTS:
                cells = xs.layout(price, m, rng)
                self.assertEqual(len(cells), xs.CELLS)
                self.assertEqual(xs.read(cells), xs.amount(price, m))

    def test_bau_cua_bao(self):
        self.assertEqual((fh.BAO, fh.BAO_LOW), (20, 10))
        self.assertEqual(fh.bc_back({'cua': 10}, ['cua'] * 3), 210)
        self.assertEqual(fh.bc_back({'cua': 10}, ['cua'] * 3, fh.BAO_LOW), 110)
        self.assertEqual(fh.bc_back({'cua': 10, 'bau': 5}, ['cua', 'cua', 'bau'], fh.BAO_LOW), 40)
        one = sum(fh.bc_back({'cua': 1}, list(d)) for d in fh.BC_OUTCOMES)
        self.assertEqual(one, 216)   # a single face returns exactly 100%
        low = sum(fh.bc_back({'cua': 1}, list(d), fh.BAO_LOW) for d in fh.BC_OUTCOMES)
        self.assertEqual(low, 206)

    def test_dog_prices(self):
        self.assertEqual(dog.OLD, ((320, 29), (240, 39), (180, 52), (120, 78), (90, 105), (50, 190)))
        for (w, m), (w0, m0) in zip(dog.CLASSES, dog.OLD):
            self.assertEqual(w, w0)
            self.assertLessEqual(w * m, 10_000)                    # no dog returns more than 100%
            self.assertLessEqual(abs(m - m0 * 1.05), .55)          # about 5% up, to a tenth
            self.assertGreater(m, m0)
        self.assertEqual(sum(w for w, _ in dog.CLASSES), 1000)
        self.assertEqual([dog.pay(c) for c in range(6)], [30, 41, 55, 82, 110, 200])
        self.assertEqual([dog.pay(c, True) for c in range(6)], [29, 39, 52, 78, 105, 190])
        self.assertEqual(dog.back(1000, 5), 20_000)
        self.assertEqual(dog.back(1000, 5, True), 19_000)
        self.assertEqual(dog.back(15, 0), 45)

    def test_boosts_are_gone(self):
        for game in ('xd', 'lt', 'xs', 'bc', 'ring', 'dg'):
            with mock.patch.dict('os.environ', {'MNL_BM_BOOST_OFF': ''}):
                self.assertIsNone(fh.boost.rate({}, game, T, 10, fh.BIG_WIN_FROM, 0))
        j = {}
        self.assertEqual(fh.luck_p(j, today(0), 'xd', T, stake=10), .57)   # the day's first round: no 65%
        self.assertNotIn(fh.boost.KEY, j)


class Commands(FairBase):
    def net(self, s, net):
        f = fh._state(s['journey'], self.clock.t + 2)
        f['net'] = net
        return s

    def pace(self, s, game, n):
        s['journey'][fh.PACE_KEY] = {game: [int(self.clock.t) - i for i in range(n)]}
        return s

    def test_xd_win_pays_three_quarters(self):
        self.dice(Dice(draws=[.1]))
        s, r = self.act(story(5000), 'fair_xd', side='chan', stake=1000)
        self.assertEqual(r['fair']['net'], 750)
        self.assertEqual(s['journey']['wallet'], 5750)
        self.assertIn('Thắng 750 xu', r['message'])
        self.dice(Dice(draws=[.99]))
        s, r = self.act(s, 'fair_xd', side='le', stake=1000)
        self.assertEqual(r['fair']['net'], -1000)
        self.assertEqual(s['journey']['wallet'], 4750)
        self.dice(Dice(draws=[.1]))
        s, r = self.act(s, 'fair_xd', side='le', stake=11)
        self.assertEqual(r['fair']['net'], 8)

    def test_xd_draw_follows_the_ledger(self):
        for net, stake, draw, won in ((0, 100, .5699, True), (0, 100, .57, False), (-200, 100, .5999, True),
                                      (-200, 300, .5999, False), (40_000, 100, .5199, True), (40_000, 100, .52, False),
                                      (100_000, 100, .4499, True), (100_000, 100, .45, False)):
            with self.subTest(net=net, stake=stake, draw=draw):
                s = self.net(story(10_000), net)
                self.dice(Dice(draws=[draw]))
                s, r = self.act(s, 'fair_xd', side='chan', stake=stake)
                self.assertEqual(r['fair']['net'] > 0, won)
                validate_state(s)

    def test_xd_pace_in_the_command(self):
        s = self.net(story(10**6), 1000)   # today a little up: the .57 band all along
        for i in range(10):
            self.dice(Dice(draws=[.1 if i % 2 else .99]))
            s, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertEqual(len(s['journey'][fh.PACE_KEY]['xd']), 10)
        self.assertEqual(public_state(s)['fair']['cool'], dict(game='xd', pace=True, n=10, gap=1))
        self.dice(Dice(draws=[.52]))   # the 11th in a minute: .57 − .05
        s2, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertLess(r['fair']['net'], 0)
        self.dice(Dice(draws=[.5199]))
        s2, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertGreater(r['fair']['net'], 0)
        validate_state(s2)

    def test_bao_20_then_10(self):
        cases = ((0, 0, 20), (0, 10, 10), (100_000, 0, 10), (0, 9, 20))
        for net, before, mult in cases:
            with self.subTest(net=net, before=before):
                s = self.net(story(1000), net)
                if before:
                    self.pace(s, 'bc', before)
                self.dice(Dice(faces=['cua'] * 3))
                s, r = self.act(s, 'fair_bc', bets={'cua': 10})
                self.assertEqual(r['fair']['bao'], 'cua')
                self.assertEqual(r['fair']['bao_x'], mult)
                self.assertEqual(r['fair']['back'], 10 * (1 + mult))
                self.assertEqual(r['fair']['net'], 10 * mult)
                self.assertEqual(s['journey']['wallet'], 1000 + 10 * mult)
                validate_state(s)

    def test_dog_prices_in_the_command(self):
        for net, before, old in ((0, 0, False), (0, 10, True), (100_000, 0, True)):
            with self.subTest(net=net, before=before):
                s = self.net(story(10_000), net)
                if before:
                    self.pace(s, 'dg', before)
                race = dog.race(self.clock.t + 2)
                lanes = dog.lineup(race)
                with mock.patch.object(dog, 'draw', lambda ln, rng: list(range(len(ln)))):
                    s, r = self.act(s, 'fair_dg', race=race, lane=0, stake=100)
                cls = lanes[0][1]
                self.assertTrue(r['fair']['won'])
                self.assertEqual(r['fair']['mult'], dog.pay(cls, old))
                self.assertEqual(r['fair']['back'], dog.back(100, cls, old))
                self.assertEqual(s['journey']['wallet'], 10_000 - 100 + dog.back(100, cls, old))
                validate_state(s)

    def test_dog_board_shows_the_prices_of_the_next_bet(self):
        s = story(100)
        board = public_state(s)['fair']['dog']['races'][0][1]
        self.assertEqual(sorted(m for _, m in board), sorted(m for _, m in dog.CLASSES))
        self.pace(s, 'dg', 10)
        board = public_state(s)['fair']['dog']['races'][0][1]
        self.assertEqual(sorted(m for _, m in board), sorted(m for _, m in dog.OLD))

    def test_scratch_ticket(self):
        self.dice(Draws([.1], seed=5))
        with mock.patch.object(fh.scratch, 'prize_mult', return_value=1.5):
            s, r = self.act(story(1000), 'fair_xs', price=5)
        d = r['fair']
        self.assertEqual((d['prize'], d['mult'], d['net']), (7, 1.5, 2))
        self.assertEqual(xs.read(d['cells']), 7)
        self.assertEqual(len(d['hits']), 3)
        self.assertEqual(s['journey']['wallet'], 1002)
        rules = public_state(s)['fair']['scratch']
        self.assertEqual(rules['mults'], [1.5, 2, 3, 5, 20])

    def test_loto_kinh_pays_18(self):
        s = story(10_000)
        with mock.patch.object(fh, '_draw_luck', return_value=True) as dl:
            s, _ = self.act(s, 'fair_loto_buy', tier='tram', n=1)
        self.assertEqual(dl.call_args.args[1:], ('lt', .57))
        g = public_state(s)['fair']['ganh']
        self.assertEqual({v['pay'] for v in g['modes_rule'].values()}, {1.8})
        lt = public_state(s)['fair']['loto']
        self.assertEqual(lt['prize'], fh.prize_of(lt['mode'], 100, 1))

    def test_public_rules_and_no_rate(self):
        s = story(10_000)
        s, _ = self.act(s, 'fair_xd', side='chan', stake=20)
        fair = public_state(s)['fair']
        self.assertEqual((fair['rules']['bao'], fair['rules']['bao_low'], fair['rules']['xd_pay']), (20, 10, 75))
        view = json.dumps(fair)
        for word in ('0.57', '0.52', '0.45', '0.6,', 'fair_pace', 'P_BACK', 'HOT_FROM'):
            self.assertNotIn(word, view)


if __name__ == '__main__':
    unittest.main()
