"""Rollback of the integrated build (Xây trên đảo + Bang + Đấu trường pet + Đảo bang, SCHEMA_VERSION 59 since the review
fixes: the archive tables) to 2.4.60
(e05bacf5): one save holding every new save key at once (journey.islb, journey.bang, pets that fought and were fielded in
the bang war, journey.bang.last with its nonce) validates, migrates and takes a command there, the blocks untouched; and
2.4.60's startup on a database at 59 with rows in every new table (the archive tables too) runs no DDL (same tables, same
indexes, version never lowered, rows kept). 🏝️ 21/10 (SCHEMA_VERSION 62, bangs.isle…): 2.4.65 (live) starts on it without DDL
and keeps playing the bangs (its pages, the island's provider, a deposit, a check-in, a founding), and a bang 2.4.65 founds
there (written without the new columns) holds cấp 1 for free on this build."""
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
PREVIOUS = 'cfc6eb7e'  # 2.4.65: the release live before the bang island purchase (schema 60)

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
          'pet_arena', 'pet_arena_matches', 'pet_war_picks', 'bang_log_old', 'bang_points_old', 'bang_stints_old',
          'pet_arena_matches_old')


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
        self.op(tok, 'isle', to=1, confirm=True)       # 🏝️ the island (21/10): the arena needs it
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
            self.assertRegex(json.loads(before)[1]['last']['r'], r'^[0-9a-f]{16}$', 'the nonce rides along untouched')

    def test_2_4_60_starts_on_schema_62_without_ddl(self):
        self.everything()
        with self.store.connect() as db:
            db.execute("INSERT INTO island_public(trip, owner, island, status, opened) VALUES('t1', 'o', 'dao_dua', 'open', 1)")
            db.execute("INSERT INTO island_visitors(trip, guest, status, at) VALUES('t1', 'g', 'in', 1)")
            db.execute("INSERT INTO bang_log_old(id, bang, sid, kind, text, at, archived_at) VALUES(1, 'b1', '', 'x', 'cũ', 1, 2)")
            db.execute("INSERT INTO bang_points_old(id, bang, sid, kind, pts, week, day, at, archived_at) "
                       "VALUES('w:1', 'b1', 's', 'work', 5, '2026-W33', '2026-08-20', 1, 2)")
            db.execute("INSERT INTO bang_stints_old(id, bang, sid, joined, left_at, why, archived_at) VALUES(1, 'b1', 's', 1, 2, 'leave', 3)")
            db.execute("INSERT INTO pet_arena_matches_old(id, kind, day, week, a, win, engine, data, at, archived_at) "
                       "VALUES('m1', 'npc', '2026-08-20', '2026-W33', 's', 0, 1, '{}', 1, 2)")

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
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 62)   # 63–74: 🛎️ Phố dịch vụ, 📜 bang_code, new careers (new tables only)
        self.assertEqual(n, before[2])
        self.assertEqual(catalog(), before, 'no table or index changed by the old startup')


OLD_BANG = '''import json,sys
from game.storage import Store
from game import bang, bang_island_source as SRC
store=Store(sys.argv[1]);tok,bid,newcomer=sys.argv[2],sys.argv[3],sys.argv[4]
sid=store.key(tok)
page=bang.page(store,sid)
view=SRC.PROVIDER.view(store,bid)
acc=SRC.PROVIDER.access(store,sid,bid)
store.command(tok,'old-give-0001',store.read(tok)[1],None,'jr_bang_give',dict(bang=bid,amount=2000000,confirm=True))
bang.post(store,tok,'checkin',{})
store.command(newcomer,'old-found-001',store.read(newcomer)[1],None,'jr_bang_found',dict(name='Hổ Xám',emoji='🐯',color='vang',confirm=True))
with store.connect() as db:
    v=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    mine=bang._mine(db,store.key(newcomer))
print(json.dumps([v,page['fund'],page['bang']['id'],view['bang_id'],acc['kind'],bang.page(store,sid)['fund'],mine['bang']]))
store.close_pool()
'''


class Previous(Integrated):
    """🏝️ 2.4.65 (live) on a database at SCHEMA_VERSION 62 (the rollout's mixed window, or a rollback)."""

    def old_tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-prev-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', PREVIOUS, 'game', 'reference', 'live'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {PREVIOUS}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    test_one_save_with_every_new_key_plays_on_2_4_60 = None
    test_2_4_60_starts_on_schema_62_without_ddl = None

    def test_live_release_plays_the_bangs_on_schema_62(self):
        from game import bang
        tok, bid = self.everything()
        newcomer = self.player(name='Hà')
        with self.store.connect() as db:
            catalog = sorted(r[0] for r in db.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() "
                                                       "AND table_name='bangs'").fetchall())
            self.assertIn('isle', catalog)
            fund = int(db.execute('SELECT fund FROM bangs WHERE id=?', (bid,)).fetchone()['fund'])
        v, page_fund, page_id, view_id, kind, after, other = self.run_old(OLD_BANG, str(self.store.path), tok, bid, newcomer)
        self.assertEqual((int(v), page_fund, page_id, view_id, kind), (pg_schema.SCHEMA_VERSION, fund, bid, bid, 'member'), 'version never lowered, rows read as they are')
        self.assertEqual(after, fund + 2_000_000, "2.4.65's deposit lands in the fund")
        with self.store.connect() as db:
            r = dict(db.execute('SELECT isle, isle_how FROM bangs WHERE id=?', (bid,)).fetchone())
            self.assertEqual(r, dict(isle=1, isle_how='buy'), 'the purchase is untouched')
            self.assertTrue(bang.has_island(db, other), 'a bang 2.4.65 founded holds cấp 1 (the column default: the grant)')
            self.assertEqual(db.execute('SELECT isle_how FROM bangs WHERE id=?', (other,)).fetchone()['isle_how'], 'grant')
            catalog2 = sorted(r[0] for r in db.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() "
                                                        "AND table_name='bangs'").fetchall())
        self.assertEqual(catalog2, catalog, 'no column changed by the old build')
