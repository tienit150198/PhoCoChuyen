"""Wealth-sensitive personal risks preserve warnings, protection and loss budgets."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from game import bank as bk, rui
from game.engine import migrate_state, public_state, validate_state
from tests.test_rui import R, act, grown, own_home, warn
from tests.test_bank_hack import mature


class WealthRiskTests(unittest.TestCase):
    def test_wealth_bands_raise_only_money_theft_odds(self):
        rows = []
        for total in (9999, 10000, 100000, 1000000):
            s = grown(wallet=2000, bank=total - 2000, day=40)
            own_home(s)
            rows.append({k: p for p, k, _, _ in rui.candidates(s, R(s), 40)})
        for kind in ('hack', 'trom', 'moc'):
            # The owned home now counts too: both first fixtures exceed 10k.
            self.assertEqual([x[kind] for x in rows],
                             [rows[0][kind] * n // 150 for n in (150, 150, 200, 300)])
        for kind in ('om', 'nha'):
            self.assertEqual(len({x[kind] for x in rows}), 1)

    def test_millionaire_can_lose_substantial_cash_or_account_funds(self):
        for kind in ('hack', 'trom'):
            s = grown(wallet=1000000 if kind == 'trom' else 0,
                      bank=1000000 if kind == 'hack' else 0, day=40)
            warn(s, kind, 'account' if kind == 'hack' else 'nha')
            mature(s)
            self.assertEqual(R(s)['card']['loss'], 79976)
            self.assertEqual(rui.wealth(s), 920024)
            validate_state(s)
            snapshot = copy.deepcopy(s)
            rui.on_life_day(s)
            self.assertEqual(s, snapshot)

    def test_rich_losses_obey_month_budget_and_two_event_limit(self):
        s = grown(wallet=0, bank=1000000, day=40)
        month = rui._month(s, R(s), 41)
        month['lost'] = month['w'] * rui.MONTH_PCT // 100 - 17
        warn(s, 'hack', 'account')
        mature(s)
        self.assertEqual(R(s)['card']['loss'], 17)
        R(s)['card'] = None
        month['n'] = rui.MONTH_EVENTS
        warn(s, 'hack', 'account')
        before = bk.get(s)['balance']
        mature(s)
        self.assertEqual(bk.get(s)['balance'], before)
        self.assertIsNone(R(s)['card'])

    def test_protection_purchase_is_once_and_changes_odds_or_loss(self):
        s = grown(wallet=200000, bank=1000000, day=40)
        own_home(s)
        odds = {k: p for p, k, _, _ in rui.candidates(s, R(s), 40)}
        loss = rui._projected(s, R(s), 'hack', 'account', None)
        for gid in ('hai_lop', 'diet_virus', 'bao_dong'):
            s, _ = act(s, 'jr_rui_gear', id=gid)
            before = rui.wealth(s)
            s, result = act(s, 'jr_rui_gear', id=gid)
            self.assertTrue(result.get('duplicate'))
            self.assertEqual(rui.wealth(s), before)
        after = {k: p for p, k, _, _ in rui.candidates(s, R(s), 40)}
        self.assertEqual(after['hack'], odds['hack'] * 2 // 5)
        self.assertEqual(after['trom'], odds['trom'] // 2)
        self.assertEqual(rui._projected(s, R(s), 'hack', 'account', None), loss // 2)
        R(s)['gear'].extend(['khoa', 'ket'])
        stacked = {k: p for p, k, _, _ in rui.candidates(s, R(s), 40)}
        self.assertEqual(stacked['trom'], odds['trom'] // 5)
        no_safe = copy.deepcopy(s)
        R(no_safe)['gear'].remove('ket')
        self.assertEqual(rui._theft(s, R(s), 'trom'), rui._theft(no_safe, R(no_safe), 'trom') // 4)
        validate_state(migrate_state(json.loads(json.dumps(s))))

    def test_large_hack_refund_roundtrips_and_returns_full_loss_once(self):
        s = grown(wallet=0, bank=1000000, day=40)
        warn(s, 'hack', 'account')
        mature(s)
        loss = R(s)['card']['loss']
        self.assertGreater(loss, 3000)
        with patch.object(rui, '_rng') as rng:
            rng.return_value.randint.return_value = 1
            s, _ = act(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='secure')
        self.assertEqual(R(s)['hack_back'][0]['amount'], loss)
        s = migrate_state(json.loads(json.dumps(s)))
        validate_state(s)
        R(s)['next_ok'] = 999
        mature(s)
        mature(s)
        self.assertEqual(bk.get(s)['balance'], 1000000)
        mature(s)
        self.assertEqual(bk.get(s)['balance'], 1000000)

    def test_newcomers_offline_reads_and_free_prevention_remain_safe(self):
        s = grown(wallet=0, bank=1000000, day=14, chapter=2)
        self.assertFalse(rui.eligible(s, R(s), 14))
        s = grown(wallet=0, bank=1000000, day=40)
        warn(s, 'hack', 'account')
        snapshot = copy.deepcopy(s)
        for _ in range(3):
            public_state(s)
        self.assertEqual(s, snapshot)
        s, _ = act(s, 'jr_rui_prevent', opt='secure')
        mature(s)
        self.assertEqual(bk.get(s)['balance'], 1000000)
        self.assertEqual(R(s)['stats']['prevented'], 1)

    def test_public_risk_profile_explains_current_limits_without_mutation(self):
        s = grown(wallet=0, bank=1000000, day=40)
        snapshot = copy.deepcopy(s)
        profile = rui.public(s).get('wealth_risk')
        self.assertIsNotNone(profile)
        self.assertEqual(profile['threshold'], 1000000)
        self.assertEqual(profile['odds_pct'], 300)
        self.assertEqual(profile['hack_max'], 80000)
        self.assertEqual(profile['event_max'], 79976)
        self.assertEqual(s, snapshot)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_ui_shows_rich_limits_and_purchasable_protection(self):
        s = grown(wallet=0, bank=1000000, day=40)
        root = Path(__file__).resolve().parents[1]
        script = """
const assert=require('node:assert/strict'),fs=require('node:fs');
const source=fs.readFileSync('public/js/v4/rui.js','utf8')
  .replace(/^import .*;\\r?\\n/gm,'').replace(/^export /gm,'');
const {S,ruiPage}=new Function('icon','esc',source+'\\nreturn {S,ruiPage};')(()=>'',String);
const f=JSON.parse(fs.readFileSync(0,'utf8'));
S.env={api:{state:{rui:f.rui},content:{journey:{rui:f.catalogue}}}};
const html=ruiPage();
assert.match(html,/tối đa 80\\.000 xu/);
assert.match(html,/Tài sản từ 1\\.000\\.000 xu/);
assert.match(html,/3 lần/);
for(const id of ['hai_lop','diet_virus','bao_dong'])assert.ok(html.includes('data-id="'+id+'"'));
assert.match(html,/Không truy thu rủi ro trong thời gian offline/);
"""
        out = subprocess.run([shutil.which('node'), '-e', script],
                             input=json.dumps(dict(rui=rui.public(s), catalogue=rui.catalogue())),
                             capture_output=True, text=True, encoding='utf-8', cwd=root, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
