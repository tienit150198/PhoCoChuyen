"""💍 Live weddings, the game server's side (game/wedding_live.py, game/marriage.py booking, game/live_effects.py kinds):
booking a real date and time, legacy couples' dates, the party cancelled by a divorce, anniversaries paid once, the
reward kinds (title, closeness, the private card), the weekly race view (ties) and the group photo upload."""
import base64
import json
import unittest
from unittest.mock import patch

from game import live_effects as lfx
from game import marriage as mr
from game import system_gift as sg
from game import wedding_live as wl
from game.engine import migrate_state, validate_state
from tests.test_marriage import DAY, PLAN, Base

WEBP = 'data:image/webp;base64,' + base64.b64encode(b'RIFF\x24\x00\x00\x00WEBPVP8 ' + b'\x00' * 24).decode()


class WedBase(Base):
    def setUp(self):
        super().setUp()
        p = patch('game.wedding_live.now', self.clock)
        p.start()
        self.addCleanup(p.stop)
        q = patch('game.live_effects.now', self.clock)
        q.start()
        self.addCleanup(q.stop)

    def couple(self, at_in=2 * 3600):
        a, b = self.user('lananh'), self.user('minhtu')
        self.engage(a, b)
        at = self.clock.t + at_in
        wid = self.plan_and_confirm(a, b, plan=dict(PLAN, at=at))
        return a, b, wid, int(at) // 60 * 60

    def pay(self, tok):
        changed = lfx.on_load(self.store, tok, self.state(tok))
        return changed

    def resolve(self, a):
        return mr.on_load(self.store, a, self.state(a))


class Booking(WedBase):
    def test_a_real_date_and_time_is_booked_for_good(self):
        a, b, wid, at = self.couple()
        w = self.row('SELECT * FROM weddings WHERE id=?', wid)
        self.assertEqual((w['status'], w['target_a'], w['target_b'], w['due_at']), ('confirmed', None, None, float(at)))
        party = self.row('SELECT * FROM wedding_parties WHERE wedding=?', wid)
        self.assertEqual((party['status'], party['at']), ('booked', float(at)))
        self.assertEqual(self.row('SELECT at, source FROM wedding_dates')['source'], 'booked')
        label = f'💍 Cưới ngày {wl.fmt_at(at)}'
        self.assertEqual(self.view(a)['couple']['wed_label'], label)
        self.assertEqual(self.view(b)['wedding']['at_label'], wl.fmt_at(at))
        # the ceremony waits for the real time, whatever the life days
        mr._mutate(self.store, {self.sid(a): lambda s: s['journey'].__setitem__('life_day', s['journey']['life_day'] + 30)})
        self.assertFalse(self.resolve(a))
        self.clock.t = at + 1
        self.resolve(a)
        self.assertEqual(self.view(a)['couple']['status'], 'married')
        self.assertEqual(self.view(b)['couple']['wed_label'], label, 'the booked time stays the date, not the resolution time')
        self.assertEqual(len(self.rows('SELECT * FROM wedding_dates')), 1)

    def test_the_phố_is_told_the_date_and_time_when_both_agree(self):
        a, b, wid, at = self.couple()
        n = self.row("SELECT text FROM news WHERE kind='booked'")
        self.assertIn(wl.fmt_at(at), n['text'])                  # e.g. "sẽ cưới lúc 04/10/2026 · 20:30 tại …"
        self.assertIn('Lịch cưới', n['text'])

    def test_no_booked_news_when_one_of_them_keeps_it_quiet(self):
        a, b = self.user('lananh'), self.user('minhtu')
        self.engage(a, b)
        self.plan_and_confirm(a, b, plan=dict(PLAN, at=self.clock.t + 2 * 3600), announce_b=False)
        self.assertIsNone(self.row("SELECT text FROM news WHERE kind='booked'"))

    def test_the_window_and_a_late_confirmation(self):
        a, b = self.user('an'), self.user('binh')
        self.engage(a, b)
        for bad in (self.clock.t + 1800, self.clock.t + 15 * DAY, 'tối nay'):
            with self.assertRaises(mr.MarriageError) as e:
                self.act(a, 'plan', plan=dict(PLAN, at=bad), mine=50, announce=True)
            self.assertEqual(e.exception.code, 'bad_plan')
        self.act(a, 'plan', plan=dict(PLAN, at=self.clock.t + 3700), mine=50, announce=True)
        w = self.view(b)['wedding']
        self.clock.t += 3700 - 600     # 10 minutes before: too late to confirm, nothing is taken
        before = self.wallet(b)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(b, 'confirm', id=w['id'], version=w['version'], announce=True)
        self.assertEqual(e.exception.code, 'too_late')
        self.assertEqual(self.wallet(b), before)
        self.assertIsNone(self.row('SELECT * FROM wedding_parties'))

    def test_older_clients_keep_life_days_and_a_divorce_cancels_the_party(self):
        a, b = self.user('an'), self.user('binh')
        self.engage(a, b)
        wid = self.plan_and_confirm(a, b)          # no `at`: as before
        w = self.row('SELECT * FROM weddings WHERE id=?', wid)
        self.assertIsNotNone(w['target_a'])
        self.assertIsNone(self.row('SELECT * FROM wedding_parties'))
        c, d, wid2, at = self.couple()
        self.act(c, 'divorce', confirm='HUY')
        self.assertEqual(self.row('SELECT status FROM wedding_parties WHERE wedding=?', wid2)['status'], 'cancelled')


