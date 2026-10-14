"""Timed staff orders for the four new careers; no owner salary duplication."""
import copy
import unittest
from unittest.mock import patch

from game import employment, workplace_business as wb
from game.engine import validate_state
from tests.creative_civic_economy import AuditJourney, CAREERS, shift


class CreativeCivicStaff(unittest.TestCase):
    def test_orders_pay_real_wages_once_and_preserve_player_tasks(self):
        for cid in CAREERS:
            with self.subTest(career=cid), patch.object(wb.time, 'time', return_value=2000000000):
                self.assertIn(cid, wb.ORDERS)
                j = AuditJourney(cid, 1, staffed=True)
                j.act('start_day')
                tasks = copy.deepcopy(j.c['tasks'])
                wallet = j.state['journey']['wallet']
                due = min(p['at'] for p in j.c['ops']['business']['pending'].values())
                before = j.c['money']
                self.assertTrue(wb.settle(j.state, due))
                receipt = j.c['ops']['business']['recent'][-1]
                self.assertEqual(j.c['ops']['business']['served'], 1)
                self.assertGreater(receipt['wage'], 0)
                self.assertGreater(receipt['materials'], 0)
                self.assertGreater(receipt['net'], 0)
                self.assertEqual(j.c['tasks'], tasks)
                self.assertEqual(j.state['journey']['wallet'], wallet)
                # 2.4.15: a staff order's rows are the day's summed rows (ref 'sum:<group>'); this is the first order
                rows = [r for r in j.c['ops']['finance']['ledger'] if (r['ref'] or '').startswith('sum:') and receipt['name'] in r['reason']]
                self.assertEqual(j.c['money'] - before, sum(r['amount'] for r in rows))
                self.assertEqual(sum(r['category'] == 'wage' for r in rows), 1)
                self.assertEqual(sum(r['category'] == 'other_income' for r in rows), 1)
                self.assertFalse(any(r['category'] == 'salary' for r in rows))
                snap = copy.deepcopy(j.state)
                wb.settle(j.state, due)
                self.assertEqual(j.state, snap)
                validate_state(j.state)

    def test_full_shift_with_elapsed_staff_work_keeps_single_contract_salary(self):
        for cid in CAREERS:
            with self.subTest(career=cid), patch.object(wb.time, 'time', return_value=2000000000):
                j = AuditJourney(cid, 1, staffed=True)
                row = shift(j, staff_orders=4)
                self.assertEqual(row['staff_orders_completed'], 4)
                self.assertLess(row['by_category']['wage'], 0)
                self.assertGreater(row['accrual_adjusted_net'], 0)
                expected = j.c['job']['salary'] if employment.required(cid) else 0
                self.assertEqual(row['salary'], expected)
                self.assertEqual(sum(b['kind'] == 'wage' for b in j.c['ops']['finance']['bills']), 0)


if __name__ == '__main__':
    unittest.main()
