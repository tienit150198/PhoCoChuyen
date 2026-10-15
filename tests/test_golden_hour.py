"""⏰ Giờ vàng / 🌟 Ngày vàng (game/golden_hour.py, owner 15/10) and the quiet counter's paused time costs (2.4.20)."""
import copy
import datetime
import os
import unittest
from unittest import mock

from game import golden_hour as g, staff_market as sm, quay_business as qb
from tests.test_quay_business import fixture

ON = {'MNL_GOLDEN_OFF': '0'}


class Plan(unittest.TestCase):
    def test_every_day_has_one_window_inside_the_open_hours_or_a_whole_golden_day(self):
        kinds = set()
        for i in range(400):
            day = datetime.date(2026, 10, 15) + datetime.timedelta(days=i)
            p = g.plan(day)
            self.assertEqual(p, g.plan(day))                      # drawn from the date: every worker agrees
            base = g._midnight(day)
            if p['kind'] == 'day':
                self.assertEqual((p['start'], p['end'], p['mult']), (base, base + 86400, g.DAY_MULT))
            else:
                self.assertIn(p['minutes'], (10, 30, 60))
                self.assertGreaterEqual(p['start'], base + g.OPEN * 60)
                self.assertLessEqual(p['end'], base + g.CLOSE * 60)
                self.assertEqual(p['end'] - p['start'], p['minutes'] * 60)
                self.assertEqual(p['mult'], g.HOUR_MULT)
            kinds.add(p['kind'])
        self.assertEqual(kinds, {'day', 'hour'})

    def window(self):
        day = next(datetime.date(2026, 10, 15) + datetime.timedelta(days=i) for i in range(30)
                   if g.plan(datetime.date(2026, 10, 15) + datetime.timedelta(days=i))['kind'] == 'hour')
        return g.plan(day)

    def test_mult_inside_and_outside_and_switched_off(self):
        p = self.window()
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(g.mult(p['start']), 200)
            self.assertEqual(g.mult(p['end'] - 1), 200)
            self.assertEqual(g.mult(p['end']), 100)
            self.assertEqual(g.mult(p['start'] - 1), 100)
            self.assertEqual(g.public(p['start'] + 5)['ends'], p['end'])
            self.assertIsNone(g.public(p['end'] + 5))
            self.assertIn('Giờ vàng', g.news_line(p['start']))
            self.assertEqual(g.scale_take(124, p['start']), 348)   # (100 + 124) × 2 − 100
            self.assertEqual(g.scale_take(124, p['end']), 124)
        self.assertEqual(g.mult(p['start']), 100)                  # tests run with MNL_GOLDEN_OFF=1
        self.assertIsNone(g.public(p['start']))

    def test_staff_orders_earn_twice_the_margin_in_the_window(self):
        p = self.window()
        with mock.patch.dict(os.environ, ON):
            self.assertEqual(sm.x('accounting', p['start']) * 100 // sm.x('accounting', p['start'] - 3600), 200)
            self.assertEqual(sm.public(p['start'])['golden']['mult'], 200)


class CounterGolden(unittest.TestCase):
    def test_a_counter_sale_in_the_window_doubles_the_owner_take(self):
        p = Plan().window()
        takes = []
        for t in (p['start'] - 7200, p['start'] + 1):
            s, st = fixture(staff=False)
            qb.settle(s, now=t - 10)
            dish = qb.qs.menu(st)['on'][0]
            st['business']['stock'][dish] = 5
            till = st['till'] + st['fund']
            with mock.patch.dict(os.environ, ON):
                qb.sale(st, [dish], int(t * 1000), owner=s)
            takes.append(st['till'] + st['fund'] - till - qb.unit_cost(st, dish))   # profit: the goods were paid at restock
        margin_take = takes[0]
        self.assertGreater(margin_take, 0)
        self.assertAlmostEqual(takes[1] / margin_take, 2, delta=0.15)   # tax and the integer bonus round a little


class QuietCounter(unittest.TestCase):
    def test_time_costs_stop_ten_minutes_after_the_last_sale_and_polling_books_the_same(self):
        def run(polls):
            s, st = fixture()
            qb.settle(s, now=1000)
            b = st['business']
            b['recent'] = [dict(id=1, at=1000.0, dish='x', qty=1, total=1, channel='counter', stars=5)]
            spent0 = sum(b['expenses'][k] for k in qb.TIME_COSTS)
            for t in polls:
                qb._charge(st, t - b['cursor'], start=b['cursor'])
                b['cursor'] = t
            return sum(b['expenses'][k] for k in qb.TIME_COSTS) - spent0, copy.deepcopy(b['carry'])
        once = run([1000 * 1000 + 3 * 3600 * 1000])
        often = run([1000 * 1000 + i * 7 * 60 * 1000 for i in range(1, 26)] + [1000 * 1000 + 3 * 3600 * 1000])
        ten = run([1000 * 1000 + qb.QUIET_MS])
        self.assertEqual(once, often)          # polling cannot change what is paid
        self.assertEqual(once, ten)            # 3 h quiet costs what the first 10 minutes cost
        self.assertGreater(ten[0], 0)

    def test_a_counter_that_never_sold_pays_as_before(self):
        s, st = fixture()
        qb.settle(s, now=1000)
        st['business']['recent'] = []
        self.assertEqual(qb._busy(st, 0, 10**7), 10**7)


if __name__ == '__main__':
    unittest.main()
