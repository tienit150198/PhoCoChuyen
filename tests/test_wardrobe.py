"""👗 Tủ đồ: the player's look (game/wardrobe.py, art in public/js/v4/look.js)."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from game import journey as jr
from game import wardrobe as wd
from game.content import CAREERS, public_content
from game.engine import (GameError, apply_action, migrate_state, needs_migration, new_state, public_state,
                         validate_state)
from game.storage import Store

ROOT = Path(__file__).resolve().parents[1]
LOOK_JS = (ROOT / 'public' / 'js' / 'v4' / 'look.js').read_text(encoding='utf-8')


def story(gender='female', wallet=500):
    s = new_state()
    jr.enable_story(s, 777)
    s['journey']['gender'] = gender
    s['journey']['wallet'] = wallet
    wd.migrate(s)
    validate_state(s)
    return s


def act(s, action, **p):
    return apply_action(s, None, action, p)


class Save(unittest.TestCase):
    def test_new_state_has_no_block_until_a_gender(self):
        s = new_state()
        self.assertNotIn('wardrobe', s)
        validate_state(s)
        self.assertEqual(wd.look_of(s), wd.default_look(None))
        s, _ = act(s, 'jr_profile', name='Lan', gender='female')
        self.assertEqual(s['wardrobe'], dict(v=1, look=wd.default_look('female'), owned=[]))

    def test_old_save_migrates_to_the_look_it_had(self):
        for g, hair, bottom in (('male', 'toc_ngan', 'quan_xam'), ('female', 'toc_bui', 'quan_kem')):
            s = new_state()
            s['journey']['gender'] = g
            m = migrate_state(s)
            self.assertEqual(m['wardrobe']['look']['hair'], hair)
            self.assertEqual(m['wardrobe']['look']['bottom'], bottom)
            self.assertEqual(m['wardrobe']['look']['top'], 'ao_quen')
            self.assertTrue(m['wardrobe']['look']['uniform'])
            validate_state(m)
        # No gender yet: nothing is added (the neutral default is drawn).
        self.assertNotIn('wardrobe', migrate_state(new_state()))

    def test_migration_through_the_store(self):
        with tempfile.TemporaryDirectory() as td:
            store = Store(Path(td) / 'w.db')
            token, _, _ = store.session()
            old = new_state()
            old['journey']['gender'] = 'male'
            with store.connect() as db:
                db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(old), store.key(token)))
            s, _, _ = store.read(token)
            # A plain read writes nothing new; the view and the next command migrate it.
            self.assertEqual(public_state(s)['wardrobe']['look']['hair'], 'toc_ngan')
            store.command(token, 'req-wd-0000', store.read(token)[1], None, 'jr_seen', {'ids': ['x']})
            self.assertEqual(store.read(token)[0]['wardrobe']['look']['hair'], 'toc_ngan')
            store.command(token, 'req-wd-0001', store.read(token)[1], None, 'jr_wd_wear', {'look': {'hair': 'toc_dai', 'uniform': False}})
            s, _, _ = store.read(token)
            self.assertEqual(s['wardrobe']['look']['hair'], 'toc_dai')
            self.assertFalse(s['wardrobe']['look']['uniform'])
            store.close_pool()

    def test_strict_validation(self):
        base = story()
        bad = [
            lambda w: w.update(extra=1),
            lambda w: w.update(v=2),
            lambda w: w['look'].update(hair='toc_tim'),
            lambda w: w['look'].update(hair='ao_len'),          # an id of another slot
            lambda w: w['look'].update(uniform='yes'),
            lambda w: w['look'].pop('shoes'),
            lambda w: w['look'].update(cape='x'),
            lambda w: w.update(owned=['toc_ngan']),             # free items are never "owned"
            lambda w: w.update(owned=['ao_len', 'ao_len']),
            lambda w: w.update(owned='ao_len'),
        ]
        for i, breaks in enumerate(bad):
            s = copy.deepcopy(base)
            breaks(s['wardrobe'])
            with self.assertRaises(GameError, msg=i):
                validate_state(s)

    def test_repair_of_a_newer_or_edited_block(self):
        s = story('male')
        s['wardrobe'] = dict(v=2, look=dict(hair='toc_xoan', cape='do', top='ao_tuong_lai', uniform=False),
                             owned=['toc_xoan', 'toc_ngan', 'hat_2030'])
        m = migrate_state(s)
        self.assertEqual(m['wardrobe']['look']['hair'], 'toc_xoan')
        self.assertEqual(m['wardrobe']['look']['top'], 'ao_quen')
        self.assertFalse(m['wardrobe']['look']['uniform'])
        self.assertEqual(m['wardrobe']['owned'], ['toc_xoan'])
        validate_state(m)

    def test_older_validators_ignore_the_key(self):
        # validate_state has no list of root keys: an older build never looks at s['wardrobe'].
        import inspect
        from game import engine
        src = inspect.getsource(engine.validate_state)
        self.assertNotIn('set(s)', src)
        self.assertNotIn('wardrobe', src)

    def test_public_state_carries_the_small_block(self):
        s = story()
        v = public_state(s)
        self.assertEqual(v['wardrobe'], s['wardrobe'])
        self.assertLess(len(json.dumps(v['wardrobe'])), 400)

    def test_gender_change_moves_an_untouched_look_only(self):
        s = story('female')
        s, _ = act(s, 'jr_profile', gender='male')
        self.assertEqual(s['wardrobe']['look'], wd.default_look('male'))
        s, _ = act(s, 'jr_wd_wear', look={'hair': 'toc_dai'})
        s, _ = act(s, 'jr_profile', gender='female')
        self.assertEqual(s['wardrobe']['look']['hair'], 'toc_dai')


class Wear(unittest.TestCase):
    def test_free_items_and_uniform(self):
        s = story()
        s, r = act(s, 'jr_wd_wear', look={'hair': 'toc_dai', 'shade': 'mau_den', 'skin': 'da_ngam', 'uniform': False})
        self.assertIn('thay đồ', r['message'])
        self.assertEqual(s['wardrobe']['look']['skin'], 'da_ngam')
        s2, r = act(s, 'jr_wd_wear', look={'hair': 'toc_dai'})
        self.assertIn('đúng bộ', r['message'])

    def test_rejects_unknown_or_locked(self):
        s = story()
        for look in ({'hair': 'ao_len'}, {'hat': 'non_la'}, {'top': 'khong_co'}, {'uniform': 1}):
            with self.assertRaises(GameError):
                act(s, 'jr_wd_wear', look=look)
        for iid in ('ao_len', 'ao_cuoi', 'vest_cuoi', 'ao_vest', 'mau_bach_kim', 'kinh_ram', 'ao_hoa'):
            with self.assertRaises(GameError, msg=iid):
                act(s, 'jr_wd_wear', look={wd.INDEX[iid]['slot']: iid})
        with self.assertRaises(GameError):
            act(s, 'jr_wd_wear', look={})

    def test_unlocks(self):
        s = story()
        s['journey']['titles']['st_office'] = 3
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_vest'})
        s['marriage'] = dict(v=1, applied=[], sticker=True, weddings=1,
                             spouse=dict(name='Minh', status='married', since=2, wed=5, date='2026-09-01'))
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_cuoi'})
        self.assertEqual(s['wardrobe']['look']['top'], 'ao_cuoi')
        # After a divorce the wedding outfit stays on until changed, but cannot be put back on.
        s['marriage']['spouse'] = None
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_cuoi', 'hair': 'toc_dai'})
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_quen'})
        with self.assertRaises(GameError):
            act(s, 'jr_wd_wear', look={'top': 'ao_cuoi'})
        # Maturity level 3 opens the sunglasses.
        for cid in list(s['careers'])[:1]:
            s['careers'][cid]['xp'] = 400
        self.assertGreaterEqual(wd._level(s), 3)
        s, _ = act(s, 'jr_wd_wear', look={'acc': 'kinh_ram'})


class Buy(unittest.TestCase):
    def test_buy_pays_the_wallet_with_a_ledger_row(self):
        s = story(wallet=100)
        s, r = act(s, 'jr_wd_buy', item='ao_len')
        self.assertEqual(s['journey']['wallet'], 20)
        self.assertEqual(s['wardrobe']['owned'], ['ao_len'])
        self.assertEqual(s['wardrobe']['look']['top'], 'ao_len')
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['kind'], row['label']), (-80, 'life', 'Mua sắm quần áo · Áo len mùa đông'))
        with self.assertRaises(GameError):
            act(s, 'jr_wd_buy', item='ao_len')          # already owned
        with self.assertRaises(GameError):
            act(s, 'jr_wd_buy', item='ao_hoodie')       # 90 xu, wallet has 20
        # Owned: wearable later without paying again.
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_quen'})
        s, _ = act(s, 'jr_wd_wear', look={'top': 'ao_len'})
        self.assertEqual(s['journey']['wallet'], 20)

    def test_buy_without_wearing_and_bad_payloads(self):
        s = story()
        s, r = act(s, 'jr_wd_buy', item='non_la', wear=False)
        self.assertEqual(s['wardrobe']['look']['acc'], 'pk_khong')
        self.assertIn('cất vào tủ', r['message'])
        for p in ({'item': 'toc_ngan'}, {'item': 'ao_cuoi'}, {'item': 'x'}, {'item': 'mu_len', 'wear': 'yes'},
                  {'item': 'mu_len', 'extra': 1}):
            with self.assertRaises(GameError, msg=p):
                act(s, 'jr_wd_buy', **p)

    def test_staff_price_and_shop_tee(self):
        if wd.SHOP not in CAREERS:
            self.skipTest('clothing is filtered out')
        s = story()
        with self.assertRaises(GameError):
            act(s, 'jr_wd_buy', item='ao_chi_may')
        s['careers'][wd.SHOP]['started'] = True
        before = s['journey']['wallet']
        s, r = act(s, 'jr_wd_buy', item='ao_chi_may')
        self.assertEqual(before - s['journey']['wallet'], 36)      # 45 − 20 %
        self.assertIn('giá nhân viên', r['message'])
        s, _ = act(s, 'jr_wd_buy', item='ao_dai')
        self.assertEqual(s['journey']['history'][-1]['amount'], -128)  # 160 − 20 %
        self.assertEqual(s['journey']['history'][-1]['career'], wd.SHOP)

    def test_failed_purchase_changes_nothing(self):
        s = story(wallet=10)
        before = copy.deepcopy(s)
        with self.assertRaises(GameError):
            act(s, 'jr_wd_buy', item='bot_den')
        self.assertEqual(s, before)


class Colors(unittest.TestCase):
    """Màu phụ kiện (1.3, góp ý #70): Màu gốc free, another colour unlocked once per accessory + colour."""

    def with_hat(self, wallet=200):
        s = story(wallet=wallet)
        s, _ = act(s, 'jr_wd_buy', item='mu_len')            # 50 xu
        return s

    def test_unlock_pricing_and_the_ledger(self):
        s = self.with_hat(200)
        self.assertNotIn('wardrobe_colors', s)                # nothing until the first colour
        s, r = act(s, 'jr_wd_color', item='mu_len', color='hong', buy=True)
        self.assertEqual(s['journey']['wallet'], 130)
        self.assertIn('mở khóa màu Hồng pastel cho Mũ len', r['message'])
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['kind'], row['label']), (-20, 'life', 'Mở khóa màu phụ kiện · Mũ len · Hồng pastel'))
        self.assertEqual(s['wardrobe_colors'], dict(v=1, wear={'mu_len': 'hong'}, owned=['mu_len:hong']))
        self.assertEqual(wd.look_of(s)['tint'], {'mu_len': 'hong'})
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='vang', buy=True)   # ánh kim: 30 xu
        self.assertEqual(s['journey']['wallet'], 100)
        # Unlocked once: switching back and forth (and to Màu gốc) is free.
        for col in ('hong', 'goc', 'vang', 'hong'):
            s, _ = act(s, 'jr_wd_color', item='mu_len', color=col)
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='vang', buy=True)   # already open: no second charge
        self.assertEqual(s['journey']['wallet'], 100)
        self.assertEqual(s['wardrobe_colors']['wear'], {'mu_len': 'vang'})
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='goc')
        self.assertEqual(s['wardrobe_colors']['wear'], {})
        self.assertNotIn('tint', wd.look_of(s))
        # Per accessory: pink on the hat does not open pink for the glasses.
        s, _ = act(s, 'jr_wd_buy', item='kinh_tron')
        with self.assertRaises(GameError):
            act(s, 'jr_wd_color', item='kinh_tron', color='hong')
        validate_state(s)

    def test_staff_price(self):
        if wd.SHOP not in CAREERS:
            self.skipTest('clothing is filtered out')
        s = self.with_hat(200)
        s['careers'][wd.SHOP]['started'] = True
        before = s['journey']['wallet']
        s, r = act(s, 'jr_wd_color', item='mu_len', color='mint', buy=True)
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='bac', buy=True)
        self.assertEqual(before - s['journey']['wallet'], 16 + 24)
        self.assertIn('giá nhân viên', r['message'])

    def test_locked_colour_cannot_be_used(self):
        s = self.with_hat()
        with self.assertRaises(GameError):
            act(s, 'jr_wd_color', item='mu_len', color='do')                 # not unlocked, no buy
        with self.assertRaises(GameError):
            act(s, 'jr_wd_wear', look={'tint': {'mu_len': 'do'}})
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='do', buy=True, wear=False)
        s, _ = act(s, 'jr_wd_wear', look={'acc': 'pk_khong'})
        s, r = act(s, 'jr_wd_wear', look={'acc': 'mu_len', 'tint': {'mu_len': 'goc'}})
        self.assertEqual((s['wardrobe']['look']['acc'], s['wardrobe_colors']['wear']), ('mu_len', {}))
        s, _ = act(s, 'jr_wd_wear', look={'tint': {'mu_len': 'do'}})
        self.assertEqual(s['wardrobe_colors']['wear'], {'mu_len': 'do'})
        # An accessory not bought yet: its colour cannot be unlocked (try it on first, buy it, then the colour).
        with self.assertRaises(GameError):
            act(s, 'jr_wd_color', item='no_toc', color='hong', buy=True)
        # Locked by level: the sunglasses' colours wait too.
        with self.assertRaises(GameError):
            act(s, 'jr_wd_color', item='kinh_ram', color='hong', buy=True)

    def test_wallet_never_goes_below_zero(self):
        s = self.with_hat(60)                                  # 10 xu left
        before = copy.deepcopy(s)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_wd_color', item='mu_len', color='hong', buy=True)
        self.assertIn('Ví chưa đủ 20 xu', str(e.exception))
        self.assertEqual(s, before)
        self.assertEqual(s['journey']['wallet'], 10)

    def test_bad_payloads(self):
        s = self.with_hat()
        for p in ({'item': 'pk_khong', 'color': 'hong'}, {'item': 'ao_len', 'color': 'hong'}, {'item': 'mu_len', 'color': 'cau_vong'},
                  {'item': 'mu_len', 'color': 5}, {'item': 'mu_len'}, {'item': 'mu_len', 'color': 'hong', 'buy': 'yes'},
                  {'item': 'mu_len', 'color': 'hong', 'buy': True, 'extra': 1}, {'item': 'mu_len', 'color': 'hong', 'wear': 1}):
            with self.assertRaises(GameError, msg=p):
                act(s, 'jr_wd_color', **p)
        for tint in ({}, {'mu_len': 'cau_vong'}, {'ao_len': 'hong'}, 'hong', {'mu_len': None}):
            with self.assertRaises(GameError, msg=tint):
                act(s, 'jr_wd_wear', look={'tint': tint})

    def test_strict_validation_of_the_block(self):
        s = self.with_hat()
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='hong', buy=True)
        bad = [
            lambda c: c.update(extra=1),
            lambda c: c.update(v=2),
            lambda c: c.update(owned=['mu_len:cau_vong']),
            lambda c: c.update(owned=['pk_khong:hong']),
            lambda c: c.update(owned=['mu_len:hong', 'mu_len:hong']),
            lambda c: c.update(owned='mu_len:hong'),
            lambda c: c['wear'].update(mu_len='do'),           # worn but never unlocked
            lambda c: c['wear'].update(ao_len='hong'),
            lambda c: c.update(wear=['mu_len']),
        ]
        for i, breaks in enumerate(bad):
            t = copy.deepcopy(s)
            breaks(t['wardrobe_colors'])
            with self.assertRaises(GameError, msg=i):
                validate_state(t)

    def test_old_saves_and_a_newer_block(self):
        s = story()                                           # a 1.2 save: no colour key at all
        validate_state(migrate_state(s))
        self.assertNotIn('tint', wd.look_of(s))
        self.assertNotIn('wardrobe_colors', migrate_state(s))
        s['wardrobe_colors'] = dict(v=2, wear={'mu_len': 'cau_vong', 'kinh_tron': 'hong', 'no_toc': 'do'},
                                    owned=['mu_len:cau_vong', 'kinh_tron:hong', 'kinh_tron:hong', 'x'], glitter=True)
        m = migrate_state(s)
        self.assertEqual(m['wardrobe_colors'], dict(v=1, wear={'kinh_tron': 'hong'}, owned=['kinh_tron:hong']))
        validate_state(m)

    def test_the_look_block_keeps_its_shape_for_older_builds(self):
        # Colours live in their own root key: s['wardrobe'] passes the 1.2 validator unchanged, so a rollback
        # neither refuses nor "repairs" the save, and the paid colours are still there afterwards.
        s = self.with_hat()
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='navy', buy=True)
        s, _ = act(s, 'jr_wd_wear', look={'tint': {'mu_len': 'goc'}, 'hair': 'toc_dai'})
        self.assertEqual(set(s['wardrobe']), wd.BLOCK_KEYS)
        self.assertEqual(set(s['wardrobe']['look']), wd.LOOK_KEYS)
        wd._validate_look(s)
        before = copy.deepcopy(s['wardrobe'])
        wd.migrate(s)
        self.assertEqual(s['wardrobe'], before)

    def test_public_state_and_content(self):
        s = self.with_hat()
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='lavender', buy=True)
        v = public_state(s)
        self.assertEqual(v['wardrobe_colors'], s['wardrobe_colors'])
        self.assertLess(len(json.dumps(v['wardrobe_colors'])), 200)
        c = public_content()['journey']['wardrobe']
        self.assertEqual([x['id'] for x in c['colors']], [x['id'] for x in wd.COLORS])
        self.assertEqual(c['tintable'], list(wd.TINTABLE))
        self.assertTrue(all(15 <= x['price'] <= 40 for x in c['colors']))
        self.assertGreaterEqual(len(wd.COLORS), 8)
        shades = [x['id'] for x in wd.ITEMS if x['slot'] == 'shade']
        self.assertEqual(sorted(c['match']), sorted(shades))   # a hint for every hair shade
        for ids in c['match'].values():
            self.assertTrue(set(ids) <= set(wd.COLOR_INDEX))

    def test_art_has_every_colour(self):
        js = re.search(r'export const ACC_COLORS=Object\.freeze\(Object\.assign\(Object\.create\(null\),\{(.*?)\}\)\);', LOOK_JS, re.S).group(1)
        self.assertEqual(re.findall(r'(\w+):\{c:', js), [x['id'] for x in wd.COLORS])
        for iid in wd.TINTABLE:   # every recolourable accessory has its own colours (Màu gốc) in the art
            self.assertRegex(LOOK_JS, r"\b%s:\{c:'#" % iid)


