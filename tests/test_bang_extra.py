"""⚔️ Bang "nhiều hơn" (game/bang_extra.py, owner 20/10 "bang hội nữa nhiều hơn"): 🏯 hall styles bought once from the
fund (Phó bang and up, the hall level, the cooldown, owned styles and colours free), 🎏 decorations (once each, the
island first, never in the facility list nor the ranking), 📋 weekly quests (measured on the bang's ledgers, a member who
did something claims once, the decorations' capped bonus, a weekly cap across bangs), the island view carrying them,
and nothing leaving the fund."""
import inspect
import unittest
from unittest.mock import patch

from game import bang
from game import bang_content as C
from game import bang_extra
from game import bang_extra_content as X
from game import bang_island as BI
from tests.test_bang import Base

DAY = 86400


class Source(unittest.TestCase):
    def test_no_way_out_of_the_fund(self):
        src = inspect.getsource(bang_extra)
        for op in bang_extra.OPS:
            self.assertNotRegex(op, 'withdraw|rut|refund|transfer|pay')
            self.assertIn(op, bang.OPS)
        self.assertEqual(src.count('INSERT INTO bang_fund'), 2)                        # a style, a decoration: both 'build'
        self.assertEqual(src.count("VALUES(?,?,?,'build',?,?,?,?)"), 2)
        self.assertNotIn('_wallet(', src)
        self.assertNotIn('live_effects', src)
        self.assertNotIn('xu', ''.join(k for k in X.QUESTS))

    def test_content(self):
        from game import island_build_content as IC
        homes = {b['id'] for b in IC.BUILDINGS if b['cat'] == 'home'}
        for sid, (name, emoji, hall, price) in X.HALL_STYLES.items():
            self.assertTrue(sid == X.HALL_DEFAULT or sid in homes, sid)              # the art is a house style
            self.assertTrue(1 <= hall <= len(C.HALL_CAP) - 1)
            self.assertEqual(price == 0, sid == X.HALL_DEFAULT)
        for d, (_, _, price, hall, _) in X.DECOR.items():
            self.assertNotIn(X.DECOR_FAC + d, C.FACILITIES)
            self.assertGreater(price, 0)
        self.assertLessEqual(X.DECOR_BONUS * len(X.DECOR), X.DECOR_BONUS_MAX)
        self.assertEqual(bang_extra.decor_bonus(99), X.DECOR_BONUS_MAX)
        for q, (_, text, measure, *_r, pts) in X.QUESTS.items():
            self.assertIn(measure, ('checkin', 'work', 'active', 'give', 'build'))
            self.assertLessEqual(pts, 100)
        weeks = [f'2026-W{n:02d}' for n in range(1, 53)]
        for w in weeks:
            qs = bang_extra.quests_of('b0123456789', w)
            self.assertEqual(len(qs), X.QUESTS_A_WEEK)
            self.assertEqual(len({X.QUESTS[q][2] for q in qs}), X.QUESTS_A_WEEK)   # one quest per measure
        self.assertGreater(len({tuple(bang_extra.quests_of('b0123456789', w)) for w in weeks}), 3)
        self.assertEqual(bang_extra.split_hall('hanok__2'), ('hanok', 2))
        self.assertEqual(bang_extra.split_hall('hanok__7'), ('hanok', 0))
        self.assertEqual(bang_extra.split_hall('thap_moi__1'), ('dinh', 0))         # a style of a newer build: the own hall
        self.assertEqual(bang_extra.split_hall(''), ('dinh', 0))


