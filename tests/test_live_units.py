"""Live service parts without sockets: filters (the owner's tone rule), rate limits, the slow-client cutoff,
cookie parsing, the reward writer (daily caps, idempotency) and the feature dispatcher."""
import asyncio
import tempfile
import time
import unittest
from pathlib import Path

from game import social
from game.storage import Store
from live import filters
from live.auth import clean_name, pid_of, token_from
from live.config import Config
from live.db import PgDB, to_pg
from live.hub import Hub
from live.limits import LRU, Bucket, Keyed, Window


class FilterTests(unittest.TestCase):
    def m(self, text):
        return filters.mask(filters.clean(text, 1000))

    def test_contacts_are_masked(self):
        cases = {
            'gọi 0912 345 678 nhé': 'gọi ••• nhé',
            'sđt 0912.345.678': 'sđt •••',
            '+84 912345678': '•••',
            'stk 1903 4567 8901 23': 'stk •••',
            'vào https://abc.com/x xem': 'vào ••• xem',
            'web shopee.vn đó': 'web ••• đó',
            'www.abc.net': '•••',
            'add zalo minh123': 'add zalo •••',
            'fb: nguyen.van.a': 'fb: •••',
            'insta xinhdep99': 'insta •••',
            '@hoanganh99 nè': '••• nè',
            'mail a.b@gmail.com nha': 'mail ••• nha',
        }
        for text, want in cases.items():
            self.assertEqual(self.m(text), want, text)

    def test_owner_tone_rule(self):
        # GenZ slang and rude banter stay as written (owner, 30/09)
        for text in ('vl thật', 'vcl luôn', 'đm cái tiệm', 'cút mẹ mày đi', 'ib zalo nha', 'tiệm lời 100.000.000 xu',
                     'con đĩa', 'buổi sáng', 'các bạn ơi', 'lon nước', 'số nhà 123', 'lên level 12'):
            self.assertEqual(self.m(text), text, text)
        # heavy, direct profanity only
        for text, want in {'địt mẹ mày': '••• mẹ mày', 'lồnnnn': '•••', 'đồ đĩ': 'đồ •••', 'fuuuck you': '••• you', 'dit me may': '••• may'}.items():
            self.assertEqual(self.m(text), want, text)

    def test_clean(self):
        self.assertEqual(filters.clean('  a​  b\n\n\n\nc\x07 ', 300), 'a b\n\nc')
        self.assertEqual(filters.clean('1\n2\n3\n4\n5\n6', 300, lines=3), '1\n2\n3 4 5 6')
        self.assertIsNone(filters.clean('   ', 300))
        self.assertIsNone(filters.clean('x' * 301, 300))
        self.assertIsNone(filters.clean(5, 300))
        self.assertEqual(filters.clean('e' + '\u0301' * 4, 10), '\u00e9' + '\u0301' * 2)   # no zalgo walls: two marks at most (NFC first)

    def test_fingerprint(self):
        self.assertEqual(filters.fingerprint('Chào CẢ phố!!'), filters.fingerprint('chào cả   phố'))


class LimitTests(unittest.TestCase):
    def test_window_and_bucket(self):
        w = Window(2, 10)
        self.assertTrue(w.hit(100))
        self.assertTrue(w.hit(101))
        self.assertFalse(w.hit(102))
        self.assertAlmostEqual(w.wait(102), 8)
        self.assertTrue(w.hit(110.5))
        b = Bucket(rate=0.001, burst=3)
        self.assertEqual([b.take() for _ in range(4)], [True, True, True, False])

    def test_bounded(self):
        lru = LRU(3)
        for i in range(5):
            lru.put(i, i)
        self.assertEqual(list(lru), [2, 3, 4])
        lru.get(2)
        lru.put(9, 9)
        self.assertEqual(list(lru), [4, 2, 9])
        k = Keyed(1, 60, cap=2)
        self.assertTrue(k.hit('a'))
        self.assertFalse(k.hit('a'))
        k.hit('b')
        k.hit('c')
        self.assertEqual(len(k.keys), 2)


class _Transport:
    def __init__(self, size):
        self.size, self.aborted = size, False

    def get_write_buffer_size(self):
        return self.size

    def abort(self):
        self.aborted = True


