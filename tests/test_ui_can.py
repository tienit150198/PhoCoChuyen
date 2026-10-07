"""Server pre-checks sent to the page as can[action] (UI foundation, docs/UI_KIT.md): the same rules and messages
the command refuses with, recorded instead of raised (game/careers/kit.py check)."""
import json
import unittest

from game.careers import kit
from game.careers import com as COM
from game.careers import pagoda as PG
from game.careers import photobooth as PB
from game.engine import GameError
from tests.helpers import Journey


def refusal(fn, *args):
    try:
        fn(*args)
    except GameError as e:
        return str(e)
    return None


class PagodaClose(unittest.TestCase):
    def task(self, typ, work):
        items = [dict(id='a', name='A'), dict(id='b', name='B'), dict(id='c', name='C')]
        st = dict(id='s1', type=typ, items=items, bins=[dict(id='x')], title='Bước')
        return dict(stage='work', known=True, at=0, needs=dict(steps=[st]), work=dict(s1=work),
                    _key=dict(s1=dict(bad={'c': [1, 'không cần', 'cr']}, rules=[], items={}))), st

    def test_sort_and_order_say_what_close_refuses(self):
        t, st = self.task('sort', {'a': 'x'})
        can = kit.check(PG._close_rules, t)
        self.assertEqual(can['why'], refusal(PG._sort_rule, t, st))
        self.assertEqual(can['why'], 'Còn thứ chưa xếp chỗ.')
        t, st = self.task('order', ['a'])
        can = kit.check(PG._close_rules, t)
        self.assertEqual(can['why'], refusal(PG._order_rule, t, st, t['_key']['s1']))
        self.assertIn('1/2', can['why'])
        t, _ = self.task('order', ['a', 'b'])
        self.assertIs(kit.check(PG._close_rules, t), True)
        t, _ = self.task('pick', [])
        self.assertIs(kit.check(PG._close_rules, t), True)

    def test_public_task_carries_it_and_stays_json(self):
        j = Journey('pagoda')
        v = PG.public_task(j.task)
        if v.get('needs'):
            self.assertIn('chua_close', v['can'])
        json.dumps(v)


class ComServe(unittest.TestCase):
    def test_plates_without_rice(self):
        t = dict(plates=[dict(va=1), dict(va=0)])
        can = kit.check(COM._plate_rules, t)
        self.assertEqual(can['why'], refusal(COM._plate_rules, t))
        self.assertEqual(can['fix']['sel'], '.com-rice')
        self.assertEqual(kit.check(COM._plate_rules, dict(plates=[]))['why'], 'Chưa có dĩa nào trên quầy.')
        self.assertIs(kit.check(COM._plate_rules, dict(plates=[dict(va=2)])), True)


class PhotoboothTrimPick(unittest.TestCase):
    def test_trim_needs_frame_and_sleeves(self):
        j = Journey('photobooth')
        c = j.c
        big = next(k for k, v in PB.PKGS.items() if v['frame'])
        for l in c['ext']['inv']['lots']:
            if l['item'] == PB.PKGS[big]['frame']:
                l['qty'] = 0
        can = kit.check(PB._trim_rules, c, big)
        self.assertEqual(can['why'], refusal(PB._trim_rules, c, big))
        self.assertIn('khung', can['why'])
        self.assertEqual(can['fix']['act'], 'inventory')
        self.assertIn(big, PB.public_data(c)['can']['pb_trim'])

    def test_pick_stops_at_the_package_size(self):
        pkg, x = next(iter(PB.PKGS.items()))
        t = dict(needs=dict(pkg=pkg), pick=list(range(x['shots'])))
        can = kit.check(PB._pick_rules, t)
        self.assertEqual(can['why'], refusal(PB._pick_rules, t))
        self.assertIs(kit.check(PB._pick_rules, dict(needs=dict(pkg=pkg), pick=[])), True)


if __name__ == '__main__':
    unittest.main()
