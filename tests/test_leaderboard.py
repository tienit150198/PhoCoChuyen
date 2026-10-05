"""Bảng xếp hạng (game/leaderboard.py): scoring, ordering, privacy, storage hooks,
backfill and the HTTP API."""
import http.client, json, os, re, tempfile, threading, time, unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from game import accounts, social
from game import leaderboard as lb
from game.engine import new_state
from game.storage import Store

ROOT =Path(__file__).resolve().parents[1]
FORMAT = 'mot-ngay-lam-nghe/save-v4'
GROUPS = ('work_safety', 'customer_service', 'grooming')  # real certificate ids: imported saves are validated


def crafted(name='Mây', **careers):
    """A valid save with some progress: careers={'grocery': (xp, day, served)}."""
    s = new_state()
    s['name'] = name
    for cid, (xp, day, served) in careers.items():
        c = s['careers'][cid]
        c.update(xp=xp, day=day, started=True)
        c['metrics']['served'] = served
    return s


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db')
        social.ensure(self.store)
        self.n = 0
        lb.clear_cache()

    def tearDown(self):
        lb.clear_cache()
        self.store.close_pool()  # Windows: no open handle on the file being removed
        self.tmp.cleanup()

    def cmd(self, token, action, payload=None, career=None):
        self.n += 1
        rev = self.store.read(token)[1]
        return self.store.command(token, f'lb-test-{self.n:05d}', rev, career, action, payload or {})

    def player(self, state=None, account=None):
        """A session with `state` imported through the real command path; `account`
        = display name registers it (returns the account's device token)."""
        token, _, _ = self.store.session()
        if state is not None:
            self.cmd(token, 'import_save', {'save': {'format': FORMAT, 'state': state}})
        if account:
            self.n += 1
            out = accounts.register(self.store, token, dict(username=f'user{self.n}x', password='mat-khau-dai-1', confirm='mat-khau-dai-1', display=account))
            token = out['token']
        return token

    def sid(self, token):
        return self.store.key(token)

    def rows(self, token):
        return {r['board']: r for r in lb.export_rows(self.store, self.sid(token))}


