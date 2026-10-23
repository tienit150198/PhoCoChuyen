"""🏝️ Thiết kế đảo (story mode; catalogue: game/island_design_content.py): every private island on a free grid, bigger,
growing out into the sea (🌊 lấn biển), with decorations placed anywhere and the buildings (game/island_build.py) moved
and turned at will. Owner 24/10: "đảo to và xây được hồ bơi, nhà,... cây này kia đặt cho đẹp hơn".

Like the buildings, nothing here ever pays xu: a decoration and a lấn biển are paid once (the wallet first, then the
bank account, never a loan, never with a wallet in debt: game/lux.py ready_why), they give a place (spots to sit, lie,
swim or stand at: a pose only) and the 🏝️ Đảo đẹp board's points (a title only: game/island_lb.py). Moving, turning
and putting a decoration back into the kho is free; the kho keeps what was bought for any island.

* The grid (C.G × C.G cells of C.CELL map units from C.X0) covers each island's map and past it; a cell is land when
  its middle is inside the island's coast at its size tier (shore(): the old coast grown by C.TIERS[tier]); what the
  island already has (C.FIXED: the villa, the pier, the pad, the spots, the palms…) covers its cells. Every island
  stands at tier 0 at least: its old coast grown 15 %, nothing on land moved, its plots' buildings where they were
  (an old plot's building stands on the C.BUILD_FOOT² cells around the plot's middle: default_pos()), the marina plot
  and the sea features moved out with the coast.
* jr_isle_place {island, kind, x, y, r, confirm}: a decoration on the cells x..x+w, y..y+h (w and h swapped when r is
  odd): from the kho when there is one (free, no confirm), else bought (confirm: True).
  jr_isle_dmove {island, id, x, y, r}: moved and / or turned. jr_isle_store {island, id}: back into the kho.
  jr_isle_bmove {island, plot, x, y, r}: a building moved (r: house styles only, game/island_build_content.py HOUSES).
  jr_isle_expand {island, confirm}: 🌊 the next size tier, C.EXPAND_PCT % of the island's list price; a decoration the
  sea features now cover, or a sea one now on land, goes back into the kho (never lost); a building in the way refuses.
  jr_isle_opt {island, paths}: 🛤️ the footpaths drawn from the pier to every door (a look, no cells).
  jr_isle_build (game/island_build.py) takes {x, y, r} instead of a plot: it stands there (place_building()).
* Placement rules (fits()): inside the grid, on land (C.DECOR `where`: coast touches the beach, pier has some cells on
  land and some on the sea, sea all on the sea, any), never on what the island already has, never on another thing.
* Selling the island (game/island.py _sell → on_sell()): its decorations go into the kho, its tier stays with the save
  (bought back, the island comes back at its size), the buildings are razed as before (game/island_build.py).

The save is the truth; PostgreSQL holds a copy visitors, the open-island list and the board read (table island_layout,
one row per owner and island, status 'up' | 'gone'; game/pg_schema.py SCHEMA_VERSION 92), written by command_commit
(game/island_build.py) in the save's transaction for every command that may change it.

State `s['journey']['isld']` (absent until the first change; journey.validate allows extra keys, so an older build keeps
it untouched: tests/test_island_design.py proves it on the release before this one):
    v    VERSION
    i    {island id: {t: tier, d: {id: [kind, x, y, r]}, b: {plot: [x, y, r]}, n: last id, ap: 0 | 1}}
         A kind this build does not know is kept by shape (never shown, never counted); an island sold keeps its tier.
    inv  {kind: how many in the kho}
    st   {xu: paid for decorations, exp: paid for lấn biển, placed, stored}
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache

from . import bank as bk
from . import island as isl
from . import island_build_content as BC
from . import island_design_content as C

VERSION = 1
KEY = 'isld'
COMMANDS = ('jr_isle_place', 'jr_isle_dmove', 'jr_isle_store', 'jr_isle_bmove', 'jr_isle_expand', 'jr_isle_opt')
DECOR = {d['id']: d for d in C.DECOR}
BLOCK_KEYS = frozenset({'v', 'i', 'inv', 'st'})
ISLE_KEYS = frozenset({'t', 'd', 'b', 'n', 'ap'})
STATS = ('xu', 'exp', 'placed', 'stored')
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
TIER_MAX = 9                     # by shape: a newer build may add tiers
ITEMS_SHAPE = 1000               # by shape: a newer build may allow more
ID_MAX = 10**6
GRID_SHAPE = 255
BIG = 10**12
TAU = math.pi * 2
LOOK_OF = {i['id']: i['look'] for i in isl.C.ISLANDS}


def _core():
    from . import engine
    return engine


def _ib():
    from . import island_build
    return island_build


def _fmt(n: int) -> str:
    return bk._fmt(n)


def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


def _id(v) -> bool:
    return isinstance(v, str) and ID_RE.fullmatch(v) is not None


def jround(v: float) -> int:
    """JavaScript's Math.round (half up), so both sides put a thing on the same cell."""
    return math.floor(v + .5)


