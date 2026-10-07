"""📱 Old iPhones (iOS 15, 16.0–16.3) must open the game (07/10 hotfix): every file under public/ parses there
(scripts/check_old_safari.mjs), the lookbehind-free splitters give the same pieces as before and boot.js's polyfills
work (tests/old_safari_regex.mjs). Run in Node."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class OldSafari(unittest.TestCase):
    def run_node(self, *args):
        out = subprocess.run([shutil.which('node'), *map(str, args)], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr or out.stdout)
        return out.stdout

    def test_every_browser_file_loads_on_safari_15(self):
        self.assertIn('OK for Safari 15.0', self.run_node(ROOT / 'scripts' / 'check_old_safari.mjs'))

    def test_splitters_match_the_old_lookbehind_and_polyfills_work(self):
        out = self.run_node(ROOT / 'tests' / 'old_safari_regex.mjs')
        self.assertIn('split exactly as before', out)
        self.assertIn('(boot polyfills): ok', out)

    def test_toast_lines_unchanged(self):
        self.assertIn('toast_lines.mjs (head): ok', self.run_node(ROOT / 'tests' / 'toast_lines.mjs'))


if __name__ == '__main__':
    unittest.main()
