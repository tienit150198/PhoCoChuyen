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
                                'Nơ', 'Kẹp tóc', 'Tóc búi', 'Tóc dài', 'Áo croptop', 'Áo baby tee')):
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
