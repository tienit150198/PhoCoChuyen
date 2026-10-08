"""🛍️ Mua sắm hạng sang: trips abroad, collections, estates, parties, courses and public sponsorships (story mode).

Owner 07/10: "đưa ra nhiều cái mà mọi người sẽ mua để kích thích khả năng tiêu tiền vì hiện tại mọi người nhiều tiền quá
rồi". The money sits at the top (DESIGN_0610 §0.1: p90 wallets ≈ 3,300, p99 ≈ 26,400, the top 1 % hold half of all
wealth); this is the shop for it, 5,000 → 3,000,000 xu (catalogue: game/lux_content.py). Never pay-to-win: no command
here pays xu (only selling back, at a loss), speeds up work or helps an exam. Status, the album, tinh thần within its
caps, and public plaques.

* ✈️ Du lịch (jr_lux_photo, jr_lux_insure, jr_lux_visa, jr_lux_trip, jr_lux_souv): five destinations. The visa is the
  annoying part: the consulate wants papers (an ID photo under 30 life days old, a bank statement of 1–3× the trip, an
  employer letter, an itinerary, travel insurance for Europe) and the US asks three interview questions. The fee is paid
  whatever happens; a missing or bad paper means a refusal (the first problem is named). A visa lasts some life days;
  then any class, one trip a life day: the album, a passport stamp, tinh thần, souvenirs of that country (that day only).
* 💎 Sưu tập (jr_lux_buy / jr_lux_sell, jr_lux_open for wine): six sets of five pieces, ★ to ★★★★, one of each.
  Resold at SELL_PCT %; an opened bottle is gone (a line in the album).
* 🏰 Dinh thự (jr_lux_buy / jr_lux_sell, jr_lux_live {id | None}): six villas, 150,000 → 2,500,000 xu
  (game/estates_content.py), lived in with their own bigger rooms on several floors (game/estates.py, game/deco.py).
  Resold at SELL_PCT %; selling the one you live in sends you back to journey.home (or Bà Tám's attic).
* 🛫 Phi cơ & du thuyền (jr_lux_buy / jr_lux_sell, jr_lux_use): vehicles with a crew above the garage's yacht. Resold
  at SELL_PCT %. One trip out a life day (its fee shown on the button) for tinh thần.
* 🧾 Phí hạng sang: every villa and vehicle, and every collection piece from INSURE_FROM xu, costs basis points of the price paid a
  tháng (game/upkeep.py's month, 5 life days), accrued every life-day morning and billed with the month: the wallet
  (never below 0), then the bank account; what both lack is waived, never owed. Nothing before `upk.since` is billed.
* 🎉 Tiệc (jr_lux_party): a birthday or a housewarming, four catering tiers × guests, one a life day.
* 🎓 Khóa học (jr_lux_course, jr_lux_study): paid up front, one free lesson a life day, a title at the end.
* 🎆 Mạnh Thường Quân (jr_lux_give): fireworks for the whole street (one show every `gap` seconds on the server), a
  numbered bench or lamp with the giver's name and a fixed dedication (permanent, one per slot), the fair's or a ZPOP
  night's sponsor of the week, the school library fund. A pure sink, public: the `lux_gifts` row is written in the save's
  own transaction (command_commit: a taken slot or fireworks too soon refuse the whole command, so nothing is paid), a
  line on the street's ticker (`news`), fireworks also on Cả phố. GET /api/mtq is the weekly board.
  🎆 Fireworks (owner 08/10: "phải có bắn toàn server cho mọi người thấy chứ k phải là chỉ có chữ"): with an optional
  wish from C.FW_WISHES (`msg`, an id kept in give.last.m), and on commit a NOTIFY op 'fireworks' that the live service
  (live/fireworks.py) turns into a real show on every open screen: bursts over the page and a long banner.
* 🏷️ Titles earned here are granted into game/spend.py's block for good (own until spend_content.PERMANENT) and worn
  from Phong cách like the weekly ones: the live service shows them as `st.t` (an older one ignores the id).

Money: purchases from the wallet, then the bank account (never a loan, never with a wallet in debt). Wallet rows use the
existing kinds 'life' ('study' for a course, 'upkeep' for the bills): no closed list grows, so 1.9.9 loads every save.

State `s['journey']['lux']` (absent until the first purchase; journey.validate allows extra keys, so 1.9.9 and older keep
it untouched and simply do not bill it), see initial():
    v       VERSION
    own     {id: {d: life day bought, p: price paid}}      collection pieces, vehicles, villas
    live    the villa lived in (an id of own) or None
    visa    {country: last life day it is valid}           photo  the life day of the ID photo (0 none)
    ins     the country of the travel insurance bought for the next application ('' none)
    trips   {country: trips}                               souv   {souvenir id: copies}
    course  {course id: lessons done}                      album  [{k, i, c, d, n}], newest last, ≤ ALBUM_MAX
    day     the life day `today` belongs to                today  ids of what was done that life day (caps)
    upk     {since, day, acc (milli-xu), paid} or None     give   {n, sum, lib, fw, last}
    stats   {bought, sold, pieces, trips, parties, lessons, opened, visas, refused, xu}
Ids a newer build wrote are kept by shape and not shown, so a rollback never loses anything.
"""
from __future__ import annotations

import datetime
import hashlib
import re
import threading
import time

from . import bank as bk
from . import estates as es
from . import lux_content as C

VERSION = 1
KEY = 'lux'
KIND = 'life'
BLOCK_KEYS = frozenset({'v', 'own', 'live', 'visa', 'photo', 'ins', 'trips', 'souv', 'course', 'album', 'day', 'today', 'upk',
                        'give', 'stats'})
GIVE_KEYS = frozenset({'n', 'sum', 'lib', 'fw', 'last'})
LAST_KEYS = frozenset({'n', 'k', 'z', 's', 'a', 'm', 'anon', 'wk', 'at'})
ALBUM_KEYS = frozenset({'k', 'i', 'c', 'd', 'n'})
ALBUM_KINDS = ('trip', 'party', 'wine', 'give', 'use')
UPK_KEYS = frozenset({'since', 'day', 'acc', 'paid'})
STATS = ('bought', 'sold', 'pieces', 'trips', 'parties', 'lessons', 'opened', 'visas', 'refused', 'xu')
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
WK_RE = re.compile(r'[0-9]{4}-W[0-9]{2}')
ALBUM_MAX = 40
TODAY_MAX = 24
OWN_MAX = 64
BIG = 10**12
CATCH_UP = 400                    # life days caught up at most (like game/upkeep.py)
COMMANDS = ('jr_lux_buy', 'jr_lux_sell', 'jr_lux_open', 'jr_lux_use', 'jr_lux_photo', 'jr_lux_insure', 'jr_lux_visa',
            'jr_lux_trip', 'jr_lux_souv', 'jr_lux_party', 'jr_lux_course', 'jr_lux_study', 'jr_lux_give', 'jr_lux_live')
VN = datetime.timezone(datetime.timedelta(hours=7))
UPKEEP_LABEL = 'Phí hạng sang'

