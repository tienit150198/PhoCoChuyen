"""🖼️ Khung danh hiệu (owner 18/10: "người ta nhiều khung thì chủ động đổi khung được k"): jr_frame keeps the frame a
player chose in journey.hf_pick (game/journey.py HF_PICK); live/honours.py puts it first in `tt`. Absent: automatic."""
import copy
import unittest

from game import journey as jr
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_journey import Play


def act(s, **p):
    return apply_action(s, None, 'jr_frame', p)


class FramePick(unittest.TestCase):
    def setUp(self):
        self.s = Play().s

    def test_choose_none_then_back_to_automatic(self):
        self.assertNotIn('hf_pick', public_state(self.s)['journey'])
        s, r = act(self.s, id='lb_wealth_3')
        self.assertEqual(s['journey']['hf_pick'], 'lb_wealth_3')
        self.assertEqual(public_state(s)['journey']['hf_pick'], 'lb_wealth_3')
        self.assertIn('Đã đổi khung', r['message'])
        s, r = act(s, id='off')
        self.assertEqual(s['journey']['hf_pick'], 'off')
        self.assertIn('Đã cất khung', r['message'])
        for v in ('t_ct_cong_vien', 'dh_mat_trang', 'lb_milk_tea_1', 'lb_all_10', 'k_01', 'k_24'):   # k_: an everyday frame
            s, _ = act(s, id=v)
            self.assertEqual(s['journey']['hf_pick'], v)
        s, r = act(s, id='auto')
        self.assertNotIn('hf_pick', s['journey'])
        self.assertNotIn('hf_pick', public_state(s)['journey'])
        self.assertIn('Tự động', r['message'].replace('tự chọn', 'Tự động'))
        s, _ = act(s)   # no id: automatic too
        self.assertNotIn('hf_pick', s['journey'])
        validate_state(s)

    def test_refuses_anything_else(self):
        for bad in ('k_03', 'k_72', 'k_', 'lb_all_11', 'lb_all_0', 'f_bao', 'w_vip', 'hf_off', 'LB_ALL_1', 'lb_all_1 ', 7, ['off'], 'x' * 80):
            with self.assertRaises(GameError, msg=repr(bad)):
                act(self.s, id=bad)
        with self.assertRaises(GameError):
            act(self.s, id='off', extra=1)
        s = copy.deepcopy(self.s)
        s['journey']['hf_pick'] = 'f_bao'   # a save edited by hand
        with self.assertRaises(GameError):
            validate_state(s)

    def test_an_older_build_keeps_the_key(self):
        """2.4.44 (the rollback target) checks set(initial()) <= set(journey): an extra key is kept, never refused."""
        s, _ = act(self.s, id='lb_all_1')
        self.assertLessEqual(set(jr.initial()), set(s['journey']))
        self.assertNotIn('hf_pick', jr.initial())


if __name__ == '__main__':
    unittest.main()
