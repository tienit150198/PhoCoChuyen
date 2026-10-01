"""Play time ("Thời gian chơi", game/admin_stats.py): the stat_play trigger on receipts (one
receipt = one game command) on SQLite and PostgreSQL, the one-off backfill from receipts, the
admin section and the purge. Runs on PostgreSQL with TEST_DATABASE_URL (tests/pg_support.py)."""
import datetime, json, random, sqlite3, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch

from game import admin_stats as st
from game import pg_schema
from game.storage import Store

VN = st.VN


def vn_day(offset=0):
    return (datetime.datetime.now(VN).date() + datetime.timedelta(days=offset)).isoformat()


def utc_text(t):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t))


def vn_epoch(day, hh=12, mm=0, ss=0):
    """Unix time of `day` hh:mm:ss in Vietnam."""
    d = datetime.date.fromisoformat(day)
    return int(datetime.datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=VN).timestamp())


class Base(unittest.TestCase):
    def setUp(self):
        st.clear_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        st.ensure(self.store)
        self.n = 0

    def tearDown(self):
        st.stop_jobs()
        st.clear_cache()
        self.store.close_pool()
        self.tmp.cleanup()

    def player(self):
        token, _, _ = self.store.session()
        return token, self.store.key(token)

    def cmd(self, token, rid=None):
        """One real game command (its receipt fires the trigger)."""
        self.n += 1
        rev = self.store.read(token)[1]
        return self.store.command(token, rid or f'req-{self.n:08d}', rev, None, 'settings', dict(lang='en' if self.n % 2 else 'vi'))

    def rows(self, sid=None):
        sql = 'SELECT day, sid, secs, sessions, cmds, first_at, last_at, hours, sess_at, lens FROM stat_play'
        with self.store.connect() as db:
            got = db.execute(sql + (' WHERE sid = ? ORDER BY day' if sid else ' ORDER BY day, sid'), (sid,) if sid else ()).fetchall()
        return [dict(zip(('day', 'sid', 'secs', 'sessions', 'cmds', 'first_at', 'last_at', 'hours', 'sess_at', 'lens'), tuple(r))) for r in got]

    def row(self, sid, day=None):
        got = [r for r in self.rows(sid) if r['day'] == (day or vn_day())]
        self.assertEqual(len(got), 1, got)
        return got[0]

    def earlier(self, sid, secs):
        """As if this save's commands so far had been sent `secs` seconds earlier."""
        with self.store.connect() as db:
            db.execute('UPDATE stat_play SET first_at = first_at - ?, last_at = last_at - ?, sess_at = sess_at - ? WHERE sid = ?',
                       (secs, secs, secs, sid))

    def sql(self, q, args=()):
        with self.store.connect() as db:
            db.execute(q, args)


