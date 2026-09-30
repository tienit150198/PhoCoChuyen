"""PATIENCE_FACTOR (game/patience.py): waiting customers last longer, never shorter than before."""
import unittest
from unittest import mock
from game import patience as pt
from game import experiences as life
from game.careers import food_service as FS


def _room(career='mother_baby', kind=None):
    t = dict(id=f'{career}-3-1', career=career, status='new', mistakes=0, patience=100, guest=dict(kind=kind) if kind else None)
    active = dict(id=f'{career}-3-0', career=career, status='new', mistakes=0, patience=100)
    return dict(open=True, turn=0, life=dict(mode='normal'), active_task=active['id'], tasks=[active, t], ext=dict(data={})), t


def _turns_until_empty(factor, tick):
    """Physical actions a waiting customer sits through before the bar is at the floor (25)."""
    with mock.patch.object(pt, 'PATIENCE_FACTOR', factor):
        c, t = _room(kind='rush')
        for n in range(1, 1000):
            c['turn'] += 1
            before = t['patience']
            tick(c)
            assert before - t['patience'] >= 0
            if t['patience'] <= 25:
                return n
    raise AssertionError('never emptied')


class PatienceFactorTests(unittest.TestCase):
    def test_default_is_a_little_more_patient(self):
        self.assertEqual(pt.PATIENCE_FACTOR, 1.2)
        self.assertEqual(pt._factor('0.5'), 1.0)   # never less patient than the original tuning
        self.assertEqual(pt._factor('oops'), 1.2)

    def test_budgets_stretch_and_never_shrink(self):
        with mock.patch.object(pt, 'PATIENCE_FACTOR', 1.0):
            self.assertEqual([pt.longer(n) for n in (1, 4, 10, 25, 120)], [1, 4, 10, 25, 120])
        with mock.patch.object(pt, 'PATIENCE_FACTOR', 1.2):
            self.assertEqual([pt.longer(n) for n in (1, 4, 10, 25, 120)], [2, 5, 12, 30, 144])

    def test_engine_waiting_drain_lasts_longer(self):
        tick = lambda c: life.update_patience(c, 'shop_pick', {}, {})
        old, new = _turns_until_empty(1.0, tick), _turns_until_empty(1.2, tick)
        self.assertEqual(old, 75)                   # 1 patience per action, 100 -> 25
        self.assertTrue(85 <= new <= 95, new)       # about +20%

    def test_food_counter_waiting_drain_lasts_longer(self):
        # A guest in a hurry: 3 per action (the flat 1 plus 2; the food counters run their own queue, kit.wait_tick).
        tick = lambda c: FS.patience_tick(c, 'mother_baby', c['active_task'])
        old, new = _turns_until_empty(1.0, tick), _turns_until_empty(1.2, tick)
        self.assertEqual(old, 25)
        self.assertTrue(28 <= new <= 32, new)

    def test_the_same_turn_always_gives_the_same_answer(self):
        c, t = _room()
        c['turn'] = 17
        self.assertEqual({pt.waits(c, t) for _ in range(5)}, {pt.waits(c, t)})
        with mock.patch.object(pt, 'PATIENCE_FACTOR', 1.0):
            self.assertTrue(all(pt.drain(dict(turn=n), t, 3) == 3 for n in range(200)))


if __name__ == '__main__':
    unittest.main()
