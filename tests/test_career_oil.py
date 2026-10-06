"""Thợ dầu khí (plugin career oil): the rotation (out → rig × 4 → home, typhoons that keep the crew on board or ashore),
the helicopter (bag, survival gear, HUET), the arrival (T-card, muster station, alarm tones), the toolbox talk (PPE,
bump test, hazards), maintenance under a permit (isolation, bleed, prove zero, gas test, the traps and stop-work
authority), rounds, drills, storm lashing, the handover and the family's money on the shore day; hidden information,
determinism, save validation, the awkward people (air_odd scripts) and every situation."""
import copy
import json
import unittest

from tests.helpers import Journey
from game.careers import kit, PLUGINS, air_odd as ao
from game.careers import oil_content as K
from game.content import make_task
from game.engine import GameError, public_state, validate_state

OIL = PLUGINS.get('oil')


def quiet(j):
    """No encounter and no desk surprise for the rest of today: these tests look at one job."""
    d = j.c['ext']['data']
    odd = ao.ensure(d)
    odd.update(day=j.c['day'], plan=[], fired=0, ev=None)
    d['desk'].update(day=j.c['day'], plan=[], fired=0, ev=None)


def find(pick, days=range(1, 120), slots=range(0, 5)):
    """The first (day, slot) whose generated task passes `pick`."""
    return next((d, s) for d in days for s in slots if pick(OIL.make_task(d, s, 1)))


def best_answer(x):
    k = x['kind']
    if k == 'bargain':
        return dict(tone='firm', say=['rule', 'alt'], to='company' if x['rank'] != 'kin' else 'self', n=x['limit'])
    say = {'charm': ['no', 'rule'], 'harass': ['stop', 'rule'], 'corner': ['speak', 'rule'], 'demand': ['rule', 'alt']}[k]
    to = 'self' if x['rank'] == 'kin' else 'company' if k in ('charm', 'harass', 'corner') else 'crew'
    return dict(tone='firm', say=say, to=to)


def settle(j):
    """Answer whatever is waiting (a desk surprise, an encounter) the careful way."""
    for _ in range(12):
        d = j.c['ext']['data']
        if d['desk']['ev']:
            x = kit.desk_script(K.DESK, d['desk']['ev']['script'])
            good = next((o['id'] for o in x['options'] if o.get('good') is True), x['options'][0]['id'])
            j.act('dk_desk', option=good)
            continue
        ev = d['odd']['ev']
        if ev:
            x = ao.script(K.ODD, ev['script'])
            j.act('dk_odd', **best_answer(x))
            continue
        return


