"""🤖 Tự nhận hàng (game/auto_stock.py): with Bộ đếm kho · Bậc 5 a crate at the door is counted and shelved by the
server, exactly as a correct manual count (and its claim) would: the same lots at the same cost, the same refund for a
short delivery, overflow left at the door, a merged van all at once. Also the older stock desks, contract and
specialism stock, the load-time settlement, the Kho switch, and saves a 2.4.3 server still accepts."""
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

import game.careers.kit as kit
from game import auto_stock, business, convenience as cv, inventory
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from tests.helpers import Journey
from tests.test_inventory_flow import Clock, empty, wait_until_ready

ROOT = Path(__file__).resolve().parents[1]
LIVE = 'rel-2.4.3'   # the release this one may be rolled back to


def unlock(j, tier=auto_stock.TIER):
    j.c['upgrades'] += [cv.item_id(j.career, 'count', n) for n in range(1, tier + 1)
                        if cv.item_id(j.career, 'count', n) not in j.c['upgrades']]
    validate_state(j.state)


def short_seq(j, item='noodle'):
    """Make the next order one the market packs short (deterministic, as tests/test_inventory_flow.py does)."""
    x = j.c['ext']['inv']
    base = j.c['day'] * 37 + sum(map(ord, item))
    x['seq'] = next(n for n in range(x['seq'], x['seq'] + 200) if (base + (n + 1) * 11) % 100 < 22)


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock
        self.addCleanup(setattr, kit, 'clock', self.old)

    def journey(self, career='restaurant', auto=True):
        j = Journey(career)
        if auto:
            unlock(j)
        return j


