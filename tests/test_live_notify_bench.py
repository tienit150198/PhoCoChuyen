"""🔔 Notifications per chat (feedback #66: groups get web pushes now; "🔔 Thông báo: Bật / Tắt 8 giờ / Tắt" per DM or
group, chat_members.muted_until) and 💕 shorter waits on the dating bench (feedback #64: who waits / came lately, the
busiest hours, "📣 Rủ mọi người" on Cả phố with its limits, a neighbour NPC after a while alone)."""
import asyncio
import time
import unittest
from unittest.mock import patch

from live import chat as lc, dating as dt
from tests.live_support import HAVE_WS, LiveCase


class PureTests(unittest.TestCase):
    def test_hot_hours(self):
        h = [0] * 24
        self.assertIsNone(dt.hot_hours(h))
        h[20], h[21], h[9] = 2, 2, 3
        self.assertEqual(dt.hot_hours(h), [20, 22])
        h = [0] * 24
        h[23], h[0] = 3, 3                      # across midnight
        self.assertEqual(dt.hot_hours(h), [23, 1])
        self.assertIsNone(dt.hot_hours([1] * 4 + [0] * 20))
        self.assertEqual(dt.hour_of(0), 7)      # Vietnam time

    def test_recent(self):
        r = dt.Recent(window=60, cap=3)
        r.put('a', 0)
        r.put('b', 10)
        r.put('a', 50)                          # again: counted once, kept by the newer time
        self.assertEqual(r.count(55), 2)
        self.assertEqual(r.count(75), 1)        # b's 10 is out, a's 50 is in
        self.assertEqual(r.count(200), 0)
        for x in 'cdef':
            r.put(x, 300)
        self.assertEqual(r.count(300), 3)       # saturates at cap


def subscribe(store, sid):
    with store.connect() as db:
        db.execute('INSERT INTO push_subs(endpoint, sid, created, prefs) VALUES(?, ?, ?, ?)',
                   (f'https://fcm.googleapis.com/{sid[:8]}', sid, time.time(), '{"social": true}'))


