"""↻ Xoay đồ 90° (góp ý #358, #330): a floor piece or a rug turns to four directions. The footprint turns with it
(w × h swap), the server checks the turned footprint against the room's edges and fixtures, and a save from before
(no turn anywhere) loads exactly as it did."""
import copy
import unittest

from game import deco as dc
from game.engine import GameError, validate_state
from tests.test_bank import act
from tests.test_deco import D, owner

U = dc.U


def room(s, rid):
    return next(r for r in dc.layout(s)['rooms'] if r['id'] == rid)


def bought(s, kind, **put):
    s, result = act(s, 'jr_deco_buy', item=kind, confirm=True, put=put)
    return s, result['uid']


def public_item(s, uid):
    return next(i for i in D(s)['items'] if i['id'] == uid)


def every_uid(s):
    return {i['id'] for i in s['journey']['reno']['items']}


def seen(s):
    """What the player can find: placed pieces and pieces in the bag (nothing may vanish)."""
    d = D(s)
    return {i['id'] for i in d['items']} | {b['id'] for b in d['bag']}


class Footprint(unittest.TestCase):
    def test_size_swaps_only_for_a_quarter_turn(self):
        self.assertEqual(dc.size('sofa'), (3, 1))
        self.assertEqual(dc.size('sofa', 1), (1, 3))
        self.assertEqual(dc.size('sofa', 2), (3, 1))
        self.assertEqual(dc.size('sofa', 3), (1, 3))
        self.assertTrue(dc.turns('sofa') and dc.turns('tham') and dc.turns('tv'))
        self.assertFalse(dc.turns('lich'))                    # a wall piece
        self.assertFalse(dc.turns('den_ngu'))                 # a small thing on a table

    def test_turned_zone_and_fixtures_use_the_turned_footprint(self):
        s = owner()
        lv, k = room(s, 'living'), room(s, 'kitchen')
        self.assertEqual(dc.zone(lv, 'sofa'), ((lv['cols'] - 3) * U, (lv['frows'] - 1) * U))
        self.assertEqual(dc.zone(lv, 'sofa', 1), ((lv['cols'] - 1) * U, (lv['frows'] - 3) * U))
        # beside the kitchen door: the long table hits the door, turned it fits; at the counter it is the other way round
        self.assertEqual(dc.blocked(k, 'ban_an', 4 * U, 0), 'door')
        self.assertEqual(dc.blocked(k, 'ban_an', 4 * U, 0, 1), '')
        self.assertEqual(dc.blocked(k, 'ban_an', 3 * U, U), '')
        self.assertEqual(dc.blocked(k, 'ban_an', 3 * U, 0, 1), 'counter')


