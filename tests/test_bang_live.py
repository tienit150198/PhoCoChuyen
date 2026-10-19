"""⚔️ Bang on the live service (live/bangs.py): the bang's chat group follows its members (join → the chat in the list,
leave / kick → gone; nobody leaves it by hand), the tag beside a name on chat messages and on 2.5D map walkers (read
from the game's tables, never from a frame; a change reaches walkers already on screen), and `bang_me` / `bang_invite`
to the players concerned."""
import asyncio
import time
import unittest

from game import bang
from tests.live_support import LiveCase, needs_ws


@needs_ws
class BangLive(LiveCase):
    cfg_extra = dict(town=True)

    def aged(self, sid, days=30):
        born = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - days * 86400))
        with self.store.connect() as db:
            db.execute('UPDATE accounts SET created_at=? WHERE sid=?', (born, sid))

    def found(self, sid, name='Rồng Đỏ'):
        """The founding's database part (the save's payment is tests/test_bang.py's business)."""
        self.aged(sid)
        x = dict(n=1, k='found', a=5_000_000, at=int(time.time()))
        info = dict(k='found', n=1, name=name, emoji='🐉', color='do', motto='Đoàn kết', open=True)
        self.store.transaction(lambda db: bang._found_commit(db, sid, bang.pid_of(sid), x, info, time.time()))
        with self.store.connect() as db:
            return dict(db.execute("SELECT * FROM bangs WHERE created_by=?", (sid,)).fetchone())

    async def test_chat_group_follows_members_and_tags(self):
        (ta, sa), (tb, sb) = self.account('Lan'), self.account('Minh')
        b0 = self.found(sa)
        ch = b0['channel']
        a = await self.connect(ta)
        self.assertIn(ch, [c['id'] for c in a.welcome['chans']])
        self.assertEqual(next(c for c in a.welcome['chans'] if c['id'] == ch)['kind'], 'group')
        b = await self.connect(tb)
        self.assertNotIn(ch, [c['id'] for c in b.welcome['chans']])
        bang.post(self.store, tb, 'join', dict(bang=b0['id']))
        f = await b.expect('chan')
        self.assertEqual(f['chan']['id'], ch)
        await b.expect('bang_me')
        # Minh writes in the bang's chat: Lan sees his tag beside the name
        await b.send(t='send', ch=ch, text='Chào cả bang!', cid='m1')
        m = await a.expect('msg', ch=ch)
        self.assertEqual(m['bg'], dict(n='Rồng Đỏ', e='🐉', c='do', r='tv'))
        mine = await b.expect('msg', ch=ch)
        self.assertEqual(mine['bg']['r'], 'tv')
        # a page of history carries the tag now (the role changed since)
        bang.post(self.store, ta, 'role', dict(pid=self.pid(sb), role='pho'))
        await b.expect('bang_me')
        await b.send(t='history', ch=ch)
        h = await b.expect('history')
        self.assertEqual([x['bg']['r'] for x in h['msgs'] if x['pid'] == self.pid(sb)], ['pho'])
        # nobody leaves the bang's chat by hand
        await b.send(t='group_leave', ch=ch)
        err = await b.expect('error')
        self.assertEqual(err['code'], 'bang')
        await b.send(t='group_add', ch=ch, pids=[])
        self.assertEqual((await b.expect('error'))['code'], 'owner')
        # leaving the bang takes the chat away
        bang.post(self.store, ta, 'role', dict(pid=self.pid(sb), role='tv'))
        bang.post(self.store, tb, 'leave', dict(confirm=True))
        u = await b.expect('unchan')
        self.assertEqual(u['ch'], ch)
        await b.send(t='send', ch=ch, text='còn ai không', cid='m2')
        self.assertEqual((await b.expect('error'))['code'], 'no_chat')

    async def test_map_walkers_carry_the_tag(self):
        (ta, sa), (tb, sb) = self.account('Lan'), self.account('Minh')
        b0 = self.found(sa)
        a, b = await self.connect(ta), await self.connect(tb)
        await a.call('town_in', 'town_room', map='iso-town-v1', x=70, y=44, direction='se')
        room = await b.call('town_in', 'town_room', map='iso-town-v1', x=70, y=44, direction='se')
        lan = next(p for p in room['people'] if p['pid'] == self.pid(sa))
        self.assertEqual((lan['bg']['n'], lan['bg']['r']), ('Rồng Đỏ', 'chu'))
        minh = None
        for _ in range(5):
            ev = await a.expect('town')
            minh = next((e for e in ev['ev'] if e.get('pid') == self.pid(sb) and e['k'] == 'in'), None)
            if minh:
                break
        self.assertNotIn('bg', minh)
        # Minh joins while both walk: Lan's screen gets his tag without a rejoin
        bang.post(self.store, tb, 'join', dict(bang=b0['id']))
        for _ in range(5):
            ev = await a.expect('town')
            got = [e for e in ev['ev'] if e.get('pid') == self.pid(sb) and 'bg' in e]
            if got:
                break
        self.assertEqual(got[-1]['bg']['r'], 'tv')
        # an admin hides the bang: the tag goes
        bang.admin_act(self.store, 'op', dict(op='hide', id=b0['id']))
        for _ in range(5):
            ev = await b.expect('town')
            got = [e for e in ev['ev'] if e.get('pid') == self.pid(sa) and 'bg' in e]
            if got:
                break
        self.assertIsNone(got[-1]['bg'])

    async def test_invite_reaches_the_player(self):
        (ta, sa), (tb, sb) = self.account('Lan'), self.account('Minh')
        self.found(sa)
        b = await self.connect(tb)
        from game import marriage as mr
        code = mr.ensure_person(self.store, sb)['code']
        bang.post(self.store, ta, 'invite', dict(code=code))
        f = await b.expect('bang_invite')
        self.assertEqual((f['name'], f['e']), ('Rồng Đỏ', '🐉'))

    async def test_a_bang_change_retags_only_its_members(self):
        """Review fix 19/10: a leader's settings or an operator's hide drop only that bang's cached tags, not everyone's."""
        from live import bangs as LB
        (ta, sa), (tc, sc), (tx, sx) = self.account('Lan'), self.account('Châu'), self.account('Xuân')
        b0, b1 = self.found(sa, 'Rồng Đỏ'), self.found(sc, 'Hổ Xám')
        tags = LB.of_app(self.app)
        pa, pc, px = (bang.pid_of(s) for s in (sa, sc, sx))
        got = await tags.of([pa, pc, px])
        self.assertEqual((got[pa]['n'], got[pc]['n'], px in got), ('Rồng Đỏ', 'Hổ Xám', False))
        self.assertEqual(tags.of_bang(b0['id']), {pa})
        kept_c, kept_x = tags.rows.get(pc), tags.rows.get(px)
        await self.app.by_name['bang'].on_notify(dict(op='bang', bang=b0['id'], pids=[]))
        self.assertIsNone(tags.rows.get(pa))                                     # read again on its next use
        self.assertIs(tags.rows.get(pc), kept_c)                                 # another bang's member: kept
        self.assertIs(tags.rows.get(px), kept_x)
        bang.post(self.store, ta, 'set', dict(color='mint'))                    # the NOTIFY names its members
        for _ in range(30):
            if tags.rows.get(pa) is None:
                break
            await asyncio.sleep(0.1)
        self.assertEqual((await tags.of([pa]))[pa]['c'], 'mint')
        self.assertIs(tags.rows.get(px), kept_x)


class OlderDatabase(unittest.IsolatedAsyncioTestCase):
    async def test_tags_answer_nothing_until_the_tables_exist(self):
        """Deploy order (review 19/10, verified): a live service on a database before SCHEMA_VERSION 57 answers {} for
        every tag and looks again only after RETRY seconds (no query storm, nothing breaks)."""
        import psycopg
        from types import SimpleNamespace
        from live import bangs as LB
        calls = []

        class Db:
            async def fetch(self, sql, args=()):
                calls.append(sql)
                raise psycopg.errors.UndefinedTable('relation "bang_members" does not exist')

            async def fetchrow(self, sql, args=()):
                calls.append(sql)
                raise psycopg.errors.UndefinedTable('relation "bang_week_win" does not exist')
        tags = LB.Bangs(SimpleNamespace(db=Db()))
        self.assertEqual(await tags.of(['a' * 16]), {})
        n = len(calls)
        self.assertEqual(await tags.of(['b' * 16]), {})
        self.assertEqual(len(calls), n)                                          # off until RETRY
        self.assertGreater(tags.off_until, time.monotonic())
