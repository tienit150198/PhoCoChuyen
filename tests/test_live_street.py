"""🚶 Đi dạo (live/street.py): places and instances, moves (clamped, routed, rate limited, batched, never in the
database), bubbles through the chat's store (filters, mutes, delete, report), emotes, the tám chuyện tables,
happenings (capped) and the red envelope (paid once, daily cap), blocks, cards and coffee for two. Real sockets
against a real game database (SQLite here, PostgreSQL with TEST_DATABASE_URL)."""
import asyncio
import math
import time
import unittest

from live import street_data as sd
from live.street import CAP, ENVELOPE_CAP, GEO, HAPPEN_GAP, SPEED, clean_look, pos_at
from tests.live_support import HAVE_WS, LiveCase

LOOK = dict(hair='toc_bob', shade='mau_hong', skin='da_trung', top='ao_hoodie', bottom='quan_jean', shoes='giay_trang', acc='kinh_tron')


class Data(unittest.TestCase):
    def test_ids_match_the_game(self):
        from game import journey, wardrobe
        ids = {}
        for it in wardrobe.ITEMS:
            ids.setdefault(it['slot'], []).append(it['id'])
        self.assertEqual({k: tuple(v) for k, v in ids.items()}, sd.LOOK_IDS)
        for g in ('male', 'female', None):
            want = {k: v for k, v in wardrobe.DEFAULTS[g].items() if k in sd.LOOK_SLOTS}
            self.assertEqual(want, sd.LOOK_DEFAULTS[g])
        for tid, text in sd.TITLES.items():   # every title shown exists in the game with the same words
            t = journey.TITLE_INDEX[tid]
            self.assertEqual(text, f"{t['emoji']} {t['name']}")

    def test_topics_and_vendors(self):
        self.assertGreaterEqual(len(sd.TOPICS), 60)
        self.assertEqual(len(set(sd.TOPICS)), len(sd.TOPICS))
        self.assertTrue(all(5 < len(t) <= 90 for t in sd.TOPICS))
        self.assertEqual(set(sd.VENDORS), set(sd.PUBLIC))

    def test_geometry_of_every_place(self):
        import random
        rnd = random.Random(7)
        for pid, g in GEO.items():
            for t in g.tables:
                self.assertTrue(all(g.inside(*s) for s in t['seats']), pid)
                self.assertIn(t['n'], (2, 3, 4))
            for k, s in g.spots.items():
                self.assertTrue(g.inside(*s), (pid, k))
            for _ in range(300):   # any two walkable points are joined by a walkable path
                a = g.clamp(rnd.uniform(0, 600), rnd.uniform(0, 900))
                b = g.clamp(rnd.uniform(0, 600), rnd.uniform(0, 900))
                path = g.route(a, b)
                self.assertEqual(path[-1], list(b), (pid, a, b))
                for p, q in zip(path, path[1:]):
                    self.assertTrue(g.seg_ok(p, q), (pid, p, q))

    def test_clamp_route_and_interpolation(self):
        g = GEO['boho']
        self.assertEqual(g.clamp(300, 420), (300.0, 515.0))     # in the lake: the nearest shore
        path = g.route((50, 300), (550, 300))                   # left of the lake to its right: around it
        self.assertGreater(len(path), 2)
        self.assertTrue(all(g.seg_ok(p, q) for p, q in zip(path, path[1:])))
        self.assertEqual(pos_at([[0, 0], [170, 0]], 100.0, 100.5), (85.0, 0.0))
        self.assertEqual(pos_at([[0, 0], [170, 0]], 100.0, 109.0), (170, 0))
        self.assertEqual(SPEED, 170.0)

    def test_look_validation(self):
        look, g = clean_look(dict(LOOK, hair='toc_unknown', uniform=True), 'female')
        self.assertEqual(look['hair'], 'toc_bui')                # unknown id: the gender's default
        self.assertEqual(look['top'], 'ao_hoodie')
        self.assertEqual(clean_look(None, 'robot'), (sd.LOOK_DEFAULTS[None], None))
        from live.protocol import LiveError
        for bad in ('x', dict(wings='big'), dict(hair=5), dict(hair='x' * 30), {f'k{i}': 'a' for i in range(20)}):
            with self.assertRaises(LiveError):
                clean_look(bad, 'male')


