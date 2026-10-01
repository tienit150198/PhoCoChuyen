"""🪴 Bày trí phòng: set up the room you live in, one piece at a time (story mode).

Every place can be set up: a home you own (game/reno.py adds its repairs and upgrades), your spouse's home, a rented
room (Phòng trọ khép kín: the room and its gác lửng; Ký túc xá Hẻm 7: only your bunk corner) and Bà Tám's attic.
Rooms are grids (deco_content: walls, floor, the fixtures that block cells); public/js/v4/reno.js draws them and the
furniture, and the player places each piece by tapping or dragging.

Furniture belongs to the player, not to the home: it is the list `journey.reno.items` (ids, kinds) that 1.2.0 began.
Where each piece stands is `journey.deco.pos` {uid: [room, x, y, flip]} for the place `journey.deco.at`. Moving out,
switching rooms or buying a home puts everything back in the túi đồ (the bag) and the player sets it up again at
the new place. Thu hồi (pick up) is free; selling back pays SELL_PCT % (as 1.2.0).

Rules of a layout (check/fit, mirrored in reno.js for the live preview, always checked here): inside the room; a
wall piece on the wall, the rest on the floor; the room type suits the piece; nothing on the cells of a fixture (the
door, the window…); no two pieces on one cell of the same layer, except that rugs lie under furniture, and a small
'top' piece stands on a free floor cell or on a surface (a table, a shelf, a bed, the kitchen counter). Moving a
surface carries what stands on it; picking it up puts those in the bag too.

Ấm cúng (points): each distinct kind placed counts its cozy once, plus each theme set completed in one room (SETS),
plus the home's upgrades (reno.COZY_LV a level, own home only). The morning bonus: a home you own keeps 1.2.0's
steps (reno.COZY_STEPS: +1 from 10, +2 from 24, with the parts at COZY_COND % and no late mortgage, paid by
reno.on_life_day); any other place gives RENT_STEPS (+1 from 10, never more: a rented corner should not beat owning
a home). On some days a neighbour drops by and praises the room (GUEST_*: a line, nothing else).

Save: `journey.deco` is absent until the first jr_deco_* command; a 1.2.0 layout (reno items with a room and slot)
is read as positions near the old slots (`_legacy`) and written there by that first command. Older builds ignore
`journey.deco` (journey.validate allows extra keys) and the reno block keeps its 1.2.0 shape, so a rollback only
shows the pieces in the 1.2.0 kho. Deterministic: the neighbour's visit is seeded by the journey seed and the day.
"""
from __future__ import annotations

import random
import re

from . import deco_content as DC
from . import housing as hs

VERSION = 1
COMMANDS = ('jr_deco_buy', 'jr_deco_place', 'jr_deco_pick', 'jr_deco_sell', 'jr_deco_layout')
STATS = ('placed', 'picked', 'guests', 'cozy_days', 'spirit', 'best')
ITEMS = DC.ITEMS
SETS = DC.SETS
SELL_PCT = 50
RENT_STEPS = ((10, 1),)            # tinh thần each morning outside a home you own: +1 at most
GUEST_MIN = 14                     # Ấm cúng from which a neighbour may drop by
GUEST_ODDS = 3                     # one day in three (seeded)
LEVELS = ((40, 'Tổ ấm trong mơ'), (24, 'Rất ấm cúng'), (10, 'Ấm cúng'), (5, 'Dễ thương'), (0, 'Còn trống trải'))
CATCHUP = 400
XY_MAX = 15
LAYER_RANK = {'rug': 0, 'wall': 1, 'floor': 2, 'top': 3}
_ID = re.compile(r'^[a-z0-9_]{1,24}$')
_KEY = re.compile(r'^[a-z0-9_:]{1,48}$')


def _rn():
    from . import reno
    return reno


def _core():
    from . import engine
    return engine


def layer_of(k: str) -> str:
    return ITEMS[k]['spot']


def lname(s: str) -> str:
    return s[:1].lower() + s[1:]


def sell_price(k: str) -> int:
    return ITEMS[k]['price'] * SELL_PCT // 100


