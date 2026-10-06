"""🪴 Bày trí phòng (game/deco.py, game/deco_content.py): the catalogue, where a piece may stand (bounds, overlap,
wall vs floor, fixtures, small things on tables), the bag (pick up, pick up all, sell back), undo, moving house,
rented rooms (decor yes, repairs no), the dorm's bunk corner, Ấm cúng with its sets and caps, the neighbour's
visit, 1.2.0 saves migrating, and the save checks."""
import copy
import unittest

from game import deco as dc
from game import deco_content as DC
from game import housing as hs
from game import journey as jr
from game import reno as rn
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import act, story
from tests.test_housing import buy

V1_RENO_KEYS = {'v', 'hid', 'day', 'seq', 'parts', 'items', 'spent', 'stats'}


def D(s):
    return public_state(s)['journey']['deco']


def at(s, uid):
    return next(((i['r'], i['x'], i['y'], i['f']) for i in D(s)['items'] if i['id'] == uid), None)


def bag(s):
    return [b['k'] for b in D(s)['bag']]


def fp(s, uid):
    """A placed piece's free spot (room, x, y, f, on) in units (U per cell), or None."""
    return next(((i['r'], i['fx'], i['fy'], i['f'], i['on']) for i in D(s)['items'] if i['id'] == uid), None)


def into_bag(s, k):
    s, r = act(s, 'jr_deco_buy', item=k, confirm=True)
    return s, r['uid']


def free(s, k, room):
    """The first spot of `room` where a piece of kind `k` fits today (x, y), or None."""
    L = dc.layout(s)
    rm = next(r for r in L['rooms'] if r['id'] == room)
    occ = dc._occupancy(L['rooms'], L['kinds'], L['pos'])
    it = DC.ITEMS[k]
    rows = rm['wrows'] if it['spot'] == 'wall' else rm['frows']
    return next(((x, y) for y in range(rows) for x in range(rm['cols']) if not dc.fit(rm, k, x, y, occ)), None)


def place_new(s, k, room, x=None, y=None, f=0):
    if x is None:
        x, y = free(s, k, room)
    return act(s, 'jr_deco_buy', item=k, confirm=True, room=room, x=x, y=y, f=f)


def tick(s, n=1):
    """Close `n` life days like end_day (bank, home, the inside of the home, the decor)."""
    from game import bank as bk
    notes = []
    for _ in range(n):
        s['journey']['life_day'] += 1
        notes += bk.on_life_day(s) + hs.on_life_day(s) + rn.on_life_day(s) + dc.on_life_day(s)
    validate_state(s)
    return notes


def owner(kind='tap_the', wallet=6000):
    s = story(wallet=wallet)
    s, _ = buy(s, kind)
    s['journey']['wallet'] = max(s['journey']['wallet'], wallet)
    return s


def renter(kind='tro_moi', wallet=6000):
    s = story(wallet=wallet)
    s, _ = act(s, 'jr_home_rent', kind=kind, confirm=True)
    return s


class Catalogue(unittest.TestCase):
    def test_items(self):
        self.assertEqual(len(DC.ITEMS), 171)
        self.assertEqual(DC.KNOWN_1715[-1], 'mam_ngu_qua')                  # the last piece 1.7.15 knows
        self.assertEqual(DC.KNOWN_132, tuple(DC.ITEMS)[:65])                # what a 1.3.2 build knows: its mirror holds only these
        self.assertNotIn('ke_go_treo', DC.KNOWN_132)
        self.assertEqual((DC.ITEMS['ke_go_treo']['spot'], DC.ITEMS['ke_go_treo']['ledge']), ('wall', 24))
        old = {'sofa': (180, 3), 'ban_tra': (70, 1), 'giuong': (220, 3), 'tv': (240, 2), 'be_ca': (150, 3), 'ke_sach': (90, 2),
               'ban_lam_viec': (120, 1), 'dan': (110, 2), 'gau_bong': (35, 1), 'cay_canh': (40, 2), 'ghe_may': (70, 1),
               'tu_lanh': (260, 2), 'ban_an': (160, 2), 'noi_com': (45, 1), 'may_giat': (200, 1), 'hoa_giay': (50, 2),
               'ban_ngoai': (160, 2), 'tranh': (70, 2), 'den_long': (35, 1), 'den_nhay': (30, 2), 'dong_ho': (50, 1),
               'guong': (45, 1), 'ke_cay': (55, 2), 'anh': (25, 1), 'lich': (15, 1), 'may_lanh': (320, 2), 'ke_bep': (30, 1)}
        self.assertEqual(set(DC.LEGACY), set(old))                          # every 1.2.0 piece still exists, same price
        for k, (price, cozy) in old.items():
            self.assertEqual((DC.ITEMS[k]['price'], DC.ITEMS[k]['cozy']), (price, cozy), k)
        cats = {c[0] for c in DC.CATS}
        for k, it in DC.ITEMS.items():
            with self.subTest(k=k):
                self.assertRegex(k, r'^[a-z0-9_]{1,24}$')
                self.assertIn(it['spot'], DC.SPOTS)
                self.assertIn(it['cat'], cats)
                self.assertTrue(1 <= it['w'] <= 3 and 1 <= it['h'] <= 2 and it['price'] > 0 and 1 <= it['cozy'] <= 3)
                self.assertTrue(it['rooms'] and set(it['rooms']) <= set(DC.TYPES))
                self.assertTrue(it['surface'] == 0 or it['spot'] == 'floor')
                if it['spot'] == 'top':
                    self.assertEqual((it['w'], it['h']), (1, 1))
                if it['spot'] == 'wall':
                    self.assertFalse(set(it['rooms']) <= set(DC.OUT))
        self.assertEqual({c['id'] for c in dc.catalogue()['cats']}, cats)
        c = jr.content()['deco']
        self.assertEqual([x['id'] for x in c['items']], list(DC.ITEMS))
        self.assertEqual(next(x for x in c['items'] if x['id'] == 'sofa')['sell'], 90)

    def test_every_piece_has_a_place_and_every_place_has_choices(self):
        places = ['attic'] + [f'rent:{k}:1' for k in ('tro_moi', 'ky_tuc_xa')] + [f'own:h1:{k}' for k in rn.HOUSES]
        fits = {k: 0 for k in DC.ITEMS}
        for key in places:
            rooms = dc.rooms_of(key)
            self.assertTrue(rooms, key)
            occ = dc._occupancy(rooms, {}, {})
            here = set()
            for rm in rooms:
                self.assertTrue(rm['cols'] <= dc.XY_MAX + 1 and rm['frows'] >= 2)
                for k, it in DC.ITEMS.items():
                    rows = rm['wrows'] if it['spot'] == 'wall' else rm['frows']
                    if any(not dc.fit(rm, k, x, y, occ) for x in range(rm['cols']) for y in range(rows)):
                        here.add(k)
                        fits[k] += 1
            with self.subTest(place=key):
                self.assertGreaterEqual(len(here), 14)                          # even the bunk corner has choices
        self.assertEqual([k for k, n in fits.items() if not n], [])           # nothing in the shop is unplaceable

    def test_sets_are_reachable(self):
        for sid, S in DC.SETS.items():
            for entry in S['need']:
                if entry[0] == 'tag':
                    self.assertTrue(any(entry[1] in it['tags'] for it in DC.ITEMS.values()), (sid, entry))
                    self.assertIn(entry[1], DC.TAG_WORDS)
                else:
                    self.assertTrue(set(entry) <= set(DC.ITEMS), (sid, entry))