COUNTRY = {c['id']: c for c in C.COUNTRIES}
CLASS = {c['id']: c for c in C.CLASSES}
DOC = {d['id']: d for d in C.DOCS}
SOUV = {it['id']: (cid, it) for cid, rows in C.SOUVENIRS.items() for it in rows}
PIECE = {it['id']: dict(it, set=st['id'], emoji=st['emoji']) for st in C.SETS for it in st['items']}
ASSET = {a['id']: a for a in C.ASSETS}
ESTATE = es.ESTATE              # 🏰 the villas (game/estates_content.py)
GOODS = {**PIECE, **ASSET, **ESTATE}
PARTY_KIND = {k['id']: k for k in C.PARTY_KINDS}
PARTY_TIER = {t['id']: t for t in C.PARTY_TIERS}
COURSE = {c['id']: c for c in C.COURSES}
GIVE = {g['id']: g for g in C.GIVES}
DEDICATION = dict(C.DEDICATIONS)
FW_WISH = dict(C.FW_WISHES)


# ---------------------------------------------------------------- helpers
def now() -> float:
    return time.time()


def week_key(t: float | None = None) -> str:
    y, w, _ = datetime.datetime.fromtimestamp(now() if t is None else t, VN).isocalendar()
    return f'{y:04d}-W{w:02d}'


def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _sp():
    from . import spend
    return spend


def _fmt(n: int) -> str:
    return bk._fmt(n)


def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


def _id(v) -> bool:
    return isinstance(v, str) and ID_RE.fullmatch(v) is not None


def initial(day: int = 1) -> dict:
    return dict(v=VERSION, own={}, live=None, visa={}, photo=0, ins='', trips={}, souv={}, course={}, album=[], day=max(1, int(day)),
                today=[], upk=None, give=dict(n=0, sum=0, lib=0, fw=0, last=None), stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial(j['life_day'])
    b = j[KEY]
    if b['day'] != j['life_day']:
        b['day'], b['today'] = j['life_day'], []
    if b['upk'] is None:   # bills start the day the block does: nothing before is owed
        b['upk'] = dict(since=j['life_day'], day=j['life_day'], acc=0, paid=0)
    return b


def _today(s: dict) -> list:
    b = get(s)
    return list(b['today']) if b and b['day'] == s['journey']['life_day'] else []


def _have(s: dict) -> int:
    """What a purchase may use: the cash in the wallet (none while it is in debt) and the bank account."""
    j = s['journey']
    b = bk.get(s)
    return max(0, j['wallet']) + (b['balance'] if b else 0)


def ready_why(s: dict, price: int) -> str:
    j = s['journey']
    if j['wallet'] < 0:
        return f'Ví đang nợ {_fmt(-j["wallet"])} xu. Trả nợ trước nhé.'
    short = price - _have(s)
    return f'Còn thiếu {_fmt(short)} xu.' if short > 0 else ''


def _take(s: dict, amount: int, label: str, kind: str = KIND) -> str:
    """`amount` from the wallet first, then the bank account (the caller checked it is there). Where it came from."""
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _jr()._wallet(j, -cash, kind, label[:120])
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label[:120], -rest)
    if rest and cash:
        return f'{_fmt(cash)} xu tiền mặt và {_fmt(rest)} xu từ tài khoản'
    return f'{_fmt(amount)} xu từ tài khoản' if rest else f'{_fmt(amount)} xu tiền mặt'


def _spirit(s: dict, n: int) -> int:
    from . import needs
    return needs._spirit(s, n)


def _pick(s: dict, salt: str, lines: tuple) -> str:
    j = s['journey']
    h = hashlib.sha256(f"{j.get('seed', 0)}|{j['life_day']}|{salt}".encode()).digest()
    return lines[h[0] % len(lines)]


def _album(b: dict, k: str, i: str, c: str, d: int, n: int = 0) -> None:
    b['album'] = (b['album'] + [dict(k=k, i=i, c=c, d=d, n=int(n))])[-ALBUM_MAX:]


