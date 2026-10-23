"""🏗️ Xây trên đảo: buildings on the plots of a private island (story mode; catalogue: game/island_build_content.py).

Owner 19/10: "công trình trên đảo k kiếm tiền, xây dựng nơi riêng, nhà này kia thôi". Nothing here ever pays xu: no
rent, no tickets, no income, no discount, no faster work. What a building gives is a place: it stands on the island for
the owner and every visitor (both interfaces), leisure buildings are spots to use (a small tinh thần, capped a day),
homes have an inside view, and the weekly 🏝️ Đảo đẹp board counts them (a title only: game/island_lb.py).

* jr_isle_build {island, plot, kind, confirm}: an empty plot of an island the save owns; level 1 is paid in full (the
  wallet first, then the bank account, never a loan, never with a wallet in debt: game/lux.py ready_why) and stands
  after its real hours (scaffolding until then). At most C.CREWS constructions at once on one island.
* jr_isle_up {island, plot, confirm}: the next level of a finished building, paid in full, its own hours.
* jr_isle_raze {island, plot, confirm}: phá dỡ (or stop a construction): C.SALVAGE_PCT % of everything the plot cost
  comes back into the wallet ("thu hồi vật liệu"), the plot is empty again. Selling the island does the same for every
  plot on it (game/island.py _sell calls on_sell()).
* jr_isle_paint {island, plot, look, confirm} (20/10): 🎨 another colour of the same house style (C.LOOKS palettes,
  public/js/house-art.js), paid at once (C.PAINT_PCT % of its level-1 price, at least C.PAINT_MIN). jr_isle_build takes
  the colour too (`look`, free). The colour lives in the kind itself, '<id>__<n>' (split()): saves, the island_builds
  rows and every reader keep their shape; an older build keeps such a plot by shape and simply does not show it.
* jr_isle_use {trip, plot}: using a leisure building on an island one is on (game/island_trips.py access: the owner, a
  friend aboard, a public visitor): tinh thần +C.USE_SPIRIT, at most C.USE_MAX times a Vietnam day. The reducer cannot
  see the database: command_commit (game/storage.py, in the save's own transaction) checks the trip, the access and
  the building, and refuses the whole command otherwise.
A wallet row is at most isl.ROW_MAX xu (journey.validate of every build): charges and refunds are split like the
island's (isl._take, isl._wallet_rows), kind 'life'.

The save is the truth; PostgreSQL holds a copy visitors, the public list and the board can read (table island_builds,
one row per owner, island and plot, status 'up' | 'gone'; game/pg_schema.py SCHEMA_VERSION 56), written by
command_commit in the save's transaction for every command that can change it (SYNC_ACTIONS). A building stands once
its ready time is past: no write is needed when it finishes (readers compare the time).

State `s['journey']['islb']` (absent until the first building; journey.validate allows extra keys, so an older build
keeps it untouched and never shows it — tests/test_island_build_compat.py proves it on those trees):
    v   VERSION
    p   {island id: {plot index (str): {k: kind, l: level standing (0 while the first is built), b: level being built
        (0: none), t: when it stands (unix s, 0: none), x: xu paid into the plot}}}
        A plot of an island the save no longer owns (sold on an older build) is kept as it is and shown again when the
        island is bought back; a kind this build does not know is kept by shape, never shown or counted.
    n   {built, up, raze, xu (paid), back (salvage received)}
    u   {d: Vietnam day ordinal, n: uses that day, trip, plot: the last use} or None
"""
from __future__ import annotations

import os
import re
import time

from . import bank as bk
from . import island as isl
from . import island_build_content as C

VERSION = 1
KEY = 'islb'
KIND = 'life'
COMMANDS = ('jr_isle_build', 'jr_isle_up', 'jr_isle_raze', 'jr_isle_use', 'jr_isle_paint')
SYNC_ACTIONS = ('jr_isle_build', 'jr_isle_up', 'jr_isle_raze', 'jr_isle_paint', 'jr_island_sell', 'jr_island_buy', 'reset_all', 'import_save',
                'jr_isle_place', 'jr_isle_dmove', 'jr_isle_store', 'jr_isle_bmove', 'jr_isle_expand', 'jr_isle_opt')   # 🏝️ game/island_design.py
