"""🔨 Nhà đấu giá đồ độc bản (owner 07/10: a big money sink; the top 1 % hold 57 % of the money, the richest 4.1 M xu,
the median earns ~262 xu a day). Story mode.

Only the street sells (system lots, never a player's: nothing to launder). Each lot is one item that exactly one player
will ever own (game/auction_content.py): a vanity plate, a phone number, a painting, the right to name a landmark, a
title, and since 16/10 a limited-edition vehicle, a plane registration and a yacht's name. Status, with one exception
decided by the owner on 16/10 (it replaces the earlier "cosmetic only, never pays xu" rule for plates): a plate attached
to the vehicle the player rides adds 3-10 % to each shift's career income (💰 Biển đẹp: game/auction_content.py
PLATE_PCT, paid by game/journey.py _end_of_day, game/garage.py bonus_now). Nothing else here pays xu, speeds up work or
helps an exam.

Schedule (plan(), ensure_plan()): 1–3 lots a Vietnam day, deterministic from the date and the pool of unsold items,
opening 20:30 / 21:00 / 21:30 and running 24 hours, plus a 🐾 pet-gear lot at 22:00 (one piece a day, A → S → SS).
When a lot opens the street's ticker says so, once (announce_open, news ref 'auc-open:<lot>'). An admin may add a lot (admin_add, POST /api/admin/auction).
Rows are created by whoever comes first (housekeeping or a page), once: deterministic ids under an advisory lock.

Bidding (jr_auc_bid {lot, amount, anon?}): one active bid per player per lot.
* The reducer (this save) holds the difference between the new bid and what this save already holds for the lot
  (`hold`), from the wallet then the bank account; never with a wallet in debt, never a loan.
* command_commit (the same transaction, game/storage.py) locks the lot row (FOR UPDATE) and checks it against the
  database: open and within its time, the account old enough (ACCOUNT_DAYS), the bid at least the next minimum, and
  this save's hold equal to the escrow the database knows for it (its bid row's `held` plus refunds not yet paid into
  the save; those are voided and reused, so raising after being outbid pays only the difference too). Then the
  previous leader's escrow becomes a refund row, the lot moves under a compare-and-set on its `seq`, a bid in the
  last SNIPE_SECS adds SNIPE_SECS, and NOTIFY tells the live service. Any refusal rolls the whole command back:
  nothing is held.
* Refunds and the item travel to a save through `live_effects` rows of kind 'auction' (game/live_effects.py: paid at
  the next load, or at once when the live service tells the page; fx_commit flips the row in the save's own
  transaction, so a refund is paid once and a voided one never). An older build leaves these rows pending.

Settlement (settle_due, housekeeping every 30 s and on a page read): under the lot's row lock, only from 'open' and
only once its end has passed: no bid → 'unsold' (the item goes back to the pool); a winner → 'sold', the winner's
escrow is BURNED (no seller, the sink), the item row ('auction' win) goes to the winner, other escrow (there should be
none: outbid holds are refunded at once) is refunded. Deterministic row ids make a second run a no-op whatever the
workers.

Save `journey.uniq` (absent until the first bid; journey.validate allows extra keys, 1.9.11 keeps it untouched):
    v      VERSION
    hold   {lot id: {a: xu held, b: the part taken from the bank account}}   escrow, shown as "đang giữ cho đấu giá"
    own    {item id: {k: kind, t: text, d: life day won, p: price paid, lot: lot id}}
    stats  {bids, won, xu (burned)}
Save `journey.uniq_x` (16/10; absent until needed): every build that knows `uniq` validates its `own` strictly (the five
first kinds, exact keys), so what came later lives beside it, kept untouched by older builds:
    v      X_VERSION
    own    {item id: {k: 'vehicle' | 'reg' | 'hull', t, d, p, lot}}   the newer kinds won (same record as uniq.own)
    on     {plate item id: vehicle id}   the auction plates attached in the garage (game/garage.py jr_garage_plate)
Absent, the dearest road plate rides on the road vehicle in use (the rule until 16/10, plates_on); the first write seeds
`on` with it, so nothing moves under the player. An older build that wins a newer kind leaves the 'win' row pending
(live_effects): the item arrives once a build that knows it loads the save.
Save `journey.uniq_y` (20/10; absent until needed): the same reason again (every build since 16/10 validates uniq_x.own
strictly), for the kinds that came on 20/10 (auction_content.Y_KINDS):
    v      Y_VERSION
    own    {item id: {k: 'decor' | 'petgear' | 'tool', t, d, p, lot, g}}   g 1: handed to its system (the piece in the bag of
           furniture, the piece in Tủ đồ thú cưng); 0: still waiting (the wardrobe was full: y_settle retries after each
           action). A tool needs nothing handed over (g 1): owning it is its use (tool_pct).
An older build keeps the block untouched (unknown journey key), the 🪑 piece in reno.items by shape (unshown) and the
🐾 piece in its wardrobe (a piece id every build since 2.4.56 knows); it just pays no 🧰 bonus.
Tables: auction_lots, auction_bids (game/pg_schema.py, SCHEMA_VERSION 29).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import threading
import time

from . import auction_content as C
from . import bank as bk

VERSION = 1
KEY = 'uniq'
BLOCK_KEYS = frozenset({'v', 'hold', 'own', 'stats'})
OWN_KEYS = frozenset({'k', 't', 'd', 'p', 'lot'})
STATS = ('bids', 'won', 'xu')
KIND = 'life'                      # wallet history kind (journey.HISTORY_KINDS): every build knows it
FX = 'auction'                     # live_effects kind
LOT_RE = re.compile(r'[0-9a-z][0-9a-z\-]{1,23}')
ITEM_RE = re.compile(r'[a-z0-9_]{1,32}')
KINDS = tuple(k for k, _, _ in C.KINDS)
OLD_KINDS = C.OLD_KINDS            # what journey.uniq.own may hold (older builds validate it strictly)
X_KEY = 'uniq_x'
X_VERSION = 1
X_KEYS = frozenset({'v', 'own', 'on'})
X_ON_MAX = 64
Y_KEY = 'uniq_y'
Y_VERSION = 1
Y_KEYS = frozenset({'v', 'own'})
Y_OWN_KEYS = OWN_KEYS | {'g'}
VID_RE = re.compile(r'[a-z0-9_]{1,24}')   # game/garage.py ID_RE
HOLD_MAX = 24
OWN_MAX = 200
TEXT_MAX = 48
BIG = 10**12
MAX_BID = 10**9
COMMANDS = ('jr_auc_bid',)
VN = datetime.timezone(datetime.timedelta(hours=7))
DAY = 86400
PUSH_EVERY = 600                   # an outbid push per lot per player at most every 10 minutes
HISTORY = 20
NEWS_FROM = 50_000                 # a sale from this price gets a line on the street's ticker
ANNOUNCE_SECS = 1800               # a lot that opened this recently gets its ticker line (a restart does not miss one)


def now() -> float:
    return time.time()


def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def fmt(n: int) -> str:
    return bk._fmt(n)


def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


def _lot(v) -> bool:
    return isinstance(v, str) and LOT_RE.fullmatch(v) is not None


def _item(v) -> bool:
    return isinstance(v, str) and ITEM_RE.fullmatch(v) is not None


def pid_of(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


def tier(n: int) -> dict:
    return C.TIERS.get(n) or C.TIERS[1]


def min_next(high: int, start: int, step: int, bids: int) -> int:
    """The smallest bid the lot takes now: its starting price, then max(+PCT %, +step) over the high bid."""
    if not bids or high <= 0:
        return start
    return high + max(-(-high * C.PCT // 100), step)


# ---------------------------------------------------------------- the save block
def initial() -> dict:
    return dict(v=VERSION, hold={}, own={}, stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial()
    return j[KEY]


def held(s: dict) -> int:
    b = get(s)
    return sum(h['a'] for h in b['hold'].values()) if b else 0


def _hold_ok(h) -> bool:
    return isinstance(h, dict) and set(h) == {'a', 'b'} and _int(h['a'], 1, MAX_BID) and _int(h['b'], 0, h['a'])


def _own_ok(k, x, kinds=OLD_KINDS) -> bool:
    return (_item(k) and isinstance(x, dict) and set(x) == OWN_KEYS and x['k'] in kinds and isinstance(x['t'], str)
            and 0 < len(x['t']) <= TEXT_MAX and _int(x['d'], 1, 10**6) and _int(x['p'], 0, MAX_BID) and _lot(x['lot']))


def validate(s: dict) -> None:
    """``s['journey']['uniq']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    j = s.get('journey')
    b = get(s)
    bad = 'Dữ liệu đấu giá trong bản lưu không hợp lệ.'
    if b is None:
        e.need(not isinstance(j, dict) or j.get(KEY) is None, bad, 'invalid_save')
        return
    need = lambda ok: e.need(ok, bad, 'invalid_save')
    need(set(b) == BLOCK_KEYS and b['v'] == VERSION)
    need(isinstance(b['hold'], dict) and len(b['hold']) <= HOLD_MAX and all(_lot(k) and _hold_ok(h) for k, h in b['hold'].items()))
    need(isinstance(b['own'], dict) and len(b['own']) <= OWN_MAX and all(_own_ok(k, x) for k, x in b['own'].items()))
    st = b['stats']
    need(isinstance(st, dict) and set(st) <= set(STATS) and all(_int(v) for v in st.values()))


