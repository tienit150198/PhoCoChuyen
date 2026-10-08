"""🎙️ Phòng hát mic trực tiếp (LIVE_KARAOKE_MIC; live/karaoke.py, live/sfu.py, game/karaoke_mic.py).

With real sockets on a disposable PostgreSQL schema and the SFU's server API replaced by a recorder (the real
LiveKit server is exercised by scripts/browser_live_karaoke_mic.py): only the stage singer gets a publishing token
(microphone only), room members get subscribe-only hidden tokens, the birth-year gate (missing → 'birth', under 16 →
'young', set once), blocks either way get no audio and a block made mid-song removes the listener, every stage change
deletes the SFU room (song end, skip, vote, kick, admin), the 6-minute limit, the admin cut and 3 reports cut it for
the rest of the song, and with the switch off nothing of it exists."""
import time
from unittest.mock import patch

from game import karaoke_mic as km
from live import karaoke as lk
from live.sfu import Sfu, verify
from tests.test_live_karaoke import VID, VID2, KaraCase

KEY, SECRET = 'devkey', 'secret-for-tests-only-0123456789abcdef'


class FakeSfu(Sfu):
    """The real token maker, a recorder for the server API."""

    def __init__(self):
        super().__init__('ws://sfu.test', 'http://127.0.0.1:1', KEY, SECRET)
        self.log, self.live = [], set()

    async def call(self, method, body, room=None):
        self.log.append((method, body))
        if method == 'CreateRoom':
            self.live.add(body['name'])
        elif method == 'DeleteRoom':
            self.live.discard(body['room'])
        elif method == 'ListRooms':
            return dict(rooms=[dict(name=n) for n in sorted(self.live)])
        return {}

    def made(self, method):
        return [b for m, b in self.log if m == method]


class MicCase(KaraCase):
    cfg_extra = dict(kara=True, kara_mic=True, sfu_url='ws://sfu.test', sfu_key=KEY, sfu_secret=SECRET)

    async def asyncSetUp(self):
        with patch.object(lk, 'Sfu', lambda *a, **k: FakeSfu()):
            await super().asyncSetUp()
        self.sfu = self.feat.sfu

    def born(self, c, year, days_old=30):
        with self.store.connect() as db:
            db.execute('INSERT INTO account_birth(sid, year, at) VALUES(?, ?, ?) ON CONFLICT(sid) DO UPDATE SET year=excluded.year', (c.sid, year, time.time()))
            db.execute('UPDATE accounts SET created_at=? WHERE sid=?', (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - days_old * 86400)), c.sid))

    async def singing(self, name='Lan', year=2000):
        """A singer on stage (the song playing) with a birth year, and two listeners."""
        a, b, c = await self.enter(name), await self.enter('Minh'), await self.enter('Hoa')
        self.born(a, year)
        e = await self.add(a)
        for x in (a, b, c):
            await x.expect('kara_play', e=e)
        await self.tick(time.time() + lk.LEAD + 0.1)
        return a, b, c, e

    async def mic_on(self, a):
        await a.send(t='kara_mic', on=1)
        return await a.expect('kara_mic', on=1)


