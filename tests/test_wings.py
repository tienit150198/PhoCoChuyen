"""🪽 Cánh (game/wings.py, owner 22/10: "cánh sẽ buff cho người chơi khi đánh pet", "cánh này là làm đẹp cho người dùng nhé,
với tăng tiền kiếm được nữa", "cho nâng nữa, nâng lên như thú đi, D > C > B > A > S > SS > SSS > Huyền thoại", "mua thì mặc
định D hoặc C ngẫu nhiên, xong nâng lên như cơ chế hiện tại nhé"): the tables, a purchase rolled D or C on the server and
answered again (never paid twice) for a retried request id, the pets' fusion rules, one wing worn, its share of the
player's own work (its own row, capped a day, story mode only, out of the 🔥 x3 net), the pet-battle buff (written into the
snapshot, a match with wings stored as engine 2, a wingless one still engine 1 and replayed exactly as 2.5.3 does), a
wing never outweighs one pet rank (simulated), the save checks, and saves with wings crossing 2.5.3 both ways."""
import copy
import io
import json
import os
import random
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import pet_arena as A
from game import pet_battle as B
from game import price_index as pi
from game import tile_match as tm
from game import wings as W
from game import wings_content as WC
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import act, days, story
from tests.test_pet_arena import rand_pet, win_rate
from tests.test_pet_tiers import get as get_pet

ROOT = Path(__file__).resolve().parents[1]
LIVE = 'afb38304'   # 2.5.3, the release this one may be rolled back to


def rolls(*values):
    """Patch wings.roll: each call takes the next value (clamped below its n)."""
    it = iter(values)
    return mock.patch.object(W, 'roll', lambda n: min(next(it), n - 1))


def Wg(s):
    return s['journey']['wings']


def buy(s, style='buom', qty=1, rid=None, r=None):
    """Buy `qty` wings; `r` forces their tier (0 D, 1 C) through the roll."""
    p = dict(style=style, qty=qty, confirm=True, **({'rid': rid} if rid else {}))
    if r is None:
        return act(s, 'jr_pet_wing_buy', **p)
    with rolls(*([0 if r == 0 else 9999] * qty)):
        return act(s, 'jr_pet_wing_buy', **p)


def owned(s, *tiers, style='thien_than'):
    """A save owning wings of these tiers (bought, then raised by hand), the ids in order."""
    s, out = buy(s, style, len(tiers), r=0)
    for x, t in zip(out['wings'], tiers):
        next(y for y in Wg(s)['own'] if y['id'] == x['id'])['r'] = t
    validate_state(s)
    return s, [x['id'] for x in out['wings']]


def refused(test, s, name, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)
    return str(cm.exception)


class Tables(unittest.TestCase):
    def test_tiers_and_styles(self):
        self.assertEqual(WC.TIERS, ('D', 'C', 'B', 'A', 'S', 'SS', 'SSS', 'HT'))
        self.assertEqual(W.tier_label(WC.TOP), 'Huyền thoại')
        for t in (WC.EARN, WC.CAP, WC.BATTLE):
            self.assertEqual(len(t), len(WC.TIERS))
            self.assertEqual(list(t), sorted(t), 'never lower at a higher tier')
        self.assertEqual((WC.EARN[0], WC.EARN[-1]), (1, 10), 'owner: about +1 % at D to +10 % at Huyền thoại')
        self.assertLessEqual(max(WC.BATTLE), 6)
        self.assertLessEqual(max(WC.BATTLE), B.WG_MAX)
        self.assertEqual(sum(W.ODDS_BUY), 10000)
        self.assertEqual(len(W.FUSE_FEE), WC.TOP)
        for st in WC.STYLES:
            self.assertEqual(st['price'] % 100, 0)
        self.assertEqual(WC.INDEX['buom']['price'], pi.price(8000))
        cat = W.catalogue()
        self.assertEqual([x['id'] for x in cat['styles']], list(WC.ORDER))
        json.dumps(cat)

    def test_chance_like_the_pets(self):
        self.assertEqual(W.chance([0, 0, 0]), W.FUSE_BP[0])
        self.assertEqual(W.chance([0, 1, 2]), W.FUSE_BP[0] + 3 * W.MIX_BP)
        self.assertEqual(W.chance([6, 6, 6]), W.LEGEND_BP)
        self.assertLessEqual(W.chance([0, 6, 6]), 9000)


