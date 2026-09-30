"""Admin statistics ("Thống kê"): metrics on a seeded DB, privacy of the payload,
the cache, the AI counters and the admin-only HTTP route (game/admin_stats.py)."""
import copy, datetime, http.client, json, os, sqlite3, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch

from game import accounts, admin_stats as st, player_feedback as pfb, social
from game.engine import new_state
from game.journey import enable_story
from game.storage import Store
from server import GameServer

REG = dict(password='matkhau-rat-dai', confirm='matkhau-rat-dai', display='Người Thử')
SECRET_NAME = 'Tên Riêng Bí Mật'


# Time budgets: these tests check the numbers, not the machine's speed (a busy disk can take
# seconds to extend a file); the budget test passes its own small `ms`.
_BUDGETS = dict(REQUEST_MS=60000, STATEMENT_MS=60000, CHUNK_MS=60000, COUNT_MS=60000)
_saved = {}


def setUpModule():
    for k, v in _BUDGETS.items():
        _saved[k] = getattr(st, k)
        setattr(st, k, v)


def tearDownModule():
    for k, v in _saved.items():
        setattr(st, k, v)


def vn_today():
    return datetime.datetime.now(st.VN).date()


class Seeded(unittest.TestCase):
    def setUp(self):
        st.clear_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        social.ensure(self.store)
        st.ensure(self.store)
        self.tokens = []

    def tearDown(self):
        st.stop_jobs()
        st.clear_cache()
        self.store.close_pool()  # Windows: no open handle on the file being removed
        self.tmp.cleanup()

    def save(self, edit=None, played=True):
        """A new save; `edit(state)` shapes it, then it is written like a command would."""
        token, _, _ = self.store.session()
        self.tokens.append(token)
        if played:
            s = self.store.read(token)[0]
            if edit:
                edit(s)
            with self.store.connect() as db:
                db.execute('UPDATE sessions SET state=?, revision=revision+1, updated_at=CURRENT_TIMESTAMP WHERE sid=?',
                           (json.dumps(s, ensure_ascii=False), self.store.key(token)))
        return token

    def sid(self, token):
        return self.store.key(token)


def english_dark(s):
    s['name'] = SECRET_NAME
    s['settings'].update(lang='en', uiTheme='dem', aiConsent=False, music=True, musicTrack='calm')
    c = s['careers']['mother_baby']
    c.update(started=True, day=5, xp=200)          # 4 days played, level 3
    s['careers']['pharmacy'].update(started=True, day=2, xp=0)
    s['journey'].update(wallet=-50, in_debt=True, chapter=2, life_day=9)
    s['journey'].setdefault('invest', {}).update(coin=dict(units=3, basis=10, realised=0, fees=0, trades=2),
                                                 stats=dict(declined=0, joined=1, lost=120, next_scam=0))


def vietnamese(s):
    s['settings'].update(lang='vi', uiTheme='kem', aiConsent=True, music=False)
    s['careers']['mother_baby'].update(started=True, day=3, xp=90)   # 2 days, level 2
    s['journey'].update(wallet=300, life_day=4)
    s['journey']['life'] = dict(spirit=60, stats=dict(outings=2, scams=1, rumours=0, warm=3, hard=1, given=0))
    s['journey']['board'] = dict(posts=[{}, {}, {}], stats=dict(player_posts=2, player_replies=1, reacts=4))


def fresh_player(s):
    s['journey'].update(wallet=1000)


