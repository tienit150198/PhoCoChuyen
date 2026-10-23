"""⚡ Cường hóa nhanh (owner 23/10: "cường hóa nhanh sẽ tự ghép mà cường hóa chứ sao lại cường hóa từng lần", "nó giống
ghép tự động của áo quần ấy"): jr_pet_wing_fuse_auto (game/wings.py), jr_pet_fuse_auto and jr_pet_gear_auto
(game/pet_tiers.py) run the single command's own step again and again in one command. Each equals the same steps made one
by one (same rolls, same things, same money), keeps within the budget, the money and its cap, stops with its reason, loses
nothing a single step would not (from S a miss loses the two others, below S nothing), never uses the worn wing, the pet
walked, a legendary, a sad pet or a worn gear as an ingredient, refuses clearly with nothing to do, is paid once from the
wallet then the account, answers a retried wing request id without paying again, and its saves load on the live release
and the one before (no new save key). The single commands still give exactly what the live release gives.
🔒 Khóa món (⚒️ Cường hóa v2, game/forge_locks.py): a locked piece is never an ingredient of a run or a fusion, `pin`
keeps one piece the main one of a run; with nothing locked every command is 2.5.6's; the optional journey key `fzl` is
kept by 2.5.6 and 2.5.5, which load, play and save such a save (Live)."""
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

from game import forge_locks as fl
from game import pet_tiers as px
from game import pet_wardrobe as pw
from game import pets as pt
from game import wings as W
from game import wings_content as WC
from game.engine import GameError, public_state, validate_state
from tests.test_bank import act, story
from tests.test_pet_tiers import get as get_pet

ROOT = Path(__file__).resolve().parents[1]
RELEASES = {'2.5.6': '7e7431ab', '2.5.5': '207854b7'}   # live when ⚒️ v2 (🔒 Khóa món) was written, and the one before
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
    """The same fusions one jr_pet_wing_fuse at a time, picked as a careful player would (the lowest tier with three of
    ONE style, then the styles' order; the worn one the main, else the oldest; the oldest two others, never the worn one)."""
    seq = lambda x: int(x['id'][1:])                # noqa: E731
    n = spent = 0
    while n < W.AUTO_MAX:
        w = Wg(s)
        g = {}
        for x in w['own']:
            if (scope == 'all' or x['k'] == scope) and x['r'] < min(top, WC.TOP):
                g.setdefault((x['r'], WC.ORDER.index(x['k'])), []).append(x)
        ready = sorted(key for key, xs in g.items() if len(xs) >= 3)
        if not ready or spent + W.FUSE_FEE[ready[0][0]] > budget:
            break
        xs = g[ready[0]]
        main = next((x for x in xs if x['id'] == w['on']), None) or min(xs, key=seq)
        rest = sorted((x for x in xs if x is not main), key=seq)[:2]
        s, _ = act(s, 'jr_pet_wing_fuse', wings=[main['id'], rest[0]['id'], rest[1]['id']], main=main['id'], confirm=True)
        spent += W.FUSE_FEE[ready[0][0]]
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
        # three SSS of one style: 🌟 Huyền thoại of that style
        s = wings(10**9, ('phuong', 6, 3))
        Wg(s)['on'] = None
        with always(W, 0):
            s, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual([(x['k'], x['r']) for x in Wg(s)['own']], [('phuong', WC.TOP)])
        self.assertEqual(r['auto']['spent'], W.FUSE_FEE[6])
        # owner 23/10 "ghép nhanh thì ghép gì nhận đó thôi k ghép nhanh mấy dòng khác nhé": two SSS of one style and one
        # of another are no set for ⚡ (a fusion by hand still may)
        s = wings(10**9, ('buom', 6, 2), ('phuong', 6, 1))
        self.assertEqual(W.sets(Wg(s)), [])
        self.assertIn('cùng kiểu, cùng hạng', refused(self, s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True))

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
        s = wings(10**9, ('buom', 0, 2), ('tien', 0, 1), ('rong', 0, 1))   # four D of three styles: no set
        self.assertIn('Chưa có ba đôi', refused(self, s, 'jr_pet_wing_fuse_auto', budget=10**6, confirm=True))
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
        # the worn one with two others of its style: the worn one goes up in place, still worn
        s = wings(10**9, ('buom', 0, 3), on=0)
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


