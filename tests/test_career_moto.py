"""🏍️ Tiệm sửa xe Út Lanh (game/careers/moto.py): an owner's motorbike shop. A ticket is one bike with one fault and one or
two awkward customer demands, worked as server-graded steps (game/careers/stepkit.py): hear and name the fault → settle
the demands → the fault's own hands-on steps → [hand-over checks] → the right bike by its plate. A wrong step stays open
and lowers the quality; parts are advanced and settled once at hand-back; option ids never say which one is right; the
answers never reach the client; strict saves; dormant until worked; players' bikes serviced through Phố dịch vụ
(xm_svc, game/moto_service.py) and calmer for ten days in 🎲 rủi ro."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game import rui
from game.careers import ORDER, PLUGINS, stepkit as sk
from game.engine import DORMANT, GameError, dormant_out, initial_career, public_state, validate_state

M = PLUGINS.get('moto')
if M is not None:
    from game.careers import moto_content as MC


def data(j):
    return j.c['ext']['data']


def wrong_value(st, right):
    typ = st['type']
    if typ == 'choice':
        return next(o['id'] for o in st['options'] if o['id'] != right)
    if typ == 'number':
        return right + 1
    if typ == 'order':
        return list(reversed(right))
    ids = sorted(o['id'] for o in st['options'])
    return [] if right == ids else ids


def clear_desk(j, prefix, scripts):
    ev = data(j)['desk']['ev']
    if ev:
        x = next(x for x in scripts if x['id'] == ev['script'])
        j.act(prefix + 'desk', option=next(o['id'] for o in x['options'] if o.get('good')))


def work(j, prefix, scripts, tid=None, wrong_at=None):
    """Ask, then answer every step with the server's key (one wrong answer first at step `wrong_at`)."""
    tid = tid or j.task['id']
    j.act('ask', task=tid)
    out = None
    for _ in range(40):
        clear_desk(j, prefix, scripts)
        t = j.get(tid)
        if t['status'] == 'completed':
            break
        st = t['needs']['steps'][t['at']]
        right = t['_key'][st['id']]
        if wrong_at is not None and t['at'] == wrong_at and not t['errors']:
            out = j.act(prefix + 'step', task=tid, step=st['id'], value=wrong_value(st, right))
            continue
        out = j.act(prefix + 'step', task=tid, step=st['id'], value=right)
    return out


def svc_finish(j, prefix, job_of, order, service, wrong=0):
    j.act(prefix + 'svc', order=order, service=service)
    steps, key = job_of(order, service)
    out = None
    for i, st in enumerate(steps):
        if i == 0:
            for _ in range(wrong):
                bad = j.act(prefix + 'svc', order=order, service=service, step=st['id'], value=wrong_value(st, key[st['id']]))
                assert bad['correct'] is False
        out = j.act(prefix + 'svc', order=order, service=service, step=st['id'], value=key[st['id']])
    return out


ORDER_A = 'sv_' + 'a1' * 12
ORDER_B = 'sv_' + 'b2' * 12


