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
        self.assertIn('max:Math.max(60,Number(o.qty)||0)', views)        # inv_receive count: the crate's own line (#277)
        self.assertIn('lineMax=Number(c.inventory?.line_cap)||30', views)  # inv_order 1..LINE_MAX (inventory.public line_cap)
        self.assertRegex(views, r'Math\.min\(lineMax,space\)')
        self.assertIn('Math.min(lineMax,l.room)', views)                 # inv_cart set 0..LINE_MAX
        self.assertEqual(inventory.LINE_MAX, 80)
        self.assertIn('min:1,max:12', app)                               # receive_stock 1..12
        self.assertIn(f'KEEP_MAX={workplace_business.KEEP_MAX}', keep)
        self.assertEqual(workplace_business.KEEP_MAX, quay_business.KEEP_MAX)
        self.assertIn(f'max:{quay_business.STOCK_MAX}', quay)
        self.assertIn('max=1e4', quay)                                   # wages 1..10 000 (game/quay.py)
        self.assertIn(f'MAX_PHAN={vang.MAX_PHAN};', invest)              # gold: typed chỉ + odd phân (fb08)
        self.assertIn('max:MAX_PHAN/10', invest)
        self.assertIn('min:0,max:9', invest)
        self.assertIn(f'max:{vang.MAX_PHAN}', src('v4/rui.js'))
        for f in ('keep-ui.js', 'v4/views.js', 'app.js', 'v4/invest.js', 'v4/rui.js', 'v4/quay.js', 'v4/lux.js', 'v4/marriage.js',
                  'v4/auction.js', 'careers/street_kit.js', 'careers/pet_shop.js', 'careers/milk_tea.js', 'careers/grocery.js',
                  'careers/pet_care.js', 'careers/air_kit.js', 'careers/mother_baby.js', 'careers/tra_da.js',
                  'careers/farm.js'):
            with self.subTest(f=f):
                self.assertRegex(src(f), r'qtyBox\(', 'every stepper screen draws the typed box')
        # No stepper number left as plain text between − and + on the screens above.
        self.assertNotRegex(views + keep, r"'−'[^`]{0,80}<(b|output)[^>]*>\$\{(qty|n|l\.qty)\}")

    def test_fb08_boxes(self):
        # Player feedback 07–08/10: restock 10 at once, gold by the chỉ, a calm colour for what is already in the cart.
        from game.careers import mother_baby, tra_da
        mb, td, farm, lux, views, social = (src('careers/mother_baby.js'), src('careers/tra_da.js'), src('careers/farm.js'),
                                            src('v4/lux.js'), src('v4/views.js'), src('v4/social.js'))
        self.assertTrue('pr.diaper_cap??12' in mb, 'mother_baby: the box stops at what the shelf takes')
        self.assertEqual(mother_baby.DIAPER['cap'], 12)
        self.assertEqual(mother_baby.ORDER_MAX, max(mother_baby.DIAPER['cap'], mother_baby.FORMULA['cap']))
        self.assertTrue('max:pm' in td, 'max:pm')
        self.assertEqual(tra_da.ICE_PLAN_MAX, 6)
        self.assertTrue('data-action="car:faSellQty"' in farm, 'data-action="car:faSellQty"')
        self.assertTrue('min:g.min,max:g.max,money:true' in lux, 'lux library: any amount in range')
        self.assertTrue("carted?'carted'" in views, 'Kho: a carted bin is not red')
        self.assertTrue('Đã thêm · ${carted}' in views, 'Đã thêm · ${carted}')
        self.assertFalse(re.search(r'type="number"(?![^>]*inputmode)', social))   # every number box opens the number pad

    def test_ice_plan_refuses_what_a_box_cannot_send(self):
        j = Journey('tra_da')
        for bad in (-1, 2.5, '5', True, None, 7):                       # 0 is "no ice tomorrow"
            with self.subTest(n=bad), self.assertRaises(GameError):
                j.act('td_ice_plan', n=bad)
        j.act('td_ice_plan', n=6)
        j.act('td_ice_plan', n=0)

    def test_order_and_cart_refuse_what_a_box_cannot_send(self):
        j = Journey('restaurant')
        for bad in BAD + (inventory.LINE_MAX + 1,):
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
        self.assertIn('e.integer(p.get(\'qty\'), 1, LINE_MAX)', (ROOT / 'game' / 'inventory.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
