"""🏅 Danh hiệu bên tên (live/honours.py): every honour title a player holds now goes out as `tt` beside the name —
the weekly leaderboard tops (lb_weekly), the fair titles kept in the save, the wedding race — on chat messages (live,
pages, reply quotes) and street walkers/cards; read from the game's records, cached, refreshed on NOTIFY; an older
client keeps every field it knew. Plus the game side (the NOTIFYs) and the client's names (public/js/v4/honours.js)."""
import asyncio
import json
import re
import time
import unittest
from pathlib import Path

from tests.live_support import LiveCase

ROOT = Path(__file__).resolve().parent.parent


class Unit(unittest.TestCase):
    def test_order_cache_notify_and_a_database_without_the_tables(self):
        from live import honours
        from live.db import Error as DbError

        class DB:
            calls = []
            missing = False
            state = {'sid-a': json.dumps({'journey': {'titles': {'g_first': 1, 'f_bao': 3, 'f_king': 9, 'f_raid': 4}}})}
            lb = [dict(sid='sid-a', board='milk_tea', rank=1), dict(sid='sid-a', board='wealth', rank=3),
                  dict(sid='sid-a', board='titles', rank=11), dict(sid='sid-b', board='all', rank=1)]

            async def fetch(self, sql, args=()):
                DB.calls.append(sql.split()[1] if 'lb_weekly' not in sql else 'lb')
                if DB.missing:
                    raise DbError[0]('no table')
                if 'lb_weekly' in sql:
                    return list(DB.lb)
                if 'FROM profiles' in sql:
                    return [dict(pid=p, sid='sid-' + p, ti=json.loads(DB.state['sid-' + p])['journey']['titles'] and
                                 json.dumps(json.loads(DB.state['sid-' + p])['journey']['titles'])) for p in args if 'sid-' + p in DB.state]
                return []

        class Wed:
            race_ids = {'a': 'w_vip', 'z': 'w_nope'}

            def enabled(self):
                return True

        class App:
            db = DB()
            by_name = {'wedding': Wed()}
            hub = None

        app = App()
        h = honours.of_app(app)
        got = asyncio.run(h.of(['a', 'b', 'z', 'admin']))
        # the leaderboard first (its order of honour: tier — a workplace's top 1 before a top 3 —, then main boards), then the fair's awards, the
        # wedding race, the fair's rounds; a rank without a title and an unknown race id are left out
        self.assertEqual(got['a'], ['lb_milk_tea_1', 'lb_wealth_3', 'f_king', 'w_vip', 'f_bao', 'f_raid'])
        self.assertEqual(got['b'], [])   # no save / no profile here: nothing (its sid is unknown)
        self.assertNotIn('admin', got)
        n = len(DB.calls)
        asyncio.run(h.of(['a', 'b']))
        self.assertEqual(len(DB.calls), n)                       # cached: no query at all
        DB.state['sid-a'] = json.dumps({'journey': {'titles': {'f_dart': 1}}})
        honours.on_notify(app, {'op': 'honours', 'pid': 'a'})    # a title was granted
        self.assertEqual(asyncio.run(h.of(['a']))['a'], ['lb_milk_tea_1', 'lb_wealth_3', 'w_vip', 'f_dart'])
        self.assertEqual(len(DB.calls), n + 1)                   # only that player read again
        DB.lb = []                                                # a new week: last week's holders are gone
        honours.on_notify(app, {'op': 'honours_lb'})
        self.assertEqual(asyncio.run(h.of(['a']))['a'], ['w_vip', 'f_dart'])
        Wed.race_ids = {}
        self.assertEqual(asyncio.run(h.of(['a']))['a'], ['f_dart'])
        # frames: a copy with `tt` (buffered frames are never mutated), none when there is nothing
        frames = [dict(pid='a', text='x'), dict(pid='b', text='y', tt=['f_bao'])]
        out = asyncio.run(honours.with_honours(app, frames))
        self.assertEqual(out, [dict(pid='a', text='x', tt=['f_dart']), dict(pid='b', text='y')])
        self.assertEqual(frames[0], dict(pid='a', text='x'))
        # a database from before lb_weekly / a failing read: no titles, never an error, not asked again at once
        app2 = type('App2', (), dict(db=DB(), by_name={}, hub=None))()
        DB.missing = True
        self.assertEqual(asyncio.run(honours.of_app(app2).of(['a'])), {'a': []})
        n = len(DB.calls)
        self.assertEqual(asyncio.run(honours.of_app(app2).of(['c'])), {'c': []})
        self.assertEqual(len(DB.calls), n)

    def test_fair_ids_are_the_fair_titles_only(self):
        from live import honours
        self.assertEqual(honours.fair_ids({'f_master': 1, 'f_oaq': 2, 'w_vip': 3, 'g_first': 4, 'x': 5}), ('f_master', 'f_oaq'))
        self.assertEqual(honours.fair_ids(None), ())
        self.assertEqual(honours._ids('not json'), ())
        self.assertEqual(honours._ids(None), ())

    def test_game_announces_granted_titles(self):
        from game import live_chat

        class DB:
            def __init__(self):
                self.sent = []

            def execute(self, sql, args=()):
                self.sent.append(json.loads(args[1]))

        db = DB()
        live_chat.honours_commit(db, 's' * 64, 'fair_bc', dict(fair=dict(titles=['f_bao'])))
        live_chat.honours_commit(db, 's' * 64, 'fair_bc', dict(fair=dict(won=3)))                     # no title
        live_chat.honours_commit(db, 's' * 64, 'live_fx', dict(message='Danh hiệu mới: x.', live=dict(kind='title')))
        live_chat.honours_commit(db, 's' * 64, 'live_fx', dict(message='', live=dict(kind='title')))   # already held
        live_chat.honours_commit(db, 's' * 64, 'live_fx', dict(message='+5 xu', live=dict(kind='coins')))
        live_chat.honours_commit(db, 's' * 64, 'jr_spend_style', dict(fair=dict(titles=['f_bao'])))
        pid = live_chat.pid_of('s' * 64)
        self.assertEqual(db.sent, [dict(op='honours', pid=pid), dict(op='honours', pid=pid)])