def sell_price(paid: int) -> int:
    return max(0, int(paid) * C.SELL_PCT // 100 // 10 * 10)


def trip_price(cid: str, cls: str) -> int:
    return COUNTRY[cid]['trip'] * CLASS[cls]['mult']


def party_price(tier: str, guests: int) -> int:
    t = PARTY_TIER[tier]
    return t['base'] + t['guest'] * int(guests)


def insure_price(cid: str) -> int:
    return COUNTRY[cid]['trip'] * C.INSURE_PCT // 100


# ---------------------------------------------------------------- 🧾 phí hạng sang
def upkeep_bp(gid: str, price: int) -> int:
    """Basis points a tháng for something owned (0: nothing to pay; an id this build does not know pays nothing)."""
    if gid in ASSET:
        return ASSET[gid]['bp']
    if gid in ESTATE:
        return ESTATE[gid]['bp']
    if gid in PIECE and price >= C.INSURE_FROM:
        return C.INSURE_BP
    return 0


def _daily_milli(price: int, bp: int) -> int:
    return max(0, int(price)) * bp // (10 * bk.MONTH_DAYS)


def month_of(gid: str, price: int) -> int:
    """About a tháng of one thing, in xu (shown; the bill is the exact sum of its days)."""
    return (_daily_milli(price, upkeep_bp(gid, price)) * bk.MONTH_DAYS + 500) // 1000


def monthly(s: dict) -> int:
    b = get(s)
    if not b:
        return 0
    m = sum(_daily_milli(x['p'], upkeep_bp(i, x['p'])) for i, x in b['own'].items() if isinstance(x, dict))
    return (m * bk.MONTH_DAYS + 500) // 1000


def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Catch the bills up to journey.life_day (idempotent: the day counter; after game/upkeep.py's bills)."""
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
        u['acc'] = min(BIG, u['acc'] + sum(_daily_milli(x['p'], upkeep_bp(i, x['p'])) for i, x in b['own'].items()))
        if u['day'] % bk.MONTH_DAYS == 0:
            amount, u['acc'] = u['acc'] // 1000, u['acc'] % 1000
            if amount <= 0:
                continue
            n = sum(1 for i, x in b['own'].items() if upkeep_bp(i, x['p']))
            got = _bill(s, amount, f'{UPKEEP_LABEL} · {n} món', u['day'])
            u['paid'] = min(BIG, u['paid'] + got)
            line = f'🧾 {UPKEEP_LABEL} (bảo hiểm, bảo dưỡng, nhân viên): {_fmt(amount)} xu.'
            if got < amount:
                line += f' Thiếu {_fmt(amount - got)} xu được miễn, không tính nợ.'
            notes.append(line)
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


def _bill(s: dict, amount: int, label: str, day: int) -> int:
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _jr()._wallet(j, -cash, 'upkeep', label)
    b = bk.get(s)
    rest = min(amount - cash, b['balance']) if b else 0
    if rest > 0:
        b['balance'] -= rest
        bk._log(b, day, 'acc', label, -rest)
    return cash + max(0, rest)


# ---------------------------------------------------------------- 🏷️ titles (worn through game/spend.py)
def _metrics(s: dict) -> dict:
    b = get(s) or initial()
    own = b['own']
    done = {cid for cid, n in b['course'].items() if cid in COURSE and n >= COURSE[cid]['lessons']}
    m = dict(countries=sum(1 for c, n in b['trips'].items() if c in COUNTRY and n > 0), pieces=b['stats'].get('pieces', 0),
             legend=sum(1 for i in own if i in PIECE and PIECE[i]['rare'] >= 4),
             home=sum(1 for i in own if i in ESTATE), island=int('dinh_thu_dao' in own),
             fly=sum(1 for i in own if i in ASSET and ASSET[i]['group'] == 'fly'), parties=b['stats'].get('parties', 0),
             langs=sum(1 for c in done if COURSE[c].get('lang')), gave=b['give']['sum'], fireworks=b['give']['fw'],
             library=b['give']['lib'])
    for c in done:
        m['course:' + c] = 1
    return m


def earned(s: dict) -> list[str]:
    m = _metrics(s)
    return [tid for tid, rule, n in C.EARN if m.get(rule, 0) >= n]


def _award(s: dict) -> list[str]:
    """Grant every title earned and not held yet (for good). The names of the new ones."""
    sp = _sp()
    from . import spend_content as SC
    new = []
    for tid in earned(s):
        b = sp.get(s)
        if b and b['own'].get(tid, 0) >= SC.PERMANENT:
            continue
        b = sp._ensure(s)
        if len(b['own']) >= sp.OWN_MAX and tid not in b['own']:
            continue   # never fails a purchase: the slot list is full of weekly items (cannot happen with today's lists)
        b['own'][tid] = SC.PERMANENT
        new.append(SC.TITLE_TEXT[tid])
    return new


# ---------------------------------------------------------------- ✈️ visa
def asked(s: dict, cid: str) -> list[int]:
    """The interview questions of the next application to `cid` (indices of C.INTERVIEW)."""
    n = COUNTRY[cid].get('interview', 0)
    if not n:
        return []
    b = get(s)
    if b and b['course'].get('tieng_anh', 0) >= COURSE['tieng_anh']['lessons']:
        n = 1   # 🇬🇧 the English course: one question is enough
    j = s['journey']
    tries = b['stats'].get('visas', 0) + b['stats'].get('refused', 0) if b else 0
    key = lambda i: hashlib.sha256(f"{j.get('seed', 0)}|{cid}|{tries}|{i}".encode()).digest()
    return sorted(sorted(range(len(C.INTERVIEW)), key=key)[:n])


def visa_left(s: dict, cid: str) -> int:
    """Life days a visa still has (0: none or expired)."""
    b = get(s)
    until = b['visa'].get(cid, 0) if b else 0
    return max(0, until - s['journey']['life_day'] + 1)


def _bank_shows(s: dict) -> int | None:
    b = bk.get(s)
    return None if not b else max(0, b['balance']) + max(0, b.get('demand', 0) or 0)


def doc_problem(s: dict, cid: str, doc: str) -> str:
    """Why the consulate would refuse this paper ('' = it is fine)."""
    j = s['journey']
    co = COUNTRY[cid]
    b = get(s)
    if doc == 'anh':
        if not b or not b['photo']:
            return 'thiếu ảnh 3.5×4.5 nền trắng'
        if j['life_day'] - b['photo'] >= C.PHOTO_DAYS:
            return f'ảnh chụp quá {C.PHOTO_DAYS} ngày rồi'
    elif doc == 'sao_ke':
        shows, want = _bank_shows(s), co['bank'] * co['trip']
        if shows is None:
            return 'chưa có tài khoản ngân hàng để sao kê'
        if shows < want:
            return f'sao kê chưa đủ {_fmt(want)} xu'
    elif doc == 'cong_viec':
        if len(j.get('days') or ()) < C.WORK_DAYS:
            return f'chưa đủ {C.WORK_DAYS} ngày đi làm để xác nhận'
    elif doc == 'bao_hiem':
        if not b or b['ins'] != cid:
            return 'chưa mua bảo hiểm du lịch'
    return ''


# ---------------------------------------------------------------- save
def _counts(d, hi: int, n: int = 64) -> bool:
    return isinstance(d, dict) and len(d) <= n and all(_id(k) and _int(v, 0, hi) for k, v in d.items())


def _own_ok(d) -> bool:
    return isinstance(d, dict) and len(d) <= OWN_MAX and all(
        _id(k) and isinstance(x, dict) and set(x) == {'d', 'p'} and _int(x['d'], 1, 10**6) and _int(x['p'], 1, 10**8)
        for k, x in d.items())


def _album_ok(x) -> bool:
    return (isinstance(x, dict) and set(x) == ALBUM_KEYS and x['k'] in ALBUM_KINDS and _id(x['i'])
            and isinstance(x['c'], str) and (x['c'] == '' or _id(x['c'])) and _int(x['d'], 1, 10**6) and _int(x['n'], 0, BIG))


def _last_ok(x) -> bool:
    return x is None or (isinstance(x, dict) and set(x) == LAST_KEYS and _int(x['n'], 1, 10**9) and _id(x['k'])
                         and isinstance(x['z'], str) and (x['z'] == '' or _id(x['z'])) and _int(x['s'], 0, 1000)
                         and _int(x['a'], 1, BIG) and isinstance(x['m'], str) and (x['m'] == '' or _id(x['m']))
                         and type(x['anon']) is bool and isinstance(x['wk'], str) and WK_RE.fullmatch(x['wk']) is not None
                         and _int(x['at'], 0, 2**34))


def _upk_ok(u, day: int) -> bool:
    return u is None or (isinstance(u, dict) and set(u) == UPK_KEYS and _int(u['since'], 1, 10**6) and _int(u['day'], 1, 10**6)
                         and u['since'] <= u['day'] <= max(u['since'], day) and _int(u['acc']) and _int(u['paid']))


def validate(s: dict) -> None:
    """``s['journey']['lux']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    j = s.get('journey')
    b = get(s)
    bad = 'Dữ liệu mua sắm trong bản lưu không hợp lệ.'
    if b is None:
        e.need(not isinstance(j, dict) or j.get(KEY) is None, bad, 'invalid_save')
        return
    need = lambda ok: e.need(ok, bad, 'invalid_save')
    need(set(b) == BLOCK_KEYS and b['v'] == VERSION and _int(b['day'], 1, 10**6))
    need(b['live'] is None or (_id(b['live']) and b['live'] in b['own']))
    need(_own_ok(b['own']) and _counts(b['visa'], 10**7, 16) and _int(b['photo'], 0, 10**6))
    need(isinstance(b['ins'], str) and (b['ins'] == '' or _id(b['ins'])))
    need(_counts(b['trips'], 10**9, 16) and _counts(b['souv'], C.SOUV_MAX) and _counts(b['course'], 1000, 32))
    need(isinstance(b['album'], list) and len(b['album']) <= ALBUM_MAX and all(_album_ok(x) for x in b['album']))
    need(isinstance(b['today'], list) and len(b['today']) <= TODAY_MAX and all(_id(x) for x in b['today']))
    need(_upk_ok(b['upk'], int(j.get('life_day', 1))))
    g = b['give']
    need(isinstance(g, dict) and set(g) == GIVE_KEYS and _int(g['n'], 0, 10**9) and _int(g['sum']) and _int(g['lib'])
         and _int(g['fw'], 0, 10**9) and _last_ok(g['last']) and (g['last'] is None or g['last']['n'] == g['n']))
    st = b['stats']
    need(isinstance(st, dict) and set(st) <= set(STATS) and all(_int(v) for v in st.values()))


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep what still makes sense. Absent stays
    absent."""
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    day = j.get('life_day') if _int(j.get('life_day'), 1, 10**6) else 1
    if not isinstance(b, dict):
        j[KEY] = initial(day)
        return
    out = initial(b['day'] if _int(b.get('day'), 1, 10**6) else day)
    d = lambda k: b.get(k) if isinstance(b.get(k), dict) else {}
    out['own'] = {k: dict(d=x['d'], p=x['p']) for k, x in list(d('own').items())[:OWN_MAX]
                  if _id(k) and isinstance(x, dict) and _int(x.get('d'), 1, 10**6) and _int(x.get('p'), 1, 10**8)}
    for k, hi, n in (('visa', 10**7, 16), ('trips', 10**9, 16), ('souv', C.SOUV_MAX, 64), ('course', 1000, 32)):
        out[k] = {x: v for x, v in list(d(k).items())[:n] if _id(x) and _int(v, 0, hi)}
    out['photo'] = b['photo'] if _int(b.get('photo'), 0, 10**6) else 0
    out['ins'] = b['ins'] if isinstance(b.get('ins'), str) and (b['ins'] == '' or _id(b['ins'])) else ''
    if isinstance(b.get('album'), list):
        out['album'] = [{k: x[k] for k in ALBUM_KEYS} for x in b['album'] if isinstance(x, dict) and set(x) >= ALBUM_KEYS
                        and _album_ok({k: x[k] for k in ALBUM_KEYS})][-ALBUM_MAX:]
    if isinstance(b.get('today'), list):
        out['today'] = [x for x in b['today'] if _id(x)][:TODAY_MAX]
    u = b.get('upk')
    if isinstance(u, dict) and set(u) >= UPK_KEYS:
        u = {k: u[k] for k in UPK_KEYS}
        out['upk'] = u if _upk_ok(u, day) else None
    g = d('give')
    for k in ('n', 'sum', 'lib', 'fw'):
        if _int(g.get(k), 0, 10**9 if k in ('n', 'fw') else BIG):
            out['give'][k] = g[k]
    last = g.get('last')
    if isinstance(last, dict) and set(last) >= LAST_KEYS:
        last = {k: last[k] for k in LAST_KEYS}
    out['give']['last'] = last if _last_ok(last) and last and last['n'] == out['give']['n'] else None
    out['live'] = b['live'] if _id(b.get('live')) and b['live'] in out['own'] else None
    st = d('stats')
    out['stats'] = {k: st[k] if _int(st.get(k)) else 0 for k in STATS}
    if out != b:
        j[KEY] = out


# ---------------------------------------------------------------- commands
def _keys(p: dict, allowed: set, required: set = frozenset()) -> None:
    _core().need(isinstance(p, dict) and set(p) <= allowed and required <= set(p), 'Thông tin không hợp lệ.')


def _confirm(p: dict, what: str) -> None:
    _core().need(p.get('confirm') is True, f'Xác nhận {what}.')


def _pay_ok(s: dict, price: int) -> None:
    why = ready_why(s, price)
    _core().need(not why, why, 'not_enough')


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Mua sắm chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    out = _ACTIONS[name](s, p)
    new = _award(s)
    if new:
        out['message'] = out.get('message', '') + ' 🏷️ Danh hiệu mới: ' + ', '.join(new) + ' (đeo ở Phong cách).'
    return out


def _buy(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'id', 'confirm'}, {'id'})
    it = GOODS.get(p['id']) if isinstance(p['id'], str) else None
    need(it is not None and not it.get('gone'), 'Chọn một món nhé.')
    b = get(s)
    if b and it['id'] in b['own']:   # a second tap: nothing to pay
        return dict(message=f'Bạn đã có {it["name"]} rồi.', duplicate=True)
    _confirm(p, f'mua {it["name"]} {_fmt(it["price"])} xu')
    _pay_ok(s, it['price'])
    how = _take(s, it['price'], f'Mua sắm · {it["name"]}')
    b = _ensure(s)
    b['own'][it['id']] = dict(d=s['journey']['life_day'], p=it['price'])
    b['stats']['bought'] += 1
    b['stats']['xu'] += it['price']
    if it['id'] in PIECE:
        b['stats']['pieces'] += 1
    m = month_of(it['id'], it['price'])
    tail = ' Vào Tài sản để dọn về ở.' if it['id'] in ESTATE else ''
    return dict(message=f'{it["emoji"]} Đã có {it["name"]}: trả {how}.' + (f' Phí giữ {_fmt(m)} xu/tháng.' if m else '') + tail)


def _sell(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'id', 'confirm'}, {'id'})
    b = get(s)
    it = GOODS.get(p['id']) if isinstance(p['id'], str) else None
    need(it is not None and b is not None and it['id'] in b['own'], 'Bạn chưa có món này.', 'not_owned')
    back = sell_price(b['own'][it['id']]['p'])
    _confirm(p, f'bán {it["name"]} lấy {_fmt(back)} xu')
    b = _ensure(s)
    b['own'].pop(it['id'])
    if b['live'] == it['id']:   # 🏰 sold the villa you live in: back to journey.home (or Bà Tám's attic)
        b['live'] = None
    b['stats']['sold'] += 1
    if back:
        _jr()._wallet(s['journey'], back, KIND, f'Bán lại · {it["name"]}'[:120])
    return dict(message=f'Đã bán {it["name"]}, nhận {_fmt(back)} xu vào ví.')