class LegacyDates(WedBase):
    def test_legacy_couples_get_their_wedding_time_then_married_at(self):
        a, b = self.user('an'), self.user('binh')
        self.engage(a, b)
        wid = self.plan_and_confirm(a, b)
        self.clock.t += 10 * DAY
        self.resolve(a)
        done_at = self.row('SELECT done_at FROM weddings WHERE id=?', wid)['done_at']
        self.assertIsNone(self.row('SELECT * FROM wedding_dates'))
        self.assertEqual(self.view(a)['couple']['wed_label'], f'💍 Cưới ngày {wl.fmt_at(done_at)}')
        with self.store.connect() as db:
            c = mr._bond(db, self.sid(a))
        self.store.transaction(lambda db: wl.date_of(db, c, write=True))
        r = self.row('SELECT * FROM wedding_dates')
        self.assertEqual((r['source'], r['at']), ('legacy', done_at))
        # nothing else was rewritten
        self.assertEqual(self.row('SELECT married_at FROM couples')['married_at'], c['married_at'])
        # a married couple without a done wedding row: married_at
        self.store.transaction(lambda db: db.execute('DELETE FROM wedding_dates'))
        self.store.transaction(lambda db: db.execute("UPDATE weddings SET status='x' WHERE id=?", (wid,)))
        with self.store.connect() as db:
            self.assertEqual(wl.date_of(db, c), c['married_at'])