def x_validate(s: dict) -> None:
    """``s['journey']['uniq_x']`` (optional). Shape only: an older build may sell a vehicle a plate is on (it does not
    know this block), so `on` may name a vehicle no longer owned; the views skip it, upgrade() drops it."""
    e = _core()
    j = s.get('journey')
    x = j.get(X_KEY) if isinstance(j, dict) else None
    if x is None:
        return
    need = lambda ok: e.need(ok, 'Dữ liệu đấu giá trong bản lưu không hợp lệ.', 'invalid_save')
    need(isinstance(x, dict) and set(x) == X_KEYS and x['v'] == X_VERSION)
    need(isinstance(x['own'], dict) and len(x['own']) <= OWN_MAX and all(_own_ok(k, o, C.NEW_KINDS) for k, o in x['own'].items()))
    need(isinstance(x['on'], dict) and len(x['on']) <= X_ON_MAX and all(_item(k) and isinstance(v, str) and VID_RE.fullmatch(v)
                                                                         for k, v in x['on'].items())
         and len(set(x['on'].values())) == len(x['on']))


def x_initial() -> dict:
    return dict(v=X_VERSION, own={}, on={})


def x_get(s: dict) -> dict | None:
    j = s.get('journey')
    x = j.get(X_KEY) if isinstance(j, dict) else None
    return x if isinstance(x, dict) else None


def x_on(s: dict) -> dict | None:
    x = x_get(s)
    return x['on'] if x else None


def legacy_on(s: dict) -> dict:
    """Before uniq_x: the dearest plate on the road vehicle ridden (how a plate showed until 16/10)."""
    b = get(s)
    j = s.get('journey') or {}
    g = j.get('garage') if isinstance(j.get('garage'), dict) else None
    ride = g.get('ride') if g else None
    if not b or not isinstance(ride, str) or not isinstance(g.get('cars'), dict) or ride not in g['cars']:
        return {}
    from .garage import VEHICLES
    if VEHICLES.get(ride, {}).get('group') not in C.PLATE_FIT['plate'] or ride in C.NO_PLATE:
        return {}
    best = max(((k, x) for k, x in b['own'].items() if x['k'] == 'plate'), key=lambda kx: (kx[1]['p'], kx[0]), default=None)
    return {best[0]: ride} if best else {}


def plates_on(s: dict) -> dict:
    """{plate item: vehicle id} as written (game/garage.py attached() checks it against the garage)."""
    on = x_on(s)
    return dict(on) if on is not None else legacy_on(s)


def x_ensure(s: dict) -> dict:
    """The block, created on its first write with the legacy plate where it showed."""
    j = s['journey']
    if not isinstance(j.get(X_KEY), dict):
        j[X_KEY] = dict(x_initial(), on=legacy_on(s))
    return j[X_KEY]


def owned(s: dict) -> dict:
    """Every item won, the three blocks: {item: {k, t, d, p, lot}}."""
    b, x, y = get(s), x_get(s), y_get(s)
    out = dict(b['own']) if b and isinstance(b.get('own'), dict) else {}
    if x and isinstance(x.get('own'), dict):
        out.update(x['own'])
    if y and isinstance(y.get('own'), dict):
        out.update({k: {f: o[f] for f in OWN_KEYS if f in o} for k, o in y['own'].items() if isinstance(o, dict)})
    return out


# ---------------------------------------------------------------- journey.uniq_y (20/10): 🪑 🐾 🧰
def y_get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    y = j.get(Y_KEY) if isinstance(j, dict) else None
    return y if isinstance(y, dict) else None


def y_ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(Y_KEY), dict):
        j[Y_KEY] = dict(v=Y_VERSION, own={})
    return j[Y_KEY]


def _y_own_ok(k, o) -> bool:
    return (isinstance(o, dict) and set(o) == Y_OWN_KEYS and o['g'] in (0, 1) and type(o['g']) is int
            and _own_ok(k, {f: o[f] for f in OWN_KEYS}, C.Y_KINDS))


def y_validate(s: dict) -> None:
    """``s['journey']['uniq_y']`` (optional)."""
    j = s.get('journey')
    y = j.get(Y_KEY) if isinstance(j, dict) else None
    if y is None:
        return
    need = lambda ok: _core().need(ok, 'Dữ liệu đấu giá trong bản lưu không hợp lệ.', 'invalid_save')
    need(isinstance(y, dict) and set(y) == Y_KEYS and y['v'] == Y_VERSION)
    need(isinstance(y['own'], dict) and len(y['own']) <= OWN_MAX and all(_y_own_ok(k, o) for k, o in y['own'].items()))


