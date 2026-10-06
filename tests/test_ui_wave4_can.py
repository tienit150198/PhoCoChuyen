"""UI wave 4 (docs/UI_KIT.md): server pre-checks sent to the page as can[action] for the shops and the street-kit
careers. Each pre-check is the command's own guard run in "check" mode (game/careers/kit.py check): the same
message, the same order, recorded instead of raised. They are view fields only (never saved)."""
import json
import unittest

from game import boba as BOBA
from game.careers import kit
from game.careers import fruit as FR
from game.careers import garbage as RC
from game.careers import homemaker as NT
from game.careers import ice_cream as KM
from game.careers import nail as NL
from game.careers import photobooth as PB
from game.careers import restaurant as RS
from game.engine import GameError
from tests.helpers import Journey


def refusal(fn, *args):
    try:
        fn(*args)
    except GameError as e:
        return str(e)
    return None


class MilkTeaSwap(unittest.TestCase):
    """tea_swap: only a bought syrup or topping of the order (the counter offered a swap for pearls it could not cook)."""
    def test_made_item_is_not_swappable(self):
        made = next(k for k in BOBA.TOPPINGS if k in BOBA.MADE)
        bought = next(k for k in BOBA.TOPPINGS if k in BOBA.BOUGHT)
        t = dict(needs=dict(toppings=[made, bought], flavor=None), cup=dict(items=[]))
        can = kit.check(BOBA._swap_rules, t, made)
        self.assertEqual(can['why'], refusal(BOBA._swap_rules, t, made))
        self.assertEqual(can['why'], 'Món này không có trong ly khách gọi.')
        self.assertIs(kit.check(BOBA._swap_rules, t, bought), True)
        t['cup']['items'] = [bought]
        self.assertEqual(kit.check(BOBA._swap_rules, t, bought)['why'], 'Món này đã vào ly rồi.')

    def test_public_task_carries_one_answer_per_ordered_item(self):
        j = Journey('milk_tea')
        tid = j.task['id']
        j.act('ask', task=tid)
        t = j.get(tid)
        v = BOBA.public_task(t)
        want = [*([t['needs']['flavor']] if t['needs'].get('flavor') else []), *t['needs']['toppings']]
        self.assertEqual(sorted(v['can']['tea_swap']), sorted(want))
        json.dumps(v)


class RestaurantSubTouch(unittest.TestCase):
    def order(self, **kw):
        t = dict(needs=dict(style='classic', broth='kimchi', toppings={'beef': 1}, spice=1, extra_noodle=False),
                 subs={}, touches=[], plates=[], bowl=dict(broth=None))
        t.update(kw)
        return t

    def test_substitute_of_a_substitute_is_refused_ahead(self):
        t = self.order(subs={'beef': 'mushroom'})
        self.assertIs(kit.check(RS._sub_rules, t, 'beef'), True)
        can = kit.check(RS._sub_rules, t, 'mushroom')
        self.assertEqual(can['why'], refusal(RS._sub_rules, t, 'mushroom'))
        self.assertEqual(can['why'], 'Món này không có trong order.')

    def test_soup_before_the_broth(self):
        t = self.order(regular=dict(notes=['soup', 'tea']))
        can = kit.check(RS._touch_rules, t, 'soup')
        self.assertEqual(can['why'], refusal(RS._touch_rules, t, 'soup'))
        self.assertIn('Chan nước dùng', can['why'])
        self.assertEqual(can['fix']['sel'], '.rs-pots')
        self.assertIs(kit.check(RS._touch_rules, t, 'tea'), True)
        t['bowl']['broth'] = 'kimchi'
        self.assertIs(kit.check(RS._touch_rules, t, 'soup'), True)
        t['touches'] = ['tea']
        self.assertEqual(kit.check(RS._touch_rules, t, 'tea')['why'], 'Đã làm việc này cho khách rồi.')

    def test_public_task(self):
        j = Journey('restaurant')
        tid = j.task['id']
        j.act('ask', task=tid)
        v = RS.public_task(j.get(tid))
        self.assertIn('rs_sub', v['can'])
        self.assertIn('rs_touch', v['can'])
        json.dumps(v)


