"""Người gác hải đăng (plugin career lighthouse): the morning round and its faults, the weather report and the warning,
the evening light (on time, its characteristic, the fog horn, a truthful log), the sea (relay at the right priority
and position, a buoy for someone close, never going out alone; captains deciding by their traits), visitors (papers,
the rules, shelter for anyone in danger, nobody in the lamp room), the supply boat (dip the tank, sign the litres
measured, the captain's basket haggled), life on the rock, surprises, encounters, situations, determinism, hidden
information and saves."""
import copy
import json
import unittest

from tests.helpers import Journey
from game.careers import kit, PLUGINS
from game.careers import air_odd as ao
from game.content import make_task
from game.engine import GameError, migrate_state, new_state, public_state, validate_state

HD = PLUGINS.get('lighthouse')
LC = __import__('game.careers.lighthouse_content', fromlist=['x']) if HD else None


def best_answer(x):
    k = x['kind']
    if k == 'bargain':
        return dict(tone='firm', say=['rule', 'alt'], to='self' if x['rank'] == 'kin' else 'company', n=x['limit'])
    say = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'corner': ['speak', 'rule'], 'demand': ['rule', 'alt']}[k]
    to = 'self' if x['rank'] == 'kin' else 'company' if k in ('charm', 'harass', 'corner') else 'crew'
    return dict(tone='firm', say=say, to=to)


def settle(j):
    """Decide an open surprise and answer an open encounter the careful way."""
    for _ in range(4 * ao.MAX_ROUNDS):
        d = j.c['ext']['data']
        if d['desk']['ev']:
            x = kit.desk_script(HD.DESK, d['desk']['ev']['script'])
            good = next((o['id'] for o in x['options'] if o.get('good') is True), x['default'])
            j.act('hd_desk', option=good)
            continue
        ev = d['odd']['ev']
        if not ev:
            return
        j.act('hd_odd', **best_answer(ao.script(HD.ODD, ev['script'])))


def quiet(j):
    d = j.c['ext']['data']
    ao.ensure(d)
    d['odd'].update(day=j.c['day'], plan=[], fired=0, ev=None)
    d['desk'].update(day=j.c['day'], plan=[], fired=0, ev=None)


def on_duty(j):
    j.c['ext']['data']['on_duty'] = True


def move(j, t):
    """The careful keeper's next move on a job (from the full task: the test may look at hidden keys)."""
    k = t['kind']
    d = j.c['ext']['data']
    if k == 'dawn':
        if t['off'] is None:
            return 'hd_off', dict(option=t['_off'][0])
        for e in HD.EQUIP_IDS:
            if e not in t['checked']:
                return 'hd_check', dict(item=e)
        if t['cleaned'] is None:
            return 'hd_clean', dict(how='lock')
        if t['fuel_log'] is None:
            return 'hd_fuel', dict(litres=t['_fuel'])
        f = t['found']
        if f and HD.FAULTS[f]['fix'] and not t['fixed']:
            return 'hd_fix', {}
        if f and set(HD.FAULTS[f]['forms']) - set(t['forms']):
            return 'hd_form', dict(form=sorted(set(HD.FAULTS[f]['forms']) - set(t['forms']))[0])
        return 'hd_sign', {}
    if k == 'weather':
        for i in HD.INSTRUMENTS:
            if i not in t['read']:
                return 'hd_read', dict(what=i)
        sk = t['_sky']
        if t['report'] is None:
            return 'hd_report', dict(wind=sk['wind'], sea=sk['sea'], vis=sk['vis'], baro=sk['baro'])
        if sk['warn'] and not t['warned']:
            return 'hd_warn', {}
        return 'hd_wdone', {}
    if k == 'dusk':
        if t['lit'] is None:
            if d['odd']['fatigue'] >= ao.TIRED and not t['awake']:
                return 'hd_wake', {}
            return 'hd_light', dict(option=t['_light'][0])
        if not t['counted']:
            return 'hd_count', {}
        if t['_slow'] and 'char' not in t['radioed']:
            return 'hd_radio', dict(what='char')
        if t['needs']['fog'] and not t['horn']:
            return 'hd_horn', {}
        if t['needs']['fog'] and t['_horn_bad'] and 'horn' not in t['radioed']:
            return 'hd_radio', dict(what='horn')
        return 'hd_log', dict(remarks=sorted(HD.truth_dusk(t, t['day'])))
    if k == 'sea':
        x = HD.SEA[t['_case']]
        if not t['looked']:
            return 'hd_look', {}
        if x['talk'] and t['talk_out'] in (None, 'again'):
            return 'hd_vhf', dict(say=['forecast', 'shelter'] if x['talk'] == 'storm' else ['law'])
        if x['talk'] == 'reef' and t['talk_out'] == 'silent' and 'lamp' not in t['did']:
            return 'hd_act', dict(what='lamp')
        for a in x['need']:
            if a in ('buoy', 'horn') and a not in t['did']:
                return 'hd_act', dict(what=a)
        want = HD.needs_relay(t)
        if want and t['relay'] is None:
            return 'hd_relay', dict(kind=want, bearing=t['_bearing'], persons=t['_persons'])
        if 'track' in x['need'] and 'track' not in t['did']:
            return 'hd_act', dict(what='track')
        return 'hd_sdone', {}
    if k == 'visitor':
        v = HD.VISITOR[t['_v']]
        if not t['papers']:
            return 'hd_papers', {}
        if t['out'] in (None, 'again'):
            return 'hd_answer', dict(answer=v['best'][0])
        if t['sneak'] and not t['stopped']:
            return 'hd_stop', {}
        return 'hd_vdone', {}
    # supply
    for w in ('before', 'after'):
        if w not in t['dipped']:
            return 'hd_dip', dict(when=w)
    for g in HD.GOODS_IDS:
        if g not in t['seen']:
            return 'hd_goods', dict(item=g)
    bad = sorted(g for g, s in t['_states'].items() if s != 'ok' and g not in t['noted'])
    if bad:
        return 'hd_note', dict(item=bad[0])
    if t['buy'] is None:
        return 'hd_skipbuy', {}
    return 'hd_ssign', dict(litres=t['_after'] - t['_before'])


