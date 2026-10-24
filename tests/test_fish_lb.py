"""🎣 The fishing boards (game/fish_lb.py, owner 24/10): a kept fish writes fish_best (all time and its Vietnam week),
fish_rec (the species' town record: 🏆 on the card) and fish_dex (the collection) in the save's own transaction; a 🔴
Cổ đại catch posts one ticker line; GET /api/leaderboard?board=fish_big|fish_all|fish_dex (privacy, own place, the dex
tie-break: species, then rarer counts, then who got there first); GET /api/fish/records; an 🏝️ island cast needs the trip.
Weekly titles and rewards (game/lb_titles.py): the boards are in MAIN with their own titles, the Monday freeze pays the
tiered default once per (week, board, rank), never an admin or a hidden player; the frames' ids are a valid hf_pick and
public/js/v4/honours.js mirrors the titles."""
import os
import secrets
import unittest
from pathlib import Path
from unittest import mock

from game import fish_lb as FL
from game import fishing as F
from game import fishing_content as C
from game import lb_titles as lbt
from game import leaderboard as lb
from game import marriage as mr
from game import pg_schema
from game.engine import GameError, validate_state
from tests.test_bank import story
from tests.test_lb_titles import MON, SUN, at
from tests.test_leaderboard import Base

ROOT = Path(__file__).resolve().parents[1]
RED = C.by_rarity(6)[0]['id']


class Anglers(Base):
    def setUp(self):
        super().setUp()
        FL.clear_cache()
        lbt.clear_cache()
        lbt._done.clear()
        lbt._pending.clear()

    def angler(self, name):
        return self.player(story(wallet=1000), account=name)

    def catch(self, tok, sp, g, t=None):
        """A fish hooked ten seconds ago, landed now through the real command path."""
        t = t or F.now()
        token = secrets.token_hex(16)

        def put(s):
            d = F.ensure(s)
            d['act'] = dict(id=token, at=t - 30, spot='ho', trip='', rod='tre', dist=12.0, zone=0, kind='fish', sp=sp, g=g,
                            bite=t - 12, hook=t - 10, reel=4.0, snap=0, nib=[])
        mr._mutate(self.store, {self.sid(tok): put})
        with mock.patch.object(F, 'now', lambda: t), mock.patch.object(FL, 'now', lambda: t):
            out = self.cmd(tok, 'jr_fish_land', {'round': token, 'ok': True})
        FL.clear_cache()
        return out

    def rows(self, sql, *args):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute(sql, args)]