class HomemakerClose(unittest.TestCase):
    def task(self, typ, work):
        items = [dict(id='a', name='A'), dict(id='b', name='B'), dict(id='c', name='C')]
        st = dict(id='s1', type=typ, items=items, bins=[dict(id='x')], title='Bước')
        return dict(stage='work', known=True, at=0, needs=dict(steps=[st]), work=dict(s1=work),
                    _key=dict(s1=dict(bad={'c': [1, 'không cần', 'cr']}, rules=[], items={}))), st

    def test_sort_and_order(self):
        t, st = self.task('sort', {'a': 'x'})
        can = kit.check(NT._close_rules, t)
        self.assertEqual(can['why'], refusal(NT._sort_rule, t, st))
        t, st = self.task('order', ['a', 'c'])
        can = kit.check(NT._close_rules, t)
        self.assertEqual(can['why'], refusal(NT._order_rule, t, st, t['_key']['s1']))
        self.assertEqual(can['why'], 'Còn việc chưa xếp vào thứ tự.')
        t, _ = self.task('order', ['b', 'a'])
        self.assertIs(kit.check(NT._close_rules, t), True)
        t, _ = self.task('pick', [])
        self.assertIs(kit.check(NT._close_rules, t), True)

    def test_public_task(self):
        j = Journey('homemaker')
        tid = j.task['id']
        j.act('ask', task=tid)
        v = NT.public_task(j.get(tid))
        self.assertIn('nt_close', v['can'])
        self.assertNotIn('_key', v)
        json.dumps(v)


class GarbageLoad(unittest.TestCase):
    def test_sweep_first(self):
        t = dict(id='t1', late=True, swept=False)
        can = kit.check(RC._load_rules, t)
        self.assertEqual(can['why'], refusal(RC._load_rules, t))
        self.assertEqual(can['fix']['cmd'], 'rac_sweep')
        self.assertEqual(can['fix']['payload'], dict(task='t1'))
        self.assertIs(kit.check(RC._load_rules, dict(t, swept=True)), True)
        self.assertIs(kit.check(RC._load_rules, dict(t, late=False)), True)


class FruitWeigh(unittest.TestCase):
    def test_bulk_range(self):
        t = dict(kind='bulk', bag=[dict(i='cam')], needs=dict(min=3, max=5, lines=[]))
        can = kit.check(FR._weigh_rules, t)
        self.assertEqual(can['why'], refusal(FR._weigh_rules, t))
        self.assertIn('3 tới 5', can['why'])
        self.assertEqual(kit.check(FR._weigh_rules, dict(t, bag=[]))['why'], 'Rổ còn trống. Chọn trái cho khách đã.')
        self.assertIs(kit.check(FR._weigh_rules, dict(t, bag=[{}] * 4)), True)
        self.assertIs(kit.check(FR._weigh_rules, dict(kind='buy', bag=[{}], needs=dict(lines=[]))), True)


class ShopOpen(unittest.TestCase):
    """nail, photobooth, ice cream: a customer picked before “Mở tiệm” is dimmed with the reason and a fix that
    brings up the morning set-up."""
    def test_open_rule_and_fix(self):
        for mod, cid in ((NL, 'nail'), (PB, 'photobooth'), (KM, 'ice_cream')):
            with self.subTest(cid):
                j = Journey(cid)
                c = j.c
                setup = next((t for t in c['tasks'] if t.get('kind') == 'setup'), None)
                can = mod.public_data(c)['can']['open']
                self.assertIsNotNone(setup)
                d = c['ext']['data']
                self.assertEqual(can['why'], refusal(mod._open_rules, d))
                self.assertEqual(can['fix']['cmd'], 'task_select')
                self.assertEqual(can['fix']['payload'], dict(task=setup['id']))
                json.dumps(mod.public_data(c))


if __name__ == '__main__':
    unittest.main()
