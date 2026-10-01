"""The live service end to end: real sockets against a real game database (SQLite here, PostgreSQL with
TEST_DATABASE_URL). Auth and origin, Cả phố (slow mode, new sessions read-only, filters), friend DMs, groups,
blocks, reports and auto-hide, mutes, deletes, unread, presence, resume after a reconnect, push throttling,
graceful restart and the socket limits."""
import asyncio
import time

from tests.live_support import HAVE_WS, LiveCase, ORIGIN

if HAVE_WS:
    from websockets.exceptions import InvalidStatus


class AuthTests(LiveCase):
    async def test_cookie_and_origin(self):
        token, sid = self.guest('Mây Bếp')
        c = await self.connect(token)
        w = c.welcome
        self.assertEqual(w['flags'], dict(chat=True, street=False, dating=False))
        self.assertEqual(w['me']['pid'], self.pid(sid))
        self.assertEqual(w['me']['name'], 'Mây Bếp')
        self.assertEqual(w['me']['town'], 'ok')
        for bad in (dict(token=None), dict(token='f' * 64), dict(token=token, origin='https://evil.example')):
            with self.assertRaises(InvalidStatus) as e:
                await self.connect(bad['token'], origin=bad.get('origin', ORIGIN))
            self.assertIn(e.exception.response.status_code, (401, 403))

    async def test_rotated_cookie_of_an_account_is_refused(self):
        token, sid = self.guest(name=None)
        with self.store.connect() as db:   # the save became an account: only a login row reaches it now
            db.execute("INSERT INTO accounts(username, display, pw, sid) VALUES('acc1', 'Acc', 'x', ?)", (sid,))
        with self.assertRaises(InvalidStatus) as e:
            await self.connect(token)
        self.assertEqual(e.exception.response.status_code, 401)
        login, _ = self.account('Lan Anh')
        c = await self.connect(login)
        self.assertEqual(c.welcome['me']['name'], 'Lan Anh')
        self.assertTrue(c.welcome['me']['account'])

    async def test_hello_first_and_frame_limits(self):
        token, _ = self.guest()
        c = await self.connect(token, hello=False)
        await c.send(t='send', ch='town', text='hi')
        code, _ = await c.wait_closed()
        self.assertEqual(code, 1008)
        c = await self.connect(token)
        await c.ws.send('{"t":"ping","x":"' + 'a' * 5000 + '"}')
        code, _ = await c.wait_closed()
        self.assertEqual(code, 1009)
        c = await self.connect(token)
        await c.ws.send('not json')
        self.assertEqual((await c.wait_closed())[0], 1007)
        c = await self.connect(token)
        for _ in range(60):
            try:
                await c.send(t='ping')
            except Exception:  # noqa: BLE001 - closed mid-flood
                break
        self.assertEqual((await c.wait_closed())[0], 1008)

    async def test_ping_and_unknown(self):
        token, _ = self.guest()
        c = await self.connect(token)
        self.assertIn('at', await c.call('ping', 'pong'))
        e = await c.call('nope', 'error')
        self.assertEqual(e['code'], 'unknown')