class Placement(unittest.TestCase):
    def test_buy_place_and_double_tap(self):
        s = owner()
        cash = s['journey']['wallet']
        s, r = place_new(s, 'sofa', 'living', 1, 1)
        uid = r['uid']
        self.assertEqual(s['journey']['wallet'], cash - 180)
        self.assertIn('Đặt ở phòng khách', r['message'])
        self.assertEqual(at(s, uid), ('living', 1, 1, 0))
        s, r = act(s, 'jr_deco_buy', item='sofa', confirm=True, room='living', x=1, y=1)
        self.assertTrue(r['duplicate'])
        self.assertEqual(s['journey']['wallet'], cash - 180)                # paid once
        self.assertEqual(D(s)['cozy']['total'], 3)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'home')

    def test_buy_into_the_bag(self):
        s = owner()
        s, r = act(s, 'jr_deco_buy', item='cay_canh', confirm=True)
        self.assertIn('túi đồ', r['message'])
        self.assertEqual((bag(s), D(s)['items']), (['cay_canh'], []))
        with self.assertRaises(GameError):
            act(s, 'jr_deco_buy', item='cay_canh')                         # no confirm
        with self.assertRaises(GameError):
            act(s, 'jr_deco_buy', item='ban_bida', confirm=True)           # not sold

    def test_where_a_piece_may_stand(self):
        s = owner()
        s, r = place_new(s, 'sofa', 'living', 1, 1)
        sofa = r['uid']
        s, r = place_new(s, 'gau_bong', 'living', 0, 2)
        cases = [
            (dict(item='ke_sach', room='living', x=5, y=0), 'vướng cửa ra vào', 'taken'),         # the door's floor cell
            (dict(item='tranh', room='living', x=1, y=0), 'vướng cửa sổ', 'taken'),               # the window
            (dict(item='tranh', room='living', x=4, y=2), 'nằm ngoài', 'bad_spot'),               # two wall rows only
            (dict(item='ke_sach', room='living', x=6, y=2), 'nằm ngoài', 'bad_spot'),             # 2 wide from the last column
            (dict(item='giuong', room='kitchen', x=0, y=1), 'không hợp', 'bad_spot'),             # a bed in the kitchen
            (dict(item='ke_sach', room='balcony', x=0, y=0), 'Chọn phòng', None),                 # the tập thể has no balcony
            (dict(item='ke_sach', room='living', x=True, y=0), 'không đặt', None),
            (dict(item='ke_sach', room='living', x='1', y=0), 'không đặt', None),
            (dict(item='ke_sach', room='living', x=0, y=0, f=2), 'Hướng', None),
        ]
        for p, words, code in cases:
            with self.subTest(p=p), self.assertRaises(GameError) as e:
                act(s, 'jr_deco_buy', confirm=True, **p)
            self.assertIn(words, str(e.exception))
            if code:
                self.assertEqual(e.exception.code, code)
        s2, r = act(s, 'jr_deco_buy', confirm=True, item='tv', room='living', x=2, y=1)   # since 1.4 pieces may overlap…
        self.assertEqual(at(s2, r['uid'])[:3], ('living', 2, 1))
        s2, r = act(s, 'jr_deco_buy', confirm=True, item='den_ban', room='living', x=2, y=1)   # …and a small thing may sit on the floor
        self.assertEqual(fp(s2, r['uid']), ('living', 40, 20, 0, ''))
        cash = s['journey']['wallet']
        s, _ = place_new(s, 'tham', 'living', 1, 1)                          # a rug goes under the sofa
        s, r = place_new(s, 'ban_tra', 'living', 4, 2)
        s, r = place_new(s, 'den_ban', 'living', 4, 2)                       # a lamp on the coffee table
        self.assertIsNotNone(at(s, r['uid']))
        s, _ = place_new(s, 'den_ban', 'kitchen', 0, 0)                      # and on the kitchen counter
        self.assertEqual(s['journey']['wallet'], cash - 90 - 70 - 35 - 35)
        self.assertEqual(at(s, sofa), ('living', 1, 1, 0))
        with self.assertRaises(GameError) as e:                               # someone else's piece
            act(s, 'jr_deco_place', uid='zz', room='living', x=0, y=0)
        self.assertIn('Không tìm thấy', str(e.exception))

    def test_move_flip_and_the_things_on_a_table(self):
        s = owner()
        s, r = place_new(s, 'ban_lam_viec', 'living', 0, 1)
        table = r['uid']
        s, r = place_new(s, 'den_ban', 'living', 1, 1)
        lamp = r['uid']
        s, r = act(s, 'jr_deco_place', uid=table, room='living', x=3, y=2)
        self.assertIn('Đèn bàn đi theo', r['message'])
        self.assertEqual((at(s, table), at(s, lamp)), (('living', 3, 2, 0), ('living', 4, 2, 0)))
        s, r = act(s, 'jr_deco_place', uid=table, room='living', x=3, y=2, f=1)
        self.assertIn('Đã lật', r['message'])
        s, r = act(s, 'jr_deco_place', uid=table, room='living', x=3, y=2, f=1)
        self.assertTrue(r['duplicate'])
        s, r = act(s, 'jr_deco_place', uid=table, room='bed', x=0, y=2)     # to another room: the lamp comes along
        self.assertIn('sang phòng ngủ', r['message'])
        self.assertEqual(at(s, lamp)[0], 'bed')
        s, r = act(s, 'jr_deco_pick', uid=table)
        self.assertIn('Kèm đèn bàn', r['message'])
        self.assertEqual((D(s)['items'], sorted(bag(s))), ([], ['ban_lam_viec', 'den_ban']))

    def test_pick_up_pick_all_and_sell(self):
        s = owner()
        s, r = place_new(s, 'sofa', 'living', 0, 1)
        sofa = r['uid']
        s, r = place_new(s, 'tranh', 'living', 3, 0)
        s, r = act(s, 'jr_deco_pick', uid=sofa)
        self.assertEqual((bag(s), D(s)['cozy']['items']), (['sofa'], 2))   # in the bag: no Ấm cúng
        with self.assertRaises(GameError) as e:
            act(s, 'jr_deco_pick', uid=sofa)
        self.assertEqual(e.exception.code, 'nothing')
        s, r = act(s, 'jr_deco_place', uid=sofa, room='living', x=0, y=2)   # back out of the bag
        self.assertIn('Đã đặt', r['message'])
        s, r = act(s, 'jr_deco_pick', uid='all')
        self.assertIn('2 món', r['message'])
        self.assertEqual((D(s)['items'], len(bag(s))), ([], 2))
        cash = s['journey']['wallet']
        s, r = act(s, 'jr_deco_sell', uid=sofa, confirm=True)
        self.assertEqual(s['journey']['wallet'], cash + 90)                 # half of 180
        self.assertNotIn(sofa, [it['id'] for it in s['journey']['reno']['items']])
        with self.assertRaises(GameError):
            act(s, 'jr_deco_sell', uid=sofa, confirm=True)
        with self.assertRaises(GameError):
            act(s, 'jr_deco_pick', uid='all')

    def test_undo(self):
        s = owner()
        s, r = place_new(s, 'sofa', 'living', 0, 1)
        sofa = r['uid']
        s, _ = act(s, 'jr_deco_place', uid=sofa, room='living', x=2, y=2)
        s, r = act(s, 'jr_deco_layout', set={sofa: ['living', 0, 1, 0]})
        self.assertEqual(at(s, sofa), ('living', 0, 1, 0))
        s, r = place_new(s, 'ban_tra', 'living', 3, 2)
        table = r['uid']
        s, r = act(s, 'jr_deco_buy', item='den_ban', confirm=True, put=dict(r='living', x=10, y=0, on=table))
        lamp = r['uid']
        was = dict(r='living', x=10, y=0, f=0, on=table)
        s, _ = act(s, 'jr_deco_put', uid=lamp, r='living', x=20, y=30)       # off the table
        s, _ = act(s, 'jr_deco_layout', set={lamp: was})                     # Hoàn tác (1.4: a free spot)
        self.assertEqual(fp(s, lamp), ('living', 10, 0, 0, table))
        s, _ = act(s, 'jr_deco_put', uid=lamp, r='living', x=20, y=30)
        s, _ = act(s, 'jr_deco_pick', uid=table)
        with self.assertRaises(GameError) as e:                               # its old spot is gone: the table is in the bag
            act(s, 'jr_deco_layout', set={lamp: was})
        self.assertEqual(e.exception.code, 'taken')
        s, r = place_new(s, 'tv', 'living', 3, 1)
        s, _ = act(s, 'jr_deco_layout', set={r['uid']: None})               # undo a purchase: into the bag
        self.assertEqual(sorted(bag(s)), ['ban_tra', 'tv'])
        for bad in ({}, {sofa: ['living', 0, 1]}, {sofa: ['attic', 0, 0, 0]}, {'zz': None}, [sofa],
                    {sofa: dict(r='living', x=0, y=0)}, {sofa: dict(r='living', x=0, y=0, f=0, z=-1)}, {sofa: 'living'}):
            with self.subTest(bad=bad), self.assertRaises(GameError):
                act(s, 'jr_deco_layout', set=bad)

    def test_buy_more_than_sixty_owned_pieces(self):
        s = owner(wallet=20000)
        s, _ = act(s, 'jr_deco_buy', item='lich', confirm=True)
        r = s['journey']['reno']
        r['items'] += [dict(id=f'x{i}', k='lich', r=None, x=None) for i in range(60)]
        validate_state(s)
        t, _ = act(s, 'jr_deco_buy', item='lich', confirm=True)
        self.assertEqual(len(rn.get(t)['items']), 62)

    def test_story_only(self):
        from game.engine import new_state
        s = new_state()
        self.assertIsNone(public_state(s)['journey']['deco'])
        with self.assertRaises(GameError) as e:
            act(s, 'jr_deco_buy', item='sofa', confirm=True)
        self.assertEqual(e.exception.code, 'story_only')


