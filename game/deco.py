"""🪴 Bày trí phòng: set up the room you live in, one piece at a time (story mode).

Every place can be set up: a home you own (game/reno.py adds its repairs and upgrades), your spouse's home, a rented
room (Phòng trọ khép kín: the room and its gác lửng; Ký túc xá Hẻm 7: only your bunk corner) and Bà Tám's attic.
public/js/v4/reno.js draws the rooms (deco_content: walls, floor, fixtures) and the furniture; the player drags each
piece where they like.

Furniture belongs to the player, not to the home: it is the list `journey.reno.items` (ids, kinds) that 1.2.0 began.
Moving out, switching rooms or buying a home puts everything back in the túi đồ (the bag) and the player sets it up
again at the new place. Thu hồi (pick up) is free; selling back pays SELL_PCT % (as 1.2.0).

Free placement (1.4). A placed piece is an object {r: room, x, y, f: mirrored 0|1[, on: what it stands on][, z]} in
units (deco_content.U to a grid cell): x across the room, y from the back of the floor (floor pieces, rugs) or from
the top of the wall (wall pieces). A small 'top' piece stands on the floor or `on` a surface: a floor piece with a
`surface` (table, bed, shelf…), a wall shelf (`ledge`) or a fixture (`#counter`, `#pillow`, the dorm's `#shelf`); its
x, y are then inside that surface and it moves, flips and goes to the bag with it. Pieces may overlap (the drawing
sorts them by depth; `z` orders wall pieces, rugs and things on one surface). Rules (check, mirrored in reno.js for
the live preview, always checked here): the room type suits the piece; inside its zone (out-of-zone numbers from a
drag are clamped in); not over a fixture that keeps pieces off (door, window, ladder, counter…); at most room_cap
pieces a room and `hold` small things a surface. Commands are idempotent (the same spot twice is a no-op; a nonce
`n` guards buying, selling and skins) and server.py rate-limits them.

Tường & sàn: each room may get a wallpaper and a floor (deco_content.SKINS): free paints, cheap papers bought once.

Ấm cúng (points): each distinct kind placed counts its cozy once, plus each theme set completed in one room (SETS),
plus the home's upgrades (reno.COZY_LV a level, own home only). The morning bonus: a home you own keeps 1.2.0's
steps (reno.COZY_STEPS: +1 from 10, +2 from 24, with the parts at COZY_COND % and no late mortgage, paid by
reno.on_life_day); any other place gives RENT_STEPS (+1 from 10, never more: a rented corner should not beat owning
a home). On some days a neighbour drops by and praises the room (GUEST_*: a line, nothing else). Skins add no points.

Saves. `journey.decor` (FREE_VERSION) holds the free layout: {v, at, sig, items {uid: piece}, skins {room: {w, f}},
owned [skin ids], ops [recent nonces]}. `journey.deco` keeps exactly the 1.3.2 shape {v, at, day, pos {uid: [room,
x, y, flip]}, stats}: since 1.4 its `pos` is a grid mirror of the free layout (to_grid: each piece on the nearest
1.3.2 cell, kept only where the 1.3.2 rules allow), so a 1.3.2 build rolled back to shows the same room snapped to its
grid (pieces that do not fit there wait in its bag) and ignores journey.decor (an extra journey key). `sig` is the
mirror's checksum: when an older build has changed the mirror, the next load merges (pieces it did not touch keep
their free spot, the rest come from its grid). A 1.3.2 layout without journey.decor converts piece by piece
(from_grid: a cell becomes its units, a small thing on a table stands on that table); a 1.2.0 layout (reno items with
a room and slot) is read as grid spots near the old slots first (`_legacy`). Nothing is written until the first
jr_deco_* command. Deterministic: the neighbour's visit is seeded by the journey seed and the day.

Commands from a page loaded before 1.4 still work: jr_deco_place / jr_deco_buy with grid cells and jr_deco_layout with
[room, x, y, f] lists convert their cells; jr_reno_buy / move / store / sell (1.2.0) go through `legacy`.
"""
from __future__ import annotations

import json
import random
import re
import zlib

from . import deco_content as DC
from . import housing as hs

VERSION = 1                        # journey.deco (the 1.3.2 block, now the grid mirror)
FREE_VERSION = 1                   # journey.decor
COMMANDS = ('jr_deco_buy', 'jr_deco_place', 'jr_deco_pick', 'jr_deco_sell', 'jr_deco_layout', 'jr_deco_put', 'jr_deco_skin')
STATS = ('placed', 'picked', 'guests', 'cozy_days', 'spirit', 'best')
ITEMS = DC.ITEMS
SETS = DC.SETS
SKINS = DC.SKINS
U = DC.U
SELL_PCT = 50
RENT_STEPS = ((10, 1),)            # tinh thần each morning outside a home you own: +1 at most
GUEST_MIN = 14                     # Ấm cúng from which a neighbour may drop by
GUEST_ODDS = 3                     # one day in three (seeded)
LEVELS = ((40, 'Tổ ấm trong mơ'), (24, 'Rất ấm cúng'), (10, 'Ấm cúng'), (5, 'Dễ thương'), (0, 'Còn trống trải'))
CATCHUP = 400
XY_MAX = 15                        # a grid cell (1.3.2, the mirror)
FREE_MAX = 400                     # a free coordinate (units): rooms are at most 9 cells (180 units) wide
Z_MAX = 99
OPS_MAX = 12                       # nonces remembered
OWNED_MAX = 64
LAYER_RANK = {'rug': 0, 'wall': 1, 'floor': 2, 'top': 3}
PIECE_KEYS = ('r', 'x', 'y', 'f')  # every placed piece
PIECE_OPT = ('on', 'z')            # optional keys of a placed piece (add new optional keys here and in _piece_ok)
_ID = re.compile(r'^[a-z0-9_]{1,24}$')
_KEY = re.compile(r'^[a-z0-9_:]{1,48}$')
_ON = re.compile(r'^#?[a-z0-9_]{1,24}$')
_NONCE = re.compile(r'^[A-Za-z0-9_-]{4,40}$')
_SKIN = re.compile(r'^[a-z0-9_]{1,24}$')
FREE_KEYS = {'v', 'at', 'sig', 'items', 'skins', 'owned', 'ops'}
NEW_KEYS = {'v', 'at', 'items'}   # journey.decor_new (1.4.11)
NEW_VERSION = 1


def _rn():
    from . import reno
    return reno


def _core():
    from . import engine
    return engine


def _rx():
    from . import relax
    return relax


def _fr():
    from . import fridge
    return fridge


def layer_of(k: str) -> str:
    return ITEMS[k]['spot']


def lname(s: str) -> str:
    return s[:1].lower() + s[1:]


def sell_price(k: str) -> int:
    return ITEMS[k]['price'] * SELL_PCT // 100


def get(s: dict) -> dict | None:
    """journey.deco: the 1.3.2 block (stats, the day, the grid mirror)."""
    j = s.get('journey')
    d = j.get('deco') if isinstance(j, dict) else None
    return d if isinstance(d, dict) else None


def get_new(s: dict) -> dict | None:
    """journey.decor_new: the free layout of the rooms added since 1.4.11 (the bathroom, a villa's pool), apart from
    journey.decor so that an older build, which checks every piece there against the rooms it knows, never sees them
    (it keeps them in its bag; the key itself it ignores). {v, at (the place), items {uid: piece}}; absent when empty."""
    j = s.get('journey')
    X = j.get('decor_new') if isinstance(j, dict) else None
    return X if isinstance(X, dict) else None


def get_free(s: dict) -> dict | None:
    """journey.decor: the free layout (1.4)."""
    j = s.get('journey')
    d = j.get('decor') if isinstance(j, dict) else None
    return d if isinstance(d, dict) else None


def blank(day: int, at: str) -> dict:
    return dict(v=VERSION, at=at, day=int(day), pos={}, stats={k: 0 for k in STATS})


def blank_free(at: str) -> dict:
    return dict(v=FREE_VERSION, at=at, sig=sig({}), items={}, skins={}, owned=[], ops=[])


