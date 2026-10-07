"""B4 part 2 (F#243 / F#247, owner 07/10 "làm theo ý bạn"): "Giữ lại cho ca của tôi". An optional per-item floor
(ops.business_keep at a workplace, business['keep'] at a counter): staff stop selling an item once its stock is down
to it and say why; the owner still uses every unit. No floor (the default) changes nothing."""
import copy
import unittest
from unittest.mock import patch

from game import inventory as inv
from game import operations as ops
from game import player_service_tasks as pst
from game import staff_orders
from game import workplace_business as wb
from game.engine import GameError, new_state, validate_state


def sample(career):
    s = new_state(); c = s['careers'][career]; c.update(open=True, started=True)
    with patch.object(wb.time, 'time', return_value=2000000000):
        ops.action(s, c, career, 'ops_hire', {'candidate': f'{career}-staff-1', 'confirm': True})
        wb.settle(s)
    c['ops']['finance']['opening_balance'] += 100000 - c['money']; c['money'] = 100000
    return s, c


def first_due(c):
    return min(x['at'] for x in c['ops']['business']['pending'].values())


def keep(s, c, career, item, qty):
    return ops.action(s, c, career, 'ops_keep', {'item': item, 'qty': qty})


class WorkplaceKeep(unittest.TestCase):
    def test_bakery_stops_at_the_floor_and_says_why(self):
        s, c = sample('cafe_bakery')
        cups = inv.count(c, 'cup')
        msg = keep(s, c, 'cafe_bakery', 'cup', cups - 3)['message']
        self.assertEqual(msg, f'🔒 Giữ {cups - 3} cho ca của bạn.')
        self.assertEqual(c['ops']['business_keep'], {'cup': cups - 3})
        wb.settle(s, first_due(c) + 8 * 3600)                     # a night away
        b = c['ops']['business']
        self.assertEqual(b['served'], 3)                           # one cup an order, three above the floor
        self.assertEqual(inv.count(c, 'cup'), cups - 3)
        self.assertEqual(b['reason'], 'stock')
        out = wb.public(c)
        self.assertTrue(out['reason_text'].startswith(f'🔒 Giữ {cups - 3} ly giấy + nắp cho ca của bạn.'))
        self.assertEqual(out['kept'], [['cup', 'Ly giấy + nắp', cups - 3]])
        self.assertIn('cup', out['keepable'])
        self.assertFalse(wb.due(s, first_due(c) if b['pending'] else 2100000000))   # a stopped team needs no writes
        inv.take(c, 'cup', 2)                                      # the owner's own shift still uses the kept cups
        self.assertEqual(inv.count(c, 'cup'), cups - 5)
        validate_state(s)
        # Lower the floor: the team picks up again from now, never for the time it stood still.
        keep(s, c, 'cafe_bakery', 'cup', 0)
        self.assertNotIn('business_keep', c['ops'])
        self.assertEqual(c['ops']['business']['reason'], 'working')
        wb.settle(s, first_due(c))
        self.assertEqual(c['ops']['business']['served'], 4)

    def test_no_floor_changes_nothing(self):
        s, c = sample('cafe_bakery')
        other = copy.deepcopy(s)
        keep(s, c, 'cafe_bakery', 'cup', 7)
        keep(s, c, 'cafe_bakery', 'cup', 0)                        # set and cleared: the key is gone again
        self.assertEqual(s, other)
        at = first_due(c) + 5 * 3600
        wb.settle(s, at); wb.settle(other, at)
        self.assertEqual(s, other)
        self.assertNotIn('kept', wb.public(c))

    def test_menu_weights_count_only_what_is_above_the_floor(self):
        s, c = sample('grocery')
        cash = wb._cash(c, 'grocery', c['ops']['staff'][0])
        before = {r[2].get('rice') and r[0]: r[3] for r in staff_orders.menu(c, 'grocery', cash)}
        have = staff_orders._available(c, 'grocery', 'rice')
        c['ops']['business_keep'] = {'rice': have - 2}
        rows = [r for r in staff_orders.menu(c, 'grocery', cash) if 'rice' in r[2]]
        self.assertTrue(all(r[2]['rice'] <= 2 for r in rows))
        self.assertTrue(all(r[3] <= 2 for r in rows))
        self.assertTrue(any(w > 2 for k, w in before.items() if k))
        c['ops']['business_keep'] = {'rice': have}
        self.assertFalse([r for r in staff_orders.menu(c, 'grocery', cash) if 'rice' in r[2]])
        self.assertEqual(staff_orders._available(c, 'grocery', 'rice', floor=False), have)
        # Sales go on with the other goods and never touch the kept rice.
        wb.settle(s, first_due(c) + 3 * 3600)
        self.assertGreater(c['ops']['business']['served'], 0)
        self.assertEqual(staff_orders._available(c, 'grocery', 'rice', floor=False), have)

    def test_clothing_keeps_a_spread_of_sizes_and_sells_the_rest(self):
        from game.careers import clothing
        s, c = sample('clothing')
        clothing._sync(c)
        tee = inv.count(c, 'tee')
        keep(s, c, 'clothing', 'tee', 4)
        wb.settle(s, first_due(c) + 3 * 3600)
        rows = c['ops']['business_clothing_receipts']
        self.assertGreater(len(rows), 4)
        self.assertEqual(inv.count(c, 'tee'), 4)                   # the rotation sold tees down to the floor only
        self.assertGreater(sum(c['ops']['business_used'].values()), tee - 4)   # other goods kept selling
        grid = c['ext']['data']['grid']['tee']
        self.assertEqual(sum(grid.values()), 4)
        self.assertGreaterEqual(sum(1 for n in grid.values() if n), 3)   # sold from the fullest size: not 4 × M
        self.assertIsNone(clothing.staff_size(c, 'tee', 4))
        self.assertIsNotNone(clothing.staff_size(c, 'tee'))       # the owner's own picker still sees them
        validate_state(s)

    def test_default_size_pick_is_unchanged(self):
        from game.careers import clothing
        s, c = sample('clothing')
        clothing._sync(c)
        for item in clothing.ITEM:
            self.assertEqual(clothing.staff_size(c, item, 0), clothing.staff_size(c, item))

    def test_visiting_players_buy_only_above_the_floor(self):
        s, c = sample('grocery')
        self.assertTrue(pst.staff_offers(s, 'grocery'))
        keep(s, c, 'grocery', 'rice', staff_orders._available(c, 'grocery', 'rice', floor=False))
        self.assertEqual(pst.staff_offers(s, 'grocery'), [])       # the authored visitor order is one bag of rice

    def test_counter_desks_and_milk_tea(self):
        from game import boba
        s, c = sample('mother_baby')
        item = next(iter(c['stock']))
        keep(s, c, 'mother_baby', item, c['stock'][item])
        self.assertEqual(staff_orders._available(c, 'mother_baby', item), 0)
        wb.settle(s, first_due(c) + 6 * 3600)
        self.assertEqual(c['stock'][item], c['ops']['business_keep'][item])
        s, c = sample('milk_tea')
        c['life']['pantry'] = [dict(id='one', item='milk', qty=4, unit_cost=4, expires=3, received=1)]
        boba.state(c)['cups']['M'] = 3
        keep(s, c, 'milk_tea', 'cup_M', 1)
        wb.settle(s, first_due(c) + 10000)
        self.assertEqual(boba.view(c)['cups']['M'], 1)
        self.assertEqual(c['ops']['business']['served'], 2)
        self.assertEqual(wb.public(c)['reason_text'], '🔒 Giữ 1 ly size M cho ca của bạn. Bỏ giữ hoặc nhập thêm để đội bán tiếp.')

    def test_command_rules(self):
        s, c = sample('cafe_bakery')
        for bad in ({'item': 'cup', 'qty': -1}, {'item': 'cup', 'qty': 1000}, {'item': 'cup', 'qty': 1.0},
                    {'item': 'cup', 'qty': True}, {'item': 'cup'}, {'item': 'nope', 'qty': 1}, {'item': 3, 'qty': 1}):
            with self.subTest(bad=bad), self.assertRaises(GameError):
                ops.action(s, c, 'cafe_bakery', 'ops_keep', bad)
        self.assertNotIn('business_keep', c['ops'])
        s, a = sample('accounting')                                # a service: staff take no goods
        with self.assertRaises(GameError):
            ops.action(s, a, 'accounting', 'ops_keep', {'item': 'cup', 'qty': 1})
        money = c['money']
        keep(s, c, 'cafe_bakery', 'milk', 999)
        self.assertEqual(c['money'], money)

    def test_saves_with_and_without_the_key(self):
        s, c = sample('cafe_bakery')
        keep(s, c, 'cafe_bakery', 'cup', 5)
        validate_state(s)
        old = copy.deepcopy(s); old['careers']['cafe_bakery']['ops'].pop('business_keep')
        validate_state(old)                                         # a 1.9.17 save
        for bad in ([], {'cup': -1}, {'cup': 1000}, {'cup': 1.5}, {'cup': True}, {'': 1}, {'x' * 81: 1},
                    {f'i{k}': 1 for k in range(wb.USED_ITEMS + 1)}):
            with self.subTest(bad=str(bad)[:40]):
                t = copy.deepcopy(c); t['ops']['business_keep'] = bad
                with self.assertRaises(GameError):
                    ops.validate(t, 'cafe_bakery')


