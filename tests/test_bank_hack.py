"""Bank hacking is a warned game risk; only the current account can lose xu."""
import copy
import json
import shutil
import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch

from game import bank as bk, rui
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_rui import R, act, grown, warn


def mature(s):
    s['journey']['life_day'] += 1
    return rui.on_life_day(s)


class BankHackTests(unittest.TestCase):
    def reported_hack(self, roll=1):
        s = grown(day=40, bank=10000)
        warn(s, 'hack', 'account')
        mature(s)
        cid = R(s)['card']['id']
        with patch.object(rui, '_rng') as rng:
            rng.return_value.randint.return_value = roll
            s, _ = act(s, 'jr_rui_choose', id=cid, choice='secure')
        R(s)['next_ok'] = 999
        return s, cid

    def test_police_refund_full_loss_to_account_after_two_days_once(self):
        s, cid = self.reported_hack()
        self.assertEqual(len(R(s)['hack_back']), 1)
        s, _ = act(s, 'jr_rui_choose', id=cid, choice='secure')
        self.assertEqual(len(R(s)['hack_back']), 1)
        self.assertEqual(bk.get(s)['balance'], 9200)
        mature(s)
        self.assertEqual(bk.get(s)['balance'], 9200)
        notes = mature(s)
        self.assertEqual(bk.get(s)['balance'], 10000)
        self.assertEqual(s['journey']['wallet'], 2000)
        self.assertTrue(any('bắt được' in n for n in notes))
        self.assertEqual((bk.get(s)['log'][-1]['acc'], bk.get(s)['log'][-1]['amt']), ('acc', 800))
        self.assertEqual(R(s)['log'][-1]['a'], 800)
        self.assertEqual(R(s)['stats']['back'], 800)
        self.assertEqual(R(s)['month']['lost'], 800)
        self.assertEqual(R(s)['hack_back'], [])
        snapshot = copy.deepcopy(s)
        rui.on_life_day(s)
        self.assertEqual(s, snapshot)
        mature(s)
        self.assertEqual(bk.get(s)['balance'], 10000)
        validate_state(s)

    def test_unsolved_case_reports_no_refund(self):
        s, _ = self.reported_hack(100)
        mature(s)
        notes = mature(s)
        self.assertEqual(bk.get(s)['balance'], 9200)
        self.assertEqual(R(s).get('hack_back'), [])
        self.assertTrue(any('chưa bắt được' in n for n in notes))
        self.assertEqual(R(s)['stats']['back'], 0)

    def test_probability_boundary_and_hidden_result(self):
        for roll, amount in ((30, 800), (31, 0)):
            s, _ = self.reported_hack(roll)
            self.assertEqual(R(s)['hack_back'][0]['amount'], amount)
            self.assertEqual(public_state(s)['rui']['hack_pending'], dict(n=1, days=2))
        states = []
        for _ in range(2):
            s = grown(day=40, bank=10000)
            warn(s, 'hack', 'account')
            mature(s)
            s, _ = act(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='secure')
            states.append(s)
        self.assertEqual(states[0], states[1])

    def test_bank_refund_does_not_overwrite_cash_theft_recovery(self):
        s, _ = self.reported_hack()
        R(s)['back'] = dict(day=43, amount=73)
        mature(s)
        mature(s)
        self.assertEqual(bk.get(s)['balance'], 10000)
        self.assertEqual(s['journey']['wallet'], 2073)
        self.assertEqual(R(s)['stats']['back'], 873)

    def test_pending_refund_roundtrip_and_missing_account_preserves_claim(self):
        s, _ = self.reported_hack()
        s = migrate_state(json.loads(json.dumps(s)))
        validate_state(s)
        saved_bank = s['journey'].pop('bank')
        mature(s)
        mature(s)
        self.assertEqual(len(R(s)['hack_back']), 1)
        self.assertEqual(s['journey']['wallet'], 2000)
        s['journey']['bank'] = saved_bank
        mature(s)
        self.assertEqual(bk.get(s)['balance'], 10000)
        self.assertEqual(R(s)['hack_back'], [])

    def test_bad_or_duplicate_recovery_claims_are_rejected(self):
        s = grown(day=40, bank=10000)
        validate_state(s)  # old save without the optional queue
        good = dict(id='r1', day=43, amount=800)
        for queue in (None, [dict(good, amount=-1)], [dict(good, amount=True)],
                      [dict(good, day='43')], [good, good], [dict(good, amount=3001)]):
            x = copy.deepcopy(s)
            R(x)['hack_back'] = queue
            with self.assertRaises(GameError):
                validate_state(x)

    def test_full_account_defers_refund_without_losing_the_claim(self):
        s, _ = self.reported_hack()
        bk.get(s)['balance'] = bk.BAL_MAX
        mature(s)
        mature(s)
        validate_state(s)
        self.assertEqual(len(R(s)['hack_back']), 1)
        self.assertEqual(bk.get(s)['balance'], bk.BAL_MAX)
        bk.get(s)['balance'] -= 800
        mature(s)
        self.assertEqual(bk.get(s)['balance'], bk.BAL_MAX)
        self.assertEqual(R(s)['hack_back'], [])

    def test_full_case_queue_retains_card_and_can_resume_after_refund(self):
        s = grown(day=40, bank=10000)
        warn(s, 'hack', 'account')
        mature(s)
        cid = R(s)['card']['id']
        R(s)['hack_back'] = [dict(id=f'old{i}', day=41, amount=800) for i in range(64)]
        bk.get(s)['balance'] = bk.BAL_MAX
        validate_state(s)
        s, _ = act(s, 'jr_rui_choose', id=cid, choice='secure')
        self.assertEqual(R(s)['card']['id'], cid)
        self.assertEqual(len(R(s)['hack_back']), 64)
        for _ in range(rui.CARD_DAYS):
            mature(s)
        validate_state(s)
        self.assertEqual(R(s)['card']['id'], cid)
        bk.get(s)['balance'] -= 800
        mature(s)
        self.assertIsNone(R(s)['card'])
        self.assertEqual(len(R(s)['hack_back']), 64)
        self.assertTrue(any(x['id'] == cid for x in R(s)['hack_back']))
        validate_state(s)

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
        loss = public_state(s)
        s, _ = act(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='secure')
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run([shutil.which('node'), str(root/'tests/bank_hack_ui.mjs')],
                             input=json.dumps(dict(warning=warning, loss=loss, pending=public_state(s), catalogue=rui.catalogue())),
                             capture_output=True, text=True, encoding='utf-8', cwd=root, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr+out.stdout)


if __name__ == '__main__':
    unittest.main()
