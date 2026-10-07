"""🔨 live/auction.py: live prices for the watchers of the auction house, the outbid and won notes to the players
themselves, from the game's NOTIFY (no polling, never a sid in a frame)."""
import json
import unittest

from live.app import NOTIFY_CHANNEL
from tests.live_support import HAVE_WS, LiveCase


@unittest.skipUnless(HAVE_WS, 'needs websockets')
class LiveAuction(LiveCase):
    def notify(self, event):
        with self.store.connect() as db:
            db.execute('SELECT pg_notify(?, ?)', (NOTIFY_CHANNEL, json.dumps(event)))

    async def test_watch_bid_outbid_end_won(self):
        (ta, sa), (tb, sb), (tc, _sc) = self.account('Lan'), self.account('Minh'), self.account('Hoa')
        a, b, c = await self.connect(ta), await self.connect(tb), await self.connect(tc)
        self.assertTrue(a.welcome['flags']['auction'])
        await a.send(t='auction_watch', open=True)
        await a.expect('auction_on')
        await c.send(t='auction_watch', open=True)
        await c.expect('auction_on')
        self.notify(dict(op='auction', lot='20261007-1', high=6000, n=2, ends=1791400000.0, next=6500, name='Minh',
                         lead=self.pid(sb), prev=self.pid(sa)))
        f = await a.expect('auction_bid')
        self.assertEqual((f['lot'], f['high'], f['n'], f['next'], f['name']), ('20261007-1', 6000, 2, 6500, 'Minh'))
        self.assertNotIn('lead', f)
        self.assertNotIn(sb, json.dumps(f))                                     # never a sid
        o = await a.expect('auction_outbid')                                    # Lan was the leader
        self.assertEqual((o['lot'], o['high']), ('20261007-1', 6000))
        lead = await b.expect('auction_bid')                                     # Minh is not watching: still told he leads
        self.assertTrue(lead['lead'])
        await c.expect('auction_bid')
        await c.nothing('auction_outbid', wait=.05)
        await c.send(t='auction_watch', open=False)
        self.notify(dict(op='auction_end', lot='20261007-1', status='sold', price=6000, name='Minh', win=self.pid(sb)))
        self.assertEqual((await a.expect('auction_end'))['status'], 'sold')
        self.assertEqual((await b.expect('auction_won'))['price'], 6000)
        await c.nothing('auction_end', wait=.05)
        self.notify(dict(op='auction', lot='BAD LOT', high=1, n=1, ends=1.0))   # a malformed event is dropped
        await a.nothing('auction_bid', wait=.05)

    async def test_title_won_shows_beside_the_name_first(self):
        from live import honours
        tok, sid = self.account('Lan')
        await self.connect(tok)   # online: the service knows her sid
        with self.store.connect() as db:
            db.execute("INSERT INTO auction_lots(id, item, kind, tier, name, emoji, start, step, starts_at, ends_at, planned_end, status, "
                       "high, high_sid, winner_sid, winner_name, price, settled_at, created) VALUES('20261007-2', 'dh_ky_lan', 'title', 2, "
                       "'Kỳ Lân Phố Mây', '🦄', 50000, 2500, 1, 2, 2, 'sold', 60000, ?, ?, 'Lan', 60000, 3, 1)", (sid, sid))
        h = honours.of_app(self.app)
        h.clear()
        self.assertEqual((await h.one(self.pid(sid)))[:1], ['dh_ky_lan'])
        honours.on_notify(self.app, dict(op='auction_end', status='sold'))   # a new win reads the holders again
        self.assertEqual(h.lb_at, -1e18)