class TownTests(LiveCase):
    async def test_post_read_and_slow_mode(self):
        a = await self.connect(self.guest('Mây Hồng')[0])
        b = await self.connect(self.guest('Gió')[0])
        idle = await self.connect(self.guest('Lá')[0])
        ja = await a.call('join', 'joined', ch='town')
        self.assertEqual((ja['why'], ja['msgs']), ('ok', []))
        await b.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='  chào   cả phố  ', cid='c1')
        mine = await a.expect('msg', cid='c1')
        self.assertEqual(mine['text'], 'chào cả phố')
        self.assertEqual(mine['wait'], 10)
        got = await b.expect('msg')
        self.assertEqual((got['text'], got['name'], got['id']), ('chào cả phố', 'Mây Hồng', mine['id']))
        await idle.nothing('msg')   # not on Cả phố: nothing sent to it
        await a.send(t='send', ch='town', text='lần nữa', cid='c2')
        e = await a.expect('error', ref='c2')
        self.assertEqual(e['code'], 'slow')
        self.assertGreater(e['wait'], 8)
        await b.send(t='send', ch='town', text='x' * 301, cid='long')
        self.assertEqual((await b.expect('error', ref='long'))['code'], 'text')
        # a late joiner gets the last messages; history pages back
        late = await self.connect(self.guest('Muộn')[0])
        j = await late.call('join', 'joined', ch='town')
        self.assertEqual([m['text'] for m in j['msgs']], ['chào cả phố'])
        again = await late.call('join', 'joined', ch='town', after=mine['id'])   # back on Cả phố: only what is new
        self.assertEqual((again['msgs'], again['inc']), ([], True))
        h = await late.call('history', 'history', ch='town', before=mine['id'] + 1)
        self.assertEqual([m['id'] for m in h['msgs']], [mine['id']])
        self.assertFalse(h['more'])

    async def test_new_session_and_unnamed_read_only(self):
        new = await self.connect(self.guest('Tí', old=False)[0])
        j = await new.call('join', 'joined', ch='town')
        self.assertEqual(j['why'], 'new')
        self.assertGreater(j['wait'], 590)
        await new.send(t='send', ch='town', text='alo', cid='n')
        self.assertEqual((await new.expect('error', ref='n'))['code'], 'new')
        anon = await self.connect(self.guest(None)[0])
        self.assertEqual(anon.welcome['me']['town'], 'name')
        await anon.send(t='send', ch='town', text='alo', cid='a')
        self.assertEqual((await anon.expect('error', ref='a'))['code'], 'name')

    async def test_filters_and_duplicates(self):
        self.cfg.town_every = 0
        a = await self.connect(self.guest('Mây Hồng')[0])
        await a.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='gọi 0912 345 678, zalo minh123, vl thật', cid='f')
        m = await a.expect('msg', cid='f')
        self.assertEqual(m['text'], 'gọi •••, zalo •••, vl thật')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT text FROM chat_messages WHERE id=?', (m['id'],)).fetchone()[0], m['text'])
        await a.send(t='send', ch='town', text='GỌI 0912 345 678 — Zalo minh123 vl thật!!', cid='d')
        self.assertEqual((await a.expect('error', ref='d'))['code'], 'dup')

    async def test_delete_own_keeps_the_row(self):
        a = await self.connect(self.guest('Mây Hồng')[0])
        b = await self.connect(self.guest('Gió')[0])
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='lỡ tay', cid='x')
        m = await a.expect('msg', cid='x')
        await b.expect('msg')
        await b.send(t='del', id=m['id'], cid='nope')
        self.assertEqual((await b.expect('error', ref='nope'))['code'], 'gone')
        await a.send(t='del', id=m['id'])
        d = await b.expect('deleted')
        self.assertEqual((d['ch'], d['id']), ('town', m['id']))
        with self.store.connect() as db:
            r = db.execute('SELECT text, deleted FROM chat_messages WHERE id=?', (m['id'],)).fetchone()
        self.assertEqual((r[0], r[1]), ('', 1))
        j = await (await self.connect(self.guest('Sau')[0])).call('join', 'joined', ch='town')
        self.assertEqual((j['msgs'][0]['text'], j['msgs'][0]['del']), ('', 1))


