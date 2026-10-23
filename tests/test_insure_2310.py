"""🛡️ 23/10: feedback #313 and #364 (game/rui.py, game/reno.py).

#313 "mua bảo hiểm nhà 100% tại sao nhà e lại phải tốn phí sửa nhà": a sự cố (dột, vỡ ống…) left for later lowers the
part in Sửa nhà, and Sửa nhà used to charge the full repair there, the insurance forgotten. Now that part costs what
Bảo hiểm & rủi ro would charge after the insurance (0 at 100 %), the sự cố closes at once; wear stays the player's,
and both screens get the policy's status (waiting days included).

#364 asked for a 100 % anti-pickpocket / anti-hack cover. Owner: "giảm còn loại 80% thôi chứ k có loại 100%": an 80 %
upgrade for the túi and the bank security, nothing stronger, no insurance tier for thefts or hacks."""
import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import reno as rn
from game import rui
from game.engine import GameError, public_state
from tests.test_rui import R, act, act_ok, days, grown, own_home, reno, warn


def broken_roof(full=True, on=True, wait_over=True, wallet=9000):
    """A lived-in nhà phố whose roof sự cố was left for later (Để đó), insured (or not) when it was warned."""
    s = grown(wallet)
    own_home(s, 'nha_pho')
    reno(s)
    if on:
        act_ok(s, 'jr_rui_pol', id='nha', on=True, full=full)
        if wait_over:
            days(s, rui.WAIT)
    warn(s, 'nha', 'dot', 'h1')
    days(s)
    act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='de')
    return s


def view(s):
    return public_state(s)['journey']['reno']


def part(v, pid):
    return next(p for p in v['parts'] if p['id'] == pid)


