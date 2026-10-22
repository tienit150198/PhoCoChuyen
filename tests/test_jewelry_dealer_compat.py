"""💍 Tiệm vàng Ngọc Mây and 🚗 Đại lý xe Phố Mây, and a rollback to the release before them (2.5.1 at b0159d84).

Saves: 2.5.1 requires exactly its own careers. Untouched, both are left out of the stored text (engine.DORMANT) and the
save plays there; a save that worked them is refused as it is, plays after `scripts/strip_new_careers.py strip --careers
jewelry,car_dealer`, and both come back byte for byte with `restore`. The only other save key they touch is the optional
journey['xe_care'] (a serviced car's calmer days, the same key as 🏍️'s bikes), which 2.5.1 keeps untouched. No table,
no schema change."""
import json
import sys
import unittest

from game import journey as jr
from game.careers import PLUGINS
from game.engine import dormant_out, initial_career, migrate_state, new_state, validate_state
from tests import test_moto_vet_compat as mv
from tests.helpers import Journey, unknown_out
from tests.test_career_car_dealer import work as dx_work
from tests.test_career_jewelry import work as vg_work

ROOT = mv.ROOT
NEW = ('jewelry', 'car_dealer')


def run_old(test, stdin):
    mv.RELEASE = 'b0159d84'   # 2.5.1
    return mv.run_old(test, stdin)


@unittest.skipIf(any(c not in PLUGINS for c in NEW), 'filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def tearDown(self):
        mv.RELEASE = 'fe504023'

    def test_untouched_they_are_left_out_and_the_save_plays_on_2_5_1(self):
        j = Journey('milk_tea')
        j.act('end_day', carry_event=True)
        j.state['journey']['xe_care'] = dict(v=1, cars={'o_to_mini': 9})
        stored = dormant_out(j.state)
        for cid in NEW:
            self.assertNotIn(cid, stored['careers'])
        out = run_old(self, json.dumps(unknown_out(stored), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        back = migrate_state(json.loads(out.stdout))
        validate_state(back)
        self.assertEqual(back['journey']['xe_care'], dict(v=1, cars={'o_to_mini': 9}))
        for cid in NEW:
            self.assertEqual(back['careers'][cid], initial_career(cid))

    def test_worked_they_are_stripped_for_2_5_1_and_restored_byte_for_byte(self):
        sys.path.insert(0, str(ROOT))
        from scripts.strip_new_careers import restore, strip
        s = new_state()
        jr.enable_story(s, 7272)
        s['journey'].update(gender='female', chapter=4, done=[1, 2, 3])
        s['journey'].setdefault('certificates', {})['jewelry_basics'] = dict(score=90, best=90, earned_day=1, attempts=1)
        played = None
        for cid, prefix, work in (('jewelry', 'vg_', vg_work), ('car_dealer', 'dx_', dx_work)):
            j = Journey.__new__(Journey)
            j.career, j.state = cid, (played or s)
            j.act('select_career')
            j.act('start_day')
            j.act(prefix + 'intro')
            work(j, j.c['tasks'][0]['id'])
            self.assertEqual(j.c['ext']['data']['open_day'], j.c['day'])
            if cid == 'car_dealer':
                j.act('dx_svc', order='sv_' + 'f6' * 12, service='bao_duong_oto')
            j.act('end_day', carry_event=True)
            played = json.loads(json.dumps(j.state))
        for cid in NEW:
            self.assertIn(cid, dormant_out(played)['careers'], 'worked: stored as it is')
        others = ('reception', 'teller', 'restore', 'research', 'radio', 'moto', 'vet')
        refused = run_old(self, json.dumps(unknown_out(dormant_out(played), others), ensure_ascii=False))
        self.assertNotEqual(refused.returncode, 0, 'the old build refuses worked careers as they are')
        stripped, removed = strip(played, list(NEW))
        self.assertTrue(set(NEW) <= set(removed))
        self.assertNotIn('jewelry_basics', stripped['journey'].get('certificates') or {})
        out = run_old(self, json.dumps(unknown_out(dormant_out(stripped)), ensure_ascii=False))
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        again, problems = restore(migrate_state(json.loads(out.stdout)), removed)
        self.assertEqual(problems, [])
        again = migrate_state(again)
        validate_state(again)
        for cid in NEW:
            self.assertEqual(json.dumps(again['careers'][cid], sort_keys=True), json.dumps(played['careers'][cid], sort_keys=True))
        self.assertEqual(again['journey']['certificates']['jewelry_basics'], played['journey']['certificates']['jewelry_basics'])


if __name__ == '__main__':
    unittest.main()
