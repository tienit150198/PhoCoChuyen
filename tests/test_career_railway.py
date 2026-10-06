"""Gác chắn đường ngang Bến Mây (plugin career railway): the hand-over and its faults, a train seen through by the book
(the read-back, clearing the crossing, the bell before the arm, the people pushing at the barrier, the clear flag,
watching the train, the station's word before opening, the log), stopping a train, delays and a second train, the
track patrol, surprises, encounters, situations, determinism, hidden information and saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game.careers import kit, PLUGINS
from game.careers import air_odd as ao
from game.content import make_task
from game.engine import GameError, migrate_state, new_state, public_state, validate_state

RW = PLUGINS.get('railway')
RC = __import__('game.careers.railway_content', fromlist=['x']) if RW else None


def best_answer(x):
    k = x['kind']
    if k == 'bargain':
        return dict(tone='firm', say=['rule', 'alt'], to='company', n=x['limit'])
    say = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'corner': ['speak', 'rule'], 'demand': ['rule', 'alt']}[k]
    to = 'self' if x['rank'] == 'kin' else 'company' if k in ('charm', 'harass', 'corner') else 'crew'
    return dict(tone='firm', say=say, to=to)


def settle(j):
    """Decide an open surprise and answer an open encounter the careful way."""
    for _ in range(4 * ao.MAX_ROUNDS):
        d = j.c['ext']['data']
        if d['desk']['ev']:
            x = kit.desk_script(RW.DESK, d['desk']['ev']['script'])
            good = next((o['id'] for o in x['options'] if o.get('good') is True), x['default'])
            j.act('rw_desk', option=good)
            continue
        ev = d['odd']['ev']
        if not ev:
            return
        j.act('rw_odd', **best_answer(ao.script(RW.ODD, ev['script'])))


def quiet(j):
    """No encounter or surprise planned for the rest of today."""
    d = j.c['ext']['data']
    ao.ensure(d)
    d['odd'].update(day=j.c['day'], plan=[], fired=0, ev=None)
    d['desk'].update(day=j.c['day'], plan=[], fired=0, ev=None)


def steps_left(t):
    return sum(RW._crowd_of(k)['steps'] - t['progress'].get(k, 0) for k in t['left'])


def train_move(t, d):
    """The careful keeper's next move on a train (from the full task: the test may look at hidden keys)."""
    tid = t['id']
    if t['eta'] is None:
        if d['odd']['fatigue'] >= ao.TIRED and not t['awake']:
            return 'rw_wake', {}
        return 'rw_readback', dict(option=t['_rb'])
    if t['standing']:
        if t['left']:
            k = t['left'][0]
            return 'rw_clear', dict(who=k, how=RW._crowd_of(k)['works'][0])
        if t['arm'] == 'up':
            return ('rw_warn', {}) if t['bell'] is None else ('rw_lower', {})
        return 'rw_allclear', {}
    if not t['passed']:
        on = RW._talking(t)
        if t['left'] and t['scanned'] and not t['stopped'] and t['eta'] - steps_left(t) - d['crank'] < 1:
            return 'rw_stop', {}
        if t['late_told'] and not t['held'] and not t['recalled'] and t['arm'] == 'down' and t['eta'] > RW.RECALL_AT:
            return 'rw_ask', {}
        if t['arm'] == 'down' and t['flag'] != 'green' and not t['stopped'] and not t['left'] and not t['held']:
            return 'rw_flag', dict(color='green')
        if on:
            return 'rw_answer', dict(who=on['id'], answer=RW.PUSH_INDEX[on['id']]['best'][0])
        if not t['scanned']:
            return 'rw_scan', {}
        if t['left']:
            if t['bell'] is None and t['arm'] == 'up' and t['eta'] - steps_left(t) <= RW.LOWER_AT + 1:
                return 'rw_warn', {}
            k = t['left'][0]
            return 'rw_clear', dict(who=k, how=RW._crowd_of(k)['works'][0])
        if t['late_told'] and not t['held'] and not t['recalled'] and t['arm'] == 'down':
            return 'rw_ask', {}
        if t['held'] and t['arm'] == 'down':
            return 'rw_raise', {}
        if t['arm'] == 'up':
            crank = d['crank']           # the hand crank takes a minute longer: start a minute earlier
            if t['eta'] <= 1 + crank and not t['stopped']:
                return 'rw_stop', {}
            if t['eta'] > RW.LOWER_AT + 1 + crank or t['held']:
                return 'rw_wait', {}
            if t['bell'] is None:
                return 'rw_warn', {}
            return 'rw_lower', {}
        if t['flag'] != 'green' and not t['stopped']:
            return 'rw_flag', dict(color='green')
        return 'rw_wait', {}
    if not t['watched']:
        return 'rw_watch', {}
    if not t['_tail'] and 'tail' not in t['radioed']:
        return 'rw_radio', dict(what='tail')
    if t['_defect'] and 'defect' not in t['radioed']:
        return 'rw_radio', dict(what='defect')
    if t['arm'] == 'down' and not t['asked']:
        return 'rw_ask', {}
    if t['arm'] == 'down':
        return 'rw_raise', {}
    return 'rw_log', dict(remarks=sorted(RW._truth(t)))


