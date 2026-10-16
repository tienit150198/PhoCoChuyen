"""Ordinary draws since 16/10 (owner: "tỷ lệ là 55 - 60% thôi"): no more one 55% round then decay (14/10); the round
draws today's band (.57 at net 0) less its pace; the old run counts are still kept, existing limits survive."""
import copy
import unittest
from unittest import mock

from game import fair as fh
from game.engine import validate_state
from tests.test_fair import OPEN, FairBase, story
from tests.test_fair_tighten import Dice
from tests.test_fair_scratch import Draws


class Rates(unittest.TestCase):
    def test_no_decay_round_by_round_only_the_pace(self):
        for game in ('xd', 'lt', 'xs'):
            with self.subTest(game=game):
                j = {}
                rates = [fh.luck_p(j, None, game, OPEN + i, stake=20) for i in range(20)]
                self.assertEqual(rates[:10], [.57] * 10)
                self.assertEqual(rates[10:15], [.52] * 5)
                self.assertEqual(rates[15:], [.45] * 5)
                j = {}
                rates = [fh.luck_p(j, None, game, OPEN + 6 * i, stake=20) for i in range(40)]   # 10 a minute
                self.assertEqual(rates, [.57] * 40)

    def test_ring_retains_ten_initial_rounds(self):
        j = {}
        rates = [fh.luck_p(j, None, 'ring', OPEN + i) for i in range(20)]
        self.assertEqual(rates[:10], [.503] * 10)
        self.assertEqual(rates[10:17], [.488, .473, .458, .443, .428, .413, .40])
        self.assertEqual(rates[17:], [.40] * 3)

    def test_saved_heat_is_kept_but_no_longer_lowers_the_draw(self):
        for game in ('xd', 'lt', 'xs'):
            saved = {fh.COOL_KEY: {game: dict(n=30, at=int(OPEN), sw=0, st=20)}}
            j = copy.deepcopy(saved)
            self.assertEqual(fh.luck_p(j, None, game, OPEN + 600, stake=20), .57)
            self.assertEqual(j[fh.COOL_KEY][game]['n'], 31)   # still counted (an older server reads it)
            fresh = copy.deepcopy(saved)
            self.assertEqual(fh.luck_p(fresh, None, game, OPEN + 601, stake=20), .57)
            self.assertEqual(fresh[fh.COOL_KEY][game]['n'], 1)   # past RUN_GAP: a new run, as before

    def test_three_qualifying_switches_still_clear_the_kept_counts(self):
        for game in ('xd', 'lt', 'xs'):
            j = {fh.COOL_KEY: {game: dict(n=9, at=int(OPEN), sw=0, st=100)}}
            for i in range(3):
                fh.luck_p(j, None, 'bc', OPEN + i, stake=24)
            self.assertEqual(j[fh.COOL_KEY][game]['sw'], 0)
            for i in range(2):
                fh.luck_p(j, None, 'bc', OPEN + 3 + i, stake=25)
            self.assertEqual(j[fh.COOL_KEY][game]['sw'], 2)
            self.assertEqual(fh.luck_p(copy.deepcopy(j), None, game, OPEN + 5, stake=20), .57)
            fh.luck_p(j, None, 'bc', OPEN + 6, stake=25)
            self.assertNotIn(game, j.get(fh.COOL_KEY, {}))
            self.assertEqual(fh.luck_p(j, None, game, OPEN + 7, stake=20), .57)

    def test_large_stake_and_streak_caps_still_apply(self):
        for game in ('xd', 'lt', 'xs'):
            self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=49_999), .57)
            for stake in (50_000, 300_000, 1_000_000):
                self.assertEqual(fh.luck_p({}, None, game, OPEN, stake=stake), .40)
            for draw, won in ((.449999, True), (.45, False)):
                for p in (.57, fh.P_BACK):
                    j = {'fair_balance': {game: 4}}
                    with mock.patch.object(fh._rng, 'random', return_value=draw):
                        self.assertEqual(fh._draw_luck(j, game, p), won)


class Commands(FairBase):
    def test_real_commands_obey_each_band_cutoff(self):
        for game in ('xd', 'lt', 'xs'):
            for net, p in ((0, .57), (-1000, .60), (40_000, .52), (100_000, .45)):
                for draw, won in ((p - .000001, True), (p, False)):
                    with self.subTest(game=game, net=net, draw=draw):
                        s = story(10_000)
                        fh._state(s['journey'], self.clock.t + 2)['net'] = net
                        self.dice(Draws(draws=[draw]) if game == 'lt' else Dice(draws=[draw]))
                        if game == 'xd':
                            s, result = self.act(s, 'fair_xd', side='chan', stake=20)
                            actual = result['fair']['net'] > 0
                        elif game == 'xs':
                            s, result = self.act(s, 'fair_xs', price=20)
                            actual = result['fair']['mult'] > 0
                        else:
                            s, _ = self.act(s, 'fair_loto_buy', tier='lon', n=2)
                            view = fh.round_view(s['journey']['fair']['loto'])
                            actual = view['mine'] <= view['npc_done']
                        self.assertEqual(actual, won, (game, net, draw))
                        self.assertEqual(s['journey'][fh.COOL_KEY][game]['n'], 1)
                        self.assertEqual(len(s['journey'][fh.PACE_KEY][game]), 1)
                        validate_state(s)