class StreetCase(LiveCase):
    cfg_extra = dict(street=True)

    @property
    def street(self):
        return self.app.by_name['street']

    async def walker(self, name, place='boho', look=LOOK, g='female', title='st_local', token=None):
        tok = token or self.account(name)[0]   # only accounts talk (owner, 01/10); guests are tested apart
        c = await self.connect(tok)
        c.room = await c.call('walk_in', 'walk_room', place=place, look=look, g=g, title=title)
        return c

    @staticmethod
    async def ev(c, k, timeout=3.0, **match):
        """The first queued diff event of kind k (and fields equal to `match`), removed from its frame."""
        end = time.monotonic() + timeout
        while True:
            for f in c.frames:
                if f.get('t') == 'walk':
                    for e in f['ev']:
                        if e.get('k') == k and all(e.get(x) == v for x, v in match.items()):
                            f['ev'].remove(e)
                            return e
            if time.monotonic() > end:
                raise AssertionError(f'no {k} {match} in {[f for f in c.frames if f.get("t") == "walk"]}')
            await asyncio.sleep(0.02)

    def room(self, rid):
        return self.app.hub.rooms.get(rid)


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Instances(StreetCase):
    async def test_join_snapshot_and_others(self):
        a = await self.walker('Lan Anh')
        r = a.room
        self.assertEqual((r['place'], r['room'], r['name']), ('boho', 'walk:boho:1', 'Bờ hồ'))
        me = r['people'][0]
        self.assertEqual((me['name'], me['ti'], me['lk']['top'], me['g']), ('Lan Anh', '🏮 Người của khu phố', 'ao_hoodie', 'female'))
        self.assertTrue(GEO['boho'].inside(*me['p'][-1]))
        b = await self.walker('Minh Tú', g='male', title='nope')
        self.assertEqual(b.room['room'], 'walk:boho:1')
        self.assertEqual({p['name'] for p in b.room['people']}, {'Lan Anh', 'Minh Tú'})
        self.assertIsNone([p for p in b.room['people'] if p['name'] == 'Minh Tú'][0]['ti'])   # unknown title: none
        came = await self.ev(a, 'in', name='Minh Tú')
        self.assertEqual(came['pid'], b.welcome['me']['pid'])
        await b.call('walk_out', 'walk_left')
        self.assertEqual((await self.ev(a, 'out'))['pid'], b.welcome['me']['pid'])
        await b.call('walk_in', 'walk_room', place='chodem', look=LOOK)
        places = {p['id']: p['n'] for p in (await a.call('walk_places', 'walk_places'))['places']}
        self.assertEqual(places, dict(boho=1, chodem=1, congvien=0, phodibo=0))
        await a.close()
        await b.close()
        await asyncio.sleep(0.1)
        self.assertEqual([r for r in self.app.hub.rooms if r.startswith('walk:')], [], 'empty rooms are dropped')

    async def test_capacity_and_the_fullest_instance(self):
        clients = [await self.walker(f'Người {i}') for i in range(CAP)]
        self.assertTrue(all(c.room['room'] == 'walk:boho:1' for c in clients))
        extra = await self.walker('Người thứ 21')
        self.assertEqual(extra.room['room'], 'walk:boho:2')
        more = await self.walker('Người thứ 22')
        self.assertEqual(more.room['room'], 'walk:boho:2')
        await clients[0].call('walk_out', 'walk_left')
        late = await self.walker('Người đến sau')   # room 1 has 19, room 2 has 2: the fullest with room
        self.assertEqual(late.room['room'], 'walk:boho:1')
        self.assertEqual(len(self.room('walk:boho:1').data['people']), CAP)

    async def test_a_second_tab_takes_the_first_out(self):
        tok, _ = self.guest('Hai Tab')
        a = await self.walker('Hai Tab', token=tok)
        b = await self.connect(tok)
        await b.call('walk_in', 'walk_room', place='congvien', look=LOOK)
        self.assertEqual((await a.expect('walk_left'))['why'], 'other')
        self.assertIsNone(self.room('walk:boho:1'))


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Moves(StreetCase):
    async def test_clamped_routed_batched_and_rate_limited(self):
        a = await self.walker('Lan Anh')
        b = await self.walker('Minh Tú')
        await self.ev(a, 'in')
        pa = a.welcome['me']['pid']
        await a.send(t='move', x=300, y=420)                     # into the lake
        mv = await self.ev(b, 'mv', pid=pa)
        g = GEO['boho']
        self.assertEqual(mv['p'][-1], [300.0, 515.0])
        self.assertTrue(all(g.seg_ok(p, q) for p, q in zip(mv['p'], mv['p'][1:])))
        self.assertAlmostEqual(mv['at'], time.time(), delta=2)
        await asyncio.sleep(1.05)
        # four moves inside one flush window: the room gets only the last one
        for x in (100, 200, 400, 500):
            await a.send(t='move', x=x, y=700)
        await asyncio.sleep(0.4)
        last = [e for f in b.frames if f.get('t') == 'walk' for e in f['ev'] if e['k'] == 'mv' and e['pid'] == pa]
        self.assertEqual(last[-1]['p'][-1], [500.0, 700.0])
        self.assertLessEqual(len(last), 2)
        # a fifth move within the second: refused (4 per second)
        err = await a.call('move', 'error', x=1, y=1)
        self.assertEqual(err['code'], 'slow')
        for bad in (dict(x='1', y=2), dict(x=None, y=2)):
            await asyncio.sleep(1.05)
            self.assertEqual((await a.call('move', 'error', **bad))['code'], 'bad')

    async def test_moves_never_touch_the_database_and_diffs_stay_under_10_per_second(self):
        clients = [await self.walker(f'Đi {i}') for i in range(6)]
        watcher = clients[0]
        await asyncio.sleep(0.3)
        db = self.app.db
        calls = []
        orig_run, orig_tx = db._run, db.transaction

        async def run(*a, **k):
            calls.append(a[0])
            return await orig_run(*a, **k)

        async def tx(*a, **k):
            calls.append('tx')
            return await orig_tx(*a, **k)
        db._run, db.transaction = run, tx
        watcher.frames.clear()
        t0 = time.monotonic()
        for step in range(8):                                    # 5 players × 4 moves per second for 2 s
            for i, c in enumerate(clients[1:]):
                await c.send(t='move', x=60 + step * 50 + i * 5, y=600 + i * 30)
            await asyncio.sleep(0.25)
        await asyncio.sleep(0.2)
        span = time.monotonic() - t0
        db._run, db.transaction = orig_run, orig_tx
        self.assertEqual(calls, [], 'moves never touch the database')
        walks = [f for f in watcher.frames if f.get('t') == 'walk']
        self.assertGreater(len(walks), 5)
        self.assertLessEqual(len(walks), math.ceil(span * 10) + 1, f'{len(walks)} diffs in {span:.2f}s')
        self.assertFalse([f for f in watcher.frames if f.get('t') == 'error'])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Talking(StreetCase):
    async def test_bubbles_filters_delete_report(self):
        a = await self.walker('Lan Anh')
        b = await self.walker('Minh Tú')
        c = await self.walker('Hà Vy')
        pa = a.welcome['me']['pid']
        await a.send(t='say', text='zalo mình 0912 345 678 nha vl 😆')
        said = await b.expect('said', pid=pa)
        self.assertEqual(said['ch'], 'walk:boho:1')
        self.assertNotIn('0912', said['text'])
        self.assertIn('vl', said['text'])                          # GenZ slang stays
        mine = await a.expect('said', pid=pa)
        with self.store.connect() as db:
            row = db.execute('SELECT channel, text FROM chat_messages WHERE id=?', (said['id'],)).fetchone()
        self.assertEqual(row['channel'], 'walk:boho:1')
        self.assertEqual(mine['id'], said['id'])
        self.assertEqual((await a.call('say', 'error', text='')) ['code'], 'text')
        self.assertEqual((await a.call('say', 'error', text='zalo mình 0912 345 678 nha vl 😆'))['code'], 'dup')
        # report it twice more → hidden for everyone (3 distinct reports)
        await b.call('report', 'reported', id=said['id'], reason='private')
        await c.call('report', 'reported', id=said['id'], reason='spam')
        d = await self.walker('Bảo')
        await d.call('report', 'reported', id=said['id'], reason='spam')
        hid = await b.expect('deleted', id=said['id'])
        self.assertEqual(hid.get('hidden'), 1)
        # an author's own delete
        await a.send(t='say', text='lát ra chợ đêm nha')
        s2 = await b.expect('said', pid=pa)
        await a.send(t='del', id=s2['id'])
        self.assertEqual((await c.expect('deleted', id=s2['id']))['ch'], 'walk:boho:1')
        # someone who was never in this room cannot report it
        far = await self.walker('Xa lạ', place='congvien')
        self.assertEqual((await far.call('report', 'error', id=s2['id'], reason='spam'))['code'], 'no_chat')

    async def test_guests_stroll_and_emote_but_do_not_talk(self):
        g = await self.walker('Khách Lạ', token=self.guest('Khách Lạ')[0])
        b = await self.walker('Minh Tú')
        pg = g.welcome['me']['pid']
        self.assertEqual((await g.call('say', 'error', text='alo alo'))['code'], 'account')
        await g.send(t='emote', e='wave')
        self.assertEqual((await b.expect('emoted', pid=pg))['e'], 'wave')

    async def test_muted_players_cannot_talk_and_emotes(self):
        a = await self.walker('Lan Anh')
        b = await self.walker('Minh Tú')
        pa = a.welcome['me']['pid']
        with self.store.connect() as db:
            db.execute('INSERT INTO chat_mutes(pid, until, by_admin, reason, at) VALUES(?, ?, ?, ?, ?)', (pa, time.time() + 3600, 'op', 'spam', time.time()))
        self.assertEqual((await a.call('say', 'error', text='alo alo'))['code'], 'muted')
        await a.send(t='emote', e='wave')
        self.assertEqual((await b.expect('emoted', pid=pa))['e'], 'wave')
        self.assertEqual((await a.call('emote', 'error', e='poop'))['code'], 'bad')


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Tables(StreetCase):
    async def test_sit_topics_votes_and_seats(self):
        people = [await self.walker(f'Ngồi {i}') for i in range(5)]
        a = people[0]
        await a.send(t='sit', table=1)                             # Bờ hồ table 1 seats 3
        tb = await self.ev(people[1], 'tb', i=1)
        self.assertIn(tb['topic'], sd.TOPICS)
        self.assertEqual(tb['seats'][0], a.welcome['me']['pid'])
        mv = await self.ev(people[1], 'mv', pid=a.welcome['me']['pid'])
        self.assertEqual(mv['p'][-1], list(GEO['boho'].tables[1]['seats'][0]))
        for c in people[1:3]:
            await c.send(t='sit', table=1)
        await asyncio.sleep(0.3)
        self.assertEqual((await people[3].call('sit', 'error', table=1))['code'], 'full')
        table = self.room('walk:boho:1').data['tables'][1]
        first = table.topic
        await a.send(t='topic')
        await people[1].send(t='topic')
        await asyncio.sleep(0.2)
        self.assertEqual(table.topic, first, 'two of three voted: same card')
        await people[2].send(t='topic')
        await asyncio.sleep(0.2)
        self.assertNotEqual(table.topic, first, 'everyone voted: a new card')
        second = table.topic
        await self.street.tick(table.until + 0.1)                   # two minutes later: a new card
        self.assertNotEqual(table.topic, second)
        await people[2].send(t='move', x=300, y=800)                # walking away stands you up
        await asyncio.sleep(0.2)
        self.assertEqual(table.seats.count(None), 1)
        await people[3].call('sit', 'walk', table=1)
        for c in people[:4]:
            await c.send(t='stand')
        await asyncio.sleep(0.2)
        self.assertEqual((table.seats, table.topic), ([None] * 3, None))
        self.assertEqual((await a.call('sit', 'error', table=9))['code'], 'bad')
        self.assertEqual((await a.call('topic', 'error'))['code'], 'bad')


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Happenings(StreetCase):
    async def test_at_most_one_per_instance_per_ten_minutes(self):
        a = await self.walker('Lan Anh')
        room = self.room('walk:boho:1')
        now = time.time()
        room.data['next_hap'] = now
        for s in range(0, HAPPEN_GAP * 3, 5):                      # 30 simulated minutes of ticks
            await self.street.tick(now + s)
        await asyncio.sleep(0.2)
        haps = [f for f in a.frames if f.get('t') == 'happen']
        self.assertGreaterEqual(len(haps), 2)
        self.assertLessEqual(len(haps), 3)
        times = sorted(h['at'] for h in haps)
        self.assertTrue(all(b - x >= HAPPEN_GAP for x, b in zip(times, times[1:])), times)
        self.assertTrue(all(h['k'] in ('vendor', 'lion', 'env') for h in haps))

    async def test_envelope_paid_once_and_capped(self):
        a = await self.walker('Lan Anh')
        b = await self.walker('Minh Tú')
        room = self.room('walk:boho:1')
        self.street._happen(room, time.time(), kind='env')
        hap = await a.expect('happen', k='env')
        await b.expect('happen', k='env')
        self.assertTrue(GEO['boho'].inside(hap['x'], hap['y']))
        await a.send(t='grab', id=hap['id'])
        await b.send(t='grab', id=hap['id'])
        got = await a.expect('grabbed')
        late = await b.expect('error')
        self.assertIn(late['code'], ('late', 'gone'))
        end = await b.expect('happen_end', id=hap['id'])
        self.assertEqual((end['pid'], end['n']), (a.welcome['me']['pid'], got['n']))
        self.assertEqual((await a.call('grab', 'error', id=hap['id']))['code'], 'gone')
        with self.store.connect() as db:
            rows = db.execute('SELECT id, sid, kind, amount, status FROM live_effects').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['kind'], rows[0]['amount'], rows[0]['status']), ('coins', got['n'], 'pending'))
        self.assertTrue(3 <= got['n'] <= 8)
        # B has had almost the whole day's cap already: the envelope stays for someone else
        sid_b = self.app.hub.players[b.welcome['me']['pid']].sid
        with self.store.connect() as db:
            db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES('env:old', ?, 'coins', ?, '{}', 'applied', ?)",
                       (sid_b, ENVELOPE_CAP - 2, time.time()))
        self.street._happen(room, time.time(), kind='env')
        hap2 = await b.expect('happen', k='env')
        await a.expect('happen', id=hap2['id'])
        self.assertEqual((await b.call('grab', 'error', id=hap2['id']))['code'], 'cap')
        await asyncio.sleep(1.05)
        got2 = await a.call('grab', 'grabbed', id=hap2['id'])
        self.assertEqual(got2['id'], hap2['id'])
        # an unclaimed envelope flies away
        self.street._happen(room, time.time(), kind='env')
        hap3 = await a.expect('happen', k='env')
        await self.street.tick(hap3['until'] + 1)
        self.assertNotIn('pid', await a.expect('happen_end', id=hap3['id']))


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Blocks(StreetCase):
    async def test_block_during_a_stroll_and_new_instances(self):
        a = await self.walker('Lan Anh')
        b = await self.walker('Minh Tú')
        c = await self.walker('Hà Vy')
        pa, pb = a.welcome['me']['pid'], b.welcome['me']['pid']
        await a.call('block', 'blocked', pid=pb)
        await self.street.tick(time.time())
        self.assertEqual((await self.ev(a, 'out', pid=pb))['pid'], pb)
        self.assertEqual((await self.ev(b, 'out', pid=pa))['pid'], pa)
        a.frames.clear()
        c.frames.clear()
        await b.send(t='say', text='có ai không')
        await b.send(t='move', x=100, y=800)
        await b.send(t='emote', e='heart')
        await c.expect('said', pid=pb)
        await self.ev(c, 'mv', pid=pb)
        await asyncio.sleep(0.3)
        self.assertFalse([f for f in a.frames if f.get('pid') == pb or any(e.get('pid') == pb for e in f.get('ev', []))])
        self.assertEqual((await a.call('card', 'error', pid=pb))['code'], 'gone')
        # out and back in: never the same instance again
        await b.call('walk_out', 'walk_left')
        b2 = await b.call('walk_in', 'walk_room', place='boho', look=LOOK)
        self.assertEqual(b2['room'], 'walk:boho:2')
        self.assertNotIn(pa, [p['pid'] for p in b2['people']])


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Cards(StreetCase):
    async def test_card_friend_code_and_coffee_for_two(self):
        ta, sa = self.account('Lan Anh')
        tb, sb = self.account('Minh Tú')
        tg, _ = self.guest('Khách Lạ')
        a = await self.walker('Lan Anh', token=ta)
        b = await self.walker('Minh Tú', token=tb)
        g = await self.walker('Khách Lạ', token=tg)
        pa, pb, pg = (x.welcome['me']['pid'] for x in (a, b, g))
        card = await a.call('card', 'card', pid=pb)
        self.assertEqual((card['name'], card['friend'], card['account']), ('Minh Tú', False, True))
        self.assertRegex(card['code'], r'PCC-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{6}')
        self.assertEqual((await a.call('card', 'card', pid=pb))['code'], card['code'], 'the same code every time')
        self.assertIsNone((await a.call('card', 'card', pid=pg))['code'], 'a guest has no code')
        self.befriend(sa, sb)
        self.assertTrue((await a.call('card', 'card', pid=pb))['friend'])
        # coffee: a declined invite, then an accepted one
        sent = await a.call('invite', 'invite_sent', pid=pb)
        inv = await b.expect('invited', id=sent['id'])
        self.assertEqual(inv['name'], 'Lan Anh')
        await b.send(t='invite_reply', id=inv['id'], ok=False)
        await a.expect('invite_no', id=sent['id'])
        sent = await a.call('invite', 'invite_sent', pid=pb)
        await b.expect('invited', id=sent['id'])
        await b.send(t='invite_reply', id=sent['id'], ok=True)
        ra, rb = await a.expect('walk_room'), await b.expect('walk_room')
        self.assertEqual(ra['room'], rb['room'])
        self.assertTrue(ra['room'].startswith('walk:cafe:') and ra['private'])
        self.assertEqual({p['pid'] for p in ra['people']}, {pa, pb})
        self.assertIn(ra['tables'][0]['topic'], sd.TOPICS)
        self.assertEqual(sorted(ra['tables'][0]['seats']), sorted([pa, pb]))
        self.assertEqual((await self.ev(g, 'out', pid=pa))['pid'], pa)
        await a.send(t='say', text='cà phê muối ở đây ngon ghê')
        self.assertEqual((await b.expect('said', pid=pa))['ch'], ra['room'])
        await asyncio.sleep(0.3)
        self.assertFalse([f for f in g.frames if f.get('t') == 'said'])
        self.assertEqual((await a.call('invite', 'error', pid=pb))['code'], 'bad')
        # an invite that nobody answers expires
        await a.call('walk_in', 'walk_room', place='boho', look=LOOK)
        await b.call('walk_in', 'walk_room', place='boho', look=LOOK)
        sent = await a.call('invite', 'invite_sent', pid=pb)
        await self.street.tick(time.time() + 31)
        await a.expect('invite_no', id=sent['id'])
        self.assertEqual((await b.call('invite_reply', 'error', id=sent['id'], ok=True))['code'], 'gone')


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class Switch(LiveCase):
    async def test_street_off(self):
        c = await self.connect(self.guest('Lan Anh')[0])
        self.assertFalse(c.welcome['flags']['street'])
        self.assertEqual((await c.call('walk_in', 'error', place='boho'))['code'], 'off')


if __name__ == '__main__':
    unittest.main()
