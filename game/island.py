"""🏝️ Đảo riêng: buying, keeping and selling a private island (story mode; catalogue: game/island_content.py).

* Bought in full (jr_island_buy {id, confirm}): the cash in the wallet first, then the bank account, never a loan,
  never with a wallet in debt (game/lux.py ready_why). A Sổ ví row holds at most ROW_MAX xu (journey.validate on this
  build and on every build it may be rolled back to), so the wallet part of a 15M+ purchase is written as several
  rows of kind 'life' (a kind every build knows). Several islands may be owned, one of each.
* 🧾 Phí giữ đảo: `bp` basis points of the price paid a tháng (game/upkeep.py's month, bk.MONTH_DAYS life days),
  accrued every life-day morning, billed on the month's day like the villas (game/lux.py on_life_day): the wallet
  (never below 0, kind 'upkeep'), then the bank account; what both lack is waived, never owed. Nothing before
  `upk.since` is billed.
* Selling back (jr_island_sell {id, confirm}): SELL_PCT % of the price paid into the wallet (rows of ≤ ROW_MAX); an
  open trip to it ends with the sale (game/island_trips.py command_commit, in the save's transaction). Its buildings
  (game/island_build.py, journey.islb) are razed with it: their salvage comes back too.
* Trips with friends live in PostgreSQL (game/island_trips.py) and the live service (live/island.py), never here.

State `s['journey']['island']` (absent until the first purchase; journey.validate allows extra keys, so 2.4.34 and
older keep it untouched, never bill it and never show it: tests/test_island_compat.py proves it on those trees):
    v      VERSION
    own    {island id: {d: life day bought, p: price paid}}   an id a newer build wrote is kept by shape, not shown
    upk    {since, day, acc (milli-xu), paid}
    stats  {bought, sold, xu}
"""
from __future__ import annotations

from . import bank as bk
from . import island_content as C

VERSION = 1
KEY = 'island'
KIND = 'life'                     # an existing wallet history kind (journey.HISTORY_KINDS of every build)
ROW_MAX = 10**7                   # journey.validate: a 'life' wallet row is within ±10,000,000 xu
OWN_MAX = 16
PRICE_MAX = 10**9
BIG = 10**12
CATCH_UP = 400
COMMANDS = ('jr_island_buy', 'jr_island_sell')
BLOCK_KEYS = frozenset({'v', 'own', 'upk', 'stats'})
UPK_KEYS = frozenset({'since', 'day', 'acc', 'paid'})
STATS = ('bought', 'sold', 'xu')
UPKEEP_LABEL = 'Phí giữ đảo'
ISLAND = {i['id']: i for i in C.ISLANDS}


def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _lx():
    from . import lux
    return lux


def _fmt(n: int) -> str:
    return bk._fmt(n)


def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


def _id(v) -> bool:
    return isinstance(v, str) and 1 <= len(v) <= 24 and all(c.isdigit() or c == '_' or 'a' <= c <= 'z' for c in v)


