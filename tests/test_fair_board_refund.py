"""🏆 Bảng vàng chợ đen (Top lời) shows the true net: fines the operator paid back count back (game/fair_refund.py), and
a fine taken outside a command (a player officer's, through marriage._mutate) moves the board row and the week's net
in the same transaction."""
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tests.pg_support import pg_only
from tests.test_fair import StoreBase
from tests.test_fair_loss import WeeklyLoss
from game import fair as fh, fair_bm as bm, fair_refund, leaderboard as lb, marriage as mr, system_gift as sg


def _script():
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'fair_board_recompute.py'
    spec = importlib.util.spec_from_file_location('fair_board_recompute', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pg_only
class TrueNet(StoreBase):
    lose, win, board = WeeklyLoss.lose, WeeklyLoss.win, WeeklyLoss.board   # its helpers, not its tests

    def setUp(self):
        super().setUp()
        from game import fair_loss as fl
        self.fl = fl
        self.addCleanup(fl.clear_cache)
        fl.clear_cache()
        p = patch.object(fl, 'now', side_effect=lambda: self.clock.t)
        p.start()
        self.addCleanup(p.stop)
        fair_refund.clear_cache()
        self.addCleanup(fair_refund.clear_cache)

    def row(self, tok):
        sid = self.store.key(tok)
        with self.store.connect() as db:
            r = db.execute('SELECT score FROM leaderboard WHERE board=? AND sid=?', (fh.board(), sid)).fetchone()
        return int(r['score']) if r else None

    def week(self, tok):
        return self.board(tok)['me']['net']

    def fine(self, tok, amount):
        """What game/cand_ops.py penalize does to the target's save: a Chợ đen fine through fair_bm.take_total."""
        def fn(s):
            j = s['journey']
            bm.take_total(j, fh._state(j, fh.now()), amount, '👮 test fine')
        mr._mutate(self.store, {self.store.key(tok): fn})

    def refund(self, tok, coins, gid):
        sg.grant(self.store, self.store.key(tok), coins, 'Quà từ Phố Có Chuyện', 'Hoàn phần phạt dư.', gid=gid)
        state = self.store.read(tok)[0]
        changed, _ = sg.on_load(self.store, tok, state)
        self.assertTrue(changed)

    def test_officer_fine_moves_the_row_and_the_week_at_once(self):
        a = self.player('Lan', wallet=10000)
        self.win(a, 100)
        won = fh.money_of(self.store.read(a)[0]['journey'])[0]
        self.assertGreater(won, 60)
        self.assertEqual((self.row(a), self.week(a)), (won, won))
        self.fine(a, 30)   # no command of the player's own: before, the row stayed at `won` until their next command
        self.assertEqual(fh.money_of(self.store.read(a)[0]['journey'])[0], won - 30)
        self.assertEqual((self.row(a), self.week(a)), (won - 30, won - 30))
        self.fine(a, won)   # below zero: off the board, the week's net follows
        self.assertIsNone(self.row(a))
        self.assertEqual(self.week(a), -30)

    def test_a_refunded_fine_counts_back(self):
        a, b = self.player('Lan', wallet=10000), self.player('Minh', wallet=10000)
        self.win(a, 100)
        self.win(b, 100)
        won = self.row(a)
        self.fine(a, 50)
        self.assertEqual(self.row(a), won - 50)
        # not a fine refund (another prefix), and a refund still pending: nothing counted
        self.refund(a, 7, 'g-other-gift-0001')
        sg.grant(self.store, self.store.key(b), 9, 'Quà', 'Hoàn.', gid='refund-cd-20261011-pend0001')
        fair_refund.clear_cache()
        self.lose(a, 1)
        self.assertEqual(self.row(a), won - 51)
        # the operator pays the fine back: the board counts it back (the save's own fair stats are left as they are)
        self.refund(a, 50, 'refund-cd-20261011-test0001')
        fair_refund.clear_cache()
        self.lose(a, 1)
        self.assertEqual(fh.money_of(self.store.read(a)[0]['journey'])[0], won - 52)
        self.assertEqual(self.row(a), won - 2)
        self.assertEqual(self.row(b), won)   # b's refund is still pending

    def test_refund_lifts_a_save_back_onto_the_board(self):
        a = self.player('Lan', wallet=10000)
        self.win(a, 100)
        won = self.row(a)
        self.fine(a, won + 40)
        self.assertIsNone(self.row(a))
        self.refund(a, won + 40, 'refund-cd-20261011-test0002')
        fair_refund.clear_cache()
        self.lose(a, 1)
        self.assertEqual(self.row(a), won - 1)

    def test_recompute_script_fixes_rows_without_touching_saves(self):
        a = self.player('Lan', wallet=10000)
        self.win(a, 100)
        won = self.row(a)
        self.fine(a, 20)
        self.refund(a, 20, 'refund-cd-20261011-test0003')
        sid = self.store.key(a)
        # a row written by an older build (no refund), the save untouched since
        self.store.transaction(lambda db: db.execute('UPDATE leaderboard SET score=? WHERE board=? AND sid=?', (won - 20, fh.board(), sid)))
        before = self.store.read(a)
        script = _script()
        fair_refund.clear_cache()
        with patch.object(script, 'Store', return_value=self.store), patch.object(self.store, 'close_pool'), \
                patch('sys.argv', ['x']), redirect_stdout(io.StringIO()) as out:
            script.main()
        self.assertIn('1 rows differ', out.getvalue())
        self.assertNotIn(sid, out.getvalue())
        self.assertEqual(self.row(a), won - 20)   # dry run: nothing written
        with patch.object(script, 'Store', return_value=self.store), patch.object(self.store, 'close_pool'), \
                patch('sys.argv', ['x', '--apply']), redirect_stdout(io.StringIO()) as out:
            script.main()
        self.assertIn('written: 1 rows', out.getvalue())
        self.assertEqual(self.row(a), won)
        self.assertEqual(self.store.read(a), before)   # the save (and its revision) as it was
        with patch.object(script, 'Store', return_value=self.store), patch.object(self.store, 'close_pool'), \
                patch('sys.argv', ['x', '--all']), redirect_stdout(io.StringIO()) as out:
            script.main()
        self.assertIn('0 rows differ', out.getvalue())

    def test_summary_extra_is_ignored_when_not_a_positive_int(self):
        a = self.player('Lan', wallet=10000)
        self.win(a, 100)
        state = self.store.read(a)[0]
        won = fh.money_of(state['journey'])[0]
        for bad in (0, -5, None, 2.5, True):
            self.assertEqual(lb.summary(state, bad)[fh.board()][0], won, bad)
        self.assertEqual(lb.summary(state, 9)[fh.board()][0], won + 9)
        self.assertEqual(fair_refund.of(None, 'x'), 0)
        self.assertEqual(fair_refund.of(self.store, None), 0)


if __name__ == '__main__':
    import unittest
    unittest.main()