class Tokens(MicCase):
    async def test_singer_publishes_listeners_subscribe(self):
        a, b, c, e = await self.singing()
        self.assertTrue(a.welcome['flags']['kara_mic'])
        got = await self.mic_on(a)
        room = got['room']
        self.assertEqual(self.sfu.made('CreateRoom')[0]['name'], room)
        self.assertEqual(got['url'], 'ws://sfu.test')
        claims = verify(got['token'], SECRET)
        self.assertEqual((claims['sub'], claims['iss']), (a.pid, KEY))
        v = claims['video']
        self.assertEqual((v['room'], v['roomJoin'], v['canPublish'], v['canPublishSources'], v['canSubscribe'], v['canPublishData']),
                         (room, True, True, ['microphone'], False, False))
        for bad in ('roomAdmin', 'roomCreate', 'roomRecord', 'recorder', 'roomList'):
            self.assertNotIn(bad, v)
        self.assertLessEqual(claims['exp'] - time.time(), km.MIC_SECS + 31)
        for x in (a, b, c):   # the notice, for everyone in the room
            live = await x.expect('kara_live', on=1)
            self.assertEqual((live['by']['pid'], live['e']), (a.pid, e))
        lis = await b.call('kara_listen', 'kara_listen')
        self.assertEqual((lis['on'], lis['room']), (1, room))
        lc = verify(lis['token'], SECRET)
        self.assertEqual((lc['sub'], lc['video']['canPublish'], lc['video']['canSubscribe'], lc['video']['hidden'], lc['video']['canPublishSources']),
                         (b.pid, False, True, True, []))
        self.assertLessEqual(lc['exp'] - time.time(), km.LISTEN_TTL + 1)
        self.assertIsNone(verify(lis['token'], 'another-secret'))
        self.assertEqual((await a.call('kara_listen', 'kara_listen'))['on'], 0)   # the singer does not listen to themselves
        # a late joiner sees the mic in the stage
        d = await self.enter('Tú')
        self.assertEqual(d.room['stage']['mic']['on'], 1)

    async def test_only_the_stage_singer(self):
        a, b, c, e = await self.singing()
        self.born(b, 1999)
        await b.send(t='kara_mic', on=1)
        self.assertEqual((await b.expect('error'))['code'], 'stage')
        self.assertEqual(self.sfu.made('CreateRoom'), [])
        g = await self.enter('Khách', account=False)
        await g.send(t='kara_mic', on=1)
        self.assertEqual((await g.expect('error'))['code'], 'stage')
        self.assertEqual((await g.call('kara_listen', 'kara_listen'))['on'], 0)   # nothing on yet
        await self.mic_on(a)
        self.assertEqual((await g.call('kara_listen', 'kara_listen'))['on'], 1)   # guests listen

    async def test_birth_year_gate(self):
        a, b, c = await self.enter('Lan'), await self.enter('Minh'), await self.enter('Hoa')
        with self.store.connect() as db:
            db.execute('UPDATE accounts SET created_at=? WHERE sid=?', ('2026-01-01 00:00:00', a.sid))
        await self.add(a)
        await a.send(t='kara_mic', on=1)
        self.assertEqual((await a.expect('error'))['code'], 'birth')
        young = km.vn_year() - km.MIN_AGE   # might be 15 still this year: listening only
        self.born(a, young)
        await a.send(t='kara_mic', on=1)
        err = await a.expect('error')
        self.assertEqual(err['code'], 'young')
        self.assertIn('16', err['msg'])
        self.assertEqual(self.sfu.made('CreateRoom'), [])
        await a.nothing('kara_live')
        self.born(a, young - 1)
        self.assertEqual((await self.mic_on(a))['on'], 1)

    async def test_new_account_and_muted(self):
        a, b, c, e = await self.singing()
        self.born(a, 1990, days_old=0)
        await a.send(t='kara_mic', on=1)
        self.assertEqual((await a.expect('error'))['code'], 'too_new')

    async def test_switch_off(self):
        self.cfg.kara_mic = False
        a, b, c, e = await self.singing()
        self.assertFalse((await self.connect(self.account('Mai')[0])).welcome['flags']['kara_mic'])
        await a.send(t='kara_mic', on=1)
        self.assertEqual((await a.expect('error'))['code'], 'off')
        self.assertEqual((await b.call('kara_listen', 'kara_listen'))['on'], 0)
        self.assertNotIn('mic', (await b.call('kara_in', 'kara_room', id='kara:tre'))['stage'])
        self.assertEqual([m for m, _ in self.sfu.log if m != 'ListRooms'], [])   # (the start-up sweep of the switched-on setUp)


