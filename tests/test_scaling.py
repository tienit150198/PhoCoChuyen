import psycopg
"""Load-related guarantees: optimistic commands, best-effort writes, lazy saves,
pruning, shared rate limits, the static fast path and WORKERS (pre-fork)."""
import concurrent.futures
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock
import urllib.error
import urllib.request
from pathlib import Path

from game import social
from game.engine import GameError, new_state
from game.storage import FRESH, Conflict, Store
from tests.helpers import Journey
from tests.pg_support import on_pg

ROOT = Path(__file__).resolve().parents[1]


class Base(unittest.TestCase):
    story = False

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'game.db'
        self.store = Store(self.path, story=self.story)
        self.token, self.csrf, _ = self.store.session()

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def cmd(self, rid, rev, action='advance', career='mother_baby', payload=None, internal=False, token=None):
        return self.store.command(token or self.token, rid, rev, career, action, payload or {}, internal=internal)

    def raw(self, sql, args=()):
        """Read fixture rows through PostgreSQL."""
        with self.store.connect() as db:
            return [tuple(r) for r in db.execute(sql, args).fetchall()]

    def pg_blocker(self, *tables):
        """Another PostgreSQL session holds write locks on `tables` (reads still work)."""
        import psycopg
        from game import db as dbm
        c = psycopg.connect(dbm.database_url())
        c.execute('SELECT set_config(%s, %s, false)', ('search_path', self.store.pg.schema))
        c.execute(f'LOCK TABLE {", ".join(tables)} IN EXCLUSIVE MODE')
        return c


