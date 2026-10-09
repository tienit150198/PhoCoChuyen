"""couple-race (10/10): the joint fund (Quỹ chung) and the social gift under real PostgreSQL concurrency.

Each test runs two threads, each on its own pooled connection, and stops one of them at a fixed point inside its
transaction while the other runs, so the interleaving is the same on every run:

1. a withdraw racing the end of a marriage (account deletion, divorce, and a withdraw that is first);
2. a joint-card hold: 60 one-xu deposits must not get a house refunded, and a load that refunds a hold while
   the purchase is still being written must not let the purchase land too;
3. the same gift sent twice at once must arrive once.
"""
import threading
import time
import unittest
from unittest.mock import patch

from game import couple as cp
from game import marriage as mr
from game import social
from game.engine import GameError
from tests.pg_support import pg_only
from tests.test_couple import CoupleBase


def _until(cond, timeout=10.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return False


class Runner:
    """A thread whose outcome ('ok', an error code, or the exception) is kept."""

    def __init__(self, name, fn):
        self.out = None
        self.thread = threading.Thread(target=self._run, args=(fn,), name=name, daemon=True)

    def _run(self, fn):
        try:
            fn()
            self.out = 'ok'
        except (mr.MarriageError, GameError, social.SocialError) as e:
            self.out = e.code
        except Exception as e:  # noqa: BLE001 - a deadlock or another database error is a failure of the test
            self.out = e

    def start(self):
        self.thread.start()
        return self

    def done(self):
        return not self.thread.is_alive()

    def join(self):
        self.thread.join(20)
        assert not self.thread.is_alive(), 'thread stuck'
        return self.out


@pg_only
class FundEndRace(CoupleBase):
    """A withdraw and the end of the marriage at the same time: the fund is paid out exactly once."""

    def setUp(self):
        super().setUp()
        self.act(self.a, 'fund_deposit', amount=600, rid='race-deposit-a')
        self.act(self.b, 'fund_deposit', amount=400, rid='race-deposit-b')
        self.assertEqual(self.balance(), 1000)

    def balance(self):
        with self.store.connect() as db:
            return cp._balance(db, self.cid)

    def waiting_on_a_lock(self, runner):
        """The other thread finished, or one of its statements waits on a PostgreSQL row lock."""
        if runner.done():
            return True
        with self.store.connect() as db:
            return db.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE datname=current_database() "
                              "AND wait_event_type='Lock' AND pid<>pg_backend_pid()").fetchone()[0] > 0

    def stop_inside_on_end(self, ender_name, start_other):
        """mr._rows reads the open debts inside cp.on_end, after the fund balance was read and before it is
        zeroed: the ending transaction stops there, the withdraw runs, then the end goes on."""
        real = mr._rows
        state = dict(stopped=False)

        def rows(db, sql, args=()):
            if (threading.current_thread().name == ender_name and 'couple_debts' in sql and not state['stopped']):
                state['stopped'] = True
                other = start_other()
                self.assertTrue(_until(lambda: self.waiting_on_a_lock(other)), 'the withdraw neither finished nor waited')
            return real(db, sql, args)
        return patch.object(mr, '_rows', rows)

    def test_account_deletion_and_withdraw_pay_the_fund_once(self):
        wa = self.wallet(self.a)
        withdraw = Runner('withdraw', lambda: self.act(self.a, 'fund_withdraw', amount=700, rid='race-withdraw-1'))
        with self.stop_inside_on_end('ender', withdraw.start):
            ender = Runner('ender', lambda: mr.forget(self.store, self.b)).start()
            self.assertEqual(ender.join(), 'ok')
        out = withdraw.join()
        mr.on_load(self.store, self.a, self.state(self.a))
        # Bình's account is gone: An keeps the whole fund (1000 xu), never the fund plus the withdraw
        self.assertEqual(self.wallet(self.a), wa + 1000, f'withdraw: {out!r}')
        self.assertEqual(out, 'not_married')
        self.assertEqual(self.balance(), 0)

    def test_divorce_then_withdraw_refuses_cleanly(self):
        wa, wb = self.wallet(self.a), self.wallet(self.b)
        withdraw = Runner('withdraw', lambda: self.act(self.a, 'fund_withdraw', amount=700, rid='race-withdraw-2'))
        with self.stop_inside_on_end('ender', withdraw.start):
            ender = Runner('ender', lambda: self.act(self.b, 'divorce', confirm='LY HON')).start()
            self.assertEqual(ender.join(), 'ok')
        out = withdraw.join()
        self.assertEqual(out, 'not_married', f'withdraw: {out!r}')   # a short reason, not a deadlock or "quỹ còn 0 xu"
        for tok in (self.a, self.b):
            mr.on_load(self.store, tok, self.state(tok))
        self.assertEqual(self.wallet(self.a) + self.wallet(self.b), wa + wb + 1000)
        self.assertEqual(self.balance(), 0)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(self.a, 'fund_withdraw', amount=1, rid='race-withdraw-3')
        self.assertEqual(e.exception.code, 'not_married')

    def test_withdraw_first_then_divorce_splits_what_is_left(self):
        """The withdraw holds the fund when the divorce starts: the divorce waits for it (no deadlock) and splits
        the 300 xu left."""
        wa, wb = self.wallet(self.a), self.wallet(self.b)
        real = cp._fund_move
        holder = {}

        def fund_move(db, *args, **kw):
            out = real(db, *args, **kw)
            if threading.current_thread().name == 'withdraw':
                holder['ender'] = ender = Runner('ender', lambda: self.act(self.b, 'divorce', confirm='LY HON')).start()
                self.assertTrue(_until(lambda: self.waiting_on_a_lock(ender)), 'the divorce neither finished nor waited')
            return out
        with patch.object(cp, '_fund_move', fund_move):
            withdraw = Runner('withdraw', lambda: self.act(self.a, 'fund_withdraw', amount=700, rid='race-withdraw-4')).start()
            self.assertEqual(withdraw.join(), 'ok')
            self.assertEqual(holder['ender'].join(), 'ok')
        for tok in (self.a, self.b):
            mr.on_load(self.store, tok, self.state(tok))
        # 700 withdrawn, then 300 split 150 / 150
        self.assertEqual(self.wallet(self.a), wa + 700 + 150)
        self.assertEqual(self.wallet(self.b), wb + 150)
        self.assertEqual(self.balance(), 0)


