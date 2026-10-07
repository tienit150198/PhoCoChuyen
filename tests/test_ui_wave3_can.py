"""UI wave 3 (docs/UI_KIT.md "Disabled with a reason"): the office desks' pre-checks the page dims buttons with.

- office.public(...)['can']['work']: the same rule as office.need_open (refusal "office_closed", a top refusal of
  hr_admin and secretary 04–06/10), with a fix that points at the overtime button while overtime is still possible;
- tax_payroll: a payroll row's can.tp_flag, the same rule as the tp_flag refusal "Mỗi dòng đánh dấu tối đa 3 ô".
Both are view fields: computed, never saved."""
import unittest

from game.careers import kit, office, tax_payroll


class OfficeCanWork(unittest.TestCase):
    def view(self, clock, ot=False):
        o = office.initial()
        o.update(day=3, clock=clock, ot=ot)
        return office.public(o, 3)

    def test_open_office_can_work(self):
        self.assertIs(self.view(office.OPEN + 60)['can']['work'], True)

    def test_after_hours_says_why_and_points_at_overtime(self):
        can = self.view(office.CLOSE)['can']['work']
        self.assertIn('17:30', can['why'])
        self.assertEqual(can['fix'], dict(sel='.ok-alert', label='🌙 Tăng ca'))

    def test_overtime_until_eight_then_locked_without_a_fix(self):
        self.assertIs(self.view(office.CLOSE + 30, ot=True)['can']['work'], True)
        can = self.view(office.LOCK, ot=True)['can']['work']
        self.assertIn('20:00', can['why'])
        self.assertIsNone(can['fix'])

    def test_same_rule_as_the_refusal(self):
        o = office.initial()
        o.update(day=3, clock=office.CLOSE)
        with self.assertRaises(Exception) as err:
            office.need_open(o)
        self.assertIn(office.public(o, 3)['can']['work']['why'], str(err.exception.args))

    def test_a_new_day_is_open(self):
        o = office.initial()
        o.update(day=2, clock=office.LOCK)          # yesterday ended locked; the view of day 3 starts at 08:00
        self.assertIs(office.public(o, 3)['can']['work'], True)


class TaxFlagCan(unittest.TestCase):
    def test_full_row_says_why(self):
        self.assertIs(kit.check(tax_payroll._flag_more_rules, ['a', 'b']), True)
        can = kit.check(tax_payroll._flag_more_rules, ['a', 'b', 'c'])
        self.assertEqual(can['why'], f'Mỗi dòng đánh dấu tối đa {tax_payroll.MAX_FLAGS} ô.')

    def test_the_command_refuses_with_the_same_words(self):
        with self.assertRaises(Exception) as err:
            tax_payroll._flag_more_rules(['a', 'b', 'c'])
        self.assertIn(f'tối đa {tax_payroll.MAX_FLAGS} ô', str(err.exception.args))


if __name__ == '__main__':
    unittest.main()
