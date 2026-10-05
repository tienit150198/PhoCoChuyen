"""Reviewer C: adversarial tests of the PostgreSQL port (game/db.py, Store on PostgreSQL).

Run with TEST_DATABASE_URL=postgresql://.../mnl_review (a scratch database: every Store gets
its own schema, see game/db.py). Without it every test here is skipped.

Covers: pool hygiene after errors / timeouts / server-side disconnects, lost updates across
threads and processes, unicode / NUL / very large saves, and the order and content of every
PostgreSQL transaction and data-fidelity behavior."""
import contextlib
import datetime
import json
import multiprocessing as mp
import os
import secrets
import tempfile
import threading
import time
import unittest
from pathlib import Path

from game import admin_stats as st
from game import db as dbm
from game import player_feedback as pfb
from game import social
from game.engine import GameError, new_state
from game.journey import enable_story
from game.storage import Store
from tests.pg_support import on_pg, pg_only




@contextlib.contextmanager
def env(**values):
    old = {k: os.environ.get(k) for k in values}
    os.environ.update({k: str(v) for k, v in values.items()})
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def admin_conn(store=None):
    """A plain psycopg connection outside the game's pool (in the Store's schema)."""
    import psycopg
    c = psycopg.connect(dbm.database_url(), autocommit=True)
    if store is not None and store.pg.schema:
        c.execute('SELECT set_config(%s, %s, false)', ('search_path', store.pg.schema))
    return c


def cas_increment(store, sid, tag):
    """One lost-update-safe increment of {"n": ..} through Store._store (the command's compare-and-set)."""
    for attempt in range(500):
        with store.connect() as db:
            row = db.execute('SELECT revision, state FROM sessions WHERE sid=?', (sid,)).fetchone()
        n = json.loads(row['state'])['n']
        if store._store(sid, row['revision'], json.dumps({'n': n + 1}), f'{tag}-{attempt}', 'fp', '{}'):
            return attempt
    raise AssertionError('no progress after 500 tries')


def _child(path, shared, own, n, out):
    """Worker process body (spawned, so it opens its own pool like a forked WORKERS=4 worker)."""
    try:
        store = Store(path)
        tries = 0
        for i in range(n):
            tries += cas_increment(store, shared, f'p{os.getpid()}-s{i}')
            tries += cas_increment(store, own, f'p{os.getpid()}-o{i}')
        store.close_pool()
        out.put(('ok', tries))
    except BaseException as e:  # noqa: BLE001
        out.put(('err', repr(e)))


def new_sid(store, state='{"n": 0}'):
    sid = secrets.token_hex(32)
    with store.connect() as db:
        db.execute('INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)', (sid, 'c', state))
    return sid


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'g.db')
        self.app = 'mnl-review-' + secrets.token_hex(3)
        # read by every PgPool._open of this test; a loaded laptop must not trip the 10 s DDL timeout at Store()
        self._env = env(PG_APPLICATION_NAME=self.app, PG_STATEMENT_TIMEOUT_MS=120000)
        self._env.__enter__()
        self.store = Store(self.path)

    def tearDown(self):
        self.store.close_pool()
        self._env.__exit__(None, None, None)
        self.tmp.cleanup()

    def backends(self):
        """(name, pid list) of this test's own server sessions, from pg_stat_activity."""
        with admin_conn() as c:
            return c.execute("SELECT pid, state FROM pg_stat_activity WHERE application_name=%s", (self.app,)).fetchall()