def pushes(store, sid):
    with store.connect() as db:
        return [r[0] for r in db.execute("SELECT body FROM push_queue WHERE sid=? AND kind='chat' ORDER BY id", (sid,)).fetchall()]


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class NotifyTests(LiveCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        (self.ta, self.sa), (self.tb, self.sb), (self.tc, self.sc) = self.account('An'), self.account('Bình'), self.account('Chi')
        self.pa, self.pb, self.pc = (self.pid(s) for s in (self.sa, self.sb, self.sc))
        for s in (self.sb, self.sc):
            self.befriend(self.sa, s)
            subscribe(self.store, s)

    def reset_push(self):
        with self.store.connect() as db:
            db.execute('DELETE FROM push_queue')
            db.execute('UPDATE chat_members SET pushed_at=0')
        self.app.chat.push_tried.clear()

    async def send(self, c, ch, text, cid):
        await c.send(t='send', ch=ch, text=text, cid=cid)
        await c.expect('msg', cid=cid)
        await asyncio.sleep(0.3)   # the push task

    async def test_groups_push_and_a_quiet_chat_does_not(self):
        a = await self.connect(self.ta)
        await a.send(t='group_new', title='Hội bàn bên', pids=[self.pb, self.pc], cid='g')
        ch = (await a.expect('chan', open=True))['chan']['id']
        await self.send(a, ch, 'tối nay đi chợ đêm không', 'm1')
        self.assertEqual(pushes(self.store, self.sb), ['Hội bàn bên · An: tối nay đi chợ đêm không'])
        self.assertEqual(len(pushes(self.store, self.sc)), 1)
        await self.send(a, ch, 'trả lời đi', 'm2')               # one push per chat per 10 minutes
        self.assertEqual(len(pushes(self.store, self.sb)), 1)
        # Chi turns this group off
        c = await self.connect(self.tc)
        q = await c.call('notify', 'quiet', ch=ch, v='off')
        self.assertEqual((q['ch'], q['until']), (ch, round(lc.QUIET_FOREVER)))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT muted_until FROM chat_members WHERE channel=? AND pid=?', (ch, self.pc)).fetchone()[0], lc.QUIET_FOREVER)
        s = await c.call('sync', 'state')
        self.assertEqual(next(x for x in s['chans'] if x['id'] == ch)['quiet'], round(lc.QUIET_FOREVER))
        await c.close()
        await asyncio.sleep(0.5)                                  # offline (presence grace)
        self.reset_push()
        await self.send(a, ch, 'Chi ơi', 'm3')
        self.assertEqual(len(pushes(self.store, self.sb)), 1)
        self.assertEqual(pushes(self.store, self.sc), [])         # quiet
        # the database says no too (another process, a stale cache)
        self.app.chat.chans.pop(ch, None)
        self.reset_push()
        from live.push import maybe_push
        self.assertFalse(await maybe_push(self.app.db, ch, self.pc, self.sc, 'x', '/', 600))
        self.assertTrue(await maybe_push(self.app.db, ch, self.pb, self.sb, 'x', '/', 600))
        # 8 hours, then on again
        c = await self.connect(self.tc)
        q = await c.call('notify', 'quiet', ch=ch, v='8h')
        self.assertAlmostEqual(q['until'], time.time() + 8 * 3600, delta=5)
        q = await c.call('notify', 'quiet', ch=ch, v='on')
        self.assertEqual(q['until'], 0)
        s = await c.call('sync', 'state')
        self.assertNotIn('quiet', next(x for x in s['chans'] if x['id'] == ch))
        await c.close()
        await asyncio.sleep(0.5)
        self.reset_push()
        await self.send(a, ch, 'bật lại rồi nè', 'm4')
        self.assertEqual(len(pushes(self.store, self.sc)), 1)

    async def test_dm_quiet_and_bad_requests(self):
        a, b = await self.connect(self.ta), await self.connect(self.tb)
        await a.send(t='send', to=self.pb, text='chào', cid='1')
        dm = (await a.expect('msg', cid='1'))['ch']
        await b.expect('msg')
        b2 = await self.connect(self.tb)                          # every tab of mine hears it
        await b.send(t='notify', ch=dm, v='off')
        for x in (b, b2):
            self.assertEqual((await x.expect('quiet', ch=dm))['until'], round(lc.QUIET_FOREVER))
        stranger = await self.connect(self.account('Lạ')[0])
        for cid, frame in (('x', dict(ch=dm, v='off')), ('t', dict(ch='town', v='off')), ('v', dict(ch=dm, v='mute'))):
            who = stranger if cid == 'x' else b
            await who.send(t='notify', cid=cid, **frame)
            self.assertEqual((await who.expect('error', ref=cid))['code'], 'no_chat' if cid == 'x' else 'bad')
        for x in (b, b2):
            await x.close()
        await asyncio.sleep(0.5)
        self.reset_push()
        await self.send(a, dm, 'có đó không', '2')
        self.assertEqual(pushes(self.store, self.sb), [])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class BenchTests(LiveCase):
    cfg_extra = dict(dating=True)

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.feat = self.app.by_name['dating']

    async def sit(self, c, pref='m', g='f'):
        await c.send(t='queue', op='sit', pref=pref, g=g)
        return await c.expect('bench', state='wait')

    async def test_counts_and_hot_hours(self):
        a = await self.connect(self.account('Lan Anh')[0])
        idle = await a.call('queue', 'bench', op='peek')
        self.assertEqual((idle['state'], idle['n'], idle['recent'], idle['hot']), ('idle', 0, 0, None))
        w = await self.sit(a)
        self.assertEqual((w['n'], w['recent'], w['call']), (1, 1, 0))
        self.assertNotIn('npc', w)
        b = await self.connect(self.account('Mai')[0])
        await self.sit(b)                                     # also wants a boy: no match, two on the bench
        f = await a.expect('bench', n=2, timeout=6)           # told when the count changes
        self.assertEqual(f['state'], 'wait')
        await b.call('queue', 'bench', op='stand')
        p = await (await self.connect(self.account('Ghé')[0])).call('queue', 'bench', op='peek')
        self.assertEqual((p['n'], p['recent']), (1, 2))       # Mai came lately
        # the busiest hours come from the dates of the last 7 days (read at start)
        t = time.time()
        base = t - (dt.hour_of(t) - 20) % 24 * 3600 - 86400   # some time at 20h (Vietnam), yesterday or so
        with self.store.connect() as db:
            for i in range(6):
                db.execute('INSERT INTO live_dates(id, a, b, a_sid, b_sid, at) VALUES(?, ?, ?, ?, ?, ?)',
                           (f'{i:012x}', f'{i:016x}', f'{i + 1:016x}', 'x', 'y', base + i * 60))
        await self.app.stop()
        from live.app import App
        self.app = App(self.cfg)
        await self.app.start()
        self.port = self.app.port()
        c = await self.connect(self.account('Sau')[0])
        self.assertEqual((await c.call('queue', 'bench', op='peek'))['hot'], [20, 22])

    async def test_call_the_street(self):
        ta, sa = self.account('Lan Anh')
        a = await self.connect(ta)
        await a.send(t='date_call', cid='early')
        self.assertEqual((await a.expect('error', ref='early'))['code'], 'sit')
        await self.sit(a)
        await a.send(t='date_call', cid='empty')
        self.assertEqual((await a.expect('error', ref='empty'))['code'], 'empty')   # nobody on Cả phố: nothing used up
        b = await self.connect(self.account('Bình')[0])
        blocker = await self.connect(self.account('Không Ưa')[0])
        for c in (b, blocker):
            await c.call('join', 'joined', ch='town')
        await blocker.call('block', 'blocked', pid=self.pid(sa))
        out = await a.call('date_call', 'called')
        self.assertEqual((out['n'], out['wait']), (1, dt.CALL_EVERY))
        f = await b.expect('call')
        self.assertEqual((f['ch'], f['kind'], f['name'], f['pid']), ('town', 'date', 'Lan Anh', self.pid(sa)))
        await blocker.nothing('call')
        bench = await a.expect('bench', state='wait')
        self.assertGreater(bench['call'], dt.CALL_EVERY - 5)
        await a.send(t='date_call', cid='again')
        e = await a.expect('error', ref='again')
        self.assertEqual(e['code'], 'slow')
        self.assertGreater(e['wait'], dt.CALL_EVERY - 5)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0], 0)   # nothing stored
        # the whole street: CALL_MAX_HOUR an hour
        d = await self.connect(self.account('Dũng')[0])
        await self.sit(d, pref='f', g='f')
        with patch.object(dt, 'CALL_MAX_HOUR', 1):
            await d.send(t='date_call', cid='street')
            e = await d.expect('error', ref='street')
            self.assertEqual(e['code'], 'busy')
            self.assertGreater(e['wait'], 3500)
            self.assertGreater((await d.call('queue', 'bench', op='peek'))['call'], 3500)
        # muted players do not call
        tm, sm = self.account('Ồn Ào')
        with self.store.connect() as db:
            db.execute('INSERT INTO chat_mutes(pid, until, by_admin, reason, at) VALUES(?, ?, ?, ?, ?)',
                       (self.pid(sm), time.time() + 3600, 'admin', '', time.time()))
        m = await self.connect(tm)
        await self.sit(m, pref='any', g=None)
        await m.send(t='date_call', cid='mute')
        self.assertEqual((await m.expect('error', ref='mute'))['code'], 'muted')

    async def test_a_neighbour_keeps_company_until_a_match(self):
        self.cfg.date_speed = 40                              # NPC_AFTER / 40 = 3 s
        a = await self.connect(self.account('Lan Anh')[0])
        await self.sit(a, pref='m', g='f')
        for _ in range(10):
            f = await a.expect('bench', state='wait', timeout=10)
            if 'npc' in f:
                break
        self.assertIn(f.get('npc'), range(dt.NPCS))
        self.assertGreaterEqual(f['waited'], dt.NPC_AFTER / 40 - 0.1)
        again = await a.call('queue', 'bench', op='peek')
        self.assertEqual(again['npc'], f['npc'])              # the same neighbour stays
        b = await self.connect(self.account('Huy')[0])
        await self.sit(b, pref='f', g='m')
        self.assertEqual((await a.expect('date', step='hello'))['peer']['name'], 'Huy')   # a real player: the date


if __name__ == '__main__':
    unittest.main()
