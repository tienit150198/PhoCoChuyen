"""🏍️ Tiệm sửa xe and 🩺 Thú y Cỏ May, and a rollback to the release live before them (2.4.71 at fe504023).

Saves: 2.4.71 requires exactly its own careers. Untouched, both are left out of the stored text (engine.DORMANT) and the
save plays there; a save that worked them is refused as it is, plays after `scripts/strip_new_careers.py strip --careers
moto,vet`, and both come back byte for byte with `restore`. The only other new save key is the optional
journey['xe_care'] (a serviced bike's calmer days), which 2.4.71 keeps untouched. No table, no schema change."""
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
RELEASE = 'fe504023'   # 2.4.71 (live)
OLD_LOAD = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action;'
            's=migrate_state(json.load(sys.stdin));validate_state(s);'
            's,_=apply_action(s,"milk_tea","select_career",{});s,_=apply_action(s,"milk_tea","start_day",{});'
            's,_=apply_action(s,"milk_tea","end_day",{"carry_event":True});validate_state(s);print(json.dumps(s,ensure_ascii=False))')
NEW = ('moto', 'vet')


def old_tree(test):
    tmp = tempfile.mkdtemp(prefix='mnl-motovet-')
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
    def test_untouched_they_are_left_out_and_the_save_plays_on_2_4_71(self):
        j = Journey('milk_tea')
        j.act('end_day', carry_event=True)
        j.state['journey']['xe_care'] = dict(v=1, cars={'xe_so': 9})   # the optional key an older build keeps
        stored = dormant_out(j.state)
        for cid in NEW:
            self.assertNotIn(cid, stored['careers'])
            self.assertNotIn(cid, unknown_out(j.state)['careers'])
        out = run_old(self, json.dumps(unknown_out(stored), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = migrate_state(json.loads(out.stdout))
        validate_state(back)
        self.assertEqual(back['journey']['xe_care'], dict(v=1, cars={'xe_so': 9}))
        for cid in NEW:
            self.assertEqual(back['careers'][cid], initial_career(cid))

    def test_worked_they_are_stripped_for_2_4_71_and_restored_byte_for_byte(self):
        sys.path.insert(0, str(ROOT))
        from scripts.strip_new_careers import restore, strip
        s = new_state()
        jr.enable_story(s, 7171)
        s['journey'].update(gender='female', chapter=4, done=[1, 2, 3])
        s['careers']['vet']['job'] = hired_record('vet')
        played = None
        for cid, prefix in (('moto', 'xm_'), ('vet', 'ty_')):
            j = Journey.__new__(Journey)
            j.career, j.state = cid, (played or s)
            j.act('select_career')
            j.act('start_day')
            j.act(prefix + 'intro')
            content = PLUGINS[cid]
            scripts = __import__(f'game.careers.{cid}_content', fromlist=['DESK']).DESK
            work(j, prefix, scripts, j.c['tasks'][0]['id'])
            j.act(prefix + 'svc', order='sv_' + 'c3' * 12, service=content.SERVICES[0])
            j.act('end_day', carry_event=True)
            played = json.loads(json.dumps(j.state))
        for cid in NEW:
            self.assertIn(cid, dormant_out(played)['careers'], 'worked: stored as it is')
        others = [c for c in ('reception', 'teller', 'restore', 'research', 'radio')]
        refused = run_old(self, json.dumps(unknown_out(dormant_out(played), others), ensure_ascii=False))
        self.assertNotEqual(refused.returncode, 0, 'the old build refuses worked careers as they are')
        stripped, removed = strip(played, list(NEW))
        self.assertTrue(set(NEW) <= set(removed))
        out = run_old(self, json.dumps(unknown_out(dormant_out(stripped)), ensure_ascii=False))
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
