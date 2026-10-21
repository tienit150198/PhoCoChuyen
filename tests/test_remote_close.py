"""📲 Máy quản lý từ xa: khép ca từ xa (game/remote_close.py, player feedback #456). The device is bought once at 📱 Mây
Mobile; with it end_day {remote: true} closes a workplace's shift from anywhere through the shop's own end_day (the
same money, stock, stats and life day), keeps the player where they are, and works before and during a contract
abroad. Without it the command is refused and nothing changes; a second close changes nothing."""
import copy
import unittest
from unittest import mock

from game import abroad as ab
from game import abroad_content as AC
from game import gadgets as gd
from game import pay_boost
from game import auto_order
from game import remote_close as rc
from game.engine import GameError, apply_action, new_state, public_state, validate_state
from tests.helpers import Journey
from tests.test_promotion import employee, story

HOME, AWAY = 'mother_baby', 'grocery'


def act(s, cid, name, **p):
    return apply_action(s, cid, name, p)


def same_clock(fn):
    """Both closes on one wall-clock second (the interest clock stamps real time)."""
    def run(*a, **k):
        with mock.patch('time.time', return_value=1_792_598_079.5):
            return fn(*a, **k)
    run.__name__ = fn.__name__
    return run


def buy(s):
    return act(s, None, 'jr_gadget_buy', id=rc.ITEM, confirm=True)


def two_shops(own=True, wallet=10000):
    """A story save with two shifts open: HOME left with its customers, AWAY on screen with three waiting."""
    j = Journey(HOME)
    story(j)
    s = j.state
    s['journey']['gender'] = 'female'
    s['journey']['wallet'] = wallet
    if own:
        s, _ = buy(s)
    s, _ = act(s, AWAY, 'select_career', confirm=True)
    s, _ = act(s, AWAY, 'start_day')
    s['careers'][HOME]['day_completed'] = 2
    validate_state(s)
    return s


def refused(test, s, career, code, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, career, 'end_day', **p)
    test.assertEqual(s, before)   # a refusal changes nothing
    test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


class Device(unittest.TestCase):
    def test_sold_once_at_may_mobile_mid_game_price(self):
        it = gd.ITEMS[rc.ITEM]
        self.assertEqual((it['group'], it['emoji'], it['name'], it['price']), ('tool', '📲', 'Máy quản lý từ xa', 5500))
        self.assertIn(('tool', '📲', 'Tiện ích'), gd.GROUPS)
        self.assertLess(pay_boost.FAST_PRICE, it['price'])            # above ⏩ Làm nhanh (2.750)
        self.assertLess(it['price'], auto_order.BOX_PRICE)            # under 📦 Gộp thùng tự đặt (10.000)
        self.assertNotIn(rc.ITEM, [x['id'] for x in gd.catalogue()['items'] if x['group'] == 'gear'])
        s = two_shops(own=False)
        w = s['journey']['wallet']
        self.assertFalse(public_state(s)['journey']['remote']['own'])
        s, r = buy(s)
        self.assertEqual(s['journey']['wallet'], w - 5500)
        self.assertTrue(rc.owned(s))
        self.assertTrue(public_state(s)['journey']['remote']['own'])
        s2, r = buy(s)                                                 # a second tap: nothing paid again
        self.assertTrue(r['duplicate'])
        self.assertEqual(s2['journey']['wallet'], w - 5500)
        self.assertIsNone(gd.show_view(s))                             # a tool, not shown off on the card

    def test_refused_without_the_device(self):
        s = two_shops(own=False)
        why = refused(self, s, HOME, 'need_device', remote=True)
        self.assertIn('Máy quản lý từ xa', why)
        self.assertIn('Mây Mobile', why)
        free = new_state()                                             # the free sandbox has no Mây Mobile
        free, _ = act(free, HOME, 'select_career')
        free, _ = act(free, HOME, 'start_day')
        refused(self, free, HOME, 'need_device', remote=True)

    def test_selling_the_device_back_ends_it(self):
        s = two_shops()
        s, _ = act(s, None, 'jr_gadget_sell', id=rc.ITEM, confirm=True)
        refused(self, s, HOME, 'need_device', remote=True)


