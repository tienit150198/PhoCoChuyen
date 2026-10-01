"""🏠 Nhà của bạn: a better rented room, buying a home and a mortgage at Ngân hàng Phố (story mode).

In-game calendar, shared with the bank's savings (game/bank.py): 1 tháng = MONTH_DAYS = 5 ngày sống,
1 năm = 12 tháng = YEAR_DAYS = 60 ngày sống. Prices are in xu; rates are quoted per year.

Where you live decides the "tiền phòng" part of the daily living cost (journey.living_cost):
* Bà Tám's attic (no `home`, or nothing rented or owned): the chapter's rent, as before;
* a rented room (`rent`): its own daily rent and a refundable deposit (tiền cọc), +1 tinh thần a day;
* your own home (`own`): no rent, only điện nước (upkeep), +comfort tinh thần a day;
* your spouse's home (`shared`, delivered through the marriage inbox by game/couple.py): the same,
  while the two of you stay married.

Buying: a down payment of at least DOWN_PCT % of the price plus a BUY_FEE_PCT % fee (công chứng, sang
tên), paid from the joint fund (married couples, optional), then the bank account, then cash. The rest
is a mortgage (vay mua nhà): it needs a bank account, a credit score from HOME_SCORE, steady income and
an installment within DTI_PCT % of a month's income; the yearly rate depends on the score. Installments
are taken every MONTH_DAYS life days from the account (then cash), like the bank's other loans.

Missed payments are gentle: a message the day before when the money is short, then GRACE life days of
grace with a retry every morning (no fee, no score change); only after that a small late fee, a
credit-score drop and one "lần trễ hạn" on the bank record (three of those is nợ xấu, as for other loans).
The comfort bonus pauses while a payment is late. The bank never takes the home: selling it (market value
minus a SELL_FEE_PCT % fee, the mortgage paid off first) is always the player's own choice.

Homes (HOMES, grouped as Phòng thuê / Căn hộ / Nhà phố / Biệt thự by GROUPS): the dearer ones (penthouse,
biệt thự) need a higher credit score for the mortgage (`score`); the installment limit is the same DTI rule.
0.9.13 raised every list price by 20 %. A home bought earlier keeps the price paid, its loan and schedule
(validate accepts OLD_PRICES); its market value still grows from the price paid, so nobody gets a windfall.
Rents did not change (the room's rent is part of the daily living cost, not a house price).

State `s['journey']['home']` (absent = never rented or bought: older saves load unchanged), see initial().
Commands arrive as `jr_home_*` through journey.action. Deterministic: nothing here is random.
"""
from __future__ import annotations

import copy

from . import archive as ar
from . import bank as bk
from . import bank_content as BK
from . import days as dy

VERSION = 1
KIND = 'home'                     # journey wallet history kind (journey.HISTORY_KINDS)
MONTH_DAYS = bk.MONTH_DAYS        # 5 life days
YEAR_DAYS = bk.YEAR_DAYS          # 60 life days

DOWN_PCT = 30                     # trả trước tối thiểu
BUY_FEE_PCT, SELL_FEE_PCT, FEE_MIN = 2, 3, 10
GROW_RATE, GROW_CAP_PCT = 300, 30  # market value: +3 %/năm on the price, at most +30 %
HOME_SCORE = 600
RATES = ((740, 900), (670, 1020), (0, 1140))   # score -> basis points per year (9 / 10,2 / 11,4 %); /12 per month
LOAN_MONTHS = (12, 24, 36)
LOAN_MIN = 100
DTI_PCT = bk.DTI_PCT              # the installment stays within 40 % of a month's income
GRACE = 3                         # life days of grace before a late fee
LATE_PCT, LATE_MIN = 2, 2
PAYOFF_FEE_PCT, PAYOFF_FEE_MIN = 1, 5
LOG_MAX, PAST_MAX = 30, 6
STATS = ('bought', 'sold', 'paid_off', 'ontime', 'late', 'comfort', 'home_days', 'rent_days')
COMMANDS = ('jr_home_rent', 'jr_home_leave', 'jr_home_buy', 'jr_home_pay', 'jr_home_payoff', 'jr_home_sell')

ATTIC = dict(emoji='🏚️', name='Căn gác nhà Bà Tám', where='Trên gác nhà Bà Tám, đầu hẻm',
             desc='Phòng nhỏ trên gác, cửa sổ nhìn ra hẻm. Tiền phòng và cơm nước Bà Tám tính theo ngày.')

# How "Nhà của bạn" groups the listings (id, emoji, name, colour of the home's tile in the UI).
GROUPS = (('rent', '🛏️', 'Phòng thuê', '#e0a93b'), ('apartment', '🏢', 'Căn hộ', '#4f9fd1'),
          ('townhouse', '🏠', 'Nhà phố', '#d9734e'), ('villa', '🏰', 'Biệt thự', '#3f9a78'))
GROUP_IDS = tuple(g[0] for g in GROUPS)

