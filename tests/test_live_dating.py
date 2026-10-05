"""💕 Dates (live/dating.py): the matcher (fairness, preferences, blocks, the 24 h rule), the date's steps and
timeouts, private picks that never leak before the reveal, an end that only says "match" for a mutual ❤️ (the same
frame for both otherwise), and the rewards (capped per day, paid once). End to end over real sockets against a real
game database (PostgreSQL with TEST_DATABASE_URL)."""
import asyncio
import random
import time
import unittest

from live import dating as dt
from live.dating import Date, Seat, fits, match
from live.dating_content import CARDS, MENU
from tests.live_support import HAVE_WS, LiveCase


def seats(*specs):
    """Seats waiting in this order: (pid, g, pref)."""
    return [Seat(pid, pref, g, since=float(i)) for i, (pid, g, pref) in enumerate(specs)]


def pairs(out):
    return [(a.pid, b.pid) for a, b in out]


class ContentTests(unittest.TestCase):
    def test_cards_and_menu(self):
        self.assertGreaterEqual(len(CARDS), 80)
        self.assertEqual(len({q for q, _ in CARDS}), len(CARDS))
        for q, opts in CARDS:
            self.assertTrue(3 <= len(opts) <= 4, q)
            self.assertEqual(len(set(opts)), len(opts), q)
            self.assertLessEqual(max(len(o) for o in opts), 40, q)
        self.assertGreaterEqual(len(MENU), dt.N_MENU)
        self.assertEqual(len({m[0] for m in MENU}), len(MENU))


class MatcherTests(unittest.TestCase):
    def test_longest_waiting_first(self):
        s = seats(('a', 'm', 'any'), ('b', 'f', 'any'), ('c', 'm', 'any'), ('d', 'f', 'any'), ('e', 'm', 'any'))
        random.shuffle(s)   # whatever the order they come in
        self.assertEqual(pairs(match(s)), [('a', 'b'), ('c', 'd')])

    def test_preferences(self):
        s = seats(('a', 'm', 'f'), ('b', 'm', 'f'), ('c', 'f', 'm'), ('d', 'f', 'any'), ('e', 'm', 'm'))
        self.assertEqual(pairs(match(s)), [('a', 'c'), ('b', 'd')])   # e (a boy who wants a boy) waits: no other one yet
        self.assertEqual(pairs(match(seats(('e', 'm', 'm'), ('x', 'm', 'any'), ('y', 'm', 'm')))), [('e', 'x')])

    def test_fits_both_ways(self):
        girl_any, boy_wants_girl, boy_wants_boy = Seat('a', 'any', 'f'), Seat('b', 'f', 'm'), Seat('c', 'm', 'm')
        self.assertTrue(fits(girl_any, boy_wants_girl))
        self.assertFalse(fits(girl_any, boy_wants_boy))      # c wants a boy
        self.assertTrue(fits(boy_wants_boy, Seat('d', 'any', 'm')))
        unknown = Seat('u', 'any', None)                     # no Nam/Nữ yet: only with someone who takes anyone
        self.assertFalse(fits(unknown, boy_wants_girl))
        self.assertTrue(fits(unknown, Seat('e', 'any', 'm')))
        self.assertFalse(fits(Seat('w', 'f', 'm'), unknown))

    def test_blocked_and_recent_pairs_are_skipped(self):
        s = seats(('a', 'm', 'any'), ('b', 'f', 'any'), ('c', 'f', 'any'))
        no_ab = lambda x, y: {x.pid, y.pid} != {'a', 'b'}   # noqa: E731 - blocked, or dated within 24 h
        self.assertEqual(pairs(match(s, no_ab)), [('a', 'c')])
        self.assertEqual(pairs(match(s, lambda x, y: False)), [])

    def test_big_bench_is_fast_and_fair(self):
        rng = random.Random(7)
        s = [Seat(f'p{i:05d}', rng.choice(dt.PREFS), rng.choice(('m', 'f', None)), since=float(i)) for i in range(3000)]
        t = time.perf_counter()
        out = match(s)
        self.assertLess(time.perf_counter() - t, 1.0)
        used = [p for ab in pairs(out) for p in ab]
        self.assertEqual(len(used), len(set(used)))
        for a, b in out:
            self.assertTrue(fits(a, b))
        # fairness: nobody left waiting could have been seated with someone who waited less than their partner
        left = [x for x in s if x.pid not in set(used)]
        for x in left[:200]:
            for y in left:
                if y is not x and fits(x, y):
                    self.fail(f'{x} and {y} both wait but fit')


