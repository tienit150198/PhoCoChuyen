"""Shared wall-clock prices: boundaries, causal history and bounded computation."""
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import time
import unittest
from unittest.mock import patch


class RealtimeMarket(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('game.realtime_market'),
                             'The shared realtime market must exist')
        from game import realtime_market
        self.market = realtime_market
        self.salt = patch.dict(os.environ, {'MNL_MARKET_SALT': 'realtime-test-v1'})
        self.salt.start()
        self.addCleanup(self.salt.stop)

    def test_epoch_and_asset_anchors(self):
        from game import vang
        m = self.market
        self.assertEqual(m.EPOCH, dt.datetime(2026, 10, 4, 17, tzinfo=dt.timezone.utc).timestamp())
        self.assertEqual(m.base_price('coin'), 10000)
        self.assertEqual(m.base_price('gold'), vang.price(dt.date(2026, 10, 5)))
        for asset in ('coin', 'gold'):
            q = m.quote(asset, m.EPOCH)
            self.assertEqual(q['price'], m.base_price(asset))
            self.assertEqual(q['previous'], q['price'])
            self.assertEqual(q['history'], [q['price']])

    def test_ten_minute_ticks_and_hourly_market_days(self):
        m = self.market
        for offset, tick, day in ((0, 0, 1), (599, 0, 1), (600, 1, 1),
                                  (3599, 5, 1), (3600, 6, 2)):
            q = m.quote('coin', m.EPOCH + offset)
            self.assertEqual((q['tick'], q['market_day']), (tick, day))
            self.assertEqual(q['as_of'], m.EPOCH + tick * 600)
            self.assertEqual(q['next_at'], q['as_of'] + 600)
        with patch.object(m, 'now', return_value=m.EPOCH + 600):
            self.assertEqual(m.quote('coin'), m.quote('coin', m.EPOCH + 600))

    def test_polls_offline_and_future_reads_do_not_rewrite_history(self):
        m = self.market
        at = m.EPOCH + 500 * 600
        original = m.quote('coin', at)
        for offset in (1, 200, 599):
            self.assertEqual(original, m.quote('coin', at + offset))
        m.quote('coin', at + 10000000)
        self.assertEqual(original, m.quote('coin', at))
        newer = m.quote('coin', at + 5 * 600)
        self.assertEqual(original['history'][5:], newer['history'][:-5])
        self.assertEqual(original['price'], newer['history'][-6])

    def test_public_quote_contains_only_past_prices_and_safe_news(self):
        m = self.market
        q = m.quote('gold', m.EPOCH + 100 * 600)
        self.assertEqual(set(q), {'price', 'previous', 'history', 'timestamps', 'tick',
                                 'market_day', 'as_of', 'next_at', 'news'})
        self.assertEqual(len(q['history']), 30)
        self.assertEqual(len(q['timestamps']), 30)
        self.assertEqual(q['previous'], q['history'][-2])
        self.assertEqual(q['price'], q['history'][-1])
        for timestamp, price in zip(q['timestamps'], q['history']):
            self.assertLessEqual(timestamp, q['as_of'])
            self.assertEqual(price, m.quote('gold', timestamp)['price'])
        self.assertEqual(set(q['news']), {'title', 'direction', 'active'})
        self.assertNotIn('realtime-test-v1', json.dumps(q))

    def test_cached_quotes_cannot_be_mutated_by_callers(self):
        m = self.market
        at = m.EPOCH + 42 * 600
        expected = m.quote('coin', at)
        altered = m.quote('coin', at)
        altered['history'].clear()
        altered['timestamps'].clear()
        altered['news']['title'] = 'tampered'
        self.assertEqual(expected, m.quote('coin', at))

    def test_fresh_worker_and_salt_fallback_are_deterministic(self):
        m = self.market
        at = m.EPOCH + 100 * 600
        code = f'from game.realtime_market import quote; import json; print(json.dumps(quote("coin", {at})))'
        actual = json.loads(subprocess.check_output([sys.executable, '-c', code], text=True))
        self.assertEqual(m.quote('coin', at), actual)
        with patch.dict(os.environ, {'MNL_MARKET_SALT': 'another-market'}):
            self.assertNotEqual(m.quote('coin', at)['history'], actual['history'])
        with patch.dict(os.environ, {'MNL_GOLD_SALT': 'fallback-market'}):
            os.environ.pop('MNL_MARKET_SALT', None)
            fallback = m.quote('coin', at)
            os.environ['MNL_MARKET_SALT'] = 'fallback-market'
            self.assertEqual(fallback, m.quote('coin', at))

    def test_both_markets_have_gains_losses_and_coin_is_noisier(self):
        m = self.market
        volatility = {}
        for asset in ('coin', 'gold'):
            quotes = [m.quote(asset, m.EPOCH + tick * 600) for tick in range(6 * 30 + 1)]
            prices = [q['price'] for q in quotes]
            returns = [b / a - 1 for a, b in zip(prices, prices[1:])]
            self.assertGreater(sum(r > 0 for r in returns), 35)
            self.assertGreater(sum(r < 0 for r in returns), 35)
            volatility[asset] = sum(abs(r) for r in returns) / len(returns)
            directions = {q['news']['direction'] for q in quotes}
            self.assertTrue({'up', 'down', 'flat'} <= directions)
            hourly = [prices[t + 6] - prices[t] for t in range(0, 180, 6)]
            self.assertTrue(any(r > 0 for r in hourly))
            self.assertTrue(any(r < 0 for r in hourly))
            # News is a regime, never a guaranteed per-tick return.
            self.assertTrue(any(q['news']['direction'] == 'up' and q['price'] < q['previous']
                                for q in quotes))
            self.assertTrue(any(q['news']['direction'] == 'down' and q['price'] > q['previous']
                                for q in quotes))
            self.assertLess(max(abs(r) for r in returns), .10)
        self.assertGreater(volatility['coin'], volatility['gold'] * 1.5)

    def test_ten_year_cold_quote_has_bounded_work(self):
        m = self.market
        with patch.dict(os.environ, {'MNL_MARKET_SALT': 'ten-year-cold'}):
            started = time.perf_counter()
            q = m.quote('coin', m.EPOCH + 10 * 365 * 86400)
            self.assertLess(time.perf_counter() - started, .5)
            self.assertEqual(len(q['history']), 30)
            self.assertGreater(q['price'], 0)

    def test_headlines_support_hourly_direction_without_guaranteeing_it(self):
        m = self.market
        for salt in ('news-audit-one', 'news-audit-two', 'news-audit-three'):
            with patch.dict(os.environ, {'MNL_MARKET_SALT': salt}):
                for asset in ('coin', 'gold'):
                    outcomes = {'up': [], 'down': []}
                    for day in range(720):
                        q = m.quote(asset, m.EPOCH + day * m.DAY_SECONDS)
                        direction = q['news']['direction']
                        if direction == 'flat':
                            continue
                        next_price = m.quote(asset, m.EPOCH + (day + 1) * m.DAY_SECONDS)['price']
                        move = next_price - q['price']
                        outcomes[direction].append(move > 0 if direction == 'up' else move < 0)
                    for direction, matched in outcomes.items():
                        agreement = sum(matched) / len(matched)
                        self.assertGreater(agreement, .60, (salt, asset, direction, agreement))
                        self.assertLess(agreement, .85, (salt, asset, direction, agreement))

    def test_invalid_asset_is_rejected(self):
        with self.assertRaises(ValueError):
            self.market.quote('unsupported', self.market.EPOCH)

    def test_deployment_epoch_override_anchors_gold_on_local_cutover_date(self):
        cutover = self.market.EPOCH + 2 * 86400 + 3600
        code = ('from game import realtime_market as m, vang; import datetime as dt,json; '
                'print(json.dumps([m.EPOCH,m.base_price("gold"),'
                'vang.price(dt.date(2026,10,7)),m.quote("coin",m.EPOCH)["price"]]))')
        env = dict(os.environ, MNL_MARKET_EPOCH=str(cutover))
        result = json.loads(subprocess.check_output([sys.executable, '-c', code], env=env, text=True))
        self.assertEqual(result[0], cutover)
        self.assertEqual(result[1], result[2])
        self.assertEqual(result[3], 10000)

    def test_invalid_deployment_epochs_fail_at_startup(self):
        for value in ('invalid', '-1', '1.5', '99999999999999999999'):
            result = subprocess.run([sys.executable, '-c', 'from game import realtime_market'],
                                    env=dict(os.environ, MNL_MARKET_EPOCH=value), capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, value)
            self.assertIn('MNL_MARKET_EPOCH', result.stderr)

    def test_public_runtime_requires_explicit_cutover(self):
        m = self.market
        self.assertTrue(callable(getattr(m, 'validate_runtime', None)), 'Runtime validation must exist')
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'MNL_MARKET_EPOCH'):
                m.validate_runtime(at=m.EPOCH)
            self.assertIsNone(m.validate_runtime(public=False, at=m.EPOCH - 1))

    def test_public_runtime_rejects_missing_or_trivial_market_secret(self):
        m = self.market
        self.assertTrue(callable(getattr(m, 'validate_runtime', None)), 'Runtime validation must exist')
        for value in ('', 'kim-phat', 'short-secret', 'x' * 32, 'kim-phat' * 4):
            with patch.dict(os.environ, {'MNL_MARKET_EPOCH': str(m.EPOCH),
                                         'MNL_MARKET_SALT': value}, clear=True):
                with self.assertRaisesRegex(ValueError, 'SALT'):
                    m.validate_runtime(at=m.EPOCH)

    def test_public_runtime_accepts_persistent_secret_or_gold_fallback(self):
        m = self.market
        self.assertTrue(callable(getattr(m, 'validate_runtime', None)), 'Runtime validation must exist')
        for key in ('MNL_MARKET_SALT', 'MNL_GOLD_SALT'):
            with patch.dict(os.environ, {'MNL_MARKET_EPOCH': str(m.EPOCH),
                                         key: '58e83fa76da44ef59c6f42bb06918c82'}, clear=True):
                self.assertIsNone(m.validate_runtime(public=True, at=m.EPOCH))
                with patch.object(m, 'now', return_value=m.EPOCH + 600):
                    self.assertIsNone(m.validate_runtime())

    def test_public_runtime_rejects_future_cutover(self):
        m = self.market
        self.assertTrue(callable(getattr(m, 'validate_runtime', None)), 'Runtime validation must exist')
        with patch.dict(os.environ, {'MNL_MARKET_EPOCH': str(m.EPOCH),
                                     'MNL_MARKET_SALT': '58e83fa76da44ef59c6f42bb06918c82'}):
            with self.assertRaisesRegex(ValueError, 'future'):
                m.validate_runtime(at=m.EPOCH - 1)

    def test_validated_workers_share_configuration_and_prices(self):
        m = self.market
        self.assertTrue(callable(getattr(m, 'validate_runtime', None)), 'Runtime validation must exist')
        env = dict(os.environ, MNL_MARKET_EPOCH=str(m.EPOCH),
                   MNL_MARKET_SALT='58e83fa76da44ef59c6f42bb06918c82')
        code = ('from game import realtime_market as m; import json; '
                'm.validate_runtime(at=m.EPOCH+600); '
                'print(json.dumps([m.EPOCH,m.quote("coin",m.EPOCH+600)]))')
        first = subprocess.check_output([sys.executable, '-c', code], env=env, text=True)
        second = subprocess.check_output([sys.executable, '-c', code], env=env, text=True)
        self.assertEqual(json.loads(first), json.loads(second))


if __name__ == '__main__':
    unittest.main()
