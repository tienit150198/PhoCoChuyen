"""🎁 "Tặng xu" on the operator site (/admin): GET /api/admin/gifts and POST /api/admin/gift (game/system_gift.py).
Only ADMIN_USERS with the session's CSRF; the server checks the account, the amount (1..MAX_COINS, an integer, a second
confirmation above LARGE), the words; the gift id comes from the server and a retry with the same key finds the same
gift; the coins reach the player's wallet once, at their next load, through the normal gift path; the admin is recorded.
Runs on PostgreSQL with TEST_DATABASE_URL."""
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import db as dbm, pg_schema
from game import system_gift as sg
from game.storage import Store
from server import GameServer

PW = 'matkhau-rat-dai'
REG = dict(password=PW, confirm=PW, display='Người Thử')


class AdminGiftHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.store = Store(Path(cls.temp.name) / 'state.db', story=True)
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'op_admin'})
        cls.env.start()
        cls.fast = [patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw),
                    patch('game.accounts.verify_password', lambda pw, stored: stored == 'scrypt$test$' + pw)]
        for p in cls.fast:
            p.start()
        cls.admin = cls.signed_up(cls, 'op_admin')
        cls.player = cls.signed_up(cls, 'be_na')
        cls.other = cls.signed_up(cls, 'be_nam')

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

    # ---- helpers ----------------------------------------------------------------------
    def req(self, dev, path, method='GET', body=None, csrf=True, headers=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if dev.get('cookie'):
            h['Cookie'] = dev['cookie']
        if csrf and dev.get('csrf'):
            h['X-Game-CSRF'] = dev['csrf']
        h.update(headers or {})
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
        return res.status, data

    def signed_up(self, name):
        dev = {}
        status, _ = AdminGiftHTTP.req(self, dev, '/api/bootstrap?lite=1')
        assert status == 200
        status, data = AdminGiftHTTP.req(self, dev, '/api/account/register', 'POST', dict(REG, username=name))
        assert status == 200, data
        return dev

    def boot(self, dev):
        status, data = self.req(dev, '/api/bootstrap?lite=1')
        self.assertEqual(status, 200, data)
        return data

    def give(self, coins, rid, user='be_na', **kw):
        return self.req(self.admin, '/api/admin/gift', 'POST', dict(user=user, coins=coins, rid=rid, **kw))

    def rows(self, user):
        with self.store.connect() as db:
            sid = db.execute('SELECT sid FROM accounts WHERE username=?', (user,)).fetchone()['sid']
            return [dict(r) for r in db.execute('SELECT * FROM system_gifts WHERE sid=? ORDER BY created', (sid,))]

    # ---- tests ------------------------------------------------------------------------
    def test_only_admins_with_the_csrf(self):
        body = dict(user='be_na', coins=10, rid='rid-nonadmin-1')
        anon = {}
        self.boot(anon)
        for dev in (anon, self.player):
            self.assertEqual(self.req(dev, '/api/admin/gift', 'POST', body)[0], 403)
            self.assertEqual(self.req(dev, '/api/admin/gifts')[0], 403)
        self.assertEqual(self.req({}, '/api/admin/gifts')[0], 401)
        self.assertEqual(self.req(self.admin, '/api/admin/gift', 'POST', body, csrf=False)[0], 403)
        self.assertEqual(self.req(self.admin, '/api/admin/gifts', csrf=False)[0], 403)
        # another site's page with the admin's cookie and token
        self.assertEqual(self.req(self.admin, '/api/admin/gift', 'POST', body, headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.rows('be_na'), [], 'nothing was written')

    def test_bounds_and_checks(self):
        cases = [(dict(coins=0), 'bad_coins'), (dict(coins=-5), 'bad_coins'), (dict(coins=sg.MAX_COINS + 1), 'bad_coins'),
                 (dict(coins=10.5), 'bad_coins'), (dict(coins='100'), 'bad_coins'), (dict(coins=True), 'bad_coins'),
                 (dict(coins=sg.LARGE + 1), 'confirm_large'), (dict(coins=50_000, large='yes'), 'confirm_large'),
                 (dict(coins=10, rid='short'), 'bad_rid'), (dict(coins=10, rid=None), 'bad_rid'),
                 (dict(coins=10, user='Bé Na'), 'bad_user'), (dict(coins=10, title='x' * (sg.TITLE_MAX + 1)), 'bad_gift'),
                 (dict(coins=10, text='y' * (sg.TEXT_MAX + 1)), 'bad_gift')]
        for extra, code in cases:
            body = {'user': 'be_na', 'rid': 'rid-bounds-0001', **extra}
            status, out = self.req(self.admin, '/api/admin/gift', 'POST', body)
            self.assertEqual((status, out.get('code')), (400, code), extra)
        status, out = self.give(10, 'rid-bounds-0002', user='khong_ai_ca')
        self.assertEqual((status, out['code']), (404, 'no_user'))
        self.assertEqual(self.rows('be_na'), [])
        # the edges are allowed
        self.assertEqual(self.give(1, 'rid-bounds-0003')[1]['status'], 'created')
        status, out = self.give(sg.MAX_COINS, 'rid-bounds-0004', large=True)
        self.assertEqual((status, out['status'], out['gift']['coins']), (200, 'created', sg.MAX_COINS))
        self.assertEqual(out['gift']['text'], 'Ban quản lý phố tặng bạn 1.000.000.000 xu. Chơi vui nha! 💛')
        self.assertEqual(out['gift']['title'], 'Quà từ Phố Có Chuyện')
        self.store.transaction(lambda db: db.execute('DELETE FROM system_gifts'))  # leave the other tests a clean table

    def test_a_big_gift_has_no_cap_but_the_wallet(self):
        """Owner 08/10 "cho admin có thể tặng tiền xu k giới hạn": 5 triệu xu goes through (with the typo check) and is paid."""
        before = self.boot(self.other)['state']['journey']['wallet']
        status, out = self.give(5_000_000, 'rid-big-0000001', user='be_nam', large=True)
        self.assertEqual((status, out['status'], out['gift']['coins']), (200, 'created', 5_000_000))
        self.assertEqual(self.boot(self.other)['state']['journey']['wallet'], before + 5_000_000)
        self.store.transaction(lambda db: db.execute('DELETE FROM system_gifts'))

    def test_idempotent_paid_once_and_recorded(self):
        before = self.boot(self.other)['state']['journey']['wallet']
        words = dict(title='  Quà nè\x07 ', text='Cảm ơn bạn đã báo lỗi 💛')
        status, first = self.give(5000, 'rid-once-000001', user='be_nam', large=True, **words)
        self.assertEqual((status, first['status']), (200, 'created'), first)
        g = first['gift']
        self.assertTrue(g['id'].startswith('admin-be_nam-'), g['id'])
        self.assertEqual((g['title'], g['text'], g['status'], g['by'], g['user']), ('Quà nè', words['text'], 'pending', 'op_admin', 'be_nam'))
        self.assertNotIn('sid', g)
        # a double click / a retry with the same key: the same gift, nothing new
        status, again = self.give(5000, 'rid-once-000001', user='be_nam', large=True, **words)
        self.assertEqual((status, again['status'], again['gift']['id']), (200, 'exists', g['id']))
        # the same key with other content is refused
        status, other = self.give(6000, 'rid-once-000001', user='be_nam', large=True, **words)
        self.assertEqual(status, 400, other)
        rows = self.rows('be_nam')
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['granted_by'], rows[0]['status'], rows[0]['coins']), ('op_admin', 'pending', 5000))
        self.assertEqual(self.boot(self.other)['state']['journey']['wallet'], before + 5000, 'paid at the next load')
        self.assertEqual(self.rows('be_nam')[0]['status'], 'applied')
        third = self.boot(self.other)
        self.assertEqual(third['state']['journey']['wallet'], before + 5000, 'only once')
        self.assertEqual([x['id'] for x in third['gifts']], [g['id']])
        # a retry after delivery still finds it and pays nothing more
        self.assertEqual(self.give(5000, 'rid-once-000001', user='be_nam', large=True, **words)[1]['status'], 'exists')
        self.assertEqual(self.boot(self.other)['state']['journey']['wallet'], before + 5000)
        # the page's lists
        status, view = self.req(self.admin, '/api/admin/gifts?q=be_na')
        self.assertEqual(status, 200)
        self.assertEqual([u['username'] for u in view['users']], ['be_na', 'be_nam'])
        mine = next(u for u in view['users'] if u['username'] == 'be_nam')
        self.assertEqual((mine['gift_count'], mine['gift_coins'], mine['gifts'][0]['status'], mine['gifts'][0]['by']), (1, 5000, 'applied', 'op_admin'))
        self.assertNotIn('sid', mine)
        self.assertIn(g['id'], [x['id'] for x in view['recent']])
        self.assertEqual(next(x for x in view['recent'] if x['id'] == g['id'])['user'], 'be_nam')
        self.assertEqual((view['max'], view['large']), (sg.MAX_COINS, sg.LARGE))
        self.assertEqual(self.req(self.admin, '/api/admin/gifts?q=@BE_NAM')[1]['users'][0]['username'], 'be_nam')
        self.assertEqual(self.req(self.admin, '/api/admin/gifts?q=%27%20OR%201%3D1')[1]['users'], [])
        newest = self.req(self.admin, '/api/admin/gifts')[1]['users']
        self.assertEqual(newest[0]['username'], 'be_nam', 'no search: the newest accounts first')

    def test_two_requests_at_once_make_one_gift(self):
        out = []
        def go():
            out.append(self.give(300, 'rid-race-0000001', user='be_na'))
        ts = [threading.Thread(target=go) for _ in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertTrue(all(s == 200 for s, _ in out), out)
        self.assertEqual(sorted(o['status'] for _, o in out).count('created'), 1)
        self.assertEqual(len({o['gift']['id'] for _, o in out}), 1)
        self.assertEqual(len([r for r in self.rows('be_na') if r['coins'] == 300]), 1)


class AdminGiftSchema(unittest.TestCase):
    def test_postgres_column_and_index(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 16)
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'g.db')
            try:
                with store.connect() as db:
                    column = db.execute("SELECT column_name,data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='system_gifts' ORDER BY ordinal_position DESC LIMIT 1").fetchone()
                    self.assertEqual(tuple(column), ('granted_by', 'text'))
            finally:
                store.close_pool()
        self.assertIn('ALTER TABLE system_gifts ADD COLUMN IF NOT EXISTS granted_by', pg_schema.TABLES_DDL)
        self.assertIn('system_gifts (created)', pg_schema.INDEX_DDL)



if __name__ == '__main__':
    unittest.main()