def sig(pos: dict) -> int:
    """The checksum of a grid mirror (journey.deco.pos) as written."""
    return zlib.crc32(json.dumps(pos, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


# ---------------------------------------------------------------- where you live, its rooms
def place(j: dict) -> dict:
    """Where the player lives now: key (changes with every move), where ('own'|'shared'|'rent'|'attic'), home kind."""
    h = j.get('home') if isinstance(j.get('home'), dict) else None
    where, kind = hs.where(h)
    if where == 'own':
        key = f"own:{h['own']['id']}:{kind}"
    elif where == 'shared':
        key = f"shared:{h['shared']['couple']}:{h['shared']['id']}:{kind}"
    elif where == 'rent':
        key = f"rent:{kind}:{h['rent']['since']}"
    else:
        key = 'attic'
    return dict(key=key, where=where, kind=kind)


_ROOMS: dict = {}


def kit_room(kit: str) -> dict:
    """A room every home of a kind gets since 1.4.11 (deco_content.KITS), marked new (an older build does not know it)."""
    return dict(DC.KITS[kit], kit=kit, new=True)


def rooms_of(key: str) -> list | None:
    """The rooms of the place `key` (None: a place this build does not know). Shared, never changed.
    The rooms it always had come first, then its new ones (deco_content.EXTRA_ROOMS: the bathroom, a villa's pool)."""
    if key in _ROOMS:
        return _ROOMS[key]
    bits = key.split(':')
    out = None
    kind = ''
    if key == 'attic':
        out, kind = list(DC.RENT_ROOMS['attic']), 'attic'
    elif bits[0] == 'rent' and len(bits) == 3 and bits[1] in DC.RENT_ROOMS:
        out, kind = list(DC.RENT_ROOMS[bits[1]]), bits[1]
    elif bits[0] in ('own', 'shared') and bits[-1] in _rn().HOUSES:
        out, kind = [DC.own_room(*row) for row in _rn().HOUSES[bits[-1]]['rooms']], bits[-1]
    if out is not None:
        out += [kit_room(k) for k in DC.EXTRA_ROOMS.get(kind, ())]
    if out is not None and len(_ROOMS) < 64:
        _ROOMS[key] = out
    return out


def old_rooms(rooms: list) -> list:
    """The rooms an older build knows (the 1.3.2 grid mirror is about these only)."""
    return [r for r in rooms if not r.get('new')]


# ---------------------------------------------------------------- the 1.3.2 grid (the mirror an older build reads)
def _cells(x: int, y: int, w: int, h: int):
    return [(x + i, y + k) for i in range(w) for k in range(h)]


def _occupancy(rooms: list, kinds: dict, pos: dict, skip=()) -> dict:
    """{room: {layer: {cell: uid or '#fixture'}}} plus the surfaces: {room: {cell: True}} under 'surf'."""
    occ = {r['id']: dict(wall={}, floor={}, rug={}, top={}, surf={}) for r in rooms}
    for r in rooms:
        o = occ[r['id']]
        for f in r['fix']:
            for c in _cells(f['x'], f['y'], f['w'], f['h']):
                o[f['layer']][c] = '#' + f['t']
                if f['surface']:
                    o['surf'][c] = True
    for uid, (room, x, y, _f) in pos.items():
        if uid in skip or room not in occ or kinds.get(uid) not in ITEMS:
            continue
        it = ITEMS[kinds[uid]]
        o = occ[room]
        for c in _cells(x, y, it['w'], it['h']):
            o[it['spot']][c] = uid
            if it['spot'] == 'floor' and it['surface']:
                o['surf'][c] = True
    return occ


def fit(room: dict, k: str, x, y, occ: dict) -> tuple[str, str] | None:
    """1.3.2's rule: can a piece of kind `k` stand on cell (x, y) of `room` among the others (`occ`)?
    None, or (code, what is in the way: a uid or '#fixture')."""
    it = ITEMS[k]
    if room['type'] not in it['rooms']:
        return ('type', '')
    spot = it['spot']
    rows = room['wrows'] if spot == 'wall' else room['frows']
    if not rows:
        return ('nowall', '')
    if type(x) is not int or type(y) is not int or x < 0 or y < 0 or x + it['w'] > room['cols'] or y + it['h'] > rows:
        return ('bounds', '')
    o = occ[room['id']]
    for c in _cells(x, y, it['w'], it['h']):
        there = o[spot].get(c)
        if there:
            return ('fixture' if there[0] == '#' else 'taken', there)
        if spot == 'floor' and not it['surface'] and o['top'].get(c):
            return ('covers', o['top'][c])
        if spot == 'top':
            under = o['floor'].get(c)
            if under and not o['surf'].get(c):
                return ('fixture' if under[0] == '#' else 'support', under)
    return None


def _order(pos: dict, seq: dict) -> list:
    """Rugs, wall pieces, floor pieces, then small things (they need to know what is under them)."""
    return sorted(pos, key=lambda u: (LAYER_RANK.get(ITEMS[seq[u][1]]['spot'], 9) if seq[u][1] in ITEMS else 9, seq[u][0]))


def settle(rooms: list, kinds: dict, pos: dict, order: list) -> tuple[dict, list]:
    """1.3.2: keep what stands on the grid where it may, in order: (kept, the uids left out)."""
    seq = {u: (i, kinds.get(u)) for i, u in enumerate(order)}
    for u in pos:
        seq.setdefault(u, (len(seq), kinds.get(u)))
    rs = {r['id']: r for r in rooms}
    kept, out = {}, []
    occ = _occupancy(rooms, kinds, {})
    for uid in _order(pos, seq):
        room, x, y, f = pos[uid]
        k = kinds.get(uid)
        if k not in DC.KNOWN_132 or room not in rs or f not in (0, 1) or fit(rs[room], k, x, y, occ):
            out.append(uid)
            continue
        kept[uid] = (room, x, y, f)
        it = ITEMS[k]
        o = occ[room]
        for c in _cells(x, y, it['w'], it['h']):
            o[it['spot']][c] = uid
            if it['spot'] == 'floor' and it['surface']:
                o['surf'][c] = True
    return {u: kept[u] for u in pos if u in kept}, out


def _near(room: dict, k: str, tx: int, ty: int, occ: dict) -> tuple[int, int] | None:
    it = ITEMS[k]
    rows = room['wrows'] if it['spot'] == 'wall' else room['frows']
    spots = [(x, y) for x in range(room['cols'] - it['w'] + 1) for y in range(rows - it['h'] + 1)]
    spots.sort(key=lambda p: (abs(p[0] - tx) + abs(p[1] - ty), abs(p[1] - ty), p[0]))
    return next((p for p in spots if not fit(room, k, p[0], p[1], occ)), None)


def slot_target(room: dict, k: str, slot: str, n: int) -> tuple[int, int]:
    """Where 1.2.0's slot `w3` / `f1` (one of `n` across the room) lies on the grid, for a piece of kind `k`."""
    it = ITEMS[k]
    i = int(slot[1:]) if slot[1:].isdigit() else 0
    n = max(n, i + 1, 1)
    if slot[0] == 'w':
        return round(room['cols'] * (i + 1) / (n + 1) - it['w'] / 2), 0
    return round(room['cols'] * (i + 0.5) / n - it['w'] / 2), max(0, room['frows'] - it['h'] - 1)


def _legacy_counts(key: str) -> dict:
    kind = key.split(':')[-1]
    rows = _rn().HOUSES.get(kind, {}).get('rooms', ())
    return {row[0]: (row[1], row[2]) for row in rows}


def _legacy(r: dict, rooms: list, kinds: dict, pos: dict, key: str) -> dict:
    """Pieces 1.2.0 (or an older build after a rollback) left in a room slot of this home: as near as they fit."""
    olds = [it for it in r['items'] if it['r'] is not None and it['k'] in ITEMS]
    if not olds:
        return pos
    rs = {x['id']: x for x in rooms}
    counts = _legacy_counts(key)
    pos = {u: p for u, p in pos.items() if u not in {it['id'] for it in olds}}
    for it in sorted(olds, key=lambda i: LAYER_RANK[ITEMS[i['k']]['spot']]):
        room = rs.get(it['r'])
        if not room or not isinstance(it['x'], str) or not it['x']:
            continue
        w, f = counts.get(room['id'], (0, 0))
        tx, ty = slot_target(room, it['k'], it['x'], w if it['x'][0] == 'w' else f)
        occ = _occupancy(rooms, kinds, pos)
        spot = _near(room, it['k'], tx, ty, occ)
        if spot:
            pos[it['id']] = (room['id'], spot[0], spot[1], 0)
    return pos


# ---------------------------------------------------------------- free placement: the rules
def fixtures(room: dict) -> list:
    """Every fixture of a room (1.3.2's and the built-ins since)."""
    return list(room['fix']) + list(room.get('more', ()))


def _ff(f: dict) -> dict:
    return DC.FIX_FREE.get(f['t'], {})


def room_cap(room: dict) -> int:
    """How many pieces one room takes (small things on tables count too)."""
    return min(_rn().ITEMS_MAX, room['cols'] * (room['wrows'] + room['frows']) + 4)


def zone(room: dict, k: str) -> tuple[int, int] | None:
    """The largest x and y a piece of kind `k` may take on its own (not on a surface) in `room`; None: no room for it."""
    it = ITEMS[k]
    rows = room['wrows'] if it['spot'] == 'wall' else room['frows']
    xm, ym = room['cols'] * U - it['w'] * U, rows * U - it['h'] * U
    return (xm, ym) if rows and xm >= 0 and ym >= 0 else None


def _ov(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def blocked(room: dict, k: str, x: int, y: int) -> str:
    """The fixture a piece at (x, y) would cover (more than half a cell both ways), or ''."""
    it = ITEMS[k]
    layer = 'wall' if it['spot'] == 'wall' else 'floor'
    w, h = it['w'] * U, it['h'] * U
    for f in fixtures(room):
        P = _ff(f)
        if f['layer'] != layer or not P.get('block') or (it['spot'] == 'rug' and P.get('rug')) or set(P.get('allow', ())) & set(it['tags']):
            continue
        fx, fy = f['x'] * U, f['y'] * U
        if _ov(x, x + w, fx, fx + f['w'] * U) > U // 2 and _ov(y, y + h, fy, fy + f['h'] * U) > U // 2:
            return f['t']
    return ''


def host_of(room: dict, on: str, pos: dict, kinds: dict) -> dict | None:
    """The surface `on` (a placed uid or '#fixture') in `room`: {w, d (0: a wall shelf), cap, wall}, or None."""
    if not isinstance(on, str) or not on:
        return None
    if on[0] == '#':
        for f in fixtures(room):
            P = _ff(f)
            if f['t'] == on[1:] and (P.get('top') or P.get('ledge')):
                return dict(w=f['w'] * U, d=0 if f['layer'] == 'wall' else f['h'] * U, cap=f['w'] * P.get('hold', 2), wall=f['layer'] == 'wall')
        return None
    q = pos.get(on)
    if not q or q['r'] != room['id'] or q.get('on') or kinds.get(on) not in ITEMS:
        return None
    it = ITEMS[kinds[on]]
    if it['spot'] == 'floor' and it['surface']:
        return dict(w=it['w'] * U, d=it['h'] * U, cap=it['w'] * it['h'] * 2, wall=False)
    if it['spot'] == 'wall' and it['ledge']:
        return dict(w=it['w'] * U, d=0, cap=it['w'] * 2, wall=True)
    return None


def check(room: dict, k: str, q: dict, pos: dict, kinds: dict) -> tuple[str, str] | None:
    """Can a piece of kind `k` stand at `q` in `room` among `pos` (itself left out)? None, or (code, what is in the
    way: '#fixture', a uid or '')."""
    it = ITEMS[k]
    if room['type'] not in it['rooms']:
        return ('type', '')
    x, y, on = q['x'], q['y'], q.get('on') or ''
    if on:
        if it['spot'] != 'top':
            return ('support', '')
        h = host_of(room, on, pos, kinds)
        if not h:
            return ('support', on if on in kinds else '')
        if not (0 <= x <= max(0, h['w'] - it['w'] * U) and 0 <= y <= max(0, h['d'] - it['h'] * U)):
            return ('bounds', '')
        if sum(1 for v in pos.values() if v.get('on') == on and v['r'] == room['id']) >= h['cap']:
            return ('host_full', on if on[0] != '#' else on)
    else:
        z = zone(room, k)
        if z is None:
            return ('nowall' if it['spot'] == 'wall' and not room['wrows'] else 'bounds', '')
        if not (0 <= x <= z[0] and 0 <= y <= z[1]):
            return ('bounds', '')
        b = blocked(room, k, x, y)
        if b:
            return ('fixture', '#' + b)
    if sum(1 for v in pos.values() if v['r'] == room['id']) >= room_cap(room):
        return ('room_full', '')
    return None


def _rank(k: str, q: dict) -> int:
    spot = ITEMS[k]['spot'] if k in ITEMS else ''
    return 4 if q.get('on') else LAYER_RANK.get(spot, 9)


def settle_free(rooms: list, kinds: dict, pos: dict, order: list) -> tuple[dict, list]:
    """Keep what may stand where it is, in order (rugs, walls, floor, small things on the floor, then on surfaces):
    (kept, the uids left out). Each piece is checked against those kept before it."""
    idx = {u: i for i, u in enumerate(order)}
    rs = {r['id']: r for r in rooms}
    kept, out = {}, []
    for uid in sorted(pos, key=lambda u: (_rank(kinds.get(u), pos[u]), idx.get(u, len(idx)))):
        q = pos[uid]
        k = kinds.get(uid)
        if k not in ITEMS or q['r'] not in rs or q['f'] not in (0, 1) or check(rs[q['r']], k, q, kept, kinds):
            out.append(uid)
            continue
        kept[uid] = q
    return {u: kept[u] for u in pos if u in kept}, out


def riders(pos: dict, uid: str) -> list:
    """The small things standing on `uid`."""
    return [u for u, v in pos.items() if v.get('on') == uid]


def _q(r: str, x: int, y: int, f: int, on: str = '', z: int = 0) -> dict:
    q = dict(r=r, x=int(x), y=int(y), f=int(f))
    if on:
        q['on'] = on
    if z:
        q['z'] = int(z)
    return q


# ---------------------------------------------------------------- grid <-> free
def from_grid(rooms: list, kinds: dict, gpos: dict) -> dict:
    """A 1.3.2 layout {uid: (room, x, y, f)} in free units: each cell at its units; a small thing on a table, a bed
    or the kitchen counter stands on it."""
    rs = {r['id']: r for r in rooms}
    out = {}
    for uid, (room, x, y, f) in gpos.items():
        k = kinds.get(uid)
        if k in ITEMS and room in rs and ITEMS[k]['spot'] != 'top':
            out[uid] = _q(room, x * U, y * U, f)
    for uid, (room, x, y, f) in gpos.items():
        k = kinds.get(uid)
        if k not in ITEMS or room not in rs or ITEMS[k]['spot'] != 'top':
            continue
        host = None
        for h, (hr, hx, hy, _g) in gpos.items():
            hk = kinds.get(h)
            if hr == room and hk in ITEMS and ITEMS[hk]['spot'] == 'floor' and ITEMS[hk]['surface'] \
                    and hx <= x < hx + ITEMS[hk]['w'] and hy <= y < hy + ITEMS[hk]['h']:
                host = (h, hx, hy)
                break
        if host is None:
            for fx in rs[room]['fix']:
                if fx['layer'] == 'floor' and fx['surface'] and fx['x'] <= x < fx['x'] + fx['w'] and fx['y'] <= y < fx['y'] + fx['h']:
                    host = ('#' + fx['t'], fx['x'], fx['y'])
                    break
        if host:
            out[uid] = _q(room, (x - host[1]) * U, (y - host[2]) * U, f, host[0])
        else:
            out[uid] = _q(room, x * U, y * U, f)
    return {u: out[u] for u in gpos if u in out}


def _cell(v: int, n: int) -> int:
    return max(0, min(n, (v + U // 2) // U))


def grid_guess(rooms: list, kinds: dict, fpos: dict) -> dict:
    """Every free piece on its nearest grid cell (not checked; small things on a wall shelf have none)."""
    rs = {r['id']: r for r in rooms}
    g = {}
    for uid, q in sorted(fpos.items(), key=lambda kv: 1 if kv[1].get('on') else 0):
        k = kinds.get(uid)
        if k not in ITEMS or q['r'] not in rs:
            continue
        it, room, on = ITEMS[k], rs[q['r']], q.get('on')
        if on and on[0] == '#':
            f = next((f for f in room['fix'] if f['t'] == on[1:] and f['layer'] == 'floor'), None)
            if not f:
                continue
            g[uid] = (room['id'], f['x'] + _cell(q['x'], f['w'] - 1), f['y'] + _cell(q['y'], f['h'] - 1), q['f'])
        elif on:
            hk, hg = kinds.get(on), g.get(on)
            if hk not in ITEMS or ITEMS[hk]['spot'] != 'floor' or not hg:
                continue
            g[uid] = (room['id'], hg[1] + _cell(q['x'], ITEMS[hk]['w'] - 1), hg[2] + _cell(q['y'], ITEMS[hk]['h'] - 1), q['f'])
        else:
            rows = room['wrows'] if it['spot'] == 'wall' else room['frows']
            g[uid] = (room['id'], _cell(q['x'], max(0, room['cols'] - it['w'])), _cell(q['y'], max(0, rows - it['h'])), q['f'])
    return g


def to_grid(rooms: list, kinds: dict, fpos: dict, order: list) -> dict:
    """The grid mirror of a free layout: what a 1.3.2 build would show (its rules; the rest waits in its bag)."""
    rooms = old_rooms(rooms)
    g = grid_guess(rooms, kinds, fpos)
    kept, _out = settle(rooms, kinds, {u: g[u] for u in fpos if u in g}, order)
    return kept


def _merge(rooms: list, kinds: dict, order: list, fpos: dict, gpos: dict) -> dict:
    """An older build changed the mirror: the pieces it left alone keep their free spot, the others come from its grid;
    a piece it put away stays in the bag."""
    mirror = to_grid(rooms, kinds, fpos, order)
    conv = from_grid(rooms, kinds, gpos)
    out = {}
    for u in order:
        if u in gpos:
            if u in fpos and mirror.get(u) == tuple(gpos[u]):
                out[u] = fpos[u]
            elif u in conv:
                out[u] = conv[u]
        elif u in fpos and u not in mirror:
            out[u] = fpos[u]
    return out


# ---------------------------------------------------------------- the layout as it stands today
def layout(s: dict) -> dict:
    """Today's layout without writing anything: place, rooms, kinds {uid: k}, order, pos {uid: piece} (journey.decor and
    journey.decor_new together), skins, journey (for _store)."""
    j = s['journey']
    pl = place(j)
    rooms = rooms_of(pl['key']) or []
    r = _rn().get(s)
    items = r['items'] if r else []
    kinds = {it['id']: it['k'] for it in items}
    order = [it['id'] for it in items]
    d, D = get(s), get_free(s)
    gpos = {}
    if d is not None and d['at'] == pl['key']:
        gpos = {u: tuple(v) for u, v in d['pos'].items() if u in kinds}
    slots = bool(r) and pl['where'] == 'own' and r['hid'] == j['home']['own']['id'] and any(it['r'] is not None for it in items)
    if slots:
        gpos = _legacy(r, rooms, kinds, gpos, pl['key'])
    gpos, _ = settle(rooms, kinds, gpos, order)
    skins = {}
    if D is not None and D['at'] == pl['key']:
        pos = {u: dict(v) for u, v in D['items'].items() if u in kinds}
        if d is not None and (slots or sig(d['pos']) != D['sig']):
            pos = _merge(rooms, kinds, order, pos, gpos)
        skins = {rm: dict(v) for rm, v in D['skins'].items()}
    else:
        pos = from_grid(rooms, kinds, gpos)
    X = get_new(s)
    if X is not None and X['at'] == pl['key']:   # the new rooms' pieces (a piece an older build has placed since: its spot)
        pos.update({u: dict(v) for u, v in X['items'].items() if u in kinds and u not in pos})
    pos, _ = settle_free(rooms, kinds, pos, order)
    return dict(place=pl, rooms=rooms, kinds=kinds, order=order, pos=pos, skins=skins, journey=j)


def _match(need: tuple, items: list, tags: tuple) -> tuple[int, list]:
    """The most entries of a set one room fills (each piece once; the room's own tags fill one tag entry each):
    (how many, the entries still missing)."""
    best = [0, list(range(len(need)))]
    pool = [(u, k) for u, k in items] + [('#' + t, '#' + t) for t in tags]

    def ok(entry, k):
        if entry[0] == 'tag':
            return (k[1:] == entry[1]) if k.startswith('#') else entry[1] in ITEMS[k]['tags']
        return not k.startswith('#') and k in entry

    def walk(i, used, got, miss):
        if got + (len(need) - i) <= best[0]:
            return
        if i == len(need):
            best[0], best[1] = got, list(miss)
            return
        for u, k in pool:
            if u not in used and ok(need[i], k):
                walk(i + 1, used | {u}, got + 1, miss)
                if best[0] == len(need):
                    return
        walk(i + 1, used, got, miss + [i])
    walk(0, frozenset(), 0, [])
    return best[0], best[1]


def sets_of(L: dict) -> list[dict]:
    """Per set: done (in some room), the room closest to it and what it still needs there."""
    out = []
    by_room = {}
    for u, q in L['pos'].items():
        by_room.setdefault(q['r'], []).append((u, L['kinds'][u]))
    for sid, S in SETS.items():
        best = (-1, None, [])
        for room in L['rooms']:
            got, miss = _match(S['need'], by_room.get(room['id'], []), room['tags'])
            if got > best[0]:
                best = (got, room['id'], miss)
        got, rid, miss = best
        possible = any(all(_fits_type(entry, room) for entry in S['need']) for room in L['rooms'])
        out.append(dict(id=sid, done=got == len(S['need']), have=max(0, got), need=len(S['need']), room=rid,
                        miss=_collapse([_entry_word(S['need'][i]) for i in miss]), possible=possible))
    return out


def _collapse(words: list) -> list:
    """['tranh, ảnh', 'tranh, ảnh'] -> ['tranh, ảnh ×2']."""
    out = []
    for w in words:
        if w not in [x.split(' ×')[0] for x in out]:
            n = words.count(w)
            out.append(f'{w} ×{n}' if n > 1 else w)
    return out


def _fits_type(entry: tuple, room: dict) -> bool:
    if entry[0] == 'tag':
        return entry[1] in room['tags'] or any(entry[1] in it['tags'] and room['type'] in it['rooms'] for it in ITEMS.values())
    return any(room['type'] in ITEMS[k]['rooms'] for k in entry)


def _entry_word(entry: tuple) -> str:
    if entry[0] == 'tag':
        return DC.TAG_WORDS.get(entry[1], entry[1])
    return ' hoặc '.join(lname(ITEMS[k]['name']) for k in entry)


def points(L: dict, sets: list | None = None) -> dict:
    """Ấm cúng from what is placed: each kind once, plus the sets done."""
    kinds = {L['kinds'][u] for u in L['pos']}
    items = sum(ITEMS[k]['cozy'] for k in kinds)
    sets = sets if sets is not None else sets_of(L)
    bonus = sum(SETS[x['id']]['bonus'] for x in sets if x['done'])
    return dict(items=items, sets=bonus, total=items + bonus)


def level_of(points: int) -> str:
    return next(name for low, name in LEVELS if points >= low)


def rent_perk(points: int) -> int:
    return next((n for low, n in RENT_STEPS if points >= low), 0)


def decor_points(s: dict) -> int:
    """reno.py: the decor part of a home's Ấm cúng."""
    return points(layout(s))['total']


def guest(s: dict, L: dict, total: int, day: int) -> dict | None:
    """The neighbour who drops by on `day` (seeded; computed, never stored): emoji, name, their line."""
    if total < GUEST_MIN or not L['pos']:
        return None
    j = s['journey']
    pl = L['place']
    rng = random.Random(f'deco-guest|{j.get("seed", 0)}|{int(day)}|{pl["key"]}')
    if rng.randrange(GUEST_ODDS):
        return None
    pool = DC.GUESTS['attic' if pl['where'] == 'attic' else pl['kind'] if pl['where'] == 'rent' and pl['kind'] in DC.GUESTS else 'home']
    emoji, name, lines = rng.choice(pool)
    k = rng.choice(sorted({L['kinds'][u] for u in L['pos']}))
    return dict(emoji=emoji, name=name, text=rng.choice(lines).format(item=lname(ITEMS[k]['name'])))


# ---------------------------------------------------------------- the daily tick
def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Follow the player home (a move puts everything in the bag), the morning bonus outside a home you own (a home
    you own: reno.on_life_day), a neighbour's visit. Only a block that exists is touched; idempotent."""
    j = s.get('journey')
    d = get(s)
    if d is None or not j.get('story'):
        return []
    notes: list[str] = []
    pl = place(j)
    D = get_free(s)
    if d['at'] != pl['key']:
        if d['pos'] or (D is not None and D['items']):
            notes.append('📦 Chuyển chỗ ở rồi: đồ trang trí đã gói vào túi đồ, vào bày lại phòng mới nhé!')
        d['at'], d['pos'] = pl['key'], {}
    if D is not None and D['at'] != pl['key']:
        D.update(at=pl['key'], items={}, skins={}, sig=sig(d['pos']))
    X = get_new(s)
    if X is not None and X['at'] != pl['key']:
        j.pop('decor_new')
    target = int(j['life_day'])
    d['day'] = max(d['day'], target - CATCHUP)
    if d['day'] < target:
        L = layout(s)
        pts = points(L)['total']
        total = pts + (_rn().upgrade_points(s) if pl['where'] == 'own' else 0)
        n = rent_perk(pts) if pl['where'] != 'own' else 0
        while d['day'] < target:
            d['day'] += 1
            if n:
                got = hs._spirit(s, n)
                d['stats']['cozy_days'] += 1
                d['stats']['spirit'] += got
        g = guest(s, L, total, target)
        if g:
            notes.append(f'{g["emoji"]} {g["name"]} ghé chơi: {g["text"]}')
            d['stats']['guests'] += 1
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- commands
_WHY = {
    'type': '{it} không hợp đặt ở {room}.',
    'nowall': '{room} không có tường để treo {it_l}.',
    'bounds': 'Chỗ này nằm ngoài {room_l} rồi.',
    'taken': 'Chỗ này vướng {other}. Dời món kia đi trước nhé.',
    'covers': 'Trên sàn chỗ này có {other}. Thu hồi nó trước, hoặc đặt món khác vào nhé.',
    'support': '{it} chỉ đặt lên bàn, kệ, giường hoặc sàn trống thôi.',
    'fixture': 'Chỗ này vướng {other}.',
    'host_full': 'Trên {other} hết chỗ rồi. Đặt chỗ khác nhé.',
    'room_full': '{room} bày đủ {cap} món rồi. Thu hồi bớt món khác nhé.',
}
FIX_NAMES = {'door': 'cửa ra vào', 'window': 'cửa sổ', 'counter': 'kệ bếp', 'splash': 'tường bếp', 'slope': 'mái gác',
             'ladder': 'cầu thang', 'pillow': 'cái gối', 'shelf': 'kệ đầu giường', 'shower': 'vòi sen', 'toilet': 'bồn cầu',
             'pool': 'hồ bơi'}


def why(code: str, k: str, room: dict, other: str, kinds: dict) -> str:
    it = ITEMS[k]['name']
    o = FIX_NAMES.get(other[1:], 'chỗ cố định') if other.startswith('#') else lname(ITEMS[kinds[other]]['name']) if kinds.get(other) in ITEMS else 'món khác'
    return _WHY[code].format(it=it, it_l=lname(it), room=room['name'], room_l=lname(room['name']), other=o, cap=room_cap(room))


def _code(bad: str) -> str:
    return 'taken' if bad in ('taken', 'covers', 'fixture', 'host_full', 'room_full') else 'bad_spot'


def _ensure(s: dict) -> tuple[dict, dict, dict]:
    """Both blocks for a command, following the player home; older layouts become free positions now
    (1.2.0 slots leave the reno items)."""
    j = s['journey']
    L = layout(s)
    d, D = get(s), get_free(s)
    if d is None:
        d = j['deco'] = blank(j['life_day'], L['place']['key'])
    if D is None:
        D = j['decor'] = blank_free(L['place']['key'])
    d['at'] = D['at'] = L['place']['key']
    D['skins'] = L['skins']
    r = _rn().get(s)
    for it in (r['items'] if r else []):
        it['r'] = it['x'] = None
    _store(d, D, L, L['pos'])
    return d, D, L


def _store(d: dict, D: dict, L: dict, pos: dict) -> None:
    """Write the free layout and its grid mirror (what an older build reads). The pieces in the new rooms go to
    journey.decor_new, the others to journey.decor (an older build checks every piece there against its own rooms)."""
    j = L['journey']
    new = {r['id'] for r in L['rooms'] if r.get('new')}
    D['items'] = {u: dict(pos[u]) for u in L['order'] if u in pos and pos[u]['r'] not in new}
    xs = {u: dict(pos[u]) for u in L['order'] if u in pos and pos[u]['r'] in new}
    if xs:
        j['decor_new'] = dict(v=NEW_VERSION, at=L['place']['key'], items=xs)
    else:
        j.pop('decor_new', None)
    L['pos'] = {u: dict(v) for u, v in list(D['items'].items()) + list(xs.items())}
    g = to_grid(L['rooms'], L['kinds'], D['items'], L['order'])
    d['pos'] = {u: list(g[u]) for u in L['order'] if u in g}
    D['sig'] = sig(d['pos'])
    d['stats']['best'] = max(d['stats']['best'], points(L)['total'])


def _int(p: dict, key: str, default=None):
    v = p.get(key, default)
    if type(v) is bool:
        v = int(v)
    return v


def _seen(D: dict | None, p: dict) -> bool:
    n = p.get('n')
    return D is not None and isinstance(n, str) and n in D['ops']


def _mark(D: dict, p: dict) -> None:
    n = p.get('n')
    if isinstance(n, str) and _NONCE.match(n):
        D['ops'] = (D['ops'] + [n])[-OPS_MAX:]


def _target(p: dict, L: dict) -> tuple[dict, int, int, int]:
    """1.3.2's grid spot {room, x, y, f} of a command (a page loaded before 1.4)."""
    need = _core().need
    rs = {r['id']: r for r in L['rooms']}
    need(p.get('room') in rs, 'Chọn phòng muốn đặt đồ nhé.')
    x, y, f = p.get('x'), p.get('y'), _int(p, 'f', 0)   # flip may come as true/false; a spot never
    need(type(x) is int and type(y) is int and 0 <= x <= XY_MAX and 0 <= y <= XY_MAX, 'Chỗ này không đặt đồ được.')
    need(f in (0, 1), 'Hướng đặt không hợp lệ.')
    return rs[p['room']], x, y, f


def _grid_q(L: dict, k: str, room: dict, x: int, y: int, f: int, skip: str = '') -> dict:
    """A grid cell of an older page as a free spot: a small thing on a cell of a table stands on that table."""
    if ITEMS[k]['spot'] == 'top':
        others = {u: v for u, v in L['pos'].items() if u != skip}
        g = grid_guess(L['rooms'], L['kinds'], others)
        q = from_grid(L['rooms'], {**L['kinds'], '\x00': k}, {**{u: g[u] for u in g if ITEMS[L['kinds'][u]]['spot'] == 'floor'},
                                                               '\x00': (room['id'], x, y, f)})
        return q.get('\x00') or _q(room['id'], x * U, y * U, f)
    return _q(room['id'], x * U, y * U, f)


def _fine(p: dict, L: dict, k: str, uid: str = '') -> dict:
    """A free spot from a command {r, x, y, f[, on][, z]}: shapes checked, numbers clamped into the zone (a drag may
    end a little outside); the rules are checked by _put."""
    need = _core().need
    rs = {r['id']: r for r in L['rooms']}
    need(p.get('r') in rs, 'Chọn phòng muốn đặt đồ nhé.')
    room = rs[p['r']]
    x, y, f, on, z = p.get('x'), p.get('y'), _int(p, 'f', 0), p.get('on') or '', p.get('z')
    need(type(x) is int and type(y) is int and abs(x) <= FREE_MAX and abs(y) <= FREE_MAX, 'Chỗ này không đặt đồ được.')
    need(f in (0, 1), 'Hướng đặt không hợp lệ.')
    need(isinstance(on, str) and (not on or (_ON.match(on) and on != uid)), 'Chỗ này không đặt đồ được.')
    need(z is None or (type(z) is int and 0 <= z <= Z_MAX), 'Thứ tự không hợp lệ.')
    it = ITEMS[k]
    if on:
        others = {u: v for u, v in L['pos'].items() if u != uid}
        h = host_of(room, on, others, L['kinds'])
        need(h is not None and it['spot'] == 'top', why('support', k, room, on, L['kinds']), 'bad_spot')
        x = max(0, min(x, max(0, h['w'] - it['w'] * U)))
        y = max(0, min(y, max(0, h['d'] - it['h'] * U)))
    else:
        zn = zone(room, k)
        if zn is not None and room['type'] in it['rooms']:
            x, y = max(0, min(x, zn[0])), max(0, min(y, zn[1]))
    cur = L['pos'].get(uid)
    if z is None:
        if cur and cur['r'] == room['id']:
            z = cur.get('z', 0)
        else:
            zs = [v.get('z', 0) for u, v in L['pos'].items() if u != uid and v['r'] == room['id']]
            z = min(Z_MAX, max(zs) + 1) if zs else 0
    return _q(room['id'], x, y, f, on, z)


def _put(L: dict, uid: str, q: dict) -> tuple[dict, list, list]:
    """The layout with `uid` at `q`: what stands on it comes along (mirrored with it). (pos, riders moved, riders to
    the bag). Refuses (GameError) when `uid` itself may not stand there."""
    need = _core().need
    kinds = L['kinds']
    rs = {r['id']: r for r in L['rooms']}
    pos = {u: dict(v) for u, v in L['pos'].items()}
    k = kinds[uid]
    cur = pos.pop(uid, None)
    ride = riders(pos, uid)
    for u in ride:
        pos.pop(u)
    room = rs[q['r']]
    bad = check(room, k, q, pos, kinds)
    if bad:
        need(False, why(bad[0], k, room, bad[1], kinds), _code(bad[0]))
    pos[uid] = q
    moved, dropped = [], []
    flip = bool(cur) and cur['f'] != q['f']
    for u in ride:
        v = dict(L['pos'][u])
        if room['type'] in ITEMS[kinds[u]]['rooms']:
            v['r'] = room['id']
            if flip:
                v['x'] = max(0, ITEMS[k]['w'] * U - ITEMS[kinds[u]]['w'] * U - v['x'])
                v['f'] = 1 - v['f']
            pos[u] = v
            moved.append(u)
        else:
            dropped.append(u)
    pos, out = settle_free(L['rooms'], kinds, pos, L['order'])
    need(uid in pos, 'Chỗ này không đặt được.', 'taken')
    dropped += [u for u in out if u != uid]
    moved = [u for u in moved if u in pos]
    return pos, moved, dropped


def _names(kinds: dict, uids: list) -> str:
    return ', '.join(lname(ITEMS[kinds[u]]['name']) for u in uids)


def _host_name(L: dict, room: dict, on: str) -> str:
    if on.startswith('#'):
        return FIX_NAMES.get(on[1:], 'kệ')
    return lname(ITEMS[L['kinds'][on]]['name'])


def _celebrate(before: list, L: dict) -> tuple[list, str]:
    done0 = {x['id'] for x in before if x['done']}
    now = sets_of(L)
    new = [x['id'] for x in now if x['done'] and x['id'] not in done0]
    text = ' '.join(f'🎉 Hoàn thành “{SETS[i]["name"]}”: ấm cúng +{SETS[i]["bonus"]}!' for i in new)
    return new, text


def _same(a: dict | None, b: dict) -> bool:
    return bool(a) and {k: v for k, v in a.items() if k != 'z'} == {k: v for k, v in b.items() if k != 'z'}


def _placed_msg(L: dict, it: dict, was: dict | None, q: dict, room: dict) -> str:
    on = q.get('on')
    if not was:
        return f'Đã đặt {lname(it["name"])} lên {_host_name(L, room, on)}.' if on else f'Đã đặt {lname(it["name"])} ở {lname(room["name"])}.'
    if _same(was, q):
        return f'Đã đưa {lname(it["name"])} lên trên.' if q.get('z', 0) > was.get('z', 0) else f'Đã đưa {lname(it["name"])} xuống dưới.'
    if {k: v for k, v in was.items() if k not in ('f', 'z')} == {k: v for k, v in q.items() if k not in ('f', 'z')}:
        return f'Đã lật {lname(it["name"])}.'
    if was['r'] != q['r']:
        return f'Đã dời {lname(it["name"])} sang {lname(room["name"])}.'
    if on and was.get('on') != on:
        return f'Đã đặt {lname(it["name"])} lên {_host_name(L, room, on)}.'
    return f'Đã dời {lname(it["name"])}.'


def apply(s: dict, name: str, p: dict) -> dict:
    """`jr_deco_*` commands. A refused command changes nothing (engine.apply_action works on a copy)."""
    e = _core()
    need = e.need
    rn = _rn()
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác bày trí không hợp lệ.', 'unknown_action')
    need(j['story'], 'Bày trí phòng chỉ có trong chế độ hành trình.', 'story_only')
    need(p.get('n') is None or (isinstance(p['n'], str) and _NONCE.match(p['n'])), 'Thao tác không hợp lệ.')
    day = j['life_day']
    h = hs.get(s)
    if name in ('jr_deco_buy', 'jr_deco_sell', 'jr_deco_skin') and _seen(get_free(s), p):
        return dict(message='Đã làm rồi nè.', duplicate=True)
    if name == 'jr_deco_buy':
        k = p.get('item')
        need(isinstance(k, str) and k in ITEMS, 'Món này không bán.')
        need(p.get('confirm') is True, 'Xác nhận mua đồ.')
        it = ITEMS[k]
        put, grid = p.get('put'), p.get('room') is not None
        need(put is None or isinstance(put, dict), 'Chỗ này không đặt đồ được.')
        L0 = layout(s)
        if grid:   # a page loaded before 1.4: a grid cell
            room, x, y, f = _target(p, L0)
            q0 = _grid_q(L0, k, room, x, y, f)
        elif put is not None:
            q0 = _fine(put, L0, k)
        if grid or put is not None:   # a second tap of the same purchase: it is already standing there
            there = next((u for u, v in L0['pos'].items() if L0['kinds'][u] == k and _same(v, q0)), None)
            if there:
                return dict(message=f'{it["name"]} đã ở đây rồi.', duplicate=True, uid=there)
        r = rn.ensure_block(s)
        need(len(r['items']) < rn.ITEMS_MAX, f'Bạn đã có {rn.ITEMS_MAX} món đồ. Bán bớt đồ trong túi trước nhé.', 'full')
        rn._pay(s, it['price'], f'Mua {lname(it["name"])} · trang trí', day)
        uid = rn.new_uid(r)
        r['items'].append(dict(id=uid, k=k, r=None, x=None))
        r['stats']['bought'] += 1
        r['spent'] += it['price']
        if h:
            hs._log(h, day, f'Mua {lname(it["name"])} để trang trí.', -it['price'])
        d, D, L = _ensure(s)
        before = sets_of(L)
        msg = f'Đã mua {lname(it["name"])}, {hs._fmt(it["price"])} xu.'
        if grid or put is not None:
            q = _grid_q(L, k, room, x, y, f, uid) if grid else _fine(put, L, k, uid)
            pos, _m, _d = _put(L, uid, q)
            _store(d, D, L, pos)
            d['stats']['placed'] += 1
            rm = next(x for x in L['rooms'] if x['id'] == q['r'])
            msg += f' Đặt lên {_host_name(L, rm, q["on"])} rồi nè!' if q.get('on') else f' Đặt ở {lname(rm["name"])} rồi nè!'
        else:
            msg += ' Nằm trong túi đồ, chạm chỗ trống để đặt nhé.'
        _mark(D, p)
        new, text = _celebrate(before, L)
        return dict(message=f'{msg} {text}'.strip(), uid=uid, sets=new, cozy=points(L)['total'])
    if name == 'jr_deco_skin':
        return _skin(s, p)
    if name == 'jr_deco_layout':   # Hoàn tác: put the pieces back where they were before the last change
        ch = p.get('set')
        need(isinstance(ch, dict) and 1 <= len(ch) <= rn.ITEMS_MAX, 'Không có gì để hoàn tác.')
        d, D, L = _ensure(s)
        before = sets_of(L)
        pos = {u: dict(v) for u, v in L['pos'].items()}
        rs = {r['id']: r for r in L['rooms']}
        grid = {}
        for uid, v in ch.items():
            need(uid in L['kinds'] and L['kinds'][uid] in ITEMS, 'Không tìm thấy món đồ này.')
            if v is None:
                pos.pop(uid, None)
            elif isinstance(v, list):   # 1.3.2: [room, x, y, f] on the grid
                need(len(v) == 4 and v[0] in rs and all(type(n) is int for n in v[1:]) and 0 <= v[1] <= XY_MAX
                     and 0 <= v[2] <= XY_MAX and v[3] in (0, 1), 'Không hoàn tác được.')
                grid[uid] = tuple(v)
                pos.pop(uid, None)
            else:
                need(isinstance(v, dict) and _piece_ok(v) and v['r'] in rs, 'Không hoàn tác được.')
                pos[uid] = _q(v['r'], v['x'], v['y'], v['f'], v.get('on', ''), v.get('z', 0))
        if grid:
            g = grid_guess(L['rooms'], L['kinds'], {u: v for u, v in pos.items() if ITEMS[L['kinds'][u]]['spot'] == 'floor'})
            pos.update({u: q for u, q in from_grid(L['rooms'], L['kinds'], {**g, **grid}).items() if u in grid})
        kept, out = settle_free(L['rooms'], L['kinds'], pos, L['order'])
        need(not out, 'Không hoàn tác được: chỗ cũ giờ không đặt được nữa.', 'taken')
        _store(d, D, L, kept)
        _new, text = _celebrate(before, L)
        return dict(message=f'Đã hoàn tác. {text}'.strip(), cozy=points(L)['total'])
    d, D, L = _ensure(s)
    kinds = L['kinds']
    before = sets_of(L)
    uid = p.get('uid')
    if name == 'jr_deco_pick' and uid == 'all':
        need(L['pos'], 'Chưa có món nào đang bày.', 'nothing')
        n = len(L['pos'])
        _store(d, D, L, {})
        d['stats']['picked'] += n
        return dict(message=f'Đã thu hồi cả {n} món vào túi đồ. Phòng trống trơn, bày lại từ đầu nào!', cozy=0)
    need(isinstance(uid, str) and uid in kinds, 'Không tìm thấy món đồ này.')
    need(kinds[uid] in ITEMS, 'Món đồ này chưa dùng được ở phiên bản này.')
    it = ITEMS[kinds[uid]]
    if name in ('jr_deco_place', 'jr_deco_put'):
        was = L['pos'].get(uid)
        if name == 'jr_deco_place':   # a page loaded before 1.4: a grid cell
            room, x, y, f = _target(p, L)
            q = _grid_q(L, kinds[uid], room, x, y, f, uid)
            if was:
                q['z'] = was.get('z', 0) if was['r'] == q['r'] else q.get('z', 0)
                q = {k2: v for k2, v in q.items() if k2 != 'z' or v}
        else:
            q = _fine(p, L, kinds[uid], uid)
        if was:   # a piece's own looks (optional keys besides on / z) stay with it when it moves
            q.update({k2: was[k2] for k2 in PIECE_OPT if k2 not in ('on', 'z') and k2 in was})
        if was == q:
            return dict(message=f'{it["name"]} đang ở đây rồi.', duplicate=True)
        room = next(x for x in L['rooms'] if x['id'] == q['r'])
        pos, moved, dropped = _put(L, uid, q)
        _store(d, D, L, pos)
        if not was:
            d['stats']['placed'] += 1
        msg = _placed_msg(L, it, was, q, room)
        if moved and not (was and (was['r'], was['x'], was['y'], was.get('on')) == (q['r'], q['x'], q['y'], q.get('on'))):
            msg += f' {_names(kinds, moved).capitalize()} đi theo.'
        if dropped:
            msg += f' {_names(kinds, dropped).capitalize()} vào túi đồ.'
        _new, text = _celebrate(before, L)
        return dict(message=f'{msg} {text}'.strip(), uid=uid, cozy=points(L)['total'])
    if name == 'jr_deco_pick':
        need(uid in L['pos'], f'{it["name"]} đang ở trong túi đồ rồi.', 'nothing')
        ride = riders(L['pos'], uid)
        pos = {u: q for u, q in L['pos'].items() if u != uid and u not in ride}
        _store(d, D, L, pos)
        d['stats']['picked'] += 1 + len(ride)
        extra = f' Kèm {_names(kinds, ride)} bên trên.' if ride else ''
        return dict(message=f'Đã thu hồi {lname(it["name"])} vào túi đồ.{extra}', cozy=points(L)['total'])
    # jr_deco_sell
    need(p.get('confirm') is True, 'Xác nhận bán món đồ.')
    r = rn.get(s)
    ride = riders(L['pos'], uid)
    pos = {u: q for u, q in L['pos'].items() if u != uid and u not in ride}
    r['items'] = [x for x in r['items'] if x['id'] != uid]
    L['kinds'] = {u: k for u, k in kinds.items() if u != uid}
    L['order'] = [u for u in L['order'] if u != uid]
    _store(d, D, L, pos)
    r['stats']['sold'] += 1
    pal = s.get('colors')   # its colour from the palette (game/wardrobe.py, s['colors']['deco'][uid]) goes with it
    if isinstance(pal, dict) and isinstance(pal.get('deco'), dict):
        pal['deco'].pop(uid, None)
    got = sell_price(kinds[uid])
    if got:
        hs._receive(s, got, f'Bán lại {lname(it["name"])}', day)
        if h:
            hs._log(h, day, f'Bán lại {lname(it["name"])}.', got)
    _mark(D, p)
    extra = f' {_names(kinds, ride).capitalize()} vào túi đồ.' if ride else ''
    return dict(message=f'Đã bán lại {lname(it["name"])}, nhận {hs._fmt(got)} xu.{extra}', cozy=points(L)['total'])


def _skin(s: dict, p: dict) -> dict:
    """jr_deco_skin {r, part: 'wall'|'floor', skin[, confirm][, n]}: a wallpaper or a floor for one room; a priced one
    is bought once (confirm) and is yours for every room after."""
    e = _core()
    need = e.need
    rn = _rn()
    j = s['journey']
    L0 = layout(s)
    rs = {r['id']: r for r in L0['rooms']}
    need(p.get('r') in rs, 'Chọn phòng nhé.')
    room = rs[p['r']]
    part, sk = p.get('part'), p.get('skin')
    need(part in ('wall', 'floor') and isinstance(sk, str) and sk in SKINS, 'Kiểu này không có.')
    need(DC.skin_fits(room, sk, part), f'{SKINS[sk]["name"]} không hợp {lname(room["name"])}.', 'bad_spot')
    D0 = get_free(s)
    owned = set(D0['owned']) if D0 is not None else set()
    key = part[0]
    cur = L0['skins'].get(room['id'], {}).get(key, 'auto')
    if cur == sk:
        if room['type'] == 'bunk':
            return dict(message=f'Giường của bạn đang trải {lname(SKINS[sk]["name"])} rồi.', duplicate=True)
        return dict(message=f'{"Tường" if part == "wall" else "Sàn"} {lname(room["name"])} đang là {lname(SKINS[sk]["name"])} rồi.', duplicate=True)
    S = SKINS[sk]
    pay = S['price'] if S['price'] and sk not in owned else 0
    if pay:
        need(p.get('confirm') is True, 'Xác nhận mua.')
        need(len(owned) < OWNED_MAX, 'Không mua thêm được.')
        rn._pay(s, pay, f'Mua {lname(S["name"])} · trang trí', j['life_day'])
        h = hs.get(s)
        if h:
            hs._log(h, j['life_day'], f'Mua {lname(S["name"])} để trang trí.', -pay)
    d, D, L = _ensure(s)
    if pay:
        D['owned'].append(sk)
    sk_room = dict(D['skins'].get(room['id'], {}))
    if sk == 'auto':
        sk_room.pop(key, None)
    else:
        sk_room[key] = sk
    if sk_room:
        D['skins'][room['id']] = sk_room
    else:
        D['skins'].pop(room['id'], None)
    _mark(D, p)
    head = f'Đã mua {lname(S["name"])}, {hs._fmt(pay)} xu. ' if pay else ''
    if room['type'] == 'bunk':
        return dict(message=f'{head}Giường của bạn giờ trải {lname(S["name"])}.', skin=sk)
    what = 'Tường' if part == 'wall' else 'Sàn'
    return dict(message=f'{head}{what} {lname(room["name"])} giờ là {lname(S["name"])}.', skin=sk)


def action(s: dict, name: str, p: dict) -> dict:
    """Entry from journey.action (which runs journey.after and validate_state)."""
    return apply(s, name, p or {})


def legacy(s: dict, name: str, p: dict) -> dict:
    """1.2.0's jr_reno_buy / move / store / sell (a page loaded before this release): the piece goes as near to the
    old slot as it fits, or into the bag."""
    need = _core().need
    L = layout(s)
    rs = {r['id']: r for r in L['rooms']}
    if name == 'jr_reno_store':
        return apply(s, 'jr_deco_pick', dict(uid=p.get('uid')))
    if name == 'jr_reno_sell':
        return apply(s, 'jr_deco_sell', dict(uid=p.get('uid'), confirm=p.get('confirm')))
    k = p.get('item') if name == 'jr_reno_buy' else L['kinds'].get(p.get('uid'))
    need(isinstance(k, str) and k in ITEMS, 'Món này không bán.' if name == 'jr_reno_buy' else 'Không tìm thấy món đồ này.')
    room, slot = rs.get(p.get('room')), p.get('slot')
    need(room is not None, 'Chọn phòng muốn đặt đồ nhé.')
    need(isinstance(slot, str) and len(slot) == 2 and slot[0] in 'wf' and slot[1].isdigit(), 'Chỗ này không đặt đồ được.')
    w, f = _legacy_counts(L['place']['key']).get(room['id'], (0, 0))
    tx, ty = slot_target(room, k, slot, w if slot[0] == 'w' else f)
    skip = {p.get('uid')} if name == 'jr_reno_move' else set()
    grid = to_grid(L['rooms'], L['kinds'], L['pos'], L['order'])
    spot = _near(room, k, tx, ty, _occupancy(L['rooms'], L['kinds'], grid, skip=skip)) if room['type'] in ITEMS[k]['rooms'] else None
    if name == 'jr_reno_buy':
        q = dict(item=k, confirm=p.get('confirm'))
        if spot:
            q.update(room=room['id'], x=spot[0], y=spot[1])
        return apply(s, 'jr_deco_buy', q)
    need(spot, 'Phòng này hết chỗ cho món này rồi.', 'taken')
    return apply(s, 'jr_deco_place', dict(uid=p.get('uid'), room=room['id'], x=spot[0], y=spot[1]))


# ---------------------------------------------------------------- views
def catalogue() -> dict:
    """Static (journey.content()['deco'], sent once at bootstrap)."""
    return dict(items=[dict(id=k, cat=v['cat'], spot=v['spot'], w=v['w'], h=v['h'], price=v['price'], cozy=v['cozy'],
                            rooms=list(v['rooms']), tags=list(v['tags']), surface=v['surface'], ledge=v['ledge'], name=v['name'],
                            emoji=v['emoji'], sell=sell_price(k)) for k, v in ITEMS.items()],
                cats=[dict(id=c, emoji=e, name=n) for c, e, n in DC.CATS],
                sets=[dict(id=k, emoji=v['emoji'], name=v['name'], bonus=v['bonus'], size=len(v['need'])) for k, v in SETS.items()],
                skins=[dict(id=k, part=v['part'], name=v['name'], price=v['price'], types=list(v['types']) if v['types'] else None)
                       for k, v in SKINS.items()],
                levels=[dict(min=low, name=n) for low, n in LEVELS], rent_steps=[dict(min=low, spirit=n) for low, n in RENT_STEPS],
                fix_names=dict(FIX_NAMES), sell_pct=SELL_PCT, guest_min=GUEST_MIN, u=U, z_max=Z_MAX,
                kits={k: _room_view(kit_room(k)) for k in DC.KITS}, no_skin=list(DC.NO_SKIN))


def _place_name(pl: dict) -> tuple[str, str]:
    if pl['where'] == 'attic':
        return hs.ATTIC['emoji'], hs.ATTIC['name']
    H = hs.HOMES[pl['kind']]
    return H['emoji'], H['name']


def _fix_view(f: dict) -> dict:
    P = _ff(f)
    return dict(f, block=bool(P.get('block')), rug=bool(P.get('rug')), allow=list(P.get('allow', ())), top=P.get('top', 0),
                ledge=P.get('ledge', 0), hold=P.get('hold', 0))


def _room_view(x: dict) -> dict:
    return dict(id=x['id'], type=x['type'], emoji=x['emoji'], name=x['name'], cols=x['cols'], wrows=x['wrows'],
                frows=x['frows'], out=x['out'], tags=list(x['tags']), fix=[_fix_view(f) for f in fixtures(x)], cap=room_cap(x))


def public(s: dict) -> dict | None:
    """The room you live in today, ready to set up (None outside story mode)."""
    j = s.get('journey') or {}
    if not j.get('story'):
        return None
    rn = _rn()
    L = layout(s)
    pl = L['place']
    sets = sets_of(L)
    pts = points(L, sets)
    own = pl['where'] == 'own'
    up = rn.upgrade_points(s) if own else 0
    total = pts['total'] + up
    if own:
        steps = [dict(min=low, spirit=n) for low, n in rn.COZY_STEPS]
        perk = rn.perk_of(total)
        off = rn.perk_off(s)
    else:
        steps = [dict(min=low, spirit=n) for low, n in RENT_STEPS]
        perk, off = rent_perk(total), None
    nxt = next((x for x in sorted(steps, key=lambda x: x['min']) if x['min'] > total), None)
    d = get(s)
    D = get_free(s)
    r = rn.get(s)
    emoji, name = _place_name(pl)
    # x, y: the grid cell (what a page loaded before 1.4 draws); fx, fy, on, z: the free spot.
    mirror = grid_guess(L['rooms'], L['kinds'], L['pos'])
    placed = []
    for u, q in L['pos'].items():
        g = mirror.get(u) or (q['r'], 0, 0, q['f'])
        placed.append(dict(id=u, k=L['kinds'][u], r=q['r'], x=g[1], y=g[2], f=q['f'], fx=q['x'], fy=q['y'], on=q.get('on', ''), z=q.get('z', 0)))
    bag = [dict(id=it['id'], k=it['k']) for it in (r['items'] if r else []) if it['id'] not in L['pos'] and it['k'] in ITEMS]
    have = hs._have(s)
    g = guest(s, L, total, j['life_day'])
    stats = dict(d['stats']) if d else {k: 0 for k in STATS}
    owned = [k for k in (D['owned'] if D else []) if k in SKINS]
    skin = lambda x: {k: v for k, v in L['skins'].get(x['id'], {}).items() if v in SKINS}   # noqa: E731
    # `rooms`: the rooms every build draws; `more`: the new ones by their template (catalogue `kits`), which a page
    # loaded before 1.4.11 ignores ({t: kit[, s: its skin]}).
    more = [dict(t=x['kit'], s=skin(x)) if skin(x) else dict(t=x['kit']) for x in L['rooms'] if x.get('new')]
    out = dict(place=dict(key=pl['key'], where=pl['where'], kind=pl['kind'], name=name, emoji=emoji, repairs=own),
               rooms=[dict(_room_view(x), skin=skin(x)) for x in L['rooms'] if not x.get('new')], more=more,
               items=placed, bag=bag, count=len(r['items']) if r else 0, max=rn.ITEMS_MAX, owned=owned,
               cozy=dict(total=total, items=pts['items'], sets=pts['sets'], up=up, level=level_of(total), perk=perk,
                         off=off, steps=steps, next=nxt),
               sets=[x for x in sets if x['done'] or x['possible']], guest=g, stats=stats, tip=stats['placed'] == 0 and not placed,
               ready=have['wallet'] + have['balance'])
    acts = _rx().view(s, L)
    if acts:
        out['relax'] = acts
    fridge = _fr().view(s, L)   # 🧊 game/fridge.py (a page loaded before ignores it)
    if fridge:
        out['fridge'] = fridge
    return out


# ---------------------------------------------------------------- saves
def upgrade(j: dict) -> None:
    """On load: future stats join with 0; pieces sold by an older build leave both layouts; a grid layout this build's
    rooms no longer allow goes back to the bag piece by piece (never lost: the pieces stay in reno.items). The free
    layout is read (and merged with an older build's changes) by layout(), written by the next command."""
    d = j.get('deco') if isinstance(j, dict) else None
    r = j.get('reno') if isinstance(j, dict) else None
    items = r.get('items') if isinstance(r, dict) else None
    kinds = {it['id']: it['k'] for it in items if isinstance(it, dict) and isinstance(it.get('id'), str)} if isinstance(items, list) else {}
    if isinstance(d, dict) and isinstance(d.get('stats'), dict) and isinstance(d.get('pos'), dict):
        for k in STATS:
            d['stats'].setdefault(k, 0)
        pos = {u: v for u, v in d['pos'].items() if u in kinds}
        rooms = rooms_of(d['at']) if isinstance(d.get('at'), str) else None
        if rooms is not None and all(kinds[u] in ITEMS for u in pos):
            shaped = {u: tuple(v) for u, v in pos.items() if isinstance(v, list) and len(v) == 4}
            kept, _out = settle(rooms, kinds, shaped, list(kinds))
            pos = {u: list(kept[u]) for u in pos if u in kept}
        if pos != d['pos']:
            d['pos'] = pos
    D = j.get('decor') if isinstance(j, dict) else None
    if isinstance(D, dict) and isinstance(D.get('items'), dict):
        gone = [u for u in D['items'] if u not in kinds]
        for u in gone:
            D['items'].pop(u)
        for u, v in list(D['items'].items()):   # standing on a piece that was sold: into the bag
            if isinstance(v, dict) and isinstance(v.get('on'), str) and v['on'] and v['on'][0] != '#' and v['on'] not in D['items']:
                D['items'].pop(u)
    X = j.get('decor_new') if isinstance(j, dict) else None
    if isinstance(X, dict) and isinstance(X.get('items'), dict):
        placed = set(D['items']) if isinstance(D, dict) and isinstance(D.get('items'), dict) else set()
        for u in [u for u in X['items'] if u not in kinds or u in placed]:   # sold, or placed by an older build since
            X['items'].pop(u)
        for u, v in list(X['items'].items()):
            if isinstance(v, dict) and isinstance(v.get('on'), str) and v['on'] and v['on'][0] != '#' and v['on'] not in X['items']:
                X['items'].pop(u)
        if not X['items']:
            j.pop('decor_new')


def _piece_ok(v) -> bool:
    """The shape of a placed piece (free units)."""
    if not isinstance(v, dict) or not set(PIECE_KEYS) <= set(v) or not set(v) <= set(PIECE_KEYS) | set(PIECE_OPT):
        return False
    if not (isinstance(v['r'], str) and _ID.match(v['r']) and all(type(v[k]) is int and 0 <= v[k] <= FREE_MAX for k in ('x', 'y'))
            and v['f'] in (0, 1) and type(v['f']) is int):
        return False
    if 'on' in v and not (isinstance(v['on'], str) and _ON.match(v['on'])):
        return False
    if 'z' in v and not (type(v['z']) is int and 0 <= v['z'] <= Z_MAX):
        return False
    return True


def validate(s: dict) -> None:
    e = _core()
    need, integer = e.need, e.integer
    j = s.get('journey')
    if not isinstance(j, dict):
        return
    r = j.get('reno')
    kinds = {it['id']: it['k'] for it in r['items']} if isinstance(r, dict) else {}
    if j.get('deco') is not None:
        d = j['deco']
        bad = 'Dữ liệu bày trí phòng không hợp lệ.'
        need(isinstance(d, dict) and set(d) == {'v', 'at', 'day', 'pos', 'stats'} and d['v'] == VERSION, bad, 'invalid_save')
        need(isinstance(d['at'], str) and _KEY.match(d['at']), bad)
        integer(d['day'], 1, 10**6)
        need(d['day'] <= j['life_day'], bad)
        need(isinstance(d['stats'], dict) and set(d['stats']) == set(STATS), bad)
        for v in d['stats'].values():
            integer(v, 0, 10**9)
        pos = d['pos']
        need(isinstance(pos, dict) and len(pos) <= _rn().ITEMS_MAX, bad)
        for uid, v in pos.items():
            need(uid in kinds, bad)
            need(isinstance(v, list) and len(v) == 4 and isinstance(v[0], str) and _ID.match(v[0])
                 and all(type(n) is int for n in v[1:]) and 0 <= v[1] <= XY_MAX and 0 <= v[2] <= XY_MAX and v[3] in (0, 1), bad)
        rooms = rooms_of(d['at'])
        if rooms is not None and all(kinds[u] in ITEMS for u in pos):   # a newer build's pieces or place: shape only
            _kept, out = settle(rooms, kinds, {u: tuple(v) for u, v in pos.items()}, list(kinds))
            need(not out, bad)
    if j.get('decor') is not None:
        D = j['decor']
        bad = 'Dữ liệu bày trí phòng không hợp lệ.'
        need(isinstance(D, dict) and set(D) == FREE_KEYS and D['v'] == FREE_VERSION, bad, 'invalid_save')
        need(isinstance(D['at'], str) and _KEY.match(D['at']), bad)
        integer(D['sig'], 0, 2**32 - 1)
        need(isinstance(D['items'], dict) and len(D['items']) <= _rn().ITEMS_MAX, bad)
        for uid, v in D['items'].items():
            need(uid in kinds and _piece_ok(v), bad)
        need(isinstance(D['skins'], dict) and len(D['skins']) <= 16, bad)
        for rm, v in D['skins'].items():
            need(isinstance(rm, str) and _ID.match(rm) and isinstance(v, dict) and set(v) <= {'w', 'f'}
                 and all(isinstance(x, str) and _SKIN.match(x) for x in v.values()), bad)
        need(isinstance(D['owned'], list) and len(D['owned']) <= OWNED_MAX and len(set(D['owned'])) == len(D['owned'])
             and all(isinstance(x, str) and _SKIN.match(x) for x in D['owned']), bad)
        need(isinstance(D['ops'], list) and len(D['ops']) <= OPS_MAX and all(isinstance(x, str) and _NONCE.match(x) for x in D['ops']), bad)
        rooms = rooms_of(D['at'])
        if rooms is not None and all(kinds[u] in ITEMS for u in D['items']):   # a newer build's pieces or place: shape only
            new = {r['id'] for r in rooms if r.get('new')}
            need(not any(v['r'] in new for v in D['items'].values()), bad)
            _kept, out = settle_free(rooms, kinds, D['items'], list(kinds))
            need(not out, bad)
    if j.get('decor_new') is not None:
        X = j['decor_new']
        bad = 'Dữ liệu bày trí phòng không hợp lệ.'
        need(isinstance(X, dict) and set(X) == NEW_KEYS and X['v'] == NEW_VERSION, bad, 'invalid_save')
        need(isinstance(X['at'], str) and _KEY.match(X['at']), bad)
        need(isinstance(X['items'], dict) and 0 < len(X['items']) <= _rn().ITEMS_MAX, bad)
        D = j.get('decor')
        placed = set(D['items']) if isinstance(D, dict) else set()
        for uid, v in X['items'].items():
            need(uid in kinds and uid not in placed and _piece_ok(v), bad)
        rooms = rooms_of(X['at'])
        if rooms is not None and all(kinds[u] in ITEMS for u in X['items']):
            new = {r['id'] for r in rooms if r.get('new')}
            need(all(v['r'] in new for v in X['items'].values()), bad)
            _kept, out = settle_free(rooms, kinds, X['items'], list(kinds))
            need(not out, bad)
