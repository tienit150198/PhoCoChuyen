"""✏️ Tiệm văn phòng phẩm Bút Mây (game/careers/stationery.py on counterkit.py): every notebook, pen, tool and bag is on
the counter, with covering, labels and photocopies as services that use up their material (cover paper, labels, A4).
A parent's class list is read out as "vở": the shop must know that grades 1–5 write in squared notebooks (vở ô li) and
grade 6 on in lined ones (vở kẻ ngang). A photocopy order is counted in runs of 10 pages. Open to everyone from chapter
1, dormant until worked, strict saves."""
import copy
import unittest

from tests.helpers import Journey, new_state
from game import journey as jr
from game.careers import ORDER, PLUGINS, counterkit as ck, kit
from game.engine import DORMANT, GameError, dormant_out, initial_career, validate_state

M = PLUGINS.get('stationery')
if M is not None:
    from game.careers import stationery_content as MC


def data(j):
    return j.c['ext']['data']


def find(pred, day=1):
    for d in range(day, day + 80):
        for slot in range(12):
            _, needs, _ = M.order(d, slot)
            if pred(needs):
                return d, slot
    raise AssertionError('no such order')


def shop(pred, day=1):
    d, slot = find(pred, day)
    return Journey('stationery', day=d, slot=slot)


def right_basket(t):
    tray = {}
    for ln in t['needs']['lines']:
        k = min(ln['any'], key=lambda x: (MC.GOODS[x]['price'], x))
        tray[k] = tray.get(k, 0) + ln['qty']
    return tray


def fill(j, tid, tray):
    for k, q in tray.items():
        while q:
            n = min(q, ck.ADD_MAX)
            j.act('vp_add', task=tid, item=k, qty=n)
            q -= n


def solve(j, tid=None):
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    fill(j, tid, right_basket(j.get(tid)))
    return j.act('vp_serve', task=tid)


