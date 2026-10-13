"""Paid milk-tea storage preserves stock, incoming orders and expiry accounting."""
import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import boba, experiences
from game.content import public_content
from game.engine import GameError, public_state
from tests.helpers import Journey
from tests.test_milk_tea_prevent import set_fund


class BobaStorageCapacity(unittest.TestCase):
    def shop(self, tier=0):
        j = Journey('milk_tea')
        j.c['upgrades'].extend(f'warehouse_storage_milk_tea_{n}' for n in range(1, tier + 1))
        set_fund(j, 100_000)
        return j

    def lot(self, j, item, qty, **extra):
        j.c['life']['pantry'] = [dict(id='test-lot', item=item, qty=qty, unit_cost=2,
                                      expires=j.c['day'] + 2, received=j.c['day'], **extra)]

    def test_all_paid_tiers_publish_capacity_without_mutating_stock(self):
        shelves = (60, 90, 135, 195, 285, 413, 600, 900, 1350, 1950, 3000)
        cups = (120, 180, 270, 390, 570, 825, 1200, 1800, 2700, 3900, 6000)
        for tier, (shelf, cup) in enumerate(zip(shelves, cups)):
            j = self.shop(tier)
            before = copy.deepcopy(j.c)
            p = boba.public(j.c)
            self.assertEqual((p['shelf_cap'], p['cup_cap']), (shelf, cup))
            self.assertEqual(j.c, before)

    def test_prepare_uses_paid_capacity_and_keeps_batch_limit(self):
        j = self.shop(1)
        self.lot(j, 'milk', 80)
        boba._prepare(j.state, j.c, dict(item='milk', qty=10, confirm=True))
        self.assertEqual(boba.held(j.c)['milk'], 90)
        with self.assertRaises(GameError):
            boba._prepare(j.state, j.c, dict(item='milk', qty=1, confirm=True))
        with self.assertRaises(GameError):
            boba._prepare(j.state, j.c, dict(item='black', qty=21, confirm=True))
        experiences.validate(j.c, 'milk_tea')

    def test_order_and_delivery_use_capacity_and_reserve_incoming(self):
        j = self.shop(1)
        self.lot(j, 'jelly', 70)
        b = boba.state(j.c)
        b['cups']['M'] = 160
        for item, qty in [('jelly', 20), ('cup_M', 1)]:
            boba._order(j.state, j.c, dict(item=item, qty=qty, supplier='express', confirm=True))
            with self.assertRaises(GameError):
                boba._order(j.state, j.c, dict(item=item, qty=1, supplier='express', confirm=True))
        cash = j.c['money']
        boba._deliver(j.state, j.c, b, now=10**8)
        self.assertEqual(boba.held(j.c)['jelly'], 90)
        self.assertEqual(b['cups']['M'], 180)
        self.assertEqual(b['orders'], [])
        self.assertEqual(j.c['money'], cash)
        experiences.validate(j.c, 'milk_tea')

    def test_blocked_prepaid_delivery_stays_pending_and_is_received_once(self):
        j = self.shop()
        b = boba.state(j.c)
        self.lot(j, 'jelly', 40)
        boba._order(j.state, j.c, dict(item='jelly', qty=20, supplier='express', confirm=True))
        self.lot(j, 'jelly', 50)
        before = copy.deepcopy(b['orders'])
        boba._deliver(j.state, j.c, b, now=10**8)
        self.assertEqual(b['orders'], before)
        self.assertEqual(boba.held(j.c)['jelly'], 50)
        j.c['life']['pantry'][0]['qty'] = 40
        boba._deliver(j.state, j.c, b, now=10**8)
        boba._deliver(j.state, j.c, b, now=10**8)
        self.assertEqual(boba.held(j.c)['jelly'], 60)
        self.assertEqual(b['orders'], [])

    def test_prepare_reserves_legacy_incoming_tea(self):
        j = self.shop()
        self.lot(j, 'milk', 50)
        b = boba.state(j.c)
        boba._place(j.state, j.c, b, 'milk', 10, boba.SUP_INDEX['partner'], 0, 2, 'Test')
        before = copy.deepcopy(j.c)
        with self.assertRaises(GameError):
            boba._prepare(j.state, j.c, dict(item='milk', qty=1, confirm=True))
        self.assertEqual(j.c, before)

    def test_expiry_keeps_full_paid_stock_waste_quantity_and_value(self):
        j = self.shop(10)
        self.lot(j, 'milk', 3000, made=boba.opening_abs(j.c))
        j.c['life']['pantry'][0]['unit_cost'] = 20
        boba.on_close(j.state, j.c)
        self.assertEqual(j.c['life']['waste'][-1]['qty'], 3000)
        self.assertEqual(j.c['life']['waste'][-1]['value'], 60_000)
        experiences.validate(j.c, 'milk_tea')

    def test_close_preserves_all_live_lot_identities(self):
        j = self.shop(10)
        j.c['life']['pantry'] = [dict(id=f'lot-{n}', item='jelly', qty=1, unit_cost=2,
                                     expires=j.c['day'] + 2, received=j.c['day']) for n in range(3000)]
        before = copy.deepcopy(j.c['life']['pantry'])
        experiences.on_close(j.state, j.c, 'milk_tea')
        self.assertEqual(j.c['life']['pantry'], before)
        experiences.validate(j.c, 'milk_tea')

    def test_maximum_stock_all_ingredients_and_cups_validates(self):
        j = self.shop(10)
        j.c['life']['pantry'] = [dict(id=item, item=item, qty=3000, unit_cost=2,
                                     expires=j.c['day'] + 2, received=j.c['day']) for item in boba.ING]
        boba.state(j.c)['cups'] = dict(M=6000, L=6000)
        experiences.validate(j.c, 'milk_tea')
        j.c['life']['pantry'][0]['qty'] += 1
        with self.assertRaises(GameError):
            experiences.validate(j.c, 'milk_tea')

    def test_short_delivery_cannot_spend_or_overfill_full_shelf(self):
        j = self.shop(1)
        self.lot(j, 'jelly', 90)
        boba.state(j.c)['event'] = dict(id='test-delivery', kind='short_delivery', stage='open',
                                        facts=dict(item='jelly', billed=10, got=7, cost=2, _honest=True))
        before = copy.deepcopy(j.c)
        with self.assertRaises(GameError):
            boba._answer(j.state, j.c, boba.state(j.c), dict(choice='count'))
        self.assertEqual(j.c, before)

    def test_promised_stock_waits_for_room_without_disappearing(self):
        j = self.shop(1)
        self.lot(j, 'jelly', 90)
        b = boba.state(j.c)
        promise = dict(kind='portions', day=j.c['day'], item='jelly', qty=3, ref='old-delivery', _honest=True)
        b['promises'] = [promise]
        b['day'] = 0
        boba.on_start(j.state, j.c)
        self.assertEqual(b['promises'], [promise])
        self.assertEqual(boba.held(j.c)['jelly'], 90)

    def test_public_freshness_groups_identical_display_rows_without_merging_saves(self):
        j = self.shop(10)
        j.c['life']['pantry'] = [dict(id=f'lot-{n}', item='milk', qty=1, unit_cost=2,
                                     expires=j.c['day'] + 2, received=j.c['day'], made=boba.opening_abs(j.c))
                                for n in range(3000)]
        before = copy.deepcopy(j.c['life']['pantry'])
        rows = next(row for row in boba.public(j.c)['batches'] if row['item'] == 'milk')['lots']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['qty'], 3000)
        self.assertEqual(j.c['life']['pantry'], before)

    def test_public_pantry_groups_each_ingredient_by_expiry(self):
        j = self.shop(10)
        j.c['life']['pantry'] = [dict(id=f'lot-{n}', item='jelly', qty=1, unit_cost=2,
                                     expires=j.c['day'] + 1 + n % 2, received=j.c['day']) for n in range(3000)]
        before = copy.deepcopy(j.c['life']['pantry'])
        rows = experiences.public_life(j.c)['pantry']
        self.assertEqual(rows, [dict(item='jelly', qty=1500, expires=j.c['day'] + n) for n in (1, 2)])
        self.assertEqual(j.c['life']['pantry'], before)

    @unittest.skipUnless(shutil.which('node'), 'node is needed to render storage controls')
    def test_prepare_screen_respects_paid_capacity_and_incoming_reservations(self):
        j = self.shop(1)
        self.lot(j, 'milk', 80)
        boba._place(j.state, j.c, boba.state(j.c), 'milk', 10, boba.SUP_INDEX['partner'], 0, 2, 'Test')
        script = """
import {readFileSync} from 'node:fs';
import tea from './public/js/careers/milk_tea.js';
import {careerContext} from './public/js/v4/careers.js';
const {state,content}=JSON.parse(readFileSync(0,'utf8'));
const x=careerContext({api:{state,content},ui:{}});
process.stdout.write(tea.page('prepare',x));
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script],
                                input=json.dumps(dict(state=public_state(j.state), content=public_content())),
                                text=True, encoding='utf-8', capture_output=True,
                                cwd=Path(__file__).resolve().parents[1], timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Kho đầy 90/90', result.stdout)


if __name__ == '__main__':
    unittest.main()
