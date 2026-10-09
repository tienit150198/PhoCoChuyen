"""Ông Hai as shipped in 1.9.36 (game/fair_oaq.py until 09/10), frozen for tests/test_fair_oaq_strong.py: a fixed
budget of KHO_NODES simulated moves, the same answer to the same board. The rules come from game/fair_oaq.py."""
from __future__ import annotations

import random

from game.fair_oaq import MAX_PLY, ROWS, begin_turn, copy, legal, over, play, score

KHO_NODES = 20000    # Ông Hai: simulated moves per request at most (owner 06/10: "không ai thắng được")
KHO_MAX_DEPTH = 40   # iterative deepening stops here (or once the result is proven)
_WIN = 1_000_000     # a finished game, plus the margin; any heuristic value stays far below


class _SearchLimit(Exception):
    pass


def _key(g: dict, side: int) -> tuple:
    """The position for the transposition table (ply only matters close to MAX_PLY)."""
    late = g['ply'] - (MAX_PLY - 2 * KHO_MAX_DEPTH)
    return (*g['b'], *g['q'], *g['cap'], side, late if late > 0 else 0)


def _eval(g: dict, side: int) -> int:
    """Ông Hai's view of an unfinished position for the side to move, in tenths of a dân: the captures, the dân on
    each row (they come home at the end), mobility, and a quan ô ripe for capture (or not)."""
    b = g['b']
    own = other = mob = 0
    for c in ROWS[side]:
        own += b[c]
        mob += b[c] > 0
    for c in ROWS[1 - side]:
        other += b[c]
        mob -= b[c] > 0
    v = 10 * (score(g, side) - score(g, 1 - side)) + 3 * (own - other) + 2 * mob
    if own == 0 and g['cap'][2 * side] < len(ROWS[side]):
        v -= 30        # cannot rải quân next turn
    return v