def y_upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields: keep every record that still makes sense (what waits is handed
    over by y_settle, after the next action). Absent stays absent."""
    if not isinstance(j, dict) or Y_KEY not in j:
        return
    y = j[Y_KEY]
    out = dict(v=Y_VERSION, own={})
    for k, o in list((y.get('own') if isinstance(y, dict) and isinstance(y.get('own'), dict) else {}).items())[:OWN_MAX]:
        if isinstance(o, dict) and set(o) >= OWN_KEYS:
            o = dict({f: o[f] for f in OWN_KEYS}, g=o['g'] if o.get('g') in (0, 1) and type(o.get('g')) is int else 0)
            if _y_own_ok(k, o):
                out['own'][k] = o
    if out != y:
        j[Y_KEY] = out


def y_settle(s: dict) -> str:
    """Hand over what still waits (g 0): a 🐾 piece once the wardrobe has room, a 🪑 piece missing from the bag. Cheap
    when there is nothing to do (game/journey.py after). The sentence for a message ('' when nothing moved)."""
    y = y_get(s)
    if not y or not isinstance(y.get('own'), dict):
        return ''
    out = ''
    for item, o in y['own'].items():
        if isinstance(o, dict) and o.get('g') == 0 and o.get('k') in C.Y_KINDS:
            line, ok = _grant_y(s, item, o['k'])
            if ok:
                o['g'] = 1
                out = out or line
    return out


def tool_pct(s: dict, career: str) -> tuple[int, dict | None]:
    """🧰 (percent, item) of the signature tool this save owns for `career`, or (0, None)."""
    it = C.TOOLS.get(career)
    y = y_get(s)
    o = (y.get('own') or {}).get(it['id']) if it and y and isinstance(y.get('own'), dict) else None
    if not isinstance(o, dict) or o.get('k') != 'tool':
        return 0, None
    return max(0, min(C.PCT_CAP, C.TOOL_PCT.get(it['tier'], 0))), it


def x_upgrade(j: dict) -> None:
    """Keep what still makes sense in uniq_x; the attachments of a vehicle no longer owned (sold by an older build)
    go back to their box. Absent stays absent."""
    if not isinstance(j, dict) or X_KEY not in j:
        return
    x = j[X_KEY]
    if not isinstance(x, dict):
        j[X_KEY] = x_initial()
        return
    out = x_initial()
    for k, o in list((x.get('own') if isinstance(x.get('own'), dict) else {}).items())[:OWN_MAX]:
        if isinstance(o, dict) and set(o) >= OWN_KEYS:
            o = {f: o[f] for f in OWN_KEYS}
            if _own_ok(k, o, C.NEW_KINDS):
                out['own'][k] = o
    g = j.get('garage') if isinstance(j.get('garage'), dict) else {}
    cars = g.get('cars') if isinstance(g.get('cars'), dict) else {}
    b = j.get(KEY) if isinstance(j.get(KEY), dict) else {}
    mine = set(out['own']) | set(b.get('own') or {})
    used = set()
    for k, v in list((x.get('on') if isinstance(x.get('on'), dict) else {}).items())[:X_ON_MAX]:
        if _item(k) and k in mine and isinstance(v, str) and VID_RE.fullmatch(v) and v in cars and v not in used:
            out['on'][k] = v
            used.add(v)
    if out != x:
        j[X_KEY] = out


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields: keep what still makes sense. Absent stays absent. Never drops a
    hold (it is money): a hold of an odd shape keeps its total."""
    if not isinstance(j, dict) or KEY not in j:
        x_upgrade(j)
        y_upgrade(j)
        return
    b = j[KEY]
    if not isinstance(b, dict):
        j[KEY] = initial()
        x_upgrade(j)
        y_upgrade(j)
        return
    out = initial()
    for k, h in list((b.get('hold') if isinstance(b.get('hold'), dict) else {}).items())[:HOLD_MAX]:
        if _lot(k) and isinstance(h, dict) and _int(h.get('a'), 1, MAX_BID):
            out['hold'][k] = dict(a=h['a'], b=h['b'] if _int(h.get('b'), 0, h['a']) else 0)
    for k, x in list((b.get('own') if isinstance(b.get('own'), dict) else {}).items())[:OWN_MAX]:
        if isinstance(x, dict) and set(x) >= OWN_KEYS:
            x = {f: x[f] for f in OWN_KEYS}
            if _own_ok(k, x):
                out['own'][k] = x
    st = b.get('stats') if isinstance(b.get('stats'), dict) else {}
    out['stats'] = {k: st[k] if _int(st.get(k)) else 0 for k in STATS}
    if out != b:
        j[KEY] = out
    y_upgrade(j)
    # A rolling-release node can receive an unknown painting, recording ownership
    # but not its furniture. Restore that entitlement once this catalogue knows it.
    r = j.get('reno')
    have = {x.get('k') for x in r.get('items', []) if isinstance(x, dict)} if isinstance(r, dict) else set()
    for iid, x in out['own'].items():
        if x['k'] == 'art' and C.ITEM.get(iid, {}).get('kind') == 'art' and f'uq_{iid}' not in have:
            _grant({'journey': j}, iid, 'art')
    x_upgrade(j)


# ---------------------------------------------------------------- money
def _have(s: dict) -> int:
    j = s['journey']
    b = bk.get(s)
    return max(0, j['wallet']) + (b['balance'] if b else 0)


ROW_MAX = 10**7   # one Sổ ví / bank log row's |amount| (journey.validate, bank.validate: every build)


def _parts(amount: int) -> list:
    """`amount` (≥ 0) as rows of at most ROW_MAX: a 50 M rod or lot is written in 5 rows."""
    return [min(ROW_MAX, amount - i) for i in range(0, max(0, amount), ROW_MAX)]


def ready_why(s: dict, amount: int) -> str:
    j = s['journey']
    if j['wallet'] < 0:
        return f'Ví đang nợ {fmt(-j["wallet"])} xu. Trả nợ trước nhé.'
    short = amount - _have(s)
    return f'Còn thiếu {fmt(short)} xu.' if short > 0 else ''


def _take(s: dict, amount: int, label: str) -> int:
    """`amount` from the wallet first, then the bank account (checked by the caller). The part from the bank."""
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    for part in _parts(cash):
        _jr()._wallet(j, -part, KIND, label[:120])
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        for part in _parts(rest):
            bk._log(b, j['life_day'], 'acc', label[:120], -part)
    return rest


def _give_back(s: dict, amount: int, bank_part: int, label: str) -> None:
    """A refund: what came from the bank account goes back there (when the account is still open), the rest to the
    wallet."""
    j = s['journey']
    b = bk.get(s)
    to_bank = min(amount, bank_part) if b else 0
    if to_bank:
        b['balance'] += to_bank
        for part in _parts(to_bank):
            bk._log(b, j['life_day'], 'acc', label[:120], part)
    for part in _parts(amount - to_bank):
        _jr()._wallet(j, part, KIND, label[:120])


# ---------------------------------------------------------------- commands
def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Đấu giá chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) <= {'lot', 'amount', 'anon', 'label'} and {'lot', 'amount'} <= set(p), 'Thông tin không hợp lệ.')
    lot, amount, anon = p['lot'], p['amount'], p.get('anon', False)
    need(_lot(lot), 'Chọn một phiên đấu giá nhé.')
    need(type(anon) is bool, 'Thông tin không hợp lệ.')
    amount = e.integer(amount, 1, MAX_BID)
    label = p.get('label') if isinstance(p.get('label'), str) else ''
    label = e.clean_text(label[:40], 40, 0) if label else ''
    label = label or lot
    b = get(s)
    before = b['hold'][lot]['a'] if b and lot in b['hold'] else 0
    if amount <= before:   # a second tap of the same bid: nothing to hold
        return dict(message=f'Bạn đã trả {fmt(before)} xu cho phiên này rồi.', duplicate=True,
                    auction=dict(lot=lot, amount=before, before=before, delta=0, anon=anon))
    need(len(b['hold']) < HOLD_MAX if b and lot not in b['hold'] else True, 'Bạn đang giữ tiền ở nhiều phiên quá.', 'limit')
    delta = amount - before
    why = ready_why(s, delta)
    need(not why, why, 'not_enough')
    from_bank = _take(s, delta, f'🔨 Giữ tiền đấu giá · {label}')
    b = _ensure(s)
    h = b['hold'].get(lot) or dict(a=0, b=0)
    b['hold'][lot] = dict(a=h['a'] + delta, b=h['b'] + from_bank)
    b['stats']['bids'] = b['stats'].get('bids', 0) + 1
    more = f' (giữ thêm {fmt(delta)} xu)' if before else ''
    return dict(message=f'🔨 Bạn trả {fmt(amount)} xu{more}. Bị trả cao hơn thì tiền về lại ngay.',
                auction=dict(lot=lot, amount=amount, before=before, delta=delta, anon=anon))


