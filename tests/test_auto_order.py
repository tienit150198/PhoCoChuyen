"""🔁 Tự đặt hàng (game/auto_order.py, feedback #387): a paid unlock per workplace with a stock room. Once owned, an item
whose shelf plus what is on the way falls below its line is ordered again through the manual order path, from the fund
only, above a floor and within a daily cap; once per item until it arrives; on load too. Saves holding it load on
2.4.11 and 2.4.12 (`git archive`), the releases this one may be rolled back to."""
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
from game import auto_order as ao, business, inventory, journey as jr
from game.engine import GameError, apply_action, public_state, validate_state
from tests.helpers import Journey
from tests.test_inventory_flow import Clock, empty, set_money, wait_until_ready

ROOT = Path(__file__).resolve().parents[1]
LIVES = (('rel-2.4.11', '2.4.11'), ('tile-nocap', '2.4.12'))   # releases this one may be rolled back to (live 2.4.12)
ITEM = 'noodle'


def own(j, only=ITEM, below=10, qty=20):
    """Owned (as bought), every other item switched off, ITEM at "còn dưới `below` thì đặt `qty`"."""
    j.c[ao.KEY] = dict(paid=ao.PRICE, items={i['id']: dict(on=False) for i in inventory.catalogue(j.career) if i['id'] != only})
    j.c[ao.KEY]['items'][only] = dict(below=below, qty=qty)
    validate_state(j.state)


def shelf(j, n, item=ITEM):
    empty(j.c, item)
    if n:
        inventory.add_lot(j.c, item, n, 3, 30, 'opening')


def auto_orders(j, item=ITEM):
    return [o for o in j.c['ext']['inv']['orders'] if o['item'] == item and o['status'] == 'in_transit']