class HomeIncident(unittest.TestCase):
    def test_a_home_insured_at_100_pays_nothing_for_the_incident_in_sua_nha(self):
        s = broken_roof(full=True)
        self.assertEqual(rn.get(s)['parts']['roof']['c'], rn.WORN_AT - 15)
        v = view(s)
        self.assertEqual(v['incident'], {'roof': 100})
        self.assertEqual(part(v, 'roof')['fix'], 0)
        self.assertEqual(v['insure'], dict(pct=100, now=100, wait=0))
        wallet, bank = s['journey']['wallet'], s['journey']['bank']['balance']
        s, res = act(s, 'jr_reno_fix', part='roof', cost=0, confirm=True)
        self.assertIn('Bảo hiểm nhà trả 100%', res['message'])
        self.assertEqual((s['journey']['wallet'], s['journey']['bank']['balance']), (wallet, bank))
        self.assertEqual(rn.get(s)['parts']['roof']['c'], 100)
        self.assertNotIn('h1', R(s)['broken']['nha'])        # closed now: no second bill in Bảo hiểm & rủi ro
        self.assertFalse(rn._broken(s))                       # Ấm cúng is back at once
        self.assertEqual(view(s)['incident'], {})

    def test_sua_het_includes_the_insured_part_and_charges_only_the_wear(self):
        s = broken_roof(full=True)
        r = rn.get(s)
        r['parts']['wall']['c'] = 50                          # plain wear: never insured
        v = view(s)
        wall = rn.fix_cost('nha_pho', 'wall', 50)
        others = sum(rn.fix_cost('nha_pho', p, r['parts'][p]['c']) for p in rn.PART_IDS if p not in ('roof', 'wall'))
        self.assertEqual(part(v, 'wall')['fix'], wall)
        self.assertEqual(v['fix_all'], wall + others)
        have = s['journey']['wallet'] + s['journey']['bank']['balance']
        s, _ = act(s, 'jr_reno_fix', part='all', cost=v['fix_all'], confirm=True)
        self.assertEqual(s['journey']['wallet'] + s['journey']['bank']['balance'], have - v['fix_all'])
        self.assertTrue(all(x['c'] == 100 for x in rn.get(s)['parts'].values()))
        self.assertNotIn('h1', R(s)['broken']['nha'])

    def test_80_pays_its_share_never_more_than_the_plain_repair(self):
        s = broken_roof(full=False)
        b = R(s)['broken']['nha']['h1']
        plain = rn.fix_cost('nha_pho', 'roof', rn.get(s)['parts']['roof']['c'])
        v = view(s)
        self.assertEqual(v['incident'], {'roof': 80})
        self.assertEqual(part(v, 'roof')['fix'], min(plain, rui._part(b['c'], 80)))
        self.assertEqual(part(v, 'roof')['fix'], rui.broken_cost(s, 'nha', 'h1'))   # the same as Bảo hiểm & rủi ro

    def test_without_insurance_the_price_is_unchanged(self):
        s = broken_roof(on=False)
        v = view(s)
        self.assertEqual(v['incident'], {'roof': 0})
        self.assertIsNone(v['insure'])
        self.assertEqual(part(v, 'roof')['fix'], rn.fix_cost('nha_pho', 'roof', rn.get(s)['parts']['roof']['c']))
        reno(s, fix='roof')
        self.assertNotIn('h1', R(s)['broken']['nha'])

    def test_wear_is_never_insured(self):
        s = grown(9000)
        own_home(s, 'nha_pho')
        reno(s)
        act_ok(s, 'jr_rui_pol', id='nha', on=True, full=True)
        days(s, rui.WAIT)
        rn.get(s)['parts']['floor']['c'] = 40
        v = view(s)
        self.assertEqual(v['incident'], {})
        self.assertEqual(part(v, 'floor')['fix'], rn.fix_cost('nha_pho', 'floor', 40))
        self.assertIn('hao mòn', rui.POLICIES['nha']['what'])

    def test_the_waiting_days_are_shown_on_both_screens(self):
        s = grown(9000)
        own_home(s, 'nha_pho')
        reno(s)
        act_ok(s, 'jr_rui_pol', id='nha', on=True, full=True)
        self.assertEqual(view(s)['insure'], dict(pct=100, now=0, wait=rui.WAIT))
        row = next(p for p in rui.public(s)['pol'] if p['id'] == 'nha')
        self.assertEqual(row['wait'], rui.WAIT)
        warn(s, 'nha', 'dot', 'h1')
        self.assertEqual((rui.public(s)['warn']['pol_wait'], rui.public(s)['warn']['pol_pct']), (rui.WAIT, 100))
        days(s)
        c = rui.public(s)['card']
        self.assertEqual((c['cover'], c['pol_wait']), (0, rui.WAIT - 1))
        days(s, rui.WAIT)
        self.assertEqual(view(s)['insure'], dict(pct=100, now=100, wait=0))
        # 80 % → 100 %: 80 % still pays during the waiting days
        s = grown(9000)
        own_home(s, 'nha_pho')
        act_ok(s, 'jr_rui_pol', id='nha', on=True)
        days(s, rui.WAIT)
        act_ok(s, 'jr_rui_pol', id='nha', on=True, full=True)
        self.assertEqual(rui.policy_status(s, 'nha'), dict(pct=100, now=80, wait=rui.WAIT))

    def test_a_stale_quote_is_refused(self):
        s = broken_roof(full=True)
        plain = rn.fix_cost('nha_pho', 'roof', rn.get(s)['parts']['roof']['c'])
        with self.assertRaises(GameError):
            act(s, 'jr_reno_fix', part='roof', cost=plain, confirm=True)
        self.assertIn('h1', R(s)['broken']['nha'])