def solve(j, tid):
    t = j.get(tid)
    if not t['known']:
        j.act('ask', task=tid)
    r = None
    for _ in range(80):
        settle(j)
        t = j.get(tid)
        if t['status'] in ('completed', 'cancelled'):
            return r
        name, payload = move(j, t)
        r = j.act(name, task=tid, **payload)
    raise AssertionError(f'job {tid} did not finish: {j.get(tid)}')


def find(pick, days=range(2, 80), slots=range(0, 7)):
    return next((d, s) for d in days for s in slots if pick(HD.make_task(d, s, 1)))


class Base(unittest.TestCase):
    def setUp(self):
        if HD is None:
            raise unittest.SkipTest('lighthouse is filtered out by MNL_CAREERS')
        self.j = Journey('lighthouse')

    @property
    def d(self):
        return self.j.c['ext']['data']

    def at(self, pick):
        day, slot = find(pick)
        j = Journey('lighthouse', slot=slot, day=day)
        quiet(j)
        on_duty(j)
        return j

    def ready(self, j, tid):
        if not j.get(tid)['known']:
            j.act('ask', task=tid)


class Spec(Base):
    def test_spec_shape(self):
        s = HD.SPEC
        self.assertEqual((s['id'], s['prefix'], s['category']), ('lighthouse', 'hd_', 'outdoor'))
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
        for k in s['no_tick'] + s['free_actions'] + tuple(HD.ACTIONS):
            self.assertTrue(k.startswith('hd_'), k)
        for post in s['employment']['postings']:
            for q in post['questions']:
                self.assertTrue(q in s['employment']['questions'] or q in ('mistake', 'conflict', 'weakness'), q)

    def test_many_awkward_people(self):
        """Owner rule: dozens of exasperating demands, not a token few."""
        self.assertGreaterEqual(len(LC.VISITORS), 15)
        self.assertGreaterEqual(len(HD.ODD), 30)
        self.assertGreaterEqual(len(HD.DESK), 15)
        self.assertGreaterEqual(len(LC.SEA), 7)
        self.assertGreaterEqual(len(LC.VISITORS) + len(HD.ODD) + len(HD.DESK) + len(LC.SEA) + len(HD.SITUATIONS) + len(LC.CALLS), 80)
        for kind in ('charm', 'harass', 'demand', 'corner', 'bargain'):
            self.assertTrue(any(x['kind'] == kind for x in HD.ODD), kind)

    def test_safety_is_always_a_way(self):
        """Giving in is never a good answer; anyone in danger is always sheltered; every surprise has one good choice."""
        for v in LC.VISITORS:
            self.assertTrue(v['best'])
            self.assertNotIn('give', v['best'] + v['ok'], v['id'])
            if v['emergency']:
                self.assertEqual(v['best'], ['shelter'], v['id'])
        for x in HD.DESK:
            self.assertEqual(len([o for o in x['options'] if o.get('good') is True]), 1, x['id'])
        for x in HD.SITUATIONS:
            self.assertEqual(len([o for o in x['options'] if o['quality'] == 'good']), 1, x['id'])
        for x in LC.SEA.values():
            self.assertNotIn('boat', x['need'])
            self.assertNotIn('swim', x['need'])

    def test_no_meta_text(self):
        banned = ('NPC', 'trong game', 'người chơi', 'nhiệm vụ', 'mô phỏng')
        blob = json.dumps([HD.DESK, HD.SITUATIONS, LC.REG_STORY, LC.INTRO, HD.SPEC['meta'], LC.VISITORS, LC.SEA, HD.ODD], ensure_ascii=False)
        for b in banned:
            self.assertNotIn(b, blob)

    def test_registered(self):
        from game.content import CAREERS
        from game import employment as emp
        self.assertIn('lighthouse', CAREERS)
        self.assertTrue(emp.required('lighthouse'))


