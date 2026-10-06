"""🎤 Phòng hát in the live service (live/karaoke.py, LIVE_KARAOKE): the room state machine with real sockets on a
disposable PostgreSQL schema, the clock driven by calling the feature's tick with chosen times.

Rooms and overflow, the ticket redeemed once, the shared start (`at`), the length from the clients' reports, the end,
the applause and the next song, vote-skip and the singer's own skip, an absent singer passed over then dropped,
reactions batched, bubbles and blocks, 🧩 Đoán bài (emoji and lyric rounds, near / right guesses, the prize and its
caps, the timeout, the reward link), and the moderation (ban, kick, close, mute, reports, admin acts from the game
server, tips announced)."""
import asyncio
import json
import secrets
import time
from unittest.mock import patch

from game import karaoke as kg
from live import karaoke as lk
from tests.live_support import LiveCase

VID, VID2, VID3 = 'dQw4w9WgXcQ', 'kJQP7kiw5Fk', '9bZkp7q19f0'


class KaraCase(LiveCase):
    cfg_extra = dict(kara=True)

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.feat = self.app.by_name['karaoke']
        with self.store.connect() as db:
            for v, t in ((VID, 'Nơi này có anh'), (VID2, 'Despacito'), (VID3, 'Gangnam Style')):
                db.execute("INSERT INTO kara_songs(vid, title, channel, ok, why, checked_at) VALUES(?, ?, '', 1, '', ?)", (v, t, time.time()))

    async def enter(self, name, theme='tre', account=True, rid=None):
        token, sid = self.account(name) if account else self.guest(name)
        c = await self.connect(token)
        c.token, c.sid, c.pid = token, sid, self.pid(sid)
        c.room = await c.call('kara_in', 'kara_room', **({'id': rid} if rid else {'theme': theme}))
        return c

    def ticket(self, c):
        e = 'kq-' + secrets.token_hex(12)
        with self.store.connect() as db:
            db.execute("INSERT INTO kara_tickets(id, sid, kind, amount, day, at) VALUES(?, ?, 'queue', 0, ?, ?)", (e, c.sid, kg.vn_day(), time.time()))
        return e

    async def add(self, c, vid=VID):
        e = self.ticket(c)
        await c.send(t='kara_add', vid=vid, e=e)
        await c.expect('kara_added', e=e)
        return e

    def room(self, rid='kara:tre'):
        return self.app.hub.rooms[rid]

    def admin(self, c):
        with self.store.connect() as db:
            u = db.execute('SELECT username FROM accounts WHERE sid=?', (c.sid,)).fetchone()['username']
        self.cfg.admins = frozenset({u.lower()})
        self.app.hub.players[c.pid].username = u.lower()

    async def tick(self, at):
        await self.feat.tick(at)

    def fresh(self, c):
        """A host who may give a round now (no gap, no rate window): the tests give many in a row."""
        p = self.app.hub.players[c.pid]
        p.ext['kara_round_at'] = 0
        p.rates.pop('kara_round', None)


class Rooms(KaraCase):
    async def test_rooms_overflow_list_and_guests(self):
        self.assertTrue((await self.connect(self.account('Mai')[0])).welcome['flags']['kara'])
        with patch.object(lk, 'ROOM_CAP', 2):
            a, b = await self.enter('Lan'), await self.enter('Minh')
            self.assertEqual(a.room['id'], 'kara:tre')
            self.assertEqual((await a.expect('kara_ppl'))['pid'], b.pid)
            c = await self.enter('Hoa', rid='kara:tre')                       # full: the overflow room of the same theme
            self.assertEqual((c.room['id'], c.room['moved'], c.room['name']), ('kara:tre-2', 1, 'Nhạc trẻ 2'))
            rooms = (await a.call('kara_list', 'kara_list'))['rooms']
            self.assertEqual([(r['id'], r['n']) for r in rooms], [('kara:tre', 2), ('kara:tre-2', 1), ('kara:bolero', 0), ('kara:qt', 0)])
        g = await self.enter('Khách vãng lai', theme='qt', account=False)     # a guest listens only
        self.assertFalse(g.room['account'])
        await g.send(t='kara_add', vid=VID, e=self.ticket(g))
        self.assertEqual((await g.expect('error', ref='kara_add'))['code'], 'account')
        await g.send(t='kara_say', text='hello')
        self.assertEqual((await g.expect('error', ref='kara_say'))['code'], 'account')
        await c.call('kara_in', 'kara_room', theme='qt')                     # one room a player: out of tre-2 (dropped, empty)
        self.assertNotIn('kara:tre-2', self.app.hub.rooms)
        await c.call('kara_out', 'kara_left')
        self.assertNotIn(c.pid, self.room('kara:qt').data['people'])
        t = await a.call('kara_time', 'kara_time', c=7)
        self.assertEqual(t['c'], 7)
        self.assertLess(abs(t['at'] - time.time()), 1)