def solve(j, tid):
    """See one job through by the book; returns the last result."""
    t = j.get(tid)
    if not t['known']:
        j.act('ask', task=tid)
    r = None
    for _ in range(120):
        settle(j)
        t = j.get(tid)
        if t['status'] in ('completed', 'cancelled'):
            return r
        d = j.c['ext']['data']
        if t['kind'] == 'shift':
            for e in RW.EQUIP_IDS:
                if e not in t['checked']:
                    r = j.act('rw_check', task=tid, item=e)
                    break
            else:
                f = t['found']
                if f and RW.FAULTS[f]['fix'] and not t['fixed']:
                    r = j.act('rw_fix', task=tid)
                elif f and set(RW.FAULTS[f]['forms']) - set(t['forms']):
                    r = j.act('rw_form', task=tid, form=sorted(set(RW.FAULTS[f]['forms']) - set(t['forms']))[0])
                else:
                    r = j.act('rw_sign', task=tid)
            continue
        if t['kind'] == 'patrol':
            todo = [p['id'] for p in t['needs']['points'] if p['id'] not in t['walked']]
            if todo:
                r = j.act('rw_walk', task=tid, point=todo[0])
                continue
            for p in t['needs']['points']:
                f = RW.FINDS[t['_finds'][p['id']]]
                if f['need'] and t['handled'].get(p['id']) != f['need']:
                    r = j.act('rw_handle', task=tid, point=p['id'], how=f['need'])
                    break
                miss = [k for k in f['forms'] if k not in t['pforms'].get(p['id'], [])]
                if miss:
                    r = j.act('rw_pform', task=tid, point=p['id'], form=miss[0])
                    break
            else:
                r = j.act('rw_patrol', task=tid)
            continue
        name, payload = train_move(t, d)
        r = j.act(name, task=tid, **payload)
    raise AssertionError(f'job {tid} did not finish: {j.get(tid)}')


def find(pick, days=range(2, 60), slots=range(1, 6)):
    """The first (day, slot) whose generated job passes `pick`."""
    return next((d, s) for d in days for s in slots if pick(RW.make_task(d, s, 1)))


def signed(j):
    j.c['ext']['data']['on_duty'] = True


class Base(unittest.TestCase):
    def setUp(self):
        if RW is None:
            raise unittest.SkipTest('railway is filtered out by MNL_CAREERS')
        self.j = Journey('railway')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, pick):
        day, slot = find(pick)
        j = Journey('railway', slot=slot, day=day)
        quiet(j)
        signed(j)
        return j

    def kind(self, kind, j=None):
        j = j or self.j
        return next(t for t in j.c['tasks'] if t['kind'] == kind and t['status'] not in ('completed', 'cancelled'))

    def ready(self, j, tid):
        """Hear the call and read it back right."""
        j.act('ask', task=tid)
        j.act('rw_readback', task=tid, option=j.get(tid)['_rb'])