class ScoringTests(unittest.TestCase):
    def test_per_career_and_overall_scores(self):
        s = crafted(grocery=(400, 6, 20), florist=(95, 2, 3), milk_tea=(0, 1, 0))
        s['careers']['grocery']['feed'] = [dict(stars=5), dict(stars=4), dict(stars=None), dict(text='no stars')]
        out = lb.summary(s)
        # score, k1 (days), k2 (stars x10), level, days, served, stars, mastered
        self.assertEqual(out['grocery'], (400, 5, 45, 5, 5, 20, 45, 1))
        self.assertEqual(out['florist'], (95, 1, 0, 2, 1, 3, 0, 0))
        self.assertNotIn('milk_tea', out)  # no progress there: not on that board
        from game.journey import maturity
        score = 400 + 95 + 80 * 2  # the journey's maturity XP
        self.assertEqual(out['all'][0], score)
        self.assertEqual(out['all'][3], maturity(score)['level'])
        self.assertEqual(out['all'][1], 1)   # mastered: level 3+ at grocery only
        self.assertEqual(out['all'][4], 6)   # days worked in total
        self.assertEqual(out['all'][5], 23)  # customers served in total
        self.assertNotIn('certs', out)
        self.assertIsNone(out[lb.NAME])      # the default name is not a public name

    def test_certificates_board(self):
        s = crafted(grocery=(10, 1, 1))
        s['journey']['certificates'] = {
            'food': dict(score=80, best=92, earned_day=9, attempts=2),
            'money': dict(score=70, best=75, earned_day=4, attempts=1),
            'failed': dict(score=40, best=40, earned_day=None, attempts=3),
            'junk': 'x'}
        n, best, day = lb._certs(s)
        self.assertEqual((n, best, day), (2, 167, 9))
        self.assertEqual(lb.summary(s)['certs'], (2, 167, -9, 2, 9, 167, 0, 2))

    def test_old_saves_without_fields(self):
        self.assertEqual(lb.summary(None), {})
        self.assertEqual(lb.summary({'careers': 'x'}), {})
        old = {'name': 'Bé Na', 'careers': {'grocery': {}, 'florist': {'xp': 'lots', 'metrics': None, 'feed': 'x', 'day': None},
                                           'milk_tea': {'xp': 180, 'day': 3}, 'not_a_career': {'xp': 999}}}
        out = lb.summary(old)
        self.assertEqual(out['milk_tea'], (180, 2, 0, 3, 2, 0, 0, 1))
        self.assertEqual(set(out), {'milk_tea', 'all', lb.NAME})
        self.assertEqual(out[lb.NAME], 'Bé Na')
        for journey in (None, 'x', {}, {'certificates': None}, {'certificates': ['a']}):
            s = dict(old, journey=journey)
            self.assertNotIn('certs', lb.summary(s))
            self.assertEqual(lb.certificates_of(s), {})

    def test_guest_names_are_filtered(self):
        self.assertEqual(lb.guest_name('Bé Na'), 'Bé Na')
        for bad in ('Mây', '', '   ', None, 42, '<script>alert(1)</script>', 'Na<b>', 'www.lua.com', '0912345678', 'vcl'):
            self.assertIsNone(lb.guest_name(bad), bad)

    def test_diff_only_when_something_moved(self):
        a = lb.summary(crafted(grocery=(90, 2, 3)))
        self.assertIsNone(lb.diff(a, lb.summary(crafted(grocery=(90, 2, 3)))))
        self.assertIsNotNone(lb.diff(a, lb.summary(crafted(grocery=(120, 2, 4)))))
        self.assertIsNotNone(lb.diff(a, lb.summary(crafted('Bé Na', grocery=(90, 2, 3)))))

    def test_summary_is_cheap(self):
        s = crafted(grocery=(400, 6, 20), florist=(95, 2, 3))
        for c in s['careers'].values():
            c['feed'] = [dict(stars=4)] * 100
        t = time.perf_counter()
        for _ in range(50):
            lb.summary(s)
        self.assertLess((time.perf_counter() - t) / 50, .01)  # well under a millisecond on a normal machine


