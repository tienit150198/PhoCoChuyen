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
        p = patch.object(LB, 'COUNTDOWN', 0.1)
        p.start()
        self.addCleanup(p.stop)

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
        ga, gb = await a.expect('bark_go'), await b.expect('bark_go')
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
            ga = await a.expect('bark_go')
            await b.expect('bark_go')
            await b.close()
            ea = await a.expect('bark_end', timeout=5)
        self.assertEqual((ea['result'], ea['why'], ea['pay']), ('win', 'gone', 1_000))
        self.assertEqual(self.row(kb)['result'], 'lose')

    async def test_quit_loses_and_bad_loudness_is_harmless(self):
        a, b, ka, kb, sa, sb = await self.pair()
        ga = await a.expect('bark_go')
        await b.expect('bark_go')
        await a.send(t='bark_v', m=ga['m'], v=[10**12, -10**12, 'x', None, [1]])
        await a.send(t='bark_v', m=ga['m'], v='loud')
        await a.send(t='bark_quit', m=ga['m'])
        ea, eb = await a.expect('bark_end', timeout=4), await b.expect('bark_end', timeout=4)
        self.assertEqual((ea['result'], ea['why'], eb['result'], eb['pay']), ('lose', 'quit', 'win', 1_000))

    async def test_draw_refunds_both(self):
        with patch.object(G, 'MATCH_S', 1.0):
            a, b, ka, kb, sa, sb = await self.pair(stake=300)
            await a.expect('bark_go')
            await b.expect('bark_go')
            ea, eb = await a.expect('bark_end', timeout=5), await b.expect('bark_end', timeout=5)
        self.assertEqual((ea['result'], ea['pay'], eb['result'], eb['pay']), ('draw', 300, 'draw', 300))
        self.assertEqual((self.fx(ka)['amount'], self.fx(kb)['amount']), (300, 300))

    async def test_house_dog_after_the_wait(self):
        ta, sa = self.account('Lan')
        a = await self.join(ta, '10.0.0.5')
        ka = self.ticket(sa, 200)
        with patch.object(G, 'DOG_AFTER', 0.2), patch.object(G, 'MATCH_S', 1.5):
            await a.call('bark_find', 'bark_wait', ticket=ka)
            go = await a.expect('bark_go', timeout=4)
            opp = go['opp']
            self.assertTrue(opp['house'])
            self.assertEqual(opp['tag'], 'Chó nhà Mây')
            self.assertIn(opp['name'], G.NAMES)
            self.assertNotIn('pid', opp)
            self.assertEqual(go['pot'], 400)
            self.assertEqual((self.row(ka)['status'], self.row(ka)['opp'], self.row(ka)['dog']), ('dog', 'dog', opp['name']))
            end = await a.expect('bark_end', timeout=5)          # silent: the dog barks on its own and wins
        self.assertEqual((end['result'], end['pay']), ('lose', 0))
        self.assertIsNone(self.fx(ka))

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
        ga = await a.expect('bark_go')
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
