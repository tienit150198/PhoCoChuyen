"""Learning checks are free; promotion progress explains every server-side blocker."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import boba, promotion as pm
from tests.helpers import Journey
from tests.test_milk_tea_ux import fix_order
from tests.test_promotion import employee, owner, story

ROOT = Path(__file__).resolve().parents[1]


class FreeOrderCheck(unittest.TestCase):
    def cup(self, base='milk'):
        j = Journey('milk_tea')
        tid = j.task['id']
        fix_order(j, j.task, dict(base='milk', flavor=None, toppings=[], size='M', sugar=50, ice='little'))
        j.act('ask', task=tid)
        j.act('tea_cup', task=tid, size='M')
        j.act('tea_add', task=tid, item=base)
        return j, tid

    def test_repeated_incomplete_checks_cost_no_mistakes_time_or_patience(self):
        j, tid = self.cup()
        before = (j.c['turn'], j.get(tid).get('patience', 100), j.c['life']['day_waste'])
        for _ in range(5):
            result = j.act('tea_check', task=tid)
            self.assertIn('chưa khớp', result['message'])
            self.assertEqual(j.get(tid)['mistakes'], 0)
            self.assertFalse(j.get(tid)['cup']['checked'])
        self.assertEqual((j.c['turn'], j.get(tid).get('patience', 100), j.c['life']['day_waste']), before)

    def test_matching_check_is_also_free_and_marks_the_cup(self):
        j, tid = self.cup()
        j.act('tea_sugar', task=tid, level=50)
        j.act('tea_ice', task=tid, level='little')
        before = j.c['turn']
        j.act('tea_check', task=tid)
        self.assertTrue(j.get(tid)['cup']['checked'])
        self.assertEqual(j.c['turn'], before)

    def test_discard_still_counts_a_mistake_and_waste(self):
        j, tid = self.cup()
        j.get(tid)['cup']['cost'] = 3  # a cup made from paid stock, rather than the free starter batch
        cost = j.get(tid)['cup']['cost']
        waste = j.c['life']['day_waste']
        j.act('tea_discard', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertEqual(j.c['life']['day_waste'], waste + cost)

    def test_wrong_delivery_still_counts_a_mistake_and_waste(self):
        j, tid = self.cup(base='black')
        j.act('tea_sugar', task=tid, level=50)
        j.act('tea_ice', task=tid, level='little')
        j.act('tea_seal', task=tid)
        j.get(tid)['cup']['cost'] = 3
        waste = j.c['life']['day_waste']
        cost = j.get(tid)['cup']['cost']
        result = j.act('tea_serve', task=tid, confirm=True)
        self.assertFalse(result['correct'])
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertEqual(j.c['life']['day_waste'], waste + cost)
        self.assertFalse(j.get(tid)['cup']['items'])


class PromotionRequirements(unittest.TestCase):
    def projection(self, j, **values):
        rec = pm.record(j.state, j.career, True)
        if pm.track(j.career) == 'emp':
            pm._sync(rec, j.c)
        rec.update(values)
        nxt = pm._next(j.state, j.c, j.career, rec)
        self.assertIn('requirements', nxt)
        self.assertEqual(all(r['met'] for r in nxt['requirements']), pm.ready(j.state, j.c, j.career, rec))
        return nxt, {r['id']: r for r in nxt['requirements']}

    def test_full_day_counter_explains_low_ratio_and_retry_together(self):
        j = employee()
        nxt, req = self.projection(j, good=5, worked=9, wait=2)
        self.assertEqual((nxt['good'], nxt['need']), (5, 5))
        self.assertTrue(req['good']['met'])
        self.assertFalse(req['ratio']['met'])
        self.assertEqual((req['ratio']['good'], req['ratio']['worked'], req['ratio']['need']), (5, 9, 70))
        self.assertFalse(req['wait']['met'])

    def test_ratio_uses_all_good_days_and_exact_threshold(self):
        for good, worked, met in ((7, 10, True), (6, 9, False), (6999, 10000, False), (0, 0, True)):
            with self.subTest(good=good, worked=worked):
                _, req = self.projection(employee(), good=good, worked=worked)
                self.assertEqual(req['ratio']['met'], met)
                self.assertEqual(req['ratio']['good'], good)

    def test_all_owner_gates_are_visible_at_once(self):
        j = owner()
        j.c['metrics']['served'] = 2
        story(j, chapter=2)
        _, req = self.projection(j, rank=3, good=20, worked=20)
        self.assertFalse(req['served']['met'])
        self.assertFalse(req['chapter']['met'])
        self.assertEqual(pm.gate(j.state, j.c, j.career, pm.record(j.state, j.career)), '100 lượt khách (2 rồi)')

    def test_rating_gate_and_customer_count_both_visible(self):
        j = owner()
        j.c['metrics']['served'] = 2
        j.c['feed'] = [dict(stars=3)]
        _, req = self.projection(j, rank=1, good=8, worked=8)
        self.assertFalse(req['served']['met'])
        self.assertFalse(req['rating']['met'])
        j.c['feed'] = []  # no ratings do not block, as in the existing server rule
        _, req = self.projection(j)
        self.assertTrue(req['rating']['met'])

    def test_probation_and_accounting_track_both_visible(self):
        j = employee('corp_accounting')
        j.c['job']['probation'] = True
        _, req = self.projection(j, good=5, worked=5)
        self.assertFalse(req['probation']['met'])
        self.assertFalse(req['care']['met'])

    def test_certificate_or_customer_alternative_is_one_requirement(self):
        j = employee()
        j.c['metrics']['served'] = 0
        _, req = self.projection(j, rank=2, good=12, worked=12)
        self.assertFalse(req['certificate_or_served']['met'])
        j.state['journey']['certificates']['work_safety'] = {'earned_day': 1}
        _, req = self.projection(j)
        self.assertTrue(req['certificate_or_served']['met'])

    def test_pending_review_is_explained_instead_of_ready_again(self):
        _, req = self.projection(employee(), good=7, worked=10, due={'to': 1})
        self.assertFalse(req['review']['met'])

    @unittest.skipUnless(shutil.which('node'), 'node is needed to render the promotion screen')
    def test_screen_and_day_summary_show_ratio_and_wait_blockers(self):
        j = employee()
        self.projection(j, good=5, worked=9, wait=2)
        p = pm.public(j.state, j.c, j.career)
        script = """
import {readFileSync} from 'node:fs';
import {promoView, promoSummary} from './public/js/v4/promo.js';
const p = JSON.parse(readFileSync(0, 'utf8'));
const env = {api:{state:{current:'delivery',careers:{delivery:{promo:p}}},content:{}}};
process.stdout.write(JSON.stringify([promoView(env), promoSummary({good:true,next:p.next})]));
"""
        run = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps(p),
                             text=True, encoding='utf-8', capture_output=True, cwd=ROOT, check=True)
        for html in json.loads(run.stdout):
            self.assertIn('70%', html)
            self.assertIn('5/9', html)
            self.assertIn('2 ngày làm', html)


if __name__ == '__main__':
    unittest.main()