class Stage(KaraCase):
    async def test_ticket_play_length_end_applause_next(self):
        a, b = await self.enter('Lan'), await self.enter('Minh')
        t0 = time.time()
        e = await self.add(a)
        pa, pb = await a.expect('kara_play'), await b.expect('kara_play')
        self.assertEqual((pa['e'], pa['vid'], pa['title'], pa['by']['pid']), (e, VID, 'Nơi này có anh', a.pid))
        self.assertEqual(pa['at'], pb['at'])                                  # one shared start for everyone
        self.assertAlmostEqual(pa['at'], t0 + lk.LEAD, delta=1)
        await asyncio.sleep(.2)
        with self.store.connect() as db:
            row = db.execute('SELECT used, vid, room, played FROM kara_tickets WHERE id=?', (e,)).fetchone()
        self.assertEqual((row['used'], row['vid'], row['room']), (1, VID, 'kara:tre'))
        self.assertIsNotNone(row['played'])
        await a.send(t='kara_add', vid=VID2, e=e)                            # a spent ticket, and already singing
        self.assertEqual((await a.expect('error', ref='kara_add'))['code'], 'queued')
        self.assertEqual((await a.call('kara_can', 'kara_can'))['why'], 'queued')
        b.room = None
        await b.send(t='kara_add', vid=VID2, e=e)                            # someone else's ticket
        self.assertEqual((await b.expect('error', ref='kara_add'))['code'], 'ticket')
        e2 = await self.add(b, VID2)
        self.assertEqual([q['e'] for q in (await a.expect('kara_q'))['queue']], [])
        self.assertEqual([q['e'] for q in (await a.expect('kara_q'))['queue']], [e2])
        await a.send(t='kara_dur', e=e, dur=200.5)
        await b.send(t='kara_dur', e=e, dur=180)
        await b.send(t='kara_dur', e='nope', dur=5)
        await asyncio.sleep(.2)
        d = self.room().data
        self.assertEqual(d['dur'], (200.5 + 180) / 2)
        await self.tick(pa['at'] + 1)
        self.assertEqual(d['phase'], 'play')
        await a.send(t='kara_react', k='❤️')
        await asyncio.sleep(.2)
        await self.tick(pa['at'] + d['dur'] + .1)
        end = await b.expect('kara_end')
        self.assertEqual((end['e'], end['why'], end['by']['pid'], end['hearts']), (e, 'done', a.pid, 1))
        self.assertAlmostEqual(end['until'] - (pa['at'] + d['dur'] + .1), lk.APPLAUSE, delta=.01)
        await self.tick(end['until'] + .1)
        await b.expect('kara_stage', stage=None)
        nxt = await a.expect('kara_play')
        self.assertEqual((nxt['e'], nxt['by']['pid']), (e2, b.pid))

    async def test_long_video_is_cut_at_seven_minutes(self):
        a = await self.enter('Lan')
        e = await self.add(a)
        p = await a.expect('kara_play')
        await a.send(t='kara_dur', e=e, dur=3600)
        await asyncio.sleep(.2)
        self.assertEqual(self.room().data['dur'], lk.DUR_MAX)
        await self.tick(p['at'] + lk.DUR_MAX + .1)
        self.assertEqual((await a.expect('kara_end'))['why'], 'cut')

    async def test_votes_own_skip_and_an_absent_singer(self):
        self.assertEqual([lk.vote_need(n) for n in (0, 1, 2, 3, 5, 10, 30)], [1, 1, 2, 3, 3, 4, 12])
        a, b, c = await self.enter('Lan'), await self.enter('Minh'), await self.enter('Hoa')
        e = await self.add(a)
        await a.expect('kara_play')
        await a.send(t='kara_vote', e=e)
        self.assertEqual((await a.expect('error', ref='kara_vote'))['code'], 'bad')
        await b.send(t='kara_vote', e=e)
        v = await c.expect('kara_votes')
        self.assertEqual((v['n'], v['need']), (1, 2))
        await b.send(t='kara_skip', e=e)                                     # not theirs
        self.assertEqual((await b.expect('error', ref='kara_skip'))['code'], 'bad')
        await c.send(t='kara_vote', e=e)
        self.assertEqual((await a.expect('kara_end'))['why'], 'vote')
        await self.tick(time.time() + lk.SHORT_CLAP + .1)
        e2 = await self.add(b)
        await a.expect('kara_play', e=e2)
        await b.send(t='kara_skip', e=e2)
        self.assertEqual((await c.expect('kara_end', e=e2))['why'], 'skip')
        e3 = await self.add(c)                                               # c queues, then walks away
        await c.call('kara_out', 'kara_left')
        e4 = await self.add(a)
        now = time.time() + lk.SHORT_CLAP + .1
        await self.tick(now)
        await b.expect('kara_play', e=e4)                                    # c is passed over, a sings
        self.assertEqual([x.e for x in self.room().data['queue']], [e3])
        await a.send(t='kara_skip', e=e4)
        await b.expect('kara_end', e=e4)
        await self.tick(now + lk.ABSENT_WAIT + lk.SHORT_CLAP + 1)
        self.assertEqual(self.room().data['queue'], [])                      # c did not come back: dropped
        self.assertIsNone(self.room().data['stage'])


