"""👗 Tủ đồ thú cưng (game/pet_wardrobe.py, owner 19/10): an older save's accessories carried over as rank D pieces,
the shop (D or C, luxury never sold, season pieces only in their days, 🪽 wings), wearing, fusing three identical pieces
(no daily limit, a luxury piece from A up), the work bonus of an outfit, the look the street and the boards get, saves,
💎 premium gear models and the live street's checks."""
import copy
import unittest
from unittest import mock

from game import pet_tiers as px
from game import pet_wardrobe as pw
from game import pet_wardrobe_content as W
from game import pets as pt
from game.engine import validate_state
from tests.test_bank import act, story
from tests.test_pet_tiers import get, refused


def WB(s):
    return s['journey']['petw']


def rolls(*values):
    it = iter(values)
    return mock.patch.object(px, 'roll', lambda n: min(next(it), n - 1))


def rich():
    s = story()
    s['journey']['wallet'] = 50_000_000
    s, pid = get(s, 'Mun')
    return s, pid


class Content(unittest.TestCase):
    def test_pieces(self):
        ids = [i['id'] for i in W.ITEMS]
        self.assertEqual(len(ids), len(set(ids)))
        from game import pets_content as C
        self.assertTrue(set(C.ACC) <= set(W.ITEM))                         # the old accessories carry over
        for i in W.ITEMS:
            self.assertIn(i['slot'], W.SLOT_IDS)
            self.assertGreaterEqual(len(i['desc']), 30, i['id'])              # owner: "giới thiệu chút thông tin"
            self.assertEqual(i['price'] == 0, bool(i.get('lux')), i['id'])
            self.assertTrue(i['art'] or i['id'] in C.ACC, i['id'])
        wings = [i for i in W.ITEMS if i['slot'] == 'back' and i['art'].startswith('w_') and not i.get('lux') and not i.get('sale')]
        self.assertGreaterEqual(len(wings), 20)                                 # "mua được cánh nữa, nhiều loại"
        self.assertGreaterEqual(len({i['art'] for i in wings}), 10)
        self.assertEqual(set(W.LUX), set(W.SLOT_IDS))


class Shop(unittest.TestCase):
    def test_buy_wear_and_the_look(self):
        s, pid = rich()
        w = s['journey']['wallet']
        s, r = act(s, 'jr_pet_wbuy', id='canh_cong', confirm=True)
        self.assertEqual(s['journey']['wallet'], w - W.ITEM['canh_cong']['price'])
        s, r = act(s, 'jr_pet_wbuy', id='canh_cong', rank=1, confirm=True)
        self.assertEqual(s['journey']['wallet'], w - W.ITEM['canh_cong']['price'] * 5)   # C costs 4 times D
        refused(self, s, 'jr_pet_wbuy', id='canh_cong', rank=2, confirm=True)             # D and C only
        refused(self, s, 'jr_pet_wbuy', id='canh_phuong_hoang', confirm=True)            # luxury: never sold
        c = next(i for i in WB(s)['it'] if i['r'] == 1)
        s, _ = act(s, 'jr_pet_wwear', pet=pid, slot='back', item=c['id'])
        refused(self, s, 'jr_pet_wwear', pet=pid, slot='head', item=c['id'])
        ref = pt.walk_ref(s)
        self.assertEqual((ref['a'], ref['ar']), (['canh_cong'], [1]))
        self.assertEqual(pw.bonus_bp(s, pt.get(s)['list'][0]), pw.BONUS_BP[1])
        view = pt.public(s)['pets'][0]
        self.assertEqual((view['w'], view['wr']), ({'back': 'canh_cong'}, {'back': 1}))
        validate_state(s)

    def test_season_pieces(self):
        s, _ = rich()
        it = W.ITEM['mu_phu_thuy']
        with mock.patch.object(pw, 'vn_date', lambda: '2026-11-02'):
            refused(self, s, 'jr_pet_wbuy', id='mu_phu_thuy', confirm=True)
        with mock.patch.object(pw, 'vn_date', lambda: it['sale'][0]):
            act(s, 'jr_pet_wbuy', id='mu_phu_thuy', confirm=True)

    def test_old_accessories_and_old_commands(self):
        s, pid = rich()
        s, _ = act(s, 'jr_pet_buy', id='non_la', confirm=True)               # an older client: rank D piece
        self.assertEqual([(i['k'], i['r']) for i in WB(s)['it']], [('non_la', 0)])
        self.assertEqual(s['journey']['pets']['own']['non_la'], 1)            # kept for an older build too
        s, _ = act(s, 'jr_pet_wear', pet=pid, slot='head', id='non_la')
        self.assertEqual(pt.walk_ref(s)['a'], ['non_la'])
        # a save from before the wardrobe: its accessories become rank D pieces, worn where they were
        old = copy.deepcopy(s)
        del old['journey']['petw']
        self.assertEqual([i['k'] for i in pw.get(old)['it']], ['non_la'])
        self.assertEqual(pt.walk_ref(old)['a'], ['non_la'])


