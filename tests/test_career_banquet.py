"""👨‍🍳 Nhà hàng tiệc Hồng Mây (game/careers/banquet.py): a salaried shift in a banquet restaurant on one of two tracks.
Bếp: Phụ bếp (sơ chế, salad, dụng cụ) is the probation, Đầu bếp (kiểm nguyên liệu, nấu, ra món) opens after it; a kitchen
shift opens with hygiene and closes with cleaning and switching off the appliances; a food-safety inspection drops in on
some days; skipping the closing check risks a fire whose bounded compensation leaves the wallet. Sảnh sự kiện: tables,
hall size, concept, menu, drinks, decor, sound and light, electrics, an incident. Every step is graded on the server, a
wrong step stays open and lowers the quality; holiday rush days follow the real Vietnam date; strict saves and the dormant
record an untouched restaurant leaves out."""
import copy
import json
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest import mock

from tests.helpers import Journey
from game import journey as jr
from game.careers import ORDER, PLUGINS, kit
from game.engine import DORMANT, GameError, dormant_out, initial_career, new_state, public_state, validate_state, wake

B = PLUGINS.get('banquet')
if B is not None:
    from game.careers import banquet_content as BC
    from game.careers import kit

VN = timezone(timedelta(hours=7))


def vn_ts(y, m, d, hour=10):
    return datetime(y, m, d, hour, tzinfo=VN).timestamp()


def slot_of(job, day=3):
    role = BC.JOBS[job][2]
    return next(s for s in range(12) if B.job_of(day, s, role) == job)


def wrong_value(st, right):
    """A value of the right shape that is not the answer."""
    typ = st['type']
    if typ == 'choice':
        return next(o['id'] for o in st['options'] if o['id'] != right)
    if typ == 'number':
        return right + 1
    if typ == 'order':
        return list(reversed(right))
    ids = sorted(o['id'] for o in st['options'])
    return [] if right == ids else ids


def data(j):
    return j.c['ext']['data']


def promote(j):
    """The probation done: three good Phụ bếp shifts on record."""
    d = data(j)
    d['stats'].update(jobs=d['stats']['jobs'] + 3, good=d['stats']['good'] + 3, prep_days=3)
    d['stats']['roles']['prep'] += 3
    d['promoted'] = True


def job_journey(job, day=3):
    """A Journey whose active slip is `job`, out of any rush."""
    role = BC.JOBS[job][2]
    j = Journey('banquet', day=day, slot=slot_of(job, day))
    if role == 'chef':
        promote(j)
    data(j)['role'] = role
    j.task.update(role=role, rush='none')
    validate_state(j.state)
    return j


def clear_desk(j):
    ev = data(j)['desk']['ev']
    if ev:
        x = next(x for x in BC.DESK if x['id'] == ev['script'])
        j.act('bq_desk', option=next(o['id'] for o in x['options'] if o.get('good')))


def solve(j, tid=None, limit=40):
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    for _ in range(limit):
        clear_desk(j)
        t = j.get(tid)
        if t['status'] == 'completed':
            return t
        _, steps, key = B._active(t)
        st = steps[t['at']]
        j.act('bq_step', task=tid, step=st['id'], value=key[st['id']])
    raise AssertionError('banquet task did not finish')


def shift(j, part):
    for _ in range(6):
        clear_desk(j)
        steps, key = B.shift_steps(j.c['day'], part)
        at = data(j)['today'][part + '_at'] if data(j)['today']['day'] == j.c['day'] else 0
        if at >= len(steps):
            return
        st = steps[at]
        j.act('bq_shift', part=part, step=st['id'], value=key[st['id']])
    raise AssertionError('shift checklist did not finish')


def roundtrip(j):
    j.state = json.loads(json.dumps(j.state))
    validate_state(j.state)


