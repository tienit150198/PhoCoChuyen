"""Risk frequency tuning preserves prevention and covers every eligible kind."""
import unittest
from unittest.mock import patch

from game import rui, quay_economy as qe
from tests.test_rui import grown, R, own_home
from tests import test_quay_economy


class RiskFrequency(unittest.TestCase):
    def test_new_risk_band_starts_a_warning_without_applying_loss(self):
        # A 10% draw missed the former 6.4% pool for this household.
        s = grown(wallet=2000, day=40, bank=10000)
        own_home(s)
        r = R(s)
        before = s['journey']['wallet'], s['journey']['bank']['balance']
        with patch.object(rui, '_rng') as random:
            random.return_value.random.return_value = .10
            random.return_value.choice.side_effect = lambda values: values[0]
            random.return_value.choices.side_effect = lambda values, **kw: [values[0]]
            rui._roll(s, r, 40, [])
        self.assertIsNotNone(r['warn'])
        self.assertIsNone(r['card'])
        self.assertGreater(r['warn']['day'], 40)
        self.assertEqual(before, (s['journey']['wallet'], s['journey']['bank']['balance']))

    def test_large_asset_pool_does_not_starve_bank_hack(self):
        s = grown(wallet=2000, day=40, bank=10000)
        r = R(s)
        with patch.object(rui, 'candidates', return_value=[(12000, 'om', '', None), (360, 'hack', 'account', None)]), patch.object(rui, '_rng') as random:
            random.return_value.random.return_value = .999
            random.return_value.choice.side_effect = lambda values: values[0]
            rui._roll(s, r, 40, [])
        self.assertEqual(r['warn']['kind'], 'hack')

    def test_counter_new_frequency_band_and_new_counter_grace(self):
        s, st = test_quay_economy.Economy().sample()
        with patch('game.quay._rng') as random:
            random.return_value.randrange.return_value = 0
            random.return_value.random.return_value = .25
            self.assertEqual(qe._event(s, st, st['opened'] + 5), 'theft')
            self.assertIsNone(qe._event(s, st, st['opened'] + 4))


if __name__ == '__main__':
    unittest.main()