# ---------------------------------------------------------------- one line a set (owner 23/10)
class OneLine(unittest.TestCase):
    """Owner 23/10: "ghép nhanh thì ghép gì nhận đó thôi k ghép nhanh mấy dòng khác nhé": every ⚡ set is three of ONE
    line and rank (🪽 one style, 🧬 one breed, 🧰 one slot and model): a run never uses up another line's piece, what is
    fused is what comes out; the lowest rank first, then the catalogue's order. Lines with three still fuse."""

    def test_wings_one_style_a_set(self):
        s = wings(10**9, ('buom', 0, 4), ('rong', 0, 2), ('tien', 0, 5), ('phuong', 4, 2), ('doi', 4, 1))
        Wg(s)['on'] = None
        self.assertEqual([(r, [x['k'] for x in t], k) for r, t, k in W.sets(Wg(s))],
                         [(0, ['buom'] * 3, 1), (0, ['tien'] * 3, 1)], 'rank first, then the styles\' order; rong ×2 and S ×2+1: none')
        for seed in range(10):
            trios = []
            real = W._fuse_three

            def spy(w, main, others):
                trios.append([main['k']] + [x['k'] for x in others])
                return real(w, main, others)
            with seeded(W, seed), mock.patch.object(W, '_fuse_three', spy):
                t, r = act(copy.deepcopy(s), 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
            self.assertTrue(trios)
            self.assertTrue(all(len(set(k)) == 1 for k in trios), trios)
            for k in ('rong', 'phuong', 'doi'):                               # no three of theirs: untouched
                self.assertEqual([x for x in Wg(t)['own'] if x['k'] == k], [x for x in Wg(s)['own'] if x['k'] == k], (seed, k))
            self.assertLessEqual(len([x for x in Wg(t)['own'] if x['k'] == 'buom']), 4)
            validate_state(t)
        with always(W, 0):
            t, r = act(copy.deepcopy(s), 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual(sorted((x['k'], x['r']) for x in Wg(t)['own']),
                         sorted([('buom', 1), ('buom', 0), ('rong', 0), ('rong', 0), ('tien', 1), ('tien', 0), ('tien', 0),
                                 ('phuong', 4), ('phuong', 4), ('doi', 4)]))
        self.assertEqual((r['auto']['n'], r['auto']['used'], r['auto']['left']), (2, 4, 0))

    def test_pets_one_breed_a_set_never_a_hybrid(self):
        s, ids = pets(0, 0, 0, 1)                                             # meo_mun
        for i, (b, r) in enumerate((('cho_ta', 0), ('cho_ta', 0), ('cho_ta', 0), ('tam_the', 0), ('tam_the', 0), ('aln', 1), ('aln', 1))):
            s, _ = get_pet(s, f'Ba {i}', breed=b, rank=r)
        s['journey']['pets']['walk'] = None
        breed = {q['id']: q['b'] for q in px.all_pets(s)}
        sets = px.fuse_sets(s)
        self.assertEqual([(r, [breed[i] for i in t], k) for r, t, k in sets], [(0, ['cho_ta'] * 3, 1), (0, ['meo_mun'] * 3, 1)],
                         'rank first, then the breeds\' order; tam_the ×2, aln ×2 and the C meo_mun: none')
        for seed in range(8):
            trios = []
            real = px._fuse_check

            def spy(s_, p_):
                trios.append(([breed.get(i) for i in p_['pets']], p_.get('mix')))
                return real(s_, p_)
            with seeded(px, seed), no_myth(), mock.patch.object(px, '_fuse_check', spy):
                t, r = act(copy.deepcopy(s), 'jr_pet_fuse_auto', budget=10**9, confirm=True)
            self.assertTrue(trios)
            self.assertTrue(all(len(set(b)) == 1 and mix is None for b, mix in trios), trios)
            after = {q['id']: q for q in px.all_pets(t)}
            for i, b in breed.items():
                if b in ('tam_the', 'aln'):
                    self.assertIn(i, after, (seed, b))
                    self.assertEqual(px.rec_of(t, after[i])['r'], px.rec_of(s, next(q for q in px.all_pets(s) if q['id'] == i))['r'])
            self.assertEqual({q['b'] for q in after.values()} - set(breed.values()), set(), 'never a 🧬 hybrid (cho_ta ×3 stays cho_ta)')
            validate_state(t)
        # two meo_mun D and one cho_ta D: no set (a fusion by hand still may)
        s, ids = pets(0, 0)
        s, _ = get_pet(s, 'Ba', breed='cho_ta')
        self.assertEqual(px.fuse_sets(s), [])
        self.assertIn('cùng giống, cùng hạng', refused(self, s, 'jr_pet_fuse_auto', budget=10**9, confirm=True))
        # a pin: only its breed
        s, ids = pets(0, 0, 0)
        for i in range(3):
            s, _ = get_pet(s, f'Ba {i}', breed='cho_ta')
        s['journey']['pets']['walk'] = None
        self.assertEqual([{px._where(s, i)[1]['b'] for i in t} for _, t, _ in px.fuse_sets(s, pin=ids[1])], [{'meo_mun'}])
        self.assertEqual(px.fuse_sets(s, pin=ids[1])[0][1][0], ids[1])

    def test_gear_one_model_a_set(self):
        s, pid = pets(0)
        for model, qty in ((0, 2), (1, 2), (3, 1)):
            s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=model, rank=0, qty=qty, confirm=True)
        model = lambda g: px.model_of(g, s)   # noqa: E731
        self.assertEqual(sorted(model(g) for g in X(s)['gear']), [0, 0, 1, 1, 3])
        self.assertIsNone(px.gear_step(s, X(s)), 'five giày D of three models: no three of one')
        self.assertIn('cùng mẫu, cùng hạng', refused(self, s, 'jr_pet_gear_auto', budget=10**9, confirm=True))
        self.assertEqual(px._gear_left(s, X(s), 'all', px.TOP), 0)
        s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=1, rank=0, qty=1, confirm=True)
        s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=3, rank=0, qty=2, confirm=True)
        self.assertEqual(px._gear_left(s, X(s), 'all', px.TOP), 2)
        step = px.gear_step(s, X(s))
        self.assertEqual(model(step[1]), 1, 'the lowest model first (the models\' order)')
        before = {g['id']: (model(g), g['r'], g['lv']) for g in X(s)['gear']}
        for seed in range(6):
            fused = []
            real = px._gear_fuse_roll

            def spy(s_, x_, main, others):
                fused.append({px.model_of(g, s_) for g in [main] + others})
                return real(s_, x_, main, others)
            with seeded(px, seed), mock.patch.object(px, '_gear_fuse_roll', spy):
                t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=10**9, confirm=True)
            self.assertTrue(fused)
            self.assertTrue(all(len(m) == 1 for m in fused), fused)
            for g in X(t)['gear']:
                if before[g['id']][0] == 0:
                    self.assertEqual((px.model_of(g, t), g['r'], g['lv']), before[g['id']], 'model 0 ×2: untouched')
            validate_state(t)
        with always(px, 0):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertEqual(sorted((px.model_of(g, t), g['r']) for g in X(t)['gear']), [(0, 0), (0, 0), (1, 1), (3, 1)])
        self.assertEqual((r['auto']['fuses'], r['auto']['used'], r['auto']['left']), (2, 4, 0))
        # a pin: only its model (a model-0 one with no mates of its model: strengthened to +10, nothing used)
        g0 = next(g['id'] for g in X(s)['gear'] if model(g) == 0)
        self.assertEqual(px.gear_step(s, X(s), pin=g0)[:2], ('up', next(g for g in X(s)['gear'] if g['id'] == g0)))
        with always(px, 0):
            t, r = act(copy.deepcopy(s), 'jr_pet_gear_auto', pin=g0, budget=10**9, confirm=True)
        self.assertEqual(len(X(t)['gear']), len(X(s)['gear']))
        self.assertEqual(next(g['lv'] for g in X(t)['gear'] if g['id'] == g0), px.GLV_MAX)