class Crowd(KaraCase):
    async def test_reactions_batched_bubbles_and_blocks(self):
        a, b, c = await self.enter('Lan'), await self.enter('Minh'), await self.enter('Hoa')
        for k in ('❤️', '❤️', '👏'):
            await b.send(t='kara_react', k=k)
        await b.send(t='kara_cheer')
        fx = await a.expect('kara_fx')
        self.assertEqual(fx['r'], {'❤️': 2, '👏': 1})
        self.assertGreater(fx['cheer'], 0)
        await asyncio.sleep(1.05)
        await b.send(t='kara_react', k='💩')
        self.assertEqual((await b.expect('error', ref='kara_react'))['code'], 'bad')
        await c.call('block', 'blocked', pid=a.pid)
        await c.send(t='kara_say', text='hát hay quá, gọi 0912345678 nha')
        said = await b.expect('kara_said')
        self.assertEqual((said['pid'], said['name'], said['text']), (c.pid, 'Hoa', 'hát hay quá, gọi ••• nha'))
        await a.nothing('kara_said')                                         # a blocked by c: never sees it
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT channel FROM chat_messages WHERE id=?', (said['id'],)).fetchone()['channel'], 'kara:tre')
        await b.send(t='report', id=said['id'], reason='spam')               # the chat's report reaches the room's bubbles
        await b.expect('reported')


