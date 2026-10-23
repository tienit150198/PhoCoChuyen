"""⚡ Cường hóa nhanh (owner 23/10: "cường hóa nhanh sẽ tự ghép mà cường hóa chứ sao lại cường hóa từng lần", "nó giống
ghép tự động của áo quần ấy"): jr_pet_wing_fuse_auto (game/wings.py), jr_pet_fuse_auto and jr_pet_gear_auto
(game/pet_tiers.py) run the single command's own step again and again in one command. Each equals the same steps made one
by one (same rolls, same things, same money), keeps within the budget, the money and its cap, stops with its reason, loses
nothing a single step would not (from S a miss loses the two others, below S nothing), never uses the worn wing, the pet
walked, a legendary, a sad pet or a worn gear as an ingredient, refuses clearly with nothing to do, is paid once from the
wallet then the account, answers a retried wing request id without paying again, and its saves load on the live release
and the one before (no new save key). The single commands still give exactly what the live release gives."""
import copy
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import pet_tiers as px
from game import pets as pt
from game import wings as W
from game import wings_content as WC
from game.engine import GameError, validate_state
from tests.test_bank import act, story
from tests.test_pet_tiers import get as get_pet

ROOT = Path(__file__).resolve().parents[1]
RELEASES = {'2.5.5': '207854b7', '2.5.4.3': '07b0db0f'}   # live when this was written, and the one before
NOW = 1792800000.0


def money(s):
    j = s['journey']
    return j['wallet'] + (j['bank']['balance'] if j.get('bank') else 0)


def seeded(mod, seed):
    rng = random.Random(seed)
    return mock.patch.object(mod, 'roll', lambda n: rng.randrange(n))


def always(mod, v):
    return mock.patch.object(mod, 'roll', lambda n: min(v, n - 1))


def clock():
    return mock.patch.object(pt, 'now', lambda: NOW)


def refused(test, s, name, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)
    return str(cm.exception)


# ---------------------------------------------------------------- 🪽 wings
def Wg(s):
    return s['journey']['wings']


def wings(wallet=10**9, *groups, on=None):
    """A save owning wings: (style, tier, how many)…; `on` the index of the wing worn (else the first bought)."""
    s = story(wallet=wallet)
    for k, r, n in groups:
        with always(W, 0):
            s, out = act(s, 'jr_pet_wing_buy', style=k, qty=n, confirm=True)
        for x in out['wings']:
            next(y for y in Wg(s)['own'] if y['id'] == x['id'])['r'] = r
    if on is not None:
        Wg(s)['on'] = Wg(s)['own'][on]['id']
    validate_state(s)
    return s


def wings_by_hand(s, budget, scope='all', top=WC.TOP):
    """The same fusions one jr_pet_wing_fuse at a time, picked as a careful player would (the lowest tier with three;
    the worn one the main, else the dearest style; the cheapest two others, never the worn one)."""
    price = lambda x: WC.INDEX[x['k']]['price']   # noqa: E731
    seq = lambda x: int(x['id'][1:])                # noqa: E731
    n = spent = 0
    while n < W.AUTO_MAX:
        w = Wg(s)
        g = {}
        for x in w['own']:
            if (scope == 'all' or x['k'] == scope) and x['r'] < min(top, WC.TOP):
                g.setdefault(x['r'], []).append(x)
        ready = sorted(r for r, xs in g.items() if len(xs) >= 3)
        if not ready or spent + W.FUSE_FEE[ready[0]] > budget:
            break
        xs = g[ready[0]]
        main = next((x for x in xs if x['id'] == w['on']), None) or sorted(xs, key=lambda x: (-price(x), seq(x)))[0]
        rest = sorted((x for x in xs if x is not main), key=lambda x: (price(x), seq(x)))[:2]
        s, _ = act(s, 'jr_pet_wing_fuse', wings=[main['id'], rest[0]['id'], rest[1]['id']], main=main['id'], confirm=True)
        spent += W.FUSE_FEE[ready[0]]
        n += 1
    return s, n, spent


