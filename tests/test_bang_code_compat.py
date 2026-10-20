"""📜 Nội quy bang and rollbacks: nothing of it is in a save, and the release live before it (2.4.66 at a808cb79) runs on
a database at SCHEMA_VERSION 73 holding both texts of a bang, their history and members' read marks: its startup runs no
DDL (same tables, same indexes, the version never lowered, rows kept), its bang list, pages and admin list read the
database as they did, and its join flow still works on a bang with public rules (it knows nothing of the tick: the
player is in, as on 2.4.66 today). Back on this build, that member sees 📜 Nội quy mới, and the rules are still there."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from game import bang
from game import pg_schema
from tests.test_bang import Base

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'a808cb79'   # 2.4.66, the release before bang rules (2.4.67 ships them): schema 62, no bang_code tables

OLD = '''import json,sys
from game.storage import Store
from game import bang
store=Store(sys.argv[1])
tok,bid=sys.argv[2],sys.argv[3]
sid=store.key(tok)
out={}
with store.connect() as db:
    out['v']=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    out['n']={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[4].split(',')}
out['search']=[c['id'] for c in bang.search(store, None)]
p=bang.page(store, sid, bid)
out['peek']=[p['member'], p['bang']['name']]
r=bang.post(store, tok, 'join', {'bang': bid})
out['joined']=r['done'].get('joined')
out['page']=len(bang.page(store, sid)['members'])
out['admin']=len(bang.admin_view(store)['bangs'])
store.close_pool()
print(json.dumps(out))
'''
TABLES = ('bang_code', 'bang_code_hist', 'bang_code_seen', 'bang_members', 'bang_log')


class OldRelease(Base):
    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-code-')
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

    def test_live_release_on_schema_73_with_rules(self):
        a = self.player(name='Lan')
        bid = self.found(a)
        self.op(a, 'code', kind='pub', text='Online góp quỹ mỗi tuần', ver=0)
        self.op(a, 'code', kind='in', text='Bang chiến Chủ nhật 20:00', ver=0)
        m = self.player(name='Minh')
        self.op(m, 'join', bang=bid, agree=True, code_ver=1)                 # a member with read marks
        newcomer = self.player(name='Tú')
        before = self.catalog()
        with self.store.connect() as db:
            n = {x: db.execute(f'SELECT COUNT(*) AS n FROM {x}').fetchone()['n'] for x in TABLES}
        self.assertTrue(all(n.values()), n)
        saves = {t: self.store.read(t) for t in (a, m, newcomer)}
        got = self.run_old(str(self.store.path), newcomer, bid, ','.join(TABLES))
        self.assertEqual(int(got['v']), pg_schema.SCHEMA_VERSION)
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 73)
        self.assertEqual(self.catalog(), before, 'no table or index changed by the old startup')
        for x in ('bang_code', 'bang_code_hist', 'bang_code_seen'):
            self.assertEqual(got['n'][x], n[x], 'rows kept')
        self.assertEqual(got['search'], [bid])
        self.assertEqual(got['peek'], [False, 'Rồng Đỏ'])
        self.assertEqual(got['joined'], bid, "2.4.66's join flow still works on a bang with rules")
        self.assertEqual(got['page'], 3)
        self.assertEqual(got['admin'], 1)
        for t in (a, m, newcomer):
            self.assertEqual(self.store.read(t)[1], saves[t][1], 'no save written')
        # and this build carries on: the rules are there, the newcomer (no read mark) sees 📜 Nội quy mới
        bang._VIEW.clear()
        code = bang.page(self.store, self.sid(newcomer))['code']
        self.assertEqual((code['pub']['text'], code['in']['text']), ('Online góp quỹ mỗi tuần', 'Bang chiến Chủ nhật 20:00'))
        self.assertEqual(code['news'], ['pub', 'in'])
        self.assertTrue(bang.me_view(self.store, newcomer)['mine']['code_new'])
        self.assertEqual(bang.page(self.store, self.sid(m))['code']['news'], ['in'])
