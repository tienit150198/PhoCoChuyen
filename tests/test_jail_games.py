"""🚔 The công ích mini-games (public/js/v4/jail.js, its pure step()) against the server's puzzles and checks
(game/jail.py puzzle(), _right()): for every one of the 14 tasks, on several sentences and days, the right taps
finish the game with an answer the server takes, a wrong tap is refused with words, and every task asks for enough
taps to fill its minimum time (TASK_MIN_S) with real work. Runs tests/jail_games.mjs with node."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import jail as jl

ROOT = Path(__file__).resolve().parents[1]


class JailGames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not installed')
        cls.cases = [dict(task=t, pz=jl.puzzle(sid, day, t, old), old=old) for t in jl.TASKS for sid in ('abc123', 'f00d42', '9e9e01')
                     for day in (1, 2, 5) for old in ((False, True) if t in jl.OLD_TASK_IDS else (False,))]
        out = subprocess.run([node, str(ROOT / 'tests' / 'jail_games.mjs')], input=json.dumps(cls.cases), cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8', timeout=120)
        assert out.returncode == 0, out.stderr + out.stdout
        cls.results = json.loads(out.stdout)

    def test_every_game_is_played_through(self):
        self.assertEqual(len(self.results), len(self.cases))
        self.assertEqual({r['task'] for r in self.results}, set(jl.TASKS))
        for case, r in zip(self.cases, self.results):
            with self.subTest(task=r['task'], pz=case['pz']):
                self.assertEqual(r['problems'], [])
                self.assertTrue(r['done'])
                self.assertTrue(jl._right(r['task'], case['pz'], r['ans']), r['ans'])   # the server takes it

    def test_wrong_taps_are_refused_with_words(self):
        said = {r['task'] for r in self.results if r['refused']}
        self.assertEqual(said, set(jl.TASKS) - {'sweep', 'rice', 'paint', 'ledger'})

    def test_enough_work_for_the_minimum_time(self):
        for case, r in zip(self.cases, self.results):
            if case['old']:   # a day adopted from an older server keeps its small puzzles
                continue
            with self.subTest(task=r['task']):
                self.assertGreaterEqual(r['moves'], 9, 'a task is a minute or two of taps, not three')


if __name__ == '__main__':
    unittest.main()
