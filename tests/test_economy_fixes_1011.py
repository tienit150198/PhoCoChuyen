"""11/10 economy audit: house resale arbitrage on the property news (game/housing.py value_of, game/property_market.py
salt), the "thiết bị hỗ trợ" fine counting the Mây savings, Mây Coin and gold (game/fair_hai.py device_fine, the
phóng dao payout left past midnight: game/fair.py _kn_settle) and bank interest never past BAL_MAX (game/bank.py)."""
import datetime as dt
import os
import unittest
from unittest import mock

from game import bank as bk
from game import fair as fh
from game import fair_bm as bm
from game import fair_hai as hai
from game import housing as hs
from game import invest as iv
from game import jail
from game import property_market as pm
from game import vang
from game.engine import validate_state
from tests import test_fair as base
from tests.test_bank import act, story as bank_story
from tests.test_fair_knife import safe_taps


def q(bp):
    return dict(multiplier_bp=bp, rent_bp=10000, news=None)


class HouseResale(unittest.TestCase):
    def buy(self, kind, bp):
        s = bank_story(wallet=100_000)
        with mock.patch.object(hs.pm, 'quote', return_value=q(bp)):
            s, r = act(s, 'jr_home_buy', kind=kind, down=hs.HOMES[kind]['price'], confirm=True)
        return s, r['id']

    def test_bought_during_bad_news_never_resells_above_list(self):
        s, hid = self.buy('biet_thu_vuon', 5700)
        j = s['journey']
        self.assertEqual(j['property_market_basis'][hid], 10000)   # the list price was paid: neutral
        own = next(x for x in [j['home']['own']] + j['home']['props'] if x and x['id'] == hid)
        price = own['price']
        for bp, want in ((10000, price), (16500, price * 16500 // 10000 // 10 * 10), (5700, price * 5700 // 10000 // 10 * 10)):
            with mock.patch.object(hs.pm, 'quote', return_value=q(bp)):
                self.assertEqual(hs.value_of(own, own['day'], j['property_market_basis'][hid]), want)
        validate_state(s)

    def test_a_saved_low_basis_reads_as_neutral(self):
        """Homes bought on 2.0.3.5 during bad news kept their low basis: it no longer multiplies the resale."""
        own = dict(price=36000, day=1, kind='biet_thu_vuon')
        with mock.patch.object(hs.pm, 'quote', return_value=q(10000)):
            self.assertEqual(hs.value_of(own, 1, 5700), 36000)       # was 63,150 (1.75×)
        with mock.patch.object(hs.pm, 'quote', return_value=q(16500)):
            self.assertEqual(hs.value_of(own, 1, 5700), 59400)       # was 104,210 (2.9×)

    def test_good_news_purchase_still_no_instant_flip(self):
        s, hid = self.buy('tap_the', 15000)
        j = s['journey']
        self.assertEqual(j['property_market_basis'][hid], 15000)
        own = next(x for x in [j['home']['own']] + j['home']['props'] if x and x['id'] == hid)
        with mock.patch.object(hs.pm, 'quote', return_value=q(15000)):
            self.assertEqual(hs.value_of(own, own['day'], 15000), own['price'])


class PropertySalt(unittest.TestCase):
    def setUp(self):
        pm._window.cache_clear()
        self.addCleanup(pm._window.cache_clear)

    def calendar(self, salt, kind='biet_thu_song', blocks=range(0, 12)):
        with mock.patch.dict(os.environ, {'MNL_PROPERTY_SALT': salt}):
            return [pm.quote(kind, pm.START + dt.timedelta(days=b * pm.WINDOW + d)) for b in blocks for d in range(pm.WINDOW)]

    def test_already_shown_window_is_unchanged(self):
        first = range(0, pm.SALT_FROM_BLOCK)
        old = [pm.quote('biet_thu_song', pm.START + dt.timedelta(days=d)) for d in range(pm.WINDOW * pm.SALT_FROM_BLOCK)]
        self.assertEqual(self.calendar('a' * 32, blocks=first), old)
        self.assertEqual(self.calendar('b' * 32, blocks=first), old)
        for kind in hs.OWN:   # the unsalted seed for every window before the cutover
            for block in first:
                self.assertEqual(pm._window(kind, block, ''), pm._window(kind, block, 'x' * 30))

    def test_later_windows_follow_the_server_secret(self):
        later = range(pm.SALT_FROM_BLOCK, pm.SALT_FROM_BLOCK + 40)
        a, b = self.calendar('a' * 32, blocks=later), self.calendar('b' * 32, blocks=later)
        self.assertNotEqual(a, b)
        self.assertEqual(a, self.calendar('a' * 32, blocks=later))   # shared and stable for one secret
        for x in a:
            self.assertTrue(pm.MIN_BP <= x['multiplier_bp'] <= pm.MAX_BP)

    def test_salt_falls_back_to_the_market_secret(self):
        env = {k: v for k, v in os.environ.items() if k not in ('MNL_PROPERTY_SALT', 'MNL_MARKET_SALT', 'MNL_GOLD_SALT')}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(pm._salt(), 'pho-nha')
            os.environ['MNL_GOLD_SALT'] = 'g' * 30
            self.assertEqual(pm._salt(), 'g' * 30)
            os.environ['MNL_MARKET_SALT'] = 'm' * 30
            self.assertEqual(pm._salt(), 'm' * 30)
            os.environ['MNL_PROPERTY_SALT'] = 'p' * 30
            self.assertEqual(pm._salt(), 'p' * 30)


def rich(wallet=1_000_000, bank=50_000, save=200_000, coin=100_000, gold_phan=200):
    """A story save with money in every pocket the device fine counts."""
    s = base.story(wallet)
    j = s['journey']
    j['stats']['max_wallet'] = max(j['stats']['max_wallet'], wallet)
    j['fair'] = fh.initial()
    j['bank'] = bk.initial(j['seed'], j['life_day'])
    j['bank']['balance'] = bank
    if save:
        iv.apply(s, 'iv_save', {'amount': save})
    if coin:
        iv.apply(s, 'iv_buy', {'amount': coin})
    if gold_phan:
        vang.action(s, 'jr_vang_buy', {'phan': gold_phan})
    validate_state(s)
    return s


def rows_ok(t, s):
    for row in s['journey']['history']:
        t.assertLessEqual(abs(row['amount']), bm.ROW_MAX)


class DeviceFine(unittest.TestCase):
    def test_base_counts_the_parked_money(self):
        s = rich()
        j = s['journey']
        parked = j['invest']['saving']['balance'] + hai._coin_net(j) + vang.value(s)
        self.assertGreater(parked, 0)
        self.assertEqual(hai.device_base(j), bm.total_money(j) + parked)

    def test_parking_no_longer_halves_the_fine(self):
        """The winnings moved into Mây savings, Mây Coin and gold (an empty wallet and bank): half is still taken."""
        s = rich(wallet=600_000, bank=0, save=100_000, coin=200_000, gold_phan=0)
        j = s['journey']
        vang.action(s, 'jr_vang_buy', {'phan': (j['wallet'] - 1000) * vang.PHAN // vang.buy_price(vang.price())})
        j['wallet'] = 0
        f = j['fair']
        phan = j['vang']['phan']
        want = hai.device_base(j) * hai.DEVICE_PCT // 100
        self.assertEqual(bm.total_money(j), 0)   # what the 2.0.3.5 fine counted
        fine = hai.device_fine(None, j, f)
        self.assertLessEqual(abs(fine - want), 2)   # a few xu of a forced sale's rounding may be let go
        self.assertEqual(j['invest']['saving']['balance'], 0)
        self.assertLess(j['vang']['phan'], phan)
        self.assertEqual(f['stats']['lost'], fine)
        validate_state(s)
        rows_ok(self, s)

    def test_wallet_and_bank_first_then_savings_gold_coin(self):
        s = rich(wallet=1_000_000, bank=50_000, save=200_000, coin=100_000, gold_phan=200)
        j = s['journey']
        f = j['fair']
        sv, ph, units = j['invest']['saving']['balance'], j['vang']['phan'], j['invest']['coin']['units']
        want = hai.device_base(j) // 2
        liquid = bm.total_money(j)
        fine = hai.device_fine(None, j, f)
        self.assertLessEqual(abs(fine - want), 2)
        if liquid >= want:
            self.assertEqual((j['invest']['saving']['balance'], j['vang']['phan'], j['invest']['coin']['units']), (sv, ph, units))
        else:
            self.assertEqual((j['wallet'], j['bank']['balance']), (0, 0))
            self.assertEqual(j['invest']['saving']['balance'], max(0, sv - (want - liquid)))
        validate_state(s)
        rows_ok(self, s)

    def test_a_fine_past_the_cash_sells_gold_and_coin(self):
        s = rich(wallet=400_000, bank=0, save=0, coin=150_000, gold_phan=0)
        j = s['journey']
        n = (j['wallet'] - 1000) * vang.PHAN // vang.buy_price(vang.price())
        vang.action(s, 'jr_vang_buy', {'phan': n})
        j['wallet'] = 0
        base_ = hai.device_base(j)
        f = j['fair']
        fine = hai.device_fine(None, j, f)
        self.assertLessEqual(abs(fine - base_ // 2), 2)
        self.assertLess(j['vang']['phan'], n)
        self.assertGreaterEqual(j['wallet'], 0)
        validate_state(s)
        rows_ok(self, s)

    def test_coin_only(self):
        s = rich(wallet=300_000, bank=0, save=0, coin=290_000, gold_phan=0)
        j = s['journey']
        j['wallet'] = 0
        units, net = j['invest']['coin']['units'], hai._coin_net(j)
        fine = hai.device_fine(None, j, j['fair'])
        self.assertLessEqual(abs(fine - net // 2), 2)
        self.assertLess(j['invest']['coin']['units'], units)
        self.assertGreater(j['invest']['coin']['units'], 0)
        self.assertEqual(j['invest']['log'][-1]['kind'], 'sell')
        validate_state(s)
        rows_ok(self, s)

    def test_nothing_parked_is_the_old_fine(self):
        s = rich(wallet=80_000, bank=20_000, save=0, coin=0, gold_phan=0)
        j = s['journey']
        fine = hai.device_fine(None, j, j['fair'])
        self.assertEqual(fine, 50_000)
        self.assertEqual(j['wallet'] + j['bank']['balance'], 50_000)
        validate_state(s)

    def test_the_device_receipt(self):
        s = rich()
        j = s['journey']
        want = hai.device_base(j) // 2
        with self.assertRaises(fh._Caught) as c:
            fh._device(j, j['fair'], base.OPEN, 'oaq', 100, 'Thắng Ông Hai', hai.FINE_LABEL)
        a = c.exception.result['fair']['arrest']
        self.assertLessEqual(abs(a['fine'] - want), 2)
        self.assertEqual(a['jail'], 0 if jail.off() else bm.JAIL_DAYS)
        validate_state(s)


class KnifeSettle(base.FairBase):
    """A phóng dao choice left past midnight is paid by _kn_settle: the device rule applies to it too."""

    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {'MNL_BM_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)

    def pending(self, wallet):
        s = base.story(wallet)
        s['journey']['stats']['max_wallet'] = wallet
        s, _ = self.act(s, 'fair_kn_start', stake=20)
        run = s['journey']['fair_kn']['run']
        sc = fh._kn_sched(run, s['journey'])
        taps = safe_taps(sc, sc['need'])
        self.clock.t += taps[-1] / 1000
        s, _ = self.act(s, 'fair_kn_throw', lv=run['lv'], taps=taps)
        self.assertEqual(s['journey']['fair_kn']['run']['sg'], 'choice')
        self.clock.t += 86400   # the next Vietnam day
        return s

    def test_a_big_prize_paid_at_midnight_is_fined(self):
        s = self.pending(400_000)
        j = s['journey']
        with mock.patch.object(fh.knife, 'prize', return_value=fh.KN_DEVICE_FROM + 50_000):
            fh._kn_settle(s)
        self.assertEqual(j['fair_kn']['run']['sg'], 'done')
        paid = 400_000 - 20 + fh.KN_DEVICE_FROM + 50_000
        self.assertEqual(j['wallet'], paid - paid // 2)
        self.assertTrue(any(r['label'] == fh.KN_DEVICE_LABEL for r in j['history']))
        self.assertNotIn('jail', j)   # before the engine's jail gate: the fine only
        validate_state(s)

    def test_a_small_prize_is_not(self):
        s = self.pending(1000)
        fh._kn_settle(s)
        self.assertEqual(s['journey']['wallet'], 1000 - 20 + s['journey']['fair_kn']['run']['pz'])
        validate_state(s)


class BankCeiling(unittest.TestCase):
    def setUp(self):
        for name, value in (('paid', True), ('forfeited', 0)):
            p = mock.patch.object(bk.ic, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def bank(self):
        s = bank_story(wallet=0)
        j = s['journey']
        j['bank'] = b = bk.initial(j['seed'], j['life_day'])
        return s, b

    def term(self, b, amount, term=30, renew=False):
        t = dict(id='t1', amount=amount, term=term, rate=bk.TERM_RATE[term], start=1, due=1 + term, renew=renew)
        b['terms'].append(t)
        return t

    def tick(self, s, b, n):
        s['journey']['life_day'] = n
        b['day'] = n
        bk._tick(s, b, n, [])
        validate_state(s)

    def test_demand_interest_stops_at_the_ceiling(self):
        s, b = self.bank()
        b['demand'] = bk.BAL_MAX - 3
        self.tick(s, b, 2)
        self.assertEqual(b['demand'], bk.BAL_MAX)
        self.tick(s, b, 3)
        self.assertEqual(b['demand'], bk.BAL_MAX)

    def test_a_maturing_term_waits_when_the_account_is_full(self):
        s, b = self.bank()
        b['balance'] = bk.BAL_MAX - 1000
        self.term(b, 500_000)
        self.tick(s, b, 31)
        self.assertEqual((len(b['terms']), b['balance']), (1, bk.BAL_MAX - 1000))
        b['balance'] = 0   # room again: it pays out in full
        self.tick(s, b, 32)
        self.assertEqual(b['terms'], [])
        self.assertEqual(b['balance'], 500_000 + bk.term_interest(500_000, bk.TERM_RATE[30], 30))

    def test_interest_that_does_not_fit_is_not_paid(self):
        s, b = self.bank()
        b['balance'] = bk.BAL_MAX - 500_010
        self.term(b, 500_000)
        self.tick(s, b, 31)
        self.assertEqual((b['terms'], b['balance']), ([], bk.BAL_MAX))

    def test_a_renewed_term_keeps_what_the_account_cannot_hold(self):
        s, b = self.bank()
        b['balance'] = bk.BAL_MAX - 1000
        self.term(b, 50_000_000, renew=True)
        self.tick(s, b, 31)
        self.assertEqual(b['balance'], bk.BAL_MAX)
        self.assertEqual(b['terms'][0]['amount'], 50_000_000 - 1000)

    def test_rates_are_unchanged_below_the_ceiling(self):
        s, b = self.bank()
        self.term(b, 20_000_000, renew=True)
        self.tick(s, b, 31)
        gain = bk.term_interest(20_000_000, bk.TERM_RATE[30], 30)
        self.assertEqual(b['balance'], 20_000_000 - bk.RENEW_MAX + gain)
        self.assertEqual(b['terms'][0]['amount'], bk.RENEW_MAX)


if __name__ == '__main__':
    unittest.main()
