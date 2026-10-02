"""🚗 Xe & phương tiện (game/garage.py): the catalogue and its prices, buying outright (wallet, then the bank account,
never below 0), paint and plate, the vehicle you ride, the daily ride out (capped), selling back, the views, and
saves (old ones without a garage, blocks a newer build wrote)."""
import copy
import unittest

from game import garage as gr
from game import journey as jr
from game import social
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state
from tests.test_bank import B, act, opened, story


def G(s):
    return s['journey']['garage']


def spirit(s):
    return s['journey']['life']['spirit']


def buy(s, vid, **kw):
    return act(s, 'jr_garage_buy', id=vid, confirm=True, **kw)


def refused(test, s, name, code=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, name, **p)
    test.assertEqual(s, before)   # a refusal changes nothing
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


class Catalogue(unittest.TestCase):
    def test_tiers_and_groups(self):
        self.assertEqual({v['group'] for v in gr.VEHICLES.values()}, set(gr.GROUP_IDS))
        for gid in gr.GROUP_IDS:
            prices = [v['price'] for v in gr.VEHICLES.values() if v['group'] == gid]
            self.assertEqual(prices, sorted(prices), gid)   # cheapest first within a tab
        cheapest = min(v['price'] for v in gr.VEHICLES.values())
        self.assertLessEqual(cheapest, jr.START_WALLET + 3 * 50)          # a bicycle within a few days of pay
        self.assertLess(max(v['price'] for v in gr.VEHICLES.values() if v['group'] == 'bike'), 1800)  # < the cheapest home
        for gid in ('boat', 'plane'):                                     # long-term goals
            self.assertGreaterEqual(min(v['price'] for v in gr.VEHICLES.values() if v['group'] == gid), 15000)

    def test_entries(self):
        for vid, v in gr.VEHICLES.items():
            self.assertRegex(vid, gr.ID_RE.pattern)
            self.assertIn(v['paint'], gr.PAINT_INDEX)
            self.assertGreater(v['price'], 0)
            self.assertTrue(1 <= v['spirit'] <= 8 and 0 <= v['fuel'] <= 30, vid)   # a small perk, small fuel
            self.assertLess(v['fuel'] * 20, v['price'], vid)
            self.assertGreater(v['price'], gr.sell_price(v['price']))           # selling back always loses
        for gid in gr.GROUP_IDS:
            self.assertTrue(gr.TRIP_LINES[gid])
        cat = gr.catalogue()
        self.assertEqual([v['id'] for v in cat['vehicles']], list(gr.ORDER))
        self.assertEqual(jr.content()['garage'], cat)


