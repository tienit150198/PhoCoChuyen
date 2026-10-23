"""🏆 Thưởng top tuần and 💍 the wedding board's weekly titles (owner 23/10: "cái đám cưới nữa, mình cho danh hiệu với
khung riêng nhé. với từ giờ những người được top sẽ có thưởng riêng hằng tuần … riêng đám cưới cho cao hơn chút";
amounts 24/10: every board 1,000,000 / 500,000 / 200,000 xu for top 1 / 2–3 / 4–10, the wedding board 2,000,000 /
1,000,000, each Trùm nghề 1,000,000, the bang war's fighters 500,000 / 200,000).

* reward_of / tiers_of: the amounts of game/lb_titles.py WEEKLY_REWARD per tier; the wedding board pays more.
* The Monday freeze writes one system gift per final holder (lbw-<week>-<board>-<rank>); a second refresh, another
  process (heal) or a direct second call never adds one. Weeks before REWARD_FROM are never paid. Admin accounts and
  players the boards hide get nothing.
* 💍 wedding: the week's guests (wedding_guests) hold its titles like any board's holders, frozen with the week."""
import os
import unittest
import unittest.mock

from game import lb_titles as lbt
from game import leaderboard as lb
from game import system_gift as sg
from tests.test_lb_titles import MON, SUN, TUE, at, story_state, with_titles
from tests.test_leaderboard import Base


class Amounts(unittest.TestCase):
    def test_table(self):
        self.assertEqual([lbt.reward_of('wedding', r) for r in (1, 2, 3, 4)], [2_000_000, 1_000_000, 1_000_000, 0])
        self.assertEqual([lbt.reward_of('all', r) for r in (1, 2, 3, 4, 10, 11)], [1_000_000, 500_000, 500_000, 200_000, 200_000, 0])
        self.assertEqual([lbt.reward_of('pet_war', r) for r in (1, 5, 6, 10, 11)], [500_000, 500_000, 200_000, 200_000, 0])
        self.assertEqual([lbt.reward_of('race_drag_bike', r) for r in (1, 3, 4)], [1_000_000, 500_000, 0])
        self.assertEqual([lbt.reward_of('milk_tea', r) for r in (1, 2)], [1_000_000, 0])   # 🏆 Trùm: top 1 only
        self.assertGreater(lbt.reward_of('wedding', 1), max(lbt.reward_of(b, 1) for b in lbt.MAIN if b != 'wedding'))
        self.assertEqual([t['reward'] for t in lbt.tiers_of('wedding')], [2_000_000, 1_000_000])
        self.assertEqual([t['reward'] for t in lbt.tiers_of('wealth')], [1_000_000, 500_000, 200_000])
        self.assertEqual([t['reward'] for t in lbt.tiers_of('pet_war')], [500_000, 200_000])
        self.assertEqual(lbt.tiers_of('grocery')[0]['reward'], 1_000_000)

    def test_wedding_board_titles(self):
        self.assertIn('wedding', lbt.MAIN)
        self.assertIn('wedding', lbt.NEW_BOARDS)
        self.assertIn('wedding', lbt.ENDED_BOARDS)
        self.assertEqual(lbt.title_of('wedding', 1)['text'], '💒 Vua ăn cưới của tuần')
        self.assertEqual(lbt.title_of('wedding', 3)['name'], 'Khách mời vàng của tuần')
        self.assertIsNone(lbt.title_of('wedding', 4))
        from game.wedding_live import TITLE_NAMES
        self.assertFalse({n for _, n in lbt.BOARD_TITLES['wedding']} & {v.split(' ', 1)[1] for v in TITLE_NAMES.values()})

    def test_a_gift_this_big_pays_into_a_story_save(self):
        s = story_state()
        w = s['journey']['wallet']
        s, r = sg.apply(s, dict(id='lbw-2026-W43-wedding-1', coins=2_000_000))
        self.assertEqual(s['journey']['wallet'], w + 2_000_000)
        s, r = sg.apply(s, dict(id='lbw-2026-W43-wedding-1', coins=2_000_000))   # once
        self.assertEqual(s['journey']['wallet'], w + 2_000_000)
        self.assertTrue(sg.valid_id('lbw-2026-W43-group_accounting-1'))


