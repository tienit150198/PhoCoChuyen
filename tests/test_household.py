import copy
import unittest

from game import household as hh
from game.engine import GameError, validate_state, public_state
from tests.test_bank import story
from tests.test_bank import opened, B, with_card
from unittest.mock import patch
from pathlib import Path
import tempfile
import shutil
import subprocess
from game.engine import apply_action


def act(s, action, **params):
    return apply_action(s, None, action, params)


class Household(unittest.TestCase):
    def ready(self):
        s = story(500)
        s['journey']['life_day'] = 12
        return s

    def test_opt_in_and_retries_do_not_adopt_or_charge_twice(self):
        s = self.ready()
        self.assertNotIn('household', s['journey'])
        self.assertEqual(hh.public(s)['members'], [])
        with self.assertRaises(GameError):
            act(s, 'jr_hh_adopt', kind='cat', name='Miu')
        s, _ = act(s, 'jr_hh_adopt', kind='cat', name='Miu', confirm=True)
        self.assertEqual(s['journey']['wallet'], 470)
        with self.assertRaises(GameError):
            act(s, 'jr_hh_adopt', kind='dog', name='Mun', confirm=True)
        self.assertEqual(s['journey']['wallet'], 470)
        validate_state(s)

    def test_care_daily_slots_growth_and_offline_no_charge(self):
        s = self.ready()
        s, _ = act(s, 'jr_hh_adopt', kind='child', name='Bông', confirm=True)
        for day in range(12, 32):
            s['journey']['life_day'] = day
            s, _ = act(s, 'jr_hh_care', member='child', act='milk')
            s, _ = act(s, 'jr_hh_care', member='child', act='play')
            with self.assertRaises(GameError):
                act(s, 'jr_hh_care', member='child', act='read')
        self.assertEqual(hh.public(s)['members'][0]['stage'], 'Bé đi học')
        wallet = s['journey']['wallet']
        s['journey']['life_day'] += 100
        before = copy.deepcopy(s)
        self.assertEqual(hh.public(s)['members'][0]['needs']['food'], 0)
        self.assertEqual(s, before)
        self.assertEqual(s['journey']['wallet'], wallet)
        validate_state(s)

    def test_bad_input_and_insufficient_payment_are_atomic(self):
        s = self.ready()
        for kind, name in [('dragon', 'Miu'), ('child', '<script>'), ('cat', ''), ('cat', 'a'*25)]:
            with self.assertRaises(GameError):
                act(s, 'jr_hh_adopt', kind=kind, name=name, confirm=True)
        s, _ = act(s, 'jr_hh_adopt', kind='child', name='Bông', confirm=True)
        s['journey']['wallet'] = 0
        before = copy.deepcopy(s)
        with self.assertRaises(GameError):
            act(s, 'jr_hh_care', member='child', act='milk')
        self.assertEqual(s, before)
        s, _ = act(s, 'jr_hh_care', member='child', act='wash')
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertIn('household', public_state(s)['journey'])

    def test_rename_clothes_and_validation(self):
        s = self.ready()
        s, _ = act(s, 'jr_hh_adopt', kind='child', name='Bông', confirm=True)
        s, _ = act(s, 'jr_hh_style', member='child', item='yem', confirm=True)
        self.assertEqual(hh.public(s)['members'][0]['outfit'], 'yem')
        s, _ = act(s, 'jr_hh_rename', member='child', name='Mây')
        self.assertEqual(hh.public(s)['members'][0]['name'], 'Mây')
        bad = copy.deepcopy(s)
        bad['journey']['household']['child']['food'] = 101
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_bad_payment_never_silently_uses_credit(self):
        s = with_card()
        s['journey']['wallet'] = 0
        before = copy.deepcopy(s)
        for pay in ('typo', [], {}, None, True):
            with self.subTest(pay=pay), self.assertRaises(GameError):
                act(s, 'jr_hh_adopt', kind='cat', name='Miu', confirm=True, pay=pay)
            self.assertEqual(s, before)

    def test_malformed_save_types_raise_game_error(self):
        s, _ = act(self.ready(), 'jr_hh_adopt', kind='cat', name='Miu', confirm=True)
        for key, value in [('kind', []), ('kind', {}), ('name', []), ('owned', ['basic', {}]), ('did', [[]]), ('outfit', []), ('food', True), ('since', 13)]:
            bad = copy.deepcopy(s)
            bad['journey']['household']['pet'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(GameError):
                validate_state(bad)
        bad = copy.deepcopy(s)
        bad['journey']['household']['v'] = True
        with self.assertRaises(GameError):
            validate_state(bad)

    def test_account_shortage_and_payment_exception_leave_household_unchanged(self):
        s = opened(wallet=500, deposit=2)
        s['journey']['life_day'] = 12
        B(s)['pref'] = 'account'
        s, _ = act(s, 'jr_hh_adopt', kind='child', name='Bông', confirm=True)
        before = copy.deepcopy(s)
        for action, params in [('jr_hh_care', dict(member='child', act='milk')), ('jr_hh_style', dict(member='child', item='yem', confirm=True)), ('jr_hh_adopt', dict(kind='dog', name='Mun', confirm=True))]:
            with self.subTest(action=action), self.assertRaises(GameError):
                act(s, action, **params)
            self.assertEqual(s, before)
        B(s)['balance'] = 200
        before = copy.deepcopy(s)
        with patch.object(hh.bank, 'pay', side_effect=GameError('Payment unavailable', 'busy')), self.assertRaises(GameError):
            act(s, 'jr_hh_care', member='child', act='milk')
        self.assertEqual(s, before)

    def test_store_replay_of_each_household_purchase_debits_once(self):
        from game.storage import Store
        from game import marriage as mr
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            store = Store(Path(tmp)/'household.db', story=True)
            try:
                token, _, _ = store.session()
                seed = opened(wallet=200, deposit=200)
                seed['journey']['life_day'] = 12
                B(seed)['pref'] = 'account'
                mr._mutate(store, {store.key(token):lambda s:s.update(copy.deepcopy(seed))})
                spend = 0
                purchases = [('jr_hh_adopt', dict(kind='child', name='Bông', confirm=True), 0), ('jr_hh_adopt', dict(kind='cat', name='Miu', confirm=True), 30), ('jr_hh_care', dict(member='child', act='milk'), 4), ('jr_hh_style', dict(member='child', item='yem', confirm=True), 18)]
                for i, (action, payload, cost) in enumerate(purchases):
                    rev = store.read(token)[1]
                    args = (token, f'household-replay-{i:04d}', rev, None, action, payload)
                    first, second = store.command(*args), store.command(*args)
                    self.assertTrue(second['replayed'])
                    self.assertEqual(first['state'], second['state'])
                    spend += cost
                    s = store.read(token)[0]
                    self.assertEqual(B(s)['balance'], 200-spend)
                    self.assertEqual(s['journey']['wallet'], 0)
                    validate_state(s)
            finally:
                store.close_pool()

    def test_joint_preference_uses_existing_payment_bridge(self):
        from game import couple as cp
        s = opened()
        s['journey']['life_day'] = 12
        B(s)['pref'] = 'joint'
        with patch.object(cp, 'joint_account', return_value=dict(balance=100, daily_left=100)), patch.object(cp, 'joint_spend', return_value={}) as spend:
            paid, _ = act(s, 'jr_hh_adopt', kind='cat', name='Miu', confirm=True)
        spend.assert_called_once()
        self.assertEqual(spend.call_args.args[1], 30)
        self.assertEqual(paid['journey']['wallet'], s['journey']['wallet'])

    def test_browser_payment_confirmation_and_failed_api(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run([node,str(root/'tests/household_payment.mjs')],cwd=root,capture_output=True,text=True,timeout=60)
        self.assertEqual(out.returncode,0,out.stderr+out.stdout)


if __name__ == '__main__':
    unittest.main()
