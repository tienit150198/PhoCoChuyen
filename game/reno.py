"""🛠️ Sửa và trang trí nhà: the inside of a home the player owns (game/housing.py `own`), story mode only.

Vào xem nhà: each home has rooms (LAYOUT per home kind, room names in ROOMS) that public/js/v4/reno.js draws
with the condition of five parts (PARTS: tường, trần mái, sàn, điện nước, bếp) and the furniture placed there.

Sửa nhà: a part's condition (0–100) wears one point every WEAR_DAYS[level] life days, never below COND_MIN, so a
home left alone only looks tired. A repair brings it back to 100 for FIX_BASE xu per 100 points, scaled by the
home's size (SIZE %). Upgrades (UPGRADES, two levels per part) renew the part, wear slower and add to Ấm cúng.

Trang trí: since 1.3 game/deco.py (Bày trí phòng) places the furniture on a grid in every place you live, rented
rooms too. The furniture itself (what the player owns) is still the list `items` of this block, so the block now
also exists for a player without a home (hid None, no parts). 1.2.0 kept a room and a slot per piece (`r`, `x`);
deco.py reads those as grid positions and clears them, and the 1.2.0 commands jr_reno_buy/move/store/sell still
work through deco.legacy. When the home is sold the next home starts with its own condition and no upgrades.
Since several homes (housing.py VERSION 2) the block follows the home you live in; moving to another home you own
hands the parts of the one you leave to housing.py (leave_home: kept on that home) and brings them back when you
return (enter_home), so repairs and upgrades are never lost by moving.

Ấm cúng: the decor points (deco.decor_points: each distinct kind placed + the theme sets) + COZY_LV per upgrade
level. From COZY_STEPS it adds +1 / +2 tinh thần each morning (on top of the home's own comfort) while the parts
average at least COZY_COND % and the mortgage is not late. Nothing here ever takes tinh thần or money away by itself.

Money: housing._have/_take, like buying the home (the bank account first, then cash; wallet rows of kind
'home', which every build accepts); furniture sold back goes through housing._receive (deco.py). Each spend writes one
line in the home's own log (Sổ nhà cửa).

Save: `s['journey']['reno']`, absent until the first jr_reno_* command or the first piece of furniture bought
(deco.py; older saves are never touched; the view of a home nobody has worked on is computed, not stored). journey.validate allows
extra journey keys, so an older build simply ignores the block. Ids below are stored in saves: never rename.
Deterministic: nothing here is random.
"""
from __future__ import annotations

import re

from . import deco_content as DC
from . import housing as hs
from .jsoncopy import tree_copy

VERSION = 1
COMMANDS = ('jr_reno_fix', 'jr_reno_up', 'jr_reno_buy', 'jr_reno_move', 'jr_reno_store', 'jr_reno_sell')
STATS = ('fixed', 'upgraded', 'bought', 'sold', 'cozy_days', 'spirit')
ITEMS_MAX = 60                     # furniture owned (placed + bag): 1.2.0 builds refuse more
COND_MIN = 30                      # wear stops here: tired, never ruined
WEAR_DAYS = (4, 6, 8)              # life days per point of wear, by upgrade level
WORN_AT = 60                       # below this the drawing shows the flaw and the morning says so once
FIX_MIN = 5
SELL_PCT = 50
COZY_LV = 2                        # Ấm cúng per upgrade level
COZY_STEPS = ((24, 2), (10, 1))    # Ấm cúng from → tinh thần each morning
COZY_COND = 50                     # the parts' average condition the bonus needs
CATCHUP = 400                      # life days caught up at most in one go (as housing.on_life_day)

# Parts: id, emoji, name, flaw when worn, repair price per 100 points at SIZE 100, upgrades (name, price at SIZE 100).
PARTS = {
    'wall': dict(emoji='🧱', name='Tường', flaw='Tường bong tróc, ố vàng', fix=120,
                 up=(('Sơn lại tường', 120), ('Giấy dán tường, ốp gỗ', 300))),
    'roof': dict(emoji='☂️', name='Trần, mái', flaw='Trần thấm dột', fix=150,
                 up=(('Chống thấm trần', 150), ('Trần cách nhiệt', 360))),
    'floor': dict(emoji='🪵', name='Sàn', flaw='Sàn nứt, bong gạch', fix=130,
                  up=(('Lát gạch men mới', 180), ('Lát sàn gỗ', 420))),
    'power': dict(emoji='💡', name='Điện nước', flaw='Điện chập chờn, ống nước rỉ', fix=100,
                  up=(('Đi lại dây điện, ống nước', 120), ('Bình nóng lạnh, đèn LED', 280))),
    'kitchen': dict(emoji='🍲', name='Bếp', flaw='Bếp cũ, ám khói', fix=90,
                    up=(('Bếp ga mới, kệ bếp', 140), ('Tủ bếp trọn bộ, máy hút mùi', 340))),
}
PART_IDS = tuple(PARTS)
LV_MAX = 2

