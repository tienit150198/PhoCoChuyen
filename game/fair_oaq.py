"""🪨 Ô ăn quan at the fair (owner 02/10: "vào đó có mấy trò dân gian như ô ăn quan, lô tô, bầu cua,... cho mọi người
chơi kiếm xu nhé"): the rules, the board and the neighbour who plays against you. Pure functions, no I/O; the
commands, the reward and the save are in game/fair.py.

The board is a ring of 12 ô: 0 is the left quan, 1..5 the player's row (left to right), 6 the right quan, 7..11 the
opponent's row (right to left, as seen from the player). Going +1 is "to the right" along the player's row.

Rules (the common variant; the "Cách chơi" in public/js/v4/fair.js says the same in a few lines):
* Start: 5 dân in each of the 10 small ô, one quan (worth QUAN dân) in each quan ô. Dân are worth 1.
* A turn: pick one of your own non-empty ô and a direction, take all its dân and sow one per ô that way (quan ô
  included). Then look at the next ô:
  - a non-empty small ô: take its dân and keep sowing;
  - a quan ô (with anything in it): the turn ends;
  - an empty ô followed by a non-empty one: capture that one (all its dân, and the quan if it is a quan ô). Then if
    the next ô is empty again and the one after has dân, capture again (ăn liên tiếp), and so on;
  - two empty ô in a row: the turn ends.
* Quan non: a quan ô that still holds its quan but fewer than QUAN_NON dân cannot be captured yet; the turn ends.
* Rải quân: when all five of your ô are empty at the start of your turn, put back one dân from your captures in each;
  with fewer than 5 dân captured you cannot, and the game ends.
* The game ends when both quan ô are empty (hết quan, tàn dân: each side takes the dân left on its own row), or when a
  player cannot rải quân, or after MAX_PLY turns. Most points wins (dân 1, quan QUAN).

The opponent: "de" (Bé Bi) takes the biggest capture now, or (DE_RANDOM) just plays anything.
"kho" (Ông Hai, owner 06/10: "mạnh không ai thắng được"): negamax alpha-beta with principal variation search,
iterative deepening, a transposition table, captures/killer/history move ordering and an evaluation of captures, dân
on each row, mobility and rải quân danger; finished games are scored exactly, so short endgames are solved. The work is
KHO_NODES simulated moves (about eight turns ahead at the start), never wall-clock time. He never picks a worse move on
purpose; only the order of equally good captures is shuffled.
"""
from __future__ import annotations

import random

QUAN = 10            # a quan is worth this many dân
QUAN_NON = 5         # a quan ô with its quan and fewer dân than this cannot be captured
START = 5            # dân per small ô
MAX_PLY = 300        # turns before the game is counted as it stands
MAX_STEPS = 400      # dân sown in one turn at most (a guard; real games are far below)
LEVELS = ('de', 'kho')
QUAN_CELLS = (0, 6)
ROWS = ((1, 2, 3, 4, 5), (7, 8, 9, 10, 11))


def new_game() -> dict:
    """b: dân per ô; q: quan still on the board (left, right); cap: [dân, quan] captured by the player, the opponent."""
    return dict(b=[0, START, START, START, START, START, 0, START, START, START, START, START], q=[1, 1], cap=[0, 0, 0, 0], ply=0)


def copy(g: dict) -> dict:
    return dict(b=g['b'][:], q=g['q'][:], cap=g['cap'][:], ply=g['ply'])


def _qi(cell: int) -> int:
    return 0 if cell == 0 else 1


def empty(g: dict, cell: int) -> bool:
    return g['b'][cell] == 0 and not (cell in QUAN_CELLS and g['q'][_qi(cell)])


def score(g: dict, side: int) -> int:
    return g['cap'][2 * side] + QUAN * g['cap'][2 * side + 1]


def legal(g: dict, side: int) -> list[tuple[int, int]]:
    return [(c, d) for c in ROWS[side] if g['b'][c] for d in (1, -1)]


def over(g: dict) -> bool:
    return empty(g, 0) and empty(g, 6)


def collect(g: dict, trace: list | None = None) -> None:
    """The end: each side takes the dân left on its own row (the quan ô are empty, or the game was cut short)."""
    for side in (0, 1):
        n = sum(g['b'][c] for c in ROWS[side])
        if n:
            for c in ROWS[side]:
                g['b'][c] = 0
            g['cap'][2 * side] += n
            if trace is not None:
                trace.append(['collect', side, n])
    for c in QUAN_CELLS:   # dân left in a quan ô whose quan is gone (cut short): to whoever leads, keep it simple
        if g['b'][c] or g['q'][_qi(c)]:
            lead = 0 if score(g, 0) >= score(g, 1) else 1
            g['cap'][2 * lead] += g['b'][c]
            g['cap'][2 * lead + 1] += g['q'][_qi(c)]
            if trace is not None:
                trace.append(['collect', lead, g['b'][c] + QUAN * g['q'][_qi(c)]])
            g['b'][c] = 0
            g['q'][_qi(c)] = 0


