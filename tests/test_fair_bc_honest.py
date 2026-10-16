"""06/10 owner: bầu cua had too many crabs and players farmed it (the win was decided first, then dice matching the
bets were picked, with a sure win after four losses). The dice are now honest: uniform, whatever was bet."""
import random
import unittest
from collections import Counter
from unittest import mock

from game import fair as fh


class HonestDice(unittest.TestCase):
    def test_faces_are_uniform_whatever_the_bet(self):
        with mock.patch.object(fh, '_rng', random.Random(7)):
            seen = Counter(face for _ in range(60000) for face in fh.bc_fair_roll())
        for face in fh.FACES:
            self.assertAlmostEqual(seen[face] / 180000, 1 / 6, delta=.006, msg=face)

    def test_a_crab_bet_breaks_even_in_the_long_run(self):
        """Owner 16/10: a bão pays BAO (20), so one face returns exactly its stake on average; at BAO_LOW (fast play or a
        day ≥ 100k up) it loses slightly."""
        with mock.patch.object(fh, '_rng', random.Random(11)):
            net = sum(fh.bc_back({'cua': 10}, fh.bc_fair_roll()) - 10 for _ in range(200000))
            low = sum(fh.bc_back({'cua': 10}, fh.bc_fair_roll(), fh.BAO_LOW) - 10 for _ in range(200000))
        self.assertAlmostEqual(net / (200000 * 10), 0, delta=.01)
        per_xu = low / (200000 * 10)
        self.assertLess(per_xu, 0)
        self.assertAlmostEqual(per_xu, -10 / 216, delta=.01)

    def test_exact_expectation(self):
        ev = sum(fh.bc_back({'cua': 1}, list(d)) - 1 for d in fh.BC_OUTCOMES)
        self.assertEqual(ev, 0)     # 0 xu over the 216 equally likely outcomes of a 1-xu bet (bão 20:1)
        ev = sum(fh.bc_back({'cua': 1}, list(d), fh.BAO_LOW) - 1 for d in fh.BC_OUTCOMES)
        self.assertEqual(ev, -10)   # −10 xu with the bão at 10:1

if __name__ == '__main__':
    unittest.main()
