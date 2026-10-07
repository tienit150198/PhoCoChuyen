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
