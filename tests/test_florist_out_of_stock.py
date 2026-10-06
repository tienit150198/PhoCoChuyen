"""Backlog #9 (06/10): fl_card / fl_banner were refused 89× at 0 stock because their buttons stayed on. They are
now disabled with the reason and a restock tap (tests/florist_out_of_stock.mjs renders the real florist.js)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game.content import public_content
from game.engine import public_state
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]


class FloristOutOfStock(unittest.TestCase):
    def test_card_and_banner_buttons_follow_stock(self):
        if not shutil.which('node'):
            self.skipTest('node not installed')
        j = Journey('florist')
        j.act('ask')
        payload = dict(state=public_state(j.state), content=public_content())
        proc = subprocess.run(['node', str(ROOT / 'tests' / 'florist_out_of_stock.mjs')], cwd=ROOT, input=json.dumps(payload),
                              text=True, encoding='utf-8', capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr[-3000:])
        self.assertIn('florist out-of-stock checks passed', proc.stdout)


if __name__ == '__main__':
    unittest.main()
