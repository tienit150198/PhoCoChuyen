"""📻 Đài phát thanh Sóng Mây and rollbacks to the release live before it (2.4.66 at a808cb79).

Saves: 2.4.66 requires exactly its own careers. An untouched station is left out of the stored text (engine.DORMANT) and the
save plays there; a save that worked the station is refused as it is, plays after `scripts/strip_new_careers.py strip
--careers radio`, and the station comes back byte for byte with `restore`. Nothing else in a save is new.

Database: 2.4.66 starts on a database at SCHEMA_VERSION 70 holding radio_lines (an aired ad, a hidden song) and the radio
orders of Phố dịch vụ: no DDL (same tables, same indexes, the version never lowered), every row kept, and its ticker
(/api/news) answers without the radio lines it does not know."""
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

from game import journey as jr
from game import pg_schema
from game import radio_station as rs
from game.employment import hired_record
from game.engine import dormant_out, initial_career, migrate_state, new_state, validate_state
from tests.helpers import Journey, unknown_out
from tests.test_career_radio import clear_desk, shift, solve
from tests.test_radio_station import Base

ROOT = Path(__file__).resolve().parents[1]
RELEASE = '5ba2e147'   # 2.4.67 (live; 2.4.66 a808cb79 before it): schema 73 (bang_code), none of this branch's tables or careers
OLD_LOAD = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action;'
            's=migrate_state(json.load(sys.stdin));validate_state(s);'
            's,_=apply_action(s,"milk_tea","select_career",{});s,_=apply_action(s,"milk_tea","start_day",{});'
            's,_=apply_action(s,"milk_tea","end_day",{"carry_event":True});validate_state(s);print(json.dumps(s,ensure_ascii=False))')
DB_PROG = '''import json,sys
from game.storage import Store
from game import marriage
store=Store(sys.argv[1],story=True)
out={}
with store.connect() as db:
    out['v']=db.execute("SELECT value FROM mnl_meta WHERE key='schema_version'").fetchone()[0]
    out['n']={t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in sys.argv[2].split(',')}
out['news']=sorted(marriage.news(store,0,None))
store.close_pool()
print(json.dumps(out))
'''
TABLES = ('radio_lines', 'svc_orders', 'svc_settings')


def old_tree(test):
    tmp = tempfile.mkdtemp(prefix='mnl-radio-')
    test.addCleanup(shutil.rmtree, tmp, True)
    try:
        data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference', 'live', 'i18n'], cwd=ROOT, capture_output=True, timeout=120,
                              check=True).stdout
    except (OSError, subprocess.SubprocessError):
        test.skipTest(f'no git tree with {RELEASE}')
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(tmp, filter='data')
    return Path(tmp)


def run_old(test, args, stdin=None, prog=OLD_LOAD):
    old = old_tree(test)
    env = dict(os.environ, PYTHONPATH=str(old), PYTHONUTF8='1')
    return subprocess.run([sys.executable, '-c', prog, *args], input=stdin, capture_output=True, text=True, cwd=old, env=env,
                          encoding='utf-8', timeout=300)


class Saves(unittest.TestCase):
    def test_an_untouched_station_is_left_out_and_the_save_plays_on_2_4_66(self):
        j = Journey('milk_tea')
        j.act('end_day', carry_event=True)
        stored = dormant_out(j.state)
        self.assertNotIn('radio', stored['careers'])
        self.assertNotIn('radio', unknown_out(j.state)['careers'])   # tests.helpers.NEWER_THAN_LIVE
        out = run_old(self, (), json.dumps(stored, ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = migrate_state(json.loads(out.stdout))   # forward again: the station comes back fresh
        validate_state(back)
        self.assertEqual(back['careers']['radio'], initial_career('radio'))

    def test_a_worked_station_is_stripped_for_2_4_66_and_restored_byte_for_byte(self):
        sys.path.insert(0, str(ROOT))
        from scripts.strip_new_careers import restore, strip
        s = new_state()
        jr.enable_story(s, 7070)
        s['journey'].update(gender='female', chapter=3, done=[1, 2])
        s['careers']['radio']['job'] = hired_record('radio')
        j = Journey.__new__(Journey)
        j.career, j.state = 'radio', s
        j.act('select_career')
        j.act('start_day')
        j.act('rd_intro')
        shift(j, 'open')
        solve(j, j.c['tasks'][0]['id'])
        clear_desk(j)
        j.act('end_day', carry_event=True)
        played = json.loads(json.dumps(j.state))
        self.assertIn('radio', dormant_out(played)['careers'], 'worked: stored as it is')
        refused = run_old(self, (), json.dumps(dormant_out(played), ensure_ascii=False))
        self.assertNotEqual(refused.returncode, 0, 'the old build refuses a worked station as it is')
        stripped, removed = strip(played, ['radio'])
        self.assertIn('radio', removed)
        out = run_old(self, (), json.dumps(dormant_out(stripped), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = json.loads(out.stdout)
        again, problems = restore(migrate_state(back), removed)
        self.assertEqual(problems, [])
        again = migrate_state(again)
        validate_state(again)
        self.assertEqual(json.dumps(again['careers']['radio'], sort_keys=True), json.dumps(played['careers']['radio'], sort_keys=True))


class Database(Base):
    def test_2_4_66_starts_on_schema_70_with_radio_rows_and_keeps_them(self):
        d, b = self.dj(), self.user('rdc_buyer')
        self.sell(d)
        self.air(d, self.buy(b, d))
        dj = self.dj('rdc_star', promoted=True)
        self.sell(dj, rs.SONG)
        o = self.buy(b, dj, rs.SONG, note='Gửi mẹ: con thương mẹ nhiều lắm')
        self.air(dj, o, pick='song_que')
        line = [x for x in self.lines() if x['order_id'] == o['id']][0]
        rs.post(self.store, b, None, 'hide', dict(line=line['id']))
        with self.store.connect() as db:
            before = {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES}
            cat = sorted(r[0] + ':' + r[1] for r in db.execute('SELECT indexname, indexdef FROM pg_indexes WHERE schemaname=current_schema()').fetchall())
        self.assertEqual(before['radio_lines'], 2)
        out = run_old(self, (str(self.store.path), ','.join(TABLES)), prog=DB_PROG)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        got = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertEqual(int(got['v']), pg_schema.SCHEMA_VERSION, 'the old release never lowers the version (no DDL)')
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 70)
        self.assertEqual(got['n'], before, 'every row kept')
        self.assertNotIn('radio', got['news'], 'its ticker does not know the radio lines and still answers')
        with self.store.connect() as db:
            self.assertEqual(sorted(r[0] + ':' + r[1] for r in db.execute('SELECT indexname, indexdef FROM pg_indexes WHERE schemaname=current_schema()').fetchall()), cat)
        rs.stale()
        self.assertEqual(len(rs.ticker(self.store)), 1, 'back on this build: the aired ad still runs, the hidden song stays hidden')


if __name__ == '__main__':
    unittest.main()
