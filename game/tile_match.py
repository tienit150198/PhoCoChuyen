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
* 300 levels from LEVELS (game/tile_match_levels.py): a seed plus parameters each, generated deterministically
  here (`build`). Generation plays a hidden intended solution while it assigns the items, so every level is
  solvable by construction; `solve` (an independent search) and the tests check it again. Later levels
  add 🔒 locked tiles (open once their 🔑 key tile is taken) and 🧊 ice tiles (two taps). Levels 101–200 (2.4.43)
  stack higher (owner 17/10 "xếp nhiều lớp hơn"): 8 to 14 layers (91–100: 4 to 7), some straight on the one below
  (STRAIGHT); since 2.4.44 also more icons, 22 at 101 to 40 at 200 (owner 18/10 "thêm 30 40 loại thoải mái").

Reward (a money buff, so the server checks everything): each NEW level cleared for the first time gives +0.2 % to
the money a player EARNS from work and business, +20 % at level 100, then +0.1 % a level, +30 % at 200, +40 % at 300 (`permille`). It is booked as its own row
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
Past level 100: journey['tile_hi'] = {lv: cleared past 100 (0..100)}, only beside tile.lv == 100; tile.lv and cur.lv stay
within 100 (older builds keep an unknown journey key as it is, and count the player at level 100).
Past level 200 (2.5.7): journey['tile_hi2'] = {lv: cleared past 200 (0..100), b?: {booster: 🎁 chest uses left}}, only beside
tile_hi.lv == 100 (tile_hi keeps its 2.4.43 shape, so 2.4.43–2.5.6.1 still validate it and count the player at level 200).
⭐ journey['tile_st'] = '0'..'3' a level (the best stars, one character a level, at most LEVEL_MAX): optional, its own key.
`public` still says max=200 (pages of 2.4.43–2.5.6.1 stop there: they do not know the new tiles) and last=300 (this page).

