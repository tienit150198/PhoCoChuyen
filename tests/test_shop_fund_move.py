"""💼 Rút / góp vốn (F#259, 08/10): "lỡ bấm rút hết vốn tiệm… cho góp vốn, hoặc điều chỉnh số tiền rút".

The server stays the authority: jr_withdraw takes any typed amount up to withdraw_max, jr_invest puts money back from
the wallet first, then the bank account (like 🏪 Góp vốn quầy), never into debt and never past what is there. The
public state says how much Góp vốn can take (journey.invest_max). No new save keys."""
import json
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


if __name__ == '__main__':
    unittest.main()
