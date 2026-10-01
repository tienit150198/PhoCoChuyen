"""Giữ chân (game/retention.py, game/admin_retention.py, POST /api/beacon): funnel steps written once,
action counts and rejections, the beacon endpoint (size, origin, rate limit, never a save), client error
aggregation, retention math on synthetic cohorts, pruning and rollups, the admin section and its CSV.
Runs on PostgreSQL with TEST_DATABASE_URL (tests/pg_support.py)."""
import datetime, http.client, json, os, tempfile, threading, time, unittest, uuid
from pathlib import Path
from unittest.mock import patch

from game import admin_retention as ar
from game import admin_stats as st
from game import retention as rt
from game.engine import GameError
from game.storage import Store
from server import GameServer
from tests.helpers import Journey
from tests import test_marriage as tm

VN = rt.VN
REG = dict(password='matkhau-rat-dai', confirm='matkhau-rat-dai', display='Người Thử')


def day(offset=0):
    return (datetime.datetime.now(VN).date() + datetime.timedelta(days=offset)).isoformat()


def utc_text(t):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t))


class Base(unittest.TestCase):
    def setUp(self):
        st.clear_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db', story=False)
        st.ensure(self.store)
        self.n = 0

    def tearDown(self):
        rt.flush(self.store)
        st.stop_jobs()
        st.clear_cache()
        self.store.close_pool()
        self.tmp.cleanup()

    def player(self):
        token, _, _ = self.store.session()
        return token, self.store.key(token)

    def cmd(self, token, action, payload=None, career=None, rid=None):
        self.n += 1
        rev = self.store.read(token)[1]
        return self.store.command(token, rid or f'req-{uuid.uuid4().hex[:12]}', rev, career, action, payload or {})

    def q(self, sql, args=()):
        with self.store.connect() as db:
            return [tuple(r) for r in db.execute(sql, args).fetchall()]

    def sql(self, sql, args=()):
        with self.store.connect() as db:
            db.execute(sql, args)

    def steps(self, sid):
        return {r[0]: r for r in self.q('SELECT key, at, day, career, detail FROM stat_milestones WHERE sid = ?', (sid,))}


class StoreJourney(Journey):
    """tests/helpers.Journey, but every action goes through Store.command (milestones, action counts)."""

    def __init__(self, test, token, career='mother_baby'):
        self.t, self.token, self.career = test, token, career
        self.state = test.store.read(token)[0]
        self.act('select_career')
        self.act('start_day')

    def act(self, action, **payload):
        out = self.t.cmd(self.token, action, payload, self.career)
        self.state = self.t.store.read(self.token)[0]
        return out['result']


# ---------------------------------------------------------------- milestones
class ReachedTests(unittest.TestCase):
    def marks(self, **kw):
        base = dict(cur=None, named=0, served=0, level=1, started=frozenset(), days=0, chapter=1, homes=0, certs=0, loans=0, savings=0)
        base.update(kw)
        return tuple(base[k] for k in ('cur', 'named', 'served', 'level', 'started', 'days', 'chapter', 'homes', 'certs', 'loans', 'savings'))

    def keys(self, a, b):
        return [k for k, _, _ in rt.reached(self.marks(**a), self.marks(**b))]

    def test_each_step_fires_when_crossed(self):
        self.assertEqual(self.keys({}, dict(cur='milk_tea')), ['picked'])
        self.assertEqual(self.keys(dict(cur='milk_tea'), dict(cur='grocery')), ['job_change'])
        self.assertEqual(self.keys({}, dict(named=1)), ['named'])
        self.assertEqual(self.keys(dict(served=0), dict(served=1)), ['served1'])
        self.assertEqual(self.keys(dict(served=2), dict(served=12)), ['served3', 'served10'])
        self.assertEqual(self.keys(dict(level=1), dict(level=2)), ['level2'])
        self.assertEqual(self.keys(dict(days=0), dict(days=3)), ['day1', 'day2', 'day3'])
        self.assertEqual(self.keys(dict(days=6), dict(days=30)), ['day7', 'day14', 'day30'])
        self.assertEqual(self.keys(dict(chapter=1), dict(chapter=3)), ['chapter2', 'chapter3'])
        self.assertEqual(self.keys({}, dict(started=frozenset({'milk_tea', 'grocery'}))), ['start:grocery', 'start:milk_tea'])
        self.assertEqual(self.keys({}, dict(homes=1, certs=1, loans=1, savings=1)), ['house', 'cert', 'loan', 'savings'])

    def test_nothing_without_a_crossing(self):
        same = dict(cur='milk_tea', named=1, served=5, level=3, days=4, chapter=2, homes=1, certs=2, loans=1, savings=1)
        self.assertEqual(self.keys(same, same), [])
        self.assertEqual(self.keys(dict(served=5), dict(served=0)), [])     # a reset journey goes down: nothing
        self.assertEqual(rt.reached(None, self.marks()), [])
        self.assertEqual(rt.reached(self.marks(), None), [])

    def test_marks_never_raise(self):
        for bad in (None, [], {'journey': 5}, {'journey': {'bank': {'loans': 'x', 'stats': 3}}, 'current': 7}):
            m = rt.marks(bad, {'x': 1})
            self.assertTrue(m is None or len(m) == 11)

    def test_marks_are_cheap(self):
        from game.engine import new_state
        from game.leaderboard import summary
        s = new_state()
        board = summary(s)
        t = time.perf_counter()
        for _ in range(2000):
            rt.reached(rt.marks(s, board), rt.marks(s, board))
        per = (time.perf_counter() - t) / 2000 * 1e6
        self.assertLess(per, 200, f'{per:.1f} us per command')


