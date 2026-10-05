"""🏦 Ngân hàng Phố (game/bank.py): account, savings, credit card, loans, credit score."""
import copy
import re
import unittest
from unittest.mock import patch

from game import bank as bk
from game import journey as jr
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state


def story(wallet=500, seed=4242):
    s = new_state()
    jr.enable_story(s, seed)
    j = s['journey']
    j['gender'] = 'female'
    j['wallet'] = wallet
    j['stats']['max_wallet'] = max(wallet, j['stats']['max_wallet'])
    validate_state(s)
    return s


def act(s, name, **p):
    """Through the engine like the browser (a copy: a failure leaves `s` untouched)."""
    return apply_action(s, None, name, p)


def B(s):
    return s['journey']['bank']


def days(s, n=1, salary=0):
    """Close `n` life days the way end_day does: salary lands, life_day moves, the bank catches up."""
    notes = []
    for _ in range(n):
        j = s['journey']
        if salary:
            jr._wallet(j, salary, 'salary', 'Lương ngày')
        j['life_day'] += 1
        notes += bk.on_life_day(s)
    validate_state(s)
    return notes


def opened(wallet=500, deposit=0, income_days=0, salary=60):
    s = story(wallet)
    s, _ = act(s, 'jr_bk_open')
    if deposit:
        s, _ = act(s, 'jr_bk_deposit', amount=deposit)
    if income_days:
        days(s, income_days, salary)
    return s


def with_card(income_days=14, salary=60, score=None, **kw):
    s = opened(income_days=income_days, salary=salary, **kw)
    if score is not None:
        B(s)['score'] = score
    s, r = act(s, 'jr_bk_card_apply', confirm=True)
    assert r.get('approved'), r['message']
    return s


def next_statement(s):
    """Advance to the next card statement day and return that statement."""
    for _ in range(30):
        days(s)
        st = B(s)['card']['stmt']
        if st and st['day'] == s['journey']['life_day']:
            return st
    raise AssertionError('no statement')


class Account(unittest.TestCase):
    def test_old_save_loads_with_an_empty_bank(self):
        s = story()
        self.assertNotIn('bank', s['journey'])
        view = public_state(s)['journey']['bank']
        self.assertFalse(view['open'])
        self.assertTrue(view['story'])
        old = copy.deepcopy(s)
        old.pop('check', None)
        validate_state(migrate_state(old))
        bk.validate(s)
        self.assertEqual(bk.on_life_day(s), [])

    def test_story_only(self):
        s = new_state()
        with self.assertRaises(GameError) as cm:
            act(s, 'jr_bk_open')
        self.assertEqual(cm.exception.code, 'story_only')
        self.assertFalse(bk.public(s)['story'])

    def test_open_deposit_withdraw_with_running_balance(self):
        s = opened(wallet=200)
        self.assertEqual(len(B(s)['no']), 10)
        with self.assertRaises(GameError):
            act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=150)
        self.assertEqual((B(s)['balance'], s['journey']['wallet']), (150, 50))
        self.assertEqual(s['journey']['history'][-1]['kind'], 'bank')
        s, r = act(s, 'jr_bk_withdraw', amount=40, atm='other')
        self.assertEqual((B(s)['balance'], s['journey']['wallet']), (150 - 40 - bk.ATM_OTHER_FEE, 90))
        self.assertIn('phí', r['message'])
        s, _ = act(s, 'jr_bk_withdraw', amount=9)
        rows = [(r['amt'], r['bal']) for r in B(s)['log'] if r['acc'] == 'acc']
        self.assertEqual(rows, [(150, 150), (-40, 110), (-1, 109), (-9, 100)])
        with self.assertRaises(GameError):
            act(s, 'jr_bk_withdraw', amount=101)
        with self.assertRaises(GameError):
            act(s, 'jr_bk_deposit', amount=100)
        with self.assertRaises(GameError):
            act(s, 'jr_bk_deposit', amount=0)

    def test_sweep_covers_a_negative_wallet(self):
        s = opened(wallet=100, deposit=100)
        s['journey']['wallet'] = -30
        notes = days(s)
        self.assertEqual((s['journey']['wallet'], B(s)['balance']), (0, 70))
        self.assertTrue(any('bù' in n for n in notes))
        s, _ = act(s, 'jr_bk_settings', sweep=False)
        s['journey']['wallet'] = -5
        days(s)
        self.assertEqual(s['journey']['wallet'], -5)


