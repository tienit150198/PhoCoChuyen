"""🏦 Ngân hàng Phố, phần thêm 22/10 (game/bank_plus.py): the 7-day rule for credit, the card's full limit, 🐷 savings tiers
(feedback #480) and 📦 vay nhập hàng / quẹt thẻ at the restock point (feedback #481), and saves crossing to 2.5.2.4."""
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import bank as bk
from game import bank_plus as bp
from game import fair_bm, wealth
from game import quay_business as qb
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from tests.test_bank import B, act, days, next_statement, opened, story, with_card
from tests.test_inventory_flow import empty, set_money
from tests.test_quay import ST, opened as quay_opened

ROOT = Path(__file__).resolve().parents[1]
LIVE = 'd4eb098b'   # 2.5.2.4, the release this one may be rolled back to
DISH = 'hong_tra'


def P(s):
    return s['journey'].get('bank_plus')


def V(s):
    return public_state(s)['journey']['bank']


def refused(test, s, name, code=None, career=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        apply_action(s, career, name, p)
    test.assertEqual(s, before)
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


def grown(s, n=8, salary=60):
    """Lived past the 7-day rule (life day 9 from a fresh save), with some income on the record."""
    days(s, n, salary)
    return s


class Gate(unittest.TestCase):
    def test_no_card_or_loan_before_seven_full_days(self):
        s = opened(wallet=5000)
        self.assertIn('đủ 7 ngày', V(s)['card_offer']['text'])
        s, r = act(s, 'jr_bk_card_apply', confirm=True)
        self.assertFalse(r['approved'])
        self.assertIn('đủ 7 ngày', r['message'])
        self.assertEqual((B(s)['score'], B(s)['inq']), (bk.SCORE_START, []))     # no inquiry on the record
        q = bk.quote(100, 'personal', 14, s['journey']['life_day'])
        s, r = act(s, 'jr_bk_loan_apply', kind='personal', amount=100, term=14, total_interest=q['interest'], confirm=True)
        self.assertFalse(r['approved'])
        self.assertEqual(V(s)['plus']['stock']['why'], 'young')
        days(s, 6, 60)                                                              # Ngày 7: still one day short
        self.assertEqual(V(s)['card_offer']['why'], 'young')
        days(s, 1, 60)                                                              # Ngày 8: 7 full days lived
        self.assertNotEqual(V(s)['card_offer']['why'], 'young')
        self.assertIsNone(V(s)['plus']['young'])

    def test_an_old_card_keeps_working(self):
        s = with_card()
        s['journey']['life_day'] = 3      # (a card opened before the rule)
        B(s)['day'] = 3
        self.assertIsNone(bk.card_usable(s))


class CardLimit(unittest.TestCase):
    def test_the_full_limit_goes_past_the_old_cap(self):
        s = with_card(income_days=14, salary=5000, score=760)
        self.assertEqual(B(s)['card']['limit'], bk.LIMIT_MAX)                     # what an older build validates
        self.assertEqual(P(s)['card'], dict(no=B(s)['card']['no'], limit=52500))  # 5.000/ngày × 7 × 1,5
        v = V(s)['card']
        self.assertEqual((v['limit'], v['available']), (52500, 52500))
        bk.pay(s, 20000, 'Đồ nghề', method='card')
        self.assertEqual(B(s)['card']['bal'], 20000)
        self.assertEqual(V(s)['card']['available'], 32500)
        self.assertEqual(V(s)['card']['cash_room'], bk.LIMIT_MAX * bk.CASH_SHARE // 100)   # ứng tiền mặt keeps the card's own limit
        validate_state(s)

    def test_a_review_raises_it_once_a_week(self):
        s = with_card(income_days=14, salary=60)
        self.assertEqual(V(s)['card']['limit'], 250)
        days(s, 14, 600)
        s, r = act(s, 'jr_bk_card_review', confirm=True)
        self.assertTrue(r['approved'], r['message'])
        lim = V(s)['card']['limit']
        self.assertGreater(lim, 250)
        self.assertEqual(B(s)['card']['limit'], min(lim, bk.LIMIT_MAX))
        refused(self, s, 'jr_bk_card_review', 'too_soon', confirm=True)
        days(s, bp.REVIEW_DAYS)
        s, r = act(s, 'jr_bk_card_review', confirm=True)                         # no higher: it stays
        self.assertFalse(r['approved'])
        self.assertEqual(V(s)['card']['limit'], lim)

    def test_a_new_card_number_does_not_inherit_a_raised_limit(self):
        s = with_card(income_days=14, salary=5000, score=760)
        P(s)['card']['no'] = '0000' if B(s)['card']['no'] != '0000' else '1111'
        self.assertEqual(V(s)['card']['limit'], bk.LIMIT_MAX)


class Tiers(unittest.TestCase):
    def rich(self):
        s = opened(wallet=300_000_000)
        s, _ = act(s, 'jr_bk_deposit', amount=250_000_000)
        return s

    def test_ten_million_then_upgrade(self):
        s = self.rich()
        s, _ = act(s, 'jr_bk_save', amount=6_000_000, term=0)
        s, _ = act(s, 'jr_bk_save', amount=4_000_000, term=30)
        msg = refused(self, s, 'jr_bk_save', 'save_cap', amount=1, term=0)
        self.assertIn('10.000.000 xu', msg)
        self.assertEqual(V(s)['plus']['room'], 0)
        refused(self, s, 'jr_bk_tier', tier=1, src='acc')                        # needs the confirm
        s, r = act(s, 'jr_bk_tier', tier=1, src='acc', confirm=True)
        self.assertIn('Bạc', r['message'])
        self.assertEqual(B(s)['balance'], 240_000_000 - 2_000_000)
        s, _ = act(s, 'jr_bk_save', amount=90_000_000, term=0)
        refused(self, s, 'jr_bk_save', 'save_cap', amount=1, term=0)
        s, _ = act(s, 'jr_bk_tier', tier=2, src='acc', confirm=True)
        self.assertEqual(B(s)['balance'], 238_000_000 - 90_000_000 - 20_000_000)
        s, _ = act(s, 'jr_bk_save', amount=100_000_000, term=0)
        refused(self, s, 'jr_bk_tier', tier=2, src='acc', confirm=True)          # already there
        refused(self, s, 'jr_bk_tier', tier=3, src='acc', confirm=True)
        validate_state(s)

    def test_two_tiers_at_once_pay_both(self):
        s = self.rich()
        self.assertEqual([t['cost'] for t in V(s)['plus']['tiers']], [0, 2_000_000, 22_000_000, 222_000_000, 2_222_000_000])
        s, _ = act(s, 'jr_bk_tier', tier=2, src='acc', confirm=True)
        self.assertEqual(B(s)['balance'], 250_000_000 - 22_000_000)
        self.assertEqual(V(s)['plus']['cap'], 10**9)

    def test_money_already_saved_above_the_cap_stays_and_earns(self):
        s = self.rich()
        B(s)['demand'] = 50_000_000                       # saved before the tiers existed
        validate_state(s)
        v = V(s)['plus']
        self.assertTrue(v['over'])
        self.assertEqual(v['room'], 0)
        refused(self, s, 'jr_bk_save', 'save_cap', amount=1, term=0)
        days(s, 3)
        self.assertGreater(B(s)['demand'], 50_000_000)    # interest still paid
        s, _ = act(s, 'jr_bk_unsave', id='demand', amount=1_000_000)
        self.assertEqual(B(s)['balance'], 251_000_000)

    def test_cash_pays_too_and_not_enough_is_refused(self):
        s = opened(wallet=1_000_000)
        refused(self, s, 'jr_bk_tier', 'not_enough', tier=1, src='cash', confirm=True)
        s['journey']['wallet'] = 3_000_000
        s, _ = act(s, 'jr_bk_tier', tier=1, src='cash', confirm=True)
        self.assertEqual((s['journey']['wallet'], P(s)['tier']), (1_000_000, 1))


class HighTiers(unittest.TestCase):
    """Owner 22/10 (later): 💎 Kim cương 10 tỷ and 👑 Thượng hạng 100 tỷ; a higher tier earns a little more interest."""

    def kim_cuong(self):
        s = opened(wallet=10**9)
        s, _ = act(s, 'jr_bk_deposit', amount=10**9)
        s, _ = act(s, 'jr_bk_tier', tier=2, src='acc', confirm=True)
        s, _ = act(s, 'jr_bk_save', amount=B(s)['balance'], term=0)                  # 978.000.000
        refused(self, s, 'jr_bk_tier', 'not_enough', tier=3, src='acc', confirm=True)
        s, r = act(s, 'jr_bk_tier', tier=3, src='sav', confirm=True)                # the fee from the savings
        self.assertIn('Kim cương', r['message'])
        self.assertEqual(B(s)['demand'], 778_000_000)
        s['journey']['wallet'] = 10**9
        s, _ = act(s, 'jr_bk_save', amount=10**9, term=0, src='cash')
        return s

    def test_kim_cuong_saves_past_one_ty_as_one_book(self):
        s = self.kim_cuong()
        self.assertEqual((B(s)['demand'], P(s)['vip']), (bk.BAL_MAX, 778_000_000))
        v = V(s)
        self.assertEqual((v['savings']['demand'], v['savings']['total'], v['plus']['saved']), (1_778_000_000,) * 3)
        self.assertEqual(v['plus']['room'], 10**10 - 1_778_000_000)
        validate_state(s)
        net = wealth.sheet(s)[1]
        self.assertEqual(fair_bm.total_money(s['journey']), 1_778_000_000)          # a fine counts it too
        s, _ = act(s, 'jr_bk_unsave', id='demand', amount=500_000_000)              # vip leaves first
        self.assertEqual((B(s)['demand'], P(s)['vip'], B(s)['balance']), (bk.BAL_MAX, 278_000_000, 500_000_000))
        self.assertEqual(wealth.sheet(s)[1], net)
        refused(self, s, 'jr_bk_tier', 'no_money', tier=4, src='sav', confirm=True)  # 2 tỷ: not there yet
        days(s)
        # 1 tỷ × 0,05 % × 1,04 = 520.000 (spills into vip: the bank's pot is full), then 278,52 triệu × 0,052 % = 144.830
        self.assertEqual((B(s)['demand'], P(s)['vip']), (bk.BAL_MAX, 278_000_000 + 520_000 + 144_830))
        validate_state(s)
        s, _ = act(s, 'jr_bk_unsave', id='demand', amount=500_000_000)              # 278,66 triệu from vip, then the rest
        self.assertEqual(P(s)['vip'], 0)
        self.assertEqual(B(s)['demand'], bk.BAL_MAX - 500_000_000 + 278_664_830)
        validate_state(s)

    def test_vip_only_from_kim_cuong(self):
        s = opened(wallet=10**9)
        s, _ = act(s, 'jr_bk_deposit', amount=10**9)
        P(s) or bp.ensure(s)
        P(s)['tier'] = 2
        B(s)['demand'] = bk.BAL_MAX - 10                                             # grandfathered at Vàng
        msg = refused(self, s, 'jr_bk_save', amount=11, term=0)
        self.assertIn('10 xu', msg)
        days(s)
        self.assertEqual((B(s)['demand'], bp.vip(s)), (bk.BAL_MAX, 0))               # what does not fit is not paid

    def test_thuong_hang_from_the_savings(self):
        s = self.kim_cuong()
        P(s)['vip'] = 3 * 10**9                                                     # saved over time
        validate_state(s)
        s, r = act(s, 'jr_bk_tier', tier=4, src='sav', confirm=True)
        self.assertIn('Thượng hạng', r['message'])
        self.assertIn('thêm 5%', r['message'])
        self.assertEqual((P(s)['tier'], P(s)['vip'], B(s)['demand']), (4, 10**9, bk.BAL_MAX))
        self.assertEqual([g['amt'] for g in B(s)['log'][-2:]], [-10**9, -10**9])   # one row holds at most 1 tỷ
        self.assertEqual(V(s)['plus']['cap'], 10**11)
        refused(self, s, 'jr_bk_tier', tier=5, src='sav', confirm=True)
        validate_state(s)

    def gains(self, tier):
        """One day of the sổ không kỳ hạn and a 7-day sổ, at `tier`."""
        s = opened(wallet=10**9)
        s, _ = act(s, 'jr_bk_deposit', amount=200_000_000)
        s, _ = act(s, 'jr_bk_save', amount=10_000_000, term=7)
        bp.ensure(s)['tier'] = tier
        B(s)['demand'] = 100_000_000
        promised = V(s)['savings']['terms'][0]['interest']
        before = B(s)['balance']
        days(s)
        demand = B(s)['demand'] - 100_000_000
        days(s, 6)
        return demand, B(s)['balance'] - before - 10_000_000, promised

    def test_a_higher_tier_earns_a_little_more(self):
        base_d, base_t, _ = self.gains(0)
        self.assertEqual(base_d, 50_000)                                           # 100 triệu × 0,05 %/ngày
        self.assertGreater(base_t, 0)
        for tier, pm in enumerate(bp.RATE_BONUS):
            with self.subTest(tier=tier):
                d, t, promised = self.gains(tier)
                self.assertEqual(d, 50_000 * (1000 + pm) // 1000)
                self.assertEqual(t, base_t * (1000 + pm) // 1000)
                self.assertEqual(promised, bk.term_interest(10_000_000, bk.TERM_RATE[7], 7) * (1000 + pm) // 1000)
        # owner 22/10: "8% cao quá, giảm nhẹ xíu đi": +0 / 1,5 / 3 / 4 / 5 % of the interest
        self.assertEqual(bp.RATE_BONUS, (0, 15, 30, 40, 50))
        self.assertEqual([self.gains(t)[0] for t in (1, 4)], [50_750, 52_500])
        s, r = act(opened(wallet=3_000_000), 'jr_bk_tier', tier=1, src='cash', confirm=True)
        self.assertIn('thêm 1,5%', r['message'])

    def test_early_close_gets_the_bonus_on_the_demand_rate(self):
        s = opened(wallet=10**9)
        s, _ = act(s, 'jr_bk_deposit', amount=200_000_000)
        bp.ensure(s)['tier'] = 4
        s, _ = act(s, 'jr_bk_save', amount=10_000_000, term=30)
        days(s, 2)
        early = V(s)['savings']['terms'][0]['early']
        before = B(s)['balance']
        s, _ = act(s, 'jr_bk_unsave', id=B(s)['terms'][0]['id'], confirm=True)
        self.assertEqual(B(s)['balance'] - before, 10_000_000 + early)
        self.assertEqual(early, 10_000_000 * bk.DEMAND_BP * 2 * 1050 // 1000 // 10000)


class QuayRestock(unittest.TestCase):
    """🏪 a counter whose till, fund and wallet cannot pay the restock (the player's case, #481)."""

    def shop(self, card=False, savings=4000, n=None):
        s = quay_opened('xe', wallet=20000)
        s, _ = act(s, 'jr_bk_open')
        days(s, (14 if card else 8) if n is None else n, 600)
        if card:
            s, r = act(s, 'jr_bk_card_apply', confirm=True)
            self.assertTrue(r['approved'], r['message'])
        if savings:
            s, _ = act(s, 'jr_bk_save', amount=savings, term=0, src='cash')
        st = ST(s)
        st['till'] = st['fund'] = 0
        s['journey']['wallet'] = 0
        return s

    def restock(self, s, n=40, **p):
        return act(s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: n}, **p)

    def test_a_restock_loan_pays_the_whole_shortfall(self):
        s = self.shop()
        cost = qb.goods_cost(ST(s), {DISH: 40})
        stock0 = ST(s)['business']['stock'].get(DISH, 0)
        s, r = self.restock(s, credit='loan')
        self.assertIn('Vay nhập hàng', r['message'])
        ln, = P(s)['loans']
        self.assertEqual((ln['principal'], ln['at']), (cost, dict(k='quay', id=ST(s)['id'])))
        self.assertEqual(ln['interest'], max(1, -(-cost * bp.STOCK_BP // 10000)))
        self.assertEqual(ln['due'], s['journey']['life_day'] + bp.STOCK_DAYS)
        self.assertEqual((ST(s)['till'], ST(s)['fund'], s['journey']['wallet']), (0, 0, 0))
        self.assertEqual(ST(s)['business']['stock'][DISH], stock0 + 40)
        self.assertEqual(V(s)['plus']['owed'], ln['principal'] + ln['interest'])
        validate_state(s)

    def test_the_card_pays_it_and_the_statement_comes_later(self):
        s = self.shop(card=True)
        cost = qb.goods_cost(ST(s), {DISH: 40})
        s, r = self.restock(s, credit='card')
        self.assertIn('Quẹt thẻ', r['message'])
        self.assertEqual(B(s)['card']['bal'], cost)
        self.assertEqual((P(s) or {}).get('loans', []), [])
        st = next_statement(s)                            # interest-free until the statement's due day
        self.assertEqual(st['amount'], cost)

    def test_the_bank_saying_no_changes_nothing(self):
        s = self.shop(savings=0)
        B(s)['score'] = bk.CARD_MIN_SCORE - 1            # the bank says no; no card either
        refused(self, s, 'jr_quay_restock', 'credit_declined', stall=ST(s)['id'], items={DISH: 40}, credit='loan')
        refused(self, s, 'jr_quay_restock', 'card_declined', stall=ST(s)['id'], items={DISH: 40}, credit='card')
        refused(self, s, 'jr_quay_restock', None, stall=ST(s)['id'], items={DISH: 40}, credit='gold')
        s = self.shop(n=6)                               # Ngày 7: one day short
        msg = refused(self, s, 'jr_quay_restock', 'credit_declined', stall=ST(s)['id'], items={DISH: 40}, credit='loan')
        self.assertIn('đủ 7 ngày', msg)

    def test_no_shortfall_borrows_nothing(self):
        s = self.shop()
        ST(s)['fund'] = 10**6
        s, r = self.restock(s, credit='loan')
        self.assertEqual(P(s), None)
        self.assertNotIn('Vay', r['message'])

    def test_due_day_takes_the_account_then_the_counter_then_the_wallet(self):
        s = self.shop()
        s, _ = self.restock(s, credit='loan')
        ln = P(s)['loans'][0]
        owe = bp.owed(ln)
        B(s)['balance'] = 10
        ST(s)['till'], ST(s)['fund'] = 5, 6
        s['journey']['wallet'] = owe                     # enough to finish
        score = B(s)['score']
        days(s, bp.STOCK_DAYS)
        self.assertEqual(P(s)['loans'], [])
        self.assertEqual((B(s)['balance'], ST(s)['till'], ST(s)['fund']), (0, 0, 0))
        self.assertEqual(s['journey']['wallet'], owe - (owe - 21))
        self.assertGreater(B(s)['score'], score - 1)     # on time: loan_ok
        self.assertTrue(any('tất toán khoản vay nhập hàng' in m['text'] for m in B(s)['inbox']))

    def test_unpaid_is_late_blocks_credit_and_ends_in_bad_debt(self):
        s = self.shop()
        s, _ = self.restock(s, credit='loan')
        B(s)['balance'] = 0
        days(s, bp.STOCK_DAYS)
        ln = P(s)['loans'][0]
        self.assertEqual(ln['nfee'], 1)
        self.assertGreaterEqual(ln['fees'], bp.STOCK_LATE_MIN)
        self.assertEqual(B(s)['misses'], 1)
        self.assertTrue(V(s)['overdue'])
        self.assertEqual(V(s)['plus']['stock']['why'], 'overdue')
        self.assertEqual(V(s)['card_offer']['why'], 'overdue')
        refused(self, s, 'jr_quay_restock', 'credit_declined', stall=ST(s)['id'], items={DISH: 40}, credit='loan')
        self.assertGreaterEqual(s['journey']['wallet'], 0)
        days(s, bk.LOAN_PERIOD * 2)                       # two more weeks: two more fees, the third miss = nợ xấu
        self.assertEqual(P(s)['loans'][0]['nfee'], 3)
        self.assertGreater(B(s)['bad_until'], s['journey']['life_day'])
        days(s, bk.LOAN_PERIOD * 3)
        self.assertEqual(P(s)['loans'][0]['nfee'], bp.NFEE_MAX)   # fees stop at NFEE_MAX
        # Paying it off by hand clears the overdue.
        ln = P(s)['loans'][0]
        s['journey']['wallet'] = bp.owed(ln)
        s, r = act(s, 'jr_bk_stock_pay', id=ln['id'], src='cash')
        self.assertEqual((P(s)['loans'], s['journey']['wallet']), ([], 0))
        self.assertFalse(V(s)['overdue'])
        validate_state(s)

    def test_the_line_follows_income_and_savings(self):
        s = self.shop(savings=0)
        inc = bk.income(s)
        num, den = bk._factor(B(s)['score'])
        self.assertEqual(V(s)['plus']['stock']['limit'], bk._floor10(inc['total'] * num // den))
        s['journey']['wallet'] = 4000
        s, _ = act(s, 'jr_bk_save', amount=4000, term=0, src='cash')
        self.assertEqual(V(s)['plus']['stock']['limit'], bk._floor10(inc['total'] * num // den + 2000))
        self.assertLessEqual(V(s)['plus']['stock']['limit'], bp.STOCK_MAX)


class StockRoom(unittest.TestCase):
    """📦 Kho & nhập hàng (inv_order / inv_order_cart): the workplace fund lacks money for an order."""

    def shop(self, card=False):
        s = story(wallet=2000)
        s, _ = apply_action(s, 'restaurant', 'select_career', {})
        s, _ = apply_action(s, 'restaurant', 'start_day', {})
        s, _ = act(s, 'jr_bk_open')
        days(s, 14 if card else 8, 600)
        if card:
            s, r = act(s, 'jr_bk_card_apply', confirm=True)
            self.assertTrue(r['approved'], r['message'])
        c = s['careers']['restaurant']
        empty(c, 'noodle')
        set_money(c, 3)
        s['journey']['wallet'] = 0
        return s

    def order(self, s, **p):
        return apply_action(s, 'restaurant', 'inv_order', dict(item='noodle', qty=10, supplier='partner', confirm=True, **p))

    def test_without_cover_the_fund_still_refuses(self):
        s = self.shop()
        refused(self, s, 'inv_order', career='restaurant', item='noodle', qty=10, supplier='partner', confirm=True)

    def test_a_loan_covers_exactly_what_the_fund_lacks(self):
        s = self.shop()
        s, r = self.order(s, cover='loan')
        c = s['careers']['restaurant']
        o = c['ext']['inv']['orders'][-1]
        ln, = P(s)['loans']
        self.assertEqual(ln['principal'], o['cost'] + o['ship'] - 3)
        self.assertEqual(c['money'], 0)
        self.assertEqual(ln['at'], dict(k='career', id='restaurant'))
        self.assertIn('Vay nhập hàng', r['message'])
        validate_state(s)

    def test_the_card_or_the_wallet(self):
        s = self.shop(card=True)
        s, r = self.order(s, cover='card')
        o = s['careers']['restaurant']['ext']['inv']['orders'][-1]
        self.assertEqual(B(s)['card']['bal'], o['cost'] + o['ship'] - 3)
        s = self.shop()
        refused(self, s, 'inv_order', 'no_money', career='restaurant', item='noodle', qty=10, supplier='partner', confirm=True, cover='wallet')
        s['journey']['wallet'] = 10**5
        s, r = self.order(s, cover='wallet')
        o = s['careers']['restaurant']['ext']['inv']['orders'][-1]
        self.assertEqual(s['journey']['wallet'], 10**5 - (o['cost'] + o['ship'] - 3))
        self.assertIsNone(P(s))

    def test_a_merged_order_too(self):
        s = self.shop()
        s, _ = apply_action(s, 'restaurant', 'inv_cart', dict(supplier='partner', op='add', item='noodle', qty=10))
        s, r = apply_action(s, 'restaurant', 'inv_order_cart', dict(supplier='partner', confirm=True, cover='loan'))
        self.assertEqual(len(P(s)['loans']), 1)
        self.assertEqual(s['careers']['restaurant']['money'], 0)

    def test_due_day_takes_the_fund_when_the_account_is_empty(self):
        s = self.shop()
        s, _ = self.order(s, cover='loan')
        owe = bp.owed(P(s)['loans'][0])
        c = s['careers']['restaurant']
        set_money(c, owe + 50)
        B(s)['balance'] = 0
        days(s, bp.STOCK_DAYS)
        self.assertEqual(P(s)['loans'], [])
        self.assertEqual(s['careers']['restaurant']['money'], 50)
        validate_state(s)

    def test_cover_only_for_a_place_you_run(self):
        s = self.shop()
        refused(self, s, 'inv_order', career='restaurant', item='noodle', qty=10, supplier='partner', confirm=True, cover='later')
        s['journey']['story'] = False
        with self.assertRaises(GameError):
            self.order(s, cover='loan')


class Validation(unittest.TestCase):
    def test_bad_blocks_are_refused(self):
        s = QuayRestock().shop()
        s, _ = act(s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 40}, credit='loan')
        validate_state(s)
        for path, value in ((('tier',), 5), (('vip',), bp.VIP_MAX + 1), (('vip',), -1), (('vpend',), 10**4), (('card',), dict(no='12', limit=10)), (('loans', 0, 'due'), 1),
                            (('loans', 0, 'at', 'k'), 'shop'), (('loans', 0, 'paid'), 10**9), (('extra',), 1), (('v',), 2)):
            with self.subTest(path=path):
                x = copy.deepcopy(s)
                node = P(x)
                for k in path[:-1]:
                    node = node[k]
                node[path[-1]] = value
                with self.assertRaises(GameError):
                    validate_state(x)
        x = copy.deepcopy(s)
        del x['journey']['bank']
        with self.assertRaises(GameError):
            validate_state(x)


NODE = shutil.which('node')
PLAYWRIGHT = Path('C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs')


@unittest.skipUnless(NODE and PLAYWRIGHT.is_file(), 'node and playwright are required')
class Page(unittest.TestCase):
    def test_bank_plus_at_phone_width(self):
        s = QuayRestock().shop(card=True)
        s, _ = act(s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 40}, credit='loan')
        r = subprocess.run([NODE, 'tests/bank_plus_browser.mjs'], cwd=ROOT, input=json.dumps(public_state(s), ensure_ascii=False),
                           capture_output=True, text=True, encoding='utf-8', timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-3000:])


class RollbackTo2524(unittest.TestCase):
    """Saves holding j['bank_plus'] (a tier, a raised card, restock loans, one late) validate, tick a life day and render on
    2.5.2.4 (`git archive d4eb098b`), and come back here intact."""

    def tree(self):
        tmp = tempfile.mkdtemp(prefix='mnl-2524-')
        try:
            data = subprocess.run(['git', 'archive', LIVE, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {LIVE}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return tmp

    def saves(self):
        out = []
        s = QuayRestock().shop(card=True)
        s, _ = act(s, 'jr_quay_restock', stall=ST(s)['id'], items={DISH: 40}, credit='loan')
        P(s)['tier'] = 1
        P(s)['card'] = dict(no=B(s)['card']['no'], limit=bk.LIMIT_MAX * 3)
        bk.pay(s, bk.LIMIT_MAX + 500, 'Đồ nghề', method='card')     # a balance above the card's own limit
        validate_state(s)
        out.append(copy.deepcopy(s))
        B(s)['balance'] = 0
        days(s, bp.STOCK_DAYS)                                       # one restock loan late
        self.assertEqual(P(s)['loans'][0]['nfee'], 1)
        out.append(copy.deepcopy(s))
        k = HighTiers().kim_cuong()                                  # 💎 1 tỷ in the bank's pot, the rest in vip
        validate_state(k)
        out.append(copy.deepcopy(k))
        return json.loads(json.dumps(out))

    def test_saves_cross_2524_both_ways(self):
        saves = self.saves()
        old = self.tree()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state;from game import bank\n'
                'out=[]\n'
                'for s in json.load(sys.stdin):\n'
                ' validate_state(s);s=migrate_state(s);validate_state(s);public_state(s)\n'
                ' s["journey"]["life_day"]+=1;bank.on_life_day(s);validate_state(s)\n'
                ' out.append(s)\n'
                'import game;print(json.dumps([game.__version__,out]))')
        env = {k: v for k, v in os.environ.items() if k != 'MNL_CAREERS'}
        env['PYTHONPATH'] = old
        got = subprocess.run([sys.executable, '-c', prog], input=json.dumps(saves), capture_output=True, text=True,
                             cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        version, back = json.loads(got.stdout)
        self.assertEqual(version, '2.5.2.4')
        for mine, s in zip(saves, back):
            self.assertEqual(s['journey']['bank_plus'], mine['journey']['bank_plus'])   # kept, not read
            s = migrate_state(s)
            validate_state(s)
            days(s)                                                  # this build catches the loans up
            public_state(s)
            validate_state(s)


if __name__ == '__main__':
    unittest.main()