class Spec(Base):
    def test_spec_shape(self):
        s = RW.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('railway', 'rw_', 'outdoor'))
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
        for k in s['no_tick'] + s['free_actions'] + tuple(RW.ACTIONS):
            self.assertTrue(k.startswith('rw_'), k)
        for post in s['employment']['postings']:
            for q in post['questions']:
                self.assertTrue(q in s['employment']['questions'] or q in ('mistake', 'conflict', 'weakness'), q)

    def test_many_awkward_people(self):
        """Owner rule: dozens of exasperating demands, not a token few."""
        self.assertGreaterEqual(len(RC.PUSH), 25)
        self.assertGreaterEqual(len(RC.CROWD), 10)
        self.assertGreaterEqual(len(RW.ODD), 24)
        self.assertGreaterEqual(len(RW.DESK), 15)
        self.assertGreaterEqual(len(RC.PUSH) + len(RC.CROWD) + len(RW.ODD) + len(RW.DESK) + len(RC.LOCALS) + len(RW.SITUATIONS), 80)
        for kind in ('charm', 'harass', 'demand', 'corner', 'bargain'):
            self.assertTrue(any(x['kind'] == kind for x in RW.ODD), kind)

    def test_safety_is_always_a_way(self):
        """Every pusher has a best answer that is not lifting the arm, and lifting it is never among the good ones."""
        for x in RC.PUSH:
            self.assertTrue(x['best'])
            self.assertNotIn('open', x['best'] + x['ok'])
        for x in RW.DESK:
            good = [o for o in x['options'] if o.get('good') is True]
            self.assertEqual(len(good), 1, x['id'])
        for x in RW.SITUATIONS:
            best = [o for o in x['options'] if o['quality'] == 'good']
            self.assertEqual(len(best), 1, x['id'])

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'nhiệm vụ', 'mô phỏng')
        blob = json.dumps([RW.DESK, RW.SITUATIONS, RW.REG_STORY, RW.INTRO, RW.SPEC['meta'], RC.PUSH, RC.CROWD, RW.ODD], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_registered(self):
        from game.content import CAREERS
        from game import employment as emp
        self.assertIn('railway', CAREERS)
        self.assertTrue(emp.required('railway'))


class Determinism(Base):
    def test_jobs_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 25):
            for slot in range(0, 7):
                a, b = RW.make_task(day, slot, 1), RW.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                self.assertEqual(json.loads(json.dumps(a['needs'])), a['needs'])
                self.assertEqual(make_task('railway', day, slot, 1)['id'], f'railway-{day:04d}-{slot:02d}')

    def test_the_board_lists_the_day_s_trains(self):
        for day in range(1, 15):
            board = RW.make_task(day, 0, 1)['needs']['board']
            trains = [RW.make_task(day, s, 1) for s in range(1, RW.daily_task_count(day))]
            self.assertEqual([b['code'] for b in board], [t['needs']['train']['code'] for t in trains if t['kind'] == 'train'])

    def test_first_day_is_gentle(self):
        kinds = [RW.make_task(1, s, 1)['kind'] for s in range(3)]
        self.assertEqual(kinds, ['shift', 'train', 'train'])
        t = RW.make_task(1, 1, 1)
        self.assertEqual(t['needs']['push'], [])
        self.assertFalse(t['_late'] or t['_second'] or t['_defect'])
        self.assertTrue(t['_tail'])
        self.assertIsNone(RW.make_task(1, 0, 1)['_fault'])

    def test_readback_has_one_right_answer(self):
        for day in range(1, 20):
            t = RW.make_task(day, 1, 1)
            if t['kind'] != 'train':
                continue
            tr = t['needs']['train']
            opts = t['needs']['readback']
            self.assertEqual(len(set(opts)), 3)
            self.assertIn(tr['code'], opts[t['_rb']])
            self.assertIn(tr['at'], opts[t['_rb']])


class Hidden(Base):
    def test_hidden_until_asked_and_seen(self):
        j = self.at(lambda t: t['kind'] == 'train' and t['needs']['crowd'] and t['needs']['push'] and not t['_tail'])
        tid = j.c['active_task']
        view = public_state(j.state)['careers']['railway']
        pv = next(t for t in view['tasks'] if t['id'] == tid)
        self.assertIsNone(pv['needs'])
        for k in ('_rb', '_late', '_second', '_tail', '_defect'):
            self.assertNotIn(k, pv)
        self.ready(j, tid)
        pv = next(t for t in public_state(j.state)['careers']['railway']['tasks'] if t['id'] == tid)
        self.assertIsNone(pv['needs']['crowd'])
        self.assertEqual(pv['left'], [])
        self.assertNotIn('push', pv['needs'])
        self.assertEqual(pv['pushers'], [])
        self.assertIsNone(pv['seen'])
        j.act('rw_scan', task=tid)
        pv = next(t for t in public_state(j.state)['careers']['railway']['tasks'] if t['id'] == tid)
        self.assertEqual([x['key'] for x in pv['left']], j.get(tid)['needs']['crowd'])
        self.assertNotIn('works', json.dumps(pv['left']))