class FriendTests(LiveCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ta, self.sa = self.account('An')
        self.tb, self.sb = self.account('Bình')
        self.pa, self.pb = self.pid(self.sa), self.pid(self.sb)

    async def test_dm_only_between_friends(self):
        a = await self.connect(self.ta)
        await a.send(t='send', to=self.pb, text='chào', cid='1')
        self.assertEqual((await a.expect('error', ref='1'))['code'], 'not_friend')
        self.befriend(self.sa, self.sb)
        b = await self.connect(self.tb)
        await a.send(t='send', to=self.pb, text='chào Bình', cid='2')
        mine = await a.expect('msg', cid='2')
        self.assertEqual(mine['ch'], f'dm:{min(self.pa, self.pb)}:{max(self.pa, self.pb)}')
        got = await b.expect('msg')
        self.assertEqual((got['text'], got['name'], got['ch']), ('chào Bình', 'An', mine['ch']))
        # unread for B, then read
        s = await b.call('sync', 'state')
        ch = next(c for c in s['chans'] if c['id'] == mine['ch'])
        self.assertEqual((ch['unread'], ch['peer']['name'], ch['last']['text']), (1, 'An', 'chào Bình'))
        b2 = await self.connect(self.tb)   # B's other tab hears the read
        await b.send(t='read', ch=mine['ch'], id=mine['id'])
        await b2.expect('read', ch=mine['ch'])
        s = await b.call('sync', 'state')
        self.assertEqual(next(c for c in s['chans'] if c['id'] == mine['ch'])['unread'], 0)
        # a stranger can neither read nor post there
        c = await self.connect(self.account('Lạ')[0])
        for t in ('history', 'send'):
            await c.send(t=t, ch=mine['ch'], text='?', cid=t)
            self.assertEqual((await c.expect('error', ref=t))['code'], 'no_chat')
        # unfriended: the chat stays readable, sending stops
        with self.store.connect() as db:
            db.execute('DELETE FROM friends WHERE sid IN (?, ?)', (self.sa, self.sb))
        await a.send(t='send', ch=mine['ch'], text='còn đó không', cid='3')
        self.assertEqual((await a.expect('error', ref='3'))['code'], 'not_friend')
        h = await a.call('history', 'history', ch=mine['ch'])
        self.assertEqual([m['text'] for m in h['msgs']], ['chào Bình'])

    async def test_blocks_hide_both_ways(self):
        self.befriend(self.sa, self.sb)
        a = await self.connect(self.ta)
        b = await self.connect(self.tb)
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        await a.call('block', 'blocked', pid=self.pb)
        await b.send(t='send', ch='town', text='B nói', cid='b')
        await b.expect('msg', cid='b')
        await a.nothing('msg')
        await a.send(t='send', ch='town', text='A nói', cid='a')
        await a.expect('msg', cid='a')
        await b.nothing('msg')
        await b.send(t='send', to=self.pa, text='nhắn riêng', cid='dm')
        self.assertEqual((await b.expect('error', ref='dm'))['code'], 'not_friend')
        # a fresh socket of A does not see B's Cả phố message either (blocks are in the database)
        j = await (await self.connect(self.ta)).call('join', 'joined', ch='town')
        self.assertEqual([m['text'] for m in j['msgs']], ['A nói'])
        # the marriage/friends block (by save id) counts the same
        with self.store.connect() as db:
            db.execute('DELETE FROM blocks')
            db.execute('INSERT INTO marriage_blocks(sid, target, at) VALUES(?, ?, ?)', (self.sb, self.sa, time.time()))
        j = await (await self.connect(self.ta)).call('join', 'joined', ch='town')
        self.assertEqual([m['text'] for m in j['msgs']], ['A nói'])

    async def test_presence_and_appear_offline(self):
        self.befriend(self.sa, self.sb)
        a = await self.connect(self.ta)
        self.assertEqual(a.welcome['friends'], [dict(pid=self.pb, name='Bình', av='🌸', on=False)])
        b = await self.connect(self.tb)
        self.assertEqual(b.welcome['friends'][0]['on'], True)
        self.assertEqual((await a.expect('presence', pid=self.pb))['on'], True)
        await b.send(t='prefs', online=False)
        await b.expect('prefs', online=False)
        self.assertEqual((await a.expect('presence', pid=self.pb))['on'], False)
        s = await a.call('sync', 'state')
        self.assertEqual(s['friends'][0]['on'], False)
        sb = await b.call('sync', 'state')        # hidden: sees nobody online either
        self.assertEqual(sb['friends'][0]['on'], False)
        await b.send(t='prefs', online=True)
        self.assertEqual((await a.expect('presence', pid=self.pb))['on'], True)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT online FROM chat_prefs WHERE pid=?', (self.pb,)).fetchone()[0], 1)
        await b.close()
        self.assertEqual((await a.expect('presence', pid=self.pb, timeout=3))['on'], False)

    async def test_resume_after_reconnect(self):
        self.befriend(self.sa, self.sb)
        a = await self.connect(self.ta)
        b = await self.connect(self.tb)
        await a.send(t='send', to=self.pb, text='một', cid='1')
        first = await a.expect('msg', cid='1')
        await b.expect('msg')
        await b.close()
        for i, text in enumerate(('hai', 'ba')):
            await a.send(t='send', ch=first['ch'], text=text, cid=f'r{i}')
            await a.expect('msg', cid=f'r{i}')
        b = await self.connect(self.tb, resume={first['ch']: first['id']})
        missed = await b.expect('missed')
        self.assertEqual([m['text'] for m in missed['msgs']], ['hai', 'ba'])
        self.assertFalse(missed['more'])

    async def test_push_once_per_ten_minutes_per_chat(self):
        self.befriend(self.sa, self.sb)
        with self.store.connect() as db:
            db.execute('INSERT INTO push_subs(endpoint, sid, created, prefs) VALUES(?, ?, ?, ?)',
                       ('https://fcm.googleapis.com/x', self.sb, time.time(), '{"social": true}'))
        a = await self.connect(self.ta)
        for i in range(3):
            await a.send(t='send', to=self.pb, text=f'tin {i}', cid=f'p{i}')
            await a.expect('msg', cid=f'p{i}')
        await asyncio.sleep(0.3)
        with self.store.connect() as db:
            rows = db.execute("SELECT kind, body, url FROM push_queue WHERE sid=?", (self.sb,)).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], 'chat')
        self.assertEqual(rows[0][1], 'An: tin 0')
        self.assertTrue(rows[0][2].startswith('/?chat=dm:'))
        # online: no push at all
        b = await self.connect(self.tb)
        with self.store.connect() as db:
            db.execute('UPDATE chat_members SET pushed_at=0')
        await a.send(t='send', to=self.pb, text='đang online', cid='on')
        await b.expect('msg')
        await asyncio.sleep(0.2)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM push_queue WHERE sid=?', (self.sb,)).fetchone()[0], 1)


