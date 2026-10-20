"""🧰 Phụ kiện nghề (game/career_gadgets.py): 🧊 Tủ trữ sữa riêng (cafe_bakery, feedback #454) and 📏 Máy kiểm tra
độ tuổi (mother_baby, feedback #452). Purchase, effect, absence (= the old behaviour), and saves holding them load on
2.4.68 (`git archive 289df99d`), the release this one may be rolled back to."""
import copy
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import career_gadgets as cg, giftshop as gs, inventory
from game.careers import cafe_bakery as cb, food_service as FS
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey
from tests.test_inventory_flow import set_money

ROOT = Path(__file__).resolve().parents[1]
LIVES = (('289df99d', '2.4.68'),)


def cafe(fund=1000):
    j = Journey('cafe_bakery')
    set_money(j.c, fund)
    return j


def shop(fund=1000):
    """Day 2, slot 1: Bà Sáu / Cô Lan / Chú Hùng asks for a 3+ toy for a baby under 3 (the safety order)."""
    j = Journey('mother_baby', slot=1, day=2)
    set_money(j.c, fund)
    return j


def milk_lots(c):
    return [(l['qty'], l['expires']) for l in c['ext']['inv']['lots'] if l['item'] == 'milk' and l['qty']]


def receive_milk(c, qty=10):
    it = inventory.item('cafe_bakery', 'milk')
    sup = inventory.suppliers('cafe_bakery')[0]
    inventory._receive_lot(c, 'cafe_bakery', dict(actual=qty, unit_cost=2, supplier=sup['id']), it, sup)
    return c['ext']['inv']['lots'][-1]


class Purchase(unittest.TestCase):
    def test_buy_from_the_fund_once(self):
        j = cafe(1000)
        r = j.act('gadget_buy', item='milk_fridge')
        self.assertIn('Tủ trữ sữa riêng', r['message'])
        self.assertEqual(j.c['money'], 1000 - cg.ITEMS['milk_fridge']['price'])
        self.assertEqual(j.c['gadgets'], {'milk_fridge': dict(paid=220, day=j.c['day'])})
        self.assertNotIn('milk_fridge', j.c['upgrades'])          # not an upgrade id: 2.4.68 would refuse the save
        with self.assertRaises(GameError):
            j.act('gadget_buy', item='milk_fridge')
        self.assertEqual(j.c['money'], 780)

    def test_other_career_and_short_fund(self):
        j = cafe(1000)
        with self.assertRaises(GameError):
            j.act('gadget_buy', item='age_checker')
        with self.assertRaises(GameError):
            j.act('gadget_buy', item='nope')
        poor = cafe(100)
        with self.assertRaises(GameError):
            poor.act('gadget_buy', item='milk_fridge')
        self.assertNotIn('gadgets', poor.c)
        self.assertEqual(poor.c['money'], 100)

    def test_cards_in_the_view(self):
        j = cafe(100)
        row = public_state(j.state)['careers']['cafe_bakery']['gadgets'][0]
        self.assertEqual((row['id'], row['price'], row['owned'], row['short']), ('milk_fridge', 220, False, 120))
        self.assertTrue(row['effects'])
        m = shop()
        self.assertEqual([r['id'] for r in public_state(m.state)['careers']['mother_baby']['gadgets']], ['age_checker'])
        self.assertIsNone(public_state(Journey('restaurant').state)['careers']['restaurant']['gadgets'])

    def test_validate_refuses_a_bad_record(self):
        j = cafe()
        for bad in ({'age_checker': dict(paid=1, day=1)}, {'milk_fridge': dict(paid=1)}, {'milk_fridge': True}, {}):
            s = copy.deepcopy(j.state)
            s['careers']['cafe_bakery']['gadgets'] = bad
            with self.assertRaises(GameError):
                validate_state(s)


class MilkFridge(unittest.TestCase):
    def test_milk_keeps_a_day_longer(self):
        j = cafe()
        plain = receive_milk(j.c)
        self.assertEqual(plain['expires'] - plain['received'], 1)   # life 2: today and tomorrow (old behaviour)
        shelf = milk_lots(j.c)
        j.act('gadget_buy', item='milk_fridge')
        self.assertEqual(milk_lots(j.c), [(q, e + 1) for q, e in shelf])   # what is on the shelf goes in the fridge too
        cold = receive_milk(j.c)
        self.assertEqual(cold['expires'] - cold['received'], 2)    # life 3
        validate_state(j.state)

    def test_other_items_unchanged(self):
        j = cafe()
        j.act('gadget_buy', item='milk_fridge')
        self.assertEqual(cb.life_bonus(j.c, 'oat'), 0)
        self.assertEqual(cb.life_bonus(j.c, 'cream'), 0)
        self.assertEqual(cb.life_bonus(j.c, 'milk'), 1)
        self.assertEqual(cb.life_bonus(cafe().c, 'milk'), 0)

    def rate(self, c, days=range(2, 3002)):
        hit = 0
        for d in days:
            p = cb._milk_luck(c, FS.new_plan(cb.ID, d, cb.MODS, cb.EVENTS))
            self.assertEqual(len(p['events']), len(FS.new_plan(cb.ID, d, cb.MODS, cb.EVENTS)['events']))
            ids = [e['id'] for e in p['events']]
            self.assertEqual(len(ids), len(set(ids)))
            hit += 'sour_milk' in ids
        return hit / len(days)

    def test_sour_milk_rarer(self):
        before = sum('sour_milk' in [e['id'] for e in FS.new_plan(cb.ID, d, cb.MODS, cb.EVENTS)['events']]
                     for d in range(2, 3002)) / 3000
        base = self.rate({})
        fridge = self.rate({'gadgets': {'milk_fridge': dict(paid=220, day=1)}})
        self.assertGreater(before, 0.2)                              # was ~23 % of days
        self.assertLess(base, before * 0.7)                          # ~14 %
        self.assertLess(fridge, 0.06)                                # ~3 %, about once a month
        self.assertGreater(fridge, 0)

    def test_plan_is_stable_and_the_event_still_works(self):
        c = {}
        day = next(d for d in range(2, 400) if 'sour_milk' in [e['id'] for e in cb._milk_luck(c, FS.new_plan(cb.ID, d, cb.MODS, cb.EVENTS))['events']])
        p = cb._milk_luck(c, FS.new_plan(cb.ID, day, cb.MODS, cb.EVENTS))
        self.assertEqual(cb._milk_luck(c, copy.deepcopy(p)), p)      # idempotent: every _plan call passes through


