"""🎢 The wild market (game/market_wild.py) and Sàn Phố holdings (game/san.py): catalogue, fairness of simple
strategies (statistical, seeded salts), caps, continuity from the old Mây Coin / gold prices, delisting."""
import copy
import json
import math
import os
import statistics as st
import subprocess
import sys
import unittest
from unittest.mock import patch

from game import market_wild as mw
from game import realtime_market as rm
from game import san
from game.engine import GameError, validate_state

H, D, W = mw.HOUR, mw.DAY_TICKS, 7 * mw.DAY_TICKS
START = 6 * 600            # a test cutover tick (hour aligned), 25 days after the epoch


class KeepAll(list):
    """An event list the engine cannot trim (the strategy checks look at every event)."""

    def __delitem__(self, k):
        pass


def adjusted(eng, a):
    """Split-adjusted prices (a split 1→10 is not a fall of 90 %)."""
    return [p / 10. ** x for p, x in zip(eng.prices[a], eng.exps[a])]


class Market(unittest.TestCase):
    """Runs every test with its own salt and a cutover at START; `at(t)` is the wall clock of tick t."""

    salt = 'wild-test-v1'

    def setUp(self):
        for p in (patch.dict(os.environ, {'MNL_MARKET_SALT': self.salt}), patch.object(mw, 'WILD_TICK', START)):
            p.start()
            self.addCleanup(p.stop)

    @staticmethod
    def at(t):
        return rm.EPOCH + t * mw.TICK + 1


