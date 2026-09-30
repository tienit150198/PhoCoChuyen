"""PgPool (game/db.py) connection reuse, with a fake driver: runs without PostgreSQL.

The real-database twins are in test_pg_backend (TEST_DATABASE_URL)."""
import io
import threading
import time
import types
import unittest
from unittest import mock

from game import db as dbm

IDLE, INTRANS, INERROR = 'idle', 'intrans', 'inerror'


class FakeRaw:
    def __init__(self, n):
        self.n = n
        self.closed = False
        self.broken = False
        self.info = types.SimpleNamespace(transaction_status=IDLE)
        self.adapters = types.SimpleNamespace(register_loader=lambda *a: None)
        self.sql = []

    def execute(self, sql, params=None):
        self.sql.append(sql)
        if sql == 'ROLLBACK':
            self.info.transaction_status = IDLE

    def close(self):
        self.closed = True


class FakeDriver:
    Error = type('Error', (Exception,), {})
    OperationalError = type('OperationalError', (Error,), {})
    InterfaceError = type('InterfaceError', (Error,), {})

    def __init__(self):
        self.made = []
        self.lock = threading.Lock()

    def connect(self, *a, **k):
        with self.lock:
            raw = FakeRaw(len(self.made))
            self.made.append(raw)
            return raw


class PoolReuseTests(unittest.TestCase):
    def setUp(self):
        self.driver = FakeDriver()
        patches = [mock.patch.object(dbm, 'psycopg', self.driver)]
        for name, value in (('IDLE', IDLE), ('INTRANS', INTRANS), ('INERROR', INERROR), ('_NumericLoader', object)):
            patches.append(mock.patch.object(dbm, name, value, create=True))
        env = dict(PG_POOL='2', PG_POOL_MAX='8', PG_POOL_IDLE_MS='10000', PG_POOL_WAIT_MS='300', PG_POOL_LOG_S='0')
        patches.append(mock.patch.dict('os.environ', env))
        patches.append(mock.patch.object(dbm, '_reap', lambda pool: None))  # no background thread: reap() is called here
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.pool = dbm.PgPool('postgresql://fake/db')

    def burst(self, n):
        held = [self.pool.connect() for _ in range(n)]
        for db in held:
            db.close()

    def test_a_burst_above_the_kept_size_reuses_its_connections(self):
        # PG_POOL=2 used to close every connection above 2 as soon as it came back: each burst of
        # 6 requests then opened (and the database forked) 4 new backends.
        for _ in range(5):
            self.burst(6)
        self.assertEqual(len(self.driver.made), 6)
        self.assertEqual(self.pool.stats()['opened'], 6)
        self.assertEqual(self.pool.stats()['closed'], 0)
        self.assertEqual((self.pool.open, len(self.pool.idle)), (6, 6))
        self.assertTrue(all(not r.closed for r in self.driver.made))

    def test_idle_connections_above_the_kept_size_are_closed_after_idle_max(self):
        self.burst(6)
        base = self.pool.idle[-1][1]
        self.assertEqual(self.pool.reap(base + 5), 0)   # not idle long enough
        self.burst(1)                                  # the most recently used one is used again
        self.assertEqual(self.pool.reap(base + 10.5), 4)  # down to PG_POOL=2, least recently used first
        self.assertEqual((self.pool.open, len(self.pool.idle)), (2, 2))
        kept = {raw.n for raw, _ in self.pool.idle}
        self.assertTrue(all(r.closed == (r.n not in kept) for r in self.driver.made))
        self.assertEqual(self.pool.reap(base + 1000), 0)  # PG_POOL connections are kept indefinitely
        self.burst(2)
        self.assertEqual(len(self.driver.made), 6)

    def test_many_threads_share_the_capped_pool(self):
        errors = []

        def work():
            try:
                for _ in range(30):
                    with self.pool.connect() as db:
                        db.raw.execute('SELECT 1')
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=work) for _ in range(16)]  # MAX_THREADS=16 > PG_POOL_MAX=8
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertLessEqual(len(self.driver.made), 8)
        self.assertEqual(self.pool.stats()['checkouts'], 16 * 30)
        self.assertEqual(self.pool.open, len(self.pool.idle))

    def test_failed_transactions_are_rolled_back_and_kept_broken_ones_dropped(self):
        a, b = self.pool.connect(), self.pool.connect()
        a.raw.info.transaction_status = INERROR
        b.raw.broken = True
        ra, rb = a.raw, b.raw
        a.close()
        b.close()
        self.assertIn('ROLLBACK', ra.sql)
        self.assertEqual([r for r, _ in self.pool.idle], [ra])
        self.assertTrue(rb.closed)
        self.assertEqual(self.pool.open, 1)
        self.assertEqual(self.pool.stats()['closed'], 1)

    def test_waiting_for_a_full_pool_is_counted_and_logged(self):
        self.pool.log_every, self.pool._log_at = 60, time.monotonic() + 60
        held = [self.pool.connect() for _ in range(8)]
        with self.assertRaises(dbm.PoolTimeout):
            self.pool.connect()
        for db in held:
            db.close()
        st = self.pool.stats()
        self.assertEqual((st['waits'], st['timeouts'], st['opened']), (1, 1, 8))
        err = io.StringIO()
        with mock.patch('sys.stderr', err):
            self.pool.reap(self.pool._log_at - 1)   # not due yet
            self.assertEqual(err.getvalue(), '')
            self.pool.reap(self.pool._log_at)
        line = err.getvalue()
        self.assertIn('[pg-pool]', line)
        self.assertIn('opened 8', line)
        self.assertIn('waited 1', line)
        self.assertEqual((self.pool.open, len(self.pool.idle)), (2, 2))  # that reap was 60 s later: back to PG_POOL
        err = io.StringIO()
        self.burst(2)
        with mock.patch('sys.stderr', err):    # a quiet minute (only reuse): nothing logged
            self.pool.reap(self.pool._log_at)
        self.assertEqual(err.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