class Cuts(MicCase):
    async def deleted(self, room):
        for _ in range(50):
            if room in [b['room'] for b in self.sfu.made('DeleteRoom')]:
                return True
            await __import__('asyncio').sleep(0.02)
        return False

    async def test_song_end_cuts_and_next_singer_gets_a_new_room(self):
        a, b, c, e = await self.singing()
        room = (await self.mic_on(a))['room']
        self.born(b, 1995)
        await self.add(b, VID2)
        await a.send(t='kara_skip', e=e)
        off = await c.expect('kara_live', on=0)
        self.assertEqual(off['why'], 'end')
        self.assertTrue(await self.deleted(room))
        await a.send(t='kara_mic', on=1)   # the old singer: not on stage any more
        self.assertEqual((await a.expect('error'))['code'], 'stage')
        await self.tick(time.time() + lk.SHORT_CLAP + 1)
        e2 = (await b.expect('kara_play'))['e']
        await self.tick(time.time() + lk.SHORT_CLAP + lk.LEAD + 2)
        room2 = (await self.mic_on(b))['room']
        self.assertNotEqual(room2, room)
        self.assertEqual(verify((await self.mic_on(b))['token'], SECRET)['video']['room'], room2)   # asked again: the same session
        self.assertEqual(len(self.sfu.made('CreateRoom')), 2)
        self.assertTrue(e2)

    async def test_vote_skip_and_turning_off_and_on(self):
        a, b, c, e = await self.singing()
        r1 = (await self.mic_on(a))['room']
        await a.send(t='kara_mic', on=0)
        await a.expect('kara_mic', on=0)
        self.assertEqual((await b.expect('kara_live', on=0))['why'], 'off')
        self.assertTrue(await self.deleted(r1))
        r2 = (await self.mic_on(a))['room']   # on again within the 6 minutes: a new SFU room
        self.assertNotEqual(r1, r2)
        for x in (b, c):
            await x.send(t='kara_vote', e=e)
        self.assertEqual((await b.expect('kara_live', on=0, e=e))['why'], 'end')
        self.assertTrue(await self.deleted(r2))

    async def test_six_minutes(self):
        a, b, c, e = await self.singing()
        got = await self.mic_on(a)
        await self.tick(got['until'] + 0.5)
        self.assertEqual((await b.expect('kara_live', on=0))['why'], 'time')
        self.assertTrue(await self.deleted(got['room']))
        await a.send(t='kara_mic', on=1)
        self.assertEqual((await a.expect('error'))['code'], 'cut')

    async def test_admin_cut_kick_and_reports(self):
        a, b, c, e = await self.singing()
        self.admin(c)
        room = (await self.mic_on(a))['room']
        await c.send(t='kara_mic_cut')
        self.assertEqual((await b.expect('kara_live', on=0))['why'], 'admin')
        self.assertTrue(await self.deleted(room))
        await a.send(t='kara_mic', on=1)
        self.assertEqual((await a.expect('error'))['code'], 'cut')   # for the rest of the song
        await b.send(t='kara_mic_cut')
        self.assertEqual((await b.expect('error'))['code'], 'admin')

    async def test_admin_site_cut_and_kick(self):
        a, b, c, e = await self.singing()
        room = (await self.mic_on(a))['room']
        await self.feat.on_notify(dict(op='kara', act='mic', room='kara:tre'))
        self.assertEqual((await b.expect('kara_live', on=0))['why'], 'admin')
        self.assertTrue(await self.deleted(room))

    async def test_kick_ends_it(self):
        a, b, c, e = await self.singing()
        room = (await self.mic_on(a))['room']
        await self.feat.on_notify(dict(op='kara', act='kick', pid=a.pid))
        self.assertEqual((await b.expect('kara_live', on=0))['why'], 'end')
        self.assertTrue(await self.deleted(room))

    async def test_three_reports_cut(self):
        a, b, c, e = await self.singing()
        d = await self.enter('Tú')
        room = (await self.mic_on(a))['room']
        for x in (b, c):
            await x.send(t='kara_report', pid=a.pid, reason='rude')
            self.assertEqual((await x.expect('kara_reported'))['target'], 'm:' + a.pid)
        await d.nothing('kara_live', on=0)
        await b.send(t='kara_report', pid=a.pid, reason='rude')   # the same reporter twice counts once
        await b.expect('kara_reported')
        await d.nothing('kara_live', on=0)
        await d.send(t='kara_report', pid=a.pid, reason='minor')
        self.assertEqual((await d.expect('kara_live', on=0))['why'], 'reports')
        self.assertTrue(await self.deleted(room))
        with self.store.connect() as db:
            n = db.execute("SELECT COUNT(*) FROM reports WHERE kind='kara' AND target=?", ('m:' + a.pid,)).fetchone()[0]
        self.assertEqual(n, 3)

    async def test_sweep_on_start(self):
        self.sfu.live.update({'kara-tre.abc.1', 'other'})
        await self.feat._sweep()
        self.assertEqual(self.sfu.live, {'other'})


