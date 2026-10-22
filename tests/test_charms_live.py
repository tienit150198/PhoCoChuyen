"""🤝 Phụ kiện đôi on the live service (live/charms.py): a 2.5D map walker carries `pr` {kind: count}, read from the game's
table at town_in (never from a frame, never a partner's name); a wear switch reaches walkers already on screen through the
NOTIFY; a database before SCHEMA_VERSION 86 answers nothing and is looked at again only after RETRY."""
import time
import unittest

from game import marriage as mr
from tests.live_support import LiveCase, needs_ws


@needs_ws
class CharmsLive(LiveCase):
    cfg_extra = dict(town=True)

    def paired(self, a, b, kind, cid):
        self.store.transaction(lambda db: db.execute(
            "INSERT INTO friend_charms(id,kind,a,b,status,price,at,paired,wear_a,wear_b) VALUES(?,?,?,?,'paired',130,?,?,1,1)",
            (cid, kind, a, b, time.time(), time.time())))

    async def test_map_walkers_carry_the_pairs_and_a_switch_reaches_the_screen(self):
        (ta, sa), (tb, sb), (tc, sc) = self.account('Lan'), self.account('Mai'), self.account('Châu')
        self.paired(sa, sb, 'tri_ki', 'fc000000000001')
        self.paired(sa, sc, 'chi_cot', 'fc000000000002')
        self.paired(sc, sa, 'chi_cot', 'fc000000000003')
        a, b = await self.connect(ta), await self.connect(tb)
        await a.call('town_in', 'town_room', map='iso-town-v1', x=70, y=44, direction='se')
        room = await b.call('town_in', 'town_room', map='iso-town-v1', x=70, y=44, direction='se')
        lan = next(p for p in room['people'] if p['pid'] == self.pid(sa))
        self.assertEqual(lan['pr'], dict(chi_cot=2, tri_ki=1))
        self.assertNotIn('pr', lan['lk'], 'never inside the look')
        self.assertNotIn('Mai', str(lan['pr']))
        # Lan takes everything off: Mai's screen hears it without a rejoin
        mr.act(self.store, ta, 'charm_wear', dict(all=True, on=False))
        got = []
        for _ in range(8):
            ev = await b.expect('town')
            got = [e for e in ev['ev'] if e.get('pid') == self.pid(sa) and 'pr' in e]
            if got:
                break
        self.assertIsNone(got[-1]['pr'])
        mr.act(self.store, ta, 'charm_wear', dict(id='fc000000000001', on=True))
        for _ in range(8):
            ev = await b.expect('town')
            got = [e for e in ev['ev'] if e.get('pid') == self.pid(sa) and 'pr' in e]
            if got:
                break
        self.assertEqual(got[-1]['pr'], dict(tri_ki=1))


class OlderDatabase(unittest.IsolatedAsyncioTestCase):
    async def test_nothing_until_the_table_exists(self):
        import psycopg
        from types import SimpleNamespace
        from live import charms as LC
        calls = []

        class Db:
            async def fetch(self, sql, args=()):
                calls.append(sql)
                raise psycopg.errors.UndefinedTable('relation "friend_charms" does not exist')
        cache = LC.Charms(SimpleNamespace(db=Db()))
        who = SimpleNamespace(pid='a' * 16, sid='s' * 20)
        self.assertEqual(await cache.of([who]), {})
        n = len(calls)
        self.assertEqual(await cache.of([SimpleNamespace(pid='b' * 16, sid='t' * 20)]), {})
        self.assertEqual(len(calls), n)
        self.assertGreater(cache.off_until, time.monotonic())

    def test_the_frame_counts_known_kinds_only(self):
        from live import charms as LC
        self.assertEqual(LC.frame(['tri_ki', 'chi_cot', 'tri_ki', 'nhan_cuoi']), dict(chi_cot=1, tri_ki=2))
        self.assertIsNone(LC.frame([]))
        self.assertEqual(LC.frame(['ban_than'] * 500), dict(ban_than=LC.COUNT_MAX))
