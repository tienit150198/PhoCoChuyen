"""🎲 Chợ đen 15/10 (game/fair_boost.py): the day's first luck round at 65%, 3–4 secret ~3-minute windows at 70% (both
only below 50,000 xu: a 50k+ round still draws 40% at most), a 3-second gap between xóc đĩa rounds, the optional save key."""
import datetime
import json
import os
import random
import unittest
from pathlib import Path
from unittest import mock

from game import fair as fh
from game import fair_boost as boost
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_fair import OPEN, FairBase, story
from tests.test_fair_scratch import Draws
from tests.test_fair_tighten import Dice

GAMES = ('xd', 'lt', 'xs')
NEXT_DAY = OPEN + 86400


class On(unittest.TestCase):
    """The boost on (tests/__init__.py turns it off for every other test), no window unless a test opens one."""
    def setUp(self):
        env = mock.patch.dict(os.environ, {'MNL_BM_BOOST_OFF': ''})
        env.start()
        self.addCleanup(env.stop)
        self.window(False)

    def window(self, on):
        p = mock.patch.object(boost, 'in_window', lambda t: on)
        p.start()
        self.addCleanup(p.stop)


class Rates(On):
    def test_first_round_of_the_day_is_65_then_ordinary(self):
        for game in GAMES:
            with self.subTest(game=game):
                j = {}
                self.assertEqual(fh.luck_p(j, None, game, OPEN, stake=20), .65)
                self.assertEqual(j[boost.KEY], dict(d=fh.vn_date(OPEN)))
                self.assertEqual(fh.luck_p(j, None, game, OPEN + 1, stake=20), .535)   # the ordinary round 2
                self.assertEqual(fh.luck_p(j, None, game, NEXT_DAY, stake=20), .65)  # a new Vietnam day

    def test_one_first_round_across_the_stalls(self):
        j = {}
        self.assertEqual(fh.luck_p(j, None, 'xd', OPEN, stake=20), .65)
        self.assertEqual(fh.luck_p(j, None, 'lt', OPEN + 1, stake=20), .55)
        self.assertEqual(fh.luck_p(j, None, 'xs', OPEN + 2, stake=20), .55)

    def test_vietnam_midnight_starts_a_new_day(self):
        midnight = datetime.datetime(2026, 10, 11, tzinfo=fh.VN).timestamp()
        j = {}
        self.assertEqual(fh.luck_p(j, None, 'xd', midnight - 1, stake=20), .65)
        self.assertEqual(fh.luck_p(j, None, 'lt', midnight - .5, stake=20), .55)
        self.assertEqual(fh.luck_p(j, None, 'lt', midnight, stake=20), .65)

    def test_50k_or_more_stays_capped_and_uses_the_first_round(self):
        for game in GAMES:
            with self.subTest(game=game):
                j = {}
                self.assertEqual(fh.luck_p(j, None, game, OPEN, stake=50_000), .40)
                self.assertEqual(fh.luck_p(j, None, 'lt' if game != 'lt' else 'xd', OPEN + 1, stake=20), .55)
                self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=49_999), .65)
                self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=10**6), .40)

    def test_a_window_draws_70_for_every_small_round(self):
        self.window(True)
        for game in GAMES:
            with self.subTest(game=game):
                j = {}
                rates = [fh.luck_p(j, None, game, OPEN + i, stake=20) for i in range(30)]
                self.assertEqual(rates, [.70] * 30)   # past the spam decay too
                self.assertEqual(fh.luck_p(j, None, game, OPEN + 31, stake=50_000), .40)
                self.assertEqual(fh.luck_p(j, None, game, OPEN + 32, stake=49_999), .70)

    def test_honest_and_free_stalls_are_unchanged(self):
        self.window(True)
        j = {}
        fh.luck_p(j, None, 'bc', OPEN, stake=20)
        self.assertEqual(fh.luck_p(j, None, 'ring', OPEN + 1), .503)
        self.assertNotIn(boost.KEY, j)
        self.assertEqual(fh.luck_p(j, None, 'xd', OPEN + 2, stake=20), .70)

    def test_off_switch(self):
        with mock.patch.dict(os.environ, {'MNL_BM_BOOST_OFF': '1'}):
            j = {}
            self.assertEqual(fh.luck_p(j, None, 'xd', OPEN, stake=20), .55)
            self.assertNotIn(boost.KEY, j)

    def test_golden_days_event_is_not_lowered(self):
        fh.golden._starts.set(int(OPEN))
        self.addCleanup(fh.golden.clear)
        self.assertEqual(fh.luck_p({}, None, 'xd', OPEN, stake=20), .70)

    def draws(self, n, rounds, seed):
        """Won share of the `rounds`-th round of fresh saves (the real _draw_luck, a seeded _rng)."""
        rng = random.Random(seed)
        won = 0
        with mock.patch.object(fh, '_rng', rng):
            for i in range(n):
                j = {}
                for r in range(rounds):
                    p = fh.luck_p(j, None, 'xd', OPEN + r, stake=20)
                    w = fh._draw_luck(j, 'xd', p)
                won += w
        return won / n

    def test_seeded_distributions(self):
        n = 20_000
        self.assertAlmostEqual(self.draws(n, 1, 1015), .65, delta=.012)
        self.assertAlmostEqual(self.draws(n, 2, 1016), .535, delta=.012)
        self.window(True)
        self.assertAlmostEqual(self.draws(n, 3, 1017), .70, delta=.012)


