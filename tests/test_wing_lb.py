"""🪽 Cánh on the main Bảng xếp hạng (game/wing_lb.py, owner 23/10: "có hạng cánh nữa nhé, xếp hạng cánh ấy"): the điểm
cánh of a save, the wing_board row written in the save's own transaction by every jr_pet_wing_* command (⚡ Cường hóa nhanh
included) and healed by any other pet command, the order, the boards' privacy, the viewer's own place, the per-process
cache, the weekly titles, SCHEMA_VERSION 91 (a new table and an index, idempotent), scripts/backfill_wing_board.py on a test
database (by primary key, dry run, idempotent), and 2.5.6 (the release before) running on a database at 91."""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from unittest import mock

from game import lb_titles as lbt
from game import leaderboard as lb
from game import pg_schema
from game import wing_lb as WL
from game import wings as W
from game.engine import validate_state
from tests import test_lb_titles as T
from tests import test_marriage as M
from tests.test_bank import story
from tests.test_lb_titles import SUN, with_titles
from tests.test_wings import owned, rolls

ROOT = Path(__file__).resolve().parents[1]
RELEASE = '7e7431ab'   # 2.5.6, the release live before this board (schema 90, no wing_board)


def wing_save(*tiers, on=None, style='thien_than'):
    s, ids = owned(story(wallet=10**6), *tiers, style=style)
    if on is not None:
        W.get(s)['on'] = ids[on]
    validate_state(s)
    return s, ids


class Score(T.unittest.TestCase):
    def test_points_are_three_to_the_tier(self):
        self.assertEqual(WL.POINTS, tuple(3 ** r for r in range(8)))
        self.assertEqual(len(WL.POINTS), len(__import__('game.wings_content', fromlist=['TIERS']).TIERS))
        self.assertIsNone(WL.score(story()))
        s, _ = wing_save(0, 0, 1, 4, 7, 6, 6)
        self.assertEqual(WL.score(s), dict(pts=1 + 1 + 3 + 81 + 2187 + 729 * 2, best=7, k='thien_than', n=[2, 1, 0, 0, 1, 0, 2, 1]))

    def test_a_fusion_that_works_keeps_the_points_and_a_higher_tier_always_weighs_more(self):
        s, ids = wing_save(2, 2, 2)
        before = WL.score(s)['pts']
        w = W.get(s)
        xs = [next(x for x in w['own'] if x['id'] == i) for i in ids]
        with rolls(0):
            self.assertTrue(W._fuse_three(w, xs[0], xs[1:]))
        self.assertEqual(WL.score(s), dict(pts=before, best=3, k='thien_than', n=[0, 0, 0, 1, 0, 0, 0, 0]))
        for r in range(1, 8):   # one wing of a tier beats two of the tier below and anything less than three
            self.assertGreater(WL.POINTS[r], 2 * WL.POINTS[r - 1])

    def test_the_best_wing_is_the_worn_one_of_the_best_tier_else_the_dearest(self):
        s, ids = owned(story(wallet=10**6), 5, 5, style='buom')
        t, more = owned(s, 5, style='phuong')
        W.get(t)['on'] = ids[1]
        self.assertEqual((WL.score(t)['best'], WL.score(t)['k']), (5, 'buom'))   # the worn one
        W.get(t)['on'] = None
        self.assertEqual(WL.score(t)['k'], 'phuong')                            # the dearest style
        W.get(t)['own'].append(dict(id='w99', k='newer_style', r=6, z=1))       # a newer build's style: still counted
        W.get(t)['seq'] = 100
        self.assertEqual((WL.score(t)['best'], WL.score(t)['k']), (6, 'newer_style'))

    def test_reached_is_the_newest_tier_time(self):
        s, _ = wing_save(0, 3)
        W.get(s)['own'][1]['z'] = 1_800_000_000
        self.assertEqual(WL.reached(s), 1_800_000_000.0)
        self.assertEqual(WL.reached(story()), 0.0)