class TriggerTests(Base):
    def test_first_command_of_the_day_starts_a_session(self):
        tok, sid = self.player()
        t = time.time()
        self.cmd(tok)
        r = self.row(sid)
        self.assertEqual((r['secs'], r['sessions'], r['cmds'], r['lens']), (60, 1, 1, ''))
        self.assertAlmostEqual(r['first_at'], t, delta=5)
        self.assertEqual((r['first_at'], r['sess_at']), (r['last_at'], r['last_at']))
        hour = datetime.datetime.fromtimestamp(r['last_at'], VN).hour
        self.assertEqual(r['hours'], 1 << hour)

    def test_a_gap_under_10_minutes_counts_as_played(self):
        tok, sid = self.player()
        self.cmd(tok)
        self.earlier(sid, 300)
        self.cmd(tok)
        self.earlier(sid, 590)
        self.cmd(tok)
        r = self.row(sid)
        self.assertAlmostEqual(r['secs'], 60 + 300 + 590, delta=2)
        self.assertEqual((r['sessions'], r['cmds'], r['lens']), (1, 3, ''))
        self.assertAlmostEqual(r['last_at'] - r['sess_at'], 890, delta=2)

    def test_a_gap_over_10_minutes_starts_a_new_session(self):
        tok, sid = self.player()
        self.cmd(tok)
        self.earlier(sid, 200)
        self.cmd(tok)                       # session 1: 200 s + the minute after
        self.earlier(sid, 610)
        self.cmd(tok)                       # session 2 starts: +60
        self.earlier(sid, 3600)
        self.cmd(tok)                       # session 3
        r = self.row(sid)
        self.assertAlmostEqual(r['secs'], 260 + 60 + 60, delta=2)
        self.assertEqual((r['sessions'], r['cmds']), (3, 4))
        lens = st._lens(r['lens'])
        self.assertEqual(len(lens), 2)
        self.assertAlmostEqual(lens[0], 260, delta=1)
        self.assertEqual(lens[1], 60)
        self.assertAlmostEqual(r['sess_at'], r['last_at'], delta=0.01)

    def test_the_trigger_follows_the_rule_of_the_backfill(self):
        """Commands at known gaps give the row _play_from computes from their times."""
        gaps = [0, 30, 200, 700, 10, 1000, 599, 5]
        tok, sid = self.player()
        for i, g in enumerate(gaps):
            if i:
                self.earlier(sid, g)
            self.cmd(tok)
        r = self.row(sid)
        ts, t = [], 100000
        for g in gaps:
            t += g
            ts.append(t)
        want = st._play_from(ts)
        self.assertEqual((r['sessions'], r['cmds']), (want['sessions'], want['cmds']))
        self.assertAlmostEqual(r['secs'], want['secs'], delta=len(gaps))
        got_lens = st._lens(r['lens'])
        self.assertEqual(len(got_lens), len(want['lens']))
        for a, b in zip(got_lens, want['lens']):
            self.assertAlmostEqual(a, b, delta=2)

    def test_a_new_day_starts_a_new_row(self):
        tok, sid = self.player()
        self.cmd(tok)
        self.cmd(tok)
        yesterday = vn_day(-1)
        self.sql('UPDATE stat_play SET day = ? WHERE sid = ?', (yesterday, sid))   # those commands were yesterday
        self.cmd(tok)
        old, new = self.row(sid, yesterday), self.row(sid)
        self.assertEqual((old['cmds'], old['secs']), (2, old['secs']))
        self.assertEqual((new['secs'], new['sessions'], new['cmds'], new['lens']), (60, 1, 1, ''))

    def test_a_retried_request_is_counted_once(self):
        tok, sid = self.player()
        first = self.cmd(tok, 'retry-000001')
        again = self.store.command(tok, 'retry-000001', 0, None, 'settings', dict(lang='en'))   # the client retries
        self.assertTrue(again['replayed'])
        self.assertEqual(self.row(sid)['cmds'], 1)
        # A retry racing the first write: its receipt insert fails, the whole write (and the trigger's) rolls back.
        with self.store.connect() as db:
            text = db.execute('SELECT state FROM sessions WHERE sid = ?', (sid,)).fetchone()[0]
        self.assertFalse(self.store._store(sid, first['revision'], text, 'retry-000001', 'x', '{}'))
        r = self.row(sid)
        self.assertEqual((r['cmds'], r['secs']), (1, 60))
        self.assertEqual(self.store.read(tok)[1], first['revision'])

    def test_deleting_a_save_drops_its_rows_and_pruning_receipts_keeps_them(self):
        tok, sid = self.player()
        other, osid = self.player()
        self.cmd(tok)
        self.cmd(other)
        self.store.prune_receipts(0, 0)    # receipts go, play time stays
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM receipts WHERE sid IN (?, ?)', (sid, osid)).fetchone()[0], 0)
        self.assertEqual(len(self.rows(sid)), 1)
        self.store.delete(tok)
        self.assertEqual(self.rows(sid), [])
        self.assertEqual(len(self.rows(osid)), 1)

    def test_schema_is_idempotent_and_matches_on_both_backends(self):
        st.ensure(self.store)
        if self.store.pg:
            with self.store.connect() as db:
                self.assertTrue(pg_schema.ensure(db, force=True))
                names = {r[0] for r in db.execute("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")}
                self.assertEqual(pg_schema.installed_version(db), pg_schema.SCHEMA_VERSION)
        else:
            with self.store.connect() as db:
                names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
        self.assertTrue({'stat_play_cmd', 'stat_play_gone'} <= names)
        self.assertIn(('receipts', 'stat_play_cmd'), pg_schema.TRIGGERS)
        cols = [c for c, _ in pg_schema.TABLE['stat_play']['columns']]
        self.assertEqual(cols[:7], ['day', 'sid', 'secs', 'sessions', 'cmds', 'first_at', 'last_at'])
        self.assertEqual(self.rows(), [])


