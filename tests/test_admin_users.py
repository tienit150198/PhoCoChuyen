"""Admin account directory: HTTP authorization, names, bounded pages and public fields.
Requires TEST_DATABASE_URL for isolated PostgreSQL schemas.
"""
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from game import accounts
from game.storage import Store
from server import COOKIE, GameServer


class AdminUsersHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.store = Store(Path(cls.temp.name) / 'state.db', story=True)
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'users_admin'})
        cls.env.start()
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.admin = cls.register('users_admin', 'Vận Hành')
        cls.player = cls.register('hong.nguyen', 'Nguyễn Hồng')
        cls.register('nam_phan', 'Phan Nam')
        cls.register('dang_hong', 'ĐẶNG HỒNG')
        with cls.store.connect() as db:
            db.execute("UPDATE profiles SET name='Bé Đào',name_key='bé đào' WHERE sid=(SELECT sid FROM accounts WHERE username='hong.nguyen')")
            # The old account name stays searchable after the character is renamed.
            db.execute("UPDATE profiles SET name='Mưa',name_key='mưa' WHERE sid=(SELECT sid FROM accounts WHERE username='dang_hong')")
            for n in range(105):
                db.execute('INSERT INTO accounts(username,display,pw,sid) VALUES(?,?,?,?)',
                           (f'paged_{n:03}', 'Người thử', 'private-password-hash', f'directory-save-{n}'))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.store.close_pool()
        cls.env.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.server.limits.clear()

    @classmethod
    def register(cls, username, display):
        token, _, _ = cls.store.session()
        out = accounts.register(cls.store, token, dict(username=username, display=display,
                                                      password='directory-password', confirm='directory-password'))
        return dict(cookie=COOKIE + '=' + out['token'], csrf=out['csrf'])

    def req(self, dev=None, query=None, csrf=True):
        dev = dev or {}
        headers = {'Host': f'127.0.0.1:{self.port}'}
        if dev.get('cookie'):
            headers['Cookie'] = dev['cookie']
        if csrf and dev.get('csrf'):
            headers['X-Game-CSRF'] = dev['csrf']
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=15)
        con.request('GET', '/api/admin/users?' + urlencode(query or {}), headers=headers)
        res = con.getresponse()
        status, data = res.status, json.loads(res.read() or b'{}')
        con.close()
        return status, data

    def names(self, query):
        status, data = self.req(self.admin, {'q': query})
        self.assertEqual(status, 200, data)
        return [x['username'] for x in data['items']]

    def test_only_admin_with_csrf_can_list(self):
        self.assertEqual(self.req()[0], 401)
        self.assertEqual(self.req(self.player)[0], 403)
        self.assertEqual(self.req(self.admin, csrf=False)[0], 403)
        self.assertEqual(self.req(self.admin)[0], 200)

    def test_list_is_paginated_and_contains_only_directory_fields(self):
        status, data = self.req(self.admin)
        self.assertEqual(status, 200, data)
        self.assertEqual(len(data['items']), 50)
        self.assertEqual(data['total'], 109)
        self.assertTrue(data['has_more'])
        for item in data['items']:
            self.assertEqual(set(item), {'id', 'username', 'display', 'name', 'created_at', 'last_active_at'})
        self.assertNotIn('private-password-hash', json.dumps(data))

    def test_find_partial_username_case_insensitively(self):
        self.assertEqual(self.names(' HONG.NG '), ['hong.nguyen'])
        self.assertEqual(self.names('@hong.nguyen'), ['hong.nguyen'])

    def test_find_account_display_name(self):
        self.assertEqual(self.names('Nguyễn Hồng'), ['hong.nguyen'])

    def test_find_current_character_name(self):
        self.assertEqual(self.names('BÉ ĐÀO'), ['hong.nguyen'])

    def test_find_uppercase_vietnamese_account_name_after_rename(self):
        self.assertEqual(self.names('đặng hồng'), ['dang_hong'])

    def test_search_treats_sql_wildcards_as_literal_text(self):
        self.assertEqual(self.names('%'), [])
        self.assertEqual(self.names("' OR 1=1 --"), [])
        self.assertEqual(len(self.names('paged_')), 50)

    def test_pages_do_not_overlap_and_last_page_is_complete(self):
        first = self.req(self.admin, {'q': 'paged_', 'limit': 100})[1]
        last = self.req(self.admin, {'q': 'paged_', 'limit': 100, 'offset': 100})[1]
        self.assertEqual(first['total'], 105)
        self.assertEqual(len(first['items']), 100)
        self.assertTrue(first['has_more'])
        self.assertEqual(len(last['items']), 5)
        self.assertFalse(last['has_more'])
        self.assertFalse({x['id'] for x in first['items']} & {x['id'] for x in last['items']})

    def test_invalid_paging_is_bounded(self):
        status, data = self.req(self.admin, {'limit': 999999, 'offset': -99})
        self.assertEqual(status, 200, data)
        self.assertEqual(len(data['items']), 100)
        self.assertEqual(data['offset'], 0)
        status, data = self.req(self.admin, {'limit': 'bad', 'offset': 'bad'})
        self.assertEqual(status, 200, data)
        self.assertEqual(len(data['items']), 50)

    def test_renamed_account_shows_both_names(self):
        status, data = self.req(self.admin, {'q': 'hong.nguyen'})
        self.assertEqual(status, 200, data)
        self.assertEqual(data['items'][0]['name'], 'Bé Đào')
        self.assertEqual(data['items'][0]['display'], 'Nguyễn Hồng')


if __name__ == '__main__':
    unittest.main()