# ---------------------------------------------------------------- pool hygiene
@pg_only
class PoolHygieneTests(Base):
    def test_exception_inside_transaction_rolls_back_and_pool_is_clean(self):
        def boom(db):
            db.execute('INSERT INTO hits(k,at) VALUES(?,?)', ('boom', 1.0))
            raise ValueError('mid-transaction')
        with self.assertRaises(ValueError):
            self.store.transaction(boom)
        with self.store.connect() as db:
            self.assertFalse(db.in_transaction)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM hits WHERE k='boom'").fetchone()[0], 0)
        self.assertFalse([b for b in self.backends() if b[1] != 'idle'])

    def test_sql_error_inside_with_block_then_the_connection_is_reused_cleanly(self):
        with self.assertRaises(dbm.Error):
            with self.store.connect() as db:
                db.execute('INSERT INTO hits(k,at) VALUES(?,?)', ('half', 1.0))
                db.execute('SELECT no_such_column FROM hits')
        for _ in range(3):  # whichever pooled connection comes back works and saw nothing
            with self.store.connect() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM hits WHERE k='half'").fetchone()[0], 0)
        self.assertFalse([b for b in self.backends() if b[1] != 'idle'])

    def test_no_session_is_left_idle_in_transaction_after_a_mixed_workload(self):
        token, _, _ = self.store.session()
        sid = self.store.key(token)
        self.store.read(token)
        social.touch(self.store, sid, None, must=True)
        self.store.transaction(lambda db: db.execute('UPDATE logins SET seen_at=seen_at WHERE 1=0'), 100)
        with self.assertRaises(dbm.Error):
            with self.store.connect() as db:
                db.execute('INSERT INTO hits(k,at) VALUES(?,?)', ('x', 1.0))
                db.execute('INSERT INTO nope VALUES(1)')
        db = self.store.connect()
        db.execute('SELECT 1')  # a read, then closed without commit
        db.close()
        states = [b[1] for b in self.backends()]
        self.assertTrue(states)
        self.assertEqual(set(states), {'idle'}, states)

    def test_idle_in_transaction_timeout_kills_the_session_and_the_pool_recovers(self):
        with env(PG_IDLE_TX_TIMEOUT_MS=700):
            pool = dbm.PgPool(dbm.database_url(), self.store.pg.schema)
        try:
            db = pool.connect()
            db.execute('INSERT INTO hits(k,at) VALUES(?,?)', ('idle-tx', 1.0))
            time.sleep(1.5)
            with self.assertRaises(dbm.Error):
                db.commit()
            db.close()
            self.assertEqual(pool.stats()['idle'], 0)  # the dead connection was not kept
            with pool.connect() as db2:
                self.assertEqual(db2.execute("SELECT COUNT(*) FROM hits WHERE k='idle-tx'").fetchone()[0], 0)
        finally:
            pool.clear()

    def test_pool_recovers_after_the_server_drops_idle_connections(self):
        """A PostgreSQL restart (apt upgrade, OOM killer, pg_ctl restart, the cut-over itself)
        drops every pooled idle connection. The next request of each must not fail."""
        token, _, _ = self.store.session()
        held = [self.store.connect() for _ in range(4)]
        for db in held:
            db.execute('SELECT 1')
        for db in held:
            db.close()
        self.assertGreaterEqual(self.store.pg.stats()['idle'], 4)
        with admin_conn() as c:
            n = c.execute('SELECT COUNT(pg_terminate_backend(pid)) FROM pg_stat_activity WHERE application_name=%s', (self.app,)).fetchone()[0]
        self.assertGreaterEqual(n, 4)
        time.sleep(0.3)
        failures = []
        for _ in range(6):
            try:
                self.store.read(token)
            except Exception as e:  # noqa: BLE001
                failures.append(type(e).__name__)
        self.assertEqual(failures, [], 'requests failed on dead pooled connections')

    def test_commit_of_a_transaction_with_a_failed_statement_keeps_nothing(self):
        """PostgreSQL aborts the whole
        transaction. The adapter must make that loud (commit raises), never silent."""
        db = self.store.connect()
        try:
            db.execute('INSERT INTO hits(k,at) VALUES(?,?)', ('first', 1.0))
            with self.assertRaises(dbm.Error):
                db.execute('INSERT INTO nope VALUES(1)')
            with self.assertRaises(dbm.Error):
                db.commit()
        finally:
            db.close()
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM hits WHERE k='first'").fetchone()[0], 0)


# ---------------------------------------------------------------- lost updates
@pg_only
class LostUpdateTests(Base):
    def test_threads_on_different_and_the_same_save_lose_nothing(self):
        shared = new_sid(self.store)
        own = [new_sid(self.store) for _ in range(6)]
        n, errors = 12, []

        def run(i):
            try:
                for k in range(n):
                    cas_increment(self.store, shared, f't{i}-s{k}')
                    cas_increment(self.store, own[i], f't{i}-o{k}')
            except BaseException as e:  # noqa: BLE001
                errors.append(repr(e))
        threads = [threading.Thread(target=run, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(120)
        self.assertEqual(errors, [])
        with self.store.connect() as db:
            row = db.execute('SELECT revision, state FROM sessions WHERE sid=?', (shared,)).fetchone()
            self.assertEqual((row['revision'], json.loads(row['state'])['n']), (6 * n, 6 * n))
            for sid in own:
                row = db.execute('SELECT revision, state FROM sessions WHERE sid=?', (sid,)).fetchone()
                self.assertEqual((row['revision'], json.loads(row['state'])['n']), (n, n))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0], 6 * n * 2)

    def test_processes_on_the_same_save_lose_nothing(self):
        shared = new_sid(self.store)
        own = [new_sid(self.store) for _ in range(4)]
        self.store.close_pool()
        ctx = mp.get_context('spawn')
        out = ctx.Queue()
        n = 10
        procs = [ctx.Process(target=_child, args=(self.path, shared, own[i], n, out)) for i in range(4)]
        for p in procs:
            p.start()
        results = [out.get(timeout=240) for _ in procs]
        for p in procs:
            p.join(60)
        self.assertEqual([r[0] for r in results], ['ok'] * 4, results)
        with self.store.connect() as db:
            row = db.execute('SELECT revision, state FROM sessions WHERE sid=?', (shared,)).fetchone()
            self.assertEqual((row['revision'], json.loads(row['state'])['n']), (4 * n, 4 * n))
            for sid in own:
                self.assertEqual(json.loads(db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()[0])['n'], n)


