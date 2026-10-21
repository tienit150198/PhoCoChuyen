"""📱 Studio Hẻm Xanh, 🎤 Phòng trà Mây Chiều and 🎬 Hãng phim Bến Mây, and a rollback to the release live before them
(2.5.1, main at b0159d84).

Saves: 2.5.1 requires exactly its own careers. Untouched, the three are left out of the stored text (engine.DORMANT) and
the save plays there; a save that worked them is refused as it is, plays after `scripts/strip_new_careers.py strip
--careers kol,singer,actor`, and all three come back byte for byte with `restore`. No new save key, no table, no schema
change."""
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
from game.employment import hired_record
from game.engine import dormant_out, initial_career, migrate_state, new_state, validate_state
from tests.helpers import Journey, unknown_out
from tests.test_career_moto import work
from game.careers import PLUGINS

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'b0159d84'   # 2.5.1 (live)
OLD_LOAD = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action;'
            's=migrate_state(json.load(sys.stdin));validate_state(s);'
            's,_=apply_action(s,"milk_tea","select_career",{});s,_=apply_action(s,"milk_tea","start_day",{});'
            's,_=apply_action(s,"milk_tea","end_day",{"carry_event":True});validate_state(s);print(json.dumps(s,ensure_ascii=False))')
NEW = ('kol', 'singer', 'actor')
PREFIX = dict(kol='ko_', singer='cs_', actor='dn_')


def old_tree(test):
    tmp = tempfile.mkdtemp(prefix='mnl-kolsa-')
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


@unittest.skipIf(any(c not in PLUGINS for c in NEW), 'filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def test_untouched_they_are_left_out_and_the_save_plays_on_2_5_1(self):
        j = Journey('milk_tea')
        j.act('end_day', carry_event=True)
        stored = dormant_out(j.state)
        for cid in NEW:
            self.assertNotIn(cid, stored['careers'])
        out = run_old(self, json.dumps(unknown_out(stored, NEW), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = migrate_state(json.loads(out.stdout))
        validate_state(back)
        for cid in NEW:
            self.assertEqual(back['careers'][cid], initial_career(cid))

    def test_worked_they_are_stripped_for_2_5_1_and_restored_byte_for_byte(self):
        sys.path.insert(0, str(ROOT))
        from scripts.strip_new_careers import restore, strip
        s = new_state()
        jr.enable_story(s, 7272)
        s['journey'].update(gender='female', chapter=4, done=[1, 2, 3])
        s['careers']['singer']['job'] = hired_record('singer')
        s['careers']['actor']['job'] = hired_record('actor')
        played = None
        for cid in NEW:
            prefix = PREFIX[cid]
            j = Journey.__new__(Journey)
            j.career, j.state = cid, (played or s)
            j.act('select_career')
            j.act('start_day')
            j.act(prefix + 'intro')
            scripts = __import__(f'game.careers.{cid}_content', fromlist=['DESK']).DESK
            work(j, prefix, scripts, j.c['tasks'][0]['id'])
            j.act('end_day', carry_event=True)
            played = json.loads(json.dumps(j.state))
        for cid in NEW:
            self.assertIn(cid, dormant_out(played)['careers'], 'worked: stored as it is')
        refused = run_old(self, json.dumps(unknown_out(dormant_out(played), ()), ensure_ascii=False))
        self.assertNotEqual(refused.returncode, 0, 'the old build refuses worked careers as they are')
        stripped, removed = strip(played, list(NEW))
        self.assertTrue(set(NEW) <= set(removed))
        out = run_old(self, json.dumps(unknown_out(dormant_out(stripped), NEW), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = json.loads(out.stdout)
        again, problems = restore(migrate_state(back), removed)
        self.assertEqual(problems, [])
        again = migrate_state(again)
        validate_state(again)
        for cid in NEW:
            self.assertEqual(json.dumps(again['careers'][cid], sort_keys=True), json.dumps(played['careers'][cid], sort_keys=True))


if __name__ == '__main__':
    unittest.main()
