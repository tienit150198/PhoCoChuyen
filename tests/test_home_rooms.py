"""🛁 Nhà tắm, 🏊 hồ bơi (1.4.11): the rooms every home gets with no payment (game/deco_content.py KITS, EXTRA_ROOMS),
how they reach the page (deco.public `more` + the catalogue's `kits`, so the save and the per-save state stay small),
their furniture and sets, the shared bathroom of the dorm and the attic, the mark that keeps an older build from
refusing a save with a piece in a new room, and the daily moment at the pool or in the bathtub (game/relax.py)."""
import copy
import json
import unittest

from game import deco as dc
from game import deco_content as DC
from game import estates_content as EC
from game import journey as jr
from game import needs as nd
from game import relax as rx
from game import reno as rn
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import act, story
from tests.test_deco import D, fp, owner, renter

OLD_ROOMS = {   # what 1.4.10 drew for each place (unchanged: the new rooms come after, in `more`)
    'tap_the': ['living', 'bed', 'kitchen'], 'biet_thu_song': ['living', 'bed', 'bed2', 'kitchen', 'yard'],
}


def put_new(s, k, room, x, y, f=0, on=None):
    q = dict(r=room, x=x, y=y)
    if on:
        q['on'] = on
    s, r = act(s, 'jr_deco_buy', item=k, confirm=True, put=q)
    return s, r['uid']


def villa(kind='biet_thu_song'):
    s = owner(kind, wallet=90000)
    s['journey']['life']['spirit'] = 50
    return s


def relax(s):
    return {a['id']: a for a in D(s).get('relax', [])}