class Hall(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def score(self):
        with self.store.connect() as db:
            return bang.week_of(db, self.bid, bang.vn_week(self.t[0]), self.t[0])['score']

    def test_buy_switch_and_cooldown(self):
        b = self.player(name='Minh')
        self.op(b, 'join', bang=self.bid)
        self.refused_op(b, 'hall', 'role', style='hanok', confirm=True)
        self.refused_op(self.a, 'hall', 'hall', style='hanok', confirm=True)        # needs the hall at 2
        self.set_level(self.bid, C.HALL, 2)
        self.refused_op(self.a, 'hall', 'not_enough', style='hanok', confirm=True)
        self.set_fund(self.bid, 30_000_000)
        before = self.score()
        self.refused_op(self.a, 'hall', None, style='hanok')                        # asks for confirmation first
        self.refused_op(self.a, 'hall', None, style='hanok', look=3, confirm=True)  # three colours: 0..2
        out = self.op(self.a, 'hall', style='hanok', look=1, confirm=True)
        self.assertIn('Hanok', out['done']['message'])
        r = self.one('SELECT fund, spent FROM bangs WHERE id=?', (self.bid,))
        self.assertEqual((r['fund'], r['spent']), (20_000_000, 10_000_000))
        self.assertEqual(self.one("SELECT id, kind, amount FROM bang_fund WHERE id LIKE 'h:%'"),
                         dict(id=f'h:{self.bid}:hanok', kind='build', amount=-10_000_000))
        self.assertEqual(self.one('SELECT place, level FROM bang_facilities WHERE bang=? AND fac=?', (self.bid, C.HALL)),
                         dict(place='hanok__1', level=2))
        self.assertEqual(self.score(), before)                                      # the ranking never moves with it
        self.assertEqual(out['page']['hall']['style'], 'hanok')
        # the same again: nothing; another colour within the hour: wait
        self.assertTrue(self.op(self.a, 'hall', style='hanok', look=1)['done'].get('again'))
        self.refused_op(self.a, 'hall', 'wait', style='hanok', look=2)
        self.t[0] += X.HALL_GAP + 1
        self.op(self.a, 'hall', style='hanok', look=2)                              # owned: free, no confirmation
        self.t[0] += X.HALL_GAP + 1
        self.op(self.a, 'hall', style='dinh')                                       # back to its own hall: free
        self.t[0] += X.HALL_GAP + 1
        self.op(self.a, 'hall', style='hanok')
        self.assertEqual(self.one('SELECT fund FROM bangs WHERE id=?', (self.bid,))['fund'], 20_000_000)   # paid once
        self.assertEqual(len(self.rows("SELECT 1 FROM bang_fund WHERE id LIKE 'h:%'")), 1)
        with self.store.connect() as db:
            self.assertEqual(bang.levels(db, self.bid)[C.HALL], 2)
        page = bang.page(self.store, self.sid(self.a))
        h = {x['id']: x for x in page['hall']['list']}
        self.assertEqual((page['hall']['style'], h['hanok']['owned'], h['villa_phap']['owned'], h['villa_phap']['open']), ('hanok', True, False, False))
        self.assertGreater(page['hall']['wait'], 0)

    def test_the_island_view_carries_it(self):
        from game.bang_island_source import BangIslandSource
        self.set_isle(self.bid, 1)
        self.set_level(self.bid, C.HALL, 3)
        self.set_fund(self.bid, 30_000_000)
        self.op(self.a, 'hall', style='villa_phap', look=2, confirm=True)
        raw = BangIslandSource().view(self.store, self.bid)
        self.assertEqual(raw['hall'], dict(style='villa_phap', look=2))
        v = BI.island_view(BI.validate_view(raw), self.t[0])
        self.assertEqual(v['hall'], dict(style='villa_phap', look=2))
        self.assertEqual([f['id'] for f in v['facilities']], list(BI.FACILITY_IDS))


class Decor(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def test_once_each_never_a_facility(self):
        self.set_fund(self.bid, 50_000_000)
        self.refused_op(self.a, 'decor', 'island', id='den_long', confirm=True)     # 🏝️ the island first
        self.set_isle(self.bid, 1)
        with self.store.connect() as db:
            before = bang.week_of(db, self.bid, bang.vn_week(self.t[0]), self.t[0])
        self.refused_op(self.a, 'decor', 'hall', id='lau_chuong', confirm=True)
        self.refused_op(self.a, 'decor', None, id='den_long')
        self.op(self.a, 'decor', id='den_long', confirm=True)
        self.op(self.a, 'decor', id='hoa_dao', confirm=True)
        self.assertTrue(self.op(self.a, 'decor', id='den_long', confirm=True)['done'].get('again'))
        self.assertEqual(self.one('SELECT fund FROM bangs WHERE id=?', (self.bid,))['fund'], 42_000_000)
        with self.store.connect() as db:
            self.assertEqual(bang_extra.decor_of(db, self.bid), ['den_long', 'hoa_dao'])
            lv = bang.levels(db, self.bid)
            after = bang.week_of(db, self.bid, bang.vn_week(self.t[0]), self.t[0])
        self.assertNotIn('d_den_long', lv)
        self.assertEqual((after['score'], after['levels']), (before['score'], before['levels']))   # never the ranking
        page = bang.page(self.store, self.sid(self.a))
        self.assertEqual([f['id'] for f in page['facilities']], list(C.FAC_ORDER))
        self.assertEqual((page['decor']['have'], page['decor']['bonus']), (['den_long', 'hoa_dao'], 2 * X.DECOR_BONUS))
        board = bang.standings(self.store.connect(), bang.vn_week(self.t[0]), self.t[0])
        self.assertEqual(board[0]['levels'], 0)
        from game.bang_island_source import BangIslandSource
        v = BI.island_view(BI.validate_view(BangIslandSource().view(self.store, self.bid)), self.t[0])
        self.assertEqual(v['decor'], ['den_long', 'hoa_dao'])


class Quests(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)
        self.b = self.player(name='Minh')
        self.op(self.b, 'join', bang=self.bid)
        p = patch.object(bang_extra, 'quests_of', lambda bid, week: ['diem_danh', 'xay_dung', 'gop_quy'])
        p.start()
        self.addCleanup(p.stop)

    def test_done_together_claimed_once(self):
        card = bang.page(self.store, self.sid(self.a))['quests']
        self.assertEqual([(q['id'], q['need'], q['done']) for q in card['list']],
                         [('diem_danh', 6, False), ('xay_dung', 1, False), ('gop_quy', 3_000_000, False)])
        self.refused_op(self.a, 'quest', 'not_done', id='diem_danh')
        self.refused_op(self.a, 'quest', 'not_this_week', id='lam_viec')
        for day in range(3):                                                         # two members, three days (Mon–Wed)
            self.op(self.a, 'checkin')
            if day < 2:
                self.op(self.b, 'checkin')
                self.t[0] += DAY
        self.refused_op(self.a, 'quest', 'not_done', id='diem_danh')                 # 5 of 6
        self.op(self.b, 'checkin')
        pts = self.mine(self.b)['points']
        out = self.op(self.b, 'quest', id='diem_danh')
        self.assertIn('+40', out['done']['message'])
        self.assertEqual(self.mine(self.b)['points'], pts + 40)
        self.assertTrue(self.op(self.b, 'quest', id='diem_danh')['done'].get('again'))
        self.op(self.a, 'quest', id='diem_danh')
        row = self.one('SELECT kind, pts FROM bang_points WHERE id=?', (f'q:{self.pid(self.b)}:{bang.vn_week(self.t[0])}:diem_danh',))
        self.assertEqual((row['kind'], row['pts']), ('quest', 40))
        page = bang.page(self.store, self.sid(self.b))
        week = {m['pid']: m['week'] for m in page['members']}
        self.assertEqual(week[self.pid(self.b)], 3 * C.CHECKIN_POINTS)               # quests never in the week column
        q = {x['id']: x for x in page['quests']['list']}
        self.assertEqual((q['diem_danh']['done'], q['diem_danh']['claimed'], page['quests']['used']), (True, True, 1))
        with self.store.connect() as db:
            self.assertEqual(bang.week_of(db, self.bid, bang.vn_week(self.t[0]), self.t[0])['score'], C.LEVEL_SCORE)   # hall 1, no island: never the quests

    def test_idle_bonus_and_weekly_cap(self):
        self.set_isle(self.bid, 1)
        self.set_fund(self.bid, 40_000_000)
        self.op(self.a, 'decor', id='den_long', confirm=True)                       # also the week's build quest
        self.op(self.a, 'decor', id='hoa_dao', confirm=True)
        self.refused_op(self.b, 'quest', 'idle', id='xay_dung')                      # nothing for the bang this week yet
        self.refused_op(self.a, 'quest', 'idle', id='xay_dung')                      # buying for the bang is not a member's own deed
        self.op(self.a, 'checkin')
        bonus = 40 * (100 + 2 * X.DECOR_BONUS) // 100                                # +10 %
        self.assertIn(f'+{bonus}', self.op(self.a, 'quest', id='xay_dung')['done']['message'])
        self.op(self.b, 'checkin')
        self.op(self.b, 'quest', id='xay_dung')
        self.give(self.a, 3_000_000)
        with patch.object(X, 'QUEST_WEEK_MAX', 1):
            self.refused_op(self.a, 'quest', 'week_max', id='gop_quy')
        self.op(self.a, 'quest', id='gop_quy')
        self.t[0] += 7 * DAY                                                         # a new week, new quests, nothing claimed
        card = bang.page(self.store, self.sid(self.a))['quests']
        self.assertEqual((card['used'], card['active']), (0, False))


class Compat(unittest.TestCase):
    def test_view_without_and_with_extras(self):
        base = dict(bang_id='b1', name='Rồng', emoji='🐉', color='#d2453d', level=1, facilities=[])
        v = BI.island_view(BI.validate_view(base), 0)
        self.assertNotIn('hall', v)
        self.assertNotIn('decor', v)
        v = BI.island_view(BI.validate_view(dict(base, hall=dict(style='NOPE!'), decor=['den_long', 5, 'x' * 40])), 0)
        self.assertNotIn('hall', v)
        self.assertEqual(v['decor'], ['den_long'])
        v = BI.island_view(BI.validate_view(dict(base, hall=dict(style='hanok', look=99))), 0)
        self.assertEqual(v['hall'], dict(style='hanok', look=0))


if __name__ == '__main__':
    unittest.main()
