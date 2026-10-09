"""Bigger shelves (player #277, owner 09/10: "nâng tổng kho ... lên 60 hoặc 80", "đặt tối đa 30 lên 60-80").

Shipped in two releases so a rollback never strands a save: the first (STEP1) only ACCEPTS saves holding up to
SAVE_STOCK units of an item and order or draft lines of up to SAVE_LINE units (and receives such a crate), while
its own orders kept 30 a line and the old shelves; the second raises the limits themselves: every stocked
career's shelf holds at least 80 of an item and one line takes up to 80 (big crates count by the tray, views.js).
Saves written with the new limits validate on STEP1 and, as expected, not on 1.9.28: hence two steps.
"""
import copy
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import inventory as I
from game.careers import PLUGINS
from game.engine import GameError, validate_state
from tests.helpers import Journey
from tests.test_inventory_cart import fresh, add
from tests.test_inventory_flow import empty, public_inv, set_money, wait_until_ready

ROOT = Path(__file__).resolve().parents[1]
STEP1 = '4425b819'      # step 1: accepts these saves (the release this one may be rolled back to)
BEFORE = 'a9777863'     # 1.9.28: refuses them (stock over its shelves), which is why there are two steps
OLD = {  # the shelves before player #277
    'cafe_bakery': 40, 'clothing': 30, 'com': 120, 'delivery': 40, 'drain': 20, 'farm': 40, 'florist': 40,
    'fruit': 40, 'garbage': 30, 'giupviec': 40, 'grocery': 60, 'homestay': 40, 'ice_cream': 80, 'library': 40,
    'nail': 80, 'pet_care': 40, 'pet_shop': 40, 'pho': 80, 'photobooth': 80, 'repair': 40, 'restaurant': 40,
    'salon': 40, 'tra_da': 40, 'zpop': 80}


def stocked():
    return sorted(cid for cid, mod in PLUGINS.items() if mod.SPEC.get('inventory'))


def big_order(j, item, qty, short=0):
    """An order line as big as a save may hold: a real order, scaled up."""
    oid = j.act('inv_order', item=item, qty=1, supplier='express', confirm=True)['eta']['order']
    o = next(o for o in j.c['ext']['inv']['orders'] if o['id'] == oid)
    o.update(qty=qty, actual=qty - short)
    return oid


def fill(j, item, qty):
    """`qty` units of `item` on the shelf, one lot."""
    x = j.c['ext']['inv']
    x['lots'] = [l for l in x['lots'] if l['item'] != item]
    x['seq'] += 1
    x['lots'].append(dict(id=f'lot-{x["seq"]}', item=item, qty=qty, unit_cost=3, expires=j.c['day'] + 5,
                          received=j.c['day'], supplier='partner'))


class SaveLimits(unittest.TestCase):
    def test_saves_hold_bigger_stock_orders_and_drafts(self):
        self.assertGreaterEqual(I.SAVE_STOCK, 80)
        self.assertGreaterEqual(I.SAVE_LINE, 80)
        for career in ('restaurant', 'clothing', 'grocery', 'garbage', 'drain', 'com'):
            self.assertGreaterEqual(I.stock_limit(career), max(80, I.capacity(career)), career)
        j = fresh()
        fill(j, 'noodle', I.stock_limit('restaurant'))
        big_order(j, 'egg', I.SAVE_LINE, short=2)
        add(j, 'partner', 'beef', 5)
        j.c['ext']['inv']['cart']['partner']['lines'][0]['qty'] = I.SAVE_LINE
        validate_state(j.state)
        for bad in ('stock', 'order', 'draft'):
            s = copy.deepcopy(j.state)
            x = s['careers']['restaurant']['ext']['inv']
            if bad == 'stock':
                next(l for l in x['lots'] if l['item'] == 'noodle')['qty'] += 1
            elif bad == 'order':
                next(o for o in x['orders'] if o['item'] == 'egg')['qty'] = I.SAVE_LINE + 1
            else:
                x['cart']['partner']['lines'][0]['qty'] = I.SAVE_LINE + 1
            with self.assertRaises(GameError, msg=bad):
                validate_state(s)

    def test_a_whole_big_lot_wasted_is_a_valid_row(self):
        j = fresh()
        j.c['life']['waste'].append(dict(day=j.c['day'], item='noodle', qty=120, value=120 * 310, reason='Bỏ lô không đạt'))
        validate_state(j.state)

    def test_orders_keep_this_release_line_max(self):
        j = fresh(money=50000)
        with self.assertRaises(GameError):
            j.act('inv_order', item='noodle', qty=I.LINE_MAX + 1, supplier='partner', confirm=True)
        with self.assertRaises(GameError):
            add(j, 'partner', 'noodle', I.LINE_MAX + 1)
        add(j, 'partner', 'noodle', I.LINE_MAX)
        with self.assertRaises(GameError):
            add(j, 'partner', 'noodle', 1)


