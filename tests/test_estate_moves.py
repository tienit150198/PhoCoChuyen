"""🏰 Feedback 08/10 ("một số biệt thự sao không vào được nhỉ"): living in a villa bought in Mua sắm (game/estates.py),
deco.place puts the villa first, and before this fix no move of game/housing.py (buy and move in, move, rent a room,
the spouse's home) nor game/rentals.py (a player's home) ended it. The house screen then said you lived in the new
home (a Biệt thự Sông Hồng, a Biệt thự Vườn Cau…) while every "Vào nhà" still opened the Mua sắm villa: the new home
could not be entered. Now a move ends living in the villa (it stays owned), the house screen shows the villa while
you live there (where_id 'estate', its điện nước), and "Về nhà cũ" there takes you home."""
from __future__ import annotations

import copy
import unittest

from game import deco as dc
from game import housing as hs
from game.engine import public_state, validate_state
from tests.test_bank import act
from tests.test_lux import LX, next_day, rich


def in_villa(eid='bt_kinh', wallet=6_000_000):
    s = rich(wallet)
    s, _ = act(s, 'jr_lux_buy', id=eid, confirm=True)
    s, _ = act(s, 'jr_lux_live', id=eid)
    return s


def buy(s, kind, move_in=None):
    p = dict(kind=kind, down=hs.HOMES[kind]['price'], confirm=True)
    if move_in is not None:
        p['move_in'] = move_in
    return act(s, 'jr_home_buy', **p)[0]


def where(s):
    return dc.place(s['journey'])


class MovingOutOfAVilla(unittest.TestCase):
    def test_buying_a_villa_and_moving_in_opens_it(self):
        for kind, key in (('biet_thu_song', 'own:h1:biet_thu_song:v2'), ('biet_thu_vuon', 'own:h1:biet_thu_vuon')):
            s = buy(in_villa(), kind, move_in=True)
            self.assertEqual(where(s)['key'], key, kind)   # "Vào nhà" opens the home moved into
            self.assertIsNone(LX(s)['live'])
            self.assertIn('bt_kinh', LX(s)['own'])           # the villa stays owned
            v = public_state(s)['journey']
            self.assertEqual(v['deco']['place']['kind'], kind)
            self.assertEqual(v['home']['place']['where_id'], 'own')
            s = next_day(s)
            self.assertEqual(where(s)['key'], key)
            validate_state(s)

    def test_buying_without_moving_in_keeps_the_villa(self):
        s = buy(in_villa(), 'biet_thu_song', move_in=False)
        self.assertEqual(where(s)['where'], 'estate')
        s = buy(s, 'tap_the')   # no move_in sent: living in a villa, the new home stays empty too
        self.assertEqual(where(s)['where'], 'estate')
        self.assertEqual(len(s['journey']['home']['props']), 2)
        s, _ = act(s, 'jr_lux_live', id=None)   # out of the villa with no home moved into: Bà Tám's attic, homes empty
        self.assertEqual(where(s)['where'], 'attic')

    def test_moving_into_another_home_renting_or_the_spouses_home(self):
        s = buy(in_villa(), 'biet_thu_vuon', move_in=False)
        hid = s['journey']['home']['props'][0]['id']
        t, _ = act(s, 'jr_home_move', id=hid, confirm=True)
        self.assertEqual(where(t)['key'], f'own:{hid}:biet_thu_vuon')
        self.assertIsNone(LX(t)['live'])
        t, _ = act(in_villa(), 'jr_home_rent', kind='tro_moi', confirm=True)
        self.assertEqual(where(t)['where'], 'rent')
        t = in_villa()
        hs.accept_shared(t, dict(couple=7, id='h3', kind='biet_thu_song', name='An', mv=0))   # family.py, on consent
        self.assertEqual(where(t)['key'], 'shared:7:h3:biet_thu_song:v2')
        self.assertIsNone(LX(t)['live'])
        validate_state(t)

    def test_the_house_screen_shows_the_villa_and_the_way_home(self):
        s = buy(in_villa('dinh_thu_dao'), 'biet_thu_song', move_in=True)
        s['journey']['lux']['live'] = 'dinh_thu_dao'   # a save from 1.9.19: moved in, the villa kept first
        validate_state(s)
        self.assertEqual(where(s)['where'], 'estate')
        p = public_state(s)['journey']['home']['place']
        self.assertEqual((p['where_id'], p['name'], p['kind'], p['group']), ('estate', 'Dinh thự đảo Hòn Mây', 'dinh_thu_dao', 'villa'))
        self.assertEqual(p['cost']['rent'], 80)                       # its điện nước, as journey.living_cost charges
        s, _ = act(s, 'jr_lux_live', id=None)                        # "Về nhà cũ" on the house screen
        self.assertEqual(where(s)['key'], 'own:h1:biet_thu_song:v2')
        self.assertEqual(public_state(s)['journey']['home']['place']['where_id'], 'own')

    def test_a_layout_left_behind_comes_back(self):
        s = buy(rich(6_000_000), 'biet_thu_song')
        s, _ = act(s, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=20, y=40))
        s, _ = act(s, 'jr_lux_buy', id='bt_kinh', confirm=True)
        s, _ = act(s, 'jr_lux_live', id='bt_kinh')
        s = next_day(s)
        s = buy(s, 'biet_thu_vuon', move_in=True)                       # out of the villa, into Vườn Cau
        s, _ = act(s, 'jr_lux_live', id='bt_kinh')
        s, _ = act(s, 'jr_lux_live', id=None)                         # back to Vườn Cau, not the villa
        self.assertEqual(where(s)['kind'], 'biet_thu_vuon')
        before = copy.deepcopy(s)
        validate_state(s)
        self.assertEqual(s, before)


if __name__ == '__main__':
    unittest.main()
