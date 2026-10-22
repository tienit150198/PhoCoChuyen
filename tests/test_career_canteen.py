"""🍱 Căn tin trường Tiểu học Phố Mây (game/careers/canteen.py on counterkit.py): a selling game. Every good is on the
counter; the player hears the student, taps goods into the tray and hands it over. The morning rush and recess wait for
the school drum (a student still waiting when it sounds runs back to class, unserved); lunch trays for a class need the
day's food sample first. Allergies, vegetarian days and pocket money are checked by the server; the client never sees
which goods answer a line. Open to everyone from chapter 1, dormant until worked, strict saves."""
import copy
import unittest

from tests.helpers import Journey, new_state
from game import journey as jr
from game.careers import ORDER, PLUGINS, counterkit as ck, kit
from game.engine import DORMANT, GameError, dormant_out, initial_career, public_state, validate_state

M = PLUGINS.get('canteen')
if M is not None:
    from game.careers import canteen_content as MC


def data(j):
    return j.c['ext']['data']


def find(pred, day=1):
    """The first (day, slot) from `day` on whose order passes pred(phase, needs)."""
    for d in range(day, day + 80):
        for slot in range(12):
            ph, _, needs, _ = M.order(d, slot)
            if pred(ph, needs):
                return d, slot
    raise AssertionError('no such order')


def counter(pred, day=1):
    d, slot = find(pred, day)
    return Journey('canteen', day=d, slot=slot)


def right_tray(t):
    """A tray that answers every line: the cheapest good of a line that the student can eat."""
    tray = {}
    for ln in t['needs']['lines']:
        ok = [k for k in ln['any'] if not set(MC.GOODS[k].get('tags', ())) & set(t['needs']['avoid'])]
        k = min(ok, key=lambda x: (MC.GOODS[x]['price'], x))
        tray[k] = tray.get(k, 0) + ln['qty']
    return tray


def fill(j, tid, tray):
    for k, q in tray.items():
        j.act('ct_add', task=tid, item=k, qty=q)


def solve(j, tid=None):
    tid = tid or j.task['id']
    if not j.get(tid)['known']:
        j.act('ask', task=tid)
    t = j.get(tid)
    if t['needs'].get('sample') and data(j)['sampled_day'] != j.c['day']:
        j.act('ct_sample')
    fill(j, tid, right_tray(j.get(tid)))
    return j.act('ct_serve', task=tid)


@unittest.skipIf(M is None, 'canteen filtered out by MNL_CAREERS')
class Registration(unittest.TestCase):
    def test_registered_after_the_dealer_dormant_and_open_to_everyone(self):
        self.assertEqual(tuple(ORDER[ORDER.index('car_dealer'):ORDER.index('car_dealer') + 3]), ('car_dealer', 'canteen', 'stationery'))
        self.assertIn('canteen', DORMANT)
        self.assertEqual(jr.LATE_UNLOCKS['canteen'], 1)
        s = new_state()
        s['journey']['story'] = True
        self.assertTrue(jr.is_unlocked(s, 'canteen'))
        self.assertEqual((M.SPEC['category'], M.SPEC['prefix']), ('shop', 'ct_'))
        self.assertNotIn('employment', M.SPEC)

    def test_content_goods_and_surprises(self):
        self.assertGreaterEqual(len(MC.DESK), 10)
        self.assertEqual(len({x['id'] for x in MC.DESK}), len(MC.DESK))
        for k, g in MC.GOODS.items():
            self.assertTrue(k.startswith('ct_'))
            self.assertLess(g['cost'], g['price'], k)
            self.assertIn(g['group'], dict(MC.GROUPS))
        self.assertLessEqual(set(MC.SAY), set(MC.GOODS))
        self.assertEqual({i['id'] for i in M.ITEMS}, set(MC.GOODS))


