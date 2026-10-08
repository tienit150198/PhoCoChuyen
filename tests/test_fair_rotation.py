"""Half-hour fair rotation, stake pricing and locked rounds."""
import json
import unittest
from unittest import mock

from game import fair as fh, fair_scratch as xs
from game.engine import validate_state
from tests.test_fair import OPEN, Dice, FairBase, story
from tests.test_fair_scratch import Draws


class Rotation(unittest.TestCase):
    def test_legacy_rotation_does_not_change_even_odds(self):
        games = ('lt', 'bc', 'xd', 'xs', 'ring')
        start = int(OPEN // 1800) * 1800
        picked = []
        for i in range(10):
            t = start + i * 1800
            selected = fh.featured_game(t)
            picked.append(selected)
            self.assertIn(selected, games)
            self.assertEqual(fh.featured_game(t + 1799.999), selected)
            self.assertNotEqual(fh.featured_game(t + 1800), selected)
            self.assertTrue(all(fh.chance_rate(g, t) == fh.BASES.get(g, fh.LUCK_BASE) for g in games))
        self.assertEqual(set(picked[:5]), set(games))
        self.assertEqual(picked[:5], picked[5:])

    def test_price_endpoints_and_monotonic_intermediate_stakes(self):
        for game, minimum in [('bc', 1), ('xd', 10), ('lt', 2), ('xs', 2)]:
            rate = fh.chance_rate(game, OPEN)   # 06/10: one rate at every stake and net
            for selected, high, low in [(game, rate, rate), ('ring', rate, rate)]:
                with self.subTest(game=game, selected=selected), mock.patch.object(fh, 'featured_game', return_value=selected):
                    rates = [fh.chance_rate(game, OPEN, stake) for stake in range(minimum, 501)]
                    self.assertAlmostEqual(rates[0], high)
                    self.assertAlmostEqual(rates[-1], low)
                    self.assertEqual(rates, sorted(rates, reverse=True))
                    self.assertEqual(rates[1], high)
                    for net in (2000, 3500, 5000, 100000):
                        self.assertTrue(all(low <= fh.chance_rate(game, OPEN, stake, net) <= rate
                                            for stake, rate in zip(range(minimum, 501), rates)))

    def test_repeat_floor_never_increases_an_already_lower_rate(self):
        x, low = fh.XD_BASE, fh.XD_FLOOR   # 07/10: a long run of xóc đĩa cools to its floor (40% won rounds)
        for selected, stake, base, floor in [('xd', 10, x, low), ('xd', 500, x, low),
                                              ('ring', 10, x, low), ('ring', 500, x, low)]:
            with self.subTest(selected=selected, stake=stake), mock.patch.object(fh, 'featured_game', return_value=selected):
                j = {}
                rates = [fh.luck_p(j, None, 'xd', OPEN + i, stake=stake) for i in range(80)]
                self.assertEqual(rates[:10], [base] * 10)
                self.assertAlmostEqual(rates[-1], floor)
                self.assertEqual(rates, sorted(rates, reverse=True))

    def test_scratch_return_is_below_cost_for_most_tiers_even_when_boosted(self):
        mean = sum(m * w for m, w in xs.PRIZES) / sum(w for _, w in xs.PRIZES)
        with mock.patch.object(fh, 'featured_game', return_value='xs'):
            returns = [fh.chance_rate('xs', OPEN, p) * mean for p in xs.TIERS]
        # Owner 08/10 (50% of tickets win, a won one pays 1.80× on average): every tier returns 90% of what it costs.
        self.assertAlmostEqual(returns[0], fh.BASES['xs'] * 1.801)
        self.assertTrue(all(abs(r - returns[0]) < 1e-9 for r in returns))
        self.assertLess(returns[0], .91)


class RotationCommands(FairBase):
    def test_ticket_price_reaches_actual_draw(self):
        for selected in ('xs','ring'):
            with mock.patch.object(fh,'featured_game',return_value=selected):
                for price in (2,500):
                    for draw,win in ((fh.BASES['xs']-.001,True),(fh.BASES['xs'],False)):
                        self.dice(Draws([draw]))
                        _,result=self.act(story(1000),'fair_xs',price=price)
                        self.assertEqual(result['fair']['prize']>0,win)

    def test_total_bets_and_cards_set_the_rate(self):
        for command, args, game, stake in [
            ('fair_bc', dict(bets={'cua': 150, 'ca': 150}), 'bc', 300),
            ('fair_xd', dict(side='chan', stake=500), 'xd', 500),
            ('fair_loto_buy', dict(tier='tram', n=3), 'lt', 300),   # no side bets since 08/10 (SIDE_OPEN)
        ]:
            with self.subTest(command=command), mock.patch.object(fh, 'luck_p', wraps=fh.luck_p) as odds:
                self.dice(Dice(draws=[.9, .9]))
                self.act(story(1000), command, **args)
                self.assertEqual(odds.call_args.args[2], game)
                self.assertEqual(odds.call_args.kwargs['stake'], stake)

    def test_ring_keeps_purchase_odds_across_rotation_boundary(self):
        start = int(OPEN // 1800) * 1800
        while fh.featured_game(start) != 'ring':
            start += 1800
        self.clock.t = start + 1795
        s, result = self.act(story(100), 'fair_ring_start')
        self.assertEqual(s['journey']['fair_chance']['ring']['p'], round(fh.LUCK_BASE * 1000))
        s = json.loads(json.dumps(s))
        self.clock.t = start + 1801
        self.dice(Dice(draws=[fh.LUCK_BASE - .01]))
        s, result = self.act(s, 'fair_ring_throw', id=result['fair']['round']['id'], taps=[0, 300, 600, 900, 1200])
        self.assertGreater(result['fair']['prize'], 0)
        validate_state(s)

    def test_skill_games_do_not_draw_odds(self):
        with mock.patch.object(fh, 'luck_p', side_effect=AssertionError('Skill must not draw chance')):
            self.act(story(100), 'fair_kn_start', stake=10)
            self.act(story(100), 'fair_oaq_start', lv='kho')
