"""Rollback of the integrated build (Xây trên đảo + Bang + Đấu trường pet + Đảo bang, SCHEMA_VERSION 58) to 2.4.60
(e05bacf5): one save holding every new save key at once (journey.islb, journey.bang, pets that fought and were fielded in
the bang war) validates, migrates and takes a command there, the blocks untouched; and 2.4.60's startup on a database
at 58 with rows in every new table runs no DDL (same tables, same indexes, version never lowered, rows kept)."""
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

from game import bang_pets
from game import marriage as mr
from game import pet_arena as A
from game import pet_tiers as px
from game import pet_war as PW
from game import pg_schema, promotion
from game.engine import validate_state
from tests.test_bang import Base
from tests.test_bank import act
from tests.test_island import buy, rich
from tests.test_lb_titles import at

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'e05bacf5'   # 2.4.60

PROG = '''import json,sys
from game.engine import validate_state,migrate_state,apply_action,CAREERS
out=[]
for s in json.load(sys.stdin):
    s['careers']={k:v for k,v in s['careers'].items() if k in CAREERS};j=s['journey']
    j['unlocked']=[c for c in j['unlocked'] if c in CAREERS];j['days']=[d for d in j['days'] if d['c'] in CAREERS]
    validate_state(s);s=migrate_state(s);validate_state(s)
    keep=lambda s:json.dumps([s['journey'].get(k) for k in ('islb','bang','pets','petx','island')],sort_keys=True)
    before=keep(s)
    s,_=apply_action(s,None,'jr_seen',{'ids':['x']})
    validate_state(s)
    out.append([before,keep(s)])
print(json.dumps(out))
'''

STARTUP = '''import json,sys
from game.storage import Store
store=Store(sys.argv[1])
with store.connect() as db:
    v=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    n={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[2].split(',')}
print(json.dumps([v,n]))
store.close_pool()
'''
TABLES = ('island_builds', 'island_public', 'island_visitors', 'bangs', 'bang_members', 'bang_fund', 'bang_points',
          'pet_arena', 'pet_arena_matches', 'pet_war_picks')


class Integrated(Base):
    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-integ-')
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

    def everything(self):
        """A player with an island and buildings, two pets, a bang founded and given to, an arena lineup, a war pick."""
        bang_pets.install()            # the server imports it; another test may have unregistered 'bang'
        s = rich(400_000_000)
        promotion.record(s, 'milk_tea', True)['rank'] = 1
        s, _ = buy(s, 'dao_hoang_hon')
        s, _ = act(s, 'jr_isle_build', island='dao_hoang_hon', plot=0, kind='lau_dai', confirm=True)
        for i, nick in enumerate(('Mít', 'Na')):
            s, _ = act(s, 'jr_pet_adopt', **{'from': 'shop'}, breed=('corgi', 'meo_mun')[i], coat=0, nick=nick, confirm=True)
        validate_state(s)
        tok = self.player(name='Lan')
        sid = self.sid(tok)
        mr._mutate(self.store, {sid: lambda x: (x.clear(), x.update(s), x.__setitem__('name', 'Lan'))})
        bid = self.found(tok)
        self.give(tok, 3_000_000, bid)
        self.cmd(tok, 'jr_isle_build', island='dao_hoang_hon', plot=1, kind='cong_vien', confirm=True)   # island_builds rows
        st = self.store.read(tok)[0]
        A.act(self.store, tok, 'lineup', dict(pets=[p['id'] for p in A.candidates(st)][:2]), st, '1.1.1.1')
        A.act(self.store, tok, 'npc', dict(stage=0), st, '1.1.1.1')                                       # a battle row
        with patch.object(A, 'now', return_value=at(2026, 10, 21, 12)):
            PW.act(self.store, tok, 'war_pick', dict(pet=px.all_pets(st)[0]['id']), st, '1.1.1.1')
        return tok, bid

    def test_one_save_with_every_new_key_plays_on_2_4_60(self):
        tok, bid = self.everything()
        s = self.store.read(tok)[0]
        validate_state(s)
        for k in ('islb', 'bang', 'pets'):
            self.assertIn(k, s['journey'], k)
        got = self.run_old(PROG, stdin=json.dumps([s]))
        for before, after in got:
            self.assertEqual(before, after)
            self.assertEqual(json.loads(before)[1]['n'], 2, 'journey.bang as written here (found + give)')

    def test_2_4_60_starts_on_schema_58_without_ddl(self):
        self.everything()
        with self.store.connect() as db:
            db.execute("INSERT INTO island_public(trip, owner, island, status, opened) VALUES('t1', 'o', 'dao_dua', 'open', 1)")
            db.execute("INSERT INTO island_visitors(trip, guest, status, at) VALUES('t1', 'g', 'in', 1)")

        def catalog():
            with self.store.connect() as db:
                t = sorted(r[0] for r in db.execute('SELECT tablename FROM pg_tables WHERE schemaname=current_schema()').fetchall())
                i = sorted(r[0] + ':' + r[1] for r in db.execute('SELECT indexname, indexdef FROM pg_indexes WHERE schemaname=current_schema()').fetchall())
                n = {x: db.execute(f'SELECT COUNT(*) FROM {x}').fetchone()[0] for x in TABLES}
            return t, i, n
        before = catalog()
        self.assertTrue(all(before[2][x] > 0 for x in TABLES), before[2])
        v, n = self.run_old(STARTUP, str(self.store.path), ','.join(TABLES))
        self.assertEqual(int(v), pg_schema.SCHEMA_VERSION)
        self.assertEqual(pg_schema.SCHEMA_VERSION, 58)
        self.assertEqual(n, before[2])
        self.assertEqual(catalog(), before, 'no table or index changed by the old startup')
