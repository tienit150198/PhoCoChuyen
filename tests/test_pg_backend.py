"""PostgreSQL backend (game/db.py, game/pg_schema.py, Store on PostgreSQL).

The translation tests run everywhere; the rest need TEST_DATABASE_URL=postgresql://...
(a local PostgreSQL 16). Each Store gets its own schema (see game/db.py, test mode)."""
import os
import re
import tempfile
import threading
import time
import unittest
from pathlib import Path

from game import db as dbm
from game import pg_schema
from game import player_feedback as pfb
from game.engine import GameError
from game.storage import Store, Conflict
from tests.pg_support import pg_only

TS = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')


class TranslateTests(unittest.TestCase):
    def t(self, sql, params=True):
        return dbm.translate(sql, params)[0]

    def test_placeholders_never_inside_literals(self):
        self.assertEqual(self.t("SELECT '?', x FROM t WHERE a=? AND b='it''s ?'"), "SELECT '?', x FROM t WHERE a=%s AND b='it''s ?'")
        self.assertEqual(self.t('SELECT "a?b" FROM t WHERE c IN (?,?)'), 'SELECT "a?b" FROM t WHERE c IN (%s,%s)')

    def test_percent_is_escaped_only_when_binding(self):
        self.assertEqual(self.t("SELECT 1 WHERE n LIKE 'a%' AND m=?"), "SELECT 1 WHERE n LIKE 'a%%' AND m=%s")
        self.assertEqual(self.t("SELECT 5 % 2", params=False), "SELECT 5 % 2")

    def test_native_conflicts_and_timestamps(self):
        self.assertEqual(self.t('INSERT INTO v(a) VALUES(?) ON CONFLICT DO NOTHING'), 'INSERT INTO v(a) VALUES(%s) ON CONFLICT DO NOTHING')
        self.assertIn(dbm.NOW_TEXT, self.t('UPDATE s SET u=CURRENT_TIMESTAMP WHERE sid=?'))

    def test_sqlite_syntax_is_rejected_instead_of_translated(self):
        for sql in ('INSERT OR IGNORE INTO v(a) VALUES(?)', 'BEGIN IMMEDIATE',
                    ' begin  immediate ', 'BEGIN EXCLUSIVE',
                    "SELECT datetime('now','-1 hour')", "SELECT DATETIME('now',?)"):
            with self.subTest(sql=sql), self.assertRaises(NotImplementedError):
                self.t(sql)

    def test_sqlite_words_in_literals_and_identifiers_are_preserved(self):
        sql = '''SELECT 'BEGIN IMMEDIATE datetime(''now'') INSERT OR IGNORE', "datetime(?)" FROM t WHERE a=?'''
        self.assertEqual(self.t(sql), sql[:-1] + '%s')

    def test_a_malformed_database_url_stops_the_process(self):
        """Never fall back to the (frozen) SQLite file when DATABASE_URL is set but unusable."""
        old = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = 'postgresql+psycopg://mnl@127.0.0.1/mnl'
        try:
            with self.assertRaises(SystemExit):
                dbm.database_url()
        finally:
            if old is None:
                os.environ.pop('DATABASE_URL', None)
            else:
                os.environ['DATABASE_URL'] = old

    def test_kinds(self):
        self.assertEqual(dbm.translate('BEGIN')[1], 'begin')
        with self.assertRaises(NotImplementedError):
            dbm.translate('PRAGMA foreign_keys=ON')
        self.assertEqual(dbm.translate(' delete FROM t')[1], 'dml')
        with self.assertRaises(NotImplementedError):
            dbm.translate('INSERT OR REPLACE INTO t VALUES(?)')
        with self.assertRaises(NotImplementedError):
            dbm.translate('SELECT ?1')


