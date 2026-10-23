"""👗 Tủ đồ, owner 24/10: the wedding pair opens from the engagement, and every piece is tagged nam / nữ / unisex
(game/wardrobe.py FOR_MALE / FOR_FEMALE, the client sorts and filters with them: tests/wardrobe-gender.mjs)."""
import unittest

from game import wardrobe as wd
from game.engine import GameError, migrate_state, validate_state
from tests.test_wardrobe import act, story


def spouse(status, **extra):
    return dict(v=1, applied=[], sticker=status == 'married', weddings=int(status == 'married'),
                spouse=dict(name='Minh', status=status, since=2, wed=5 if status == 'married' else None,
                            date='2026-09-01' if status == 'married' else None, **extra))


class Tags(unittest.TestCase):
    def test_every_item_is_tagged(self):
        self.assertTrue(wd.ITEMS)
        for it in wd.ITEMS:
            self.assertIn(it.get('g'), wd.GENDERS, it['id'])
        ids = set(wd.INDEX)
        self.assertLessEqual(wd.FOR_FEMALE, ids, wd.FOR_FEMALE - ids)
        self.assertLessEqual(wd.FOR_MALE, ids, wd.FOR_MALE - ids)
        self.assertFalse(wd.FOR_FEMALE & wd.FOR_MALE)
        content = wd.content()['items']
        self.assertEqual({x['id']: x['g'] for x in content}, {x['id']: x['g'] for x in wd.ITEMS}, 'the client gets the tags')

    def test_the_tagging_rule(self):
        g = {x['id']: x['g'] for x in wd.ITEMS}
        for it in wd.ITEMS:
            name = it['name']
            if name.startswith(('Đầm', 'Váy', 'Chân váy', 'Áo dài', 'Giày búp bê', 'Giày Mary Jane', 'Bông tai', 'Khuyên tai',
                                'Nơ cài', 'Nơ lụa', 'Kẹp tóc', 'Tóc búi', 'Tóc dài thả', 'Áo croptop', 'Áo baby tee')) and ' nam' not in name:
                self.assertEqual(g[it['id']], 'female', name)
            if it['slot'] in ('shade', 'skin'):
                self.assertEqual(g[it['id']], 'unisex', name)
        self.assertEqual(g['ao_cuoi'], 'female')
        self.assertEqual(g['vest_cuoi'], 'male')
        for iid in ('ao_quen', 'ao_thun_kem', 'ao_hoodie', 'ao_so_mi', 'quan_jean', 'quan_xam', 'giay_trang', 'sneaker_chunky',
                    'mu_luoi_trai', 'kinh_tron', 'pk_khong'):
            self.assertEqual(g[iid], 'unisex', iid)
        n = {k: sum(1 for x in wd.ITEMS if x['g'] == k) for k in wd.GENDERS}
        self.assertEqual(sum(n.values()), len(wd.ITEMS))
        self.assertGreater(n['female'], 0)
        self.assertGreater(n['male'], 0)

    def test_each_gender_has_a_full_wardrobe(self):
        for gender in ('male', 'female'):
            for slot, iid in wd.default_look(gender).items():
                if slot != 'uniform':
                    self.assertIn(wd.INDEX[iid]['g'], (gender, 'unisex'), f'{gender} default {slot}: {iid}')
            for slot in wd.SLOTS:
                mine = [x for x in wd.ITEMS if x['slot'] == slot and x['g'] in (gender, 'unisex')]
                self.assertGreaterEqual(len(mine), 3, f'{gender} {slot}')
        # The wedding pair: the bride sees the áo dài cưới, the groom the vest.
        self.assertEqual([x['id'] for x in wd.ITEMS if x['need'] == 'married' and x['g'] in ('female', 'unisex')], ['ao_cuoi'])
        self.assertEqual([x['id'] for x in wd.ITEMS if x['need'] == 'married' and x['g'] in ('male', 'unisex')], ['vest_cuoi'])