class ClientNames(unittest.TestCase):
    """public/js/v4/honours.js mirrors the game's names."""

    @classmethod
    def setUpClass(cls):
        cls.js = (ROOT / 'public/js/v4/honours.js').read_text(encoding='utf-8')

    def block(self, name):
        m = re.search(r'const ' + name + r'=\{(.*?)\n\};|const ' + name + r'=\{(.*?)\};', self.js, re.S)
        return m.group(1) or m.group(2)

    def test_boards_careers_fair_and_race(self):
        from game import lb_titles as lbt
        from game.fair import TITLE_ROWS
        from game.wedding_live import TITLE_NAMES
        boards = self.block('BOARDS')
        for board, tiers in lbt.BOARD_TITLES.items():
            row = re.search(board + r":\['[^']+',\[(.*)\]\]", boards).group(1)
            self.assertEqual(re.findall(r"\['([^']+)','([^']+)'\]", row), [tuple(t) for t in tiers], board)
        nouns = dict(re.findall(r"([a-z_]+):'([^']+)'", self.block('NOUN')))
        self.assertEqual(nouns, lbt.CAREER_NOUN)
        events = {k: (e, n) for k, e, n in re.findall(r"(\w+):\['([^']+)','([^']+)','[^']+','[^']+'\]", self.block('EVENT'))}
        for tid, emoji, name, _ in TITLE_ROWS:
            self.assertEqual(events.get(tid), (emoji, name), tid)
        for tid in ('w_vip', 'w_pro'):
            self.assertEqual(' '.join(events[tid]), TITLE_NAMES[tid])
        self.assertIn("pagoda:['🪷','Siêng việc chùa nhất tuần'", self.js)
        self.assertEqual(lbt.CAREER_TITLE['pagoda'], ('🪷', 'Siêng việc chùa nhất tuần'))