class Determinism(Base):
    def test_jobs_are_pure_functions_of_day_and_slot(self):
        for day in range(1, 30):
            for slot in range(0, 7):
                a, b = HD.make_task(day, slot, 1), HD.make_task(day, slot, 99)
                a.pop('created_turn'), b.pop('created_turn')
                self.assertEqual(a, b)
                self.assertEqual(json.loads(json.dumps(a)), a)
                self.assertEqual(make_task('lighthouse', day, slot, 1)['id'], f'lighthouse-{day:04d}-{slot:02d}')

    def test_the_day_runs_dawn_to_dusk(self):
        for day in range(1, 40):
            plan = HD.plan_of(day)
            self.assertEqual((plan[0], plan[1], plan[-1]), ('dawn', 'weather', 'dusk'))
            self.assertEqual('supply' in plan, HD.supply_day(day))

    def test_first_day_is_gentle(self):
        self.assertEqual([HD.make_task(1, s, 1)['kind'] for s in range(4)], ['dawn', 'weather', 'visitor', 'dusk'])
        self.assertIsNone(HD.make_task(1, 0, 1)['_fault'])
        self.assertEqual(HD.make_task(1, 2, 1)['_v'], 'tour')
        self.assertEqual(HD.make_task(2, 2, 1)['_case'], 'drift')

    def test_the_evening_knows_the_morning_s_fault(self):
        for day in range(2, 40):
            dawn, dusk = HD.make_task(day, 0, 1), HD.make_task(day, HD.daily_task_count(day) - 1, 1)
            self.assertEqual(dusk['_slow'], dawn['_fault'] == 'motor')
            self.assertEqual(dusk['_horn_bad'], dawn['_fault'] == 'horn')

    def test_weather_needs_a_warning_from_force_six(self):
        for day in range(1, 60):
            sk = HD.sky(day)
            lo, hi = HD.BEAUFORT[sk['wind']][1:]
            self.assertTrue(lo <= sk['ms'] <= hi)
            self.assertEqual(sk['warn'], sk['wind'] >= 6 or sk['baro'] == 'fast')


class Hidden(Base):
    def test_visitor_and_sea_hidden_until_asked(self):
        j = self.at(lambda t: t['kind'] == 'sea' and t['_case'] == 'flare')
        tid = j.c['active_task']
        pv = next(t for t in public_state(j.state)['careers']['lighthouse']['tasks'] if t['id'] == tid)
        self.assertIsNone(pv['needs'])
        for k in ('_case', '_bearing', '_persons', '_boat', '_answers'):
            self.assertNotIn(k, pv)
        j.act('ask', task=tid)
        pv = next(t for t in public_state(j.state)['careers']['lighthouse']['tasks'] if t['id'] == tid)
        self.assertIsNone(pv['seen'])
        j.act('hd_look', task=tid)
        pv = next(t for t in public_state(j.state)['careers']['lighthouse']['tasks'] if t['id'] == tid)
        self.assertIn(j.get(tid)['_bearing'], pv['seen'])

    def test_weather_readings_show_only_once_read(self):
        tid = next(t['id'] for t in self.j.c['tasks'] if t['kind'] == 'weather')
        pv = next(t for t in public_state(self.j.state)['careers']['lighthouse']['tasks'] if t['id'] == tid)
        self.assertEqual(pv['seen'], {})
        self.assertNotIn('_sky', pv)


