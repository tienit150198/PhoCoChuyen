"""Current character names reach connected friends without changing login usernames."""
import asyncio
from tests.live_support import LiveCase
from tests.test_live_home import HomeCase


class PlayerNameTests(LiveCase):
    async def people(self):
        self.cfg.town_every = 0
        ta, sa = self.account('Tên Cũ')
        tb, sb = self.account('Bạn Thân')
        self.befriend(sa, sb)
        return ta, sa, await self.connect(ta), tb, sb, await self.connect(tb)

    async def post(self, c, text, **fields):
        await c.send(t='send', cid=text, text=text, **fields)
        return await c.expect('msg', cid=text)

    async def notify_name(self, sid, name):
        with self.store.connect() as db:
            db.execute('UPDATE accounts SET display=? WHERE sid=?', (name, sid))
        await self.app.chat.on_notify(dict(op='name', sid=sid))

    async def test_rename_updates_online_friend_cache_and_same_socket_posts(self):
        ta, sa, a, tb, sb, b = await self.people()
        with self.store.connect() as db:
            username = db.execute('SELECT username FROM accounts WHERE sid=?', (sa,)).fetchone()[0]
        await self.notify_name(sa, 'Tên Mới')
        event = await b.expect('renamed')
        self.assertEqual(event, dict(t='renamed', pid=self.pid(sa), name='Tên Mới'))
        self.assertEqual((await a.expect('renamed'))['name'], 'Tên Mới')
        self.assertEqual(self.app.hub.players[self.pid(sb)].friends[self.pid(sa)]['name'], 'Tên Mới')
        self.assertEqual((await self.post(a, 'xin chào', to=self.pid(sb)))['name'], 'Tên Mới')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT username FROM accounts WHERE sid=?', (sa,)).fetchone()[0], username)

    async def test_old_history_quote_inbox_pin_and_members_use_current_name(self):
        ta, sa, a, tb, sb, b = await self.people()
        original = await self.post(a, 'old dm text', to=self.pid(sb))
        quote = await self.post(b, 'quote old dm', ch=original['ch'], reply_to=original['id'])
        group = (await a.call('group_new', 'chan', title='Nhóm', pids=[self.pid(sb)]))['chan']['id']
        await self.post(a, 'group old text', ch=group)
        await a.call('join', 'joined', ch='town')
        town = await self.post(a, 'town old text', ch='town')
        self.cfg.admins = frozenset({self.app.hub.players[self.pid(sa)].username})
        await a.call('pin', 'pinned', id=town['id'])
        await self.notify_name(sa, 'Tên Hiện Tại')
        if hasattr(self.app.chat, 'names'):
            self.app.chat.names.clear()  # simulate cold caches after process restart
        page = await b.call('history', 'history', ch=original['ch'])
        self.assertEqual(page['msgs'][0]['name'], 'Tên Hiện Tại')
        self.assertEqual(page['msgs'][1]['reply']['name'], 'Tên Hiện Tại')
        state = await b.call('sync', 'state')
        dm = next(c for c in state['chans'] if c['id'] == original['ch'])
        self.assertEqual(dm['peer']['name'], 'Tên Hiện Tại')
        self.assertEqual(dm['last']['reply']['name'], 'Tên Hiện Tại')
        last = next(c['last'] for c in state['chans'] if c['id'] == group)
        self.assertEqual(last['name'], 'Tên Hiện Tại')
        joined = await b.call('join', 'joined', ch='town')
        self.assertEqual(joined['msgs'][-1]['name'], 'Tên Hiện Tại')
        self.assertEqual(joined['pin']['name'], 'Tên Hiện Tại')
        members = await b.call('members', 'members', ch=group)
        self.assertEqual(next(m['name'] for m in members['members'] if m['pid'] == self.pid(sa)), 'Tên Hiện Tại')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT name FROM chat_messages WHERE id=?', (original['id'],)).fetchone()[0], 'Tên Cũ')

    async def test_rename_event_scoped_and_blocked_both_directions(self):
        ta, sa, a, tb, sb, b = await self.people()
        tc, sc = self.account('Người Trong Nhóm')
        self.befriend(sa, sc)
        c = await self.connect(tc)
        await a.call('group_new', 'chan', title='Nhóm', pids=[self.pid(sb), self.pid(sc)])
        idle = await self.connect(self.account('Ngoài Cuộc')[0])
        watcher = await self.connect(self.account('Đọc Phố')[0])
        await watcher.call('join', 'joined', ch='town')
        await b.call('block', 'blocked', pid=self.pid(sa))
        await self.notify_name(sa, 'Tên Công Khai')
        self.assertEqual((await c.expect('renamed'))['name'], 'Tên Công Khai')
        self.assertEqual((await watcher.expect('renamed'))['name'], 'Tên Công Khai')
        await b.nothing('renamed')
        await idle.nothing('renamed')
        await self.notify_name(sb, 'Bạn Bị Chặn')
        await a.nothing('renamed', pid=self.pid(sb))

    async def test_settings_command_pushes_rename_without_reconnect(self):
        ta, sa, a, tb, sb, b = await self.people()
        _, revision, _ = self.store.read(ta)
        self.store.command(ta, 'rename-live-player', revision, None, 'settings', {'name': 'Tên Từ Cài Đặt'})
        self.assertEqual((await b.expect('renamed'))['name'], 'Tên Từ Cài Đặt')
        self.assertEqual((await self.post(a, 'post after settings', to=self.pid(sb)))['name'], 'Tên Từ Cài Đặt')

    async def test_listener_reconcile_recovers_missed_name_notification(self):
        ta, sa, a, tb, sb, b = await self.people()
        await self.post(a, 'prime cached name', to=self.pid(sb))
        with self.store.connect() as db:
            db.execute('UPDATE accounts SET display=? WHERE sid=?', ('Tên Khi Mất Kết Nối', sa))
        await self.app.chat.reconcile()
        self.assertEqual((await b.expect('renamed'))['name'], 'Tên Khi Mất Kết Nối')
        self.assertEqual((await self.post(a, 'post after recovery', to=self.pid(sb)))['name'], 'Tên Khi Mất Kết Nối')

    async def test_delayed_name_lookup_cannot_overwrite_newer_rename(self):
        from unittest.mock import patch
        ta, sa, a, tb, sb, b = await self.people()
        original = await self.post(a, 'name race source', to=self.pid(sb))
        await self.post(b, 'name race reply', ch=original['ch'], reply_to=original['id'])
        self.app.chat.names.clear()
        entered, release = asyncio.Event(), asyncio.Event()
        fetch = self.app.db.fetch

        async def delayed(sql, args=()):
            rows = await fetch(sql, args)
            if 'SELECT sid, display FROM accounts' in sql:
                entered.set()
                await release.wait()
            return rows

        with patch.object(self.app.db, 'fetch', side_effect=delayed):
            await b.send(t='history', ch=original['ch'])
            try:
                await asyncio.wait_for(entered.wait(), 3)
                await self.notify_name(sa, 'Tên Mới Nhất')
                await b.expect('renamed', pid=self.pid(sa))
            finally:
                release.set()
            page = await b.expect('history')
        self.assertEqual(page['msgs'][0]['name'], 'Tên Mới Nhất')
        self.assertEqual(page['msgs'][1]['reply'].get('name'), 'Tên Mới Nhất')
        self.assertEqual(self.app.chat.names.get(self.pid(sa)), 'Tên Mới Nhất')

    async def test_cold_offline_names_use_profile_index_and_cache_unknown_pids(self):
        from unittest.mock import patch
        from live.player_names import names_of
        token, sid = self.account('Tên Ngoại Tuyến')
        pid, missing = self.pid(sid), '0' * 16
        with self.store.connect() as db:
            db.execute('INSERT INTO profiles(pid,sid,created,updated,seen) VALUES(?,?,0,0,0)', (pid, sid))
        with patch.object(self.app.db, 'fetch', wraps=self.app.db.fetch) as fetch:
            self.assertEqual(await names_of(self.app.chat, [pid, missing]), {pid: 'Tên Ngoại Tuyến', missing: ''})
            self.assertEqual(await names_of(self.app.chat, [pid, missing]), {pid: 'Tên Ngoại Tuyến', missing: ''})
        self.assertEqual(fetch.await_count, 1)
        self.assertIn('WHERE p.pid IN', fetch.call_args.args[0])


class HomeNameTests(HomeCase):
    async def test_new_home_entrant_sees_renamed_resident(self):
        owner = await self.join()
        with self.store.connect() as db:
            db.execute('UPDATE accounts SET display=? WHERE sid=?', ('Chủ Nhà Mới', self.sa))
        await self.app.chat.on_notify(dict(op='name', sid=self.sa))
        await owner.expect('renamed', pid=self.pid(self.sa))
        guest = await self.join(self.tb)
        self.assertEqual(guest.room['people'][0]['name'], 'Chủ Nhà Mới')