class Anniversaries(WedBase):
    def married(self):
        a, b, wid, at = self.couple()
        self.clock.t = at + 60
        self.resolve(a)
        self.resolve(b)
        return a, b, at

    def test_paid_once_per_milestone_with_the_card_and_title(self):
        a, b, at = self.married()
        self.assertFalse(wl.on_load(self.store, a, self.state(a)))
        self.clock.t = at + 100 * DAY + 60
        w0 = self.wallet(a)
        self.assertTrue(wl.on_load(self.store, a, self.state(a)))
        self.assertFalse(wl.on_load(self.store, b, self.state(b)), 'the other spouse has the same rows already')
        rows = self.rows("SELECT id, kind, amount FROM live_effects WHERE sid=? ORDER BY id", self.sid(a))
        self.assertEqual([r['kind'] for r in rows], ['coins', 'coins', 'title'])
        npc = next(r['amount'] for r in rows if r['id'].endswith(':npc'))
        self.assertTrue(self.pay(a))
        self.assertEqual(self.wallet(a), w0 + 200 + npc)
        s = self.state(a)
        self.assertIn('w_100', s['journey']['titles'])
        validate_state(migrate_state(s))
        changed, cards = sg.on_load(self.store, a, self.state(a))
        self.assertEqual([(g['coins'], g['title']) for g in cards], [(200, '💞 Trăm ngày bên nhau')])
        self.assertFalse(self.pay(a))
        self.assertFalse(wl.on_load(self.store, a, self.state(a)))
        self.assertEqual(self.wallet(a), w0 + 200 + npc)
        news = self.rows("SELECT text FROM news WHERE kind='anniversary'")
        self.assertEqual(len(news), 1)
        self.assertIn('tròn 100 ngày cưới', news[0]['text'])
        # a year later: only the year
        self.clock.t = at + 365 * DAY + 60
        wl.on_load(self.store, a, self.state(a))
        self.pay(a)
        self.assertIn('w_1y', self.state(a)['journey']['titles'])
        self.assertEqual(len(self.rows("SELECT id FROM live_effects WHERE sid=? AND kind='title'", self.sid(a))), 2)

    def test_a_divorce_stops_the_count(self):
        a, b, at = self.married()
        self.act(a, 'divorce', confirm='LY HON')
        self.clock.t = at + 100 * DAY + 60
        self.assertFalse(wl.on_load(self.store, a, self.state(a)))
        self.assertEqual(self.rows('SELECT * FROM live_effects'), [])

    def test_the_1000_days_pays_1500(self):
        a, b, at = self.married()
        self.clock.t = at + 1000 * DAY + 60
        wl.on_load(self.store, a, self.state(a))
        w0 = self.wallet(a)
        for _ in range(3):
            self.pay(a)
        gained = self.wallet(a) - w0
        npc = sum(r['amount'] for r in self.rows("SELECT amount FROM live_effects WHERE sid=? AND id LIKE '%npc'", self.sid(a)))
        self.assertEqual(gained, 200 + 500 + 800 + 1500 + npc)
        self.assertTrue({'w_100', 'w_1y', 'w_500', 'w_1000'} <= set(self.state(a)['journey']['titles']))


class Kinds(WedBase):
    def test_closeness_title_and_card_rows_are_applied_once(self):
        a, b = self.user('an'), self.user('binh')
        sa, sb = self.sid(a), self.sid(b)
        self.store.transaction(lambda db: (wl.grant(db, sa, 'closeness', 2, 'wedc:1:x:a', {'with': sb}),
                                           wl.grant(db, sa, 'closeness', 2, 'wedc:2:x:a', {'with': sb}),
                                           wl.grant(db, sa, 'title', 1, 'wedhost:1:a:w_crowd', dict(title='w_crowd')),
                                           wl.grant(db, sa, 'title', 1, 'bad:1', dict(title='st_local')),
                                           wl.grant(db, sa, 'coins', 1100, 'wedhost:1:a', dict(src='host', popup=dict(title='💍', text='25 khách')))))
        w0 = self.wallet(a)
        self.pay(a)
        self.pay(a)
        with self.store.connect() as db:
            self.assertEqual(wl.close_points(db, sa, sb), 4)
        s = self.state(a)
        self.assertIn('w_crowd', s['journey']['titles'])
        self.assertNotIn('st_local', s['journey']['titles'], 'only the wedding titles come this way')
        self.assertEqual(self.row("SELECT status FROM live_effects WHERE id='bad:1'")['status'], 'pending')
        self.assertEqual(self.wallet(a), w0 + 1100)
        hist = [r for r in s['journey']['history'] if r['label'] == lfx.LABELS['host']]
        self.assertEqual(len(hist), 1)
        self.assertEqual(len(self.rows("SELECT * FROM system_gifts WHERE sid=? AND status='applied'", sa)), 1)
        # friends see the closeness on the card
        self.befriend(sa, sb)
        from game import friends as fr
        with self.store.connect() as db:
            card = fr._card(db, sa, sb)
        self.assertEqual(card['close'], 4)


class Race(WedBase):
    def guest(self, wid, sid, at, ok=1):
        week = wl.vn_week(at)
        self.store.transaction(lambda db: db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,?,1,1,?,?,?)',
                                                     (wid, sid, 'p' + sid[:15], ok, at, wl.vn_day(at), week)))

    def test_most_weddings_first_and_ties_to_whoever_got_there_first(self):
        a, b, c = self.user('an'), self.user('binh'), self.user('chi')
        sa, sb, sc = self.sid(a), self.sid(b), self.sid(c)
        t = wl.week_start(self.clock.t) + 3600
        self.clock.t = t + 5 * 3600
        for i, (sid, dt) in enumerate([(sa, 10), (sa, 400), (sb, 20), (sb, 300), (sc, 30)]):
            self.guest(100 + i, sid, t + dt)
        self.guest(200, sc, t + 40, ok=0)          # not a counted guest
        v = wl.race_view(self.store, sc)
        self.assertEqual([(r['name'], r['n']) for r in v['top']], [('Binh', 2), ('An', 2), ('Chi', 1)])
        self.assertTrue(v['top'][2]['me'])
        self.assertEqual([p['xu'] for p in v['prizes']], [300, 150, 150])


