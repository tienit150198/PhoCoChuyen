"""📊 Tổng quan đầu tư (game/kpi.py, game/admin_kpi.py) and the fixes to the older admin numbers it relies on:
the never-played migrated saves, new players of a day, VN-day feedback windows, D30 cohorts, the AI counters of
every worker, the frozen daily numbers (survivorship), counters, the CSV export (small cells hidden, no personal
data) and the admin-only route. Runs on PostgreSQL with TEST_DATABASE_URL (tests/pg_support.py)."""
import csv, datetime, http.client, io, json, os, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch

from game import admin_kpi as ak
from game import admin_retention as ar
from game import admin_stats as st
from game import kpi
from game import retention as rt
from game import storage as storage_mod
from game.storage import Store
from server import GameServer

VN = kpi.VN
SECRET = 'Tên Riêng Bí Mật'
REG = dict(password='matkhau-rat-dai', confirm='matkhau-rat-dai', display='Người Thử')


def day(offset=0, now=None):
    return (datetime.datetime.fromtimestamp(time.time() if now is None else now, VN).date() + datetime.timedelta(days=offset)).isoformat()


def utc_text(t):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t))


class Base(unittest.TestCase):
    def setUp(self):
        st.clear_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        st.ensure(self.store)

    def tearDown(self):
        kpi.flush(self.store)
        rt.flush(self.store)
        st.stop_jobs()
        st.clear_cache()
        self.store.close_pool()
        self.tmp.cleanup()

    def sql(self, sql, args=()):
        with self.store.connect() as db:
            db.execute(sql, args)

    def q(self, sql, args=()):
        with self.store.connect() as db:
            return [tuple(r) for r in db.execute(sql, args).fetchall()]

    def born(self, sid, born, active=(), revision=1, updated=None):
        """A save created on Vietnam day `born` and active on the days `active` (the trigger rows, set by hand)."""
        self.sql('INSERT INTO sessions(sid, csrf, state, revision) VALUES (?, ?, ?, ?)', (sid, 'c', '{}', revision))
        self.sql('UPDATE stat_births SET day = ? WHERE sid = ?', (born, sid))
        self.sql('DELETE FROM stat_active WHERE sid = ?', (sid,))
        for d in active:
            self.sql('INSERT INTO stat_active(day, sid) VALUES (?, ?)', (d, sid))
        if updated is not None:
            self.sql('UPDATE sessions SET updated_at = ? WHERE sid = ?', (utc_text(updated), sid))
            self.sql('DELETE FROM stat_active WHERE sid = ?', (sid,))
            for d in active:
                self.sql('INSERT INTO stat_active(day, sid) VALUES (?, ?)', (d, sid))

    def players(self, days=7):
        with st._read(self.store, 10000) as db:
            return st.players(db, days, datetime.datetime.now(VN).date())