class OptimisticCommandTests(Base):
    def setUp(self):
        super().setUp()
        self.cmd('open-0001', 0, 'start_day')

    def test_concurrent_commands_same_revision_one_wins(self):
        """Many tabs send a command for the same revision at once: exactly one is stored."""
        def go(i):
            try:
                return self.cmd(f'tab-{i:04d}-x', 1)['revision']
            except Conflict as e:
                return e.code
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            out = list(pool.map(go, range(16)))
        self.assertEqual(out.count(2), 1, out)
        self.assertEqual(out.count('revision_conflict'), 15, out)
        state, rev, _ = self.store.read(self.token)
        self.assertEqual(rev, 2)
        self.assertEqual(self.raw('SELECT COUNT(*) FROM receipts')[0][0], 2)

    def test_concurrent_internal_commands_all_applied(self):
        """Internal commands have no revision guard: under contention they are recomputed
        on the newer save (or computed under the lock), never lost."""
        def go(i):
            # On a starved machine a command can time out waiting for the save (a clean
            # rollback, a 500 for the client): the client then retries with the SAME request
            # id, which must apply it exactly once.
            for attempt in range(3):
                try:
                    return self.cmd(f'srv-{i:04d}-x', None, 'advance', internal=True)['revision']
                except dbm.Error:
                    if attempt == 2:
                        raise
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            revs = sorted(pool.map(go, range(20)))
        self.assertEqual(revs, list(range(2, 22)))   # 20 distinct steps: none lost, none applied twice
        self.assertEqual(self.store.read(self.token)[1], 21)
        per_id = self.raw("SELECT request_id, COUNT(*) FROM receipts WHERE request_id LIKE 'srv-%' GROUP BY request_id")
        self.assertEqual(sorted(r[0] for r in per_id), [f'srv-{i:04d}-x' for i in range(20)])
        self.assertEqual({r[1] for r in per_id}, {1})   # exactly one receipt per applied command

    def test_idempotent_retry_concurrent(self):
        """The same request id sent 12 times at once (client retries) is applied once."""
        def go(_):
            return self.cmd('retry-000001', 1)
        with concurrent.futures.ThreadPoolExecutor(6) as pool:
            out = list(pool.map(go, range(12)))
        self.assertEqual({o['revision'] for o in out}, {2})
        self.assertEqual(sum(not o['replayed'] for o in out), 1)
        self.assertEqual(self.store.read(self.token)[1], 2)

    def test_retry_after_success_replays_with_current_state(self):
        first = self.cmd('req-aaaaaaaa', 1)
        again = self.cmd('req-aaaaaaaa', 1)
        self.assertTrue(again['replayed'])
        self.assertEqual(again['revision'], first['revision'])
        self.assertEqual(again['result'], first['result'])
        with self.assertRaises(Conflict) as ctx:
            self.cmd('req-aaaaaaaa', 2, 'end_day')
        self.assertEqual(ctx.exception.code, 'idempotency_conflict')

    def test_revision_moved_during_compute_is_a_conflict(self):
        """Another write lands while this command is being computed (lock-free):
        the compare-and-set fails and the command answers revision_conflict."""
        real = self.store._compute
        calls = []

        def racing(*a, **k):
            out = real(*a, **k)
            if not calls:
                calls.append(1)
                self.cmd('other-tab-01', 1)  # lands first
            return out
        self.store._compute = racing
        with self.assertRaises(Conflict) as ctx:
            self.cmd('slow-tab-001', 1)
        self.assertEqual(ctx.exception.code, 'revision_conflict')
        self.assertEqual(self.store.read(self.token)[1], 2)
        self.assertEqual(self.raw("SELECT COUNT(*) FROM receipts WHERE request_id='slow-tab-001'")[0][0], 0)

    def test_internal_command_recomputed_after_race(self):
        real = self.store._compute
        seen, inner = [], []

        def racing(sid, text, *a, **k):
            if inner:
                return real(sid, text, *a, **k)
            seen.append(json.loads(text)['careers']['mother_baby']['turn'])
            out = real(sid, text, *a, **k)
            if len(seen) == 1:
                inner.append(1)
                self.cmd('other-tab-01', 1)
                inner.clear()
            return out
        self.store._compute = racing
        out = self.cmd('srv-internal-1', None, internal=True)
        self.assertEqual(out['revision'], 3)
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[1], seen[0] + 1)  # the second compute started from the newer save

    def test_game_error_on_stale_snapshot_becomes_conflict(self):
        """A rule error decided on a save that changed meanwhile is re-judged (-> 409), not a 400."""
        real = self.store._compute
        calls = []

        def racing(*a, **k):
            if not calls:
                calls.append(1)
                self.cmd('other-tab-01', 1)
                raise GameError('stale rule error')
            return real(*a, **k)
        self.store._compute = racing
        with self.assertRaises(Conflict):
            self.cmd('stale-0000001', 1)

    def test_game_error_without_race_is_reported(self):
        with self.assertRaises(GameError) as ctx:
            self.cmd('bad-00000001', 1, 'buy_upgrade', payload={'item': 'unknown'})
        self.assertNotIsInstance(ctx.exception, Conflict)
        self.assertEqual(self.store.read(self.token)[1], 1)

    def test_heavy_contention_falls_back_to_locked_path(self):
        """Every lock-free attempt loses the race: the command is then computed under the lock."""
        real = self.store._compute
        inner, outer = [], []

        def always_racing(*a, **k):
            out = real(*a, **k)
            if not inner:
                outer.append(1)
                inner.append(1)
                self.cmd(f'noise-{len(outer):06d}', None, internal=True)
                inner.clear()
            return out
        self.store._compute = always_racing
        locked, real_locked = [], self.store._command_locked

        def fallback(*a, **k):
            locked.append(1)
            inner.append(1)  # nobody can write while the fallback holds the lock
            try:
                return real_locked(*a, **k)
            finally:
                inner.clear()
        self.store._command_locked = fallback
        out = self.cmd('srv-final-001', None, internal=True)
        self.assertEqual(locked, [1])
        self.assertEqual(len(outer), 4)  # every lock-free attempt lost to a noise write
        self.assertEqual(out['revision'], 1 + 4 + 1)
        self.assertEqual(self.store.read(self.token)[1], 6)
        self.assertEqual(self.raw("SELECT COUNT(*) FROM receipts WHERE request_id='srv-final-001'")[0][0], 1)

    def test_command_does_not_hold_write_lock_while_computing(self):
        """While a command is computing, another connection can still write."""
        real = self.store._compute
        wrote = []

        def slow(*a, **k):
            self.assertEqual(self.store.transaction(lambda db: db.execute("UPDATE logins SET seen_at=seen_at WHERE 1=0").rowcount, 200), 0)
            wrote.append(True)
            return real(*a, **k)
        self.store._compute = slow
        self.cmd('compute-lock1', 1)
        self.assertEqual(wrote, [True])


