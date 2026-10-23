"""✈️ Du lịch trải nghiệm (story mode): book a flight, fly with a cabin crew, visit a new place, fly home.

Feedback #464 (owner OK 23/10, "du lịch trải nghiệm thật"): the old trip (game/lux.py jr_lux_trip) was one tap and a
line. This one is a short journey in four steps, every money move here, the client only draws it (public/js/v4/travel.js):

1. 🎫 Đặt vé (jr_trip_book {to, cls, day, confirm}): one of C.DESTS (five in Việt Nam, seven abroad), economy or
   business, a departure life day from today to today + C.MAX_AHEAD. The fare depends on how far ahead it is booked
   (C.AHEAD_PCT: flying today costs twice the best fare, C.GOOD_AHEAD+ days ahead is the best fare). A place abroad
   that needs a visa wants the game/lux.py visa valid on the departure day (the consulate's paperwork stays there).
   Paid from the wallet, then the bank account (game/lux.py _take; never with the wallet in debt). One ticket at a
   time, never while travelling. Cancel (jr_trip_cancel {confirm}): C.REFUND_EARLY % back before the flight's life day,
   C.REFUND_LATE % on the day. A flight missed (its life day passed) is refunded C.REFUND_LATE % by itself.
2. 🛫 Bay (jr_trip_board on the departure life day; jr_trip_meal {food, drink} once per leg, the crew's menu of the
   class, included in the ticket; jr_trip_land): landing stamps the passport (stamps), tinh thần, the place's greeting.
   A place with a game/lux.py country also counts as a lux trip there (titles, album, its souvenir shop that day).
3. 🗺️ Tham quan (jr_trip_spot {id}, jr_trip_buy {id}): each spot once per trip, a small fee, tinh thần, a postcard
   kept for good (cards); dishes fill bụng, rests wake you up (game/needs.py bars). Souvenirs of the place.
4. 🏠 Về (jr_trip_home, a meal again, jr_trip_land): the trip summary goes to the log. A trip still open C.STAY_DAYS
   life days after it left flies home by itself (on_life_day, after every command like the other mornings).

Nothing here pays xu except refunds of what was paid (never more). No penalty beyond a missed flight's half fare.

State journey['travel'] (absent until the first booking; journey.validate allows extra keys, so an older build keeps it
untouched, and keys a newer build adds to this block are kept too):
    v       VERSION
    book    None | {to, cls, day: the departure life day, at: the life day it was booked, paid}
    trip    None | {to, cls, day: the life day it left, ph: fly | here | back, meal: '' | 'food:drink' (this leg),
                    seen: [spot ids this trip], xu: spent there, sp: tinh thần gained}
    stamps  {place id: trips}        cards  [spot ids ever visited: the postcards]      souv  {souvenir id: copies}
    log     [{to, cls, d, n: spots, sp, xu}] newest last, ≤ C.LOG_MAX
    stats   {trips, xu, back, spots}
Wallet rows use the existing kind 'life' (journey.HISTORY_KINDS is a closed list older builds validate).
"""
from __future__ import annotations

import hashlib
import re

from . import lux as lx
from . import price_index as pi
from . import travel_content as C

VERSION = 1
KEY = 'travel'
KIND = 'life'
KEYS = frozenset({'v', 'book', 'trip', 'stamps', 'cards', 'souv', 'log', 'stats'})
BOOK_KEYS = frozenset({'to', 'cls', 'day', 'at', 'paid'})
TRIP_KEYS = frozenset({'to', 'cls', 'day', 'ph', 'meal', 'seen', 'xu', 'sp'})
LOG_KEYS = frozenset({'to', 'cls', 'd', 'n', 'sp', 'xu'})
STATS = ('trips', 'xu', 'back', 'spots')
PHASES = ('fly', 'here', 'back')
COMMANDS = ('jr_trip_book', 'jr_trip_cancel', 'jr_trip_board', 'jr_trip_meal', 'jr_trip_land', 'jr_trip_spot',
            'jr_trip_buy', 'jr_trip_home')
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
MEAL_RE = re.compile(r'[a-z0-9_]{1,24}:[a-z0-9_]{1,24}')
BIG = 10**12
CARDS_MAX = 400