class GroupTests(LiveCase):
    async def test_groups(self):
        people = [self.account(n) for n in ('Chủ', 'Một', 'Hai', 'Lạ')]
        (to, so), (t1, s1), (t2, s2), (tx, sx) = people
        for s in (s1, s2):
            self.befriend(so, s)
        owner = await self.connect(to)
        one = await self.connect(t1)
        two = await self.connect(t2)
        await owner.send(t='group_new', title='Hội bàn bên', pids=[self.pid(sx)], cid='bad')
        self.assertEqual((await owner.expect('error', ref='bad'))['code'], 'not_friend')
        await owner.send(t='group_new', title='Hội bàn bên', pids=[self.pid(s1)], cid='g')
        g = await owner.expect('chan', open=True)
        ch = g['chan']['id']
        self.assertEqual((g['chan']['n'], g['chan']['role']), (2, 'owner'))
        self.assertEqual((await one.expect('chan'))['chan']['id'], ch)
        await owner.send(t='group_add', ch=ch, pids=[self.pid(s2)])
        self.assertEqual((await two.expect('chan'))['chan']['n'], 3)
        await one.send(t='send', ch=ch, text='chào nhóm', cid='m')
        await one.expect('msg', cid='m')
        for c in (owner, two):
            self.assertEqual((await c.expect('msg'))['text'], 'chào nhóm')
        m = await one.call('members', 'members', ch=ch)
        self.assertEqual([x['name'] for x in m['members']], ['Chủ', 'Một', 'Hai'])
        await one.send(t='group_kick', ch=ch, pid=self.pid(s2), cid='k')
        self.assertEqual((await one.expect('error', ref='k'))['code'], 'owner')
        await owner.send(t='group_kick', ch=ch, pid=self.pid(s2))
        await two.expect('unchan', ch=ch)
        await two.send(t='send', ch=ch, text='còn không', cid='z')
        self.assertEqual((await two.expect('error', ref='z'))['code'], 'no_chat')
        await owner.send(t='group_leave', ch=ch)
        await owner.expect('unchan', ch=ch)
        for _ in range(5):   # the next member leads
            if (await one.expect('chan'))['chan']['owner'] == self.pid(s1):
                break
        else:
            self.fail('no new owner')
        # at most 20 people
        many = [self.account(f'B{i}')[1] for i in range(20)]
        for s in many:
            self.befriend(so, s)
        await owner.send(t='group_new', title='Đông quá', pids=[self.pid(s) for s in many], cid='full')
        self.assertEqual((await owner.expect('error', ref='full'))['code'], 'full')