class BestEffortTests(Base):
    def lock_db(self):
        return self.pg_blocker('profiles', 'logins', 'sessions')

    def test_social_me_survives_a_busy_database(self):
        social.ensure(self.store)
        state = self.store.read(self.token)[0]
        social.get(self.store, self.token, state, 'me', {})  # creates the profile row
        with self.store.connect() as db:
            db.execute('UPDATE profiles SET seen=0, updated=0')
        blocker = self.lock_db()
        try:
            t = time.monotonic()
            out = social.get(self.store, self.token, state, 'me', {})
            self.assertLess(time.monotonic() - t, 3)
            self.assertIn('community', out)
        finally:
            blocker.rollback()
            blocker.close()
        # nothing was written while busy; the next visit refreshes it
        self.assertEqual(self.raw('SELECT seen FROM profiles')[0][0], 0)
        social.get(self.store, self.token, state, 'me', {})
        self.assertGreater(self.raw('SELECT seen FROM profiles')[0][0], 0)

    def test_social_me_without_profile_row_while_busy(self):
        social.ensure(self.store)
        state = self.store.read(self.token)[0]
        blocker = self.lock_db()
        try:
            out = social.get(self.store, self.token, state, 'me', {})
            self.assertIsNone(out['me'])
        finally:
            blocker.rollback()
            blocker.close()

    def test_touch_throttled(self):
        social.ensure(self.store)
        state = self.store.read(self.token)[0]
        sid = self.store.key(self.token)
        social.touch(self.store, sid, state)
        before = self.raw('SELECT seen, updated FROM profiles')[0]
        social.touch(self.store, sid, state)
        self.assertEqual(self.raw('SELECT seen, updated FROM profiles')[0], before)

    def test_login_seen_at_is_best_effort(self):
        from game import accounts
        out = accounts.register(self.store, self.token, dict(username='bestuser', password='mat-khau-1', confirm='mat-khau-1', display='Best'))
        token = out['token']
        with self.store.connect() as db:
            db.execute("UPDATE logins SET seen_at=to_char((statement_timestamp() AT TIME ZONE 'UTC') - interval '2 hours', 'YYYY-MM-DD HH24:MI:SS')")
        blocker = self.lock_db()
        try:
            t = time.monotonic()
            got, csrf, created = self.store.session(token)
            self.assertLess(time.monotonic() - t, 3)
            self.assertEqual((got, created), (token, False))
        finally:
            blocker.rollback()
            blocker.close()
        self.store.session(token)
        self.assertTrue(self.raw("SELECT seen_at>to_char((statement_timestamp() AT TIME ZONE 'UTC') - interval '10 minutes', 'YYYY-MM-DD HH24:MI:SS') FROM logins")[0][0])


    def test_pool_rolls_back_uncommitted_work(self):
        db = self.store.connect()
        db.execute("UPDATE sessions SET revision=99")
        db.close()  # back to the pool without commit: discarded, like a real close
        self.assertEqual(self.raw('SELECT revision FROM sessions')[0][0], 0)
        with self.store.connect() as db2:
            self.assertFalse(db2.in_transaction)


class LazySaveTests(Base):
    story = True

    def setUp(self):
        env = unittest.mock.patch.dict(os.environ, {'LAZY_SAVES': '1'})
        env.start()
        self.addCleanup(env.stop)
        super().setUp()

    def test_off_by_default_writes_a_full_save(self):
        with unittest.mock.patch.dict(os.environ, {'LAZY_SAVES': '0'}):
            token, _, _ = self.store.session()
        text = self.raw('SELECT state FROM sessions WHERE sid=?', (self.store.digest(token),))[0][0]
        self.assertEqual(json.loads(text), self.store.read(token)[0])  # old servers can read it

    def test_never_played_guest_registers_exports_and_is_skipped_by_stats(self):
        from game import accounts, admin_stats
        social.ensure(self.store)
        admin_stats.ensure(self.store)
        with self.store.connect() as db:
            rows, _ = admin_stats.sample(db)
        self.assertEqual(rows, [])  # revision 0: never sampled
        out = accounts.register(self.store, self.token, dict(username='freshguest', password='mat-khau-1', confirm='mat-khau-1', display='Khach Moi'))
        state, rev, _ = self.store.read(out['token'])
        self.assertEqual(state['name'], 'Khach Moi')  # the adopted name was a real first command
        self.assertEqual(rev, 1)
        self.assertNotEqual(self.raw('SELECT state FROM sessions')[0][0], FRESH)
        other, _, _ = self.store.session()
        self.assertTrue(accounts.has_progress(self.store.read(other)[0]) is False)

    def test_new_session_stores_a_marker_not_a_save(self):
        text, rev = self.raw('SELECT state, revision FROM sessions')[0]
        self.assertEqual((text, rev), (FRESH, 0))
        a = self.store.read(self.token)
        b = self.store.read(self.token)
        self.assertEqual(a, b)  # rebuilt identically (story seed from the sid)
        self.assertTrue(a[0]['journey']['story'])
        self.assertEqual(a[1], 0)

    def test_first_command_materialises_the_save(self):
        state, rev, _ = self.store.read(self.token)
        out = self.store.command(self.token, 'first-000001', 0, None, 'settings', {'sound': False})
        self.assertEqual(out['revision'], 1)
        text = self.raw('SELECT state FROM sessions')[0][0]
        saved = json.loads(text)
        self.assertFalse(saved['settings']['sound'])
        self.assertEqual(saved['journey']['seed'], state['journey']['seed'])