class Places(unittest.TestCase):
    def test_the_attic_can_be_set_up_but_not_repaired(self):
        s = story(wallet=2000)
        v = D(s)
        self.assertEqual((v['place']['where'], [r['id'] for r in v['rooms']], v['place']['repairs']), ('attic', ['attic'], False))
        s, r = place_new(s, 'den_long', 'attic')
        self.assertIn('Đặt ở căn gác', r['message'])
        self.assertIsNone(public_state(s)['journey']['reno'])               # no structure of yours
        for name, p in (('jr_reno_fix', dict(part='all', cost=10)), ('jr_reno_up', dict(part='wall', lv=1, cost=10))):
            with self.subTest(name=name), self.assertRaises(GameError) as e:
                act(s, name, confirm=True, **p)
            self.assertEqual(e.exception.code, 'no_home')
        s, _ = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_reno_fix', part='all', cost=10, confirm=True)
        self.assertIn('chủ nhà', str(e.exception))

    def test_moving_out_puts_everything_in_the_bag(self):
        s = renter()
        self.assertEqual([r['id'] for r in D(s)['rooms']], ['tro', 'loft'])
        s, _ = place_new(s, 'ban_hoc', 'tro', 0, 0)
        s, _ = place_new(s, 'den_ban', 'tro', 0, 0)
        s, _ = place_new(s, 'nem', 'loft', 0, 0)
        self.assertEqual(len(D(s)['items']), 3)
        s, r = act(s, 'jr_home_leave', confirm=True)                         # back to the attic
        self.assertTrue(any('đồ trang trí đã gói vào túi đồ' in n for n in r.get('effects', [])))
        v = D(s)
        self.assertEqual((v['place']['where'], v['items'], sorted(bag(s))), ('attic', [], ['ban_hoc', 'den_ban', 'nem']))
        self.assertEqual(s['journey']['deco']['pos'], {})
        s, _ = act(s, 'jr_deco_place', uid=v['bag'][0]['id'], room='attic', x=0, y=2)   # set up the attic with them
        s, _ = buy(s, 'tap_the')                                            # buying a home: the attic's things go too
        self.assertEqual(D(s)['items'], [])
        self.assertEqual(len(bag(s)), 3)
        validate_state(s)

    def test_renting_again_starts_with_an_empty_room(self):
        s = renter()
        s, _ = place_new(s, 'den_long', 'tro')
        s, _ = act(s, 'jr_home_rent', kind='ky_tuc_xa', confirm=True)       # tro → dorm: a new place key
        self.assertEqual((D(s)['items'], bag(s)), ([], ['den_long']))
        self.assertTrue(D(s)['place']['key'].startswith('rent:ky_tuc_xa:'))

    def test_the_dorm_bunk_corner(self):
        s = renter('ky_tuc_xa')
        v = D(s)
        self.assertEqual([(r['id'], r['cols'], r['frows']) for r in v['rooms']], [('bunk', 5, 2)])
        with self.assertRaises(GameError) as e:
            place_new(s, 'sofa', 'bunk', 1, 0)
        self.assertIn('không hợp', str(e.exception))
        with self.assertRaises(GameError):                                   # no big bed in a bunk
            act(s, 'jr_deco_buy', item='giuong', confirm=True, room='bunk', x=0, y=0)
        s, _ = place_new(s, 'rem_giuong', 'bunk', 4, 0)
        s, r = place_new(s, 'den_ngu', 'bunk', 2, 0)
        self.assertIn('Giấc ngủ êm', r['message'])                           # the bunk is the bed of the set
        self.assertEqual(D(s)['cozy']['sets'], 3)
        with self.assertRaises(GameError):                                   # the pillow lies there
            place_new(s, 'gau_bong', 'bunk', 0, 0)
        with self.assertRaises(GameError):
            act(s, 'jr_deco_buy', item='rem_giuong', confirm=True, room='attic', x=0, y=0)

    def test_a_spouses_home_can_be_set_up_not_repaired(self):
        s = story(wallet=3000)
        s['marriage'] = dict(v=1, applied=[], spouse=dict(name='Bình', status='married', since=1, wed=1, date=None, couple=7, side='b'),
                             sticker=True, weddings=1)
        hs.apply_effect(s, dict(set='in', couple=7, id='h1', kind='nha_pho', name='An'))
        v = D(s)
        self.assertEqual((v['place']['where'], v['place']['repairs']), ('shared', False))
        s, r = place_new(s, 'sofa', 'living')
        self.assertIsNotNone(at(s, r['uid']))
        with self.assertRaises(GameError) as e:
            act(s, 'jr_reno_fix', part='all', cost=10, confirm=True)
        self.assertEqual(e.exception.code, 'not_owner')


