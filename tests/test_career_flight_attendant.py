"""Tiếp viên Cánh Cò (plugin career flight_attendant): boarding at the door, the safety
demonstration and the cabin check, the cart row by row with the special meals, the timed
turbulence, difficult passengers, first aid, the pay, hidden information, determinism,
save validation and old saves."""
import copy
import json
import unittest
from unittest import mock

from tests.helpers import Journey
from game.careers import kit, PLUGINS
from game.content import make_task
from game.engine import GameError, migrate_state, new_state, public_state, validate_state

FA = PLUGINS.get('flight_attendant')


def find(pick, days=range(1, 80), slots=range(0, 8)):
    return next((d, s) for d in days for s in slots if pick(FA.make_task(d, s, 1)))


class Base(unittest.TestCase):
    def setUp(self):
        if FA is None:
            raise unittest.SkipTest('flight_attendant is filtered out by MNL_CAREERS')
        self.j = Journey('flight_attendant')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, pick, days=range(1, 80)):
        day, slot = find(pick, days)
        j = Journey('flight_attendant', slot=slot, day=day)
        tid = j.c['active_task']
        if not j.get(tid)['known']:
            j.act('ask', task=tid)
        return j, tid

    def view(self, j, tid):
        return next(t for t in public_state(j.state)['careers']['flight_attendant']['tasks'] if t['id'] == tid)

    def settle_desk(self, j):
        ev = j.c['ext']['data']['desk']['ev']
        if ev:
            j.act('fa_desk', option=kit.desk_script(FA.DESK, ev['script'])['default'])

    def serve_row(self, j, tid):
        for st in FA._row(j.get(tid))['seats']:
            if st['kind'] == 'sleep':
                j.act('fa_skip', task=tid, seat=st['seat'])
                continue
            for it in FA.right_items(st):
                j.act('fa_give', task=tid, seat=st['seat'], item=it)

    def solve(self, j, tid):
        self.settle_desk(j)
        t = j.get(tid)
        if not t['known']:
            j.act('ask', task=tid)
        t = j.get(tid)
        n, k = t['needs'], t['kind']
        if k == 'board':
            for q in n['queue']:
                j.act('fa_door', task=tid, act=FA.ISSUE_ACT[q['issue']])
            return j.act('fa_close', task=tid)
        if k == 'demo':
            for x in FA.DEMO_IDS:
                j.act('fa_demo', task=tid, part=x)
            j.act('fa_walk', task=tid)
            for seat, v in n['cabin']['state'].items():
                if v != 'ok':
                    j.act('fa_fix', task=tid, seat=seat)
            return j.act('fa_ready', task=tid)
        if k == 'service':
            for i in range(len(n['rows'])):
                self.serve_row(j, tid)
                if i < len(n['rows']) - 1:
                    j.act('fa_next', task=tid)
                    tb = j.c['ext']['data']['turb']
                    if tb and tb['stage'] == 'coming':
                        for w in FA.SECURE_IDS:
                            j.act('fa_secure', what=w)
            return j.act('fa_stow', task=tid)
        if k == 'calm':
            r = None
            for _ in range(3):
                r = j.act('fa_calm', task=tid, option='a')
            return r
        for q in FA.Q_IDS:
            j.act('fa_ask', task=tid, q=q)
        for it in FA.CASES[n['case']]['need']:
            j.act('fa_care', task=tid, item=it)
        return j.act('fa_done', task=tid)


