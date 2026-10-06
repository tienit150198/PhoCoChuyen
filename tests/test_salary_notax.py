"""Owner 06/10: salaried, non-shop careers pay no 4% shop tax and no premises rent on their pay.

operations.SALARIED careers (pagoda, nurse, police, office jobs…) accrue no rent and bill no period tax from now
on; shops keep the old rule. Bills and periods already in a save are never touched (no refund, no back-charge),
and nothing new is written to the save, so an older release still reads it (validate_state's period rule).
"""
import copy
import json
import unittest
from unittest.mock import patch

from game import operations as ops
from game.careers import PLUGINS
from game.engine import money, public_state, validate_state
from tests.helpers import Journey


class SalariedNoTaxTests(unittest.TestCase):
    def setUp(self):
        for target in ('game.workplace_business.refresh', 'game.workplace_business.settle'):
            mocked = patch(target, return_value=False);mocked.start();self.addCleanup(mocked.stop)

    def journey(self, career):
        j = Journey(career);j.state['settings']['securityEvents'] = False
        return j

    def week(self, j, pay=100, days=7):
        """Close `days` days, each with `pay` xu booked as finished work (the 'Hoàn thành:' revenue row)."""
        summaries = []
        for n in range(days):
            money(j.state, j.c, pay, 'Hoàn thành: việc thử')
            summaries.append(j.act('end_day', carry_event=True)['summary']['operations'])
            if n < days - 1:j.act('start_day')
        return summaries

    def assert_books(self, j):
        validate_state(json.loads(json.dumps(j.state)))
        for c in j.state['careers'].values():
            f = c['ops']['finance']
            self.assertEqual(c['money'], f['opening_balance'] + sum(x['amount'] for x in f['ledger']))

    def test_the_list_is_real_careers_and_leaves_shops_alone(self):
        self.assertLessEqual(ops.SALARIED, set(ops.CAREERS))
        for cid in ('pagoda', 'nurse', 'police', 'hr_admin', 'secretary', 'it_helpdesk', 'corp_accounting', 'pilot'):
            if cid in PLUGINS:self.assertTrue(ops.salaried(cid), cid)
        for cid in ('milk_tea', 'mother_baby', 'pharmacy', 'accounting', 'tax_payroll', 'restaurant', 'drain', 'delivery', None):
            self.assertFalse(ops.salaried(cid), cid)

    def test_salaried_week_has_no_tax_or_rent(self):
        for career in ('nurse', 'pagoda', 'police', 'hr_admin', 'teacher'):
            if career not in ops.CAREERS:continue
            with self.subTest(career=career):
                j = self.journey(career);before = j.c['money']
                summaries = self.week(j)
                f = j.c['ops']['finance']
                self.assertFalse([b for b in f['bills'] if b['kind'] in ('tax', 'rent')])
                self.assertEqual(f['history'], [])
                self.assertEqual((f['period_revenue'], f['period_rent'], f['period_days']), (0, 0, 0))
                self.assertTrue(all(s['rent_accrued'] == 0 and s['period'] is None for s in summaries))
                # Điện nước stays (the owner exempted tax and rent only), one bill a closed day.
                self.assertEqual(len([b for b in f['bills'] if b['kind'] == 'utility']), 7)
                # The pay itself is untouched: the same ledger row, the same category.
                rows = [x for x in f['ledger'] if x['reason'] == 'Hoàn thành: việc thử']
                self.assertEqual([x['category'] for x in rows], ['revenue'] * 7)
                self.assertGreaterEqual(j.c['money'], before)
                self.assertFalse([e for e in j.c['journal'] if e['kind'] == 'period'])
                self.assert_books(j)

    def test_shop_week_is_unchanged(self):
        j = self.journey('mother_baby')
        summaries = self.week(j)
        f = j.c['ops']['finance'];h = f['history'][0]
        self.assertEqual((h['revenue'], h['tax'], h['rent'], h['rate']), (700, 28, 42, 4))
        self.assertEqual(summaries[-1]['period']['tax'], 28);self.assertEqual(summaries[0]['rent_accrued'], 6)
        self.assertEqual({b['kind'] for b in f['bills']} >= {'tax', 'rent'}, True)
        self.assert_books(j)

    def test_old_bills_and_periods_stay_and_the_open_accrual_is_never_billed(self):
        """A save from before: a closed period, its unpaid bills and a half-accrued period. Nothing is refunded,
        nothing new is billed, no money moves."""
        j = self.journey('nurse')
        f = j.c['ops']['finance'];day = j.c['day']
        old = dict(id='period-1-7', start=1, end=7, revenue=700, tax=28, rent=42, rate=4)
        f['history'] = [old]
        ops.bill(j.c, 'rent-period-1-7', 'rent', 'Mặt bằng · kỳ 1–7', 42, day + 2, 'period-1-7')
        ops.bill(j.c, 'tax-period-1-7', 'tax', 'Thuế 4% · kỳ kết ngày 7', 28, day + 2, 'period-1-7')
        f.update(period_revenue=300, period_rent=18, period_days=3)
        validate_state(j.state)
        bills, ledger, cash = copy.deepcopy(f['bills']), copy.deepcopy(f['ledger']), j.c['money']
        for _ in range(4):
            j.act('end_day', carry_event=True);j.act('start_day')
        f = j.c['ops']['finance']
        self.assertEqual(f['history'], [old])
        self.assertEqual([b for b in f['bills'] if b['kind'] in ('tax', 'rent')], [b for b in bills if b['kind'] in ('tax', 'rent')])
        self.assertEqual(f['ledger'][:len(ledger)], ledger)
        self.assertEqual(j.c['money'], cash + sum(x['amount'] for x in f['ledger'][len(ledger):]))
        self.assertEqual((f['period_revenue'], f['period_rent']), (0, 0))
        self.assert_books(j)

    def test_books_view_flags_the_exemption(self):
        j = self.journey('nurse');money(j.state, j.c, 101, 'Hoàn thành: việc thử')
        f = public_state(j.state, 'nurse')['careers']['nurse']['ops']['finance']
        self.assertTrue(f['tax_exempt']);self.assertEqual((f['estimate_tax'], f['period_revenue'], f['period_rent']), (0, 0, 0))
        self.assertEqual(j.c['ops']['finance']['period_revenue'], 101)  # the view only: the save is not rewritten
        shop = self.journey('mother_baby');money(shop.state, shop.c, 101, 'Hoàn thành: việc thử')
        f = public_state(shop.state, 'mother_baby')['careers']['mother_baby']['ops']['finance']
        self.assertNotIn('tax_exempt', f);self.assertEqual(f['estimate_tax'], 5)

    def test_no_new_save_keys(self):
        j = self.journey('nurse');self.week(j)
        self.assertEqual(set(j.c['ops']['finance']), set(ops.initial_operations('nurse')['finance']))


if __name__ == '__main__':
    unittest.main()