class Windows(unittest.TestCase):
    def setUp(self):
        boost._windows.cache_clear()
        self.addCleanup(boost._windows.cache_clear)

    def test_three_or_four_spread_non_overlapping_3_minute_windows(self):
        counts = set()
        day = datetime.date(2026, 10, 15)
        for k in range(400):
            d = day + datetime.timedelta(days=k)
            w = boost.windows(d)
            counts.add(len(w))
            self.assertIn(len(w), (3, 4))
            base = datetime.datetime(d.year, d.month, d.day, tzinfo=boost.VN).timestamp()
            for a, b in w:
                self.assertEqual(b - a, 180)
                self.assertGreaterEqual(a, base + 8 * 3600)
                self.assertLessEqual(b, base + 24 * 3600)
            for (a1, b1), (a2, b2) in zip(w, w[1:]):
                self.assertLessEqual(b1, a2)
        self.assertEqual(counts, {3, 4})

    def test_deterministic_per_date_and_salted(self):
        d = datetime.date(2026, 10, 16)
        first = boost.windows(d)
        boost._windows.cache_clear()
        self.assertEqual(boost.windows(d), first)
        self.assertNotEqual(boost.windows(d + datetime.timedelta(days=1)), first)
        with mock.patch.dict(os.environ, {'MNL_PROPERTY_SALT': 'another-server-secret-0123456789'}):
            other = [boost.windows(d + datetime.timedelta(days=k)) for k in range(5)]
        self.assertNotEqual(other, [boost.windows(d + datetime.timedelta(days=k)) for k in range(5)])

    def test_in_window_edges(self):
        d = datetime.date(2026, 10, 16)
        for a, b in boost.windows(d):
            self.assertTrue(boost.in_window(a))
            self.assertTrue(boost.in_window(b - 1))
            self.assertFalse(boost.in_window(b))
            self.assertFalse(boost.in_window(a - 1))

    def test_a_real_window_boosts_luck_p(self):
        a, _ = boost.windows(datetime.date(2026, 10, 16))[0]
        with mock.patch.dict(os.environ, {'MNL_BM_BOOST_OFF': ''}):
            j = {boost.KEY: dict(d=fh.vn_date(a))}   # the day's first round already played
            self.assertEqual(fh.luck_p(j, None, 'xd', a + 10, stake=20), .70)
            self.assertEqual(fh.luck_p(j, None, 'xd', a + 200, stake=20), .535)