class Buy(unittest.TestCase):
    def test_d_or_c_paid_once_and_the_first_one_worn(self):
        s = story(wallet=100000)
        price = WC.INDEX['doi']['price']
        with rolls(W.ODDS_BUY[0] - 1, W.ODDS_BUY[0]):
            s, out = act(s, 'jr_pet_wing_buy', style='doi', qty=2, rid='req-0001-abc', confirm=True)
        self.assertEqual([(x['k'], x['r']) for x in out['wings']], [('doi', 0), ('doi', 1)])
        self.assertEqual(s['journey']['wallet'], 100000 - 2 * price)
        self.assertEqual(Wg(s)['on'], out['wings'][0]['id'], 'the first wing goes on at once')
        again_s, again = act(s, 'jr_pet_wing_buy', style='doi', qty=2, rid='req-0001-abc', confirm=True)
        self.assertTrue(again['duplicate'])
        self.assertEqual(again['wings'], out['wings'], 'a retried request answers the same wings')
        self.assertEqual(again_s['journey']['wallet'], s['journey']['wallet'], 'and pays nothing')
        self.assertEqual(len(Wg(again_s)['own']), 2)
        s, more = buy(s, 'doi', r=0)
        self.assertEqual(Wg(s)['on'], out['wings'][0]['id'], 'a later one does not replace the worn one')
        validate_state(s)

    def test_refusals(self):
        s = story(wallet=100)
        self.assertIn('Xác nhận', refused(self, s, 'jr_pet_wing_buy', style='buom', confirm=False))
        refused(self, s, 'jr_pet_wing_buy', style='buom', confirm=True)   # not enough money
        refused(self, s, 'jr_pet_wing_buy', style='nope', confirm=True)
        refused(self, s, 'jr_pet_wing_buy', style='buom', qty=W.QTY_MAX + 1, confirm=True)
        refused(self, s, 'jr_pet_wing_buy', style='buom', rid='x y', confirm=True)
        s = story(wallet=10**8)
        s, _ = buy(s, qty=W.QTY_MAX, r=0)
        s, _ = buy(s, qty=W.QTY_MAX, r=0)
        s, _ = buy(s, qty=W.QTY_MAX, r=0)
        self.assertEqual(len(Wg(s)['own']), W.OWN_MAX)
        refused(self, s, 'jr_pet_wing_buy', style='buom', confirm=True)

    def test_request_ids_kept_bounded(self):
        s = story(wallet=10**7)
        for i in range(W.RQ_KEEP + 3):
            s, _ = buy(s, rid=f'request-{i:04d}', r=0)
        self.assertEqual(len(Wg(s)['rq']), W.RQ_KEEP)
        self.assertNotIn('request-0000', Wg(s)['rq'])
        validate_state(s)


