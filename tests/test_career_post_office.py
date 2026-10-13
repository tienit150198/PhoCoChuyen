"""Post-office work: evidence, postage accounting, save safety and long progress."""
import copy
import importlib.util
import json
import unittest


class PostOfficeContract(unittest.TestCase):
    def test_plugin_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('game.careers.post_office'))


def solve(j, limit=100):
    tid = j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    for _ in range(limit):
        t = j.get(tid)
        if t['status'] == 'completed':
            return t
        step = t['needs']['steps'][t['at']]
        j.act('post_step', task=tid, step=step['id'], value=t['_key'][step['id']])
    raise AssertionError('post task did not finish')


@unittest.skipUnless(importlib.util.find_spec('game.careers.post_office'), 'implementation pending')
class PostOfficeJourney(unittest.TestCase):
    def setUp(self):
        from game.careers import post_office
        self.mod = post_office

    def journey(self, day=1, slot=1):
        from tests.helpers import Journey
        return Journey('post_office', day=day, slot=slot)

    def test_complete_pays_bonus_not_postage_and_cannot_repeat(self):
        from game.engine import GameError, validate_state
        j = self.journey()
        tid = j.task['id']
        done = solve(j)
        self.assertEqual(done['at'], len(done['needs']['steps']))
        self.assertEqual(j.c['ext']['data']['stats']['qualified'], 1)
        self.assertEqual(j.c['ext']['data']['stats']['bonus'], 5)
        self.assertGreater(j.c['ext']['data']['stats']['postage'], 0)
        rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('ref') == tid]
        self.assertTrue(rows)
        self.assertFalse(any('postage' in r.get('reason', '') for r in rows))
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('post_step', task=tid, step=done['needs']['steps'][-1]['id'], value='manifest')
        self.assertEqual(j.state, before)
        validate_state(j.state)

    def test_wrong_choice_and_amount_cost_quality_but_can_recover(self):
        j = self.journey()
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.get(tid)['needs']['steps'][0]
        wrong = next(o['id'] for o in st['options'] if o['id'] != j.get(tid)['_key'][st['id']])
        result = j.act('post_step', task=tid, step=st['id'], value=wrong)
        self.assertFalse(result['correct'])
        self.assertEqual(j.get(tid)['at'], 0)
        while j.get(tid)['needs']['steps'][j.get(tid)['at']]['kind'] != 'tariff':
            t = j.get(tid); st = t['needs']['steps'][t['at']]
            j.act('post_step', task=tid, step=st['id'], value=t['_key'][st['id']])
        t = j.get(tid); st = t['needs']['steps'][t['at']]
        result = j.act('post_step', task=tid, step=st['id'], value=999)
        self.assertFalse(result['correct'])
        done = solve(j)
        self.assertEqual(done['mistakes'], 2)
        self.assertEqual(j.c['ext']['data']['stats']['qualified'], 0)
        self.assertEqual(j.c['ext']['data']['stats']['bonus'], 4)

    def test_invalid_and_out_of_order_payloads_are_atomic(self):
        from game.engine import GameError
        j = self.journey(); j.act('ask')
        st = j.task['needs']['steps'][0]
        for p in [dict(step=st['id'], value=[]), dict(step=st['id'], value=True),
                  dict(step=st['id'], value='forged'), dict(step='p1.tariff', value=10),
                  dict(step={}, value='match')]:
            before = copy.deepcopy(j.state)
            with self.assertRaises(GameError): j.act('post_step', **p)
            self.assertEqual(j.state, before)

    def test_halfway_roundtrip_and_forged_progress_rejected(self):
        from game.engine import GameError, validate_state
        j = self.journey(day=40); tid = j.task['id']; j.act('ask')
        for _ in range(5):
            t = j.get(tid); st = t['needs']['steps'][t['at']]
            j.act('post_step', step=st['id'], value=t['_key'][st['id']])
        j.state = json.loads(json.dumps(j.state)); validate_state(j.state)
        for field in ('needs', '_key', 'work', 'at'):
            bad = copy.deepcopy(j.state); t = bad['careers']['post_office']['tasks'][0]
            if field == 'needs': t[field]['variant'] = 'fake'
            elif field == '_key': t[field][next(iter(t[field]))] = 'fake'
            elif field == 'work': t[field] = {}
            else: t[field] += 1
            with self.assertRaises(GameError): validate_state(bad)
        self.assertEqual(solve(j)['status'], 'completed')

    def test_public_projection_hides_solutions(self):
        t = self.mod.make_task(40, 2, 1)
        self.assertIsNone(self.mod.public_task(t)['needs'])
        t['known'] = True
        v = self.mod.public_task(t)
        self.assertNotIn('_key', v)
        self.assertNotIn('answer', json.dumps(v))
        self.assertEqual(v['work'], {})
        v['needs']['variant'] = 'tamper'
        self.assertNotEqual(v['needs'], t['needs'])

    def test_content_bands_determinism_and_sixty_day_balance(self):
        variants = set(); kinds = set(); weights = set(); actions = []; bonus = []; postage = []
        for day in range(1, 61):
            for slot in range(8):
                t = self.mod.make_task(day, slot, 7)
                self.assertEqual(t, self.mod.make_task(day, slot, 7))
                self.mod.validate_task(t, copy.deepcopy(t))
                variants.add(t['needs']['variant']); kinds.add(t['kind'])
                weights.update(p['weight_g'] for p in t['needs']['parcels'])
                actions.append(len(t['needs']['steps']))
                bonus.append(t['needs']['bonus']); postage.append(t['needs']['postage'])
        self.assertGreaterEqual(len(variants), 15)
        self.assertGreater(len(weights), 12)
        self.assertEqual(kinds, {'send', 'registered', 'fragile', 'collection', 'return', 'batch'})
        self.assertEqual(min(actions), 8)
        self.assertGreaterEqual(max(actions), 24)
        self.assertTrue(all(4 <= b <= 9 for b in bonus))
        self.assertLess(sum(bonus), sum(postage))
        for day in (1, 4, 10, 20, 40, 60):
            j = self.journey(day=day)
            self.assertEqual(solve(j)['status'], 'completed')

    def test_empty_days_do_not_unlock_accomplishments(self):
        j = self.journey(); d = j.c['ext']['data']
        for day in range(1, 61):
            j.c['day'] = day; self.mod.on_start(j.state, j.c); self.mod.on_close(j.state, j.c)
        self.assertEqual(d['stats']['active_days'], 0)
        self.assertEqual(self.mod.public_data(j.c)['progress']['earned'], [])

    def test_active_days_count_once_with_qualified_jobs(self):
        j = self.journey(); solve(j)
        self.mod.on_close(j.state, j.c); self.mod.on_close(j.state, j.c)
        self.assertEqual(j.c['ext']['data']['stats']['active_days'], 1)
        self.assertEqual(self.mod.public_data(j.c)['progress']['earned'], [])

    def test_forged_numeric_types_in_fixed_data_are_rejected(self):
        from game.engine import GameError
        original = self.mod.make_task(1, 1, 1)
        t = copy.deepcopy(original); t['gen'] = True
        with self.assertRaises(GameError): self.mod.validate_task(t, original)

    def test_intro_explains_work_and_rewards(self):
        intro = self.mod.content()['intro']
        self.assertIn('lead', intro)
        self.assertEqual(len(intro.get('work', [])), 3)

    def test_all_authored_scenarios_complete_and_keep_original_facts(self):
        unseen = {r[0] for r in self.mod.pc.SCENARIOS}
        for day in range(1, 61):
            for slot in range(8):
                raw = self.mod.make_task(day, slot, 1)
                variant = raw['needs']['variant']
                if variant not in unseen: continue
                j = self.journey(day, slot)
                facts = copy.deepcopy(j.task['needs'])
                done = solve(j)
                self.assertEqual(done['needs'], facts)
                self.assertEqual(done['status'], 'completed')
                self.assertEqual(j.c['ext']['data']['stats']['postage'], raw['needs']['postage'])
                unseen.remove(variant)
        self.assertEqual(unseen, set())

    def test_salary_is_paid_only_by_shared_employment_once_at_close(self):
        from game.engine import GameError
        j = self.journey(); solve(j)
        self.assertFalse(any(r.get('category') == 'salary' for r in j.c['ops']['finance']['ledger']))
        j.act('end_day', carry_event=True)
        rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('category') == 'salary']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['amount'], 65)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError): j.act('end_day', carry_event=True)
        self.assertEqual(j.state, before)

    def test_final_milestone_requires_late_batch_work(self):
        j = self.journey(); stats = j.c['ext']['data']['stats']
        stats.update(jobs=180, qualified=180, active_days=45, advanced=0)
        self.assertNotIn('master', self.mod.public_data(j.c)['progress']['earned'])
        stats['advanced'] = 12
        self.assertIn('master', self.mod.public_data(j.c)['progress']['earned'])

    def test_existing_task_mistakes_do_not_qualify_for_progress(self):
        j = self.journey(); j.task['mistakes'] = 1
        solve(j)
        self.assertEqual(j.c['ext']['data']['stats']['qualified'], 0)


if __name__ == '__main__':
    unittest.main()
