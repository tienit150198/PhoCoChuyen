"""📱 Studio Hẻm Xanh (game/careers/kol.py): an owner's content studio. A deal is one brand brief with one or two awkward
brand demands, worked as server-graded steps (game/careers/stepkit.py): read the brief and name the format → settle the
demands → the format's own steps (hook, script order, shots, products per livestream minute, royalty-free music, posting
time, comments, an honest engagement rate) → the report sent to the right contract. A fee per deal by quality, no
salary; option ids never say which one is right; the answers never reach the client; strict saves; dormant until worked."""
import copy
import json
import unittest

from tests.helpers import Journey
from tests.test_career_moto import data, work, wrong_value
from game import journey as jr
from game.careers import ORDER, PLUGINS, stepkit as sk
from game.engine import DORMANT, GameError, dormant_out, initial_career, public_state, validate_state

K = PLUGINS.get('kol')
if K is not None:
    from game.careers import kol_content as KC


@unittest.skipIf(K is None, 'kol filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_after_vet_dormant_late_unlock_owner_studio(self):
        self.assertEqual(tuple(ORDER[ORDER.index('vet'):ORDER.index('vet') + 4]), ('vet', 'kol', 'singer', 'actor'))
        self.assertIn('kol', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['kol'], 2)
        self.assertEqual((K.SPEC['category'], K.SPEC['prefix']), ('shop', 'ko_'))
        self.assertNotIn('employment', K.SPEC)
        from game.operations import SALARIED
        self.assertNotIn('kol', SALARIED)

    def test_content_has_many_awkward_turns(self):
        self.assertGreaterEqual(len(KC.DEMANDS), 10)
        self.assertGreaterEqual(len(KC.DESK), 10)
        self.assertGreaterEqual(len(KC.DEALS), 6)
        for x in KC.DEMANDS:
            self.assertTrue(x[4] is None or set(x[4]) <= set(KC.DEALS) | {d['plan'] for d in KC.DEALS.values()}, x[1])


@unittest.skipIf(K is None, 'kol filtered out by MNL_CAREERS')
class Deals(unittest.TestCase):
    def test_a_deal_is_pure_and_every_answer_fits_its_step(self):
        seen, lengths, fees = set(), set(), set()
        for day in range(1, 60):
            for slot in range(8):
                dl = K.deal(day, slot)
                self.assertEqual(json.dumps(dl, sort_keys=True), json.dumps(K.deal(day, slot), sort_keys=True))
                ids = [st['id'] for st in dl['steps']]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual((ids[0], ids[-1]), ('brief.dang', 'gui.hop_dong'))
                for st in dl['steps']:
                    self.assertTrue(sk.same(sk.value(st, dl['key'][st['id']]), dl['key'][st['id']]))
                    labels = [o['label'] for o in st.get('options') or ()]
                    self.assertEqual(len(labels), len(set(labels)), st['id'])
                    for o in st.get('options') or ():
                        self.assertRegex(o['id'], r'^[a-j]$', 'neutral ids only')
                self.assertLessEqual(KC.DEALS[dl['deal']]['day'], day)
                seen.add(dl['deal'])
                lengths.add(len(ids))
                fees.add(dl['net'])
        self.assertEqual(seen, set(KC.DEALS))
        self.assertLessEqual(max(lengths), 11, 'a deal stays a few minutes of work')
        self.assertTrue(min(fees) >= 13 and max(fees) <= 24, fees)

    def test_music_is_royalty_free_and_the_report_is_honest(self):
        for day in range(1, 60, 2):
            for slot in range(6):
                dl = K.deal(day, slot)
                for st in dl['steps']:
                    right = dl['key'][st['id']]
                    if st['id'] == 'dung.nhac':
                        label = next(o['label'] for o in st['options'] if o['id'] == right)
                        self.assertNotIn(label, KC.MUSIC_TRAPS)
                    if st['id'] == 'bao_cao.gui_gi':
                        chosen = {o['label'] for o in st['options'] if o['id'] in right}
                        self.assertFalse(chosen & set(KC.REPORT_BAD))

    def test_the_client_never_sees_the_answers_nor_the_format_before_it_is_named(self):
        j = Journey('kol', day=8, slot=2)
        tid = j.task['id']
        v = public_state(j.state)['careers']['kol']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertIsNone(v['needs'])
        j.act('ask', task=tid)
        v = public_state(j.state)['careers']['kol']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertNotIn('deal', v['needs'])
        self.assertNotIn('deal_name', v['needs'])


@unittest.skipIf(K is None, 'kol filtered out by MNL_CAREERS')
class Work(unittest.TestCase):
    def test_a_clean_deal_pays_its_fee(self):
        j = Journey('kol', day=6, slot=1)
        tid = j.task['id']
        n = j.task['needs']
        before = j.c['money']
        out = work(j, 'ko_', KC.DESK)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality'], t['paid']), ('completed', 100, n['net']))
        self.assertTrue(out['celebrate'])
        self.assertEqual((data(j)['today']['jobs'], data(j)['today']['earned']), (1, n['net']))
        self.assertGreaterEqual(j.c['money'] - before, n['net'])
        validate_state(j.state)

    def test_the_certificate_adds_a_xu_to_the_fee(self):
        got = []
        for cert in (False, True):
            j = Journey('kol', day=6, slot=1)
            if cert:
                j.state['journey'].setdefault('certificates', {})[K.CERT_ID] = dict(score=90, best=90, earned_day=1, attempts=1)
            before = j.c['money']
            work(j, 'ko_', KC.DESK)
            got.append(j.c['money'] - before)
            validate_state(j.state)
        self.assertEqual(got[1] - got[0], 1)
        from game import certificate_content as cc
        g = next(x for x in cc.GROUPS if x['id'] == K.CERT_ID)
        self.assertEqual((g['hire'], g['careers']), (False, ('kol',)))

    def test_a_wrong_step_stays_open_and_costs_quality(self):
        j = Journey('kol', day=6, slot=3)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        out = j.act('ko_step', task=tid, step=st['id'], value=wrong_value(st, j.task['_key'][st['id']]))
        self.assertFalse(out['correct'])
        t = j.get(tid)
        self.assertEqual((t['at'], t['wrong'], t['quality'], t['errors']), (0, 1, 100 - KC.WRONG_COST, [st['id']]))
        work(j, 'ko_', KC.DESK, tid)
        t = j.get(tid)
        self.assertEqual(t['paid'], max(5, t['needs']['net'] * (100 - KC.WRONG_COST) // 100))
        validate_state(j.state)

    def test_steps_in_order_only_and_a_tampered_save_is_refused(self):
        j = Journey('kol', day=6, slot=4)
        tid = j.task['id']
        with self.assertRaises(GameError):
            j.act('ko_step', task=tid, step='brief.dang', value='a')   # brief not read yet
        j.act('ask', task=tid)
        steps = j.task['needs']['steps']
        with self.assertRaises(GameError):
            j.act('ko_step', task=tid, step=steps[1]['id'], value='a')
        for field, value in (('quality', 50), ('at', 3), ('paid', 9)):
            s = copy.deepcopy(j.state)
            s['careers']['kol']['tasks'][0][field] = value
            with self.assertRaises(GameError, msg=field):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['kol']['tasks'][0]['needs']['net'] = 99
        with self.assertRaises(GameError):
            validate_state(s)


@unittest.skipIf(K is None, 'kol filtered out by MNL_CAREERS')
class Desk(unittest.TestCase):
    def test_a_scam_ad_blocks_work_until_decided_and_comes_back(self):
        j = Journey('kol', day=8, slot=1)
        d = data(j)
        d['desk'].update(day=j.c['day'], ev=dict(id='desk-1', script='loan_app', day=j.c['day'], at='between'), seq=1, fired=1)
        validate_state(j.state)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        with self.assertRaises(GameError):
            j.act('ko_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        j.act('ko_desk', option='take')
        self.assertIn('scam_ad', data(j)['desk']['marks'])
        self.assertTrue(any(x.get('need_mark') == 'scam_ad' for x in KC.DESK))
        j.act('ko_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        validate_state(j.state)


class Saves(unittest.TestCase):
    def test_untouched_new_careers_are_left_out_of_the_stored_text(self):
        j = Journey('milk_tea')
        for cid in ('kol', 'singer', 'actor'):
            if cid in PLUGINS:
                self.assertEqual(j.state['careers'][cid], initial_career(cid))
                self.assertNotIn(cid, dormant_out(j.state)['careers'])


if __name__ == '__main__':
    unittest.main()