def _open(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'id', 'confirm'}, {'id'})
    b = get(s)
    it = PIECE.get(p['id']) if isinstance(p['id'], str) else None
    need(it is not None and it['set'] == C.WINE_SET, 'Chỉ khui được rượu vang.')
    need(b is not None and it['id'] in b['own'], 'Bạn chưa có chai này.', 'not_owned')
    _confirm(p, f'khui {it["name"]} (không bán lại được nữa)')
    b = _ensure(s)
    b['own'].pop(it['id'])
    b['stats']['opened'] += 1
    got = 0
    if 'wine' not in b['today']:
        b['today'].append('wine')
        got = _spirit(s, C.OPEN_SPIRIT)
    _album(b, 'wine', it['id'], '', s['journey']['life_day'])
    note = ' Hương mận chín, gỗ sồi, hậu vị dài.' if b['course'].get('ruou_vang', 0) >= COURSE['ruou_vang']['lessons'] else ''
    return dict(message=f'🍷 Khui {it["name"]}.{note}' + (f' Tinh thần +{got}.' if got else ''))


def _use(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'id'}, {'id'})
    b = get(s)
    a = ASSET.get(p['id']) if isinstance(p['id'], str) else None
    need(a is not None and b is not None and a['id'] in b['own'], 'Bạn chưa có chỗ này.', 'not_owned')
    need('use' not in _today(s), 'Hôm nay đi nghỉ rồi. Mai nhé.', 'already_done')
    _pay_ok(s, a['use'])
    how = _take(s, a['use'], f'{a["verb"]} · {a["name"]}')
    b = _ensure(s)
    b['today'].append('use')
    got = _spirit(s, C.TRIP_SPIRIT)
    _album(b, 'use', a['id'], '', s['journey']['life_day'])
    b['stats']['xu'] += a['use']
    return dict(message=f'{a["emoji"]} {a["verb"]} ({how}).' + (f' Tinh thần +{got}.' if got else ''),
                effects=[_pick(s, a['id'], C.USE_LINES[a['group']])])