class Buying(unittest.TestCase):
    def test_buy_with_cash(self):
        s = story(500)
        s, r = buy(s, 'xe_dap', color='do', plate='MÂY 01')
        j = s['journey']
        self.assertEqual(j['wallet'], 380)
        self.assertEqual(G(s)['cars'], {'xe_dap': dict(c='do', n='MÂY 01', d=j['life_day'], p=120)})
        self.assertEqual(G(s)['ride'], 'xe_dap')       # the first vehicle is the one you ride
        self.assertEqual(j['history'][-1]['kind'], 'life')
        self.assertEqual(j['history'][-1]['amount'], -120)
        self.assertIn('120 xu tiền mặt', r['message'])
        s, r = buy(s, 'xe_dap_dien')                    # the default paint; the ride stays
        self.assertEqual(G(s)['cars']['xe_dap_dien']['c'], gr.VEHICLES['xe_dap_dien']['paint'])
        self.assertEqual(G(s)['ride'], 'xe_dap')
        validate_state(s)

    def test_not_enough_is_refused_with_the_reason(self):
        s = story(500)
        why = refused(self, s, 'jr_garage_buy', 'not_enough', id='xe_so', confirm=True)
        self.assertIn('Còn thiếu 100 xu', why)
        row = next(m for m in public_state(s)['journey']['garage']['market'] if m['id'] == 'xe_so')
        self.assertEqual(row['why'], 'Còn thiếu 100 xu.')
        self.assertIsNone(next(m for m in public_state(s)['journey']['garage']['market'] if m['id'] == 'xe_dap')['why'])

    def test_debt_buys_nothing_and_the_card_is_never_used(self):
        s = story(-5)
        why = refused(self, s, 'jr_garage_buy', id='xe_dap', confirm=True)
        self.assertIn('Ví đang nợ 5 xu', why)
        s = opened(wallet=1000, deposit=0)
        refused(self, s, 'jr_garage_buy', 'not_enough', id='o_to_mini', confirm=True)

    def test_wallet_then_account_never_below_zero(self):
        s = opened(wallet=3000, deposit=2500)          # 500 cash, 2 500 in the account
        s, r = buy(s, 'o_to_mini')                      # 3 000
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(B(s)['balance'], 0)
        self.assertIn('500 xu tiền mặt và 2.500 xu từ tài khoản', r['message'])
        self.assertEqual(B(s)['log'][-1]['amt'], -2500)
        refused(self, s, 'jr_garage_buy', 'not_enough', id='xe_dap', confirm=True)
        validate_state(s)

    def test_confirm_duplicate_and_bad_input(self):
        s = story(500)
        refused(self, s, 'jr_garage_buy', id='xe_dap')                    # no confirm
        refused(self, s, 'jr_garage_buy', id='tau_vu_tru', confirm=True)  # not sold
        refused(self, s, 'jr_garage_buy', id='xe_dap', color='cau_vong', confirm=True)
        refused(self, s, 'jr_garage_buy', id='xe_dap', plate='X' * (gr.PLATE_MAX + 1), confirm=True)
        refused(self, s, 'jr_garage_buy', id='xe_dap', confirm=True, price=1)
        s, _ = buy(s, 'xe_dap')
        s, r = buy(s, 'xe_dap')                         # a second tap pays nothing
        self.assertTrue(r.get('duplicate'))
        self.assertEqual(s['journey']['wallet'], 380)

    def test_free_play_has_no_garage(self):
        s = new_state()
        self.assertFalse(s['journey']['story'])
        refused(self, s, 'jr_garage_buy', id='xe_dap', confirm=True)


class Owning(unittest.TestCase):
    def setUp(self):
        s = story(2000)
        s, _ = buy(s, 'xe_dap')
        s, _ = buy(s, 'xe_so', color='den')
        self.s = s

    def test_paint_plate_and_ride(self):
        s, r = act(self.s, 'jr_garage_paint', id='xe_so', color='vang', plate='  59-MÂY  ')
        self.assertEqual(G(s)['cars']['xe_so'], dict(c='vang', n='59-MÂY', d=1, p=600))
        self.assertEqual(s['journey']['wallet'], 2000 - 720)   # repainting is free
        s, r = act(s, 'jr_garage_paint', id='xe_so', plate='')
        self.assertEqual(G(s)['cars']['xe_so']['n'], '')
        refused(self, s, 'jr_garage_paint', id='xe_ga', color='do')          # not yours
        s, _ = act(s, 'jr_garage_ride', id='xe_so')
        self.assertEqual(G(s)['ride'], 'xe_so')
        self.assertEqual(public_state(s)['journey']['garage']['ride'], 'xe_so')
        self.assertEqual(social.snapshot(s)[0]['ride'], dict(emoji='🏍️', name='Xe số Cub', color=gr.PAINT_INDEX['vang']['hex']))
        s, _ = act(s, 'jr_garage_ride', id=None)
        self.assertIsNone(G(s)['ride'])
        self.assertNotIn('ride', social.snapshot(s)[0])
        validate_state(s)

    def test_one_ride_out_a_day(self):
        s = self.s
        L = s['journey']['life']
        L['spirit'] = 50
        s, r = act(s, 'jr_garage_trip', id='xe_so')
        self.assertEqual(spirit(s), 53)
        self.assertEqual(s['journey']['wallet'], 2000 - 720 - 2)   # the fuel, shown on the button
        self.assertEqual(r['effects'], ['😊 Tinh thần +3'])
        self.assertEqual(G(s)['trip'], s['journey']['life_day'])
        self.assertTrue(any(line in r['message'] for line in gr.TRIP_LINES['bike']))
        for vid in ('xe_so', 'xe_dap'):                   # capped across every vehicle
            refused(self, s, 'jr_garage_trip', 'already_done', id=vid)
        self.assertTrue(public_state(s)['journey']['garage']['tripped'])
        s['journey']['life_day'] += 1
        s, _ = act(s, 'jr_garage_trip', id='xe_dap')     # a bicycle needs no fuel
        self.assertEqual(spirit(s), 55)
        self.assertEqual(s['journey']['wallet'], 2000 - 720 - 2)
        self.assertEqual(G(s)['stats']['trips'], 2)

    def test_fuel_needs_the_wallet(self):
        s = self.s
        s['journey']['wallet'] = 1
        why = refused(self, s, 'jr_garage_trip', 'not_enough', id='xe_so')
        self.assertIn('2 xu tiền xăng', why)
        car = next(c for c in public_state(s)['journey']['garage']['cars'] if c['id'] == 'xe_so')
        self.assertEqual(car['trip_why'], why)

    def test_sell_back(self):
        s = self.s
        refused(self, s, 'jr_garage_sell', id='xe_dap')   # no confirm
        s, r = act(s, 'jr_garage_sell', id='xe_dap', confirm=True)
        self.assertEqual(s['journey']['wallet'], 2000 - 720 + 80)   # 70 % of 120, rounded down to 10
        self.assertNotIn('xe_dap', G(s)['cars'])
        self.assertIsNone(G(s)['ride'])
        refused(self, s, 'jr_garage_sell', id='xe_dap', confirm=True)
        s, _ = buy(s, 'xe_dap')                               # buy it again at the list price
        self.assertEqual(G(s)['stats'], dict(bought=3, sold=1, trips=0))
        validate_state(s)


