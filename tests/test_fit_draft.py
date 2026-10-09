"""The stock room's "🛒 Gộp N món" draft (public/js/v4/restock.js fitDraft, views.js fillGo): checked with node
(tests/fit_draft.mjs), then the draft it builds for a fresh nail shop (20 items low, 320 xu) is put through the
real server: inv_cart takes it whole and inv_order_cart places it (owner report: the step showed an error)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import inventory as I
from tests.helpers import Journey
from tests.test_inventory_flow import public_inv

ROOT = Path(__file__).resolve().parents[1]


class FitDraftTest(unittest.TestCase):
    def setUp(self):
        self.node = shutil.which('node')
        if not self.node:
            self.skipTest('node not installed')

    def run_node(self, *args):
        out = subprocess.run([self.node, str(ROOT / 'tests' / 'fit_draft.mjs'), *args], cwd=ROOT, capture_output=True,
                             text=True, timeout=60, encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        return out.stdout

    def test_helpers(self):
        self.assertIn('fit_draft ok', self.run_node())

    def test_nail_draft_is_placed(self):
        j = Journey('nail')
        inv = public_inv(j)
        sup = next(s for s in inv['suppliers'] if s['id'] == 'partner')
        by = {i['id']: i for i in I.catalogue('nail')}
        low = [i for i in by if inv['stock'].get(i, 0) + inv['arriving'].get(i, 0) <= max(2, inv['capacity'] * 8 // 100)]
        self.assertGreaterEqual(len(low), inv['cart_lines'])  # 20 low, 20 lines a draft since 1.7.16
        lines = [dict(id=i, cost=by[i]['cost'], q=min(inv['room'][i], 10)) for i in low]
        draft = json.loads(self.run_node(json.dumps(dict(lines=lines, sup=sup, money=j.c['money'], free=inv['cart_lines'], have=0, line_cap=inv['line_cap']))))
        self.assertEqual(len(draft), inv['cart_lines'])
        j.act('inv_cart', supplier='partner', op='add', lines=[dict(item=l['id'], qty=l['q']) for l in draft], fit=True)
        k = next(k for k in public_inv(j)['carts'] if k['supplier'] == 'partner')
        self.assertEqual((k['n'], k['short'], k['below_min']), (len(draft), 0, 0))
        money = j.c['money']
        j.act('inv_order_cart', supplier='partner', confirm=True)
        self.assertEqual(j.c['money'], money - k['total'])
        self.assertGreaterEqual(j.c['money'], 0)


if __name__ == '__main__':
    unittest.main()
