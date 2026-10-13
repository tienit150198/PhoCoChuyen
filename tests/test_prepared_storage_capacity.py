"""Owned storage expands prepared buffers, never cooking batches or free refills."""
import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game.careers import cafe_bakery as C, restaurant as R, com as M, pho as P, kit
from game import experiences
from game.content import public_content
from game.engine import GameError, public_state
from tests.helpers import Journey


class PreparedStorageCapacity(unittest.TestCase):
    def shop(self, career, tier=1):
        j = Journey(career)
        j.c['upgrades'].extend(f'warehouse_storage_{career}_{n}' for n in range(1, tier + 1))
        return j

    def test_public_limits_scale_without_filling_any_buffer(self):
        for career, mod, values in [('cafe_bakery', C, {'case_max': 45}),
                                    ('restaurant', R, {'pot_max': 18}),
                                    ('com', M, {'rack_max': 12, 'tray_max': 24})]:
            j = self.shop(career)
            before = copy.deepcopy(j.c)
            p = mod.public_data(j.c)
            self.assertEqual({key: p.get(key) for key in values}, values)
            self.assertEqual(j.c, before)

    def test_cafe_oven_reserves_display_space_before_consuming_ingredients(self):
        j = self.shop('cafe_bakery', 0)
        d = kit.data(j.c)
        d['case'] = [dict(id='test-cookie', item='cookie', qty=20, day=j.c['day'], q='golden', sale=False, cost=1)]
        C._bake(j.state, j.c, d, dict(item='cookie'))
        before = copy.deepcopy(j.c)
        with self.assertRaises(GameError):
            C._bake(j.state, j.c, d, dict(item='cookie'))
        self.assertEqual(j.c, before)

    def test_cafe_bakes_above_old_capacity_and_saves_exact_output(self):
        j = self.shop('cafe_bakery')
        d = kit.data(j.c)
        d['case'] = [dict(id='test-cookie', item='cookie', qty=30, day=j.c['day'], q='golden', sale=False, cost=1)]
        C._bake(j.state, j.c, d, dict(item='cookie'))
        rack = d['oven'][0]
        rack['start'] = kit.now() - 10
        C._unload(j.state, j.c, d, dict(rack=rack['id']))
        self.assertEqual(C._case_count(d, 'cookie'), 38)
        C.validate_data(j.c)

    def test_cafe_reserves_picked_pastries_until_served_or_returned(self):
        j = self.shop('cafe_bakery')
        d = kit.data(j.c)
        d['case'] = [dict(id='test-cookie', item='cookie', qty=30, day=j.c['day'], q='golden', sale=False, cost=1)]
        j.task['bag']['items'] = [dict(item='cookie', day=j.c['day'], q='golden', cost=1) for _ in range(8)]
        before = copy.deepcopy(j.c)
        with self.assertRaises(GameError):
            C._bake(j.state, j.c, d, dict(item='cookie'))
        self.assertEqual(j.c, before)

    def test_cafe_full_display_discard_and_expiry_record_exact_waste(self):
        for expire in (False, True):
            j = self.shop('cafe_bakery', 10)
            d = kit.data(j.c)
            d['case'] = [dict(id='test-cookie', item='cookie', qty=1500, day=1, q='golden', sale=False, cost=10000)]
            if expire:
                j.c['day'] = C.BAKES['cookie']['max_age'] + 1
                C._close_case(j.state, j.c)
            else:
                C._case_action(j.state, j.c, d, 'cb_discard', dict(lot='test-cookie', confirm=True))
            waste = next(w for w in j.c['life']['waste'] if w['item'] == 'cookie')
            self.assertEqual((waste['qty'], waste['value']), (1500, 15_000_000))
            self.assertEqual(d['case'], [])
            experiences.validate(j.c, 'cafe_bakery')

    def test_restaurant_paid_batch_retains_all_broth_above_old_max(self):
        j = self.shop('restaurant')
        d = kit.data(j.c)
        d['pots']['kimchi'] = 12
        d['pot_lots']['kimchi'] = [[12, 0]]
        pack = R.BROTH_INDEX['kimchi']['pack']
        before = kit.stock(j.c, pack)
        R.handle(j.state, j.c, 'rs_pot', dict(broth='kimchi'))
        self.assertEqual(d['pots']['kimchi'], 18)
        self.assertEqual(sum(n for n, _ in d['pot_lots']['kimchi']), 18)
        self.assertEqual(kit.stock(j.c, pack), before - 1)
        with self.assertRaises(GameError):
            R.handle(j.state, j.c, 'rs_pot', dict(broth='kimchi'))
        R.validate_data(j.c)

    def test_com_trays_and_rack_expand_with_original_batch_sizes(self):
        j = self.shop('com')
        d = kit.data(j.c)
        d['trays']['bi']['n'] = 16
        M._tray(j.state, j.c, d, dict(item='bi'))
        self.assertEqual(d['trays']['bi']['n'], 24)
        d['rack'] = [dict(q='ok', c=1) for _ in range(8)]
        d['grill']['lit'] = True
        M._grill(j.state, j.c, d, dict(n=4))
        M._lift(j.state, j.c, d, {})
        self.assertEqual(len(d['rack']), 12)
        with self.assertRaises(GameError):
            M._grill(j.state, j.c, d, dict(n=1))
        with self.assertRaises(GameError):
            M._grill(j.state, j.c, d, dict(n=5))
        M.validate_data(j.c)

    def test_max_tier_prepared_buffers_validate_and_reject_overflow(self):
        for career, mod, key, qty in [('cafe_bakery', C, 'case_max', 1500), ('restaurant', R, 'pot_max', 600), ('com', M, 'tray_max', 800)]:
            j = self.shop(career, 10)
            d = kit.data(j.c)
            if career == 'cafe_bakery':
                d['case'] = [dict(id='test-cookie', item='cookie', qty=qty, day=j.c['day'], q='golden', sale=False, cost=1)]
                row, field = d['case'][0], 'qty'
            elif career == 'restaurant':
                d['pots']['kimchi'] = qty
                d['pot_lots']['kimchi'] = [[qty, 0]]
                row, field = d['pots'], 'kimchi'
            else:
                d['trays']['bi']['n'] = qty
                d['rack'] = [dict(q='ok', c=1) for _ in range(400)]
                row, field = d['trays']['bi'], 'n'
            mod.validate_data(j.c)
            self.assertEqual(mod.public_data(j.c)[key], qty)
            row[field] += 1
            with self.assertRaises(GameError):
                mod.validate_data(j.c)

    def test_pho_free_daily_small_pot_remains_base_amount(self):
        j = self.shop('pho', 10)
        self.assertEqual(kit.data(j.c)['small'], 100)
        self.assertEqual(P.SMALL_MAX, 100)

    @unittest.skipUnless(shutil.which('node'), 'node is needed for prepared storage controls')
    def test_screens_show_and_use_owned_capacity(self):
        states = []
        for career in ('cafe_bakery', 'restaurant', 'com'):
            j = self.shop(career)
            j.act('ask', task=j.task['id'])
            d = kit.data(j.c)
            if career == 'restaurant':
                d['pots']['kimchi'] = 12
                d['pot_lots']['kimchi'] = [[12, 0]]
            if career == 'com':
                d['rack'] = [dict(q='ok', c=1) for _ in range(8)]
                d['grill']['lit'] = True
                d['intro'] = True
            states.append(public_state(j.state))
        script = """
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {careerContext} from './public/js/v4/careers.js';
const {states,content}=JSON.parse(readFileSync(0,'utf8'));
globalThis.document={querySelector:()=>({sheet:{}}),addEventListener:()=>{},documentElement:{hasAttribute:()=>false}};
for(const state of states){
  const mod=(await import(`./public/js/careers/${state.current}.js`)).default;
  const x=careerContext({api:{state,content},ui:{}}),t=x.room.tasks.find(t=>t.id===x.room.active_task);
  x.ui.tabFor=t.id;x.ui.tab='oven';
  const html=state.current==='com'?mod.idle(x):mod.job(t,x);
  if(state.current==='cafe_bakery')assert.ok(html.includes('45 bánh / loại'),'display capacity');
  if(state.current==='com')assert.ok(html.includes('8/12'),'warming rack capacity');
  if(state.current==='restaurant')assert.ok([...html.matchAll(/<button[^>]+>/g)].some(m=>m[0].includes('rs_pot')&&m[0].includes('kimchi')),'can cook into purchased space');
}
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script],
                                input=json.dumps(dict(states=states, content=public_content())),
                                text=True, encoding='utf-8', capture_output=True,
                                cwd=Path(__file__).resolve().parents[1], timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
