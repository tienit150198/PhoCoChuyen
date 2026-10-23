"""🛋️ Thêm đồ trang trí (owner 21/10/2026: "thêm đồ trang trí cho nhà"): 55 evergreen pieces for every room and style
(nét Việt xưa, tối giản, pastel, gaming, đọc sách, bếp, nhà tắm, ban công), eight theme sets with bonuses within the
old cap, the shop's style filter, and the rolling release: every piece is bought, placed, seen by a visitor, survives
a save round trip, and a build that does not know them (2.4.71) still accepts the save and loses nothing."""
import contextlib
import copy
import json
import re
import unittest
from pathlib import Path

from game import deco as dc
from game import deco_content as DC
from game import deco_mate as dm
from game import estates_content as EC
from game import reno as rn
from game.engine import migrate_state, validate_state
from tests.test_bank import act
from tests.test_deco import D, bag, owner
from tests.test_estate_moves import in_villa

ROOT = Path(__file__).resolve().parents[1]
NEW = DC.NEW_2026
NEW_SETS = DC.NEW_SETS_2026


@contextlib.contextmanager
def build_2471():
    """What the live 2.4.71 server knows: its catalogue and its sets (no new pieces, no new sets)."""
    items = {k: DC.ITEMS.pop(k) for k in NEW}
    sets = {k: DC.SETS.pop(k) for k in NEW_SETS}
    dc._SETS_MEMO.clear()
    try:
        yield
    finally:
        DC.ITEMS.update(items)
        DC.SETS.update(sets)
        dc._SETS_MEMO.clear()


def spot(s, k, prefer=()):
    """A free spot {r, x, y} for kind `k` where the player lives (the rooms in `prefer` first), by the server's rules."""
    L = dc.layout(s)
    rooms = sorted(L['rooms'], key=lambda r: (r['id'] not in prefer, prefer.index(r['id']) if r['id'] in prefer else 0))
    for room in rooms:
        z = dc.zone(room, k) if room['type'] in DC.ITEMS[k]['rooms'] else None
        if not z:
            continue
        for y in range(0, z[1] + 1, 10):
            for x in range(0, z[0] + 1, 10):
                q = dict(r=room['id'], x=x, y=y, f=0)
                if not dc.check(room, k, q, L['pos'], L['kinds']):
                    return dict(r=room['id'], x=x, y=y)
    return None


def buy_put(s, k, prefer=(), on=None):
    q = spot(s, k, prefer)
    assert q, k
    if on:
        q = dict(r=q['r'], x=0, y=0, on=on)
    s, r = act(s, 'jr_deco_buy', item=k, confirm=True, put=q)
    return s, r


class Catalogue(unittest.TestCase):
    def test_the_new_pieces(self):
        self.assertTrue(40 <= len(NEW) <= 70)
        self.assertEqual(tuple(DC.ITEMS)[-len(NEW):], NEW)                 # appended last: the KNOWN_* lists keep their meaning
        self.assertEqual(DC.KNOWN_2471, tuple(DC.ITEMS)[:-len(NEW)])
        self.assertEqual(len({it['name'] for it in DC.ITEMS.values()}), len(DC.ITEMS))
        cats = {c[0] for c in DC.CATS}
        for k in NEW:
            it = DC.ITEMS[k]
            with self.subTest(k=k):
                self.assertTrue(it.get('new') and not it.get('uq'))
                self.assertIn(it['cat'], cats)
                self.assertTrue(20 <= it['price'] <= 1200 and 1 <= it['cozy'] <= 3)
                self.assertTrue(set(it['rooms']) <= set(DC.TYPES))
                if it['spot'] == 'top':
                    self.assertEqual((it['w'], it['h']), (1, 1))
                if it['spot'] == 'wall':
                    self.assertTrue(all(it['h'] <= {'loft': 1}.get(t, 2) for t in it['rooms']))   # fits every wall it is sold for
                    self.assertFalse(set(it['rooms']) <= set(DC.OUT))
                base = {t for t, (_e, _n, b) in EC.ROOM_TYPES.items() if set(b) & set(it['rooms'])}
                self.assertTrue(base <= set(it['rooms']))                  # 🏰 villa rooms take them by BASE
        for t in ('living', 'bed', 'kitchen', 'bath', 'balcony', 'yard', 'studio'):
            self.assertGreaterEqual(sum(1 for k in NEW if t in DC.ITEMS[k]['rooms']), 4, t)
        prices = sorted(DC.ITEMS[k]['price'] for k in NEW)
        self.assertGreaterEqual(sum(1 for p in prices if p <= 60), 15)    # many cheap small things
        self.assertGreaterEqual(sum(1 for p in prices if p >= 400), 4)    # a few big pieces for the rich
        for name in ('Sập gụ chân quỳ', 'Tủ chè khảm trai', 'Đèn lồng Hội An', 'Tranh Đông Hồ đàn gà'):
            self.assertIn(name, {DC.ITEMS[k]['name'] for k in NEW})

    def test_the_shop_sends_them_with_styles(self):
        c = dc.catalogue()
        by = {x['id']: x for x in c['items']}
        self.assertTrue(all(by[k].get('new') for k in NEW))
        self.assertFalse(any(x.get('new') for k, x in by.items() if k not in NEW))
        self.assertTrue(4 <= len(c['styles']) <= 8)
        for st in c['styles']:
            with self.subTest(style=st['id']):
                self.assertTrue(st['items'] and set(st['items']) <= set(DC.ITEMS))
                self.assertFalse(any(DC.ITEMS[k].get('uq') for k in st['items']))
                self.assertTrue(set(st['items']) & set(NEW))
        self.assertTrue(set(NEW) - {'thang_khan', 'chau_ngam_chan', 'ke_tre_tam', 'den_muoi', 'ban_an_tron', 'tu_bep_treo',
                                     'may_rua_bat', 'gio_banh_mi', 'den_hoi_an'} <= {k for st in c['styles'] for k in st['items']} | set(NEW))

    def test_drawn_and_named_in_english(self):
        js = (ROOT / 'public/js/v4/deco-art.js').read_text(encoding='utf-8')
        art = js[js.index('export const ART={'):js.index('/* ---------------------------------------------------------------- the room')]
        drawn = set(re.findall(r'^\s+([a-z_0-9]+):\{h:', art, re.M))
        tint = js[js.index('export const TINT={'):js.index('const MAPS=')]
        for k in NEW:
            with self.subTest(k=k):
                self.assertIn(k, drawn)
                self.assertRegex(tint, rf'[{{,\s]{k}:')                   # every piece takes a palette colour
                flag = {'wall': 'wall:1', 'rug': 'rug:1', 'top': 'top:1'}.get(DC.ITEMS[k]['spot'])
                entry = art[art.index(f'  {k}:{{h:'):][:120]
                if flag:
                    self.assertIn(flag, entry)
        en = json.loads((ROOT / 'i18n/overrides.json').read_text(encoding='utf-8'))['strings']
        for k in NEW:
            self.assertIn(DC.ITEMS[k]['name'], en, k)
        for sid in NEW_SETS:
            self.assertIn(DC.SETS[sid]['name'], en, sid)
        for _i, _e, name, _ks in DC.STYLES:
            self.assertIn(name, en, name)


