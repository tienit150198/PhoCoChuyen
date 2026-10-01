"""🏅 Danh hiệu tuần (game/lb_titles.py) and 🏷️ several titles and certificates worn at once (game/journey.py):
the titles board, who holds which weekly title, the daily refresh, the Monday freeze, the multi-wear rules and
the migration of the one title worn before."""
import contextlib
import copy
import datetime
import io
import types
import unittest
import unittest.mock

from game import journey as jr
from game import lb_titles as lbt
from game import leaderboard as lb
from game.content import CAREERS
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state
from tests.test_leaderboard import Base, crafted

VN = lbt.VN


def at(y, m, d, hh=12, mm=0):
    """Epoch seconds of a Vietnam wall-clock time."""
    return datetime.datetime(y, m, d, hh, mm, tzinfo=VN).timestamp()


SUN = at(2026, 10, 4, 20)          # Sunday of ISO week 2026-W40
MON = at(2026, 10, 5, 0, 5)        # Monday 00:05: week 2026-W41 has begun
TUE = at(2026, 10, 6, 9)


def story_state():
    s = new_state()
    jr.enable_story(s, 12345)
    s['journey']['gender'] = 'female'
    validate_state(s)
    return s


def act(s, action, **p):
    return apply_action(s, None, action, p)


class TitleNames(unittest.TestCase):
    def test_tiers_and_names(self):
        self.assertEqual([lbt.tier_of('all', r) for r in (1, 2, 3, 4, 10, 11)], [0, 1, 1, 2, 2, None])
        self.assertEqual(lbt.title_of('all', 1)['text'], '👑 Trùm cuối của phố')
        self.assertEqual(lbt.title_of('certs', 3)['name'], 'Học bá chính hiệu')
        self.assertEqual(lbt.title_of('titles', 7)['label'], 'Top 4–10')
        self.assertIsNone(lbt.title_of('titles', 11))
        self.assertEqual(lbt.title_of('milk_tea', 1)['text'], '🏆 Trùm trà sữa')
        self.assertIsNone(lbt.title_of('milk_tea', 2))   # a workplace board: top 1 only
        names = [n for tiers in lbt.BOARD_TITLES.values() for _, n in tiers] + [lbt.title_of(c, 1)['name'] for c in CAREERS]
        self.assertEqual(len(names), len(set(names)), 'every title has its own name')
        self.assertTrue(all(len(n) <= 32 for n in names), 'short enough for a name tag')

    def test_every_workplace_has_its_noun(self):
        self.assertEqual(set(lbt.CAREER_NOUN), set(CAREERS))

    def test_honour_order(self):
        keys = sorted([('milk_tea', 1), ('certs', 2), ('all', 5), ('titles', 1), ('all', 1)], key=lambda x: lbt.honour(*x))
        self.assertEqual(keys, [('all', 1), ('titles', 1), ('milk_tea', 1), ('certs', 2), ('all', 5)])


class TitlesBoard(unittest.TestCase):
    def test_summary_counts_game_titles(self):
        s = crafted(grocery=(10, 2, 1))
        s['journey']['titles'] = {'g_first': 2, 'g_tasks50': 7, 'x_streak10': 5, 'nope': 3}
        self.assertEqual(lb._titles(s), (3, 1, 7))
        self.assertEqual(lb.summary(s)['titles'], (3, 1, -7, 3, 7, 1, 0, 3))
        self.assertNotIn('titles', lb.summary(crafted(grocery=(10, 2, 1))))
        self.assertIn('titles', lb.BOARDS)
        self.assertEqual(lb.parse_query({'board': 'titles'}), ('titles', 50))


def with_titles(n, xp=100, day=3):
    s = crafted(grocery=(xp, 2, 1))
    s['journey']['life_day'] = 20
    s['journey']['titles'] = {t['id']: day for t in jr.TITLES[:n]}
    return s