class Spec(Base):
    def test_spec_shape(self):
        s = FA.SPEC
        self.assertEqual((s['id'], s['prefix']), ('flight_attendant', 'fa_'))
        self.assertTrue(5 <= len(s['people']) <= 8)
        for p in s['people']:
            self.assertIn(p[3], ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet'))
        self.assertEqual(len(s['staff']), 4)
        self.assertEqual(len(s['stories']), 3)
        self.assertEqual(len(s['review_asides']), 4)
        self.assertTrue(5 <= len(s['situations']) <= 8)
        for x in s['situations']:
            for opt in x['options']:
                self.assertTrue(2 <= len(opt['perspectives']) <= 3, opt['id'])
                self.assertLessEqual(opt.get('cost', 0), 80)
        for k in s['no_tick'] + s['free_actions'] + tuple(FA.ACTIONS):
            self.assertTrue(k.startswith('fa_'), k)
        for x in FA.CALM.values():
            self.assertEqual(len(x['beats']), 3)
            for b in x['beats']:
                self.assertEqual([o['id'] for o in b['options']], ['a', 'b', 'c'])
                self.assertEqual(b['options'][0]['grade'], 'good')     # tests (and the first-day guide) pick 'a'

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'giả lập', 'nhiệm vụ')
        blob = json.dumps([FA.DESK, FA.SITUATIONS, FA.REG_STORY, FA.ARC, FA.INTRO, FA.SPEC['meta'], FA.CALM, FA.CASES, FA.BOARDERS],
                          ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_registered(self):
        from game.content import CAREERS
        from game import employment as emp
        self.assertIn('flight_attendant', CAREERS)
        self.assertTrue(emp.required('flight_attendant'))


class Determinism(Base):
    def test_jobs_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 20):
            for slot in range(0, 8):
                a, b = FA.make_task(day, slot, 1), FA.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                self.assertEqual(json.loads(json.dumps(a['needs'])), a['needs'])
                self.assertEqual(make_task('flight_attendant', day, slot, 1)['id'], f'flight_attendant-{day:04d}-{slot:02d}')

    def test_first_day_is_gentle(self):
        self.assertEqual([FA.make_task(1, s, 1)['kind'] for s in range(3)], ['board', 'demo', 'service'])
        q = FA.make_task(1, 0, 1)['needs']['queue']
        self.assertEqual([x['issue'] for x in q], [None, 'bag', None, None])
        sv = FA.make_task(1, 2, 1)['needs']
        self.assertIsNone(sv['ssr']['nut'])
        self.assertIsNone(FA.turb_plan(1))
        self.assertEqual(FA.turb_plan(2), FA.TURB_FIRST)

    def test_every_service_can_be_served_by_the_rules(self):
        for day in range(1, 60):
            for slot in range(0, 8):
                t = FA.make_task(day, slot, 1)
                if t['kind'] != 'service':
                    continue
                nut = t['needs']['ssr'].get('nut')
                for row in t['needs']['rows']:
                    for s in row['seats']:
                        items = FA.right_items(s)
                        if row['row'] == nut:
                            self.assertNotIn('nuts', items, s)
                        if s['kind'] == 'kid':
                            self.assertFalse(set(items) & FA.HOT)

    def test_kinds_all_show_up(self):
        kinds = {FA.make_task(d, s, 1)['kind'] for d in range(2, 30) for s in range(8)}
        self.assertEqual(kinds, set(FA.KINDS))