def get(s: dict) -> dict | None:
    j = s.get('journey')
    d = j.get('deco') if isinstance(j, dict) else None
    return d if isinstance(d, dict) else None


def blank(day: int, at: str) -> dict:
    return dict(v=VERSION, at=at, day=int(day), pos={}, stats={k: 0 for k in STATS})


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


def rooms_of(key: str) -> list | None:
    """The rooms of the place `key` (None: a place this build does not know). Shared, never changed."""
    if key in _ROOMS:
        return _ROOMS[key]
    bits = key.split(':')
    out = None
    if key == 'attic':
        out = list(DC.RENT_ROOMS['attic'])
    elif bits[0] == 'rent' and len(bits) == 3 and bits[1] in DC.RENT_ROOMS:
        out = list(DC.RENT_ROOMS[bits[1]])
    elif bits[0] in ('own', 'shared') and bits[-1] in _rn().HOUSES:
        out = [DC.own_room(*row) for row in _rn().HOUSES[bits[-1]]['rooms']]
    if out is not None and len(_ROOMS) < 64:
        _ROOMS[key] = out
    return out


# ---------------------------------------------------------------- the rules of a layout
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
    """Can a piece of kind `k` stand at (x, y) of `room` among the others (`occ`, itself left out)?
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
    """Keep what stands where it may, in order (rugs, walls, floor, then small things): (kept, the uids left out)."""
    seq = {u: (i, kinds.get(u)) for i, u in enumerate(order)}
    for u in pos:
        seq.setdefault(u, (len(seq), kinds.get(u)))
    rs = {r['id']: r for r in rooms}
    kept, out = {}, []
    occ = _occupancy(rooms, kinds, {})
    for uid in _order(pos, seq):
        room, x, y, f = pos[uid]
        k = kinds.get(uid)
        if k not in ITEMS or room not in rs or f not in (0, 1) or fit(rs[room], k, x, y, occ):
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


def riders(rooms: list, kinds: dict, pos: dict, uid: str) -> list:
    """The small things standing on the surface `uid` (none when it is not a surface on the floor)."""
    if uid not in pos or kinds.get(uid) not in ITEMS:
        return []
    it = ITEMS[kinds[uid]]
    if it['spot'] != 'floor' or not it['surface']:
        return []
    room, x, y, _f = pos[uid]
    cells = set(_cells(x, y, it['w'], it['h']))
    return [u for u, (r, ux, uy, _g) in pos.items() if u != uid and r == room and kinds.get(u) in ITEMS
            and ITEMS[kinds[u]]['spot'] == 'top' and (ux, uy) in cells]


# ---------------------------------------------------------------- the 1.2.0 slots
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


# ---------------------------------------------------------------- the layout as it stands today
def layout(s: dict) -> dict:
    """Today's layout without writing anything: place, rooms, kinds {uid: k}, order, pos {uid: (room, x, y, f)}."""
    j = s['journey']
    pl = place(j)
    rooms = rooms_of(pl['key']) or []
    r = _rn().get(s)
    items = r['items'] if r else []
    kinds = {it['id']: it['k'] for it in items}
    order = [it['id'] for it in items]
    d = get(s)
    pos = {}
    if d is not None and d['at'] == pl['key']:
        pos = {u: tuple(v) for u, v in d['pos'].items() if u in kinds}
    if r and pl['where'] == 'own' and r['hid'] == j['home']['own']['id']:
        pos = _legacy(r, rooms, kinds, pos, pl['key'])
    pos, _ = settle(rooms, kinds, pos, order)
    return dict(place=pl, rooms=rooms, kinds=kinds, order=order, pos=pos)


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
    for u, (room, *_rest) in L['pos'].items():
        by_room.setdefault(room, []).append((u, L['kinds'][u]))
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
    if d['at'] != pl['key']:
        if d['pos']:
            notes.append('📦 Chuyển chỗ ở rồi: đồ trang trí đã gói vào túi đồ, vào bày lại phòng mới nhé!')
        d['at'], d['pos'] = pl['key'], {}
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
    'support': '{it} chỉ đặt lên bàn, kệ, giường hoặc sàn trống thôi: {other} không đỡ được.',
    'fixture': 'Chỗ này vướng {other}.',
}
FIX_NAMES = {'door': 'cửa ra vào', 'window': 'cửa sổ', 'counter': 'kệ bếp', 'splash': 'tường bếp', 'slope': 'mái gác',
             'ladder': 'cầu thang', 'pillow': 'cái gối'}


