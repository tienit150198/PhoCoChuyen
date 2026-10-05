"""🛵 Tự lái (public/js/careers/delivery_drive.js): the drawn town is rideable by its arrow, the tap flow stays wired."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game.careers import delivery as D

ROOT = Path(__file__).resolve().parents[1]


class Town(unittest.TestCase):
    def test_rideable_in_node(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'delivery_drive.mjs')], cwd=ROOT, input=json.dumps(D.NODES, ensure_ascii=False),
                             capture_output=True, text=True, encoding='utf-8', timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        self.assertIn('legs ridden by the arrow', out.stdout)

    def test_stops_fit_the_drawn_grid(self):
        # The street view draws a 7×5 grid of junctions; every stop must sit on it.
        for nid, n in D.NODES.items():
            self.assertTrue(0 <= n['x'] <= 6 and 0 <= n['y'] <= 4, nid)


class Wiring(unittest.TestCase):
    def test_touch_navigation_and_signal_regressions(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        for filename in ('delivery_controls.mjs', 'delivery_pointer_controls.mjs',
                         'delivery_input_lifecycle.mjs', 'delivery_navigation.mjs', 'delivery_signal_clock.mjs'):
            with self.subTest(filename=filename):
                out = subprocess.run([node, str(ROOT / 'tests' / filename)], cwd=ROOT,
                                     capture_output=True, text=True, encoding='utf-8', timeout=30)
                self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_drive_uses_the_tap_flow_commands(self):
        js = (ROOT / 'public' / 'js' / 'careers' / 'delivery.js').read_text(encoding='utf-8')
        drive = (ROOT / 'public' / 'js' / 'careers' / 'delivery_drive.js').read_text(encoding='utf-8')
        # Arriving on the street view sends the same commands as tapping (dl_plan, then dl_ride main) — no money on the client.
        self.assertIn("x.send('dl_plan',{route:want},{quiet:true})", js)
        self.assertIn("x.send('dl_ride',{way:'main'})", js)
        self.assertIn("act:'car:quick'", js)
        self.assertIn("MODE_KEY='mnl.dlDrive'", js)
        self.assertIn("import('./delivery_drive.js')", js)
        self.assertNotIn('x.send(', drive)
        self.assertNotIn('fetch(', drive)


if __name__ == '__main__':
    unittest.main()