class MetricsTests(Seeded):
    def seed(self):
        self.a = self.save(english_dark)
        self.b = self.save(vietnamese)
        self.c = self.save(fresh_player)
        self.bounce = self.save(played=False)   # opened the page, never played

    def test_players_and_activity(self):
        self.seed()
        data = st.compute(self.store, 7)
        p = data['players']
        self.assertEqual(len(p['days']), 7)
        self.assertEqual(p['days'][-1], vn_today().isoformat())
        self.assertEqual((p['total'], p['played'], p['accounts'], p['guests']), (4, 3, 0, 3))   # guests: played, no account
        self.assertEqual(p['dau'][-1], 3)
        self.assertEqual(sum(p['dau']), 3)
        self.assertEqual((p['wau'], p['mau']), (3, 3))
        self.assertEqual(p['new_sessions'][-1], 4)
        self.assertEqual(p['new_players'][-1], 3)
        self.assertEqual(p['tracked_since'], vn_today().isoformat())
        # An account turns one guest save into an account save.
        accounts.register(self.store, self.a, dict(REG, username='someone_x'))
        p = st.compute(self.store, 30)['players']
        self.assertEqual((p['accounts'], p['account_saves'], p['guests']), (1, 1, 2))
        self.assertEqual(p['new_accounts'][-1], 1)
        self.assertEqual(len(p['dau']), 30)

    def test_play_economy_life_board(self):
        self.seed()
        d = st.compute(self.store, 7)
        play, eco = d['play'], d['economy']
        self.assertEqual(d['sample']['size'], 3)
        self.assertEqual(play['sample'], 3)
        by = {c['id']: c for c in play['careers']}
        self.assertEqual((by['mother_baby']['players'], by['mother_baby']['days']), (2, 6))
        self.assertEqual(by['mother_baby']['avg_level'], 2.5)
        self.assertEqual((by['pharmacy']['players'], by['pharmacy']['days']), (1, 1))
        self.assertEqual(play['careers'][0]['id'], 'mother_baby')
        self.assertEqual({x['key']: x['n'] for x in play['levels']}, {'2': 1, '3': 1})
        self.assertEqual({x['key']: x['n'] for x in play['lang']}, {'vi': 2, 'en': 1})
        self.assertEqual({x['key']: x['n'] for x in play['theme']}, {'kem': 2, 'dem': 1})
        self.assertEqual((play['story'], play['ai_on'], play['music_on']), (3, 2, 1))
        self.assertEqual({x['key']: x['n'] for x in play['chapters']}, {'1': 2, '2': 1})
        self.assertEqual(play['life_day']['median'], 4)
        self.assertEqual(eco['wallet']['median'], 300)
        self.assertEqual((eco['debt'], eco['investors'], eco['scam_lost'], eco['scam_victims'], eco['scam_joined']), (1, 1, 120, 1, 1))
        self.assertEqual({b['label']: b['n'] for b in eco['buckets']}['Nợ (< 0)'], 1)
        self.assertEqual(sum(b['n'] for b in eco['buckets']), 3)
        life, board = d['life'], d['board']
        self.assertGreaterEqual(life['saves'], 1)
        self.assertGreaterEqual(life['outings'], 2)
        self.assertEqual(board['posts'] >= 3 and board['player_posts'] >= 2 and board['active'] >= 1, True)

    def test_sql_and_python_readers_agree(self):
        self.seed()
        with self.store.connect() as db:
            rows, engine = st.sample(db)
            states = [json.loads(r[0]) for r in db.execute('SELECT state FROM sessions WHERE revision>0 ORDER BY updated_at DESC')]
        self.assertEqual(engine, 'sql')
        self.assertEqual(st.play_stats(rows), st.play_stats([st.compact(s) for s in states]))

    def test_missing_new_keys_are_guarded(self):
        def bare(s):
            s['journey'].pop('life', None); s['journey'].pop('board', None); s['journey'].pop('invest', None)
        self.save(bare)
        d = st.compute(self.store, 7)
        self.assertEqual((d['life']['saves'], d['board']['saves'], d['economy']['investors']), (0, 0, 0))
        self.assertIsNone(d['life']['avg_spirit'])
        # Weird values do not break the aggregation either.
        weird = st.compact({'settings': {'lang': 7}, 'journey': {'wallet': 'x', 'life': [], 'board': 3}, 'careers': {'x': 5}})
        out = st.play_stats([weird, {}])
        self.assertEqual(out['play']['lang'][0]['key'], 'khác')
        self.assertIsNone(out['economy']['wallet']['median'])

    def test_retention_d1_d7(self):
        today = vn_today()
        born = (today - datetime.timedelta(days=10)).isoformat()
        plus = lambda n: (today - datetime.timedelta(days=10 - n)).isoformat()
        sids = ['s1', 's2', 's3']
        with self.store.connect() as db:
            for sid in sids:
                db.execute('INSERT INTO stat_births(sid,day) VALUES(?,?)', (sid, born))
                db.execute('INSERT INTO stat_active(day,sid) VALUES(?,?)', (born, sid))
            db.execute('INSERT INTO stat_births(sid,day) VALUES(?,?)', ('bounce', born))      # never played: not in the cohort
            db.execute('INSERT INTO stat_active(day,sid) VALUES(?,?)', (plus(1), 's1'))
            db.execute('INSERT INTO stat_active(day,sid) VALUES(?,?)', (plus(1), 's2'))
            db.execute('INSERT INTO stat_active(day,sid) VALUES(?,?)', (plus(7), 's3'))
            # A player born yesterday is too young for D1.
            db.execute('INSERT INTO stat_births(sid,day) VALUES(?,?)', ('young', (today - datetime.timedelta(days=1)).isoformat()))
            db.execute('INSERT INTO stat_active(day,sid) VALUES(?,?)', ((today - datetime.timedelta(days=1)).isoformat(), 'young'))
            r = st.retention(db, today, 30)
        self.assertEqual(r['cohort'], 4)
        self.assertEqual((r['d1_n'], r['d7_n']), (3, 3))
        self.assertEqual((r['d1'], r['d7']), (66.7, 33.3))

    def test_triggers_follow_the_save(self):
        tok = self.save(fresh_player)
        sid = self.sid(tok)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM stat_births WHERE sid=?', (sid,)).fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM stat_active WHERE sid=?', (sid,)).fetchone()[0], 1)
        # A real command marks the day active too (idempotent per day).
        self.store.command(tok, 'req-000001', 1, None, 'settings', dict(lang='en'))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM stat_active WHERE sid=?', (sid,)).fetchone()[0], 1)
        self.store.delete(tok)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM stat_births WHERE sid=?', (sid,)).fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM stat_active WHERE sid=?', (sid,)).fetchone()[0], 0)
        st.ensure(self.store)   # idempotent

    def test_feedback_counts_newest_and_ack_time(self):
        tok = self.save(fresh_player)
        s = self.store.read(tok)[0]
        ids = [pfb.submit(self.store, tok, s, dict(kind=k, text=f'Góp ý loại {k}\ndòng hai'))['id'] for k in ('bug', 'bug', 'idea', 'praise')]
        with self.store.connect() as db:
            db.execute('UPDATE player_feedback SET created_at=created_at-7200')
        pfb.update(self.store, ids[0], status='seen')
        pfb.update(self.store, ids[0], status='done')     # a second change keeps the first time
        pfb.update(self.store, ids[2], status='done')
        fb = st.compute(self.store, 7)['feedback']
        kinds = {k['kind']: k for k in fb['kinds']}
        self.assertEqual((kinds['bug']['new'], kinds['bug']['done'], kinds['idea']['done'], kinds['praise']['new']), (1, 1, 1, 1))
        self.assertEqual((fb['open'], fb['unread'], fb['total'], fb['in_range']), (2, 2, 4, 4))
        self.assertEqual(fb['ack']['n'], 2)
        self.assertAlmostEqual(fb['ack']['median_h'], 2.0, delta=0.1)
        self.assertEqual([x['id'] for x in fb['newest']], ids[::-1])
        self.assertEqual(fb['newest'][0]['text'], 'Góp ý loại praise')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM stat_fb_ack').fetchone()[0], 2)
        pfb.forget(self.store, tok)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM stat_fb_ack').fetchone()[0], 0)

    def test_server_section(self):
        self.seed()
        srv = st.compute(self.store, 7)['server']
        tables = {t['name']: t['rows'] for t in srv['tables']}
        self.assertEqual(tables['sessions'], 4)
        self.assertIn('player_feedback', tables)
        self.assertGreater(srv['db_bytes'], 0)
        self.assertGreaterEqual(srv['uptime'], 0)
        self.assertTrue(srv['version'])

    def test_payload_has_no_personal_data(self):
        self.seed()
        accounts.register(self.store, self.b, dict(REG, username='private_user', display='Hiển Thị Riêng'))
        data = st.get(self.store, 30)
        text = json.dumps(data, ensure_ascii=False)
        with self.store.connect() as db:
            secrets_ = [r[0] for r in db.execute('SELECT sid FROM sessions')] + [r[0] for r in db.execute('SELECT csrf FROM sessions')]
            secrets_ += [r[0] for r in db.execute('SELECT pw FROM accounts')] + [r[0] for r in db.execute('SELECT token FROM logins')]
        for value in secrets_ + self.tokens + ['private_user', 'Hiển Thị Riêng', SECRET_NAME]:
            self.assertNotIn(value, text)
        for key in ('"sid"', '"token"', '"csrf"', '"pw"', '"password"', '"email"', '"username"', '"account"'):
            self.assertNotIn(key, text)