def why(code: str, k: str, room: dict, other: str, kinds: dict) -> str:
    it = ITEMS[k]['name']
    o = FIX_NAMES.get(other[1:], 'chỗ cố định') if other.startswith('#') else lname(ITEMS[kinds[other]]['name']) if kinds.get(other) in ITEMS else 'món khác'
    return _WHY[code].format(it=it, it_l=lname(it), room=room['name'], room_l=lname(room['name']), other=o)


def _ensure(s: dict) -> tuple[dict, dict]:
    """The block for commands, following the player home; 1.2.0 slots become positions (and leave the reno items)."""
    j = s['journey']
    L = layout(s)
    d = get(s)
    if d is None:
        d = j['deco'] = blank(j['life_day'], L['place']['key'])
    d['at'] = L['place']['key']
    d['pos'] = {u: list(p) for u, p in L['pos'].items()}
    r = _rn().get(s)
    for it in (r['items'] if r else []):
        it['r'] = it['x'] = None
    return d, L


def _store(d: dict, L: dict, pos: dict) -> None:
    d['pos'] = {u: list(pos[u]) for u in L['order'] if u in pos}
    L['pos'] = {u: tuple(v) for u, v in d['pos'].items()}
    d['stats']['best'] = max(d['stats']['best'], points(L)['total'])


def _int(p: dict, key: str, default=None):
    v = p.get(key, default)
    if type(v) is bool:
        v = int(v)
    return v


def _target(p: dict, L: dict) -> tuple[dict, int, int, int]:
    need = _core().need
    rs = {r['id']: r for r in L['rooms']}
    need(p.get('room') in rs, 'Chọn phòng muốn đặt đồ nhé.')
    x, y, f = p.get('x'), p.get('y'), _int(p, 'f', 0)   # flip may come as true/false; a spot never
    need(type(x) is int and type(y) is int and 0 <= x <= XY_MAX and 0 <= y <= XY_MAX, 'Chỗ này không đặt đồ được.')
    need(f in (0, 1), 'Hướng đặt không hợp lệ.')
    return rs[p['room']], x, y, f


def _put(L: dict, uid: str, room: dict, x: int, y: int, f: int) -> tuple[dict, list, list]:
    """The layout with `uid` at (room, x, y, f): what stands on it comes along. (pos, riders moved, riders to the bag).
    Refuses (GameError) when `uid` itself does not fit there."""
    need = _core().need
    kinds, pos = L['kinds'], dict(L['pos'])
    k = kinds[uid]
    ride = riders(L['rooms'], kinds, pos, uid)
    cur = pos.get(uid)
    occ = _occupancy(L['rooms'], kinds, pos, skip={uid, *ride})
    bad = fit(room, k, x, y, occ)
    if bad:
        need(False, why(bad[0], k, room, bad[1], kinds), 'taken' if bad[0] in ('taken', 'covers', 'fixture') else 'bad_spot')
    for u in ride:
        pos.pop(u)
    pos.pop(uid, None)
    pos[uid] = (room['id'], x, y, f)
    moved, dropped = [], []
    for u in ride:
        _r, ux, uy, uf = L['pos'][u]
        nx, ny = ux - cur[1] + x, uy - cur[2] + y
        if room['type'] in ITEMS[kinds[u]]['rooms']:
            pos[u] = (room['id'], nx, ny, uf)
            moved.append(u)
        else:
            dropped.append(u)
    pos, out = settle(L['rooms'], kinds, pos, L['order'])
    need(uid in pos, 'Chỗ này không đặt được.', 'taken')
    dropped += [u for u in out if u != uid]
    moved = [u for u in moved if u in pos]
    return pos, moved, dropped