class Boarding(Base):
    def test_door_reads_the_pass(self):
        j = self.j
        tid = j.c['active_task']
        v = self.view(j, tid)
        self.assertIsNone(v['needs'])
        j.act('ask', task=tid)
        v = self.view(j, tid)
        self.assertEqual(sum(x is not None for x in v['needs']['queue']), 1)
        self.assertNotIn('issue', json.dumps(v['needs']['queue']))
        r = self.solve(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertIn(f'{FA.BONUS} xu', r['message'])

    def test_power_bank_to_the_hold_is_a_safety_slip(self):
        j, tid = self.at(lambda t: t['kind'] == 'board' and any(q['issue'] == 'power' for q in t['needs']['queue']))
        q = j.get(tid)['needs']['queue']
        for x in q:
            if x['issue'] == 'power':
                r = j.act('fa_door', task=tid, act='hold')
                self.assertFalse(r['correct'])
                self.assertTrue(j.get(tid)['slips'][-1]['safety'])
            j.act('fa_door', task=tid, act=FA.ISSUE_ACT[x['issue']])
        j.act('fa_close', task=tid)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_exit_row_needs_able_adults(self):
        j, tid = self.at(lambda t: t['kind'] == 'board' and any(q['issue'] == 'exit' for q in t['needs']['queue']))
        for x in j.get(tid)['needs']['queue']:
            if x['issue'] == 'exit':
                self.assertIn(int(x['seat'][:-1]), (1, 17))
                r = j.act('fa_door', task=tid, act='seat')
                self.assertFalse(r['correct'])
                self.assertEqual(j.get(tid)['slips'][-1]['code'], 'exit')
            j.act('fa_door', task=tid, act=FA.ISSUE_ACT[x['issue']])

    def test_cannot_close_the_door_early(self):
        j = self.j
        tid = j.c['active_task']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('fa_close', task=tid)


class Demo(Base):
    def test_demo_in_order_then_the_cabin(self):
        j = self.j
        tid = next(t['id'] for t in j.c['tasks'] if t['kind'] == 'demo')
        self.assertTrue(j.get(tid)['known'])            # the purser's job for you: nothing to ask
        r = j.act('fa_demo', task=tid, part='vest')
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['step'], 0)
        with self.assertRaises(GameError):
            j.act('fa_walk', task=tid)
        for x in FA.DEMO_IDS:
            j.act('fa_demo', task=tid, part=x)
        self.assertIsNone(self.view(j, tid)['needs']['cabin']['state'])
        j.act('fa_walk', task=tid)
        state = self.view(j, tid)['needs']['cabin']['state']
        bad = [k for k, v in state.items() if v != 'ok']
        self.assertEqual(len(bad), 2)
        ok = next(k for k, v in state.items() if v == 'ok')
        with self.assertRaises(GameError):
            j.act('fa_fix', task=tid, seat=ok)
        j.act('fa_fix', task=tid, seat=bad[0])
        j.act('fa_ready', task=tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertTrue(any(x['code'] in ('belt', 'cabin_tray') for x in t['slips']))

    def test_unbelted_passenger_left_is_a_safety_slip(self):
        j, tid = self.at(lambda t: t['kind'] == 'demo' and 'belt' in t['needs']['cabin']['state'].values())
        for x in FA.DEMO_IDS:
            j.act('fa_demo', task=tid, part=x)
        j.act('fa_walk', task=tid)
        j.act('fa_ready', task=tid)
        self.assertTrue(any(x['safety'] for x in j.get(tid)['slips']))


class Service(Base):
    def service(self, pick=lambda t: True, days=range(2, 80)):
        return self.at(lambda t: t['kind'] == 'service' and pick(t), days)

    def test_rows_are_revealed_one_at_a_time(self):
        j, tid = self.service()
        v = self.view(j, tid)
        rows = v['needs']['rows']
        self.assertIsNotNone(rows[0]['seats'])
        self.assertTrue(all(r['seats'] is None for r in rows[1:]))

    def test_peanuts_never_in_the_allergy_row(self):
        j, tid = self.service(lambda t: t['needs']['ssr'].get('nut'))
        t = j.get(tid)
        nut = t['needs']['ssr']['nut']
        while FA._row(j.get(tid))['row'] != nut:
            self.serve_row(j, tid)
            j.act('fa_next', task=tid)
            tb = self.d['turb']
            if tb and tb['stage'] == 'coming':
                for w in FA.SECURE_IDS:
                    j.act('fa_secure', what=w)
        seat = next(s for s in FA._row(j.get(tid))['seats'] if s['kind'] == 'nutrow')
        r = j.act('fa_give', task=tid, seat=seat['seat'], item='nuts')
        self.assertFalse(r['correct'])
        self.assertTrue(j.get(tid)['slips'][-1]['safety'])
        self.assertNotIn('nuts', j.get(tid)['given'].get(seat['seat'], []))
        j.act('fa_give', task=tid, seat=seat['seat'], item='cake')

    def test_no_hot_drink_for_a_small_child(self):
        j, tid = self.at(lambda t: t['kind'] == 'service' and any(s['kind'] == 'kid' for s in t['needs']['rows'][0]['seats']), range(1, 80))
        kid = next(s for s in FA._row(j.get(tid))['seats'] if s['kind'] == 'kid')
        r = j.act('fa_give', task=tid, seat=kid['seat'], item=kid['drink'])
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['slips'][-1]['code'], 'hot_kid')
        j.act('fa_give', task=tid, seat=kid['seat'], item='juice')
        self.assertIn('juice', j.get(tid)['given'][kid['seat']])

    def test_vegetarian_meal_from_the_list(self):
        j, tid = self.at(lambda t: t['kind'] == 'service' and any(s['kind'] == 'veg' for s in t['needs']['rows'][0]['seats']), range(1, 80))
        veg = next(s for s in FA._row(j.get(tid))['seats'] if s['kind'] == 'veg')
        self.assertEqual(j.get(tid)['needs']['ssr']['veg'], veg['seat'])
        r = j.act('fa_give', task=tid, seat=veg['seat'], item='banhmi')
        self.assertFalse(r['correct'])
        j.act('fa_give', task=tid, seat=veg['seat'], item='veg')

    def test_let_a_sleeper_sleep(self):
        j, tid = self.at(lambda t: t['kind'] == 'service' and any(s['kind'] == 'sleep' for s in t['needs']['rows'][0]['seats']))
        z = next(s for s in FA._row(j.get(tid))['seats'] if s['kind'] == 'sleep')
        with self.assertRaises(GameError):
            j.act('fa_skip', task=tid, seat=next(s for s in FA._row(j.get(tid))['seats'] if s['kind'] != 'sleep')['seat'])
        j.act('fa_skip', task=tid, seat=z['seat'])
        self.assertIn(z['seat'], j.get(tid)['skipped'])

    def test_skipping_a_row_is_noticed(self):
        j, tid = self.service()
        j.act('fa_next', task=tid)
        self.assertTrue(any(x['code'].startswith('missed_') for x in j.get(tid)['slips']))

    def test_turbulence_in_time(self):
        clock = [1000.0]
        with mock.patch.object(kit, 'now', side_effect=lambda: clock[0]):
            j, tid = self.service(days=range(2, 3))
            self.serve_row(j, tid)
            r = j.act('fa_next', task=tid)
            self.assertTrue(r.get('surprise'))
            tb = j.c['ext']['data']['turb']
            self.assertEqual((tb['stage'], tb['limit']), ('coming', FA.TURB_FIRST))
            with self.assertRaises(GameError):
                j.act('fa_give', task=tid, seat=FA._row(j.get(tid))['seats'][0]['seat'], item='water')
            with self.assertRaises(GameError):
                j.act('fa_turb_end')
            for w in FA.SECURE_IDS:
                clock[0] += 3
                r = j.act('fa_secure', what=w)
            self.assertTrue(r.get('celebrate'))
            self.assertEqual(j.c['ext']['data']['turb']['stage'], 'done')
            self.assertFalse(any(x['code'] in ('spill', 'cart', 'stand') for x in j.get(tid).get('slips') or []))

    def test_turbulence_too_slow(self):
        clock = [1000.0]
        with mock.patch.object(kit, 'now', side_effect=lambda: clock[0]):
            j, tid = self.service(days=range(2, 3))
            self.serve_row(j, tid)
            j.act('fa_next', task=tid)
            j.act('fa_secure', what='sit')
            clock[0] += FA.TURB_FIRST + 1
            r = j.act('fa_turb_end')
            self.assertFalse(r['correct'])
        codes = {x['code'] for x in j.get(tid)['slips']}
        self.assertTrue({'spill', 'cart'} <= codes)
        self.assertNotIn('stand', codes)
        validate_state(json.loads(json.dumps(j.state)))

    def test_turbulence_once_a_day_and_closed_at_day_end(self):
        clock = [1000.0]
        with mock.patch.object(kit, 'now', side_effect=lambda: clock[0]):
            j, tid = self.service(days=range(2, 3))
            self.serve_row(j, tid)
            j.act('fa_next', task=tid)
            j.act('end_day')
        self.assertEqual(j.c['ext']['data']['turb']['stage'], 'done')
        validate_state(j.state)