class Blocks(MicCase):
    async def test_blocked_listener_gets_no_audio(self):
        a, b, c, e = await self.singing()
        await b.send(t='block', pid=a.pid)          # b blocked the singer before the mic
        await b.expect('blocked')
        await self.mic_on(a)
        self.assertEqual((await b.call('kara_listen', 'kara_listen'))['on'], 0)
        self.assertEqual((await c.call('kara_listen', 'kara_listen'))['on'], 1)

    async def test_singer_blocked_the_listener(self):
        a, b, c, e = await self.singing()
        await a.send(t='block', pid=c.pid)
        await a.expect('blocked')
        await self.mic_on(a)
        self.assertEqual((await c.call('kara_listen', 'kara_listen'))['on'], 0)

    async def test_block_mid_song_and_leaving_remove_the_listener(self):
        a, b, c, e = await self.singing()
        room = (await self.mic_on(a))['room']
        self.assertEqual((await b.call('kara_listen', 'kara_listen'))['on'], 1)
        self.assertEqual((await c.call('kara_listen', 'kara_listen'))['on'], 1)
        await b.send(t='block', pid=a.pid)
        await b.expect('blocked')
        await self.tick(time.time())
        self.assertEqual((await b.expect('kara_listen'))['on'], 0)
        self.assertIn(dict(room=room, identity=b.pid), self.sfu.made('RemoveParticipant'))
        await c.send(t='kara_out')
        await c.expect('kara_left')
        for _ in range(50):
            if dict(room=room, identity=c.pid) in self.sfu.made('RemoveParticipant'):
                break
            await __import__('asyncio').sleep(0.02)
        self.assertIn(dict(room=room, identity=c.pid), self.sfu.made('RemoveParticipant'))

    async def test_sfu_down(self):
        a, b, c, e = await self.singing()

        async def down(method, body, room=None):
            return None
        with patch.object(self.sfu, 'call', down):
            await a.send(t='kara_mic', on=1)
            self.assertEqual((await a.expect('error'))['code'], 'sfu')
        await b.nothing('kara_live')
        self.assertEqual((await self.mic_on(a))['on'], 1)   # back up: works


