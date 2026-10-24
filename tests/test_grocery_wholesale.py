"""📦 Tạp hóa: newer goods by career level and wholesale customers (feedback #373)."""
import copy
import json
import os
import unittest
from unittest import mock

import game.careers.kit as kit
from game import inventory
from game.engine import GameError, public_state, validate_state
from game.careers import grocery as G
from tests.helpers import Journey


def shop(day=5, level=5):
    """A started shop on `day` at career `level` (morning count done, no surprise in the way)."""
    j = Journey('grocery')
    j.c['xp'] = 90 * (level - 1)
    j.c['day'] = day
    G.on_start(j.state, j.c)
    j.c['ext']['data']['desk'] = kit.desk_initial()
    return j


def ws(j):
    return j.c['ext']['data']['ws']


def offer(j):
    return next(o for o in ws(j)['orders'] if o['state'] == 'offer' and o['day'] == j.c['day'])


def stock_for(j, o, short=None):
    for k, q in o['lines'].items():
        have = kit.stock(j.c, k)
        want = q if k != short else max(0, q - 3)
        if have > want:
            kit.take(j.c, k, have - want)
        elif have < want:
            inventory.add_lot(j.c, k, want - have, G.ITEM_INDEX[k]['cost'], 999, 'partner')


def next_day(j):
    j.act('end_day', carry_event=True)
    j.act('start_day')
    j.c['ext']['data']['desk'] = kit.desk_initial()


def roundtrip(j):
    validate_state(json.loads(json.dumps(j.state)))


