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
    def counted(self, wid, n, ok=1, steps=WL.GUEST_MIN_MINUTES, first=0):
        with self.store.connect() as db:
            for i in range(first, first + n):
                db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,?,1,?,?,?,?)',
                           (wid, f'guest{i:04d}', f'p{i:015d}', ok, steps, time.time(), 'd', 'w'))

    async def test_scaling_title_cap_and_once(self):
        for n, want, title in ((9, 135, False), (19, 285, False), (25, 375, True), (370, 5400, True)):
            (ta, tb), (sa, sb), wid, at = self.party(wid=100 + n)
            self.counted(wid, n)
            self.counted(wid + 1000, 3)                     # another party's guests
            self.counted(wid, 4, steps=1, first=5000)       # stayed under 2 minutes: not counted (owner, 01/10)
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
        await asyncio.sleep(0.3)
        with self.store.connect() as db:   # stayed the whole party (the ticks between are skipped here)
            db.execute('UPDATE wedding_guests SET steps=? WHERE wedding=? AND sid=?', (WL.PARTY_MINUTES, wid, gs))
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
                    db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,1,1,2,?,?,?)',
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



@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Feast(WedCase):
    """1.3.0: the mâm cỗ (+1 tinh thần a dish, 3 a party; −1 a beer, 2 a party; a soft drink is just fun), the bouquet."""

    def fx(self, like):
        return self.rows('SELECT id, kind, amount FROM live_effects WHERE id LIKE ? ORDER BY id', like)

    async def test_dishes_and_beer_capped_with_fixed_ids(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        gt, gs = self.account('Bảo')
        g = await self.join(gt, wid)
        got = [await g.call('wed_eat', 'wed_ate', k='dish', d=i) for i in range(4)]
        self.assertEqual([(r['n'], r['left']) for r in got], [(1, 2), (1, 1), (1, 0), (0, 0)])
        seen = await bride.expect('wed_eat')
        self.assertEqual((seen['pid'], seen['k'], seen['d']), (g.welcome['me']['pid'], 'dish', 0), 'the room sees who ate what')
        beers = [await g.call('wed_eat', 'wed_ate', k='beer') for _ in range(3)]
        self.assertEqual([(r['n'], r['left']) for r in beers], [(-1, 1), (-1, 0), (0, 0)])
        soda = await g.call('wed_eat', 'wed_ate', k='soda')
        self.assertEqual((soda['n'], soda['left']), (0, None))
        k = gs[:24]
        self.assertEqual(self.fx('weat:%'), [dict(id=f'weat:{wid}:{k}:{i}', kind='spirit', amount=1) for i in (1, 2, 3)])
        self.assertEqual(self.fx('wbeer:%'), [dict(id=f'wbeer:{wid}:{k}:{i}', kind='spirit', amount=-1) for i in (1, 2)])
        self.assertEqual((await g.call('wed_eat', 'error', k='dish'))['code'], 'slow', '8 taps in 10 seconds')

    async def test_a_restart_never_pays_twice_and_the_rules(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        gt, gs = self.account('Hà Vy')
        with self.store.connect() as db:   # paid before a restart of the service
            db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?, ?, 'spirit', 1, '{}', 'applied', ?)",
                       (f'weat:{wid}:{gs[:24]}:1', gs, time.time()))
        g = await self.join(gt, wid)
        self.assertEqual(g.room['wed']['eat'], dict(dish=WL.EAT_MAX, beer=WL.BEER_MAX))
        r = await g.call('wed_eat', 'wed_ate', k='dish', d=2)
        self.assertEqual((r['n'], r['left']), (1, 1), 'slot 1 was taken: slot 2')
        self.wed.parties[wid].pop('eats')                       # a new process: read back by primary key
        r = await g.call('wed_eat', 'wed_ate', k='dish', d=3)
        self.assertEqual((r['n'], r['left']), (1, 0))
        r = await g.call('wed_eat', 'wed_ate', k='dish', d=3)
        self.assertEqual(r['n'], 0)
        self.assertEqual(len(self.fx('weat:%')), 3)
        self.assertEqual((await g.call('wed_eat', 'error', k='dish', d=99))['code'], 'bad')
        self.assertEqual((await g.call('wed_eat', 'error', k='cake'))['code'], 'bad')
        stranger = await self.connect(self.account('Người Ngoài')[0])   # not in the party
        self.assertEqual((await stranger.call('wed_eat', 'error', k='dish', d=0))['code'], 'not_in')
        await self.wed.tick(at + WL.PARTY_SECS + 1)             # the party is over
        await asyncio.sleep(0.3)
        self.assertEqual((await g.call('wed_eat', 'error', k='beer'))['code'], 'over')
        self.assertEqual(self.fx('wbeer:%'), [])

    async def test_bouquet_once_to_a_guest_present(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        groom = await self.join(tb, wid, g='male')
        guests = [await self.join(self.account(n)[0], wid) for n in ('Một', 'Hai', 'Ba')]
        pids = {c.welcome['me']['pid'] for c in guests}
        self.assertEqual((await guests[0].call('wed_toss', 'error'))['code'], 'bad', 'only the couple throws it')
        self.assertEqual((await bride.call('wed_toss', 'error'))['code'], 'early')
        await self.wed.tick(at + WL.TOSS_AT)
        op = await guests[1].expect('wed_toss_open')
        self.assertAlmostEqual(op['until'], at + WL.TOSS_AT + WL.TOSS_WAIT, delta=1)
        late = await self.join(self.account('Bốn')[0], wid)
        self.assertTrue(late.room['wed']['toss']['open'], 'a late guest sees the button state')
        pids.add(late.welcome['me']['pid'])
        await bride.send(t='wed_toss')
        t = await groom.expect('wed_toss')
        self.assertEqual(t['by'], bride.welcome['me']['pid'])
        self.assertIn(t['pid'], pids, 'a guest present catches it, never the couple')
        self.assertEqual(t['xu'], WL.TOSS_XU)
        rows = self.rows("SELECT sid, kind, amount FROM live_effects WHERE id=?", f'wtoss:{wid}')
        self.assertEqual([(r['kind'], r['amount']) for r in rows], [('coins', WL.TOSS_XU)])
        self.assertEqual(self.pid(rows[0]['sid']), t['pid'])
        self.assertEqual((await groom.call('wed_toss', 'error'))['code'], 'done')
        await bride.expect('wed_toss_open')
        self.wed.parties[wid].pop('toss_state')                # a restart: caught already, never opened again
        await self.wed.tick(at + WL.TOSS_AT + 5)
        await asyncio.sleep(0.3)
        await bride.nothing('wed_toss_open')
        self.assertEqual(self.wed.parties[wid]['toss_state'], 'done')

    async def test_bouquet_thrown_for_the_couple(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        g = await self.join(self.account('Bảo')[0], wid)
        await self.wed.tick(at + WL.TOSS_AT + 1)
        await g.expect('wed_toss_open')
        await self.wed.tick(at + WL.TOSS_AT + WL.TOSS_WAIT + 2)
        t = await g.expect('wed_toss')
        self.assertEqual((t['by'], t['pid'], t['xu']), (bride.welcome['me']['pid'], g.welcome['me']['pid'], WL.TOSS_XU))
        await self.wed.tick(at + WL.TOSS_AT + WL.TOSS_WAIT + 5)
        await g.nothing('wed_toss')
        self.assertEqual(len(self.rows("SELECT id FROM live_effects WHERE id LIKE 'wtoss:%'")), 1)

    async def test_dance_emote(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        g = await self.join(self.account('Bảo')[0], wid)
        await g.send(t='emote', e='dance')
        self.assertEqual((await bride.expect('emoted'))['e'], 'dance')


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Music(WedCase):
    """1.3.0 follow-up: the groom picks the music (the bride when he is away), once every MUSIC_GAP seconds a party."""

    def gap(self, wid):
        self.wed.parties[wid]['music']['at'] -= WL.MUSIC_GAP   # MUSIC_GAP seconds later

    async def test_the_groom_picks_and_everyone_hears_it(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        groom = await self.join(tb, wid, g='male')
        guest = await self.join(self.account('Bảo')[0], wid, g='male')
        self.assertIsNone(guest.room['wed']['music'], 'the programme until someone picks')
        self.assertEqual(guest.room['wed']['musics'], list(WL.MUSIC))
        self.assertEqual((await guest.call('wed_music', 'error', k='edm'))['code'], 'bad', 'a guest never picks')
        self.assertEqual((await bride.call('wed_music', 'error', k='edm'))['code'], 'bad', 'the groom is here: his pick')
        self.assertEqual((await groom.call('wed_music', 'error', k='j97'))['code'], 'bad', 'only the list')
        self.assertEqual((await groom.call('wed_music', 'error', k=None))['code'], 'bad')
        t0 = time.time()
        await groom.send(t='wed_music', k='edm')
        m = await guest.expect('wed_music')
        self.assertEqual((m['k'], m['by'], m['who'], m['name']), ('edm', groom.welcome['me']['pid'], 'groom', 'Minh Tú'))
        self.assertAlmostEqual(m['at'], t0, delta=2)
        self.assertEqual((await bride.expect('wed_music'))['k'], 'edm', 'the whole room, the same switch time')
        slow = await groom.call('wed_music', 'error', k='love')
        self.assertEqual(slow['code'], 'slow', f'once every {WL.MUSIC_GAP} s')
        late = await self.join(self.account('Hà Vy')[0], wid)
        self.assertEqual((late.room['wed']['music']['k'], late.room['wed']['music']['at']), ('edm', m['at']), 'a late guest joins the song')
        self.gap(wid)
        await groom.send(t='wed_music', k='auto')
        self.assertEqual((await late.expect('wed_music'))['k'], 'auto', 'back to the programme')

    async def test_the_bride_picks_when_the_groom_is_away(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        bride = await self.join(ta, wid)
        guest = await self.join(self.account('Bảo')[0], wid, g='male')
        await bride.send(t='wed_music', k='funk')
        m = await guest.expect('wed_music')
        self.assertEqual((m['k'], m['who']), ('funk', 'bride'))
        groom = await self.join(tb, wid, g='male')
        self.gap(wid)
        self.assertEqual((await bride.call('wed_music', 'error', k='love'))['code'], 'bad', 'he came: his pick now')
        await groom.send(t='wed_music', k='love')
        self.assertEqual((await guest.expect('wed_music'))['who'], 'groom')
        await groom.call('walk_out', 'walk_left')
        self.gap(wid)
        await bride.send(t='wed_music', k='disco')
        self.assertEqual((await guest.expect('wed_music'))['k'], 'disco', 'he left: the bride again')
        await self.wed.tick(at + WL.PARTY_SECS + 1)
        await asyncio.sleep(0.3)
        self.gap(wid)
        self.assertEqual((await bride.call('wed_music', 'error', k='edm'))['code'], 'over')

    async def test_two_brides_or_two_grooms_both_pick(self):
        (ta, tb), (sa, sb), wid, at = self.party()
        a = await self.join(ta, wid)
        b = await self.join(tb, wid)                       # both characters are women
        await b.send(t='wed_music', k='remix')
        self.assertEqual((await a.expect('wed_music'))['who'], 'couple')
        await b.expect('wed_music')                        # her own pick comes back too
        self.gap(wid)
        await a.send(t='wed_music', k='latin')
        self.assertEqual((await b.expect('wed_music'))['k'], 'latin')


if __name__ == '__main__':
    unittest.main()