class Calm(Base):
    def test_three_beats_graded(self):
        j, tid = self.at(lambda t: t['kind'] == 'calm' and t['needs']['script'] == 'bin')
        j.act('fa_calm', task=tid, option='c')
        v = self.view(j, tid)
        self.assertEqual(len(v['needs']['calm']['said']), 1)
        self.assertNotIn('grade', json.dumps(v['needs']['calm']))
        j.act('fa_calm', task=tid, option='a')
        j.act('fa_calm', task=tid, option='b')
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        crit = {x['key']: x['score'] for x in FA.feedback(j.c, t)['criteria']}
        self.assertEqual((crit['calm'], crit['rule'], crit['solve']), (2, 5, 3))

    def test_ignoring_smoke_is_a_safety_slip(self):
        j, tid = self.at(lambda t: t['kind'] == 'calm' and t['needs']['script'] == 'vape')
        j.act('fa_calm', task=tid, option='c')
        self.assertTrue(j.get(tid)['slips'][-1]['safety'])


class Medical(Base):
    def test_right_care_and_the_captain(self):
        j, tid = self.at(lambda t: t['kind'] == 'medical' and t['needs']['case'] == 'hypo')
        v = self.view(j, tid)
        self.assertEqual(v['needs']['case']['answers'], {})
        j.act('fa_ask', task=tid, q='history')
        self.assertIn('tiểu đường', json.dumps(self.view(j, tid)['needs']['case'], ensure_ascii=False))
        for it in ('juice', 'cake', 'captain'):
            j.act('fa_care', task=tid, item=it)
        r = j.act('fa_done', task=tid)
        self.assertEqual(j.get(tid)['mistakes'], 0)
        self.assertTrue(r.get('celebrate'))

    def test_own_medicine_is_never_given(self):
        j, tid = self.at(lambda t: t['kind'] == 'medical')
        r = j.act('fa_care', task=tid, item='own_med')
        self.assertFalse(r['correct'])
        self.assertTrue(j.get(tid)['slips'][-1]['safety'])

    def test_chest_pain_without_the_captain_is_unsafe(self):
        j, tid = self.at(lambda t: t['kind'] == 'medical' and t['needs']['case'] == 'chest')
        j.act('fa_care', task=tid, item='oxygen')
        r = j.act('fa_done', task=tid)
        self.assertFalse(r['correct'])
        codes = {x['code'] for x in j.get(tid)['slips']}
        self.assertTrue({'no_captain', 'no_doctor'} <= codes)

    def test_done_needs_some_care(self):
        j, tid = self.at(lambda t: t['kind'] == 'medical')
        with self.assertRaises(GameError):
            j.act('fa_done', task=tid)