class MilestoneStoreTests(Base):
    def test_created_with_the_session(self):
        tok, sid = self.player()
        got = self.steps(sid)
        self.assertEqual(set(got), {'created'})
        self.assertAlmostEqual(got['created'][1], time.time(), delta=60)
        self.assertEqual(got['created'][2], 1)

    def test_playing_writes_each_step_once(self):
        tok, sid = self.player()
        j = StoreJourney(self, tok)
        self.assertEqual(set(self.steps(sid)), {'created', 'picked'})
        self.assertEqual(self.steps(sid)['picked'][3], 'mother_baby')
        j.solve()
        got = self.steps(sid)
        self.assertTrue({'served1', 'start:mother_baby'} <= set(got), got)
        first = got['served1'][1]
        for _ in range(3):
            if j.c['active_task']:
                j.solve()
        got = self.steps(sid)
        self.assertTrue({'served3', 'level2'} <= set(got), got)
        self.assertEqual(got['served1'][1], first)                       # never written again
        self.assertEqual(len(self.q("SELECT 1 FROM stat_milestones WHERE sid = ? AND key = 'served1'", (sid,))), 1)
        self.cmd(tok, 'jr_profile', dict(name='Lan', gender='female'))
        self.assertIn('named', self.steps(sid))
        self.cmd(tok, 'select_career', {}, 'pharmacy')
        self.assertEqual(self.steps(sid)['job_change'][4], 'mother_baby>pharmacy')

    def test_a_rejected_command_writes_no_step(self):
        tok, sid = self.player()
        with patch.object(rt, 'reached', side_effect=AssertionError('no step on a rejected command')):
            with self.assertRaises(GameError):
                self.cmd(tok, 'select_career', {}, 'no_such_place')
        self.assertEqual(set(self.steps(sid)), {'created'})

    def test_account_step(self):
        tok, sid = self.player()
        from game import accounts
        with patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw):
            accounts.register(self.store, tok, dict(REG, username='giuchan_test'))
        self.assertIn('account', self.steps(sid))

    def test_hook_sees_new_steps_after_the_commit(self):
        seen = []
        rt.on_event(lambda e, sid, p: seen.append((e, sid, p.get('career'))))
        self.addCleanup(rt._hooks.clear)
        tok, sid = self.player()
        self.cmd(tok, 'select_career', {}, 'mother_baby')
        self.assertIn(('milestone:picked', sid, 'mother_baby'), seen)

    def test_off_switch(self):
        with patch.object(rt, 'ENABLED', False):
            tok, sid = self.player()
            self.cmd(tok, 'select_career', {}, 'mother_baby')
            rt.flush(self.store)
        self.assertEqual(self.steps(sid), {})
        self.assertEqual(self.q('SELECT COUNT(*) FROM stat_actions'), [(0,)])

    def test_backfill_seeds_from_counters(self):
        tok, sid = self.player()
        j = StoreJourney(self, tok)
        j.solve()
        self.sql('DELETE FROM stat_milestones WHERE sid = ?', (sid,))
        self.sql("UPDATE stat_milestones SET at = at")   # nothing else there
        out = rt.backfill(self.store, day(-1), day(0), pause=0)
        self.assertEqual(out['saves'], 1)
        got = self.steps(sid)
        self.assertTrue({'created', 'picked', 'served1', 'start:mother_baby'} <= set(got), got)
        self.assertTrue(all(r[1] is None and r[4] == 'backfill' for r in got.values()))
        self.assertEqual(rt.backfill(self.store, day(-1), day(0), pause=0)['saves'], 0)   # idempotent: it has `created` now


class MarriageStepTests(tm.Base):
    def test_engaged_and_married_steps(self):
        a, b = self.user('an', 1500), self.user('binh', 1500)
        tm.Base.engage(self, a, b)
        with self.store.connect() as db:
            keys = {(r[0], r[1]) for r in db.execute("SELECT sid, key FROM stat_milestones WHERE key IN ('engaged', 'married')")}
        self.assertEqual(keys, {(self.sid(a), 'engaged'), (self.sid(b), 'engaged')})
        self.act(a, 'plan', plan=tm.PLAN, mine=50, announce=True)
        w = self.view(b)['wedding']
        self.act(b, 'confirm', id=w['id'], version=w['version'], announce=True)
        self.store.transaction(lambda db: db.execute('UPDATE weddings SET due_at=? WHERE id=?', (self.clock.t - 1, w['id'])))
        tm.mr.on_load(self.store, b, self.state(b))
        with self.store.connect() as db:
            married = {r[0] for r in db.execute("SELECT sid FROM stat_milestones WHERE key = 'married'")}
        self.assertEqual(married, {self.sid(a), self.sid(b)})


