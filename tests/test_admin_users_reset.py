"""Admin password reset through HTTP and isolated PostgreSQL account metadata."""
import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import accounts, admin_users, db as dbm, tiktok_auth
from game.storage import Store
from server import COOKIE, GameServer, SharedLimits


OLD_PASSWORD = 'reset-original-password'
NEW_PASSWORD = 'reset-new-password-2026'
RESET_PATH = '/api/admin/users/password'


class AdminPasswordResetHTTP(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'reset_admin,reset_admin2'})
        self.env.start()
        self.store = Store(Path(self.temp.name) / 'state.db', story=True)
        self.server = GameServer(('127.0.0.1', 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.admin = self.register('reset_admin', 'Vận Hành')
        self.admin2 = self.register('reset_admin2', 'Quản Trị')
        self.target = self.register('reset_player', 'Người Chơi')
        self.other = self.register('reset_other', 'Người Khác')
        self.target_phone = self.login_device('reset_player')
        token, csrf, _ = self.store.session()
        self.anonymous = dict(token=token, cookie=COOKIE + '=' + token, csrf=csrf)
        self.server.limits.clear()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.store.close_pool()
        self.env.stop()
        self.temp.cleanup()

    def register(self, username, display):
        token, _, _ = self.store.session()
        out = accounts.register(self.store, token, dict(username=username, display=display,
                               password=OLD_PASSWORD, confirm=OLD_PASSWORD))
        with self.store.connect() as db:
            row = db.execute('SELECT uid,sid FROM accounts WHERE username=?', (username,)).fetchone()
        return dict(id=row['uid'], sid=row['sid'], username=username, display=display,
                    token=out['token'], cookie=COOKIE + '=' + out['token'], csrf=out['csrf'])

    def login_device(self, username, password=OLD_PASSWORD):
        out = accounts.login(self.store, None, dict(username=username, password=password))
        return dict(token=out['token'], cookie=COOKIE + '=' + out['token'], csrf=out['csrf'])

    def req(self, dev, path=RESET_PATH, method='POST', body=None, csrf=True, origin=None):
        headers = {'Host': f'127.0.0.1:{self.port}'}
        if dev.get('cookie'):
            headers['Cookie'] = dev['cookie']
        if csrf and dev.get('csrf'):
            headers['X-Game-CSRF'] = dev['csrf']
        if method == 'POST':
            headers['Content-Type'] = 'application/json'
            headers['Origin'] = origin or f'http://127.0.0.1:{self.port}'
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=15)
        con.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        res = con.getresponse()
        status, data, response_headers = res.status, json.loads(res.read() or b'{}'), dict(res.getheaders())
        con.close()
        return status, data, response_headers

    def payload(self, target=None, **changes):
        target = target or self.target
        return {**dict(id=target['id'], username=target['username'], password=NEW_PASSWORD,
                       confirm=NEW_PASSWORD), **changes}

    def rows(self, table):
        order = {'accounts': 'uid', 'sessions': 'sid', 'profiles': 'pid',
                 'logins': 'token', 'tiktok_flows': 'state_hash'}[table]
        with self.store.connect() as db:
            return [dict(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY {order}').fetchall()]

    def add_flow(self, device, name):
        sid, login_csrf = self.store.resolve(device['token'])
        with self.store.connect() as db:
            db.execute('INSERT INTO tiktok_flows(state_hash,binding_hash,source_token,source_sid,source_login,mode,client_key,expires_at,phase) '
                       'VALUES(?,?,?,?,?,?,?,?,?)',
                       (name, name + '-binding', self.store.digest(device['token']), sid,
                        int(bool(login_csrf)), 'link', 'test-client', 9999999999, 'pending'))

    def assert_bad(self, body, code, status=400):
        before = {table: self.rows(table) for table in ('accounts', 'logins', 'sessions', 'profiles')}
        response_status, data, _ = self.req(self.admin, body=body)
        self.assertEqual((response_status, data.get('code')), (status, code), data)
        for table, expected in before.items():
            self.assertEqual(self.rows(table), expected, table)
        encoded = json.dumps(data)
        self.assertNotIn(NEW_PASSWORD, encoded)
        self.assertNotIn(self.admin['token'], encoded)

    def test_anonymous_cookie_and_unsigned_request_cannot_reset(self):
        self.assertEqual(self.req({}, body=self.payload())[0], 401)
        self.assertEqual(self.req(self.anonymous, body=self.payload())[0], 403)

    def test_ordinary_player_cannot_reset(self):
        status, data, _ = self.req(self.target, body=self.payload())
        self.assertEqual((status, data.get('code')), (403, 'forbidden'))

    def test_admin_without_csrf_cannot_reset(self):
        self.assertEqual(self.req(self.admin, body=self.payload(), csrf=False)[0], 403)

    def test_admin_from_another_origin_cannot_reset(self):
        self.assertEqual(self.req(self.admin, body=self.payload(), origin='https://evil.example')[0], 403)

    def test_reset_changes_only_target_password_and_revokes_every_target_login(self):
        revision = self.store.read(self.target['token'])[1]
        self.store.command(self.target['token'], 'reset-save-fixture', revision, None, 'settings', {'sound': False})
        before_saves, before_profiles = self.rows('sessions'), self.rows('profiles')
        before_accounts = self.rows('accounts')
        before_other_logins = [row for row in self.rows('logins') if row['sid'] != self.target['sid']]
        self.add_flow(self.target, 'target-laptop')
        self.add_flow(self.target_phone, 'target-phone')
        self.add_flow(self.other, 'other-player')
        self.add_flow(self.anonymous, 'anonymous')

        status, data, headers = self.req(self.admin, body=self.payload())
        self.assertEqual(status, 200, data)
        self.assertEqual(set(data) - {'server_time', 'server_recv'},
                         {'ok', 'username', 'display', 'message', 'reauthenticate'})
        self.assertIs(data['ok'], True)
        self.assertIs(data['reauthenticate'], False)
        self.assertEqual((data['username'], data['display']), ('reset_player', 'Người Chơi'))
        self.assertTrue(data['message'])
        self.assertNotIn('Set-Cookie', headers)
        self.assertNotIn(NEW_PASSWORD, json.dumps(data))
        self.assertEqual(self.rows('sessions'), before_saves)
        self.assertEqual(self.rows('profiles'), before_profiles)
        after_accounts = self.rows('accounts')
        for before, after in zip(before_accounts, after_accounts):
            if before['uid'] == self.target['id']:
                self.assertNotEqual(before['pw'], after['pw'])
                self.assertTrue(accounts.verify_password(NEW_PASSWORD, after['pw']))
                self.assertFalse(accounts.verify_password(OLD_PASSWORD, after['pw']))
                self.assertEqual({k: v for k, v in after.items() if k not in ('pw', 'updated_at')},
                                 {k: v for k, v in before.items() if k not in ('pw', 'updated_at')})
                self.assertNotIn(after['pw'], json.dumps(data))
            else:
                self.assertEqual(after, before)
        self.assertEqual(self.rows('logins'), before_other_logins)
        self.assertEqual({row['state_hash'] for row in self.rows('tiktok_flows')}, {'other-player', 'anonymous'})
        for device in (self.target, self.target_phone):
            self.assertEqual(self.req(device, '/api/state', 'GET')[0], 401)
        self.assertEqual(self.req(self.other, '/api/state', 'GET')[0], 200)
        self.assertEqual(self.req(self.admin, '/api/admin/users', 'GET')[0], 200)
        self.assertEqual(self.req(self.anonymous, '/api/account/login', body=dict(
            username='reset_player', password=OLD_PASSWORD))[0], 401)
        status, login, headers = self.req(self.anonymous, '/api/account/login', body=dict(
            username='reset_player', password=NEW_PASSWORD))
        self.assertEqual(status, 200, login)
        self.assertEqual(login['account']['username'], 'reset_player')
        self.assertIn('Set-Cookie', headers)

    def test_reset_never_reads_or_writes_save_json(self):
        queries = []
        execute = dbm.PgConnection.execute

        def observe(db, sql, params=()):
            queries.append(sql.lower())
            return execute(db, sql, params)

        with patch.object(self.store, 'read', side_effect=AssertionError('save read')), \
             patch.object(self.store, 'parse_state', side_effect=AssertionError('save parse')), \
             patch.object(self.store, 'command', side_effect=AssertionError('save write')), \
             patch.object(dbm.PgConnection, 'execute', observe):
            status, data, _ = self.req(self.admin, body=self.payload())
        self.assertEqual(status, 200, data)
        session_queries = [query for query in queries if 'sessions' in query]
        self.assertTrue(session_queries, 'CSRF still checks the real session metadata')
        for query in session_queries:
            self.assertNotIn('state', query)
            self.assertNotIn('select *', query)
            self.assertNotIn('update sessions', query)
            self.assertNotIn('insert into sessions', query)
            self.assertNotIn('delete from sessions', query)

    def test_password_must_be_a_valid_string(self):
        for value in ('short', 'x' * 129, None, True, 12345678, ['long-password']):
            with self.subTest(value=value):
                self.assert_bad(self.payload(password=value, confirm=value), 'weak_password')

    def test_confirmation_is_required_and_must_be_matching_string(self):
        missing = self.payload()
        del missing['confirm']
        for body in (missing, self.payload(confirm=None), self.payload(confirm=False),
                     self.payload(confirm=123), self.payload(confirm='different-password')):
            with self.subTest(confirm=body.get('confirm')):
                self.assert_bad(body, 'password_mismatch')

    def test_id_must_be_a_strict_positive_integer(self):
        for value in (None, True, False, 0, -1, str(self.target['id']), float(self.target['id']), []):
            with self.subTest(id=value):
                self.assert_bad(self.payload(id=value), 'bad_target')

    def test_username_must_be_a_canonical_valid_string(self):
        for value in (None, True, ['reset_player'], '', 'RESET_PLAYER', ' reset_player ', 'x' * 25):
            with self.subTest(username=value):
                self.assert_bad(self.payload(username=value), 'bad_username')

    def test_id_and_username_must_match_the_same_account(self):
        self.assert_bad(self.payload(username='reset_other'), 'account_missing', 404)

    def test_missing_account_cannot_reset(self):
        self.assert_bad(self.payload(id=2 ** 31 - 1, username='missing_player'), 'account_missing', 404)

    def test_rate_limit_is_ten_per_minute_for_each_admin(self):
        missing = self.payload(id=2 ** 31 - 1, username='missing_player')
        for _ in range(10):
            self.assertEqual(self.req(self.admin, body=missing)[0], 404)
        status, data, _ = self.req(self.admin, body=self.payload())
        self.assertEqual((status, data.get('code')), (429, 'rate_limited'))
        self.assertEqual(self.req(self.admin2, body=self.payload())[0], 200)

    def test_self_reset_requires_reauthentication_and_revokes_current_and_other_devices(self):
        other_device = self.login_device('reset_admin')
        self.add_flow(self.admin, 'admin-current')
        self.add_flow(other_device, 'admin-other-device')
        status, data, _ = self.req(self.admin, body=self.payload(self.admin))
        self.assertEqual(status, 200, data)
        self.assertIs(data['reauthenticate'], True)
        self.assertEqual(data['username'], 'reset_admin')
        for dev in (self.admin, other_device):
            self.assertEqual(self.req(dev, '/api/admin/users', 'GET')[0], 401)
        self.assertFalse(self.rows('tiktok_flows'))
        status, data, _ = self.req(self.anonymous, '/api/account/login', body=dict(
            username='reset_admin', password=NEW_PASSWORD))
        self.assertEqual(status, 200, data)

    def test_failed_login_revocation_rolls_back_password_and_tiktok_cleanup(self):
        self.add_flow(self.target, 'rollback-target')
        before = {table: self.rows(table) for table in ('accounts', 'logins', 'tiktok_flows')}
        with self.store.connect() as db:
            db.execute("CREATE FUNCTION reject_reset_login_delete() RETURNS trigger LANGUAGE plpgsql AS $$ "
                       "BEGIN RAISE EXCEPTION 'test revocation failure' USING ERRCODE='22000'; END $$")
            db.execute('CREATE TRIGGER reject_reset_login_delete BEFORE DELETE ON logins '
                       'FOR EACH ROW EXECUTE FUNCTION reject_reset_login_delete()')
        status, data, _ = self.req(self.admin, body=self.payload())
        self.assertEqual((status, data.get('code')), (400, 'invalid_data'), data)
        for table, expected in before.items():
            self.assertEqual(self.rows(table), expected, table)

    def test_login_verified_before_reset_cannot_create_a_session_after_reset(self):
        verified, resume = threading.Event(), threading.Event()
        results = []
        verify = accounts.verify_password

        def pause_after_verification(password, stored):
            valid = verify(password, stored)
            verified.set()
            if not resume.wait(10):
                raise AssertionError('test did not resume the pending login')
            return valid

        def pending_login():
            try:
                results.append(accounts.login(self.store, None, dict(
                    username=self.target['username'], password=OLD_PASSWORD)))
            except Exception as error:
                results.append(error)

        worker = threading.Thread(target=pending_login, daemon=True)
        with patch('game.accounts.verify_password', pause_after_verification):
            worker.start()
            try:
                self.assertTrue(verified.wait(5), 'login must first verify the old password')
                status, data, _ = self.req(self.admin, body=self.payload())
                self.assertEqual(status, 200, data)
            finally:
                resume.set()
                worker.join(10)
        self.assertFalse(worker.is_alive(), 'pending login must finish')
        self.assertEqual(len(results), 1)
        self.assertTrue(isinstance(results[0], accounts.AccountError),
                        'login with a password verified before reset must be rejected')
        self.assertEqual((results[0].status, results[0].code), (401, 'bad_login'))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM logins WHERE sid=?',
                                        (self.target['sid'],)).fetchone()[0], 0)
        self.login_device(self.target['username'], NEW_PASSWORD)

    def test_password_change_verified_before_reset_cannot_overwrite_admin_password(self):
        verified, resume = threading.Event(), threading.Event()
        results = []
        verify = accounts.verify_password
        before_saves, before_profiles = self.rows('sessions'), self.rows('profiles')

        def pause_after_verification(password, stored):
            valid = verify(password, stored)
            verified.set()
            if not resume.wait(10):
                raise AssertionError('test did not resume the pending password change')
            return valid

        def pending_change():
            try:
                results.append(accounts.change_password(self.store, self.target['token'], dict(
                    current=OLD_PASSWORD, password='stale-request-password', confirm='stale-request-password')))
            except Exception as error:
                results.append(error)

        worker = threading.Thread(target=pending_change, daemon=True)
        with patch('game.accounts.verify_password', pause_after_verification):
            worker.start()
            try:
                self.assertTrue(verified.wait(5), 'password change must first verify the old password')
                status, data, _ = self.req(self.admin, body=self.payload())
                self.assertEqual(status, 200, data)
                reset_accounts = self.rows('accounts')
            finally:
                resume.set()
                worker.join(10)
        self.assertFalse(worker.is_alive(), 'pending password change must finish')
        self.assertEqual(len(results), 1)
        self.assertTrue(isinstance(results[0], accounts.AccountError),
                        'a password change verified before reset must be rejected')
        self.assertEqual((results[0].status, results[0].code), (401, 'bad_login'))
        self.assertEqual(self.rows('accounts'), reset_accounts)
        self.assertEqual(self.rows('sessions'), before_saves)
        self.assertEqual(self.rows('profiles'), before_profiles)
        self.assertFalse(any(row['sid'] == self.target['sid'] for row in self.rows('logins')))
        self.login_device(self.target['username'], NEW_PASSWORD)

    def test_pending_password_change_rechecks_that_its_login_was_not_revoked(self):
        verified, resume = threading.Event(), threading.Event()
        results = []
        verify = accounts.verify_password
        before_accounts = self.rows('accounts')

        def pause_after_verification(password, stored):
            valid = verify(password, stored)
            verified.set()
            if not resume.wait(10):
                raise AssertionError('test did not resume the logged-out password change')
            return valid

        def pending_change():
            try:
                results.append(accounts.change_password(self.store, self.target['token'], dict(
                    current=OLD_PASSWORD, password=NEW_PASSWORD, confirm=NEW_PASSWORD)))
            except Exception as error:
                results.append(error)

        worker = threading.Thread(target=pending_change, daemon=True)
        with patch('game.accounts.verify_password', pause_after_verification):
            worker.start()
            try:
                self.assertTrue(verified.wait(5), 'password change must first verify the password')
                accounts.logout(self.store, self.target['token'])
            finally:
                resume.set()
                worker.join(10)
        self.assertFalse(worker.is_alive(), 'logged-out password change must finish')
        self.assertEqual(len(results), 1)
        self.assertTrue(isinstance(results[0], accounts.AccountError),
                        'a pending password change must reject its revoked login')
        self.assertEqual(results[0].code, 'not_signed_in')
        self.assertEqual(self.rows('accounts'), before_accounts)
        self.login_device(self.target['username'], OLD_PASSWORD)

    def test_reset_and_actual_tiktok_link_complete_without_deadlock(self):
        link_ready, release_link, reset_started = threading.Event(), threading.Event(), threading.Event()
        outcomes, reset_pid = {}, []
        execute = dbm.PgConnection.execute
        env = dict(TIKTOK_CLIENT_KEY='test-client', TIKTOK_CLIENT_SECRET='test-secret',
                   TIKTOK_REDIRECT_URI='https://game.example/auth/tiktok/callback', TIKTOK_MODE='sandbox')

        def observe(db, sql, params=()):
            name = threading.current_thread().name
            if name == 'reset-tiktok-link' and sql.startswith('SELECT * FROM accounts WHERE sid=') and 'FOR UPDATE' in sql:
                link_ready.set()
                if not release_link.wait(10):
                    raise AssertionError('test did not release the TikTok account lookup')
            if name == 'reset-during-tiktok':
                reset_pid[:] = [db.raw.info.backend_pid]
                reset_started.set()
            return execute(db, sql, params)

        def link():
            try:
                outcomes['link'] = tiktok_auth._finish(self.store, flow['state'], flow['binding'],
                                                      'reset-link-person', 'TikTok Person')
            except Exception as error:
                outcomes['link'] = error

        def reset():
            try:
                outcomes['reset'] = admin_users.reset_password(self.store, self.admin['token'], self.payload())
            except Exception as error:
                outcomes['reset'] = error

        with patch.dict(os.environ, env):
            flow = tiktok_auth.start(self.store, self.target['token'], 'link')
            with self.store.connect() as db:
                db.execute("UPDATE tiktok_flows SET phase='exchanging' WHERE state_hash=?",
                           (tiktok_auth.digest(flow['state']),))
            before_saves, before_profiles = self.rows('sessions'), self.rows('profiles')
            linking = threading.Thread(target=link, name='reset-tiktok-link', daemon=True)
            resetting = threading.Thread(target=reset, name='reset-during-tiktok', daemon=True)
            with patch.object(dbm.PgConnection, 'execute', observe):
                linking.start()
                try:
                    self.assertTrue(link_ready.wait(5), 'TikTok must hold its session and flow locks')
                    resetting.start()
                    self.assertTrue(reset_started.wait(5), 'reset must reach the database')
                    blocked, deadline = False, time.monotonic() + 5
                    while time.monotonic() < deadline:
                        with self.store.connect() as db:
                            row = db.pg('SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s',
                                        (reset_pid[0],)).fetchone()
                        if row and row[0] == 'Lock':
                            blocked = True
                            break
                        time.sleep(0.01)
                    self.assertTrue(blocked, 'reset must wait on a lock held by TikTok')
                finally:
                    release_link.set()
                    linking.join(10)
                    if resetting.ident is not None:
                        resetting.join(10)
            self.assertFalse(linking.is_alive(), 'TikTok completion must finish')
            self.assertFalse(resetting.is_alive(), 'reset must finish')
        self.assertTrue(isinstance(outcomes.get('link'), dict),
                        'TikTok completion must avoid a database deadlock: ' + type(outcomes.get('link')).__name__)
        self.assertTrue(isinstance(outcomes.get('reset'), dict),
                        'reset must avoid a database deadlock: ' + type(outcomes.get('reset')).__name__)
        self.assertEqual(outcomes['link']['status'], 'linked')
        self.assertIs(outcomes['reset']['ok'], True)
        self.assertFalse(any(row['sid'] == self.target['sid'] for row in self.rows('logins')))
        self.assertEqual(self.rows('sessions'), before_saves)
        self.assertEqual(self.rows('profiles'), before_profiles)
        self.login_device(self.target['username'], NEW_PASSWORD)

    def test_login_locks_target_and_existing_source_metadata_in_sorted_order(self):
        locks = []
        execute = dbm.PgConnection.execute

        def observe(db, sql, params=()):
            if 'FOR UPDATE' in sql:
                if 'FROM sessions' in sql:
                    locks.append(('session', params[0]))
                    self.assertNotIn('state', sql.lower())
                elif 'FROM accounts' in sql:
                    locks.append(('account', None))
            return execute(db, sql, params)

        with patch.object(dbm.PgConnection, 'execute', observe):
            accounts.login(self.store, self.other['token'], dict(
                username=self.target['username'], password=OLD_PASSWORD))
        self.assertEqual(locks[:2], [('session', sid) for sid in sorted({self.target['sid'], self.other['sid']})])
        self.assertEqual(locks[2:], [('account', None)])

    def test_password_change_locks_own_metadata_before_account_and_login(self):
        locks = []
        execute = dbm.PgConnection.execute

        def observe(db, sql, params=()):
            if 'FOR UPDATE' in sql:
                for table in ('sessions', 'accounts', 'logins'):
                    if 'FROM ' + table in sql:
                        locks.append(table)
                if 'FROM sessions' in sql:
                    self.assertNotIn('state', sql.lower())
            return execute(db, sql, params)

        with patch.object(dbm.PgConnection, 'execute', observe):
            accounts.change_password(self.store, self.target['token'], dict(
                current=OLD_PASSWORD, password=NEW_PASSWORD, confirm=NEW_PASSWORD))
        self.assertEqual(locks, ['sessions', 'accounts', 'logins'])

    def test_reset_budget_is_shared_between_worker_servers(self):
        peer = GameServer(('127.0.0.1', 0), self.store)
        peer.shared_limits = SharedLimits(self.store)
        self.server.shared_limits = SharedLimits(self.store)
        thread = threading.Thread(target=peer.serve_forever, daemon=True)
        thread.start()
        original_port = self.port
        missing = self.payload(id=2 ** 31 - 1, username='missing_player')
        try:
            for attempt in range(10):
                self.port = original_port if attempt % 2 == 0 else peer.server_port
                self.assertEqual(self.req(self.admin, body=missing)[0], 404)
            self.port = original_port
            status, data, _ = self.req(self.admin, body=self.payload())
            self.assertEqual((status, data.get('code')), (429, 'rate_limited'))
        finally:
            self.port = original_port
            peer.shutdown()
            peer.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