# Homes, cheapest first within each group. `price` is the list price in xu (0.9.13: +20 % on the 0.9.5 prices),
# `upkeep` the daily điện nước (apartments add phí quản lý, so they cost more to run than a house of the
# same comfort), `comfort` the tinh thần added each morning. Optional: `perk` (one line the listing shows),
# `score` (the credit score the bank needs to lend on this home, HOME_SCORE when absent).
# Ids are stored in saves: never rename or remove one.
HOMES = {
    'tro_moi': dict(kind='rent', group='rent', emoji='🛏️', name='Phòng trọ khép kín', where='Hẻm 12, cạnh chợ',
                    desc='Phòng 18 m² có gác lửng, cửa sổ, nhà vệ sinh riêng. Cô Hạnh chủ nhà cho nuôi mèo.',
                    rent=14, deposit=60, comfort=1),
    'tap_the': dict(kind='own', group='apartment', emoji='🏢', name='Căn tập thể cũ', where='Khu tập thể đầu phố, tầng 4',
                    desc='35 m², hai phòng nhỏ. Cầu thang hơi dốc nhưng hàng xóm vui tính, chiều nào cũng có người pha trà.',
                    price=1800, upkeep=2, comfort=1),
    'can_ho_studio': dict(kind='own', group='apartment', emoji='🛋️', name='Studio Nắng Mai', where='Tòa Nắng Mai, tầng 9',
                          desc='Căn studio 28 m², bếp mở, cửa kính lớn đón nắng sớm. Nhỏ mà xinh, phí quản lý hơi cao.',
                          price=2400, upkeep=4, comfort=2),
    'can_ho_mini': dict(kind='own', group='apartment', emoji='🏙️', name='Căn hộ mini', where='Đường Hoa Sữa',
                        desc='30 m², có thang máy, ban công nhỏ phơi đồ, bảo vệ giữ xe dưới sảnh.',
                        price=3600, upkeep=3, comfort=2),
    'can_ho_1pn': dict(kind='own', group='apartment', emoji='☁️', name='Căn hộ Mây Xanh', where='Tòa Mây Xanh, tầng 12 · 1 phòng ngủ',
                       desc='Một phòng ngủ riêng, phòng khách nhìn ra hồ, sảnh có quầy trà sữa. Chiều gió lồng lộng.',
                       price=5400, upkeep=5, comfort=3),
    'can_ho_2pn': dict(kind='own', group='apartment', emoji='🪁', name='Căn hộ Cánh Diều', where='Tòa Cánh Diều, tầng 15 · 2 phòng ngủ',
                       desc='Hai phòng ngủ, hai ban công, sân chơi trẻ con dưới sảnh. Đủ chỗ cho cả nhà.',
                       price=10200, upkeep=6, comfort=4),
    'penthouse': dict(kind='own', group='apartment', emoji='🌃', name='Penthouse Mây Xanh', where='Tầng thượng tòa Mây Xanh',
                      desc='Tầng cao nhất, sân thượng riêng trồng rau thơm. Tối ngồi ngắm cả phố lên đèn.',
                      perk='🌿 Sân thượng riêng', price=21600, upkeep=9, comfort=5, score=670),
    'nha_pho': dict(kind='own', group='townhouse', emoji='🏠', name='Nhà phố nhỏ', where='Hẻm xe hơi sau chợ',
                    desc='Một trệt một lầu, ngang 3 mét, phòng khách đủ kê bộ bàn ghế gỗ và một bàn thờ nhỏ.',
                    price=7800, upkeep=4, comfort=3),
    'nha_san': dict(kind='own', group='townhouse', emoji='🏡', name='Nhà có sân', where='Cuối hẻm, gần bờ kênh',
                    desc='Sân trước có cây khế và giàn bông giấy, cổng sắt sơn xanh, chỗ để hai chiếc xe.',
                    price=14400, upkeep=5, comfort=4),
    'biet_thu_vuon': dict(kind='own', group='villa', emoji='🌳', name='Biệt thự Vườn Cau', where='Đường ven kênh, cuối phố',
                          desc='Hai tầng giữa vườn cau và hàng chuối. Sáng nghe chim, chiều hái rau, cuối tuần cả xóm sang chơi.',
                          perk='🌳 Vườn rộng, có xích đu', price=36000, upkeep=12, comfort=6, score=700),
    'biet_thu_song': dict(kind='own', group='villa', emoji='🌅', name='Biệt thự Sông Hồng', where='Bờ sông, cuối con đê',
                          desc='Ba tầng nhìn ra sông, hồ bơi nhỏ sau nhà. Hoàng hôn đổ xuống mặt nước mỗi chiều.',
                          perk='🌊 Hồ bơi và bến ngắm sông', price=60000, upkeep=16, comfort=7, score=740),
}
OWN = tuple(k for k, v in HOMES.items() if v['kind'] == 'own')
RENT = tuple(k for k, v in HOMES.items() if v['kind'] == 'rent')

# List prices before 0.9.13. A home bought then keeps the price paid (own.price, the loan and its schedule),
# and its market value keeps growing from that price (value_of), so the +20 % is no windfall for owners.
OLD_PRICES = {'tap_the': (1500,), 'can_ho_mini': (3000,), 'nha_pho': (6500,), 'nha_san': (12000,)}


def prices(kind: str) -> tuple[int, ...]:
    """Every list price a save may hold for `kind`: today's, then older ones."""
    return (HOMES[kind]['price'],) + OLD_PRICES.get(kind, ())


def need_score(kind: str) -> int:
    """The credit score the bank needs to lend on this home."""
    return HOMES[kind].get('score', HOME_SCORE)


def lname(name: str) -> str:
    """A home's name inside a sentence: "Biệt thự Sông Hồng" -> "biệt thự Sông Hồng"."""
    return name[:1].lower() + name[1:]


# What the neighbours say when you move (whole sentences, no names of real people).
MOVE_LINES = {
    'rent': 'Bà Tám dúi cho bịch trái cây: “Ở đâu cũng nhớ về ăn cơm với bà nghe cháu.”',
    'own': 'Bà Tám lau nước mắt: “Có nhà rồi, mừng cho cháu quá. Bữa nào tân gia nhớ gọi bà!”',
    'back': 'Bà Tám mở cửa gác, phủi lại cái chiếu: “Phòng vẫn để đó, về lúc nào cũng được.”',
}


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _couple():
    try:
        from . import couple
        return couple
    except ImportError:   # a build without marriage
        return None


_fmt = bk._fmt


