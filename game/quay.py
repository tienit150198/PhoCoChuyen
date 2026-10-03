"""🏪 Quầy của bạn: your own counter in the street, run by staff you hire (story mode).

Owner 03/10: "tự mở quầy, thuê nhân viên hoặc người chơi khác về làm, trả lương… tự set lương… khách nhiều ít tùy
ngày, đa số lời… lâu lâu trộm vào hoặc mất két", then "đơn giản, thoải mái, người chơi thấy vui". So:

* Unlock: chapter UNLOCK_CHAPTER and UNLOCK_SERVED jobs done in one of the TRADES (you sell what you know).
  At most MAX_STALLS counters. A counter is a PLACE (a cart, a market stall, a street kiosk) and a TRADE.
* Opening: the place's price plus a starting fund (vốn quầy, START_DAYS days of running costs), from the cash in
  the wallet first, then the bank account (never a loan). Wallet rows use existing kinds only: 'invest' (open,
  capital, upgrades), 'draw' (Thu két, selling, money back), 'upkeep' (rent the counter could not cover).
* Staff: NPC staff from the trade's own people (game/operations.py PEOPLE: names, bios, speed, precision), three
  candidates a tháng. You set each wage yourself (WAGE_MIN_PCT..WAGE_MAX_PCT % of what they ask; below it they
  say no). Morale follows the wage; a happy or very careful person sells a little more (like the shop staff's
  per-job bonus in game/operations.py: morale >= 80 or precision >= 90).
* Every life day the player ends (journey.after -> on_life_day, idempotent by the counter's own day), each counter
  runs that day: customers = base x trade x pace x weather x x3 x upgrades x reputation x noise, capped by the
  stock you ordered (Ít / Vừa / Nhiều) and by your staff's hands. The takings go into the till (két); goods, wages
  and power come out of the takings first, then the fund. Most days are profitable (tests/test_quay.py: >= 75 %).
  A life day only passes when the player plays, so an offline player's counter never runs (nor loses).
* Thu két (one tap): the till into the wallet (or the fund). LEFT_DAYS life days without it, the counter closes and
  waits for its owner (no sales, no wages).
* Risks, rare and capped: a night thief takes part of the till (THEFT_PCT a night, once per THEFT_GAP days at most,
  never more than THEFT_CAP x the average day's takings, never the fund, the wallet or the bank); without a safe,
  sometimes the whole cash box goes (mất két). "Báo công an" may bring part of it back after POLICE_DAYS days.
* Rent every MONTH_DAYS (a tháng) from the till, the fund, then the wallet and the bank. What none covers pauses the
  counter until it is paid ("Đóng tiền thuê"): never a debt.
* Sang nhượng: SELL_PCT % of the place's price and UPGRADE_BACK % of the upgrades, plus the till and the fund.

Hired players (game/quay_hire.py): a counter can also take another player for one shift; their real hands-on day
in the trade earns the counter `shift_value` x their performance, paid into the till through the live_effects
inbox (kind 'quay', applied once by its fixed id), and their wage is the owner's escrowed xu (a transfer).

State journey['quay'] (optional; journey.validate allows extra keys, an older build keeps it untouched and its
counters simply do not run there):
    v        VERSION
    seq      the last counter id number
    stalls   [≤ MAX_STALLS counter]
    shift    None | the hired shift this player accepted at someone's counter (game/quay_hire.py)
    out      [≤ OUT_MAX finished shifts waiting to be settled with the server] (game/quay_hire.py)
A counter: {id, trade, place, name, opened, day, fund, till, order, due, left, rep, items, staff, case, theft,
            hist, log}. Validation is strict on the keys it knows and lets a newer build add keys.
"""
from __future__ import annotations

import random
import re

from . import archive as ar
from . import bank as bk

VERSION = 1
KEY = 'quay'
MAX_STALLS = 2
UNLOCK_CHAPTER = 3
UNLOCK_SERVED = 10
MONTH_DAYS = bk.MONTH_DAYS        # rent every 5 life days, new candidates every tháng
START_DAYS = 3                    # the starting fund: this many days of running costs (one person, market wage)
LEFT_DAYS = 5                     # life days without Thu két: the counter closes and waits for its owner
CATCH_UP = 3                      # life days a counter catches up at most (a day played on an older build)
WAGE_MIN_PCT, WAGE_MAX_PCT = 60, 300
NAME_MAX = 24
SELL_PCT, UPGRADE_BACK = 50, 30
THEFT_MIN = 20                    # a till under this tempts nobody
THEFT_GAP = 10                    # life days between two thefts at one counter, at least
THEFT_SAFE_DAYS = 5               # a new counter: no theft in its first days
THEFT_CAP = 3                     # a theft takes at most this many average days of takings
POLICE_DAYS = 3
HIST_MAX, LOG_MAX = 7, 20
OUT_MAX = 6
MONEY_MAX = 10**8
KIND_IN, KIND_OUT, KIND_RENT = 'invest', 'draw', 'upkeep'   # journey.HISTORY_KINDS (an older build validates them)