class Sets(unittest.TestCase):
    def test_bonuses_stay_within_the_old_cap(self):
        self.assertTrue(4 <= len(NEW_SETS) <= 8)
        self.assertEqual(DC.SET_BONUS_MAX, 3)
        for sid, S in DC.SETS.items():
            with self.subTest(sid=sid):
                self.assertTrue(2 <= S['bonus'] <= DC.SET_BONUS_MAX)
        for sid in NEW_SETS:
            for entry in DC.SETS[sid]['need']:
                self.assertTrue(entry[0] == 'tag' or set(entry) <= set(DC.ITEMS), (sid, entry))
            self.assertTrue(any(set(e) & set(NEW) for e in DC.SETS[sid]['need'] if e[0] != 'tag'), sid)   # new pieces make it

    def test_every_new_set_can_be_finished_and_counts_once(self):
        plans = {
            'nha_xua': ('living', ('sap_gu', 'tu_che', 'binh_phong')),
            'hoi_an': ('living', ('den_hoi_an', 'am_tich', 'non_la')),
            'toi_gian': ('living', ('sofa_goc', 'den_san_cong', 'tranh_truu_tuong')),
            'pastel': ('bed', ('giuong_may', 'den_may', 'tham_may')),
            'stream': ('bed2', ('man_hinh_cong', 'ban_phim_led', 'den_thanh_rgb')),
            'doc_sach': ('bed2', ('ghe_doc_sach', 'den_doc_sach', 'tu_sach_cao')),
            'ban_cong': ('yard', ('ban_ghe_ban_cong', 'chau_lan', 'den_nang_luong')),
            'bep_viet': ('kitchen', ('ban_an_tron', 'noi_dat', 'tu_bep_treo')),
        }
        self.assertEqual(set(plans), set(NEW_SETS))
        s = owner('biet_thu_vuon', wallet=90000)
        before = D(s)['cozy']['sets']
        for sid, (room, kinds) in plans.items():
            with self.subTest(sid=sid):
                for i, k in enumerate(kinds):
                    s, r = buy_put(s, k, (room,))
                done = {x['id'] for x in D(s)['sets'] if x['done']}
                self.assertIn(sid, done)
                self.assertIn(DC.SETS[sid]['name'], r['message'])           # 🎉 the last piece says so
        cozy = D(s)['cozy']
        done = {x['id'] for x in D(s)['sets'] if x['done']}
        self.assertTrue(set(NEW_SETS) <= done)
        self.assertEqual(cozy['sets'], sum(DC.SETS[x]['bonus'] for x in done))   # each done set once, at its bonus
        self.assertEqual(before, 0)
        s2, _ = buy_put(s, 'non_la', ('living',))                            # a second hat: the set still counts once
        self.assertEqual(D(s2)['cozy']['sets'], cozy['sets'])
        validate_state(s)