class Rewards(Base):
    def setUp(self):
        super().setUp()
        lbt.clear_cache()
        lbt._done.clear()
        lbt._pending.clear()
        for p in (unittest.mock.patch.object(lbt, 'now', return_value=at(2026, 9, 1, 12)),
                  unittest.mock.patch.object(lbt, 'REWARD_FROM', '2026-W40')):
            p.start()
            self.addCleanup(p.stop)

    def rows(self, sql, *args):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args)]

    def gifts(self):
        return {r['id']: r for r in self.rows("SELECT id, sid, coins, title, text, status FROM system_gifts WHERE id LIKE 'lbw-%'")}

    def username(self, tok):
        return self.rows('SELECT username FROM accounts WHERE sid=?', self.sid(tok))[0]['username']

    def guests(self, week, counts):
        """wedding_guests rows: {sid: weddings attended in `week`} (counted, past the minimum minutes)."""
        def run(db):
            w = 1
            for sid, n in counts.items():
                for i in range(n):
                    db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?, ?, ?, 1, 0, 5, ?, ?, ?)',
                               (w, sid, sid[:12], SUN - 3600 + w, '2026-10-04', week))
                    w += 1
        self.store.transaction(run)

    def test_freeze_pays_once_each(self):
        a = self.player(with_titles(2, xp=300), account='An')
        b = self.player(with_titles(1, xp=200), account='Bình')
        lbt.refresh(self.store, SUN)
        self.assertFalse(self.gifts(), 'a daily refresh pays nothing')
        self.assertTrue(lbt.refresh(self.store, MON))
        g = self.gifts()
        self.assertEqual(g['lbw-2026-W40-all-1']['sid'], self.sid(a))
        self.assertEqual(g['lbw-2026-W40-all-1']['coins'], 1_000_000)
        self.assertEqual((g['lbw-2026-W40-all-2']['sid'], g['lbw-2026-W40-all-2']['coins']), (self.sid(b), 500_000))
        self.assertEqual(g['lbw-2026-W40-grocery-1']['sid'], self.sid(a))   # 🏆 Trùm tạp hóa
        self.assertEqual({r['status'] for r in g.values()}, {'pending'})
        self.assertEqual({r['title'] for r in g.values()}, {lbt.REWARD_TITLE})
        self.assertIn('Trùm cuối của phố', g['lbw-2026-W40-all-1']['text'])
        self.assertIn('1.000.000 xu', g['lbw-2026-W40-all-1']['text'])
        final = {(r['board'], r['rank']) for r in self.rows("SELECT board, rank FROM lb_weekly WHERE final=1 AND week='2026-W40'")}
        self.assertEqual({tuple(k.split('-')[3:5]) for k in g}, {(b_, str(r)) for b_, r in final})
        n = len(g)
        # again: the same process, another process of this build (heal), a direct call, the next day
        self.assertFalse(lbt.refresh(self.store, MON + 60))
        lbt._done.clear()
        self.assertFalse(lbt.refresh(self.store, MON + 120))
        self.assertEqual(self.store.transaction(lambda db: lbt.reward_week(db, '2026-W40', MON)), 0)
        self.assertTrue(lbt.refresh(self.store, TUE))
        self.assertEqual(len(self.gifts()), n)
        # paid on load once, by the gift's own path (game/system_gift.py)
        self.assertEqual(len(self.rows("SELECT 1 FROM system_gifts WHERE id LIKE 'lbw-2026-W41-%'")), 0)

    def test_two_processes_race(self):
        """Both write the same ids under ON CONFLICT DO NOTHING: the second writes nothing."""
        self.player(with_titles(2, xp=300), account='An')
        lbt.refresh(self.store, SUN)
        self.assertTrue(lbt.refresh(self.store, MON))
        before = self.gifts()
        self.store.transaction(lambda db: db.execute("DELETE FROM system_gifts WHERE id='lbw-2026-W40-all-1'"))
        self.assertEqual(self.store.transaction(lambda db: lbt.reward_week(db, '2026-W40', MON)), 1)
        self.assertEqual(self.store.transaction(lambda db: lbt.reward_week(db, '2026-W40', MON)), 0)
        self.assertEqual(set(self.gifts()), set(before))

    def test_weeks_before_the_start_are_never_paid(self):
        self.player(with_titles(2, xp=300), account='An')
        with unittest.mock.patch.object(lbt, 'REWARD_FROM', '2026-W41'):
            lbt.refresh(self.store, SUN)
            self.assertTrue(lbt.refresh(self.store, MON))
            self.assertFalse(self.gifts())
            lbt._done.clear()
            self.assertFalse(lbt.refresh(self.store, MON + 60))   # heal: still nothing for W40
            self.assertFalse(self.gifts())

    def test_admin_and_hidden_get_nothing(self):
        a = self.player(with_titles(2, xp=300), account='An')
        b = self.player(with_titles(1, xp=200), account='Bình')
        lbt.refresh(self.store, SUN)
        env = unittest.mock.patch.dict(os.environ, {'ADMIN_USERS': f'someone,{self.username(a).upper()}'})
        env.start()
        self.addCleanup(env.stop)
        self.assertTrue(lbt.refresh(self.store, MON))
        g = self.gifts()
        self.assertFalse([k for k, r in g.items() if r['sid'] == self.sid(a)], 'an admin account')
        self.assertTrue([k for k, r in g.items() if r['sid'] == self.sid(b)])
        # a holder hidden since (or a row written for a player the boards do not show): nothing
        lb.set_visible(self.store, b, self.store.read(b)[0], False)
        guest = self.player(with_titles(1, xp=50))
        self.store.transaction(lambda db: lbt._insert(db, '2026-W40', [('titles', 9, self.sid(b), 1), ('titles', 10, self.sid(guest), 1)], 1, '2026-10-05', MON))
        self.assertEqual(self.store.transaction(lambda db: lbt.reward_week(db, '2026-W40', MON)), 0)

    def test_wedding_board(self):
        a = self.player(with_titles(1, xp=50), account='An')
        b = self.player(with_titles(1, xp=40), account='Bình')
        c = self.player(with_titles(1, xp=30), account='Chi')
        d = self.player(with_titles(1, xp=20), account='Dũng')
        hidden = self.player(with_titles(1, xp=10), account='Ẩn')
        lb.set_visible(self.store, hidden, self.store.read(hidden)[0], False)
        self.guests('2026-W40', {self.sid(hidden): 9, self.sid(b): 5, self.sid(a): 3, self.sid(c): 3, self.sid(d): 1})
        self.assertTrue(lbt.refresh(self.store, SUN))
        cur = [(r['rank'], r['sid']) for r in self.rows("SELECT rank, sid FROM lb_weekly WHERE board='wedding' AND final=0 ORDER BY rank")]
        self.assertEqual(cur, [(1, self.sid(b)), (2, self.sid(a)), (3, self.sid(c))])   # hidden: on no board; a tie: who got there first
        self.assertEqual(lbt.held(self.store, self.sid(b))[0]['text'], '💒 Vua ăn cưới của tuần')
        self.guests('2026-W41', {self.sid(d): 2})   # the new week starts from its own guests
        self.assertTrue(lbt.refresh(self.store, MON))
        final = [(r['rank'], r['sid']) for r in self.rows("SELECT rank, sid FROM lb_weekly WHERE board='wedding' AND final=1 AND week='2026-W40' ORDER BY rank")]
        self.assertEqual(final, cur)
        now_ = [r['sid'] for r in self.rows("SELECT sid FROM lb_weekly WHERE board='wedding' AND final=0")]
        self.assertEqual(now_, [self.sid(d)])
        g = self.gifts()
        self.assertEqual((g['lbw-2026-W40-wedding-1']['sid'], g['lbw-2026-W40-wedding-1']['coins']), (self.sid(b), 2_000_000))
        self.assertEqual(g['lbw-2026-W40-wedding-3']['coins'], 1_000_000)
        self.assertNotIn('lbw-2026-W40-wedding-4', g)
        with unittest.mock.patch.object(lbt, 'now', return_value=TUE):
            v = lbt.board_view(self.store, 'wedding', self.sid(b))
        self.assertEqual([t['reward'] for t in v['tiers']], [2_000_000, 1_000_000])
        self.assertTrue(v['last']['tiers'][0]['holders'][0]['me'])


if __name__ == '__main__':
    unittest.main()
