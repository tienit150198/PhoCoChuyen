"""🧩 Ghép ba Phố Mây: a "Tile Master" style triple-match mini-game (owner design, 14/10).

Play (public/js/v4/tile-match.js draws it; this file is the authority):
* Square tiles with item icons from the town (son môi, váy, điện thoại, phở, bánh mì, hoa, thú cưng…) sit in
  overlapping layers. A tile covered, even partly, by a tile of a higher layer is greyed out and cannot be tapped.
  Stacks are piles of face-down tiles: only the top one is open, the rest show as a fan of edges.
* Tapping an open tile moves it to the tray (7 slots); same items sit together, three of a kind vanish.
  Win: the board is cleared. Lose: the tray holds 7 with no triple.
* Boosters: ↩ Hoàn tác (the last tile back), 🔀 Xáo (shuffles the items of the tiles still on the board),
  ⇪ Đẩy ra (the first 3 tray tiles to a holding row; tap them to bring them back), ➕ one more tray slot this level.
  A few are free per real (Vietnam) day; then they cost xu, the price doubling with each paid use in the level.
* 100 levels from LEVELS (game/tile_match_levels.py): a seed plus parameters each, generated deterministically
  here (`build`). Generation plays a hidden intended solution while it assigns the items, so every level is
  solvable by construction; `solve` (an independent search) and the tests check it again for all 100. Later levels
  add 🔒 locked tiles (open once their 🔑 key tile is taken) and 🧊 ice tiles (two taps).

Reward (a money buff, so the server checks everything): each NEW level cleared for the first time gives +0.2 % to
the money a player EARNS from work and business, +20 % at level 100 (`permille`). It is booked as its own row
"🧩 Phúc lợi +X%" next to the earning it multiplies (`fund_bonus`, `till_bonus`, `scale_bonus`, `extra`), at
these places only: own finished jobs (income_gear.completion_bonus, the hook every guarded terminal job calls),
the hired job's salary (employment.on_close, the TT99 practice salary), staff orders (workplace_business._finish),
counter sales (quay_business.sale), the 2.x settlements (scale_settle, special_settle) and the clothing branch's
commission abroad (clothing_abroad.on_close; the salary abroad is the employment salary). Never on bank interest,
Mây Coin, gold, the fair/black market, dog bark, auctions, transfers, gifts or mishaps: none of them calls these.
The day's fund rows are kept out of the 🔥 x3 day's net (journey._end_of_day), so the buff never multiplies twice.

Anti-cheat (2.4.7: a level is self-describing; the page plays locally and sends one command when it is won):
`jr_tile_end {n, moves, ms?}` rebuilds level n from its seed (`build`), replays the taps and boosters, and counts a
win only if n == lv + 1 (the first clear: the buff, at most CAP_DAY a Vietnam day) or n <= lv (a replay: nothing but
the boosters' price). Boosters ride in `moves` and are priced at the end (today's free uses first, then xu doubling
within the level; refused when the wallet is short). A first clear needs max(MIN_LEVEL_MS, MIN_TAP_MS × taps) of
server time since the save's clock `cur.t` (set by the previous accepted first clear, or an older page's first
start); a save that never had a clock falls back to the page's own `ms`, once. Nothing else is needed from the
server first, so a lost start, a double start, a quit, a 409 retry or a day change can no longer lose a clear.
Pages of 2.4.5–2.4.6 still send `jr_tile_start {lv}` (records the level; never moves the clock), `jr_tile_boost {kind, lv}`
(grants and charges one booster at once, kept in cur.b / cur.p) and `jr_tile_end {lv, moves}` (its granted boosters
are not charged again). A won end that does not replay as a win changes nothing.

State (optional, absent until the first play): journey['tile'] = {lv: highest cleared (0..100), d: the Vietnam
day of n/u, n: new levels cleared that day, u: {booster: free uses that day}, cur: {lv: the next level (or an older
page's level), t: the clock (server ms), b: {booster: granted to an older page's attempt}, p: {booster: paid by
it}}}. The shape is 2.4.5's and 2.4.6's (journey.validate there checks it the same way), so a rollback reads it unchanged.
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import time

from . import price_index

VERSION = 1
KEY = 'tile'
LEVEL_MAX = 100
CAP_DAY = 15                 # the save's bound on `n` (older builds validate n <= 15); owner 14/10: NO daily cap any more
DAILY_CAP = False            # owner 14/10 "đừng giới hạn 1 ngày 15 màn, chơi không giới hạn"
MIN_TAP_MS = 250             # at least this much server time per tap…
MIN_LEVEL_MS = 20_000        # …and per level
PERMILLE_PER_LEVEL = 2       # +0.2 % a level
TRAY = 7
SLOT_MAX = 1                 # ➕ at most once a level
HOLD = 3                     # ⇪ the holding row's places
BOOSTS = ('undo', 'shuffle', 'push', 'slot')
MOVE = {'undo': -1, 'shuffle': -2, 'push': -3, 'slot': -4}
BOOST_OF = {v: k for k, v in MOVE.items()}
FREE = {'undo': 3, 'shuffle': 1, 'push': 1, 'slot': 1}
PRICE = {k: price_index.price(v) for k, v in {'undo': 40, 'shuffle': 80, 'push': 100, 'slot': 150}.items()}
PAID_MAX = 12                # paid uses of one booster in one attempt (the 13th would cost 4096 × the base)
MOVES_MAX = 2000
ICE, KEY_TILE, LOCK = 1, 2, 4
PREFIX = '🧩 Phúc lợi'
NAME = '🧩 Ghép ba Phố Mây'
VN = datetime.timezone(datetime.timedelta(hours=7))
# The town's things, the most distinct first (early levels take from the front). Each must draw on the oldest phone the
# game opens on (iOS 15.0, Emoji 13): 2.4.10 put 🥥 where 🪷 was (Emoji 14, iOS 15.4: a blank box from level 77 on
# iOS 15.0–15.3); same place in the tuple, so every level keeps its layout and kinds.
ICONS = ('💄', '📱', '🍜', '🐶', '☕', '👗', '💐', '⌚', '🥖', '👜', '🐱', '🧋', '🍨', '🧴', '👠', '💍',
         '🎤', '🍉', '🛵', '🏮', '🎁', '🧸', '🌸', '🍚', '🥐', '🥥', '🐠', '💅')


def _core():
    from . import engine
    return engine


def _now() -> float:
    return time.time()


def today(t: float | None = None) -> str:
    return datetime.datetime.fromtimestamp(_now() if t is None else t, VN).date().isoformat()


# ---------------------------------------------------------------- deterministic random (same as the page's)
M32 = 0xFFFFFFFF


class Rng:
    """mulberry32, bit for bit the page's (tile-match.js rng): the shuffle booster is replayed on both sides."""

    def __init__(self, seed: int):
        self.a = seed & M32

    def next(self) -> int:
        self.a = (self.a + 0x6D2B79F5) & M32
        a = self.a
        t = ((a ^ (a >> 15)) * (1 | a)) & M32
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & M32)) & M32) ^ t
        return (t ^ (t >> 14)) & M32

    def below(self, n: int) -> int:
        return self.next() % n if n > 0 else 0

    def chance(self, permille: int) -> bool:
        return self.below(1000) < permille

    def pick(self, seq):
        return seq[self.below(len(seq))]

    def shuffle(self, seq: list) -> list:
        for i in range(len(seq) - 1, 0, -1):
            j = self.below(i + 1)
            seq[i], seq[j] = seq[j], seq[i]
        return seq


