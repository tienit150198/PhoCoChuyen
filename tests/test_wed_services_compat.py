"""💒 Rollback of Dịch vụ cưới từ người chơi (game/wed_services.py, SCHEMA_VERSION 69) to 2.4.66 (a808cb79, live): its
startup on a database at 69 with wedsvc_jobs rows (and the svc_orders they belong to) runs no DDL and keeps them; a
wedding resolved by this build (its result carries the optional `services` list) is shown by 2.4.66's Hôn nhân sheet,
and 2.4.66 resolves a wedding of its own with wedding orders around; the saves of a couple who paid for a service and of
the provider who was paid (wallet rows of kind 'life' / 'salary') validate, migrate and take a command there. No save
key was added."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from game import pg_schema
from game.engine import validate_state
from tests.test_wed_services import WedBase
from tests.helpers import unknown_out   # 🔑 careers newer than 2.4.66 as the stored text leaves them out

ROOT = Path(__file__).resolve().parents[1]
RELEASE = '2808dc10'   # 2.4.69 (live; 2.4.67 5ba2e147 and 2.4.66 a808cb79 before it): schema 73 (bang_code), none of this branch's tables or careers

STARTUP = '''import json,sys
from game.storage import Store
store=Store(sys.argv[1])
with store.connect() as db:
    v=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    n={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('wedsvc_jobs','svc_orders')}
print(json.dumps([v,n]))
store.close_pool()
'''

VIEW = '''import json,sys
from game.storage import Store
from game import marriage as mr
store=Store(sys.argv[1])
out=[]
for tok in sys.argv[2:]:
    st=store.read(tok)[0]
    v=mr.view(store,tok,st)
    w=v.get('wedding') or {}
    out.append([w.get('status'),[x['line'] for x in (w.get('result') or {}).get('services',[])],(w.get('result') or {}).get('guests') is not None])
print(json.dumps(out))
store.close_pool()
'''

SAVES = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action
out=[]
for s in json.load(sys.stdin):
    validate_state(s);s=migrate_state(s);validate_state(s)
    keep=json.dumps([s['journey'].get(k) for k in ('wallet','bank')],sort_keys=True)
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([keep,json.dumps([s['journey'].get(k) for k in ('wallet','bank')],sort_keys=True),sorted(s)])
print(json.dumps(out))
'''


class Rollback(WedBase):
    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-wedsvc-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {RELEASE}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def run_old(self, code, *args, stdin=None):
        old = self.old_tree()
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', code, *args], input=stdin, capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout.strip().splitlines()[-1])

    def served(self):
        self.sell(self.hoa, 'hoa')
        self.sell(self.hoa, 'vay')
        o = self.hire(self.a, self.hoa)
        self.spost(self.hoa, 'take', order=o['id'])
        self.work(self.hoa, o['id'])
        self.wpost(self.hoa, 'deliver', order=o['id'])
        self.hire(self.b, self.hoa, 'vay')    # paid, waiting: an open escrow row during the rollback
        return o

    def test_2_4_66_starts_on_schema_69_without_ddl(self):
        self.served()
        with self.store.connect() as db:
            before = {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('wedsvc_jobs', 'svc_orders')}
            idx = sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename='wedsvc_jobs'").fetchall())
        v, n = self.run_old(STARTUP, str(self.store.path))
        self.assertEqual(int(v), pg_schema.SCHEMA_VERSION, 'the version is never lowered')
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 69)
        self.assertEqual(n, before)
        with self.store.connect() as db:
            idx2 = sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename='wedsvc_jobs'").fetchall())
        self.assertEqual(idx2, idx)
        self.assertEqual(len(idx), 3)

    def test_a_wedding_served_by_players_shows_on_2_4_66(self):
        self.served()
        self.resolve()
        got = self.run_old(VIEW, str(self.store.path), self.a, self.b)
        for status, lines, guests in got:
            self.assertEqual((status, lines, guests), ('done', ['Hoa do Hoa cắm'], True))

    def test_2_4_66_resolves_its_own_wedding_with_wedding_orders_around(self):
        self.served()
        # the old build decides the day (its resolve knows nothing of the services): the NPC wedding as planned
        self.store.transaction(lambda db: db.execute('UPDATE weddings SET due_at=? WHERE id=?', (self.clock.t - 1, self.wid)))
        code = '''import json,sys
from game.storage import Store
from game import marriage as mr
store=Store(sys.argv[1])
for tok in sys.argv[2:]:
    mr.on_load(store,tok,store.read(tok)[0])
with store.connect() as db:
    r=db.execute("SELECT status,result FROM weddings ORDER BY id DESC LIMIT 1").fetchone()
print(json.dumps([r['status'],'services' in json.loads(r['result'])]))
store.close_pool()
'''
        self.assertEqual(self.run_old(code, str(self.store.path), self.a, self.b), ['done', False])

    def test_saves_that_paid_and_were_paid_load_on_2_4_66(self):
        self.served()
        saves = [self.state(t) for t in (self.a, self.b, self.hoa)]
        for s in saves:
            validate_state(s)
        got = self.run_old(SAVES, stdin=json.dumps([unknown_out(x) for x in saves]))
        for (before, after, keys), s in zip(got, saves):
            self.assertEqual(before, after)
            self.assertEqual(keys, sorted(s), 'no new save key')