Levels 201–300 (2.5.7, owner 23/10 "thêm mở tới màn 300 nhé, khó hơn, với có item ẩn … học candy fruits"): up to 48
icons, deeper boards, and four special tiles, each introduced on its own level with a card (the page), each replayed here:
* 🎁 BOX (hộp bí ẩn, from 201): the page shows "?" until the tile is open (nothing covers it); then its real item. The
  rules never change (the item is the tile's kind, deterministic from the seed): only what the page shows.
* 🌈 JOKER (cầu vồng, from 211): no item (kind -1). It goes to the tray like a tile (it takes a slot). Whenever the tray
  holds a 🌈 and a pair (two of one item), the leftmost pair and the leftmost 🌈 vanish, and the pair's third tile is
  pulled off the board (or the holding row) with them: of that item's tiles there, the lowest layer, then the lowest
  number. So every item still goes in threes, whichever pair a 🌈 takes. A 🌈 is never needed: the level is won once
  every item is gone (a 🌈 left over vanishes). 🔀 Xáo never moves a 🌈. A clear resets ↩ (as a triple does).
* ⛓️ CHAIN (xích, from 221): level['chain'] = [[tile, c]]: the tile cannot be tapped before c triples (any, 🌈 ones too)
  were cleared in the attempt. Clears never go back (↩ stops at a clear), so a chain once open stays open.
* 💣 BOMB (bom, from 231): level['fuse'] = [[tile, f]]: once the tile is open (or in the tray / holding row) it is lit;
  every tap after that (an ice crack too) takes one from it while it is not gone; at 0 the attempt is lost. Boosters
  never tick it and ↩ never gives a tap back.
Each is placed by `build` along the intended solution (the tile's chain at most the clears before its tap, a bomb's
fuse at least the taps from its lighting to its clear plus a margin), then the solution is replayed with `Game`
(a level that does not win is never made) and `solve` checks it again on its own.
Rewards past 200: +0.1 % a level (+40 % at 300); a 🎁 chest on the first clear of every tenth level (210 … 300) adds
free booster uses kept in tile_hi2.b (used after the day's own free ones, before the 📺 ones).
"""
from __future__ import annotations

import copy
import datetime
import hashlib
import time

from . import price_index

VERSION = 1
KEY = 'tile'
KEY_HI = 'tile_hi'           # levels 101–200 (2.4.43): {lv: 0..100} cleared past 100, its own key so older builds' bounds hold
KEY_HI2 = 'tile_hi2'         # levels 201–300 (2.5.7): {lv: 0..100, b?: {booster: chest uses}}, beside tile_hi.lv == 100
KEY_STAR = 'tile_st'         # ⭐ the best stars a level: '0'..'3' each (2.5.7)
BASE_MAX = 100               # journey.tile.lv and cur.lv stay within this (older builds validate <= 100)
HI_MAX = 200                 # journey.tile_hi.lv stays within 100 (2.4.43–2.5.6.1 validate <= 100); pages of then stop at 200
LEVEL_MAX = 300
CHEST_EVERY = 10             # 🎁 a chest on the first clear of 210, 220 … 300
CHEST = {'undo': 2, 'shuffle': 1, 'push': 1, 'slot': 1}   # ×2 on 250 and 300
CHEST_CAP = 99               # tile_hi2.b: uses kept a booster at most
CAP_DAY = 15                 # the save's bound on `n` (older builds validate n <= 15); owner 14/10: NO daily cap any more
DAILY_CAP = False            # owner 14/10 "đừng giới hạn 1 ngày 15 màn, chơi không giới hạn"
MIN_TAP_MS = 250             # at least this much server time per tap…
MIN_LEVEL_MS = 20_000        # …and per level
PERMILLE_PER_LEVEL = 2       # +0.2 % a level
PERMILLE_PER_HI = 1          # +0.1 % a level past 100: +30 % at 200
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
BOX, JOKER, BOMB, CHAIN = 8, 16, 32, 64   # 🎁 🌈 💣 ⛓️ (levels 201–300, see the module doc)
CHAIN_MAX = 9                # ⛓️ at most this many clears (one digit on the tile)
PREFIX = '🧩 Phúc lợi'
NAME = '🧩 Ghép ba Phố Mây'
VN = datetime.timezone(datetime.timedelta(hours=7))
# The town's things, the most distinct first (early levels take from the front). Each must draw on the oldest phone the
# game opens on (iOS 15.0, Emoji 13): 2.4.10 put 🥥 where 🪷 was (Emoji 14, iOS 15.4: a blank box from level 77 on
# iOS 15.0–15.3); same place in the tuple, so every level keeps its layout and kinds.
ICONS = ('💄', '📱', '🍜', '🐶', '☕', '👗', '💐', '⌚', '🥖', '👜', '🐱', '🧋', '🍨', '🧴', '👠', '💍',
         '🎤', '🍉', '🛵', '🏮', '🎁', '🧸', '🌸', '🍚', '🥐', '🥥', '🐠', '💅',
         # 2.4.44 (owner 18/10 "thêm 30 40 loại thoải mái"): appended, so a level of ≤ 20 kinds draws from the same 28
         '🍩', '🎈', '📷', '🎸', '🍓', '🍕', '🧁', '🎒', '👒', '🌻', '🍔', '🐰', '🐸', '🥭', '🎧', '📚', '🐼', '🦋', '👟', '🎮')


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
# Levels 101–200 also stack some layers straight on the one below ("xếp nhiều lớp hơn", owner 17/10), so the 7 × 8 board
# takes more layers before the shifts shrink it away: an upper-case offset ('H') in pairs (straight, shifted, straight…),
# a digit 3 after it ('h3') one straight layer in every three. Fully covered tiles make a level much harder.
STRAIGHT = {1: lambda z: z % 2, 2: lambda z: (z // 2) % 2, 3: lambda z: (z - z // 3) % 2}   # layer z shifted? by period
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
    shifted = STRAIGHT[int(offset[1:]) if offset[1:] else 2 if offset.isupper() else 1]
    dx, dy = OFFSETS[offset[0].lower()]
    for z in range(1, layers):
        ox, oy = (dx, dy) if shifted(z) else (0, 0)
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


def _assign_x(rng: Rng, order: list[int], kinds: int, peak: int, eager: int, jokers: set, key) -> tuple[list[int], set]:
    """_assign for a level with 🌈 (levels 201–300): items along the intended order, playing Game's own tray (a 🌈 waits
    in the tray; a pair beside a 🌈 clears with it and pulls off the pair's third tile: the lowest `key` of that item on the
    board). The third tile is the board tile of lowest key not yet given an item, so Game pulls that very one. Returns
    (kinds, the tiles pulled off: never tapped)."""
    n = len(order)
    items = n - len(jokers)
    triples = items // 3
    per = [triples // kinds + (1 if i < triples % kinds else 0) for i in range(kinds)]
    by_key = sorted((t for t in range(n) if t not in jokers), key=key)
    for _ in range(80):
        left = list(per)
        rng.shuffle(left)
        kind = [-1] * n
        done = set()        # tiles given an item (tapped or pulled off)
        swept = set()
        tray = []           # the tray's kinds in Game's order, -1 a 🌈
        ptr = [0]
        remaining = [items]   # items not yet given

        def pull(k):
            while ptr[0] < len(by_key) and by_key[ptr[0]] in done:
                ptr[0] += 1
            if ptr[0] >= len(by_key):
                return False
            x = by_key[ptr[0]]
            kind[x] = k
            done.add(x)
            swept.add(x)
            remaining[0] -= 1
            return True

        def settle():
            """Game's clears after a tile came in: a triple, else the leftmost pair with the leftmost 🌈."""
            cnt = {}
            for k in tray:
                if k >= 0:
                    cnt[k] = cnt.get(k, 0) + 1
            for k, v in cnt.items():
                if v == 3:
                    tray[:] = [x for x in tray if x != k]
                    return True
            if -1 in tray:
                for k in tray:
                    if k >= 0 and cnt[k] == 2:
                        tray[:] = [x for x in tray if x != k]
                        tray.remove(-1)
                        return pull(k)
            return None

        ok = True
        live = [t for t in order]
        for i, t in enumerate(live):
            if t in swept:
                continue
            if t in jokers:
                cnt = {}
                for k in tray:
                    if k >= 0:
                        cnt[k] = cnt.get(k, 0) + 1
                if not any(v == 2 for v in cnt.values()) and len(tray) + 1 >= peak:
                    ok = False
                    break
                tray.append(-1)
                if settle() is False:
                    ok = False
                    break
                continue
            open_ = {}
            for k in tray:
                if k >= 0:
                    open_[k] = open_.get(k, 0) + 1
            size = len(tray)
            remaining[0] -= 1
            rest = remaining[0]
            need = sum(3 - v for v in open_.values())
            twos = sum(1 for v in open_.values() if v == 2)
            jk = -1 in tray
            after = next((u for u in live[i + 1:] if u not in swept), None)
            soon = after in jokers and not twos   # a 🌈 comes next: better hold a pair for it
            joins = [k for k, v in sorted(open_.items()) if v == 2 or size + 1 <= peak]
            can_new = (size + 1 < peak or (size + 1 == peak and (twos or jk))) and rest >= need + 2 \
                and any(left[k] > 0 and k not in open_ for k in range(kinds))
            if can_new and (not joins or (not soon and rng.chance(eager))):
                free = [k for k in range(kinds) if left[k] > 0 and k not in open_]
                most = max(left[k] for k in free)
                k = rng.pick([k for k in free if left[k] >= most - 1])
                left[k] -= 1
            elif joins:
                tw = [k for k in joins if open_[k] == 2]
                ones = [k for k in joins if open_[k] == 1]
                if soon and ones:
                    k = rng.pick(ones)
                else:
                    k = rng.pick(tw) if tw and rng.chance(550) else rng.pick(joins)
            else:
                ok = False
                break
            kind[t] = k
            done.add(t)
            at = None
            for j in range(len(tray) - 1, -1, -1):
                if tray[j] == k:
                    at = j + 1
                    break
            if at is None:
                at = tray.index(-1) if -1 in tray else len(tray)
            tray.insert(at, k)
            if settle() is False:
                ok = False
                break
        if ok and not any(k >= 0 for k in tray) and not any(left) and remaining[0] == 0:
            return kind, swept
    raise Gen('assign')


TABLE = 3   # the level table this build serves (2.4.44: levels 101–200 with up to 40 icons); older ones still replayed:
            # 1 = 2.4.5–2.4.6's (100 levels), 2 = 2.4.7–2.4.43's (101–200 with 20 icons since 2.4.43)
TABLES = (1, 2, TABLE)


def table(v: int = TABLE) -> tuple:
    if v == 1:
        from .tile_match_levels_v1 import LEVELS
    elif v == 2:
        from .tile_match_levels_v2 import LEVELS
    else:
        from .tile_match_levels import LEVELS
    return LEVELS


def _row(row: tuple) -> tuple:
    """A level row's parameters; rows of levels 201–300 carry five more: 🎁 boxes, 🌈 jokers, ⛓️ chains, 💣 bombs, tray."""
    extra = tuple(row[11:]) + (0,) * (5 - len(row[11:]))
    return tuple(row[:11]) + extra


def build(lv: int, row: tuple | None = None, v: int = TABLE) -> dict:
    """Level `lv` (1..LEVEL_MAX) from its row in table `v`: a dict the page draws and `Game` replays."""
    if row is None:
        row = table(v)[lv - 1]
    seed, shape, kinds, layers, fill, offset, stacks, locks, ice, peak, target, box, jokers, chains, bombs, cap = _row(row)
    rng = Rng(seed)
    stack_n = sum(stacks)
    places = _layout(rng, shape, layers, fill, offset)
    places = _trim(rng, places, stack_n - jokers, target)   # the items (all but the 🌈) go in threes
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
    special = set()      # 🌈 and the tiles they pull off: never a 🔒, 🔑, 🧊 or another special
    if jokers:
        xr = Rng(seed ^ 0x6A0C3E21)
        cands = [t for t in range(board) if n // 5 <= pos[t] <= n * 4 // 5]
        jk = set(xr.shuffle(cands)[:jokers])
        if len(jk) < jokers:
            raise Gen('jokers')
        kind, swept = _assign_x(rng, order, kinds, peak, eager, jk, lambda t: (places[t][2], t))
        special = jk | swept
    else:
        kind, swept, jk = _assign(rng, order, kinds, peak, eager), set(), set()
    flags = [JOKER if t in jk else 0 for t in range(n)]
    lock_of = {}
    stacked = set(range(board, n))
    if locks:
        # a lock: a tile open early (visible) whose key is taken earlier in the intended order
        top = rng.shuffle([t for t in range(board) if not blockers[t] and pos[t] > n // 6 and t not in special])
        rest = rng.shuffle([t for t in range(board) if blockers[t] and pos[t] > n // 6 and t not in special])
        cands = top + rest
        used = set()
        for t in cands:
            if len(lock_of) >= locks:
                break
            keys = [k for k in order[:pos[t]] if k not in used and k not in lock_of and k != t and k not in stacked
                    and pos[t] - pos[k] >= 3 and k not in special]
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
        cands = [t for t in range(board) if not flags[t] and t not in special]
        rng.shuffle(cands)
        for t in cands[:ice]:
            flags[t] |= ICE
    pool = list(ICONS[:max(kinds + 4, min(len(ICONS), 8 + kinds))])
    icons = []
    for _ in range(kinds):
        icons.append(pool.pop(rng.below(len(pool)) if lv > 3 else 0))
    solution = []
    for t in order:
        if t not in swept:
            solution += [t, t] if flags[t] & ICE else [t]
    out = dict(lv=lv, v=v, seed=seed, shape=shape, cap=cap or TRAY, w=W, h=H + (3 if stacks else 0), icons=icons,
               tiles=[[x, y, z, kind[i], flags[i]] for i, (x, y, z) in enumerate(places)],
               b=blockers, stacks=stack_rows, board=board, peak=peak, solution=solution)
    if box or chains or bombs:
        _specials(out, lv, seed, box, chains, bombs, special)
    if jokers or box or chains or bombs:
        if not replay(out, solution).won:   # never made unless the intended solution wins by Game's own rules
            raise Gen('verify')
    return out


def _slack(lv: int) -> tuple[int, int]:
    """(⛓️ triples kept spare, 💣 taps of margin) at level lv: a little less room as the levels go on."""
    return (1 if lv <= 260 else 0), (6 if lv <= 250 else 5 if lv <= 275 else 4)


def _trace(level: dict) -> tuple[list, list, list]:
    """The intended solution played with Game: when each tile is first open (taps done before; 0 at the start), the tap
    that takes it off (gone), and the triples cleared before its first tap."""
    g = Game(level)
    n = g.n
    open_at = [0 if g.open(t) else None for t in range(n)]
    gone_at = [None] * n
    clears = [None] * n
    for i, m in enumerate(level['solution'], 1):
        if clears[m] is None:
            clears[m] = g.clears
        g.tap(m)
        for t in range(n):
            if open_at[t] is None and g.open(t):
                open_at[t] = i
            if gone_at[t] is None and g.where[t] == 'g':
                gone_at[t] = i
    return open_at, gone_at, clears


def _specials(out: dict, lv: int, seed: int, box: int, chains: int, bombs: int, special: set) -> None:
    """🎁 ⛓️ 💣 along the intended solution, from their own random stream (the layout and the items stay as they are)."""
    xr = Rng(seed ^ 0x2B7E1516)
    tiles, board = out['tiles'], out['board']
    open_at, gone_at, clears = _trace(out)
    free = lambda t: t < board and not tiles[t][4] and t not in special
    c_slack, b_slack = _slack(lv)
    chain = {}
    if chains:
        # a tile in sight early (tempting) whose tap comes after enough triples
        cands = [t for t in range(board) if free(t) and clears[t] is not None and clears[t] - c_slack >= 2]
        early = xr.shuffle([t for t in cands if open_at[t] == 0])
        late = xr.shuffle([t for t in cands if open_at[t] != 0])
        for t in (early + late)[:chains]:
            chain[t] = min(CHAIN_MAX, clears[t] - c_slack)
            tiles[t][4] |= CHAIN
    if box:
        cands = xr.shuffle([t for t in range(board) if free(t) and open_at[t] and t not in chain])
        cands.sort(key=lambda t: 0 if open_at[t] >= 8 else 1)   # stable: shuffled within each
        for t in cands[:box]:
            tiles[t][4] |= BOX
    fuse = {}
    if bombs:
        span = lambda t: gone_at[t] - open_at[t]
        cands = [t for t in range(board) if free(t) and t not in chain and gone_at[t] and open_at[t] is not None]
        # one that shows up late with its two mates close at hand: a short, readable count
        good = xr.shuffle([t for t in cands if 3 <= span(t) <= 8 and open_at[t] >= 3])
        fair = xr.shuffle([t for t in cands if t not in good and 3 <= span(t) <= 12 and open_at[t] >= 3])
        rest = xr.shuffle([t for t in cands if t not in good and t not in fair and 2 <= span(t) <= 16])
        for t in (good + fair + rest)[:bombs]:
            fuse[t] = max(5, span(t) + b_slack)
            tiles[t][4] |= BOMB
    if chain:
        out['chain'] = [[t, chain[t]] for t in sorted(chain)]
    if fuse:
        out['fuse'] = [[t, fuse[t]] for t in sorted(fuse)]


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
        self.joker = [bool(t[4] & JOKER) for t in lv['tiles']]
        self.items = self.n - sum(self.joker)   # the level is won when they are gone (a 🌈 left over vanishes)
        self.where = ['b'] * self.n          # b board, t tray, h hold, g gone
        self.block = [len(b) for b in lv['b']]
        self.under = [[] for _ in range(self.n)]
        for i, b in enumerate(lv['b']):
            for j in b:
                self.under[j].append(i)
        self.chain = [0] * self.n            # ⛓️ the triples cleared before the tile opens
        for t, c in lv.get('chain', ()):
            self.chain[t] = c
        self.fuse = {t: f for t, f in lv.get('fuse', ())}   # 💣 taps once lit
        self.lit: dict[int, int] = {}        # 💣 lit: taps left
        self.tray: list[int] = []
        self.hold: list[int] = []
        self.cap = lv['cap']
        self.undo_stack: list[tuple] = []
        self.shuffles = 0
        self.slots = 0
        self.gone = 0
        self.done = 0                        # items gone
        self.clears = 0                      # triples cleared (🌈 ones too)
        self.taps = 0
        self.lost = False
        self.boom = None                     # the 💣 that went off
        self.used = dict.fromkeys(BOOSTS, 0)
        self._light()

    @property
    def won(self) -> bool:
        return self.done == self.items

    @property
    def over(self) -> bool:
        return self.lost or self.won

    def open(self, t: int) -> bool:
        return self.where[t] == 'h' or (self.where[t] == 'b' and self.block[t] == 0 and self.chain[t] <= self.clears)

    def _leave_board(self, t):
        for d in self.under[t]:
            self.block[d] -= 1

    def _back_on_board(self, t):
        for d in self.under[t]:
            self.block[d] += 1

    def _clear(self, out: list[int]) -> list[int]:
        for x in out:
            if self.where[x] == 't':
                self.tray.remove(x)
            self.where[x] = 'g'
        self.gone += len(out)
        self.done += sum(1 for x in out if not self.joker[x])
        self.clears += 1
        self.undo_stack = []
        return out

    def _to_tray(self, t):
        k = self.kind[t]
        if self.joker[t]:
            self.tray.append(t)
        else:
            at = None
            for i in range(len(self.tray) - 1, -1, -1):
                if self.kind[self.tray[i]] == k:
                    at = i + 1
                    break
            if at is None:   # a new item: before the 🌈 waiting at the end
                at = next((i for i, x in enumerate(self.tray) if self.joker[x]), len(self.tray))
            self.tray.insert(at, t)
        self.where[t] = 't'
        if not self.joker[t]:
            same = [x for x in self.tray if self.kind[x] == k]
            if len(same) == 3:
                return self._clear(same)
        jk = [x for x in self.tray if self.joker[x]]
        if jk:   # 🌈: the leftmost pair with the leftmost 🌈, and that item's third tile off the board
            for x in self.tray:
                if self.joker[x]:
                    continue
                pair = [y for y in self.tray if self.kind[y] == self.kind[x]]
                if len(pair) == 2:
                    third = [y for y in range(self.n) if self.kind[y] == self.kind[x] and not self.joker[y]
                             and self.where[y] in ('b', 'h')]
                    out = pair + [jk[0]]
                    if third:
                        y = min(third, key=lambda y: (self.lv['tiles'][y][2], y))
                        if self.where[y] == 'b':
                            self._leave_board(y)
                        else:
                            self.hold.remove(y)
                        out.append(y)
                    return self._clear(out)
        if len(self.tray) >= self.cap:
            self.lost = True
        return None

    def _light(self):
        for b, f in self.fuse.items():
            if b not in self.lit and self.where[b] != 'g' and (self.where[b] != 'b' or self.open(b)):
                self.lit[b] = f

    def _tick(self):
        """💣 After a tap: every lit bomb still there loses one; at 0 the attempt is lost. Then newly open ones light."""
        if not self.fuse:
            return
        for b in self.lit:
            if self.where[b] != 'g':
                self.lit[b] -= 1
                if self.lit[b] <= 0 and not self.lost:
                    self.lost = True
                    self.boom = b
        self._light()

    def tap(self, t: int):
        if self.over or type(t) is not int or not 0 <= t < self.n or not self.open(t):
            raise Bad('tap')
        self.taps += 1
        if self.where[t] == 'b' and self.ice[t]:
            self.ice[t] -= 1
            self._tick()
            return 'ice'
        if self.where[t] == 'h':
            i = self.hold.index(t)
            self.hold.pop(i)
            self.undo_stack.append((t, i))
        else:
            self._leave_board(t)
            self.undo_stack.append((t, None))
        out = self._to_tray(t) or 'tray'
        if not self.won:
            self._tick()
        return out

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
        ids = [t for t in range(self.n) if self.where[t] == 'b' and not self.joker[t]]   # a 🌈 stays a 🌈
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

    @property
    def boosters(self) -> int:
        return sum(self.used.values())


def stars(boosters: int) -> int:
    """⭐ a won attempt: 3 with no booster, 2 with one or two, else 1 (the page shows the same)."""
    return 3 if boosters <= 0 else 2 if boosters <= 2 else 1


def replay(lv: dict, moves) -> Game:
    """The attempt after `moves` (raises Bad on an impossible move)."""
    if not isinstance(moves, list) or len(moves) > MOVES_MAX:
        raise Bad('moves')
    g = Game(lv)
    for m in moves:
        g.move(m)
    return g


# ---------------------------------------------------------------- the solver (an independent check)
def solve(lv: dict, cap: int | None = None, limit: int = 400_000) -> list[int] | None:
    """A sequence of taps that clears the level without boosters, or None (not found within `limit` nodes).
    The tray's content only depends on which tiles were taken (each kind's count mod 3), so the search
    remembers dead sets of taken tiles. Levels with 🌈 ⛓️ 💣 take `_solve_x` (its own search of the same rules)."""
    cap = lv.get('cap', TRAY) if cap is None else cap
    if lv.get('chain') or lv.get('fuse') or any(t[4] & JOKER for t in lv['tiles']):
        return _solve_x(lv, cap, limit)
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


def _solve_x(lv: dict, cap: int, limit: int) -> list[int] | None:
    """`solve` for levels 201–300, written apart from Game (an independent check of the generator): a depth-first
    search over taps (an ice tile is cracked and taken in two taps in a row) with the 🌈, ⛓️ and 💣 rules of the
    module doc. A dead state is remembered by the tiles taken, the tray's kinds in order and the lit fuses."""
    tiles = lv['tiles']
    n = len(tiles)
    kind = [t[3] for t in tiles]
    z = [t[2] for t in tiles]
    joker = [bool(t[4] & JOKER) for t in tiles]
    ice = [bool(t[4] & ICE) for t in tiles]
    chain = [0] * n
    for t, c in lv.get('chain', ()):
        chain[t] = c
    fuse = {t: f for t, f in lv.get('fuse', ())}
    block = [len(b) for b in lv['b']]
    under = [[] for _ in range(n)]
    for i, b in enumerate(lv['b']):
        for j in b:
            under[j].append(i)
    items = n - sum(joker)
    rank = {t: r for r, t in enumerate(sorted(range(n), key=lambda t: (z[t], t)))}
    by_kind = {}
    for t in sorted(range(n), key=lambda t: rank[t]):
        if not joker[t]:
            by_kind.setdefault(kind[t], []).append(t)
    st = dict(mask=0, done=0, tray=[], lit={})
    dead = {}
    path = []
    nodes = [0]

    def taken(t):
        return (st['mask'] >> t) & 1

    def can(t):
        return not taken(t) and block[t] == 0 and chain[t] <= st['done'] // 3

    def off(t, gone):
        st['mask'] |= 1 << t
        gone.append(t)
        for d in under[t]:
            block[d] -= 1

    def tick():
        tray = st['tray']
        for b in st['lit']:
            if not taken(b) or b in tray:
                st['lit'][b] -= 1
                if st['lit'][b] <= 0:
                    return False
        for b, f in fuse.items():
            if b not in st['lit'] and (b in tray or can(b)):
                st['lit'][b] = f
        return True

    def take(t, gone) -> bool:
        if ice[t] and not tick():
            return False
        off(t, gone)
        tray = st['tray']
        if joker[t]:
            tray.append(t)
        else:
            at = next((i + 1 for i in range(len(tray) - 1, -1, -1) if kind[tray[i]] == kind[t]), None)
            if at is None:
                at = next((i for i, x in enumerate(tray) if joker[x]), len(tray))
            tray.insert(at, t)
        cleared = False
        if not joker[t] and sum(1 for x in tray if kind[x] == kind[t]) == 3:
            st['tray'] = [x for x in tray if kind[x] != kind[t]]
            st['done'] += 3
            cleared = True
        elif any(joker[x] for x in tray):
            for x in tray:
                if not joker[x] and sum(1 for y in tray if kind[y] == kind[x]) == 2:
                    k = kind[x]
                    j = next(y for y in tray if joker[y])
                    st['tray'] = [y for y in tray if kind[y] != k and y != j]
                    third = next((y for y in by_kind[k] if not taken(y)), None)
                    if third is not None:
                        off(third, gone)
                    st['done'] += 3
                    cleared = True
                    break
        if not cleared and len(st['tray']) >= cap:
            return False
        if st['done'] == items:
            return True
        return tick()

    def rec() -> bool:
        if st['done'] == items:
            return True
        nodes[0] += 1
        if nodes[0] > limit:
            return False
        # the same tiles taken lights the same bombs: a state with no more taps left on any of them than a dead one is dead
        live = sorted((b, v) for b, v in st['lit'].items() if not taken(b) or b in st['tray'])
        key = (st['mask'], tuple(kind[x] for x in st['tray']), tuple(b for b, _ in live))
        val = tuple(v for _, v in live)
        if any(all(a <= b for a, b in zip(val, d)) for d in dead.get(key, ())):
            return False
        tray = st['tray']
        cnt = {}
        for x in tray:
            cnt[kind[x]] = cnt.get(kind[x], 0) + 1
        pair = any(v == 2 for k, v in cnt.items() if k >= 0)
        waiting = cnt.get(-1, 0) > 0
        hot = set()
        for b in st['lit']:
            if not taken(b) or b in tray:
                c = cnt.get(kind[b], 0)
                if max(1, 3 - c - (1 if waiting and c else 0)) > st['lit'][b]:   # too few taps left to clear it
                    dead.setdefault(key, []).append(val)
                    return False
                hot.add(kind[b])
        dig = set()   # the tiles right over a lit bomb's item: dig them out first
        for k in hot:
            for x in by_kind[k]:
                if not taken(x):
                    dig.update(y for y in lv['b'][x] if not taken(y))
        hot_pair = any(v == 2 and k in hot for k, v in cnt.items())
        opens = [t for t in range(n) if can(t)]

        def order(t):
            if joker[t]:
                c = 3 if pair else -1
                p = 2 if hot_pair else 0
            else:
                c = cnt.get(kind[t], 0) + (waiting and cnt.get(kind[t], 0) == 1)
                p = 2 if kind[t] in hot else 1 if t in dig else 0
            return (-p, -c, -len(under[t]), -z[t], t)
        opens.sort(key=order)
        for t in opens:
            snap = (st['mask'], st['done'], list(tray), dict(st['lit']))
            gone = []
            ok = take(t, gone)
            if ok:
                path.append(t)
                if rec():
                    return True
                path.pop()
            st['mask'], st['done'], st['tray'], st['lit'] = snap[0], snap[1], snap[2], snap[3]
            tray = st['tray']
            for x in gone:
                for d in under[x]:
                    block[d] += 1
            if nodes[0] > limit:
                return False
        dead.setdefault(key, []).append(val)
        return False

    for b, f in fuse.items():
        if can(b):
            st['lit'][b] = f
    import sys
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, n + 200))
    try:
        ok = rec()
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
            hot = {g.kind[b] for b in g.lit if g.where[b] != 'g'}   # 💣 lit: its item first (levels 201–300)
            pair = any(v == 2 for k, v in cnt.items() if k >= 0)

            def score(t):
                if g.joker[t]:   # 🌈 with a pair waiting, else last
                    return (40 if pair else 0) + rng.below(6)
                c = cnt.get(g.kind[t], 0)
                seen = sum(1 for o in opens if g.kind[o] == g.kind[t])
                return (3 if c == 2 else 2 if c == 1 else 1 if c + seen >= 3 else 0) * 10 + min(9, len(g.under[t])) + rng.below(6) \
                    + (15 if g.kind[t] in hot else 0)
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


def _hi(s: dict, key: str = KEY_HI) -> int:
    h = (s.get('journey') or {}).get(key)
    lv = h.get('lv') if isinstance(h, dict) else 0
    return lv if type(lv) is int and 0 <= lv <= HI_MAX - BASE_MAX else 0


def cleared(s: dict) -> int:
    t = get(s)
    lv = t.get('lv') if t else 0
    lv = lv if type(lv) is int and 0 <= lv <= BASE_MAX else 0
    if lv < BASE_MAX:
        return lv
    hi = _hi(s)
    return BASE_MAX + hi + (_hi(s, KEY_HI2) if hi == HI_MAX - BASE_MAX else 0)


def _set_cleared(s: dict, t: dict, lv: int) -> None:
    if lv <= BASE_MAX:
        t['lv'] = lv
    elif lv <= HI_MAX:
        s['journey'][KEY_HI] = dict(lv=lv - BASE_MAX)
    else:
        h2 = s['journey'].get(KEY_HI2)
        h2 = s['journey'][KEY_HI2] = h2 if isinstance(h2, dict) else {}
        h2['lv'] = lv - HI_MAX


def chest(lv: int) -> dict:
    """🎁 The chest of level lv's first clear (210, 220 … 300; double on 250 and 300), else {}."""
    if lv <= HI_MAX or lv % CHEST_EVERY:
        return {}
    m = 2 if lv % 50 == 0 else 1
    return {k: v * m for k, v in CHEST.items()}


def chest_left(s: dict) -> dict:
    h2 = (s.get('journey') or {}).get(KEY_HI2)
    b = h2.get('b') if isinstance(h2, dict) else None
    return {k: int(v) for k, v in b.items() if k in BOOSTS and type(v) is int and v > 0} if isinstance(b, dict) else {}


def _chest_add(s: dict, gift: dict) -> None:
    h2 = s['journey'][KEY_HI2]
    b = h2.setdefault('b', {})
    for k, v in gift.items():
        b[k] = min(CHEST_CAP, b.get(k, 0) + v)


def _chest_spend(s: dict, kind: str, n: int) -> None:
    if n <= 0:
        return
    b = s['journey'][KEY_HI2]['b']
    left = b[kind] - n
    _core().need(left >= 0, 'Trợ giúp không đủ.', 'tile_paid')
    if left:
        b[kind] = left
    else:
        del b[kind]
    if not b:
        del s['journey'][KEY_HI2]['b']


def star_text(s: dict) -> str:
    v = (s.get('journey') or {}).get(KEY_STAR)
    return v if isinstance(v, str) and len(v) <= LEVEL_MAX and set(v) <= set('0123') else ''


def _star_set(s: dict, lv: int, n: int) -> bool:
    """⭐ Keeps the best stars of level lv; True when it is better than before."""
    st = star_text(s)
    if len(st) >= lv and int(st[lv - 1]) >= n:
        return False
    st = st.ljust(lv, '0')
    s['journey'][KEY_STAR] = st[:lv - 1] + str(n) + st[lv:]
    return True


def permille(s: dict) -> int:
    """The buff in ‰ of what is earned: 2 a cleared level to 100 (20 %), then 1 a level (30 % at 200)."""
    c = cleared(s)
    return min(BASE_MAX, c) * PERMILLE_PER_LEVEL + max(0, c - BASE_MAX) * PERMILLE_PER_HI


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


def _free_all(s: dict, t: dict | None) -> dict:
    """Today's free uses plus the 🎁 chests' (tile_hi2.b) and the 📺 boosters an ad gave (game/ads.py, kept until used)."""
    from . import ads
    tb = ads.tile_credits(s)
    cb = chest_left(s)
    return {k: v + cb.get(k, 0) + tb.get(k, 0) for k, v in free_left(t).items()}


def price(kind: str, paid: int) -> int:
    return PRICE[kind] * (2 ** paid)


def public(s: dict) -> dict:
    """journey.tile for the page (also when the save has none yet)."""
    t = get(s)
    fresh = not t or t.get('d') != today()
    cur = (t or {}).get('cur') if t else None
    pm = permille(s)
    out = dict(lv=cleared(s), max=HI_MAX, last=LEVEL_MAX, pm=pm, pct=pct_text(pm), n=0 if fresh else int(t.get('n', 0)), cap=CAP_DAY, capped=DAILY_CAP, day=today(),
               free=_free_all(s, t), price=dict(PRICE), slot_max=SLOT_MAX)
    if isinstance(cur, dict):
        out['cur'] = dict(lv=cur['lv'], b=dict(cur.get('b') or {}), p=dict(cur.get('p') or {}))
        out['at'] = cur['t']   # the clock: a first clear is counted from need_ms(taps) after it (server ms)
    out['min'] = dict(level=MIN_LEVEL_MS, tap=MIN_TAP_MS)
    if st := star_text(s):
        out['st'] = st   # ⭐ the best stars a level
    if cb := chest_left(s):
        out['chest'] = cb   # 🎁 chest uses left (in `free` too)
    return out


def _ms() -> int:
    return int(_now() * 1000)


def _clock(t: dict, now: int) -> int:
    """The save's clock: the previous accepted first clear (or an older page's first start); `now` if it has none."""
    cur = t.get('cur')
    return cur['t'] if isinstance(cur, dict) and type(cur.get('t')) is int else now


def _rest(t: dict, clock: int) -> None:
    """cur between attempts: the next level and the clock, no booster of an older page's attempt (2.4.5's shape). Its lv
    stays within 100 (older builds' bound; only an older page, at most level 100, reads it)."""
    t['cur'] = dict(lv=min(BASE_MAX, t['lv'] + 1), t=clock, b={}, p={})


def need_ms(taps: int) -> int:
    """The least server time a first clear of `taps` taps takes since the clock."""
    return max(MIN_LEVEL_MS, MIN_TAP_MS * taps)


def _end(s: dict, p: dict, e) -> dict:
    """A finished level, self-described: {n, moves, ms?} (or an older page's {lv, moves}). See the module doc."""
    need = e.need
    new = 'n' in p
    need(({'n', 'moves'} <= set(p) <= {'n', 'moves', 'ms', 'v'}) if new else set(p) == {'lv', 'moves'}, 'Thao tác không hợp lệ.')
    need(type(p.get('v', TABLE)) is int and p.get('v', TABLE) in TABLES, 'Màn chơi không hợp lệ.', 'tile_level')
    lv = p['n'] if new else p['lv']
    need(type(lv) is int and 1 <= lv <= LEVEL_MAX, 'Màn chơi không hợp lệ.', 'tile_level')
    need(lv <= len(table(p.get('v', TABLE))), 'Màn chơi không hợp lệ.', 'tile_level')   # table 1 has 100 levels, 2 has 200
    moves = p['moves']
    need(isinstance(moves, list) and len(moves) <= MOVES_MAX and all(type(m) is int for m in moves), 'Ván chơi không hợp lệ.', 'tile_invalid')
    t = _ensure(s)
    top = cleared(s)
    need(lv <= top + 1, f'Qua màn {top + 1} trước đã nhé.', 'tile_locked')
    # The table the page played: its own `v`; a 2.4.5–2.4.6 page (no `v`) may hold a level of either table.
    g = None
    for v in ((p.get('v', TABLE),) if new else (TABLE, 1) if lv <= BASE_MAX else (TABLE,)):
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
    daily = free_left(t)
    free, cost = _free_all(s, t), 0
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
    first = lv == top + 1
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
    from . import ads
    chests = chest_left(s)
    for k, v in uses.items():
        if v:
            own = min(v, daily[k])   # the day's own free uses first, then the 🎁 chests', then the 📺 ones
            if own:
                t['u'][k] = t['u'].get(k, 0) + own
            box = min(v - own, chests.get(k, 0))
            _chest_spend(s, k, box)
            ads.spend_tile(s, k, v - own - box)
    gift = {}
    if first:
        _set_cleared(s, t, lv)
        t['n'] = min(CAP_DAY, t['n'] + 1)   # counted for show only; stays within older builds' bound
        gift = chest(lv)
        if gift:
            _chest_add(s, gift)
    star = stars(g.boosters)
    best = _star_set(s, lv, star)
    _rest(t, now if first or cur is None else cur['t'])
    pm = permille(s)
    msg = f'🎉 Qua màn {lv}!' + (f' {PREFIX} +{pct_text(pm)}%.' if first else '')
    return dict(message=msg, win=True, first=first, lv=lv, taps=g.taps, cost=cost, stars=star, best=best,
                **({'chest': gift} if gift else {}),
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
        need(type(lv) is int and 1 <= lv <= BASE_MAX, 'Màn chơi không hợp lệ.', 'tile_level')   # older pages stop at 100
        t = _ensure(s)
        top = cleared(s)
        need(lv <= top + 1, f'Qua màn {top + 1} trước đã nhé.', 'tile_locked')
        if lv == top + 1:
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
    for key in (KEY_HI, KEY_HI2, KEY_STAR):
        if isinstance((old.get('journey') or {}).get(key), (dict, str)):
            fresh['journey'][key] = copy.deepcopy(old['journey'][key])
    if isinstance(t, dict):
        fresh['journey'][KEY] = keep = {k: copy.deepcopy(v) for k, v in t.items() if k != 'cur'}
        if isinstance(t.get('cur'), dict):   # the clock stays (a reset is no way round the time a level takes)
            _rest(keep, t['cur']['t'])


def validate(s: dict) -> None:
    e = _core()
    t = (s.get('journey') or {}).get(KEY)
    h = (s.get('journey') or {}).get(KEY_HI)
    need, integer = e.need, e.integer
    msg = 'Ghép ba trong bản lưu không hợp lệ.'
    if h is not None:
        need(isinstance(h, dict) and set(h) == {'lv'} and isinstance(t, dict) and t.get('lv') == BASE_MAX, msg)
        integer(h['lv'], 0, HI_MAX - BASE_MAX)
    h2 = (s.get('journey') or {}).get(KEY_HI2)
    if h2 is not None:   # levels 201–300: only beside tile_hi.lv == 100
        need(isinstance(h2, dict) and 'lv' in h2 and set(h2) <= {'lv', 'b'} and isinstance(h, dict) and h.get('lv') == HI_MAX - BASE_MAX, msg)
        integer(h2['lv'], 0, LEVEL_MAX - HI_MAX)
        if 'b' in h2:
            need(isinstance(h2['b'], dict) and h2['b'] and set(h2['b']) <= set(BOOSTS), msg)
            for v in h2['b'].values():
                integer(v, 1, CHEST_CAP)
    st = (s.get('journey') or {}).get(KEY_STAR)
    if st is not None:
        need(isinstance(st, str) and 0 < len(st) <= LEVEL_MAX and set(st) <= set('0123'), msg)
    if t is None:
        return
    need(isinstance(t, dict) and {'lv', 'd', 'n', 'u'} <= set(t) <= {'lv', 'd', 'n', 'u', 'cur'}, msg)
    integer(t['lv'], 0, BASE_MAX)
    need(isinstance(t['d'], str) and len(t['d']) == 10, msg)
    integer(t['n'], 0, CAP_DAY)
    need(isinstance(t['u'], dict) and set(t['u']) <= set(BOOSTS), msg)
    for k, v in t['u'].items():
        integer(v, 0, FREE[k])
    cur = t.get('cur')
    if cur is not None:
        need(isinstance(cur, dict) and set(cur) == {'lv', 't', 'b', 'p'}, msg)
        integer(cur['lv'], 1, min(BASE_MAX, t['lv'] + 1))
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
    whole: opening balance + rows == fund). `direct`: the staff orders' way (no journal line, like their rows).
    🐾 Your own work (not `direct`) also gets the walking pet's share (game/pet_tiers.py): its own row, in the total."""
    pet = 0
    if not direct and isinstance(s.get('journey'), dict) and s['journey'].get('story'):
        from . import pet_tiers
        pet = pet_tiers.fund_bonus(s, c, base, what, ref)
        from . import pay_boost   # 💰 Tiền công +% (raise, 🎉 Tuần lễ tay nghề, 🧰 Bộ đồ nghề): its own row, in the total
        pet += pay_boost.on_earning(s, c, base, what, ref)
        from . import wings   # 🪽 the worn wing's +% (game/wings.py): its own row, in the total, on the same base
        pet += wings.fund_bonus(s, c, base, what, ref)
    bonus = extra(s, base, f'{ref}|{what}|{c.get("day")}')
    if not bonus:
        return pet
    if direct:
        from . import operations as ops
        c['money'] += bonus
        c['earnings'] += bonus
        why = label(s, what)
        ops.record_money(c, bonus, why, ref, 'other_income', group=why)  # the staff orders' rows: one a day
    else:
        _core().money(s, c, bonus, label(s, what), ref, category='other_income')
    return bonus + pet


def day_total(c: dict, day: int) -> int:
    """The buff rows of a workplace's day (kept out of the 🔥 x3 day's net: it never multiplies twice), the 🐾 pet's and
    the 🪽 wing's too."""
    from .pet_tiers import PREFIX as PET
    from .wings import PREFIX as WING
    rows = c.get('ops', {}).get('finance', {}).get('ledger', [])
    return sum(r['amount'] for r in rows if r.get('day') == day and r.get('amount', 0) > 0
               and r.get('category') == 'other_income' and str(r.get('reason', '')).startswith((PREFIX, PET, WING)))