def _photo(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, set())
    j = s['journey']
    b = get(s)
    need(not b or not b['photo'] or j['life_day'] - b['photo'] >= C.PHOTO_DAYS - 5, 'Ảnh thẻ còn mới, chưa cần chụp lại.', 'already_done')
    need(j['wallet'] >= C.PHOTO_PRICE, f'Ví chưa đủ {C.PHOTO_PRICE} xu.', 'not_enough')
    _jr()._wallet(j, -C.PHOTO_PRICE, KIND, 'Chụp ảnh thẻ 3.5×4.5')
    b = _ensure(s)
    b['photo'] = j['life_day']
    b['stats']['xu'] += C.PHOTO_PRICE
    return dict(message=f'📷 Ảnh 3.5×4.5 nền trắng ({C.PHOTO_PRICE} xu), dùng {C.PHOTO_DAYS} ngày.')


def _country(p: dict) -> dict:
    co = COUNTRY.get(p.get('country')) if isinstance(p.get('country'), str) else None
    _core().need(co is not None, 'Chọn một nơi nhé.')
    return co


def _insure(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'country'}, {'country'})
    co = _country(p)
    need('bao_hiem' in co['docs'], f'{co["name"]} không đòi bảo hiểm du lịch.')
    b = get(s)
    need(not b or b['ins'] != co['id'], 'Đã có bảo hiểm cho hồ sơ này.', 'already_done')
    price = insure_price(co['id'])
    _pay_ok(s, price)
    how = _take(s, price, f'Bảo hiểm du lịch · {co["name"]}')
    b = _ensure(s)
    b['ins'] = co['id']
    b['stats']['xu'] += price
    return dict(message=f'🛡️ Bảo hiểm du lịch {co["name"]} ({how}).')


def _visa(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'country', 'docs', 'answers', 'confirm'}, {'country', 'docs'})
    co = _country(p)
    docs, answers = p['docs'], p.get('answers', [])
    need(isinstance(docs, list) and len(docs) <= len(DOC) and len(set(map(str, docs))) == len(docs) and all(d in DOC for d in docs),
         'Hồ sơ không hợp lệ.')
    qs = asked(s, co['id'])
    need(isinstance(answers, list) and len(answers) == len(qs) and all(type(a) is int and 0 <= a < 3 for a in answers),
         'Trả lời đủ câu phỏng vấn nhé.')
    left = visa_left(s, co['id'])
    need(not left, f'Visa {co["name"]} còn {left} ngày.', 'already_done')
    _confirm(p, f'nộp hồ sơ visa {co["name"]}, phí {_fmt(co["visa"])} xu')
    _pay_ok(s, co['visa'])
    how = _take(s, co['visa'], f'Phí visa · {co["name"]}')
    b = _ensure(s)
    b['stats']['xu'] += co['visa']
    why = ''
    for d in co['docs']:   # the consulate's order; extra papers do no harm
        if d not in docs:
            why = f'thiếu {DOC[d]["name"].lower()}' if d != 'anh' else 'thiếu ảnh 3.5×4.5 nền trắng'
        else:
            why = doc_problem(s, co['id'], d)
        if why:
            break
    if not why and any(C.INTERVIEW[q]['ok'] != a for q, a in zip(qs, answers)):
        why = 'câu trả lời phỏng vấn chưa thuyết phục'
    if 'bao_hiem' in co['docs'] and 'bao_hiem' in docs and b['ins'] == co['id']:
        b['ins'] = ''   # the insurance went with this application
    if why:
        b['stats']['refused'] += 1
        return dict(message=f'🛂 Lãnh sự trả hồ sơ: {why}. Phí {how} không hoàn lại.', refused=True)
    b['stats']['visas'] += 1
    b['visa'][co['id']] = s['journey']['life_day'] + co['days'] - 1
    return dict(message=f'🛂 Visa {co["name"]} được duyệt, dùng {co["days"]} ngày ({how}).')


def _trip(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'country', 'cls', 'confirm'}, {'country', 'cls'})
    co = _country(p)
    cl = CLASS.get(p['cls']) if isinstance(p['cls'], str) else None
    need(cl is not None, 'Chọn hạng vé nhé.')
    need(visa_left(s, co['id']) > 0, f'Cần visa {co["name"]} trước.', 'no_visa')
    need('trip' not in _today(s), 'Hôm nay vừa đi một chuyến. Mai đi tiếp nhé.', 'already_done')
    price = trip_price(co['id'], cl['id'])
    _confirm(p, f'đi {co["name"]} hạng {cl["name"].lower()} {_fmt(price)} xu')
    _pay_ok(s, price)
    how = _take(s, price, f'Du lịch {co["name"]} · {cl["name"]}')
    b = _ensure(s)
    day = s['journey']['life_day']
    b['today'] += ['trip', f'in_{co["id"]}']
    b['trips'][co['id']] = b['trips'].get(co['id'], 0) + 1
    b['stats']['trips'] += 1
    b['stats']['xu'] += price
    _album(b, 'trip', co['id'], cl['id'], day, b['trips'][co['id']])
    got = _spirit(s, C.TRIP_SPIRIT)
    lines = [_pick(s, co['id'], C.TRIP_LINES[co['id']])]
    if b['course'].get(co['lang'], 0) >= COURSE[co['lang']]['lessons']:
        lines.append('🗣️ Bạn nói chuyện được với người bản xứ, được chỉ quán ngon.')
    return dict(message=f'{co["flag"]} {co["name"]}, hạng {cl["name"].lower()} ({how}). Đóng dấu hộ chiếu.'
                + (f' Tinh thần +{got}.' if got else ''), effects=lines)


def _souv(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'id'}, {'id'})
    x = SOUV.get(p['id']) if isinstance(p['id'], str) else None
    need(x is not None, 'Chọn một món quà nhé.')
    cid, it = x
    need(f'in_{cid}' in _today(s), f'Quà này chỉ mua được khi đang ở {COUNTRY[cid]["name"]}.', 'locked')
    b = get(s)
    need(b['souv'].get(it['id'], 0) < C.SOUV_MAX, 'Mua đủ rồi.', 'limit')
    _pay_ok(s, it['price'])
    how = _take(s, it['price'], f'Quà lưu niệm · {it["name"]}')
    b = _ensure(s)
    b['souv'][it['id']] = b['souv'].get(it['id'], 0) + 1
    b['stats']['xu'] += it['price']
    return dict(message=f'{it["emoji"]} {it["name"]} ({how}).')


def _has_home(s: dict) -> bool:
    from . import housing
    b = get(s)
    return bool(housing.homes(s['journey'].get('home') or None)) or bool(b and any(i in ESTATE for i in b['own']))


