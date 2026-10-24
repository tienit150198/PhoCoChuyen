"""🔧 Xưởng độ xe Tư Pít-tông (game/careers/tuning.py): an owner's tuning shop. A ticket is one customer's car or motorbike
with a goal and a parts budget, worked as server-graded steps (game/careers/stepkit.py): the goal → inspect [→ the papers]
→ the build sheet (the goal's priority list within the budget, the illegal fit left out) → the parts total → the demands
→ fit and read the parts → the dyno chart [→ the AFR line] → [safety] → noise or CO against the notebook → test drive →
the true spec card. A wrong step stays open and lowers the quality; an illegal answer also brings the ward's warning (a
fine and, every third time, the inspection team); parts are advanced and settled once at hand-back; the answers, the
goal before it is named, the build before the sheet is settled and the dyno before the car is on it never reach the
client; strict saves; dormant until worked; players' vehicles tuned through Phố dịch vụ (dx_svc)."""
import copy
import json
import unittest

from tests.helpers import Journey
from tests.test_career_moto import ORDER_A, ORDER_B, clear_desk, svc_finish, wrong_value
from game import journey as jr
from game.careers import ORDER, PLUGINS, stepkit as sk
from game.engine import DORMANT, GameError, dormant_out, initial_career, public_state, validate_state

T = PLUGINS.get('tuning')
if T is not None:
    from game.careers import tuning_content as TC


def data(j):
    return j.c['ext']['data']


def work(j, tid=None, wrong_at=None, illegal=False):
    """Ask, then answer every step with the server's key (one wrong / illegal answer first where asked)."""
    tid = tid or j.task['id']
    j.act('ask', task=tid)
    out = None
    for _ in range(60):
        clear_desk(j, 'dx_', TC.DESK)
        t = j.get(tid)
        if t['status'] == 'completed':
            break
        st = t['needs']['steps'][t['at']]
        right = t['_key'][st['id']]
        if illegal and st['id'] == 'bang.chon' and not t['errors']:
            bad = t['_key'][T.LAW][st['id']]
            out = j.act('dx_step', task=tid, step=st['id'], value=sorted(set(right) | set(bad)))
            continue
        if wrong_at is not None and t['at'] == wrong_at and not t['errors']:
            out = j.act('dx_step', task=tid, step=st['id'], value=wrong_value(st, right))
            continue
        out = j.act('dx_step', task=tid, step=st['id'], value=right)
    return out