BUILD = {b['id']: b for b in C.BUILDINGS}
LOOK_RE = re.compile(r'([a-z0-9_]+?)__([1-9])')
BLOCK_KEYS = frozenset({'v', 'p', 'n', 'u'})
PLOT_KEYS = frozenset({'k', 'l', 'b', 't', 'x'})
USE_KEYS = frozenset({'d', 'n', 'trip', 'plot'})
STATS = ('built', 'up', 'raze', 'xu', 'back')
LEVEL_MAX = 9                     # by shape: a newer build may add levels
PLOTS_MAX = 64
PAID_MAX = 10**10
TS_MAX = 2**34
BIG = 10**12
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
TRIP_RE = re.compile(r'[0-9a-f]{16}')


def now() -> float:
    return time.time()


def looks_of(it: dict) -> int:
    """How many colours a building comes in (1: just its own)."""
    return len(it.get('looks') or ()) or 1


def split(kind) -> tuple:
    """A stored kind → (style id, colour): 'pho_hoi_an__2' → ('pho_hoi_an', 2); a plain id → (id, 0). A suffix this
    build does not know (no such style, or more colours than it has) stays as it is: an unknown kind."""
    m = LOOK_RE.fullmatch(kind) if isinstance(kind, str) else None
    if m and m.group(1) in BUILD and int(m.group(2)) < looks_of(BUILD[m.group(1)]):
        return m.group(1), int(m.group(2))
    return kind, 0


def known(kind) -> dict | None:
    """The catalogue entry of a stored kind (its colour aside), None for a kind this build does not know."""
    return BUILD.get(split(kind)[0])


def kind_of(sid: str, look: int = 0) -> str:
    return f'{sid}__{look}' if look else sid


