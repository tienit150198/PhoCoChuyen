"""Gentler new rounds, with saved rounds retaining their purchased rules."""
import copy
import json
import unittest

from game import fair_knife as kn
from game import fair as fh
from game.engine import GameError, public_state, validate_state
from tests.test_fair import Dice, FairBase, story
from tests.test_fair_knife import safe_taps


class KnifeSchedule(unittest.TestCase):
    def test_gentler_rotation_and_count_preserve_legacy_boards(self):
        for seed in (0, 12345, 2**31 - 1):
            for level in range(1, 11):
                for hot in range(4):
                    with self.subTest(seed=seed, level=level, hot=hot):
                        base = kn.schedule(seed, level, hot)
                        old = kn.schedule(seed, level, hot, 150)
                        new = kn.schedule(seed, level, hot, 135)
                        self.assertEqual(old['need'], (base['need'] * 3 + 1) // 2)
                        self.assertEqual(old['segs'], [[ms, v * 1.5, ramp] for ms, v, ramp in base['segs']])
                        self.assertEqual(new['need'], (base['need'] * 135 + 99) // 100)
                        self.assertLessEqual(new['need'], old['need'])
                        self.assertEqual(new['pre'], old['pre'])
                        self.assertEqual(new['th0'], old['th0'])
                        for a, b in zip(new['segs'], old['segs'], strict=True):
                            self.assertEqual((a[0], a[2]), (b[0], b[2]))
                            self.assertAlmostEqual(a[1], b[1] * .9)


class SavedRoundCompatibility(FairBase):
    def test_first_board_ten_throws_and_reload_partial_round(self):
        s, result = self.act(story(100), 'fair_kn_start', stake=10)
        self.assertEqual(result['fair']['run']['board']['need'], 9)   # 06/10: the softer 115% board
        self.assertEqual(s['journey']['fair_kn_skill']['difficulty'], 135)
        sc = fh._kn_sched(s['journey']['fair_kn']['run'], s['journey'])
        taps = safe_taps(sc, sc['need'])
        self.clock.t += taps[-1] / 1000
        s, partial = self.act(s, 'fair_kn_throw', lv=1, taps=taps[:8])
        self.assertEqual(partial['fair']['run']['stage'], 'play')
        s = json.loads(json.dumps(s))
        validate_state(s)
        self.dice(Dice(draws=[.99]))  # Clean throws win regardless of random draws.
        s, result = self.act(s, 'fair_kn_throw', lv=1, taps=taps)
        self.assertTrue(result['fair']['cleared'])
        s, result = self.act(s, 'fair_kn_stop')
        self.assertEqual(result['fair']['prize'], 11)
        self.assertEqual(s['journey']['wallet'], 101)

    def test_old_knife_keeps_current_board_then_switches_to_gentle_skill(self):
        for probability in (450, 600):
            with self.subTest(probability=probability):
                s, _ = self.act(story(100), 'fair_kn_start', stake=10)
                s['journey'].pop('fair_kn_skill')
                s['journey'].pop('fair_kn_soft')
                fh._set_chance(s['journey'], 'kn', s['journey']['fair_kn']['run'], probability / 1000)
                s['journey']['fair_chance']['kn'].update(p=probability, difficulty=150)
                s = json.loads(json.dumps(s))
                validate_state(s)
                board = public_state(s)['fair']['knife']['run']['board']
                self.assertEqual(board['need'], 11)
                self.dice(Dice(draws=[.99]))
                s, result = self.act(s, 'fair_kn_throw', lv=1, taps=list(range(0, 11 * 120, 120)))
                self.assertTrue(result['fair']['cleared'])
                s, result = self.act(s, 'fair_kn_next')
                self.assertEqual(result['fair']['run']['board']['need'], 9)
                self.assertFalse(result['fair']['run']['chance'])
                self.assertNotIn('kn', s['journey']['fair_chance'])
                self.assertEqual(s['journey']['fair_kn_skill']['difficulty'], 135)
                sc = fh._kn_sched(s['journey']['fair_kn']['run'], s['journey'])
                taps = safe_taps(sc, sc['need'])
                self.clock.t += taps[-1] / 1000
                s, result = self.act(s, 'fair_kn_throw', lv=2, taps=taps)
                self.assertTrue(result['fair']['cleared'])
                validate_state(s)

    def test_old_ring_keeps_its_locked_odds_on_reload(self):
        for draw, won in ((.449999, True), (.45, False)):
            with self.subTest(draw=draw):
                s, start = self.act(story(100), 'fair_ring_start')
                s['journey']['fair_chance']['ring']['p'] = 450
                s = json.loads(json.dumps(s))
                validate_state(s)
                self.dice(Dice(draws=[draw]))
                s, result = self.act(s, 'fair_ring_throw', id=start['fair']['round']['id'], taps=[0, 300, 600, 900, 1200])
                self.assertEqual(result['fair']['prize'] > 0, won)
                validate_state(s)

    def test_validator_accepts_old_and_new_rules_rejects_malformed_values(self):
        s, _ = self.act(story(100), 'fair_kn_start', stake=10)
        s['journey'].pop('fair_kn_skill')
        fh._set_chance(s['journey'], 'kn', s['journey']['fair_kn']['run'], .70)
        for p in (400, 450, 550, 600, 700):
            for difficulty in (135, 150):
                s['journey']['fair_chance']['kn'].update(p=p, difficulty=difficulty)
                validate_state(s)
        for key, value in (('p', 399), ('p', 701), ('p', True), ('difficulty', 136), ('difficulty', 149), ('difficulty', True)):
            bad = copy.deepcopy(s)
            bad['journey']['fair_chance']['kn'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(GameError):
                validate_state(bad)
