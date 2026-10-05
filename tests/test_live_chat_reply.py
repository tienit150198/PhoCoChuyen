"""Reply quotes use current, per-reader-visible server text, over real PostgreSQL/sockets."""
import asyncio
from tests.live_support import LiveCase


class ReplyTests(LiveCase):
    async def test_schema_upgrade_preserves_existing_message(self):
        from game import pg_schema
        a, b, sa, sb, _ = await self.pair()
        original = await self.post(a, 'keep existing', ch='town')
        with self.store.connect() as db:
            db.execute('ALTER TABLE chat_messages DROP COLUMN IF EXISTS reply_to')
            db.execute("UPDATE mnl_meta SET value='20' WHERE key='schema_version'")
            self.assertTrue(pg_schema.ensure(db))
            self.assertFalse(pg_schema.ensure(db))
            row = db.execute('SELECT text, reply_to FROM chat_messages WHERE id=?', (original['id'],)).fetchone()
            self.assertEqual(tuple(row), ('keep existing', None))

    async def pair(self):
        self.cfg.town_every = 0
        ta, sa = self.account('Lan Anh')
        tb, sb = self.account('Minh Tú')
        self.befriend(sa, sb)
        return await self.connect(ta), await self.connect(tb), sa, sb, tb

    async def post(self, c, text, **fields):
        await c.send(t='send', text=text, cid=text[:40], **fields)
        return await c.expect('msg', cid=text[:40])

    async def test_town_canonical_live_history_buffer_and_duplicate(self):
        a, b, sa, sb, _ = await self.pair()
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        original = await self.post(a, 'gọi 0912 345 678', ch='town')
        await b.expect('msg')
        reply = await self.post(b, 'trả lời', ch='town', reply_to=original['id'], reply={'text': 'forged'})
        expected = dict(id=original['id'], pid=self.pid(sa), name='Lan Anh', text=original['text'])
        self.assertEqual(reply.get('reply'), expected)
        self.assertNotIn('reply_to', reply)
        self.assertEqual((await a.expect('msg'))['reply'], expected)
        for action, response in [('join', 'joined'), ('history', 'history')]:
            page = await b.call(action, response, ch='town')
            self.assertEqual(page['msgs'][-1]['reply'], expected)
        await b.send(t='send', ch='town', text='trả lời', cid='again', reply_to=original['id'])
        repeated = await b.expect('msg', cid='again')
        self.assertNotEqual(repeated['id'], reply['id'])
        self.assertEqual(repeated['reply'], expected)
        self.assertEqual((await a.expect('msg', id=repeated['id']))['reply'], expected)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT reply_to FROM chat_messages WHERE id=?', (reply['id'],)).fetchone()[0], original['id'])

    async def test_dm_resume_and_inbox_last(self):
        a, b, sa, sb, tb = await self.pair()
        original = await self.post(a, 'xin chào', to=self.pid(sb))
        await b.expect('msg')
        reply = await self.post(a, 'hẹn gặp', ch=original['ch'], reply_to=original['id'])
        state = await b.call('sync', 'state')
        self.assertEqual(state['chans'][0]['last'].get('reply', {}).get('id'), original['id'])
        reconnect = await self.connect(tb, resume={original['ch']: original['id']})
        self.assertEqual((await reconnect.expect('missed'))['msgs'][0]['reply']['id'], original['id'])
        self.assertEqual((await b.call('history', 'history', ch=original['ch']))['msgs'][-1]['reply']['id'], original['id'])

    async def test_bad_or_foreign_channel_reply_rejected(self):
        a, b, sa, sb, _ = await self.pair()
        original = await self.post(a, 'private', to=self.pid(sb))
        for n, value in enumerate([True, 0, -1, '1', {}, 2**80]):
            await b.send(t='send', ch='town', text='bad value', cid=str(n), reply_to=value)
            self.assertEqual((await b.expect('error', ref=str(n)))['code'], 'bad')
        await b.send(t='send', ch='town', text='wrong channel', cid='cross', reply_to=original['id'])
        self.assertEqual((await b.expect('error', ref='cross'))['code'], 'gone')
        await b.send(t='send', ch='town', text='missing', cid='missing', reply_to=9999999)
        self.assertEqual((await b.expect('error', ref='missing'))['code'], 'gone')

    async def test_recall_and_moderation_never_resurrect_buffer_quote(self):
        a, b, sa, sb, _ = await self.pair()
        await a.call('join', 'joined', ch='town')
        original = await self.post(a, 'secret', ch='town')
        await self.post(b, 'reply', ch='town', reply_to=original['id'])
        await a.call('del', 'deleted', id=original['id'])
        for action, response in [('join', 'joined'), ('history', 'history')]:
            page = await b.call(action, response, ch='town')
            self.assertEqual(page['msgs'][-1].get('reply'), dict(id=original['id'], unavailable=True))
        await b.send(t='send', ch='town', text='too late', cid='gone', reply_to=original['id'])
        self.assertEqual((await b.expect('error', ref='gone'))['code'], 'gone')

    async def test_group_recipient_personal_hide_clear_and_block(self):
        a, b, sa, sb, _ = await self.pair()
        tc, sc = self.account('Thảo Vy')
        self.befriend(sa, sc)
        c = await self.connect(tc)
        group = await a.call('group_new', 'chan', title='Nhóm', pids=[self.pid(sb), self.pid(sc)])
        ch = group['chan']['id']
        original = await self.post(a, 'nội dung gốc', ch=ch)
        await b.expect('msg')
        await c.expect('msg')
        await c.call('hide', 'hid', id=original['id'])
        reply = await self.post(b, 'quote one', ch=ch, reply_to=original['id'])
        self.assertEqual((await a.expect('msg')).get('reply', {}).get('text'), original['text'])
        self.assertEqual((await c.expect('msg')).get('reply'), dict(id=original['id'], unavailable=True))
        await c.send(t='send', ch=ch, text='hidden reply', cid='hidden', reply_to=original['id'])
        self.assertEqual((await c.expect('error', ref='hidden'))['code'], 'gone')
        await c.call('clear', 'cleared', chs=[ch])
        await self.post(b, 'quote two', ch=ch, reply_to=original['id'])
        self.assertEqual((await c.expect('msg'))['reply'], dict(id=original['id'], unavailable=True))
        await c.call('block', 'blocked', pid=self.pid(sa))
        await self.post(b, 'quote three', ch=ch, reply_to=original['id'])
        self.assertEqual((await c.expect('msg'))['reply'], dict(id=original['id'], unavailable=True))

    async def test_quote_after_database_purge_hidden_or_missing_and_pin(self):
        a, b, sa, sb, _ = await self.pair()
        self.cfg.admins = frozenset({self.app.hub.players[self.pid(sa)].username})
        await a.call('join', 'joined', ch='town')
        original = await self.post(a, 'x' * 200, ch='town')
        reply = await self.post(b, 'pinned reply', ch='town', reply_to=original['id'])
        self.assertLessEqual(len(reply.get('reply', {}).get('text', '')), 160)
        await a.call('pin', 'pinned', id=reply['id'])
        joined = await b.call('join', 'joined', ch='town')
        self.assertEqual(joined['pin'].get('reply', {}).get('id'), original['id'])
        for sql in ["UPDATE chat_messages SET hidden=1 WHERE id=?", "UPDATE chat_messages SET hidden=0, deleted=1, text='' WHERE id=?", 'DELETE FROM chat_messages WHERE id=?']:
            with self.store.connect() as db:
                db.execute(sql, (original['id'],))
            joined = await b.call('join', 'joined', ch='town')
            self.assertEqual(joined['msgs'][-1]['reply'], dict(id=original['id'], unavailable=True))
            self.assertEqual(joined['pin']['reply'], dict(id=original['id'], unavailable=True))

    async def test_block_and_purge_invalidate_other_online_quote_caches(self):
        from game import live_chat
        a, b, sa, sb, tb = await self.pair()
        await a.call('join', 'joined', ch='town')
        original = await self.post(a, 'hello original', ch='town')
        reply = await self.post(b, 'another message', ch='town', reply_to=original['id'])
        await a.call('block', 'blocked', pid=self.pid(sb))
        self.assertEqual((await b.expect('reply_hidden'))['pid'], self.pid(sa))
        self.assertEqual((await a.expect('reply_hidden'))['pid'], self.pid(sb))
        live_chat.forget(self.store, tb)
        self.assertEqual((await a.expect('reply_hidden'))['pid'], self.pid(sb))
        with self.store.connect() as db:
            row = db.execute('SELECT deleted FROM chat_messages WHERE id=?', (reply['id'],)).fetchone()
            self.assertEqual(row[0], 1)

    async def test_current_database_marriage_block_hides_source(self):
        a, b, sa, sb, _ = await self.pair()
        original = await self.post(a, 'marriage block source', ch='town')
        await self.post(b, 'marriage block quote', ch='town', reply_to=original['id'])
        with self.store.connect() as db:
            db.execute('INSERT INTO marriage_blocks(sid, target, at) VALUES(?, ?, ?)', (sa, sb, 1))
        page = await b.call('history', 'history', ch='town')
        self.assertEqual(page['msgs'][-1]['reply'], dict(id=original['id'], unavailable=True))

    async def test_recalled_reply_itself_has_no_quote_and_membership_is_current(self):
        a, b, sa, sb, _ = await self.pair()
        original = await self.post(a, 'dm source', to=self.pid(sb))
        reply = await self.post(b, 'dm reply', ch=original['ch'], reply_to=original['id'])
        await b.call('del', 'deleted', id=reply['id'])
        page = await b.call('history', 'history', ch=original['ch'])
        self.assertNotIn('reply', page['msgs'][-1])
        with self.store.connect() as db:
            db.execute('DELETE FROM chat_members WHERE channel=? AND pid=?', (original['ch'], self.pid(sb)))
        # Cached Chan still knows this player, but quote validation must use current membership.
        await b.send(t='send', ch=original['ch'], text='removed reply', reply_to=original['id'], cid='removed')
        self.assertEqual((await b.expect('error', ref='removed'))['code'], 'gone')

    async def test_page_projection_batches_sources_without_mutating_buffer(self):
        from unittest.mock import patch
        from live import chat_reply
        a, b, sa, sb, _ = await self.pair()
        original = await self.post(a, 'batched original', ch='town')
        frames = [dict(id=i, ch='town', reply_to=original['id']) for i in range(100, 130)]
        with patch.object(self.app.db, 'fetch', wraps=self.app.db.fetch) as fetch:
            projected = await chat_reply.project(self.app.chat, self.app.hub.players[self.pid(sb)], frames)
        self.assertEqual(fetch.await_count, 1)
        self.assertTrue(all(m['reply']['text'] == original['text'] for m in projected))
        self.assertTrue(all('reply' not in m and m['reply_to'] == original['id'] for m in frames))
        self.assertTrue(all('reply_to' not in m for m in projected))

    async def test_recall_during_quote_read_never_restores_deleted_text(self):
        from unittest.mock import patch
        a, b, sa, sb, _ = await self.pair()
        tc, sc = self.account('Thảo Vy')
        c = await self.connect(tc)
        for client in (a, b, c):
            await client.call('join', 'joined', ch='town')
        original = await self.post(a, 'race source', ch='town')
        await b.expect('msg')
        await c.expect('msg')
        entered, release = asyncio.Event(), asyncio.Event()
        fetch = self.app.db.fetch

        async def paused(sql, args=()):
            rows = await fetch(sql, args)
            if 'm.name, m.text FROM chat_messages m' in sql and self.pid(sc) in args:
                entered.set()
                await release.wait()
            return rows

        with patch.object(self.app.db, 'fetch', side_effect=paused):
            await b.send(t='send', ch='town', text='race reply', reply_to=original['id'], cid='race')
            try:
                await asyncio.wait_for(entered.wait(), 3)
                await a.call('del', 'deleted', id=original['id'])
                await c.expect('deleted', id=original['id'])
            finally:
                release.set()
            incoming = await c.expect('msg')
            self.assertEqual(incoming['reply'], dict(id=original['id'], unavailable=True))

    async def test_live_fanout_batches_recipient_visibility(self):
        from unittest.mock import patch
        a, b, sa, sb, _ = await self.pair()
        c = await self.connect(self.account('Thảo Vy')[0])
        for client in (a, b, c):
            await client.call('join', 'joined', ch='town')
        original = await self.post(a, 'fanout source', ch='town')
        sender = self.app.hub.players[self.pid(sb)]
        frame = await self.app.chat.store_message(sender, 'town', 'fanout reply', 300, reply_to=original['id'])
        with patch.object(self.app.db, 'fetch', wraps=self.app.db.fetch) as fetch:
            await self.app.chat.deliver_message(await self.app.chat.chan('town'), frame, sender=sender)
        self.assertEqual(fetch.await_count, 1)

    async def test_history_resolves_quotes_after_other_async_decorations(self):
        from unittest.mock import patch
        a, b, sa, sb, _ = await self.pair()
        for client in (a, b):
            await client.call('join', 'joined', ch='town')
        original = await self.post(a, 'history race source', ch='town')
        await self.post(b, 'history race reply', ch='town', reply_to=original['id'])
        entered, release = asyncio.Event(), asyncio.Event()
        with_faces = self.app.chat.with_faces

        async def paused(messages):
            result = await with_faces(messages)
            entered.set()
            await release.wait()
            return result

        with patch.object(self.app.chat, 'with_faces', side_effect=paused):
            await b.send(t='history', ch='town')
            try:
                await asyncio.wait_for(entered.wait(), 3)
                await a.call('del', 'deleted', id=original['id'])
                await b.expect('deleted', id=original['id'])
            finally:
                release.set()
            page = await b.expect('history')
            self.assertEqual(page['msgs'][-1]['reply'], dict(id=original['id'], unavailable=True))

    async def test_welcome_drops_quote_invalidated_during_other_hello_work(self):
        from unittest.mock import patch
        a, b, sa, sb, tb = await self.pair()
        original = await self.post(a, 'welcome source', to=self.pid(sb))
        await self.post(b, 'welcome reply', ch=original['ch'], reply_to=original['id'])
        entered, release = asyncio.Event(), asyncio.Event()
        on_hello = self.app.chat.on_hello

        async def paused(conn):
            await on_hello(conn)
            entered.set()
            await release.wait()

        with patch.object(self.app.chat, 'on_hello', side_effect=paused):
            pending = asyncio.create_task(self.connect(tb))
            try:
                await asyncio.wait_for(entered.wait(), 3)
                await a.call('del', 'deleted', id=original['id'])
            finally:
                release.set()
            reconnect = await pending
            self.assertEqual(reconnect.welcome['chans'][0]['last']['reply'], dict(id=original['id'], unavailable=True))
