"""🪴 Đồ nhà kiểu Việt (after 1.4.19): 35 more pieces for every room (sập gỗ, tranh Đông Hồ, màn tuyn, chạn bát, chum
sành, mai đào ngày Tết…), five theme sets, the new 'Trung thu & Tết' shelf of the shop, their drawings, their English,
and the rolling release: a 1.4.19 server that does not know them must accept a save that owns and places them, show
the rest of the room, and lose nothing (the pieces wait in reno.items and come back to the bag here)."""
import contextlib
import copy
import json
import re
import unittest
from pathlib import Path

from game import deco as dc
from game import deco_content as DC
from game import estates_content as EC
from game import journey as jr
from game.engine import migrate_state, public_state, validate_state
from tests.test_bank import act, story
from tests.test_deco import D, bag, fp, owner
from tests.test_home_rooms import put_new

ROOT = Path(__file__).resolve().parents[1]
NEW = tuple(DC.ITEMS)[len(DC.KNOWN_1419):len(DC.KNOWN_1715)]
LATER = tuple(DC.ITEMS)[len(DC.KNOWN_1715):]          # after 1.7.15 (tests/test_deco_more.py)
LATER_SETS = ('choi', 'bep_nha', 'sao') + tuple(EC.SETS)   # + 🏰 the villa sets (game/estates_content.py)
NEW_SETS = ('tet', 'xua', 'hien', 'bep_moi', 'mo')


@contextlib.contextmanager
def older_build():
    """The catalogue as 1.4.19 has it: without the pieces, sets and shop shelf added since (restored in order)."""
    items = {k: DC.ITEMS.pop(k) for k in NEW + LATER}
    sets = {k: DC.SETS.pop(k) for k in NEW_SETS + LATER_SETS}
    resort = DC.SETS['resort']
    DC.SETS['resort'] = dict(resort, need=(('ghe_tam_nang',), ('du_che',), ('phao', 'vit_cao_su')))
    cats = DC.CATS
    DC.CATS = tuple(c for c in cats if c[0] not in ('le', 'bep'))
    try:
        yield
    finally:
        DC.ITEMS.update(items)
        DC.SETS.update(sets)
        DC.SETS['resort'] = resort
        DC.CATS = cats


class Catalogue(unittest.TestCase):
    def test_the_new_pieces(self):
        self.assertEqual(len(NEW), 35)
        self.assertEqual(DC.KNOWN_1419[-1], 'den_vuon')                       # the last piece 1.4.19 knows
        self.assertEqual(list(DC.KNOWN_132), list(DC.ITEMS)[:65])
        cats = {c[0] for c in DC.CATS}
        self.assertIn('le', cats)
        for k in NEW:
            it = DC.ITEMS[k]
            with self.subTest(k=k):
                self.assertTrue(10 <= it['price'] <= 320 and 1 <= it['cozy'] <= 3, k)   # the shop's usual range
                self.assertIn(it['cat'], cats)
                if it['spot'] == 'wall':
                    self.assertTrue(set(it['rooms']) - set(DC.OUT))
                    rows = {'loft': 1}
                    self.assertTrue(all(it['h'] <= rows.get(t, 2) for t in it['rooms']), k)   # fits every wall it is sold for
        self.assertEqual(len({DC.ITEMS[k]['name'] for k in DC.ITEMS}), len(DC.ITEMS))  # no two pieces share a name
        by_room = {t: [k for k in NEW if t in DC.ITEMS[k]['rooms']] for t in ('living', 'bed', 'kitchen', 'bath', 'balcony', 'yard', 'pool')}
        for t, ks in by_room.items():
            self.assertGreaterEqual(len(ks), 3, t)                               # something new for every kind of room
        self.assertEqual([x['id'] for x in jr.content()['deco']['items']][81:116], list(NEW))

    def test_every_piece_is_drawn_and_named_in_english(self):
        js = (ROOT / 'public' / 'js' / 'v4' / 'deco-art.js').read_text(encoding='utf-8')
        art = js[js.index('export const ART={'):js.index('/* ---------------------------------------------------------------- the room')]
        drawn = set(re.findall(r'^\s+([a-z_0-9]+):\{h:', art, re.M))
        self.assertEqual(drawn, set(DC.ITEMS))
        en = json.loads((ROOT / 'i18n' / 'overrides.json').read_text(encoding='utf-8'))['strings']
        for k in NEW:
            self.assertIn(DC.ITEMS[k]['name'], en, k)
        for sid in NEW_SETS:
            self.assertIn(DC.SETS[sid]['name'], en, sid)
        self.assertIn('Trung thu & Tết', en)