class CounterKeep(unittest.TestCase):
    def fixture(self):
        from tests.test_quay_business import fixture
        from game import quay_business as qb
        s, st = fixture()
        qb.settle(s, now=1000)
        return s, st, qb

    def test_staff_stop_at_the_floor_and_the_owner_keeps_it(self):
        s, st, qb = self.fixture()
        b = st['business']
        dish = max(b['stock'], key=lambda d: b['stock'][d])
        floor = b['stock'][dish]
        r = qb.action(s, st, 'jr_quay_keep', {'stall': st['id'], 'dish': dish, 'qty': floor})
        self.assertIn('cho ca của bạn', r['message'])
        qb.settle(s, now=100000000)
        self.assertEqual(b['stock'][dish], floor)
        self.assertEqual(qb.status(st), 'out_of_stock')
        out = qb.public(st)
        self.assertEqual(out['kept'], [[dish, floor]])
        self.assertTrue(out['reason'].startswith(f'🔒 Giữ {floor} '))
        self.assertEqual(next(x for x in out['stock'] if x['id'] == dish)['keep'], floor)
        from game import quay
        quay.validate(s)
        qb.action(s, st, 'jr_quay_keep', {'stall': st['id'], 'dish': dish, 'qty': 0})
        self.assertNotIn('keep', b)
        qb.settle(s, now=100000000 + 3600 * 1000)
        self.assertLess(b['stock'][dish], floor)

    def test_no_floor_changes_nothing_and_rules(self):
        s, st, qb = self.fixture()
        other = copy.deepcopy(s)
        dish = next(iter(st['business']['stock']))
        qb.action(s, st, 'jr_quay_keep', {'stall': st['id'], 'dish': dish, 'qty': 3})
        qb.action(s, st, 'jr_quay_keep', {'stall': st['id'], 'dish': dish, 'qty': 0})
        self.assertEqual(s, other)
        qb.settle(s, now=50000); qb.settle(other, now=50000)
        self.assertEqual(s, other)
        for bad in ({'dish': 'nope', 'qty': 1}, {'dish': dish, 'qty': -1}, {'dish': dish, 'qty': 1000},
                    {'dish': dish, 'qty': '2'}, {'dish': dish, 'qty': 1, 'x': 1}):
            with self.subTest(bad=bad), self.assertRaises(GameError):
                qb.action(s, st, 'jr_quay_keep', {'stall': st['id'], **bad})
        from game import quay
        for bad in ([], {'nope': 1}, {dish: -1}, {dish: 1000}, {dish: 1.5}):
            with self.subTest(bad=bad):
                t = copy.deepcopy(st); t['business']['keep'] = bad
                with self.assertRaises(Exception):
                    quay.validate({'journey': {**s['journey'], 'quay': {**s['journey']['quay'], 'stalls': [t]}}})


if __name__ == '__main__':
    unittest.main()