def varied(rng):
    """A save shaped by a seeded rng: every field the dashboard reads, in many shapes."""
    def edit(s):
        s['settings'].update(lang=rng.choice(['vi', 'en', 'vi']), uiTheme=rng.choice(['kem', 'dem', 'bien', 'keo']),
                             aiConsent=rng.random() < .5, music=rng.random() < .5, musicTrack=rng.choice(['calm', 'off']))
        j = s['journey']
        j.update(chapter=rng.randint(1, 5), life_day=rng.randint(1, 60), wallet=rng.randint(-300, 5000))
        j['in_debt'] = j['wallet'] < 0
        if rng.random() < .5:
            j.setdefault('invest', {}).update(coin=dict(units=rng.randint(0, 4), basis=10, realised=0, fees=0, trades=rng.randint(0, 3)),
                                              stats=dict(declined=0, joined=rng.randint(0, 2), lost=rng.choice([0, 80]), next_scam=0))
        if rng.random() < .5:
            j['life'] = dict(spirit=rng.randint(0, 100), stats=dict(outings=rng.randint(0, 5), scams=1, rumours=2, warm=3, hard=0, given=1))
        if rng.random() < .5:
            j['board'] = dict(posts=[{}] * rng.randint(0, 5), stats=dict(player_posts=rng.randint(0, 3), player_replies=1, reacts=2))
        for cid in rng.sample(sorted(s['careers']), rng.randint(1, 4)):
            s['careers'][cid].update(started=True, day=rng.randint(1, 20), xp=rng.randint(0, 600))
    return edit