# ---------------------------------------------------------------- action counts
class ActionTests(Base):
    def rows(self):
        return {(r[2], r[3]): r for r in self.q('SELECT day, sid, career, action, n, errors, err FROM stat_actions')}

    def test_counts_and_errors(self):
        tok, sid = self.player()
        self.cmd(tok, 'select_career', {}, 'mother_baby')
        self.cmd(tok, 'start_day', {}, 'mother_baby')
        for _ in range(2):
            with self.assertRaises(GameError):
                self.cmd(tok, 'shop_deliver', dict(task='nope'), 'mother_baby')
        with self.assertRaises(GameError):
            self.cmd(tok, 'settings', dict(nonsense=1))
        self.assertEqual(self.rows(), {})          # memory only until the flush
        self.assertGreaterEqual(rt.flush(self.store), 4)
        got = self.rows()
        self.assertEqual(got[('mother_baby', 'select_career')][4:6], (1, 0))
        deliver = got[('mother_baby', 'shop_deliver')]
        self.assertEqual(deliver[4:6], (2, 2))
        self.assertTrue(deliver[6] and len(deliver[6]) <= 80)
        self.assertEqual(got[('', 'settings')][4:6], (1, 1))
        self.assertTrue(all(r[0] == day() and r[1] == sid[:16] for r in got.values()))   # 16 hex characters of the save id
        # a second flush adds to the same rows
        self.cmd(tok, 'settings', dict(lang='vi'))
        rt.flush(self.store)
        self.assertEqual(self.rows()[('', 'settings')][4:6], (2, 1))

    def test_replays_and_internal_commands_are_not_counted(self):
        tok, sid = self.player()
        self.cmd(tok, 'settings', dict(lang='en'), rid='same-request-1')
        self.store.command(tok, 'same-request-1', 0, None, 'settings', dict(lang='en'))   # the client's retry
        rt.flush(self.store)
        self.assertEqual(self.rows()[('', 'settings')][4], 1)

    def test_conflicts_count_as_errors(self):
        tok, sid = self.player()
        self.cmd(tok, 'settings', dict(lang='en'))
        with self.assertRaises(GameError):
            self.store.command(tok, 'stale-request-1', 0, None, 'settings', dict(lang='vi'))
        rt.flush(self.store)
        r = self.rows()[('', 'settings')]
        self.assertEqual((r[4], r[5], r[6]), (2, 1, 'revision_conflict'))

    def test_identifiers_only_and_bounded(self):
        rt.count(self.store, 'sid-x', 'milk tea<script>', 'a' * 200, None)
        with patch.object(rt, 'BUFFER_MAX', 3):
            for i in range(5):
                rt.count(self.store, f'sid-{i}', 'milk_tea', 'serve', None)
        b = rt._bufs[self.store.path][1]
        self.assertEqual(len(b), 3)
        self.assertIn((day(), 'sid-x', '', '?'), b)
        self.assertGreaterEqual(rt.buffered()['dropped'], 3)
        self.assertEqual(rt.flush(self.store), 3)
        self.assertEqual(self.rows(), {})          # no such saves: nothing is written for them

    def test_deleting_the_save_deletes_its_rows(self):
        tok, sid = self.player()
        other, osid = self.player()
        for t in (tok, other):
            self.cmd(t, 'settings', dict(lang='en'))
        rt.flush(self.store)
        self.cmd(tok, 'settings', dict(lang='vi'))   # still in memory when the save goes
        leave_payload = '{"v":"job"}'
        rt.beacon(self.store, sid, dict(leave=dict(v='job')))
        self.sql('UPDATE stat_leave_last SET payload = ? WHERE sid = ?', (leave_payload, sid))
        self.assertEqual(self.q('SELECT COUNT(*) FROM stat_leaves WHERE sid = ?', (sid[:16],)), [(1,)])
        self.sql('INSERT INTO stat_acquisition(sid, at, day, source) VALUES (?, ?, ?, ?)', (sid, time.time(), day(), 'fb'))
        self.assertTrue(self.store.delete(tok))
        rt.flush(self.store)
        for table in ('stat_actions', 'stat_milestones', 'stat_leaves', 'stat_leave_last', 'stat_acquisition'):
            self.assertEqual(self.q(f'SELECT COUNT(*) FROM {table} WHERE sid IN (?, ?)', (sid, sid[:16])), [(0,)], table)
        self.assertEqual(self.q('SELECT COUNT(*) FROM stat_actions WHERE sid = ?', (osid[:16],)), [(1,)])

    def test_error_text_is_short_and_impersonal(self):
        self.assertEqual(rt.error_text(GameError('x', 'revision_conflict')), 'revision_conflict')
        e = GameError('Chưa đủ 1.250 xu cho “Bánh của Lan” — xem https://a.b/c?token=123 hoặc lan@mail.com')
        t = rt.error_text(e)
        self.assertNotIn('Lan', t)
        self.assertNotIn('token', t)
        self.assertNotIn('lan@', t)
        self.assertNotIn('1.250', t)
        self.assertLessEqual(len(t), 80)