class Days(Base):
    def test_a_full_first_day_by_the_book(self):
        j = self.j
        j.act('hd_intro')
        tids = [t['id'] for t in j.c['tasks']]
        self.assertEqual(len(tids), 4)
        for tid in tids:
            solve(j, tid)
            self.assertEqual(j.get(tid)['status'], 'completed')
            self.assertEqual(j.get(tid)['mistakes'], 0, j.get(tid).get('slips'))
        stars = [f['stars'] for f in j.c['feed'] if f.get('kind') == 'review']
        self.assertTrue(stars and min(stars) >= 4, stars)
        self.assertEqual(self.d['stats']['lit'], 1)
        r = j.act('end_day')
        self.assertEqual(r['summary']['job']['salary'], j.c['job']['salary'])
        self.assertEqual(r['summary']['career']['lit'], 1)

    def test_three_weeks_by_the_book_keep_everyone_safe(self):
        j = self.j
        j.act('hd_intro')
        for _ in range(21):
            for t in list(j.c['tasks']):
                if t['day'] == j.c['day'] and t['status'] not in ('completed', 'cancelled'):
                    solve(j, t['id'])
            for t in j.c['tasks']:
                if t['day'] == j.c['day']:
                    self.assertFalse(any(x['safety'] for x in t.get('slips') or []), (t['id'], t.get('slips')))
            settle(j)
            j.act('end_day')
            validate_state(json.loads(json.dumps(j.state)))
            j.act('start_day')
            settle(j)
        self.assertGreaterEqual(self.d['stats']['supplies'], 2)


