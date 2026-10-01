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
        self.assertEqual(len(DC.ITEMS), 65)
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
            (dict(item='tv', room='living', x=2, y=1), 'vướng sofa vải', 'taken'),               # overlap
            (dict(item='ke_sach', room='living', x=5, y=0), 'vướng cửa ra vào', 'taken'),         # the door's floor cell
            (dict(item='tranh', room='living', x=1, y=0), 'vướng cửa sổ', 'taken'),               # the window
            (dict(item='tranh', room='living', x=4, y=2), 'nằm ngoài', 'bad_spot'),               # two wall rows only
            (dict(item='ke_sach', room='living', x=6, y=2), 'nằm ngoài', 'bad_spot'),             # 2 wide from the last column
            (dict(item='giuong', room='kitchen', x=0, y=1), 'không hợp', 'bad_spot'),             # a bed in the kitchen
            (dict(item='den_ban', room='living', x=2, y=1), 'chỉ đặt lên bàn', 'bad_spot'),       # a lamp on the sofa
            (dict(item='tv', room='living', x=0, y=2), 'Trên sàn chỗ này có gấu bông', 'taken'),  # over the bear
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
        s, r = place_new(s, 'tv', 'living', 3, 1)
        with self.assertRaises(GameError) as e:                               # its old spot is taken now
            act(s, 'jr_deco_layout', set={sofa: ['living', 2, 1, 0]})
        self.assertEqual(e.exception.code, 'taken')
        s, _ = act(s, 'jr_deco_layout', set={r['uid']: None})               # undo a purchase: into the bag
        self.assertEqual(bag(s), ['tv'])
        for bad in ({}, {sofa: ['living', 0, 1]}, {sofa: ['attic', 0, 0, 0]}, {'zz': None}, [sofa]):
            with self.subTest(bad=bad), self.assertRaises(GameError):
                act(s, 'jr_deco_layout', set=bad)

    def test_items_max(self):
        s = owner(wallet=20000)
        s, _ = act(s, 'jr_deco_buy', item='lich', confirm=True)
        r = s['journey']['reno']
        r['items'] += [dict(id=f'x{i}', k='lich', r=None, x=None) for i in range(rn.ITEMS_MAX - 1)]
        validate_state(s)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_deco_buy', item='lich', confirm=True)
        self.assertEqual(e.exception.code, 'full')

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
        # Sold: the entry is harmless until the next load drops it.
        s, _ = act(s, 'jr_deco_sell', uid=uid, confirm=True)
        validate_state(s)
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
