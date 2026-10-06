"""👗 Tủ đồ 1.9.3 (góp ý #200): the new pieces kept in s['wardrobe_plus'] so a 1.9.1 worker never meets their ids."""
import copy
import json
import unittest

from game import journey as jr
from game import wardrobe as wd
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state
from live import street_data as sd
from live.street import clean_look


def player(gender='female', chapter=3, wallet=3000):
    s = new_state()
    jr.enable_story(s, 11)
    s['journey']['gender'] = gender
    s['journey']['wallet'] = wallet
    for n in range(2, chapter + 1):
        jr._unlock_chapter(s['journey'], n)
    s['journey']['chapter'] = chapter
    s['journey']['done'] = list(range(1, chapter))
    wd.migrate(s)
    validate_state(s)
    return s


def act(s, action, **p):
    return apply_action(s, None, action, p)


class Catalogue(unittest.TestCase):
    def test_counts_prices_and_gate(self):
        plus = [x for x in wd.ITEMS if x.get('plus')]
        by = {}
        for x in plus:
            by.setdefault(x['slot'], []).append(x['id'])
        dress = [i for i in by['top'] if wd.INDEX[i]['name'].startswith(('Đầm', 'Váy', 'Áo dài'))]
        skirt = [i for i in by['bottom'] if 'váy' in wd.INDEX[i]['name'].lower()]
        self.assertGreaterEqual(len(by['hair']), 8)
        self.assertGreaterEqual(len(dress) + len(skirt), 10)                       # dresses and skirts
        self.assertGreaterEqual(len(by['top']) + len(by['bottom']) - len(dress) - len(skirt), 10)   # tops, trousers
        self.assertGreaterEqual(len(by['shoes']), 4)
        self.assertGreaterEqual(len(by['acc']), 10)
        for x in plus:   # priced like the shop's other goods, sold once the shop is open
            self.assertEqual(x['need'], wd.OPEN_SHOP)
            self.assertTrue(30 <= x['price'] <= 180, x['id'])
            self.assertLessEqual(len(x['id']), 24)    # live/street.py clean_look takes ids up to 24 characters
        self.assertTrue(set(wd.BASE_INDEX).isdisjoint(wd.PLUS))
        self.assertEqual(wd.PAIRS, frozenset(f'{i}:{c}' for i in wd.BASE_TINTABLE for c in wd.COLOR_INDEX))

    def test_live_street_shows_them(self):
        look, _ = clean_look(dict(hair='toc_wolf', top='ao_bomber', bottom='quan_cargo', shoes='sneaker_chunky',
                                  acc='mu_bucket', tint={'mu_bucket': 'navy', 'quan_cargo': 'do'}), 'male')
        self.assertEqual((look['hair'], look['top'], look['acc']), ('toc_wolf', 'ao_bomber', 'mu_bucket'))
        self.assertEqual(look['tint'], {'mu_bucket': 'navy', 'quan_cargo': 'do'})
        self.assertIn('kep_toc', sd.TINTABLE)


