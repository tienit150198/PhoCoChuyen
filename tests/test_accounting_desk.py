"""Bookkeeping desk: the till count and the fake note, duplicate and typo rows,
bank fees, periods, a payee-change scam, the hidden-revenue story and audits."""
import copy
import unittest

from game import desk, desk_content as dc
from game.engine import GameError, validate_state
from tests.desk_support import Journey, desk_journey, reports, review, roundtrip, secrets, solve_desk


def till(j):
    return secrets(j)['cash']


class TillTests(unittest.TestCase):
    def test_count_must_match_the_real_notes(self):
        j = desk_journey('accounting', 'ac_cash')
        tid = j.task['id']
        j.act('ask')
        with self.assertRaises(GameError):  # the till has its own counting action
            j.act('desk_check', task=tid, check='count')
        r = j.act('desk_count', task=tid, total=till(j) + 5)
        self.assertEqual(r['mark'], 'wrong')
        self.assertEqual(j.task['miscounts'], 1)
        self.assertNotIn('count', j.task['verified'])
        r = j.act('desk_count', task=tid, total=till(j))
        self.assertEqual(r['mark'], 'found')
        self.assertIn('count', j.task['verified'])
        with self.assertRaises(GameError):
            j.act('desk_count', task=tid, total=till(j))
        validate_state(j.state)

    def test_drawer_notes_add_up_to_the_till(self):
        j = desk_journey('accounting', 'ac_cash')
        self.assertEqual(sum(n['v'] for n in j.task['drawer'] if n['thread']), till(j))
        j.act('ask')
        view = j.task
        self.assertTrue(all(set(n) == {'id', 'v', 'thread'} for n in view['drawer']))

    def test_the_fake_note_must_be_set_aside(self):
        j = desk_journey('accounting', 'ac_cash', lambda c: any(i['id'] == 'fake' for i in c['issues']), days=range(6, 200))
        fake = [n for n in j.task['drawer'] if not n['thread']]
        self.assertEqual([n['v'] for n in fake], [50])
        j.act('ask')
        r = j.act('desk_count', task=j.task['id'], total=till(j) + 50)  # counted the fake note too
        self.assertEqual(r['mark'], 'wrong')
        self.assertIn('sợi bạc', r['message'])
        t = solve_desk(j)
        self.assertEqual((t['verdict'], t['grade']), ('minutes', 'perfect'))

    def test_counting_is_capped(self):
        j = desk_journey('accounting', 'ac_cash')
        j.act('ask')
        for _ in range(6):
            j.act('desk_count', task=j.task['id'], total=till(j) + 1)
        with self.assertRaises(GameError):
            j.act('desk_count', task=j.task['id'], total=till(j))
        # a stamp is still possible, just not a clean one
        v = next(k for k, g in secrets(j)['accept'].items() if g == 'best')
        j.act('desk_decide', task=j.task['id'], verdict=v, confirm=True)
        self.assertEqual(j.get(j.c['completed_ids'][-1])['grade'], 'good')

    def test_short_till_gets_minutes_not_pocket_money(self):
        j = desk_journey('accounting', 'ac_cash', lambda c: c['cover'] > 0)
        short = secrets(j)['cover']
        self.assertEqual(solve_desk(j)['verdict'], 'minutes')
        k = desk_journey('accounting', 'ac_cash', lambda c: c['cover'] > 0)
        money = k.c['money']
        t = solve_desk(k, verdict='cover')
        self.assertEqual(t['grade'], 'wrong')
        self.assertEqual(k.c['money'], money - short)
        self.assertTrue(any(x['amount'] == -short and x['category'] == 'cash_cover' for x in k.c['ops']['finance']['ledger']))
        validate_state(k.state)
        f = desk_journey('accounting', 'ac_cash', lambda c: c['cover'] > 0)
        self.assertEqual(solve_desk(f, verdict='force')['grade'], 'wrong')
        self.assertEqual(f.c['ext']['data']['desk']['risk'], 2)

    def test_count_only_exists_on_the_till(self):
        j = desk_journey('accounting', 'ac_dup')
        j.act('ask')
        with self.assertRaises(GameError):
            j.act('desk_count', task=j.task['id'], total=100)


