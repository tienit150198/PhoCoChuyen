"""Stop-on-tap meters on a slow phone and a busy server (player reports: the clothes shop's sewing machine "canh tới
mức xanh nhưng tới mức đỏ nó mới dừng"; feedback #100, the pet bath and the milk-tea sealer "bấm dừng rồi nó vẫn
cứ chạy lố"). The clocks are checked with node (tests/meter_clock.mjs); the grading side is tests/test_tap_stop.py;
the whole thing on a throttled phone is scripts/browser_tap_stop.py. Here: that node test, and the wiring a later
edit must not drop."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
read = lambda rel: (ROOT / rel).read_text(encoding='utf-8')


class MeterLagTest(unittest.TestCase):
    def test_clocks(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'meter_clock.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_cues_follow_the_bars_frame_by_frame(self):
        js = read('public/js/v4/careers.js')
        # While a bar glides the meters run on every frame (their colour / words / stop controls keep up).
        self.assertIn('if(sliding.size&&!raf&&envOf)raf=requestAnimationFrame(frameDraw);', js)
        self.assertIn('envOf=getEnv;', js)
        # A stop the workbench turns down at its moment: answered on the page, the bars run on.
        self.assertIn('if(stop.early){early={el,why:stop.early};return;}', js)
        self.assertIn('e.stopImmediatePropagation();getEnv()?.toast?.(k.why);', js)

    def test_sewing_machine_wiring(self):
        js = read('public/js/careers/clothing.js')
        self.assertIn("tapStop:(op,p,at,x)=>{", js)
        self.assertIn("{early:'Kim chưa tới vạch, đạp thêm chút nữa rồi dừng.'}", js)
        py = read('game/careers/clothing.py')
        self.assertIn('lo, hi = sew_zone(t)', py)
        self.assertIn("zone=list(sew_zone(t))", py)

    def test_page_clock(self):
        api = read('public/js/api.js')
        self.assertIn('this.clockOffset=clockSample(this.clock,sent,got,data.server_time,data.server_recv);', api)
        self.assertLess(api.index('const got=early?'), api.index('data=await response.json()'))   # before the parse
        self.assertIn('B.got=Date.now();', read('public/js/boot.js'))
        self.assertIn('server_recv=round(', read('server.py'))

    def test_hidden_room_does_not_repaint_under_a_sheet(self):
        js = read('public/js/v4/dayclock.js')
        self.assertIn('now=performance.now()/1000', js)
        self.assertIn('w.covered?.()', js)


if __name__ == '__main__':
    unittest.main()