def paint_price(it: dict) -> int:
    return max(C.PAINT_MIN, it['levels'][0][0] * C.PAINT_PCT // 100 // 1000 * 1000)


def _core():
    from . import engine
    return engine


def _fmt(n: int) -> str:
    return bk._fmt(n)


def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


def _id(v) -> bool:
    return isinstance(v, str) and ID_RE.fullmatch(v) is not None


def vn_day(t: float | None = None) -> int:
    from .wealth_fee import today
    return today(t)


# ---------------------------------------------------------------- the block
def initial() -> dict:
    return dict(v=VERSION, p={}, n={k: 0 for k in STATS}, u=None)


def get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial()
    return j[KEY]


def plots_of(iid: str) -> tuple:
    return C.PLOTS.get(iid, ())


def salvage(paid: int) -> int:
    return max(0, int(paid) * C.SALVAGE_PCT // 100 // 10 * 10)


def _entry_ok(e) -> bool:
    if not (isinstance(e, dict) and set(e) == PLOT_KEYS and _id(e['k']) and _int(e['l'], 0, LEVEL_MAX)
            and _int(e['b'], 0, LEVEL_MAX) and _int(e['t'], 0, TS_MAX) and _int(e['x'], 1, PAID_MAX)):
        return False
    if e['b']:
        return e['b'] == e['l'] + 1 and e['t'] > 0
    return e['l'] >= 1 and e['t'] == 0


def _plots_ok(p) -> bool:
    return isinstance(p, dict) and len(p) <= isl.OWN_MAX and all(
        _id(iid) and isinstance(d, dict) and len(d) <= PLOTS_MAX
        and all(isinstance(k, str) and k.isdigit() and len(k) <= 2 and _entry_ok(e) for k, e in d.items())
        for iid, d in p.items())


def _use_ok(u) -> bool:
    return u is None or (isinstance(u, dict) and set(u) == USE_KEYS and _int(u['d'], 0, 10**7) and _int(u['n'], 0, 1000)
                         and isinstance(u['trip'], str) and len(u['trip']) <= 32 and _int(u['plot'], 0, PLOTS_MAX))


def validate(s: dict) -> None:
    """``s['journey']['islb']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    j = s.get('journey')
    b = get(s)
    bad = 'Dữ liệu công trình trên đảo trong bản lưu không hợp lệ.'
    if b is None:
        e.need(not isinstance(j, dict) or j.get(KEY) is None, bad, 'invalid_save')
        return
    n = b.get('n')
    e.need(set(b) == BLOCK_KEYS and b['v'] == VERSION and _plots_ok(b['p']) and _use_ok(b['u'])
           and isinstance(n, dict) and set(n) <= set(STATS) and all(_int(v) for v in n.values()), bad, 'invalid_save')


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep what still makes sense."""
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    if not isinstance(b, dict):
        j[KEY] = initial()
        return
    out = initial()
    p = b.get('p') if isinstance(b.get('p'), dict) else {}
    for iid, d in list(p.items())[:isl.OWN_MAX]:
        if not (_id(iid) and isinstance(d, dict)):
            continue
        keep = {}
        for k, e in list(d.items())[:PLOTS_MAX]:
            if isinstance(k, str) and k.isdigit() and len(k) <= 2 and isinstance(e, dict) and set(e) >= PLOT_KEYS:
                e = {x: e[x] for x in PLOT_KEYS}
                if _entry_ok(e):
                    keep[k] = e
        out['p'][iid] = keep
    n = b.get('n') if isinstance(b.get('n'), dict) else {}
    out['n'] = {k: n[k] if _int(n.get(k)) else 0 for k in STATS}
    u = b.get('u')
    if isinstance(u, dict) and set(u) >= USE_KEYS:
        u = {k: u[k] for k in USE_KEYS}
        out['u'] = u if _use_ok(u) else None
    if out != b:
        j[KEY] = out


# ---------------------------------------------------------------- reading a plot
def standing(e: dict, t: float) -> int:
    """The level standing on the plot at time t (0: nothing finished yet)."""
    return e['b'] if e['b'] and e['t'] <= t else e['l']


def building(e: dict, t: float) -> bool:
    """Scaffolding on the plot at time t."""
    return bool(e['b']) and e['t'] > t


def _settle(b: dict, t: float) -> list:
    """Constructions whose hours are over stand now (in place). [(island, plot, kind, level)] finished."""
    done = []
    for iid, d in b['p'].items():
        for k, e in d.items():
            if e['b'] and e['t'] <= t:
                e['l'], e['b'], e['t'] = e['b'], 0, 0
                done.append((iid, int(k), e['k'], e['l']))
    return done


def crews_busy(plots: dict, t: float) -> int:
    return sum(1 for e in plots.values() if isinstance(e, dict) and building(e, t))


def score(plots, t: float) -> int:
    """The 🏝️ Đảo đẹp points of one island's plots at time t: every standing level × its kind's points, plus
    C.VARIETY for each different kind standing. Scaffolding counts nothing yet."""
    total, kinds = 0, set()
    for e in plots:
        it = known(e['k'])
        lv = standing(e, t) if it else 0
        if lv:
            total += it['pts'] * min(lv, C.LEVELS)
            kinds.add(it['id'])
    return total + C.VARIETY * len(kinds)


def worth(j: dict) -> int:
    """What a phá dỡ would give back for every plot of every island the save owns (C.SALVAGE_PCT % of what was paid,
    construction in progress included): the 💰 board (game/wealth.py) and the phí giữ tài sản lớn (game/wealth_fee.py)
    count the buildings at that value."""
    b = j.get(KEY) if isinstance(j, dict) else None
    p = b.get('p') if isinstance(b, dict) else None
    if not isinstance(p, dict):
        return 0
    isle = j.get('island') if isinstance(j.get('island'), dict) else {}
    own = isle.get('own') if isinstance(isle.get('own'), dict) else {}
    total = 0
    for iid, d in p.items():
        if iid in own and iid in isl.ISLAND and isinstance(d, dict):
            total += sum(salvage(e['x']) for e in d.values() if isinstance(e, dict) and _int(e.get('x'), 1, PAID_MAX))
    return total


OFF_TEXT = 'Xây trên đảo đang tạm nghỉ để bảo trì. Công trình đang xây vẫn xong đúng giờ, quay lại sau nhé!'


def off() -> bool:
    """🛑 MNL_ISLAND_BUILD_OFF=1 (ops' kill switch, default unset: on): the 🏗️ Xây tab hides (the island catalogue's
    `build_off`), jr_isle_* are refused gracefully. Saves keep journey.islb as it is, a construction still stands once
    its time is up (readers compare the time), selling an island still pays its salvage, the islands still show them."""
    return os.environ.get('MNL_ISLAND_BUILD_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


# ---------------------------------------------------------------- commands
def _design():
    from . import island_design
    return island_design


def action(s: dict, name: str, p: dict) -> dict:
    need = _core().need
    j = s['journey']
    need(j.get('story'), 'Xây trên đảo chỉ có trong hành trình.', 'locked')
    need(not off(), OFF_TEXT, 'off')
    if name in _design().COMMANDS:   # 🏝️ Thiết kế đảo: decorations, moving, lấn biển (game/island_design.py)
        return _design().action(s, name, p)
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict), 'Thông tin không hợp lệ.')
    if name == 'jr_isle_use':
        return _use(s, p)
    grid = name == 'jr_isle_build' and 'plot' not in p   # 🏝️ placed on the grid: {x, y, r} (game/island_design.py)
    need(set(p) <= {'island', 'plot', 'kind', 'confirm', 'look', 'x', 'y', 'r'} and 'island' in p
         and (grid and {'x', 'y'} <= set(p) or not grid and 'plot' in p and not {'x', 'y', 'r'} & set(p)), 'Thông tin không hợp lệ.')
    iid = p['island']
    need(isinstance(iid, str) and iid in isl.owned(s), 'Bạn chưa có hòn đảo này.', 'not_owned')
    if not grid:
        need(type(p['plot']) is int and 0 <= p['plot'] < PLOTS_MAX
             and (p['plot'] < len(plots_of(iid)) or str(p['plot']) in _plots(s, iid)), 'Chọn một ô đất nhé.')
    t = now()
    b = get(s)
    done = _settle(b, t) if b else []
    if grid:
        out = _build(s, p, iid, '', t)
    else:
        out = {'jr_isle_build': _build, 'jr_isle_up': _up, 'jr_isle_raze': _raze, 'jr_isle_paint': _paint}[name](s, p, iid, str(p['plot']), t)
    if done:
        out.setdefault('effects', []).extend(f'{it["emoji"]} {it["name"]} đã xây xong (cấp {lv}).' for _, _, k, lv in done if (it := known(k)))
    return out


def _plots(s: dict, iid: str) -> dict:
    b = get(s)
    d = b['p'].get(iid) if b else None
    return d if isinstance(d, dict) else {}


def _look(it: dict, p: dict) -> int:
    """The colour asked for (`look`, absent: the first), one this style comes in."""
    look = p.get('look', 0)
    _core().need(type(look) is int and 0 <= look < looks_of(it), 'Chọn một màu nhé.')
    return look


def _build(s: dict, p: dict, iid: str, key: str, t: float) -> dict:
    need = _core().need
    it = BUILD.get(p.get('kind')) if isinstance(p.get('kind'), str) else None
    need(it is not None, 'Chọn một công trình nhé.')
    look = _look(it, p)
    plots = _plots(s, iid)
    D = _design()
    if not key:   # 🏝️ on the grid: a free plot index, the cells checked (bounds, land, the coast, nothing in the way)
        r = p.get('r', 0)
        need(type(p['x']) is int and type(p['y']) is int and type(r) is int and 0 <= r <= 3, 'Thông tin không hợp lệ.')
        why = D.check_building(s, iid, it['id'], p['x'], p['y'], r)
        if why == 'Phải đặt sát bờ biển.':
            why = f'{it["name"]} phải đặt sát bờ biển.'
        need(not why, why, 'place')
        n = D.free_plot(s, iid)
        need(n >= 0, 'Đảo đã kín công trình rồi.', 'limit')
        key = str(n)
    cur = plots.get(key)
    if cur and split(cur['k'])[0] == it['id'] and cur['l'] == 0 and cur['b'] == 1:   # a second tap: nothing to pay
        return dict(message=f'{it["name"]} đang được xây ở ô này rồi.', duplicate=True)
    need(cur is None, 'Ô đất này đã có công trình.', 'taken')
    isle = isl.ISLAND[iid]
    if 'x' not in p:   # an old plot (an older client): the old rules, and its cells free of decorations
        need(int(key) < len(plots_of(iid)), 'Chọn một ô đất nhé.')
        if it.get('coast'):
            need(plots_of(iid)[int(key)][2], f'{it["name"]} cần ô đất sát bờ biển (ô có ⚓).', 'coast')
        why = D.check_plot(s, iid, int(key))
        need(not why, why, 'taken')
    if it.get('big'):
        need(isle['price'] >= C.BIG_FROM, f'{it["name"]} chỉ xây được trên đảo lớn (Mây Đá, Hoàng Hôn).', 'small')
    if it.get('max'):
        n = sum(1 for e in plots.values() if split(e['k'])[0] == it['id'])
        need(n < it['max'], f'Mỗi đảo chỉ có {it["max"]} {it["name"]}.', 'limit')
    need(crews_busy(plots, t) < C.CREWS, f'Cả {C.CREWS} đội thợ đang bận. Chờ một công trình xong nhé.', 'busy')
    price, hours = it['levels'][0]
    need(p.get('confirm') is True, f'Xác nhận xây {it["name"]} {_fmt(price)} xu.')
    why = isl._lx().ready_why(s, price)
    need(not why, why, 'not_enough')
    how = isl._take(s, price, f'🏗️ Xây {it["name"]} · {isle["name"]}')
    b = _ensure(s)
    b['p'].setdefault(iid, {})[key] = dict(k=kind_of(it['id'], look), l=0, b=1, t=int(t + hours * 3600), x=price)
    if 'x' in p:
        D.set_building(s, iid, int(key), p['x'], p['y'], p.get('r', 0))
    b['n']['built'] = min(BIG, b['n']['built'] + 1)
    b['n']['xu'] = min(BIG, b['n']['xu'] + price)
    return dict(message=f'{it["emoji"]} Khởi công {it["name"]} trên {isle["name"]}: trả {how}. Xong sau {hours} giờ.',
                isle=dict(island=iid, plot=int(key)))


def _up(s: dict, p: dict, iid: str, key: str, t: float) -> dict:
    need = _core().need
    need('kind' not in p, 'Thông tin không hợp lệ.')
    plots = _plots(s, iid)
    e = plots.get(key)
    need(e is not None and known(e['k']), 'Ô đất này chưa có công trình.', 'empty')
    it = known(e['k'])
    need(not e['b'], f'{it["name"]} đang được xây. Chờ xong rồi nâng cấp nhé.', 'busy')
    need(e['l'] < C.LEVELS, f'{it["name"]} đã ở cấp cao nhất.', 'max')
    need(crews_busy(plots, t) < C.CREWS, f'Cả {C.CREWS} đội thợ đang bận. Chờ một công trình xong nhé.', 'busy')
    price, hours = it['levels'][e['l']]
    lv = e['l'] + 1
    need(p.get('confirm') is True, f'Xác nhận nâng {it["name"]} lên cấp {lv}: {_fmt(price)} xu.')
    why = isl._lx().ready_why(s, price)
    need(not why, why, 'not_enough')
    isle = isl.ISLAND[iid]
    how = isl._take(s, price, f'🏗️ Nâng cấp {it["name"]} · {isle["name"]}')
    e.update(b=lv, t=int(t + hours * 3600), x=min(PAID_MAX, e['x'] + price))
    b = get(s)
    b['n']['up'] = min(BIG, b['n']['up'] + 1)
    b['n']['xu'] = min(BIG, b['n']['xu'] + price)
    return dict(message=f'{it["emoji"]} Nâng {it["name"]} lên cấp {lv}: trả {how}. Xong sau {hours} giờ.',
                isle=dict(island=iid, plot=int(key)))


def _raze(s: dict, p: dict, iid: str, key: str, t: float) -> dict:
    need = _core().need
    need('kind' not in p, 'Thông tin không hợp lệ.')
    plots = _plots(s, iid)
    e = plots.get(key)
    need(e is not None, 'Ô đất này chưa có công trình.', 'empty')
    name = known(e['k'])['name'] if known(e['k']) else 'Công trình'
    back = salvage(e['x'])
    j = s['journey']
    need(j['wallet'] + back <= isl.PRICE_MAX, 'Ví đã quá đầy. Gửi bớt vào ngân hàng rồi phá nhé.', 'limit')
    need(p.get('confirm') is True, f'Xác nhận phá {name}, nhận lại {_fmt(back)} xu.')
    plots.pop(key)
    _design().on_raze(s, iid, int(key))   # 🏝️ its place on the grid goes with it
    b = get(s)
    b['n']['raze'] = min(BIG, b['n']['raze'] + 1)
    b['n']['back'] = min(BIG, b['n']['back'] + back)
    if back:
        isl._wallet_rows(j, back, KIND, f'🏗️ Thu hồi vật liệu · {name}')
    return dict(message=f'Đã phá {name}. Thu hồi vật liệu: {_fmt(back)} xu vào ví. Ô đất trống lại.',
                isle=dict(island=iid, plot=int(key)))


def _paint(s: dict, p: dict, iid: str, key: str, t: float) -> dict:
    """🎨 Another colour of the same style: paid at once, nothing else changes (its level, a construction going on)."""
    need = _core().need
    need('kind' not in p and 'look' in p, 'Thông tin không hợp lệ.')
    e = _plots(s, iid).get(key)
    it = known(e['k']) if e else None
    need(it is not None, 'Ô đất này chưa có công trình.', 'empty')
    need(looks_of(it) > 1, f'{it["name"]} chỉ có một màu.', 'one_look')
    look = _look(it, p)
    if split(e['k'])[1] == look:
        return dict(message=f'{it["name"]} đang là màu {it["looks"][look]} rồi.', duplicate=True)
    price = paint_price(it)
    need(p.get('confirm') is True, f'Xác nhận sơn {it["name"]} màu {it["looks"][look]}: {_fmt(price)} xu.')
    why = isl._lx().ready_why(s, price)
    need(not why, why, 'not_enough')
    isle = isl.ISLAND[iid]
    how = isl._take(s, price, f'🎨 Sơn lại {it["name"]} · {isle["name"]}')
    e.update(k=kind_of(it['id'], look), x=min(PAID_MAX, e['x'] + price))
    b = get(s)
    b['n']['xu'] = min(BIG, b['n']['xu'] + price)
    return dict(message=f'🎨 {it["name"]} đã sơn màu {it["looks"][look]}: trả {how}.', isle=dict(island=iid, plot=int(key)))


def on_sell(s: dict, iid: str) -> int:
    """Selling island `iid` (game/island.py _sell, after its checks): every plot on it is razed, the salvage paid into the
    wallet. The xu given back."""
    b = get(s)
    plots = b['p'].pop(iid, None) if b else None
    if not plots:
        return 0
    back = sum(salvage(e['x']) for e in plots.values())
    b['n']['raze'] = min(BIG, b['n']['raze'] + len(plots))
    b['n']['back'] = min(BIG, b['n']['back'] + back)
    if back:
        isl._wallet_rows(s['journey'], back, KIND, f'🏗️ Thu hồi vật liệu · {isl.ISLAND[iid]["name"]}')
    return back


def sell_back(s: dict, iid: str) -> int:
    """What on_sell would give back now."""
    return sum(salvage(e['x']) for e in _plots(s, iid).values())


def _use(s: dict, p: dict) -> dict:
    need = _core().need
    need(set(p) == {'trip', 'plot'} and isinstance(p['trip'], str) and TRIP_RE.fullmatch(p['trip'])
         and type(p['plot']) is int and 0 <= p['plot'] < PLOTS_MAX, 'Thông tin không hợp lệ.')
    t = now()
    day = vn_day(t)
    b = get(s)
    u = b['u'] if b and b['u'] else None
    used = u['n'] if u and u['d'] == day else 0
    need(used < C.USE_MAX, f'Hôm nay bạn đã thư giãn đủ {C.USE_MAX} lần rồi. Mai chơi tiếp nhé!', 'limit')
    from . import needs
    got = needs._spirit(s, C.USE_SPIRIT)
    b = _ensure(s)
    b['u'] = dict(d=day, n=used + 1, trip=p['trip'], plot=p['plot'])
    left = C.USE_MAX - used - 1
    return dict(message=f'Tinh thần +{got}.' if got else 'Thư giãn một chút.', isle_use=dict(left=left))


# ---------------------------------------------------------------- PostgreSQL (game/storage.py, in the save's transaction)
def _rows(after) -> dict:
    """{(island, plot): entry} the table should show for this save: the islands it owns, kinds this build knows."""
    b = get(after) if isinstance(after, dict) else None
    if not b:
        return {}
    owned = set(isl.owned(after))
    out = {}
    for iid, d in b['p'].items():
        if iid not in owned or not isinstance(d, dict):
            continue
        for k, e in d.items():
            if known(e['k']) and int(k) < PLOTS_MAX:   # 🏝️ since 24/10 a building may stand on any plot index (the grid)
                out[(iid, int(k))] = e
    return out


def sync(db, sid: str, after) -> None:
    """island_builds rows of this owner = the save (upsert what is there, 'gone' for what is not); 🏝️ island_layout too
    (game/island_design.py)."""
    t = now()
    want = _rows(after)
    have = {(r['island'], int(r['plot'])): r for r in db.execute(
        'SELECT island, plot, kind, lvl, next_lvl, ready_at, paid, status FROM island_builds WHERE owner=?', (sid,)).fetchall()}
    moved = set()
    for (iid, plot), e in want.items():
        r = have.get((iid, plot))
        row = (e['k'], e['l'], e['b'], float(e['t']), e['x'])
        if r and r['status'] == 'up' and (r['kind'], int(r['lvl']), int(r['next_lvl']), float(r['ready_at']), int(r['paid'])) == row:
            continue
        db.execute('INSERT INTO island_builds(owner, island, plot, kind, lvl, next_lvl, ready_at, paid, status, at) '
                   "VALUES(?,?,?,?,?,?,?,?,'up',?) ON CONFLICT(owner, island, plot) DO UPDATE SET kind=excluded.kind, "
                   'lvl=excluded.lvl, next_lvl=excluded.next_lvl, ready_at=excluded.ready_at, paid=excluded.paid, '
                   "status='up', at=excluded.at", (sid, iid, plot, *row, t))
        moved.add(iid)
    for key, r in have.items():
        if key not in want and r['status'] == 'up':
            db.execute("UPDATE island_builds SET status='gone', at=? WHERE owner=? AND island=? AND plot=?", (t, sid, key[0], key[1]))
            moved.add(key[0])
    moved |= _design().sync(db, sid, after, t)
    if moved:   # whoever is on that island now sees the new scaffolding / the empty plot (live island_ping 'seat')
        from . import island_trips as it
        for trip in db.execute("SELECT id, island FROM island_trips WHERE owner=? AND status='open'", (sid,)).fetchall():
            if trip['island'] in moved:
                for who in {sid, *it._members(db, trip['id'])}:
                    it._notify(db, who, 'seat', trip['id'])
        from . import island_lb
        island_lb.clear_cache()


def command_commit(db, sid: str, action: str, after) -> None:
    """Called by the storage layer in the save's transaction. A GameError here rolls the whole command back."""
    if action == 'jr_isle_use':
        _check_use(db, sid, after)
    elif action in SYNC_ACTIONS:
        sync(db, sid, after)


def _check_use(db, sid: str, after) -> None:
    need = _core().need
    b = get(after)
    u = b['u'] if b else None
    need(u, 'Thông tin không hợp lệ.')
    from . import island_trips as it
    t = now()
    row = db.execute(it.ACCESS_SQL, (sid, u['trip'])).fetchone()
    need(it.access_for(row, sid, t), 'Bạn không ở trên hòn đảo này.', 'no_island')
    r = db.execute("SELECT kind, lvl, next_lvl, ready_at FROM island_builds WHERE owner=? AND island=? AND plot=? AND status='up'",
                   (row['owner'], row['island'], u['plot'])).fetchone()
    lv = (int(r['next_lvl']) if r and int(r['next_lvl']) and float(r['ready_at']) <= t else int(r['lvl'])) if r else 0
    need(r and known(r['kind']) and known(r['kind'])['cat'] == 'fun' and lv >= 1, 'Chỗ này chưa có gì để chơi.', 'not_here')


def island_rows(db, owner: str, iid: str) -> list:
    """The buildings visitors see on `owner`'s island `iid` (no sid in it)."""
    rows = db.execute("SELECT plot, kind, lvl, next_lvl, ready_at FROM island_builds WHERE owner=? AND island=? AND status='up' "
                      'ORDER BY plot', (owner, iid)).fetchall()
    return [dict(p=int(r['plot']), k=r['kind'], l=int(r['lvl']), b=int(r['next_lvl']), t=float(r['ready_at']))
            for r in rows if known(r['kind']) and int(r['plot']) < PLOTS_MAX]


def row_score(rows: list, t: float) -> int:
    return score([dict(k=r['k'], l=r['l'], b=r['b'], t=r['t']) for r in rows], t)


# ---------------------------------------------------------------- views
def public(s: dict) -> dict | None:
    """Small (it rides on every state): None until the first building."""
    b = get(s)
    if not b:
        return None
    owned = set(isl.owned(s))
    t = now()
    u = b['u']
    return dict(p={iid: {k: dict(k=e['k'], l=e['l'], b=e['b'], t=e['t'], back=salvage(e['x'])) for k, e in d.items() if known(e['k'])}
                   for iid, d in b['p'].items() if iid in owned},
                used=u['n'] if u and u['d'] == vn_day(t) else 0)


def catalogue() -> dict:
    """Static lists for the client (bootstrap content, cached)."""
    return dict(buildings=[dict(id=x['id'], emoji=x['emoji'], name=x['name'], cat=x['cat'], pts=x['pts'], desc=x['desc'],
                                levels=[dict(price=pr, hours=h, text=x['lv'][i]) for i, (pr, h) in enumerate(x['levels'])],
                                max=x.get('max', 0), coast=bool(x.get('coast')), big=bool(x.get('big')), spot=x['spot'],
                                lines=list(x.get('lines', ())),
                                **(dict(tier=x.get('tier') or C.TIER_OF.get(x['id'], 1)) if x['cat'] == 'home' else {}),
                                **(dict(looks=list(x['looks']), paint=paint_price(x)) if x.get('looks') else {})) for x in C.BUILDINGS],
                plots={iid: [[x, y, c] for x, y, c in ps] for iid, ps in C.PLOTS.items()},
                tiers=[[n, label] for n, label in C.TIERS],
                crews=C.CREWS, salvage_pct=C.SALVAGE_PCT, big_from=C.BIG_FROM, use_max=C.USE_MAX, variety=C.VARIETY)


def forget(db, sid: str) -> None:
    """A player erased their data (game/storage.py delete): their buildings leave the open-island list and the board."""
    db.execute('DELETE FROM island_builds WHERE owner=?', (sid,))
    _design().forget(db, sid)
    from . import island_lb
    island_lb.clear_cache()