class VideoTime(MicCase):
    """🎙️ kara_vt: the singer's own video time, relayed (stamped) to the mic's listeners only."""

    async def live(self):
        a, b, c, e = await self.singing()
        await self.mic_on(a)
        for x in (b, c):
            self.assertEqual((await x.call('kara_listen', 'kara_listen'))['on'], 1)
        return a, b, c, e

    def again(self, *conns):
        """The next kara_vt may be relayed at once (no VT_GAP, no rate window)."""
        mic = self.room().data['mic']
        mic['vt_at'] = 0.0
        for x in conns:
            self.app.hub.players[x.pid].rates.pop('kara_vt', None)

    async def test_relayed_stamped_to_listeners_of_this_room(self):
        a, b, c, e = await self.live()
        d = await self.enter('Tú')                       # in the room, never asked to listen
        o = await self.enter('Khoa', theme='bolero')     # another room
        t0 = time.time()
        await a.send(t='kara_vt', e=e, vt=1.25, st=t0 - 0.2, rtt=84)
        for x in (b, c):
            f = await x.expect('kara_vt')
            self.assertEqual((f['id'], f['e'], f['vt'], f['rtt']), ('kara:tre', e, 1.25, 84))
            self.assertAlmostEqual(f['at'], t0 - 0.2, delta=0.01)   # the singer's own moment, not the relay's
        await a.nothing('kara_vt')
        await d.nothing('kara_vt', wait=0.05)
        await o.nothing('kara_vt', wait=0.05)
        await a.nothing('error', wait=0.05)                         # no reply to the singer either

    async def test_only_the_live_singer_and_song(self):
        a, b, c, e = await self.singing()
        self.assertEqual((await b.call('kara_listen', 'kara_listen'))['on'], 0)
        await a.send(t='kara_vt', e=e, vt=1.0)                      # the mic is not on yet
        await b.nothing('kara_vt')
        await self.mic_on(a)
        for x in (b, c):
            await x.call('kara_listen', 'kara_listen')
        await b.send(t='kara_vt', e=e, vt=1.0)                      # a listener cannot steer the others
        await c.nothing('kara_vt')
        await a.send(t='kara_vt', e='kq-other', vt=1.0)             # another song's
        await c.nothing('kara_vt')
        await a.send(t='kara_vt', e=e, vt=1.0)
        await c.expect('kara_vt', vt=1.0)
        await a.send(t='kara_mic', on=0)
        await c.expect('kara_live', on=0)
        self.again(a)
        await a.send(t='kara_vt', e=e, vt=2.0)                      # the mic is off again
        await c.nothing('kara_vt', vt=2.0)
        g = await self.enter('Khách', account=False)
        await g.send(t='kara_vt', e=e, vt=1.0)
        await c.nothing('kara_vt', vt=1.0, wait=0.05)

    async def test_sane_numbers(self):
        a, b, c, e = await self.live()
        for vt in ('1.5', None, True, -1, 1e9, 40.0, [1]):          # 40 s: far from the shared clock (VT_SPAN)
            self.again(a)
            await a.send(t='kara_vt', e=e, vt=vt)
        await b.nothing('kara_vt')
        t0 = time.time()
        # at: 'back' = the relay's now − VT_BACK (too old a stamp), 'now' = the relay's now, else the singer's own stamp
        for st, rtt, r, want_at, want_rtt, want_r in ((t0 - 60, -5, 9, 'back', None, None), (t0 + 60, 99999, 1, 'now', None, None),
                                                      ('x', 'x', '1.05', 'now', None, None), (None, 120.7, 1.05, 'now', 120, 1.05),
                                                      (t0, 0, 0.95, t0, 0, 0.95), (t0, None, True, t0, None, None)):
            self.again(a)
            t1 = time.time()
            await a.send(t='kara_vt', e=e, vt=2.0, st=st, rtt=rtt, r=r)
            f = await b.expect('kara_vt')
            t2 = time.time()
            if want_at == 'back':
                self.assertTrue(t1 - lk.VT_BACK - 0.01 <= f['at'] <= t2 - lk.VT_BACK + 0.01, (f['at'], t1, t2))
            elif want_at == 'now':
                self.assertTrue(t1 - 0.01 <= f['at'] <= t2 + 0.01, (f['at'], t1, t2))
            else:
                self.assertAlmostEqual(f['at'], want_at, delta=0.001)
            self.assertEqual((f.get('rtt'), f.get('r')), (want_rtt, want_r))

    async def test_gap_and_rate_limit(self):
        a, b, c, e = await self.live()
        await a.send(t='kara_vt', e=e, vt=1.0)
        await a.send(t='kara_vt', e=e, vt=1.1)                      # within VT_GAP: dropped
        await b.expect('kara_vt', vt=1.0)
        await b.nothing('kara_vt', vt=1.1)
        self.room().data['mic']['vt_at'] = 0.0
        for i in range(4):
            await a.send(t='kara_vt', e=e, vt=2.0 + i)
        err = await a.expect('error')                               # the 5th within 3 s
        self.assertEqual((err['code'], err['ref']), ('slow', 'kara_vt'))

    async def test_blocks_respected(self):
        a, b, c, e = await self.live()
        await c.send(t='block', pid=a.pid)
        await c.expect('blocked')
        await a.send(t='kara_vt', e=e, vt=1.0)                      # before the tick takes c out of the SFU room
        await b.expect('kara_vt', vt=1.0)
        await c.nothing('kara_vt')

    async def test_not_in_a_room(self):
        a, b, c, e = await self.live()
        await a.send(t='kara_out')
        await a.expect('kara_left')
        await a.send(t='kara_vt', e=e, vt=1.0)
        self.assertEqual((await a.expect('error'))['ref'], 'kara_vt')   # the page ignores it (v4/karaoke.js)
        await b.nothing('kara_vt')


