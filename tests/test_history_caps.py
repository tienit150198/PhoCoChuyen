"""Bounded histories (v0.8.1): journal 300 rows, cash book 300-400 rows (never the last
two weeks), 10 day recaps; older saves are cut once by migrate_state."""
import unittest

from game import operations as ops
from game.engine import JOURNAL_KEPT, log, migrate_state, money, new_state, validate_state
from game.experiences import GOALS_KEPT
from tests.helpers import Journey


def wallet_ok(c):
    f = c['ops']['finance']
    return f['opening_balance'] + sum(x['amount'] for x in f['ledger']) == c['money']


class HistoryCapTests(unittest.TestCase):
    def test_journal_keeps_the_newest_rows(self):
        j = Journey('milk_tea')
        for i in range(JOURNAL_KEPT + 50):
            log(j.state, j.c, 'fact', f'row {i}')
        self.assertEqual(len(j.c['journal']), JOURNAL_KEPT)
        self.assertEqual(j.c['journal'][-1]['text'], f'row {JOURNAL_KEPT + 49}')
        validate_state(j.state)

    def test_cash_book_folds_old_rows_and_keeps_the_wallet_identity(self):
        j = Journey('milk_tea')
        made = []
        for i in range(ops.LEDGER_HIGH + 1):  # ten sales a day
            j.c['day'] = 1 + i // 10
            money(j.state, j.c, 1 if i % 2 else 2, 'Bán hàng')
            made.append(j.c['day'])
        f = j.c['ops']['finance']
        recent = j.c['day'] - ops.LEDGER_DAYS
        self.assertLessEqual(len(f['ledger']), ops.LEDGER_HIGH)
        self.assertTrue(wallet_ok(j.c))
        # every row of the last two weeks is still there, older ones are folded
        self.assertEqual(sum(r['day'] >= recent for r in f['ledger']), sum(d >= recent for d in made))
        validate_state(j.state)

    def test_recent_two_weeks_are_never_folded(self):
        j = Journey('milk_tea')
        before = len(j.c['ops']['finance']['ledger'])
        for i in range(ops.LEDGER_HIGH + 100):
            money(j.state, j.c, 1, 'Bán hàng')  # all on the same day
        self.assertEqual(len(j.c['ops']['finance']['ledger']), before + ops.LEDGER_HIGH + 100)
        self.assertTrue(wallet_ok(j.c))
        for i in range(ops.LEDGER_MAX):
            money(j.state, j.c, 1, 'Bán hàng')
        self.assertLessEqual(len(j.c['ops']['finance']['ledger']), ops.LEDGER_MAX)  # the hard bound still holds
        self.assertTrue(wallet_ok(j.c))

    def test_older_save_is_cut_once_by_the_migration(self):
        s = new_state()
        c = s['careers']['grocery']
        c['day'] = 200
        c['journal'] = [dict(id=f'log-{i}', kind='fact', text='x', npc=None, ref=None, day=1 + i // 8, turn=0) for i in range(1200)]
        f = c['ops']['finance']
        f['ledger'] = [dict(id=f'entry-{i}', day=1 + i // 8, turn=0, amount=1, category='revenue', reason='Bán', ref=None) for i in range(1500)]
        c['money'] = f['opening_balance'] + 1500
        c['life']['goals_history'] = [dict(day=d) for d in range(30)]
        validate_state(s)
        m = migrate_state(s)
        mc = m['careers']['grocery']
        self.assertEqual(len(mc['journal']), JOURNAL_KEPT)
        self.assertEqual(len(mc['ops']['finance']['ledger']), ops.LEDGER_KEEP)
        self.assertEqual(len(mc['life']['goals_history']), GOALS_KEPT)
        self.assertTrue(wallet_ok(mc))
        validate_state(m)
        self.assertEqual(migrate_state(m), m)  # idempotent


if __name__ == '__main__':
    unittest.main()