class BackfillTests(Base):
    """Receipts written before the trigger existed: inserted by hand, then the rows the trigger
    made for them removed (stat_play is derived; receipts stay as they are)."""
    NOW_DAY = '2026-09-30'

    def setUp(self):
        super().setUp()
        self.now = vn_epoch(self.NOW_DAY, 18, 0)
        self.yday = '2026-09-29'

    def receipts(self, sid, times):
        with self.store.connect() as db:
            for t in times:
                self.n += 1
                db.execute('INSERT INTO receipts(sid, request_id, request_hash, result, created_at) VALUES (?, ?, ?, ?, ?)',
                           (sid, f'old-{self.n:08d}', 'h', '{}', utc_text(t)))
            for day in {st._vn_day(t) for t in times}:
                db.execute('INSERT OR IGNORE INTO stat_active(day, sid) VALUES (?, ?)', (day, sid))

    def untracked(self):
        self.sql('DELETE FROM stat_play')

    def tracked_row(self, sid, day, ts):
        """The row the trigger would hold for commands at `ts` (sorted)."""
        r = st._play_from(ts)
        self.sql('INSERT INTO stat_play(day, sid, secs, sessions, cmds, first_at, last_at, hours, sess_at, lens) VALUES (?,?,?,?,?,?,?,?,?,?)',
                 (day, sid, r['secs'], r['sessions'], r['cmds'], r['first_at'], r['last_at'], r['hours'], r['sess_at'],
                  ''.join(f'{x},' for x in r['lens'])))

    def receipt_count(self):
        with self.store.connect() as db:
            return db.execute('SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM receipts').fetchone()

    def test_seeds_untracked_days_and_joins_tracked_rows(self):
        a, b, c = (self.player()[1] for _ in range(3))
        base = vn_epoch(self.NOW_DAY, 10)
        a_old = [base, base + 100, base + 200, base + 1500]              # two sessions before tracking
        b_old = [base + 3000, base + 3100]                              # ... joined to the tracked one (gap 300)
        c_yday = [vn_epoch(self.yday, 21), vn_epoch(self.yday, 21, 5)]  # yesterday only
        stale = [vn_epoch('2026-09-28', 23, 30)]                         # the day before: partial, left alone
        self.receipts(a, a_old)
        self.receipts(b, b_old)
        self.receipts(c, c_yday + stale)
        self.untracked()
        a_new, b_new = [base + 4000, base + 4030], [base + 3400, base + 3500, base + 5000]
        self.receipts(a, a_new)
        self.receipts(b, b_new)
        self.untracked()
        self.tracked_row(a, self.NOW_DAY, a_new)
        self.tracked_row(b, self.NOW_DAY, b_new)
        before = self.receipt_count()
        out = st.backfill_play(self.store, days=2, now=self.now, pause=0)
        self.assertEqual(self.receipt_count(), before)            # receipts are only read
        self.assertEqual((out['merged'], out['inserted'], out['capped']), (2, 1, 0))
        self.assertEqual(out['per_day'], {self.yday: dict(saves=1, capped=0), self.NOW_DAY: dict(saves=2, capped=0)})
        # Merged rows equal what the trigger would have counted from the start.
        for sid, ts in ((a, a_old + a_new), (b, b_old + b_new)):
            want, got = st._play_from(ts), self.row(sid, self.NOW_DAY)
            self.assertEqual((got['secs'], got['sessions'], got['cmds'], got['first_at'], got['hours']),
                             (want['secs'], want['sessions'], want['cmds'], want['first_at'], want['hours']), sid)
            self.assertEqual((st._lens(got['lens']), got['sess_at'], got['last_at']), (want['lens'], want['sess_at'], want['last_at']))
        self.assertEqual(self.row(b, self.NOW_DAY)['sessions'], 2)
        want = st._play_from(c_yday)
        got = self.row(c, self.yday)
        self.assertEqual((got['secs'], got['sessions'], got['cmds']), (want['secs'], 1, 2))
        self.assertEqual([r['day'] for r in self.rows(c)], [self.yday])
        with self.store.connect() as db:
            est = {r[0]: (r[1], r[2]) for r in db.execute('SELECT day, saves, capped FROM stat_play_est')}
        self.assertEqual(est, {self.yday: (1, 0), self.NOW_DAY: (2, 0)})
        # Idempotent: a second run adds nothing.
        snapshot = self.rows()
        again = st.backfill_play(self.store, days=2, now=self.now, pause=0)
        self.assertEqual((again['merged'], again['inserted']), (0, 0))
        self.assertEqual(again['covered'], 3)
        self.assertEqual(self.rows(), snapshot)
        with self.store.connect() as db:
            self.assertEqual({r[0]: (r[1], r[2]) for r in db.execute('SELECT day, saves, capped FROM stat_play_est')}, est)

    def test_dry_run_writes_nothing_and_capped_saves_are_counted(self):
        a = self.player()[1]
        base = vn_epoch(self.NOW_DAY, 9)
        self.receipts(a, [base + 20 * i for i in range(6)])
        self.untracked()
        dry = st.backfill_play(self.store, now=self.now, pause=0, dry_run=True, cap=5)
        self.assertEqual((dry['inserted'], dry['capped']), (1, 1))
        self.assertEqual(self.rows(), [])
        out = st.backfill_play(self.store, now=self.now, pause=0, cap=5, batch=1)
        self.assertEqual((out['inserted'], out['per_day'][self.NOW_DAY]), (1, dict(saves=1, capped=1)))
        self.assertEqual(self.row(a, self.NOW_DAY)['secs'], 100 + 60)

    def test_merge_equals_counting_from_the_start(self):
        rnd = random.Random(7)
        for _ in range(300):
            ts, t = [], 1_000_000
            for _ in range(rnd.randint(2, 12)):
                t += rnd.choice((0, 5, 60, 400, 599, 600, 601, 900, 4000))
                ts.append(t)
            k = rnd.randint(1, len(ts) - 1)
            if ts[k] == ts[k - 1]:
                continue
            tail = st._play_from(ts[k:])
            row = dict(tail, lens=''.join(f'{x},' for x in tail['lens']))
            m, want = st._play_merge(st._play_from(ts[:k]), row), st._play_from(ts)
            self.assertEqual((m['secs'], m['sessions'], m['cmds'], m['first_at'], m['hours'], m['sess_at'], st._lens(m['lens'])),
                             (want['secs'], want['sessions'], want['cmds'], want['first_at'], want['hours'], want['sess_at'], want['lens']), ts)