# ---------------------------------------------------------------- beacons (unit) and client errors
class BeaconUnitTests(Base):
    def test_leave_payload_keeps_known_fields_only(self):
        p = json.loads(rt.leave_payload(dict(v='job', p='confirmDialog', c='milk_tea', d=3, t='d1:s2', s=245,
                                             a=['x', 'shop_pick', '<b>', 'serve'], name='Lan', extra={'x': 1})))
        self.assertEqual(p, dict(v='job', p='confirmDialog', c='milk_tea', d=3, t='d1:s2', s=245, a=['shop_pick', 'serve']))
        self.assertIsNone(rt.leave_payload(dict(v='bad value with spaces')))
        self.assertIsNone(rt.leave_payload('x'))

    def test_beacon_writes_and_caps(self):
        tok, sid = self.player()
        got = rt.beacon(self.store, sid, dict(leave=dict(v='job', d=1)))
        self.assertEqual(got['leave'], 1)
        self.assertEqual(self.q('SELECT payload FROM stat_leave_last WHERE sid = ?', (sid,)), [('{"v":"job","d":1}',)])
        with patch.object(rt, 'LEAVES_PER_DAY', 2):
            rt._leaves.clear()
            stored = [rt.beacon(self.store, sid, dict(leave=dict(v='home')))['leave'] for _ in range(4)]
        self.assertEqual(stored, [1, 1, 0, 0])
        self.assertEqual(rt.beacon(self.store, 'no-such-save', dict(leave=dict(v='job')))['leave'], 0)

    def test_errors_aggregate(self):
        tok, sid = self.player()
        errs = [dict(k='js', m='TypeError: x is null @app.js:12', s='job'), dict(k='js', m='TypeError: x is null @app.js:12', s='job', n=3),
                dict(k='asset', m='https://phocochuyen.io.vn/js/careers/fruit.js?v=abc123', s='loading'), dict(k='evil', m='x'),
                dict(k='toast', m='Chưa đủ 300 xu cho “Lan”')]
        rt.beacon(self.store, sid, dict(errors=errs))
        rt.beacon(self.store, sid, dict(errors=errs[:1]))
        rows = {r[1]: r for r in self.q('SELECT kind, message_key, screen, count, sample FROM stat_client_errors')}
        self.assertEqual(rows['TypeError: x is null @app.js:#'][3], 5)
        self.assertIn('https://phocochuyen.io.vn/js/careers/fruit.js', rows)
        self.assertEqual(rows['Chưa đủ # xu cho “…”'][0], 'toast')
        rt.beacon(self.store, sid, dict(errors=[dict(k='api', m='502 /api/social/123/feed'), dict(k='api', m='0 /api/command')]))
        keys = {r[0] for r in self.q("SELECT message_key FROM stat_client_errors WHERE kind = 'api'")}
        self.assertEqual(keys, {'502 /api/social/#/feed', '0 /api/command'})       # the status stays, ids in the path do not
        self.assertEqual(len(rows), 3)                                       # unknown kinds dropped
        with patch.object(rt, 'ERRORS_PER_BEACON', 2):
            self.assertEqual(rt.beacon(self.store, sid, dict(errors=[dict(k='js', m=f'e{i}') for i in range(9)]))['errors'], 2)

    def test_errors_stack_and_foreign(self):
        # 01/10: 163 "Cannot read properties of undefined (reading …)" with no hint of where; 64 Zalo-injected errors
        tok, sid = self.player()
        stack = 'js/app.js:1:59652 < js/app.js:1:37283 < js/app.js:1:28135'
        reading = "Cannot read properties of undefined (reading 'filter')"
        rt.beacon(self.store, sid, dict(errors=[dict(k='promise', m=reading, s='start')]), own_host='phocochuyen.io.vn')   # an older page: no stack
        got = rt.beacon(self.store, sid, dict(errors=[
            dict(k='promise', m=reading, s='start', st=stack),
            dict(k='js', m='Uncaught ReferenceError: zaloJSV2 is not defined', s='loading'),
            dict(k='promise', m="Cannot read properties of undefined (reading 'sendMessage')", s='job', st='~ < ~'),
            dict(k='asset', m='connect.facebook.net/en_US/fbevents.js', s='job'),
            dict(k='asset', m='https://phocochuyen.io.vn/js/careers/fruit.js', s='loading'),
            dict(k='js', m='Uncaught TypeError: boom', s='job', st='js/app.js:1:5 < <script>alert(1)</script>:1:1'),
        ]), own_host='phocochuyen.io.vn')
        self.assertEqual(got['errors'], 3)
        rows = {r[1]: r for r in self.q('SELECT kind, message_key, screen, count, sample FROM stat_client_errors')}
        self.assertEqual(set(rows), {'Cannot read properties of undefined (reading ‹filter›)', 'https://phocochuyen.io.vn/js/careers/fruit.js',
                                     'Uncaught TypeError: boom'})
        row = rows['Cannot read properties of undefined (reading ‹filter›)']
        self.assertEqual(row[3], 2)
        self.assertTrue(row[4].endswith(' @ ' + stack), row[4])                 # the first sample had none: the stack replaces it
        rt.beacon(self.store, sid, dict(errors=[dict(k='promise', m=reading, s='start', st='js/other.js:1:1')]))
        self.assertTrue(self.q('SELECT sample FROM stat_client_errors WHERE kind = ?', ('promise',))[0][0].endswith(stack), 'kept once it has one')
        self.assertNotIn(' @ ', rows['Uncaught TypeError: boom'][4], 'a malformed stack is dropped, the error kept')
        self.assertEqual(rt.stack_text('a.js:1:2 < b.js:3:4 < c.js:5:6 < d.js:7:8'), 'a.js:1:2 < b.js:3:4 < c.js:5:6')
        self.assertIsNone(rt.stack_text(['x']))
        # rows stored before the filter existed are left out of the admin's list and total
        day = rt.vn_day(time.time())
        self.sql('INSERT INTO stat_client_errors(day, kind, message_key, screen, count, last_at) VALUES (?, ?, ?, ?, ?, ?)',
                 (day, 'js', 'Uncaught ReferenceError: zaloJSV# is not defined', 'loading', 64, time.time()))
        with self.store.connect() as db:
            d = ar.client_errors(db, datetime.date.fromisoformat(day))
        self.assertNotIn('zaloJSV', json.dumps(d))
        self.assertEqual(d['today_total'], 5)                                # 3 + 1 + 1, the 64 not counted
        top = next(e for e in d['today'] if e['kind'] == 'promise')
        self.assertEqual(top['stack'], stack)

    def test_load_and_acquisition(self):
        tok, sid = self.player()
        got = rt.beacon(self.store, sid, dict(load=dict(ttfb=180, dcl=900, frame=2350, net='3g', mem=2, cpu=8, cache='cold'),
                                              acq=dict(ref='m.facebook.com', src='FB Ads!', med='cpc', cmp='launch_10/2026')))
        self.assertEqual((got['load'], got['acq']), (4, 1))
        rows = self.q("SELECT metric, net, who, cache, tier, bucket, n FROM stat_loads WHERE metric = 'frame'")
        self.assertEqual(rows, [('frame', '3g', 'new', 'cold', 'low', rt.load_bucket(2350), 1)])
        self.assertEqual(self.q('SELECT source, medium, campaign, ref_domain FROM stat_acquisition'), [('fb_ads', 'cpc', 'launch_102026', 'facebook')])
        rt.beacon(self.store, sid, dict(acq=dict(ref='google.com')))       # the first one stays
        self.assertEqual(self.q('SELECT ref_domain FROM stat_acquisition'), [('facebook',)])
        # an old save (born long ago) gets no acquisition row
        old, osid = self.player()
        self.sql('UPDATE stat_births SET day = ? WHERE sid = ?', (day(-20), osid))
        self.assertEqual(rt.beacon(self.store, osid, dict(acq=dict(ref='zalo.me')))['acq'], 0)

    def test_ref_domains(self):
        cases = {'': 'direct', 'm.facebook.com': 'facebook', 'l.facebook.com': 'facebook', 'www.tiktok.com': 'tiktok',
                 'www.google.com.vn': 'google', 'google.de': 'google', 'zalo.me': 'zalo', 'www.threads.net': 'threads',
                 'phocochuyen.io.vn': 'self', 'blog.example.com.vn': 'example.com.vn', 'sub.news.example.org': 'example.org',
                 'bad host!': 'other', 'android-app://com.google.android.gm/': 'google'}
        for host, want in cases.items():
            self.assertEqual(rt.ref_domain(host, 'phocochuyen.io.vn'), want, host)
        self.assertEqual(rt.utm(' Facebook Ads/Oct?x=1 '), 'facebook_adsoctx1')