class Fuse(unittest.TestCase):
    def test_success_raises_the_main_in_place_and_uses_the_others(self):
        s = story(wallet=10**7)
        s, (a, b, c) = owned(s, 0, 0, 1)
        Wg(s)['on'] = b
        before = s['journey']['wallet']
        with rolls(0):
            s, out = act(s, 'jr_pet_wing_fuse', wings=[c, a, b], main=c, confirm=True)
        self.assertTrue(out['fuse']['ok'])
        self.assertEqual([(x['id'], x['r']) for x in Wg(s)['own']], [(c, 1)], 'never below what it was')
        self.assertEqual(Wg(s)['on'], c, 'the worn one used up: the main one is worn instead')
        self.assertEqual(s['journey']['wallet'], before - W.FUSE_FEE[0])
        validate_state(s)

    def test_failure_keeps_all_below_s_and_loses_the_others_from_s(self):
        s = story(wallet=10**8)
        s, ids = owned(s, 2, 2, 2)
        with rolls(9999):
            s2, out = act(s, 'jr_pet_wing_fuse', wings=ids, confirm=True)
        self.assertFalse(out['fuse']['ok'])
        self.assertEqual(len(Wg(s2)['own']), 3)
        self.assertEqual(s2['journey']['wallet'], s['journey']['wallet'] - W.FUSE_FEE[2], 'the fee is spent either way')
        s, ids = owned(story(wallet=10**8), 4, 4, 5)
        with rolls(9999):
            s, out = act(s, 'jr_pet_wing_fuse', wings=ids, main=ids[2], confirm=True)
        self.assertEqual(out['fuse']['lost'], ids[:2])
        self.assertEqual([(x['id'], x['r']) for x in Wg(s)['own']], [(ids[2], 5)])

    def test_three_sss_make_a_legend_and_a_legend_is_the_top(self):
        s, ids = owned(story(wallet=10**8), 6, 6, 6)
        with rolls(W.LEGEND_BP - 1):
            s, out = act(s, 'jr_pet_wing_fuse', wings=ids, confirm=True)
        self.assertEqual(out['fuse']['tier'], WC.TOP)
        self.assertIn('HUYỀN THOẠI', out['message'])
        s, more = owned(s, 0, 0)
        refused(self, s, 'jr_pet_wing_fuse', wings=[ids[0], *more], main=ids[0], confirm=True)
        refused(self, s, 'jr_pet_wing_fuse', wings=more, confirm=True)
        refused(self, s, 'jr_pet_wing_fuse', wings=[more[0], more[0], more[1]], confirm=True)

    def test_wear_and_drop(self):
        s, ids = owned(story(wallet=10**6), 0, 3)
        s, _ = act(s, 'jr_pet_wing_wear', id=ids[1])
        self.assertEqual(W.ref(s), dict(k='thien_than', r=3))
        s, _ = act(s, 'jr_pet_wing_wear', id=None)
        self.assertIsNone(W.ref(s))
        s, _ = act(s, 'jr_pet_wing_wear', id=ids[0])
        s, _ = act(s, 'jr_pet_wing_drop', id=ids[0], confirm=True)
        self.assertIsNone(Wg(s)['on'])
        refused(self, s, 'jr_pet_wing_wear', id='w999')
        validate_state(s)


class Earnings(unittest.TestCase):
    def setUp(self):
        self.s, (self.wid,) = owned(story(wallet=10**6), 4)   # S: +5 %, ≤ 80 000 a day
        self.c = self.s['careers']['mother_baby']

    def test_own_row_capped_and_out_of_the_x3_net(self):
        s, c = self.s, self.c
        money = c['money']
        self.assertEqual(tm.fund_bonus(s, c, 10000, 'Đơn', 'r1'), 500)
        self.assertEqual(c['money'], money + 500)
        self.assertEqual(tm.day_total(c, c['day']), 500, 'kept out of the 🔥 x3 day net like the pet row')
        self.assertEqual(tm.fund_bonus(s, c, 10000, 'Đơn', 'r2', direct=True), 0, 'never on staff orders')
        Wg(s)['day']['got'] = WC.CAP[4] - 30
        self.assertEqual(tm.fund_bonus(s, c, 10**6, 'Lương', 'r3'), 30)
        self.assertEqual(tm.fund_bonus(s, c, 10**6, 'Lương', 'r4'), 0)
        validate_state(s)

    def test_on_the_unboosted_base_and_added_to_the_pet(self):
        s, pid = get_pet(story(wallet=10**6), 'A', 'corgi', 0, 4)            # 🐾 S: +12 %
        s, _ = owned(s, 4)
        Wg(s)['on'] = Wg(s)['own'][0]['id']
        c = s['careers']['mother_baby']
        self.assertEqual(tm.fund_bonus(s, c, 1000, 'Đơn', 'r1'), 120 + 50, 'added, never multiplied')
        self.assertEqual(W.fund_bonus(s, c, 1000, 'Đơn', 'r2'), 50, 'its own share of the same base')

    def test_none_unworn_or_outside_story(self):
        s, c = self.s, self.c
        Wg(s)['on'] = None
        self.assertEqual(tm.fund_bonus(s, c, 10000, 'Đơn', 'r1'), 0)
        s = copy.deepcopy(self.s)
        s['journey']['story'] = False
        self.assertEqual(W.fund_bonus(s, s['careers']['mother_baby'], 10000, 'Đơn', 'r1'), 0)