def shuffle_seed(seed: int, n: int) -> int:
    """The n-th 🔀 of a level (0-based)."""
    return (seed ^ ((0x9E3779B1 * (n + 1)) & M32)) & M32


# ---------------------------------------------------------------- shapes (7 × 8 cells; '#' is a tile place)
SHAPES = {
    'o3': ('###', '###', '###'),
    'bar': ('####', '####', '####'),
    'plus': ('.###.', '#####', '#####', '#####', '.###.'),
    'diamond': ('..#..', '.###.', '#####', '.###.', '..#..'),
    'square': ('#####', '#####', '#####', '#####', '#####'),
    'pyramid': ('...#...', '..###..', '.#####.', '#######', '#######'),
    'heart': ('.##.##.', '#######', '#######', '#######', '.#####.', '..###..', '...#...'),
    'house': ('...#...', '..###..', '.#####.', '#######', '.#####.', '.##.##.', '.##.##.'),
    'butterfly': ('##...##', '###.###', '#######', '..###..', '#######', '###.###', '##...##'),
    'hourglass': ('#######', '.#####.', '..###..', '..###..', '.#####.', '#######'),
    'ring': ('#######', '##...##', '#.....#', '#.....#', '##...##', '#######'),
    'x': ('##...##', '###.###', '.#####.', '..###..', '.#####.', '###.###', '##...##'),
    'big': ('#######', '#######', '#######', '#######', '#######', '#######', '#######'),
    # the town's landmarks
    'pagoda': ('...#...', '.#####.', '..###..', '#######', '.#####.', '.#.#.#.', '#######'),        # 🛕 Chùa
    'lighthouse': ('...#...', '..###..', '...#...', '..###..', '..###..', '.#####.', '.#####.', '#######'),  # 🗼 Hải đăng
    'lantern': ('...#...', '.#####.', '#######', '#######', '#######', '.#####.', '...#...'),      # 🏮 Đèn lồng
    'boba': ('....#..', '...#...', '#######', '.#####.', '.#####.', '..###..', '..###..'),         # 🧋 Ly trà sữa
    'bridge': ('#######', '#######', '##...##', '#.....#', '#.....#'),                             # 🌉 Cầu Thê Húc
}
SHAPE_NAMES = {'heart': 'Trái tim', 'house': 'Ngôi nhà', 'pagoda': 'Chùa', 'lighthouse': 'Hải đăng', 'lantern': 'Đèn lồng',
               'boba': 'Ly trà sữa', 'bridge': 'Cây cầu', 'pyramid': 'Kim tự tháp', 'butterfly': 'Cánh bướm'}
OFFSETS = {'d': (1, 1), 'h': (1, 0), 'v': (0, 1), 's': (0, 0)}
COLS, ROWS = 7, 8
W, H = COLS * 2, ROWS * 2    # the board in half tiles
STACK_SPOTS = ((0, 17), (12, 17), (6, 17))   # under the board: left, right, middle


def _cells(shape: str) -> list[tuple[int, int]]:
    rows = SHAPES[shape]
    w = max(len(r) for r in rows)
    ox, oy = (COLS - w) // 2, (ROWS - len(rows)) // 2
    return [(ox + x, oy + y) for y, r in enumerate(rows) for x, ch in enumerate(r) if ch == '#']


