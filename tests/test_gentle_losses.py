"""Forced fines and thefts stay small, local, and safe for existing saves."""
import copy
import unittest
from unittest.mock import patch

from game import bank, incidents, invest, live_effects, mishap, quay_economy, rui, shop_events
from tests.test_incidents import open_day, fire, choose, set_money
from tests.test_quay_economy import Economy
from tests.test_rui import grown, R


def limit(cash, fine=False):
    return min(cash * (2 if fine else 1) // 100, 2000 if fine else 1000, max(0, cash - 100))


class GentleLosses(unittest.TestCase):
    def test_mishaps_are_capped_on_only_the_affected_pocket(self):
        for cash in (0, 1, 99, 100, 101, 1000, 1000000):
            for sub in mishap.SUBS:
                with self.subTest(cash=cash, sub=sub):
                    s = grown(wallet=cash, bank=cash, day=40)
                    b = bank.get(s)
                    b['demand'] = 10000000
                    b['terms'] = [dict(amount=10000000, start=1, term=180)]
                    j = s['journey']
                    j['invest'] = invest.initial(j['seed'], j['life_day'])
                    j['invest']['saving'].update(balance=10000000, pending=12)
                    j['invest']['coin'].update(units=10000000, basis=10000000)
                    savings, funds = copy.deepcopy((b['demand'], b['terms'], j['invest'])), copy.deepcopy(s['careers'])
                    p = dict(sub=sub)
                    mishap.apply_fx(s, p, 10**9)
                    expected = limit(cash, sub == 'police')
                    self.assertEqual(p['_taken'], expected)
                    self.assertEqual(j['wallet'], cash - (expected if sub in ('police', 'thug') else 0))
                    self.assertEqual(b['balance'], cash - (expected if sub not in ('police', 'thug') else 0))
                    self.assertEqual((b['demand'], b['terms'], j['invest']), savings)
                    self.assertEqual(s['careers'], funds)

    def test_mishap_gear_reduces_the_capped_amount(self):
        s = grown(wallet=1000, bank=1000, day=40)
        R(s)['gear'] = ['diet_virus']
        p = dict(sub='hack')
        mishap.apply_fx(s, p, 10**9)
        self.assertEqual(p['_taken'], 5)

    def test_live_rows_are_bounded_separately_and_replays_do_not_charge(self):
        s = grown(wallet=1000, bank=1000, day=40)
        p = dict(id='mishap-safe-1', kind='mishap', amount=10**9, sub='police')
        s, first = live_effects.apply(s, p)
        s, replay = live_effects.apply(s, p)
        self.assertEqual(first['live']['taken'], 20)
        self.assertTrue(replay['live']['already'])
        s, second = live_effects.apply(s, dict(p, id='mishap-safe-2'))
        self.assertEqual(second['live']['taken'], 19)
        self.assertEqual(s['journey']['wallet'], 961)
        self.assertEqual(bank.get(s)['balance'], 1000)

    def test_saved_quotes_and_legacy_security_losses_are_small(self):
        s = grown(wallet=1000, bank=900, day=40)
        r = R(s)
        for kind, expected in (('hack', 9), ('trom', 10)):
            q = dict(kind=kind, wealth=100000000, percent=20)
            self.assertEqual(rui._security_loss(s, r, q, 41), expected)
            self.assertEqual(rui._projected(s, r, kind, 'vi', None), expected)
        r['gear'] = ['diet_virus', 'ket']
        self.assertEqual(rui._security_loss(s, r, dict(kind='hack', wealth=10**8, percent=20), 41), 4)
        self.assertEqual(rui._theft(s, r, 'trom'), 2)

    def test_saved_parking_fine_never_drains_bank(self):
        for choice in ('nop', 'xin'):
            s = grown(wallet=1000, bank=10000000, day=40)
            r = R(s)
            r['card'] = dict(id='r1', kind='phat', sub='', ref=None, day=40, cost=10**8, loss=0, cover=0)
            self.assertEqual(rui.options(s, r)[0]['cost'], 20)
            with patch.object(rui, '_rng') as rng:
                rng.return_value.randint.return_value = 100
                rui._resolve(s, r, choice, 40)
            self.assertEqual(s['journey']['wallet'], 980)
            self.assertEqual(bank.get(s)['balance'], 10000000)

    def test_shop_saved_quotes_and_small_pockets_keep_reserve_and_gear(self):
        for cash in (0, 1, 99, 100, 101, 1000, 1000000):
            for kind, cid in (('theft', 'record'), ('fake_transfer', 'trust'), ('traffic_inspection', 'fine')):
                x = next(x for x in shop_events.CATALOGUE[kind]['choices'] if x['id'] == cid)
                maximum = limit(cash, kind == 'traffic_inspection')
                loss = shop_events._cost(x, cash, kind, wealth=10**8, percent=20 if kind == 'theft' else None)
                self.assertLessEqual(loss, maximum)
        x = shop_events.CATALOGUE['theft']['choices'][1]
        self.assertEqual(shop_events._cost(x, 1000000, 'theft', ['ket'], wealth=10**8, percent=20), 500)

    def test_period_theft_is_small_and_local(self):
        for event in ('theft', 'robbery', 'police_check'):
            s, st = Economy().sample()
            st.update(till=1000, fund=1000000)
            st['hist'] = [dict(d=1, n=1, rev=100000, net=100000, w='am', p='normal')]
            quay_economy.config(st)['invoices'] = False
            with patch.object(quay_economy, '_event', return_value=event):
                quay_economy.settle(s, st, 1)
            self.assertLessEqual(st['hist'][-1]['costs']['incident'], limit(1000, event == 'police_check'))

    def test_incident_fine_and_extortion_do_not_fall_back_to_wallet(self):
        for script, option, fine in (('noise_fine', 'pay', True), ('racket_again', 'pay', False)):
            s = open_day('milk_tea')
            s['journey']['wallet'] = 10000000
            c = s['careers']['milk_tea']
            set_money(c, 1000)
            row = fire(s, 'milk_tea', script)
            if 'percent' in row:
                row.update(wealth=10**8, percent=20)
            s, _ = choose(s, 'milk_tea', option)
            self.assertEqual(s['careers']['milk_tea']['money'], 1000-limit(1000, fine))
            self.assertEqual(s['journey']['wallet'], 10000000)

    def test_multiple_penalty_lines_share_one_incident_cap(self):
        s = open_day('milk_tea')
        c = s['careers']['milk_tea']
        set_money(c, 1000)
        rows = incidents._pay(s, c, 'milk_tea', [('fund', -1000000, 'fine')] * 3, 'Fine', 'gentle-test')
        self.assertEqual(-sum(x['amount'] for x in rows), 20)
        self.assertEqual(c['money'], 980)


if __name__ == '__main__':
    unittest.main()