# ---------------------------------------------------------------- the beacon endpoint
class BeaconHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = GameServer(('127.0.0.1', 0), Store(Path(cls.temp.name) / 'state.db'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'op_ret'})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); st.stop_jobs(); cls.server.store.close_pool(); cls.temp.cleanup(); cls.env.stop()
        st.clear_cache()

    def setUp(self):
        self.server.limits.clear()
        rt._leaves.clear()

    def raw(self, method, path, body=None, headers=None, cookie=None, csrf=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if cookie: h['Cookie'] = cookie
        if csrf: h['X-Game-CSRF'] = csrf
        h.update(headers or {})
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=60)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse(); data = res.read(); hdrs = dict(res.getheaders()); con.close()
        return res.status, hdrs, data

    def device(self):
        status, h, body = self.raw('GET', '/api/bootstrap')
        self.assertEqual(status, 200)
        d = json.loads(body)
        return dict(cookie=h['Set-Cookie'].split(';')[0], csrf=d['csrf'])

    def beacon(self, dev, body, origin='same', site='same-origin'):
        h = {'Content-Type': 'text/plain;charset=UTF-8'}
        if origin == 'same': h['Origin'] = f'http://127.0.0.1:{self.port}'
        elif origin: h['Origin'] = origin
        if site: h['Sec-Fetch-Site'] = site
        data = body if isinstance(body, (bytes, str)) else json.dumps(body)
        return self.raw('POST', '/api/beacon', data, h, cookie=(dev or {}).get('cookie'))[0]

    def sid(self, dev):
        return self.server.store.key(dev['cookie'].split('=', 1)[1])

    def rows(self, sid):
        with self.server.store.connect() as db:
            return [r[0] for r in db.execute('SELECT payload FROM stat_leaves WHERE sid = ?', (sid[:16],))]

    def test_takes_a_leave(self):
        dev = self.device()
        self.assertEqual(self.beacon(dev, dict(leave=dict(v='job', c='milk_tea', d=1, s=40, a=['shop_pick']))), 204)
        self.assertEqual(json.loads(self.rows(self.sid(dev))[0])['v'], 'job')
        self.assertEqual(self.beacon(dev, dict(leave=dict(v='home')), origin=None), 204)   # Sec-Fetch-Site alone is enough
        self.assertEqual(self.beacon(dev, dict(leave=dict(v='home')), site=None), 204)     # Origin alone too

    def test_refuses_other_sites_and_no_session(self):
        dev = self.device()
        body = dict(leave=dict(v='job'))
        self.assertEqual(self.beacon(dev, body, origin='https://evil.example'), 403)
        self.assertEqual(self.beacon(dev, body, site='cross-site'), 403)
        self.assertEqual(self.beacon(dev, body, site='same-site'), 403)
        self.assertEqual(self.beacon(dev, body, origin=None, site=None), 403)
        self.assertEqual(self.beacon(None, body), 401)
        self.assertEqual(self.beacon(dict(cookie='mnl_session=' + 'ab' * 32), body), 204)   # unknown save: taken, nothing stored
        self.assertEqual(self.rows(self.server.store.digest('ab' * 32)), [])
        self.assertEqual(self.rows(self.sid(dev)), [])

    def test_size_limit_and_bad_json(self):
        dev = self.device()
        self.assertEqual(self.beacon(dev, 'x' * (rt.BEACON_MAX + 1)), 413)
        self.assertEqual(self.beacon(dev, '{"leave":'), 400)
        self.assertEqual(self.beacon(dev, '[1,2]'), 400)
        self.assertEqual(self.beacon(dev, json.dumps(dict(leave=dict(v='job'), pad='y' * 7000))), 204)

    def test_rate_limited(self):
        dev = self.device()
        with patch.dict(os.environ, {'BEACONS_PER_MINUTE': '5'}):
            codes = [self.beacon(dev, dict(leave=dict(v='job'))) for _ in range(7)]
        self.assertEqual(codes, [204] * 5 + [429] * 2)

    def test_never_reads_a_save(self):
        dev = self.device()
        boom = AssertionError('a beacon must not read a save')
        with patch.object(Store, 'read', side_effect=boom), patch.object(Store, 'parse_state', side_effect=boom):
            self.assertEqual(self.beacon(dev, dict(leave=dict(v='job'), errors=[dict(k='js', m='x')],
                                                   load=dict(frame=1200, net='4g'), acq=dict(ref='zalo.me'))), 204)
        self.assertEqual(len(self.rows(self.sid(dev))), 1)

    def test_no_csrf_needed_but_commands_still_need_it(self):
        dev = self.device()
        self.assertEqual(self.beacon(dev, dict(leave=dict(v='job'))), 204)
        status, _, _ = self.raw('POST', '/api/command', json.dumps(dict(request_id='x' * 12, expected_revision=0, action='settings', payload={})),
                                {'Content-Type': 'application/json'}, cookie=dev['cookie'])
        self.assertEqual(status, 403)

    def test_admin_section_and_csv(self):
        anon = self.device()
        status, _, _ = self.raw('GET', '/api/admin/stats/section?name=retention', cookie=anon['cookie'], csrf=anon['csrf'])
        self.assertEqual(status, 403)
        self.assertEqual(self.raw('GET', '/api/admin/stats/section?name=retention')[0], 401)
        admin = self.device()
        with patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw):
            status, h, body = self.raw('POST', '/api/account/register', json.dumps(dict(REG, username='op_ret')),
                                       {'Content-Type': 'application/json'}, cookie=admin['cookie'], csrf=admin['csrf'])
        self.assertEqual(status, 200, body)
        admin['cookie'] = h['Set-Cookie'].split(';')[0]
        admin['csrf'] = json.loads(body)['csrf']
        self.beacon(anon, dict(leave=dict(v='job', c='milk_tea', d=1), errors=[dict(k='js', m='boom')], load=dict(frame=1500, net='4g')))
        st.clear_cache()
        status, _, body = self.raw('GET', '/api/admin/stats/section?name=retention', cookie=admin['cookie'], csrf=admin['csrf'])
        self.assertEqual(status, 200, body)
        d = json.loads(body)
        for key in ('cohorts', 'funnel', 'by_day', 'churn', 'careers', 'sources', 'loads', 'errors', 'sizes', 'cohort_summary'):
            self.assertIn(key, d)
        self.assertEqual([p['key'] for p in d['funnel']], ['today', 'yesterday', 'd7', 'd30'])
        self.assertEqual(len(d['cohorts']), ar.COHORT_DAYS)
        self.assertGreaterEqual(d['funnel'][0]['n'], 2)
        self.assertEqual(d['errors']['today'][0]['message'], 'boom')
        self.assertEqual(d['loads']['week']['frame']['n'], 1)
        self.assertNotIn(self.sid(anon), body.decode())
        self.assertNotIn('op_ret', body.decode())
        status, h, body = self.raw('GET', '/api/admin/stats/section?name=retention&format=csv', cookie=admin['cookie'], csrf=admin['csrf'])
        self.assertEqual(status, 200)
        self.assertIn('text/csv', h['Content-Type'])
        self.assertIn('attachment', h['Content-Disposition'])
        text = body.decode('utf-8-sig')
        for name in ('# cohorts', '# funnel_d7', '# churn_screen', '# careers', '# sources_d30', '# load_first_frame_ms', '# client_errors_today', '# log_sizes'):
            self.assertIn(name, text)
        self.assertEqual(self.raw('GET', '/api/admin/stats/section?name=playtime&format=csv', cookie=admin['cookie'], csrf=admin['csrf'])[0], 400)