def _index(base: int) -> int:
    return pi.price(base) if base > 0 else 0


# The catalogue with today's prices (game/price_index.py), built once.
DEST = {}
SPOT = {}       # spot id -> (place id, spot)
SOUV = {}       # souvenir id -> (place id, souvenir)
for _d in C.DESTS:
    _x = dict(_d, fare=_index(_d['base']), spots=tuple(dict(sp, fee=_index(sp['fee'])) for sp in _d['spots']),
              souv=tuple(dict(g, price=_index(g['price'])) for g in _d['souv']))
    DEST[_x['id']] = _x
    for _sp in _x['spots']:
        SPOT[_sp['id']] = (_x['id'], _sp)
    for _g in _x['souv']:
        SOUV[_g['id']] = (_x['id'], _g)
CLASS = {c['id']: c for c in C.CLASSES}
FOOD = {m['id']: m for m in C.MEALS['food']}
DRINK = {m['id']: m for m in C.MEALS['drink']}


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _fmt(n: int) -> str:
    return lx._fmt(n)


def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


def _id(v) -> bool:
    return isinstance(v, str) and ID_RE.fullmatch(v) is not None


def fare(to: str, cls: str, ahead: int) -> int:
    """The return ticket booked `ahead` life days before the flight (0 = today), rounded to 10 xu."""
    pct = C.AHEAD_PCT[max(0, min(C.MAX_AHEAD, int(ahead)))]
    raw = DEST[to]['fare'] * pct * CLASS[cls]['mult']        # in xu × 100
    return max(10, (raw + 500) // 1000 * 10)


def refund(book: dict, day: int) -> int:
    """What cancelling `book` on life day `day` gives back."""
    pct = C.REFUND_EARLY if book['day'] > day else C.REFUND_LATE
    return int(book['paid']) * pct // 100


def initial() -> dict:
    return dict(v=VERSION, book=None, trip=None, stamps={}, cards=[], souv={}, log=[], stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial()
    return j[KEY]


def _name(to: str) -> str:
    d = DEST.get(to)
    return f'{d["flag"]} {d["name"]}' if d else '✈️ chuyến đi'


def _visa_until(s: dict, d: dict) -> int:
    """The last life day the game/lux.py visa this place needs is valid (BIG: none needed, 0: none held)."""
    if not d['visa']:
        return BIG
    b = lx.get(s)
    return int(b['visa'].get(d['visa'], 0)) if b else 0


def _visa_name(d: dict) -> str:
    co = lx.COUNTRY.get(d['visa'])
    return co['name'] if co else d['name']


def _spirit(s: dict, n: int) -> int:
    from . import needs
    return needs._spirit(s, n)


def _bar(s: dict, key: str, n: int) -> int:
    """Move a needs bar (game/needs.py: full | wake) by n within 0..100, when the save has the bars."""
    from . import needs
    nd = needs.get(s)
    if not nd or type(nd.get(key)) is not int or not n:
        return 0
    before = nd[key]
    nd[key] = max(0, min(100, before + n))
    return nd[key] - before


def _hash(s: dict, *parts) -> int:
    j = s['journey']
    return int.from_bytes(hashlib.sha256('|'.join(map(str, (j.get('seed', 0),) + parts)).encode()).digest()[:4], 'big')


def ticket(s: dict, to: str, cls: str, day: int) -> dict:
    """The boarding pass's flight code, seat and gate (drawn from the save's seed: the same ticket every time)."""
    h = _hash(s, 'tv', to, day)
    row = 1 + h % 4 if cls == 'biz' else 8 + h % 30
    letters = 'ACDF' if cls == 'biz' else 'ABCDEF'
    return dict(code=f'{C.FLIGHT_PREFIX}{100 + (h >> 8) % 900}', seat=f'{row}{letters[(h >> 4) % len(letters)]}', gate=1 + (h >> 16) % 24)


def _keys(p: dict, allowed: set, required: set = frozenset()) -> None:
    _core().need(isinstance(p, dict) and set(p) <= allowed and required <= set(p), 'Thông tin không hợp lệ.')


def _confirm(p: dict, what: str) -> None:
    _core().need(p.get('confirm') is True, f'Xác nhận {what}.')


def _pay(s: dict, amount: int, label: str) -> str:
    why = lx.ready_why(s, amount)
    _core().need(not why, why, 'not_enough')
    return lx._take(s, amount, label)


def _trip(s: dict, *phases) -> dict:
    b = get(s)
    t = b.get('trip') if b else None
    e = _core()
    if not phases:
        e.need(t is not None, 'Bạn đang không đi du lịch.', 'locked')
    elif t is None or t['ph'] not in phases:
        msg = {('fly', 'back'): 'Chỉ làm được khi đang trên máy bay.', ('here',): 'Chỉ làm được khi đang tham quan.'}
        e.need(False, msg.get(phases, 'Chưa tới bước này.'), 'locked')
    e.need(t['to'] in DEST and t['cls'] in CLASS, 'Chuyến đi này không còn trong lịch bay.', 'locked')
    return t


# ---------------------------------------------------------------- commands
def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    e.need(s['journey'].get('story'), 'Du lịch chỉ có trong hành trình.', 'locked')
    e.need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    return _ACTIONS[name](s, p)


def _book(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'to', 'cls', 'day', 'confirm'}, {'to', 'cls', 'day'})
    d = DEST.get(p['to']) if isinstance(p['to'], str) else None
    need(d is not None, 'Chọn một nơi muốn đến nhé.')
    cl = CLASS.get(p['cls']) if isinstance(p['cls'], str) else None
    need(cl is not None, 'Chọn hạng vé nhé.')
    day, today = p['day'], s['journey']['life_day']
    need(type(day) is int, 'Chọn ngày bay nhé.')
    need(day >= today, f'Ngày {day} qua rồi. Chọn từ hôm nay (Ngày {today}) nhé.', 'past')
    need(day <= today + C.MAX_AHEAD, f'Hãng chỉ mở bán trước tối đa {C.MAX_AHEAD} ngày.', 'too_far')
    b = get(s)
    need(not (b and b['trip']), 'Bạn đang trong một chuyến đi rồi.', 'already_done')
    if b and b['book']:
        x = b['book']
        need(False, f'Bạn đã có vé đi {_name(x["to"])} Ngày {x["day"]}. Hủy vé đó trước nếu muốn đổi.', 'already_done')
    need(_visa_until(s, d) >= day, f'Cần visa {_visa_name(d)} còn hạn tới ngày bay. Làm visa ở Đại lý vé nhé.', 'no_visa')
    ahead = day - today
    price = fare(d['id'], cl['id'], ahead)
    _confirm(p, f'mua vé khứ hồi {d["name"]} hạng {cl["name"].lower()} {_fmt(price)} xu')
    how = _pay(s, price, f'Vé máy bay {d["name"]} · {cl["name"]}')
    b = _ensure(s)
    b['book'] = dict(to=d['id'], cls=cl['id'], day=day, at=today, paid=price)
    b['stats']['xu'] += price
    when = 'bay hôm nay' if not ahead else f'bay Ngày {day} (còn {ahead} ngày)'
    tip = ' Đặt sớm nên được giá tốt!' if ahead >= C.GOOD_AHEAD else ''
    return dict(message=f'🎫 Đã đặt vé {_name(d["id"])}, {when}: {how}.{tip}', travel=dict(booked=d['id']))


def _cancel(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'confirm'})
    b = get(s)
    need(b is not None and b['book'] is not None, 'Bạn chưa có vé nào.', 'not_found')
    x, today = b['book'], s['journey']['life_day']
    back = refund(x, today)
    _confirm(p, f'hủy vé, nhận lại {_fmt(back)} xu')
    b['book'] = None
    if back:
        _jr()._wallet(s['journey'], back, KIND, f'Hoàn vé máy bay · {DEST[x["to"]]["name"] if x["to"] in DEST else x["to"]}'[:120])
    b['stats']['back'] += back
    return dict(message=f'Đã hủy vé {_name(x["to"])}. Hoàn {_fmt(back)} xu vào ví.')


