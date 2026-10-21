"""🎬 Hãng phim Bến Mây (game/careers/actor.py): a salaried TV actor on the series “Ngõ Nhỏ Có Nắng”. A scene is one script
page with one or two awkward crew demands, worked as server-graded steps: read the page and name the scene → settle the
demands → lines in order, the tape mark, [continuity], the director's note, [the takes still needed], [the stunt
routine] (or, at the premiere, the speech, the press and what may be posted) → the costume back on its hook. Salary from
the posting, a small quality bonus per scene; strict saves; dormant until worked."""
import copy
import json
import unittest

from tests.helpers import Journey
from tests.test_career_moto import data, work
from game import journey as jr
from game.careers import ORDER, PLUGINS, stepkit as sk
from game.engine import DORMANT, GameError, public_state, validate_state

V = PLUGINS.get('actor')
if V is not None:
    from game.careers import actor_content as VC


@unittest.skipIf(V is None, 'actor filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_after_singer_dormant_salaried_late_unlock(self):
        self.assertEqual(ORDER[ORDER.index('actor') - 1], 'singer')
        self.assertIn('actor', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['actor'], 3)
        post = V.SPEC['employment']['postings'][0]
        self.assertEqual((post['org'], post['salary']), ('Hãng phim Bến Mây', (58, 76)))
        from game.operations import SALARIED
        self.assertIn('actor', SALARIED)

    def test_content_has_many_awkward_turns(self):
        self.assertGreaterEqual(len(VC.DEMANDS), 10)
        self.assertGreaterEqual(len(VC.DESK), 10)
        self.assertGreaterEqual(len(VC.SCENES), 6)
        for x in VC.DEMANDS:
            self.assertTrue(x[4] is None or set(x[4]) <= set(VC.SCENES), x[1])


@unittest.skipIf(V is None, 'actor filtered out by MNL_CAREERS')
class Scenes(unittest.TestCase):
    def test_a_scene_is_pure_and_every_answer_fits_its_step(self):
        seen, lengths = set(), set()
        for day in range(1, 60):
            for slot in range(8):
                sc = V.scene(day, slot)
                self.assertEqual(json.dumps(sc, sort_keys=True), json.dumps(V.scene(day, slot), sort_keys=True))
                ids = [st['id'] for st in sc['steps']]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual((ids[0], ids[-1]), ('kich_ban.canh', 'phuc_trang.moc'))
                for st in sc['steps']:
                    right = sc['key'][st['id']]
                    self.assertTrue(sk.same(sk.value(st, right), right))
                    labels = [o['label'] for o in st.get('options') or ()]
                    self.assertEqual(len(labels), len(set(labels)), st['id'])
                    if st['id'] == 'quay_lai.luot':
                        self.assertGreater(right, 0)
                if sc['scene'] == 'hanh_dong':
                    self.assertIn('an_toan.thu_tu', ids, 'an action scene always rehearses its stunt safely')
                seen.add(sc['scene'])
                lengths.add(len(ids))
        self.assertEqual(seen, set(VC.SCENES))
        self.assertLessEqual(max(lengths), 10)

    def test_the_client_never_sees_the_answers(self):
        j = Journey('actor', day=8, slot=2)
        tid = j.task['id']
        j.act('ask', task=tid)
        v = public_state(j.state)['careers']['actor']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertNotIn('scene', v['needs'])
        self.assertNotIn('scene_name', v['needs'])


@unittest.skipIf(V is None, 'actor filtered out by MNL_CAREERS')
class Work(unittest.TestCase):
    def test_a_clean_scene_pays_the_quality_bonus(self):
        j = Journey('actor', day=6, slot=1)
        tid = j.task['id']
        out = work(j, 'dn_', VC.DESK)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality'], t['paid']), ('completed', 100, t['needs']['bonus']))
        self.assertTrue(out['celebrate'])
        self.assertEqual(data(j)['today']['bonus'], t['needs']['bonus'])
        validate_state(j.state)

    def test_a_wrong_step_costs_quality_and_the_save_stays_strict(self):
        j = Journey('actor', day=12, slot=5)
        tid = j.task['id']
        work(j, 'dn_', VC.DESK, tid, wrong_at=1)
        t = j.get(tid)
        self.assertEqual((t['wrong'], t['quality']), (1, 100 - VC.WRONG_COST))
        self.assertEqual(t['paid'], max(3, t['needs']['bonus'] * t['quality'] // 100))
        validate_state(j.state)
        s = copy.deepcopy(j.state)
        s['careers']['actor']['tasks'][0]['quality'] = 100
        with self.assertRaises(GameError):
            validate_state(s)

    def test_a_leaked_script_is_remembered_and_comes_back(self):
        j = Journey('actor', day=8, slot=1)
        d = data(j)
        d['desk'].update(day=j.c['day'], ev=dict(id='desk-1', script='script_photo', day=j.c['day'], at='between'), seq=1, fired=1)
        validate_state(j.state)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        with self.assertRaises(GameError):
            j.act('dn_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        j.act('dn_desk', option='join')
        self.assertIn('leaked', data(j)['desk']['marks'])
        self.assertTrue(any(x['id'] == 'leak_found' and x.get('need_mark') == 'leaked' for x in VC.DESK))
        j.act('dn_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        validate_state(j.state)


if __name__ == '__main__':
    unittest.main()
