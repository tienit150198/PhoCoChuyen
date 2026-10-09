"""🚔 Owner 09/10: "bị bắt thì k được làm gì khác, chỉ được ở tù, nhắn tin, làm công ích thôi".

While jailed (game/jail.py) the game is an ALLOWLIST, default deny, on all three doors:
* game commands: every command name the game knows (the modules' command lists, the engine's own names and every name
  the client sends) is refused with code 'jailed' unless it is in OPEN_COMMANDS; a name nobody has written yet too;
  an imported backup is no way out either;
* HTTP POST routes (server.py): only the open ones (account, góp ý, friends, bail, inbox, popups seen, money coming in);
* live frames (live/protocol.py): the chat and leaving a room; a street/fair/home… frame is refused.
What others do FOR the jailed player still lands, and the release opens everything again."""
import http.client
import importlib
import json
import os
import re
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from game import jail as jl
from game.engine import GameError, apply_action
from tests.test_jail import JailBase, T0
from tests.test_black_market import story

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r'^[a-z][a-z0-9_]{1,40}$')
# Open on purpose (and why): the owner's rule, plus the harmless account/system acknowledgements.
EXPECTED_OPEN = {'settings',                                          # language, sound, name…
                 'jail_end', 'jail_task_start', 'jail_task_done',     # the camp and its công ích
                 'jr_seen', 'st_seen', 'hap_ack', 'bd_seen', 'jr_bk_read', 'lf_close'}   # popups already on screen


def registry() -> set:
    """Every command name the game knows of: the game modules' command lists (COMMANDS, *_ACTIONS), the names the
    engine and the modules test (`action == "x"`, `name == 'x'`, `action in (...)`), and every name the client sends."""
    names = set()
    for path in sorted((ROOT / 'game').glob('*.py')):
        try:
            mod = importlib.import_module(f'game.{path.stem}')
        except ImportError:   # a content module only its owner imports (a cycle when loaded alone): its source is read below
            mod = None
        for attr, val in (vars(mod) if mod else {}).items():
            if not (attr == 'COMMANDS' or attr.endswith('_ACTIONS') or attr == 'SELF_ACTIONS'):
                continue
            if isinstance(val, dict):
                val = val.keys()
            if isinstance(val, (tuple, list, set, frozenset, type({}.keys()))):
                names |= {x for x in val if isinstance(x, str) and NAME.match(x)}
        src = path.read_text(encoding='utf-8')
        names |= set(re.findall(r'\b(?:action|name)\s*==\s*["\']([a-z][a-z0-9_]+)["\']', src))
        for group in re.findall(r'\b(?:action|name)\s+in\s*[\(\{\[]([^\)\}\]]*)[\)\}\]]', src):
            names |= set(re.findall(r'["\']([a-z][a-z0-9_]+)["\']', group))
    for path in (ROOT / 'public' / 'js').rglob('*.js'):
        src = path.read_text(encoding='utf-8', errors='replace')
        names |= set(re.findall(r'\b(?:cmd|command|act|run|send|doCmd)\(\s*[\'"]([a-z][a-z0-9_]+)[\'"]', src))
    return names


