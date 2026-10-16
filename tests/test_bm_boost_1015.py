"""🎲 Chợ đen 15/10 (game/fair_boost.py) after the 16/10 rebalance: the day's first luck round at 65% and the 3–4
secret ~3-minute windows at 70% are gone (rate() is always None, luck_p draws game/fair.py's ledger bands); the
3-second gap between xóc đĩa rounds stays, and so does the optional save key (its legacy 'd' still validates)."""
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
from tests.test_fair_tighten import Dice

GAMES = ('xd', 'lt', 'xs')
NEXT_DAY = OPEN + 86400


class On(unittest.TestCase):
    """The old switch cleared (tests/__init__.py sets it): the boosts must be gone either way."""
    def setUp(self):
        env = mock.patch.dict(os.environ, {'MNL_BM_BOOST_OFF': ''})
        env.start()
        self.addCleanup(env.stop)


class Gone(On):
    def test_the_first_round_of_the_day_draws_the_ordinary_rate(self):
        for game in GAMES:
            with self.subTest(game=game):
                j = {}
                self.assertEqual(fh.luck_p(j, None, game, OPEN, stake=20), fh.BASES[game])
                self.assertNotIn(boost.KEY, j)
                self.assertEqual(fh.luck_p(j, None, game, OPEN + 30, stake=20), fh.BASES[game])
                self.assertEqual(fh.luck_p(j, None, game, NEXT_DAY, stake=20), fh.BASES[game])

    def test_rate_is_none_at_any_hour(self):
        day = datetime.datetime(2026, 10, 16, tzinfo=fh.VN).timestamp()
        for game in GAMES + ('bc', 'dg', 'ring'):
            for t in range(int(day), int(day) + 86400, 97):
                self.assertIsNone(boost.rate({}, game, t, 20, fh.BIG_WIN_FROM, 0))
        self.assertFalse(hasattr(boost, 'FIRST_P'))
        self.assertFalse(hasattr(boost, 'WINDOW_P'))
        self.assertFalse(hasattr(boost, 'windows'))

    def test_a_legacy_first_round_mark_changes_nothing(self):
        for mark in ({}, dict(d=fh.vn_date(OPEN)), dict(d='2026-10-15', xd=1)):
            j = {boost.KEY: dict(mark)}
            self.assertEqual(fh.luck_p(j, None, 'xd', OPEN, stake=20), .57)
            self.assertEqual(j[boost.KEY], mark)

    def test_50k_or_more_stays_capped(self):
        for game in GAMES:
            self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=50_000), .40)
            self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=10**6), .40)
            self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=49_999), .57)

    def test_golden_days_event_is_not_lowered(self):
        fh.golden._starts.set(int(OPEN))
        self.addCleanup(fh.golden.clear)
        self.assertEqual(fh.luck_p({}, None, 'xd', OPEN, stake=20), .70)

    def test_seeded_first_rounds(self):
        rng = random.Random(1016)
        won, n = 0, 20_000
        with mock.patch.object(fh, '_rng', rng):
            for _ in range(n):
                j = {}
                won += fh._draw_luck(j, 'xd', fh.luck_p(j, None, 'xd', OPEN, stake=20))
        self.assertAlmostEqual(won / n, .57, delta=.012)


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

    def test_xd_first_round_draws_57(self):
        for draw, won in ((.5699, True), (.57, False)):
            with self.subTest(draw=draw):
                s, w = self.xd(story(10_000), draw)
                self.assertEqual(w, won)
                self.assertNotIn('d', s['journey'][boost.KEY])
                validate_state(s)

    def test_xs_first_ticket_is_ordinary(self):
        s = story(10_000)
        self.dice(Dice(draws=[.5699]))
        with mock.patch.object(fh.scratch, 'prize_mult', return_value=2) as pm:
            s, r = self.act(s, 'fair_xs', price=10)
        self.assertIs(pm.call_args.kwargs['profit_only'], False)
        self.assertEqual(r['fair']['prize'], 20)
        s2 = story(10_000)
        with mock.patch.object(fh, '_draw_luck', return_value=True) as dl:
            self.act(s2, 'fair_loto_buy', tier='lon', n=1)
        self.assertEqual(dl.call_args.args[1:], ('lt', .57))

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
        s = story(10_000)
        s, r = self.act(s, 'fair_xd', side='chan', stake=20)
        view = json.dumps([public_state(s)['fair'], public_state(s)['journey'], r], ensure_ascii=False)
        self.assertNotIn(boost.KEY, view)
        self.assertNotIn(fh.PACE_KEY, view)


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
        for word in ('fair_bm_day', 'fair_pace', 'WINDOW_P', 'FIRST_P', '0.65', '.65', '0.57', '.57', 'giờ vàng chợ'):
            self.assertNotIn(word, js)


if __name__ == '__main__':
    unittest.main()
