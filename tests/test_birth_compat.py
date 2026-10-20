"""🏥 Rollback of Phòng sinh & nhận nuôi (game/birth.py, SCHEMA_VERSION 65) to 2.4.66 (a808cb79, live): its startup on a
database at 65 with rows in birth_rooms / birth_stays runs no DDL and keeps them; a child born through a paid birth room
(with its optional `birth` block and the nurse's head start) is shown, cared for and split on divorce by 2.4.66's
game/family.py, which keeps the block; and saves that paid (wallet then account), were refunded, or adopted the personal
child with the fee validate, migrate and take a command there."""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from game import birth as bt
from tests.helpers import unknown_out   # 🔑 careers newer than 2.4.66 as the stored text leaves them out
from game import marriage as mr
from game import pg_schema
from game.engine import validate_state
from tests.test_birth import BirthBase, nurse

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'a808cb79'   # 2.4.66

STARTUP = '''import json,sys
from game.storage import Store
store=Store(sys.argv[1])
with store.connect() as db:
    v=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    n={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('birth_rooms','birth_stays')}
print(json.dumps([v,n]))
store.close_pool()
'''

FAMILY = '''import json,sys
from unittest.mock import patch
from game.storage import Store
from game import family, marriage as mr
store=Store(sys.argv[1]);a,b,t=sys.argv[2],sys.argv[3],float(sys.argv[4])
with patch('game.marriage.now',lambda:t):
    with store.connect() as db:
        c=mr._bond(db,a);st=store.parse_state(db.execute('SELECT state FROM sessions WHERE sid=?',(a,)).fetchone()['state'],a)
        v=family.view(db,a,c,st)
    care=family.act(store,b,'family_child_care',dict(child='shared',act='wash',rid='old-build-care-01'))
    with store.connect() as db:
        raw=json.loads(db.execute('SELECT state FROM family_children WHERE couple=?',(c['id'],)).fetchone()['state'])
    def end(db):
        cc=mr._row(db,'SELECT * FROM couples WHERE id=? FOR UPDATE',(c['id'],))
        family.end(db,cc)
    store.transaction(end)
    with store.connect() as db:
        copies=[json.loads(r['state']) for r in db.execute('SELECT state FROM family_custody WHERE child=? ORDER BY sid',(c['id'],))]
print(json.dumps([v['child'],care['message'],raw,copies]))
store.close_pool()
'''

SAVES = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action
out=[]
for s in json.load(sys.stdin):
    validate_state(s);s=migrate_state(s);validate_state(s)
    keep=json.dumps([s['journey'].get(k) for k in ('household','wallet','bank')],sort_keys=True)
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([keep,json.dumps([s['journey'].get(k) for k in ('household','wallet','bank')],sort_keys=True)])
print(json.dumps(out))
'''


class Rollback(BirthBase):
    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-birth-')
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

    def born_with_nurse(self):
        dao = self.user('dao', 5)
        mr._mutate(self.store, {self.sid(dao): nurse})
        self.book()
        self.accept()
        sid = self.stay(self.a)['id']
        self.do(dao, 'family_birth_nurse', id=sid)
        self.do(self.a, 'family_birth_checkin', id=sid)
        self.clock.t += bt.STAY_HOURS * 3600
        self.do(self.b, 'family_birth_done', id=sid)
        return sid

    def test_2_4_66_starts_on_schema_65_without_ddl(self):
        self.born_with_nurse()
        with self.store.connect() as db:
            db.execute("INSERT INTO birth_rooms(sid,career,name,price,open,at) VALUES('x','homestay','Phòng X',600000,true,1)")
            before = {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('birth_rooms', 'birth_stays')}
            idx = sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename LIKE 'birth%'").fetchall())
        v, n = self.run_old(STARTUP, str(self.store.path))
        self.assertEqual(int(v), pg_schema.SCHEMA_VERSION, 'the version is never lowered')
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 65)   # later steps only add tables
        self.assertEqual(n, before)
        with self.store.connect() as db:
            idx2 = sorted(r[0] for r in db.execute("SELECT indexname FROM pg_indexes WHERE schemaname=current_schema() AND tablename LIKE 'birth%'").fetchall())
        self.assertEqual(idx2, idx)

    def test_a_child_born_in_a_paid_room_lives_on_2_4_66(self):
        self.born_with_nurse()
        child, message, raw, copies = self.run_old(FAMILY, str(self.store.path), self.sid(self.a), self.sid(self.b), str(self.clock.t))
        self.assertEqual((child['name'], child['origin'], child['waiting'], child['bond']), ('Bông', 'birth', False, 10))
        self.assertEqual(child['needs'], dict(food=85, clean=85, joy=85))
        self.assertIn('Bông', message)
        self.assertEqual(raw['birth']['nurse'], 'Dao', "2.4.66's care keeps the optional block")
        self.assertEqual(raw['clean'], 100)
        self.assertEqual(len(copies), 2)
        self.assertTrue(all(c['birth']['where'] == bt.NPC['name'] for c in copies), 'custody copies carry it too')

    def test_saves_that_paid_or_were_refunded_load_on_2_4_66(self):
        self.fund(self.a, 300_000)
        self.account(self.a, 600_000)
        self.book()
        self.accept()
        paid = self.state(self.a)
        self.do(self.a, 'family_birth_cancel', id=self.stay(self.a)['id'])
        refunded = self.state(self.a)
        from game.engine import apply_action
        from tests.test_bank import story
        s = story(bt.ADOPT_FEE)
        s['journey']['life_day'] = 12
        personal, _ = apply_action(s, None, 'jr_hh_adopt', dict(kind='child', name='Mây', confirm=True, fee=bt.ADOPT_FEE))
        saves = [paid, refunded, personal]
        for x in saves:
            validate_state(x)
        got = self.run_old(SAVES, stdin=json.dumps([unknown_out(x) for x in saves]))
        for before, after in got:
            self.assertEqual(before, after)
        self.assertEqual(json.loads(got[2][0])[0]['child']['name'], 'Mây')