class Rules(Base):
    def test_the_morning_round_must_be_signed_first(self):
        tid = next(t['id'] for t in self.j.c['tasks'] if t['kind'] == 'dusk')
        with self.assertRaises(GameError):
            self.j.act('hd_light', task=tid, option=0)

    def test_putting_the_light_out_in_the_dark_is_unsafe(self):
        t = self.j.task
        self.j.act('hd_off', task=t['id'], option=t['_off'][2])
        self.assertTrue(any(x['code'] == 'off_early' and x['safety'] for x in self.j.get(t['id'])['slips']))

    def test_cleaning_a_turning_lens_is_unsafe(self):
        t = self.j.task
        self.j.act('hd_check', task=t['id'], item='lens')
        self.j.act('hd_clean', task=t['id'], how='quick')
        self.assertTrue(any(x['code'] == 'no_lockout' and x['safety'] for x in self.j.get(t['id'])['slips']))

    def test_a_dangerous_fault_must_reach_the_station(self):
        j = self.at(lambda t: t['kind'] == 'dawn' and t['_fault'] == 'motor')
        tid = j.c['active_task']
        for e in HD.EQUIP_IDS:
            j.act('hd_check', task=tid, item=e)
        j.act('hd_clean', task=tid, how='lock')
        j.act('hd_form', task=tid, form='phieu')
        j.act('hd_sign', task=tid)
        self.assertTrue(any(x['code'] == 'no_station' and x['safety'] for x in j.get(tid)['slips']))

    def test_the_fuel_log_must_match_the_tank(self):
        t = self.j.task
        self.j.act('hd_check', task=t['id'], item='gen')
        self.j.act('hd_fuel', task=t['id'], litres=t['_fuel'] + 40)
        self.j.act('hd_sign', task=t['id'])
        self.assertTrue(any(x['code'] == 'fuel_log' for x in self.j.get(t['id'])['slips']))

    def test_a_slow_light_must_be_radioed(self):
        j = self.at(lambda t: t['kind'] == 'dusk' and t['_slow'])
        tid = j.c['active_task']
        j.act('hd_light', task=tid, option=j.get(tid)['_light'][0])
        r = j.act('hd_count', task=tid)
        self.assertIn('19 giây', r['message'])
        j.act('hd_log', task=tid, remarks=sorted(HD.truth_dusk(j.get(tid), j.get(tid)['day'])))
        self.assertTrue(any(x['code'] == 'char_unreported' and x['safety'] for x in j.get(tid)['slips']))

    def test_fog_needs_the_horn(self):
        j = self.at(lambda t: t['kind'] == 'dusk' and t['needs']['fog'] and not t['_horn_bad'] and not t['_slow'])
        tid = j.c['active_task']
        j.act('hd_light', task=tid, option=j.get(tid)['_light'][0])
        j.act('hd_count', task=tid)
        j.act('hd_log', task=tid, remarks=sorted(HD.truth_dusk(j.get(tid), j.get(tid)['day'])))
        self.assertTrue(any(x['code'] == 'no_horn' for x in j.get(tid)['slips']))

    def test_the_evening_log_must_be_true(self):
        j = self.at(lambda t: t['kind'] == 'dusk' and not t['_slow'] and not t['needs']['fog'])
        tid = j.c['active_task']
        j.act('hd_light', task=tid, option=j.get(tid)['_light'][0])
        j.act('hd_count', task=tid)
        j.act('hd_log', task=tid, remarks=['char_bad'])
        self.assertTrue(any(x['code'] == 'log' for x in j.get(tid)['slips']))

    def test_a_storm_must_be_warned(self):
        j = self.at(lambda t: t['kind'] == 'weather' and t['_sky']['warn'])
        tid = j.c['active_task']
        sk = j.get(tid)['_sky']
        for i in HD.INSTRUMENTS:
            j.act('hd_read', task=tid, what=i)
        j.act('hd_report', task=tid, wind=sk['wind'], sea=sk['sea'], vis=sk['vis'], baro=sk['baro'])
        j.act('hd_wdone', task=tid)
        self.assertTrue(any(x['code'] == 'no_warn' and x['safety'] for x in j.get(tid)['slips']))

    def test_warning_in_calm_weather_is_never_a_mistake(self):
        tid = next(t['id'] for t in self.j.c['tasks'] if t['kind'] == 'weather')
        sk = self.j.get(tid)['_sky']
        self.assertFalse(sk['warn'])
        for i in HD.INSTRUMENTS:
            self.j.act('hd_read', task=tid, what=i)
        self.j.act('hd_report', task=tid, wind=sk['wind'], sea=sk['sea'], vis=sk['vis'], baro=sk['baro'])
        self.j.act('hd_warn', task=tid)
        self.j.act('hd_wdone', task=tid)
        self.assertEqual(self.j.get(tid)['mistakes'], 0)

    def test_a_wrong_report_is_a_slip(self):
        tid = next(t['id'] for t in self.j.c['tasks'] if t['kind'] == 'weather')
        sk = self.j.get(tid)['_sky']
        self.j.act('hd_report', task=tid, wind=(sk['wind'] + 3) % 10, sea=sk['sea'], vis=sk['vis'], baro=sk['baro'])
        codes = {x['code'] for x in self.j.get(tid)['slips']}
        self.assertTrue({'guess', 'obs_wind'} <= codes, codes)


class Sea(Base):
    def test_going_out_alone_is_never_right(self):
        j = self.at(lambda t: t['kind'] == 'sea' and t['_case'] == 'flare')
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('hd_look', task=tid)
        j.act('hd_act', task=tid, what='boat')
        self.assertTrue(any(x['code'] == 'went_out' and x['safety'] for x in j.get(tid)['slips']))

    def test_a_distress_must_be_relayed_at_the_right_priority(self):
        j = self.at(lambda t: t['kind'] == 'sea' and t['_case'] == 'flare')
        tid = j.c['active_task']
        self.ready(j, tid)
        t = j.get(tid)
        j.act('hd_look', task=tid)
        j.act('hd_relay', task=tid, kind='pan', bearing=t['_bearing'], persons=t['_persons'])
        j.act('hd_act', task=tid, what='track')
        j.act('hd_sdone', task=tid)
        self.assertTrue(any(x['code'] == 'under_call' and x['safety'] for x in j.get(tid)['slips']))

    def test_a_wrong_bearing_sends_rescue_the_wrong_way(self):
        j = self.at(lambda t: t['kind'] == 'sea' and t['_case'] == 'drift')
        tid = j.c['active_task']
        self.ready(j, tid)
        t = j.get(tid)
        wrong = next(b for b in t['needs']['bearings'] if b != t['_bearing'])
        j.act('hd_look', task=tid)
        j.act('hd_relay', task=tid, kind='pan', bearing=wrong, persons=t['_persons'])
        j.act('hd_act', task=tid, what='track')
        j.act('hd_sdone', task=tid)
        self.assertTrue(any(x['code'] == 'bad_bearing' for x in j.get(tid)['slips']))

    def test_the_captain_decides_by_himself_and_always_the_same(self):
        j = self.at(lambda t: t['kind'] == 'sea' and t['_case'] == 'storm_out')
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('hd_look', task=tid)
        a = j.act('hd_vhf', task=tid, say=['threat'])['message']
        j2 = self.at(lambda t: t['kind'] == 'sea' and t['_case'] == 'storm_out')
        self.ready(j2, tid)
        j2.act('hd_look', task=tid)
        self.assertEqual(j2.act('hd_vhf', task=tid, say=['threat'])['message'], a)

    def test_a_captain_who_will_not_turn_back_must_be_reported(self):
        for day, slot in ((d, s) for d in range(3, 200) for s in range(2, 5)):
            t = HD.make_task(day, slot, 1)
            if t['kind'] != 'sea' or t['_case'] != 'storm_out':
                continue
            t['talk'] = [['threat'], ['beg']]
            if HD.talk_outcome(t) == 'refuse':
                break
        else:
            self.skipTest('no stubborn captain in range')
        j = Journey('lighthouse', slot=slot, day=day)
        quiet(j)
        on_duty(j)
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('hd_look', task=tid)
        j.act('hd_vhf', task=tid, say=['threat'])
        j.act('hd_vhf', task=tid, say=['beg'])
        self.assertEqual(j.get(tid)['talk_out'], 'refuse')
        j.act('hd_sdone', task=tid)
        self.assertTrue(any(x['code'] == 'no_report' and x['safety'] for x in j.get(tid)['slips']))