class Train(Base):
    def test_a_full_first_day_by_the_book(self):
        j = self.j
        j.act('rw_intro')
        money = j.c['money']
        tids = [t['id'] for t in j.c['tasks']]
        self.assertEqual(len(tids), 3)
        for tid in tids:
            solve(j, tid)
            self.assertEqual(j.get(tid)['status'], 'completed')
            self.assertEqual(j.get(tid)['mistakes'], 0, j.get(tid).get('slips'))
        stars = [f['stars'] for f in j.c['feed'] if f.get('kind') == 'review']
        self.assertTrue(stars and min(stars) >= 4, stars)
        self.assertEqual(self.d['stats']['trains'], 2)
        self.assertEqual(self.d['stats']['safe'], 2)
        r = j.act('end_day')
        self.assertEqual(r['summary']['job']['salary'], j.c['job']['salary'])
        self.assertEqual(r['summary']['career']['trains'], 2)
        self.assertGreater(j.c['money'], money)
        validate_state(json.loads(json.dumps(j.state)))

    def test_a_fortnight_by_the_book_keeps_every_train_safe(self):
        j = self.j
        for day in range(1, 15):
            self.assertEqual(j.c['day'], day)
            settle(j)
            for t in [x for x in j.c['tasks'] if x['status'] not in ('completed', 'cancelled')]:
                solve(j, t['id'])
                self.assertFalse(j.get(t['id']).get('slips'), (day, t['id'], j.get(t['id']).get('slips')))
            validate_state(json.loads(json.dumps(j.state)))
            j.act('end_day')
            j.act('start_day')
        st = self.d['stats']
        self.assertGreaterEqual(st['trains'], 20)
        self.assertEqual(st['safe'], st['trains'])
        self.assertGreaterEqual(st['patrols'], 5)
        self.assertEqual(st['opened'], 0)

    def test_no_order_no_work(self):
        j = self.at(lambda t: t['kind'] == 'train')
        tid = j.c['active_task']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('rw_lower', task=tid)
        wrong = next(i for i in range(3) if i != j.get(tid)['_rb'])
        r = j.act('rw_readback', task=tid, option=wrong)
        self.assertFalse(r.get('correct', True))
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertIsNone(j.get(tid)['eta'])

    def test_the_shift_must_be_signed_first(self):
        j = self.j
        tid = next(t['id'] for t in j.c['tasks'] if t['kind'] == 'train')
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('rw_readback', task=tid, option=j.get(tid)['_rb'])

    def test_lowering_without_bell_or_look_is_unsafe(self):
        j = self.at(lambda t: t['kind'] == 'train' and t['needs']['crowd'])
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('rw_lower', task=tid)
        codes = {x['code'] for x in j.get(tid)['slips']}
        self.assertTrue({'no_bell', 'trapped'} <= codes)
        self.assertTrue(all(x['safety'] for x in j.get(tid)['slips'] if x['code'] in ('no_bell', 'trapped')))

    def test_lowering_early_is_safe_but_the_street_waits(self):
        j = self.at(lambda t: t['kind'] == 'train' and not t['needs']['crowd'] and len(t['needs']['push']) >= 4 and not t['_late'] and t['needs']['eta'] >= 7)
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('rw_scan', task=tid)
        j.act('rw_warn', task=tid)
        j.act('rw_lower', task=tid)
        t = j.get(tid)
        self.assertGreater(t['early'], 0)
        self.assertFalse(t.get('slips'))
        solve(j, tid)
        t = j.get(tid)
        self.assertFalse(t.get('slips'))
        self.assertGreaterEqual(sum(x['out'] not in (None, 'waited') for x in t['pushers']), 3)
        fb = RW.feedback(j.c, t)
        self.assertEqual(next(x for x in fb['criteria'] if x['key'] == 'timing')['score'], 4)

    def test_lifting_the_arm_for_someone_is_never_right(self):
        j = self.at(lambda t: t['kind'] == 'train' and t['needs']['push'] and t['needs']['push'][0][1] == 0 and not t['needs']['crowd'])
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('rw_scan', task=tid)
        for _ in range(8):
            if j.get(tid)['eta'] <= RW.LOWER_AT + 1:
                break
            j.act('rw_wait', task=tid)
        j.act('rw_warn', task=tid)
        j.act('rw_lower', task=tid)
        on = RW._talking(j.get(tid))
        self.assertIsNotNone(on)
        with self.assertRaises(GameError):
            j.act('rw_raise', task=tid)          # someone is talking: answer first
        before = self.j.c['ext']['data']['odd']['conduct']['points']
        r = j.act('rw_answer', task=tid, who=on['id'], answer='open')
        self.assertFalse(r['correct'])
        t = j.get(tid)
        self.assertTrue(any(x['code'] == 'opened' and x['safety'] for x in t['slips']))
        self.assertEqual(j.c['ext']['data']['odd']['conduct']['points'], 2)
        self.assertEqual(before, 0)
        self.assertEqual(j.c['ext']['data']['stats']['opened'], 1)

    def test_the_train_arriving_on_an_open_crossing_is_the_worst(self):
        j = self.at(lambda t: t['kind'] == 'train' and not t['_late'])
        tid = j.c['active_task']
        self.ready(j, tid)
        for _ in range(12):
            if j.get(tid)['passed']:
                break
            j.act('rw_wait', task=tid)
        t = j.get(tid)
        self.assertTrue(t['passed'])
        self.assertTrue(any(x['code'] == 'unprotected' and x['safety'] for x in t['slips']))
        solve(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        paid = [r for r in j.c['ops']['finance']['ledger'] if r.get('ref') == tid]
        self.assertEqual(paid, [])                 # no bonus for an unsafe train

    def test_stopping_the_train_is_always_allowed_and_never_a_mistake(self):
        j = self.at(lambda t: t['kind'] == 'train' and 'drunk' in t['needs']['crowd'] and not t['_late'])
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('rw_scan', task=tid)
        j.act('rw_stop', task=tid)
        solve(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))
        self.assertIn('stopped', t['remarks'])
        self.assertGreaterEqual(t['late_min'], RW.HOLD_STOP)

    def test_a_sneaker_must_be_pulled_back_or_the_train_stopped(self):
        j = self.at(lambda t: t['kind'] == 'train' and any(RW.PUSH_INDEX[p]['sneaky'] for p, _ in t['needs']['push']))
        tid = j.c['active_task']
        t = j.get(tid)
        t['left'].append('sneak:' + next(p for p, _ in t['needs']['push'] if RW.PUSH_INDEX[p]['sneaky']))
        t['sneaks'].append(t['left'][-1][6:])
        self.ready(j, tid)
        with self.assertRaises(GameError):
            j.act('rw_flag', task=tid, color='green')
        solve(j, tid)
        t = j.get(tid)
        self.assertIn('violator', t['remarks'])

    def test_a_delay_held_at_the_station_lets_the_street_through(self):
        j = self.at(lambda t: t['kind'] == 'train' and t['_late'] and not t['needs']['crowd'])
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('rw_scan', task=tid)
        while j.get(tid)['eta'] > RW.LOWER_AT + 1:
            j.act('rw_wait', task=tid)
        j.act('rw_warn', task=tid)
        j.act('rw_lower', task=tid)
        for _ in range(6):
            t = j.get(tid)
            if t['late_told']:
                break
            on = RW._talking(t)
            j.act('rw_answer', task=tid, who=on['id'], answer=RW.PUSH_INDEX[on['id']]['best'][0]) if on else j.act('rw_wait', task=tid)
        t = j.get(tid)
        self.assertTrue(t['late_told'])
        self.assertGreater(t['eta'], RW.LOWER_AT)
        j.act('rw_ask', task=tid)
        j.act('rw_raise', task=tid)
        self.assertFalse(j.get(tid).get('slips'))
        self.assertEqual(j.get(tid)['reopened'], 1)
        solve(j, tid)
        t = j.get(tid)
        self.assertFalse(t.get('slips'))
        self.assertTrue(t['recalled'])
        self.assertIn('late', t['remarks'])

    def test_opening_in_a_delay_without_the_station_is_unsafe(self):
        j = self.at(lambda t: t['kind'] == 'train' and t['_late'] and not t['needs']['crowd'])
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('rw_scan', task=tid)
        j.act('rw_warn', task=tid)
        j.act('rw_lower', task=tid)
        for _ in range(6):
            t = j.get(tid)
            if t['late_told']:
                break
            on = RW._talking(t)
            j.act('rw_answer', task=tid, who=on['id'], answer='hold') if on else j.act('rw_wait', task=tid)
        while RW._talking(j.get(tid)):
            on = RW._talking(j.get(tid))
            j.act('rw_answer', task=tid, who=on['id'], answer='hold')
        j.act('rw_raise', task=tid)
        self.assertTrue(any(x['code'] == 'open_due' and x['safety'] for x in j.get(tid)['slips']))

    def test_a_second_train_needs_the_station_s_word(self):
        pick = lambda t: t['kind'] == 'train' and t['_second'] and not t['_late']
        j = self.at(pick)
        tid = j.c['active_task']
        t = j.get(tid)
        for _ in range(80):
            t = j.get(tid)
            if t['passed'] and t['watched'] and (t['_tail'] or 'tail' in t['radioed']) and (not t['_defect'] or 'defect' in t['radioed']):
                break
            name, payload = train_move(t, j.c['ext']['data'])
            if name == 'rw_readback' and not t['known']:
                j.act('ask', task=tid)
            j.act(name, task=tid, **payload)
        j.act('rw_raise', task=tid)
        self.assertTrue(any(x['code'] == 'second' and x['safety'] for x in j.get(tid)['slips']))
        # The careful way: ask, the second train goes by, ask again, then open.
        j2 = self.at(pick)
        solve(j2, j2.c['active_task'])
        t2 = j2.get(j2.c['active_task']) if j2.c['active_task'] else j2.get(tid)
        self.assertFalse(t2.get('slips'))
        self.assertIn('second', t2['remarks'])

    def test_a_missing_tail_lamp_must_be_radioed(self):
        j = self.at(lambda t: t['kind'] == 'train' and not t['_tail'] and not t['_second'] and not t['_late'])
        tid = j.c['active_task']
        for _ in range(80):
            t = j.get(tid)
            if t['watched']:
                break
            name, payload = train_move(t, j.c['ext']['data'])
            if not t['known']:
                j.act('ask', task=tid)
            j.act(name, task=tid, **payload)
        with self.assertRaises(GameError):
            j.act('rw_radio', task=tid, what='defect') if not j.get(tid)['_defect'] else j.act('rw_radio', task=tid, what='bogus')
        j.act('rw_ask', task=tid)
        j.act('rw_raise', task=tid)
        j.act('rw_log', task=tid, remarks=sorted(RW._truth(j.get(tid))))
        self.assertTrue(any(x['code'] == 'tail_unreported' and x['safety'] for x in j.get(tid)['slips']))

    def test_the_log_must_be_true(self):
        j = self.at(lambda t: t['kind'] == 'train' and not t['_late'])
        tid = j.c['active_task']
        for _ in range(80):
            t = j.get(tid)
            if t['passed'] and t['arm'] == 'up':
                break
            name, payload = train_move(t, j.c['ext']['data'])
            if not t['known']:
                j.act('ask', task=tid)
            j.act(name, task=tid, **payload)
        with self.assertRaises(GameError):
            j.act('rw_log', task=tid, remarks=['made_up'])
        truth = RW._truth(j.get(tid))
        wrong = sorted(truth ^ {'ontime', 'late'})
        j.act('rw_log', task=tid, remarks=wrong)
        self.assertTrue(any(x['code'] == 'log' for x in j.get(tid)['slips']))

    def test_people_decide_by_themselves_and_always_the_same(self):
        px = RC.PUSH_INDEX['grab']
        from game.careers import street_folk as folk
        outs = set()
        for i in range(60):
            tr = folk.traits(f'seed-{i}', 'genz')
            for ans in ('hold', 'explain', 'detour', 'calm', 'report'):
                a = RW._push_react(tr, px, ans, 0, 3)
                self.assertEqual(a, RW._push_react(tr, px, ans, 0, 3))
                outs.add(a)
        self.assertTrue({'ok', 'sulk', 'again'} <= outs)

    def test_tired_keepers_wake_themselves_first(self):
        j = self.at(lambda t: t['kind'] == 'train')
        tid = j.c['active_task']
        j.c['ext']['data']['odd']['fatigue'] = ao.TIRED
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('rw_readback', task=tid, option=j.get(tid)['_rb'])
        j.act('rw_wake', task=tid)
        j.act('rw_readback', task=tid, option=j.get(tid)['_rb'])
        self.assertTrue(j.get(tid)['rb'])