@pg_only
class CardHoldReplay(CoupleBase):
    """A joint-card hold is settled with the purchase's own save write."""

    def buy_home(self, rid):
        return self.store.command(self.a, rid, self.store.read(self.a)[1], None, 'jr_home_buy',
                                  dict(kind='tap_the', down=1800, joint=800, confirm=True))

    def setUp(self):
        super().setUp()
        self.act(self.a, 'fund_deposit', amount=800, rid='hold-deposit-1')
        self.fund(self.a, 1300)

    def owned(self):
        return ((self.state(self.a)['journey'].get('home') or {}).get('own') or {}).get('kind')

    def fund_balance(self):
        return cp.joint_account(self.state(self.a))['balance']

    def test_sixty_small_deposits_do_not_refund_a_house(self):
        self.assertTrue(self.buy_home('hold-home-1')['result']['approved'])
        self.assertEqual((self.owned(), self.fund_balance()), ('tap_the', 0))
        # a second connection, in another thread, pushes the hold's id out of the save's last 60 ids
        def deposits():
            for i in range(mr.APPLIED_KEPT):
                self.act(self.a, 'fund_deposit', amount=1, rid=f'hold-tiny-{i:04d}')
        self.assertEqual(Runner('deposits', deposits).start().join(), 'ok')
        self.assertFalse(any(k.startswith('jspend:') for k in self.state(self.a)['marriage']['applied']))
        self.clock.t += cp.HOLD_S + 1
        mr.on_load(self.store, self.a, self.state(self.a))
        self.assertEqual(self.owned(), 'tap_the')
        self.assertEqual(self.fund_balance(), mr.APPLIED_KEPT)   # the 60 xu, not 860
        self.assertEqual(self.row("SELECT status FROM joint_ledger WHERE kind='home'")['status'], 'done')

    def test_a_refund_while_the_purchase_is_written_never_lets_both_happen(self):
        """The command has charged the card and not written its save yet; another connection loads the save
        HOLD_S later and refunds the hold. The purchase must then fail: never a house AND a refund."""
        real = cp.joint_spend
        armed = [True]

        def joint_spend(s, *args, **kw):
            out = real(s, *args, **kw)
            if armed.pop() if armed else False:   # the command's own thread (storage's save-command pool), once
                self.clock.t += cp.HOLD_S + 1
                loader = Runner('loader', lambda: mr.on_load(self.store, self.a, self.state(self.a))).start()
                self.assertEqual(loader.join(), 'ok')
            return out
        with patch.object(cp, 'joint_spend', joint_spend):
            out = Runner('buyer', lambda: self.buy_home('hold-home-2')).start().join()
        owned, bal = self.owned(), self.fund_balance()
        self.assertFalse(owned == 'tap_the' and bal == 800, f'house kept AND refunded ({out!r})')
        self.assertEqual((out, owned, bal), ('expired', None, 800))
        self.assertEqual(self.row("SELECT status FROM joint_ledger WHERE kind='home'")['status'], 'void')


@pg_only
class GiftRace(unittest.TestCase):
    """The same gift tapped twice at once: the coins leave once and arrive once."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        from game import push
        from game.storage import Store
        from tests.test_social import Player
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db')
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.store.close_pool)
        social.ensure(self.store)
        push.ensure(self.store)
        self.a = Player(self.store, 'Mây Bếp')
        self.b = Player(self.store, 'Gió Hoa')

    def test_two_taps_at_once_give_one_gift(self):
        before_a, before_b = self.a.c['money'], self.b.c['money']
        sa = self.a.state
        real = social._cmd
        meet = threading.Barrier(2)

        def cmd(*args, **kw):
            try:
                meet.wait(3)   # both taps past the checks? (with the fix, the second waits on the giver's lock)
            except threading.BrokenBarrierError:
                pass
            return real(*args, **kw)
        with patch.object(social, '_cmd', cmd):
            taps = [Runner(f'tap{i}', lambda: social.post(self.store, self.a.token, sa, 'gift',
                                                           dict(pid=self.b.pid, sticker='🍜', coins=10))).start() for i in range(2)]
            outs = sorted(str(t.join()) for t in taps)
        with self.store.connect() as db:
            rows = db.execute('SELECT COUNT(*) FROM gifts WHERE from_pid=?', (self.a.pid,)).fetchone()[0]
        self.b.get('inbox')   # delivers the gifts
        self.assertEqual(rows, 1, outs)
        self.assertEqual(outs, ['ok', 'social_error'])
        self.assertEqual(self.a.c['money'], before_a - 10)
        self.assertEqual(self.b.c['money'], before_b + 10)


if __name__ == '__main__':
    unittest.main()