class DateStateTests(unittest.TestCase):
    A = dict(pid='a' * 16, sid='sa', name='Lan', av='🌸', account=True)
    B = dict(pid='b' * 16, sid='sb', name='Huy', av='☕', account=True)

    def date(self, t=1000.0):
        return Date('0123456789ab', self.A, self.B, t, rng=random.Random(3))

    def test_steps_and_timeouts(self):
        d, t = self.date(), 1000.0
        a, b = d.pids
        self.assertEqual(d.step, 'hello')
        self.assertFalse(d.advance(t + 1))
        d.advance(t + dt.HELLO_S)
        self.assertEqual((d.step, d.i, d.shown), ('card', 0, False))
        t += dt.HELLO_S
        d.picks[a][0] = 1
        d.advance(t + 1)
        self.assertFalse(d.shown)                    # one pick: still waiting for the other
        d.advance(t + dt.CARD_S)                     # time is up: revealed anyway
        self.assertTrue(d.shown)
        self.assertEqual(d.view(a, t)['cards'][0]['them'], None)
        t += dt.CARD_S
        d.advance(t + dt.REVEAL_S)
        self.assertEqual((d.step, d.i), ('card', 1))
        t += dt.REVEAL_S
        for i in (1, 2):
            d.picks[a][i] = d.picks[b][i] = 0         # both pick: revealed at once
            d.advance(t)
            self.assertTrue(d.shown)
            t += dt.REVEAL_S
            d.advance(t)
        self.assertEqual(d.step, 'menu')
        self.assertEqual(d.same(), 2)
        d.advance(t + dt.MENU_S)                      # nobody ordered: revealed empty, then chat
        self.assertTrue(d.ordered)
        self.assertEqual(d.hits(), 0)
        t += dt.MENU_S + dt.MENU_REVEAL_S
        d.advance(t)
        self.assertEqual(d.step, 'chat')
        d.chat_done.update(d.pids)                    # both tapped "xong": the vote at once
        d.advance(t + 1)
        self.assertEqual(d.step, 'vote')
        self.assertFalse(d.advance(t + 2))
        self.assertTrue(d.advance(t + 1 + dt.VOTE_S))  # nobody voted: over (👋 for both)

    def test_five_minutes_at_most(self):
        d, t = self.date(), 1000.0
        while not d.advance(t):
            t += 0.5
        self.assertLessEqual(t - 1000.0, 300)

    def test_picks_stay_private_until_revealed(self):
        d, t = self.date(), 1000.0
        a, b = d.pids
        d.advance(t + dt.HELLO_S)
        d.picks[a][0] = 2
        va, vb = d.view(a, t), d.view(b, t)
        self.assertEqual(va['mine'], 2)
        self.assertIsNone(vb['mine'])
        self.assertTrue(vb['peer_done'])
        self.assertEqual(vb['cards'], [])
        self.assertNotIn('them', str(vb))
        d.picks[b][0] = 2
        d.advance(t + dt.HELLO_S + 1)
        self.assertEqual(d.view(b, t)['cards'][0], dict(q=CARDS[d.cards[0]][0], opts=list(CARDS[d.cards[0]][1]), me=2, them=2))
        # the menu: what I crave and what I order stay mine until both are in
        while d.step != 'menu':
            d.advance(t + 1000)
            t += 1000
        d.want[a], d.give[a] = d.menu[0], d.menu[1]
        vb = d.view(b, t)
        self.assertNotIn('order', vb)
        self.assertIsNone(vb['want'])
        d.want[b], d.give[b] = d.menu[1], d.menu[0]
        d.advance(t)
        self.assertEqual(d.view(b, t)['order']['hits'], 2)
        # votes are never in anyone's view
        while d.step != 'vote':
            d.advance(t + 1000)
            t += 1000
        d.votes[a] = 'wave'
        self.assertNotIn('wave', str(d.view(b, t)))
        self.assertEqual(d.view(a, t)['mine'], 'wave')


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class DatingLiveTests(LiveCase):
    cfg_extra = dict(dating=True)

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.cfg.date_speed = 40          # the 5 minutes in a few seconds (answers move it on at once anyway)
        self.feat = self.app.by_name['dating']

    async def pair(self, a_name='Lan Anh', b_name='Huy', accounts=True):
        mk = self.account if accounts else (lambda n: self.guest(n))
        (ta, sa), (tb, sb) = mk(a_name), mk(b_name)
        a, b = await self.connect(ta), await self.connect(tb)
        a.sid, b.sid = sa, sb
        return a, b

    async def sit(self, c, pref='any', g='f'):
        await c.send(t='queue', op='sit', pref=pref, g=g)
        return await c.expect('bench', state='wait')

    async def until_step(self, c, step, timeout=8.0, **match):
        while True:
            f = await c.expect('date', timeout=timeout, **match)
            if f['step'] == step:
                return f

    async def play_cards(self, a, b, d, same=(True, False, True)):
        for i in range(dt.N_CARDS):
            fa = await self.until_step(a, 'card', i=i)
            await self.until_step(b, 'card', i=i)
            await a.send(t='answer', date=d, step='card', i=i, pick=0)
            mine = await a.expect('date', mine=0, i=i, shown=False)
            self.assertNotIn('them', str(mine.get('cards', [])[i:]))
            seen = await b.expect('date', peer_done=True, i=i, shown=False)
            self.assertIsNone(seen['mine'])
            self.assertEqual(len(seen['cards']), i)              # nothing of card i shows yet
            await b.send(t='answer', date=d, step='card', i=i, pick=0 if same[i] else 1)
            ra = await a.expect('date', shown=True, i=i)
            self.assertEqual(ra['cards'][i]['them'], 0 if same[i] else 1)
            self.assertEqual(len(fa['opts']), len(ra['cards'][i]['opts']))

    async def test_full_date_mutual_heart(self):
        a, b = await self.pair()
        self.assertEqual(a.welcome['bonds'], [])
        await self.sit(a, 'm', 'f')
        await self.sit(b, 'f', 'm')
        ha, hb = await a.expect('date', step='hello'), await b.expect('date', step='hello')
        d = ha['id']
        self.assertEqual((ha['peer']['name'], hb['peer']['name']), ('Huy', 'Lan Anh'))
        self.assertEqual(hb['peer']['pid'], self.pid(a.sid))
        await self.play_cards(a, b, d)
        ma = await self.until_step(a, 'menu')
        await self.until_step(b, 'menu')
        items = [m['id'] for m in ma['menu']]
        await a.send(t='answer', date=d, step='menu', want=items[0], give=items[1])
        await b.expect('date', peer_done=True, step='menu')
        await b.send(t='answer', date=d, step='menu', want=items[1], give=items[2])
        ra = await a.expect('date', shown=True, step='menu')
        self.assertEqual((ra['order']['i_gave']['id'], ra['order']['they_want']['id'], ra['order']['hits']), (items[1], items[1], 1))
        await self.until_step(a, 'chat')
        await self.until_step(b, 'chat')
        await a.send(t='date_say', date=d, text='chào nha, zalo minh123 nè', cid='s1')
        mine = await a.expect('msg', cid='s1')
        got = await b.expect('msg')
        self.assertEqual(got['text'], 'chào nha, zalo ••• nè')
        self.assertEqual((mine['ch'], got['id']), ('date:' + d, mine['id']))
        for c in (a, b):
            await c.send(t='answer', date=d, step='chat')
        await self.until_step(a, 'vote')
        await self.until_step(b, 'vote')
        await a.send(t='heart', date=d, v='heart')
        await a.expect('date', mine='heart')
        await b.nothing('date', wait=0.3, mine='heart')        # b is not told a has chosen
        await b.send(t='heart', date=d, v='heart')
        ea, eb = await a.expect('date', step='end'), await b.expect('date', step='end')
        self.assertEqual((ea['how'], eb['how']), ('match', 'match'))
        self.assertTrue(ea['friends'] and eb['friends'])
        self.assertEqual((ea['spirit'], eb['spirit'], ea['same']), (dt.SPIRIT, dt.SPIRIT, 2))
        self.assertEqual((await a.expect('bond'))['pid'], self.pid(b.sid))
        state = await a.expect('state')
        self.assertIn(self.pid(b.sid), [f['pid'] for f in state['friends']])
        with self.store.connect() as db:
            x, y = sorted((a.sid, b.sid))
            self.assertTrue(db.execute('SELECT 1 FROM date_bonds WHERE a=? AND b=?', (x, y)).fetchone())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM friends WHERE (sid=? AND friend=?) OR (sid=? AND friend=?)',
                                        (a.sid, b.sid, b.sid, a.sid)).fetchone()[0], 2)
            fx = db.execute("SELECT sid, kind, amount, status FROM live_effects ORDER BY sid").fetchall()
            self.assertEqual(sorted((r['sid'], r['kind'], r['amount'], r['status']) for r in fx),
                             sorted([(a.sid, 'spirit', dt.SPIRIT, 'pending'), (b.sid, 'spirit', dt.SPIRIT, 'pending')]))
            row = db.execute('SELECT how, same, hits, ended FROM live_dates WHERE id=?', (d,)).fetchone()
            self.assertEqual((row['how'], row['same'], row['hits']), ('match', 2, 1))
            from game import friends as fr
            self.assertTrue(fr._card(db, a.sid, b.sid)['dating'])        # "Đang tìm hiểu 💕" on the friend card
        again = await self.connect(a.token)
        self.assertEqual(again.welcome['bonds'], [self.pid(b.sid)])

    async def connect(self, token, **kw):
        c = await super().connect(token, **kw)
        c.token = token
        return c

    async def test_one_sided_says_nothing_about_who(self):
        a, b = await self.pair()
        await self.sit(a)
        await self.sit(b)
        d = (await a.expect('date', step='hello'))['id']
        for c in (a, b):
            await self.until_step(c, 'card', i=0)
        # skip ahead: nobody answers the cards or the menu (timeouts), both end the chat
        await self.until_step(a, 'chat', timeout=15)
        await self.until_step(b, 'chat', timeout=15)
        for c in (a, b):
            await c.send(t='answer', date=d, step='chat')
        await self.until_step(a, 'vote')
        await self.until_step(b, 'vote')
        await a.send(t='heart', date=d, v='heart')
        await b.send(t='heart', date=d, v='wave')
        ea, eb = await a.expect('date', step='end'), await b.expect('date', step='end')
        self.assertEqual((ea['how'], eb['how']), ('nope', 'nope'))
        strip = lambda f: {k: v for k, v in f.items() if k != 'peer'}   # noqa: E731
        self.assertEqual(strip(ea), strip(eb))                          # the same frame for both
        self.assertNotIn('wave', str(ea))
        self.assertNotIn('spirit', ea)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM date_bonds').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM live_effects').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM friends').fetchone()[0], 0)

    async def test_leave_early_and_the_24h_rule(self):
        a, b = await self.pair()
        await self.sit(a)
        await self.sit(b)
        d = (await a.expect('date', step='hello'))['id']
        await b.expect('date', step='hello')
        await a.send(t='date_leave', date=d)
        self.assertEqual((await a.expect('date', step='end'))['how'], 'left')
        self.assertEqual((await b.expect('date', step='end'))['how'], 'gone')
        e = await a.call('answer', 'error', date=d, step='card', i=0, pick=0)
        self.assertEqual(e['code'], 'no_date')
        # back on the bench: not with each other again today
        await self.sit(a)
        await self.sit(b)
        await asyncio.sleep(1.5)
        await a.nothing('date', wait=0.1)
        c = await self.connect(self.account('Mai')[0])
        await self.sit(c)
        hello = await c.expect('date', step='hello')
        self.assertEqual(hello['peer']['pid'], self.pid(a.sid))          # a waited longest
        self.assertIn(self.pid(b.sid), self.feat.queue)                 # b still waits

    async def test_blocked_pairs_never_meet(self):
        a, b = await self.pair()
        with self.store.connect() as db:
            db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?)', (self.pid(b.sid), self.pid(a.sid), time.time()))
        await self.sit(a)
        await self.sit(b)
        await asyncio.sleep(1.5)
        await a.nothing('date', wait=0.1)
        await b.nothing('date', wait=0.1)
        self.assertEqual(len(self.feat.queue), 2)

    async def test_block_on_the_date_screen(self):
        a, b = await self.pair()
        await self.sit(a)
        await self.sit(b)
        d = (await a.expect('date', step='hello'))['id']
        await b.send(t='date_report', date=d, reason='rude')
        self.assertEqual((await b.expect('reported'))['date'], d)
        await b.send(t='date_block', date=d)
        self.assertEqual((await b.expect('date', step='end'))['how'], 'left')
        self.assertEqual((await a.expect('date', step='end'))['how'], 'gone')    # gently: not "blocked"
        await b.expect('blocked', pid=self.pid(a.sid))
        with self.store.connect() as db:
            self.assertTrue(db.execute('SELECT 1 FROM blocks WHERE pid=? AND target=?', (self.pid(b.sid), self.pid(a.sid))).fetchone())
            self.assertTrue(db.execute("SELECT 1 FROM reports WHERE kind='date' AND reporter=?", (self.pid(b.sid),)).fetchone())

    async def test_disconnect_ends_the_date_gently(self):
        dt_gone, dt.GONE_S = dt.GONE_S, 0.5
        try:
            a, b = await self.pair()
            await self.sit(a)
            await self.sit(b)
            await a.expect('date', step='hello')
            await b.close()
            self.assertEqual((await a.expect('date', step='end', timeout=5))['how'], 'gone')
            self.assertEqual(self.feat.in_date, {})
        finally:
            dt.GONE_S = dt_gone

    async def test_reconnect_lands_back_in_the_date(self):
        a, b = await self.pair()
        await self.sit(a)
        await self.sit(b)
        d = (await a.expect('date', step='hello'))['id']
        await a.close()
        a2 = await self.connect(a.token)
        self.assertEqual(a2.welcome['date']['id'], d)
        await self.until_step(a2, 'card', i=0)

    async def test_bench_rules(self):
        anon = await self.connect(self.guest(None)[0])
        e = await anon.call('queue', 'error', op='sit', pref='any')
        self.assertEqual(e['code'], 'name')
        a = await self.connect(self.account('Lan')[0])
        for bad in (dict(pref='both'), dict(g='x'), dict(spot='<b>')):
            e = await a.call('queue', 'error', op='sit', **bad)
            self.assertEqual(e['code'], 'bad')
        w = await self.sit(a, 'f')
        self.assertEqual((w['pref'], w['n']), ('f', 1))
        self.assertEqual((await a.call('queue', 'bench', op='peek'))['state'], 'wait')
        await a.send(t='queue', op='stand')
        self.assertEqual((await a.expect('bench'))['state'], 'idle')
        self.assertEqual(self.feat.queue, {})
        await self.sit(a)
        await a.close()
        await asyncio.sleep(0.2)
        self.assertEqual(self.feat.queue, {})           # the last tab closed: off the bench

    async def test_guests_see_the_bench_but_cannot_sit(self):
        """Only accounts date (owner, 01/10: "người lạ không chat được", as for chat)."""
        token, sid = self.guest('Bé Khách')
        g = await self.connect(token)
        self.assertEqual((await g.call('queue', 'bench', op='peek'))['state'], 'idle')
        e = await g.call('queue', 'error', op='sit', pref='any', g='f')
        self.assertEqual(e['code'], 'account')
        self.assertEqual(self.feat.queue, {})
        a = await self.connect(self.account('Lan')[0])
        await self.sit(a)
        await g.nothing('date', wait=1.3)                  # never matched with the waiting account either
        self.assertEqual(len(self.feat.queue), 1)            # only Lan waits
        # the guest registers (an account takes over this save): sitting works without a new socket
        with self.store.connect() as db:
            db.execute("INSERT INTO accounts(username, display, pw, sid) VALUES('khach_moi', 'Bé Khách', 'x', ?)", (sid,))
        await self.sit(g)
        self.assertEqual((await g.expect('date', step='hello'))['peer']['name'], 'Lan')

    async def test_switch_off(self):
        self.cfg.dating = False
        a = await self.connect(self.guest('Lan')[0])
        self.assertEqual((await a.call('queue', 'error', op='sit'))['code'], 'off')


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class RewardTests(LiveCase):
    cfg_extra = dict(dating=True)

    async def test_spirit_capped_per_day_and_paid_once(self):
        from live.effects import grant
        _, sid = self.guest('Lan')
        db = self.app.db
        got = [await grant(db, sid, 'spirit', dt.SPIRIT, key=f'date:d{i}:p', cap=dt.SPIRIT_CAP) for i in range(4)]
        self.assertEqual(got, [True, True, True, False])
        self.assertFalse(await grant(db, sid, 'spirit', dt.SPIRIT, key='date:d0:p', cap=dt.SPIRIT_CAP))   # same key: once
        with self.store.connect() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM live_effects WHERE sid=?", (sid,)).fetchone()[0], 3)


if __name__ == '__main__':
    unittest.main()