class AgeChecker(unittest.TestCase):
    def test_absent_shows_nothing(self):
        j = shop()
        t = j.task
        self.assertEqual(t['gift_kind'], 'safety')
        j.act('ask', task=t['id'])
        self.assertNotIn('age_check', public_state(j.state)['careers']['mother_baby'])

    def test_safety_order_alternatives(self):
        j = shop()
        j.act('gadget_buy', item='age_checker')
        t = j.task
        self.assertNotIn(t['id'], public_state(j.state)['careers']['mother_baby']['age_check'])   # not asked yet
        j.act('ask', task=t['id'])
        a = public_state(j.state)['careers']['mother_baby']['age_check'][t['id']]
        age, asked = t['gift']['age'], t['needs']['product']
        self.assertEqual((a['age'], a['asked'], a['ok']), (age, asked, False))
        self.assertEqual(a['rule'], gs.LABELS[asked]['label'])
        self.assertTrue(a['alternatives'])
        for o in a['alternatives']:
            self.assertTrue(gs.suits(o['id'], age))
            self.assertLessEqual(o['price'], t['needs']['budget'])
            self.assertGreater(j.c['stock'][o['id']], 0)
        self.assertEqual({k for k, ok in a['fits'].items() if not ok} >= {asked}, True)
        # It only suggests: the player advises, and the order still needs picking, packing and the check.
        r = j.act('gift_advise', task=t['id'], item=a['alternatives'][0]['id'])
        self.assertTrue(r.get('celebrate'))
        t = j.task
        self.assertEqual((t['gs']['swap'], t['basket'], t['status'] in ('completed',)), (a['alternatives'][0]['id'], {}, False))
        a = public_state(j.state)['careers']['mother_baby']['age_check'][t['id']]
        self.assertEqual((a['asked'], a['ok']), (t['gs']['swap'], True))

    def test_out_of_stock_alternatives_drop(self):
        j = shop()
        j.act('gadget_buy', item='age_checker')
        t = j.task
        j.act('ask', task=t['id'])
        for k in gs.LABELS:
            if k != t['needs']['product']:
                j.c['stock'][k] = 0
        self.assertEqual(gs.age_check(j.c, j.task)['alternatives'], [])

    def test_kit_age_only_once_asked(self):
        j = Journey('mother_baby', slot=0, day=3)
        set_money(j.c, 1000)
        j.act('gadget_buy', item='age_checker')
        t = j.task
        self.assertEqual(t['gift_kind'], 'kit')
        j.act('ask', task=t['id'])
        self.assertIsNone(gs.age_check(j.c, j.task))
        j.act('gift_ask', task=t['id'], topic='age')
        a = gs.age_check(j.c, j.task)
        self.assertIsNone(a['asked'])                                # choosing is the job: ✓ / ✗ only
        self.assertEqual(a['alternatives'], [])
        self.assertTrue(a['fits'])


class RollbackTo2468(unittest.TestCase):
    """Saves holding both accessories validate, migrate, render and take a command on 2.4.68, which keeps the key."""

    def tree(self, ref):
        tmp = tempfile.mkdtemp(prefix='mnl-gadget-')
        self.addCleanup(subprocess.run, ['rm', '-rf', tmp])
        try:
            data = subprocess.run(['git', 'archive', ref, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return tmp

    def saves(self):
        a = cafe()
        a.act('gadget_buy', item='milk_fridge')
        receive_milk(a.c)
        b = shop()
        b.act('gadget_buy', item='age_checker')
        b.act('ask', task=b.task['id'])
        return json.loads(json.dumps([['cafe_bakery', a.state], ['mother_baby', b.state]]))

    def test_saves_validate_on_2468(self):
        saves = self.saves()
        trees = [(self.tree(ref), want) for ref, want in LIVES]
        if not any(t for t, _ in trees):
            self.skipTest('no git tree with ' + ', '.join(ref for ref, _ in LIVES))
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,public_state,apply_action;out=[]\n'
                'for cid,s in json.load(sys.stdin):\n validate_state(s);s=migrate_state(s);validate_state(s);public_state(s)\n'
                ' s,_=apply_action(s,cid,"advance",{});validate_state(s)\n'
                ' out.append(s["careers"][cid].get("gadgets"))\n'
                'import game;print(json.dumps([game.__version__,out]))')
        for old, want in trees:
            if not old:
                continue
            env = {k: v for k, v in os.environ.items() if k != 'MNL_CAREERS'}
            env['PYTHONPATH'] = old
            got = subprocess.run([sys.executable, '-c', prog], input=json.dumps(saves), capture_output=True, text=True,
                                 cwd=old, env=env, encoding='utf-8', timeout=300)
            self.assertEqual(got.returncode, 0, got.stderr[-3000:])
            version, keys = json.loads(got.stdout)
            self.assertEqual(version, want)
            self.assertEqual(keys, [s['careers'][cid]['gadgets'] for cid, s in saves])   # kept, not read


if __name__ == '__main__':
    unittest.main()
