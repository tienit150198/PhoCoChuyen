import http.client, json, os, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch

from tests.pg_support import on_pg
from game import accounts, social
from game.storage import Store, Conflict
from server import GameServer

REG = dict(username='Mai.Chi_9', password='matkhau-rat-dai', confirm='matkhau-rat-dai', display='Mai Chi')


class AccountStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db')
        social.ensure(self.store)
        self.token, self.csrf, _ = self.store.session()
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def play(self, token, action='start_day', career='mother_baby'):
        self.n += 1
        rev = self.store.read(token)[1]
        return self.store.command(token, f'acct-test-{self.n:04d}', rev, career, action, {})

    def test_password_hash_is_salted_scrypt_and_verifies(self):
        a, b = accounts.hash_password('abcdefgh'), accounts.hash_password('abcdefgh')
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith('scrypt$'))
        self.assertTrue(accounts.verify_password('abcdefgh', a))
        self.assertFalse(accounts.verify_password('abcdefgX', a))
        self.assertFalse(accounts.verify_password('abcdefgh', 'garbage'))

    def test_register_attaches_current_save_and_rotates_token(self):
        self.play(self.token)
        before = self.store.read(self.token)
        out = accounts.register(self.store, self.token, REG)
        self.assertEqual(out['account'], dict(username='mai.chi_9', display='Mai Chi'))
        self.assertEqual(out['csrf'], self.csrf)  # open tabs keep their CSRF
        state, rev, csrf = self.store.read(out['token'])
        self.assertTrue(state['careers']['mother_baby']['started'])
        self.assertGreaterEqual(rev, before[1])
        self.assertEqual(state['name'], 'Mai Chi')  # adopted: player had the default name
        # The pre-registration cookie no longer opens the account's save.
        with self.assertRaises(Exception):
            self.store.read(self.token)
        with self.store.connect() as db:
            row = db.execute('SELECT pw FROM accounts').fetchone()
            prof = db.execute('SELECT name FROM profiles').fetchone()
        self.assertNotIn('matkhau', row['pw'])
        self.assertEqual(prof['name'], 'Mai Chi')

    def test_register_keeps_a_chosen_name(self):
        self.n += 1
        self.store.command(self.token, 'acct-name-0001', 0, None, 'settings', {'name': 'Tí Nị'})
        out = accounts.register(self.store, self.token, REG)
        self.assertEqual(self.store.read(out['token'])[0]['name'], 'Tí Nị')

    def test_register_validation(self):
        bad = [dict(REG, username='ab'), dict(REG, username='có dấu'), dict(REG, username='x' * 25),
               dict(REG, password='short', confirm='short'), dict(REG, confirm='khac-hoan-toan'),
               dict(REG, display=''), dict(REG, display='https://spam.com'), dict(REG, display='12345'), dict(REG, display=None)]
        for d in bad:
            with self.subTest(d=d), self.assertRaises(accounts.AccountError):
                accounts.register(self.store, self.token, d)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM accounts').fetchone()[0], 0)

    def test_duplicate_username_is_case_insensitive(self):
        accounts.register(self.store, self.token, REG)
        other, _, _ = self.store.session()
        with self.assertRaises(accounts.AccountError) as e:
            accounts.register(self.store, other, dict(REG, username='MAI.CHI_9'))
        self.assertEqual(e.exception.code, 'username_taken')

    def test_cannot_register_twice_from_signed_in_device(self):
        out = accounts.register(self.store, self.token, REG)
        with self.assertRaises(accounts.AccountError):
            accounts.register(self.store, out['token'], dict(REG, username='khac'))

    def test_login_wrong_password_and_unknown_user_are_generic(self):
        accounts.register(self.store, self.token, REG)
        other, _, _ = self.store.session()
        msgs = set()
        for d in (dict(username='mai.chi_9', password='sai-mat-khau'), dict(username='khong_co', password='sai-mat-khau')):
            with self.assertRaises(accounts.AccountError) as e:
                accounts.login(self.store, other, d)
            msgs.add(e.exception.message)
        self.assertEqual(msgs, {accounts.WRONG})

    def test_login_replaces_save_and_two_devices_share_it(self):
        a = accounts.register(self.store, self.token, REG)['token']
        self.play(a)
        phone, _, _ = self.store.session()
        self.play(phone, career='florist')  # this device has its own progress (a shop: no hiring step)
        with self.assertRaises(accounts.AccountError) as e:
            accounts.check_replace(self.store, phone, dict(username='mai.chi_9', password=REG['password']))
        self.assertEqual(e.exception.code, 'confirm_replace')
        accounts.check_replace(self.store, phone, dict(replace=True))
        out = accounts.login(self.store, phone, dict(username='MAI.CHI_9', password=REG['password'], replace=True))
        self.assertTrue(out['drop_anonymous'])
        b = out['token']
        sa, ra, ca = self.store.read(a)
        sb, rb, cb = self.store.read(b)
        self.assertEqual((sa, ra), (sb, rb))
        self.assertNotEqual(ca, cb)  # CSRF is per device
        self.assertFalse(sb['careers']['florist']['started'])
        # A write on one device bumps the shared revision; the other device's stale write conflicts.
        self.store.command(a, 'acct-share-0001', ra, 'mother_baby', 'settings', {'sound': False})
        with self.assertRaises(Conflict):
            self.store.command(b, 'acct-share-0002', rb, 'mother_baby', 'settings', {'sound': True})
        self.assertFalse(self.store.read(b)[0]['settings']['sound'])
        self.assertEqual(accounts.status(self.store, b), dict(username='mai.chi_9', display='Mai Chi'))
        self.assertIsNone(accounts.status(self.store, phone))

    def test_fresh_device_needs_no_confirmation(self):
        accounts.register(self.store, self.token, REG)
        fresh, _, _ = self.store.session()
        accounts.check_replace(self.store, fresh, dict(username='mai.chi_9'))  # no raise

    def test_logout_revokes_only_this_device(self):
        a = accounts.register(self.store, self.token, REG)['token']
        other, _, _ = self.store.session()
        b = accounts.login(self.store, other, dict(username='mai.chi_9', password=REG['password']))['token']
        accounts.logout(self.store, b)
        with self.assertRaises(Exception):
            self.store.read(b)
        self.store.read(a)
        with self.assertRaises(accounts.AccountError):
            accounts.logout(self.store, other)  # anonymous: nothing to log out of

    def test_change_password(self):
        a = accounts.register(self.store, self.token, REG)['token']
        other, _, _ = self.store.session()
        b = accounts.login(self.store, other, dict(username='mai.chi_9', password=REG['password']))['token']
        with self.assertRaises(accounts.AccountError):
            accounts.change_password(self.store, a, dict(current='sai-mat-khau', password='moi-moi-moi', confirm='moi-moi-moi'))
        with self.assertRaises(accounts.AccountError):
            accounts.change_password(self.store, a, dict(current=REG['password'], password='moi-moi-moi', confirm='khac-khac-khac'))
        accounts.change_password(self.store, a, dict(current=REG['password'], password='moi-moi-moi', confirm='moi-moi-moi'))
        self.store.read(a)
        with self.assertRaises(Exception):
            self.store.read(b)  # other devices sign in again
        third, _, _ = self.store.session()
        with self.assertRaises(accounts.AccountError):
            accounts.login(self.store, third, dict(username='mai.chi_9', password=REG['password']))
        accounts.login(self.store, third, dict(username='mai.chi_9', password='moi-moi-moi'))

    def test_delete_removes_account_and_logins(self):
        a = accounts.register(self.store, self.token, REG)['token']
        social.forget(self.store, a)
        self.store.delete(a)
        with self.store.connect() as db:
            for table in ('accounts', 'logins'):
                self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0)
        other, _, _ = self.store.session()
        with self.assertRaises(accounts.AccountError):
            accounts.login(self.store, other, dict(username='mai.chi_9', password=REG['password']))
        accounts.register(self.store, other, REG)  # the name is free again

    def test_prune_keeps_account_saves(self):
        a = accounts.register(self.store, self.token, REG)['token']
        anon, _, _ = self.store.session()
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET updated_at=to_char((statement_timestamp() AT TIME ZONE 'UTC') - interval '400 days', 'YYYY-MM-DD HH24:MI:SS')")
        self.store.prune(180)
        self.store.read(a)
        with self.assertRaises(Exception):
            self.store.read(anon)

    def test_old_database_gains_tables_and_sessions_keep_working(self):
        path = Path(self.tmp.name) / 'old.db'
        old = Store(path)
        token, _, _ = old.session()
        with old.connect() as db:
            db.execute('DROP TABLE logins')
            db.execute('DROP TABLE accounts')
        again = Store(path)
        self.assertEqual(again.read(token)[1], 0)
        self.assertIsNone(accounts.status(again, token))


class AccountHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = GameServer(('127.0.0.1', 0), Store(Path(cls.temp.name) / 'state.db'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.quiet = patch.dict(os.environ, {'QUIET': '1'})
        cls.quiet.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.temp.cleanup(); cls.quiet.stop()

    def setUp(self):
        self.server.limits.clear()

    def req(self, dev, path, method='GET', body=None, headers=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if dev.get('cookie'): h['Cookie'] = dev['cookie']
        if dev.get('csrf'): h['X-Game-CSRF'] = dev['csrf']
        if body is not None: h['Content-Type'] = 'application/json'; body = json.dumps(body)
        h.update(headers or {})
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse(); data = json.loads(res.read() or b'{}'); hdrs = dict(res.getheaders()); con.close()
        if 'Set-Cookie' in hdrs: dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        if isinstance(data, dict) and data.get('csrf'): dev['csrf'] = data['csrf']
        return res.status, data, hdrs

    def device(self):
        dev = {}
        status, data, _ = self.req(dev, '/api/bootstrap')
        self.assertEqual(status, 200)
        self.assertIsNone(data['account'])
        return dev

    def play(self, dev, n=1):
        _, st, _ = self.req(dev, '/api/state')
        return self.req(dev, '/api/command', 'POST', dict(request_id=f'http-acct-{id(dev)}-{n}', expected_revision=st['revision'], career='mother_baby', action='start_day', payload={}))

    def user(self, name):
        return dict(REG, username=name)

    def test_full_flow_register_clear_cookies_login(self):
        a = self.device()
        self.assertEqual(self.play(a)[0], 200)
        status, data, h = self.req(a, '/api/account/register', 'POST', self.user('flow_user'))
        self.assertEqual(status, 200, data)
        self.assertIn('HttpOnly', h['Set-Cookie']); self.assertIn('SameSite=Strict', h['Set-Cookie'])
        self.assertNotIn('token', data); self.assertNotIn('pw', json.dumps(data))
        _, boot, _ = self.req(a, '/api/bootstrap')
        self.assertEqual(boot['account']['username'], 'flow_user')
        self.assertTrue(boot['state']['careers']['mother_baby']['started'])
        # Browser reset: a new anonymous device logs in; a fresh session needs no confirm.
        b = self.device()
        status, data, _ = self.req(b, '/api/account/login', 'POST', dict(username='Flow_User', password=REG['password']))
        self.assertEqual(status, 200, data)
        _, boot, _ = self.req(b, '/api/bootstrap')
        self.assertTrue(boot['state']['careers']['mother_baby']['started'])
        self.assertEqual(boot['account']['display'], 'Mai Chi')
        # Two devices, one save: device A still works with its own CSRF.
        _, sa, _ = self.req(a, '/api/state'); _, sb, _ = self.req(b, '/api/state')
        self.assertEqual(sa['revision'], sb['revision'])
        self.assertNotEqual(a['csrf'], b['csrf'])
        # CSRF of one device is not accepted with the other device's cookie.
        stolen = dict(cookie=b['cookie'], csrf=a['csrf'])
        self.assertEqual(self.req(stolen, '/api/account/logout', 'POST', {})[0], 403)
        # Logout starts a fresh anonymous session.
        status, data, h = self.req(b, '/api/account/logout', 'POST', {})
        self.assertEqual(status, 200)
        _, boot, _ = self.req(b, '/api/bootstrap')
        self.assertIsNone(boot['account'])
        self.assertFalse(boot['state']['careers']['mother_baby']['started'])

    def test_login_with_progress_asks_confirmation_first(self):
        a = self.device(); self.req(a, '/api/account/register', 'POST', self.user('confirm_me'))
        b = self.device(); self.play(b)
        status, data, _ = self.req(b, '/api/account/login', 'POST', dict(username='confirm_me', password=REG['password']))
        self.assertEqual((status, data['code']), (409, 'confirm_replace'))
        status, data, _ = self.req(b, '/api/account/login', 'POST', dict(username='confirm_me', password=REG['password'], replace=True))
        self.assertEqual(status, 200, data)

    def test_duplicate_and_wrong_password(self):
        a = self.device(); self.assertEqual(self.req(a, '/api/account/register', 'POST', self.user('dup_user'))[0], 200)
        b = self.device()
        status, data, _ = self.req(b, '/api/account/register', 'POST', self.user('DUP_user'))
        self.assertEqual((status, data['code']), (409, 'username_taken'))
        status, data, _ = self.req(b, '/api/account/login', 'POST', dict(username='dup_user', password='wrong-password'))
        self.assertEqual((status, data['error']), (401, 'Sai tên đăng nhập hoặc mật khẩu.'))
        status, data, _ = self.req(b, '/api/account/login', 'POST', dict(username='nobody_here', password='wrong-password'))
        self.assertEqual((status, data['error']), (401, 'Sai tên đăng nhập hoặc mật khẩu.'))

    def test_login_rate_limited_per_username(self):
        a = self.device(); self.req(a, '/api/account/register', 'POST', self.user('limited'))
        b = self.device()
        codes = [self.req(b, '/api/account/login', 'POST', dict(username='limited', password='wrong-password'))[0] for _ in range(6)]
        self.assertEqual(codes[:5], [401] * 5)
        self.assertEqual(codes[5], 429)
        # Even the right password waits while the limit holds.
        self.assertEqual(self.req(b, '/api/account/login', 'POST', dict(username='limited', password=REG['password']))[0], 429)

    def test_register_rate_limited_per_ip(self):
        codes = []
        for i in range(6):
            d = self.device()
            codes.append(self.req(d, '/api/account/register', 'POST', self.user(f'burst_{i}'))[0])
        self.assertEqual(codes, [200] * 5 + [429])

    def test_account_posts_need_csrf_and_same_origin(self):
        a = self.device()
        self.assertEqual(self.req(dict(cookie=a['cookie'], csrf='wrong'), '/api/account/register', 'POST', self.user('csrf_user'))[0], 403)
        self.assertEqual(self.req(a, '/api/account/register', 'POST', self.user('csrf_user'), {'Origin': 'https://evil.example'})[0], 403)

    def test_change_password_and_delete(self):
        a = self.device(); self.req(a, '/api/account/register', 'POST', self.user('pw_user'))
        status, data, _ = self.req(a, '/api/account/password', 'POST', dict(current='wrong-password', password='new-pass-123', confirm='new-pass-123'))
        self.assertEqual(status, 401)
        status, data, _ = self.req(a, '/api/account/password', 'POST', dict(current=REG['password'], password='new-pass-123', confirm='new-pass-123'))
        self.assertEqual(status, 200, data)
        status, data, _ = self.req(a, '/api/account/delete', 'POST', dict(confirm='XOA'))
        self.assertEqual(status, 200)
        b = self.device()
        status, _, _ = self.req(b, '/api/account/login', 'POST', dict(username='pw_user', password='new-pass-123'))
        self.assertEqual(status, 401)
        with self.server.store.connect() as db:
            self.assertIsNone(db.execute("SELECT 1 FROM accounts WHERE username='pw_user'").fetchone())


if __name__ == '__main__':
    unittest.main()