def _board(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, set())
    b = get(s)
    need(b is not None and b['book'] is not None, 'Bạn chưa có vé. Đặt vé trước nhé.', 'not_found')
    need(not b['trip'], 'Bạn đang trong một chuyến đi rồi.', 'already_done')
    x, today = b['book'], s['journey']['life_day']
    need(x['to'] in DEST and x['cls'] in CLASS, 'Chuyến bay này không còn trong lịch bay.', 'locked')
    need(x['day'] <= today, f'Vé bay Ngày {x["day"]}. Còn {x["day"] - today} ngày nữa nhé.', 'not_yet')
    need(x['day'] == today, 'Chuyến bay này đã cất cánh mất rồi.', 'missed')
    d = DEST[x['to']]
    need(_visa_until(s, d) >= today, f'Visa {_visa_name(d)} hết hạn rồi.', 'no_visa')
    b['book'] = None
    b['trip'] = dict(to=x['to'], cls=x['cls'], day=today, ph='fly', meal='', seen=[], xu=0, sp=0)
    return dict(message=f'🛫 {C.AIRLINE} cất cánh đi {_name(d["id"])}. Thắt dây an toàn nhé!', effects=[C.CAPTAIN['up']],
                travel=dict(boarded=d['id']))


def _meal(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'food', 'drink'}, {'food', 'drink'})
    t = _trip(s, 'fly', 'back')
    need(not t['meal'], 'Bạn dùng bữa trên chuyến này rồi.', 'already_done')
    f = FOOD.get(p['food']) if isinstance(p['food'], str) else None
    dr = DRINK.get(p['drink']) if isinstance(p['drink'], str) else None
    need(f is not None and dr is not None, 'Chọn một món ăn và một đồ uống nhé.')
    need(t['cls'] == 'biz' or (f['cls'] == 'eco' and dr['cls'] == 'eco'), 'Món này chỉ phục vụ hạng thương gia.', 'locked')
    t['meal'] = f'{f["id"]}:{dr["id"]}'
    got = _spirit(s, C.MEAL_SPIRIT[t['cls']])
    t['sp'] += got
    _bar(s, 'full', C.MEAL_FULL)
    line = C.SERVE_LINES[_hash(s, 'serve', t['day'], t['ph']) % len(C.SERVE_LINES)]
    return dict(message=f'{f["emoji"]}{dr["emoji"]} {f["name"]} và {dr["name"].lower()}.' + (f' Tinh thần +{got}.' if got else ''),
                effects=[f'💁 {line}'])


