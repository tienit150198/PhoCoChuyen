"""🛠️ Sửa nhà (game/reno.py): the view of a home you own, repairs and upgrades paid like the home, gentle wear, the
Ấm cúng morning bonus, moving house, validation and older saves. Furniture is game/deco.py's now (tests/test_deco.py);
here only 1.2.0's slot commands, still sent by a page loaded before 1.3, which land on the grid."""
import copy
import unittest

from game import housing as hs
from game import journey as jr
from game import reno as rn
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import B, act, opened, story
from tests.test_housing import buy


def R(s):
    return s['journey']['reno']


def view(s):
    return public_state(s)['journey']['reno']


def deco(s):
    return public_state(s)['journey']['deco']


def placed(s):
    return {i['id']: (i['k'], i['r']) for i in deco(s)['items']}


def part(v, pid):
    return next(p for p in v['parts'] if p['id'] == pid)


def tick(s, n=1, salary=0):
    """Close `n` life days like end_day: the bank, the home, then the inside of the home catch up."""
    from game import bank as bk
    notes = []
    for _ in range(n):
        j = s['journey']
        if salary:
            jr._wallet(j, salary, 'salary', 'Lương ngày')
        j['life_day'] += 1
        notes += bk.on_life_day(s)
        notes += hs.on_life_day(s)
        notes += rn.on_life_day(s)
    validate_state(s)
    return notes


def owner(kind='tap_the', wallet=4000, days=0):
    s = story(wallet=wallet)
    s, r = buy(s, kind)
    if days:
        tick(s, days)
    return s


def spirit(s):
    return s['journey']['life']['spirit']


class Catalogue(unittest.TestCase):
    def test_every_home_has_rooms_and_sane_prices(self):
        self.assertEqual(set(rn.HOUSES), set(hs.OWN))                       # a new home needs a layout here
        for kind, H in rn.HOUSES.items():
            with self.subTest(kind=kind):
                rooms = rn.rooms(kind)
                self.assertTrue({'living', 'bed', 'kitchen'} <= {r['id'] for r in rooms})
                self.assertTrue(all(r['wall'] <= 9 and r['floor'] <= 9 for r in rooms))   # slots w0..w9 / f0..f9
                ups = sum(rn.up_cost(kind, p, lv) for p in rn.PARTS for lv in (1, 2))
                self.assertLess(ups, hs.HOMES[kind]['price'])               # a full renovation costs less than the home
                start = rn.blank(dict(id='h1', kind=kind, day=1), 1)['parts']
                self.assertTrue(all(rn.COND_MIN <= x['c'] <= 100 for x in start.values()))
        fix = sum(rn.fix_cost('tap_the', p, x['c']) for p, x in rn.blank(dict(id='h1', kind='tap_the', day=1), 1)['parts'].items())
        self.assertLess(fix, 300)                                            # the old tập thể: a few days of salary
        from game import deco_content as DC
        self.assertIs(rn.ITEMS, DC.ITEMS)                                    # one catalogue (deco_content.py)
        c = jr.content()['reno']
        self.assertNotIn('items', c)
        self.assertEqual((c['cozy_lv'], c['cozy_cond'], c['sell_pct']), (rn.COZY_LV, rn.COZY_COND, 50))


class NoHome(unittest.TestCase):
    def test_nothing_without_a_home_of_your_own(self):
        s = story(wallet=4000)
        self.assertIsNone(view(s))
        with self.assertRaises(GameError) as e:
            act(s, 'jr_reno_buy', item='sofa', room='living', slot='f0', confirm=True)
        self.assertEqual(e.exception.code, 'no_home')
        s, _ = act(s, 'jr_home_rent', kind='tro_moi', confirm=True)          # a rented room is not yours to renovate
        self.assertIsNone(view(s))
        self.assertNotIn('reno', s['journey'])

    def test_spouse_home_is_theirs(self):
        s = story(wallet=1000)
        s['marriage'] = dict(v=1, applied=[], spouse=dict(name='Bình', status='married', since=1, wed=1, date=None, couple=7, side='b'),
                             sticker=True, weddings=1)
        hs.apply_effect(s, dict(set='in', couple=7, id='h1', kind='nha_pho', name='An'))
        with self.assertRaises(GameError) as e:
            act(s, 'jr_reno_fix', part='all', cost=10, confirm=True)
        self.assertEqual(e.exception.code, 'not_owner')
        self.assertIn('An', str(e.exception))


