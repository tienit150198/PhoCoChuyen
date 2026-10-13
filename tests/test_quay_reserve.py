"""F#362: opt-in operating reserve, collection conserves every xu."""
import json
import unittest

from game import quay as qy
from game.engine import GameError, public_state, validate_state
from tests.test_quay import ST, act, opened, refused
from tests.test_quay_manage import NODE, plan


class Reserve(unittest.TestCase):
    def fixture(self, fund=20, till=150, reserve=None):
        s = opened(staff=False)
        ST(s).update(fund=fund, till=till)
        if reserve is not None:
            ST(s)['reserve'] = reserve
        return s

    def test_old_save_defaults_to_zero_and_collects_everything(self):
        s = self.fixture()
        ST(s).pop('reserve', None)
        validate_state(s)
        view = public_state(s)['journey']['quay']['stalls'][0]
        self.assertEqual((view.get('reserve'), view.get('collectable_till')), (0, 150))
        wallet = s['journey']['wallet']
        s, _ = act(s, 'jr_quay_till', stall=ST(s)['id'])
        self.assertEqual((ST(s)['fund'], ST(s)['till'], s['journey']['wallet'] - wallet), (20, 0, 150))

    def test_collection_only_fills_floor_and_conserves_money(self):
        for fund, till, reserve, kept, collected in ((20, 150, 100, 80, 70), (20, 30, 100, 30, 0),
                                                   (120, 150, 100, 0, 150), (20, 150, 0, 0, 150),
                                                   (qy.MONEY_MAX - 10, 50, qy.MONEY_MAX, 10, 40)):
            with self.subTest(fund=fund, till=till, reserve=reserve):
                s = self.fixture(fund, till, reserve)
                wallet = s['journey']['wallet']
                s, result = act(s, 'jr_quay_till', stall=ST(s)['id'])
                self.assertEqual((ST(s)['fund'], ST(s)['till'], s['journey']['wallet'] - wallet),
                                 (fund + kept, 0, collected))
                self.assertEqual((result.get('collected'), result.get('retained')), (collected, kept))
                s, result = act(s, 'jr_quay_till', stall=ST(s)['id'])
                self.assertEqual((ST(s)['fund'], s['journey']['wallet'] - wallet), (fund + kept, collected))
                self.assertEqual((result.get('collected'), result.get('retained')), (0, 0))
                validate_state(s)

    def test_setting_reserve_is_optional_and_does_not_transfer_money(self):
        s = self.fixture()
        balances = (ST(s)['fund'], ST(s)['till'], s['journey']['wallet'])
        for amount in (100, qy.MONEY_MAX, 0):
            s, _ = act(s, 'jr_quay_reserve', stall=ST(s)['id'], amount=amount)
            self.assertEqual(ST(s).get('reserve'), amount)
            self.assertEqual((ST(s)['fund'], ST(s)['till'], s['journey']['wallet']), balances)
            s = json.loads(json.dumps(s))
            validate_state(s)
            self.assertEqual(public_state(s)['journey']['quay']['stalls'][0]['reserve'], amount)

    def test_invalid_settings_and_tampered_saves_are_rejected_atomically(self):
        for value in (-1, qy.MONEY_MAX + 1, True, 1.5, '100', None, {}, []):
            with self.subTest(value=value):
                s = self.fixture(reserve=100)
                refused(self, s, 'jr_quay_reserve', stall=ST(s)['id'], amount=value)
                ST(s)['reserve'] = value
                with self.assertRaises(GameError):
                    validate_state(s)
        s = self.fixture(reserve=100)
        refused(self, s, 'jr_quay_reserve', stall=ST(s)['id'], amount=0, wallet=999)
        refused(self, s, 'jr_quay_reserve', stall='q999', amount=0)

    def test_manual_till_to_fund_preserves_overflow(self):
        s = self.fixture(fund=qy.MONEY_MAX - 10, till=50, reserve=0)
        wallet = s['journey']['wallet']
        s, _ = act(s, 'jr_quay_till', stall=ST(s)['id'], to='fund')
        self.assertEqual((ST(s)['fund'], ST(s)['till'], s['journey']['wallet']), (qy.MONEY_MAX, 40, wallet))
        s, _ = act(s, 'jr_quay_till', stall=ST(s)['id'], to='fund')
        self.assertEqual((ST(s)['fund'], ST(s)['till']), (qy.MONEY_MAX, 40))

    @unittest.skipUnless(NODE, 'node required')
    def test_bulk_preview_matches_server_even_when_everything_is_retained(self):
        for till, expected in ((150, 70), (30, 0)):
            s = self.fixture(till=till, reserve=100)
            p = plan(kind='till', journey=public_state(s)['journey'])
            self.assertEqual(p['total'], expected)
            self.assertEqual(p['steps'], [{'stall': ST(s)['id']}])
            wallet = s['journey']['wallet']
            for payload in p['steps']:
                s, _ = act(s, 'jr_quay_till', **payload)
            self.assertEqual(s['journey']['wallet'] - wallet, expected)
            self.assertEqual(ST(s)['fund'], 20 + till - expected)


if __name__ == '__main__':
    unittest.main()
