"""🧾 Hóa đơn tháng của tài sản: phí giữ xe & bảo dưỡng, phí bảo trì nhà (story mode).

Owner 03/10: "tính toán xem có cách nào bào thêm xu của người dùng nhé" (the xu sinks, docs/ECONOMY_SINKS.md). What a
player owns costs a little to keep, like in real life, in proportion to what it is worth: the rich pay most, a new
player who owns nothing (or a bicycle, or a small flat) pays nothing.

* 🚗 Each vehicle in the garage (game/garage.py): CAR_BP[its group] basis points of the price paid, a tháng
  (MONTH_DAYS life days): xe máy 0,5 %, ô tô 0,75 %, du thuyền 1 %, máy bay 1,25 % (about 6 / 9 / 12 / 15 % a year of
  the in-game calendar: insurance, parking or the marina, servicing). Bicycles (price under CAR_FREE_BELOW) are free.
* 🏠 Each home you own (game/housing.py: the one you live in, the empty ones and the ones let), by its list price:
  from 6 000 xu 0,2 %, from 20 000 xu 0,3 %, from 30 000 xu 0,35 % of the price paid a tháng (HOME_BANDS: maintenance,
  thuế đất, the garden and the pool of a villa). The small flats (under 6 000 xu) pay nothing more than their điện nước.
  A let home still earns more rent (0,42 % a tháng of the list price) than it costs, so letting stays worth it.
* Accrual: every life-day morning adds one day's share of everything owned that morning (in thousandths of a xu), so a
  vehicle or a home bought or sold in the middle of a tháng pays only its days. On the life days that are a multiple of
  MONTH_DAYS the whole xu of each part are billed: one Sổ ví row per part (kind 'upkeep', 💡) and one line of the day.
* Never a debt: the bill comes out of the cash in the wallet (never below 0), then the bank account; what both do not
  cover is waived (said in the line), never owed. The bank's card, loans and the home loans are not touched.
* Nothing is charged for the days before this block existed: it starts on the first life day it sees (`since`). The
  first time it starts while the player already owns something billable, one line says what it will cost a tháng.

The savings tier (game/invest.py SAVE_TIER) reads `since`: a Mây savings term that began before it keeps the old
flat rate until that term ends.

State journey['upk'] (optional: absent until the first morning under this build; journey.validate allows extra keys,
so an older build keeps it untouched and simply does not bill):
    v      VERSION
    since  the life day this block started (nothing before it is billed)
    day    the last life day accrued
    acc    {car, home}: thousandths of a xu accrued and not billed yet
    paid   {car, home}: xu paid in all
Deterministic, idempotent (the day counter): replays and retries never bill twice.
"""
from __future__ import annotations

from . import bank as bk

VERSION = 1
KEY = 'upk'
KIND = 'upkeep'                   # journey wallet history kind (journey.HISTORY_KINDS: 💡 in Sổ ví)
MONTH_DAYS = bk.MONTH_DAYS        # 5 life days
PARTS = ('car', 'home')
CAR_BP = {'bike': 50, 'car': 75, 'boat': 100, 'plane': 125}   # basis points of the price paid, a tháng
CAR_FREE_BELOW = 500              # bicycles: no fee
HOME_BANDS = ((30000, 35), (20000, 30), (6000, 20))           # list price from -> basis points a tháng; cheaper: none
LABELS = dict(car='Phí giữ xe & bảo dưỡng', home='Phí bảo trì nhà')
UNITS = dict(car='xe', home='căn')
CATCH_UP = 400                    # life days caught up at most (like the bank and the home)
ACC_MAX = 10**12
KEYS = frozenset({'v', 'since', 'day', 'acc', 'paid'})


def _jr():
    from . import journey
    return journey


def _fmt(n: int) -> str:
    return bk._fmt(n)


# ---------------------------------------------------------------- rates
def car_bp(vid: str, price: int) -> int:
    """Basis points a tháng for a vehicle (0: free). An id this build does not know pays nothing."""
    from .garage import VEHICLES
    V = VEHICLES.get(vid)
    if not V or V['price'] < CAR_FREE_BELOW or price < CAR_FREE_BELOW:
        return 0
    return CAR_BP.get(V['group'], 0)


def home_bp(kind: str) -> int:
    """Basis points a tháng for a home you own, by its list price (0: a small flat, a room)."""
    from .housing import HOMES
    H = HOMES.get(kind)
    if not H or H['kind'] != 'own':
        return 0
    return next((bp for low, bp in HOME_BANDS if H['price'] >= low), 0)


def daily_milli(price: int, bp: int) -> int:
    """One life day's share, in thousandths of a xu: price × bp / 10 000 a tháng, over MONTH_DAYS days."""
    return max(0, int(price)) * bp // (10 * MONTH_DAYS)


def month_xu(price: int, bp: int) -> int:
    """About what a tháng costs, in xu (shown; the bill is the exact sum of the days)."""
    return (daily_milli(price, bp) * MONTH_DAYS + 500) // 1000


def car_month(vid: str, price: int) -> int:
    return month_xu(price, car_bp(vid, price))


def home_month(kind: str, price: int) -> int:
    return month_xu(price, home_bp(kind))


