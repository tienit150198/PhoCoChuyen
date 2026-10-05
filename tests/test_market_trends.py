"""Fictional market episodes: deterministic moves, migration and public truthfulness."""
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from game import invest as iv
from game import vang
from game import realtime_market as rm


def coin_state(seed=17, day=1):
    return {'journey': {'seed': seed, 'life_day': day, 'wallet': 0,
                        'stats': {'max_wallet': 0}, 'invest': iv.initial(seed, day)}}


def advance(s, n=1):
    s['journey']['life_day'] += n
    return iv.on_life_day(s)


class CoinNews(unittest.TestCase):
    def setUp(self):
        clock = patch.object(rm, 'now', return_value=rm.EPOCH + 600 * 100)
        clock.start()
        self.addCleanup(clock.stop)

    def test_existing_save_is_unchanged_by_migration_defaults_and_public_reads(self):
        s = coin_state(day=58)
        inv = s['journey']['invest']
        inv.update(price=23879, prices=[19001, 22103, 23879])
        inv['coin'].update(units=1500, basis=307, realised=-17, fees=9, trades=3)
        before = copy.deepcopy(s)
        iv.migrate(s)
        for _ in range(4):
            self.assertEqual(iv.public(s)['coin']['market_news'], rm.quote('coin')['news'])
        self.assertEqual(s, before)
        advance(s)
        after = s['journey']['invest']
        self.assertEqual(after['prices'], rm.quote('coin')['history'])
        self.assertEqual(after['coin'], dict(before['journey']['invest']['coin'], units=1500 * 23879 // iv.BASE))
        self.assertEqual(set(after), set(before['journey']['invest']))

    def test_legacy_walk_episodes_are_occasional_multiday_and_match_news(self):
        # This historical helper remains available for legacy analysis only.
        price = iv.initial(17)['price']
        runs, run = [], None
        active_days, ups, downs = 0, 0, 0
        for day in range(1, 1601):
            old = price
            price, event = iv._market_step(price, 17, day)
            news = event.public_news() if event else None
            if news:
                self.assertEqual(set(news), {'title', 'direction', 'active'})
                self.assertIs(news['active'], True)
                self.assertIn(news['direction'], ('up', 'down'))
                self.assertIn('trong game', news['title'])
                self.assertLessEqual(len(news['title']), 110)
                self.assertGreater((price - old) * (1 if news['direction'] == 'up' else -1), 0)
                active_days += 1
                if run is None:
                    run = [news, 0]
                    ups += news['direction'] == 'up'
                    downs += news['direction'] == 'down'
                self.assertEqual(news, run[0])
                run[1] += 1
            elif run:
                runs.append(run[1])
                run = None
        self.assertTrue(all(2 <= n <= 5 for n in runs), runs)
        self.assertGreater(len(runs), 40)
        self.assertTrue(.1 < active_days / 1600 < .3)
        self.assertTrue(.6 < ups / (ups + downs) < .8, (ups, downs))

    def test_chunking_polling_and_reload_never_reroll_prices_or_news(self):
        a = coin_state(seed=58)
        b = copy.deepcopy(a)
        for _ in range(200):
            advance(a)
            snapshot = copy.deepcopy(a)
            first = iv.public(a)
            self.assertEqual(iv.public(a), first)
            self.assertEqual(iv.on_life_day(a), [])
            self.assertEqual(a, snapshot)
            a = json.loads(json.dumps(a))
        for _ in range(4):
            advance(b, 50)
        self.assertEqual(a, b)
        self.assertEqual(iv.public(a), iv.public(b))

    def test_life_days_do_not_create_market_news_logs(self):
        s = coin_state()
        initial = iv.public(s)['coin']
        for _ in range(200):
            advance(s)
            self.assertEqual(iv.public(s)['coin'], initial)
            self.assertFalse(any(x['kind'] in ('pump', 'crash') for x in s['journey']['invest']['log']))

    def test_1710_roundtrip_accepts_marker_and_preserves_holdings_and_quotes(self):
        old = Path(os.environ.get('MNL_MARKET_OLD_TREE') or
                   Path(__file__).resolve().parents[1] / 'output/release-1710/mot-ngay-lam-nghe')
        if not (old / 'game/invest.py').is_file():
            self.skipTest('1.7.10 fixture unavailable (MNL_MARKET_OLD_TREE)')
        from tests.test_invest import state, act
        from game.engine import migrate_state, validate_state
        s, _ = act(state(wallet=5000), 'iv_buy', amount=700)
        s, _ = act(s, 'iv_save', amount=300)
        advance(s, 20)
        inv = copy.deepcopy(s['journey']['invest'])
        marker = s['journey'][iv.REALTIME_KEY]
        code = ('import json,sys;from game.engine import migrate_state,validate_state;'
                'from game import invest;s=migrate_state(json.load(sys.stdin));'
                'validate_state(s);invest.validate(s);invest.public(s);print(json.dumps(s))')
        env = dict(os.environ, PYTHONPATH=str(old) + os.pathsep + os.environ.get('PYTHONPATH', ''))
        proc = subprocess.run([sys.executable, '-c', code], input=json.dumps(s), capture_output=True,
                              text=True, encoding='utf-8', cwd=old, env=env, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        back = json.loads(proc.stdout)
        self.assertEqual(back['journey']['invest'], inv)
        self.assertEqual(back['journey'][iv.REALTIME_KEY], marker)
        back = migrate_state(back)
        validate_state(back)
        self.assertEqual(back['journey']['invest'], inv)
        self.assertEqual(iv.public(back), iv.public(s))

    def test_long_run_growth_does_not_pin_the_price_ceiling(self):
        self.assertTrue(hasattr(iv, '_market_step'), 'future ticks need the multi-day market step')
        profits = 0
        for seed in range(20):
            p = iv.initial(seed)['price']
            start = p
            for d in range(1, 5001):
                p, _ = iv._market_step(p, seed, d)
                self.assertTrue(iv.PRICE_MIN < p < iv.PRICE_MAX // 10)
                if d == 365:
                    profits += p > start
            self.assertLess(p, iv.BASE * 20)
        self.assertGreaterEqual(profits, 15)


class GoldNews(unittest.TestCase):
    def test_legacy_prices_and_headlines_are_identical_through_october_fifth(self):
        anchors = {
            'kim-phat': '5bab6f736c89b76473b415993126ff26c1e61af9a243c47c3a05a27a0e35035e',
            'another': '172f7ad7d24daacd0aefd63e71d182f1fa17a2ea9b57f5965d7438c4fdefb734',
            'regression': 'f2acbd5bab41f61b1efebb3d0057bcdec324af13b1c288de85ad5ed3ee7c8b73',
        }
        cutoff = dt.date(2026, 10, 5)
        for salt, expected in anchors.items():
            old = vang._walk(salt, cutoff)
            self.assertEqual(hashlib.sha256(json.dumps(old).encode()).hexdigest(), expected)
            self.assertEqual(vang._walk(salt, cutoff + dt.timedelta(days=200))[:len(old)], old)

    def test_gold_quotes_and_news_are_shared_without_mutating_holdings(self):
        s = {'journey': {'story': True, 'vang': vang.initial()}}
        s['journey']['vang'].update(phan=27, cost=1357)
        before = copy.deepcopy(s)
        for tick in range(72):
            with patch.object(rm, 'now', return_value=rm.EPOCH + tick * 600):
                p = vang.public(s)
                q = rm.quote('gold')
                self.assertEqual(p, vang.public(s))
                self.assertEqual(p['p'], vang.price())
                self.assertEqual(p['hist'][-1], p['p'])
                self.assertEqual(p['market_news'], q['news'])
                news = p['market_news']
                if news:
                    self.assertEqual(set(news), {'title', 'direction', 'active'})
                    self.assertEqual(p['news'], news['title'])
                    self.assertIn(news['direction'], ('up', 'down', 'flat'))
                    self.assertLess(len(json.dumps(news, ensure_ascii=False)), 175)
                quote = dict(p)
                quote.pop('market_news')
                clock = quote.pop('market_clock')
                self.assertLess(len(json.dumps(quote, ensure_ascii=False)), 400)
                self.assertLess(len(json.dumps(clock)), 600)
        self.assertEqual(s, before)

    def test_gold_keeps_growing_slowly_without_exponential_money_or_ceiling(self):
        prices = [p for p, _ in vang._walk('kim-phat', dt.date(2040, 10, 6))]
        self.assertTrue(all(50 < p < 10000 for p in prices))
        self.assertGreater(prices[-1], prices[34])
        self.assertLess(prices[-1], prices[34] * 10)


if __name__ == '__main__':
    unittest.main()
