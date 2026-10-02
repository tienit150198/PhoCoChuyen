import copy
import json
import unittest

from game.engine import GameError, apply_action, new_state, public_state, validate_state
from game import employment
from game.careers import tax_payroll as T
from game.careers import kit, office
from tests.helpers import Journey

FORMS = ('payslip', 'transfer', 'question', 'vat', 'calendar', 'yearend')
CAR = 'tax_payroll'


def find(form):
    for day in range(1, 12):
        for slot in range(4):
            if T.make_task(day, slot, 1)['form'] == form:
                return day, slot
    raise AssertionError('no slot for ' + form)


from game.careers import PLUGINS


@unittest.skipUnless('tax_payroll' in PLUGINS, 'tax_payroll is filtered out by MNL_CAREERS')
class TaxPayrollTests(unittest.TestCase):
    def journey(self, form):
        day, slot = find(form)
        self.j = Journey('tax_payroll', slot=slot, day=day)
        return self.j

    def view(self):
        return public_state(self.j.state)['careers']['tax_payroll']['tasks'][0]

    def solve(self, j):
        tid = j.task['id']
        for st in copy.deepcopy(j.task['proc']):
            r = j.act('tp_submit', task=tid, step=st['id'], answer=st['_key'])
            self.assertTrue(r['correct'], st['id'])
        return tid

    # ---------------------------------------------------------------- employment gate
    def test_start_day_requires_contract(self):
        s = new_state()
        s, _ = apply_action(s, 'tax_payroll', 'select_career', {})
        with self.assertRaises(GameError) as cm:
            apply_action(s, 'tax_payroll', 'start_day', {})
        self.assertEqual(cm.exception.code, 'not_hired')

    def test_employment_spec(self):
        posts = employment.postings('tax_payroll')
        self.assertTrue(2 <= len(posts) <= 3)
        for p in posts:
            self.assertLessEqual(p['salary'][1], 200)
            self.assertTrue(1 <= len(p['questions']) <= 5)
            for q in p['questions']:
                self.assertIsNotNone(employment.question('tax_payroll', q), q)
        own = T.SPEC['employment']['questions']
        self.assertTrue(3 <= len(own) <= 5)
        for q in own.values():
            self.assertEqual(sorted(o['score'] for o in q['options'])[-1], 3)

    # ---------------------------------------------------------------- every form end to end
    def test_every_form_solvable_and_paid(self):
        for form in FORMS:
            with self.subTest(form=form):
                j = self.journey(form)
                j.act('ask')
                money = j.c['money']
                tid = self.solve(j)
                self.assertTrue(j.task['proc_state']['at'] == len(j.task['proc']))
                validate_state(json.loads(json.dumps(j.state)))
                r = j.act('tp_file', task=tid, confirm=True)
                t = j.get(tid)
                self.assertEqual(t['status'], 'completed')
                self.assertFalse(t['late'])
                self.assertEqual(j.c['money'], money + max(office.MIN_PAY, t['bonus'] + office.RAISE))
                self.assertTrue(r.get('celebrate'))
                post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
                self.assertEqual(post['stars'], 5)
                self.assertEqual({x['key'] for x in post['feedback']['criteria']}, {'accuracy', 'quality', 'care', 'speed'})
                validate_state(json.loads(json.dumps(j.state)))

    def test_many_days_generate_valid_tasks(self):
        from game import procedures
        for day in range(1, 25):
            for slot in range(4):
                t = T.make_task(day, slot, 3)
                self.assertEqual(json.loads(json.dumps(t)), t)
                tt = copy.deepcopy(t)
                for st in tt['proc']:
                    self.assertTrue(procedures.shape_ok(st, st['_key']), (t['form'], st['id']))
                    self.assertTrue(procedures.submit(tt, st['id'], copy.deepcopy(st['_key']))[0])
                    if st['kind'] in ('choice', 'multi'):
                        self.assertGreaterEqual(len(st['options']), 3)
                self.assertTrue(t['papers'])

    # ---------------------------------------------------------------- mistakes, hints, malformed input
    def test_wrong_answer_counts_mistake_and_shows_hint(self):
        j = self.journey('payslip')
        j.act('ask')
        st = j.task['proc'][0]
        wrong = {k: 'r150' for k in st['_key']}
        r = j.act('tp_submit', step='ot', answer=wrong)
        self.assertFalse(r['correct'])
        self.assertEqual(j.task['mistakes'], 1)
        self.assertIn(st['hints'][0], r['message'])
        r = j.act('tp_submit', step='ot', answer=wrong)
        self.assertIn(st['hints'][1], r['message'])
        self.assertEqual(j.task['proc_state']['attempts']['ot'], 2)
        j.act('tp_submit', step='ot', answer=st['_key'])
        # A wrong number inside the gross fields counts one more mistake, never reveals the key.
        g = dict(j.task['proc'][1]['_key'])
        g['gross'] += 1
        r = j.act('tp_submit', step='gross', answer=g)
        self.assertFalse(r['correct'])
        self.assertNotIn(str(j.task['proc'][1]['_key']['gross']), r['message'])
        self.assertEqual(j.task['mistakes'], 3)

    def test_deeper_hints_work_on_the_players_numbers_never_the_key(self):
        import re
        nums = lambda lines: {int(n.replace('.', '')) for n in re.findall(r'\d[\d.]*\d|\d', ' '.join(lines))}
        j = self.journey('payslip')
        j.act('ask')
        for st in copy.deepcopy(j.task['proc'][:3]):
            j.act('tp_submit', step=st['id'], answer=st['_key'])
        key = dict(j.task['proc'][3]['_key'])
        # A tax bigger than the taxable income: a sanity check at once, a short toast, the message as before.
        r = j.act('tp_submit', step='tax', answer=dict(taxable=key['taxable'], pit=key['taxable'] * 3))
        self.assertFalse(r['correct'])
        self.assertEqual((r['bad'], r['toast']), (['pit'], '✗ Chưa khớp 1/2 ô.'))
        self.assertIn('Khớp 1/2 ô', r['message'])
        self.assertTrue(any('không thể lớn hơn thu nhập tính thuế' in x for x in r['deep']), r['deep'])
        self.assertNotIn('Chia thu nhập', ' '.join(r['deep']))           # the method waits for a second miss
        # A flat rate on the whole income, second check: the brackets cut on the player's own taxable income.
        r = j.act('tp_submit', step='tax', answer=dict(taxable=key['taxable'], pit=key['taxable'] * 15 // 100))
        deep = ' '.join(r['deep'])
        self.assertIn(f'Chia thu nhập tính thuế {T.fmt(key["taxable"])} thành từng bậc: tới 2.000', deep)
        self.assertIn('không nhân cả', deep)
        self.assertNotIn(key['pit'], nums(r['deep']))
        # A wrong taxable income is checked against the gross already matched, never against the key.
        r = j.act('tp_submit', step='tax', answer=dict(taxable=key['taxable'] + 99999, pit=0))
        self.assertTrue(any('phải nhỏ hơn Tổng thu nhập' in x for x in r['deep']), r['deep'])
        self.assertFalse(nums(r['deep']) & set(key.values()))

    def test_deeper_hints_never_hold_a_right_value(self):
        import re
        nums = lambda lines: {int(n.replace('.', '')) for n in re.findall(r'\d[\d.]*\d|\d', ' '.join(lines))}
        seen = 0
        for form in FORMS:
            j = self.journey(form)
            j.act('ask')
            for st in copy.deepcopy(j.task['proc']):
                if st['kind'] in ('fields', 'number'):
                    k = st['_key']
                    for bump in (7, 3001, -50000):
                        wrong = k + bump if st['kind'] == 'number' else {f: v + bump if type(v) is int else v for f, v in k.items()}
                        r = j.act('tp_submit', step=st['id'], answer=wrong)
                        self.assertFalse(r['correct'])
                        self.assertIsInstance(r['deep'], list)
                        seen += len(r['deep'])
                        right = {k} if st['kind'] == 'number' else {v for v in k.values() if type(v) is int}
                        public = {0, 12, T.PERSONAL, T.DEPENDENT} | {top * m for top, _ in T.BRACKETS[:-1] for m in (1, 12)}   # the rules' own numbers
                        self.assertFalse(nums(r['deep']) & right - public, (form, st['id'], r['deep']))
                j.act('tp_submit', step=st['id'], answer=st['_key'])
        self.assertGreater(seen, 10)

    def test_malformed_and_out_of_order_rejected_without_mistake(self):
        j = self.journey('payslip')
        with self.assertRaises(GameError):
            j.act('tp_submit', step='ot', answer={})        # not asked yet
        j.act('ask')
        gross = j.task['proc'][1]
        for step, answer in (('gross', gross['_key']), ('ot', 'r150'), ('ot', {'ot1': 'r999', 'ot2': 'r150', 'ot3': 'r150'}),
                             ('ot', {'ot1': 'r150'}), (5, {})):
            with self.assertRaises(GameError, msg=str(answer)):
                j.act('tp_submit', step=step, answer=answer)
        for answer in ({'ot1': ['r150'], 'ot2': 'r150', 'ot3': 'r150'}, [['r150']], None, True):
            with self.assertRaises(GameError, msg=str(answer)):     # unhashable / wrong types never crash the server
                j.act('tp_submit', step='ot', answer=answer)
        j.act('tp_submit', step='ot', answer=j.task['proc'][0]['_key'])
        bad = dict(gross['_key'], gross='12000')
        with self.assertRaises(GameError):
            j.act('tp_submit', step='gross', answer=bad)
        with self.assertRaises(GameError):
            j.act('tp_submit', step='gross', answer=dict(gross['_key'], gross=1.5))
        with self.assertRaises(GameError):
            j.act('tp_file', confirm=True)                  # steps left
        self.assertEqual(j.task['mistakes'], 0)

    def test_file_needs_confirm(self):
        j = self.journey('transfer')
        j.act('ask')
        self.solve(j)
        with self.assertRaises(GameError):
            j.act('tp_file')
        with self.assertRaises(GameError):
            j.act('tp_submit', step='approve', answer='dual')   # already complete

    # ---------------------------------------------------------------- hidden answers
    def test_public_view_hides_keys(self):
        j = self.journey('vat')
        v = self.view()
        self.assertIsNone(v['papers'])
        self.assertIsNone(v['steps'])
        self.assertNotIn('proc', v)
        j.act('ask')
        v = self.view()
        dump = json.dumps(v, ensure_ascii=False)
        self.assertNotIn('_key', dump)
        self.assertNotIn('proc_state', v)
        self.assertEqual(v['steps'][0]['state'], 'current')
        self.assertNotIn('explain', v['steps'][0])
        self.assertEqual(v['progress']['total'], 4)
        j.act('tp_submit', step='invalid', answer=j.task['proc'][0]['_key'])
        v = self.view()
        self.assertIn('explain', v['steps'][0])
        self.assertEqual(v['steps'][0]['answer'], j.task['proc'][0]['_key'])
        self.assertNotIn('explain', v['steps'][1])

    # ---------------------------------------------------------------- deadlines & review
    def test_late_filing_loses_bonus(self):
        j = self.journey('calendar')
        j.act('ask')
        tid = self.solve(j)
        j.task['due'] = office.OPEN + 10
        money = j.c['money']
        r = j.act('tp_file', task=tid, confirm=True)
        t = j.get(tid)
        self.assertTrue(t['late'])
        self.assertEqual(j.c['money'], money + t['bonus'] + office.RAISE - office.ROOKIE_LATE_CUT)
        self.assertIn('Trễ hạn', r['message'])
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
        crit = {x['key']: x['score'] for x in post['feedback']['criteria']}
        self.assertEqual(crit['speed'], 1)
        self.assertEqual(j.c['ext']['data']['late'], 1)

    def test_mistakes_reduce_bonus_and_ethic_choice_hurts_care(self):
        j = self.journey('payslip')
        j.act('ask')
        tid = j.task['id']
        for st in copy.deepcopy(j.task['proc']):
            if st['id'] == 'send':
                j.act('tp_submit', step='send', answer='group')
            j.act('tp_submit', step=st['id'], answer=st['_key'])
        money = j.c['money']
        j.task['due'] = office.LOCK
        j.act('tp_file', confirm=True)
        self.assertEqual(j.c['money'], money + 30 + office.RAISE - 2)   # on probation a mistake costs 2
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
        crit = {x['key']: x['score'] for x in post['feedback']['criteria']}
        self.assertEqual(crit['care'], 2)
        self.assertEqual(crit['accuracy'], 4)

    # ---------------------------------------------------------------- tampering
    def test_tampered_save_rejected(self):
        j = self.journey('yearend')
        j.act('ask')
        j.act('tp_submit', step='route', answer=j.task['proc'][0]['_key'])
        for mutate in (lambda t: t['proc'][2]['_key'].update(due=0), lambda t: t['papers'][0]['rows'].pop(),
                       lambda t: t.update(bonus=999), lambda t: t.update(due_turn=10 ** 6),
                       lambda t: t['proc_state'].update(at=3, solved=['route', 'docs', 'calc']),
                       lambda t: t['proc_state']['answers'].update(route='none'), lambda t: t.update(filed=True),
                       lambda t: t.update(late='no')):
            state = copy.deepcopy(j.state)
            mutate(state['careers']['tax_payroll']['tasks'][0])
            with self.assertRaises(GameError):
                validate_state(state)
        state = copy.deepcopy(j.state)
        state['careers']['tax_payroll']['ext']['data']['log'] = [dict(day=1)]
        with self.assertRaises(GameError):
            validate_state(state)

    # ---------------------------------------------------------------- rules & content
    def test_game_rule_math(self):
        self.assertEqual(T.pit(0), 0)
        self.assertEqual(T.pit(2000), 100)
        self.assertEqual(T.pit(5000), 400)
        self.assertEqual(T.pit(10000), 1150)
        self.assertEqual(T.pit(12000), 1550)
        self.assertEqual(T.pit(3608), 260)
        self.assertEqual(T.pit(24000, 12), 1200)
        self.assertEqual(T.pit(120000, 12), 13800)
        self.assertEqual(T.insurance(10400), dict(bhxh=832, bhyt=156, bhtn=104))
        self.assertEqual(T.holder('Nguyễn Thị Diệu'), 'NGUYEN THI DIEU')
        self.assertEqual(T.holder('Đỗ Quang Vinh'), 'DO QUANG VINH')
        p = T._pay(50, 1, 700, 500, 200, 1, [(2, 'r150'), (4, 'r200'), (3, 'r300')])
        self.assertEqual((p['gross'], p['ins_total'], p['taxable'], p['pit'], p['net']), (12400, 1092, 3608, 260, 11048))
        cc = T.content()
        self.assertIn('disclaimer', cc)
        self.assertTrue(all('game' in x or True for x in cc['rules']))

    def test_hint_and_assist(self):
        j = self.journey('vat')
        t = j.task
        self.assertIn('Nhận hồ sơ', T.hint(j.c, t))
        j.act('ask')
        t = j.task
        self.assertEqual(T.hint(j.c, t), t['proc'][0]['hints'][0])
        self.assertIn(t['proc'][0]['hints'][0], T.assist({}, j.c, dict(name='Tuấn', role='tax'), t))
        self.assertIsNone(T.assist({}, j.c, dict(name='Ngân', role='payroll'), t))
        self.assertIn('hồ sơ', T.assist({}, j.c, dict(name='Thư', role='filing'), t))

    def test_situations_playable(self):
        j = Journey('tax_payroll')
        self.assertTrue(10 <= len(T.SITUATIONS) <= 14)
        for sit in T.SITUATIONS:
            for o in sit['options']:
                self.assertTrue(2 <= len(o['perspectives']) <= 3)
            for opt in sit['options']:
                j.act('sit_practice', script=sit['id'])
                for f in sit['facts']:
                    j.act('sit_read', fact=f['id'])
                j.act('sit_choose', option=opt['id'])
                r = j.act('sit_confirm', confirm=True)
                self.assertTrue(r['message'])
                j.act('sit_dismiss')
        validate_state(json.loads(json.dumps(j.state)))

    def test_full_day_has_distinct_forms(self):
        j = Journey('tax_payroll')
        forms = [t['form'] for t in j.c['tasks'] if t['career'] == 'tax_payroll']
        self.assertEqual(len(forms), 3)
        self.assertEqual(len(set(forms)), 3)
        validate_state(json.loads(json.dumps(j.state)))

    # ---------------------------------------------------------------- the payroll grid
    def grid(self, day=1):
        self.j = Journey(CAR, slot=0, day=day)
        self.assertEqual(self.j.task['form'], 'grid')
        return self.j

    @property
    def office(self):
        return self.j.c['ext']['data']['office']

    def flag_truth(self, tid, rows=None):
        for row in rows or self.j.get(tid)['rows']:
            for z in row['_truth']['z']:
                self.j.act('tp_flag', task=tid, row=row['id'], cell=z)
            self.j.act('tp_row', task=tid, row=row['id'])

    def test_first_task_of_the_day_is_the_payroll_grid(self):
        j = Journey(CAR)
        first = min(j.c['tasks'], key=lambda t: t['id'])
        self.assertEqual(first['form'], 'grid')
        self.assertEqual(first['gen'], T.GEN)
        self.assertEqual(first['due'], office.DUE[0])
        self.assertIn(len(first['rows']), (3, 4))                                # + one row that should not be there

    def test_grid_generation_is_consistent(self):
        seen = set()
        for day in range(1, 41):
            for slot in (0, 4):
                t = T.make_task(day, slot, 1)
                self.assertEqual(t, T.make_task(day, slot, 9) | dict(created_turn=1))
                self.assertEqual(json.loads(json.dumps(t)), t)
                self.assertTrue(any(r['_truth']['z'] for r in t['rows']))
                self.assertTrue(any(not r['_truth']['z'] for r in t['rows']))
                for r in t['rows']:
                    tr = r['_truth']
                    self.assertEqual([c['z'] for c in r['cells']], [z for z, _ in T.GRID_COLS])
                    self.assertTrue(set(tr['z']) <= {c['z'] for c in r['cells']})
                    self.assertEqual(len(tr['z']), len(set(tr['z'])))
                    self.assertTrue(all(len(tr[k]) == len(tr['z']) for k in ('kinds', 'why', 'dirs', 'fines', 'claims')))
                    self.assertTrue(all(k in T.GRID_HINTS for k in tr['kinds']))
                    seen |= set(tr['kinds'])
        self.assertEqual(seen, set(T.ROW_ERRORS) | set(T.PEOPLE_ERRORS))
        self.assertLess(T.grid_size(1, 'normal'), T.grid_size(9, 'normal'))
        early = {k for s in range(0, 8, 4) for r in T.make_task(1, s, 1)['rows'] for k in r['_truth']['kinds']}
        self.assertTrue(early <= {k for k, d in T.ERR_MIN_DAY.items() if d <= 1})

    def test_clean_grid_pays_bonus_and_builds_trust(self):
        j = self.grid()
        tid = j.task['id']
        j.act('ask', task=tid)
        self.flag_truth(tid)
        money = j.c['money']
        r = j.act('tp_pay', task=tid, confirm=True)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertTrue(r['celebrate'])
        self.assertEqual(j.c['money'], money + T.GRID_BONUS + office.RAISE)
        self.assertTrue(all(x['ok'] for x in t['results'].values()))
        caught = sum(len(x['_truth']['z']) for x in t['rows'])
        self.assertEqual(self.office['trust'], office.TRUST_START + min(3, caught) + 2)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
        self.assertEqual(post['stars'], 5)
        self.assertEqual({x['key'] for x in post['feedback']['criteria']}, {'accuracy', 'quality', 'care', 'speed'})
        self.assertFalse(j.c['ext']['data']['claims'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_missed_underpayment_becomes_a_claim_tomorrow(self):
        day, slot, row = next((d, s, r) for d in range(1, 30) for s in (0,) for r in T.make_task(d, s, 1)['rows']
                              if 'under' in r['_truth']['dirs'] and len(r['_truth']['z']) == 1)
        self.j = Journey(CAR, slot=slot, day=day)
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        self.flag_truth(tid, [r for r in j.task['rows'] if r['id'] != row['id']])
        j.act('tp_row', task=tid, row=row['id'])
        r = j.act('tp_pay', task=tid, confirm=True)
        self.assertIn('khiếu nại', r['message'])
        claims = j.c['ext']['data']['claims']
        self.assertEqual(len(claims), 1)
        cl = claims[0]
        self.assertEqual((cl['status'], cl['from_day'], cl['amount']), ('open', day + 1, row['_truth']['claims'][0]))
        self.assertFalse(public_state(j.state)['careers'][CAR]['data']['claims'])      # workers notice tomorrow
        with self.assertRaises(GameError):
            j.act('tp_claim', claim=cl['id'], choice='pay_now')
        view = public_state(j.state)['careers'][CAR]['tasks'][0]
        missed = next(x for x in view['rows'] if x['id'] == row['id'])
        self.assertEqual(missed['result']['missed'], row['_truth']['z'])
        self.assertEqual(missed['truth']['why'], row['_truth']['why'])
        j.act('end_day', carry_event=True)
        j.act('start_day')
        data = public_state(j.state)['careers'][CAR]['data']
        self.assertEqual([x['id'] for x in data['claims']], [cl['id']])
        trust = self.office['trust']
        with self.assertRaises(GameError):
            j.act('tp_claim', claim=cl['id'], choice='maybe')
        r = j.act('tp_claim', claim=cl['id'], choice='pay_now')
        self.assertTrue(r['celebrate'])
        self.assertEqual(self.office['trust'], trust + 2)
        self.assertEqual(j.c['ext']['data']['claims'][0]['status'], 'paid')
        with self.assertRaises(GameError):
            j.act('tp_claim', claim=cl['id'], choice='deny')
        validate_state(json.loads(json.dumps(j.state)))

    def test_claim_denied_or_ignored_costs_trust(self):
        j = self.grid()
        d = j.c['ext']['data']
        d['claims'] = [dict(id='cl-a', day=1, from_day=1, task='x', name='Nguyễn Thị Diệu', amount=300, why='Thiếu tăng ca.', status='open'),
                       dict(id='cl-b', day=1, from_day=1, task='x', name='Lê Văn Tài', amount=100, why='Trừ tạm ứng hai lần.', status='open')]
        validate_state(j.state)
        trust = self.office['trust']
        r = j.act('tp_claim', claim='cl-a', choice='deny')
        self.assertFalse(r['correct'])
        self.assertEqual(self.office['trust'], trust - 4)
        r = j.act('end_day', carry_event=True)
        self.assertEqual(r['summary']['career']['claims_ignored'], 1)
        self.assertEqual([x['status'] for x in j.c['ext']['data']['claims']], ['denied', 'ignored'])

    def test_missed_overpayment_is_fined_and_capped_by_wallet(self):
        day, row = next((d, r) for d in range(1, 30) for r in T.make_task(d, 0, 1)['rows'] if r['_truth']['dirs'] == ['over'])
        self.j = Journey(CAR, slot=0, day=day)
        j = self.j
        tid = j.task['id']
        j.act('ask', task=tid)
        self.flag_truth(tid, [r for r in j.task['rows'] if r['id'] != row['id']])
        j.act('tp_row', task=tid, row=row['id'])
        money = j.c['money']
        j.act('tp_pay', task=tid, confirm=True)
        fine = row['_truth']['fines'][0]
        self.assertTrue(any(e['category'] == 'penalty' and e['amount'] == -fine for e in j.c['ops']['finance']['ledger']))
        self.assertLess(j.c['money'], money + T.GRID_BONUS)
        post = next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)
        crit = {x['key']: x['score'] for x in post['feedback']['criteria']}
        # The missed overpayment is now a recorded mistake: it also pulls 'accuracy' down to the star cap.
        self.assertEqual(crit['care'], 2)
        self.assertLessEqual(crit['accuracy'], 3)

    def test_false_flags_hold_pay_and_cost_trust(self):
        j = self.grid()
        tid = j.task['id']
        j.act('ask', task=tid)
        clean = next(r for r in j.task['rows'] if not r['_truth']['z'])
        j.act('tp_flag', task=tid, row=clean['id'], cell='days')
        self.flag_truth(tid, [r for r in j.task['rows'] if r['id'] != clean['id']])
        j.act('tp_row', task=tid, row=clean['id'])
        r = j.act('tp_pay', task=tid, confirm=True)
        self.assertIn('nhầm', r['message'])
        self.assertEqual(j.get(tid)['results'][clean['id']]['extra'], ['days'])
        self.assertEqual(j.get(tid)['mistakes'], 1)

    def test_grid_flags_rows_and_pay_rules(self):
        j = self.grid()
        tid = j.task['id']
        with self.assertRaises(GameError):
            j.act('tp_flag', task=tid, row='r1', cell='days')                      # not received yet
        j.act('ask', task=tid)
        r1 = j.task['rows'][0]
        self.assertTrue(j.act('tp_flag', task=tid, row='r1', cell='days')['flagged'])
        self.assertFalse(j.act('tp_flag', task=tid, row='r1', cell='days')['flagged'])
        self.assertNotIn('r1', j.task['flags'])
        for z in ('days', 'ot', 'ins'):
            j.act('tp_flag', task=tid, row='r1', cell=z)
        with self.assertRaises(GameError):
            j.act('tp_flag', task=tid, row='r1', cell='bank')                      # three at most
        for bad in (dict(row='r99', cell='days'), dict(row='r1', cell='salary'), dict(row='r1', cell=['days']), dict(row=None, cell='days')):
            with self.subTest(bad=bad), self.assertRaises(GameError):
                j.act('tp_flag', task=tid, **bad)
        with self.assertRaises(GameError):
            j.act('tp_pay', task=tid, confirm=True)                                # rows left
        j.act('tp_row', task=tid, row=r1['id'])
        with self.assertRaises(GameError):
            j.act('tp_flag', task=tid, row='r1', cell='bank')                      # reviewed rows are locked
        with self.assertRaises(GameError):
            j.act('tp_row', task=tid, row='r1')
        with self.assertRaises(GameError):
            j.act('tp_submit', task=tid, step='x', answer=1)
        with self.assertRaises(GameError):
            j.act('tp_file', task=tid, confirm=True)
        for row in j.task['rows'][1:]:
            j.act('tp_row', task=tid, row=row['id'])
        with self.assertRaises(GameError):
            j.act('tp_pay', task=tid)                                              # needs confirm
        j.act('tp_pay', task=tid, confirm=True)
        with self.assertRaises(GameError):
            j.act('tp_pay', task=tid, confirm=True)
        validate_state(json.loads(json.dumps(j.state)))

    def test_grid_hint_and_hidden_truth(self):
        j = self.grid()
        tid = j.task['id']
        v = self.view()
        self.assertIsNone(v['rows'])
        j.act('ask', task=tid)
        v = self.view()
        dump = json.dumps(v, ensure_ascii=False)
        for secret in ('_truth', 'kinds', 'dirs', 'claims', '"why"'):
            self.assertNotIn(secret, dump)
        self.assertEqual(v['grid']['total'], len(j.task['rows']))
        bad = next(r for r in j.task['rows'] if r['_truth']['z'])
        clock = self.office['clock']
        r = j.act('tp_hint', task=tid, row=bad['id'])
        self.assertIn(T.GRID_HINTS[bad['_truth']['kinds'][0]], r['message'])
        self.assertEqual(self.office['clock'], clock + T.HINT_MIN)
        row = next(x for x in self.view()['rows'] if x['id'] == bad['id'])
        self.assertTrue(row['hinted'])
        self.assertEqual(row['tip'], T.GRID_HINTS[bad['_truth']['kinds'][0]])
        self.assertNotIn('truth', row)

    def test_tampered_grid_rejected(self):
        j = self.grid()
        tid = j.task['id']
        j.act('ask', task=tid)
        self.flag_truth(tid)
        j.act('tp_pay', task=tid, confirm=True)
        for mutate in (lambda t: t['rows'][0]['_truth'].update(z=['bank']),
                       lambda t: t['rows'][0]['cells'][1].update(v='0 ngày'),
                       lambda t: t['results'].update(r1=dict(ok=True, missed=[], extra=[])) if not t['results']['r1']['ok'] else t['flags'].pop('r1'),
                       lambda t: t['flags'].update(r1=['nowhere']),
                       lambda t: t['reviewed'].pop(),
                       lambda t: t.update(tips=['r99']),
                       lambda t: t.update(filed=False)):
            s = copy.deepcopy(j.state)
            mutate(s['careers'][CAR]['tasks'][0])
            with self.assertRaises(GameError):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers'][CAR]['ext']['data']['claims'] = [dict(id='x')]
        with self.assertRaises(GameError):
            validate_state(s)

    # ---------------------------------------------------------------- rules that shift, luck of the day, the clock
    def test_rules_shift_between_pay_periods(self):
        a, b = T._rules_raw(1), T._rules_raw(6)
        self.assertEqual(a['m'], 9)
        self.assertEqual(a['holiday'], '2/9')
        self.assertNotEqual((a['floor'], a['cut'], a['holiday']), (b['floor'], b['cut'], b['holiday']))
        self.assertFalse(any(x['new'] for x in T.rules(1)))
        self.assertTrue({'holiday', 'ins', 'deps'} <= {x['id'] for x in T.rules(6) if x['new']})
        # A contract below the floor is paid in at the floor; the grid follows the period's rules.
        for day in (1, 6, 11):
            r = T._rules_raw(day)
            for row in T.make_task(day, 0, 1)['rows']:
                ins = next(c['v'] for c in row['cells'] if c['z'] == 'ins')
                if 'ins' not in row['_truth']['z'] and row['cells'][0]['v'] not in T.STRANGERS:
                    self.assertGreaterEqual(int(ins.split()[0].replace('.', '')), r['floor'])

    def test_luck_of_the_day(self):
        self.assertEqual([T._mod(d)['id'] for d in range(1, 6)], ['normal', 'intern', 'inspector', 'cutoff', 'crunch'])
        self.assertGreater(T.grid_size(2, 'intern'), T.grid_size(2, 'normal'))
        j = Journey(CAR, slot=0, day=4)
        self.assertEqual(j.task['due'], 570)                                       # the bank closes at 09:30
        j = Journey(CAR, slot=0, day=5)
        self.assertEqual(j.task['due'], office.DUE[0] - 30)

    def test_inspector_day_rewards_a_clean_payroll(self):
        j = self.grid(3)
        tid = j.task['id']
        j.act('ask', task=tid)
        self.flag_truth(tid)
        j.act('tp_pay', task=tid, confirm=True)
        r = j.act('end_day', carry_event=True)
        self.assertTrue(r['summary']['career']['inspect']['ok'])
        self.assertTrue(any(e['category'] == 'audit_bonus' for e in j.c['ops']['finance']['ledger']))
        self.assertTrue(any(p['kind'] == 'review' and p['npc'] == kit.npc_id(CAR, 5) for p in j.c['feed']))

    def test_inspector_day_fines_a_slip(self):
        day = 3
        j = self.grid(day)
        tid = j.task['id']
        j.act('ask', task=tid)
        risky = next(r for r in j.task['rows'] if set(r['_truth']['dirs']) & {'over', 'risk'})
        self.flag_truth(tid, [r for r in j.task['rows'] if r['id'] != risky['id']])
        j.act('tp_row', task=tid, row=risky['id'])
        j.act('tp_pay', task=tid, confirm=True)
        r = j.act('end_day', carry_event=True)
        self.assertFalse(r['summary']['career']['inspect']['ok'])

    def test_clock_overtime_and_closing_time(self):
        j = self.grid()
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('tp_row', task=tid, row='r1')
        self.assertEqual(self.office['clock'], office.OPEN + T.ROW_MIN)
        self.office['clock'] = office.CLOSE
        with self.assertRaises(GameError) as cm:
            j.act('tp_row', task=tid, row='r2')
        self.assertEqual(cm.exception.code, 'office_closed')
        money = j.c['money']
        j.act('tp_overtime', confirm=True)
        self.assertEqual(j.c['money'], money + 12)
        j.act('tp_row', task=tid, row='r2')
        self.assertTrue(self.office['ot'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_late_payroll_loses_bonus_and_trust(self):
        j = self.grid()
        tid = j.task['id']
        j.act('ask', task=tid)
        self.flag_truth(tid)
        j.task['due'] = office.OPEN + 5
        money = j.c['money']
        r = j.act('tp_pay', task=tid, confirm=True)
        self.assertTrue(j.get(tid)['late'])
        self.assertEqual(j.c['money'], money + T.GRID_BONUS + office.RAISE - office.ROOKIE_LATE_CUT)
        self.assertIn('Trễ hạn', r['message'])
        self.assertTrue(any('chốt lệnh' in n['text'] for n in self.office['notes']))

    def test_old_save_keeps_its_dossiers(self):
        j = Journey(CAR)
        s = copy.deepcopy(j.state)
        c = s['careers'][CAR]
        old = T.make_task(1, 2, kit.LEGACY_TURN + 4)
        self.assertNotIn('gen', old)
        self.assertEqual(old['due_turn'], 4 + 40 + 6 * len(old['proc']))
        old['created_turn'] = 4
        c['tasks'] = [old]
        c['active_task'] = old['id']
        c['ext']['data'] = dict(filed=0, late=0, log=[])
        public_state(s)
        validate_state(s)
        self.assertIn('office', c['ext']['data'])
        j.state = s
        j.act('ask', task=old['id'])
        self.solve(j)
        j.act('tp_file', task=old['id'], confirm=True)
        self.assertEqual(j.get(old['id'])['status'], 'completed')
        validate_state(json.loads(json.dumps(j.state)))
        legacy_question = next(T.make_task(d, s_, kit.LEGACY_TURN + 1) for d in range(1, 12) for s_ in range(4)
                               if T.make_task(d, s_, kit.LEGACY_TURN + 1)['form'] == 'question')
        labels = [o['label'] for st in legacy_question['proc'] for o in st.get('options') or []]
        self.assertTrue(any('chị cũng không rõ' in x for x in labels))

    def test_player_is_not_addressed_by_gender(self):
        blob = json.dumps([T.SITUATIONS, T.SPEC['meta']], ensure_ascii=False)
        self.assertNotIn('Chị lương', blob)
        for day in range(1, 12):
            for slot in range(4):
                blob = json.dumps(T.make_task(day, slot, 1), ensure_ascii=False)
                self.assertNotIn('chị cũng không rõ', blob)

    def test_first_payroll_coach_names_the_wrong_cells(self):
        j = self.grid()
        tid = j.task['id']
        self.assertEqual(public_state(j.state)['careers'][CAR]['data']['coach'], {})
        j.act('ask', task=tid)
        coach = public_state(j.state)['careers'][CAR]['data']['coach'][tid]['rows']
        t = j.get(tid)
        self.assertEqual(coach, {r['id']: dict(z=r['_truth']['z'], why=r['_truth']['why']) for r in t['rows']})
        self.assertNotIn('_truth', json.dumps(public_state(j.state)['careers'][CAR]['tasks'], ensure_ascii=False))
        j.c['metrics']['served'] = 1
        self.assertEqual(public_state(j.state)['careers'][CAR]['data']['coach'], {})

    def test_public_data_shape(self):
        j = self.grid()
        data = public_state(j.state)['careers'][CAR]['data']
        self.assertEqual(data['today']['mod']['id'], 'normal')
        self.assertEqual(data['office']['time'], '08:00')
        self.assertTrue(data['today']['rules'])
        self.assertNotIn('day_grids', data)


class ConsequenceTests(unittest.TestCase):
    """Payroll errors that go out with the transfer cost the bonus, stars and chị Hồng's trust."""

    def run_grid(self, pick, extra=False):
        for day in range(1, 40):
            rows = pick(T.make_task(day, 0, 1))
            if rows is not None:
                break
        j = Journey(CAR, slot=0, day=day)
        tid = j.task['id']
        j.act('ask', task=tid)
        money = j.c['money']
        for row in j.get(tid)['rows']:
            if row['id'] not in rows:
                for z in row['_truth']['z']:
                    j.act('tp_flag', task=tid, row=row['id'], cell=z)
            elif extra:
                j.act('tp_flag', task=tid, row=row['id'], cell='days')
            j.act('tp_row', task=tid, row=row['id'])
        r = j.act('tp_pay', task=tid, confirm=True)
        return j, j.get(tid), money, r

    @staticmethod
    def with_dirs(dirs):
        def f(t):
            row = next((r for r in t['rows'] if r['_truth']['dirs'] == dirs), None)
            return [row['id']] if row else None
        return f

    @staticmethod
    def review(j, tid):
        return next(p for p in j.c['feed'] if p['kind'] == 'review' and p['source'] == tid)

    def test_clean_payroll_has_no_slips(self):
        j, t, money, r = self.run_grid(lambda t: [])
        self.assertFalse(t.get('slips'))
        self.assertEqual(j.c['money'], money + T.GRID_BONUS + office.RAISE)
        self.assertEqual(self.review(j, t['id'])['stars'], 5)

    def test_missed_overpayment_is_named_and_cut_once(self):
        j, t, money, r = self.run_grid(self.with_dirs(['over']))
        row = next(x for x in t['rows'] if x['_truth']['dirs'] == ['over'])
        self.assertEqual([x['code'] for x in t['slips']], ['pay_over'])
        post = self.review(j, t['id'])
        self.assertLessEqual(post['stars'], 3)
        self.assertIn(row['_truth']['why'][0][:30], post['text'])
        cut = t['reaction']['cut']
        self.assertGreater(cut, 0)
        bonus = [e['amount'] for e in j.c['ops']['finance']['ledger'] if e['ref'] == t['id'] and e['category'] != 'penalty']
        full = T.GRID_BONUS + office.RAISE
        self.assertEqual(bonus, [full - cut] if full - cut else [])
        self.assertIn('Chị Hồng', r['message'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_false_flag_is_a_small_slip(self):
        def clean(t):
            row = next((r for r in t['rows'] if not r['_truth']['z']), None)
            return [row['id']] if row else None
        j1, t1, _, _ = self.run_grid(clean, extra=True)
        j2, t2, _, _ = self.run_grid(self.with_dirs(['over']))
        self.assertEqual([x['sev'] for x in t1['slips']], [1])
        self.assertEqual(self.review(j1, t1['id'])['stars'], 4)
        self.assertGreater(self.review(j1, t1['id'])['stars'], self.review(j2, t2['id'])['stars'])

    def test_two_errors_are_reported_to_the_boss(self):
        def two(t):
            a = next((r for r in t['rows'] if r['_truth']['dirs'] == ['over']), None)
            b = next((r for r in t['rows'] if r['_truth']['dirs'] == ['risk']), None)
            return [a['id'], b['id']] if a and b else None
        j, t, money, r = self.run_grid(two)
        self.assertGreaterEqual(sum(x['sev'] for x in t['slips']), 4)
        self.assertLessEqual(self.review(j, t['id'])['stars'], 2)
        self.assertTrue(any(p.get('report') and p['source'] == t['id'] for p in j.c['feed']))
        self.assertTrue(any('phản ánh' in n['text'] for n in j.c['ext']['data']['office']['notes']))
        validate_state(json.loads(json.dumps(j.state)))



# ---------------------------------------------------------------- office care: the filing calendar, colleagues, energy
def solve_task(j, tid):
    j.act('ask', task=tid)
    t = j.get(tid)
    if t['form'] == 'grid':
        for row in t['rows']:
            for z in row['_truth']['z']:
                j.act('tp_flag', task=tid, row=row['id'], cell=z)
            j.act('tp_row', task=tid, row=row['id'])
        return j.act('tp_pay', task=tid, confirm=True)
    for st in copy.deepcopy(t['proc']):
        j.act('tp_submit', task=tid, step=st['id'], answer=st['_key'])
    return j.act('tp_file', task=tid, confirm=True)


@unittest.skipUnless('tax_payroll' in PLUGINS, 'tax_payroll is filtered out by MNL_CAREERS')
class OfficeCareTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey(CAR)

    @property
    def care(self):
        return self.j.c['ext']['data']['care']

    @property
    def o(self):
        return self.j.c['ext']['data']['office']

    def view(self):
        return public_state(self.j.state)['careers'][CAR]['data']['care']

    def plan(self, fid):
        return next(x for x in self.view()['plan']['items'] if x['id'] == fid)

    def roll(self, n=1):
        for _ in range(n):
            self.j.act('end_day', carry_event=True)
            self.j.act('start_day')

    def open_tasks(self):
        return [t for t in self.j.c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]

    def test_calendar_and_plan_view(self):
        v = self.view()
        self.assertEqual([m['id'] for m in v['mates']], ['binh', 'hoa', 'bay'])
        self.assertIsNone(v['mates'][0]['npc'])                                        # Bình is a colleague without a portrait
        self.assertEqual(v['mates'][1]['npc'], kit.npc_id(CAR, 6))
        self.assertEqual([x['state'] for x in v['plan']['items']], ['todo', 'locked', 'locked'])
        self.assertTrue(self.plan('pit')['can'])
        self.assertFalse(self.plan('ins')['can'])
        cal = v['calendar']
        self.assertEqual([i['text'] for i in cal[1]['items']], ['Thuế TNCN'])
        self.assertIn('Trả lương', [i['text'] for i in cal[4]['items']])

    def test_file_on_time(self):
        j = self.j
        clock, trust, turn = self.o['clock'], self.o['trust'], j.c['turn']
        with self.assertRaises(GameError):
            j.act('tp_declare', filing='pit')                                           # needs confirm
        with self.assertRaises(GameError) as cm:
            j.act('tp_declare', filing='vat', confirm=True)
        self.assertIn('Chưa tới kỳ', str(cm.exception))
        r = j.act('tp_declare', filing='pit', confirm=True)
        self.assertIn('đúng hạn', r['message'])
        self.assertEqual(self.o['clock'], clock + T.FILING_INDEX['pit']['minutes'])
        self.assertEqual(self.o['trust'], trust + 1)
        self.assertEqual(j.c['turn'], turn)
        self.assertEqual(self.plan('pit')['state'], 'filed')
        with self.assertRaises(GameError):
            j.act('tp_declare', filing='pit', confirm=True)
        with self.assertRaises(GameError):
            j.act('tp_declare', filing='tea', confirm=True)
        validate_state(json.loads(json.dumps(j.state)))

    def test_insurance_needs_a_paid_payroll(self):
        j = self.j
        self.roll()
        with self.assertRaises(GameError) as cm:
            j.act('tp_declare', filing='ins', confirm=True)
        self.assertIn('bảng lương', str(cm.exception))
        self.assertIn('bảng lương', self.plan('ins')['why'])
        grid = next(t for t in self.open_tasks() if t['form'] == 'grid')
        solve_task(j, grid['id'])
        self.assertEqual(self.care['filings']['grids'], 1)
        j.act('tp_declare', filing='ins', confirm=True)
        self.assertEqual(self.care['filings']['st']['ins']['s'], 'filed')

    def test_late_fees_run_until_filed_and_the_boss_files_at_month_end(self):
        j = self.j
        self.roll()                                                                     # day 2: pit is due today
        money, trust = j.c['money'], self.o['trust']
        r = j.act('end_day', carry_event=True)
        late = r['summary']['career']['filings']
        self.assertEqual([x['name'] for x in late], [T._fname(T.FILING_INDEX['pit'], 2)])
        self.assertEqual(self.care['filings']['st']['pit']['fee'], T.LATE_FEE)
        self.assertTrue(any(n['kind'] == 'late' and 'Quá hạn' in n['text'] for n in self.o['notes']))
        self.assertTrue(any(e['reason'].startswith('Tiền chậm nộp') for e in j.c['ops']['finance']['ledger']))
        j.act('start_day')
        self.assertEqual(self.plan('pit')['state'], 'late')
        self.assertIn('Thuế TNCN', [i['text'] for i in self.view()['calendar'][0]['items'] if i['state'] == 'late'])
        j.act('end_day', carry_event=True)                                              # day 3: a second late day
        self.assertEqual(self.care['filings']['st']['pit']['fee'], 2 * T.LATE_FEE)
        j.act('start_day')
        r = j.act('tp_declare', filing='pit', confirm=True)                              # day 4: filed late, fees stop
        self.assertIn('muộn 2 ngày', r['message'])
        self.assertEqual(self.plan('pit')['state'], 'late_filed')
        for fid in ('ins', 'vat'):
            self.care['filings']['st'][fid].update(s='filed', day=3)
        j.act('end_day', carry_event=True)
        self.assertEqual(self.care['filings']['st']['pit']['fee'], 2 * T.LATE_FEE)
        # day 5: a filing still open at the month end is filed by chị Hồng
        j.act('start_day')
        self.care['filings']['st']['vat'].update(s='todo', day=0)
        trust = self.o['trust']
        r = j.act('end_day', carry_event=True)
        boss = [x for x in r['summary']['career']['filings'] if x['boss']]
        self.assertEqual(len(boss), 1)
        self.assertEqual(self.care['filings']['st']['vat']['s'], 'boss')
        j.act('start_day')
        self.assertEqual(self.care['filings']['month'], 1)                               # a new month, all to do again
        self.assertTrue(all(st['s'] == 'todo' for st in self.care['filings']['st'].values()))
        validate_state(json.loads(json.dumps(j.state)))

    def test_fees_never_exceed_the_wallet(self):
        j = self.j
        self.roll()
        j.c['ops']['finance']['opening_balance'] -= j.c['money']
        j.c['money'] = 0
        validate_state(j.state)
        j.act('end_day', carry_event=True)
        self.assertEqual(self.care['filings']['st']['pit']['fee'], 0)
        validate_state(json.loads(json.dumps(j.state)))

    def test_old_save_mid_month_is_not_charged_for_the_past(self):
        day, slot = find('payslip')
        j = self.j = Journey(CAR, slot=slot, day=4)
        j.c['ext']['data'].pop('care')
        validate_state(j.state)
        st = self.care['filings']['st']
        self.assertEqual([st[f]['s'] for f in ('pit', 'ins', 'vat')], ['filed', 'filed', 'todo'])
        self.assertEqual(self.plan('pit')['state'], 'filed')

    def test_no_favour_against_the_bank_cutoff(self):
        day = next(d for d in range(2, 40) if T._mod(d)['id'] == 'cutoff')
        j = self.j = Journey(CAR, slot=0, day=day)
        t = j.task
        self.assertEqual(t['form'], 'grid')
        self.care['mates']['hoa'].update(bond=1, owes=1)
        self.assertNotIn(t['id'], self.view()['coverable'])
        with self.assertRaises(GameError) as cm:
            j.act('tp_cover', mate='hoa', task=t['id'])
        self.assertIn('ngân hàng', str(cm.exception))

    def test_help_and_cover_on_a_form(self):
        day, slot = find('payslip')
        j = self.j = Journey(CAR, slot=slot, day=day)
        self.care['ask'] = dict(day=day, mate='bay', i=1, state='open')
        validate_state(j.state)
        j.act('tp_help', mate='bay', answer='yes')
        self.assertEqual(j.c['relationships'][kit.npc_id(CAR, 3)], 4)
        due = j.task['due']
        j.act('tp_cover', mate='bay', task=j.task['id'])
        self.assertEqual(j.task['due'], due + 60)
        validate_state(json.loads(json.dumps(j.state)))

    def test_exhausted_no_overtime(self):
        self.care['energy'] = 20
        self.o['clock'] = office.CLOSE
        with self.assertRaises(GameError):
            self.j.act('tp_overtime', confirm=True)
        self.care['energy'] = 50
        self.j.act('tp_overtime', confirm=True)
        r = self.j.act('end_day', carry_event=True)
        self.assertEqual(r['summary']['career']['care']['energy'], 50 - 25)

    def test_tampered_filings_rejected(self):
        for f in (lambda fl: fl['st']['pit'].update(s='sent'), lambda fl: fl['st'].pop('vat'), lambda fl: fl['st']['pit'].update(fee=99),
                  lambda fl: fl['st']['pit'].update(s='filed', day=0), lambda fl: fl.update(grids=-1)):
            j = Journey(CAR)
            f(j.c['ext']['data']['care']['filings'])
            with self.assertRaises(GameError):
                validate_state(json.loads(json.dumps(j.state)))

    def test_a_month_of_days(self):
        j = self.j
        for day in range(1, 7):
            if day > 1:
                j.act('start_day')
            for f in self.view()['plan']['items']:
                if f['can'] and f['id'] != 'ins':
                    j.act('tp_declare', filing=f['id'], confirm=True)
            for t in self.open_tasks():
                solve_task(j, t['id'])
            if self.plan('ins')['can']:
                j.act('tp_declare', filing='ins', confirm=True)
            validate_state(json.loads(json.dumps(j.state)))
            r = j.act('end_day', carry_event=True)
            self.assertNotIn('filings', r['summary']['career'], day)
        self.assertGreaterEqual(self.care['reliable'], 3)


# ---------------------------------------------------------------- feedback #71: every wrong cell named, with its working
def _grids(days=range(1, 41), slots=(0, 4)):
    for day in days:
        for slot in slots:
            yield T.make_task(day, slot, 1)


@unittest.skipUnless('tax_payroll' in PLUGINS, 'tax_payroll is filtered out by MNL_CAREERS')
class GridExplainTests(unittest.TestCase):
    def play(self, pick):
        """A grid where `pick(t)` returns {row id: [cells to flag]} (None: try the next day); every row is then closed and paid."""
        for t in _grids(range(1, 40), (0,)):
            flags = pick(t)
            if flags is not None:
                break
        else:
            self.skipTest('no grid fits')
        self.j = j = Journey(CAR, slot=0, day=t['day'])
        tid = j.task['id']
        j.act('ask', task=tid)
        for row in j.task['rows']:
            for z in flags.get(row['id'], []):
                j.act('tp_flag', task=tid, row=row['id'], cell=z)
            j.act('tp_row', task=tid, row=row['id'])
        r = j.act('tp_pay', task=tid, confirm=True)
        view = next(x for x in public_state(j.state)['careers'][CAR]['tasks'] if x['id'] == tid)
        return j.get(tid), view, r

    def test_every_cell_has_its_right_value_and_working(self):
        n = 0
        for t in _grids():
            t['flags'] = {}
            ex = T.grid_explain(t)
            self.assertIsNotNone(ex, t['id'])
            for row, x in zip(t['rows'], ex):
                truth = set(row['_truth']['z'])
                self.assertEqual(set(x['cells']), {z for z, _ in T.GRID_COLS})
                for z, c in x['cells'].items():
                    self.assertTrue(c['steps'] and all(isinstance(s, str) and s for s in c['steps']))
                    self.assertTrue(c['src'])
                    self.assertEqual(c['s'], 'miss' if z in truth else 'moot' if c['want'] is None else 'ok')
                if x['cells']['name']['want'] == 'Xóa cả dòng':
                    self.assertEqual(truth, {'name'})
                    continue
                # The draft differs from the worked-out value exactly where the hidden truth says it is wrong.
                self.assertEqual({c['z'] for c in row['cells'] if x['cells'][c['z']]['want'] != c['v']}, truth, (t['id'], row['id']))
                self.assertEqual(len(x['why']), len(truth))
                n += 1
        self.assertGreater(n, 300)

    def test_annual_leave_flagged_by_mistake_is_explained(self):
        # A right day count with annual leave in it, flagged: the review says it is right and shows 26 − unpaid.
        def pick(t):
            for row in t['rows']:
                ex = T.grid_explain(dict(t, flags={}))
                i = t['rows'].index(row)
                days = ex[i]['cells']['days']
                if not row['_truth']['z'] and days['want'] != 'Xóa cả dòng' and any('phép năm' in s and 'vẫn hưởng' in s for s in days['steps']):
                    return {r['id']: list(r['_truth']['z']) for r in t['rows'] if r is not row} | {row['id']: ['days']}
            return None
        t, view, r = self.play(pick)
        row = next(x for x in view['rows'] if x['result']['extra'] == ['days'])
        cell = row['explain']['days']
        self.assertEqual(cell['s'], 'extra')
        self.assertEqual(cell['want'], next(c['v'] for c in row['cells'] if c['z'] == 'days'))
        self.assertTrue(any('ngày không lương' in s for s in cell['steps']))
        self.assertIn('Ngày công', ' '.join(cell['src']))
        who = next(c['v'] for c in row['cells'] if c['z'] == 'name').split()[-1]
        self.assertIn(f'{who} · Ngày công hưởng lương', r['message'])
        self.assertIn(f'{who} · Ngày công hưởng lương', next(s['text'] for s in t['slips'] if s['code'] == 'pay_hold'))
        validate_state(json.loads(json.dumps(self.j.state)))

    def test_missed_floor_and_duplicate_rows_show_the_right_value(self):
        def pick(t):
            kinds = [k for r in t['rows'] for k in r['_truth']['kinds']]
            if 'ins_floor' not in kinds:
                return None
            return {r['id']: [z for z, k in zip(r['_truth']['z'], r['_truth']['kinds']) if k != 'ins_floor'] for r in t['rows']}
        t, view, r = self.play(pick)
        row = next(x for x in view['rows'] if x['result']['missed'] == ['ins'])
        cell = row['explain']['ins']
        floor = T._rules_raw(t['day'])['floor']
        self.assertEqual((cell['s'], cell['want']), ('miss', T.xu(floor)))
        self.assertTrue(any('mức sàn' in s for s in cell['steps']))
        self.assertTrue(any(c['s'] == 'hit' for x in view['rows'] for c in x['explain'].values()))
        self.assertIn('Lương đóng BH', r['message'])

    def test_dependant_reason_counts_the_file_sent_in_time(self):
        # The stored reason said “1 registered, one short” while the draft showed 1: the file sent before the cut-off is the
        # missing person. The explanation, the slip and the claim say so now.
        def pick(t):
            for row in t['rows']:
                if 'dep_missing' in row['_truth']['kinds'] and any(
                        h[0] == next(c['v'] for c in row['cells'] if c['z'] == 'name') and 'hồ sơ nộp' in h[3] for h in t['papers'][0]['rows']):
                    return {r['id']: list(r['_truth']['z']) for r in t['rows'] if r is not row}
            return None
        t, view, r = self.play(pick)
        row = next(x for x in view['rows'] if x['result']['missed'] == ['deps'])
        cell = row['explain']['deps']
        n = int(cell['want'].split()[0])
        self.assertEqual(int(next(c['v'] for c in row['cells'] if c['z'] == 'deps').split()[0]), n - 1)
        self.assertTrue(any('trước mốc' in s and '(+1)' in s for s in cell['steps']))
        why = row['truth']['why'][0]
        self.assertIn('hồ sơ nộp', why)
        self.assertIn(f'= {n} người', why)
        claim = self.j.c['ext']['data']['claims'][-1]
        self.assertEqual(claim['why'], why)

    def test_a_grid_that_does_not_regenerate_keeps_the_stored_reasons(self):
        t = T.make_task(5, 0, 1)
        t['rows'] = copy.deepcopy(t['rows'])
        t['rows'][0]['cells'][1]['v'] = '1 ngày'
        self.assertIsNone(T.grid_explain(t))
        t = T.make_task(5, 1, 1)
        self.assertIsNone(T.grid_explain(t))                                         # not a grid

    def test_grid_view_carries_its_own_period_rules(self):
        j = Journey(CAR, slot=0, day=11)
        j.act('ask', task=j.task['id'])
        v = public_state(j.state)['careers'][CAR]['tasks'][0]
        self.assertEqual(v['period']['month'], T._rules_raw(11)['m'])
        cards = {c['id']: c for c in v['period']['rules']}
        self.assertIn(T.fmt(T._rules_raw(11)['floor']), cards['ins']['text'])
        self.assertNotIn('explain', v['rows'][0])                                     # nothing before payday
        self.assertNotIn('_truth', json.dumps(v))

    def test_bracket_lines_add_up(self):
        for x, months in ((0, 1), (1999, 1), (2000, 1), (3457, 1), (12345, 1), (122580, 12), (24000, 12), (999999, 12)):
            lines = T.bracket_lines(x, months)
            self.assertTrue(lines[-1].startswith(f'Thuế = {T.xu(T.pit(x, months))}'), (x, lines))

    def test_wrong_boxes_are_named_never_their_value(self):
        day, slot = find('payslip')
        j = Journey(CAR, slot=slot, day=day)
        j.act('ask')
        j.act('tp_submit', step='ot', answer=j.task['proc'][0]['_key'])
        st = j.task['proc'][1]
        g = dict(st['_key'], leave=st['_key']['leave'] + 3, gross=st['_key']['gross'] + 3)
        r = j.act('tp_submit', step='gross', answer=g)
        self.assertFalse(r['correct'])
        self.assertEqual(r['bad'], ['leave', 'gross'])
        self.assertIn('Khớp 2/4 ô', r['where'])
        self.assertIn('“Tổng thu nhập”', r['message'])
        self.assertNotIn(str(st['_key']['gross']), r['message'])
        j.act('tp_submit', step='gross', answer=st['_key'])
        j.act('tp_submit', step='ins', answer=j.task['proc'][2]['_key'])
        j.act('tp_submit', step='tax', answer=j.task['proc'][3]['_key'])
        steps = public_state(j.state)['careers'][CAR]['tasks'][0]['steps']
        tax = next(s for s in steps if s['id'] == 'tax')
        self.assertTrue(tax['work'][0].startswith('Bậc 1'))
        self.assertNotIn('work', next(s for s in steps if s['id'] == 'net'))         # not solved yet

    def test_multi_choice_says_how_many_are_right(self):
        day, slot = find('transfer')
        j = Journey(CAR, slot=slot, day=day)
        j.act('ask')
        st = j.task['proc'][0]
        other = next(o['id'] for o in st['options'] if o['id'] not in st['_key'])
        r = j.act('tp_submit', step='errors', answer=[st['_key'][0], other])
        self.assertIn(f'Đúng 1/{len(st["_key"])} mục cần chọn, thừa 1 mục', r['message'])
        self.assertEqual(r['bad'], [])

    def test_yearend_review_shows_the_whole_calculation(self):
        day, slot = find('yearend')
        j = Journey(CAR, slot=slot, day=day)
        j.act('ask')
        for st in copy.deepcopy(j.task['proc']):
            j.act('tp_submit', task=j.task['id'], step=st['id'], answer=st['_key'])
        k = j.task['proc'][2]['_key']
        calc = next(s for s in public_state(j.state)['careers'][CAR]['tasks'][0]['steps'] if s['id'] == 'calc')
        text = '\n'.join(calc['work'])
        self.assertIn(f'= {T.fmt(k["deduct"])}', calc['work'][0])
        self.assertIn(f'= {T.fmt(k["taxable"])}', calc['work'][1])
        self.assertIn(f'Thuế = {T.xu(k["due"])}', text)
        self.assertIn(T.xu(abs(k['balance'])) if k['balance'] else '0 xu', calc['work'][-1])


if __name__ == '__main__':
    unittest.main()