class Inventory(Base):
    def test_a_crate_at_the_door_goes_on_the_shelf_at_its_cost(self):
        j = self.journey()
        empty(j.c, 'noodle')
        j.act('inv_order', item='noodle', qty=6, supplier='partner', confirm=True)
        o = j.c['ext']['inv']['orders'][-1]
        self.assertEqual(kit.stock(j.c, 'noodle'), 0)
        wait_until_ready_or_received(j, o['id'])
        o = next(x for x in j.c['ext']['inv']['orders'] if x['id'] == o['id'])
        self.assertEqual(o['status'], 'received')
        self.assertEqual(kit.stock(j.c, 'noodle'), o['actual'])
        lot = [l for l in j.c['ext']['inv']['lots'] if l['item'] == 'noodle']
        self.assertEqual([(l['qty'], l['unit_cost'], l['supplier']) for l in lot], [(o['actual'], o['unit_cost'], 'partner')])
        self.assertTrue(any(r['text'].startswith(f'📦 Tự nhận {o["actual"]} món') for r in j.c['journal']))
        self.assertGreaterEqual(j.c['metrics'].get('restocked', 0), 1)
        validate_state(j.state)

    def test_same_result_as_a_correct_manual_count_and_claim_for_a_short_delivery(self):
        manual, auto = self.journey(auto=False), self.journey()
        for j in (manual, auto):
            empty(j.c, 'noodle')
            short_seq(j)
            j.act('inv_order', item='noodle', qty=8, supplier='market', confirm=True)
        o = manual.c['ext']['inv']['orders'][-1]
        self.assertLess(o['actual'], o['qty'])
        wait_until_ready(manual, o['id'])
        manual.act('inv_receive', order=o['id'], count=o['actual'])
        manual.act('inv_claim', order=o['id'])
        wait_until_ready_or_received(auto, o['id'])
        a, m = auto.c['ext']['inv']['orders'][-1], manual.c['ext']['inv']['orders'][-1]
        for k in ('status', 'actual', 'qty', 'claimed', 'reply', 'cost', 'unit_cost'):
            self.assertEqual(a[k], m[k], k)
        self.assertTrue(a['claimed'])
        lots = lambda j: sorted((l['item'], l['qty'], l['unit_cost'], l['supplier'], l['expires']) for l in j.c['ext']['inv']['lots'])
        self.assertEqual(lots(auto), lots(manual))
        self.assertEqual(auto.c['money'], manual.c['money'])            # the same refund, once
        refund = [r for r in auto.c['ops']['finance']['ledger'] if r.get('category') == 'refund']
        self.assertEqual(len(refund), 1)
        self.assertIn('đã khiếu nại hoàn', next(r['text'] for r in auto.c['journal'] if r['text'].startswith('📦 Tự nhận')))
        with self.assertRaises(GameError):                              # nothing left to claim
            auto.act('inv_claim', order=a['id'])
        validate_state(auto.state)

    def test_a_crate_that_does_not_fit_waits_at_the_door(self):
        j = self.journey()
        empty(j.c, 'noodle')
        j.act('inv_order', item='noodle', qty=6, supplier='partner', confirm=True)
        o = j.c['ext']['inv']['orders'][-1]
        cap = inventory.capacity('restaurant', j.c)
        inventory.add_lot(j.c, 'noodle', cap - 2, 1, 30, 'opening')     # the shelf filled meanwhile (a gift, returns)
        wait_until_ready(j, o['id'])
        j.act('inv_wait') if public_state(j.state)['careers']['restaurant']['inventory']['clock']['is_open'] else j.act('start_day')
        o = next(x for x in j.c['ext']['inv']['orders'] if x['id'] == o['id'])
        self.assertEqual(o['status'], 'in_transit')                    # left at the door, as inv_receive refuses it
        self.assertEqual(kit.stock(j.c, 'noodle'), cap - 2)
        with self.assertRaises(GameError):
            j.act('inv_receive', order=o['id'], count=o['actual'])

    def test_a_merged_van_is_received_whole(self):
        j = self.journey()
        for item in ('noodle', 'egg'):
            empty(j.c, item)
        j.act('inv_cart', supplier='partner', op='add', item='noodle', qty=4)
        j.act('inv_cart', supplier='partner', op='add', item='egg', qty=3)
        j.act('inv_order_cart', supplier='partner', confirm=True)
        lines = [o for o in j.c['ext']['inv']['orders'] if o.get('group')]
        self.assertEqual(len(lines), 2)
        wait_until_ready_or_received(j, lines[0]['id'])
        lines = [o for o in j.c['ext']['inv']['orders'] if o.get('group')]
        self.assertEqual({o['status'] for o in lines}, {'received'})
        self.assertEqual((kit.stock(j.c, 'noodle'), kit.stock(j.c, 'egg')), (lines[0]['actual'], lines[1]['actual']))
        validate_state(j.state)

    def test_switch_off_and_on_and_locked_below_tier_5(self):
        j = self.journey(auto=False)
        unlock(j, 4)
        with self.assertRaises(GameError):
            j.act('stock_auto', on=False)
        pub = public_state(j.state)['careers']['restaurant']['warehouse']['auto']
        self.assertEqual(pub, dict(unlocked=False, on=False))
        unlock(j)
        self.assertTrue(public_state(j.state)['careers']['restaurant']['warehouse']['auto']['on'])   # on by default
        turn = j.c['turn']
        j.act('stock_auto', on=False)
        self.assertEqual((j.c.get('auto_stock'), j.c['turn']), (False, turn))   # no shop time
        empty(j.c, 'noodle')
        j.act('inv_order', item='noodle', qty=6, supplier='partner', confirm=True)
        o = j.c['ext']['inv']['orders'][-1]
        wait_until_ready(j, o['id'])
        self.assertEqual(j.c['ext']['inv']['orders'][-1]['status'], 'in_transit')   # off: waits for the count
        self.assertFalse(auto_stock.due(j.state))
        j.act('stock_auto', on=True)                                    # on again: the key goes, the crate comes in
        self.assertNotIn('auto_stock', j.c)
        self.assertEqual(j.c['ext']['inv']['orders'][-1]['status'], 'received')
        with self.assertRaises(GameError):
            j.act('stock_auto', on='yes')

    def test_the_load_settlement_receives_what_came_while_away(self):
        j = self.journey(auto=False)
        empty(j.c, 'noodle')
        j.act('inv_order', item='noodle', qty=6, supplier='partner', confirm=True)
        wait_until_ready(j, j.c['ext']['inv']['orders'][-1]['id'])
        self.assertFalse(auto_stock.due(j.state))
        unlock(j)                                                       # bought on another device, say
        self.assertTrue(auto_stock.due(j.state))
        state, result = apply_action(j.state, None, business.ACTION, {}, internal=True)
        self.assertEqual(state['careers']['restaurant']['ext']['inv']['orders'][-1]['status'], 'received')
        self.assertTrue(any('Tự nhận' in x for x in result['effects']))
        self.assertFalse(auto_stock.due(state))

    def test_task_generation_and_the_catalogue_tier_5_text(self):
        item = next(i for i in cv.catalogue(['restaurant']) if i['id'] == cv.item_id('restaurant', 'count', 5))
        self.assertIn('Tự nhận hàng', item['description'])
        self.assertEqual(item['price'], 350000)                         # the price it already had


def wait_until_ready_or_received(j, oid, limit=120):
    for _ in range(limit):
        o = next(x for x in j.c['ext']['inv']['orders'] if x['id'] == oid)
        if o['status'] == 'received':
            return
        clk = public_state(j.state)['careers'][j.career]['inventory']['clock']
        if clk['is_open'] and clk['minute'] < clk['close']:
            j.act('inv_wait')
        else:
            if clk['is_open']:
                j.act('end_day', carry_event=True)
            j.act('start_day')
    raise AssertionError(f'order {oid} never received')


class Legacy(Base):
    def test_mother_baby_parcel_is_shelved_when_here(self):
        j = self.journey('mother_baby')
        before = j.c['stock']['cat_bag']
        j.act('order_stock', item='cat_bag', qty=2, supplier='express')
        ship = j.c['shipments'][-1]
        for _ in range(8):
            if j.c['shipments'][-1]['status'] == 'received':
                break
            j.act('advance')
        self.assertEqual(j.c['shipments'][-1]['status'], 'received')
        self.assertEqual(j.c['stock']['cat_bag'], before + 2)
        self.assertTrue(any(r['text'].startswith('📦 Tự nhận 2 món') for r in j.c['journal']))
        self.assertEqual(ship['id'], j.c['shipments'][-1]['id'])
        validate_state(j.state)


