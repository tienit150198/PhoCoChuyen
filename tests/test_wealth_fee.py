"""🏛️ Phí giữ tài sản lớn (game/wealth_fee.py) and 🏬 the counter chain's tax and rent (game/quay_business.py, owner 18/10)."""
import unittest

from game import wealth_fee as wf
from game import quay_business as qb
from game.engine import new_state, validate_state


def story(wallet):
    s = new_state()
    s['journey']['story'] = True   # the fee is for the story journey; free play has none
    s['journey']['wallet'] = wallet
    return s


class Fee(unittest.TestCase):
    def test_daily_ladder(self):
        self.assertEqual(wf.daily(30_000_000), 0)
        self.assertEqual(wf.daily(40_000_000), 50_000)              # 0.5 % of 10M
        self.assertEqual(wf.daily(100_000_000), 350_000)            # 0.5 % of 70M
        self.assertEqual(wf.daily(132_000_000), 350_000 + 320_000)  # + 1 % of 32M

    def test_once_a_day_from_the_wallet_never_a_debt(self):
        s = story(50_000_000); j = s['journey']
        day = wf.today(1_800_000_000)
        self.assertTrue(wf.settle(s, 1_800_000_000))
        self.assertEqual(j['wallet'], 50_000_000 - 100_000)
        self.assertEqual(j[wf.KEY], dict(d=day, paid=100_000, last=100_000))
        self.assertFalse(wf.settle(s, 1_800_000_000 + 60))           # same day: nothing more
        self.assertEqual(j['history'][-1]['label'], wf.LABEL)
        wf.settle(s, 1_800_000_000 + 10 * 86400)                     # ten days away: at most MAX_DAYS
        self.assertEqual(j[wf.KEY]['last'], wf.daily(49_900_000) * wf.MAX_DAYS)
        validate_state(s)

    def test_poor_players_carry_nothing(self):
        s = story(1_000_000)
        self.assertFalse(wf.settle(s, 1_800_000_000))
        self.assertNotIn(wf.KEY, s['journey'])


    def test_kill_switch(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {'MNL_WEALTH_FEE_OFF': '1'}):
            self.assertTrue(wf.off())
        with mock.patch.dict(os.environ, {'MNL_WEALTH_FEE_OFF': ''}):
            self.assertFalse(wf.off())


class Chain(unittest.TestCase):
    def test_tax_and_rent_grow_with_the_chain(self):
        self.assertEqual([qb.chain_tax(n) for n in (1, 5, 6, 10, 11, 20, 21, 30, 31, 50, 51, 64)],
                         [0, 0, 2, 2, 5, 5, 10, 10, 15, 15, 20, 20])
        st = dict(place='kiot', staff=[], business=dict())
        base = qb._rates(st)['rent']
        token = qb._CHAIN.set(64)
        try:
            self.assertEqual(qb._rates(st)['rent'], base * 64 // 10)
            self.assertEqual(qb.tax_percent(), 7 + 20)
        finally:
            qb._CHAIN.reset(token)
        self.assertEqual(qb.tax_percent(), 7)


if __name__ == '__main__':
    unittest.main()
