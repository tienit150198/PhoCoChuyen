"""🤖 Tự nhập hàng (game/quay_auto.py, player feedback #461): off by default; under 20 % of the storage the last manual
order again, cut to the room and the batch limit, paid from the till + fund like a manual restock (one goods expense),
at most 30 % of the counter's till + fund per Vietnam day, never into debt; settling twice buys once, polling equals
offline; the saves still load on 2.5.0.1 (`git archive origin/main`)."""
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import quay, quay_auto as qa
from game import quay_business as qb
from game import quay_self as qs
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_quay_business import fixture
from tests.test_quay import opened, ST, act

ROOT = Path(__file__).resolve().parents[1]
T0 = 1_800_000_000 - (1_800_000_000 + 7 * 3600) % 86400 + 8 * 3600   # 08:00 in Vietnam


def counter(again=None, on=True):
    """A staffed milk-tea cart, settled once at T0 (its starter shelf), with a last order and the switch."""
    s, st = fixture()
    qb.settle(s, now=T0)
    board = qs.menu(st)['on']
    if again is not False:
        st['business']['again'] = again or {board[0]: 30, board[1]: 20}
    if on:
        s['journey']['quay'][qa.KEY] = True
    return s, st


def low(st, n=10):
    """Leave `n` portions of the first board dish on the shelf (under 20 % of the 500-portion cart)."""
    b = st['business']
    b['stock'] = {d: 0 for d in b['stock']}
    b['stock'][qs.menu(st)['on'][0]] = n


