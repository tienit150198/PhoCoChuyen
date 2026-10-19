"""⚔️ Review fixes of the 19/10 integration on the Bang side (game/bang.py; PostgreSQL with TEST_DATABASE_URL):
* a deposit is never lost: the ledger id comes from a nonce (never n alone, which starts again after reset_all or an
  imported older save) and a clash refuses the whole command (nothing paid);
* the one lock order (bang rows in id order, then member rows): check-in against a kick, an approval against the
  applicant moving bang, both at once, never deadlock;
* the pet war's lineup counts current members only (leavers, kicked, a hidden bang free their slots);
* rows past their keep move to the archive tables (bang_log, bang_points, bang_stints), batched, never dropped;
* a bang page read opens a write transaction only when a build is due; a leader's settings name the members to re-tag;
* the ops' kill switch MNL_BANG_OFF."""
import copy
import os
import threading
import time
from unittest.mock import patch

from game import bang
from game import bang_content as C
from game import marriage as mr
from game import pet_war as PW
from game.engine import GameError
from tests.test_bang import Base, T0


class Deposits(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan', wallet=30_000_000)
        self.bid = self.found(self.a)

    def fund(self):
        return int(self.one('SELECT fund FROM bangs WHERE id=?', (self.bid,))['fund'])

    def refill(self, xu=30_000_000):
        sid = self.sid(self.a)

        def fn(s):
            s['journey']['story'] = True
            s['journey']['wallet'] = xu
        mr._mutate(self.store, {sid: fn})

    def give_counted(self, amount):
        """One deposit: the wallet must lose exactly what the fund gains."""
        w0, f0 = self.wallet(self.a), self.fund()
        self.give(self.a, amount, self.bid)
        self.assertEqual(w0 - self.wallet(self.a), amount)
        self.assertEqual(self.fund() - f0, amount)
        return amount

    def test_reset_all_then_give_twice(self):
        taken = self.give_counted(1_000_000)
        self.cmd(self.a, 'reset_all', confirm='BAT DAU LAI')
        self.assertIsNone(self.store.read(self.a)[0]['journey'].get('bang'))      # the counter starts again at 1
        self.refill()
        taken += self.give_counted(2_000_000)                                    # n = 1 again: a new id all the same
        taken += self.give_counted(3_000_000)
        self.assertEqual(self.fund(), taken)
        led = self.rows("SELECT id, amount FROM bang_fund WHERE bang=? AND kind='give'", (self.bid,))
        self.assertEqual(sum(r['amount'] for r in led), taken)
        self.assertEqual(len({r['id'] for r in led}), 3)

    def test_imported_older_save_then_give(self):
        taken = self.give_counted(1_000_000)
        older = copy.deepcopy(self.store.read(self.a)[0])                        # n = 2 (the founding was 1)
        taken += self.give_counted(1_000_000)                                    # n = 3
        with patch.dict(os.environ, {'MNL_IMPORT_GUARD_OFF': '1'}):
            self.cmd(self.a, 'import_save', save=dict(format='mot-ngay-lam-nghe/save-v4', state=older))
        self.assertEqual(self.store.read(self.a)[0]['journey']['bang']['n'], 2)
        self.refill()
        taken += self.give_counted(4_000_000)                                    # n = 3 again
        taken += self.give_counted(5_000_000)
        self.assertEqual(self.fund(), taken)

    def test_a_ledger_clash_refuses_the_whole_command(self):
        """Should an id ever be there already, the command rolls back: no wallet debit without its deposit."""
        with patch.object(bang.secrets, 'token_hex', lambda n=8: 'ab' * n):
            self.give(self.a, 1_000_000, self.bid)
            before = self.fund()
            msg = self.refused_cmd(self.a, 'jr_bang_give', 'retry', bang=self.bid, amount=2_000_000, confirm=True)
        self.assertIn('Thử lại', msg)
        self.assertEqual(self.fund(), before)

    def test_old_block_without_nonce_keeps_its_id(self):
        self.assertEqual(bang.give_ref('p' * 16, dict(n=7)), f'g:{"p" * 16}:7')
        self.assertEqual(bang.give_ref('p' * 16, dict(n=7, r='0123456789abcdef')), f'g:{"p" * 16}:0123456789abcdef')


class LockOrder(Base):
    """Two operations that once took a bang row and a member row in opposite orders: each waits, neither deadlocks."""

    def race(self, first, first_name, pause_on, second):
        """`first` runs in a thread until it reaches `pause_on` (a bang function, holding its locks), then `second`
        starts and is left waiting a moment, then `first` goes on. Returns the errors of both."""
        reached, go = threading.Event(), threading.Event()
        real = getattr(bang, pause_on)

        def paused(*a, **k):
            out = real(*a, **k)
            if threading.current_thread().name == first_name and not reached.is_set():
                reached.set()
                go.wait(5)
            return out
        errors = []

        def run(fn):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        with patch.object(bang, pause_on, paused):
            t1 = threading.Thread(target=run, args=(first,), name=first_name)
            t1.start()
            self.assertTrue(reached.wait(10))
            t2 = threading.Thread(target=run, args=(second,), name='second')
            t2.start()
            time.sleep(0.6)                      # the second one is waiting for a row the first one holds
            go.set()
            t1.join(20)
            t2.join(20)
        return errors

    def test_checkin_against_a_kick(self):
        a, b = self.player(name='Lan'), self.player(name='Minh')
        bid = self.found(a)
        self.op(b, 'join', bang=bid)
        errors = self.race(lambda: self.op(b, 'checkin'), 'checkin', '_earn',
                           lambda: self.op(a, 'kick', pid=self.pid(b), confirm=True))
        self.assertEqual(errors, [])
        self.assertIsNone(self.mine(b))                                          # kicked after the check-in
        self.assertEqual(len(self.rows("SELECT 1 FROM bang_points WHERE sid=? AND kind='checkin'", (self.sid(b),))), 1)

    def test_approve_against_the_applicant_moving(self):
        a, e, p = self.player(name='Lan'), self.player(name='Hùng'), self.player(name='Phúc')
        x, y = sorted([self.found(a, 'Rồng Đỏ'), self.found(e, 'Hổ Xám')], reverse=True)   # y < x
        leader_x = a if self.mine(a)['bang'] == x else e
        self.op(leader_x, 'set', open=False)
        self.op(p, 'join', bang=y)                                               # p is in the smaller id
        self.op(p, 'join', bang=x)                                               # and asks the larger (closed) one
        self.assertTrue(self.one("SELECT 1 FROM bang_asks WHERE bang=? AND sid=? AND status='open'", (x, self.sid(p))))
        errors = self.race(lambda: self.op(leader_x, 'approve', pid=self.pid(p)), 'approve', '_lock',
                           lambda: self.op(p, 'join', bang=x))                    # p touches both rows meanwhile
        self.assertEqual(errors, [])
        self.assertEqual(self.mine(p)['bang'], x)


class WarLineup(Base):
    def setUp(self):
        super().setUp()
        from game import bang_pets
        bang_pets.install()
        self.addCleanup(bang_pets.install)
        self.toks = [self.player(name=f'Người {i}') for i in range(7)]
        self.bid = self.found(self.toks[0])
        for tok in self.toks[1:]:
            self.op(tok, 'join', bang=self.bid)
        self.week = PW.A.vn_week(self.t[0])

    def pick(self, tok):
        def run(db):
            db.execute('INSERT INTO pet_war_picks(week, sid, team_kind, team_id, name, pet, snap, at) VALUES(?,?,?,?,?,?,?,?)',
                       (self.week, self.sid(tok), 'bang', self.bid, 'x', 'p1', '{}', self.t[0]))
        self.store.transaction(run)

    def picks(self):
        return {r['sid'] for r in self.rows('SELECT sid FROM pet_war_picks WHERE week=?', (self.week,))}

    def test_five_leavers_never_block_the_lineup(self):
        self.assertLess(self.t[0], PW.lock_of(self.t[0]))
        for tok in self.toks[1:6]:
            self.pick(tok)
        with self.store.connect() as db:
            self.assertEqual(len(PW.current_picks(db, self.week, 'bang', self.bid)), 5)
        self.op(self.toks[0], 'kick', pid=self.pid(self.toks[1]), confirm=True)   # kicked
        for tok in self.toks[2:5]:
            self.op(tok, 'leave', confirm=True)                                     # left
        self.store.transaction(lambda db: db.execute("UPDATE bang_members SET status='out' WHERE sid=?", (self.sid(self.toks[5]),)))
        # 4 picks gone with their players; the fifth (out by hand) still has a row but no longer counts
        self.assertEqual(self.picks(), {self.sid(self.toks[5])})
        with self.store.connect() as db:
            self.assertEqual(PW.current_picks(db, self.week, 'bang', self.bid), [])
            self.assertEqual(len(PW.current_picks(db, self.week, 'bang', self.bid, exclude=self.sid(self.toks[6]))), 0)

    def test_hidden_or_disbanded_bang_frees_its_picks(self):
        for tok in self.toks[1:4]:
            self.pick(tok)
        bang.admin_act(self.store, 'ops', dict(op='hide', id=self.bid))
        self.assertEqual(self.picks(), set())
        bang.admin_act(self.store, 'ops', dict(op='show', id=self.bid))
        for tok in self.toks[1:3]:
            self.pick(tok)
        self.op(self.toks[0], 'disband', confirm=True, name='Rồng Đỏ')
        self.assertEqual(self.picks(), set())

    def test_after_the_lock_picks_stay(self):
        self.pick(self.toks[1])
        self.t[0] = PW.lock_of(self.t[0]) + 1
        self.op(self.toks[1], 'leave', confirm=True)
        self.assertEqual(self.picks(), {self.sid(self.toks[1])})                    # the war played on them: history


class Archive(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)
        self.op(self.a, 'checkin')                                               # a recent point row: it stays
        self.old = T0 - 60 * 86400

    def test_old_rows_move_never_drop(self):
        quiet = 'bquiet00001'

        def seed(db):
            for i in range(60):   # this bang's old lines (its newest LOG_SHOWN are also old here: they go too)
                db.execute('INSERT INTO bang_log(bang, sid, kind, text, at) VALUES(?,?,?,?,?)', (self.bid, '', 'x', f'old {i}', self.old + i))
            for i in range(30):   # a quiet bang: every line old, its newest LOG_SHOWN stay for its page
                db.execute('INSERT INTO bang_log(bang, sid, kind, text, at) VALUES(?,?,?,?,?)', (quiet, '', 'x', f'q {i}', self.old + i))
            for i in range(10):
                db.execute('INSERT INTO bang_points(id, bang, sid, kind, pts, week, day, at) VALUES(?,?,?,?,?,?,?,?)',
                           (f'w:old:{i}', self.bid, 's', 'work', 5, '2026-W33', '2026-08-20', self.old))
            db.execute('INSERT INTO bang_stints(bang, sid, joined, left_at, why) VALUES(?,?,?,?,?)', (self.bid, 'gone', self.old, self.old + 10, 'leave'))
            db.execute('INSERT INTO bang_stints(bang, sid, joined) VALUES(?,?,?)', (self.bid, 'still', self.old))   # open: stays
        self.store.transaction(seed)
        n_log = len(self.rows('SELECT 1 FROM bang_log'))
        with patch.object(bang, 'ARCHIVE_BATCH', 25):
            moved = bang.archive_old(self.store, T0)
        self.assertEqual(moved['bang_points'], 10)
        self.assertEqual(moved['bang_stints'], 1)
        self.assertEqual(len(self.rows('SELECT 1 FROM bang_log WHERE bang=?', (quiet,))), bang.LOG_SHOWN)
        kept = [r['text'] for r in self.rows('SELECT text FROM bang_log WHERE bang=? ORDER BY id DESC', (quiet,))]
        self.assertEqual(kept[0], 'q 29')
        # every row is in exactly one of the two tables, unchanged
        self.assertEqual(len(self.rows('SELECT 1 FROM bang_log')) + len(self.rows('SELECT 1 FROM bang_log_old')), n_log)
        self.assertEqual(moved['bang_log'], len(self.rows('SELECT 1 FROM bang_log_old')))
        self.assertEqual(self.one("SELECT text, at FROM bang_log_old WHERE text='old 0'"), dict(text='old 0', at=self.old))
        self.assertEqual(self.one("SELECT pts, week FROM bang_points_old WHERE id='w:old:3'"), dict(pts=5, week='2026-W33'))
        self.assertEqual({r['sid'] for r in self.rows('SELECT sid FROM bang_stints_old')}, {'gone'})
        self.assertTrue(self.one("SELECT 1 FROM bang_stints WHERE sid='still'"))
        self.assertTrue(self.one('SELECT 1 FROM bang_points WHERE bang=? AND at>?', (self.bid, T0 - 86400)))   # recent: stays
        self.assertEqual(bang.archive_old(self.store, T0), dict(bang_log=0, bang_points=0, bang_stints=0))   # nothing more

    def test_housekeeping_waits_out_the_peak_and_its_interval(self):
        calls = []
        with patch.object(bang, 'archive_old', lambda store, t: calls.append(t) or {}):
            bang._ARCH['at'] = 0.0
            peak = 1_792_408_500.0             # 18:15 VN
            with patch.object(bang, 'now', lambda: peak):
                bang.run_housekeeping(self.store)
            self.assertEqual(calls, [])
            with patch.object(bang, 'now', lambda: T0):
                bang.run_housekeeping(self.store)
                bang.run_housekeeping(self.store)                                 # not again within ARCHIVE_EVERY
            self.assertEqual(calls, [T0])


class Reads(Base):
    def test_a_page_read_opens_no_write_transaction_unless_a_build_is_due(self):
        a = self.player(name='Lan')
        bid = self.found(a)
        real, seen = self.store.transaction, []

        def spy(fn, *x, **k):
            seen.append(fn)
            return real(fn, *x, **k)
        crown = patch.object(bang, 'crown', lambda store, t=None: None)   # the week's crown is read on its own (cached)
        crown.start()
        self.addCleanup(crown.stop)
        with patch.object(self.store, 'transaction', spy):
            bang.page(self.store, self.sid(a))
        self.assertEqual(seen, [])
        self.set_fund(bid, 10_000_000)
        self.op(a, 'build', fac='kho', confirm=True)
        r = self.one("SELECT ready_at FROM bang_facilities WHERE bang=? AND fac='kho'", (bid,))
        self.t[0] = float(r['ready_at']) + 1
        with patch.object(self.store, 'transaction', spy):
            bang.page(self.store, self.sid(a))
            bang.page(self.store, self.sid(a))
        self.assertEqual(len(seen), 1)                                           # once, when it was due
        with self.store.connect() as db:
            self.assertEqual(bang.levels(db, bid)['kho'], 1)

    def test_settings_name_the_members_to_retag(self):
        a, b = self.player(name='Lan'), self.player(name='Minh')
        bid = self.found(a)
        self.op(b, 'join', bang=bid)
        self.sent.clear()
        self.op(a, 'set', color='mint')
        ev = next(e for e in self.sent if e.get('op') == 'bang' and e.get('bang') == bid)
        self.assertEqual(set(ev['pids']), {self.pid(a), self.pid(b)})


class KillSwitch(Base):
    def test_bang_off_refuses_gracefully(self):
        a = self.player(name='Lan')
        bid = self.found(a)
        with patch.dict(os.environ, {'MNL_BANG_OFF': '1'}):
            self.assertTrue(bang.off())
            self.refused_cmd(a, 'jr_bang_give', 'off', bang=bid, amount=1000, confirm=True)
            self.assertIn('bảo trì', self.refused_op(a, 'checkin', 'off'))
            with self.assertRaises(bang.BangError) as cm:
                bang.get_view(self.store, a, {})
            self.assertEqual(cm.exception.status, 503)
            me = bang.me_view(self.store, a)
            self.assertTrue(me['off'])
            self.assertNotIn('mine', me)
            from game import content
            self.assertEqual(content._kill_switches()['off'], dict(bang=True))
            bang.admin_view(self.store)                                           # the operator still sees every bang
        self.assertFalse(bang.off())
        self.assertEqual(self.mine(a)['bang'], bid)                              # nothing changed meanwhile
        from game import content
        self.assertEqual(content._kill_switches(), {})


class GoldenSnapshot(Base):
    """Review fix 19/10: the windows' snapshot is read by one thread a process (the others go on with theirs), never
    reset by a join or a leave, and the players' own older windows are kept for a bounded number of players."""

    def test_single_flight_and_no_reset_on_membership(self):
        a, b = self.player(name='Lan'), self.player(name='Minh')
        bid = self.found(a)
        with self.store.connect() as db:
            bang.prepare(db, self.t[0])
        at0 = bang._GH['at']
        self.assertGreater(at0, 0)
        self.op(b, 'join', bang=bid)
        self.op(b, 'leave', confirm=True)
        self.assertEqual(bang._GH['at'], at0)                                    # no reset: the next minute's read
        calls, gate = [], threading.Event()
        real = bang._load_hot

        def slow(db, t):
            calls.append(t)
            gate.wait(2)
            return real(db, t)
        self.t[0] += bang.GH_REFRESH + 1
        with patch.object(bang, '_load_hot', slow):
            def run():
                with self.store.connect() as db:
                    bang.prepare(db, self.t[0])
            th = [threading.Thread(target=run) for _ in range(5)]
            [x.start() for x in th]
            time.sleep(0.3)
            gate.set()
            [x.join(10) for x in th]
        self.assertEqual(len(calls), 1)
        self.assertEqual(bang._GH['at'], self.t[0])

    def test_older_windows_per_player_are_bounded(self):
        with patch.object(bang, 'GH_COLD_MAX', 3), self.store.connect() as db:
            for i in range(6):
                bang.prepare(db, self.t[0], sid=f's{i}')
        self.assertEqual(list(bang._COLD), ['s3', 's4', 's5'])