@unittest.skipIf(T is None, 'tuning filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_last_dormant_late_unlock_owner_shop(self):
        self.assertEqual(ORDER[ORDER.index('tuning') - 1], 'actor')   # then 💍 jewelry, 🚗 car_dealer, 🍱 canteen, ✏️ stationery
        self.assertIn('tuning', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['tuning'], 2)
        self.assertEqual(T.SPEC['category'], 'shop')
        self.assertNotIn('employment', T.SPEC)
        self.assertEqual(T.SPEC['prefix'], 'dx_')

    def test_content_has_many_awkward_turns_and_every_legal_rule(self):
        self.assertGreaterEqual(len(TC.DEMANDS), 14)
        self.assertGreaterEqual(len(TC.DESK), 12)
        self.assertEqual(len({x['id'] for x in TC.DESK}), len(TC.DESK))
        self.assertEqual(set(TC.GOALS), {'pho', 'show', 'drag', 'deo'})
        self.assertEqual({x['rule'] for x in TC.ILLEGAL.values()}, {'tiếng ồn', 'khí thải', 'đèn', 'biển số'})
        self.assertTrue({d[5] for d in TC.DEMANDS} >= {'khi_thai', 'tieng_on', 'den', 'bien_so'})
        for goal in TC.GOALS.values():
            self.assertTrue(set(goal['prio']) <= set(TC.MODS))


@unittest.skipIf(T is None, 'tuning filtered out by MNL_CAREERS')
class Tickets(unittest.TestCase):
    def test_a_ticket_is_pure_and_every_answer_fits_its_step(self):
        goals, kinds, lengths = set(), set(), []
        for day in range(1, 60, 3):
            for slot in range(6):
                tk = T.ticket(day, slot)
                self.assertEqual(json.dumps(tk, sort_keys=True), json.dumps(T.ticket(day, slot), sort_keys=True))
                ids = [st['id'] for st in tk['steps']]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual((ids[0], ids[-1]), ('nghe.muc_tieu', 'giao.the'))
                self.assertIn('bang.chon', ids)
                self.assertIn('dyno.doc', ids)
                for st in tk['steps']:
                    self.assertTrue(sk.same(sk.value(st, tk['key'][st['id']]), tk['key'][st['id']]))
                    for o in st.get('options') or ():
                        self.assertRegex(o['id'], r'^[a-j]$', 'neutral ids only')
                self.assertLessEqual(TC.GOALS[tk['goal']]['day'], day)
                goals.add(tk['goal'])
                kinds.add(tk['kind'])
                lengths.append(len(ids))
        self.assertEqual(goals, set(TC.GOALS))
        self.assertEqual(kinds, {'bike', 'car'})
        self.assertTrue(10 <= min(lengths) and max(lengths) <= 18, (min(lengths), max(lengths)))

    def test_the_build_is_the_priority_list_within_the_budget_and_one_option_is_illegal(self):
        for day in range(1, 40, 2):
            for slot in range(5):
                tk = T.ticket(day, slot)
                build = T.build_of(tk['goal'], tk['kind'], tk['budget'])
                self.assertEqual(tk['build'], build)
                self.assertTrue(build, 'a build always has a part')
                self.assertLessEqual(tk['cost'], tk['budget'])
                self.assertEqual(tk['cost'], sum(T.cost_of(m, tk['kind']) for m in build))
                if tk['kind'] == 'bike':
                    self.assertFalse({'turbo', 'khi_dong'} & set(build), 'no turbo, no wing on a bike')
                law = tk['key'][T.LAW]
                self.assertEqual(len(law['bang.chon']), 1)
                self.assertNotIn(law['bang.chon'][0], tk['key']['bang.chon'])
                self.assertEqual(tk['key']['bang.tong'], tk['cost'])
                d = tk['dyno']
                self.assertEqual(len(d['rpm']), len(d['before']))
                self.assertEqual(len(d['rpm']), len(d['afr']))
                self.assertEqual(tk['key']['dyno.doc'], max(d['after']) - max(d['before']) if d['gain'] else max(d['after']))

    def test_the_client_never_sees_the_answers_the_goal_the_build_nor_the_dyno_early(self):
        j = Journey('tuning', day=12, slot=2)
        tid = j.task['id']
        v = public_state(j.state)['careers']['tuning']['tasks'][0]
        self.assertNotIn('_key', v)
        self.assertIsNone(v['needs'])
        j.act('ask', task=tid)
        v = public_state(j.state)['careers']['tuning']['tasks'][0]
        self.assertNotIn('_key', v)
        for k in ('goal', 'goal_name', 'build', 'cost', 'dyno'):
            self.assertNotIn(k, v['needs'])
        self.assertTrue(all(st['title'] == '' for st in v['needs']['steps'][1:]), 'later steps are blank stubs')
        self.assertTrue(all('options' not in st for st in v['needs']['steps'][1:]), 'no parts list before the goal is set')


@unittest.skipIf(T is None, 'tuning filtered out by MNL_CAREERS')
class Work(unittest.TestCase):
    def test_a_clean_ticket_pays_labour_and_settles_parts_once(self):
        j = Journey('tuning', day=6, slot=1)
        tid = j.task['id']
        n = j.task['needs']
        before = j.c['money']
        out = work(j)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality'], t['paid']), ('completed', 100, n['net']))
        self.assertTrue(out['celebrate'])
        self.assertEqual(data(j)['today']['jobs'], 1)
        self.assertEqual(data(j)['today']['earned'], n['net'])
        self.assertGreaterEqual(j.c['money'] - before, n['net'] - 1, 'labour kept, parts paid back (gear bonus may add)')
        self.assertEqual(data(j)['legal'], dict(warn=0, fined=0))
        validate_state(j.state)
        # the dyno sheet is public once the car has been on it
        v = public_state(j.state)['careers']['tuning']['tasks'][0]
        self.assertIn('dyno', v['needs'])

    def test_a_wrong_dyno_reading_points_at_the_numbers_then_works_it_out(self):
        """#524 (a blind player 'nhập mò' until the third try): the dyno sheet's numbers are public once the car is on it
        (the client reads them out under 📋 Đọc số liệu); a wrong reading says where to look, the second shows the peaks."""
        j = Journey('tuning', day=6, slot=1)
        tid = j.task['id']
        j.act('ask', task=tid)
        while True:
            clear_desk(j, 'dx_', TC.DESK)
            t = j.get(tid)
            st = t['needs']['steps'][t['at']]
            if st['id'] == 'dyno.doc':
                break
            j.act('dx_step', task=tid, step=st['id'], value=t['_key'][st['id']])
        d = public_state(j.state)['careers']['tuning']['tasks'][0]['needs']['dyno']
        right = t['_key']['dyno.doc']
        a, b = max(d['after']), max(d['before'])
        self.assertEqual(right, a - b if d['gain'] else a, 'the public numbers are enough to answer exactly')
        first = j.act('dx_step', task=tid, step='dyno.doc', value=right + 1)
        self.assertIn('📋 Đọc số liệu', first['message'])
        second = j.act('dx_step', task=tid, step='dyno.doc', value=right + 1)
        ra = T._thousands(d['rpm'][d['after'].index(a)])
        self.assertIn(f'Anh Tư chỉ: đỉnh {"sau độ" if d["gain"] else "công suất"} {a} mã lực ở {ra} vòng/phút', second['message'])
        self.assertTrue(second['message'].endswith(f'= {right} mã lực.' if d['gain'] else f'{ra} vòng/phút.'))
        j.act('dx_step', task=tid, step='dyno.doc', value=right)
        validate_state(j.state)

    def test_the_certificate_takes_two_xu_off_the_parts(self):
        got = []
        for cert in (False, True):
            j = Journey('tuning', day=6, slot=1)
            if cert:
                j.state['journey'].setdefault('certificates', {})[T.CERT_ID] = dict(score=90, best=90, earned_day=1, attempts=1)
            before, cost = j.c['money'], j.task['needs']['cost']
            work(j)
            got.append(j.c['money'] - before)
            validate_state(j.state)
        self.assertEqual(got[1] - got[0], min(2, cost))
        from game import certificate_content as cc
        g = next(x for x in cc.GROUPS if x['id'] == T.CERT_ID)
        self.assertEqual((g['hire'], g['careers']), (False, ('tuning',)))

    def test_a_wrong_step_stays_open_and_costs_quality(self):
        j = Journey('tuning', day=6, slot=3)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        out = j.act('dx_step', task=tid, step=st['id'], value=wrong_value(st, j.task['_key'][st['id']]))
        self.assertFalse(out['correct'])
        t = j.get(tid)
        self.assertEqual((t['at'], t['wrong'], t['quality'], t['errors']), (0, 1, 100 - TC.WRONG_COST, [st['id']]))
        validate_state(j.state)
        work(j, tid)
        t = j.get(tid)
        self.assertEqual(t['paid'], max(6, t['needs']['net'] * (100 - TC.WRONG_COST) // 100))
        validate_state(j.state)

    def test_an_illegal_fit_is_a_wrong_step_plus_the_wards_warning(self):
        j = Journey('tuning', day=6, slot=2)
        tid = j.task['id']
        before = j.c['money']
        work(j, tid, illegal=True)
        t = j.get(tid)
        self.assertEqual(t['errors'], ['bang.chon'])
        self.assertEqual(data(j)['legal'], dict(warn=1, fined=TC.LEGAL_FINE))
        self.assertTrue(any('trái luật' in line for line in t['lines']))
        self.assertLessEqual(j.c['money'] - before, t['paid'] - TC.LEGAL_FINE + 1, 'the fine comes off the day')
        validate_state(j.state)

    def test_every_third_warning_brings_the_inspection_team(self):
        j = Journey('tuning', day=6, slot=2)
        d = data(j)
        d['legal'].update(warn=2, fined=2 * TC.LEGAL_FINE)
        validate_state(j.state)
        work(j, illegal=True)
        self.assertEqual(data(j)['legal']['warn'], 3)
        self.assertIn('warned', data(j)['desk']['marks'])
        self.assertTrue(any(x['id'] == 'inspection' and x.get('need_mark') == 'warned' for x in TC.DESK))
        validate_state(j.state)

    def test_a_legal_wrong_answer_is_not_a_warning(self):
        j = Journey('tuning', day=6, slot=2)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]   # the goal: wrong but not illegal
        j.act('dx_step', task=tid, step=st['id'], value=wrong_value(st, j.task['_key'][st['id']]))
        self.assertEqual(data(j)['legal']['warn'], 0)

    def test_steps_in_order_only_and_shapes_checked(self):
        j = Journey('tuning', day=6, slot=4)
        tid = j.task['id']
        with self.assertRaises(GameError):
            j.act('dx_step', task=tid, step='nghe.muc_tieu', value='a')   # not heard yet
        j.act('ask', task=tid)
        steps = j.task['needs']['steps']
        with self.assertRaises(GameError):
            j.act('dx_step', task=tid, step=steps[1]['id'], value=['a'])
        with self.assertRaises(GameError):
            j.act('dx_step', task=tid, step=steps[0]['id'], value='z')

    def test_a_tampered_save_is_refused(self):
        j = Journey('tuning', day=6, slot=1)
        j.act('ask', task=j.task['id'])
        for field, value in (('quality', 50), ('at', 3), ('paid', 9)):
            s = copy.deepcopy(j.state)
            s['careers']['tuning']['tasks'][0][field] = value
            with self.assertRaises(GameError, msg=field):
                validate_state(s)
        for path, value in ((('needs', 'net'), 99), (('needs', 'cost'), 1), (('needs', 'budget'), 999)):
            s = copy.deepcopy(j.state)
            s['careers']['tuning']['tasks'][0][path[0]][path[1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)
        for bad in (lambda d: d['legal'].update(fined=99), lambda d: d['legal'].update(warn=-1), lambda d: d.update(extra=1)):
            s = copy.deepcopy(j.state)
            bad(s['careers']['tuning']['ext']['data'])
            with self.assertRaises(GameError):
                validate_state(s)


@unittest.skipIf(T is None, 'tuning filtered out by MNL_CAREERS')
class Desk(unittest.TestCase):
    def test_a_surprise_blocks_work_until_decided_and_marks_come_back(self):
        j = Journey('tuning', day=8, slot=1)
        d = data(j)
        d['desk'].update(day=j.c['day'], ev=dict(id='desk-1', script='street_race', day=j.c['day'], at='between'), seq=1, fired=1)
        validate_state(j.state)
        tid = j.task['id']
        j.act('ask', task=tid)
        st = j.task['needs']['steps'][0]
        with self.assertRaises(GameError):
            j.act('dx_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        j.act('dx_desk', option='do')
        self.assertIn('street_build', data(j)['desk']['marks'])
        self.assertTrue(any(x['id'] == 'street_crash' and x.get('need_mark') == 'street_build' for x in TC.DESK))
        j.act('dx_step', task=tid, step=st['id'], value=j.task['_key'][st['id']])
        validate_state(j.state)


@unittest.skipIf(T is None, 'tuning filtered out by MNL_CAREERS')
class PlayerJobs(unittest.TestCase):
    def test_each_service_is_three_graded_steps_and_lands_in_svc_ok(self):
        for service in T.SERVICES:
            j = Journey('tuning', day=4, slot=1)
            with self.assertRaises(GameError):
                j.act('dx_svc', order='sv_nope', service=service)
            steps, key = T.svc_job(ORDER_A, service)
            self.assertEqual(len(steps), 3)
            self.assertEqual((steps, key), T.svc_job(ORDER_A, service), 'pure')
            out = svc_finish(j, 'dx_', T.svc_job, ORDER_A, service, wrong=1)
            self.assertEqual(out['svc_ready'], ORDER_A)
            d = data(j)
            self.assertEqual((d['svc'], d['svc_ok']), ([], [dict(o=ORDER_A, s=service, q=2)]))
            self.assertEqual(d['stats']['svc'], 1)
            validate_state(j.state)
            self.assertEqual(public_state(j.state)['careers']['tuning']['data']['svc_ok'], [ORDER_A])

    def test_open_jobs_are_capped_and_a_stale_one_can_be_dropped(self):
        j = Journey('tuning', day=4, slot=1)
        orders = ['sv_' + f'{i:02x}' * 12 for i in range(sk.SVC_OPEN)]
        for o in orders:
            j.act('dx_svc', order=o, service='do_dong_co')
        with self.assertRaises(GameError):
            j.act('dx_svc', order=ORDER_B, service='do_dong_co')
        j.act('dx_svc', order=orders[0], service='do_dong_co', drop=True, confirm=True)
        j.act('dx_svc', order=ORDER_B, service='do_dong_co')
        view = public_state(j.state)['careers']['tuning']['data']['svc']
        self.assertEqual(len(view), sk.SVC_OPEN)
        self.assertTrue(all(x['step'] and '_key' not in x for x in view))
        validate_state(j.state)


@unittest.skipIf(T is None, 'tuning filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def test_an_untouched_shop_is_left_out_of_the_stored_text(self):
        j = Journey('milk_tea')
        self.assertEqual(j.state['careers']['tuning'], initial_career('tuning'))
        self.assertNotIn('tuning', dormant_out(j.state)['careers'])

    def test_pay_sits_with_the_motorbike_shop(self):
        """Labour per ticket 18–32 xu before quality (moto: 14–24); the parts come back at hand-back."""
        nets = [T.ticket(day, slot)['net'] for day in range(1, 60) for slot in range(6)]
        self.assertGreaterEqual(min(nets), 18)
        self.assertLessEqual(max(nets), 32)


if __name__ == '__main__':
    unittest.main()