class Fuse(unittest.TestCase):
    def three(self, k='canh_cong', r=0):
        s, pid = rich()
        for _ in range(3):
            s, _ = act(s, 'jr_pet_wbuy', id=k, confirm=True)
        for i in WB(s)['it']:
            i['r'] = r
        return s, pid

    def test_fuse_three_identical(self):
        s, pid = self.three()
        s, _ = act(s, 'jr_pet_wwear', pet=pid, slot='back', item=WB(s)['it'][0]['id'])
        with rolls(9999):
            s, r = act(s, 'jr_pet_wfuse', k='canh_cong', r=0, confirm=True)
        self.assertFalse(r['ok'])
        self.assertEqual(len(WB(s)['it']), 3)
        with rolls(0, 9999):
            s, r = act(s, 'jr_pet_wfuse', k='canh_cong', r=0, confirm=True)
        self.assertTrue(r['ok'])
        self.assertEqual([(i['k'], i['r']) for i in WB(s)['it']], [('canh_cong', 1)])
        self.assertEqual(WB(s)['on'], {})                                       # the worn one was taken off
        refused(self, s, 'jr_pet_wfuse', k='canh_cong', r=1, confirm=True)    # needs three
        validate_state(s)

    def test_no_daily_limit_and_luxury_from_a(self):
        s, _ = self.three(r=3)
        WB(s)['day'] = dict(d=px.vn_day(), f=500)
        with rolls(0, 0):
            s, r = act(s, 'jr_pet_wfuse', k='canh_cong', r=3, confirm=True)
        self.assertTrue(r['lux'])
        self.assertEqual([(i['k'], i['r']) for i in WB(s)['it']], [(W.LUX['back'], 4)])
        self.assertEqual(pw.best_rank(s), (4, True))
        validate_state(s)


class Legend(unittest.TestCase):
    def test_kept_breed_is_in_the_block(self):
        s, pid = rich()
        pw.set_legend(s, pid)
        p = pt.get(s)['list'][0]
        self.assertTrue(px.is_legend(p, s))
        validate_state(s)
        bad = copy.deepcopy(s)
        WB(bad)['lg'].append('nope')
        with self.assertRaises(Exception):
            validate_state(bad)


class Gear(unittest.TestCase):
    def test_premium_models(self):
        s, pid = rich()
        w = s['journey']['wallet']
        s, r = act(s, 'jr_pet_gear_buy', slot='giay', model=7, rank=1, confirm=True)
        self.assertEqual(s['journey']['wallet'], w - px.GSHOP[1] * px.GX_MULT[4])
        g = s['journey']['petx']['gear'][0]
        self.assertEqual((g['m'], WB(s)['gm'], px.model_of(g, s)), (0, {g['id']: 4}, 7))   # an older build: a plain one
        self.assertEqual(px.gear_value(g, s), px.GBASE[1] + px.GX_BONUS[4])
        self.assertIn('Giày mây bay', r['message'])
        view = px.public(s)['gear'][0]
        self.assertEqual((view['name'], view['vip']), ('Giày mây bay', True))
        refused(self, s, 'jr_pet_gear_buy', slot='giay', model=8, rank=0, confirm=True)
        for _ in range(2):
            s, _ = act(s, 'jr_pet_gear_buy', slot='giay', model=0, rank=1, confirm=True)
        ids = [x['id'] for x in s['journey']['petx']['gear']]
        with rolls(0, 0):
            s, r = act(s, 'jr_pet_gear_fuse', gears=ids, confirm=True)
        new = s['journey']['petx']['gear'][0]
        self.assertEqual((new['r'], px.model_of(new, s), list(WB(s)['gm'])), (2, 7, [new['id']]))   # keeps the best model
        validate_state(s)
        s, _ = act(s, 'jr_pet_gear_drop', gear=new['id'], confirm=True)
        self.assertEqual(WB(s)['gm'], {})


