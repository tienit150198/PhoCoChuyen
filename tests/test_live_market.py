import unittest
from unittest.mock import patch
from game import realtime_market as rm
from tests.live_support import LiveCase,HAVE_WS

@unittest.skipUnless(HAVE_WS,'needs websockets')
class LiveMarket(LiveCase):
    async def test_visible_subscription_tick_switch_and_unsubscribe(self):
        c=await self.connect(self.guest()[0]);self.assertTrue(c.welcome['flags']['market'])
        at=rm.EPOCH+3601
        with patch.object(rm,'now',return_value=at):
            await c.send(t='market_watch',range='1D')
            first=await c.expect('market_quote')
            self.assertEqual(first['range'],'1D')
            self.assertEqual(first['coin']['price'],rm.quote('coin',at)['price'])
            feat=self.app.by_name['market']
            await feat.tick(at+1);await c.nothing('market_quote',wait=.03)
            with patch.object(rm,'now',return_value=at+600):
                await feat.tick(at+600)
                second=await c.expect('market_quote');self.assertEqual(second['tick'],first['tick']+1)
                await c.send(t='market_watch',range='1M');self.assertEqual((await c.expect('market_quote'))['range'],'1M')
                await c.send(t='market_watch',open=False)
                await c.send(t='ping');await c.expect('pong')
                self.assertFalse(feat.viewers)
                await feat.tick(at+1200);await c.nothing('market_quote',wait=.03)
        await c.send(t='market_watch',range='100Y');self.assertEqual((await c.expect('error'))['code'],'range')
