"""🔬 Viện nghiên cứu Sông Mây (game/careers/research.py): a salaried research shift on one of three tracks.

🌱 Giống cây (lai tạo, khảo nghiệm, ngân hàng hạt), 🍳 Công thức món (chuẩn hóa, hội đồng nếm, giá vốn và nhãn), 🛠️ Sáng chế
(mẫu thử, độ bền, hồ sơ sáng chế). Every step graded on the server; a wrong step stays open and lowers the quality; many
"oái oăm" demands (owner's standing rule): rats in the seed store, a ruined plot, a biased taster, a colleague taking the
credit, the council step from day 4, and the desk surprises (thí nghiệm nổ, chuột ăn mẫu, hội đồng khó tính, nhà tài trợ
đòi sớm, đồng nghiệp nhận vơ công…). Shift checklists, the director's safety walk, the night fine bounded by the wallet,
strict saves and the dormant record an untouched institute leaves out."""
import copy
import json
import unittest

from tests.helpers import Journey
from game import journey as jr
from game.careers import ORDER, PLUGINS
from game.engine import DORMANT, GameError, dormant_out, initial_career, new_state, public_state, validate_state, wake

R = PLUGINS.get('research')
if R is not None:
    from game.careers import research_content as RC


def slot_of(job, day=3):
    track = RC.JOBS[job][2]
    return next(s for s in range(12) if R.job_of(day, s, track) == job)


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


def job_journey(job, day=3):
    track = RC.JOBS[job][2]
    j = Journey('research', day=day, slot=slot_of(job, day))
    data(j)['track'] = track
    j.task.update(track=track)
    validate_state(j.state)
    return j


def clear_desk(j):
    ev = data(j)['desk']['ev']
    if ev:
        x = next(x for x in RC.DESK if x['id'] == ev['script'])
        j.act('rs_desk', option=next(o['id'] for o in x['options'] if o.get('good')))


def solve(j, tid=None, limit=40):
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    for _ in range(limit):
        clear_desk(j)
        t = j.get(tid)
        if t['status'] == 'completed':
            return t
        _, steps, key = R._active(t)
        st = steps[t['at']]
        j.act('rs_step', task=tid, step=st['id'], value=key[st['id']])
    raise AssertionError('research task did not finish')


def shift(j, part):
    for _ in range(6):
        clear_desk(j)
        steps, key = R.shift_steps(j.c['day'], part)
        at = data(j)['today'][part + '_at'] if data(j)['today']['day'] == j.c['day'] else 0
        if at >= len(steps):
            return
        st = steps[at]
        j.act('rs_shift', part=part, step=st['id'], value=key[st['id']])
    raise AssertionError('shift checklist did not finish')


def roundtrip(j):
    j.state = json.loads(json.dumps(j.state))
    validate_state(j.state)


