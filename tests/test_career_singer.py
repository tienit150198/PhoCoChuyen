"""🎤 Phòng trà Mây Chiều (game/careers/singer.py): a salaried tea-room singer. A set is one table's wish with one or two
awkward guest demands, worked as server-graded steps: read the room and name the kind of set → settle the demands →
warm up in order → a song from the chord book (never an unlicensed hit) → the sound check → [the minutes left, a request
slip] → [an incident on stage] → the encore → the dedication read to the right table. Salary from the posting, a small
quality bonus per set; strict saves; dormant until worked."""
import copy
import json
import unittest

from tests.helpers import Journey
from tests.test_career_moto import data, work, wrong_value
from game import journey as jr
from game.careers import ORDER, PLUGINS, stepkit as sk
from game.engine import DORMANT, GameError, public_state, validate_state

V = PLUGINS.get('singer')
if V is not None:
    from game.careers import singer_content as VC


@unittest.skipIf(V is None, 'singer filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_after_kol_dormant_salaried_late_unlock(self):
        self.assertEqual(ORDER[ORDER.index('singer') - 1], 'kol')
        self.assertIn('singer', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['singer'], 2)
        post = V.SPEC['employment']['postings'][0]
        self.assertEqual((post['org'], post['salary']), ('Phòng trà Mây Chiều', (54, 70)))
        from game.operations import SALARIED
        self.assertIn('singer', SALARIED)

    def test_content_has_many_awkward_turns(self):
        self.assertGreaterEqual(len(VC.DEMANDS), 10)
        self.assertGreaterEqual(len(VC.DESK), 10)
        self.assertGreaterEqual(len(VC.SETS), 6)
        for x in VC.DEMANDS:
            self.assertTrue(x[4] is None or set(x[4]) <= set(VC.SETS), x[1])


@unittest.skipIf(V is None, 'singer filtered out by MNL_CAREERS')
class Sets(unittest.TestCase):
    def test_a_set_is_pure_and_every_answer_fits_its_step(self):
        seen, lengths = set(), set()
        for day in range(1, 60):
            for slot in range(8):
                ev = V.evening(day, slot)
                self.assertEqual(json.dumps(ev, sort_keys=True), json.dumps(V.evening(day, slot), sort_keys=True))
                ids = [st['id'] for st in ev['steps']]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual((ids[0], ids[-1]), ('phong.kieu', 'loi_chuc.ban'))
                for st in ev['steps']:
                    right = ev['key'][st['id']]
                    self.assertTrue(sk.same(sk.value(st, right), right))
                    labels = [o['label'] for o in st.get('options') or ()]
                    self.assertEqual(len(labels), len(set(labels)), st['id'])
                    if st['id'] == 'so.bai':
                        self.assertNotEqual(next(o['label'] for o in st['options'] if o['id'] == right), VC.SONG_TRAP)
                    if st['id'] == 'gio.con_lai':
                        self.assertGreater(right, 0)
                seen.add(ev['set'])
                lengths.add(len(ids))
        self.assertEqual(seen, set(VC.SETS))
        self.assertLessEqual(max(lengths), 11)

    def test_the_client_never_sees_the_answers(self):
        j = Journey('singer', day=8, slot=2)
        tid = j.task['id']
        j.act('ask', task=tid)
        v = public_state(j.state)['careers']['singer']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertNotIn('set', v['needs'])
        self.assertNotIn('set_name', v['needs'])


@unittest.skipIf(V is None, 'singer filtered out by MNL_CAREERS')
class Work(unittest.TestCase):
    def test_a_clean_set_pays_the_quality_bonus(self):
        j = Journey('singer', day=6, slot=1)
        tid = j.task['id']
        out = work(j, 'cs_', VC.DESK)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality'], t['paid']), ('completed', 100, t['needs']['bonus']))
        self.assertTrue(out['celebrate'])
        self.assertEqual(data(j)['today']['bonus'], t['needs']['bonus'])
        validate_state(j.state)

    def test_a_wrong_step_costs_quality_and_the_save_stays_strict(self):
        j = Journey('singer', day=12, slot=5)
        tid = j.task['id']
        work(j, 'cs_', VC.DESK, tid, wrong_at=1)
        t = j.get(tid)
        self.assertEqual((t['wrong'], t['quality']), (1, 100 - VC.WRONG_COST))
        self.assertEqual(t['paid'], max(3, t['needs']['bonus'] * t['quality'] // 100))
        validate_state(j.state)
        s = copy.deepcopy(j.state)
        s['careers']['singer']['tasks'][0]['paid'] += 5
        with self.assertRaises(GameError):
            validate_state(s)

    def test_lip_sync_is_remembered_and_comes_back(self):
        j = Journey('singer', day=8, slot=1)
        d = data(j)
        d['desk'].update(day=j.c['day'], ev=dict(id='desk-1', script='guest_mime', day=j.c['day'], at='between'), seq=1, fired=1)
        validate_state(j.state)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        with self.assertRaises(GameError):
            j.act('cs_step', task=tid, step=st['id'], value=wrong_value(st, j.task['_key'][st['id']]))
        j.act('cs_desk', option='mime')
        self.assertIn('mimed', data(j)['desk']['marks'])
        self.assertTrue(any(x.get('need_mark') == 'mimed' for x in VC.DESK))
        j.act('cs_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        validate_state(j.state)


if __name__ == '__main__':
    unittest.main()