class ClientData(unittest.TestCase):
    def test_content_lists_every_item(self):
        c = public_content()['journey']['wardrobe']
        self.assertEqual([x['id'] for x in c['items']], [x['id'] for x in wd.ITEMS])
        self.assertEqual([x['id'] for x in c['slots']], list(wd.SLOTS))
        for x in c['items']:
            self.assertIn(x['slot'], wd.SLOTS)
            self.assertTrue(x['name'])
            if x['need'] and x['need'].startswith('title:'):
                self.assertIn(x['need'][6:], jr.TITLE_INDEX)
        for slot in wd.SLOTS:   # a free basic in every slot
            self.assertTrue(any(x['slot'] == slot and not x['price'] and not x['need'] for x in wd.ITEMS), slot)

    def test_every_item_has_art_and_the_same_defaults(self):
        for x in wd.ITEMS:
            self.assertRegex(LOOK_JS, r'\b%s:\{' % re.escape(x['id']), x['id'])
        js = json.loads(re.search(r'const DEFAULTS=(\{.*?\});\n', LOOK_JS).group(1))
        self.assertEqual(js['male'], wd.default_look('male'))
        self.assertEqual(js['female'], wd.default_look('female'))
        self.assertEqual(js['none'], wd.default_look(None))


if __name__ == '__main__':
    unittest.main()