class Commands(M.Base):
    """The row follows the save, written in the save's own transaction (game/pets.py command_commit)."""

    def setUp(self):
        super().setUp()
        self.tok = self.user('wing_lb', wallet=10**9)
        self.s = self.sid(self.tok)
        self.k = 0

    def run_cmd(self, action, **p):
        self.k += 1
        return self.store.command(self.tok, f'wlb-{action}-{self.k}-{os.urandom(3).hex()}', self.store.read(self.tok)[1], None, action, p)

    def row(self, sid=None):
        with self.store.connect() as db:
            r = db.execute('SELECT pts, best, k, n, at FROM wing_board WHERE sid=?', (sid or self.s,)).fetchone()
        return dict(pts=int(r['pts']), best=int(r['best']), k=r['k'], n=json.loads(r['n']), at=float(r['at'])) if r else None

    def same(self):
        want = WL.score(self.store.read(self.tok)[0])
        got = self.row()
        if want is None:
            self.assertIsNone(got)
        else:
            got.pop('at')
            self.assertEqual(got, want)

    def test_every_wing_command_writes_the_row(self):
        self.assertIsNone(self.row())
        with rolls(0, 0, 0, 0, 0, 0):
            self.run_cmd('jr_pet_wing_buy', style='rong', qty=6, confirm=True)        # six D
        self.assertEqual(self.row()['pts'], 6)
        self.same()
        at0 = self.row()['at']
        self.run_cmd('jr_pet_wing_wear', id='w3')
        self.same()
        self.assertEqual(self.row()['at'], at0, 'the points did not move: when they were reached stays')
        with rolls(0):
            self.run_cmd('jr_pet_wing_fuse', wings=['w1', 'w2', 'w3'], confirm=True)
        self.same()
        self.assertEqual((self.row()['pts'], self.row()['best']), (6, 1))
        with rolls(0, 0, 0, 0, 0, 0, 0, 0):                                           # ⚡ Cường hóa nhanh
            self.run_cmd('jr_pet_wing_fuse_auto', budget=10**7, confirm=True)
        self.same()
        self.assertEqual((self.row()['pts'], self.row()['n']), (6, [0, 2, 0, 0, 0, 0, 0, 0]), 'three D fused: two C')
        with rolls(9999):
            self.run_cmd('jr_pet_wing_buy', style='buom', confirm=True)
        self.same()
        for x in list(W.get(self.store.read(self.tok)[0])['own']):
            self.run_cmd('jr_pet_wing_drop', id=x['id'], confirm=True)
            self.same()
        self.assertIsNone(self.row(), 'the last wing gone: no row')

    def test_the_row_is_in_the_saves_transaction(self):
        with rolls(0):
            self.run_cmd('jr_pet_wing_buy', style='rong', confirm=True)
        rev = self.store.read(self.tok)[1]
        with mock.patch.object(WL, 'write', side_effect=RuntimeError('boom')), self.assertRaises(Exception):
            with rolls(0):
                self.run_cmd('jr_pet_wing_buy', style='rong', confirm=True)
        self.assertEqual(self.store.read(self.tok)[1], rev, 'the save was not stored either')
        self.assertEqual(self.row()['pts'], 1)

    def test_another_pet_command_heals_a_missing_row_and_a_wingless_save_writes_nothing(self):
        with mock.patch.object(WL, 'write', wraps=WL.write) as w:
            self.run_cmd('jr_pet_adopt', **{'from': 'shop', 'breed': 'samoyed', 'coat': 0, 'nick': 'Mây', 'qty': 1, 'confirm': True})
        self.assertFalse(w.called, 'never had a wing: no statement')
        with rolls(9999, 9999):
            self.run_cmd('jr_pet_wing_buy', style='tien', qty=2, confirm=True)
        self.store.transaction(lambda db: db.execute('DELETE FROM wing_board WHERE sid=?', (self.s,)))   # as an older build left it
        self.run_cmd('jr_pet_adopt', **{'from': 'shop', 'breed': 'samoyed', 'coat': 0, 'nick': 'Bông', 'qty': 1, 'confirm': True})
        self.same()
        self.assertEqual(self.row()['pts'], 6)

    def test_erasing_the_data_removes_the_row(self):
        with rolls(0):
            self.run_cmd('jr_pet_wing_buy', style='rong', confirm=True)
        self.store.transaction(lambda db: W.forget(db, self.s))
        self.assertIsNone(self.row())