class WingAuto(unittest.TestCase):
    def test_equals_the_fusions_one_by_one(self):
        base = wings(10**9, ('buom', 0, 14), ('rong', 0, 4), ('tien', 1, 5), ('phuong', 3, 3), on=15)
        for seed in (1, 5, 77, 2024):
            for budget, scope, top in ((10**9, 'all', WC.TOP), (6_000, 'all', WC.TOP), (10**9, 'buom', 2), (10**9, 'all', 1)):
                with self.subTest(seed=seed, budget=budget, scope=scope, top=top):
                    with seeded(W, seed), clock():
                        a, r = act(copy.deepcopy(base), 'jr_pet_wing_fuse_auto', budget=budget, scope=scope, top=top, confirm=True)
                    with seeded(W, seed), clock():
                        b, n, spent = wings_by_hand(copy.deepcopy(base), budget, scope, top)
                    self.assertEqual(Wg(a)['own'], Wg(b)['own'])
                    self.assertEqual(Wg(a)['on'], Wg(b)['on'])
                    self.assertEqual(money(a), money(b))
                    self.assertEqual(money(base) - money(a), spent)
                    self.assertEqual((r['auto']['n'], r['auto']['spent']), (n, spent))
                    self.assertLessEqual(spent, budget)
                    validate_state(a)

    def test_the_summary_and_a_cascade(self):
        s = wings(10**9, ('buom', 0, 9))
        with always(W, 0), clock():
            s, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        a = r['auto']
        self.assertEqual([(x['k'], x['r']) for x in Wg(s)['own']], [('buom', 2)], 'nine D → three C → one B, one command')
        self.assertEqual((a['n'], a['ok'], a['used'], a['stop'], a['left']), (4, 4, 8, 'done', 0))
        self.assertEqual(a['spent'], 3 * W.FUSE_FEE[0] + W.FUSE_FEE[1])
        self.assertEqual(a['made'], [dict(Wg(s)['own'][0])])
        self.assertTrue(r['ok'])
        self.assertIn('4 thành công', r['message'])
        self.assertNotIn('%', r['message'], 'never the odds (owner 19/10)')
        # ghép tới hạng C: three C made, then it stops there
        s = wings(10**9, ('buom', 0, 9))
        with always(W, 0):
            s, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, top=1, confirm=True)
        self.assertEqual(sorted(x['r'] for x in Wg(s)['own']), [1, 1, 1])
        self.assertEqual(r['auto']['stop'], 'top')
        self.assertIn('Đã tới hạng C', refused(self, s, 'jr_pet_wing_fuse_auto', budget=10**9, top=1, confirm=True))
        # three SSS: 🌟 Huyền thoại, the dearest style kept
        s = wings(10**9, ('buom', 6, 2), ('phuong', 6, 1))
        Wg(s)['on'] = None                                                    # none worn: the dearest style is the main one
        with always(W, 0):
            s, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual([(x['k'], x['r']) for x in Wg(s)['own']], [('phuong', WC.TOP)])
        self.assertEqual(r['auto']['spent'], W.FUSE_FEE[6])

    def test_budget_money_and_cap(self):
        s = wings(10**9, ('buom', 0, 6))
        w = s['journey']['wallet']
        with always(W, 9999):                                                # every one misses: the three stay (below S)
            t, r = act(copy.deepcopy(s), 'jr_pet_wing_fuse_auto', budget=1_200, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['spent'], r['auto']['stop'], r['auto']['used']), (2, 1_000, 'budget', 0))
        self.assertEqual(t['journey']['wallet'], w - 1_000)
        self.assertEqual(Wg(t)['own'], Wg(s)['own'], 'below S a miss loses nothing')
        self.assertFalse(r['ok'])
        self.assertIn('500 xu', refused(self, s, 'jr_pet_wing_fuse_auto', budget=499, confirm=True))
        with always(W, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['stop'], r['auto']['spent']), (W.AUTO_MAX, 'cap', W.AUTO_MAX * 500))
        # the money: the wallet then the account, one charge; then it stops
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=s['journey']['wallet'] - 700)
        bal = s['journey']['bank']['balance']
        with always(W, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_wing_fuse_auto', budget=1_500, confirm=True)
        self.assertEqual((t['journey']['wallet'], t['journey']['bank']['balance']), (0, bal - 800))
        self.assertIn('700 xu tiền mặt và 800 xu từ tài khoản', r['message'])
        s = wings(10**9, ('buom', 0, 3))
        s['journey']['wallet'] = 1_200
        with always(W, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_wing_fuse_auto', budget=10**6, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['stop'], t['journey']['wallet']), (2, 'money', 200))
        s['journey']['wallet'] = 300
        self.assertIn('Còn thiếu 200 xu', refused(self, s, 'jr_pet_wing_fuse_auto', budget=10**6, confirm=True))

    def test_refusals(self):
        s = wings(10**9, ('buom', 0, 2), ('tien', 1, 2))
        self.assertIn('Chưa có ba đôi', refused(self, s, 'jr_pet_wing_fuse_auto', budget=10**6, confirm=True))
        self.assertIn('Chưa có ba đôi', refused(self, story(wallet=10**6), 'jr_pet_wing_fuse_auto', budget=10**6, confirm=True))
        s = wings(10**9, ('buom', 0, 3), ('tien', 7, 3))
        for bad in (dict(budget=0), dict(budget=-1), dict(budget=2.5), dict(budget='9'), dict(budget=True), dict(budget=10**13),
                    dict(scope='nope'), dict(scope=3), dict(top=0), dict(top=8), dict(top=True), dict(rid='x'), dict(rid=5),
                    dict(extra=1)):
            with self.subTest(**{k: str(v) for k, v in bad.items()}):
                refused(self, s, 'jr_pet_wing_fuse_auto', **{'budget': 10**6, 'confirm': True, **bad})
        refused(self, s, 'jr_pet_wing_fuse_auto', confirm=True)               # the budget is required
        self.assertIn('Xác nhận', refused(self, s, 'jr_pet_wing_fuse_auto', budget=10**6, confirm=False))
        self.assertIn('Chưa có ba đôi', refused(self, s, 'jr_pet_wing_fuse_auto', scope='tien', budget=10**9, confirm=True))

    def test_from_s_a_miss_loses_the_two_others_only(self):
        s = wings(10**9, ('rong', 4, 4), on=0)
        with always(W, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        a = r['auto']
        self.assertEqual((a['n'], a['ok'], a['used'], a['stop']), (1, 0, 2, 'done'))
        self.assertEqual([x['id'] for x in Wg(t)['own']], [Wg(s)['own'][0]['id'], Wg(s)['own'][3]['id']],
                         'the worn one (the main) and the fourth stay; the two cheapest others went, as one jr_pet_wing_fuse')
        self.assertEqual(Wg(t)['on'], Wg(s)['on'])
        self.assertEqual(money(s) - money(t), W.FUSE_FEE[4])

    def test_the_worn_wing_is_never_used_up(self):
        for seed in range(12):
            s = wings(10**9, ('buom', 0, 3), ('phuong', 0, 1), ('tien', 4, 5), on=2)
            worn = Wg(s)['on']
            with seeded(W, seed):
                t, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
            self.assertIn(worn, [x['id'] for x in Wg(t)['own']])
            self.assertEqual(Wg(t)['on'], worn)
            validate_state(t)
        # the worn wing of another style: one style's run leaves it alone
        s = wings(10**9, ('buom', 0, 3), ('phuong', 0, 2), on=3)
        with always(W, 0):
            t, r = act(s, 'jr_pet_wing_fuse_auto', scope='buom', budget=10**9, confirm=True)
        self.assertEqual(sorted((x['k'], x['r']) for x in Wg(t)['own']), [('buom', 1), ('phuong', 0), ('phuong', 0)])
        self.assertEqual(Wg(t)['on'], Wg(s)['own'][3]['id'])
        # the worn one with two others: the worn one goes up in place, still worn
        s = wings(10**9, ('buom', 0, 2), ('tien', 0, 1), on=0)
        with always(W, 0):
            t, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual([(x['id'], x['k'], x['r']) for x in Wg(t)['own']], [(Wg(s)['on'], 'buom', 1)])
        self.assertEqual(Wg(t)['on'], Wg(s)['on'])

    def test_request_id(self):
        s = wings(10**9, ('buom', 0, 6))
        with always(W, 0):
            s, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, rid='forge-auto-0001', confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['ok']), (2, 2), 'six D → two C')
        again_s, again = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, rid='forge-auto-0001', confirm=True)
        self.assertTrue(again['duplicate'])
        self.assertEqual(again_s, s, 'a retried request pays nothing and fuses nothing')
        self.assertEqual([x['id'] for x in again['wings']], [x['id'] for x in r['auto']['made']])
        self.assertIn('forge-auto-0001', Wg(s)['rq'])
        validate_state(s)
        for i in range(W.RQ_KEEP + 2):                                       # kept like the purchases', the last RQ_KEEP
            s, _ = act(s, 'jr_pet_wing_buy', style='buom', rid=f'later-buy-{i:04d}', confirm=True)
        self.assertNotIn('forge-auto-0001', Wg(s)['rq'])
        validate_state(s)

    def test_through_the_store_a_lost_answer_resent(self):
        from game import marriage as mr
        from game.storage import Store
        tmp = tempfile.TemporaryDirectory(prefix='mnl-fa-', ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 's.db', story=True)
        self.addCleanup(store.close_pool)
        token, _, _ = store.session()
        store.read(token)

        def fn(s):
            s['journey']['wallet'] = 1_000_000
            w = W._ensure(s)
            for _ in range(6):
                W._new(w, 'buom', 0)
        mr._mutate(store, {store.key(token): fn})
        rev = store.read(token)[1]
        pay = dict(budget=1_500, rid='forge-store-0001', confirm=True)
        with always(W, 9999):
            one = store.command(token, 'req-wfa-0001', rev, None, 'jr_pet_wing_fuse_auto', pay)
            again = store.command(token, 'req-wfa-0001', rev, None, 'jr_pet_wing_fuse_auto', pay)
        self.assertEqual(one['result'], again['result'])
        self.assertEqual(one['result']['auto']['n'], 3)
        s = store.read(token)[0]
        self.assertEqual(s['journey']['wallet'], 1_000_000 - 1_500)
        validate_state(s)


