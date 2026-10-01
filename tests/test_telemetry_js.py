"""Client-error beacons (public/js/telemetry.js, public/js/boot.js): the stack each error carries and the errors
that are not the game's (in-app browsers, extensions), checked with node (tests/telemetry.mjs)."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TelemetryJsTest(unittest.TestCase):
    def test_stack_and_foreign(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'telemetry.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_same_injected_names_both_sides(self):
        from game import retention as rt
        js = (ROOT / 'public/js/telemetry.js').read_text(encoding='utf-8')
        names = js.split('const INJECTED=/')[1].split('/i;')[0].replace('\\.', '.').split('|')
        self.assertEqual(sorted(names), sorted(rt.FOREIGN_NAMES))


if __name__ == '__main__':
    unittest.main()