class _Hai:
    """Negamax alpha-beta (principal variation search) with iterative deepening, a transposition table, captures
    first, killer and history moves. The work is counted in simulated moves, never in time: the same board always
    gets the same move, whatever the server's load."""

    def __init__(self, nodes: int):
        self.left = nodes
        self.tt: dict = {}
        self.killers: dict = {}
        self.history: dict = {}
        self.reached = 0   # the last depth searched in full (for the checks)

    def children(self, g: dict, side: int, skip=()) -> list:
        out = []
        for move in legal(g, side):
            if move in skip:
                continue
            if self.left <= 0:
                raise _SearchLimit
            self.left -= 1
            child = copy(g)
            out.append((play(child, side, *move), move, child))
        return out

    def order(self, kids: list, side: int, first, ply: int) -> list:
        killers = self.killers.get(ply, ())
        hist = self.history

        def rank(item):
            gain, move, _ = item
            return (move == first, gain, move in killers, hist.get((side, move), 0))
        return sorted(kids, key=rank, reverse=True)

    def moves(self, g: dict, side: int, first, ply: int):
        """The moves one by one, best guesses first: the table's move and the killers are played (and counted) only
        when reached, so a cut-off on them saves the rest; then the captures, biggest first."""
        b, tried = g['b'], []
        for move in (first, *self.killers.get(ply, ())):
            if move is None or move in tried or move[0] not in ROWS[side] or not b[move[0]]:
                continue
            if self.left <= 0:
                raise _SearchLimit
            self.left -= 1
            child = copy(g)
            play(child, side, *move)
            tried.append(move)
            yield move, child
        rest = self.children(g, side, tried)
        for _, move, child in self.order(rest, side, None, ply):
            yield move, child

    def search(self, g: dict, side: int, depth: int, alpha: int, beta: int, ply: int) -> int:
        b = g['b']
        if over(g) or g['ply'] >= MAX_PLY or not any(b[c] for c in ROWS[side]):
            g = copy(g)
            if not begin_turn(g, side):
                d = score(g, side) - score(g, 1 - side)
                return _WIN + d if d > 0 else -_WIN + d if d < 0 else 0
        if depth <= 0:
            return _eval(g, side)
        key = _key(g, side)
        hit = self.tt.get(key)
        first = None
        if hit is not None:
            h_depth, h_value, h_flag, first = hit
            if h_depth >= depth:
                if h_flag == 0:
                    return h_value
                if h_flag > 0:
                    alpha = max(alpha, h_value)
                else:
                    beta = min(beta, h_value)
                if alpha >= beta:
                    return h_value
        alpha0 = alpha
        best, best_move = -2 * _WIN, None
        for i, (move, child) in enumerate(self.moves(g, side, first, ply)):
            if i == 0:
                v = -self.search(child, 1 - side, depth - 1, -beta, -alpha, ply + 1)
            else:
                v = -self.search(child, 1 - side, depth - 1, -alpha - 1, -alpha, ply + 1)
                if alpha < v < beta:
                    v = -self.search(child, 1 - side, depth - 1, -beta, -alpha, ply + 1)
            if v > best:
                best, best_move = v, move
            if v > alpha:
                alpha = v
            if alpha >= beta:
                ks = self.killers.setdefault(ply, [])
                if move not in ks:
                    ks.insert(0, move)
                    del ks[2:]
                self.history[(side, move)] = self.history.get((side, move), 0) + depth * depth
                break
        flag = 1 if best >= beta else -1 if best <= alpha0 else 0
        self.tt[key] = (depth, best, flag, best_move)
        return best

    def best_move(self, g: dict, side: int, rng: random.Random | None = None) -> tuple[int, int]:
        kids = self.children(g, side)
        # The captures first; among equal ones the order is shuffled (from rng), so that of two moves worth exactly
        # the same Ông Hai does not always play the same one: a line learnt by heart does not win twice for sure.
        # The work and the value of the chosen move do not depend on it.
        tie = [rng.random() if rng else 0 for _ in kids]
        kids = [k for _, k in sorted(zip(tie, kids), key=lambda x: (x[1][0], x[0]), reverse=True)]
        chosen = kids[0][1]
        for depth in range(1, KHO_MAX_DEPTH + 1):
            alpha, scored, done = -2 * _WIN, [], True
            try:
                for i, (gain, move, child) in enumerate(kids):
                    if i == 0:
                        v = -self.search(child, 1 - side, depth - 1, -2 * _WIN, -alpha, 1)
                    else:
                        v = -self.search(child, 1 - side, depth - 1, -alpha - 1, -alpha, 1)
                        if v > alpha:
                            v = -self.search(child, 1 - side, depth - 1, -2 * _WIN, -alpha, 1)
                    scored.append((v, -i, gain, move, child))
                    alpha = max(alpha, v)
            except _SearchLimit:
                done = False
            if scored:
                # The first move (the last depth's best) was fully searched: any move proven better at this depth
                # is better, so even an unfinished depth can only improve the choice.
                top = max(scored)
                chosen = top[3]
            if not done:
                break
            self.reached = depth
            scored.sort(reverse=True)
            kids = [(gain, move, child) for _, _, gain, move, child in scored]
            if abs(scored[0][0]) >= _WIN // 2 and depth > 1:
                break   # the result is proven (a sure win, or a sure loss whatever Ông Hai does)
        return chosen


def _strong_move(g: dict, side: int, rng: random.Random | None = None) -> tuple[int, int]:
    """Ông Hai's move: at most KHO_NODES simulated moves; the same board and rng state give the same move."""
    try:
        return _Hai(KHO_NODES).best_move(g, side, rng)
    except _SearchLimit:   # the budget cannot run out on the first ply (≤ 10 moves); a guard all the same
        return legal(g, side)[0]


def move(g: dict, side: int = 1, rng: random.Random | None = None) -> tuple[int, int]:
    return _strong_move(g, side, rng)