class Weekly(Base):
    def holders(self):
        return {self.name_of(sid): [(h['board'], h['rank']) for h in v] for sid, v in lbt.holders(self.store).items()}

    def name_of(self, sid):
        with self.store.connect() as db:
            r = db.execute('SELECT display FROM accounts WHERE sid=?', (sid,)).fetchone()
        return r['display'] if r else sid

    def rows(self, sql, *args):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args)]

    def setUp(self):
        super().setUp()
        lbt.clear_cache()
        lbt._done.clear()
        lbt._pending.clear()

    def test_ranks_hold_their_tier(self):
        toks = {}
        for i in range(12):   # 12 accounts: more XP for the lower i, more titles for the higher i
            toks[i] = self.player(with_titles(i + 1, xp=1000 - i * 10), account=f'Người {i:02d}')
        guest = self.player(with_titles(30, xp=5000))   # a guest who never opted in: on no board, holds nothing
        self.assertTrue(lbt.refresh(self.store, SUN))
        h = self.holders()
        self.assertEqual(h['Người 00'][0], ('all', 1))
        self.assertIn(('grocery', 1), h['Người 00'])           # top 1 of a workplace board
        self.assertEqual([x for x in h['Người 01'] if x[0] == 'all'], [('all', 2)])
        self.assertEqual([x for x in h['Người 09'] if x[0] == 'all'], [('all', 10)])
        self.assertFalse([x for x in h.get('Người 10', []) if x[0] == 'all'])   # rank 11: no title
        self.assertNotIn(self.sid(guest), lbt.holders(self.store))
        mine = lbt.held(self.store, self.sid(toks[0]))
        self.assertEqual(mine[0]['text'], '👑 Trùm cuối của phố')     # best first
        self.assertEqual(lbt.best(self.store, self.sid(toks[0])), dict(emoji='👑', name='Trùm cuối của phố'))
        v = lb.view(self.store, 'all', token=toks[1])
        self.assertEqual(v['rows'][0]['title'], dict(emoji='👑', name='Trùm cuối của phố'))
        self.assertNotIn('title', v['rows'][10])
        tiers = v['weekly']['tiers']
        self.assertEqual([len(t['holders']) for t in tiers], [1, 2, 7])
        self.assertTrue(tiers[1]['holders'][0]['me'])
        self.assertEqual(v['me']['titles'][0]['name'], 'Chiến thần cày cuốc')
        self.assertEqual(v['weekly']['week'], lbt.vn_week(lbt.now()))

    def test_daily_refresh_once_a_day(self):
        a = self.player(with_titles(2, xp=300), account='An')
        b = self.player(with_titles(5, xp=200), account='Bình')
        self.assertTrue(lbt.refresh(self.store, SUN - 3600 * 10))
        self.assertFalse(lbt.refresh(self.store, SUN), 'same Vietnam day: nothing to do')
        lbt._done.clear()   # another process: it reads the mark and does nothing either
        self.assertFalse(lbt.refresh(self.store, SUN))
        self.assertEqual(self.holders()['An'][0], ('all', 1))
        # Bình overtakes An during the day: the titles move at the next day's refresh, not before.
        st = self.store.read(b)[0]
        st['careers']['grocery']['xp'] = 900
        self.cmd(b, 'import_save', {'save': {'format': 'mot-ngay-lam-nghe/save-v4', 'state': st}})
        lb.clear_cache()
        self.assertFalse(lbt.refresh(self.store, SUN))
        self.assertEqual(self.holders()['An'][0], ('all', 1))
        self.assertEqual(lb.view(self.store, 'all')['rows'][0]['name'], 'Bình')   # the board itself is live
        self.assertTrue(lbt.refresh(self.store, SUN + 86400 / 2 - 3600 * 5))  # Monday morning: next day (and next week)
        self.assertEqual(self.holders()['Bình'][0], ('all', 1))
        self.assertEqual(self.holders()['Bình'][1], ('titles', 1))
        meta = self.rows("SELECT v FROM leaderboard_meta WHERE k='weekly'")[0]['v']
        self.assertEqual(meta, f'{lbt.vn_day(SUN + 86400 / 2 - 3600 * 5)}|2026-W41')
        self.assertTrue(a)

    def test_monday_freezes_the_week_that_ended(self):
        a = self.player(with_titles(2, xp=300), account='An')
        b = self.player(with_titles(1, xp=200), account='Bình')
        lbt.refresh(self.store, SUN)
        st = self.store.read(b)[0]   # Sunday evening: Bình takes the lead before midnight
        st['careers']['grocery']['xp'] = 900
        self.cmd(b, 'import_save', {'save': {'format': 'mot-ngay-lam-nghe/save-v4', 'state': st}})
        self.assertTrue(lbt.refresh(self.store, MON))
        final = self.rows("SELECT week, board, rank, sid, final FROM lb_weekly WHERE final=1 AND board='all' ORDER BY rank")
        self.assertEqual([(r['week'], r['rank'], self.name_of(r['sid'])) for r in final], [('2026-W40', 1, 'Bình'), ('2026-W40', 2, 'An')])
        cur = self.rows("SELECT week FROM lb_weekly WHERE final=0")
        self.assertEqual({r['week'] for r in cur}, {'2026-W41'})
        # Later days of the new week never touch the frozen week.
        st = self.store.read(a)[0]
        st['careers']['grocery']['xp'] = 2000
        self.cmd(a, 'import_save', {'save': {'format': 'mot-ngay-lam-nghe/save-v4', 'state': st}})
        self.assertTrue(lbt.refresh(self.store, TUE))
        again = self.rows("SELECT week, board, rank, sid FROM lb_weekly WHERE final=1 AND board='all' ORDER BY rank")
        self.assertEqual([(r['rank'], self.name_of(r['sid'])) for r in again], [(1, 'Bình'), (2, 'An')])
        self.assertEqual(self.holders()['An'][0], ('all', 1))
        with unittest.mock.patch.object(lbt, 'now', return_value=TUE):
            v = lbt.board_view(self.store, 'all', self.sid(a))
        self.assertEqual(v['week'], '2026-W41')
        self.assertEqual(v['last']['week'], '2026-W40')
        self.assertEqual(v['last']['tiers'][0]['holders'], [dict(rank=1, name='Bình', me=False)])
        self.assertEqual(v['tiers'][0]['holders'], [dict(rank=1, name='An', me=True)])
        self.assertEqual(v['updated'], TUE)
        self.assertEqual(lbt.fmt_updated(TUE), '06/10 · 09:00')

    def test_a_week_long_gone_keeps_its_last_daily_holders(self):
        self.player(with_titles(2, xp=300), account='An')
        lbt.refresh(self.store, SUN - 7 * 86400)   # week 39
        self.player(with_titles(1, xp=900), account='Bình')
        self.assertTrue(lbt.refresh(self.store, TUE))   # the server was off for a week
        w39 = self.rows("SELECT rank, sid FROM lb_weekly WHERE week='2026-W39' AND final=1 AND board='all'")
        self.assertEqual([self.name_of(r['sid']) for r in w39], ['An'])
        self.assertFalse(self.rows("SELECT 1 FROM lb_weekly WHERE week='2026-W40'"))

    def test_hidden_names_hold_nothing_and_deleted_saves_go(self):
        a = self.player(with_titles(2, xp=300), account='An')
        b = self.player(with_titles(1, xp=200), account='Bình')
        lb.set_visible(self.store, a, self.store.read(a)[0], False)
        lbt.refresh(self.store, SUN)
        self.assertNotIn(self.sid(a), lbt.holders(self.store))
        self.assertEqual(self.holders()['Bình'][0], ('all', 1))
        self.store.transaction(lambda db: lb.forget(db, [self.sid(b)]))
        self.assertFalse(self.rows('SELECT 1 FROM lb_weekly WHERE sid=?', self.sid(b)))

    def test_waits_for_the_boards_to_be_rebuilt(self):
        self.player(with_titles(2, xp=300), account='An')
        self.store.transaction(lambda db: db.execute("INSERT INTO leaderboard_meta(k,v) VALUES('backfill','1')"))   # an older formula
        self.assertFalse(lbt.refresh(self.store, SUN))
        self.assertEqual(lbt.holders(self.store), {})
        self.assertEqual(lb.backfill(self.store, pause=0), 1)
        lbt._pending.clear()
        self.assertTrue(lbt.refresh(self.store, SUN))
        self.assertEqual(self.holders()['An'][0], ('all', 1))

    def test_housekeeping_and_the_request_path_never_raise(self):
        broken = types.SimpleNamespace(path='x', connect=lambda: (_ for _ in ()).throw(RuntimeError('db down')))
        with contextlib.redirect_stderr(io.StringIO()) as err:
            lbt.run_refresh(broken)
        self.assertIn('refresh: RuntimeError', err.getvalue())
        lbt.ensure(broken)
        self.assertEqual(lbt.holders(broken), {})


