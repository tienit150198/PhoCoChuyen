"""F#232 / F#220: stall staff sell only the board. A new counter's board is the whole trade; restocking a dish off the
board turns it on; the 📦 tab's "Bật ở Menu" can add dishes while you stand at the counter. 💼 Góp vốn: wallet, then bank."""
import copy
import unittest
from unittest.mock import patch

from game import quay as qy, quay_business as qb, quay_self as qs
from game.engine import validate_state
from tests.test_quay import ST, act, opened, owner, refused
from tests.test_quay_business import fixture


class BoardAndStock(unittest.TestCase):
    def test_new_counter_board_is_the_whole_trade_and_staff_sell_every_stocked_dish(self):
        s = opened('kiot', wallet=20000)
        st = ST(s)
        self.assertEqual(st['menu']['on'], [d[0] for d in qs.MENUS[st['trade']]][:qs.MENU_MAX])
        self.assertEqual(len(st['menu']['on']), 12)
        validate_state(s)
        now = st['business']['cursor'] / 1000
        st['business']['stock'] = {d: 50 for d in qs.DISH[st['trade']]}
        st['fund'] = 10**6
        qb.settle(s, now=now + 4 * 3600)
        sold = {row['dish'] for row in st['business']['recent']}
        self.assertGreater(len(sold), 3)            # not only the first three dishes (Áo thun / Quần jean / Váy) any more
        self.assertTrue(sold - {d[0] for d in qs.MENUS[st['trade']][:3]})

    def test_full_board_sells_one_at_a_time_at_the_same_rate(self):
        s, st = fixture(place='xe', trade='clothing')
        qb.settle(s, now=1000)
        three = copy.deepcopy(s)
        st['menu'] = qs.default_menu('clothing')
        st['business']['stock'] = {d: 500 for d in qs.DISH['clothing']}
        ST3 = three['journey']['quay']['stalls'][0]
        ST3['business']['stock'] = {d: 2000 for d in qs.menu(ST3)['on']}
        qb.settle(s, now=1001)
        qb.settle(three, now=1001)
        arrivals = sorted(st['business']['arrivals'].values())
        self.assertEqual(len(set(arrivals)), 12)    # staggered: twelve different first arrivals, not one burst
        day = 1001 + 24 * 3600
        qb.settle(s, now=day)
        qb.settle(three, now=day)
        a, b = st['business']['sold'], ST3['business']['sold']
        self.assertLessEqual(abs(a - b), 12)        # the same throughput over a day (within one round)

    def test_old_counter_keeps_its_board_until_a_restock_turns_the_dish_on(self):
        s = opened('xe', staff=False)
        st = ST(s)
        st.pop('menu')                              # a counter from before 1.9.10 that never saved a board
        sid = st['id']
        s, _ = act(s, 'jr_quay_menu', stall=sid, on=['ts_tran_chau', 'hong_tra', 'tra_dao'], p={'hong_tra': 12})
        before = copy.deepcopy(ST(s)['menu'])
        validate_state(s)
        s, r = act(s, 'jr_quay_restock', stall=sid, items={'matcha': 3, 'hong_tra': 2})
        m = ST(s)['menu']
        self.assertEqual(m['on'], ['ts_tran_chau', 'hong_tra', 'tra_dao', 'matcha'])   # trade order
        self.assertEqual(m['p'], before['p'])                                          # prices kept
        self.assertIn('Đã bật ở Menu: Matcha latte', r['message'])
        s, r = act(s, 'jr_quay_restock', stall=sid, items={'matcha': 1})
        self.assertNotIn('Menu', r['message'])
        validate_state(s)

    def test_one_tap_turns_stocked_dishes_on_even_while_standing_at_the_counter(self):
        s = opened('xe', staff=False)
        st = ST(s)
        st['menu'] = dict(on=['ts_tran_chau', 'hong_tra', 'tra_dao'], p={'tra_dao': 15})
        sid = st['id']
        s, _ = act(s, 'jr_quay_start', stall=sid)
        self.assertTrue(ST(s)['run']['continuous'])
        refused(self, s, 'jr_quay_menu', 'busy', stall=sid, on=['ts_tran_chau', 'hong_tra'])                # removing: no
        refused(self, s, 'jr_quay_menu', 'busy', stall=sid, on=['ts_tran_chau', 'hong_tra', 'tra_dao', 'matcha'],
                p={'matcha': 20})                                                                          # repricing: no
        s, _ = act(s, 'jr_quay_menu', stall=sid, on=['ts_tran_chau', 'hong_tra', 'tra_dao', 'matcha', 'olong'])
        self.assertEqual(ST(s)['menu'], dict(on=['ts_tran_chau', 'hong_tra', 'tra_dao', 'matcha', 'olong'], p={'tra_dao': 15}))
        validate_state(s)

    def test_old_style_run_keeps_its_board(self):
        s, st = fixture()
        qb.settle(s, now=1000)
        st['menu'] = dict(on=['hong_tra'], p={})
        st['run'] = dict(d=s['journey']['life_day'], x=False)       # a pre-continuous run: walk-ins drawn at the start
        self.assertTrue(qs.board_locked(st, s['journey']['life_day']))
        with patch.object(qb.time, 'time', return_value=1000):
            r = qy.action(s, 'jr_quay_restock', dict(stall='q1', items={'matcha': 2}))
        self.assertEqual(st['menu']['on'], ['hong_tra'])
        self.assertNotIn('Menu', r['message'])
        st['run'] = None
        self.assertEqual(qs.turn_on(st, ['matcha', 'olong']), ['matcha', 'olong'])
        self.assertEqual(qs.turn_on(st, ['matcha']), [])


class FundFromBank(unittest.TestCase):
    def counter(self):
        s = owner(5000)
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_quay_open', trade='milk_tea', place='xe', confirm=True)
        s['journey']['bank']['balance'] = 700
        s['journey']['wallet'] = 100
        validate_state(s)
        return s, ST(s)['id']

    def test_wallet_first_then_the_bank_account(self):
        s, sid = self.counter()
        fund = ST(s)['fund']
        s, r = act(s, 'jr_quay_fund', stall=sid, amount=500)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 300)
        self.assertEqual(ST(s)['fund'], fund + 500)
        self.assertIn('500', r['message'])
        validate_state(s)

    def test_never_into_debt(self):
        s, sid = self.counter()
        refused(self, s, 'jr_quay_fund', 'no_money', stall=sid, amount=801)
        s['journey']['wallet'] = -5
        refused(self, s, 'jr_quay_fund', 'in_debt', stall=sid, amount=10)
        s['journey']['wallet'] = 100
        s, _ = act(s, 'jr_quay_fund', stall=sid, amount=800)
        self.assertEqual((s['journey']['wallet'], s['journey']['bank']['balance']), (0, 0))


if __name__ == '__main__':
    unittest.main()