def _land(s: dict, p: dict) -> dict:
    _keys(p, set())
    t = _trip(s, 'fly', 'back')
    b = get(s)
    d, cl = DEST[t['to']], CLASS[t['cls']]
    if t['ph'] == 'back':
        got = _spirit(s, C.HOME_SPIRIT)
        t['sp'] += got
        summary = _finish(b, t)
        return dict(message=f'🏠 Hạ cánh {C.HOME_AIRPORT}. Về nhà rồi, chuyến {d["name"]} thật đáng nhớ!',
                    travel=dict(summary=summary))
    t['ph'], t['meal'] = 'here', ''
    b['stamps'][d['id']] = b['stamps'].get(d['id'], 0) + 1
    b['stats']['trips'] += 1
    got = _spirit(s, C.LAND_SPIRIT[cl['id']])
    t['sp'] += got
    if cl['id'] == 'biz':
        _bar(s, 'wake', C.BIZ_WAKE)
    titles = _lux_trip(s, d, cl)
    msg = f'🛬 Hạ cánh {d["airport"]}. Đóng dấu hộ chiếu {d["flag"]}!' + (f' Tinh thần +{got}.' if got else '')
    if titles:
        msg += ' 🏷️ Danh hiệu mới: ' + ', '.join(titles) + ' (đeo ở Phong cách).'
    return dict(message=msg, effects=[d['greet']], travel=dict(stamp=d['id'], first=b['stamps'][d['id']] == 1))