def put(store, sid, pts, best=0, k='thien_than', at=1.0, n=None):
    n = n or [0] * 8
    store.transaction(lambda db: db.execute('INSERT INTO wing_board(sid, pts, best, k, n, at) VALUES(?,?,?,?,?,?) ON CONFLICT (sid) DO UPDATE '
                                            'SET pts=EXCLUDED.pts, best=EXCLUDED.best, k=EXCLUDED.k, n=EXCLUDED.n, at=EXCLUDED.at',
                                            (sid, pts, best, k, json.dumps(n), at)))


class Board(T.Weekly):   # (the module, not the class: pytest would run Weekly's own tests here again)
    def setUp(self):
        super().setUp()
        WL.clear_cache()
        self.addCleanup(WL.clear_cache)

    def wing(self, token, pts, best=0, at=1.0, k='rong', n=None):
        put(self.store, self.sid(token), pts, best, k, at, n)
        WL.clear_cache()

    def test_query_and_titles(self):
        self.assertEqual(lb.parse_query({'board': 'wings'}), ('wings', 50))
        self.assertEqual(lbt.title_of('wings', 1)['text'], '🪽 Đôi cánh số 1 phố')
        self.assertEqual(lbt.title_of('wings', 3)['name'], 'Cánh thần thoại')
        self.assertEqual(lbt.title_of('wings', 10)['name'], 'Hội chắp cánh')
        self.assertIsNone(lbt.title_of('wings', 11))
        self.assertIn('wings', lbt.MAIN)
        self.assertIn('wings', lbt.NEW_BOARDS, "2.5.6's daily refresh drops it: healed")
        js = (ROOT / 'public/js/v4/honour-frames.js').read_text(encoding='utf-8')
        self.assertIn("wings:['36','57','27']", js, 'its frames (else the top 1 would wear a workplace "Trùm" frame)')

    def test_order_privacy_me_and_cache(self):
        a = self.player(with_titles(1), account='An')
        b = self.player(with_titles(1), account='Bình')
        c = self.player(with_titles(1), account='Chi')
        g = self.player(with_titles(1))                       # a guest who never opted in: counted for nobody, never named
        self.wing(a, 300, 4, at=5.0)
        self.wing(b, 2187, 7, k='phuong', n=[0, 0, 0, 0, 0, 0, 0, 1])
        self.wing(c, 300, 4, at=2.0)                          # same points and tier as An, earlier: ahead
        d = self.player(with_titles(1), account='Dũng')
        self.wing(d, 300, 5, at=9.0)                          # same points, a better tier: ahead of both
        self.wing(g, 10**6, 7)
        v = lb.view(self.store, 'wings', 50, a)
        self.assertEqual([(r['name'], r['score'], r['rank'], r['me']) for r in v['rows']],
                         [('Bình', 2187, 1, False), ('Dũng', 300, 2, False), ('Chi', 300, 3, False), ('An', 300, 4, True)])
        top = v['rows'][0]
        self.assertEqual((top['wg'], top['n']), (dict(k='phuong', r=7), [0, 0, 0, 0, 0, 0, 0, 1]))
        self.assertNotIn('sid', top)
        self.assertEqual(v['total'], 4)
        self.assertEqual((v['me']['rank'], v['me']['score'], v['me']['wg']), (4, 300, dict(k='rong', r=4)))
        # cached a while per process; the viewer's own place is read live
        self.wing(a, 5000, 6)
        self.assertEqual(lb.view(self.store, 'wings', 50, a)['rows'][0]['name'], 'An')
        put(self.store, self.sid(c), 9000, 6)                 # not cleared: the cached top stays
        v = lb.view(self.store, 'wings', 50, a)
        self.assertEqual(v['rows'][0]['name'], 'An')
        self.assertEqual(v['me']['rank'], 2, 'read live: Chi is ahead already')
        with mock.patch.object(WL.time, 'monotonic', return_value=WL.time.monotonic() + WL.CACHE_SECONDS + 1):
            self.assertEqual(lb.view(self.store, 'wings', 50, a)['rows'][0]['name'], 'Chi')
        # hidden: off the board, still told where they would stand
        WL.clear_cache()
        lb.set_visible(self.store, c, self.store.read(c)[0], False)
        WL.clear_cache()
        v = lb.view(self.store, 'wings', 50, c)
        self.assertEqual([r['name'] for r in v['rows']], ['An', 'Bình', 'Dũng'])
        self.assertEqual(v['me']['rank'], 1)
        self.assertFalse(v['me']['visible'])
        e = self.player(with_titles(1), account='Em')         # no wing yet
        self.assertIsNone(lb.view(self.store, 'wings', 50, e)['me']['rank'])
        self.assertEqual(len(lb.view(self.store, 'wings', 2, e)['rows']), 2)

    def test_weekly_titles(self):
        a = self.player(with_titles(1), account='An')
        b = self.player(with_titles(1), account='Bình')
        self.wing(a, 100, 3)
        self.wing(b, 200, 4)
        self.assertTrue(lbt.refresh(self.store, SUN))
        self.assertIn(('wings', 1), self.holders()['Bình'])
        self.assertIn(('wings', 2), self.holders()['An'])
        v = lb.view(self.store, 'wings', 50, a)
        self.assertEqual(v['rows'][0]['title'], dict(emoji='🪽', name='Đôi cánh số 1 phố'))
        self.assertEqual(v['weekly']['tiers'][0]['holders'][0]['name'], 'Bình')
        # 2.5.6's refresh rewrites the current holders of the boards it knows: the next heal brings the wings' back
        self.store.transaction(lambda db: db.execute("DELETE FROM lb_weekly WHERE final=0 AND board='wings'"))
        lbt.clear_cache()
        self.assertTrue(lbt.heal(self.store, SUN))
        self.assertIn(('wings', 1), self.holders()['Bình'])


