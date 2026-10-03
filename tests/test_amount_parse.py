"""Money boxes of the accounting screens (player reports 03/10: no minus on a phone pad, no "6+4", no "10 triệu"):
the shared parser public/js/v4/amount-parse.js is checked with node (tests/amount_parse.mjs), and the boxes that use it
stay text boxes with the full keyboard, so a later edit does not bring back type="number"."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOXES = {
    'public/js/v4/accounting-school.js': 'amountAttrs(',
    'public/js/careers/corp_accounting.js': 'amountAttrs(',
    'public/js/careers/group_accounting.js': 'amountAttrs(',
    'public/js/careers/tax_payroll.js': 'amountAttrs(',
}


class AmountParseTest(unittest.TestCase):
    def test_parser(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'amount_parse.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)

    def test_accounting_boxes_take_text(self):
        for path, marker in BOXES.items():
            src = (ROOT / path).read_text(encoding='utf-8')
            self.assertIn("amount-parse.js'", src, path)
            self.assertIn(marker, src, path)
            self.assertNotRegex(src, r'type="number"', path)
            self.assertIsNone(re.search(r'inputmode="(numeric|decimal)"[^>]*data-amount|data-amount[^>]*inputmode="(numeric|decimal)"', src), path)

    def test_no_eval(self):
        src = (ROOT / 'public/js/v4/amount-parse.js').read_text(encoding='utf-8')
        self.assertNotRegex(src, r'\beval\(|new Function|Function\(')

    def test_note_style_is_global(self):
        css = (ROOT / 'public/css/app.css').read_text(encoding='utf-8')
        self.assertIn('.amt-note', css)


if __name__ == '__main__':
    unittest.main()
