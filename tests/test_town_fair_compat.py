"""🎪 Rollback of Hội chợ việc làm (game/town_fair.py, SCHEMA_VERSION 74) to 2.4.66 (a808cb79, live): its startup on a
database at 74 with fair rows (a fair settled and archived, booths, stamps, a claimed reward, the admin's switches) runs no
DDL and keeps them; a 'tfair' live_effects row waiting for a save stays pending there (a kind 2.4.66 does not pay) and is
paid once by this build afterwards; the saves of a visitor who holds and wears the fair's 🎨 Phong cách title, of a booth
owner paid 95 % for discounted fair orders and of a buyer validate, migrate and take a command on 2.4.66, as the stored
text holds them. No save key was added."""
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
from game import service_market as sm
from game import spend_content as SC
from game import town_fair as tf
from game import town_fair_content as C
from game.engine import validate_state
from tests.helpers import unknown_out   # 🔑 careers newer than 2.4.66 as the stored text leaves them out
from tests.test_town_fair import FairBase, H

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'fe504023'   # 2.4.71 (live; 2.4.67 5ba2e147 and 2.4.66 a808cb79 before it): schema 73 (bang_code), none of this branch's tables or careers
TABLES = ('fair_events', 'fair_booths', 'fair_stamps', 'fair_rewards', 'fair_config', 'svc_orders', 'live_effects')

STARTUP = '''import json,sys
from game.storage import Store
store=Store(sys.argv[1])
with store.connect() as db:
    v=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    n={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[2].split(',')}
print(json.dumps([v,n]))
store.close_pool()
'''

FX = '''import json,sys
from game.storage import Store
from game import live_effects
store=Store(sys.argv[1])
tok=sys.argv[2]
before=store.read(tok)[1]
live_effects.on_load(store,tok,store.read(tok)[0])
with store.connect() as db:
    st=[r['status'] for r in db.execute("SELECT status FROM live_effects WHERE kind='tfair' ORDER BY id").fetchall()]
print(json.dumps([st,store.read(tok)[1]==before]))
store.close_pool()
'''

SAVES = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action
from game import spend
out=[]
for s in json.load(sys.stdin):
    validate_state(s);s=migrate_state(s);validate_state(s)
    keep=json.dumps([s['journey'].get(k) for k in ('wallet','bank')]+[(spend.get(s) or {}).get('own'),(spend.get(s) or {}).get('wear')],sort_keys=True)
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([keep,json.dumps([s['journey'].get(k) for k in ('wallet','bank')]+[(spend.get(s) or {}).get('own'),(spend.get(s) or {}).get('wear')],sort_keys=True),
                sorted(s),spend.style_now(s)])
print(json.dumps(out))
'''


class Rollback(FairBase):
    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-tfair-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120,
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

    def fair(self):
        """A fair with three booths, a visitor who completed three fair orders and claimed (and wears) the first tier, a
        booth owner who served three customers (their titles granted when the fair settles), a fair order still in escrow."""
        ps = [self.provider(f'rb_{c}', c) for c in ('milk_tea', 'florist', 'salon')]
        for tok, c in zip(ps, ('milk_tea', 'florist', 'salon')):
            self.fpost(tok, 'open', career=c, pct=20)
        v, w = self.user('rb_v', wallet=50000), self.user('rb_w', wallet=50000)
        for tok, c in zip(ps, ('milk_tea', 'florist', 'salon')):
            self.complete(v, tok, c)
        self.complete(w, ps[0])
        self.complete(self.user('rb_x', wallet=50000), ps[0])   # three distinct customers (a repeat buyer counts once)
        self.order(w, ps[1], 'florist')       # paid, waiting: an open escrow row during the rollback
        self.fpost(v, 'claim', event=self.ev['id'], tier=1)
        self.cmd(v, 'jr_spend_wear', kind='title', id='t_hc_khach')
        tf.admin_act(self.store, 'admin', dict(op='weekly', on=True))
        self.clock.t = self.ev['ends'] + tf.SETTLE_HOURS * H + 1
        tf._swept[0] = 0
        sm._swept[0] = 0
        self.assertEqual(tf.run_housekeeping(self.store), 1)
        return ps, v, w

    def test_2_4_66_starts_on_schema_74_without_ddl(self):
        self.fair()
        with self.store.connect() as db:
            before = {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES}
            idx = sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename LIKE 'fair_%'").fetchall())
        self.assertTrue(all(before.values()), before)
        v, n = self.run_old(STARTUP, str(self.store.path), ','.join(TABLES))
        self.assertEqual(int(v), pg_schema.SCHEMA_VERSION, 'the version is never lowered')
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 74)
        self.assertEqual(n, before, 'rows kept')
        with self.store.connect() as db:
            idx2 = sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename LIKE 'fair_%'").fetchall())
        self.assertEqual(idx2, idx)

    def test_a_pending_fair_reward_waits_on_2_4_66_and_is_paid_once_here(self):
        ps, v, w = self.fair()
        host = ps[0]
        with self.store.connect() as db:
            st = db.execute("SELECT status FROM live_effects WHERE sid=? AND kind='tfair'", (self.sid(host),)).fetchone()['status']
        self.assertEqual(st, 'pending')
        statuses, same = self.run_old(FX, str(self.store.path), host)
        self.assertTrue(same, 'the old build does not touch the save')
        self.assertIn('pending', statuses)
        self.load(host)
        self.assertEqual(set(self.own(host)), {C.HOST_ITEM, C.SERVED_ITEM, C.RATED_ITEM})
        self.load(host)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM live_effects WHERE sid=? AND kind='tfair' AND status='applied'",
                                        (self.sid(host),)).fetchone()['n'], 1)

    def test_saves_of_the_fair_load_on_2_4_66(self):
        ps, v, w = self.fair()
        self.load(ps[0])
        saves = [self.state(t) for t in (v, w, ps[0])]
        for s in saves:
            validate_state(s)
        self.assertEqual(self.own(v), {'t_hc_khach': SC.PERMANENT})
        got = self.run_old(SAVES, stdin=json.dumps([unknown_out(x) for x in saves]))
        for (before, after, keys, worn), s in zip(got, saves):
            self.assertEqual(before, after, 'wallet, bank and the style items kept as they are')
            self.assertLessEqual(set(s), set(keys), 'no save key 2.4.66 does not know')
            self.assertNotIn('t', worn, '2.4.66 does not show a title it does not know')
