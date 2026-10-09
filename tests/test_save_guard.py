"""💾 Nhập bản lưu (game/save_guard.py), over HTTP: an account's save never imports (an operator's restore excepted);
a guest imports only an untouched export of this server, not older and not richer than the save it replaces; every
attempt writes one `[import]` line. Runs on PostgreSQL with TEST_DATABASE_URL."""
import contextlib
import copy
import http.client
import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import save_guard
from game.storage import Store
from server import GameServer

PW = 'matkhau-rat-dai'
REG = dict(password=PW, confirm=PW, display='Người Thử')


class SaveGuardHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.store = Store(Path(cls.temp.name) / 'state.db', story=True)
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'op_admin', 'MNL_IMPORT_GUARD_OFF': '0',
                                          'SAVE_SIGN_SECRET': 'test-secret'})
        cls.env.start()
        cls.fast = [patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw),
                    patch('game.accounts.verify_password', lambda pw, stored: stored == 'scrypt$test$' + pw)]
        for p in cls.fast:
            p.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.store.close_pool()
        for p in cls.fast:
            p.stop()
        cls.env.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.server.limits.clear()
        self.n = 0

    def req(self, dev, path, method='GET', body=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if dev.get('cookie'):
            h['Cookie'] = dev['cookie']
        if dev.get('csrf'):
            h['X-Game-CSRF'] = dev['csrf']
        if body is not None:
            h['Content-Type'] = 'application/json'
            body = json.dumps(body)
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=15)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse()
        raw, hdrs = res.read(), dict(res.getheaders())
        con.close()
        data = json.loads(raw or b'{}')
        if 'Set-Cookie' in hdrs:
            dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        if isinstance(data, dict) and data.get('csrf'):
            dev['csrf'] = data['csrf']
        if isinstance(data, dict) and isinstance(data.get('revision'), int):
            dev['rev'] = data['revision']
        return res.status, data

    def guest(self):
        dev = {}
        self.assertEqual(self.req(dev, '/api/bootstrap?lite=1')[0], 200)
        return dev

    def account(self, name):
        dev = self.guest()
        status, data = self.req(dev, '/api/account/register', 'POST', dict(REG, username=name))
        self.assertEqual(status, 200, data)
        self.req(dev, '/api/bootstrap?lite=1')
        return dev

    def cmd(self, dev, action, payload=None):
        self.n += 1
        return self.req(dev, '/api/command', 'POST', dict(request_id=f'sg-{id(dev)}-{self.n:04d}',
                        expected_revision=dev.get('rev', 0), career=None, action=action, payload=payload or {}))

    def export(self, dev):
        status, data = self.req(dev, '/api/save/export')
        self.assertEqual(status, 200)
        return json.loads(json.dumps(data))  # what a browser sends back from the file

    def imp(self, dev, save):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            status, data = self.cmd(dev, 'import_save', dict(save=save))
        lines = [ln for ln in err.getvalue().splitlines() if ln.startswith('[import]')]
        self.assertEqual(len(lines), 1, err.getvalue())
        return status, data, lines[0]

    # ---- accounts --------------------------------------------------------------------
    def test_account_save_never_imports(self):
        dev = self.account('sg_player')
        save = self.export(dev)
        status, data, line = self.imp(dev, save)
        self.assertEqual(status, 400, data)
        self.assertEqual(data.get('code'), 'import_account')
        self.assertIn('uid=sg_player', line)
        self.assertIn('refused:import_account', line)

    def test_operator_may_restore(self):
        dev = self.account('op_admin')
        save = self.export(dev)
        save['state']['journey']['wallet'] = save['state']['journey'].get('wallet', 0) + 5  # even an edited one
        status, data, line = self.imp(dev, save)
        self.assertEqual(status, 200, data)
        self.assertIn('uid=op_admin', line)
        self.assertIn('ok admin', line)

    def test_client_cannot_claim_admin(self):
        dev = self.account('sg_sneaky')
        save = self.export(dev)
        self.n += 1
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            status, data = self.req(dev, '/api/command', 'POST', dict(request_id=f'sg-sneak-{self.n:04d}',
                                    expected_revision=dev.get('rev', 0), career=None, action='import_save',
                                    payload=dict(save=save, admin_restore=True)))
        self.assertEqual(data.get('code'), 'import_account')

    # ---- guests ----------------------------------------------------------------------
    def test_guest_untouched_export_of_the_same_revision(self):
        a = self.guest()
        save = self.export(a)
        status, data, line = self.imp(a, save)  # same save, same revision: allowed (nothing gained)
        self.assertEqual(status, 200, data)
        self.assertIn('guest=', line)
        self.assertIn(' ok', line)

    def test_guest_edited_file_refused(self):
        a = self.guest()
        save = self.export(a)
        save['state']['journey']['wallet'] = 0  # less money, still an edit
        save['state']['name'] = 'Đã sửa'
        status, data, line = self.imp(a, save)
        self.assertEqual(data.get('code'), 'import_unsigned', data)
        self.assertIn('refused:import_unsigned', line)

    def test_guest_old_file_without_signature_refused(self):
        a = self.guest()
        save = self.export(a)
        save.pop('sign')
        self.assertEqual(self.imp(a, save)[1].get('code'), 'import_unsigned')

    def test_guest_older_export_refused(self):
        a = self.guest()
        save = self.export(a)
        self.assertEqual(self.cmd(a, 'settings', dict(name='Bé A'))[0], 200)
        status, data, line = self.imp(a, save)
        self.assertEqual(data.get('code'), 'import_older', data)

    def test_guest_richer_clone_refused(self):
        a = self.guest()
        token = a['cookie'].split('=', 1)[1]
        sid = self.store.resolve(token)[0]
        # a's save holds more xu than a fresh save: an operator gift is the honest way to get it here
        state, rev, _ = self.store.read(token)
        rich = copy.deepcopy(state)
        rich['journey']['wallet'] = save_guard.money(state) + 50_000
        rich.pop('check', None)
        save = dict(format='mot-ngay-lam-nghe/save-v4', state=rich, sign=save_guard.sign(sid, rev + 50, rich))
        b = self.guest()
        status, data, line = self.imp(b, save)
        self.assertEqual(data.get('code'), 'import_richer', data)
        self.assertIn('xu=', line)

    def test_signature_survives_integral_floats(self):
        st = {'a': 3.0, 'b': [1.0, 2.5], 'c': {'d': 0.0}}
        self.assertEqual(save_guard.digest(st), save_guard.digest(json.loads(json.dumps({'a': 3, 'b': [1, 2.5], 'c': {'d': 0}}))))


if __name__ == '__main__':
    unittest.main()