def initial(day: int = 1) -> dict:
    return dict(v=VERSION, own={}, upk=None, stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def owned(s: dict) -> list[str]:
    """The islands of this build that the save owns."""
    b = get(s)
    return [i for i in (b['own'] if b and isinstance(b.get('own'), dict) else {}) if i in ISLAND]


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial(j['life_day'])
    b = j[KEY]
    if b['upk'] is None:   # bills start the day the block does
        b['upk'] = dict(since=j['life_day'], day=j['life_day'], acc=0, paid=0)
    return b


def sell_price(paid: int) -> int:
    return max(0, int(paid) * C.SELL_PCT // 100 // 10 * 10)


def _bp(iid: str) -> int:
    return ISLAND[iid]['bp'] if iid in ISLAND else 0   # an id this build does not know pays nothing here


def _daily_milli(price: int, bp: int) -> int:
    return max(0, int(price)) * bp // (10 * bk.MONTH_DAYS)


def month_of(iid: str, price: int) -> int:
    return (_daily_milli(price, _bp(iid)) * bk.MONTH_DAYS + 500) // 1000


def monthly(s: dict) -> int:
    b = get(s)
    if not b:
        return 0
    m = sum(_daily_milli(x['p'], _bp(i)) for i, x in b['own'].items() if isinstance(x, dict))
    return (m * bk.MONTH_DAYS + 500) // 1000


# ---------------------------------------------------------------- money
def _wallet_rows(j: dict, amount: int, kind: str, label: str) -> None:
    """`amount` (signed) in or out of the wallet as rows of at most ROW_MAX xu each."""
    sign, left = (1 if amount > 0 else -1), abs(int(amount))
    while left:
        part = min(left, ROW_MAX)
        _jr()._wallet(j, sign * part, kind, label[:120])
        left -= part


def _take(s: dict, amount: int, label: str) -> str:
    """`amount` from the wallet first, then the bank account (the caller checked it is there). Where it came from."""
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _wallet_rows(j, -cash, KIND, label)
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label[:120], -rest)
    if rest and cash:
        return f'{_fmt(cash)} xu tiền mặt và {_fmt(rest)} xu từ tài khoản'
    return f'{_fmt(amount)} xu từ tài khoản' if rest else f'{_fmt(amount)} xu tiền mặt'


def _bill(s: dict, amount: int, label: str, day: int) -> int:
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _wallet_rows(j, -cash, 'upkeep', label)
    b = bk.get(s)
    rest = min(amount - cash, b['balance']) if b else 0
    if rest > 0:
        b['balance'] -= rest
        bk._log(b, day, 'acc', label, -rest)
    return cash + max(0, rest)


def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Catch the bills up to journey.life_day (idempotent: the day counter; after game/lux.py's bills)."""
    j = s.get('journey')
    b = get(s)
    if not isinstance(j, dict) or not j.get('story') or not b or not isinstance(b.get('upk'), dict):
        return []
    u = b['upk']
    target = int(j['life_day'])
    notes = []
    u['day'] = max(u['day'], target - CATCH_UP)
    while u['day'] < target:
        u['day'] += 1
        u['acc'] = min(BIG, u['acc'] + sum(_daily_milli(x['p'], _bp(i)) for i, x in b['own'].items()))
        if u['day'] % bk.MONTH_DAYS == 0:
            amount, u['acc'] = u['acc'] // 1000, u['acc'] % 1000
            if amount <= 0:
                continue
            n = sum(1 for i in b['own'] if _bp(i))
            got = _bill(s, amount, f'{UPKEEP_LABEL} · {n} đảo', u['day'])
            u['paid'] = min(BIG, u['paid'] + got)
            line = f'🏝️ {UPKEEP_LABEL} (người trông đảo, cầu tàu, máy phát điện): {_fmt(amount)} xu.'
            if got < amount:
                line += f' Thiếu {_fmt(amount - got)} xu được miễn, không tính nợ.'
            notes.append(line)
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- vehicles that can take friends
def seats_of(vid: str) -> tuple[int, str] | None:
    """(seats with the owner, where it lands) of a vehicle id, None: it cannot carry guests to an island."""
    if vid in C.SEATS:
        return C.SEATS[vid]
    from . import garage
    v = garage.VEHICLES.get(vid)
    return C.GROUP_SEATS.get(v['group']) if v else None


def vehicles(s: dict) -> list[dict]:
    """The yachts and planes the save owns (game/garage.py, game/lux.py), with their seats, most seats first."""
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict):
        return []
    from . import garage
    out = []
    cars = (j.get('garage') or {}).get('cars') if isinstance(j.get('garage'), dict) else None
    for vid in (cars if isinstance(cars, dict) else {}):
        v, seat = garage.VEHICLES.get(vid), seats_of(vid)
        if v and seat:
            out.append(dict(id=vid, emoji=v['emoji'], name=v['name'], seats=seat[0], arrive=seat[1]))
    lux = j.get('lux') if isinstance(j.get('lux'), dict) else None
    for vid in (lux.get('own') if lux and isinstance(lux.get('own'), dict) else {}):
        a = _lx().ASSET.get(vid)
        seat = C.SEATS.get(vid)
        if a and seat:
            out.append(dict(id=vid, emoji=a['emoji'], name=a['name'], seats=seat[0], arrive=seat[1]))
    return sorted(out, key=lambda x: (-x['seats'], x['id']))


# ---------------------------------------------------------------- save
def _own_ok(d) -> bool:
    return isinstance(d, dict) and len(d) <= OWN_MAX and all(
        _id(k) and isinstance(x, dict) and set(x) == {'d', 'p'} and _int(x['d'], 1, 10**6) and _int(x['p'], 1, PRICE_MAX)
        for k, x in d.items())


def _upk_ok(u, day: int) -> bool:
    return u is None or (isinstance(u, dict) and set(u) == UPK_KEYS and _int(u['since'], 1, 10**6) and _int(u['day'], 1, 10**6)
                         and u['since'] <= u['day'] <= max(u['since'], day) and _int(u['acc']) and _int(u['paid']))


def validate(s: dict) -> None:
    """``s['journey']['island']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    j = s.get('journey')
    b = get(s)
    bad = 'Dữ liệu đảo riêng trong bản lưu không hợp lệ.'
    if b is None:
        e.need(not isinstance(j, dict) or j.get(KEY) is None, bad, 'invalid_save')
        return
    need = lambda ok: e.need(ok, bad, 'invalid_save')
    need(set(b) == BLOCK_KEYS and b['v'] == VERSION and _own_ok(b['own']))
    need(_upk_ok(b['upk'], int(j.get('life_day', 1)) if _int(j.get('life_day'), 1, 10**6) else 1))
    st = b['stats']
    need(isinstance(st, dict) and set(st) <= set(STATS) and all(_int(v) for v in st.values()))


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep what still makes sense."""
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    day = j.get('life_day') if _int(j.get('life_day'), 1, 10**6) else 1
    if not isinstance(b, dict):
        j[KEY] = initial(day)
        return
    out = initial(day)
    own = b.get('own') if isinstance(b.get('own'), dict) else {}
    out['own'] = {k: dict(d=x['d'], p=x['p']) for k, x in list(own.items())[:OWN_MAX]
                  if _id(k) and isinstance(x, dict) and _int(x.get('d'), 1, 10**6) and _int(x.get('p'), 1, PRICE_MAX)}
    u = b.get('upk')
    if isinstance(u, dict) and set(u) >= UPK_KEYS:
        u = {k: u[k] for k in UPK_KEYS}
        out['upk'] = u if _upk_ok(u, day) else None
    st = b.get('stats') if isinstance(b.get('stats'), dict) else {}
    out['stats'] = {k: st[k] if _int(st.get(k)) else 0 for k in STATS}
    if out != b:
        j[KEY] = out


# ---------------------------------------------------------------- commands
def action(s: dict, name: str, p: dict) -> dict:
    need = _core().need
    j = s['journey']
    need(j.get('story'), 'Đảo riêng chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) <= {'id', 'confirm'} and 'id' in p, 'Thông tin không hợp lệ.')
    return _buy(s, p) if name == 'jr_island_buy' else _sell(s, p)


def _buy(s: dict, p: dict) -> dict:
    need = _core().need
    it = ISLAND.get(p['id']) if isinstance(p['id'], str) else None
    need(it is not None and not it.get('gone'), 'Chọn một hòn đảo nhé.')
    b = get(s)
    if b and it['id'] in b['own']:   # a second tap: nothing to pay
        return dict(message=f'Bạn đã có {it["name"]} rồi.', duplicate=True)
    need(len(b['own']) < OWN_MAX if b else True, 'Bạn có nhiều đảo quá rồi.', 'limit')
    need(p.get('confirm') is True, f'Xác nhận mua {it["name"]} {_fmt(it["price"])} xu.')
    why = _lx().ready_why(s, it['price'])
    need(not why, why, 'not_enough')
    how = _take(s, it['price'], f'Mua đảo · {it["name"]}')
    b = _ensure(s)
    b['own'][it['id']] = dict(d=s['journey']['life_day'], p=it['price'])
    b['stats']['bought'] += 1
    b['stats']['xu'] = min(BIG, b['stats']['xu'] + it['price'])
    return dict(message=f'{it["emoji"]} {it["name"]} là của bạn: trả {how}. Phí giữ đảo {_fmt(month_of(it["id"], it["price"]))} xu/tháng. '
                        'Ra đảo một mình hoặc rủ bạn bè đi du thuyền, phi cơ nhé!')


def _sell(s: dict, p: dict) -> dict:
    need = _core().need
    b = get(s)
    it = ISLAND.get(p['id']) if isinstance(p['id'], str) else None
    need(it is not None and b is not None and it['id'] in b['own'], 'Bạn chưa có hòn đảo này.', 'not_owned')
    back = sell_price(b['own'][it['id']]['p'])
    from . import island_build as ib
    built = ib.sell_back(s, it['id'])   # 🏗️ its buildings are razed with it: their salvage comes back too
    j = s['journey']
    need(j['wallet'] + back + built <= PRICE_MAX, 'Ví đã quá đầy. Gửi bớt vào ngân hàng rồi bán nhé.', 'limit')
    need(p.get('confirm') is True, f'Xác nhận bán {it["name"]} lấy {_fmt(back + built)} xu.')
    b = _ensure(s)
    b['own'].pop(it['id'])
    b['stats']['sold'] += 1
    if back:
        _wallet_rows(j, back, KIND, f'Bán lại · {it["name"]}')
    built = ib.on_sell(s, it['id'])
    extra = f' Công trình trên đảo được phá dỡ, thu hồi vật liệu {_fmt(built)} xu.' if built else ''
    return dict(message=f'Đã bán {it["name"]}, nhận {_fmt(back)} xu vào ví.{extra} Chuyến ra đảo đang mở (nếu có) cũng kết thúc.')


# ---------------------------------------------------------------- views
def public(s: dict) -> dict | None:
    """Small (it rides on every state): None until the first purchase."""
    b = get(s)
    if not b:
        return None
    j = s['journey']
    return dict(own={i: dict(p=x['p'], d=x['d'], sell=sell_price(x['p']), m=month_of(i, x['p'])) for i, x in b['own'].items() if i in ISLAND},
                month=monthly(s), next=(j['life_day'] // bk.MONTH_DAYS + 1) * bk.MONTH_DAYS,
                due=(b['upk']['acc'] // 1000) if b['upk'] else 0, paid=b['upk']['paid'] if b['upk'] else 0,
                rides=vehicles(s))   # what can take friends out (the 🏝️ dialog's "Ra đảo" list)


def worth(j: dict) -> int:
    """What the 💰 board counts for this block: every island at its buy-back price (game/wealth.py)."""
    b = j.get(KEY) if isinstance(j, dict) else None
    own = b.get('own') if isinstance(b, dict) else None
    if not isinstance(own, dict):
        return 0
    return sum(sell_price(x['p']) for i, x in own.items() if i in ISLAND and isinstance(x, dict) and _int(x.get('p'), 1, PRICE_MAX))


def catalogue() -> dict:
    """Static lists for the client (bootstrap content, cached)."""
    from . import garage
    from . import island_build as ib
    seats = {vid: dict(seats=n, arrive=k) for vid, (n, k) in C.SEATS.items()}
    for vid, v in garage.VEHICLES.items():
        if vid not in seats and v['group'] in C.GROUP_SEATS:
            n, k = C.GROUP_SEATS[v['group']]
            seats[vid] = dict(seats=n, arrive=k)
    return dict(islands=[dict(i, month=month_of(i['id'], i['price']), sell=sell_price(i['price'])) for i in C.ISLANDS if not i.get('gone')],
                seats=seats, arrive=dict(C.ARRIVE), sell_pct=C.SELL_PCT, minutes=C.SESSION_MIN, invite_max=C.INVITE_MAX,
                month_days=bk.MONTH_DAYS, unlimited=True, public_cap=C.PUBLIC_CAP,   # 19/10: a trip has no time limit (`minutes`: for older clients)
                build=ib.catalogue(), **({'build_off': True} if ib.off() else {}))   # 🏗️ Xây trên đảo (game/island_build.py; MNL_ISLAND_BUILD_OFF hides its tab)
