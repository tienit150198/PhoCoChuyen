"""Golden-days odds depend on this round's stake and today's Chợ đen net (owner 11/10: the 70% only for a stake
under 50,000 while today's net is at most 300,000; 40% from 300,000), never the wallet."""
import random
from unittest import mock

from game import engine, fair as fh, fair_golden_days as golden
from tests.test_fair import OPEN, Dice, FairBase, story
from tests.test_fair_scratch import Draws


class GoldenHighStakes(FairBase):
    def setUp(self):
        super().setUp()
        golden._starts.set(int(OPEN))
        self.addCleanup(golden.clear)

    def test_threshold_starts_at_300000_per_round(self):
        # owner 11/10 (evening): from fair.BIG_WIN_FROM a round draws at most fair.BIG_WIN_P, event or not
        for stake, expected in [(10, .70), (49999, .70), (50000, .40), (299000, .40), (299999, .40),
                                (300000, .40), (300001, .40), (1000000, .40)]:
            with self.subTest(stake=stake):
                self.assertEqual(fh.luck_p({}, None, 'xd', OPEN, stake=stake), expected)

    def test_the_event_rate_boundaries(self):
        W, H = golden.WIN_P, golden.HIGH_STAKE_WIN_P
        self.assertEqual((golden.SMALL_STAKE, golden.NET_STOP, golden.HIGH_STAKE), (50_000, 300_000, 300_000))
        for stake, net, expected in [(10, 0, W), (49_999, 0, W), (50_000, 0, None), (299_999, 0, None),
                                     (49_999, 300_000, W), (49_999, 300_001, None), (10, -10**6, W), (10, 10**8, None),
                                     (300_000, 0, H), (300_000, 300_001, H), (10**7, 10**8, H)]:
            with self.subTest(stake=stake, net=net):
                self.assertEqual(golden.rate(stake, net), expected)

    def test_today_s_net_stops_the_boost(self):
        """luck_p reads today's net from journey['fair'] (an older day's does not count)."""
        for net, expected in [(0, .70), (300_000, .70), (300_001, fh.BASES['xd']), (10**6, fh.BASES['xd'])]:
            with self.subTest(net=net):
                f = dict(fh.initial(), date=fh.vn_date(OPEN), net=net)
                self.assertEqual(fh.luck_p({}, f, 'xd', OPEN, stake=49_999), expected)
                self.assertEqual(fh.luck_p({}, f, 'xd', OPEN, stake=300_000), .40)
        yesterday = dict(fh.initial(), date='2026-10-09', net=10**6)
        self.assertEqual(fh.luck_p({}, yesterday, 'xd', OPEN, stake=49_999), .70)

    def test_scratch_event_prizes_only_with_the_boost(self):
        """A vé cào pays the event's prizes (no break-even refund) only for a round drawn at golden.WIN_P."""
        for net, boosted in ((0, True), (300_000, True), (300_001, False)):
            with self.subTest(net=net):
                s = story(1000)
                s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition(), net=net)
                self.dice(Draws([0]))   # a won ticket
                with mock.patch.object(fh.scratch, 'prize_mult', return_value=2) as pm:
                    s, r = self.act(s, 'fair_xs', price=10)
                pm.assert_called_once()
                self.assertIs(pm.call_args.kwargs['profit_only'], boosted)

    @mock.patch.object(fh, 'GRACE_ROUNDS', 1000)
    def test_alternating_stakes_and_large_wallet_do_not_carry_the_boost(self):
        s = story(10000000)
        for stake, won in [(49999, True), (50000, False), (299999, False), (300000, False), (10, True), (1000000, False)]:
            watched = fh.bm.arrest_p(s['journey'].get('fair'), stake) > 0   # only then is the dẹp chiếu drawn for
            self.dice(Dice(draws=[.99, .50] if watched else [.50]))  # No raid; the same draw straddles the rates.
            before = s['journey']['wallet']
            s, result = self.act(s, 'fair_xd', side='chan', stake=stake)
            self.assertEqual(result['fair']['net'], stake if won else -stake)
            self.assertEqual(s['journey']['wallet'], before + result['fair']['net'])
            engine.validate_state(s)

    def test_large_stake_draw_boundary_survives_existing_streak_and_spam(self):
        j = dict(fair_balance={'xd': fh.STREAK})
        for n in range(40):
            p = fh.luck_p(j, None, 'xd', OPEN + n, stake=300001)
            self.assertEqual(p, .40)
            with mock.patch.object(fh, '_rng', Dice(draws=[.399999, .40])):
                self.assertTrue(fh._draw_luck(j, 'xd', p))
                self.assertFalse(fh._draw_luck(j, 'xd', p))

    def test_expired_event_retains_ordinary_rules(self):
        t = OPEN + golden.DURATION
        self.assertEqual(fh.luck_p({}, None, 'xd', t, stake=49_999), fh.BASES['xd'])
        self.assertEqual(fh.luck_p({}, None, 'xd', t, stake=1000000), min(fh.BASES['xd'], fh.BIG_WIN_P))
        self.assertEqual(fh.luck_p({}, None, 'xd', t, stake=50_000), min(fh.BASES['xd'], fh.BIG_WIN_P))

    def test_large_stake_seeded_distribution_is_40_percent(self):
        self.dice(random.Random(301001))
        j = {}
        wins = sum(fh._draw_luck(j, 'xd', fh.luck_p(j, None, 'xd', OPEN + n / 100, stake=1000000))
                   for n in range(20000))
        self.assertAlmostEqual(wins / 20000, .40, delta=.015)