def _covers(a, b) -> bool:
    """Two tiles (x, y in half tiles, 2 × 2) overlap."""
    return abs(a[0] - b[0]) < 2 and abs(a[1] - b[1]) < 2


# ---------------------------------------------------------------- level generation
class Gen(Exception):
    pass


def _layout(rng: Rng, shape: str, layers: int, fill: int, offset: str) -> list[tuple[int, int, int]]:
    """Tile places [(x, y, z)], symmetric left-right; each tile of layer z rests on layer z-1."""
    base = [(2 * x, 2 * y, 0) for x, y in _cells(shape)]
    out = list(base)
    below = base
    dx, dy = OFFSETS[offset]
    for z in range(1, layers):
        ox, oy = (dx, dy) if z % 2 else (0, 0)
        quarters = {(t[0] + i, t[1] + j) for t in below for i in (0, 1) for j in (0, 1)}
        cand = [(x, y, z) for y in range(oy, H, 2) for x in range(ox, W, 2)
                if all((x + i, y + j) in quarters for i in (0, 1) for j in (0, 1))]
        keep = {}
        for c in cand:
            m = (W - 2 - c[0], c[1])
            k = min((c[0], c[1]), m)
            if k not in keep:
                keep[k] = rng.chance(fill)
        layer = [c for c in cand if keep[min((c[0], c[1]), (W - 2 - c[0], c[1]))]]
        if not layer:
            break
        out += layer
        below = layer
    return out