class Shift(Base):
    def test_signing_blind_is_a_slip(self):
        j = self.j
        tid = self.kind('shift')['id']
        j.act('rw_sign', task=tid)
        self.assertTrue(any(x['code'] == 'unchecked' for x in j.get(tid)['slips']))
        self.assertTrue(j.c['ext']['data']['on_duty'])

    def test_a_dangerous_fault_must_reach_the_station(self):
        day, slot = find(lambda t: t['kind'] == 'shift' and t['_fault'] == 'motor', slots=[0])
        j = Journey('railway', slot=0, day=day)
        quiet(j)
        tid = j.c['active_task']
        for e in RW.EQUIP_IDS:
            j.act('rw_check', task=tid, item=e)
        self.assertEqual(j.get(tid)['found'], 'motor')
        j.act('rw_form', task=tid, form='phieu')
        j.act('rw_sign', task=tid)
        codes = {x['code'] for x in j.get(tid)['slips']}
        self.assertIn('no_station', codes)
        self.assertIn('unfixed', codes)
        self.assertTrue(j.c['ext']['data']['jam'])

    def test_the_hand_crank_makes_every_close_slower(self):
        day, slot = find(lambda t: t['kind'] == 'shift' and t['_fault'] == 'motor', slots=[0])
        j = Journey('railway', slot=0, day=day)
        quiet(j)
        solve(j, j.c['active_task'])
        self.assertTrue(j.c['ext']['data']['crank'])
        self.assertFalse(j.get(f'railway-{day:04d}-00').get('slips'))