class Closing(unittest.TestCase):
    @same_clock
    def test_same_as_closing_at_the_shop(self):
        s = two_shops()
        at = copy.deepcopy(s)
        at['current'] = HOME                                           # standing in the shop, nothing left behind
        a, ra = act(at, HOME, 'end_day', carry_event=True)
        b, rb = act(copy.deepcopy(s), HOME, 'end_day', remote=True)
        self.assertEqual((a['current'], b['current']), (HOME, AWAY))   # the remote close leaves you where you were
        a['current'] = b['current']
        self.assertEqual(a, b)                                         # money, stock, stats, wallet, life day: all the same
        self.assertEqual(ra['summary'], rb['summary'])
        self.assertEqual(ra['effects'], rb['effects'])
        c = b['careers'][HOME]
        self.assertFalse(c['open'])
        self.assertEqual(c['shift_summary']['completed'], 2)
        self.assertEqual(rb['remote'], HOME)
        self.assertIn('📲 Đã khép ca từ xa', rb['message'])
        self.assertEqual(b['journey']['life_day'], s['journey']['life_day'] + 1)
        validate_state(b)

    def test_the_place_on_screen_is_not_left(self):
        s = two_shops()
        here = copy.deepcopy(s['careers'][AWAY])
        s2, r = act(s, HOME, 'end_day', remote=True)
        self.assertNotIn('abandon', r)
        self.assertEqual(s2['current'], AWAY)
        self.assertTrue(s2['careers'][AWAY]['open'])
        self.assertEqual(s2['careers'][AWAY]['tasks'], here['tasks'])  # its waiting customers are still there
        self.assertEqual(s2['careers'][AWAY]['money'], here['money'])  # no fine for leaving
        v = public_state(s2)['journey']['remote']
        self.assertEqual([x['career'] for x in v['shops']], [AWAY])

    def test_a_running_event_is_carried_like_the_shop_close(self):
        s = two_shops()
        s, _ = act(s, HOME, 'select_career', confirm=True)
        s, _ = act(s, HOME, 'event_start', event='MB-E07')
        s, _ = act(s, AWAY, 'select_career', confirm=True)
        self.assertNotEqual(s['careers'][HOME]['event']['stage'], 'resolved')
        before = copy.deepcopy(s)
        with self.assertRaises(GameError):                             # at the shop: carry it or finish it first
            act(before, HOME, 'end_day')
        s2, _ = act(s, HOME, 'end_day', remote=True)
        self.assertFalse(s2['careers'][HOME]['open'])
        self.assertTrue(s2['careers'][HOME]['event'])                  # waits for tomorrow, as "Khép ca" does
        v = public_state(s)['journey']['remote']['shops']
        self.assertTrue(next(x for x in v if x['career'] == HOME)['event'])

    def test_a_second_close_changes_nothing(self):
        s = two_shops()
        s, _ = act(s, HOME, 'end_day', remote=True)
        again, r = act(copy.deepcopy(s), HOME, 'end_day', remote=True)
        self.assertTrue(r['duplicate'])
        self.assertEqual(again, s)
        with self.assertRaises(GameError):                             # the shop's own button still says so
            act(s, HOME, 'end_day', carry_event=True)

    @same_clock
    def test_close_where_you_stand(self):
        s = two_shops()
        a, ra = act(copy.deepcopy(s), AWAY, 'end_day', carry_event=True)
        b, rb = act(copy.deepcopy(s), AWAY, 'end_day', remote=True)
        self.assertEqual(a, b)
        self.assertEqual(ra['summary'], rb['summary'])

    def test_public_view(self):
        s = two_shops(own=False)
        v = public_state(s)['journey']['remote']
        self.assertEqual(v['item'], rc.ITEM)
        here = {x['career']: x for x in v['shops']}
        self.assertEqual(set(here), {HOME, AWAY})
        self.assertTrue(here[AWAY]['here'])
        self.assertEqual((here[HOME]['done'], here[AWAY]['left']), (2, 3))
        for cid in (HOME, AWAY):
            s['careers'][cid]['open'] = False
        self.assertNotIn('remote', public_state(s)['journey'])         # nothing open, no device: no key at all


class Abroad(unittest.TestCase):
    @same_clock
    def test_close_every_shift_then_leave_and_close_abroad(self):
        j = employee('delivery')
        s = j.state
        s['journey']['gender'] = 'female'
        s['journey']['wallet'] = 20000
        j.act('end_day', carry_event=True)                             # the first shift, off probation
        j.c['job']['probation'] = False
        s = j.state
        s, _ = act(s, 'delivery', 'start_day')
        s, _ = act(s, 'pho', 'select_career', confirm=True)
        s, _ = act(s, 'pho', 'start_day')
        with self.assertRaises(GameError) as e:
            act(s, None, 'jr_abroad_work', to='han_quoc', career='delivery', confirm=True)
        self.assertEqual(e.exception.code, 'shift_open')
        s, _ = buy(s)
        for cid in ('delivery', 'pho'):
            s, r = act(s, cid, 'end_day', remote=True)
            self.assertEqual(s['current'], 'pho')
        s, r = act(s, None, 'jr_abroad_work', to='han_quoc', career='delivery', confirm=True)
        self.assertTrue(ab.contract(s))
        base = s['careers']['delivery']['job']['salary']
        s, _ = act(s, 'delivery', 'start_day')
        s['careers']['delivery']['day_completed'] = 2
        at = copy.deepcopy(s)
        s['current'] = 'pho'                                           # looking at home from the branch's city
        s, r = act(s, 'delivery', 'end_day', remote=True)
        a, ra = act(at, 'delivery', 'end_day', carry_event=True)
        self.assertEqual(r['summary']['job']['salary'], round(base * (100 + AC.WORK['han_quoc']['pct']) / 100))
        self.assertEqual(s['journey']['abroad']['work']['n'], 1)       # a day abroad, counted like at the branch
        self.assertTrue(any(x.startswith('🌏 Ngày') for x in r['effects']))
        self.assertEqual(r['summary'], ra['summary'])
        a['current'] = s['current']
        self.assertEqual(a, s)
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