class Battle(unittest.TestCase):
    def test_snapshot_derive_and_engine(self):
        s, pid = get_pet(story(wallet=10**6), 'A', 'corgi', 0, 2)
        from game import pet_tiers as px
        p = next(q for q in px.all_pets(s) if q['id'] == pid)
        self.assertNotIn('wg', A.fighter(s, p), 'no wings: the snapshot of 2.5.3')
        s, _ = owned(s, WC.TOP)
        f = A.fighter(s, p)
        self.assertEqual(f['wg'], WC.BATTLE[WC.TOP])
        plain = dict(f)
        del plain['wg']
        d0, d1 = B.derive(plain), B.derive(f)
        self.assertEqual(d1['hp'], d0['hp'] + d0['hp'] * f['wg'] // 100)
        self.assertEqual(d1['atk'], d0['atk'] + d0['atk'] * f['wg'] // 100)
        self.assertEqual({k: v for k, v in d1.items() if k not in ('hp', 'atk')}, {k: v for k, v in d0.items() if k not in ('hp', 'atk')})
        self.assertEqual(B.ENGINE, 1)
        self.assertEqual(B.engine_of([plain], [plain]), B.ENGINE)
        self.assertEqual(B.engine_of([plain], [f]), B.WING_ENGINE)
        self.assertEqual(B.wing_pct(dict(f, wg=99)), B.WG_MAX)
        self.assertEqual(B.wing_pct(dict(f, wg='5')), 0)

    def test_a_wing_never_outweighs_a_rank(self):
        """Owner 22/10 "buff cho người chơi khi đánh pet": modest. 1-vs-1, each side first half the time."""
        n = 1200
        for r in (1, 3, 5):
            R = random.Random(40 + r)
            wing = win_rate(R, lambda: dict(rand_pet(R, r), wg=WC.BATTLE[WC.TOP]), lambda: rand_pet(R, r), n)
            R = random.Random(60 + r)
            rank = win_rate(R, lambda: rand_pet(R, r + 1), lambda: rand_pet(R, r), n)
            R = random.Random(80 + r)
            both = win_rate(R, lambda: rand_pet(R, r + 1), lambda: dict(rand_pet(R, r), wg=WC.BATTLE[WC.TOP]), n)
            self.assertGreater(wing, .5, 'the wings help')
            self.assertLess(wing, .68)
            self.assertLess(wing, rank)
            self.assertGreater(both, .52, 'a pet one rank up still wins against a Huyền thoại-winged one')

    def test_wingless_battles_replay_exactly_as_2_5_3(self):
        """ENGINE 1 untouched: the same fighters and seeds give the same fights on 2.5.3 (`git archive afb38304`)."""
        R = random.Random(5)
        cases = [([rand_pet(R, R.randint(0, 6)) for _ in range(3)], [rand_pet(R, R.randint(0, 6)) for _ in range(3)], R.getrandbits(64))
                 for _ in range(25)]
        cases = json.loads(json.dumps(cases))
        old = tree(self)
        prog = ('import json,sys;from game import pet_battle as B\n'
                'print(json.dumps([B.battle(a,b,seed) for a,b,seed in json.load(sys.stdin)]))')
        got = run_old(self, old, prog, cases)
        self.assertEqual(got, json.loads(json.dumps([B.battle(a, b, seed) for a, b, seed in cases])))


def tree(test):
    tmp = tempfile.mkdtemp(prefix='mnl-253-')
    try:
        data = subprocess.run(['git', 'archive', LIVE, 'game', 'reference'], cwd=ROOT, capture_output=True,
                              timeout=120, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        test.skipTest(f'no git tree with {LIVE}')
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(tmp, filter='data')
    return tmp


def run_old(test, old, prog, data):
    env = {k: v for k, v in os.environ.items() if k != 'MNL_CAREERS'}
    env['PYTHONPATH'] = old
    got = subprocess.run([sys.executable, '-c', prog], input=json.dumps(data), capture_output=True, text=True,
                         cwd=old, env=env, encoding='utf-8', timeout=300)
    test.assertEqual(got.returncode, 0, got.stderr[-3000:])
    return json.loads(got.stdout)


class Save(unittest.TestCase):
    def test_validate(self):
        s = story()
        validate_state(s)
        self.assertNotIn('wings', s['journey'], 'absent until the first wing')
        s, _ = owned(story(wallet=10**6), 0, 7)
        for bad in (lambda w: w.update(v=2), lambda w: w['own'][0].update(r=8), lambda w: w['own'][0].update(k='x' * 30),
                    lambda w: w.update(on='w99'), lambda w: w['own'].append(dict(w['own'][0])), lambda w: w.update(extra=1),
                    lambda w: w['day'].update(got=-1)):
            t = copy.deepcopy(s)
            bad(Wg(t))
            with self.assertRaises(GameError):
                validate_state(t)
        t = copy.deepcopy(s)
        Wg(t)['own'][0]['k'] = 'newer_style'   # a newer build's style: kept, drawn by nobody here
        validate_state(t)

    def test_public(self):
        s, ids = owned(story(wallet=10**6), 5)
        pub = public_state(s)['journey']['wings']
        self.assertEqual(pub['on'], ids[0])
        self.assertEqual(pub['cap'], WC.CAP[5])
        self.assertNotIn('rq', pub)


class RollbackTo253(unittest.TestCase):
    """Saves holding j['wings'] (owned, worn, a day's bonus) validate, migrate, render and tick a life day on 2.5.3
    (`git archive afb38304`), which keeps the unknown journey key untouched, and come back here intact."""

    def saves(self):
        s, ids = owned(story(wallet=10**6), 0, 4, 7)
        Wg(s)['on'] = ids[2]
        W.fund_bonus(s, s['careers']['mother_baby'], 10000, 'Đơn', 'r1')
        validate_state(s)
        t, _ = buy(story(wallet=10**5), 'phuong', rid='rollback-0001', r=1)
        return json.loads(json.dumps([s, t]))

    def test_saves_cross_253_both_ways(self):
        saves = self.saves()
        old = tree(self)
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state;from game import bank\n'
                'out=[]\n'
                'for s in json.load(sys.stdin):\n'
                ' validate_state(s);s=migrate_state(s);validate_state(s);public_state(s)\n'
                ' s["journey"]["life_day"]+=1;bank.on_life_day(s);validate_state(s)\n'
                ' out.append(s)\n'
                'import game;print(json.dumps([game.__version__,out]))')
        version, back = run_old(self, old, prog, saves)
        self.assertEqual(version, '2.5.3')
        for mine, s in zip(saves, back):
            self.assertEqual(s['journey']['wings'], mine['journey']['wings'], 'kept, not read')
            s = migrate_state(s)
            validate_state(s)
            days(s)
            public_state(s)
            validate_state(s)
            self.assertEqual(W.ref(s), W.ref(mine))


class Table(unittest.TestCase):
    """The save's command writes what others see (wing_worn, SCHEMA_VERSION 90) in its own transaction."""

    def test_the_worn_wing_row_follows_the_commands(self):
        from tests.test_marriage import Base

        class T(Base):
            def runTest(self):
                pass
        t = T()
        t.setUp()
        try:
            tok = t.user('wing_row', wallet=10**6)
            sid = t.sid(tok)

            def run(action, **p):
                return t.store.command(tok, f'wing-{action}-{len(str(p))}-{os.urandom(3).hex()}', t.store.read(tok)[1], None, action, p)

            def row():
                with t.store.connect() as db:
                    r = db.execute('SELECT k, r FROM wing_worn WHERE sid=?', (sid,)).fetchone()
                return (r['k'], int(r['r'])) if r else None
            self.assertIsNone(row())
            with rolls(9999):
                run('jr_pet_wing_buy', style='rong', confirm=True)
            self.assertEqual(row(), ('rong', 1))
            run('jr_pet_wing_wear', id=None)
            self.assertIsNone(row())
            run('jr_pet_wing_wear', id='w1')
            self.assertEqual(row(), ('rong', 1))
        finally:
            t.doCleanups()


class Client(unittest.TestCase):
    def test_the_art_in_both_modes(self):
        """tests/wings-art.mjs: v4/wings-art.js through look.js, the 2.5D stamp's key, walkers on both maps."""
        try:
            r = subprocess.run(['node', str(ROOT / 'tests' / 'wings-art.mjs')], cwd=ROOT, capture_output=True, text=True,
                               encoding='utf-8', timeout=120)
        except OSError:
            self.skipTest('no node')
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
