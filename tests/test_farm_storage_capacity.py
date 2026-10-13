import copy
import json
import unittest

from game import capacity_progression as cp
from game.careers import farm as farm, farm_plus as fp
from game.engine import GameError, validate_state
from tests.helpers import Journey


class FarmStorageCapacity(unittest.TestCase):
    def farm(self, tier=0):
        j = Journey('farm')
        j.c['upgrades'].extend(cp.item_id('farm', n) for n in range(1, tier + 1))
        return j

    def cold(self, j, qty, rows=1):
        d = j.c['ext']['data']
        d['cold'] = []
        for _ in range(rows):
            farm._add_lot(j.c, d, 'muong', 'A', qty, True, False, 'P1')
        return d

    def garden(self, j):
        fp.handle(j.state, j.c, 'fa_v_open', {})
        return j.c['ext'][fp.KEY]

    def test_public_owned_limits_and_no_refill(self):
        j = self.farm()
        g = self.garden(j)
        before = copy.deepcopy((j.c['ext']['data'], g))
        j.c['upgrades'].append(cp.item_id('farm', 1))
        view = farm.public_data(j.c)
        self.assertEqual(view['cold_cap'], 240)
        self.assertEqual(view['cold_lot_cap'], 45)
        self.assertEqual(view['coop']['nest_cap'], 60)
        self.assertEqual(fp.view(j.c)['store_cap'], 360)
        self.assertEqual((j.c['ext']['data'], g), before)

    def test_harvest_uses_owned_cold_space(self):
        for tier, allowed in ((0, False), (1, True)):
            j = self.farm(tier)
            d = self.cold(j, 160)
            p = d['plots'][0]
            p.update(crop='muong', growth=farm.RIPE, weeds=0, stress=0, pests=0)
            if allowed:
                farm._handle(j.state, j.c, 'fa_harvest', {'plot': p['id'], 'confirm': True})
                self.assertGreater(farm._cold_units(d), 160)
            else:
                before = copy.deepcopy(d)
                with self.assertRaises(GameError):
                    farm._handle(j.state, j.c, 'fa_harvest', {'plot': p['id'], 'confirm': True})
                self.assertEqual(d, before)

    def test_owned_lot_slots_and_save_roundtrip(self):
        j = self.farm(1)
        d = self.cold(j, 1, 44)
        d['coop'].update(nest=50, stale=0)
        farm._handle(j.state, j.c, 'fa_collect', {})
        self.assertEqual(len(d['cold']), 45)
        validate_state(json.loads(json.dumps(j.state)))

    def test_nest_growth_uses_owned_space(self):
        j = self.farm(1)
        coop = j.c['ext']['data']['coop']
        coop.update(nest=40, stale=0, fed=j.c['day'], cleaned=j.c['day'], mood=100)
        laid = farm._hens_night(j.c, coop)
        self.assertEqual(coop['nest'], 40 + laid)
        self.assertEqual(coop['stale'], 40)
        validate_state(json.loads(json.dumps(j.state)))

    def test_packed_produce_reserves_cold_room(self):
        j = self.farm(1)
        d = self.cold(j, 240)
        lot = d['cold'][0]
        task = j.task
        task['needs']['items']['muong'] = 8
        farm._order_action(j.state, j.c, d, task, 'fa_pack', {'lot': lot['id'], 'qty': 8})
        d['coop'].update(nest=1, stale=0)
        with self.assertRaises(GameError):
            farm._handle(j.state, j.c, 'fa_collect', {})
        farm._order_action(j.state, j.c, d, task, 'fa_unpack', {'lot': lot['id']})
        self.assertEqual(farm._cold_units(d), 240)
        self.assertEqual(d['coop']['nest'], 1)

    def test_plus_paid_harvest_and_animals_share_owned_store(self):
        j = self.farm(1)
        g = self.garden(j)
        now = fp._now()
        g['store'] = {'lua': [240, 0]}
        fp._plant(j.state, j.c, g, 0, fp.CROP['ot'], now)
        p = g['plots'][0]
        p['done'] = [k for k, _ in p['needs']]
        fp._harvest(j.state, j.c, g, 0, p['at'] + p['dur'])
        self.assertGreater(fp._store_units(g), 240)
        g['pens']['duck'] = dict(fed=now - 2000, n=0)
        fp.handle(j.state, j.c, 'fa_v_collect', {'animal': 'duck'})
        self.assertIn('trung_vit', g['store'])
        validate_state(json.loads(json.dumps(j.state)))

    def test_full_plus_store_preserves_prepaid_animal_yield(self):
        j = self.farm(1)
        g = self.garden(j)
        g['store'] = {'lua': [360, 0]}
        g['pens']['duck'] = dict(fed=fp._now() - 2000, n=0)
        before = copy.deepcopy(g)
        with self.assertRaises(GameError):
            fp.handle(j.state, j.c, 'fa_v_collect', {'animal': 'duck'})
        self.assertEqual(g, before)
        g['store']['lua'][0] -= 6
        fp.handle(j.state, j.c, 'fa_v_collect', {'animal': 'duck'})
        self.assertEqual(fp._store_units(g), 360)

    def test_top_tier_save_handles_large_egg_lot_and_plus_stock(self):
        j = self.farm(10)
        d = self.cold(j, 1)
        d['coop'].update(nest=2000, stale=0)
        farm._handle(j.state, j.c, 'fa_collect', {})
        g = self.garden(j)
        g['store'] = {'lua': [12000, 0]}
        validate_state(json.loads(json.dumps(j.state)))
        self.assertEqual(farm.public_data(j.c)['cold_cap'], 8000)

    def test_legacy_overfilled_saves_load_but_cannot_take_more(self):
        # Old returns could exceed the runtime total cap. Keep these bounded
        # saves readable; do not destroy produce or manufacture new space.
        j = self.farm()
        d = self.cold(j, 200, 2)
        g = self.garden(j)
        g['store'] = {'lua': [240, 240]}
        validate_state(json.loads(json.dumps(j.state)))
        d['coop'].update(nest=1, stale=0)
        with self.assertRaises(GameError):
            farm._handle(j.state, j.c, 'fa_collect', {})
        g['pens']['duck'] = dict(fed=fp._now() - 2000, n=0)
        with self.assertRaises(GameError):
            fp.handle(j.state, j.c, 'fa_v_collect', {'animal': 'duck'})
        self.assertEqual(farm._cold_units(d), 400)
        self.assertEqual(fp._store_units(g), 480)

    def test_ownership_controls_save_bounds_and_does_not_expand_market(self):
        j = self.farm(1)
        d = self.cold(j, 1)
        d['coop']['nest'] = 61
        with self.assertRaises(GameError):
            farm.validate_data(j.c)
        d['coop']['nest'] = 60
        g = self.garden(j)
        g['store'] = {'lua': [361, 0]}
        with self.assertRaises(GameError):
            fp.validate(j.c)
        g['store'] = {'lua': [360, 0]}
        fp.handle(j.state, j.c, 'fa_v_sell', {'item': 'lua', 'grade': 'A', 'qty': 360})
        self.assertEqual(g['store']['lua'][0], 360 - fp.DEPTH)
        self.assertEqual(len(g['plots']), fp.START_PLOTS)


if __name__ == '__main__':
    unittest.main()