def _names(kinds: dict, uids: list) -> str:
    return ', '.join(lname(ITEMS[kinds[u]]['name']) for u in uids)


def _celebrate(before: list, L: dict) -> tuple[list, str]:
    done0 = {x['id'] for x in before if x['done']}
    now = sets_of(L)
    new = [x['id'] for x in now if x['done'] and x['id'] not in done0]
    text = ' '.join(f'🎉 Hoàn thành “{SETS[i]["name"]}”: ấm cúng +{SETS[i]["bonus"]}!' for i in new)
    return new, text


def apply(s: dict, name: str, p: dict) -> dict:
    """`jr_deco_*` commands. A refused command changes nothing (engine.apply_action works on a copy)."""
    e = _core()
    need = e.need
    rn = _rn()
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác bày trí không hợp lệ.', 'unknown_action')
    need(j['story'], 'Bày trí phòng chỉ có trong chế độ hành trình.', 'story_only')
    day = j['life_day']
    h = hs.get(s)
    if name == 'jr_deco_buy':
        k = p.get('item')
        need(isinstance(k, str) and k in ITEMS, 'Món này không bán.')
        need(p.get('confirm') is True, 'Xác nhận mua đồ.')
        it = ITEMS[k]
        want = p.get('room') is not None
        if want:   # a second tap of the same purchase: it is already standing there
            L0 = layout(s)
            room, x, y, f = _target(p, L0)
            there = next((u for u, q in L0['pos'].items() if q[:3] == (room['id'], x, y) and L0['kinds'][u] == k), None)
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
        d, L = _ensure(s)
        before = sets_of(L)
        msg = f'Đã mua {lname(it["name"])}, {hs._fmt(it["price"])} xu.'
        if want:
            room, x, y, f = _target(p, L)
            pos, _m, _d = _put(L, uid, room, x, y, f)
            _store(d, L, pos)
            d['stats']['placed'] += 1
            msg += f' Đặt ở {lname(room["name"])} rồi nè!'
        else:
            msg += ' Nằm trong túi đồ, chạm chỗ trống để đặt nhé.'
        new, text = _celebrate(before, L)
        return dict(message=f'{msg} {text}'.strip(), uid=uid, sets=new, cozy=points(L)['total'])
    if name == 'jr_deco_layout':   # Hoàn tác: put the pieces back where they were before the last change
        ch = p.get('set')
        need(isinstance(ch, dict) and 1 <= len(ch) <= rn.ITEMS_MAX, 'Không có gì để hoàn tác.')
        d, L = _ensure(s)
        before = sets_of(L)
        pos = dict(L['pos'])
        rs = {r['id']: r for r in L['rooms']}
        for uid, v in ch.items():
            need(uid in L['kinds'] and L['kinds'][uid] in ITEMS, 'Không tìm thấy món đồ này.')
            if v is None:
                pos.pop(uid, None)
                continue
            need(isinstance(v, list) and len(v) == 4 and v[0] in rs and all(type(n) is int for n in v[1:]) and v[3] in (0, 1),
                 'Không hoàn tác được.')
            pos[uid] = tuple(v)
        kept, out = settle(L['rooms'], L['kinds'], pos, L['order'])
        need(not out, 'Không hoàn tác được: chỗ cũ giờ đã có đồ khác.', 'taken')
        _store(d, L, kept)
        _new, text = _celebrate(before, L)
        return dict(message=f'Đã hoàn tác. {text}'.strip(), cozy=points(L)['total'])
    d, L = _ensure(s)
    kinds = L['kinds']
    before = sets_of(L)
    uid = p.get('uid')
    if name == 'jr_deco_pick' and uid == 'all':
        need(L['pos'], 'Chưa có món nào đang bày.', 'nothing')
        n = len(L['pos'])
        _store(d, L, {})
        d['stats']['picked'] += n
        return dict(message=f'Đã thu hồi cả {n} món vào túi đồ. Phòng trống trơn, bày lại từ đầu nào!', cozy=0)
    need(isinstance(uid, str) and uid in kinds, 'Không tìm thấy món đồ này.')
    need(kinds[uid] in ITEMS, 'Món đồ này chưa dùng được ở phiên bản này.')
    it = ITEMS[kinds[uid]]
    if name == 'jr_deco_place':
        room, x, y, f = _target(p, L)
        if L['pos'].get(uid) == (room['id'], x, y, f):
            return dict(message=f'{it["name"]} đang ở đây rồi.', duplicate=True)
        was = L['pos'].get(uid)
        pos, moved, dropped = _put(L, uid, room, x, y, f)
        _store(d, L, pos)
        if not was:
            d['stats']['placed'] += 1
            msg = f'Đã đặt {lname(it["name"])} ở {lname(room["name"])}.'
        elif was[:3] == (room['id'], x, y):
            msg = f'Đã lật {lname(it["name"])}.'
        elif was[0] != room['id']:
            msg = f'Đã dời {lname(it["name"])} sang {lname(room["name"])}.'
        else:
            msg = f'Đã dời {lname(it["name"])}.'
        if moved:
            msg += f' {_names(kinds, moved).capitalize()} đi theo.'
        if dropped:
            msg += f' {_names(kinds, dropped).capitalize()} vào túi đồ.'
        _new, text = _celebrate(before, L)
        return dict(message=f'{msg} {text}'.strip(), uid=uid, cozy=points(L)['total'])
    if name == 'jr_deco_pick':
        need(uid in L['pos'], f'{it["name"]} đang ở trong túi đồ rồi.', 'nothing')
        ride = riders(L['rooms'], kinds, L['pos'], uid)
        pos = {u: q for u, q in L['pos'].items() if u != uid and u not in ride}
        _store(d, L, pos)
        d['stats']['picked'] += 1 + len(ride)
        extra = f' Kèm {_names(kinds, ride)} bên trên.' if ride else ''
        return dict(message=f'Đã thu hồi {lname(it["name"])} vào túi đồ.{extra}', cozy=points(L)['total'])
    # jr_deco_sell
    need(p.get('confirm') is True, 'Xác nhận bán món đồ.')
    r = rn.get(s)
    ride = riders(L['rooms'], kinds, L['pos'], uid)
    pos = {u: q for u, q in L['pos'].items() if u != uid and u not in ride}
    r['items'] = [x for x in r['items'] if x['id'] != uid]
    L['kinds'] = {u: k for u, k in kinds.items() if u != uid}
    L['order'] = [u for u in L['order'] if u != uid]
    _store(d, L, pos)
    r['stats']['sold'] += 1
    got = sell_price(kinds[uid])
    if got:
        hs._receive(s, got, f'Bán lại {lname(it["name"])}', day)
        if h:
            hs._log(h, day, f'Bán lại {lname(it["name"])}.', got)
    extra = f' {_names(kinds, ride).capitalize()} vào túi đồ.' if ride else ''
    return dict(message=f'Đã bán lại {lname(it["name"])}, nhận {hs._fmt(got)} xu.{extra}', cozy=points(L)['total'])


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
    spot = _near(room, k, tx, ty, _occupancy(L['rooms'], L['kinds'], L['pos'], skip=skip)) if room['type'] in ITEMS[k]['rooms'] else None
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
                            rooms=list(v['rooms']), tags=list(v['tags']), surface=v['surface'], name=v['name'], emoji=v['emoji'],
                            sell=sell_price(k)) for k, v in ITEMS.items()],
                cats=[dict(id=c, emoji=e, name=n) for c, e, n in DC.CATS],
                sets=[dict(id=k, emoji=v['emoji'], name=v['name'], bonus=v['bonus'], size=len(v['need'])) for k, v in SETS.items()],
                levels=[dict(min=low, name=n) for low, n in LEVELS], rent_steps=[dict(min=low, spirit=n) for low, n in RENT_STEPS],
                fix_names=dict(FIX_NAMES), sell_pct=SELL_PCT, guest_min=GUEST_MIN)