class BoardTests(Base):
    def test_ordering_and_deterministic_ties(self):
        a = self.player(crafted(grocery=(300, 4, 9)), account='An')
        b = self.player(crafted(grocery=(300, 6, 9)), account='Bình')   # same XP, more days -> ahead
        c = self.player(crafted(grocery=(500, 2, 9)), account='Chi')    # most XP -> first
        d = self.player(crafted(grocery=(300, 4, 9)), account='Dung')   # full tie with An, reached later -> after An
        v = lb.view(self.store, 'grocery')
        self.assertEqual([r['name'] for r in v['rows']], ['Chi', 'Bình', 'An', 'Dung'])
        self.assertEqual([r['rank'] for r in v['rows']], [1, 2, 3, 4])
        self.assertEqual(v['total'], 4)
        # A full tie (same second) falls back to a fixed order, the same on every read.
        with self.store.connect() as db:
            db.execute("UPDATE leaderboard SET since=1 WHERE board='grocery' AND sid IN (?,?)", (self.sid(a), self.sid(d)))
        lb.clear_cache()
        first = [r['name'] for r in lb.view(self.store, 'grocery')['rows']]
        lb.clear_cache()
        self.assertEqual(first, [r['name'] for r in lb.view(self.store, 'grocery')['rows']])
        self.assertEqual(first[:2], ['Chi', 'Bình'])

    def test_stars_break_ties_after_days(self):
        with self.store.connect() as db:
            for sid, stars in (('s-low', 38), ('s-high', 47), ('s-none', 0)):
                db.execute("INSERT INTO sessions(sid,csrf,state,revision) VALUES(?,?,?,1)", (sid, 'x', '{}'))
                lb.write(db, sid, {'florist': (200, 3, stars, 3, 3, 10, stars, 1), lb.NAME: 'Khách ' + sid[2:]}, now=5.0)
                db.execute("INSERT INTO leaderboard_players(sid,show,updated) VALUES(?,1,0) ON CONFLICT(sid) DO UPDATE SET show=1", (sid,))
        rows = lb.view(self.store, 'florist')['rows']
        self.assertEqual([r['name'] for r in rows], ['Khách high', 'Khách low', 'Khách none'])
        self.assertEqual(rows[0]['stars'], 4.7)
        self.assertIsNone(rows[2]['stars'])
        self.assertTrue(all(r['guest'] for r in rows))

    def test_me_outside_the_top_and_payload_has_no_ids(self):
        top = [self.player(crafted(grocery=(900 - i * 100, 3, 5)), account=f'Người {i}') for i in range(3)]
        me = self.player(crafted(grocery=(50, 2, 1)), account='Tôi Đây')
        v = lb.view(self.store, 'grocery', 2, me)
        self.assertEqual(len(v['rows']), 2)
        self.assertEqual(v['me']['rank'], 4)
        self.assertTrue(v['me']['visible'])
        self.assertFalse(any(r['me'] for r in v['rows']))
        mine = lb.view(self.store, 'grocery', 50, me)
        self.assertTrue(mine['rows'][3]['me'])
        blob = json.dumps(mine, ensure_ascii=False)
        for token in top + [me]:
            self.assertNotIn(self.sid(token), blob)
        self.assertNotIn('user', blob)  # usernames never leave the server
        for key in ('sid', 'username', 'uid', 'ip'):
            self.assertNotIn(f'"{key}"', blob)

    def test_privacy_account_default_on_and_opt_out(self):
        acc = self.player(crafted(grocery=(200, 3, 5)), account='Mai Chi')
        other = self.player(crafted(grocery=(100, 3, 5)), account='Lan')
        self.assertEqual([r['name'] for r in lb.view(self.store, 'all')['rows']], ['Mai Chi', 'Lan'])
        out = lb.set_visible(self.store, acc, self.store.read(acc)[0], False)
        self.assertFalse(out['visible'])
        v = lb.view(self.store, 'all', token=acc)
        self.assertEqual([r['name'] for r in v['rows']], ['Lan'])
        self.assertEqual(v['total'], 1)
        self.assertFalse(v['me']['visible'])
        self.assertEqual(v['me']['rank'], 1)  # "if shown, you would be first"
        self.assertEqual(lb.view(self.store, 'all', token=other)['me']['rank'], 1)
        lb.set_visible(self.store, acc, self.store.read(acc)[0], True)
        self.assertEqual([r['name'] for r in lb.view(self.store, 'all')['rows']], ['Mai Chi', 'Lan'])

    def test_guest_display_needs_a_name_and_an_opt_in(self):
        named = self.player(crafted('Bé Na', grocery=(300, 3, 5)))
        nameless = self.player(crafted(grocery=(400, 3, 5)))
        acc = self.player(crafted(grocery=(100, 3, 5)), account='Tài Khoản')
        self.assertEqual([r['name'] for r in lb.view(self.store, 'grocery')['rows']], ['Tài Khoản'])
        out = lb.set_visible(self.store, named, self.store.read(named)[0], True)
        self.assertTrue(out['visible'])
        out = lb.set_visible(self.store, nameless, self.store.read(nameless)[0], True)
        self.assertFalse(out['visible'])
        self.assertFalse(out['can_show'])
        self.assertIn('Đặt tên', out['message'])
        rows = lb.view(self.store, 'grocery')['rows']
        self.assertEqual([(r['name'], r['guest']) for r in rows], [('Bé Na', True), ('Tài Khoản', False)])
        # The account's own name is its display name, never the username.
        self.assertNotIn('user', json.dumps(rows))
        # A guest who renames the character to something unfit disappears from the board.
        self.cmd(named, 'settings', {'name': 'vcl'})
        lb.clear_cache()
        self.assertEqual([r['name'] for r in lb.view(self.store, 'grocery')['rows']], ['Tài Khoản'])

    def test_names_are_stored_verbatim_and_safely(self):
        tricky = "O'Neil -- 1"
        acc = self.player(crafted(grocery=(100, 2, 1)), account=tricky)
        self.assertEqual(lb.view(self.store, 'grocery', token=acc)['rows'][0]['name'], tricky)
        with self.assertRaises(accounts.AccountError):
            accounts.clean_display('<img src=x onerror=alert(1)>')
        # The browser renders every name through escapeHTML and marks it data-no-translate.
        js = (ROOT / 'public/js/v4/leaderboard.js').read_text(encoding='utf-8')
        self.assertIn('${esc(r.name)}', js)
        self.assertIn('${esc(me.name)}', js)
        self.assertIsNone(re.search(r'\$\{(r|me)\.name\}', js))
        self.assertNotIn('innerHTML', js)

    def test_certs_board_order(self):
        def with_certs(*recs):
            s = crafted(grocery=(10, 2, 1))
            s['journey']['life_day'] = 10
            s['journey']['certificates'] = {g: dict(score=b, best=b, earned_day=d, attempts=1) for g, (b, d) in zip(GROUPS, recs)}
            return s
        self.player(with_certs((90, 5)), account='Một Chứng Chỉ')
        self.player(with_certs((80, 5), (76, 9)), account='Hai Muộn')
        self.player(with_certs((80, 3), (76, 4)), account='Hai Sớm')
        self.player(with_certs((95, 3), (90, 8)), account='Hai Giỏi')
        self.player(crafted(grocery=(10, 2, 1)), account='Chưa Có')
        v = lb.view(self.store, 'certs')
        self.assertEqual([r['name'] for r in v['rows']], ['Hai Giỏi', 'Hai Sớm', 'Hai Muộn', 'Một Chứng Chỉ'])
        self.assertEqual(v['rows'][0]['certs'], 2)
        self.assertEqual(v['rows'][0]['best'], 185)


    def test_parse_query(self):
        self.assertEqual(lb.parse_query({}), ('all', 50))
        self.assertEqual(lb.parse_query({'career': 'grocery', 'limit': '10'}), ('grocery', 10))
        self.assertEqual(lb.parse_query({'board': 'certs'}), ('certs', 50))
        for bad in ({'career': 'nope'}, {'career': '../x'}, {'limit': '0'}, {'limit': '51'}, {'limit': 'abc'}, {'limit': '-1'}, {'limit': '１０'}):
            with self.assertRaises(ValueError):
                lb.parse_query(bad)


