"""Players #427 #431 (ginnytina.25, tiệm áo, 19/10): "đếm từng món rồi nhập hàng luôn thay vì đợi đến hết" and
"thuê nhân viên rồi thì nhân viên cũng phải phụ". A merged crate (đơn gộp, 📦 thùng tự đặt) goes onto the shelf line
by line, as each line is counted (inv_receive {group|box, counts} with only the counted lines); the rest stays at the
door. 👥 Nhân viên đếm giúp (inv_receive {staff: true}): a staff member on shift counts every crate at the door.
Counts stay server-checked: a wrong count receives nothing, nothing is received twice, nothing is free."""
import copy
import unittest

from game import inventory as I
from game.engine import GameError, public_state, validate_state
from tests.test_inventory_cart import add, fresh, group_lines, place
from tests.test_inventory_flow import public_inv, set_money, wait_until_ready


def ready_group(j, career='restaurant'):
    for i, q in (('noodle', 6), ('egg', 5), ('sausage', 4)):
        add(j, 'partner', i, q)
    _, gid = place(j)
    wait_until_ready(j, f'{gid}-1')
    return gid


def hire(j, career='restaurant'):
    set_money(j.c, 5000)
    j.act('ops_hire', candidate=f'{career}-staff-1', confirm=True)
    e = j.c['ops']['staff'][0]
    e['on_shift'] = True
    return e


class LineByLine(unittest.TestCase):
    def test_one_line_now_the_rest_later(self):
        j = fresh()
        gid = ready_group(j)
        lines = group_lines(j, gid)
        first = lines[0]
        turn = j.c['turn']
        r = j.act('inv_receive', group=gid, counts={first['id']: first['actual']})
        self.assertIn('phần đã đếm', r['message'])
        self.assertIn('Còn 2 món', r['message'])
        self.assertEqual(j.c['turn'], turn + 1)
        self.assertEqual([o['status'] for o in group_lines(j, gid)], ['received', 'in_transit', 'in_transit'])
        self.assertEqual(I.count(j.c, first['item']), first['actual'])
        self.assertEqual(I.count(j.c, lines[1]['item']), 0, 'an uncounted line is not on the shelf')
        # The rest is still a crate at the door; the client sees it as such.
        pub = [o for o in public_inv(j)['orders'] if o.get('group') == gid and o['status'] == 'in_transit']
        self.assertEqual(len(pub), 2)
        self.assertTrue(all(o['ready_now'] and o['count_hint'] is not None for o in pub))
        # Rating waits for the whole order.
        with self.assertRaises(GameError):
            j.act('inv_rate', group=gid, stars=5)
        # A line already received cannot come in twice (its id is left out; nothing else given: refused).
        with self.assertRaises(GameError):
            j.act('inv_receive', group=gid, counts={first['id']: first['actual']})
        self.assertEqual(I.count(j.c, first['item']), first['actual'])
        rest = {o['id']: o['actual'] for o in group_lines(j, gid) if o['status'] == 'in_transit'}
        r = j.act('inv_receive', group=gid, counts=rest)
        self.assertIn('cả thùng', r['message'])
        self.assertTrue(all(o['status'] == 'received' for o in group_lines(j, gid)))
        j.act('inv_rate', group=gid, stars=5)
        validate_state(j.state)

    def test_a_wrong_count_receives_nothing(self):
        j = fresh()
        gid = ready_group(j)
        lines = group_lines(j, gid)
        before = copy.deepcopy(j.state)
        with self.assertRaises(GameError) as e:
            j.act('inv_receive', group=gid, counts={lines[0]['id']: lines[0]['actual'], lines[1]['id']: lines[1]['actual'] + 1})
        self.assertIn(I.item('restaurant', lines[1]['item'])['name'], e.exception.message)
        self.assertEqual(j.state, before)
        with self.assertRaises(GameError):
            j.act('inv_receive', group=gid, counts={})
        with self.assertRaises(GameError):
            j.act('inv_receive', group=gid, counts={lines[0]['id']: lines[0]['qty'] + 5})
        self.assertTrue(all(o['status'] == 'in_transit' for o in group_lines(j, gid)))

    def test_partial_short_line_is_claimed(self):
        j = fresh()
        gid = ready_group(j)
        lines = group_lines(j, gid)
        lines[0]['actual'] = lines[0]['qty'] - 1
        r = j.act('inv_receive', group=gid, counts={lines[0]['id']: lines[0]['actual']})
        self.assertEqual(r['short']['group'], gid)
        money = j.c['money']
        j.act('inv_claim', group=gid)
        self.assertGreater(j.c['money'], money)
        rest = {o['id']: o['actual'] for o in group_lines(j, gid) if o['status'] == 'in_transit'}
        j.act('inv_receive', group=gid, counts=rest)
        validate_state(j.state)

    def test_not_at_the_door_yet(self):
        j = fresh()
        for i, q in (('noodle', 6), ('egg', 5)):
            add(j, 'partner', i, q)
        _, gid = place(j)
        lines = group_lines(j, gid)
        with self.assertRaises(GameError) as e:
            j.act('inv_receive', group=gid, counts={lines[0]['id']: lines[0]['actual']})
        self.assertIn('Hàng chưa tới', e.exception.message)