class PruneTests(Base):
    def add_session(self, rev=0, state=None, days_idle=5):
        token, csrf, _ = self.store.session()
        sid = self.store.digest(token)
        text = FRESH if state is None else json.dumps(state)
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET revision=?, state=?, updated_at=to_char((statement_timestamp() AT TIME ZONE 'UTC') + CAST(? AS interval), 'YYYY-MM-DD HH24:MI:SS') WHERE sid=?", (rev, text, f'-{days_idle} days', sid))
            db.execute('INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)', (sid, 'r-' + sid[:10], 'h', '{}'))
        return token, sid

    def test_prune_guests(self):
        social.ensure(self.store)
        from game import accounts
        gone_fresh = self.add_session()[1]
        gone_one = self.add_session(1, new_state())[1]
        played = new_state()
        played['careers']['mother_baby']['started'] = True
        kept_progress = self.add_session(1, played)[1]           # e.g. an imported backup: revision 1 but real progress
        kept_played = self.add_session(5, new_state())[1]
        kept_recent = self.add_session(0, None, days_idle=1)[1]
        tok, kept_account = self.add_session()
        accounts.register(self.store, tok, dict(username='acctuser', password='mat-khau-1', confirm='mat-khau-1', display='Acct'))
        tok2, kept_named = self.add_session()
        social.post(self.store, tok2, self.store.read(tok2)[0], 'profile', dict(name='Ten Quan', bio='', avatar='🌸', visible=True))
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET updated_at=to_char((statement_timestamp() AT TIME ZONE 'UTC') - interval '5 days', 'YYYY-MM-DD HH24:MI:SS'), revision=0 WHERE sid IN (?,?)", (kept_account, kept_named))
        n = self.store.prune_guests(3)
        sids = {r[0] for r in self.raw('SELECT sid FROM sessions')}
        self.assertEqual(n, 2)
        self.assertNotIn(gone_fresh, sids)
        self.assertNotIn(gone_one, sids)
        for sid in (kept_progress, kept_played, kept_recent, kept_account, kept_named):
            self.assertIn(sid, sids)
        receipt_sids = {r[0] for r in self.raw('SELECT sid FROM receipts')}
        self.assertFalse({gone_fresh, gone_one} & receipt_sids)

    def test_prune_receipts_age_and_cap(self):
        sid = self.store.key(self.token)
        with self.store.connect() as db:
            db.executemany("INSERT INTO receipts(sid,request_id,request_hash,result,created_at) VALUES(?,?,?,?,to_char((statement_timestamp() AT TIME ZONE 'UTC') + CAST(? AS interval), 'YYYY-MM-DD HH24:MI:SS'))",
                           [(sid, f'old-{i}', 'h', '{}', '-3 days') for i in range(30)] + [(sid, f'new-{i:04d}', 'h', '{}', '-1 hours') for i in range(250)])
        n = self.store.prune_receipts(2, 200)
        self.assertEqual(n, 30 + 50)
        left = [r[0] for r in self.raw('SELECT request_id FROM receipts ORDER BY created_at, request_id')]
        self.assertEqual(len(left), 200)
        self.assertEqual(left[0], 'new-0050')

    def test_prune_batches_and_keeps_accounts(self):
        # the historic prune(): anonymous saves idle for months go, with their receipts
        token, sid = self.add_session(5, new_state(), days_idle=200)
        out = self.store.prune(180)
        self.assertEqual(out['sessions'], 1)
        self.assertNotIn(sid, {r[0] for r in self.raw('SELECT sid FROM sessions')})