class ContractAndSpecialism(unittest.TestCase):
    def test_contract_cartons_are_received_at_their_cost(self):
        from game import career_scale_inventory as si
        from game.career_scale_content import profile
        from game.content import initial_career
        c = initial_career('grocery')
        c['money'] = c['ops']['finance']['opening_balance'] = 10**8
        c['scale'] = {'tier': 1, 'sites': [{'id': 'base'}, {'id': 'branch-1'}]}
        c['upgrades'] += [cv.item_id('grocery', 'count', n) for n in range(1, 6)]
        s = {'seq': 0, 'careers': {'grocery': c}, 'journey': {}}
        code = profile('grocery').materials[0].code
        si.action(s, c, 'grocery', 'scale_stock_buy', {'site': 'base', 'code': code, 'quantity': 2})
        order = copy.deepcopy(c[si.KEY]['orders'][-1])
        c['journal'] = []
        got = auto_stock.run(s, c, 'grocery')
        self.assertTrue(got and 'Tự nhận' in got[0])
        lot = c[si.KEY]['lots'][-1]
        self.assertEqual((lot['units'], lot['unit_cost'], lot['site'], lot['reserved']), (order['units'], order['unit_cost'], 'base', {}))
        self.assertTrue(c[si.KEY]['orders'][-1]['received'])
        si.validate(c, 'grocery')
        self.assertEqual(auto_stock.run(s, c, 'grocery'), [])           # once

    def test_specialism_bundles_keep_fifo_cost(self):
        from game import career_specialism_stock as stock
        from tests.test_career_specialism import act, learn, prepared
        s, c = prepared()
        learn(s, c, 'grocery', 1)
        act(s, c, 'grocery', 'special_offer', {'tier': 1})
        c['upgrades'] += [cv.item_id('grocery', 'count', n) for n in range(1, 6)]
        act(s, c, 'grocery', 'special_stock_buy', dict(code='sp1_0', quantity=3))
        act(s, c, 'grocery', 'special_stock_buy', dict(code='sp1_0', quantity=2))
        orders = copy.deepcopy(c[stock.KEY]['orders'])
        auto_stock.run(s, c, 'grocery')
        self.assertEqual(c[stock.KEY]['orders'], [])
        self.assertEqual(c[stock.KEY]['lots'][-2:], orders)               # the same rows, in order, at their cost
        stock.validate(c, 'grocery')


class RollbackTo243(unittest.TestCase):
    """Saves written with 🤖 Tự nhận hàng (the switch turned off, crates received and claimed by the server) validate,
    migrate and render on 2.4.3 (`git archive rel-2.4.3`), the release this one may be rolled back to."""

    def tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-243-')
        try:
            data = subprocess.run(['git', 'archive', LIVE, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {LIVE}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return tmp

    def saves(self):
        clock = Clock()
        old, kit.clock = kit.clock, clock
        try:
            out = []
            j = Journey('restaurant')
            unlock(j)
            empty(j.c, 'noodle')
            short_seq(j)
            j.act('inv_order', item='noodle', qty=8, supplier='market', confirm=True)
            wait_until_ready_or_received(j, j.c['ext']['inv']['orders'][-1]['id'])
            out.append(copy.deepcopy(j.state))
            j.act('stock_auto', on=False)
            out.append(copy.deepcopy(j.state))
            m = Journey('mother_baby')
            unlock(m)
            m.act('order_stock', item='cat_bag', qty=2, supplier='express')
            for _ in range(8):
                m.act('advance')
            m.act('stock_auto', on=False)
            out.append(copy.deepcopy(m.state))
            return json.loads(json.dumps(out))
        finally:
            kit.clock = old

    def test_saves_validate_on_243(self):
        saves = self.saves()
        self.assertIs(saves[1]['careers']['restaurant']['auto_stock'], False)
        self.assertEqual(saves[0]['careers']['restaurant']['ext']['inv']['orders'][-1]['claimed'], True)
        old = self.tree()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state;out=[]\n'
                'for s in json.load(sys.stdin):\n validate_state(s);s=migrate_state(s);validate_state(s);public_state(s)\n'
                ' out.append(s["careers"]["restaurant"].get("auto_stock",None) if "restaurant" in s.get("careers",{}) else None)\n'
                'import game;print(json.dumps([game.__version__,out]))')
        env = {k: v for k, v in os.environ.items() if k != 'MNL_CAREERS'}   # a test module's career filter
        env['PYTHONPATH'] = old
        got = subprocess.run([sys.executable, '-c', prog], input=json.dumps(saves), capture_output=True, text=True,
                             cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        version, keys = json.loads(got.stdout)
        self.assertEqual(version, '2.4.3')
        self.assertEqual(keys[1], False)                                  # the key is kept, just not read


if __name__ == '__main__':
    unittest.main()
