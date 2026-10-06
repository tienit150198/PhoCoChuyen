"""Tiệm Áo Chỉ Mây, 1.7.16: the new goods (góp ý #191), the customers' extra wishes that ask for them,
and talking through a bill over the budget instead of a flat refusal (góp ý #199)."""
import unittest

from game.engine import GameError
from game.careers import kit
from tests.test_career_clothing import A, job, roundtrip, slip_codes, bill_and_pay, pay_exact


def stock_new(j, item, n=6):
    """Goods of 1.7.16 arrive (inventory → on_receive fills the size, the grid row appears)."""
    for size in A.SIZES[item]:
        A.on_receive(j.c, dict(item=item, size=size, actual=n))
        kit.add_lot(j.c, item, n, A.ITEM[item]['cost'], 999, 'test')
    A._sync(j.c)


def outfit_over(j, extra=30):
    """An outfit whose one-piece costs the budget + `extra` (the shop's own price tag)."""
    t = j.task
    j.c['life']['prices']['dress'] = A._base_budget(t) + extra
    top = t['needs']['top'] if t['needs']['top'] in A.SIZES['dress'] else 'L'
    j.act('ao_pick', task=t['id'], item='dress', size=top, colour='xanh mint')
    return t['id']


def regular(t):
    return A._npc_index(t) in A.CALL


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingCatalogueTests(unittest.TestCase):
    def test_new_goods_are_complete(self):
        new = [x['id'] for x in A.ITEMS if x['id'] not in A.LEGACY]
        self.assertGreaterEqual(len(new), 12)
        self.assertGreaterEqual(sum(A.GROUP[i] == 'one' for i in A.ITEM), 6)
        for i in A.ITEM:
            self.assertIn(i, A.PRICES)
            self.assertIn(i, A.SIZES)
            self.assertEqual(set(A.FILL[i]), set(A.SIZES[i]), i)
            self.assertTrue(A.COLOURS[i], i)
            for col in A.COLOURS[i]:
                self.assertIn(col, A.SWATCH, (i, col))
            self.assertGreater(A.PRICES[i], A.ITEM[i]['cost'], i)
        for occ in A.OCCASIONS.values():
            for main in occ['mains']:
                self.assertTrue(all(x in A.ITEM for x in main))
            for key in ('plus', 'odd', 'need'):
                self.assertTrue(all(x in A.ITEM for x in occ[key]))
        for npc, items in A.ADDON.items():
            self.assertTrue(all(x in A.ITEM and x not in A.LEGACY for x in items), npc)

    def test_new_goods_sell_and_survive_a_roundtrip(self):
        j = job('fit')
        t = j.task
        self.assertNotIn('maxi', j.c['ext']['data']['grid'])
        with self.assertRaises(GameError):      # nothing on the rack yet: order it first
            j.act('ao_pick', task=t['id'], item='maxi', size='M', colour='trắng')
        stock_new(j, 'maxi')
        self.assertEqual(sum(j.c['ext']['data']['grid']['maxi'].values()), kit.stock(j.c, 'maxi'))
        roundtrip(j)
        j.act('ao_pick', task=t['id'], item='maxi', size='M', colour='trắng')
        self.assertEqual(j.get(t['id'])['picks'][-1]['item'], 'maxi')

    def test_new_occasion_sets(self):
        self.assertEqual(A._judge(A.OCCASIONS['interview'], [('blazer', 'đen'), ('trousers', 'đen')]), [])
        self.assertEqual(A._judge(A.OCCASIONS['beach'], [('maxi', 'xanh biển'), ('hat', 'cói'), ('sandal', 'nâu')]), [])
        self.assertEqual(A._judge(A.OCCASIONS['tet'], [('set2', 'hồng phấn')]), [])
        self.assertIn('colour_taboo', [r[0] for r in A._judge(A.OCCASIONS['wedding'], [('maxi', 'trắng')])])
        self.assertIn('odd_piece', [r[0] for r in A._judge(A.OCCASIONS['interview'],
                                                            [('shirt', 'trắng'), ('trousers', 'đen'), ('sandal', 'nâu')])])

    def test_new_sizes_follow_their_clues(self):
        t = dict(kind='outfit', needs=dict(top='M', waist='29'), wish=dict(kind='shoes', say='x', foot='37', extra=A.SHOE_EXTRA))
        self.assertEqual(A._want_size(t, dict(item='trousers', colour='đen')), '29')
        self.assertEqual(A._want_size(t, dict(item='sandal', colour='nâu')), '37')
        self.assertIsNone(A._want_size(t, dict(item='bag', colour='đen')))
        self.assertTrue(A._free_size('earrings'))
        self.assertEqual(A._base_budget(t | dict(needs=dict(budget=400))), 400 + A.SHOE_EXTRA)


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingWishTests(unittest.TestCase):
    def setUp(self):
        self.chance = A.WISH_CHANCE
        A.WISH_CHANCE = 1.0

    def tearDown(self):
        A.WISH_CHANCE = self.chance

    def _fit(self):
        return job('fit', lambda t: len(t['needs']['lines']) < A.MAX_PICKS and regular(t), days=range(2, 40))

    def test_fit_addon_is_asked_and_billed(self):
        j = self._fit()
        t = j.task
        t.pop('wish', None)
        A.on_task(j.state, j.c, t)                  # a known task never gets a wish afterwards
        self.assertNotIn('wish', t)
        t.update(known=False, status='new')
        A.on_task(j.state, j.c, t)
        t.update(known=True, status='understood')
        w = t['wish']
        self.assertEqual(w['kind'], 'addon')
        self.assertIn('À mà em ơi', A.known_request(j.c, t))
        self.assertNotIn('_size', A.public_task(t)['wish']['line'])
        self.assertNotIn('wish', A.public_task(dict(t, known=False)))
        stock_new(j, w['line']['item'])
        for ln in t['needs']['lines']:
            j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
        with self.assertRaises(GameError):      # the add-on is on the rack: the customer wants it
            j.act('ao_bill', task=t['id'])
        ln = w['line']
        j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
        bill_and_pay(j, t['id'])
        done = j.get(t['id'])
        self.assertEqual(done['status'], 'completed')
        self.assertEqual(slip_codes(done), [])
        roundtrip(j)

    def test_fit_addon_sold_out_is_not_a_mistake(self):
        j = self._fit()
        t = j.task
        t['wish'] = A.make_wish(j.c, dict(t, known=False))
        self.assertEqual(t['wish']['kind'], 'addon')
        for ln in t['needs']['lines']:
            j.act('ao_pick', task=t['id'], item=ln['item'], size=ln['_size'], colour=ln['colour'])
        bill_and_pay(j, t['id'])
        done = j.get(t['id'])
        self.assertTrue(done['wish']['skipped'])
        self.assertEqual(slip_codes(done), [])
        self.assertTrue(any('nhập về bán' in x['text'] for x in j.c['ext']['data']['notes']))

    def test_outfit_wish_needs_stock_and_is_judged(self):
        j = job('outfit', lambda t: t['needs']['occasion'] == 'interview' and regular(t), days=range(2, 40))
        t = j.task
        self.assertIsNone(A.make_wish(j.c, dict(t, known=False)))   # no trousers, skirts or bags yet: no such wish
        stock_new(j, 'trousers')
        w = A.make_wish(j.c, dict(t, known=False))
        self.assertEqual(w['kind'], 'no_jeans')
        t['wish'] = w
        top, waist = t['needs']['top'], t['needs']['waist']
        for item, size, colour in (('shirt', top, 'trắng'), ('jeans', waist, 'đen')):
            j.act('ao_pick', task=t['id'], item=item, size=size, colour=colour)
        bill_and_pay(j, t['id'])
        self.assertIn('wish_miss', slip_codes(j.get(t['id'])))
        rows = {r['key']: r for r in A.feedback(j.c, j.get(t['id']))['criteria']}
        self.assertEqual(rows['wish']['score'], 2)

    def test_bad_wish_is_refused_by_validation(self):
        j = self._fit()
        j.task['wish'] = dict(kind='shoes', say='x', foot='37', extra=A.SHOE_EXTRA)   # an outfit wish on a fit task
        with self.assertRaises(GameError):
            roundtrip(j)


