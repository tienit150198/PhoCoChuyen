"""🔁 Tự đặt hàng on the older stock desks, Mẹ & bé and Nhà thuốc (game/auto_order.py DESK, player feedback #433 "Sao
trong tiệm mẹ và bé lại ko có nút nhập hàng tự động vậy?"): the same paid unlock, rule per item, fund floor, daily cap
and partial order as the other shops, placed through engine.order_stock (one merged order per supplier, SLOTS_FREE vans
kept for the player). The save key c[DESK_KEY] loads on 2.4.58 and 2.4.51 (`git archive`), which ignore it."""
import copy
import io
import json
import math
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import auto_order as ao, business, engine
from game.engine import GameError, apply_action, public_state, validate_state
from tests.helpers import Journey, as_stored
from tests.test_inventory_flow import set_money

ROOT = Path(__file__).resolve().parents[1]
LIVES = (('92968b5f', '2.4.58'), ('origin/rel/2.4.51', '2.4.51'))   # releases this one may be rolled back to
ITEM = 'bunny'


def journey(career='mother_baby', fund=20000):
    j = Journey(career)
    set_money(j.c, fund)
    j.c['day_start_money'] = fund
    return j


def own(j, only=ITEM, below=10, qty=20):
    """Owned (as bought), every other item switched off, `only` at "còn dưới `below` thì đặt `qty`"."""
    j.c[ao.DESK_KEY] = dict(paid=ao.PRICE, items={i['id']: dict(on=False) for i in ao.catalogue(j.career) if i['id'] != only})
    j.c[ao.DESK_KEY]['items'][only] = dict(below=below, qty=qty)
    validate_state(j.state)


def auto(j, item=None):
    return [x for x in j.c['shipments'] if x['status'] == 'in_transit' and (item is None or x['item'] == item)]


def reorder(j):
    return public_state(j.state)['careers'][j.career]['warehouse']['reorder']


class Purchase(unittest.TestCase):
    def test_bought_like_the_other_shops_under_the_desk_key(self):
        for career in ('mother_baby', 'pharmacy'):
            with self.subTest(career=career):
                j = journey(career, fund=400000)
                ro = reorder(j)
                self.assertEqual((ro['owned'], ro['price'], ro['short']), (False, 100000, 0))
                with self.assertRaises(GameError):
                    j.act('stock_reorder', buy=True)                          # no confirm
                with self.assertRaises(GameError):
                    j.act('stock_reorder', on=False)                          # not owned yet
                turn = j.c['turn']
                j.act('stock_reorder', buy=True, confirm=True)
                self.assertEqual(j.c[ao.DESK_KEY]['paid'], 100000)
                self.assertNotIn(ao.KEY, j.c)                                 # 2.4.58 would refuse c[KEY] here
                self.assertNotIn('auto_order', j.c['upgrades'])
                self.assertEqual(j.c['turn'], turn)                           # no shop time
                row = next(r for r in j.c['ops']['finance']['ledger'] if r['amount'] == -100000)
                self.assertEqual(row['category'], 'upgrade')
                with self.assertRaises(GameError):
                    j.act('stock_reorder', buy=True, confirm=True)            # once
                ro = reorder(j)
                self.assertTrue(ro['owned'] and ro['on'])
                self.assertIsNone(ro['box'])                                  # the desk merges by itself: no box sold
                self.assertEqual((ro['cap'], ro['line']), (80, 80))
                self.assertEqual({i['id'] for i in ro['items']}, {i['id'] for i in ao.catalogue(career)})
                with self.assertRaises(GameError):
                    j.act('stock_reorder', buy_box=True, confirm=True)
                validate_state(j.state)

    def test_the_locked_line_shows_after_a_few_orders(self):
        j = journey(fund=400000)
        self.assertFalse(reorder(j)['tease'])                                 # #384: no advert for a newcomer
        for item in ('bear', 'towel', 'card'):
            j.act('order_stock', item=item, qty=1)
        self.assertTrue(reorder(j)['tease'])