def solve(j, tid, careful=True):
    """Do one job the way a careful technician does."""
    settle(j)
    t = j.get(tid)
    if not t['known']:
        j.act('ask', task=tid)
    t = j.get(tid)
    n, k = t['needs'], t['kind']
    step = lambda action, **p: (settle(j), j.act(action, task=tid, **p), settle(j))
    if k == 'heli':
        if n['cancel']:
            step('dk_wait')
            return j.get(tid)
        for item in n['bag']:
            if K.BAG_INDEX[item]['banned']:
                step('dk_bag', item=item)
        for item in ('ta', 'mi', 'laptop', 'banh'):
            if OIL.bag_kg(j.get(tid)) > n['limit'] and item in n['bag'] and item not in j.get(tid)['bag_out']:
                step('dk_bag', item=item)
        for g in K.GEAR_IDS:
            step('dk_gear', item=g)
        step('dk_quiz', answer=K.QUIZ_INDEX[n['quiz']]['answer'])
        if n['delay']:
            step('dk_wait')
        step('dk_board')
    elif k == 'induct':
        step('dk_tcard')
        step('dk_station', station=n['station'])
        for tone in n['tones']:
            step('dk_tone', tone=tone, pick=tone)
        step('dk_settle')
    elif k == 'toolbox':
        for x in K.PPE_IDS:
            step('dk_ppe', item=x)
        step('dk_bump')
        if j.get(tid)['bumped'] == 'fail':
            step('dk_swap')
            step('dk_bump')
        for h in t['_real']:
            step('dk_hazard', hazard=h)
        step('dk_remind')
        step('dk_talk')
    elif k == 'ptw':
        job = K.JOB_INDEX[n['job']]
        step('dk_permit', permit=job['permit'])
        step('dk_xref')
        for pid, _, _ in job['points']:
            step('dk_iso', point=pid)
        if job['bleed']:
            step('dk_bleed')
        if job['prove']:
            step('dk_verify')
        step('dk_gas')
        if t['_trap'] and careful:
            step('dk_stop', reason=K.TRAPS[t['_trap']]['reason'])
            step('dk_nearmiss')
        if job['watch']:
            step('dk_watch')
        step('dk_work')
        step('dk_restore')
        step('dk_close')
    elif k == 'round':
        for g in n['gauges']:
            v = OIL._gauge(j.get(tid), g['tag'])
            step('dk_read', tag=g['tag'], verdict=v['verdict'])
            if v['verdict'] != 'ok':
                step('dk_call', tag=g['tag'])
        for a in n['areas']:
            step('dk_look', area=a)
            if j.get(tid)['found'] and j.get(tid)['leak'] is None:
                step('dk_leak', how='report')
        step('dk_log')
    elif k == 'drill':
        step('dk_alarm', pick=t['_alarm'])
        step('dk_drop')
        step('dk_route', route='up')
        step('dk_station2', station=n['station'])
        step('dk_card')
    elif k == 'secure':
        for i in n['items']:
            step('dk_secure', item=i, how=K.LOOSE_INDEX[i]['do'])
        step('dk_crane')
        step('dk_report')
    elif k == 'handover':
        for i in n['items']:
            if K.OPEN_INDEX[i]['must']:
                step('dk_note', item=i)
        step('dk_handover')
    elif k == 'shore':
        step('dk_love')
        for rid in n['reqs']:
            r = K.REQUEST_INDEX[rid]
            step('dk_ask', req=rid)
            amount = r['need'] if r['kind'] in ('need', 'gift', 'loan') else 0
            step('dk_send', req=rid, amount=amount, words=['explain', 'love'])
            if j.get(tid)['sent'][rid]['out'] == 'counter':
                step('dk_send', req=rid, amount=j.get(tid)['sent'][rid]['counter'], words=['explain'])
        step('dk_done')
    return j.get(tid)


def fund(j, amount):
    """Set the workplace fund and keep the ledger balanced (operations.validate)."""
    j.c['ops']['finance']['opening_balance'] += amount - j.c['money']
    j.c['money'] = amount


def at(pick, **kw):
    day, slot = find(pick, **kw)
    j = Journey('oil', slot=slot, day=day)
    fund(j, 500)
    quiet(j)
    return j


@unittest.skipUnless(OIL, 'oil is filtered out by MNL_CAREERS')
class Rotation(unittest.TestCase):
    def test_cycle_and_storms(self):
        kinds = [OIL.phase(d)['kind'] for d in range(1, 400)]
        self.assertEqual(kinds[:6], ['out', 'rig', 'rig', 'rig', 'rig', 'home'])
        self.assertIn('stay', kinds)
        self.assertIn('wait', kinds)
        for d in range(2, 400):
            p, q = OIL.phase(d - 1), OIL.phase(d)
            if q['kind'] == 'stay':
                self.assertIn(p['kind'], ('rig', 'stay'))
                self.assertEqual(OIL.mod_of(d)['id'], 'typhoon')
            if q['kind'] == 'out':
                self.assertIn(p['kind'], ('home', 'wait'))
            if p['kind'] == 'home':
                self.assertIn(q['kind'], ('out', 'wait'))
                self.assertEqual(q['hitch'], p['hitch'] + 1)

    def test_plan_matches_phase(self):
        for d in range(1, 120):
            kinds = OIL.plan_of(d)
            ph = OIL.phase(d)['kind']
            self.assertEqual(OIL.daily_task_count(d), len(kinds))
            if ph == 'out':
                self.assertEqual(kinds, ['heli', 'induct'])
            elif ph == 'home':
                self.assertEqual(kinds, ['handover', 'shore'])
            elif ph == 'wait':
                self.assertEqual(kinds, ['heli', 'shore'])
            else:
                self.assertEqual(kinds[0], 'toolbox')

    def test_deterministic(self):
        for d in range(1, 40):
            for s in range(0, 6):
                self.assertEqual(OIL.make_task(d, s, 3), OIL.make_task(d, s, 3))


