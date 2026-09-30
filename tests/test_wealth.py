"""💰 Tiền của bạn (public/js/v4/wealth.js): the pure helpers checked with node (tests/wealth.mjs), the
public state fields they read, and the places they are wired into."""
import shutil
import subprocess
import unittest
from pathlib import Path

from game import whats_new as wn
from game.engine import public_state
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]


class WealthTest(unittest.TestCase):
    def test_helpers(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'wealth.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_public_state_has_what_the_sheet_reads(self):
        j = Journey('florist')
        s = j.state
        s['journey']['story'] = True
        v = public_state(s)
        J = v['journey']
        self.assertIsInstance(J['wallet'], int)
        place = J['places']['florist']
        for k in ('fund', 'withdraw_max', 'employed', 'paused'):
            self.assertIn(k, place)
        self.assertEqual(place['fund'], s['careers']['florist']['money'])
        self.assertIn('open', J['bank'])
        self.assertIn('married', J['home'])
        self.assertIn('own', J['home'])

    def test_wired_in(self):
        app = (ROOT / 'public/js/app.js').read_text(encoding='utf-8')
        self.assertIn("from './v4/wealth.js'", app)
        self.assertIn('hudChipsHTML(hudMoney(', app)
        self.assertIn("case'money':openSheet('money')", app)
        self.assertIn("tile('money','👛'", app, 'the status sheet wallet tile opens the money sheet')
        journey = (ROOT / 'public/js/v4/journey.js').read_text(encoding='utf-8')
        self.assertIn('class="jr-stat ${J.debt?\'bad\':\'\'}" data-action="money"', journey)
        self.assertIn('.wl-row', (ROOT / 'public/css/money.css').read_text(encoding='utf-8'))
        self.assertIn('.hud-chip', (ROOT / 'public/css/app.css').read_text(encoding='utf-8'))

    def test_whats_new_line(self):
        items = [it for e in wn.ENTRIES if e['version'] == '0.9.8' for it in e['items']]
        line = next(it for it in items if it['emoji'] == '💰')
        self.assertEqual(line['text'], 'Bấm vào tiền trên cùng để xem hết: ví, quỹ từng nơi làm, ngân hàng, nhà.')
        self.assertEqual(line.get('go'), {'action': 'money'})


if __name__ == '__main__':
    unittest.main()