PLACES = {
    'xe': dict(id='xe', emoji='🛺', name='Xe đẩy đầu hẻm', price=800, rent=30, slots=1, wage=15, base=9, power=2, cap=14, theft=30),
    'sap': dict(id='sap', emoji='🏪', name='Sạp chợ Phố', price=4000, rent=100, slots=2, wage=18, base=26, power=6, cap=17, theft=25),
    'kiot': dict(id='kiot', emoji='🏬', name='Ki-ốt mặt phố', price=15000, rent=350, slots=3, wage=22, base=70, power=15, cap=30, theft=20),
}
PLACE_IDS = tuple(PLACES)
# price a customer, customers x mult (%), cost of goods %, unsold goods that spoil %, weather and festival (%).
TRADES = {
    'tra_da': dict(emoji='🧊', name='Trà đá', price=4, mult=160, cogs=30, spoil=0, nang=125, mua=65, fest=100),
    'fruit': dict(emoji='🍉', name='Trái cây', price=9, mult=105, cogs=52, spoil=20, nang=110, mua=80, fest=100),
    'ice_cream': dict(emoji='🍦', name='Kem', price=6, mult=130, cogs=42, spoil=10, nang=135, mua=60, fest=100),
    'cafe_bakery': dict(emoji='🥐', name='Bánh & cà phê', price=8, mult=100, cogs=45, spoil=25, nang=100, mua=110, fest=100),
    'milk_tea': dict(emoji='🧋', name='Trà sữa', price=9, mult=82, cogs=40, spoil=10, nang=115, mua=85, fest=100),
    'florist': dict(emoji='💐', name='Hoa', price=18, mult=54, cogs=50, spoil=25, nang=100, mua=85, fest=150),
    'grocery': dict(emoji='🛒', name='Tạp hóa', price=12, mult=118, cogs=68, spoil=2, nang=100, mua=100, fest=100),
    'clothing': dict(emoji='👕', name='Quần áo', price=30, mult=35, cogs=55, spoil=0, nang=100, mua=75, fest=135),
}
TRADE_IDS = tuple(TRADES)
ITEMS = {
    'bang': dict(id='bang', emoji='🪧', name='Bảng hiệu đèn', price=dict(xe=150, sap=600, kiot=2000), line='+8% khách'),
    'tu': dict(id='tu', emoji='🧊', name='Tủ mát', price=dict(xe=200, sap=700, kiot=2500), line='Ít hư hàng, +4% khách'),
    'ket': dict(id='ket', emoji='🔐', name='Két sắt', price=dict(xe=250, sap=700, kiot=1500), line='Ít trộm, không mất cả két'),
}
ITEM_IDS = tuple(ITEMS)
ORDERS = {'it': 75, 'vua': 100, 'nhieu': 130}          # stock, % of the day's forecast
ORDER_NAMES = {'it': 'Ít', 'vua': 'Vừa', 'nhieu': 'Nhiều'}
WEATHER = (('nang', '☀️', 'nắng', 50), ('mua', '🌧️', 'mưa', 30), ('am', '☁️', 'âm u', 20))
PACE = (('calm', 'phố vắng', 75, 25), ('normal', 'phố vừa', 100, 55), ('festival', 'phố đông', 135, 20))

STALL_KEYS = frozenset({'id', 'trade', 'place', 'name', 'opened', 'day', 'fund', 'till', 'order', 'due', 'left', 'rep', 'items',
                        'staff', 'case', 'theft', 'hist', 'log'})
STAFF_KEYS = frozenset({'id', 'name', 'wage', 'ask', 'mo', 'd', 'g'})
CASE_KEYS = frozenset({'day', 'lost', 'all', 'rep', 'due'})
HIST_KEYS = frozenset({'d', 'n', 'rev', 'net', 'w', 'p'})
LOG_KEYS = frozenset({'d', 't', 'a'})
SHIFT_KEYS = frozenset({'id', 'career', 'day', 'base', 'wage', 'value', 'who', 'name', 'until'})
OUT_KEYS = frozenset({'id', 'tasks', 'stars', 'late'})
ID_RE = re.compile(r'q[0-9]{1,6}')
JOB_RE = re.compile(r'qj-[0-9a-f]{8,24}')


def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _qs():
    from . import quay_self
    return quay_self


SELF_ACTIONS = frozenset({'jr_quay_menu', 'jr_quay_look', 'jr_quay_online', 'jr_quay_start', 'jr_quay_serve', 'jr_quay_ship', 'jr_quay_choose',
                          'jr_quay_close'})   # 🧑‍🍳 game/quay_self.py


def _fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def _rng(s: dict, st: dict, day: int, tag: str) -> random.Random:
    return random.Random(f"quay|{s['journey'].get('seed', 0)}|{st['id']}|{day}|{tag}")


# ---------------------------------------------------------------- the block
def get(s: dict) -> dict | None:
    j = s.get('journey')
    q = j.get(KEY) if isinstance(j, dict) else None
    return q if isinstance(q, dict) else None


def ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = dict(v=VERSION, seq=0, stalls=[], shift=None, out=[])
    return j[KEY]


def stall(s: dict, sid) -> dict:
    q = get(s)
    st = next((x for x in (q or {}).get('stalls', ()) if x['id'] == sid), None)
    _core().need(st, 'Không thấy quầy này.', 'no_stall')
    return st


def served(s: dict, trade: str) -> int:
    c = s['careers'].get(trade) or {}
    return int((c.get('metrics') or {}).get('served', 0))


def known_trades(s: dict) -> list[str]:
    return [t for t in TRADE_IDS if served(s, t) >= UNLOCK_SERVED]


def why_locked(s: dict) -> str | None:
    """Why this save cannot open a counter yet (None: it can)."""
    j = s['journey']
    if not j.get('story'):
        return 'Quầy riêng chỉ có trong hành trình.'
    if int(j.get('chapter', 1)) < UNLOCK_CHAPTER:
        return f'Mở từ chương {UNLOCK_CHAPTER}.'
    if not known_trades(s):
        return f'Làm {UNLOCK_SERVED} việc ở một nghề bán hàng trước nhé.'
    return None