class Visitors(Base):
    def test_anyone_in_danger_is_sheltered(self):
        j = self.at(lambda t: t['kind'] == 'visitor' and t['_v'] == 'kayak')
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('hd_papers', task=tid)
        j.act('hd_answer', task=tid, answer='refuse')
        self.assertTrue(any(x['code'] == 'refused_emergency' and x['safety'] for x in j.get(tid)['slips']))

    def test_giving_in_costs_conduct_and_pays_nothing(self):
        j = self.at(lambda t: t['kind'] == 'visitor' and t['_v'] == 'propose')
        tid = j.c['active_task']
        self.ready(j, tid)
        money = j.c['money']
        j.act('hd_papers', task=tid)
        j.act('hd_answer', task=tid, answer='give')
        self.assertTrue(any(x['code'] == 'gave_in' and x['safety'] for x in j.get(tid)['slips']))
        self.assertGreater(j.c['ext']['data']['odd']['conduct']['points'], 0)
        self.assertEqual(j.c['money'], money)

    def test_a_group_with_papers_is_welcomed(self):
        j = self.j
        tid = next(t['id'] for t in j.c['tasks'] if t['kind'] == 'visitor')
        on_duty(j)
        self.ready(j, tid)
        j.act('hd_papers', task=tid)
        j.act('hd_answer', task=tid, answer='refuse')
        self.assertTrue(any(x['code'] == 'refuse_permit' for x in j.get(tid)['slips']))

    def test_a_sneaker_must_be_brought_down(self):
        for day, slot in ((d, s) for d in range(2, 300) for s in range(2, 5)):
            t = HD.make_task(day, slot, 1)
            if t['kind'] != 'visitor' or not HD.VISITOR[t['_v']]['sneaky']:
                continue
            v = HD.VISITOR[t['_v']]
            if 'report' not in v['best'] + v['ok'] and HD.visit_react(t, v, 'report', 0) == 'again' and HD.visit_react(t, v, 'report', 1) == 'sneak':
                break
        else:
            self.skipTest('no sneaky visitor in range')
        j = Journey('lighthouse', slot=slot, day=day)
        quiet(j)
        on_duty(j)
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('hd_papers', task=tid)
        j.act('hd_answer', task=tid, answer='report')
        j.act('hd_answer', task=tid, answer='report')
        self.assertTrue(j.get(tid)['sneak'])
        with self.assertRaises(GameError):
            j.act('hd_answer', task=tid, answer='refuse')
        j.act('hd_vdone', task=tid)
        self.assertTrue(any(x['code'] == 'intruder' and x['safety'] for x in j.get(tid)['slips']))