class StorageHookTests(Base):
    def test_rows_follow_the_save(self):
        token = self.player(crafted('Bé Na', grocery=(200, 3, 5), florist=(30, 1, 1)))
        rows = self.rows(token)
        self.assertEqual(set(rows), {'grocery', 'florist', 'all'})
        self.assertEqual(rows['grocery']['score'], 200)
        # Replacing the save with less progress drops the boards it no longer earns.
        self.cmd(token, 'import_save', {'save': {'format': FORMAT, 'state': crafted('Bé Na', grocery=(250, 4, 6))}})
        rows = self.rows(token)
        self.assertEqual(set(rows), {'grocery', 'all'})
        self.assertEqual(rows['grocery']['score'], 250)

    def test_written_only_when_a_number_moved(self):
        token = self.player(crafted(grocery=(200, 3, 5)))
        calls = []
        real = lb.write
        with mock.patch.object(lb, 'write', side_effect=lambda *a, **k: (calls.append(a[2]), real(*a, **k))[1]):
            self.cmd(token, 'settings', {'sound': False})          # nothing on a board moved
            self.cmd(token, 'select_career', {}, 'grocery')
            self.assertEqual(calls, [])
            self.cmd(token, 'settings', {'name': 'Bé Na'})         # the guest name did
            self.assertEqual(len(calls), 1)

    def test_since_keeps_who_got_there_first(self):
        token = self.player(crafted(grocery=(200, 3, 5)))
        since = self.rows(token)['grocery']['since']
        time.sleep(.01)
        self.cmd(token, 'settings', {'name': 'Bé Na'})  # rows re-synced, XP unchanged
        self.assertEqual(self.rows(token)['grocery']['since'], since)

    def test_real_play_updates_the_board(self):
        from tests.helpers import Journey
        j = Journey('mother_baby')
        j.solve()
        token = self.player(j.state)
        self.assertGreater(self.rows(token)['mother_baby']['score'], 0)
        self.assertGreater(self.rows(token)['all']['served'], 0)

    def test_delete_and_prune_forget_the_rows(self):
        token = self.player(crafted('Bé Na', grocery=(200, 3, 5)))
        lb.set_visible(self.store, token, self.store.read(token)[0], True)
        sid = self.sid(token)
        self.store.delete(token)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM leaderboard WHERE sid=?", (sid,)).fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM leaderboard_players WHERE sid=?", (sid,)).fetchone()[0], 0)
        idle = self.player(crafted(grocery=(200, 3, 5)))
        sid = self.sid(idle)
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET updated_at=to_char((statement_timestamp() AT TIME ZONE 'UTC') - interval '400 days', 'YYYY-MM-DD HH24:MI:SS') WHERE sid=?", (sid,))
        self.store.prune(idle_days=180)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM leaderboard WHERE sid=?", (sid,)).fetchone()[0], 0)