def _party(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'kind', 'tier', 'guests', 'confirm'}, {'kind', 'tier', 'guests'})
    k = PARTY_KIND.get(p['kind']) if isinstance(p['kind'], str) else None
    t = PARTY_TIER.get(p['tier']) if isinstance(p['tier'], str) else None
    need(k is not None and t is not None, 'Chọn kiểu tiệc nhé.')
    g = p['guests']
    need(type(g) is int and C.GUESTS_MIN <= g <= C.GUESTS_MAX and g % C.GUESTS_STEP == 0, 'Số khách không hợp lệ.')
    need(not k.get('home') or _has_home(s), 'Tân gia cần một căn nhà của bạn.', 'locked')
    need('party' not in _today(s), 'Hôm nay vừa mở tiệc. Mai nhé.', 'already_done')
    price = party_price(t['id'], g)
    _confirm(p, f'mở tiệc {k["name"].lower()} {_fmt(price)} xu')
    _pay_ok(s, price)
    how = _take(s, price, f'Tiệc {k["name"].lower()} · {t["name"]} · {g} khách')
    b = _ensure(s)
    b['today'].append('party')
    b['stats']['parties'] += 1
    b['stats']['xu'] += price
    _album(b, 'party', k['id'], t['id'], s['journey']['life_day'], g)
    got = _spirit(s, C.PARTY_SPIRIT)
    return dict(message=f'{k["emoji"]} Tiệc {k["name"].lower()} {t["name"].lower()}, {g} khách ({how}).'
                + (f' Tinh thần +{got}.' if got else ''))


def _course(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'id', 'confirm'}, {'id'})
    c = COURSE.get(p['id']) if isinstance(p['id'], str) else None
    need(c is not None, 'Chọn một khóa học nhé.')
    b = get(s)
    need(not b or c['id'] not in b['course'], 'Bạn đã đăng ký khóa này rồi.', 'already_done')
    _confirm(p, f'đăng ký {c["name"]} {_fmt(c["price"])} xu')
    _pay_ok(s, c['price'])
    how = _take(s, c['price'], f'Học phí · {c["name"]}', 'study')
    b = _ensure(s)
    b['course'][c['id']] = 0
    b['stats']['xu'] += c['price']
    return dict(message=f'{c["emoji"]} Đăng ký {c["name"]} ({how}). {c["lessons"]} buổi, mỗi ngày một buổi.')


def _study(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'id'}, {'id'})
    c = COURSE.get(p['id']) if isinstance(p['id'], str) else None
    b = get(s)
    need(c is not None and b is not None and c['id'] in b['course'], 'Đăng ký khóa học trước nhé.', 'locked')
    need(b['course'][c['id']] < c['lessons'], 'Khóa này học xong rồi.', 'already_done')
    need(f'st_{c["id"]}' not in _today(s), 'Hôm nay học buổi này rồi. Mai học tiếp.', 'already_done')
    b = _ensure(s)
    b['today'].append(f'st_{c["id"]}')
    b['course'][c['id']] += 1
    b['stats']['lessons'] += 1
    n = b['course'][c['id']]
    return dict(message=f'{c["emoji"]} Buổi {n}/{c["lessons"]}.' + (' Tốt nghiệp!' if n >= c['lessons'] else ''))


def give_price(g: dict, p: dict) -> int:
    if 'sizes' in g:
        z = next((x for x in g['sizes'] if x['id'] == p.get('size')), None)
        _core().need(z is not None, 'Chọn cỡ pháo hoa nhé.')
        return z['price']
    if 'min' in g:
        return _core().integer(p.get('amount'), g['min'], g['max'])
    return g['price']


def _give(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'kind', 'size', 'slot', 'amount', 'msg', 'anon', 'confirm'}, {'kind'})
    g = GIVE.get(p['kind']) if isinstance(p['kind'], str) else None
    need(g is not None, 'Chọn một cách tài trợ nhé.')
    price = give_price(g, p)
    anon = p.get('anon', False)
    need(type(anon) is bool, 'Thông tin không hợp lệ.')
    slot, msg = 0, ''
    if 'slots' in g:
        slot, msg = p.get('slot'), p.get('msg')
        need(type(slot) is int and 1 <= slot <= g['slots'], 'Chọn một chỗ nhé.')
        need(isinstance(msg, str) and msg in DEDICATION, 'Chọn lời khắc nhé.')
    elif g['id'] == 'phao_hoa' and p.get('msg') not in (None, ''):   # 🎆 an optional wish shown with the show
        msg = p['msg']
        need(isinstance(msg, str) and msg in FW_WISH, 'Chọn lời chúc nhé.')
    _confirm(p, f'{g["name"].lower()} {_fmt(price)} xu')
    _pay_ok(s, price)
    how = _take(s, price, f'{g["name"]}' + (f' số {slot}' if slot else ''))
    b = _ensure(s)
    gv = b['give']
    gv['n'] += 1
    gv['sum'] += price
    if g['id'] == 'thu_vien':
        gv['lib'] += price
    if g['id'] == 'phao_hoa':
        gv['fw'] += 1
    gv['last'] = dict(n=gv['n'], k=g['id'], z=p.get('size') or '', s=slot, a=price, m=msg, anon=anon, wk=week_key(),
                      at=int(now()))
    b['stats']['xu'] += price
    _album(b, 'give', g['id'], p.get('size') or '', s['journey']['life_day'], price)
    where = f' Ghế/cột số {slot}, {g["where"]}: “{DEDICATION[msg]}”.' if slot else ''
    if g['id'] == 'phao_hoa':
        z = next(z for z in g['sizes'] if z['id'] == p['size'])
        return dict(message=f'🎆 {z["name"]} lên trời rồi, cả phố cùng xem! ({how})')
    return dict(message=f'{g["emoji"]} {g["name"]} ({how}).{where} Cả phố cảm ơn bạn!')


def _live(s: dict, p: dict) -> dict:
    """🏰 Dọn về dinh thự (id) or back home (None): the furniture goes to the bag, as on every move (game/deco.py)."""
    need = _core().need
    _keys(p, {'id'})
    eid = p.get('id')
    b = get(s)
    if eid is None:
        need(b is not None and b['live'], 'Bạn đang không ở dinh thự.', 'already_done')
        b['live'] = None
        return dict(message='Dọn về nhà cũ. Đồ trang trí đã gói vào túi.')
    e = ESTATE.get(eid) if isinstance(eid, str) else None
    need(e is not None and b is not None and eid in b['own'], 'Bạn chưa có dinh thự này.', 'not_owned')
    need(b['live'] != eid, f'Bạn đang ở {e["name"]} rồi.', 'already_done')
    b = _ensure(s)
    b['live'] = eid
    return dict(message=f'{e["emoji"]} Dọn về {e["name"]}. Vào nhà bày trí từng phòng nhé!')


_ACTIONS = dict(jr_lux_live=_live, jr_lux_buy=_buy, jr_lux_sell=_sell, jr_lux_open=_open, jr_lux_use=_use, jr_lux_photo=_photo,
                jr_lux_insure=_insure, jr_lux_visa=_visa, jr_lux_trip=_trip, jr_lux_souv=_souv, jr_lux_party=_party,
                jr_lux_course=_course, jr_lux_study=_study, jr_lux_give=_give)


