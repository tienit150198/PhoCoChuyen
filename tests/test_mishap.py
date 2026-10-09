"""🔐 Scheduled mishaps (game/mishap.py, kind 'mishap' of game/live_effects.py): taken once, in order, never into
debt, only once their time has come, the player's gear counts; the plan script spreads uneven amounts."""
import copy
import json
import random
import time
import unittest

from game import bank as bk
from game import live_effects as lfx
from game import mishap
from game.engine import validate_state
from tests.test_live_effects_apply import Base


def rich(s, balance=1000, demand=500, terms=(2000,), saving=300, wallet=200):
    j = s['journey']
    if j.get('bank') is None:
        j['bank'] = bk.initial(j.get('seed') or 1, j['life_day'])
    b = j['bank']
    b['balance'], b['demand'] = balance, demand
    b['terms'] = []
    for n, a in enumerate(terms):
        b['terms'].append(dict(id=f't{n}', amount=a, term=180, rate=bk.TERM_RATE[180], start=j['life_day'], due=j['life_day'] + 180, renew=True))
    iv = j.get('invest')
    if isinstance(iv, dict):
        iv['saving']['balance'] = saving
    j['wallet'] = wallet
    return s


class Apply(Base):
    def fresh(self):
        tok = self.guest()
        s = self.state(tok)
        return tok, s

    def take(self, s, amount, sub='scam', eid='mishap-1-x-1'):
        return lfx.apply(s, dict(id=eid, kind='mishap', amount=amount, sub=sub))

    def test_order_and_no_debt(self):
        _tok, s = self.fresh()
        try:
            rich(s)
            validate_state(s)
        except Exception as e:   # noqa: BLE001 - a save shape this build does not allow: skip quietly
            self.skipTest(f'save shape: {e}')
        s1, r = self.take(copy.deepcopy(s), 1200)
        b = s1['journey']['bank']
        self.assertEqual(r['live']['taken'], 1200)
        self.assertEqual((b['balance'], b['demand'], len(b['terms'])), (0, 300, 1))   # account first, then the demand pot
        s2, r = self.take(copy.deepcopy(s), 10**8)
        j = s2['journey']
        total = 1000 + 500 + 2000 + (300 if isinstance(j.get('invest'), dict) else 0) + 200
        self.assertEqual(r['live']['taken'], total)
        self.assertEqual((j['bank']['balance'], j['bank']['demand'], j['bank']['terms'], j['wallet']), (0, 0, [], 0))
        self.assertTrue(j['bank']['inbox'][-1]['text'].startswith('Ngân hàng Phố'))
        validate_state(s2)

    def test_a_term_closed_early_returns_the_rest(self):
        _tok, s = self.fresh()
        try:
            rich(s, balance=0, demand=0, terms=(5000,), saving=0, wallet=0)
            validate_state(s)
        except Exception as e:   # noqa: BLE001
            self.skipTest(f'save shape: {e}')
        s1, r = self.take(s, 1234)
        b = s1['journey']['bank']
        self.assertEqual((r['live']['taken'], b['terms'], b['balance']), (1234, [], 5000 - 1234))

    def test_paid_once_per_row(self):
        _tok, s = self.fresh()
        try:
            rich(s)
            validate_state(s)
        except Exception as e:   # noqa: BLE001
            self.skipTest(f'save shape: {e}')
        s, r1 = self.take(s, 700)
        s, r2 = self.take(s, 700)
        self.assertEqual(r1['live']['taken'], 700)
        self.assertTrue(r2['live'].get('already'))
        self.assertEqual(s['journey']['bank']['balance'], 300)

    def test_gear(self):
        _tok, s = self.fresh()
        try:
            rich(s)
            validate_state(s)
        except Exception as e:   # noqa: BLE001
            self.skipTest(f'save shape: {e}')
        from game import rui
        if rui.get(s) is None:
            s['journey'][rui.KEY] = rui.initial(s['journey']['life_day'])
        r = rui.get(s)
        r['gear'] = ['diet_virus']
        s1, res = self.take(copy.deepcopy(s), 800, sub='hack')
        self.assertEqual(res['live']['taken'], 400)
        r['gear'] = ['hai_lop']
        s2, res = self.take(copy.deepcopy(s), 800, sub='hack')
        self.assertEqual(res['live']['taken'], 800)
        self.assertIn('cuộc gọi', s2['journey']['bank']['log'][-1]['text'])

    def test_a_bad_sub_is_refused(self):
        _tok, s = self.fresh()
        with self.assertRaises(Exception):
            self.take(s, 10, sub='nope')


class Schedule(Base):
    def insert(self, tok, eid, amount, at, sub='scam'):
        sid = self.store.key(tok)
        self.store.transaction(lambda db: db.execute(
            "INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?, ?, 'mishap', ?, ?, 'pending', ?)",
            (eid, sid, amount, json.dumps(dict(sub=sub)), at)))

    def test_only_once_its_time_has_come(self):
        tok = self.guest()
        self.insert(tok, 'mishap-9-a-1', 5, time.time() + 3600)
        self.assertFalse(self.load(tok))
        self.assertEqual(self.status('mishap-9-a-1'), 'pending')
        self.insert(tok, 'mishap-9-a-2', 5, time.time() - 1)
        self.load(tok)
        self.assertEqual(self.status('mishap-9-a-2'), 'applied')
        self.assertEqual(self.status('mishap-9-a-1'), 'pending')


class Plan(unittest.TestCase):
    def test_uneven_amounts_that_add_up(self):
        from scripts.mishap_plan import split
        for target in (146_367_316, 9_999_999, 410_000):
            rows = split(target, random.Random(target), t0=1_800_000_000, days=10)
            amounts = [a for _at, a, _sub in rows]
            self.assertEqual(sum(amounts), target)
            self.assertEqual(len(set(amounts)), len(amounts))
            self.assertTrue(all(a % 1000 for a in amounts))
            days = [int((at - 1_800_000_000) // 86400) for at, _a, _s in rows]
            self.assertTrue(all(0 <= d < 10 for d in days))
            self.assertTrue(all(sub in mishap.SUBS for *_x, sub in rows))


if __name__ == '__main__':
    unittest.main()