@pg_only
class PgStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db')

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def player(self):
        token, _, _ = self.store.session()
        self.store.command(token, 'first-' + token[:12], 0, 'mother_baby', 'start_day', {})
        return token

    def raw(self):
        """A connection outside the pool, on this Store's schema."""
        import psycopg
        c = psycopg.connect(dbm.database_url(), autocommit=True)
        c.execute('SELECT set_config(%s, %s, false)', ('search_path', self.store.pg.schema))
        self.addCleanup(c.close)
        return c

    def lock_row(self, token):
        """Hold the row lock of this save (as another command would) until release()."""
        c = self.raw()
        c.execute('BEGIN')
        c.execute('SELECT revision FROM sessions WHERE sid=%s FOR UPDATE', (self.store.key(token),))
        return c

    def test_backend_is_postgres(self):
        self.assertEqual(self.store.backend, 'pg')
        with self.store.connect() as db:
            self.assertEqual(db.dialect, 'pg')
        self.assertFalse(Path(self.store.path).exists())

    def test_rejected_sqlite_syntax_leaves_the_connection_idle(self):
        with self.store.connect() as db:
            for execute in (db.execute, db.pg):
                for sql in ('BEGIN IMMEDIATE', 'INSERT OR IGNORE INTO hits(k,at) VALUES(?,?)', "SELECT datetime('now')"):
                    with self.subTest(sql=sql, api=execute.__name__), self.assertRaises(NotImplementedError):
                        execute(sql, ('rejected', 1) if sql.startswith('INSERT') else ())
                    self.assertFalse(db.in_transaction)
            self.assertEqual(db.execute('SELECT 42').fetchone()[0], 42)

    def test_different_players_do_not_wait_for_each_other(self):
        a, b = self.player(), self.player()
        holder = self.lock_row(a)          # a's save is busy (row locked)
        t0 = time.perf_counter()
        out = self.store.command(b, 'b-cmd-000001', 1, 'mother_baby', 'advance', {})
        took = time.perf_counter() - t0
        holder.execute('ROLLBACK')
        self.assertEqual(out['revision'], 2)
        self.assertLess(took, 2.0)  # the lock timeout is 5 s: b never waited for a

    def test_same_player_is_serialized(self):
        a = self.player()
        holder = self.lock_row(a)
        done = []
        th = threading.Thread(target=lambda: done.append(self.store.command(a, 'a-cmd-000002', 1, 'mother_baby', 'advance', {})))
        th.start()
        time.sleep(0.6)
        self.assertEqual(done, [])         # waits for the row lock
        holder.execute('ROLLBACK')
        th.join(10)
        self.assertEqual(done[0]['revision'], 2)

    def test_a_command_waits_for_its_row_longer_than_the_default_lock_timeout(self):
        """A command's save must be written: its row lock waits BUSY_MS (like SQLite's writer
        turn), not the session lock_timeout, so a queue on one busy save does not fail it."""
        a = self.player()
        pool = self.store.pg
        pool.clear()
        old = pool.settings['lock_timeout']
        pool.settings['lock_timeout'] = '300'   # new connections: a 300 ms session lock_timeout
        try:
            holder = self.lock_row(a)
            done = []
            th = threading.Thread(target=lambda: done.append(self.store.command(a, 'a-cmd-patient', 1, 'mother_baby', 'advance', {})))
            th.start()
            time.sleep(1.5)                     # 5x the session lock_timeout
            self.assertEqual(done, [])          # still waiting, not failed
            holder.execute('ROLLBACK')
            th.join(10)
            self.assertEqual(done[0]['revision'], 2)
            with self.store.connect() as db:    # other statements keep the short session timeout
                self.assertEqual(db.execute("SELECT current_setting('lock_timeout')").fetchone()[0], '300ms')
        finally:
            pool.settings['lock_timeout'] = old
            pool.clear()

    def test_parallel_commands_on_one_save_lose_nothing(self):
        a = self.player()
        errors = []

        def one(i):
            try:
                self.store.command(a, f'par-{i:08d}', None, 'mother_baby', 'settings', dict(lang='en' if i % 2 else 'vi'), internal=True)
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=one, args=(i,)) for i in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(30)
        self.assertEqual(errors, [])
        self.assertEqual(self.store.read(a)[1], 1 + 8)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM receipts WHERE sid=?', (self.store.key(a),)).fetchone()[0], 1 + 8)

    def test_revision_conflict(self):
        a = self.player()
        with self.assertRaises(Conflict):
            self.store.command(a, 'stale-000001', 0, 'mother_baby', 'advance', {})
        again = self.store.command(a, 'first-' + a[:12], 0, 'mother_baby', 'start_day', {})
        self.assertTrue(again['replayed'])

    def test_pool_never_keeps_a_transaction_or_snapshot(self):
        a = self.player()
        with self.store.connect() as db:   # a SELECT whose rows are not all read
            db.execute('SELECT sid FROM sessions UNION ALL SELECT sid FROM sessions').fetchone()
        db = self.store.connect()          # a transaction left open by mistake
        db.execute('UPDATE sessions SET csrf=csrf')
        db.close()
        with self.assertRaises(ZeroDivisionError):
            with self.store.connect() as db:
                db.execute('UPDATE sessions SET csrf=csrf')
                raise ZeroDivisionError
        db = self.store.connect()          # a failed transaction
        db.execute('BEGIN')
        with self.assertRaises(dbm.Error):
            db.execute('SELECT 1/0')
        db.close()
        with self.assertRaises(dbm.Error):  # a failed autocommit statement
            with self.store.connect() as db:
                db.execute('SELECT nosuchcolumn FROM sessions')
        pool = self.store.pg
        self.assertGreater(len(pool.idle), 0)
        for raw, _ in pool.idle:
            self.assertEqual(raw.info.transaction_status, dbm.IDLE)
        pids = [raw.info.backend_pid for raw, _ in pool.idle]
        rows = self.raw().execute('SELECT pid, state, backend_xmin, backend_xid FROM pg_stat_activity WHERE pid = ANY(%s)', (pids,)).fetchall()
        self.assertEqual(len(rows), len(pids))
        for pid, state, xmin, xid in rows:
            self.assertEqual((state, xmin, xid), ('idle', None, None), pid)
        self.assertEqual(self.store.read(a)[1], 1)  # nothing of the above was committed... except csrf=csrf, a no-op

    def test_pool_caps_connections(self):
        pool = self.store.pg
        old = (pool.cap, pool.wait)
        pool.cap, pool.wait = pool.open, 0.3   # every open connection is idle now: none more may open
        try:
            held = [self.store.connect() for _ in range(len(pool.idle))]
            with self.assertRaises(dbm.PoolTimeout):
                self.store.connect()
            for db in held:
                db.close()
            self.store.connect().close()
        finally:
            pool.cap, pool.wait = old

    def test_timestamps_are_utc_text(self):
        a = self.player()
        with self.store.connect() as db:
            updated = db.execute('SELECT updated_at FROM sessions WHERE sid=?', (self.store.key(a),)).fetchone()[0]
            receipt = db.execute('SELECT created_at FROM receipts WHERE sid=?', (self.store.key(a),)).fetchone()['created_at']
            db.execute("SET TIME ZONE 'Pacific/Auckland'")
            hour = db.execute(f"SELECT {dbm.UTC_INTERVAL_TEXT}", ('-1 hour',)).fetchone()[0]
            now = db.execute('SELECT CURRENT_TIMESTAMP').fetchone()[0]
        for v in (updated, receipt, hour, now):
            self.assertRegex(v, TS)
            self.assertEqual(len(v), 19)
        py = dbm.utc_text()
        self.assertLessEqual(abs(time.mktime(time.strptime(now, dbm.FMT)) - time.mktime(time.strptime(py, dbm.FMT))), 2)
        self.assertEqual(dbm.utc_text(-3600)[:13], hour[:13])

    def test_rows_by_name_and_index_and_sums_are_ints(self):
        self.player()
        with self.store.connect() as db:
            r = db.execute('SELECT sid, revision FROM sessions').fetchone()
            self.assertEqual(r[0], r['sid'])
            self.assertEqual(dict(r), dict(sid=r['sid'], revision=r['revision']))
            total = db.execute('SELECT SUM(revision) FROM sessions').fetchone()[0]
            self.assertIs(type(total), int)

    def test_identity_ids_continue_after_a_copy(self):
        a = self.player()
        state = self.store.read(a)[0]
        with self.store.connect() as db:   # rows copied with their ids, as the migration does
            db.execute("INSERT INTO player_feedback(id,sid,kind,text,created_at,updated_at) VALUES(500,'x','bug','copied',1,1)")
        with self.store.connect() as db:
            self.assertEqual(pg_schema.reset_sequences(db)['player_feedback'], 501)
        self.assertEqual(pfb.submit(self.store, a, state, dict(kind='bug', text='Sau khi chép'))['id'], 501)
        with self.store.connect() as db:   # SQLite's sqlite_sequence may be higher (deleted rows)
            pg_schema.reset_sequences(db, {'player_feedback': 900})
        self.assertEqual(pfb.submit(self.store, a, state, dict(kind='idea', text='Không dùng lại số cũ'))['id'], 901)

    def test_best_effort_write_gives_up_on_a_locked_row(self):
        a = self.player()
        holder = self.lock_row(a)
        t0 = time.perf_counter()
        out = self.store.transaction(lambda db: db.execute('UPDATE sessions SET csrf=csrf WHERE sid=?', (self.store.key(a),)).rowcount, 200)
        holder.execute('ROLLBACK')
        self.assertIsNone(out)
        self.assertLess(time.perf_counter() - t0, 2.0)

    def test_schema_is_complete_and_idempotent(self):
        with self.store.connect() as db:
            self.assertEqual(pg_schema.missing_tables(db), [])
            self.assertFalse(pg_schema.ensure(db))
            self.assertEqual(db.pg("SELECT attcompression FROM pg_attribute WHERE attrelid='sessions'::regclass AND attname='state'").fetchone()[0], 'l')
            db.execute('DROP TABLE push_daily')
        again = Store(Path(self.tmp.name) / 'g.db')   # a missing table is created again at start-up
        with again.connect() as db:
            self.assertEqual(pg_schema.missing_tables(db), [])

    # ---- dead pooled connections (a PostgreSQL restart, an OOM kill, pg_terminate_backend)
    def fill_pool(self, n=4):
        held = [self.store.connect() for _ in range(n)]
        for db in held:
            db.execute('SELECT 1')
        for db in held:
            db.close()
        pool = self.store.pg
        self.assertGreaterEqual(len(pool.idle), n)
        return [raw.info.backend_pid for raw, _ in pool.idle]

    def terminate(self, pids):
        n = self.raw().execute('SELECT COUNT(*) FROM (SELECT pg_terminate_backend(p) FROM unnest(%s::int[]) p) x', (pids,)).fetchone()[0]
        self.assertEqual(n, len(pids))
        time.sleep(0.2)

    def test_requests_succeed_after_the_server_drops_pooled_connections(self):
        a = self.player()
        self.terminate(self.fill_pool())
        held = [self.store.connect() for _ in range(4)]   # all 4 dead ones at once (the pool is LIFO)
        for db in held:   # each dead connection is replaced on its first statement
            self.assertEqual(db.execute('SELECT 1').fetchone()[0], 1)
        for db in held:
            db.close()
        self.terminate(self.fill_pool())
        held = [self.store.connect() for _ in range(4)]
        for i, db in enumerate(held):   # a write as the very first statement: its BEGIN is retried
            db.execute('INSERT INTO hits(k,at) VALUES(?,?)', ('after-restart', i))
            db.commit()
            db.close()
        self.assertEqual(self.store.read(a)[1], 1)
        self.assertEqual(self.store.command(a, 'after-restart-1', 1, 'mother_baby', 'advance', {})['revision'], 2)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM hits WHERE k='after-restart'").fetchone()[0], 4)
        pool = self.store.pg
        self.assertEqual(pool.open, len(pool.idle))   # no slot leaked by the swaps

    def test_long_idle_connections_are_checked_before_use(self):
        pool = self.store.pg
        dead = self.fill_pool()
        self.terminate(dead)
        old, pool.check = pool.check, 0.0   # every idle connection counts as "long idle"
        try:
            with self.store.connect() as db:
                self.assertNotIn(db.raw.info.backend_pid, dead)
                self.assertFalse(db._used)   # handed out alive: no retry was needed
        finally:
            pool.check = old
        self.assertEqual(pool.open, len(pool.idle))

    def test_no_retry_once_a_transaction_has_written(self):
        db = self.store.connect()
        db.execute("INSERT INTO hits(k,at) VALUES('in-flight',1)")
        self.terminate([db.raw.info.backend_pid])
        with self.assertRaises(dbm.Error):
            db.execute("INSERT INTO hits(k,at) VALUES('in-flight',2)")
        db.close()
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM hits WHERE k='in-flight'").fetchone()[0], 0)
        self.assertEqual(self.store.pg.open, len(self.store.pg.idle))

    def test_statement_errors_are_not_retried(self):
        with self.assertRaises(dbm.DataError):   # a NUL in text: bad client data, a 400 in server.py
            with self.store.connect() as db:
                db.execute('SELECT 1 FROM hits WHERE k=?', ('a\x00b',))
        token, _, _ = self.store.session()
        with self.assertRaises(GameError):
            self.store.command(token, 'rid\x00-12345678', 0, None, 'settings', {})

    def test_shared_limits_live_in_postgres(self):
        import server
        lim = server.SharedLimits(self.store)
        self.assertEqual([lim.hit('acct-login:1.2.3.4', 3, 60) for _ in range(4)], [True, True, True, False])
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])
        lim.prune()
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM hits').fetchone()[0], 3)


if __name__ == '__main__':
    unittest.main()