@unittest.skipUnless(R, 'research filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_last_dormant_and_salaried(self):
        from game import operations
        from game.career_voice import salaried_set
        self.assertGreater(ORDER.index('research'), ORDER.index('banquet'))   # appended (other careers may sit between)
        self.assertIn('research', DORMANT)
        self.assertIn('research', salaried_set())
        self.assertIn('research', operations.SALARIED)
        posting = R.SPEC['employment']['postings'][0]
        self.assertEqual(posting['org'], 'Viện nghiên cứu Sông Mây')
        self.assertEqual((posting['salary'], posting['probation_days']), ((54, 70), 3))
        self.assertEqual(R.SPEC['tip'], 0)

    def test_opens_from_chapter_three_without_listing_it(self):
        s = new_state()
        jr.enable_story(s, 4242)
        s['journey']['chapter'] = 2
        self.assertFalse(jr.is_unlocked(s, 'research'))
        s['journey']['chapter'] = 3
        self.assertTrue(jr.is_unlocked(s, 'research'))
        self.assertNotIn('research', s['journey']['unlocked'])   # an older build would refuse a save that lists it
        self.assertIn('research', public_state(s)['journey']['unlocked'])

    def test_an_untouched_institute_stays_out_of_the_stored_save(self):
        s = new_state()
        out = dormant_out(s)
        self.assertNotIn('research', out['careers'])
        back = json.loads(json.dumps(out))
        self.assertTrue(wake(back))
        self.assertEqual(back['careers']['research'], initial_career('research'))
        j = job_journey('cross')
        solve(j)
        self.assertIn('research', dormant_out(j.state)['careers'])   # once worked, never left out again

    def test_every_registry_knows_it(self):
        from game import (career_competition_content as cc, career_scale_content as sc, career_specialism_content as spc,
                          career_stories as cs, certificate_content as ce, guide_content as gc, incident_content as ic,
                          life_content as lc, lb_titles, promotion_content as pc, review_aspects_content as ra, tip_content as tc,
                          work_gear, workplace_business as wb)
        from game.coach import own
        self.assertIn('research', cc.PROFILES)
        self.assertEqual(len(spc.packs('research')), 10)
        sc.profile('research')
        self.assertEqual(len(cs.ARCS['research']['beats']), 5)
        self.assertTrue(any('research' in g['careers'] for g in ce.GROUPS))
        self.assertIn('research', gc.CAREERS)
        self.assertIn('research', ic.EMPLOYEE)
        self.assertIn('research', lc.EMPLOYED)
        self.assertIn('research', lb_titles.CAREER_NOUN)
        self.assertIn('research', pc.EMP_TITLES)
        self.assertEqual(ra.FAMILY['research'], 'office')
        self.assertIn('research', tc.NORMS)
        self.assertIn('research', work_gear.NAMES)
        self.assertIn('research', wb.ORDERS)
        self.assertTrue(own('research'))


@unittest.skipUnless(R, 'research filtered out by MNL_CAREERS')
class Tracks(unittest.TestCase):
    def test_each_track_rotates_through_its_jobs_and_is_pure(self):
        for day in range(1, 8):
            for track, jobs in RC.TRACK_JOBS.items():
                self.assertEqual({R.job_of(day, s, track) for s in range(len(jobs))}, set(jobs))
        self.assertEqual(R.brief(5, 2, 'recipe'), R.brief(5, 2, 'recipe'))
        self.assertEqual(R.make_task(5, 2, 1)['track'], 'seed')

    def test_unread_slips_follow_the_track_chosen(self):
        j = Journey('research')
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError):
            j.act('rs_track', track='alchemy')
        self.assertEqual(j.state, before)
        r = j.act('rs_track', track='invent')
        self.assertIn('sáng chế', r['message'].lower())
        self.assertTrue(all(t['track'] == 'invent' for t in j.c['tasks'] if not t['known']))

    def test_every_job_of_every_track_finishes_and_pays_a_bonus(self):
        for job in RC.JOBS:
            for day in (2, 5, 12):
                with self.subTest(job=job, day=day):
                    j = job_journey(job, day)
                    money = j.c['money']
                    t = solve(j)
                    self.assertEqual((t['status'], t['quality']), ('completed', 100))
                    self.assertEqual(t['paid'], RC.BONUS[job])
                    self.assertGreaterEqual(j.c['money'] - money, t['paid'])
                    roundtrip(j)

    def test_answers_stay_on_the_server(self):
        j = job_journey('taste')
        j.act('ask', task=j.task['id'])
        v = public_state(j.state)['careers']['research']
        t = next(x for x in v['tasks'] if x['id'] == j.task['id'])
        self.assertNotIn('_key', json.dumps(t))
        self.assertTrue(t['needs']['steps'])


@unittest.skipUnless(R, 'research filtered out by MNL_CAREERS')
class Demands(unittest.TestCase):
    def test_a_wrong_step_stays_open_lowers_quality_and_explains(self):
        j = job_journey('cross')
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = R._active(j.get(tid))
        st = steps[1]   # the seeds number
        j.act('rs_step', task=tid, step=steps[0]['id'], value=key[steps[0]['id']])
        r = j.act('rs_step', task=tid, step=st['id'], value=wrong_value(st, key[st['id']]))
        self.assertFalse(r['correct'])
        self.assertIn('nảy mầm', r['message'])
        t = j.get(tid)
        self.assertEqual((t['at'], t['quality'], t['errors']), (1, 100 - RC.WRONG_COST, [st['id']]))
        solve(j, tid)
        self.assertEqual(j.get(tid)['paid'], max(3, round(RC.BONUS['cross'] * (100 - RC.WRONG_COST) / 100)))
        roundtrip(j)

    def test_the_council_closes_every_job_from_day_four(self):
        for job in RC.JOBS:
            early = R.brief(3, slot_of(job, 3), RC.JOBS[job][2])[1]
            late = R.brief(9, slot_of(job, 9), RC.JOBS[job][2])[1]
            self.assertFalse(any(s['id'].endswith('.council') for s in early), job)
            self.assertEqual(late[-1]['id'], f'{job}.council', job)
            self.assertIn('right', [o['id'] for o in late[-1]['options']])

    def test_rats_get_into_some_field_trials_and_a_plot_is_always_ruined(self):
        seen = 0
        for day in range(3, 40):
            b, steps, key, *_ = R.brief(day, slot_of('field', day) if R.job_of(day, slot_of('field', day), 'seed') == 'field' else 0, 'seed')
            if b.get('plots') is None:
                continue
            ids = [s['id'] for s in steps]
            seen += 'field.rats' in ids
            labels = [o['label'] for o in steps[0]['options']]
            self.assertEqual(sum(any(w in lbl for _, w in RC.PLOT_SPOIL) for lbl in labels), 1)
        self.assertGreater(seen, 0)

    def test_tasting_drops_the_biased_taster_and_the_winner_is_unique(self):
        for day in range(1, 30):
            b, steps, key, *_ = R.brief(day, slot_of('taste', 3), 'recipe')
            if 'codes' not in b:
                continue
            self.assertEqual(key['taste.code'], 'blind')
            self.assertIn(key['taste.best'], [o['id'] for o in steps[3]['options']])

    def test_many_annoying_desk_surprises_each_with_a_right_answer(self):
        ids = {x['id'] for x in RC.DESK}
        self.assertGreaterEqual(len(ids), 12)
        self.assertTrue({'boom', 'rats', 'council', 'sponsor', 'credit'} <= ids)   # nổ, chuột, hội đồng, nhà tài trợ, nhận vơ công
        for x in RC.DESK:
            self.assertEqual(sum(1 for o in x['options'] if o.get('good') is True), 1, x['id'])
            self.assertIn(x['default'], [o['id'] for o in x['options']])

    def test_a_surprise_blocks_work_until_decided(self):
        j = Journey('research', day=6, slot=1)
        d = data(j)
        d['desk']['ev'] = dict(id='desk-1', script='credit', day=6, at='between')
        validate_state(j.state)
        j.act('ask', task=j.task['id'])
        _, steps, key = R._active(j.task)
        with self.assertRaises(GameError):
            j.act('rs_step', task=j.task['id'], step=steps[0]['id'], value=key[steps[0]['id']])
        r = j.act('rs_desk', option='book')
        self.assertTrue(r['celebrate'])
        roundtrip(j)


