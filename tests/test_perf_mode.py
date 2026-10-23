"""⚡ Light mode for slow phones (owner 23/10 "hiện tại lag lắm"): public/js/perf-mode.js is checked with node
(tests/perf-mode.mjs), and the scenes that read it keep doing so, so a later edit does not drop the slow-device path."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USERS = {
    'public/js/world.js': ('markLowEnd(', 'AMBIENT_SHARE'),
    'public/js/boba-world.js': ('ROOM_SHARE', 'lowEnd()'),
    'client/isometric/phaser-world.ts': ("'/js/perf-mode.js'", 'capFps('),
    'public/css/app.css': ('html[data-perf="low"]',),
}


class PerfModeTest(unittest.TestCase):
    def test_module(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'perf-mode.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_scenes_use_it(self):
        for path, markers in USERS.items():
            src = (ROOT / path).read_text(encoding='utf-8')
            for marker in markers:
                self.assertIn(marker, src, path)
        # the built bundle carries the frame watch too (scripts/build_isometric.mjs)
        self.assertIn('/js/perf-mode.js', (ROOT / 'public/js/isometric/phaser-world.js').read_text(encoding='utf-8'))
