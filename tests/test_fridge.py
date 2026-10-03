"""🧊 Tủ lạnh ở nhà (game/fridge.py): no fridge, a fridge in the bag, one in the kitchen (own home, rented room, the
attic), the dorm's shared shelf, buying into it, capacity, eating from it and buying to eat at once, the wallet never
below 0, the needs caps, the Sổ ví row, moving house, the view in deco.public, validation, and saves crossing a 1.4.27
build both ways (MNL_OLD_TREE, else ../_rel1427/mot-ngay-lam-nghe when it is there)."""
import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from game import deco as dc
from game import fridge as fr
from game import needs as nd
from game.engine import GameError, migrate_state, public_state, validate_state
from tests.test_bank import act, story
from tests.test_deco import free, owner, renter

ROOT = Path(__file__).resolve().parents[1]


def with_fridge(s, k='tu_lanh', room=None):
    """Buy a fridge and stand it in the first room that takes it."""
    L = dc.layout(s)
    room = room or next(r['id'] for r in L['rooms'] if r['type'] in ('kitchen', 'studio'))
    x, y = free(s, k, room)
    s, r = act(s, 'jr_deco_buy', item=k, confirm=True, room=room, x=x, y=y, f=0)
    return s, r['uid']


def home(wallet):
    """A tập thể of your own and `wallet` xu in hand."""
    s = owner()
    s['journey']['wallet'] = wallet
    return s


def F(s):
    return public_state(s)['journey']['deco']['fridge']


def food(s, fid):
    return next(x for x in F(s)['foods'] if x['id'] == fid)


def hungry(s, full=40, wake=60):
    n = nd.ensure(s)
    n['full'], n['wake'] = full, wake
    return s


class NoFridge(unittest.TestCase):
    def test_refused_without_a_fridge(self):
        s = owner()
        v = F(s)
        self.assertEqual((v['cap'], v['kind'], v['why']), (0, '', fr.NO_FRIDGE))
        self.assertNotIn('foods', v)   # no list without a fridge: the state answer stays small
        for name in ('jr_fridge_buy', 'jr_fridge_eat'):
            with self.assertRaises(GameError) as e:
                act(s, name, item='sua')
            self.assertEqual(e.exception.code, 'no_fridge')
        self.assertNotIn('fridge', s['journey'])

    def test_a_fridge_in_the_bag_is_not_plugged_in(self):
        s = owner()
        s, _ = act(s, 'jr_deco_buy', item='tu_lanh', confirm=True)
        self.assertEqual(F(s)['why'], fr.IN_BAG)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_fridge_buy', item='sua')
        self.assertIn('túi đồ', e.exception.message)

    def test_story_only_and_junk(self):
        s = owner()
        s, _ = with_fridge(s)
        for p in ({}, {'item': 'pizza'}, {'item': 'sua', 'n': 2}, {'item': 3}):
            with self.assertRaises(GameError):
                act(s, 'jr_fridge_buy', **p)
        off = copy.deepcopy(s)
        off['journey']['story'] = False
        with self.assertRaises(GameError):
            fr.action(off, 'jr_fridge_buy', {'item': 'sua'})
        self.assertIsNone(fr.view(off))