# ---------------------------------------------------------------- the shape of each island
def blob(cx, cy, rx, ry, bumps, steps=48) -> tuple:
    """public/js/island-layout.js blob(): an ellipse whose radius wobbles by `bumps`, smoothed, 4 decimals."""
    n, out = len(bumps), []
    for i in range(steps):
        a = i / steps * TAU
        f = a / TAU * n
        k = math.floor(f)
        t = f - k
        b0, b1 = bumps[k % n], bumps[(k + 1) % n]
        w = b0 + (b1 - b0) * (1 - math.cos(t * math.pi)) / 2
        out.append((float(f'{cx + math.cos(a) * rx * w:.4f}'), float(f'{cy + math.sin(a) * ry * w:.4f}')))
    return tuple(out)


def tier_scale(t: int) -> float:
    return C.TIERS[max(0, min(len(C.TIERS) - 1, t))]


def tiers_max() -> int:
    return len(C.TIERS) - 1


@lru_cache(maxsize=64)
def shore(look: str, t: int) -> tuple:
    cx, cy, rx, ry, bumps, _ = C.SHAPES.get(look, C.SHAPES['dua'])
    s = tier_scale(t)
    return blob(cx, cy, rx * s, ry * s, bumps)


def in_poly(pts, x: float, y: float) -> bool:
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        ax, ay = pts[i]
        bx, by = pts[j]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
        j = i
    return inside


def shift(look: str, t: int, x: float, y: float) -> tuple:
    """How far the coast moved out at (x, y)'s bearing from the island's middle, tier 0.. against the old coast: what lies
    on the water moves with it (public/js/island-layout.js coastShift)."""
    cx, cy, rx, ry, bumps, _ = C.SHAPES.get(look, C.SHAPES['dua'])
    a = math.atan2((y - cy) / ry, (x - cx) / rx)
    if a < 0:
        a += TAU
    n = len(bumps)
    f = a / TAU * n
    k = math.floor(f)
    u = f - k
    b0, b1 = bumps[k % n], bumps[(k + 1) % n]
    w = b0 + (b1 - b0) * (1 - math.cos(u * math.pi)) / 2
    s = tier_scale(t) - 1
    return (s * math.cos(a) * rx * w, s * math.sin(a) * ry * w)


def cell_x(i: int) -> float:
    return C.X0 + (i + .5) * C.CELL


def _span(lo: float, hi: float) -> range:
    a = max(0, math.floor((lo - C.X0) / C.CELL + 1e-9))
    b = min(C.G, math.ceil((hi - C.X0) / C.CELL - 1e-9))
    return range(a, b)


def fixed_rects(look: str, t: int) -> list:
    """What the island already has at tier t: [(x, y, w, h)], the sea ones moved out with the coast."""
    out = []
    for x, y, w, h, sea in C.FIXED.get(look, ()):
        if sea:
            dx, dy = shift(look, t, x, y)
            x, y = x + dx, y + dy
        out.append((x, y, w, h))
    return out


@lru_cache(maxsize=64)
def cells(look: str, t: int) -> tuple:
    """(land, coast, fixed) of an island at tier t: two bytes of C.G² (1: yes) and the frozenset of cells its own
    features cover (index j * G + i)."""
    pts = shore(look, t)
    g = C.G
    land = bytearray(g * g)
    for j in range(g):
        y = cell_x(j)
        for i in range(g):
            if in_poly(pts, cell_x(i), y):
                land[j * g + i] = 1
    coast = bytearray(g * g)
    for j in range(g):
        for i in range(g):
            if not land[j * g + i]:
                continue
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    a, b = i + di, j + dj
                    if not (0 <= a < g and 0 <= b < g) or not land[b * g + a]:
                        coast[j * g + i] = 1
    fixed = set()
    for x, y, w, h in fixed_rects(look, t):
        for j in _span(y - h / 2, y + h / 2):
            for i in _span(x - w / 2, x + w / 2):
                fixed.add(j * g + i)
    return bytes(land), bytes(coast), frozenset(fixed)


# ---------------------------------------------------------------- footprints
def foot_of(kind: str) -> tuple | None:
    """(w, h, where) of a decoration or a building kind; None: a kind this build does not know."""
    d = DECOR.get(kind)
    if d:
        return d['w'], d['h'], d['where']
    it = _ib().known(kind)
    if it:
        return C.BUILD_FOOT, C.BUILD_FOOT, 'coast' if it.get('coast') else 'land'
    return None


