"""🛡️ Player #275 (08/10): a gói trọn 100 % next to the gói thường 80 % for every policy, at exactly twice the price,
and 💡 Bảo hiểm điện nước (game/rui.py). Existing policies keep working as bought; switching tiers mid-term; claims say
the % paid; the điện nước mishaps on their own random stream (the other risks roll exactly as before); the save checks;
and every save this build writes is accepted by the 1.9.20 server (MNL_OLD_TREE_1920, else ../_rel1920/mot-ngay-lam-nghe)."""
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from game import rui
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_rui import R, act, act_ok, days, grown, own_car, own_home, warn

ROOT = Path(__file__).resolve().parents[1]


def renter(wallet=5000, **kw):
    s = grown(wallet, **kw)
    act_ok(s, 'jr_home_rent', kind='tro_moi', confirm=True)
    return s


def dn_warn(s, sub='bom', lead=1, cost=None):
    """Put a điện nước warning on the save, as _dn_day would."""
    day = s['journey']['life_day']
    R(s)['dn'] = dict(warn=dict(sub=sub, day=day + lead, at=day, cost=rui._dn_cost(s, sub) if cost is None else cost), card=None)


def head_rui():
    """game/rui.py as released in 1.9.20 (git HEAD of origin/main ad4e716), loaded beside the new one."""
    src = subprocess.run(['git', 'show', 'ad4e716:game/rui.py'], cwd=ROOT, capture_output=True, encoding='utf-8')
    if src.returncode:
        return None
    path = Path(tempfile.mkdtemp(prefix='mnl-rui1920-')) / 'rui_1920.py'
    path.write_text(src.stdout, encoding='utf-8')
    spec = importlib.util.spec_from_file_location('game._rui_1920', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Tiers(unittest.TestCase):
    def test_every_policy_has_two_tiers_the_full_one_twice_the_price(self):
        s = renter(9000, bank=2000)
        own_car(s, 'xe_ga')
        own_home(s, 'nha_pho', live=False)
        rows = {p['id']: p for p in rui.public(s)['pol']}
        self.assertEqual(set(rows), {'yte', 'xe', 'nha', 'dn'})
        for pid, row in rows.items():
            self.assertTrue(row['can'], pid)
            self.assertEqual(row['full_month'], 2 * row['month'], pid)
            self.assertGreater(row['month'], 0, pid)
        cat = {p['id']: p for p in rui.catalogue()['policies']}
        self.assertEqual({(p['cover'], p['full']) for p in cat.values()}, {(80, 100)})
        # What is accrued a life day: exactly twice (thousandths of a xu), for each policy.
        a, b = copy.deepcopy(s), copy.deepcopy(s)
        for pid in rows:
            act_ok(a, 'jr_rui_pol', id=pid, on=True)
            act_ok(b, 'jr_rui_pol', id=pid, on=True, full=True)
            self.assertEqual(rui._accrue(b, R(b), pid), 2 * rui._accrue(a, R(a), pid), pid)
        acc_a, acc_b = R(a)['acc'], R(b)['acc']
        days(a)
        days(b)
        self.assertEqual(R(b)['acc'] - acc_b, 2 * (R(a)['acc'] - acc_a))
        self.assertEqual(R(a)['pol'].keys(), {'yte', 'xe', 'nha'})        # dn lives in pol2 (the 1.9.20 validator)
        self.assertEqual(R(a)['pol2'], {'dn': R(a)['pol']['yte']})
        self.assertNotIn('full', R(a))
        self.assertEqual(set(R(b)['full']), set(rows))

    def test_a_policy_bought_before_this_build_keeps_working_as_bought(self):
        s = grown(3000)
        own_car(s, 'o_to_mini')
        day = s['journey']['life_day']
        R(s)['pol'] = {'xe': day - 10}                         # a 1.9.20 save: no 'full', no 'pol2'
        validate_state(s)
        self.assertEqual(rui.cover(s, R(s), 'xe', day), 80)
        self.assertEqual(rui._accrue(s, R(s), 'xe'), rui.premium_milli(s, 'xe'))
        row = next(p for p in rui.public(s)['pol'] if p['id'] == 'xe')
        self.assertTrue(row['on'])
        self.assertNotIn('full', row)
        res = act_ok(s, 'jr_rui_pol', id='xe', on=True)       # an older client: "buy" again, no tier: nothing changes
        self.assertTrue(res.get('duplicate'))
        self.assertEqual(R(s)['pol'], {'xe': day - 10})

    def test_claims_at_100_cost_nothing_and_say_so(self):
        s = grown(3000)
        own_car(s, 'o_to_mini')
        act_ok(s, 'jr_rui_pol', id='xe', on=True, full=True)
        days(s, rui.WAIT)
        warn(s, 'xe', 'car', 'o_to_mini')
        days(s)
        c = public_state(s)['rui']['card']
        self.assertEqual(c['cover'], 100)
        self.assertEqual(next(o for o in c['opts'] if o['id'] == 'sua')['cost'], 0)
        w = s['journey']['wallet']
        res = act_ok(s, 'jr_rui_choose', id=c['id'], choice='sua')
        self.assertEqual(s['journey']['wallet'], w)
        self.assertIn('Bảo hiểm trả 100%', res['message'])
        self.assertEqual(R(s)['stats']['covered'], 132)
        # Left broken, then fixed from the page: still free.
        R(s)['month']['n'] = 0
        warn(s, 'xe', 'car', 'o_to_mini')
        days(s)
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='de')
        self.assertEqual(rui.broken_cost(s, 'xe', 'o_to_mini'), 0)
        w = s['journey']['wallet']
        res = act_ok(s, 'jr_rui_fix', kind='xe', ref='o_to_mini')
        self.assertIn('bảo hiểm trả 100%', res['message'].lower())
        self.assertEqual(s['journey']['wallet'], w)

    def test_claims_at_80_say_the_percent(self):
        s = grown(3000)
        own_car(s, 'o_to_mini')
        act_ok(s, 'jr_rui_pol', id='xe', on=True)
        days(s, rui.WAIT)
        warn(s, 'xe', 'car', 'o_to_mini')
        days(s)
        res = act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='sua')
        self.assertIn('bảo hiểm trả 80%', res['message'])

    def test_switch_up_mid_term_and_back(self):
        s = grown(3000)
        act_ok(s, 'jr_rui_pol', id='yte', on=True)
        start = s['journey']['life_day']
        days(s, rui.WAIT + 1)
        res = act_ok(s, 'jr_rui_pol', id='yte', on=True, full=True)
        up = s['journey']['life_day']
        self.assertIn('100%', res['message'])
        self.assertEqual(R(s)['pol']['yte'], start)              # the policy is the same one: no new waiting days
        self.assertEqual(R(s)['full']['yte'], up)
        row = next(p for p in rui.public(s)['pol'] if p['id'] == 'yte')
        self.assertEqual((row.get('full'), row.get('wait_full'), row.get('wait')), (True, rui.WAIT, None))
        self.assertEqual(rui.cover(s, R(s), 'om', up), 80)          # warned before the 100 % starts: 80 %
        self.assertEqual(rui.cover(s, R(s), 'om', up + rui.WAIT), 100)
        self.assertEqual(rui._accrue(s, R(s), 'yte'), 2 * rui.premium_milli(s, 'yte'))   # the new price from today
        self.assertTrue(act_ok(s, 'jr_rui_pol', id='yte', on=True, full=True).get('duplicate'))
        res = act_ok(s, 'jr_rui_pol', id='yte', on=True, full=False)
        self.assertIn('80%', res['message'])
        self.assertNotIn('yte', R(s).get('full', {}))
        self.assertEqual(rui.cover(s, R(s), 'om', up + rui.WAIT), 80)
        self.assertEqual(R(s)['pol']['yte'], start)
        act_ok(s, 'jr_rui_pol', id='yte', on=True, full=True)
        act_ok(s, 'jr_rui_pol', id='yte', on=False)                  # stopped: both marks go
        self.assertEqual((R(s)['pol'], R(s).get('full')), ({}, {}))
        validate_state(s)

    def test_refusals(self):
        s = grown(3000)
        for bad in (dict(id='yte', on=True, full='yes'), dict(id='yte', on=True, full=1), dict(id='yte', on=True, tier=100),
                    dict(id='dn', on=True)):   # dn: Bà Tám's attic, nothing of your own to insure
            with self.assertRaises(GameError, msg=bad):
                act(s, 'jr_rui_pol', **bad)

    def test_a_bill_that_cannot_be_paid_stops_every_tier(self):
        s = renter(5000, bank=0)
        for pid in ('yte', 'dn'):
            act_ok(s, 'jr_rui_pol', id=pid, on=True, full=True)
        s['journey']['wallet'] = 0
        days(s, rui.MONTH_DAYS)
        self.assertEqual(R(s)['pol'], {})
        self.assertNotIn('pol2', R(s))
        self.assertNotIn('full', R(s))

    def test_a_stale_mark_from_an_older_server_is_dropped(self):
        s = grown(3000)
        day = s['journey']['life_day']
        R(s)['pol'] = {'yte': day}
        R(s)['full'] = {'yte': day - 5, 'xe': day - 5}   # the old server stopped them and bought yte again at 80 %
        validate_state(s)
        self.assertFalse(rui.is_full(R(s), 'yte'))
        self.assertEqual(rui._accrue(s, R(s), 'yte'), rui.premium_milli(s, 'yte'))
        days(s)
        self.assertEqual(R(s)['full'], {})


