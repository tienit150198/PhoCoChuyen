"""🚗 Biển 179 (owner 22/10, player feedback #476 "ok để biển số xe, thêm vào luôn nha"): road plates with 179 in them join
the auction's one-of-a-kind catalogue (game/auction_content.py FEATURED), priced by tier like the other nice numbers, go
up first in their tier's daily slot until FEATURE_TO, and once won work like any Biển đẹp (garage, +x %)."""
import datetime
import unittest

from game import auction as au
from game import auction_content as AC
from game import garage as gr
from game.engine import GameError
from tests.test_bank import act, story
from tests.test_vehicle_plates import rows, shift, win

LAST = datetime.date.fromisoformat(AC.FEATURE_TO)


class Catalogue(unittest.TestCase):
    def test_the_179_plates_are_ordinary_one_of_a_kind_plates(self):
        self.assertEqual(len(AC.FEATURED), 5)
        folded = [au.fold_plate(it['name']) for it in AC.ITEMS if it['kind'] in AC.PLATE_KINDS]
        self.assertEqual(len(folded), len(set(folded)))                      # no plate copies another
        for i in AC.FEATURED:
            it = AC.ITEM[i]
            self.assertEqual(it['kind'], 'plate')
            self.assertIn('179', au.fold_plate(it['name']))
            self.assertIn(it['tier'], (1, 2))                                  # nice numbers, not the legendary tier
            self.assertNotIn('start', it)                                     # the tier's price, like the others
            self.assertLessEqual(len(it['name']), 12)
            self.assertRegex(i, au.ITEM_RE)
            self.assertIn(au.fold_plate(it['name']), au.plates())            # a free biển tên may not copy it
        self.assertIn('pl_may0179', {x['id'] for x in au.catalogue()['items']})

    def test_a_free_name_plate_may_not_copy_one(self):
        s = story(2_000_000)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_garage_buy', id='xe_so', color='do', plate='51A 179 79', confirm=True)
        self.assertEqual(e.exception.code, 'taken')


class Schedule(unittest.TestCase):
    def test_they_go_up_first_until_the_window_ends(self):
        d = datetime.date(2026, 10, 23)
        taken, seen = set(), []
        while d <= LAST:
            for x in au.plan(d):
                it = au.pick(d, x['slot'], x['tier'], taken)
                if it and x['slot'] in (1, 2):
                    seen.append(it['id'])
                    if it['id'] in AC.FEATURED:
                        self.assertEqual(it['tier'], x['tier'])
            d += datetime.timedelta(days=1)
        self.assertTrue(seen and all(i in AC.FEATURED for i in seen))      # every 179 plate unsold: back on the block
        self.assertEqual(au.pick(LAST, 1, 1, set())['id'] in AC.FEATURED, True)
        after = LAST + datetime.timedelta(days=1)
        free1 = [it for it in AC.ITEMS if it['tier'] == 1 and it['kind'] != 'petgear']
        picks = {au.pick(after + datetime.timedelta(days=i), 1, 1, set())['id'] for i in range(60)}
        self.assertTrue(picks - set(AC.FEATURED))                            # after it: one lot among all again
        self.assertTrue(picks <= {it['id'] for it in free1})

    def test_sold_ones_leave_the_others(self):
        d = datetime.date(2026, 10, 25)
        t1 = [i for i in AC.FEATURED if AC.ITEM[i]['tier'] == 1]
        self.assertIn(au.pick(d, 1, 1, set(t1[:-1]))['id'], t1[-1:])
        self.assertNotIn(au.pick(d, 1, 1, set(t1))['id'], AC.FEATURED)     # all sold: the ordinary pool
        t2 = [i for i in AC.FEATURED if AC.ITEM[i]['tier'] == 2]
        self.assertIn(au.pick(d, 2, 2, set())['id'], t2)


class Garage(unittest.TestCase):
    def test_a_won_179_plate_rides_and_pays_like_any_plate(self):
        s = story(2_000_000)
        s, _ = act(s, 'jr_garage_buy', id='xe_so', confirm=True)
        self.assertIn('Gắn biển', win(s, 'pl_51a17979'))
        s, _ = act(s, 'jr_garage_plate', item='pl_51a17979', id='xe_so')
        s, _ = act(s, 'jr_garage_ride', id='xe_so')
        self.assertEqual(gr.my_plates(s)['pl_51a17979']['tier'], 2)
        s, r = shift(s, 1000)
        pct = AC.PLATE_PCT['bike'][1]
        self.assertEqual(r['summary']['journey']['plate_pct'], pct)
        self.assertEqual(rows(s), [r['summary']['net'] * pct // 100])
        row = next(x for x in gr.public(s)['cars'] if x['id'] == 'xe_so')
        self.assertEqual((row['uq']['t'], row['uq']['pct']), ('51A-179.79', pct))   # shown in gold on the vehicle


if __name__ == '__main__':
    unittest.main()
