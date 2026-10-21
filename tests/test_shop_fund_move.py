"""💼 Rút / góp vốn (F#259, 08/10): "lỡ bấm rút hết vốn tiệm… cho góp vốn, hoặc điều chỉnh số tiền rút".

The server stays the authority: jr_withdraw takes any typed amount up to withdraw_max, jr_invest puts money back from
the wallet first, then the bank account (like 🏪 Góp vốn quầy), never into debt and never past what is there. The
public state says how much Góp vốn can take (journey.invest_max). No new save keys."""
import json
import copy
import unittest

from game import journey as jr
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_journey import Play, ledger_ok


def act(s, action, **p):
    return apply_action(s, None, action, p)


class FundMoveTest(unittest.TestCase):
    def setUp(self):
        self.s = Play().s
        self.c = self.s['careers']['milk_tea']

    def test_withdraw_a_typed_part_then_put_it_back(self):
        most = jr.withdraw_max(self.c)
        self.assertGreater(most, 2)
        fund0, wallet0 = self.c['money'], self.s['journey']['wallet']
        part = most // 2
        s, r = act(self.s, 'jr_withdraw', career='milk_tea', amount=part)
        self.assertEqual(s['careers']['milk_tea']['money'], fund0 - part)
        self.assertEqual(s['journey']['wallet'], wallet0 + part)
        self.assertIn(f'Quỹ còn {fund0 - part} xu', r['message'])
        # Put it all back: the fund is whole again, the ledger stays an owner transfer.
        s, r = act(s, 'jr_invest', career='milk_tea', amount=part)
        c = s['careers']['milk_tea']
        self.assertEqual(c['money'], fund0)
        self.assertEqual(s['journey']['wallet'], wallet0)
        self.assertEqual(c['ops']['finance']['ledger'][-1]['category'], 'owner_capital')
        self.assertIn(f'Quỹ thành {fund0} xu', r['message'])
        self.assertNotIn('ngân hàng', r['message'])
        self.assertTrue(ledger_ok(c))
        self.assertEqual(s['journey']['history'][-1]['kind'], 'invest')
        validate_state(json.loads(json.dumps(s)))

    def test_invest_takes_the_wallet_then_the_bank_account(self):
        s = self.s
        s['journey']['wallet'] = 30
        s, _ = act(s, 'jr_bk_open')
        s['journey']['bank']['balance'] = 100
        self.assertEqual(jr.invest_max(s), 130)
        self.assertEqual(public_state(s)['journey']['invest_max'], 130)
        fund0 = s['careers']['milk_tea']['money']
        with self.assertRaises(GameError):
            act(s, 'jr_invest', career='milk_tea', amount=131)
        s2, r = act(s, 'jr_invest', career='milk_tea', amount=110)
        self.assertEqual(s2['journey']['wallet'], 0)
        self.assertEqual(s2['journey']['bank']['balance'], 20)
        self.assertEqual(s2['careers']['milk_tea']['money'], fund0 + 110)
        self.assertIn('80 xu từ tài khoản ngân hàng', r['message'])
        self.assertEqual(s2['journey']['stats']['invested'], 110)
        self.assertTrue(ledger_ok(s2['careers']['milk_tea']))
        validate_state(json.loads(json.dumps(s2)))

    def test_invest_never_runs_into_debt_and_refuses_bad_numbers(self):
        s = self.s
        s['journey']['wallet'] = 40
        for bad in (0, -5, 41, 1.5, '10', True, None, 10**7):
            with self.assertRaises(GameError, msg=repr(bad)):
                act(s, 'jr_invest', career='milk_tea', amount=bad)
        s['journey']['wallet'] = -10
        s, _ = act(s, 'jr_bk_open')
        s['journey']['bank']['balance'] = 500
        self.assertEqual(jr.invest_max(s), 0)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_invest', career='milk_tea', amount=5)
        self.assertIn('Ví đang nợ', str(e.exception))
        self.assertEqual(s['journey']['bank']['balance'], 500)

    def test_withdraw_limits_unchanged(self):
        most = jr.withdraw_max(self.c)
        for bad in (0, most + 1, 2.5, '5'):
            with self.assertRaises(GameError):
                act(self.s, 'jr_withdraw', career='milk_tea', amount=bad)
        s, _ = act(self.s, 'jr_withdraw', career='milk_tea', amount=most)
        self.assertEqual(s['careers']['milk_tea']['money'], jr._unpaid(s['careers']['milk_tea']) + jr.RESERVE)
        # Drew everything by mistake: Góp vốn brings it back (the wallet holds it now).
        s, _ = act(s, 'jr_invest', career='milk_tea', amount=most)
        self.assertEqual(s['careers']['milk_tea']['money'], self.c['money'])

    def test_free_play_has_no_invest(self):
        from tests.helpers import Journey
        j = Journey('milk_tea')
        self.assertEqual(public_state(j.state)['journey']['invest_max'], 0)
        with self.assertRaises(GameError):
            j.act('jr_invest', career='milk_tea', amount=5)

    def test_hundred_million_capital_preserves_cash_and_ledger(self):
        s = self.s
        s['journey']['wallet'] = 25_000_000
        s, _ = act(s, 'jr_bk_open')
        s['journey']['bank']['balance'] = 90_000_000
        old = s['careers']['milk_tea']
        start = old['money']
        self.assertEqual(public_state(s)['journey']['invest_max'], 115_000_000)   # F#462: no 100 triệu cap per Góp vốn
        s, _ = act(s, 'jr_invest', career='milk_tea', amount=100_000_000)
        c = s['careers']['milk_tea']
        self.assertEqual(c['money'], start + 100_000_000)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 15_000_000)
        self.assertEqual((c['earnings'], c['costs']), (old['earnings'], old['costs']))
        self.assertTrue(ledger_ok(c))
        rows = [r for r in s['journey']['history'] if r['kind'] == 'invest']
        self.assertEqual(sum(r['amount'] for r in rows), -25_000_000)
        self.assertTrue(all(abs(r['amount']) <= 10_000_000 for r in rows))
        validate_state(json.loads(json.dumps(s)))

    def test_a_fund_over_a_million_can_be_drawn(self):
        # F#416 (18/10): "không rút tiền từ quỹ về ví được": a fund past 1,000,080 xu answered "Số lượng không hợp lệ."
        s = self.s
        c = s['careers']['milk_tea']
        c['ops']['finance']['opening_balance'] += 50_000_000 - c['money']
        c['money'] = 50_000_000
        wallet0 = s['journey']['wallet']
        most = public_state(s)['journey']['places']['milk_tea']['withdraw_max']
        self.assertEqual(most, jr.withdraw_max(c, s['journey']))
        self.assertGreater(most, 45_000_000)
        s, r = act(s, 'jr_withdraw', career='milk_tea', amount=45_000_000)
        self.assertEqual(s['careers']['milk_tea']['money'], 5_000_000)
        self.assertEqual(s['journey']['wallet'], wallet0 + 45_000_000)
        rows = [x for x in s['journey']['history'] if x['kind'] == 'draw']
        self.assertEqual(sum(x['amount'] for x in rows), 45_000_000)
        self.assertTrue(all(0 < x['amount'] <= jr.ROW_MAX for x in rows))
        self.assertTrue(ledger_ok(s['careers']['milk_tea']))
        validate_state(json.loads(json.dumps(s)))

    def test_a_draw_never_fills_the_wallet_past_its_limit(self):
        s = self.s
        c = s['careers']['milk_tea']
        c['ops']['finance']['opening_balance'] += 50_000_000 - c['money']
        c['money'] = 50_000_000
        s['journey']['wallet'] = jr.WALLET_MAX - 1000
        self.assertEqual(jr.withdraw_max(c, s['journey']), 1000)
        before = copy.deepcopy(s)
        with self.assertRaisesRegex(GameError, 'tối đa 1000 xu'):
            act(s, 'jr_withdraw', career='milk_tea', amount=1001)
        self.assertEqual(s, before)
        s, _ = act(s, 'jr_withdraw', career='milk_tea', amount=1000)
        self.assertEqual(s['journey']['wallet'], jr.WALLET_MAX)
        validate_state(json.loads(json.dumps(s)))

    def test_capital_rejects_overflow_before_moving_money(self):
        s = self.s
        s['journey']['wallet'] = 200_000_000
        c = s['careers']['milk_tea']
        c['ops']['finance']['opening_balance'] += 999_999_990 - c['money']
        c['money'] = 999_999_990
        before = copy.deepcopy(s)
        with self.assertRaisesRegex(GameError, 'Quỹ nghề chỉ còn chỗ'):
            act(s, 'jr_invest', career='milk_tea', amount=11)
        self.assertEqual(s, before)
        self.assertEqual(public_state(s)['journey']['places']['milk_tea']['invest_max'], 10)
        with self.assertRaises(GameError):
            act(s, 'jr_invest', career='milk_tea', amount=100_000_001)
        self.assertEqual(s, before)


if __name__ == '__main__':
    unittest.main()