def assets(s: dict) -> list[dict]:
    """What is billed this morning: [{part, id, price, bp, milli}] (vehicles first, then homes; free ones left out)."""
    j = s['journey']
    out = []
    g = j.get('garage')
    if isinstance(g, dict) and isinstance(g.get('cars'), dict):
        for vid, car in g['cars'].items():
            if isinstance(car, dict) and type(car.get('p')) is int:
                bp = car_bp(vid, car['p'])
                if bp:
                    out.append(dict(part='car', id=vid, price=car['p'], bp=bp, milli=daily_milli(car['p'], bp)))
    h = j.get('home')
    if isinstance(h, dict):
        from .housing import homes
        for x in homes(h):
            bp = home_bp(x.get('kind'))
            if bp and type(x.get('price')) is int:
                out.append(dict(part='home', id=x['id'], price=x['price'], bp=bp, milli=daily_milli(x['price'], bp)))
    return out


def monthly(s: dict) -> dict:
    """{car, home}: about what a tháng of what is owned now costs, in xu."""
    out = {p: 0 for p in PARTS}
    for a in assets(s):
        out[a['part']] += a['milli']
    return {p: (m * MONTH_DAYS + 500) // 1000 for p, m in out.items()}


def next_bill(day: int) -> int:
    """The next bill day after life day `day` (or `day` itself when it is one and its morning is still ahead)."""
    return (int(day) // MONTH_DAYS + 1) * MONTH_DAYS


# ---------------------------------------------------------------- the block
def initial(day: int) -> dict:
    return dict(v=VERSION, since=int(day), day=int(day), acc={p: 0 for p in PARTS}, paid={p: 0 for p in PARTS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    u = j.get(KEY) if isinstance(j, dict) else None
    return u if isinstance(u, dict) else None


def since(s: dict) -> int | None:
    """The life day this save's bills (and the savings tier) began, None before the first morning under this build."""
    u = get(s)
    return u['since'] if u else None


def _take(s: dict, amount: int, label: str, day: int) -> int:
    """Up to `amount` from the cash in the wallet (never below 0), then the bank account. Returns what was taken."""
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _jr()._wallet(j, -cash, KIND, label)
    b = bk.get(s)
    rest = min(amount - cash, b['balance']) if b else 0
    if rest > 0:
        b['balance'] -= rest
        bk._log(b, day, 'acc', label, -rest)
    return cash + max(0, rest)


def _bill(s: dict, u: dict, day: int, notes: list) -> None:
    owned = assets(s)
    parts, waived = [], 0
    for part in PARTS:
        amount = u['acc'][part] // 1000
        u['acc'][part] %= 1000
        if amount <= 0:
            continue
        n = sum(1 for a in owned if a['part'] == part)
        label = LABELS[part] + (f' · {n} {UNITS[part]}' if n else '')
        got = _take(s, amount, label, day)
        u['paid'][part] = min(ACC_MAX, u['paid'][part] + got)
        waived += amount - got
        parts.append(f'{LABELS[part].lower()} {_fmt(amount)} xu')
    if parts:
        line = '🧾 Hóa đơn tháng: ' + ', '.join(parts) + '.'
        if waived:
            line += f' Ví và tài khoản chưa đủ: {_fmt(waived)} xu còn thiếu được miễn, không tính nợ.'
        notes.append(line)


def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Catch the bills up to `journey.life_day` (idempotent; after the home's and the bank's morning)."""
    j = s.get('journey')
    if not isinstance(j, dict) or not j.get('story'):
        return []
    notes: list[str] = []
    target = int(j['life_day'])
    u = get(s)
    if u is None:
        u = j[KEY] = initial(target)
        m = monthly(s)
        if m['car'] or m['home']:
            what = ' và '.join(x for x in (('phí giữ xe, bảo dưỡng' if m['car'] else ''), ('phí bảo trì nhà' if m['home'] else '')) if x)
            notes.append(f'🧾 Ban quản lý gửi thông báo: {what} của bạn khoảng {_fmt(m["car"] + m["home"])} xu mỗi tháng '
                         f'({MONTH_DAYS} ngày sống), trừ vào cuối tháng. Xem ở Nhà xe và Nhà của bạn.')
    u['day'] = max(u['day'], target - CATCH_UP)
    while u['day'] < target:
        u['day'] += 1
        n = u['day']
        for a in assets(s):   # the morning of day n: one day of everything owned now
            u['acc'][a['part']] = min(ACC_MAX, u['acc'][a['part']] + a['milli'])
        if n % MONTH_DAYS == 0:
            _bill(s, u, n, notes)
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


def public(s: dict) -> dict:
    """{car, home} (xu a tháng of what is owned now), next (the next bill day), due {car, home} (accrued, not billed)."""
    j = s['journey']
    u = get(s)
    m = monthly(s)
    acc = u['acc'] if u else {p: 0 for p in PARTS}
    return dict(m, next=next_bill(j['life_day']), due={p: acc[p] // 1000 for p in PARTS}, month_days=MONTH_DAYS)


def validate(s: dict) -> None:
    """journey['upk'] when present (strict). Raises GameError like validate_state."""
    from . import engine as e
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    u = j[KEY]
    bad = 'Hóa đơn tháng trong bản lưu không hợp lệ.'
    e.need(isinstance(u, dict) and set(u) == KEYS and u['v'] == VERSION, bad, 'invalid_save')
    for k in ('since', 'day'):
        e.need(type(u[k]) is int and 1 <= u[k] <= 10**6, bad, 'invalid_save')
    e.need(u['since'] <= u['day'] <= max(u['since'], int(j.get('life_day', 1))), bad, 'invalid_save')
    for k in ('acc', 'paid'):
        e.need(isinstance(u[k], dict) and set(u[k]) == set(PARTS)
               and all(type(v) is int and 0 <= v <= ACC_MAX for v in u[k].values()), bad, 'invalid_save')