class Commands(On, FairBase):
    def setUp(self):
        FairBase.setUp(self)
        On.setUp(self)
        self.t = OPEN
        p = mock.patch.object(fh, 'now', lambda: self.t)
        p.start()
        self.addCleanup(p.stop)

    def xd(self, s, draw, stake=20):
        watched = fh.bm.arrest_p(s['journey'].get('fair'), stake) > 0   # only then is the dẹp chiếu drawn for first
        self.dice(Dice(draws=[.99, draw] if watched else [draw]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=stake)
        self.t += 3.5
        return s, r['fair']['net'] > 0

    def test_xd_first_round_cutoff_then_ordinary(self):
        for draw, won in ((.649999, True), (.65, False)):
            with self.subTest(draw=draw):
                s, w = self.xd(story(10_000), draw)
                self.assertEqual(w, won)
                validate_state(s)
        s, _ = self.xd(story(10_000), .9)
        s, w = self.xd(s, .5349)   # round 2: the ordinary .535
        self.assertTrue(w)
        s, w = self.xd(s, .5199)   # round 3: .52, the same streak rules as before
        self.assertTrue(w)
        s, w = self.xd(s, .505)    # round 4: .505
        self.assertFalse(w)

    def test_xd_in_a_window(self):
        self.window(True)
        s = story(10**6)
        for _ in range(6):
            s, w = self.xd(s, .6999)
            self.assertTrue(w)
        s, w = self.xd(s, .70)
        self.assertFalse(w)
        s, w = self.xd(s, .3999, stake=50_000)
        self.assertTrue(w)
        s, w = self.xd(s, .40, stake=50_000)
        self.assertFalse(w)

    def test_xs_boosted_win_is_a_profit_and_lt_draws_the_boost(self):
        s = story(10_000)
        self.dice(Draws([.6499]))
        with mock.patch.object(fh.scratch, 'prize_mult', return_value=2) as pm:
            s, r = self.act(s, 'fair_xs', price=10)
        self.assertIs(pm.call_args.kwargs['profit_only'], True)
        self.t += 1
        self.dice(Draws([.5]))   # round 2 is ordinary: a won ticket may be a refund again
        with mock.patch.object(fh.scratch, 'prize_mult', return_value=1) as pm:
            s, r = self.act(s, 'fair_xs', price=10)
        self.assertIs(pm.call_args.kwargs['profit_only'], False)
        self.t += 1
        s2 = story(10_000)
        with mock.patch.object(fh, '_draw_luck', return_value=True) as dl:
            self.act(s2, 'fair_loto_buy', tier='lon', n=1)
        self.assertEqual(dl.call_args.args[1:], ('lt', .65))

    @mock.patch.object(boost, 'XD_GAP_MS', 3000)   # FairBase's 2 s clock steps run with no gap
    def test_xd_three_second_gap(self):
        s = story(10_000)
        s, _ = self.act(s, 'fair_xd', side='chan', stake=20)
        mark = s['journey'][boost.KEY]['xd']
        self.assertEqual(mark, int(self.t * 1000))
        for gap, left in ((.5, 3), (2.0, 1), (2.999, 1)):
            with self.subTest(gap=gap):
                self.t = OPEN + gap
                with self.assertRaises(GameError) as e:
                    self.act(s, 'fair_xd', side='le', stake=20)
                self.assertEqual(e.exception.code, 'fair_slow')
                self.assertIn(f'{left} giây', e.exception.message)
        self.t = OPEN + 1
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})   # other stalls are not held back
        self.t = OPEN + 3
        s, r = self.act(s, 'fair_xd', side='le', stake=20)
        self.assertEqual(s['journey'][boost.KEY]['xd'], int(self.t * 1000))
        self.t = OPEN - 60   # a clock gone back does not lock the stall
        s, r = self.act(s, 'fair_xd', side='le', stake=20)

    def test_nothing_reaches_the_client(self):
        self.window(True)
        s = story(10_000)
        s, r = self.act(s, 'fair_xd', side='chan', stake=20)
        view = json.dumps([public_state(s)['fair'], public_state(s)['journey'], r], ensure_ascii=False)
        self.assertNotIn(boost.KEY, view)
        for a, b in boost.windows(datetime.date(2026, 10, 10)):
            self.assertNotIn(str(a), view)


class Saves(unittest.TestCase):
    def test_old_saves_and_the_new_key_validate(self):
        s = story(100)
        self.assertNotIn(boost.KEY, s['journey'])
        validate_state(s)
        for good in ({}, dict(d='2026-10-15'), dict(xd=0), dict(d='2026-10-15', xd=1_760_000_000_000)):
            with self.subTest(good=good):
                s['journey'][boost.KEY] = good
                validate_state(s)

    def test_bad_values_are_refused(self):
        s = story(100)
        for bad in ([], 'x', dict(d='2026-13-01'), dict(d='15/10/2026'), dict(d=20261015), dict(xd=-1), dict(xd='1'),
                    dict(xd=1.5), dict(xd=10**15), dict(d='2026-10-15', at=1)):
            with self.subTest(bad=bad):
                s['journey'][boost.KEY] = bad
                with self.assertRaises(GameError):
                    validate_state(s)


class Sources(unittest.TestCase):
    def test_no_rate_in_the_client_code(self):
        js = (Path(__file__).resolve().parents[1] / 'public' / 'js' / 'v4' / 'fair.js').read_text(encoding='utf-8')
        for word in ('fair_bm_day', 'WINDOW_P', 'FIRST_P', '0.65', '.65', 'giờ vàng chợ'):
            self.assertNotIn(word, js)


if __name__ == '__main__':
    unittest.main()