class OwnFridge(unittest.TestCase):
    def setUp(self):
        self.s, self.uid = with_fridge(home(300))

    def test_buy_into_the_fridge(self):
        s = self.s
        w = s['journey']['wallet']
        s, r = act(s, 'jr_fridge_buy', item='com_hop')
        s, r = act(s, 'jr_fridge_buy', item='com_hop')
        s, r = act(s, 'jr_fridge_buy', item='sua')
        self.assertEqual(s['journey']['wallet'], w - 5 - 5 - 2)
        self.assertEqual(s['journey']['fridge']['items'], {'com_hop': 2, 'sua': 1})
        self.assertIn('3/10', r['message'])
        v = F(s)
        self.assertEqual((v['kind'], v['cap'], v['used']), ('own', fr.FRIDGE_CAP, 3))
        self.assertEqual(food(s, 'com_hop')['n'], 2)
        # one Sổ ví row a day, updated in place
        rows = [h for h in s['journey']['history'] if h['label'].startswith(fr.LABEL)]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['kind'], rows[0]['amount'], rows[0]['label']), ('living', -12, f'{fr.LABEL} · 3 món'))
        validate_state(s)

    def test_capacity(self):
        s = self.s
        for _ in range(fr.FRIDGE_CAP):
            s, _ = act(s, 'jr_fridge_buy', item='sua')
        self.assertEqual(food(s, 'flan')['buy'], fr.FULL)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_fridge_buy', item='flan')
        self.assertEqual(e.exception.code, 'full')
        # a second fridge doubles the room, no more than FRIDGES_MAX count
        s['journey']['wallet'] += 300
        s, _ = with_fridge(s, 'tu_lanh_magnet')
        self.assertEqual(F(s)['cap'], 2 * fr.FRIDGE_CAP)
        s, _ = act(s, 'jr_fridge_buy', item='flan')
        validate_state(s)

    def test_wallet_never_below_zero(self):
        s = hungry(self.s)
        s['journey']['wallet'] = 4
        self.assertEqual(food(s, 'com_hop')['buy'], fr.POOR)
        self.assertEqual(food(s, 'com_hop')['eat'], fr.EMPTY)
        before = copy.deepcopy(s)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_fridge_buy', item='com_hop')
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(s, before)
        s, _ = act(s, 'jr_fridge_buy', item='banh_bao')    # 3 of the 4 xu
        self.assertEqual(s['journey']['wallet'], 1)
        s['journey']['wallet'] = -20                          # in debt: nothing bought, the fridge still feeds
        with self.assertRaises(GameError):
            act(s, 'jr_fridge_buy', item='sua')
        s = hungry(s)
        s, _ = act(s, 'jr_fridge_eat', item='banh_bao')
        self.assertEqual(s['journey']['wallet'], -20)

    def test_eat_from_the_fridge(self):
        s = self.s
        s, _ = act(s, 'jr_fridge_buy', item='com_hop')
        s = hungry(s, full=30)
        w = s['journey']['wallet']
        s, r = act(s, 'jr_fridge_eat', item='com_hop')
        self.assertEqual(s['journey']['needs']['full'], 30 + fr.FOODS['com_hop']['full'])
        self.assertEqual(s['journey']['wallet'], w)                 # paid when it went in
        self.assertEqual(s['journey']['fridge']['items'], {})
        self.assertEqual(s['journey']['fridge']['n'], 1)
        self.assertIn('No bụng 70', r['message'])
        validate_state(s)

    def test_nothing_to_eat_in_an_empty_fridge(self):
        s = hungry(self.s, full=20)
        before = copy.deepcopy(s)
        self.assertEqual(food(s, 'goi_cuon')['eat'], fr.EMPTY)
        with self.assertRaises(GameError) as e:
            act(s, 'jr_fridge_eat', item='goi_cuon')
        self.assertEqual(e.exception.code, 'empty')
        self.assertEqual(s, before)
        s, _ = act(s, 'jr_fridge_buy', item='goi_cuon')     # hungry at home: store one, eat it
        s, _ = act(s, 'jr_fridge_eat', item='goi_cuon')
        self.assertEqual(s['journey']['needs']['full'], 45)
        self.assertEqual(s['journey']['fridge'], {'v': 1, 'items': {}, 'n': 1, 'b': 1})

    def test_needs_caps_like_an_extra_snack(self):
        s = self.s
        s, _ = act(s, 'jr_fridge_buy', item='flan')
        s, _ = act(s, 'jr_fridge_buy', item='ca_phe')
        s = hungry(s, full=nd.FULL_CAP, wake=nd.WAKE_CAP)
        self.assertEqual(food(s, 'flan')['eat'], fr.TOO_FULL)
        self.assertEqual(food(s, 'ca_phe')['eat'], fr.AWAKE)
        for k in ('flan', 'ca_phe'):
            with self.assertRaises(GameError) as e:
                act(s, 'jr_fridge_eat', item=k)
            self.assertEqual(e.exception.code, 'too_full')
        s = hungry(s, full=95, wake=50)
        s, r = act(s, 'jr_fridge_eat', item='ca_phe')
        self.assertEqual(s['journey']['needs']['wake'], 65)
        self.assertEqual(s['journey']['needs']['full'], 95)
        s = hungry(s, full=89)
        s, _ = act(s, 'jr_fridge_eat', item='flan')
        self.assertEqual(s['journey']['needs']['full'], 97)   # at most 100

    def test_evening_counts_too(self):
        s = self.s
        s, _ = act(s, 'jr_fridge_buy', item='banh_bao')
        n = hungry(s, full=30)['journey']['needs']
        n['day'] = s['journey']['life_day'] - 1 if s['journey']['life_day'] > 1 else 1
        s, _ = act(s, 'jr_fridge_eat', item='banh_bao')
        self.assertEqual(s['journey']['needs']['full'], 50)

    def test_fridge_put_away_keeps_the_food(self):
        s = self.s
        s, _ = act(s, 'jr_fridge_buy', item='sua')
        s, _ = act(s, 'jr_deco_pick', uid=self.uid)
        self.assertEqual(F(s)['why'], fr.IN_BAG)
        with self.assertRaises(GameError):
            act(s, 'jr_fridge_eat', item='sua')
        self.assertEqual(s['journey']['fridge']['items'], {'sua': 1})
        self.assertNotIn('foods', F(s))   # it waits in the save until the fridge is set up again