def rotatable(kind: str) -> bool:
    d = DECOR.get(kind)
    if d:
        return d['rot']
    it = _ib().known(kind)
    return bool(it and it.get('looks'))   # 🏡 the house styles (public/js/house-art.js) turn; the first eight do not


def footprint(w: int, h: int, x: int, y: int, r: int) -> list:
    if r % 2:
        w, h = h, w
    return [(y + b) * C.G + (x + a) for b in range(h) for a in range(w)]


@lru_cache(maxsize=1024)
def default_pos(iid: str, plot: int, t: int) -> tuple | None:
    """Where an old plot's building stands when it was never moved: the cells around the plot's middle; a marina plot
    (by the sea) moved out with the coast, then nudged to the nearest place on land touching the beach, clear of the
    island's own features. None: a plot this build has no place for (a building placed by a newer build). The server
    sends every building's place (view(), with_places()): the clients never work this out."""
    spots = BC.PLOTS.get(iid, ())
    if not 0 <= plot < len(spots):
        return None
    x, y, coast = spots[plot]
    look = LOOK_OF.get(iid, 'dua')
    if coast:
        dx, dy = shift(look, t, x, y)
        x, y = x + dx, y + dy
    f = C.BUILD_FOOT
    half = f / 2
    gx = max(0, min(C.G - f, jround((x - C.X0) / C.CELL - half)))
    gy = max(0, min(C.G - f, jround((y - C.X0) / C.CELL - half)))
    if coast:
        land, sea_edge, fixed = cells(look, t)

        def ok(i, j):
            cs = footprint(f, f, i, j, 0)
            return all(land[c] for c in cs) and any(sea_edge[c] for c in cs) and not any(c in fixed for c in cs)
        if not ok(gx, gy):
            near = sorted(((a * a + b * b, b, a) for a in range(-4, 5) for b in range(-4, 5) if a or b))
            for _, b, a in near:
                i, j = gx + a, gy + b
                if 0 <= i <= C.G - f and 0 <= j <= C.G - f and ok(i, j):
                    return i, j, 0
    return gx, gy, 0


