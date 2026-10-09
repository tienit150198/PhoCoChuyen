"""Ông Hai (06/10, 09/10): a strong, bounded, legal search that no line learnt by heart beats; Bé Bi unchanged; the
10,000 xu prize. On 09/10 one player won 502 of 532 games by replaying two lines (LINES): the 1.9.36 Ông Hai
(tests/oaq_hai_1936.py) answered the same board the same way every time."""
import random
import time
import unittest
from unittest.mock import patch

from game import fair as fh
from game import fair_oaq as oaq
from tests import oaq_hai_1936 as old_hai

# The two lines replayed on 09/10 (Ông Hai's moves H, the player's P; cell and way), each won hundreds of times.
LINES = [[(1 if t[0] == 'H' else 0, int(t[1:-1]), 1 if t[-1] == '+' else -1) for t in line.split()] for line in (
    'H9- P4- H10- P4- H9- P3+ H11+ P3- H8+ P5+ H11+ P3+ H8- P5- H10- P4+ H7+ P2- H8+ P5+ H7- P2- H10+ P5- H11+ P4- '
    'H11+ P3+ H7- P5+ H9- P1- H7- P3+ H9- P2+ H8- P1- H7+',
    'H9+ P2+ H8+ P2+ H9+ P3- H7- P3+ H10- P1- H7- P3- H10+ P1+ H8+ P2- H11- P4+ H10- P1- H11+ P4+ H8- P1+ H7- P2+ '
    'H7- P3- H11+ P1- H9+ P5+ H11+ P3- H9+ P4- H10+ P5+ H11-')]


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


def positions(seed, n, plies=40):
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        g, side = oaq.new_game(), 0
        for _ in range(rng.randrange(0, plies)):
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


def greedy(g, side=0):
    """The biggest capture now, the first such move (no randomness: the same board, the same move)."""
    return max(oaq.legal(g, side), key=lambda m: oaq.play(oaq.copy(g), side, *m))


def lookahead(depth):
    def pick(g, rng, side=0):
        vals = []
        for c, d in oaq.legal(g, side):
            k = oaq.copy(g)
            oaq.play(k, side, c, d)
            vals.append((oaq._search(k, 1 - side, side, depth - 1), rng.random(), (c, d)))
        return max(vals)[2]
    return pick


def match(player, n, seed):
    """n games at the fair (Ông Hai opens, side 1): (Ông Hai's wins, draws, the player's wins, the games' lines)."""
    rng = random.Random(seed)
    out = [0, 0, 0]
    lines = []
    for _ in range(n):
        g, side, line = oaq.new_game(), 1, []
        while oaq.begin_turn(g, side):
            move = oaq.ai_move(g, 'kho', rng) if side == 1 else player(g, rng)
            line.append(move)
            oaq.play(g, side, *move)
            side = 1 - side
        a, b = oaq.score(g, 1), oaq.score(g, 0)
        out[0 if a > b else 2 if a < b else 1] += 1
        lines.append(tuple(line))
    return (*out, lines)


