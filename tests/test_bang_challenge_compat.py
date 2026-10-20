"""⚔️ Thách đấu bang and rollbacks: nothing of it is in a save, and the release live before it (2.4.65 at cfc6eb7e) runs on a
database at SCHEMA_VERSION 62 (61: the challenge tables, 62: the 🏝️ bangs.isle columns) with challenges played and an
island bought, an upgrade building and a bang without one: its startup runs no DDL (same tables, same indexes, the version
never lowered, rows kept), its bang pages, lists and ranking and its arena read the database as they did (the 'chal'
điểm cống hiến rows and the 'chal' log lines included), and its arena refuses the new ops gracefully."""
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import io
from pathlib import Path

from game import pg_schema
from tests.test_bang_challenge import Base

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'cfc6eb7e'   # 2.4.65 (live): schema 60, no challenge tables, no island columns

OLD = '''import json,sys
from game.storage import Store
from game import bang, pet_arena as A, pet_war
store=Store(sys.argv[1])
tok=sys.argv[2]
sid=store.key(tok)
out={}
with store.connect() as db:
    out['v']=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    out['n']={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[3].split(',')}
    out['scores']=bang.scores(db, bang.vn_week(bang.now()))
p=bang.page(store, sid)
out['page']=[p['member'], len(p['members']), len(p['log'])]
out['search']=len(bang.search(store, None))
out['board']=len(bang.board(store)['top'])
st=store.read(tok)[0]
v=A.act(store, tok, 'view', {}, st, '1.1.1.1')
out['view']=[v.get('locked'), len(v.get('team') or [])]
out['war']=A.act(store, tok, 'war', {}, None, '1.1.1.1')['team']['kind']
try:
    A.act(store, tok, 'tc', {}, None, '1.1.1.1')
    out['tc']='?'
except A.ArenaError as e:
    out['tc']=e.code
with store.connect() as db:
    A.on_pet_commit(db, sid, st)
store.close_pool()
print(json.dumps(out))
'''
TABLES = ('bang_chal', 'bang_chal_team', 'bang_chal_roster', 'pet_power', 'bang_points')


class OldRelease(Base):
    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-chal-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {RELEASE}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def run_old(self, *args):
        old = self.old_tree()
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', OLD, *args], capture_output=True, text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout.strip().splitlines()[-1])

    def catalog(self):
        with self.store.connect() as db:
            t = sorted(r[0] for r in db.execute('SELECT tablename FROM pg_tables WHERE schemaname=current_schema()').fetchall())
            i = sorted(r[0] + ':' + r[1] for r in db.execute('SELECT indexname, indexdef FROM pg_indexes WHERE schemaname=current_schema()').fetchall())
        return t, i

    def test_live_release_on_schema_62_with_challenges_played(self):
        a, b, ba, bb = self.two()
        cid = self.send(a[0], bb)['chal']['id']
        self.tc(b[0], 'tc_answer', id=cid, ok=True)
        self.send(b[0], ba)                                             # one still open
        for t in a[:2]:                                                 # 💪 pet_power rows
            self.tc(t, 'view')
        self.sql('UPDATE bangs SET isle=2, isle_to=3, isle_started=?, isle_ready=?, isle_paid=?, isle_how=? WHERE id=?',
                 (self.t[0], self.t[0] + 3600, 60_000_000, 'buy', ba))       # 🏝️ one building its next level…
        self.sql("UPDATE bangs SET isle=0, isle_how='' WHERE id=?", (bb,))  # …one without an island (founded from 21/10)
        before = self.catalog()
        with self.store.connect() as db:
            n = {x: db.execute(f'SELECT COUNT(*) AS n FROM {x}').fetchone()['n'] for x in TABLES}
        self.assertTrue(all(n.values()), n)
        saves = {t: self.store.read(t) for t in a + b}
        got = self.run_old(str(self.store.path), a[0], ','.join(TABLES))
        self.assertEqual(int(got['v']), pg_schema.SCHEMA_VERSION)
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 62)   # later steps (63+: other features) keep these tables as they are
        self.assertEqual(got['n'], n, 'rows kept')
        self.assertEqual(self.catalog(), before, 'no table or index changed by the old startup')
        self.assertEqual(len(got['scores']), 2)
        self.assertEqual(got['page'][:2], [True, 5])
        self.assertEqual((got['search'], got['board']), (2, 2))
        self.assertEqual(got['view'], [None, 1])
        self.assertEqual(got['war'], 'bang')
        self.assertEqual(got['tc'], 'unknown', 'the old arena refuses the new ops gracefully')
        for t in a + b:
            self.assertEqual(self.store.read(t)[1], saves[t][1], 'the old build wrote no save either')
        # and this build carries on with what is there
        v = self.tc(a[0], 'tc')
        self.assertEqual(len(v['roster']), 5)
        self.assertEqual(v['mine']['w'] + v['mine']['l'] + v['mine']['d'], 1)
