"""Feedback #324/#333: forty item/size lines, preserving stock and payment safeguards."""
import copy
import json
import unittest
from unittest.mock import patch

from game import inventory as I
from game.careers import clothing
from game.engine import GameError, validate_state
from tests.helpers import Journey
from tests.test_inventory_cart import cart, group_lines, books, place
from tests.test_inventory_flow import empty, public_inv, set_money


class FortyLineClothingDraft(unittest.TestCase):
    def setUp(self):
        self.j = Journey('clothing')
        self.j.c['xp'] = 900
        set_money(self.j.c, 100000)
        self.lines = [dict(item=i['id'], size=z, qty=1)
                      for i in I.catalogue('clothing')
                      for z in clothing.SIZES[i['id']]][:41]
        self.assertEqual(len(self.lines), 41)
        for item in {l['item'] for l in self.lines}:
            empty(self.j.c, item)

    def fill(self):
        self.j.act('inv_cart', supplier='partner', op='add', lines=self.lines[:40])

    def test_forty_sizes_survive_save_with_one_out_of_stock(self):
        self.fill()
        self.assertEqual(public_inv(self.j)['cart_lines'], 40)
        self.assertEqual(len(cart(self.j)['lines']), 40)
        self.j.state = json.loads(json.dumps(self.j.state))
        validate_state(self.j.state)
        self.assertLessEqual(len(self.j.c['ext']['inv']['cart']['partner']['lines']), 8)
        money = self.j.c['money']
        r, gid = place(self.j)
        ordered = group_lines(self.j, gid)
        held = (cart(self.j) or {}).get('lines', [])
        self.assertEqual((len(ordered), len(held)), (39, 1))
        self.assertEqual(held[0]['item'], r['oos'])
        self.assertTrue(held[0]['oos'])
        self.assertEqual(len(books(self.j, gid)), 1, 'one payment for a merged order')
        self.assertEqual(money - self.j.c['money'], -books(self.j, gid)[0]['amount'])
        self.assertEqual(money - self.j.c['money'], sum(o['cost'] + o.get('ship', 0) for o in ordered))
        validate_state(self.j.state)

    def test_all_forty_sizes_ship_in_one_group_for_one_exact_payment(self):
        self.fill()
        self.j.state = json.loads(json.dumps(self.j.state))
        validate_state(self.j.state)
        quoted_total = cart(self.j)['total']
        money = self.j.c['money']
        # Isolate the full-stock outcome while keeping pricing, ordering and payment real.
        with patch.dict(I.supplier('clothing', 'partner'), oos=0):
            result, gid = place(self.j)
        ordered = self.j.c['ext']['inv']['orders']
        self.assertEqual(len(ordered), 40)
        self.assertEqual({o['group'] for o in ordered}, {gid})
        self.assertCountEqual(
            [(o['item'], o['size'], o['qty']) for o in ordered],
            [(l['item'], l['size'], l['qty']) for l in self.lines[:40]],
        )
        self.assertIsNone(result['oos'])
        self.assertIsNone(cart(self.j))
        self.assertEqual(len(books(self.j, gid)), 1)
        self.assertEqual(books(self.j, gid)[0]['amount'], -quoted_total)
        self.assertEqual(money - self.j.c['money'], quoted_total)
        self.assertEqual(sum(o['cost'] + o.get('ship', 0) for o in ordered), quoted_total)
        validate_state(self.j.state)

    def test_forty_first_size_is_rejected_without_changing_the_draft(self):
        self.fill()
        before = copy.deepcopy(self.j.state)
        with self.assertRaises(GameError) as error:
            self.j.act('inv_cart', supplier='partner', op='add', **self.lines[40])
        self.assertIn('tối đa 40 món', error.exception.message)
        self.assertEqual(self.j.state, before)


if __name__ == '__main__':
    unittest.main()