@unittest.skipIf(M is None, 'stationery filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_last_dormant_and_open_to_everyone(self):
        self.assertEqual(ORDER[ORDER.index('canteen') + 1], 'stationery')
        self.assertIn('stationery', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['stationery'], 1)
        s = new_state()
        s['journey']['story'] = True
        self.assertTrue(jr.is_unlocked(s, 'stationery'))
        self.assertEqual((M.SPEC['category'], M.SPEC['prefix']), ('shop', 'vp_'))

    def test_goods_services_and_surprises(self):
        self.assertGreaterEqual(len(MC.DESK), 8)
        self.assertEqual(len({x['id'] for x in MC.DESK}), len(MC.DESK))
        for k, g in MC.GOODS.items():
            self.assertTrue(k.startswith('vp_'))
            if g.get('service'):
                self.assertIn(g['uses'], MC.GOODS)
                self.assertFalse(MC.GOODS[g['uses']].get('service'))
            else:
                self.assertLess(g['cost'], g['price'], k)
        self.assertEqual({i['id'] for i in M.ITEMS}, {k for k, g in MC.GOODS.items() if not g.get('service')})


@unittest.skipIf(M is None, 'stationery filtered out by MNL_CAREERS')
class Orders(unittest.TestCase):
    def test_an_order_is_pure_and_a_class_list_names_the_grade_s_notebook(self):
        kinds = set()
        for day in range(1, 40):
            for slot in range(12):
                a = M.order(day, slot)
                self.assertEqual(a, M.order(day, slot))
                npc, needs, say = a
                kinds.add(needs['kind'])
                self.assertTrue(say)
                for ln in needs['lines']:
                    self.assertTrue(ln['any'] and set(ln['any']) <= set(MC.GOODS))
                self.assertLessEqual(sum(right_basket(dict(needs=needs)).values()), ck.TRAY_MAX)
                if needs['kind'] == 'list':
                    want = 'vp_vo_oli' if needs['grade'] <= 5 else 'vp_vo_ke'
                    self.assertEqual(needs['lines'][0]['any'], [want])
                    self.assertIn(f'lớp {needs["grade"]}', say)
                if needs['kind'] == 'photo':
                    self.assertEqual(needs['lines'][0]['qty'] * 10, needs['sets'] * needs['pages'])
                if needs['budget'] is not None:
                    self.assertGreaterEqual(needs['budget'], ck.bill(M.SHOP, right_basket(dict(needs=needs))))
        self.assertEqual(kinds, {'le', 'budget', 'list', 'boc', 'photo'})
        self.assertEqual((M.notebook(1), M.notebook(5), M.notebook(6), M.notebook(9)), ('vp_vo_oli', 'vp_vo_oli', 'vp_vo_ke', 'vp_vo_ke'))


@unittest.skipIf(M is None, 'stationery filtered out by MNL_CAREERS')
class Counter(unittest.TestCase):
    def test_a_class_list_with_the_wrong_notebook_is_sent_back(self):
        j = shop(lambda n: n['kind'] == 'list' and n['grade'] <= 5, day=2)
        tid = j.task['id']
        j.act('ask', task=tid)
        right = right_basket(j.task)
        wrong = dict(right)
        wrong['vp_vo_ke'] = wrong.pop('vp_vo_oli')
        fill(j, tid, wrong)
        out = j.act('vp_serve', task=tid)
        self.assertIn('Còn thiếu', out['message'])
        self.assertIn('vở ô li', out['message'])
        j.act('vp_clear', task=tid)
        fill(j, tid, right)
        j.state['journey'].setdefault('certificates', {})['stationery_basics'] = dict(score=90, best=90, earned_day=1, attempts=1)
        out = j.act('vp_serve', task=tid)
        t = j.get(tid)
        self.assertEqual((t['status'], t['quality'], t['paid']), ('completed', 90, ck.bill(M.SHOP, right)))
        self.assertIn('chứng chỉ', out['message'])
        validate_state(j.state)

    def test_covering_uses_the_cover_paper_and_photocopies_the_a4(self):
        j = shop(lambda n: n['kind'] == 'boc' and len(n['lines']) == 2, day=4)
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.task['needs']['lines'][0]['qty']
        paper, labels = kit.stock(j.c, 'vp_giay_boc'), kit.stock(j.c, 'vp_nhan')
        solve(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertEqual((kit.stock(j.c, 'vp_giay_boc'), kit.stock(j.c, 'vp_nhan')), (paper - n, labels - n))
        validate_state(j.state)
        j = shop(lambda n: n['kind'] == 'photo')
        tid = j.task['id']
        j.act('ask', task=tid)
        runs = j.task['needs']['lines'][0]['qty']
        a4 = kit.stock(j.c, 'vp_a4')
        solve(j, tid)
        self.assertEqual(kit.stock(j.c, 'vp_a4'), a4 - runs)
        validate_state(j.state)

    def test_a_service_waits_for_its_material(self):
        j = shop(lambda n: n['kind'] == 'photo')
        tid = j.task['id']
        j.act('ask', task=tid)
        kit.take(j.c, 'vp_a4', kit.stock(j.c, 'vp_a4'))
        self.assertEqual(kit.stock(j.c, 'vp_a4'), 0)
        with self.assertRaises(GameError):
            j.act('vp_add', task=tid, item='vp_photo')

    def test_pocket_money(self):
        j = shop(lambda n: n['kind'] == 'budget', day=2)
        tid = j.task['id']
        j.act('ask', task=tid)
        fill(j, tid, {'vp_vo_ke': 1, 'vp_but_may': 1})
        out = j.act('vp_serve', task=tid)
        self.assertIn('xu thôi à', out['message'])
        j.act('vp_clear', task=tid)
        solve(j, tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        validate_state(j.state)

    def test_a_tampered_save_is_refused(self):
        j = shop(lambda n: n['kind'] == 'le')
        tid = j.task['id']
        j.act('ask', task=tid)
        fill(j, tid, right_basket(j.task))
        validate_state(j.state)
        for field, value in (('quality', 50), ('paid', 9), ('tray', {'vp_khong_co': 1}), ('stage', 'done'), ('wrong', 2)):
            s = copy.deepcopy(j.state)
            s['careers']['stationery']['tasks'][0][field] = value
            with self.assertRaises(GameError, msg=field):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['stationery']['tasks'][0]['needs']['lines'][0]['qty'] = 99
        with self.assertRaises(GameError):
            validate_state(s)


@unittest.skipIf(M is None, 'stationery filtered out by MNL_CAREERS')
class Days(unittest.TestCase):
    def test_a_few_days_play_through(self):
        j = Journey('stationery')
        j.act('vp_intro')
        for _ in range(3):
            for t in [t for t in j.c['tasks'] if t['status'] not in ck.DONE]:
                if data(j)['desk']['ev']:
                    x = next(x for x in MC.DESK if x['id'] == data(j)['desk']['ev']['script'])
                    j.act('vp_desk', option=next(o['id'] for o in x['options'] if o.get('good')))
                solve(j, t['id'])
            j.act('end_day', carry_event=True)
            validate_state(j.state)
            j.act('start_day')
            validate_state(j.state)
        self.assertGreaterEqual(data(j)['stats']['jobs'], 6)

    def test_an_untouched_shop_is_left_out_of_the_stored_text(self):
        j = Journey('milk_tea')
        self.assertEqual(j.state['careers']['stationery'], initial_career('stationery'))
        self.assertNotIn('stationery', dormant_out(j.state)['careers'])


if __name__ == '__main__':
    unittest.main()