def _place_name(pl: dict) -> tuple[str, str]:
    if pl['where'] == 'attic':
        return hs.ATTIC['emoji'], hs.ATTIC['name']
    H = hs.HOMES[pl['kind']]
    return H['emoji'], H['name']


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
    r = rn.get(s)
    emoji, name = _place_name(pl)
    placed = [dict(id=u, k=L['kinds'][u], r=q[0], x=q[1], y=q[2], f=q[3]) for u, q in L['pos'].items()]
    bag = [dict(id=it['id'], k=it['k']) for it in (r['items'] if r else []) if it['id'] not in L['pos'] and it['k'] in ITEMS]
    have = hs._have(s)
    g = guest(s, L, total, j['life_day'])
    stats = dict(d['stats']) if d else {k: 0 for k in STATS}
    return dict(place=dict(key=pl['key'], where=pl['where'], kind=pl['kind'], name=name, emoji=emoji, repairs=own),
                rooms=[dict(id=x['id'], type=x['type'], emoji=x['emoji'], name=x['name'], cols=x['cols'], wrows=x['wrows'],
                            frows=x['frows'], out=x['out'], tags=list(x['tags']), fix=[dict(f) for f in x['fix']]) for x in L['rooms']],
                items=placed, bag=bag, count=len(r['items']) if r else 0, max=rn.ITEMS_MAX,
                cozy=dict(total=total, items=pts['items'], sets=pts['sets'], up=up, level=level_of(total), perk=perk,
                          off=off, steps=steps, next=nxt),
                sets=[x for x in sets if x['done'] or x['possible']], guest=g, stats=stats, tip=stats['placed'] == 0 and not placed,
                ready=have['wallet'] + have['balance'])