class SplitTests(Seeded):
    """The operator page's summary + sections carry the same numbers as the one-statement
    computation they replace (sample() + play_stats(), players(), feedback()), and no request
    reads a save."""

    def seed(self, n=24):
        import random
        rng = random.Random(5)
        for i in range(n):
            self.save(varied(rng))
        self.save(played=False)
        accounts.register(self.store, self.tokens[0], dict(REG, username='someone_y'))
        s = self.store.read(self.tokens[1])[0]
        for k in ('bug', 'idea', 'praise'):
            pfb.submit(self.store, self.tokens[1], s, dict(kind=k, text=f'Góp ý {k}'))

    def legacy(self, days):
        """The computation before the split: one statement over the saves."""
        today = vn_today()
        with self.store.connect() as db:
            rows, engine = st.sample(db)
            return dict(players=st.players(db, days, today), feedback=st.feedback(db, days, time.time()),
                        sample=dict(size=len(rows), limit=st.SAMPLE, engine=engine), **st.play_stats(rows))

    def test_summary_and_sections_equal_the_old_computation(self):
        self.seed()
        st.refresh_now(self.store)          # what the background job does
        with patch.object(st, 'wake', lambda store, fresh=False: None):
            for days in st.RANGES:
                st.clear_cache()
                old = self.legacy(days)
                top = st.get_summary(self.store, days)
                sv = st.get_section(self.store, 'saves')
                sysd = st.get_section(self.store, 'system')
                self.assertEqual(top['players'], old['players'])
                self.assertEqual(top['feedback'], old['feedback'])
                for k in ('play', 'economy', 'life', 'board'):
                    self.assertEqual(sv[k], old[k], k)
                self.assertEqual({k: sv['sample'][k] for k in ('size', 'limit', 'engine')}, old['sample'])
                tables = {t['name']: t['rows'] for t in sysd['server']['tables']}
                self.assertEqual(tables['sessions'], 25)
                self.assertEqual(tables['accounts'], 1)
                self.assertFalse(any(t['approx'] for t in sysd['server']['tables']))
                full = st.get(self.store, days)          # the in-game tab: same parts
                for k in ('players', 'feedback', 'play', 'economy', 'life', 'board', 'sample'):
                    self.assertEqual(full[k], old[k], k)
                self.assertFalse(full['pending'])
        self.assertEqual(sv['sample']['size'], 24)

    def test_pure_python_twin_agrees_on_varied_saves(self):
        self.seed()
        with self.store.connect() as db:
            states = [json.loads(r[0]) for r in db.execute('SELECT state FROM sessions WHERE revision > 0 ORDER BY updated_at DESC')]
        job = st._Job(self.store, None, pause=0)
        job.pass_saves()
        rows = [v[1] for v in job.rows.values()]
        self.assertEqual(st.play_stats(rows), st.play_stats([st.compact(s) for s in states]))

    def test_request_paths_never_read_a_save(self):
        self.seed(3)
        def boom(*a, **k):
            raise AssertionError('a request must not read saves')
        with patch.object(st, 'sample', boom), patch.object(st, 'compact', boom), patch.object(st._Job, 'pass_saves', boom), \
                patch.object(st, 'wake', lambda store, fresh=False: None):
            top = st.get_summary(self.store, 7)
            self.assertTrue(st.get_section(self.store, 'saves')['pending'])     # before the job's first pass
            self.assertTrue(st.get_section(self.store, 'system')['pending'])
            full = st.get(self.store, 30)
        self.assertEqual(top['players']['played'], 3)
        self.assertNotIn('play', top)
        self.assertTrue(full['pending'])
        self.assertEqual(full['play']['sample'], 0)
        self.assertEqual(top['names']['grocery'], st.career_names()['grocery'])
        if not getattr(self.store, 'pg', None):  # SQLite: not one statement of the summary names the save column
            seen = []
            real = sqlite3.connect
            def traced(*a, **k):
                con = real(*a, **k)
                con.set_trace_callback(seen.append)
                return con
            st.clear_cache()
            with patch.object(st.sqlite3, 'connect', traced), patch.object(st, 'wake', lambda store, fresh=False: None):
                st.get_summary(self.store, 90)
            self.assertTrue(seen)
            self.assertFalse([s for s in seen if 'state' in s.replace('statement', '')])

    def test_reads_are_read_only_and_budgeted(self):
        self.seed(1)
        heavy = ("SELECT count(*) FROM generate_series(1, 200000000)" if getattr(self.store, 'pg', None) else
                 "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c LIMIT 200000000) SELECT count(*) FROM c")
        t = time.monotonic()
        with self.assertRaises(st.Busy):
            with st._read(self.store, 100) as db:
                (db.pg(heavy) if getattr(db, 'dialect', '') == 'pg' else db.execute(heavy)).fetchone()
        self.assertLess(time.monotonic() - t, 3)
        with self.assertRaises(Exception):
            with st._read(self.store, 1000) as db:
                db.execute('DELETE FROM stat_active')
        with self.store.connect() as db:
            self.assertGreater(db.execute('SELECT COUNT(*) FROM stat_active').fetchone()[0], 0)

    def test_job_rereads_only_changed_saves_and_remembers_across_restarts(self):
        self.seed(6)
        job = st._Job(self.store, None, pause=0)
        job.pass_saves()
        self.assertEqual((job.out['saves']['sample']['size'], job.out['saves']['sample']['reread']), (6, 6))
        job.pass_saves()
        self.assertEqual(job.out['saves']['sample']['reread'], 0)          # nothing moved
        s = self.store.read(self.tokens[2])[0]
        s['journey']['wallet'] = 123456
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=?, revision=revision+1, updated_at=CURRENT_TIMESTAMP WHERE sid=?',
                       (json.dumps(s, ensure_ascii=False), self.sid(self.tokens[2])))
        job.pass_saves()
        self.assertEqual(job.out['saves']['sample']['reread'], 1)
        self.assertIn(123456, [v[1]['wallet'] for v in job.rows.values()])
        with self.store.connect() as db:
            self.assertEqual({k: job.out['saves'][k] for k in ('play', 'economy')}, {k: st.play_stats(st.sample(db)[0])[k] for k in ('play', 'economy')})
        self.store.delete(self.tokens[3])
        job.pass_saves()
        self.assertEqual((job.out['saves']['sample']['size'], len(job.rows)), (5, 5))
        # A new process (server restart) starts from the rows file: nothing to read again.
        again = st._Job(self.store, None, pause=0)
        again.pass_saves()
        self.assertEqual(again.out['saves']['sample']['reread'], 0)
        self.assertEqual(again.out['saves']['play'], job.out['saves']['play'])

    def test_background_pass_yields_to_players_and_stops_when_the_page_is_closed(self):
        self.seed(3)
        p = st._paths(self.store)
        job = st._Job(self.store, lock_fd=-1, pause=0)   # a background job (lock_fd set)
        st._write_json(p['want'], dict(at=time.time(), fresh=0))
        waits = []
        with patch.object(st, '_load', return_value=5.0), patch.object(st.time, 'sleep', waits.append):
            job.pass_saves()                               # machine busy: waits BUSY_WAIT, then gives up
        self.assertEqual(sum(waits), st.BUSY_WAIT)
        self.assertNotIn('saves', job.out)
        self.assertEqual(job.rows, {})
        st._write_json(p['want'], dict(at=time.time() - st.IDLE - 1, fresh=0))
        with patch.object(st, '_load', return_value=0.0):
            job.pass_saves()                               # nobody on the page any more: nothing is read
        self.assertNotIn('saves', job.out)
        st._write_json(p['want'], dict(at=time.time(), fresh=0))
        with patch.object(st, '_load', return_value=0.0), patch.object(st.time, 'sleep', lambda s: None):
            job.pass_saves()                               # idle machine, operator watching: the pass runs
        self.assertEqual(job.out['saves']['sample']['size'], 3)
        job.lock_fd = None

    def test_a_save_over_the_chunk_budget_is_skipped_not_waited_for(self):
        self.seed(4)
        real = st._Job._chunk
        def slow(job, part):
            if self.sid(self.tokens[1]) in part:
                raise st.Busy('over budget')
            return real(job, part)
        with patch.object(st._Job, '_chunk', slow):
            job = st._Job(self.store, None, pause=0)
            job.pass_saves()
        self.assertEqual((job.out['saves']['sample']['size'], job.out['saves']['sample']['skipped']), (3, 1))

    def test_one_job_per_database_and_it_serves_the_sections(self):
        self.seed(3)
        lock = st._paths(self.store)['lock']
        fd = st._try_lock(lock)
        self.assertIsNotNone(fd)
        self.assertIsNone(st._try_lock(lock))        # a second worker cannot run it too
        st.wake(self.store)                          # this "worker" sees the lock taken: no job here
        self.assertNotIn(self.store.path, st._jobs)
        st._unlock(fd)
        st.wake(self.store)
        self.assertIn(self.store.path, st._jobs)
        for _ in range(250):
            sv = st.get_section(self.store, 'saves')
            if not sv.get('pending'):
                break
            time.sleep(0.02)
        self.assertEqual(sv['play']['sample'], 3)
        for _ in range(250):
            sysd = st.get_section(self.store, 'system')
            if not sysd.get('pending'):
                break
            time.sleep(0.02)
        self.assertIn('sessions', {t['name'] for t in sysd['server']['tables']})
        st.stop_jobs()
        self.assertNotIn(self.store.path, st._jobs)
        fd = st._try_lock(lock)                      # released when the job stopped
        self.assertIsNotNone(fd)
        st._unlock(fd)

    def test_a_slow_disk_gets_the_jobs_copy_of_the_first_screen(self):
        self.seed(3)
        real = st.summary
        live = []
        def slow(store, days, ms=None):
            if ms is None:  # a request's live read: out of time
                live.append(days)
                raise st.Busy('over budget')
            return real(store, days, ms)
        with patch.object(st, 'summary', slow), patch.object(st, 'wake', lambda store, fresh=False: None):
            first = st.get_summary(self.store, 7)
            self.assertEqual((first.get('pending'), first.get('range')), (True, 7))   # nothing computed yet
            self.assertEqual(st.get_summary(self.store, 30).get('pending'), True)
            self.assertEqual(live, [7])            # the second range did not ask the slow disk again
            job = st._Job(self.store, None, pause=0)
            job.pass_summary()
            job.write()
            st.clear_cache()
            top = st.get_summary(self.store, 30)
            self.assertTrue(top['stale'])
            self.assertEqual(top['players'], real(self.store, 30)['players'])
            full = st.get(self.store, 90)
            self.assertEqual(full['players']['played'], 3)
        self.assertEqual({'7', '30', '90'}, set(job.out['summary']))

    def test_concurrent_summaries_share_one_computation(self):
        self.seed(2)
        calls, gate = [], threading.Event()
        real = st.summary
        def slow(store, days):
            calls.append(days)
            gate.wait(3)
            return real(store, days)
        out = []
        with patch.object(st, 'summary', slow), patch.object(st, 'wake', lambda store, fresh=False: None):
            threads = [threading.Thread(target=lambda: out.append(st.get_summary(self.store, 7))) for _ in range(4)]
            for t in threads:
                t.start()
            time.sleep(0.2)
            gate.set()
            for t in threads:
                t.join(10)
        self.assertEqual(calls, [7])
        self.assertEqual(len(out), 4)

    def test_summary_and_sections_carry_no_personal_data(self):
        self.seed(4)
        accounts.register(self.store, self.tokens[2], dict(REG, username='private_user2', display='Hiển Thị Riêng'))
        st.refresh_now(self.store)
        with patch.object(st, 'wake', lambda store, fresh=False: None):
            text = json.dumps([st.get_summary(self.store, 30), st.get_section(self.store, 'saves'), st.get_section(self.store, 'system'),
                               st.get(self.store, 7)], ensure_ascii=False)
        with self.store.connect() as db:
            secrets_ = [r[0] for r in db.execute('SELECT sid FROM sessions')] + [r[0] for r in db.execute('SELECT csrf FROM sessions')]
            secrets_ += [r[0] for r in db.execute('SELECT pw FROM accounts')]
        for value in secrets_ + self.tokens + ['private_user2', 'someone_y', 'Hiển Thị Riêng']:
            self.assertNotIn(value, text)
        for key in ('"sid"', '"token"', '"csrf"', '"pw"', '"password"', '"email"', '"username"', '"account"'):
            self.assertNotIn(key, text)
        if os.name != 'nt':  # the job's files next to the database are private
            self.assertEqual(os.stat(st._paths(self.store)['rows']).st_mode & 0o077, 0)


