"""TikTok OAuth: cookie binding, one-use flows, save ownership and HTTP boundaries."""
import contextlib
import http.client
import importlib
import io
import json
import os
import re
import tempfile
import threading
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

from game import accounts, pg_schema, social
from game.storage import Store
from server import GameServer
from tests.pg_support import on_pg

ENV = dict(TIKTOK_CLIENT_KEY='test-client', TIKTOK_CLIENT_SECRET='test-secret',
           TIKTOK_REDIRECT_URI='https://game.example/auth/tiktok/callback', TIKTOK_MODE='sandbox')
REG = dict(username='local_player', display='Local Player', password='a-long-password', confirm='a-long-password')


class TikTokHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = GameServer(('127.0.0.1', 0), Store(Path(self.tmp.name) / 'g.db'))
        self.server.daemon_threads = False  # wait for handlers before deleting their database
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.env = patch.dict(os.environ, dict(ENV, QUIET='1'))
        self.env.start()
        self.dev = {}

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.env.stop(); self.tmp.cleanup()

    def req(self, path, method='GET', body=None, headers=None, cookie=None):
        if path == '/api/bootstrap': path += '?lite=1'  # these tests do not need the catalogue
        h = {'Host': f'127.0.0.1:{self.server.server_port}', 'Connection': 'close'}
        if cookie is not None: h['Cookie'] = cookie
        elif self.dev.get('cookie'): h['Cookie'] = self.dev['cookie']
        if self.dev.get('csrf'): h['X-Game-CSRF'] = self.dev['csrf']
        if isinstance(body, dict): h['Content-Type'] = 'application/json'; body = json.dumps(body)
        h.update(headers or {})
        con = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        try:
            con.request(method, path, body, h)
            res = con.getresponse(); raw = res.read(); hdrs = res.getheaders()
        finally: con.close()
        data = json.loads(raw) if 'application/json' in res.getheader('Content-Type', '') else raw.decode()
        if isinstance(data, dict) and data.get('csrf'): self.dev['csrf'] = data['csrf']
        for key, value in hdrs:
            if key == 'Set-Cookie' and value.startswith('mnl_session='):
                self.dev['cookie'] = value.split(';')[0]
        return res.status, data, hdrs

    def start(self, mode='login'):
        self.req('/api/bootstrap')
        status, data, hdrs = self.req('/api/account/tiktok/start', 'POST', {'mode': mode})
        self.assertEqual(status, 200, data)
        flow = next(v.split(';')[0] for k, v in hdrs if k == 'Set-Cookie')
        state = parse_qs(urlsplit(data['authorization_url']).query)['state'][0]
        return state, flow

    def test_not_configured_is_disabled_without_breaking_local_account(self):
        with patch.dict(os.environ, {'TIKTOK_CLIENT_SECRET': ''}):
            status, data, _ = self.req('/api/bootstrap')
            self.assertEqual(status, 200)
            self.assertIn('auth', data)
            self.assertEqual(data['auth']['tiktok'], {'enabled': False, 'mode': 'sandbox'})
            status, data, _ = self.req('/api/account/tiktok/start', 'POST', {'mode': 'login'})
            self.assertEqual((status, data['code']), (503, 'tiktok_unavailable'))
        status, data, _ = self.req('/api/account/register', 'POST', REG)
        self.assertEqual(status, 200, data)
        self.assertEqual(data['account'], {'username': REG['username'], 'display': REG['display']})

    def test_start_authorization_url_and_cookie(self):
        state, flow = self.start()
        status, data, hdrs = self.req('/api/account/tiktok/start', 'POST', {'mode': 'login'})
        url = urlsplit(data['authorization_url']); q = parse_qs(url.query)
        self.assertEqual((url.scheme, url.netloc, url.path), ('https', 'www.tiktok.com', '/v2/auth/authorize/'))
        self.assertEqual(q['scope'], ['user.info.basic']); self.assertEqual(q['response_type'], ['code'])
        self.assertEqual(q['redirect_uri'], [ENV['TIKTOK_REDIRECT_URI']])
        self.assertNotIn('test-secret', json.dumps(data))
        c = next(v for k, v in hdrs if k == 'Set-Cookie')
        for attr in ('HttpOnly', 'Secure', 'SameSite=Lax', 'Path=/auth/tiktok', 'Max-Age=600'): self.assertIn(attr, c)

    def test_start_needs_csrf_and_same_origin(self):
        self.req('/api/bootstrap')
        for headers in ({'X-Game-CSRF': 'wrong'}, {'Origin': 'https://evil.example'}, {'Sec-Fetch-Site': 'cross-site'}):
            self.assertEqual(self.req('/api/account/tiktok/start', 'POST', {'mode': 'login'}, headers)[0], 403)

    def test_callback_works_without_main_strict_cookie_and_cleans_codes(self):
        state, flow = self.start()
        with patch('game.tiktok_auth.exchange_identity', return_value=('person-a', 'TikTok Person')) as exchange:
            status, data, hdrs = self.req('/auth/tiktok/callback?' + urlencode({'state': state, 'code': 'private-code'}), cookie=flow)
        self.assertEqual(status, 303, data); exchange.assert_called_once()
        h = dict(hdrs)
        self.assertEqual(h['Location'], '/?tiktok=success')
        self.assertNotIn('private-code', str(hdrs) + data)
        cookies = [v for k, v in hdrs if k == 'Set-Cookie']
        self.assertTrue(any('mnl_session=' in c and 'SameSite=Strict' in c for c in cookies))
        self.assertTrue(any('Path=/auth/tiktok' in c and 'Max-Age=0' in c for c in cookies))
        self.assertEqual(self.req('/api/bootstrap')[1]['account']['tiktok_linked'], True)

    def test_confirmation_form_csrf_cancel_and_no_cache(self):
        tt = importlib.import_module('game.tiktok_auth')
        owner, _, _ = self.server.store.session()
        begin = tt.start(self.server.store, owner, 'login')
        with patch('game.tiktok_auth.exchange_identity', return_value=('person-confirm', 'TikTok Person')):
            tt.callback(self.server.store, begin['state'], begin['binding'], 'code')
        self.req('/api/bootstrap')
        token = self.dev['cookie'].split('=', 1)[1]
        self.server.store.command(token, 'tt-http-progress', 0, 'florist', 'start_day', {})
        state, flow = self.start()
        with patch('game.tiktok_auth.exchange_identity', return_value=('person-confirm', 'TikTok Person')):
            status, html, hdrs = self.req('/auth/tiktok/callback?' + urlencode({'state': state, 'code': 'code'}), cookie=flow)
        self.assertEqual(status, 303)
        self.assertEqual(dict(hdrs)['Location'], '/auth/tiktok/confirm')
        status, html, hdrs = self.req('/auth/tiktok/confirm', cookie=flow)
        self.assertEqual(status, 200)
        self.assertIn('action="/auth/tiktok/confirm"', html); self.assertIn('name="nonce"', html)
        self.assertIn('Thay tiến trình', html); self.assertEqual(dict(hdrs)['Cache-Control'], 'no-store')
        self.assertEqual(self.req('/auth/tiktok/confirm', 'POST', {'nonce': 'wrong', 'choice': 'confirm'}, cookie=flow)[0], 303)
        self.assertIsNone(accounts.status(self.server.store, token))
        self.assertTrue(self.server.store.read(token)[0]['careers']['florist']['started'])
        nonce = re.search(r'name="nonce" value="([^"]+)"', html)[1]
        status, _, hdrs = self.req('/auth/tiktok/confirm', 'POST', urlencode({'nonce': nonce, 'choice': 'cancel'}),
                                  {'Content-Type': 'application/x-www-form-urlencoded'}, cookie=flow)
        self.assertEqual(status, 303); self.assertEqual(dict(hdrs)['Location'], '/?tiktok=cancelled')
        self.assertTrue(self.server.store.read(token)[0]['careers']['florist']['started'])
        status, _, hdrs = self.req('/auth/tiktok/confirm', 'POST', urlencode({'nonce': nonce, 'choice': 'confirm'}),
                                  {'Content-Type': 'application/x-www-form-urlencoded'}, cookie=flow)
        self.assertEqual(dict(hdrs)['Location'], '/?tiktok=tiktok_state')

    def test_callback_query_never_appears_in_request_log(self):
        stream = io.StringIO()
        with patch.dict(os.environ, {'QUIET': ''}), contextlib.redirect_stderr(stream):
            self.req('/auth/tiktok/callback?state=private-state&code=private-code', cookie='')
        self.assertNotIn('private-state', stream.getvalue()); self.assertNotIn('private-code', stream.getvalue())

    def test_normal_login_before_callback_revokes_guest_flow(self):
        self.req('/api/bootstrap'); self.req('/api/account/register', 'POST', REG)
        self.dev = {}; state, flow = self.start()
        status, data, _ = self.req('/api/account/login', 'POST', {'username': REG['username'], 'password': REG['password']})
        self.assertEqual(status, 200, data)
        with patch('game.tiktok_auth.exchange_identity') as exchange:
            status, _, hdrs = self.req('/auth/tiktok/callback?' + urlencode({'state': state, 'code': 'private-code'}), cookie=flow)
        self.assertEqual(status, 303); exchange.assert_not_called()
        self.assertEqual(dict(hdrs)['Location'], '/?tiktok=tiktok_state')
        self.assertEqual(self.req('/api/bootstrap')[1]['account']['username'], REG['username'])
        with self.server.store.connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM tiktok_identities').fetchone()[0], 0)

    def test_head_cannot_consume_pending_authorization(self):
        state, flow = self.start()
        query = '/auth/tiktok/callback?' + urlencode({'state': state, 'code': 'private-code'})
        with patch('game.tiktok_auth.exchange_identity') as exchange:
            self.assertEqual(self.req(query, 'HEAD', cookie=flow)[0], 405)
        exchange.assert_not_called()
        with patch('game.tiktok_auth.exchange_identity', return_value=('person-head', 'Player')):
            self.assertEqual(self.req(query, cookie=flow)[0], 303)