# ---------------------------------------------------------------- 🧬 pets
def X(s):
    return s['journey']['petx']


def pets(*ranks, wallet=10**9, breed='meo_mun'):
    s = story(wallet=wallet)
    ids = []
    for i, r in enumerate(ranks):
        s, pid = get_pet(s, f'Bé {i + 1}', breed=breed, rank=r)
        ids.append(pid)
    return s, ids


def where(s, pid):
    return px._where(s, pid)[2]


def pets_by_hand(s, budget, scope='all', top=px.TOP + 1):
    n = spent = 0
    while n < px.AUTO_MAX:
        left = px.fuse_sets(s, scope, top)
        if not left or spent + px.FUSE_FEE[left[0][0]] > budget:
            break
        r, ids, _ = left[0]
        s, out = act(s, 'jr_pet_fuse', pets=ids, main=ids[0], confirm=True)
        spent += px.FUSE_FEE[r]
        n += 1
        if out['fuse'].get('myth'):
            break
    return s, n, spent


class PetAuto(unittest.TestCase):
    def test_equals_the_fusions_one_by_one(self):
        base, _ = pets(*([0] * 10 + [1] * 4 + [3] * 3))
        for seed in (2, 9, 31, 400):
            for budget in (10**9, 9_000):
                with self.subTest(seed=seed, budget=budget):
                    with seeded(px, seed), clock():
                        a, r = act(copy.deepcopy(base), 'jr_pet_fuse_auto', budget=budget, confirm=True)
                    with seeded(px, seed), clock():
                        b, n, spent = pets_by_hand(copy.deepcopy(base), budget)
                    for k in ('pets', 'petx', 'petw'):
                        self.assertEqual(a['journey'].get(k), b['journey'].get(k))
                    self.assertEqual(money(a), money(b))
                    self.assertEqual((r['auto']['n'], r['auto']['spent']), (n, spent))
                    self.assertEqual(money(base) - money(a), spent)
                    self.assertLessEqual(spent, budget)
                    validate_state(a)

    def test_the_pick_walked_main_kennel_first_no_legend_no_sad(self):
        s, ids = pets(0, 0, 0, 0, 0)
        b = s['journey']['pets']
        homes = [p['id'] for p in b['list']]
        walk = b['walk']
        self.assertIn(walk, homes)
        r, pick, k = px.fuse_sets(s)[0]
        self.assertEqual((r, pick[0], k), (0, walk, 1), 'the pet walked is the main one')
        self.assertNotIn(walk, pick[1:])
        self.assertEqual([where(s, i) for i in pick[1:]], ['ken', 'ken'], 'the kennel before home')
        # a legendary or a sad pet is never used
        s, ids = pets(6, 6, 6, 6)
        from game import pet_wardrobe as pw
        pw.set_legend(s, ids[1])
        self.assertEqual(px.fuse_sets(s), [(6, px.fuse_sets(s)[0][1], 1)])
        self.assertNotIn(ids[1], px.fuse_sets(s)[0][1])
        s, ids = pets(0, 0, 0)
        home = [p for p in s['journey']['pets']['list'] if p['id'] != s['journey']['pets']['walk']]
        for k in pt.NEEDS:
            home[0][k] = 0
        self.assertEqual(px.fuse_sets(s), [])
        self.assertIn('Chưa có ba bé', refused(self, s, 'jr_pet_fuse_auto', budget=10**6, confirm=True))

    def test_cascade_stops_and_losses(self):
        s, ids = pets(0, 0, 0, 0, 0, 0, 0, 0, 0)
        with always(px, 0), clock():
            t, r = act(copy.deepcopy(s), 'jr_pet_fuse_auto', budget=10**9, top=1, confirm=True)
        self.assertEqual(sorted(px.rec_of(t, p)['r'] for p in px.all_pets(t)), [1, 1, 1])
        self.assertEqual((r['auto']['n'], r['auto']['used'], r['auto']['stop']), (3, 6, 'top'))
        self.assertEqual(len(X(t)['ret']), 6, 'the two others retire to the grandparents, as one jr_pet_fuse')
        with always(px, 0), clock():
            t, r = act(copy.deepcopy(s), 'jr_pet_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual([px.rec_of(t, p)['r'] for p in px.all_pets(t)], [2])
        self.assertEqual((r['auto']['n'], r['auto']['ok'], r['auto']['stop']), (4, 4, 'done'))
        self.assertEqual(r['auto']['made'][0]['r'], 2)
        # from S a miss loses the two others (never retired), the main one stays
        s, ids = pets(4, 4, 4)
        with always(px, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['used'], r['auto']['stop']), (1, 2, 'done'))
        self.assertEqual([p['id'] for p in px.all_pets(t)], [s['journey']['pets']['walk']])
        self.assertEqual(X(t)['ret'], X(s)['ret'])
        # below S a miss keeps the three: tried again until the budget
        s, ids = pets(1, 1, 1)
        with always(px, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_fuse_auto', budget=7_000, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['spent'], r['auto']['stop'], r['auto']['used']), (3, 6_000, 'budget', 0))
        self.assertEqual(len(px.all_pets(t)), 3)

    def test_a_than_thu_offer_stops_it(self):
        s, ids = pets(3, 3, 3, 3, 3, 3)
        with always(px, 0), clock():
            t, r = act(s, 'jr_pet_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['stop']), (1, 'myth'))
        self.assertIsNotNone(r['auto']['myth'])
        self.assertIn('mo', t['journey']['petw'])
        validate_state(t)

    def test_budget_cap_money_refusals(self):
        s, ids = pets(0, 0, 0, 0, 0, 0)
        with always(px, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['stop'], r['auto']['spent']), (px.AUTO_MAX, 'cap', px.AUTO_MAX * 500))
        self.assertEqual(len(px.all_pets(t)), 6)
        s['journey']['wallet'] = 1_200
        with always(px, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['stop'], t['journey']['wallet']), (2, 'money', 200))
        self.assertIn('500 xu', refused(self, s, 'jr_pet_fuse_auto', budget=499, confirm=True))
        self.assertIn('Xác nhận', refused(self, s, 'jr_pet_fuse_auto', budget=10**6, confirm=False))
        for bad in (dict(budget=0), dict(budget='1'), dict(scope='fish'), dict(top=0), dict(top=8), dict(extra=1)):
            with self.subTest(**{k: str(v) for k, v in bad.items()}):
                refused(self, s, 'jr_pet_fuse_auto', **{'budget': 10**6, 'confirm': True, **bad})
        self.assertIn('Chưa có ba bé', refused(self, s, 'jr_pet_fuse_auto', scope='dog', budget=10**6, confirm=True))