class ModerationTests(LiveCase):
    async def test_three_reports_hide_until_review(self):
        self.cfg.town_every = 0
        author = await self.connect(self.guest('Tác giả')[0])
        readers = [await self.connect(self.guest(f'R{i}')[0]) for i in range(3)]
        for c in (author, *readers):
            await c.call('join', 'joined', ch='town')
        await author.send(t='send', ch='town', text='spam spam', cid='s')
        m = await author.expect('msg', cid='s')
        await author.send(t='report', id=m['id'], reason='spam', cid='own')
        self.assertEqual((await author.expect('error', ref='own'))['code'], 'bad')
        for i, r in enumerate(readers):
            await r.send(t='report', id=m['id'], reason='spam')
            await r.expect('reported')
            if i == 0:   # the same reporter twice counts once
                await r.send(t='report', id=m['id'], reason='rude')
                await r.expect('reported')
        d = await author.expect('deleted')
        self.assertEqual((d['id'], d['hidden']), (m['id'], 1))
        with self.store.connect() as db:
            r = db.execute('SELECT hidden, reports, text FROM chat_messages WHERE id=?', (m['id'],)).fetchone()
            self.assertEqual((r[0], r[1], r[2]), (1, 3, 'spam spam'))   # kept for the admin
            self.assertEqual(db.execute("SELECT COUNT(*) FROM reports WHERE kind='chat' AND target=?", (str(m['id']),)).fetchone()[0], 3)
        j = await (await self.connect(self.guest('Mới')[0])).call('join', 'joined', ch='town')
        self.assertEqual(j['msgs'], [])
        h = await readers[0].call('history', 'history', ch='town')
        self.assertEqual(h['msgs'], [])

    async def test_mute_blocks_every_chat(self):
        token, sid = self.guest('Ồn ào')
        c = await self.connect(token)
        with self.store.connect() as db:
            db.execute('INSERT INTO chat_mutes(pid, until, by_admin, reason, at) VALUES(?, ?, ?, ?, ?)',
                       (self.pid(sid), time.time() + 3600, 'admin', '', time.time()))
        await c.send(t='send', ch='town', text='alo', cid='m')
        e = await c.expect('error', ref='m')
        self.assertEqual(e['code'], 'muted')
        self.assertGreater(e['until'], time.time() + 3500)
        c2 = await self.connect(token)
        self.assertEqual(c2.welcome['me']['town'], 'muted')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0], 0)


class RestartTests(LiveCase):
    async def test_stop_closes_with_1012(self):
        c = await self.connect(self.guest()[0])
        await self.app.stop()
        self.assertEqual((await c.wait_closed())[0], 1012)
        self.app.db = None   # tearDown stops it again: harmless

    async def test_oldest_tab_closed_past_the_cap(self):
        self.cfg.per_player = 2
        token, _ = self.guest()
        first = await self.connect(token)
        await self.connect(token)
        await self.connect(token)
        self.assertEqual((await first.wait_closed())[0], 4002)

    async def test_switches_off(self):
        self.cfg.chat = False
        c = await self.connect(self.guest()[0], hello=False)
        await c.send(t='hello', v=1)
        w = await c.expect('welcome')
        self.assertEqual(w['flags']['chat'], False)
        self.assertEqual((await c.wait_closed())[0], 4001)
