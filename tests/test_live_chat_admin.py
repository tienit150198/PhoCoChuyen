"""📌 Admins on Cả phố (owner, 01/10): an account listed in ADMIN_USERS posts freely (no slow mode, no "new player"
wait, no mute, no duplicate check, links and numbers kept, 500 characters / 6 lines) and pins one message for
everyone. The pin is durable (chat_pins), goes away with its message, survives pruning, and a pin written from the
server (scripts/chat_pin.py, e.g. the operator's pid 'admin' announcement) reaches players within the 30 s poll.
Plus the schema on both backends (chat_messages.adm, chat_pins, SCHEMA_VERSION 10) and the SQLite upgrade."""
import io
import secrets
import sqlite3
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from game import live_chat, pg_schema
from game.storage import Store
from tests.live_support import LiveCase
from tests.pg_support import columns, on_pg, sqlite_only

ANN = '📢 Ban quản lý Phố'


class ConfigTests(unittest.TestCase):
    def test_admin_users_like_the_game_server(self):
        from live.config import admin_users
        self.assertEqual(admin_users(' Boss , mod_2,, '), frozenset({'boss', 'mod_2'}))
        self.assertEqual(admin_users(''), frozenset())


class AdminCase(LiveCase):
    cfg_extra = dict(admins=frozenset({'boss'}))

    def admin(self, display='Ban Quản Lý', username='boss', old=True):
        """The admin account (username in ADMIN_USERS) signed in on this device. Returns (token, sid)."""
        token, sid = self.guest(name=None, old=old)
        login = secrets.token_hex(32)
        with self.store.connect() as db:
            db.execute('INSERT INTO accounts(username, display, pw, sid) VALUES(?, ?, ?, ?)', (username, display, 'x', sid))
            db.execute('INSERT INTO logins(token, sid, csrf) VALUES(?, ?, ?)', (self.store.digest(login), sid, 'c'))
        return login, sid

    def add(self, text, pid='a' * 16, name='Ai đó', ch='town', **cols):
        with self.store.connect() as db:
            return db.execute('INSERT INTO chat_messages(channel, pid, name, av, text, at, hidden, deleted) VALUES(?,?,?,?,?,?,?,?) RETURNING id',
                              (ch, pid, name, '📢' if pid == 'admin' else '🌸', text, time.time(), cols.get('hidden', 0),
                               cols.get('deleted', 0))).fetchone()[0]

    def pin_row(self):
        with self.store.connect() as db:
            r = db.execute("SELECT msg, by_pid FROM chat_pins WHERE channel='town'").fetchone()
        return (r[0], r[1]) if r else None

    async def poll(self):
        """The 30 s poll of the pin row, now."""
        self.app.chat._pin_at = 0
        await self.app.chat.tick(time.time())