class TheftGuard(unittest.TestCase):
    def test_no_theft_protection_above_80(self):
        self.assertEqual(rui.THEFT_GUARD_MAX, 80)
        for k in ('moc', 'trom', 'hack', 'phat'):
            self.assertNotIn(k, rui.POLICY_OF)                  # no insurance for thefts or hacks, at any tier
        s = grown(5000)
        r = R(s)
        for pid in rui.POLICIES:
            rui._pols(r, pid)[pid] = 1
            r.setdefault('full', {})[pid] = 1
        for k in ('moc', 'trom', 'hack'):
            self.assertEqual(rui.cover(s, r, k, 100), 0, k)

    def test_upgrades_need_their_base_and_cut_80(self):
        s = grown(9000, bank=20000)
        r = R(s)
        self.assertEqual(rui.GEAR['tui_khoa']['up'], 'tui')
        self.assertEqual(rui.GEAR['hai_lop_80']['up'], 'hai_lop')
        self.assertGreater(rui.GEAR['hai_lop_80']['price'], rui.GEAR['hai_lop']['price'])
        self.assertGreater(rui.GEAR['tui_khoa']['price'], rui.GEAR['tui']['price'])
        for gid in ('tui_khoa', 'hai_lop_80'):
            with self.assertRaises(GameError):
                act(s, 'jr_rui_gear', id=gid)

        def odds(state, kind):
            return next(p for p, k, *_ in rui.candidates(state, R(state), 40) if k == kind)
        s['journey']['wallet'] = 9000
        base = {k: odds(s, k) for k in ('moc', 'hack')}
        act_ok(s, 'jr_rui_gear', id='tui')
        act_ok(s, 'jr_rui_gear', id='hai_lop')
        s['journey']['wallet'] = 9000
        self.assertEqual(odds(s, 'moc'), base['moc'] // 2)
        self.assertEqual(odds(s, 'hack'), base['hack'] * 2 // 5)
        act_ok(s, 'jr_rui_gear', id='tui_khoa')
        act_ok(s, 'jr_rui_gear', id='hai_lop_80')
        s['journey']['wallet'] = 9000
        self.assertEqual(odds(s, 'moc'), base['moc'] // 5)          # 80 %, never 100 %
        self.assertEqual(odds(s, 'hack'), base['hack'] // 5)
        self.assertGreater(odds(s, 'moc'), 0)
        self.assertGreater(odds(s, 'hack'), 0)
        self.assertEqual(R(s)['gear'], ['tui', 'hai_lop', 'tui_khoa', 'hai_lop_80'])
        cat = {g['id']: g for g in rui.catalogue()['gear']}
        self.assertEqual(cat['hai_lop_80']['up'], 'hai_lop')
        self.assertEqual(rui.catalogue()['rules']['guard_max'], 80)

    def test_a_pickpocket_warning_offers_the_next_step(self):
        s = grown(9000, bank=100)
        warn(s, 'moc', 'vi')
        self.assertIn('tui', [o['id'] for o in rui.warn_options(s, R(s))])
        R(s)['gear'].append('tui')
        self.assertIn('tui_khoa', [o['id'] for o in rui.warn_options(s, R(s))])
        act_ok(s, 'jr_rui_prevent', opt='tui_khoa')
        self.assertIn('tui_khoa', R(s)['gear'])
        R(s)['warn'] = None
        warn(s, 'moc', 'vi')
        self.assertFalse({'tui', 'tui_khoa'} & {o['id'] for o in rui.warn_options(s, R(s))})

    def test_an_old_save_with_the_old_gear_keeps_it(self):
        s = grown(9000)
        R(s)['gear'] = ['tui', 'khoa', 'ket', 'binh', 'hai_lop', 'diet_virus', 'bao_dong']
        old = copy.deepcopy(R(s)['gear'])
        days(s, 2)
        self.assertEqual(R(s)['gear'], old)


class Screens(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'node')
    def test_the_screens_on_real_views(self):
        insured = view(broken_roof(full=True))
        uninsured = view(broken_roof(on=False))
        s = grown(9000)
        own_home(s, 'nha_pho')
        reno(s)
        act_ok(s, 'jr_rui_pol', id='nha', on=True, full=True)
        waiting = view(s)
        warn(s, 'nha', 'dot', 'h1')
        rui_waiting = public_state(s)
        R(s)['warn'] = None
        R(s)['gear'] = ['tui']
        fixture = dict(insured=insured, uninsured=uninsured, waiting=waiting, rui_waiting=rui_waiting,
                       rui_based=public_state(s), rui_catalogue=rui.catalogue(), reno_catalogue=rn.catalogue())
        root = Path(__file__).resolve().parents[1]
        out = subprocess.run([shutil.which('node'), str(root / 'tests/insure_ui.mjs')], input=json.dumps(fixture),
                             capture_output=True, text=True, encoding='utf-8', cwd=root, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