class Place(unittest.TestCase):
    def test_every_piece_is_bought_placed_seen_and_survives_a_round_trip(self):
        homes = {}
        for k in NEW:
            it = DC.ITEMS[k]
            kind = ('biet_thu_vuon' if set(it['rooms']) & {'living', 'bed', 'bed2', 'kitchen', 'yard'} else
                    'nha_pho' if set(it['rooms']) - set(EC.TYPES) else 'dinh_thu_dao')   # 🏋️📚 the villa gym and study ones
            homes.setdefault(kind, []).append(k)
        seen = set()
        for kind, ks in homes.items():
            s, placed = (in_villa(kind) if kind in {e['id'] for e in EC.ESTATES} else owner(kind, wallet=90000)), {}
            for k in ks:
                with self.subTest(k=k):
                    s, r = buy_put(s, k)
                    placed[r['uid']] = k
            s = migrate_state(json.loads(json.dumps(s)))                      # the save, written and read back
            validate_state(s)
            L = dc.layout(s)
            mine = {u: kk for u, kk in placed.items() if u in L['kinds']}
            self.assertEqual(set(mine), {u for u in L['pos'] if u in mine}, kind)   # every one still placed
            pub = dc.public(s)                                                 # what the owner and a visitor are sent
            shown = {i['id']: i['k'] for i in pub['items']}
            for u, kk in mine.items():
                self.assertEqual(shown.get(u), kk)
            rooms = {r['id'] for r in L['rooms']}
            self.assertTrue(set(mine.values()) <= {p['k'] for p in dm.pieces(s, rooms)})   # 💞 a housemate's view too
            seen |= set(mine.values())
        self.assertEqual(seen, set(NEW))

    def test_small_things_stand_on_the_new_surfaces(self):
        s = owner('biet_thu_vuon', wallet=90000)
        s, r = buy_put(s, 'tu_che', ('living',))
        cab = r['uid']
        s, r = act(s, 'jr_deco_buy', item='am_tich', confirm=True, put=dict(r='living', x=0, y=0, on=cab))
        self.assertEqual(dc.layout(s)['pos'][r['uid']]['on'], cab)
        s, r2 = buy_put(s, 'ke_cau_vong', ('bed',))
        s, r = act(s, 'jr_deco_buy', item='chau_sen_da', confirm=True, put=dict(r='bed', x=0, y=0, on=r2['uid']))
        self.assertEqual(dc.layout(s)['pos'][r['uid']]['on'], r2['uid'])
        validate_state(s)

    def test_sold_back_at_half(self):
        s = owner('nha_pho', wallet=90000)
        w = s['journey']['wallet']
        s, r = buy_put(s, 'sofa_goc', ('living',))
        s, _ = act(s, 'jr_deco_sell', uid=r['uid'], confirm=True, n='sell-sofa-goc')
        self.assertEqual(s['journey']['wallet'], w - DC.ITEMS['sofa_goc']['price'] + DC.ITEMS['sofa_goc']['price'] // 2)


class Rollback(unittest.TestCase):
    def test_a_2471_server_accepts_the_save_and_loses_nothing(self):
        s = owner('biet_thu_vuon', wallet=90000)
        for k in ('sofa_goc', 'tu_che', 'den_hoi_an', 'chieu_hoa', 'giuong_may', 'am_tich'):
            s, _ = buy_put(s, k, ('living', 'bed'))
        s, old_piece = buy_put(s, 'sofa', ('living',))
        saved = json.loads(json.dumps(s))
        with build_2471():
            t = copy.deepcopy(saved)
            validate_state(t)                                                  # accepted as it is
            L = dc.layout(t)
            self.assertIn(old_piece['uid'], L['pos'])                          # the old pieces stand
            self.assertFalse(set(L['kinds'][u] for u in L['pos']) & set(NEW))  # the new ones wait, unshown
            self.assertEqual(len(rn.get(t)['items']), 7)                       # nothing lost
            t, _ = act(t, 'jr_deco_pick', uid=old_piece['uid'])                # the old build changes the room
            validate_state(t)
        back = migrate_state(json.loads(json.dumps(saved)))                    # read back by this build untouched: all placed
        validate_state(back)
        self.assertEqual(len(dc.layout(back)['pos']), 7)
        t = migrate_state(json.loads(json.dumps(t)))                           # after the old build wrote: in the bag, owned
        validate_state(t)
        self.assertEqual(sorted(bag(t)), sorted(['sofa', 'sofa_goc', 'tu_che', 'den_hoi_an', 'chieu_hoa', 'giuong_may', 'am_tich']))
        s2, r = buy_put(t, 'non_la', ('living',))                              # and set out again as usual
        uid = next(b['id'] for b in D(t)['bag'] if b['k'] == 'tu_che')
        q = spot(t, 'tu_che', ('living',))
        t, _ = act(t, 'jr_deco_put', uid=uid, **q)
        self.assertIn(uid, dc.layout(t)['pos'])
        validate_state(t)


if __name__ == '__main__':
    unittest.main()