class AdminPostTests(AdminCase):
    async def test_admin_posts_freely_players_unchanged(self):
        ta, sa = self.admin(old=False)   # a new session: players would wait 10 minutes
        with self.store.connect() as db:   # and muted
            db.execute('INSERT INTO chat_mutes(pid, until, by_admin, reason, at) VALUES(?, ?, ?, ?, ?)',
                       (self.pid(sa), time.time() + 3600, 'op', '', time.time()))
        a = await self.connect(ta)
        b = await self.connect(self.account('Gió')[0])
        me = a.welcome['me']
        self.assertEqual((me['adm'], me['town'], me['wait'], me['muted']), (1, 'ok', 0, 0))
        self.assertEqual(a.welcome['limits']['admin_len'], 500)
        self.assertNotIn('adm', b.welcome['me'])
        ja = await a.call('join', 'joined', ch='town')
        self.assertEqual((ja['why'], ja['wait'], ja['pin']), ('ok', 0, None))
        await b.call('join', 'joined', ch='town')
        text = 'Sự kiện mới: https://phocochuyen.io.vn/su-kien?a=1&b=2 — hotline 0912 345 678, zalo minh123'
        await a.send(t='send', ch='town', text=text, cid='a1')
        m1 = await a.expect('msg', cid='a1')
        self.assertEqual((m1['text'], m1['adm'], m1['wait']), (text, 1, 0))
        got = await b.expect('msg')
        self.assertEqual((got['text'], got['adm'], got['name']), (text, 1, 'Ban Quản Lý'))
        await a.send(t='send', ch='town', text=text, cid='a2')            # again at once, the same words: fine
        self.assertEqual((await a.expect('msg', cid='a2'))['adm'], 1)
        long = '\n'.join(['x' * 80] * 6)                                    # 6 lines, 485 characters
        await a.send(t='send', ch='town', text=long, cid='a3')
        self.assertEqual((await a.expect('msg', cid='a3'))['text'], long)
        await a.send(t='send', ch='town', text='y' * 501, cid='a4')
        self.assertEqual((await a.expect('error', ref='a4'))['code'], 'text')
        with self.store.connect() as db:
            rows = db.execute('SELECT text, adm FROM chat_messages ORDER BY id').fetchall()
        self.assertEqual([(r[0], r[1]) for r in rows], [(text, 1), (text, 1), (long, 1)])
        # an ordinary player: masked, slow mode, no adm
        await b.send(t='send', ch='town', text=text, cid='b1')
        mb = await b.expect('msg', cid='b1')
        self.assertNotIn('adm', mb)
        self.assertNotIn('https://', mb['text'])
        self.assertNotIn('0912', mb['text'])
        await b.send(t='send', ch='town', text='nữa', cid='b2')
        self.assertEqual((await b.expect('error', ref='b2'))['code'], 'slow')
        # nobody reports an admin message; loaded back from the database, it is still an admin's
        await b.send(t='report', id=m1['id'], reason='spam', cid='r')
        self.assertEqual((await b.expect('error', ref='r'))['code'], 'bad')
        late = await self.connect(self.account('Muộn')[0])
        j = await late.call('join', 'joined', ch='town')
        self.assertEqual([m.get('adm') for m in j['msgs']], [1, 1, 1, None])
        await self.app.stop()
        from live.app import App
        self.app = App(self.cfg)
        await self.app.start()
        self.port = self.app.port()
        c = await self.connect(self.account('Sau')[0])
        h = await c.call('history', 'history', ch='town')
        self.assertEqual([m.get('adm') for m in h['msgs']], [1, 1, 1, None])

    async def test_operator_rows_and_case_of_usernames(self):
        mid = self.add('Chào cả phố!', pid='admin', name=ANN)
        c = await self.connect(self.account('Gió')[0])
        h = await c.call('history', 'history', ch='town')   # written behind the service's back: from the database
        self.assertEqual((h['msgs'][0]['id'], h['msgs'][0]['adm']), (mid, 1))
        await c.send(t='report', id=mid, reason='spam', cid='r')
        self.assertEqual((await c.expect('error', ref='r'))['code'], 'bad')
        # only the usernames listed in ADMIN_USERS
        t2, _ = self.admin(display='Mod', username='other')
        self.assertNotIn('adm', (await self.connect(t2)).welcome['me'])