class Cozy(unittest.TestCase):
    def test_each_kind_once_and_sets(self):
        s = owner(wallet=9000)
        s, _ = place_new(s, 'cay_canh', 'living', 0, 1)
        s, _ = place_new(s, 'cay_canh', 'living', 1, 1)
        self.assertEqual(D(s)['cozy']['total'], 2)                          # the same plant twice: once
        s, r = place_new(s, 'cay_monstera', 'bed')
        self.assertNotIn('🎉', r['message'])                                 # three plants, two rooms: not a set
        s, r = place_new(s, 'cay_luoi_ho', 'living', 2, 1)
        self.assertIn('🎉 Hoàn thành “Góc xanh”: ấm cúng +3!', r['message'])
        c = D(s)['cozy']
        self.assertEqual((c['items'], c['sets'], c['total']), (2 + 2 + 1, 3, 8))
        xanh = next(x for x in D(s)['sets'] if x['id'] == 'xanh')
        self.assertEqual((xanh['done'], xanh['room']), (True, 'living'))
        hoc = next(x for x in D(s)['sets'] if x['id'] == 'hoc')
        self.assertEqual((hoc['have'], hoc['miss']), (0, ['một cái bàn', 'một cây đèn', 'kệ sách']))
        self.assertFalse(any(x['id'] == 'vuon' for x in D(s)['sets']))       # no garden in a tập thể: not shown
        self.assertEqual(D(s)['stats']['best'], 8)

    def test_levels(self):
        self.assertEqual([dc.level_of(n) for n in (0, 4, 5, 10, 24, 40, 99)],
                         ['Còn trống trải', 'Còn trống trải', 'Dễ thương', 'Ấm cúng', 'Rất ấm cúng', 'Tổ ấm trong mơ', 'Tổ ấm trong mơ'])

    def rented_cozy(self, decor=True):
        s = renter(wallet=9000)
        if decor:
            for k, room, x, y in (('ban_hoc', 'tro', 0, 0), ('den_ban', 'tro', 0, 0), ('ke_sach', 'tro', 3, 1), ('ghe_luoi', 'tro', 5, 2),
                                  ('tham', 'tro', 2, 1), ('o_meo', 'tro', 0, 2), ('tranh', 'tro', 4, 0), ('den_nhay', 'tro', 4, 1),
                                  ('dong_ho', 'tro', 0, 0), ('anh', 'tro', 1, 0), ('guong', 'tro', 0, 1)):
                s, _ = place_new(s, k, room, x, y)
        return s

    def test_a_rented_room_gives_one_point_at_most(self):
        s = self.rented_cozy()
        c = D(s)['cozy']
        self.assertGreaterEqual(c['total'], 24)                              # Rất ấm cúng…
        self.assertEqual((c['perk'], c['up'], c['steps']), (1, 0, [dict(min=10, spirit=1)]))   # …still +1
        bare = self.rented_cozy(decor=False)
        for x in (s, bare):
            x['journey']['life']['spirit'] = 40
            tick(x, 1)
        self.assertEqual(s['journey']['life']['spirit'] - bare['journey']['life']['spirit'], 1)
        self.assertEqual((s['journey']['deco']['stats']['cozy_days'], s['journey']['deco']['stats']['spirit']), (1, 1))

    def test_own_home_keeps_its_rules_and_no_double_bonus(self):
        s = owner(wallet=9000)
        s, _ = act(s, 'jr_reno_fix', part='all', cost=public_state(s)['journey']['reno']['fix_all'], confirm=True)
        for k, room, x, y in (('sofa', 'living', 0, 1), ('be_ca', 'living', 3, 2), ('tranh', 'living', 3, 0), ('den_nhay', 'bed', 1, 1)):
            s, _ = place_new(s, k, room, x, y)
        c = D(s)['cozy']
        self.assertEqual((c['total'], c['perk'], c['off']), (10, 1, None))
        self.assertEqual(public_state(s)['journey']['reno']['cozy'], 10)
        s['journey']['life']['spirit'] = 50
        tick(s, 1)
        self.assertEqual(s['journey']['life']['spirit'], 50 + hs.HOMES['tap_the']['comfort'] + 1)
        self.assertEqual(s['journey']['deco']['stats']['cozy_days'], 0)      # reno.py paid it, deco.py did not
        self.assertEqual(s['journey']['reno']['stats']['cozy_days'], 1)

    def test_a_run_down_home_shows_why(self):
        s = owner(wallet=9000)
        tick(s, 20)
        for k, room, x, y in (('sofa', 'living', 0, 1), ('be_ca', 'living', 3, 2), ('tranh', 'living', 3, 0), ('den_nhay', 'bed', 1, 1)):
            s, _ = place_new(s, k, room, x, y)
        self.assertEqual(D(s)['cozy']['off'], 'cond')

    def test_the_neighbour_drops_by(self):
        s = self.rented_cozy()
        L = dc.layout(s)
        days = [d for d in range(1, 61) if dc.guest(s, L, 20, d)]
        self.assertTrue(8 <= len(days) <= 32, days)                          # about one day in three
        g = dc.guest(s, L, 20, days[0])
        self.assertEqual(g, dc.guest(s, L, 20, days[0]))                     # seeded: the same visit every time
        self.assertEqual(g['name'], 'Cô Hạnh')
        self.assertNotIn('{item}', g['text'])
        self.assertIsNone(dc.guest(s, L, dc.GUEST_MIN - 1, days[0]))          # not cozy enough: nobody comes
        bare, notes = self.rented_cozy(decor=False), []
        for _ in range(12):
            notes += tick(s, 1)
            tick(bare, 1)
        self.assertTrue(any('Cô Hạnh ghé chơi' in n for n in notes))
        self.assertGreater(s['journey']['deco']['stats']['guests'], 0)
        spent = s['journey']['wallet'] - bare['journey']['wallet']           # a visit is flavour: no money changes hands
        self.assertEqual(spent, -sum(DC.ITEMS[k]['price'] for k in ('ban_hoc', 'den_ban', 'ke_sach', 'ghe_luoi', 'tham', 'o_meo', 'tranh', 'den_nhay',
                                                                     'dong_ho', 'anh', 'guong')))


class Saves(unittest.TestCase):
    def old_save(self):
        """A 1.2.0 save: pieces in room slots, no deco block."""
        s = owner(wallet=9000)
        r = rn.ensure_block(s)
        for k, room, slot in (('sofa', 'living', 'f1'), ('tranh', 'living', 'w0'), ('cay_canh', 'bed', 'f0'), ('lich', 'kitchen', 'w0'), ('tv', 'living', 'f1')):
            if (room, slot) not in {(i['r'], i['x']) for i in r['items']}:
                r['items'].append(dict(id=rn.new_uid(r), k=k, r=room, x=slot))
        r['items'].append(dict(id=rn.new_uid(r), k='ghe_may', r=None, x=None))   # one in the old kho
        validate_state(s)
        self.assertNotIn('deco', s['journey'])
        return s

    def test_old_slots_become_spots(self):
        s = migrate_state(self.old_save())
        validate_state(s)
        v = D(s)
        got = {i['k']: (i['r'], i['y']) for i in v['items']}
        self.assertEqual(set(got), {'sofa', 'tranh', 'cay_canh', 'lich'})
        self.assertEqual((got['sofa'][0], got['tranh'][0], got['cay_canh'][0], got['lich'][0]), ('living', 'living', 'bed', 'kitchen'))
        self.assertEqual(bag(s), ['ghe_may'])
        self.assertEqual(v['cozy']['total'], 3 + 2 + 2 + 1)
        self.assertNotIn('deco', s['journey'])                              # looking writes nothing
        s, _ = act(s, 'jr_deco_buy', item='den_long', confirm=True)          # the first command writes the block
        R = s['journey']['reno']
        self.assertTrue(all(i['r'] is None and i['x'] is None for i in R['items']))
        self.assertEqual(set(R), V1_RENO_KEYS)                               # 1.2.0 still reads this block
        rn.validate(s)
        self.assertEqual({i['k'] for i in D(s)['items']}, {'sofa', 'tranh', 'cay_canh', 'lich'})
        self.assertEqual(sorted(bag(s)), ['den_long', 'ghe_may'])

    def test_a_new_save_round_trips(self):
        s = renter()
        s, _ = place_new(s, 'ban_hoc', 'tro', 0, 0)
        block = copy.deepcopy(s['journey']['deco'])
        s2 = migrate_state(copy.deepcopy(s))
        validate_state(s2)
        self.assertEqual(s2['journey']['deco'], block)

    def test_bad_blocks_are_refused(self):
        s = renter()
        s, r = place_new(s, 'ban_hoc', 'tro', 0, 0)
        uid = r['uid']
        s, r2 = act(s, 'jr_deco_buy', item='ke_sach', confirm=True)
        breaks = [
            lambda d: d.update(v=2),
            lambda d: d.update(extra=1),
            lambda d: d.update(at='Phòng!'),
            lambda d: d['stats'].pop('placed'),
            lambda d: d.update(day=10**5),
            lambda d: d['pos'].update(zz=['tro', 0, 0, 0]),                  # not yours
            lambda d: d['pos'].update({uid: ['tro', 0, 0]}),
            lambda d: d['pos'].update({uid: ['tro', 0, 0, 2]}),
            lambda d: d['pos'].update({uid: ['tro', 6, 0, 0]}),              # out of the room
            lambda d: d['pos'].update({r2['uid']: ['tro', 1, 0, 0]}),        # on top of the desk
            lambda d: d['pos'].update({uid: ['tro', True, 0, 0]}),
        ]
        for i, brk in enumerate(breaks):
            bad = copy.deepcopy(s)
            brk(bad['journey']['deco'])
            with self.subTest(i=i), self.assertRaises(GameError):
                validate_state(bad)

    def test_upgrade_mends_what_an_older_build_left(self):
        s = renter()
        s, r = place_new(s, 'ban_hoc', 'tro', 0, 0)
        s, r2 = act(s, 'jr_deco_buy', item='ke_sach', confirm=True)
        d = s['journey']['deco']
        d['pos'][r2['uid']] = ['tro', 1, 0, 0]                               # overlapping (written by hand)
        d['pos']['gone'] = ['tro', 3, 2, 0]                                  # sold by a rollback build
        d['stats'].pop('guests')
        jr.upgrade(s['journey'])
        self.assertEqual(set(d['pos']), {r['uid']})
        self.assertEqual(d['stats']['guests'], 0)
        validate_state(s)

    def test_a_newer_builds_piece_survives(self):
        s = renter()
        s, _ = place_new(s, 'ban_hoc', 'tro', 0, 0)
        R = s['journey']['reno']
        R['items'].append(dict(id='d9', k='ban_bida', r=None, x=None))      # unknown here: kept, not shown
        validate_state(s)
        self.assertNotIn('ban_bida', bag(s))
        s, _ = act(s, 'jr_deco_buy', item='loa', confirm=True)
        self.assertIn('ban_bida', [i['k'] for i in s['journey']['reno']['items']])

    def test_saves_without_decor_load_unchanged(self):
        for s in (story(wallet=300), owner()):
            before = copy.deepcopy(s['journey'])
            s2 = migrate_state(copy.deepcopy(s))
            validate_state(s2)
            self.assertNotIn('deco', s2['journey'])
            self.assertEqual(s2['journey'].get('reno'), before.get('reno'))