class BigCrate(unittest.TestCase):
    """The biggest crate a save may hold is counted and received like any other, never stranded at the door."""

    def test_big_crate_is_received(self):
        j = fresh()
        qty = I.SAVE_LINE
        oid = big_order(j, 'noodle', qty, short=1)
        wait_until_ready(j, oid)
        with self.assertRaises(GameError):
            j.act('inv_receive', order=oid, count=qty)  # the slip, not what is in the crate
        j.act('inv_receive', order=oid, count=qty - 1)
        self.assertEqual(I.count(j.c, 'noodle'), qty - 1)
        validate_state(j.state)


class Limits(unittest.TestCase):
    def test_every_stocked_shelf_holds_at_least_80_and_none_shrank(self):
        self.assertEqual(I.LINE_MAX, 80)
        for cid in stocked():
            with self.subTest(cid):
                self.assertGreaterEqual(I.capacity(cid), 80)
                self.assertGreaterEqual(I.capacity(cid), OLD.get(cid, 40))
                self.assertLessEqual(I.capacity(cid), I.stock_limit(cid))  # what it writes, step 1 reads
        self.assertEqual(I.capacity('com'), 120)

    def test_one_line_takes_80(self):
        j = fresh(money=50000)
        r = j.act('inv_order', item='noodle', qty=80, supplier='partner', confirm=True)
        o = next(o for o in j.c['ext']['inv']['orders'] if o['id'] == r['eta']['order'])
        self.assertEqual(o['qty'], 80)
        it, sup = I.item('restaurant', 'noodle'), I.supplier('restaurant', 'partner')
        self.assertEqual(o['cost'], I.line_price(it, 80, sup)['cost'])
        self.assertEqual(I.line_price(it, 80, sup)['bulk'], max(p for _, p in sup['bulk']), 'tiers unchanged: 20+ is the top')
        with self.assertRaises(GameError):  # the shelf counts goods on the way
            j.act('inv_order', item='noodle', qty=1, supplier='partner', confirm=True)
        add(j, 'partner', 'egg', 50)
        add(j, 'partner', 'egg', 30)
        with self.assertRaises(GameError):
            add(j, 'partner', 'egg', 1)
        pub = public_inv(j)
        self.assertEqual((pub['line_cap'], pub['capacity']), (80, 80))
        self.assertEqual(next(l for l in pub['carts'][0]['lines'] if l['item'] == 'egg')['qty'], 80)
        validate_state(j.state)

    def test_fit_fills_lines_up_to_80(self):
        j = fresh(money=50000)
        j.act('inv_cart', supplier='partner', op='add', fit=True, lines=[dict(item='noodle', qty=80), dict(item='egg', qty=80)])
        lines = {l['item']: l['qty'] for l in public_inv(j)['carts'][0]['lines']}
        self.assertEqual(lines, {'noodle': 80, 'egg': 80})

    def test_clothing_shares_80_across_sizes(self):
        j = Journey('clothing')
        set_money(j.c, 10**5)
        sizes = I._spec('clothing')['sizes']
        it = next(i for i in I.catalogue('clothing') if i.get('unlock', 1) <= 1 and len(sizes.get(i['id'], ())) >= 2)
        empty(j.c, it['id'])
        a, b = sizes[it['id']][:2]
        sup = next(x for x in I.suppliers('clothing') if I.sells(x, it['id']))
        j.act('inv_order', item=it['id'], qty=50, size=a, supplier=sup['id'], confirm=True)
        j.act('inv_order', item=it['id'], qty=30, size=b, supplier=sup['id'], confirm=True)
        with self.assertRaises(GameError):
            j.act('inv_order', item=it['id'], qty=1, size=b, supplier=sup['id'], confirm=True)
        validate_state(j.state)