class Rentals(unittest.TestCase):
    def test_rented_room_and_attic_with_a_fridge(self):
        for s in (renter('tro_moi'), story(wallet=6000)):
            self.assertEqual(F(s)['why'], fr.NO_FRIDGE)
            s, _ = with_fridge(s)
            self.assertEqual((F(s)['kind'], F(s)['cap']), ('own', fr.FRIDGE_CAP))
            s, _ = act(s, 'jr_fridge_buy', item='trai_cay')
            s = hungry(s)
            s, _ = act(s, 'jr_fridge_eat', item='trai_cay')
            self.assertEqual(s['journey']['needs']['full'], 52)
            validate_state(s)

    def test_dorm_shared_shelf(self):
        s = renter('ky_tuc_xa')
        v = F(s)
        self.assertEqual((v['kind'], v['cap'], v['why']), ('dorm', fr.DORM_CAP, ''))
        for _ in range(fr.DORM_CAP):
            s, r = act(s, 'jr_fridge_buy', item='sua')
        self.assertIn('ngăn tủ chung', r['message'])
        with self.assertRaises(GameError) as e:
            act(s, 'jr_fridge_buy', item='sua')
        self.assertEqual(e.exception.code, 'full')
        self.assertIn('Ngăn tủ chung đầy', e.exception.message)
        s = hungry(s)
        s, _ = act(s, 'jr_fridge_eat', item='sua')
        self.assertEqual(s['journey']['fridge']['items'], {'sua': 3})
        validate_state(s)

    def test_moving_from_a_big_fridge_to_the_dorm(self):
        s, _ = with_fridge(renter('tro_moi'))
        for _ in range(6):
            s, _ = act(s, 'jr_fridge_buy', item='flan')
        s, _ = act(s, 'jr_home_rent', kind='ky_tuc_xa', confirm=True)
        v = F(s)
        self.assertEqual((v['kind'], v['cap'], v['used']), ('dorm', fr.DORM_CAP, 6))
        self.assertEqual(food(s, 'sua')['buy'], fr.FULL)
        s = hungry(s)
        s, _ = act(s, 'jr_fridge_eat', item='flan')       # eat first, no buying until there is room
        validate_state(s)