# ---------------------------------------------------------------- bugs of the older numbers
class PlayedTests(Base):
    def test_migrated_never_played_save_is_not_a_player_nor_active(self):
        """Bug: reading a save after a release that adds a career migrates it and bumps its revision without a
        command (no updated_at change, no stat_active row): it counted as "Đã chơi", as a guest who played, and,
        through the saves' last change, as active (DAU/WAU/MAU) on the day it was created."""
        self.born('real', day(0), [day(0)])
        self.born('ghost', day(0), [], revision=0)
        self.sql('UPDATE sessions SET revision = revision + 1 WHERE sid = ?', ('ghost',))   # what migrate-on-read does
        p = self.players()
        self.assertEqual((p['total'], p['played'], p['guests'], p['unplayed_migrated']), (2, 1, 1, 1))
        self.assertEqual((p['dau'][-1], p['wau'], p['mau']), (1, 1, 1))

    def test_legacy_saves_from_before_the_day_log_still_count(self):
        """A save older than the day log (no stat_births row) keeps the old rule: revision > 0 means played, and
        its last change fills the days before the log."""
        self.born('real', day(0), [day(0)])
        self.born('old', day(0), [], revision=3, updated=time.time() - 20 * 86400)
        self.sql('DELETE FROM stat_births WHERE sid = ?', ('old',))
        p = self.players(30)
        self.assertEqual(p['played'], 2)
        self.assertEqual(p['tracked_since'], day(0))
        # Its last change (20 days ago) lies before the log began (today): it is an active day.
        self.assertEqual(p['mau'], 2)
        self.assertEqual(p['dau'][-21], 1)

    def test_last_change_after_the_log_began_is_not_reused(self):
        self.born('first', day(-5), [day(-5)])          # the log begins 5 days ago
        self.born('ghost', day(-2), [], revision=2, updated=time.time() - 2 * 86400)
        p = self.players(7)
        self.assertEqual(p['dau'][-3], 0)                # its creation day is not an active day
        self.assertEqual(p['played'], 1)

    def test_new_players_of_a_day_are_those_who_played_that_day(self):
        """Bug: a save created on day X that first played on day X+3 was added to day X afterwards (the number
        of an old day grew), unlike the retention cohort."""
        self.born('same', day(-3), [day(-3)])
        self.born('late', day(-3), [day(0)])
        p = self.players(7)
        self.assertEqual(p['new_players'][-4], 1)
        self.assertEqual(p['new_sessions'][-4], 2)

    def test_churn_ignores_saves_without_a_command(self):
        now = time.time()
        self.born('gone', day(-10), [day(-10)], updated=now - 5 * 86400)
        self.born('ghost', day(-10), [], updated=now - 5 * 86400)
        with st._read(self.store, 10000) as db:
            c = ar.churn(db, now, datetime.datetime.now(VN).date())
        self.assertEqual(c['players'], 1)


class CohortTests(Base):
    def test_d30_and_d14_are_computed(self):
        """Bug: with 30 listed start days a D30 (day + 30 < today) could never be ready."""
        d = day(-40)
        for i in range(10):
            back = [d] + ([day(-26)] if i < 4 else []) + ([day(-10)] if i < 2 else [])
            self.born(f'c{i}', d, back)
        with st._read(self.store, 10000) as db:
            rows = ar.cohorts(self.store, db, datetime.datetime.now(VN).date())
        self.assertEqual(len(rows), ar.COHORT_DAYS)
        r = next(x for x in rows if x['day'] == d)
        self.assertEqual((r['n'], r['d14'], r['d30']), (10, 40.0, 20.0))
        s = ar.cohort_summary(rows)
        self.assertEqual((s['d30'], s['d30_n']), (20.0, 10))

    def test_d1_label_counts_only_ready_cohorts(self):
        self.born('a', day(-2), [day(-2), day(-1)])
        self.born('b', day(0), [day(0)])                 # today's player: no D1 yet
        r = self.players()['retention']
        self.assertEqual((r['cohort'], r['d1_n'], r['d1']), (2, 1, 100.0))