class Patrol(Base):
    def test_a_danger_left_unprotected_is_unsafe(self):
        j = self.at(lambda t: t['kind'] == 'patrol' and any(RW.FINDS[f]['danger'] for f in t['_finds'].values()))
        tid = j.c['active_task']
        for p in j.get(tid)['needs']['points']:
            j.act('rw_walk', task=tid, point=p['id'])
        j.act('rw_patrol', task=tid)
        codes = {x['code'] for x in j.get(tid)['slips']}
        self.assertIn('no_alarm', codes)
        self.assertTrue(cq_safety(j.get(tid)))

    def test_by_the_book(self):
        j = self.at(lambda t: t['kind'] == 'patrol' and any(RW.FINDS[f]['danger'] for f in t['_finds'].values()))
        tid = j.c['active_task']
        solve(j, tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t.get('slips'))

    def test_skipping_a_point_is_a_slip_and_caution_never_is(self):
        j = self.at(lambda t: t['kind'] == 'patrol')
        tid = j.c['active_task']
        pts = j.get(tid)['needs']['points']
        j.act('rw_walk', task=tid, point=pts[0]['id'])
        j.act('rw_handle', task=tid, point=pts[0]['id'], how='protect')     # over-careful: fine
        j.act('rw_pform', task=tid, point=pts[0]['id'], form='khan')
        j.act('rw_patrol', task=tid)
        codes = {x['code'] for x in j.get(tid)['slips']}
        self.assertIn('skipped', codes)
        with self.assertRaises(GameError):
            Journey('railway').act('rw_walk', task=tid, point='p9')


