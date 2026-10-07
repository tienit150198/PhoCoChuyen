"""1.9.18: Biệt thự Sông Hồng's three-floor inside keeps every piece of the old house where it stood (incident 07/10:
1.9.11 sent 139 pieces of 16 players to the bag, kitchen and second bedroom a row shallower, new windows and a longer
counter over old cells, and the re-settled grid mirror made layout() snap some others to grid cells), a rollback to
1.9.11..1.9.17 never refuses the save (journey.decor_wide), and a move never loses a layout (journey.decor_away)."""
from __future__ import annotations

import copy
import unittest

from game import deco as dc
from game import deco_content as DC
from game import estates as es
from game import journey as jr
from game.engine import validate_state
from tests.test_bank import act
from tests.test_deco import owner, tick
from tests.test_lux import LX, next_day

U = dc.U
OLD = 'own:h1:biet_thu_song'
NEW = OLD + es.V2


def _spots(room: dict, k: str):
    """Every free spot (x, y in steps of U/2) a piece of kind k may take on its own in an empty `room`."""
    z = dc.zone(room, k)
    if z is None:
        return
    for x in range(0, z[0] + 1, U // 2):
        for y in range(0, z[1] + 1, U // 2):
            if not dc.blocked(room, k, x, y):
                yield x, y


def _hosts(room: dict):
    return [f for f in dc.fixtures(room) if dc._ff(f).get('top') or dc._ff(f).get('ledge')]


class Superset(unittest.TestCase):
    def test_every_old_spot_is_still_free_in_the_three_floor_inside(self):
        """For each room the old house had: every kind that suits it, at every spot (floor, wall, rug, and on top of a
        built-in surface such as the counter), placeable in the old room is placeable in the new one."""
        old = {r['id']: r for r in dc.rooms_of(OLD)}
        new = {r['id']: r for r in dc.rooms_of(NEW)}
        self.assertTrue(set(old) <= set(new))
        checked = 0
        for rid, o in old.items():
            n = new[rid]
            self.assertEqual(n['type'], o['type'])
            self.assertGreaterEqual((n['cols'], n['wrows'], n['frows']), (o['cols'], o['wrows'], o['frows']))
            self.assertGreaterEqual(min(n['cols'] - o['cols'], n['wrows'] - o['wrows'], n['frows'] - o['frows']), 0)
            self.assertGreaterEqual(dc.room_cap(n), dc.room_cap(o))
            self.assertGreaterEqual(dc.old_cap(n), dc.old_cap(o))
            kinds = [k for k, it in dc.ITEMS.items() if o['type'] in it['rooms']]
            for k in kinds:
                if dc.ITEMS[k]['spot'] == 'top':
                    continue
                for x, y in _spots(o, k):
                    q = dict(r=rid, x=x, y=y, f=0)
                    self.assertIsNone(dc.check(n, k, q, {}, {}), f'{rid} {k} at {x},{y}')
                    checked += 1
            for f in _hosts(o):   # small things on a built-in surface (the counter, the toilet's cistern)
                h = dc.host_of(o, '#' + f['t'], {}, {})
                hn = dc.host_of(n, '#' + f['t'], {}, {})
                self.assertIsNotNone(hn, f'{rid} #{f["t"]}')
                self.assertGreaterEqual((hn['w'], hn['d'], hn['cap']), (h['w'], h['d'], h['cap']))
                for k in [k for k in kinds if dc.ITEMS[k]['spot'] == 'top']:
                    for x in range(0, max(0, h['w'] - dc.ITEMS[k]['w'] * U) + 1, U // 2):
                        q = dict(r=rid, x=x, y=0, f=0, on='#' + f['t'])
                        if dc.check(o, k, q, {}, {}) is None:
                            self.assertIsNone(dc.check(n, k, q, {}, {}), f'{rid} {k} on #{f["t"]} at {x}')
                            checked += 1
        self.assertGreater(checked, 10000)

    def test_a_spot_of_the_1_9_11_inside_stays_free_too(self):
        """Grown from 1.9.11's rooms (estates.legacy_rooms), never smaller: a layout made since stays, except a small
        thing on the 7th cell of the kitchen counter, which 1.9.11 laid over the old floor beside the counter (the
        fridge's spot in 10 of the 16 kitchens hit on 07/10)."""
        leg = {r['id']: r for r in es.legacy_rooms(NEW)}
        new = {r['id']: r for r in dc.rooms_of(NEW)}
        self.assertEqual([r['id'] for r in es.legacy_rooms(NEW)], list(new))
        for rid, o in leg.items():
            n = new[rid]
            self.assertGreaterEqual((n['cols'], n['wrows'], n['frows']), (o['cols'], o['wrows'], o['frows']))
            for k in [k for k, it in dc.ITEMS.items() if o['type'] in it['rooms'] and it['spot'] != 'top'][:40]:
                for x, y in _spots(o, k):
                    self.assertIsNone(dc.check(n, k, dict(r=rid, x=x, y=y, f=0), {}, {}), f'{rid} {k} at {x},{y}')
        self.assertEqual(dc.host_of(new['kitchen'], '#counter', {}, {})['w'], 6 * U)
        self.assertEqual(dc.host_of(leg['kitchen'], '#counter', {}, {})['w'], 7 * U)
        self.assertIsNone(es.legacy_rooms(OLD))
        self.assertIsNone(es.legacy_rooms('estate:dinh_thu_dao:1'))


# The pieces of the 07/10 incident (uid 877's kitchen and living room, and others'): each one went to the bag in 1.9.11.
INCIDENT = (
    ('lich', dict(r='living', x=66, y=3, f=0)),             # under the living room's wider window
    ('ke_go_treo', dict(r='living', x=115, y=0, f=0)),      # under its new second window
    ('xuong_rong', dict(r='living', x=0, y=0, f=0, on='@1')),   # on that shelf
    ('ban_an', dict(r='kitchen', x=110, y=50, f=0)),        # the kitchen's 4th floor row
    ('gio_trai_cay', dict(r='kitchen', x=2, y=0, f=0, on='@3')),  # on that table
    ('cay_canh', dict(r='kitchen', x=116, y=0, f=0)),       # beside the counter, which grew
    ('ghe_may', dict(r='kitchen', x=123, y=46, f=1)),       # 4th row (1.9.11 snapped it to a grid cell)
    ('o_meo', dict(r='bed2', x=86, y=48, f=0)),             # the second bedroom's 4th row
    ('duong_xi', dict(r='bed', x=140, y=0, f=0)),           # under the bedroom's moved window
    ('noi_com', dict(r='kitchen', x=20, y=0, f=0, on='#counter')),
)


def old_save():
    """A Sông Hồng owner whose layout was saved by a build before 1.9.11 (blocks at the old key, its own rooms)."""
    s = owner('biet_thu_song', wallet=90000)
    uids = []
    for k, _q in INCIDENT:
        s, r = act(s, 'jr_deco_buy', item=k, confirm=True)
        uids.append(r['uid'])
    j = s['journey']
    pos = {}
    for (k, q), u in zip(INCIDENT, uids):
        q = dict(q)
        if q.get('on', '').startswith('@'):
            q['on'] = uids[int(q['on'][1:])]
        pos[u] = q
    d, D = j['deco'], j['decor']
    d['at'] = D['at'] = OLD
    L = dict(place=dict(key=OLD, where='own', kind='biet_thu_song'), rooms=dc.rooms_of(OLD), kinds={u: k for (k, _), u in zip(INCIDENT, uids)},
             order=[it['id'] for it in j['reno']['items']], pos=pos, skins={}, journey=j)
    L['kinds'] = {it['id']: it['k'] for it in j['reno']['items']}
    kept, out = dc.settle_free(L['rooms'], L['kinds'], pos, L['order'])
    assert not out, out   # every piece stands in the old house
    dc._store(d, D, L, kept)   # what a 1.9.10 build writes (no legacy rooms at the old key)
    return s, kept


class Alias(unittest.TestCase):
    def test_an_old_layout_comes_through_at_its_exact_spots(self):
        s, kept = old_save()
        before = dc.layout(s, dict(dc.place(s['journey']), key=OLD))['pos']
        self.assertEqual(before, kept)
        t = copy.deepcopy(s)
        jr.upgrade(t['journey'])
        j = t['journey']
        for name in ('deco', 'decor', 'decor_new', 'decor_more', 'decor_wide'):
            if j.get(name):
                self.assertEqual(j[name]['at'], NEW, name)
        self.assertEqual(dc.sig(j['deco']['pos']), j['decor']['sig'])   # the mirror agrees: layout() never merges
        self.assertEqual(dc.layout(t)['pos'], before)                    # byte-identical positions, nothing in the bag
        validate_state(t)
        # what a 1.9.11..1.9.17 build validates is written for its own (smaller) rooms; the rest rides in decor_wide
        leg = es.legacy_rooms(NEW)
        kinds = {it['id']: it['k'] for it in j['reno']['items']}
        _k, out = dc.settle_free(leg, kinds, j['decor']['items'], list(kinds), dc.old_cap)
        self.assertEqual(out, [])
        _k, out = dc.settle(leg, kinds, {u: tuple(v) for u, v in j['deco']['pos'].items()}, list(kinds))
        self.assertEqual(out, [])
        self.assertTrue(j['decor_wide']['items'])
        self.assertTrue(set(j['decor_wide']['items']) <= set(before))
        # a command keeps it so (the blocks are written again, the same way)
        picked = next(u for u in j['decor']['items'] if not any(q.get('on') == u for q in before.values()))
        t2, _ = act(t, 'jr_deco_pick', uid=picked)
        self.assertEqual(dc.layout(t2)['pos'], {u: q for u, q in before.items() if u != picked})
        self.assertEqual(dc.sig(t2['journey']['deco']['pos']), t2['journey']['decor']['sig'])
        validate_state(t2)
        # idempotent: loading again changes nothing
        u = copy.deepcopy(t)
        jr.upgrade(u['journey'])
        self.assertEqual(u['journey'], t['journey'])

    def test_a_piece_that_cannot_stand_is_logged(self):
        s, kept = old_save()
        uid = next(u for u, q in kept.items() if q['r'] == 'kitchen' and not q.get('on'))
        s['journey']['decor']['items'][uid]['r'] = 'nowhere'   # a spot no build can take (shape is still valid)
        import io
        from contextlib import redirect_stderr
        err = io.StringIO()
        with redirect_stderr(err):
            jr.upgrade(s['journey'])
        self.assertNotIn(uid, dc.layout(s)['pos'])
        self.assertIn(uid, [it['id'] for it in s['journey']['reno']['items']])   # in the bag, never lost


class Moving(unittest.TestCase):
    def test_a_villa_and_back_puts_the_home_layout_back(self):
        """The 07/10 trap: buy a villa, move in, a day passes, sell it: the home's layout came back empty."""
        s, kept = old_save()
        jr.upgrade(s['journey'])
        home = dc.layout(s)['pos']
        skins = {'living': {'w': next(k for k, v in DC.SKINS.items() if v['part'] == 'wall')}}
        s['journey']['decor']['skins'] = copy.deepcopy(skins)
        s['journey']['wallet'] += 400_000
        s, _ = act(s, 'jr_lux_buy', id='bt_vuon_da_lat', confirm=True)
        s, _ = act(s, 'jr_lux_live', id='bt_vuon_da_lat')
        s = next_day(s)                                  # on_life_day follows the player
        self.assertEqual(dc.layout(s)['pos'], {})
        self.assertEqual(s['journey']['decor_away']['places'][-1]['at'], NEW)
        validate_state(s)
        s, _ = act(s, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=40, y=40))   # in the villa
        villa = dc.place(s['journey'])['key']
        self.assertTrue(villa.startswith('estate:'))
        s, _ = act(s, 'jr_lux_sell', id='bt_vuon_da_lat', confirm=True)
        s = next_day(s)
        self.assertEqual(dc.layout(s)['pos'], home)       # every piece where it was
        self.assertEqual(s['journey']['decor']['skins'], skins)
        self.assertEqual([x['at'] for x in s['journey']['decor_away']['places']], [villa])   # the villa's, kept in turn
        validate_state(s)

    def test_the_first_command_after_a_move_keeps_the_layout_too(self):
        s, _ = old_save()
        jr.upgrade(s['journey'])
        home = dc.layout(s)['pos']
        s['journey']['wallet'] += 400_000
        s, _ = act(s, 'jr_lux_buy', id='bt_vuon_da_lat', confirm=True)
        s, _ = act(s, 'jr_lux_live', id='bt_vuon_da_lat')
        s, _ = act(s, 'jr_deco_buy', item='sofa', confirm=True, put=dict(r='living', x=40, y=40))   # no day passed
        self.assertTrue(s['journey']['decor_away'])
        s, _ = act(s, 'jr_lux_live', id=None)
        s, _ = act(s, 'jr_deco_buy', item='cay_canh', confirm=True)   # into the bag: the first command back home
        self.assertEqual({u: q for u, q in dc.layout(s)['pos'].items() if u in home}, home)
        validate_state(s)

    def test_a_piece_sold_while_away_stays_sold(self):
        s, _ = old_save()
        jr.upgrade(s['journey'])
        home = dc.layout(s)['pos']
        gone = next(u for u, q in home.items() if not q.get('on') and not any(v.get('on') == u for v in home.values()))
        s['journey']['wallet'] += 400_000
        s, _ = act(s, 'jr_lux_buy', id='bt_vuon_da_lat', confirm=True)
        s, _ = act(s, 'jr_lux_live', id='bt_vuon_da_lat')
        s = next_day(s)
        s, _ = act(s, 'jr_deco_sell', uid=gone, confirm=True)
        validate_state(s)
        t = copy.deepcopy(s)
        jr.upgrade(t['journey'])   # the next build's load drops it from the kept layout
        self.assertNotIn(gone, t['journey']['decor_away']['places'][0]['items'])
        s, _ = act(s, 'jr_lux_sell', id='bt_vuon_da_lat', confirm=True)
        s = next_day(s)
        self.assertEqual(dc.layout(s)['pos'], {u: q for u, q in home.items() if u != gone})
        self.assertNotIn(gone, [it['id'] for it in s['journey']['reno']['items']])

    def test_kept_layouts_are_capped(self):
        s, _ = old_save()
        j = s['journey']
        j['decor_away'] = dict(v=dc.AWAY_VERSION, places=[dict(at=f'rent:tro_moi:{n}', items={}, skins={'tro': {'w': 'x'}})
                                                            for n in range(dc.AWAY_MAX)])
        validate_state(s)
        j['decor_away']['places'].append(dict(at='attic', items={}, skins={}))
        with self.assertRaises(Exception):
            validate_state(s)


if __name__ == '__main__':
    unittest.main()