class TikTokStoreTests(unittest.TestCase):
    def setUp(self):
        self.tt = importlib.import_module('game.tiktok_auth')
        self.tmp = tempfile.TemporaryDirectory(); self.store = Store(Path(self.tmp.name) / 'g.db')
        social.ensure(self.store)
        self.token, self.csrf, _ = self.store.session()
        self.env = patch.dict(os.environ, ENV); self.env.start()

    def tearDown(self):
        self.env.stop(); self.tmp.cleanup()

    def begin(self, token=None, mode='login'):
        return self.tt.start(self.store, token or self.token, mode)

    def finish(self, flow, identity=('person-a', 'TikTok Person')):
        with patch('game.tiktok_auth.exchange_identity', return_value=identity):
            return self.tt.callback(self.store, flow['state'], flow['binding'], 'private-code')

    def test_configuration_requires_fixed_https_callback(self):
        for redirect in ('http://game.example/auth/tiktok/callback', 'https://game.example/wrong',
                         'https://game.example/auth/tiktok/callback?next=x', 'https://u:p@game.example/auth/tiktok/callback'):
            with self.subTest(redirect=redirect), patch.dict(os.environ, {'TIKTOK_REDIRECT_URI': redirect}):
                self.assertFalse(self.tt.public_config()['enabled'])
        self.assertEqual(self.tt.public_config(), {'enabled': True, 'mode': 'sandbox'})

    def test_state_and_binding_are_hashed_expire_and_cannot_replay(self):
        f = self.begin()
        with self.store.connect() as db:
            row = dict(db.execute('SELECT * FROM tiktok_flows').fetchone())
        for raw in (f['state'], f['binding'], self.token, 'test-secret'): self.assertNotIn(raw, str(row))
        for state, binding in ((f['state'], 'wrong'), ('wrong', f['binding'])):
            with self.assertRaises(accounts.AccountError), patch('game.tiktok_auth.exchange_identity') as exchange:
                self.tt.callback(self.store, state, binding, 'code')
            exchange.assert_not_called()
        self.finish(f)
        with self.assertRaises(accounts.AccountError), patch('game.tiktok_auth.exchange_identity') as exchange:
            self.tt.callback(self.store, f['state'], f['binding'], 'code')
        exchange.assert_not_called()
        new, _, _ = self.store.session(); f = self.begin(new)
        with self.store.connect() as db: db.execute('UPDATE tiktok_flows SET expires_at=0')
        with self.assertRaises(accounts.AccountError): self.finish(f)

    def test_guest_save_becomes_tiktok_only_account_without_password(self):
        self.store.command(self.token, 'tt-guest-progress', 0, 'florist', 'start_day', {})
        sid = self.store.key(self.token)
        out = self.finish(self.begin())
        self.assertEqual(self.store.key(out['token']), sid); self.assertEqual(out['csrf'], self.csrf)
        self.assertTrue(self.store.read(out['token'])[0]['careers']['florist']['started'])
        self.assertFalse(out['account']['has_password']); self.assertTrue(out['account']['tiktok_linked'])
        self.assertRegex(out['account']['username'], r'^tt_[0-9a-f]+$')
        with self.store.connect() as db: a = db.execute('SELECT * FROM accounts').fetchone()
        self.assertFalse(accounts.verify_password('any-password', a['pw']))
        with self.assertRaises(Exception): self.store.read(self.token)
        with self.assertRaises(accounts.AccountError): accounts.login(self.store, None, {'username': a['username'], 'password': 'any-password'})

    def test_link_keeps_local_password_username_and_save(self):
        local = accounts.register(self.store, self.token, REG)['token']; sid = self.store.key(local)
        with self.store.connect() as db: before = dict(db.execute('SELECT * FROM accounts').fetchone())
        out = self.finish(self.begin(local, 'link'))
        self.assertEqual(out['account']['username'], REG['username']); self.assertTrue(out['account']['has_password'])
        self.assertEqual(self.store.key(out['token']), sid)
        with self.store.connect() as db: after = dict(db.execute('SELECT * FROM accounts').fetchone())
        self.assertEqual((before['pw'], before['sid'], before['username']), (after['pw'], after['sid'], after['username']))
        fresh, _, _ = self.store.session()
        login = accounts.login(self.store, fresh, {'username': REG['username'], 'password': REG['password']})
        self.assertEqual(self.store.key(login['token']), sid)

    def test_link_requires_signed_in_account_and_rejects_identity_owned_elsewhere(self):
        with self.assertRaises(accounts.AccountError): self.begin(mode='link')
        owner = self.finish(self.begin())
        fresh, _, _ = self.store.session(); local = accounts.register(self.store, fresh, REG)['token']
        with self.assertRaises(accounts.AccountError) as e: self.finish(self.begin(local, 'link'))
        self.assertEqual(e.exception.code, 'tiktok_conflict')
        self.assertEqual(accounts.status(self.store, local), {'username': REG['username'], 'display': REG['display']})
        self.store.read(owner['token'])

    def test_existing_identity_login_on_second_device(self):
        owner = self.finish(self.begin()); sid = self.store.key(owner['token'])
        phone, _, _ = self.store.session(); out = self.finish(self.begin(phone))
        self.assertEqual(self.store.key(out['token']), sid)
        self.assertNotEqual(out['csrf'], owner['csrf']); self.store.read(owner['token'])

    def test_existing_identity_with_guest_progress_needs_real_confirm_or_cancel(self):
        owner = self.finish(self.begin()); phone, _, _ = self.store.session()
        self.store.command(phone, 'tt-phone-progress', 0, 'florist', 'start_day', {})
        f = self.begin(phone); out = self.finish(f)
        self.assertEqual(out['status'], 'confirm'); self.assertNotIn('token', out)
        self.assertTrue(self.store.read(phone)[0]['careers']['florist']['started'])
        with self.assertRaises(accounts.AccountError): self.tt.confirm(self.store, f['binding'], 'wrong', 'confirm')
        cancelled = self.tt.confirm(self.store, f['binding'], out['nonce'], 'cancel')
        self.assertEqual(cancelled['status'], 'cancelled'); self.store.read(phone)
        with self.assertRaises(accounts.AccountError): self.tt.confirm(self.store, f['binding'], out['nonce'], 'confirm')
        f = self.begin(phone); out = self.finish(f)
        login = self.tt.confirm(self.store, f['binding'], out['nonce'], 'confirm')
        self.assertEqual(self.store.key(login['token']), self.store.key(owner['token']))

    def test_logout_replacement_or_deletion_invalidates_pending_source(self):
        local = accounts.register(self.store, self.token, REG)['token']; f = self.begin(local, 'link')
        accounts.logout(self.store, local)
        with self.assertRaises(accounts.AccountError): self.finish(f)
        guest, _, _ = self.store.session(); f = self.begin(guest)
        accounts.register(self.store, guest, dict(REG, username='another_player'))
        with self.assertRaises(accounts.AccountError): self.finish(f)
        guest, _, _ = self.store.session(); f = self.begin(guest); self.store.delete(guest)
        with self.assertRaises(accounts.AccountError): self.finish(f)

    def test_regular_login_invalidates_guest_oauth_even_before_guest_cleanup(self):
        accounts.register(self.store, self.token, REG)
        guest, _, _ = self.store.session(); f = self.begin(guest)
        accounts.login(self.store, guest, {'username': REG['username'], 'password': REG['password']})
        # The HTTP caller cleans up later. The account mutation itself must revoke OAuth.
        self.store.read(guest)
        with self.assertRaises(accounts.AccountError): self.finish(f)

    def test_logout_during_exchange_cannot_link(self):
        local = accounts.register(self.store, self.token, REG)['token']; f = self.begin(local, 'link')
        def exchange(code):
            accounts.logout(self.store, local)
            return ('person-a', 'TikTok Person')
        with patch('game.tiktok_auth.exchange_identity', side_effect=exchange), self.assertRaises(accounts.AccountError):
            self.tt.callback(self.store, f['state'], f['binding'], 'code')
        with self.store.connect() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM tiktok_identities').fetchone()[0], 0)

    def test_password_change_revokes_other_devices_pending_flow_before_exchange(self):
        first = accounts.register(self.store, self.token, REG)['token']
        guest, _, _ = self.store.session()
        second = accounts.login(self.store, guest, {'username': REG['username'], 'password': REG['password']})['token']
        flow = self.begin(second, 'link')
        accounts.change_password(self.store, first, {'current': REG['password'], 'password': 'new-long-password', 'confirm': 'new-long-password'})
        with patch('game.tiktok_auth.exchange_identity') as exchange, self.assertRaises(accounts.AccountError):
            self.tt.callback(self.store, flow['state'], flow['binding'], 'private-code')
        exchange.assert_not_called()
        self.store.read(first)
        with self.assertRaises(Exception): self.store.read(second)

    def test_confirmation_rejects_source_replaced_after_provider_return(self):
        self.finish(self.begin()); phone, _, _ = self.store.session()
        self.store.command(phone, 'tt-confirm-replaced', 0, 'florist', 'start_day', {})
        f = self.begin(phone); out = self.finish(f)
        self.assertEqual(out['status'], 'confirm')
        accounts.register(self.store, phone, REG)
        with self.assertRaises(accounts.AccountError): self.tt.confirm(self.store, f['binding'], out['nonce'], 'confirm')

    def test_confirmation_rejects_disabled_or_changed_provider_configuration(self):
        self.finish(self.begin()); phone, _, _ = self.store.session()
        self.store.command(phone, 'tt-config-change', 0, 'florist', 'start_day', {})
        flow = self.begin(phone); out = self.finish(flow)
        for changed in ({'TIKTOK_CLIENT_SECRET': ''}, {'TIKTOK_CLIENT_KEY': 'another-app'}):
            with patch.dict(os.environ, changed), self.assertRaises(accounts.AccountError):
                self.tt.confirm(self.store, flow['binding'], out['nonce'], 'confirm')
        self.assertTrue(self.store.read(phone)[0]['careers']['florist']['started'])

    @unittest.skipUnless(on_pg(), 'Requires isolated PostgreSQL')
    def test_concurrent_account_deletion_cannot_leave_new_login_or_flow(self):
        owner = self.finish(self.begin()); owner_sid = self.store.key(owner['token'])
        with self.store.connect() as db: uid = db.execute('SELECT uid FROM accounts WHERE sid=?', (owner_sid,)).fetchone()[0]
        guest, _, _ = self.store.session(); flow = self.begin(guest)
        holder = self.store.connect(); holder.execute('BEGIN')
        holder.execute('SELECT sid FROM sessions WHERE sid=? FOR UPDATE', (owner_sid,))
        # Pause deletion at the exact production ordering: old logins/flows are
        # already removed, while the account's session lock is still held.
        holder.execute('DELETE FROM logins WHERE sid=?', (owner_sid,))
        holder.execute('DELETE FROM tiktok_flows WHERE source_sid=? OR target_uid=?', (owner_sid, uid))
        saw_identity = threading.Event(); done = threading.Event(); results = []
        connect = self.store.connect

        class ObservedConnection:
            def __init__(self, inner): self.inner = inner
            def __enter__(self): self.inner.__enter__(); return self
            def __exit__(self, *args): return self.inner.__exit__(*args)
            def __getattr__(self, name): return getattr(self.inner, name)
            def execute(self, sql, args=()):
                out = self.inner.execute(sql, args)
                if sql.startswith('SELECT') and 'FROM tiktok_identities' in sql: saw_identity.set()
                return out

        def callback():
            try: results.append(self.tt.callback(self.store, flow['state'], flow['binding'], 'code'))
            except Exception as error: results.append(error)
            finally: done.set()

        thread = threading.Thread(target=callback)
        try:
            with patch.object(self.store, 'connect', side_effect=lambda: ObservedConnection(connect())), \
                    patch('game.tiktok_auth.exchange_identity', return_value=('person-a', 'TikTok Person')):
                thread.start(); self.assertTrue(saw_identity.wait(10))
                # Old code locks identity/account first, inserts another login
                # and commits while deletion waits here. Fixed code waits for
                # the target session before locking those rows.
                holder.execute('DELETE FROM tiktok_identities WHERE sid=?', (owner_sid,))
                holder.execute('DELETE FROM accounts WHERE sid=?', (owner_sid,))
                holder.execute('DELETE FROM sessions WHERE sid=?', (owner_sid,))
                holder.commit(); self.assertTrue(done.wait(10)); thread.join(10)
        finally:
            holder.rollback(); holder.close()
            if thread.is_alive(): thread.join(10)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM logins WHERE sid=?', (owner_sid,)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM tiktok_flows WHERE target_uid=?', (uid,)).fetchone()[0], 0)
        self.assertEqual(len(results), 1); self.assertIsInstance(results[0], accounts.AccountError)
        self.store.read(guest)

    @unittest.skipUnless(on_pg(), 'Requires isolated PostgreSQL')
    def test_identity_created_after_preflight_requires_new_authorization(self):
        first_flow = self.begin(); other, _, _ = self.store.session(); other_flow = self.begin(other)
        preflight = threading.Event(); release = threading.Event(); results = []
        connect = self.store.connect

        class ObservedConnection:
            def __init__(self, inner): self.inner = inner
            def __enter__(self): self.inner.__enter__(); return self
            def __exit__(self, *args): return self.inner.__exit__(*args)
            def __getattr__(self, name): return getattr(self.inner, name)
            def execute(self, sql, args=()):
                out = self.inner.execute(sql, args)
                if (threading.current_thread().name == 'tt-preflight-race' and sql.startswith('SELECT')
                        and 'FROM tiktok_identities' in sql and 'FOR UPDATE' not in sql):
                    preflight.set()
                    if not release.wait(10): raise AssertionError('second identity creation did not finish')
                return out

        def callback():
            try: results.append(self.tt.callback(self.store, first_flow['state'], first_flow['binding'], 'code'))
            except Exception as error: results.append(error)

        thread = threading.Thread(target=callback, name='tt-preflight-race')
        try:
            with patch.object(self.store, 'connect', side_effect=lambda: ObservedConnection(connect())), \
                    patch('game.tiktok_auth.exchange_identity', return_value=('racing-person', 'TikTok Person')):
                thread.start(); self.assertTrue(preflight.wait(10))
                owner = self.tt.callback(self.store, other_flow['state'], other_flow['binding'], 'code')
                release.set(); thread.join(10); self.assertFalse(thread.is_alive())
        finally:
            release.set()
            if thread.is_alive(): thread.join(10)
        self.assertEqual(len(results), 1); self.assertIsInstance(results[0], accounts.AccountError)
        self.assertEqual(results[0].code, 'tiktok_conflict')
        self.store.read(self.token); self.store.read(owner['token'])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM accounts').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM tiktok_identities').fetchone()[0], 1)

    def test_concurrent_callbacks_exchange_state_only_once(self):
        f = self.begin(); entered = threading.Event(); release = threading.Event(); results = []
        def exchange(code):
            entered.set(); self.assertTrue(release.wait(5)); return ('person-a', 'TikTok Person')
        def callback():
            try: results.append(self.tt.callback(self.store, f['state'], f['binding'], 'code'))
            except accounts.AccountError as e: results.append(e.code)
        with patch('game.tiktok_auth.exchange_identity', side_effect=exchange) as provider:
            first = threading.Thread(target=callback); first.start(); self.assertTrue(entered.wait(5))
            second = threading.Thread(target=callback); second.start(); second.join(5)
            release.set(); first.join(5)
            self.assertFalse(first.is_alive()); self.assertFalse(second.is_alive()); provider.assert_called_once()
        self.assertIn('tiktok_state', results)
        self.assertEqual(sum(isinstance(r, dict) and r.get('status') == 'success' for r in results), 1)

    def test_denial_provider_failure_consumes_flow_and_preserves_save(self):
        f = self.begin()
        with self.assertRaises(accounts.AccountError): self.tt.callback(self.store, f['state'], f['binding'], None, 'access_denied')
        self.store.read(self.token)
        with self.assertRaises(accounts.AccountError): self.finish(f)
        f = self.begin()
        with patch('game.tiktok_auth.exchange_identity', side_effect=accounts.AccountError('safe', 'tiktok_provider')):
            with self.assertRaises(accounts.AccountError): self.tt.callback(self.store, f['state'], f['binding'], 'code')
        self.store.read(self.token)
        with self.assertRaises(accounts.AccountError): self.finish(f)

    def test_identity_is_namespaced_by_client_key_not_display_name(self):
        owner = self.finish(self.begin()); fresh, _, _ = self.store.session()
        out = self.finish(self.begin(fresh), ('different-person', 'TikTok Person'))
        self.assertNotEqual(self.store.key(owner['token']), self.store.key(out['token']))
        fresh, _, _ = self.store.session()
        with patch.dict(os.environ, {'TIKTOK_CLIENT_KEY': 'second-app'}):
            out = self.finish(self.begin(fresh))
        self.assertNotEqual(self.store.key(owner['token']), self.store.key(out['token']))

    def test_account_deletion_removes_identity_and_source_or_target_flows(self):
        out = self.finish(self.begin()); f = self.begin(out['token'], 'link')
        fresh, _, _ = self.store.session(); self.finish(self.begin(fresh))
        phone, _, _ = self.store.session(); self.store.command(phone, 'tt-delete-progress', 0, 'florist', 'start_day', {})
        other = self.begin(phone); self.finish(other)
        social.forget(self.store, out['token']); self.store.delete(out['token'])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM tiktok_identities').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM tiktok_flows').fetchone()[0], 0)

    def test_pg_metadata_contains_additive_identity_and_flow_tables(self):
        names = {t['name'] for t in pg_schema.TABLES}
        self.assertTrue({'tiktok_identities', 'tiktok_flows'} <= names)
        self.assertIn('CREATE TABLE IF NOT EXISTS tiktok_identities', pg_schema.TABLES_DDL)