class SharedLimitTests(unittest.TestCase):

    def test_shared_between_processes(self):
        import server
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'limits')
            self.addCleanup(store.close_pool)
            a = server.SharedLimits(store)
            b = server.SharedLimits(store)  # another worker
            got = [x.hit('ai-global', 3, 60) for x in (a, b, a, b)]
            self.assertEqual(got, [True, True, True, False])
            self.assertTrue(a.hit('ai-other', 1, 60))

    def test_fails_closed_except_new_sessions(self):
        import server
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'limits')
            self.addCleanup(store.close_pool)
            lim = server.SharedLimits(store)
            failure = unittest.mock.patch.object(store, 'connect', side_effect=psycopg.OperationalError('database unavailable'))
            failure.start()
            self.addCleanup(failure.stop)
            self.assertFalse(lim.hit('ai:tok', 5, 60))
            self.assertTrue(lim.hit('newsession:1.2.3.4', 5, 60))


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


@unittest.skipUnless(hasattr(os, 'fork'), 'WORKERS needs fork()')
class WorkersTests(unittest.TestCase):
    def test_workers_serve_and_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            port = free_port()
            env = dict(os.environ, QUIET='1', PUSH_DISABLED='1', WORKERS='3', MNL_DEV='1')
            env.pop('LLM_API_KEY', None)
            p = subprocess.Popen([sys.executable, 'server.py', '--port', str(port), '--namespace', os.path.join(tmp, 'g.db')],
                                 cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            base = f'http://127.0.0.1:{port}'
            try:
                for _ in range(300):
                    try:
                        urllib.request.urlopen(base + '/api/health', timeout=1)
                        break
                    except Exception:
                        time.sleep(0.1)
                children = subprocess.run(['pgrep', '-P', str(p.pid)], capture_output=True, text=True).stdout.split()
                self.assertEqual(len(children), 3)
                # a player's page load and commands, spread over the workers
                r = urllib.request.urlopen(base + '/api/bootstrap', timeout=10)
                cookie = r.headers['Set-Cookie'].split(';')[0]
                boot = json.loads(r.read())
                rev = boot['revision']
                self.assertIn('catalogue', boot['content'])
                for i in range(12):
                    body = json.dumps(dict(request_id=f'wk-{i:08d}', expected_revision=rev, career='mother_baby',
                                           action='select_career' if i == 0 else 'settings', payload={} if i == 0 else {'sound': bool(i % 2)})).encode()
                    req = urllib.request.Request(base + '/api/command', data=body, method='POST', headers={
                        'Cookie': cookie, 'X-Game-CSRF': boot['csrf'], 'Content-Type': 'application/json'})
                    rev = json.loads(urllib.request.urlopen(req, timeout=10).read())['revision']
                self.assertEqual(rev, 12)
                statics = [urllib.request.urlopen(base + '/js/app.js', timeout=10).status for _ in range(10)]
                self.assertEqual(set(statics), {200})
            finally:
                p.send_signal(signal.SIGTERM)
                p.wait(10)
            self.assertEqual(p.returncode, 0)
            # Rate limits use the hits table; no database file is created.
            self.assertEqual(os.path.exists(os.path.join(tmp, 'g-limits.db')), False)
            self.assertFalse(os.path.exists(ROOT / 'storage' / 'g-limits.db'))
            time.sleep(0.3)
            for pid in children:
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(pid), 0)


class StaticFastPathTests(unittest.TestCase):
    def test_changed_file_is_served_after_recheck(self):
        import server
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 'g.db')
        quiet = unittest.mock.patch.dict(os.environ, {'QUIET': '1'})
        quiet.start()
        self.addCleanup(quiet.stop)
        srv = server.GameServer(('127.0.0.1', 0), store)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        base = f'http://127.0.0.1:{srv.server_port}'
        with urllib.request.urlopen(base + '/js/boot.js') as r1:
            etag = r1.headers['ETag']
        req = urllib.request.Request(base + '/js/boot.js', headers={'If-None-Match': etag})
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 304)
        # a cached route is trusted for STATIC_RECHECK seconds, then re-validated against the file
        key = '/js/boot.js'
        entry, _ = srv.static_routes[key]
        srv.static_routes[key] = (entry[:3] + ('"stale"',) + entry[4:], time.monotonic() - server.STATIC_RECHECK - 1)
        with urllib.request.urlopen(base + '/js/boot.js') as r2:
            self.assertEqual(r2.headers['ETag'], etag)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(base + '/nope.js')
        self.assertEqual(ctx.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
