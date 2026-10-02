"""🗑️ Deleting in chat (owner, 03/10): "Xóa ở phía tôi" (hide one message for myself), emptying whole chats from the
chat list (clear, for myself), "Thu hồi" (recall my own message for everyone, within 24 h), and 🚫 the list of people
I blocked, to unblock them (feedback #93). Nobody else's view changes; the admin side still sees every message."""
import time

from game import live_chat
from tests.live_support import LiveCase


class DeleteTests(LiveCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ta, self.sa = self.account('An')
        self.tb, self.sb = self.account('Bình')
        self.pa, self.pb = self.pid(self.sa), self.pid(self.sb)
        self.befriend(self.sa, self.sb)

    async def dm(self, a, b, texts):
        out = []
        for i, t in enumerate(texts):
            await a.send(t='send', to=self.pb, text=t, cid=f'm{i}')
            out.append(await a.expect('msg', cid=f'm{i}'))
            await b.expect('msg')
        return out

    def count(self, sql, args=()):
        with self.store.connect() as db:
            return db.execute(sql, args).fetchone()[0]

    async def test_flag_and_hide_one_message_for_me_only(self):
        a = await self.connect(self.ta)
        b = await self.connect(self.tb)
        self.assertTrue(b.welcome['flags']['chatdel'])
        self.assertTrue(b.welcome['flags']['blocks'])
        m1, m2 = await self.dm(a, b, ['một', 'hai'])
        b2 = await self.connect(self.tb)   # B's other tab hears it too
        await b.send(t='hide', id=m1['id'])
        self.assertEqual((await b.expect('hid'))['id'], m1['id'])
        self.assertEqual((await b2.expect('hid'))['ch'], m1['ch'])
        await a.nothing('hid')
        hb = await b.call('history', 'history', ch=m1['ch'])
        self.assertEqual([m['text'] for m in hb['msgs']], ['hai'])
        ha = await a.call('history', 'history', ch=m1['ch'])
        self.assertEqual([m['text'] for m in ha['msgs']], ['một', 'hai'])
        self.assertEqual(self.count('SELECT COUNT(*) FROM chat_messages WHERE deleted=0 AND hidden=0'), 2)   # the rows stay
        # the last message hidden: no preview in my list, theirs unchanged
        await b.send(t='hide', id=m2['id'])
        await b.expect('hid')
        c = next(x for x in (await b.call('sync', 'state'))['chans'] if x['id'] == m1['ch'])
        self.assertNotIn('last', c)
        c = next(x for x in (await a.call('sync', 'state'))['chans'] if x['id'] == m1['ch'])
        self.assertEqual(c['last']['text'], 'hai')
        # a reconnect resumes without them
        b3 = await self.connect(self.tb, resume={m1['ch']: 0})
        self.assertEqual((await b3.expect('missed'))['msgs'], [])
        # a stranger cannot hide inside a chat they are not in
        tc, _ = self.account('Chi')
        c = await self.connect(tc)
        await c.send(t='hide', id=m1['id'], cid='x')
        self.assertEqual((await c.expect('error', ref='x'))['code'], 'no_chat')
        await c.send(t='hide', id=10 ** 9, cid='y')
        self.assertEqual((await c.expect('error', ref='y'))['code'], 'gone')

    async def test_town_hide_prune_and_forget(self):
        self.cfg.town_every = 0
        a = await self.connect(self.ta)
        b = await self.connect(self.tb)
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='rao vặt', cid='t1')
        m = await a.expect('msg', cid='t1')
        await b.expect('msg')
        await a.send(t='send', ch='town', text='chào phố', cid='t2')
        await a.expect('msg', cid='t2')
        await b.send(t='hide', id=m['id'])
        await b.expect('hid')
        jb = await b.call('join', 'joined', ch='town')
        self.assertEqual([x['text'] for x in jb['msgs']], ['chào phố'])
        ja = await a.call('join', 'joined', ch='town')
        self.assertEqual([x['text'] for x in ja['msgs']], ['rao vặt', 'chào phố'])
        hb = await b.call('history', 'history', ch='town')
        self.assertEqual([x['text'] for x in hb['msgs']], ['chào phố'])
        # pruning Cả phố takes the hide rows of the pruned messages with it
        self.assertEqual(await self.app.chat.prune_town(keep=1), 1)
        self.assertEqual(self.count('SELECT COUNT(*) FROM chat_hides'), 0)
        # a player who deletes their data loses their hide and clear rows
        await b.send(t='send', ch='town', text='của B', cid='t3')
        own = await b.expect('msg', cid='t3')
        await a.send(t='hide', id=own['id'])
        await a.expect('hid')
        with self.store.connect() as db:
            db.execute('INSERT INTO chat_clears(channel, pid, upto, at) VALUES(?, ?, 1, 0)', ('g:0123456789', self.pa))
        live_chat.forget(self.store, self.ta)
        self.assertEqual(self.count('SELECT COUNT(*) FROM chat_hides WHERE pid=?', (self.pa,)), 0)
        self.assertEqual(self.count('SELECT COUNT(*) FROM chat_clears WHERE pid=?', (self.pa,)), 0)

    async def test_clear_whole_chats_from_the_list(self):
        tc, sc = self.account('Chi')
        self.befriend(self.sa, sc)
        a = await self.connect(self.ta)
        b = await self.connect(self.tb)
        c = await self.connect(tc)
        m1, _ = await self.dm(a, b, ['một', 'hai'])
        await a.send(t='group_new', title='Hội ba người', pids=[self.pb, self.pid(sc)], cid='g')
        g = (await a.expect('chan', open=True))['chan']['id']
        await a.send(t='send', ch=g, text='nhóm đây', cid='gm')
        await a.expect('msg', cid='gm')
        await b.expect('msg', ch=g)
        s = await b.call('sync', 'state')
        self.assertEqual({x['id']: x['unread'] for x in s['chans']}, {m1['ch']: 2, g: 1})
        await b.send(t='clear', chs=[m1['ch'], g])
        done = await b.expect('cleared')
        self.assertEqual(set(done['chs']), {m1['ch'], g})
        s = await b.call('sync', 'state')
        self.assertEqual([(x['id'], x['unread'], 'last' in x) for x in s['chans']], [(g, 0, False)])   # the DM left, the group stays empty
        self.assertEqual((await b.call('history', 'history', ch=m1['ch']))['msgs'], [])
        self.assertEqual((await b.call('history', 'history', ch=g))['msgs'], [])
        self.assertEqual(len((await a.call('history', 'history', ch=m1['ch']))['msgs']), 2)   # A keeps everything
        self.assertEqual(len((await c.call('history', 'history', ch=g))['msgs']), 1)
        # a new message brings the DM back, with only what came after
        await a.send(t='send', to=self.pb, text='ba', cid='n')
        await a.expect('msg', cid='n')
        await b.expect('msg', ch=m1['ch'])
        s = await b.call('sync', 'state')
        d = next(x for x in s['chans'] if x['id'] == m1['ch'])
        self.assertEqual((d['unread'], d['last']['text']), (1, 'ba'))
        self.assertEqual([x['text'] for x in (await b.call('history', 'history', ch=m1['ch']))['msgs']], ['ba'])
        # Cả phố and chats I am not in cannot be cleared; bad lists are refused
        for i, chs in enumerate((['town'], [], 'x', [g] * 2, [f'dm:{"0" * 16}:{"1" * 16}'], [g] + ['y'] * 21)):
            await b.send(t='clear', chs=chs, cid=f'c{i}')
            self.assertIn((await b.expect('error', ref=f'c{i}'))['code'], ('bad', 'no_chat'))

    async def test_recall_within_24_hours_and_reported_text_kept_for_admins(self):
        a = await self.connect(self.ta)
        b = await self.connect(self.tb)
        m1, m2, m3 = await self.dm(a, b, ['nhầm', 'cũ rồi', 'nói bậy'])
        await a.send(t='del', id=m1['id'])
        self.assertEqual((await b.expect('deleted'))['id'], m1['id'])
        with self.store.connect() as db:
            db.execute('UPDATE chat_messages SET at=? WHERE id=?', (time.time() - 25 * 3600, m2['id']))
        await a.send(t='del', id=m2['id'], cid='old')
        self.assertEqual((await a.expect('error', ref='old'))['code'], 'old')
        await b.call('report', 'reported', id=m3['id'], reason='rude')
        await a.send(t='del', id=m3['id'])
        await b.expect('deleted')
        with self.store.connect() as db:
            rows = {r[0]: (r[1], r[2], r[3]) for r in db.execute('SELECT id, text, raw, deleted FROM chat_messages').fetchall()}
        self.assertEqual(rows[m1['id']], ('', None, 1))
        self.assertEqual(rows[m2['id']], ('cũ rồi', None, 0))
        self.assertEqual(rows[m3['id']], ('', 'nói bậy', 1))   # reported first: the admin still reads it
        item = live_chat.search(self.store, dict(pid=self.pa))['items']
        self.assertEqual(next(x for x in item if x['id'] == m3['id'])['raw'], 'nói bậy')
        h = await b.call('history', 'history', ch=m1['ch'])
        self.assertEqual([(x['text'], x.get('del')) for x in h['msgs']], [('', 1), ('cũ rồi', None), ('', 1)])   # never to players
        # the tombstone can still be deleted on my side
        await b.send(t='hide', id=m1['id'])
        await b.expect('hid')

    async def test_without_the_tables_the_options_are_off(self):
        with self.store.connect() as db:
            db.execute('DROP TABLE chat_hides')
            db.execute('DROP TABLE chat_clears')
        self.assertFalse(await self.app.chat.check_del())
        a = await self.connect(self.ta)
        b = await self.connect(self.tb)
        self.assertFalse(b.welcome['flags']['chatdel'])
        m1, = await self.dm(a, b, ['một'])
        await b.send(t='hide', id=m1['id'], cid='h')
        self.assertEqual((await b.expect('error', ref='h'))['code'], 'off')
        self.assertEqual(len((await b.call('history', 'history', ch=m1['ch']))['msgs']), 1)   # everything else as before
        self.assertEqual(len((await b.call('sync', 'state'))['chans']), 1)
        with self.store.connect() as db:   # the game server of this release starts: on again at the next look
            db.executescript(live_chat.SCHEMA)
        await self.app.chat.tick(time.time() + 3600)
        self.assertTrue(self.app.chat.del_ok)
        b2 = await self.connect(self.tb)
        self.assertTrue(b2.welcome['flags']['chatdel'])
        await b2.call('hide', 'hid', id=m1['id'])

    async def test_blocked_list_and_unblock(self):
        tc, sc = self.account('Chi')
        a = await self.connect(self.ta)
        c = await self.connect(tc)
        self.cfg.town_every = 0
        await c.send(t='send', ch='town', text='chào', cid='t')
        await c.expect('msg', cid='t')
        self.assertEqual((await a.call('blocks', 'blocks'))['list'], [])
        await a.call('block', 'blocked', pid=self.pb)            # a friend
        await a.call('block', 'blocked', pid=self.pid(sc))       # someone from Cả phố
        got = (await a.call('blocks', 'blocks'))['list']
        self.assertEqual({x['pid']: x['name'] for x in got}, {self.pb: 'Bình', self.pid(sc): 'Chi'})
        b = await self.connect(self.tb)
        self.assertEqual((await b.call('blocks', 'blocks'))['list'], [])   # only my own blocks
        r = await a.call('unblock', 'blocked', pid=self.pb)
        self.assertFalse(r['on'])
        self.assertEqual([x['pid'] for x in (await a.call('blocks', 'blocks'))['list']], [self.pid(sc)])