class Schema(M.Base):
    def catalog(self):
        with self.store.connect() as db:
            t = sorted(r[0] for r in db.execute('SELECT tablename FROM pg_tables WHERE schemaname=current_schema()').fetchall())
            i = sorted(r[0] + ':' + r[1] for r in db.execute('SELECT indexname, indexdef FROM pg_indexes WHERE schemaname=current_schema()').fetchall())
        return t, i

    def test_91_is_a_new_table_and_an_index_idempotent(self):
        import re
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 91)
        self.assertIn('SCHEMA_VERSION = 91  # 91: 🪽 wing_board', open(pg_schema.__file__, encoding='utf-8').read())
        names = [t['name'] for t in pg_schema.TABLES]
        self.assertLess(names.index('wing_board'), names.index('mnl_meta'))
        ddl = pg_schema.TABLES_DDL
        part = ddl[ddl.index('CREATE TABLE IF NOT EXISTS wing_board'):]
        part = part[:part.index(';', part.index('CREATE INDEX IF NOT EXISTS wing_board_rank')) + 1]
        self.assertNotIn('REFERENCES', part, 'no FK')
        self.assertFalse(re.search(r'\b(ALTER|DROP|UPDATE|INSERT)\b', part), 'a new table and an index only, no backfill')
        before = self.catalog()
        self.assertIn('wing_board', before[0])
        self.assertTrue(any(x.startswith('wing_board_rank:') for x in before[1]))
        with self.store.connect() as db:
            db.execute('DROP TABLE wing_board')
            db.execute("UPDATE mnl_meta SET value='90' WHERE key='schema_version'")
        with self.store.connect() as db:
            self.assertTrue(pg_schema.ensure(db))
            self.assertFalse(pg_schema.ensure(db))
            self.assertEqual(pg_schema.installed_version(db), pg_schema.SCHEMA_VERSION)
            self.assertTrue(pg_schema.ensure(db, force=True))   # everything again: nothing changes
        self.assertEqual(self.catalog(), before)