def _lux_trip(s: dict, d: dict, cl: dict) -> list[str]:
    """A place with a game/lux.py country counts as a lux trip there: the countries for titles, the album, and that
    country's souvenir shop for the day (lux `in_<country>`). The new titles' names."""
    cid = d['visa']
    if not cid or cid not in lx.COUNTRY:
        return []
    b = lx._ensure(s)
    day = s['journey']['life_day']
    b['trips'][cid] = min(10**9, b['trips'].get(cid, 0) + 1)
    b['stats']['trips'] += 1
    if f'in_{cid}' not in b['today'] and len(b['today']) < lx.TODAY_MAX:
        b['today'].append(f'in_{cid}')
    lx._album(b, 'trip', cid, cl['lux'], day, b['trips'][cid])
    return lx._award(s)


def _finish(b: dict, t: dict) -> dict:
    """The trip ends: a line in the log, the summary shown."""
    row = dict(to=t['to'], cls=t['cls'], d=t['day'], n=len(t['seen']), sp=t['sp'], xu=t['xu'])
    b['log'] = (b['log'] + [row])[-C.LOG_MAX:]
    b['trip'] = None
    return dict(row, cards=sum(1 for x in b['cards'] if SPOT.get(x, ('',))[0] == t['to']),
                of=len(DEST[t['to']]['spots']) if t['to'] in DEST else 0)


def _spot(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'id'}, {'id'})
    t = _trip(s, 'here')
    x = SPOT.get(p['id']) if isinstance(p['id'], str) else None
    need(x is not None and x[0] == t['to'], 'Chỗ này không ở nơi bạn đang đến.')
    sp = x[1]
    need(sp['id'] not in t['seen'], f'Bạn ghé {sp["name"]} rồi. Đi chỗ khác nhé.', 'already_done')
    how = _pay(s, sp['fee'], f'Tham quan · {sp["name"]}') if sp['fee'] else ''
    b = get(s)
    t['xu'] += sp['fee']
    b['stats']['xu'] += sp['fee']
    t['seen'].append(sp['id'])
    b['stats']['spots'] += 1
    new = sp['id'] not in b['cards']
    if new and len(b['cards']) < CARDS_MAX:
        b['cards'].append(sp['id'])
    got = _spirit(s, sp['sp'])
    t['sp'] += got
    if sp['kind'] == 'food':
        _bar(s, 'full', C.FOOD_FULL)
    elif sp['kind'] == 'rest':
        _bar(s, 'wake', C.REST_WAKE)
    msg = f'{sp["emoji"]} {sp["name"]}' + (f' ({how})' if how else '') + '.' + (f' Tinh thần +{got}.' if got else '')
    if new:
        msg += ' 💌 Bưu thiếp mới!'
    return dict(message=msg, effects=[sp['line']], travel=dict(card=sp['id'], new=new))


def _buy(s: dict, p: dict) -> dict:
    need = _core().need
    _keys(p, {'id'}, {'id'})
    x = SOUV.get(p['id']) if isinstance(p['id'], str) else None
    need(x is not None, 'Chọn một món quà nhé.')
    to, g = x
    b = get(s)
    t = b.get('trip') if b else None
    need(t is not None and t['ph'] == 'here' and t['to'] == to, f'Quà này chỉ mua được khi đang ở {DEST[to]["name"]}.', 'locked')
    need(b['souv'].get(g['id'], 0) < C.SOUV_MAX, 'Mua đủ rồi.', 'limit')
    how = _pay(s, g['price'], f'Quà lưu niệm · {g["name"]}')
    b['souv'][g['id']] = b['souv'].get(g['id'], 0) + 1
    t['xu'] += g['price']
    b['stats']['xu'] += g['price']
    return dict(message=f'{g["emoji"]} {g["name"]} ({how}). Cất vào vali rồi!', travel=dict(souv=g['id']))


def _home(s: dict, p: dict) -> dict:
    _keys(p, set())
    t = _trip(s, 'here')
    t['ph'], t['meal'] = 'back', ''
    return dict(message=f'🛫 Tạm biệt {DEST[t["to"]]["name"]}! Lên chuyến bay về nhà.', effects=[C.CAPTAIN['up']])