class Base(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        old = kit.clock
        kit.clock = self.clock
        self.addCleanup(setattr, kit, 'clock', old)

    def journey(self, fund=20000):
        j = Journey('restaurant')
        set_money(j.c, fund)
        j.c['day_start_money'] = fund
        return j


class Purchase(Base):
    def test_price_paid_from_the_fund(self):
        self.assertEqual(ao.PRICE, 100000)
        j = self.journey(fund=400000)
        pub = public_state(j.state)['careers']['restaurant']['warehouse']['reorder']
        self.assertEqual((pub['owned'], pub['price'], pub['short']), (False, 100000, 0))
        with self.assertRaises(GameError):
            j.act('stock_reorder', buy=True)                                  # no confirm
        with self.assertRaises(GameError):
            j.act('stock_reorder', item=ITEM, on=False)                       # not owned yet
        turn = j.c['turn']
        j.act('stock_reorder', buy=True, confirm=True)
        self.assertEqual(j.c[ao.KEY]['paid'], 100000)
        self.assertEqual(j.c['turn'], turn)                                   # no shop time
        row = next(r for r in reversed(j.c['ops']['finance']['ledger']) if r['amount'] == -100000)
        self.assertEqual(row['category'], 'upgrade')
        with self.assertRaises(GameError):
            j.act('stock_reorder', buy=True, confirm=True)                    # once
        self.assertNotIn('auto_order', j.c['upgrades'])
        validate_state(j.state)

    def test_fund_first_then_the_wallet(self):
        j = self.journey(fund=100000)
        jr.enable_story(j.state, 7)
        j.state['journey']['wallet'] = 300000
        j.act('stock_reorder', buy=True, confirm=True)
        self.assertEqual(j.state['journey']['wallet'], 50000)                 # 250,000 from the wallet
        self.assertTrue(ao.owned(j.c))
        f = j.c['ops']['finance']
        self.assertEqual(f['opening_balance'] + sum(x['amount'] for x in f['ledger']), j.c['money'])
        self.assertEqual(j.state['journey']['history'][-1]['amount'], -250000)
        validate_state(j.state)

    def test_refused_when_fund_and_wallet_are_short(self):
        j = self.journey(fund=100000)
        jr.enable_story(j.state, 7)
        j.state['journey']['wallet'] = 200000
        before = copy.deepcopy(j.state)
        pub = public_state(j.state)['careers']['restaurant']['warehouse']['reorder']
        self.assertEqual(pub['short'], 50000)
        with self.assertRaises(GameError) as e:
            j.act('stock_reorder', buy=True, confirm=True)
        self.assertIn('50.000', str(e.exception))
        self.assertEqual(j.state, before)                                    # nothing changed
        classic = self.journey(fund=349999)                                   # no story: no wallet to top up from
        with self.assertRaises(GameError):
            classic.act('stock_reorder', buy=True, confirm=True)


class Trigger(Base):
    def test_orders_below_the_line_once(self):
        j = self.journey()
        own(j)
        shelf(j, 10)
        j.act('inv_wait')
        self.assertEqual(auto_orders(j), [])                                  # 10 is not below 10
        inventory.take(j.c, ITEM, 1)
        r = j.act('inv_wait')
        orders = auto_orders(j)
        self.assertEqual([o['qty'] for o in orders], [20])
        self.assertEqual(orders[0]['supplier'], 'partner')                   # the default supplier
        self.assertTrue(any(x.startswith('🔁 Tự đặt 1 món') for x in r['effects']))
        self.assertTrue(any(x['text'].startswith('🔁 Tự đặt 20 vắt Mì tươi (Nhà phân phối Hạt Nắng, ') for x in j.c['journal']))
        inventory.take(j.c, ITEM, 9)                                          # empty shelf, still one on the way
        j.act('inv_wait')
        self.assertEqual(len(auto_orders(j)), 1)
        validate_state(j.state)

    def test_one_pending_per_item_even_when_a_small_order_leaves_it_low(self):
        j = self.journey()
        own(j, below=30, qty=5)
        shelf(j, 0)
        j.act('inv_wait')
        j.act('inv_wait')
        self.assertEqual([o['qty'] for o in auto_orders(j)], [5])            # 0 + 5 < 30, but one is pending

    def test_last_used_supplier(self):
        j = self.journey()
        shelf(j, 40)
        j.act('inv_order', item=ITEM, qty=5, supplier='market', confirm=True)
        wait_until_ready(j, j.c['ext']['inv']['orders'][-1]['id'])
        own(j)
        shelf(j, 2)
        j.act('inv_receive', order=j.c['ext']['inv']['orders'][-1]['id'], count=j.c['ext']['inv']['orders'][-1]['actual'])
        shelf(j, 2)
        j.act('inv_wait') if public_state(j.state)['careers']['restaurant']['inventory']['clock']['is_open'] else j.act('start_day')
        self.assertEqual(auto_orders(j)[-1]['supplier'], 'market')

    def test_same_order_and_lot_as_a_manual_order(self):
        manual, auto = self.journey(), self.journey()
        own(auto, qty=24)
        for j in (manual, auto):
            shelf(j, 3)
        manual.act('inv_order', item=ITEM, qty=24, supplier='partner', confirm=True)
        auto.act('inv_wait')                                                  # the same one tick of shop time
        m, a = manual.c['ext']['inv']['orders'][-1], auto.c['ext']['inv']['orders'][-1]
        self.assertEqual(a, m)                                                # price, wholesale, ship, lead time, packing
        self.assertEqual(auto.c['money'], manual.c['money'])
        row = lambda j: [(r['amount'], r['category'], r['reason']) for r in j.c['ops']['finance']['ledger'] if r['ref'] == m['id']]
        self.assertEqual(row(auto), row(manual))
        for j in (manual, auto):
            wait_until_ready(j, m['id'])
            j.act('inv_receive', order=m['id'], count=m['actual'])
        lots = lambda j: sorted((l['item'], l['qty'], l['unit_cost'], l['supplier'], l['expires']) for l in j.c['ext']['inv']['lots'] if l['item'] == ITEM)
        self.assertEqual(lots(auto), lots(manual))                            # FIFO lots at the order's unit cost


class Money(Base):
    def test_fund_floor_skips_with_one_notice_a_day(self):
        j = self.journey()
        set_money(j.c, ao.floor(j.state, j.c) + 10)                         # above the floor by less than an order
        own(j)
        shelf(j, 0)
        r = j.act('inv_wait')
        self.assertEqual(auto_orders(j), [])
        self.assertIn('🔁 Quỹ không đủ để tự đặt.', r['effects'])
        self.assertTrue(public_state(j.state)['careers']['restaurant']['warehouse']['reorder']['warn'])
        r = j.act('inv_wait')
        self.assertNotIn('🔁 Quỹ không đủ để tự đặt.', r['effects'])        # once a day
        set_money(j.c, 20000)
        j.act('inv_wait')
        self.assertEqual(len(auto_orders(j)), 1)

    def test_daily_cap_is_half_the_morning_fund(self):
        j = self.journey()
        own(j, qty=20)
        for item in ('egg', 'beef'):
            j.c[ao.KEY]['items'][item] = dict(below=10, qty=20)
        price = lambda item: inventory.line_price(inventory.item('restaurant', item), 20, inventory.supplier('restaurant', 'partner'))
        costs = {i: price(i)['cost'] + inventory.ship_fee(inventory.supplier('restaurant', 'partner'), price(i)['cost']) for i in (ITEM, 'egg', 'beef')}
        j.c['day_start_money'] = 2 * (costs[ITEM] + costs['egg'])             # room for two of the three
        for item in costs:
            shelf(j, 0, item)
        r = j.act('inv_wait')
        placed = [o['item'] for o in j.c['ext']['inv']['orders'] if o['status'] == 'in_transit']
        self.assertEqual(len(placed), 2)
        self.assertLessEqual(j.c[ao.KEY]['spent'], ao.budget(j.c))
        self.assertTrue(any('Tự đặt 2 món' in x for x in r['effects']))
        self.assertEqual(ao.plan(j.state, j.c, 'restaurant')[1], 'cap')
        r = j.act('inv_wait')
        self.assertIn('🔁 Hết mức tự đặt hôm nay.', r['effects'])
        self.assertEqual(len([o for o in j.c['ext']['inv']['orders'] if o['status'] == 'in_transit']), 2)
        j.act('end_day', carry_event=True)                                    # a new shop day: a new cap
        j.act('start_day')
        missed = next(i for i in costs if i not in placed)
        self.assertEqual(len(auto_orders(j, missed)), 1)
        self.assertEqual(j.c[ao.KEY]['day'], j.c['day'])

    def test_never_the_wallet(self):
        j = self.journey(fund=100)
        jr.enable_story(j.state, 7)
        j.state['journey']['wallet'] = 10**6
        own(j)
        shelf(j, 0)
        j.act('inv_wait')
        self.assertEqual(auto_orders(j), [])
        self.assertEqual(j.state['journey']['wallet'], 10**6)


class Offline(Base):
    def test_load_settlement_orders_what_ran_low_while_away(self):
        j = self.journey()
        own(j)
        shelf(j, 20)
        j.act('inv_wait')
        self.assertFalse(ao.due(j.state))
        shelf(j, 4)                                                           # staff sold it while the player was away
        self.assertTrue(ao.due(j.state))
        state, result = apply_action(j.state, None, business.ACTION, {}, internal=True)
        self.assertEqual(len([o for o in state['careers']['restaurant']['ext']['inv']['orders'] if o['status'] == 'in_transit']), 1)
        self.assertTrue(any('Tự đặt' in x for x in result['effects']))
        self.assertFalse(ao.due(state))

    def test_a_paused_place_is_left_alone(self):
        j = self.journey()
        jr.enable_story(j.state, 7)
        own(j)
        shelf(j, 0)
        j.state['journey']['paused']['restaurant'] = 1
        self.assertFalse(ao.due(j.state))


class Switches(Base):
    def test_off_stops_it_and_on_resumes(self):
        j = self.journey()
        own(j)
        j.act('stock_reorder', on=False)
        self.assertIs(j.c[ao.KEY]['on'], False)
        shelf(j, 0)
        j.act('inv_wait')
        self.assertEqual(auto_orders(j), [])
        self.assertFalse(ao.due(j.state))
        j.act('stock_reorder', item=ITEM, on=False)
        j.act('stock_reorder', on=True)
        self.assertNotIn('on', j.c[ao.KEY])
        self.assertEqual(auto_orders(j), [])                                  # the item itself is off
        r = j.act('stock_reorder', item=ITEM, on=True)
        self.assertEqual(len(auto_orders(j)), 1)                              # on again: ordered at once
        self.assertIn('còn dưới 10 thì đặt 20', r['message'])

    def test_numbers_are_checked_and_defaults_stay_out_of_the_save(self):
        j = self.journey()
        own(j)
        below, qty = ao.defaults(j.c, 'restaurant')
        self.assertEqual((below, qty), (16, 56))                              # 20 % of 80, then up to 90 %
        with self.assertRaises(GameError):
            j.act('stock_reorder', item=ITEM, below=0)
        with self.assertRaises(GameError):
            j.act('stock_reorder', item=ITEM, qty=10**6)
        with self.assertRaises(GameError):
            j.act('stock_reorder', item='nope', on=True)
        j.act('stock_reorder', item=ITEM, below=below, qty=qty)
        self.assertNotIn(ITEM, j.c[ao.KEY]['items'])
        for bad in (dict(paid=-1), dict(paid=1, on=True), dict(paid=1, items={'x': {}}), dict(paid=1, items={ITEM: {'on': 1}}), dict(paid=1, extra=1)):
            j.c[ao.KEY] = bad
            with self.assertRaises(GameError):
                validate_state(j.state)


class RollbackTo2411(unittest.TestCase):
    """Saves holding 🔁 Tự đặt hàng (bought, settings, automatic orders on the way and received, the switch off) validate,
    migrate, render and take a command on 2.4.11 and 2.4.12 (`git archive`), which keep the key without reading it."""

    def tree(self, ref):
        tmp = tempfile.mkdtemp(prefix='mnl-2411-')
        self.addCleanup(subprocess.run, ['rm', '-rf', tmp])
        try:
            data = subprocess.run(['git', 'archive', ref, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return tmp

    def saves(self):
        clock = Clock()
        old, kit.clock = kit.clock, clock
        try:
            out = []
            j = Journey('restaurant')
            jr.enable_story(j.state, 7)
            set_money(j.c, 200000)
            j.c['day_start_money'] = 200000
            j.state['journey']['wallet'] = 200000
            j.act('stock_reorder', buy=True, confirm=True)                    # fund then wallet: the fund is empty now
            set_money(j.c, 20000)
            j.c['day_start_money'] = 20000
            j.act('stock_reorder', item=ITEM, below=12, qty=30)
            shelf(j, 0)
            j.act('inv_wait')
            out.append(copy.deepcopy(j.state))
            o = j.c['ext']['inv']['orders'][-1]
            wait_until_ready(j, o['id'])
            j.act('inv_receive', order=o['id'], count=o['actual'])
            j.act('stock_reorder', on=False)
            out.append(copy.deepcopy(j.state))
            return json.loads(json.dumps(out))
        finally:
            kit.clock = old

    def test_saves_validate_on_2411_and_2412(self):
        saves = self.saves()
        self.assertIn('open', saves[0]['careers']['restaurant']['auto_order'])
        self.assertIs(saves[1]['careers']['restaurant']['auto_order']['on'], False)
        trees = [(self.tree(ref), want) for ref, want in LIVES]
        if not any(t for t, _ in trees):
            self.skipTest('no git tree with ' + ', '.join(ref for ref, _ in LIVES))
        for old, want in trees:
            if old:
                with self.subTest(want=want):
                    self.check(old, want, saves)

    def check(self, old, want, saves):
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state,apply_action;out=[]\n'
                'for s in json.load(sys.stdin):\n validate_state(s);s=migrate_state(s);validate_state(s);public_state(s)\n'
                ' s,_=apply_action(s,"restaurant","inv_wait",{});validate_state(s)\n'
                ' out.append(s["careers"]["restaurant"].get("auto_order"))\n'
                'import game;print(json.dumps([game.__version__,out]))')
        env = {k: v for k, v in os.environ.items() if k != 'MNL_CAREERS'}
        env['PYTHONPATH'] = old
        got = subprocess.run([sys.executable, '-c', prog], input=json.dumps(saves), capture_output=True, text=True,
                             cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        version, keys = json.loads(got.stdout)
        self.assertEqual(version, want)
        self.assertEqual(keys, [s['careers']['restaurant']['auto_order'] for s in saves])   # kept, not read


if __name__ == '__main__':
    unittest.main()