class Supply(Base):
    def test_signing_more_than_measured_is_a_corner_cut(self):
        j = self.at(lambda t: t['kind'] == 'supply' and t['_after'] - t['_before'] < 200)
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('hd_dip', task=tid, when='before')
        j.act('hd_dip', task=tid, when='after')
        j.act('hd_ssign', task=tid, litres=200)
        self.assertTrue(any(x['code'] == 'signed_more' for x in j.get(tid)['slips']))
        self.assertGreater(j.c['ext']['data']['odd']['conduct']['points'], 0)

    def test_the_basket_is_haggled_and_paid_from_the_wallet(self):
        j = self.at(lambda t: t['kind'] == 'supply')
        tid = j.c['active_task']
        self.ready(j, tid)
        t = j.get(tid)
        floor = HD.basket_floor(t)
        r = j.act('hd_offer', task=tid, price=floor - 1)
        self.assertIsNotNone(j.get(tid)['counter'])
        money = j.c['money']
        j.act('hd_offer', task=tid, price=j.get(tid)['counter'])
        self.assertEqual(j.get(tid)['buy'], 'bought')
        self.assertEqual(j.c['money'], money - j.get(tid)['offers'][-1])
        self.assertTrue(r['message'])

    def test_a_lowball_makes_the_captain_walk(self):
        j = self.at(lambda t: t['kind'] == 'supply')
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('hd_offer', task=tid, price=5)
        self.assertEqual(j.get(tid)['buy'], 'walked')


class Life(Base):
    def test_life_on_the_rock(self):
        j = self.j
        before = self.d['lonely']
        j.act('hd_pet')
        j.act('hd_call')
        j.act('hd_garden')
        self.assertEqual(self.d['lonely'], max(0, before - 4))
        with self.assertRaises(GameError):
            j.act('hd_pet')

    def test_loneliness_grows_without_fresh_food_and_tires(self):
        j = self.j
        self.d.update(fresh=0, lonely=6)
        f = self.d['odd']['fatigue']
        j.act('end_day')
        j.act('start_day')
        self.assertEqual(self.d['lonely'], 8)
        self.assertGreaterEqual(self.d['odd']['fatigue'], f)


class Around(Base):
    def test_every_surprise_option_is_playable(self):
        for x in HD.DESK:
            for o in x['options']:
                j = Journey('lighthouse')
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-t', script=x['id'], day=j.c['day'], at='between')
                with self.assertRaises(GameError):
                    j.act('hd_check', task=j.c['active_task'], item='lamp')
                r = j.act('hd_desk', option=o['id'])
                self.assertTrue(r['message'])
                self.assertIsNone(j.c['ext']['data']['desk']['ev'])
                validate_state(json.loads(json.dumps(j.state)))

    def test_every_encounter_can_be_answered_every_way(self):
        for x in HD.ODD:
            for say in (best_answer(x), dict(tone='soft', say=['yes'], to='self', **({'n': x['ask']} if x['kind'] == 'bargain' else {}))):
                j = Journey('lighthouse')
                odd = ao.ensure(j.c['ext']['data'])
                odd['ev'] = dict(id='odd-t', script=x['id'], day=j.c['day'], at='between', said=[])
                r = None
                for _ in range(ao.MAX_ROUNDS):
                    if j.c['ext']['data']['odd']['ev'] is None:
                        break
                    r = j.act('hd_odd', **say)
                self.assertIsNone(j.c['ext']['data']['odd']['ev'], x['id'])
                self.assertTrue(r['message'])
                out = j.c['ext']['data']['odd']['last']['outcome']
                for word in ('tổ bay', 'hãng', 'đình chỉ bay', 'chuyến bay', 'phòng an toàn', 'đường ngang'):
                    self.assertNotIn(word, out, x['id'])
                validate_state(json.loads(json.dumps(j.state)))

    def test_giving_in_is_never_rewarded(self):
        for x in HD.ODD:
            if x['kind'] in ('charm', 'corner'):
                j = Journey('lighthouse')
                odd = ao.ensure(j.c['ext']['data'])
                odd['ev'] = dict(id='odd-t', script=x['id'], day=j.c['day'], at='between', said=[])
                money = j.c['money']
                j.act('hd_odd', tone='soft', say=['yes'], to='self')
                self.assertGreater(j.c['ext']['data']['odd']['conduct']['points'], 0, x['id'])
                self.assertLessEqual(j.c['money'], money)

    def test_situations_are_playable(self):
        j = self.j
        for x in HD.SPEC['situations']:
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
        self.assertEqual(dc.hours(self.j.c, 'lighthouse'), HD.HOURS)


