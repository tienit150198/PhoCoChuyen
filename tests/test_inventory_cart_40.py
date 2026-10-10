"""Feedback #324: forty item/size lines, with the existing stock and payment safeguards."""
import copy
import json
import unittest

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

    def test_forty_sizes_survive_save_and_place_as_one_order(self):
        self.fill()
        self.assertEqual(public_inv(self.j)['cart_lines'], 40)
        self.assertEqual(len(cart(self.j)['lines']), 40)
        validate_state(json.loads(json.dumps(self.j.state)))
        self.assertLessEqual(len(self.j.c['ext']['inv']['cart']['partner']['lines']), 8)
        money = self.j.c['money']
        r, gid = place(self.j)
        ordered = group_lines(self.j, gid)
        held = (cart(self.j) or {}).get('lines', [])
        self.assertEqual(len(ordered) + len(held), 40)
        self.assertGreater(len(ordered), 20)
        self.assertEqual(len(books(self.j, gid)), 1, 'one payment for a merged order')
        self.assertEqual(money - self.j.c['money'], -books(self.j, gid)[0]['amount'])
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