class Rounds(KaraCase):
    async def test_emoji_round_near_right_prize_reward(self):
        a, b, c = await self.enter('Lan'), await self.enter('Minh'), await self.enter('Hoa')
        await c.call('block', 'blocked', pid=a.pid)
        await a.send(t='kara_round', mode='emoji', clue='🌧️💔🏠', answer='Nơi này có anh / NNCA', vid=f'https://youtu.be/{VID2}')
        rd = (await b.expect('kara_round'))['round']
        self.assertEqual((rd['mode'], rd['clue'], rd['words'], rd['host']['pid'], rd['reward']), ('emoji', '🌧️💔🏠', 4, a.pid, True))
        self.assertNotIn('answer', rd)
        self.assertNotIn('keys', json.dumps(rd))
        await c.nothing('kara_round')                                         # blocked from the host
        await a.send(t='kara_round', mode='emoji', clue='🎵🎵', answer='x y')
        self.assertEqual((await a.expect('error', ref='kara_round'))['code'], 'busy')
        await b.send(t='kara_say', text='em của ngày hôm qua')                # wrong: a bubble everyone sees
        self.assertEqual((await a.expect('kara_said'))['text'], 'em của ngày hôm qua')
        await b.send(t='kara_say', text='nơi này có em')                     # close: only b is told (and a bubble)
        await b.expect('kara_near')
        await a.expect('kara_said')
        await a.nothing('kara_near', wait=.1)
        with patch.object(lk, 'GUESS_MIN_SECS', 0):
            await b.send(t='kara_say', text='NOI NAY CO ANH')
            await b.expect('kara_said', win=1)
        rv = await a.expect('kara_reveal')
        self.assertEqual((rv['answer'], rv['by']['pid'], rv['xu'], rv['why']), ('Nơi này có anh', b.pid, kg.GUESS_XU, 'won'))
        await b.expect('kara_won')
        await a.nothing('kara_said', wait=.1)                                  # the right guess is never shown
        with self.store.connect() as db:
            fx = db.execute("SELECT sid, amount, data FROM live_effects WHERE id LIKE 'kguess:%'").fetchall()
        self.assertEqual([(r['sid'], r['amount'], json.loads(r['data'])['src']) for r in fx], [(b.sid, kg.GUESS_XU, 'kara_guess')])
        rew = await b.expect('kara_play')                                    # the host's link plays as the reward
        self.assertEqual((rew['vid'], rew['by']['pid'], rew['reward']), (VID2, a.pid, 1))

    async def test_caps_timeout_lyric_rules_and_host(self):
        a, b = await self.enter('Lan'), await self.enter('Minh')
        await a.send(t='kara_round', mode='lyric', clue='Em ơi Hà Nội phố', answer='Hà Nội phố')
        self.assertEqual((await a.expect('error', ref='kara_round'))['code'], 'no_blank')
        await a.send(t='kara_round', mode='lyric', clue='một hai ba bốn năm sáu bảy tám chín mười mười một ___ ___', answer='abc')
        self.assertEqual((await a.expect('error', ref='kara_round'))['code'], 'clue_long')
        await a.send(t='kara_round', mode='lyric', clue='Em ơi ___ ___ phố', answer='Hà Nội', vid='https://evil.com/x')
        self.assertEqual((await a.expect('error', ref='kara_round'))['code'], 'song')
        self.fresh(a)
        await a.send(t='kara_round', mode='lyric', clue='Em ơi ___ ___ phố', answer='Hà Nội phố')
        rd = (await b.expect('kara_round'))['round']
        self.assertEqual(rd['clue'], 'Em ơi ___ ___ phố')
        await a.send(t='kara_say', text='hà nội phố')                        # the host's own words: a plain bubble
        await b.expect('kara_said')
        await b.send(t='kara_say', text='Hà Nội phố')                         # too fast (GUESS_MIN_SECS): right, but no xu
        rv = await a.expect('kara_reveal')
        self.assertEqual((rv['by']['pid'], rv['xu']), (b.pid, 0))
        self.fresh(a)
        await a.send(t='kara_round', mode='emoji', clue='🎤🎶', answer='karaoke')
        rd = (await b.expect('kara_round'))['round']
        await self.tick(rd['until'] + .1)                                     # nobody: the answer after the time
        rv = await b.expect('kara_reveal', why='time')
        self.assertEqual((rv['by'], rv['answer']), (None, 'karaoke'))
        self.fresh(a)
        self.app.hub.players[a.pid].ext['kara_round_at'] = time.time()
        await a.send(t='kara_round', mode='emoji', clue='🎤🎶', answer='karaoke')
        self.assertEqual((await a.expect('error', ref='kara_round'))['code'], 'slow')
        self.fresh(a)
        with patch.object(kg, 'GUESS_DAY_CAP', kg.GUESS_XU), patch.object(lk, 'GUESS_MIN_SECS', 0):   # one paid win a day
            for i in range(2):
                self.fresh(a)
                await a.send(t='kara_round', mode='emoji', clue='🌙⭐', answer=f'đêm sao {i}')
                await b.expect('kara_round')
                await b.send(t='kara_say', text=f'dem sao {i}')
                rv = await a.expect('kara_reveal', answer=f'đêm sao {i}')
                self.assertEqual(rv['xu'], kg.GUESS_XU if i == 0 else 0)
        self.fresh(a)
        await a.send(t='kara_round', mode='emoji', clue='🌙⭐', answer='trăng')
        await b.expect('kara_round')
        await a.call('kara_out', 'kara_left')                                 # the host leaves: the round ends
        await b.expect('kara_reveal', why='left')