class DienNuoc(unittest.TestCase):
    def test_where_it_can_be_bought(self):
        s = grown(3000)
        self.assertFalse(rui.insurable(s, 'dn'))                    # Bà Tám's attic
        self.assertTrue(rui.insurable(renter(3000), 'dn'))
        s = grown(3000)
        own_home(s, 'can_ho_mini', live=False)
        self.assertTrue(rui.insurable(s, 'dn'))                     # a home owned (its vỡ ống, chập điện)

    def test_a_mishap_warned_fixed_and_covered(self):
        s = renter(5000)
        act_ok(s, 'jr_rui_pol', id='dn', on=True)
        days(s, rui.WAIT)
        dn_warn(s, 'nong')
        v = public_state(s)['rui']['warn']
        self.assertEqual((v['kind'], v['title']), ('dn', 'Điện nước trong nhà'))
        days(s)
        c = public_state(s)['rui']['card']
        self.assertEqual((c['kind'], c['title'], c['cover']), ('dn', 'Bình nóng lạnh hỏng', 80))
        self.assertEqual([o['id'] for o in c['opts']], ['tho', 'chiu'])
        cost = R(s)['dn']['card']['cost']
        w = s['journey']['wallet']
        res = act_ok(s, 'jr_rui_choose', id=c['id'], choice='tho')
        self.assertEqual(w - s['journey']['wallet'], cost - cost * 80 // 100)
        self.assertIn('bảo hiểm trả 80%', res['message'])
        self.assertIsNone(R(s)['dn']['card'])
        self.assertEqual(s['journey']['history'][-1]['kind'], 'home')
        validate_state(s)

    def test_full_tier_prevention_and_default(self):
        s = renter(5000)
        act_ok(s, 'jr_rui_pol', id='dn', on=True, full=True)
        days(s, rui.WAIT)
        dn_warn(s, 'bom')
        w = s['journey']['wallet']
        opt = public_state(s)['rui']['warn']['opts'][0]
        self.assertEqual((opt['id'], opt['cost']), ('kiem', 0))
        res = act_ok(s, 'jr_rui_prevent', opt='kiem')
        self.assertIn('100%', res['message'])
        self.assertEqual((s['journey']['wallet'], R(s)['dn']['warn']), (w, None))
        R(s)['next_ok'] = 0
        dn_warn(s, 'lanh')
        days(s)                                                    # a card, not answered: "chịu khó" after CARD_DAYS
        self.assertIsNotNone(R(s)['dn']['card'])
        notes = days(s, rui.CARD_DAYS)
        self.assertIsNone(R(s)['dn']['card'])
        self.assertTrue(any('Chưa chọn nên tự động' in n for n in notes), notes)
        self.assertFalse([x for x in s['journey']['history'] if x['label'].startswith('Sửa điện nước')])

    def test_it_also_covers_a_homes_pipes_and_wiring(self):
        s = grown(5000)
        own_home(s, 'nha_pho')
        act_ok(s, 'jr_rui_pol', id='dn', on=True, full=True)
        day = s['journey']['life_day'] + rui.WAIT
        self.assertEqual(rui.cover(s, R(s), 'nha', day, 'ong'), 100)
        self.assertEqual(rui.cover(s, R(s), 'nha', day, 'dien'), 100)
        self.assertEqual(rui.cover(s, R(s), 'nha', day, 'dot'), 0)
        act_ok(s, 'jr_rui_pol', id='nha', on=True)
        day += rui.WAIT
        self.assertEqual(rui.cover(s, R(s), 'nha', day, 'ong'), 100)   # the better of the two
        self.assertEqual(rui.cover(s, R(s), 'nha', day, 'chay'), 80)
        days(s, 2 * rui.WAIT)
        warn(s, 'nha', 'dien', 'h1')
        days(s)
        self.assertEqual(R(s)['card']['cover'], 100)
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='de')
        self.assertEqual(rui.broken_cost(s, 'nha', 'h1'), 0)

    def test_one_thing_at_a_time(self):
        s = renter(5000)
        dn_warn(s, 'o')
        r = R(s)
        r['next_ok'] = 0
        notes = []
        rui._roll(s, r, s['journey']['life_day'], notes)            # the other risks wait for the điện nước one
        self.assertIsNone(r['warn'])
        warn(s, 'om', 'cam')                                        # an open card first: the điện nước waits a day
        days(s)
        self.assertIsNotNone(R(s)['card'])
        self.assertIsNotNone(R(s)['dn']['warn'])
        self.assertEqual(public_state(s)['rui']['card']['kind'], 'om')
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='nghi')
        days(s)
        self.assertEqual(public_state(s)['rui']['card']['kind'], 'dn')

    def test_the_other_risks_roll_exactly_as_in_1920(self):
        old = head_rui()
        if old is None:
            self.skipTest('no git history')
        for seed in range(60):
            s = renter(4000 + 97 * seed, seed=seed, day=30 + seed % 20, bank=1500)
            if seed % 3 == 0:
                own_car(s, 'xe_ga')
            if seed % 4 == 0:
                own_home(s, 'nha_pho', live=False)
            day = s['journey']['life_day']
            a, b = copy.deepcopy(s), copy.deepcopy(s)
            ra, rb = R(a), R(b)
            ra['next_ok'] = rb['next_ok'] = 0
            old._roll(a, ra, day, [])
            rui._roll(b, rb, day, [])
            self.assertEqual(ra['warn'], rb['warn'], seed)
            self.assertEqual(old.candidates(a, ra, day), rui.candidates(b, rb, day))
        # Not living anywhere of your own (Bà Tám's attic): the whole life-day tick is the 1.9.20 one.
        for seed in range(4):
            a = grown(6000, seed=seed, day=30, bank=2000)
            b = copy.deepcopy(a)
            for _ in range(25):
                for x in (a, b):
                    x['journey']['life_day'] += 1
                old.on_life_day(a)
                rui.on_life_day(b)
                self.assertEqual(R(a), R(b))

    def test_low_odds(self):
        n = hits = 0
        for seed in range(40):
            s = renter(6000, seed=seed, day=40, bank=2000)
            r = R(s)
            for d in range(40, 70):
                x = copy.deepcopy(s)
                rx = R(x)
                rx['next_ok'] = 0
                rx['month'] = dict(i=(d - 1) // rui.MONTH_DAYS, w=10**5, lost=0, n=0)
                rui._dn_day(x, rx, d, [])
                n += 1
                hits += bool(rx.get('dn'))
        self.assertLess(hits / n, rui.DN_P / 10000 * 2)
        self.assertGreater(hits, 0)


class Saves(unittest.TestCase):
    def test_bad_blocks_are_refused(self):
        s = renter(5000)
        act_ok(s, 'jr_rui_pol', id='dn', on=True, full=True)
        dn_warn(s)
        validate_state(s)
        for k, bad in (('pol2', {'yte': 3}), ('pol2', {'xx': 3}), ('pol2', []), ('full', {'zz': 3}), ('full', {'yte': 0}),
                       ('dn', {'warn': {'sub': 'zz', 'day': 3, 'at': 3, 'cost': 1}, 'card': None}),
                       ('dn', {'warn': None, 'card': {'id': 'r1', 'sub': 'bom', 'day': 3, 'cost': 5, 'cover': 120}}),
                       ('dn', {'x': None})):
            x = copy.deepcopy(s)
            R(x)[k] = bad
            with self.assertRaises(GameError, msg=f'{k}={bad}'):
                validate_state(x)
        self.assertNotIn('dn', R(s)['pol'])

    def test_views_stay_small(self):
        s = renter(9000, bank=3000)
        own_car(s, 'xe_ga')
        own_home(s, 'nha_pho', live=False)
        for pid in rui.POLICIES:
            act_ok(s, 'jr_rui_pol', id=pid, on=True, full=pid != 'xe')
        dn_warn(s)
        days(s)
        v = public_state(s)['rui']
        self.assertEqual(v['card']['kind'], 'dn')
        self.assertLess(len(json.dumps(v, ensure_ascii=False)), 1500)


class OldServer1920(unittest.TestCase):
    """The 1.9.20 server (the one before this build) accepts and keeps every save this build writes."""

    def old_tree(self):
        old = os.environ.get('MNL_OLD_TREE_1920') or str(ROOT.parent / '_rel1920' / 'mot-ngay-lam-nghe')
        if not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no 1.9.20 tree (MNL_OLD_TREE_1920)')
        return old

    def run_old(self, old, prog, s):
        env = dict(os.environ, PYTHONPATH=old + os.pathsep + os.environ.get('PYTHONPATH', ''))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    def saves(self):
        """Every new field: tiers, the điện nước policy, its warning, its card, a 100 % claim, a switch down."""
        out = []
        s = renter(9000, bank=3000)
        own_car(s, 'xe_ga')
        own_home(s, 'nha_pho', live=False)
        for pid in rui.POLICIES:
            act_ok(s, 'jr_rui_pol', id=pid, on=True, full=pid in ('yte', 'dn'))
        days(s, rui.WAIT)
        act_ok(s, 'jr_rui_pol', id='xe', on=True, full=True)         # switched up mid-term
        act_ok(s, 'jr_rui_pol', id='yte', on=True, full=False)       # and one back down
        dn_warn(s, 'bom')
        out.append(copy.deepcopy(s))                                 # a điện nước warning open
        days(s)
        out.append(copy.deepcopy(s))                                 # its card open
        act_ok(s, 'jr_rui_choose', id=R(s)['dn']['card']['id'], choice='tho')
        R(s)['month']['n'] = 0
        warn(s, 'om', 'cam')
        days(s)
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='kham')
        days(s, rui.MONTH_DAYS)                                      # a bill at both tiers
        out.append(copy.deepcopy(s))
        for x in out:
            validate_state(x)
            self.assertTrue(set(R(x)['pol']) <= {'yte', 'xe', 'nha'})
        return out

    def test_saves_cross_the_1920_build_both_ways(self):
        old = self.old_tree()
        prog = ('import json,sys\nfrom game.engine import validate_state,migrate_state,public_state,apply_action\n'
                'from game import rui\n'
                'out=[]\n'
                'for s in json.load(sys.stdin):\n'
                ' s=migrate_state(s);validate_state(s);v=public_state(s)\n'
                ' s["journey"]["life_day"]+=1;rui.on_life_day(s);validate_state(s)\n'   # the old build ticks a life day
                ' out.append(dict(s=s,pol=[p for p in v["rui"]["pol"]]))\n'
                'print(json.dumps(out))')
        saves = self.saves()
        got = self.run_old(old, prog, saves)
        for mine, back in zip(saves, got):
            r0, r1 = R(mine), back['s']['journey']['rui']
            for k in ('full', 'pol2', 'dn'):
                if k in r0:
                    self.assertEqual(r1.get(k), r0[k], k)             # kept as it was
            self.assertEqual({p['id'] for p in back['pol']}, {'yte', 'xe', 'nha'})   # the old page: three policies
            s = migrate_state(back['s'])
            validate_state(s)
            days(s)
            public_state(s)
            validate_state(s)


