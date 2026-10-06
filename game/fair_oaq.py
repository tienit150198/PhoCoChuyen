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
"kho" (Ông Hai) searches up to six turns ahead with alpha-beta pruning and a fixed
work budget. It only uses completed searches and never deliberately picks a worse move.
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
KHO_DEPTH = 6
KHO_NODES = 6000     # maximum simulated moves per request, including move ordering


class _SearchLimit(Exception):
    pass


def _children(g: dict, side: int, me: int, budget: list[int]) -> list:
    children = []
    for move in legal(g, side):
        if budget[0] <= 0:
            raise _SearchLimit
        budget[0] -= 1
        child = copy(g)
        play(child, side, *move)
        children.append((_value(child, me), move, child))
    return sorted(children, key=lambda item: item[0], reverse=side == me)


def _deep_search(g: dict, side: int, me: int, depth: int,
                 alpha: float, beta: float, budget: list[int]) -> float:
    h = copy(g)
    if not begin_turn(h, side):
        return (score(h, me) - score(h, 1 - me)) * 10
    if depth == 0:
        return _value(h, me)
    maximizing = side == me
    best = -float('inf') if maximizing else float('inf')
    for _, _, child in _children(h, side, me, budget):
        value = _deep_search(child, 1 - side, me, depth - 1, alpha, beta, budget)
        if maximizing:
            best = max(best, value)
            alpha = max(alpha, best)
        else:
            best = min(best, value)
            beta = min(beta, best)
        if alpha >= beta:
            break
    return best


def _strong_move(g: dict, side: int, rng: random.Random) -> tuple[int, int]:
    budget = [KHO_NODES]
    children = _children(g, side, side, budget)
    # Randomize only the order of tied candidates, never the final score.
    children.sort(key=lambda item: (item[0], rng.random()), reverse=True)
    chosen = children[0][1]
    for depth in range(3, KHO_DEPTH + 1):
        alpha, scored = -float('inf'), []
        candidate = chosen
        try:
            for _, move, child in children:
                value = _deep_search(child, 1 - side, side, depth - 1,
                                     alpha, float('inf'), budget)
                scored.append((value, move, child))
                if value > alpha:
                    alpha, candidate = value, move
        except _SearchLimit:
            break  # a partly searched depth cannot replace a fully searched one
        chosen = candidate
        children = sorted(scored, key=lambda item: item[0], reverse=True)
    return chosen


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