@unittest.skipUnless(OIL, 'oil is filtered out by MNL_CAREERS')
class Days(unittest.TestCase):
    def test_play_two_hitches_carefully(self):
        j = Journey('oil')
        j.act('dk_intro')
        fund(j, 300)
        stars = []
        for _ in range(14):
            day = j.c['day']
            for _ in range(8):
                open_ = [t for t in j.c['tasks'] if t['status'] not in ('completed', 'cancelled', 'referred') and t['day'] == day]
                if not open_:
                    break
                t = solve(j, open_[0]['id'])
                self.assertEqual(t['status'], 'completed', (day, t['kind'], t.get('slips')))
                self.assertFalse(t.get('slips'), (day, t['kind'], t.get('slips')))
            settle(j)
            r = j.act('end_day')
            self.assertIn('lines', r['summary']['career'])
            validate_state(json.loads(json.dumps(j.state)))
            j.act('start_day')
        reviews = [f for f in j.c['feed'] if f.get('stars')]
        self.assertTrue(reviews)

    def test_hidden_before_ask(self):
        j = Journey('oil')
        t = j.task
        pub = public_state(j.state)
        room = pub['careers']['oil'] if 'careers' in pub and 'oil' in pub['careers'] else None
        js = json.dumps(pub, ensure_ascii=False)
        self.assertNotIn('_trap', js)
        self.assertNotIn('"_push"', js)
        if room:
            vt = next(x for x in room['tasks'] if x['id'] == t['id'])
            self.assertIsNone(vt['needs'])

    def test_tampered_fixed_field_rejected(self):
        j = at(lambda t: t['kind'] == 'ptw' and t['_trap'])
        t = j.task
        t['_trap'] = None
        with self.assertRaises(GameError):
            validate_state(j.state)


