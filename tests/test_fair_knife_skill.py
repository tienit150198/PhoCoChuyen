"""Knife wins follow visible collisions, never the chance-stall odds."""
import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from game import fair as fh, fair_knife as kn
from game.engine import validate_state, public_state, GameError
from tests.test_fair import Dice, FairBase, story
from tests.test_fair_knife import safe_taps, crash_tap


class ClientServerPhysics(unittest.TestCase):
    def test_same_collisions_at_all_levels_heat_and_wrap_boundaries(self):
        cases = []
        for seed in (0, 7, 12345, 2**31 - 1):
            for lv in range(1, kn.LEVELS + 1):
                for hot in range(kn.HEAT_MAX + 1):
                    sc = kn.schedule(seed, lv, hot, kn.SKILL_DIFFICULTY)
                    taps = safe_taps(sc, 3)
                    for attempt in (taps, taps + [crash_tap(sc, taps)]):
                        stuck, hit = kn.judge(sc, attempt)
                        cases.append(dict(board=kn.public_schedule(sc), taps=attempt, stuck=stuck, hit=hit))
        # Close misses must not become hits through rounding or angle wrapping.
        for angle in (0, 89.999, 180, 359.999):
            for separation in (kn.GAP - .000001, kn.GAP + .000001):
                sc = dict(need=1, pre=[(angle + separation) % 360], th0=90 - angle, segs=[[60000, 0, 0]])
                stuck, hit = kn.judge(sc, [0])
                cases.append(dict(board=sc, taps=[0], stuck=stuck, hit=hit))
        program = """
import {judge} from './public/js/v4/fair-knife.js';
let input=''; for await (const chunk of process.stdin) input+=chunk;
const data=JSON.parse(input);
process.stdout.write(JSON.stringify(data.cases.map(c=>judge(c.board,data.rules,c.taps))));
"""
        result = subprocess.run(['node', '--input-type=module', '-e', program],
                                cwd=Path(__file__).resolve().parents[1],
                                input=json.dumps(dict(cases=cases, rules=dict(impact=kn.IMPACT, fly=kn.FLY_MS, gap=kn.GAP))),
                                text=True, capture_output=True, check=True, timeout=30)
        actual = json.loads(result.stdout)
        self.assertEqual(len(actual), len(cases))
        for case, client in zip(cases, actual):
            with self.subTest(board=case['board'], taps=case['taps']):
                self.assertEqual(client['hit'], case['hit'])
                self.assertEqual(len(client['stuck']), len(case['stuck']))
                for a, b in zip(client['stuck'], case['stuck']):
                    self.assertLessEqual(kn.dist(a, b), .00501)


