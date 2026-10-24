"""🎣 Hồ câu đông vui (live/fish_lake.py, owner 24/10 "map câu cá nhiều người vào vẫn thấy được nhé … để ai câu lên con gì
mình nhìn được ấy", "hồ k tối đa lượng người mỗi bến"): joining and leaving a spot's lake, one lake per spot with no cap
(50 fishers: everyone is there, the frames stay bounded), the cosmetic hints (validated, clamped to the rod's reach, rate
limited, only to viewers looking nearby), the catch broadcast only after a real jr_fish_land committed (game/fishing.py
command_commit → NOTIFY), the feed, the mini card, the bubbles, and the island lake's trip check."""
import json
import secrets
import time
import unittest
from unittest import mock

from game import fish_lb as FL
from game import fishing as F
from game import fishing_content as C
from game import marriage as mr
from live import fish_lake as LK
from live.protocol import LiveError
from tests.live_support import LiveCase
from tests.test_bank import story
from tests.test_leaderboard import FORMAT

LOOK = dict(hair='toc_ngan', top='ao_thun')
PURPLE = C.by_rarity(3)[0]


class Units(unittest.TestCase):
    def test_slots_alternate_from_the_middle(self):
        self.assertEqual([LK.pos(s) for s in range(7)], [0, 1, -1, 2, -2, 3, -3])
        self.assertEqual(len({LK.pos(s) for s in range(500)}), 500)

    def test_hints_are_validated_and_clamped(self):
        self.assertEqual(LK.clean_act(dict(k='cast', d=5000, x=3), 'tre'), dict(k='cast', d=80.0, x=1.0))
        self.assertEqual(LK.clean_act(dict(k='cast', d=1, x=-.2), 'tre'), dict(k='cast', d=15.0, x=-.2))
        self.assertEqual(LK.clean_act(dict(k='cast', d=1900, rod='long_vuong'), 'tre'), dict(k='cast', rod='long_vuong', d=1900.0, x=0.0))
        self.assertEqual(LK.clean_act(dict(k='reel'), 'tre'), dict(k='reel'))
        for bad in (dict(k='catch'), dict(k='cast'), dict(k='cast', d=float('nan')), dict(k='cast', d='9'), dict(k='bite', rod='xx'), {}):
            with self.assertRaises(LiveError, msg=bad):
                LK.clean_act(bad, 'tre')

    def test_client_in_node(self):
        """The client's layout, room and crowd drawing (public/js/v4/fish-lake*.js): tests/fishing-lake.mjs."""
        import shutil
        import subprocess
        from pathlib import Path
        node = shutil.which('node')
        if not node:
            self.skipTest('node is not installed')
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run([node, str(root / 'tests' / 'fishing-lake.mjs')], cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        self.assertIn('fishing-lake: ok', out.stdout)

    def test_slots_match_the_client(self):
        from pathlib import Path
        js = (Path(__file__).resolve().parents[1] / 'public' / 'js' / 'v4' / 'fish-lake-layout.js').read_text(encoding='utf-8')
        self.assertIn("export const posOf=s=>{s=Math.max(0,Math.floor(Number(s)||0));return s===0?0:s%2?(s+1)/2:-(s/2);};", js)

    def test_room_ids(self):
        self.assertEqual(LK.room_id('ho'), 'fl:ho')
        self.assertEqual(LK.room_id('dao', 'ab' * 8), 'fl:dao:' + 'ab' * 8)


class Lake(LiveCase):
    cfg_extra = dict(fish=True, per_ip=200, handshakes_per_ip=400)

    def angler(self, name, account=False):
        """A guest (or a registered player) with a story save (fishing needs the journey)."""
        token, sid = self.account(name) if account else self.guest(name)
        rev = self.store.read(token)[1]
        self.store.command(token, 'imp-' + secrets.token_hex(4), rev, None, 'import_save', {'save': {'format': FORMAT, 'state': story(wallet=1000)}})
        with self.store.connect() as db:   # the import rewrites the board's row: the character's name again
            if not account:
                db.execute('INSERT INTO leaderboard_players(sid, name, updated) VALUES(?, ?, ?) ON CONFLICT(sid) DO UPDATE SET name=excluded.name',
                           (sid, name, time.time()))
        return token, sid

    async def enter(self, token, spot='ho', **extra):
        c = await self.connect(token)
        c.pid = self.pid(self.store.key(token))
        c.room = await c.call('fl_in', 'fl_room', spot=spot, look=LOOK, g='female', **extra)
        return c

    async def ev(self, c, kind, timeout=3.0):
        while True:
            f = await c.expect('fl', timeout=timeout)
            for e in f['ev']:
                if e['k'] == kind:
                    return e

    def land(self, token, sp, g, *, ok=True, early=False, spot='ho'):
        """A fish hooked a moment ago, landed now through the real command path (game/storage.py → command_commit)."""
        t = time.time()
        rnd = secrets.token_hex(16)
        hook = t - (0.2 if early else 10)

        def put(s):
            d = F.ensure(s)
            d['act'] = dict(id=rnd, at=t - 30, spot=spot, trip='', rod='tre', dist=12.0, zone=0, kind='fish', sp=sp, g=g,
                            bite=hook - 2, hook=hook, reel=4.0, snap=0, nib=[])
        mr._mutate(self.store, {self.store.key(token): put})
        rev = self.store.read(token)[1]
        with mock.patch.object(F, 'now', lambda: t), mock.patch.object(FL, 'now', lambda: t):
            return self.store.command(token, 'land-' + rnd[:8], rev, None, 'jr_fish_land', {'round': rnd, 'ok': ok})

    async def test_join_see_each_other_and_leave(self):
        a_tok, a_sid = self.angler('Lan Cau')
        b_tok, _ = self.angler('Minh Moi')
        a = await self.enter(a_tok, fh=None, rod='truc')
        self.assertEqual((a.room['spot'], a.room['s'], a.room['n'], a.room['people'], a.room['far'], a.room['feed']), ('ho', 0, 1, [], [], []))
        b = await self.enter(b_tok)
        self.assertEqual(b.room['s'], 1)
        self.assertEqual(b.room['n'], 2)
        seen = b.room['people'][0]
        self.assertEqual((seen['pid'], seen['name'], seen['s'], seen['rod'], seen['g']), (a.pid, 'Lan Cau', 0, 'truc', 'female'))
        self.assertEqual(seen['lk']['hair'], 'toc_ngan')
        came = await self.ev(a, 'in')
        self.assertEqual((came['pid'], came['name'], came['s']), (b.pid, 'Minh Moi', 1))
        self.assertIn('lk', came)
        other = await self.enter(self.angler('O Song')[0], spot='song')   # another spot: another lake
        self.assertEqual((other.room['n'], other.room['s']), (1, 0))
        await a.nothing('fl', wait=.3)
        await b.call('fl_out', 'fl_left')
        self.assertEqual((await self.ev(a, 'out'))['pid'], b.pid)
        b2 = await self.enter(b_tok)   # back: the same place
        self.assertEqual(b2.room['s'], 1)
        await b2.close()
        self.assertEqual((await self.ev(a, 'out'))['pid'], b.pid)
        self.assertNotIn(a_sid, json.dumps(b.frames + [b.room, b2.room]))

    async def test_fifty_fishers_share_one_lake_and_the_frames_stay_small(self):
        clients = []
        for i in range(50):
            clients.append(await self.enter(self.angler(f'Ca Thu {i}')[0]))
        last = clients[-1]
        self.assertEqual(last.room['n'], 50)
        self.assertEqual(sorted(c.room['s'] for c in clients), list(range(50)))
        self.assertEqual(len(last.room['people']), LK.FULL)
        self.assertEqual(len(last.room['people']) + len(last.room['far']), 49)
        self.assertTrue(all(set(x) == {'pid', 'name', 's'} for x in last.room['far']))
        near = [abs(LK.pos(x['s']) - LK.pos(last.room['s'])) for x in last.room['people']]
        far = [abs(LK.pos(x['s']) - LK.pos(last.room['s'])) for x in last.room['far']]
        self.assertLessEqual(max(near), min(far))
        self.assertLess(len(json.dumps(last.room)), 24_000)
        # the middle fisher (slot 0) sees the newcomer at slot 49 (pos 25) only as a name: its look is not sent
        first = clients[0]
        for _ in range(49):
            e = await self.ev(first, 'in')
        self.assertEqual(set(e), {'k', 'pid', 'name', 's'})
        # a cast at the far end reaches its neighbours, not the middle
        await last.send(t='fl_act', k='cast', d=40, x=.1)
        hint = await self.ev(clients[-3], 'act')
        self.assertEqual((hint['pid'], hint['a'], hint['d'], hint['x']), (last.pid, 'cast', 40.0, .1))
        await first.nothing('fl', wait=.4)
        # looking that way: the whole entries there, and the hints from then on
        near_end = await first.call('fl_view', 'fl_near', c=LK.pos(49))
        self.assertIn(last.pid, {x['pid'] for x in near_end['people']})
        self.assertLessEqual(len(near_end['people']), LK.FULL)
        await last.send(t='fl_act', k='reel')
        self.assertEqual((await self.ev(first, 'act'))['pid'], last.pid)

    async def test_hints_validated_and_rate_limited(self):
        a = await self.enter(self.angler('Lan Cau')[0])
        b = await self.enter(self.angler('Minh Moi')[0])
        await self.ev(a, 'in')
        await b.send(t='fl_act', k='cast', d=99999, x=.4)
        hint = await self.ev(a, 'act')
        self.assertEqual((hint['pid'], hint['a'], hint['d'], hint['x']), (b.pid, 'cast', 80.0, .4))   # Cần tre reaches 80 m at most
        await b.send(t='fl_act', k='catch', s='ca_chep')
        self.assertEqual((await b.expect('error'))['code'], 'bad')
        await b.send(t='fl_act', k='cast', d=10, rod='zzz')
        self.assertEqual((await b.expect('error'))['code'], 'bad')
        for _ in range(20):
            await b.send(t='fl_act', k='bite')
        self.assertEqual((await b.expect('error', code='slow'))['code'], 'slow')
        late = await self.enter(self.angler('Den Sau')[0])
        mid = next(x for x in late.room['people'] if x['pid'] == b.pid)
        self.assertEqual(mid['a'], dict(k='bite'))   # a newcomer sees the bobber already out
        out = await self.connect(self.angler('Ngoai Ho')[0])
        await out.send(t='fl_act', k='cast', d=10)
        self.assertEqual((await out.expect('error'))['code'], 'no_lake')
        await out.send(t='fl_in', spot='bien_xa', look=LOOK)
        self.assertEqual((await out.expect('error'))['code'], 'bad')

    async def test_the_catch_comes_from_the_server_after_a_real_landing(self):
        a_tok, _ = self.angler('Lan Cau')
        b_tok, _ = self.angler('Minh Moi', account=True)
        a = await self.enter(a_tok)
        b = await self.enter(b_tok)
        await self.ev(a, 'in')
        with self.assertRaises(Exception):   # reeled for 0.2 s: refused, rolled back, nothing to see
            self.land(b_tok, PURPLE['id'], 34_000, early=True)
        await a.nothing('fl', wait=.5)
        self.land(b_tok, PURPLE['id'], 34_000)
        e = await self.ev(a, 'catch')
        self.assertEqual((e['pid'], e['s'], e['g'], e['r']), (b.pid, PURPLE['id'], 34_000, 3))
        self.assertEqual((e['feed']['name'], e['feed']['s']), ('Minh Moi', PURPLE['id']))
        mine = await self.ev(b, 'catch')   # the catcher's own lake hears it too
        self.assertEqual(mine['pid'], b.pid)
        c = await self.enter(self.angler('Den Sau')[0])
        self.assertEqual([(x['name'], x['s'], x['g']) for x in c.room['feed']], [('Minh Moi', PURPLE['id'], 34_000)])
        await self.ev(a, 'in')
        self.land(b_tok, PURPLE['id'], 34_000, ok=False)   # it got away: nothing
        await a.nothing('fl', wait=.5)
        card = await a.call('fl_card', 'fl_card', pid=b.pid)
        self.assertEqual((card['name'], card['today']['s'], card['today']['g']), ('Minh Moi', PURPLE['id'], 34_000))
        self.assertEqual((card['best']['s'], card['best']['g'], card['dex']), (PURPLE['id'], 34_000, 1))
        hidden = await b.call('fl_card', 'fl_card', pid=a.pid)   # a guest off the boards: only what the lake saw today
        self.assertEqual(set(hidden) - {'t'}, {'pid', 'name'})
        await a.send(t='fl_card', pid='0' * 16)
        self.assertEqual((await a.expect('error'))['code'], 'gone')

    async def test_a_catch_at_another_spot_or_outside_the_lake_shows_nothing(self):
        a_tok, _ = self.angler('Lan Cau')
        b_tok, _ = self.angler('Minh Moi')
        a = await self.enter(a_tok)
        b = await self.enter(b_tok)
        await self.ev(a, 'in')
        self.land(b_tok, PURPLE['id'], 30_000, spot='song')   # fished at the river from another tab
        await a.nothing('fl', wait=.5)
        await b.call('fl_out', 'fl_left')
        await self.ev(a, 'out')
        self.land(b_tok, PURPLE['id'], 30_000)
        await a.nothing('fl', wait=.5)

    async def test_bubbles_near_me(self):
        tok, _ = self.account('Hoa Gio')
        a = await self.enter(tok)
        b = await self.enter(self.angler('Minh Moi')[0])
        await self.ev(a, 'in')
        await a.send(t='fl_say', text='Cá cắn chưa?')
        said = await self.ev(b, 'said')
        self.assertEqual((said['pid'], said['text']), (a.pid, 'Cá cắn chưa?'))
        self.assertEqual((await self.ev(a, 'said'))['text'], 'Cá cắn chưa?')

    async def test_the_island_lake_needs_the_trip(self):
        c = await self.connect(self.angler('Lan Cau')[0])
        await c.send(t='fl_in', spot='dao', trip='ab' * 8, look=LOOK)
        self.assertEqual((await c.expect('error'))['code'], 'no_island')
        await c.send(t='fl_in', spot='dao', trip='zz', look=LOOK)
        self.assertEqual((await c.expect('error'))['code'], 'bad')


if __name__ == '__main__':
    unittest.main()