ROOMS = {'living': ('🛋️', 'Phòng khách'), 'bed': ('🛏️', 'Phòng ngủ'), 'bed2': ('🧸', 'Phòng ngủ nhỏ'),
         'kitchen': ('🍲', 'Bếp'), 'balcony': ('🌤️', 'Ban công'), 'yard': ('🌳', 'Sân vườn')}
OUTDOOR = ('balcony', 'yard')
INDOOR = ('living', 'bed', 'bed2', 'kitchen')

# Per home: size (% of the base prices: the tập thể is 35 m², a riverside villa many times that), how worn it is the
# day it is bought (condition %), and its rooms: (room, wall slots, floor slots[, its own name]).
HOUSES = {
    'tap_the': dict(size=70, start=55, rooms=(('living', 2, 3), ('bed', 2, 3), ('kitchen', 1, 2))),
    'can_ho_studio': dict(size=60, start=90, rooms=(('living', 2, 3), ('bed', 1, 2, 'Góc ngủ'), ('kitchen', 1, 2))),
    'can_ho_mini': dict(size=65, start=82, rooms=(('living', 2, 3), ('bed', 2, 3), ('kitchen', 1, 2), ('balcony', 0, 2))),
    'can_ho_1pn': dict(size=90, start=88, rooms=(('living', 3, 4), ('bed', 2, 3), ('kitchen', 2, 3), ('balcony', 0, 2))),
    'can_ho_2pn': dict(size=120, start=90, rooms=(('living', 3, 4), ('bed', 2, 3), ('bed2', 2, 3), ('kitchen', 2, 3), ('balcony', 0, 3))),
    'penthouse': dict(size=180, start=95, rooms=(('living', 3, 5), ('bed', 3, 4), ('bed2', 2, 3), ('kitchen', 2, 3), ('balcony', 0, 4, 'Sân thượng'))),
    'nha_pho': dict(size=110, start=72, rooms=(('living', 3, 4), ('bed', 2, 3), ('kitchen', 2, 3), ('balcony', 0, 2))),
    'nha_san': dict(size=140, start=70, rooms=(('living', 3, 4), ('bed', 2, 3), ('bed2', 2, 3), ('kitchen', 2, 3), ('yard', 0, 4, 'Sân trước'))),
    'biet_thu_vuon': dict(size=240, start=85, rooms=(('living', 3, 5), ('bed', 3, 4), ('bed2', 2, 3), ('kitchen', 2, 3), ('yard', 0, 5, 'Vườn cau'))),
    'biet_thu_song': dict(size=320, start=92, rooms=(('living', 3, 5), ('bed', 3, 4), ('bed2', 3, 4), ('kitchen', 2, 4), ('yard', 0, 5, 'Sân hồ bơi'))),
}
# A part's start against the home's: the kitchen and the walls age first.
START_OFF = dict(wall=-5, roof=0, floor=5, power=-3, kitchen=-8)

# Furniture: the whole catalogue lives in game/deco_content.py (the first 27 ids came with 1.2.0).
ITEMS = DC.ITEMS
_ID = re.compile(r'^[a-z0-9_]{1,24}$')
_SLOT = re.compile(r'^[wf][0-9]$')


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _deco():
    from . import deco
    return deco


def get(s: dict) -> dict | None:
    j = s.get('journey')
    r = j.get('reno') if isinstance(j, dict) else None
    return r if isinstance(r, dict) else None


def _own(s: dict) -> dict | None:
    h = hs.get(s)
    return h['own'] if h and isinstance(h.get('own'), dict) and h['own'].get('kind') in HOUSES else None


def size(kind: str) -> int:
    return HOUSES[kind]['size']