class CoSing(MicCase):
    """🎤 Hát cùng (feedback #268): others ask to sing along with the live stage singer, who says yes or no; each
    co-singer gets an SFU room of their own (one publisher a room: every block rule holds per voice)."""

    async def asyncSetUp(self):
        grace = patch.object(lk, 'CO_GRACE', 0.05)   # (the pages' head start before a co room is deleted)
        grace.start()
        self.addCleanup(grace.stop)
        await super().asyncSetUp()

    async def test_the_frame_goes_before_the_room(self):
        """A co-singer's room is deleted CO_GRACE after kara_co on:0: the pages disconnect cleanly first."""
        a, b, c, e, host = await self.live()
        await self.let_in(a, b, e)
        rb = self.co_room(b)
        with patch.object(lk, 'CO_GRACE', 0.4):
            await a.send(t='kara_let', e=e, pid=b.pid, ok=0)
            self.assertEqual((await c.expect('kara_co', on=0, pid=b.pid))['why'], 'kick')
            self.assertNotIn(rb, [x['room'] for x in self.sfu.made('DeleteRoom')])
            self.assertTrue(await self.deleted(rb))

    async def live(self):
        a, b, c, e = await self.singing()
        self.born(b, 1999)
        host = await self.mic_on(a)
        return a, b, c, e, host

    async def let_in(self, a, x, e):
        """x asks, a says yes: x's kara_sing (with the publishing token)."""
        got = await x.call('kara_join', 'kara_join', e=e, on=1)
        self.assertEqual((got['on'], got['ask']), (1, 1))
        ask = await a.expect('kara_ask', on=1, pid=x.pid)
        self.assertEqual(ask['e'], e)
        await a.send(t='kara_let', e=e, pid=x.pid, ok=1)
        return await x.expect('kara_sing', on=1)

    def co_room(self, x):
        return self.room().data['mic']['co'][x.pid]['sfu']

    async def deleted(self, room):
        return await Cuts.deleted(self, room)

    async def test_ask_yes_tokens_and_listening(self):
        a, b, c, e, host = await self.live()
        sing = await self.let_in(a, b, e)
        room = sing['room']
        self.assertNotEqual(room, host['room'])
        self.assertIn(room, self.sfu.live)
        claims = verify(sing['token'], SECRET)
        v = claims['video']
        self.assertEqual((claims['sub'], v['room'], v['canPublish'], v['canPublishSources'], v['canSubscribe'], v['canPublishData']),
                         (b.pid, room, True, ['microphone'], False, False))
        await a.expect('kara_ask', on=0, pid=b.pid)               # the ask is gone from the singer's line
        for x in (a, b, c):                                       # everyone sees who sings along
            co = await x.expect('kara_co', on=1)
            self.assertEqual((co['pid'], co['name'], co['e']), (b.pid, 'Minh', e))
        # listening: each voice its own token; nobody hears themselves
        lc = await c.call('kara_listen', 'kara_listen', pid=b.pid)
        self.assertEqual((lc['on'], lc['pid'], lc['room']), (1, b.pid, room))
        lv = verify(lc['token'], SECRET)['video']
        self.assertEqual((lv['room'], lv['canPublish'], lv['canSubscribe'], lv['hidden']), (room, False, True, True))
        self.assertEqual((await c.call('kara_listen', 'kara_listen'))['room'], host['room'])   # no pid: the stage singer, as before
        self.assertEqual((await b.call('kara_listen', 'kara_listen'))['room'], host['room'])   # the co-singer hears the singer
        self.assertEqual((await a.call('kara_listen', 'kara_listen', pid=b.pid))['room'], room)   # and the singer them
        self.assertEqual((await b.call('kara_listen', 'kara_listen', pid=b.pid))['on'], 0)
        self.assertEqual((await c.call('kara_listen', 'kara_listen', pid='nobody'))['on'], 0)
        # a late comer: the stage lists the co-singers
        d = await self.enter('Tú')
        self.assertEqual(d.room['stage']['mic']['co'], [dict(pid=b.pid, name='Minh')])
        # asked again while on (the page lost the SFU): a fresh token for the same room
        again = await b.call('kara_join', 'kara_join', e=e, on=1)
        self.assertEqual(again['live'], 1)
        self.assertEqual((await b.expect('kara_sing', on=1))['room'], room)
        self.assertEqual(len(self.sfu.made('CreateRoom')), 2)

    async def test_no_kick_and_the_gates(self):
        a, b, c, e, host = await self.live()
        await b.send(t='kara_join', e=e, on=1)
        await a.expect('kara_ask', on=1, pid=b.pid)
        await a.send(t='kara_let', e=e, pid=b.pid, ok=0)
        self.assertEqual((await b.expect('kara_sing', on=0))['why'], 'no')
        await b.send(t='kara_join', e=e, on=1)                    # a "no" holds for the song
        self.assertEqual((await b.expect('error'))['code'], 'no')
        self.born(c, 2001)
        await self.let_in(a, c, e)
        rc = self.co_room(c)
        await a.send(t='kara_let', e=e, pid=c.pid, ok=0)          # the singer turns a co-singer off
        off = await b.expect('kara_co', on=0, pid=c.pid)
        self.assertEqual(off['why'], 'kick')
        self.assertTrue(await self.deleted(rc))
        await c.send(t='kara_join', e=e, on=1)
        self.assertEqual((await c.expect('error'))['code'], 'no')
        # the gates: the singer cannot ask; a guest, a missing birth year, the young; only the singer decides
        await a.send(t='kara_join', e=e, on=1)
        self.assertEqual((await a.expect('error'))['code'], 'bad')
        g = await self.enter('Khách', account=False)
        await g.send(t='kara_join', e=e, on=1)
        self.assertEqual((await g.expect('error'))['code'], 'account')
        d = await self.enter('Tú')
        await d.send(t='kara_join', e=e, on=1)
        self.assertEqual((await d.expect('error'))['code'], 'birth')
        self.born(d, km.vn_year() - km.MIN_AGE + 1)
        await d.send(t='kara_join', e=e, on=1)
        self.assertEqual((await d.expect('error'))['code'], 'young')
        await d.send(t='kara_let', e=e, pid=b.pid, ok=1)
        self.assertEqual((await d.expect('error'))['code'], 'bad')
        await d.send(t='kara_join', e='kq-old', on=1)              # another song's
        self.assertEqual((await d.expect('error'))['code'], 'nolive')
        await a.send(t='kara_let', e=e, pid=d.pid, ok=1)           # nothing asked: nothing to let in
        self.assertEqual((await a.expect('error'))['code'], 'gone')

    async def test_full_and_an_ask_nobody_answers(self):
        a, b, c, e, host = await self.live()
        self.born(c, 1998)
        with patch.object(lk, 'CO_MAX', 1):
            await self.let_in(a, b, e)
            await c.send(t='kara_join', e=e, on=1)
            self.assertEqual((await c.expect('error'))['code'], 'full')
            await b.send(t='kara_join', e=e, on=0)                 # b stops: a place again
            self.assertEqual((await c.expect('kara_co', on=0, pid=b.pid))['why'], 'off')
            self.assertEqual((await c.call('kara_join', 'kara_join', e=e, on=1))['ask'], 1)
        await a.expect('kara_ask', on=1, pid=c.pid)
        await self.tick(time.time() + lk.ASK_SECS + 1)
        self.assertEqual((await c.expect('kara_sing', on=0))['why'], 'time')
        await a.expect('kara_ask', on=0, pid=c.pid)
        self.assertEqual((await c.call('kara_join', 'kara_join', e=e, on=1))['ask'], 1)   # may ask again
        await a.expect('kara_ask', on=1, pid=c.pid)
        await c.send(t='kara_join', e=e, on=0)                     # and withdraw it
        await a.expect('kara_ask', on=0, pid=c.pid)
        await a.send(t='kara_let', e=e, pid=c.pid, ok=1)
        self.assertEqual((await a.expect('error'))['code'], 'gone')

    async def test_the_singer_mic_off_song_end_and_leaving_cut_co_singers(self):
        a, b, c, e, host = await self.live()
        self.born(c, 1998)
        await self.let_in(a, b, e)
        rb = self.co_room(b)
        await a.send(t='kara_mic', on=0)                           # the stage singer's mic off: every co-singer's too
        await c.expect('kara_live', on=0)
        self.assertTrue(await self.deleted(rb))
        self.assertTrue(await self.deleted(host['room']))
        self.assertIsNone(self.feat._session_of(self.room().data['mic'], b.pid))
        await b.send(t='kara_join', e=e, on=1)                     # nothing to sing along with now
        self.assertEqual((await b.expect('error'))['code'], 'nolive')
        await self.mic_on(a)                                       # on again: ask again
        await self.let_in(a, b, e)
        await self.let_in(a, c, e)
        rc = self.co_room(c)
        await c.send(t='kara_out')                                 # a co-singer leaves the room
        self.assertEqual((await b.expect('kara_co', on=0, pid=c.pid))['why'], 'left')
        self.assertTrue(await self.deleted(rc))
        rb = self.co_room(b)
        await a.send(t='kara_skip', e=e)                           # the song ends
        await b.expect('kara_live', on=0)
        self.assertTrue(await self.deleted(rb))

    async def test_blocks_per_voice(self):
        a, b, c, e, host = await self.live()
        d = await self.enter('Tú')
        await d.send(t='block', pid=b.pid)                         # d blocked b before b sings
        await d.expect('blocked')
        await self.let_in(a, b, e)
        rb = self.co_room(b)
        await d.nothing('kara_co', on=1)                           # nothing of b for d …
        self.assertEqual((await d.call('kara_listen', 'kara_listen', pid=b.pid))['on'], 0)
        self.assertEqual((await d.call('kara_listen', 'kara_listen'))['on'], 1)   # … the stage singer still
        self.assertEqual((await c.call('kara_listen', 'kara_listen', pid=b.pid))['on'], 1)
        await c.send(t='block', pid=b.pid)                         # mid-song: c out of b's room only
        await c.expect('blocked')
        await self.tick(time.time())
        self.assertEqual((await c.expect('kara_listen', on=0))['pid'], b.pid)
        self.assertIn(dict(room=rb, identity=c.pid), self.sfu.made('RemoveParticipant'))
        self.assertNotIn(dict(room=host['room'], identity=c.pid), self.sfu.made('RemoveParticipant'))
        await a.send(t='block', pid=b.pid)                         # the singer blocks a co-singer: their mic off for the song
        await a.expect('blocked')
        await self.tick(time.time())
        self.assertEqual((await a.expect('kara_co', on=0, pid=b.pid))['why'], 'block')
        self.assertTrue(await self.deleted(rb))
        await b.send(t='kara_join', e=e, on=1)
        self.assertEqual((await b.expect('error'))['code'], 'no')

    async def test_blocked_by_the_singer_cannot_ask(self):
        a, b, c, e, host = await self.live()
        await a.send(t='block', pid=b.pid)
        await a.expect('blocked')
        await b.send(t='kara_join', e=e, on=1)
        self.assertEqual((await b.expect('error'))['code'], 'no')
        await a.nothing('kara_ask')

    async def test_video_time_relayed_per_voice_with_own_latency(self):
        a, b, c, e, host = await self.live()
        await self.let_in(a, b, e)
        d = await self.enter('Tú')
        for x in (c, b):
            await x.call('kara_listen', 'kara_listen')             # the stage singer's voice
        for x in (c, a):
            await x.call('kara_listen', 'kara_listen', pid=b.pid)  # b's voice (d never asks)
        t0 = time.time()
        await b.send(t='kara_vt', e=e, vt=1.5, st=t0, rtt=90, ol=180)
        for x in (c, a):
            f = await x.expect('kara_cvt')
            self.assertEqual((f['pid'], f['e'], f['vt'], f['rtt'], f['ol']), (b.pid, e, 1.5, 90, 180))
        await d.nothing('kara_cvt', wait=0.05)
        await b.nothing('kara_cvt', wait=0.05)
        await a.send(t='kara_vt', e=e, vt=1.6, ol=5000)            # a nonsense latency is dropped, the rest relayed
        for x in (c, b):
            f = await x.expect('kara_vt')
            self.assertEqual((f['pid'], f['vt'], f.get('ol')), (a.pid, 1.6, None))
        await c.send(t='kara_vt', e=e, vt=1.6)                     # a listener steers nothing
        await a.nothing('kara_cvt', wait=0.05)

    async def test_reports_cut_a_co_singer(self):
        a, b, c, e, host = await self.live()
        await self.let_in(a, b, e)
        rb = self.co_room(b)
        d, f = await self.enter('Tú'), await self.enter('Khoa')
        for x in (c, d, f):
            await x.send(t='kara_report', pid=b.pid, reason='rude')
            self.assertEqual((await x.expect('kara_reported'))['target'], 'm:' + b.pid)
        self.assertEqual((await a.expect('kara_co', on=0, pid=b.pid))['why'], 'reports')
        self.assertTrue(await self.deleted(rb))
        self.assertIn(host['room'], self.sfu.live)                 # the stage singer sings on

    async def test_admin_cut_and_mute(self):
        a, b, c, e, host = await self.live()
        await self.let_in(a, b, e)
        rb = self.co_room(b)
        await self.feat.on_notify(dict(op='mute', pid=b.pid, until=time.time() + 600))
        self.assertEqual((await a.expect('kara_co', on=0, pid=b.pid))['why'], 'admin')
        self.assertTrue(await self.deleted(rb))
        self.born(c, 1998)
        await self.let_in(a, c, e)
        rc = self.co_room(c)
        await self.feat.on_notify(dict(op='kara', act='mic', room='kara:tre'))   # the admin site's cut: every voice
        await b.expect('kara_live', on=0)
        self.assertTrue(await self.deleted(rc))

    async def test_switch_off(self):
        self.cfg.kara_mic = False
        a, b, c, e = await self.singing()
        await b.send(t='kara_join', e=e, on=1)
        self.assertEqual((await b.expect('error'))['code'], 'off')