def apply_fx(s: dict, p: dict, amount: int) -> str:
    """A 'auction' live_effects row paid into the save (game/live_effects.py apply): what='back' a refund of escrow,
    what='win' the item (the escrow is burned)."""
    e = _core()
    need = e.need
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    lot, what = data.get('lot'), data.get('what')
    need(_lot(lot) and what in ('back', 'win'), 'Dữ liệu đấu giá không hợp lệ.')
    j = s['journey']
    b = _ensure(s)
    h = b['hold'].pop(lot, None)
    name = data.get('name') if isinstance(data.get('name'), str) else ''
    name = name[:TEXT_MAX] or lot
    if what == 'back':
        bank_part = h['b'] if h else 0
        if h and h['a'] > amount:   # a partial refund (never written today): keep the rest held
            keep_b = max(0, bank_part - amount)
            b['hold'][lot] = dict(a=h['a'] - amount, b=min(keep_b, h['a'] - amount))
            bank_part = bank_part - keep_b
        _give_back(s, amount, bank_part, f'🔨 Trả lại tiền giữ · {name}')
        return f'🔨 Có người trả cao hơn ở “{name}”: {fmt(amount)} xu đã về lại.'
    item, kind, text = data.get('item'), data.get('kind'), data.get('text')
    need(_item(item) and kind in KINDS and isinstance(text, str) and 0 < len(text) <= TEXT_MAX, 'Dữ liệu đấu giá không hợp lệ.')
    if h and h['a'] > amount:   # held more than the price (never written today): the difference goes back
        _give_back(s, h['a'] - amount, max(0, h['b'] - amount), f'🔨 Trả lại phần dư · {name}')
    rec = dict(k=kind, t=text, d=j['life_day'], p=amount, lot=lot)
    extra = None
    if kind in OLD_KINDS:
        if item not in b['own'] and len(b['own']) < OWN_MAX:
            b['own'][item] = rec
    elif kind in C.Y_KINDS:   # 🪑 🐾 🧰 (20/10): a third block, handed over at once when it can be
        y = y_ensure(s)
        extra = ''
        if item not in y['own'] and len(y['own']) < OWN_MAX:
            extra, ok = _grant_y(s, item, kind)
            y['own'][item] = dict(rec, g=1 if ok else 0)
    else:   # 🏎️ ✈️ ⚓ the newer kinds: beside the block an older build validates strictly
        x = x_ensure(s)
        if item not in x['own'] and len(x['own']) < OWN_MAX:
            x['own'][item] = rec
    b['stats']['won'] = b['stats'].get('won', 0) + 1
    b['stats']['xu'] = b['stats'].get('xu', 0) + amount
    if extra is None:
        extra = _grant(s, item, kind)
    return f'🔨 Bạn thắng “{text}” với {fmt(amount)} xu!{extra}'


def _grant(s: dict, item: str, kind: str) -> str:
    """The parts other modules show: a title worn from Phong cách, a painting in the bag of furniture."""
    if kind == 'title':
        from . import spend as sp
        from . import spend_content as SC
        if item in SC.STYLE_ITEMS:
            b = sp._ensure(s)
            if b['own'].get(item, 0) < SC.PERMANENT and (item in b['own'] or len(b['own']) < sp.OWN_MAX):
                b['own'][item] = SC.PERMANENT
            return ' Đeo ở Phong cách nhé.'
    if kind == 'art':
        from . import deco_content as DC
        k = f'uq_{item}'
        if k in DC.ITEMS:
            from . import reno as rn
            r = rn.ensure_block(s)
            if not any(x.get('k') == k for x in r['items']):
                r['items'].append(dict(id=rn.new_uid(r), k=k, r=None, x=None))
            return ' Tranh nằm trong túi đồ trang trí, treo lên tường nhé.'
    if kind == 'vehicle':   # 🏎️ a limited edition parks in the garage (game/garage.py)
        from . import garage as gr
        return gr.grant_limited(s, item)
    if kind in C.PLATE_KINDS:
        return ' Gắn biển ở Nhà xe nhé.'
    return ''


def _grant_y(s: dict, item: str, kind: str) -> tuple[str, bool]:
    """🪑 🐾 🧰 (20/10): (the sentence for the win's message, handed over). An item this build does not know (a newer
    build's catalogue on a rolling release) is kept as won and waits (g 0) for a build that knows it."""
    it = C.ITEM.get(item)
    if not it or it['kind'] != kind:
        return '', False
    if kind == 'decor':
        from . import deco_content as DC
        k = f'uq_{item}'
        if k not in DC.ITEMS:
            return '', False
        from . import reno as rn
        r = rn.ensure_block(s)
        if not any(x.get('k') == k for x in r['items']):
            r['items'].append(dict(id=rn.new_uid(r), k=k, r=None, x=None))
        return ' Món đồ nằm trong túi đồ trang trí, bày ở nhà nhé.', True
    if kind == 'petgear':
        from . import pet_wardrobe as pw
        from . import pet_wardrobe_content as W
        if it['piece'] not in W.ITEM:
            return '', False
        x = pw._ensure(s)
        if len(x['it']) >= pw.ITEM_MAX:
            return f' Tủ đồ thú cưng đã đủ {pw.ITEM_MAX} món: bỏ bớt một món là món này tự vào tủ.', False
        pw._new(x, it['piece'], max(0, min(pw.TOP, it['rank'])))
        return ' Món đồ đã vào Tủ đồ thú cưng, cho bé đeo nhé.', True
    if kind == 'tool':
        from . import journey as jr
        return f' Đồ nghề về {jr._place(it["career"])}: mỗi ca ở đó lợi nhuận +{C.TOOL_PCT.get(it["tier"], 0)}%.', True
    return '', True


def view_extra(it: dict) -> dict:
    """What the client draws and says beyond the lot's row: `use` (use_line), and a 🪑 piece's footprint (w, h, spot)."""
    out = {}
    use = use_line(it)
    if use:
        out['use'] = use
    if it.get('kind') == 'decor':
        from . import deco_content as DC
        P = DC.ITEMS.get(f'uq_{it["id"]}')
        if P:
            out.update(w=P['w'], h=P['h'], spot=P['spot'])
    return out