def fix_cost(kind: str, part: str, cond: int) -> int:
    if cond >= 100:
        return 0
    return max(FIX_MIN, -(-PARTS[part]['fix'] * (100 - cond) * size(kind) // 10000))


def up_cost(kind: str, part: str, lv: int) -> int:
    """Price of upgrade level `lv` (1 or 2)."""
    return -(-PARTS[part]['up'][lv - 1][1] * size(kind) // 1000) * 10


def sell_price(k: str) -> int:
    return ITEMS[k]['price'] * SELL_PCT // 100


def _wear_count(a: int, b: int, w: int, idx: int) -> int:
    """Life days d in (a, b] with (d + idx) % w == 0: the points a part loses between those mornings."""
    return max(0, (b + idx) // w - (a + idx) // w)


def _worn(c: int, n: int) -> int:
    return max(min(c, COND_MIN), c - n)


def _start_parts(kind: str, since: int, day: int) -> dict:
    """The parts the day a block is created: the home's start condition, worn since it was bought."""
    out = {}
    for i, p in enumerate(PART_IDS):
        c = max(COND_MIN, min(100, HOUSES[kind]['start'] + START_OFF[p]))
        out[p] = dict(c=_worn(c, _wear_count(since, day, WEAR_DAYS[0], i)), lv=0)
    return out


def blank(own: dict, day: int) -> dict:
    return dict(v=VERSION, hid=own['id'], day=int(day), seq=0, parts=_start_parts(own['kind'], int(own['day']), int(day)),
                items=[], spent=0, stats={k: 0 for k in STATS})


def _wear_to(r: dict, day: int) -> None:
    """Bring the parts' wear up to life day `day` (closed form, no notes)."""
    if r['parts'] and day > r['day']:
        for i, p in enumerate(PART_IDS):
            x = r['parts'][p]
            x['c'] = _worn(x['c'], _wear_count(r['day'], day, WEAR_DAYS[x['lv']], i))
    r['day'] = max(r['day'], day)


def _sync(r: dict, own: dict | None, day: int) -> bool:
    """The block follows the home: another home (or none) puts the furniture in the kho and starts new parts
    (worn from the day it was bought). True when the home changed."""
    hid = own['id'] if own else None
    if r['hid'] == hid:
        return False
    for it in r['items']:
        it['r'] = it['x'] = None
    r['hid'] = hid
    if own:
        day = max(day, int(own['day']))
        r['parts'] = _start_parts(own['kind'], int(own['day']), day)
    else:
        r['parts'] = {}
    r['day'] = max(r['day'], day)
    return True


def leave_home(s: dict, own: dict, day: int) -> dict | None:
    """🏘️ Moving out of a home you keep (housing.py, several homes): its parts and upgrades as they stand today,
    for housing.py to keep on that home (`keep`). None: nobody has worked on it (its view is computed)."""
    r = get(s)
    if r is None or r['hid'] != own['id'] or not r['parts']:
        return None
    _wear_to(r, day)
    return dict(day=int(r['day']), parts=tree_copy(r['parts']))


def enter_home(s: dict, own: dict, keep: dict | None, day: int) -> None:
    """🏘️ Moving back into a home you own: its kept parts come back, worn by the days it stood empty (no Ấm cúng
    bonus for those days). Without `keep` the block simply follows the home on the next morning (_sync)."""
    r = get(s)
    if r is None or not keep:
        return
    for it in r['items']:
        it['r'] = it['x'] = None
    r['hid'] = own['id']
    r['parts'] = tree_copy(keep['parts'])
    r['day'] = int(keep['day'])
    _wear_to(r, day)


def upgrade(j: dict) -> None:
    """Future fields join an existing block here (setdefault only). Absent stays absent."""
    r = j.get('reno') if isinstance(j, dict) else None
    if isinstance(r, dict) and isinstance(r.get('stats'), dict):
        for k in STATS:
            r['stats'].setdefault(k, 0)


def _view_block(s: dict) -> dict | None:
    """The block as the view sees it today, without writing to the save (None: no home of your own)."""
    own = _own(s)
    if not own:
        return None
    day = s['journey']['life_day']
    r = get(s)
    if r is None:
        return blank(own, day)
    r = tree_copy(r)
    _sync(r, own, day)
    _wear_to(r, day)
    return r


def _ensure(s: dict, own: dict) -> dict:
    j = s['journey']
    day = j['life_day']
    r = get(s)
    if r is None:
        r = j['reno'] = blank(own, day)
    _sync(r, own, day)
    _wear_to(r, day)
    return r


# ---------------------------------------------------------------- rooms, comfort
def rooms(kind: str) -> list[dict]:
    """The rooms of a home you own, with 1.2.0's slot counts (deco.py draws them as grids)."""
    out = []
    for row in HOUSES[kind]['rooms']:
        rid, w, f = row[:3]
        emoji, name = ROOMS[rid]
        out.append(dict(id=rid, emoji=emoji, name=row[3] if len(row) > 3 else name, wall=w, floor=f, out=rid in OUTDOOR))
    return out


def levels(r: dict | None) -> int:
    return sum(x['lv'] for x in r['parts'].values()) if r and r['parts'] else 0


def upgrade_points(s: dict) -> int:
    """Ấm cúng from the upgrades of the home you own today (COZY_LV a level)."""
    return COZY_LV * levels(_view_block(s))


def cozy_total(s: dict) -> int:
    """The home's Ấm cúng: the furniture placed and the sets (deco.py) + the upgrades."""
    return _deco().decor_points(s) + upgrade_points(s)


def cond_avg(r: dict) -> int:
    return sum(x['c'] for x in r['parts'].values()) // len(PART_IDS) if r['parts'] else 0


def perk_of(points: int) -> int:
    return next((n for low, n in COZY_STEPS if points >= low), 0)


def _late(s: dict) -> bool:
    own = _own(s)
    return bool(own) and hs._late(own.get('loan'))


def perk_off(s: dict) -> str | None:
    """Why the morning bonus of a home you own is paused: 'late' (a mortgage payment), 'cond' (needs repairs)."""
    if _late(s):
        return 'late'
    r = _view_block(s)
    return 'cond' if r is not None and cond_avg(r) < COZY_COND else None


# ---------------------------------------------------------------- the daily tick
def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Catch the block up to `journey.life_day` (idempotent): wear, the Ấm cúng morning bonus.
    Only a block that exists (the player has worked on a home or owns furniture) is touched."""
    j = s.get('journey')
    r = get(s)
    if r is None or not j.get('story'):
        return []
    target = int(j['life_day'])
    own = _own(s)
    notes: list[str] = []
    placed = any(it['r'] is not None for it in r['items'])   # 1.2.0 slots (since 1.3 deco.py says it)
    if _sync(r, own, r['day']) and placed:
        notes.append('📦 Đồ đạc trong nhà cũ đã chuyển vào túi đồ.')
    if not own:
        r['day'] = max(r['day'], target)
    else:
        r['day'] = max(r['day'], target - CATCHUP)
    if r['day'] < target:   # most commands: the same day, nothing to do
        late = _late(s)
        pts = cozy_total(s)   # furniture and levels do not change overnight
    while r['day'] < target:
        r['day'] += 1
        d = r['day']
        for i, p in enumerate(PART_IDS):
            x = r['parts'][p]
            if (d + i) % WEAR_DAYS[x['lv']] == 0 and x['c'] > COND_MIN:
                x['c'] -= 1
                if x['c'] == WORN_AT - 1 and len(notes) < 2:
                    notes.append(f'{PARTS[p]["emoji"]} Nhà mình: {PARTS[p]["flaw"][:1].lower() + PARTS[p]["flaw"][1:]}.')
        n = perk_of(pts) if cond_avg(r) >= COZY_COND and not late else 0
        if n:
            got = hs._spirit(s, n)
            r['stats']['cozy_days'] += 1
            r['stats']['spirit'] += got
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- commands
def _pay(s: dict, cost: int, label: str, day: int) -> None:
    need = _core().need
    have = hs._have(s)
    short = cost - have['wallet'] - have['balance']
    need(short <= 0, f'Cần {hs._fmt(cost)} xu: tài khoản và ví còn thiếu {hs._fmt(short)} xu.', 'not_enough')
    hs._take(s, cost, label, day)


def ensure_block(s: dict) -> dict:
    """The block that holds the player's furniture: a home's (as _ensure), or one with no home (hid None)."""
    own = _own(s)
    if own:
        return _ensure(s, own)
    j = s['journey']
    r = get(s)
    if r is None:
        r = j['reno'] = dict(v=VERSION, hid=None, day=int(j['life_day']), seq=0, parts={}, items=[], spent=0,
                             stats={k: 0 for k in STATS})
    return r


def new_uid(r: dict) -> str:
    used = {x['id'] for x in r['items']}
    r['seq'] += 1
    while f'd{r["seq"]}' in used:   # an id a newer build may have handed out
        r['seq'] += 1
    return f'd{r["seq"]}'


def apply(s: dict, name: str, p: dict) -> dict:
    """`jr_reno_*` commands. A refused command changes nothing (engine.apply_action works on a copy)."""
    e = _core()
    need = e.need
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác sửa nhà không hợp lệ.', 'unknown_action')
    need(j['story'], 'Sửa và trang trí nhà chỉ có trong chế độ hành trình.', 'story_only')
    own = _own(s)
    h = hs.get(s)
    sh = h.get('shared') if h else None
    if name in ('jr_reno_buy', 'jr_reno_move', 'jr_reno_store', 'jr_reno_sell'):   # 1.2.0's slots: Bày trí phòng now
        if not own and name in ('jr_reno_buy', 'jr_reno_move'):
            need(not sh, f'Đây là nhà của {sh["name"] if sh else ""}: muốn sửa sang thì bàn với người ấy nhé.', 'not_owner')
            need(False, 'Mua nhà rồi mới sửa và trang trí được nhé.', 'no_home')
        return _deco().legacy(s, name, p)
    if not own:
        need(not sh, f'Đây là nhà của {sh["name"] if sh else ""}: muốn sửa sang thì bàn với người ấy nhé.', 'not_owner')
        need(False, 'Nhà thuê là của chủ nhà: chỉ bày đồ trang trí thôi, không sửa được nhé.' if h and h.get('rent')
             else 'Mua nhà rồi mới sửa được nhé.', 'no_home')
    day = j['life_day']
    kind = own['kind']
    home = hs.lname(hs.HOMES[kind]['name'])
    part = p.get('part')
    need(part in PARTS or (name == 'jr_reno_fix' and part == 'all'), 'Chọn hạng mục cần sửa nhé.')
    need(p.get('confirm') is True, 'Xác nhận sửa nhà.')
    r = _ensure(s, own)
    if name == 'jr_reno_fix':
        todo = [x for x in (PART_IDS if part == 'all' else (part,)) if r['parts'][x]['c'] < 100]
        need(todo, 'Nhà đang như mới, chưa cần sửa gì.' if part == 'all' else f'{PARTS[part]["name"]} đang như mới rồi.', 'nothing')
        cost = sum(fix_cost(kind, x, r['parts'][x]['c']) for x in todo)
        need(p.get('cost') == cost, 'Giá sửa vừa thay đổi. Xem lại rồi sửa nhé.', 'stale_quote')
        what = 'Sửa cả nhà' if len(todo) > 1 else f'Sửa {PARTS[todo[0]]["name"].lower()}'
        _pay(s, cost, f'{what} · {home}', day)
        for x in todo:
            r['parts'][x]['c'] = 100
        r['stats']['fixed'] += len(todo)
        r['spent'] += cost
        hs._log(h, day, f'{what}: {", ".join(PARTS[x]["name"].lower() for x in todo)}.', -cost)
        return dict(message=f'{what} xong, {hs._fmt(cost)} xu. Nhà sáng sủa hẳn!', cozy=cozy_total(s))
    x = r['parts'][part]
    lv = p.get('lv')
    need(x['lv'] < LV_MAX, f'{PARTS[part]["name"]} đã nâng cấp hết mức rồi.', 'nothing')
    need(type(lv) is int and lv == x['lv'] + 1, f'{PARTS[part]["name"]} vừa được nâng cấp rồi. Xem lại nhé.', 'stale_quote')
    cost = up_cost(kind, part, lv)
    need(p.get('cost') == cost, 'Giá nâng cấp vừa thay đổi. Xem lại nhé.', 'stale_quote')
    what = PARTS[part]['up'][lv - 1][0]
    _pay(s, cost, f'{what} · {home}', day)
    x.update(lv=lv, c=100)
    r['stats']['upgraded'] += 1
    r['spent'] += cost
    hs._log(h, day, f'{what}.', -cost)
    return dict(message=f'{what} xong, {hs._fmt(cost)} xu. Ấm cúng +{COZY_LV}.', cozy=cozy_total(s))


def action(s: dict, name: str, p: dict) -> dict:
    """Entry from journey.action (which runs journey.after and validate_state)."""
    return apply(s, name, p or {})


# ---------------------------------------------------------------- views
def catalogue() -> dict:
    """Static (journey.content()['reno'], sent once at bootstrap): parts and the comfort rules (furniture: deco.catalogue)."""
    return dict(parts=[dict(id=k, emoji=v['emoji'], name=v['name'], flaw=v['flaw'], up=[n for n, _ in v['up']]) for k, v in PARTS.items()],
                steps=[dict(min=low, spirit=n) for low, n in COZY_STEPS], cozy_lv=COZY_LV, cozy_cond=COZY_COND, worn_at=WORN_AT,
                sell_pct=SELL_PCT, items_max=ITEMS_MAX)


def public(s: dict) -> dict | None:
    """The structure of the home you own today (None: none): parts, repairs, upgrades. Prices depend on the home."""
    j = s.get('journey') or {}
    if not j.get('story'):
        return None
    r = _view_block(s)
    if r is None:
        return None
    own = _own(s)
    kind = own['kind']
    H = hs.HOMES[kind]
    parts = []
    for p in PART_IDS:
        x = r['parts'][p]
        lv = x['lv']
        parts.append(dict(id=p, c=x['c'], lv=lv, fix=fix_cost(kind, p, x['c']), worn=x['c'] < WORN_AT,
                          up=dict(lv=lv + 1, name=PARTS[p]['up'][lv][0], cost=up_cost(kind, p, lv + 1)) if lv < LV_MAX else None))
    pts, avg = cozy_total(s), cond_avg(r)
    late = _late(s)
    have = hs._have(s)
    return dict(home=dict(kind=kind, name=H['name'], emoji=H['emoji'], group=H['group']), rooms=rooms(kind), parts=parts,
                fix_all=sum(x['fix'] for x in parts), cozy=pts, cond=avg, perk=perk_of(pts), perk_on=avg >= COZY_COND and not late, late=late,
                ready=have['wallet'] + have['balance'], spent=r['spent'], count=len(r['items']))


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    e = _core()
    need, integer = e.need, e.integer
    j = s.get('journey')
    if not isinstance(j, dict) or j.get('reno') is None:
        return
    r = j['reno']
    bad = 'Dữ liệu sửa nhà không hợp lệ.'
    need(isinstance(r, dict) and set(r) == {'v', 'hid', 'day', 'seq', 'parts', 'items', 'spent', 'stats'} and r['v'] == VERSION, bad, 'invalid_save')
    need(r['hid'] is None or (isinstance(r['hid'], str) and 1 <= len(r['hid']) <= 16), bad)
    integer(r['day'], 1, 10**6)
    need(r['day'] <= j['life_day'], bad)
    integer(r['seq'], 0, 10**6)
    integer(r['spent'], 0, 10**9)
    need(isinstance(r['stats'], dict) and set(r['stats']) == set(STATS), bad)
    for v in r['stats'].values():
        integer(v, 0, 10**9)
    parts = r['parts']
    need(isinstance(parts, dict) and set(parts) == (set() if r['hid'] is None else set(PART_IDS)), bad)
    for x in parts.values():
        need(isinstance(x, dict) and set(x) == {'c', 'lv'}, bad)
        integer(x['c'], 0, 100)
        integer(x['lv'], 0, LV_MAX)
    items = r['items']
    need(isinstance(items, list) and len(items) <= ITEMS_MAX, bad)
    ids, spots = set(), set()
    for it in items:
        # Kinds and rooms are checked by shape only: a newer build's furniture survives a rollback (not drawn).
        need(isinstance(it, dict) and set(it) == {'id', 'k', 'r', 'x'} and isinstance(it['id'], str) and 1 <= len(it['id']) <= 12
             and it['id'] not in ids and isinstance(it['k'], str) and _ID.match(it['k']), bad)
        ids.add(it['id'])
        need((it['r'] is None) == (it['x'] is None), bad)
        if it['r'] is not None:
            need(isinstance(it['r'], str) and _ID.match(it['r']) and isinstance(it['x'], str) and _SLOT.match(it['x'])
                 and (it['r'], it['x']) not in spots, bad)
            spots.add((it['r'], it['x']))