# ---------------------------------------------------------------- 🧰 gear
def gear(*specs, wallet=10**9):
    """A save with a pet and gear: (slot, rank, level, worn)…"""
    s, pid = pets(0, wallet=wallet)
    for slot, r, lv, on in specs:
        s, out = act(s, 'jr_pet_gear_buy', slot=slot, model=0, rank=min(r, 1), confirm=True)
        g = next(g for g in X(s)['gear'] if g['id'] == out['gear'])
        g['r'], g['lv'] = r, lv
        if on:
            s, _ = act(s, 'jr_pet_gear_wear', pet=pid[0], slot=slot, gear=g['id'])
    validate_state(s)
    return s, pid[0]


def gear_by_hand(s, budget, scope='all', top=px.TOP):
    n = spent = 0
    while n < px.GEAR_AUTO_MAX:
        step = px.gear_step(s, X(s), scope, top)
        if not step or spent + px._step_fee(step) > budget:
            break
        fee = px._step_fee(step)
        if step[0] == 'up':
            s, _ = act(s, 'jr_pet_gear_up', gear=step[1]['id'], confirm=True)
        else:
            s, _ = act(s, 'jr_pet_gear_fuse', gears=[step[1]['id']] + [g['id'] for g in step[2]], confirm=True)
        spent += fee
        n += 1
    return s, n, spent