class LedgerTests(unittest.TestCase):
    def test_duplicate_row_either_end_is_found(self):
        for ref in ('ledger.L2', 'ledger.L4'):
            j = desk_journey('accounting', 'ac_dup')
            j.act('ask')
            self.assertEqual(j.act('desk_flag', task=j.task['id'], field=ref, rule='ac_once')['mark'], 'found')

    def test_typo_matches_the_bill(self):
        t = solve_desk(desk_journey('accounting', 'ac_typo'))
        self.assertEqual((t['verdict'], t['grade']), ('adjust', 'perfect'))

    def test_bank_fee_follows_todays_bulletin(self):
        j = desk_journey('accounting', 'ac_fee')
        fee = dc.bank_fee(j.task['day'])
        rule = next(r for r in dc.bulletin('accounting', j.task['day'])['rules'] if r['id'] == 'ac_fee')
        self.assertIn(f'{fee} xu', rule['text'])
        self.assertIn(str(fee * 2), j.task['title'])
        self.assertEqual(solve_desk(j)['grade'], 'perfect')

    def test_fee_changes_are_announced(self):
        day = next(d for d in range(2, 30) if dc.bank_fee(d) != dc.bank_fee(d - 1))
        b = dc.bulletin('accounting', day)
        self.assertIn('ac_fee', [r['id'] for r in b['rules'] if r['new']])
        self.assertTrue(any('đổi phí' in n for n in b['notices']))

    def test_next_period_rent_and_the_weekly_close(self):
        j = desk_journey('accounting', 'ac_period')
        start, end = dc.period(j.task['day'])
        self.assertIn(f'kỳ {start}–{end}', secrets(j)['issues'][0]['why'])
        self.assertEqual(solve_desk(j)['grade'], 'perfect')
        close = Journey('accounting', slot=0, day=14)
        self.assertEqual(close.task['variant'], 'ac_close')
        self.assertEqual({i['id'] for i in secrets(close)['issues']}, {'period', 'fee'})
        self.assertEqual(solve_desk(close)['grade'], 'perfect')
        self.assertTrue(any('khóa sổ' in n for n in dc.bulletin('accounting', 14)['notices']))

    def test_private_bills_and_deposits(self):
        self.assertEqual(solve_desk(desk_journey('accounting', 'ac_private'))['verdict'], 'adjust')
        j = desk_journey('accounting', 'ac_deposit')
        self.assertEqual(solve_desk(j, verdict='post')['grade'], 'wrong')

    def test_supplier_letter_can_be_right_or_wrong(self):
        dup = desk_journey('accounting', 'ac_supplier', lambda c: bool(c['issues']))
        self.assertEqual(solve_desk(dup)['verdict'], 'claim')
        honest = desk_journey('accounting', 'ac_supplier', lambda c: not c['issues'])
        self.assertEqual(solve_desk(honest)['verdict'], 'reply')
        again = desk_journey('accounting', 'ac_supplier', lambda c: not c['issues'])
        self.assertEqual(solve_desk(again, verdict='claim')['grade'], 'wrong')


class PayeeTests(unittest.TestCase):
    def test_fake_payee_change(self):
        j = desk_journey('accounting', 'ac_payee', lambda c: bool(c['issues']))
        self.assertEqual(solve_desk(j)['verdict'], 'hold')
        k = desk_journey('accounting', 'ac_payee', lambda c: bool(c['issues']))
        t = solve_desk(k, verdict='pay')
        self.assertEqual(t['grade'], 'wrong')
        self.assertEqual(k.c['ext']['data']['desk']['risk'], 3)

    def test_real_payee_change_still_needs_the_call(self):
        pred = lambda c: not c['issues']
        j = desk_journey('accounting', 'ac_payee', pred, days=range(7, 300), slots=range(12))
        tid = j.task['id']
        j.act('ask')
        r = j.act('desk_decide', task=tid, verdict='pay', confirm=True)['desk_result']
        self.assertEqual(r['grade'], 'wrong')  # right answer, taken blind
        self.assertIn('chưa gọi xác minh', r['says'])
        self.assertIn('Làm trước khi', r['citation']['rule'])
        k = desk_journey('accounting', 'ac_payee', pred, days=range(7, 300), slots=range(12))
        t = solve_desk(k)
        self.assertEqual((t['verdict'], t['grade']), ('pay', 'perfect'))

    def test_payee_rule_from_day_four(self):
        self.assertNotIn('ac_payee', [r['id'] for r in dc.bulletin('accounting', 3)['rules']])
        self.assertIn('ac_payee', [r['id'] for r in dc.bulletin('accounting', 4)['rules']])