class TikTokProviderTests(unittest.TestCase):
    def setUp(self):
        self.tt = importlib.import_module('game.tiktok_auth')
        self.env = patch.dict(os.environ, ENV); self.env.start()

    def tearDown(self): self.env.stop()

    def test_exchange_uses_fixed_endpoints_form_body_minimal_fields_no_redirects(self):
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        seen = []
        class Opener:
            def open(self, req, timeout):
                seen.append((req, timeout))
                body = {'access_token': 'private-token', 'open_id': 'person-a', 'scope': 'user.info.basic'} if req.data else {'data': {'user': {'open_id': 'person-a', 'display_name': 'Display'}}, 'error': {'code': 'ok'}}
                return Response(json.dumps(body).encode())
        with patch('game.tiktok_auth.build_opener', return_value=Opener()) as build:
            self.assertEqual(self.tt.exchange_identity('private-code'), ('person-a', 'Display'))
        self.assertIsInstance(build.call_args.args[0], self.tt.NoRedirect)
        token, info = seen
        self.assertEqual(token[0].full_url, 'https://open.tiktokapis.com/v2/oauth/token/')
        form = parse_qs(token[0].data.decode())
        self.assertEqual(form['grant_type'], ['authorization_code']); self.assertEqual(form['redirect_uri'], [ENV['TIKTOK_REDIRECT_URI']])
        self.assertEqual(token[0].get_header('Content-type'), 'application/x-www-form-urlencoded')
        self.assertEqual(info[0].full_url, 'https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name')
        self.assertEqual(info[0].get_header('Authorization'), 'Bearer private-token')
        self.assertLessEqual(token[1], 10); self.assertLessEqual(info[1], 10)
        self.assertIsNone(self.tt.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.example'))

    def test_provider_errors_and_oversized_responses_are_sanitized(self):
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        for raw in (b'{"error":"private-provider-message"}', b'x' * 70000, b'invalid-json'):
            opener = unittest.mock.Mock(); opener.open.return_value = Response(raw)
            with self.subTest(raw=raw[:40]), patch('game.tiktok_auth.build_opener', return_value=opener), self.assertRaises(accounts.AccountError) as e:
                self.tt.exchange_identity('private-code')
            self.assertNotIn('private-', str(e.exception))


class TikTokFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is not installed')
    def test_account_forms_and_oauth_callback_feedback(self):
        out = subprocess.run(['node', '--experimental-default-type=module', str(Path(__file__).with_name('tiktok_account.mjs'))],
                             capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(json.loads(out.stdout)['ok'])


if __name__ == '__main__': unittest.main()