class GearAuto(unittest.TestCase):
    def test_equals_the_steps_one_by_one(self):
        base, _ = gear(*([('giay', 0, 0, False)] * 7), ('giay', 1, 8, True), ('giap', 0, 3, False), ('giap', 0, 9, False),
                       ('giap', 0, 0, False), ('dau', 2, 2, True))
        for seed in (3, 8, 99):
            for budget, scope in ((10**9, 'all'), (25_000, 'all'), (10**9, 'giap')):
                with self.subTest(seed=seed, budget=budget, scope=scope):
                    with seeded(px, seed), clock():
                        a, r = act(copy.deepcopy(base), 'jr_pet_gear_auto', budget=budget, scope=scope, confirm=True)
                    with seeded(px, seed), clock():
                        b, n, spent = gear_by_hand(copy.deepcopy(base), budget, scope)
                    self.assertEqual(a['journey']['petx'], b['journey']['petx'])
                    self.assertEqual(a['journey'].get('petw'), b['journey'].get('petw'))
                    self.assertEqual(money(a), money(b))
                    self.assertEqual((r['auto']['n'], r['auto']['spent']), (n, spent))
                    self.assertLessEqual(spent, budget)
                    validate_state(a)

    def test_strengthen_then_rank_up_then_the_worn_one(self):
        s, pid = gear(('giay', 0, 0, False), ('giay', 0, 0, False), ('giay', 0, 0, False))
        with always(px, 0):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertEqual([(g['r'], g['lv']) for g in X(t)['gear']], [(1, 0)], '+1 … +10, then three → one of rank C')
        self.assertEqual((r['auto']['n'], r['auto']['fuses'], r['auto']['used'], r['auto']['stop']), (11, 1, 2, 'done'))
        self.assertEqual(r['auto']['spent'], sum(px.GUP_FEE[0] * k for k in range(1, 11)) + px.GFUSE_FEE[0])
        # a worn gear and nothing to rank up: the worn one strengthened to +10, an unworn single one left alone
        s, pid = gear(('giay', 2, 7, True), ('giap', 0, 0, False))
        with always(px, 0):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertEqual([(g['s'], g['r'], g['lv']) for g in X(t)['gear']], [('giay', 2, 10), ('giap', 0, 0)])
        self.assertEqual(r['auto']['n'], 3)
        self.assertIn('Chưa có món nào', refused(self, t, 'jr_pet_gear_auto', budget=10**9, confirm=True))

    def test_worn_gear_is_never_an_ingredient_and_losses(self):
        s, pid = gear(('giay', 0, 10, True), ('giay', 0, 0, False), ('giay', 0, 0, False), ('giay', 0, 10, False))
        with always(px, 0):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=10**9, top=1, confirm=True)
        worn = X(s)['t'][pid]['g']['giay']
        self.assertEqual(X(t)['t'][pid]['g']['giay'], worn)
        self.assertEqual(next(g for g in X(t)['gear'] if g['id'] == worn)['r'], 1, 'the worn one goes up in place')
        self.assertEqual(r['auto']['stop'], 'done')
        # two worn of a kind: no three (the ingredients must be free); the worn ones to +10 only
        s, pid2 = gear(('giay', 0, 10, True), ('giay', 0, 0, False), ('giay', 0, 10, False))
        s, other = get_pet(s, 'Bé hai')
        s, _ = act(s, 'jr_pet_gear_wear', pet=other, slot='giay', gear=X(s)['gear'][1]['id'])
        with always(px, 0):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertEqual([g['r'] for g in X(t)['gear']], [0, 0, 0])
        # from S a miss loses the two others, the main one stays; below S nothing
        s, pid = gear(('giay', 4, 10, False), ('giay', 4, 0, False), ('giay', 4, 0, False))
        with always(px, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertEqual([(g['r'], g['lv']) for g in X(t)['gear']], [(4, 10)])
        self.assertEqual((r['auto']['n'], r['auto']['used']), (1, 2))
        s, pid = gear(('giay', 1, 10, False), ('giay', 1, 0, False), ('giay', 1, 0, False))
        with always(px, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertEqual(len(X(t)['gear']), 3)
        self.assertEqual((r['auto']['n'], r['auto']['stop']), (px.GEAR_AUTO_MAX, 'cap'))

    def test_budget_money_refusals(self):
        s, pid = gear(('giay', 0, 1, True))                                   # +1 → +2: 200 xu a try (+0 → +1 never misses)
        with always(px, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=450, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['spent'], r['auto']['stop']), (2, 400, 'budget'))
        self.assertEqual(X(t)['gear'], X(s)['gear'], 'a miss loses nothing but the fee')
        s['journey']['wallet'] = 500
        with always(px, 9999):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=10**6, confirm=True)
        self.assertEqual((r['auto']['n'], r['auto']['stop'], t['journey']['wallet']), (2, 'money', 100))
        self.assertIn('200 xu', refused(self, s, 'jr_pet_gear_auto', budget=199, confirm=True))
        self.assertIn('Xác nhận', refused(self, s, 'jr_pet_gear_auto', budget=10**6, confirm=False))
        for bad in (dict(budget=0), dict(scope='canh'), dict(top=0), dict(top=7), dict(extra=1)):
            with self.subTest(**{k: str(v) for k, v in bad.items()}):
                refused(self, s, 'jr_pet_gear_auto', **{'budget': 10**6, 'confirm': True, **bad})
        self.assertIn('Chưa có món nào', refused(self, s, 'jr_pet_gear_auto', scope='giap', budget=10**6, confirm=True))