class _WS:
    def __init__(self, size):
        self.transport = _Transport(size)


class _Conn:
    def __init__(self, size):
        self.ws, self.closing = _WS(size), False

    def buffered(self):
        return self.ws.transport.get_write_buffer_size()


class HubTests(unittest.TestCase):
    def test_slow_client_is_cut_off(self):
        hub = Hub(Config())
        written = []
        hub.write = lambda wss, data, text: written.append((len(wss), data))
        fast, slow = _Conn(10), _Conn(300 * 1024)
        self.assertEqual(hub.send_many([fast, slow], {'t': 'msg', 'text': 'x'}), 1)
        self.assertTrue(slow.ws.transport.aborted and slow.closing)
        self.assertFalse(fast.ws.transport.aborted)
        self.assertEqual(written, [(1, b'{"t":"msg","text":"x"}')])
        self.assertEqual(hub.send_many([slow], {'t': 'x'}), 0)   # closing: skipped
        self.assertEqual(hub.cut, 1)


class AuthTests(unittest.TestCase):
    def test_helpers(self):
        t = 'ab' * 32
        self.assertEqual(token_from(f'a=1; mnl_session={t}; b=2'), t)
        self.assertIsNone(token_from('mnl_session=short'))
        self.assertIsNone(token_from(None))
        self.assertEqual(pid_of('x' * 64), social.pid_of('x' * 64))
        self.assertEqual(clean_name(' <b>Hoa</b> '), 'bHoa/b')
        self.assertEqual(clean_name('Mây'), '')   # the default character name is no name

    def test_sql_translation(self):
        self.assertEqual(to_pg("SELECT 1 WHERE a=? AND b LIKE 'x%'"), "SELECT 1 WHERE a=%s AND b LIKE 'x%%'")


class EffectsTests(unittest.IsolatedAsyncioTestCase):
    async def test_grant_caps_and_idempotency(self):
        from live.effects import grant
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / 'g.db')
            db = PgDB(store.pg.url, store.pg.schema)
            try:
                self.assertTrue(await grant(db, 's1', 'coins', 5, key='env:1', cap=12))
                self.assertFalse(await grant(db, 's1', 'coins', 5, key='env:1', cap=12))   # same key: once
                self.assertTrue(await grant(db, 's1', 'coins', 5, key='env:2', cap=12))
                self.assertFalse(await grant(db, 's1', 'coins', 5, key='env:3', cap=12))   # over today's cap
                self.assertTrue(await grant(db, 's2', 'coins', 5, key='env:4', cap=12))
                with self.assertRaises(ValueError):
                    await grant(db, 's1', 'gold', 5, key='x')
                rows = await db.fetch('SELECT id, status FROM live_effects ORDER BY id')
                self.assertEqual([(r['id'], r['status']) for r in rows], [('env:1', 'pending'), ('env:2', 'pending'), ('env:4', 'pending')])
            finally:
                await db.close()
                store.close_pool()


class DispatcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_switch_off_and_duplicates(self):
        from live.protocol import Dispatcher, Feature, on

        class App:
            cfg = Config(chat=False)
            hub = Hub(cfg)

        class Street(Feature):
            name, flag = 'street', 'street'

            @on('move', rate=(1, 60))
            async def move(self, conn, f):
                return {'t': 'moved'}

        class Clash(Feature):
            @on('move')
            async def other(self, conn, f):
                return None

        app = App()
        sent = []
        app.hub.send = lambda conn, frame: sent.append(frame)
        d = Dispatcher([Street(app)])

        class P:
            rates = {}
        conn = type('C', (), {'player': P()})()
        await d.dispatch(conn, {'t': 'move', 'cid': 'a'})
        self.assertEqual(sent[-1], dict(t='error', code='off', msg='Tính năng này đang tắt.', ref='a'))
        app.cfg.street = True
        await d.dispatch(conn, {'t': 'move'})
        self.assertEqual(sent[-1], {'t': 'moved'})
        await d.dispatch(conn, {'t': 'move'})
        self.assertEqual(sent[-1]['code'], 'slow')
        with self.assertRaises(RuntimeError):
            Dispatcher([Street(app), Clash(app)])


if __name__ == '__main__':
    unittest.main()