def backfill_module():
    spec = importlib.util.spec_from_file_location('backfill_wing_board', ROOT / 'scripts' / 'backfill_wing_board.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Backfill(M.Base):
    def test_fills_the_wearers_by_primary_key_dry_run_first_and_again_changes_nothing(self):
        B = backfill_module()
        src = (ROOT / 'scripts' / 'backfill_wing_board.py').read_text(encoding='utf-8')
        for line in src.splitlines():   # never a scan of the big saves table: every read of it is by its key
            if 'FROM sessions' in line:
                self.assertIn('WHERE sid=?', line)
        toks = [self.user(f'wbf{i}', wallet=10**7) for i in range(4)]
        for i, tok in enumerate(toks[:3]):
            with rolls(*[0 if j % 2 else 9999 for j in range(i + 2)]):
                self.store.command(tok, f'wbf-buy-{i:04d}', self.store.read(tok)[1], None, 'jr_pet_wing_buy', dict(style='rong', qty=i + 2, confirm=True))
        # toks[2] took its wings off: not in wing_worn, left to its next command
        self.store.command(toks[2], 'wbf-off-0001', self.store.read(toks[2])[1], None, 'jr_pet_wing_wear', dict(id=None))
        sids = [self.sid(t) for t in toks]
        want = {s: WL.score(self.store.read(t)[0]) for s, t in zip(sids, toks)}
        self.store.transaction(lambda db: db.execute('DELETE FROM wing_board'))   # as before 2.5.7
        put(self.store, sids[1], 1, 0)                                             # one row there already: kept
        with self.store.connect() as db:
            revs = {s: db.execute('SELECT revision, state FROM sessions WHERE sid=?', (s,)).fetchone() for s in sids}
        logs = []
        out = B.run(self.store, dry_run=True, batch=1, pause=0, log=logs.append)
        self.assertEqual(out, dict(seen=2, had=1, written=1, none=0, gone=0))
        self.assertTrue(logs)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM wing_board').fetchone()[0], 1, 'dry run: nothing written')
        out = B.run(self.store, batch=1, pause=0, log=logs.append)
        self.assertEqual(out['written'], 1)
        with self.store.connect() as db:
            r = db.execute('SELECT pts, best, k, n, at FROM wing_board WHERE sid=?', (sids[0],)).fetchone()
            self.assertEqual(dict(pts=r['pts'], best=r['best'], k=r['k'], n=json.loads(r['n'])), want[sids[0]])
            self.assertGreater(r['at'], 0)
            self.assertEqual(db.execute('SELECT pts FROM wing_board WHERE sid=?', (sids[1],)).fetchone()[0], 1, 'kept (no --force)')
            self.assertIsNone(db.execute('SELECT 1 FROM wing_board WHERE sid=?', (sids[2],)).fetchone())
            for s in sids:
                self.assertEqual(tuple(db.execute('SELECT revision, state FROM sessions WHERE sid=?', (s,)).fetchone()), tuple(revs[s]), 'saves untouched')
        self.assertEqual(B.run(self.store, batch=10, pause=0, log=logs.append)['written'], 0, 'again: nothing to do')
        self.assertEqual(B.run(self.store, batch=10, pause=0, force=True, log=logs.append)['written'], 2)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT pts FROM wing_board WHERE sid=?', (sids[1],)).fetchone()[0], want[sids[1]]['pts'])

    def test_refuses_a_database_before_91(self):
        B = backfill_module()
        with self.store.connect() as db:
            db.execute("UPDATE mnl_meta SET value='90' WHERE key='schema_version'")
        env = dict(os.environ, PYTHONUTF8='1')
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'backfill_wing_board.py'), '--namespace', self.store.path, '--dry-run'],
                           capture_output=True, text=True, encoding='utf-8', env=env, cwd=ROOT, timeout=120)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('cần 91', r.stderr)
        with self.store.connect() as db:
            self.assertEqual(pg_schema.installed_version(db), 90, 'no DDL run by the script')
        self.assertTrue(B.NEED == 91)


