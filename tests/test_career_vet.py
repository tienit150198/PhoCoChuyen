"""🩺 Phòng khám Thú y Cỏ May (game/careers/vet.py): a salaried vet. A case is one pet with one problem and one or two
awkward owner demands, worked as server-graded steps: hear the owner and name the problem → settle the demands → the
case's own steps (weighing by difference, a temperature, a dose by weight, a fluid volume, a procedure's order) → the
right pet by its cage slip. Salary from the posting, a small quality bonus per case; strict saves; dormant until worked;
players' pets examined or vaccinated through Phố dịch vụ (ty_svc, game/vet_service.py)."""
import copy
import unittest

from tests.helpers import Journey
from tests.test_career_moto import ORDER_A, data, svc_finish, work, wrong_value
from game import journey as jr
from game.careers import ORDER, PLUGINS, stepkit as sk
from game.engine import DORMANT, GameError, public_state, validate_state

V = PLUGINS.get('vet')
if V is not None:
    from game.careers import vet_content as VC


@unittest.skipIf(V is None, 'vet filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_last_dormant_salaried_late_unlock(self):
        self.assertEqual(ORDER[ORDER.index('moto') + 1], 'vet')   # 🔧 tuning appended after
        self.assertIn('vet', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['vet'], 3)
        post = V.SPEC['employment']['postings'][0]
        self.assertEqual((post['org'], post['salary']), ('Phòng khám Thú y Cỏ May', (56, 72)))
        from game.operations import SALARIED
        self.assertIn('vet', SALARIED)

    def test_content_has_many_awkward_turns(self):
        self.assertGreaterEqual(len(VC.DEMANDS), 10)
        self.assertGreaterEqual(len(VC.DESK), 10)
        self.assertEqual(len(VC.CASES), 8)
        for x in VC.DEMANDS:
            self.assertTrue(x[4] is None or set(x[4]) <= set(VC.CASES) | {'dog', 'cat'}, x[1])


@unittest.skipIf(V is None, 'vet filtered out by MNL_CAREERS')
class Cases(unittest.TestCase):
    def test_a_case_is_pure_and_fits_its_pet(self):
        seen = set()
        for day in range(1, 60, 3):
            for slot in range(6):
                cs = V.case(day, slot)
                self.assertEqual(cs, V.case(day, slot))
                self.assertIn(cs['pet_kind'], VC.CASES[cs['case']]['kinds'])
                ids = [st['id'] for st in cs['steps']]
                self.assertEqual((ids[0], ids[-1]), ('kham.benh', 'tra.be'))
                for st in cs['steps']:
                    self.assertTrue(sk.same(sk.value(st, cs['key'][st['id']]), cs['key'][st['id']]))
                    if st['id'].startswith('chu.'):
                        self.assertFalse(cs['pet_kind'] == 'dog' and 'mèo uống' in st['evidence'], 'a cat-only demand on a dog')
                seen.add(cs['case'])
        self.assertEqual(seen, set(VC.CASES))

    def test_weighing_by_difference_and_doses_by_weight(self):
        for day in range(3, 60):
            for slot in range(8):
                cs = V.case(day, slot)
                if cs['case'] == 'socola' and 'socola.lieu' in cs['key']:
                    st = next(s for s in cs['steps'] if s['id'] == 'socola.can')
                    self.assertEqual(cs['key']['socola.lieu'] * 5, cs['key']['socola.can'])
                    self.assertIn('kg', st['unit'])
                    return
        self.fail('no early chocolate case found')

    def test_the_title_and_the_view_never_give_the_diagnosis_away(self):
        j = Journey('vet', day=8, slot=2)
        tid = j.task['id']
        self.assertNotIn(VC.CASES[j.task['needs']['case']]['name'].lower(), j.task['title'].lower())
        j.act('ask', task=tid)
        v = public_state(j.state)['careers']['vet']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertNotIn('case_name', v['needs'])
        st = j.task['needs']['steps'][0]
        j.act('ty_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        self.assertIn('case_name', public_state(j.state)['careers']['vet']['tasks'][0]['needs'])


@unittest.skipIf(V is None, 'vet filtered out by MNL_CAREERS')
class Work(unittest.TestCase):
    def test_a_clean_case_pays_the_quality_bonus(self):
        j = Journey('vet', day=6, slot=1)
        tid = j.task['id']
        out = work(j, 'ty_', VC.DESK)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality'], t['paid']), ('completed', 100, t['needs']['bonus']))
        self.assertTrue(out['celebrate'])
        self.assertEqual(data(j)['today']['bonus'], t['needs']['bonus'])
        validate_state(j.state)

    def test_a_wrong_step_costs_quality_and_the_save_stays_strict(self):
        j = Journey('vet', day=12, slot=5)
        tid = j.task['id']
        work(j, 'ty_', VC.DESK, tid, wrong_at=1)
        t = j.get(tid)
        self.assertEqual((t['wrong'], t['quality']), (1, 100 - VC.WRONG_COST))
        self.assertEqual(t['paid'], max(3, t['needs']['bonus'] * t['quality'] // 100))
        validate_state(j.state)
        s = copy.deepcopy(j.state)
        s['careers']['vet']['tasks'][0]['paid'] += 5
        with self.assertRaises(GameError):
            validate_state(s)


@unittest.skipIf(V is None, 'vet filtered out by MNL_CAREERS')
class PlayerJobs(unittest.TestCase):
    def test_kham_and_tiem_are_three_steps_each(self):
        for service in V.SERVICES:
            steps, key = V.svc_job(ORDER_A, service)
            self.assertEqual(len(steps), 3)
            self.assertEqual(steps[0]['id'], 'dv.can')
        j = Journey('vet', day=4, slot=1)
        out = svc_finish(j, 'ty_', V.svc_job, ORDER_A, 'tiem')
        self.assertEqual(out['svc_ready'], ORDER_A)
        self.assertEqual(data(j)['svc_ok'], [dict(o=ORDER_A, s='tiem', q=3)])
        with self.assertRaises(GameError):
            j.act('ty_svc', order=ORDER_A, service='spa')
        validate_state(j.state)

    def test_the_clinic_s_effect_on_a_buyer_s_pets(self):
        from game import vet_service as vs
        from game import pets_content as PC
        day = 30
        pets = [dict(n='Lu', h=40, vac=0, t=day), dict(n='Mướp', h=90, vac=day + 5, t=day), dict(n='Ki', h=70, vac=10, t=day)]
        state = {'journey': {'life_day': day, 'pets': {'list': pets, 'stats': {'vet': 0}}}}
        from unittest.mock import patch
        with patch('game.pets.needs_at', lambda p, d: dict(h=p['h'])), patch('game.pets._tick', lambda p, d: None):
            self.assertEqual([p['n'] for p in vs.candidates(state, 'kham')], ['Lu', 'Ki', 'Mướp'][:2 + (90 < PC.FULL)])
            self.assertEqual(vs.apply(state, 'tiem', 4), ['Lu', 'Ki'])
        self.assertEqual(pets[0]['vac'], day + PC.VACCINE['days'] - 1)
        self.assertEqual(pets[0]['h'], max(40 + PC.VACCINE['h'], PC.VACCINE['floor']))
        self.assertEqual(pets[1]['vac'], day + 5, 'still covered: untouched')
        self.assertEqual(state['journey']['pets']['stats']['vet'], 2)


if __name__ == '__main__':
    unittest.main()