class Trigger(unittest.TestCase):
    def test_orders_below_the_line_once_at_the_desk_price(self):
        j = journey()
        own(j)
        j.c['stock'][ITEM] = 10
        j.act('advance')
        self.assertEqual(auto(j), [])                                         # 10 is not below 10
        j.c['stock'][ITEM] = 9
        r = j.act('advance')
        got = auto(j)
        self.assertEqual([(x['item'], x['qty'], x['supplier'], x['cost']) for x in got], [(ITEM, 20, 'partner', 36 * 20)])
        self.assertTrue(any(x.startswith('🔁 Tự đặt 1 món · 720 xu') for x in r['effects']))
        self.assertTrue(any(x['text'].startswith('🔁 Tự đặt 20 món Thỏ bông Mây (') for x in j.c['journal']))
        self.assertEqual(j.c[ao.DESK_KEY]['open'], {ITEM: got[0]['id']})
        self.assertEqual(j.c[ao.DESK_KEY]['spent'], 720)
        j.c['stock'][ITEM] = 0                                                # still one on the way
        j.act('advance')
        self.assertEqual(len(auto(j)), 1)
        self.assertTrue(next(i for i in reorder(j)['items'] if i['id'] == ITEM)['auto'])
        validate_state(j.state)

    def test_last_used_supplier(self):
        j = journey()
        j.act('order_stock', item=ITEM, qty=1, supplier='market')
        j.c['shipments'][-1]['status'] = 'received'
        own(j)
        j.c['stock'][ITEM] = 0
        j.act('advance')
        self.assertEqual([x['supplier'] for x in auto(j)], ['market'])
        self.assertEqual(auto(j)[0]['cost'], math.ceil(36 * 20 * engine._stock_supplier('mother_baby', 'market')['factor']))

    def test_one_merged_order_per_supplier_and_vans_kept_for_the_player(self):
        j = journey(fund=10**6)
        for p in ao.catalogue('mother_baby')[:5]:                             # five vans of the player's own
            j.act('order_stock', item=p['id'], qty=1)
        self.assertEqual(engine.stock_vans(j.c), 5)
        j.c[ao.DESK_KEY] = dict(paid=ao.PRICE)                                # every item on, the defaults
        for k in j.c['stock']:
            j.c['stock'][k] = 0
        j.act('advance')
        got = [x for x in auto(j) if x['qty'] > 1]
        self.assertEqual(len(got), engine.STOCK_LINES)                        # one van left: one merged order of 12
        self.assertEqual(engine.stock_vans(j.c), engine.STOCK_VANS - ao.SLOTS_FREE)
        self.assertEqual(len({(x['placed'], x['at']) for x in got}), 1)
        self.assertEqual({x['qty'] for x in got}, {56})                       # 90 % of 80 minus the line of 16
        validate_state(j.state)
        j.act('order_stock', item='lixi', qty=1)                              # the player still has a van
        validate_state(j.state)

    def test_never_past_the_shelf(self):
        j = journey()
        own(j, below=80, qty=80)
        j.c['stock'][ITEM] = 70
        j.act('advance')
        self.assertEqual([x['qty'] for x in auto(j)], [10])                   # capacity 80


class Money(unittest.TestCase):
    def test_fund_floor_part_order_and_one_notice_a_day(self):
        j = journey()
        own(j)
        set_money(j.c, ao.floor(j.state, j.c) + 300)                         # 20 cost 720: the most it covers is 8
        j.c['stock'][ITEM] = 0
        j.act('advance')
        self.assertEqual([x['qty'] for x in auto(j)], [8])
        j2 = journey()
        own(j2)
        set_money(j2.c, ao.floor(j2.state, j2.c) + 100)                      # not even Y / PART_MIN (5 × 36)
        j2.c['stock'][ITEM] = 0
        r = j2.act('advance')
        self.assertEqual(auto(j2), [])
        self.assertIn('🔁 Quỹ không đủ để tự đặt.', r['effects'])
        self.assertEqual(reorder(j2)['why'], 'fund')
        r = j2.act('advance')
        self.assertNotIn('🔁 Quỹ không đủ để tự đặt.', r['effects'])        # once a day

    def test_daily_cap(self):
        j = journey()
        own(j)
        j.c['day_start_money'] = 2 * 100                                      # cap 100 xu: not a quarter of the order
        j.c['stock'][ITEM] = 0
        r = j.act('advance')
        self.assertEqual(auto(j), [])
        self.assertIn('🔁 Hết mức tự đặt hôm nay.', r['effects'])
        self.assertEqual(reorder(j)['why'], 'cap')


class Pharmacy(unittest.TestCase):
    def test_valid_lots_only_and_a_held_lot_is_left_alone(self):
        j = journey('pharmacy')
        self.assertEqual({i['id'] for i in ao.catalogue('pharmacy')}, {f'P-0{n}-A' for n in range(1, 7)})
        own(j, only='P-01-A')
        j.act('ph_quarantine', lot='P-02-A')
        j.c[ao.DESK_KEY]['items'].pop('P-02-A')                               # on too
        j.act('advance')                                                      # the shelf holds 6 of each, below 10
        self.assertEqual([(x['item'], x['qty']) for x in auto(j)], [('P-01-A', 20)])
        with self.assertRaises(GameError):
            j.act('stock_reorder', item='P-01-B', on=False)                   # not a valid lot: never ordered
        validate_state(j.state)