class CacheTests(Seeded):
    def test_cached_then_refreshed_in_background(self):
        self.save(fresh_player)
        calls = []
        real = st._full
        def counting(store, days):
            calls.append(days)
            return real(store, days)
        with patch.object(st, '_full', counting), patch.object(st, 'wake', lambda store, fresh=False: None):
            first = st.get(self.store, '7')
            self.assertFalse(first['cached'])
            second = st.get(self.store, 7)
            self.assertTrue(second['cached'])
            self.assertEqual(calls, [7])
            st.get(self.store, 30)
            self.assertEqual(calls, [7, 30])
            # fresh=1 only recomputes when the copy is older than 10 s.
            self.assertTrue(st.get(self.store, 7, fresh=True)['cached'])
            key = (self.store.path, 7)
            stamp, data = st._cache[key]
            st._cache[key] = (stamp - 11, data)
            self.assertFalse(st.get(self.store, 7, fresh=True)['cached'])
            self.assertEqual(calls, [7, 30, 7])
            # Past the TTL: the stale copy comes back at once, one thread recomputes.
            stamp, data = st._cache[key]
            st._cache[key] = (stamp - st.TTL - 1, data)
            self.save(fresh_player)
            stale = st.get(self.store, 7)
            self.assertTrue(stale['cached'])
            self.assertEqual(stale['players']['total'], 1)
            for _ in range(200):
                if len(calls) == 4 and key not in st._running:
                    break
                time.sleep(0.02)
            self.assertEqual(len(calls), 4)
            self.assertEqual(st.get(self.store, 7)['players']['total'], 2)

    def test_bad_range(self):
        for bad in ('1', 'x', '365', -7):
            with self.assertRaises(ValueError):
                st.parse_range(bad)
        self.assertEqual(st.parse_range(None), 7)
        with self.assertRaises(ValueError):
            st.get_section(self.store, 'players')


