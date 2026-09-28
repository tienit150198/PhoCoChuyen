"""Paperwork desks shared by the pharmacy counter, the bookkeeping desk and the
support station: schedule, secrecy, grading, saves and old-save upgrades."""
import copy
import json
import re
import unittest

from game import desk, desk_content as dc
from game.content import make_task
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from tests.desk_support import Journey, desk_journey, find_case, flag_all, secrets, solve_desk

CAREERS = dc.CAREERS
META = re.compile(r'mô phỏng|giả lập|\bgame\b', re.I)


def all_text(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from all_text(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from all_text(v)


def view(j, n=0):
    return public_state(j.state)['careers'][j.career]['tasks'][n]


def review_of(j, tid):
    return next(f for f in j.c['feed'] if (f.get('feedback') or {}).get('task') == tid)


class ScheduleTests(unittest.TestCase):
    def test_day_one_keeps_the_classic_counter_first(self):
        for cid in CAREERS:
            self.assertIsNone(dc.plan(cid, 1, 0))
            self.assertIsNone(dc.plan(cid, 1, 1))
            self.assertEqual([dc.plan(cid, 1, s) for s in range(2, 6)], dc.DAY_ONE[cid])

    def test_plan_is_deterministic_and_varied(self):
        for cid in CAREERS:
            self.assertEqual([dc.plan(cid, 7, s) for s in range(12)], [dc.plan(cid, 7, s) for s in range(12)])
            seen = {dc.plan(cid, d, s) for d in range(1, 15) for s in range(3)} - {None}
            self.assertGreaterEqual(len(seen), 10, cid)
            # the original counter task still shows up most days
            classic_days = sum(any(dc.plan(cid, d, s) is None for s in range(3)) for d in range(2, 30))
            self.assertGreaterEqual(classic_days, 18, cid)
            # days do not all open with the same case
            firsts = [dc.plan(cid, d, 0) for d in range(2, 30)]
            self.assertGreater(len(set(firsts)), 5, cid)

    def test_deck_never_repeats_a_case_the_next_day(self):
        for cid in CAREERS:
            prev = set()
            for day in range(1, 80):
                today = {dc.plan(cid, day, s) for s in range(dc.PACE_SLOTS)} & set(dc.POOL[cid])
                self.assertFalse(today & prev, (cid, day, today & prev))
                prev = today
            # every unlocked case comes round within a couple of weeks
            for v, (low, _) in dc.POOL[cid].items():
                days = [d for d in range(low, low + 80) if v in {dc.plan(cid, d, s) for s in range(dc.PACE_SLOTS)}]
                self.assertTrue(days and days[0] - low <= 10, (cid, v, days[:1]))
                self.assertLessEqual(max(b - a for a, b in zip(days, days[1:])), 14, (cid, v))

    def test_deck_does_not_depend_on_what_was_asked_first(self):
        want = {cid: [dc.plan(cid, d, s) for d in (40, 3, 17, 9000) for s in range(6)] for cid in CAREERS}
        dc._MORNINGS.clear()
        for cid in CAREERS:
            dc.plan(cid, 60, 3)  # warm the cache in a different order
            self.assertEqual([dc.plan(cid, d, s) for d in (40, 3, 17, 9000) for s in range(6)], want[cid])

    def test_at_least_eight_new_situations_per_career(self):
        for cid in CAREERS:
            self.assertGreaterEqual(len(dc.POOL[cid]), 11, cid)
            self.assertGreaterEqual(len(dc.ALL_VARIANTS[cid]), 12, cid)

    def test_difficulty_grows_with_the_day(self):
        self.assertEqual([dc.tier(d) for d in (1, 3, 7, 12)], [1, 2, 3, 4])
        for cid in CAREERS:
            early = {dc.plan(cid, d, s) for d in (1, 2) for s in range(12)} - {None}
            late = {dc.plan(cid, d, s) for d in range(8, 20) for s in range(6)} - {None}
            self.assertLess(len(early), len(late), cid)
            self.assertTrue(all(dc.POOL[cid][v][0] <= 2 for v in early if v in dc.POOL[cid]), cid)
        # pay and the support timer both follow the tier
        a = desk_journey('pharmacy', 'ph_otc', days=range(1, 3))
        b = desk_journey('pharmacy', 'ph_otc', days=range(10, 40))
        self.assertLess(desk.pay_for(a.task, 'perfect'), desk.pay_for(b.task, 'perfect'))
        early = desk_journey('customer_care', 'cs_wrong', days=range(3, 5)).task
        late = desk_journey('customer_care', 'cs_wrong', days=range(10, 40)).task
        self.assertLess(late['due_turn'] - late['created_turn'], early['due_turn'] - early['created_turn'])
        # rules pile up: the book on day 12 is thicker than on day 1
        for cid in CAREERS:
            self.assertGreater(len(dc.bulletin(cid, 12)['rules']), len(dc.bulletin(cid, 1)['rules']), cid)

    def test_every_case_is_self_consistent(self):
        for cid in CAREERS:
            for day in range(1, 31):
                for slot in range(6):
                    v = dc.plan(cid, day, slot)
                    if not v:
                        continue
                    case, b, _ = dc.build(cid, v, day, slot)
                    self.assertEqual(case, dc.build(cid, v, day, slot)[0])
                    ids = {x['id'] for x in case['verdicts']}
                    fields = {d['id'] + '.' + f['id'] for d in case['docs'] for f in d['fields']}
                    rules = {r['id'] for r in b['rules']}
                    checks = {c['id'] for c in case.get('checks', [])}
                    self.assertTrue(set(case['accept']) <= ids and 'best' in case['accept'].values(), (cid, v))
                    self.assertTrue(ids <= set(case['says']), (cid, v))
                    self.assertTrue(set(case['risk']) <= ids and set(case.get('tip', {})) <= ids, (cid, v))
                    self.assertTrue(set(case['pleases']) <= ids, (cid, v))
                    for i in case['issues']:
                        self.assertTrue(set(i['fields']) <= fields and i['rule'] in rules, (cid, v, day, i))
                    self.assertEqual(len({i['id'] for i in case['issues']}), len(case['issues']))
                    self.assertTrue(set(case.get('needs', [])) <= checks, (cid, v))
                    self.assertTrue(set(case.get('requires', {}).values()) <= checks, (cid, v))
                    hidden = {f['hidden'] for d in case['docs'] for f in d['fields'] if f.get('hidden')}
                    self.assertTrue(hidden <= checks, (cid, v))
                    # a right stamp never carries risk
                    self.assertFalse(set(case['accept']) & {k for k, n in case['risk'].items() if n}, (cid, v))
                    for text in all_text(case):
                        self.assertIsNone(META.search(text), (cid, v, text))

    def test_rulebook_changes_over_days(self):
        self.assertNotEqual(dc.stamps(2), dc.stamps(3))
        self.assertIn('ph_stamp', [r['id'] for r in dc.bulletin('pharmacy', 3)['rules'] if r['new']])
        self.assertNotEqual(dc.recall_lots(3), dc.recall_lots(4))
        self.assertGreater(len({dc.bank_fee(d) for d in range(1, 20)}), 1)
        self.assertNotEqual(dc.window_days(3), dc.window_days(4))
        self.assertIn('ac_fake', [r['id'] for r in dc.bulletin('accounting', 6)['rules'] if r['new']])
        self.assertNotIn('ac_fake', [r['id'] for r in dc.bulletin('accounting', 5)['rules']])
        for cid in CAREERS:
            for d in range(1, 20):
                for text in all_text(dc.bulletin(cid, d)):
                    self.assertIsNone(META.search(text))

    def test_new_rules_are_announced_once(self):
        j = Journey('pharmacy', slot=0, day=3)
        first = j.act('advance')
        self.assertTrue(any('quy định mới' in x for x in first['effects']))
        again = j.act('advance')
        self.assertFalse(any('quy định mới' in x for x in again['effects']))


class SecrecyTests(unittest.TestCase):
    def test_papers_arrive_only_after_asking(self):
        j = desk_journey('pharmacy', 'ph_clean')
        self.assertIsNone(view(j)['docs'])
        self.assertTrue(view(j)['rules'])
        j.act('ask')
        self.assertTrue(view(j)['docs'])

    def test_answers_are_never_in_the_public_view(self):
        for cid, variant in (('pharmacy', 'ph_norx'), ('accounting', 'ac_dup'), ('customer_care', 'cs_takeover')):
            j = desk_journey(cid, variant)
            j.act('ask')
            raw = json.dumps(view(j), ensure_ascii=False)
            for i in secrets(j)['issues']:
                self.assertNotIn(i['why'], raw)
            for key in ('"accept"', '"issues"', '"says"', '"risk"', '"pleases"', '"cash"'):
                self.assertNotIn(key, raw)

    def test_locked_rows_open_after_the_check(self):
        j = desk_journey('pharmacy', 'ph_cold')
        j.act('ask')
        fridge = next(d for d in view(j)['docs'] if d['id'] == 'fridge')
        self.assertTrue(all(f['value'] is None and f['locked'] for f in fridge['fields']))
        with self.assertRaises(GameError):
            j.act('desk_flag', task=j.task['id'], field='fridge.t12', rule='ph_cold')
        r = j.act('desk_check', task=j.task['id'], check='fridge')
        self.assertIn('12 giờ', r['message'])
        fridge = next(d for d in view(j)['docs'] if d['id'] == 'fridge')
        self.assertTrue(all(f['value'] for f in fridge['fields']))

    def test_no_desk_work_before_the_papers(self):
        j = desk_journey('pharmacy', 'ph_clean')
        with self.assertRaises(GameError):
            j.act('desk_decide', task=j.task['id'], verdict='give', confirm=True)


class PlayTests(unittest.TestCase):
    def test_careful_play_is_perfect_for_every_situation(self):
        for cid in CAREERS:
            for variant in sorted(dc.ALL_VARIANTS[cid]):
                with self.subTest(career=cid, variant=variant):
                    j = desk_journey(cid, variant)
                    before = j.c['money']
                    t = solve_desk(j)
                    self.assertIn(t['status'], ('completed', 'referred'))
                    self.assertEqual(t['grade'], 'perfect', (variant, t['result']))
                    self.assertEqual(t['mistakes'], 0)
                    self.assertGreaterEqual(j.c['money'], before + desk.pay_for(t, 'perfect'))
                    self.assertEqual(review_of(j, t['id'])['feedback']['fair'], 5)
                    self.assertIsNone(j.last['desk_result']['citation'])
                    validate_state(j.state)

    def test_each_wrong_stamp_is_graded_wrong_and_unpaid(self):
        for cid in CAREERS:
            for variant in sorted(dc.POOL[cid]):
                j = desk_journey(cid, variant)
                case = secrets(j)
                bad = next((v['id'] for v in j.task['verdicts'] if v['id'] not in case['accept']), None)
                if not bad:
                    continue
                with self.subTest(career=cid, variant=variant, stamp=bad):
                    t = solve_desk(j, verdict=bad)
                    self.assertEqual(t['grade'], 'wrong')
                    self.assertEqual(j.last['desk_result']['pay'], 0)
                    self.assertEqual(t['mistakes'], 3)
                    validate_state(j.state)

    def test_wrong_flag_costs_patience_and_the_perfect_grade(self):
        j = desk_journey('pharmacy', 'ph_expired')
        tid = j.task['id']
        j.act('ask')
        before = j.task.get('patience', 100)
        r = j.act('desk_flag', task=tid, field='slip.patient', rule='ph_person')
        self.assertEqual(r['mark'], 'wrong')
        self.assertEqual(j.task['false_flags'], 1)
        self.assertEqual(j.task['patience'], max(25, before - desk.FALSE_FLAG_PATIENCE))
        flag_all(j)
        j.act('desk_decide', task=tid, verdict='refuse', confirm=True)
        self.assertEqual(j.get(tid)['grade'], 'good')
        self.assertEqual(j.get(tid)['result']['pay'], desk.pay_for(j.get(tid), 'good'))

    def test_right_row_wrong_rule_is_a_hint_not_a_penalty(self):
        j = desk_journey('pharmacy', 'ph_expired')
        j.act('ask')
        r = j.act('desk_flag', task=j.task['id'], field='slip.until', rule='ph_stamp')
        self.assertEqual(r['mark'], 'partial')
        self.assertEqual(j.task['false_flags'], 0)
        self.assertEqual(j.task['found'], [])
        with self.assertRaises(GameError):  # the same mark twice
            j.act('desk_flag', task=j.task['id'], field='slip.until', rule='ph_stamp')
        with self.assertRaises(GameError):  # a rule that is not in today's book
            j.act('desk_flag', task=j.task['id'], field='slip.until', rule='ac_once')

    def test_missed_row_is_only_good(self):
        j = desk_journey('pharmacy', 'ph_expired')
        j.act('ask')
        r = j.act('desk_decide', task=j.task['id'], verdict='refuse', confirm=True)
        self.assertEqual(r['desk_result']['grade'], 'good')
        self.assertTrue(r['desk_result']['missed'])

    def test_stamp_needs_confirmation_and_a_listed_verdict(self):
        j = desk_journey('accounting', 'ac_clean')
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('desk_decide', task=j.task['id'], verdict='post')
        with self.assertRaises(GameError):
            j.act('desk_decide', task=j.task['id'], verdict='claim', confirm=True)
        tid = j.task['id']
        j.act('desk_decide', task=tid, verdict='post', confirm=True)
        money = j.c['money']
        with self.assertRaises(GameError):  # no second stamp, no second pay
            j.act('desk_decide', task=tid, verdict='post', confirm=True)
        self.assertEqual(j.c['money'], money)

    def test_classic_counter_actions_do_not_touch_desk_cases(self):
        j = desk_journey('pharmacy', 'ph_qty')
        j.act('ask')
        before = copy.deepcopy(j.state)
        for action, payload in (('ph_pick', dict(item='P-01-A')), ('ph_deliver', {}), ('ph_refer', {}), ('ph_inspect', dict(lot='P-01-A'))):
            with self.assertRaises(GameError):
                apply_action(j.state, 'pharmacy', action, dict(payload, task=j.task['id']))
        self.assertEqual(j.state, before)
        k = desk_journey('customer_care', 'cs_wrong')
        with self.assertRaises(GameError):
            k.act('cs_identity', task=k.task['id'])
        a = desk_journey('accounting', 'ac_dup')
        with self.assertRaises(GameError):
            a.act('ac_inspect', task=a.task['id'], doc='CT-01')

    def test_closed_shift_blocks_desk_work(self):
        j = desk_journey('pharmacy', 'ph_otc')
        j.act('ask')
        j.c['open'] = False
        with self.assertRaises(GameError):
            j.act('desk_decide', task=j.task['id'], verdict='give', confirm=True)

    def test_risky_stamps_warn_twice_then_fine(self):
        j = desk_journey('pharmacy', 'ph_norx')
        j.act('ask')
        r = j.act('desk_decide', task=j.task['id'], verdict='give', confirm=True)['desk_result']
        self.assertEqual(r['grade'], 'wrong')
        self.assertEqual(r['tip'], 0)  # the temptation is offered, but cô Thu hands it back after a wrong hand-off
        self.assertIn('trả lại 10 xu', ' '.join(r['lines']))
        self.assertEqual(r['fine'], 0)
        self.assertIn('Phiếu nhắc 1/2', ' '.join(r['lines']))
        self.assertEqual(j.c['ext']['data']['desk']['risk'], 3)
        validate_state(j.state)
        # …and the third risky stamp of a day is fined as well.
        k = desk_journey('pharmacy', 'ph_norx')
        k.c['ext']['data']['desk']['today'] = dict(day=k.c['day'], citations=2, fines=0)
        k.act('ask')
        money = k.c['money']
        r = k.act('desk_decide', task=k.task['id'], verdict='give', confirm=True)['desk_result']
        self.assertEqual(r['fine'], 15)
        self.assertIn('Phiếu phạt', ' '.join(r['lines']))
        self.assertEqual(k.c['money'], money - 15)
        fines = [x for x in k.c['ops']['finance']['ledger'] if x['category'] == 'fine']
        self.assertEqual([x['amount'] for x in fines], [-15])
        self.assertEqual(k.c['ext']['data']['desk']['citations'][-1]['fine'], 15)
        validate_state(k.state)

    def test_inspection_day_praises_a_clean_counter(self):
        day = next(d for d in range(2, 20) if d % dc.INSPECT_EVERY['pharmacy'] == 0)
        j = Journey('pharmacy', slot=0, day=day)
        self.assertEqual(j.task['variant'], 'ph_inspect')
        solve_desk(j)
        r = j.act('end_day', carry_event=True)
        self.assertIn('Thưởng 25 xu', r['summary']['career']['note'])
        self.assertTrue(any(x['amount'] == 25 and x['ref'] == f'desk-inspect-{day}' for x in j.c['ops']['finance']['ledger']))
        self.assertEqual(j.c['ext']['data']['desk']['inspections'][-1]['outcome'], 'praise')
        validate_state(j.state)

    def test_inspection_day_fines_a_risky_counter(self):
        j = Journey('accounting', slot=0, day=5)
        j.c['ext']['data']['desk']['risk'] = 6
        money = j.c['money']
        r = j.act('end_day', carry_event=True)
        self.assertIn('lập biên bản', r['summary']['career']['note'])
        self.assertTrue(any(x['amount'] == -30 and x['category'] == 'fine' for x in j.c['ops']['finance']['ledger']))
        self.assertEqual(j.c['ext']['data']['desk']['risk'], 0)
        self.assertEqual(j.c['ext']['data']['desk']['inspections'][-1]['outcome'], 'fine')
        self.assertLess(j.c['money'], money)
        validate_state(j.state)

    def test_small_risk_is_a_warning(self):
        j = Journey('customer_care', slot=0, day=6)
        j.c['ext']['data']['desk']['risk'] = 2
        r = j.act('end_day', carry_event=True)
        self.assertIn('nhắc nhở', r['summary']['career']['note'])
        self.assertEqual(j.c['ext']['data']['desk']['inspections'][-1]['outcome'], 'warning')

    def test_staff_can_run_a_check_but_never_stamps(self):
        j = desk_journey('pharmacy', 'ph_cold')
        self.assertIsNone(desk.assist(j.state, j.c, j.task, 'inspection'))  # nothing before the papers
        j.act('ask')
        note = desk.assist(j.state, j.c, j.task, 'inspection')
        self.assertIn('Quyết định vẫn là của bạn', note)
        self.assertIn('fridge', j.task['verified'])
        self.assertIsNone(j.task['verdict'])
        validate_state(j.state)

    def test_wrong_stamp_costs_stars_even_when_it_pleased_at_the_counter(self):
        # Changed on purpose (consequences wave): selling without a slip used to earn 4★ because it pleased.
        j = desk_journey('pharmacy', 'ph_norx')
        t = solve_desk(j, verdict='give')
        self.assertEqual(review_of(j, t['id'])['feedback']['fair'], 1)
        k = desk_journey('pharmacy', 'ph_otc')
        t = solve_desk(k, verdict='refuse')
        self.assertEqual(review_of(k, t['id'])['feedback']['fair'], 3)

    def test_day_summary_counts_the_desk(self):
        j = desk_journey('accounting', 'ac_clean', days=range(2, 40))
        solve_desk(j)
        r = j.act('end_day', carry_event=True)
        self.assertIn('1 chuẩn', r['summary']['career']['lines'][0])


class StoryTests(unittest.TestCase):
    def chapter(self, cid, n, flags=()):
        day = next(d for d, ch in dc.STORY_DAYS[cid].items() if ch == n)
        j = Journey(cid, slot=1, day=day)
        self.assertTrue(j.task['variant'].endswith('_story'))
        self.assertEqual(j.task['chapter'], n)
        j.c['ext']['data']['desk']['flags'] = list(flags)
        return j

    def test_each_career_has_four_chapters_that_play_cleanly(self):
        for cid in CAREERS:
            for n in range(1, 5):
                with self.subTest(career=cid, chapter=n):
                    j = self.chapter(cid, n)
                    self.assertEqual(solve_desk(j)['grade'], 'perfect')

    def test_pharmacy_ending_remembers_the_rushed_delivery(self):
        j = self.chapter('pharmacy', 2)
        solve_desk(j, verdict='give')
        self.assertIn('nam_risk', j.c['ext']['data']['desk']['flags'])
        late = self.chapter('pharmacy', 4, ['nam_risk'])
        solve_desk(late)
        self.assertIn('soát kỹ hơn', late.last['desk_result']['says'])
        self.assertEqual(late.last['desk_result']['tip'], 0)
        kind = self.chapter('pharmacy', 4, ['nam_safe'])
        solve_desk(kind)
        self.assertEqual(kind.last['desk_result']['tip'], 10)

    def test_hidden_revenue_comes_back_at_the_tax_letter(self):
        j = self.chapter('accounting', 2)
        t = solve_desk(j, verdict='comply')
        self.assertEqual(t['grade'], 'wrong')
        self.assertIn('hoa_hid', j.c['ext']['data']['desk']['flags'])
        hid = self.chapter('accounting', 3, ['hoa_hid'])
        solve_desk(hid)
        self.assertIn('nộp phạt', hid.last['desk_result']['says'])
        honest = self.chapter('accounting', 3, ['hoa_honest'])
        solve_desk(honest)
        self.assertEqual(honest.last['desk_result']['tip'], 15)
        loan = self.chapter('accounting', 4, ['hoa_honest'])
        money = loan.c['money']
        solve_desk(loan)
        self.assertEqual(loan.last['desk_result']['tip'], 10)
        self.assertGreaterEqual(loan.c['money'], money + 10)

    def test_the_favor_is_remembered(self):
        j = self.chapter('customer_care', 3)
        solve_desk(j, verdict='favor')
        self.assertIn('phuc_favor', j.c['ext']['data']['desk']['flags'])
        again = self.chapter('customer_care', 4, ['phuc_favor'])
        solve_desk(again)
        self.assertIn('từ chối khó hơn', again.last['desk_result']['says'])
        fair = self.chapter('customer_care', 4, ['phuc_fair'])
        solve_desk(fair)
        self.assertEqual(fair.last['desk_result']['tip'], 10)


class SaveTests(unittest.TestCase):
    def test_mid_case_save_round_trips(self):
        j = desk_journey('customer_care', 'cs_lost', days=range(2, 40))
        tid = j.task['id']
        j.act('desk_reply', task=tid, reply='r0')
        j.act('desk_check', task=tid, check='courier')
        saved = json.loads(json.dumps(j.state))
        validate_state(saved)
        self.assertEqual(migrate_state(saved)['careers']['customer_care']['tasks'][0]['pending'], j.task['pending'])

    def test_tampered_desk_tasks_are_rejected(self):
        j = desk_journey('pharmacy', 'ph_stamp')
        tid = j.task['id']
        j.act('ask')
        j.act('desk_flag', task=tid, field='slip.patient', rule='ph_person')
        validate_state(j.state)
        cases = {
            'claim a find never marked': lambda t: t['found'].append('stamp'),
            'turn a wrong mark into a find': lambda t: t['marks'][0].update(result='found'),
            'rewrite a paper': lambda t: t['docs'][0]['fields'][0].update(value='X'),
            'erase a wrong mark count': lambda t: t.update(false_flags=0),
            'stamp without the work': lambda t: t.update(verdict='refer', status='completed', grade='perfect', result={}),
            'rename the case': lambda t: t.update(title='Khác'),
            'invent a check': lambda t: t['verified'].append('fridge'),
            'reply at the pharmacy': lambda t: t.update(reply='r0'),
        }
        for name, change in cases.items():
            s = copy.deepcopy(j.state)
            change(s['careers']['pharmacy']['tasks'][0])
            with self.assertRaises(GameError, msg=name):
                validate_state(s)

    def test_open_case_from_an_older_build_starts_again(self):
        j = desk_journey('pharmacy', 'ph_expired')
        tid = j.task['id']
        j.act('ask')
        j.act('desk_flag', task=tid, field='slip.until', rule='ph_date')
        s = copy.deepcopy(j.state)
        old = s['careers']['pharmacy']['tasks'][0]
        old['verdicts'] = old['verdicts'][:2]  # papers as an older build dealt them
        old['docs'][0]['fields'][0]['value'] = 'PK Cũ'
        with self.assertRaises(GameError):
            validate_state(s)
        s = migrate_state(s)
        validate_state(s)
        t = s['careers']['pharmacy']['tasks'][0]
        self.assertEqual((t['id'], t['known'], t['found'], t['status']), (tid, False, [], 'new'))
        self.assertEqual(t['verdicts'], j.task['verdicts'])
        self.assertEqual(s['careers']['pharmacy']['active_task'], tid)
        s, _ = apply_action(s, 'pharmacy', 'ask', {'task': tid})
        validate_state(s)

    def test_finished_case_from_an_older_build_stays_closed(self):
        j = desk_journey('pharmacy', 'ph_clean')
        tid = j.task['id']
        solve_desk(j)
        s = copy.deepcopy(j.state)
        s['careers']['pharmacy']['tasks'][0]['title'] = 'Tên hồ sơ cũ'
        money = s['careers']['pharmacy']['money']
        s = migrate_state(s)
        validate_state(s)
        t = s['careers']['pharmacy']['tasks'][0]
        self.assertEqual((t['id'], t['status'], t['result']), (tid, 'cancelled', None))
        self.assertEqual(s['careers']['pharmacy']['money'], money)
        # the slot stays taken: new work never deals the same case (and pay) again
        s, _ = apply_action(s, 'pharmacy', 'more_work', {})
        self.assertEqual(len({x['id'] for x in s['careers']['pharmacy']['tasks']}), 2)
        with self.assertRaises(GameError):
            apply_action(s, 'pharmacy', 'desk_decide', {'task': tid, 'verdict': 'give', 'confirm': True})

    def test_count_must_match_the_till(self):
        j = desk_journey('accounting', 'ac_cash')
        j.act('ask')
        s = copy.deepcopy(j.state)
        t = s['careers']['accounting']['tasks'][0]
        t['verified'].append('count')
        t['count'] = secrets(j)['cash'] + 1
        with self.assertRaises(GameError):
            validate_state(s)

    def test_desk_memory_is_validated(self):
        j = desk_journey('accounting', 'ac_clean')
        for change in (lambda d: d['flags'].append('made_up'), lambda d: d['stats'].pop('good'), lambda d: d.update(risk=-1),
                       lambda d: d['history'].append(dict(day=1, grade='great'))):
            s = copy.deepcopy(j.state)
            change(s['careers']['accounting']['ext']['data']['desk'])
            with self.assertRaises(GameError):
                validate_state(s)

    def test_classic_tasks_saved_in_desk_slots_still_load(self):
        for cid in CAREERS:
            day, slot = find_case(cid, dc.DAY_ONE[cid][0])
            j = Journey(cid, slot=0)
            old = make_task(cid, day, slot, 1, True)
            j.c['tasks'] = [old]
            j.c['active_task'] = old['id']
            validate_state(j.state)
            self.assertFalse(view(j).get('desk'))
            j.act('ask', task=old['id'])  # and it still plays at the classic counter
            validate_state(j.state)


class OldSaveUpgradeTests(unittest.TestCase):
    """Saves made before the wording clean-up still had 'mô phỏng', 'game', 'giả lập' in stored text."""
    OLD = {new: old for old, new in desk.LEGACY_TEXT.items()}

    def age(self, obj, keys):
        n = 0
        for k in keys:
            if obj.get(k) in self.OLD:
                obj[k] = self.OLD[obj[k]]
                n += 1
        return n

    def old_save(self):
        j = Journey('pharmacy')
        # an unfinished card game in the pharmacy corner…
        j.act('life_activity_start', spec='pharmacy-match', practice=True, replace=True)
        s = j.state
        aged = 0
        for cid in ('pharmacy', 'customer_care'):
            c = s['careers'][cid]
            c.update(day=1, open=True, started=True)
            c['tasks'] = [make_task(cid, 1, slot, 1, True) for slot in range(6)]
            c['active_task'] = c['tasks'][0]['id']
            for t in c['tasks']:
                aged += self.age(t, ('opening',))
                for ev in t.get('evidence') or []:
                    aged += self.age(ev, ('title', 'text'))
        # …with the old card label
        act = s['careers']['pharmacy']['life']['activity']
        for card in act['cards']:
            aged += self.age(card, ('label', 'value', 'hint'))
        for card in act['right']:
            aged += self.age(card, ('label', 'hint'))
        for cid in CAREERS:
            s['careers'][cid]['ext']['data'].pop('desk', None)  # before the desks existed
        self.assertGreaterEqual(aged, 6)  # the fixture really carries the old wording
        return json.loads(json.dumps(s))

    def test_the_fixture_is_an_old_save(self):
        s = self.old_save()
        text = json.dumps(s, ensure_ascii=False)
        for old in desk.LEGACY_TEXT:
            self.assertIn(old, text)
        with self.assertRaises(GameError):
            validate_state(s)

    def test_old_save_validates_and_is_upgraded(self):
        s = migrate_state(self.old_save())
        validate_state(s)
        text = json.dumps({cid: s['careers'][cid]['tasks'] for cid in ('pharmacy', 'customer_care')}, ensure_ascii=False)
        text += json.dumps(s['careers']['pharmacy']['life']['activity'], ensure_ascii=False)
        self.assertIsNone(META.search(text))
        for new in desk.LEGACY_TEXT.values():
            self.assertIn(new, text)
        for cid in CAREERS:
            self.assertEqual(s['careers'][cid]['ext']['data']['desk'], desk.fresh())
        # and it plays on at the classic counter
        s2, _ = apply_action(s, 'customer_care', 'ask', {'task': s['careers']['customer_care']['tasks'][0]['id']})
        s2, _ = apply_action(s2, 'pharmacy', 'ask', {'task': s2['careers']['pharmacy']['tasks'][0]['id']})
        validate_state(s2)

    def test_public_view_of_an_old_save_has_no_meta_words(self):
        for cid in ('pharmacy', 'customer_care'):
            s = self.old_save()
            s['current'] = cid
            tasks = public_state(s)['careers'][cid]['tasks']
            self.assertEqual(len(tasks), 6)
            for text in all_text(tasks):
                self.assertIsNone(META.search(text), text)


if __name__ == '__main__':
    unittest.main()
