"""🦉 Cú đêm của phố (game/online_board.py): the weekly board of play time read from stat_play, shown an hour less,
its weekly titles (game/lb_titles.py) and the Monday freeze with the ended week's own totals."""
import time
import unittest.mock

from game import lb_titles as lbt
from game import leaderboard as lb
from game import online_board as ob
from game.wedding_live import vn_day
from tests import test_lb_titles as T
from tests.test_lb_titles import MON, SUN, TUE, at, with_titles
from tests.test_leaderboard import ROOT


class OnlineBoard(T.Weekly):   # (the module, not the class: pytest would run Weekly's own tests here again)
    def setUp(self):
        super().setUp()
        ob.clear_cache()
        self.addCleanup(ob.clear_cache)

    def play(self, token, day, secs):
        sid = self.sid(token)

        def w(db):
            db.execute('INSERT INTO stat_play(day,sid,secs,sessions,cmds,first_at,last_at,sess_at) VALUES(?,?,?,1,1,0,0,0) '
                       'ON CONFLICT(day,sid) DO UPDATE SET secs=excluded.secs', (day, sid, secs))
        self.store.transaction(w)
        ob.clear_cache()

    def test_week_days_and_shown_time(self):
        self.assertEqual(ob.week_days(SUN), ('2026-09-28', '2026-10-04'))
        self.assertEqual(ob.week_days(MON), ('2026-10-05', '2026-10-11'))
        self.assertEqual(ob.shown(5 * 3600), 4 * 3600)   # owner: online 5 hours shows 4
        self.assertEqual(ob.shown(1800), 0)
        self.assertEqual(lb.parse_query({'board': 'online'}), ('online', 50))
        self.assertEqual(lbt.title_of('online', 1)['text'], '🦉 Cú đêm của phố')
        self.assertEqual(lbt.title_of('online', 3)['name'], 'Thức cùng ánh trăng')
        self.assertEqual(lbt.title_of('online', 10)['name'], 'Hội cú đêm')

    def test_board_order_privacy_and_me(self):
        a = self.player(with_titles(1), account='An')
        b = self.player(with_titles(1), account='Bình')
        c = self.player(with_titles(1), account='Chi')
        g = self.player(with_titles(1))                      # a guest who never opted in: counted, never named
        self.play(a, '2026-10-05', 3 * 3600)
        self.play(a, '2026-10-06', 2 * 3600)                 # 5 h over two days of the same week
        self.play(b, '2026-10-06', 6 * 3600)
        self.play(c, '2026-10-06', 3600 + 30)                # shows 30 s: not yet on the board
        self.play(g, '2026-10-06', 9 * 3600)
        self.play(b, '2026-10-04', 50 * 3600)                # last week: not this week's
        v = ob.view(self.store, 50, a, t=TUE)
        self.assertEqual([(r['name'], r['score'], r['rank'], r['me']) for r in v['rows']],
                         [('Bình', 5 * 3600, 1, False), ('An', 4 * 3600, 2, True)])
        self.assertEqual(v['total'], 2)
        self.assertEqual((v['me']['rank'], v['me']['score']), (2, 4 * 3600))
        self.assertIsNone(ob.view(self.store, 50, c, t=TUE)['me']['rank'])
        lb.set_visible(self.store, b, self.store.read(b)[0], False)
        ob.clear_cache()
        v = ob.view(self.store, 50, b, t=TUE)
        self.assertEqual([r['name'] for r in v['rows']], ['An'])
        self.assertEqual(v['me']['rank'], 1)                 # hidden: still told where they would stand
        self.assertFalse(v['me']['visible'])

    def test_titles_daily_and_monday_freeze(self):
        a = self.player(with_titles(1), account='An')
        b = self.player(with_titles(1), account='Bình')
        self.play(a, '2026-10-03', 8 * 3600)
        self.play(b, '2026-10-04', 7 * 3600)
        self.assertTrue(lbt.refresh(self.store, SUN))
        self.assertIn(('online', 1), self.holders()['An'])
        self.assertIn(('online', 2), self.holders()['Bình'])
        self.play(b, '2026-10-04', 10 * 3600)                # Bình passes An on Sunday evening
        self.play(a, '2026-10-05', 2 * 3600)                 # and An plays after midnight: the new week
        self.assertTrue(lbt.refresh(self.store, MON))
        final = self.rows("SELECT week, rank, sid, score FROM lb_weekly WHERE final=1 AND board='online' ORDER BY rank")
        self.assertEqual([(r['week'], r['rank'], self.name_of(r['sid']), r['score']) for r in final],
                         [('2026-W40', 1, 'Bình', 9 * 3600), ('2026-W40', 2, 'An', 7 * 3600)])
        cur = self.rows("SELECT week, rank, sid FROM lb_weekly WHERE final=0 AND board='online' ORDER BY rank")
        self.assertEqual([(r['week'], r['rank'], self.name_of(r['sid'])) for r in cur], [('2026-W41', 1, 'An')])
        with unittest.mock.patch.object(lbt, 'now', return_value=TUE):
            w = lbt.board_view(self.store, 'online', self.sid(a))
        self.assertEqual(w['last']['tiers'][0]['holders'], [dict(rank=1, name='Bình', me=False)])
        self.assertEqual(w['tiers'][0]['holders'], [dict(rank=1, name='An', me=True)])

    def test_top_ten_only(self):
        toks = [self.player(with_titles(1), account=f'Người {i:02d}') for i in range(12)]
        for i, tok in enumerate(toks):
            self.play(tok, '2026-10-06', (20 - i) * 3600)
        self.assertTrue(lbt.refresh(self.store, at(2026, 10, 7, 9)))
        ranks = sorted(h['rank'] for v in lbt.holders(self.store).values() for h in v if h['board'] == 'online')
        self.assertEqual(ranks, list(range(1, 11)))

    def test_monday_small_hours_are_counted_f434(self):
        """F#434 (minnie, Monday 19/10 01:37–01:55): the week is the Vietnam week (Monday 01:55 VN is still Sunday in
        UTC), and 18 minutes of a new week, shown as nothing (shown = real − 1 h), still tell the player they count and
        how much more puts the name up, not a bare "not on the board"."""
        self.assertEqual(ob.week_days(at(2026, 10, 19, 1, 55)), ('2026-10-19', '2026-10-25'))
        late = at(2026, 10, 5, 1, 55)
        self.assertEqual(ob.week_days(late), ('2026-10-05', '2026-10-11'))
        m = self.player(with_titles(1), account='Minnie')
        fresh = self.player(with_titles(1), account='Mới')
        self.play(m, '2026-10-04', 3 * 3600)                 # Sunday: the week that ended
        self.play(m, '2026-10-05', 18 * 60)                  # Monday 01:37–01:55
        self.play(fresh, '2026-10-04', 3600)
        v = ob.view(self.store, 50, m, t=late)
        self.assertEqual(v['rows'], [])
        me = v['me']
        self.assertIsNone(me['rank'])
        self.assertNotIn('score', me)
        self.assertTrue(me['counted'])
        self.assertEqual(me['need'], ob.SHOWN_OFF + ob.SHOWN_MIN - 18 * 60)   # 43 more minutes
        me = ob.view(self.store, 50, fresh, t=late)['me']
        self.assertFalse(me['counted'])
        self.assertEqual(me['need'], ob.SHOWN_OFF + ob.SHOWN_MIN)
        self.play(m, '2026-10-05', 2 * 3600)                 # on the board: no `need` any more
        me = ob.view(self.store, 50, m, t=late)['me']
        self.assertEqual((me['rank'], me['score']), (1, 3600))
        self.assertNotIn('need', me)

    def test_real_commands_reach_the_own_card(self):
        """The whole path: game commands → receipts → trigger stat_play_cmd (Vietnam day) → the own card."""
        a = self.player(with_titles(1), account='An')
        sid = self.sid(a)
        self.cmd(a, 'settings', {'sound': False})
        self.cmd(a, 'settings', {'sound': True})
        now = time.time()
        row = self.rows('SELECT day, cmds, secs FROM stat_play WHERE sid=?', sid)
        self.assertEqual([r['day'] for r in row], [vn_day(now)])
        self.assertGreaterEqual(row[0]['cmds'], 3)           # import_save + 2 settings
        me = ob.view(self.store, 50, a, t=now)['me']
        self.assertIsNone(me['rank'])
        self.assertTrue(me['counted'])
        self.assertEqual(me['need'], ob.SHOWN_OFF + ob.SHOWN_MIN - row[0]['secs'])

    def test_own_card_text_f434(self):
        js = (ROOT / 'public/js/v4/leaderboard.js').read_text(encoding='utf-8')
        self.assertIn(":board==='online'?onlineWait(me)", js)
        self.assertIn('đã được ghi nhận', js)
        self.assertIn('giờ chơi đầu tiên của tuần chưa tính lên bảng', js)