class Rooms(unittest.TestCase):
    def test_every_place_has_a_bathroom_and_the_villas_a_pool(self):
        for kind in rn.HOUSES:
            rooms = dc.rooms_of(f'own:h1:{kind}')
            types = [r['type'] for r in rooms]
            with self.subTest(kind=kind):
                self.assertEqual(types[:len(rn.HOUSES[kind]['rooms'])], [row[0] for row in rn.HOUSES[kind]['rooms']])   # the old ones first
                self.assertEqual(types.count('bath'), 1)
                self.assertEqual('pool' in types, kind.startswith('biet_thu'))
                for r in rooms[len(rn.HOUSES[kind]['rooms']):]:
                    self.assertTrue(r['new'] and r['id'] in DC.NEW_ROOMS and r['kit'] in DC.KITS)
        for key in ('attic', 'rent:ky_tuc_xa:3'):
            self.assertEqual([r['type'] for r in dc.rooms_of(key)][-1], 'bathc')
        self.assertEqual([r['type'] for r in dc.rooms_of('rent:tro_moi:3')], ['studio', 'loft', 'bath'])
        big = {r['id']: r['cols'] for r in dc.rooms_of('own:h1:biet_thu_song')}
        self.assertGreater(big['bath'], {r['id']: r['cols'] for r in dc.rooms_of('own:h1:tap_the')}['bath'])

    def test_the_page_gets_them_by_template(self):
        s = owner('biet_thu_song', wallet=90000)
        v = D(s)
        # 🏰 Sông Hồng's three floors (game/estates_content.py SONG_HONG_V2): every room it had, bigger, and more
        self.assertEqual([r['id'] for r in v['rooms']], [r[0] for r in EC.SONG_HONG_V2['rooms']])
        self.assertLessEqual(set(OLD_ROOMS['biet_thu_song']), {r['id'] for r in v['rooms']})
        self.assertEqual(v['more'], [{'t': 'bath_xl', 'fl': 2}, {'t': 'pool_l', 'fl': 1}])
        kits = jr.content()['deco']['kits']
        self.assertEqual(set(kits), set(DC.KITS))
        self.assertEqual(kits['pool_l']['type'], 'pool')
        self.assertEqual({f['t'] for f in kits['bath_s']['fix']}, {'shower', 'window', 'toilet', 'door'})
        self.assertEqual(set(kits['bath_s']), set(v['rooms'][0]) - {'skin', 'fl', 'skin0'})   # the same shape as a room (🏰 + its floor, its look)
        self.assertNotIn('decor', s['journey'])                                         # nothing written by looking
        s2 = story()
        self.assertEqual(D(s2)['more'], [{'t': 'bathc'}])

    def test_furniture_for_the_new_rooms(self):
        for k in ('bon_tam', 'buong_tam', 'bon_rua', 'guong_tam', 'ke_khan', 'ke_tam', 'gio_do_tam', 'tham_tam', 'vit_cao_su',
                  'ghe_tam_nang', 'du_che', 'phao', 'lo_nuong', 'cay_dua', 'den_vuon'):
            it = DC.ITEMS[k]
            self.assertTrue(10 <= it['price'] <= 300 and it['cat'] in ('bath', 'pool'), k)
        self.assertIn('bath', DC.ITEMS['may_giat']['rooms'])
        self.assertIn('pool', DC.ITEMS['ban_ngoai']['rooms'])
        self.assertNotIn('bon_tam', [k for k, it in DC.ITEMS.items() if 'bathc' in it['rooms']])   # the shared one: only small things
        self.assertEqual(sorted(k for k, it in DC.ITEMS.items() if 'bathc' in it['rooms']), ['coc_ban_chai', 'gio_do_tam', 'may_say_toc', 'nen_thom', 'tham_tam', 'vit_cao_su'])   # nến thơm: after 1.4.19; cốc bàn chải, máy sấy: after 1.7.15

    def test_a_bathroom_set_up_and_the_spa_set(self):
        s = owner('tap_the')
        cash = s['journey']['wallet']
        s, tub = put_new(s, 'bon_tam', 'bath', 0, 20)
        s, towel = put_new(s, 'ke_khan', 'bath', 20, 20)
        s, plant = put_new(s, 'cay_luoi_ho', 'bath', 60, 40)
        s, cactus = put_new(s, 'xuong_rong', 'bath', 0, 0, on='#toilet')               # on the cistern
        self.assertEqual(fp(s, cactus)[4], '#toilet')
        self.assertEqual(s['journey']['wallet'], cash - 300 - 40 - 50 - 15)
        done = {x['id'] for x in D(s)['sets'] if x['done']}
        self.assertIn('spa', done)
        with self.assertRaises(GameError):                                              # a sofa does not go in a bathroom
            put_new(s, 'sofa', 'bath', 0, 20)
        with self.assertRaises(GameError):                                              # nor over the toilet
            put_new(s, 'ghe_dau', 'bath', 40, 0)
        validate_state(s)

    def test_the_pool_deck(self):
        s = villa()
        s, chair = put_new(s, 'ghe_tam_nang', 'pool', 0, 60)
        s, umb = put_new(s, 'du_che', 'pool', 160, 0)
        s, ring = put_new(s, 'phao', 'pool', 60, 25)                                    # a float on the water
        self.assertEqual(fp(s, ring)[:3], ('pool', 60, 25))
        with self.assertRaises(GameError):                                              # a grill does not float
            put_new(s, 'lo_nuong', 'pool', 60, 25)
        self.assertIn('resort', {x['id'] for x in D(s)['sets'] if x['done']})
        with self.assertRaises(GameError):                                              # the deck stays as built
            act(s, 'jr_deco_skin', r='pool', part='floor', skin='go_sang')
        s, _ = act(s, 'jr_deco_skin', r='bath', part='wall', skin='bac_ha')             # the bathroom takes paint
        self.assertEqual(D(s)['more'][0], {'t': 'bath_xl', 's': {'w': 'bac_ha'}, 'fl': 2})   # 🏰 Sông Hồng: on the 2nd floor
        validate_state(s)

    def test_the_shared_bathroom(self):
        for s in (story(wallet=500), renter('ky_tuc_xa')):
            s, basket = put_new(s, 'gio_do_tam', 'bath', 0, 0, on='#shelf')             # your basket on the shared shelf
            self.assertEqual(fp(s, basket)[4], '#shelf')
            with self.assertRaises(GameError):
                put_new(s, 'cay_canh', 'bath', 0, 20)
            with self.assertRaises(GameError):
                act(s, 'jr_deco_skin', r='bath', part='wall', skin='bac_ha')
            self.assertNotIn('relax', D(s))
            self.assertFalse(any(x['room'] == 'bath' for x in D(s)['sets']))             # no set to chase there
            validate_state(s)