# ---------------------------------------------------------------- the live release
# ---------------------------------------------------------------- 🔒 Khóa món (game/forge_locks.py)
def lock(s, *ids, on=True):
    s, r = act(s, 'jr_pet_lock', ids=list(ids), on=on)
    validate_state(s)
    return s, r


def no_myth():
    """No thần thú offer (it would stop a pets' run early)."""
    return mock.patch.object(pw, 'MYTH_BP', {})


def code_of(test, s, name, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)
    return cm.exception.code, str(cm.exception)


class Locks(unittest.TestCase):
    """⚒️ Cường hóa v2 (owner-approved 23/10): a 🔒 locked piece is never an ingredient of ⚡, Ghép tất cả or a fusion; a
    `pin` keeps one piece the main one of a run; the lock lives in an optional journey key (older builds keep it)."""

    def test_the_command_and_the_save(self):
        s2 = wings(10**9, ('buom', 0, 3))
        w = [x['id'] for x in Wg(s2)['own']]
        s2, r = lock(s2, w[0], w[2])
        self.assertEqual(s2['journey'][fl.KEY], dict(v=1, ids=[w[0], w[2]]))
        self.assertEqual(r['locks'], [w[0], w[2]])
        self.assertEqual(public_state(s2)['journey']['forge_locks'], [w[0], w[2]])
        self.assertTrue(fl.locked(s2, w[0]) and not fl.locked(s2, w[1]))
        s2, _ = lock(s2, w[0], w[1])                                          # locking again: no doubles, order kept
        self.assertEqual(s2['journey'][fl.KEY]['ids'], [w[0], w[2], w[1]])
        s2, r = lock(s2, w[0], w[1], w[2], on=False)
        self.assertNotIn(fl.KEY, s2['journey'], 'nothing locked leaves no key')
        self.assertNotIn('forge_locks', public_state(s2)['journey'])
        self.assertIn('mở khóa 3 món', r['message'])
        # every kind at once: wings, pets, clothes, gear
        s, pid = gear(('giay', 0, 0, False))
        s, _ = act(s, 'jr_pet_wbuy', id='no_hong', qty=2, confirm=True)
        s, _ = act(s, 'jr_pet_wing_buy', style='buom', confirm=True)
        o = pw.get(s)['it'][0]['id']
        g = X(s)['gear'][0]['id']
        s, _ = lock(s, pid, o, g, Wg(s)['own'][0]['id'])
        self.assertEqual(len(fl.ids(s)), 4)
        # refusals: what is not owned, a bad shape
        for bad in (dict(ids=['w999'], on=True), dict(ids=['p999'], on=True), dict(ids=[], on=True), dict(ids=[g, g], on=True),
                    dict(ids=['x1'], on=True), dict(ids=[g], on=1), dict(ids=[g], on='yes'), dict(ids=g, on=True),
                    dict(ids=[g]), dict(ids=[g], on=True, extra=1), dict(ids=[5], on=True)):
            with self.subTest(bad=str(bad)):
                refused(self, s, 'jr_pet_lock', **bad)
        # a piece gone (thrown out after unlocking it) leaves the list at the next change
        s, _ = lock(s, g, on=False)
        s, _ = lock(s, g)
        X(s)['gear'].clear()                                                  # as an older build might use it up
        validate_state(s)
        s, _ = lock(s, pid, on=False)
        self.assertNotIn(g, fl.ids(s))
        # the save's block: strict
        for bad in (dict(v=2, ids=[g]), dict(v=1, ids=[]), dict(v=1, ids='g1'), dict(v=1, ids=['g1', 'g1']), dict(v=1, ids=['zz']),
                    dict(v=1, ids=['g1'], x=1), [], 'x', dict(v=1, ids=['g1'] * 0 + [f'g{i}' for i in range(fl.MAX + 1)])):
            t = copy.deepcopy(s)
            t['journey'][fl.KEY] = bad
            with self.subTest(block=str(bad)[:40]), self.assertRaises(GameError):
                validate_state(t)

    def test_wings_auto_and_one_shot(self):
        # 🪽 three C: the locked one is the main one (it goes up, never away)
        s = wings(10**9, ('buom', 1, 3))
        w = [x['id'] for x in Wg(s)['own']]
        Wg(s)['on'] = None
        s, _ = lock(s, w[2])
        self.assertEqual([x['id'] for x in W.sets(Wg(s), locks=fl.ids(s))[0][1]], [w[2], w[0], w[1]])
        with always(W, 0):
            t, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
        self.assertEqual([(x['id'], x['r']) for x in Wg(t)['own']], [(w[2], 2)])
        # two locked of three: nothing to do; the refusal says so
        s, _ = lock(s, w[1])
        self.assertEqual(W.sets(Wg(s), locks=fl.ids(s)), [])
        self.assertIn('Chưa có ba đôi', refused(self, s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True))
        # many seeds, from S (a miss loses the two others): the locked and the worn wings always stay
        for seed in range(10):
            s = wings(10**9, ('rong', 4, 7), ('buom', 0, 6), on=8)
            keep = [Wg(s)['own'][i]['id'] for i in (1, 3, 9)]
            s, _ = lock(s, *keep)
            with seeded(W, seed):
                t, r = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, confirm=True)
            left = {x['id'] for x in Wg(t)['own']}
            self.assertTrue(set(keep) <= left, seed)
            self.assertIn(Wg(s)['on'], left)
            self.assertEqual(Wg(t)['on'], Wg(s)['on'])
            validate_state(t)
        # `pin`: that wing is the main one even when it is not the dearest nor worn; one style's run
        s = wings(10**9, ('buom', 0, 4), ('rong', 0, 2))
        Wg(s)['on'] = None
        pin = Wg(s)['own'][3]['id']
        self.assertEqual(W.sets(Wg(s), 'buom', pin=pin)[0][1][0]['id'], pin)
        self.assertNotEqual(W.sets(Wg(s), 'buom')[0][1][0]['id'], pin, 'without the pin another one is the main one')
        with always(W, 0):
            t, r = act(s, 'jr_pet_wing_fuse_auto', scope='buom', pin=pin, budget=10**9, confirm=True)
        self.assertIn((pin, 1), [(x['id'], x['r']) for x in Wg(t)['own']])
        for bad in ('x', 5, 'w1;', ''):
            refused(self, s, 'jr_pet_wing_fuse_auto', pin=bad, budget=10**9, confirm=True)
        # one shot: a locked ingredient refused (state unchanged), a locked main one fine; throwing away refused
        s = wings(10**9, ('buom', 0, 3))
        w = [x['id'] for x in Wg(s)['own']]
        s, _ = lock(s, w[1])
        c, msg = code_of(self, s, 'jr_pet_wing_fuse', wings=w, confirm=True)
        self.assertEqual(c, 'locked')
        self.assertIn('đang khóa', msg)
        with always(W, 0):
            t, r = act(s, 'jr_pet_wing_fuse', wings=[w[1], w[0], w[2]], main=w[1], confirm=True)
        self.assertEqual([(x['id'], x['r']) for x in Wg(t)['own']], [(w[1], 1)])
        self.assertEqual(code_of(self, s, 'jr_pet_wing_drop', id=w[1], confirm=True)[0], 'locked')
        t, _ = act(s, 'jr_pet_wing_drop', id=w[0], confirm=True)
        self.assertEqual(len(Wg(t)['own']), 2)

    def test_pets_auto_and_one_shot(self):
        s, ids = pets(0, 0, 0, 0, 0, 0)
        s, _ = lock(s, ids[1], ids[4])
        sets = px.fuse_sets(s, locks=fl.ids(s))
        walk = s['journey']['pets']['walk']
        self.assertEqual(sets[0][2], 1, "three kept (walked, two locked), three free: one set")
        for _, trio, _ in sets:
            self.assertFalse(set(trio[1:]) & {ids[1], ids[4], walk})
        for seed in range(8):
            with seeded(px, seed), no_myth():
                t, r = act(s, 'jr_pet_fuse_auto', budget=10**9, confirm=True)
            left = {q['id'] for q in px.all_pets(t)}
            self.assertTrue({ids[1], ids[4], walk} <= left, seed)
            validate_state(t)
        # `pin`: the main one of the run
        s, ids = pets(0, 0, 0)
        s['journey']['pets']['walk'] = None
        self.assertEqual(px.fuse_sets(s, pin=ids[2])[0][1][0], ids[2])
        with always(px, 0), no_myth():
            t, r = act(s, 'jr_pet_fuse_auto', pin=ids[2], budget=10**9, confirm=True)
        self.assertEqual([q['id'] for q in px.all_pets(t)], [ids[2]], 'the pinned pet went up, the two others retired')
        # one shot: a locked ingredient refused, a locked main one fine
        s, ids = pets(0, 0, 0)
        s, _ = lock(s, ids[2])
        self.assertEqual(code_of(self, s, 'jr_pet_fuse', pets=ids, main=ids[0], confirm=True)[0], 'locked')
        with always(px, 0), no_myth():
            t, r = act(s, 'jr_pet_fuse', pets=ids, main=ids[2], confirm=True)
        self.assertTrue(r['fuse']['ok'])
        self.assertEqual([q['id'] for q in px.all_pets(t)], [ids[2]])

    def test_clothes_and_gear(self):
        # 👗 four no_hong D, one locked: ⚡ and the one-shot use the three others; three with one locked: refused
        s, _ = pets(0)
        s, _ = act(s, 'jr_pet_wbuy', id='no_hong', qty=4, confirm=True)
        o = [i['id'] for i in pw.get(s)['it']]
        s, _ = lock(s, o[0])
        with always(px, 0), always(pw, 0):
            t, r = act(s, 'jr_pet_wfuse', k='no_hong', r=0, confirm=True)
        self.assertIn(o[0], [i['id'] for i in pw.get(t)['it']])
        with always(pw, 0):
            t, r = act(s, 'jr_pet_wfuse_auto', budget=10**9, confirm=True)
        self.assertEqual(r['auto']['n'], 1)
        self.assertIn(o[0], [i['id'] for i in pw.get(t)['it']])
        s, _ = lock(s, o[1])
        self.assertEqual(code_of(self, s, 'jr_pet_wfuse', k='no_hong', r=0, confirm=True)[0], 'locked')
        self.assertIn('Không còn ba món', refused(self, s, 'jr_pet_wfuse_auto', budget=10**9, confirm=True))
        t, _ = act(s, 'jr_pet_wdrop', k='no_hong', r=0, confirm=True)       # an unlocked one goes
        self.assertTrue({o[0], o[1]} <= {i['id'] for i in pw.get(t)['it']})
        t, _ = lock(t, *[i['id'] for i in pw.get(t)['it'] if i['id'] not in fl.ids(t)])
        self.assertEqual(code_of(self, t, 'jr_pet_wdrop', k='no_hong', r=0, confirm=True)[0], 'locked')
        # 🧰 gear: a locked one is never a mate; a locked +10 is the main one; one shot refused; throwing away refused
        s, _ = gear(('giay', 0, 10, False), ('giay', 0, 10, False), ('giay', 0, 0, False), ('giay', 0, 0, False))
        g = [x['id'] for x in X(s)['gear']]
        s, _ = lock(s, g[1])
        step = px.gear_step(s, X(s), locks=fl.ids(s))
        self.assertEqual((step[0], step[1]['id'], [x['id'] for x in step[2]]), ('fuse', g[1], [g[2], g[3]]))
        with always(px, 0):
            t, r = act(s, 'jr_pet_gear_auto', budget=10**9, confirm=True)
        self.assertIn(g[1], [x['id'] for x in X(t)['gear']])
        self.assertEqual(code_of(self, s, 'jr_pet_gear_fuse', gears=[g[0], g[1], g[2]], confirm=True)[0], 'locked')
        self.assertEqual(code_of(self, s, 'jr_pet_gear_drop', gear=g[1], confirm=True)[0], 'locked')
        self.assertEqual(px.gear_step(s, X(s), pin=g[0])[1]['id'], g[0], 'the pinned gear is the main one')
        with always(px, 0):
            t, r = act(s, 'jr_pet_gear_auto', pin=g[0], budget=10**9, confirm=True)
        self.assertIn(g[0], [x['id'] for x in X(t)['gear']])
        self.assertIn(g[1], [x['id'] for x in X(t)['gear']])

    def test_pin_is_cường_hóa_tối_đa_of_one_piece(self):
        """`pin` (⚒️ "Cường hóa tối đa" on one piece): the tiers below build its ingredients, nothing above it is touched,
        the pinned one is the main one; a gear with no mates is strengthened to +10; a Huyền thoại / 🌟 has nothing to do."""
        s = wings(10**9, ('rong', 0, 6), ('rong', 1, 1), ('tien', 4, 3), ('buom', 0, 3), ('buom', 1, 2))
        Wg(s)['on'] = None
        pin = next(x['id'] for x in Wg(s)['own'] if x['k'] == 'rong' and x['r'] == 1)
        keep = {x['id']: x['r'] for x in Wg(s)['own'] if x['k'] != 'rong'}
        self.assertEqual([r for r, _, _ in W.sets(Wg(s), pin=pin)], [0], 'only below the pinned C (the S are left alone)')
        self.assertTrue(all(x['k'] == 'rong' for _, t, _ in W.sets(Wg(s), pin=pin) for x in t), 'only the pinned style')
        with always(W, 0):
            t, r = act(s, 'jr_pet_wing_fuse_auto', pin=pin, budget=10**9, confirm=True)
        own = {x['id']: x for x in Wg(t)['own']}
        self.assertEqual(own[pin]['r'], 2, 'six D → two C, then the pinned C and the two → B')
        self.assertEqual({i: own[i]['r'] for i in keep if i in own}, keep, 'other styles untouched (the S, the butterflies)')
        self.assertEqual(r['auto']['n'], 3)
        top = wings(10**9, ('buom', 7, 1), ('rong', 0, 3))
        self.assertEqual(W.sets(Wg(top), pin=Wg(top)['own'][0]['id']), [], 'a Huyền thoại pinned: nothing')
        # 🧬 pets: only up to the pinned pet's rank
        s, ids = pets(0, 0, 0, 2, 2, 2)
        s['journey']['pets']['walk'] = None
        self.assertEqual([r for r, _, _ in px.fuse_sets(s, pin=ids[0])], [0])
        self.assertEqual([r for r, _, _ in px.fuse_sets(s, pin=ids[3])], [0, 2])
        # 🧰 gear: an unworn one with no mates goes to +10 (the worn ones after it); only its slot and up to its rank
        s, _ = gear(('giay', 1, 3, False), ('giay', 2, 0, False), ('giay', 2, 0, False), ('giay', 2, 0, False), ('giap', 0, 0, True))
        g = X(s)['gear'][0]['id']
        self.assertEqual(px.gear_step(s, X(s), pin=g)[1]['id'], g)
        with always(px, 0):
            t, r = act(s, 'jr_pet_gear_auto', pin=g, budget=10**9, confirm=True)
        got = {x['id']: x for x in X(t)['gear']}
        self.assertEqual((got[g]['r'], got[g]['lv']), (1, 10))
        self.assertEqual(sorted((x['r'], x['lv']) for x in X(t)['gear'] if x['s'] == 'giay' and x['id'] != g), [(2, 0)] * 3,
                         'the B above it untouched')
        self.assertEqual(next(x for x in X(t)['gear'] if x['s'] == 'giap')['lv'], 0, 'another slot untouched')

    def test_nothing_locked_is_the_live_pick(self):
        """No lock, no pin: the sets of one style are those of 2.5.6 (Live checks the commands against the release
        itself); since 23/10 the two rong D are no set with the butterflies (one style a set)."""
        s = wings(10**9, ('buom', 0, 7), ('rong', 0, 2), ('tien', 1, 4), on=3)
        self.assertEqual(W.sets(Wg(s)), W.sets(Wg(s), locks=frozenset(), pin=None))
        self.assertEqual([(r, t[0]['k'], k) for r, t, k in W.sets(Wg(s))], [(0, 'buom', 2), (1, 'tien', 1)])


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
                rows={'w':lambda:s['journey']['wings']['own'],'g':lambda:s['journey']['petx']['gear'],'o':lambda:s['journey']['petw']['it']}[kind]()
                for x in ([x for x in rows if x['id']==i] if isinstance(i,str) else [rows[i]]):
                    x[k]=v
        try:
            s,r=apply_action(s,None,name,p);out.append([r.get('message'),r.get('ok'),r.get('fuse'),r.get('gear'),r.get('lost'),r.get('auto')])
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
        """jr_pet_wing_fuse, jr_pet_fuse, jr_pet_gear_up, jr_pet_gear_fuse and the four ⚡ runs with nothing 🔒 locked (and
        no pin): the journey and the answers the live release gives (same save, rolls, clock)."""
        adopt = lambda n: ['jr_pet_adopt', dict({'from': 'shop'}, breed='meo_mun', coat=0, nick=n, confirm=True), None]   # noqa: E731
        off = ['jr_pet_wing_wear', dict(id=None), None]   # 🪽 2.5.7: a worn wing lifts every pet's stats (💪), so the pets' picks compare wingless
        cmds = [['jr_pet_wing_buy', dict(style='buom', qty=12, confirm=True), None], off]
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
        # ⚡ the four runs, nothing locked: what 2.5.6 does
        cmds += [['jr_pet_wing_buy', dict(style='tien', qty=15, confirm=True), None], off,   # one style (23/10: one line a set)
                 ['jr_pet_wing_fuse_auto', dict(budget=10**8, scope='tien', confirm=True), None], off]
        cmds += [adopt(f'Ba {i}') for i in range(6)] + [['jr_pet_fuse_auto', dict(budget=10**8, confirm=True), None]]
        cmds += [['jr_pet_gear_buy', dict(slot='giap', model=0, rank=0, qty=9, confirm=True), None],
                 ['jr_pet_gear_auto', dict(budget=10**8, scope='giap', confirm=True), None]]
        cmds += [['jr_pet_wbuy', dict(id='no_hong', qty=9, confirm=True), None], ['jr_pet_wfuse_auto', dict(budget=10**8, confirm=True), None]]
        for seed in ('1', '6'):
            with self.subTest(seed=seed):
                old = json.loads(self.run_in(self.tree(RELEASES['2.5.6']), SINGLE, json.dumps(cmds), seed))
                new = json.loads(self.run_in(ROOT, SINGLE, json.dumps(cmds), seed))
                self.assertEqual(old, new)
                played = [c[0] for c, o in zip(cmds, new[1]) if o[0] != 'ERR']
                for name in ('jr_pet_wing_fuse', 'jr_pet_fuse', 'jr_pet_gear_up', 'jr_pet_gear_fuse'):
                    self.assertGreaterEqual(played.count(name), 3, name)
                for name in ('jr_pet_wing_fuse_auto', 'jr_pet_fuse_auto', 'jr_pet_gear_auto', 'jr_pet_wfuse_auto'):
                    self.assertIn(name, played)
                autos = [o[5] for o in new[1] if o[0] != 'ERR' and o[5]]
                self.assertEqual(len(autos), 4)
                self.assertTrue(all(a['n'] > 0 for a in autos), autos)

    def test_auto_saves_load_on_the_live_releases(self):
        saves = []
        s = wings(10**9, ('buom', 0, 20), ('tien', 4, 6), on=0)
        with seeded(W, 4):
            s, _ = act(s, 'jr_pet_wing_fuse_auto', budget=10**9, rid='forge-live-0001', confirm=True)
        s, _ = act(s, 'settings', forgeAnon=True)   # 📣 🕶️ an optional journey key (game/forge_news.py)
        s, _ = act(s, 'jr_pet_lock', ids=[x['id'] for x in Wg(s)['own'][:2]], on=True)   # 🔒 another (game/forge_locks.py)
        saves.append(s)
        s, _ = pets(*([0] * 9 + [4] * 3))
        with seeded(px, 4):
            s, _ = act(s, 'jr_pet_fuse_auto', budget=10**9, confirm=True)
        s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, qty=6, confirm=True)
        s, _ = act(s, 'jr_pet_lock', ids=[X(s)['gear'][1]['id'], px.all_pets(s)[0]['id']], on=True)
        with seeded(px, 4):
            s, r = act(s, 'jr_pet_gear_auto', budget=10**9, pin=X(s)['gear'][0]['id'], confirm=True)
        self.assertGreater(r['auto']['n'], 5)
        saves.append(s)
        for x in saves:
            validate_state(x)
        self.assertEqual(set(Wg(saves[0])), W.BLOCK_KEYS, 'no new save key')
        self.assertEqual(set(X(saves[1])), px.BLOCK_KEYS)
        # each save loads there, shows, and a command played there saves it with the 🔒 block untouched
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state,apply_action\n'
                'out=[]\n'
                'for s in json.load(sys.stdin):\n'
                ' validate_state(s);s=migrate_state(s);validate_state(s);public_state(s)\n'
                ' s,_=apply_action(s,None,"jr_pet_wing_wear" if s["journey"].get("wings") else "jr_pet_kennel",{"id":None} if s["journey"].get("wings") else {"pet":s["journey"]["pets"]["list"][-1]["id"],"to":"ken"});validate_state(s)\n'
                ' out.append({k:s["journey"].get(k) for k in ("wings","petx","pets","fzn","fzl")})\n'
                'print(json.dumps(out))')
        for label, rev in RELEASES.items():
            with self.subTest(release=label):
                got = json.loads(self.run_in(self.tree(rev), prog, stdin=json.dumps(saves)))
                for back, mine in zip(got, saves):
                    self.assertEqual(back['fzn'], mine['journey'].get('fzn'))
                    self.assertEqual(back['fzl'], mine['journey'].get('fzl'), '🔒 kept by the older build')
                    self.assertTrue(back['fzl'])
                self.assertEqual(got[0]['fzn'], dict(v=1, anon=True), '🕶️ kept by the older build')
                self.assertEqual([x['id'] for x in got[0]['wings']['own']], [x['id'] for x in Wg(saves[0])['own']])
                self.assertIsNone(got[0]['wings']['on'], 'the command played there (wings put away)')
                self.assertEqual(got[1]['petx']['gear'], X(saves[1])['gear'])


if __name__ == '__main__':
    unittest.main()