def cq_safety(t):
    return any(x['safety'] for x in t.get('slips') or [])


class Around(Base):
    def test_every_surprise_option_is_playable(self):
        for x in RW.DESK:
            for o in x['options']:
                j = Journey('railway')
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('rw_check', task=j.c['active_task'], item='bell')
                r = j.act('rw_desk', option=o['id'])
                self.assertTrue(r['message'])
                self.assertIsNone(j.c['ext']['data']['desk']['ev'])
                validate_state(json.loads(json.dumps(j.state)))

    def test_every_encounter_can_be_answered_every_way(self):
        for x in RW.ODD:
            for say in ([best_answer(x)], [dict(tone='soft', say=['yes'], to='self', **({'n': x['ask']} if x['kind'] == 'bargain' else {}))]):
                j = Journey('railway')
                odd = ao.ensure(j.c['ext']['data'])
                odd['ev'] = dict(id='odd-t', script=x['id'], day=j.c['day'], at='between', said=[])
                for _ in range(ao.MAX_ROUNDS):
                    if odd['ev'] is None:
                        break
                    r = j.act('rw_odd', **say[0])
                    odd = j.c['ext']['data']['odd']
                self.assertIsNone(j.c['ext']['data']['odd']['ev'], x['id'])
                self.assertTrue(r['message'])
                out = j.c['ext']['data']['odd']['last']['outcome']
                for word in ('tổ bay', 'hãng', 'đình chỉ bay', 'chuyến bay', 'phòng an toàn'):
                    self.assertNotIn(word, out, x['id'])
                validate_state(json.loads(json.dumps(j.state)))

    def test_giving_in_is_never_rewarded(self):
        for x in RW.ODD:
            if x['kind'] in ('charm', 'corner'):
                j = Journey('railway')
                odd = ao.ensure(j.c['ext']['data'])
                odd['ev'] = dict(id='odd-t', script=x['id'], day=j.c['day'], at='between', said=[])
                money = j.c['money']
                j.act('rw_odd', tone='soft', say=['yes'], to='self')
                self.assertGreater(j.c['ext']['data']['odd']['conduct']['points'], 0, x['id'])
                self.assertLessEqual(j.c['money'], money)

    def test_situations_are_playable(self):
        j = self.j
        for x in RW.SPEC['situations']:
            for opt in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_hours_are_the_keeper_s_day(self):
        from game import dayclock as dc
        self.assertEqual(dc.hours(self.j.c, 'railway'), RW.HOURS)