def use_line(it: dict) -> str:
    """What the item does once won, in a sentence (the lot card, Của tôi)."""
    k = it.get('kind')
    if k == 'vehicle':
        from .garage import VEHICLES, vname
        B = VEHICLES.get(it.get('base'))
        if not B:
            return ''
        return f'Về Nhà xe, đi như {vname(B)}. Gắn biển độc bản: thêm +{C.LIMITED_PCT}% mỗi ca (tối đa {C.PCT_CAP}%).'
    if k in C.PLATE_KINDS:
        return f'Gắn ở Nhà xe lên xe hợp loại rồi đi xe đó: lợi nhuận mỗi ca +3–{C.PCT_CAP}%.'
    if k == 'title':
        return 'Đeo ở Phong cách: hiện cạnh tên, có khung chat độc bản.'
    if k == 'art':
        return f'Treo tường ở nhà: Ấm cúng +{C.ART_COZY}.'
    if k == 'decor':
        from . import deco_content as DC
        P, B = DC.ITEMS.get(f'uq_{it["id"]}'), DC.ITEMS.get(it.get('base'))
        if not P or not B:
            return ''
        from .deco import lname
        return f'Bày ở nhà từ túi đồ: Ấm cúng +{P["cozy"]}, tính như {lname(B["name"])} trong các bộ.'
    if k == 'petgear':
        from . import pet_wardrobe as pw
        from . import pet_wardrobe_content as W
        P = W.ITEM.get(it.get('piece'))
        if not P:
            return ''
        bp = pw.BONUS_BP[max(0, min(pw.TOP, it['rank']))] + (pw.LUX_BONUS if P.get('lux') else 0)
        return f'Vào Tủ đồ thú cưng, cho bé đeo: thưởng làm việc +{bp / 100:g}% (trong trần của bé).'
    if k == 'tool':
        from . import journey as jr
        return (f'Tự dùng ở {jr._place(it["career"])}: lợi nhuận mỗi ca +{C.TOOL_PCT.get(it["tier"], 0)}% '
                f'(cùng biển đẹp tối đa {C.PCT_CAP}%).')
    return ''


# ---------------------------------------------------------------- views
def collection_score(s: dict) -> tuple[int, int, int]:
    """Rarity points, received items, legendary items. Bids/prices never buy extra points.

    Unknown operator-created numbers remain owned but unscored: their tier isn't in a save.
    Future catalogue ids can be scored on upgrade without rewriting ownership records.
    """
    own = owned(s)
    if not own:
        return 0, 0, 0
    items = [C.ITEM[k] for k, x in own.items()
             if k in C.ITEM and _own_ok(k, x, KINDS) and x['k'] == C.ITEM[k]['kind']]
    return (sum(it['collector_points'] for it in items), len(items), sum(it['tier'] == 3 for it in items))


def public(s: dict) -> dict | None:
    """Small (it rides on every state): the escrow and what was won. None until the first bid."""
    b = get(s)
    if not b:
        return None
    return dict(hold={k: h['a'] for k, h in b['hold'].items()}, held=sum(h['a'] for h in b['hold'].values()),
                own={k: dict(k=x['k'], t=x['t'], p=x['p']) for k, x in owned(s).items()}, stats=dict(b['stats']))


def show_view(s: dict) -> dict | None:
    """The player's card (game/social.py snapshot): the plate, the phone number, the titles, paintings and lands won."""
    own = owned(s)
    if not own:
        return None
    out = {}
    from .garage import bonus_now
    on_ride = bonus_now(s)
    if on_ride and on_ride['k'] == 'plate':   # 🔨 the plate on the vehicle ridden first
        out['plate'] = on_ride['t']
    for k, x in sorted(own.items(), key=lambda kv: -kv[1]['p']):
        if x['k'] in ('plate', 'phone') and x['k'] not in out:
            out[x['k']] = x['t']
        elif x['k'] in ('art', 'land', 'title', 'vehicle'):
            out.setdefault(x['k'], []).append(x['t'])
    for k in ('art', 'land', 'title', 'vehicle'):
        if k in out:
            out[k] = out[k][:3]
    return out


def worth(j: dict) -> int:
    """What the 💰 board counts: the escrow held for bids (still the player's money until a lot is won)."""
    b = j.get(KEY) if isinstance(j, dict) else None
    hold = b.get('hold') if isinstance(b, dict) else None
    if not isinstance(hold, dict):
        return 0
    return sum(h['a'] for h in hold.values() if isinstance(h, dict) and _int(h.get('a'), 1, MAX_BID))


def plates() -> frozenset:
    """Plate texts a free "biển tên" (game/garage.py) may not copy, folded."""
    return _PLATES


def fold_plate(text: str) -> str:
    import unicodedata
    t = unicodedata.normalize('NFD', str(text).upper())
    t = ''.join(ch for ch in t if not unicodedata.combining(ch)).replace('Đ', 'D')
    return re.sub(r'[^A-Z0-9]', '', t)


_PLATES = frozenset(fold_plate(it['name']) for it in C.ITEMS if it['kind'] in C.PLATE_KINDS)


def catalogue() -> dict:
    """Static lists for the client (bootstrap content, cached)."""
    return dict(tiers={str(k): dict(v) for k, v in C.TIERS.items()}, pct=C.PCT, quick=list(C.QUICK), kinds=[list(k) for k in C.KINDS],
                items=[dict(it, **({'colors': list(it['colors'])} if 'colors' in it else {}),
                            **({'alt': list(it['alt'])} if 'alt' in it else {}), **view_extra(it)) for it in C.ITEMS],
                snipe=C.SNIPE_SECS, account_days=C.ACCOUNT_DAYS)


# ---------------------------------------------------------------- the schedule
def vn_date(t: float | None = None) -> datetime.date:
    return datetime.datetime.fromtimestamp(now() if t is None else t, VN).date()


def _h(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16)


def plan(d: datetime.date) -> list[dict]:
    """The day's slots: [{id, slot, tier, starts_at, ends_at}], deterministic from the date."""
    n = C.COUNTS[_h('auc', d.isoformat()) % len(C.COUNTS)]
    base = datetime.datetime(d.year, d.month, d.day, C.OPEN_HOUR, C.OPEN_MIN, tzinfo=VN).timestamp()
    out = []
    for i in range(n):
        t0 = base + i * C.SLOT_GAP_MIN * 60
        out.append(dict(id=f'{d:%Y%m%d}-{i + 1}', slot=i + 1, tier=i + 1, starts_at=t0, ends_at=t0 + C.HOURS * 3600))
    t0 = datetime.datetime(d.year, d.month, d.day, C.PET_HOUR, C.PET_MIN, tzinfo=VN).timestamp()
    out.append(dict(id=f'{d:%Y%m%d}-p', slot=C.PET_SLOT, tier=0, starts_at=t0, ends_at=t0 + C.HOURS * 3600))
    return out


def pet_ready(it: dict, taken: set) -> bool:
    """🐾 Pet pieces go up cheapest first (owner 21/10 "đưa A trước, SS sau"): a piece waits until every pet piece of a
    lower rank is on the block or sold."""
    if it['kind'] != 'petgear':
        return True
    return all(x['id'] in taken for x in C.ITEMS if x['kind'] == 'petgear' and x['rank'] < it['rank'])


def pick(d: datetime.date, slot: int, tier_n: int, taken: set) -> dict | None:
    """The slot's item: deterministic from the date among the free items of its tier (then the lower tiers); the pet
    slot takes the cheapest free pet piece."""
    if slot == C.PET_SLOT:
        free = [it for it in C.ITEMS if it['kind'] == 'petgear' and it['id'] not in taken and pet_ready(it, taken)]
        if not free:
            return None
        low = sorted(it['id'] for it in free if it['rank'] == min(x['rank'] for x in free))
        return C.ITEM[low[_h('pick', d.isoformat(), slot) % len(low)]]
    for t in range(tier_n, 0, -1):
        free = sorted(it['id'] for it in C.ITEMS if it['tier'] == t and it['kind'] != 'petgear' and it['id'] not in taken)
        if d.isoformat() <= C.FEATURE_TO:   # 🚗 biển 179 (owner 22/10, #476): its tier's slot takes one of them first
            free = [i for i in free if i in C.FEATURED] or free
        if free:
            return C.ITEM[free[_h('pick', d.isoformat(), slot) % len(free)]]
    return None


