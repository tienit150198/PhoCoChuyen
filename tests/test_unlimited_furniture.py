"""Furniture ownership, colours and shared views must not truncate a player's belongings."""
import copy
import json
import unittest

from game import deco as dc, deco_mate as dm, reno as rn, wardrobe as wd
from game.engine import GameError, migrate_state, validate_state
from tests.test_bank import act
from tests.test_deco import D, owner


def stocked(n, kind='lich'):
    s = owner('biet_thu_song', wallet=100000)
    r = rn.ensure_block(s)
    r['items'] = [dict(id=f'd{i + 1}', k=kind, r=None, x=None) for i in range(n)]
    r['seq'] = n
    return s


def filled(n):
    """A valid free layout across several rooms; per-room geometry still limits placement."""
    s = stocked(n)
    d, free, L = dc._ensure(s)
    pos, remaining = {}, iter(L['order'])
    for rm in L['rooms']:
        if rm['type'] not in dc.ITEMS['lich']['rooms']:
            continue
        zone = dc.zone(rm, 'lich')
        xy = next(((x, y) for y in range(zone[1] + 1) for x in range(zone[0] + 1)
                   if not dc.check(rm, 'lich', dict(r=rm['id'], x=x, y=y, f=0), {}, L['kinds'])), None)
        if xy is None:
            continue
        for _ in range(dc.room_cap(rm)):
            uid = next(remaining, None)
            if uid is None:
                dc._store(d, free, L, pos)
                return s
            pos[uid] = dict(r=rm['id'], x=xy[0], y=xy[1], f=0)
    raise AssertionError('Not enough geometric room capacity for this fixture')