# ---------------------------------------------------------------- saves
def upgrade(j: dict) -> None:
    """On load: future stats join with 0; pieces sold by an older build leave the layout; a layout this build's
    rooms no longer allow goes back to the bag piece by piece (never lost: the pieces stay in reno.items)."""
    d = j.get('deco') if isinstance(j, dict) else None
    if not isinstance(d, dict) or not isinstance(d.get('stats'), dict) or not isinstance(d.get('pos'), dict):
        return
    for k in STATS:
        d['stats'].setdefault(k, 0)
    r = j.get('reno')
    items = r.get('items') if isinstance(r, dict) else None
    kinds = {it['id']: it['k'] for it in items if isinstance(it, dict) and isinstance(it.get('id'), str)} if isinstance(items, list) else {}
    pos = {u: v for u, v in d['pos'].items() if u in kinds}
    rooms = rooms_of(d['at']) if isinstance(d.get('at'), str) else None
    if rooms is not None and all(kinds[u] in ITEMS for u in pos):
        shaped = {u: tuple(v) for u, v in pos.items() if isinstance(v, list) and len(v) == 4}
        kept, _out = settle(rooms, kinds, shaped, list(kinds))
        pos = {u: list(kept[u]) for u in pos if u in kept}
    if pos != d['pos']:
        d['pos'] = pos


def validate(s: dict) -> None:
    e = _core()
    need, integer = e.need, e.integer
    j = s.get('journey')
    if not isinstance(j, dict) or j.get('deco') is None:
        return
    d = j['deco']
    bad = 'Dữ liệu bày trí phòng không hợp lệ.'
    need(isinstance(d, dict) and set(d) == {'v', 'at', 'day', 'pos', 'stats'} and d['v'] == VERSION, bad, 'invalid_save')
    need(isinstance(d['at'], str) and _KEY.match(d['at']), bad)
    integer(d['day'], 1, 10**6)
    need(d['day'] <= j['life_day'], bad)
    need(isinstance(d['stats'], dict) and set(d['stats']) == set(STATS), bad)
    for v in d['stats'].values():
        integer(v, 0, 10**9)
    r = j.get('reno')
    kinds = {it['id']: it['k'] for it in r['items']} if isinstance(r, dict) else {}
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