class KnifeSkill(FairBase):
    def complete(self, state, taps):
        self.clock.t += taps[-1] / 1000
        run = state['journey']['fair_kn']['run']
        return self.act(state, 'fair_kn_throw', lv=run['lv'], id=f'{run["sd"]}-{run["lv"]}', taps=taps)

    def test_new_board_has_real_obstacles_and_no_chance_flag(self):
        s, r = self.act(story(100), 'fair_kn_start', stake=10)
        board = r['fair']['run']['board']
        self.assertFalse(r['fair']['run']['chance'])
        self.assertFalse(board.get('chance', False))
        self.assertEqual(board['need'], 9)   # 06/10: the softer 115% board (was 10 at 135%)
        self.assertTrue(board['pre'])
        self.assertEqual(s['journey']['fair_kn_skill']['difficulty'], 135)
        self.assertNotIn('kn', s['journey'].get('fair_chance', {}))
        self.assertFalse(public_state(story())['fair']['knife']['chance'])
        validate_state(s)

    def test_clean_throws_win_even_with_a_losing_random_draw(self):
        s, _ = self.act(story(100), 'fair_kn_start', stake=10)
        sc = fh._kn_sched(s['journey']['fair_kn']['run'], s['journey'])
        taps = safe_taps(sc, sc['need'])
        self.dice(Dice(draws=[.999999]))
        s, r = self.complete(s, taps)
        self.assertTrue(r['fair'].get('cleared'))
        self.assertEqual(r['fair']['hit'], -1)
        self.assertEqual(r['fair']['stuck'], kn.judge(sc, taps)[0])
        s, r = self.act(s, 'fair_kn_stop')
        self.assertEqual(s['journey']['wallet'], 101)
        self.assertEqual(r['fair']['prize'], 11)

    def test_real_collision_loses_even_with_a_winning_random_draw(self):
        s, _ = self.act(story(100), 'fair_kn_start', stake=10)
        sc = fh._kn_sched(s['journey']['fair_kn']['run'], s['journey'])
        taps = safe_taps(sc, 2)
        taps.append(crash_tap(sc, taps))
        self.dice(Dice(draws=[0]))
        s, r = self.complete(s, taps)
        self.assertTrue(r['fair'].get('lost'))
        self.assertEqual(r['fair']['hit'], 2)
        self.assertEqual(s['journey']['wallet'], 90)

    def test_spam_and_profit_do_not_draw_a_win_probability(self):
        for net in (0, 6000):
            s = story(10000)
            s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(self.clock.t), net=net)
            s['journey']['fair_run'] = dict(g='dt', n=100, at=int(self.clock.t))
            with mock.patch.object(fh, 'luck_p', side_effect=AssertionError('Skill knife must not draw odds')):
                s, _ = self.act(s, 'fair_kn_start', stake=10)
                sc = fh._kn_sched(s['journey']['fair_kn']['run'], s['journey'])
                self.dice(Dice(draws=[.999999]))
                s, r = self.complete(s, safe_taps(sc, sc['need']))
            self.assertTrue(r['fair'].get('cleared'))
            self.assertNotIn('fair_run', s['journey'])

    def test_reload_and_next_level_keep_skill_rules(self):
        s, _ = self.act(story(100), 'fair_kn_start', stake=10)
        sc = fh._kn_sched(s['journey']['fair_kn']['run'], s['journey'])
        taps = safe_taps(sc, sc['need'])
        s, _ = self.complete(s, taps[:3])
        s = json.loads(json.dumps(s))
        validate_state(s)
        self.assertEqual(fh._kn_sched(s['journey']['fair_kn']['run'], s['journey'])['segs'], sc['segs'])
        s, r = self.complete(s, taps)
        self.assertTrue(r['fair']['cleared'])
        s, r = self.act(s, 'fair_kn_next')
        self.assertFalse(r['fair']['run']['chance'])
        self.assertEqual(r['fair']['run']['board']['need'], 9)
        validate_state(s)

    def test_in_progress_chance_level_finishes_without_invented_collision_then_switches(self):
        s, _ = self.act(story(100), 'fair_kn_start', stake=10)
        s['journey'].pop('fair_kn_skill', None)
        run = s['journey']['fair_kn']['run']
        fh._set_chance(s['journey'], 'kn', run, .45)
        s['journey']['fair_chance']['kn']['difficulty'] = 135
        n = fh._kn_sched(run, s['journey'])['need']
        self.dice(Dice(draws=[.999999]))
        s, r = self.complete(s, [i * kn.MIN_TAP for i in range(n)])
        self.assertTrue(r['fair'].get('cleared'), 'Already displayed chance-mode throws cannot be retroactively judged as collisions')
        s, r = self.act(s, 'fair_kn_next')
        self.assertFalse(r['fair']['run']['chance'])
        self.assertNotIn('kn', s['journey'].get('fair_chance', {}))
        self.assertTrue(r['fair']['run']['board']['pre'])
        validate_state(s)

    def test_invalid_skill_metadata_is_rejected(self):
        s, _ = self.act(story(100), 'fair_kn_start', stake=10)
        for bad in (None, {}, {'at': 0, 'seed': 0, 'difficulty': True},
                    {'at': 0, 'seed': 0, 'difficulty': 134},
                    {'at': -1, 'seed': 0, 'difficulty': 135}):
            s['journey']['fair_kn_skill'] = bad
            with self.subTest(bad=bad), self.assertRaises(GameError):
                validate_state(s)
