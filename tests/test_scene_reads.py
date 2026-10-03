"""The room backdrop cache (public/js/boba-world.js backdrop()): a new state repaints the room only when something
the paint read of the game changed (public/js/scenes/room-watch.js, checked with node in tests/scene_reads.mjs), and
the milk tea room keeps its moving bits (clouds past the window, fairy lights) out of it (BobaWorld.ambient), so it
is painted once instead of every ROOM_TICK. In the browser, ?deltacheck=1 on localhost also paints each kept
backdrop again and compares the pixels (globalThis.__mnlBackdrop)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'public' / 'js'


class SceneReadsTest(unittest.TestCase):
    def test_reads(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'scene_reads.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_wired_in(self):
        world = (JS / 'boba-world.js').read_text(encoding='utf-8')
        self.assertIn("import {watch,CHECK} from './scenes/room-watch.js'", world)
        backdrop = world.split(' backdrop(){', 1)[1].split('\n draw(){', 1)[0]
        key = re.search(r"const key=\[(.*?)\]\.join", backdrop).group(1)
        self.assertNotIn('this.rev', key)          # a new state alone does not repaint ...
        self.assertIn('this.reduced', key)         # ... but what the paint reads off the world itself does
        self.assertIn("watch(this,['c','state','game'])", backdrop)
        self.assertIn('L.reads?.same(this)', backdrop)
        self.assertIn('L.ambience', backdrop)

    def test_milk_tea_room_is_still(self):
        tea = (JS / 'scenes' / 'teabar.js').read_text(encoding='utf-8')
        rooms = tea.split('function landRoom(', 1)[1].split('/* ---', 1)[0]
        self.assertNotIn('w.time', rooms)          # world time only inside world.ambient(...)
        bar = tea.split('function windowBar(', 1)[1].split('\n/**', 1)[0]
        self.assertIn('world.ambient(', bar)
        self.assertEqual(bar.count('world.time'), 1)
        self.assertLess(bar.index('world.ambient('), bar.index('world.time'))


if __name__ == '__main__':
    unittest.main()