class SectionTests(Base):
    def put(self, day, sid, secs, sessions=1, lens=(), hours=(20,), cmds=None, first=None):
        first = first if first is not None else vn_epoch(day, 20)
        last_len = secs - sum(lens)
        self.sql('INSERT INTO stat_play(day, sid, secs, sessions, cmds, first_at, last_at, hours, sess_at, lens) VALUES (?,?,?,?,?,?,?,?,?,?)',
                 (day, sid, secs, sessions, cmds or sessions * 3, first, first + 5000, sum(1 << h for h in hours),
                  first + 5000 - (last_len - 60), ''.join(f'{x},' for x in lens)))

    def seed(self):
        today, yday, old = vn_day(), vn_day(-1), vn_day(-5)
        # today: 4 players, 1, 3, 8 and 70.5 minutes (the last in two sessions: 40 and 30.5 min)
        self.put(today, 'secret-a', 60)
        self.put(today, 'secret-b', 180)
        self.put(today, 'secret-c', 480)
        self.put(today, 'secret-d', 4230, sessions=2, lens=(2400,), hours=(9, 20))
        for sid in ('secret-c', 'secret-d', 'secret-z'):   # z opened the page and never played
            self.sql('INSERT INTO stat_births(sid, day) VALUES (?, ?)', (sid, today))
        # yesterday (seeded by the backfill: estimated) and 5 days ago (the first tracked day)
        self.put(yday, 'secret-a', 600, hours=(8,))
        self.put(yday, 'secret-b', 1200, hours=(8, 9))
        self.put(old, 'secret-a', 300, hours=(8,))
        self.sql('INSERT INTO stat_play_est(day, saves, capped, at) VALUES (?, ?, ?, ?)', (yday, 2, 1, 123.0))
        return today, yday, old

    def test_periods_distribution_hours_and_first_day(self):
        today, yday, old = self.seed()
        out = st.playtime(self.store)
        by = {p['key']: p for p in out['periods']}
        t = by['today']
        total = 60 + 180 + 480 + 4230
        self.assertEqual((t['player_days'], t['players'], t['sessions'], t['hours']), (4, 4.0, 5, round(total / 3600, 1)))
        self.assertEqual((t['avg_min'], t['median_min']), (round(total / 4 / 60, 1), 5.5))
        self.assertEqual((t['session_avg_min'], t['sessions_per_player']), (round(total / 5 / 60, 1), 1.25))
        self.assertEqual(t['session_median_min'], 8.0)             # sessions of 1, 3, 8, 30.5 and 40 min
        self.assertEqual([b['n'] for b in t['bands']], [2, 1, 0, 0, 1])
        self.assertEqual(t['bands'][0]['pct'], 50.0)
        self.assertEqual(t['new'], dict(n=2, avg_min=round(2355 / 60, 1), median_min=round(2355 / 60, 1), over_pct=50.0))
        self.assertTrue(t['exact'])
        self.assertEqual((t['estimated'], t['partial']), ([], False))
        y = by['yesterday']
        self.assertEqual((y['player_days'], y['avg_min'], y['estimated'], y['exact']), (2, 15.0, [yday], False))
        w = by['d7']
        self.assertEqual((w['days'], w['tracked'], w['player_days'], w['partial'], w['estimated']), (7, 6, 7, True, [yday]))
        self.assertEqual(w['players'], round(7 / 6, 1))
        self.assertEqual((by['d30']['player_days'], by['d30']['tracked']), (7, 6))
        # Hours: the finished days of the last week since tracking began (5 days ago .. yesterday).
        self.assertEqual(out['hours']['days'], 5)
        self.assertEqual((out['hours']['avg'][8], out['hours']['avg'][9], out['hours']['avg'][20]), (0.6, 0.2, 0))
        self.assertEqual((out['since']['day'], out['since']['estimated']), (old, False))
        self.assertEqual(out['estimated'], [dict(day=yday, saves=2, capped=1)])
        self.assertNotIn('secret-', json.dumps(out))              # aggregates only

    def test_empty_database(self):
        out = st.playtime(self.store)
        self.assertEqual(out['since']['day'], None)
        t = out['periods'][0]
        self.assertEqual((t['player_days'], t['avg_min'], t['median_min'], t['tracked']), (0, None, None, 0))
        self.assertEqual(out['hours']['avg'], [0] * 24)

    def test_finished_days_are_read_once_and_again_after_the_backfill(self):
        self.seed()
        calls = []
        real = st.play_day
        with patch.object(st, 'play_day', lambda db, day: calls.append(day) or real(db, day)):
            st.playtime(self.store)
            first = list(calls)
            calls.clear()
            st.playtime(self.store)
            self.assertEqual(calls, [vn_day()])                   # only today again
            self.sql('UPDATE stat_play_est SET at = 456.0')       # the backfill ran again on yesterday
            calls.clear()
            st.playtime(self.store)
            self.assertEqual(sorted(calls), sorted([vn_day(-1), vn_day()]))
        self.assertEqual(len(first), 6)                           # 5 days ago .. today
        self.assertLessEqual(len(st._play_days), st.PLAY_DAYS_KEPT)

    def test_request_reads_only_the_stat_tables_and_is_cached(self):
        self.seed()
        if not self.store.pg:
            seen = []
            real = sqlite3.connect
            def traced(*a, **k):
                con = real(*a, **k)
                con.set_trace_callback(seen.append)
                return con
            with patch.object(st.sqlite3, 'connect', traced):
                st.get_section(self.store, 'playtime')
            self.assertTrue(seen)
            self.assertFalse([q for q in seen if 'sessions' in q.replace('sessions,', '').replace('sessions FROM', '')], seen)
            self.assertFalse([q for q in seen if 'receipts' in q])
        st.clear_cache()
        a = st.get_section(self.store, 'playtime')
        b = st.get_section(self.store, 'playtime')
        self.assertFalse(a['cached'])
        self.assertTrue(b['cached'])
        self.assertNotIn(self.store.path, st._jobs)             # never wakes the save job
        with patch.object(st, 'playtime', side_effect=st.Busy('over PLAY_MS')):
            st.clear_cache()
            self.assertEqual(st.get_section(self.store, 'playtime').get('pending'), True)

    def test_quantile_of_the_histogram(self):
        h = st._hist()
        for s in (60, 120, 600):
            h[st._bucket(s)] += 1
        self.assertEqual(st._quantile(h, .5), 120)
        h = st._hist()
        for s in (60, 180):
            h[st._bucket(s)] += 1
        self.assertEqual(st._quantile(h, .5), 120)
        h = st._hist()
        h[st._bucket(5000)] += 1
        self.assertAlmostEqual(st._quantile(h, .5), 5000, delta=30)
        self.assertIsNone(st._quantile(st._hist(), .5))
        self.assertEqual([st._bucket(x) for x in (0, 599, 600, 3599, 3600, 14399, 14400, 10 ** 7)], [0, 599, 600, 899, 900, 1079, 1080, 1199])

    def test_purge_keeps_play_days_and_rolls_the_older_ones_up(self):
        keep = st.PLAY_KEEP_DAYS
        self.assertEqual(keep, 60)
        self.put(vn_day(-keep - 1), 'old', 60)
        self.put(vn_day(-keep - 1), 'old2', 120)
        self.put(vn_day(-keep + 1), 'kept', 60)
        self.sql('INSERT INTO stat_play_est(day, saves, capped, at) VALUES (?, 1, 0, 1.0)', (vn_day(-keep - 1),))
        from game import retention
        with patch.object(st, 'PURGE_ROWS', 1), patch.object(retention, '_peak', lambda now: False):
            st._Job(self.store, None, pause=0).purge()
        self.assertEqual([r['sid'] for r in self.rows()], ['kept'])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM stat_play_est').fetchone()[0], 0)
            day, players, secs, data = db.execute('SELECT day, players, secs, data FROM stat_play_daily').fetchone()
        # The purged day survives as one summary row (kept forever), with its histograms.
        self.assertEqual((day, players, secs), (vn_day(-keep - 1), 2, 180))
        self.assertEqual(sum(json.loads(data)['per_player'].values()), 2)

    def test_purge_waits_out_the_peak_hours(self):
        self.put(vn_day(-st.PLAY_KEEP_DAYS - 5), 'old', 60)
        from game import retention
        with patch.object(retention, '_peak', lambda now: True):
            self.assertEqual(st.upkeep(self.store).get('skipped'), 'peak')
        self.assertEqual([r['sid'] for r in self.rows()], ['old'])


if __name__ == '__main__':
    unittest.main()
