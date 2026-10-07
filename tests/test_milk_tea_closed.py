"""Milk tea while the shop is closed (07/10): after end_day the unfinished cup stays and the counter still opens, but the
server refuses every brewing step. The counter then shows no pick ahead, dims its brewing controls with "Mở ca trước"
and its main button opens the shift (tests/milk_tea_closed.mjs)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game.content import public_content
from game.engine import GameError, public_state
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]


class MilkTeaClosed(unittest.TestCase):
    def test_closed_counter(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        opened = public_state(j.state)
        j.act('end_day', carry_event=True)
        self.assertFalse(j.c['open'])
        self.assertTrue(any(t['id'] == tid and t['status'] not in ('completed', 'cancelled', 'referred') for t in j.c['tasks']))
        for op, p in (('tea_cup', dict(size='M')), ('tea_ice', dict(level='normal')), ('tea_add', dict(item='black'))):
            with self.assertRaises(GameError) as err:
                j.act(op, task=tid, **p)
            self.assertIn('Mở cửa quán', str(err.exception))
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        payload = dict(open=opened, closed=public_state(j.state), content=public_content())
        out = subprocess.run([node, str(ROOT / 'tests' / 'milk_tea_closed.mjs')], input=json.dumps(payload, ensure_ascii=False), cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