class Saves(unittest.TestCase):
    def test_old_save_and_views(self):
        s = story(100)
        self.assertNotIn('garage', s['journey'])
        validate_state(s)
        v = public_state(s)['journey']['garage']
        self.assertEqual((v['cars'], v['ride'], v['tripped']), ([], None, False))
        self.assertEqual(len(v['market']), len(gr.VEHICLES))
        s2 = migrate_state(copy.deepcopy(s))
        self.assertNotIn('garage', s2['journey'])        # absent stays absent

    def test_strict_validation(self):
        s = story(500)
        s, _ = buy(s, 'xe_dap')
        for bad in (lambda g: g.update(v=2), lambda g: g.update(extra=1), lambda g: g.update(ride='xe_so'),
                    lambda g: g['cars']['xe_dap'].update(p=-1), lambda g: g['cars']['xe_dap'].update(n='x' * 20),
                    lambda g: g['cars'].update({'Bad Id': dict(c='do', n='', d=1, p=1)}), lambda g: g.update(trip=-1),
                    lambda g: g['stats'].update(trips='1')):
            t = copy.deepcopy(s)
            bad(G(t))
            with self.assertRaises(GameError):
                validate_state(t)
        t = copy.deepcopy(s)
        t['journey']['garage'] = 'oops'
        with self.assertRaises(GameError):
            validate_state(t)

    def test_newer_build_vehicle_is_kept(self):
        s = story(500)
        s, _ = buy(s, 'xe_dap')
        G(s)['cars']['tau_ngam'] = dict(c='cau_vong', n='', d=1, p=99999)   # a newer build's vehicle and paint
        G(s)['ride'] = 'tau_ngam'
        validate_state(s)
        v = public_state(s)['journey']['garage']
        self.assertEqual([c['id'] for c in v['cars']], ['xe_dap'])
        self.assertNotIn('ride', social.snapshot(s)[0])
        s, _ = act(s, 'jr_garage_ride', id='xe_dap')
        self.assertIn('tau_ngam', G(s)['cars'])           # never dropped

    def test_upgrade_repairs_and_keeps(self):
        s = story(500)
        s, _ = buy(s, 'xe_dap')
        g = G(s)
        g['future'] = True
        g['cars']['xe_so'] = 'broken'
        g['stats']['trips'] = -3
        s = migrate_state(s)
        self.assertEqual(set(G(s)), gr.BLOCK_KEYS)
        self.assertEqual(list(G(s)['cars']), ['xe_dap'])
        self.assertEqual(G(s)['ride'], 'xe_dap')
        self.assertEqual(G(s)['stats']['trips'], 0)
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