class Turning(unittest.TestCase):
    def test_an_old_save_has_no_turn_and_looks_the_same(self):
        s = owner()
        s, uid = bought(s, 'sofa', r='living', x=0, y=40)
        self.assertNotIn('rot', dc.layout(s)['pos'][uid])
        self.assertNotIn('rot', public_item(s, uid))
        self.assertNotIn('decor_rot', s['journey'])
        self.assertNotIn('decor_spin', s['journey'])
        self.assertEqual(dc.rot_in(dc.layout(s), uid), 0)

    def test_turn_a_sofa_four_ways_and_back(self):
        s = owner()
        s, uid = bought(s, 'sofa', r='living', x=0, y=0)
        for rot in (1, 2, 3, 0):
            with self.subTest(rot=rot):
                q = {k: v for k, v in dc.layout(s)['pos'][uid].items() if k not in ('rot', 'face')}
                s, result = act(s, 'jr_deco_put', uid=uid, **q, rot=rot)
                self.assertIn('xoay', result['message'])
                pos = dc.layout(s)['pos'][uid]
                self.assertEqual(pos.get('rot', 0), rot)
                self.assertEqual(public_item(s, uid).get('rot', 0), rot)
                self.assertEqual(pos.get('face', 'front'), 'back' if rot == 2 else 'front')   # older pages read `face`
                validate_state(s)
        self.assertNotIn('decor_rot', s['journey'])

    def test_a_turned_piece_is_kept_in_its_zone_and_out_of_fixtures(self):
        s = owner()
        s, uid = bought(s, 'sofa', r='living', x=0, y=0)
        s, _ = act(s, 'jr_deco_put', uid=uid, r='living', x=2 * U, y=2 * U, f=0, rot=1)
        self.assertEqual(dc.layout(s)['pos'][uid]['y'], 0)          # three rows deep in a three-row room: the back row
        before = copy.deepcopy(s)
        with self.assertRaises(GameError):                           # turned, it would stand in the door
            act(s, 'jr_deco_put', uid=uid, r='living', x=6 * U, y=0, f=0, rot=1)
        self.assertEqual(s, before)

    def test_a_turn_only_fit_beside_the_door(self):
        s = owner()
        before = copy.deepcopy(s)
        with self.assertRaises(GameError):
            bought(s, 'ban_an', r='kitchen', x=4 * U, y=0)
        self.assertEqual(s, before)
        s, uid = bought(s, 'ban_an', r='kitchen', x=4 * U, y=0, rot=1)
        self.assertEqual(dc.layout(s)['pos'][uid]['rot'], 1)
        self.assertIn(uid, s['journey']['decor_spin']['items'])      # older builds do not know this spot: it waits there
        validate_state(s)

    def test_turns_are_refused_for_wall_and_top_pieces_and_bad_values(self):
        s = owner()
        s, wall = bought(s, 'lich', r='living', x=0, y=0)
        s, sofa = bought(s, 'sofa', r='living', x=0, y=0)
        before = copy.deepcopy(s)
        for rot in (1, 2, 3):
            with self.subTest(rot=rot), self.assertRaises(GameError):
                act(s, 'jr_deco_put', uid=wall, r='living', x=0, y=0, f=0, rot=rot)
        for rot in (4, -1, 1.5, '1', None, True):
            with self.subTest(rot=rot), self.assertRaises(GameError):
                act(s, 'jr_deco_put', uid=sofa, r='living', x=0, y=0, f=0, rot=rot)
        self.assertEqual(s, before)

    def test_the_turn_travels_to_the_bag_and_back_and_undo_restores_it(self):
        s = owner()
        s, uid = bought(s, 'sofa', r='living', x=0, y=0)
        straight = {k: v for k, v in dc.layout(s)['pos'][uid].items()}
        s, _ = act(s, 'jr_deco_put', uid=uid, r='living', x=0, y=0, f=0, rot=3)
        s, _ = act(s, 'jr_deco_pick', uid=uid)
        self.assertEqual(next(b for b in D(s)['bag'] if b['id'] == uid).get('rot'), 3)
        s, _ = act(s, 'jr_deco_put', uid=uid, r='living', x=U, y=0, f=0)    # no rot: it keeps its own
        self.assertEqual(dc.layout(s)['pos'][uid]['rot'], 3)
        s, _ = act(s, 'jr_deco_layout', set={uid: straight})                 # ↶ Hoàn tác to the straight sofa
        self.assertNotIn('rot', dc.layout(s)['pos'][uid])
        s, _ = act(s, 'jr_deco_layout', set={uid: dict(straight, rot=1)})
        self.assertEqual(dc.layout(s)['pos'][uid]['rot'], 1)
        s, _ = act(s, 'jr_deco_sell', uid=uid, confirm=True)
        self.assertNotIn(uid, (s['journey'].get('decor_rot') or {}).get('items', {}))
        self.assertNotIn(uid, (s['journey'].get('decor_spin') or {}).get('items', {}))
        validate_state(s)

    def test_an_older_page_sending_only_face_keeps_working(self):
        s = owner()
        s, uid = bought(s, 'tv', r='living', x=0, y=40)
        q = dict(dc.layout(s)['pos'][uid])
        s, _ = act(s, 'jr_deco_put', uid=uid, **q, face='back')
        self.assertEqual(dc.layout(s)['pos'][uid].get('rot'), 2)
        q = {k: v for k, v in dc.layout(s)['pos'][uid].items() if k not in ('rot', 'face')}
        s, _ = act(s, 'jr_deco_put', uid=uid, **q, rot=1)
        s, _ = act(s, 'jr_deco_put', uid=uid, **q, face='front')               # front again keeps the side turn
        self.assertEqual(dc.layout(s)['pos'][uid].get('rot'), 1)


class Saves(unittest.TestCase):
    def turned_home(self):
        s = owner()
        s, a = bought(s, 'sofa', r='living', x=0, y=0, rot=1)
        s, b = bought(s, 'ban_an', r='kitchen', x=4 * U, y=0, rot=1)       # only fits turned
        s, c = bought(s, 'tham', r='living', x=2 * U, y=U, rot=1)
        s, d = bought(s, 'tv', r='living', x=4 * U, y=40, rot=2)
        return s, (a, b, c, d)

    def test_turns_survive_validate_and_reload(self):
        s, uids = self.turned_home()
        validate_state(s)
        t = copy.deepcopy(s)
        validate_state(t)
        self.assertEqual({u: dc.layout(t)['pos'][u].get('rot') for u in uids}, {uids[0]: 1, uids[1]: 1, uids[2]: 1, uids[3]: 2})

    def test_an_older_build_loses_nothing(self):
        """An older build drops the keys it does not know: every piece still stands or waits in the bag, unturned."""
        s, uids = self.turned_home()
        t = copy.deepcopy(s)
        t['journey'].pop('decor_rot', None)
        t['journey'].pop('decor_spin', None)
        validate_state(t)
        L = dc.layout(t)
        self.assertTrue(all('rot' not in q or q['rot'] == 2 for q in L['pos'].values()))   # the TV keeps `face` back
        self.assertEqual(seen(t), every_uid(t))
        self.assertNotIn(uids[1], L['pos'])          # the table that only fits turned waits in the bag
        self.assertEqual(seen(s), every_uid(s))

    def test_bad_turn_blocks_are_refused(self):
        s, uids = self.turned_home()
        for bad in (dict(v=2, items={uids[0]: 1}), dict(v=1, items={uids[0]: 0}), dict(v=1, items={uids[0]: 4}),
                    dict(v=1, items={'nope': 1}), dict(v=1, items={}), dict(v=1, items={uids[0]: 1}, x=1),
                    dict(v=1, items={uids[0]: '1'})):
            t = copy.deepcopy(s)
            t['journey']['decor_rot'] = bad
            with self.subTest(bad=bad), self.assertRaises(GameError):
                validate_state(t)
        t = copy.deepcopy(s)
        t['journey']['decor_spin']['v'] = 99
        with self.assertRaises(GameError):
            validate_state(t)


if __name__ == '__main__':
    unittest.main()
