"""Order steps: equally right real-life orders are accepted, and a wrong order says where it goes wrong."""
import unittest

from game import procedures as P


def festival():
    ids = ['gather', 'parade', 'feast', 'show', 'clean']
    return P.step('flow', 'order', 'Chương trình', 'Sắp xếp chương trình đêm hội.', ids,
                  items=[dict(id=x, label=x) for x in ids], hints=['Bắt đầu bằng điểm danh, kết thúc bằng dọn dẹp.'])


class OrderSteps(unittest.TestCase):
    def test_feast_before_parade_is_also_right(self):
        st = festival()
        self.assertTrue(P.check(st, ['gather', 'parade', 'feast', 'show', 'clean']))
        self.assertTrue(P.check(st, ['gather', 'feast', 'parade', 'show', 'clean']))
        self.assertFalse(P.check(st, ['feast', 'gather', 'parade', 'show', 'clean']))

    def test_wrong_order_points_at_the_first_wrong_slot(self):
        t = dict(proc=[festival()], proc_state=P.initial_state(), mistakes=0)
        ok, msg = P.submit(t, 'flow', ['gather', 'show', 'feast', 'parade', 'clean'])
        self.assertFalse(ok)
        self.assertIn('3/5', msg)
        self.assertIn('ô số 2', msg)

    def test_a_saved_alternative_answer_still_validates(self):
        st = festival()
        t = dict(proc=[st], proc_state=P.initial_state(), mistakes=0)
        ok, _ = P.submit(t, 'flow', ['gather', 'feast', 'parade', 'show', 'clean'])
        self.assertTrue(ok)
        P.validate(t, dict(proc=[st]))


if __name__ == '__main__':
    unittest.main()