@unittest.skipIf(M is None, 'moto filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_last_dormant_late_unlock_owner_shop(self):
        self.assertEqual(tuple(ORDER[-2:]), ('moto', 'vet'))
        self.assertIn('moto', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['moto'], 2)
        self.assertEqual(M.SPEC['category'], 'shop')
        self.assertNotIn('employment', M.SPEC)
        self.assertEqual(M.SPEC['prefix'], 'xm_')

    def test_content_has_many_awkward_turns(self):
        self.assertGreaterEqual(len(MC.DEMANDS), 10)
        self.assertGreaterEqual(len(MC.DESK), 10)
        self.assertEqual(len({x['id'] for x in MC.DESK}), len(MC.DESK))
        self.assertEqual(len(MC.FAULTS), 8)


@unittest.skipIf(M is None, 'moto filtered out by MNL_CAREERS')
class Tickets(unittest.TestCase):
    def test_a_ticket_is_pure_and_every_answer_fits_its_step(self):
        faults = set()
        for day in range(1, 60, 3):
            for slot in range(6):
                tk = M.ticket(day, slot)
                self.assertEqual(json.dumps(tk, sort_keys=True), json.dumps(M.ticket(day, slot), sort_keys=True))
                ids = [st['id'] for st in tk['steps']]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual((ids[0], ids[-1]), ('nghe.loi', 'giao.xe'))
                for st in tk['steps']:
                    self.assertTrue(sk.same(sk.value(st, tk['key'][st['id']]), tk['key'][st['id']]))
                    for o in st.get('options') or ():
                        self.assertRegex(o['id'], r'^[a-j]$', 'neutral ids only')
                faults.add(tk['fault'])
                self.assertLessEqual(MC.FAULTS[tk['fault']]['day'], day)
        self.assertEqual(faults, set(MC.FAULTS))

    def test_the_client_never_sees_the_answers_nor_the_fault_before_it_is_named(self):
        j = Journey('moto', day=8, slot=2)
        tid = j.task['id']
        v = public_state(j.state)['careers']['moto']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertIsNone(v['needs'])
        j.act('ask', task=tid)
        v = public_state(j.state)['careers']['moto']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertNotIn('fault', v['needs'])
        self.assertNotIn('fault_name', v['needs'])
        self.assertNotIn(MC.FAULTS[j.task['needs']['fault']]['name'], v['title'])


@unittest.skipIf(M is None, 'moto filtered out by MNL_CAREERS')
class Work(unittest.TestCase):
    def test_a_clean_ticket_pays_labour_and_settles_parts_once(self):
        j = Journey('moto', day=6, slot=1)
        tid = j.task['id']
        n = j.task['needs']
        before = j.c['money']
        out = work(j, 'xm_', MC.DESK)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality'], t['paid']), ('completed', 100, n['net']))
        self.assertTrue(out['celebrate'])
        self.assertEqual(data(j)['today']['jobs'], 1)
        self.assertEqual(data(j)['today']['earned'], n['net'])
        self.assertGreaterEqual(j.c['money'] - before, n['net'] - 1, 'labour kept, parts paid back (gear bonus may add)')
        validate_state(j.state)

    def test_the_certificate_takes_a_xu_off_the_parts(self):
        got = []
        for cert in (False, True):
            j = Journey('moto', day=6, slot=1)
            if cert:
                j.state['journey'].setdefault('certificates', {})[M.CERT_ID] = dict(score=90, best=90, earned_day=1, attempts=1)
            before, cost = j.c['money'], j.task['needs']['cost']
            work(j, 'xm_', MC.DESK)
            got.append(j.c['money'] - before)
            validate_state(j.state)
        self.assertEqual(got[1] - got[0], 1 if cost > 0 else 0)
        from game import certificate_content as cc
        g = next(x for x in cc.GROUPS if x['id'] == M.CERT_ID)
        self.assertEqual((g['hire'], g['careers']), (False, ('moto',)))

    def test_a_wrong_step_stays_open_and_costs_quality(self):
        j = Journey('moto', day=6, slot=3)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        out = j.act('xm_step', task=tid, step=st['id'], value=wrong_value(st, j.task['_key'][st['id']]))
        self.assertFalse(out['correct'])
        t = j.get(tid)
        self.assertEqual((t['at'], t['wrong'], t['quality'], t['errors']), (0, 1, 100 - MC.WRONG_COST, [st['id']]))
        self.assertEqual(t['slips'][0]['code'], st['id'])
        validate_state(j.state)
        work(j, 'xm_', MC.DESK, tid)
        t = j.get(tid)
        self.assertEqual(t['paid'], max(5, t['needs']['net'] * (100 - MC.WRONG_COST) // 100))
        validate_state(j.state)

    def test_steps_in_order_only_and_shapes_checked(self):
        j = Journey('moto', day=6, slot=4)
        tid = j.task['id']
        with self.assertRaises(GameError):
            j.act('xm_step', task=tid, step='nghe.loi', value='a')   # not heard yet
        j.act('ask', task=tid)
        steps = j.task['needs']['steps']
        with self.assertRaises(GameError):
            j.act('xm_step', task=tid, step=steps[1]['id'], value='a')
        with self.assertRaises(GameError):
            j.act('xm_step', task=tid, step=steps[0]['id'], value='z')

    def test_a_tampered_save_is_refused(self):
        j = Journey('moto', day=6, slot=1)
        j.act('ask', task=j.task['id'])
        for field, value in (('quality', 50), ('at', 3), ('paid', 9)):
            s = copy.deepcopy(j.state)
            s['careers']['moto']['tasks'][0][field] = value
            with self.assertRaises(GameError, msg=field):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['moto']['tasks'][0]['needs']['net'] = 99
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['moto']['ext']['data']['svc_ok'] = [dict(o='sv_x', s='bao_duong', q=3)]
        with self.assertRaises(GameError):
            validate_state(s)


@unittest.skipIf(M is None, 'moto filtered out by MNL_CAREERS')
class Desk(unittest.TestCase):
    def test_a_surprise_blocks_work_until_decided_and_marks_come_back(self):
        j = Journey('moto', day=8, slot=1)
        d = data(j)
        d['desk'].update(day=j.c['day'], ev=dict(id='desk-1', script='odometer', day=j.c['day'], at='between'), seq=1, fired=1)
        validate_state(j.state)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        with self.assertRaises(GameError):
            j.act('xm_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        j.act('xm_desk', option='do')
        self.assertIn('odo_faked', data(j)['desk']['marks'])
        self.assertTrue(any(x['id'] == 'odo_buyer' and x.get('need_mark') == 'odo_faked' for x in MC.DESK))
        j.act('xm_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        validate_state(j.state)


@unittest.skipIf(M is None, 'moto filtered out by MNL_CAREERS')
class PlayerJobs(unittest.TestCase):
    def test_a_player_job_is_three_graded_steps_and_lands_in_svc_ok(self):
        j = Journey('moto', day=4, slot=1)
        with self.assertRaises(GameError):
            j.act('xm_svc', order='sv_nope', service='bao_duong')
        out = svc_finish(j, 'xm_', M.svc_job, ORDER_A, 'bao_duong', wrong=1)
        self.assertEqual(out['svc_ready'], ORDER_A)
        d = data(j)
        self.assertEqual((d['svc'], d['svc_ok']), ([], [dict(o=ORDER_A, s='bao_duong', q=2)]))
        self.assertEqual(d['stats']['svc'], 1)
        self.assertEqual(j.act('xm_svc', order=ORDER_A, service='bao_duong')['svc_ready'], ORDER_A, 'a finished job just points to Giao')
        validate_state(j.state)
        self.assertEqual(public_state(j.state)['careers']['moto']['data']['svc_ok'], [ORDER_A])

    def test_open_jobs_are_capped_and_a_stale_one_can_be_dropped(self):
        j = Journey('moto', day=4, slot=1)
        orders = ['sv_' + f'{i:02x}' * 12 for i in range(sk.SVC_OPEN)]
        for o in orders:
            j.act('xm_svc', order=o, service='bao_duong')
        with self.assertRaises(GameError):
            j.act('xm_svc', order=ORDER_B, service='bao_duong')
        j.act('xm_svc', order=orders[0], service='bao_duong', drop=True, confirm=True)
        j.act('xm_svc', order=ORDER_B, service='bao_duong')
        view = public_state(j.state)['careers']['moto']['data']['svc']
        self.assertEqual(len(view), sk.SVC_OPEN)
        self.assertTrue(all(x['step'] and '_key' not in x for x in view))
        validate_state(j.state)

    def test_a_started_job_cannot_be_dropped_to_wipe_its_mistakes(self):
        j = Journey('moto', day=4, slot=1)
        j.act('xm_svc', order=ORDER_A, service='bao_duong')
        steps, key = M.svc_job(ORDER_A, 'bao_duong')
        st = steps[0]
        j.act('xm_svc', order=ORDER_A, service='bao_duong', step=st['id'], value=wrong_value(st, key[st['id']]))
        with self.assertRaises(GameError):
            j.act('xm_svc', order=ORDER_A, service='bao_duong', drop=True, confirm=True)
        out = svc_finish(j, 'xm_', M.svc_job, ORDER_A, 'bao_duong')
        self.assertEqual(data(j)['svc_ok'], [dict(o=ORDER_A, s='bao_duong', q=2)], 'the mistake stays in the grade')
        self.assertEqual(out['svc_ready'], ORDER_A)

    def test_the_job_book_is_checked_on_load(self):
        j = Journey('moto', day=4, slot=1)
        svc_finish(j, 'xm_', M.svc_job, ORDER_A, 'bao_duong')
        j.act('xm_svc', order=ORDER_B, service='bao_duong')
        validate_state(j.state)
        for bad in (lambda d: d['svc_ok'].append(dict(d['svc_ok'][0])),                       # finished twice
                    lambda d: d['svc_ok'].append(dict(o=ORDER_B, s='bao_duong', q=3)),         # open and finished
                    lambda d: d['svc_ok'][0].update(q=True)):                                  # a bool is not a grade
            s = copy.deepcopy(j.state)
            bad(s['careers']['moto']['ext']['data'])
            with self.assertRaises(GameError):
                validate_state(s)


@unittest.skipIf(M is None, 'moto filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def test_an_untouched_shop_is_left_out_of_the_stored_text(self):
        j = Journey('milk_tea')
        self.assertEqual(j.state['careers']['moto'], initial_career('moto'))
        self.assertNotIn('moto', dormant_out(j.state)['careers'])
        self.assertNotIn('vet', dormant_out(j.state)['careers'])

    def test_a_serviced_bike_breaks_half_as_often_for_ten_days(self):
        from game import moto_service as ms
        s = {'journey': {'life_day': 20, 'xe_care': {'v': 1, 'cars': {'xe_so': 29}}}}
        self.assertEqual(rui.care_until(s, 'xe_so'), 29)
        self.assertEqual(rui.care_until(s, 'vespa'), 0)
        self.assertEqual(rui.care_until({'journey': {'xe_care': 'odd'}}, 'xe_so'), 0)
        self.assertEqual(ms.CARE_DAYS, 10)


if __name__ == '__main__':
    unittest.main()