@unittest.skipUnless(shutil.which('node'), 'node not installed')
class Page(unittest.TestCase):
    def test_two_tiers_side_by_side(self):
        s = renter(9000, bank=3000)
        own_car(s, 'xe_ga')
        own_home(s, 'nha_pho', live=False)
        act_ok(s, 'jr_rui_pol', id='xe', on=True, full=True)
        act_ok(s, 'jr_rui_pol', id='yte', on=True)
        script = r"""
const assert=require('node:assert/strict'),fs=require('node:fs');
const source=fs.readFileSync('public/js/v4/rui.js','utf8').replace(/^import .*;\r?\n/gm,'').replace(/^export /gm,'');
const {S,ruiPage}=new Function('icon','esc',source+'\nreturn {S,ruiPage};')(()=>'',String);
const f=JSON.parse(fs.readFileSync(0,'utf8'));
S.env={api:{state:{rui:f.rui},content:{journey:{rui:f.catalogue}}}};
const html=ruiPage();
for(const id of ['yte','xe','nha','dn']){
  assert.ok(html.includes(`data-id="${id}" data-on="1" data-full="0"`),id);
  assert.ok(html.includes(`data-id="${id}" data-on="1" data-full="1"`),id);
}
assert.equal((html.match(/rui-pct">80%/g)||[]).length,4);
assert.equal((html.match(/rui-pct">100%/g)||[]).length,4);
assert.equal((html.match(/✓ Đang dùng/g)||[]).length,2);
assert.match(html,/Gói trọn/);assert.match(html,/Gói thường/);assert.match(html,/Bảo hiểm điện nước/);
const xe=f.rui.pol.find(p=>p.id==='xe');
assert.ok(html.includes(`${(xe.month*2).toLocaleString('vi-VN')} xu/tháng`));
"""
        out = subprocess.run([shutil.which('node'), '-e', script],
                             input=json.dumps(dict(rui=rui.public(s), catalogue=rui.catalogue())),
                             capture_output=True, text=True, encoding='utf-8', cwd=ROOT, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