class UnlimitedFurniture(unittest.TestCase):
    def test_buy_beyond_sixty_and_nonce_is_still_idempotent(self):
        for n in (60, 121, 1000):
            with self.subTest(n=n):
                s = stocked(n)
                before = copy.deepcopy(s)
                t, result = act(s, 'jr_deco_buy', item='lich', confirm=True, n='large-bag')
                self.assertEqual(s, before)
                self.assertEqual(len(rn.get(t)['items']), n + 1)
                self.assertEqual(t['journey']['wallet'], s['journey']['wallet'] - dc.ITEMS['lich']['price'])
                again, repeat = act(t, 'jr_deco_buy', item='lich', confirm=True, n='large-bag')
                self.assertTrue(repeat['duplicate'])
                self.assertEqual(again, t)
                self.assertEqual(result['uid'], f'd{n + 1}')
                self.assertIsNone(D(t)['max'])

    def test_lifetime_uid_sequence_has_no_million_purchase_ceiling(self):
        s = stocked(1)
        rn.get(s)['seq'] = 10**6
        t, result = act(s, 'jr_deco_buy', item='lich', confirm=True)
        self.assertEqual(result['uid'], 'd1000001')
        validate_state(t)

    def test_large_inventory_survives_json_and_migration(self):
        s = stocked(1000)
        validate_state(s)
        t = json.loads(json.dumps(s))
        t = migrate_state(t)
        validate_state(t)
        self.assertEqual(rn.get(t)['items'], rn.get(s)['items'])
        self.assertEqual(len(D(t)['bag']), 1000)
        self.assertIsNone(rn.catalogue()['items_max'])

    def test_palette_repair_retains_every_valid_owned_colour(self):
        s = stocked(121)
        s['colors'] = dict(v=wd.PAL_VERSION, have=['hong'], wear={}, deco={f'd{i + 1}': 'hong' for i in range(121)})
        s['colors']['deco'][''] = 'hong'  # triggers repair, not truncation
        s['colors']['deco']['sold'] = 'hong'
        s = migrate_state(s)
        validate_state(s)
        self.assertEqual(s['colors']['deco'], {f'd{i + 1}': 'hong' for i in range(121)})
        s = stocked(122)
        s['colors'] = dict(v=wd.PAL_VERSION, have=['hong'], wear={}, deco={f'd{i + 1}': 'hong' for i in range(121)})
        t, _ = act(s, 'jr_wd_deco', uid='d122', color='hong')
        self.assertEqual(len(t['colors']['deco']), 122)

    def test_many_placed_pieces_and_pick_all_undo_are_lossless(self):
        s = filled(121)
        validate_state(s)
        before = copy.deepcopy(dc.layout(s)['pos'])
        t, _ = act(s, 'jr_deco_pick', uid='all')
        self.assertEqual(len(D(t)['bag']), 121)
        t, _ = act(t, 'jr_deco_layout', set=before)
        self.assertEqual(dc.layout(t)['pos'], before)
        validate_state(t)

    def test_spouse_view_does_not_stop_at_120(self):
        s = filled(121)
        s['colors'] = dict(v=wd.PAL_VERSION, have=['hong'], wear={}, deco={f'd{i + 1}': 'hong' for i in range(121)})
        before = copy.deepcopy(s)
        pieces = dm.pieces(s, {r['id'] for r in dc.layout(s)['rooms']})
        self.assertEqual(len(pieces), 121)
        self.assertEqual({p['id'] for p in pieces}, {f'p:d{i + 1}' for i in range(121)})
        self.assertTrue(all(p['c'] == 'hong' for p in pieces))
        self.assertEqual(s, before)

    def test_forward_compatible_layout_shape_has_no_global_cardinality_cap(self):
        for block in ('deco', 'decor', 'decor_new'):
            with self.subTest(block=block):
                s = stocked(121, 'future_furniture')
                at = dc.place(s['journey'])['key']
                if block == 'deco':
                    s['journey'][block] = dc.blank(s['journey']['life_day'], at)
                    s['journey'][block]['pos'] = {f'd{i + 1}': ['living', 0, 0, 0] for i in range(121)}
                else:
                    s['journey'][block] = dc.blank_free(at) if block == 'decor' else dict(v=dc.NEW_VERSION, at=at, items={})
                    s['journey'][block]['items'] = {f'd{i + 1}': dict(r='living', x=0, y=0, f=0) for i in range(121)}
                validate_state(s)

    def test_large_inventory_keeps_identity_and_sequence_checks(self):
        s = stocked(121)
        for break_it in (lambda r: r.update(seq=True), lambda r: r.update(seq=-1),
                         lambda r: r['items'].append(copy.deepcopy(r['items'][0]))):
            t = copy.deepcopy(s)
            break_it(rn.get(t))
            with self.assertRaises(GameError):
                validate_state(t)


