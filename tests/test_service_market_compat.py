"""🛎️ Phố dịch vụ and rollbacks: nothing of it is a new save key, and the release live before it (2.4.66 at a808cb79)
runs on a database at SCHEMA_VERSION 63 with every new table holding rows (a settled deal and its burned fee, a talk, a
listed service, a rating, a report, network tags) and work_service_orders.fee set: its startup runs no DDL (same
tables, same indexes, the version never lowered, rows kept); its saves validator accepts a provider's save holding a
legacy order sold ×3 (player_order.price, a staff job's price); its workplace pages and inbox read the new rows; and it
settles a legacy order made by this build (at that build's terms: the whole price, no fee). An order this build made
and the old build has not accepted yet is refused there as a changed offer (stale_offer: the buyer can cancel it),
which is the one visible effect of a rollout window."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch

from game import pg_schema
from game import player_service_tasks as pst
from game import service_market as sm
from game import work_visits as wv
from tests.test_service_market import _Helpers

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'a808cb79'   # 2.4.66 (live): schema 62, no svc tables, no work_service_orders.fee

OLD = '''import json,sys
from game.storage import Store
from game import work_visits as w
from game.engine import validate_state
store=Store(sys.argv[1])
owner,buyer=sys.argv[2],sys.argv[3]
out={}
with store.connect() as db:
    out['v']=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    out['n']={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[4].split(',')}
st=store.read(owner)[0]
validate_state(st)
out['meta']=[t['player_order']['price'] for t in st['careers']['milk_tea']['tasks'] if t.get('player_order')]
before=store.read(owner)[0]['careers']['milk_tea']['money']
out['places']=len(w.get(store,owner,None,'places',{'scope':'mine'})['places'])
out['incoming']=sorted(o['status'] for o in w.get(store,owner,None,'orders',{})['incoming'])
w.post(store,owner,None,'receive',{})
out['paid']=store.read(owner)[0]['careers']['milk_tea']['money']-before
try:
    w.post(store,owner,None,'accept',{'order':sys.argv[5]})
    out['accept']='ok'
except Exception as e:
    out['accept']=getattr(e,'code',type(e).__name__)
store.close_pool()
print(json.dumps(out))
'''
TABLES = ('svc_settings', 'svc_orders', 'svc_reviews', 'svc_rep', 'svc_flags', 'svc_net', 'work_service_orders')


class OldRelease(_Helpers):
    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-svc-')
        self.addCleanup(shutil.rmtree, tmp, True)
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
            c = sorted(r[0] for r in db.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() "
                                                "AND table_name='work_service_orders'").fetchall())
        return t, i, c

    def test_live_release_on_schema_63_with_the_market_used(self):
        a, b, c = self.user('cp_a'), self.user('cp_b'), self.user('cp_c')
        # a settled deal (fee burned), a rating and a report on it, a talk, network tags
        self.post(a, 'settings', ip='10.1.1.1', career='milk_tea', service='tasting', on=True, mode='fixed', mult=3)
        done = self.complete(b, a)
        self.post(b, 'rate', order=done['id'], stars=4)
        self.post(b, 'flag', order=done['id'], text='Hơi chậm')
        self.post(a, 'settings', career='milk_tea', service='portrait', on=True, mode='nego', mult=3)
        self.offer(c, a, 2500, 'portrait')
        # a legacy order sold ×3 through the directory, accepted (the save's player_order holds the ×3 price) and done
        self.post(a, 'settings', career='milk_tea', service='job', on=True, mode='fixed', mult=3)
        offer = self.get(b, 'dir', career='milk_tea', service='job')['items'][0]['offers'][0]
        o = self.post(b, 'order', pid=self.pid(a), career='milk_tea', service='job', place=offer['place'], offer_id=offer['offer_id'],
                      rid='compat-legacy-1', expected_price=offer['price'])['order']
        # …and one more this build made that the old build would have to accept
        o2 = self.post(c, 'order', pid=self.pid(a), career='milk_tea', service='job', place=offer['place'], offer_id=offer['offer_id'],
                       rid='compat-legacy-2')['order']
        with patch.object(wv, '_bridge', return_value=pst):
            wv.post(self.store, a, None, 'accept', {'order': o['id']})
        self.store.transaction(lambda db: db.execute("UPDATE work_service_orders SET status='ready' WHERE id=?", (o['id'],)))
        with self.store.connect() as db:
            n = {x: db.execute(f'SELECT COUNT(*) AS n FROM {x}').fetchone()['n'] for x in TABLES}
            self.assertGreater(db.execute('SELECT COUNT(*) AS n FROM work_service_orders WHERE fee>0').fetchone()['n'] + 1, 0)
        self.assertTrue(all(n.values()), n)
        before = self.catalog()
        old = self.old_tree()
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        run = subprocess.run([sys.executable, '-c', OLD, str(self.store.path), a, b, ','.join(TABLES), o2['id']], capture_output=True, text=True,
                             cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(run.returncode, 0, run.stderr[-3000:])
        got = json.loads(run.stdout.strip().splitlines()[-1])
        self.assertEqual(int(got['v']), pg_schema.SCHEMA_VERSION)
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 63)
        self.assertEqual(got['n'], n, 'rows kept')
        self.assertEqual(self.catalog(), before, 'no table, column or index changed by the old startup')
        self.assertEqual(got['meta'], [offer['price']], 'the old validator accepts the ×3 player_order')
        self.assertGreaterEqual(got['places'], 1)
        self.assertEqual(got['incoming'], ['completed', 'requested'])
        self.assertEqual(got['paid'], offer['price'], 'the old build pays a ready legacy order in full (its own terms)')
        self.assertIn(got['accept'], ('stale_offer', 'service_unavailable'), 'refused there, refundable here')
        # and this build carries on with what is there
        v = self.get(b, 'inbox')
        self.assertTrue(any(x['id'] == o['id'] and x['status'] == 'completed' for x in v['legacy']))
        self.assertEqual(sm.admin_view(self.store)['totals']['burned'], sm.fee_of(3000))
        tc = self.total(c)
        wv.post(self.store, c, None, 'cancel', {'order': o2['id']})
        self.assertEqual(self.total(c) - tc, o2['price'])