class Moderation(KaraCase):
    async def test_admin_ban_kick_close_and_reports(self):
        a, b, boss = await self.enter('Lan'), await self.enter('Minh'), await self.enter('Sếp')
        self.admin(boss)
        boss.room = await boss.call('kara_in', 'kara_room', theme='tre')
        self.assertEqual(boss.room['adm'], 1)
        e = await self.add(a)
        await b.expect('kara_play')
        await b.send(t='kara_ban', vid=VID)
        self.assertEqual((await b.expect('error', ref='kara_ban'))['code'], 'admin')
        await b.send(t='kara_report', vid=VID, reason='rude')
        await b.expect('kara_reported')
        await b.send(t='kara_report', pid=a.pid, reason='minor')
        await b.expect('kara_reported')
        with self.store.connect() as db:
            rows = {(r['target'], r['reason']) for r in db.execute("SELECT target, reason FROM reports WHERE kind='kara'").fetchall()}
        self.assertEqual(rows, {('v:' + VID, 'rude'), ('p:' + a.pid, 'minor')})
        await boss.send(t='kara_ban', vid=VID)
        self.assertEqual((await a.expect('kara_end', e=e))['why'], 'admin')
        await boss.expect('kara_banned')
        await self.tick(time.time() + lk.SHORT_CLAP + .1)
        await a.send(t='kara_add', vid=VID, e=self.ticket(a))
        self.assertEqual((await a.expect('error', ref='kara_add'))['code'], 'song')
        await boss.send(t='kara_kick', pid=b.pid)
        self.assertEqual((await b.expect('kara_left'))['why'], 'kick')
        await b.send(t='kara_in', theme='bolero')
        self.assertEqual((await b.expect('error', ref='kara_in'))['code'], 'kicked')
        await boss.send(t='kara_close')
        self.assertEqual((await a.expect('kara_left'))['why'], 'closed')
        await a.send(t='kara_in', id='kara:tre')
        self.assertEqual((await a.expect('error', ref='kara_in'))['code'], 'closed')
        a.room = await a.call('kara_in', 'kara_room', theme='bolero')
        self.assertEqual(a.room['id'], 'kara:bolero')

    async def test_mute_game_admin_acts_and_tips_reach_the_room(self):
        a, b = await self.enter('Lan', theme='qt'), await self.enter('Minh', theme='qt')
        e = await self.add(a)
        await b.expect('kara_play')
        e2 = await self.add(b, VID2)
        await a.expect('kara_q')
        await a.expect('kara_q')
        kg.admin_act(self.store, 'boss', dict(act='mute', pid=b.pid, minutes=10))     # the chat's mute, through NOTIFY
        q = await a.expect('kara_q')
        self.assertEqual(q['queue'], [])
        self.assertNotIn(e2, [x.e for x in self.room('kara:qt').data['queue']])
        await b.send(t='kara_say', text='alo')
        self.assertEqual((await b.expect('error', ref='kara_say'))['code'], 'muted')
        # a tip paid on the game server is announced to the room
        with self.store.connect() as db:
            db.execute('UPDATE kara_tickets SET played=? WHERE id=?', (time.time(), e))
        self.store.transaction(lambda db: kg._notify(db, dict(op='kara_tip', e=e, frm=b.pid, name='Minh', to=a.pid, xu=20, got=16)))
        tipped = await a.expect('kara_tipped')
        self.assertEqual((tipped['xu'], tipped['frm']['name'], tipped['tips']), (20, 'Minh', 20))
        kg.admin_act(self.store, 'boss', dict(act='skip', room='kara:qt'))
        self.assertEqual((await a.expect('kara_end', e=e))['why'], 'admin')
        kg.admin_act(self.store, 'boss', dict(act='close', room='kara:qt'))
        self.assertEqual((await a.expect('kara_left'))['why'], 'closed')
        self.assertNotIn('kara:qt', self.app.hub.rooms)