def big_save(cid):
    """A save written with the new limits in `cid`: a full shelf (a real LINE_MAX crate counted in, topped up), a
    LINE_MAX order on the way, a LINE_MAX draft line, and a LINE_MAX lot of its dearest item thrown out (a waste row)."""
    j = Journey(cid)
    set_money(j.c, 10**6)
    cap, level = I.capacity(cid), 1 + j.c['xp'] // 90
    n = min(I.LINE_MAX, cap)
    items = [i for i in I.catalogue(cid) if i.get('unlock', 1) <= level and any(I.sells(x, i['id']) for x in I.suppliers(cid))]
    sup = lambda i: next(x for x in sorted(I.suppliers(cid), key=lambda x: x['kind'] != 'rush') if I.sells(x, i['id']))
    a, b, c = (items * 3)[:3]
    for i in {a['id'], b['id'], c['id']}:
        empty(j.c, i)
    oid = j.act('inv_order', item=a['id'], qty=n, supplier=sup(a)['id'], confirm=True)['eta']['order']
    wait_until_ready(j, oid)
    o = next(o for o in j.c['ext']['inv']['orders'] if o['id'] == oid)
    j.act('inv_receive', order=oid, count=o['actual'])
    top = cap - I.count(j.c, a['id'])
    if top > 0:
        I.add_lot(j.c, a['id'], top, a['cost'], I._life(a), 'market')
    if b['id'] != a['id']:
        j.act('inv_order', item=b['id'], qty=n, supplier=sup(b)['id'], confirm=True)
    if c['id'] not in (a['id'], b['id']):
        j.act('inv_cart', supplier=sup(c)['id'], op='add', item=c['id'], qty=n)
    dear = max(items, key=lambda i: i['cost'])
    if dear['id'] not in (a['id'], b['id'], c['id']):
        empty(j.c, dear['id'])
        lot = I.add_lot(j.c, dear['id'], n, dear['cost'], I._life(dear), 'market')
        j.act('inv_discard', lot=lot['id'], confirm=True)
    validate_state(j.state)
    return json.loads(json.dumps(j.state)), max(I.count(j.c, i['id']) for i in items)


def old_tree(test, release, env_key):
    if os.environ.get(env_key):
        return Path(os.environ[env_key])
    try:
        data = subprocess.run(['git', 'archive', release, 'game', 'reference'], cwd=ROOT, capture_output=True,
                              timeout=120, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        test.skipTest(f'no git tree with {release} ({env_key})')
    tmp = tempfile.mkdtemp(prefix=f'mnl-{release}-')
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(tmp, filter='data')
    return Path(tmp)


CHECK = '''import json, sys
from game.engine import validate_state, migrate_state, public_state
out = {}
for cid, s in json.load(sys.stdin).items():
    try:
        validate_state(s); s = migrate_state(s); validate_state(s); public_state(s); out[cid] = None
    except Exception as e:
        out[cid] = str(getattr(e, 'message', e))[:200]
print(json.dumps(out, ensure_ascii=False))
'''


def check_on(tree, saves):
    """Validate, migrate and show each save on an older tree, in one subprocess: {career: None or the error}."""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(tree), os.environ.get('PYTHONPATH', '')) if x))
    out = subprocess.run([sys.executable, '-c', CHECK], input=json.dumps(saves), capture_output=True, text=True,
                         cwd=tree, env=env, encoding='utf-8', timeout=900)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


class OldTrees(unittest.TestCase):
    """Every stocked career's save with the new limits loads on step 1; 1.9.28 refuses the bigger shelves."""
    saves = most = None

    @classmethod
    def build(cls):
        if cls.saves is None:
            cls.saves, cls.most = {}, {}
            for cid in stocked():
                cls.saves[cid], cls.most[cid] = big_save(cid)
        return cls.saves

    def test_saves_load_on_step_1(self):
        saves = self.build()
        self.assertEqual(check_on(old_tree(self, STEP1, 'MNL_STOCK_STEP1_TREE'), saves), {cid: None for cid in saves})

    def test_saves_over_the_old_shelves_fail_on_1_9_28(self):
        saves = self.build()
        got = check_on(old_tree(self, BEFORE, 'MNL_STOCK_1928_TREE'), saves)
        over = {cid for cid in saves if self.most[cid] > OLD.get(cid, 40)}
        self.assertTrue(over)
        for cid in over:
            self.assertIsNotNone(got[cid], cid)


if __name__ == '__main__':
    unittest.main()