@unittest.skipUnless(R, 'research filtered out by MNL_CAREERS')
class Shift(unittest.TestCase):
    def test_open_and_close_checklists_and_closing_stops_lab_work(self):
        j = job_journey('proto')
        shift(j, 'open')
        solve(j)
        shift(j, 'close')
        self.assertTrue(public_state(j.state)['careers']['research']['data']['shift']['close']['done'])
        roundtrip(j)

    def test_close_waits_for_work_in_progress(self):
        j = job_journey('drop')
        tid = j.task['id']
        j.act('ask', task=tid)
        _, steps, key = R._active(j.task)
        j.act('rs_step', task=tid, step=steps[0]['id'], value=key[steps[0]['id']])
        steps_c, key_c = R.shift_steps(j.c['day'], 'close')
        with self.assertRaises(GameError):
            j.act('rs_shift', part='close', step=steps_c[0]['id'], value=key_c[steps_c[0]['id']])

    def test_safety_walk_passes_with_the_opening_and_warns_without(self):
        day = next(d for d in range(2, 200) if R.safety_day(d))
        good = job_journey('scale', day)
        shift(good, 'open')
        solve(good)
        self.assertEqual(data(good)['today']['safety'], 1)
        bad = job_journey('scale', day)
        solve(bad)
        self.assertEqual(data(bad)['today']['safety'], 2)
        self.assertEqual(data(bad)['stats']['safety_fail'], 1)
        roundtrip(bad)

    def test_the_night_fine_is_bounded_by_the_contract_and_the_wallet(self):
        from game.careers import kit
        self.assertEqual(R.night_fine(dict(job=dict(salary=70))), 6)
        self.assertEqual(R.night_fine(dict(job=dict(salary=10))), RC.NIGHT_MIN)
        hit = None
        for seed in range(400):
            if kit.rng('research', 'night', seed, 3).random() < RC.NIGHT_CHANCE:
                hit = seed
                break
        self.assertIsNotNone(hit)
        j = job_journey('bank')
        jr.enable_story(j.state, hit)
        j.state['journey']['seed'] = hit
        j.state['journey']['wallet'] = 2
        solve(j)
        before = j.state['journey']['wallet']
        out = R.on_close(j.state, j.c)
        self.assertTrue(any('🌙' in line for line in out['lines']))
        self.assertEqual(before - j.state['journey']['wallet'], min(2, R.night_fine(j.c)))
        self.assertGreaterEqual(j.state['journey']['wallet'], 0)


@unittest.skipUnless(R, 'research filtered out by MNL_CAREERS')
class StrictSaves(unittest.TestCase):
    def test_a_tampered_task_or_record_is_refused(self):
        j = job_journey('patent')
        tid = j.task['id']
        solve(j)
        for mutate in (lambda t: t.update(paid=t['paid'] + 5), lambda t: t.update(quality=90), lambda t: t.update(track='seed'),
                       lambda t: t['_key'].update(x=1), lambda t: t.update(at=0)):
            bad = copy.deepcopy(j.state)
            t = next(x for x in bad['careers']['research']['tasks'] if x['id'] == tid)
            mutate(t)
            with self.assertRaises(GameError):
                validate_state(bad)
        for mutate in (lambda d: d.update(track='magic'), lambda d: d['stats'].update(good=d['stats']['jobs'] + 1),
                       lambda d: d['today'].update(night=99), lambda d: d.update(extra=1)):
            bad = copy.deepcopy(j.state)
            mutate(bad['careers']['research']['ext']['data'])
            with self.assertRaises(GameError):
                validate_state(bad)
