"""Ông Hai (06/10): a strong, bounded, legal search; Bé Bi unchanged; the 10,000 xu prize."""
import random
import unittest
from unittest.mock import patch
from game import fair as fh
from game import fair_oaq as oaq


def plain(g, side, depth):
    """Exhaustive negamax with Ông Hai's own evaluation: what the pruned search must return."""
    h = oaq.copy(g)
    if not oaq.begin_turn(h, side):
        d = oaq.score(h, side) - oaq.score(h, 1 - side)
        return oaq._WIN + d if d > 0 else -oaq._WIN + d if d < 0 else 0
    if depth == 0:
        return oaq._eval(h, side)
    best = None
    for move in oaq.legal(h, side):
        k = oaq.copy(h)
        oaq.play(k, side, *move)
        v = -plain(k, 1 - side, depth - 1)
        best = v if best is None or v > best else best
    return best


def positions(seed, n):
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        g, side = oaq.new_game(), 0
        for _ in range(rng.randrange(0, 40)):
            if not oaq.begin_turn(g, side):
                break
            oaq.play(g, side, *rng.choice(oaq.legal(g, side)))
            side = 1 - side
        if oaq.begin_turn(g, side):
            out.append((g, side))
    return out


def old_bebi(g, rng, side=1):
    """Bé Bi as shipped before 06/10."""
    moves = oaq.legal(g, side)
    if rng.random() < 0.45:
        return rng.choice(moves)
    scored = []
    for c, d in moves:
        k = oaq.copy(g)
        scored.append((oaq.play(k, side, c, d), rng.random(), (c, d)))
    return max(scored)[2]


class StrongHai(unittest.TestCase):
    def test_does_not_deliberately_miss_the_tactical_move(self):
        board = dict(b=[6, 1, 12, 0, 0, 1, 6, 3, 11, 2, 0, 0],
                     q=[1, 1], cap=[6, 0, 2, 0], ply=6)
        before = oaq.copy(board)
        for seed in range(12):
            self.assertEqual(oaq.ai_move(board, 'kho', random.Random(seed), side=0), (5, -1))
        self.assertEqual(board, before)

    def test_opening_search_is_bounded_and_keeps_board_unchanged(self):
        board = oaq.new_game()
        before = oaq.copy(board)
        with patch.object(oaq, 'play', wraps=oaq.play) as play:
            move = oaq.ai_move(board, 'kho', random.Random(1))
        self.assertIn(move, oaq.legal(board, 1))
        self.assertLessEqual(play.call_count, oaq.KHO_NODES)
        self.assertGreater(play.call_count, oaq.KHO_NODES // 2)   # the budget is really used
        self.assertEqual(board, before)

    def test_budget_in_moves_not_time_and_deterministic(self):
        for g, side in positions(3, 6):
            before = oaq.copy(g)
            a = oaq.ai_move(g, 'kho', random.Random(9), side)
            with patch.object(oaq, 'play', wraps=oaq.play) as play:
                b = oaq.ai_move(g, 'kho', random.Random(9), side)
            self.assertEqual(a, b)                        # same board, same rng state: same move
            self.assertIn(a, oaq.legal(g, side))
            self.assertLessEqual(play.call_count, oaq.KHO_NODES)
            self.assertEqual(g, before)
            self.assertEqual(oaq._Hai(oaq.KHO_NODES).best_move(g, side), oaq._Hai(oaq.KHO_NODES).best_move(g, side))

    def test_searches_deeper_than_before(self):
        h = oaq._Hai(oaq.KHO_NODES)
        h.best_move(oaq.new_game(), 0)
        self.assertGreaterEqual(h.reached, 6)              # at the opening (the 05/10 one: at most 6, 6,000 moves)

    def test_pruned_search_matches_exhaustive_search(self):
        for g, side in positions(5, 12):
            for depth in (1, 2, 3):
                self.assertEqual(oaq._Hai(10 ** 9).search(g, side, depth, -2 * oaq._WIN, 2 * oaq._WIN, 0),
                                 plain(g, side, depth))

    def test_endgame_is_solved_exactly(self):
        # few dân left: the search reaches the end of the game and the value is exact
        g = dict(b=[0, 1, 0, 0, 2, 0, 0, 0, 1, 0, 0, 1], q=[0, 0], cap=[20, 1, 25, 1], ply=40)
        h = oaq._Hai(oaq.KHO_NODES)
        move = h.best_move(g, 1)
        self.assertIn(move, oaq.legal(g, 1))
        self.assertLess(h.reached, oaq.KHO_MAX_DEPTH)       # stopped early: proven

    def test_whole_games_stay_legal_and_end(self):
        rng = random.Random(4)
        for i in range(4):
            g, side = oaq.new_game(), 0
            while oaq.begin_turn(g, side):
                move = oaq.ai_move(g, 'kho', rng, side) if side == i % 2 else rng.choice(oaq.legal(g, side))
                self.assertIn(move, oaq.legal(g, side))
                oaq.play(g, side, *move)
                self.assertTrue(oaq.valid(g))
                side = 1 - side
            self.assertEqual(oaq.score(g, 0) + oaq.score(g, 1), 50 + 2 * oaq.QUAN)

    def test_beats_greedy_and_random_when_opening(self):
        rng = random.Random(8)
        for opp in ('greedy', 'random'):
            won = 0
            for _ in range(3):
                g, side = oaq.new_game(), 1          # as at the fair: Ông Hai opens
                while oaq.begin_turn(g, side):
                    if side == 1:
                        move = oaq.ai_move(g, 'kho', rng)
                    elif opp == 'random':
                        move = rng.choice(oaq.legal(g, 0))
                    else:
                        move = max(oaq.legal(g, 0), key=lambda m: (oaq.play(oaq.copy(g), 0, *m), rng.random()))
                    oaq.play(g, side, *move)
                    side = 1 - side
                won += oaq.score(g, 1) > oaq.score(g, 0)
            self.assertEqual(won, 3, opp)


class BeBiUnchanged(unittest.TestCase):
    def test_same_moves_as_before(self):
        for i, (g, side) in enumerate(positions(11, 60)):
            self.assertEqual(oaq.ai_move(g, 'de', random.Random(i), side), old_bebi(g, random.Random(i), side))


class Prize(unittest.TestCase):
    def test_prize_and_opening(self):
        self.assertEqual(fh.OAQ_PRIZE, dict(de=50, kho=10000))   # owner 09/10: "thắng ông Hai vẫn là 10k/1 lần"
        self.assertEqual(fh.OAQ_FIRST, ('kho',))
        self.assertEqual(oaq.LEVELS, ('de', 'kho'))


if __name__ == '__main__':
    unittest.main()