class WeekScript(WedBase):
    def test_settles_last_week_once(self):
        import os
        import subprocess
        import sys
        import time
        from pathlib import Path
        if self.store.pg:
            self.skipTest('the script is run against SQLite here')
        a, b = self.user('an'), self.user('binh')
        prev = wl.week_start(time.time()) - 7 * DAY + 3600
        for i, tok in enumerate((a, b, a)):
            sid = self.sid(tok)
            self.store.transaction(lambda db, sid=sid, i=i: db.execute(
                'INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?,?,?,1,1,1,?,?,?)',
                (10 + i, sid, 'p' + sid[:15], prev + i, 'd', wl.vn_week(prev))))
        env = {k: v for k, v in os.environ.items() if k != 'DATABASE_URL'}
        root = Path(__file__).resolve().parents[1]
        run = lambda *x: subprocess.run([sys.executable, str(root / 'scripts' / 'wedding_week.py'), '--db', str(self.store.path), *x],
                                         capture_output=True, text=True, env=env, timeout=60)
        dry = run('--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn('not settled yet', dry.stdout)
        self.assertEqual(self.rows('SELECT * FROM live_effects'), [])
        for _ in range(2):
            out = run()
            self.assertEqual(out.returncode, 0, out.stderr)
        coins = self.rows("SELECT sid, amount FROM live_effects WHERE kind='coins' ORDER BY amount DESC")
        self.assertEqual([(c['sid'], c['amount']) for c in coins], [(self.sid(a), 300), (self.sid(b), 150)])
        self.assertEqual(len(self.rows('SELECT * FROM wedding_race')), 1)


class Schema(unittest.TestCase):
    def test_version_and_tables(self):
        from game import pg_schema
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 8)   # 8: the wedding tables (7 went to dates in 1.0.1)
        names = {t['name'] for t in pg_schema.TABLES}
        for t in ('wedding_dates', 'wedding_parties', 'wedding_guests', 'wedding_photos', 'wedding_race', 'player_closeness'):
            self.assertIn(t, names)
            self.assertIn(f'CREATE TABLE IF NOT EXISTS {t} ', pg_schema.TABLES_DDL)
            self.assertIn(f'CREATE TABLE IF NOT EXISTS {t} ', wl.SCHEMA)


class Photos(WedBase):
    def test_upload_once_by_the_taker(self):
        a, b, wid, at = self.couple()
        g = self.user('khach')
        self.store.transaction(lambda db: db.execute('INSERT INTO wedding_photos(wedding, n, sid, at) VALUES(?, 1, ?, ?)', (wid, self.sid(g), self.clock.t)))
        with self.assertRaises(wl.WeddingError):
            wl.save_photo(self.store, self.sid(a), dict(wedding=wid, n=1, image=WEBP))     # not the taker
        with self.assertRaises(wl.WeddingError):
            wl.save_photo(self.store, self.sid(g), dict(wedding=wid, n=1, image='data:image/png;base64,AAAA'))
        self.assertEqual(wl.save_photo(self.store, self.sid(g), dict(wedding=wid, n=1, image=WEBP)), dict(ok=True))
        with self.assertRaises(wl.WeddingError) as e:
            wl.save_photo(self.store, self.sid(g), dict(wedding=wid, n=1, image=WEBP))
        self.assertEqual(e.exception.code, 'gone')
        self.assertEqual([p['n'] for p in wl.photos(self.store, self.sid(b))], [1])
        self.assertEqual(wl.photos(self.store, self.sid(g)), [], 'only the couple sees them')


if __name__ == '__main__':
    unittest.main()
