"""Bank hacking is a warned game risk; only the current account can lose xu."""
import copy
import json
import shutil
import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch

from game import bank as bk, rui
from game.engine import migrate_state, public_state, validate_state
from tests.test_rui import R, act, grown, warn


def mature(s):
    s['journey']['life_day'] += 1
    return rui.on_life_day(s)


class BankHackTests(unittest.TestCase):
    def test_only_funded_current_accounts_are_candidates(self):
        for balance, expected in ((None, False), (0, False), (10, False), (10000, True)):
            s = grown(day=40, bank=balance)
            if bk.get(s):
                bk.get(s)['demand'] = 20000
            self.assertEqual(any(k == 'hack' for _, k, _, _ in rui.candidates(s, R(s), 40)), expected)

    def test_actual_roll_can_warn_and_public_save_roundtrips(self):
        s = grown(day=40, bank=10000)
        cands = rui.candidates(s, R(s), 40)
        before = 0
        for p, k, _, _ in cands:
            if k == 'hack':
                break
            before += p
        with patch.object(rui, '_rng') as rng:
            rng.return_value.random.return_value = (before + 1) / 10000
            rng.return_value.choice.return_value = 1
            rui._roll(s, R(s), 40, [])
        self.assertIsNotNone(R(s)['warn'])
        self.assertEqual(R(s)['warn']['kind'], 'hack')
        self.assertEqual(public_state(s)['rui']['warn']['opts'][0]['cost'], 0)
        validate_state(s)
        migrate_state(s)
        self.assertEqual(R(s)['warn']['kind'], 'hack')

    def test_loss_debits_only_account_and_both_ledgers_once(self):
        s = grown(day=40, bank=10000)
        b = bk.get(s)
        b['demand'] = 20000
        other = copy.deepcopy({k: v for k, v in b.items() if k not in ('balance', 'log', 'seq')})
        cash = s['journey']['wallet']
        warn(s, 'hack', 'account')
        mature(s)
        self.assertEqual(b['balance'], 9200)
        self.assertEqual(s['journey']['wallet'], cash)
        self.assertEqual({k: v for k, v in b.items() if k not in ('balance', 'log', 'seq')}, other)
        self.assertEqual(R(s)['stats']['lost'], 800)
        self.assertEqual(R(s)['month']['lost'], 800)
        self.assertEqual(R(s)['card']['loss'], 800)
        self.assertEqual(b['log'][-1]['amt'], -800)
        self.assertEqual(R(s)['log'][-1]['a'], -800)
        self.assertEqual(public_state(s)['rui']['card']['kind'], 'hack')
        validate_state(s)
        snapshot = copy.deepcopy(s)
        rui.on_life_day(s)
        self.assertEqual(s, snapshot)
        cid = R(s)['card']['id']
        s, _ = act(s, 'jr_rui_choose', id=cid, choice='secure')
        s, _ = act(s, 'jr_rui_choose', id=cid, choice='secure')
        self.assertEqual(bk.get(s)['balance'], 9200)
        self.assertIsNone(R(s)['card'])

    def test_prevention_is_free_and_cancels_loss(self):
        s = grown(day=40, bank=10000)
        warn(s, 'hack', 'account')
        s, _ = act(s, 'jr_rui_prevent', opt='secure')
        s, _ = act(s, 'jr_rui_prevent', opt='secure')
        R(s)['next_ok'] = 999
        mature(s)
        self.assertIsNone(R(s)['card'])
        self.assertEqual(bk.get(s)['balance'], 10000)
        self.assertEqual(s['journey']['wallet'], 2000)
        self.assertEqual(R(s)['stats']['prevented'], 1)

    def test_no_fallback_after_account_emptied(self):
        s = grown(day=40, bank=10000)
        warn(s, 'hack', 'account')
        bk.get(s)['balance'] = 0
        mature(s)
        self.assertEqual(s['journey']['wallet'], 2000)
        self.assertEqual(bk.get(s)['balance'], 0)
        self.assertIsNone(R(s)['card'])
        self.assertEqual(R(s)['stats']['fizzled'], 1)

    def test_loss_caps_and_current_balance(self):
        for balance, expected in ((1000000, 3000), (10000, 800), (100, 8)):
            s = grown(day=40, bank=10000)
            warn(s, 'hack', 'account')
            bk.get(s)['balance'] = balance
            mature(s)
            self.assertEqual(R(s)['card']['loss'], expected)
            self.assertEqual(bk.get(s)['balance'], balance - expected)
        s = grown(wallet=0, day=40, bank=400)
        warn(s, 'hack', 'account')
        mature(s)
        self.assertEqual(R(s)['card']['loss'], 8)  # 8% of wealth above 300
        s = grown(day=40, bank=10000)
        warn(s, 'hack', 'account')
        m = rui._month(s, R(s), 41)
        m['lost'] = m['w'] * rui.MONTH_PCT // 100 - 7
        mature(s)
        self.assertEqual(R(s)['card']['loss'], 7)

    def test_offline_reads_do_not_fire_warning(self):
        s = grown(day=40, bank=10000)
        warn(s, 'hack', 'account')
        snapshot = copy.deepcopy(s)
        for _ in range(3):
            public_state(s)
        self.assertEqual(s, snapshot)

    def test_unanswered_card_expires_without_second_debit(self):
        s = grown(day=40, bank=10000)
        warn(s, 'hack', 'account')
        mature(s)
        R(s)['next_ok'] = 999
        for _ in range(rui.CARD_DAYS):
            mature(s)
        self.assertIsNone(R(s)['card'])
        self.assertEqual(bk.get(s)['balance'], 9200)
        self.assertEqual(R(s)['stats']['events'], 1)
        validate_state(s)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_rendered_card_names_account_loss_and_free_prevention(self):
        s = grown(day=40, bank=10000)
        warn(s, 'hack', 'account')
        warning = public_state(s)
        mature(s)
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run([shutil.which('node'), str(root/'tests/bank_hack_ui.mjs')],
                             input=json.dumps(dict(warning=warning, loss=public_state(s), catalogue=rui.catalogue())),
                             capture_output=True, text=True, encoding='utf-8', cwd=root, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr+out.stdout)


if __name__ == '__main__':
    unittest.main()
