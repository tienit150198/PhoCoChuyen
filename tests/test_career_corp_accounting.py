import copy
import json
import unittest

from game import employment
from game.careers import corp_accounting as CA
from game.careers import kit, office
from game.content import make_task
from game.engine import GameError, apply_action, new_state, public_state, validate_state
from tests.helpers import Journey

CAR = 'corp_accounting'


def answer(st):
    """The correct answer for a step, in the shape the client sends."""
    if st['kind'] == 'entry':
        return [dict(debit=d, credit=c, amount=a) for d, c, a in st['_key']]
    return copy.deepcopy(st['_key'])


def slot_for(kind, start=1):
    return next((d, s) for d in range(start, 60) for s in range(4) if CA._kind(d, s) == kind)


def day_with(mod_id):
    return next(d for d in range(1, 80) if CA._mod(d)['id'] == mod_id)


def roundtrip(j):
    validate_state(json.loads(json.dumps(j.state)))


class CorpAccountingTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey(CAR)

    def open_all(self, tid):
        for d in self.j.get(tid)['docs']:
            self.j.act('ca_open', task=tid, doc=d['id'])

    def stamp_right(self, tid, case):
        tr = case['_truth']
        if tr['v'] != 'approve':
            self.j.act('ca_circle', task=tid, case=case['id'], zone=tr['z'][0])
        return self.j.act('ca_stamp', task=tid, case=case['id'], verdict=tr['v'])

    def solve(self, tid=None, note='specific'):
        j = self.j
        tid = tid or j.task['id']
        j.act('ask', task=tid)
        self.open_all(tid)
        t = j.get(tid)
        if t['variant'] == 'desk':
            for case in t['cases']:
                r = self.stamp_right(tid, case)
                self.assertTrue(r['correct'], (case['_k'], r))
            return j.act('ca_submit', task=tid, confirm=True)
        for st in t['proc']:
            r = j.act('ca_step', task=tid, step=st['id'], answer=answer(st))
            self.assertTrue(r['correct'], (st['id'], r))
        return j.act('ca_submit', task=tid, note=note, confirm=True)

    def use(self, kind, start=1):
        day, slot = slot_for(kind, start)
        self.j = Journey(CAR, slot=slot, day=day)
        self.assertEqual(self.j.task['variant'], kind)
        return self.j.task['id']

    def use_day(self, day, kind='desk'):
        slot = next(s for s in range(4) if CA._kind(day, s) == kind)
        self.j = Journey(CAR, slot=slot, day=day)
        return self.j.task['id']

    @property
    def office(self):
        return self.j.c['ext']['data']['office']

    # ------------------------------------------------------------ happy paths
    def test_first_day_starts_with_the_desk(self):
        t = self.j.task
        self.assertEqual(t['variant'], 'desk')
        self.assertEqual(t['gen'], CA.GEN)
        self.assertEqual(len(t['cases']), 3)
        self.assertEqual(t['due'], office.DUE[0])
        self.assertEqual([x['due'] for x in self.j.c['tasks']], list(office.DUE[:len(self.j.c['tasks'])]))

    def test_dossier_happy_path_review_and_money(self):
        tid = self.use('journal')
        j = self.j
        money = j.c['money']
        r = self.solve(tid)
        self.assertIn('+30', r['message'])
        self.assertIn('Kịp hạn', r['message'])
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertFalse(t['late'])
        self.assertEqual(j.c['money'], money + 30)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        self.assertEqual(post['stars'], 5)
        self.assertEqual({x['key'] for x in post['feedback']['criteria']}, {'accuracy', 'independence', 'speed', 'handover'})
        d = j.c['ext']['data']
        self.assertEqual(d['done'], 1)
        self.assertIn(CA.KINDS[t['variant']]['milestone'], d['milestones'])
        self.assertEqual(self.office['trust'], office.TRUST_START + 2)
        roundtrip(j)

    def test_desk_happy_path(self):
        j = self.j
        tid = j.task['id']
        money = j.c['money']
        r = self.solve(tid)
        self.assertIn('+30', r['message'])
        self.assertIn('sạch khay', r['message'])
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual(set(t['results'].values()), {'ok'})
        bad = sum(1 for x in t['cases'] if x['_truth']['v'] != 'approve')
        d = j.c['ext']['data']
        self.assertEqual(d['catches'], bad)
        self.assertEqual(d['desks'], 1)
        self.assertEqual(j.c['money'], money + 30)
        self.assertEqual(self.office['trust'], office.TRUST_START + bad + 2)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        self.assertEqual({x['key'] for x in post['feedback']['criteria']}, {'accuracy', 'vigilance', 'grounds', 'speed'})
        self.assertEqual(post['stars'], 5)
        roundtrip(j)

    def test_every_kind_solvable_and_saves(self):
        for kind in CA.KINDS:
            with self.subTest(kind=kind):
                tid = self.use(kind)
                self.solve(tid)
                self.assertEqual(self.j.get(tid)['status'], 'completed')
                self.assertEqual(sum(self.j.c['ext']['data']['ledger'].values()), 0)
                roundtrip(self.j)

    def test_generation_deterministic_and_json_safe(self):
        for day in range(1, 31):
            for slot in range(6):
                a, b = CA.make_task(day, slot, 1), CA.make_task(day, slot, 7)
                self.assertEqual(a['proc'], b['proc'])
                self.assertEqual(a['docs'], b['docs'])
                self.assertEqual(a.get('cases'), b.get('cases'))
                self.assertEqual(json.loads(json.dumps(a)), a)
                for st in a['proc']:
                    if st['kind'] == 'entry':
                        for d, c, amt in st['_key']:
                            self.assertNotEqual(d, c)
                            self.assertGreater(amt, 0)
                for x in a.get('cases') or []:
                    tr = x['_truth']
                    self.assertIn(tr['v'], CA.VERDICTS)
                    self.assertTrue(set(tr['z']) <= set(x['zones']))
                    self.assertTrue(tr['v'] == 'approve' or tr['z'])
                    self.assertTrue(tr['why'])

    def test_every_case_kind_appears_and_desk_grows(self):
        seen = set()
        for day in range(1, 61):
            for slot in range(4):
                t = CA.make_task(day, slot, 1)
                if t['variant'] == 'desk':
                    seen |= {x['_k'] for x in t['cases']}
                    self.assertTrue(any(x['_truth']['v'] == 'approve' for x in t['cases']))
                    self.assertTrue(any(x['_truth']['v'] != 'approve' for x in t['cases']))
        self.assertEqual(seen, set(CA.CASE_KINDS))
        self.assertLess(CA.desk_size(1, 'normal'), CA.desk_size(12, 'normal'))
        day1 = CA.make_task(1, 0, 1)
        self.assertTrue({x['_k'] for x in day1['cases']} <= {'ok_inv', 'ok_req', 'dup', 'nosign', 'fake_mst'})

    # ------------------------------------------------------------ hidden information
    def test_brief_docs_and_answers_hidden(self):
        tid = self.use('journal')
        j = self.j
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertIsNone(view['docs'])
        self.assertIsNone(view['proc'])
        self.assertIsNone(view['brief'])
        j.act('ask', task=tid)
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        blob = json.dumps(view, ensure_ascii=False)
        self.assertNotIn('_key', blob)
        self.assertNotIn('_handover', blob)
        self.assertTrue(all(d.get('closed') for d in view['docs']))
        self.assertTrue(all(set(d) == {'id', 'type', 'title', 'source', 'closed'} for d in view['docs']))
        cur = next(s for s in view['proc'] if s['state'] == 'current')
        self.assertNotIn('explain', cur)
        for st in view['proc']:
            if st['state'] == 'locked':
                self.assertEqual(set(st), {'id', 'kind', 'title', 'state'})
        self.assertIsNone(view['handover_options'])
        j.act('ca_open', task=tid, doc=view['docs'][0]['id'])
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertNotIn('closed', view['docs'][0])

    def test_desk_truth_hidden_until_stamped(self):
        j = self.j
        tid = j.task['id']
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertIsNone(view['cases'])
        j.act('ask', task=tid)
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        blob = json.dumps(view, ensure_ascii=False)
        for secret in ('_truth', '_k', 'oops', '"why"'):
            self.assertNotIn(secret, blob)
        self.assertTrue(all(c['stamp'] is None and 'truth' not in c for c in view['cases']))
        case = j.get(tid)['cases'][0]
        self.stamp_right(tid, case)
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        first = next(c for c in view['cases'] if c['id'] == case['id'])
        self.assertEqual(first['truth']['v'], case['_truth']['v'])
        self.assertEqual(first['result'], 'ok')
        self.assertTrue(all('truth' not in c for c in view['cases'] if c['id'] != case['id']))
        self.assertNotIn('oops', json.dumps(view, ensure_ascii=False))

    def test_actions_need_known_task(self):
        with self.assertRaises(GameError):
            self.j.act('ca_open', task=self.j.task['id'], doc='x')
        with self.assertRaises(GameError):
            self.j.act('ca_stamp', task=self.j.task['id'], case='c1', verdict='approve')

    # ------------------------------------------------------------ the desk: stamps, circles, consequences
    def bad_case(self, tid, verdict=None):
        return next(x for x in self.j.get(tid)['cases'] if x['_truth']['v'] != 'approve' and (verdict is None or x['_truth']['v'] == verdict))

    def test_reject_needs_a_circle_and_the_right_reason(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        case = self.bad_case(tid)
        with self.assertRaises(GameError) as cm:
            j.act('ca_stamp', task=tid, case=case['id'], verdict=case['_truth']['v'])
        self.assertIn('Khoanh', cm.exception.message)
        self.assertEqual(j.get(tid)['mistakes'], 0)
        wrong_zone = next(z for z in case['zones'] if z not in case['_truth']['z'])
        j.act('ca_circle', task=tid, case=case['id'], zone=wrong_zone)
        r = j.act('ca_stamp', task=tid, case=case['id'], verdict=case['_truth']['v'])
        self.assertFalse(r['correct'])
        self.assertEqual(r['result'], 'reason')
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertEqual(j.c['ext']['data']['catches'], 0)
        with self.assertRaises(GameError):
            j.act('ca_stamp', task=tid, case=case['id'], verdict='approve')
        roundtrip(j)

    def test_wrong_approval_fines_and_costs_trust(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        case = self.bad_case(tid)
        money = j.c['money']
        r = j.act('ca_stamp', task=tid, case=case['id'], verdict='approve')
        self.assertEqual(r['result'], 'wrong')
        fine = min(case['_truth']['fine'], money)
        self.assertEqual(j.c['money'], money - fine)
        self.assertIn(case['_truth']['oops'], r['message'])
        self.assertEqual(self.office['trust'], office.TRUST_START - 4)
        self.assertEqual(self.office['fines'], fine)
        entry = j.c['ops']['finance']['ledger'][-1]
        self.assertEqual((entry['amount'], entry['category']), (-fine, 'penalty'))
        self.assertEqual(j.c['ext']['data']['slips'], 1)
        roundtrip(j)

    def test_fine_never_exceeds_the_wallet(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        j.c['ops']['finance']['opening_balance'] += 3 - j.c['money']
        j.c['money'] = 3
        validate_state(j.state)
        case = self.bad_case(tid)
        j.act('ca_stamp', task=tid, case=case['id'], verdict='approve')
        self.assertEqual(j.c['money'], 0)
        self.assertEqual(self.office['fines'], 3)

    def test_rejecting_a_valid_document_hurts_trust(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        case = next(x for x in j.get(tid)['cases'] if x['_truth']['v'] == 'approve')
        j.act('ca_circle', task=tid, case=case['id'], zone=case['zones'][0])
        money = j.c['money']
        r = j.act('ca_stamp', task=tid, case=case['id'], verdict='reject')
        self.assertEqual(r['result'], 'wrong')
        self.assertEqual(j.c['money'], money)
        self.assertEqual(self.office['trust'], office.TRUST_START - 2)

    def test_circles_toggle_limit_and_lock(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        case = j.get(tid)['cases'][0]
        zones = case['zones']
        for z in zones[:3]:
            self.assertTrue(j.act('ca_circle', task=tid, case=case['id'], zone=z)['circled'])
        with self.assertRaises(GameError):
            j.act('ca_circle', task=tid, case=case['id'], zone=zones[3])
        self.assertFalse(j.act('ca_circle', task=tid, case=case['id'], zone=zones[0])['circled'])
        self.assertEqual(j.get(tid)['circles'][case['id']], zones[1:3])
        for bad in ('nope', 5, None, ['seller']):
            with self.subTest(zone=bad), self.assertRaises(GameError):
                j.act('ca_circle', task=tid, case=case['id'], zone=bad)
        with self.assertRaises(GameError):
            j.act('ca_circle', task=tid, case='c99', zone=zones[0])
        for v in ('stamp', None, 1):
            with self.subTest(verdict=v), self.assertRaises(GameError):
                j.act('ca_stamp', task=tid, case=case['id'], verdict=v)
        self.stamp_right(tid, case) if case['_truth']['v'] == 'approve' else j.act('ca_stamp', task=tid, case=case['id'], verdict='escalate')
        with self.assertRaises(GameError):
            j.act('ca_circle', task=tid, case=case['id'], zone=zones[0])
        roundtrip(j)

    def test_desk_submit_needs_every_stamp(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        cases = j.get(tid)['cases']
        self.stamp_right(tid, cases[0])
        with self.assertRaises(GameError):
            j.act('ca_submit', task=tid, confirm=True)
        for case in cases[1:]:
            self.stamp_right(tid, case)
        with self.assertRaises(GameError):
            j.act('ca_submit', task=tid)
        j.act('ca_submit', task=tid, confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        with self.assertRaises(GameError):
            j.act('ca_stamp', task=tid, case=cases[0]['id'], verdict='approve')

    def test_desk_hint_points_to_the_right_book(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        case = self.bad_case(tid)
        clock = self.office['clock']
        r = j.act('ca_hint', task=tid, case=case['id'])
        self.assertIn(CA.DESK_HINTS[case['_k']], r['message'])
        self.assertEqual(self.office['clock'], clock + office.COST['hint'])
        self.assertIn(case['id'], j.get(tid)['tips'])
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertTrue(next(c for c in view['cases'] if c['id'] == case['id'])['hinted'])

    def test_tampered_desk_rejected(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        case = self.bad_case(tid)
        self.stamp_right(tid, case)
        for mutate in (
            lambda t: t['cases'][0]['_truth'].__setitem__('v', 'approve' if t['cases'][0]['_truth']['v'] != 'approve' else 'reject'),
            lambda t: t['cases'][0]['paper'].__setitem__('title', 'Giả'),
            lambda t: t['results'].__setitem__(case['id'], 'wrong'),
            lambda t: t['stamps'].__setitem__(case['id'], 'approve'),
            lambda t: t['stamps'].__setitem__('c99', 'approve'),
            lambda t: t['circles'].__setitem__(case['id'], ['nowhere']),
            lambda t: t['circles'].__setitem__(case['id'], []),
            lambda t: t.__setitem__('status', 'completed'),
            lambda t: t.__setitem__('tips', ['c99']),
            lambda t: t.__setitem__('due', 5),
        ):
            s = copy.deepcopy(j.state)
            mutate(next(t for t in s['careers'][CAR]['tasks'] if t['id'] == tid))
            with self.assertRaises(GameError):
                validate_state(s)

    # ------------------------------------------------------------ rules that shift, luck of the day
    def test_rules_shift_between_months(self):
        r1, r6 = CA._rules_raw(1), CA._rules_raw(6)
        self.assertNotEqual(r1['limit'], r6['limit'])
        self.assertNotEqual(r1['blocked'], r6['blocked'])
        self.assertFalse(any(x['new'] for x in CA.rules(1)))
        self.assertFalse(any(x['new'] for x in CA.rules(2)))
        new6 = {x['id'] for x in CA.rules(6) if x['new']}
        self.assertTrue({'limit', 'blocked', 'vat'} <= new6)
        self.assertIn('split', {x['id'] for x in CA.rules(4) if x['new']})
        self.assertNotIn('vat', {x['id'] for x in CA.rules(11)})
        # The desk follows the rules of its month.
        t6 = CA.make_task(6, 0, 1)
        sig = next(d for d in t6['docs'] if d['id'] == 'sig')
        self.assertIn(CA._n(r6['limit']), json.dumps(sig, ensure_ascii=False))

    def test_luck_of_the_day_is_deterministic_and_shapes_the_desk(self):
        self.assertEqual([CA._mod(d)['id'] for d in range(1, 6)], ['normal', 'intern', 'audit', 'boss_away', 'crunch'])
        self.assertEqual(CA._mod(10)['id'], 'crunch')
        self.assertEqual([CA._mod(d)['id'] for d in range(1, 40)], [CA._mod(d)['id'] for d in range(1, 40)])
        for d in range(6, 60):
            if (d - 1) % 5 != 4:
                self.assertNotEqual(CA._mod(d)['id'], CA._mod(d - 1)['id'])
        away = day_with('boss_away')
        self.assertIn('oral', {x['_k'] for x in CA.make_task(away, next(s for s in range(4) if CA._kind(away, s) == 'desk'), 1)['cases']})
        self.assertIn('math', {x['_k'] for x in CA.make_task(2, 1, 1)['cases']})

    def test_public_data_today_and_office(self):
        j = self.j
        data = public_state(j.state)['careers'][CAR]['data']
        self.assertEqual(data['period']['month'], 1)
        self.assertTrue(data['balanced'])
        self.assertEqual(data['today']['mod']['id'], 'normal')
        self.assertTrue(data['today']['rules'])
        self.assertEqual(data['office']['time'], '08:00')
        self.assertEqual(data['office']['trust'], office.TRUST_START)
        self.assertNotIn('day_stamps', data)
        content = CA.content()
        self.assertTrue(all(a['id'] in CA.ACCOUNT_NAME for a in content['accounts']))
        self.assertEqual([m['id'] for m in content['milestones']], CA.MILESTONE_IDS)

    # ------------------------------------------------------------ office clock, deadlines, overtime
    def test_clock_moves_with_work_and_lunch(self):
        tid = self.use('journal')
        j = self.j
        j.act('ask', task=tid)
        self.assertEqual(self.office['clock'], office.OPEN)
        j.act('ca_open', task=tid, doc=j.get(tid)['docs'][0]['id'])
        self.assertEqual(self.office['clock'], office.OPEN + office.COST['open'])
        j.act('ca_open', task=tid, doc=j.get(tid)['docs'][0]['id'])
        self.assertEqual(self.office['clock'], office.OPEN + office.COST['open'])
        self.open_all(tid)
        self.office['clock'] = office.LUNCH - 5
        st = j.get(tid)['proc'][0]
        r = j.act('ca_step', task=tid, step=st['id'], answer=answer(st))
        self.assertIn('Nghỉ trưa', r['message'])
        self.assertEqual(self.office['clock'], office.LUNCH - 5 + office.COST['step'] + office.LUNCH_MIN)

    def test_closing_time_blocks_work_until_overtime(self):
        tid = self.use('journal')
        j = self.j
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('ca_overtime', confirm=True)
        self.office['clock'] = office.CLOSE
        with self.assertRaises(GameError) as cm:
            j.act('ca_open', task=tid, doc=j.get(tid)['docs'][0]['id'])
        self.assertEqual(cm.exception.code, 'office_closed')
        with self.assertRaises(GameError):
            j.act('ca_overtime')
        money = j.c['money']
        r = j.act('ca_overtime', confirm=True)
        self.assertIn('20:00', r['message'])
        self.assertEqual(j.c['money'], money + 12)
        self.assertEqual(j.c['ops']['finance']['ledger'][-1]['category'], 'overtime')
        with self.assertRaises(GameError):
            j.act('ca_overtime', confirm=True)
        j.act('ca_open', task=tid, doc=j.get(tid)['docs'][0]['id'])
        self.office['clock'] = office.LOCK
        with self.assertRaises(GameError):
            j.act('ca_open', task=tid, doc=j.get(tid)['docs'][1]['id'])
        roundtrip(j)
        j.act('end_day', carry_event=True)
        j.act('start_day')
        self.assertEqual(self.office['clock'], office.OPEN + office.TIRED_MIN)
        self.assertFalse(self.office['ot'])

    def test_crunch_day_overtime_earns_trust(self):
        tid = self.use_day(5)
        j = self.j
        j.act('ask', task=tid)
        self.office['clock'] = office.CLOSE
        trust = self.office['trust']
        money = j.c['money']
        j.act('ca_overtime', confirm=True)
        self.assertEqual(j.c['money'], money + 18)
        self.assertEqual(self.office['trust'], trust + 3)

    def test_late_dossier_loses_bonus_and_trust(self):
        tid = self.use('journal')
        j = self.j
        j.get(tid)['due'] = office.OPEN + 30
        r = self.solve(tid)
        self.assertIn('+22', r['message'])
        self.assertIn('Trễ hạn', r['message'])
        self.assertTrue(j.get(tid)['late'])
        self.assertEqual(self.office['trust'], office.TRUST_START - 3)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        self.assertEqual(next(x for x in post['feedback']['criteria'] if x['key'] == 'speed')['score'], 2)

    def test_leftovers_are_due_in_the_morning_and_cost_trust(self):
        j = self.j
        n = sum(1 for t in j.c['tasks'] if t['status'] != 'completed')
        r = j.act('end_day', carry_event=True)
        self.assertEqual(r['summary']['career']['office']['carried'], n)
        self.assertEqual(self.office['trust'], office.TRUST_START - min(6, 2 * n))
        j.act('start_day')
        old = [t for t in j.c['tasks'] if t['day'] == 1]
        self.assertTrue(old)
        self.assertTrue(all(t['due'] == office.CARRY_DUE and t['due_day'] == 2 for t in old))
        new = [t for t in j.c['tasks'] if t['day'] == 2]
        self.assertTrue(all(t['due'] in office.DUE + (office.CLOSE,) for t in new))
        roundtrip(j)

    def test_more_work_is_due_later_the_same_day(self):
        j = self.j
        for t in list(j.c['tasks'])[1:]:
            j.c['tasks'].remove(t)
        self.office.update(day=1, clock=office.OPEN + 200)
        validate_state(j.state)
        j.act('more_work')
        t = j.c['tasks'][-1]
        self.assertEqual(t['due'], office.OPEN + 200 + office.MORE_WORK_WINDOW)

    def test_boss_away_hints_are_slow_and_lag_doubles_reading(self):
        away = day_with('boss_away')
        tid = self.use_day(away, CA._kind(away, 0))
        j = self.j
        j.act('ask', task=tid)
        t = j.get(tid)
        clock = self.office['clock']
        payload = dict(task=tid, case=t['cases'][0]['id']) if t['variant'] == 'desk' else dict(task=tid)
        r = j.act('ca_hint', **payload)
        self.assertIn('15 phút', r['message'])
        self.assertEqual(self.office['clock'], clock + 15)
        lag = day_with('lag')
        tid = self.use_day(lag, CA._kind(lag, 0))
        j = self.j
        j.act('ask', task=tid)
        t = j.get(tid)
        clock = self.office['clock']
        j.act('ca_open', task=tid, doc=t['docs'][0]['id'])
        self.assertEqual(self.office['clock'], clock + 2 * office.COST['ref' if t['variant'] == 'desk' else 'open'])

    def test_audit_day_rewards_a_clean_desk(self):
        tid = self.use_day(3)
        j = self.j
        self.solve(tid)
        money = j.c['money']
        trust = self.office['trust']
        r = j.act('end_day', carry_event=True)
        audit = r['summary']['career']['audit']
        self.assertTrue(audit['ok'])
        self.assertTrue(any(e['category'] == 'audit_bonus' and e['amount'] == 10 for e in j.c['ops']['finance']['ledger']))
        self.assertTrue(any(p['kind'] == 'review' and p['npc'] == kit.npc_id(CAR, 4) for p in j.c['feed']))
        self.assertGreaterEqual(j.c['money'], money + 10)
        missed = len((r['summary']['career'].get('close') or {}).get('missed', []))   # the month-end close plan's due item
        self.assertEqual(r['summary']['career']['office']['trust'], min(100, trust + 3 - CA.CLOSE_MISS * missed))

    def test_audit_day_fines_a_slip(self):
        tid = self.use_day(3)
        j = self.j
        j.act('ask', task=tid)
        case = self.bad_case(tid)
        j.act('ca_stamp', task=tid, case=case['id'], verdict='approve')
        money = j.c['money']
        r = j.act('end_day', carry_event=True)
        audit = r['summary']['career']['audit']
        self.assertFalse(audit['ok'])
        self.assertEqual(audit['amount'], min(10, money))
        self.assertEqual(r['summary']['career']['desk']['slips'], 1)

    # ------------------------------------------------------------ validation of play (dossiers)
    def test_docs_must_be_opened_first(self):
        tid = self.use('journal')
        j = self.j
        j.act('ask', task=tid)
        first = j.get(tid)['proc'][0]
        self.assertTrue(first['docs'])
        with self.assertRaises(GameError) as cm:
            j.act('ca_step', task=tid, step=first['id'], answer=answer(first))
        self.assertIn('Mở chứng từ', cm.exception.message)
        self.assertEqual(j.get(tid)['mistakes'], 0)
        self.open_all(tid)
        self.assertTrue(j.act('ca_step', task=tid, step=first['id'], answer=answer(first))['correct'])

    def test_steps_in_order(self):
        tid = self.use('month_close')
        j = self.j
        j.act('ask', task=tid)
        self.open_all(tid)
        second = j.get(tid)['proc'][1]
        with self.assertRaises(GameError):
            j.act('ca_step', task=tid, step=second['id'], answer=answer(second))

    def test_wrong_answer_counts_mistake_and_lowers_bonus(self):
        tid = self.use('depreciation')
        j = self.j
        j.act('ask', task=tid)
        self.open_all(tid)
        st = j.get(tid)['proc'][0]
        wrong = copy.deepcopy(answer(st))
        if st['kind'] == 'fields':
            k = next(iter(wrong))
            wrong[k] += 10
        elif st['kind'] == 'number':
            wrong += 10
        else:
            self.skipTest('first step is not numeric')
        clock = self.office['clock']
        r = j.act('ca_step', task=tid, step=st['id'], answer=wrong)
        self.assertFalse(r['correct'])
        self.assertEqual(self.office['clock'], clock + office.COST['step'] + office.COST['wrong'])
        self.assertEqual(j.get(tid)['mistakes'], 1)
        for s in j.get(tid)['proc']:
            j.act('ca_step', task=tid, step=s['id'], answer=answer(s))
        money = j.c['money']
        r = j.act('ca_submit', task=tid, note='specific', confirm=True)
        self.assertIn('+20', r['message'])
        self.assertEqual(j.c['money'], money + 20)

    def test_wrong_fields_check_names_the_boxes_off(self):
        tid = self.use('depreciation')
        j = self.j
        j.act('ask', task=tid)
        self.open_all(tid)
        st = j.get(tid)['proc'][0]
        self.assertEqual(st['kind'], 'fields')
        wrong = copy.deepcopy(answer(st))
        k = sorted(wrong)[-1]
        wrong[k] += 10
        r = j.act('ca_step', task=tid, step=st['id'], answer=wrong)
        self.assertFalse(r['correct'])
        self.assertEqual(r['bad'], [k])

    def test_unbalanced_and_malformed_entries_rejected_without_mistake(self):
        tid = self.use('journal')
        j = self.j
        j.act('ask', task=tid)
        self.open_all(tid)
        st = j.get(tid)['proc'][0]
        d, c, a = st['_key'][0]
        bad = [
            dict(debit=[dict(account=d, amount=a)], credit=[dict(account=c, amount=a + 10)]),   # unbalanced
            [dict(debit='999', credit=c, amount=a)],                                           # unknown account
            [dict(debit=d, credit=d, amount=a)],                                               # same account both sides
            [dict(debit=d, credit=c, amount='100')],                                           # amount not int
            [dict(debit=d, credit=c, amount=0)],                                               # zero
            'Nợ 111',                                                                          # garbage
            [],
        ]
        for ans in bad:
            with self.subTest(ans=ans), self.assertRaises(GameError):
                j.act('ca_step', task=tid, step=st['id'], answer=ans)
        self.assertEqual(j.get(tid)['mistakes'], 0)
        with self.assertRaises(GameError) as cm:
            j.act('ca_step', task=tid, step=st['id'], answer=bad[0])
        self.assertIn('chưa cân', str(cm.exception.message))

    def test_wrong_entry_gives_diagnosis_and_right_compound_voucher_posts(self):
        tid = self.use('journal')
        j = self.j
        j.act('ask', task=tid)
        self.open_all(tid)
        st = j.get(tid)['proc'][0]
        d, c, a = st['_key'][0]
        other = next(x['id'] for x in st['accounts'] if x['id'] not in (d, c))
        r = j.act('ca_step', task=tid, step=st['id'], answer=[dict(debit=d, credit=other, amount=a)])
        self.assertFalse(r['correct'])
        self.assertIn('Bên Nợ chọn đúng', r['message'])
        deb, cre = {}, {}
        for dd, cc, aa in st['_key']:
            deb[dd] = deb.get(dd, 0) + aa
            cre[cc] = cre.get(cc, 0) + aa
        rows_d = []
        for acc, amt in deb.items():
            rows_d += [dict(account=acc, amount=amt - amt // 2)] + ([dict(account=acc, amount=amt // 2)] if amt // 2 else [])
        r = j.act('ca_step', task=tid, step=st['id'], answer=dict(debit=rows_d, credit=[dict(account=k, amount=v) for k, v in cre.items()]))
        self.assertTrue(r['correct'])
        led = j.c['ext']['data']['ledger']
        self.assertEqual(sum(led.values()), 0)
        for dd, cc, aa in st['_key']:
            self.assertIn(dd, led)
        self.assertEqual(j.c['ext']['data']['posted'], 1)
        roundtrip(j)

    def test_malformed_choice_and_number(self):
        tid = self.use('invoice_in')
        j = self.j
        j.act('ask', task=tid)
        self.open_all(tid)
        st = j.get(tid)['proc'][0]
        for ans in ('nope', ['nope'], 5, None, {'a': 1}):
            with self.subTest(ans=ans), self.assertRaises(GameError):
                j.act('ca_step', task=tid, step=st['id'], answer=ans)
        self.assertEqual(j.get(tid)['mistakes'], 0)

    def test_submit_requires_done_note_and_confirm(self):
        tid = self.use('journal')
        j = self.j
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('ca_submit', task=tid, note='specific', confirm=True)
        self.open_all(tid)
        for st in j.get(tid)['proc']:
            j.act('ca_step', task=tid, step=st['id'], answer=answer(st))
        with self.assertRaises(GameError):
            j.act('ca_step', task=tid, step=j.get(tid)['proc'][0]['id'], answer=answer(j.get(tid)['proc'][0]))
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertEqual([o['id'] for o in view['handover_options']], list(CA.HANDOVER))
        with self.assertRaises(GameError):
            j.act('ca_submit', task=tid, note='poem', confirm=True)
        with self.assertRaises(GameError):
            j.act('ca_submit', task=tid, note='short')
        j.act('ca_submit', task=tid, note='none', confirm=True)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        hand = next(x for x in post['feedback']['criteria'] if x['key'] == 'handover')
        self.assertEqual(hand['score'], 2)

    def test_hint_is_recorded_and_lowers_independence(self):
        tid = self.use('journal')
        j = self.j
        j.act('ask', task=tid)
        r = j.act('ca_hint', task=tid)
        self.assertIn('gợi ý', r['message'])
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        cur = next(s for s in view['proc'] if s['state'] == 'current')
        self.assertTrue(cur['tip'])
        self.open_all(tid)
        for st in j.get(tid)['proc']:
            j.act('ca_step', task=tid, step=st['id'], answer=answer(st))
        j.act('ca_submit', task=tid, note='specific', confirm=True)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review')
        ind = next(x for x in post['feedback']['criteria'] if x['key'] == 'independence')
        self.assertEqual(ind['score'], 4)

    # ------------------------------------------------------------ save integrity & old saves
    def test_tampered_fixed_fields_rejected(self):
        tid = self.use('journal')
        j = self.j
        j.act('ask', task=tid)
        for mutate in (
            lambda t: t['proc'][0].__setitem__('_key', 'x'),
            lambda t: t['docs'][0].__setitem__('title', 'Giả'),
            lambda t: t.__setitem__('_handover', 'khác'),
            lambda t: t.__setitem__('variant', 'month_close' if t['variant'] != 'month_close' else 'journal'),
            lambda t: t['proc_state'].__setitem__('at', 2),
            lambda t: t.__setitem__('inspected', ['zzz']),
            lambda t: t.__setitem__('handover', 'poem'),
            lambda t: t.__setitem__('gen', 1),
            lambda t: t.__setitem__('late', 'yes'),
        ):
            s = copy.deepcopy(j.state)
            mutate(s['careers'][CAR]['tasks'][0])
            with self.assertRaises(GameError):
                validate_state(s)

    def test_office_data_validated(self):
        for mutate in (lambda o: o.__setitem__('trust', 101), lambda o: o.__setitem__('clock', 5),
                       lambda o: o.__setitem__('ot', 'yes'), lambda o: o.__setitem__('notes', [1])):
            s = copy.deepcopy(self.j.state)
            validate_state(s)
            mutate(s['careers'][CAR]['ext']['data']['office'])
            with self.assertRaises(GameError):
                validate_state(s)

    def test_old_save_keeps_its_dossiers(self):
        j = self.j
        s = copy.deepcopy(j.state)
        c = s['careers'][CAR]
        # A save from before the desk: old data fields, old dossiers without a generator mark.
        old = CA.make_task(1, 0, kit.LEGACY_TURN + 3)
        self.assertNotIn('gen', old)
        self.assertEqual(old['variant'], 'journal')
        old['created_turn'] = 3
        c['tasks'] = [old]
        c['active_task'] = old['id']
        c['ext']['data'] = dict(ledger={}, entries=[], milestones=[], posted=0, closes=0, rejected=0, done=0, day_posted=0, day_done=0)
        public_state(s)                      # the page can show it before any action
        validate_state(s)
        self.assertGreaterEqual(c['tasks'][0]['created_turn'], kit.LEGACY_TURN)
        self.assertIn('office', c['ext']['data'])
        j.state = s
        tid = old['id']
        r = self.solve(tid)
        self.assertIn('+30', r['message'])
        self.assertEqual(j.get(tid)['status'], 'completed')
        roundtrip(j)

    def test_ledger_must_balance_in_save(self):
        j = self.j
        s = copy.deepcopy(j.state)
        s['careers'][CAR]['ext']['data']['ledger'] = {'111': 100, '511': -90}
        with self.assertRaises(GameError):
            validate_state(s)
        s['careers'][CAR]['ext']['data']['ledger'] = {'999': 100, '511': -100}
        with self.assertRaises(GameError):
            validate_state(s)
        s['careers'][CAR]['ext']['data']['ledger'] = {'111': 100, '511': -100}
        validate_state(s)

    def test_month_close_closes_profit_and_loss_into_421(self):
        tid = self.use('journal')
        self.solve(tid)
        j = self.j
        d, s = slot_for('month_close')
        j.c['day'] = max(j.c['day'], d)
        t = make_task(CAR, j.c['day'], s, 99)
        self.assertEqual(t['variant'], 'month_close')
        j.c['tasks'].append(t)
        j.c['active_task'] = t['id']
        validate_state(j.state)
        j.c['ext']['data']['ledger'] = {'111': 500, '511': -800, '632': 300}
        r = self.solve(t['id'])
        led = j.c['ext']['data']['ledger']
        for a in CA.PL_ACCOUNTS:
            self.assertNotIn(a, led)
        self.assertEqual(sum(led.values()), 0)
        self.assertIn('421', led)
        self.assertEqual(j.c['ext']['data']['closes'], 1)
        self.assertIn('421', r['message'])
        roundtrip(j)

    def test_day_cycle_resets_day_counters(self):
        j = self.j
        self.solve()
        self.assertEqual(j.c['ext']['data']['day_done'], 1)
        r = j.act('end_day', carry_event=True)
        summary = r['summary']['career']
        self.assertEqual(summary['dossiers'], 1)
        self.assertEqual(summary['milestones'], ['Chứng từ & hóa đơn'])
        self.assertEqual(summary['desk']['stamped'], 3)
        self.assertEqual(j.c['ext']['data']['day_done'], 0)
        j.act('start_day')
        self.assertEqual(j.c['day'], 2)
        roundtrip(j)

    # ------------------------------------------------------------ situations & employment
    def test_all_situations_playable(self):
        j = self.j
        self.assertTrue(10 <= len(CA.SPEC['situations']) <= 14)
        for x in CA.SPEC['situations']:
            self.assertLess(x['npc'], len(CA.PEOPLE))
            self.assertTrue(all(2 <= len(o['perspectives']) <= 3 for o in x['options'] if o.get('quality') == 'good'))
            for opt in x['options']:
                self.assertLessEqual(opt.get('cost', 0), 80)
                self.assertLessEqual(opt.get('reward', 0), 60)
                j.act('sit_practice', script=x['id'])
                for f in x['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(j.state)

    def test_player_is_not_addressed_by_gender(self):
        blob = json.dumps([CA.SPEC['situations'], CA.SPEC['meta']], ensure_ascii=False)
        for phrase in ('nha chị', 'Ok chị', 'mà chị,', 'Chị tuyệt vời', 'Chị từ chối', 'Chị dễ thương'):
            self.assertNotIn(phrase, blob)

    def test_situation_option_requires_facts(self):
        j = self.j
        x = next(s for s in CA.SPEC['situations'] if any(o.get('requires') for o in s['options']))
        opt = next(o for o in x['options'] if o.get('requires'))
        j.act('sit_practice', script=x['id'])
        with self.assertRaises(GameError):
            j.act('sit_choose', option=opt['id'])

    def test_start_day_blocked_until_hired_then_full_hiring_flow(self):
        state = new_state()
        state, _ = apply_action(state, CAR, 'select_career', {})
        with self.assertRaises(GameError) as cm:
            apply_action(state, CAR, 'start_day', {})
        self.assertEqual(cm.exception.code, 'not_hired')
        post = CA.SPEC['employment']['postings'][0]

        def act(name, **p):
            nonlocal state
            state, r = apply_action(state, CAR, name, p)
            return r
        act('job_apply', posting=post['id'])
        act('job_cv', strengths=post['wants'][:3], claims=['fresh'])
        act('job_letter', parts=dict(why='specific', example='story', close='available'))
        r = None
        for qid in post['questions']:
            q = employment.question(CAR, qid)
            best = max(q['options'], key=lambda o: o['score'])
            r = act('job_answer', question=qid, option=best['id'])
        if state['careers'][CAR]['job']['status'] != 'offer':
            self.skipTest('hiring flow changed: ' + state['careers'][CAR]['job']['status'])
        self.assertGreaterEqual(r['score'], 60)
        act('job_accept', confirm=True)
        job = state['careers'][CAR]['job']
        self.assertEqual(job['status'], 'hired')
        self.assertEqual(job['employer'], post['id'])
        act('start_day')
        self.assertTrue(state['careers'][CAR]['tasks'])
        validate_state(json.loads(json.dumps(state)))

    def test_employment_spec_shape(self):
        emp = CA.SPEC['employment']
        self.assertTrue(2 <= len(emp['postings']) <= 3)
        self.assertEqual(len({p['org'] for p in emp['postings']}), len(emp['postings']))
        for p in emp['postings']:
            self.assertLessEqual(p['salary'][1], 200)
            for qid in p['questions']:
                self.assertTrue(employment.question(CAR, qid))
        for q in emp['questions'].values():
            self.assertEqual(max(o['score'] for o in q['options']), 3)

    def test_staff_assist_opens_documents(self):
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        t = j.get(tid)
        msg = CA.assist(j.state, j.c, dict(role='ca_filing'), t)
        self.assertTrue(msg)
        self.assertEqual(len(t['inspected']), 1)
        validate_state(j.state)

    def test_first_dossier_coached_then_never_again(self):
        """Only the player's first dossier carries its answers in the view (the screen lights them); the task view never does."""
        j = self.j
        tid = j.task['id']
        view = lambda: public_state(j.state)['careers'][CAR]
        self.assertEqual(view()['data']['coach'], {})
        j.act('ask', task=tid)
        t = j.get(tid)
        self.assertEqual(view()['data']['coach'][tid]['cases'], {x['id']: dict(v=x['_truth']['v'], z=x['_truth']['z']) for x in t['cases']})
        self.assertNotIn('_truth', json.dumps(view()['tasks'], ensure_ascii=False))
        first = t['cases'][0]
        self.stamp_right(tid, first)
        self.assertNotIn(first['id'], view()['data']['coach'][tid]['cases'])
        for case in t['cases'][1:]:
            self.stamp_right(tid, case)
        j.act('ca_submit', task=tid, confirm=True)
        nxt = next(x for x in j.c['tasks'] if x['status'] not in ('completed', 'cancelled'))
        j.act('ask', task=nxt['id'])
        self.assertEqual(view()['data']['coach'], {})
        roundtrip(j)

    def test_first_step_dossier_coach_is_the_current_key(self):
        tid = self.use('journal')
        j = self.j
        j.act('ask', task=tid)
        st = j.get(tid)['proc'][0]
        self.assertEqual(public_state(j.state)['careers'][CAR]['data']['coach'][tid], dict(step=st['id'], key=st['_key']))


class ConsequenceTests(unittest.TestCase):
    """A tray handed in with wrong stamps costs the bonus, stars and chị Hạnh's trust."""

    def tray(self, plan):
        j = Journey(CAR)
        tid = j.task['id']
        j.act('ask', task=tid)
        money = j.c['money']
        for i, case in enumerate(j.get(tid)['cases']):
            tr = case['_truth']
            v = plan(i, case)
            if v != 'approve':
                j.act('ca_circle', task=tid, case=case['id'], zone=tr['z'][0] if tr['z'] else case['zones'][0])
            j.act('ca_stamp', task=tid, case=case['id'], verdict=v)
        r = j.act('ca_submit', task=tid, confirm=True)
        return j, j.get(tid), money, r

    @staticmethod
    def review(j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def test_approving_a_bad_voucher_costs_bonus_stars_and_trust(self):
        first = next(i for i, x in enumerate(Journey(CAR).task['cases']) if x['_truth']['v'] != 'approve')
        j, t, money, r = self.tray(lambda i, c: 'approve' if i == first else c['_truth']['v'])
        case = t['cases'][first]
        self.assertEqual(len(t['slips']), 1)
        self.assertEqual(t['slips'][0]['sev'], 3 if case['_truth']['fine'] >= 25 else 2)
        post = self.review(j, t['id'])
        self.assertLessEqual(post['stars'], 3)
        self.assertIn(case['_truth']['oops'][:40], post['text'])
        self.assertIn(t['reaction']['kind'], ('discount', 'refund', 'walkout'))
        cut = t['reaction']['cut']
        self.assertGreater(cut, 0)
        bonus = [e['amount'] for e in j.c['ops']['finance']['ledger'] if e['ref'] == t['id'] and e['category'] != 'penalty']
        self.assertEqual(bonus, [30 - cut])  # one cut, taken once; the fine at the stamp stays separate
        fine = min(case['_truth']['fine'], money)
        self.assertEqual(j.c['money'], money - fine + 30 - cut)
        self.assertIn('Chị Hạnh', r['message'])
        self.assertFalse(r['celebrate'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_serious_slip_reaches_the_boss(self):
        j = Journey(CAR)
        bad = [i for i, x in enumerate(j.task['cases']) if x['_truth']['v'] != 'approve']
        j, t, _, r = self.tray(lambda i, c: 'approve' if i in bad else c['_truth']['v'])
        self.assertGreaterEqual(sum(x['sev'] for x in t['slips']), 3)
        self.assertTrue(any(p.get('report') and p['source'] == t['id'] for p in j.c['feed']))
        o = j.c['ext']['data']['office']
        self.assertTrue(any('phản ánh' in n['text'] for n in o['notes']))
        self.assertIn('uy tín với sếp giảm', r['message'])

    def test_rejecting_a_valid_voucher_is_a_small_slip(self):
        j = Journey(CAR)
        good = next((i for i, x in enumerate(j.task['cases']) if x['_truth']['v'] == 'approve'), None)
        first = next(i for i, x in enumerate(j.task['cases']) if x['_truth']['v'] != 'approve')
        if good is None:
            self.skipTest('no valid voucher in this tray')
        j1, t1, _, _ = self.tray(lambda i, c: 'reject' if i == good else c['_truth']['v'])
        j2, t2, _, _ = self.tray(lambda i, c: 'approve' if i == first else c['_truth']['v'])
        self.assertEqual([x['sev'] for x in t1['slips']], [1])
        self.assertEqual(self.review(j1, t1['id'])['stars'], 4)
        self.assertGreater(self.review(j1, t1['id'])['stars'], self.review(j2, t2['id'])['stars'])

    def test_clean_tray_has_no_slips_and_full_bonus(self):
        j, t, money, r = self.tray(lambda i, c: c['_truth']['v'])
        self.assertFalse(t.get('slips'))
        self.assertEqual(t['reaction']['kind'], 'accept')
        self.assertEqual(j.c['money'], money + 30)
        self.assertEqual(self.review(j, t['id'])['stars'], 5)

    def test_wrong_step_answers_are_blocked_and_counted_not_slips(self):
        day, slot = slot_for('journal')
        j = Journey(CAR, slot=slot, day=day)
        tid = j.task['id']
        j.act('ask', task=tid)
        for d in j.task['docs']:
            j.act('ca_open', task=tid, doc=d['id'])
        st = j.get(tid)['proc'][0]
        key = answer(st)
        wrong = [dict(debit=key[0]['credit'], credit=key[0]['debit'], amount=key[0]['amount'])] if st['kind'] == 'entry' else None
        if wrong is None:
            self.skipTest('first step is not an entry')
        r = j.act('ca_step', task=tid, step=st['id'], answer=wrong)
        self.assertFalse(r['correct'])
        self.assertEqual(j.get(tid)['proc_state']['at'], 0)  # blocked: the wrong answer never goes into the dossier
        self.assertEqual(j.get(tid)['mistakes'], 1)
        for s in copy.deepcopy(j.get(tid)['proc']):
            j.act('ca_step', task=tid, step=s['id'], answer=answer(s))
        r = j.act('ca_submit', task=tid, note='specific', confirm=True)
        t = j.get(tid)
        self.assertFalse(t.get('slips'))
        self.assertIn('+20', r['message'])



# ---------------------------------------------------------------- office care: energy, colleagues, mentor track, close plan
def solve_task(j, tid):
    """Hand in any corp dossier correctly (hidden truth)."""
    j.act('ask', task=tid)
    for d in j.get(tid)['docs']:
        j.act('ca_open', task=tid, doc=d['id'])
    t = j.get(tid)
    if t['variant'] == 'desk':
        for case in t['cases']:
            tr = case['_truth']
            if tr['v'] != 'approve':
                j.act('ca_circle', task=tid, case=case['id'], zone=tr['z'][0])
            j.act('ca_stamp', task=tid, case=case['id'], verdict=tr['v'])
        return j.act('ca_submit', task=tid, confirm=True)
    for st in t['proc']:
        j.act('ca_step', task=tid, step=st['id'], answer=answer(st))
    return j.act('ca_submit', task=tid, note='specific', confirm=True)


def next_day(j):
    r = j.act('end_day', carry_event=True)
    j.act('start_day')
    return r


class OfficeCareTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey(CAR)

    @property
    def d(self):
        return self.j.c['ext']['data']

    @property
    def care(self):
        return self.d['care']

    @property
    def o(self):
        return self.d['office']

    def view(self):
        return public_state(self.j.state)['careers'][CAR]['data']['care']

    def open_tasks(self):
        return [t for t in self.j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]

    def ask(self, mate='na', i=0):
        self.care['ask'] = dict(day=self.j.c['day'], mate=mate, i=i, state='open')
        validate_state(self.j.state)

    # ------------------------------------------------------------ the shape of it
    def test_fresh_care_view(self):
        v = self.view()
        self.assertEqual(v['energy']['value'], CA.ENERGY_START)
        self.assertEqual([m['id'] for m in v['mates']], ['na', 'lua', 'bao'])
        self.assertTrue(all(m['npc'] and m['bond'] == 0 and m['owes'] == 0 for m in v['mates']))
        self.assertEqual(v['track']['rank'], 0)
        self.assertEqual(v['track']['next']['left'], CA.RANK_NEEDS[1][0])
        cal = v['calendar']
        self.assertEqual([c['rel'] for c in cal[:3]], ['Hôm nay', 'Mai', 'Ngày kia'])
        self.assertEqual(len(cal), 5)
        self.assertIn('Chốt chứng từ', [i['text'] for i in cal[1]['items']])          # docs is due on the 2nd day of the month
        self.assertEqual(cal[4]['mod']['name'], CA.MOD_INDEX['crunch']['name'])        # day 5: the close day
        plan = v['plan']
        self.assertEqual(plan['kind'], 'close')
        self.assertEqual([x['id'] for x in plan['items']], CA.CLOSE_IDS)
        self.assertTrue(all(x['state'] == 'todo' for x in plan['items']))
        self.assertNotIn('asks', json.dumps(v))                                        # only today's request goes out

    def test_old_save_gets_care_and_counts_this_months_work(self):
        self.d.pop('care')
        self.d['milestones'] = ['docs', 'debts']
        validate_state(self.j.state)
        self.assertEqual(self.care['energy'], CA.ENERGY_START)
        self.assertEqual(self.care['close']['done'], {'docs': 1})
        roundtrip(self.j)

    # ------------------------------------------------------------ colleagues
    def test_asks_are_seeded_and_vary(self):
        rolls = [CA.care_roll_ask(CA.CARE, d) for d in range(1, 60)]
        self.assertIsNone(rolls[0])
        self.assertEqual(rolls, [CA.care_roll_ask(CA.CARE, d) for d in range(1, 60)])
        asked = [r for r in rolls if r]
        self.assertTrue(30 <= len(asked) <= 55)
        self.assertEqual({r['mate'] for r in asked}, {'na', 'lua', 'bao'})
        for a, b in zip(rolls, rolls[1:]):
            if a and b:
                self.assertNotEqual(a['mate'], b['mate'])

    def test_help_costs_minutes_and_earns_a_favour(self):
        j = self.j
        self.ask('na', 0)
        text, minutes = CA.CARE['mates'][0]['asks'][0]
        self.assertEqual(self.view()['mates'][0]['ask'], dict(text=text, minutes=minutes))
        clock, turn = self.o['clock'], j.c['turn']
        with self.assertRaises(GameError):
            j.act('ca_help', mate='lua', answer='yes')                               # not the one asking
        r = j.act('ca_help', mate='na', answer='yes')
        self.assertIn('Na', r['message'])
        self.assertEqual(self.o['clock'], clock + minutes)
        self.assertEqual(j.c['turn'], turn)                                            # office clock, not the patience turn
        st = self.care['mates']['na']
        self.assertEqual((st['bond'], st['owes'], st['helped']), (1, 1, 1))
        self.assertEqual(j.c['relationships'][kit.npc_id(CAR, 7)], 4)
        with self.assertRaises(GameError):
            j.act('ca_help', mate='na', answer='yes')                                  # answered already
        self.assertIsNone(self.view()['mates'][0]['ask'])
        roundtrip(j)

    def test_declining_is_free(self):
        self.ask('bao', 1)
        clock = self.o['clock']
        r = self.j.act('ca_help', mate='bao', answer='no')
        self.assertIn('Bảo', r['message'])
        self.assertEqual(self.o['clock'], clock)
        self.assertEqual(self.care['mates']['bao'], dict(bond=0, owes=0, helped=0))
        self.assertEqual(self.o['trust'], office.TRUST_START)
        with self.assertRaises(GameError):
            self.j.act('ca_help', mate='bao', answer='maybe')

    def test_a_favour_pushes_one_deadline_once(self):
        j = self.j
        t = self.open_tasks()[0]
        with self.assertRaises(GameError):
            j.act('ca_cover', mate='na', task=t['id'])                                 # nobody owes you yet
        self.ask('na', 1)
        j.act('ca_help', mate='na', answer='yes')
        self.assertIn(t['id'], self.view()['coverable'])
        due = t['due']
        r = j.act('ca_cover', mate='na', task=t['id'])
        self.assertIn('lùi', ''.join(n['text'] for n in self.o['notes']))
        self.assertIn(office.hhmm(due + CA.COVER_MIN), r['message'])
        self.assertEqual(j.get(t['id'])['due'], due + CA.COVER_MIN)
        self.assertEqual(j.get(t['id'])['cover'], 'na')
        self.assertEqual(self.care['mates']['na']['owes'], 0)
        self.assertNotIn(t['id'], self.view()['coverable'])
        self.care['mates']['na']['owes'] = 1
        with self.assertRaises(GameError):
            j.act('ca_cover', mate='na', task=t['id'])                                 # once per dossier
        roundtrip(j)

    def test_no_favour_for_a_late_dossier(self):
        j = self.j
        t = self.open_tasks()[0]
        self.care['mates']['lua'].update(bond=1, owes=1)
        self.o['clock'] = t['due'] + 1
        with self.assertRaises(GameError) as cm:
            j.act('ca_cover', mate='lua', task=t['id'])
        self.assertIn('trễ', str(cm.exception))
        self.assertEqual(self.care['mates']['lua']['owes'], 1)

    def test_a_close_colleague_can_owe_two(self):
        self.care['mates']['lua'].update(bond=3, owes=1, helped=3)
        self.ask('lua', 0)
        self.j.act('ca_help', mate='lua', answer='yes')
        st = self.care['mates']['lua']
        self.assertEqual((st['bond'], st['owes']), (4, 2))
        roundtrip(self.j)

    # ------------------------------------------------------------ energy
    def test_one_long_night_is_fine_two_cost_a_slow_day(self):
        j = self.j
        self.o['clock'] = office.CLOSE
        j.act('ca_overtime', confirm=True)
        r = next_day(j)
        self.assertEqual(r['summary']['career']['care']['energy'], CA.ENERGY_START - CA.ENERGY_OT)
        self.o['clock'] = office.CLOSE
        j.act('ca_overtime', confirm=True)
        r = next_day(j)
        low = CA.ENERGY_START - 2 * CA.ENERGY_OT
        self.assertEqual(self.care['energy'], low)
        self.assertEqual(r['summary']['career']['care']['energy_label'], 'Kiệt sức')
        self.assertTrue(self.view()['energy']['low'])
        # exhausted: a fifth slower on the clock, and no overtime tonight
        t = self.open_tasks()[0]
        j.act('ask', task=t['id'])
        clock = self.o['clock']
        doc = j.get(t['id'])['docs'][0]
        cost = office.COST['ref' if t['variant'] == 'desk' else 'open'] * (2 if CA._mod(j.c['day'])['id'] == 'lag' else 1)
        r = j.act('ca_open', task=t['id'], doc=doc['id'])
        self.assertEqual(self.o['clock'], clock + cost + cost // CA.SLOW_DIV)
        self.o['clock'] = office.CLOSE
        with self.assertRaises(GameError) as cm:
            j.act('ca_overtime', confirm=True)
        self.assertIn('Sức bền', str(cm.exception))
        # one normal day brings you back above the line
        next_day(j)
        self.assertEqual(self.care['energy'], low + CA.ENERGY_REST)
        self.assertGreaterEqual(self.care['energy'], CA.ENERGY_LOW)
        self.assertFalse(self.view()['energy']['low'])
        roundtrip(j)

    def test_coffee_break_once_a_day(self):
        j = self.j
        self.care['energy'] = 50
        clock = self.o['clock']
        j.act('ca_break')
        self.assertEqual(self.care['energy'], 50 + CA.BREAK_GAIN)
        self.assertEqual(self.o['clock'], clock + CA.BREAK_MIN)
        self.assertFalse(self.view()['energy']['can_break'])
        with self.assertRaises(GameError):
            j.act('ca_break')
        next_day(j)
        self.care['energy'] = 100
        with self.assertRaises(GameError):
            j.act('ca_break')                                                          # already full
        roundtrip(j)

    # ------------------------------------------------------------ reliable days and the mentor track
    def test_reliable_day_and_rank_up(self):
        j = self.j
        self.care.update(reliable=2, streak=2)
        solve_task(j, self.open_tasks()[0]['id'])
        r = j.act('end_day', carry_event=True)
        care = r['summary']['career']['care']
        self.assertTrue(care['reliable'], care)
        self.assertEqual(care['rank_up'], CA.CARE['ranks'][1])
        self.assertEqual(self.care['rank'], 1)
        self.assertTrue(any('Lộ trình' in e['text'] for e in j.c['journal']))
        self.assertTrue(any(n['kind'] == 'care' for n in self.o['notes']))
        self.assertEqual(self.care['days'][-1]['day'], 1)
        roundtrip(j)

    def test_an_empty_or_late_day_is_not_reliable(self):
        j = self.j
        r = j.act('end_day', carry_event=True)
        self.assertFalse(r['summary']['career']['care']['reliable'])
        self.assertEqual(self.care['streak'], 0)
        j.act('start_day')
        t = self.open_tasks()[0]
        j.get(t['id'])['due'] = office.OPEN + 1
        solve_task(j, t['id'])
        r = j.act('end_day', carry_event=True)
        self.assertIn('trễ', r['summary']['career']['care']['why'])
        self.assertEqual(self.care['reliable'], 0)

    def test_rank_two_needs_trust_and_pays_on_reliable_days(self):
        j = self.j
        self.care.update(reliable=5, streak=0, rank=1)
        self.o['trust'] = 40
        solve_task(j, self.open_tasks()[0]['id'])
        self.o['trust'] = 40
        r = j.act('end_day', carry_event=True)
        self.assertIsNone(r['summary']['career']['care']['rank_up'])                   # trust too low
        self.assertEqual(self.care['rank'], 1)
        j.act('start_day')
        self.o['trust'] = 80
        solve_task(j, self.open_tasks()[0]['id'])
        money = j.c['money']
        r = j.act('end_day', carry_event=True)
        self.assertEqual(r['summary']['career']['care']['rank_up'], CA.CARE['ranks'][2])
        self.assertEqual(r['summary']['career']['care']['pay'], CA.RANK_PAY[2])
        self.assertTrue(any(e['category'] == 'office_bonus' and e['amount'] == CA.RANK_PAY[2] for e in j.c['ops']['finance']['ledger']))
        self.assertGreaterEqual(j.c['money'], money + CA.RANK_PAY[2])

    # ------------------------------------------------------------ the month-end close plan
    def test_close_plan_ticks_from_this_months_dossiers(self):
        day, slot = slot_for('bank_rec')
        j = self.j = Journey(CAR, slot=slot, day=day)
        r = solve_task(j, j.task['id'])
        self.assertIn('Kế hoạch khóa sổ', r['message'])
        self.assertEqual(self.care['close']['done'], {'bank': day})
        item = next(x for x in self.view()['plan']['items'] if x['id'] == 'bank')
        self.assertEqual(item['state'], 'done')
        roundtrip(j)

    def test_last_months_dossier_does_not_tick_this_month(self):
        day, slot = slot_for('bank_rec')
        j = self.j = Journey(CAR, slot=slot, day=day)
        j.c['day'] = day + 5
        self.o['day'] = 0
        solve_task(j, j.task['id'])
        self.assertNotIn('bank', self.care['close']['done'])

    def test_a_missed_mark_costs_trust_and_a_full_month_pays(self):
        j = self.j
        r = next_day(j)                                                                 # day 1: nothing due
        self.assertNotIn('close', r['summary']['career'])
        trust = self.o['trust']
        self.care['close']['done'] = {}
        r = j.act('end_day', carry_event=True)                                          # day 2: docs is due
        self.assertEqual(r['summary']['career']['close']['missed'], [CA.CLOSE_PLAN[0][2]])
        self.assertTrue(any(n['kind'] == 'late' and 'khóa sổ' in n['text'] for n in self.o['notes']))
        self.assertEqual(self.care['close']['missed'], ['docs'])
        self.assertLessEqual(r['summary']['career']['office']['trust'], trust - CA.CLOSE_MISS)
        # month end with every mark done on time
        j.act('start_day')
        j.c['day'] = 5
        self.o['day'] = 0
        self.care['close'] = dict(month=0, done={'docs': 2, 'cash': 3, 'bank': 4, 'fixed': 4, 'close': 5}, missed=[])
        validate_state(j.state)
        money = j.c['money']
        r = j.act('end_day', carry_event=True)
        close = r['summary']['career']['close']
        self.assertEqual((close['on_time'], close['bonus']), (5, CA.CLOSE_BONUS))
        self.assertTrue(any(e['reason'] == 'Thưởng khóa sổ đúng hạn' for e in j.c['ops']['finance']['ledger']))
        self.assertGreaterEqual(j.c['money'], money + CA.CLOSE_BONUS)
        j.act('start_day')
        self.assertEqual(self.care['close'], dict(month=1, done={}, missed=[]))       # a new month starts empty
        roundtrip(j)

    # ------------------------------------------------------------ validation
    def test_tampered_care_is_rejected(self):
        bad = [lambda cr: cr.update(energy=150), lambda cr: cr['mates']['na'].update(bond=9),
               lambda cr: cr['mates']['na'].update(owes=2), lambda cr: cr.update(ask=dict(day=1, mate='boss', i=0, state='open')),
               lambda cr: cr.update(ask=dict(day=1, mate='na', i=9, state='open')), lambda cr: cr.update(rank=3),
               lambda cr: cr.update(streak=4), lambda cr: cr['mates'].update(boss=dict(bond=0, owes=0, helped=0)), lambda cr: cr['close']['done'].update(tea=1),
               lambda cr: cr['close']['done'].update(docs=99), lambda cr: cr.update(days=[dict(day=1, ok='yes', why='x')])]
        for i, f in enumerate(bad):
            with self.subTest(i=i):
                j = Journey(CAR)
                f(j.c['ext']['data']['care'])
                with self.assertRaises(GameError):
                    validate_state(json.loads(json.dumps(j.state)))
        j = Journey(CAR)
        next(t for t in j.c['tasks'])['cover'] = 'stranger'
        with self.assertRaises(GameError):
            validate_state(json.loads(json.dumps(j.state)))

    def test_several_days_play_through(self):
        j = self.j
        for day in range(1, 7):
            if day > 1:
                j.act('start_day')
            a = CA.care_ask_today(self.care, j.c['day'])
            if a:
                j.act('ca_help', mate=a['mate'], answer='yes')
            for t in self.open_tasks():
                solve_task(j, t['id'])
            roundtrip(j)
            j.act('end_day', carry_event=True)
        self.assertGreaterEqual(self.care['reliable'], 3)
        self.assertGreaterEqual(self.care['rank'], 1)
        self.assertEqual(len(self.care['days']), 6)
        roundtrip(j)


if __name__ == '__main__':
    unittest.main()