_ACTIONS = dict(jr_trip_book=_book, jr_trip_cancel=_cancel, jr_trip_board=_board, jr_trip_meal=_meal, jr_trip_land=_land,
                jr_trip_spot=_spot, jr_trip_buy=_buy, jr_trip_home=_home)


# ---------------------------------------------------------------- the life-day morning
def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """A missed flight is refunded C.REFUND_LATE %; a trip left open C.STAY_DAYS life days flies home. Idempotent (after
    every command, like game/lux.py on_life_day)."""
    j = s.get('journey')
    b = get(s)
    if not isinstance(j, dict) or not j.get('story') or not b:
        return []
    today = int(j['life_day'])
    notes = []
    x = b.get('book')
    if isinstance(x, dict) and x['day'] < today:
        back = refund(x, today)
        b['book'] = None
        if back:
            _jr()._wallet(j, back, KIND, f'Hoàn vé lỡ chuyến · {DEST[x["to"]]["name"] if x["to"] in DEST else x["to"]}'[:120])
        b['stats']['back'] += back
        notes.append(f'🎫 Bạn lỡ chuyến bay đi {_name(x["to"])} Ngày {x["day"]}. Hãng hoàn {C.REFUND_LATE}% ({_fmt(back)} xu) vào ví.')
    t = b.get('trip')
    if isinstance(t, dict) and today > t['day'] + C.STAY_DAYS:
        _finish(b, t)
        notes.append(f'🏠 Chuyến đi {_name(t["to"])} khép lại, bạn đã bay về nhà. Xem lại ở Sổ du lịch nhé.')
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- views
def public(s: dict) -> dict | None:
    """Small (it rides on every state)."""
    j = s.get('journey')
    if not isinstance(j, dict) or not j.get('story'):
        return None
    b = get(s) or initial()
    today = int(j['life_day'])
    out = dict(stamps={k: v for k, v in b['stamps'].items() if k in DEST}, cards=[c for c in b['cards'] if c in SPOT],
               souv={k: v for k, v in b['souv'].items() if k in SOUV}, log=[dict(r) for r in b['log'] if r.get('to') in DEST][-6:],
               trips=b['stats'].get('trips', 0))
    x = b['book']
    if x and x['to'] in DEST and x['cls'] in CLASS:
        out['book'] = dict(to=x['to'], cls=x['cls'], day=x['day'], paid=x['paid'], left=x['day'] - today, back=refund(x, today),
                           **ticket(s, x['to'], x['cls'], x['day']))
    t = b['trip']
    if t and t['to'] in DEST and t['cls'] in CLASS:
        out['trip'] = dict(to=t['to'], cls=t['cls'], day=t['day'], ph=t['ph'], meal=bool(t['meal']), seen=list(t['seen']),
                           xu=t['xu'], sp=t['sp'], **ticket(s, t['to'], t['cls'], t['day']))
    lb = lx.get(s)
    if lb:
        out['visa'] = {d['id']: lb['visa'][d['visa']] for d in DEST.values()
                       if d['visa'] and lb['visa'].get(d['visa'], 0) >= today}
    return out


def catalogue() -> dict:
    """Static lists for the client (bootstrap content, cached)."""
    dests = []
    for d in DEST.values():
        dests.append(dict({k: d[k] for k in ('id', 'kind', 'flag', 'name', 'area', 'airport', 'fly', 'visa', 'sky', 'land', 'accent',
                                              'skyline', 'tag', 'greet')},
                          visa_name=_visa_name(d) if d['visa'] else '',
                          fares={c: [fare(d['id'], c, a) for a in range(C.MAX_AHEAD + 1)] for c in CLASS},
                          spots=[dict(sp) for sp in d['spots']], souv=[dict(g) for g in d['souv']]))
    return dict(dests=dests, classes=[dict(c) for c in C.CLASSES], ahead=list(C.AHEAD_PCT), max_ahead=C.MAX_AHEAD,
                good_ahead=C.GOOD_AHEAD, refund_early=C.REFUND_EARLY, refund_late=C.REFUND_LATE, stay=C.STAY_DAYS,
                meals={k: [dict(m) for m in v] for k, v in C.MEALS.items()}, crew=[dict(x) for x in C.CREW],
                captain=dict(C.CAPTAIN), kinds={k: dict(v) for k, v in C.KINDS.items()}, home=C.HOME_AIRPORT,
                airline=C.AIRLINE)


