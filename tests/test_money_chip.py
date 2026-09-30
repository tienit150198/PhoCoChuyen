"""The 💰 money chip (public/js/v4/money.js): pure helpers checked with node (tests/money_chip.mjs),
and the places it is wired into, so a later edit does not drop it."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MoneyChipTest(unittest.TestCase):
    def test_helpers(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'money_chip.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_wired_in(self):
        app = (ROOT / 'public/js/app.js').read_text(encoding='utf-8')
        self.assertIn("from './v4/money.js'", app)
        self.assertIn('moneyBoot(', app)
        self.assertIn('confirmMoney(dialogBalances(', app)
        # Every sheet where the fund is spent is in the scope list.
        for view in ('job', 'inventory', 'prepare', 'operations', 'social', 'decor', 'people', 'incident'):
            self.assertIn(f"'{view}'", app.split('const MONEY_FUND=')[1].split('\n')[0], view)
        self.assertTrue((ROOT / 'public/css/money.css').exists())
        money = (ROOT / 'public/js/v4/money.js').read_text(encoding='utf-8')
        self.assertIn("asset('/css/money.css')", money)


if __name__ == '__main__':
    unittest.main()