class Sets(unittest.TestCase):
    def test_a_home_set_up_the_vietnamese_way(self):
        s = owner('biet_thu_vuon', wallet=90000)
        s, sap = put_new(s, 'sap_go', 'living', 20, 40)
        s, _ = put_new(s, 'am_chen', 'living', 10, 0, on=sap)
        s, _ = put_new(s, 'tranh_dong_ho', 'living', 70, 4)
        self.assertIn('xua', [x['id'] for x in D(s)['sets'] if x['done']])
        s, _ = put_new(s, 'bonsai', 'yard', 0, 0)
        s, _ = put_new(s, 'long_chim', 'yard', 30, 0)
        s, r = act(s, 'jr_deco_buy', item='ban_co_tuong', confirm=True, put=dict(r='yard', x=60, y=20))
        self.assertIn('Hiên nhà thong thả', r['message'])
        for k, q in (('lo_vi_song', dict(x=10, y=0, on='#counter')), ('am_sieu_toc', dict(x=40, y=0, on='#counter')),
                     ('chan_bat', dict(x=100, y=20))):
            s, _ = put_new(s, k, 'kitchen', q['x'], q['y'], on=q.get('on'))
        s, td = put_new(s, 'ban_trang_diem', 'bed', 20, 0)
        s, _ = put_new(s, 'den_sao', 'bed', 10, 0, on=td)
        s, _ = put_new(s, 'gau_bong_lon', 'bed', 0, 50)
        s, _ = put_new(s, 'phao_hong_hac', 'pool', 60, 25)                       # on the water: a float may go there
        s, _ = put_new(s, 'ghe_tam_nang', 'pool', 0, 60)
        s, _ = put_new(s, 'du_che', 'pool', 140, 60)
        done = {x['id'] for x in D(s)['sets'] if x['done']}
        self.assertTrue({'xua', 'hien', 'bep_moi', 'mo', 'resort'} <= done)
        self.assertEqual(fp(s, sap)[:3], ('living', 20, 40))
        validate_state(migrate_state(copy.deepcopy(s)))

    def test_tet_in_the_attic(self):
        s = story(wallet=3000)
        sets = {x['id'] for x in D(s)['sets']}
        self.assertEqual(sets & set(NEW_SETS), {'tet'})                         # the attic's state carries one more set only
        s, _ = put_new(s, 'cay_mai', 'attic', 0, 40)
        s, _ = put_new(s, 'cau_doi', 'attic', 30, 0)                            # between the roof's slope and the window
        s, r = act(s, 'jr_deco_buy', item='mam_ngu_qua', confirm=True, put=dict(r='attic', x=40, y=40))
        self.assertIn('Góc Tết sum vầy', r['message'])
        validate_state(s)

    def test_where_they_may_not_go(self):
        from game.engine import GameError
        s = owner('tap_the')
        for k, room in (('sap_go', 'bed'), ('tu_lanh_magnet', 'living'), ('phao_hong_hac', 'living'), ('ao_choang', 'living')):
            with self.subTest(k=k), self.assertRaises(GameError):
                act(s, 'jr_deco_buy', item=k, confirm=True, put=dict(r=room, x=0, y=20))
        with self.assertRaises(GameError):                                       # the couplets keep off the window
            act(s, 'jr_deco_buy', item='cau_doi', confirm=True, put=dict(r='living', x=20, y=0))


class RollingRelease(unittest.TestCase):
    def setUp(self):
        s = owner('biet_thu_vuon', wallet=90000)
        s, self.sofa = put_new(s, 'sofa', 'living', 100, 40)
        s, self.sap = put_new(s, 'sap_go', 'living', 0, 40)
        s, self.lamp = put_new(s, 'den_ban', 'living', 10, 0, on=self.sap)     # an old piece on a new one
        s, self.candle = put_new(s, 'nen_thom', 'bath', 0, 0, on='#toilet')     # a new piece in a new room
        s, self.mai = put_new(s, 'cay_mai', 'yard', 0, 0)
        self.s = s

    def test_an_older_server_accepts_and_shows_the_rest(self):
        with older_build():
            old = migrate_state(copy.deepcopy(self.s))
            validate_state(old)
            v = public_state(old)['journey']['deco']
            self.assertEqual({i['id'] for i in v['items']}, {self.sofa})         # the pieces it cannot draw are left out
            self.assertNotIn('sap_go', [b['k'] for b in v['bag']])
            self.assertIn('den_ban', [b['k'] for b in v['bag']])                 # the lamp it knows waits in its bag
            old, _ = act(old, 'jr_deco_buy', item='loa', confirm=True)            # and it can go on playing
            validate_state(old)
        self.assertEqual({it['k'] for it in old['journey']['reno']['items']} >= {'sap_go', 'nen_thom', 'cay_mai', 'loa'}, True)
        back = migrate_state(old)
        validate_state(back)
        self.assertEqual(fp(back, self.sofa)[:3], ('living', 100, 40))
        self.assertTrue({'sap_go', 'nen_thom', 'cay_mai', 'den_ban', 'loa'} <= set(bag(back)))   # nothing lost: in the bag

    def test_only_looking_on_an_older_server_changes_nothing(self):
        with older_build():
            old = migrate_state(copy.deepcopy(self.s))
            validate_state(old)
            public_state(old)
        back = migrate_state(old)
        self.assertEqual(fp(back, self.sap)[:3], ('living', 0, 40))
        self.assertEqual(fp(back, self.lamp)[4], self.sap)
        self.assertEqual(fp(back, self.candle)[4], '#toilet')
        self.assertEqual(fp(back, self.mai)[:3], ('yard', 0, 0))

    def test_the_grid_mirror_holds_only_what_132_knows(self):
        g = self.s['journey']['deco']['pos']
        kinds = {it['id']: it['k'] for it in self.s['journey']['reno']['items']}
        self.assertTrue(all(kinds[u] in DC.KNOWN_132 for u in g))


if __name__ == '__main__':
    unittest.main()