class FeedbackTests(Base):
    def note(self, at, status='new', acked=None):
        with self.store.connect() as db:
            db.execute('INSERT INTO player_feedback(sid, kind, text, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                       ('s', 'bug', 'x', status, at, acked or at))
            if acked:
                nid = db.execute('SELECT MAX(id) FROM player_feedback').fetchone()[0]
                db.execute('INSERT INTO stat_fb_ack(id, at) VALUES (?, ?)', (nid, acked))

    def test_range_starts_at_vietnam_midnight(self):
        """Bug: "7 ngày" meant now − 7×24 h, so the count changed with the hour and disagreed with the other cards
        (Vietnam days)."""
        now = datetime.datetime(2026, 10, 2, 12, 0, tzinfo=VN).timestamp()
        start = datetime.datetime(2026, 9, 26, 0, 0, tzinfo=VN).timestamp()
        self.note(start - 3600)          # 25/09 23:00: inside "now − 7 days", outside the 7 Vietnam days
        self.note(start + 60)            # 26/09 00:01
        with st._read(self.store, 10000) as db:
            f = st.feedback(db, 7, now)
        self.assertEqual(f['in_range'], 1)

    def test_waiting_notes_are_not_hidden_by_the_median(self):
        now = time.time()
        self.note(now - 3 * 3600, status='seen', acked=now - 2 * 3600)   # read after 1 h
        self.note(now - 50 * 3600)                                       # still waiting, 50 h
        with st._read(self.store, 10000) as db:
            a = st.feedback(db, 7, now)['ack']
        self.assertEqual((a['n'], a['median_h'], a['waiting'], a['read_pct']), (1, 1.0, 1, 50.0))
        self.assertAlmostEqual(a['oldest_wait_h'], 50.0, delta=0.1)


class AiCounterTests(Base):
    def test_every_worker_counts_and_survives_a_restart(self):
        """Bug: the AI counters lived in each worker's memory: with WORKERS=8 the page showed one worker's calls,
        and a restart reset them."""
        st.install_ai_counters(self.store)
        self.addCleanup(st.install_ai_counters, None)
        for _ in range(3):
            st._bump('calls')
        kpi.add(self.store, 'ai:calls', 5)          # another worker's calls, written by it
        kpi.flush(self.store)
        with st._ai_lock:
            st._ai.clear()                           # a restart: this worker's memory is gone
        st._ai_read.clear()
        u = st.ai_usage(self.store)
        self.assertTrue(u['persisted'])
        self.assertEqual(u['total']['calls'], 8)


# ---------------------------------------------------------------- counters
class CounterTests(Base):
    def test_sums_maxima_and_bad_keys(self):
        t = time.time()
        kpi.add(self.store, 'http:2xx', 2, t)
        kpi.add(self.store, 'http:2xx', 3, t)
        kpi.add(self.store, 'Bad Key!', 1, t)
        kpi.add(self.store, 'max:cheat', 99, t)     # a max: key only through peak()
        kpi.peak(self.store, 'online5m', 4, t)
        kpi.peak(self.store, 'online5m', 2, t)
        self.assertEqual(kpi.pending(self.store)[(day(0, t), 'http:2xx')], 5)
        kpi.flush(self.store)
        kpi.add(self.store, 'http:2xx', 1, t)
        kpi.peak(self.store, 'online5m', 3, t)       # lower than the stored 4: kept 4
        kpi.flush(self.store)
        with self.store.connect() as db:
            got = kpi.read(db, day(-1, t))[day(0, t)]
        self.assertEqual(got, {'http:2xx': 6, 'max:online5m': 4})

    def test_vietnam_midnight_splits_days(self):
        midnight = datetime.datetime(2026, 10, 2, 0, 0, tzinfo=VN).timestamp()
        kpi.add(self.store, 'up_min', 1, midnight - 1)
        kpi.add(self.store, 'up_min', 1, midnight)
        kpi.flush(self.store)
        with self.store.connect() as db:
            got = kpi.read(db, '2026-09-30', 'up_min')
        self.assertEqual((got['2026-10-01']['up_min'], got['2026-10-02']['up_min']), (1, 1))

    def test_devices_and_bots(self):
        ua = {'iphone': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit Version/17.0 Mobile/15E148 Safari/604.1',
              'zalo': 'Mozilla/5.0 (Linux; Android 13; SM-A515F) AppleWebKit Chrome/120 Mobile Safari/537.36 Zalo android/12',
              'win': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit Chrome/120 Safari/537.36 Edg/120',
              'bot': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
        self.assertEqual(kpi.device(ua['iphone']), dict(os='ios', form='mobile', browser='safari', bot=False))
        self.assertEqual(kpi.device(ua['zalo']), dict(os='android', form='mobile', browser='zalo', bot=False))
        self.assertEqual(kpi.device(ua['win']), dict(os='windows', form='desktop', browser='edge', bot=False))
        self.assertTrue(kpi.device(ua['bot'])['bot'])
        t = time.time()
        kpi.count_session(self.store, ua['zalo'], 'vi-VN,vi;q=0.9', t)
        kpi.count_session(self.store, ua['bot'], '', t)
        p = {k: v for (d, k), v in kpi.pending(self.store).items()}
        self.assertEqual((p['dev_os:android'], p['dev_br:zalo'], p['lang:vi'], p['dev_bot']), (1, 1, 1, 1))
        self.assertNotIn('dev_os:other', p)          # a bot is counted apart, not as a device

    def test_command_counts_xu_created_and_destroyed(self):
        """Wiring: a stored command adds its change of the xu held (wallet + funds + bank) to xu_in / xu_out of its
        action; a rejected or replayed one adds nothing."""
        token = self.store.session()[0]
        real = storage_mod.apply_action

        def fake(raw, career, action, payload, **kw):
            raw, result = real(raw, career, 'jr_seen', {}, **kw) if False else (raw, dict(message='ok'))
            raw['journey']['wallet'] += 50 if action == 'earn' else -20
            return raw, result
        with patch.object(storage_mod, 'apply_action', fake):
            rev = self.store.read(token)[1]
            self.store.command(token, 'req-earn-0001', rev, None, 'earn', {})
            self.store.command(token, 'req-earn-0001', rev, None, 'earn', {})          # replayed: not again
            self.store.command(token, 'req-spend-001', rev + 1, None, 'spend', {})
        p = {k: v for (d, k), v in kpi.pending(self.store).items()}
        self.assertEqual((p.get('xu_in:earn'), p.get('xu_out:spend')), (50, 20))

    def test_xu_includes_the_bank(self):
        s = dict(journey=dict(wallet=100, bank=dict(balance=40, demand=10, terms=[dict(amount=5)])), careers=dict(a=dict(money=7)))
        self.assertEqual(kpi.xu(s), 162)
        self.assertIsNone(kpi.xu(None))

    def test_sample_minute_records_peaks_once_a_minute(self):
        self.born('a', day(0), [day(0)])
        now = time.time()
        self.assertIsNotNone(kpi.sample_minute(self.store, now))
        self.assertIsNone(kpi.sample_minute(self.store, now))          # same minute
        p = {k: v for (d, k), v in kpi.pending(self.store).items()}
        self.assertEqual((p['max:online5m'], p['up_min']), (1, 1))


# ---------------------------------------------------------------- frozen days
class FreezeTests(Base):
    def seed(self):
        d3, d2 = day(-3), day(-2)
        for i in range(6):
            self.born(f'p{i}', d3, [d3] + ([d2] if i < 3 else []))
        self.born('late', d2, [d2])
        self.born('old', day(-20), [day(-20), d2])            # back after 18 days

    def test_freeze_is_correct_idempotent_and_survives_deletion(self):
        self.seed()
        out = kpi.freeze(self.store, pause=0)
        self.assertGreaterEqual(out['days'], 3)
        self.assertEqual(kpi.freeze(self.store, pause=0)['days'], 0)    # nothing new
        with self.store.connect() as db:
            f = kpi.frozen(db, day(-21))
        self.assertEqual((f[day(-3)]['dau'], f[day(-3)]['new_players'], f[day(-3)]['new_sessions']), (6, 6, 6))
        self.assertEqual((f[day(-2)]['dau'], f[day(-2)]['new_players'], f[day(-2)]['resurrected']), (5, 1, 1))
        self.assertEqual(f[day(-3)]['ret_d1'], 3)
        # A deleted save leaves the past alone (no survivorship): the frozen days do not move.
        token_sid = 'p0'
        with self.store.connect() as db:
            rt.forget(db, token_sid)
            db.execute('DELETE FROM sessions WHERE sid = ?', (token_sid,))
        with self.store.connect() as db:
            f2 = kpi.frozen(db, day(-21))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM stat_players WHERE sid = ?', ('p0',)).fetchone()[0], 1)   # kept forever
        self.assertEqual(f2[day(-3)]['dau'], 6)

    def test_players_table_and_lifetime(self):
        self.seed()
        kpi.freeze(self.store, pause=0)
        rows = dict((r[0], r[1:]) for r in self.q('SELECT sid, first_day, last_day, days FROM stat_players'))
        self.assertEqual(rows['p0'], (day(-3), day(-2), 2))
        self.assertEqual(rows['old'], (day(-20), day(-2), 2))
        self.assertEqual(rows['p5'], (day(-3), day(-3), 1))

    def test_a_day_is_frozen_only_after_its_midnight_plus_margin(self):
        midnight = datetime.datetime.combine(datetime.datetime.now(VN).date(), datetime.time(), VN).timestamp()
        self.born('a', day(-1), [day(-1)])
        kpi.freeze(self.store, now=midnight + 60, pause=0)                  # 00:01: yesterday's buffers may still be in memory
        self.assertEqual(self.q("SELECT COUNT(*) FROM stat_kpi_daily WHERE day = ? AND key = '_done'", (day(-1),))[0][0], 0)
        kpi.freeze(self.store, now=midnight + kpi.FREEZE_AFTER + 60, pause=0)
        self.assertEqual(self.q("SELECT COUNT(*) FROM stat_kpi_daily WHERE day = ? AND key = '_done'", (day(-1),))[0][0], 1)

    def test_weeks_growth_accounting(self):
        today = datetime.datetime.now(VN).date()
        mon = today - datetime.timedelta(days=today.weekday() + 14)     # Monday two weeks ago (a finished week, and the one after)
        w1 = [(mon + datetime.timedelta(days=i)).isoformat() for i in range(7)]
        w2 = [(mon + datetime.timedelta(days=7 + i)).isoformat() for i in range(7)]
        self.born('stay', w1[0], [w1[0], w2[3]])
        self.born('leave', w1[1], [w1[1]])
        self.born('new', w2[2], [w2[2]])
        kpi.freeze(self.store, pause=0)
        with self.store.connect() as db:
            f = kpi.frozen(db, w1[0])
        wk = f[w2[0]]
        self.assertEqual((wk['wk_active'], wk['wk_prev'], wk['wk_retained'], wk['wk_new'], wk['wk_churned'], wk['wk_back']), (2, 2, 1, 1, 1, 0))
        self.assertEqual(f[w1[0]]['wk_partial'], 1)                     # the week before the first is not in the history

    def test_features_of_a_day(self):
        d = day(-2)
        self.born('a', d, [d])
        self.born('b', d, [d])
        with self.store.connect() as db:
            for sid, action in (('a', 'jr_bk_deposit'), ('a', 'serve'), ('b', 'serve'), ('b', 'bd_post')):
                db.execute('INSERT INTO stat_actions(day, sid, career, action, n) VALUES (?, ?, ?, ?, 1)', (d, rt.short(sid), 'milk_tea', action))
            got = kpi.features_day(db, d)
        self.assertEqual((got['feat:bank'], got['feat:work'], got['feat:board'], got['feat:fair']), (1, 2, 1, 0))

    def test_stats_kept_forever_and_outlive_the_save(self):
        """Owner, 02/10: player statistics are never lost. No time limit, and a deleted save keeps its stat rows."""
        self.assertEqual((st.KEEP_DAYS, st.PLAY_KEEP_DAYS), (0, 0))
        old = day(-400)
        self.born('x', old, [old])
        st.upkeep(self.store, force=True)
        st.upkeep(self.store, force=True)
        self.assertEqual(self.q('SELECT COUNT(*) FROM stat_active WHERE day = ?', (old,))[0][0], 1)
        with self.store.connect() as db:
            db.execute("INSERT INTO stat_milestones(sid, key, at, day, career, detail) VALUES ('x', 'k', 1.0, 1, NULL, NULL)")
            db.execute("INSERT INTO stat_acquisition(sid, at, day, source) VALUES ('x', 1.0, ?, 'zalo')", (old,))
            if not db.execute("SELECT 1 FROM stat_players WHERE sid = 'x'").fetchone():
                db.execute("INSERT INTO stat_players(sid, first_day, last_day, days) VALUES ('x', ?, ?, 1)", (old, old))
            rt.forget(db, 'x')
            db.execute("DELETE FROM sessions WHERE sid = 'x'")
        for t in ('stat_births', 'stat_active', 'stat_players', 'stat_milestones', 'stat_acquisition'):
            self.assertEqual(self.q(f"SELECT COUNT(*) FROM {t} WHERE sid = 'x'")[0][0], 1, t)

    def test_upkeep_keeps_unfrozen_activity(self):
        """With an operator limit, stat_active days past KEEP_DAYS are dropped only once frozen (their numbers kept)."""
        patcher = patch.object(st, 'KEEP_DAYS', 120)
        patcher.start()
        self.addCleanup(patcher.stop)
        old = day(-(st.KEEP_DAYS + 5))
        self.born('x', old, [old])
        with patch.object(kpi, 'freeze', return_value={}):              # the freeze has not reached that day
            st.upkeep(self.store, force=True)
        self.assertEqual(self.q('SELECT COUNT(*) FROM stat_active WHERE day = ?', (old,))[0][0], 1)
        st.upkeep(self.store, force=True)                               # frozen first, then dropped
        self.assertEqual(self.q('SELECT COUNT(*) FROM stat_active WHERE day = ?', (old,))[0][0], 0)
        self.assertEqual(self.q("SELECT value FROM stat_kpi_daily WHERE day = ? AND key = 'dau'", (old,))[0][0], 1)

    def test_chat_day_by_vietnam_midnight(self):
        with self.store.connect() as db:
            if not kpi._exists(db, 'chat_messages'):
                self.skipTest('no chat table')
        d = day(-1)
        t0 = kpi.epoch_of(d)
        with self.store.connect() as db:
            for i, (at, pid, adm) in enumerate(((t0 - 1, 'p1', 0), (t0, 'p1', 0), (t0 + 10, 'p2', 0), (t0 + 20, 'op', 1),
                                                (kpi.epoch_of(day(0)) - 1, 'p3', 0), (kpi.epoch_of(day(0)), 'p4', 0))):
                db.execute('INSERT INTO chat_messages(channel, pid, text, at, adm) VALUES (?, ?, ?, ?, ?)', ('all', pid, 'x', at, adm))
            self.assertEqual(kpi.chat_day(db, d), (3, 3))


# ---------------------------------------------------------------- the overview
class OverviewTests(Base):
    def compute(self):
        kpi.freeze(self.store, pause=0)
        return ak.compute(self.store)

    def test_empty_database(self):
        d = self.compute()
        self.assertEqual(d['errors'], {})
        self.assertEqual(d['growth']['totals']['players_total'], 0)
        self.assertIsNone(d['retention']['curve'][0]['pct'])
        self.assertEqual(d['days'], [day(0)])
        csv_text = ak.to_csv(d)
        self.assertIn('# definitions', csv_text)
        for p in ak.PARTS:
            ak.to_csv(d, p)
        with self.assertRaises(ValueError):
            ak.to_csv(d, 'nope')

    def test_numbers_small_cells_and_no_personal_data(self):
        d3, d2 = day(-3), day(-2)
        for i in range(8):
            self.born(f'p{i}', d3, [d3] + ([d2] if i < 2 else []))
        self.sql('INSERT INTO accounts(username, display, pw, sid) VALUES (?, ?, ?, ?)', ('secret_user', SECRET, 'x', 'p0'))
        d = self.compute()
        self.assertEqual(d['errors'], {})
        i3 = d['days'].index(d3)
        self.assertEqual(d['growth']['series']['new_players'][i3], 8)
        self.assertEqual(d['activity']['series']['dau'][i3 + 1], 2)
        c1 = next(c for c in d['retention']['curve'] if c['k'] == 1)
        self.assertEqual((c1['pct'], c1['n']), (25.0, 8))
        lo, hi = c1['ci']
        self.assertTrue(lo < 25.0 < hi and hi - lo > 30)                 # 8 players: a wide interval, shown
        conv = d['retention']['conversion']
        self.assertEqual((conv['n'], conv['accounts']), (8, 1))
        text = ak.to_csv(d)
        blob = json.dumps(d, ensure_ascii=False) + text
        for secret in (SECRET, 'secret_user', 'p0'):
            self.assertNotIn(secret, blob)
        rows = list(csv.reader(io.StringIO(text)))
        conv_row = rows[[r[:1] for r in rows].index(['# retention_conversion_30d']) + 2]
        self.assertEqual(conv_row[1], '<5')                                # 1 account: hidden
        daily = rows[[r[:1] for r in rows].index(['# growth_daily']) + 1:]
        self.assertIn([d3, '8'], [r[:2] for r in daily])

    def test_period_rules(self):
        days = ['2026-09-29', '2026-09-30', '2026-10-01', '2026-10-02']
        v = [1, 2, 3, 100]                       # the last day is today (not complete): left out
        self.assertEqual(ak._period(days, v, 'sum', 0, '2026-10-02'), 6)
        self.assertEqual(ak._period(days, v, 'avg', 2, '2026-10-02'), 2.5)
        self.assertEqual(ak._period(days, v, 'max', 0, '2026-10-02'), 3)
        extra = dict(a=[1, 1, 1, 1], b=[2, 0, 2, 2])
        self.assertEqual(ak._period(days, v, 'ratio:a/b', 0, '2026-10-02', extra), 50.0)   # a zero denominator day is skipped
        self.assertIsNone(ak._period(days, [None] * 4, 'avg', 0, '2026-10-02'))

    def test_wilson(self):
        self.assertIsNone(ak.wilson(0, 0))
        lo, hi = ak.wilson(50, 100)
        self.assertTrue(40 < lo < 41 and 59 < hi < 60)
        self.assertEqual(ak.wilson(0, 3)[0], 0.0)

    def test_a_part_out_of_time_is_named_not_wrong(self):
        self.born('a', day(-1), [day(-1)])
        with patch.object(ak, 'retention', side_effect=st.Busy('admin stats: over the time budget')):
            d = self.compute()
        self.assertIsNone(d['retention'])
        self.assertIn('retention', d['errors'])
        self.assertIsNotNone(d['growth'])
        self.assertIn('không có số liệu', ak.to_csv(d, 'retention'))

    @patch.object(st._Job, 'pass_system', lambda self: None)   # table sizes: not this test's subject (slow on a shared test cluster)
    def test_job_runs_it_and_the_section_serves_the_copy(self):
        self.assertTrue(st.get_section(self.store, 'invest').get('pending'))
        st.refresh_now(self.store)
        st._result_cache.clear()
        got = st.get_section(self.store, 'invest')
        self.assertFalse(got.get('pending'))
        self.assertIn('headline', got)
        self.assertIn('sample', st.saves_section(self.store))
        self.assertIn('covers_since', st.saves_section(self.store)['sample'])

    def test_a_later_saves_pass_fills_the_sample_parts(self):
        d = self.compute()
        self.assertIsNone(d['economy']['sample'])                        # the job's saves pass had not run yet
        saves = dict(economy=dict(sample=40, wallet=dict(median=1200, p90=9000, avg=2500.0), debt=10, investors=4),
                     sample=dict(covers_since='2026-10-01 00:00:00'), sizes=dict(n=40, median=52000), generated_at=1.0)
        ak.with_saves(d, saves)
        s = d['economy']['sample']
        self.assertEqual((s['n'], s['wallet']['median'], s['debt_pct']), (40, 1200, 25.0))
        self.assertEqual(d['infra']['save_sizes']['median'], 52000)
        self.assertIn('economy_saves_sample', ak.to_csv(d, 'economy'))

    def test_latency_quantiles(self):
        edges = st.CMD_EDGES
        hist = [0] * (len(edges) + 1)
        hist[0], hist[5], hist[len(edges)] = 90, 9, 1    # 90 under 2 ms, 9 under 30 ms, 1 over the last edge
        self.assertEqual(ak._hist_q(hist, edges, .5), 2)
        self.assertEqual(ak._hist_q(hist, edges, .95), 30)
        self.assertEqual(ak._hist_q(hist, edges, .999), edges[-1] * 2)


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = GameServer(('127.0.0.1', 0), Store(Path(cls.temp.name) / 'state.db'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'ADMIN_USERS': 'kpi_admin'})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); st.stop_jobs(); cls.server.store.close_pool(); cls.temp.cleanup(); cls.env.stop()
        st.clear_cache()

    def req(self, dev, path, body=None, ua=None):
        h = {'Host': f'127.0.0.1:{self.port}'}
        if ua:
            h['User-Agent'] = ua
        if dev.get('cookie'): h['Cookie'] = dev['cookie']
        if dev.get('csrf'): h['X-Game-CSRF'] = dev['csrf']
        method = 'GET'
        if body is not None:
            method = 'POST'; h['Content-Type'] = 'application/json'; body = json.dumps(body)
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=60)
        con.request(method, path, body=body, headers=h)
        res = con.getresponse(); raw = res.read(); hdrs = dict(res.getheaders()); con.close()
        if 'Set-Cookie' in hdrs: dev['cookie'] = hdrs['Set-Cookie'].split(';')[0]
        data = json.loads(raw) if hdrs.get('Content-Type', '').startswith('application/json') else raw
        if isinstance(data, dict) and data.get('csrf'): dev['csrf'] = data['csrf']
        return res.status, data, hdrs

    def signed(self, name):
        dev = {}
        self.req(dev, '/api/bootstrap', ua='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile Safari/604.1')
        status, data, _ = self.req(dev, '/api/account/register', dict(REG, username=name))
        self.assertEqual(status, 200, data)
        self.req(dev, '/api/bootstrap')
        return dev

    @patch.object(st, '_load', lambda: 0.0)
    @patch.object(st._Job, 'pass_system', lambda self: None)
    def test_admin_only_csv_and_counters(self):
        player = self.signed('kpi_player')
        status, data, _ = self.req(player, '/api/admin/stats/section?name=invest')
        self.assertEqual(status, 403)
        self.assertEqual(self.req(player, '/api/admin/stats/section?name=invest&format=csv')[0], 403)
        admin = self.signed('kpi_admin')
        st.refresh_now(self.server.store)
        st._result_cache.clear()
        status, data, _ = self.req(admin, '/api/admin/stats/section?name=invest')
        self.assertEqual(status, 200, data)
        self.assertIn('defs', data)
        status, body, hdrs = self.req(admin, '/api/admin/stats/section?name=invest&format=csv&part=growth')
        self.assertEqual(status, 200)
        self.assertIn('text/csv', hdrs['Content-Type'])
        text = body.decode('utf-8-sig')
        self.assertIn('# growth_daily', text)
        self.assertNotIn('kpi_player', text)
        self.assertEqual(self.req(admin, '/api/admin/stats/section?name=invest&format=csv&part=nope')[0], 400)
        p = {k: v for (d, k), v in kpi.pending(self.server.store).items()}
        self.assertGreaterEqual(p.get('http:2xx', 0), 4)
        self.assertGreaterEqual(p.get('http:4xx', 0), 1)
        self.assertGreaterEqual(p.get('dev_os:ios', 0), 2)


if __name__ == '__main__':
    unittest.main()
