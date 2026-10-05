import copy
import json
import unittest
from unittest.mock import patch

from game import wealth_pricing as wp, shop_events as events, quay_business as qb, incidents, rui, bank
from game.engine import GameError, validate_state, migrate_state
from tests.test_quay_business import fixture
from tests.test_incidents import open_day, fire, choose
from tests.test_rui import grown, R


class SecurityPercent(unittest.TestCase):
    def test_server_draw_spans_one_to_twenty_and_is_repeatable(self):
        self.assertTrue(hasattr(wp, 'event_quote'))
        s, _ = fixture(staff=False)
        quotes = [wp.event_quote(s, f'theft-{n}', wealth=1000000) for n in range(300)]
        self.assertEqual({q['percent'] for q in quotes}, set(range(1, 21)))
        self.assertEqual(quotes[25], wp.event_quote(s, 'theft-25', wealth=1000000))
        for q in quotes:
            self.assertEqual(wp.event_cost(q), 10000 * q['percent'])

    def test_shop_quote_survives_reload_matches_debit_and_cannot_replay(self):
        s, st = fixture(staff=False)
        qb.settle(s, now=1000)
        st['business']['sold'] = events.GAP
        with patch.object(events, 'select_kind', return_value='theft'):
            events.tick_quay(s, st)
        q = st['shop_events']['pending']
        self.assertIn('percent', q)
        self.assertTrue(1 <= q['percent'] <= 20)
        st.update(fund=10000000, till=0)
        view = events.public(st, True)['pending']
        price = next(x['cost'] for x in view['choices'] if x['id'] == 'record')
        self.assertEqual(price, wp.event_cost(q))
        s['journey']['wallet'] += 999999
        self.assertEqual(events.public(st, True)['pending'], view)
        before = st['fund']
        payload = dict(event=q['id'], choice='record', confirm=True)
        events.choose_quay(s, st, payload)
        self.assertEqual(before - st['fund'], price)
        events.validate(json.loads(json.dumps(st)), st['id'], st['trade'], st['place'])
        with self.assertRaises(GameError):
            events.choose_quay(s, st, payload)

    def test_racket_payment_uses_percent_but_repairs_keep_their_own_price(self):
        s = open_day('milk_tea'); s['journey']['wallet'] = 10000000
        fire(s, 'milk_tea', 'racket_again'); c = s['careers']['milk_tea']
        q = c['incidents']['active']
        self.assertIn('percent', q)
        q['percent'] = 20
        spec = incidents._priced_spec(q)
        paid = next(o for o in spec['options'] if o['id'] == 'pay')
        self.assertEqual(-sum(a for _, a, _ in paid['pay']), wp.event_cost(q))
        repair = next(o for o in spec['options'] if o['id'] == 'call')
        self.assertEqual(-sum(a for _, a, _ in repair['pay']), wp.cost(10, q['wealth']))
        from game.engine import money
        money(s, c, wp.event_cost(q), 'Test capital', category='other_income')
        before = c['money']; s, _ = choose(s, 'milk_tea', 'pay')
        self.assertEqual(before - s['careers']['milk_tea']['money'], wp.event_cost(q))
        validate_state(migrate_state(json.loads(json.dumps(s))))

    def test_personal_loss_uses_frozen_percent_and_correct_account(self):
        for kind in ('hack', 'trom'):
            for pct in (1, 20):
                s = grown(wallet=1000000, bank=1000000, day=40)
                r = R(s)
                with patch.object(rui, 'candidates', return_value=[(10000, kind, 'account' if kind == 'hack' else 'nha', None)]):
                    rui._roll(s, r, 40, [])
                self.assertIn('percent', r['warn'])
                # Exercise both endpoints without depending on a particular seed.
                r['warn'].update(percent=pct, wealth=2000000)
                w = copy.deepcopy(r['warn'])
                day = w['day']; s['journey']['life_day'] = day
                wallet, balance = s['journey']['wallet'], bank.get(s)['balance']
                rui._fire(s, r, day, [])
                expected = 2000000 * pct // 100
                self.assertEqual(r['card']['loss'], expected)
                self.assertEqual(wallet-s['journey']['wallet'], expected if kind == 'trom' else 0)
                self.assertEqual(balance-bank.get(s)['balance'], expected if kind == 'hack' else 0)
                rui.validate(s)

    def test_invalid_percent_is_rejected_and_fees_stay_progressive(self):
        s, st = fixture(staff=False); qb.settle(s, now=1000)
        st['business']['sold'] = events.GAP
        with patch.object(events, 'select_kind', return_value='theft'): events.tick_quay(s, st)
        for bad in (0, 21, True, '10'):
            st['shop_events']['pending']['percent'] = bad
            with self.assertRaises(GameError): events.validate(st, st['id'], st['trade'], st['place'])
        self.assertEqual(wp.cost(7, 1000000), 77)

    def test_rich_but_cash_poor_never_sells_assets_or_overdraws(self):
        s = grown(wallet=1000, bank=900, day=40)
        r = R(s)
        q = dict(kind='hack', wealth=100000000, percent=20)
        self.assertEqual(rui._security_loss(s, r, q, 41), 900)
        q['kind'] = 'trom'
        self.assertEqual(rui._security_loss(s, r, q, 41), 1000)
        bank.get(s)['balance'] = 0
        self.assertEqual(rui._security_loss(s, r, q, 41), 700)
        q.update(wealth=100000, percent=20)
        s['journey']['wallet'] = 100000
        rui._month(s, r, 41)['lost'] = 19900
        self.assertEqual(rui._security_loss(s, r, q, 41), 100)

    def test_compatible_reader_writes_no_new_quotes_but_accepts_them(self):
        s, st = fixture(staff=False)
        with patch.object(wp, 'ENABLED', False):
            qb.settle(s, now=1000)
            self.assertNotIn('protection_quote', st['business'])
            st['business']['sold'] = events.GAP
            with patch.object(events, 'select_kind', return_value='theft'): events.tick_quay(s, st)
            self.assertNotIn('wealth', st['shop_events']['pending'])
            st['shop_events']['pending'].update(wealth=1000000, percent=20)
            events.validate(st, st['id'], st['trade'], st['place'])

    def test_equipment_reduces_personal_loss_without_rerolling(self):
        s = grown(wallet=1000000, bank=1000000, day=40); r = R(s)
        q = dict(kind='hack', wealth=2000000, percent=10)
        self.assertEqual(rui._security_loss(s, r, q, 41), 200000)
        r['gear'].append('diet_virus')
        self.assertEqual(rui._security_loss(s, r, q, 41), 100000)
        q['kind'] = 'trom'; r['gear'].append('ket')
        self.assertEqual(rui._security_loss(s, r, q, 41), 50000)