class Rule(unittest.TestCase):
    def test_off_by_default(self):
        s, st = counter(on=False)
        self.assertFalse(qa.on(s))
        goods = st['business']['expenses']['goods']
        qb.settle(s, now=T0 + 3 * 86400)
        b = st['business']
        self.assertEqual(sum(b['stock'].values()), 0)   # sold out, nothing bought
        self.assertEqual(b['expenses']['goods'], goods)
        self.assertNotIn(qa.STATE, b)
        self.assertFalse(qa.attempt(s, st, T0 * 1000) and qa.on(s))

    def test_restocks_only_under_the_threshold_with_the_last_order(self):
        s, st = counter()
        b = st['business']
        board = qs.menu(st)['on']
        low(st, 100)   # 20 % of 500: not under
        self.assertFalse(qa.attempt(s, st, T0 * 1000))
        self.assertEqual(b['stock'][board[0]], 100)
        low(st, 99)
        cash, goods = st['till'] + st['fund'], b['expenses']['goods']
        self.assertTrue(qa.attempt(s, st, T0 * 1000))
        self.assertEqual((b['stock'][board[0]], b['stock'][board[1]]), (99 + 30, 20))
        cost = 30 * qb.unit_cost(st, board[0]) + 20 * qb.unit_cost(st, board[1])
        self.assertEqual(st['till'] + st['fund'], cash - cost)
        self.assertEqual(b['expenses']['goods'], goods + cost)   # booked once, at the same unit costs
        self.assertEqual(b['again'], {board[0]: 30, board[1]: 20})   # the last manual order is kept as it was
        self.assertEqual(b[qa.STATE]['spent'], cost)
        self.assertEqual(st['log'][-1], dict(d=s['journey']['life_day'], t=qa.LOG, a=-cost))

    def test_same_plan_as_the_manual_restock_through_the_engine(self):
        s = opened(wallet=50000)
        sid = ST(s)['id']
        board = qs.menu(ST(s))['on']
        ST(s)['fund'] += 10000
        s, _ = act(s, 'jr_quay_restock', stall=sid, items={board[0]: 7, board[2]: 4})
        s, r = act(s, 'jr_quay_auto', on=True)
        self.assertTrue(s['journey']['quay'][qa.KEY])
        st = ST(s)
        low(st, 3)
        validate_state(s)
        before = dict(st['business']['stock'])
        self.assertTrue(qa.attempt(s, st, st['business']['cursor']))
        after = st['business']['stock']
        self.assertEqual({d: after[d] - before.get(d, 0) for d in after if after[d] != before.get(d, 0)}, {board[0]: 7, board[2]: 4})
        validate_state(s)
        s, r = act(s, 'jr_quay_auto', on=False)
        self.assertNotIn(qa.KEY, s['journey']['quay'])
        with self.assertRaises(GameError):
            act(s, 'jr_quay_auto', on='yes')

    def test_turning_it_on_restocks_an_empty_counter_at_once(self):
        s = opened(wallet=50000)
        sid = ST(s)['id']
        board = qs.menu(ST(s))['on']
        ST(s)['fund'] += 5000
        s, _ = act(s, 'jr_quay_restock', stall=sid, items={board[0]: 5})
        st = ST(s)
        st['business']['stock'] = {d: 0 for d in st['business']['stock']}
        validate_state(s)
        self.assertEqual(qb.status(st), 'out_of_stock')
        s, r = act(s, 'jr_quay_auto', on=True)
        self.assertIn('1 quầy', r['message'])
        self.assertEqual(ST(s)['business']['stock'][board[0]], 5)

    def test_room_and_batch_limits(self):
        s, st = counter(again=None)
        b = st['business']
        board = qs.menu(st)['on']
        b['again'] = {board[0]: 150, board[1]: 150}   # 300 > the 200-portion batch
        low(st, 10)
        self.assertTrue(qa.attempt(s, st, T0 * 1000))
        self.assertEqual((b['stock'][board[0]], b['stock'][board[1]]), (160, 50))
        b['paid_tier'] = {'restock': 4}               # 900 a time; the 500-portion room is the limit now
        b['again'] = {board[0]: 300, board[1]: 300}
        low(st, 90)
        self.assertTrue(qa.attempt(s, st, (T0 + 1) * 1000))
        self.assertEqual((b['stock'][board[0]], b['stock'][board[1]]), (390, 110))   # 300, then the 110 left
        self.assertEqual(sum(b['stock'].values()), 500)
        quay.validate(s)

    def test_daily_cap_cuts_then_waits_for_the_next_vietnam_day(self):
        s, st = counter()
        b = st['business']
        board = qs.menu(st)['on']
        c0, c1 = qb.unit_cost(st, board[0]), qb.unit_cost(st, board[1])
        st['till'], st['fund'] = 0, 400   # cap 120 xu today; the order costs 30·c0 + 20·c1 = 200
        low(st, 10)
        self.assertTrue(qa.attempt(s, st, T0 * 1000))
        cost = 30 * c0 + 20 * c1
        want = {board[0]: 30 * 120 // cost, board[1]: 20 * 120 // cost}
        self.assertEqual((b['stock'][board[0]] - 10, b['stock'][board[1]]), (want[board[0]], want[board[1]]))
        spent = want[board[0]] * c0 + want[board[1]] * c1
        self.assertLessEqual(spent, 120)
        self.assertEqual(b[qa.STATE], dict(day=qa.vn_day(T0 * 1000), base=400, spent=spent, at=T0 * 1000))
        low(st, 10)
        self.assertFalse(qa.attempt(s, st, (T0 + 3600) * 1000))   # same day: what is left of the cap buys nothing
        self.assertEqual(b[qa.STATE]['why'], 'cap')
        self.assertEqual(st['fund'], 400 - spent)
        midnight = qa.next_midnight(T0 * 1000)
        self.assertFalse(qa.attempt(s, st, midnight - 1))
        self.assertTrue(qa.attempt(s, st, midnight))      # a new day: a new cap from the till + fund now
        self.assertEqual(b[qa.STATE]['base'], 400 - spent)
        self.assertNotIn('why', b[qa.STATE])
        quay.validate(s)

    def test_never_into_debt_when_the_counter_is_short(self):
        s, st = counter()
        b = st['business']
        board = qs.menu(st)['on']
        s['journey']['wallet'] = 10**6
        st['till'], st['fund'] = 0, 100
        b[qa.STATE] = dict(day=qa.vn_day(T0 * 1000), base=10**6, spent=0)   # a cap that would allow it
        low(st, 10)
        before = copy.deepcopy(s)
        self.assertFalse(qa.attempt(s, st, T0 * 1000))
        self.assertEqual(b[qa.STATE].pop('why'), 'cash')
        self.assertEqual(b[qa.STATE].pop('cash'), 100)
        self.assertEqual(s, before)   # no stock, no money moved: not the wallet, not the bank
        self.assertEqual(qa.stall_public(st)['why'], None)
        qa.attempt(s, st, T0 * 1000)
        self.assertEqual(qa.stall_public(st)['why'], 'cash')
        b.pop('again')
        self.assertEqual(qa.stall_public(st)['why'], 'none')

    def test_settling_twice_buys_once_and_polling_equals_offline(self):
        s, st = counter()
        other = copy.deepcopy(s)
        for t in range(T0 + 600, T0 + 2 * 86400, 600):
            qb.settle(s, now=t)
        qb.settle(other, now=T0 + 2 * 86400 - 600)
        self.assertEqual(s, other)
        b = st['business']
        self.assertGreater(b[qa.STATE]['spent'], 0)
        again = copy.deepcopy(s)
        qb.settle(s, now=T0 + 2 * 86400 - 600)   # the same time again: nothing bought twice
        self.assertEqual(s, again)

    def test_goods_expense_equals_what_was_bought(self):
        s, st = counter()
        b = st['business']
        goods, revenue = b['expenses']['goods'], b['revenue']
        board = qs.menu(st)['on']
        bought = {}
        orig = qb.shelve

        def spy(st_, items, cost):
            for d, n in items.items():
                bought[d] = bought.get(d, 0) + n
            return orig(st_, items, cost)
        from unittest import mock
        with mock.patch.object(qb, 'shelve', spy):
            qb.settle(s, now=T0 + 86400)
        cost = sum(qb.unit_cost(st, d) * n for d, n in bought.items())
        self.assertGreater(cost, 0)
        self.assertEqual(b['expenses']['goods'] - goods, cost)
        days = {qa.vn_day(T0 * 1000), qa.vn_day((T0 + 86400) * 1000)}
        self.assertEqual(len(days), 2)
        self.assertGreater(b['revenue'], revenue)
        self.assertTrue(set(bought) <= set(board[:2]))

    def test_an_empty_counter_restocks_at_the_next_midnight_offline(self):
        s, st = counter()
        st['till'], st['fund'] = 0, 300
        b = st['business']
        b[qa.STATE] = dict(day=qa.vn_day(T0 * 1000), base=0, spent=0)   # today's cap is used up
        b['stock'] = {d: 0 for d in b['stock']}
        self.assertTrue(qb.due(s, now=T0 + 60))
        qb.settle(s, now=T0 + 60)
        self.assertEqual(b[qa.STATE]['why'], 'cap')
        self.assertFalse(qb.due(s, now=T0 + 120))         # nothing moved: the load settlement leaves it alone
        midnight = qa.next_midnight(T0 * 1000) // 1000
        self.assertTrue(qb.due(s, now=midnight + 5))
        qb.settle(s, now=midnight + 3600)
        self.assertEqual(b[qa.STATE]['day'], qa.vn_day(midnight * 1000))
        self.assertGreater(b['sold'], 0)
        self.assertGreaterEqual(b[qa.STATE].get('at', 0), midnight * 1000)


class View(unittest.TestCase):
    def test_public_state_and_validation(self):
        s = opened(wallet=50000)
        sid = ST(s)['id']
        board = qs.menu(ST(s))['on']
        ST(s)['fund'] += 5000
        s, _ = act(s, 'jr_quay_restock', stall=sid, items={board[0]: 5})
        ST(s)['business']['stock'] = {d: 0 for d in ST(s)['business']['stock']}
        s, _ = act(s, 'jr_quay_auto', on=True)
        q = public_state(s)['journey']['quay']
        self.assertEqual({k: q['auto'][k] for k in ('on', 'low', 'share', 'n')}, dict(on=True, low=20, share=30, n=1))
        self.assertEqual(q['auto']['xu'], 5 * qb.unit_cost(ST(s), board[0]))
        self.assertIsNotNone(q['auto']['at'])
        self.assertEqual(q['stalls'][0]['business']['auto']['spent'], q['auto']['xu'])
        for bad in ({qa.KEY: False}, ):
            t = copy.deepcopy(s)
            t['journey']['quay'].update(bad)
            with self.assertRaises(GameError):
                validate_state(t)
        t = copy.deepcopy(s)
        ST(t)['business'][qa.STATE]['why'] = 'cash'   # why without cash
        with self.assertRaises(GameError):
            validate_state(t)


NODE = shutil.which('node')
PLAYWRIGHT = Path('C:/Users/ADMIN/miniconda3/Lib/site-packages/playwright/driver/package/index.mjs')


@unittest.skipUnless(NODE and PLAYWRIGHT.is_file(), 'node and playwright are required')
class Browser(unittest.TestCase):
    def test_switch_in_the_quay_dialog_at_390px(self):
        r = subprocess.run([NODE, 'tests/quay_auto_browser.mjs'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
                           timeout=240)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-4000:])


