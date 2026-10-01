"""💍 Live wedding parties (live/wedding.py): the schedule, the room's window, the couple on the stage, the 60-visible cap
and the watchers, attendance (everyone recorded on entry, 20 xu for every minute present, 2 paid weddings a day, a
restart loses nothing), the anti-abuse rules, the couple's 15 xu a guest (the title at 20), the group photo, the
reminder, the weekly race settle (ties, once) and its titles on name tags, and the end of the party. Real sockets
against a real game database."""
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
        guest = await self.join(self.account('Bảo')[0], wid)          # only accounts talk (1.0.1)
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
            a = await self.join(self.account('Một')[0], wid)
            b = await self.join(self.account('Hai')[0], wid)
            c = await self.join(self.account('Ba')[0], wid)
            groom = await self.join(tb, wid, g='male')     # the couple always gets in
            tg, sg = self.guest('Khách Lâu Năm')              # named, long-time, but no account: watches, never counts
            g = await self.join(tg, wid)
        self.assertFalse(b.room['wed']['overflow'])
        self.assertEqual(c.room['wed']['overflow'], 'full')
        self.assertEqual(g.room['wed']['overflow'], 'account')
        self.assertEqual((await g.call('wed_photo', 'error'))['code'], 'not_in')
        self.assertFalse(groom.room['wed']['overflow'])
        self.assertEqual(groom.room['people'][-1]['ti'] if groom.room['people'][-1]['pid'] == groom.welcome['me']['pid'] else '💍 Chú rể', '💍 Chú rể')
        await a.send(t='say', text='đông vui quá')
        await c.expect('said')                              # watchers see and hear the party
        self.assertEqual((await c.call('say', 'error', text='cho mình vào với'))['code'], 'not_in')
        await asyncio.sleep(0.3)
        counted = {r['sid'] for r in self.rows('SELECT sid FROM wedding_guests WHERE wedding=?', wid)}
        ok = {r['sid'] for r in self.rows('SELECT sid FROM wedding_guests WHERE wedding=? AND ok=1', wid)}
        self.assertEqual(len(counted), 4, 'everyone who walked in is recorded at once, the gate too')
        self.assertEqual(len(ok), 3, 'the full-house watcher is counted too; the couple and a player without an account never')
        self.assertNotIn(sb, counted)
        self.assertIn(sg, counted)
        self.assertNotIn(sg, ok)
        await self.ticks(at - 1, 62)
        self.assertEqual(self.rows("SELECT * FROM live_effects WHERE sid=?", sg), [])
        self.assertEqual(len(self.rows("SELECT * FROM live_effects WHERE kind='coins' AND id LIKE 'wedm:%'")), 4, '3 guests and the groom')
        self.assertEqual((await g.expect('wed_xu'))['why'], 'account')
        await c.call('walk_out', 'walk_left')
        self.assertNotIn(c.welcome['me']['pid'], self.app.hub.rooms[f'wed:{wid}'].data['watch'])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Attendance(WedCase):
    async def test_recorded_on_entry_and_paid_every_minute(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        tok, sid = self.account('Hà Vy')
        g = await self.join(tok, wid)
        g2 = await self.connect(tok)                        # a second tab of the same account
        await g2.call('wed_in', 'walk_room', id=wid, look=LOOK)
        bride = await self.join(ta, wid)
        etok, esid = self.account('Ghé Qua')
        early = await self.join(etok, wid)
        await asyncio.sleep(0.3)
        self.assertEqual(self.rows('SELECT ok, paid, steps FROM wedding_guests WHERE wedding=? AND sid=?', wid, sid), [dict(ok=1, paid=0, steps=0)],
                         'recorded the moment they walk in')
        await self.ticks(at - 30, 30 + 90)                  # the party starts, and someone leaves after a minute and a half
        await early.call('walk_out', 'walk_left')
        await self.ticks(at + 90, 3 * 60)                   # four minutes in
        coins = self.rows("SELECT id, amount FROM live_effects WHERE sid=? AND kind='coins' ORDER BY id", sid)
        self.assertEqual([r['amount'] for r in coins], [WL.MINUTE_XU] * 4)
        self.assertEqual(len(self.rows("SELECT id FROM live_effects WHERE sid=? AND kind='coins'", sa)), 4, 'the couple are paid too')
        self.assertEqual(len(self.rows("SELECT id FROM live_effects WHERE sid=? AND kind='coins'", esid)), 2, 'only the minutes present')
        close = self.rows("SELECT data FROM live_effects WHERE sid=? AND kind='closeness'", sid)
        self.assertEqual(sorted(json.loads(r['data'])['with'] for r in close), sorted([sa, sb]))
        xu = await g2.expect('wed_xu')
        self.assertEqual((xu['n'], xu['max']), (WL.MINUTE_XU, WL.PARTY_MINUTES))
        await self.ticks(at + 270, WL.PARTY_SECS)
        for _ in range(30):   # the last minute is paid by a task: a loaded machine needs more than the ticks' 0.3 s
            coins = self.rows("SELECT amount FROM live_effects WHERE sid=? AND kind='coins' AND id LIKE 'wedm:%'", sid)
            if len(coins) >= WL.PARTY_MINUTES:
                break
            await asyncio.sleep(0.1)
        self.assertEqual(len(coins), WL.PARTY_MINUTES, '20 xu a minute, 10 minutes')
        r = self.rows('SELECT ok, paid, steps FROM wedding_guests WHERE wedding=? AND sid=?', wid, sid)
        self.assertEqual(r, [dict(ok=1, paid=1, steps=WL.PARTY_MINUTES)])
        del bride

    async def test_a_restart_of_the_service_loses_nothing(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        tok, sid = self.account('Hà Vy')
        await self.join(tok, wid)
        await self.ticks(at - 5, 5 + 125)                   # minutes 1 and 2 paid
        self.wed.att.clear()                                # a new process: nothing in memory
        for p in self.wed.parties.values():
            p.pop('minute', None)
        g = await self.join(tok, wid)                       # the socket walks back in
        await asyncio.sleep(0.3)
        await self.ticks(at + 125, 60)
        coins = self.rows("SELECT id FROM live_effects WHERE sid=? AND kind='coins' ORDER BY id", sid)
        self.assertEqual(len(coins), 3)
        self.assertEqual(self.rows('SELECT paid, steps FROM wedding_guests WHERE wedding=? AND sid=?', wid, sid), [dict(paid=1, steps=3)])
        self.assertEqual(g.room['wed']['minutes'], WL.PARTY_MINUTES)

    async def test_two_paid_weddings_a_day_and_the_anti_abuse_rules(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        tok, sid = self.account('Hà Vy')
        day, week = WL.vn_day(time.time()), WL.vn_week(time.time())
        with self.store.connect() as db:
            for other in (1, 2):
                db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,1,1,4,?,?,?)',
                           (other, sid, 'x', time.time(), day, week))
        g = await self.join(tok, wid)
        await self.join(self.account('Bé Mới', old=False)[0], wid)  # a brand-new account: counted now (owner, 01/10)
        await self.join(self.guest('Lâu Năm')[0], wid)              # no account: watches, recorded, never counted
        await self.join(self.guest(None)[0], wid)                   # no name, no account: never counted
        await self.join(ta, wid)                                    # the bride: never her own guest
        await self.ticks(at - 1, 62)
        rows = {r['sid']: r for r in self.rows('SELECT sid, ok, paid, steps FROM wedding_guests WHERE wedding=?', wid)}
        self.assertEqual((rows[sid]['ok'], rows[sid]['paid'], rows[sid]['steps']), (1, 0, 1), 'counted for the couple and the race, no coins (3rd today)')
        self.assertEqual(sorted(r['ok'] for r in rows.values()), [0, 0, 1, 1])
        self.assertNotIn(sa, rows)
        self.assertEqual(self.rows("SELECT * FROM live_effects WHERE sid=? AND id LIKE 'wedm:%'", sid), [])
        self.assertEqual((await g.expect('wed_xu'))['why'], 'cap')


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Hosts(WedCase):
    def counted(self, wid, n, ok=1):
        with self.store.connect() as db:
            for i in range(n):
                db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,?,1,1,?,?,?)',
                           (wid, f'guest{i:04d}', f'p{i:015d}', ok, time.time(), 'd', 'w'))

    async def test_scaling_title_cap_and_once(self):
        for n, want, title in ((9, 135, False), (19, 285, False), (25, 375, True), (370, 5400, True)):
            (ta, tb), (sa, sb), wid, at = self.party(wid=100 + n)
            self.counted(wid, n)
            self.counted(wid + 1000, 3)                     # another party's guests
            await self.wed.refresh(time.time())
            p = self.wed.parties[wid]
            self.assertEqual(await self.wed.settle_party(p), min(n, WL.HOST_COUNT_MAX))
            await self.wed.settle_party(p)
            for s in (sa, sb):
                coins = self.rows("SELECT amount, data FROM live_effects WHERE sid=? AND kind='coins'", s)
                self.assertEqual(sum(c['amount'] for c in coins), want, (n, coins))
                self.assertLessEqual(max(c['amount'] for c in coins), 2000)
                self.assertEqual(sum('popup' in json.loads(c['data']) for c in coins), 1)
                titles = self.rows("SELECT data FROM live_effects WHERE sid=? AND kind='title'", s)
                self.assertEqual(bool(titles), title)
            self.assertEqual(self.rows('SELECT status, guests FROM wedding_parties WHERE wedding=?', wid), [dict(status='done', guests=min(n, WL.HOST_COUNT_MAX))])
            with self.store.connect() as db:
                db.execute('DELETE FROM live_effects')

    async def test_the_end_of_the_party(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        guest = await self.join(self.account('Bảo')[0], wid)
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
class Envelope(WedCase):
    def given(self, sid, wid, rid, amount, wish, couple):
        """What POST /api/marriage/envelope writes (game/wedding_live.py envelope): the debit and the two halves."""
        with self.store.connect() as db:
            db.execute("INSERT INTO marriage_effects(id, sid, kind, amount, label, data, status, due, at, applied_at) VALUES(?, ?, 'wallet', ?, '', ?, 'applied', 0, ?, ?)",
                       (f'wenv:{wid}:{rid}', sid, -amount, json.dumps(dict(wedding=wid, wish=wish)), time.time(), time.time()))
            for side, s in zip('ab', couple):
                db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?, ?, 'coins', ?, '{}', 'pending', ?)",
                           (f'wedenv:{wid}:{side}:{rid}', s, amount // 2, time.time()))

    async def test_the_room_hears_it_once_and_the_couple_card_sums_it(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        gt, gs = self.account('Bảo')
        guest = await self.join(gt, wid)
        self.assertEqual((guest.room['wed']['envs'], guest.room['wed']['env_max']), (list(WL.ENVELOPES), WL.ENVELOPE_MAX))
        self.given(gs, wid, 'rid-abc-0001', 100, 1, (sa, sb))
        await guest.send(t='wed_env', rid='rid-abc-0001')
        e = await bride.expect('wed_env')
        self.assertEqual((e['n'], e['name'], e['text'], e['pid']), (100, 'Bảo', WL.WISHES[1], guest.welcome['me']['pid']))
        await guest.send(t='wed_env', rid='rid-abc-0001')                  # told once
        await bride.nothing('wed_env')
        self.given(gs, wid, 'rid-abc-0002', 10, 0, (sa, sb))
        self.assertEqual((await bride.call('wed_env', 'error', rid='rid-abc-0002'))['code'], 'bad', "not the bride's envelope")
        self.assertEqual((await guest.call('wed_env', 'error', rid='rid-none-0001'))['code'], 'bad', 'no such envelope')
        await self.wed.refresh(time.time())
        await self.wed.tick(at + 1)
        await self.wed.tick(at + WL.PARTY_SECS + 1)
        await asyncio.sleep(0.3)
        for s in (sa, sb):
            card = [json.loads(r['data'])['popup']['text'] for r in self.rows("SELECT data FROM live_effects WHERE sid=? AND id LIKE 'wedhost:%'", s)]
            self.assertIn('🧧 Phong bì khách mừng: 55 xu', card[0])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class PhotoAndReminder(WedCase):
    async def test_group_photo(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        guest = await self.join(self.account('Bảo')[0], wid)
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
        toks = {name: self.account(name) for name, _ in plan}
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
        # The race title leads; what the player wears follows by its emoji (1.2: several worn at once).
        self.assertEqual(room['people'][0]['ti'], '🥇 Khách quý của phố 🏮')


if __name__ == '__main__':
    unittest.main()