def _taken(db) -> set:
    return {r['item'] for r in db.execute("SELECT item FROM auction_lots WHERE status IN ('open','sold')").fetchall()}


def _insert_lot(db, lid: str, it: dict, tier_n: int, t0: float, t1: float, src: str) -> bool:
    T = tier(tier_n)
    extra = {k: it[k] for k in ('artist', 'year', 'colors', 'motif', 'base', 'where', 'medium', 'story', 'paint', 'serial',
                                'piece', 'rank', 'career', 'glow')
             if k in it}
    own = tier_n == it.get('tier')   # an item's premium starting price, unless the operator moved it to another tier
    start, step = (it.get('start') or T['start'], it.get('step') or T['step']) if own else (T['start'], T['step'])
    return db.execute(
        'INSERT INTO auction_lots(id, item, kind, tier, name, emoji, data, start, step, starts_at, ends_at, planned_end, '
        "status, src, created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'open',?,?) ON CONFLICT DO NOTHING",
        (lid, it['id'], it['kind'], tier_n, it['name'][:TEXT_MAX], it['emoji'], json.dumps(extra, ensure_ascii=False),
         start, step, t0, t1, t1, src, now())).rowcount == 1


_planned: dict = {}               # date -> monotonic of the last check (bounded: one entry)
_PLAN_LOCK = threading.Lock()


def ensure_plan(store, t: float | None = None, force: bool = False) -> int:
    """Create today's lots if they are missing (once, whoever comes first). The number created."""
    d = vn_date(t)
    with _PLAN_LOCK:
        if not force and _planned.get(d) is not None and time.monotonic() - _planned[d] < 300:
            return 0
    slots = plan(d)

    def run(db):
        db.execute('SELECT pg_advisory_xact_lock(17824, 1)')
        have = {r['id'] for r in db.execute('SELECT id FROM auction_lots WHERE id IN (%s)' % ','.join('?' * len(slots)),
                                             [x['id'] for x in slots]).fetchall()}
        taken, made = _taken(db), 0
        for x in slots:
            if x['id'] in have:
                continue
            it = pick(d, x['slot'], x['tier'], taken)
            if it is None:
                continue
            if _insert_lot(db, x['id'], it, it['tier'], x['starts_at'], x['ends_at'], 'plan'):
                taken.add(it['id'])
                made += 1
        return made
    made = store.transaction(run)
    with _PLAN_LOCK:
        _planned.clear()
        _planned[d] = time.monotonic()
    if made:
        _VIEW.clear()
    return made


# ---------------------------------------------------------------- database: the bid (the save's own transaction)
def _account(db, sid: str):
    return db.execute('SELECT display, created_at FROM accounts WHERE sid=?', (sid,)).fetchone()


def old_enough(db, sid: str, t: float | None = None) -> bool:
    r = _account(db, sid)
    if not r:
        return False
    cut = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime((now() if t is None else t) - C.ACCOUNT_DAYS * DAY))
    return str(r['created_at']) <= cut


def display(db, sid: str, anon: bool) -> str:
    """The name a lot shows: the account's display name (already through accounts.clean_display; an offensive one is
    never shown), Ẩn danh, or a guest's placeholder."""
    if anon:
        return C.ANON
    r = _account(db, sid)
    name = str(r['display'])[:24] if r and r['display'] else ''
    if name:
        from .accounts import offensive_name
        if offensive_name(name):
            name = ''
    return name or C.GONE


def _refund_rows(db, sid: str, lot: str) -> list:
    return [dict(r) for r in db.execute("SELECT id, amount FROM live_effects WHERE sid=? AND kind=? AND status='pending' AND id LIKE ?",
                                        (sid, FX, f'auc:{lot}:%')).fetchall()]


def _refund(db, sid: str, lot: dict, amount: int, n: int) -> str:
    """Escrow back to a save through live_effects (paid at its next load, or at once when the page hears of it)."""
    rid = f'auc:{lot["id"]}:{pid_of(sid)[:10]}:b{n}'
    db.execute('INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
               (rid, sid, FX, int(amount), json.dumps(dict(lot=lot['id'], what='back', name=lot['name'][:TEXT_MAX], src='auction'),
                                                       ensure_ascii=False), 'pending', now()))
    return rid


def _notify(db, event: dict) -> None:
    from . import live_chat
    live_chat.notify(db, event)


def command_commit(db, sid: str, action: str, before: dict, after: dict, result) -> None:
    """jr_auc_bid in the save's transaction (game/storage.py). A GameError rolls the whole command back."""
    if action != 'jr_auc_bid':
        return
    e = _core()
    need = e.need
    r = (result or {}).get('auction') if isinstance(result, dict) else None
    if not isinstance(r, dict) or not r.get('delta'):
        return   # a duplicate: nothing held, nothing to write
    t = now()
    lid, amount, prev_hold, anon = r['lot'], int(r['amount']), int(r['before']), bool(r['anon'])
    lot = db.execute('SELECT * FROM auction_lots WHERE id=? FOR UPDATE', (lid,)).fetchone()
    need(lot is not None, 'Không có phiên đấu giá này.', 'not_found')
    lot = dict(lot)
    need(lot['status'] == 'open' and lot['ends_at'] > t, 'Phiên này đã kết thúc.', 'closed')
    need(lot['starts_at'] <= t, 'Phiên này chưa mở.', 'not_open')
    need(old_enough(db, sid, t), f'Cần tài khoản đã đăng ký đủ {C.ACCOUNT_DAYS} ngày để đấu giá.', 'too_new')
    mine = db.execute('SELECT * FROM auction_bids WHERE lot=? AND sid=?', (lid, sid)).fetchone()
    mine = dict(mine) if mine else None
    pend = _refund_rows(db, sid, lid)
    db_hold = (mine['held'] if mine else 0) + sum(int(x['amount']) for x in pend)
    need(prev_hold == db_hold, 'Tiền giữ đang cập nhật, mở lại phiên rồi thử nhé.', 'auction_sync')
    lead = lot['high_sid'] == sid
    floor = (lot['high'] + 1) if lead else min_next(lot['high'], lot['start'], lot['step'], lot['bids'])
    need(amount >= floor, f'Giá mới nhất {fmt(lot["high"])} xu: trả ít nhất {fmt(floor)} xu nhé.' if lot['bids'] else
         f'Giá khởi điểm {fmt(lot["start"])} xu.', 'outbid')
    for x in pend:   # refunds not paid into the save yet: reused as escrow (this save still counts them as held)
        need(db.execute("UPDATE live_effects SET status='void', applied_at=? WHERE id=? AND status='pending'", (t, x['id'])).rowcount == 1,
             'Tiền giữ đang cập nhật, thử lại nhé.', 'auction_sync')
    prev = None
    if lot['high_sid'] and not lead:
        p = db.execute('SELECT * FROM auction_bids WHERE lot=? AND sid=?', (lid, lot['high_sid'])).fetchone()
        if p and p['held'] > 0:
            n = int(p['refunds']) + 1
            _refund(db, p['sid'], lot, int(p['held']), n)
            push = t - float(p['pushed_at'] or 0) >= PUSH_EVERY
            db.execute('UPDATE auction_bids SET held=0, refunds=?, pushed_at=? WHERE lot=? AND sid=?',
                       (n, t if push else p['pushed_at'], lid, p['sid']))
            if push:
                from . import push as pu
                pu.queue(db, p['sid'], 'auction', f'🔨 Có người trả {fmt(amount)} xu cho “{lot["name"]}”. Tiền giữ đã về ví.', '/?open=auction')
            prev = p['sid']
    if mine:
        db.execute('UPDATE auction_bids SET amount=?, held=?, anon=?, n=n+1, at=? WHERE lot=? AND sid=?',
                   (amount, amount, 1 if anon else 0, t, lid, sid))
    else:
        db.execute('INSERT INTO auction_bids(lot, sid, amount, held, anon, n, refunds, at, pushed_at) VALUES(?,?,?,?,?,1,0,?,0)',
                   (lid, sid, amount, amount, 1 if anon else 0, t))
    ends = lot['ends_at']
    if ends - t <= C.SNIPE_SECS:
        ends = min(ends + C.SNIPE_SECS, lot['planned_end'] + C.SNIPE_CAP_SECS)
    need(db.execute('UPDATE auction_lots SET high=?, high_sid=?, high_anon=?, bids=bids+1, seq=seq+1, ends_at=? WHERE id=? AND seq=?',
                    (amount, sid, 1 if anon else 0, ends, lid, lot['seq'])).rowcount == 1, 'Giá vừa đổi, thử lại nhé.', 'outbid')
    _VIEW.clear()
    _notify(db, dict(op='auction', lot=lid, high=amount, n=int(lot['bids']) + 1, ends=round(ends, 1),
                     next=min_next(amount, lot['start'], lot['step'], 1), lead=pid_of(sid), name=display(db, sid, anon),
                     prev=pid_of(prev) if prev else ''))