class Menswear(unittest.TestCase):
    """👔 owner 24/10: ~25 more pieces for men, in every slot but colours, sold like the 1.9.2 pieces."""

    def test_counts_and_slots(self):
        self.assertEqual(len(wd.MENSWEAR), 28)
        self.assertEqual(len(set(wd.MENSWEAR)), 28)
        for iid in wd.MENSWEAR:
            it = wd.INDEX[iid]
            self.assertEqual(it['g'], 'male', iid)
            self.assertTrue(it.get('plus'), f'{iid}: saved in wardrobe_plus (an older worker never meets it)')
            self.assertEqual(it['need'], wd.OPEN_SHOP, iid)
            self.assertGreater(it['price'], 0, iid)
        n = {k: sum(1 for x in wd.ITEMS if x['g'] == k) for k in wd.GENDERS}
        self.assertEqual(n, dict(male=32, female=49, unisex=62))
        for slot, want in dict(hair=8, top=10, bottom=4, shoes=4, acc=6).items():
            self.assertEqual(sum(1 for x in wd.ITEMS if x['slot'] == slot and x['g'] == 'male'), want, slot)

    def test_prices_sit_with_similar_pieces(self):
        from game import price_index as pi
        base = {'toc_mohican': 60, 'toc_dau_dinh': 40, 'ao_dai_nam_lam': 160, 'vest_den': 180, 'so_mi_ke': 70,
                'ao_khoac_da': 170, 'quan_au_den': 80, 'giay_tay_den': 100, 'dep_quai_hau': 45, 'mu_fedora': 75}
        for iid, p in base.items():
            self.assertEqual(wd.INDEX[iid]['price'], pi.price(p), iid)
        self.assertEqual(wd.INDEX['ao_dai_nam_lam']['price'], wd.INDEX['ao_dai']['price'], 'áo dài nam = áo dài lụa')

    def test_buy_wear_colour_and_rollback_shape(self):
        from tests.test_wardrobe_plus import player
        s = player('male')   # chapter 3: Tiệm Áo Chỉ Mây is open
        for iid in ('ao_dai_nam_lam', 'quan_au_den', 'giay_tay_den', 'ca_vat', 'toc_mohican'):
            slot = wd.INDEX[iid]['slot']
            s, _ = act(s, 'jr_wd_buy', item=iid)
            self.assertEqual(wd.worn(s)[slot], iid)
            self.assertEqual(s['wardrobe']['look'][slot], wd.default_look('male')[slot], 'an older build sees the default')
        s, _ = act(s, 'jr_wd_color', item='ca_vat', color='navy', buy=True)
        self.assertEqual(wd.look_of(s)['tint']['ca_vat'], 'navy')
        validate_state(s)
        m = migrate_state(s)
        self.assertEqual(wd.worn(m)['top'], 'ao_dai_nam_lam')

    def test_live_street_and_art_know_every_piece(self):
        from pathlib import Path
        from live import street_data as sd
        js = (Path(__file__).resolve().parents[1] / 'public' / 'js' / 'v4' / 'look.js').read_text(encoding='utf-8')
        for iid in wd.MENSWEAR:
            slot = wd.INDEX[iid]['slot']
            self.assertIn(iid, sd.LOOK_IDS[slot], iid)
            self.assertIn(f'{iid}:{{', js, iid)
            if slot == 'acc':
                self.assertIn(iid, sd.TINTABLE)


class Engaged(unittest.TestCase):
    def test_single_is_locked_with_the_new_words(self):
        s = story()
        why = wd.locked(s, 'ao_cuoi')
        self.assertIn('đính hôn', why)
        with self.assertRaises(GameError):
            act(s, 'jr_wd_wear', look={'top': 'ao_cuoi'})

    def test_engaged_opens_the_wedding_pair(self):
        for g in ('female', 'male'):
            s = story(g)
            s['marriage'] = spouse('engaged')
            validate_state(s)
            self.assertIsNone(wd.locked(s, 'ao_cuoi'))
            self.assertIsNone(wd.locked(s, 'vest_cuoi'))
            mine = 'ao_cuoi' if g == 'female' else 'vest_cuoi'
            s, _ = act(s, 'jr_wd_wear', look={'top': mine})
            self.assertEqual(s['wardrobe']['look']['top'], mine)
            self.assertIn(mine, s['wardrobe_plus']['owned'])
            validate_state(s)

    def test_married_still_opens_it(self):
        s = story()
        s['marriage'] = spouse('married')
        s, _ = act(s, 'jr_wd_wear', look={'top': 'vest_cuoi'})   # anyone may wear anything
        self.assertEqual(s['wardrobe']['look']['top'], 'vest_cuoi')

    def test_a_broken_engagement_takes_nothing_away(self):
        s = story()
        s['marriage'] = spouse('engaged')
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_cuoi'})
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_quen'})
        s['marriage']['spouse'] = None   # the engagement is broken (marriage._apply_effect set=None)
        validate_state(s)
        self.assertIsNone(wd.locked(s, 'ao_cuoi'))
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_cuoi'})
        self.assertEqual(wd.worn(s)['top'], 'ao_cuoi')
        self.assertIsNotNone(wd.locked(s, 'vest_cuoi'), 'never worn: not kept')
        # the kept piece survives a load (migrate) and is still not for sale
        m = migrate_state(s)
        validate_state(m)
        self.assertIn('ao_cuoi', m['wardrobe_plus']['owned'])
        self.assertNotIn('ao_cuoi', wd._box_owned(m))
        with self.assertRaises(GameError):
            act(m, 'jr_wd_buy', item='ao_cuoi')

    def test_worn_before_this_build_is_kept_when_taken_off(self):
        # A save that put the dress on before 24/10 (nothing kept yet), then a divorce: taking it off keeps it.
        s = story()
        s['marriage'] = spouse('married')
        s['wardrobe']['look']['top'] = 'ao_cuoi'
        s['marriage']['spouse'] = None
        self.assertNotIn('wardrobe_plus', s)
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_quen'})
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_cuoi'})
        self.assertEqual(wd.worn(s)['top'], 'ao_cuoi')

    def test_buying_over_the_dress_keeps_it(self):
        s = story(wallet=900)
        s['marriage'] = spouse('engaged')
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_cuoi'})
        s['marriage']['spouse'] = None
        s, _ = act(s, 'jr_wd_buy', item='ao_hoodie')
        self.assertEqual(wd.worn(s)['top'], 'ao_hoodie')
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_cuoi'})
        self.assertEqual(wd.worn(s)['top'], 'ao_cuoi')


if __name__ == '__main__':
    unittest.main()
