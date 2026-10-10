"""🐕 live/dog_bark.py: matching (same stake, never the same IP, never the same pair more than 3 in a row), the
tug-of-war on loudness numbers, the settlement once (a win pays the pot, a draw refunds, a disconnect or a quit loses),
and the house dog after the wait, clearly labelled and within today's caps."""
import asyncio
import secrets
import time
import unittest
from unittest.mock import patch

from game import dog_bark as G
from live import dog_bark as LB
from tests.live_support import HAVE_WS, ORIGIN, Client, LiveCase


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class LiveDogBark(LiveCase):
    cfg_extra = dict(bark=True, trust_proxy=True)

    async def asyncSetUp(self):
        await super().asyncSetUp()
        for p in (patch.object(LB, 'COUNTDOWN', 0.1), patch.object(G, 'K', 0.05)):   # a quicker rope for the tests
            p.start()
            self.addCleanup(p.stop)

    async def ready(self, *cs):
        """bark_go, then the page says its mic delivers (the rope waits for it)."""
        out = []
        for c in cs:
            g = await c.expect('bark_go', timeout=4)
            self.assertIsNone(g['cd'])                      # not started before every mic is ready
            await c.send(t='bark_ready', m=g['m'], floor=-58)
            out.append(g)
        for c in cs:
            await c.expect('bark_start', timeout=3)
        return out

    async def join(self, token, ip):
        from websockets.asyncio.client import connect
        ws = await connect(f'ws://127.0.0.1:{self.port}/live', origin=ORIGIN, open_timeout=5,
                           additional_headers={'Cookie': f'mnl_session={token}', 'X-Real-IP': ip})
        c = Client(ws)
        self.clients.append(c)
        await c.send(t='hello', v=1)
        c.welcome = await c.expect('welcome')
        return c

    def ticket(self, sid, stake=500, **kw):
        tid = 'k' + secrets.token_hex(10)
        with self.store.connect() as db:
            db.execute("INSERT INTO bark_tickets(id, sid, stake, status, created) VALUES(?,?,?,'wait',?)", (tid, sid, stake, time.time()))
        return tid

    def row(self, tid):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM bark_tickets WHERE id=?', (tid,)).fetchone())

    def fx(self, tid):
        with self.store.connect() as db:
            r = db.execute("SELECT amount, status FROM live_effects WHERE id=?", (f'bark:{tid}',)).fetchone()
            return dict(r) if r else None

    async def pair(self, stake=500, ips=('10.0.0.1', '10.0.0.2')):
        (ta, sa), (tb, sb) = self.account('Lan'), self.account('Minh')
        a, b = await self.join(ta, ips[0]), await self.join(tb, ips[1])
        ka, kb = self.ticket(sa, stake), self.ticket(sb, stake)
        self.assertTrue(a.welcome['flags']['bark'])
        await a.call('bark_find', 'bark_wait', ticket=ka)
        await b.send(t='bark_find', ticket=kb)
        return a, b, ka, kb, sa, sb

    async def shout(self, c, m, v, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            await c.send(t='bark_v', m=m, v=[v, v - 2, v + 1, v - 1])   # a real voice wobbles (a flat run is no voice)
            await asyncio.sleep(0.25)
            if any(f.get('t') == 'bark_end' for f in c.frames):
                return

    async def test_match_win_pays_the_pot_once(self):
        a, b, ka, kb, sa, sb = await self.pair()
        ga, gb = await self.ready(a, b)
        self.assertEqual((ga['m'], {ga['side'], gb['side']}, ga['pot']), (gb['m'], {'a', 'b'}, 1_000))
        self.assertEqual((ga['opp']['house'], ga['opp']['name']), (False, 'Minh'))
        self.assertEqual(self.row(ka)['status'], 'play')
        await self.shout(a, ga['m'], 95, 6)
        ea, eb = await a.expect('bark_end', timeout=6), await b.expect('bark_end', timeout=6)
        self.assertEqual((ea['result'], ea['pay'], ea['why']), ('win', 1_000, 'end'))
        self.assertEqual((eb['result'], eb['pay']), ('lose', 0))
        self.assertEqual((self.row(ka)['status'], self.row(ka)['result'], self.row(ka)['pay']), ('done', 'win', 1_000))
        self.assertEqual(self.fx(ka), dict(amount=1_000, status='pending'))
        self.assertIsNone(self.fx(kb))
        feat = self.app.by_name['bark']
        self.assertEqual((feat.matches, feat.in_match), ({}, {}))
        await a.send(t='bark_v', m=ga['m'], v=[100])            # a late frame changes nothing
        await a.call('bark_rejoin', 'bark_none')

    async def test_same_ip_is_never_matched(self):
        a, b, ka, kb, sa, sb = await self.pair(ips=('10.0.0.9', '10.0.0.9'))
        await b.expect('bark_wait')
        await a.nothing('bark_go', wait=1.6)                     # a matching pass ran meanwhile
        lob = await a.call('bark_lobby', 'bark_lobby')
        self.assertEqual(lob['wait'], [[500, 1]])
        self.assertEqual((self.row(ka)['status'], self.row(kb)['status']), ('wait', 'wait'))
        feat = self.app.by_name['bark']
        self.assertTrue(all(len(w.iph) == 16 and '10.0.0.9' not in w.iph for w in feat.queue.values()))

    async def test_disconnect_loses(self):
        with patch.object(G, 'GONE_S', 0.4):
            a, b, ka, kb, sa, sb = await self.pair()
            await self.ready(a, b)
            await b.close()
            ea = await a.expect('bark_end', timeout=5)
        self.assertEqual((ea['result'], ea['why'], ea['pay']), ('win', 'gone', 1_000))
        self.assertEqual(self.row(kb)['result'], 'lose')

    async def test_quit_loses_and_bad_loudness_is_harmless(self):
        a, b, ka, kb, sa, sb = await self.pair()
        ga, _ = await self.ready(a, b)
        await a.send(t='bark_v', m=ga['m'], v=[10**12, -10**12, 'x', None, [1]])
        await a.send(t='bark_v', m=ga['m'], v='loud')
        await a.send(t='bark_quit', m=ga['m'])
        ea, eb = await a.expect('bark_end', timeout=4), await b.expect('bark_end', timeout=4)
        self.assertEqual((ea['result'], ea['why'], eb['result'], eb['pay']), ('lose', 'quit', 'win', 1_000))

    async def test_draw_refunds_both(self):
        with patch.object(G, 'MATCH_S', 1.0):
            a, b, ka, kb, sa, sb = await self.pair(stake=300)
            ga, _ = await self.ready(a, b)
            for _ in range(4):                               # both sides only talk and hum: nothing moves
                await a.send(t='bark_v', m=ga['m'], v=[20, 25, 18, 28])
                await b.send(t='bark_v', m=ga['m'], v=[60, 60, 60, 60])
                await asyncio.sleep(0.2)
            ea, eb = await a.expect('bark_end', timeout=5), await b.expect('bark_end', timeout=5)
        self.assertEqual((ea['result'], ea['pay'], eb['result'], eb['pay'], ea['x']), ('draw', 300, 'draw', 300, 0))
        self.assertEqual((self.fx(ka)['amount'], self.fx(kb)['amount']), (300, 300))

    async def test_house_dog_after_the_wait(self):
        ta, sa = self.account('Lan')
        a = await self.join(ta, '10.0.0.5')
        ka = self.ticket(sa, 200)
        with patch.object(G, 'DOG_AFTER', 0.2), patch.object(G, 'MATCH_S', 4.0):
            await a.call('bark_find', 'bark_wait', ticket=ka)
            (go,) = await self.ready(a)
            opp = go['opp']
            self.assertTrue(opp['house'])
            self.assertEqual(opp['tag'], 'Chó nhà Mây')
            self.assertIn(opp['name'], G.NAMES)
            self.assertNotIn('pid', opp)
            self.assertEqual(go['pot'], 400)
            self.assertEqual((self.row(ka)['status'], self.row(ka)['opp'], self.row(ka)['dog']), ('dog', 'dog', opp['name']))
            end = time.monotonic() + 6
            while time.monotonic() < end and not any(f['t'] == 'bark_end' for f in a.frames):   # silent, but the mic delivers
                await a.send(t='bark_v', m=go['m'], v=[3, 5, 2, 4])
                await asyncio.sleep(0.25)
            ev = await a.expect('bark_end', timeout=3)
        self.assertEqual((ev['result'], ev['pay']), ('lose', 0))
        self.assertIsNone(self.fx(ka))
        frames = [f for f in a.frames if f['t'] in ('bark_dog', 'bark_st')]
        first = next(i for i, f in enumerate(frames) if f['t'] == 'bark_dog')   # heard before it pulls
        self.assertTrue(all(f['x'] == 0 for f in frames[:first] if f['t'] == 'bark_st'))
        self.assertTrue(all(f['d'] > 0 and f['p'] > 0 for f in frames if f['t'] == 'bark_dog'))

    async def test_barking_beats_the_dog_and_a_dead_mic_waits(self):
        ta, sa = self.account('Lan')
        a = await self.join(ta, '10.0.0.7')
        ka = self.ticket(sa, 200)
        with patch.object(G, 'DOG_AFTER', 0.2):
            await a.call('bark_find', 'bark_wait', ticket=ka)
            (go,) = await self.ready(a)
            await self.shout(a, go['m'], 96, 8)
            ev = await a.expect('bark_end', timeout=3)
        self.assertEqual((ev['result'], ev['pay'], ev['why']), ('win', 400, 'end'))
        kb = self.ticket(sa, 200)                            # the mic says ready, then sends nothing: the match waits
        with patch.object(G, 'DOG_AFTER', 0.2), patch.object(G, 'PAUSE_MAX', 1.0):
            await a.call('bark_find', 'bark_wait', ticket=kb)
            (go,) = await self.ready(a)
            st = await a.expect('bark_st', timeout=3, m=go['m'])
            while 'w' not in st:
                st = await a.expect('bark_st', timeout=3, m=go['m'])
            self.assertEqual(st['x'], 0)
            ev = await a.expect('bark_end', timeout=4)
        self.assertEqual((ev['result'], ev['why']), ('draw', 'nomic'))
        await a.nothing('bark_dog', wait=0.05, m=go['m'])   # no sample, no time, no dog bark

    async def test_no_mic_no_match(self):
        with patch.object(G, 'READY_MAX', 0.8):
            a, b, ka, kb, sa, sb = await self.pair(stake=300)
            g = await a.expect('bark_go')
            await b.expect('bark_go')
            await a.send(t='bark_ready', m=g['m'], floor=-60)   # only one side's mic ever delivers
            ea = await a.expect('bark_end', timeout=4)
        self.assertEqual((ea['result'], ea['why'], ea['pay']), ('draw', 'nomic', 300))
        self.assertEqual((self.fx(ka)['amount'], self.fx(kb)['amount']), (300, 300))

    async def test_house_dog_respects_the_day_caps(self):
        ta, sa = self.account('Lan')
        a = await self.join(ta, '10.0.0.6')
        now = time.time()
        with self.store.connect() as db:
            db.execute("INSERT INTO bark_tickets(id, sid, stake, status, created, ended, opp, result, pay) "
                       "VALUES(?,?,4900,'done',?,?,'dog','win',9800)", ('k' + 'a' * 20, sa, now - 5, now - 2))
        ka = self.ticket(sa, 500)                               # 4,900 won today: the dog takes 100 more at most
        with patch.object(G, 'DOG_AFTER', 0.2):
            await a.call('bark_find', 'bark_wait', ticket=ka)
            info = await a.expect('bark_info', timeout=4)
            self.assertEqual((info['code'], info['room']), ('dog_full', 100))
            await a.nothing('bark_go', wait=1.2)
            back = await a.call('bark_cancel', 'bark_back', ticket=ka)
        self.assertTrue(back['ok'])
        self.assertEqual(self.fx(ka), dict(amount=500, status='pending'))
        self.assertEqual((await a.call('bark_cancel', 'bark_back', ticket=ka))['ok'], False)   # once

    async def test_same_pair_at_most_three_in_a_row(self):
        (ta, sa), (tb, sb) = self.account('Lan'), self.account('Minh')
        feat = self.app.by_name['bark']
        for _ in range(G.PAIR_MAX):
            feat.pairs.played(sa, sb, time.time())
        a, b = await self.join(ta, '10.0.1.1'), await self.join(tb, '10.0.1.2')
        await a.call('bark_find', 'bark_wait', ticket=self.ticket(sa))
        await b.call('bark_find', 'bark_wait', ticket=self.ticket(sb))
        await a.nothing('bark_go', wait=1.5)
        tc, sc = self.account('Hoa')                             # someone else waiting: matched at once
        c = await self.join(tc, '10.0.1.3')
        await c.send(t='bark_find', ticket=self.ticket(sc))
        go = await c.expect('bark_go', timeout=3)
        self.assertIn(go['opp']['name'], ('Lan', 'Minh'))

    async def test_watch_and_cheer(self):
        a, b, ka, kb, sa, sb = await self.pair()
        ga, _ = await self.ready(a, b)
        tw, _ = self.account('Tư')
        w = await self.join(tw, '10.0.2.1')
        lob = await w.call('bark_lobby', 'bark_lobby')
        self.assertEqual([m['m'] for m in lob['matches']], [ga['m']])
        room = await w.call('bark_watch', 'bark_room', m=ga['m'])
        self.assertEqual({room['a']['name'], room['b']['name']}, {'Lan', 'Minh'})
        await w.send(t='bark_cheer', m=ga['m'], e='🔥')
        await w.send(t='bark_cheer', m=ga['m'], e='💩')        # not a cheer: ignored
        st = await w.expect('bark_st', timeout=2, fx={'🔥': 1})
        self.assertIn('x', st)
        await w.expect('bark_st')