class OlderBuilds(unittest.TestCase):
    """The pieces in a new room live in journey.decor_new: a build from before 1.4.11 checks every piece of journey.decor
    against the rooms it knows (and would refuse the save), and ignores an extra journey key. There, those pieces wait in
    its bag; the rest of the home looks exactly as here."""

    def old_build_check(self, s):
        """What 1.4.10 checks: journey.decor holds no piece in a room it does not know; the 1.3.2 copy neither."""
        j = s['journey']
        old = {r['id'] for r in dc.rooms_of(dc.place(j)['key']) if not r.get('new')}
        self.assertTrue(all(v['r'] in old for v in j['decor']['items'].values()))
        self.assertTrue(all(v[0] in old for v in j['deco']['pos'].values()))

    def test_the_new_rooms_pieces_are_kept_apart(self):
        s = owner('tap_the')
        s, sofa = put_new(s, 'sofa', 'living', 0, 20)
        self.assertNotIn('decor_new', s['journey'])                                     # nothing in a new room: as before
        s, tub = put_new(s, 'bon_tam', 'bath', 0, 20)
        s, duck = put_new(s, 'vit_cao_su', 'bath', 10, 0, on=tub)
        j = s['journey']
        key = dc.place(j)['key']
        self.assertEqual(j['decor_new'], dict(v=1, at=key, items={tub: dict(r='bath', x=0, y=20, f=0), duck: dict(r='bath', x=10, y=0, f=0, on=tub, z=1)}))
        self.assertEqual(set(j['decor']['items']), {sofa})
        self.old_build_check(s)
        s2 = migrate_state(copy.deepcopy(s))                                             # this build reads it back as it was
        validate_state(s2)
        self.assertEqual(fp(s2, tub)[:3], ('bath', 0, 20))
        self.assertEqual(fp(s2, duck)[4], tub)
        with self.assertRaises(GameError):                                              # a tub in the living room? no
            act(s, 'jr_deco_put', uid=tub, r='living', x=0, y=40)
        s, plant = put_new(s, 'cay_canh', 'bath', 100, 40)
        s, _ = act(s, 'jr_deco_put', uid=plant, r='living', x=40, y=0)                   # a plant moves to the living room
        self.assertEqual(set(s['journey']['decor_new']['items']), {tub, duck})
        self.assertIn(plant, s['journey']['decor']['items'])
        self.old_build_check(s)
        s, _ = act(s, 'jr_deco_pick', uid=tub)                                          # the duck rides along into the bag
        self.assertNotIn('decor_new', s['journey'])
        self.assertEqual(fp(s, sofa)[:3], ('living', 0, 20))
        validate_state(s)

    def test_an_older_build_played_a_day(self):
        s = owner('tap_the')
        s, sofa = put_new(s, 'sofa', 'living', 0, 20)
        s, tub = put_new(s, 'bon_tam', 'bath', 0, 20)
        s, plant = put_new(s, 'cay_canh', 'bath', 100, 40)
        # 1.4.10: the tub and the plant are in its bag; the player sells the tub and puts the plant in the living room
        old = copy.deepcopy(s)
        j = old['journey']
        j['reno']['items'] = [it for it in j['reno']['items'] if it['id'] != tub]
        j['decor']['items'][plant] = dict(r='living', x=0, y=0, f=0)
        back = migrate_state(old)
        validate_state(back)
        self.assertEqual(fp(back, sofa)[:3], ('living', 0, 20))
        self.assertEqual(fp(back, plant)[:3], ('living', 0, 0))                         # its spot there wins
        self.assertIsNone(fp(back, tub))
        self.assertNotIn('decor_new', back['journey'])

    def test_bad_blocks_are_refused(self):
        s = owner('tap_the')
        s, tub = put_new(s, 'bon_tam', 'bath', 0, 20)
        for bad in (lambda X, j: X.update(v=2), lambda X, j: X.update(items={}), lambda X, j: X['items'][tub].update(r='living'),
                    lambda X, j: X['items'].update(zz=dict(r='bath', x=0, y=0, f=0)), lambda X, j: X['items'][tub].update(x=-1),
                    lambda X, j: X.pop('at'), lambda X, j: j['decor']['items'].update({tub: dict(r='bath', x=0, y=20, f=0)})):
            s2 = copy.deepcopy(s)
            bad(s2['journey']['decor_new'], s2['journey'])
            with self.assertRaises(GameError):
                validate_state(s2)

    def test_moving_puts_the_bathroom_in_the_bag_too(self):
        from game import housing as hs
        from tests.test_deco import tick
        s = owner('tap_the')
        s, tub = put_new(s, 'bon_tam', 'bath', 0, 20)
        s, _ = act(s, 'jr_home_sell', confirm=True, value=hs.value_of(s['journey']['home']['own'], s['journey']['life_day']))
        tick(s)
        self.assertIn('bon_tam', [b['k'] for b in D(s)['bag']])
        self.assertNotIn('decor_new', s['journey'])


