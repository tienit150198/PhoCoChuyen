"""🧰 Thợ phục chế and rollbacks to the release live before it (2.4.66 at a808cb79):
* a buyer's save holding the optional journey.restored marks (a vehicle that rides again, a home part back to 100, a piece
  of furniture made cổ điển) loads, validates, migrates and plays there; 2.4.66 keeps the unknown journey key untouched
  (journey.validate only asks for its own keys), and back on this build the marks are still there;
* an untouched 🧰 workshop is left out of the stored save (engine.DORMANT), so 2.4.66, which requires exactly its own
  careers, loads it; a worked one is refused as is, stripped with scripts/strip_new_careers.py and restored byte for byte;
* 2.4.66 starts on a database at SCHEMA_VERSION 72 with restore_tickets rows in every state: no DDL (the version is
  never lowered, every table, index and row kept), and the buyer's stored save plays there."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import pg_schema
from game import restore_service as rs
from game import service_market as sm
from game.engine import dormant_out, migrate_state, validate_state
from tests.helpers import Journey
from tests.test_restore_service import RestoreBase, right

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'a808cb79'   # 2.4.66 (live): schema 62, no restore career, no restore_tickets, no journey.restored

LOAD = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action
s=migrate_state(json.load(sys.stdin));validate_state(s)
keep=json.dumps(s['journey'].get('restored'),sort_keys=True)
s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
validate_state(s)
print(json.dumps([keep,json.dumps(s['journey'].get('restored'),sort_keys=True),s]))
'''
DB = '''import json,sys
from game.storage import Store
from game.engine import validate_state,migrate_state,apply_action
store=Store(sys.argv[1])
out={}
with store.connect() as db:
    out['v']=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    out['n']={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[2].split(',')}
s=store.read(sys.argv[3])[0]
validate_state(s);s=migrate_state(s);validate_state(s)
keep=json.dumps(s['journey'].get('restored'),sort_keys=True)
s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
validate_state(s)
out['save']=[keep,json.dumps(s['journey'].get('restored'),sort_keys=True)]
store.close_pool()
print(json.dumps(out))
'''
TABLES = ('restore_tickets', 'svc_orders', 'svc_settings', 'svc_rep')


def old_tree(test):
    tmp = tempfile.mkdtemp(prefix='mnl-restore-')
    test.addCleanup(shutil.rmtree, tmp, True)
    try:
        data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        test.skipTest(f'no git tree with {RELEASE}')
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(tmp, filter='data')
    return Path(tmp)


def run(test, prog, args=(), stdin=None, ok=True):
    old = old_tree(test)
    env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
    out = subprocess.run([sys.executable, '-c', prog, *args], input=stdin, capture_output=True, text=True, cwd=old, env=env,
                         encoding='utf-8', timeout=300)
    if not ok:
        return out
    test.assertEqual(out.returncode, 0, out.stderr[-3000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


class Restored(RestoreBase):
    """Two real accounts: every service delivered once, then the saves and the database handed to 2.4.66."""

    def flow(self):
        tho, khach = self.restorer('rc_tho'), self.owner('rc_khach')
        s = self.state(khach)
        r = s['journey']['reno']
        part = next(p for p, x in r['parts'].items() if x['c'] < 100)
        uid = next(it['id'] for it in r['items'] if it['k'] == 'ban_tra')
        for svc, ref, kind, style in (('xe', 'xe_so', 'xe', 'moi'), ('nha', f'{r["hid"]}:{part}', 'nha', 'giu'), ('co_dien', uid, 'decor', 'giu')):
            self.ticket(khach, svc, ref, style)
            o = self.order(khach, tho, svc)
            sm.post(self.store, tho, None, 'take', dict(order=o['id']))
            self.finish_bench(tho, o['id'], kind, style)
            self.assertEqual(sm.post(self.store, tho, None, 'done', dict(order=o['id']))['order']['status'], 'done')
        return tho, khach

    def test_a_buyer_with_restored_things_plays_on_2_4_66_and_comes_back(self):
        tho, khach = self.flow()
        s = self.state(khach)
        self.assertEqual(len(s['journey']['restored']['items']), 3)
        stored = dormant_out(s)
        self.assertNotIn('restore', stored['careers'], 'the buyer never worked the workshop: left out of the stored save')
        before, after, back = run(self, LOAD, stdin=json.dumps(stored, ensure_ascii=False))
        mine = json.dumps(s['journey']['restored'], sort_keys=True)
        self.assertEqual((before, after), (mine, mine), '2.4.66 keeps the marks untouched')
        back = migrate_state(back)
        validate_state(back)
        self.assertEqual(back['journey']['restored'], s['journey']['restored'])
        self.assertIn('restore', back['careers'], 'forward again: the workshop comes back fresh')

    def test_2_4_66_starts_on_schema_72_with_tickets_in_every_state(self):
        tho, khach = self.flow()
        # an open ticket, a dropped one and a bound one whose order was refunded (open again on the next read)
        other = self.owner('rc_k2', home=None, piece=None)
        self.ticket(other, 'xe', 'xe_so')
        o = self.order(other, tho, 'xe')
        sm.post(self.store, tho, None, 'take', dict(order=o['id']))
        self.work(tho, o['id'], right('xe', 0, 'giu'))
        sm.post(self.store, tho, None, 'decline', dict(order=o['id']))
        third = self.owner('rc_k3', car='xe_dap', home=None, piece=None)
        t = self.ticket(third, 'xe', 'xe_dap')['ticket']
        rs.post(self.store, third, None, 'drop', dict(ticket=t))
        self.ticket(third, 'xe', 'xe_dap')
        with self.store.connect() as db:
            n = {x: db.execute(f'SELECT COUNT(*) AS n FROM {x}').fetchone()['n'] for x in TABLES}
            states = sorted({r['status'] for r in db.execute('SELECT status FROM restore_tickets').fetchall()})
            cat = sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename='restore_tickets'").fetchall())
        self.assertEqual(states, ['bound', 'done', 'dropped', 'open'])
        got = run(self, DB, (str(self.store.path), ','.join(TABLES), khach))
        self.assertEqual(int(got['v']), pg_schema.SCHEMA_VERSION, 'the old release never lowers the version (no DDL)')
        self.assertEqual(pg_schema.SCHEMA_VERSION, 72)
        self.assertEqual(got['n'], n, 'every row kept')
        keep, after = got['save']
        self.assertEqual(keep, after)
        self.assertEqual(json.loads(keep), self.state(khach)['journey']['restored'])
        with self.store.connect() as db:
            self.assertEqual(cat, sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename='restore_tickets'").fetchall()))
        # back on this build: the refunded order's ticket opens again, the work carries on
        self.assertEqual(self.mine(other)['tickets'][0]['status'], 'open')


class Workshop(unittest.TestCase):
    def test_untouched_workshop_is_left_out_and_a_worked_one_is_stripped_and_restored(self):
        j = Journey('milk_tea')
        j.act('end_day', carry_event=True)
        stored = dormant_out(j.state)
        self.assertNotIn('restore', stored['careers'])
        out = run(self, LOAD, stdin=json.dumps(stored, ensure_ascii=False))
        self.assertIsNone(json.loads(out[0]))
        sys.path.insert(0, str(ROOT))
        from scripts.strip_new_careers import restore, strip
        from tests.test_career_restore import solve
        w = Journey('restore', day=4, slot=2)
        solve(w, w.task['id'])
        w.act('end_day')
        played = json.loads(json.dumps(w.state))
        refused = run(self, LOAD, stdin=json.dumps(dormant_out(played), ensure_ascii=False), ok=False)
        self.assertNotEqual(refused.returncode, 0, 'the old build refuses a worked workshop as is')
        stripped, removed = strip(played, ['restore'])
        self.assertIn('restore', removed)
        back = run(self, LOAD, stdin=json.dumps(dormant_out(stripped), ensure_ascii=False))[2]
        again, problems = restore(migrate_state(back), removed)
        self.assertEqual(problems, [])
        again = migrate_state(again)
        validate_state(again)
        self.assertEqual(json.dumps(again['careers']['restore'], sort_keys=True), json.dumps(played['careers']['restore'], sort_keys=True))


if __name__ == '__main__':
    unittest.main()