def first_day(pred, start=2, stop=200):
    return next(d for d in range(start, stop) if pred(d))


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_last_dormant_and_salaried(self):
        from game import operations
        from game.career_voice import salaried_set
        self.assertEqual(ORDER[ORDER.index('hotel') + 1], 'banquet')   # appended after the hotel (📻 radio came next)
        self.assertIn('banquet', DORMANT)
        self.assertIn('banquet', salaried_set())
        self.assertIn('banquet', operations.SALARIED)
        posting = B.SPEC['employment']['postings'][0]
        self.assertEqual(posting['org'], 'Nhà hàng tiệc Hồng Mây')
        self.assertEqual((posting['salary'], posting['probation_days']), ((52, 66), 3))   # in line with the hotel
        self.assertEqual(B.SPEC['tip'], 0)
        self.assertNotEqual(B.ID, 'restaurant')   # Quán Mì Cay Mây keeps its own id and plugin
        self.assertIn('restaurant', ORDER)

    def test_journey_opens_the_restaurant_from_chapter_three_without_listing_it(self):
        s = new_state()
        jr.enable_story(s, 12345)
        s['journey']['chapter'] = 2
        self.assertFalse(jr.is_unlocked(s, 'banquet'))
        s['journey']['chapter'] = 3
        self.assertTrue(jr.is_unlocked(s, 'banquet'))
        self.assertNotIn('banquet', s['journey']['unlocked'])   # an older build would refuse a save that lists it
        self.assertIn('banquet', public_state(s)['journey']['unlocked'])
        self.assertEqual(jr.content()['unlock_chapter']['banquet'], 3)

    def test_an_untouched_restaurant_stays_out_of_the_stored_save(self):
        s = new_state()
        self.assertIn('banquet', s['careers'])
        out = dormant_out(s)
        self.assertNotIn('banquet', out['careers'])
        back = json.loads(json.dumps(out))
        self.assertTrue(wake(back))
        self.assertEqual(back['careers']['banquet'], initial_career('banquet'))
        j = job_journey('prep')
        solve(j)
        self.assertIn('banquet', dormant_out(j.state)['careers'])   # once worked, never left out again


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Roles(unittest.TestCase):
    def test_each_role_rotates_through_its_own_jobs(self):
        for day in range(1, 8):
            for role, jobs in BC.ROLE_JOBS.items():
                self.assertEqual({B.job_of(day, s, role) for s in range(len(jobs))}, set(jobs))
        self.assertEqual(B.make_task(5, 2, 1), B.make_task(5, 2, 1))
        self.assertEqual(B.make_task(5, 2, 1)['role'], 'prep')

    def test_chef_is_locked_until_the_probation_is_done(self):
        j = Journey('banquet')
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('bq_role', role='chef')
        self.assertEqual(j.state, before)
        with self.assertRaises(GameError):
            j.act('bq_role', role='owner')
        r = j.act('bq_role', role='hall')
        self.assertIn('sảnh', r['message'].lower())
        self.assertTrue(all(t['role'] == 'hall' for t in j.c['tasks']))   # unread slips follow the role just chosen
        validate_state(j.state)
        promote(j)
        j.act('bq_role', role='chef')
        self.assertTrue(all(t['role'] == 'chef' for t in j.c['tasks']))
        roundtrip(j)

    def test_a_slip_already_read_keeps_its_role(self):
        j = Journey('banquet')
        first = j.c['tasks'][0]['id']
        j.act('ask', task=first)
        j.act('bq_role', role='hall')
        self.assertEqual(j.get(first)['role'], 'prep')
        self.assertTrue(all(t['role'] == 'hall' for t in j.c['tasks'] if t['id'] != first))
        roundtrip(j)


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Jobs(unittest.TestCase):
    def test_a_task_slipped_before_17_10_keeps_its_quality(self):
        j = job_journey('event')
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = B._active(j.get(tid))
        j.act('bq_step', task=tid, step=steps[0]['id'], value=wrong_value(steps[0], key[steps[0]['id']]))
        t = j.get(tid)
        t['quality'] = 88                     # one slip under the old rule (12 a slip)
        validate_state(j.state)
        t['quality'] = 77
        with self.assertRaises(GameError):
            validate_state(j.state)

    def test_each_job_end_to_end_with_a_mistake_fixed_in_place(self):
        for job in BC.JOBS:
            with self.subTest(job=job):
                j = job_journey(job)
                tid = j.task['id']
                j.act('ask', task=tid)
                _, steps, key = B._active(j.get(tid))
                st = steps[0]
                r = j.act('bq_step', task=tid, step=st['id'], value=wrong_value(st, key[st['id']]))
                self.assertFalse(r['correct'])
                t = j.get(tid)
                self.assertEqual((t['at'], t['wrong'], t['errors'], t['quality']), (0, 1, [st['id']], 94))   # 17/10: 6 a slip
                self.assertNotIn(' chỉ: ', r['message'])                       # the first slip: the way to work it out
                answer = kit.answer_text(st, key[st['id']])
                r = j.act('bq_step', task=tid, step=st['id'], value=wrong_value(st, key[st['id']]))
                self.assertIn(' chỉ: ' + answer, r['message'])                  # the second: the answer itself (17/10)
                t = j.get(tid)
                self.assertEqual((t['at'], t['wrong'], t['errors'], t['quality']), (0, 2, [st['id']], 88))
                roundtrip(j)   # a half-done job with a mistake is a valid save
                money = j.c['money']
                done = solve(j, tid)
                self.assertEqual(done['status'], 'completed')
                self.assertEqual(done['quality'], 88)
                self.assertEqual(done['work'], {s['id']: key[s['id']] for s in steps})
                self.assertEqual(done['paid'], max(3, round(BC.BONUS[job] * 88 / 100)))
                self.assertEqual(j.c['money'], money + done['paid'])
                d = data(j)
                self.assertEqual(d['today']['jobs'], 1)
                self.assertEqual(d['today']['good'], 0)
                roundtrip(j)

    def test_a_clean_job_counts_for_the_journey(self):
        j = job_journey('event')
        done = solve(j)
        self.assertEqual((done['quality'], done['paid']), (100, BC.BONUS['event']))
        d = data(j)
        self.assertEqual((d['stats']['good'], d['stats']['roles']['hall'], d['today']['good']), (1, 1, 1))
        self.assertEqual(d['today']['kitchen'], 0)   # the hall never touches the kitchen checklist
        B.on_close(j.state, j.c)
        B.on_close(j.state, j.c)
        self.assertEqual(d['stats']['active_days'], 1)
        roundtrip(j)

    def test_wrong_shapes_and_out_of_order_steps_change_nothing(self):
        j = job_journey('salad')
        tid = j.task['id']
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):   # the job slip is read first
            j.act('bq_step', task=tid, step='salad.wash', value=[])
        self.assertEqual(j.state, before)
        j.act('ask', task=tid)
        _, steps, key = B._active(j.get(tid))
        first = steps[0]['id']
        for p in (dict(step='salad.sauce', value='mayo'), dict(step=first, value=['pick']), dict(step=first, value='pick'),
                  dict(step=first, value=key[first] + ['pick']), dict(step={}, value=1), dict(step=first, value=None)):
            before = copy.deepcopy(j.state)
            with self.assertRaises(GameError):
                j.act('bq_step', task=tid, **p)
            self.assertEqual(j.state, before)
        with self.assertRaises(GameError):
            j.act('bq_forge', task=tid)

    def test_numbers_are_bounded(self):
        j = job_journey('prep')
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = B._active(j.get(tid))
        for st in steps[:2]:
            j.act('bq_step', task=tid, step=st['id'], value=key[st['id']])
        st = B._active(j.get(tid))[1][2]
        self.assertEqual(st['type'], 'number')
        for value in (-1, 100001, 'x', [1], 1.5):
            before = copy.deepcopy(j.state)
            with self.assertRaises(GameError):
                j.act('bq_step', task=tid, step=st['id'], value=value)
            self.assertEqual(j.state, before)

    def test_the_answer_key_never_reaches_the_client(self):
        t = B.make_task(3, 0, 1)
        self.assertIsNone(B.public_task(t)['needs'])
        t['known'] = True
        for role in B.ROLES:
            v = B.public_task(dict(t, role=role))
            self.assertNotIn('_key', v)
            self.assertNotIn('key', json.dumps(v['needs']))
            self.assertEqual(v['role_info']['id'], role)
            self.assertEqual(v['job']['id'], B.job_of(3, 0, role))

    def test_the_event_hall_and_menu_rules_hold(self):
        for day in range(1, 40):
            for slot in range(12):
                b, steps, key, *_ = B.brief(day, slot, 'hall')
                tables = key['event.tables']
                halls = {h[0]: h for h in BC.HALLS}
                self.assertGreaterEqual(halls[key['event.hall']][2], tables)
                smaller = [h for h in BC.HALLS if h[2] < halls[key['event.hall']][2]]
                self.assertTrue(all(h[2] < tables for h in smaller))   # the smallest hall that seats everyone
                menu = next(m for m in BC.MENUS if m[0] == key['event.menu'])
                self.assertLessEqual(menu[2], b['budget'])
                self.assertTrue(key['event.decor'])
                self.assertTrue(key['event.power'])
                self.assertNotIn('fire', key['event.decor'])   # a closed hall never takes real candles

    def test_a_full_day_closes_with_the_contract_salary_once(self):
        with mock.patch.object(B, 'rush_now', return_value='none'):
            j = Journey('banquet')
            shift(j, 'open')
            for t in list(j.c['tasks']):
                solve(j, t['id'])
            shift(j, 'close')
        self.assertFalse(any(r.get('category') == 'salary' for r in j.c['ops']['finance']['ledger']))
        j.act('end_day', carry_event=True)
        rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('category') == 'salary']
        self.assertEqual(len(rows), 1)
        self.assertGreater(rows[0]['amount'], 0)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('end_day', carry_event=True)
        self.assertEqual(j.state, before)
        roundtrip(j)


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Shift(unittest.TestCase):
    def test_the_opening_hygiene_is_graded_and_repeated_until_right(self):
        j = Journey('banquet')
        steps, key = B.shift_steps(j.c['day'], 'open')
        st = steps[0]
        r = j.act('bq_shift', part='open', step=st['id'], value=list(reversed(key[st['id']])))
        self.assertFalse(r['correct'])
        self.assertEqual((data(j)['today']['open_at'], data(j)['today']['slips']), (0, 1))
        r = j.act('bq_shift', part='open', step=st['id'], value=key[st['id']])
        self.assertTrue(r['correct'])
        self.assertTrue(B.public_data(j.c)['shift']['open']['done'])
        with self.assertRaises(GameError):
            j.act('bq_shift', part='open', step=st['id'], value=key[st['id']])
        self.assertEqual(key[st['id']], ['wash', 'sanitize', 'cap', 'gloves', 'stove'])   # tay sạch rồi mới đeo bao tay
        roundtrip(j)

    def test_closing_waits_for_the_dish_in_hand_and_ends_the_kitchen_work(self):
        j = job_journey('cook')
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = B._active(j.get(tid))
        j.act('bq_step', task=tid, step=steps[0]['id'], value=key[steps[0]['id']])
        csteps, ckey = B.shift_steps(j.c['day'], 'close')
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):   # a dish half cooked: finish it first
            j.act('bq_shift', part='close', step=csteps[0]['id'], value=ckey[csteps[0]['id']])
        self.assertEqual(j.state, before)
        solve(j, tid)
        shift(j, 'close')
        self.assertTrue(B.public_data(j.c)['shift']['close']['done'])
        self.assertEqual(ckey['close.clean'], ['trash', 'dishes', 'wipe', 'floor'])
        self.assertTrue(set(ckey['close.power']) <= {'gas', 'hood', 'rice', 'oven', 'kettle', 'fryer'})   # fridges keep running
        roundtrip(j)

    def test_after_closing_the_kitchen_takes_no_more_steps_but_the_hall_does(self):
        j = job_journey('prep')
        shift(j, 'close')
        tid = j.task['id']
        j.act('ask', task=tid)
        st = B._active(j.get(tid))[1][0]
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('bq_step', task=tid, step=st['id'], value=B._active(j.get(tid))[2][st['id']])
        self.assertEqual(j.state, before)
        j2 = job_journey('event')
        shift(j2, 'close')
        self.assertEqual(solve(j2)['status'], 'completed')

    def test_the_closing_power_check_always_has_something_to_switch_off(self):
        for day in range(1, 120):
            steps, key = B.shift_steps(day, 'close')
            self.assertTrue(key['close.power'])
            self.assertEqual(len(steps[1]['options']), len(BC.APPLIANCES))
            self.assertEqual(B.shift_steps(day, 'close'), (steps, key))


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Inspection(unittest.TestCase):
    def test_a_clean_kitchen_passes_the_inspection(self):
        day = first_day(B.inspection_day)
        j = job_journey('prep', day=day)
        shift(j, 'open')
        xp = j.c['xp']
        solve(j)
        d = data(j)
        self.assertEqual((d['today']['insp'], d['stats']['insp_pass'], d['stats']['insp_fail']), (1, 1, 0))
        self.assertGreaterEqual(j.c['xp'], xp + 6)
        roundtrip(j)

    def test_skipping_the_hygiene_is_written_up_and_the_shift_does_not_count(self):
        day = first_day(B.inspection_day)
        j = job_journey('prep', day=day)
        solve(j)
        d = data(j)
        self.assertEqual((d['today']['insp'], d['stats']['insp_fail']), (2, 1))
        npc = kit.npc_id('banquet', BC.INSPECTOR)
        self.assertTrue(any(p['npc'] == npc and p['stars'] == 2 and p['kind'] == 'review' for p in j.c['feed']))
        shift(j, 'open')   # a late wash does not undo the warning
        shift(j, 'close')
        B.on_close(j.state, j.c)
        self.assertEqual(d['stats']['prep_days'], 0)
        roundtrip(j)

    def test_no_inspection_on_a_quiet_day(self):
        day = first_day(lambda x: not B.inspection_day(x))
        j = job_journey('prep', day=day)
        solve(j)
        self.assertEqual(data(j)['today']['insp'], 0)


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Fire(unittest.TestCase):
    def fire_day(self, j, hit=True):
        seed = int(j.state['journey'].get('seed') or 0)
        return first_day(lambda d: (kit.rng('banquet', 'fire', seed, d).random() < BC.FIRE_CHANCE) == hit, start=3)

    def test_the_fine_is_a_few_percent_of_the_salary_with_a_small_cap(self):
        self.assertEqual(B.fire_fine({'job': {'salary': 52}}), 4)
        self.assertEqual(B.fire_fine({'job': {'salary': 66}}), 5)
        self.assertEqual(B.fire_fine({'job': {'salary': 500}}), BC.FIRE_CAP)
        self.assertEqual(B.fire_fine({'job': {'salary': 5}}), BC.FIRE_MIN)
        self.assertEqual(B.fire_fine({}), 4)
        self.assertLessEqual(BC.FIRE_CAP, 66 * 10 // 100)   # never more than a tenth of a day's pay

    def test_a_kitchen_left_on_burns_and_the_workplace_pays_within_what_it_holds(self):
        probe = Journey('banquet')
        day = self.fire_day(probe)
        j = job_journey('prep', day=day)
        solve(j)
        money = j.c['money']
        out = B.on_close(j.state, j.c)
        fine = min(B.fire_fine(j.c), money)
        self.assertEqual(j.c['money'], money - fine)
        d = data(j)
        self.assertEqual((d['stats']['fires'], d['stats']['fined']), (1, fine))
        self.assertTrue(any('🔥' in line for line in out['lines']))
        B.on_close(j.state, j.c)   # once a night
        self.assertEqual(d['stats']['fires'], 1)
        roundtrip(j)

    def test_story_wallet_pays_the_fine_and_never_goes_negative(self):
        probe = Journey('banquet')
        day = self.fire_day(probe)
        for wallet, want in ((60, None), (2, 2), (0, 0)):
            with self.subTest(wallet=wallet):
                j = job_journey('prep', day=day)
                solve(j)
                jj = j.state['journey']
                jj.update(story=True, wallet=wallet)
                fine = B.fire_fine(j.c)
                want = fine if want is None else want
                money = j.c['money']
                B.on_close(j.state, j.c)
                self.assertEqual(jj['wallet'], wallet - want)
                self.assertGreaterEqual(jj['wallet'], 0)
                self.assertEqual(j.c['money'], money)   # the workplace fund is not touched in a story
                self.assertEqual(data(j)['stats']['fined'], want)

    def test_no_fire_after_the_closing_check_or_on_a_lucky_night_or_in_the_hall(self):
        probe = Journey('banquet')
        day = self.fire_day(probe)
        j = job_journey('prep', day=day)
        solve(j)
        shift(j, 'close')
        money = j.c['money']
        B.on_close(j.state, j.c)
        self.assertEqual((data(j)['stats']['fires'], j.c['money']), (0, money))
        lucky = self.fire_day(probe, hit=False)
        j = job_journey('prep', day=lucky)
        solve(j)
        out = B.on_close(j.state, j.c)
        self.assertEqual(data(j)['stats']['fires'], 0)
        self.assertTrue(any('⚠️' in line for line in out['lines']))
        j = job_journey('event', day=day)
        solve(j)
        B.on_close(j.state, j.c)
        self.assertEqual(data(j)['stats']['fires'], 0)

    def test_the_risk_is_explained_before_it_happens(self):
        text = ' '.join(BC.NOTEBOOK)
        self.assertIn(f'{BC.FIRE_PCT}% lương ca', text)
        self.assertIn(f'nhiều nhất {BC.FIRE_CAP} xu', text)
        intro = json.dumps(B.content(), ensure_ascii=False)
        self.assertIn('tối đa', intro)
        j = Journey('banquet')
        self.assertEqual(B.public_data(j.c)['fire_fine'], B.fire_fine(j.c))


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Probation(unittest.TestCase):
    def good_prep_day(self, j, day):
        j.c['day'] = day
        t = B.make_task(day, slot_of('prep', day), j.c['turn'])
        j.c['tasks'] = [t]
        j.c['active_task'] = t['id']
        B.on_task(j.state, j.c, t)
        t['rush'] = 'none'
        shift(j, 'open')
        solve(j, t['id'])
        shift(j, 'close')
        return B.on_close(j.state, j.c)

    def test_three_good_prep_shifts_make_a_chef(self):
        quiet = [d for d in range(2, 80) if not B.inspection_day(d)][:4]
        j = job_journey('prep', day=quiet[0])
        j.c['tasks'] = []
        out = self.good_prep_day(j, quiet[0])
        self.assertEqual(data(j)['stats']['prep_days'], 1)
        self.assertTrue(any('Còn 2 ca' in line for line in out['lines']))
        B.on_close(j.state, j.c)   # counted once a day
        self.assertEqual(data(j)['stats']['prep_days'], 1)
        self.good_prep_day(j, quiet[1])
        self.assertFalse(data(j)['promoted'])
        xp = j.c['xp']
        out = self.good_prep_day(j, quiet[2])
        self.assertTrue(data(j)['promoted'])
        self.assertGreaterEqual(j.c['xp'], xp + 10)
        self.assertTrue(any('Đầu bếp' in line for line in out['lines']))
        validate_state(j.state)
        j.act('bq_role', role='chef')
        self.assertEqual(data(j)['role'], 'chef')

    def test_a_prep_shift_without_the_closing_check_does_not_count(self):
        day = first_day(lambda x: not B.inspection_day(x))
        j = job_journey('prep', day=day)
        shift(j, 'open')
        solve(j)
        B.on_close(j.state, j.c)
        self.assertEqual(data(j)['stats']['prep_days'], 0)


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Rush(unittest.TestCase):
    def test_rush_days_follow_the_vietnam_calendar(self):
        cases = {
            date(2026, 10, 16): None, date(2026, 10, 20): 'vnwomen', date(2026, 9, 2): 'national', date(2026, 11, 20): 'teachers',
            date(2026, 2, 14): 'valentine', date(2026, 2, 15): 'tet', date(2026, 2, 17): 'tet', date(2026, 2, 20): 'tet',
            date(2026, 2, 21): None, date(2027, 2, 4): 'tet', date(2027, 2, 3): None, date(2026, 12, 25): 'noel',
            date(2026, 12, 31): 'newyear', date(2027, 1, 1): 'newyear', date(2026, 4, 30): 'reunify', date(2026, 5, 1): 'reunify',
            date(2026, 6, 1): 'children', date(2026, 3, 8): 'women',
        }
        for d, want in cases.items():
            with self.subTest(day=d.isoformat()):
                self.assertEqual(B.rush_of(d), want)

    def test_the_real_date_is_read_in_vietnam_time(self):
        with mock.patch('game.careers.kit.now', return_value=vn_ts(2026, 10, 19, 23)):
            self.assertEqual(B.rush_now(), 'none')
        with mock.patch('game.careers.kit.now', return_value=datetime(2026, 10, 20, 0, 30, tzinfo=VN).timestamp()):
            self.assertEqual(B.rush_now(), 'vnwomen')
            self.assertEqual(B.rush_view()['bonus'], 1.5)

    def test_a_rush_day_adds_a_job_pays_more_and_costs_more_per_slip(self):
        with mock.patch('game.careers.kit.now', return_value=vn_ts(2026, 10, 16)):
            calm = Journey('banquet')
        with mock.patch('game.careers.kit.now', return_value=vn_ts(2026, 10, 20)):
            busy = Journey('banquet')
        self.assertEqual(len(busy.c['tasks']), len(calm.c['tasks']) + 1)
        self.assertTrue(all(t['rush'] == 'vnwomen' for t in busy.c['tasks']))
        validate_state(busy.state)
        tid = busy.c['tasks'][0]['id']
        busy.act('ask', task=tid)
        _, steps, key = B._active(busy.get(tid))
        busy.act('bq_step', task=tid, step=steps[0]['id'], value=wrong_value(steps[0], key[steps[0]['id']]))
        self.assertEqual(busy.get(tid)['quality'], 100 - BC.RUSH_WRONG_COST)
        done = solve(busy, tid)
        job = B._job(done)
        self.assertEqual(done['paid'], round(max(3, round(BC.BONUS[job] * 91 / 100)) * 1.5))
        self.assertEqual(data(busy)['stats']['rush'], 1)
        roundtrip(busy)   # validates on another (calm) date too: the slip keeps its rush


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def halfway(self):
        j = job_journey('tools')
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = B._active(j.get(tid))
        st = steps[0]
        j.act('bq_step', task=tid, step=st['id'], value=wrong_value(st, key[st['id']]))
        for st in steps[:2]:
            j.act('bq_step', task=tid, step=st['id'], value=key[st['id']])
        roundtrip(j)
        return j

    def test_forged_task_fields_are_refused(self):
        j = self.halfway()
        forge = {
            'needs': lambda t: t.update(needs={'x': 1}),
            '_key': lambda t: t.update(_key={'tools.wash': 'proper'}),
            'kind': lambda t: t.update(kind='event'),
            'work': lambda t: t['work'].pop('tools.tools'),
            'work value': lambda t: t['work'].update({'tools.vessels': t['work']['tools.vessels'] + 1}),
            'at': lambda t: t.update(at=t['at'] + 1),
            'quality': lambda t: t.update(quality=100),
            'wrong': lambda t: t.update(wrong=0),
            'errors': lambda t: t.update(errors=[]),
            'errors ahead': lambda t: t['errors'].append('tools.wash'),
            'paid': lambda t: t.update(paid=50),
            'stage': lambda t: t.update(stage='done'),
            'rush': lambda t: t.update(rush='halloween'),
            'role': lambda t: t.update(role='owner'),
            'chef before probation': lambda t: t.update(role='chef'),
        }
        for name, fn in forge.items():
            with self.subTest(field=name):
                bad = copy.deepcopy(j.state)
                fn(bad['careers']['banquet']['tasks'][0])
                with self.assertRaises(GameError):
                    validate_state(bad)

    def test_forged_records_are_refused(self):
        j = job_journey('event')
        solve(j)
        roundtrip(j)
        forge = {
            'good above jobs': lambda d: d['stats'].update(good=5),
            'role without a good job': lambda d: d['stats']['roles'].update(chef=1),
            'unknown role': lambda d: d['stats']['roles'].update(owner=0),
            'intro type': lambda d: d.update(intro=1),
            'extra key': lambda d: d.update(vip=True),
            'active days': lambda d: d['stats'].update(active_days=9),
            'promoted without probation': lambda d: d.update(promoted=True),
            'chef role without probation': lambda d: d.update(role='chef'),
            'probation days without prep jobs': lambda d: d['stats'].update(prep_days=1),
            'fine without a fire': lambda d: d['stats'].update(fined=3),
            'fire above the cap': lambda d: d['today'].update(fire=BC.FIRE_CAP + 1),
            'inspection state': lambda d: d['today'].update(insp=3),
            'checklist ahead': lambda d: d['today'].update(open_at=9),
            'desk script': lambda d: d['desk'].update(ev=dict(id='desk-9', script='free_cake', day=3, at='between')),
        }
        for name, fn in forge.items():
            with self.subTest(record=name):
                bad = copy.deepcopy(j.state)
                fn(bad['careers']['banquet']['ext']['data'])
                with self.assertRaises(GameError):
                    validate_state(bad)


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Desk(unittest.TestCase):
    def test_ten_well_formed_surprises(self):
        self.assertEqual(len(BC.DESK), 10)
        self.assertEqual(len({x['id'] for x in BC.DESK}), 10)
        banned = ('NPC', 'người chơi', 'trong game', 'mô phỏng', 'anh ấy', 'cô ấy')
        for x in BC.DESK:
            with self.subTest(script=x['id']):
                self.assertTrue(x['title'] and x['text'] and x['emoji'])
                self.assertGreaterEqual(len(x['options']), 3)
                self.assertEqual(len({o['id'] for o in x['options']}), len(x['options']))
                self.assertEqual(sum(1 for o in x['options'] if o.get('good') is True), 1)
                for o in x['options']:
                    ends = [o['luck']['win'], o['luck']['lose']] if o.get('luck') else [o]
                    self.assertTrue(o['label'] and all(e['outcome'] for e in ends))
                    self.assertGreaterEqual(o.get('effects', {}).get('money', 0), 0)   # a surprise never charges the player
                text = json.dumps(x, ensure_ascii=False)
                for b in banned:
                    self.assertNotIn(b, text)

    def test_each_surprise_blocks_the_work_and_every_choice_saves(self):
        for x in BC.DESK:
            for o in x['options']:
                with self.subTest(script=x['id'], option=o['id']):
                    j = job_journey('prep', day=4)
                    data(j)['desk']['ev'] = dict(id='desk-1', script=x['id'], day=4, at='between')
                    data(j)['desk'].update(seq=1, fired=1)
                    validate_state(j.state)
                    tid = j.task['id']
                    j.act('ask', task=tid)
                    _, steps, key = B._active(j.get(tid))
                    before = copy.deepcopy(j.state)
                    with self.assertRaises(GameError):
                        j.act('bq_step', task=tid, step=steps[0]['id'], value=key[steps[0]['id']])
                    self.assertEqual(j.state, before)
                    r = j.act('bq_desk', option=o['id'])
                    self.assertTrue(r['message'])
                    self.assertIsNone(data(j)['desk']['ev'])
                    roundtrip(j)

    def test_surprises_arrive_during_a_long_shift(self):
        seen = set()
        with mock.patch.object(B, 'rush_now', return_value='none'):
            for day in range(2, 14):
                j = Journey('banquet')
                j.c['day'] = day
                data(j)['desk'] = kit.desk_initial()
                B.on_start(j.state, j.c)
                for t in list(j.c['tasks']):
                    solve(j, t['id'])
                seen.update(h['script'] for h in data(j)['desk']['log'])
                validate_state(j.state)
        self.assertGreater(len(seen), 1)


@unittest.skipUnless(B, 'banquet filtered out by MNL_CAREERS')
class Content(unittest.TestCase):
    def test_every_task_is_consistent_and_solvable_for_every_role(self):
        for day in range(1, 31):
            for slot in range(12):
                t = B.make_task(day, slot, 1)
                B.validate_task(copy.deepcopy(t), t)
                for role in B.ROLES:
                    for rush in ('none', 'tet'):
                        _, steps, key = B._active(dict(t, role=role, rush=rush))
                        self.assertEqual(set(key), {s['id'] for s in steps})
                        for st in steps:
                            self.assertIn(st['type'], B.TYPES)
                            ids = [o['id'] for o in st.get('options', [])]
                            self.assertEqual(len(ids), len(set(ids)))
                            if st['type'] == 'choice':
                                self.assertIn(key[st['id']], ids)
                            elif st['type'] == 'order':
                                self.assertEqual(sorted(key[st['id']]), sorted(ids))
                            elif st['type'] == 'multi':
                                self.assertLessEqual(set(key[st['id']]), set(ids))
                            else:
                                self.assertIsInstance(key[st['id']], int)

    def test_the_copy_addresses_the_player_neutrally(self):
        text = json.dumps([B.content(), B.SPEC, BC.NOTEBOOK, BC.DESK, BC.PEOPLE], ensure_ascii=False)
        for word in ('anh ấy', 'cô ấy', 'người chơi', 'NPC'):
            self.assertNotIn(word, text)
        for day in range(1, 13):
            for slot in range(6):
                for role in B.ROLES:
                    blob = json.dumps(B.brief(day, slot, role)[0], ensure_ascii=False)
                    self.assertNotIn('người chơi', blob)

    def test_milestones_need_good_jobs_days_and_roles(self):
        j = job_journey('prep')
        st = data(j)['stats']
        st.update(jobs=20, good=20, active_days=6, prep_days=3, roles=dict(prep=20, chef=0, hall=0))
        data(j)['promoted'] = True
        self.assertEqual(B.public_data(j.c)['progress']['earned'], ['helper'])
        st['roles'].update(prep=10, chef=5, hall=5)
        st.update(jobs=60, good=60, active_days=20)
        st['roles'].update(prep=20, chef=20, hall=20)
        self.assertEqual(B.public_data(j.c)['progress']['earned'], ['helper', 'both'])
        validate_state(j.state)


if __name__ == '__main__':
    unittest.main()