# ---------------------------------------------------------------- save
def _counts(d, hi: int, n: int) -> bool:
    return isinstance(d, dict) and len(d) <= n and all(_id(k) and _int(v, 0, hi) for k, v in d.items())


def _book_ok(x) -> bool:
    return x is None or (isinstance(x, dict) and set(x) == BOOK_KEYS and _id(x['to']) and _id(x['cls'])
                         and _int(x['day'], 1, 10**6) and _int(x['at'], 1, 10**6) and x['at'] <= x['day'] and _int(x['paid'], 0, 10**8))


def _trip_ok(t) -> bool:
    return t is None or (isinstance(t, dict) and set(t) == TRIP_KEYS and _id(t['to']) and _id(t['cls']) and _int(t['day'], 1, 10**6)
                         and t['ph'] in PHASES and isinstance(t['meal'], str) and (t['meal'] == '' or MEAL_RE.fullmatch(t['meal']))
                         and isinstance(t['seen'], list) and len(t['seen']) <= 16 and len(set(t['seen'])) == len(t['seen'])
                         and all(_id(x) for x in t['seen']) and _int(t['xu'], 0, 10**8) and _int(t['sp'], 0, 1000))


def _log_ok(r) -> bool:
    return (isinstance(r, dict) and set(r) == LOG_KEYS and _id(r['to']) and _id(r['cls']) and _int(r['d'], 1, 10**6)
            and _int(r['n'], 0, 16) and _int(r['sp'], 0, 1000) and _int(r['xu'], 0, 10**8))


def validate(s: dict) -> None:
    """``s['journey']['travel']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    need = lambda ok: e.need(ok, 'Dữ liệu du lịch trong bản lưu không hợp lệ.', 'invalid_save')
    need(isinstance(b, dict) and KEYS <= set(b) and b['v'] == VERSION)   # keys a newer build adds are kept
    need(_book_ok(b['book']) and _trip_ok(b['trip']) and not (b['book'] and b['trip']))
    need(_counts(b['stamps'], 10**6, 64) and _counts(b['souv'], C.SOUV_MAX, 256))
    need(isinstance(b['cards'], list) and len(b['cards']) <= CARDS_MAX and len(set(b['cards'])) == len(b['cards'])
         and all(_id(x) for x in b['cards']))
    need(isinstance(b['log'], list) and len(b['log']) <= C.LOG_MAX and all(_log_ok(r) for r in b['log']))
    st = b['stats']
    need(isinstance(st, dict) and set(STATS) <= set(st) and all(_int(v) for v in st.values()))


def upgrade(j: dict) -> None:
    """A block hand-edited or broken: keep what still makes sense. Absent stays absent."""
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    if not isinstance(b, dict):
        j[KEY] = initial()
        return
    out = initial()
    out.update({k: v for k, v in b.items() if k not in KEYS})   # a newer build's own keys stay
    out['book'] = b.get('book') if _book_ok(b.get('book')) else None
    out['trip'] = b.get('trip') if _trip_ok(b.get('trip')) else None
    if out['book'] and out['trip']:
        out['book'] = None
    d = lambda k: b.get(k) if isinstance(b.get(k), dict) else {}
    out['stamps'] = {k: v for k, v in list(d('stamps').items())[:64] if _id(k) and _int(v, 0, 10**6)}
    out['souv'] = {k: v for k, v in list(d('souv').items())[:256] if _id(k) and _int(v, 0, C.SOUV_MAX)}
    cards = b.get('cards') if isinstance(b.get('cards'), list) else []
    out['cards'] = list(dict.fromkeys(x for x in cards if _id(x)))[:CARDS_MAX]
    logs = b.get('log') if isinstance(b.get('log'), list) else []
    out['log'] = [r for r in logs if _log_ok(r)][-C.LOG_MAX:]
    st = d('stats')
    out['stats'] = {k: st[k] if _int(st.get(k)) else 0 for k in STATS}
    if out != b:
        j[KEY] = out