class PinTests(AdminCase):
    async def test_pin_unpin_and_who_may(self):
        ta, sa = self.admin()
        a = await self.connect(ta)
        tb, sb = self.account('Gió')
        b = await self.connect(tb)
        idle = await self.connect(self.account('Lá')[0])
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        self.cfg.town_every = 0
        await b.send(t='send', ch='town', text='quán mới mở ở đầu ngõ', cid='m')
        m = await b.expect('msg', cid='m')
        await a.expect('msg')
        # players cannot pin or unpin
        for t in ('pin', 'unpin'):
            await b.send(t=t, id=m['id'])
            self.assertEqual((await b.expect('error', ref=t))['code'], 'admin')
        self.assertIsNone(self.pin_row())
        # the admin pins a player's message: everyone on Cả phố sees it at once
        await a.send(t='pin', id=m['id'])
        for c in (a, b):
            f = await c.expect('pinned')
            self.assertEqual((f['ch'], f['pin']['id'], f['pin']['text'], f['pin']['name']), ('town', m['id'], 'quán mới mở ở đầu ngõ', 'Gió'))
            self.assertNotIn('t', f['pin'])
        await idle.nothing('pinned')
        self.assertEqual(self.pin_row(), (m['id'], self.pid(sa)))
        j = await (await self.connect(self.account('Muộn')[0])).call('join', 'joined', ch='town')
        self.assertEqual(j['pin']['id'], m['id'])
        # one pin at a time: the admin's own message replaces it
        await a.send(t='send', ch='town', text='Thông báo: bảo trì 23h https://phocochuyen.io.vn', cid='x')
        own = await a.expect('msg', cid='x')
        await a.send(t='pin', id=own['id'])
        f = await b.expect('pinned')
        self.assertEqual((f['pin']['id'], f['pin']['adm']), (own['id'], 1))
        await a.expect('pinned')
        self.assertEqual(self.pin_row()[0], own['id'])
        # bad targets
        dm = self.add('riêng', ch='dm:' + 'a' * 16 + ':' + 'b' * 16)
        hidden = self.add('ẩn', hidden=2)
        for bad in (dm, hidden, 10 ** 9):
            await a.send(t='pin', id=bad, cid=f'p{bad}')
            self.assertEqual((await a.expect('error', ref=f'p{bad}'))['code'], 'gone')
        await a.send(t='pin', id='1', cid='s')
        self.assertEqual((await a.expect('error', ref='s'))['code'], 'bad')
        # unpin
        await a.send(t='unpin')
        for c in (a, b):
            await c.expect('pinned', pin=None)
        self.assertIsNone(self.pin_row())
        self.assertIsNone((await b.call('join', 'joined', ch='town'))['pin'])

    async def test_pin_goes_with_its_message(self):
        ta, _ = self.admin()
        a = await self.connect(ta)
        tb, sb = self.account('Gió')
        b = await self.connect(tb)
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        await b.send(t='send', ch='town', text='tin sẽ thu hồi', cid='m')
        m = await b.expect('msg', cid='m')
        await a.send(t='pin', id=m['id'])
        for c in (a, b):
            await c.expect('pinned', ch='town')
        await b.send(t='del', id=m['id'])           # its author takes it back
        await a.expect('pinned', pin=None)
        self.assertIsNone(self.pin_row())
        # an admin hides it (game server, SQLite: no NOTIFY): gone within the poll
        mid = self.add('tin bị ẩn')
        await a.send(t='pin', id=mid)
        await a.expect('pinned')
        live_chat.act(self.store, 'op', dict(op='hide', id=mid))
        self.assertIsNone(self.pin_row())
        await self.poll()
        await b.expect('pinned', pin=None)
        # a hidden message under the pin, written by hand: the poll removes the pin row too
        mid = self.add('tin thứ ba')
        await a.send(t='pin', id=mid)
        await a.expect('pinned')
        with self.store.connect() as db:
            db.execute('UPDATE chat_messages SET hidden=1 WHERE id=?', (mid,))
        await self.poll()
        await b.expect('pinned', pin=None)
        self.assertIsNone(self.pin_row())

    async def test_blocked_author_pin_hidden(self):
        ta, _ = self.admin()
        a = await self.connect(ta)
        tb, sb = self.account('Gió')
        tc, _ = self.account('Lá')
        b, c = await self.connect(tb), await self.connect(tc)
        await b.call('join', 'joined', ch='town')
        await b.send(t='send', ch='town', text='xin chào', cid='m')
        m = await b.expect('msg', cid='m')
        await c.call('block', 'blocked', pid=self.pid(sb))
        await a.send(t='pin', id=m['id'])
        await a.expect('pinned')
        self.assertIsNone((await c.call('join', 'joined', ch='town'))['pin'])
        self.assertEqual((await b.call('join', 'joined', ch='town'))['pin']['id'], m['id'])

    async def test_pruning_keeps_the_pinned_message(self):
        first = self.add('cũ nhất, được ghim', pid='admin', name=ANN)
        for i in range(20):
            self.add(f'tin {i}')
        with self.store.connect() as db:
            db.execute("INSERT INTO chat_pins(channel, msg, by_pid, at) VALUES('town', ?, 'admin', ?)", (first, time.time()))
        gone = await self.app.chat.prune_town(keep=5)
        self.assertEqual(gone, 15)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_messages WHERE id=?', (first,)).fetchone()[0], 1)
        self.assertEqual(self.pin_row(), (first, 'admin'))

    @sqlite_only
    async def test_pin_from_the_server_script(self):
        from scripts import chat_pin
        mid = self.add('Phố Có Chuyện chào mọi người!\nXem thêm: https://phocochuyen.io.vn/tin-tuc.', pid='admin', name=ANN)
        c = await self.connect(self.account('Gió')[0])
        self.assertIsNone((await c.call('join', 'joined', ch='town'))['pin'])
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(chat_pin.main(['--db', self.store.path, '--msg', str(mid), '--dry-run']), 0)
        self.assertIn('Thử (không ghi)', out.getvalue())
        self.assertIsNone(self.pin_row())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(chat_pin.main(['--db', self.store.path, '--msg', str(mid)]), 0)
        self.assertEqual(self.pin_row(), (mid, 'admin'))
        await c.nothing('pinned', wait=0.2)
        await self.poll()                          # the service reads the pin row every 30 s
        f = await c.expect('pinned')
        self.assertEqual((f['pin']['id'], f['pin']['adm'], f['pin']['name']), (mid, 1, ANN))
        await self.poll()                          # no change, no frame
        await c.nothing('pinned', wait=0.2)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(chat_pin.main(['--db', self.store.path, '--show']), 0)
        self.assertIn(f'#{mid}', out.getvalue())
        # a restart reads it at start
        await self.app.stop()
        from live.app import App
        self.app = App(self.cfg)
        await self.app.start()
        self.port = self.app.port()
        c2 = await self.connect(self.account('Sau')[0])
        self.assertEqual((await c2.call('join', 'joined', ch='town'))['pin']['id'], mid)
        # refused: a hidden message, a missing one
        hid = self.add('ẩn', hidden=2)
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            self.assertEqual(chat_pin.main(['--db', self.store.path, '--msg', str(hid)]), 2)
            self.assertEqual(chat_pin.main(['--db', self.store.path, '--msg', '999999']), 2)
        self.assertEqual(self.pin_row(), (mid, 'admin'))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(chat_pin.main(['--db', self.store.path, '--unpin']), 0)
        self.assertIsNone(self.pin_row())
        await self.poll()
        await c2.expect('pinned', pin=None)


