"""Laundry: garment constraints, repair, real service margins and active-day mastery."""
import copy
import json
import unittest

from game.careers import PLUGINS, kit
from game.engine import GameError, validate_state
from tests.helpers import Journey


def move(j, tid):
    t = j.get(tid)
    if not t['known']:
        return j.act('ask', task=tid)
    stage = t['stage']
    payload = ({'items': [g['id'] for g in t['needs']['garments']]} if stage == 'inspect' else
               {'checks': ['count', 'stains', 'dry', 'finish', 'tag']} if stage == 'check' else
               {'tag': t['needs']['tag']} if stage == 'deliver' else {'choices': t['_key'][stage]})
    return j.act('ld_' + stage, task=tid, **payload)


def solve(j, tid):
    for _ in range(12):
        if j.get(tid)['status'] == 'completed':
            return j.get(tid)
        move(j, tid)
    raise AssertionError('laundry did not finish')


class LaundryTests(unittest.TestCase):
    def setUp(self):
        self.assertIn('laundry', PLUGINS, 'The new laundry plugin must be registered')
        self.mod = PLUGINS['laundry']

    def test_full_jobs_each_variant_have_balanced_margin_and_single_cost(self):
        seen = set()
        for day in (1, 4, 10, 20, 40):
            for slot in range(12):
                t = self.mod.make_task(day, slot, 1)
                if t['kind'] in seen:
                    continue
                seen.add(t['kind'])
                j = Journey('laundry', day=day, slot=slot)
                tid = j.task['id']
                kit.money(j.state, j.c, -j.c['money'], 'Test empty wallet')
                done = solve(j, tid)
                self.assertEqual(done['quality'], 100)
                rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('ref') == tid]
                costs = [r for r in rows if r['amount'] < 0]
                self.assertEqual(len(costs), 1)
                self.assertGreaterEqual(sum(r['amount'] for r in rows), 12)
                self.assertLessEqual(sum(r['amount'] for r in rows), 28)
                state = copy.deepcopy(j.state)
                with self.assertRaises(GameError):
                    j.act('ld_deliver', task=tid, tag=done['needs']['tag'])
                self.assertEqual(state, j.state)
                validate_state(json.loads(json.dumps(j.state)))
        self.assertGreaterEqual(len(seen), 12)

    def test_wrong_wash_and_customer_tag_can_be_repaired_without_extra_charge(self):
        j = Journey('laundry', day=40, slot=3)
        tid = j.task['id']
        while j.get(tid)['stage'] != 'wash':
            move(j, tid)
        right = j.get(tid)['_key']['wash']
        wrong = {k: 'boil' for k in right}
        j.act('ld_wash', task=tid, choices=wrong)
        self.assertEqual(j.get(tid)['stage'], 'wash')
        self.assertLess(j.get(tid)['quality'], 100)
        while j.get(tid)['stage'] != 'deliver':
            move(j, tid)
        j.act('ld_deliver', task=tid, tag=j.get(tid)['needs']['tag_options'][1])
        self.assertEqual(j.get(tid)['stage'], 'deliver')
        solve(j, tid)
        self.assertEqual(j.c['ext']['data']['stats']['good'], 0)
        self.assertEqual(j.c['ext']['data']['stats']['jobs'], 1)

    def test_invalid_payload_order_and_hidden_facts(self):
        j = Journey('laundry', slot=0)
        tid = j.task['id']
        for action, payload in [('ld_inspect', {'items': []}), ('ld_deliver', {'tag': 'x'})]:
            before = copy.deepcopy(j.state)
            with self.assertRaises(GameError):
                j.act(action, task=tid, **payload)
            self.assertEqual(j.state, before)
        move(j, tid)
        move(j, tid)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('ld_sort', task=tid, choices={'g1': []})
        self.assertEqual(j.state, before)
        public = self.mod.public_task(j.get(tid))
        self.assertNotIn('_key', public)
        forged = copy.deepcopy(j.state)
        forged['careers']['laundry']['tasks'][0]['needs']['cost'] = 0
        with self.assertRaises(GameError):
            validate_state(forged)
        j.state = json.loads(json.dumps(j.state))
        validate_state(j.state)
        solve(j, tid)

    def test_determinism_60_days_and_empty_day_no_mastery(self):
        for day in range(1, 61):
            for slot in range(12):
                t = self.mod.make_task(day, slot, 7)
                self.assertEqual(t, self.mod.make_task(day, slot, 7))
                self.assertGreaterEqual(len(t['needs']['garments']), 2)
                self.assertLessEqual(len(t['needs']['garments']), 4)
                self.mod.validate_task(json.loads(json.dumps(t)), t)
        j = Journey('laundry', slot=0)
        for day in range(1, 61):
            j.c['day'] = day
            self.mod.on_start(j.state, j.c)
            self.mod.on_close(j.state, j.c)
        self.assertEqual(j.c['ext']['data']['stats']['active_days'], 0)
        self.assertFalse(self.mod.public_data(j.c)['mastered'])
        self.mod.on_start(j.state, j.c)
        solve(j, j.task['id'])
        self.mod.on_close(j.state, j.c)
        self.mod.on_close(j.state, j.c)
        self.assertEqual(j.c['ext']['data']['stats']['active_days'], 1)

    def test_every_stage_survives_reload_and_forged_completion_is_rejected(self):
        j = Journey('laundry', day=20, slot=7)
        tid = j.task['id']
        for _ in range(9):
            j.state = json.loads(json.dumps(j.state))
            validate_state(j.state)
            t = j.get(tid)
            public = self.mod.public_task(t)
            self.assertNotIn('_key', json.dumps(public))
            move(j, tid)
        self.assertEqual(j.get(tid)['stage'], 'done')
        validate_state(json.loads(json.dumps(j.state)))
        forged = self.mod.make_task(1, 0, 1)
        forged['status'] = 'completed'
        with self.assertRaises(GameError):
            self.mod.validate_task(forged, self.mod.make_task(1, 0, 1))

    def test_mistakes_each_processing_stage_require_rework(self):
        for stage in ('sort', 'treat', 'wash', 'dry', 'finish'):
            j = Journey('laundry', day=40, slot=1)
            tid = j.task['id']
            while j.get(tid)['stage'] != stage:
                move(j, tid)
            t = j.get(tid)
            wrong = dict(t['_key'][stage])
            first = next(iter(wrong))
            wrong[first] = next(o['id'] for o in self.mod.step_options(stage) if o['id'] != wrong[first])
            j.act('ld_' + stage, task=tid, choices=wrong)
            self.assertEqual(j.get(tid)['quality'], 88)
            self.assertEqual(j.get(tid)['stage'], stage)
            done = solve(j, tid)
            self.assertEqual(done['quality'], 88)
            rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('ref') == tid]
            self.assertEqual(len([r for r in rows if r['amount'] < 0]), 1)
            self.assertEqual(sum(r['amount'] for r in rows), done['needs']['net'] * 88 // 100)

    def test_mastery_requires_both_quality_and_active_days(self):
        j = Journey('laundry', slot=0)
        stats = j.c['ext']['data']['stats']
        for good, days, mastered, expert in [(100,29,False,False),(99,30,False,False),
                                             (100,30,True,False),(180,44,True,False),(180,45,True,True)]:
            stats.update(good=good,jobs=good,active_days=days)
            result = self.mod.public_data(j.c)
            self.assertEqual(result['mastered'], mastered)
            self.assertEqual(result['expert'], expert)


if __name__ == '__main__':
    unittest.main()