def visible(s: dict) -> bool:
    """The public view carries the block only for saves that have one or reached its chapter (state size)."""
    j = s.get('journey') or {}
    return get(s) is not None or (bool(j.get('story')) and int(j.get('chapter', 1)) >= UNLOCK_CHAPTER)


# ---------------------------------------------------------------- numbers
def market_wage(place: str) -> int:
    return PLACES[place]['wage']


def day_cost(place: str) -> int:
    P = PLACES[place]
    return P['wage'] + P['power']


def start_fund(place: str) -> int:
    return START_DAYS * day_cost(place)


def open_cost(place: str) -> int:
    return PLACES[place]['price'] + start_fund(place)


def shift_value(place: str, trade: str) -> int:
    """What one pair of hands at this counter earns it in a full day (after goods): a hired player's shift is worth
    this x their performance (game/quay_hire.py)."""
    P, T = PLACES[place], TRADES[trade]
    return max(1, P['cap'] * T['mult'] * T['price'] * (100 - T['cogs']) // 10000)


def _weather(s: dict, st: dict, day: int) -> tuple:
    r = _rng(s, st, day, 'w').random() * 100
    edge = 0
    for w in WEATHER:
        edge += w[3]
        if r < edge:
            return w
    return WEATHER[0]


def _pace(s: dict, st: dict, day: int) -> tuple:
    r = _rng(s, st, day, 'p').random() * 100
    edge = 0
    for p in PACE:
        edge += p[3]
        if r < edge:
            return p
    return PACE[1]


def _x3(trade: str) -> bool:
    try:
        from . import x3_week
        return bool(x3_week.on(trade))
    except Exception:  # noqa: BLE001 - the counter never fails on the weekly list
        return False


def forecast(s: dict, st: dict, day: int) -> dict:
    """The day's expected customers before luck: {w, pace, n, x3}."""
    P, T = PLACES[st['place']], TRADES[st['trade']]
    w, pace = _weather(s, st, day), _pace(s, st, day)
    f = P['base'] * T['mult'] / 100 * pace[2] / 100 * T[w[0]] / 100 if w[0] in T else P['base'] * T['mult'] / 100 * pace[2] / 100
    if pace[0] == 'festival':
        f *= T['fest'] / 100
    x3 = _x3(st['trade'])
    if x3:
        f *= 1.3
    f *= 1 + (8 if 'bang' in st['items'] else 0) / 100 + (4 if 'tu' in st['items'] else 0) / 100
    f *= st['rep'] / 100
    f *= _qs().demand_pct(st) / 100   # 🍽️ the board's prices and dishes, tables, online (100 for a 1.5.1 counter)
    return dict(w=w[0], pace=pace[0], n=max(1, round(f)), x3=x3)


def _hands(st: dict) -> float:
    """Customers the staff can serve in a day."""
    P, T = PLACES[st['place']], TRADES[st['trade']]
    total = 0.0
    for e in st['staff']:
        k = 0.85 + 0.25 * e['mo'] / 100
        if e['mo'] >= 80 or e['g']:
            k *= 1.05
        total += P['cap'] * T['mult'] / 100 * k
    return total


def _target_mood(e: dict) -> int:
    return max(10, min(100, round(60 + 40 * (e['wage'] / max(1, e['ask']) - 1))))


# ---------------------------------------------------------------- candidates
def candidates(s: dict, st: dict) -> list[dict]:
    """Three people this tháng (seeded by counter and tháng), from the trade's own staff (game/operations.py)."""
    from .operations import PEOPLE
    month = (int(s['journey']['life_day']) - 1) // MONTH_DAYS
    people = list(enumerate(PEOPLE.get(st['trade']) or ()))
    rng = random.Random(f"quay-c|{s['journey'].get('seed', 0)}|{st['id']}|{month}")
    rng.shuffle(people)
    hired = {e['id'] for e in st['staff']}
    out = []
    for i, (name, _role, bio, speed, precision) in people:
        cid = f'{st["trade"]}-{i + 1}'
        if cid in hired:
            continue
        pct = max(85, min(125, 100 + (speed + precision - 160) // 2))
        out.append(dict(id=cid, name=name, bio=bio, ask=max(8, market_wage(st['place']) * pct // 100), g=precision >= 90))
        if len(out) == 3:
            break
    return out


# ---------------------------------------------------------------- money helpers
def _have(s: dict) -> int:
    j = s['journey']
    b = bk.get(s)
    return max(0, j['wallet']) + (b['balance'] if b else 0)


def _take(s: dict, amount: int, label: str, career: str | None, kind: str = KIND_IN) -> int:
    """Up to `amount` from the cash in the wallet (never below 0), then the bank account. Returns what was taken."""
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _jr()._wallet(j, -cash, kind, label, career)
    b = bk.get(s)
    rest = min(amount - cash, b['balance']) if b else 0
    if rest > 0:
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label, -rest)
    return cash + max(0, rest)


def _log(st: dict, day: int, text: str, amount: int = 0) -> None:
    st['log'] = ar.last(st['log'] + [dict(d=int(day), t=text[:120], a=int(amount))], LOG_MAX, 'quay.log', ar.JOURNEY)


def _from_till_fund(st: dict, amount: int) -> int:
    """Up to `amount` from the till, then the fund. Returns what was paid."""
    a = min(st['till'], amount)
    st['till'] -= a
    b = min(st['fund'], amount - a)
    st['fund'] -= b
    return a + b


# ---------------------------------------------------------------- a day at the counter
def run_day(s: dict, st: dict, day: int) -> str | None:
    """One life day of a counter. Returns its line for the morning (None: nothing to say)."""
    P, T = PLACES[st['place']], TRADES[st['trade']]
    run = st.get('run')
    if isinstance(run, dict) and not run.get('x'):
        if run.get('d') == day:   # 🧑‍🍳 the owner stood at the counter and the life day ended before "Đóng ca"
            return _qs().close(s, st, day)
        if run.get('d', 0) < day:
            st['run'] = None      # a run whose day was played elsewhere (an older build ran it)
    st['left'] += 1
    label = f'{P["emoji"]} {st["name"]}'
    line = None
    if st['due'] > 0:
        line = f'{label} đang đóng: chờ đóng {_fmt(st["due"])} xu tiền thuê.'
    elif st['left'] > LEFT_DAYS:
        line = f'{label} đóng cửa chờ chủ: ghé Thu két để mở lại.' if st['left'] == LEFT_DAYS + 1 else None
    elif not st['staff']:
        line = f'{label} chưa có người đứng quầy.' if day % 2 == 0 else None
    elif st['fund'] + st['till'] < sum(e['wage'] for e in st['staff']) + P['power']:
        line = f'{label} hết vốn hôm nay: góp thêm vốn quầy nhé.'
    else:
        line = _sell(s, st, day)
    _rent(s, st, day)
    _police(s, st, day)
    return line


def _sell(s: dict, st: dict, day: int) -> str:
    P, T = PLACES[st['place']], TRADES[st['trade']]
    fc = forecast(s, st, day)
    rng = _rng(s, st, day, 'd')
    demand = fc['n'] * rng.uniform(0.8, 1.2)
    stock = max(1, round(fc['n'] * ORDERS[st['order']] / 100))
    sold = int(min(demand, stock, _hands(st)))
    qs = _qs()
    unit = T['price'] * qs.goods_pct(st) / 100 * T['cogs'] / 100   # 🍽️ the board's dishes (the trade's price at its default)
    spoil = T['spoil'] * (0.5 if 'tu' in st['items'] else 1) / 100
    spoiled = (stock - sold) * spoil
    revenue = round(sold * T['price'] * qs.board_pct(st) / 100)   # the board's prices (exactly sold x price at its default)
    goods = round((sold + spoiled) * unit)
    wages = sum(e['wage'] for e in st['staff'])
    cost = goods + wages + P['power'] + (round(revenue * qs.PASSIVE_FEE / 100) if st.get('online') else 0)
    st['till'] = min(MONEY_MAX, st['till'] + revenue)
    _from_till_fund(st, cost)   # a shortfall past both is waived (the run checked the fixed costs were there)
    net = revenue - cost
    for e in st['staff']:
        t = _target_mood(e)
        e['mo'] = min(t, e['mo'] + 10) if e['mo'] < t else max(t, e['mo'] - 10)
        e['d'] = min(10**6, e['d'] + 1)
    st['rep'] = max(90, min(110, st['rep'] + (-2 if demand > stock + 0.5 else 1) + {'cheap': 1, 'dear': -1, 'fair': 0}[qs.react(st)]))
    st['hist'] = ar.last(st['hist'] + [dict(d=day, n=sold, rev=revenue, net=net, w=fc['w'], p=fc['pace'])], HIST_MAX, 'quay.hist', ar.JOURNEY)
    _theft(s, st, day)
    sign = '+' if net >= 0 else '−'
    return f'{P["emoji"]} {st["name"]} hôm qua: {sold} khách, lời {sign}{_fmt(abs(net))} xu. Két đang giữ {_fmt(st["till"])} xu.'


def avg_revenue(st: dict) -> int:
    h = st['hist']
    return sum(x['rev'] for x in h) // len(h) if h else 0


def _theft(s: dict, st: dict, day: int) -> None:
    """A night thief, rare and capped: only the till, never the fund, the wallet or the bank."""
    if st['till'] < THEFT_MIN or day - st['opened'] < THEFT_SAFE_DAYS or (st['theft'] and day - st['theft'] < THEFT_GAP):
        return
    P = PLACES[st['place']]
    rng = _rng(s, st, day, 't')
    chance = P['theft'] * (0.4 if 'ket' in st['items'] else 1)   # per thousand nights
    if rng.random() * 1000 >= chance:
        return
    whole = 'ket' not in st['items'] and rng.random() < 0.3
    lost = st['till'] if whole else round(st['till'] * rng.uniform(0.4, 0.8))
    lost = max(1, min(lost, THEFT_CAP * max(avg_revenue(st), THEFT_MIN)))
    st['till'] -= lost
    st['theft'] = day
    st['case'] = dict(day=day, lost=lost, all=whole, rep=False, due=0)
    _log(st, day, 'Mất cả két đêm qua' if whole else 'Trộm lấy tiền trong két', -lost)


def _police(s: dict, st: dict, day: int) -> None:
    case = st['case']
    if not case:
        return
    if not case['rep']:
        if day - case['day'] > 5:   # never reported: the case closes quietly
            st['case'] = None
        return
    if day < case['due']:
        return
    rng = _rng(s, st, case['day'], 'police')
    chance = 25 + (10 if case['due'] == case['day'] + 1 + POLICE_DAYS else 0)
    back = round(case['lost'] * rng.uniform(0.5, 1.0)) if rng.random() * 100 < chance else 0
    if back:
        st['till'] = min(MONEY_MAX, st['till'] + back)
        _log(st, day, 'Công an tìm lại tiền', back)
    else:
        _log(st, day, 'Công an chưa tìm được kẻ trộm', 0)
    st['case'] = None


def _rent(s: dict, st: dict, day: int) -> None:
    n = day - st['opened'] + 1   # the counter's days so far, its opening day included
    if n <= 0 or n % MONTH_DAYS:
        return
    rent = PLACES[st['place']]['rent']
    paid = _from_till_fund(st, rent)
    if paid < rent:
        paid += _take(s, rent - paid, f'Tiền thuê {st["name"]}', st['trade'], KIND_RENT)
    if paid < rent:
        st['due'] += rent - paid
    _log(st, day, 'Tiền thuê tháng', -paid)


def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Run every counter up to the life day that just ended (idempotent: each counter keeps its own day)."""
    q = get(s)
    j = s.get('journey') or {}
    if not q or not j.get('story'):
        return []
    last = int(j['life_day']) - 1
    notes = []
    for st in q['stalls']:
        st['day'] = max(st['day'], last - CATCH_UP)
        while st['day'] < last:
            st['day'] += 1
            line = run_day(s, st, st['day'])
            if line:
                notes.append(line)
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- commands
def _name(raw) -> str:
    e = _core()
    text = e.clean_text(raw, NAME_MAX)
    from .social import BANNED
    for word in BANNED:
        text = re.sub(r'(?<!\w)' + re.escape(word) + r'(?!\w)', '•••', text, flags=re.I)
    return text


def _money(p: dict, key: str = 'amount', low: int = 1) -> int:
    return _core().integer(p.get(key), low, MONEY_MAX)


def action(s: dict, name: str, p: dict) -> dict:
    """`jr_quay_*` commands (through journey.action: journey.after and validate_state run)."""
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Quầy riêng chỉ có trong hành trình.', 'not_story')
    need(isinstance(p, dict), 'Dữ liệu không hợp lệ.')
    day = int(j['life_day'])
    if name == 'jr_quay_open':
        need(set(p) <= {'trade', 'place', 'name', 'confirm'}, 'Thông tin mở quầy không hợp lệ.')
        why = why_locked(s)
        need(not why, why or '', 'locked')
        q = ensure(s)
        need(len(q['stalls']) < MAX_STALLS, f'Tối đa {MAX_STALLS} quầy thôi nhé.', 'max_stalls')
        trade, place = p.get('trade'), p.get('place')
        need(trade in TRADES, 'Chọn một món để bán.')
        need(served(s, trade) >= UNLOCK_SERVED, f'Làm {UNLOCK_SERVED} việc ở nghề này trước nhé.', 'locked')
        need(place in PLACES, 'Chọn một chỗ đặt quầy.')
        need(p.get('confirm') is True, 'Xác nhận mở quầy.')
        nm = _name(p.get('name') or f'{TRADES[trade]["name"]} {str(s.get("name") or "")}'.strip()[:NAME_MAX])
        need(j['wallet'] >= 0, 'Ví đang nợ. Trả nợ trước rồi mở quầy nhé.', 'in_debt')
        total = open_cost(place)
        need(_have(s) >= total, f'Cần {_fmt(total)} xu (gồm {_fmt(start_fund(place))} xu vốn quầy).', 'no_money')
        q['seq'] += 1
        st = dict(id=f'q{q["seq"]}', trade=trade, place=place, name=nm, opened=day, day=day - 1, fund=start_fund(place), till=0,
                  order='vua', due=0, left=0, rep=100, items=[], staff=[], case=None, theft=0, hist=[], log=[])
        _take(s, total, f'Mở quầy {nm}', trade)
        _log(st, day, 'Mở quầy', -total)
        q['stalls'].append(st)
        return dict(message=f'🏪 {nm} đã mở! Thuê người đứng quầy nhé.')
    q = get(s)
    need(q is not None, 'Bạn chưa có quầy nào.', 'no_stall')
    st = stall(s, p.get('stall'))
    P, T = PLACES[st['place']], TRADES[st['trade']]
    if name in SELF_ACTIONS:
        return _qs().action(s, name, p, st)
    if name == 'jr_quay_till':
        need(set(p) <= {'stall', 'to'} and p.get('to', 'wallet') in ('wallet', 'fund'), 'Thao tác két không hợp lệ.')
        amount = st['till']
        was = st['left'] > LEFT_DAYS
        st['left'] = 0
        if amount <= 0:
            return dict(message='Két trống. Quầy vẫn mở bình thường.' if not was else 'Quầy mở lại rồi!')
        st['till'] = 0
        if p.get('to') == 'fund':
            st['fund'] = min(MONEY_MAX, st['fund'] + amount)
            _log(st, day, 'Két vào vốn quầy', 0)
            return dict(message=f'Đã cất {_fmt(amount)} xu vào vốn quầy.')
        _jr()._wallet(j, amount, KIND_OUT, f'Thu két {st["name"]}', st['trade'])
        _log(st, day, 'Thu két về ví', amount)
        return dict(message=f'💰 Thu két: +{_fmt(amount)} xu vào ví.')
    if name == 'jr_quay_fund':
        need(set(p) <= {'stall', 'amount'}, 'Thao tác vốn không hợp lệ.')
        amount = e.integer(p.get('amount'), -MONEY_MAX, MONEY_MAX)
        need(amount != 0, 'Số xu không hợp lệ.')
        if amount > 0:
            need(j['wallet'] >= amount, 'Ví không đủ số này.', 'no_money')
            _jr()._wallet(j, -amount, KIND_IN, f'Góp vốn quầy {st["name"]}', st['trade'])
            st['fund'] = min(MONEY_MAX, st['fund'] + amount)
            return dict(message=f'Đã góp {_fmt(amount)} xu vào vốn quầy.')
        need(st['fund'] >= -amount, f'Vốn quầy chỉ còn {_fmt(st["fund"])} xu.', 'no_money')
        st['fund'] += amount
        _jr()._wallet(j, -amount, KIND_OUT, f'Rút vốn quầy {st["name"]}', st['trade'])
        return dict(message=f'Đã rút {_fmt(-amount)} xu vốn về ví.')
    if name == 'jr_quay_order':
        need(set(p) <= {'stall', 'level'} and p.get('level') in ORDERS, 'Mức nhập hàng không hợp lệ.')
        st['order'] = p['level']
        return dict(message=f'Nhập hàng: {ORDER_NAMES[st["order"]]}.')
    if name == 'jr_quay_hire':
        need(set(p) <= {'stall', 'cand', 'wage'}, 'Thông tin tuyển không hợp lệ.')
        need(len(st['staff']) < P['slots'], f'Quầy này chỉ đủ chỗ cho {P["slots"]} người.', 'full')
        cand = next((c for c in candidates(s, st) if c['id'] == p.get('cand')), None)
        need(cand, 'Người này không còn tìm việc.')
        wage = e.integer(p.get('wage'), 1, 10**4)
        need(wage * 100 >= cand['ask'] * WAGE_MIN_PCT, f'{cand["name"]} chê ít quá, không nhận.', 'too_low')
        need(wage * 100 <= cand['ask'] * WAGE_MAX_PCT, f'Lương tối đa {_fmt(cand["ask"] * WAGE_MAX_PCT // 100)} xu.', 'too_high')
        member = dict(id=cand['id'], name=cand['name'], wage=wage, ask=cand['ask'], mo=60, d=0, g=cand['g'])
        member['mo'] = _target_mood(member)
        st['staff'].append(member)
        _log(st, day, f'Thuê {cand["name"]}', 0)
        return dict(message=f'{cand["name"]} nhận việc, lương {wage} xu/ngày.')
    if name in ('jr_quay_wage', 'jr_quay_fire'):
        need(set(p) <= {'stall', 'staff', 'wage', 'confirm'}, 'Thao tác nhân viên không hợp lệ.')
        member = next((x for x in st['staff'] if x['id'] == p.get('staff')), None)
        need(member, 'Không có người này ở quầy.')
        if name == 'jr_quay_fire':
            need(p.get('confirm') is True, 'Xác nhận cho nghỉ.')
            st['staff'] = [x for x in st['staff'] if x is not member]
            _log(st, day, f'{member["name"]} nghỉ', 0)
            return dict(message=f'{member["name"]} đã nghỉ. Cảm ơn bạn ấy nhé.')
        wage = e.integer(p.get('wage'), 1, 10**4)
        need(wage * 100 >= member['ask'] * WAGE_MIN_PCT, f'Thấp vậy {member["name"]} buồn lắm, không chịu đâu.', 'too_low')
        need(wage * 100 <= member['ask'] * WAGE_MAX_PCT, f'Lương tối đa {_fmt(member["ask"] * WAGE_MAX_PCT // 100)} xu.', 'too_high')
        up = wage > member['wage']
        member['wage'] = wage
        return dict(message=f'{member["name"]}: lương {wage} xu/ngày.' + (' Bạn ấy vui lắm!' if up else ''))
    if name == 'jr_quay_buy':
        need(set(p) <= {'stall', 'item', 'confirm'} and p.get('item') in ITEMS, 'Món này không có.')
        it = ITEMS[p['item']]
        need(it['id'] not in st['items'], f'Quầy đã có {it["name"].lower()} rồi.')
        need(p.get('confirm') is True, 'Xác nhận mua.')
        price = it['price'][st['place']]
        need(j['wallet'] >= 0 and _have(s) >= price, f'Cần {_fmt(price)} xu.', 'no_money')
        _take(s, price, f'{it["name"]} cho {st["name"]}', st['trade'])
        st['items'].append(it['id'])
        _log(st, day, f'Lắp {it["name"].lower()}', -price)
        return dict(message=f'{it["emoji"]} Đã lắp {it["name"].lower()}.')
    if name == 'jr_quay_police':
        need(set(p) <= {'stall'}, 'Thao tác không hợp lệ.')
        case = st['case']
        need(case and not case['rep'], 'Không có vụ nào cần báo.')
        case['rep'] = True
        case['due'] = day + POLICE_DAYS   # reported the morning after (day == case day + 1): a better chance
        return dict(message=f'🚓 Đã báo công an. Có tin sau khoảng {POLICE_DAYS} ngày.')
    if name == 'jr_quay_pay':
        need(set(p) <= {'stall'}, 'Thao tác không hợp lệ.')
        need(st['due'] > 0, 'Quầy không nợ tiền thuê.')
        due = st['due']
        paid = _from_till_fund(st, due)
        need(paid == due or _have(s) >= due - paid, f'Cần {_fmt(due)} xu tiền thuê.', 'no_money')
        if paid < due:
            _take(s, due - paid, f'Tiền thuê {st["name"]}', st['trade'], KIND_RENT)
        st['due'] = 0
        _log(st, day, 'Đóng tiền thuê', -due)
        return dict(message=f'Đã đóng {_fmt(due)} xu. Quầy mở lại!')
    if name == 'jr_quay_sell':
        need(set(p) <= {'stall', 'confirm'} and p.get('confirm') is True, 'Xác nhận sang nhượng.')
        back = sell_back(st)
        q['stalls'] = [x for x in q['stalls'] if x is not st]
        _jr()._wallet(j, back, KIND_OUT, f'Sang nhượng {st["name"]}', st['trade'])
        return dict(message=f'Đã sang nhượng {st["name"]}: +{_fmt(back)} xu vào ví.')
    raise e.GameError('Thao tác quầy không hợp lệ.', 'unknown_action')


def sell_back(st: dict) -> int:
    P = PLACES[st['place']]
    ups = sum(ITEMS[i]['price'][st['place']] for i in st['items'] if i in ITEMS)
    return max(0, P['price'] * SELL_PCT // 100 + ups * UPGRADE_BACK // 100 + st['till'] + st['fund'] - st['due'])


# ---------------------------------------------------------------- hired players (applied by game/quay_hire.py)
def credit(s: dict, sid: str, what: str, amount: int, label: str) -> str:
    """Money for one counter from outside a command (a hired player's shift into the till, an escrowed wage back into
    the fund). A counter that was sold meanwhile: into the wallet. Returns the line to show."""
    j = s['journey']
    q = get(s)
    st = next((x for x in (q or {}).get('stalls', ()) if x['id'] == sid), None)
    if st is None:
        _jr()._wallet(j, amount, KIND_OUT, label[:120])
        return f'{label}: +{_fmt(amount)} xu vào ví.'
    if what == 'shift':
        st['till'] = min(MONEY_MAX, st['till'] + amount)
        _log(st, j['life_day'], label, amount)
        return f'{label}: +{_fmt(amount)} xu vào két.'
    st['fund'] = min(MONEY_MAX, st['fund'] + amount)
    _log(st, j['life_day'], label, amount)
    return f'{label}: +{_fmt(amount)} xu về vốn quầy.'


def on_shift(s: dict, career: str | None, action: str, result: dict) -> None:
    """journey.after, every action: the hired shift this save holds (game/quay_hire.py) ends with the day of its career
    that it was taken for. Closing that day moves it to `out` (the tasks done since accepting it) for the server to
    settle; a day closed elsewhere (an older build) moves it as late (pays nobody, the escrow goes back)."""
    q = get(s)
    if not q or not q.get('shift'):
        return
    sh = q['shift']
    c = s['careers'].get(sh['career'])
    summary = result.get('summary') if isinstance(result.get('summary'), dict) else {}
    if action == 'end_day' and career == sh['career'] and summary.get('day') == sh['day']:
        done = max(0, int(summary.get('completed') or 0) - sh['base'])
        avg = (summary.get('reviews') or {}).get('average')
        stars = max(0, min(50, int(round(float(avg) * 10)))) if isinstance(avg, (int, float)) else 0
        late = False
    elif not isinstance(c, dict) or int(c.get('day', 0)) > sh['day']:
        done, stars, late = 0, 0, True
    else:
        return
    if len(q['out']) >= OUT_MAX:
        return
    q['out'].append(dict(id=sh['id'], tasks=done, stars=stars, late=late))
    q['shift'] = None
    result['quay'] = 'shift'
    if not late:
        from .quay_hire import MIN_TASKS
        line = (f'💼 Xong ca làm thêm ở {sh["name"]}: {done} việc. Lương {sh["wage"]} xu về ví ngay.' if done >= MIN_TASKS
                else f'💼 Ca ở {sh["name"]} chưa đủ {MIN_TASKS} việc nên chưa tính lương.')
        result.setdefault('effects', []).append(line)


# ---------------------------------------------------------------- views
def catalogue() -> dict:
    """Static numbers for the client (bootstrap content)."""
    return dict(places=[dict(id=k, emoji=v['emoji'], name=v['name'], price=v['price'], rent=v['rent'], slots=v['slots'], wage=v['wage'],
                             fund=start_fund(k), base=v['base']) for k, v in PLACES.items()],
                trades={k: dict(emoji=v['emoji'], name=v['name']) for k, v in TRADES.items()},
                items=[dict(id=k, emoji=v['emoji'], name=v['name'], price=v['price'], line=v['line']) for k, v in ITEMS.items()],
                orders=[dict(id=k, name=ORDER_NAMES[k]) for k in ORDERS], weather={w[0]: w[1] + ' ' + w[2] for w in WEATHER},
                pace={p[0]: p[1] for p in PACE}, chapter=UNLOCK_CHAPTER, served=UNLOCK_SERVED, max=MAX_STALLS, left=LEFT_DAYS,
                month=MONTH_DAYS, wage_pct=[WAGE_MIN_PCT, WAGE_MAX_PCT], **_qs().catalogue())


def _stall_view(s: dict, st: dict) -> dict:
    P = PLACES[st['place']]
    day = int(s['journey']['life_day'])
    fc = forecast(s, st, day)
    out = dict({k: st[k] for k in ('id', 'trade', 'place', 'name', 'fund', 'till', 'order', 'due', 'rep', 'items')},
               closed=st['due'] > 0 or st['left'] > LEFT_DAYS, left=max(0, LEFT_DAYS - st['left']),
               staff=[{k: x[k] for k in ('id', 'name', 'wage', 'ask', 'mo', 'g')} for x in st['staff']],
               case=dict(lost=st['case']['lost'], all=st['case']['all'], rep=st['case']['rep']) if st['case'] else None,
               hist=[[x['d'], x['n'], x['net']] for x in st['hist']], today=fc, sell=sell_back(st),
               value=shift_value(st['place'], st['trade']), **_qs().stall_view(s, st))
    if len(st['staff']) < P['slots']:
        out['cands'] = [{k: c[k] for k in ('id', 'name', 'bio', 'ask', 'g')} for c in candidates(s, st)]
    return out


def public(s: dict) -> dict:
    q = get(s) or {}
    out = dict(stalls=[_stall_view(s, st) for st in q.get('stalls', ())], lock=why_locked(s), can=known_trades(s))
    if q.get('shift'):
        out['shift'] = {k: q['shift'][k] for k in ('id', 'career', 'wage', 'who', 'name', 'until')}
    if q.get('out'):
        out['out'] = len(q['out'])
    return out


# ---------------------------------------------------------------- validation
def _int(v, low: int, high: int) -> bool:
    return type(v) is int and low <= v <= high


def _text(v, n: int) -> bool:
    return isinstance(v, str) and len(v) <= n


def validate(s: dict) -> None:
    """journey['quay'] when present: strict on the keys this build knows (a newer build may add keys)."""
    from . import engine as e
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    q = j[KEY]
    bad = 'Dữ liệu quầy trong bản lưu không hợp lệ.'
    need = lambda ok: e.need(ok, bad, 'invalid_save')  # noqa: E731
    need(isinstance(q, dict) and {'v', 'seq', 'stalls', 'shift', 'out'} <= set(q) and q['v'] == VERSION)
    need(_int(q['seq'], 0, 10**6) and isinstance(q['stalls'], list) and len(q['stalls']) <= MAX_STALLS)
    ids = set()
    for st in q['stalls']:
        need(isinstance(st, dict) and STALL_KEYS <= set(st))
        need(isinstance(st['id'], str) and ID_RE.fullmatch(st['id']) is not None and st['id'] not in ids)
        ids.add(st['id'])
        need(st['trade'] in TRADES and st['place'] in PLACES and st['order'] in ORDERS)
        need(_text(st['name'], NAME_MAX) and 1 <= len(st['name']) and st['name'] == st['name'].strip())
        for k in ('opened', 'day'):
            need(_int(st[k], 0, 10**6))
        for k in ('fund', 'till', 'due'):
            need(_int(st[k], 0, MONEY_MAX))
        need(_int(st['left'], 0, 10**6) and _int(st['rep'], 90, 110) and _int(st['theft'], 0, 10**6))
        need(isinstance(st['items'], list) and len(set(st['items'])) == len(st['items']) and set(st['items']) <= set(ITEMS))
        need(isinstance(st['staff'], list) and len(st['staff']) <= PLACES[st['place']]['slots'])
        for x in st['staff']:
            need(isinstance(x, dict) and STAFF_KEYS <= set(x) and isinstance(x['id'], str) and len(x['id']) <= 40
                 and _text(x['name'], 40) and _int(x['wage'], 1, 10**4) and _int(x['ask'], 1, 10**4) and _int(x['mo'], 0, 100)
                 and _int(x['d'], 0, 10**6) and type(x['g']) is bool)
        c = st['case']
        need(c is None or (isinstance(c, dict) and CASE_KEYS <= set(c) and _int(c['day'], 0, 10**6) and _int(c['lost'], 1, MONEY_MAX)
                           and type(c['all']) is bool and type(c['rep']) is bool and _int(c['due'], 0, 10**6)))
        need(isinstance(st['hist'], list) and len(st['hist']) <= HIST_MAX)
        for h in st['hist']:
            need(isinstance(h, dict) and HIST_KEYS <= set(h) and _int(h['d'], 0, 10**6) and _int(h['n'], 0, 10**6)
                 and _int(h['rev'], 0, MONEY_MAX) and _int(h['net'], -MONEY_MAX, MONEY_MAX) and _text(h['w'], 12) and _text(h['p'], 12))
        need(isinstance(st['log'], list) and len(st['log']) <= LOG_MAX)
        for x in st['log']:
            need(isinstance(x, dict) and LOG_KEYS <= set(x) and _int(x['d'], 0, 10**6) and _text(x['t'], 120)
                 and _int(x['a'], -MONEY_MAX, MONEY_MAX))
        _qs().validate(st, need, _int, _text)   # 🧑‍🍳 the board, the look, online, the day at the counter (optional keys)
    sh = q['shift']
    need(sh is None or (isinstance(sh, dict) and SHIFT_KEYS <= set(sh) and isinstance(sh['id'], str) and JOB_RE.fullmatch(sh['id']) is not None
                        and sh['career'] in TRADES and _int(sh['day'], 0, 10**6) and _int(sh['base'], 0, 10**4) and _int(sh['wage'], 1, 10**4)
                        and _int(sh['value'], 1, 10**4) and _text(sh['who'], 40) and _text(sh['name'], 40) and _int(sh['until'], 0, 10**11)))
    need(isinstance(q['out'], list) and len(q['out']) <= OUT_MAX)
    for o in q['out']:
        need(isinstance(o, dict) and OUT_KEYS <= set(o) and isinstance(o['id'], str) and JOB_RE.fullmatch(o['id']) is not None
             and _int(o['tasks'], 0, 10**4) and _int(o['stars'], 0, 50) and type(o['late']) is bool)
