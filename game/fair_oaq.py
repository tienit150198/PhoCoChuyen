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
"kho" (Ông Hai, owner 06/10: "mạnh không ai thắng được", 09/10: "hạn chế cho người ta thắng"): a fixed opening, then
negamax alpha-beta with principal variation search, iterative deepening, a transposition table, captures/killer/history
move ordering and an evaluation of captures, dân on each row and mobility; finished games are scored exactly, so short
endgames are solved. The work is at most KHO_NODES simulated moves and KHO_MS milliseconds; each move is a fresh draw
among those within KHO_SPREAD of his best (see the opponent's section).
"""
from __future__ import annotations

import random
import time

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
    """A plain view of a position (the tests' look-ahead players): captures, plus a little for dân on its own row."""
    own = sum(g['b'][c] for c in ROWS[side])
    other = sum(g['b'][c] for c in ROWS[1 - side])
    return score(g, side) - score(g, 1 - side) + 0.3 * (own - other)


def _search(g: dict, side: int, me: int, depth: int) -> float:
    """Plain minimax with _value, `depth` moves deep, for `me` (the tests' look-ahead players)."""
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
# Ông Hai (owner 09/10: "ông Hai tăng lên để k cho người dùng thắng nữa"). Until 09/10 he searched a fixed number of
# moves and, the board being the same, always answered the same way: one player won 502 of 532 games with two lines
# learnt by heart (one for each way he opened). Now:
# * he opens from the middle ô (OPENING, either way: mirror images), the best of the ten in test matches;
# * every other move is a fresh draw: each candidate gets a bonus of 0..KHO_SPREAD tenths of a dân, so any move that
#   close to his best may come (a proven result is never traded for it), and no line comes back for sure;
# * the search is bounded by moves (KHO_NODES) and by time (KHO_MS): a move costs a server worker ~30 ms (the 05/10
#   one: ~350 ms), each simulated move about twice as cheap (flat positions, _sow).
OPENING = ((9, 1), (9, -1))   # 24 games each against the 1.9.36 engine: the player won 0 (ô 8 / 10: 17%, 42%; ô 7 / 11: 88%+)
KHO_NODES = 4000     # simulated moves per request at most
KHO_MS = 35          # ... and this many milliseconds (read every _TICK + 1 moves; the first ply is always searched)
KHO_MAX_DEPTH = 40   # iterative deepening stops here (or once the result is proven)
KHO_SPREAD = 2       # the bonus drawn for each of his moves, in tenths of a dân
_WIN = 1_000_000     # a finished game, plus the margin; any heuristic value stays far below
_TICK = 255          # the clock is read once every _TICK + 1 simulated moves

# The search works on a flat position: a list of 18 ints, b[0..11], q[0], q[1], cap[0..3] (the dict's own order).
_QI = (12, 13)
_CAP = (14, 16)
_NEXT = (None, tuple((c + 1) % 12 for c in range(12)), tuple((c - 1) % 12 for c in range(12)))   # [d]: d = 1 / -1
_DROP = (None,) + tuple(tuple(tuple(tuple((c + d * k) % 12 for k in range(1, n + 1)) for n in range(12)) for c in range(12))
                        for d in (1, -1))   # [d][cell][n]: the n ô after `cell` going `d`


class _SearchLimit(Exception):
    pass


def _flat(g: dict) -> list:
    return g['b'] + g['q'] + g['cap']


def _sow(s: list, side: int, cell: int, d: int) -> tuple | None:
    """`play` on a flat position: (the new position, what it captured in dân), or None past MAX_STEPS (then the
    search plays it the slow way). The ply is counted by the caller."""
    b = s[:]
    nx, drop = _NEXT[d], _DROP[d]
    hand, b[cell], pos, steps = b[cell], 0, cell, 0
    while True:
        steps += hand
        if steps > MAX_STEPS:
            return None
        if hand < 12:
            for k in drop[pos][hand]:
                b[k] += 1
        else:
            full, rest = divmod(hand, 12)
            for k in range(12):
                b[k] += full
            for k in drop[pos][rest]:
                b[k] += 1
        pos = (pos + d * hand) % 12
        if steps == MAX_STEPS:
            return b, 0
        n = nx[pos]
        if b[n]:
            if n == 0 or n == 6:
                return b, 0
            hand, b[n], pos = b[n], 0, n
            continue
        if n == 0 and b[12] or n == 6 and b[13]:
            return b, 0
        got, ci = 0, _CAP[side]
        while True:
            t = nx[n]
            if t == 0 or t == 6:
                qi = 12 if t == 0 else 13
                dan, quan = b[t], b[qi]
                if not quan:
                    if not dan:
                        break
                elif dan < QUAN_NON:
                    break
                b[t] = b[qi] = 0
                b[ci + 1] += quan
                got += dan + QUAN * quan
            else:
                dan = b[t]
                if not dan:
                    break
                b[t] = 0
                got += dan
            b[ci] += dan
            n = nx[t]
            if b[n] or n == 0 and b[12] or n == 6 and b[13]:
                break
        return b, got


def _slow(s: list, side: int, cell: int, d: int, ply: int) -> tuple:
    g = dict(b=s[:12], q=s[12:14], cap=s[14:18], ply=ply)
    got = play(g, side, cell, d)
    return _flat(g), got


def _final(s: list, side: int) -> int:
    """The game ends now (collect): `side`'s score minus the other's."""
    sc = [s[14] + QUAN * s[15] + s[1] + s[2] + s[3] + s[4] + s[5], s[16] + QUAN * s[17] + s[7] + s[8] + s[9] + s[10] + s[11]]
    for c, qi in ((0, 12), (6, 13)):
        if s[c] or s[qi]:
            sc[0 if sc[0] >= sc[1] else 1] += s[c] + QUAN * s[qi]
    d = sc[side] - sc[1 - side]
    return _WIN + d if d > 0 else -_WIN + d if d < 0 else 0


def _turn(s: list, side: int, ply: int) -> list | int:
    """begin_turn for the search: the position `side` moves in (rải quân done, a copy), or the final value."""
    if not (s[0] or s[12] or s[6] or s[13]) or ply >= MAX_PLY:
        return _final(s, side)
    row = ROWS[side]
    if s[row[0]] or s[row[1]] or s[row[2]] or s[row[3]] or s[row[4]]:
        return s
    ci = _CAP[side]
    if s[ci] < len(row):
        return _final(s, side)
    s = s[:]
    for c in row:
        s[c] = 1
    s[ci] -= len(row)
    return s


def _eval_flat(s: list, side: int) -> int:
    """Ông Hai's view of an unfinished position for the side to move, in tenths of a dân: the captures, the dân on
    each row (they come home at the end), mobility, and a row that cannot be refilled."""
    if side:
        mine, theirs, a, o = s[7:12], s[1:6], 16, 14
    else:
        mine, theirs, a, o = s[1:6], s[7:12], 14, 16
    own = sum(mine)
    v = 10 * (s[a] - s[o]) + 10 * QUAN * (s[a + 1] - s[o + 1]) + 3 * (own - sum(theirs)) + 2 * (theirs.count(0) - mine.count(0))
    if own == 0 and s[a] < 5:
        v -= 30        # cannot rải quân next turn
    return v


def _eval(g: dict, side: int) -> int:
    return _eval_flat(_flat(g), side)


class _Hai:
    """Negamax alpha-beta (principal variation search) with iterative deepening, a transposition table, captures
    first, killer and history moves, on flat positions. Bounded by `nodes` simulated moves and `ms` milliseconds
    (None: moves only, as the tests use it)."""

    def __init__(self, nodes: int, ms: float | None = None):
        self.left = nodes
        self.deadline = None if ms is None else time.perf_counter() + ms / 1000
        self.tt: dict = {}
        self.killers: dict = {}
        self.history: dict = {}
        self.reached = 0   # the last depth searched in full (for the checks)

    def tick(self) -> None:
        """One more simulated move."""
        self.left -= 1
        self.check()

    def check(self) -> None:
        """Past the budget (moves, or time: read every _TICK + 1 moves), the search stops."""
        if self.left < 0 or not self.left & _TICK and self.deadline is not None and time.perf_counter() > self.deadline:
            raise _SearchLimit

    def search(self, s: list, side: int, depth: int, alpha: int, beta: int, ply: int, height: int = 1) -> int:
        """The value of flat position `s` for `side` (to move, at game ply `ply`), `depth` moves deep."""
        s = _turn(s, side, ply)
        if type(s) is int:
            return s
        if depth <= 0:
            return _eval_flat(s, side)
        nxt = 1 - side
        if depth == 1:   # the frontier: each move's position is valued at once, no table
            best = -2 * _WIN
            for c in ROWS[side]:
                if s[c]:
                    for d in (1, -1):
                        self.left -= 1
                        if self.left < 0 or not self.left & _TICK:
                            self.check()
                        k = _turn((_sow(s, side, c, d) or _slow(s, side, c, d, ply))[0], nxt, ply + 1)
                        v = -k if type(k) is int else -_eval_flat(k, nxt)
                        if v > best:
                            best = v
                            if v >= beta:
                                return v
            return best
        late = ply - (MAX_PLY - 2 * KHO_MAX_DEPTH)
        key = (*s, side, late if late > 0 else 0)
        hit = self.tt.get(key)
        first = None
        if hit is not None:
            h_depth, h_value, h_flag, first = hit
            if h_depth >= depth:
                if h_flag == 0:
                    return h_value
                if h_flag > 0:
                    if h_value > alpha:
                        alpha = h_value
                elif h_value < beta:
                    beta = h_value
                if alpha >= beta:
                    return h_value
        alpha0 = alpha
        best, best_move = -2 * _WIN, None
        d1, i = depth - 1, 0
        if first is not None:   # the table's move first, alone: a cut-off on it saves simulating the others
            self.tick()
            k = (_sow(s, side, *first) or _slow(s, side, *first, ply))[0]
            v = -self.search(k, nxt, d1, -beta, -alpha, ply + 1, height + 1)
            best, best_move, i = v, first, 1
            if v > alpha:
                alpha = v
        if alpha < beta:
            rest = []
            killers = self.killers.get(height, ())
            hist = self.history
            for c in ROWS[side]:
                if s[c]:
                    for d in (1, -1):
                        move = (c, d)
                        if move != first:
                            self.left -= 1
                            if self.left < 0 or not self.left & _TICK:
                                self.check()
                            k, gain = _sow(s, side, c, d) or _slow(s, side, c, d, ply)
                            rest.append((gain, move in killers, hist.get((side, move), 0), move, k))
            rest.sort(reverse=True)
            for _, _, _, move, k in rest:
                if i == 0:
                    v = -self.search(k, nxt, d1, -beta, -alpha, ply + 1, height + 1)
                else:
                    v = -self.search(k, nxt, d1, -alpha - 1, -alpha, ply + 1, height + 1)
                    if alpha < v < beta:
                        v = -self.search(k, nxt, d1, -beta, -alpha, ply + 1, height + 1)
                i += 1
                if v > best:
                    best, best_move = v, move
                    if v > alpha:
                        alpha = v
                        if alpha >= beta:
                            break
        if best >= beta:
            ks = self.killers.setdefault(height, [])
            if best_move not in ks:
                ks.insert(0, best_move)
                del ks[2:]
            self.history[(side, best_move)] = self.history.get((side, best_move), 0) + depth * depth
        self.tt[key] = (depth, best, 1 if best >= beta else -1 if best <= alpha0 else 0, best_move)
        return best

    def best_move(self, g: dict, side: int, rng: random.Random | None = None, spread: int = 0) -> tuple[int, int]:
        """The move for `side` (begin_turn done): the best value plus a bonus of 0..spread tenths drawn for each move
        (from rng), so moves that close are all candidates; a proven result outweighs any bonus."""
        s, ply = _flat(g), g['ply']
        moves = legal(g, side)
        if rng is not None:
            rng.shuffle(moves)
        bonus = {m: (rng.randint(0, spread) if rng is not None and spread else 0) for m in moves}
        kids = []
        for m in moves:   # the first ply is always searched (≤ 10 moves, counted)
            self.left -= 1
            k, gain = _sow(s, side, *m) or _slow(s, side, *m, ply)
            kids.append((gain, m, k))
        kids.sort(key=lambda x: x[0], reverse=True)   # stable: the shuffled order among equal captures
        kids = [(m, k) for _, m, k in kids]
        chosen = kids[0][0]
        nxt = 1 - side
        for depth in range(1, KHO_MAX_DEPTH + 1):
            alpha, scored, done = -3 * _WIN, [], True
            try:
                for i, (m, k) in enumerate(kids):
                    b = bonus[m]
                    if i == 0:
                        v = -self.search(k, nxt, depth - 1, -3 * _WIN, 3 * _WIN, ply + 1)
                    else:
                        v = -self.search(k, nxt, depth - 1, b - alpha - 1, b - alpha, ply + 1)
                        if v + b > alpha:
                            v = -self.search(k, nxt, depth - 1, -3 * _WIN, b - alpha, ply + 1)
                    total = v + b if abs(v) < _WIN // 2 else v
                    scored.append((total, -i, m, k))
                    if total > alpha:
                        alpha = total
            except _SearchLimit:
                done = False
            if scored:
                # The first move (the last depth's best) was fully searched: any move proven better at this depth
                # is better, so even an unfinished depth can only improve the choice.
                chosen = max(scored)[2]
            if not done:
                break
            self.reached = depth
            scored.sort(reverse=True)
            kids = [(m, k) for _, _, m, k in scored]
            if abs(scored[0][0]) >= _WIN // 2 and depth > 1:
                break   # the result is proven (a sure win, or a sure loss whatever Ông Hai does)
        return chosen


def _opening(g: dict, side: int) -> bool:
    return side == 1 and g['ply'] == 0 and g['b'] == [0] + [START] * 5 + [0] + [START] * 5 and g['q'] == [1, 1] and not any(g['cap'])


def _strong_move(g: dict, side: int, rng: random.Random | None = None, nodes: int | None = None,
                 ms: float | None = None) -> tuple[int, int]:
    """Ông Hai's move: his opening (OPENING), else at most KHO_NODES simulated moves and KHO_MS milliseconds, a fresh
    draw among his best."""
    if _opening(g, side):
        return rng.choice(OPENING) if rng is not None else OPENING[0]
    hai = _Hai(KHO_NODES if nodes is None else nodes, KHO_MS if ms is None else ms)
    try:
        return hai.best_move(g, side, rng, KHO_SPREAD if rng is not None else 0)
    except _SearchLimit:   # the first ply (≤ 10 moves) is always searched; a guard all the same
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