class Boards(Anglers):
    def test_a_catch_writes_best_record_and_collection(self):
        a, b = self.angler('An'), self.angler('Bình')
        out = self.catch(a, 'ca_chep', 3000)
        res = out.get('result', out)
        self.assertTrue(res['land']['catch']['rec'])
        self.assertIn('🏆 Kỷ lục loài của cả phố!', res['effects'])
        week = FL._week(F.now())
        best = {r['week']: (r['sp'], r['g']) for r in self.rows('SELECT week, sp, g FROM fish_best WHERE sid=?', self.sid(a))}
        self.assertEqual(best, {'all': ('ca_chep', 3000), week: ('ca_chep', 3000)})
        self.catch(a, 'ca_ro', 200)   # lighter: the best stays, the collection grows
        self.assertEqual(self.rows('SELECT g FROM fish_best WHERE sid=? AND week=?', self.sid(a), 'all')[0]['g'], 3000)
        self.assertEqual(self.rows('SELECT n FROM fish_dex WHERE sid=?', self.sid(a))[0]['n'], 2)
        res = self.catch(b, 'ca_chep', 4000)
        self.assertTrue(res.get('result', res)['land']['catch']['rec'])
        self.assertEqual(self.rows('SELECT sid, g FROM fish_rec WHERE sp=?', 'ca_chep')[0], dict(sid=self.sid(b), g=4000))
        res = self.catch(a, 'ca_chep', 3500)   # not a record any more
        self.assertNotIn('rec', res.get('result', res)['land']['catch'])
        recs = FL.records(self.store, a)
        self.assertEqual(recs['records']['ca_chep'], dict(g=4000, name='Bình', me=False))
        self.assertEqual([r['name'] for r in recs['tops']['fish_big']], ['Bình', 'An'])

    def test_an_ancient_catch_posts_once(self):
        a = self.angler('An')
        self.catch(a, RED, C.grams(C.SPECIES[RED]['w'][0]))
        news = self.rows("SELECT text FROM news WHERE kind='fish'")
        self.assertEqual(len(news), 1)
        self.assertIn(C.SPECIES[RED]['name'], news[0]['text'])

    def test_ancient_lines_are_spaced_on_the_ticker(self):
        # 2.6.5: Cổ đại comes often on the best rods; one fish line per 10 minutes, one a player an hour
        a, b = self.angler('An'), self.angler('Bình')
        g = C.grams(C.SPECIES[RED]['w'][0])
        self.catch(a, RED, g)
        self.catch(b, RED, g)   # within 10 minutes of An's line: no line
        self.assertEqual(len(self.rows("SELECT id FROM news WHERE kind='fish'")), 1)
        later = F.now() + FL.NEWS_GAP_S + 5
        with mock.patch.object(FL, 'now', return_value=later), self.store.connect() as db:
            self.assertTrue(FL._news_room(db, self.sid(b)))    # Bình: room again after the gap
            self.assertFalse(FL._news_room(db, self.sid(a)))   # An: not before an hour
        self.catch(b, RED, g, t=later)
        self.assertEqual(len(self.rows("SELECT id FROM news WHERE kind='fish'")), 2)

    def test_views_privacy_and_order(self):
        a, b, c = self.angler('An'), self.angler('Bình'), self.angler('Chi')
        self.catch(a, 'ca_chep', 3000)
        self.catch(b, 'ca_chep', 5000)
        self.catch(c, 'ca_tram', 9000)
        lb.set_visible(self.store, c, self.store.read(c)[0], False)
        FL.clear_cache()
        v = FL.view(self.store, 'fish_big', 10, a)
        self.assertEqual([(r['name'], r['score'], r['sp']) for r in v['rows']], [('Bình', 5000, 'ca_chep'), ('An', 3000, 'ca_chep')])
        self.assertEqual(v['me']['rank'], 2)
        self.assertIsNotNone(v['weekly'])
        hidden = FL.view(self.store, 'fish_big', 10, c)
        self.assertEqual(hidden['me']['rank'], 1, 'a hidden player still sees his own place')
        self.assertIsNone(FL.view(self.store, 'fish_all', 10, a)['weekly'])
        self.assertEqual(lb.parse_query({'board': 'fish_dex'}), ('fish_dex', lb.LIMIT))

    def test_collection_tie_break(self):
        a, b, c = self.angler('An'), self.angler('Bình'), self.angler('Chi')
        hiem = C.by_rarity(3)[0]['id']
        t = F.now()
        self.catch(a, 'ca_ro', 200, t - 100)
        self.catch(a, 'ca_chep', 2000, t - 90)
        self.catch(b, 'ca_ro', 200, t - 80)
        self.catch(b, hiem, C.grams(C.SPECIES[hiem]['w'][0]), t - 70)   # same count, a rarer one: above
        self.catch(c, 'ca_ro', 200, t - 200)
        self.catch(c, 'ca_chep', 2000, t - 150)                        # same as An, earlier: above An
        v = FL.view(self.store, 'fish_dex', 10, a)
        self.assertEqual([r['name'] for r in v['rows']], ['Bình', 'Chi', 'An'])
        self.assertEqual(v['rows'][0]['rc'][3], 1)
        self.assertGreater(FL.key_of(2, [1, 0, 0, 1, 0, 0, 0]), FL.key_of(2, [1, 1, 0, 0, 0, 0, 0]))
        self.assertGreater(FL.key_of(3, [3, 0, 0, 0, 0, 0, 0]), FL.key_of(2, [0, 0, 0, 0, 0, 0, 2]))

    def test_an_island_cast_needs_the_trip(self):
        a = self.angler('An')
        before = self.store.read(a)[0]['journey'].get('fish')
        with self.assertRaises(GameError) as e:
            self.cmd(a, 'jr_fish_cast', {'spot': 'dao', 'power': 0.5, 'trip': 'ab' * 8})
        self.assertEqual(e.exception.code, 'no_island')
        self.assertEqual(self.store.read(a)[0]['journey'].get('fish'), before, 'rolled back')
        self.cmd(a, 'jr_fish_cast', {'spot': 'ho', 'power': 0.5})

    def test_forget(self):
        a = self.angler('An')
        self.catch(a, 'ca_chep', 3000)
        self.store.transaction(lambda db: FL.forget(db, self.sid(a)))
        self.assertFalse(self.rows('SELECT 1 FROM fish_best'))
        self.assertFalse(self.rows('SELECT 1 FROM fish_rec'))