class CoHoaTests(unittest.TestCase):
    def test_the_hush_money_is_paid_and_remembered(self):
        j = Journey('accounting', slot=1, day=4)
        self.assertEqual(j.task['chapter'], 2)
        money = j.c['money']
        t = solve_desk(j, verdict='comply')
        self.assertEqual(t['grade'], 'wrong')
        self.assertEqual(j.c['money'], money + 20)
        self.assertEqual(j.c['ext']['data']['desk']['flags'], ['hoa_hid'])
        k = Journey('accounting', slot=1, day=4)
        solve_desk(k)
        self.assertEqual(k.c['ext']['data']['desk']['flags'], ['hoa_honest'])

    def test_the_second_counter_is_a_clean_till(self):
        j = Journey('accounting', slot=1, day=11)
        self.assertEqual(j.task['title'], 'Quầy thứ hai của cô Hoa')
        self.assertEqual(secrets(j)['issues'], [])
        self.assertEqual(solve_desk(j)['verdict'], 'close')


class AuditTests(unittest.TestCase):
    def test_internal_audit_day(self):
        j = Journey('accounting', slot=0, day=10)
        self.assertEqual(j.task['variant'], 'ac_audit')
        self.assertIn('ac_note', [r['id'] for r in dc.bulletin('accounting', 10)['rules']])
        t = solve_desk(j)
        self.assertEqual((t['verdict'], t['grade']), ('own', 'perfect'))

    def test_fake_note_rule_from_day_six(self):
        self.assertNotIn('ac_fake', [r['id'] for r in dc.bulletin('accounting', 5)['rules']])
        for day in range(1, 6):
            for slot in range(12):
                if dc.plan('accounting', day, slot) == 'ac_cash':
                    case, _, _ = dc.build('accounting', 'ac_cash', day, slot)
                    self.assertTrue(all(n['thread'] for n in case['notes']))


class ConsequenceTests(unittest.TestCase):
    def test_right_books_keep_five_stars(self):
        j = desk_journey('accounting', 'ac_dup')
        money = j.c['money']
        t = solve_desk(j)
        self.assertFalse(t.get('slips'))
        self.assertEqual(review(j, t['id'])['stars'], 5)
        self.assertEqual(j.c['money'], money + desk.pay_for(t, 'perfect'))

    def test_missed_duplicate_is_named_in_the_review(self):
        j = desk_journey('accounting', 'ac_dup')
        t = solve_desk(j, verdict='post')
        post = review(j, t['id'])
        self.assertLessEqual(post['stars'], 3)
        self.assertIn('ghi hai lần', post['text'])
        self.assertIn(t['reaction']['kind'], ('accept', 'grumble', 'discount', 'refund', 'walkout'))
        roundtrip(j)

    def test_forcing_the_book_to_match_the_till_is_reported(self):
        j = desk_journey('accounting', 'ac_cash', lambda c: bool(c['issues']))
        t = solve_desk(j, verdict='force')
        self.assertEqual(t['slips'][0]['sev'], 3)
        self.assertLessEqual(review(j, t['id'])['stars'], 2)
        self.assertIn('sửa sổ quỹ cho khớp két', review(j, t['id'])['text'])
        self.assertTrue(reports(j, t['id']))
        roundtrip(j)

    def test_severity_scales_the_stars(self):
        small = desk_journey('accounting', 'ac_clean')
        t1 = solve_desk(small, verdict='hold')       # sev 1
        clear = desk_journey('accounting', 'ac_clean')
        t2 = solve_desk(clear, verdict='adjust')     # sev 2
        big = desk_journey('accounting', 'ac_payee', lambda c: bool(c['issues']))
        t3 = solve_desk(big, verdict='pay')          # sev 3: money to a fake account
        stars = [review(x, t['id'])['stars'] for x, t in ((small, t1), (clear, t2), (big, t3))]
        self.assertEqual(stars, [4, 3, 2])

    def test_right_stamp_taken_blind_is_a_slip(self):
        j = desk_journey('accounting', 'ac_payee', lambda c: not c['issues'], days=range(6, 90))
        tid = j.task['id']
        j.act('ask')
        j.act('desk_decide', task=tid, verdict='pay', confirm=True)
        t = j.get(tid)
        self.assertEqual(t['slips'][0]['code'], 'blind_pay')
        self.assertLessEqual(review(j, tid)['stars'], 3)
        roundtrip(j)


if __name__ == '__main__':
    unittest.main()