class Wearing(unittest.TestCase):
    def owned(self):
        s = story_state()
        j = s['journey']
        j['life_day'] = 5
        j['titles'].update(g_first=1, g_tasks50=2, k_careful=2, x_streak10=3)
        j['certificates']['accounting'] = dict(score=90, best=90, earned_day=2, attempts=1)
        j['certificates']['teaching'] = dict(score=40, best=40, earned_day=None, attempts=1)
        validate_state(s)
        return s

    def test_wear_several_titles_and_certificates(self):
        s = self.owned()
        s, r = act(s, 'jr_equip', worn=['cert:accounting', 'g_first', 'x_streak10'])
        j = s['journey']
        self.assertEqual(j['worn'], ['cert:accounting', 'g_first', 'x_streak10'])
        self.assertEqual(j['equipped'], 'g_first', 'the first title stays in `equipped` for older clients')
        self.assertEqual(r['message'], 'Đang đeo 3/3.')
        pub = public_state(s)['journey']
        self.assertEqual([(w['id'], w['kind'], w['emoji']) for w in pub['worn']],
                         [('cert:accounting', 'cert', '🧮'), ('g_first', 'title', '🌱'), ('x_streak10', 'title', '✨')])
        self.assertEqual(pub['wear_max'], 3)
        from game.social import snapshot
        self.assertEqual([t['name'] for t in snapshot(s)[0]['titles']], ['Chứng chỉ Kế toán cơ bản', 'Việc đầu tiên', 'Mười việc liền mạch'])
        s, r = act(s, 'jr_equip', worn=[])
        self.assertEqual((s['journey']['worn'], s['journey']['equipped']), ([], None))

    def test_cap_duplicates_and_what_you_do_not_have(self):
        s = self.owned()
        for worn, why in ((['g_first', 'g_tasks50', 'k_careful', 'x_streak10'], 'tối đa 3'),
                          (['g_first', 'g_first'], 'một lần'), (['g_tasks200'], 'chưa có danh hiệu'),
                          (['cert:teaching'], 'chưa có chứng chỉ'), (['cert:nope'], 'chưa có chứng chỉ'),
                          ('g_first', 'không hợp lệ'), ([1], 'không hợp lệ')):
            with self.assertRaises(GameError) as e:
                act(s, 'jr_equip', worn=worn)
            self.assertIn(why, str(e.exception).lower(), worn)
        self.assertEqual(s['journey']['worn'], [])

    def test_an_older_client_wears_one(self):
        s = self.owned()
        s, _ = act(s, 'jr_equip', worn=['cert:accounting', 'g_tasks50'])
        s, _ = act(s, 'jr_equip', title='k_careful')
        self.assertEqual((s['journey']['worn'], s['journey']['equipped']), (['k_careful'], 'k_careful'))
        s, _ = act(s, 'jr_equip', title=None)
        self.assertEqual(s['journey']['worn'], [])

    def test_tampered_worn_is_rejected(self):
        s = self.owned()
        for edit in (lambda j: j.update(worn=['g_tasks200']), lambda j: j.update(worn=['cert:teaching']),
                     lambda j: j.update(worn=['g_first'] * 2), lambda j: j.update(worn='g_first'),
                     lambda j: j.update(worn=['g_first', 'g_tasks50', 'k_careful', 'cert:accounting'])):
            bad = copy.deepcopy(s)
            edit(bad['journey'])
            with self.assertRaises(GameError):
                validate_state(bad)

    def test_the_title_worn_before_comes_first(self):
        s = self.owned()
        j = s['journey']
        j['equipped'] = 'g_tasks50'
        del j['worn']                       # a save from before 1.2
        s.pop('check', None)
        before = copy.deepcopy(s)
        out = migrate_state(s)
        validate_state(out)
        self.assertEqual(out['journey']['worn'], ['g_tasks50'])
        self.assertEqual(out['journey']['equipped'], 'g_tasks50')
        self.assertEqual(out['journey']['wallet'], before['journey']['wallet'])
        self.assertEqual({k: v['money'] for k, v in out['careers'].items()}, {k: v['money'] for k, v in before['careers'].items()})
        self.assertEqual(out['journey']['titles'], before['journey']['titles'])
        self.assertEqual(before, s, 'the stored save is never changed in place')
        none = copy.deepcopy(before)
        none['journey']['equipped'] = None
        self.assertEqual(migrate_state(none)['journey']['worn'], [])

    def test_new_scene_title_goes_first(self):
        # "Đeo ngay" on a new title sends the list with it first (public/js/v4/journey.js jrEquip).
        s = self.owned()
        s, _ = act(s, 'jr_equip', worn=['g_first', 'k_careful', 'cert:accounting'])
        s, _ = act(s, 'jr_equip', worn=['x_streak10', 'g_first', 'k_careful'])
        self.assertEqual(s['journey']['equipped'], 'x_streak10')


