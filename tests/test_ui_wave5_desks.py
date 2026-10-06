"""UI wave 5 (docs/UI_KIT.md "Disabled with a reason"): the classic pharmacy and bookkeeping desks' pre-checks.

Top refusals 04–06/10 (scratchpad uiaudit refusal_top): pharmacy ph_check "Số lượng trong khay chưa khớp phiếu." /
"Cần xác nhận đủ mã…" and accounting ac_match "Tổng phiếu … chưa khớp …" / "Ghép theo từng quan hệ nhiều-một…".
The guards live once in game/desk_can.py: the commands refuse with them, the public task view runs them through
kit.check as `can`:
- pharmacy: can.ph_check (the tray against the slip; the page adds the three ticks after it, as the command does);
- accounting: can.ac_match = {doc: {why, fix}} for each free card that could not go into a group yet, and
  can.ac_complete. The page adds the rules about the picked set (one-many, the sums, the codes) in the same order.
`can` is a view field: never saved."""
import unittest

from game.engine import GameError, public_state
from game import desk_can
from game.careers import kit
from tests.helpers import Journey


def view_task(j):
    v = public_state(j.state)['careers'][j.career]
    return next(t for t in v['tasks'] if t['id'] == v['active_task'])


class PharmacyCan(unittest.TestCase):
    def refused(self, j, action, **payload):
        with self.assertRaises(GameError) as err:
            j.act(action, **payload)
        return err.exception.message

    def test_unknown_slip_points_at_asking(self):
        j = Journey('pharmacy')
        can = view_task(j)['can']['ph_check']
        self.assertEqual(can['why'], self.refused(j, 'ph_check', checks=['code', 'quantity', 'lot']))
        self.assertEqual(can['fix']['cmd'], 'ask')

    def test_empty_tray_says_the_count_like_the_refusal(self):
        j = Journey('pharmacy'); j.act('ask')
        can = view_task(j)['can']['ph_check']
        self.assertEqual(can['why'], 'Số lượng trong khay chưa khớp phiếu.')
        self.assertEqual(can['why'], self.refused(j, 'ph_check', checks=['code', 'quantity', 'lot']))
        self.assertEqual(can['fix']['sel'], '.dw-lots')

    def test_unread_label_offers_to_read_it(self):
        j = Journey('pharmacy'); j.act('ask')
        n = j.task['needs']
        lot = n['product'] + '-A'
        j.act('ph_inspect', lot=lot)
        for _ in range(n['qty']):
            j.act('ph_pick', item=lot)
        self.assertIs(view_task(j)['can']['ph_check'], True)
        j.task['inspected'].remove(lot)          # a label not read (an older save): the same words as the refusal
        can = view_task(j)['can']['ph_check']
        self.assertEqual(can['why'], self.refused(j, 'ph_check', checks=['code', 'quantity', 'lot']))
        self.assertEqual(can['fix'], dict(cmd='ph_inspect', payload=dict(task=j.task['id'], lot=lot), label='👁️ Đọc nhãn ' + lot))

    def test_ready_tray_goes_and_can_is_never_saved(self):
        j = Journey('pharmacy'); j.act('ask')
        n = j.task['needs']; lot = n['product'] + '-A'
        j.act('ph_inspect', lot=lot)
        for _ in range(n['qty']):
            j.act('ph_pick', item=lot)
        self.assertIs(view_task(j)['can']['ph_check'], True)
        j.act('ph_check', checks=['code', 'quantity', 'lot'])
        self.assertTrue(j.task['checked'])
        self.assertNotIn('can', j.task)
        self.assertFalse(any('can' in t for t in j.c['tasks']))

    def test_done_slip_has_no_can(self):
        j = Journey('pharmacy'); t = j.solve()
        self.assertIsNone(desk_can.ph_view(t, j.c))


class AccountingCan(unittest.TestCase):
    def refused(self, j, **payload):
        with self.assertRaises(GameError) as err:
            j.act('ac_match', **payload)
        return err.exception.message

    def test_every_unread_card_says_why_with_a_fix(self):
        j = Journey('accounting')
        can = view_task(j)['can']
        self.assertEqual(set(can['ac_match']), {d['id'] for d in j.task['docs']})
        first = can['ac_match']['CT-01']
        self.assertEqual(first['why'], self.refused(j, docs=['CT-01'], transactions=['GD-02']))
        self.assertEqual(first['fix']['cmd'], 'ac_inspect')
        self.assertEqual(can['ac_complete']['why'], 'Còn chứng từ chưa đối chiếu, thiếu nguồn hoặc chưa loại bản trùng.')

    def test_a_read_copy_says_remove_it(self):
        j = Journey('accounting')                         # day 1, slot 0: the duplicate file (CT-04 copies CT-03)
        for d in ('CT-01', 'CT-02', 'CT-03', 'CT-04'):
            j.act('ac_inspect', doc=d)
        can = view_task(j)['can']['ac_match']
        self.assertEqual(set(can), {'CT-04'})
        self.assertEqual(can['CT-04']['why'], self.refused(j, docs=['CT-04'], transactions=['GD-02']))
        self.assertEqual(can['CT-04']['fix']['cmd'], 'ac_duplicate')

    def test_the_sums_and_the_one_many_rule_keep_their_words(self):
        j = Journey('accounting')
        for d in ('CT-01', 'CT-02', 'CT-03'):
            j.act('ac_inspect', doc=d)
        t = j.task
        self.assertEqual(kit.check(desk_can.ac_match_rules, t, ['CT-01'], ['GD-01'])['why'], self.refused(j, docs=['CT-01'], transactions=['GD-01']))
        self.assertIn('chưa khớp giao dịch', self.refused(j, docs=['CT-01'], transactions=['GD-01']))
        many = self.refused(j, docs=['CT-01', 'CT-02'], transactions=['GD-01', 'GD-02'])
        self.assertEqual(many, 'Ghép theo từng quan hệ nhiều-một hoặc một-nhiều, không gộp cả hồ sơ.')
        self.assertIs(kit.check(desk_can.ac_match_rules, t, ['CT-01', 'CT-02'], ['GD-01']), True)

    def test_solved_file_has_no_can_and_nothing_is_saved(self):
        j = Journey('accounting'); t = j.solve()
        self.assertEqual(t['status'], 'completed')
        self.assertIsNone(desk_can.ac_view(t))
        self.assertFalse(any('can' in x for x in j.c['tasks']))

    def test_typo_card_points_at_the_original(self):
        j = Journey('accounting', slot=1)                 # "Một chữ số đi lạc": CT-02 is off its original
        j.act('ac_inspect', doc='CT-02')
        can = view_task(j)['can']['ac_match']['CT-02']
        self.assertEqual(can['why'], 'Số nhập còn khác nguồn. Điều chỉnh có căn cứ trước.')
        self.assertEqual(can['fix']['cmd'], 'ac_correct')


if __name__ == '__main__':
    unittest.main()