def _trim(rng: Rng, places: list, total_extra: int, target: int) -> list:
    """Remove top tiles (nothing above them), in mirrored pairs where possible, down to `target` (a multiple
    of 3 with the stacks' tiles)."""
    places = list(places)
    want = max(3, target)
    while (len(places) + total_extra) % 3 or len(places) + total_extra > want:
        tops = [p for p in places if not any(q[2] > p[2] and _covers(p, q) for q in places)]
        tops.sort(key=lambda p: (-p[2], p[1], p[0]))
        total = len(places) + total_extra
        rm = total - want if total > want else total % 3
        hi = tops[0][2]
        layer = [p for p in tops if p[2] == hi]
        centre = [p for p in layer if p[0] == W // 2 - 1]
        pairs = [p for p in layer if p[0] < W // 2 - 1 and (W - 2 - p[0], p[1], p[2]) in layer]
        if rm >= 2 and pairs:
            p = rng.pick(pairs)
            places.remove(p)
            places.remove((W - 2 - p[0], p[1], p[2]))
        elif centre:
            places.remove(rng.pick(centre))
        else:
            places.remove(rng.pick(layer))
        if len(places) < 3:
            raise Gen('too few')
    return places


def _blockers(places: list) -> list[list[int]]:
    return [[j for j, q in enumerate(places) if q[2] > p[2] and _covers(p, q)] for p in places]


def _order(rng: Rng, n: int, blockers: list[list[int]]) -> list[int]:
    """A random order in which every tile is open when it is taken (the intended solution's order)."""
    left = [len(b) for b in blockers]
    under = [[] for _ in range(n)]
    for i, b in enumerate(blockers):
        for j in b:
            under[j].append(i)
    ready = sorted(i for i in range(n) if not left[i])
    out = []
    while ready:
        i = ready.pop(rng.below(len(ready)))
        out.append(i)
        for d in under[i]:
            left[d] -= 1
            if not left[d]:
                ready.append(d)
        ready.sort()
    if len(out) != n:
        raise Gen('cycle')
    return out


def _assign(rng: Rng, order: list[int], kinds: int, peak: int, eager: int) -> list[int]:
    """Items along the intended order so that playing it never holds more than `peak` tiles in the tray."""
    n = len(order)
    triples = n // 3
    per = [triples // kinds + (1 if i < triples % kinds else 0) for i in range(kinds)]
    for _ in range(80):
        left = list(per)
        rng.shuffle(left)
        open_ = {}           # kind -> tiles of it in the tray (1 or 2)
        kind = [0] * n
        ok = True
        for step, t in enumerate(order):
            size = sum(open_.values())
            rest = n - step - 1
            need = sum(3 - v for v in open_.values())
            twos = sum(1 for v in open_.values() if v == 2)
            # never step into a full tray (peak) with no pair waiting to be completed: a dead end
            joins = [k for k, v in sorted(open_.items()) if v == 2 or size + 1 <= peak]   # a 1 joined is a pair
            can_new = (size + 1 < peak or (size + 1 == peak and twos)) and rest >= need + 2 \
                and any(left[k] > 0 and k not in open_ for k in range(kinds))
            if can_new and (not joins or rng.chance(eager)):
                free = [k for k in range(kinds) if left[k] > 0 and k not in open_]
                most = max(left[k] for k in free)
                k = rng.pick([k for k in free if left[k] >= most - 1])
                left[k] -= 1
                open_[k] = 1
            elif joins:
                twos = [k for k in joins if open_[k] == 2]
                k = rng.pick(twos) if twos and rng.chance(550) else rng.pick(joins)
                open_[k] += 1
                if open_[k] == 3:
                    del open_[k]
            else:
                ok = False
                break
            kind[t] = k
        if ok and not open_:
            return kind
    raise Gen('assign')


TABLE = 2   # the level table this build serves (2.4.7: harder from level 5); 1 = 2.4.5–2.4.6's, still replayed


def table(v: int = TABLE) -> tuple:
    if v == 1:
        from .tile_match_levels_v1 import LEVELS
    else:
        from .tile_match_levels import LEVELS
    return LEVELS


def build(lv: int, row: tuple | None = None, v: int = TABLE) -> dict:
    """Level `lv` (1..100) from its row in table `v`: a dict the page draws and `Game` replays."""
    if row is None:
        row = table(v)[lv - 1]
    seed, shape, kinds, layers, fill, offset, stacks, locks, ice, peak, target = row
    rng = Rng(seed)
    stack_n = sum(stacks)
    places = _layout(rng, shape, layers, fill, offset)
    places = _trim(rng, places, stack_n, target)
    board = len(places)
    # stacks: the top first, each under the one above it
    stack_rows = []
    for si, depth in enumerate(stacks):
        x, y = STACK_SPOTS[si]
        ids = list(range(len(places), len(places) + depth))
        for d in range(depth):
            places.append((x, y, depth - d))
        stack_rows.append(dict(x=x, y=y, ids=ids))
    n = len(places)
    blockers = _blockers(places[:board]) + [[] for _ in range(stack_n)]
    for st in stack_rows:
        for a, b in zip(st['ids'], st['ids'][1:]):
            blockers[b] = [a]
    order = _order(rng, n, blockers)
    pos = {t: i for i, t in enumerate(order)}
    eager = 350 + 120 * (peak - 3)
    kind = _assign(rng, order, kinds, peak, eager)
    flags = [0] * n
    lock_of = {}
    stacked = set(range(board, n))
    if locks:
        # a lock: a tile open early (visible) whose key is taken earlier in the intended order
        top = rng.shuffle([t for t in range(board) if not blockers[t] and pos[t] > n // 6])
        rest = rng.shuffle([t for t in range(board) if blockers[t] and pos[t] > n // 6])
        cands = top + rest
        used = set()
        for t in cands:
            if len(lock_of) >= locks:
                break
            keys = [k for k in order[:pos[t]] if k not in used and k not in lock_of and k != t and k not in stacked
                    and pos[t] - pos[k] >= 3]
            if not keys:
                continue
            k = rng.pick(keys[-12:])
            lock_of[t] = k
            used.add(k)
            used.add(t)
            flags[t] |= LOCK
            flags[k] |= KEY_TILE
            blockers[t] = sorted(set(blockers[t]) | {k})
    if ice:
        cands = [t for t in range(board) if not flags[t]]
        rng.shuffle(cands)
        for t in cands[:ice]:
            flags[t] |= ICE
    pool = list(ICONS[:max(kinds + 4, min(len(ICONS), 8 + kinds))])
    icons = []
    for _ in range(kinds):
        icons.append(pool.pop(rng.below(len(pool)) if lv > 3 else 0))
    solution = []
    for t in order:
        solution += [t, t] if flags[t] & ICE else [t]
    return dict(lv=lv, v=v, seed=seed, shape=shape, cap=TRAY, w=W, h=H + (3 if stacks else 0), icons=icons,
                tiles=[[x, y, z, kind[i], flags[i]] for i, (x, y, z) in enumerate(places)],
                b=blockers, stacks=stack_rows, board=board, peak=peak, solution=solution)


_CACHE: dict[tuple, dict] = {}


def level(lv: int, v: int = TABLE) -> dict:
    """The built level (bounded cache: at most LEVEL_MAX entries a table)."""
    got = _CACHE.get((v, lv))
    if got is None:
        got = _CACHE[v, lv] = build(lv, v=v)
    return got


def public_level(lv: int) -> dict:
    """What the page needs (no intended solution). `v` names the table: the page sends it back with the end."""
    x = level(lv)
    return {k: v for k, v in x.items() if k not in ('solution', 'peak')}


# ---------------------------------------------------------------- the rules (replayed by the server)
class Bad(Exception):
    pass


class Game:
    """One attempt. `tap(t)` and the boosters change it; `won`/`lost` end it. The page runs the same rules."""

    def __init__(self, lv: dict):
        self.lv = lv
        self.n = len(lv['tiles'])
        self.kind = [t[3] for t in lv['tiles']]
        self.ice = [1 if t[4] & ICE else 0 for t in lv['tiles']]
        self.where = ['b'] * self.n          # b board, t tray, h hold, g gone
        self.block = [len(b) for b in lv['b']]
        self.under = [[] for _ in range(self.n)]
        for i, b in enumerate(lv['b']):
            for j in b:
                self.under[j].append(i)
        self.tray: list[int] = []
        self.hold: list[int] = []
        self.cap = lv['cap']
        self.undo_stack: list[tuple] = []
        self.shuffles = 0
        self.slots = 0
        self.gone = 0
        self.taps = 0
        self.lost = False
        self.used = dict.fromkeys(BOOSTS, 0)

    @property
    def won(self) -> bool:
        return self.gone == self.n

    @property
    def over(self) -> bool:
        return self.lost or self.won

    def open(self, t: int) -> bool:
        return self.where[t] == 'h' or (self.where[t] == 'b' and self.block[t] == 0)

    def _leave_board(self, t):
        for d in self.under[t]:
            self.block[d] -= 1

    def _back_on_board(self, t):
        for d in self.under[t]:
            self.block[d] += 1

    def _to_tray(self, t):
        k = self.kind[t]
        at = len(self.tray)
        for i in range(len(self.tray) - 1, -1, -1):
            if self.kind[self.tray[i]] == k:
                at = i + 1
                break
        self.tray.insert(at, t)
        self.where[t] = 't'
        same = [x for x in self.tray if self.kind[x] == k]
        if len(same) == 3:
            for x in same:
                self.tray.remove(x)
                self.where[x] = 'g'
            self.gone += 3
            self.undo_stack = []
            return same
        if len(self.tray) >= self.cap:
            self.lost = True
        return None

    def tap(self, t: int):
        if self.over or type(t) is not int or not 0 <= t < self.n or not self.open(t):
            raise Bad('tap')
        self.taps += 1
        if self.where[t] == 'b' and self.ice[t]:
            self.ice[t] -= 1
            return 'ice'
        if self.where[t] == 'h':
            i = self.hold.index(t)
            self.hold.pop(i)
            self.undo_stack.append((t, i))
        else:
            self._leave_board(t)
            self.undo_stack.append((t, None))
        return self._to_tray(t) or 'tray'

    def undo(self):
        if self.over or not self.undo_stack:
            raise Bad('undo')
        t, i = self.undo_stack.pop()
        self.tray.remove(t)
        if i is None:
            self.where[t] = 'b'
            self._back_on_board(t)
        else:
            self.hold.insert(i, t)
            self.where[t] = 'h'
        self.used['undo'] += 1

    def shuffle(self):
        if self.over:
            raise Bad('shuffle')
        ids = [t for t in range(self.n) if self.where[t] == 'b']
        if len(ids) < 2:
            raise Bad('shuffle')
        kinds = [self.kind[t] for t in ids]
        Rng(shuffle_seed(self.lv['seed'], self.shuffles)).shuffle(kinds)
        for t, k in zip(ids, kinds):
            self.kind[t] = k
        self.shuffles += 1
        self.used['shuffle'] += 1

    def push(self):
        if self.over or not self.tray or self.hold:
            raise Bad('push')
        out, self.tray = self.tray[:HOLD], self.tray[HOLD:]
        for t in out:
            self.where[t] = 'h'
        self.hold = out
        self.undo_stack = []
        self.used['push'] += 1

    def slot(self):
        if self.over or self.slots >= SLOT_MAX:
            raise Bad('slot')
        self.slots += 1
        self.cap += 1
        self.used['slot'] += 1

    def move(self, m: int):
        if type(m) is not int:
            raise Bad('move')
        if m >= 0:
            return self.tap(m)
        b = BOOST_OF.get(m)
        if b is None:
            raise Bad('move')
        getattr(self, b)()
        return b


def replay(lv: dict, moves) -> Game:
    """The attempt after `moves` (raises Bad on an impossible move)."""
    if not isinstance(moves, list) or len(moves) > MOVES_MAX:
        raise Bad('moves')
    g = Game(lv)
    for m in moves:
        g.move(m)
    return g


# ---------------------------------------------------------------- the solver (an independent check)
def solve(lv: dict, cap: int = TRAY, limit: int = 400_000) -> list[int] | None:
    """A sequence of taps that clears the level without boosters, or None (not found within `limit` nodes).
    The tray's content only depends on which tiles were taken (each kind's count mod 3), so the search
    remembers dead sets of taken tiles."""
    tiles = lv['tiles']
    n = len(tiles)
    kind = [t[3] for t in tiles]
    ice = [t[4] & ICE for t in tiles]
    block = [len(b) for b in lv['b']]
    under = [[] for _ in range(n)]
    for i, b in enumerate(lv['b']):
        for j in b:
            under[j].append(i)
    height = [tiles[i][2] for i in range(n)]
    counts = [0] * (max(kind) + 1)
    dead = set()
    path = []
    nodes = [0]

    def rec(mask: int, size: int) -> bool:
        if len(path) == n:
            return True
        nodes[0] += 1
        if nodes[0] > limit or mask in dead:
            return False
        opens = [t for t in range(n) if not (mask >> t) & 1 and block[t] == 0]
        opens.sort(key=lambda t: (-counts[kind[t]], -len(under[t]), -height[t], t))
        for t in opens:
            c = counts[kind[t]]
            nsize = size - 2 if c == 2 else size + 1
            if nsize >= cap:
                continue
            counts[kind[t]] = (c + 1) % 3
            for d in under[t]:
                block[d] -= 1
            path.append(t)
            if rec(mask | (1 << t), nsize):
                return True
            path.pop()
            for d in under[t]:
                block[d] += 1
            counts[kind[t]] = c
            if nodes[0] > limit:
                return False
        dead.add(mask)
        return False

    import sys
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, n + 200))
    try:
        ok = rec(0, 0)
    finally:
        sys.setrecursionlimit(old)
    if not ok:
        return None
    out = []
    for t in path:
        out += [t, t] if ice[t] else [t]
    return out


# ---------------------------------------------------------------- difficulty (offline, for the level table)
def greedy_rate(lv: dict, runs: int = 48, seed: int = 7) -> float:
    """Share of wins of a plausible quick player: completes a pair when it can, often follows a single, else
    taps any open tile. No boosters. Deterministic."""
    rng = Rng(seed)
    wins = 0
    for _ in range(runs):
        g = Game(lv)
        while not g.over:
            opens = [t for t in range(g.n) if g.open(t)]
            cnt = {}
            for x in g.tray:
                cnt[g.kind[x]] = cnt.get(g.kind[x], 0) + 1
            # a careful but short-sighted player: a pair first, then a single, then whatever opens the most tiles;
            # every choice a little noisy, like a thumb in a hurry
            def score(t):
                c = cnt.get(g.kind[t], 0)
                seen = sum(1 for o in opens if g.kind[o] == g.kind[t])
                return (3 if c == 2 else 2 if c == 1 else 1 if c + seen >= 3 else 0) * 10 + min(9, len(g.under[t])) + rng.below(6)
            g.tap(max(opens, key=score) if not rng.chance(120) else rng.pick(opens))
        wins += g.won
    return wins / runs


def difficulty(lv: dict, rate: float | None = None) -> float:
    """0..100: how hard the level plays (mostly the quick player's failure rate, then size and twists)."""
    n = len(lv['tiles'])
    kinds = len(lv['icons'])
    layers = 1 + max(t[2] for t in lv['tiles'][:lv['board']])
    locks = sum(1 for t in lv['tiles'] if t[4] & LOCK)
    ice = sum(1 for t in lv['tiles'] if t[4] & ICE)
    stacked = n - lv['board']
    rate = greedy_rate(lv) if rate is None else rate
    return round(46 * (1 - rate) + 18 * min(1, n / 180) + 14 * min(1, (kinds - 3) / 14) + 8 * min(1, (layers - 1) / 6)
                 + 5 * min(1, stacked / 24) + 6 * min(1, (locks + ice / 3) / 10) + 3 * (lv['peak'] - 3) / 3, 2)


# ---------------------------------------------------------------- the save
def get(s: dict) -> dict | None:
    t = (s.get('journey') or {}).get(KEY)
    return t if isinstance(t, dict) else None


def cleared(s: dict) -> int:
    t = get(s)
    lv = t.get('lv') if t else 0
    return lv if type(lv) is int and 0 <= lv <= LEVEL_MAX else 0


def permille(s: dict) -> int:
    """The buff in ‰ of what is earned: 2 a cleared level, 200 (20 %) at most."""
    return min(LEVEL_MAX, cleared(s)) * PERMILLE_PER_LEVEL


def pct_text(pm: int) -> str:
    whole, part = divmod(pm, 10)
    return f'{whole},{part}' if part else str(whole)


def _ensure(s: dict) -> dict:
    j = s['journey']
    t = j.get(KEY)
    if not isinstance(t, dict):
        t = j[KEY] = dict(lv=0, d=today(), n=0, u={})
    if t.get('d') != today():
        t['d'] = today()
        t['n'] = 0
        t['u'] = {}
    return t


def free_left(t: dict | None) -> dict:
    fresh = not t or t.get('d') != today()
    used = {} if fresh else (t.get('u') or {})
    return {k: max(0, FREE[k] - int(used.get(k, 0))) for k in BOOSTS}


def price(kind: str, paid: int) -> int:
    return PRICE[kind] * (2 ** paid)


def public(s: dict) -> dict:
    """journey.tile for the page (also when the save has none yet)."""
    t = get(s)
    fresh = not t or t.get('d') != today()
    cur = (t or {}).get('cur') if t else None
    pm = permille(s)
    out = dict(lv=cleared(s), max=LEVEL_MAX, pm=pm, pct=pct_text(pm), n=0 if fresh else int(t.get('n', 0)), cap=CAP_DAY, capped=DAILY_CAP, day=today(),
               free=free_left(t), price=dict(PRICE), slot_max=SLOT_MAX)
    if isinstance(cur, dict):
        out['cur'] = dict(lv=cur['lv'], b=dict(cur.get('b') or {}), p=dict(cur.get('p') or {}))
        out['at'] = cur['t']   # the clock: a first clear is counted from need_ms(taps) after it (server ms)
    out['min'] = dict(level=MIN_LEVEL_MS, tap=MIN_TAP_MS)
    return out


def _ms() -> int:
    return int(_now() * 1000)


def _clock(t: dict, now: int) -> int:
    """The save's clock: the previous accepted first clear (or an older page's first start); `now` if it has none."""
    cur = t.get('cur')
    return cur['t'] if isinstance(cur, dict) and type(cur.get('t')) is int else now


def _rest(t: dict, clock: int) -> None:
    """cur between attempts: the next level and the clock, no booster of an older page's attempt (2.4.5's shape)."""
    t['cur'] = dict(lv=min(LEVEL_MAX, t['lv'] + 1), t=clock, b={}, p={})


def need_ms(taps: int) -> int:
    """The least server time a first clear of `taps` taps takes since the clock."""
    return max(MIN_LEVEL_MS, MIN_TAP_MS * taps)


def _end(s: dict, p: dict, e) -> dict:
    """A finished level, self-described: {n, moves, ms?} (or an older page's {lv, moves}). See the module doc."""
    need = e.need
    new = 'n' in p
    need(({'n', 'moves'} <= set(p) <= {'n', 'moves', 'ms', 'v'}) if new else set(p) == {'lv', 'moves'}, 'Thao tác không hợp lệ.')
    need(type(p.get('v', TABLE)) is int and p.get('v', TABLE) in (1, TABLE), 'Màn chơi không hợp lệ.', 'tile_level')
    lv = p['n'] if new else p['lv']
    need(type(lv) is int and 1 <= lv <= LEVEL_MAX, 'Màn chơi không hợp lệ.', 'tile_level')
    moves = p['moves']
    need(isinstance(moves, list) and len(moves) <= MOVES_MAX and all(type(m) is int for m in moves), 'Ván chơi không hợp lệ.', 'tile_invalid')
    t = _ensure(s)
    need(lv <= t['lv'] + 1, f'Qua màn {t["lv"] + 1} trước đã nhé.', 'tile_locked')
    # The table the page played: its own `v`; a 2.4.5–2.4.6 page (no `v`) may hold a level of either table.
    g = None
    for v in ((p.get('v', TABLE),) if new else (TABLE, 1)):
        try:
            g = replay(level(lv, v), moves)
        except Bad:
            continue
        if g.won:
            break
    if g is None:
        raise e.GameError('Ván chơi không khớp với màn này.', 'tile_invalid')
    if not g.won:   # never sent by a page for a game it did not win: nothing changes (a stale end cannot undo anything)
        return dict(message='Chưa qua màn. Thử lại nhé!', win=False, lv=lv, tile=public(s))
    cur = t.get('cur')
    cur = cur if isinstance(cur, dict) else None
    mine = cur if cur is not None and not new and cur['lv'] == lv else None   # an older page's attempt: its boosters are paid
    granted, paid = (mine or {}).get('b') or {}, dict((mine or {}).get('p') or {})
    free, cost = free_left(t), 0
    uses = {}
    for k in BOOSTS:
        extra = g.used[k] - granted.get(k, 0)
        if extra <= 0:
            continue
        uses[k] = min(extra, free[k])
        for _ in range(extra - uses[k]):
            n = paid.get(k, 0)
            need(n < PAID_MAX, 'Màn này dùng trợ giúp nhiều quá rồi.', 'tile_paid')
            cost += price(k, n)
            paid[k] = n + 1
    now = _ms()
    first = lv == t['lv'] + 1
    if first:
        need(not DAILY_CAP or t['n'] < CAP_DAY, f'Hôm nay đã qua {CAP_DAY} màn mới, màn này mai tính nhé.', 'tile_cap')
        least = need_ms(g.taps)
        if cur is not None:
            need(now - cur['t'] >= least, 'Nhanh quá, chưa tính màn này. Đợi giây lát nhé!', 'tile_fast')
        else:   # a save with no clock yet (once): the page's own time
            need(type(p.get('ms')) is int and p['ms'] >= least, 'Nhanh quá, không tính màn này. Chơi lại thong thả nhé!', 'tile_fast')
    if cost:
        need(s['journey']['wallet'] >= cost, f'Ví chưa đủ {cost} xu cho trợ giúp đã dùng.', 'tile_poor')
        from . import bank
        bank.pay(s, cost, f'{NAME} · trợ giúp', method='cash', kind='life', short=f'Ví chưa đủ {cost} xu cho trợ giúp.')
    for k, v in uses.items():
        if v:
            t['u'][k] = t['u'].get(k, 0) + v
    if first:
        t['lv'] = lv
        t['n'] = min(CAP_DAY, t['n'] + 1)   # counted for show only; stays within older builds' bound
    _rest(t, now if first or cur is None else cur['t'])
    pm = permille(s)
    msg = f'🎉 Qua màn {lv}!' + (f' {PREFIX} +{pct_text(pm)}%.' if first else '')
    return dict(message=msg, win=True, first=first, lv=lv, taps=g.taps, cost=cost,
                ms=now - cur['t'] if cur is not None else p.get('ms'), tile=public(s))


# ---------------------------------------------------------------- the commands
COMMANDS = ('jr_tile_start', 'jr_tile_boost', 'jr_tile_end', 'jr_tile_quit')


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    need(isinstance(p, dict), 'Thao tác không hợp lệ.')
    j = s['journey']
    need(j.get('story'), 'Ghép ba mở khi bạn đã vào hành trình.', 'tile_story')
    if name == 'jr_tile_start':   # an older page: records the level for its boosters; the clock is never moved
        need(set(p) <= {'lv'}, 'Thao tác không hợp lệ.')
        lv = p.get('lv')
        need(type(lv) is int and 1 <= lv <= LEVEL_MAX, 'Màn chơi không hợp lệ.', 'tile_level')
        t = _ensure(s)
        need(lv <= t['lv'] + 1, f'Qua màn {t["lv"] + 1} trước đã nhé.', 'tile_locked')
        if lv == t['lv'] + 1:
            need(not DAILY_CAP or t['n'] < CAP_DAY, f'Hôm nay đã qua {CAP_DAY} màn mới. Mai chơi tiếp, giờ chơi lại màn cũ cho vui nhé!', 'tile_cap')
        t['cur'] = dict(lv=lv, t=_clock(t, _ms()), b={}, p={})
        return dict(message=f'🧩 Màn {lv}', tile=public(s))
    t = get(s)
    cur = t.get('cur') if t else None
    if name == 'jr_tile_quit':   # an older page: the attempt's boosters are gone; the clock stays
        need(set(p) <= set(), 'Thao tác không hợp lệ.')
        if isinstance(cur, dict):
            _rest(t, cur['t'])
        return dict(message='Đã rời màn.', tile=public(s))
    if name == 'jr_tile_boost':   # an older page
        need(isinstance(cur, dict), 'Bắt đầu một màn trước đã nhé.', 'tile_none')
        need(set(p) == {'kind', 'lv'}, 'Thao tác không hợp lệ.')
        kind = p['kind']
        need(kind in BOOSTS, 'Trợ giúp không hợp lệ.')
        need(p['lv'] == cur['lv'], 'Màn đã đổi, mở lại màn nhé.', 'tile_stale')
        t = _ensure(s)
        cur = t['cur']
        b, paid = cur.setdefault('b', {}), cur.setdefault('p', {})
        if kind == 'slot':
            need(b.get('slot', 0) < SLOT_MAX, 'Mỗi màn chỉ thêm được 1 ô.', 'tile_slot')
        left = free_left(t)[kind]
        if left > 0:
            t['u'][kind] = t['u'].get(kind, 0) + 1
            cost = 0
        else:
            n = paid.get(kind, 0)
            need(n < PAID_MAX, 'Màn này dùng trợ giúp nhiều quá rồi.', 'tile_paid')
            cost = price(kind, n)
            from . import bank
            bank.pay(s, cost, f'{NAME} · trợ giúp', method='cash', kind='life', short=f'Ví chưa đủ {cost} xu cho trợ giúp.')
            paid[kind] = n + 1
        b[kind] = b.get(kind, 0) + 1
        return dict(message=('Miễn phí hôm nay.' if not cost else f'−{cost} xu.'), boost=kind, cost=cost, tile=public(s))
    if name == 'jr_tile_end':
        return _end(s, p, e)
    raise e.GameError('Thao tác không hợp lệ.', 'unknown_action')


def carry_reset(old: dict, fresh: dict) -> None:
    """reset_all keeps the levels cleared and today's counts (they were earned, and the cap must hold)."""
    t = (old.get('journey') or {}).get(KEY)
    if isinstance(t, dict):
        fresh['journey'][KEY] = keep = {k: copy.deepcopy(v) for k, v in t.items() if k != 'cur'}
        if isinstance(t.get('cur'), dict):   # the clock stays (a reset is no way round the time a level takes)
            _rest(keep, t['cur']['t'])


def validate(s: dict) -> None:
    e = _core()
    t = (s.get('journey') or {}).get(KEY)
    if t is None:
        return
    need, integer = e.need, e.integer
    msg = 'Ghép ba trong bản lưu không hợp lệ.'
    need(isinstance(t, dict) and {'lv', 'd', 'n', 'u'} <= set(t) <= {'lv', 'd', 'n', 'u', 'cur'}, msg)
    integer(t['lv'], 0, LEVEL_MAX)
    need(isinstance(t['d'], str) and len(t['d']) == 10, msg)
    integer(t['n'], 0, CAP_DAY)
    need(isinstance(t['u'], dict) and set(t['u']) <= set(BOOSTS), msg)
    for k, v in t['u'].items():
        integer(v, 0, FREE[k])
    cur = t.get('cur')
    if cur is not None:
        need(isinstance(cur, dict) and set(cur) == {'lv', 't', 'b', 'p'}, msg)
        integer(cur['lv'], 1, min(LEVEL_MAX, t['lv'] + 1))
        integer(cur['t'], 0, 10**14)
        for part, top in (('b', FREE['undo'] + PAID_MAX), ('p', PAID_MAX)):
            need(isinstance(cur[part], dict) and set(cur[part]) <= set(BOOSTS), msg)
            for k, v in cur[part].items():
                integer(v, 0, top)
        need(cur['b'].get('slot', 0) <= SLOT_MAX, msg)


# ---------------------------------------------------------------- the buff where money is earned
def extra(s: dict, base: int, key: str) -> int:
    """The buff on an earning of `base` xu (0 below 1 xu or without levels): base × ‰ / 1000, its fraction rounded
    up or down by a hash of `key` (deterministic for a retried command; fair on average, no state)."""
    pm = permille(s)
    if pm <= 0 or type(base) is not int or base <= 0:
        return 0
    whole, frac = divmod(base * pm, 1000)
    if frac and int(hashlib.sha256(f'tile|{key}|{base}'.encode()).hexdigest()[:8], 16) % 1000 < frac:
        whole += 1
    return whole


def label(s: dict, what: str) -> str:
    return f'{PREFIX} +{pct_text(permille(s))}% · {what}'[:120]


def fund_bonus(s: dict, c: dict, base: int, what: str, ref: str | None, *, direct: bool = False) -> int:
    """Book the buff on an earning of a workplace fund as its own 'other_income' row (the fund's cash book stays
    whole: opening balance + rows == fund). `direct`: the staff orders' way (no journal line, like their rows)."""
    bonus = extra(s, base, f'{ref}|{what}|{c.get("day")}')
    if not bonus:
        return 0
    if direct:
        from . import operations as ops
        c['money'] += bonus
        c['earnings'] += bonus
        why = label(s, what)
        ops.record_money(c, bonus, why, ref, 'other_income', group=why)  # the staff orders' rows: one a day
    else:
        _core().money(s, c, bonus, label(s, what), ref, category='other_income')
    return bonus


def day_total(c: dict, day: int) -> int:
    """The buff rows of a workplace's day (kept out of the 🔥 x3 day's net: it never multiplies twice)."""
    rows = c.get('ops', {}).get('finance', {}).get('ledger', [])
    return sum(r['amount'] for r in rows if r.get('day') == day and r.get('amount', 0) > 0
               and r.get('category') == 'other_income' and str(r.get('reason', '')).startswith(PREFIX))
