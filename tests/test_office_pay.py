import unittest

from game.careers import office


class OfficePayTests(unittest.TestCase):
    """Dossier pay of the three office careers (owner 02/10: a little more for everyone, gentler on probation)."""

    def test_everyone_gets_a_little_more_and_a_higher_floor(self):
        self.assertEqual(office.pay(30, 0, False), 32)
        self.assertEqual(office.pay(24, 2, False), 26 - 8)
        self.assertEqual(office.pay(24, 9, False), office.MIN_PAY)
        self.assertEqual(office.pay(10, 0, False), office.MIN_PAY)       # the smallest form still pays the floor

    def test_probation_halves_the_cut_and_keeps_half_the_bonus(self):
        self.assertEqual(office.pay(24, 2, True), 26 - 4)
        self.assertEqual(office.pay(30, 20, True), 16)                   # never under half of 32
        self.assertEqual(office.pay(30, 3, True, slip=5), 32 - 6)
        for bonus in (10, 15, 20, 24, 25, 30):
            for m in range(12):
                self.assertGreaterEqual(office.pay(bonus, m, True), office.pay(bonus, m, False))

    def test_rookie_is_rank_zero_of_the_track(self):
        self.assertTrue(office.rookie(dict(care=dict(rank=0))))
        self.assertFalse(office.rookie(dict(care=dict(rank=1))))
        self.assertFalse(office.rookie({}))                              # no track yet: normal rules
        self.assertEqual(office.wrong_min(dict(care=dict(rank=0))), office.ROOKIE_WRONG)
        self.assertEqual(office.wrong_min(dict(care=dict(rank=2))), office.COST['wrong'])

    def test_late_cut_is_halved_on_probation(self):
        for new, cut in ((False, office.LATE_CUT), (True, office.ROOKIE_LATE_CUT)):
            o = office.initial()
            o.update(day=3, clock=office.OPEN + 100)
            late, adj, note = office.settle(o, dict(due=office.OPEN, due_day=3), 3, new)
            self.assertTrue(late)
            self.assertEqual(adj, -cut)
            self.assertIn(f'−{cut} xu', note)
            self.assertEqual(o['trust'], office.TRUST_START - 3)


if __name__ == '__main__':
    unittest.main()