class Commands(JailBase):
    @classmethod
    def setUpClass(cls):
        cls.names = registry()

    def test_the_allowlist_is_small_and_deliberate(self):
        self.assertEqual(set(jl.OPEN_COMMANDS), EXPECTED_OPEN)
        self.assertLessEqual(EXPECTED_OPEN, self.names, 'every open name is a real command')
        self.assertGreater(len(self.names), 400, 'the walk found the command lists')
        for name in ('start_day', 'end_day', 'select_career', 'reset_all', 'import_save', 'fair_bc', 'jr_bk_deposit',
                     'jr_wd_wear', 'jr_equip', 'jr_profile', 'jr_avatar', 'qn_chat', 'bd_post', 'lf_choose', 'iv_buy'):
            self.assertIn(name, self.names)
            self.assertFalse(jl.allowed(name), name)

    def test_every_other_command_is_refused(self):
        s = self.jailed()
        refused = 0
        for name in sorted(self.names | {'zz_a_command_from_next_year', 'jr_future_thing'}):
            if name in EXPECTED_OPEN:
                continue
            with self.subTest(name=name):
                for career in (None, 'milk_tea'):
                    e = self.refused(s, name, 'jailed', career)
                    self.assertEqual(e.message, jl.JAILED)
                refused += 1
        self.assertGreater(refused, 400)
        self.assertEqual(jl.JAILED, 'Đang ở trại tạm giữ, ra rồi hẵng làm nha.')

    def test_internal_commands_are_not_held(self):
        s = self.jailed()
        for name in ('start_day', 'zz_anything'):
            jl.gate(s, name, internal=True)

    def test_open_commands_work(self):
        s = self.jailed()
        s, r = self.act(s, 'settings', sound=False, lang='en')
        self.assertEqual(s['settings']['lang'], 'en')
        for name, p in (('jr_seen', dict(ids=['n1'])), ('bd_seen', {}), ('hap_ack', {}), ('jr_bk_read', {}),
                        ('st_seen', dict(id='nope')), ('lf_close', dict(id='nope'))):
            with self.subTest(name=name):
                try:
                    s, _ = self.act(s, name, 'milk_tea' if name == 'hap_ack' else None, **p)
                except Exception as e:  # noqa: BLE001 - nothing to acknowledge in a fresh save: refused for that, never for the jail
                    self.assertNotEqual(getattr(e, 'code', None), 'jailed', (name, str(e)))
        b = s['journey']['jail']
        task = b['tasks'][0]
        s, r = self.act(s, 'jail_task_start', task=task)
        self.assertEqual(r['jail']['task'], task)
        self.later(jl.DAY_MIN_S)
        s, r = self.act(s, 'jail_end', day=b['day'])
        self.assertIn('jail', s['journey'])

    def test_release_opens_everything_again(self):
        s = self.jailed(1, 'cop')
        self.refused(s, 'start_day', 'jailed', 'milk_tea')
        self.later(jl.DAY_MIN_S)
        s, r = self.act(s, 'jail_end', day=1)
        self.assertTrue(r['jail']['free'])
        s, _ = self.act(s, 'jr_profile', name='Bé Na')
        s, _ = self.act(s, 'start_day', 'milk_tea')
        for name in sorted(self.names)[:80]:
            jl.gate(s, name)   # nothing is held any more

    def test_an_imported_backup_is_no_way_out(self):
        from game.storage import Store
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 's.db', story=True)
        self.addCleanup(store.close_pool)
        token, state, rev = store.session(None)
        mutate(store, token, lambda st: jl.arrest(st['journey'], 'bm', 3, self.clock.t))
        state, rev, _ = store.read(token)
        self.assertTrue(jl.jailed(state, self.clock.t))
        with self.assertRaises(GameError) as e:
            store.command(token, 'import-jail-0001', rev, None, 'import_save', dict(save=dict(format='x', state={})))
        self.assertEqual(e.exception.code, 'jailed')


def mutate(store, token, fn):
    from game import marriage as mr
    mr._mutate(store, {store.key(token): fn})


