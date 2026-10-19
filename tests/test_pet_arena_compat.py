"""⚔️ Đấu trường pet and rollbacks: nothing of the arena is in a save, and the previous release (2.4.60 at e05bacf5) runs
on a database at SCHEMA_VERSION 58: its startup leaves the new tables and their rows alone (no DDL: the stored version is
higher), and the saves of players who fought validate, migrate and take a command there, their pets as they were."""
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

from game import pet_arena as A
from game import pg_schema
from game.engine import validate_state
from tests.test_pet_arena import Store, pet_save

ROOT = Path(__file__).resolve().parents[1]
RELEASES = {'2.4.60': 'e05bacf5'}

PROG = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action,CAREERS
out=[]
for s in json.load(sys.stdin):
    # a career a later release added is not this tree's business (it may unlock by the calendar): the pets are
    s['careers']={k:v for k,v in s['careers'].items() if k in CAREERS};j=s['journey']
    j['unlocked']=[c for c in j['unlocked'] if c in CAREERS];j['days']=[d for d in j['days'] if d['c'] in CAREERS]
    validate_state(s);s=migrate_state(s);validate_state(s)
    keep=lambda s:json.dumps([s['journey'].get(k) for k in ('pets','petx','petw')],sort_keys=True)
    before=keep(s)
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([before,keep(s)])
print(json.dumps(out))
'''

STARTUP = '''import sys
from game.storage import Store
store=Store(sys.argv[1])
with store.connect() as db:
    v=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    n=db.execute('SELECT COUNT(*) FROM pet_arena').fetchone()[0]
    m=db.execute('SELECT COUNT(*) FROM pet_arena_matches').fetchone()[0]
print(v,n,m)
store.close_pool()
'''


class OldRelease(Store):
    def old_tree(self, rev):
        tmp = tempfile.mkdtemp(prefix=f'mnl-arena-{rev}-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', rev, 'game', 'reference'], cwd=ROOT, capture_output=True, timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {rev}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def run_old(self, rev, code, *args, stdin=None):
        old = self.old_tree(rev)
        env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', code, *args], input=stdin, capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return out.stdout.strip().splitlines()[-1]

    def test_saves_after_battles(self):
        a, b = self.arena(('Mít', 'Na')), self.arena(('Bơ',))
        self.op(b, 'view', ip='2.2.2.2')
        for op, data in (('view', {}), ('fight', {}), ('npc', dict(stage=0))):
            self.op(a, op, **data)
        saves = [self.store.read(t)[0] for t in (a, b)]
        for s in saves:
            validate_state(s)
            self.assertNotIn('arena', json.dumps(sorted(s['journey'])))
        for rev in RELEASES.values():
            got = json.loads(self.run_old(rev, PROG, stdin=json.dumps(saves)))
            for before, after in got:
                self.assertEqual(before, after)

    def test_old_startup_on_schema_58(self):
        a, b = self.arena(), self.arena()
        self.op(b, 'view', ip='2.2.2.2')
        self.op(a, 'fight')
        for rev in RELEASES.values():
            v, n, m = self.run_old(rev, STARTUP, str(self.store.path)).split()
            self.assertEqual(int(v), pg_schema.SCHEMA_VERSION)        # never lowered
            self.assertEqual((int(n), int(m)), (2, 1))                # rows kept
        self.assertEqual(self.op(a, 'view')['me']['games'], 1)        # and this build carries on


class Fresh(unittest.TestCase):
    def test_no_save_key(self):
        s = pet_save(('Mít',))
        keys = set(s['journey'])
        A.lineup_snap(s, [p['id'] for p in A.candidates(s)])
        self.assertEqual(set(s['journey']), keys)