class Engine(unittest.TestCase):
    def setUp(self):
        p = patch.object(oaq, 'KHO_MS', 10 ** 6)   # the moves' budget only: the same on any machine
        p.start()
        self.addCleanup(p.stop)

    def test_fast_sowing_is_the_rules(self):
        rng = random.Random(1)
        checked = 0
        for g, side in positions(2, 400, plies=80):
            for move in oaq.legal(g, side):
                k = oaq.copy(g)
                got = oaq.play(k, side, *move)
                out = oaq._sow(oaq._flat(g), side, *move) or oaq._slow(oaq._flat(g), side, *move, g['ply'])
                self.assertEqual(out, (oaq._flat(k), got))
                checked += 1
        for _ in range(3000):   # any spread of the 50 dân (big hands that go round, a quan ô without its quan)
            b = [0] * 12
            for _ in range(rng.randrange(51)):
                b[rng.randrange(12)] += 1
            left = 50 - sum(b)
            q = [rng.randrange(2), rng.randrange(2)]
            cap = [left, 2 - sum(q), 0, 0] if rng.random() < .5 else [0, 0, left, 2 - sum(q)]
            g, side = dict(b=b, q=q, cap=cap, ply=rng.randrange(oaq.MAX_PLY)), rng.randrange(2)
            self.assertTrue(oaq.valid(g))
            h = oaq.copy(g)
            alive = oaq.begin_turn(h, side)
            t = oaq._turn(oaq._flat(g), side, g['ply'])
            if not alive:
                d = oaq.score(h, side) - oaq.score(h, 1 - side)
                self.assertEqual(t, oaq._WIN + d if d > 0 else -oaq._WIN + d if d < 0 else 0)
                continue
            self.assertEqual(t, oaq._flat(h))
            for move in oaq.legal(h, side):
                k = oaq.copy(h)
                got = oaq.play(k, side, *move)
                out = oaq._sow(oaq._flat(h), side, *move) or oaq._slow(oaq._flat(h), side, *move, h['ply'])
                self.assertEqual(out, (oaq._flat(k), got))
                checked += 1
        self.assertGreater(checked, 10000)

    def test_pruned_search_matches_exhaustive_search(self):
        for g, side in positions(5, 12):
            for depth in (1, 2, 3):
                self.assertEqual(oaq._Hai(10 ** 9).search(oaq._flat(g), side, depth, -2 * oaq._WIN, 2 * oaq._WIN, g['ply']),
                                 plain(g, side, depth))
            h = oaq._Hai(10 ** 9)   # iterative deepening: a table filled at shallower depths changes nothing
            for depth in (1, 2, 3):
                v = h.search(oaq._flat(g), side, depth, -2 * oaq._WIN, 2 * oaq._WIN, g['ply'])
            self.assertEqual(v, plain(g, side, 3))

    def test_does_not_deliberately_miss_the_tactical_move(self):
        board = dict(b=[6, 1, 12, 0, 0, 1, 6, 3, 11, 2, 0, 0],
                     q=[1, 1], cap=[6, 0, 2, 0], ply=6)
        before = oaq.copy(board)
        for seed in range(12):
            self.assertEqual(oaq.ai_move(board, 'kho', random.Random(seed), side=0), (5, -1))
        self.assertEqual(board, before)

    def test_opens_from_the_middle_either_way(self):
        board = oaq.new_game()
        seen = {oaq.ai_move(board, 'kho', random.Random(seed)) for seed in range(30)}
        self.assertEqual(seen, set(oaq.OPENING))
        self.assertEqual(seen, {(9, 1), (9, -1)})
        self.assertEqual(board, oaq.new_game())

    def test_bounded_by_moves(self):
        for g, side in positions(3, 6):
            if oaq._opening(g, side):
                continue
            before = oaq.copy(g)
            with patch.object(oaq, '_sow', wraps=oaq._sow) as sow:
                move = oaq.ai_move(g, 'kho', random.Random(9), side)
            self.assertIn(move, oaq.legal(g, side))
            self.assertLessEqual(sow.call_count, oaq.KHO_NODES)
            self.assertEqual(g, before)
        with patch.object(oaq, '_sow', wraps=oaq._sow) as sow:   # mid-opening: the budget is really used
            g = oaq.new_game()
            oaq.play(g, 1, 9, 1)
            oaq.play(g, 0, 2, 1)
            oaq.ai_move(g, 'kho', random.Random(1))
        self.assertGreater(sow.call_count, oaq.KHO_NODES * 3 // 4)
        self.assertLessEqual(sow.call_count, oaq.KHO_NODES)

    def test_bounded_by_time(self):
        g = oaq.new_game()
        oaq.play(g, 1, 9, 1)
        oaq.play(g, 0, 2, 1)
        with patch.object(oaq, 'KHO_NODES', 10 ** 9), patch.object(oaq, 'KHO_MS', 15):
            t = time.perf_counter()
            move = oaq.ai_move(g, 'kho', random.Random(1))
            took = (time.perf_counter() - t) * 1000
        self.assertIn(move, oaq.legal(g, 1))
        self.assertLess(took, 15 + 60)   # the clock is read every 256 simulated moves (well under a millisecond here)

    def test_a_move_is_quick(self):
        """At KHO_NODES a move takes a few ms here (the production server, ~8× slower: ~30 ms, KHO_MS caps it)."""
        times = []
        for g, side in positions(4, 12):
            t = time.perf_counter()
            oaq.ai_move(g, 'kho', random.Random(1), side)
            times.append((time.perf_counter() - t) * 1000)
        self.assertLess(sorted(times)[len(times) // 2], 100)

    def test_same_rng_state_same_move(self):
        for g, side in positions(3, 6):
            a = oaq.ai_move(g, 'kho', random.Random(9), side)
            b = oaq.ai_move(g, 'kho', random.Random(9), side)
            self.assertEqual(a, b)

    def test_no_line_comes_back_for_sure(self):
        """The same board does not always get the same answer, and a player who always plays the same way (no
        randomness at all) meets many different games."""
        varied = 0
        for g, side in positions(6, 20, plies=20):
            if oaq._opening(g, side):
                continue
            varied += len({oaq.ai_move(g, 'kho', random.Random(seed), side) for seed in range(8)}) > 1
        self.assertGreaterEqual(varied, 5)
        hai, draws, won, lines = match(lambda g, rng: old_hai.move(g, 0, rng), 8, 5)   # the 1.9.36 engine: no randomness
        self.assertGreaterEqual(len(set(lines)), 4)
        self.assertEqual(won, 0)

    def test_the_lines_learnt_by_heart_no_longer_win(self):
        """The 09/10 lines: the player plays them while Ông Hai answers as in them, then goes on by itself. Against
        1.9.36's Ông Hai they were replayed to the end and won every time. Now he leaves them by the 12th move (they
        are a real answer to his opening: whoever goes on as strongly as the 1.9.36 engine wins from there, see
        scratchpad); a player who goes on with a plain look-ahead does not win."""
        def replay(hai_move, n, seed, then=lambda g, rng: old_hai.move(g, 0, rng)):
            rng = random.Random(seed)
            won = longest = 0
            for _ in range(n):
                g, side, hist, on = oaq.new_game(), 1, [], True
                while oaq.begin_turn(g, side):
                    if side == 1:
                        move = hai_move(g, rng)
                    else:
                        line = next((x for x in LINES if x[:len(hist)] == hist), None)
                        on = on and line is not None and len(line) > len(hist)
                        move = line[len(hist)][1:] if on else then(g, rng)
                    hist.append((side, *move))
                    oaq.play(g, side, *move)
                    side = 1 - side
                longest = max(longest, max(len([1 for a, b in zip(hist, x) if a == b]) for x in LINES))
                won += oaq.score(g, 0) > oaq.score(g, 1)
            return won, longest
        self.assertEqual(replay(lambda g, rng: old_hai.move(g, 1, rng), 2, 1), (2, 39))
        won, longest = replay(lambda g, rng: oaq.ai_move(g, 'kho', rng), 6, 2, lookahead(3))
        self.assertEqual(won, 0)
        self.assertLessEqual(longest, 12)

    def test_beats_the_old_engine_and_lookahead_players(self):
        """Ông Hai opens, as at the fair; the player is the 1.9.36 Ông Hai (5× his budget a move), plain look-ahead
        minimax, or the biggest capture now. scratchpad runs (100 games each): the player won 5% (jittered 1.9.36
        budget), 0% otherwise (look-ahead 4: half draws)."""
        hai, draws, won, _ = match(lambda g, rng: old_hai.move(g, 0, rng), 6, 1)
        self.assertEqual(won, 0)
        self.assertGreaterEqual(hai, 5)
        for depth in (2, 3):
            hai, draws, won, _ = match(lambda g, rng: lookahead(depth)(g, rng), 6, depth)
            self.assertEqual(won, 0, depth)
        hai, draws, won, _ = match(lambda g, rng: greedy(g), 10, 7)
        self.assertEqual(hai, 10)
        hai, draws, won, _ = match(lambda g, rng: rng.choice(oaq.legal(g, 0)), 10, 8)
        self.assertEqual(hai, 10)

    def test_endgame_is_solved_exactly(self):
        # few dân left: the search reaches the end of the game and the value is exact
        g = dict(b=[0, 1, 0, 0, 2, 0, 0, 0, 1, 0, 0, 1], q=[0, 0], cap=[20, 1, 25, 1], ply=40)
        h = oaq._Hai(oaq.KHO_NODES)
        move = h.best_move(g, 1)
        self.assertIn(move, oaq.legal(g, 1))
        self.assertLess(h.reached, oaq.KHO_MAX_DEPTH)       # stopped early: proven

    def test_searches_several_moves_ahead(self):
        g = oaq.new_game()
        oaq.play(g, 1, 9, -1)
        h = oaq._Hai(oaq.KHO_NODES)
        h.best_move(g, 0)
        self.assertGreaterEqual(h.reached, 5)

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