@unittest.skipIf(M is None, 'canteen filtered out by MNL_CAREERS')
class Orders(unittest.TestCase):
    def test_an_order_is_pure_answerable_and_fits_the_tray(self):
        kinds = set()
        for day in range(1, 40):
            for slot in range(12):
                a, b = M.order(day, slot), M.order(day, slot)
                self.assertEqual(a, b)
                ph, npc, needs, say = a
                kinds.add((ph, needs['kind']))
                self.assertEqual(ph, M.phase(day, slot))
                self.assertTrue(say)
                for ln in needs['lines']:
                    self.assertTrue(ln['any'] and set(ln['any']) <= set(MC.GOODS))
                    self.assertTrue(any(not set(MC.GOODS[k].get('tags', ())) & set(needs['avoid']) for k in ln['any']), ln)
                tray = right_tray(dict(needs=needs))
                self.assertLessEqual(sum(tray.values()), ck.TRAY_MAX)
                if needs['budget'] is not None:
                    self.assertGreaterEqual(needs['budget'], ck.bill(M.SHOP, tray))
                if ph == 'trua':
                    self.assertGreaterEqual(day, MC.MILESTONES[0])
                    self.assertTrue(needs['sample'])
                else:
                    self.assertGreater(needs['bell'], 0)
        self.assertLessEqual({('sang', 'order'), ('sang', 'allergy'), ('sang', 'chay'), ('sang', 'budget'), ('ra_choi', 'group'),
                              ('ra_choi', 'allergy'), ('ra_choi', 'budget'), ('trua', 'trua')}, kinds)

    def test_the_client_never_sees_which_goods_answer_a_line(self):
        j = counter(lambda ph, n: n['kind'] == 'allergy')
        tid = j.task['id']
        view = public_state(j.state)['careers']['canteen']
        task = next(t for t in view['tasks'] if t['id'] == tid)
        self.assertIsNone(task['needs'])
        j.act('ask', task=tid)
        task = next(t for t in public_state(j.state)['careers']['canteen']['tasks'] if t['id'] == tid)
        self.assertTrue(task['needs']['avoid'])
        for ln in task['needs']['lines']:
            self.assertEqual(set(ln), {'id', 'qty'})