class Catalogue(unittest.TestCase):
    def test_new_assets_have_personalities_and_safe_bounds(self):
        coins = [a for a in mw.NEW if mw.ASSETS[a]['kind'] == 'coin']
        stocks = [a for a in mw.NEW if mw.ASSETS[a]['kind'] == 'stock']
        self.assertGreaterEqual(len(coins), 8)
        self.assertGreaterEqual(len(stocks), 10)
        self.assertEqual(len({mw.ASSETS[a]['sym'] for a in mw.ORDER}), len(mw.ORDER))
        self.assertIn('mai', coins)
        self.assertGreaterEqual(len({mw.ASSETS[a]['sector'] for a in stocks}), 8)
        for a in mw.ORDER:
            sp = mw.ASSETS[a]
            self.assertIn(sp['sector'], mw.SECTORS)
            self.assertGreaterEqual(sp['lo'], 50)
            self.assertLess(sp['lo'], sp['launch'] if not sp['legacy'] else sp['hi'])
            self.assertLessEqual(sp['hi'], 10_000_000)
            self.assertLessEqual(sp['hi'] * san.UNITS_MAX // san.SCALE, 10**17)
            if sp['risky']:
                self.assertIn('hủy niêm yết', sp['desc'])
                self.assertGreaterEqual(sp['delist'], 100)
                self.assertGreater(sp['unlock'], 500)
            else:
                self.assertEqual(sp['delist'], 0)
            if not sp['legacy']:
                # the bottom taper and the rounding stay far from the launch price (≥ 1 xu and ≤ 1 % a tick)
                self.assertGreaterEqual(sp['launch'], 1000)
                self.assertGreaterEqual(sp['launch'] / sp['lo'], 10)
        self.assertEqual([x['id'] for x in mw.catalogue()], list(mw.ORDER))
        self.assertNotIn('vol', json.dumps(mw.catalogue()))

    def test_compensator_makes_every_step_fair(self):
        """E[e^r] = 1 for every asset, regime and taper: the moment generating functions of the draws are exact."""
        import random
        for a in ('coin', 'pho', 'mai', 'dua', 'pmf', 'app', 'gold'):
            sp = mw.ASSETS[a]
            sec = mw.SECTORS[sp['sector']]
            fac = mw.FACTORS[sec['market']]
            for reg in ('normal', 'bull', 'wild'):
                for tau in (1., .4):
                    mu = mw.Engine._mu(sp, sec, fac, reg, 'normal', tau)
                    vm, jm, qs = mw.REGIMES[reg]
                    rng = random.Random(f'{a}{reg}{tau}')
                    u = rng.random
                    total, n = 0., 60000
                    for _ in range(n):
                        z = [(u() + u() + u() + u() - 2.) * 1.7320508075688772 for _ in range(3)]
                        r = mu + (sp['beta'] * fac['vol'] * z[0] + sp['gamma'] * sec['vol'] * vm * z[1] + sp['vol'] * vm * z[2]) * tau / 12
                        r += sp['gamma'] * tau * mw._jump_u(u(), u(), u(), sec['shocks'] / D, sec['up'], *sec['size'])
                        r += sp['beta'] * tau * mw._jump_u(u(), u(), u(), fac['shocks'] / D, fac['up'], *fac['size'])
                        lo, hi = sp['jsize']
                        r += mw._jump_u(u(), u(), u(), min(.5, sp['jumps'] * jm / D), min(.95, max(.05, sp['up'] + qs)),
                                        lo * tau, hi * tau)
                        total += math.exp(r)
                    self.assertAlmostEqual(total / n, 1, delta=.0015, msg=(a, reg, tau))

    def test_pump_hazard_is_fair(self):
        for g in (.01, .05, .12):
            for D_ in (.1, .8, 2.):
                h = (math.exp(g) - 1) / (math.exp(g) - math.exp(-D_))
                self.assertAlmostEqual((1 - h) * math.exp(g) + h * math.exp(-D_), 1, places=12)


class Strategies(unittest.TestCase):
    """No simple rule a player can follow earns: after fees every one loses on average (24 seeded markets × 10 days).
    The standard error comes from the per-market means (paths in one market share the factors)."""

    @classmethod
    def setUpClass(cls):
        cls.markets = []
        for k in range(24):
            eng = mw.Engine(f'ev-{k}', 6000, {'coin': 11000, 'gold': 650})
            eng.events = KeepAll()
            eng.advance(6000 + 10 * D)
            eng.adj = {a: adjusted(eng, a) for a in mw.ORDER}
            eng.at = {}
            for ev in eng.events:
                eng.at.setdefault((ev[0], ev[1], ev[2]), []).append(ev)
            cls.markets.append(eng)

    @staticmethod
    def rt(a, p0, p1):
        if mw.ASSETS[a]['kind'] == 'gold':
            return .975 / 1.025 * p1 / p0 - 1
        f = mw.ASSETS[a]['fee'] / 100
        return (1 - f) ** 2 * p1 / p0 - 1

    def collect(self, rule, assets):
        means = []
        for eng in self.markets:
            xs = []
            for a in assets:
                P, G = eng.adj[a], eng.gens[a]
                for i in range(D, len(P) - D, 1):
                    hold = rule(P, i, eng, a)
                    if hold and P[i] > 0:
                        j = i + hold
                        xs.append(self.rt(a, P[i], P[j] if G[j] == G[i] else 0))
            if xs:
                means.append(st.mean(xs))
        if len(means) < 2:
            return 0., 0., len(means)
        return st.mean(means), st.pstdev(means) / math.sqrt(len(means)), len(means)

    def check(self, name, rule, assets):
        m, se, n = self.collect(rule, assets)
        if 'hold' in name:
            self.assertGreater(n, 5, name)          # a rare signal (gold news, a stock pump) may never fire
        # never reliably positive: the mean stays under +1 standard error above zero
        self.assertLess(m, max(.002, se), f'{name}: mean {m:+.4f} se {se:.4f}')
        return m

    def test_no_rule_beats_the_fee(self):
        stocks = [a for a in mw.NEW if mw.ASSETS[a]['kind'] == 'stock']
        coins = ['coin'] + [a for a in mw.NEW if mw.ASSETS[a]['kind'] == 'coin' and not mw.ASSETS[a]['risky']]
        risky = [a for a in mw.NEW if mw.ASSETS[a]['risky']]
        every = lambda k: (lambda P, i, e, a: k if i % 7 == 0 else 0)  # noqa: E731

        def dip(P, i, e, a):
            if i % H or P[i] <= 0:
                return 0
            avg = sum(P[i - D:i]) / D
            return 72 if P[i] <= .9 * avg else 0

        def momentum(P, i, e, a):
            return H if i % H == 0 and P[i - H] > 0 and P[i] >= 1.05 * P[i - H] else 0

        def news_up(P, i, e, a):
            return H if any(ev[5] > 0 for ev in e.at.get((e.start + i, a, 'news'), ())) else 0

        def pump(P, i, e, a):
            return H if (e.start + i, a, 'pump') in e.at else 0

        for group in (stocks, coins, risky, ['gold']):
            for name, rule in (('hold 1h', every(H)), ('hold 1d', every(D)), ('dip', dip), ('momentum', momentum),
                               ('news up', news_up), ('ride a pump', pump)):
                if name == 'ride a pump' and group in (stocks, ['gold']):
                    continue
                self.check(f'{group[0]}… {name}', rule, group)

    def test_the_engine_keeps_only_recent_events(self):
        eng = mw.Engine('trim', 6000)
        eng.advance(6000 + 5 * D)
        self.assertLessEqual(len(eng.events), mw.EVENTS_KEEP * 2)
        self.assertGreater(sum(len(v) for v in self.markets[0].at.values()), mw.EVENTS_KEEP * 2)

    def test_swings_are_wild_but_bounded(self):
        big_coin = big_stock = 0
        for eng in self.markets:
            for a in mw.ORDER:
                sp, raw, P = mw.ASSETS[a], eng.prices[a], eng.adj[a]
                for i in range(len(P)):
                    if raw[i]:
                        self.assertTrue(sp['lo'] <= raw[i] <= sp['hi'], (a, raw[i]))
                    else:
                        self.assertTrue(sp['risky'], a)
                    if i >= H and P[i] and P[i - H]:
                        ch = P[i] / P[i - H] - 1
                        if sp['kind'] == 'coin' and abs(ch) >= .4:
                            big_coin += 1
                        if sp['kind'] == 'stock' and abs(ch) >= .08:
                            big_stock += 1
        self.assertGreater(big_coin, 20)
        self.assertGreater(big_stock, 20)


class Continuity(Market):
    def test_mây_coin_and_gold_continue_from_the_old_price(self):
        last = START - 1
        for a in ('coin', 'gold'):
            old = rm._price(a, rm._salt(), rm.base_price(a), last)
            self.assertEqual(rm.price_at(a, last), old)
            self.assertEqual(rm.quote(a, self.at(last))['price'], old)
            eng = mw.Engine(rm._salt(), START, mw._legacy_start(rm._salt(), START))     # fresh: same prices
            eng.advance(START)
            self.assertEqual(eng.price(a, START), mw.price_at(a, START))
            self.assertAlmostEqual(math.exp(eng.st[a]['L']) / mw.price_at(a, START), 1, delta=.01)
            first = mw.price_at(a, START)
            self.assertLess(abs(math.log(first / old)), .35, a)        # one ordinary step, no jump at deploy
            q = rm.quote(a, self.at(START + 3))
            self.assertEqual(q['history'][-4], first)
            self.assertEqual(q['history'][-5], old)                   # the chart runs straight through the cutover
            self.assertEqual(len(q['history']), 30)

    def test_new_assets_list_at_cutover_at_their_launch_price(self):
        self.assertFalse(mw.listed(START - 1))
        self.assertEqual(mw.history('pho', START - 1, 30), [mw.ASSETS['pho']['launch']])
        self.assertTrue(mw.listed(START))
        self.assertEqual(len(mw.history('pho', START + 2, 30)), 3)

    def test_prices_are_shared_by_workers_and_never_ahead_of_now(self):
        t = START + 2 * D + 5
        code = (f'import os; os.environ["MNL_MARKET_SALT"]="{self.salt}"; '
                f'from game import market_wild as mw; mw.WILD_TICK={START}; '
                f'print(mw.price_at("cuoi", {t}), mw.price_at("pmf", {t}), mw.price_at("coin", {t}))')
        out = subprocess.check_output([sys.executable, '-c', code], text=True).split()
        self.assertEqual([int(x) for x in out], [mw.price_at('cuoi', t), mw.price_at('pmf', t), mw.price_at('coin', t)])
        eng = mw.engine(t)
        self.assertEqual(eng.t, t)
        b = mw.board(self.at(t))
        self.assertEqual(eng.t, t)
        self.assertTrue(all(r['tick'] <= t for r in b['ticker']))
        self.assertNotIn(self.salt, json.dumps(b))
        with patch.dict(os.environ, {'MNL_MARKET_SALT': 'another-wild-salt'}):
            self.assertNotEqual([mw.price_at(a, t) for a in mw.NEW], [int(x) for x in out[:1]] * len(mw.NEW))

    def test_market_data_carries_the_board_and_the_open_asset(self):
        import market_data as md
        md._snapshot.cache_clear()
        t = START + D
        data = md.snapshot('1D', self.at(t), 'mtech')
        self.assertEqual(set(data['board']['assets']), set(mw.ORDER))
        self.assertEqual(data['sel']['id'], 'mtech')
        self.assertEqual(data['sel']['points'][-1][1], mw.price_at('mtech', t))
        self.assertLessEqual(len(data['sel']['points']), 181)
        self.assertGreaterEqual(data['sel']['points'][0][0], rm.EPOCH + START * mw.TICK)
        self.assertEqual(data['coin']['points'][-1][1], rm.quote('coin', self.at(t))['price'])
        with self.assertRaises(ValueError):
            md.snapshot('1D', self.at(t), 'nope')


def story(wallet=50000, max_wallet=None):
    from game import invest as iv
    from game import journey as jr
    from game.engine import new_state
    s = new_state()
    jr.enable_story(s, 4242)
    j = s['journey']
    j['gender'] = 'female'
    j['wallet'] = wallet
    j['stats']['max_wallet'] = max(wallet, max_wallet or 0)
    iv.migrate(s)
    validate_state(s)
    return s


def act(s, name, **p):
    from game import journey as jr
    t = copy.deepcopy(s)
    t, r = jr.action(t, None, name, p)
    validate_state(t)
    return t, r


class Holdings(Market):
    def setUp(self):
        super().setUp()
        self.t = START + D + 3
        p = patch.object(rm, 'now', return_value=self.at(self.t))
        p.start()
        self.addCleanup(p.stop)

    def test_buy_sell_fees_rows_and_wealth(self):
        from game import wealth, wealth_pricing
        s = story(50000)
        price = mw.price_at('pmf', self.t)
        s, r = act(s, 'jr_san_buy', a='pmf', amount=10000)
        h = s['journey']['san']['h']['pmf']
        self.assertEqual(h['b'], 10000)
        self.assertEqual(h['u'], (10000 - 100) * san.SCALE // price)     # stocks: 1 % fee
        self.assertEqual(s['journey']['wallet'], 40000)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'invest')
        self.assertEqual(wealth._extras(s['journey'])[0] - wealth._extras(story(40000)['journey'])[0], 10000)
        self.assertEqual(san.value(s), san.value_of(h['u'], price))
        self.assertGreaterEqual(wealth_pricing.total(s), 40000 + san.value(s))
        pub = san.public(s)
        self.assertEqual(pub['hold']['pmf']['value'], san.value_of(h['u'], price))
        self.assertTrue(pub['open'])
        s, r = act(s, 'jr_san_sell', a='pmf', all=True)
        self.assertNotIn('pmf', s['journey']['san']['h'])
        gross = san.value_of(h['u'], price)
        self.assertEqual(s['journey']['wallet'], 40000 + gross - max(1, -(-gross // 100)))
        self.assertLess(s['journey']['wallet'], 50000)                     # a round trip at one price costs the fee
        self.assertEqual(s['journey']['san']['st']['n'], 2)

    def test_locks_limits_and_refusals_change_nothing(self):
        s = story(1500, 1500)
        with self.assertRaises(GameError) as cm:
            act(s, 'jr_san_buy', a='pmf', amount=100)                       # stocks open at 2 000 xu
        self.assertEqual(cm.exception.code, 'locked')
        s = story(50000)
        for bad in (dict(a='coin', amount=100), dict(a='gold', amount=100), dict(a='nope', amount=100),
                    dict(a='pho', amount=5), dict(a='pho', amount=san.AMOUNT_MAX + 1), dict(a='pho', amount=60000),
                    dict(a='pho', amount=1.5), dict(a='pho'), dict(a='pho', amount=100, all=True)):
            before = copy.deepcopy(s)
            with self.assertRaises(GameError, msg=bad):
                act(s, 'jr_san_buy', **bad)
            self.assertEqual(s, before)
        with self.assertRaises(GameError):
            act(s, 'jr_san_sell', a='pho', all=True)
        with patch.object(mw, 'WILD_TICK', self.t + 10):
            with self.assertRaises(GameError):
                act(s, 'jr_san_buy', a='pho', amount=100)

    def test_big_sales_are_split_into_wallet_rows_and_capped(self):
        s = story(10**7 + 100, 10**8)
        s, _ = act(s, 'jr_san_buy', a='heo', amount=10**7)
        h = s['journey']['san']['h']['heo']
        h['u'] *= 30                                    # as if the price had gone up 30×
        h['b'] *= 30
        validate_state(s)
        value = san.value_of(h['u'], mw.price_at('heo', self.t))
        self.assertGreater(value, san.SELL_MAX)
        s2, _ = act(s, 'jr_san_sell', a='heo', all=True)
        rows = [r for r in s2['journey']['history'] if r['label'].startswith('Bán Heo')]
        self.assertTrue(all(abs(r['amount']) <= san.ROW_MAX for r in rows))
        self.assertLessEqual(sum(r['amount'] for r in rows), san.SELL_MAX)
        self.assertGreater(s2['journey']['san']['h']['heo']['u'], 0)       # the rest stays for another order
        s['journey']['wallet'] = 10**9 - 10
        with self.assertRaises(GameError):
            act(s, 'jr_san_sell', a='heo', amount=1000)

    def test_regret_note_tracks_the_peak_since_buying(self):
        s = story(50000)
        s, _ = act(s, 'jr_san_buy', a='caro', amount=20000)
        later = self.t + 3 * D
        with patch.object(rm, 'now', return_value=self.at(later)):
            pub = san.public(s)['hold']['caro']
            peak = max(mw.history('caro', later, later - self.t + 1))    # split-adjusted to now
            self.assertAlmostEqual(pub['peak'], peak, delta=max(1, peak // 10**6))
            self.assertEqual(pub['e'], mw.exp_at('caro', later))
            self.assertEqual(pub['regret'], bool(pub['peak_net'] > pub['basis'] and
                                                  san.value_of(pub['units'], peak) * 100 >= pub['value'] * 110))

    def test_device_fine_sells_holdings_too(self):
        from game import fair_hai
        s = story(30000)
        s, _ = act(s, 'jr_san_buy', a='pmf', amount=20000)
        j = s['journey']
        base = fair_hai.device_base(j)
        self.assertGreaterEqual(base, j['wallet'] + san.net_value(j))
        j['wallet'] = 0
        f = dict(net=0, stats=dict(lost=0))
        taken = fair_hai._take_parked(j, f, 5000, 'Phạt')
        self.assertEqual(taken, 5000)
        self.assertLess(j['san']['h']['pmf']['u'], 20000 * san.SCALE)
        validate_state(s)


class Splits(Market):
    """A new asset far above (below) its launch price is split 1→10 (merged 10→1): price and units change, the
    value and the chart do not."""

    def test_the_engine_splits_and_keeps_the_chart_continuous(self):
        eng = mw.Engine('split', 6000)
        sp = mw.ASSETS['pho']
        eng.advance(6000)
        eng.st['pho']['L'] = math.log(sp['launch'] * mw.SPLIT * 1.5)
        eng.st['heo']['L'] = math.log(mw.ASSETS['heo']['launch'] / mw.SPLIT / 1.5)
        eng.advance(6002)
        self.assertEqual(eng.exp10('pho', 6001), -1)
        self.assertTrue(sp['launch'] <= eng.price('pho', 6001) <= sp['launch'] * 3)
        self.assertEqual(eng.exp10('heo', 6001), 1)
        adj = adjusted(eng, 'pho')                                  # base units: no ÷10 at the split
        self.assertLess(abs(math.log(adj[1] / (sp['launch'] * mw.SPLIT * 1.5))), .5)
        self.assertLess(abs(math.log(adj[2] / adj[1])), .5)
        self.assertTrue(any(ev[2] == 'split' for ev in eng.events))
        self.assertEqual(eng.range_max('pho', 6000, 6001), max(round(eng.price('pho', 6000) / 10), eng.price('pho', 6001)))

    def test_a_split_keeps_every_holding_worth_the_same(self):
        t = START + D
        with patch.object(rm, 'now', return_value=self.at(t)):
            s = story(50000)
            s, _ = act(s, 'jr_san_buy', a='pho', amount=20000)
            h = s['journey']['san']['h']['pho']
            self.assertEqual(h['e'], mw.exp_at('pho', t))
            before, units = san.value(s), h['u']
            price = mw.price_at('pho', t)
            with patch.object(mw, 'exp_at', return_value=h['e'] - 1), patch.object(mw, 'price_at', return_value=price // 10):
                self.assertEqual(san.public(s)['hold']['pho']['units'], units * 10)
                self.assertAlmostEqual(san.value(s), before, delta=before // 1000 + 1)          # the patched price is rounded down
                san.sync(s)
                self.assertEqual((h['u'], h['e']), (units * 10, mw.exp_at('pho', t)))
                validate_state(s)
            h['e'] = 99
            with self.assertRaises(GameError):
                validate_state(s)
            del h['e']                                      # a save from before splits counts in e = 0
            validate_state(s)


    def test_mây_coin_merges_keep_the_old_holding_worth_the_same(self):
        from game import invest as iv
        eng = mw.Engine('split-coin', 6000, {'coin': 11000, 'gold': 650})
        eng.advance(6000)
        eng.st['coin']['L'] = math.log(mw.ASSETS['coin']['launch'] / mw.SPLIT / 1.5)
        eng.advance(6001)
        self.assertEqual(eng.exp10('coin', 6001), 1)                 # Mây Coin under 10 xu: 10→1
        t = START + D
        with patch.object(rm, 'now', return_value=self.at(t)):
            s = story(50000)
            s, _ = iv.action(s, 'iv_buy', {'amount': 10000})
            units, before = s['journey']['invest']['coin']['units'], iv.value(s)
            real = rm.quote

            def merged(a, at=None, **k):
                q = dict(real(a, at, **k))
                if a == 'coin':
                    q['price'], q['e'] = q['price'] * 10, q.get('e', 0) + 1
                    q['history'] = [x * 10 for x in q['history']]
                return q
            with patch.object(rm, 'quote', side_effect=merged):
                self.assertAlmostEqual(iv.value(s), before, delta=2)
                self.assertEqual(iv.public(s)['coin']['units'], units // 10)
                iv.sync_market(s)
                self.assertEqual(s['journey']['invest']['coin']['units'], units // 10)
                self.assertEqual(s['journey'][iv.SPLIT_KEY], mw.exp_at('coin', t) + 1)
                validate_state(s)
                self.assertAlmostEqual(iv.value(s), before, delta=2)
            s['journey'][iv.SPLIT_KEY] = 99
            with self.assertRaises(GameError):
                validate_state(s)


class Delisting(Market):
    salt = 'wild-delist-hunt'

    def test_a_delisted_coin_leaves_holders_nothing_and_lists_again(self):
        found = None
        for k in range(40):
            salt = f'wild-delist-{k}'
            with patch.dict(os.environ, {'MNL_MARKET_SALT': salt}):
                eng = mw.engine(START + 20 * D)
                for a in mw.NEW:
                    if mw.ASSETS[a]['risky'] and 0 in eng.prices[a]:
                        found = (salt, a, START + list(eng.prices[a]).index(0))
                        break
            if found:
                break
        self.assertIsNotNone(found, 'a risky coin should delist now and then')
        salt, a, t0 = found
        with patch.dict(os.environ, {'MNL_MARKET_SALT': salt}):
            self.assertEqual(mw.price_at(a, t0), 0)
            self.assertTrue(mw.board(self.at(t0))['assets'][a]['delisted'])
            relist = t0 + mw.RELIST
            self.assertEqual(mw.price_at(a, relist - 1), 0)
            self.assertEqual(mw.gen_at(a, relist), mw.gen_at(a, t0) + 1)
            self.assertGreater(mw.price_at(a, relist), 0)
            with patch.object(rm, 'now', return_value=self.at(t0 - 2)):
                s = story(50000, 20000)
                s, _ = act(s, 'jr_san_buy', a=a, amount=5000)
            with patch.object(rm, 'now', return_value=self.at(relist + 1)):
                self.assertTrue(san.public(s)['hold'][a]['dead'])
                self.assertEqual(san.value(s), 0)
                notes = []
                san.sync(s, notes)
                self.assertNotIn(a, s['journey']['san']['h'])
                self.assertEqual(s['journey']['san']['st']['lost'], 5000)
                self.assertTrue(notes)
                validate_state(s)
                san.sync(s, notes)                      # once
                self.assertEqual(s['journey']['san']['st']['lost'], 5000)


class Validation(unittest.TestCase):
    def test_unknown_ids_survive_a_rollback_and_bad_rows_do_not(self):
        s = story(1000)
        s['journey']['san'] = dict(v=1, h={'future_coin': dict(u=5, b=10, r=0, f=1, n=1, g=1, t=0)}, log=[],
                                   st=dict(r=0, f=0, n=0, lost=0))
        validate_state(s)
        self.assertEqual(san.value(s), 0)
        self.assertEqual(san.public(s)['hold'], {})
        for bad in (dict(u=0), dict(b=-1), dict(b=10**10), dict(g=0)):
            t = copy.deepcopy(s)
            t['journey']['san']['h']['future_coin'].update(bad)
            with self.assertRaises(GameError):
                validate_state(t)
        t = copy.deepcopy(s)
        t['journey']['san']['h']['Bad Id'] = t['journey']['san']['h'].pop('future_coin')
        with self.assertRaises(GameError):
            validate_state(t)


class Performance(unittest.TestCase):
    def test_a_month_of_market_steps_quickly(self):
        import time
        eng = mw.Engine('perf', 6000)
        started = time.perf_counter()
        eng.advance(6000 + 30 * D)
        self.assertLess(time.perf_counter() - started, 3.0)     # ≈ 0,4 s here: a year ≈ 5 s, once per process


if __name__ == '__main__':
    unittest.main()