class AICounterTests(unittest.TestCase):
    def setUp(self):
        with st._ai_lock:
            st._ai.clear(); st._blocked.clear()

    def test_wrappers_count_and_pass_through(self):
        answers = iter([('Xin chào', None), (None, 'busy'), (None, 'unavailable'), (None, 'not_configured')])
        chat = st._counted_chat(lambda *a, **k: next(answers))
        self.assertEqual(chat([]), ('Xin chào', None))
        self.assertEqual(chat([])[1], 'busy')
        chat([]); chat([])
        clean = st._counted_clean(lambda text, *a, **k: (None, 'numbers') if 'x' in text else (text, None))
        self.assertEqual(clean('ok'), ('ok', None))
        clean('x')
        abusive = st._counted_abusive(lambda text: 'bậy' in text)
        self.assertTrue(abusive('nói bậy'))
        self.assertTrue(abusive('nói bậy'))        # same message checked twice: counted once
        self.assertFalse(abusive('lịch sự'))
        total = st.ai_usage()['total']
        self.assertEqual(total, dict(calls=3, ok=1, failed=1, busy=1, rejected=1, guard=1))

    def test_install_is_idempotent(self):
        from game import ai
        st.install_ai_counters(); st.install_ai_counters()
        self.assertTrue(ai.chat._counted)
        self.assertFalse(getattr(ai.chat.__wrapped__, '_counted', False))
        self.assertTrue(ai.abusive._counted and ai.clean_reply._counted)


class StatsHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = GameServer(('127.0.0.1', 0), Store(Path(cls.temp.name) / 'state.db'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'op_admin'})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); st.stop_jobs(); cls.server.store.close_pool(); cls.temp.cleanup(); cls.env.stop()
        st.clear_cache()

    def setUp(self):
        self.server.limits.clear()
        st.clear_cache()

    def req(self, dev, path, csrf=True):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if dev.get('cookie'): h['Cookie'] = dev['cookie']
        if csrf and dev.get('csrf'): h['X-Game-CSRF'] = dev['csrf']
        body = None
        method = 'GET'
        if isinstance(path, tuple):
            path, body = path
            method = 'POST'; h['Content-Type'] = 'application/json'; body = json.dumps(body)
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=60)  # a loaded CI machine: the first bootstrap builds the catalogue
        con.request(method, path, body=body, headers=h)
        res = con.getresponse(); data = json.loads(res.read() or b'{}'); hdrs = dict(res.getheaders()); con.close()
        if 'Set-Cookie' in hdrs: dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        if isinstance(data, dict) and data.get('csrf'): dev['csrf'] = data['csrf']
        return res.status, data

    def device(self):
        dev = {}
        self.assertEqual(self.req(dev, '/api/bootstrap')[0], 200)
        return dev

    def signed(self, name):
        dev = self.device()
        status, data = self.req(dev, ('/api/account/register', dict(REG, username=name)))
        self.assertEqual(status, 200, data)
        self.req(dev, '/api/bootstrap')
        return dev

    def test_admin_only(self):
        anon, player = self.device(), self.signed('regular_joe')
        for dev in (anon, player):
            status, data = self.req(dev, '/api/admin/stats')
            self.assertEqual(status, 403)
            self.assertNotIn('players', data)
        self.assertEqual(self.req({}, '/api/admin/stats')[0], 401)
        admin = self.signed('op_admin')
        self.assertEqual(self.req(admin, '/api/admin/stats', csrf=False)[0], 403)   # cookie alone is not enough
        status, data = self.req(admin, '/api/admin/stats?range=30')
        self.assertEqual(status, 200, data)
        self.assertEqual(data['range'], 30)
        self.assertEqual(len(data['players']['dau']), 30)
        self.assertGreaterEqual(data['players']['total'], 3)
        for key in ('play', 'economy', 'life', 'board', 'feedback', 'ai', 'server', 'sample'):
            self.assertIn(key, data)
        self.assertEqual(self.req(admin, '/api/admin/stats?range=365')[0], 400)
        status, again = self.req(admin, '/api/admin/stats?range=30')
        self.assertTrue(again['cached'])
        self.assertNotIn('op_admin', json.dumps(again))
        # Leaving ADMIN_USERS closes it at once, even with a warm cache.
        with patch.dict(os.environ, {'ADMIN_USERS': ''}):
            self.assertEqual(self.req(admin, '/api/admin/stats?range=30')[0], 403)

    def test_summary_and_sections_admin_only(self):
        anon, player = self.device(), self.signed('regular_jane')
        paths = ('/api/admin/stats/summary?range=7', '/api/admin/stats/section?name=saves', '/api/admin/stats/section?name=system')
        for path in paths:
            for dev in (anon, player):
                status, data = self.req(dev, path)
                self.assertEqual(status, 403, path)
                self.assertFalse({'players', 'play', 'server'} & set(data))
            self.assertEqual(self.req({}, path)[0], 401)
        env = patch.dict(os.environ, {'ADMIN_USERS': 'op_admin3'})
        env.start()
        self.addCleanup(env.stop)
        admin = self.signed('op_admin3')
        for path in paths:
            self.assertEqual(self.req(admin, path, csrf=False)[0], 403)   # cookie alone is not enough
        status, top = self.req(admin, '/api/admin/stats/summary?range=30')
        self.assertEqual(status, 200, top)
        self.assertEqual((top['range'], len(top['players']['dau'])), (30, 30))
        for key in ('feedback', 'ai', 'server', 'names'):
            self.assertIn(key, top)
        self.assertFalse({'play', 'economy', 'life', 'board'} & set(top))
        def ready(path):  # the background job answers {pending} until its first pass is done
            for _ in range(25):                     # under the 30/min rate limit
                status, data = self.req(admin, path)
                self.assertEqual(status, 200, data)
                if not data.get('pending'):
                    return data
                self.assertIn('retry_ms', data)
                time.sleep(0.3)
            self.fail('section still pending')
        sv = ready('/api/admin/stats/section?name=saves')
        for key in ('play', 'economy', 'life', 'board', 'sample', 'generated_at'):
            self.assertIn(key, sv)
        sysd = ready('/api/admin/stats/section?name=system')
        self.assertIn('sessions', {t['name'] for t in sysd['server']['tables']})
        self.assertEqual(self.req(admin, '/api/admin/stats/summary?range=365')[0], 400)
        self.assertEqual(self.req(admin, '/api/admin/stats/section?name=secrets')[0], 400)
        self.assertEqual(self.req(admin, '/api/admin/stats/section')[0], 400)
        self.assertNotIn('op_admin3', json.dumps([top, sv, sysd]))
        with patch.dict(os.environ, {'ADMIN_USERS': ''}):
            for path in paths:
                self.assertEqual(self.req(admin, path)[0], 403)

    def test_rate_limited(self):
        admin = self.signed('op_admin2')
        with patch.dict(os.environ, {'ADMIN_USERS': 'op_admin2'}):
            codes = [self.req(admin, '/api/admin/stats')[0] for _ in range(31)]
        self.assertEqual(codes[:30], [200] * 30)
        self.assertEqual(codes[30], 429)


if __name__ == '__main__':
    unittest.main()
