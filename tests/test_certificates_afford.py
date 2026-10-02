"""🎓 Thi chứng chỉ (1.4.4, player confusion: every "Ví chưa đủ # xu học phí" refusal was a tap on a class the
wallet could not pay). certificates.js feePay() decides from the public journey whether the paid class can be
paid ('cash', 'card') or not (None: the class is shut, the free self-study is the main button). These tests
mirror it in Python and check every verdict against the server."""
import copy
import unittest

from game import certificates as ct
from game.engine import GameError, public_state, validate_state
from tests.test_bank import B, act, story, with_card

GID = 'work_safety'


def fee_pay(s, fee):
    """certificates.js feePay over the public journey."""
    J = public_state(s)['journey']
    if not fee > 0 or J['wallet'] >= fee:
        return 'cash'
    bank, card = J.get('bank') or {}, (J.get('bank') or {}).get('card')
    return 'card' if card and not card['locked'] and card['available'] >= fee and bank.get('pref') != 'cash' else None


class FeePay(unittest.TestCase):
    def enrol(self, s):
        return act(s, 'jr_cert_enrol', cert=GID, mode='class')   # the client sends no `pay`: 'auto'

    def refused(self, s):
        before = copy.deepcopy(s)
        with self.assertRaises(GameError) as e:
            self.enrol(s)
        self.assertIn('Ví chưa đủ', str(e.exception))   # the wallet refusal, not some other check
        self.assertEqual(s, before)

    def test_wallet_short_and_no_card_shuts_the_class_but_self_study_is_free(self):
        fee = ct.tuition(GID)
        s = story(wallet=fee - 1)
        self.assertIsNone(fee_pay(s, fee))
        self.refused(s)
        s, r = act(s, 'jr_cert_enrol', cert=GID, mode='self')
        self.assertEqual((s['journey']['study']['fee'], s['journey']['wallet']), (0, fee - 1))

    def test_wallet_enough_pays_cash(self):
        fee = ct.tuition(GID)
        s = story(wallet=fee)
        self.assertEqual(fee_pay(s, fee), 'cash')
        s, _ = self.enrol(s)
        self.assertEqual(s['journey']['wallet'], 0)

    def test_a_usable_card_pays_when_the_wallet_is_short(self):
        fee = ct.tuition(GID)
        s = with_card()
        s['journey']['wallet'] = 0
        validate_state(s)
        self.assertEqual(fee_pay(s, fee), 'card')
        s, r = self.enrol(s)
        self.assertEqual(B(s)['card']['bal'], fee)

    def test_cash_only_preference_or_a_locked_card_does_not(self):
        fee = ct.tuition(GID)
        s = with_card()
        s['journey']['wallet'] = 0
        B(s)['pref'] = 'cash'
        validate_state(s)
        self.assertIsNone(fee_pay(s, fee))
        self.refused(s)
        B(s)['pref'] = 'auto'
        B(s)['card']['past_due'] = 5
        validate_state(s)
        self.assertIsNone(fee_pay(s, fee))
        self.refused(s)


if __name__ == '__main__':
    unittest.main()