class StaffCount(unittest.TestCase):
    def test_no_staff_no_help(self):
        j = fresh()
        ready_group(j)
        self.assertIsNone(public_inv(j)['helper'])
        with self.assertRaises(GameError) as e:
            j.act('inv_receive', staff=True)
        self.assertIn('nhân viên', e.exception.message)

    def test_staff_count_every_crate_at_the_door(self):
        j = fresh()
        e = hire(j)
        self.assertEqual(public_inv(j)['helper'], e['name'])
        gid = ready_group(j)
        lines = group_lines(j, gid)
        j.act('inv_receive', group=gid, counts={lines[0]['id']: lines[0]['actual']})   # one line by hand
        turn = j.c['turn']
        r = j.act('inv_receive', staff=True)
        self.assertIn(e['name'], r['message'])
        self.assertEqual(j.c['turn'], turn + 1, 'one shop step, like one crate')
        for o in group_lines(j, gid):
            self.assertEqual(o['status'], 'received')
            self.assertEqual(I.count(j.c, o['item']), o['actual'], 'the real count, once')
        with self.assertRaises(GameError):
            j.act('inv_receive', staff=True)   # nothing left at the door
        validate_state(j.state)

    def test_staff_leave_what_is_on_the_way_and_what_does_not_fit(self):
        j = fresh()
        hire(j)
        gid = ready_group(j)
        far = j.act('inv_order', item='mushroom', qty=3, supplier='partner', confirm=True)['eta']['order']
        lines = group_lines(j, gid)
        # The noodle shelf filled up meanwhile (a gift, a market buy): that line waits at the door.
        cap = I.capacity('restaurant', j.c)
        I.add_lot(j.c, 'noodle', cap - I.count(j.c, 'noodle'), 1, 9, 'market')
        r = j.act('inv_receive', staff=True)
        self.assertIn('còn chờ ở cửa', r['message'])
        status = {o['item']: o['status'] for o in group_lines(j, gid)}
        self.assertEqual(status['noodle'], 'in_transit')
        self.assertEqual(status['egg'], 'received')
        o = next(o for o in j.c['ext']['inv']['orders'] if o['id'] == far)
        self.assertEqual(o['status'], 'in_transit', 'a crate still on the road is not counted')
        self.assertEqual(len(lines), 3)
        validate_state(j.state)

    def test_staff_off_shift_cannot_help(self):
        j = fresh()
        e = hire(j)
        e['on_shift'] = False
        ready_group(j)
        self.assertIsNone(public_inv(j)['helper'])
        with self.assertRaises(GameError):
            j.act('inv_receive', staff=True)

    def test_public_state_carries_helper(self):
        j = fresh()
        hire(j)
        inv = public_state(j.state)['careers']['restaurant']['inventory']
        self.assertIn('helper', inv)


if __name__ == '__main__':
    unittest.main()
