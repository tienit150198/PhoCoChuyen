"""🏨 Phòng cho người chơi and rollbacks: no new save key, and the release live before it (2.4.66 at a808cb79) runs on a
database at SCHEMA_VERSION 68 with hotel_stays / hotel_hosts / hotel_rest holding rows (a stay checked out and paid, a
couple's stay with the partner's rest applied, a stay in progress with its situations, a no-show refunded) and the
market's tables used by them: its startup runs no DDL (same tables, same indexes, the version never lowered, rows
kept), and the saves this build touched (a host who paid burned costs and was paid 95 %, a guest and a partner whose
tỉnh táo / no bụng / tinh thần moved) validate, migrate and take a command there."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from game import hotel_stay as hs
from game import pg_schema
from game.engine import validate_state
from tests.test_hotel_stay import HotelBase, M

ROOT = Path(__file__).resolve().parents[1]
RELEASE = '2808dc10'   # 2.4.69 (live; 2.4.67 5ba2e147 and 2.4.66 a808cb79 before it): schema 73 (bang_code), none of this branch's tables or careers

OLD = '''import json,sys
from game.storage import Store
from game.engine import validate_state,migrate_state,apply_action
store=Store(sys.argv[1])
out={}
with store.connect() as db:
    out['v']=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    out['n']={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[2].split(',')}
saves=[]
for tok in sys.argv[3].split(','):
    s=store.read(tok)[0]
    validate_state(s);s=migrate_state(s);validate_state(s)
    keep=json.dumps([s['journey'].get(k) for k in ('wallet','needs')]+[s['journey']['life']['spirit']],sort_keys=True)
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    saves.append([keep,json.dumps([s['journey'].get(k) for k in ('wallet','needs')]+[s['journey']['life']['spirit']],sort_keys=True)])
out['saves']=saves
store.close_pool()
print(json.dumps(out))
'''
TABLES = ('hotel_stays', 'hotel_hosts', 'hotel_rest', 'svc_orders', 'svc_settings', 'svc_reviews', 'svc_rep')


class OldRelease(HotelBase):
    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-hotel-')
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
        return t, i

    def test_2_4_66_on_schema_68_with_stays_in_every_state(self):
        h, g, a, b, c = self.host('oc_h', 'hotel'), self.guest('oc_g'), self.guest('oc_a'), self.guest('oc_b'), self.guest('oc_c')
        for svc in ('stay_night', 'stay_hours', 'stay_couple'):
            self.sell(h, 'hotel', svc)
        # a stay checked out, paid and rated (the host paid a suite and an answer: burned costs)
        o = self.to_in(h, g, 'hotel', 'stay_hours', room='p501')
        self.clock.t += 40 * M
        st = self.stay(h, o['id'])
        ev = next((e for e in st['events'] if e['st'] == 'open'), None)
        if ev:
            self.do(h, 'handle', order=o['id'], ev=ev['key'], pick=ev['opts'][0]['id'])
        self.clock.t += 21 * M
        st = self.stay(h, o['id'])
        self.do(h, 'checkout', order=o['id'], pick=st['out_quirk']['opts'][0]['id'])
        from game import service_market as sm
        sm.post(self.store, g, None, 'rate', dict(order=o['id'], stars=4))
        # a couple's stay: both rested
        self.couple(a, b, 'married')
        o2 = self.to_in(h, a, 'hotel', 'stay_couple', room='p101')
        self.clock.t += 181 * M
        st = self.stay(h, o2['id'])
        self.do(h, 'checkout', order=o2['id'], pick=st['out_quirk']['opts'][1]['id'])
        hs.settle_partner(self.store)
        self.assertEqual(self.row(o2['id'])['partner_rest'], 2)
        # a no-show refunded by the housekeeping
        o4 = self.order(g, h, 'hotel', 'stay_night')
        self.do(h, 'confirm', order=o4['id'])
        self.clock.t += hs.ARRIVE_HOURS * 3600 + 1
        hs._swept[0] = 0
        hs.run_housekeeping(self.store)
        self.assertEqual((self.svc(o4['id'])['status'], self.row(o4['id'])['stage']), ('refunded', 'gone'))
        # a stay in progress with a request waiting
        o3 = self.to_in(h, c, 'hotel', 'stay_night', room='p205')
        self.do(c, 'ask', order=o3['id'], ask='goi')
        with self.store.connect() as db:
            n = {x: db.execute(f'SELECT COUNT(*) AS n FROM {x}').fetchone()['n'] for x in TABLES}
        self.assertTrue(all(n.values()), n)
        toks = [h, g, a, b]
        for t in toks:
            validate_state(self.state(t))
        before = self.catalog()
        old = self.old_tree()
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        run = subprocess.run([sys.executable, '-c', OLD, str(self.store.path), ','.join(TABLES), ','.join(toks)], capture_output=True, text=True,
                             cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(run.returncode, 0, run.stderr[-3000:])
        got = json.loads(run.stdout.strip().splitlines()[-1])
        self.assertEqual(int(got['v']), pg_schema.SCHEMA_VERSION)
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 68)
        self.assertEqual(got['n'], n, 'rows kept')
        self.assertEqual(self.catalog(), before, 'no table or index changed by the old startup')
        self.assertEqual(len(got['saves']), 4)
        for keep, after in got['saves']:
            self.assertEqual(keep, after, 'the old build keeps wallet, needs and spirit as they are')
        # and this build carries on with what is there
        self.clock.t += 181 * M + hs.GRACE_MIN * M
        hs._swept[0] = 0
        hs.run_housekeeping(self.store)
        self.assertEqual(self.svc(o3['id'])['status'], 'done')