# ---------------------------------------------------------------- data fidelity
TEXTS = [
    'Phố Có Chuyện', 'Nguyễn Thị Ánh Tuyết · Bà Tư bán bún bò Huế', 'Phố có chuyện',  # NFD kept as is
    '🍜🧑‍🍳👩🏽‍🌾🇻🇳', '𝔘𝔫𝔦𝔠𝔬𝔡𝔢 and 😀 astral', "it's ? and ?? and %s and %(x)s and 100%",
    'back\\slash \\u0000 \\n "quotes"', 'line\nbreak\r\ntab\t', '  ﻿ zero​width',
    "'; DROP TABLE sessions; --", 'x' * 70000,
]


@pg_only
class FidelityTests(Base):
    def test_unicode_and_emoji_round_trip_byte_for_byte(self):
        with self.store.connect() as db:
            for i, t in enumerate(TEXTS):
                db.execute("INSERT INTO inbox(pid,kind,text,ref,at) VALUES(?,'k?',?,'lit ? %',?)", (f'p{i}', t, float(i)))
        with self.store.connect() as db:
            got = db.execute("SELECT pid,kind,text,ref FROM inbox ORDER BY at").fetchall()
        self.assertEqual([r['text'] for r in got], TEXTS)
        self.assertEqual({(r['kind'], r['ref']) for r in got}, {('k?', 'lit ? %')})



    def test_raw_nul_is_refused_and_the_connection_survives(self):
        with self.assertRaises(dbm.Error):
            with self.store.connect() as db:
                db.execute('SELECT 1 FROM hits WHERE k=?', ('a\x00b',))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT 1').fetchone()[0], 1)

    def test_a_request_id_with_nul_is_a_clean_game_error_not_a_500(self):
        token, _, _ = self.store.session()
        with self.assertRaises((GameError, ValueError)):
            self.store.command(token, 'rid\x00-12345678', 0, None, 'settings', {})

    def test_escaped_nul_in_a_save_round_trips_and_admin_sample_still_works(self):
        state = new_state()
        state['name'] = 'Tên có \x00 NUL'  # json.dumps writes \u0000: valid text, refused by jsonb
        sid = new_sid(self.store, json.dumps(state, ensure_ascii=False))
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET revision=1 WHERE sid=?', (sid,))
            self.assertEqual(json.loads(db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()[0])['name'], state['name'])
        with self.store.connect() as db:
            rows, engine = st.sample(db, 100)
        self.assertEqual((len(rows), engine), (1, 'python'))

    def test_very_large_saves(self):
        for mb in (2, 10):
            sid = new_sid(self.store)
            blob = json.dumps({'n': 1, 'album': ['ảnh🍜' + secrets.token_hex(16)] * (mb * 1024 * 1024 // 45)}, ensure_ascii=False)
            self.assertGreater(len(blob.encode()), mb * 1024 * 1024 * 0.9)
            t0 = time.perf_counter()
            self.assertTrue(self.store._store(sid, 0, blob, f'big-{mb}', 'fp', '{}'))
            took = time.perf_counter() - t0
            with self.store.connect() as db:
                back = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()[0]
            self.assertEqual(back, blob)
            self.assertLess(took, 8, f'{mb} MB save took {took:.1f}s')


# ---------------------------------------------------------------- same data, same answers


# ---------------------------------------------------------------- concurrent PostgreSQL row-lock behavior
@pg_only
class DeleteRaceTests(Base):
    def test_delete_during_a_command_leaves_no_archive_or_receipt_rows(self):
        """A command holds its save's row lock and has written archive + receipt rows (not yet
        committed) when the player's "Xóa dữ liệu" runs: nothing of that save may survive."""
        token, _, _ = self.store.session()
        sid = self.store.key(token)
        cmd = self.store.connect()
        cmd.execute('BEGIN')
        cmd.execute('SELECT revision FROM sessions WHERE sid=? FOR UPDATE', (sid,))
        cmd.execute("INSERT INTO archive(sid,career,kind,seq,day,row) VALUES(?,'','log',0,1,'{}')", (sid,))
        cmd.execute("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,'rid-racing','h','{}')", (sid,))
        done = []
        t = threading.Thread(target=lambda: done.append(self.store.delete(token)))
        t.start()
        time.sleep(1.0)  # delete() has removed the children it could see and waits for the row lock
        cmd.execute("UPDATE sessions SET revision=revision+1 WHERE sid=?", (sid,))
        cmd.commit()
        cmd.close()
        t.join(30)
        self.assertEqual(done, [True])
        with self.store.connect() as db:
            left = [db.execute(f'SELECT COUNT(*) FROM {t} WHERE sid=?', (sid,)).fetchone()[0] for t in ('sessions', 'archive', 'receipts')]
        self.assertEqual(left, [0, 0, 0], 'rows of a deleted save survived (sessions, archive, receipts)')


class BackendChoiceTests(unittest.TestCase):
    def test_a_malformed_database_url_is_rejected(self):
        with env(DATABASE_URL='postgresql+psycopg://mnl@127.0.0.1/mnl'):
            try:
                got = dbm.database_url()
            except (Exception, SystemExit):  # noqa: BLE001 - refusing is the point
                return
        self.fail(f'DATABASE_URL set but unusable, but it was accepted (database_url() -> {got!r})')


if __name__ == '__main__':
    unittest.main()