class Weekly(Anglers):
    def setUp(self):
        super().setUp()
        for p in (mock.patch.object(lbt, 'now', return_value=at(2026, 9, 1, 12)), mock.patch.object(lbt, 'REWARD_FROM', '2026-W40')):
            p.start()
            self.addCleanup(p.stop)

    def gifts(self):
        return {r['id']: r for r in self.rows("SELECT id, sid, coins FROM system_gifts WHERE id LIKE 'lbw-%-fish_%'")}

    def username(self, tok):
        return self.rows('SELECT username FROM accounts WHERE sid=?', self.sid(tok))[0]['username']

    def test_titles_freeze_and_pay_once_never_admins_or_hidden(self):
        a, b, c, d = self.angler('An'), self.angler('Bình'), self.angler('Chi'), self.angler('Dũng')
        self.catch(a, 'ca_tram', 9000, SUN - 3600)
        self.catch(b, 'ca_chep', 5000, SUN - 3000)
        self.catch(c, 'ca_chep', 4000, SUN - 2000)
        self.catch(d, 'ca_ro', 300, SUN - 1000)
        self.catch(d, 'ca_chep', 300, SUN - 900)
        lb.set_visible(self.store, c, self.store.read(c)[0], False)
        env = mock.patch.dict(os.environ, {'ADMIN_USERS': self.username(b)})
        env.start()
        self.addCleanup(env.stop)
        lbt.refresh(self.store, SUN)
        self.assertFalse(self.gifts(), 'a daily refresh pays nothing')
        self.assertTrue(lbt.refresh(self.store, MON))
        g = self.gifts()
        self.assertEqual((g['lbw-2026-W40-fish_big-1']['sid'], g['lbw-2026-W40-fish_big-1']['coins']), (self.sid(a), 1_000_000))
        self.assertEqual(g['lbw-2026-W40-fish_dex-1']['sid'], self.sid(d))
        paid = {r['sid'] for r in g.values()}
        self.assertNotIn(self.sid(b), paid, 'an admin')
        self.assertNotIn(self.sid(c), paid, 'a hidden player')
        self.assertEqual({lbt.reward_of('fish_big', r) for r in (1, 2, 4, 11)}, {1_000_000, 500_000, 200_000, 0})
        n = len(g)
        lbt._done.clear()
        self.assertFalse(lbt.refresh(self.store, MON + 120))
        self.assertEqual(self.store.transaction(lambda db: lbt.reward_week(db, '2026-W40', MON)), 0)
        self.assertEqual(len(self.gifts()), n)
        final = {(r['board'], r['rank']) for r in self.rows("SELECT board, rank FROM lb_weekly WHERE final=1 AND week='2026-W40' AND board LIKE 'fish_%'")}
        self.assertIn(('fish_big', 1), final)


class Names(unittest.TestCase):
    def test_titles_frames_and_mirror(self):
        self.assertIn('fish_big', lbt.MAIN)
        self.assertIn('fish_dex', lbt.NEW_BOARDS)
        self.assertEqual(lbt.title_of('fish_big', 1)['text'], '🐋 Vua cá lớn của tuần')
        self.assertEqual(lbt.title_of('fish_dex', 1)['text'], '📖 Nhà sưu tập cá của tuần')
        others = {n for b, ts in lbt.BOARD_TITLES.items() if b not in ('fish_big', 'fish_dex') for _, n in ts}
        self.assertFalse(others & {n for b in ('fish_big', 'fish_dex') for _, n in lbt.BOARD_TITLES[b]}, 'their own names')
        js = (ROOT / 'public/js/v4/honours.js').read_text(encoding='utf-8')
        for b in ('fish_big', 'fish_dex'):
            for e, n in lbt.BOARD_TITLES[b]:
                self.assertIn(n, js)
        frames = (ROOT / 'public/js/v4/honour-frames.js').read_text(encoding='utf-8')
        self.assertIn("fish_big:[['🐋'", frames.replace(' ', ''))
        self.assertIn('fish_dex:', frames)

    def test_frame_ids_and_titles_pass_validate_state(self):
        from game import spend as sp
        from game.spend_content import PERMANENT
        for v in ('lb_fish_big_1', 'lb_fish_big_10', 'lb_fish_dex_3', 't_ca_than_cau'):
            s = story()
            s['journey']['hf_pick'] = v
            validate_state(s)
        s = story()
        own = sp._ensure(s)['own']
        for t in C.STYLE_TITLES + C.STYLE_FRAMES:
            own[t['id']] = PERMANENT
        validate_state(s)

    def test_schema_93(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 93)   # the fish tables came with 93; later schemas keep them
        names = [t['name'] for t in pg_schema.TABLES]
        for t in ('fish_best', 'fish_dex', 'fish_rec'):
            self.assertIn(t, names)
            self.assertIn(f'CREATE TABLE IF NOT EXISTS {t}', pg_schema.TABLES_DDL)


if __name__ == '__main__':
    unittest.main()
