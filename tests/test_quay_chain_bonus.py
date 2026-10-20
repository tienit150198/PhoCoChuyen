"""🌸 Chuỗi quầy (owner 21/10, "quầy hoa" sold at ~half from 20/10): the chain's extra rent, power and tax points are paid
at face value but never shrink the staff profit bonus, and rent / power stop growing at RENT_MAX / POWER_MAX counters.

2.4.71 (the numbers this file guards against), one florist ki-ốt selling lan at 25 xu, normal speed, one real day:
the owner's take was 168,780 xu before 20/10 and 100,438 / 56,652 / -25,911 xu in a chain of 21 / 31 / 64 counters
(each xu of extra rent or power also took 2.36 xu of bonus away)."""
import unittest
from unittest import mock

from game import quay_business as qb, quay_self as qs
from game.engine import GameError
from game.quay import _int
from tests.test_quay import bare

T0 = 1_760_000_000


def day(trade='florist', place='kiot', n=1, chain=True, menu=None):
    """One real day of staff sales at one counter of an n-counter chain: (owner's take after goods, bonus, stall)."""
    s, st = bare(place, trade)
    st['menu'] = menu or qs.default_menu(trade)
    s['journey']['quay'] = dict(v=1, seq=1, stalls=[st], shift=None, out=[])
    with mock.patch('game.wealth_fee.START_TS', 0 if chain else 10**12), mock.patch.object(qb, 'chain_of', lambda s: n):
        qb.settle(s, now=T0)
        b = st['business']
        b['stock'] = {d: 20000 // len(qs.menu(st)['on']) for d in qs.menu(st)['on']}
        b['halted'] = -1
        cash, stock, boost = st['till'] + st['fund'], dict(b['stock']), b['profit_boost']['total']
        qb.settle(s, now=T0 + 86400)
    goods = sum((k - b['stock'][d]) * qb.unit_cost(st, d) for d, k in stock.items())
    return st['till'] + st['fund'] - cash - goods, b['profit_boost']['total'] - boost, st


def valid(st):
    def need(ok):
        if not ok:
            raise GameError('bad', 'invalid_save')
    qb.validate(st, need, _int)


class ChainBonus(unittest.TestCase):
    def test_rent_and_power_stop_growing(self):
        st = dict(place='kiot', staff=[], business=dict())
        base = qb._rates(st, chain=1)
        for n, rent, power in ((5, 70, 15), (10, 70, 30), (11, 77, 30), (15, 105, 30), (64, 105, 30), (200, 105, 30)):
            token = qb._CHAIN.set(n)
            try:
                self.assertEqual((qb._rates(st)['rent'], qb._rates(st)['power']), (rent, power), n)
            finally:
                qb._CHAIN.reset(token)
        self.assertEqual((base['rent'], base['power']), (70, 15))
        self.assertEqual([qb.rent_x(n) / qb.RENT_FREE for n in (1, 10, 12, 15, 64)], [1, 1, 1.2, 1.5, 1.5])
        self.assertEqual([qb.power_x(n) / qb.POWER_FREE for n in (1, 5, 8, 10, 64)], [1, 1, 1.6, 2, 2])

    def test_tax_splits_base_and_chain_with_their_own_carries(self):
        s, st = bare('kiot', 'florist')
        s['journey']['quay'] = dict(v=1, seq=1, stalls=[st], shift=None, out=[])
        qb.settle(s, now=T0)
        b = st['business']
        token = qb._CHAIN.set(64)
        try:
            parts = [qb.income_tax_parts(st, 3, 0) for _ in range(100)]   # 3 xu of margin a receipt, 100 receipts
        finally:
            qb._CHAIN.reset(token)
        self.assertEqual(sum(p[0] for p in parts), 300 * 7 // 100)      # 21: the base 7 %, nothing rounded away
        self.assertEqual(sum(p[1] for p in parts), 300 * 20 // 100)     # 60: the chain's 20 points
        self.assertEqual(b['expenses']['income_tax'], 81)
        self.assertEqual(b['chain_carry']['tax'], 0)
        valid(st)

    def test_small_chain_unchanged_and_writes_nothing_new(self):
        take, bonus, st = day(n=5)
        self.assertEqual((take, bonus), day(n=5, chain=False)[:2])
        self.assertNotIn('chain_carry', st['business'])

    def test_chain_bonus_is_the_pre_chain_bonus(self):
        for n in (6, 11, 31, 64):
            take, bonus, st = day(n=n)
            before, before_bonus, _ = day(n=n, chain=False)
            self.assertEqual(bonus, before_bonus, n)          # the chain's costs never shrink the bonus
            self.assertLess(take, before, n)                  # but they are paid
            self.assertGreaterEqual(take, before * 85 // 100, n)
            valid(st)

    def test_lan_kiosk_numbers(self):
        """The case of the report (2.4.71: 100,438 / 56,652 / -25,911 at 21 / 31 / 64 counters)."""
        lan = dict(on=['lan'], p={'lan': 25})
        before = day(n=64, chain=False, menu=lan)[0]
        self.assertEqual(before, 168780)
        for n in (21, 31, 64):
            self.assertGreaterEqual(day(n=n, menu=lan)[0], before * 88 // 100, n)

    def test_no_trade_or_place_falls_under_seventy_percent(self):
        for trade in qs.DISH:
            for place in ('xe', 'kiot'):
                before, after = day(trade, place, 64, chain=False)[0], day(trade, place, 64)[0]
                self.assertGreater(before, 0, (trade, place))
                self.assertGreaterEqual(after, before * 70 // 100, (trade, place, before, after))

    def test_chain_carry_validation(self):
        _, _, st = day(n=64)
        b = st['business']
        self.assertTrue(set(b['chain_carry']) <= {'rent', 'power', 'tax'})
        valid(st)
        for bad in ({'x': 1}, {'tax': 100}, {'rent': qb.DEN}, {'power': -1}, []):
            b['chain_carry'] = bad
            with self.assertRaises(GameError):
                valid(st)
        del b['chain_carry']
        valid(st)


if __name__ == '__main__':
    unittest.main()