class Savings(unittest.TestCase):
    def test_demand_interest_credited_daily(self):
        s = opened(wallet=3000, deposit=2000)
        s, _ = act(s, 'jr_bk_save', amount=2000, term=0)
        days(s, 3)
        self.assertEqual(B(s)['demand'], 2003)   # 0,05 %/ngày of 2000 = 1 xu a day
        s2 = opened(wallet=100)
        s2, _ = act(s2, 'jr_bk_save', amount=100, term=0, src='cash')
        days(s2, 19)
        self.assertEqual(B(s2)['demand'], 100)
        days(s2, 1)
        self.assertEqual(B(s2)['demand'], 101)   # fractions wait in `pend` until they make a whole xu
        s2, _ = act(s2, 'jr_bk_unsave', id='demand', amount=101)
        self.assertEqual((B(s2)['demand'], B(s2)['balance']), (0, 101))

    def test_term_deposit_matures_with_interest(self):
        s = opened(wallet=1000, deposit=1000)
        s, r = act(s, 'jr_bk_save', amount=1000, term=7)
        self.assertIn('7 xu', r['message'])   # 1000 × 6 %/năm × 7/60 = 7
        self.assertIn('6%/năm', r['message'])
        t = B(s)['terms'][0]
        self.assertEqual(t['due'], s['journey']['life_day'] + 7)
        days(s, 6)
        self.assertEqual(B(s)['balance'], 0)
        notes = days(s, 1)
        self.assertEqual((B(s)['balance'], B(s)['terms']), (1007, []))
        self.assertTrue(any('đáo hạn' in n for n in notes))

    def test_early_withdrawal_falls_back_to_demand_rate(self):
        s = opened(wallet=3000, deposit=3000)
        s, _ = act(s, 'jr_bk_save', amount=2000, term=30)
        days(s, 10)
        tid = B(s)['terms'][0]['id']
        with self.assertRaises(GameError):
            act(s, 'jr_bk_unsave', id=tid)
        s, r = act(s, 'jr_bk_unsave', id=tid, confirm=True)
        self.assertEqual(B(s)['balance'], 1000 + 2000 + 2000 * bk.DEMAND_BP * 10 // 10000)
        self.assertIn('trước hạn', r['message'])

    def test_minimum_and_count(self):
        s = opened(wallet=1000, deposit=1000)
        with self.assertRaises(GameError):
            act(s, 'jr_bk_save', amount=bk.SAVE_MIN - 1, term=7)
        for _ in range(bk.TERMS_MAX):
            s, _ = act(s, 'jr_bk_save', amount=20, term=15)
        with self.assertRaises(GameError):
            act(s, 'jr_bk_save', amount=20, term=15)
        with self.assertRaises(GameError):   # 14 ngày only lives on in sổ opened before 0.9.5
            act(opened(wallet=100, deposit=100), 'jr_bk_save', amount=20, term=14)


class Card(unittest.TestCase):
    def test_no_income_is_declined_but_the_inquiry_counts(self):
        s = opened()
        s, r = act(s, 'jr_bk_card_apply', confirm=True)
        self.assertFalse(r['approved'])
        self.assertIsNone(B(s)['card'])
        self.assertEqual(B(s)['score'], bk.SCORE_START + bk.DELTA['inquiry'])

    def test_limit_follows_income_and_score(self):
        low = with_card(income_days=14, salary=60)           # 60/ngày × 7 × 0,6 (score < 670)
        self.assertEqual(B(low)['card']['limit'], 250)
        high = with_card(income_days=14, salary=60, score=760)  # × 1,5
        self.assertEqual(B(high)['card']['limit'], 630)
        s = opened(income_days=14)
        B(s)['score'] = 560
        s, r = act(s, 'jr_bk_card_apply', confirm=True)
        self.assertFalse(r['approved'])
        self.assertIn('Điểm tín dụng', r['message'])

    def test_many_applications_are_declined(self):
        s = opened()
        for _ in range(bk.INQ_MANY):
            s, r = act(s, 'jr_bk_card_apply', confirm=True)
        days(s, 14, 60)
        B(s)['inq'] = [s['journey']['life_day']] * bk.INQ_MANY
        before = B(s)['score']
        s, r = act(s, 'jr_bk_card_apply', confirm=True)
        self.assertFalse(r['approved'])
        self.assertIn('nhiều hồ sơ', r['message'])
        day = s['journey']['life_day']
        self.assertIn(f'Nộp lại được từ Ngày {day + bk.INQ_WINDOW} (còn {bk.INQ_WINDOW} ngày)', r['message'])
        self.assertEqual(B(s)['score'], before)   # the bank's own filter: no new inquiry

    def test_pay_helper_cash_card_auto(self):
        s = with_card(wallet=30)
        s['journey']['wallet'] = 30
        self.assertEqual(bk.pay(s, 20, 'Sách', method='cash', kind='study')['method'], 'cash')
        self.assertEqual(s['journey']['wallet'], 10)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'study')
        out = bk.pay(s, 40, 'Áo mới')   # auto: the wallet is short, the card pays
        self.assertEqual(out['method'], 'card')
        self.assertEqual((B(s)['card']['bal'], s['journey']['wallet']), (40, 10))
        self.assertEqual(B(s)['ting'], 40)
        r = {}
        bk.on_life_day(s, r)
        self.assertEqual(r['card_swipe'], 40)
        self.assertNotIn('ting', B(s))
        with self.assertRaises(GameError) as cm:
            bk.pay(s, 10**4, 'Xe máy', method='card')
        self.assertEqual(cm.exception.code, 'card_declined')
        with self.assertRaises(GameError) as cm:
            bk.pay(s, 11, 'Bánh', method='cash', short='Ví chưa đủ tiền bánh.')
        self.assertEqual(cm.exception.message, 'Ví chưa đủ tiền bánh.')
        B(s)['pref'] = 'card'
        self.assertEqual(bk.pay(s, 5, 'Nước')['method'], 'card')
        B(s)['pref'] = 'cash'
        with self.assertRaises(GameError):
            bk.pay(s, 50, 'Giày')   # cash only, the wallet is short
        validate_state(s)

    def test_pay_without_a_bank_is_plain_cash(self):
        s = story(wallet=50)
        self.assertEqual(bk.pay(s, 30, 'Học phí', kind='study')['method'], 'cash')
        self.assertEqual(s['journey']['wallet'], 20)
        with self.assertRaises(GameError):
            bk.pay(s, 30, 'Học phí')

    def statement(self, s):
        return next_statement(s)

    def test_statement_minimum_and_due(self):
        s = with_card()
        bk.pay(s, 120, 'Tủ lạnh', method='card')
        st = self.statement(s)
        self.assertEqual((st['amount'], st['min'], st['due']), (120, 12, st['day'] + bk.CARD_GRACE))
        view = bk.public(s)['card']
        self.assertEqual(view['stmt']['min_left'], 12)

    def test_paying_in_full_costs_no_interest(self):
        s = with_card(deposit=300)
        bk.pay(s, 100, 'Quạt', method='card')
        self.statement(s)
        before = B(s)['score']
        s, _ = act(s, 'jr_bk_card_pay', what='stmt', src='acc')
        days(s, bk.CARD_GRACE)
        self.assertEqual(B(s)['score'], before + bk.DELTA['card_full'])
        st = self.statement(s)
        self.assertEqual((B(s)['card']['bal'], st['amount']), (0, 0))
        self.assertEqual(B(s)['stats']['interest_out'], 0)

    def test_carrying_a_balance_pays_interest(self):
        s = with_card(deposit=300)
        bk.pay(s, 200, 'Tivi', method='card')
        self.statement(s)
        s, _ = act(s, 'jr_bk_card_pay', what='min', src='acc')   # 20
        days(s, bk.CARD_GRACE)
        st = self.statement(s)
        interest = -(-180 * bk.CARD_BP * bk.CARD_CYCLE // 10000)  # 6,3 → 7
        self.assertEqual(st['amount'], 180 + interest)
        self.assertEqual(B(s)['stats']['interest_out'], interest)

    def test_missing_the_minimum(self):
        s = with_card()
        bk.pay(s, 100, 'Điện thoại', method='card')
        self.statement(s)
        before = B(s)['score']
        notes = days(s, bk.CARD_GRACE)
        c = B(s)['card']
        self.assertEqual((c['past_due'], c['bal']), (10, 100 + bk.CARD_LATE_FEE))
        self.assertLess(B(s)['score'], before)
        self.assertTrue(any('chưa được thanh toán' in n for n in notes))
        self.assertIn('trễ hạn', bk.card_usable(s))
        with self.assertRaises(GameError):
            bk.pay(s, 5, 'Nước', method='card')
        with self.assertRaises(GameError):   # overdue: no new credit
            act(s, 'jr_bk_card_cash', amount=10)
        s, _ = act(s, 'jr_bk_card_pay', what='min', src='cash')
        self.assertEqual(B(s)['card']['past_due'], 0)
        self.assertIsNone(bk.card_usable(s))
        # The next statement's minimum still carries the missed part only if it was not paid.
        st = self.statement(s)
        self.assertEqual(st['min'], max(-(-st['amount'] * 10 // 100), 10))

    def test_autopay_minimum_from_the_account(self):
        s = with_card(deposit=100)
        s, _ = act(s, 'jr_bk_card_autopay', mode='min')
        bk.pay(s, 150, 'Lò vi sóng', method='card')
        self.statement(s)
        days(s, bk.CARD_GRACE)
        self.assertEqual((B(s)['card']['past_due'], B(s)['balance'], B(s)['card']['bal']), (0, 85, 135))

    def test_cash_advance(self):
        s = with_card(wallet=0)
        s['journey']['wallet'] = 0
        limit = B(s)['card']['limit']
        s, r = act(s, 'jr_bk_card_cash', amount=50)
        fee = max(bk.CASH_FEE_MIN, -(-50 * bk.CASH_FEE_PCT // 100))
        self.assertEqual((s['journey']['wallet'], B(s)['card']['bal']), (50, 50 + fee))
        with self.assertRaises(GameError):
            act(s, 'jr_bk_card_cash', amount=limit)   # over half the limit
        start = B(s)['card']['cash_day']
        st = self.statement(s)
        days_out = st['day'] - start
        self.assertEqual(st['amount'], 50 + fee + -(-50 * bk.CARD_BP * days_out // 10000))
        self.assertEqual(B(s)['card']['cash'], 0)

    def test_close_card(self):
        s = with_card()
        bk.pay(s, 10, 'Kẹo', method='card')
        with self.assertRaises(GameError):
            act(s, 'jr_bk_card_close', confirm=True)
        s, _ = act(s, 'jr_bk_card_pay', what='all', src='cash')
        s, _ = act(s, 'jr_bk_card_close', confirm=True)
        self.assertIsNone(B(s)['card'])


class Loans(unittest.TestCase):
    def test_schedule_math(self):
        for p, kind, term in ((300, 'personal', 28), (1000, 'shop', 21), (57, 'personal', 14), (5000, 'personal', 28)):
            q = bk.quote(p, kind, term, 10)
            rows = q['rows']
            self.assertEqual(len(rows), term // 7)
            self.assertEqual(sum(r['principal'] for r in rows), p)
            self.assertEqual([r['due'] for r in rows], [10 + 7 * (i + 1) for i in range(len(rows))])
            self.assertTrue(all(r['amount'] <= q['installment'] for r in rows))
            self.assertEqual(q['total'], p + q['interest'])
            self.assertFalse(bk._fits(p, bk.LOAN_BP[kind], len(rows), q['installment'] - 1))   # the smallest installment
        self.assertEqual(bk.quote(300, 'personal', 28)['interest'], 30)

    def apply(self, s, amount=100, term=28, kind='personal', **kw):
        q = bk.quote(amount, kind, term)
        return act(s, 'jr_bk_loan_apply', kind=kind, amount=amount, term=term, total_interest=q['interest'], confirm=True, **kw)

    def test_signing_needs_the_quote_seen(self):
        s = opened(income_days=14)
        with self.assertRaises(GameError) as cm:
            act(s, 'jr_bk_loan_apply', kind='personal', amount=100, term=28, total_interest=0, confirm=True)
        self.assertEqual(cm.exception.code, 'stale_quote')
        with self.assertRaises(GameError):
            act(s, 'jr_bk_loan_apply', kind='personal', amount=100, term=28, total_interest=bk.quote(100, 'personal', 28)['interest'])

    def test_disburse_and_auto_debit(self):
        s = opened(income_days=14, salary=60)
        s, r = self.apply(s, 100)
        self.assertTrue(r['approved'], r['message'])
        ln = B(s)['loans'][0]
        self.assertIn(f'kỳ đầu Ngày {ln["rows"][0]["due"]} (còn {bk.LOAN_PERIOD} ngày)', r['message'])
        self.assertNotIn('ngày sống', r['message'])
        self.assertEqual(B(s)['balance'], 100)
        first = ln['rows'][0]
        days(s, 6)
        self.assertEqual(first['paid'], 0)
        days(s, 1)
        ln = B(s)['loans'][0]
        self.assertEqual(ln['rows'][0]['paid'], ln['rows'][0]['amount'])
        self.assertEqual(B(s)['balance'], 100 - ln['rows'][0]['amount'])
        today = [(r['why'], r['delta']) for r in B(s)['score_log'] if r['day'] == s['journey']['life_day']]
        self.assertIn(('loan_ok', bk.DELTA['loan_ok']), today)
        days(s, 21)
        self.assertEqual(B(s)['loans'], [])
        self.assertEqual(B(s)['stats']['loans_closed'], 1)

    def test_offer_limits_and_dti(self):
        s = opened(income_days=14, salary=60)
        off = bk.loan_offer(s, B(s), 'personal')
        self.assertEqual(off['max'], 60 * 14 * 3 // 5 // 10 * 10)
        s, r = self.apply(s, off['max'] + 10)
        self.assertFalse(r['approved'])
        s, r = self.apply(s, 500, term=14)   # 2 installments of ~256 > 40 % of 420 a week
        self.assertFalse(r['approved'])
        self.assertIn('%', r['message'])

    def test_early_repayment_fee(self):
        s = opened(wallet=500, income_days=14, salary=60)
        s, _ = self.apply(s, 200)
        days(s, 3)
        off = bk.public(s)['loans'][0]['payoff']
        self.assertEqual(off['principal'], 200)
        self.assertEqual(off['fee'], max(bk.EARLY_FEE_MIN, -(-200 * bk.EARLY_FEE_PCT // 100)))
        self.assertEqual(off['interest'], -(-200 * 400 * 3 // (10000 * 7)))
        with self.assertRaises(GameError):   # the account alone is short
            act(s, 'jr_bk_loan_close', id=B(s)['loans'][0]['id'], src='acc', confirm=True)
        wallet = s['journey']['wallet']
        s, r = act(s, 'jr_bk_loan_close', id=B(s)['loans'][0]['id'], src='cash', confirm=True)
        self.assertEqual(B(s)['loans'], [])
        self.assertEqual(s['journey']['wallet'], wallet - off['total'])
        self.assertIn('tiết kiệm được', r['message'])

    def test_missed_installments_penalty_calls_and_bad_debt(self):
        s = opened(wallet=0, income_days=14, salary=60)
        s, _ = self.apply(s, 150)
        s, _ = act(s, 'jr_bk_card_apply', confirm=True)
        s, _ = act(s, 'jr_bk_withdraw', amount=150)
        s['journey']['wallet'] = 0
        before = B(s)['score']
        notes = days(s, 7)
        row = B(s)['loans'][0]['rows'][0]
        self.assertTrue(row['late'])
        self.assertEqual(row['fee'], max(bk.LOAN_LATE_MIN, -(-(row['amount'] - row['fee']) * bk.LOAN_LATE_PCT // 100)))
        self.assertLess(B(s)['score'], before)
        self.assertTrue(any('chưa được thanh toán' in n for n in notes))
        notes = days(s, 2)
        self.assertTrue(any('Nhân viên thu hồi nợ gọi' in n for n in notes))
        call = [m for m in B(s)['inbox'] if m['kind'] == 'call'][0]['text']
        for word in ('đe dọa', 'công an', 'hàng xóm', 'gia đình'):
            self.assertNotIn(word, call)
        # A third miss (second installment + the card) → nợ xấu.
        with patch.object(bk, 'BAD_MISSES', 2):
            days(s, 5)
        self.assertGreater(B(s)['bad_until'], s['journey']['life_day'])
        self.assertIn('nợ xấu', bk.card_usable(s))
        s, r = self.apply(s, 60, term=14)
        self.assertFalse(r['approved'])
        self.assertIn('nợ xấu', r['message'])
        # Paying everything and waiting clears the flag.
        s['journey']['wallet'] = 5000
        lid = B(s)['loans'][0]['id']
        s, _ = act(s, 'jr_bk_loan_close', id=lid, src='cash', confirm=True)
        if B(s)['card']['past_due']:
            s, _ = act(s, 'jr_bk_card_pay', what='all', src='cash')
        days(s, bk.BAD_DAYS)
        self.assertEqual(B(s)['bad_until'], 0)

    def test_pay_overdue_by_hand(self):
        s = opened(wallet=0, income_days=14, salary=60)
        s, _ = self.apply(s, 100)
        s, _ = act(s, 'jr_bk_withdraw', amount=100)
        s['journey']['wallet'] = 0
        days(s, 7)
        s['journey']['wallet'] = 200
        lid = B(s)['loans'][0]['id']
        s, _ = act(s, 'jr_bk_loan_pay', id=lid, src='cash')
        row = B(s)['loans'][0]['rows'][0]
        self.assertEqual(row['paid'], row['amount'])
        self.assertFalse(bk._overdue(B(s), s['journey']['life_day']))

    def test_shop_loan_goes_into_the_fund(self):
        s = opened(income_days=14, salary=60)
        cid = 'milk_tea'
        s['careers'][cid]['started'] = True
        self.assertIn(cid, bk.owned_places(s))
        fund = s['careers'][cid]['money']
        s, r = self.apply(s, 200, term=21, kind='shop', career=cid)
        self.assertTrue(r['approved'], r['message'])
        self.assertEqual(s['careers'][cid]['money'], fund + 200)
        self.assertEqual(B(s)['balance'], 0)
        self.assertEqual(s['careers'][cid]['ops']['finance']['ledger'][-1]['category'], 'owner_capital')
        self.assertEqual(bk.income(s)['total'], 14 * 60 - 200)   # drawing the loan back out is not income


class Score(unittest.TestCase):
    def test_weekly_income_and_age_raise_the_score(self):
        s = opened()
        start = B(s)['score']
        days(s, 7, salary=40)
        self.assertEqual(B(s)['score'], start + bk.DELTA['income'] + bk.DELTA['age'])
        days(s, 7)   # no income this week: only the age point
        self.assertEqual(B(s)['score'], start + bk.DELTA['income'] + 2 * bk.DELTA['age'])
        self.assertEqual(bk.public(s)['score']['log'][0]['why'], 'age')

    def test_high_utilization_lowers_the_score(self):
        s = with_card()
        bk.pay(s, B(s)['card']['limit'], 'Máy giặt', method='card')
        next_statement(s)
        self.assertIn(('util_high', bk.DELTA['util_high']), [(r['why'], r['delta']) for r in B(s)['score_log']])
        s = with_card()
        bk.pay(s, 10, 'Bút', method='card')
        next_statement(s)
        self.assertIn('util_low', [r['why'] for r in B(s)['score_log']])

    def test_score_is_clamped_and_banded(self):
        s = opened()
        B(s)['score'] = 845
        bk._score(B(s), 1, 'loan_done')
        self.assertEqual(B(s)['score'], bk.SCORE_MAX)
        self.assertEqual(bk.public(s)['score']['band'], 'Rất tốt')
        B(s)['score'] = 305
        bk._score(B(s), 1, 'bad')
        self.assertEqual(B(s)['score'], bk.SCORE_MIN)


class Tick(unittest.TestCase):
    def test_ticks_are_idempotent(self):
        s = with_card(deposit=300)
        s, _ = act(s, 'jr_bk_save', amount=100, term=7)
        bk.pay(s, 80, 'Bàn', method='card')
        s['journey']['life_day'] += 10
        bk.on_life_day(s)
        once = copy.deepcopy(B(s))
        bk.on_life_day(s)
        bk.on_life_day(s)
        self.assertEqual(B(s), once)
        validate_state(s)

    def test_journey_after_runs_the_tick(self):
        s = opened(wallet=3000, deposit=2000)
        s, _ = act(s, 'jr_bk_save', amount=2000, term=0)
        s['journey']['life_day'] += 2
        s, r = act(s, 'jr_bk_read')
        self.assertEqual(B(s)['day'], s['journey']['life_day'])
        self.assertEqual(B(s)['demand'], 2002)

    def test_the_same_seed_gives_the_same_bank(self):
        a, b = opened(income_days=14), opened(income_days=14)
        self.assertEqual(B(a)['no'], B(b)['no'])
        self.assertEqual(public_state(a)['journey']['bank'], public_state(b)['journey']['bank'])


class Validate(unittest.TestCase):
    def test_corrupt_bank_is_rejected(self):
        s = with_card()
        for path, value in ((('balance',), -1), (('score',), 900), (('card', 'limit'), 10), (('pref',), 'gold'),
                            (('log',), [dict(id='g1', day=1, acc='x', text='a', amt=1, bal=1)]), (('day',), 10**6)):
            t = copy.deepcopy(s)
            box = t['journey']['bank']
            for k in path[:-1]:
                box = box[k]
            box[path[-1]] = value
            with self.assertRaises(GameError):
                validate_state(t)
        t = copy.deepcopy(s)
        t['journey']['bank']['extra'] = 1
        with self.assertRaises(GameError):
            validate_state(t)


class Wiring(unittest.TestCase):
    def test_certificate_tuition_by_card(self):
        from game import certificates as ct
        s = with_card(wallet=0)
        s['journey']['wallet'] = 0
        gid = next(iter(ct.INDEX))
        s, r = act(s, 'jr_cert_enrol', cert=gid, mode='class', pay='card')
        cost = s['journey']['study']['fee']
        if cost:
            self.assertEqual(B(s)['card']['bal'], cost)
            self.assertIn('quẹt thẻ', r['message'])
            self.assertEqual(r.get('card_swipe'), cost)

    def test_back_door_by_card(self):
        from tests import test_certificates as tc
        from game import employment as emp
        tc.here(tc.CID)
        s, _ = tc.interview(tc.story(wallet=0))
        s, _ = act(s, 'jr_bk_open')
        days(s, 14, 60)
        s, r = act(s, 'jr_bk_card_apply', confirm=True)
        self.assertTrue(r['approved'], r['message'])
        s['journey']['wallet'] = 0
        fee = emp.backdoor_fee(tc.post_of(tc.CID, tc.POST))
        s, r = apply_action(s, tc.CID, 'job_backdoor', dict(confirm=True, pay='card'))
        self.assertEqual(s['careers'][tc.CID]['job']['status'], 'hired')
        self.assertEqual((B(s)['card']['bal'], s['journey']['wallet']), (fee, 0))

    def test_end_day_runs_the_bank_tick(self):
        from tests import test_certificates as tc
        s = opened(wallet=3000, deposit=2000)
        s, _ = act(s, 'jr_bk_save', amount=2000, term=0)
        day = s['journey']['life_day']
        s = tc.next_life_day(s)
        self.assertEqual(s['journey']['life_day'], day + 1)
        self.assertEqual((B(s)['day'], B(s)['demand']), (day + 1, 2001))

    def test_ring_and_lunch_by_card_through_marriage_spend(self):
        from game import marriage as mr
        s = with_card()
        mr._box(s)
        wallet, bal = s['journey']['wallet'], B(s)['card']['bal']
        B(s)['pref'] = 'card'
        eff = mr._effect('ring:test:1', 'sid', 'wallet', -30, 'Mua nhẫn bạc')
        self.assertTrue(mr._can_spend(s, 30))
        self.assertTrue(mr._spend(s, eff))
        self.assertEqual((s['journey']['wallet'], B(s)['card']['bal']), (wallet, bal + 30))
        self.assertNotIn('ting', B(s))
        self.assertFalse(mr._spend(s, eff))                       # replayed effect: no second charge
        self.assertEqual(B(s)['card']['bal'], bal + 30)
        mr._spend(s, mr._effect('lunch:test:1', 'sid', 'wallet', -5, 'Cơm trưa'), 'cash')
        self.assertEqual((s['journey']['wallet'], B(s)['card']['bal']), (wallet - 5, bal + 30))
        s['journey']['wallet'] = 0                                   # no cash: auto falls back to the card
        B(s)['pref'] = 'auto'
        self.assertTrue(mr._can_spend(s, 20))
        self.assertFalse(mr._can_spend(s, 20, 'cash'))
        mr._spend(s, mr._effect('dep:test:a', 'sid', 'wallet', -20, 'Đặt cọc tiệc cưới'))
        self.assertEqual((s['journey']['wallet'], B(s)['card']['bal']), (0, bal + 50))
        validate_state(s)
        plain = story()                                              # no bank: exactly the old wallet path
        mr._box(plain)
        self.assertFalse(mr._can_spend(plain, 10 ** 6))
        mr._spend(plain, mr._effect('ring:test:2', 'sid', 'wallet', -30, 'Mua nhẫn'))
        self.assertEqual(plain['journey']['wallet'], 470)

    def test_joint_card_through_the_marriage_helper(self):
        try:
            from game import couple as cp
        except ImportError:
            self.skipTest('game/couple.py is absent')
        if not hasattr(cp, 'joint_account') or not hasattr(cp, 'joint_spend'):
            self.skipTest('joint card helpers are absent')
        s = opened()
        fund = dict(id=1, balance=100, members=[], history=[], daily_left=60)
        spent = []
        with patch.object(cp, 'joint_account', return_value=fund), \
                patch.object(cp, 'joint_spend', side_effect=lambda st, amount, label, ref: spent.append((amount, label, ref)) or {}):
            self.assertTrue(bk.can_pay(s, 50, 'joint'))
            self.assertTrue(bk.can_pay(s, 70, 'joint'))    # no daily quota
            self.assertFalse(bk.can_pay(s, 101, 'joint'))  # actual balance
            out = bk.pay(s, 50, 'Đi chợ', method='joint')
            self.assertEqual(out['method'], 'joint')
            self.assertEqual(spent[0][0], 50)
            with self.assertRaises(GameError) as cm:
                bk.pay(s, 101, 'Tủ', method='joint')
            self.assertEqual(cm.exception.code, 'card_declined')
            B(s)['pref'] = 'joint'
            again = copy.deepcopy(s)
            self.assertEqual(bk.pay(s, 10, 'Rau')['method'], 'joint')
            self.assertEqual(bk.pay(again, 10, 'Rau')['method'], 'joint')   # a retried command: same ref
            self.assertEqual(bk.pay(s, 10, 'Rau')['method'], 'joint')       # a new purchase: new ref
            refs = [r for _, _, r in spent]
            self.assertEqual(refs[1], refs[2])
            self.assertEqual(len({refs[0], refs[1], refs[3]}), 3)
            self.assertTrue(all(re.fullmatch(r'[A-Za-z0-9:_\-]{1,40}', r) for r in refs))
            # joint_spend refuses under the store write lock ('busy'): automatic choice pays another way.
            with patch.object(cp, 'joint_spend', side_effect=GameError('Quỹ chung đang bận.', 'busy')):
                self.assertEqual(bk.pay(s, 10, 'Rau')['method'], 'cash')
                with self.assertRaises(GameError):
                    bk.pay(s, 10, 'Rau', method='joint')
            # Inside a marriage/couple transaction: cash or card only, the fund is never looked up.
            n = len(spent)
            s['journey']['wallet'] = 0
            self.assertFalse(bk.can_pay(s, 10, 'joint', no_joint=True))
            with self.assertRaises(GameError):
                bk.pay(s, 10, 'Nhẫn', method='joint', no_joint=True)
            self.assertEqual(len(spent), n)
        self.assertIsNone(bk.joint(s))   # no database bound in unit tests


if __name__ == '__main__':
    unittest.main()