class GroceryWholesaleTests(unittest.TestCase):
    def test_locked_below_the_level(self):
        j = shop(level=2)
        self.assertNotIn('ws', j.c['ext']['data'])
        view = public_state(j.state)['careers']['grocery']['data']['ws_view']
        self.assertFalse(view['on'])
        self.assertEqual(view['unlock'], G.WS_LEVEL)
        self.assertTrue(all(not g['open'] for g in view['goods']))
        self.assertNotIn('ws', public_state(j.state)['careers']['grocery']['data'])
        roundtrip(j)

    def test_new_goods_are_locked_in_the_stock_room_until_their_level(self):
        for k in G.NEW_GOODS:
            it = G.ITEM_INDEX[k]
            self.assertGreaterEqual(it['unlock'], G.WS_LEVEL)
            self.assertEqual(it['start'], 0)
            self.assertIn(k, G.PRICES)
            self.assertGreater(G.PRICES[k], it['cost'])
        whole = inventory.supplier('grocery', 'wholesale')
        self.assertTrue(all(inventory.sells(whole, k) for k in G.NEW_GOODS))
        # every account only orders goods open at its own level
        for a in G.WS_ACCOUNTS:
            self.assertTrue(all(G.ITEM_INDEX[k].get('unlock', 1) <= a['lvl'] for k, _ in a['lines']), a['id'])
            self.assertTrue(all(q <= 60 for _, q in a['lines']))

    def test_offer_take_and_deliver_on_the_due_day(self):
        j = shop()
        o = offer(j)
        self.assertEqual(o['due'], j.c['day'] + 1)
        self.assertEqual(o['value'], G._ws_value(o['lines'], o['off']))
        self.assertLess(o['value'], sum(G.PRICES[k] * q for k, q in o['lines'].items()))   # a wholesale discount
        money = j.c['money']
        j.act('gr_ws_take', order=o['id'])
        self.assertEqual(j.c['money'] - money, o['deposit'])
        self.assertEqual(j.act('gr_ws_take', order=o['id'])['message'][:7], 'Đã nhận')   # the same tap again: nothing more
        self.assertEqual(j.c['money'] - money, o['deposit'])
        stock_for(j, o)
        with self.assertRaises(GameError) as e:
            j.act('gr_ws_deliver', order=o['id'], confirm=True)                       # pre-order: not before its day
        self.assertIn(f'ngày {o["due"]}', e.exception.message)
        roundtrip(j)
        next_day(j)
        stock_for(j, o)
        acc, trust = o['acc'], ws(j)['trust'][o['acc']]
        money = j.c['money']
        r = j.act('gr_ws_deliver', order=o['id'], confirm=True)
        self.assertTrue(r.get('celebrate'))
        self.assertEqual(j.c['money'] - money, o['value'] - o['deposit'])
        self.assertEqual(ws(j)['trust'][acc], trust + 1)
        done = next(x for x in ws(j)['orders'] if x['id'] == o['id'])
        self.assertEqual((done['state'], done['paid'], done['got']), ('done', o['value'], o['lines']))
        self.assertTrue(all(kit.stock(j.c, k) == 0 for k in o['lines']))
        roundtrip(j)

    def test_short_stock_needs_partial_and_costs_trust(self):
        j = shop()
        o = offer(j)
        j.act('gr_ws_take', order=o['id'])
        next_day(j)
        short = next(iter(o['lines']))
        stock_for(j, o, short=short)
        with self.assertRaises(GameError) as e:
            j.act('gr_ws_deliver', order=o['id'], confirm=True)
        self.assertIn('Chưa đủ hàng', e.exception.message)
        trust = ws(j)['trust'][o['acc']]
        j.act('gr_ws_deliver', order=o['id'], confirm=True, partial=True)
        done = next(x for x in ws(j)['orders'] if x['id'] == o['id'])
        self.assertEqual(done['got'][short], o['lines'][short] - 3)
        self.assertEqual(done['paid'], G._ws_value(done['got'], o['off']))
        self.assertEqual(ws(j)['trust'][o['acc']], max(1, trust - 1))
        roundtrip(j)

    def test_missed_delivery_refunds_the_deposit_and_costs_two(self):
        j = shop()
        o = offer(j)
        j.act('gr_ws_take', order=o['id'])
        trust = ws(j)['trust'][o['acc']]
        next_day(j)
        money = j.c['money']
        summary = j.act('end_day', carry_event=True)['summary']
        self.assertTrue(any('hoàn cọc' in x for x in summary['career']['lines']))
        missed = next(x for x in ws(j)['orders'] if x['id'] == o['id'])
        self.assertEqual(missed['state'], 'missed')
        self.assertEqual(ws(j)['missed'], 1)
        refunds = [e for e in j.c['ops']['finance']['ledger'] if e['ref'] == o['id'] and e['amount'] < 0]
        self.assertEqual(-sum(e['amount'] for e in refunds), o['deposit'])
        self.assertEqual(ws(j)['trust'][o['acc']], trust - 2)
        roundtrip(j)

    @mock.patch.dict(os.environ, {'MNL_INCOME_BOOST_OFF': '0'})
    def test_the_income_boost_counts_a_deposit_only_once_it_is_earned(self):
        from game import income_boost as ib

        def boosted(j):
            return sum(e['amount'] for e in j.c['ops']['finance']['ledger'] if e['ref'] == ib.REF)
        for deliver in (False, True):
            j = shop()
            j.state['journey']['story'] = True
            o = offer(j)
            money, b0 = j.c['money'], boosted(j)
            j.act('gr_ws_take', order=o['id'])
            self.assertEqual((j.c['money'] - money, boosted(j) - b0), (o['deposit'], 0))   # not earned yet: no +50%
            next_day(j)
            if deliver:
                stock_for(j, o)
                b0 = boosted(j)
                j.act('gr_ws_deliver', order=o['id'], confirm=True)
                self.assertGreater(boosted(j) - b0, o['value'] // 3)   # the whole order's share, deposit included
            else:
                money, b0 = j.c['money'], boosted(j)
                j.act('end_day', carry_event=True)                     # missed: the deposit goes back, nothing kept
                refunds = [e for e in j.c['ops']['finance']['ledger'] if e['ref'] == o['id'] and e['amount'] < 0]
                self.assertEqual(-sum(e['amount'] for e in refunds), o['deposit'])
                self.assertEqual(sum(e['amount'] for e in j.c['ops']['finance']['ledger'] if e['ref'] == o['id']), 0)

    def test_trust_at_zero_pauses_the_account(self):
        j = shop()
        o = offer(j)
        ws(j)['trust'][o['acc']] = 1
        j.act('gr_ws_take', order=o['id'])
        next_day(j)
        j.act('end_day', carry_event=True)
        self.assertEqual(ws(j)['pause'][o['acc']], j.c['day'] - 1 + G.WS_PAUSE)   # counted from the closing day
        self.assertEqual(ws(j)['trust'][o['acc']], 1)
        view = public_state(j.state)['careers']['grocery']['data']['ws_view']
        acc = next(a for a in view['accounts'] if a['id'] == o['acc'])
        self.assertEqual(acc['pause'], G.WS_PAUSE - 1)
        roundtrip(j)

    def test_skipped_and_untaken_offers_lapse_without_a_penalty(self):
        j = shop()
        o = offer(j)
        trust = dict(ws(j)['trust'])
        j.act('gr_ws_skip', order=o['id'])
        with self.assertRaises(GameError):
            j.act('gr_ws_take', order=o['id'])
        next_day(j)
        self.assertEqual(ws(j)['trust'], trust)
        o2 = offer(j)
        next_day(j)
        lapsed = next(x for x in ws(j)['orders'] if x['id'] == o2['id'])
        self.assertEqual(lapsed['state'], 'expired')
        with self.assertRaises(GameError):
            j.act('gr_ws_take', order=o2['id'])
        self.assertEqual(ws(j)['trust'], trust)
        roundtrip(j)

    def test_two_offers_from_level_six_and_bigger_orders_with_trust(self):
        j = shop(level=6)
        self.assertEqual(len([o for o in ws(j)['orders'] if o['day'] == j.c['day']]), 2)
        accs = [a['id'] for a in G.WS_ACCOUNTS if a['lvl'] <= 6]
        self.assertTrue(all(o['acc'] in accs for o in ws(j)['orders']))
        a = G.WS_ACCOUNTS[0]
        small = {k: max(1, min(60, q * G.WS_SIZE[1] * 100 // 10000)) for k, q in a['lines']}
        big = {k: max(1, min(60, q * G.WS_SIZE[5] * 100 // 10000)) for k, q in a['lines']}
        self.assertGreater(sum(big.values()), sum(small.values()))

    def test_walk_ins_buy_only_unlocked_new_goods(self):
        j = shop(level=4)
        for k in G.NEW_GOODS:
            inventory.add_lot(j.c, k, 10, G.ITEM_INDEX[k]['cost'], 999, 'partner')
        money = j.c['money']
        summary = j.act('end_day', carry_event=True)['summary']
        line = next(x for x in summary['career']['lines'] if x.startswith('🆕'))
        self.assertIn('gói đường', line)
        sold = {k: 10 - kit.stock(j.c, k) for k in G.NEW_GOODS}
        self.assertTrue(all(sold[k] == 0 for k in G.NEW_GOODS if G.ITEM_INDEX[k]['unlock'] > 4))
        self.assertTrue(all(1 <= sold[k] <= 4 for k in G.NEW_GOODS if G.ITEM_INDEX[k]['unlock'] <= 4))
        got = [e for e in j.c['ops']['finance']['ledger'] if e['ref'] == f'walk-{j.c["day"] - 1}']
        self.assertEqual(sum(e['amount'] for e in got), sum(sold[k] * G.PRICES[k] for k in G.NEW_GOODS))
        self.assertGreater(j.c['money'], money - 10**6)
        roundtrip(j)

    def test_view_care_and_forecast(self):
        j = shop()
        o = offer(j)
        data = public_state(j.state)['careers']['grocery']['data']
        row = next(r for r in data['ws_view']['orders'] if r['id'] == o['id'])
        self.assertEqual((row['state'], row['can'], row['deposit']), ('offer', None, o['deposit']))
        self.assertTrue(any(r['icon'] == '📦' for r in data['care']))
        j.act('gr_ws_take', order=o['id'])
        data = public_state(j.state)['careers']['grocery']['data']
        self.assertEqual(next(r for r in data['ws_view']['orders'] if r['id'] == o['id'])['can'], 'not_yet')
        want = {r['item']: r['want'] for r in data['forecast']['needs']}
        self.assertTrue(all(k in want for k in list(o['lines'])[:1]))
        next_day(j)
        data = public_state(j.state)['careers']['grocery']['data']
        self.assertTrue(any(r['icon'] == '🚚' for r in data['care']))

    def test_validation_refuses_a_changed_order(self):
        j = shop()
        o = offer(j)
        for change in (dict(value=o['value'] + 1), dict(off=1), dict(state='won'), dict(lines={'beer': 999})):
            bad = copy.deepcopy(j.state)
            bad_o = next(x for x in bad['careers']['grocery']['ext']['data']['ws']['orders'] if x['id'] == o['id'])
            bad_o.update(change)
            with self.assertRaises(GameError, msg=str(change)):
                validate_state(bad)


if __name__ == '__main__':
    unittest.main()