class Saves(Base):
    def test_forged_needs_are_rejected(self):
        for key, value in (('_rb', 2), ('_tail', False), ('_late', 99)):
            s = copy.deepcopy(self.j.state)
            t = next(x for x in s['careers']['railway']['tasks'] if x['kind'] == 'train')
            t[key] = value if t[key] != value else (0 if key == '_rb' else value)
            if t[key] == RW.make_task(t['day'], int(t['id'][-2:]), 1)[key]:
                continue
            with self.assertRaises(GameError, msg=key):
                validate_state(s)
        s = copy.deepcopy(self.j.state)
        t = next(x for x in s['careers']['railway']['tasks'] if x['kind'] == 'train')
        t['needs']['eta'] = 30
        with self.assertRaises(GameError):
            validate_state(s)

    def test_broken_task_fields_are_rejected(self):
        j = self.at(lambda t: t['kind'] == 'train' and t['needs']['push'])
        tid = j.c['active_task']
        self.ready(j, tid)
        for key, value in (('arm', 'sideways'), ('eta', 'soon'), ('left', ['ghost']), ('flag', 'blue'), ('pushers', []),
                           ('radioed', ['tail', 'tail']), ('remarks', ['lies']), ('rb', 'yes'), ('second', 'maybe'), ('progress', {'cow': 9})):
            s = copy.deepcopy(j.state)
            next(x for x in s['careers']['railway']['tasks'] if x['id'] == tid)[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_broken_data_is_rejected(self):
        for path, value in ((('stats', 'trains'), -2), (('intro',), 'yes'), (('regulars',), {'9': {'visits': 1}}), (('log',), [dict(day=1)]),
                            (('odd', 'fatigue'), 99)):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['railway']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_mid_train_save_round_trip(self):
        j = self.at(lambda t: t['kind'] == 'train' and t['needs']['push'] and t['needs']['crowd'])
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('rw_scan', task=tid)
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        j.state = s
        solve(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        validate_state(json.loads(json.dumps(j.state)))

    def test_old_save_without_the_crossing_gains_it_and_nothing_else_changes(self):
        s = new_state()
        old = copy.deepcopy(s)
        old['careers'].pop('railway')
        a, b = migrate_state(old), migrate_state(copy.deepcopy(s))
        for cid in b['careers']:
            if cid != 'railway':
                self.assertEqual(a['careers'][cid], b['careers'][cid], cid)
        validate_state(a)
        self.assertEqual(a['careers']['railway']['job']['status'], 'none')   # nobody is hired without applying

    def test_story_players_past_chapter_four_find_the_crossing_open(self):
        from game import journey as jr
        j = jr.initial(True, 5)
        j['chapter'] = 5
        j['unlocked'] = [c for n in range(1, 6) for c in jr.CH_UNLOCKS[n] if c != 'railway']
        old = list(j['unlocked'])
        jr.upgrade(j)
        self.assertEqual(j['unlocked'][:len(old)], old)
        self.assertIn('railway', j['unlocked'])
        young = jr.initial(True, 5)
        jr.upgrade(young)
        self.assertNotIn('railway', young['unlocked'])

    def test_public_view_is_json(self):
        view = public_state(self.j.state)['careers']['railway']
        json.dumps(view)
        for k in ('board', 'mod', 'desk', 'odd', 'intro', 'on_duty'):
            self.assertIn(k, view['data'])

    def test_yesterday_s_train_is_closed_and_today_is_full(self):
        j = self.j
        solve(j, j.c['active_task'])
        tid = next(t['id'] for t in j.c['tasks'] if t['kind'] == 'train' and t['status'] != 'completed')
        self.ready(j, tid)
        j.act('end_day')
        j.act('start_day')
        self.assertEqual(j.get(tid)['status'], 'cancelled')
        today = [t for t in j.c['tasks'] if t['day'] == 2]
        self.assertEqual(len(today), RW.daily_task_count(2))
        self.assertEqual(sorted(int(t['id'][-2:]) for t in today), list(range(RW.daily_task_count(2))))
        validate_state(json.loads(json.dumps(j.state)))


if __name__ == '__main__':
    unittest.main()