class FurnitureFacing(unittest.TestCase):
    def placed_tv(self):
        s = owner()
        s, result = act(s, 'jr_deco_buy', item='tv', confirm=True, put=dict(r='living', x=0, y=40))
        return s, result['uid']

    def test_front_back_is_independent_of_mirroring_and_persists(self):
        s, uid = self.placed_tv()
        q = dc.layout(s)['pos'][uid]
        t, _ = act(s, 'jr_deco_put', uid=uid, **q, face='back')
        self.assertEqual(dc.layout(t)['pos'][uid]['face'], 'back')
        q = {**q, 'f': 1, 'x': 10}
        t, _ = act(t, 'jr_deco_put', uid=uid, **q)
        self.assertEqual(dc.layout(t)['pos'][uid]['face'], 'back')
        self.assertEqual(dc.layout(t)['pos'][uid]['f'], 1)
        self.assertEqual(D(t)['items'][0]['face'], 'back')
        self.assertNotIn('face', t['journey']['decor']['items'][uid])
        self.assertEqual(len(t['journey']['deco']['pos'][uid]), 4)
        restored = json.loads(json.dumps(t))
        restored = migrate_state(restored)
        validate_state(restored)
        self.assertEqual(dc.layout(restored)['pos'][uid]['face'], 'back')
        pieces = dm.pieces(restored, {'living'})
        self.assertEqual(pieces[0]['face'], 'back')

    def test_bag_and_undo_retain_facing_and_sale_prunes_it(self):
        s, uid = self.placed_tv()
        front = dc.layout(s)['pos'][uid]
        s, _ = act(s, 'jr_deco_put', uid=uid, **front, face='back')
        back = dc.layout(s)['pos'][uid]
        s, _ = act(s, 'jr_deco_pick', uid=uid)
        self.assertEqual(D(s)['bag'][0]['face'], 'back')
        s, _ = act(s, 'jr_deco_put', uid=uid, **front)
        self.assertEqual(dc.layout(s)['pos'][uid]['face'], 'back')
        s, _ = act(s, 'jr_deco_layout', set={uid: front})
        self.assertNotIn('face', dc.layout(s)['pos'][uid])
        s, _ = act(s, 'jr_deco_layout', set={uid: back})
        self.assertEqual(dc.layout(s)['pos'][uid]['face'], 'back')
        s, _ = act(s, 'jr_deco_sell', uid=uid, confirm=True)
        self.assertNotIn(uid, s['journey'].get('decor_faces', {}).get('items', {}))
        validate_state(s)

    def test_invalid_or_unsupported_facing_refuses_without_mutating(self):
        s, uid = self.placed_tv()
        before = copy.deepcopy(s)
        for face in ('side', 1, None, {}, []):
            with self.subTest(face=face), self.assertRaises(GameError):
                act(s, 'jr_deco_put', uid=uid, **dc.layout(s)['pos'][uid], face=face)
        self.assertEqual(s, before)
        s, result = act(s, 'jr_deco_buy', item='lich', confirm=True)
        with self.assertRaises(GameError):
            act(s, 'jr_deco_put', uid=result['uid'], r='living', x=0, y=0, face='back')

    def test_facing_save_is_strict_and_owned(self):
        s, uid = self.placed_tv()
        s['journey']['decor_faces'] = dict(v=1, items={uid: 'back'})
        validate_state(s)
        for value in (dict(v=2, items={uid: 'back'}), dict(v=1, items={uid: 'side'}),
                      dict(v=1, items={'p:' + uid: 'back'}), dict(v=1, items={uid: 'back'}, extra=1)):
            t = copy.deepcopy(s)
            t['journey']['decor_faces'] = value
            with self.assertRaises(GameError):
                validate_state(t)
        self.assertEqual(set(dc.catalogue()['facing']), {'tv', 'sofa'})

    def test_explicit_front_and_new_back_purchase_are_idempotent(self):
        for kind in ('tv', 'sofa'):
            with self.subTest(kind=kind):
                s = owner()
                s, result = act(s, 'jr_deco_buy', item=kind, confirm=True,
                                put=dict(r='living', x=0, y=40, face='back'), n='back-purchase')
                uid = result['uid']
                self.assertEqual(dc.layout(s)['pos'][uid]['face'], 'back')
                q = dict(dc.layout(s)['pos'][uid], face='front')
                s, _ = act(s, 'jr_deco_put', uid=uid, **q)
                self.assertNotIn('face', dc.layout(s)['pos'][uid])
                again, result = act(s, 'jr_deco_put', uid=uid, **q)
                self.assertTrue(result['duplicate'])
                self.assertEqual(again, s)

    def test_older_grid_commands_keep_the_bag_pieces_saved_facing(self):
        s, uid = self.placed_tv()
        q = dc.layout(s)['pos'][uid]
        s, _ = act(s, 'jr_deco_put', uid=uid, **q, face='back')
        s, _ = act(s, 'jr_deco_pick', uid=uid)
        s, _ = act(s, 'jr_deco_place', uid=uid, room='living', x=0, y=2, f=1)
        self.assertEqual(dc.layout(s)['pos'][uid]['face'], 'back')
        s, _ = act(s, 'jr_deco_pick', uid=uid)
        s, _ = act(s, 'jr_deco_layout', set={uid: ['living', 0, 2, 0]})
        self.assertEqual(dc.layout(s)['pos'][uid]['face'], 'back')