class Saves(unittest.TestCase):
    def test_validation(self):
        s, _ = with_fridge(owner())
        s, _ = act(s, 'jr_fridge_buy', item='sua')
        validate_state(s)
        for bad in ({'v': 2, 'items': {}, 'n': 0, 'b': 0}, {'v': 1, 'items': {}, 'n': 0}, {'v': 1, 'items': {'pizza': 1}, 'n': 0, 'b': 0},
                    {'v': 1, 'items': {'sua': 0}, 'n': 0, 'b': 0}, {'v': 1, 'items': {'sua': fr.CAP_MAX + 1}, 'n': 0, 'b': 0},
                    {'v': 1, 'items': {'sua': 15, 'flan': 15}, 'n': 0, 'b': 0}, {'v': 1, 'items': [], 'n': 0, 'b': 0},
                    {'v': 1, 'items': {}, 'n': -1, 'b': 0}, [], None):
            x = copy.deepcopy(s)
            x['journey']['fridge'] = bad
            with self.assertRaises(GameError, msg=repr(bad)):
                validate_state(x)

    def test_older_save_without_the_key(self):
        s = owner()
        self.assertNotIn('fridge', s['journey'])
        s = migrate_state(s)
        validate_state(s)
        self.assertEqual(F(s), {'kind': '', 'cap': 0, 'why': fr.NO_FRIDGE})

    def old_tree(self):
        old = os.environ.get('MNL_OLD_TREE') or str(ROOT.parent / '_rel1427' / 'mot-ngay-lam-nghe')
        if not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no 1.4.27 tree (MNL_OLD_TREE)')
        return old

    def run_old(self, old, prog, s):
        env = dict(os.environ, PYTHONPATH=old + os.pathsep + os.environ.get('PYTHONPATH', ''))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr[-2000:])
        return json.loads(out.stdout)

    def test_saves_cross_a_1427_build_both_ways(self):
        old = self.old_tree()
        s, uid = with_fridge(home(500))
        s, _ = act(s, 'jr_fridge_buy', item='com_hop')
        s, _ = act(s, 'jr_fridge_buy', item='ca_phe')
        s = hungry(s)
        s, _ = act(s, 'jr_fridge_eat', item='ca_phe')
        validate_state(s)
        # The careers this release adds (phở, cơm, photobooth, giúp việc) are unknown there: a rollback takes their blocks out
        # (tests/test_career_pho.py rollback_strip) and they come back fresh here.
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action,public_state,GameError;'
                'from game.content import CAREERS;s=json.load(sys.stdin);s["careers"]={k:v for k,v in s["careers"].items() if k in CAREERS};'
                's=migrate_state(s);validate_state(s);public_state(s);'
                's,_=apply_action(s,None,"jr_deco_buy",{"item":"cay_canh","confirm":True});'
                'code="";\n'
                'try:\n apply_action(s,None,"jr_fridge_buy",{"item":"sua"})\n'
                'except GameError as e:\n code=e.code\n'
                'print(json.dumps(dict(s=s,code=code)))')
        got = self.run_old(old, prog, s)
        self.assertEqual(got['code'], 'unknown_action')           # a new page on an old server: refused cleanly
        back = got['s']
        self.assertEqual(back['journey']['fridge'], s['journey']['fridge'])   # the old build kept the key
        back = migrate_state(back)                                  # and this build loads what the old one wrote
        validate_state(back)
        back, _ = act(back, 'jr_fridge_eat', item='com_hop')
        self.assertEqual(back['journey']['fridge']['items'], {})

    def test_an_old_save_on_this_build(self):
        old = self.old_tree()
        prog = ('import json,sys;from game.engine import new_state,validate_state,apply_action;from game import journey as jr;'
                's=new_state();jr.enable_story(s,7);s["journey"].update(gender="male",wallet=900);validate_state(s);'
                's,_=apply_action(s,None,"jr_home_rent",{"kind":"tro_moi","confirm":True});print(json.dumps(s))')
        s = self.run_old(old, prog, {})
        s = migrate_state(s)
        validate_state(s)
        self.assertEqual(F(s)['why'], fr.NO_FRIDGE)
        s, _ = with_fridge(s)
        s, _ = act(s, 'jr_fridge_buy', item='sua')
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
