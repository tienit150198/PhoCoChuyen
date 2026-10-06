"""💬 Chat on the game server: PostgreSQL tables, the admin "Chat" tab (reports queue, hide / keep,
mute 1 h / 24 h / 7 d) behind ADMIN_USERS, the page CSP that lets the page open its own socket, the cleanup
when a player deletes their data, and (PostgreSQL) the NOTIFY that makes the live service apply an admin
decision at once."""
import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import admin_stats as st, live_chat, pg_schema, social
from game.storage import Store
from server import GameServer
from tests.live_support import HAVE_WS, LiveCase, needs_ws
from tests.pg_support import columns, pg_only

PW = 'matkhau-rat-dai'
REG = dict(password=PW, confirm=PW, display='Người Thử')


def add_msg(db, ch, pid, text, name='Ai đó', reports=0, hidden=0):
    return db.execute('INSERT INTO chat_messages(channel, pid, name, av, text, at, reports, hidden) VALUES(?,?,?,?,?,?,?,?) RETURNING id',
                      (ch, pid, name, '🌸', text, time.time(), reports, hidden)).fetchone()[0]


class SchemaTests(unittest.TestCase):
    def test_new_tables_only(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 6)   # 6: the chat tables (5 was Giữ chân, 0.9.18)
        for t in ('chat_channels', 'chat_members', 'chat_messages', 'chat_mutes', 'chat_prefs', 'live_effects'):
            self.assertIn(f'CREATE TABLE IF NOT EXISTS {t} (', pg_schema.TABLES_DDL)
            self.assertIn(t, pg_schema.TABLE)
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / 'g.db')
            with store.connect() as db:
                expected = {
                    'chat_channels': {'id', 'kind', 'title', 'owner_pid', 'created'},
                    'chat_members': {'channel', 'pid', 'sid', 'role', 'joined', 'last_read', 'muted_until', 'pushed_at'},
                    'chat_messages': {'id', 'channel', 'pid', 'name', 'av', 'text', 'at', 'hidden', 'deleted', 'reports', 'reviewed_at', 'adm', 'raw'},
                    'chat_mutes': {'pid', 'until', 'by_admin', 'reason', 'at'},
                    'chat_prefs': {'pid', 'online', 'updated'},
                    'live_effects': {'id', 'sid', 'kind', 'amount', 'data', 'status', 'at', 'applied_at'},
                }
                for t, names in expected.items():
                    self.assertEqual(columns(db, t), names, t)
            store.close_pool()


class AdminChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db')
        social.ensure(self.store)

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def test_queue_hide_keep_mute(self):
        with self.store.connect() as db:
            before = add_msg(db, 'town', 'a' * 16, 'trước')
            bad = add_msg(db, 'town', 'b' * 16, 'tin xấu', name='Kẻ Xấu', reports=3, hidden=1)
            after = add_msg(db, 'town', 'a' * 16, 'sau')
            for i, reason in enumerate(('spam', 'spam', 'rude')):
                db.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?, 'chat', ?, ?, ?)", (f'{i:016x}', str(bad), reason, time.time()))
        v = live_chat.view(self.store)
        self.assertEqual(v['counts'], dict(pending=1, auto_hidden=1, safety=0, names=0))   # 🛟 safety, names: moderation #13/#14
        item = v['items'][0]
        self.assertEqual((item['id'], item['text'], item['reasons']), (bad, 'tin xấu', dict(spam=2, rude=1)))
        self.assertEqual([m['id'] for m in item['context']], [before, after])
        self.assertEqual([m['id'] for m in v['town']], [after, bad, before])
        out = live_chat.act(self.store, 'op', dict(op='hide', id=bad))
        self.assertEqual((out['item']['hidden'], out['item']['reviewed']), (2, True))
        self.assertEqual(live_chat.view(self.store)['counts']['pending'], 0)
        live_chat.act(self.store, 'op', dict(op='keep', id=bad))
        with self.store.connect() as db:
            self.assertEqual(tuple(db.execute('SELECT hidden, text FROM chat_messages WHERE id=?', (bad,)).fetchone()), (0, 'tin xấu'))
        m = live_chat.act(self.store, 'op', dict(op='mute', pid='b' * 16, hours=24, reason='spam'))
        self.assertAlmostEqual(m['until'], time.time() + 86400, delta=5)
        self.assertEqual([x['pid'] for x in live_chat.view(self.store)['mutes']], ['b' * 16])
        self.assertEqual(live_chat.view(self.store)['mutes'][0]['name'], 'Kẻ Xấu')
        live_chat.act(self.store, 'op', dict(op='unmute', pid='b' * 16))
        self.assertEqual(live_chat.view(self.store)['mutes'], [])
        for bad_op in (dict(op='mute', pid='b' * 16, hours=5), dict(op='hide', id='1'), dict(op='mute', pid='x', hours=1), dict(op='drop')):
            with self.assertRaises(live_chat.ChatAdminError):
                live_chat.act(self.store, 'op', bad_op)

    def test_forget_empties_my_messages_only(self):
        token, _, _ = self.store.session(None)
        pid = social.pid_of(self.store.key(token))
        with self.store.connect() as db:
            mine = add_msg(db, 'town', pid, 'của tôi')
            other = add_msg(db, 'town', 'c' * 16, 'của người khác')
            db.execute("INSERT INTO chat_members(channel, pid, sid, joined) VALUES('g:0000000001', ?, 'x', 0)", (pid,))
        live_chat.forget(self.store, token)
        with self.store.connect() as db:
            self.assertEqual(tuple(db.execute('SELECT text, deleted FROM chat_messages WHERE id=?', (mine,)).fetchone()), ('', 1))
            self.assertEqual(tuple(db.execute('SELECT text, deleted FROM chat_messages WHERE id=?', (other,)).fetchone()), ('của người khác', 0))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_members').fetchone()[0], 0)


class AdminEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = GameServer(('127.0.0.1', 0), Store(Path(cls.temp.name) / 'state.db'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'chat_admin'})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.server.store.close_pool(); cls.temp.cleanup(); cls.env.stop()
        st.clear_cache()

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
        if 'Set-Cookie' in hdrs:
            dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        data = json.loads(raw or b'{}') if hdrs.get('Content-Type', '').startswith('application/json') else raw
        if isinstance(data, dict) and data.get('csrf'):
            dev['csrf'] = data['csrf']
        return res.status, data, hdrs

    def device(self):
        dev = {}
        self.assertEqual(self.req(dev, '/api/bootstrap')[0], 200)
        return dev

    def test_admin_only_and_actions(self):
        self.server.limits.clear()
        player = self.device()
        self.assertEqual(self.req(player, '/api/admin/chat')[0], 403)
        self.assertEqual(self.req(player, '/api/admin/chat', 'POST', dict(op='hide', id=1))[0], 403)
        admin = self.device()
        status, data, _ = self.req(admin, '/api/account/register', 'POST', dict(REG, username='chat_admin'))
        self.assertEqual(status, 200, data)
        with self.server.store.connect() as db:
            mid = add_msg(db, 'town', 'd' * 16, 'tin bị báo', reports=1)
        status, view, _ = self.req(admin, '/api/admin/chat')
        self.assertEqual(status, 200, view)
        self.assertEqual([x['id'] for x in view['items']], [mid])
        status, out, _ = self.req(admin, '/api/admin/chat', 'POST', dict(op='hide', id=mid))
        self.assertEqual((status, out['item']['hidden']), (200, 2))
        status, out, _ = self.req(admin, '/api/admin/chat', 'POST', dict(op='mute', pid='d' * 16, hours=1))
        self.assertEqual(status, 200)
        with self.server.store.connect() as db:
            self.assertEqual(db.execute('SELECT by_admin FROM chat_mutes').fetchone()[0], 'chat_admin')
        self.assertEqual(self.req(admin, '/api/admin/chat', 'POST', dict(op='mute', pid='d' * 16, hours=3))[0], 400)

    def test_socket_only_when_the_game_names_a_live_service(self):
        from server import live_hint
        with patch.dict(os.environ, {'LIVE_URL': ''}):
            self.assertEqual(live_hint(), {})
            self.assertNotIn('live', self.req({}, '/api/bootstrap?lite=1')[1])
        with patch.dict(os.environ, {'LIVE_URL': '/live'}):
            self.assertEqual(self.req({}, '/api/bootstrap?lite=1')[1]['live'], dict(url='/live'))
        for bad in ('javascript:alert(1)', 'http://x/live', '/live"x'):
            with patch.dict(os.environ, {'LIVE_URL': bad}):
                self.assertEqual(live_hint(), {}, bad)

    def test_page_csp_allows_its_own_socket(self):
        status, _, hdrs = self.req({}, '/')
        self.assertEqual(status, 200)
        self.assertIn(f"connect-src 'self' ws://127.0.0.1:{self.port}", hdrs['Content-Security-Policy'])


@pg_only
@needs_ws
class NotifyTests(LiveCase):
    """An admin decision on the game server reaches open screens through PostgreSQL NOTIFY."""

    async def test_hide_and_mute_apply_at_once(self):
        import asyncio
        self.cfg.town_every = 0
        token, sid = self.account('Người Nói')   # only accounts post on Cả phố (1.0.1)
        a = await self.connect(token)
        b = await self.connect(self.guest('Người Nghe')[0])
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='câu cần ẩn', cid='x')
        m = await a.expect('msg', cid='x')
        await b.expect('msg')
        await asyncio.sleep(0.3)    # the LISTEN connection is up
        await asyncio.to_thread(live_chat.act, self.store, 'op', dict(op='hide', id=m['id']))
        d = await b.expect('deleted', timeout=5)
        self.assertEqual((d['id'], d['hidden']), (m['id'], 1))
        j = await (await self.connect(self.guest('Đến Sau')[0])).call('join', 'joined', ch='town')
        self.assertEqual(j['msgs'], [])
        await asyncio.to_thread(live_chat.act, self.store, 'op', dict(op='keep', id=m['id']))
        r = await b.expect('msg', timeout=5, restore=1)
        self.assertEqual(r['id'], m['id'])
        await asyncio.to_thread(live_chat.act, self.store, 'op', dict(op='mute', pid=self.pid(sid), hours=1))
        self.assertGreater((await a.expect('muted', timeout=5))['until'], time.time())
        await a.send(t='send', ch='town', text='còn nói được không', cid='y')
        self.assertEqual((await a.expect('error', ref='y'))['code'], 'muted')


if __name__ == '__main__':
    unittest.main()
