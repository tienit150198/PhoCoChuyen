"""Owner 07/10 ("mấy cái con số nhập hàng, mua vàng,.. đang phải bấm cộng mệt quá, cho nhập số nhé"): the number between
− and + is typed (public/js/qty-input.js). The box clamps on the phone, but the server stays the authority: a typed
number that is out of range, a fraction, a string or a bool is refused by the commands the boxes send, and the boxes
are drawn with the server's own limits."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from game import inventory, quay_business, vang, workplace_business
from game.engine import GameError, apply_action
from tests.helpers import Journey
from tests.test_bank import story

ROOT = Path(__file__).resolve().parents[1]
BAD = (0, -1, 2.5, '5', True, None, 10**9)


def src(path):
    return (ROOT / 'public' / 'js' / path).read_text(encoding='utf-8')


class TypedBox(unittest.TestCase):
    def test_the_shared_box_in_node(self):
        if not shutil.which('node'):
            self.skipTest('node not installed')
        out = subprocess.run(['node', '--test', str(ROOT / 'tests' / 'qty_input.mjs')], cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8', timeout=120)
        self.assertEqual(out.returncode, 0, out.stdout[-3000:] + out.stderr[-2000:])

    def test_boxes_use_the_server_limits(self):
        views, app, keep, quay, invest = src('v4/views.js'), src('app.js'), src('keep-ui.js'), src('v4/quay.js'), src('v4/invest.js')
        self.assertIn('max:60', views)                                   # inv_receive count 0..60
        self.assertRegex(views, r'Math\.min\(30,space\)')                # inv_order 1..30
        self.assertIn('Math.min(30,l.room)', views)                      # inv_cart set 0..30
        self.assertIn('min:1,max:12', app)                               # receive_stock 1..12
        self.assertIn(f'KEEP_MAX={workplace_business.KEEP_MAX}', keep)
        self.assertEqual(workplace_business.KEEP_MAX, quay_business.KEEP_MAX)
        self.assertIn(f'max:{quay_business.STOCK_MAX}', quay)
        self.assertIn('max=1e4', quay)                                   # wages 1..10 000 (game/quay.py)
        self.assertIn(f'max:{vang.MAX_PHAN}', invest)
        self.assertIn(f'max:{vang.MAX_PHAN}', src('v4/rui.js'))
        for f in ('keep-ui.js', 'v4/views.js', 'app.js', 'v4/invest.js', 'v4/rui.js', 'v4/quay.js', 'v4/lux.js', 'v4/marriage.js',
                  'v4/auction.js', 'careers/street_kit.js', 'careers/pet_shop.js', 'careers/milk_tea.js', 'careers/grocery.js',
                  'careers/pet_care.js', 'careers/air_kit.js'):
            with self.subTest(f=f):
                self.assertRegex(src(f), r'qtyBox\(', 'every stepper screen draws the typed box')
        # No stepper number left as plain text between − and + on the screens above.
        self.assertNotRegex(views + keep, r"'−'[^`]{0,80}<(b|output)[^>]*>\$\{(qty|n|l\.qty)\}")

    def test_order_and_cart_refuse_what_a_box_cannot_send(self):
        j = Journey('restaurant')
        for bad in BAD + (31,):
            with self.subTest(qty=bad), self.assertRaises(GameError):
                j.act('inv_order', item='noodle', qty=bad, supplier='partner', confirm=True)
        j.act('inv_order', item='noodle', qty=3, supplier='partner', confirm=True)
        self.assertEqual(j.c['ext']['inv']['orders'][-1]['qty'], 3)

    def test_gold_refuses_what_a_box_cannot_send(self):
        s = story(100000)
        for bad in BAD + (vang.MAX_PHAN + 1,):
            with self.subTest(phan=bad), self.assertRaises(GameError):
                apply_action(s, None, 'jr_vang_buy', {'phan': bad})
        s, _ = apply_action(s, None, 'jr_vang_buy', {'phan': 15})
        self.assertEqual(s['journey']['vang']['phan'], 15)
        for bad in (0, 2.5, '5', True, 16):
            with self.subTest(sell=bad), self.assertRaises(GameError):
                apply_action(s, None, 'jr_vang_sell', {'phan': bad})

    def test_integer_check_is_strict(self):
        from game.engine import integer
        for bad in (2.0, '3', True, None, float('nan')):
            with self.subTest(v=bad), self.assertRaises(GameError):
                integer(bad, 0, 10)
        self.assertEqual(integer(7, 0, 10), 7)
        self.assertTrue(re.search(r'type\(value\) is int', (ROOT / 'game' / 'engine.py').read_text(encoding='utf-8')))
        self.assertIn('e.integer(p.get(\'qty\'), 1, 30)', (ROOT / 'game' / 'inventory.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
