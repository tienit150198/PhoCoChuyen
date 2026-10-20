"""📸 Chụp ảnh cho người chơi and rollbacks. The release live before it (2.4.66 at a808cb79):
* loads, validates, migrates and plays a save holding a framed photo: the `anh_chup` piece in the bag and one placed on a
  wall (journey.reno.items, journey.decor) and journey.photo_wall {uid: photo id}; it keeps them untouched (journey allows
  extra keys; the room-fit check skips a kind it does not know), and back on this build the frame and its photo are there;
* starts on a database at SCHEMA_VERSION 66 with orders, photos, a profile photo and a refund waiting: no DDL (the
  version is never lowered, the rows stay), its live_effects pays what it knows and leaves the 'photo' refund pending
  (paid by this build later, once)."""
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

from game import deco as dc
from game.engine import migrate_state
from tests.helpers import unknown_out   # 🔑 careers newer than 2.4.66 as the stored text leaves them out
from game import live_effects as lfx
from game import pg_schema
from game import photo_studio as P
from game import reno as rn
from game.engine import validate_state
from tests.test_bank import act
from tests.test_deco import owner
from tests.test_photo_studio import Base

ROOT = Path(__file__).resolve().parents[1]
RELEASE = '2808dc10'   # 2.4.69 (live; 2.4.67 5ba2e147 and 2.4.66 a808cb79 before it): schema 73 (bang_code), none of this branch's tables or careers

PROG = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action,CAREERS
out=[]
for s in json.load(sys.stdin):
    validate_state(s);s=migrate_state(s);validate_state(s)
    j=s['journey'];before=json.dumps([j.get('photo_wall'),[x for x in j['reno']['items'] if x['k']=='anh_chup']],sort_keys=True)
    j['life_day']+=3
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s);j=s['journey']
    out.append([before,json.dumps([j.get('photo_wall'),[x for x in j['reno']['items'] if x['k']=='anh_chup']],sort_keys=True),s])
print(json.dumps(out))
'''

DB_PROG = '''import json,sys
from game.storage import Store
from game import live_effects as lfx
store=Store(sys.argv[1],story=True)
tok=sys.argv[2]
out={}
with store.connect() as db:
    out['v']=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    out['n']={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[3].split(',')}
st=store.read(tok)[0]
lfx.on_load(store,tok,st)
with store.connect() as db:
    out['fx']=[r[0] for r in db.execute("SELECT status FROM live_effects WHERE kind='photo'").fetchall()]
out['wallet']=store.read(tok)[0]['journey']['wallet']
store.close_pool()
print(json.dumps(out))
'''
TABLES = ('photo_studios', 'photo_orders', 'photos', 'photo_pfp')


def old_tree(test):
    tmp = tempfile.mkdtemp(prefix='mnl-photo-')
    test.addCleanup(shutil.rmtree, tmp, True)
    try:
        data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        test.skipTest(f'no git tree with {RELEASE}')
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(tmp, filter='data')
    return Path(tmp)


def run(test, prog, args=(), stdin=None):
    old = old_tree(test)
    env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
    out = subprocess.run([sys.executable, '-c', prog, *args], input=stdin, capture_output=True, text=True, cwd=old, env=env,
                         encoding='utf-8', timeout=300)
    test.assertEqual(out.returncode, 0, out.stderr[-3000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


class Saves(unittest.TestCase):
    def framed(self):
        """A home owner with two framed photos: one in the bag, one hung on the living room wall."""
        s = owner('tap_the', wallet=9000)
        blk = rn.ensure_block(s)
        a, b = rn.new_uid(blk), None
        blk['items'].append(dict(id=a, k=P.FRAME_KIND, r=None, x=None))
        b = rn.new_uid(blk)
        blk['items'].append(dict(id=b, k=P.FRAME_KIND, r=None, x=None))
        s['journey'][P.WALL_KEY] = {a: 'ph' + '1' * 16, b: 'ph' + '2' * 16}
        validate_state(s)
        placed = None
        for x in range(0, 200, 10):
            for y in (0, 5, 10, 20):
                try:
                    s2, _ = act(s, 'jr_deco_put', uid=b, r='living', x=x, y=y)
                except Exception:   # noqa: BLE001  (a spot the wall does not take: the next one)
                    continue
                placed = s2
                break
            if placed:
                break
        self.assertIsNotNone(placed, 'the frame hangs somewhere on the living room wall')
        self.assertIn(b, dc.layout(placed)['pos'])
        validate_state(placed)
        return placed, a, b

    def test_a_framed_photo_save_plays_on_2_4_66_and_comes_back(self):
        s, a, b = self.framed()
        got = run(self, PROG, stdin=json.dumps([unknown_out(s)]))
        before, after, back = got[0]
        back = migrate_state(back, owned=True)   # 💤 as storage reads it: the careers 2.4.66 left out come back
        mine = json.dumps([s['journey']['photo_wall'], [x for x in s['journey']['reno']['items'] if x['k'] == 'anh_chup']], sort_keys=True)
        self.assertEqual(before, mine)
        self.assertEqual(after, mine)
        # back on this build: still valid, still hung, still its photo
        validate_state(back)
        self.assertEqual(back['journey']['photo_wall'], s['journey']['photo_wall'])
        self.assertIn(b, dc.layout(back)['pos'])
        back, _ = act(back, 'jr_seen', ids=['y'])
        validate_state(back)


class Database(Base):
    def test_2_4_66_starts_on_schema_66_and_leaves_photo_refunds_pending(self):
        sh, by = self.shooter(), self.buyer()
        o = self.order(by, sh)['order']
        self.op(sh, 'accept', id=o['id'])
        self.shoot_all(sh, o['id'])
        photo = self.op(sh, 'deliver', id=o['id'], pick=0, rt={})['photo']
        P.post(self.store, by, None, 'pfp', dict(id=photo))
        b = self.order(by, sh)['order']
        self.op(sh, 'decline', id=b['id'])   # a refund row waits for the buyer
        w = self.wallet(by)
        with self.store.connect() as db:
            before = {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES}
        got = run(self, DB_PROG, (self.store.path, by, ','.join(TABLES)))
        self.assertEqual(got['v'], str(pg_schema.SCHEMA_VERSION), 'the old release never lowers the version (no DDL)')
        self.assertEqual(got['n'], before, 'every row kept')
        self.assertEqual(got['fx'], ['pending'], "2.4.66 does not know 'photo': the refund waits")
        self.assertEqual(got['wallet'], w)
        # back on this build: paid once
        lfx.on_load(self.store, by, self.state(by))
        self.assertEqual(self.wallet(by), w + 900)
        lfx.on_load(self.store, by, self.state(by))
        self.assertEqual(self.wallet(by), w + 900)