class ViewAndRepairs(unittest.TestCase):
    def test_view_is_computed_until_the_first_command(self):
        s = owner(days=12)
        v = view(s)
        self.assertNotIn('reno', s['journey'])                              # looking writes nothing to the save
        self.assertEqual(v['home']['kind'], 'tap_the')
        self.assertEqual([r['id'] for r in v['rooms']], ['living', 'bed', 'kitchen'])
        wall = part(v, 'wall')
        self.assertEqual(wall['c'], 50 - 3)                                 # 55 − 5, then a point every 4 life days
        self.assertTrue(wall['worn'])
        self.assertEqual(wall['fix'], rn.fix_cost('tap_the', 'wall', wall['c']))
        self.assertEqual(v['fix_all'], sum(p['fix'] for p in v['parts']))
        self.assertEqual((v['cozy'], v['perk'], v['count']), (0, 0, 0))

    def test_fix_everything_from_the_wallet(self):
        s = owner(days=12)
        before = s['journey']['wallet']
        v = view(s)
        s, r = act(s, 'jr_reno_fix', part='all', cost=v['fix_all'], confirm=True)
        self.assertIn('Sửa cả nhà xong', r['message'])
        self.assertEqual(s['journey']['wallet'], before - v['fix_all'])
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount']), ('home', -v['fix_all']))
        self.assertIn('Sửa cả nhà', row['label'])
        self.assertEqual(hs.get(s)['log'][-1]['amt'], -v['fix_all'])       # Sổ nhà cửa
        self.assertTrue(all(p['c'] == 100 and not p['fix'] for p in view(s)['parts']))
        self.assertEqual(R(s)['stats']['fixed'], 5)
        with self.assertRaises(GameError) as e:                              # a second tap: nothing left to pay
            act(s, 'jr_reno_fix', part='all', cost=v['fix_all'], confirm=True)
        self.assertEqual(e.exception.code, 'nothing')

    def test_bank_account_pays_first(self):
        s = opened(wallet=2500, deposit=2400)
        s, _ = buy(s, 'tap_the')                                            # 1800 + fee from the account first
        tick(s, 8)
        bal, cash = B(s)['balance'], s['journey']['wallet']
        p = part(view(s), 'roof')
        s, _ = act(s, 'jr_reno_fix', part='roof', cost=p['fix'], confirm=True)
        took = min(bal, p['fix'])
        self.assertEqual((B(s)['balance'], s['journey']['wallet']), (bal - took, cash - (p['fix'] - took)))

    def test_not_enough_money_and_stale_prices(self):
        s = owner(wallet=1800 + hs.buy_fee(1800) + 20, days=12)            # 20 xu left after buying
        v = view(s)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_reno_fix', part='all', cost=v['fix_all'], confirm=True)
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertIn('còn thiếu', str(e.exception))
        self.assertNotIn('reno', s['journey'])                              # nothing changed
        s['journey']['wallet'] += 1000
        with self.assertRaises(GameError) as e:
            act(s, 'jr_reno_fix', part='wall', cost=part(v, 'wall')['fix'] + 1, confirm=True)
        self.assertEqual(e.exception.code, 'stale_quote')
        with self.assertRaises(GameError):
            act(s, 'jr_reno_fix', part='wall', cost=part(v, 'wall')['fix'])   # no confirm
        with self.assertRaises(GameError):
            act(s, 'jr_reno_fix', part='attic', cost=1, confirm=True)

    def test_upgrades_two_levels(self):
        s = owner(days=12)
        p = part(view(s), 'floor')
        self.assertEqual((p['up']['lv'], p['up']['name']), (1, 'Lát gạch men mới'))
        with self.assertRaises(GameError):
            act(s, 'jr_reno_up', part='floor', lv=2, cost=rn.up_cost('tap_the', 'floor', 2), confirm=True)   # skipping a level
        s, r = act(s, 'jr_reno_up', part='floor', lv=1, cost=p['up']['cost'], confirm=True)
        self.assertIn('Ấm cúng +2', r['message'])
        p2 = part(view(s), 'floor')
        self.assertEqual((p2['lv'], p2['c'], p2['up']['name']), (1, 100, 'Lát sàn gỗ'))
        with self.assertRaises(GameError) as e:                              # a double tap of the first level
            act(s, 'jr_reno_up', part='floor', lv=1, cost=p['up']['cost'], confirm=True)
        self.assertEqual(e.exception.code, 'stale_quote')
        s, _ = act(s, 'jr_reno_up', part='floor', lv=2, cost=p2['up']['cost'], confirm=True)
        self.assertIsNone(part(view(s), 'floor')['up'])
        self.assertEqual(view(s)['cozy'], 2 * rn.COZY_LV)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_reno_up', part='floor', lv=3, cost=1, confirm=True)
        self.assertEqual(e.exception.code, 'nothing')

    def test_wear_is_slow_and_stops(self):
        s = owner(kind='can_ho_mini')
        s, _ = act(s, 'jr_reno_fix', part='all', cost=view(s)['fix_all'], confirm=True)
        notes = tick(s, 4 * 41)                                             # a point every 4 life days at level 0
        c = {p['id']: p['c'] for p in view(s)['parts']}
        self.assertTrue(all(58 <= x <= 60 for x in c.values()), c)
        self.assertTrue(any('Nhà mình' in n for n in notes))               # said once when a part looks worn
        tick(s, 400)
        self.assertTrue(all(p['c'] == rn.COND_MIN for p in view(s)['parts']))   # tired, never ruined
        s, _ = act(s, 'jr_reno_up', part='wall', lv=1, cost=part(view(s), 'wall')['up']['cost'], confirm=True)
        tick(s, 60)
        self.assertEqual(part(view(s), 'wall')['c'], 90)                    # level 1: a point every 6 days


