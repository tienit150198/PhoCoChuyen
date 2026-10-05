"""Spouses may use furniture in their actual common home, with separate possessions and food."""
import copy
import unittest
from unittest.mock import patch

from game import deco as dc, deco_mate as dm, fridge as fr, housing as hs, marriage as mr, relax as rx
from game.engine import GameError, public_state
from tests.test_bank import act
from tests.test_couple import CoupleBase
from tests.test_deco import free
from tests.test_housing import buy


def replace(s, t):
    s.clear()
    s.update(t)


class SharedFurnitureUse(CoupleBase):
    def setUp(self):
        super().setUp()
        self.uids = {}
        def furnish(s):
            s['journey']['wallet'] = 20000
            t, _ = buy(s, 'tap_the')
            for k, room in (('tu_lanh', 'kitchen'), ('bon_tam', 'bath')):
                x, y = free(t, k, room)
                t, result = act(t, 'jr_deco_buy', item=k, confirm=True, room=room, x=x, y=y)
                self.uids[k] = result['uid']
            replace(s, t)
        mr._mutate(self.store, {self.sid(self.a): furnish})
        self.hid = self.state(self.a)['journey']['home']['own']['id']
        mr._mutate(self.store, {self.sid(self.b): lambda s: hs.accept_shared(s, dict(couple=self.cid, id=self.hid, kind='tap_the', name='An'))})

    def command(self, tok, name, rid=None, **payload):
        revision = self.store.read(tok)[1]
        self.store.command(tok, rid or name + '-test', revision, None, name, payload)

    def test_spouse_uses_fridge_and_tub_without_owning_or_changing_them(self):
        b = self.state(self.b)
        owner_before = self.store.read(self.a)
        own_layout = copy.deepcopy(dc.layout(b)['pos'])
        self.assertEqual(fr.spot(b)['cap'], fr.FRIDGE_CAP)
        self.assertEqual(rx.why_not(b, 'ngam'), '')
        view = public_state(b)['journey']['deco']
        self.assertEqual(view['fridge']['cap'], fr.FRIDGE_CAP)
        self.assertTrue(next(x for x in view['relax'] if x['id'] == 'ngam')['ok'])
        mate = dm.view(self.store, self.b, b)
        self.assertEqual(mate['use']['fridge']['cap'], fr.FRIDGE_CAP)
        self.assertTrue(next(x for x in mate['use']['relax'] if x['id'] == 'ngam')['ok'])
        wallet = b['journey']['wallet']
        self.command(self.b, 'jr_fridge_buy', item='sua')
        self.command(self.b, 'jr_relax_do', act='ngam')
        after = self.state(self.b)
        self.assertEqual(after['journey']['wallet'], wallet - fr.FOODS['sua']['price'])
        self.assertEqual(after['journey']['fridge']['items'], {'sua': 1})
        self.assertEqual(after['journey']['relax']['did'], ['ngam'])
        self.assertEqual(dc.layout(after)['pos'], own_layout)
        self.assertFalse(any(u.startswith('p:') for u in dc.layout(after)['kinds']))
        self.assertEqual(self.store.read(self.a), owner_before)
        self.command(self.b, 'jr_fridge_buy', item='sua')  # same request: one purchase
        self.assertEqual(self.state(self.b)['journey']['fridge']['items'], {'sua': 1})
        with self.assertRaises(GameError):
            self.command(self.b, 'jr_deco_pick', uid='p:' + self.uids['tu_lanh'])
        with self.assertRaises(GameError):
            self.command(self.b, 'jr_wd_deco', uid='p:' + self.uids['tu_lanh'], color='goc')

    def test_shared_food_is_personal_and_capacity_uses_both_placed_fridges(self):
        self.command(self.b, 'jr_fridge_buy', item='com_hop')
        self.assertEqual(fr.stock(self.state(self.a)), {})
        self.command(self.a, 'jr_fridge_buy', item='sua')
        self.assertEqual(fr.stock(self.state(self.b)), {'com_hop': 1})
        def add(s):
            x, y = free(s, 'tu_lanh', 'kitchen')
            t, _ = act(s, 'jr_deco_buy', item='tu_lanh', confirm=True, room='kitchen', x=x, y=y)
            replace(s, t)
        mr._mutate(self.store, {self.sid(self.b): add})
        self.assertEqual(fr.spot(self.state(self.a))['cap'], fr.FRIDGE_CAP * fr.FRIDGES_MAX)
        self.assertEqual(fr.spot(self.state(self.b))['cap'], fr.FRIDGE_CAP * fr.FRIDGES_MAX)

    def test_access_ends_immediately_when_owner_packs_the_piece(self):
        self.command(self.a, 'jr_deco_pick', rid='pack-fridge', uid=self.uids['tu_lanh'])
        self.assertEqual(fr.spot(self.state(self.b))['cap'], 0)
        with self.assertRaises(GameError) as err:
            self.command(self.b, 'jr_fridge_buy', item='sua')
        self.assertEqual(err.exception.code, 'no_fridge')
        self.command(self.a, 'jr_deco_pick', rid='pack-tub', uid=self.uids['bon_tam'])
        self.assertEqual(rx.why_not(self.state(self.b), 'ngam'), 'Cần một bồn tắm trong nhà tắm')
        with self.assertRaises(GameError):
            self.command(self.b, 'jr_relax_do', act='ngam')

    def test_apart_or_divorced_never_uses_spouse_furniture(self):
        mr._mutate(self.store, {self.sid(self.b): hs.leave_shared})
        self.assertEqual(fr.spot(self.state(self.b))['cap'], 0)
        self.assertEqual(dm.view(self.store, self.b, self.state(self.b)), {})
        mr._mutate(self.store, {self.sid(self.b): lambda s: hs.accept_shared(s, dict(couple=self.cid, id=self.hid, kind='tap_the', name='An'))})
        self.act(self.a, 'divorce', confirm='LY HON')
        self.assertEqual(fr.spot(self.state(self.b))['cap'], 0)
        self.assertFalse(any(u.startswith('p:') for u in dm.use_layout(self.state(self.b))['pos']))

    def test_bad_relation_wrong_home_and_unavailable_save_fail_closed(self):
        b = self.state(self.b)
        for modify in (lambda s: s['journey']['home']['shared'].update(id='h99'),
                       lambda s: s['marriage']['spouse'].update(couple=self.cid + 1),
                       lambda s: s['marriage']['spouse'].update(status='engaged')):
            t = copy.deepcopy(b)
            modify(t)
            self.assertEqual(fr.spot(t)['cap'], 0)
        with patch.object(mr, '_read_state', side_effect=ValueError('broken')):
            self.assertEqual(fr.spot(b)['cap'], 0)
        with patch.object(mr, 'STORE', None):
            self.assertEqual(fr.spot(b)['cap'], 0)
