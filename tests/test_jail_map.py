"""Walkable holding camp (owner 09/10: "vô tù có map, di chuyển này kia được"): the camp plan
public/js/scenes/jail-place.js is checked with node (tests/jail_place.mjs): every công ích task of game/jail.py has its
own reachable corner, taps pick the right spot, and the player stays on screen on phones and desktops."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class JailMapTest(unittest.TestCase):
    def test_camp_plan(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'jail_place.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn('0 problems', out.stdout)

    def test_map_is_the_default_view(self):
        src = (ROOT / 'public/js/v4/jail.js').read_text(encoding='utf-8')
        self.assertIn("from './jail-map.js'", src)
        self.assertRegex(src, r'mapOn\s*[:=]')

    def test_walk_stays_client_side(self):
        # The walking position is never sent to the server: the map only calls the existing jail_* commands.
        src = (ROOT / 'public/js/v4/jail-map.js').read_text(encoding='utf-8')
        self.assertIsNone(re.search(r'\bfetch\(|/api/|command\(', src))


if __name__ == '__main__':
    unittest.main()