class OldPage(unittest.TestCase):
    """1.2.0's jr_reno_buy / move / store / sell from a page loaded before 1.3: as near the old slot as fits."""
    def test_buy_into_a_slot(self):
        s = owner()
        cash = s['journey']['wallet']
        s, r = act(s, 'jr_reno_buy', item='sofa', room='living', slot='f0', confirm=True)
        self.assertEqual(s['journey']['wallet'], cash - 180)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'home')
        self.assertEqual(r['uid'], 'd1')
        self.assertEqual(placed(s), {'d1': ('sofa', 'living')})
        self.assertEqual(view(s)['cozy'], 3)
        self.assertEqual(R(s)['items'], [dict(id='d1', k='sofa', r=None, x=None)])   # 1.2.0's shape, no slot
        s, r = act(s, 'jr_reno_buy', item='tranh', room='living', slot='w0', confirm=True)
        self.assertEqual(next(i for i in deco(s)['items'] if i['id'] == r['uid'])['y'], 0)   # on the wall

    def test_refusals(self):
        s = owner()
        cases = [
            (dict(item='ke_sach', room='living', slot='f7x'), 'không đặt'),
            (dict(item='ke_sach', room='balcony', slot='f0'), 'Chọn phòng'),    # the tập thể has no balcony
            (dict(item='ban_tho', room='living', slot='f1'), 'không bán'),
        ]
        for p, words in cases:
            with self.subTest(p=p), self.assertRaises(GameError) as e:
                act(s, 'jr_reno_buy', confirm=True, **p)
            self.assertIn(words, str(e.exception))
        s, r = act(s, 'jr_reno_buy', item='giuong', room='kitchen', slot='f0', confirm=True)   # no bed in a kitchen:
        self.assertEqual(deco(s)['bag'], [dict(id=r['uid'], k='giuong')])                    # it waits in the bag

    def test_move_store_sell(self):
        s = owner()
        s, _ = act(s, 'jr_reno_buy', item='cay_canh', room='living', slot='f0', confirm=True)
        s, _ = act(s, 'jr_reno_buy', item='tranh', room='living', slot='w0', confirm=True)
        s, r = act(s, 'jr_reno_move', uid='d1', room='bed', slot='f2')
        self.assertIn('phòng ngủ', r['message'])
        s, _ = act(s, 'jr_reno_store', uid='d2')
        self.assertEqual((placed(s), deco(s)['bag']), ({'d1': ('cay_canh', 'bed')}, [dict(id='d2', k='tranh')]))
        self.assertEqual(view(s)['cozy'], 2)                                 # in the bag: no Ấm cúng
        s, _ = act(s, 'jr_reno_move', uid='d2', room='kitchen', slot='w0')  # back out of the bag
        cash = s['journey']['wallet']
        s, r = act(s, 'jr_reno_sell', uid='d1', confirm=True)
        self.assertEqual(s['journey']['wallet'], cash + 20)                 # half of 40 xu
        self.assertEqual([i['id'] for i in R(s)['items']], ['d2'])
        with self.assertRaises(GameError):
            act(s, 'jr_reno_sell', uid='d1', confirm=True)

    def test_each_kind_counts_once(self):
        s = owner()
        s, _ = act(s, 'jr_reno_buy', item='cay_canh', room='living', slot='f0', confirm=True)
        s, _ = act(s, 'jr_reno_buy', item='cay_canh', room='living', slot='f1', confirm=True)
        self.assertEqual(view(s)['cozy'], 2)

    def test_legacy_buy_more_than_sixty_owned_pieces(self):
        s = owner(wallet=20000)
        s, _ = act(s, 'jr_reno_buy', item='lich', room='living', slot='w0', confirm=True)
        R(s)['items'] += [dict(id=f'x{i}', k='lich', r=None, x=None) for i in range(60)]
        validate_state(s)
        t, _ = act(s, 'jr_reno_buy', item='lich', room='living', slot='w1', confirm=True)
        self.assertEqual(len(R(t)['items']), 62)


