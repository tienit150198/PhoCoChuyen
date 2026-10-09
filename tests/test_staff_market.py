"""📈 Staff-order market multiplier and 🔥 the hot career of the day (game/staff_market.py)."""
import copy
import datetime
import os
import unittest
from unittest import mock

from game import staff_market as sm, workplace_business as wb
from game.engine import new_state, public_state

T0 = 2000000000
ON = {'MNL_MARKET_OFF': '0'}


def receipts(c):
    return wb._recent(c)


class MarketCurve(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, ON); p.start(); self.addCleanup(p.stop)

    def test_same_value_for_the_same_career_and_time(self):
        for career in ('clothing', 'teacher', 'pho'):
            self.assertEqual([sm.market(career, T0 + i * 977) for i in range(200)],
                             [sm.market(career, T0 + i * 977) for i in range(200)])
        # Inside one 30-minute slot the value holds; careers have their own phases.
        slot = T0 // sm.SLOT * sm.SLOT
        self.assertEqual(sm.market('clothing', slot), sm.market('clothing', slot + sm.SLOT - 1))
        self.assertGreater(len({sm.market(c, T0) for c in sm.careers()}), 10)

    def test_bounds_and_smooth_steps(self):
        for career in sm.careers():
            v = [sm.market(career, T0 + i * sm.SLOT) for i in range(48 * 60)]
            self.assertGreaterEqual(min(v), sm.LOW); self.assertLessEqual(max(v), sm.HIGH)
            self.assertLessEqual(max(abs(b - a) / a for a, b in zip(v, v[1:])), 0.10, career)
            self.assertGreater(max(v) - min(v), 60, career)       # it does move

    def test_long_run_average_stays_at_the_base(self):
        # Four whole hot rotations (4 × 50 days): each career has 4 hot days, the rest is its market.
        days = 4 * len(sm.careers())
        start = datetime.datetime.combine(datetime.date.fromordinal(sm.EPOCH), datetime.time(), sm.VN).timestamp()
        for career in sm.careers():
            v = [sm.x(career, start + i * sm.SLOT * 3) for i in range(days * 16)]
            avg = sum(v) / len(v)
            self.assertLess(abs(avg - 100), 5, (career, avg))

    def test_off_switch(self):
        with mock.patch.dict(os.environ, {'MNL_MARKET_OFF': '1'}):
            self.assertEqual({sm.x(c, T0) for c in sm.careers()}, {100})
            self.assertIsNone(sm.hot(T0))


class HotRotation(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, ON); p.start(); self.addCleanup(p.stop)

    def test_deterministic_never_twice_in_a_row_and_a_full_cycle(self):
        n = len(sm.careers())
        days = [sm.hot_on(d) for d in range(n * 12)]
        self.assertEqual(days, [sm.hot_on(d) for d in range(n * 12)])
        self.assertTrue(all(a != b for a, b in zip(days, days[1:])))
        for k in range(12):
            self.assertEqual(sorted(days[k * n:(k + 1) * n]), sorted(sm.careers()), k)

    def test_the_day_follows_the_vietnam_calendar(self):
        midnight = datetime.datetime(2026, 10, 12, tzinfo=sm.VN).timestamp()
        self.assertEqual(sm.hot(midnight - 1), sm.hot_on(10))
        self.assertEqual(sm.hot(midnight), sm.hot_on(11))
        self.assertEqual(sm.hot(midnight + 86399), sm.hot_on(11))

    def test_hot_boost_only_for_that_career(self):
        for i in range(0, 48 * 30, 7):
            t = T0 + i * sm.SLOT
            h = sm.hot(t)
            self.assertTrue(sm.HOT_LOW <= sm.x(h, t) <= sm.HOT_HIGH)
            self.assertEqual(sm.x(h, t), max(sm.HOT_LOW, min(sm.HOT_HIGH, 2 * sm.market(h, t))))
            others = [sm.x(c, t) for c in sm.careers() if c != h]
            self.assertLess(max(others), sm.x(h, t))
            self.assertEqual(others, [sm.market(c, t) for c in sm.careers() if c != h])

    def test_public_state_carries_the_day(self):
        with mock.patch.object(sm, 'now', return_value=T0):
            v = public_state(new_state())['market']
        self.assertEqual(v['hot'], sm.hot(T0))
        self.assertEqual(set(v['x']), set(wb.ORDERS))
        self.assertGreaterEqual(v['x'][v['hot']], sm.HOT_LOW)


