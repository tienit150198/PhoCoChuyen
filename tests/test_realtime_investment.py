"""Shared wall-clock quotes and one-time conversion of legacy Mây holdings."""
import copy
import json
import unittest
from unittest.mock import patch

from game import invest as iv, vang
from game.engine import GameError, validate_state
from tests.test_invest import state, act, days, inv


class SharedMarket(unittest.TestCase):
    def setUp(self):
        from game import realtime_market as rm
        self.rm = rm
        self.clock = patch.object(rm, 'now', return_value=rm.EPOCH + 6000)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_players_share_prices_despite_seed_and_life_day(self):
        a, b = state(seed=7), state(seed=83)
        b['journey']['life_day'] = 100
        self.assertEqual(iv.public(a)['coin']['price'], iv.public(b)['coin']['price'])

    def test_public_projects_legacy_units_without_mutation(self):
        s = state()
        inv(s).update(price=23879, prices=[22103, 23879])
        inv(s)['coin'].update(units=1500, basis=307, fees=9, realised=-17, trades=3)
        before = copy.deepcopy(s)
        c = iv.public(s)['coin']
        self.assertEqual(c['units'], 1500 * 23879 // iv.BASE)
        self.assertEqual(s, before)

    def test_conversion_is_once_and_login_delay_keeps_market_change(self):
        s = state()
        inv(s).update(price=23879, prices=[22103, 23879])
        inv(s)['coin'].update(units=1500, basis=307, fees=9, realised=-17, trades=3)
        old = copy.deepcopy(inv(s)['coin'])
        early, late = copy.deepcopy(s), copy.deepcopy(s)
        self.now.return_value = self.rm.EPOCH
        iv.on_life_day(early)
        expected = 1500 * 23879 // self.rm.base_price('coin')
        self.assertEqual(inv(early)['coin']['units'], expected)
        self.assertLessEqual(abs(iv.value(early) - iv._value(1500, 23879)), 1)
        self.now.return_value += 900 * 600
        snapshot = copy.deepcopy(late)
        self.assertEqual(iv.public(late)['coin'], iv.public(early)['coin'])
        self.assertEqual(snapshot, late)
        iv.on_life_day(early)
        iv.on_life_day(late)
        self.assertEqual(inv(early), inv(late))
        reloaded = json.loads(json.dumps(late))
        iv.on_life_day(reloaded)
        self.assertEqual(reloaded, late)
        self.assertEqual(inv(late)['coin'], dict(old, units=expected))
        self.assertEqual(late['journey']['wallet'], s['journey']['wallet'])
        iv.validate(late)
        validate_state(late)

    def test_extreme_and_dust_conversion_preserve_basis_and_are_bounded(self):
        self.now.return_value = self.rm.EPOCH
        for units in (0, 1, 9, 999, 10**12):
            for price in (iv.PRICE_MIN, 23879, iv.PRICE_MAX):
                s = state()
                inv(s).update(price=price, prices=[price])
                inv(s)['coin'].update(units=units, basis=1 if units else 0)
                old_numerator = units * price
                iv.on_life_day(s)
                c = inv(s)['coin']
                self.assertEqual(c['basis'], 1 if units else 0)
                self.assertLess(abs(c['units'] * iv.BASE - old_numerator), iv.BASE)
                self.assertLessEqual(c['units'], iv.MAX_UNITS)
                iv.validate(s)

    def test_life_days_do_not_move_prices_but_savings_still_accrue(self):
        s, _ = act(state(wallet=1000), 'iv_save', amount=1000)
        before = iv.public(s)['coin']
        days(s, 7)
        self.assertEqual(iv.public(s)['coin'], before)
        self.assertEqual(inv(s)['saving']['earned'], 21)
        self.now.return_value += 86400
        self.assertEqual(iv.public(s)['saving']['earned'], 21)
        self.assertNotEqual(iv.public(s)['coin']['prices'], before['prices'])

    def test_trade_uses_new_tick_and_failed_direct_trade_does_not_convert(self):
        s = state(wallet=1000)
        before = copy.deepcopy(s)
        with self.assertRaises(GameError):
            iv.apply(s, 'iv_buy', {'amount': 1001})
        self.assertEqual(s, before)
        self.now.return_value = self.rm.EPOCH + 599
        self.assertEqual(iv.public(s)['coin']['market_clock']['tick'], 0)
        self.now.return_value += 1
        price = self.rm.quote('coin')['price']
        s, _ = act(s, 'iv_buy', amount=200)
        self.assertEqual(inv(s)['price'], price)
        self.assertEqual(inv(s)['coin']['units'], 196 * iv.COIN * iv.CENT // price)
        self.assertEqual(inv(s)['coin']['basis'], 200)
        self.assertEqual(inv(s)['coin']['fees'], 4)
        self.assertEqual(s['journey']['wallet'], 800)
        units = inv(s)['coin']['units']
        self.now.return_value += 600 * 25
        price = self.rm.quote('coin')['price']
        gross = iv._value(units, price)
        s, _ = act(s, 'iv_sell', all=True)
        self.assertEqual(s['journey']['wallet'], 800 + gross - iv._fee(gross))
        self.assertEqual(inv(s)['coin']['realised'], gross - iv._fee(gross) - 200)
        self.assertEqual(inv(s)['coin']['basis'], 0)

    def test_clock_and_gold_trade_value_share_quote_and_reads_are_pure(self):
        from game import rui
        s = state(wallet=5000)
        before = copy.deepcopy(s)
        c, g = iv.public(s)['coin'], vang.public(s)
        self.assertEqual(s, before)
        self.assertEqual(c['market_clock'], g['market_clock'])
        self.assertEqual(set(g['market_clock']),
                         {'tick', 'market_day', 'as_of', 'next_at', 'tick_seconds', 'day_seconds', 'timestamps'})
        self.assertEqual(g['p'], vang.price())
        self.assertEqual(g['hist'], vang.history())
        vang.action(s, 'jr_vang_buy', {'phan': 12})
        cost = vang.cost_of(12)
        self.assertEqual(s['journey']['wallet'], 5000 - cost)
        self.now.return_value += 500 * 600
        q = self.rm.quote('gold')
        expected = vang.worth(12, q['price'])
        self.assertEqual(vang.public(s)['value'], expected)
        self.assertEqual(vang.value(s), expected)
        self.assertEqual(rui.wealth(s), 5000 - cost + expected)
        vang.action(s, 'jr_vang_sell', {'all': True})
        self.assertEqual(s['journey']['wallet'], 5000 - cost + expected)
        vang.validate(s)

    def test_invalid_conversion_marker_rejected(self):
        s = state()
        for bad in (True, '1', 0, 2, {}):
            s['journey'][iv.REALTIME_KEY] = bad
            with self.assertRaises(GameError):
                iv.validate(s)


if __name__ == '__main__':
    unittest.main()
