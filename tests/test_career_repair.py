import copy
import json
import unittest

import game.careers.kit as kit
from game.engine import GameError, public_state, validate_state
from game.careers import repair as R
from tests.helpers import Journey


def find_slot(pred, days=range(1, 16), special=False, slots=4):
    """Everyday jobs by default; special=True also looks at the v0.5 special cases."""
    for day in days:
        for slot in range(slots):
            t = R.make_task(day, slot, 1)
            if (special or not t['needs'].get('case')) and pred(t):
                return day, slot
    raise AssertionError('no task matches')


def journey_for(pred, special=False, days=range(1, 16), slots=4):
    day, slot = find_slot(pred, days, special, slots)
    return Journey('repair', slot=slot, day=day)


def case_journey(case, pred=lambda t: True):
    return journey_for(lambda t: t['needs'].get('case') == case and pred(t), special=True, days=range(1, 40), slots=10)


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey('repair')

    # --- helpers -------------------------------------------------------------------
    def grade_for(self, j, t, fault):
        fd = R._fault_def(t['needs']['device'], fault)
        options = [g for g in fd['parts'] if not (t['needs']['genuine_only'] and g in ('compatible', 'used'))]
        options = [g for g in options if not fd['parts'][g] or R.ITEM_INDEX[fd['parts'][g]].get('unlock', 1) <= kit.level(j.c)]
        if len(options) > 1:
            options = [g for g in options if g != 'used']   # new parts on the everyday path; used parts have their own tests
        return min(options, key=lambda g: R._line(j.c, t['needs']['device'], fd, g)['price'])

    def intake(self, j, tid):
        j.act('ask', task=tid)
        n = j.get(tid)['needs']
        j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=n['device'] in R.DATA_DEVICES)

    def repair(self, j, tid, finish=True):
        self.intake(j, tid)
        t = j.get(tid)
        dev = R.DEVICES[t['needs']['device']]
        j.act('rp_diagnose', task=tid, fault=t['_fault'])
        for step in dev['safety']:
            j.act('rp_safety', task=tid, step=step)
        j.act('rp_open', task=tid)
        t = j.get(tid)
        grades = {f: self.grade_for(j, t, f) for f in R._open_scope(t['bench'])}
        r = j.act('rp_quote', task=tid, grades=grades)
        self.assertTrue(r['accepted'], r['message'])
        for f in grades:
            j.act('rp_fix', task=tid, fault=f)
        j.act('rp_close', task=tid)
        r = j.act('rp_final', task=tid)
        self.assertEqual(j.get(tid)['bench']['final'], 'pass', r['message'])
        if finish:
            j.act('rp_warranty', task=tid, days=R._recommended(j.get(tid)))
            j.act('rp_handover', task=tid, confirm=True)
        return j.get(tid)

    # --- tests ---------------------------------------------------------------------
    def test_happy_path_every_feasible_job_template(self):
        seen = set()
        for day in range(1, 8):
            for slot in range(4):
                t = R.make_task(day, slot, 1)
                key = (t['_fault'], t['_extra'])
                if key in seen or t['_fault'] == 'motor' or t['needs'].get('case'):
                    continue
                seen.add(key)
                j = Journey('repair', slot=slot, day=day)
                j.c['xp'] = 200  # unlock genuine parts like a player on day `day`
                earned = j.c['earnings']
                done = self.repair(j, t['id'])
                self.assertEqual(done['status'], 'completed')
                paid = done['bench']['paid']
                self.assertGreater(paid, 0)
                self.assertLessEqual(paid, t['needs']['budget'])
                # (money may also move from shared random events, so compare earnings)
                self.assertEqual(j.c['earnings'], earned + paid)
                post = next(p for p in j.c['feed'] if p['kind'] == 'review')
                self.assertEqual(post['feedback']['fair'], 5, (key, post['feedback']['criteria']))
                validate_state(json.loads(json.dumps(j.state)))
        self.assertGreaterEqual(len(seen), 10)

    def test_hidden_until_ask_and_fault_never_public(self):
        view = public_state(self.j.state)['careers']['repair']['tasks'][0]
        self.assertIsNone(view['needs'])
        self.assertNotIn('_fault', view)
        with self.assertRaises(GameError):
            self.j.act('rp_intake', marks=[], accessories=[])
        tid = self.j.task['id']
        self.intake(self.j, tid)
        view = next(t for t in public_state(self.j.state)['careers']['repair']['tasks'] if t['id'] == tid)
        self.assertIsNotNone(view['needs'])
        dump = json.dumps(view, ensure_ascii=False)
        self.assertNotIn('_fault', dump)
        self.assertNotIn('_extra', dump)
        self.assertNotIn('solved', view)

    def test_intake_validation_and_mismatch_is_mistake(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.get(tid)['needs']
        dev = R.DEVICES[n['device']]
        for bad in (dict(marks='crack'), dict(marks=['not-a-mark']), dict(accessories=['case', 'case']), dict(consent='yes')):
            payload = dict(task=tid, marks=n['marks'], accessories=n['accessories'], consent=n['device'] in R.DATA_DEVICES)
            payload.update(bad)
            with self.assertRaises(GameError):
                j.act('rp_intake', **payload)
        with self.assertRaises(GameError):
            j.act('rp_test', task=tid, test=R.TESTS[n['device']][0]['id'])  # intake first
        wrong_acc = [a for a in dev['accessories'] if a not in n['accessories']][:1]
        j.act('rp_intake', task=tid, marks=n['marks'], accessories=wrong_acc, consent=n['device'] in R.DATA_DEVICES)
        self.assertEqual(j.get(tid)['mistakes'], 1)
        with self.assertRaises(GameError):
            j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=True)

    def test_phone_requires_consent_question_and_refuses_data_test(self):
        j = journey_for(lambda t: t['needs']['device'] == 'phone' and t['_data_ok'] is False)
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.task['needs']
        with self.assertRaises(GameError):
            j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=False)
        j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=True)
        self.assertIs(j.task['bench']['data_ok'], False)
        with self.assertRaises(GameError) as ctx:
            j.act('rp_test', task=tid, test='battery_health')
        self.assertEqual(ctx.exception.code, 'privacy')
        # Hardware tests are still fine.
        r = j.act('rp_test', task=tid, test='loupe')
        self.assertIn('Soi cổng sạc', r['message'])

    def test_tests_rule_out_hypotheses_and_cost_patience(self):
        j = journey_for(lambda t: t['needs']['device'] == 'fan' and t['_fault'] == 'capacitor')
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_test', task=tid, test='power')
        self.assertEqual(j.task['bench']['ruled_out'], ['bearing'])
        j.act('rp_test', task=tid, test='push')
        self.assertEqual(set(j.task['bench']['ruled_out']), {'bearing', 'motor'})
        with self.assertRaises(GameError):
            j.act('rp_test', task=tid, test='push')          # same test twice
        with self.assertRaises(GameError):
            j.act('rp_test', task=tid, test='cap_meter')     # needs the case open
        before = j.task['patience']
        j.act('rp_test', task=tid, test='spin')
        self.assertEqual(j.task['patience'], before - 3)
        # Diagnosing against the readings is a mistake.
        j.act('rp_diagnose', task=tid, fault='motor')
        self.assertEqual(j.task['mistakes'], 1)

    def test_live_test_needs_closed_case_and_repowers(self):
        j = journey_for(lambda t: t['needs']['device'] == 'fan')
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_safety', task=tid, step='unplug')
        j.act('rp_safety', task=tid, step='discharge')
        j.act('rp_test', task=tid, test='power')
        self.assertEqual(j.task['bench']['safe'], [])
        j.act('rp_safety', task=tid, step='unplug')
        j.act('rp_safety', task=tid, step='discharge')
        j.act('rp_open', task=tid)
        with self.assertRaises(GameError):
            j.act('rp_test', task=tid, test='push')
        self.assertEqual(j.task['mistakes'], 0)

    def test_unsafe_order_and_opening_live_device_are_hazards(self):
        j = journey_for(lambda t: t['needs']['device'] == 'fan')
        tid = j.task['id']
        self.intake(j, tid)
        r = j.act('rp_safety', task=tid, step='discharge')
        self.assertIn('Khoan', r['message'])
        self.assertEqual(j.task['bench']['safe'], [])
        r = j.act('rp_open', task=tid)
        self.assertIn('Tê', r['message'])
        self.assertEqual(j.task['bench']['hazards'], 2)
        self.assertEqual(j.task['mistakes'], 2)
        with self.assertRaises(GameError):
            j.act('rp_safety', task=tid, step='nope')

    def test_extra_fault_found_on_open_needs_requote(self):
        j = journey_for(lambda t: t['_fault'] == 'tube' and t['_extra'] == 'rimtape')
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_test', task=tid, test='squeeze')
        j.act('rp_diagnose', task=tid, fault='tube')
        r = j.act('rp_quote', task=tid, grades={'tube': 'standard'})
        self.assertTrue(r['accepted'])
        j.act('rp_safety', task=tid, step='stand')
        r = j.act('rp_open', task=tid)
        self.assertIn('dây lót vành', r['message'])
        self.assertEqual(j.task['bench']['found'], ['rimtape'])
        j.act('rp_fix', task=tid, fault='tube')
        # Fixing the newly found part without asking is a serious mistake → needs confirm.
        with self.assertRaises(GameError):
            j.act('rp_fix', task=tid, fault='rimtape', grade='standard')
        with self.assertRaises(GameError):
            j.act('rp_quote', task=tid, grades={})
        r = j.act('rp_quote', task=tid, grades={'rimtape': 'standard'})
        self.assertTrue(r['accepted'])
        self.assertIn('phát sinh', r['message'])
        j.act('rp_fix', task=tid, fault='rimtape')
        j.act('rp_close', task=tid)
        j.act('rp_final', task=tid)
        j.act('rp_warranty', task=tid, days=30)
        money = j.c['earnings']
        j.act('rp_handover', task=tid, confirm=True)
        b = j.get(tid)['bench']
        self.assertEqual(b['paid'], 20 + 8)
        self.assertEqual(j.c['earnings'], money + 28)

    def test_quote_rules_budget_genuine_and_locks(self):
        j = journey_for(lambda t: t['_fault'] == 'battery' and t['needs']['genuine_only'])
        tid = j.task['id']
        self.intake(j, tid)
        with self.assertRaises(GameError):
            j.act('rp_quote', task=tid, grades={'battery': 'genuine'})   # nothing diagnosed yet
        j.act('rp_diagnose', task=tid, fault='battery')
        for bad in ({'battery': 'gold'}, {'screen': 'genuine'}, 'battery', {}):
            with self.assertRaises(GameError):
                j.act('rp_quote', task=tid, grades=bad)
        r = j.act('rp_quote', task=tid, grades={'battery': 'compatible'})
        self.assertFalse(r['accepted'])
        self.assertIn('chính hãng', r['message'])
        r = j.act('rp_quote', task=tid, grades={'battery': 'genuine'})
        self.assertTrue(r['accepted'])
        self.assertEqual(j.task['bench']['approved']['battery'], dict(grade='genuine', price=24 + 30))
        # Genuine screens are locked at level 1.
        j2 = journey_for(lambda t: t['_fault'] == 'screen')
        t2 = j2.task['id']
        self.intake(j2, t2)
        j2.act('rp_diagnose', task=t2, fault='screen')
        with self.assertRaises(GameError):
            j2.act('rp_quote', task=t2, grades={'screen': 'genuine'})

    def test_over_budget_declined_then_honest_return(self):
        j = journey_for(lambda t: t['_fault'] == 'motor')
        j.c['xp'] = 400
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_test', task=tid, test='push')
        j.act('rp_diagnose', task=tid, fault='motor')
        r = j.act('rp_quote', task=tid, grades={'motor': 'standard'})
        self.assertFalse(r['accepted'])
        money = j.c['earnings']
        j.act('rp_return', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(j.c['earnings'], money + R.CHECK_FEE)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        crit = {x['key']: x['score'] for x in post['feedback']['criteria']}
        self.assertEqual(crit['honesty'], 5)
        self.assertGreaterEqual(post['feedback']['fair'], 4)
        self.assertEqual(public_state(j.state)['careers']['repair']['tasks'][-1].get('solved'), ['motor'])

    def test_misdiagnosis_wastes_part_and_requires_requote(self):
        j = journey_for(lambda t: t['_fault'] == 'lint')
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_test', task=tid, test='usb_meter')          # lint and port read the same
        j.act('rp_diagnose', task=tid, fault='port')          # a plausible but wrong guess
        r = j.act('rp_quote', task=tid, grades={'port': 'standard'})
        self.assertTrue(r['accepted'])
        j.act('rp_safety', task=tid, step='power_off')
        j.act('rp_open', task=tid)
        ports = kit.stock(j.c, 'port')
        solder = kit.stock(j.c, 'solder')
        j.act('rp_fix', task=tid, fault='port')
        self.assertEqual((kit.stock(j.c, 'port'), kit.stock(j.c, 'solder')), (ports - 1, solder - 1))
        with self.assertRaises(GameError):
            j.act('rp_final', task=tid)                      # still open
        j.act('rp_close', task=tid)
        waste = len(j.c['life']['waste'])
        r = j.act('rp_final', task=tid)
        b = j.task['bench']
        self.assertEqual(b['final'], 'fail', r['message'])
        self.assertEqual(len(j.c['life']['waste']), waste + 1)
        self.assertEqual(j.c['life']['waste'][-1]['item'], 'port')
        self.assertNotIn('port', b['fixed'])
        self.assertNotIn('port', b['approved'])
        self.assertIn('port', b['ruled_out'])
        self.assertIsNone(b['diagnosis'])
        with self.assertRaises(GameError):
            j.act('rp_handover', task=tid, confirm=True)
        j.act('rp_test', task=tid, test='loupe')
        j.act('rp_diagnose', task=tid, fault='lint')
        r = j.act('rp_quote', task=tid, grades={'lint': 'none'})
        self.assertTrue(r['accepted'])
        j.act('rp_safety', task=tid, step='power_off')
        j.act('rp_open', task=tid)
        j.act('rp_fix', task=tid, fault='lint')
        j.act('rp_close', task=tid)
        j.act('rp_final', task=tid)
        j.act('rp_warranty', task=tid, days=7)
        j.act('rp_handover', task=tid, confirm=True)
        t = j.get(tid)
        # The shop absorbs its wrong part; the customer only remembers the extra wait.
        self.assertEqual([x['code'] for x in t['slips']], ['misdiag'])
        self.assertEqual(t['bench']['paid'], 12 - t['reaction']['cut'])
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        crit = {x['key']: x['score'] for x in post['feedback']['criteria']}
        self.assertEqual(crit['diagnosis'], 3)
        validate_state(json.loads(json.dumps(j.state)))

    def test_unauthorized_repair_pays_parts_only_and_caps_review(self):
        j = journey_for(lambda t: t['_fault'] == 'dirt')
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_diagnose', task=tid, fault='dirt')
        j.act('rp_safety', task=tid, step='unplug')
        j.act('rp_open', task=tid)
        with self.assertRaises(GameError):
            j.act('rp_fix', task=tid, fault='dirt')                      # no grade, no confirm
        with self.assertRaises(GameError):
            j.act('rp_fix', task=tid, fault='dirt', grade='none')        # no confirm
        j.act('rp_fix', task=tid, fault='dirt', grade='none', confirm=True)
        self.assertEqual(j.task['mistakes'], 2)
        j.act('rp_close', task=tid)
        j.act('rp_final', task=tid)
        j.act('rp_warranty', task=tid, days=7)
        price = R._line(j.c, 'headphone', R._fault_def('headphone', 'dirt'), 'none')['price']
        j.act('rp_handover', task=tid, confirm=True)
        t = j.get(tid)
        # Billed at the list price, then the customer pushes back at the counter (serious mistake).
        self.assertEqual([x['code'] for x in t['slips']], ['unauthorized'])
        self.assertIn(t['reaction']['kind'], ('discount', 'refund', 'walkout'))
        self.assertEqual(t['bench']['paid'], price - t['reaction']['cut'])
        self.assertLess(t['bench']['paid'], price)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        self.assertLessEqual(post['stars'], 2)

    def test_warranty_overpromise_is_mistake_and_handover_needs_slip(self):
        j = journey_for(lambda t: t['_fault'] == 'dirt')
        tid = j.task['id']
        self.repair(j, tid, finish=False)
        with self.assertRaises(GameError):
            j.act('rp_handover', task=tid, confirm=True)
        with self.assertRaises(GameError):
            j.act('rp_warranty', task=tid, days=45)
        r = j.act('rp_warranty', task=tid, days=90)
        self.assertIn('tự gánh', r['message'])
        self.assertEqual(j.task['mistakes'], 1)
        with self.assertRaises(GameError):
            j.act('rp_warranty', task=tid, days=7)
        with self.assertRaises(GameError):
            j.act('rp_handover', task=tid)                   # confirm required
        j.act('rp_handover', task=tid, confirm=True)
        with self.assertRaises(GameError):
            j.act('rp_handover', task=tid, confirm=True)     # never paid twice

    def test_out_of_stock_part_blocks_fix(self):
        j = journey_for(lambda t: t['_fault'] == 'tube')
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_diagnose', task=tid, fault='tube')
        j.act('rp_safety', task=tid, step='stand')
        j.act('rp_open', task=tid)
        j.act('rp_quote', task=tid, grades={'tube': 'standard', 'rimtape': 'standard'})
        inv = j.c['ext']['inv']
        inv['lots'] = [lot for lot in inv['lots'] if lot['item'] != 'tube']
        with self.assertRaises(GameError) as ctx:
            j.act('rp_fix', task=tid, fault='tube')
        self.assertIn('Hết', ctx.exception.message)
        rim = kit.stock(j.c, 'rimtape')
        j.act('rp_fix', task=tid, fault='rimtape')
        self.assertEqual(kit.stock(j.c, 'rimtape'), rim - 1)

    def test_tampered_fixed_fields_and_readings_rejected(self):
        j = self.j
        tid = j.task['id']
        self.intake(j, tid)
        s = copy.deepcopy(j.state)
        t = next(x for x in s['careers']['repair']['tasks'] if x['id'] == tid)
        t['_fault'] = next(f for f in t['needs']['hypotheses'] if f != t['_fault'])
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        t = next(x for x in s['careers']['repair']['tasks'] if x['id'] == tid)
        t['needs']['budget'] = 999
        with self.assertRaises(GameError):
            validate_state(s)
        dev = j.task['needs']['device']
        test = next(x for x in R.TESTS[dev] if x['mode'] in ('live', 'any') and not x['consent'])
        j.act('rp_test', task=tid, test=test['id'])
        s = copy.deepcopy(j.state)
        t = next(x for x in s['careers']['repair']['tasks'] if x['id'] == tid)
        t['bench']['tests'][0]['reading'] = 'số đo bịa'
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        t = next(x for x in s['careers']['repair']['tasks'] if x['id'] == tid)
        t['bench']['paid'] = -5
        with self.assertRaises(GameError):
            validate_state(s)
        validate_state(json.loads(json.dumps(j.state)))

    def test_deterministic_tasks(self):
        for day in range(1, 10):
            for slot in range(5):
                self.assertEqual(R.make_task(day, slot, 3), R.make_task(day, slot, 3))
            ids = [R.make_task(day, s, 1)['title'] for s in range(3)]
            self.assertEqual(len(set(ids)), 3)

    def test_every_hypothesis_is_identifiable(self):
        for dev, rows in R.TESTS.items():
            hyp = R._hyp(dev)
            for f in hyp:
                others = [g for g in hyp if g != f]
                ruled = {g for t in rows for g in others if t['read'][g] != t['read'][f]}
                self.assertEqual(ruled, set(others), (dev, f))

    def test_assist_apprentice_does_safety_only(self):
        j = journey_for(lambda t: t['needs']['device'] == 'fan')
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_diagnose', task=tid, fault='capacitor')
        note = R.assist(j.state, j.c, dict(role='apprentice'), j.task)
        self.assertIn('rút điện', note)
        self.assertEqual(j.task['bench']['safe'], ['unplug'])
        self.assertFalse(j.task['bench']['opened'])
        self.assertIsNone(R.assist(j.state, j.c, dict(role='nobody'), j.task))

    def test_all_situations_playable(self):
        j = self.j
        for x in R.SPEC['situations']:
            self.assertTrue(5 <= len(R.SPEC['situations']) <= 8)
            for opt in x['options']:
                self.assertGreaterEqual(len(opt['perspectives']), 2, (x['id'], opt['id']))
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_real_situation_after_first_repair_and_day_close(self):
        j = self.j
        self.repair(j, j.task['id'])
        self.assertIsNotNone(j.c['ext']['situation'])
        r = j.act('end_day')
        self.assertEqual(r['summary']['career']['repaired'], 1)
        self.assertEqual(j.c['ext']['data']['day_repaired'], 0)
        validate_state(json.loads(json.dumps(j.state)))

    def test_content_hides_readings(self):
        c = R.content()
        self.assertNotIn('read', json.dumps(c['tests']))
        self.assertEqual(set(c['devices']), set(R.DEVICES))

    # --- v0.5: generator versions, luck of the day ----------------------------------
    def flow(self, j, tid, grades=None, pre_quote=None, finish=True, days=None):
        """Intake → diagnose the real fault → safe + open → (pre_quote) → quote → fix → close → final."""
        self.intake(j, tid)
        t = j.get(tid)
        dev = R.DEVICES[t['needs']['device']]
        j.act('rp_diagnose', task=tid, fault=t['_fault'])
        for step in dev['safety']:
            j.act('rp_safety', task=tid, step=step)
        j.act('rp_open', task=tid)
        if pre_quote:
            pre_quote()
        t = j.get(tid)
        grades = grades or {f: self.grade_for(j, t, f) for f in R._open_scope(t['bench'])}
        r = j.act('rp_quote', task=tid, grades=grades)
        self.assertTrue(r['accepted'], r['message'])
        for f in grades:
            j.act('rp_fix', task=tid, fault=f)
        j.act('rp_close', task=tid)
        r = j.act('rp_final', task=tid)
        self.assertEqual(j.get(tid)['bench']['final'], 'pass', r['message'])
        if finish:
            j.act('rp_warranty', task=tid, days=R._recommended(j.get(tid)) if days is None else days)
            j.act('rp_handover', task=tid, confirm=True)
        return j.get(tid)

    def review_of(self, j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def test_old_save_keeps_old_jobs_and_gains_new_fields(self):
        j = self.j
        s = copy.deepcopy(j.state)
        c = s['careers']['repair']
        old = R._make_v1(1, 0, 5)
        for k in R.BENCH_V2:
            old['bench'].pop(k)
        c['tasks'] = [old]
        c['active_task'] = old['id']
        d = c['ext']['data']
        for k in list(d):
            if k not in ('repaired', 'returned', 'hazards', 'unauthorized', 'wrong_parts', 'day_repaired', 'day_returned', 'day_hazards'):
                d.pop(k)
        c['ext']['inv']['lots'] = [l for l in c['ext']['inv']['lots'] if l['item'] not in R.NEW_ITEMS]
        validate_state(s)           # migrates in place, like loading an old save
        t = c['tasks'][0]
        self.assertGreaterEqual(t['created_turn'], kit.LEGACY_TURN)
        self.assertNotIn('gen', t)
        self.assertEqual(R.make_task(1, 0, t['created_turn']), R._make_v1(1, 0, t['created_turn']))
        self.assertIn('units', t['bench'])
        self.assertIn('desk', d)
        self.assertIs(d['v2_stock'], False)
        validate_state(json.loads(json.dumps(s)))     # idempotent
        j.state = s
        done = self.repair(j, old['id'])
        self.assertEqual(done['status'], 'completed')
        self.assertIs(j.c['ext']['data']['v2_stock'], True)
        self.assertEqual(kit.stock(j.c, 'screen_u'), R.ITEM_INDEX['screen_u']['start'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_luck_of_the_day_is_stable_and_shown(self):
        self.assertEqual(R.today(1)['id'], 'steady')
        for day in range(2, 40):
            self.assertEqual(R.today(day), R.today(day))
            self.assertNotEqual(R.today(day)['id'], R.today(day - 1)['id'])
        self.assertGreaterEqual(len({R.today(d)['id'] for d in range(1, 40)}), 5)
        self.assertEqual(self.j.c['ext']['data']['today'], dict(id='steady', day=1))
        view = public_state(self.j.state)['careers']['repair']['data']
        self.assertEqual(view['today']['title'], R.TODAY_INDEX['steady']['title'])
        self.assertIsNone(view['desk']['ev'])
        # Harder days: more special cases, the first customer is always an everyday repair.
        early = sum(bool(R.make_task(d, s, 1)['needs'].get('case')) for d in range(1, 3) for s in range(6))
        late = sum(bool(R.make_task(d, s, 1)['needs'].get('case')) for d in range(10, 12) for s in range(6))
        self.assertLess(early, late)
        self.assertTrue(all(not R.make_task(d, 0, 1)['needs'].get('case') for d in range(1, 30)))

    def test_no_customer_twice_a_day_or_back_the_next_morning(self):
        prev = []
        for day in range(1, 121):
            tasks = [R.make_task(day, slot, 1) for slot in range(6)]
            self.assertEqual(len({t['npc'] for t in tasks}), 6, day)
            titles = [t['title'] for t in tasks]
            self.assertEqual(len(set(titles)), 6, day)
            self.assertFalse(set(titles[:3]) & set(prev), day)
            prev = titles[:3]
        self.assertEqual(R.make_task(40, 2, 1), R.make_task(40, 2, 1))
        self.assertEqual(R.make_task(3, 20, 1)['career'], 'repair')

    def test_every_special_case_appears(self):
        cases = {R.make_task(d, s, 1)['needs'].get('case') for d in range(1, 40) for s in range(8)}
        self.assertEqual(cases - {None}, set(R.CASES))
        keys = {j['key'] for j in R.JOBS2}
        seen = {R._pick_v2(d, s)['key'] for d in range(1, 60) for s in range(10)}
        self.assertEqual(seen, keys)

    def test_outage_day_live_tests_burn_fuel(self):
        day = next(d for d in range(3, 60) if R.today(d)['id'] == 'outage')
        j = journey_for(lambda t: t['day'] == day and t['needs']['device'] != 'laptop', days=[day], slots=10)
        tid = j.task['id']
        self.intake(j, tid)
        rows = R.TESTS[j.task['needs']['device']]
        live = next(x['id'] for x in rows if x['mode'] == 'live' and not x['consent'])
        hand = next(x['id'] for x in rows if x['mode'] == 'any')
        money = j.c['money']
        r = j.act('rp_test', task=tid, test=live)
        self.assertEqual(j.c['money'], money - 2)
        self.assertIn('máy phát', r['message'])
        self.assertEqual(j.c['ops']['finance']['ledger'][-1]['category'], 'utilities')
        j.act('rp_test', task=tid, test=hand)            # measured by hand: free
        self.assertEqual(j.c['money'], money - 2)

    # --- used parts -------------------------------------------------------------------
    def used_journey(self, bad_first):
        for day in range(1, 120):
            for slot in range(8):
                t = R.make_task(day, slot, 1)
                if (t['_fault'] == 'screen' and not t['needs'].get('case') and not t['_extra']
                        and R._unit_bad(t, 'screen', 0) is bad_first and not R._unit_bad(t, 'screen', 1)):
                    return Journey('repair', slot=slot, day=day)
        raise AssertionError('no task')

    def test_used_part_must_be_tested_or_the_final_test_may_fail(self):
        j = self.used_journey(True)
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_diagnose', task=tid, fault='screen')
        with self.assertRaises(GameError):
            j.act('rp_parttest', task=tid, fault='screen')     # not quoted as a used part
        r = j.act('rp_quote', task=tid, grades={'screen': 'used'})
        self.assertTrue(r['accepted'])
        j.act('rp_safety', task=tid, step='power_off')
        j.act('rp_open', task=tid)
        stock = kit.stock(j.c, 'screen_u')
        r = j.act('rp_fix', task=tid, fault='screen')
        self.assertIn('chưa cắm thử', r['message'])
        j.act('rp_close', task=tid)
        mistakes = j.task['mistakes']
        r = j.act('rp_final', task=tid)
        b = j.task['bench']
        self.assertEqual(b['final'], 'fail')
        self.assertIn('hao hụt', r['message'])
        self.assertNotIn('screen', b['fixed'])
        self.assertEqual(b['units']['screen'], 1)
        self.assertEqual(j.task['mistakes'], mistakes + 1)
        self.assertEqual(kit.stock(j.c, 'screen_u'), stock - 1)
        # Test units on the bench this time; dead ones are scrapped until one works.
        j.act('rp_safety', task=tid, step='power_off')
        j.act('rp_open', task=tid)
        for _ in range(4):
            if 'screen' in j.task['bench']['checked']:
                break
            j.act('rp_parttest', task=tid, fault='screen')
        self.assertIn('screen', j.task['bench']['checked'])
        with self.assertRaises(GameError):
            j.act('rp_parttest', task=tid, fault='screen')     # already tested
        j.act('rp_fix', task=tid, fault='screen')
        j.act('rp_close', task=tid)
        j.act('rp_final', task=tid)
        self.assertEqual(j.task['bench']['final'], 'pass')
        self.assertEqual(R._recommended(j.task), 7)
        j.act('rp_warranty', task=tid, days=7)
        j.act('rp_handover', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['bench']['paid'], R._line(j.c, 'phone', R._fault_def('phone', 'screen'), 'used')['price'])
        self.assertGreaterEqual(j.c['ext']['data']['used_scrapped'], 1)
        validate_state(json.loads(json.dumps(j.state)))

    def test_tested_used_part_passes_first_time(self):
        j = self.used_journey(False)
        tid = j.task['id']
        self.intake(j, tid)
        j.act('rp_diagnose', task=tid, fault='screen')
        j.act('rp_quote', task=tid, grades={'screen': 'used'})
        j.act('rp_safety', task=tid, step='power_off')
        j.act('rp_open', task=tid)
        r = j.act('rp_parttest', task=tid, fault='screen')
        self.assertIn('ngon', r['message'])
        j.act('rp_fix', task=tid, fault='screen')
        j.act('rp_close', task=tid)
        j.act('rp_final', task=tid)
        self.assertEqual(j.task['bench']['final'], 'pass')
        j.act('rp_warranty', task=tid, days=7)
        j.act('rp_handover', task=tid, confirm=True)
        crit = {x['key']: x['score'] for x in self.review_of(j, tid)['feedback']['criteria']}
        self.assertEqual(crit['result'], 4)
        # A genuine-only customer refuses used parts.
        j2 = journey_for(lambda t: t['_fault'] == 'battery' and t['needs']['genuine_only'])
        t2 = j2.task['id']
        self.intake(j2, t2)
        j2.act('rp_diagnose', task=t2, fault='battery')
        self.assertFalse(j2.act('rp_quote', task=t2, grades={'battery': 'used'})['accepted'])

    def test_bargain_jobs_are_only_affordable_with_used_parts(self):
        j = case_journey('bargain')
        t = j.task
        fault = t['_fault']
        fd = R._fault_def(t['needs']['device'], fault)
        prices = {g: R._line(j.c, t['needs']['device'], fd, g)['price'] for g in fd['parts']}
        self.assertLessEqual(prices['used'], t['needs']['budget'])
        self.assertTrue(all(p > t['needs']['budget'] for g, p in prices.items() if g != 'used'))

    # --- the phone that "never got wet" -------------------------------------------------
    def test_water_damage_denied_until_the_tag_is_shown(self):
        j = case_journey('water')
        tid = j.task['id']
        self.intake(j, tid)
        self.assertIn('water', j.task['needs']['hypotheses'])
        j.act('rp_diagnose', task=tid, fault='water')
        r = j.act('rp_quote', task=tid, grades={'water': 'none'})
        self.assertFalse(r['accepted'])
        self.assertIn('nước', r['message'])
        with self.assertRaises(GameError):
            j.act('rp_show', task=tid)                  # nothing to show yet
        j.act('rp_safety', task=tid, step='power_off')
        j.act('rp_open', task=tid)
        r = j.act('rp_test', task=tid, test='water_tag')
        self.assertIn('đỏ', r['message'])
        j.act('rp_show', task=tid)
        self.assertTrue(j.task['bench']['shown'])
        with self.assertRaises(GameError):
            j.act('rp_show', task=tid)
        self.assertTrue(j.act('rp_quote', task=tid, grades={'water': 'none'})['accepted'])
        j.act('rp_fix', task=tid, fault='water')
        j.act('rp_close', task=tid)
        j.act('rp_final', task=tid)
        self.assertEqual(R._recommended(j.task), 0)
        mistakes = j.task['mistakes']
        j.act('rp_warranty', task=tid, days=0)
        self.assertEqual(j.task['mistakes'], mistakes)
        j.act('rp_handover', task=tid, confirm=True)
        validate_state(json.loads(json.dumps(j.state)))
        # A dry phone has nothing to show.
        j2 = journey_for(lambda t: t['needs']['device'] == 'phone' and t['_fault'] == 'screen')
        t2 = j2.task['id']
        self.intake(j2, t2)
        j2.act('rp_safety', task=t2, step='power_off')
        j2.act('rp_open', task=t2)
        j2.act('rp_test', task=t2, test='water_tag')
        with self.assertRaises(GameError):
            j2.act('rp_show', task=t2)

    # --- warranty book ------------------------------------------------------------------
    def test_warranty_claim_covered_is_free_and_booked(self):
        j = case_journey('warranty', R._covered)
        tid = j.task['id']
        slip = j.task['needs']['claim']['slip']
        self.assertTrue(any(r['slip'] == slip for r in j.c['ext']['data']['book']))

        def decide():
            with self.assertRaises(GameError):
                j.act('rp_claim', task=tid, choice='cover')        # look it up first
            r = j.act('rp_book', task=tid)
            self.assertIn(slip, r['message'])
            self.assertEqual(j.task['bench']['book'], R._book_view(j.task))
            with self.assertRaises(GameError):
                j.act('rp_quote', task=tid, grades={f: 'standard' for f in R._open_scope(j.task['bench'])})
            j.act('rp_claim', task=tid, choice='cover')
        done = self.flow(j, tid, pre_quote=decide)
        self.assertEqual(done['bench']['paid'], 0)
        crit = {x['key']: x['score'] for x in self.review_of(j, tid)['feedback']['criteria']}
        self.assertEqual(crit['claim'], 5)
        self.assertEqual(public_state(j.state)['careers']['repair']['tasks'][-1]['truth'], dict(covered=True))
        validate_state(json.loads(json.dumps(j.state)))

    def test_warranty_claim_charged_when_covered_is_a_mistake(self):
        j = case_journey('warranty', R._covered)
        tid = j.task['id']

        def charge():
            j.act('rp_book', task=tid)
            j.act('rp_claim', task=tid, choice='charge')
        done = self.flow(j, tid, pre_quote=charge)
        self.assertGreater(done['bench']['paid'], 0)
        self.assertGreaterEqual(done['mistakes'], 2)
        post = self.review_of(j, tid)
        self.assertLessEqual(post['stars'], 2)

    def test_warranty_claim_not_covered_is_charged(self):
        j = case_journey('warranty', lambda t: not R._covered(t))
        tid = j.task['id']

        def charge():
            j.act('rp_book', task=tid)
            j.act('rp_claim', task=tid, choice='charge')
        done = self.flow(j, tid, pre_quote=charge)
        self.assertGreater(done['bench']['paid'], 0)
        crit = {x['key']: x['score'] for x in self.review_of(j, tid)['feedback']['criteria']}
        self.assertEqual(crit['claim'], 5)
        self.assertEqual(done['mistakes'], 0)

    # --- rush jobs ----------------------------------------------------------------------
    def test_rush_bonus_only_on_time(self):
        j = case_journey('rush')
        tid = j.task['id']
        bonus = j.task['needs']['rush']['bonus']
        view = next(t for t in public_state(j.state)['careers']['repair']['tasks'] if t['id'] == tid)
        self.assertIsNone(view['needs'])
        j.act('ask', task=tid)
        view = next(t for t in public_state(j.state)['careers']['repair']['tasks'] if t['id'] == tid)
        self.assertEqual(view['due_turn'], j.task['created_turn'] + j.task['needs']['rush']['steps'])
        done = self.flow(j, tid, finish=False)
        quoted = sum(v['price'] for v in done['bench']['approved'].values())
        j.act('rp_warranty', task=tid, days=R._recommended(j.get(tid)))
        r = j.act('rp_handover', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['bench']['paid'], quoted + bonus)
        self.assertIn('Kịp giờ', r['message'])
        # Same job, but the clock ran out.
        j2 = case_journey('rush')
        t2 = j2.task['id']
        self.flow(j2, t2, finish=False)
        j2.c['turn'] += 40
        j2.act('rp_warranty', task=t2, days=R._recommended(j2.get(t2)))
        r = j2.act('rp_handover', task=t2, confirm=True)
        self.assertNotIn('Kịp giờ', r['message'])
        self.assertEqual(j2.get(t2)['bench']['paid'], sum(v['price'] for v in j2.get(t2)['bench']['approved'].values()))

    # --- second-hand phones ----------------------------------------------------------------
    def test_buyin_stolen_phone_costs_the_shop(self):
        j = case_journey('buyin', lambda t: t['_x']['stolen'] and t['_x']['imei'] == 'reported')
        tid = j.task['id']
        j.act('ask', task=tid)
        dump = json.dumps(next(t for t in public_state(j.state)['careers']['repair']['tasks'] if t['id'] == tid), ensure_ascii=False)
        self.assertNotIn('stolen', dump)
        self.assertNotIn('reported', dump)
        with self.assertRaises(GameError):
            j.act('rp_intake', task=tid, marks=[], accessories=[], consent=True)
        with self.assertRaises(GameError):
            j.act('rp_deal', task=tid, choice='buy')              # needs confirm
        r = j.act('rp_imei', task=tid)
        self.assertIn('KHỚP', r['message'])
        money, stock = j.c['money'], kit.stock(j.c, 'screen_u')
        j.act('rp_deal', task=tid, choice='buy', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(t['mistakes'], 3)
        self.assertLess(j.c['money'], money)
        self.assertEqual(kit.stock(j.c, 'screen_u'), stock)
        self.assertEqual(public_state(j.state)['careers']['repair']['tasks'][-1]['truth'], dict(stolen=True))
        validate_state(json.loads(json.dumps(j.state)))

    def test_buyin_clean_phone_gives_used_parts_and_false_report_hurts(self):
        j = case_journey('buyin', lambda t: not t['_x']['stolen'])
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('rp_imei', task=tid)
        j.act('rp_papers', task=tid)
        with self.assertRaises(GameError):
            j.act('rp_papers', task=tid)
        before = {k: kit.stock(j.c, k) for k in ('screen_u', 'battery_u')}
        offer = j.task['needs']['offer']
        money = j.c['money']
        j.act('rp_deal', task=tid, choice='buy', confirm=True)
        self.assertEqual(j.c['money'], money - offer)
        for k, v in before.items():
            self.assertEqual(kit.stock(j.c, k), min(40, v + 1))
        crit = {x['key']: x['score'] for x in self.review_of(j, tid)['feedback']['criteria']}
        self.assertEqual(crit['deal'], 5)
        j2 = case_journey('buyin', lambda t: not t['_x']['stolen'])
        t2 = j2.task['id']
        j2.act('ask', task=t2)
        j2.act('rp_deal', task=t2, choice='report', confirm=True)
        self.assertEqual(j2.get(t2)['mistakes'], 2)

    # --- data that is not the customer's --------------------------------------------------
    def test_privacy_request_trade_off(self):
        j = case_journey('privacy')
        tid = j.task['id']
        self.flow(j, tid, finish=False)
        j.act('rp_warranty', task=tid, days=R._recommended(j.task))
        with self.assertRaises(GameError):
            j.act('rp_handover', task=tid, confirm=True)
        mistakes = j.task['mistakes']
        j.act('rp_data', task=tid, choice='copy')
        self.assertEqual(j.task['mistakes'], mistakes + 2)
        self.assertIn('leak', j.c['ext']['data']['desk']['marks'])
        with self.assertRaises(GameError):
            j.act('rp_data', task=tid, choice='refuse')
        quoted = sum(v['price'] for v in j.task['bench']['approved'].values())
        j.act('rp_handover', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['bench']['paid'], quoted + R.DATA_FEE)
        j2 = case_journey('privacy')
        t2 = j2.task['id']
        self.intake(j2, t2)
        patience = j2.task['patience']
        j2.act('rp_data', task=t2, choice='refuse')
        self.assertEqual(j2.task['patience'], max(25, patience - 10))
        self.assertNotIn('leak', j2.c['ext']['data']['desk']['marks'])

    def test_laptop_needs_consent_and_respects_privacy(self):
        j = journey_for(lambda t: t['needs']['device'] == 'laptop' and t['_data_ok'] is False)
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.task['needs']
        with self.assertRaises(GameError):
            j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=False)
        j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=True)
        with self.assertRaises(GameError) as ctx:
            j.act('rp_test', task=tid, test='temp')
        self.assertEqual(ctx.exception.code, 'privacy')
        r = j.act('rp_test', task=tid, test='boot')
        self.assertIn('Loại', r['message'])
        j2 = journey_for(lambda t: t['needs']['device'] == 'laptop' and t['_fault'] == 'ssd')
        self.assertEqual(self.flow(j2, j2.task['id'])['status'], 'completed')

    # --- surprises at the counter ------------------------------------------------------------
    def day_two(self):
        j = self.j
        j.act('end_day')
        j.act('start_day')
        self.assertEqual(j.c['day'], 2)
        self.assertEqual(j.c['ext']['data']['desk']['plan'][0], 2)
        return j

    def test_desk_event_fires_blocks_work_and_resolves(self):
        self.assertEqual(kit.desk_plan('repair', 1), [])
        j = self.day_two()
        tid = j.c['active_task']
        j.act('ask', task=tid)
        j.c['day_completed'] = 2          # two customers already served today
        n = j.task['needs']
        r = j.act('rp_intake' if n.get('case') != 'buyin' else 'rp_imei', task=tid, marks=n['marks'], accessories=n['accessories'],
                  consent=n['device'] in R.DATA_DEVICES)
        self.assertTrue(r.get('surprise'), r)
        desk = j.c['ext']['data']['desk']
        self.assertIsNotNone(desk['ev'])
        with self.assertRaises(GameError) as ctx:
            j.act('rp_test', task=tid, test=R.TESTS[n['device']][0]['id'])
        self.assertEqual(ctx.exception.code, 'surprise_open')
        view = public_state(j.state)['careers']['repair']['data']['desk']
        self.assertEqual(view['ev']['script'], desk['ev']['script'])
        self.assertNotIn('luck', json.dumps(view))
        self.assertNotIn('effects', json.dumps(view))
        script = R.DESK_INDEX[desk['ev']['script']]
        with self.assertRaises(GameError):
            j.act('rp_desk', option='not-an-option')
        r = j.act('rp_desk', option=script['default'])
        self.assertTrue(r['message'])
        self.assertIsNone(j.c['ext']['data']['desk']['ev'])
        self.assertEqual(j.c['ext']['data']['desk']['last']['script'], script['id'])
        # Only one surprise was planned for day 2.
        j.act('rp_test', task=tid, test=next(x['id'] for x in R.TESTS[n['device']] if x['mode'] != 'open' and not x['consent']))
        self.assertIsNone(j.c['ext']['data']['desk']['ev'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_desk_options_are_shown_in_a_shuffled_order(self):
        j = self.day_two()
        spots = set()
        for x in R.DESK:
            j.c['ext']['data']['desk']['ev'] = dict(id='desk-99', script=x['id'], day=j.c['day'], at='between')
            shown = public_state(j.state)['careers']['repair']['data']['desk']['ev']['options']
            self.assertEqual(sorted(o['id'] for o in shown), sorted(o['id'] for o in x['options']), x['id'])
            again = public_state(j.state)['careers']['repair']['data']['desk']['ev']['options']
            self.assertEqual([o['id'] for o in shown], [o['id'] for o in again], x['id'])
            good = [o['id'] for o in x['options'] if o.get('good')]
            if good:
                spots.add([o['id'] for o in shown].index(good[0]))
        self.assertGreater(len(spots), 1, 'the careful answer always sits in the same place')
        j.c['ext']['data']['desk']['ev'] = None

    def test_every_desk_option_applies_cleanly(self):
        j = self.day_two()
        base = j.state
        for x in R.DESK:
            self.assertGreaterEqual(len(x['options']), 2, x['id'])
            self.assertIn(x['default'], [o['id'] for o in x['options']])
            for o in x['options']:
                j.state = copy.deepcopy(base)
                desk = j.c['ext']['data']['desk']
                desk['ev'] = dict(id='desk-99', script=x['id'], day=j.c['day'], at='between')
                validate_state(j.state)
                money = j.c['money']
                r = j.act('rp_desk', option=o['id'])
                self.assertTrue(r['message'], (x['id'], o['id']))
                cost = -min(0, o.get('effects', {}).get('money', 0))
                self.assertGreaterEqual(j.c['money'], money - cost - 50)
                validate_state(json.loads(json.dumps(j.state)))
        j.state = base

    def test_undecided_surprise_takes_default_at_closing(self):
        j = self.day_two()
        j.c['ext']['data']['desk']['ev'] = dict(id='desk-99', script='kid_toy', day=2, at='between')
        r = j.act('end_day')
        self.assertIn('Bé Bin', r['summary']['career']['surprise'])
        lines = r['summary']['career']['lines']
        self.assertTrue(lines[0].startswith('Hôm nay sửa xong 0 máy'), lines)
        self.assertTrue(any('Bé Bin' in x for x in lines), lines)
        self.assertIn(R.today(j.c['day'])['title'], lines[-1])          # closing moved to the next day: its forecast
        last = j.c['ext']['data']['desk']['last']
        self.assertEqual((last['choice'], last['auto']), ('later', True))
        self.assertIsNone(j.c['ext']['data']['desk']['ev'])

    def test_shady_parts_lead_to_the_harder_inspection(self):
        j = self.day_two()
        j.c['day'] = 5
        j.c['ext']['data']['desk']['ev'] = dict(id='desk-99', script='shady_lot', day=5, at='between')
        j.act('rp_desk', option='take')
        self.assertIn('no_invoice', j.c['ext']['data']['desk']['marks'])
        pool = {x['id'] for x in kit._desk_pool('repair', j.c, j.c['ext']['data']['desk'], R.DESK, 'between', 'steady')}
        self.assertIn('inspect_bad', pool)
        self.assertNotIn('inspect_ok', pool)
        self.assertNotIn('shady_lot', pool)


class RepairConsequenceTests(unittest.TestCase):
    """Doing the job wrong costs you at the counter, in proportion (game/consequences.py)."""

    def simple(self, device):
        return journey_for(lambda t: t['needs']['device'] == device and not t['_extra'] and t['_fault'] != 'motor')

    def job(self, j, skip_safety=False, grades=None, test=True, days=None):
        tid = j.task['id']
        j.act('ask', task=tid)
        t = j.get(tid)
        n = t['needs']
        j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=n['device'] in R.DATA_DEVICES)
        j.act('rp_diagnose', task=tid, fault=t['_fault'])
        if not skip_safety:
            for step in R.DEVICES[n['device']]['safety']:
                j.act('rp_safety', task=tid, step=step)
        j.act('rp_open', task=tid)
        t = j.get(tid)
        grades = grades or {f: RepairTests.grade_for(None, j, t, f) for f in R._open_scope(t['bench'])}
        self.assertTrue(j.act('rp_quote', task=tid, grades=grades)['accepted'])
        for f in grades:
            j.act('rp_fix', task=tid, fault=f)
        j.act('rp_close', task=tid)
        if test:
            j.act('rp_final', task=tid)
            j.act('rp_warranty', task=tid, days=R._recommended(j.get(tid)) if days is None else days)
        r = j.act('rp_handover', task=tid, confirm=True)
        return j.get(tid), r

    def wrong_part_untested(self):
        j = journey_for(lambda t: t['_fault'] == 'lint')
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.task['needs']
        j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=True)
        j.act('rp_test', task=tid, test='usb_meter')
        j.act('rp_diagnose', task=tid, fault='port')
        j.act('rp_quote', task=tid, grades={'port': 'standard'})
        j.act('rp_safety', task=tid, step='power_off')
        j.act('rp_open', task=tid)
        j.act('rp_fix', task=tid, fault='port')
        j.act('rp_close', task=tid)
        price = j.task['bench']['approved']['port']['price']
        r = j.act('rp_handover', task=tid, confirm=True)       # no final test: allowed now, with consequences
        return j, j.get(tid), price, r

    def review(self, j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def reward(self, j, tid):
        return sum(x['amount'] for x in j.c['ops']['finance']['ledger'] if x['ref'] == tid and x['reason'].startswith('Hoàn thành'))

    def test_right_job_full_pay_no_slips(self):
        j = self.simple('phone')
        t, r = self.job(j)
        self.assertEqual(t.get('slips') or [], [])
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertEqual(t['bench']['paid'], sum(v['price'] for v in t['bench']['approved'].values()))
        self.assertGreaterEqual(self.review(j, t['id'])['stars'], 4)
        self.assertTrue(r.get('celebrate'))

    def test_device_not_fixed_costs_the_job(self):
        j, t, price, r = self.wrong_part_untested()
        self.assertEqual(t['status'], 'completed')
        self.assertEqual([x['code'] for x in t['slips']], ['not_fixed', 'wrong_part'])
        post = self.review(j, t['id'])
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('vẫn y bệnh cũ', post['text'])
        self.assertIn(t['reaction']['kind'], ('refund', 'walkout'))
        self.assertLess(t['bench']['paid'], price)
        self.assertEqual(t['bench']['paid'], price - t['reaction']['cut'])
        self.assertTrue(any(p.get('report') for p in j.c['feed']))
        self.assertIsNone(next((x for x in j.c['ext']['data']['book'] if x['title'] == t['title'] and x['day'] == j.c['day']), None))
        validate_state(json.loads(json.dumps(j.state)))

    def test_severity_scales_the_stars(self):
        j1 = self.simple('phone')
        small, _ = self.job(j1, test=False)                      # right fix, just not tested in front of the customer
        self.assertEqual([x['code'] for x in small['slips']], ['no_test'])
        j3, big, _, _ = self.wrong_part_untested()
        self.assertGreater(self.review(j1, small['id'])['stars'], self.review(j3, big['id'])['stars'])
        self.assertGreaterEqual(self.review(j1, small['id'])['stars'], 3)

    def test_opening_a_live_device_is_a_safety_mistake(self):
        j = self.simple('phone')
        t, r = self.job(j, skip_safety=True)
        self.assertEqual(t['bench']['unsafe'], 1)
        self.assertTrue(t['slips'][0]['safety'])
        self.assertEqual(self.review(j, t['id'])['stars'], 1)
        self.assertEqual(t['reaction']['kind'], 'refuse')
        self.assertEqual(t['bench']['paid'], 0)
        self.assertTrue(any(p.get('report') and p['source'] == t['id'] for p in j.c['feed']))
        self.assertIn('slip_safety_inspect', json.dumps(j.c['incidents']['follow']))
        validate_state(json.loads(json.dumps(j.state)))

    def test_bike_dropped_is_a_clear_mistake_not_a_safety_one(self):
        j = self.simple('bike')
        t, _ = self.job(j, skip_safety=True)
        self.assertEqual([(x['code'], x['sev'], x['safety']) for x in t['slips']], [('unsafe', 2, False)])
        self.assertLessEqual(self.review(j, t['id'])['stars'], 3)

    def test_safety_step_in_the_wrong_order_is_stopped_in_time(self):
        j = self.simple('fan')
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.task['needs']
        j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=False)
        self.assertIn('Khoan', j.act('rp_safety', task=tid, step='discharge')['message'])
        self.assertEqual(j.task['bench']['unsafe'], 0)          # nothing happened to the customer's fan

    def test_no_double_charge_and_replay_is_harmless(self):
        j, t, price, _ = self.wrong_part_untested()
        tid = t['id']
        self.assertEqual(self.reward(j, tid), price - t['reaction']['cut'])
        money = j.c['money']
        with self.assertRaises(GameError):
            j.act('rp_handover', task=tid, confirm=True)
        again = R.cq.react(j.state, j.c, j.get(tid), price)
        self.assertEqual(again['kind'], t['reaction']['kind'])
        self.assertEqual(j.c['money'], money)
        self.assertEqual(self.reward(j, tid), price - t['reaction']['cut'])

    def test_counter_slips_for_paperwork_warranty_and_giving_up(self):
        j = self.simple('phone')
        t, _ = self.job(j, days=0)
        self.assertEqual([(x['code'], x['sev']) for x in t['slips']], [('short_warranty', 1)])
        # A charger handed over but left off the intake slip.
        j = self.simple('phone')
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.task['needs']
        j.act('rp_intake', task=tid, marks=n['marks'], accessories=[a for a in n['accessories'] if a != n['accessories'][0]], consent=True)
        j.act('rp_test', task=tid, test=R.TESTS['phone'][0]['id'])
        j.act('rp_return', task=tid, confirm=True)
        t = j.get(tid)
        codes = [x['code'] for x in t['slips']]
        self.assertIn('lost_acc', codes)
        if R._feasible(j.c, t):
            self.assertIn('gave_up', codes)
        self.assertLessEqual(self.review(j, tid)['stars'], 3)
        validate_state(json.loads(json.dumps(j.state)))

    def test_charging_a_covered_warranty_is_an_overcharge(self):
        j = case_journey('warranty', R._covered)
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.task['needs']
        j.act('rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=n['device'] in R.DATA_DEVICES)
        j.act('rp_diagnose', task=tid, fault=j.task['_fault'])
        for step in R.DEVICES[n['device']]['safety']:
            j.act('rp_safety', task=tid, step=step)
        j.act('rp_open', task=tid)
        j.act('rp_book', task=tid)
        j.act('rp_claim', task=tid, choice='charge')
        t = j.get(tid)
        grades = {f: RepairTests.grade_for(None, j, t, f) for f in R._open_scope(t['bench'])}
        j.act('rp_quote', task=tid, grades=grades)
        for f in grades:
            j.act('rp_fix', task=tid, fault=f)
        j.act('rp_close', task=tid)
        j.act('rp_final', task=tid)
        j.act('rp_warranty', task=tid, days=R._recommended(j.get(tid)))
        j.act('rp_handover', task=tid, confirm=True)
        t = j.get(tid)
        self.assertIn('overcharge', [x['code'] for x in t['slips']])
        post = self.review(j, tid)
        self.assertLessEqual(post['stars'], 2)
        self.assertLessEqual(len(post['feedback']['criteria']), 8)
        validate_state(json.loads(json.dumps(j.state)))



# ------------------------------------------------------------------------------ care loop (multi-day)
def plain_journey(pred, days=range(1, 20), slots=6):
    """An everyday job (no special case) matching pred, with every part unlocked."""
    j = journey_for(pred, days=days, slots=slots)
    j.c['xp'] = 400
    return j


def clear_desk(j):
    ev = R._data(j.c)['desk']['ev']
    if ev and j.c['open']:
        j.act('rp_desk', option=R.DESK_INDEX[ev['script']]['default'])


def act(j, name, **p):
    clear_desk(j)
    return j.act(name, **p)


def new_day(j):
    clear_desk(j)
    j.act('end_day', carry_event=True)
    j.act('start_day')
    clear_desk(j)


def drain(j, item):
    q = kit.stock(j.c, item)
    if q:
        kit.take(j.c, item, q)


def care_view(j, tid=None):
    care = public_state(j.state)['careers']['repair']['data']['care']
    return care['tasks'].get(tid) if tid else care


def roundtrip(j):
    validate_state(json.loads(json.dumps(j.state)))


class CareLoopTests(unittest.TestCase):
    def quoted(self, j, grade, drain_part=True):
        """Take the device in, pin the real fault and have the customer accept `grade` for it."""
        tid = j.task['id']
        act(j, 'ask', task=tid)
        n = j.get(tid)['needs']
        act(j, 'rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=n['device'] in R.DATA_DEVICES)
        fault = j.get(tid)['_fault']
        act(j, 'rp_diagnose', task=tid, fault=fault)
        item = R._fault_def(n['device'], fault)['parts'][grade]
        if drain_part and item:
            drain(j, item)
        r = act(j, 'rp_quote', task=tid, grades={fault: grade})
        self.assertTrue(r['accepted'], r['message'])
        return tid, fault, item

    def finish(self, j, tid, test=True):
        t = j.get(tid)
        for step in R.DEVICES[t['needs']['device']]['safety'][len(t['bench']['safe']):]:
            act(j, 'rp_safety', task=tid, step=step)
        if not j.get(tid)['bench']['opened']:
            act(j, 'rp_open', task=tid)
        t = j.get(tid)
        pending = [f for f in R._open_scope(t['bench']) if f not in t['bench']['approved']]
        if pending:
            grades = {f: RepairTests.grade_for(None, j, t, f) for f in pending}
            self.assertTrue(act(j, 'rp_quote', task=tid, grades=grades)['accepted'])
        for f in R._open_scope(j.get(tid)['bench']):
            act(j, 'rp_fix', task=tid, fault=f)
        act(j, 'rp_close', task=tid)
        if test:
            act(j, 'rp_final', task=tid)
            self.assertEqual(j.get(tid)['bench']['final'], 'pass')
            act(j, 'rp_warranty', task=tid, days=R._recommended(j.get(tid)))
        return act(j, 'rp_handover', task=tid, confirm=True)

    def review(self, j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    # --- part orders ------------------------------------------------------------
    def test_lam_order_arrives_this_afternoon_and_is_fitted(self):
        j = plain_journey(lambda t: t['_fault'] == 'capacitor')
        tid, fault, item = self.quoted(j, 'compatible')
        for step in R.DEVICES['fan']['safety']:
            act(j, 'rp_safety', task=tid, step=step)
        act(j, 'rp_open', task=tid)
        with self.assertRaises(GameError) as ctx:
            act(j, 'rp_fix', task=tid, fault=fault)
        self.assertIn('Đặt riêng', ctx.exception.message)
        with self.assertRaises(GameError):
            act(j, 'rp_order', task=tid, fault=fault)                  # needs confirm
        money = j.c['money']
        r = act(j, 'rp_order', task=tid, fault=fault, confirm=True)
        self.assertIn('chiều nay 15:00', r['message'])
        cost = R.ITEM_INDEX[item]['cost'] + R.SOURCES['lam']['ship']
        self.assertEqual(j.c['money'], money - cost)
        o = j.get(tid)['bench']['orders'][fault]
        self.assertEqual((o['day'], o['minute'], o['src']), (j.c['day'], R.LAM_ARRIVE, 'lam'))
        self.assertEqual(care_view(j, tid)['orders'][fault]['when'], 'chiều nay 15:00')
        with self.assertRaises(GameError) as ctx:
            act(j, 'rp_fix', task=tid, fault=fault)
        self.assertIn('chưa về', ctx.exception.message)
        with self.assertRaises(GameError):
            act(j, 'rp_order', task=tid, fault=fault, confirm=True)    # already on its way
        j.c['turn'] += 60                                               # the afternoon passes with other customers
        r = act(j, 'rp_test', task=tid, test='coil_meter')
        self.assertIn('đã về', r['message'])
        self.assertTrue(j.get(tid)['bench']['orders'][fault]['told'])
        stock = kit.stock(j.c, item)
        act(j, 'rp_fix', task=tid, fault=fault)
        b = j.get(tid)['bench']
        self.assertTrue(b['orders'][fault]['used'])
        self.assertEqual(kit.stock(j.c, item), stock)                   # the ordered unit, not the shelf's
        self.assertEqual(b['fixcost'][fault], cost)
        self.finish(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        keys = [x['key'] for x in self.review(j, tid)['feedback']['criteria']]
        self.assertIn('speed', keys)                                   # never shelved: judged on waiting at the counter
        roundtrip(j)

    def test_order_rules(self):
        j = plain_journey(lambda t: t['_fault'] == 'capacitor')
        tid = j.task['id']
        act(j, 'ask', task=tid)
        n = j.task['needs']
        act(j, 'rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=False)
        act(j, 'rp_diagnose', task=tid, fault='capacitor')
        with self.assertRaises(GameError) as ctx:
            act(j, 'rp_order', task=tid, fault='capacitor', confirm=True)
        self.assertIn('duyệt báo giá', ctx.exception.message)
        with self.assertRaises(GameError):
            act(j, 'rp_order', task=tid, fault='motor', confirm=True)
        j2 = plain_journey(lambda t: t['_fault'] == 'bearing')
        tid2, fault2, _ = self.quoted(j2, 'none')
        with self.assertRaises(GameError) as ctx:
            act(j2, 'rp_order', task=tid2, fault=fault2, confirm=True)
        self.assertIn('không đặt riêng', ctx.exception.message)

    def test_unused_order_goes_to_the_shelf_when_the_device_is_returned(self):
        j = plain_journey(lambda t: t['_fault'] == 'capacitor')
        tid, fault, item = self.quoted(j, 'compatible')
        act(j, 'rp_order', task=tid, fault=fault, confirm=True)
        act(j, 'rp_return', task=tid, confirm=True)
        self.assertEqual(kit.stock(j.c, item), 1)
        self.assertTrue(j.get(tid)['bench']['orders'][fault]['used'])
        roundtrip(j)

    # --- shelf, calls, promises ---------------------------------------------------
    def genuine_battery(self):
        j = plain_journey(lambda t: t['_fault'] == 'battery' and t['needs']['genuine_only'], days=range(2, 25))
        tid, fault, item = self.quoted(j, 'genuine')
        r = act(j, 'rp_order', task=tid, fault=fault, confirm=True)
        self.assertIn('ngày kia', r['message'])
        return j, tid, fault

    def test_city_part_shelf_honest_call_and_pickup_on_the_moved_day(self):
        j, tid, fault = self.genuine_battery()
        day = j.c['day']
        r = act(j, 'rp_shelf', task=tid, days=1, confirm=True)
        self.assertIn('#001', r['message'])
        self.assertIn('Đồ chưa về kịp', r['message'])
        t = j.get(tid)
        self.assertTrue(t['deferred'])
        self.assertNotEqual(j.c['active_task'], tid)
        self.assertEqual(care_view(j, tid)['promise'], 'mai')
        roundtrip(j)
        new_day(j)
        v = care_view(j, tid)
        self.assertTrue(v['call'])
        self.assertTrue(j.get(tid)['deferred'])
        self.assertIn(tid, care_view(j)['shelf'])
        turn = j.c['turn']
        r = act(j, 'rp_answer', task=tid, reply='truth')
        self.assertEqual(j.c['turn'], turn)                            # a phone call takes no turn
        self.assertIn('sáng mai', r['message'])
        sh = j.get(tid)['bench']['shelf']
        self.assertEqual((sh['promise'], sh['moved'], sh['call']), (day + 2, 1, None))
        with self.assertRaises(GameError):
            act(j, 'rp_answer', task=tid, reply='truth')
        new_day(j)
        self.assertTrue(j.get(tid)['bench']['orders'][fault]['told'])  # arrived overnight
        act(j, 'rp_answer', task=tid, reply='truth')
        self.assertEqual(j.get(tid)['bench']['shelf']['moved'], 1)
        r = self.finish(j, tid)
        self.assertIn('đúng hẹn', r['message'])
        post = self.review(j, tid)
        row = next(x for x in post['feedback']['criteria'] if x['key'] == 'promise')
        self.assertEqual(row['score'], 4)
        self.assertNotIn('speed', [x['key'] for x in post['feedback']['criteria']])
        rec = R._data(j.c)['regulars'][j.get(tid)['npc']]
        self.assertEqual((rec['visits'], rec['ontime'], rec['late'], rec['trust']), (1, 1, 0, 1))
        self.assertEqual(rec['history'][-1]['grade'], 'genuine')
        self.assertEqual(R._data(j.c)['pickups_on_time'], 1)
        roundtrip(j)

    def test_soothing_lie_and_late_pickup_cost_trust(self):
        j, tid, fault = self.genuine_battery()
        act(j, 'rp_shelf', task=tid, days=0, confirm=True)
        new_day(j)                                                      # promised yesterday: late once
        self.assertEqual(j.get(tid)['bench']['shelf']['late'], 1)
        r = act(j, 'rp_answer', task=tid, reply='soothe')
        self.assertIn('chiều nay xong', r['message'])
        sh = j.get(tid)['bench']['shelf']
        self.assertTrue(sh['lied'])
        self.assertEqual(sh['promise'], j.c['day'])
        new_day(j)
        self.assertEqual(j.get(tid)['bench']['shelf']['late'], 2)
        self.finish(j, tid)
        t = j.get(tid)
        slip = next(x for x in t['slips'] if x['code'] == 'late_pickup')
        self.assertEqual(slip['sev'], 2)
        row = next(x for x in self.review(j, tid)['feedback']['criteria'] if x['key'] == 'promise')
        self.assertEqual(row['score'], 2)
        rec = R._data(j.c)['regulars'][t['npc']]
        self.assertEqual((rec['late'], rec['trust']), (1, 0))
        roundtrip(j)

    def test_devices_left_at_closing_stay_overnight_and_unanswered_calls_count(self):
        j = plain_journey(lambda t: t['_fault'] == 'capacitor')
        tid = j.task['id']
        act(j, 'ask', task=tid)
        n = j.task['needs']
        act(j, 'rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=False)
        r = j.act('end_day', carry_event=True)
        sh = j.get(tid)['bench']['shelf']
        self.assertTrue(sh['auto'])
        self.assertEqual(sh['promise'], j.c['day'])                    # the day has already turned: "mai" is today
        self.assertTrue(any('qua đêm' in line for line in r['summary']['career']['lines']))
        j.act('start_day')
        self.assertEqual(j.get(tid)['bench']['shelf']['call'], j.c['day'])
        self.assertNotEqual(j.c['active_task'], tid)
        new_day(j)
        sh = j.get(tid)['bench']['shelf']
        self.assertEqual((sh['missed'], sh['late']), (1, 1))
        roundtrip(j)

    def test_shelf_rules(self):
        j = Journey('repair')
        tids = [t['id'] for t in j.c['tasks']]
        self.assertGreaterEqual(len(tids), 3)
        with self.assertRaises(GameError):
            act(j, 'rp_shelf', task=tids[0], days=1, confirm=True)     # not asked yet
        for tid in tids[:3]:
            act(j, 'ask', task=tid)
            t = j.get(tid)
            if t['needs'].get('case') == 'buyin':
                continue
            n = t['needs']
            act(j, 'rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=n['device'] in R.DATA_DEVICES)
        ready = [tid for tid in tids[:3] if j.get(tid)['bench']['intake']]
        for bad in (True, 5, '1', None, -1):
            with self.assertRaises(GameError):
                act(j, 'rp_shelf', task=ready[0], days=bad, confirm=True)
        with self.assertRaises(GameError):
            act(j, 'rp_shelf', task=ready[0], days=1)                  # confirm
        with self.assertRaises(GameError):
            act(j, 'rp_answer', task=ready[0], reply='truth')          # nobody called
        act(j, 'rp_shelf', task=ready[0], days=1, confirm=True)
        with self.assertRaises(GameError):
            act(j, 'rp_shelf', task=ready[0], days=2, confirm=True)    # already there
        if len(ready) >= 3:
            act(j, 'rp_shelf', task=ready[1], days=2, confirm=True)
            with self.assertRaises(GameError) as ctx:
                act(j, 'rp_shelf', task=ready[2], days=1, confirm=True)
            self.assertIn('đủ', ctx.exception.message)
        roundtrip(j)

    # --- tools --------------------------------------------------------------------
    def test_flat_meter_battery_wastes_the_test_until_replaced(self):
        j = plain_journey(lambda t: t['_fault'] == 'capacitor')
        tid = j.task['id']
        act(j, 'ask', task=tid)
        n = j.task['needs']
        act(j, 'rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=False)
        for step in R.DEVICES['fan']['safety']:
            act(j, 'rp_safety', task=tid, step=step)
        act(j, 'rp_open', task=tid)
        R._data(j.c)['tools']['meter'] = 15
        r = act(j, 'rp_test', task=tid, test='cap_meter')
        self.assertIn('nhảy loạn', r['message'])
        self.assertEqual(j.get(tid)['bench']['tests'], [])
        self.assertEqual(R._data(j.c)['tools']['meter'], 9)
        with self.assertRaises(GameError):
            act(j, 'rp_tool', tool='meter', how='battery')             # confirm
        with self.assertRaises(GameError):
            act(j, 'rp_tool', tool='meter', how='clean', confirm=True)
        money = j.c['money']
        act(j, 'rp_tool', tool='meter', how='battery', confirm=True)
        self.assertEqual((R._data(j.c)['tools']['meter'], j.c['money']), (100, money - R.METER_COST))
        act(j, 'rp_test', task=tid, test='cap_meter')
        self.assertEqual(len(j.get(tid)['bench']['tests']), 1)
        self.assertEqual(R._data(j.c)['tools']['meter'], 100 - R.METER_WEAR)
        roundtrip(j)

    def test_worn_soldering_tip_costs_solder_and_can_come_back(self):
        j = plain_journey(lambda t: 'solder' in R._fault_def(t['needs']['device'], t['_fault'])['supplies'] and not t['_extra'])
        tid, fault, item = self.quoted(j, next(g for g in R._fault_def(j.task['needs']['device'], j.task['_fault'])['parts']
                                                 if g not in ('genuine', 'used')), drain_part=False)
        tools = R._data(j.c)['tools']
        tools['tip'] = 0
        for step in R.DEVICES[j.task['needs']['device']]['safety']:
            act(j, 'rp_safety', task=tid, step=step)
        act(j, 'rp_open', task=tid)
        with self.assertRaises(GameError) as ctx:
            act(j, 'rp_fix', task=tid, fault=fault)
        self.assertIn('Mũi hàn', ctx.exception.message)
        act(j, 'rp_tool', tool='tip', how='clean')
        self.assertEqual(R._data(j.c)['tools']['tip'], R.TIP_CLEAN)
        solder = kit.stock(j.c, 'solder')
        act(j, 'rp_fix', task=tid, fault=fault)
        self.assertEqual(kit.stock(j.c, 'solder'), solder - 2)
        self.assertTrue(j.get(tid)['bench']['cold'])
        self.assertEqual(R._data(j.c)['tools']['tip'], R.TIP_CLEAN - R.TIP_WEAR)
        R._data(j.c)['tools']['tip'] = 90
        with self.assertRaises(GameError):
            act(j, 'rp_tool', tool='tip', how='clean')                 # still shiny
        money = j.c['money']
        act(j, 'rp_tool', tool='tip', how='replace', confirm=True)
        self.assertEqual((R._data(j.c)['tools']['tip'], j.c['money']), (100, money - R.TIP_COST))
        roundtrip(j)

    # --- comebacks ----------------------------------------------------------------
    def comeback_journey(self):
        """An everyday job whose seeded roll brings it back after an untested, cheap repair."""
        for day in range(1, 30):
            for slot in range(6):
                t = R.make_task(day, slot, 1)
                if t['needs'].get('case') or t['_extra'] or t['_fault'] not in ('chain', 'tube', 'brake', 'dirt', 'bearing'):
                    continue
                grade = next(iter(R._fault_def(t['needs']['device'], t['_fault'])['parts']))
                if kit.rng('repair', 'back', t['id']).random() < R.GRADE_RISK[grade] + 0.3:
                    j = Journey('repair', slot=slot, day=day)
                    return j, grade
        raise AssertionError('no comeback job')

    def test_untested_cheap_repair_comes_back_and_is_honoured(self):
        j, grade = self.comeback_journey()
        tid, fault, _ = self.quoted(j, grade, drain_part=False)
        self.finish(j, tid, test=False)
        d = R._data(j.c)
        row = d['comebacks'][0]
        self.assertEqual((row['state'], row['cause'], row['task']), ('wait', 'untested', tid))
        self.assertEqual(public_state(j.state)['careers']['repair']['data']['comebacks'], [])   # not yet at the counter
        roundtrip(j)
        while R._data(j.c)['comebacks'][0]['state'] == 'wait':
            new_day(j)
        pub = public_state(j.state)['careers']['repair']['data']['comebacks'][0]
        self.assertFalse(pub['covered'])                               # no warranty slip on an untested hand-over
        with self.assertRaises(GameError):
            act(j, 'rp_back', id=row['id'], choice='redo')             # confirm
        with self.assertRaises(GameError):
            act(j, 'rp_back', id='nope', choice='redo', confirm=True)
        money = j.c['money']
        r = act(j, 'rp_back', id=row['id'], choice='redo', confirm=True)
        self.assertEqual(j.c['money'], money - pub['cost'])
        self.assertIn('hết hạn', r['message'])
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == row['id'])
        self.assertEqual(post['stars'], 5)
        self.assertEqual(R._data(j.c)['comebacks'], [])
        roundtrip(j)

    def test_charging_a_covered_comeback_and_ignoring_one(self):
        j, grade = self.comeback_journey()
        tid, fault, _ = self.quoted(j, grade, drain_part=False)
        self.finish(j, tid, test=False)
        d = R._data(j.c)
        row = d['comebacks'][0]
        row['days'] = 30                                                # as if a 30-day slip had been written
        extra = dict(row, id='BL-extra')
        d['comebacks'].append(extra)
        rec = d['regulars'].setdefault(row['npc'], dict(visits=1, trust=0, ontime=0, late=0, history=[]))
        rec['trust'] = 3
        while R._data(j.c)['comebacks'][0]['state'] == 'wait':
            new_day(j)
        money = j.c['money']
        cost, price = R._back_fee(j.c, row)
        act(j, 'rp_back', id=row['id'], choice='charge', confirm=True)
        self.assertEqual(j.c['money'], money + price)
        self.assertEqual(R._data(j.c)['regulars'][row['npc']]['trust'], 1)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == row['id'])
        self.assertEqual(post['stars'], 1)
        r = j.act('end_day', carry_event=True)                          # nobody saw the other one
        self.assertEqual(R._data(j.c)['comebacks'], [])
        self.assertEqual(R._data(j.c)['regulars'][row['npc']]['trust'], 0)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == 'BL-extra')
        self.assertEqual(post['stars'], 2)
        roundtrip(j)

    def test_genuine_part_never_comes_back(self):
        self.assertEqual(R.GRADE_RISK['genuine'], 0.0)
        j, tid, fault = self.genuine_battery()
        new_day(j)
        new_day(j)
        self.finish(j, tid)
        self.assertEqual(R._data(j.c)['comebacks'], [])

    # --- regulars -----------------------------------------------------------------
    def test_trusted_regular_waits_calmer_and_stretches_the_budget(self):
        j = plain_journey(lambda t: t['_fault'] == 'capacitor')
        t = j.task
        tid = t['id']
        j.c['life']['prices']['fan'] = 54                               # labour 43 + part 6 = 49 xu, budget 45
        act(j, 'ask', task=tid)
        n = t['needs']
        act(j, 'rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=False)
        act(j, 'rp_diagnose', task=tid, fault='capacitor')
        r = act(j, 'rp_quote', task=tid, grades={'capacitor': 'compatible'})
        self.assertFalse(r['accepted'])
        R._data(j.c)['regulars'][t['npc']] = dict(visits=4, trust=3, ontime=2, late=0, history=[])
        r = act(j, 'rp_quote', task=tid, grades={'capacitor': 'compatible'})
        self.assertTrue(r['accepted'], r['message'])
        self.assertIn('tiệm quen', r['message'])
        fresh = R.make_task(t['day'], 5, 1)
        fresh['npc'] = t['npc']
        R.on_task(j.state, j.c, fresh)
        base = max(60, 100 - 4 * kit.tier(t['day']) - (8 if R._today(j.c)['id'] == 'market' else 0))
        self.assertEqual(fresh['patience'], min(100, base + 3 * R.TRUST_PATIENCE))
        roundtrip(j)

    def test_clean_repair_builds_the_regulars_card(self):
        j = plain_journey(lambda t: t['_fault'] == 'capacitor')
        tid, fault, item = self.quoted(j, 'compatible', drain_part=False)
        r = self.finish(j, tid)
        rec = R._data(j.c)['regulars'][j.get(tid)['npc']]
        self.assertEqual((rec['visits'], rec['trust']), (1, 1))
        self.assertIn('💛', r['message'])
        self.assertEqual(rec['history'][0]['fault'], 'capacitor')

    # --- saves ----------------------------------------------------------------------
    def test_old_save_without_care_fields_migrates(self):
        j = plain_journey(lambda t: t['_fault'] == 'capacitor')
        tid = j.task['id']
        d = j.c['ext']['data']
        for k in R.DATA_V3:
            d.pop(k, None)
        for k in R.BENCH_V3:
            j.task['bench'].pop(k, None)
        old = json.loads(json.dumps(j.state))
        validate_state(old)
        public_state(json.loads(json.dumps(j.state)))
        act(j, 'ask', task=tid)
        n = j.get(tid)['needs']
        act(j, 'rp_intake', task=tid, marks=n['marks'], accessories=n['accessories'], consent=False)
        self.assertIn('shelf', j.get(tid)['bench'])
        self.assertEqual(R._data(j.c)['tools'], dict(tip=100, meter=100))
        self.assertIsNotNone(R._data(j.c)['clock'])                    # a shift opened before the clock starts it now
        roundtrip(j)

    def test_tampered_care_fields_are_rejected(self):
        j, tid, fault = self.genuine_battery()
        act(j, 'rp_shelf', task=tid, days=1, confirm=True)
        roundtrip(j)
        bad = []
        def tweak(fn):
            st = copy.deepcopy(j.state)
            c = st['careers']['repair']
            t = next(x for x in c['tasks'] if x['id'] == tid)
            fn(c, c['ext']['data'], t['bench'])
            bad.append(st)
        tweak(lambda c, d, b: b['shelf'].update(promise=b['shelf']['since'] - 1))
        tweak(lambda c, d, b: b['shelf'].update(lied='yes'))
        tweak(lambda c, d, b: b['orders'][fault].update(src='lam'))
        tweak(lambda c, d, b: b['orders'][fault].update(item='screen_g'))
        tweak(lambda c, d, b: b['orders'][fault].update(cost=-1))
        tweak(lambda c, d, b: b.update(cold=1))
        tweak(lambda c, d, b: d['tools'].update(tip=150))
        tweak(lambda c, d, b: d['tools'].update(hammer=5))
        tweak(lambda c, d, b: d['regulars'].update(repair_npc_07=dict(visits=1, trust=0, ontime=0, late=0, history=[])))
        tweak(lambda c, d, b: d['regulars'].update(repair_npc_01=dict(visits=1, trust=9, ontime=0, late=0, history=[])))
        tweak(lambda c, d, b: d.update(clock=dict(day=1)))
        tweak(lambda c, d, b: d.update(comebacks=[dict(id='BL-1', task='x', npc='repair_npc_01', device='fan', fault='capacitor',
                                                       grade='compatible', days=30, paid=10, handed=2, due=40, cause='part',
                                                       state='here', title='Quạt')]))
        tweak(lambda c, d, b: d.update(comebacks=[dict(id='BL-1', task='x', npc='repair_npc_01', device='fan', fault='capacitor',
                                                       grade='compatible', days=30, paid=10, handed=2, due=4, cause='ghost',
                                                       state='here', title='Quạt')]))
        tweak(lambda c, d, b: d.update(shelf_seq=-1))
        for st in bad:
            with self.assertRaises(GameError):
                validate_state(json.loads(json.dumps(st)))


if __name__ == '__main__':
    unittest.main()