@unittest.skipIf(M is None, 'canteen filtered out by MNL_CAREERS')
class Counter(unittest.TestCase):
    def test_a_right_tray_is_paid_and_leaves_the_shelf(self):
        j = counter(lambda ph, n: n['kind'] == 'order')
        tid = j.task['id']
        j.act('ask', task=tid)
        tray = right_tray(j.task)
        stock = {k: kit.stock(j.c, k) for k in tray}
        money = j.c['money']
        fill(j, tid, tray)
        out = j.act('ct_serve', task=tid)
        t = j.get(tid)
        self.assertEqual(t['status'], 'completed')
        self.assertEqual((t['quality'], t['paid']), (100, ck.bill(M.SHOP, tray)))
        self.assertIn('Giao đủ cho', out['message'])
        for k, q in tray.items():
            self.assertEqual(kit.stock(j.c, k), stock[k] - q)
        self.assertGreater(j.c['money'], money)
        self.assertEqual(data(j)['stats']['jobs'], 1)
        validate_state(j.state)

    def test_a_short_tray_stays_open_costs_quality_and_names_what_is_missing(self):
        j = counter(lambda ph, n: n['kind'] == 'order' and len(n['lines']) >= 2)
        tid = j.task['id']
        j.act('ask', task=tid)
        tray = right_tray(j.task)
        first = next(iter(tray))
        j.act('ct_add', task=tid, item=first, qty=tray[first])
        out = j.act('ct_serve', task=tid)
        self.assertIn('Còn thiếu', out['message'])
        t = j.get(tid)
        self.assertEqual((t['status'] in ('completed', 'referred'), t['quality'], t['errors']), (False, 90, ['missing']))
        validate_state(j.state)
        fill(j, tid, {k: q for k, q in tray.items() if k != first})
        j.act('ct_serve', task=tid)
        self.assertEqual((j.get(tid)['status'], j.get(tid)['quality']), ('completed', 90))
        validate_state(j.state)

    def test_an_allergic_student_refuses_the_milk(self):
        j = counter(lambda ph, n: n['kind'] == 'allergy' and 'milk' in n['avoid'] and ph == 'sang')
        tid = j.task['id']
        j.act('ask', task=tid)
        tray = right_tray(j.task)
        drink = next(ln for ln in j.task['needs']['lines'] if 'ct_sua_hop' in ln['any'])
        tray = {k: q for k, q in tray.items() if k not in drink['any']}
        tray['ct_sua_hop'] = 1
        fill(j, tid, tray)
        out = j.act('ct_serve', task=tid)
        self.assertIn('không ăn được sữa', out['message'])
        self.assertEqual(j.get(tid)['errors'], ['avoid'])
        validate_state(j.state)

    def test_pocket_money_caps_the_tray(self):
        j = counter(lambda ph, n: n['kind'] == 'budget')
        tid = j.task['id']
        j.act('ask', task=tid)
        dear = max(MC.FOODS, key=lambda k: MC.GOODS[k]['price'])
        fill(j, tid, {dear: 2, 'ct_sua_hop': 2})
        out = j.act('ct_serve', task=tid)
        self.assertIn('xu thôi à', out['message'])
        self.assertEqual(j.get(tid)['errors'], ['budget'])
        validate_state(j.state)

    def test_lunch_waits_for_the_food_sample_once_a_day_and_the_certificate_adds_two(self):
        j = counter(lambda ph, n: ph == 'trua', day=MC.MILESTONES[0])
        tid = j.task['id']
        j.act('ask', task=tid)
        fill(j, tid, right_tray(j.task))
        out = j.act('ct_serve', task=tid)
        self.assertIn('Lưu mẫu', out['message'])
        self.assertEqual(j.get(tid)['errors'], ['sample'])
        j.act('ct_sample')
        with self.assertRaises(GameError):
            j.act('ct_sample')
        j.state['journey'].setdefault('certificates', {})['canteen_basics'] = dict(score=90, best=90, earned_day=1, attempts=1)
        money = j.c['money']
        out = j.act('ct_serve', task=tid)
        self.assertEqual(j.get(tid)['status'], 'completed')
        self.assertIn('chứng chỉ', out['message'])
        self.assertGreaterEqual(j.c['money'] - money, j.get(tid)['paid'] + 2 - 1)

    def test_an_order_is_heard_before_the_tray(self):
        j = counter(lambda ph, n: n['kind'] == 'order')
        with self.assertRaises(GameError):
            j.act('ct_add', task=j.task['id'], item='ct_xoi')
        j.act('ask', task=j.task['id'])
        with self.assertRaises(GameError):
            j.act('ct_add', task=j.task['id'], item='ct_khong_co')
        with self.assertRaises(GameError):
            j.act('ct_add', task=j.task['id'], item='ct_xoi', qty=ck.ADD_MAX + 1)


@unittest.skipIf(M is None, 'canteen filtered out by MNL_CAREERS')
class Bell(unittest.TestCase):
    def test_the_drum_sends_a_waiting_student_back_to_class_unserved(self):
        j = counter(lambda ph, n: ph == 'sang')
        tid = j.task['id']
        j.act('ask', task=tid)
        j.act('ct_add', task=tid, item=next(iter(right_tray(j.task))))
        j.c['metrics']['served'] = ck.LEARN
        j.c['turn'] = j.task['created_turn'] + j.task['needs']['bell']
        self.assertTrue(ck.bell_due(j.c, j.task))
        money, stock = j.c['money'], {k: kit.stock(j.c, k) for k in MC.GOODS}
        out = j.act('ct_add', task=tid, item='ct_xoi')   # the tap was for the student who just left: a message, not an error
        self.assertIn('Trống trường đã đánh', out['message'])
        t = j.get(tid)
        self.assertEqual((t['status'], t['tray'], t['paid']), ('referred', {}, 0))
        self.assertEqual(data(j)['stats']['missed'], 1)
        self.assertEqual(j.c['money'], money)
        self.assertEqual({k: kit.stock(j.c, k) for k in MC.GOODS}, stock)
        self.assertEqual(M.feedback(j.c, t)['cap'], 2)
        validate_state(j.state)

    def test_a_calm_shift_and_the_first_customers_have_no_drum(self):
        j = counter(lambda ph, n: ph == 'sang')
        j.c['turn'] = j.task['created_turn'] + 999
        self.assertFalse(ck.bell_due(j.c, j.task))   # metrics served < LEARN
        j.c['metrics']['served'] = ck.LEARN
        j.c['life']['mode'] = 'calm'
        self.assertFalse(ck.bell_due(j.c, j.task))


