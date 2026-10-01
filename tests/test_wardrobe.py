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
    """Bảng màu: Màu gốc free; a colour unlocked once (40 xu, ánh kim 60) is free on every accessory, top, bottom and pair
    of shoes (furniture: tests/test_deco.py). 1.3.1's per-accessory colours join the wallet."""

    def with_hat(self, wallet=200):
        s = story(wallet=wallet)
        s, _ = act(s, 'jr_wd_buy', item='mu_len')            # 50 xu
        return s

    def test_unlock_once_use_on_every_kind_of_item(self):
        s = self.with_hat(500)
        self.assertNotIn('colors', s)                         # nothing until the first colour
        self.assertNotIn('wardrobe_colors', s)
        s, r = act(s, 'jr_wd_unlock', color='navy')
        self.assertEqual(s['journey']['wallet'], 410)
        self.assertIn('Đã trả 40 xu mở khóa màu Xanh navy.', r['message'])
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['kind'], row['label']), (-40, 'life', 'Mở khóa màu · Xanh navy'))
        self.assertEqual(s['colors'], dict(v=1, have=['navy'], wear={}, deco={}))
        # Mirrored for 1.3.1/1.3.2 (rollback): navy on every accessory, in the 1.3.1 shape.
        self.assertEqual(s['wardrobe_colors'], dict(v=1, wear={}, owned=[f'{i}:navy' for i in wd.TINTABLE]))
        # The accessory, the top, the bottom and the shoes: all free now.
        look = wd.look_of(s)
        for iid in (look['acc'], look['top'], look['bottom'], look['shoes']):
            s, r = act(s, 'jr_wd_color', item=iid, color='navy')
            self.assertNotIn('Đã trả', r['message'])
        self.assertEqual(s['journey']['wallet'], 410)
        self.assertEqual(wd.look_of(s)['tint'], {'mu_len': 'navy', 'ao_quen': 'navy', 'quan_kem': 'navy', 'giay_nau': 'navy'})
        self.assertEqual(s['colors']['wear'], {'ao_quen': 'navy', 'quan_kem': 'navy', 'giay_nau': 'navy'})
        self.assertEqual(s['wardrobe_colors']['wear'], {'mu_len': 'navy'})   # accessories keep their 1.3.1 home
        # Back to Màu gốc, and switching through jr_wd_wear's tint, all free.
        s, r = act(s, 'jr_wd_color', item='giay_nau', color='goc')
        self.assertEqual(r['message'], 'Giày nâu trở lại màu gốc. Mặc luôn rồi nè!')
        s, _ = act(s, 'jr_wd_wear', look={'tint': {'quan_kem': 'goc', 'mu_len': 'goc', 'giay_nau': 'navy'}})
        self.assertEqual(wd.look_of(s)['tint'], {'ao_quen': 'navy', 'giay_nau': 'navy'})
        self.assertEqual(s['journey']['wallet'], 410)
        validate_state(s)

    def test_names_do_not_contradict_the_colour(self):
        s = story(wallet=500)
        s, _ = act(s, 'jr_wd_buy', item='ao_hoodie')
        s, r = act(s, 'jr_wd_color', item='ao_hoodie', color='navy', buy=True)
        self.assertEqual(r['message'], 'Đã trả 40 xu mở khóa màu Xanh navy. Áo hoodie giờ mang màu Xanh navy. Mặc luôn rồi nè!')
        self.assertEqual(wd.item_name('ao_hoodie', 'navy'), 'Áo hoodie · Xanh navy')
        self.assertEqual(wd.item_name('ao_hoodie'), 'Áo hoodie tím')
        self.assertEqual(wd.item_name('giay_do', 'den'), 'Giày búp bê · Đen tuyền')
        self.assertEqual(wd.item_name('ao_len', 'hong'), 'Áo len mùa đông · Hồng pastel')
        for it in wd.ITEMS:                                  # a name with a colour word has a plain one
            if it['slot'] in ('top', 'bottom', 'shoes'):
                for word in ('tím', 'trắng', 'đỏ', 'đen', 'nâu', 'xám', 'kem', 'xanh'):
                    self.assertNotIn(f' {word}', f' {it["plain"].lower()}', it['id'])

    def test_metal_colours_and_the_staff_price(self):
        s = self.with_hat(300)
        s, _ = act(s, 'jr_wd_unlock', color='vang')
        self.assertEqual(s['journey']['wallet'], 190)        # ánh kim: 60
        if wd.SHOP not in CAREERS:
            return
        s['careers'][wd.SHOP]['started'] = True
        before = s['journey']['wallet']
        s, r = act(s, 'jr_wd_unlock', color='mint')
        s, _ = act(s, 'jr_wd_unlock', color='bac')
        self.assertEqual(before - s['journey']['wallet'], 32 + 48)
        self.assertIn('giá nhân viên', r['message'])
        self.assertEqual(s['journey']['history'][-1]['career'], wd.SHOP)

    def test_a_second_tap_never_pays_twice(self):
        s = self.with_hat(300)
        s, _ = act(s, 'jr_wd_unlock', color='hong')
        s, r = act(s, 'jr_wd_unlock', color='hong')
        self.assertTrue(r.get('duplicate'))
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='hong', buy=True)   # open already: no charge
        self.assertEqual(s['journey']['wallet'], 210)
        self.assertEqual(sum(1 for x in s['journey']['history'] if x['label'].startswith('Mở khóa màu')), 1)
        # Through the store: the same request sent twice is applied once.
        with tempfile.TemporaryDirectory() as td:
            store = Store(Path(td) / 'w.db')
            token, _, _ = store.session()
            st = story(wallet=100)
            with store.connect() as db:
                db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(st), store.key(token)))
            rev = store.read(token)[1]
            store.command(token, 'req-col-0001', rev, None, 'jr_wd_unlock', {'color': 'do'})
            store.command(token, 'req-col-0001', rev, None, 'jr_wd_unlock', {'color': 'do'})
            s2 = store.read(token)[0]
            self.assertEqual((s2['journey']['wallet'], s2['colors']['have']), (60, ['do']))
            store.close_pool()

    def test_locked_colour_or_item_cannot_be_used(self):
        s = self.with_hat()
        with self.assertRaises(GameError):
            act(s, 'jr_wd_color', item='mu_len', color='do')                 # not unlocked, no buy
        with self.assertRaises(GameError):
            act(s, 'jr_wd_wear', look={'tint': {'ao_quen': 'do'}})
        s, _ = act(s, 'jr_wd_unlock', color='do')
        s, _ = act(s, 'jr_wd_wear', look={'tint': {'ao_quen': 'do'}})       # the top worn: free now
        # An item not bought yet: its colour waits (try it on first, buy it, then the colour).
        with self.assertRaises(GameError):
            act(s, 'jr_wd_color', item='ao_hoodie', color='do')
        with self.assertRaises(GameError):                                   # locked by level
            act(s, 'jr_wd_color', item='kinh_ram', color='do')
        with self.assertRaises(GameError):                                   # married only
            act(s, 'jr_wd_color', item='ao_cuoi', color='do')
        # The colour of something not worn may still be set (it is remembered), when the item is yours.
        s, _ = act(s, 'jr_wd_color', item='ao_thun_kem', color='do', wear=False)
        self.assertEqual(s['colors']['wear']['ao_thun_kem'], 'do')
        self.assertEqual(s['wardrobe']['look']['top'], 'ao_quen')

    def test_wallet_never_goes_below_zero(self):
        s = self.with_hat(80)                                  # 30 xu left
        before = copy.deepcopy(s)
        for name, p in (('jr_wd_unlock', {'color': 'hong'}), ('jr_wd_color', {'item': 'mu_len', 'color': 'hong', 'buy': True})):
            with self.assertRaises(GameError) as e:
                act(s, name, **p)
            self.assertIn('Ví chưa đủ 40 xu', str(e.exception))
        self.assertEqual(s, before)
        self.assertEqual(s['journey']['wallet'], 30)

    def test_bad_payloads(self):
        s = self.with_hat()
        for p in ({'item': 'pk_khong', 'color': 'hong'}, {'item': 'toc_dai', 'color': 'hong'}, {'item': 'mau_hong', 'color': 'hong'},
                  {'item': 'mu_len', 'color': 'cau_vong'}, {'item': 'mu_len', 'color': 5}, {'item': 'mu_len'},
                  {'item': 'mu_len', 'color': 'hong', 'buy': 'yes'}, {'item': 'mu_len', 'color': 'hong', 'buy': True, 'extra': 1},
                  {'item': 'mu_len', 'color': 'hong', 'wear': 1}, {'item': 'mu_len', 'color': 'hong', 'buy': True, 'pay': 'gold'}):
            with self.assertRaises(GameError, msg=p):
                act(s, 'jr_wd_color', **p)
        for p in ({}, {'color': 'goc'}, {'color': 'cau_vong'}, {'color': ['hong']}, {'color': 'hong', 'item': 'mu_len'}):
            with self.assertRaises(GameError, msg=p):
                act(s, 'jr_wd_unlock', **p)
        for tint in ({}, {'mu_len': 'cau_vong'}, {'toc_dai': 'hong'}, 'hong', {'mu_len': None}):
            with self.assertRaises(GameError, msg=tint):
                act(s, 'jr_wd_wear', look={'tint': tint})

    def test_strict_validation_of_the_wallet(self):
        s = self.with_hat(400)
        s, _ = act(s, 'jr_wd_unlock', color='hong')
        s, _ = act(s, 'jr_wd_color', item='ao_quen', color='hong')
        validate_state(s)
        bad = [
            lambda p: p.update(extra=1),
            lambda p: p.update(v=2),
            lambda p: p.update(have=['cau_vong']),
            lambda p: p.update(have=['hong', 'hong']),
            lambda p: p.update(have='hong'),
            lambda p: p['wear'].update(ao_len='do'),            # worn but never unlocked
            lambda p: p['wear'].update(mu_len='hong'),          # accessories live in wardrobe_colors
            lambda p: p['wear'].update(toc_dai='hong'),
            lambda p: p.update(wear=['ao_quen']),
            lambda p: p['deco'].update({'d1': 'do'}),           # a colour not unlocked
            lambda p: p['deco'].update({'': 'hong'}),
            lambda p: p['deco'].update({'x' * 13: 'hong'}),
            lambda p: p.update(deco={f'd{i}': 'hong' for i in range(wd.DECO_MAX + 1)}),
        ]
        for i, breaks in enumerate(bad):
            t = copy.deepcopy(s)
            breaks(t['colors'])
            with self.assertRaises(GameError, msg=i):
                validate_state(t)
        # The 1.3.1 block stays as strict as 1.3.1 made it.
        for breaks in (lambda c: c.update(extra=1), lambda c: c['wear'].update(mu_len='do'), lambda c: c.update(owned=['ao_len:hong'])):
            t = copy.deepcopy(s)
            breaks(t['wardrobe_colors'])
            with self.assertRaises(GameError):
                validate_state(t)

    def test_migration_from_a_131_save(self):
        """Colours bought per accessory in 1.3.1 become colours of the wallet; what was worn stays worn."""
        s = self.with_hat()
        s['wardrobe_colors'] = dict(v=1, wear={'mu_len': 'hong'}, owned=['mu_len:hong', 'kinh_tron:vang'])
        validate_state(s)                                     # a valid 1.3.1 save, as it is in production
        before = copy.deepcopy(s)
        m = migrate_state(s)
        self.assertEqual(s, before)                           # the stored save itself is untouched
        self.assertEqual(m['colors'], dict(v=1, have=['vang', 'hong'], wear={}, deco={}))   # palette order
        self.assertEqual(m['wardrobe_colors']['wear'], {'mu_len': 'hong'})
        self.assertEqual(set(m['wardrobe_colors']['owned']), {f'{i}:{c}' for i in wd.TINTABLE for c in ('hong', 'vang')})
        self.assertEqual(m['wardrobe_colors']['owned'][:2], ['mu_len:hong', 'kinh_tron:vang'])   # nothing removed
        self.assertEqual(wd.look_of(m)['tint'], {'mu_len': 'hong'})
        for k in set(s) - {'colors', 'wardrobe_colors', 'check'}:   # nothing else of the player changes
            self.assertEqual(m[k], s[k], k)
        validate_state(m)
        m, _ = act(m, 'jr_wd_color', item='ao_quen', color='vang')   # gold on the top: free
        self.assertEqual(m['journey']['wallet'], s['journey']['wallet'])
        self.assertEqual(migrate_state(m)['colors'], m['colors'])    # idempotent

    def test_old_saves_and_newer_blocks(self):
        s = story()                                           # a 1.2 save: no colour key at all
        m = migrate_state(s)
        validate_state(m)
        self.assertNotIn('tint', wd.look_of(m))
        self.assertNotIn('wardrobe_colors', m)
        self.assertNotIn('colors', m)
        s['wardrobe_colors'] = dict(v=2, wear={'mu_len': 'cau_vong', 'kinh_tron': 'hong', 'no_toc': 'do'},
                                    owned=['mu_len:cau_vong', 'kinh_tron:hong', 'kinh_tron:hong', 'x'], glitter=True)
        s['colors'] = dict(v=3, have=['navy', 'cau_vong', 5, 'navy'], wear={'ao_len': 'navy', 'ao_moi_2030': 'navy', 'quan_jean': 'do'},
                           deco={'d1': 'navy', 'd2': 'cau_vong', 7: 'navy'}, stickers=['x'])
        m = migrate_state(s)
        self.assertEqual(m['wardrobe_colors']['wear'], {'kinh_tron': 'hong'})
        self.assertEqual(m['colors']['have'], ['hong', 'navy'])
        self.assertEqual(m['colors']['wear'], {'ao_len': 'navy'})
        self.assertEqual(m['colors']['deco'], {})            # no furniture of that id in this save
        validate_state(m)

    def test_rollback_shape(self):
        # The look block keeps its 1.2 shape; the 1.3.1 block keeps its 1.3.1 shape and holds every unlocked colour for
        # every accessory; clothes and furniture live in a root key older builds never read (validate_state lists none).
        s = self.with_hat(400)
        s, _ = act(s, 'jr_wd_unlock', color='navy')
        s, _ = act(s, 'jr_wd_color', item='mu_len', color='navy')
        s, _ = act(s, 'jr_wd_color', item='ao_quen', color='navy')
        self.assertEqual(set(s['wardrobe']), wd.BLOCK_KEYS)
        self.assertEqual(set(s['wardrobe']['look']), wd.LOOK_KEYS)
        self.assertEqual(set(s['wardrobe_colors']), {'v', 'wear', 'owned'})
        self.assertTrue(all(x in wd.PAIRS for x in s['wardrobe_colors']['owned']))
        self.assertTrue(all(f'{k}:{v}' in s['wardrobe_colors']['owned'] for k, v in s['wardrobe_colors']['wear'].items()))
        self.assertTrue({f'{i}:navy' for i in wd.TINTABLE} <= set(s['wardrobe_colors']['owned']))
        wd._validate_look(s)
        wd.validate_colors(s)
        # What a 1.3.1 build would do with this save: drop nothing, ignore s['colors'].
        old = copy.deepcopy(s)
        old.pop('colors')
        validate_state(old)

    def test_public_state_and_content(self):
        s = self.with_hat(400)
        s, _ = act(s, 'jr_wd_unlock', color='lavender')
        s, _ = act(s, 'jr_wd_color', item='quan_kem', color='lavender')
        v = public_state(s)
        self.assertEqual(v['colors'], s['colors'])
        self.assertEqual(v['wardrobe_colors'], s['wardrobe_colors'])
        self.assertLess(len(json.dumps(v['colors'])), 200)
        c = public_content()['journey']['wardrobe']
        self.assertEqual([x['id'] for x in c['colors']], [x['id'] for x in wd.COLORS])
        self.assertEqual(c['tintable'], list(wd.TINTABLE))
        self.assertEqual(c['clothes'], [x['id'] for x in wd.ITEMS if x['slot'] in ('top', 'bottom', 'shoes')])
        self.assertEqual(sorted({x['price'] for x in c['colors']}), [40, 60])
        self.assertEqual([x['id'] for x in c['colors'] if x['price'] == 60], ['vang', 'bac'])
        self.assertTrue(all(x['plain'] for x in c['items']))
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
        self.assertIn("TINT_SLOTS=['top','bottom','shoes','acc']", LOOK_JS)
        self.assertEqual(wd.TINT_SLOTS, ('top', 'bottom', 'shoes', 'acc'))


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