class FreePlacement(unittest.TestCase):
    """1.4: a piece stands anywhere in its zone (units, U per cell), pieces may overlap, small things stand on surfaces."""

    def test_spots_are_clamped_into_the_zone(self):
        s = owner()
        s, sofa = into_bag(s, 'sofa')
        s, r = act(s, 'jr_deco_put', uid=sofa, r='living', x=13, y=7)
        self.assertEqual(fp(s, sofa), ('living', 13, 7, 0, ''))
        self.assertIn('Đã đặt', r['message'])
        s, r = act(s, 'jr_deco_put', uid=sofa, r='living', x=-15, y=90)    # a drag that ends a little outside
        self.assertEqual(fp(s, sofa), ('living', 0, 40, 0, ''))             # 7 x 3 cells: x ≤ 140-60, y ≤ 60-20
        s, r = act(s, 'jr_deco_put', uid=sofa, r='living', x=130, y=40)
        self.assertEqual(fp(s, sofa), ('living', 80, 40, 0, ''))
        s, r = act(s, 'jr_deco_put', uid=sofa, r='living', x=80, y=40)      # a double tap
        self.assertTrue(r['duplicate'])
        self.assertEqual(at(s, sofa), ('living', 4, 2, 0))   # what a 1.3.2 page draws
        s, tranh = into_bag(s, 'tranh')
        s, _ = act(s, 'jr_deco_put', uid=tranh, r='living', x=70, y=3)
        self.assertEqual(fp(s, tranh), ('living', 70, 3, 0, ''))
        with self.assertRaises(GameError) as e:                               # half a cell over the window
            act(s, 'jr_deco_put', uid=tranh, r='living', x=40, y=0)
        self.assertEqual((e.exception.code, 'vướng cửa sổ' in str(e.exception)), ('taken', True))
        s, rem = into_bag(s, 'rem')
        s, _ = act(s, 'jr_deco_put', uid=rem, r='living', x=30, y=0)        # a curtain may hang over it
        s, rug = into_bag(s, 'tham_hoa')
        s, _ = act(s, 'jr_deco_put', uid=rug, r='living', x=110, y=0)       # a doormat by the door
        self.assertEqual(fp(s, rug), ('living', 100, 0, 0, ''))
        s, shelf = into_bag(s, 'ke_sach')
        with self.assertRaises(GameError) as e:                               # but no bookcase in the doorway
            act(s, 'jr_deco_put', uid=shelf, r='living', x=120, y=0)
        self.assertIn('vướng cửa ra vào', str(e.exception))
        s, _ = act(s, 'jr_deco_put', uid=shelf, r='living', x=10, y=0)      # over the rug and the sofa's corner: fine
        for p in (dict(r='living', x=True, y=0), dict(r='living', x='1', y=0), dict(r='living', x=0, y=0, f=2),
                  dict(r='living', x=0, y=0, z=100), dict(r='living', x=0, y=0, z=-1), dict(r='living', x=0, y=0, on=5),
                  dict(r='living', x=0, y=0, on='Bàn!'), dict(r='living', x=401, y=0), dict(r='attic', x=0, y=0),
                  dict(r='living', x=0.5, y=0), dict(r='living', y=0)):
            with self.subTest(p=p), self.assertRaises(GameError):
                act(s, 'jr_deco_put', uid=shelf, **p)
        with self.assertRaises(GameError):
            act(s, 'jr_deco_put', uid='zz', r='living', x=0, y=0)
        with self.assertRaises(GameError):                                   # a bed in the kitchen
            s2, bed = into_bag(s, 'giuong')
            act(s2, 'jr_deco_put', uid=bed, r='kitchen', x=0, y=20)

    def test_overlap_and_order(self):
        s = owner()
        s, a = into_bag(s, 'tranh')
        s, b = into_bag(s, 'anh')
        s, _ = act(s, 'jr_deco_put', uid=a, r='living', x=70, y=0)
        s, _ = act(s, 'jr_deco_put', uid=b, r='living', x=80, y=5)          # a photo over the picture
        z = {i['id']: i['z'] for i in D(s)['items']}
        self.assertGreater(z[b], z[a])                                       # the newest on top
        s, r = act(s, 'jr_deco_put', uid=a, r='living', x=70, y=0, z=z[b] + 1)   # Lên trên
        self.assertIn('lên trên', r['message'])
        self.assertEqual({i['id']: i['z'] for i in D(s)['items']}[a], z[b] + 1)
        s, r = act(s, 'jr_deco_put', uid=a, r='living', x=70, y=0, z=0)     # Xuống dưới
        self.assertIn('xuống dưới', r['message'])

    def test_small_things_stand_on_tables(self):
        s = owner(wallet=9000)
        s, table = into_bag(s, 'ban_tra')
        s, _ = act(s, 'jr_deco_put', uid=table, r='living', x=40, y=20)
        s, r = act(s, 'jr_deco_buy', item='den_ban', confirm=True, put=dict(r='living', x=99, y=9, on=table))
        lamp = r['uid']
        self.assertEqual(fp(s, lamp), ('living', 20, 0, 0, table))          # clamped onto the 2-cell top (a row deep)
        s, r = act(s, 'jr_deco_put', uid=table, r='living', x=0, y=40)
        self.assertIn('Đèn bàn đi theo', r['message'])
        self.assertEqual(fp(s, lamp), ('living', 20, 0, 0, table))          # relative to the table: it came along
        s, r = act(s, 'jr_deco_put', uid=table, r='living', x=0, y=40, f=1)
        self.assertIn('Đã lật', r['message'])
        self.assertEqual(fp(s, lamp), ('living', 0, 0, 1, table))           # mirrored with it
        s, r = act(s, 'jr_deco_put', uid=lamp, r='living', x=20, y=0, f=1, on=table)
        self.assertNotIn('đi theo', r['message'])
        for k in ('binh_hoa', 'gau_bong', 'den_ngu'):                         # 2 x 1 cells: room for four
            s, _ = act(s, 'jr_deco_buy', item=k, confirm=True, put=dict(r='living', x=0, y=0, on=table))
        with self.assertRaises(GameError) as e:
            act(s, 'jr_deco_buy', item='goi_om', confirm=True, put=dict(r='living', x=0, y=0, on=table))
        self.assertIn('hết chỗ', str(e.exception))
        s, sofa = into_bag(s, 'sofa')
        s, _ = act(s, 'jr_deco_put', uid=sofa, r='living', x=60, y=0)
        for k, on in (('goi_om', sofa), ('ke_sach', table), ('goi_om', '#counter'), ('goi_om', 'zz')):
            with self.subTest(k=k, on=on), self.assertRaises(GameError) as e:   # not a surface / not a small thing / no such host
                act(s, 'jr_deco_buy', item=k, confirm=True, put=dict(r='living', x=0, y=0, on=on))
            self.assertEqual(e.exception.code, 'bad_spot')
        s, r = act(s, 'jr_deco_sell', uid=table, confirm=True)
        self.assertIn('vào túi đồ', r['message'])
        self.assertEqual(sorted(bag(s)), ['binh_hoa', 'den_ban', 'den_ngu', 'gau_bong'])
        validate_state(s)

    def test_shelves_counters_and_the_bunk(self):
        s = owner(wallet=9000)
        s, r = act(s, 'jr_deco_buy', item='den_ban', confirm=True, put=dict(r='kitchen', x=30, y=0, on='#counter'))
        self.assertEqual(fp(s, r['uid']), ('kitchen', 30, 0, 0, '#counter'))
        self.assertIn('kệ bếp', r['message'])
        s, shelf = into_bag(s, 'ke_go_treo')
        s, _ = act(s, 'jr_deco_put', uid=shelf, r='living', x=70, y=0)      # a wall shelf…
        s, r = act(s, 'jr_deco_buy', item='binh_hoa', confirm=True, put=dict(r='living', x=4, y=0, on=shelf))
        vase = r['uid']
        s, r = act(s, 'jr_deco_put', uid=shelf, r='living', x=90, y=10)     # …and the vase goes with it
        self.assertEqual(fp(s, vase), ('living', 4, 0, 0, shelf))
        for k in ('den_ngu', 'gau_bong', 'goi_om'):                           # two cells wide: four small things
            s, _ = act(s, 'jr_deco_buy', item=k, confirm=True, put=dict(r='living', x=0, y=0, on=shelf))
        with self.assertRaises(GameError) as e:
            act(s, 'jr_deco_buy', item='binh_hoa', confirm=True, put=dict(r='living', x=0, y=0, on=shelf))
        self.assertIn('Trên kệ gỗ treo trơn hết chỗ', str(e.exception))
        b = renter('ky_tuc_xa')
        b, r = act(b, 'jr_deco_buy', item='gau_bong', confirm=True, put=dict(r='bunk', x=0, y=0, on='#pillow'))
        b, r2 = act(b, 'jr_deco_buy', item='den_ngu', confirm=True, put=dict(r='bunk', x=10, y=0, on='#shelf'))
        self.assertEqual((fp(b, r['uid'])[4], fp(b, r2['uid'])[4]), ('#pillow', '#shelf'))
        self.assertTrue(any(f['t'] == 'shelf' and f['ledge'] for f in D(b)['rooms'][0]['fix']))
        with self.assertRaises(GameError):
            act(b, 'jr_deco_buy', item='gau_bong', confirm=True, put=dict(r='bunk', x=0, y=0, on='#counter'))
        validate_state(b)

    def test_a_room_holds_so_many(self):
        b = renter('ky_tuc_xa', wallet=20000)
        rm = next(r for r in dc.layout(b)['rooms'] if r['id'] == 'bunk')
        cap = dc.room_cap(rm)
        old = rm['cols'] * (rm['wrows'] + rm['frows']) + 4                 # 1.7.15's cap; ×1.5 since (góp ý #192)
        self.assertEqual((dc.old_cap(rm), cap), (old, old * 3 // 2))
        self.assertEqual(D(b)['rooms'][0]['cap'], cap)
        for i in range(cap):
            b, _ = act(b, 'jr_deco_buy', item='lich', confirm=True, put=dict(r='bunk', x=i * 2 % 80, y=i % 3))
        with self.assertRaises(GameError) as e:
            act(b, 'jr_deco_buy', item='lich', confirm=True, put=dict(r='bunk', x=79, y=5))
        self.assertIn(f'đủ {cap} món', str(e.exception))
        self.assertIn('phòng khác', str(e.exception))                       # and how to get more room
        self.assertEqual(len(b['journey']['decor']['items']), old)           # what a 1.7.15 build accepts
        self.assertEqual(len(b['journey']['decor_more']['items']), cap - old)   # the rest, which it shows in its bag
        first = D(b)['items'][0]['id']
        b, _ = act(b, 'jr_deco_put', uid=first, r='bunk', x=33, y=1)        # moving inside a full room is fine
        validate_state(b)


class Skins(unittest.TestCase):
    def test_paint_and_floors(self):
        s = owner()
        cash = s['journey']['wallet']
        s, r = act(s, 'jr_deco_skin', r='living', part='wall', skin='bac_ha')   # a free paint
        self.assertIn('sơn xanh bạc hà', r['message'])
        self.assertEqual((s['journey']['wallet'], D(s)['rooms'][0]['skin']), (cash, {'w': 'bac_ha'}))
        with self.assertRaises(GameError):                                   # a priced one wants a yes
            act(s, 'jr_deco_skin', r='living', part='wall', skin='hoa_nhi')
        s, r = act(s, 'jr_deco_skin', r='living', part='wall', skin='hoa_nhi', confirm=True, n='skin-1')
        self.assertIn('Đã mua giấy hoa nhí, 35 xu', r['message'])
        s, r = act(s, 'jr_deco_skin', r='living', part='wall', skin='hoa_nhi', confirm=True, n='skin-1')
        self.assertTrue(r['duplicate'])
        self.assertEqual((s['journey']['wallet'], D(s)['owned']), (cash - 35, ['hoa_nhi']))
        s, r = act(s, 'jr_deco_skin', r='bed', part='wall', skin='hoa_nhi')  # bought once, any room
        self.assertEqual(s['journey']['wallet'], cash - 35)
        s, _ = act(s, 'jr_deco_skin', r='living', part='floor', skin='go_sang')
        self.assertEqual(D(s)['rooms'][0]['skin'], {'w': 'hoa_nhi', 'f': 'go_sang'})
        s, r = act(s, 'jr_deco_skin', r='living', part='floor', skin='go_sang')
        self.assertTrue(r['duplicate'])
        s, _ = act(s, 'jr_deco_skin', r='living', part='wall', skin='auto')  # back as it was
        self.assertEqual(D(s)['rooms'][0]['skin'], {'f': 'go_sang'})
        cozy = D(s)['cozy']['total']
        self.assertEqual(cozy, 0)                                            # looks only: no Ấm cúng from a wall
        for p in (dict(r='living', part='wall', skin='go_sang'), dict(r='living', part='roof', skin='kem'),
                  dict(r='living', part='wall', skin='zz'), dict(r='living', part='floor', skin='ga_ke'),
                  dict(r='attic', part='wall', skin='kem'), dict(r='living', part='wall', skin='kem', n='!')):
            with self.subTest(p=p), self.assertRaises(GameError):
                act(s, 'jr_deco_skin', **p)
        validate_state(s)

    def test_bunk_sheets_and_the_yard(self):
        b = renter('ky_tuc_xa')
        b, r = act(b, 'jr_deco_skin', r='bunk', part='floor', skin='ga_ke')
        self.assertIn('Giường của bạn giờ trải ga kẻ hồng', r['message'])
        for p in (dict(part='wall', skin='kem'), dict(part='floor', skin='go_sang')):
            with self.subTest(p=p), self.assertRaises(GameError):
                act(b, 'jr_deco_skin', r='bunk', **p)
        s = owner('nha_san', wallet=20000)
        yards = [r['id'] for r in dc.layout(s)['rooms'] if r['type'] == 'yard']
        self.assertTrue(yards)
        with self.assertRaises(GameError):
            act(s, 'jr_deco_skin', r=yards[0], part='floor', skin='go_sang')

    def test_skins_survive_a_move(self):
        s = renter()
        s, _ = act(s, 'jr_deco_skin', r='tro', part='floor', skin='caro', confirm=True)
        s, _ = act(s, 'jr_home_rent', kind='ky_tuc_xa', confirm=True)
        b = D(s)
        self.assertEqual((b['owned'], b['rooms'][0]['skin']), (['caro'], {}))  # bought skins stay yours, a new place starts plain
        s, _ = act(s, 'jr_home_leave', confirm=True)
        s, r = act(s, 'jr_deco_skin', r='attic', part='floor', skin='caro')
        self.assertNotIn('Đã mua', r['message'])


class Idempotent(unittest.TestCase):
    def test_a_double_tap_pays_once(self):
        s = owner()
        cash = s['journey']['wallet']
        s, r = act(s, 'jr_deco_buy', item='cay_canh', confirm=True, n='tap-aaaa')
        s, r2 = act(s, 'jr_deco_buy', item='cay_canh', confirm=True, n='tap-aaaa')
        self.assertTrue(r2['duplicate'])
        self.assertEqual((bag(s), s['journey']['wallet']), (['cay_canh'], cash - 40))
        s, r = act(s, 'jr_deco_buy', item='cay_canh', confirm=True, put=dict(r='living', x=0, y=20))
        s, r2 = act(s, 'jr_deco_buy', item='cay_canh', confirm=True, put=dict(r='living', x=0, y=20))   # same piece, same spot
        self.assertTrue(r2['duplicate'])
        self.assertEqual(s['journey']['wallet'], cash - 80)
        s, _ = act(s, 'jr_deco_sell', uid=r['uid'], confirm=True, n='sell-bbbb')
        s, r3 = act(s, 'jr_deco_sell', uid=r['uid'], confirm=True, n='sell-bbbb')
        self.assertTrue(r3['duplicate'])
        self.assertEqual(s['journey']['wallet'], cash - 80 + 20)
        for i in range(dc.OPS_MAX + 3):                                      # the nonces kept stay few
            s, _ = act(s, 'jr_deco_skin', r='living', part='wall', skin=('kem', 'bac_ha')[i % 2], n=f'op-{i:04d}')
        self.assertEqual(len(s['journey']['decor']['ops']), dc.OPS_MAX)
        validate_state(s)


class FreeSaves(unittest.TestCase):
    """journey.deco keeps the 1.3.2 shape (since 1.4 a grid copy of the free layout, for a rollback);
    journey.decor holds the free spots, the skins and what was bought."""
    V132 = {'v', 'at', 'day', 'pos', 'stats'}

    def save_132(self):
        """A save written by 1.3.2: a grid layout in journey.deco, no journey.decor."""
        s = owner(wallet=9000)
        r = rn.ensure_block(s)
        ids = {}
        for k in ('tham', 'sofa', 'tranh', 'ban_tra', 'den_ban', 'cay_canh', 'ghe_may'):
            ids[k] = rn.new_uid(r)
            r['items'].append(dict(id=ids[k], k=k, r=None, x=None))
        j = s['journey']
        d = j['deco'] = dc.blank(j['life_day'], dc.place(j)['key'])
        d['pos'] = {ids['tham']: ['living', 0, 1, 0], ids['sofa']: ['living', 0, 1, 0], ids['tranh']: ['living', 3, 0, 1],
                    ids['ban_tra']: ['living', 3, 2, 0], ids['den_ban']: ['living', 4, 2, 0], ids['cay_canh']: ['bed', 1, 2, 0]}
        validate_state(s)
        self.assertNotIn('decor', j)
        return s, ids

    def check_132(self, s):
        """What a 1.3.2 build checks: the same keys, [room, x, y, f] small integers, its own pieces only."""
        d = s['journey']['deco']
        self.assertEqual(set(d), self.V132)
        kinds = {i['id']: i['k'] for i in s['journey']['reno']['items']}
        for uid, v in d['pos'].items():
            self.assertTrue(isinstance(v, list) and len(v) == 4 and all(type(n) is int for n in v[1:]), v)
            self.assertTrue(0 <= v[1] <= dc.XY_MAX and 0 <= v[2] <= dc.XY_MAX and v[3] in (0, 1))
            self.assertIn(kinds[uid], DC.KNOWN_132)
        L = dc.layout(s)
        _kept, out = dc.settle(L['rooms'], L['kinds'], {u: tuple(v) for u, v in d['pos'].items()}, list(d['pos']))
        self.assertEqual(out, [])
        self.assertEqual(set(s['journey']['reno']['items'][0]), {'id', 'k', 'r', 'x'})

    def test_a_132_layout_converts_on_load(self):
        s, ids = self.save_132()
        s = migrate_state(s)
        validate_state(s)
        v = D(s)
        self.assertEqual({i['k'] for i in v['items']}, {'tham', 'sofa', 'tranh', 'ban_tra', 'den_ban', 'cay_canh'})
        self.assertEqual(bag(s), ['ghe_may'])
        self.assertEqual(fp(s, ids['sofa']), ('living', 0, 20, 0, ''))      # a cell is U units
        self.assertEqual(fp(s, ids['tranh']), ('living', 60, 0, 1, ''))
        self.assertEqual(fp(s, ids['den_ban'])[4], ids['ban_tra'])          # the lamp on the coffee table stands on it
        self.assertEqual(at(s, ids['den_ban']), ('living', 4, 2, 0))        # and a 1.3.2 page still sees it where it was
        self.assertNotIn('decor', s['journey'])                              # looking writes nothing
        s, _ = act(s, 'jr_deco_put', uid=ids['sofa'], r='living', x=13, y=23)   # the first change writes both blocks
        D2 = s['journey']['decor']
        self.assertEqual(set(D2), dc.FREE_KEYS)
        self.assertEqual(len(D2['items']), 6)
        self.assertEqual(D2['sig'], dc.sig(s['journey']['deco']['pos']))
        self.assertEqual(s['journey']['deco']['pos'][ids['sofa']], ['living', 1, 1, 0])   # the grid copy follows, rounded
        self.check_132(s)

    def test_rolled_back_and_forward_again(self):
        s, ids = self.save_132()
        s, _ = act(s, 'jr_deco_put', uid=ids['sofa'], r='living', x=13, y=23)
        s, _ = act(s, 'jr_deco_put', uid=ids['cay_canh'], r='bed', x=27, y=31)
        s, r = act(s, 'jr_deco_buy', item='ke_go_treo', confirm=True, put=dict(r='living', x=90, y=0))   # 1.3.2 has no such piece
        shelf = r['uid']
        s, _ = act(s, 'jr_deco_skin', r='living', part='wall', skin='bac_ha')
        self.check_132(s)
        self.assertNotIn(shelf, s['journey']['deco']['pos'])
        # a 1.3.2 build plays a day: moves the tranh one cell, puts the plant in its bag, leaves the rest
        old = copy.deepcopy(s)
        pos = old['journey']['deco']['pos']
        pos[ids['tranh']] = ['living', 4, 0, 1]
        del pos[ids['cay_canh']]
        validate_state(old)
        back = migrate_state(old)
        validate_state(back)
        self.assertEqual(fp(back, ids['sofa']), ('living', 13, 23, 0, ''))  # untouched there: its fine spot kept
        self.assertEqual(fp(back, ids['tranh']), ('living', 80, 0, 1, ''))  # moved there: taken from the grid
        self.assertIsNone(fp(back, ids['cay_canh']))                         # bagged there: in the bag here
        self.assertIn('cay_canh', bag(back))
        self.assertEqual(fp(back, shelf), ('living', 90, 0, 0, ''))          # never on the grid: kept
        self.assertEqual(D(back)['rooms'][0]['skin'], {'w': 'bac_ha'})        # the skins waited
        back, _ = act(back, 'jr_deco_put', uid=ids['sofa'], r='living', x=14, y=23)
        self.assertEqual(back['journey']['decor']['sig'], dc.sig(back['journey']['deco']['pos']))
        self.check_132(back)

    def test_legacy_commands_still_work(self):
        s, ids = self.save_132()
        s, r = act(s, 'jr_deco_place', uid=ids['ghe_may'], room='living', x=2, y=2)
        self.assertEqual(at(s, ids['ghe_may']), ('living', 2, 2, 0))
        s, r = act(s, 'jr_deco_buy', item='binh_hoa', confirm=True, room='living', x=3, y=2)   # a 1.3.2 page: a cell on the table
        self.assertEqual(fp(s, r['uid'])[4], ids['ban_tra'])
        s, _ = act(s, 'jr_deco_layout', set={ids['sofa']: ['living', 2, 1, 0]})   # a 1.3.2 undo
        self.assertEqual(at(s, ids['sofa']), ('living', 2, 1, 0))
        s, r = act(s, 'jr_reno_buy', item='lich', confirm=True, room='living', slot='w0')   # 1.2.0
        self.assertIsNotNone(at(s, r['uid']))
        s, _ = act(s, 'jr_reno_store', uid=r['uid'])
        self.assertIn('lich', bag(s))
        self.check_132(s)

    def test_bad_free_blocks_are_refused(self):
        s, ids = self.save_132()
        s, _ = act(s, 'jr_deco_put', uid=ids['sofa'], r='living', x=13, y=23)
        sofa, lamp = ids['sofa'], ids['den_ban']
        breaks = [
            lambda D: D.update(v=2),
            lambda D: D.update(extra=1),
            lambda D: D.pop('ops'),
            lambda D: D.update(sig=-1),
            lambda D: D.update(at='Phòng!'),
            lambda D: D['items'].update(zz=dict(r='living', x=0, y=0, f=0)),           # not yours
            lambda D: D['items'].update({sofa: dict(r='living', x=0, y=0)}),
            lambda D: D['items'].update({sofa: dict(r='living', x=0, y=0, f=2)}),
            lambda D: D['items'].update({sofa: dict(r='living', x=True, y=0, f=0)}),
            lambda D: D['items'].update({sofa: dict(r='living', x=0, y=0, f=0, z=500)}),
            lambda D: D['items'].update({sofa: dict(r='living', x=0, y=0, f=0, junk=1)}),
            lambda D: D['items'].update({sofa: dict(r='living', x=999, y=0, f=0)}),
            lambda D: D['items'].update({sofa: dict(r='kitchen', x=0, y=20, f=0)}),        # a sofa in the kitchen
            lambda D: D['items'].update({lamp: dict(r='living', x=0, y=0, f=0, on='zz')}),  # on nothing
            lambda D: D['skins'].update(living={'w': 'Kem!'}),
            lambda D: D['skins'].update(living={'roof': 'kem'}),
            lambda D: D.update(owned=['kem', 'kem']),
            lambda D: D.update(owned=[1]),
            lambda D: D.update(ops=['x'] * 3),
            lambda D: D.update(ops=[f'op-{i:04d}' for i in range(dc.OPS_MAX + 1)]),
        ]
        for i, brk in enumerate(breaks):
            bad = copy.deepcopy(s)
            brk(bad['journey']['decor'])
            with self.subTest(i=i), self.assertRaises(GameError):
                validate_state(bad)
        ok = copy.deepcopy(s)
        ok['journey']['decor']['skins']['living'] = {'w': 'giay_tu_ban_moi'}  # a newer build's skin: kept, not shown
        validate_state(ok)
        self.assertEqual(D(ok)['rooms'][0]['skin'], {})

    def test_upgrade_prunes_what_is_gone(self):
        s, ids = self.save_132()
        s, _ = act(s, 'jr_deco_put', uid=ids['sofa'], r='living', x=13, y=23)
        D0 = s['journey']['decor']
        s['journey']['reno']['items'] = [i for i in s['journey']['reno']['items'] if i['id'] != ids['ban_tra']]   # sold by an older build
        s['journey']['deco']['pos'].pop(ids['ban_tra'], None)
        s['journey']['deco']['pos'].pop(ids['den_ban'], None)
        jr.upgrade(s['journey'])
        self.assertNotIn(ids['ban_tra'], D0['items'])
        validate_state(s)
        self.assertIn('den_ban', bag(s))


class Colours(unittest.TestCase):
    """Bảng màu (game/wardrobe.py): a piece of furniture wears a colour of the player's palette, stored per piece
    (s['colors']['deco'][uid]) so it stays with the piece in the bag, at the next place, in a rented room or the dorm."""

    def test_a_colour_follows_the_piece_into_the_bag_and_the_next_home(self):
        s = renter()
        s, r = place_new(s, 'ban_hoc', 'tro', 0, 0)
        uid = r['uid']
        w0 = s['journey']['wallet']
        with self.assertRaises(GameError):                                   # not unlocked, no buy
            act(s, 'jr_wd_deco', uid=uid, color='navy')
        s, r = act(s, 'jr_wd_deco', uid=uid, color='navy', buy=True)
        self.assertEqual(r['message'], 'Đã trả 40 xu mở khóa màu Xanh navy. Bàn học giờ mang màu Xanh navy.')
        self.assertEqual(s['journey']['wallet'], w0 - 40)
        self.assertEqual(public_state(s)['colors']['deco'], {uid: 'navy'})
        s, r = act(s, 'jr_wd_deco', uid=uid, color='navy', buy=True)         # a second tap: nothing paid
        self.assertTrue(r.get('duplicate'))
        self.assertEqual(s['journey']['wallet'], w0 - 40)
        s, _ = place_new(s, 'den_ban', 'tro', 0, 0)
        lamp = D(s)['items'][-1]['id']
        s, _ = act(s, 'jr_wd_deco', uid=lamp, color='navy')                  # unlocked once: free on any piece
        self.assertEqual(s['journey']['wallet'], w0 - 40 - DC.ITEMS['den_ban']['price'])
        s, _ = act(s, 'jr_home_leave', confirm=True)                         # moving out: everything in the bag
        self.assertEqual(D(s)['items'], [])
        self.assertEqual(s['colors']['deco'], {uid: 'navy', lamp: 'navy'})
        s, _ = act(s, 'jr_deco_place', uid=uid, room='attic', x=0, y=2)
        self.assertEqual(s['colors']['deco'][uid], 'navy')
        s, _ = act(s, 'jr_deco_pick', uid=uid)                               # put away and placed again: same colour
        s, _ = act(s, 'jr_deco_place', uid=uid, room='attic', x=0, y=2)
        self.assertEqual(s['colors']['deco'][uid], 'navy')
        s, r = act(s, 'jr_wd_deco', uid=lamp, color='goc')
        self.assertEqual((r['message'], s['colors']['deco']), ('Đèn bàn trở lại màu gốc.', {uid: 'navy'}))
        validate_state(s)
        # Sold: the colour goes with it (and a load drops any an older build left behind).
        s, _ = act(s, 'jr_deco_sell', uid=uid, confirm=True)
        validate_state(s)
        self.assertEqual(s['colors']['deco'], {})
        self.assertEqual(migrate_state(s)['colors']['deco'], {})
        with self.assertRaises(GameError):
            act(s, 'jr_wd_deco', uid=uid, color='navy')

    def test_the_dorm_bunk_and_bad_payloads(self):
        s = renter('ky_tuc_xa')
        s, r = place_new(s, 'rem_giuong', 'bunk', 4, 0)
        uid = r['uid']
        s, _ = act(s, 'jr_wd_unlock', color='mint')
        s, _ = act(s, 'jr_wd_deco', uid=uid, color='mint')
        self.assertEqual(s['colors']['deco'], {uid: 'mint'})
        for p in ({'uid': 'zz', 'color': 'mint'}, {'uid': uid, 'color': 'cau_vong'}, {'uid': uid}, {'uid': uid, 'color': 'mint', 'x': 1},
                  {'uid': uid, 'color': 'mint', 'buy': 'yes'}, {'uid': 5, 'color': 'mint'}, {'uid': uid, 'color': 'hong'}):
            with self.assertRaises(GameError, msg=p):
                act(s, 'jr_wd_deco', **p)
        validate_state(s)

    def test_colours_with_free_placement(self):
        """1.4: the colour stays in s['colors']['deco'] (not journey.decor) through free moves, stacking and a sale."""
        s = owner(wallet=9000)
        s, r = act(s, 'jr_deco_buy', item='ban_tra', confirm=True, put=dict(r='living', x=40, y=20))
        table = r['uid']
        s, r = act(s, 'jr_deco_buy', item='binh_hoa', confirm=True, put=dict(r='living', x=10, y=0, on=table))
        vase = r['uid']
        s, _ = act(s, 'jr_wd_deco', uid=table, color='navy', buy=True)
        s, _ = act(s, 'jr_wd_deco', uid=vase, color='navy')
        s, _ = act(s, 'jr_deco_put', uid=table, r='living', x=0, y=40, f=1)   # moved and flipped, the vase rides along
        self.assertEqual(s['colors']['deco'], {table: 'navy', vase: 'navy'})
        self.assertNotIn('colors', str(s['journey']['decor']))
        s2 = migrate_state(copy.deepcopy(s))                                  # a load prunes nothing that is still yours
        self.assertEqual(s2['colors']['deco'], {table: 'navy', vase: 'navy'})
        s, _ = act(s, 'jr_deco_sell', uid=table, confirm=True, n='sell-tint')
        self.assertEqual(s['colors']['deco'], {vase: 'navy'})                # the table's colour went with it
        self.assertIn('binh_hoa', bag(s))
        s = migrate_state(s)
        validate_state(s)
        self.assertEqual(public_state(s)['colors']['deco'], {vase: 'navy'})

    def test_every_piece_can_take_a_colour(self):
        from pathlib import Path
        js = (Path(__file__).resolve().parents[1] / 'public' / 'js' / 'v4' / 'deco-art.js').read_text(encoding='utf-8')
        start = js.index('export const TINT={') + len('export const TINT={')
        block = js[start:js.index('};', start)]
        import re
        block = re.sub(r'\{[^{}]*\}|\[[^\[\]]*\]', '0', block)                     # nested family maps and lists
        ids = set(re.findall(r'([a-z_]+):', block))
        self.assertEqual(ids, set(DC.ITEMS))


if __name__ == '__main__':
    unittest.main()
