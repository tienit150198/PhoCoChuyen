"""Personal account purchases: explicit opt-in, atomic accounting, replay safety."""
import copy
import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from game import bank as bk, marriage as mr, certificates as ct
from game.engine import GameError, validate_state, migrate_state
from tests.test_bank import opened, with_card, story, act, B


class AccountPurchases(unittest.TestCase):
    def test_explicit_account_logs_actual_balance_without_cash_or_debt(self):
        s = with_card(deposit=200)
        wallet = s['journey']['wallet']
        before_stats = copy.deepcopy(B(s)['stats'])
        self.assertEqual(bk.pay(s, 35, 'Áo mới', method='account')['method'], 'account')
        self.assertEqual((B(s)['balance'], s['journey']['wallet'], B(s)['card']['bal']), (165, wallet, 0))
        self.assertEqual(B(s)['stats'], before_stats)
        row = B(s)['log'][-1]
        self.assertEqual((row['acc'], row['amt'], row['bal']), ('acc', -35, 165))
        self.assertIn('Áo mới', row['text'])
        B(s).pop('ting', None)
        validate_state(s)

    def test_account_preference_is_saved_and_never_falls_back_when_short(self):
        s = with_card(deposit=20)
        s, _ = act(s, 'jr_bk_settings', pref='account')
        self.assertEqual(bk.public(s)['pref'], 'account')
        self.assertIn('account', bk.public(s)['prefs'])
        self.assertFalse(bk.can_pay(s, 21))
        before = copy.deepcopy(s)
        with self.assertRaises(GameError) as cm:
            bk.pay(s, 21, 'Mua hàng')
        self.assertEqual(cm.exception.code, 'not_enough')
        self.assertIn('Tài khoản', cm.exception.message)
        self.assertEqual(s, before)
        self.assertEqual(bk.pay(s, 20, 'Mua hàng')['method'], 'account')
        self.assertEqual(B(s)['balance'], 0)
        B(s).pop('ting', None)
        validate_state(migrate_state(copy.deepcopy(s)))

    def test_no_account_declines_even_with_cash(self):
        s = story(500)
        self.assertFalse(bk.can_pay(s, 30, 'account'))
        before = copy.deepcopy(s)
        with self.assertRaises(GameError):
            bk.pay(s, 30, 'Mua hàng', method='account')
        self.assertEqual(s, before)

    def test_old_preferences_do_not_implicitly_spend_account(self):
        s = with_card(deposit=200)
        self.assertEqual(bk.pay(s, 10, 'Mua hàng')['method'], 'cash')
        s['journey']['wallet'] = 0
        self.assertEqual(bk.pay(s, 10, 'Mua hàng')['method'], 'card')
        B(s)['pref'] = 'cash'
        self.assertFalse(bk.can_pay(s, 10))
        self.assertEqual(B(s)['balance'], 200)

    def test_joint_preference_and_busy_fallback_remain_unchanged(self):
        from game import couple as cp
        s = opened(deposit=200)
        B(s)['pref'] = 'joint'
        with patch.object(cp, 'joint_account', return_value={'balance':100, 'daily_left':100}), patch.object(cp, 'joint_spend', side_effect=GameError('busy', 'busy')):
            self.assertEqual(bk.pay(s, 10, 'Mua hàng')['method'], 'cash')
        self.assertEqual(B(s)['balance'], 200)
        B(s)['pref'] = 'account'
        with patch.object(cp, 'joint_account', side_effect=AssertionError('must not read joint fund')):
            self.assertEqual(bk.pay(s, 10, 'Mua hàng', no_joint=True)['method'], 'account')

    def test_marriage_account_effect_replay_cannot_charge_twice(self):
        s = opened(deposit=200)
        B(s)['pref'] = 'account'
        eff = mr._effect('ring:account:1', 'sid', 'wallet', -30, 'Mua nhẫn')
        self.assertTrue(mr._can_spend(s, 30))
        wallet = s['journey']['wallet']
        self.assertTrue(mr._spend(s, eff))
        self.assertFalse(mr._spend(s, eff))
        self.assertEqual((B(s)['balance'], s['journey']['wallet']), (170, wallet))
        self.assertFalse(mr._can_spend(s, 171))
        validate_state(s)

    def test_certificate_purchase_and_recomputed_command_are_atomic(self):
        s = opened(wallet=500, deposit=500)
        s, _ = act(s, 'jr_bk_settings', pref='account')
        before = copy.deepcopy(s)
        args = dict(cert=next(iter(ct.INDEX)), mode='class')
        paid, receipt = act(s, 'jr_cert_enrol', **args)
        retry, _ = act(s, 'jr_cert_enrol', **args)
        cost = paid['journey']['study']['fee']
        self.assertGreater(cost, 0)
        self.assertIn('tài khoản', receipt['message'])
        self.assertNotIn('quẹt thẻ', receipt['message'])
        self.assertEqual(B(paid)['balance'], 500-cost)
        self.assertEqual(paid['journey']['wallet'], 0)
        self.assertEqual(paid, retry)
        self.assertEqual(s, before)
        with self.assertRaises(GameError):
            act(paid, 'jr_cert_enrol', **args)
        self.assertEqual(B(paid)['balance'], 500-cost)

    def test_color_unlock_from_account_and_repeated_unlock_is_free(self):
        from game import wardrobe as wd
        s = opened(wallet=500, deposit=500)
        color = wd.COLORS[0]['id']
        paid, _ = act(s, 'jr_wd_unlock', color=color, pay='account')
        self.assertLess(B(paid)['balance'], 500)
        self.assertEqual(paid['journey']['wallet'], 0)
        again, _ = act(paid, 'jr_wd_unlock', color=color, pay='account')
        self.assertEqual(B(again)['balance'], B(paid)['balance'])

    def test_store_receipt_retry_debits_account_once(self):
        from game.storage import Store
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            store = Store(Path(tmp) / 'bank.db', story=True)
            try:
                token, _, _ = store.session()
                seed = opened(wallet=500, deposit=500)
                B(seed)['pref'] = 'account'
                mr._mutate(store, {store.key(token):lambda s:s.update(copy.deepcopy(seed))})
                rev = store.read(token)[1]
                args = (token, 'account-purchase-retry-0001', rev, None, 'jr_cert_enrol', dict(cert=next(iter(ct.INDEX)), mode='class'))
                first = store.command(*args)
                again = store.command(*args)
                self.assertTrue(again['replayed'])
                self.assertFalse(first['replayed'])
                self.assertEqual(first['state'], again['state'])
                s = store.read(token)[0]
                self.assertEqual(B(s)['balance'], 500-s['journey']['study']['fee'])
                self.assertEqual(s['journey']['wallet'], 0)
                validate_state(s)
            finally:
                store.close_pool()

    def test_browser_payment_chooser(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run([node, str(root/'tests/personal_payment.mjs')], cwd=root, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr+out.stdout)
        out = subprocess.run([node,str(root/'tests/payment_choice.mjs')],cwd=root,capture_output=True,text=True,timeout=60)
        self.assertEqual(out.returncode,0,out.stderr+out.stdout)


if __name__ == '__main__':
    unittest.main()
