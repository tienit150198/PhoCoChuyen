"""🪽 Cánh on the live service (live/wings.py): a 2.5D map walker and a street walker carry `wg` {k, r}, read from the game's
table wing_worn at entry (never from a frame); a wing put on or taken off (game/wings.py commit: the row and NOTIFY
{op: 'wing'}) reaches walkers already on screen; a database before SCHEMA_VERSION 90 answers nothing and is looked at again
only after RETRY."""
import time
import unittest

from game import wings as W
from tests.live_support import LiveCase, needs_ws


def wearing(k, r):
    return dict(journey=dict(story=True, wings=dict(v=1, own=[dict(id='w1', k=k, r=r, z=0)], on='w1', seq=2, day=dict(d=0, got=0), rq={})))


@needs_ws
class WingsLive(LiveCase):
    cfg_extra = dict(town=True)

    async def test_map_walkers_carry_the_wings_and_a_change_reaches_the_screen(self):
        (ta, sa), (tb, sb) = self.account('Lan'), self.account('Mai')
        self.store.transaction(lambda db: W.commit(db, sa, wearing('phuong', 7)))
        a, b = await self.connect(ta), await self.connect(tb)
        await a.call('town_in', 'town_room', map='iso-town-v1', x=70, y=44, direction='se')
        room = await b.call('town_in', 'town_room', map='iso-town-v1', x=70, y=44, direction='se')
        lan = next(p for p in room['people'] if p['pid'] == self.pid(sa))
        self.assertEqual(lan['wg'], dict(k='phuong', r=7))
        self.assertNotIn('wg', lan['lk'], 'never inside the look')
        self.store.transaction(lambda db: W.commit(db, sa, dict(journey=dict(story=True))))   # taken off
        got = []
        for _ in range(8):
            ev = await b.expect('town')
            got = [e for e in ev['ev'] if e.get('pid') == self.pid(sa) and 'wg' in e]
            if got:
                break
        self.assertIsNone(got[-1]['wg'])
        self.store.transaction(lambda db: W.commit(db, sa, wearing('buom', 2)))
        for _ in range(8):
            ev = await b.expect('town')
            got = [e for e in ev['ev'] if e.get('pid') == self.pid(sa) and 'wg' in e]
            if got:
                break
        self.assertEqual(got[-1]['wg'], dict(k='buom', r=2))


class OlderDatabase(unittest.IsolatedAsyncioTestCase):
    async def test_nothing_until_the_table_exists(self):
        import psycopg
        from types import SimpleNamespace
        from live import wings as LW
        calls = []

        class Db:
            async def fetch(self, sql, args=()):
                calls.append(sql)
                raise psycopg.errors.UndefinedTable('relation "wing_worn" does not exist')
        cache = LW.Wings(SimpleNamespace(db=Db()))
        self.assertEqual(await cache.of([SimpleNamespace(pid='a' * 16, sid='s' * 20)]), {})
        n = len(calls)
        self.assertEqual(await cache.of([SimpleNamespace(pid='b' * 16, sid='t' * 20)]), {})
        self.assertEqual(len(calls), n)
        self.assertGreater(cache.off_until, time.monotonic())

    def test_the_frame_keeps_known_styles_only(self):
        from live import wings as LW
        self.assertEqual(LW.frame('rong', 7), dict(k='rong', r=7))
        self.assertIsNone(LW.frame('newer', 1))
        self.assertIsNone(LW.frame('rong', 8))
        self.assertIsNone(LW.frame('rong', True))