class Settings(unittest.TestCase):
    def test_numbers_are_checked_and_defaults_stay_out_of_the_save(self):
        j = journey(fund=400000)
        j.act('stock_reorder', buy=True, confirm=True)
        j.act('stock_reorder', item=ITEM, below=12, qty=30)
        self.assertEqual(j.c[ao.DESK_KEY]['items'], {ITEM: dict(below=12, qty=30)})
        with self.assertRaises(GameError):
            j.act('stock_reorder', item=ITEM, below=81)                       # past the shelf
        with self.assertRaises(GameError):
            j.act('stock_reorder', item=ITEM, qty=81)                         # past the order line
        with self.assertRaises(GameError):
            j.act('stock_reorder', item='noodle', on=False)                   # not sold here
        j.act('stock_reorder', item=ITEM, below=16, qty=56)                   # the defaults
        self.assertNotIn('items', j.c[ao.DESK_KEY])
        j.act('stock_reorder', on=False)
        self.assertIs(j.c[ao.DESK_KEY]['on'], False)
        validate_state(j.state)

    def test_each_kind_of_workplace_keeps_its_own_key(self):
        cases = (('mother_baby', ao.KEY, dict(paid=1)), ('mother_baby', ao.BOX_KEY, dict(paid=1)),
                 ('restaurant', ao.DESK_KEY, dict(paid=1)), ('mother_baby', ao.DESK_KEY, dict(paid=1, items={'noodle': {}})),
                 ('pharmacy', ao.DESK_KEY, dict(paid=1, open={'P-01-C': 'shipment-1'})))
        for career, key, value in cases:
            with self.subTest(career=career, key=key):
                j = Journey(career)
                j.c[key] = value
                with self.assertRaises(GameError):
                    validate_state(j.state)


class Offline(unittest.TestCase):
    def test_load_settlement_orders_what_ran_low_while_away(self):
        j = journey()
        own(j)
        j.c['stock'][ITEM] = 20
        j.act('advance')
        self.assertFalse(ao.due(j.state))
        j.c['stock'][ITEM] = 4                                                # sold while the player was away
        self.assertTrue(ao.due(j.state))
        state, result = apply_action(j.state, None, business.ACTION, {}, internal=True)
        self.assertEqual(len([x for x in state['careers']['mother_baby']['shipments'] if x['status'] == 'in_transit']), 1)
        self.assertTrue(any('Tự đặt' in x for x in result['effects']))
        self.assertFalse(ao.due(state))
        validate_state(state)


class Rollback(unittest.TestCase):
    """Saves holding 🔁 Tự đặt hàng on Mẹ & bé validate, migrate, render and take a command on 2.4.58 and 2.4.51
    (`git archive`), which keep c[DESK_KEY] without reading it."""

    def tree(self, ref):
        tmp = tempfile.mkdtemp(prefix='mnl-desk-')
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
        j = journey(fund=400000)
        j.act('stock_reorder', buy=True, confirm=True)                        # orders what is low at once
        j.act('stock_reorder', item=ITEM, below=12, qty=30)
        out = [copy.deepcopy(j.state)]
        j.act('stock_reorder', on=False)
        out.append(copy.deepcopy(j.state))
        return json.loads(json.dumps(out))

    def test_saves_validate_on_older_releases(self):
        saves = self.saves()
        self.assertIn('open', saves[0]['careers']['mother_baby'][ao.DESK_KEY])
        self.assertIs(saves[1]['careers']['mother_baby'][ao.DESK_KEY]['on'], False)
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
                ' s,_=apply_action(s,"mother_baby","advance",{});validate_state(s)\n'
                f' out.append(s["careers"]["mother_baby"].get("{ao.DESK_KEY}"))\n'
                'import game;print(json.dumps([game.__version__,out]))')
        env = {k: v for k, v in os.environ.items() if k != 'MNL_CAREERS'}
        env['PYTHONPATH'] = old
        got = subprocess.run([sys.executable, '-c', prog], input=json.dumps([as_stored(s) for s in saves]), capture_output=True, text=True,
                             cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        version, keys = json.loads(got.stdout)
        self.assertEqual(version, want)
        self.assertEqual(keys, [s['careers']['mother_baby'][ao.DESK_KEY] for s in saves])   # kept, not read


if __name__ == '__main__':
    unittest.main()
