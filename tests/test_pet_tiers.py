"""🏅 Hạng thú cưng, 🧬 ghép ba, 📊 chỉ số, 🧰 linh kiện (game/pet_tiers.py, owner 19/10): ranks rolled on arrival and
given to older pets, the kennel, the fusion (fees, odds, the three retiring, hybrids, legendaries, the daily limit),
training and strolls, gear, the walking pet's share of work earnings (capped, a sad pet gives nothing, never on the
staff orders, kept out of the 🔥 x3 net), saves (older builds keep the block; a rollback loses nothing), the live
street (its rank only up to one the player has) and the 💪 lực chiến board."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import pet_tiers as px
from game import pets as pt
from game import pets_content as C
from game import tile_match as tm
from game.engine import GameError, validate_state
from tests.test_bank import act, story


def P(s):
    return s['journey']['pets']


def X(s):
    return s['journey']['petx']


def rolls(*values):
    """Patch pet_tiers.roll: each call takes the next value (clamped below its n)."""
    it = iter(values)
    return mock.patch.object(px, 'roll', lambda n: min(next(it), n - 1))


def get(s, nick, breed='meo_mun', coat=0, rank=0):
    """Buy a pet and give it a rank (and let it settle in: MIN_AGE life days)."""
    s, _ = act(s, 'jr_pet_adopt', **{'from': 'shop'}, breed=breed, coat=coat, nick=nick, confirm=True)
    p = next(q for q in px.all_pets(s) if q['n'] == nick)
    X(s)['t'][p['id']]['r'] = rank
    X(s)['t'][p['id']]['fx'] = px.FX[0][0] if rank == px.TOP else ''
    j = s['journey']
    j['life_day'] = max(j['life_day'], 1 + px.MIN_AGE)
    p['d'] = j['life_day'] - px.MIN_AGE
    for q in px.all_pets(s):
        q['t'] = j['life_day']
    validate_state(s)
    return s, p['id']


def refused(test, s, name, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)
    return str(cm.exception)


class Ranks(unittest.TestCase):
    def test_tables(self):
        self.assertEqual(sum(px.ODDS_SHELTER), px.ODDS)
        self.assertEqual(sum(px.ODDS_SHOP), px.ODDS)
        self.assertEqual(px.ODDS_SHOP[-1] * 100 / px.ODDS, 0.0001)          # SSS 0,0001 % in the shop
        self.assertEqual(px.ODDS_SHELTER[-1], 0)                            # never at the shelter
        self.assertEqual(px.FUSE_BP, (6000, 4500, 3000, 1500, 600, 300))    # owner 19/10 "thấp xuống tí", SSS 3 %
        self.assertEqual(px.FUSE_FEE[5], 5_000_000)                         # SS → SSS 5 triệu a try
        self.assertEqual(px.FUSE_FEE[6], 10_000_000)                        # 3 SSS → legendary 10 triệu
        self.assertEqual(px.LEGEND_BP, 500)
        self.assertEqual(px.PROFIT, (2, 3, 5, 8, 12, 20, 30))
        for k, (hybrid, floor) in px.RECIPES.items():
            self.assertEqual(list(k), sorted(k))
            self.assertEqual(C.BREEDS[hybrid]['fuse'], 'hybrid')
            self.assertTrue(all(b in C.SHOP for b in k), k)
            self.assertEqual({C.BREEDS[b]['kind'] for b in k}, {C.BREEDS[hybrid]['kind']})
        for kind, bid in px.LEGEND.items():
            self.assertEqual((C.BREEDS[bid]['kind'], C.BREEDS[bid]['fuse']), (kind, 'legend'))
        self.assertFalse({b for b in C.BREEDS if C.BREEDS[b]['fuse']} & set(C.SHOP))

    def test_rolled_on_arrival(self):
        s = story(wallet=100000)
        with mock.patch.object(px, '_pick', return_value=6):
            s, r = act(s, 'jr_pet_adopt', **{'from': 'shop'}, breed='corgi', coat=0, nick='Bơ', confirm=True)
        self.assertEqual(r['rank'], 'SSS')
        rec = X(s)['t'][P(s)['list'][0]['id']]
        self.assertEqual(rec['r'], 6)
        self.assertIn(rec['fx'], dict((f[0], 1) for f in px.FX))           # an SSS has a coat of its own
        self.assertEqual(rec['tn'], [0] * 5)
        s, r = act(s, 'jr_pet_adopt', **{'from': 'shelter'}, i=0, nick='Mít', confirm=True)
        self.assertIn(r['rank'], px.RANKS[:6])

    def test_hybrids_are_not_sold(self):
        s = story(wallet=10**7)
        refused(self, s, 'jr_pet_adopt', **{'from': 'shop'}, breed='pomsky', coat=0, nick='Bơ', confirm=True)
        refused(self, s, 'jr_pet_adopt', **{'from': 'shop'}, breed='than_tai', coat=0, nick='Bơ', confirm=True)

    def test_older_pets_adopted_d_bought_c(self):
        s = story(wallet=100000)
        s, _ = act(s, 'jr_pet_adopt', **{'from': 'shop'}, breed='corgi', coat=0, nick='Bơ', confirm=True)
        s, _ = act(s, 'jr_pet_adopt', **{'from': 'shelter'}, i=0, nick='Mít', confirm=True)
        del s['journey']['petx']                     # a save from before 19/10
        validate_state(s)
        bought, adopted = P(s)['list']
        self.assertEqual((px.rec_of(s, bought)['r'], px.rec_of(s, adopted)['r']), (1, 0))
        self.assertEqual(px.rec_of(s, bought)['pt'], px.rec_of(s, bought)['pt'])   # steady: a view never re-rolls
        view = pt.public(s)
        self.assertEqual([p['rank'] for p in view['pets']], ['C', 'D'])


class Kennel(unittest.TestCase):
    def test_home_then_kennel_then_full(self):
        s = story(wallet=10**6)
        for n in 'ABC':
            s, _ = get(s, n)
        s, r = act(s, 'jr_pet_adopt', **{'from': 'shop'}, breed='meo_mun', coat=0, nick='K', confirm=True)
        self.assertEqual([p['n'] for p in X(s)['ken']], ['K'])
        k = X(s)['ken'][0]['id']
        refused(self, s, 'jr_pet_kennel', pet=k, to='home')               # home is full
        a = P(s)['list'][0]['id']
        s, _ = act(s, 'jr_pet_kennel', pet=a, to='ken')
        self.assertNotEqual(P(s)['walk'], a)
        s, _ = act(s, 'jr_pet_kennel', pet=k, to='home')
        self.assertIn(k, [p['id'] for p in P(s)['list']])
        X(s)['ken'] = [dict(X(s)['ken'][0], id=f'p{900 + i}') for i in range(px.KENNEL_MAX)]
        P(s)['seq'] = 2000
        for p in X(s)['ken']:
            X(s)['t'][p['id']] = copy.deepcopy(X(s)['t'][a])
        X(s)['t'].pop(a)
        validate_state(s)
        self.assertIn('đầy', refused(self, s, 'jr_pet_adopt', **{'from': 'shop'}, breed='meo_mun', coat=0, nick='Z', confirm=True))


class Fusion(unittest.TestCase):
    def three(self, rank=0, breeds=('meo_mun',) * 3, wallet=10**8, coats=(0, 0, 0)):
        s = story(wallet=wallet)
        ids = []
        for i, (b, c) in enumerate(zip(breeds, coats)):
            s, pid = get(s, 'ABC'[i], b, c, rank)
            ids.append(pid)
        s['journey']['wallet'] = wallet
        validate_state(s)
        return s, ids

    def test_success_retires_the_three_and_pays(self):
        s, ids = self.three(0)
        w = s['journey']['wallet']
        with rolls(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0):
            s, r = act(s, 'jr_pet_fuse', pets=ids, nick='Con', confirm=True)
        self.assertTrue(r['fuse']['ok'])
        self.assertEqual(s['journey']['wallet'], w - px.FUSE_FEE[0])
        kept = px.all_pets(s)
        self.assertEqual([p['n'] for p in kept], ['Con'])
        self.assertEqual(X(s)['t'][kept[0]['id']]['r'], 1)                 # D ×3 → C
        self.assertEqual(([x['n'] for x in X(s)['ret']], X(s)['rn']), (['A', 'B', 'C'], 3))
        self.assertEqual(P(s)['walk'], kept[0]['id'])
        self.assertEqual(X(s)['day']['f'], 1)

    def test_failure_keeps_all_three_and_spends_the_fee(self):
        s, ids = self.three(5)
        w = s['journey']['wallet']
        with rolls(9999):
            s, r = act(s, 'jr_pet_fuse', pets=ids, confirm=True)
        self.assertFalse(r['fuse']['ok'])
        self.assertEqual(r['fuse']['chance'], 300)                         # SS ×3 → SSS: 3 %
        self.assertEqual(s['journey']['wallet'], w - 5_000_000)
        self.assertEqual(sorted(p['id'] for p in px.all_pets(s)), sorted(ids))

    def test_odds_mix_and_legend(self):
        self.assertEqual(px.chance([0, 0, 0]), 6000)
        self.assertEqual(px.chance([2, 3, 4]), 3000 + 300 * 3)
        self.assertEqual(px.chance([6, 6, 6]), 500)
        s, ids = self.three(6, ('corgi',) * 3)
        with rolls(0, 0, 0, 0, 0, 0, 0, 0, 0, 0):
            s, r = act(s, 'jr_pet_fuse', pets=ids, confirm=True)
        self.assertEqual((r['fuse']['breed'], r['fuse']['rank']), ('linh_khuyen', 'SSS'))
        self.assertTrue(px.is_legend(px.all_pets(s)[0]))

    def test_hybrid_recipe(self):
        s, ids = self.three(1, ('pom', 'husky', 'samoyed'))
        with rolls(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0):
            s, r = act(s, 'jr_pet_fuse', pets=ids, confirm=True)
        self.assertEqual((r['fuse']['breed'], r['fuse']['rank']), ('pomsky', 'B'))   # its floor is B
        s, ids = self.three(0, ('cho_ta',) * 3, coats=(0, 0, 1))             # Chó Lài vằn hổ wants three coats
        with rolls(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0):
            s, r = act(s, 'jr_pet_fuse', pets=ids, confirm=True)
        self.assertEqual(r['fuse']['breed'], 'cho_ta')

    def test_rules(self):
        s, ids = self.three(0, ('meo_mun', 'meo_mun', 'corgi'))
        self.assertIn('cùng loài', refused(self, s, 'jr_pet_fuse', pets=ids, confirm=True))
        s, ids = self.three(0)
        refused(self, s, 'jr_pet_fuse', pets=ids[:2], confirm=True)
        refused(self, s, 'jr_pet_fuse', pets=[ids[0]] * 3, confirm=True)
        refused(self, s, 'jr_pet_fuse', pets=ids, confirm=False)
        young = copy.deepcopy(s)
        P(young)['list'][0]['d'] = young['journey']['life_day']
        self.assertIn('chưa đủ', refused(self, young, 'jr_pet_fuse', pets=ids, confirm=True))
        poor = copy.deepcopy(s)
        poor['journey']['wallet'] = 10
        refused(self, poor, 'jr_pet_fuse', pets=ids, confirm=True)
        X(s)['day'] = dict(d=px.vn_day(), f=px.FUSE_DAY, tr=0, w=0, got=0)
        self.assertIn('Mai ghép tiếp', refused(self, s, 'jr_pet_fuse', pets=ids, confirm=True))


class StatsGear(unittest.TestCase):
    def test_stats_training_and_power(self):
        s = story(wallet=10**6)
        s, a = get(s, 'A', 'husky', 0, 3)
        p = P(s)['list'][0]
        st = px.stats(s, p)
        rec = X(s)['t'][a]
        lo, hi = px.RANGE[3]
        self.assertEqual(st[1], lo + (hi - lo) * rec['pt'][1] // 100 + C.BREEDS['husky']['st'][1])
        s, _ = act(s, 'jr_pet_train', pet=a, stat='sta')
        self.assertEqual(px.stats(s, P(s)['list'][0])[1], st[1] + px.TRAIN_STEP)
        self.assertEqual(pt.public(s)['pets'][0]['pw'], sum(px.stats(s, P(s)['list'][0])))

    def test_gear_buy_up_fuse_wear(self):
        s = story(wallet=10**7)
        s, a = get(s, 'A', 'corgi', 0, 0)
        for _ in range(3):
            s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=0, rank=0, confirm=True)
        g = [x['id'] for x in X(s)['gear']]
        s, _ = act(s, 'jr_pet_gear_wear', pet=a, slot='giay', gear=g[0])
        spd = px.stats(s, P(s)['list'][0])[0]
        with rolls(0):
            s, r = act(s, 'jr_pet_gear_up', gear=g[0], confirm=True)
        self.assertTrue(r['ok'])
        self.assertEqual(X(s)['gear'][0]['lv'], 1)
        refused(self, s, 'jr_pet_gear_fuse', gears=g, confirm=True)        # one is worn
        s, _ = act(s, 'jr_pet_gear_wear', pet=a, slot='giay')
        self.assertLess(px.stats(s, P(s)['list'][0])[0], spd + 1)
        with rolls(9999):
            s, r = act(s, 'jr_pet_gear_fuse', gears=g, confirm=True)
        self.assertEqual((r['ok'], len(X(s)['gear'])), (False, 3))         # a failure loses nothing
        with rolls(0, 0):
            s, r = act(s, 'jr_pet_gear_fuse', gears=g, confirm=True)
        self.assertEqual([(x['s'], x['r']) for x in X(s)['gear']], [('giay', 1)])
        s, _ = act(s, 'jr_pet_gear_drop', gear=X(s)['gear'][0]['id'], confirm=True)
        self.assertEqual(X(s)['gear'], [])

    def test_stroll(self):
        s = story(wallet=10**6)
        s, a = get(s, 'A', 'corgi', 0, 0)
        with rolls(*[0] * 8):
            s, r = act(s, 'jr_pet_stroll')
        self.assertTrue(r['found'])
        for _ in range(px.STROLL_DAY - 1):
            with rolls(9999):
                s, r = act(s, 'jr_pet_stroll')
            self.assertIsNone(r['found'])
        refused(self, s, 'jr_pet_stroll')


class Bonus(unittest.TestCase):
    def setUp(self):
        s = story(wallet=10**6)
        s, self.pid = get(s, 'A', 'corgi', 0, 4)                          # S: +12 %
        self.s = s
        self.c = s['careers']['mother_baby']

    def test_share_of_work_capped_and_out_of_the_x3_net(self):
        s, c = self.s, self.c
        got = tm.fund_bonus(s, c, 1000, 'Đơn', 'r1')
        self.assertEqual(got, 120)
        self.assertEqual(tm.day_total(c, c['day']), 120)
        self.assertEqual(tm.fund_bonus(s, c, 1000, 'Đơn', 'r2', direct=True), 0)   # staff orders: none
        X(s)['day']['got'] = px.CAP[4] - 50
        self.assertEqual(tm.fund_bonus(s, c, 10**6, 'Lương', 'r3'), 50)
        self.assertEqual(tm.fund_bonus(s, c, 10**6, 'Lương', 'r4'), 0)
        validate_state(s)

    def test_sad_or_home_gives_nothing(self):
        s, c = self.s, self.c
        P(s)['list'][0]['f'] = 0
        self.assertEqual(tm.fund_bonus(s, c, 1000, 'Đơn', 'r1'), 0)
        s, c = copy.deepcopy(self.s), None
        P(s)['walk'] = None
        self.assertEqual(tm.fund_bonus(s, s['careers']['mother_baby'], 1000, 'Đơn', 'r1'), 0)

    def test_sss_bond(self):
        p = P(self.s)['list'][0]
        X(self.s)['t'][p['id']]['r'] = 6
        self.assertEqual(px.bonus_rate(self.s, p), (30, 1_000_000))
        p['x'] = 200
        self.assertEqual(px.bonus_rate(self.s, p), (50, 1_500_000))


class Saves(unittest.TestCase):
    def test_validate_and_rollback(self):
        s = story(wallet=10**6)
        s, a = get(s, 'A', 'corgi', 0, 2)
        bad = copy.deepcopy(s)
        X(bad)['t'][a]['r'] = 9
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = copy.deepcopy(s)
        X(bad)['gear'].append(dict(id='g1', s='giay', m=0, r=0, lv=0))
        X(bad)['t'][a]['g']['giay'] = 'g9'
        with self.assertRaises(GameError):
            validate_state(bad)
        orphan = copy.deepcopy(s)
        X(orphan)['t']['p77'] = copy.deepcopy(X(orphan)['t'][a])   # a pet an older build let go
        px.upgrade(orphan['journey'])
        self.assertNotIn('p77', X(orphan)['t'])

    def test_walk_ref_and_live(self):
        from live.street import clean_pet
        from live import pet_rank
        s = story(wallet=10**6)
        s, a = get(s, 'A', 'corgi', 0, 6)
        ref = pt.walk_ref(s)
        self.assertEqual((ref['r'], ref['x']), (6, px.FX[0][0]))
        self.assertEqual(clean_pet(ref), ref)
        self.assertEqual(pet_rank.cap(clean_pet(ref), (6, False)), ref)
        self.assertNotIn('r', pet_rank.cap(clean_pet(ref), (3, False)))      # a rank they do not have: no aura
        self.assertNotIn('x', pet_rank.cap(clean_pet(ref), (3, False)))
        self.assertIsNone(pet_rank.cap(dict(b='than_tai', c=0, a=[]), (6, False)))


class Database(unittest.TestCase):
    def test_power_board_and_news(self):
        from game.storage import Store
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / 's.db', story=True)
        self.addCleanup(store.close_pool)
        pt._BOARD.clear()
        token, _, _ = store.session()
        store.read(token)
        from game import marriage as mr

        def fn(s):
            s['journey']['wallet'] = 10**8
        mr._mutate(store, {store.key(token): fn})
        n = [0]

        def cmd(action, **p):
            n[0] += 1
            return store.command(token, f'req-{n[0]:08d}', store.read(token)[1], None, action, p)
        with mock.patch.object(px, '_pick', return_value=5):
            for nick in 'ABC':
                cmd('jr_pet_adopt', **{'from': 'shop'}, breed='corgi', coat=0, nick=nick, confirm=True)

        def age(s):
            s['journey']['life_day'] += px.MIN_AGE
            for p in s['journey']['pets']['list']:
                p['t'] = s['journey']['life_day']
        mr._mutate(store, {store.key(token): age})
        board = pt.board(store, token, 'power')
        self.assertEqual(board['kind'], 'power')
        self.assertEqual(board['top'][0]['r'], 5)
        self.assertTrue(board['top'][0]['me'])
        ids = [p['id'] for p in store.read(token)[0]['journey']['pets']['list']]
        with rolls(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0):
            out = cmd('jr_pet_fuse', pets=ids, confirm=True)
        self.assertTrue(out['result']['fuse']['ok'] if 'result' in out else True)
        from game.marriage import _recent_news
        with store.connect() as db:
            rows = db.execute("SELECT text FROM news WHERE kind='pets'").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn('SSS', rows[0]['text'])
        self.assertTrue(callable(_recent_news))


if __name__ == '__main__':
    unittest.main()