class BackfillTests(Base):
    def raw_save(self, state, revision=3):
        """A save written by an older server: no leaderboard rows."""
        token, _, _ = self.store.session()
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET state=?,revision=? WHERE sid=?", (json.dumps(state, ensure_ascii=False), revision, self.sid(token)))
        return token

    def test_backfill_fills_marks_and_is_idempotent(self):
        a = self.raw_save(crafted('Bé Na', grocery=(300, 3, 5)))
        b = self.raw_save(crafted(florist=(120, 2, 3)))
        fresh = self.raw_save(new_state(), revision=0)       # never played: skipped
        broken = self.raw_save(crafted(grocery=(1, 1, 1)))
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET state='{not json' WHERE sid=?", (self.sid(broken),))
        self.assertEqual(self.rows(a), {})
        n = lb.backfill(self.store, pause=0)
        self.assertEqual(n, 3)
        self.assertEqual(set(self.rows(a)), {'grocery', 'all'})
        self.assertEqual(set(self.rows(b)), {'florist', 'all'})
        self.assertEqual(self.rows(fresh), {})
        self.assertEqual(self.rows(broken), {})
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT name FROM leaderboard_players WHERE sid=?", (self.sid(a),)).fetchone()[0], 'Bé Na')
        self.assertEqual(lb.backfill(self.store, pause=0), 0)  # done for this VERSION
        with self.store.connect() as db:
            db.execute("DELETE FROM leaderboard")
        self.assertEqual(lb.backfill(self.store, pause=0, force=True), 3)
        self.assertEqual(set(self.rows(a)), {'grocery', 'all'})

    def test_accounts_first_and_stop(self):
        guest = self.raw_save(crafted(grocery=(300, 3, 5)))
        acc = self.player(None, account='Tài Khoản')
        with self.store.connect() as db:
            db.execute("UPDATE sessions SET state=?,revision=4 WHERE sid=?", (json.dumps(crafted(grocery=(100, 2, 1))), self.sid(acc)))
        order = []
        real = lb._sync

        def spy(store, items):
            order.extend(sid for sid, _, _ in items)
            return real(store, items)
        with mock.patch.object(lb, '_sync', side_effect=spy):
            lb.backfill(self.store, pause=0, batch=1)
        self.assertEqual(order, [self.sid(acc), self.sid(guest)])
        stop = threading.Event()
        stop.set()
        with self.store.connect() as db:
            db.execute("DELETE FROM leaderboard_meta")
        self.assertEqual(lb.backfill(self.store, stop, pause=0), 0)
        with self.store.connect() as db:
            self.assertIsNone(lb._meta(db, 'backfill'))  # not marked done: runs again next start

    def test_backfill_rereads_a_save_played_meanwhile(self):
        token = self.raw_save(crafted(grocery=(300, 3, 5)))
        real = lb._sync
        raced = []

        def racing(store, items):
            if not raced:  # the player finishes a task between the read and the write
                raced.append(1)
                with store.connect() as db:
                    db.execute("UPDATE sessions SET state=?,revision=revision+1 WHERE sid=?", (json.dumps(crafted(grocery=(330, 3, 6))), items[0][0]))
            return real(store, items)
        with mock.patch.object(lb, '_sync', side_effect=racing):
            lb.backfill(self.store, pause=0)
        self.assertEqual(self.rows(token)['grocery']['score'], 330)

    def test_run_backfill_never_raises(self):
        with mock.patch.object(lb, 'backfill', side_effect=RuntimeError('boom')), patch('sys.stderr'):
            lb.run_backfill(self.store)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from server import GameServer
        cls.quiet = patch.dict(os.environ, {'QUIET': '1'})
        cls.quiet.start()
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.temp.name) / 'state.db')
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
        cls.quiet.stop()
        lb.clear_cache()

    def setUp(self):
        self.cookie = self.csrf = None
        lb.clear_cache()

    def req(self, path, method='GET', body=None, headers=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if self.cookie:
            h['Cookie'] = self.cookie
        if self.csrf:
            h['X-Game-CSRF'] = self.csrf
        if body is not None:
            h['Content-Type'] = 'application/json'
            body = json.dumps(body)
        h.update(headers or {})
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse()
        data = res.read()
        con.close()
        return res.status, json.loads(data or b'{}')

    def bootstrap(self):
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request('GET', '/api/bootstrap', headers={'Host': f'127.0.0.1:{self.port}'})
        res = con.getresponse()
        data = json.loads(res.read())
        con.close()
        self.cookie = res.getheader('Set-Cookie').split(';')[0]
        self.csrf = data['csrf']
        return self.cookie.split('=', 1)[1]

    def test_get_board_and_validation(self):
        status, d = self.req('/api/leaderboard')
        self.assertEqual(status, 200)
        self.assertEqual((d['board'], d['rows'], d['me']), ('all', [], None))
        for path in ('/api/leaderboard?career=hacker', '/api/leaderboard?career=grocery&limit=0', '/api/leaderboard?limit=500',
                     '/api/leaderboard?limit=1e3', "/api/leaderboard?career=all'--"):
            self.assertEqual(self.req(path)[0], 400, path)
        self.assertEqual(self.req('/api/leaderboard?board=certs&limit=5')[0], 200)
        self.assertEqual(self.req('/api/leaderboard', headers={'Host': 'evil.example'})[0], 403)

    def test_me_and_visibility_route(self):
        token = self.bootstrap()
        n = [0]

        def cmd(action, payload, career=None):
            n[0] += 1
            rev = self.store.read(token)[1]
            return self.store.command(token, f'lb-http-{n[0]:04d}', rev, career, action, payload)
        cmd('import_save', {'save': {'format': FORMAT, 'state': crafted('Bé Na', grocery=(150, 3, 4))}})
        status, d = self.req('/api/leaderboard?career=grocery')
        self.assertEqual(status, 200)
        self.assertEqual(d['rows'], [])
        self.assertEqual(d['me']['rank'], 1)
        self.assertFalse(d['me']['visible'])
        self.assertTrue(d['me']['can_show'])
        # Writes need the CSRF token and a boolean.
        csrf, self.csrf = self.csrf, 'wrong'
        self.assertEqual(self.req('/api/leaderboard/visibility', 'POST', {'visible': True})[0], 403)
        self.csrf = csrf
        self.assertEqual(self.req('/api/leaderboard/visibility', 'POST', {'visible': 'yes'})[0], 400)
        self.assertEqual(self.req('/api/leaderboard/visibility', 'POST', {'visible': True}, {'Origin': 'https://elsewhere.example'})[0], 403)
        status, d = self.req('/api/leaderboard/visibility', 'POST', {'visible': True})
        self.assertEqual(status, 200)
        self.assertTrue(d['visible'])
        status, d = self.req('/api/leaderboard?career=grocery')
        self.assertEqual([(r['name'], r['guest'], r['me']) for r in d['rows']], [('Bé Na', True, True)])

    def test_rate_limited(self):
        self.cookie = 'mnl_session=' + 'ab' * 32  # not a session: limited per token string anyway
        codes = {self.req('/api/leaderboard?limit=1')[0] for _ in range(125)}
        self.assertIn(429, codes)


if __name__ == '__main__':
    unittest.main()