@unittest.skipIf(M is None, 'canteen filtered out by MNL_CAREERS')
class Saves(unittest.TestCase):
    def test_a_tampered_save_is_refused(self):
        j = counter(lambda ph, n: n['kind'] == 'order')
        tid = j.task['id']
        j.act('ask', task=tid)
        fill(j, tid, right_tray(j.task))
        validate_state(j.state)
        for field, value in (('quality', 50), ('paid', 9), ('tray', {'ct_khong_co': 1}), ('tray', {'ct_xoi': 0}),
                             ('stage', 'done'), ('errors', ['missing']), ('wrong', 3), ('cogs', -1)):
            s = copy.deepcopy(j.state)
            s['careers']['canteen']['tasks'][0][field] = value
            with self.assertRaises(GameError, msg=field):
                validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['canteen']['tasks'][0]['needs']['budget'] = 999
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['canteen']['ext']['data']['stats']['good'] = 10**6
        with self.assertRaises(GameError):
            validate_state(s)
        s = copy.deepcopy(j.state)
        s['careers']['canteen']['ext']['data']['sampled_day'] = 'x'
        with self.assertRaises(GameError):
            validate_state(s)

    def test_a_surprise_blocks_the_counter_until_decided(self):
        j = counter(lambda ph, n: n['kind'] == 'order')
        d = data(j)
        x = MC.DESK[0]
        d['desk'].update(day=j.c['day'], ev=dict(id='desk-1', script=x['id'], day=j.c['day'], at='between'), seq=1, fired=1)
        validate_state(j.state)
        tid = j.task['id']
        j.act('ask', task=tid)
        with self.assertRaises(GameError):
            j.act('ct_add', task=tid, item='ct_xoi')
        j.act('ct_desk', option=next(o['id'] for o in x['options'] if o.get('good')))
        j.act('ct_add', task=tid, item='ct_xoi')
        validate_state(j.state)


@unittest.skipIf(M is None, 'canteen filtered out by MNL_CAREERS')
class Days(unittest.TestCase):
    def test_a_few_days_play_through(self):
        j = Journey('canteen')
        j.act('ct_intro')
        for _ in range(3):
            self.assertEqual(len([t for t in j.c['tasks'] if t['status'] not in ck.DONE]), 4)
            for t in [t for t in j.c['tasks'] if t['status'] not in ck.DONE]:
                if data(j)['desk']['ev']:
                    x = next(x for x in MC.DESK if x['id'] == data(j)['desk']['ev']['script'])
                    j.act('ct_desk', option=next(o['id'] for o in x['options'] if o.get('good')))
                if j.get(t['id'])['status'] not in ck.DONE:
                    solve(j, t['id'])
            j.act('end_day', carry_event=True)
            validate_state(j.state)
            j.act('start_day')
            validate_state(j.state)
        self.assertGreaterEqual(data(j)['stats']['jobs'], 8)
        self.assertGreaterEqual(data(j)['stats']['active_days'], 1)

    def test_an_untouched_canteen_is_left_out_of_the_stored_text(self):
        j = Journey('milk_tea')
        self.assertEqual(j.state['careers']['canteen'], initial_career('canteen'))
        self.assertNotIn('canteen', dormant_out(j.state)['careers'])


if __name__ == '__main__':
    unittest.main()
