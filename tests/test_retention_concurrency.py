"""Bulk action counters take overlapping row locks in one canonical SQL order."""
import tempfile
import threading
import time
import unittest
from pathlib import Path

from game import db as dbm
from game import retention as rt
from game.storage import Store


@unittest.skipUnless(dbm.test_mode(), 'requires an isolated TEST_DATABASE_URL schema')
class RetentionBatchConcurrency(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'retention.db')
        self.addCleanup(self.store.close_pool)

    def test_opposite_batch_orders_do_not_deadlock_or_lose_counts(self):
        day = rt.vn_day(time.time())
        first, second, deleted = 'a' * 64, 'b' * 64, 'd' * 64
        with self.store.connect() as db:
            for sid in (first, second):
                db.execute('INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)', (sid, 'csrf', '{}'))
                db.execute('INSERT INTO stat_actions(day,sid,career,action,n,errors,err) VALUES(?,?,?,?,0,0,NULL)',
                           (day, sid[:16], 'milk_tea', 'feed_like'))
            db.pg('''CREATE FUNCTION retention_test_gate() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    PERFORM 1 FROM stat_actions
                    WHERE day=NEW.day AND sid=NEW.sid AND career=NEW.career AND action=NEW.action
                    FOR UPDATE;
                    PERFORM pg_advisory_xact_lock(913410, pg_backend_pid());
                    RETURN NEW;
                END $$''')
            db.pg('''CREATE TRIGGER retention_test_gate BEFORE INSERT ON stat_actions
                FOR EACH ROW EXECUTE FUNCTION retention_test_gate()''')

        # SQL must impose the order itself: sorted Python inputs alone do not
        # constrain the existence check's join plan. Deliberately reverse one input.
        rows = [
            [(day, first, 'milk_tea', 'feed_like', 2, 0, None),
             (day, second, 'milk_tea', 'feed_like', 3, 0, None),
             (day, deleted, 'milk_tea', 'feed_like', 100, 0, None)],
            [(day, second, 'milk_tea', 'feed_like', 7, 2, None),
             (day, first, 'milk_tea', 'feed_like', 5, 1, 'revision_conflict'),
             (day, deleted, 'milk_tea', 'feed_like', 100, 0, None)],
        ]
        workers = [self.store.connect(), self.store.connect()]
        control = self.store.connect()
        pids = [db.raw.info.backend_pid for db in workers]
        failures = []

        def write(db, batch):
            try:
                db.begin()
                db.set_local('statement_timeout', '8s')
                db.set_local('lock_timeout', '5s')
                db.set_local('deadlock_timeout', '100ms')
                # Exercise a valid join plan that can retain input order before
                # the final SQL sort. All settings are local to this test transaction.
                db.set_local('enable_hashjoin', 'off')
                db.set_local('enable_mergejoin', 'off')
                db.pg(rt._UPSERT_PG, tuple(list(column) for column in zip(*batch)))
                db.commit()
            except Exception as exc:
                failures.append((type(exc).__name__, getattr(exc, 'sqlstate', None)))
                db.rollback()
            finally:
                db.close()

        threads = [threading.Thread(target=write, args=(db, batch), daemon=True)
                   for db, batch in zip(workers, rows)]
        try:
            for pid in pids:
                control.raw.execute('SELECT pg_advisory_lock(%s,%s)', (913410, pid))
            for thread in threads:
                thread.start()
            # The BEFORE INSERT trigger locks the conflict row, then waits at a
            # gate before the next input row can run (AFTER triggers run too late).
            # Correct ordering makes the second writer wait on the first writer
            # instead. Either way, both must be blocked before gates are released.
            deadline = time.monotonic() + 3
            blocked = set()
            while time.monotonic() < deadline:
                blocked = {row[0] for row in control.raw.execute(
                    'SELECT pid FROM pg_stat_activity WHERE pid=ANY(%s) AND cardinality(pg_blocking_pids(pid))>0',
                    (pids,)).fetchall()}
                if blocked == set(pids):
                    break
                time.sleep(0.01)
            self.assertEqual(blocked, set(pids), 'writers did not reach the controlled contention point')
        finally:
            control.raw.execute('SELECT pg_advisory_unlock_all()')
            control.close()
            for thread in threads:
                if thread.ident is not None:
                    thread.join(timeout=9)
            for db, thread in zip(workers, threads):
                if thread.is_alive():
                    db.raw.cancel()
                    thread.join(timeout=2)
                elif thread.ident is None:
                    db.close()
        self.assertFalse(any(thread.is_alive() for thread in threads), 'counter writer did not finish')
        self.assertEqual(failures, [], 'overlapping metric batches must both commit')
        with self.store.connect() as db:
            got = [tuple(row) for row in db.execute(
                'SELECT sid,n,errors,err FROM stat_actions ORDER BY sid').fetchall()]
        self.assertEqual(got, [(first[:16], 7, 1, 'revision_conflict'), (second[:16], 10, 2, None)])


if __name__ == '__main__':
    unittest.main()