class Live(unittest.TestCase):
    def test_street_keeps_only_what_is_owned(self):
        from live import pet_rank
        from live.street import clean_pet
        pt_ = clean_pet(dict(b='cho_ta', c=0, a=['canh_pha_le', 'vong_kim_cuong', 'zzz', 'o_bong'], ar=[6, 3, 1, 2], o=2, st='hoang_gia', lg=True))
        self.assertEqual(pt_, dict(b='cho_ta', c=0, a=['canh_pha_le', 'vong_kim_cuong'], ar=[6, 3], o=2, st='hoang_gia', lg=True))
        self.assertEqual(pet_rank.cap(pt_, (6, False, 4, False)), dict(b='cho_ta', c=0, a=['canh_pha_le'], ar=[4], o=2))
        self.assertEqual(pet_rank.cap(pt_, (6, True, 6, True)), pt_)
        self.assertEqual(pet_rank.cap(dict(b='cho_ta', c=0, a=[]), (0, False)), dict(b='cho_ta', c=0, a=[]))   # an old cache


if __name__ == '__main__':
    unittest.main()


class Myth(unittest.TestCase):
    """✨ Owner 19/10: kỳ lân, khủng long … come with a fusion to S or more (hidden odds); the game picks which one and the
    player keeps the pet or lets it turn into that one."""
    def three(self, rank, breed='meo_mun'):
        from tests.test_pet_tiers import Fusion
        return Fusion.three(None, rank, (breed,) * 3)

    def test_offer_from_s_and_the_choice(self):
        from game import pets_content as C
        self.assertGreaterEqual(len(C.MYTH), 6)
        self.assertTrue(all(not C.BREEDS[b]['shop'] for b in C.MYTH))
        refused(self, story(wallet=10**8), 'jr_pet_adopt', **{'from': 'shop'}, breed='ky_lan', coat=0, nick='X', confirm=True)
        s, ids = self.three(2)                                         # B → A: never
        with rolls(0, 0, 0, 0, 0, 0, 0), mock.patch.object(pw, 'roll', lambda n: 0):
            s, r = act(s, 'jr_pet_fuse', pets=ids, confirm=True)
        self.assertTrue(r['fuse']['ok'])
        self.assertIsNone(r['fuse']['myth'])
        s, ids = self.three(3)                                         # A → S: may
        with rolls(0, 0, 0, 0, 0, 0, 0), mock.patch.object(pw, 'roll', lambda n: 0):
            s, r = act(s, 'jr_pet_fuse', pets=ids, main=ids[1], confirm=True)
        m = r['fuse']['myth']
        self.assertEqual((m['p'], m['b']), (ids[1], C.MYTH[0]))
        self.assertIn(C.BREEDS[m['b']]['name'], r['message'])
        self.assertEqual(pt.public(s)['petw']['mo']['b'], m['b'])
        validate_state(s)
        bad = copy.deepcopy(s)
        WB(bad)['mo']['b'] = 'corgi'                                    # only a thần thú
        with self.assertRaises(Exception):
            validate_state(bad)
        refused(self, s, 'jr_pet_morph', take='yes')
        keep = copy.deepcopy(s)
        keep, r = act(keep, 'jr_pet_morph', take=False)
        self.assertEqual(next(p for p in px.all_pets(keep) if p['id'] == ids[1])['b'], 'meo_mun')
        self.assertNotIn('mo', WB(keep))
        refused(self, keep, 'jr_pet_morph', take=True)                  # answered once
        s, r = act(s, 'jr_pet_morph', take=True)
        p = next(p for p in px.all_pets(s) if p['id'] == ids[1])
        self.assertEqual((p['b'], px.rec_of(s, p)['r']), (m['b'], 4))  # the rank, name, gear stay
        self.assertIn('hóa thành', r['message'])
        validate_state(s)

    def test_no_offer_when_the_roll_misses_and_a_legend_stays_legend(self):
        s, ids = self.three(4)
        with rolls(0, 0, 0, 0, 0, 0, 0), mock.patch.object(pw, 'roll', lambda n: n - 1):
            s, r = act(s, 'jr_pet_fuse', pets=ids, confirm=True)
        self.assertIsNone(r['fuse']['myth'])
        self.assertNotIn('mo', s['journey'].get('petw') or {})
        s, ids = self.three(6)
        p = next(p for p in px.all_pets(s) if p['id'] == ids[0])
        p['b'] = 'than_tai'
        WB_ = pw._ensure(s)
        WB_['mo'] = dict(p=p['id'], b='rong_con', c=0)
        s, r = act(s, 'jr_pet_morph', take=True)
        p = next(p for p in px.all_pets(s) if p['id'] == ids[0])
        self.assertEqual(p['b'], 'rong_con')
        self.assertTrue(px.is_legend(p, s))                             # Mèo Thần Tài → rồng con, still 🌟
        validate_state(s)
