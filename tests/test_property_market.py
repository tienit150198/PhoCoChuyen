"""Shared fictional property news follows real Vietnam dates, never player turns."""
import datetime as dt
import importlib
import unittest
from unittest.mock import patch

from game import property_market as market


START = dt.date(2026, 10, 6)


def days(n=3650, kind='can_ho'):
    for offset in range(n):
        day = START + dt.timedelta(days=offset)
        yield day, market.quote(kind, day)


class PropertyMarketTests(unittest.TestCase):
    def test_historical_quotes_are_neutral(self):
        for day in (dt.date.min, dt.date(2026, 1, 1), dt.date(2026, 10, 5)):
            self.assertEqual(market.quote('can_ho', day),
                             dict(multiplier_bp=10000, rent_bp=10000, news=None))

    def test_default_clock_uses_vietnam_midnight(self):
        midnight = dt.datetime(2026, 10, 6, 17, tzinfo=dt.timezone.utc).timestamp()
        with patch.object(market, 'now', return_value=midnight - 1):
            self.assertEqual(market.today(), dt.date(2026, 10, 6))
            self.assertEqual(market.quote('can_ho'), market.quote('can_ho', '2026-10-06'))
        with patch.object(market, 'now', return_value=midnight):
            self.assertEqual(market.today(), dt.date(2026, 10, 7))

    def test_reads_and_module_reload_share_the_same_quote(self):
        day, first = next((d, q) for d, q in days() if q['news'])
        for _ in range(10):
            self.assertEqual(market.quote('can_ho', day), first)
        importlib.reload(market)
        self.assertEqual(market.quote('can_ho', day.isoformat()), first)
        modified = market.quote('can_ho', day)
        modified['multiplier_bp'] = 1
        modified['news']['title'] = 'tampered'
        self.assertEqual(market.quote('can_ho', day), first)

    def test_episode_persists_then_recovers_without_rerolling(self):
        samples = list(days(365))
        start = next(i for i, (_, q) in enumerate(samples) if q['news'])
        episode = samples[start][1]
        identity = episode['news']['id']
        active, recovery = [], []
        for day, q in samples[start:]:
            if not q['news'] or q['news']['id'] != identity:
                self.assertEqual(q['multiplier_bp'], 10000)
                self.assertEqual(q['rent_bp'], 10000)
                self.assertIsNone(q['news'])
                break
            self.assertEqual(q['news']['title'], episode['news']['title'])
            self.assertEqual(q['news']['direction'], episode['news']['direction'])
            (active if q['news']['phase'] == 'active' else recovery).append(q)
        self.assertGreaterEqual(len(active), 3)
        self.assertTrue(all(q == episode for q in active))
        self.assertGreaterEqual(len(recovery), 5)
        for key in ('multiplier_bp', 'rent_bp'):
            deviations = [abs(q[key] - 10000) for q in active[-1:] + recovery]
            self.assertTrue(all(a > b > 0 for a, b in zip(deviations, deviations[1:])))

    def test_calendar_is_varied_occasional_and_bounded(self):
        headlines, directions, active_days = set(), set(), 0
        deep_drop, strong_rise = False, False
        for _, q in days():
            for key in ('multiplier_bp', 'rent_bp'):
                self.assertIs(type(q[key]), int)
                self.assertTrue(5500 <= q[key] <= 16500)
            news = q['news']
            if news:
                active_days += 1
                headlines.add(news['title'])
                directions.add(news['direction'])
                self.assertIn('trong game', news['title'])
                self.assertNotIn('end', news)
                sign = 1 if news['direction'] == 'up' else -1
                self.assertGreater((q['multiplier_bp'] - 10000) * sign, 0)
                self.assertGreater((q['rent_bp'] - 10000) * sign, 0)
                deep_drop |= q['multiplier_bp'] <= 6500 and q['rent_bp'] <= 6500
                strong_rise |= q['multiplier_bp'] >= 14500
        self.assertGreaterEqual(len(headlines), 8)
        self.assertEqual(directions, {'up', 'down'})
        self.assertTrue(0.15 < active_days / 3650 < 0.5)
        self.assertTrue(deep_drop)
        self.assertTrue(strong_rise)

    def test_kinds_have_independent_but_shared_calendars(self):
        self.assertTrue(any(q != market.quote('biet_thu', day) for day, q in days(365)))

    def test_far_future_uses_bounded_lookup_and_cache(self):
        market._window.cache_clear()
        q = market.quote('can_ho', dt.date.max)
        self.assertTrue(5500 <= q['multiplier_bp'] <= 16500)
        self.assertEqual(market._window.cache_info().misses, 1)
        for offset in range(1500):
            market.quote('can_ho', START + dt.timedelta(days=offset * 28))
        self.assertLessEqual(market._window.cache_info().currsize, 1024)

    def test_bad_day_is_rejected_instead_of_silently_using_today(self):
        with self.assertRaises(ValueError):
            market.quote('can_ho', 'bad-date')
        with self.assertRaises(TypeError):
            market.quote('can_ho', 123)


if __name__ == '__main__':
    unittest.main()