class LiveFrames(LiveCase):
    cfg_extra = dict(street=True)

    def save(self, sid, titles):
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps({'journey': {'titles': titles}}), sid))

    def holds(self, sid, board, rank):
        with self.store.connect() as db:
            db.execute('INSERT INTO lb_weekly(week,board,rank,sid,score,title,final,day,at) VALUES(?,?,?,?,?,?,?,?,?)',
                       ('2026-W41', board, rank, sid, 100, 'x', 0, '2026-10-07', time.time()))

    def notify(self, **event):
        from game import live_chat
        with self.store.connect() as db:
            live_chat.notify(db, event)

    async def test_chat_frames_carry_tt_and_refresh_on_notify(self):
        self.cfg.town_every = 0
        ta, sa = self.account('Lan Anh')
        tb, sb = self.account('Minh Tú')
        self.befriend(sa, sb)
        self.save(sa, {'g_first': 1, 'f_bao': 2, 'f_dart': 3})
        self.holds(sa, 'wealth', 3)
        a, b = await self.connect(ta), await self.connect(tb)
        for c in (a, b):
            await c.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='ai biết chỗ mua trà sữa không', cid='q')
        mine = await a.expect('msg', cid='q')
        self.assertEqual(mine['tt'], ['lb_wealth_3', 'f_bao', 'f_dart'])
        seen = await b.expect('msg', id=mine['id'])
        self.assertEqual(seen['tt'], ['lb_wealth_3', 'f_bao', 'f_dart'])
        # an older client: every field it knew is there, as before; `ti`/`st` untouched (nobody bought one)
        for k in ('t', 'ch', 'id', 'pid', 'name', 'av', 'text', 'at'):
            self.assertIn(k, seen)
        self.assertNotIn('st', seen)
        # the reply ("hỏi đáp"): the quoted author's titles ride on the quote; Minh Tú has none
        await b.send(t='send', ch='town', text='ở đầu hẻm á', cid='r', reply_to=mine['id'])
        reply = await b.expect('msg', cid='r')
        self.assertNotIn('tt', reply)
        self.assertEqual(reply['reply']['tt'], ['lb_wealth_3', 'f_bao', 'f_dart'])
        page = await b.call('history', 'history', ch='town')
        self.assertEqual([m.get('tt') for m in page['msgs'][-2:]], [['lb_wealth_3', 'f_bao', 'f_dart'], None])
        # a DM carries them too
        await a.send(t='send', to=self.pid(sb), text='chào', cid='dm')
        dm = await b.expect('msg', text='chào')
        self.assertEqual(dm['tt'], ['lb_wealth_3', 'f_bao', 'f_dart'])
        # a new title is granted (the game announces it): the next message has it, no restart
        self.save(sa, {'f_bao': 2, 'f_dart': 3, 'f_king': 9})
        self.notify(op='honours', pid=self.pid(sa))
        await asyncio.sleep(0.3)
        await a.send(t='send', ch='town', text='có thêm danh hiệu nè', cid='q2')
        self.assertEqual((await a.expect('msg', cid='q2'))['tt'], ['lb_wealth_3', 'f_king', 'f_bao', 'f_dart'])
        # the week ended: the game replaces its holders and announces it; the leaderboard title is gone
        with self.store.connect() as db:
            db.execute('DELETE FROM lb_weekly WHERE final=0')
        self.notify(op='honours_lb')
        await asyncio.sleep(0.3)
        await a.send(t='send', ch='town', text='hết tuần rồi', cid='q3')
        self.assertEqual((await a.expect('msg', cid='q3'))['tt'], ['f_king', 'f_bao', 'f_dart'])

    async def test_street_walkers_and_cards(self):
        ta, sa = self.account('Lan Anh')
        tb, sb = self.account('Minh Tú')
        self.save(sa, {'f_hu': 1})
        self.holds(sa, 'milk_tea', 1)
        a, b = await self.connect(ta), await self.connect(tb)
        ra = await a.call('walk_in', 'walk_room', place='chodem', look={}, g='female')
        me = next(p for p in ra['people'] if p['pid'] == self.pid(sa))
        self.assertEqual(me['tt'], ['lb_milk_tea_1', 'f_hu'])
        self.assertTrue(me['ti'])                                  # the text an older client shows stays
        await b.call('walk_in', 'walk_room', place='chodem', look={}, g='male')
        card = await b.call('card', 'card', pid=self.pid(sa))
        self.assertEqual(card['tt'], ['lb_milk_tea_1', 'f_hu'])
        self.assertNotIn('tt', await a.call('card', 'card', pid=self.pid(sb)))