# ---------------------------------------------------------------- the live release
SINGLE = '''import json,sys
from unittest import mock
from game import pet_tiers as px, pets as pt, wings as W
from game import journey as jr
from game.engine import apply_action,new_state,validate_state
s=new_state();jr.enable_story(s,4242);s['journey'].update(gender='female',wallet=10**9)
s['journey']['stats']['max_wallet']=10**9
validate_state(s)
rng=__import__('random').Random(int(sys.argv[2]))
out=[]
with mock.patch.object(px,'roll',lambda n:rng.randrange(n)), mock.patch.object(W,'roll',lambda n:rng.randrange(n)), \\
        mock.patch('time.time',lambda:1792800000.0):
    for name,p,fix in json.loads(sys.argv[1]):
        if fix:
            for kind,i,k,v in fix:
                rows=s['journey']['wings']['own'] if kind=='w' else s['journey']['petx']['gear']
                for x in ([x for x in rows if x['id']==i] if isinstance(i,str) else [rows[i]]):
                    x[k]=v
        try:
            s,r=apply_action(s,None,name,p);out.append([r.get('message'),r.get('ok'),r.get('fuse'),r.get('gear'),r.get('lost')])
        except Exception as e:
            out.append(['ERR',str(e)])
print(json.dumps([s['journey'],out],sort_keys=True,ensure_ascii=False))
'''