class Cozy(unittest.TestCase):
    def cozy_home(self, fix=True):
        s = owner(wallet=6000, days=4 if fix else 20)
        if fix:
            s, _ = act(s, 'jr_reno_fix', part='all', cost=view(s)['fix_all'], confirm=True)
        for item, room, slot in (('sofa', 'living', 'f0'), ('be_ca', 'living', 'f1'), ('tranh', 'living', 'w0'), ('den_nhay', 'bed', 'w0')):
            s, _ = act(s, 'jr_reno_buy', item=item, room=room, slot=slot, confirm=True)
        return s

    def test_morning_bonus(self):
        s = self.cozy_home()
        v = view(s)
        self.assertEqual((v['cozy'], v['perk'], v['perk_on']), (10, 1, True))
        s['journey']['life']['spirit'] = 50
        tick(s, 1)
        self.assertEqual(spirit(s), 50 + hs.HOMES['tap_the']['comfort'] + 1)
        self.assertEqual(R(s)['stats']['cozy_days'], 1)

    def test_no_bonus_in_a_run_down_home_and_never_a_penalty(self):
        s = self.cozy_home(fix=False)
        v = view(s)
        self.assertLess(v['cond'], rn.COZY_COND)
        self.assertEqual((v['perk'], v['perk_on']), (1, False))
        s['journey']['life']['spirit'] = 50
        tick(s, 1)
        self.assertEqual(spirit(s), 50 + hs.HOMES['tap_the']['comfort'])   # the home's own comfort only

    def test_bonus_steps(self):
        self.assertEqual([rn.perk_of(n) for n in (0, 9, 10, 23, 24, 80)], [0, 0, 1, 1, 2, 2])


class MovingHouse(unittest.TestCase):
    def test_selling_puts_furniture_in_the_kho_and_the_next_home_starts_fresh(self):
        s = owner(wallet=9000)
        s, _ = act(s, 'jr_reno_buy', item='sofa', room='living', slot='f0', confirm=True)
        s, _ = act(s, 'jr_reno_up', part='wall', lv=1, cost=rn.up_cost('tap_the', 'wall', 1), confirm=True)
        tick(s, 2)
        s, _ = act(s, 'jr_home_sell', confirm=True, value=hs.value_of(hs.get(s)['own'], s['journey']['life_day']))
        self.assertIsNone(view(s))
        self.assertEqual((R(s)['hid'], R(s)['parts'], R(s)['items'][0]['r']), (None, {}, None))
        validate_state(s)
        cash = s['journey']['wallet']
        s, r = act(s, 'jr_reno_sell', uid='d1', confirm=True)              # the kho can still be sold from the attic
        self.assertEqual(s['journey']['wallet'], cash + 90)
        s, _ = buy(s, 'can_ho_mini')
        v = view(s)
        self.assertEqual(v['home']['kind'], 'can_ho_mini')
        self.assertTrue(all(p['lv'] == 0 for p in v['parts']))              # upgrades stayed with the old home
        self.assertIn('balcony', [r['id'] for r in v['rooms']])

    def test_free_spots_and_skins_keep_the_old_blocks(self):
        """1.4's free placement and wallpapers live in journey.decor: reno keeps 1.2.0's shape, Ấm cúng its rules."""
        s = owner(wallet=9000, days=2)
        s, _ = act(s, 'jr_reno_fix', part='all', cost=view(s)['fix_all'], confirm=True)
        s, r = act(s, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=17, y=11))
        s, _ = act(s, 'jr_deco_buy', item='ban_tra', confirm=True, put=dict(r='living', x=50, y=40))
        s, _ = act(s, 'jr_deco_skin', r='living', part='wall', skin='op_go', confirm=True)
        self.assertEqual(view(s)['cozy'], 4)                                 # a wallpaper is looks only
        self.assertEqual(set(R(s)), {'v', 'hid', 'day', 'seq', 'parts', 'items', 'spent', 'stats'})
        self.assertTrue(all(set(i) == {'id', 'k', 'r', 'x'} and i['r'] is None for i in R(s)['items']))
        s, _ = act(s, 'jr_reno_move', uid=r['uid'], room='living', slot='f2')   # a 1.2.0 page still moves it
        self.assertEqual(placed(s)[r['uid']], ('sofa', 'living'))
        self.assertEqual(view(s)['cozy'], 4)
        s, _ = act(s, 'jr_home_sell', confirm=True, value=hs.value_of(hs.get(s)['own'], s['journey']['life_day']))
        s, _ = buy(s, 'can_ho_mini')
        v = deco(s)
        self.assertEqual((v['items'], v['owned']), ([], ['op_go']))          # a new home starts plain; the wallpaper is still yours
        self.assertTrue(all(rm['skin'] == {} for rm in v['rooms']))
        validate_state(s)

    def test_furniture_follows_to_the_next_home(self):
        s = owner(wallet=9000)
        s, _ = act(s, 'jr_reno_buy', item='be_ca', room='living', slot='f0', confirm=True)
        s, _ = act(s, 'jr_home_sell', confirm=True, value=hs.value_of(hs.get(s)['own'], s['journey']['life_day']))
        s, _ = buy(s, 'can_ho_studio')
        self.assertEqual((placed(s), deco(s)['bag']), ({}, [dict(id='d1', k='be_ca')]))
        s, _ = act(s, 'jr_reno_move', uid='d1', room='living', slot='f2')
        self.assertEqual(placed(s), {'d1': ('be_ca', 'living')})


