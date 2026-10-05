import unittest
from unittest.mock import patch
from game import realtime_market as rm
import market_data as md

class MarketData(unittest.TestCase):
    def test_ranges_are_real_time_bounded_and_match_trade_quotes(self):
        at=rm.EPOCH+100*86400+310
        for span,seconds in md.RANGES.items():
            data=md.snapshot(span,at)
            self.assertEqual(data['range'],span)
            for asset in ('coin','gold'):
                q=data[asset];actual=rm.quote(asset,at)
                self.assertEqual(q['price'],actual['price'])
                self.assertEqual(q['previous'],actual['previous'])
                points=q['points']
                self.assertLessEqual(len(points),181)
                self.assertEqual(points[-1],[actual['as_of'],actual['price']])
                self.assertGreaterEqual(points[0][0],actual['as_of']-seconds)
                self.assertEqual(sorted(set(p[0] for p in points)),[p[0] for p in points])
                self.assertTrue(all(rm.EPOCH<=p[0]<=at for p in points))

    def test_early_market_has_no_fabricated_past_or_future(self):
        q=md.snapshot('1M',rm.EPOCH+901)['coin']
        self.assertEqual([p[0] for p in q['points']],[rm.EPOCH,rm.EPOCH+600])
        self.assertEqual(q['points'][-1][1],q['price'])

    def test_cache_shared_within_tick_and_not_mutable_by_caller(self):
        md._snapshot.cache_clear()
        at=rm.EPOCH+1000
        first=md.snapshot('1D',at);first['coin']['points'][0][1]=-1
        with patch.object(rm,'quote',side_effect=AssertionError('recomputed')):
            second=md.snapshot('1D',at+1)
        self.assertGreater(second['coin']['points'][0][1],0)
        self.assertEqual(md._snapshot.cache_info().hits,1)

    def test_only_allowlisted_ranges(self):
        for bad in ['all','100Y','',None,[],{}]:
            with self.assertRaises(ValueError):md.snapshot(bad)

    def test_http_quotes_never_read_or_write_player_store(self):
        import http.client,json,threading,tempfile
        from pathlib import Path
        from game.storage import Store
        from server import GameServer
        tmp=tempfile.TemporaryDirectory()
        store=Store(Path(tmp.name)/'market-test')
        server=GameServer(('127.0.0.1',0),store)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch.object(store,'read',side_effect=AssertionError('save read')) as reads, patch.object(store,'command',side_effect=AssertionError('save write')) as writes:
                for span,status in [('1D',200),('1M',200),('100Y',400)]:
                    conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
                    conn.request('GET','/api/market?range='+span)
                    response=conn.getresponse();data=json.loads(response.read());conn.close()
                    self.assertEqual(response.status,status)
                    if status==200:self.assertEqual(data['range'],span);self.assertNotIn('state',data)
                reads.assert_not_called();writes.assert_not_called()
        finally:server.shutdown();server.server_close();thread.join();store.close_pool();tmp.cleanup()
