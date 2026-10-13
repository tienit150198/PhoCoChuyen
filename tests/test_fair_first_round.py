"""Ordinary 14/10 draws: one 55% round, then decay; existing limits survive."""
import copy
import unittest
from unittest import mock

from game import fair as fh
from game.engine import validate_state
from tests.test_fair import OPEN, FairBase, story
from tests.test_fair_tighten import Dice
from tests.test_fair_scratch import Draws


class Rates(unittest.TestCase):
    def test_first_round_only_and_floor_boundaries(self):
        for game in ('xd', 'lt', 'xs'):
            with self.subTest(game=game):
                j = {}
                rates = [fh.luck_p(j, None, game, OPEN + i, stake=20) for i in range(14)]
                floor = .404 if game == 'xd' else .40
                self.assertEqual(rates[:10], [.55, .535, .52, .505, .49, .475, .46, .445, .43, .415])
                self.assertEqual(rates[10:], [floor] * 4)

    def test_ring_retains_ten_initial_rounds(self):
        j = {}
        rates = [fh.luck_p(j, None, 'ring', OPEN + i) for i in range(20)]
        self.assertEqual(rates[:10], [.503] * 10)
        self.assertEqual(rates[10:17], [.488, .473, .458, .443, .428, .413, .40])
        self.assertEqual(rates[17:], [.40] * 3)

    def test_saved_heat_survives_reload_and_resets_only_after_gap(self):
        for game in ('xd', 'lt', 'xs'):
            saved = {fh.COOL_KEY: {game: dict(n=3, at=int(OPEN), sw=0, st=20)}}
            self.assertEqual(fh.luck_p(copy.deepcopy(saved), None, game, OPEN + 600, stake=20), .505)
            fresh = copy.deepcopy(saved)
            self.assertEqual(fh.luck_p(fresh, None, game, OPEN + 601, stake=20), .55)
            self.assertEqual(fh.luck_p(fresh, None, game, OPEN + 602, stake=20), .535)

    def test_three_qualifying_switches_restore_one_initial_round(self):
        for game in ('xd', 'lt', 'xs'):
            j = {fh.COOL_KEY: {game: dict(n=9, at=int(OPEN), sw=0, st=100)}}
            for i in range(3):
                fh.luck_p(j, None, 'bc', OPEN + i, stake=24)
            self.assertEqual(j[fh.COOL_KEY][game]['sw'], 0)
            for i in range(2):
                fh.luck_p(j, None, 'bc', OPEN + 3 + i, stake=25)
            self.assertEqual(fh.luck_p(copy.deepcopy(j), None, game, OPEN + 5, stake=20), .415)
            fh.luck_p(j, None, 'bc', OPEN + 6, stake=25)
            self.assertEqual(fh.luck_p(j, None, game, OPEN + 7, stake=20), .55)
            self.assertEqual(fh.luck_p(j, None, game, OPEN + 8, stake=20), .535)

    def test_large_stake_and_streak_caps_still_apply(self):
        for game in ('xd', 'lt', 'xs'):
            self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=49_999), .55)
            for stake in (50_000, 300_000, 1_000_000):
                self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=stake), .40)
            for draw, won in ((.449999, True), (.45, False)):
                j = {'fair_balance': {game: 4}}
                p = fh.luck_p(j, None, game, OPEN, stake=20)
                with mock.patch.object(fh._rng, 'random', return_value=draw):
                    self.assertEqual(fh._draw_luck(j, game, p), won)


class Commands(FairBase):
    def test_real_commands_obey_each_of_first_four_cutoffs(self):
        for game in ('xd', 'lt', 'xs'):
            for n, p in enumerate((.55, .535, .52, .505), 1):
                for draw, won in ((p - .000001, True), (p, False)):
                    with self.subTest(game=game, round=n, draw=draw):
                        s = story(10_000)
                        if n > 1:
                            s['journey'][fh.COOL_KEY] = {game: dict(n=n - 1, at=int(self.clock.t), sw=0, st=20)}
                        self.dice(Draws(draws=[draw]) if game == 'lt' else Dice(draws=[draw]))
                        if game == 'xd':
                            s, result = self.act(s, 'fair_xd', side='chan', stake=20)
                            actual = result['fair']['net'] > 0
                        elif game == 'xs':
                            s, result = self.act(s, 'fair_xs', price=20)
                            actual = result['fair']['mult'] > 0  # refunds count as wins
                        else:
                            s, _ = self.act(s, 'fair_loto_buy', tier='lon', n=2)
                            view = fh.round_view(s['journey']['fair']['loto'])
                            actual = view['mine'] <= view['npc_done']
                        self.assertEqual(actual, won, (game, n, draw))
                        self.assertEqual(s['journey'][fh.COOL_KEY][game]['n'], n)
                        validate_state(s)