class Day(Base):
    def test_a_full_first_day_by_the_book(self):
        j = self.j
        j.act('fa_intro')
        tids = [t['id'] for t in j.c['tasks']]
        self.assertEqual([j.get(x)['kind'] for x in tids], ['board', 'demo', 'service'])
        for tid in tids:
            self.solve(j, tid)
            self.assertEqual(j.get(tid)['status'], 'completed')
            self.assertEqual(j.get(tid)['mistakes'], 0, j.get(tid).get('slips'))
        paid = [r['amount'] for r in j.c['ops']['finance']['ledger'] if r.get('ref') in tids and r.get('category') == 'revenue']
        self.assertEqual(paid, [FA.BONUS] * 3)
        stars = [f['stars'] for f in j.c['feed'] if f.get('kind') == 'review']
        self.assertTrue(stars and min(stars) >= 4)
        r = j.act('end_day')
        self.assertEqual(r['summary']['job']['salary'], j.c['job']['salary'])
        self.assertTrue(r['summary']['career']['lines'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_a_week_keeps_the_save_valid(self):
        j = self.j
        clock = [5000.0]
        with mock.patch.object(kit, 'now', side_effect=lambda: clock[0]):
            for day in range(1, 8):
                for t in [x for x in j.c['tasks'] if x['status'] not in ('completed', 'cancelled')]:
                    self.solve(j, t['id'])
                    self.assertEqual(j.get(t['id'])['status'], 'completed')
                validate_state(json.loads(json.dumps(j.state)))
                j.act('end_day')
                j.act('start_day')
        self.assertGreaterEqual(self.d['stats']['jobs'], 14)

    def test_story_and_regulars(self):
        j = self.j
        self.assertIsNone(self.d['arc']['due'])
        tid = j.c['active_task']
        r = self.solve(j, tid)
        self.assertEqual(self.d['arc']['due'], 'scarf')
        j.act('fa_arc')
        npc = int(j.get(tid)['npc'].rsplit('_', 1)[1]) - 1
        if npc in FA.REG_STORY:
            self.assertIn(FA.REG_STORY[npc][0], r['message'])

    def test_every_surprise_option_is_playable(self):
        for x in FA.DESK:
            for o in x['options']:
                j = Journey('flight_attendant')
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('fa_door', task=j.c['active_task'], act='seat')
                r = j.act('fa_desk', option=o['id'])
                self.assertTrue(r['message'])
                validate_state(json.loads(json.dumps(j.state)))

    def test_situations_are_playable(self):
        j = self.j
        j.c['money'] += 100
        j.c['ops']['finance']['opening_balance'] += 100
        for x in FA.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)


class Saves(Base):
    def test_forged_needs_are_rejected(self):
        s = copy.deepcopy(self.j.state)
        t = s['careers']['flight_attendant']['tasks'][0]
        t['needs']['queue'][0]['issue'] = 'power'
        with self.assertRaises(GameError):
            validate_state(s)

    def test_broken_task_fields_are_rejected(self):
        j = self.j
        tid = next(t['id'] for t in j.c['tasks'] if t['kind'] == 'service')
        for key, value in (('given', {'99Z': ['water']}), ('stage', 'moon'), ('row', 9), ('used', ['magic']), ('choices', ['z']),
                           ('skipped', ['1A', '1A']), ('step', 40)):
            s = copy.deepcopy(j.state)
            next(x for x in s['careers']['flight_attendant']['tasks'] if x['id'] == tid)[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_broken_data_is_rejected(self):
        for path, value in ((('stats', 'jobs'), -1), (('arc', 'due'), 'dragon'),
                            (('turb',), dict(day=1, task='x', stage='coming', start=1.0, limit=999, done=[], result=None)),
                            (('turbs',), [dict(day=1)] * 30)):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['flight_attendant']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_old_save_without_the_cabin_gains_it(self):
        s = new_state()
        s['careers'].pop('flight_attendant')
        s = migrate_state(s)
        validate_state(s)
        self.assertEqual(s['careers']['flight_attendant']['job']['status'], 'none')

    def test_old_data_gains_new_fields(self):
        j = self.j
        d = j.c['ext']['data']
        for k in ('intro', 'arc', 'regulars', 'today', 'turbs', 'log'):
            d.pop(k)
        d['stats'].pop('calm')
        s = migrate_state(json.loads(json.dumps(j.state)))
        validate_state(s)
        j.state = s
        self.solve(j, j.c['active_task'])
        validate_state(j.state)

    def test_public_view_is_json(self):
        view = public_state(self.j.state)['careers']['flight_attendant']
        json.dumps(view)
        for k in ('stats', 'mod', 'desk', 'arc', 'intro', 'turb'):
            self.assertIn(k, view['data'])


class Shell(Base):
    """The crew's own shell: airline words on duty, a departures board line per job, passenger reviews."""
    def test_reporting_for_duty_and_another_job_have_airline_words(self):
        j = self.j
        j.act('fa_intro')
        for t in list(j.c['tasks']):
            self.solve(j, t['id'])
        j.act('end_day')
        self.assertEqual(j.act('start_day')['message'], FA.SPEC['open_line'])
        self.settle_desk(j)
        self.assertEqual(j.act('more_work')['message'], FA.SPEC['more_line'])

    def test_the_board_line_is_public_before_the_job_is_read(self):
        j = self.j
        tid = j.c['active_task']
        view = self.view(j, tid)
        self.assertEqual(view['leg'], j.get(tid)['needs']['leg'])
        self.assertRegex(view['leg']['dep'], r'^\d\d:\d\d$')

    def test_reviews_are_passengers_never_a_shop(self):
        from game import feedback as fbm
        j = self.j
        j.act('fa_intro')
        for t in list(j.c['tasks']):
            self.solve(j, t['id'])
        posts = [f for f in j.c['feed'] if f.get('kind') == 'review']
        self.assertTrue(posts)
        for p in posts:
            self.assertTrue(p['feedback']['own'])
            self.assertEqual(p['feedback']['status'], 'closed')
            self.assertNotRegex(p['text'].lower(), r'quán|tiệm')
            self.assertFalse(fbm.public_post(p)['feedback']['can_report'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_every_voice_speaks_for_both_ends(self):
        t = FA.make_task(3, 1, 1)
        for i in FA.VOICES:
            for s in (1, 3, 4, 5):
                text = FA.review_text(None, dict(t, npc=f'flight_attendant_npc_{i + 1:02d}', slips=[]), 'regular', s, [], 3)
                self.assertTrue(text)
                self.assertNotIn('quán', text)


if __name__ == '__main__':
    unittest.main()