# ---------------------------------------------------------------- the block
def initial() -> dict:
    return dict(v=VERSION, i={}, inv={}, st={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial()
    return j[KEY]


def _isle_new() -> dict:
    return dict(t=0, d={}, b={}, n=0, ap=0)


def _isle(s: dict, iid: str) -> dict:
    b = _ensure(s)
    if iid not in b['i']:
        b['i'][iid] = _isle_new()
    return b['i'][iid]


def isle_of(s: dict, iid: str) -> dict:
    """The island's design as it is (a fresh one when nothing was ever changed): never written."""
    b = get(s)
    d = b['i'].get(iid) if b else None
    return d if isinstance(d, dict) else _isle_new()


def _pos_ok(v) -> bool:
    return isinstance(v, list) and len(v) == 3 and _int(v[0], 0, GRID_SHAPE) and _int(v[1], 0, GRID_SHAPE) and _int(v[2], 0, 3)


def _item_ok(v) -> bool:
    return (isinstance(v, list) and len(v) == 4 and _id(v[0]) and _int(v[1], 0, GRID_SHAPE) and _int(v[2], 0, GRID_SHAPE)
            and _int(v[3], 0, 3))


def _isle_ok(d) -> bool:
    return (isinstance(d, dict) and set(d) == ISLE_KEYS and _int(d['t'], 0, TIER_MAX) and _int(d['n'], 0, ID_MAX)
            and _int(d['ap'], 0, 1)
            and isinstance(d['d'], dict) and len(d['d']) <= ITEMS_SHAPE
            and all(isinstance(k, str) and k.isdigit() and len(k) <= 7 and _item_ok(v) for k, v in d['d'].items())
            and isinstance(d['b'], dict) and len(d['b']) <= _ib().PLOTS_MAX
            and all(isinstance(k, str) and k.isdigit() and len(k) <= 2 and _pos_ok(v) for k, v in d['b'].items()))


def validate(s: dict) -> None:
    """``s['journey']['isld']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    j = s.get('journey')
    b = get(s)
    bad = 'Dữ liệu thiết kế đảo trong bản lưu không hợp lệ.'
    if b is None:
        e.need(not isinstance(j, dict) or j.get(KEY) is None, bad, 'invalid_save')
        return
    st, inv = b.get('st'), b.get('inv')
    e.need(set(b) == BLOCK_KEYS and b['v'] == VERSION and isinstance(b['i'], dict) and len(b['i']) <= isl.OWN_MAX
           and all(_id(k) and _isle_ok(v) for k, v in b['i'].items())
           and isinstance(inv, dict) and len(inv) <= 500 and all(_id(k) and _int(v, 1, 10**6) for k, v in inv.items())
           and isinstance(st, dict) and set(st) <= set(STATS) and all(_int(v) for v in st.values()), bad, 'invalid_save')


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep what still makes sense."""
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    if not isinstance(b, dict):
        j[KEY] = initial()
        return
    out = initial()
    for iid, d in list((b.get('i') if isinstance(b.get('i'), dict) else {}).items())[:isl.OWN_MAX]:
        if not (_id(iid) and isinstance(d, dict)):
            continue
        x = _isle_new()
        x['t'] = d['t'] if _int(d.get('t'), 0, TIER_MAX) else 0
        x['n'] = d['n'] if _int(d.get('n'), 0, ID_MAX) else 0
        x['ap'] = d['ap'] if _int(d.get('ap'), 0, 1) else 0
        items = d.get('d') if isinstance(d.get('d'), dict) else {}
        x['d'] = {k: list(v) for k, v in list(items.items())[:ITEMS_SHAPE]
                  if isinstance(k, str) and k.isdigit() and len(k) <= 7 and _item_ok(v)}
        if x['d']:
            x['n'] = max(x['n'], max(int(k) for k in x['d']))
        pos = d.get('b') if isinstance(d.get('b'), dict) else {}
        x['b'] = {k: list(v) for k, v in list(pos.items())[:64] if isinstance(k, str) and k.isdigit() and len(k) <= 2 and _pos_ok(v)}
        out['i'][iid] = x
    inv = b.get('inv') if isinstance(b.get('inv'), dict) else {}
    out['inv'] = {k: v for k, v in list(inv.items())[:500] if _id(k) and _int(v, 1, 10**6)}
    st = b.get('st') if isinstance(b.get('st'), dict) else {}
    out['st'] = {k: st[k] if _int(st.get(k)) else 0 for k in STATS}
    if out != b:
        j[KEY] = out


# ---------------------------------------------------------------- the island's cells now
def _buildings(s: dict, iid: str) -> dict:
    """{plot: entry} of journey.islb on this island (kinds this build knows)."""
    p = _ib()._plots(s, iid)
    return {int(k): e for k, e in p.items() if _ib().known(e['k'])}


def building_pos(d: dict, iid: str, plot: int) -> tuple | None:
    v = d['b'].get(str(plot))
    return tuple(v) if v else default_pos(iid, plot, d['t'])


def occupied(s: dict, iid: str, d: dict | None = None, skip: str = '') -> dict:
    """{cell: who} of what stands on the island: 'b<plot>' a building, 'd<id>' a decoration; `skip`: leave one out."""
    d = d or isle_of(s, iid)
    out = {}
    for plot, e in _buildings(s, iid).items():
        tag = f'b{plot}'
        pos = building_pos(d, iid, plot)
        if tag == skip or not pos:
            continue
        for c in footprint(C.BUILD_FOOT, C.BUILD_FOOT, *pos):
            out.setdefault(c, tag)
    for k, (kind, x, y, r) in d['d'].items():
        tag = f'd{k}'
        f = DECOR.get(kind)
        if tag == skip or not f:
            continue
        for c in footprint(f['w'], f['h'], x, y, r):
            out.setdefault(c, tag)
    return out


def fits(look: str, t: int, w: int, h: int, where: str, x, y, r, taken: dict) -> str:
    """Why a thing of w × h cells (`where` it may stand) cannot go at (x, y) turned r: '' when it can."""
    if not (_int(x, 0, C.G - 1) and _int(y, 0, C.G - 1) and _int(r, 0, 3)):
        return 'Chỗ này nằm ngoài đảo.'
    ww, hh = (h, w) if r % 2 else (w, h)
    if x + ww > C.G or y + hh > C.G:
        return 'Chỗ này nằm ngoài đảo.'
    land, coast, fixed = cells(look, t)
    cs = footprint(w, h, x, y, r)
    if any(c in fixed for c in cs):
        return 'Chỗ này đã có công trình sẵn của đảo.'
    if any(c in taken for c in cs):
        return 'Chỗ này đã có đồ khác. Dời đồ kia đi trước nhé.'
    on = sum(1 for c in cs if land[c])
    if where in ('land', 'coast') and on < len(cs):
        return 'Phải đặt trên đất liền.'
    if where == 'coast' and not any(coast[c] for c in cs):
        return 'Phải đặt sát bờ biển.'
    if where == 'pier' and not 0 < on < len(cs):
        return 'Đặt một đầu trên bờ, một đầu ra biển.'
    if where == 'sea' and on:
        return 'Phải đặt trên mặt nước.'
    return ''


# ---------------------------------------------------------------- points (the 🏝️ Đảo đẹp board)
def decor_pts(items) -> int:
    """Each decoration's points (at most C.PTS_COPIES of one kind count) plus C.VARIETY for each different one."""
    n: dict = {}
    for kind in items:
        if kind in DECOR:
            n[kind] = n.get(kind, 0) + 1
    return sum(DECOR[k]['pts'] * min(c, C.PTS_COPIES) for k, c in n.items()) + C.VARIETY * len(n)


def tier_pts(t: int) -> int:
    return sum(C.EXPAND_PTS[:max(0, min(t, len(C.EXPAND_PTS)))])


def design_pts(d: dict) -> int:
    return decor_pts(v[0] for v in d['d'].values()) + tier_pts(d['t'])


def expand_price(iid: str, t: int) -> int:
    """The price of the lấn biển to tier t (1…): C.EXPAND_PCT of the island's list price."""
    it = isl.ISLAND.get(iid)
    if not it or not 1 <= t <= len(C.EXPAND_PCT):
        return 0
    return it['price'] * C.EXPAND_PCT[t - 1] // 100


# ---------------------------------------------------------------- commands
def action(s: dict, name: str, p: dict) -> dict:
    need = _core().need
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and isinstance(p.get('island'), str), 'Thông tin không hợp lệ.')
    iid = p['island']
    need(iid in isl.owned(s), 'Bạn chưa có hòn đảo này.', 'not_owned')
    fn = {'jr_isle_place': _place, 'jr_isle_dmove': _dmove, 'jr_isle_store': _store, 'jr_isle_bmove': _bmove,
          'jr_isle_expand': _expand, 'jr_isle_opt': _opt}[name]
    out = fn(s, p, iid)
    out.setdefault('isle', dict(island=iid))
    return out


def _keys(p: dict, allowed: set, needed: set) -> None:
    _core().need(set(p) <= allowed and needed <= set(p), 'Thông tin không hợp lệ.')


def _rot(p: dict, kind: str) -> int:
    r = p.get('r', 0)
    _core().need(_int(r, 0, 3), 'Thông tin không hợp lệ.')
    _core().need(r == 0 or rotatable(kind), 'Công trình này không xoay được.', 'no_turn')
    return r


def _place(s: dict, p: dict, iid: str) -> dict:
    need = _core().need
    _keys(p, {'island', 'kind', 'x', 'y', 'r', 'confirm'}, {'island', 'kind', 'x', 'y'})
    it = DECOR.get(p['kind']) if isinstance(p['kind'], str) else None
    need(it is not None, 'Chọn một món để đặt nhé.')
    r = _rot(p, it['id'])
    d = isle_of(s, iid)
    need(sum(1 for v in d['d'].values() if v[0] == it['id']) < it['max'], f'Mỗi đảo tối đa {it["max"]} {it["name"]}.', 'limit')
    need(len(d['d']) < C.ITEMS_MAX, f'Mỗi đảo tối đa {C.ITEMS_MAX} món trang trí.', 'limit')
    why = fits(LOOK_OF[iid], d['t'], it['w'], it['h'], it['where'], p['x'], p['y'], r, occupied(s, iid, d))
    need(not why, why, 'place')
    b = get(s)
    kept = (b['inv'].get(it['id'], 0) if b else 0) > 0
    how = ''
    if not kept:
        need(p.get('confirm') is True, f'Xác nhận mua {it["name"]} {_fmt(it["price"])} xu.')
        money = isl._lx().ready_why(s, it['price'])
        need(not money, money, 'not_enough')
        how = isl._take(s, it['price'], f'🏝️ {it["name"]} · {isl.ISLAND[iid]["name"]}')
    b = _ensure(s)
    d = _isle(s, iid)
    if kept:
        b['inv'][it['id']] -= 1
        if not b['inv'][it['id']]:
            b['inv'].pop(it['id'])
    else:
        b['st']['xu'] = min(BIG, b['st']['xu'] + it['price'])
    d['n'] = min(ID_MAX, d['n'] + 1)
    d['d'][str(d['n'])] = [it['id'], p['x'], p['y'], r]
    b['st']['placed'] = min(BIG, b['st']['placed'] + 1)
    msg = f'{it["emoji"]} Đã đặt {it["name"]} từ kho.' if kept else f'{it["emoji"]} Đã mua và đặt {it["name"]}: trả {how}.'
    return dict(message=msg, isle=dict(island=iid, item=d['n']))


def _item(s: dict, iid: str, p: dict) -> tuple:
    need = _core().need
    key = p.get('id')
    need(_int(key, 1, ID_MAX), 'Thông tin không hợp lệ.')
    d = isle_of(s, iid)
    v = d['d'].get(str(key))
    need(v is not None, 'Món này không còn trên đảo.', 'gone')
    return d, str(key), v


def _dmove(s: dict, p: dict, iid: str) -> dict:
    need = _core().need
    _keys(p, {'island', 'id', 'x', 'y', 'r'}, {'island', 'id', 'x', 'y'})
    d, key, (kind, x0, y0, r0) = _item(s, iid, p)
    it = DECOR.get(kind)
    need(it is not None, 'Món này không dời được.', 'unknown')
    r = _rot(p, kind)
    if [p['x'], p['y'], r] == [x0, y0, r0]:
        return dict(message=f'{it["name"]} đã ở đây rồi.', duplicate=True)
    why = fits(LOOK_OF[iid], d['t'], it['w'], it['h'], it['where'], p['x'], p['y'], r, occupied(s, iid, d, skip='d' + key))
    need(not why, why, 'place')
    _isle(s, iid)['d'][key] = [kind, p['x'], p['y'], r]
    return dict(message=f'{it["emoji"]} Đã dời {it["name"]}.' if [p['x'], p['y']] != [x0, y0] else f'{it["emoji"]} Đã xoay {it["name"]}.')


def _store(s: dict, p: dict, iid: str) -> dict:
    need = _core().need
    _keys(p, {'island', 'id'}, {'island', 'id'})
    d, key, (kind, *_) = _item(s, iid, p)
    b = _ensure(s)
    need(b['inv'].get(kind, 0) < C.INV_MAX, 'Kho đã đầy món này.', 'limit')
    _isle(s, iid)['d'].pop(key)
    b['inv'][kind] = b['inv'].get(kind, 0) + 1
    b['st']['stored'] = min(BIG, b['st']['stored'] + 1)
    it = DECOR.get(kind)
    return dict(message=f'{it["emoji"] if it else "📦"} Đã cất {it["name"] if it else "món này"} vào kho. Đặt lại lúc nào cũng được, không mất tiền.')


def _bmove(s: dict, p: dict, iid: str) -> dict:
    need = _core().need
    _keys(p, {'island', 'plot', 'x', 'y', 'r'}, {'island', 'plot', 'x', 'y'})
    plot = p['plot']
    need(_int(plot, 0, _ib().PLOTS_MAX - 1), 'Thông tin không hợp lệ.')
    e = _buildings(s, iid).get(plot)
    need(e is not None, 'Chỗ này chưa có công trình.', 'empty')
    it = _ib().known(e['k'])
    kind = it['id']
    r = _rot(p, kind)
    d = isle_of(s, iid)
    cur = building_pos(d, iid, plot)
    if cur and [p['x'], p['y'], r] == list(cur):
        return dict(message=f'{it["name"]} đã ở đây rồi.', duplicate=True)
    w, h, where = foot_of(kind)
    why = fits(LOOK_OF[iid], d['t'], w, h, where, p['x'], p['y'], r, occupied(s, iid, d, skip=f'b{plot}'))
    if why == 'Phải đặt sát bờ biển.':
        why = f'{it["name"]} phải đặt sát bờ biển.'
    need(not why, why, 'place')
    _isle(s, iid)['b'][str(plot)] = [p['x'], p['y'], r]
    moved = not cur or [p['x'], p['y']] != list(cur[:2])
    return dict(message=f'{it["emoji"]} Đã {"dời" if moved else "xoay"} {it["name"]}.', isle=dict(island=iid, plot=plot))


def _expand(s: dict, p: dict, iid: str) -> dict:
    need = _core().need
    _keys(p, {'island', 'confirm'}, {'island'})
    d = isle_of(s, iid)
    t = d['t'] + 1
    need(t <= tiers_max(), 'Đảo đã lấn biển tới cỡ lớn nhất rồi.', 'max')
    price = expand_price(iid, t)
    look = LOOK_OF[iid]
    # what the bigger island moves: the sea features (and an old marina plot's building) go out with the coast
    nd = dict(d, t=t, d=dict(d['d']), b=dict(d['b']))
    land, _, fixed = cells(look, t)
    taken: dict = {}
    for plot, e in _buildings(s, iid).items():
        pos = building_pos(nd, iid, plot)
        if not pos:
            continue
        cs = footprint(C.BUILD_FOOT, C.BUILD_FOOT, *pos)
        it = _ib().known(e['k'])
        need(not any(c in fixed for c in cs) and not any(c in taken for c in cs),
             f'{it["emoji"]} {it["name"]} đang chắn chỗ bờ biển mới. Dời nó vào trong một chút rồi lấn biển nhé.', 'blocked')
        for c in cs:
            taken[c] = f'b{plot}'
    back = []
    for k, (kind, x, y, r) in sorted(d['d'].items(), key=lambda kv: int(kv[0])):
        it = DECOR.get(kind)
        if not it:
            continue
        cs = footprint(it['w'], it['h'], x, y, r)
        on = sum(1 for c in cs if land[c])
        wrong = (it['where'] == 'sea' and on) or (it['where'] == 'pier' and on == len(cs))
        if wrong or any(c in fixed or c in taken for c in cs):
            back.append(k)
        else:
            for c in cs:
                taken[c] = 'd' + k
    need(p.get('confirm') is True, f'Xác nhận lấn biển {isl.ISLAND[iid]["name"]} {_fmt(price)} xu.')
    money = isl._lx().ready_why(s, price)
    need(not money, money, 'not_enough')
    how = isl._take(s, price, f'🌊 Lấn biển · {isl.ISLAND[iid]["name"]}')
    b = _ensure(s)
    x = _isle(s, iid)
    x['t'] = t
    for k in back:
        kind = x['d'].pop(k)[0]
        b['inv'][kind] = b['inv'].get(kind, 0) + 1
    b['st']['exp'] = min(BIG, b['st']['exp'] + price)
    extra = f' {len(back)} món trên bờ cũ được cất vào kho, đặt lại lúc nào cũng được.' if back else ''
    return dict(message=f'🌊 {isl.ISLAND[iid]["name"]} đã lấn biển (cỡ {t + 1}): trả {how}. Đảo rộng hơn, bãi cát mới chờ bạn trang trí!{extra}',
                isle=dict(island=iid, tier=t))


def _opt(s: dict, p: dict, iid: str) -> dict:
    _keys(p, {'island', 'paths'}, {'island', 'paths'})
    _core().need(type(p['paths']) is bool, 'Thông tin không hợp lệ.')
    x = _isle(s, iid)
    x['ap'] = 1 if p['paths'] else 0
    return dict(message='🛤️ Đã bật lối mòn tự động.' if p['paths'] else '🛤️ Đã tắt lối mòn tự động.')


# ---------------------------------------------------------------- the buildings (game/island_build.py)
def free_plot(s: dict, iid: str) -> int:
    """A plot index for a building placed on the grid: after the old plots of the island first (an older build shows
    nothing there), then any one free. -1: none left."""
    used = {int(k) for k in _ib()._plots(s, iid)}
    n = len(BC.PLOTS.get(iid, ()))
    for k in [*range(n, _ib().PLOTS_MAX), *range(n)]:
        if k not in used:
            return k
    return -1


def check_building(s: dict, iid: str, kind: str, x, y, r, plot: int | None = None) -> str:
    """Why building `kind` cannot stand at (x, y) turned r ('' when it can); `plot`: one that moves (left out)."""
    w, h, where = foot_of(kind)
    if r and not rotatable(kind):
        return 'Công trình này không xoay được.'
    why = fits(LOOK_OF[iid], isle_of(s, iid)['t'], w, h, where, x, y, r, occupied(s, iid, skip=f'b{plot}' if plot is not None else ''))
    return why


def check_plot(s: dict, iid: str, plot: int) -> str:
    """An old client builds on an old plot: its cells must still be free of decorations and moved buildings."""
    d = isle_of(s, iid)
    pos = building_pos(d, iid, plot)
    if not pos:
        return ''
    taken = occupied(s, iid, d)
    return 'Ô đất này đã có đồ trang trí. Dời đồ đi trước nhé.' if any(c in taken for c in footprint(C.BUILD_FOOT, C.BUILD_FOOT, *pos)) else ''


def set_building(s: dict, iid: str, plot: int, x: int, y: int, r: int) -> None:
    _isle(s, iid)['b'][str(plot)] = [x, y, r]


def on_raze(s: dict, iid: str, plot: int) -> None:
    b = get(s)
    d = b['i'].get(iid) if b else None
    if d:
        d['b'].pop(str(plot), None)


def on_sell(s: dict, iid: str) -> int:
    """Selling island `iid` (game/island.py _sell): its decorations go back into the kho (how many), the buildings'
    places go with them (they are razed), its tier stays with the save."""
    b = get(s)
    d = b['i'].get(iid) if b else None
    if not d:
        return 0
    n = 0
    for kind, *_ in d['d'].values():
        b['inv'][kind] = min(10**6, b['inv'].get(kind, 0) + 1)
        n += 1
    d['d'] = {}
    d['b'] = {}
    return n


# ---------------------------------------------------------------- views
def places(s: dict, iid: str, d: dict) -> dict:
    """{plot: [x, y, r]} of every building standing on the island (moved or on its old plot's cells)."""
    out = {}
    for plot in sorted(_buildings(s, iid)):
        pos = building_pos(d, iid, plot)
        if pos:
            out[str(plot)] = list(pos)
    return out


def with_places(lay: dict, iid: str, plots) -> dict:
    """A design read from island_layout (or none: tier 0) with a place for each of `plots` it has none for."""
    for plot in plots:
        if str(plot) not in lay['b']:
            pos = default_pos(iid, int(plot), lay['t'])
            if pos:
                lay['b'][str(plot)] = list(pos)
    return lay


def view(d: dict, s: dict | None = None, iid: str = '') -> dict:
    """One island's design for the clients: tier, decorations [[id, kind, x, y, r]], every building's place (with the
    save: the ones never moved too), footpaths, points."""
    return dict(t=d['t'], d=[[int(k), *v] for k, v in sorted(d['d'].items(), key=lambda kv: int(kv[0]))],
                b=places(s, iid, d) if s is not None else {k: list(v) for k, v in d['b'].items()}, ap=d['ap'], pts=design_pts(d))


def public(s: dict) -> dict | None:
    """The owned islands' designs (every one with a building or a design: its buildings' places come from here) and
    the kho. None while there is nothing to show (every island at tier 0, no building)."""
    b = get(s)
    out = {}
    for iid in isl.owned(s):
        d = b['i'].get(iid) if b else None
        if d or _buildings(s, iid):
            out[iid] = view(d or _isle_new(), s, iid)
    if not out and not b:
        return None
    return dict(i=out, inv=dict(b['inv']) if b else {})


def catalogue() -> dict:
    """Static lists for the client (bootstrap content, cached)."""
    return dict(g=C.G, x0=C.X0, cell=C.CELL, foot=C.BUILD_FOOT, items_max=C.ITEMS_MAX, copies=C.PTS_COPIES,
                variety=C.VARIETY, cats=[list(c) for c in C.CATS],
                tiers=[dict(s=s, pts=C.EXPAND_PTS[i - 1] if i else 0, pct=C.EXPAND_PCT[i - 1] if i else 0,
                            name=C.EXPAND_NAMES[i - 1] if i else 'Cỡ gốc') for i, s in enumerate(C.TIERS)],
                expand={i['id']: [expand_price(i['id'], t) for t in range(1, len(C.TIERS))] for i in isl.C.ISLANDS},
                decor=[dict(d) for d in C.DECOR])


# ---------------------------------------------------------------- PostgreSQL (island_layout; game/storage.py → island_build.command_commit)
def _rows(after) -> dict:
    """{island: (tier, data, pts)} the table should show for this save: the islands it owns that have a design."""
    b = get(after) if isinstance(after, dict) else None
    if not b:
        return {}
    owned = set(isl.owned(after))
    out = {}
    for iid, d in b['i'].items():
        if iid in owned:
            v = view(d, after, iid)
            data = json.dumps(dict(d=v['d'], b=v['b'], ap=v['ap']), separators=(',', ':'))
            out[iid] = (d['t'], data, v['pts'])
    return out


def sync(db, sid: str, after, t: float) -> set:
    """island_layout rows of this owner = the save. The islands whose row moved."""
    want = _rows(after)
    have = {r['island']: r for r in db.execute('SELECT island, tier, data, pts, status FROM island_layout WHERE owner=?', (sid,)).fetchall()}
    moved = set()
    for iid, row in want.items():
        r = have.get(iid)
        if r and r['status'] == 'up' and (int(r['tier']), r['data'], int(r['pts'])) == row:
            continue
        db.execute('INSERT INTO island_layout(owner, island, tier, data, pts, status, at) VALUES(?,?,?,?,?,\'up\',?) '
                   'ON CONFLICT(owner, island) DO UPDATE SET tier=excluded.tier, data=excluded.data, pts=excluded.pts, '
                   "status='up', at=excluded.at", (sid, iid, *row, t))
        moved.add(iid)
    for iid, r in have.items():
        if iid not in want and r['status'] == 'up':
            db.execute("UPDATE island_layout SET status='gone', at=? WHERE owner=? AND island=?", (t, sid, iid))
            moved.add(iid)
    return moved


def design_row(db, owner: str, iid: str) -> dict:
    """What visitors see of `owner`'s island `iid` (no sid in it): tier, decorations, buildings' places, points."""
    r = db.execute("SELECT tier, data, pts FROM island_layout WHERE owner=? AND island=? AND status='up'", (owner, iid)).fetchone()
    if not r:
        return dict(t=0, d=[], b={}, ap=0, pts=0)
    try:
        data = json.loads(r['data'])
    except (TypeError, ValueError):
        data = {}
    return dict(t=int(r['tier']), d=data.get('d') or [], b=data.get('b') or {}, ap=int(data.get('ap') or 0), pts=int(r['pts']))


def forget(db, sid: str) -> None:
    db.execute('DELETE FROM island_layout WHERE owner=?', (sid,))