class Live(unittest.TestCase):
    def tree(self, rev):
        tmp = tempfile.mkdtemp(prefix=f'mnl-fa-{rev}-')
        self.addCleanup(shutil.rmtree, tmp, True)
        try:
            data = subprocess.run(['git', 'archive', rev, 'game', 'reference'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {rev}')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def run_in(self, where, code, *args, stdin=''):
        env = dict(os.environ, PYTHONPATH=str(where), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', code, *args], input=stdin, capture_output=True, text=True, cwd=where,
                             env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return out.stdout.strip().splitlines()[-1]

    def test_single_commands_are_the_live_ones(self):
        """jr_pet_wing_fuse, jr_pet_fuse, jr_pet_gear_up and jr_pet_gear_fuse after the refactor: the journey and the answers
        the live release gives (same save, rolls, clock)."""
        adopt = lambda n: ['jr_pet_adopt', dict({'from': 'shop'}, breed='meo_mun', coat=0, nick=n, confirm=True), None]   # noqa: E731
        cmds = [['jr_pet_wing_buy', dict(style='buom', qty=12, confirm=True), None]]
        cmds += [['jr_pet_wing_fuse', dict(wings=[f'w{a}', f'w{b}', f'w{c}'], confirm=True), None]
                 for a, b, c in ((1, 2, 3), (1, 4, 5), (6, 7, 8), (1, 9, 10), (1, 11, 12))]
        cmds += [['jr_pet_wing_buy', dict(style='rong', qty=6, confirm=True), [('w', i, 'r', 4) for i in range(-6, 0)]]]
        cmds += [['jr_pet_wing_fuse', dict(wings=['w13', 'w14', 'w15'], main='w15', confirm=True), None]] * 3
        cmds += [adopt(f'Mi {i}') for i in range(9)]
        cmds += [['jr_pet_fuse', dict(pets=[f'p{a}', f'p{b}', f'p{c}'], confirm=True), None]
                 for a, b, c in ((1, 2, 3), (1, 4, 5), (6, 7, 8), (1, 9, 6))]
        cmds += [['jr_pet_gear_buy', dict(slot='giay', model=0, rank=0, qty=15, confirm=True), None]]
        cmds += [['jr_pet_gear_up', dict(gear='g1', confirm=True), None]] * 14
        cmds += [['jr_pet_gear_fuse', dict(gears=[f'g{a}', f'g{a + 1}', f'g{a + 2}'], confirm=True), [('g', f'g{a}', 'lv', 10)]]
                 for a in (1, 4, 7)]
        cmds += [['jr_pet_gear_fuse', dict(gears=['g10', 'g11', 'g12'], confirm=True), [('g', f'g{i}', 'r', 4) for i in (10, 11, 12)]
                  + [('g', 'g10', 'lv', 10)]] for _ in range(2)]
        cmds += [['jr_pet_gear_fuse', dict(gears=['g13', 'g14', 'g15'], confirm=True), [('g', f'g{i}', 'r', 1) for i in (13, 14, 15)]
                  + [('g', 'g13', 'lv', 10)]]]
        for seed in ('1', '6'):
            with self.subTest(seed=seed):
                old = json.loads(self.run_in(self.tree(RELEASES['2.5.5']), SINGLE, json.dumps(cmds), seed))
                new = json.loads(self.run_in(ROOT, SINGLE, json.dumps(cmds), seed))
                self.assertEqual(old, new)
                played = [c[0] for c, o in zip(cmds, new[1]) if o[0] != 'ERR']
                for name in ('jr_pet_wing_fuse', 'jr_pet_fuse', 'jr_pet_gear_up', 'jr_pet_gear_fuse'):
                    self.assertGreaterEqual(played.count(name), 3, name)

    def test_auto_saves_load_on_the_live_releases(self):
        saves = []
        s = wings(10**9, ('buom', 0, 20), ('tien', 4, 6), on=0)
        with seeded(W, 4):
            s, _ = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, rid='forge-live-0001', confirm=True)
        s, _ = act(s, 'settings', forgeAnon=True)   # 📣 🕶️ an optional journey key (game/forge_news.py)
        saves.append(s)
        s, _ = pets(*([0] * 9 + [4] * 3))
        with seeded(px, 4):
            s, _ = act(s, 'jr_pet_fuse_auto', budget=10**9, confirm=True)
        s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, qty=6, confirm=True)
        with seeded(px, 4):
            s, r = act(s, 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertGreater(r['auto']['n'], 5)
        saves.append(s)
        for x in saves:
            validate_state(x)
        self.assertEqual(set(Wg(saves[0])), W.BLOCK_KEYS, 'no new save key')
        self.assertEqual(set(X(saves[1])), px.BLOCK_KEYS)
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state\n'
                'out=[]\n'
                'for s in json.load(sys.stdin):\n'
                ' validate_state(s);s=migrate_state(s);validate_state(s);public_state(s)\n'
                ' out.append({k:s["journey"].get(k) for k in ("wings","petx","pets","fzn")})\n'
                'print(json.dumps(out))')
        for label, rev in RELEASES.items():
            with self.subTest(release=label):
                got = json.loads(self.run_in(self.tree(rev), prog, stdin=json.dumps(saves)))
                for back, mine in zip(got, saves):
                    self.assertEqual(back['wings'], mine['journey'].get('wings'))
                    self.assertEqual(back['petx'], mine['journey'].get('petx'))
                    self.assertEqual(back['fzn'], mine['journey'].get('fzn'))
                self.assertEqual(got[0]['fzn'], dict(v=1, anon=True), '🕶️ kept by the older build')


if __name__ == '__main__':
    unittest.main()