class SchemaTests(unittest.TestCase):
    def test_both_backends(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 10)   # 10: chat_messages.adm, chat_pins
        self.assertIn('CREATE TABLE IF NOT EXISTS chat_pins (', pg_schema.TABLES_DDL)
        self.assertIn('ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS adm bigint NOT NULL DEFAULT 0;', pg_schema.TABLES_DDL)
        self.assertEqual(pg_schema.TABLE['chat_pins']['key'], ('channel',))
        self.assertEqual([c for c, _ in pg_schema.TABLE['chat_messages']['columns']][-2:], ['adm', 'raw'])
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / 'g.sqlite3')
            with store.connect() as db:
                for t in ('chat_messages', 'chat_pins'):
                    self.assertEqual(columns(db, t), {c for c, _ in pg_schema.TABLE[t]['columns']}, t)
            store.close_pool()

    @unittest.skipIf(on_pg(), 'SQLite upgrade')
    def test_older_sqlite_file_gains_adm(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'g.sqlite3'
            db = sqlite3.connect(path)
            db.executescript("""CREATE TABLE chat_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT NOT NULL, pid TEXT NOT NULL, name TEXT NOT NULL DEFAULT '',
              av TEXT NOT NULL DEFAULT '', text TEXT NOT NULL, at REAL NOT NULL, hidden INTEGER NOT NULL DEFAULT 0,
              deleted INTEGER NOT NULL DEFAULT 0, reports INTEGER NOT NULL DEFAULT 0, reviewed_at REAL);
              INSERT INTO chat_messages(channel, pid, name, text, at) VALUES('town', 'a', 'Ai', 'cũ', 1);""")
            db.commit()
            db.close()
            store = Store(path)
            with store.connect() as db:
                self.assertEqual(tuple(db.execute('SELECT text, adm FROM chat_messages').fetchone()), ('cũ', 0))
                self.assertIn('chat_pins', {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")})
            self.assertEqual(live_chat.view(store)['town'][0]['adm'], 0)
            store.close_pool()
            Store(path).close_pool()   # a second start: nothing to add


if __name__ == '__main__':
    unittest.main()