OLD = r'''import json,sys
from game.storage import Store
store=Store(sys.argv[1], story=True)
tok=sys.argv[2]
out={}
with store.connect() as db:
    out['v']=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
r=store.command(tok,'old-wing-buy',store.read(tok)[1],None,'jr_pet_wing_buy',{'style':'phuong','qty':2,'confirm':True})
r=store.command(tok,'old-wing-off',store.read(tok)[1],None,'jr_pet_wing_wear',{'id':None})
import game;out['version']=game.__version__
store.close_pool()
print(json.dumps(out))
'''


class Rollback(M.Base):
    """2.5.6 (`git archive 7e7431ab`) on a database at SCHEMA_VERSION 91: its startup runs no DDL and never lowers the
    version, its wing commands work and leave wing_board as it was (it never reads or writes it), and back on this
    build the player's next pet command heals the row."""

    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-256-')
        self.addCleanup(__import__('shutil').rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {RELEASE}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def catalog(self):
        with self.store.connect() as db:
            t = sorted(r[0] for r in db.execute('SELECT tablename FROM pg_tables WHERE schemaname=current_schema()').fetchall())
            i = sorted(r[0] + ':' + r[1] for r in db.execute('SELECT indexname, indexdef FROM pg_indexes WHERE schemaname=current_schema()').fetchall())
        return t, i

    def test_256_on_91(self):
        tok = self.user('wing_old', wallet=10**7)
        sid = self.sid(tok)
        with rolls(0, 0):
            self.store.command(tok, 'new-buy-0001', self.store.read(tok)[1], None, 'jr_pet_wing_buy', dict(style='rong', qty=2, confirm=True))
        with self.store.connect() as db:
            row = tuple(db.execute('SELECT pts, best, k, n, at FROM wing_board WHERE sid=?', (sid,)).fetchone())
        self.assertEqual(row[0], 2)
        before = self.catalog()
        old = self.old_tree()
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        env.pop('MNL_CAREERS', None)
        r = subprocess.run([sys.executable, '-c', OLD, str(self.store.path), tok], capture_output=True, text=True, cwd=old, env=env,
                           encoding='utf-8', timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-3000:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got['version'], '2.5.6')
        self.assertEqual(int(got['v']), pg_schema.SCHEMA_VERSION)
        self.assertEqual(self.catalog(), before, 'no table or index changed by the old startup')
        with self.store.connect() as db:
            self.assertEqual(pg_schema.installed_version(db), 91, 'never lowered')
            self.assertEqual(tuple(db.execute('SELECT pts, best, k, n, at FROM wing_board WHERE sid=?', (sid,)).fetchone()), row,
                             'untouched by 2.5.6')
        s = self.store.read(tok)[0]
        self.assertEqual(len(W.get(s)['own']), 4, "2.5.6's wings are in the save")
        self.store.command(tok, 'new-wear-001', self.store.read(tok)[1], None, 'jr_pet_wing_wear', dict(id='w1'))
        want = WL.score(self.store.read(tok)[0])
        with self.store.connect() as db:
            r = db.execute('SELECT pts, best, k, n FROM wing_board WHERE sid=?', (sid,)).fetchone()
        self.assertEqual(dict(pts=r['pts'], best=r['best'], k=r['k'], n=json.loads(r['n'])), want)
        self.assertGreaterEqual(want['pts'], 4)


if __name__ == '__main__':
    T.unittest.main()