class Saves(unittest.TestCase):
    def test_older_saves_load_unchanged(self):
        for s in (story(wallet=300), owner(days=3)):
            before = copy.deepcopy(s['journey'])
            s2 = migrate_state(copy.deepcopy(s))
            validate_state(s2)
            self.assertNotIn('reno', s2['journey'])
            self.assertEqual(s2['journey'].get('home'), before.get('home'))

    def test_a_save_with_the_block_round_trips(self):
        s = owner()
        s, _ = act(s, 'jr_reno_buy', item='sofa', room='living', slot='f0', confirm=True)
        block = copy.deepcopy(R(s))
        s2 = migrate_state(copy.deepcopy(s))
        validate_state(s2)
        self.assertEqual(R(s2), block)

    def test_bad_blocks_are_refused(self):
        s = owner()
        s, _ = act(s, 'jr_reno_buy', item='sofa', room='living', slot='f0', confirm=True)
        breaks = [
            lambda r: r.update(v=2),
            lambda r: r.update(extra=1),
            lambda r: r['parts']['wall'].update(c=101),
            lambda r: r['parts']['wall'].update(lv=3),
            lambda r: r['parts'].pop('roof'),
            lambda r: r['items'].append(dict(r['items'][0])),                # the same id twice
            lambda r: r['items'].extend([dict(id='d8', k='tv', r='living', x='f0'), dict(id='d9', k='tv', r='living', x='f0')]),   # one slot, two things
            lambda r: r['items'][0].update(r='living'),                      # a room without a slot
            lambda r: r['items'][0].update(k='Sofa!'),
            lambda r: r['stats'].pop('fixed'),
            lambda r: r.update(day=10**5),
            lambda r: r.update(spent=-1),
        ]
        for i, brk in enumerate(breaks):
            bad = copy.deepcopy(s)
            brk(R(bad))
            with self.subTest(i=i), self.assertRaises(GameError):
                validate_state(bad)

    def test_furniture_from_a_newer_build_survives(self):
        s = owner()
        s, _ = act(s, 'jr_reno_buy', item='sofa', room='living', slot='f0', confirm=True)
        R(s)['items'].append(dict(id='d2', k='ban_bida', r='yard', x='f0'))  # unknown here: kept, not drawn
        validate_state(s)
        self.assertEqual([i['k'] for i in deco(s)['items']], ['sofa'])
        self.assertEqual(deco(s)['bag'], [])
        s, _ = act(s, 'jr_reno_buy', item='tv', room='living', slot='f1', confirm=True)
        self.assertIn('ban_bida', [i['k'] for i in R(s)['items']])

    def test_upgrade_fills_missing_stats_only(self):
        s = owner()
        s, _ = act(s, 'jr_reno_buy', item='sofa', room='living', slot='f0', confirm=True)
        R(s)['stats'].pop('spirit')
        jr.upgrade(s['journey'])
        self.assertEqual(R(s)['stats']['spirit'], 0)
        j = story()['journey']
        jr.upgrade(j)
        self.assertNotIn('reno', j)


if __name__ == '__main__':
    unittest.main()