# ---------------------------------------------------------------- HTTP
class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from game.storage import Store
        from server import GameServer
        cls.env = mock.patch.dict(os.environ, {'QUIET': '1', 'MNL_JAIL_OFF': '0'})
        cls.env.start()
        cls.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.store = Store(Path(cls.temp.name) / 'state.db', story=True)
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.store.close_pool()
        cls.temp.cleanup()
        cls.env.stop()

    def setUp(self):
        self.server.limits.clear()

    def req(self, dev, path, method='GET', body=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if dev.get('cookie'):
            h['Cookie'] = dev['cookie']
        if dev.get('csrf'):
            h['X-Game-CSRF'] = dev['csrf']
        if body is not None:
            h['Content-Type'] = 'application/json'
            body = json.dumps(body)
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse()
        raw, hdrs = res.read(), dict(res.getheaders())
        con.close()
        data = json.loads(raw or b'{}')
        if 'Set-Cookie' in hdrs:
            dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        if isinstance(data, dict) and data.get('csrf'):
            dev['csrf'] = data['csrf']
        return res.status, data

    def player(self):
        dev = {}
        status, data = self.req(dev, '/api/bootstrap?lite=1')
        self.assertEqual(status, 200, data)
        dev['token'] = dev['cookie'].split('=', 1)[1]
        return dev

    def jail(self, dev):
        mutate(self.store, dev['token'], lambda st: self.assertEqual(jl.arrest(st['journey'], 'bm', 3), 3))

    def free(self, dev):
        mutate(self.store, dev['token'], lambda st: jl.release(st['journey']))

    def command(self, dev, action, payload=None, career=None):
        status, data = self.req(dev, '/api/state')
        return self.req(dev, '/api/command', 'POST', dict(request_id=f'jo-{action}-{time.time_ns()}', expected_revision=data.get('revision', 0),
                                                         career=career, action=action, payload=payload or {}))

    CLOSED = ('/api/social/board', '/api/social/comment', '/api/social/buy', '/api/marriage/ring_buy', '/api/marriage/propose',
              '/api/marriage/send', '/api/marriage/envelope', '/api/rentals/rent', '/api/quay/post', '/api/bank/xfer/send',
              '/api/work-visits/order', '/api/home-guests/invite', '/api/home-guests/deco/act', '/api/karaoke/ticket',
              '/api/wedinvite/send', '/api/wedding/photo', '/api/ai/chat', '/api/ai/board', '/api/ai/review',
              '/api/a-route-from-next-year')
    OPEN = ('/api/social/inbox_read', '/api/bank/xfer/receive', '/api/work-visits/receive', '/api/marriage/jail_ask',
            '/api/marriage/seen', '/api/marriage/friend_search', '/api/gift/seen', '/api/leaderboard/visibility',
            '/api/feedback', '/api/push/unsubscribe', '/api/account/logout')

    def test_closed_routes_while_jailed(self):
        dev = self.player()
        self.jail(dev)
        for route in self.CLOSED:
            with self.subTest(route=route):
                status, data = self.req(dev, route, 'POST', {})
                self.assertEqual((status, data.get('code')), (409, 'jailed'), data)
                self.assertEqual(data.get('error'), jl.JAILED)
        status, data = self.command(dev, 'start_day', career='milk_tea')
        self.assertEqual(data.get('code'), 'jailed', data)
        status, data = self.command(dev, 'settings', dict(sound=False))
        self.assertEqual(status, 200, data)

    def test_open_routes_while_jailed(self):
        dev = self.player()
        self.jail(dev)
        for route in self.OPEN:
            with self.subTest(route=route):
                status, data = self.req(dev, route, 'POST', {})
                self.assertNotEqual(data.get('code'), 'jailed', (route, status, data))
        self.assertTrue(all(jl.route_open(r) for r in self.OPEN))
        self.assertFalse(any(jl.route_open(r) for r in self.CLOSED))

    def test_release_reopens_the_routes(self):
        dev = self.player()
        self.jail(dev)
        self.assertEqual(self.req(dev, '/api/social/board', 'POST', {})[1].get('code'), 'jailed')
        self.free(dev)
        for route in self.CLOSED[:6]:
            with self.subTest(route=route):
                self.assertNotEqual(self.req(dev, route, 'POST', {})[1].get('code'), 'jailed')
        status, data = self.command(dev, 'start_day', career='milk_tea')
        self.assertNotEqual(data.get('code'), 'jailed', data)

    def test_a_free_player_never_pays_for_the_check(self):
        dev = self.player()
        with mock.patch.object(jl, 'jailed', wraps=jl.jailed) as spy:
            self.req(dev, '/api/social/inbox_read', 'POST', {})
            self.assertEqual(spy.call_count, 0)   # an open route: no check at all
            self.req(dev, '/api/social/board', 'POST', {})
            self.assertEqual(spy.call_count, 1)
        # a light route (the save not read for it): the jail_marks row, never the save
        with mock.patch.object(jl, 'marked', wraps=jl.marked) as mark, \
                mock.patch.object(type(self.store), 'read', wraps=self.store.read) as read:
            status, data = self.req(dev, '/api/work-visits/order', 'POST', {})
            self.assertNotEqual(data.get('code'), 'jailed', data)
            self.assertEqual((mark.call_count, read.call_count), (1, 0))
        self.jail(dev)
        self.assertEqual(self.req(dev, '/api/work-visits/order', 'POST', {})[1].get('code'), 'jailed')
        self.free(dev)
        self.assertNotEqual(self.req(dev, '/api/work-visits/order', 'POST', {})[1].get('code'), 'jailed')


# ---------------------------------------------------------------- live
class LiveRegistry(unittest.TestCase):
    def test_every_live_frame_but_the_chat_is_closed(self):
        from live.app import FEATURES
        from live.protocol import Core
        kinds = {}
        for cls in [Core, *FEATURES]:
            for attr in dir(cls):
                spec = getattr(getattr(cls, attr, None), '_live', None)
                if spec:
                    kinds[spec[0]] = cls.name
        self.assertGreater(len(kinds), 80)
        opened = {k for k, f in kinds.items() if jl.frame_open(f, k)}
        self.assertEqual({k for k, f in kinds.items() if f not in ('chat', 'core')} & opened, set(jl.OPEN_FRAMES) & set(kinds))
        for k in ('send', 'history', 'read', 'join', 'ping', 'walk_out', 'fair_out', 'home_out'):
            self.assertIn(k, opened)
        for k in ('walk_in', 'move', 'say', 'fair_in', 'booth_make', 'home_in', 'kara_add', 'date_call', 'market_watch',
                  'auction_watch', 'visit_in', 'wed_in'):
            self.assertIn(k, kinds)
            self.assertNotIn(k, opened)
        self.assertTrue(all(k.endswith(('_out', '_leave', '_cancel')) for k in jl.OPEN_FRAMES))


class LiveFrames(unittest.IsolatedAsyncioTestCase):
    """The real dispatcher and the real query on the game database; a chat-like and a street-like feature."""
    async def asyncSetUp(self):
        from types import SimpleNamespace
        from game.storage import Store
        from live.db import PgDB
        from live.protocol import Core, Dispatcher, Feature, LiveError, on
        self.env = mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '0'})
        self.env.start()
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        self.db = PgDB(self.store.pg.url, self.store.pg.schema, 2)
        self.sent, self.sqls = [], []
        real, run = self.db.fetchrow, self.db.execute

        async def fetchrow(sql, args=()):
            self.sqls.append(sql)
            return await real(sql, args)

        async def execute(sql, args=()):
            self.sqls.append(sql)
            return await run(sql, args)
        self.db.fetchrow, self.db.execute = fetchrow, execute
        hub = SimpleNamespace(send=lambda conn, out: self.sent.append(out), rate=None)
        app = SimpleNamespace(hub=hub, cfg=SimpleNamespace(flags=lambda: {}), db=self.db)

        class Chat(Feature):
            name = 'chat'

            @on('send')
            async def send(self, conn, f):
                return dict(t='msg', text=f.get('text'))

        class Street(Feature):
            name = 'street'

            @on('walk_in')
            async def walk_in(self, conn, f):
                return dict(t='walk_room')

            @on('walk_out')
            async def walk_out(self, conn, f):
                return dict(t='walk_left')
        self.d = Dispatcher([Core(app), Chat(app), Street(app)])
        self.LiveError = LiveError

    async def asyncTearDown(self):
        await self.db.close()
        self.store.close_pool()
        self.tmp.cleanup()
        self.env.stop()

    def player(self, jailed):
        from types import SimpleNamespace
        token, state, rev = self.store.session(None)
        if jailed:
            mutate(self.store, token, lambda st: jl.arrest(st['journey'], 'bm', 3))
        return SimpleNamespace(player=SimpleNamespace(sid=self.store.key(token), ext={}), token=token)

    async def frame(self, conn, **f):
        self.sent.clear()
        await self.d.dispatch(conn, f)
        return self.sent[-1]

    async def test_only_the_chat_while_jailed(self):
        conn = self.player(True)
        out = await self.frame(conn, t='walk_in')
        self.assertEqual((out['t'], out['code'], out['msg']), ('error', 'jailed', jl.JAILED))
        self.assertEqual((await self.frame(conn, t='send', text='chào'))['t'], 'msg')
        self.assertEqual((await self.frame(conn, t='ping'))['t'], 'pong')
        self.assertEqual((await self.frame(conn, t='walk_out'))['t'], 'walk_left')
        self.assertEqual(self.sqls, [jl.MARK_GET, jl.MARK_SAVE])   # marked: the save confirms it once
        for _ in range(5):   # cached: no query per frame
            self.assertEqual((await self.frame(conn, t='walk_in'))['code'], 'jailed')
        self.assertEqual(len(self.sqls), 2)
        conn.player.ext['jail'] = (0, True)   # the short cache stale: the mark alone (the save was read just now)
        self.assertEqual((await self.frame(conn, t='walk_in'))['code'], 'jailed')
        self.assertEqual(self.sqls[2:], [jl.MARK_GET])
        # released (a friend's bail, the last day): the mark goes with it, the rooms open once the short cache is stale
        mutate(self.store, conn.token, lambda st: jl.release(st['journey']))
        conn.player.ext['jail'] = (0, True)
        self.assertEqual((await self.frame(conn, t='walk_in'))['t'], 'walk_room')
        self.assertEqual(self.sqls[3:], [jl.MARK_GET])
        from live import protocol
        self.assertLessEqual(protocol.JAIL_TTL_IN, protocol.JAIL_TTL)
        self.assertLessEqual(protocol.JAIL_TTL, 30)

    async def test_a_free_player_is_never_held_and_rarely_read(self):
        conn = self.player(False)
        for _ in range(4):
            self.assertEqual((await self.frame(conn, t='walk_in'))['t'], 'walk_room')
        self.assertEqual(self.sqls, [jl.MARK_GET])   # one primary-key read of jail_marks: sessions.state never read
        self.assertNotIn('sessions', jl.MARK_GET)
        conn.player.ext['jail'] = (0, False)
        await self.frame(conn, t='walk_in')
        self.assertEqual(self.sqls, [jl.MARK_GET] * 2)

    async def test_a_stale_mark_is_dropped(self):
        conn = self.player(True)
        with self.store.connect() as db:   # an older server let the player out: the save is free, the mark stayed
            state = json.loads(db.execute('SELECT state FROM sessions WHERE sid=?', (conn.player.sid,)).fetchone()['state'])
        state['journey'].pop('jail')
        state['journey'].pop('jail2', None)
        self.store.transaction(lambda db: db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(state), conn.player.sid)))
        self.assertEqual((await self.frame(conn, t='walk_in'))['t'], 'walk_room')
        self.assertEqual(self.sqls, [jl.MARK_GET, jl.MARK_SAVE, jl.MARK_STALE])
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM jail_marks WHERE sid=?', (conn.player.sid,)).fetchone())

    async def test_a_mark_past_its_time_is_free_without_the_save(self):
        conn = self.player(True)
        with mock.patch.object(jl, 'now', lambda: time.time() + 4 * jl.SAFE_S):
            self.assertEqual((await self.frame(conn, t='walk_in'))['t'], 'walk_room')
        self.assertEqual(self.sqls, [jl.MARK_GET])

    async def test_the_kill_switch_holds_nobody(self):
        conn = self.player(True)
        with mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '1'}):
            self.assertEqual((await self.frame(conn, t='walk_in'))['t'], 'walk_room')
        self.assertEqual(self.sqls, [])


if __name__ == '__main__':
    unittest.main()
