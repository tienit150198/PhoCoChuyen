"""🏠 The house screen's inventory (tests/home_items.mjs) and the scroll fixes for the home and work sheets
(tests/home_scroll.mjs: rails keep their scroll through a redraw, redraws wait for a fling), run in Node."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class HomeUiJs(unittest.TestCase):
    def run_mjs(self, name):
        out = subprocess.run([shutil.which('node'), str(ROOT / 'tests' / name)], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr or out.stdout)
        return out.stdout

    def test_inventory_lists_everything_owned(self):
        self.assertIn('Home items', self.run_mjs('home_items.mjs'))

    def test_rails_and_lists_keep_their_scroll(self):
        self.assertIn('Home scroll', self.run_mjs('home_scroll.mjs'))


if __name__ == '__main__':
    unittest.main()