def begin_turn(g: dict, side: int, trace: list | None = None) -> bool:
    """Before `side` moves: the end of the game, or rải quân. Returns False when the game is over."""
    if over(g) or g['ply'] >= MAX_PLY:
        collect(g, trace)
        return False
    if any(g['b'][c] for c in ROWS[side]):
        return True
    if g['cap'][2 * side] < len(ROWS[side]):   # nothing to rải: the game ends
        collect(g, trace)
        return False
    for c in ROWS[side]:
        g['b'][c] = 1
    g['cap'][2 * side] -= len(ROWS[side])
    if trace is not None:
        trace.append(['seed', side])
    return True


def play(g: dict, side: int, cell: int, d: int, trace: list | None = None) -> int:
    """`side` sows ô `cell` towards `d` (+1/-1) in place; returns what it captured (in dân)."""
    b, q = g['b'], g['q']
    hand, b[cell], pos = b[cell], 0, cell
    if trace is not None:
        trace.append(['pick', cell, hand])
    got, steps = 0, 0
    while True:
        while hand and steps < MAX_STEPS:
            pos = (pos + d) % 12
            b[pos] += 1
            hand -= 1
            steps += 1
            if trace is not None:
                trace.append(['drop', pos])
        if hand or steps >= MAX_STEPS:   # the guard: whatever is left goes back where it was taken
            b[pos] += hand
            break
        nxt = (pos + d) % 12
        if not empty(g, nxt):
            if nxt in QUAN_CELLS:
                break
            hand, b[nxt], pos = b[nxt], 0, nxt
            if trace is not None:
                trace.append(['pick', nxt, hand])
            continue
        # an empty ô: capture what follows, as long as empty / full pairs go on
        while True:
            tgt = (nxt + d) % 12
            if empty(g, tgt):
                break
            if tgt in QUAN_CELLS and q[_qi(tgt)] and b[tgt] < QUAN_NON:
                if trace is not None:
                    trace.append(['non', tgt])
                break
            dan, quan = b[tgt], (q[_qi(tgt)] if tgt in QUAN_CELLS else 0)
            b[tgt] = 0
            if quan:
                q[_qi(tgt)] = 0
            g['cap'][2 * side] += dan
            g['cap'][2 * side + 1] += quan
            got += dan + QUAN * quan
            if trace is not None:
                trace.append(['cap', tgt, dan, quan])
            nxt = (tgt + d) % 12
            if not empty(g, nxt):
                break
        break
    g['ply'] += 1
    return got


# ---------------------------------------------------------------- the opponent
def _value(g: dict, side: int) -> float:
    """The opponent's view of a position: captures, plus a little for dân on its own row (they come home at the end)."""
    own = sum(g['b'][c] for c in ROWS[side])
    other = sum(g['b'][c] for c in ROWS[1 - side])
    return score(g, side) - score(g, 1 - side) + 0.3 * (own - other)


def _search(g: dict, side: int, me: int, depth: int) -> float:
    h = copy(g)
    if not begin_turn(h, side):
        return (score(h, me) - score(h, 1 - me)) * 10
    if depth == 0:
        return _value(h, me)
    best = None
    for c, d in legal(h, side):
        k = copy(h)
        play(k, side, c, d)
        v = _search(k, 1 - side, me, depth - 1)
        if best is None or (v > best if side == me else v < best):
            best = v
    return best if best is not None else _value(h, me)


DE_RANDOM = 0.45     # Bé Bi: a random move this often, else the biggest capture now
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


def ai_move(g: dict, level: str, rng: random.Random, side: int = 1) -> tuple[int, int]:
    """Choose a legal move after begin_turn; the board and the player's score stay untouched."""
    moves = legal(g, side)
    if level == 'de':
        if rng.random() < DE_RANDOM:
            return rng.choice(moves)
        scored = []
        for c, d in moves:
            k = copy(g)
            scored.append((play(k, side, c, d), rng.random(), (c, d)))
        return max(scored)[2]
    return _strong_move(g, side, rng)


# ---------------------------------------------------------------- checks
def valid(g: object) -> bool:
    """Shape and conservation: 50 dân and 2 quan in all, wherever they are."""
    if not isinstance(g, dict) or set(g) != {'b', 'q', 'cap', 'ply'}:
        return False
    b, q, cap, ply = g['b'], g['q'], g['cap'], g['ply']
    if not (isinstance(b, list) and len(b) == 12 and all(type(x) is int and 0 <= x <= 70 for x in b)):
        return False
    if not (isinstance(q, list) and len(q) == 2 and all(x in (0, 1) and type(x) is int for x in q)):
        return False
    if not (isinstance(cap, list) and len(cap) == 4 and all(type(x) is int and 0 <= x <= 70 for x in cap)):
        return False
    if type(ply) is not int or not 0 <= ply <= MAX_PLY:
        return False
    return sum(b) + cap[0] + cap[2] == 10 * START and sum(q) + cap[1] + cap[3] == 2
