"""🔧 Xưởng độ xe and 🏁 Đường đua Bến Mây, and a rollback to the release live before them (2.5.1 at b0159d84).

Saves: 2.5.1 requires exactly its own careers. Untouched, tuning is left out of the stored text (engine.DORMANT) and the
save plays there; a save that worked it is refused as it is, plays after `scripts/strip_new_careers.py strip --careers
tuning`, and it comes back byte for byte with `restore`. The only other new save key is the optional journey['tune'] (the
parts fitted to the player's own vehicles, game/racing.py), which 2.5.1 keeps untouched and this build reads back.
Database: SCHEMA_VERSION 84 adds two tables (race_runs, race_duels); 2.5.1 at 80 neither reads them nor runs any DDL on a
database already past its own version (game/pg_schema.py ensure)."""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import journey as jr
from game import racing as R
from game.engine import dormant_out, initial_career, migrate_state, new_state, validate_state
from game.careers import PLUGINS
from tests.helpers import Journey, unknown_out
from tests.test_bank import act

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'b0159d84'   # 2.5.1 (live)
OLD_LOAD = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action;'
            's=migrate_state(json.load(sys.stdin));validate_state(s);'
            's,_=apply_action(s,"milk_tea","select_career",{});s,_=apply_action(s,"milk_tea","start_day",{});'
            's,_=apply_action(s,"milk_tea","end_day",{"carry_event":True});validate_state(s);print(json.dumps(s,ensure_ascii=False))')


def old_tree(test):
    tmp = tempfile.mkdtemp(prefix='mnl-tuning-')
    test.addCleanup(shutil.rmtree, tmp, True)
    try:
        data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference', 'live', 'i18n'], cwd=ROOT, capture_output=True, timeout=120,
                              check=True).stdout
    except (OSError, subprocess.SubprocessError):
        test.skipTest(f'no git tree with {RELEASE}')
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(tmp, filter='data')
    return Path(tmp)


def run_old(test, stdin):
    old = old_tree(test)
    env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
    return subprocess.run([sys.executable, '-c', OLD_LOAD], input=stdin, capture_output=True, text=True, cwd=old, env=env,
                          encoding='utf-8', timeout=300)


def tuned():
    """journey['tune'] (the optional key) of a story player: a Cub with two parts and a hand-tuned map."""
    s = new_state()
    jr.enable_story(s, 2520)
    s['journey'].update(gender='male', chapter=2, done=[1], wallet=50_000)
    s2, _ = act(s, 'jr_garage_buy', id='xe_so', confirm=True)
    for mod in ('may', 'lop'):
        s2, _ = act(s2, 'jr_tune_buy', id='xe_so', mod=mod)
    R.service_apply(s2, 'do_dong_co')
    return s2['journey']['tune']


@unittest.skipIf('tuning' not in PLUGINS, 'filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def test_untouched_it_is_left_out_and_the_parts_survive_2_5_1(self):
        j = Journey('milk_tea')
        tune = tuned()
        self.assertEqual((tune['cars']['xe_so']['m']['may'], tune['cars']['xe_so']['fx']), (1, {'may': R.FX_RACES}))
        j.state['journey']['tune'] = json.loads(json.dumps(tune))
        validate_state(j.state)
        j.act('end_day', carry_event=True)
        stored = dormant_out(j.state)
        self.assertNotIn('tuning', stored['careers'])
        out = run_old(self, json.dumps(unknown_out(stored), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = migrate_state(json.loads(out.stdout))
        validate_state(back)
        self.assertEqual(back['journey']['tune'], tune, 'kept unread by 2.5.1, read back here')
        self.assertEqual(back['careers']['tuning'], initial_career('tuning'))

    def test_worked_it_is_stripped_for_2_5_1_and_restored_byte_for_byte(self):
        sys.path.insert(0, str(ROOT))
        from scripts.strip_new_careers import restore, strip
        from tests.test_career_tuning import work
        s = new_state()
        jr.enable_story(s, 2510)
        s['journey'].update(gender='female', chapter=4, done=[1, 2, 3])
        j = Journey.__new__(Journey)
        j.career, j.state = 'tuning', s
        j.act('select_career')
        j.act('start_day')
        j.act('dx_intro')
        work(j, j.c['tasks'][0]['id'])
        j.act('dx_svc', order='sv_' + 'd4' * 12, service='do_dong_co')
        j.act('end_day', carry_event=True)
        played = json.loads(json.dumps(j.state))
        self.assertIn('tuning', dormant_out(played)['careers'], 'worked: stored as it is')
        refused = run_old(self, json.dumps(unknown_out(dormant_out(played), ()), ensure_ascii=False))
        self.assertNotEqual(refused.returncode, 0, 'the old build refuses a worked career as it is')
        stripped, removed = strip(played, ['tuning'])
        self.assertIn('tuning', removed)
        out = run_old(self, json.dumps(unknown_out(dormant_out(stripped)), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        again, problems = restore(migrate_state(json.loads(out.stdout)), removed)
        self.assertEqual(problems, [])
        again = migrate_state(again)
        validate_state(again)
        self.assertEqual(json.dumps(again['careers']['tuning'], sort_keys=True), json.dumps(played['careers']['tuning'], sort_keys=True))


class Database(unittest.TestCase):
    def test_new_tables_only_and_2_5_1_runs_no_ddl_past_its_version(self):
        from game import pg_schema
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 84)   # 86: 🤝 friend_charms (a new table only, after these)
        names = [t['name'] for t in pg_schema.TABLES]
        self.assertLess(names.index('race_duels'), names.index('mnl_meta'))
        ddl = pg_schema.TABLES_DDL
        part = ddl[ddl.index('CREATE TABLE IF NOT EXISTS race_runs'):]
        self.assertNotIn('REFERENCES', part, 'no FK')
        self.assertFalse(re.search(r'\b(ALTER|DROP|UPDATE|INSERT)\b', part), 'new tables and indexes only, no backfill')
        old = subprocess.run(['git', 'show', f'{RELEASE}:game/pg_schema.py'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        if old.returncode:
            self.skipTest(f'no git tree with {RELEASE}')
        self.assertIn('SCHEMA_VERSION = 80', old.stdout)
        self.assertNotIn('race_runs', old.stdout)
        # 2.5.1's ensure(): a database at or past its version with none of its own tables missing runs nothing
        self.assertIn('previous_version >= SCHEMA_VERSION and not missing_tables(raw)', old.stdout)


if __name__ == '__main__':
    unittest.main()