# ---------------------------------------------------------------- views
def public(s: dict) -> dict:
    """Small (it rides on every state): money reasons are the client's (wallet, bank balance, prices); the server says
    what only it knows: visas, caps used today, the interview questions of the next US application, the bills."""
    j = s['journey']
    b = get(s)
    out = dict(story=bool(j.get('story')), ask=asked(s, 'my'), month=monthly(s), next=(j['life_day'] // bk.MONTH_DAYS + 1) * bk.MONTH_DAYS)
    if b:
        out.update(own={i: dict(p=x['p'], sell=sell_price(x['p']), m=month_of(i, x['p'])) for i, x in b['own'].items() if i in GOODS},
                   live=es.living_in(s['journey']), visa={c: visa_left(s, c) for c in b['visa'] if c in COUNTRY and visa_left(s, c)}, photo=b['photo'], ins=b['ins'],
                   trips={c: n for c, n in b['trips'].items() if c in COUNTRY}, souv={i: n for i, n in b['souv'].items() if i in SOUV},
                   course={c: n for c, n in b['course'].items() if c in COURSE}, today=_today(s), album=b['album'][-12:],
                   give=dict(n=b['give']['n'], sum=b['give']['sum'], lib=b['give']['lib']),
                   due=(b['upk']['acc'] // 1000) if b['upk'] else 0, paid=b['upk']['paid'] if b['upk'] else 0)
    return out


def show_view(s: dict) -> dict | None:
    """The player's card (game/social.py snapshot): the dearest asset, the dearest piece, how many pieces, countries."""
    b = get(s)
    if not b:
        return None
    assets = sorted((i for i in b['own'] if i in ASSET or i in ESTATE), key=lambda i: -GOODS[i]['price'])
    pieces = sorted((i for i in b['own'] if i in PIECE), key=lambda i: -PIECE[i]['price'])
    countries = sum(1 for c, n in b['trips'].items() if c in COUNTRY and n)
    if not assets and not pieces and not countries:
        return None
    out = dict(n=len(pieces), c=countries)
    if assets:
        out['a'] = dict(e=GOODS[assets[0]]['emoji'], name=GOODS[assets[0]]['name'])
    if pieces:
        out['p'] = dict(e=PIECE[pieces[0]]['emoji'], name=PIECE[pieces[0]]['name'], r=PIECE[pieces[0]]['rare'])
    return out


def worth(j: dict) -> int:
    """What the 💰 board counts for this block: every asset and piece at its buy-back price (game/wealth.py)."""
    b = j.get(KEY) if isinstance(j, dict) else None
    own = b.get('own') if isinstance(b, dict) else None
    if not isinstance(own, dict):
        return 0
    return sum(sell_price(x['p']) for i, x in own.items() if i in GOODS and isinstance(x, dict) and _int(x.get('p'), 1, 10**8))


def catalogue() -> dict:
    """Static lists for the client (bootstrap content, cached)."""
    return dict(countries=[dict(c) for c in C.COUNTRIES], classes=[dict(c) for c in C.CLASSES], docs=[dict(d) for d in C.DOCS],
                photo=dict(price=C.PHOTO_PRICE, days=C.PHOTO_DAYS), work_days=C.WORK_DAYS, insure_pct=C.INSURE_PCT,
                interview=[dict(q=x['q'], a=list(x['a'])) for x in C.INTERVIEW],
                souvenirs={k: [dict(x) for x in v] for k, v in C.SOUVENIRS.items()},
                sets=[dict(id=st['id'], emoji=st['emoji'], name=st['name'], items=[dict(x) for x in st['items']]) for st in C.SETS],
                wine=C.WINE_SET, insure_from=C.INSURE_FROM, insure_bp=C.INSURE_BP, assets=[dict(a) for a in C.ASSETS],
                sell_pct=C.SELL_PCT, party_kinds=[dict(k) for k in C.PARTY_KINDS], party_tiers=[dict(t) for t in C.PARTY_TIERS],
                guests=dict(min=C.GUESTS_MIN, max=C.GUESTS_MAX, step=C.GUESTS_STEP), courses=[dict(c) for c in C.COURSES],
                gives=[dict(g, sizes=[dict(z) for z in g.get('sizes', ())]) for g in C.GIVES],
                dedications=[dict(id=k, text=v) for k, v in C.DEDICATIONS], fw_wishes=[dict(id=k, text=v) for k, v in C.FW_WISHES],
                month_days=bk.MONTH_DAYS, **es.catalogue())


# ---------------------------------------------------------------- database (the save's own transaction)
def _pid(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


GUEST_NAME = 'Một người hàng xóm'
ANON_NAME = 'Một người hàng xóm giấu tên'


def _display(db, sid: str, anon: bool) -> str:
    if anon:
        return ANON_NAME
    r = db.execute('SELECT display FROM accounts WHERE sid=?', (sid,)).fetchone()
    return str(r['display'])[:24] if r and r['display'] else GUEST_NAME


def _news(db, ref: str, text: str, force: bool = False) -> None:
    """A line on the street's ticker (game/marriage.py news, GET /api/news): one every NEWS_GAP seconds at most."""
    from . import marriage
    if not force:
        r = db.execute("SELECT MAX(at) AS at FROM news WHERE kind='lux'").fetchone()
        if r and r['at'] is not None and now() - float(r['at']) < C.NEWS_GAP:
            return
    marriage._post_news(db, 'lux', ref, text, '', '')


def _town_chat(db, text: str) -> None:
    """🎆 A line on Cả phố from the street itself (pid 'admin', like an operator's announcement), delivered at once by the
    live service's existing 'unhide' event (it loads the row by id and sends it to everyone on Cả phố)."""
    from . import live_chat
    r = db.execute("INSERT INTO chat_messages(channel, pid, name, av, text, at, adm) VALUES('town', 'admin', ?, '🎆', ?, ?, 1) "
                   'RETURNING id', ('🎆 Pháo hoa phố', text[:300], now())).fetchone()
    if r:
        live_chat.notify(db, dict(op='unhide', id=int(r['id'])))


def _show(db, rid: str, pid: str, size: str, who: str, wish: str, at) -> None:
    """🎆 The show itself on every open screen (live/fireworks.py): bursts over the page and a long banner with the name
    and the wish. Sent on commit (NOTIFY), so a refused command shows nothing. `pid` lets the live service leave the
    name and the wish out for players who blocked the giver (or were blocked); it never reaches a page. An older live
    service ignores the op."""
    from . import live_chat
    live_chat.notify(db, dict(op='fireworks', id=rid, pid=pid, size=size, name=who, wish=wish, at=float(at)))


def command_commit(db, sid: str, action: str, after: dict) -> None:
    """Called by the storage layer for jr_lux_* commands, in the save's transaction (game/storage.py). A GameError here
    rolls the whole command back (nothing paid): a numbered plaque already taken, fireworks too soon after the last."""
    if action not in ('jr_lux_give', 'jr_lux_party'):
        return
    e = _core()
    b = get(after)
    if not b:
        return
    pid = _pid(sid)
    if action == 'jr_lux_party':
        x = b['album'][-1] if b['album'] else None
        t = PARTY_TIER.get(x['c']) if x and x['k'] == 'party' else None
        if t and t.get('news'):
            k = PARTY_KIND[x['i']]
            _news(db, f'luxp:{pid}:{b["stats"]["parties"]}',
                  f'🎉 {_display(db, sid, False)} mở tiệc {k["name"].lower()} {t["name"].lower()}, {x["n"]} khách!')
        return
    x = b['give']['last']
    if not x:
        return
    g = GIVE[x['k']]
    rid = f'{pid}:{x["n"]}'
    slot = f'{x["k"]}:{x["s"]}' if x['s'] else ''
    if g['id'] == 'phao_hoa':
        db.execute('SELECT pg_advisory_xact_lock(17823, 1)')
        r = db.execute("SELECT MAX(at) AS at FROM lux_gifts WHERE kind='phao_hoa'").fetchone()
        wait = int(g['gap'] - (now() - float(r['at']))) if r and r['at'] is not None else 0
        e.need(wait <= 0, f'Trời đang có pháo hoa. Đợi {max(1, -(-wait // 60))} phút nữa nhé.', 'busy')
    r = db.execute('INSERT INTO lux_gifts(id, sid, week, kind, slot, size, amount, msg, anon, at) VALUES(?,?,?,?,?,?,?,?,?,?) '
                   'ON CONFLICT DO NOTHING RETURNING id',
                   (rid, sid, x['wk'], x['k'], slot, x['z'], x['a'], x['m'], 1 if x['anon'] else 0, float(x['at']))).fetchone()
    if not r:
        held = db.execute('SELECT id FROM lux_gifts WHERE slot=? AND slot<>\'\'', (slot,)).fetchone() if slot else None
        e.need(not held or held['id'] == rid, 'Chỗ này vừa có người khắc tên. Chọn chỗ khác nhé.', 'taken')
        return
    _BOARD.clear()
    who = _display(db, sid, x['anon'])
    if g['id'] == 'phao_hoa':
        z = next(z for z in g['sizes'] if z['id'] == x['z'])
        wish = FW_WISH.get(x['m'], '')
        text = f'🎆 {who} bắn {z["name"].lower()} tặng cả phố!' + (f' “{wish}”' if wish else '')
        _news(db, f'lux:{rid}', text, force=True)
        _town_chat(db, text + ' Ngước lên trời nào 🎇')
        _show(db, rid, pid, z['id'], who, wish, x['at'])
    elif 'slots' in g:
        _news(db, f'lux:{rid}', f'{g["emoji"]} {who} khắc tên {g["name"].split()[0].lower()} số {x["s"]} ({g["where"]}): “{DEDICATION.get(x["m"], "")}”.')
    elif g.get('week'):
        _news(db, f'lux:{rid}', f'{g["emoji"]} {who} {g["name"].lower()} tuần này!')
    elif x['a'] >= 200000:
        _news(db, f'lux:{rid}', f'{g["emoji"]} {who} góp {_fmt(x["a"])} xu cho {g["name"].lower()}.')


def forget(db, sid: str) -> None:
    """A player erased their data: their gifts stay (plaques, the board) as anonymous."""
    db.execute("UPDATE lux_gifts SET sid='', anon=1 WHERE sid=?", (sid,))
    _BOARD.clear()


# ---------------------------------------------------------------- 🎆 Bảng Mạnh Thường Quân (GET /api/mtq)
BOARD_TOP = 10
BOARD_SECS = 10.0
_BOARD: dict = {}          # week key -> (at, rows): one entry, bounded
_LOCK = threading.Lock()


def _name(r) -> str:
    return ANON_NAME if r['anon'] else (str(r['display'])[:24] if r['display'] else GUEST_NAME)


def _board_rows(store, wk: str) -> dict:
    with _LOCK:
        hit = _BOARD.get(wk)
        if hit and time.monotonic() - hit[0] < BOARD_SECS:
            return hit[1]
    join = 'FROM lux_gifts g LEFT JOIN accounts a ON a.sid=g.sid AND g.anon=0'
    with store.connect() as db:
        top = db.execute(f'SELECT g.sid AS sid, g.anon AS anon, SUM(g.amount) AS xu, MIN(g.at) AS first, a.display AS display {join} '
                         'WHERE g.week=? GROUP BY g.sid, g.anon, a.display ORDER BY xu DESC, first ASC LIMIT ?', (wk, BOARD_TOP)).fetchall()
        tot = db.execute('SELECT COALESCE(SUM(amount), 0) AS xu, COUNT(DISTINCT sid) AS people FROM lux_gifts WHERE week=?', (wk,)).fetchone()
        banners = {}
        for k in ('hoi_cho', 'zpop'):
            r = db.execute(f'SELECT g.anon AS anon, a.display AS display, SUM(g.amount) AS xu, MIN(g.at) AS first {join} '
                           'WHERE g.week=? AND g.kind=? GROUP BY g.sid, g.anon, a.display ORDER BY xu DESC, first ASC LIMIT 1', (wk, k)).fetchone()
            if r:
                banners[k] = _name(r)
        lib = db.execute(f'SELECT g.anon AS anon, a.display AS display, SUM(g.amount) AS xu, MIN(g.at) AS first {join} '
                         "WHERE g.kind='thu_vien' GROUP BY g.sid, g.anon, a.display ORDER BY xu DESC, first ASC LIMIT 1").fetchone()
        libsum = db.execute("SELECT COALESCE(SUM(amount), 0) AS xu FROM lux_gifts WHERE kind='thu_vien'").fetchone()
        plaques = db.execute(f"SELECT g.kind AS kind, g.slot AS slot, g.msg AS msg, g.anon AS anon, a.display AS display {join} "
                             "WHERE g.slot<>'' ORDER BY g.at").fetchall()
        fw = db.execute("SELECT MAX(at) AS at FROM lux_gifts WHERE kind='phao_hoa'").fetchone()
    out = dict(top=[dict(sid=r['sid'], name=_name(r), xu=int(r['xu'])) for r in top], xu=int(tot['xu']), people=int(tot['people']),
               banners=banners, library=dict(name=_name(lib) if lib else '', xu=int(libsum['xu'])),
               plaques=[dict(k=r['kind'], s=int(str(r['slot']).rsplit(':', 1)[-1]), name=_name(r), msg=DEDICATION.get(r['msg'], ''))
                        for r in plaques], fw_at=float(fw['at']) if fw and fw['at'] is not None else 0.0)
    with _LOCK:
        _BOARD.clear()
        _BOARD[wk] = (time.monotonic(), out)
    return out


def board(store, token: str | None) -> dict:
    """This week's Mạnh Thường Quân board, this week's banners, the library's top giver, every plaque, when the next
    fireworks may go up, and mine."""
    wk = week_key()
    rows = _board_rows(store, wk)
    sid = store.key(token) if isinstance(token, str) and 16 <= len(token) <= 128 else None
    mine = 0
    if sid:
        with store.connect() as db:
            r = db.execute('SELECT COALESCE(SUM(amount), 0) AS xu FROM lux_gifts WHERE week=? AND sid=?', (wk, sid)).fetchone()
            mine = int(r['xu'])
    gap = GIVE['phao_hoa']['gap']
    return dict(week=wk, top=[dict(name=x['name'], xu=x['xu'], me=bool(sid) and x['sid'] == sid) for x in rows['top']],
                xu=rows['xu'], people=rows['people'], banners=rows['banners'], library=rows['library'], plaques=rows['plaques'],
                fw_wait=max(0, int(rows['fw_at'] + gap - now())) if rows['fw_at'] else 0, mine=mine)