class Rules(unittest.TestCase):
    def test_shop_gate_follows_the_chapter(self):
        s = player(chapter=2)
        self.assertFalse(wd.shop_open(s))
        self.assertIn('chương 3', wd.locked(s, 'ao_croptop'))
        with self.assertRaises(GameError):
            act(s, 'jr_wd_buy', item='ao_croptop')
        s = player(chapter=3)
        self.assertTrue(wd.shop_open(s))
        free = new_state()    # outside the story every workplace (and the shop) is open
        free['journey']['gender'] = 'male'
        self.assertTrue(wd.shop_open(free))

    def test_buy_and_wear_keep_the_old_block_old(self):
        s = player()
        s, r = act(s, 'jr_wd_buy', item='ao_bomber')
        self.assertIn('Mặc luôn', r['message'])
        self.assertEqual(s['wardrobe']['look']['top'], 'ao_quen')            # what 1.9.1 shows
        self.assertEqual(s['wardrobe_plus']['look']['top'], ['ao_bomber', 'ao_quen'])
        self.assertEqual(s['wardrobe_plus']['owned'], ['ao_bomber'])
        self.assertEqual(wd.look_of(s)['top'], 'ao_bomber')
        self.assertEqual(s['journey']['history'][-1]['label'], 'Mua sắm quần áo · Áo khoác bomber xanh rêu')
        with self.assertRaises(GameError):
            act(s, 'jr_wd_buy', item='ao_bomber')
        # an older piece in the same slot takes the new one off (it stays owned)
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_thun_kem'})
        self.assertEqual(wd.look_of(s)['top'], 'ao_thun_kem')
        self.assertNotIn('top', s['wardrobe_plus']['look'])
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_bomber', 'hair': 'toc_dai'})
        self.assertEqual(wd.look_of(s)['top'], 'ao_bomber')
        validate_state(s)

    def test_colours_live_in_the_new_block(self):
        s = player()
        s, _ = act(s, 'jr_wd_buy', item='mu_bucket')
        s, _ = act(s, 'jr_wd_unlock', color='navy')
        s, _ = act(s, 'jr_wd_color', item='mu_bucket', color='navy')
        self.assertEqual(s['wardrobe_plus']['wear'], {'mu_bucket': 'navy'})
        self.assertNotIn('mu_bucket', s['wardrobe_colors']['wear'])
        self.assertTrue(all(not x.startswith('mu_bucket:') for x in s['wardrobe_colors']['owned']))
        self.assertEqual(wd.look_of(s)['tint'], {'mu_bucket': 'navy'})
        s, _ = act(s, 'jr_wd_buy', item='quan_cargo')
        s, _ = act(s, 'jr_wd_wear', look={'tint': {'quan_cargo': 'navy'}})
        self.assertEqual(s['wardrobe_plus']['wear']['quan_cargo'], 'navy')
        self.assertNotIn('quan_cargo', (s.get('colors') or {}).get('wear', {}))
        validate_state(s)

    def test_not_owned_cannot_be_worn(self):
        s = player()
        with self.assertRaises(GameError):
            act(s, 'jr_wd_wear', look={'hair': 'toc_wolf'})

    def test_salon_outing_offers_only_older_styles(self):
        from game import outings
        ids = {x['id'] for x in outings._hair(player())}
        self.assertTrue(ids.isdisjoint(wd.PLUS))


class Save(unittest.TestCase):
    def test_an_older_build_changed_the_slot(self):
        s = player()
        s, _ = act(s, 'jr_wd_buy', item='sneaker_chunky')
        s['wardrobe']['look']['shoes'] = 'dep_lao'     # what a 1.9.1 worker's jr_wd_wear does
        self.assertEqual(wd.look_of(s)['shoes'], 'dep_lao')   # the stale entry is ignored...
        m = migrate_state(s)
        self.assertNotIn('shoes', m['wardrobe_plus']['look'])  # ...and dropped on the next load
        self.assertIn('sneaker_chunky', m['wardrobe_plus']['owned'])   # nothing bought is lost
        validate_state(m)

    def test_validation_and_repair(self):
        s = player()
        s, _ = act(s, 'jr_wd_buy', item='kep_toc')
        validate_state(s)
        for bad in (lambda b: b.update(v=2), lambda b: b.update(extra=1), lambda b: b['look'].update(top='ao_bomber'),
                    lambda b: b['owned'].append(3), lambda b: b['wear'].update(kep_toc='cam')):
            t = copy.deepcopy(s)
            bad(t['wardrobe_plus'])
            with self.assertRaises(GameError):
                validate_state(t)
            m = migrate_state(t)
            validate_state(m)
            self.assertIn('kep_toc', m['wardrobe_plus']['owned'])
        # a later build's piece is kept (owned), not drawn
        t = copy.deepcopy(s)
        t['wardrobe_plus']['owned'].append('ao_tuong_lai')
        t['wardrobe_plus']['look']['top'] = ['ao_tuong_lai', 'ao_quen']
        validate_state(t)
        self.assertEqual(wd.look_of(t)['top'], 'ao_quen')
        self.assertIn('ao_tuong_lai', migrate_state(t)['wardrobe_plus']['owned'])

    def test_the_old_block_never_holds_a_new_id(self):
        s = player(wallet=20000)
        for it in [x['id'] for x in wd.ITEMS if x.get('plus')]:
            s, _ = act(s, 'jr_wd_buy', item=it)
            look = s['wardrobe']['look']
            self.assertTrue(all(look[k] in wd.BASE_INDEX for k in wd.SLOTS), it)
            self.assertTrue(set(s['wardrobe']['owned']) <= wd.BASE_BUYABLE)
        validate_state(s)
        self.assertLess(len(json.dumps(s['wardrobe_plus'])), 1200)
        self.assertEqual(public_state(s)['wardrobe_plus'], s['wardrobe_plus'])


if __name__ == '__main__':
    unittest.main()