def _ceil10(x: int) -> int:
    return -(-int(x) // 10) * 10


def initial(day: int = 1) -> dict:
    return dict(v=VERSION, seq=0, day=int(day), rent=None, own=None, shared=None, past=[], log=[],
                stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    h = j.get('home') if isinstance(j, dict) else None
    return h if isinstance(h, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('home'), dict):
        j['home'] = initial(j['life_day'])
    return j['home']


def upgrade(j: dict) -> None:
    """Future fields join an existing `home` here (setdefault only). Absent stays absent."""
    h = j.get('home') if isinstance(j, dict) else None
    if not isinstance(h, dict):
        return
    for k, v in initial(int(j.get('life_day') or 1)).items():
        h.setdefault(k, copy.deepcopy(v))
    if isinstance(h.get('stats'), dict):
        for k in STATS:
            h['stats'].setdefault(k, 0)


def _log(h: dict, day: int, text: str, amt: int = 0) -> None:
    h['log'] = ar.last(h['log'] + [dict(day=int(day), text=text[:140], amt=int(amt))], LOG_MAX, 'home.log', ar.JOURNEY)


def _seq(h: dict) -> str:
    h['seq'] += 1
    return f'h{h["seq"]}'


def down_min(price: int) -> int:
    return _ceil10(price * DOWN_PCT / 100)


def buy_fee(price: int) -> int:
    return max(FEE_MIN, -(-price * BUY_FEE_PCT // 100))


def sell_fee(value: int) -> int:
    return max(FEE_MIN, -(-value * SELL_FEE_PCT // 100))


def value_of(own: dict, day: int) -> int:
    """Market value today: the price plus GROW_RATE per year held, capped, rounded down to 10 xu."""
    price = own['price']
    held = max(0, day - own['day'])
    grown = price + price * GROW_RATE * held // (10000 * YEAR_DAYS)
    return min(price * (100 + GROW_CAP_PCT) // 100, grown) // 10 * 10


def rate_for(score: int) -> int:
    return next(rate for low, rate in RATES if score >= low)


def attic_rent(j: dict) -> int:
    return _jr().LIVING.get(j['chapter'], _jr().LIVING[_jr().LAST]) * 6 // 10


def _spouse(s: dict) -> dict | None:
    m = s.get('marriage')
    sp = m.get('spouse') if isinstance(m, dict) else None
    return sp if isinstance(sp, dict) and sp.get('status') == 'married' else None


def _shared_ok(s: dict, sh: dict | None) -> bool:
    """The spouse's home counts while the two are still married to each other."""
    if not sh:
        return False
    sp = _spouse(s)
    if not sp:
        return False
    return type(sp.get('couple')) is not int or sp['couple'] == sh['couple']


def where(h: dict | None) -> tuple[str, str | None]:
    """('own'|'shared'|'rent'|'attic', home kind)."""
    if not h:
        return 'attic', None
    if h['own']:
        return 'own', h['own']['kind']
    if h['shared']:
        return 'shared', h['shared']['kind']
    if h['rent']:
        return 'rent', h['rent']['kind']
    return 'attic', None


def living(j: dict, total: int) -> dict:
    """journey.living_cost: the day's total split into rent (or điện nước at home) and meals."""
    rent = total * 6 // 10
    meals = total - rent
    place, kind = where(j.get('home') if isinstance(j.get('home'), dict) else None)
    if place in ('own', 'shared'):
        rent, label = HOMES[kind]['upkeep'], 'Cơm nước và điện nước nhà mình'
    elif place == 'rent':
        rent, label = HOMES[kind]['rent'], 'Tiền phòng trọ và cơm nước'
    else:
        label = 'Tiền phòng và cơm nước'
    return dict(total=rent + meals, rent=rent, meals=meals, label=label, where=place)


def _spirit(s: dict, n: int) -> int:
    L = s['journey'].get('life')
    if not isinstance(L, dict) or type(L.get('spirit')) is not int:
        return 0
    before = L['spirit']
    L['spirit'] = max(0, min(100, before + n))
    return L['spirit'] - before


# ---------------------------------------------------------------- mortgage maths (mirrored in public/js/v4/house.js)
def month_bp(rate: int) -> int:
    return rate // 12


def schedule(principal: int, rate: int, months: int, start: int) -> list[dict]:
    bp = month_bp(rate)
    pay = bk.installment(principal, bp, months)
    rows, rest = [], principal
    for k in range(1, months + 1):
        i = bk._interest(rest, bp)
        part = rest if k == months else max(0, min(rest, pay - i))
        rows.append(dict(k=k, due=start + MONTH_DAYS * k, principal=part, interest=i, amount=part + i, paid=0, fee=0, late=False))
        rest -= part
    return rows


def quote(principal: int, rate: int, months: int, start: int = 0) -> dict:
    rows = schedule(principal, rate, months, start)
    return dict(rows=rows, installment=rows[0]['amount'], interest=sum(r['interest'] for r in rows),
                total=sum(r['amount'] for r in rows))


def offer(s: dict, score: int = HOME_SCORE) -> dict:
    """The bank's answer before amounts: ok, why, text, the rate for this score, the monthly room.
    `score`: the credit score the home needs (need_score(kind)); the listing asks with HOME_SCORE."""
    b = bk.get(s)
    if b is None:
        return dict(ok=False, why='no_account', text='Mở tài khoản Ngân hàng Phố trước rồi mới vay mua nhà được.',
                    rate=RATES[-1][1], room=0, score=None)
    why, text = bk._screen(s, b, score)
    inc = bk.income(s)
    room = max(0, inc['avg'] * MONTH_DAYS * DTI_PCT // 100 - bk._weekly_due(b) * MONTH_DAYS // 7)
    return dict(ok=why is None, why=why, text=text, rate=rate_for(b['score']), room=room, score=b['score'])


def _payoff(ln: dict, day: int, fee: bool = True) -> dict:
    """Early settlement: overdue rows in full, the rest of the principal, interest for the days used, a small fee."""
    overdue = sum(r['amount'] - r['paid'] for r in ln['rows'] if r['due'] <= day and r['paid'] < r['amount'])
    future = [r for r in ln['rows'] if r['due'] > day and r['paid'] < r['amount']]
    principal = sum(r['principal'] for r in future)
    used = 0
    if future:
        start = future[0]['due'] - MONTH_DAYS
        used = -(-principal * month_bp(ln['rate']) * max(0, day - start) // (10000 * MONTH_DAYS))
    charge = max(PAYOFF_FEE_MIN, -(-principal * PAYOFF_FEE_PCT // 100)) if principal and fee else 0
    return dict(overdue=overdue, principal=principal, interest=used, fee=charge, total=overdue + principal + used + charge,
                saved=sum(r['interest'] for r in future) - used)


def _late(ln: dict | None) -> bool:
    return bool(ln) and any(r['late'] and r['paid'] < r['amount'] for r in ln['rows'])


# ---------------------------------------------------------------- the daily tick
def _close_loan(s: dict, h: dict, day: int, why: str) -> None:
    own = h['own']
    own['loan'] = None
    s['journey']['stats']['home_paid'] = s['journey']['stats'].get('home_paid', 0) + 1
    h['stats']['paid_off'] += 1
    b = bk.get(s)
    if b is not None and why:
        bk._score(b, day, why)


def _tick_loan(s: dict, h: dict, n: int, notes: list) -> None:
    b = bk.get(s)
    own = h['own']
    ln = own['loan']
    if b is None or ln is None:
        return
    name = HOMES[own['kind']]['name']
    total = len(ln['rows'])
    j = s['journey']
    for r in ln['rows']:
        if r['paid'] >= r['amount']:
            continue
        left = r['amount'] - r['paid']
        if r['due'] == n + 1 and b['balance'] + max(0, j['wallet']) < left:
            notes.append('🏠 ' + bk._inbox(b, n, 'sms', f'{BK.BANK_NAME}: Ngày mai (Ngày {r["due"]}) đến hạn trả góp nhà kỳ {r["k"]}/{total}, '
                                                        f'{_fmt(left)} xu. Tài khoản và ví hiện chưa đủ, quý khách nhớ nộp thêm nhé.'))
        if r['due'] > n:
            continue
        if bk._debit(s, b, left, f'Trả góp nhà kỳ {r["k"]}/{total} · {name}', n):
            r['paid'] = r['amount']
            bk._log(b, n, 'loan', f'Kỳ {r["k"]}/{total} · Vay mua nhà', -left)
            if not r['late']:
                bk._score(b, n, 'home_ok')
                h['stats']['ontime'] += 1
                bk._inbox(b, n, 'sms', BK.INSTALLMENT_SMS.format(bank=BK.BANK_NAME, amount=_fmt(left), k=r['k'], n=total, what='vay mua nhà'))
            else:
                notes.append(f'🏠 Đã trích {_fmt(left)} xu trả kỳ {r["k"]} khoản vay mua nhà đang trễ.')
            continue
        late_for = n - r['due']
        if late_for == 0:
            notes.append('🏠 ' + bk._inbox(b, n, 'sms', f'{BK.BANK_NAME}: Kỳ trả góp nhà {r["k"]}/{total} ({_fmt(left)} xu) chưa trích được vì '
                                                        f'tài khoản và ví chưa đủ. Quý khách có {GRACE} ngày ân hạn, ngân hàng thử lại mỗi sáng, chưa tính phí.'))
        elif late_for == GRACE and not r['late']:
            fee = max(LATE_MIN, -(-r['amount'] * LATE_PCT // 100))
            r.update(late=True, fee=r['fee'] + fee, amount=r['amount'] + fee)
            b['stats']['fees'] += fee
            b['stats']['late'] += 1
            b['misses'] += 1
            h['stats']['late'] += 1
            bk._score(b, n, 'home_late')
            bk._log(b, n, 'loan', f'Phạt trễ hạn kỳ {r["k"]} · Vay mua nhà', -fee)
            notes.append('⚠️ ' + bk._inbox(b, n, 'sms', BK.REMIND_SMS[1].format(bank=BK.BANK_NAME, what=f'trả góp nhà kỳ {r["k"]}',
                                                                              amount=_fmt(r['amount'] - r['paid']))))
        elif r['late'] and late_for > GRACE and (late_for - GRACE) % MONTH_DAYS == 0:
            notes.append('📞 ' + bk._call(s, b, n, 'vay mua nhà', r['amount'] - r['paid'], late_for))
    if all(r['paid'] >= r['amount'] for r in ln['rows']):
        _close_loan(s, h, n, 'home_done')
        _log(h, n, f'Trả xong khoản vay mua {lname(name)}.')
        notes.append(f'🎉 Bạn đã trả xong khoản vay mua nhà. {name} giờ hoàn toàn là của bạn!')


def _tick(s: dict, h: dict, n: int, notes: list) -> None:
    """Morning of life day `n`."""
    if h['own'] and h['own']['loan']:
        _tick_loan(s, h, n, notes)
    place, kind = where(h)
    if place == 'attic':
        return
    h['stats']['rent_days' if place == 'rent' else 'home_days'] += 1
    if not _late(h['own']['loan'] if h['own'] else None):
        h['stats']['comfort'] += _spirit(s, HOMES[kind]['comfort'])


def _check_shared(s: dict, h: dict, notes: list) -> None:
    sh = h['shared']
    if sh and not _shared_ok(s, sh):
        h['shared'] = None
        _log(h, s['journey']['life_day'], f'Dọn khỏi {lname(HOMES[sh["kind"]]["name"])} của {sh["name"]}.')
        if not h['own'] and not h['rent']:
            notes.append('🏚️ ' + MOVE_LINES['back'])


def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Catch the home up to `journey.life_day` (idempotent): installments, comfort, the spouse's home."""
    j = s.get('journey')
    h = get(s)
    if not h or not j.get('story'):
        return []
    notes: list[str] = []
    _check_shared(s, h, notes)
    target = int(j['life_day'])
    h['day'] = max(h['day'], target - 400)
    while h['day'] < target:
        h['day'] += 1
        _tick(s, h, h['day'], notes)
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- the spouse's home (game/couple.py, game/marriage.py)
def partner_effects(state: dict, couple_id: int, side: str, other_sid: str, effect) -> list:
    """Marriage inbox effects that bring the spouse into this save's home (and out of homes sold since).
    `effect` is marriage._effect; ids are fixed, so each is inserted and applied once."""
    h = get(state)
    if not h or not (state.get('journey') or {}).get('story'):
        return []
    out = []
    own = h['own']
    if own:
        name = str(state.get('name') or 'Người ấy')[:24]
        out.append(effect(f'home:{couple_id}:{side}:{own["id"]}', other_sid, 'home', 0,
                          f'{name} đón bạn về ở chung {lname(HOMES[own["kind"]]["name"])}',
                          dict(set='in', couple=couple_id, id=own['id'], kind=own['kind'], name=name)))
    for p in h['past']:
        out.append(effect(f'homeoff:{couple_id}:{side}:{p["id"]}', other_sid, 'home', 0, 'Căn nhà chung đã bán',
                          dict(set='out', couple=couple_id, id=p['id'])))
    return out


def apply_effect(s: dict, data: dict) -> None:
    """A 'home' effect from the marriage inbox, applied to the spouse's save (never raises)."""
    j = s.get('journey')
    if not isinstance(j, dict) or not j.get('story') or not isinstance(data, dict):
        return
    what, couple, hid = data.get('set'), data.get('couple'), data.get('id')
    if type(couple) is not int or not isinstance(hid, str) or not 1 <= len(hid) <= 16:
        return
    if what == 'in' and data.get('kind') in OWN:
        h = _ensure(s)
        name = str(data.get('name') or 'Người ấy')[:24] or 'Người ấy'
        h['shared'] = dict(couple=couple, id=hid, kind=data['kind'], name=name, since=int(j['life_day']))
        _log(h, j['life_day'], f'Về ở chung {lname(HOMES[data["kind"]]["name"])} của {name}.')
        if h['rent']:   # moving in with the spouse ends a rented room, the deposit comes back
            _leave_rent(s, h, j['life_day'])
    elif what == 'out':
        h = get(s)
        if h and h['shared'] and h['shared']['id'] == hid and h['shared']['couple'] == couple:
            sh = h['shared']
            h['shared'] = None
            _log(h, j['life_day'], f'{sh["name"]} đã bán {lname(HOMES[sh["kind"]]["name"])}.')


# ---------------------------------------------------------------- commands
def _have(s: dict) -> dict:
    j = s['journey']
    b = bk.get(s)
    return dict(wallet=max(0, j['wallet']), balance=b['balance'] if b else 0)


def _take(s: dict, amount: int, label: str, day: int) -> None:
    """Take `amount` from the bank account first, then cash. The caller checked it is there."""
    b = bk.get(s)
    from_acc = min(b['balance'], amount) if b else 0
    if from_acc:
        b['balance'] -= from_acc
        bk._log(b, day, 'acc', label, -from_acc)
    if amount > from_acc:
        _jr()._wallet(s['journey'], -(amount - from_acc), KIND, label)


def _receive(s: dict, amount: int, label: str, day: int) -> str:
    """Money back to the player: into the bank account when there is one, else the wallet."""
    b = bk.get(s)
    if b is not None:
        b['balance'] += amount
        bk._log(b, day, 'acc', label, amount)
        return 'tài khoản ngân hàng'
    _jr()._wallet(s['journey'], amount, KIND, label)
    return 'ví'


def _leave_rent(s: dict, h: dict, day: int) -> int:
    r = h['rent']
    h['rent'] = None
    _jr()._wallet(s['journey'], r['deposit'], KIND, f'Nhận lại tiền cọc {lname(HOMES[r["kind"]]["name"])}')
    _log(h, day, f'Trả phòng {lname(HOMES[r["kind"]]["name"])}, nhận lại {_fmt(r["deposit"])} xu tiền cọc.', r['deposit'])
    return r['deposit']


def _int(p: dict, key: str, low: int, high: int, msg: str) -> int:
    v = p.get(key)
    _core().need(type(v) is int and low <= v <= high, msg)
    return v


def apply(s: dict, name: str, p: dict) -> dict:
    """`jr_home_*` commands. Everything is checked before anything changes (a declined mortgage is a
    normal result: the bank's inquiry stays on the record, like bank.py's declines)."""
    e = _core()
    need = e.need
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác nhà ở không hợp lệ.', 'unknown_action')
    need(j['story'], 'Thuê và mua nhà chỉ có trong chế độ hành trình.', 'story_only')
    day = j['life_day']
    h = get(s)
    own = h['own'] if h else None
    rent = h['rent'] if h else None
    if name == 'jr_home_rent':
        kind = p.get('kind')
        need(kind in RENT, 'Chọn phòng muốn thuê nhé.')
        need(not own, 'Bạn đã có nhà riêng rồi.')
        need(not rent, 'Bạn đang thuê một phòng rồi.')
        need(p.get('confirm') is True, 'Xác nhận thuê phòng.')
        H = HOMES[kind]
        have = _have(s)
        need(have['wallet'] + have['balance'] >= H['deposit'],
             f'Tiền cọc {_fmt(H["deposit"])} xu: bạn còn thiếu {_fmt(H["deposit"] - have["wallet"] - have["balance"])} xu.', 'not_enough')
        h = _ensure(s)
        _take(s, H['deposit'], f'Đặt cọc {lname(H["name"])}', day)
        h['rent'] = dict(kind=kind, since=day, deposit=H['deposit'])
        _log(h, day, f'Thuê {lname(H["name"])}, đặt cọc {_fmt(H["deposit"])} xu.', -H['deposit'])
        return dict(message=f'Đã thuê {lname(H["name"])}: tiền phòng {_fmt(H["rent"])} xu/ngày, cọc {_fmt(H["deposit"])} xu '
                            f'(trả lại khi dọn đi). {MOVE_LINES["rent"]}')
    if name == 'jr_home_leave':
        need(rent, 'Bạn không thuê phòng nào.')
        need(p.get('confirm') is True, 'Xác nhận trả phòng.')
        back = _leave_rent(s, h, day)
        return dict(message=f'Đã trả phòng, nhận lại {_fmt(back)} xu tiền cọc vào ví. {MOVE_LINES["back"]}')
    if name == 'jr_home_buy':
        kind = p.get('kind')
        need(kind in OWN, 'Chọn căn nhà muốn mua nhé.')
        need(not own, 'Bạn đang có nhà rồi. Muốn đổi nhà thì bán căn hiện tại trước nhé.')
        H = HOMES[kind]
        price, fee = H['price'], buy_fee(H['price'])
        down = _int(p, 'down', down_min(price), price, f'Trả trước từ {_fmt(down_min(price))} xu ({DOWN_PCT}% giá nhà) tới {_fmt(price)} xu.')
        loan = price - down
        need(loan == 0 or loan >= LOAN_MIN, f'Vay ít nhất {_fmt(LOAN_MIN)} xu, hoặc trả đủ luôn nhé.')
        pay = down + fee
        joint = p.get('joint', 0)
        need(type(joint) is int and 0 <= joint <= pay, 'Số xu lấy từ quỹ chung không hợp lệ.')
        need(p.get('confirm') is True, 'Xác nhận ký hợp đồng mua nhà.')
        have = _have(s)
        short = pay - joint - have['balance'] - have['wallet']
        need(short <= 0, f'Trả trước và phí cần {_fmt(pay)} xu: bạn còn thiếu {_fmt(short)} xu.', 'not_enough')
        if joint:
            acc = bk.joint(s)
            need(acc is not None, 'Bạn chưa có quỹ chung vợ chồng.', 'no_joint')
            need(acc['balance'] >= joint, f'Quỹ chung chỉ còn {_fmt(acc["balance"])} xu.', 'not_enough')
        b = bk.get(s)
        months, q, rate = 0, None, 0
        if loan:
            months = p.get('months')
            need(months in LOAN_MONTHS, 'Chọn thời hạn vay nhé.')
            o = offer(s, need_score(kind))
            need(o['why'] != 'no_account', o['text'], 'no_account')
            rate = o['rate']
            q = quote(loan, rate, months, day)
            need(p.get('total_interest') == q['interest'], 'Điều khoản vay vừa thay đổi. Xem lại lịch trả góp rồi ký nhé.', 'stale_quote')
            if o['why'] != 'many':
                b['inq'] = (b['inq'] + [day])[-bk.INQ_MAX:]
                bk._score(b, day, 'inquiry')
            if not o['ok']:
                return dict(message=f'Hồ sơ vay mua nhà chưa được duyệt. {o["text"]}', approved=False)
            if q['installment'] > o['room']:
                return dict(message=f'Hồ sơ vay mua nhà chưa được duyệt: mỗi kỳ {_fmt(q["installment"])} xu vượt {DTI_PCT}% thu nhập một tháng '
                                    f'({_fmt(o["room"])} xu). Trả trước nhiều hơn hoặc vay dài hơn nhé.', approved=False)
        h = _ensure(s)
        if joint:   # its own database transaction, idempotent by ref (a retried command never pays twice)
            sp = _spouse(s) or {}
            _couple().joint_spend(s, joint, f'Mua {lname(H["name"])}', f'home{sp.get("side", "x")}{day}n{h["seq"] + 1}', kind='home')
        hid = _seq(h)
        _take(s, pay - joint, f'Trả trước mua {lname(H["name"])}', day)
        back = _leave_rent(s, h, day) if h['rent'] else 0
        ln = None
        if loan:
            ln = dict(principal=loan, rate=rate, months=months, start=day, rows=q['rows'])
            bk._log(b, day, 'loan', f'Giải ngân vay mua nhà: {_fmt(loan)} xu trả thẳng cho bên bán', 0)
            bk._inbox(b, day, 'sms', f'{BK.BANK_NAME}: Khoản vay mua nhà {_fmt(loan)} xu đã giải ngân cho bên bán. Trả góp {months} kỳ, mỗi kỳ '
                                     f'{_fmt(q["installment"])} xu, cứ {MONTH_DAYS} ngày một kỳ, kỳ đầu Ngày {q["rows"][0]["due"]}.')
        h['own'] = dict(id=hid, kind=kind, price=price, day=day, down=down, fee=fee, joint=joint, loan=ln)
        h['stats']['bought'] += 1
        j['stats']['homes_bought'] = j['stats'].get('homes_bought', 0) + 1
        _log(h, day, f'Mua {lname(H["name"])} giá {_fmt(price)} xu' + (f', vay {_fmt(loan)} xu' if loan else ', trả đủ một lần') + '.', -pay)
        msg = f'Chúc mừng! {H["name"]} ở {H["where"]} giờ là nhà của bạn. Đã trả {_fmt(pay)} xu (gồm {_fmt(fee)} xu phí công chứng, sang tên)'
        msg += f', trong đó {_fmt(joint)} xu từ quỹ chung.' if joint else '.'
        if loan:
            msg += f' Khoản vay {_fmt(loan)} xu trả {months} kỳ, mỗi kỳ khoảng {_fmt(q["installment"])} xu, kỳ đầu {dy.on_day(s, q["rows"][0]["due"])}.'
        if back:
            msg += f' Đã trả phòng trọ, nhận lại {_fmt(back)} xu tiền cọc.'
        return dict(message=f'{msg} {MOVE_LINES["own"]}', approved=True, home=kind)
    if name in ('jr_home_pay', 'jr_home_payoff'):
        need(own and own['loan'], 'Bạn không có khoản vay mua nhà nào.')
        ln = own['loan']
        b = bk.get(s)
        have = _have(s)
        if name == 'jr_home_pay':
            rows = [r for r in ln['rows'] if r['due'] <= day and r['paid'] < r['amount']]
            if not rows:
                rows = [next(r for r in ln['rows'] if r['paid'] < r['amount'])]
            amount = sum(r['amount'] - r['paid'] for r in rows)
            need(have['balance'] + have['wallet'] >= amount, f'Cần {_fmt(amount)} xu: tài khoản và ví còn thiếu '
                                                              f'{_fmt(amount - have["balance"] - have["wallet"])} xu.', 'not_enough')
            _take(s, amount, f'Trả góp nhà kỳ {", ".join(str(r["k"]) for r in rows)}', day)
            for r in rows:
                r['paid'] = r['amount']
            bk._log(b, day, 'loan', f'Trả kỳ {", ".join(str(r["k"]) for r in rows)} · Vay mua nhà', -amount)
            msg = f'Đã trả {_fmt(amount)} xu cho khoản vay mua nhà.'
            if all(r['paid'] >= r['amount'] for r in ln['rows']):
                _close_loan(s, h, day, 'home_done')
                _log(h, day, 'Trả xong khoản vay mua nhà.')
                msg += ' Khoản vay đã trả xong, căn nhà hoàn toàn là của bạn!'
            return dict(message=msg)
        need(p.get('confirm') is True, 'Xác nhận tất toán khoản vay mua nhà.')
        off = _payoff(ln, day)
        need(have['balance'] + have['wallet'] >= off['total'], f'Tất toán cần {_fmt(off["total"])} xu: tài khoản và ví còn thiếu '
                                                                f'{_fmt(off["total"] - have["balance"] - have["wallet"])} xu.', 'not_enough')
        _take(s, off['total'], 'Tất toán sớm vay mua nhà', day)
        b['stats']['fees'] += off['fee']
        bk._log(b, day, 'loan', f'Tất toán sớm vay mua nhà · phí {_fmt(off["fee"])} xu', -off['total'])
        _close_loan(s, h, day, 'home_done')
        _log(h, day, f'Tất toán sớm khoản vay mua nhà: {_fmt(off["total"])} xu.', -off['total'])
        return dict(message=f'Đã tất toán {_fmt(off["total"])} xu (phí trả trước hạn {_fmt(off["fee"])} xu), bớt được '
                            f'{_fmt(max(0, off["saved"]))} xu tiền lãi. Căn nhà giờ không còn nợ!')
    # jr_home_sell
    need(own, 'Bạn chưa có nhà để bán.')
    need(p.get('confirm') is True, 'Xác nhận bán nhà.')
    value = value_of(own, day)
    need(p.get('value') == value, 'Giá thị trường vừa thay đổi. Xem lại rồi bán nhé.', 'stale_quote')
    fee = sell_fee(value)
    off = _payoff(own['loan'], day, fee=False) if own['loan'] else None
    got = value - fee - (off['total'] if off else 0)
    need(got >= 0, 'Tiền bán nhà chưa đủ trả hết khoản vay. Nộp thêm tiền trả bớt nợ rồi hãy bán nhé.')
    H = HOMES[own['kind']]
    b = bk.get(s)
    if off:
        bk._log(b, day, 'loan', f'Bán nhà, trả hết vay mua nhà: {_fmt(off["total"])} xu', -off['total'])
        _close_loan(s, h, day, '')
    to = _receive(s, got, f'Tiền bán {lname(H["name"])}', day) if got else 'ví'
    h['past'] = ar.last(h['past'] + [dict(id=own['id'], kind=own['kind'], bought=own['day'], sold=day, price=own['price'], got=got)], PAST_MAX, 'home.past', ar.JOURNEY)
    h['own'] = None
    h['stats']['sold'] += 1
    _log(h, day, f'Bán {lname(H["name"])} được {_fmt(value)} xu, phí {_fmt(fee)} xu' + (f', trả nợ vay {_fmt(off["total"])} xu' if off else '') + '.', got)
    msg = f'Đã bán {lname(H["name"])} giá {_fmt(value)} xu (phí môi giới, thuế {_fmt(fee)} xu)'
    msg += f', trả hết nợ vay {_fmt(off["total"])} xu' if off else ''
    msg += f'. {_fmt(got)} xu đã về {to}.'
    back = where(h)[0]
    return dict(message=msg + (' ' + MOVE_LINES['back'] if back == 'attic' else ''))


def action(s: dict, name: str, p: dict) -> dict:
    """Entry from journey.action (which runs journey.after and validate_state)."""
    return apply(s, name, p or {})


# ---------------------------------------------------------------- views
def rules() -> dict:
    return dict(month_days=MONTH_DAYS, year_days=YEAR_DAYS, down_pct=DOWN_PCT, buy_fee_pct=BUY_FEE_PCT, sell_fee_pct=SELL_FEE_PCT,
                fee_min=FEE_MIN, grow_rate=GROW_RATE, grow_cap_pct=GROW_CAP_PCT, home_score=HOME_SCORE,
                rates=[dict(min=low, rate=rate) for low, rate in RATES], months=list(LOAN_MONTHS), loan_min=LOAN_MIN, dti_pct=DTI_PCT,
                grace=GRACE, late_pct=LATE_PCT, late_min=LATE_MIN, payoff_fee_pct=PAYOFF_FEE_PCT, payoff_fee_min=PAYOFF_FEE_MIN)


def catalogue() -> dict:
    """The homes on the market, static (journey.content()['homes'], sent once at bootstrap): public()'s
    market rows carry only what changes (how much is still missing), the browser joins the two by id."""
    homes = []
    for k, H in HOMES.items():
        row = dict(id=k, kind=H['kind'], group=H['group'], emoji=H['emoji'], name=H['name'], where=H['where'], desc=H['desc'],
                   comfort=H['comfort'], perk=H.get('perk'))
        if H['kind'] == 'rent':
            row.update(rent=H['rent'], deposit=H['deposit'])
        else:
            p = H['price']
            row.update(price=p, upkeep=H['upkeep'], down_min=down_min(p), fee=buy_fee(p), need=down_min(p) + buy_fee(p),
                       cash_all=p + buy_fee(p), score=need_score(k))
        homes.append(row)
    return dict(groups=[dict(id=g, emoji=e, name=n, color=c) for g, e, n, c in GROUPS], homes=homes)


def _market(ready: int) -> list[dict]:
    """Per home: what is still missing for the deposit (rent), the down payment and fee, or the whole price."""
    out = []
    for k, H in HOMES.items():
        if H['kind'] == 'rent':
            out.append(dict(id=k, missing=max(0, H['deposit'] - ready)))
        else:
            p, fee = H['price'], buy_fee(H['price'])
            out.append(dict(id=k, missing=max(0, down_min(p) + fee - ready), missing_all=max(0, p + fee - ready)))
    return out


def _place_view(s: dict, h: dict | None) -> dict:
    j = s['journey']
    place, kind = where(h)
    cost = living(j, _jr().LIVING.get(j['chapter'], _jr().LIVING[_jr().LAST]))
    if place == 'attic':
        return dict(ATTIC, where_id='attic', kind=None, group=None, comfort=0, perk=None, cost=cost)
    H = HOMES[kind]
    out = dict(emoji=H['emoji'], name=H['name'], where=H['where'], desc=H['desc'], where_id=place, kind=kind, group=H['group'],
               comfort=H['comfort'], perk=H.get('perk'), cost=cost)
    if place == 'shared':
        out['with'] = h['shared']['name']
    return out


def public(s: dict) -> dict:
    j = s['journey']
    h = get(s)
    b = bk.get(s)
    day = j['life_day']
    have = _have(s)
    ready = have['wallet'] + have['balance']
    attic = attic_rent(j)
    market = _market(ready)
    o = offer(s)
    o['rate_text'] = bk.year_text(o['rate'])
    own = None
    if h and h['own']:
        x = h['own']
        H = HOMES[x['kind']]
        value = value_of(x, day)
        fee = sell_fee(value)
        ln = x['loan']
        loan = None
        off_sale = _payoff(ln, day, fee=False) if ln else None
        if ln:
            nxt = next((r for r in ln['rows'] if r['paid'] < r['amount']), None)
            loan = dict(ln, rate_text=bk.year_text(ln['rate']), left=sum(r['amount'] - r['paid'] for r in ln['rows']),
                        principal_left=sum(r['principal'] for r in ln['rows'] if r['paid'] < r['amount']), next=nxt,
                        overdue=sum(r['amount'] - r['paid'] for r in ln['rows'] if r['due'] <= day and r['paid'] < r['amount']),
                        late=_late(ln), payoff=_payoff(ln, day), paid_rows=sum(1 for r in ln['rows'] if r['paid'] >= r['amount']))
        own = dict(x, emoji=H['emoji'], group=H['group'], perk=H.get('perk'), list_price=H['price'], name=H['name'], where=H['where'],
                   desc=H['desc'], upkeep=H['upkeep'], comfort=H['comfort'],
                   value=value, loan=loan, sell=dict(value=value, fee=fee, payoff=off_sale['total'] if off_sale else 0,
                                                     get=value - fee - (off_sale['total'] if off_sale else 0)))
    rent = None
    if h and h['rent']:
        H = HOMES[h['rent']['kind']]
        rent = dict(h['rent'], emoji=H['emoji'], name=H['name'], where=H['where'], rent_day=H['rent'], comfort=H['comfort'])
    shared = None
    if h and h['shared']:
        H = HOMES[h['shared']['kind']]
        shared = dict(h['shared'], emoji=H['emoji'], home=H['name'], where=H['where'], upkeep=H['upkeep'], comfort=H['comfort'])
    sp = _spouse(s)
    return dict(story=bool(j.get('story')), life_day=day, have=dict(have, ready=ready, bank=b is not None, debt=max(0, -j['wallet']),
                savings=bk._savings_total(b) if b else 0), place=_place_view(s, h), attic_rent=attic, market=market, offer=o,
                own=own, rent=rent, shared=shared, married=bool(sp), spouse=(sp or {}).get('name'),
                log=list(reversed(h['log'])) if h else [], stats=dict(h['stats']) if h else {k: 0 for k in STATS}, rules=rules())


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    j = s.get('journey')
    if not isinstance(j, dict) or j.get('home') is None:
        return
    h = j['home']
    bad = 'Dữ liệu nhà ở không hợp lệ.'
    need(isinstance(h, dict) and set(h) == set(initial()) and h['v'] == VERSION, bad, 'invalid_save')
    integer(h['seq'], 0, 10**6)
    integer(h['day'], 1, 10**6)
    need(h['day'] <= j['life_day'], bad)
    need(isinstance(h['stats'], dict) and set(h['stats']) == set(STATS), bad)
    for v in h['stats'].values():
        integer(v, 0, 10**9)
    r = h['rent']
    if r is not None:
        need(isinstance(r, dict) and set(r) == {'kind', 'since', 'deposit'} and r['kind'] in RENT and r['deposit'] == HOMES[r['kind']]['deposit'], bad)
        integer(r['since'], 1, 10**6)
    x = h['own']
    need(not (x and r), bad)
    if x is not None:
        need(isinstance(x, dict) and set(x) == {'id', 'kind', 'price', 'day', 'down', 'fee', 'joint', 'loan'} and x['kind'] in OWN
             and x['price'] in prices(x['kind']) and x['fee'] == buy_fee(x['price']), bad)
        txt(x['id'], 16)
        integer(x['day'], 1, 10**6)
        integer(x['down'], down_min(x['price']), x['price'])
        integer(x['joint'], 0, x['down'] + x['fee'])
        ln = x['loan']
        if ln is not None:
            need(bk.get(s) is not None, bad)
            need(isinstance(ln, dict) and set(ln) == {'principal', 'rate', 'months', 'start', 'rows'} and ln['months'] in LOAN_MONTHS
                 and ln['rate'] in [rate for _, rate in RATES] and ln['principal'] == x['price'] - x['down'] and ln['start'] == x['day'], bad)
            rows = ln['rows']
            need(isinstance(rows, list) and len(rows) == ln['months'], bad)
            for i, row in enumerate(rows):
                need(isinstance(row, dict) and set(row) == {'k', 'due', 'principal', 'interest', 'amount', 'paid', 'fee', 'late'}
                     and row['k'] == i + 1 and row['due'] == ln['start'] + MONTH_DAYS * (i + 1) and type(row['late']) is bool, bad)
                for k in ('principal', 'interest', 'amount', 'paid', 'fee'):
                    integer(row[k], 0, bk.AMOUNT_MAX * 2)
                need(row['amount'] == row['principal'] + row['interest'] + row['fee'] and row['paid'] <= row['amount'], bad)
            need(sum(row['principal'] for row in rows) == ln['principal'], bad)
    sh = h['shared']
    if sh is not None:
        need(isinstance(sh, dict) and set(sh) == {'couple', 'id', 'kind', 'name', 'since'} and sh['kind'] in OWN, bad)
        integer(sh['couple'], 1, 10**12)
        txt(sh['id'], 16)
        txt(sh['name'], 24)
        integer(sh['since'], 1, 10**6)
    need(isinstance(h['past'], list) and len(h['past']) <= PAST_MAX, bad)
    for p in h['past']:
        need(isinstance(p, dict) and set(p) == {'id', 'kind', 'bought', 'sold', 'price', 'got'} and p['kind'] in OWN, bad)
        txt(p['id'], 16)
        for k in ('bought', 'sold'):
            integer(p[k], 1, 10**6)
        integer(p['price'], 1, bk.AMOUNT_MAX)
        integer(p['got'], 0, bk.AMOUNT_MAX * 2)
    need(isinstance(h['log'], list) and len(h['log']) <= LOG_MAX, bad)
    for row in h['log']:
        need(isinstance(row, dict) and set(row) == {'day', 'text', 'amt'}, bad)
        integer(row['day'], 1, 10**6)
        txt(row['text'], 140)
        integer(row['amt'], -bk.AMOUNT_MAX * 2, bk.AMOUNT_MAX * 2)
