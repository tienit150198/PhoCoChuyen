"""💍 Live wedding parties (live/wedding.py): the schedule, the room's window, the couple on the stage, the 60-visible cap
and the watchers, attendance (5-minute steps, at most 4, 2 weddings a day), the anti-abuse rules, the couple's reward
scaling (capped at 50 guests, the title at 20), the group photo, the reminder, the weekly race settle (ties, once) and
its titles on name tags, and the end of the party. Real sockets against a real game database."""
import asyncio
import json
import time
import unittest
from unittest.mock import patch

from game import wedding_live as WL
from tests.live_support import HAVE_WS, LiveCase

LOOK = dict(hair='toc_bob', shade='mau_hong', skin='da_trung', top='ao_dai', bottom='vay_dai', shoes='giay_do', acc='no_toc')


class WedCase(LiveCase):
    cfg_extra = dict(street=True, wedding=True)

    @property
    def wed(self):
        return self.app.by_name['wedding']

    def party(self, at_in=60.0, wid=7):
        """A booked party (as game/marriage.py confirms one) between two accounts; returns (tokens, sids, wid, at)."""
        ta, sa = self.account('Lan Anh')
        tb, sb = self.account('Minh Tú')
        at = time.time() + at_in
        with self.store.connect() as db:
            db.execute('INSERT INTO couples(id, a, b, status, since) VALUES(?, ?, ?, ?, ?)', (wid, sa, sb, 'engaged', time.time()))
            db.execute("INSERT INTO wedding_parties(wedding, couple, a, b, at, status, created) VALUES(?, ?, ?, ?, ?, 'booked', ?)",
                       (wid, wid, sa, sb, at, time.time()))
        return (ta, tb), (sa, sb), wid, at

    async def join(self, token, wid, g='female'):
        c = await self.connect(token)
        c.room = await c.call('wed_in', 'walk_room', id=wid, look=LOOK, g=g, title='st_local')
        return c

    async def ticks(self, start: float, secs: float, step: float = 5.0):
        """Simulated time: one tick every `step` seconds of party time."""
        t = start
        self.wed.last = t
        while t < start + secs:
            t += step
            await self.wed.tick(t)
        await asyncio.sleep(0.3)
        return t

    def rows(self, sql, *args):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args).fetchall()]


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Room(WedCase):
    async def test_schedule_window_stage_and_bubbles(self):
        (ta, tb), (sa, sb), wid, at = self.party(at_in=WL.OPEN_BEFORE + 120)
        g = await self.connect(self.guest('Hà Vy')[0])
        lst = await g.call('wed_list', 'wed_list')
        self.assertEqual([(p['id'], p['a'], p['b'], p['open']) for p in lst['parties']], [(wid, 'Lan Anh', 'Minh Tú', False)])
        self.assertEqual((await g.call('wed_in', 'error', id=wid))['code'], 'early')
        at = time.time() + 60                                         # the room is open now (10 minutes before)
        with self.store.connect() as db:
            db.execute('UPDATE wedding_parties SET at=? WHERE wedding=?', (at, wid))
        await self.wed.refresh(time.time())
        bride = await self.join(ta, wid)
        w = bride.room['wed']
        self.assertEqual((w['a'], w['b'], w['overflow']), ('Lan Anh', 'Minh Tú', False))
        me = bride.room['people'][0]
        self.assertEqual(me['ti'], '💍 Cô dâu')
        self.assertLess(me['p'][-1][1], 300, 'the couple stands on the stage')
        guest = await self.join(self.guest('Bảo')[0], wid)
        self.assertEqual(len(guest.room['people']), 2)
        self.assertEqual(guest.room['place'], 'wedding')
        await guest.send(t='say', text='Chúc mừng hạnh phúc nha 🎉 zalo 0912345678')
        said = await bride.expect('said')
        self.assertEqual(said['ch'], f'wed:{wid}')
        self.assertNotIn('0912', said['text'])
        await guest.send(t='emote', e='heart')
        await bride.expect('emoted')
        self.assertEqual((await guest.call('invite', 'error', pid=bride.welcome['me']['pid']))['code'], 'bad', 'no coffee from a wedding')
        lst = await g.call('wed_list', 'wed_list')
        self.assertEqual((lst['parties'][0]['open'], lst['parties'][0]['n']), (True, 2))

    async def test_visible_cap_and_watchers_still_count(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        with patch.object(WL, 'VISIBLE', 2):
            a = await self.join(self.guest('Một')[0], wid)
            b = await self.join(self.guest('Hai')[0], wid)
            c = await self.join(self.guest('Ba')[0], wid)
            groom = await self.join(tb, wid, g='male')     # the couple always gets in
        self.assertFalse(b.room['wed']['overflow'])
        self.assertTrue(c.room['wed']['overflow'])
        self.assertFalse(groom.room['wed']['overflow'])
        self.assertEqual(groom.room['people'][-1]['ti'] if groom.room['people'][-1]['pid'] == groom.welcome['me']['pid'] else '💍 Chú rể', '💍 Chú rể')
        await a.send(t='say', text='đông vui quá')
        await c.expect('said')                              # watchers see and hear the party
        self.assertEqual((await c.call('say', 'error', text='cho mình vào với'))['code'], 'not_in')
        await self.ticks(time.time(), WL.GUEST_STEP + 5)
        counted = {r['sid'] for r in self.rows('SELECT sid FROM wedding_guests WHERE wedding=?', wid)}
        self.assertEqual(len(counted), 3, 'the watcher is counted too; the couple never')
        self.assertNotIn(sb, counted)
        await c.call('walk_out', 'walk_left')
        self.assertNotIn(c.welcome['me']['pid'], self.app.hub.rooms[f'wed:{wid}'].data['watch'])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Attendance(WedCase):
    async def test_steps_of_five_minutes_at_most_four(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        tok, sid = self.guest('Hà Vy')
        g = await self.join(tok, wid)
        g2 = await self.connect(tok)                        # a second tab of the same account
        await g2.call('wed_in', 'walk_room', id=wid, look=LOOK)
        await self.ticks(time.time(), 3 * WL.GUEST_STEP - 10)
        coins = self.rows("SELECT id, amount FROM live_effects WHERE sid=? AND kind='coins' ORDER BY id", sid)
        self.assertEqual([r['amount'] for r in coins], [15, 15])
        close = self.rows("SELECT data FROM live_effects WHERE sid=? AND kind='closeness'", sid)
        self.assertEqual(sorted(json.loads(r['data'])['with'] for r in close), sorted([sa, sb]))
        xu = await g2.expect('wed_xu')
        self.assertEqual(xu['n'], 15)
        await self.ticks(time.time(), 6 * WL.GUEST_STEP)
        coins = self.rows("SELECT amount FROM live_effects WHERE sid=? AND kind='coins'", sid)
        self.assertEqual(len(coins), WL.GUEST_STEPS, '60 xu at most per wedding')
        r = self.rows('SELECT ok, paid, steps FROM wedding_guests WHERE wedding=?', wid)
        self.assertEqual(r, [dict(ok=1, paid=1, steps=4)])

    async def test_two_weddings_a_day_and_the_anti_abuse_rules(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        tok, sid = self.guest('Hà Vy')
        day, week = WL.vn_day(time.time()), WL.vn_week(time.time())
        with self.store.connect() as db:
            for other in (1, 2):
                db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,1,1,4,?,?,?)',
                           (other, sid, 'x', time.time(), day, week))
        await self.join(tok, wid)
        await self.join(self.guest('Bé Mới', old=False)[0], wid)    # a brand-new save: present, never counted
        await self.join(self.guest(None)[0], wid)                   # no name yet: never counted
        await self.join(ta, wid)                                    # the bride: never her own guest
        await self.ticks(time.time(), WL.GUEST_STEP + 5)
        rows = {r['sid']: r for r in self.rows('SELECT sid, ok, paid FROM wedding_guests WHERE wedding=?', wid)}
        self.assertEqual((rows[sid]['ok'], rows[sid]['paid']), (1, 0), 'counted for the couple and the race, no coins (3rd wedding today)')
        self.assertEqual(sorted(r['ok'] for r in rows.values()), [0, 0, 1])
        self.assertNotIn(sa, rows)
        self.assertEqual(self.rows("SELECT * FROM live_effects WHERE sid=? AND id LIKE 'wedg:%'", sid), [])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Hosts(WedCase):
    def counted(self, wid, n, ok=1):
        with self.store.connect() as db:
            for i in range(n):
                db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,?,1,1,?,?,?)',
                           (wid, f'guest{i:04d}', f'p{i:015d}', ok, time.time(), 'd', 'w'))

    async def test_scaling_title_cap_and_once(self):
        for n, want, title in ((9, 270, False), (12, 460, False), (25, 1100, True), (70, 1850, True)):
            (ta, tb), (sa, sb), wid, at = self.party(wid=100 + n)
            self.counted(wid, n)
            self.counted(wid + 1000, 3)                     # another party's guests
            await self.wed.refresh(time.time())
            p = self.wed.parties[wid]
            self.assertEqual(await self.wed.settle_party(p), min(n, 50))
            await self.wed.settle_party(p)
            for s in (sa, sb):
                coins = self.rows("SELECT amount, data FROM live_effects WHERE sid=? AND kind='coins'", s)
                self.assertEqual([c['amount'] for c in coins], [want], (n, coins))
                self.assertIn('popup', json.loads(coins[0]['data']))
                titles = self.rows("SELECT data FROM live_effects WHERE sid=? AND kind='title'", s)
                self.assertEqual(bool(titles), title)
            self.assertEqual(self.rows('SELECT status, guests FROM wedding_parties WHERE wedding=?', wid), [dict(status='done', guests=min(n, 50))])
            with self.store.connect() as db:
                db.execute('DELETE FROM live_effects')

    async def test_the_end_of_the_party(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        guest = await self.join(self.guest('Bảo')[0], wid)
        await self.wed.refresh(time.time())
        await self.wed.tick(at + 1)
        await guest.expect('wed_start')
        await self.wed.tick(at + WL.PARTY_SECS + 1)
        await asyncio.sleep(0.3)
        await guest.expect('wed_end')
        await self.wed.tick(at + WL.PARTY_SECS + 200)
        self.assertEqual((await guest.expect('walk_left'))['why'], 'wed_end')
        self.assertNotIn(f'wed:{wid}', self.app.hub.rooms)
        self.assertEqual((await guest.call('wed_in', 'error', id=wid, look=LOOK))['code'], 'gone')
        del bride


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class PhotoAndReminder(WedCase):
    async def test_group_photo(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        guest = await self.join(self.guest('Bảo')[0], wid)
        await guest.send(t='wed_photo')
        shot = await bride.expect('wed_photo')
        self.assertEqual((shot['n'], shot['pid']), (1, guest.welcome['me']['pid']))
        self.assertEqual((await bride.call('wed_photo', 'error'))['code'], 'slow')
        with patch('live.wedding.PHOTO_GAP', 0):
            for _ in range(2):
                await bride.send(t='wed_photo')
                await guest.expect('wed_photo')
            self.assertEqual((await guest.call('wed_photo', 'error'))['code'], 'full')
        self.assertEqual([r['n'] for r in self.rows('SELECT n FROM wedding_photos WHERE wedding=? ORDER BY n', wid)], [1, 2, 3])

    async def test_the_reminder_once(self):
        (ta, tb), (sa, sb), wid, at = self.party(at_in=20 * 60)
        f1, s1 = self.account('Bạn Một')
        self.befriend(sa, s1)
        with self.store.connect() as db:
            db.execute("INSERT INTO marriage_people(sid, code, created, updated) VALUES(?, 'PCC-ABCDEF', 1, 1)", (s1,))
            db.execute("INSERT INTO push_subs(endpoint, sid, created, prefs) VALUES('https://push.example/1', ?, 1, '{}')", (s1,))
        await self.wed.refresh(time.time())
        await self.wed.refresh(time.time())
        notice = self.rows('SELECT notice FROM marriage_people WHERE sid=?', s1)[0]['notice']
        self.assertIn('Lan Anh và Minh Tú', notice)
        self.assertEqual(len(self.rows("SELECT * FROM push_queue WHERE sid=? AND kind='wedding'", s1)), 1)
        self.assertIsNotNone(self.rows('SELECT reminded FROM wedding_parties WHERE wedding=?', wid)[0]['reminded'])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class WeeklyRace(WedCase):
    async def test_ties_settled_once_and_worn_on_name_tags(self):
        t = time.time()
        prev_start = WL.week_start(t) - 7 * 86400
        week = WL.vn_week(prev_start + 3600)
        plan = (('An', [100, 900]), ('Bình', [200, 300]), ('Chi', [50]), ('Dũng', [60]))
        toks = {name: self.guest(name) for name, _ in plan}
        with self.store.connect() as db:
            for name, times in plan:
                sid = toks[name][1]
                for i, dt in enumerate(times):
                    db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,1,1,1,?,?,?)',
                               (500 + i, sid, self.pid(sid), prev_start + dt, 'd', week))
        await self.wed._race(t)
        await self.wed._race(t)
        top = json.loads(self.rows('SELECT top FROM wedding_race WHERE week=?', week)[0]['top'])
        names = {v[1]: k for k, v in toks.items()}
        self.assertEqual([(names[r['sid']], r['n'], r['title']) for r in top], [('Bình', 2, 'w_vip'), ('An', 2, 'w_pro'), ('Chi', 1, 'w_pro')])
        rows = self.rows("SELECT id, sid, amount FROM live_effects WHERE kind='coins' ORDER BY id")
        self.assertEqual([(names[r['sid']], r['amount']) for r in rows], [('Bình', 300), ('An', 150), ('Chi', 150)])
        await self.wed.settle_week(week)
        self.assertEqual(len(self.rows("SELECT id FROM live_effects WHERE kind='coins'")), 3, 'paid once')
        c = await self.connect(toks['Bình'][0])
        room = await c.call('walk_in', 'walk_room', place='boho', look=LOOK, title='st_local')
        self.assertEqual(room['people'][0]['ti'], '🥇 Khách quý của phố')


if __name__ == '__main__':
    unittest.main()