def fx_commit(db, sid: str, result) -> None:
    """live_fx of an 'auction' row, in the save's transaction: the row flips pending → applied here, so a refund is
    paid once and a refund voided by a new bid never (a GameError rolls the payment back)."""
    live = (result or {}).get('live') if isinstance(result, dict) else None
    if not isinstance(live, dict) or live.get('kind') != FX or live.get('already'):
        return
    _core().need(db.execute("UPDATE live_effects SET status='applied', applied_at=? WHERE id=? AND sid=? AND status='pending'",
                            (now(), live.get('id'), sid)).rowcount == 1, 'Khoản này đã xử lý rồi.', 'auction_sync')


# ---------------------------------------------------------------- settlement (housekeeping, idempotent)
def settle_one(store, lid: str, t: float | None = None) -> str | None:
    """Close one lot whose end has passed: its new status, or None when there was nothing to do (already settled,
    not over yet). Safe to run any number of times from any worker."""
    t = now() if t is None else t

    def run(db):
        lot = db.execute('SELECT * FROM auction_lots WHERE id=? FOR UPDATE', (lid,)).fetchone()
        if not lot or lot['status'] != 'open' or lot['ends_at'] > t:
            return None
        lot = dict(lot)
        win = lot['high_sid']
        if win and not db.execute('SELECT 1 FROM sessions WHERE sid=?', (win,)).fetchone():
            win = ''   # the leader erased their data meanwhile: their escrow went with the save
            status = 'void'
        else:
            status = 'sold' if win else 'unsold'
        name = display(db, win, bool(lot['high_anon'])) if win else ''
        db.execute('UPDATE auction_lots SET status=?, winner_sid=?, winner_name=?, price=?, settled_at=?, seq=seq+1 WHERE id=? AND status=?',
                   (status, win, name, lot['high'] if win else 0, t, lid, 'open'))
        for b in db.execute('SELECT * FROM auction_bids WHERE lot=? AND held>0', (lid,)).fetchall():
            if b['sid'] == lot['high_sid']:
                continue   # the winner's escrow is burned below (a leader who erased their data: it went with the save)
            n = int(b['refunds']) + 1
            _refund(db, b['sid'], lot, int(b['held']), n)
            db.execute('UPDATE auction_bids SET held=0, refunds=? WHERE lot=? AND sid=?', (n, lid, b['sid']))
        if lot['high_sid']:
            db.execute('UPDATE auction_bids SET held=0 WHERE lot=? AND sid=?', (lid, lot['high_sid']))
        if win:
            text = _won_text(lot, name)
            data = dict(lot=lid, what='win', item=lot['item'], kind=lot['kind'], text=text, name=lot['name'][:TEXT_MAX], src='auction')
            db.execute('INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                       (f'auc:{lid}:win', win, FX, int(lot['high']), json.dumps(data, ensure_ascii=False), 'pending', t))
            from . import push as pu
            pu.queue(db, win, 'auction', f'🔨 Bạn thắng “{text}” với {fmt(lot["high"])} xu!', '/?open=auction')
            if lot['high'] >= NEWS_FROM:
                from . import marriage
                marriage._post_news(db, 'auction', f'auc:{lid}', f'🔨 {name} thắng “{text}” với {fmt(lot["high"])} xu!', '', '')
        _notify(db, dict(op='auction_end', lot=lid, status=status, price=int(lot['high']) if win else 0, name=name,
                         win=pid_of(win) if win else ''))
        return status
    out = store.transaction(run)
    if out:
        _VIEW.clear()
    return out


def _won_text(lot: dict, name: str) -> str:
    """The item's text in the winner's save: a landmark gets the winner's name ("Hồ Lan Mây")."""
    if lot['kind'] == 'land':
        try:
            base = json.loads(lot['data'] or '{}').get('base') or ''
        except ValueError:
            base = ''
        who = 'Vô Danh' if name in (C.ANON, C.GONE, '') else name
        return f'{base} {who}'.strip()[:TEXT_MAX]
    return str(lot['name'])[:TEXT_MAX]


def settle_due(store, t: float | None = None, limit: int = 20) -> list:
    t = now() if t is None else t
    with store.connect() as db:
        ids = [r['id'] for r in db.execute("SELECT id FROM auction_lots WHERE status='open' AND ends_at<=? ORDER BY ends_at LIMIT ?",
                                           (t, limit)).fetchall()]
    return [(lid, s) for lid in ids if (s := settle_one(store, lid, t))]


def announce_open(store, t: float | None = None) -> int:
    """🔨 A line on the street's ticker for every lot that opened in the last ANNOUNCE_SECS, once (news.ref is unique)."""
    t = now() if t is None else t
    with store.connect() as db:
        rows = db.execute("SELECT id, name, emoji, start FROM auction_lots WHERE status='open' AND starts_at<=? AND starts_at>? "
                          'ORDER BY starts_at', (t, t - ANNOUNCE_SECS)).fetchall()
    if not rows:
        return 0
    from . import marriage

    def run(db):
        return sum(marriage._post_news(db, 'auction', f'auc-open:{r["id"]}',
                                       f'🔨 Nhà đấu giá vừa mở phiên: {r["emoji"]} {r["name"]}, khởi điểm {fmt(int(r["start"]))} xu, '
                                       f'trả giá trong {C.HOURS} giờ!', '', '') for r in rows)
    return store.transaction(run)


def run_housekeeping(store) -> None:
    """server.py maintenance (every 30 s, one process): today's lots, the ticker line of a lot that opened, then the
    lots that ended. Never raises."""
    import sys
    try:
        ensure_plan(store)
        announce_open(store)
        for lid, st in settle_due(store):
            sys.stderr.write(f'[auction] {lid}: {st}\n')
    except Exception as e:  # noqa: BLE001 - housekeeping never takes the server down
        sys.stderr.write(f'[auction] housekeeping: {type(e).__name__}\n')


# ---------------------------------------------------------------- the page (GET /api/auction)
VIEW_SECS = 1.0
_VIEW: dict = {}           # 'v' -> (monotonic, rows): one entry, bounded
_VIEW_LOCK = threading.Lock()


def _lot_view(r) -> dict:
    try:
        data = json.loads(r['data'] or '{}')
    except ValueError:
        data = {}
    it = C.ITEM.get(r['item'], {})
    data = dict(data if isinstance(data, dict) else {}, **{k: it[k] for k in ('medium', 'story') if k in it})
    if it:
        data.update(view_extra(it))
    out = dict(id=r['id'], item=r['item'], kind=r['kind'], tier=int(r['tier']), name=r['name'], emoji=r['emoji'],
               collector_points=it.get('collector_points', 0), rarity=it.get('tier'),
               start=int(r['start']), step=int(r['step']), starts_at=float(r['starts_at']), ends_at=float(r['ends_at']),
               status=r['status'], high=int(r['high']), bids=int(r['bids']),
               next=min_next(int(r['high']), int(r['start']), int(r['step']), int(r['bids'])), **({'data': data} if data else {}))
    if r['status'] != 'open':
        out.update(price=int(r['price']), winner=r['winner_name'] or '', settled_at=float(r['settled_at'] or 0))
    return out


def _rows(store) -> dict:
    with _VIEW_LOCK:
        hit = _VIEW.get('v')
        if hit and time.monotonic() - hit[0] < VIEW_SECS:
            return hit[1]
    with store.connect() as db:
        live = db.execute("SELECT * FROM auction_lots WHERE status='open' ORDER BY starts_at, id LIMIT 12").fetchall()
        names = {}
        for r in live:
            if r['high_sid']:
                names[r['id']] = display(db, r['high_sid'], bool(r['high_anon']))
        past = db.execute("SELECT * FROM auction_lots WHERE status<>'open' ORDER BY settled_at DESC, id LIMIT ?", (HISTORY,)).fetchall()
        lands = db.execute("SELECT * FROM auction_lots WHERE status='sold' AND kind='land' ORDER BY settled_at").fetchall()
        burned = db.execute("SELECT COALESCE(SUM(price), 0) AS xu, COUNT(*) AS n FROM auction_lots WHERE status='sold'").fetchone()
    out = dict(lots=[dict(_lot_view(r), who=names.get(r['id'], '')) for r in live], past=[_lot_view(r) for r in past],
               lands=[dict(id=r['item'], name=_won_text(dict(r), r['winner_name']), emoji=r['emoji'],
                           where=(json.loads(r['data'] or '{}').get('where') or ''), by=r['winner_name']) for r in lands],
               burned=int(burned['xu']), sold=int(burned['n']))
    with _VIEW_LOCK:
        _VIEW.clear()
        _VIEW['v'] = (time.monotonic(), out)
    return out


def view(store, token: str | None) -> dict:
    """Open and upcoming lots, the last HISTORY settled, the named landmarks, and mine (my bids, can I bid)."""
    try:
        ensure_plan(store)
        if any(x['ends_at'] <= now() for x in _rows(store)['lots']):
            settle_due(store)
    except Exception:  # noqa: BLE001 - a page never fails because of the housekeeping
        pass
    rows = _rows(store)
    out = dict(rows, now=now())
    sid = store.key(token) if isinstance(token, str) and 16 <= len(token) <= 128 else None
    if sid:
        me = pid_of(sid)
        with store.connect() as db:
            mine = {r['lot']: dict(amount=int(r['amount']), held=int(r['held']))
                    for r in db.execute('SELECT lot, amount, held FROM auction_bids WHERE sid=? AND lot IN (%s)'
                                        % (','.join('?' * len(rows['lots'])) or "''"), [sid] + [x['id'] for x in rows['lots']]).fetchall()}
            can = old_enough(db, sid)
            acct = bool(_account(db, sid))
        out['me'] = dict(pid=me, bids=mine, can=can, why='' if can else (f'Cần tài khoản đủ {C.ACCOUNT_DAYS} ngày' if acct else 'Cần đăng ký tài khoản'))
    return out


# ---------------------------------------------------------------- admin (POST /api/admin/auction)
def admin_add(store, by: str, data: dict) -> dict:
    """Add a lot: {item} from the catalogue (free: not open, not sold), or {kind: plate|phone, text} made up by the
    operator (or reg|hull: a plane registration, a yacht's name); tier 1–3, hours 1–72, starts in `delay` minutes (0–10080)."""
    from .social import SocialError
    def need(ok, msg):
        if not ok:
            raise SocialError(msg, 'bad_auction')
    data = data if isinstance(data, dict) else {}
    hours, delay = data.get('hours', C.HOURS), data.get('delay', 0)
    need(type(hours) is int and 1 <= hours <= 72 and type(delay) is int and 0 <= delay <= 10080, 'Thời gian không hợp lệ.')
    t0 = now() + delay * 60
    iid = data.get('item')
    if iid is not None:
        need(isinstance(iid, str) and iid in C.ITEM, 'Không có món này trong danh mục.')
        it = C.ITEM[iid]
    else:
        kind, text = data.get('kind'), data.get('text')
        need(kind in ('plate', 'phone', 'reg', 'hull') and isinstance(text, str) and 3 <= len(text.strip()) <= 16, 'Biển số/số điện thoại 3–16 ký tự.')
        text = text.strip()
        it = dict(id='x_' + hashlib.sha256(f'{kind}|{text}'.encode()).hexdigest()[:12], kind=kind, name=text, emoji=C.KIND_EMOJI[kind])
    tier_n = data.get('tier', it.get('tier', 1))
    need(tier_n in C.TIERS, 'Hạng 1, 2 hoặc 3.')
    lid = 'a' + format(int(t0 * 1000), 'x')[-10:]

    def run(db):
        db.execute('SELECT pg_advisory_xact_lock(17824, 1)')
        need(it['id'] not in _taken(db), 'Món này đang đấu giá hoặc đã có chủ.')
        need(_insert_lot(db, lid, it, tier_n, t0, t0 + hours * 3600, f'admin:{str(by)[:40]}'), 'Trùng mã phiên, thử lại.')
    store.transaction(run)
    _VIEW.clear()
    return dict(ok=True, id=lid, item=it['id'], name=it['name'], starts_at=t0, ends_at=t0 + hours * 3600)


def admin_view(store) -> dict:
    with store.connect() as db:
        rows = db.execute('SELECT * FROM auction_lots ORDER BY created DESC LIMIT 60').fetchall()
        taken = _taken(db)
    return dict(lots=[dict(_lot_view(r), src=r['src']) for r in rows], free=[it['id'] for it in C.ITEMS if it['id'] not in taken])


# ---------------------------------------------------------------- account deletion
def forget(db, sid: str) -> None:
    """A player erased their data: their past wins stay in the history under the name shown then; their escrow went
    with the save (a lot they lead is voided at its end, the item back to the pool)."""
    db.execute("UPDATE auction_lots SET winner_sid='' WHERE winner_sid=? AND status<>'open'", (sid,))
    _VIEW.clear()
