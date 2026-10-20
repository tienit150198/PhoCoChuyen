"""📻 Đài phát thanh Sóng Mây (game/careers/radio.py): a salaried shift at the ward radio station. Phát thanh viên (bulletin,
sponsor's spot, listeners' wishes) is the probation, DJ (song requests, callers on air, the show's running order) opens after
it; every shift opens with the studio check (required before the first step on air); on some days the power goes out after the
first finished job and the outage drill blocks the work until it is done. Every step is graded on the server, a wrong step stays
open and lowers the quality; option ids never say which one is right; strict saves and the dormant record an untouched station
leaves out."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game.careers import ORDER, PLUGINS, kit
from game.engine import DORMANT, GameError, dormant_out, initial_career, new_state, public_state, validate_state, wake

R = PLUGINS.get('radio')
if R is not None:
    from game.careers import radio_content as RC


def slot_of(job, day=3):
    role = RC.JOBS[job][2]
    return next(s for s in range(12) if R.job_of(day, s, role) == job)


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


def data(j):
    return j.c['ext']['data']


def promote(j):
    d = data(j)
    d['stats'].update(jobs=d['stats']['jobs'] + 3, good=d['stats']['good'] + 3, news_days=3)
    d['stats']['roles']['news'] += 3
    d['promoted'] = True


def quiet(day):
    """`day` or the next day without a power cut (the tests that are not about the outage)."""
    while R.outage_day(day):
        day += 1
    return day


def job_journey(job, day=3, studio=True):
    role = RC.JOBS[job][2]
    j = Journey('radio', day=day, slot=slot_of(job, day))
    if role == 'dj':
        promote(j)
    data(j)['role'] = role
    j.task.update(role=role)
    validate_state(j.state)
    if studio:
        shift(j, 'open')
    return j


def clear_desk(j):
    ev = data(j)['desk']['ev']
    if ev:
        x = next(x for x in RC.DESK if x['id'] == ev['script'])
        j.act('rd_desk', option=next(o['id'] for o in x['options'] if o.get('good')))


def shift(j, part):
    for _ in range(4):
        clear_desk(j)
        steps, key = R.shift_steps(j.c['day'], part)
        today = data(j)['today']
        at = (today['open_at'] if part == 'open' else today['out_at']) if today['day'] == j.c['day'] else 0
        if at >= len(steps):
            return
        st = steps[at]
        j.act('rd_shift', part=part, step=st['id'], value=key[st['id']])
    raise AssertionError('shift checklist did not finish')


def solve(j, tid=None, limit=40):
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    for _ in range(limit):
        clear_desk(j)
        if data(j)['today']['out'] == 1:
            shift(j, 'outage')
        t = j.get(tid)
        if t['status'] == 'completed':
            return t
        _, steps, key = R._active(t)
        st = steps[t['at']]
        j.act('rd_step', task=tid, step=st['id'], value=key[st['id']])
    raise AssertionError('radio task did not finish')


def roundtrip(j):
    j.state = json.loads(json.dumps(j.state))
    validate_state(j.state)


@unittest.skipUnless(R, 'radio filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_dormant_and_salaried(self):
        from game import operations
        from game.career_voice import salaried_set
        self.assertIn('radio', ORDER)
        self.assertEqual(ORDER[-1], 'radio')   # appended last (reception, teller, restore, research, radio)
        self.assertIn('radio', DORMANT)
        self.assertIn('radio', salaried_set())
        self.assertIn('radio', operations.SALARIED)
        posting = R.SPEC['employment']['postings'][0]
        self.assertEqual(posting['org'], 'Đài phát thanh Sóng Mây')
        self.assertEqual((posting['salary'], posting['probation_days']), ((50, 64), 3))
        self.assertEqual(R.SPEC['tip'], 0)

    def test_journey_opens_the_station_from_chapter_three_without_listing_it(self):
        s = new_state()
        jr.enable_story(s, 12345)
        s['journey']['chapter'] = 2
        self.assertFalse(jr.is_unlocked(s, 'radio'))
        s['journey']['chapter'] = 3
        self.assertTrue(jr.is_unlocked(s, 'radio'))
        self.assertNotIn('radio', s['journey']['unlocked'])   # an older build would refuse a save that lists it
        self.assertIn('radio', public_state(s)['journey']['unlocked'])
        self.assertEqual(jr.content()['unlock_chapter']['radio'], 3)

    def test_an_untouched_station_stays_out_of_the_stored_save(self):
        s = new_state()
        self.assertIn('radio', s['careers'])
        out = dormant_out(s)
        self.assertNotIn('radio', out['careers'])
        back = json.loads(json.dumps(out))
        self.assertTrue(wake(back))
        self.assertEqual(back['careers']['radio'], initial_career('radio'))
        j = job_journey('bulletin', day=quiet(3))
        solve(j)
        self.assertIn('radio', dormant_out(j.state)['careers'])   # once worked, never left out again


@unittest.skipUnless(R, 'radio filtered out by MNL_CAREERS')
class Roles(unittest.TestCase):
    def test_each_role_rotates_through_its_own_jobs(self):
        for day in range(1, 8):
            for role, jobs in RC.ROLE_JOBS.items():
                self.assertEqual({R.job_of(day, s, role) for s in range(len(jobs))}, set(jobs))
        self.assertEqual(R.make_task(5, 2, 1), R.make_task(5, 2, 1))
        self.assertEqual(R.make_task(5, 2, 1)['role'], 'news')

    def test_dj_is_locked_until_the_probation_is_done(self):
        j = Journey('radio')
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('rd_role', role='dj')
        self.assertEqual(j.state, before)
        with self.assertRaises(GameError):
            j.act('rd_role', role='owner')
        promote(j)
        r = j.act('rd_role', role='dj')
        self.assertIn('dj', r['message'].lower())
        self.assertTrue(all(t['role'] == 'dj' for t in j.c['tasks']))   # unread slips follow the role just chosen
        roundtrip(j)


@unittest.skipUnless(R, 'radio filtered out by MNL_CAREERS')
class Jobs(unittest.TestCase):
    def test_each_job_end_to_end_with_a_mistake_fixed_in_place(self):
        for job in RC.JOBS:
            with self.subTest(job=job):
                j = job_journey(job, day=quiet(3))
                tid = j.task['id']
                j.act('ask', task=tid)
                _, steps, key = R._active(j.get(tid))
                st = steps[0]
                r = j.act('rd_step', task=tid, step=st['id'], value=wrong_value(st, key[st['id']]))
                self.assertFalse(r['correct'])
                t = j.get(tid)
                self.assertEqual((t['at'], t['wrong'], t['errors'], t['quality']), (0, 1, [st['id']], 94))
                r = j.act('rd_step', task=tid, step=st['id'], value=wrong_value(st, key[st['id']]))
                self.assertIn(' chỉ: ' + kit.answer_text(st, key[st['id']]), r['message'])   # the second slip shows the answer
                roundtrip(j)
                money = j.c['money']
                done = solve(j, tid)
                self.assertEqual((done['status'], done['quality']), ('completed', 88))
                self.assertEqual(done['work'], {s['id']: key[s['id']] for s in steps})
                self.assertEqual(done['paid'], max(3, round(RC.BONUS[job] * 88 / 100)))
                self.assertEqual(j.c['money'], money + done['paid'])
                roundtrip(j)

    def test_no_step_on_air_before_the_studio_check(self):
        j = job_journey('spot', day=quiet(3), studio=False)
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = R._active(j.get(tid))
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('rd_step', task=tid, step=steps[0]['id'], value=key[steps[0]['id']])
        self.assertEqual(j.state, before)
        osteps, okey = R.shift_steps(j.c['day'], 'open')
        r = j.act('rd_shift', part='open', step=osteps[0]['id'], value=list(reversed(okey['open.studio'])))
        self.assertFalse(r['correct'])
        self.assertEqual((data(j)['today']['open_at'], data(j)['today']['slips']), (0, 1))
        shift(j, 'open')
        self.assertEqual(solve(j, tid)['status'], 'completed')
        labels = {o['id']: o['label'] for o in osteps[0]['options']}
        self.assertTrue(labels[okey['open.studio'][-1]].startswith('Bật đèn ĐANG PHÁT SÓNG'))   # the lamp comes last
        roundtrip(j)

    def test_option_ids_never_say_which_is_right(self):
        for day in range(1, 25):
            for slot in range(6):
                for role in R.ROLES:
                    _, steps, key, *_ = R.brief(day, slot, role)
                    for st in steps:
                        for o in st.get('options', []):
                            self.assertRegex(o['id'], r'^[a-h]$')
        rights = {R.brief(d, s, 'news')[2]['bulletin.fix'] for d in range(1, 30) for s in range(12) if R.job_of(d, s, 'news') == 'bulletin'}
        self.assertGreater(len(rights), 1, 'the right answer moves around')

    def test_the_rules_of_the_station_hold_in_every_slip(self):
        for day in range(1, 40):
            for slot in range(12):
                b, steps, key, *_ = R.brief(day, slot, 'news')
                job = R.job_of(day, slot, 'news')
                labels = {s['id']: {o['id']: o['label'] for o in s.get('options', [])} for s in steps}
                if job == 'bulletin':
                    read = [labels['bulletin.order'][k] for k in key['bulletin.order']]
                    kinds = [next(kind for kind, rows in RC.NEWS.items() if any(r[1] == text for r in rows)) for text in read]
                    self.assertEqual(kinds, list(RC.READ_ORDER))   # urgent, then public service, then an event
                    picked = {labels['bulletin.pick'][k] for k in key['bulletin.pick']}
                    self.assertFalse(picked & {r[1] for k in ('rumor', 'ad') for r in RC.NEWS[k]})
                if job == 'spot':
                    chosen = labels['spot.version'][key['spot.version']]
                    self.assertIn('đã ký duyệt', chosen)
                    later = [lab for lab in labels['spot.version'].values() if lab.startswith('Bản ') and lab > chosen and 'đã ký' in lab]
                    self.assertEqual(later, [], 'the newest signed script')
                    cut = {labels['spot.cut'][k] for k in key['spot.cut']}
                    self.assertTrue(cut and cut <= set(RC.SPOT_BAD))
                if job == 'wishes':
                    skipped = {labels['wishes.skip'][k].split(' · ', 1)[1] for k in key['wishes.skip']}
                    self.assertEqual(skipped, {w[1] for w in RC.WISH_BAD} & skipped)
                    times = [labels['wishes.order'][k].split(' · ')[0] for k in key['wishes.order']]
                    self.assertEqual(times, sorted(times))

    def test_wrong_shapes_and_forged_names_change_nothing(self):
        j = job_journey('wishes', day=quiet(3))
        tid = j.task['id']
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):   # the slip is read first
            j.act('rd_step', task=tid, step='wishes.skip', value=[])
        self.assertEqual(j.state, before)
        j.act('ask', task=tid)
        _, steps, key = R._active(j.get(tid))
        first = steps[0]['id']
        for p in (dict(step='wishes.name', value='a'), dict(step=first, value=['z']), dict(step=first, value='a'),
                  dict(step={}, value=1), dict(step=first, value=None)):
            before = copy.deepcopy(j.state)
            with self.assertRaises(GameError):
                j.act('rd_step', task=tid, **p)
            self.assertEqual(j.state, before)
        with self.assertRaises(GameError):
            j.act('rd_forge', task=tid)

    def test_the_answer_key_never_reaches_the_client(self):
        t = R.make_task(3, 0, 1)
        self.assertIsNone(R.public_task(t)['needs'])
        t['known'] = True
        for role in R.ROLES:
            v = R.public_task(dict(t, role=role))
            self.assertNotIn('_key', v)
            self.assertNotIn('key', json.dumps(v['needs']))
            self.assertEqual(v['role_info']['id'], role)

    def test_a_full_day_closes_with_the_contract_salary_once(self):
        j = Journey('radio')
        shift(j, 'open')
        for t in list(j.c['tasks']):
            solve(j, t['id'])
        j.act('end_day', carry_event=True)
        rows = [r for r in j.c['ops']['finance']['ledger'] if r.get('category') == 'salary']
        self.assertEqual(len(rows), 1)
        self.assertGreater(rows[0]['amount'], 0)
        roundtrip(j)


@unittest.skipUnless(R, 'radio filtered out by MNL_CAREERS')
class Outage(unittest.TestCase):
    def day(self):
        return next(d for d in range(2, 200) if R.outage_day(d))

    def test_the_power_goes_out_after_the_first_job_and_blocks_the_air(self):
        day = self.day()
        j = job_journey('bulletin', day=day)
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = R._active(j.get(tid))
        r = None
        for st in steps:
            clear_desk(j)
            r = j.act('rd_step', task=tid, step=st['id'], value=key[st['id']])
        self.assertTrue(r.get('outage'))
        self.assertEqual(data(j)['today']['out'], 1)
        self.assertEqual(R.public_data(j.c)['shift']['outage']['state'], 'cut')
        other = R.make_task(day, (slot_of('bulletin', day) + 1) % 12, 2)
        j.c['tasks'].append(other)
        R.on_task(j.state, j.c, other)
        j.act('ask', task=other['id'])
        st = R._active(j.get(other['id']))[1][0]
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('rd_step', task=other['id'], step=st['id'], value=R._active(j.get(other['id']))[2][st['id']])
        self.assertEqual(j.state, before)
        xp = j.c['xp']
        shift(j, 'outage')
        self.assertEqual((data(j)['today']['out'], data(j)['stats']['restored']), (2, 1))
        self.assertGreaterEqual(j.c['xp'], xp + 6)
        self.assertEqual(solve(j, other['id'])['status'], 'completed')
        roundtrip(j)

    def test_too_many_slips_on_the_drill_leave_the_air_dead(self):
        day = self.day()
        j = job_journey('bulletin', day=day)
        solve_until_cut(j)
        steps, key = R.shift_steps(day, 'outage')
        for _ in range(RC.OUTAGE_SLIPS):
            j.act('rd_shift', part='outage', step=steps[0]['id'], value=list(reversed(key['outage.drill'])))
        shift(j, 'outage')
        d = data(j)
        self.assertEqual((d['stats']['dead_air'], d['stats']['restored']), (1, 0))
        self.assertTrue(any(p['stars'] == 2 and p['kind'] == 'review' for p in j.c['feed']))
        R.on_close(j.state, j.c)
        self.assertEqual(d['stats']['news_days'], 0, 'a day with dead air does not count for the probation')
        roundtrip(j)

    def test_an_outage_left_alone_ends_the_day_dead(self):
        j = job_journey('bulletin', day=self.day())
        solve_until_cut(j)
        out = R.on_close(j.state, j.c)
        self.assertTrue(any('Mất điện' in line for line in out['lines']))
        self.assertEqual(data(j)['stats']['dead_air'], 1)
        roundtrip(j)

    def test_no_outage_on_a_quiet_day(self):
        j = job_journey('bulletin', day=quiet(3))
        solve(j)
        self.assertEqual(data(j)['today']['out'], 0)


def solve_until_cut(j):
    tid = j.task['id']
    j.act('ask', task=tid)
    _, steps, key = R._active(j.get(tid))
    for st in steps:
        clear_desk(j)
        j.act('rd_step', task=tid, step=st['id'], value=key[st['id']])
    assert data(j)['today']['out'] == 1


@unittest.skipUnless(R, 'radio filtered out by MNL_CAREERS')
class Probation(unittest.TestCase):
    def good_day(self, j, day):
        j.c['day'] = day
        t = R.make_task(day, slot_of('bulletin', day), j.c['turn'])
        j.c['tasks'] = [t]
        j.c['active_task'] = t['id']
        R.on_task(j.state, j.c, t)
        shift(j, 'open')
        solve(j, t['id'])
        return R.on_close(j.state, j.c)

    def test_three_good_shifts_make_a_dj(self):
        days = [d for d in range(2, 80) if not R.outage_day(d)][:3]
        j = job_journey('bulletin', day=days[0], studio=False)
        out = self.good_day(j, days[0])
        self.assertEqual(data(j)['stats']['news_days'], 1)
        self.assertTrue(any('Còn 2 ca' in line for line in out['lines']))
        R.on_close(j.state, j.c)   # counted once a day
        self.assertEqual(data(j)['stats']['news_days'], 1)
        self.good_day(j, days[1])
        self.assertFalse(data(j)['promoted'])
        xp = j.c['xp']
        out = self.good_day(j, days[2])
        self.assertTrue(data(j)['promoted'])
        self.assertGreaterEqual(j.c['xp'], xp + 10)
        self.assertTrue(any('DJ' in line for line in out['lines']))
        validate_state(j.state)
        j.act('rd_role', role='dj')
        self.assertEqual(data(j)['role'], 'dj')


@unittest.skipUnless(R, 'radio filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def halfway(self):
        j = job_journey('playlist', day=quiet(3))
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = R._active(j.get(tid))
        st = steps[0]
        j.act('rd_step', task=tid, step=st['id'], value=wrong_value(st, key[st['id']]))
        for st in steps[:2]:
            j.act('rd_step', task=tid, step=st['id'], value=key[st['id']])
        roundtrip(j)
        return j

    def test_forged_task_fields_are_refused(self):
        j = self.halfway()
        forge = {
            'needs': lambda t: t.update(needs={'x': 1}),
            '_key': lambda t: t.update(_key={'playlist.fill': 1}),
            'kind': lambda t: t.update(kind='event'),
            'work': lambda t: t['work'].pop('playlist.drop'),
            'work value': lambda t: t['work'].update({'playlist.order': ['a']}),
            'at': lambda t: t.update(at=t['at'] + 1),
            'quality': lambda t: t.update(quality=100),
            'wrong': lambda t: t.update(wrong=0),
            'errors': lambda t: t.update(errors=[]),
            'errors ahead': lambda t: t['errors'].append('playlist.guest'),
            'paid': lambda t: t.update(paid=50),
            'stage': lambda t: t.update(stage='done'),
            'role': lambda t: t.update(role='owner'),
        }
        for name, fn in forge.items():
            with self.subTest(field=name):
                bad = copy.deepcopy(j.state)
                fn(bad['careers']['radio']['tasks'][0])
                with self.assertRaises(GameError):
                    validate_state(bad)

    def test_forged_records_are_refused(self):
        j = job_journey('bulletin', day=quiet(3))
        solve(j)
        roundtrip(j)
        forge = {
            'good above jobs': lambda d: d['stats'].update(good=5),
            'role without a good job': lambda d: d['stats']['roles'].update(dj=1),
            'unknown role': lambda d: d['stats']['roles'].update(owner=0),
            'intro type': lambda d: d.update(intro=1),
            'extra key': lambda d: d.update(vip=True),
            'active days': lambda d: d['stats'].update(active_days=9),
            'promoted without probation': lambda d: d.update(promoted=True),
            'dj role without probation': lambda d: d.update(role='dj'),
            'probation days without news jobs': lambda d: d['stats'].update(news_days=2),
            'restored without an outage': lambda d: d['stats'].update(restored=1),
            'outage state': lambda d: d['today'].update(out=3),
            'drill progress without an outage': lambda d: d['today'].update(out_at=1),
            'checklist ahead': lambda d: d['today'].update(open_at=9),
            'desk script': lambda d: d['desk'].update(ev=dict(id='desk-9', script='free_cake', day=3, at='between')),
        }
        for name, fn in forge.items():
            with self.subTest(record=name):
                bad = copy.deepcopy(j.state)
                fn(bad['careers']['radio']['ext']['data'])
                with self.assertRaises(GameError):
                    validate_state(bad)


@unittest.skipUnless(R, 'radio filtered out by MNL_CAREERS')
class Desk(unittest.TestCase):
    def test_ten_well_formed_surprises(self):
        self.assertEqual(len(RC.DESK), 10)
        self.assertEqual(len({x['id'] for x in RC.DESK}), 10)
        for x in RC.DESK:
            with self.subTest(script=x['id']):
                self.assertTrue(x['title'] and x['text'] and x['emoji'])
                self.assertGreaterEqual(len(x['options']), 3)
                self.assertEqual(sum(1 for o in x['options'] if o.get('good') is True), 1)
                for o in x['options']:
                    self.assertGreaterEqual(o.get('effects', {}).get('money', 0), 0)
                text = json.dumps(x, ensure_ascii=False)
                for b in ('NPC', 'người chơi', 'trong game', 'mô phỏng', 'anh ấy', 'cô ấy'):
                    self.assertNotIn(b, text)

    def test_each_surprise_blocks_the_work_and_every_choice_saves(self):
        for x in RC.DESK:
            for o in x['options']:
                with self.subTest(script=x['id'], option=o['id']):
                    j = job_journey('bulletin', day=quiet(4))
                    data(j)['desk']['ev'] = dict(id='desk-1', script=x['id'], day=j.c['day'], at='between')
                    data(j)['desk'].update(seq=1, fired=1)
                    validate_state(j.state)
                    tid = j.task['id']
                    j.act('ask', task=tid)
                    _, steps, key = R._active(j.get(tid))
                    before = copy.deepcopy(j.state)
                    with self.assertRaises(GameError):
                        j.act('rd_step', task=tid, step=steps[0]['id'], value=key[steps[0]['id']])
                    self.assertEqual(j.state, before)
                    self.assertTrue(j.act('rd_desk', option=o['id'])['message'])
                    self.assertIsNone(data(j)['desk']['ev'])
                    roundtrip(j)


@unittest.skipUnless(R, 'radio filtered out by MNL_CAREERS')
class Content(unittest.TestCase):
    def test_every_task_is_consistent_and_solvable_for_every_role(self):
        for day in range(1, 31):
            for slot in range(12):
                t = R.make_task(day, slot, 1)
                R.validate_task(copy.deepcopy(t), t)
                for role in R.ROLES:
                    _, steps, key = R._active(dict(t, role=role))
                    self.assertEqual(set(key), {s['id'] for s in steps})
                    for st in steps:
                        ids = [o['id'] for o in st.get('options', [])]
                        self.assertEqual(len(ids), len(set(ids)))
                        if st['type'] == 'choice':
                            self.assertIn(key[st['id']], ids)
                        elif st['type'] == 'order':
                            self.assertEqual(sorted(key[st['id']]), sorted(ids))
                        elif st['type'] == 'multi':
                            self.assertTrue(key[st['id']] and set(key[st['id']]) <= set(ids))
                        else:
                            self.assertIsInstance(key[st['id']], int)
                            self.assertGreater(key[st['id']], 0)

    def test_many_annoying_demands(self):
        # owner's standing rule: callers, sponsors, power cuts, abusive callers, names read wrong…
        self.assertGreaterEqual(len(RC.BULLETIN_FIX) + len(RC.SPOT_DEMANDS) + len(RC.WISH_SLIPS) + len(RC.NO_AIR) + len(RC.REQUEST_ODD)
                                + len(RC.CALL_FIRST) + len(RC.CALL_GRIPES) + len(RC.CALL_OFFTOPIC) + len(RC.GUEST_ODD) + len(RC.OUTAGE_CAUSES), 35)

    def test_the_copy_addresses_the_player_neutrally(self):
        text = json.dumps([R.content(), R.SPEC, RC.NOTEBOOK, RC.DESK, RC.PEOPLE], ensure_ascii=False)
        for word in ('anh ấy', 'cô ấy', 'người chơi', 'NPC'):
            self.assertNotIn(word, text)


if __name__ == '__main__':
    unittest.main()