class NameTags(unittest.TestCase):
    """live/street.py title_of: the honour first, then what is worn (the first by name, the rest by emoji)."""

    def tag(self, title=None, titles=None, race=None, lb_title=None):
        from live.street import StreetFeature
        wed = types.SimpleNamespace(race_title=lambda pid: race, enabled=lambda: True)
        fake = types.SimpleNamespace(app=types.SimpleNamespace(by_name={'wedding': wed}), lb={'s1': lb_title} if lb_title else {})
        player = types.SimpleNamespace(pid='p1', sid='s1')
        return StreetFeature.title_of(fake, player, title, titles)

    def test_compose(self):
        self.assertEqual(self.tag('g_first'), '🌱 Việc đầu tiên')
        self.assertEqual(self.tag('g_first', ['cert:accounting', 'g_first', 'x_streak10']), '🧮 Chứng chỉ Kế toán cơ bản 🌱✨')
        self.assertEqual(self.tag(None, ['g_first'], lb_title='👑 Trùm cuối của phố'), '👑 Trùm cuối của phố 🌱')
        self.assertEqual(self.tag(None, None, race='🥇 Khách quý của phố', lb_title='👑 Trùm cuối của phố'), '🥇 Khách quý của phố')
        self.assertEqual(self.tag('fake', ['nope', 5, 'g_first', 'k_calm', 'm_home', 'x_boss']), '🌱 Việc đầu tiên')   # the first 3 ids only
        self.assertIsNone(self.tag(None, []))

    def test_certificate_names_match_the_game(self):
        from game import certificates as ct
        from live import street_data as sd
        self.assertEqual(sd.CERTS, {f'{jr.CERT_WEAR}{g["id"]}': f'{g["emoji"]} {g["name"]}' for g in ct.GROUPS})


if __name__ == '__main__':
    unittest.main()
