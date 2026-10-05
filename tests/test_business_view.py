import concurrent.futures
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import business_view
from game import business
from game.engine import GameError, public_state
from game.storage import Store
from tests.test_quay import opened, ST


class QuaySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'quay-view')
        self.token, _, _ = self.store.session()
        self.now = 2000000000
        with patch('game.business.time.time', return_value=self.now):
            self.state = opened(staff=False)
            self.store.command(self.token, 'import-view', 0, None, 'import_save',
                {'save': {'format': 'mot-ngay-lam-nghe/save-v4', 'state': self.state}})

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def snapshot(self, at=None):
        with patch('business_view.time.time', return_value=self.now if at is None else at):
            return business_view.quay_snapshot(self.store, self.token)

    def test_projection_matches_authoritative_view_and_excludes_other_careers(self):
        got = self.snapshot()
        state, revision, _ = self.store.read(self.token)
        expected = public_state(state)['journey']
        self.assertEqual(got, {'revision': revision, 'journey':
            {key: expected.get(key) for key in ('story', 'life_day', 'wallet', 'quay')}})
        self.assertNotIn('state', got)

    def test_http_projection_requires_session_and_cached_poll_skips_large_read(self):
        import http.client
        import json
        import threading
        from server import GameServer
        server = GameServer(('127.0.0.1', 0), self.store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def get(cookie=None):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
            conn.request('GET', '/api/business/quay', headers={'Cookie': 'mnl_session=' + cookie} if cookie else {})
            response = conn.getresponse()
            body = json.loads(response.read())
            conn.close()
            return response.status, body
        try:
            self.assertEqual(get()[0], 401)
            with patch('business_view.time.time', return_value=self.now):
                status, first = get(self.token)
                self.assertEqual(status, 200)
                with patch.object(self.store, 'read', side_effect=AssertionError('large save reread')):
                    status, second = get(self.token)
            self.assertEqual(status, 200)
            self.assertEqual(first['journey'], second['journey'])
            self.assertEqual(first['revision'], second['revision'])
            self.assertNotIn('state', second)
            self.assertNotIn('csrf', second)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_idle_cache_checks_revision_without_reading_save_and_cannot_be_mutated(self):
        first = self.snapshot()
        first['journey']['wallet'] = -999
        first['journey']['quay']['stalls'].clear()
        with patch.object(self.store, 'read', side_effect=AssertionError('large save reread')):
            second = self.snapshot(self.now + 5)
        self.assertGreater(second['journey']['wallet'], 0)
        self.assertEqual(len(second['journey']['quay']['stalls']), 1)

    def test_cache_observes_external_revision_change(self):
        before = self.snapshot()
        self.store.command(self.token, 'rename-view', before['revision'], None, 'settings', {'name': 'Tên mới'})
        with patch.object(self.store, 'read', wraps=self.store.read) as reads:
            after = self.snapshot(self.now + 5)
        self.assertGreater(after['revision'], before['revision'])
        self.assertEqual(reads.call_count, 1)

    def test_cache_rejects_revoked_login(self):
        login = 'b' * 64
        sid = self.store.key(self.token)
        with self.store.connect() as db:
            db.execute('INSERT INTO logins(token,sid,csrf) VALUES(?,?,?)', (self.store.digest(login), sid, 'csrf'))
        with patch('business_view.time.time', return_value=self.now):
            business_view.quay_snapshot(self.store, login)
        with self.store.connect() as db:
            db.execute('DELETE FROM logins WHERE token=?', (self.store.digest(login),))
        with self.assertRaises(GameError) as caught:
            business_view.quay_snapshot(self.store, login)
        self.assertEqual(caught.exception.code, 'session_missing')

    def test_new_token_resolution_never_reuses_previous_players_projection(self):
        login = 'c' * 64
        other, _, _ = self.store.session()
        sid = self.store.key(self.token)
        with self.store.connect() as db:
            db.execute('INSERT INTO logins(token,sid,csrf) VALUES(?,?,?)', (self.store.digest(login), sid, 'csrf'))
        with patch('business_view.time.time', return_value=self.now):
            before = business_view.quay_snapshot(self.store, login)
            with self.store.connect() as db:
                db.execute('UPDATE logins SET sid=? WHERE token=?', (self.store.key(other), self.store.digest(login)))
            after = business_view.quay_snapshot(self.store, login)
        self.assertTrue(before['journey']['quay']['stalls'])
        self.assertIsNone(after['journey']['quay'])

    def test_running_shop_uses_atomic_settlement_and_concurrent_reads_never_double_pay(self):
        with patch('game.business.time.time', return_value=self.now):
            running = opened(staff=True)
            revision = self.store.read(self.token)[1]
            self.store.command(self.token, 'import-running', revision, None, 'import_save',
                {'save': {'format': 'mot-ngay-lam-nghe/save-v4', 'state': running}})
        state, _, _ = self.store.read(self.token)
        at = self.now + 100
        expected = copy.deepcopy(state)
        with patch('game.business.time.time', return_value=at):
            business.settle(expected)
            business.reconcile(expected)
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: business_view.quay_snapshot(self.store, self.token), range(4)))
        actual, _, _ = self.store.read(self.token)
        self.assertEqual(ST(actual)['business']['sold'], ST(expected)['business']['sold'])
        self.assertEqual(ST(actual)['fund'], ST(expected)['fund'])
        self.assertEqual(ST(actual)['till'], ST(expected)['till'])
        self.assertEqual(results[-1]['journey']['quay']['stalls'][0]['business']['sold'], ST(actual)['business']['sold'])

    def test_cache_horizon_does_not_delay_future_workplace_order(self):
        from tests.test_business_storage import BusinessStorageTests
        sample = BusinessStorageTests()
        sample.setUp()
        try:
            with patch('business_view.time.time', return_value=sample.at - 60):
                business_view.quay_snapshot(sample.store, sample.token)
            with patch('business_view.time.time', return_value=sample.at), patch.object(sample.store, 'command', wraps=sample.store.command) as commands:
                business_view.quay_snapshot(sample.store, sample.token)
            self.assertEqual(commands.call_count, 1)
            state, _, _ = sample.store.read(sample.token)
            self.assertEqual(state['careers']['accounting']['ops']['business']['served'], 1)
        finally:
            sample.tearDown()