@unittest.skipIf(A is None, 'clothing filtered out')
class ClothingBudgetTalkTests(unittest.TestCase):
    def setUp(self):
        self.flex = A._flex

    def tearDown(self):
        A._flex = self.flex

    def _over(self, extra=30):
        j = job('outfit', lambda t: regular(t) and t['needs']['occasion'] in ('wedding', 'tet'), days=range(2, 40))
        j.task.pop('wish', None)
        tid = outfit_over(j, extra)
        r = j.act('ao_bill', task=tid)
        self.assertTrue(r.get('refused'))
        self.assertIn('Trao đổi', r['message'])
        self.assertEqual(slip_codes(j.get(tid)), [])
        self.assertEqual(A.public_task(j.get(tid))['talk_view']['off'], extra)
        return j, tid

    def test_swap_then_cheaper_set_is_clean(self):
        j, tid = self._over()
        j.act('ao_talk', task=tid, answer='swap')
        j.c['life']['prices']['dress'] = A.PRICES['dress']
        bill_and_pay(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertNotIn('over_budget', slip_codes(t))
        rows = {r['key']: r for r in A.feedback(j.c, t)['criteria']}
        self.assertEqual(rows['budget']['score'], 5)

    def test_swap_promise_broken_is_a_slip(self):
        j, tid = self._over()
        j.act('ao_talk', task=tid, answer='swap')
        r = j.act('ao_bill', task=tid)
        self.assertTrue(r.get('refused'))
        self.assertIn('over_budget', slip_codes(j.get(tid)))

    def test_raise_within_the_hidden_stretch(self):
        A._flex = lambda t: 25
        j, tid = self._over(30)
        r = j.act('ao_talk', task=tid, answer='raise')
        self.assertFalse(r.get('refused'))
        self.assertEqual(j.get(tid)['talk']['state'], 'raised')
        bill_and_pay(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertNotIn('over_budget', slip_codes(t))
        rows = {r['key']: r for r in A.feedback(j.c, t)['criteria']}
        self.assertEqual(rows['budget']['score'], 4)
        roundtrip(j)

    def test_raise_refused_then_nagging_is_pushy(self):
        A._flex = lambda t: 0
        j, tid = self._over(30)
        before = j.get(tid)['patience']
        r = j.act('ao_talk', task=tid, answer='raise')
        self.assertTrue(r.get('refused'))
        self.assertLess(j.get(tid)['patience'], before)
        self.assertEqual(slip_codes(j.get(tid)), [])
        self.assertTrue(A.public_task(j.get(tid))['talk_view']['asked'])
        r = j.act('ao_talk', task=tid, answer='raise')
        self.assertTrue(r.get('refused'))
        self.assertIn('pushy', slip_codes(j.get(tid)))

    def test_flex_is_hidden_seeded_and_mood_bound(self):
        j, tid = self._over()
        t = j.get(tid)
        a = A._flex(t)
        self.assertEqual(a, A._flex(t))
        lo, hi = A.FLEX[A._npc_index(t)]
        self.assertTrue(lo <= a <= hi)
        self.assertEqual(A._flex(dict(t, patience=30)), a // 2)
        self.assertNotIn('flex', str(A.public_task(t)['talk_view']))

    def test_discount_within_cap_bills_the_budget(self):
        j, tid = self._over(30)
        j.act('ao_talk', task=tid, answer='discount')
        j.act('ao_bill', task=tid)
        t = j.get(tid)
        self.assertEqual(t['bill']['off'], 30)
        self.assertEqual(t['bill']['total'], A._base_budget(t))
        self.assertIsNone(t['haggle'])
        pay_exact(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertNotIn('over_budget', slip_codes(j.get(tid)))
        roundtrip(j)

    def test_discount_over_cap_is_refused(self):
        j, tid = self._over(400)
        self.assertFalse(A.public_task(j.get(tid))['talk_view']['off_ok'])
        with self.assertRaises(GameError):
            j.act('ao_talk', task=tid, answer='discount')

    def test_decline_ends_the_visit(self):
        j, tid = self._over()
        j.act('ao_talk', task=tid, answer='decline')
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['result']['total'], 0)
        self.assertEqual(slip_codes(t), ['no_sale'])
        roundtrip(j)

    def test_talk_needs_a_frown(self):
        j = job('outfit', days=range(2, 40))
        with self.assertRaises(GameError):
            j.act('ao_talk', task=j.task['id'], answer='raise')

    def test_task_without_talk_or_wish_still_validates(self):
        j, tid = self._over()
        j.get(tid).pop('talk')
        roundtrip(j)


if __name__ == '__main__':
    unittest.main()
