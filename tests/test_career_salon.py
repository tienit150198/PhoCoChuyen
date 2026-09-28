import copy
import json
import unittest

import game.careers.kit as kit
from game.engine import GameError, public_state, validate_state
from game.careers import salon as S
from tests.helpers import Journey


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t


def find(title):
    """An everyday client with this title (v0.5 special clients have their own finder)."""
    for day in range(1, 30):
        for slot in range(6):
            t = S.make_task(day, slot, 1)
            if t['title'] == title and not t['needs'].get('case'):
                return day, slot
    raise AssertionError('no slot for ' + title)


T_OFFICE = 'Nâu lạnh đi làm, tỉa ngọn'
T_IDOL = 'Bạch kim như ảnh idol'
T_GRAY = 'Nhuộm phủ bạc lần đầu'
T_MC = 'Tóc bóng mượt để làm MC'
T_KID = 'Mái bằng đầu đời của bé Su'
T_RED = 'Đỏ rượu vang cho sang'
T_UNDERCUT = 'Undercut gọn cho mùa nóng'


class SalonTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def journey(self, title):
        day, slot = find(title)
        self.j = Journey('salon', slot=slot, day=day)
        return self.j

    def roundtrip(self):
        validate_state(json.loads(json.dumps(self.j.state)))

    def review(self, tid):
        return next(p for p in self.j.c['feed'] if p['kind'] == 'review' and p.get('source') == tid)

    def office_to_plan(self):
        j = self.journey(T_OFFICE)
        j.act('ask')
        for topic in ('history', 'patch', 'length', 'budget'):
            j.act('sl_consult', topic=topic)
        j.act('sl_inspect', zone='ends')
        j.act('sl_plan', services=['color', 'cut', 'style'], sessions=1)
        return j

    # ---------------------------------------------------------------- happy path
    def test_office_full_service_five_stars(self):
        j = self.office_to_plan()
        tid = j.task['id']
        money = j.c['money']
        stock = kit.stock(j.c, 'dye_6_1')
        j.act('sl_mix', kind='color', shade='dye_6_1', dev=20, ratio='1:1')
        self.assertEqual(kit.stock(j.c, 'dye_6_1'), stock - 1)
        self.assertTrue(j.task['bowl']['ok'])
        j.act('sl_apply')
        view = public_state(j.state)['careers']['salon']['tasks'][0]
        self.assertEqual(view['timer']['window'], S.WINDOWS['color'])
        self.clock.t += 14
        j.act('sl_rinse')
        self.assertEqual(j.task['results']['color']['zone'], 'ideal')
        j.act('sl_cut', step='section')
        j.act('sl_cut', step='guide', length=3)
        j.act('sl_cut', step='check')
        j.act('sl_style', finish='sleek')
        self.roundtrip()
        j.act('sl_checkout', products=['rt_colorsafe'], confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(t['sold'], ['rt_colorsafe'])
        self.assertEqual(j.c['money'], money + 105 + 25 + S.SPEC['tip'])
        post = self.review(tid)
        self.assertEqual(post['stars'], 5)
        self.assertEqual({x['key'] for x in post['feedback']['criteria']}, {'accuracy', 'quality', 'care', 'attitude', 'speed'})
        self.assertEqual(j.c['ext']['data']['served'], 1)
        self.roundtrip()

    def test_needs_and_answers_hidden_until_asked(self):
        j = self.journey(T_OFFICE)
        view = public_state(j.state)['careers']['salon']['tasks'][0]
        self.assertIsNone(view['needs'])
        self.assertFalse(any(k.startswith('_') for k in view))
        with self.assertRaises(GameError):
            j.act('sl_consult', topic='history')
        j.act('ask')
        view = public_state(j.state)['careers']['salon']['tasks'][0]
        self.assertEqual(view['needs']['services'], ['color', 'cut', 'style'])
        self.assertIsNone(view['budget'])
        self.assertEqual(view['findings'], {})
        j.act('sl_inspect', zone='scalp')
        j.act('sl_consult', topic='budget')
        view = public_state(j.state)['careers']['salon']['tasks'][0]
        self.assertEqual(view['budget'], 140)
        self.assertIn('scalp', view['findings'])
        self.assertNotIn('_key', json.dumps(view))

    def test_payload_validation(self):
        j = self.journey(T_OFFICE)
        j.act('ask')
        for action, payload in (('sl_consult', dict(topic='horoscope')), ('sl_inspect', dict(zone='toes')),
                                ('sl_plan', dict(services='color', sessions=1)), ('sl_plan', dict(services=['color'], sessions=1.0)),
                                ('sl_plan', dict(services=['color', 'color'], sessions=1)), ('sl_plan', dict(services=[], sessions=1))):
            with self.assertRaises(GameError, msg=action):
                j.act(action, **payload)
        j.act('sl_consult', topic='history')
        with self.assertRaises(GameError):
            j.act('sl_consult', topic='history')
        with self.assertRaises(GameError):
            j.act('sl_mix', kind='color', shade='dye_6_1', dev=20, ratio='1:1')   # no plan yet
        j.act('sl_plan', services=['color', 'cut', 'style'], sessions=1)
        for payload in (dict(kind='perm', shade='dye_6_1', dev=20, ratio='1:1'), dict(kind='color', shade='dye_9_9', dev=20, ratio='1:1'),
                        dict(kind='color', shade='dye_6_1', dev=25, ratio='1:1'), dict(kind='color', shade='dye_6_1', dev='20', ratio='1:1'),
                        dict(kind='color', shade='dye_6_1', dev=20, ratio='3:1'), dict(kind='bleach', dev=20, ratio='1:2')):
            with self.assertRaises(GameError, msg=str(payload)):
                j.act('sl_mix', **payload)
        with self.assertRaises(GameError):
            j.act('sl_checkout', products=[], confirm=True)   # services not done
        with self.assertRaises(GameError):
            j.act('sl_cut', step='section')   # hair not washed yet

    # ---------------------------------------------------------------- consultation honesty
    def test_extra_service_and_overpromise(self):
        j = self.journey(T_IDOL)
        j.act('ask')
        r = j.act('sl_plan', services=['bleach', 'toner', 'treatment', 'cut'], sessions=3)
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['mistakes'], 1)
        self.assertIn('pushy', j.task['flags'])
        r = j.act('sl_plan', services=['bleach', 'toner'], sessions=3)   # dropping treatment is not justified
        self.assertTrue(r.get('refused'))
        self.assertIsNone(j.task['plan'])
        j.act('sl_plan', services=['bleach', 'toner', 'treatment'], sessions=1)
        self.assertTrue(j.task['plan']['overpromise'])
        self.assertFalse(j.task['plan']['informed'])

    def test_idol_route_needs_strand_test_and_narrow_window(self):
        j = self.journey(T_IDOL)
        tid = j.task['id']
        j.act('ask')
        j.act('sl_consult', topic='history')
        j.act('sl_inspect', zone='lengths')
        j.act('sl_plan', services=['bleach', 'toner', 'treatment'], sessions=3)
        self.assertTrue(j.task['plan']['informed'])
        with self.assertRaises(GameError):
            j.act('sl_mix', kind='toner', shade='toner_silver', dev=10, ratio='1:2')   # toner before bleach
        j.act('sl_mix', kind='bleach', dev=20, ratio='1:2')
        r = j.act('sl_apply')
        self.assertTrue(r.get('refused'))
        self.assertIn('no_strand', j.task['flags'])
        self.assertEqual(j.task['mistakes'], 1)
        r = j.act('sl_strand')
        self.assertIn('3 buổi', r['message'])
        j.act('sl_apply')
        self.assertTrue(j.task['timer']['fragile'])
        self.clock.t += 13   # would be ideal on virgin hair, over on box-dyed hair
        j.act('sl_rinse')
        self.assertEqual(j.task['results']['bleach']['zone'], 'over')
        j.act('sl_mix', kind='toner', shade='toner_silver', dev=10, ratio='1:2')
        j.act('sl_apply')
        self.clock.t += 6
        j.act('sl_rinse')
        j.act('sl_treat')
        self.roundtrip()
        j.act('sl_checkout', products=['rt_purple', 'rt_mask'], confirm=True)
        t = j.get(tid)
        self.assertEqual(t['sold'], ['rt_purple'])        # 40 xu left after services: mask no longer fits
        self.assertEqual(t['declined'], ['rt_mask'])
        post = self.review(tid)
        crit = {x['key']: x['score'] for x in post['feedback']['criteria']}
        self.assertEqual(crit['quality'], 3)
        self.assertLess(crit['care'], 5)
        self.assertEqual(crit['attitude'], 5)

    def test_timer_zones_and_breakage(self):
        j = self.office_to_plan()
        j.act('sl_mix', kind='color', shade='dye_6_1', dev=20, ratio='1:1')
        j.act('sl_apply')
        self.clock.t += 40
        r = j.act('sl_rinse')
        self.assertEqual(j.task['results']['color']['zone'], 'damage')
        self.assertIn('breakage', j.task['flags'])
        self.assertEqual(j.task['mistakes'], 1)
        self.assertIn('gãy', r['message'])
        self.assertEqual(S._zone(3, S.WINDOWS['color']), 'under')
        self.assertEqual(S._zone(20, S.WINDOWS['color']), 'over')
        self.assertEqual(S._zone(12, S.WINDOWS['bleach_fragile']), 'over')

    def test_wrong_formula_hint_and_dump_records_waste(self):
        j = self.office_to_plan()
        r = j.act('sl_mix', kind='color', shade='dye_4_6', dev=20, ratio='1:1')
        self.assertEqual(j.task['mistakes'], 1)
        self.assertFalse(j.task['bowl']['ok'])
        self.assertIn('Linh', r['message'])
        with self.assertRaises(GameError):
            j.act('sl_mix', kind='color', shade='dye_6_1', dev=20, ratio='1:1')   # bowl busy
        with self.assertRaises(GameError):
            j.act('sl_dump')                                                    # needs confirm
        j.act('sl_dump', confirm=True)
        self.assertIsNone(j.task['bowl'])
        self.assertEqual(j.c['life']['waste'][-1]['item'], 'bowl')
        self.assertEqual(j.c['ext']['data']['dumped'], 1)
        j.act('sl_mix', kind='color', shade='dye_6_1', dev=40, ratio='1:1')
        with self.assertRaises(GameError):
            j.act('sl_apply')   # 40 vol never on the scalp
        self.roundtrip()

    def test_wash_before_colour_is_a_mistake(self):
        j = self.office_to_plan()
        j.act('sl_wash')
        self.assertIn('wet_color', j.task['flags'])
        self.assertEqual(j.task['mistakes'], 1)

    # ---------------------------------------------------------------- safety stops
    def test_patch_test_referral_and_next_day_record(self):
        j = self.journey(T_GRAY)
        tid = j.task['id']
        j.act('ask')
        j.act('sl_consult', topic='patch')
        self.assertEqual(j.task['patch_record'], 'none')
        j.act('sl_plan', services=['color', 'cut'], sessions=1)
        r = j.act('sl_mix', kind='color', shade='dye_5_0', dev=20, ratio='1:1')
        self.assertTrue(r.get('refused'))
        self.assertIn('no_patch', j.task['flags'])
        self.assertEqual(j.task['plan']['services'], ['cut'])   # colour struck out, cut kept
        self.assertEqual(j.task['quote'], 30)
        j.act('sl_patch')
        self.assertTrue(j.task['patch_done'])
        self.assertEqual(j.c['ext']['data']['patch_log'][j.task['npc']], j.c['day'])
        r = j.act('sl_plan', services=['color', 'cut'], sessions=1)
        self.assertTrue(r.get('refused'))
        j.act('sl_wash')
        j.act('sl_cut', step='section')
        j.act('sl_cut', step='guide', length=1)
        r = j.act('sl_cut', step='check')
        self.assertIn('tầng', r['message'])     # layers still missing
        j.act('sl_cut', step='layers')
        j.act('sl_cut', step='check')
        j.act('sl_checkout', products=[], confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.roundtrip()
        # The salon log counts as a record from the next game day on.
        c = j.c
        self.assertTrue(S._has_record(dict(c, day=c['day'] + 1), t))
        self.assertFalse(S._has_record(c, t))

    def test_patch_only_client_is_referred(self):
        tpl = S.JOB2_INDEX['c_grey']
        saved = tpl['services']
        tpl['services'] = ['color']      # a colour-only visit (template patched for this test only)
        try:
            j = self.journey(T_GRAY)
            tid = j.task['id']
            j.act('ask')
            money = j.c['money']
            r = j.act('sl_patch')
            self.assertTrue(r.get('celebrate'))
            t = j.get(tid)
            self.assertEqual(t['status'], 'referred')
            self.assertEqual(j.c['money'], money + S.PRICES['patch'] + S.SPEC['tip'])
            crit = {x['key']: x['score'] for x in self.review(tid)['feedback']['criteria']}
            self.assertEqual(crit['care'], 5)
            self.roundtrip()
        finally:
            tpl['services'] = saved

    def test_patch_not_needed_without_colour(self):
        j = self.journey(T_UNDERCUT)
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('sl_patch')
        with self.assertRaises(GameError):
            j.act('sl_strand')

    def test_scratched_scalp_stops_colour(self):
        j = self.journey(T_RED)
        tid = j.task['id']
        j.act('ask')
        j.act('sl_consult', topic='patch')
        j.act('sl_inspect', zone='scalp')
        j.act('sl_plan', services=['style'], sessions=1)         # colour postponed with a reason
        self.assertEqual(j.task['quote'], 15)
        j.act('sl_wash')
        j.act('sl_style', finish='volume')
        j.act('sl_checkout', products=[], confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')

    def test_scratched_scalp_safety_stop_on_mix(self):
        j = self.journey(T_RED)
        j.act('ask')
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        r = j.act('sl_mix', kind='color', shade='dye_4_6', dev=10, ratio='1:1')
        self.assertTrue(r.get('refused'))
        self.assertIn('scalp_stop', j.task['flags'])
        self.assertEqual(j.task['plan']['services'], ['style'])
        self.assertEqual(kit.stock(j.c, 'dye_4_6'), 4)   # nothing opened

    # ---------------------------------------------------------------- cutting & finish
    def test_cut_too_short_is_irreversible(self):
        j = self.journey(T_KID)
        tid = j.task['id']
        j.act('ask')
        j.act('sl_plan', services=['cut'], sessions=1)
        j.act('sl_wash')
        with self.assertRaises(GameError):
            j.act('sl_cut', step='guide', length=2)   # section first
        j.act('sl_cut', step='section')
        j.act('sl_cut', step='guide', length=4)
        self.assertTrue(j.task['cut']['short'])
        self.assertEqual(j.task['mistakes'], 1)
        j.act('sl_cut', step='check')
        j.act('sl_checkout', products=[], confirm=True)
        post = self.review(tid)
        crit = {x['key']: x['score'] for x in post['feedback']['criteria']}
        self.assertLessEqual(crit['accuracy'], 3)

    def test_pushy_upsell_is_declined(self):
        j = self.journey(T_UNDERCUT)
        tid = j.task['id']
        j.act('ask')
        j.act('sl_consult', topic='length')
        j.act('sl_consult', topic='lifestyle')
        j.act('sl_plan', services=['cut', 'style'], sessions=1)
        j.act('sl_wash')
        j.act('sl_cut', step='section')
        j.act('sl_cut', step='guide', length=6)
        j.act('sl_cut', step='check')
        with self.assertRaises(GameError):
            j.act('sl_style', finish='glitter')
        j.act('sl_style', finish='natural')
        stock = kit.stock(j.c, 'rt_mask')
        j.act('sl_checkout', products=['rt_mask'], confirm=True)
        t = j.get(tid)
        self.assertEqual(t['declined'], ['rt_mask'])
        self.assertIn('pushy', t['flags'])
        self.assertEqual(kit.stock(j.c, 'rt_mask'), stock)
        crit = {x['key']: x['score'] for x in self.review(tid)['feedback']['criteria']}
        self.assertEqual(crit['attitude'], 4)

    def test_mc_treatment_style(self):
        j = self.journey(T_MC)
        tid = j.task['id']
        j.act('ask')
        j.act('sl_consult', topic='history')
        j.act('sl_inspect', zone='ends')
        j.act('sl_plan', services=['treatment', 'style'], sessions=1)
        with self.assertRaises(GameError):
            j.act('sl_style', finish='volume')   # not washed
        j.act('sl_wash')
        with self.assertRaises(GameError):
            j.act('sl_style', finish='volume')   # treatment first
        j.act('sl_treat')
        j.act('sl_style', finish='volume')
        j.act('sl_checkout', products=['rt_heat'], confirm=True)
        t = j.get(tid)
        self.assertEqual(t['mistakes'], 0)
        self.assertEqual(self.review(tid)['stars'], 5)

    # ---------------------------------------------------------------- persistence & tampering
    def test_tampered_save_rejected(self):
        j = self.office_to_plan()
        for mutate in (lambda t: t['_key'].update(budget=9999), lambda t: t['needs'].update(services=['cut']),
                       lambda t: t['plan'].update(services=['color', 'cut', 'style', 'bleach']),
                       lambda t: t.update(bowl=dict(kind='color', shade='dye_x', dev=20, ratio='1:1', cost=0, ok=True)),
                       lambda t: t['cut'].update(removed=-3), lambda t: t.update(done=['bleach'])):
            state = copy.deepcopy(j.state)
            mutate(state['careers']['salon']['tasks'][0])
            with self.assertRaises(GameError):
                validate_state(state)
        state = copy.deepcopy(j.state)
        state['careers']['salon']['ext']['data']['patch_log'] = {'stranger': 1}
        with self.assertRaises(GameError):
            validate_state(state)

    def test_sanitize_once_per_day(self):
        j = self.journey(T_OFFICE)
        j.act('sl_sanitize')
        with self.assertRaises(GameError):
            j.act('sl_sanitize')
        self.assertTrue(public_state(j.state)['careers']['salon']['data']['sanitized_today'])

    def test_content_and_spec(self):
        cc = S.content()
        self.assertEqual(len(cc['levels']), 10)
        self.assertIn('disclaimer', cc)
        self.assertTrue(5 <= len(S.SITUATIONS) <= 8)
        for x in S.SITUATIONS:
            for o in x['options']:
                self.assertGreaterEqual(len(o['perspectives']), 2)
        for x in S.CLIENTS:
            base = sum(S.PRICES[k] for k in x['services'])
            self.assertLessEqual(base * 1.25, x['key']['budget'], x['title'])

    def test_situations_playable(self):
        j = Journey('salon')
        for sit in S.SITUATIONS:
            j.act('sit_practice', script=sit['id'])
            for f in sit['facts']:
                j.act('sit_read', fact=f['id'])
            good = next(o for o in sit['options'] if o['quality'] == 'good')
            j.act('sit_choose', option=good['id'])
            j.act('sit_confirm', confirm=True)
            j.act('sit_dismiss')
        validate_state(json.loads(json.dumps(j.state)))

    def test_full_day_journey(self):
        j = Journey('salon')
        self.assertEqual(len([t for t in j.c['tasks'] if t['career'] == 'salon']), 3)
        self.assertEqual(len({t['title'] for t in j.c['tasks']}), 3)
        validate_state(json.loads(json.dumps(j.state)))


# ==================================================================== v0.5
def slot_for(pred, days=range(1, 45), slots=10):
    for day in days:
        for slot in range(slots):
            t = S.make_task(day, slot, 1)
            if pred(t):
                return day, slot
    raise AssertionError('no task matches')


def case_of(case, pred=lambda t: True, days=range(1, 45)):
    return slot_for(lambda t: t['needs'].get('case') == case and pred(t), days)


def crit(j, tid):
    post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p.get('source') == tid)
    return {x['key']: x for x in post['feedback']['criteria']}


class SalonV2Tests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def at(self, day, slot):
        self.j = Journey('salon', slot=slot, day=day)
        return self.j

    def view(self, j=None):
        j = j or self.j
        return next(v for v in public_state(j.state)['careers']['salon']['tasks'] if v['id'] == j.task['id'])

    def ok(self):
        validate_state(json.loads(json.dumps(self.j.state)))

    def colour_rinse(self, secs=14, **mix):
        j = self.j
        j.act('sl_mix', kind='color', **mix)
        j.act('sl_apply')
        self.clock.t += secs
        return j.act('sl_rinse')

    # ---------------------------------------------------------------- saves & generator
    def test_old_save_keeps_old_clients_and_gains_new_fields(self):
        day, slot = find(T_OFFICE)
        j = self.at(day, slot)
        s = copy.deepcopy(j.state)
        c = s['careers']['salon']
        old = S._make_v1(1, 0, 5)          # the office client, made by the first generator
        self.assertEqual(old['title'], S._make_v1(1, 0, 5)['title'])
        c['tasks'] = [old]
        c['active_task'] = old['id']
        c['day'] = 1
        d = c['ext']['data']
        for k in list(d):
            if k not in ('served', 'dumped', 'sanitize_day', 'patch_log'):
                d.pop(k)
        validate_state(s)                 # migrates in place, like loading an old save
        t = c['tasks'][0]
        self.assertGreaterEqual(t['created_turn'], kit.LEGACY_TURN)
        self.assertNotIn('gen', t)
        self.assertEqual(S.make_task(1, 0, t['created_turn']), S._make_v1(1, 0, t['created_turn']))
        self.assertIn('desk', d)
        self.assertEqual(d['allergy'], {})
        validate_state(json.loads(json.dumps(s)))    # idempotent
        j.state = s
        j.act('ask')
        if 'color' in t['needs']['services'] and t['_hair']['patch']:
            want = t['_key']['color']
            j.act('sl_consult', topic='history')
            j.act('sl_plan', services=list(t['needs']['services']), sessions=t['_key']['sessions'])
            j.act('sl_mix', kind='color', shade=want['shade'], dev=want['dev'], ratio=want['ratio'], shade2='dye_3_0', parts=[1, 1])
            self.assertTrue(j.task['bowl']['ok'])       # old clients keep the exact-tube rule; extra mix fields are ignored
            self.assertNotIn('mix', j.task['bowl'])
        self.ok()

    def test_luck_of_the_day_is_stable_and_shown(self):
        self.assertEqual(S.today(1)['id'], 'steady')
        for day in range(2, 40):
            self.assertNotEqual(S.today(day)['id'], S.today(day - 1)['id'])
        self.assertGreaterEqual(len({S.today(d)['id'] for d in range(1, 40)}), 5)
        j = Journey('salon')
        self.assertEqual(j.c['ext']['data']['today'], dict(id='steady', day=1))
        view = public_state(j.state)['careers']['salon']['data']
        self.assertEqual(view['today']['title'], S.TODAY_INDEX['steady']['title'])
        self.assertIsNone(view['desk']['ev'])
        self.assertIsInstance(view['allergy'], int)          # only a count leaves the server

    def test_no_client_twice_a_day_or_back_the_next_morning(self):
        prev = []
        for day in range(1, 121):
            n = 5 if day == 1 else 6                                       # day one only has five everyday clients
            tasks = [S.make_task(day, slot, 1) for slot in range(n)]
            self.assertEqual(len({t['npc'] for t in tasks}), n, day)
            titles = [t['title'] for t in tasks]
            self.assertEqual(len(set(titles)), n, day)
            self.assertFalse(set(titles[:3]) & set(prev), day)
            prev = titles[:3]
        self.assertEqual(S.make_task(40, 2, 1), S.make_task(40, 2, 1))     # still a pure function of (day, slot)
        self.assertEqual(S.make_task(3, 20, 1)['career'], 'salon')          # extra slots past the plan still work

    def test_every_special_case_appears_and_day_one_is_gentle(self):
        for case in S.CASES:
            day, slot = case_of(case)
            self.assertGreaterEqual(day, 2, case)
            self.assertGreater(slot, 0, case)                  # the first client of a day is an everyday one
        for slot in range(5):
            self.assertIsNone(S.make_task(1, slot, 1)['needs']['case'])
        # Harder days bring more special clients and shorter rush deadlines.
        share = lambda days: sum(bool(S.make_task(d, k, 1)['needs']['case']) for d in days for k in range(1, 4)) / len(days)
        self.assertGreater(share(range(10, 40)), share(range(2, 6)))
        early = S.make_task(*case_of('walkin', days=range(2, 6)), 1)['needs']['rush']['steps']
        late = S.make_task(*case_of('walkin', days=range(12, 60)), 1)['needs']['rush']['steps']
        self.assertLess(late, early)

    def test_patience_starts_lower_on_busy_later_days(self):
        day, slot = slot_for(lambda t: not t['needs']['case'] and kit.tier(t['day']) == 3 and S.today(t['day'])['id'] == 'walkin')
        j = self.at(day, slot)
        self.assertEqual(j.task['patience'], 100 - 12 - 8)

    # ---------------------------------------------------------------- the mixing bowl
    def test_two_tube_mix_hits_an_in_between_shade(self):
        j = self.at(*slot_for(lambda t: t['title'] == 'Nâu socola ấm cho mùa tiệc'))
        tid = j.task['id']
        j.act('ask')
        for topic in ('history', 'patch'):
            j.act('sl_consult', topic=topic)
        j.act('sl_inspect', zone='roots')
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        for bad in (dict(shade='dye_3_0', shade2='dye_3_0', parts=[1, 1]), dict(shade='dye_3_0', shade2='dye_7_3', parts=[0, 1]),
                    dict(shade='dye_3_0', shade2='dye_7_3', parts=[4, 1]), dict(shade='dye_3_0', shade2='dye_7_3', parts=[True, 1]),
                    dict(shade='dye_3_0', shade2='dye_7_3'), dict(shade='dye_3_0', parts=[1, 2]), dict(shade='dye_3_0', shade2='dye_9_9', parts=[1, 1])):
            with self.assertRaises(GameError, msg=str(bad)):
                j.act('sl_mix', kind='color', dev=20, ratio='1:1', **bad)
        # One tube of 5.0 is the right level but not the warm tone in the photo.
        r = j.act('sl_mix', kind='color', shade='dye_5_0', dev=20, ratio='1:1')
        self.assertFalse(j.task['bowl']['ok'])
        self.assertFalse(j.task['bowl']['hit'])
        self.assertIn('Ấm', r['message'])
        self.assertEqual(j.task['mistakes'], 1)
        j.act('sl_dump', confirm=True)
        a, b = kit.stock(j.c, 'dye_3_0'), kit.stock(j.c, 'dye_7_3')
        r = j.act('sl_mix', kind='color', shade='dye_3_0', shade2='dye_7_3', parts=[1, 1], dev=20, ratio='1:1')
        self.assertTrue(j.task['bowl']['ok'] and j.task['bowl']['hit'], r['message'])
        self.assertEqual((kit.stock(j.c, 'dye_3_0'), kit.stock(j.c, 'dye_7_3')), (a - 1, b - 1))
        self.assertIn('level 5', r['message'])
        j.act('sl_apply')
        self.clock.t += 14
        j.act('sl_rinse')
        self.assertEqual(j.task['results']['color']['mix'], dict(b='dye_7_3', pa=1, pb=1))
        v = self.view()
        self.assertEqual((v['mix_result']['level'], v['mix_result']['band']), ('5', 'warm'))
        self.assertEqual(v['look']['level'], 5)
        self.assertEqual(j.c['ext']['data']['mixes'], 1)
        self.ok()
        j.act('sl_wash') if not j.task['washed'] else None
        j.act('sl_style', finish='volume')
        j.act('sl_checkout', products=[], confirm=True)
        c = crit(j, tid)
        self.assertEqual(c['accuracy']['score'], 5)          # the kept bowl matched the photo
        self.ok()

    def test_mix_maths_matches_the_bands(self):
        m = S._mix('dye_6_1', 'dye_8_1', 1, 1)
        self.assertEqual((m['lv'] / m['den'], m['band']), (7.0, 'ash'))
        self.assertEqual(S._mix('dye_5_0', 'dye_8_1', 1, 1)['band'], 'cool')
        self.assertEqual(S._mix('dye_7_3')['band'], 'deep')
        self.assertEqual(S._mix('dye_6_1', warm=1)['band'], 'natural')      # brassy base warms an ash tube to neutral
        self.assertTrue(S._level_ok(S._mix('dye_5_0', 'dye_4_6', 3, 1), 5))  # 4.75 is within a quarter
        self.assertFalse(S._level_ok(S._mix('dye_5_0', 'dye_7_3', 3, 1), 5))  # 5.5 is not
        self.assertEqual(S._blend([('#000000', 1), ('#ffffff', 1)]), '#808080')

    def test_every_colour_client_has_a_recipe(self):
        for jb in S.JOBS2:
            wants = [S._col(r['level'], r['tone'], 20) for r in S.PHOTO_REAL] if jb['case'] == 'photo' else [jb['k'].get('color')]
            for want in [w for w in wants if w]:
                warm = jb['hair'].get('warm', 0)
                hits = [(a, b, pa, pb) for a in S.DYE_INDEX for b in [None, *S.DYE_INDEX] if b != a
                        for pa in S.MIX_PARTS for pb in ((0,) if b is None else S.MIX_PARTS)
                        if S._level_ok(m := S._mix(a, b, pa, pb, warm), want['level']) and m['band'] == want['tone']
                        and (not want['grey'] or 2 * m['nat'] >= m['den'])]
                self.assertTrue(hits, jb['key'])
                lift = want['level'] - jb['hair']['level']
                self.assertLessEqual(lift, 2, jb['key'])
                self.assertEqual(want['dev'], 20 if lift >= 1 or want['grey'] or jb['key'] == 'c_grey' else 10, jb['key'])
            base = sum(S.PRICES[k] for k in jb['services'])
            self.assertLessEqual(base * 1.25, jb['k']['budget'], jb['key'])

    def test_heat_day_speeds_processing(self):
        j = self.at(*slot_for(lambda t: t['title'] == T_OFFICE and not t['needs']['case'] and S.today(t['day'])['id'] == 'heat'))
        j.act('ask')
        j.act('sl_plan', services=['color', 'cut', 'style'], sessions=1)
        j.act('sl_mix', kind='color', shade='dye_6_1', dev=20, ratio='1:1')
        r = j.act('sl_apply')
        self.assertTrue(j.task['timer']['fast'])
        self.assertIn('nóng', r['message'])
        self.assertEqual(self.view()['timer']['window'], dict(under=8, ideal=14, over=21))
        self.clock.t += 16                   # ideal on a normal day, over on a hot one
        j.act('sl_rinse')
        self.assertEqual(j.task['results']['color']['zone'], 'over')
        self.ok()

    # ---------------------------------------------------------------- special clients
    def test_filtered_photo_must_be_checked_before_promising(self):
        day, slot = case_of('photo')
        j = self.at(day, slot)
        real = j.task['_x']['real']
        j.act('ask')
        v = self.view()
        self.assertIsNone(v['real'])
        self.assertNotIn(real['text'], json.dumps(v))
        j.act('sl_consult', topic='history')
        j.act('sl_inspect', zone='roots')
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        self.assertFalse(j.task['plan']['informed'])
        self.assertIn('photo_blind', j.task['flags'])
        before = copy.deepcopy(j.state)
        r = j.act('sl_mix', kind='color', shade='dye_8_1', dev=20, ratio='1:1')   # chasing the filtered level 9 look
        self.assertIn('filter', r['message'])
        self.assertFalse(j.task['bowl']['ok'])
        j.state = before                                                         # look at the original photo instead
        r = j.act('sl_photo')
        self.assertIn(f'level {real["level"]}', r['message'])
        with self.assertRaises(GameError):
            j.act('sl_photo')
        self.assertEqual(self.view()['real']['level'], real['level'])
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        self.assertTrue(j.task['plan']['informed'])
        self.assertNotIn('photo_blind', j.task['flags'])
        recipe = dict(shade='dye_6_1', shade2='dye_8_1', parts=[1, 1]) if real['level'] == 7 else dict(shade='dye_5_0', shade2='dye_8_1', parts=[2, 1])
        self.colour_rinse(**recipe, dev=20, ratio='1:1')
        self.assertTrue(j.task['results']['color']['hit'])
        office = self.at(*find(T_OFFICE))
        office.act('ask')
        with self.assertRaises(GameError):
            office.act('sl_photo')                 # an ordinary photo needs no second look

    def test_stale_patch_record_reacts_and_goes_in_the_allergy_book(self):
        day, slot = case_of('react', lambda t: t['_x']['react'])
        j = self.at(day, slot)
        tid, npc = j.task['id'], j.task['npc']
        j.act('ask')
        j.act('sl_consult', topic='patch')
        self.assertEqual(j.task['patch_record'], 'none')                     # “last year, somewhere else” is no record
        j.act('sl_inspect', zone='scalp')
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        r = j.act('sl_patch')
        self.assertTrue(j.task['reacted'])
        self.assertIn('dị ứng', r['message'])
        d = j.c['ext']['data']
        self.assertEqual(d['allergy'], {npc: day})
        self.assertNotIn(npc, d['patch_log'])
        self.assertEqual(j.task['plan']['services'], ['style'])               # colour struck out, the rest re-quoted
        j.act('sl_wash')
        j.act('sl_style', finish='sleek')
        j.act('sl_checkout', products=[], confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertIn('dị ứng', crit(j, tid)['care']['note'])
        self.ok()
        # She comes back another day: the book still says no dye.
        day2, slot2 = case_of('react', days=range(day + 1, 60))
        t2 = S.make_task(day2, slot2, j.c['turn'])
        j.c['day'] = day2
        j.c['tasks'].append(t2)
        j.c['active_task'] = t2['id']
        self.ok()
        j.act('ask')
        j.act('sl_consult', topic='patch')
        self.assertEqual(j.task['patch_record'], 'allergy')
        self.assertIn('không nhuộm', self.view()['answers']['patch'])
        with self.assertRaises(GameError):
            j.act('sl_patch')
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        r = j.act('sl_mix', kind='color', shade='dye_5_0', dev=20, ratio='1:1')
        self.assertTrue(r.get('refused'))
        self.assertEqual(j.task['plan']['services'], ['style'])
        self.assertEqual(kit.stock(j.c, 'dye_5_0'), S.ITEM_INDEX['dye_5_0']['start'])   # nothing opened
        self.ok()

    def test_patch_test_without_reaction_books_colour_for_later(self):
        day, slot = case_of('react', lambda t: not t['_x']['react'])
        j = self.at(day, slot)
        j.act('ask')
        j.act('sl_patch')
        self.assertFalse(j.task['reacted'])
        self.assertEqual(j.c['ext']['data']['patch_log'], {j.task['npc']: day})
        self.assertEqual(j.c['ext']['data']['allergy'], {})

    def kid(self):
        day, slot = case_of('kid')
        j = self.at(day, slot)
        j.act('ask')
        self.assertNotIn(S.CALM_HINT[j.task['_x']['soothe']], json.dumps(self.view()))
        j.act('sl_consult', topic='length')
        r = j.act('sl_consult', topic='lifestyle')
        self.assertIn(S.CALM_HINT[j.task['_x']['soothe']], r['message'])
        j.act('sl_plan', services=['cut'], sessions=1)
        return j

    def test_wriggly_kid_slips_without_soothing(self):
        j = self.kid()
        tid, tier = j.task['id'], kit.tier(j.task['day'])
        calm = 55 - 5 * tier
        self.assertEqual(j.task['calm'], calm)
        j.act('sl_wash')
        self.assertEqual(j.task['calm'], calm - 8)
        j.act('sl_cut', step='section')
        calm -= 8 + 12 + 3 * tier
        self.assertEqual(j.task['calm'], calm)
        self.assertLess(calm, 40)
        slip = 2 if calm < 20 else 1
        r = j.act('sl_cut', step='guide', length=2)
        self.assertIn(f'lẹm thêm {slip} cm', r['message'])
        self.assertIn('slip', j.task['flags'])
        self.assertEqual(j.task['cut']['removed'], 2 + slip)
        j.act('sl_cut', step='check')
        j.act('sl_checkout', products=[], confirm=True)
        self.assertLess(crit(j, tid)['care']['score'], 5)
        self.assertEqual(j.c['ext']['data']['kids_calm'], 0)
        self.assertEqual(self.j.get(tid)['status'], 'completed')
        v = next(x for x in public_state(j.state)['careers']['salon']['tasks'] if x['id'] == tid)
        self.assertEqual(v['truth']['soothe'], j.get(tid)['_x']['soothe'])

    def test_wriggly_kid_calmed_the_right_way(self):
        j = self.kid()
        tid = j.task['id']
        best = j.task['_x']['soothe']
        other = next(x for x in S.CALM_IDS if x != best)
        j.act('sl_calm', tool=other)
        self.assertEqual(j.task['calm'], 55 - 5 * kit.tier(j.task['day']) + S.CALM_OTHER)
        with self.assertRaises(GameError):
            j.act('sl_calm', tool=other)
        with self.assertRaises(GameError):
            j.act('sl_calm', tool='candy')
        r = j.act('sl_calm', tool=best)
        self.assertTrue(r.get('celebrate'))
        j.act('sl_wash')
        j.act('sl_cut', step='section')
        j.act('sl_cut', step='guide', length=2)
        self.assertNotIn('slip', j.task['flags'])
        j.act('sl_cut', step='check')
        j.act('sl_checkout', products=[], confirm=True)
        self.assertEqual(j.c['ext']['data']['kids_calm'], 1)
        self.assertIn('dỗ bé', crit(j, tid)['attitude']['note'])
        su = self.at(*find(T_KID))                 # an everyday kid's cut has no calm meter
        su.act('ask')
        self.assertIsNone(su.task['calm'])
        with self.assertRaises(GameError):
            su.act('sl_calm', tool=best)

    def bride(self):
        day, slot = case_of('bride')
        j = self.at(day, slot)
        j.act('ask')
        j.act('sl_consult', topic='history')
        j.act('sl_inspect', zone='lengths')
        j.act('sl_plan', services=['treatment', 'style'], sessions=1)
        j.act('sl_wash')
        j.act('sl_treat')
        return j

    def test_bride_updo_on_time_earns_the_rush_bonus(self):
        j = self.bride()
        tid, n = j.task['id'], j.task['needs']
        self.assertEqual(self.view()['due_turn'], j.task['created_turn'] + n['rush']['steps'])
        j.act('sl_style', finish='updo')
        self.assertNotIn('finish_wrong', j.task['flags'])
        money = j.c['money']
        r = j.act('sl_checkout', products=[], confirm=True)
        self.assertIn('Kịp giờ', r['message'])
        self.assertEqual(j.c['ext']['data']['rush_on_time'], 1)
        self.assertEqual(j.c['money'], money + j.get(tid)['quote'] + n['rush']['bonus'] + S.SPEC['tip'])
        self.assertEqual(crit(j, tid)['speed']['score'], 5)
        self.ok()

    def test_bride_late_or_wrong_style_loses_out(self):
        j = self.bride()
        tid = j.task['id']
        j.act('sl_style', finish='volume')
        self.assertIn('finish_wrong', j.task['flags'])
        j.c['turn'] += 40
        money = j.c['money']
        r = j.act('sl_checkout', products=[], confirm=True)
        if j.get(tid)['status'] == 'in_progress':          # the bride asks for the style to be redone (consequences)
            self.assertEqual(j.get(tid)['reaction']['kind'], 'remake')
            self.assertNotIn('style', j.get(tid)['done'])
            j.act('sl_style', finish='volume')             # …and gets the wrong one again
            r = j.act('sl_checkout', products=[], confirm=True)
        self.assertIn('Trễ hẹn', r['message'])
        self.assertLessEqual(j.c['money'] - money, j.get(tid)['quote'] + S.SPEC['tip'])   # no rush bonus
        c = crit(j, tid)
        self.assertEqual(c['speed']['score'], 2)
        self.assertLess(c['accuracy']['score'], 5)

    def test_grey_coverage_needs_a_natural_base(self):
        j = self.at(*case_of('grey'))
        tid = j.task['id']
        j.act('ask')
        j.act('sl_consult', topic='history')
        r = j.act('sl_inspect', zone='roots')
        self.assertIn('nền tự nhiên', r['message'])
        self.assertEqual(self.view()['grey'], 60)
        j.act('sl_plan', services=['color', 'cut'], sessions=1)
        r = j.act('sl_mix', kind='color', shade='dye_4_6', shade2='dye_6_1', parts=[1, 1], dev=20, ratio='1:1')
        self.assertTrue(j.task['bowl']['hit'])            # right level and tone…
        self.assertFalse(j.task['bowl']['ok'])            # …but the grey would still show
        self.assertIn('nền tự nhiên', r['message'])
        j.act('sl_apply')
        self.clock.t += 14
        r = j.act('sl_rinse')
        self.assertIn('grey_show', j.task['flags'])
        self.assertIn('bạc', r['message'])
        j.act('sl_cut', step='section')
        j.act('sl_cut', step='guide', length=1)
        j.act('sl_cut', step='check')
        j.act('sl_checkout', products=[], confirm=True)
        self.assertIn('tóc bạc còn lộ', crit(j, tid)['accuracy']['note'])

    def test_grey_coverage_done_right(self):
        j = self.at(*case_of('grey'))
        j.act('ask')
        j.act('sl_plan', services=['color', 'cut'], sessions=1)
        self.colour_rinse(shade='dye_3_0', shade2='dye_7_3', parts=[1, 1], dev=20, ratio='1:1')
        self.assertTrue(j.task['results']['color']['ok'])
        self.assertNotIn('grey_show', j.task['flags'])

    def test_brassy_correction_counts_the_orange_base(self):
        j = self.at(*case_of('fix'))
        j.act('ask')
        j.act('sl_consult', topic='history')
        j.act('sl_plan', services=['color', 'treatment'], sessions=1)
        self.assertIsNone(self.view()['base_warm'])
        r = j.act('sl_mix', kind='color', shade='dye_5_0', shade2='dye_8_1', parts=[3, 1], dev=10, ratio='1:1')
        self.assertFalse(j.task['bowl']['hit'])
        self.assertIn('cam', r['message'])               # Linh points at the brassy lengths
        j.act('sl_dump', confirm=True)
        j.act('sl_inspect', zone='lengths')
        self.assertEqual(self.view()['base_warm'], 1)
        self.colour_rinse(shade='dye_6_1', dev=10, ratio='1:1')
        self.assertTrue(j.task['results']['color']['ok'])
        self.assertEqual(self.view()['mix_result']['band'], 'natural')
        self.ok()

    def test_walkin_rush_is_short_and_tampering_is_caught(self):
        j = self.at(*case_of('walkin'))
        self.assertLessEqual(j.task['needs']['rush']['steps'], 11)
        self.assertLessEqual(j.task['patience'], 94)
        j.act('ask')
        for mutate in (lambda t: t.update(calm=50), lambda t: t.update(photo_seen=True), lambda t: t.update(reacted=True),
                       lambda t: t.update(soothed=['toy']), lambda t: t['_x'].update(react=True),
                       lambda t: t['needs']['rush'].update(bonus=99)):
            state = copy.deepcopy(j.state)
            mutate(state['careers']['salon']['tasks'][0])
            with self.assertRaises(GameError):
                validate_state(state)
        state = copy.deepcopy(j.state)
        state['careers']['salon']['ext']['data']['allergy'] = {'stranger': 2}
        with self.assertRaises(GameError):
            validate_state(state)

    def test_bowl_tampering_is_caught(self):
        j = self.at(*slot_for(lambda t: t['title'] == 'Nâu socola ấm cho mùa tiệc'))
        j.act('ask')
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        j.act('sl_mix', kind='color', shade='dye_3_0', shade2='dye_7_3', parts=[1, 1], dev=20, ratio='1:1')
        self.ok()
        for mutate in (lambda b: b['mix'].update(pb=5), lambda b: b['mix'].update(b='dye_3_0'), lambda b: b.update(hit='yes'),
                       lambda b: b['mix'].update(b=None), lambda b: b.pop('hit')):
            state = copy.deepcopy(j.state)
            mutate(state['careers']['salon']['tasks'][0]['bowl'])
            with self.assertRaises(GameError):
                validate_state(state)

    # ---------------------------------------------------------------- surprises at the desk
    def desk_day(self):
        day, slot = slot_for(lambda t: t['title'] == T_OFFICE and not t['needs']['case'], days=range(2, 4))
        j = self.at(day, slot)
        self.assertEqual(kit.desk_plan('salon', day)[0], 2)
        return j

    def test_desk_event_blocks_work_but_never_the_rinse(self):
        self.assertEqual(kit.desk_plan('salon', 1), [])
        j = self.desk_day()
        j.act('ask')
        j.act('sl_plan', services=['color', 'cut', 'style'], sessions=1)
        j.act('sl_mix', kind='color', shade='dye_6_1', dev=20, ratio='1:1')
        j.c['day_completed'] = 2                  # two clients already served today
        r = j.act('sl_apply')
        self.assertTrue(r.get('surprise'), r)
        desk = j.c['ext']['data']['desk']
        self.assertIsNotNone(desk['ev'])
        with self.assertRaises(GameError) as ctx:
            j.act('sl_consult', topic='budget')
        self.assertEqual(ctx.exception.code, 'surprise_open')
        with self.assertRaises(GameError):
            j.act('sl_sanitize')
        view = public_state(j.state)['careers']['salon']['data']['desk']
        self.assertEqual(view['ev']['script'], desk['ev']['script'])
        self.assertNotIn('luck', json.dumps(view))
        self.assertNotIn('effects', json.dumps(view))
        self.clock.t += 14
        j.act('sl_rinse')                          # the timer does not wait for the counter
        self.assertEqual(j.task['results']['color']['zone'], 'ideal')
        with self.assertRaises(GameError):
            j.act('sl_desk', option='nope')
        turn = j.c['turn']
        script = S.DESK_INDEX[desk['ev']['script']]
        j.act('sl_desk', option=script['default'])
        self.assertEqual(j.c['turn'], turn)        # deciding at the counter costs no step
        self.assertIsNone(j.c['ext']['data']['desk']['ev'])
        j.act('sl_cut', step='section')
        self.ok()

    def test_desk_options_are_shown_in_a_shuffled_order(self):
        j = self.desk_day()
        spots = set()
        for x in S.DESK:
            j.c['ext']['data']['desk']['ev'] = dict(id='desk-99', script=x['id'], day=j.c['day'], at='between')
            shown = public_state(j.state)['careers']['salon']['data']['desk']['ev']['options']
            self.assertEqual(sorted(o['id'] for o in shown), sorted(o['id'] for o in x['options']), x['id'])
            again = public_state(j.state)['careers']['salon']['data']['desk']['ev']['options']
            self.assertEqual([o['id'] for o in shown], [o['id'] for o in again], x['id'])
            good = [o['id'] for o in x['options'] if o.get('good')]
            if good:
                spots.add([o['id'] for o in shown].index(good[0]))
        self.assertGreater(len(spots), 1, 'the careful answer always sits in the same place')
        j.c['ext']['data']['desk']['ev'] = None

    def test_every_desk_option_applies_cleanly(self):
        j = self.desk_day()
        base = j.state
        self.assertGreaterEqual(len(S.DESK), 8)
        for x in S.DESK:
            self.assertGreaterEqual(len(x['options']), 2, x['id'])
            self.assertIn(x['default'], [o['id'] for o in x['options']])
            self.assertTrue(any(o.get('good') or (o.get('luck') and o['luck']['win'].get('good')) for o in x['options']), x['id'])
            for o in x['options']:
                j.state = copy.deepcopy(base)
                j.c['ext']['data']['desk']['ev'] = dict(id='desk-99', script=x['id'], day=j.c['day'], at='between')
                validate_state(j.state)
                r = j.act('sl_desk', option=o['id'])
                self.assertTrue(r['message'], (x['id'], o['id']))
                self.assertEqual(j.c['ext']['data']['desk']['last']['outcome'], r['message'])
                validate_state(json.loads(json.dumps(j.state)))
        j.state = base

    def test_health_inspection_reads_the_sanitation_log(self):
        j = self.desk_day()
        base = copy.deepcopy(j.state)
        desk = lambda: j.c['ext']['data']['desk']
        desk()['ev'] = dict(id='desk-99', script='health', day=j.c['day'], at='between')
        money = j.c['money']
        r = j.act('sl_desk', option='show')
        self.assertIn('phạt 15', r['message'])
        self.assertEqual(j.c['money'], money - 15)
        j.state = copy.deepcopy(base)
        j.act('sl_sanitize')
        desk()['ev'] = dict(id='desk-98', script='health', day=j.c['day'], at='between')
        xp, money = j.c['xp'], j.c['money']
        r = j.act('sl_desk', option='show')
        self.assertIn('đạt', r['message'])
        self.assertEqual((j.c['xp'], j.c['money']), (xp + 10, money))
        j.state = copy.deepcopy(base)
        desk()['ev'] = dict(id='desk-97', script='health', day=j.c['day'], at='between')
        j.act('sl_desk', option='clean')
        self.assertEqual(j.c['ext']['data']['sanitize_day'], j.c['day'])
        with self.assertRaises(GameError):
            j.act('sl_sanitize')                   # already done in front of the inspectors

    def test_choices_leave_marks_that_change_later_surprises(self):
        j = self.desk_day()
        j.c['day'] = 6
        pool = lambda: {x['id'] for x in kit._desk_pool('salon', j.c, j.c['ext']['data']['desk'], S.DESK, 'between', 'steady')}

        class D:                                   # the state object is replaced after every action
            def __getitem__(_, k):
                return j.c['ext']['data'][k]
        d = D()
        self.assertIn('price_review', pool())
        d['desk']['ev'] = dict(id='desk-99', script='price_review', day=6, at='between')
        j.act('sl_desk', option='reply')
        self.assertIn('price_board', d['desk']['marks'])
        self.assertFalse({'price_review', 'price_again'} & pool())
        d['desk']['ev'] = dict(id='desk-98', script='staff_fight', day=6, at='between')
        j.act('sl_desk', option='side')
        self.assertIn('quit', pool())
        self.assertNotIn('staff_fight', pool())
        d['desk']['ev'] = dict(id='desk-97', script='quit', day=6, at='between')
        j.act('sl_desk', option='talk')
        self.assertNotIn('grudge', d['desk']['marks'])
        d['desk']['ev'] = dict(id='desk-96', script='recall', day=6, at='between')
        j.act('sl_desk', option='keep')
        self.assertIn('itch', pool())
        self.assertNotIn('leak', pool())           # the leaking roof only on rainy days
        self.ok()

    def test_undecided_surprise_takes_default_at_closing(self):
        j = Journey('salon')
        j.c['ext']['data']['desk']['ev'] = dict(id='desk-99', script='ring', day=1, at='between')
        r = j.act('end_day')
        lines = r['summary']['career']['lines']
        self.assertTrue(any('Nhẫn' in x for x in lines), lines)
        self.assertIn(S.today(j.c['day'])['title'], lines[-1])            # closing moved to the next day: its forecast ends the notebook
        last = j.c['ext']['data']['desk']['last']
        self.assertEqual((last['choice'], last['auto']), ('box', True))
        self.assertIsNone(j.c['ext']['data']['desk']['ev'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_text_never_assumes_the_stylists_gender(self):
        import re
        texts = json.dumps([S.JOBS2, S.DESK, S.SITUATIONS, S.SPEC['stories'], S.CALM_HINT, S.PHOTO_REAL], ensure_ascii=False)
        for bad in ('Chị chủ', 'chị chủ', 'anh chủ', 'cô chủ', 'Chị thợ', 'Chị ơi em', 'nè chị', 'Chú xịt'):
            self.assertNotIn(bad, texts)
        self.assertFalse(re.search(r'trong game|của game|người chơi|NPC', texts))


# ==================================================================== doing it wrong costs, in proportion
from game import consequences as cq


class SalonConsequenceTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.old = kit.clock
        kit.clock = self.clock

    def tearDown(self):
        kit.clock = self.old

    def office(self, shade='dye_6_1', secs=14, guide=3, layers=False, finish='sleek', products=('rt_colorsafe',)):
        """The office client end to end; each argument can be set wrong on purpose."""
        self.j = j = Journey('salon', slot=find(T_OFFICE)[1], day=find(T_OFFICE)[0])
        tid = j.task['id']
        j.act('ask')
        for topic in ('history', 'patch', 'length', 'budget'):
            j.act('sl_consult', topic=topic)
        j.act('sl_inspect', zone='ends')
        j.act('sl_plan', services=['color', 'cut', 'style'], sessions=1)
        j.act('sl_mix', kind='color', shade=shade, dev=20, ratio='1:1')
        j.act('sl_apply')
        self.clock.t += secs
        j.act('sl_rinse')
        j.act('sl_cut', step='section')
        j.act('sl_cut', step='guide', length=guide)
        if layers:
            j.act('sl_cut', step='layers')
        j.act('sl_cut', step='check')
        j.act('sl_style', finish=finish)
        self.money = j.c['money']
        self.r = j.act('sl_checkout', products=list(products), confirm=True)
        return tid

    def choco(self, **mix):
        self.j = j = Journey('salon', *reversed(slot_for(lambda t: t['title'] == 'Nâu socola ấm cho mùa tiệc')))
        tid = j.task['id']
        j.act('ask')
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        j.act('sl_mix', kind='color', dev=20, ratio='1:1', **mix)
        j.act('sl_apply')
        self.clock.t += 14
        j.act('sl_rinse')
        j.act('sl_style', finish='volume')
        self.money = j.c['money']
        self.r = j.act('sl_checkout', products=[], confirm=True)
        return tid

    def stars(self, tid):
        return next(p for p in self.j.c['feed'] if p['kind'] == 'review' and p.get('source') == tid)['stars']

    def review(self, tid):
        return next(p for p in self.j.c['feed'] if p['kind'] == 'review' and p.get('source') == tid)['text']

    def test_right_work_full_pay_no_slips(self):
        tid = self.office()
        t = self.j.get(tid)
        self.assertEqual(cq.slips(t), [])
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertGreaterEqual(self.stars(tid), 4)
        self.assertEqual(self.j.c['money'] - self.money, 105 + 25 + S.SPEC['tip'])

    def test_wrong_colour_costs_stars_and_money(self):
        tid = self.office(shade='dye_4_6')                 # wine red instead of a cool ash brown
        t = self.j.get(tid)
        self.assertEqual([x['code'] for x in cq.slips(t)], ['colour'])
        self.assertEqual(cq.slips(t)[0]['sev'], 3)
        self.assertLessEqual(self.stars(tid), 3)
        self.assertIn('nhuộm ra màu khác hẳn', self.review(tid))
        self.assertIn(t['reaction']['kind'], ('discount', 'refund', 'walkout'))
        self.assertGreater(t['reaction']['cut'], 0)
        self.assertLess(self.j.c['money'] - self.money, 105 + 25)
        validate_state(json.loads(json.dumps(self.j.state)))

    def test_severity_scales(self):
        small = self.choco(shade='dye_5_0')                # right level, one tone band cooler
        t = self.j.get(small)
        self.assertEqual([(x['code'], x['sev']) for x in cq.slips(t)], [('colour', 1)])
        self.assertIn('lạnh hơn', cq.slips(t)[0]['text'])
        s1 = self.stars(small)
        big = self.office(shade='dye_4_6')
        self.assertGreater(s1, self.stars(big))
        a = self.office(guide=5)                            # one centimetre over
        sev_a, st_a = cq.slips(self.j.get(a))[0]['sev'], self.stars(a)
        b = self.office(guide=9)                            # five centimetres over
        sev_b, st_b = cq.slips(self.j.get(b))[0]['sev'], self.stars(b)
        self.assertEqual((sev_a, sev_b), (1, 3))
        self.assertGreater(st_a, st_b)
        self.assertIn('9 phân', self.review(b))

    def test_processing_and_cut_slips_name_the_mistake(self):
        for kw, code in ((dict(secs=5), 'color_under'), (dict(secs=40), 'color_damage'), (dict(layers=True), 'layers')):
            tid = self.office(**kw)
            t = self.j.get(tid)
            self.assertEqual([x['code'] for x in cq.slips(t)], [code], kw)
            self.assertLessEqual(self.stars(tid), 3, kw)
            self.assertNotEqual(t['reaction']['kind'], 'accept', kw)

    def test_dye_without_patch_test_is_refused_and_inspected(self):
        day, slot = find(T_GRAY)
        self.j = j = Journey('salon', slot=slot, day=day)
        tid = j.task['id']
        j.act('ask')
        j.act('sl_plan', services=['color', 'cut'], sessions=1)
        r = j.act('sl_mix', kind='color', shade='dye_5_0', dev=20, ratio='1:1')
        self.assertTrue(r.get('refused'))                  # Linh still stops the first try
        j.act('sl_plan', services=['color', 'cut'], sessions=1)
        r = j.act('sl_mix', kind='color', shade='dye_5_0', dev=20, ratio='1:1')
        self.assertFalse(r.get('refused'))
        self.assertIn('dye_no_patch', j.task['flags'])
        j.act('sl_apply')
        self.clock.t += 14
        j.act('sl_rinse')
        j.act('sl_cut', step='section')
        j.act('sl_cut', step='guide', length=1)
        j.act('sl_cut', step='layers')
        j.act('sl_cut', step='check')
        money = j.c['money']
        j.act('sl_checkout', products=[], confirm=True)
        t = j.get(tid)
        self.assertTrue(cq.safety(t))
        self.assertEqual(self.stars(tid), 1)
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(j.c['money'], money)             # nothing paid for the services
        self.assertTrue(any(p.get('report') and p.get('source') == tid for p in j.c['feed']))
        self.assertTrue(any(f['src'] == tid for f in j.c['incidents']['follow']))
        self.assertIn('thử dị ứng', self.review(tid))
        validate_state(json.loads(json.dumps(j.state)))

    def test_stale_record_client_reacts_when_dyed_anyway(self):
        day, slot = case_of('react', lambda t: t['_x']['react'])
        self.j = j = Journey('salon', slot=slot, day=day)
        tid = j.task['id']
        j.act('ask')
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        j.act('sl_mix', kind='color', shade='dye_5_0', dev=20, ratio='1:1')
        j.act('sl_plan', services=['color', 'style'], sessions=1)
        j.act('sl_mix', kind='color', shade='dye_5_0', dev=20, ratio='1:1')
        j.act('sl_apply')
        self.clock.t += 14
        r = j.act('sl_rinse')
        self.assertIn('dị ứng', r['message'])
        self.assertIn(j.task['npc'], j.c['ext']['data']['allergy'])
        j.act('sl_style', finish='sleek')
        j.act('sl_checkout', products=[], confirm=True)
        self.assertIn('nổi mẩn', cq.slips(j.get(tid))[0]['text'])
        self.assertEqual(self.stars(tid), 1)
        validate_state(json.loads(json.dumps(j.state)))

    def test_no_double_charge(self):
        tid = self.office(guide=9)
        t = self.j.get(tid)
        cut = t['reaction']['cut']
        delta = self.j.c['money'] - self.money
        paid_products = 25 * len(t['sold'])
        self.assertIn(delta, (105 - cut + paid_products, 105 - cut + paid_products + S.SPEC['tip']))
        again = cq.react({}, self.j.c, t, 105)             # a replayed reaction moves no money
        self.assertEqual(again['cut'], cut)
        self.assertEqual(self.j.c['money'] - self.money, delta)
        with self.assertRaises(GameError):
            self.j.act('sl_checkout', task=tid, products=[], confirm=True)
        validate_state(json.loads(json.dumps(self.j.state)))

    def test_wrong_blow_dry_can_be_redone(self):
        tid = self.office(finish='natural')
        t = self.j.get(tid)
        self.assertEqual(cq.slips(t)[0]['code'], 'finish' if t['status'] == 'completed' else 'returned')
        if t['status'] == 'in_progress':
            self.assertEqual(t['reaction']['kind'], 'remake')
            self.assertNotIn('style', t['done'])
            self.assertEqual(self.j.c['money'], self.money)
            validate_state(json.loads(json.dumps(self.j.state)))
            self.j.act('sl_style', finish='sleek')
            self.j.act('sl_checkout', products=[], confirm=True)
            t = self.j.get(tid)
            self.assertEqual([x['code'] for x in cq.slips(t)], ['returned'])
            self.assertEqual(self.stars(tid), 4)
            self.assertIn('sấy lại', self.review(tid))
        self.assertEqual(t['status'], 'completed')
        self.assertLessEqual(self.stars(tid), 4)


if __name__ == '__main__':
    unittest.main()
