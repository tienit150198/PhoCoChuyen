"""😍 Reactions in chat (press and hold a message: one of ❤️ 😂 😮 😢 👍 🔥 per player per message) and 🔎 the admin
"Tin nhắn" tab (every chat, 200 a page, search, the original of a masked message: admins only, never to players)."""
import http.client
import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from game import admin_stats as st, live_chat, social
from game.storage import Store
from server import GameServer
from tests.live_support import LiveCase

PW = 'matkhau-rat-dai'
TYPED = 'gọi 0912 345 678 nhé'   # the filter masks the phone number
SECRET = '0912 345 678'           # (spaces: never inside a hex pid)


def add(db, ch, pid, text, name='Ai đó', raw=None, hidden=0, deleted=0):
    return db.execute('INSERT INTO chat_messages(channel, pid, name, av, text, at, raw, hidden, deleted) VALUES(?,?,?,?,?,?,?,?,?) RETURNING id',
                      (ch, pid, name, '🌸', text, time.time(), raw, hidden, deleted)).fetchone()[0]


class ReactTests(LiveCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.cfg.town_every = 0
        self.ta, self.sa = self.account('Lan Anh')
        self.tb, self.sb = self.account('Minh Tú')
        self.pa, self.pb = self.pid(self.sa), self.pid(self.sb)

    async def test_set_replace_take_back_on_town(self):
        a, b = await self.connect(self.ta), await self.connect(self.tb)
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='chào cả phố', cid='m')
        m = await a.expect('msg', cid='m')
        await b.expect('msg')
        mid = m['id']
        await b.send(t='react', id=mid, e='❤️')
        for c in (a, b):
            f = await c.expect('reacts', id=mid, by=self.pb)
            self.assertEqual((f['ch'], f['r'], f['e']), ('town', {'❤️': 1}, '❤️'))
        await a.send(t='react', id=mid, e='❤️')
        self.assertEqual((await b.expect('reacts', id=mid, by=self.pa))['r'], {'❤️': 2})
        await b.send(t='react', id=mid, e='😂')            # another one replaces mine
        f = await a.expect('reacts', id=mid, by=self.pb, e='😂')
        self.assertEqual(list(f['r'].items()), [('❤️', 1), ('😂', 1)])   # in the bar's order
        await b.send(t='react', id=mid, e='😂')            # the same again takes it back
        f = await a.expect('reacts', id=mid, by=self.pb, e=None)
        self.assertEqual(f['r'], {'❤️': 1})
        with self.store.connect() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT pid, emoji FROM chat_reacts').fetchall()], [(self.pa, '❤️')])
        # pages carry the counts, and `my` for my own
        late = await self.connect(self.account('Đến Sau')[0])
        j = await late.call('join', 'joined', ch='town')
        self.assertEqual((j['msgs'][0]['r'], j['msgs'][0].get('my')), ({'❤️': 1}, None))
        a2 = await self.connect(self.ta)
        j = await a2.call('join', 'joined', ch='town')
        self.assertEqual((j['msgs'][0]['r'], j['msgs'][0]['my']), ({'❤️': 1}, '❤️'))
        h = await a2.call('history', 'history', ch='town', before=mid + 1)
        self.assertEqual((h['msgs'][0]['r'], h['msgs'][0]['my']), ({'❤️': 1}, '❤️'))
        # not on Cả phố: still hears its own reaction
        await late.send(t='react', id=mid, e='🔥')
        self.assertEqual((await a.expect('reacts', id=mid, by=late.welcome['me']['pid']))['r'], {'❤️': 1, '🔥': 1})
        # bad requests
        for cid, frame in (('e', dict(id=mid, e='🍕')), ('i', dict(id='1', e='❤️')), ('n', dict(id=mid + 99, e='❤️'))):
            await b.send(t='react', cid=cid, **frame)
            self.assertEqual((await b.expect('error', ref=cid))['code'], 'bad' if cid != 'n' else 'gone')

    async def test_guests_muted_deleted_hidden(self):
        with self.store.connect() as db:
            hidden = add(db, 'town', 'c' * 16, 'đã ẩn', hidden=2)
            db.execute('INSERT INTO chat_mutes(pid, until, by_admin, reason, at) VALUES(?, ?, ?, ?, ?)',
                       (self.pb, time.time() + 3600, 'admin', '', time.time()))
        a = await self.connect(self.ta)
        await a.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='lỡ tay', cid='m')
        mid = (await a.expect('msg', cid='m'))['id']
        g = await self.connect(self.guest('Khách')[0])
        await g.send(t='react', id=mid, e='❤️', cid='g')
        self.assertEqual((await g.expect('error', ref='g'))['code'], 'account')
        b = await self.connect(self.tb)
        await b.send(t='react', id=mid, e='❤️', cid='b')
        self.assertEqual((await b.expect('error', ref='b'))['code'], 'muted')
        await a.send(t='react', id=hidden, e='❤️', cid='h')
        self.assertEqual((await a.expect('error', ref='h'))['code'], 'gone')
        await a.send(t='react', id=mid, e='👍')
        await a.expect('reacts', id=mid)
        await a.send(t='del', id=mid)
        await a.expect('deleted', id=mid)
        await a.send(t='react', id=mid, e='❤️', cid='d')
        self.assertEqual((await a.expect('error', ref='d'))['code'], 'gone')
        j = await (await self.connect(self.account('Sau')[0])).call('join', 'joined', ch='town')
        self.assertEqual((j['msgs'][0]['del'], 'r' in j['msgs'][0]), (1, False))   # deleted: its reactions are not shown
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_reacts').fetchone()[0], 1)   # kept, never shown

    async def test_dms_and_groups_members_only(self):
        self.befriend(self.sa, self.sb)
        a, b = await self.connect(self.ta), await self.connect(self.tb)
        await a.send(t='send', to=self.pb, text='chào Tú', cid='1')
        m = await a.expect('msg', cid='1')
        await b.expect('msg')
        await b.send(t='react', id=m['id'], e='👍')
        f = await a.expect('reacts', id=m['id'])
        self.assertEqual((f['ch'], f['r'], f['by'], f['e']), (m['ch'], {'👍': 1}, self.pb, '👍'))
        stranger = await self.connect(self.account('Người Lạ')[0])
        await stranger.send(t='react', id=m['id'], e='❤️', cid='x')
        self.assertEqual((await stranger.expect('error', ref='x'))['code'], 'no_chat')
        await stranger.nothing('reacts')
        # resume after a reconnect: missed messages carry the counts
        await b.close()
        await a.send(t='send', ch=m['ch'], text='còn đó không', cid='2')
        m2 = await a.expect('msg', cid='2')
        await a.send(t='react', id=m2['id'], e='😮')
        await a.expect('reacts', id=m2['id'])
        b = await self.connect(self.tb, resume={m['ch']: m['id']})
        missed = await b.expect('missed')
        self.assertEqual((missed['msgs'][0]['r'], missed['msgs'][0].get('my')), ({'😮': 1}, None))
        h = await b.call('history', 'history', ch=m['ch'])
        self.assertEqual([(x.get('r'), x.get('my')) for x in h['msgs']], [({'👍': 1}, '👍'), ({'😮': 1}, None)])
        # a group
        await a.send(t='group_new', title='Hội bàn bên', pids=[self.pb], cid='g')
        ch = (await a.expect('chan', open=True))['chan']['id']
        await b.expect('chan')
        await b.send(t='send', ch=ch, text='chào nhóm', cid='gm')
        gm = await b.expect('msg', cid='gm')
        await a.expect('msg', ch=ch)
        await a.send(t='react', id=gm['id'], e='🔥')
        self.assertEqual((await b.expect('reacts', id=gm['id']))['r'], {'🔥': 1})
        await stranger.send(t='react', id=gm['id'], e='🔥', cid='gx')
        self.assertEqual((await stranger.expect('error', ref='gx'))['code'], 'no_chat')

    async def test_pruned_and_forgotten_take_their_reactions(self):
        with self.store.connect() as db:
            ids = [add(db, 'town', 'a' * 16, f'tin {i}') for i in range(6)]
            for i in ids:
                db.execute('INSERT INTO chat_reacts(msg, pid, emoji, at) VALUES(?, ?, ?, 0)', (i, 'b' * 16, '❤️'))
        counts = await self.app.chat.react_counts(ids)
        self.assertEqual(counts[ids[0]], {'❤️': 1})
        gone = await self.app.chat.prune_town(keep=2)
        self.assertEqual(gone, 4)
        with self.store.connect() as db:
            self.assertEqual(sorted(r[0] for r in db.execute('SELECT msg FROM chat_reacts').fetchall()), ids[-2:])
        self.assertIsNone(self.app.chat.reacts.get(ids[0]))
        token, sid = self.guest('Xóa Dữ Liệu')
        with self.store.connect() as db:
            db.execute('INSERT INTO chat_reacts(msg, pid, emoji, at) VALUES(?, ?, ?, 0)', (ids[-1], self.pid(sid), '😂'))
        live_chat.forget(self.store, token)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_reacts WHERE pid=?', (self.pid(sid),)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_reacts').fetchone()[0], 2)

    async def test_original_text_never_reaches_players(self):
        self.befriend(self.sa, self.sb)
        a, b = await self.connect(self.ta), await self.connect(self.tb)
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        seen = []
        await a.send(t='send', ch='town', text=TYPED, cid='t')
        m = await a.expect('msg', cid='t')
        seen += [m, await b.expect('msg')]
        await a.send(t='send', ch='town', text='chào bình thường', cid='n')
        plain = await a.expect('msg', cid='n')
        await a.send(t='send', to=self.pb, text=TYPED, cid='d')
        dm = await a.expect('msg', cid='d')
        seen += [dm, await b.expect('msg', ch=dm['ch'])]
        with self.store.connect() as db:
            raw = dict(db.execute('SELECT id, raw FROM chat_messages').fetchall())
        self.assertEqual((raw[m['id']], raw[plain['id']], raw[dm['id']]), (TYPED, None, TYPED))   # kept only when masked
        await b.send(t='react', id=m['id'], e='❤️')
        seen.append(await a.expect('reacts', id=m['id']))
        c = await self.connect(self.tb, resume={dm['ch']: dm['id'] - 1})
        seen += [c.welcome, await c.expect('missed'), await c.call('join', 'joined', ch='town'),
                 await c.call('history', 'history', ch='town'), await c.call('history', 'history', ch=dm['ch']),
                 await c.call('sync', 'state')]
        for f in seen + a.frames + b.frames + c.frames:
            s = json.dumps(f, ensure_ascii=False)
            self.assertNotIn(SECRET, s, f.get('t'))
            self.assertNotIn('"raw"', s, f.get('t'))
        # the admin screen has it
        found = live_chat.search(self.store, dict(q='0912'))
        self.assertEqual([(x['id'], x['raw']) for x in found['items']], [(dm['id'], TYPED), (m['id'], TYPED)])
        self.assertEqual({x['id']: x.get('raw') for x in live_chat.view(self.store)['town']}, {m['id']: TYPED, plain['id']: None})


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.store = Store(Path(self.tmp.name) / 'g.sqlite3')
        social.ensure(self.store)

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def test_filters_and_pages(self):
        a, b = 'a' * 16, 'b' * 16
        dm, g = f'dm:{a}:{b}', 'g:0123456789'
        with self.store.connect() as db:
            db.execute("INSERT INTO chat_channels(id, kind, title, created) VALUES(?, 'group', 'Hội bàn bên', 0)", (g,))
            town = [add(db, 'town', a if i % 2 else b, f'phố {i}', name='Lan' if i % 2 else 'Tú') for i in range(250)]
            d = add(db, dm, a, 'gọi •••', name='Lan', raw='gọi 0912 345 678')
            gm = add(db, g, b, '100% thật_ra', name='Tú')
            gone = add(db, 'town', a, '', name='Lan', deleted=1)
        p1 = live_chat.search(self.store, {})
        self.assertEqual((len(p1['items']), p1['page'], p1['items'][0]['id']), (200, 200, gone))
        self.assertIsNotNone(p1['next'])
        p2 = live_chat.search(self.store, dict(before=str(p1['next'])))
        self.assertEqual(len(p2['items']), 53)
        self.assertIsNone(p2['next'])
        self.assertEqual({x['id'] for x in p1['items'] + p2['items']}, set(town) | {d, gm, gone})
        k = lambda **q: [x['id'] for x in live_chat.search(self.store, q)['items']]
        self.assertEqual(k(kind='dm'), [d])
        self.assertEqual(k(kind='group'), [gm])
        self.assertEqual(live_chat.search(self.store, dict(kind='group'))['items'][0]['title'], 'Hội bàn bên')
        self.assertEqual(len(k(kind='town')), 200)
        self.assertEqual(k(ch=dm), [d])
        self.assertEqual(k(q='0912'), [d])                           # the original only
        self.assertEqual(k(q='gọi'), [d])
        self.assertEqual(k(q='100%'), [gm])                         # LIKE wildcards are literal
        self.assertEqual(k(q='%'), [gm])
        self.assertEqual(k(q='thật_r'), [gm])
        self.assertEqual(k(q='h_t'), [])
        self.assertEqual(k(q='phố 249'), [town[-1]])
        mine = live_chat.search(self.store, dict(q=b))               # a pid in the box: that player
        self.assertEqual((mine['filters']['pid'], mine['filters']['q'], mine['player']['name']), (b, '', 'Tú'))
        self.assertEqual(set(x['pid'] for x in mine['items']), {b})
        self.assertEqual(k(pid=a, kind='dm'), [d])
        self.assertEqual(live_chat.search(self.store, dict(q='0912'))['items'][0]['raw'], 'gọi 0912 345 678')
        with self.assertRaises(live_chat.ChatAdminError):
            live_chat.search(self.store, dict(pid='nope'))
        # words look at a window of ids, then move it
        with patch.object(live_chat, 'WINDOW', 100):
            w = live_chat.search(self.store, dict(q='phố'))
            self.assertEqual((len(w['items']), w['scanned']), (97, gone - 100))
            self.assertEqual(w['next'], gone - 99)
            w2 = live_chat.search(self.store, dict(q='phố', before=str(w['next'])))
            self.assertEqual(len(w2['items']), 100)
            self.assertTrue(all(x['id'] < w['next'] for x in w2['items']))

    def test_old_sqlite_file_gets_raw(self):
        path = Path(self.tmp.name) / 'old.sqlite3'
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, channel TEXT, pid TEXT, name TEXT, av TEXT, text TEXT, at REAL)')
        db.execute("INSERT INTO chat_messages(channel, pid, name, av, text, at) VALUES('town', 'a', 'A', '', 'cũ', 0)")
        live_chat.migrate(db)
        cols = [r[1] for r in db.execute('PRAGMA table_info(chat_messages)').fetchall()]
        self.assertEqual(cols[-2:], ['adm', 'raw'])
        self.assertEqual(db.execute('SELECT text, adm, raw FROM chat_messages').fetchone(), ('cũ', 0, None))
        db.close()


class SearchEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
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
        return res.status, data

    def device(self):
        dev = {}
        self.assertEqual(self.req(dev, '/api/bootstrap')[0], 200)
        return dev

    def test_admins_only(self):
        self.server.limits.clear()
        with self.server.store.connect() as db:
            mid = add(db, 'town', 'd' * 16, 'gọi •••', raw=TYPED)
        player = self.device()
        status, data = self.req(player, '/api/admin/chat/messages?q=0912')
        self.assertEqual(status, 403)
        self.assertNotIn(SECRET, json.dumps(data, ensure_ascii=False))
        self.assertIn(self.req({}, '/api/admin/chat/messages')[0], (401, 403))   # no session at all
        admin = self.device()
        status, data = self.req(admin, '/api/account/register', 'POST', dict(password=PW, confirm=PW, display='Quản Trị', username='chat_admin'))
        self.assertEqual(status, 200, data)
        status, data = self.req(admin, '/api/admin/chat/messages?q=0912')
        self.assertEqual(status, 200, data)
        self.assertEqual([(x['id'], x['text'], x['raw']) for x in data['items']], [(mid, 'gọi •••', TYPED)])
        status, data = self.req(admin, '/api/admin/chat/messages?pid=xyz')
        self.assertEqual(status, 400, data)


if __name__ == '__main__':
    unittest.main()
