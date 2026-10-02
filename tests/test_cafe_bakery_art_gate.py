"""Sớm Mai (1.4.4, player confusion: "Rót sữa lên espresso — chiết shot trước đã." on 44 of 497 latte-art taps in a
day). cafe_bakery.js artWait() names what latte art still waits for and offers no tap until then; this mirrors it
over the public task and checks each verdict against the server's cb_art."""
import copy
import unittest

from game.engine import GameError, public_state
from tests import test_career_cafe_bakery as cbt   # its fixtures (not the class itself: it would run here too)


def art_wait(d):
    """cafe_bakery.js artWait over the public drink."""
    if not d['shots']:
        return 'Chiết shot trước'
    if d.get('steaming'):
        return 'Tắt vòi hơi trước'
    if not (d.get('milk') and d['milk']['mode'] == 'steam'):
        return 'Đánh sữa nóng trước'
    return ''


class ArtGate(unittest.TestCase):
    setUp = cbt.CafeBakeryTests.setUp
    tearDown = cbt.CafeBakeryTests.tearDown
    journey = cbt.CafeBakeryTests.journey
    stock_up = cbt.CafeBakeryTests.stock_up

    def pub_drink(self, tid):
        return next(t for t in public_state(self.j.state)['careers']['cafe_bakery']['tasks'] if t['id'] == tid)['drink']

    def check(self, tid, pattern, want):
        self.assertEqual(art_wait(self.pub_drink(tid)), want)
        if want:
            before = copy.deepcopy(self.j.state)
            with self.assertRaises(GameError):
                self.j.act('cb_art', task=tid, pattern=pattern)
            self.assertEqual(self.j.state, before)
        else:
            self.j.act('cb_art', task=tid, pattern=pattern)
            self.assertIsNotNone(self.j.get(tid)['drink']['art'])

    def hot_art_order(self):
        j = self.journey(lambda n: n['kind'] == 'drink' and n['milk'] and not n['iced'] and n['art'] and n['shots'] == 1, days=range(1, 30))
        tid = j.task['id']
        j.act('ask', task=tid)
        n = j.get(tid)['needs']
        j.act('cb_cup', task=tid, kind='paper' if n['takeaway'] else 'mug', size=n['size'])
        return j, tid, n

    def pull(self, j, tid, n):
        j.act('cb_dose', task=tid, beans=n['beans'], grind='fine', grams=18)
        j.act('cb_pull', task=tid)
        self.clock.t += 27
        j.act('cb_stop', task=tid)

    def test_milk_first_then_the_shot(self):
        j, tid, n = self.hot_art_order()
        self.check(tid, n['art'], 'Chiết shot trước')
        j.act('cb_milk', task=tid, milk=n['milk'], mode='steam', foam=n['foam'])
        self.check(tid, n['art'], 'Chiết shot trước')
        self.clock.t += 13
        j.act('cb_milk_stop', task=tid)
        self.check(tid, n['art'], 'Chiết shot trước')
        self.pull(j, tid, n)
        self.check(tid, n['art'], '')

    def test_shot_first_then_the_milk(self):
        j, tid, n = self.hot_art_order()
        self.pull(j, tid, n)
        self.check(tid, n['art'], 'Đánh sữa nóng trước')
        j.act('cb_milk', task=tid, milk=n['milk'], mode='steam', foam=n['foam'])
        self.check(tid, n['art'], 'Tắt vòi hơi trước')
        self.clock.t += 13
        j.act('cb_milk_stop', task=tid)
        self.check(tid, n['art'], '')


if __name__ == '__main__':
    unittest.main()