class StaffOrders(unittest.TestCase):
    def sample(self, career):
        from tests.test_workplace_business import WorkplaceBusinessTests
        return WorkplaceBusinessTests().sample(career)

    def run_orders(self, career, hot, market=100, n=12):
        with mock.patch.dict(os.environ, ON), mock.patch.object(sm, 'hot', return_value=hot), \
                mock.patch.object(sm, 'market', return_value=market):
            s, c, e = self.sample(career); c['money'] = 10**6
            for _ in range(n):
                wb.settle(s, min(p['at'] for p in c['ops']['business']['pending'].values()))
        return receipts(c)

    def margins(self, rows, career):
        return [r['revenue'] - r['cash_expenses'] - wb._replacement(career, r['items']) for r in rows]

    def test_hot_doubles_the_staff_margin_of_that_career_only(self):
        for career in ('accounting', 'clothing', 'grocery'):
            with self.subTest(career=career):
                normal = self.margins(self.run_orders(career, 'pho'), career)
                hot = self.margins(self.run_orders(career, career), career)
                self.assertTrue(all(m > 0 for m in normal))
                self.assertEqual(hot, [m * 2 for m in normal])
                low = self.margins(self.run_orders(career, 'pho', market=60), career)
                self.assertEqual(low, [m * 60 // 100 for m in normal])

    def test_clothing_staff_margin_is_in_the_normal_band(self):
        rows = self.run_orders('clothing', None, n=10)
        from game.careers import clothing
        for r, m in zip(rows, self.margins(rows, 'clothing')):
            item = next(iter(r['items']))
            shelf = clothing.PRICES[item] * (80 + 4 * r['stars']) // 100 - r['cash_expenses'] - clothing.ITEM[item]['cost']
            self.assertLessEqual(m, sm.CEIL * (80 + 4 * r['stars']) // 96)
            if shelf > 2 * sm.CEIL:
                self.assertLess(m * 2, shelf)        # was the whole shelf margin (~100 xu); now a capped share
            else:
                self.assertLessEqual(m, shelf)       # socks, a hat: a small margin stays (nearly) as it was
        # Per order, clothing now sits beside the other shops, not 10× an office job.
        office = self.margins(self.run_orders('accounting', None, n=10), 'accounting')
        self.assertLess(sum(self.margins(rows, 'clothing')) / len(rows), 4 * sum(office) / len(office))

    def test_small_margins_are_left_as_they_were(self):
        for m in range(-5, sm.KNEE + 1):
            self.assertEqual(sm.shape(m), m)
        self.assertEqual(sm.staff_revenue(18, 4, 5, 0), 18 * 96 // 100)
        self.assertEqual(sm.staff_revenue(10, 1, 9, 5), 10 * 84 // 100)   # a loss is never multiplied
        self.assertEqual(sm.staff_revenue(10, 1, 9, 5, 250), 10 * 84 // 100)

    def test_next_order_and_income_show_the_market(self):
        with mock.patch.dict(os.environ, ON), mock.patch.object(sm, 'hot', return_value='accounting'), \
                mock.patch.object(sm, 'market', return_value=100):
            s, c, e = self.sample('accounting')
            v = wb.public(c, T0)
            plain = copy.deepcopy(v['next_order'])
            self.assertTrue(v['market']['hot']); self.assertEqual(v['market']['x'], 200)
            self.assertEqual(len(v['market']['curve']), sm.SERIES)
        with mock.patch.dict(os.environ, {'MNL_MARKET_OFF': '1'}):
            off = wb.public(c, T0)['next_order']
        self.assertEqual(plain['margin'], 2 * off['margin'])


class OwnSalesUnchanged(unittest.TestCase):
    """The player's own sales never read the market: a hot ×2.5 day and a ×1.6 market change nothing."""

    def play(self, env, hot='clothing', market=160):
        from tests.helpers import Journey
        from tests.test_career_clothing import solve, A
        from game.careers import kit
        with mock.patch.dict(os.environ, env), mock.patch.object(sm, 'hot', return_value=hot), \
                mock.patch.object(sm, 'market', return_value=market):
            j = Journey('clothing')
            for _ in range(4):
                open_ = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred')]
                if not open_:
                    j.act('more_work'); open_ = [j.task]
                for it in A.ITEMS:
                    if min(j.c['ext']['data']['grid'].get(it['id'], {'F': 0}).values()) < 2 and kit.stock(j.c, it['id']) < A.CAPACITY - 8:
                        kit.add_lot(j.c, it['id'], 8, it['cost'], 999, 'test')
                A._sync(j.c)
                solve(j, open_[0]['id'])
            return j.c['money'], j.c['earnings'], [f['amount'] for f in j.c['ops']['finance']['ledger']]

    def test_clothing_own_sales_match_with_the_market_on_and_off(self):
        self.assertEqual(self.play({'MNL_MARKET_OFF': '1'}), self.play(ON))


if __name__ == '__main__':
    unittest.main()