# ---------------------------------------------------------------- retention math on synthetic cohorts
class MathTests(Base):
    def born(self, sid, born, active=(), updated=None, created_at=None):
        self.sql('INSERT INTO sessions(sid, csrf, state, revision) VALUES (?, ?, ?, 1)', (sid, 'c', '{}'))
        self.sql('UPDATE stat_births SET day = ? WHERE sid = ?', (born, sid))
        self.sql('DELETE FROM stat_active WHERE sid = ?', (sid,))
        for d in active:
            self.sql('INSERT INTO stat_active(day, sid) VALUES (?, ?)', (d, sid))
        if updated is not None:
            self.sql('UPDATE sessions SET updated_at = ? WHERE sid = ?', (utc_text(updated), sid))
            self.sql('DELETE FROM stat_active WHERE sid = ? AND day = ?', (sid, day()))
            for d in active:
                self.sql('INSERT OR IGNORE INTO stat_active(day, sid) VALUES (?, ?)', (d, sid))
        if created_at is not None:
            self.sql('INSERT INTO stat_milestones(sid, key, at, day) VALUES (?, ?, ?, 1)', (sid, 'created', created_at))

    def test_cohort_retention(self):
        d10 = day(-10)
        for i in range(10):   # 10 players started 10 days ago; 4 came back on D1, 2 on D3, 1 on D7, none on D14
            back = [d10]
            if i < 4: back.append(day(-9))
            if i < 2: back.append(day(-7))
            if i < 1: back.append(day(-3))
            self.born(f'c{i}', d10, back)
        self.born('ghost', d10, [])            # opened the page, never played: not in the cohort
        self.born('today1', day(0), [day(0)])
        with st._read(self.store, 5000) as db:
            rows = {r['day']: r for r in ar.cohorts(self.store, db, datetime.datetime.now(VN).date())}
        r = rows[d10]
        self.assertEqual((r['n'], r['d1'], r['d3'], r['d7'], r['d14'], r['d30']), (10, 40.0, 20.0, 10.0, None, None))
        self.assertEqual((rows[day(0)]['n'], rows[day(0)]['d1']), (1, None))   # not old enough
        s = ar.cohort_summary(list(rows.values()))
        self.assertEqual((s['d1'], s['d1_n'], s['d7'], s['d14']), (40.0, 10, 10.0, None))

    def test_funnel_shares_and_median_times(self):
        t0 = time.time() - 3600
        for i in range(4):
            sid = f'f{i}'
            self.born(sid, day(0), [day(0)], created_at=t0)
            self.sql("INSERT INTO stat_milestones(sid, key, at) VALUES (?, 'picked', ?)", (sid, t0 + 60 * (i + 1)))
            if i < 2:
                self.sql("INSERT INTO stat_milestones(sid, key, at) VALUES (?, 'served1', ?)", (sid, t0 + 600))
        self.born('est', day(0), [day(0)])
        self.sql("INSERT INTO stat_milestones(sid, key, at) VALUES ('est', 'created', NULL)")
        self.sql("INSERT INTO stat_milestones(sid, key, at) VALUES ('est', 'picked', NULL)")
        with st._read(self.store, 5000) as db:
            f = ar.funnel_period(db, day(0), day(0))
        steps = {s['key']: s for s in f['steps']}
        self.assertEqual(f['n'], 5)
        self.assertEqual((steps['picked']['n'], steps['picked']['pct'], steps['picked']['est']), (5, 100.0, 1))
        self.assertEqual(steps['picked']['median_min'], 2.5)      # 1, 2, 3, 4 minutes; the seeded one has no time
        self.assertEqual((steps['served1']['pct'], steps['served1']['median_min']), (40.0, 10.0))
        self.assertTrue(f['est'])

    def test_churn_groups_by_last_leave_and_step(self):
        now = time.time()
        for i, (screen, career, life) in enumerate([('job', 'milk_tea', 1), ('job', 'milk_tea', 2), ('prepare', 'grocery', 9)]):
            sid = f'g{i}'
            self.born(sid, day(-10), [day(-10)], updated=now - 5 * 86400, created_at=now - 10 * 86400)
            self.sql('INSERT INTO stat_leave_last(sid, at, payload) VALUES (?, ?, ?)', (sid, now - 5 * 86400,
                     json.dumps(dict(v=screen, c=career, d=life, t='d1:s2', a=['serve']))))
            self.sql("INSERT INTO stat_milestones(sid, key, at) VALUES (?, 'served1', ?)", (sid, now - 9 * 86400))
        self.born('recent', day(-1), [day(-1)], updated=now - 3600)        # played an hour ago: not churned
        with st._read(self.store, 5000) as db:
            c = ar.churn(db, now, datetime.datetime.now(VN).date())
        self.assertEqual((c['players'], c['with_leave'], c['tracked']), (3, 3, 3))
        self.assertEqual(c['screen'][0], dict(label='job', n=2, pct=66.7))
        self.assertEqual(c['career'][0]['label'], 'milk_tea')
        self.assertEqual({r['label']: r['n'] for r in c['life']}, {'Ngày 1': 1, 'Ngày 2': 1, 'Ngày 8–14': 1})
        self.assertEqual(c['by_step'], [dict(label='Khách đầu', n=3, pct=100.0)])

    def test_first_session_leavers(self):
        for i in range(4):
            sid = f'h{i}'
            self.born(sid, day(-6), [day(-6)])
            self.sql('INSERT INTO stat_play(day, sid, secs, sessions, cmds, first_at, last_at, hours, sess_at, lens) VALUES (?,?,?,?,?,?,?,?,?,?)',
                     (day(-6), sid, 120 * (i + 1), 1 if i < 3 else 2, 5, 1.0, 2.0, 0, 1.0, ''))
        self.sql('INSERT INTO stat_play(day, sid, secs, sessions, cmds, first_at, last_at, hours, sess_at, lens) VALUES (?,?,?,?,?,?,?,?,?,?)',
                 (day(-5), 'h0', 60, 1, 1, 1.0, 2.0, 0, 1.0, ''))          # h0 came back the next day
        self.sql('INSERT INTO stat_leave_last(sid, at, payload) VALUES (?, ?, ?)', ('h1', time.time(), '{"v":"loading"}'))
        with st._read(self.store, 5000) as db:
            f = ar.first_session(db, datetime.datetime.now(VN).date())
        self.assertEqual((f['cohort'], f['n'], f['pct'], f['median_min']), (4, 2, 50.0, 5.0))
        self.assertEqual(f['screen'], [dict(label='loading', n=1, pct=100.0)])

    def test_sources_and_loads(self):
        for i, src in enumerate(['facebook', 'facebook', 'tiktok']):
            sid = f's{i}'
            self.born(sid, day(-8), [day(-8)] + ([day(-7)] if i == 0 else []))
            self.sql('INSERT INTO stat_acquisition(sid, at, day, ref_domain) VALUES (?, ?, ?, ?)', (sid, time.time(), day(-8), src))
        self.sql("INSERT INTO stat_milestones(sid, key, at) VALUES ('s1', 'served1', 1.0)")
        for ms_, n in ((1000, 50), (3000, 40), (9000, 10)):
            self.sql("INSERT INTO stat_loads(day, metric, net, who, cache, tier, bucket, n) VALUES (?, 'frame', '4g', 'ret', 'warm', 'mid', ?, ?)",
                     (day(-1), rt.load_bucket(ms_), n))
        today = datetime.datetime.now(VN).date()
        with st._read(self.store, 5000) as db:
            s = ar.sources(db, today)
            L = ar.loads(db, today)
        fb = next(x for x in s['d30'] if x['source'] == 'facebook')
        self.assertEqual((fb['n'], fb['d1'], fb['d7'], fb['served1']), (2, 50.0, 0.0, 50.0))
        self.assertEqual(s['d7'], [])                                     # born 8 days ago: outside 7 days
        w = L['week']['frame']
        self.assertEqual(w['n'], 100)
        self.assertTrue(900 <= w['p50'] <= 1000, w)
        self.assertTrue(2750 <= w['p75'] <= 3000, w)
        self.assertTrue(w['p90'] <= 3000 and w['p90'] >= 2750, w)

    def test_career_errors_from_rollups_and_live_rows(self):
        self.sql("INSERT INTO stat_actions_daily(day, career, action, players, n, errors, err) VALUES (?, 'milk_tea', 'mt_serve', 10, 100, 20, 'Sai món')", (day(-2),))
        self.sql("INSERT INTO stat_rollups(kind, day, rows, at) VALUES ('actions', ?, 1, 1.0)", (day(-2),))
        self.sql("INSERT INTO stat_actions(day, sid, career, action, n, errors, err) VALUES (?, 'x', 'milk_tea', 'mt_serve', 10, 5, 'Sai món')", (day(0),))
        self.sql("INSERT INTO stat_actions(day, sid, career, action, n, errors, err) VALUES (?, 'x', 'milk_tea', 'mt_pick', 50, 0, NULL)", (day(0),))
        with st._read(self.store, 5000) as db:
            e = ar.action_errors(db, datetime.datetime.now(VN).date())
        self.assertEqual(e['milk_tea'], [dict(action='mt_serve', n=110, errors=25, rate=22.7, err='Sai món')])