@unittest.skipUnless(OIL, 'oil is filtered out by MNL_CAREERS')
class Helicopter(unittest.TestCase):
    def test_banned_item_is_a_safety_slip(self):
        j = at(lambda t: t['kind'] == 'heli' and not t['needs']['cancel'] and not t['needs']['delay'])
        tid = j.task['id']
        j.act('ask', task=tid)
        for g in K.GEAR_IDS:
            j.act('dk_gear', task=tid, item=g)
        j.act('dk_quiz', task=tid, answer=K.QUIZ_INDEX[j.task['needs']['quiz']]['answer'])
        j.act('dk_board', task=tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertTrue(any(s['code'] == 'banned' and s['safety'] for s in t['slips']))

    def test_no_boarding_without_gear(self):
        j = at(lambda t: t['kind'] == 'heli' and not t['needs']['cancel'] and not t['needs']['delay'])
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('dk_quiz', task=tid, answer=K.QUIZ_INDEX[j.task['needs']['quiz']]['answer'])
        r = j.act('dk_board', task=tid)
        self.assertIs(r.get('correct'), False)
        self.assertNotEqual(j.get(tid)['status'], 'completed')

    def test_fog_must_be_waited(self):
        j = at(lambda t: t['kind'] == 'heli' and t['needs']['delay'])
        tid = j.task['id']
        j.act('ask', task=tid)
        for g in K.GEAR_IDS:
            j.act('dk_gear', task=tid, item=g)
        j.act('dk_quiz', task=tid, answer=K.QUIZ_INDEX[j.task['needs']['quiz']]['answer'])
        with self.assertRaises(GameError):
            j.act('dk_board', task=tid)

    def test_typhoon_cancels(self):
        j = at(lambda t: t['kind'] == 'heli' and t['needs']['cancel'])
        tid = j.task['id']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('dk_board', task=tid)
        j.act('dk_wait', task=tid)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_wrong_quiz_teaches(self):
        j = at(lambda t: t['kind'] == 'heli' and not t['needs']['cancel'])
        tid = j.task['id']
        j.act('ask', task=tid)
        q = K.QUIZ_INDEX[j.task['needs']['quiz']]
        wrong = next(o[0] for o in q['options'] if o[0] != q['answer'])
        r = j.act('dk_quiz', task=tid, answer=wrong)
        self.assertIs(r['correct'], False)
        self.assertIn(q['why'], r['message'])


@unittest.skipUnless(OIL, 'oil is filtered out by MNL_CAREERS')
class Permit(unittest.TestCase):
    def prep(self, j, tid, gas=True):
        t = j.get(tid)
        job = K.JOB_INDEX[t['needs']['job']]
        j.act('dk_permit', task=tid, permit=job['permit'])
        j.act('dk_xref', task=tid)
        for pid, _, _ in job['points']:
            j.act('dk_iso', task=tid, point=pid)
        if job['bleed']:
            j.act('dk_bleed', task=tid)
        if job['prove']:
            j.act('dk_verify', task=tid)
        if gas:
            j.act('dk_gas', task=tid)
        if job['watch']:
            j.act('dk_watch', task=tid)
        return job

    def test_wrong_permit_refused(self):
        j = at(lambda t: t['kind'] == 'ptw')
        tid = j.task['id']
        j.act('ask', task=tid)
        right = K.JOB_INDEX[j.task['needs']['job']]['permit']
        wrong = next(k for k in K.PERMITS if k != right)
        r = j.act('dk_permit', task=tid, permit=wrong)
        self.assertIs(r['correct'], False)
        self.assertIsNone(j.get(tid)['permit'])

    def test_trap_stop_is_rewarded_and_working_through_is_a_safety_slip(self):
        for trap in K.TRAPS:
            pick = lambda t, trap=trap: t['kind'] == 'ptw' and t['_trap'] == trap
            try:
                find(pick)
            except StopIteration:
                continue
            j = at(pick)
            tid = j.task['id']
            j.act('ask', task=tid)
            self.prep(j, tid)
            seen = K.TRAPS[trap]['seen']
            self.assertIn(seen, j.get(tid)['read'])
            j.act('dk_stop', task=tid, reason=K.TRAPS[trap]['reason'])
            self.assertTrue(j.get(tid)['fixed'])
            j.act('dk_nearmiss', task=tid)
            j.act('dk_work', task=tid)
            j.act('dk_restore', task=tid)
            j.act('dk_close', task=tid)
            t = j.get(tid)
            self.assertEqual(t['status'], 'completed')
            self.assertFalse(t.get('slips'), trap)

            j2 = at(pick)
            tid = j2.task['id']
            j2.act('ask', task=tid)
            self.prep(j2, tid)
            j2.act('dk_work', task=tid)
            self.assertTrue(any(s['code'] == 'trap_' + trap and s['safety'] for s in j2.get(tid)['slips']))

    def test_stop_without_hazard_costs_no_mark(self):
        j = at(lambda t: t['kind'] == 'ptw' and not t['_trap'])
        tid = j.task['id']
        j.act('ask', task=tid)
        for _ in range(3):
            j.act('dk_stop', task=tid, reason='unsure')
        self.assertFalse(j.get(tid).get('slips'))
        with self.assertRaises(GameError):
            j.act('dk_nearmiss', task=tid)
        self.prep(j, tid)
        j.act('dk_work', task=tid)
        j.act('dk_restore', task=tid)
        j.act('dk_close', task=tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertTrue(all(c['score'] == 5 for c in OIL.feedback(j.c, t)['criteria']), OIL.feedback(j.c, t))

    def test_skipped_isolation_and_gas_are_safety_slips(self):
        j = at(lambda t: t['kind'] == 'ptw' and not t['_trap'] and K.JOB_INDEX[t['needs']['job']]['points'])
        tid = j.task['id']
        j.act('ask', task=tid)
        job = K.JOB_INDEX[j.task['needs']['job']]
        j.act('dk_permit', task=tid, permit=job['permit'])
        j.act('dk_work', task=tid)
        codes = {s['code'] for s in j.get(tid)['slips']}
        self.assertIn('iso', codes)
        self.assertIn('nogas', codes)
        j.act('dk_close', task=tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual(OIL.feedback(j.c, j.get(tid))['criteria'][0]['score'], 1)

    def test_verify_needs_locks(self):
        j = at(lambda t: t['kind'] == 'ptw' and K.JOB_INDEX[t['needs']['job']]['prove'] and K.JOB_INDEX[t['needs']['job']]['points'])
        tid = j.task['id']
        j.act('ask', task=tid)
        job = K.JOB_INDEX[j.task['needs']['job']]
        j.act('dk_permit', task=tid, permit=job['permit'])
        with self.assertRaises(GameError):
            j.act('dk_verify', task=tid)


@unittest.skipUnless(OIL, 'oil is filtered out by MNL_CAREERS')
class RoundsDrillsStorm(unittest.TestCase):
    def test_tighten_leak_is_unsafe(self):
        j = at(lambda t: t['kind'] == 'round' and t['_leak'])
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('dk_look', task=tid, area=j.task['_leak']['area'])
        r = j.act('dk_leak', task=tid, how='tighten')
        self.assertIs(r['correct'], False)
        self.assertTrue(any(s['code'] == 'tighten' and s['safety'] for s in j.get(tid)['slips']))

    def test_unreported_gauge(self):
        j = at(lambda t: t['kind'] == 'round' and any(OIL._gauge(t, g['tag'])['verdict'] != 'ok' for g in t['needs']['gauges']))
        tid = j.task['id']
        j.act('ask', task=tid)
        for g in j.task['needs']['gauges']:
            j.act('dk_read', task=tid, tag=g['tag'], verdict=OIL._gauge(j.get(tid), g['tag'])['verdict'])
        j.act('dk_log', task=tid)
        self.assertIn('nocall', {s['code'] for s in j.get(tid)['slips']})

    def test_lift_and_phone_in_a_drill(self):
        j = at(lambda t: t['kind'] == 'drill')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('dk_alarm', task=tid, pick=j.task['_alarm'])
        j.act('dk_phone', task=tid)
        j.act('dk_route', task=tid, route='lift')
        codes = {s['code'] for s in j.get(tid)['slips']}
        self.assertTrue({'phone', 'lift'} <= codes)

    def test_storm_lashing(self):
        j = at(lambda t: t['kind'] == 'secure')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('dk_report', task=tid)
        codes = {s['code'] for s in j.get(tid)['slips']}
        self.assertTrue({'loose', 'crane'} <= codes)

    def test_handover_omission(self):
        j = at(lambda t: t['kind'] == 'handover')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('dk_handover', task=tid)
        self.assertIn('omit', {s['code'] for s in j.get(tid)['slips']})


@unittest.skipUnless(OIL, 'oil is filtered out by MNL_CAREERS')
class Shore(unittest.TestCase):
    def test_scam_costs_money_and_a_slip(self):
        j = at(lambda t: t['kind'] == 'shore' and 'crypto' in t['needs']['reqs'])
        tid = j.task['id']
        j.act('ask', task=tid)
        before = j.c['money']
        j.act('dk_send', task=tid, req='crypto', amount=20, words=[])
        t = j.get(tid)
        self.assertIn('scam', {s['code'] for s in t['slips']})
        self.assertEqual(j.c['money'], before + t['needs']['allowance'] - 20)

    def test_ask_reveals_fact_and_refusing_scam_is_good(self):
        j = at(lambda t: t['kind'] == 'shore' and any(K.REQUEST_INDEX[r]['kind'] == 'scam' for r in t['needs']['reqs']))
        tid = j.task['id']
        j.act('ask', task=tid)
        rid = next(r for r in j.task['needs']['reqs'] if K.REQUEST_INDEX[r]['kind'] == 'scam')
        j.act('dk_ask', task=tid, req=rid)
        pub = OIL.public_task(j.get(tid))
        self.assertEqual(next(x for x in pub['reqs'] if x['id'] == rid)['fact'], K.REQUEST_INDEX[rid]['fact'])
        r = j.act('dk_send', task=tid, req=rid, amount=0, words=['explain'])
        self.assertTrue(r.get('celebrate'))

    def test_haggle_counter_then_final(self):
        j = at(lambda t: t['kind'] == 'shore' and any(K.REQUEST_INDEX[r]['kind'] == 'need' and t['_push'][r] >= 1 for r in t['needs']['reqs']))
        tid = j.task['id']
        j.act('ask', task=tid)
        rid = next(r for r in j.task['needs']['reqs'] if K.REQUEST_INDEX[r]['kind'] == 'need' and j.task['_push'][r] >= 1)
        j.act('dk_send', task=tid, req=rid, amount=1, words=['explain'])
        self.assertEqual(j.get(tid)['sent'][rid]['out'], 'counter')
        j.act('dk_send', task=tid, req=rid, amount=K.REQUEST_INDEX[rid]['need'], words=['love'])
        self.assertEqual(j.get(tid)['sent'][rid]['out'], 'happy')
        with self.assertRaises(GameError):
            j.act('dk_send', task=tid, req=rid, amount=1, words=[])


@unittest.skipUnless(OIL, 'oil is filtered out by MNL_CAREERS')
class Around(unittest.TestCase):
    def test_every_odd_script_resolves(self):
        j = Journey('oil')
        fund(j, 1000)
        odd = ao.ensure(j.c['ext']['data'])
        for i, x in enumerate(K.ODD):
            odd.update(ev=dict(id=f'odd-t{i}', script=x['id'], day=j.c['day'], at='between', said=[]), day=j.c['day'], plan=[], fired=0)
            for _ in range(ao.MAX_ROUNDS):
                if not odd['ev']:
                    break
                j.act('dk_odd', **best_answer(x))
                odd = ao.ensure(j.c['ext']['data'])
            self.assertIsNone(odd['ev'], x['id'])
            self.assertNotEqual(odd['last']['good'], False, x['id'])
            validate_state(j.state)

    def test_giving_in_to_a_corner_costs_conduct(self):
        j = Journey('oil')
        odd = ao.ensure(j.c['ext']['data'])
        x = next(s for s in K.ODD if s['id'] == 'dk-skipgas')
        odd.update(ev=dict(id='odd-g', script=x['id'], day=j.c['day'], at='between', said=[]), plan=[], fired=0, day=j.c['day'])
        j.act('dk_odd', tone='soft', say=['yes'], to='self')
        self.assertGreater(ao.ensure(j.c['ext']['data'])['conduct']['points'], 0)

    def test_desk_scripts_choose(self):
        j = Journey('oil')
        fund(j, 500)
        for i, x in enumerate(K.DESK):
            for o in x['options']:
                j.c['ext']['data']['desk']['ev'] = dict(id=f'desk-t{i}{o["id"]}', script=x['id'], day=j.c['day'], at='between')
                j.act('dk_desk', option=o['id'])
        validate_state(j.state)

    def test_situations(self):
        j = Journey('oil')
        fund(j, 500)
        for x in K.SITUATIONS:
            for o in x['options']:
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=o['id'])
                self.assertTrue(j.act('sit_confirm', confirm=True)['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_employment_required(self):
        from game.engine import new_state, apply_action
        s = new_state()
        s, _ = apply_action(s, 'oil', 'select_career', {})
        with self.assertRaises(GameError):
            apply_action(s, 'oil', 'start_day', {})

    def test_save_round_trip(self):
        j = Journey('oil')
        validate_state(json.loads(json.dumps(j.state)))


if __name__ == '__main__':
    unittest.main()
