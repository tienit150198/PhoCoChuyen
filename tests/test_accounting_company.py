import copy
import importlib.util
import unittest

from game.engine import GameError, new_state


class AccountingCompanyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('game.accounting_company'), 'Linked accounting company is not implemented')
        from game import accounting_company as company
        self.company = company
        self.book = company.initial()

    def complete(self):
        for task in self.company.tasks(self.book):
            self.company.inspect(self.book, task['id'])
            self.company.submit(self.book, task['id'], copy.deepcopy(task['_key']))

    def test_company_has_linked_transactions_and_four_reports(self):
        tasks = self.company.tasks(self.book)
        self.assertGreaterEqual(len(tasks), 30)
        self.assertEqual({t['report'] for t in tasks if t.get('report')}, {'position', 'profit', 'cashflow', 'notes'})
        self.complete()
        result = self.company.reports(self.book)
        self.assertEqual(result['assets'], result['liabilities'] + result['equity'])
        self.assertEqual(result['cash_end'] - result['cash_start'], result['cash_net'])
        self.assertEqual(sum(self.company.ledger(self.book).values()), 0)
        self.company.validate(self.book)

    def test_full_year_each_cash_balance_and_complete_statements_reconcile(self):
        for period in range(1, 13):
            self.book['period'] = period
            for task in self.company.tasks(self.book):
                self.company.inspect(self.book, task['id'])
                self.assertTrue(self.company.submit(self.book, task['id'], copy.deepcopy(task['_key']))['correct'])
                balance = self.company.ledger(self.book)
                self.assertGreaterEqual(balance.get('111', 0), 0)
                self.assertGreaterEqual(balance.get('112', 0), 0)
            view = self.company.public(self.book)
            forms = view['statements']
            values = lambda fid: {r['code']: r['value'] for r in forms[fid]['rows']}
            b1, b2, b3 = (values(fid) for fid in ('B01', 'B02', 'B03'))
            self.assertEqual(b1['280'], b1['440'])
            self.assertEqual(b1['280'], view['reports']['assets'])
            opening = self.company._opening(period)[0]
            distribution = next(t['_key'][0] for t in self.company._transactions(period) if t['id']=='dividend')
            self.assertEqual(b1['420a'], -opening.get('4211',0)-opening.get('4212',0)-distribution['amount'])
            self.assertEqual(b1['420b'], view['reports']['profit'])
            self.assertEqual(b2['60'], view['reports']['profit'])
            balance=self.company.ledger(self.book)
            self.assertEqual(balance.get('3331',0),0)
            self.assertGreater(balance.get('1332',0),0)
            self.assertEqual(b3['70'] - b3['60'], b3['50'] + b3['61'])
            self.assertGreaterEqual(len(forms['B01']['rows']), 120)
            self.assertGreaterEqual(len(forms['B09']['rows']), 100)
            self.assertEqual(sum(x['debit'] for x in view['ledger']), sum(x['credit'] for x in view['ledger']))
            self.assertTrue(all('opening_debit' in x and 'movement_credit' in x for x in view['ledger']))
            self.assertTrue(view['details']['assets'])
            self.assertTrue(view['details']['foreign_currency'])
            self.company.validate(self.book)
            if period < 12: self.company.next_period(self.book)

    def test_entry_requires_source_and_sequence_and_does_not_duplicate(self):
        first = self.company.tasks(self.book)[0]
        with self.assertRaises(GameError): self.company.submit(self.book, first['id'], first['_key'])
        self.company.inspect(self.book, first['id'])
        before = self.company.ledger(self.book)
        bad = copy.deepcopy(first['_key']); bad[0]['amount'] += 1
        self.assertFalse(self.company.submit(self.book, first['id'], bad)['correct'])
        self.assertEqual(before, self.company.ledger(self.book))
        self.assertTrue(self.company.submit(self.book, first['id'], first['_key'])['correct'])
        posted = self.company.ledger(self.book)
        with self.assertRaises(GameError): self.company.submit(self.book, first['id'], first['_key'])
        self.assertEqual(posted, self.company.ledger(self.book))

    def test_import_cannot_jump_periods_without_prior_completed_book(self):
        self.book['period']=12
        with self.assertRaises(GameError):self.company.validate(self.book)

    def test_arbitrary_entry_metadata_rejected(self):
        task=self.company.tasks(self.book)[0]
        self.company.inspect(self.book,task['id'])
        answer=copy.deepcopy(task['_key']);answer[0]['ignored']='x'*200_000
        with self.assertRaises(GameError):self.company.submit(self.book,task['id'],answer)
        self.assertEqual(self.book['at'],0)

    def test_next_period_carries_balances_and_rejects_early_reset(self):
        with self.assertRaises(GameError): self.company.next_period(self.book)
        self.complete()
        old = self.company.ledger(self.book)
        self.company.next_period(self.book)
        self.assertEqual(self.company.ledger(self.book), old)
        self.assertEqual(self.book['period'], 2)
        self.complete()
        self.company.validate(self.book)

    def test_public_book_has_no_answer_key_or_unsolved_explanation(self):
        view = self.company.public(self.book)
        self.assertNotIn('_key', repr(view))
        self.assertNotIn('explain', view['task'])
        self.assertEqual(view['chart']['112'], 'Tiền gửi không kỳ hạn')


if __name__ == '__main__': unittest.main()