class RollbackTo2501(unittest.TestCase):
    """A save with the switch on and automatic restocks done validates, migrates, renders and takes quầy commands on
    2.5.0.1 (`git archive origin/main`), which keeps the optional keys without reading them."""

    def tree(self, ref):
        tmp = tempfile.mkdtemp(prefix='mnl-2501-')
        self.addCleanup(subprocess.run, ['rm', '-rf', tmp])
        try:
            data = subprocess.run(['git', 'archive', ref, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return tmp

    def test_save_loads_on_2501(self):
        s = opened(wallet=50000)
        sid = ST(s)['id']
        board = qs.menu(ST(s))['on']
        ST(s)['fund'] += 5000
        s, _ = act(s, 'jr_quay_restock', stall=sid, items={board[0]: 5})
        ST(s)['business']['stock'] = {d: 0 for d in ST(s)['business']['stock']}
        s, _ = act(s, 'jr_quay_auto', on=True)
        ST(s)['business'][qa.STATE].update(why='cap', cash=7)
        validate_state(s)
        from game.engine import dormant_out
        saves = json.loads(json.dumps([dormant_out(s)]))   # as the store writes it: unused new careers left out
        old = self.tree('origin/main')
        if not old:
            self.skipTest('no git tree for origin/main')
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state,apply_action;out=[]\n'
                'for s in json.load(sys.stdin):\n s=migrate_state(s);validate_state(s);public_state(s)\n'
                ' sid=s["journey"]["quay"]["stalls"][0]["id"]\n'
                ' s,_=apply_action(s,None,"jr_quay_till",{"stall":sid});validate_state(s)\n'
                ' out.append([s["journey"]["quay"].get("auto_restock"),s["journey"]["quay"]["stalls"][0]["business"].get("auto")])\n'
                'import game;print(json.dumps([game.__version__,out]))')
        env = {k: v for k, v in os.environ.items() if k != 'MNL_CAREERS'}
        env['PYTHONPATH'] = old
        got = subprocess.run([sys.executable, '-c', prog], input=json.dumps(saves), capture_output=True, text=True,
                             cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(got.returncode, 0, got.stderr[-3000:])
        version, keys = json.loads(got.stdout)
        self.assertEqual(version, '2.5.0.1')
        self.assertEqual(keys, [[True, saves[0]['journey']['quay']['stalls'][0]['business']['auto']]])   # kept, not read


if __name__ == '__main__':
    unittest.main()
