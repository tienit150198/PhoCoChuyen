"""Ông Hai searches legal moves without deliberate mistakes or unbounded work."""
import random
import unittest
from unittest.mock import patch
from game import fair_oaq as oaq


class StrongHai(unittest.TestCase):
    def test_does_not_deliberately_miss_the_tactical_move(self):
        board = dict(b=[6, 1, 12, 0, 0, 1, 6, 3, 11, 2, 0, 0],
                     q=[1, 1], cap=[6, 0, 2, 0], ply=6)
        before = oaq.copy(board)
        for seed in range(24):
            self.assertEqual(oaq.ai_move(board, 'kho', random.Random(seed), side=0), (5, -1))
        self.assertEqual(board, before)

    def test_opening_search_is_bounded_and_keeps_board_unchanged(self):
        board = oaq.new_game()
        before = oaq.copy(board)
        with patch.object(oaq, 'play', wraps=oaq.play) as play:
            move = oaq.ai_move(board, 'kho', random.Random(1))
        self.assertIn(move, oaq.legal(board, 1))
        self.assertLessEqual(play.call_count, oaq.KHO_NODES)
        self.assertEqual(board, before)

    def test_pruned_search_matches_exhaustive_search(self):
        board = oaq.new_game()
        for side in (0, 1):
            expected = oaq._search(board, side, side, 3)
            actual = oaq._deep_search(board, side, side, 3, -float('inf'), float('inf'), [10000])
            self.assertAlmostEqual(actual, expected)