# ---------------------------------------------------------------- pruning and rollups
class PruneTests(Base):
    def test_rollup_then_prune(self):
        old, kept = day(-rt.ACTIONS_KEEP_DAYS - 2), day(-3)
        for d in (old, kept):
            for sid, n, e in (('a', 3, 1), ('b', 2, 0)):
                self.sql("INSERT INTO stat_actions(day, sid, career, action, n, errors, err) VALUES (?, ?, 'milk_tea', 'serve', ?, ?, ?)",
                         (d, sid, n, e, 'oops' if e else None))
        now = time.time()
        self.sql('INSERT INTO stat_leaves(sid, at, day, payload) VALUES (?, ?, ?, ?)', ('a', now - (rt.LEAVES_KEEP_DAYS + 1) * 86400, old, '{}'))
        self.sql('INSERT INTO stat_leaves(sid, at, day, payload) VALUES (?, ?, ?, ?)', ('a', now - 86400, kept, '{}'))
        self.sql('INSERT INTO stat_leave_last(sid, at, payload) VALUES (?, ?, ?)', ('z', now - (rt.LEAVES_KEEP_DAYS + 1) * 86400, '{}'))
        self.sql("INSERT INTO stat_client_errors(day, kind, message_key, screen, count, last_at) VALUES (?, 'js', 'x', '-', 1, 1.0)", (old,))
        self.sql("INSERT INTO stat_client_errors(day, kind, message_key, screen, count, last_at) VALUES (?, 'js', 'x', '-', 1, 1.0)", (kept,))
        self.sql("INSERT INTO stat_loads(day, metric, net, who, cache, tier, bucket, n) VALUES (?, 'frame', '4g', 'new', '?', '?', 3, 1)",
                 (day(-rt.LOADS_KEEP_DAYS - 1),))
        with patch.object(rt, 'BATCH', 1):
            out = rt.maintain(self.store, now, pause=0, force=True)
        self.assertEqual(self.q('SELECT DISTINCT day FROM stat_actions'), [(kept,)])
        daily = self.q('SELECT day, career, action, players, n, errors, err FROM stat_actions_daily ORDER BY day')
        self.assertEqual(daily, [(old, 'milk_tea', 'serve', 2, 5, 1, 'oops'), (kept, 'milk_tea', 'serve', 2, 5, 1, 'oops')])
        self.assertEqual(self.q('SELECT day FROM stat_leaves'), [(kept,)])
        self.assertEqual(self.q('SELECT COUNT(*) FROM stat_leave_last'), [(0,)])
        self.assertEqual(self.q('SELECT day FROM stat_client_errors'), [(kept,)])
        self.assertEqual(self.q('SELECT COUNT(*) FROM stat_loads'), [(0,)])
        self.assertEqual((out['actions'], out['leaves']), (2, 1))
        again = rt.maintain(self.store, now, pause=0, force=True)        # idempotent: nothing rolled twice
        self.assertEqual((again['rolled'], again['actions']), (0, 0))
        self.assertEqual(len(self.q('SELECT * FROM stat_actions_daily')), 2)

    def test_today_is_not_rolled_and_a_day_waits_for_its_late_flushes(self):
        self.sql("INSERT INTO stat_actions(day, sid, career, action, n, errors) VALUES (?, 'a', '', 'settings', 1, 0)", (day(0),))
        self.sql("INSERT INTO stat_actions(day, sid, career, action, n, errors) VALUES (?, 'a', '', 'settings', 1, 0)", (day(-1),))
        midnight = datetime.datetime.combine(datetime.datetime.now(VN).date(), datetime.time(), VN).timestamp()
        rt.maintain(self.store, midnight + 60, pause=0, force=True)       # one minute after midnight: yesterday may still get counts
        self.assertEqual(self.q('SELECT COUNT(*) FROM stat_actions_daily'), [(0,)])
        rt.maintain(self.store, midnight + rt.ROLL_AFTER + 60, pause=0, force=True)
        self.assertEqual(self.q('SELECT day FROM stat_actions_daily'), [(day(-1),)])

    def test_peak_hours_and_lock(self):
        evening = datetime.datetime.combine(datetime.datetime.now(VN).date(), datetime.time(18, 30), VN).timestamp()
        self.assertEqual(rt.maintain(self.store, evening)['skipped'], 'peak')
        fd = rt._lock(self.store)
        try:
            if type(fd) is int:
                self.assertEqual(rt.maintain(self.store, evening, force=True)['skipped'], 'locked')
        finally:
            rt._unlock(fd)

    def test_upkeep_is_wired_to_the_job_and_housekeeping(self):
        import server
        src = Path(server.__file__).read_text(encoding='utf-8')
        self.assertIn('admin_stats.upkeep(store)', src)
        with patch.object(rt, 'maintain', return_value=dict(ok=1)) as m, patch.object(rt, '_peak', lambda now: False):
            st._Job(self.store, None, pause=0).purge()
        m.assert_called_once()


if __name__ == '__main__':
    unittest.main()
