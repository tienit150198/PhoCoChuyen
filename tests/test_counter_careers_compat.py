"""🍱 Căn tin trường and ✏️ Tiệm văn phòng phẩm, and a rollback to the release before them (2.5.2.4 at d4eb098b).

Saves: 2.5.2.4 requires exactly its own careers. Untouched, both are left out of the stored text (engine.DORMANT) and the
save plays there; a save that worked them is refused as it is, plays after `scripts/strip_new_careers.py strip --careers
canteen,stationery` (which also takes their certificates), and both come back byte for byte with `restore`. Neither
career writes any other save key. No table, no schema change."""
import json
import sys
import unittest

from game import journey as jr
from game.careers import PLUGINS
from game.engine import dormant_out, initial_career, migrate_state, new_state, validate_state
from tests import test_moto_vet_compat as mv
from tests.helpers import NEWER_THAN_LIVE, Journey, unknown_out
from tests.test_career_canteen import solve as ct_solve
from tests.test_career_stationery import solve as vp_solve

ROOT = mv.ROOT
NEW = ('canteen', 'stationery')
CERTS = ('canteen_basics', 'stationery_basics')


def run_old(test, stdin):
    mv.RELEASE = 'd4eb098b'   # 2.5.2.4
    return mv.run_old(test, stdin)


@unittest.skipIf(any(c not in PLUGINS for c in NEW), 'filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def tearDown(self):
        mv.RELEASE = 'fe504023'

    def test_untouched_they_are_left_out_and_the_save_plays_on_2_5_2_4(self):
        j = Journey('milk_tea')
        j.act('end_day', carry_event=True)
        stored = dormant_out(j.state)
        for cid in NEW:
            self.assertNotIn(cid, stored['careers'])
        out = run_old(self, json.dumps(unknown_out(stored), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = migrate_state(json.loads(out.stdout))
        validate_state(back)
        for cid in NEW:
            self.assertEqual(back['careers'][cid], initial_career(cid))

    def test_worked_they_are_stripped_for_2_5_2_4_and_restored_byte_for_byte(self):
        sys.path.insert(0, str(ROOT))
        from scripts.strip_new_careers import restore, strip
        s = new_state()
        jr.enable_story(s, 7272)
        s['journey'].update(gender='female', chapter=2, done=[1])
        certs = s['journey'].setdefault('certificates', {})
        for cert in CERTS:
            certs[cert] = dict(score=90, best=90, earned_day=1, attempts=1)
        played = None
        for cid, prefix, solve in (('canteen', 'ct_', ct_solve), ('stationery', 'vp_', vp_solve)):
            j = Journey.__new__(Journey)
            j.career, j.state = cid, (played or s)
            j.act('select_career')
            j.act('start_day')
            j.act(prefix + 'intro')
            tid = j.c['tasks'][0]['id']
            solve(j, tid)
            self.assertEqual(j.get(tid)['status'], 'completed')
            j.act('end_day', carry_event=True)
            played = json.loads(json.dumps(j.state))
        for cid in NEW:
            self.assertIn(cid, dormant_out(played)['careers'], 'worked: stored as it is')
        others = tuple(c for c in NEWER_THAN_LIVE if c not in NEW)
        refused = run_old(self, json.dumps(unknown_out(dormant_out(played), others), ensure_ascii=False))
        self.assertNotEqual(refused.returncode, 0, 'the old build refuses worked careers as they are')
        stripped, removed = strip(played, list(NEW))
        self.assertTrue(set(NEW) <= set(removed))
        for cert in CERTS:
            self.assertNotIn(cert, stripped['journey'].get('certificates') or {})
        out = run_old(self, json.dumps(unknown_out(dormant_out(stripped)), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        again, problems = restore(migrate_state(json.loads(out.stdout)), removed)
        self.assertEqual(problems, [])
        again = migrate_state(again)
        validate_state(again)
        for cid in NEW:
            self.assertEqual(json.dumps(again['careers'][cid], sort_keys=True), json.dumps(played['careers'][cid], sort_keys=True))
        for cert in CERTS:
            self.assertEqual(again['journey']['certificates'][cert], played['journey']['certificates'][cert])


if __name__ == '__main__':
    unittest.main()