class Saves(Base):
    def test_forged_needs_are_rejected(self):
        for key, value in (('_fuel', 1), ('_fault', 'motor'), ('_off', [2, 1, 0])):
            s = copy.deepcopy(self.j.state)
            t = next(x for x in s['careers']['lighthouse']['tasks'] if x['kind'] == 'dawn')
            if t[key] == value:
                continue
            t[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)
        s = copy.deepcopy(self.j.state)
        t = next(x for x in s['careers']['lighthouse']['tasks'] if x['kind'] == 'weather')
        t['_sky']['wind'] = 9
        with self.assertRaises(GameError):
            validate_state(s)

    def test_broken_task_fields_are_rejected(self):
        j = self.at(lambda t: t['kind'] == 'sea' and t['_case'] == 'storm_out')
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('hd_look', task=tid)
        j.act('hd_vhf', task=tid, say=['forecast'])
        for key, value in (('did', ['fly']), ('talk_out', 'back' if j.get(tid)['talk_out'] != 'back' else 'refuse'), ('talk', [['x']]),
                           ('relay', dict(kind='mayday', bearing='999', persons=None)), ('looked', 'yes')):
            s = copy.deepcopy(j.state)
            next(x for x in s['careers']['lighthouse']['tasks'] if x['id'] == tid)[key] = value
            with self.assertRaises(GameError, msg=key):
                validate_state(s)

    def test_broken_data_is_rejected(self):
        for path, value in ((('stats', 'lit'), -2), (('intro',), 'yes'), (('regulars',), {'9': {'visits': 1}}), (('log',), [dict(day=1)]),
                            (('odd', 'fatigue'), 99), (('lonely',), 99), (('fresh',), -1)):
            s = copy.deepcopy(self.j.state)
            node = s['careers']['lighthouse']['ext']['data']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            with self.assertRaises(GameError, msg=path):
                validate_state(s)

    def test_mid_job_save_round_trip(self):
        j = self.at(lambda t: t['kind'] == 'sea' and t['_case'] == 'flare')
        tid = j.c['active_task']
        self.ready(j, tid)
        j.act('hd_look', task=tid)
        s = json.loads(json.dumps(j.state))
        validate_state(s)
        j.state = s
        solve(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        validate_state(json.loads(json.dumps(j.state)))

    def test_old_save_without_the_light_gains_it_and_nothing_else_changes(self):
        s = new_state()
        old = copy.deepcopy(s)
        old['careers'].pop('lighthouse')
        a, b = migrate_state(old), migrate_state(copy.deepcopy(s))
        for cid in b['careers']:
            if cid != 'lighthouse':
                self.assertEqual(a['careers'][cid], b['careers'][cid], cid)
        validate_state(a)
        self.assertEqual(a['careers']['lighthouse']['job']['status'], 'none')

    def test_story_players_past_chapter_four_find_the_light_open(self):
        from game import journey as jr
        j = jr.initial(True, 5)
        j['chapter'] = 5
        j['unlocked'] = [c for n in range(1, 6) for c in jr.CH_UNLOCKS[n] if c != 'lighthouse']
        old = list(j['unlocked'])
        jr.upgrade(j)
        self.assertEqual(j['unlocked'][:len(old)], old)
        self.assertIn('lighthouse', j['unlocked'])
        young = jr.initial(True, 5)
        jr.upgrade(young)
        self.assertNotIn('lighthouse', young['unlocked'])

    def test_public_view_is_json(self):
        view = public_state(self.j.state)['careers']['lighthouse']
        json.dumps(view)
        for k in ('mod', 'desk', 'odd', 'intro', 'on_duty', 'life', 'supply_in', 'rise', 'set'):
            self.assertIn(k, view['data'])

    def test_yesterday_s_jobs_are_closed_and_today_is_full(self):
        j = self.j
        solve(j, j.c['active_task'])
        tid = next(t['id'] for t in j.c['tasks'] if t['kind'] == 'visitor')
        self.ready(j, tid)
        j.act('end_day')
        j.act('start_day')
        self.assertEqual(j.get(tid)['status'], 'cancelled')
        today = [t for t in j.c['tasks'] if t['day'] == 2]
        self.assertEqual(len(today), HD.daily_task_count(2))
        self.assertEqual(sorted(int(t['id'][-2:]) for t in today), list(range(HD.daily_task_count(2))))
        validate_state(json.loads(json.dumps(j.state)))


if __name__ == '__main__':
    unittest.main()