class Relax(unittest.TestCase):
    def test_only_where_there_is_a_pool_or_your_bathroom(self):
        self.assertNotIn('relax', D(story()))
        self.assertNotIn('relax', D(renter()))
        s = owner('tap_the')
        self.assertEqual(list(relax(s)), ['ngam'])
        self.assertEqual(relax(s)['ngam']['why'], 'Cần một bồn tắm trong nhà tắm')
        with self.assertRaises(GameError) as e:
            act(s, 'jr_relax_do', act='ngam')
        self.assertEqual(e.exception.code, 'not_here')
        with self.assertRaises(GameError) as e:
            act(s, 'jr_relax_do', act='boi')
        self.assertEqual(e.exception.code, 'not_here')
        self.assertEqual(list(relax(villa())), ['boi', 'nam', 'ngam'])

    def test_a_swim_once_a_day_free(self):
        s = villa()
        cash, spirit = s['journey']['wallet'], s['journey']['life']['spirit']
        self.assertTrue(relax(s)['boi']['ok'])
        s, r = act(s, 'jr_relax_do', act='boi')
        self.assertIn('tinh thần +3', r['message'])
        self.assertEqual(s['journey']['life']['spirit'], spirit + 3)
        self.assertEqual(s['journey']['wallet'], cash)                                   # never xu
        self.assertEqual(s['journey']['relax'], dict(v=1, day=s['journey']['life_day'], did=['boi'], n=1))
        v = relax(s)
        self.assertTrue(v['boi']['done'])
        self.assertFalse(v['nam']['ok'])                                                # one moment by the pool a day
        for a in ('boi', 'nam'):
            with self.assertRaises(GameError) as e:
                act(s, 'jr_relax_do', act=a)
            self.assertEqual(e.exception.code, 'already_done')
        from tests.test_deco import tick
        tick(s)
        self.assertTrue(relax(s)['nam']['ok'])
        s, r = act(s, 'jr_relax_do', act='nam')
        self.assertEqual(s['journey']['relax']['n'], 2)
        validate_state(s)

    def test_a_swim_follows_the_needs(self):
        s = villa()
        n = nd.ensure(s)
        n['full'], n['wake'] = nd.LOW - 1, 80
        self.assertEqual(relax(s)['boi']['why'], 'Bụng đói, ăn chút gì đã')
        with self.assertRaises(GameError) as e:
            act(s, 'jr_relax_do', act='boi')
        self.assertEqual(e.exception.code, 'too_hungry')
        n['full'], n['wake'] = 80, nd.LOW - 1
        with self.assertRaises(GameError) as e:
            act(s, 'jr_relax_do', act='boi')
        self.assertEqual(e.exception.code, 'too_sleepy')
        self.assertTrue(relax(s)['nam']['ok'])                                           # lying in the sun is always fine
        n['wake'] = 60
        s, r = act(s, 'jr_relax_do', act='boi')
        self.assertEqual((s['journey']['needs']['full'], s['journey']['needs']['wake']), (80 + rx.SWIM_FULL, 60 + rx.SWIM_WAKE))

    def test_a_soak_needs_a_tub_in_the_bathroom(self):
        s = owner('can_ho_1pn')
        s['journey']['life']['spirit'] = 40
        s, tub = put_new(s, 'bon_tam', 'bath', 0, 20)
        self.assertTrue(relax(s)['ngam']['ok'])
        s, r = act(s, 'jr_relax_do', act='ngam')
        self.assertEqual(s['journey']['life']['spirit'], 42)
        self.assertTrue(r['message'].startswith('🛁 '))
        with self.assertRaises(GameError):
            act(s, 'jr_relax_do', act='ngam')

    def test_bad_payloads_and_saves(self):
        s = villa()
        for p in ({}, {'act': 'lan'}, {'act': 'boi', 'x': 1}):
            with self.assertRaises(GameError):
                act(s, 'jr_relax_do', **p)
        s, _ = act(s, 'jr_relax_do', act='nam')
        for bad in (lambda r: r.update(v=2), lambda r: r.update(did=['nam', 'nam']), lambda r: r.update(did=['xx']),
                    lambda r: r.update(n=-1), lambda r: r.update(day=10**7), lambda r: r.pop('n')):
            s2 = copy.deepcopy(s)
            bad(s2['journey']['relax'])
            with self.assertRaises(GameError):
                validate_state(s2)
        plain = story()
        jr.upgrade(plain['journey'])
        self.assertNotIn('relax', plain['journey'])                                      # older saves load unchanged
        validate_state(plain)

    def test_story_only(self):
        from game.engine import new_state
        s = new_state()
        with self.assertRaises(GameError):
            act(s, 'jr_relax_do', act='boi')

    def test_small_state(self):
        s = villa()
        v = D(s)
        self.assertLess(len(json.dumps(v.get('relax'), ensure_ascii=False)) + len(json.dumps(v['more'])), 600)


if __name__ == '__main__':
    unittest.main()
