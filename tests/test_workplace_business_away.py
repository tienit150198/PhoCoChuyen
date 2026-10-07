"""B4 (backlog 6, F#243 / F#247): "Lúc bạn vắng". Staff orders keep a running total of the items they took
(ops.business_used, optional); the page shows the difference since the player's last look. Expiry, a theft or the
owner's own work never move it, so the report can say "nhân viên đã bán", never "hết hạn"."""
import copy
import unittest
from unittest.mock import patch

from game import inventory as inv
from game import operations as ops
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


def shelf(c, career):
    return {x['id']: inv.count(c, x['id']) for x in inv.catalogue(career)}


class AwayUsage(unittest.TestCase):
    def test_bakery_totals_match_what_left_the_shelf(self):
        s, c = sample('cafe_bakery')
        self.assertNotIn('business_used', c['ops'])            # created by the first order, not by hiring
        before = shelf(c, 'cafe_bakery')
        wb.settle(s, first_due(c) + 6 * 3600)                    # a night away
        b = c['ops']['business']
        self.assertGreater(b['served'], 5)
        after = shelf(c, 'cafe_bakery')
        gone = {i: before[i] - after[i] for i in before if before[i] != after[i]}
        self.assertEqual(c['ops']['business_used'], gone)        # every unit that left went with an order
        self.assertEqual(c['ops']['business_used'].get('cup'), b['served'])   # one cup an order (F#247)
        used = wb.public(c)['used']
        self.assertEqual({i: q for i, _, q in used}, gone)
        self.assertEqual(dict((i, n) for i, n, _ in used)['cup'], wb._item_names('cafe_bakery')['cup'])
        self.assertEqual([q for *_, q in used], sorted((q for *_, q in used), reverse=True))
        ops.validate(c, 'cafe_bakery')
        validate_state(s)

    def test_clothing_counts_each_piece_sold(self):
        s, c = sample('clothing')
        wb.settle(s, first_due(c) + 3 * 3600)
        n = c['ops']['business']['served']
        self.assertGreater(n, 2)
        self.assertEqual(sum(c['ops']['business_used'].values()), n)  # one piece an order
        validate_state(s)

    def test_expiry_theft_and_owner_use_do_not_count(self):
        s, c = sample('grocery')
        wb.settle(s, first_due(c))
        used = copy.deepcopy(c['ops']['business_used'])
        for lot in c['ext']['inv']['lots']:
            lot['qty'] = max(0, lot['qty'] - 1)                  # lost to expiry / theft / the owner's own basket
        wb.settle(s, first_due(c) - 1)                           # nothing due: nothing counted
        self.assertEqual(c['ops']['business_used'], used)

    def test_services_without_goods_have_no_totals(self):
        s, c = sample('accounting')
        wb.settle(s, first_due(c) + 3600)
        self.assertGreater(c['ops']['business']['served'], 0)
        self.assertNotIn('business_used', c['ops'])
        self.assertNotIn('used', wb.public(c))
        validate_state(s)

    def test_milk_tea_names_its_boba_inputs(self):
        from game import boba
        s, c = sample('milk_tea')
        c['life']['pantry'] = [dict(id='one', item='milk', qty=1, unit_cost=4, expires=3, received=1)]
        boba.state(c)['cups']['M'] = 1
        wb.settle(s, first_due(c) + 10000)
        names = {i: n for i, n, _ in wb.public(c)['used']}
        self.assertEqual(names, {'milk': 'Sữa tươi', 'cup_M': 'Ly size M'})

    def test_public_is_read_only_and_saves_without_totals_stay_valid(self):
        s, c = sample('cafe_bakery')
        wb.settle(s, first_due(c) + 3600)
        snap = copy.deepcopy(s)
        wb.public(c)
        self.assertEqual(s, snap)
        old = copy.deepcopy(s)
        old['careers']['cafe_bakery']['ops'].pop('business_used')    # a save from 1.9.16 or older
        validate_state(old)
        self.assertNotIn('used', wb.public(old['careers']['cafe_bakery']))

    def test_corrupt_totals_are_rejected(self):
        s, c = sample('cafe_bakery')
        wb.settle(s, first_due(c) + 3600)
        for bad in ([], {'cup': 0}, {'cup': -1}, {'cup': 1.5}, {'cup': True}, {'': 1}, {'x' * 81: 1},
                    {f'i{k}': 1 for k in range(wb.USED_ITEMS + 1)}, {'cup': wb.LIMIT + 1}):
            with self.subTest(bad=str(bad)[:40]):
                t = copy.deepcopy(c); t['ops']['business_used'] = bad
                with self.assertRaises(GameError):
                    ops.validate(t, 'cafe_bakery')

    def test_totals_are_bounded(self):
        c = {'ops': {'business_used': {f'i{k}': 1 for k in range(wb.USED_ITEMS)}}}
        wb._count_used(c, {'new': 1, 'i0': 2})
        self.assertNotIn('new', c['ops']['business_used'])          # a full table keeps counting what it has
        self.assertEqual(c['ops']['business_used']['i0'], 3)
        c['ops']['business_used']['i1'] = wb.LIMIT
        wb._count_used(c, {'i1': 5})
        self.assertEqual(c['ops']['business_used']['i1'], wb.LIMIT)


if __name__ == '__main__':
    unittest.main()
