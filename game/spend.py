"""☕ Chỗ tiêu xu: be a customer on your own street, give at the pagoda, and wear a name colour for a week (story mode).

Owner 06/10: "cho nhiều cái cho mọi người tiêu tiền hơn". DESIGN_0610 §3, recommendation ①: the median player earns
≈ 262 xu a life day and spends ≈ 12; these are the everyday and status sinks (catalogue: game/spend_content.py).

* ☕ Đi quán (jr_spend_eat {shop, item}): the street's own shops sell to the player. No bụng / tỉnh táo go up (only
  while today's bars are on, game/needs.py; refused when every bar the item fills is already full), the first quán of
  a life day gives +1 tinh thần (+2 for a ≥ 28 xu meal), every order stamps that shop's card: the 10th stamp is its
  sticker. A line of the shop being awkward for once ("Quán hết đá…"), flavour only.
* 💆 Spa (jr_spend_spa {item}): +2 tinh thần for the first spa of a life day; buying again only rests the eyes.
* 🎬 Rạp Mây (jr_spend_film {}): one film a week (Vietnam ISO week), 20 xu, +2 tinh thần, the ticket stub is kept.
* 🙏 Công đức (jr_spend_give {amount, wish, anon, confirm}): 5 – 1,000,000 xu, a pure sink. A wish from a fixed list
  (nothing typed reaches the public board), anonymous or by account name. The Sư thầy thanks everyone the same way.
  The row goes to the `donations` table in the save's own transaction (command_commit); board() is the weekly
  "Bảng công đức" (GET /api/congduc).
* 🎨 Phong cách (jr_spend_style {id, confirm}, jr_spend_wear {kind, id|None}): a name colour, a profile frame or a
  title for 7 real days (renewable, stacked up to 4 weeks ahead). What is worn goes to `chat_style` in the same
  transaction, with pg_notify {op: 'style', pid}: the live service (live/styles.py) shows it beside the name in chat
  and on the street as an optional `st` field, outside `look` (an older live service never reads the table, an older
  client ignores `st`). Social cards (game/social.py snapshot) carry it as `style`.

Money: the T0 items come from the wallet only (never debt); công đức and the weekly items from the wallet, then the
bank account (garage._take), never a loan. Wallet rows use the existing kind 'life' (journey.HISTORY_KINDS of every
older build): no closed list grows, so no two-step release is needed. No command pays xu.

State `s['journey']['spend']` (absent until the first purchase; journey.validate allows extra keys, so 1.9.4 and older
keep loading and writing the save with it untouched), see initial():
    v        VERSION
    day      the life day `today` belongs to
    today    effect caps used that life day: 'cafe', 'spa'
    stamps   {shop id: 0..9}       stickers {shop id: count}
    film     the week key of the last ticket ('' none)        stubs [film ids], newest last, ≤ STUBS_MAX
    give     {n, sum, wk, wsum, last}: donations made, xu given, this week's key and sum, the last one
             {n, a (xu), w (wish id), anon, wk, at (unix s)} for the board row
    own      {style id: until (unix s)}                         wear {color|frame|title: style id | None}
    stats    {eat, spa, film, give, style, xu}
Ids a newer build wrote are kept by shape and not shown, so a rollback never loses anything.
"""
from __future__ import annotations

import datetime
import hashlib
import re
import threading
import time

from . import spend_content as C

VERSION = 1
KIND = 'life'
BLOCK_KEYS = frozenset({'v', 'day', 'today', 'stamps', 'stickers', 'film', 'stubs', 'give', 'own', 'wear', 'stats'})
GIVE_KEYS = frozenset({'n', 'sum', 'wk', 'wsum', 'last'})
LAST_KEYS = frozenset({'n', 'a', 'w', 'anon', 'wk', 'at'})
STATS = ('eat', 'spa', 'film', 'give', 'style', 'xu')
TODAY = ('cafe', 'spa')
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
WK_RE = re.compile(r'[0-9]{4}-W[0-9]{2}')
STUBS_MAX = 52
OWN_MAX = 48
KEEP_EXPIRED = 30 * 86400          # an expired weekly item leaves the save a month later (on the next purchase)
COMMANDS = ('jr_spend_eat', 'jr_spend_spa', 'jr_spend_film', 'jr_spend_give', 'jr_spend_style', 'jr_spend_wear')
STYLE_ACTIONS = ('jr_spend_style', 'jr_spend_wear')
VN = datetime.timezone(datetime.timedelta(hours=7))
BIG = 10**12

ITEMS = {it['id']: (sid, it) for sid, sh in C.SHOPS.items() for it in sh['items']}
SPA = {it['id']: it for it in C.SPA}
WISH = dict(C.WISHES)


# ---------------------------------------------------------------- helpers
def now() -> float:
    return time.time()


def week_key(t: float | None = None) -> str:
    y, w, _ = datetime.datetime.fromtimestamp(now() if t is None else t, VN).isocalendar()
    return f'{y:04d}-W{w:02d}'


def film_of(t: float | None = None) -> dict:
    _, w, _ = datetime.datetime.fromtimestamp(now() if t is None else t, VN).isocalendar()
    return C.FILMS[w % len(C.FILMS)]


def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _nd():
    from . import needs
    return needs


def _gr():
    from . import garage
    return garage


def _fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def initial(day: int = 1) -> dict:
    return dict(v=VERSION, day=max(1, int(day)), today=[], stamps={}, stickers={}, film='', stubs=[],
                give=dict(n=0, sum=0, wk='', wsum=0, last=None), own={}, wear={k: None for k in C.KINDS},
                stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    b = j.get('spend') if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('spend'), dict):
        j['spend'] = initial(j['life_day'])
    b = j['spend']
    if b['day'] != j['life_day']:
        b['day'], b['today'] = j['life_day'], []
    return b


def _today(s: dict) -> list:
    """Effect caps used this life day (a block of an earlier day counts as none)."""
    b = get(s)
    return list(b['today']) if b and b['day'] == s['journey']['life_day'] else []


def _bars(s: dict, full: int, wake: int) -> tuple[dict | None, str]:
    """Today's needs block (None: not on now) and why the item would do nothing ('' = it helps)."""
    n = _nd().get(s)
    if not n or n['day'] != s['journey']['life_day']:
        return None, ''
    nd = _nd()
    full_done = not full or n['full'] >= nd.FULL_CAP
    wake_done = not wake or n['wake'] >= nd.WAKE_CAP
    if (full or wake) and full_done and wake_done:
        return n, 'Bụng no rồi' if full else 'Đang tỉnh rồi'
    return n, ''


def _feed(s: dict, full: int, wake: int) -> list[str]:
    n, _ = _bars(s, full, wake)
    if not n:
        return []
    nd, out = _nd(), []
    if full:
        n['full'] = nd._clamp(n['full'] + full)
        out.append(f'No bụng {n["full"]}')
    if wake:
        n['wake'] = nd._clamp(n['wake'] + wake)
        out.append(f'Tỉnh táo {n["wake"]}')
    return out


def _cash_why(s: dict, price: int) -> str:
    w = s['journey']['wallet']
    return '' if w >= price else f'Ví còn {_fmt(max(0, w))} xu, chưa đủ {price} xu.'


def _ready_why(s: dict, price: int) -> str:
    """Công đức and weekly items: the wallet then the bank account, never with a wallet in debt."""
    j = s['journey']
    if j['wallet'] < 0:
        return f'Ví đang nợ {_fmt(-j["wallet"])} xu. Trả nợ trước nhé.'
    short = price - _gr()._have(s)['ready']
    return f'Còn thiếu {_fmt(short)} xu.' if short > 0 else ''


def _line(s: dict, salt: str, lines: tuple) -> str:
    j, b = s['journey'], get(s)
    n = b['stats']['eat'] + b['stats']['spa'] if b else 0
    h = hashlib.sha256(f"{j.get('seed', 0)}|{j['life_day']}|{n}|{salt}".encode()).digest()
    return lines[h[0] % len(lines)]


def _style_lock(s: dict, sid_: str) -> str:
    """Why a weekly item cannot be bought now, money aside ('' = only money decides)."""
    it = C.STYLE_ITEMS[sid_]
    b = get(s)
    stats = b['stats'] if b else {}
    for k, n in (it.get('need') or {}).items():
        if stats.get(k, 0) < n:
            return {'eat': f'Đi quán {n} lần để mở', 'film': f'Xem {n} phim để mở',
                    'give': f'Công đức {n} lần để mở'}.get(k, 'Chưa mở')
    t = int(now())
    until = (b['own'].get(sid_) if b else 0) or 0
    if max(t, until) + C.WEEK_SECS - t > C.AHEAD_MAX:
        return 'Đã gia hạn đủ 4 tuần'
    return ''


def style_why(s: dict, sid_: str) -> str:
    """Why this weekly item cannot be bought now ('' = it can)."""
    return _style_lock(s, sid_) or _ready_why(s, C.STYLE_ITEMS[sid_]['price'])


def style_now(s: dict, t: float | None = None) -> dict:
    """What is worn and not expired, known to this build: {'c': id, 'f': id, 't': id} (absent kinds left out)."""
    b = get(s)
    if not b:
        return {}
    t = now() if t is None else t
    out = {}
    for kind, key in (('color', 'c'), ('frame', 'f'), ('title', 't')):
        x = b['wear'].get(kind)
        if x and x in C.STYLE_ITEMS and C.STYLE_ITEMS[x]['kind'] == kind and b['own'].get(x, 0) > t:
            out[key] = x
    return out


def _prune(b: dict, t: int) -> None:
    gone = [k for k, u in b['own'].items() if u < t - KEEP_EXPIRED and k not in b['wear'].values()]
    for k in gone:
        b['own'].pop(k)


# ---------------------------------------------------------------- save
def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


def _counts(d, hi: int) -> bool:
    return isinstance(d, dict) and len(d) <= 64 and all(
        isinstance(k, str) and ID_RE.fullmatch(k) and _int(v, 0, hi) for k, v in d.items())


def _last_ok(x) -> bool:
    return x is None or (isinstance(x, dict) and set(x) == LAST_KEYS and _int(x['n'], 1) and _int(x['a'], C.GIVE_MIN, C.GIVE_MAX)
                         and isinstance(x['w'], str) and (x['w'] == '' or ID_RE.fullmatch(x['w']) is not None)
                         and type(x['anon']) is bool and isinstance(x['wk'], str) and WK_RE.fullmatch(x['wk']) is not None
                         and _int(x['at'], 0, 2**34))


def validate(s: dict) -> None:
    """``s['journey']['spend']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    b = get(s)
    j = s.get('journey')
    bad = 'Dữ liệu chi tiêu trong bản lưu không hợp lệ.'
    if b is None:
        e.need(not isinstance(j, dict) or j.get('spend') is None, bad, 'invalid_save')
        return
    need = lambda ok: e.need(ok, bad, 'invalid_save')
    need(set(b) == BLOCK_KEYS and b['v'] == VERSION and _int(b['day'], 1, 10**6))
    need(isinstance(b['today'], list) and len(b['today']) <= 8 and all(isinstance(x, str) and ID_RE.fullmatch(x) for x in b['today']))
    need(_counts(b['stamps'], C.STAMP_CARD - 1) and _counts(b['stickers'], 10**6))
    need(isinstance(b['film'], str) and (b['film'] == '' or WK_RE.fullmatch(b['film']) is not None))
    need(isinstance(b['stubs'], list) and len(b['stubs']) <= STUBS_MAX and all(isinstance(x, str) and ID_RE.fullmatch(x) for x in b['stubs']))
    g = b['give']
    need(isinstance(g, dict) and set(g) == GIVE_KEYS and _int(g['n'], 0, 10**9) and _int(g['sum']) and _int(g['wsum'])
         and isinstance(g['wk'], str) and (g['wk'] == '' or WK_RE.fullmatch(g['wk']) is not None) and _last_ok(g['last'])
         and (g['last'] is None or g['last']['n'] == g['n']))
    need(_counts(b['own'], 2**34) and len(b['own']) <= OWN_MAX)
    w = b['wear']
    need(isinstance(w, dict) and set(w) == set(C.KINDS) and all(v is None or (isinstance(v, str) and v in b['own']) for v in w.values()))
    st = b['stats']
    need(isinstance(st, dict) and set(st) <= set(STATS) and all(_int(v) for v in st.values()))


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep what still makes sense. Absent stays
    absent."""
    if not isinstance(j, dict) or 'spend' not in j:
        return
    b = j['spend']
    if not isinstance(b, dict):
        j['spend'] = initial(j.get('life_day') if _int(j.get('life_day'), 1, 10**6) else 1)
        return
    out = initial(b['day'] if _int(b.get('day'), 1, 10**6) else 1)
    if isinstance(b.get('today'), list):
        out['today'] = [x for x in b['today'] if isinstance(x, str) and ID_RE.fullmatch(x)][:8]
    for k, hi in (('stamps', C.STAMP_CARD - 1), ('stickers', 10**6)):
        d = b.get(k) if isinstance(b.get(k), dict) else {}
        out[k] = {x: v for x, v in list(d.items())[:64] if isinstance(x, str) and ID_RE.fullmatch(x) and _int(v, 0, hi)}
    if isinstance(b.get('film'), str) and WK_RE.fullmatch(b['film']):
        out['film'] = b['film']
    if isinstance(b.get('stubs'), list):
        out['stubs'] = [x for x in b['stubs'] if isinstance(x, str) and ID_RE.fullmatch(x)][-STUBS_MAX:]
    g = b.get('give') if isinstance(b.get('give'), dict) else {}
    for k in ('n', 'sum', 'wsum'):
        if _int(g.get(k), 0, 10**9 if k == 'n' else BIG):
            out['give'][k] = g[k]
    if isinstance(g.get('wk'), str) and WK_RE.fullmatch(g['wk']):
        out['give']['wk'] = g['wk']
    last = g.get('last')
    if isinstance(last, dict) and set(last) >= LAST_KEYS:
        last = {k: last[k] for k in LAST_KEYS}
    out['give']['last'] = last if _last_ok(last) and last and last['n'] == out['give']['n'] else None
    own = b.get('own') if isinstance(b.get('own'), dict) else {}
    out['own'] = {k: v for k, v in list(own.items())[:OWN_MAX] if isinstance(k, str) and ID_RE.fullmatch(k) and _int(v, 0, 2**34)}
    w = b.get('wear') if isinstance(b.get('wear'), dict) else {}
    out['wear'] = {k: w.get(k) if isinstance(w.get(k), str) and w.get(k) in out['own'] else None for k in C.KINDS}
    st = b.get('stats') if isinstance(b.get('stats'), dict) else {}
    out['stats'] = {k: st[k] if _int(st.get(k)) else 0 for k in STATS}
    if out != b:
        j['spend'] = out


# ---------------------------------------------------------------- commands
def _keys(p: dict, allowed: set, required: set = frozenset()) -> None:
    _core().need(isinstance(p, dict) and set(p) <= allowed and required <= set(p), 'Thông tin không hợp lệ.')


def _spirit(s: dict, n: int) -> int:
    return _nd()._spirit(s, n)


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Đi quán, đi chùa và phong cách chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    jr = _jr()
    if name == 'jr_spend_eat':
        _keys(p, {'shop', 'item'}, {'shop', 'item'})
        x = ITEMS.get(p['item']) if isinstance(p['item'], str) else None
        need(x is not None and x[0] == p['shop'] and not x[1].get('gone'), 'Chọn một món trong quán nhé.')
        shop_id, it = x
        shop = C.SHOPS[shop_id]
        _, full = _bars(s, it['full'], it['wake'])
        need(not full, f'{full}, gọi món khác hoặc lát nữa nhé.', 'too_full')
        why = _cash_why(s, it['price'])
        need(not why, why, 'not_enough')
        jr._wallet(j, -it['price'], KIND, f'Đi quán · {it["name"]}'[:120])
        b = _ensure(s)
        bars = _feed(s, it['full'], it['wake'])
        got = 0
        if 'cafe' not in b['today']:
            b['today'].append('cafe')
            got = _spirit(s, 2 if it['price'] >= 28 else 1)
        n = b['stamps'].get(shop_id, 0) + 1
        sticker = n >= C.STAMP_CARD
        b['stamps'][shop_id] = 0 if sticker else n
        if sticker:
            b['stickers'][shop_id] = b['stickers'].get(shop_id, 0) + 1
        b['stats']['eat'] += 1
        b['stats']['xu'] += it['price']
        bits = [f'{it["emoji"]} {it["name"]} ({it["price"]} xu).'] + [x + '.' for x in bars] + ([f'Tinh thần +{got}.'] if got else [])
        bits.append(f'🏷️ Đủ {C.STAMP_CARD} dấu: nhận nhãn dán {shop["name"]}!' if sticker else f'Thẻ tích điểm {n}/{C.STAMP_CARD}.')
        return dict(message=' '.join(bits), effects=[_line(s, shop_id, C.QUAN_LINES)])
    if name == 'jr_spend_spa':
        _keys(p, {'item'}, {'item'})
        it = SPA.get(p['item']) if isinstance(p['item'], str) else None
        need(it is not None and not it.get('gone'), 'Chọn một dịch vụ nhé.')
        why = _cash_why(s, it['price'])
        need(not why, why, 'not_enough')
        jr._wallet(j, -it['price'], KIND, f'Spa · {it["name"]}'[:120])
        b = _ensure(s)
        bars = _feed(s, 0, it['wake']) if it['wake'] and not _bars(s, 0, it['wake'])[1] else []
        got = 0
        if 'spa' not in b['today']:
            b['today'].append('spa')
            got = _spirit(s, C.SPA_SPIRIT)
        b['stats']['spa'] += 1
        b['stats']['xu'] += it['price']
        tail = f'Tinh thần +{got}.' if got else 'Hôm nay thư giãn rồi, chỉ thêm thơm tho.'
        return dict(message=' '.join([f'{it["emoji"]} {it["name"]} ({it["price"]} xu).'] + [x + '.' for x in bars] + [tail]))
    if name == 'jr_spend_film':
        _keys(p, set())
        wk = week_key()
        b = get(s)
        need(not b or b['film'] != wk, 'Tuần này bạn xem phim rồi. Tuần sau có phim mới.', 'already_done')
        why = _cash_why(s, C.FILM_PRICE)
        need(not why, why, 'not_enough')
        f = film_of()
        jr._wallet(j, -C.FILM_PRICE, KIND, f'Rạp Mây · {f["name"]}'[:120])
        b = _ensure(s)
        b['film'] = wk
        if f['id'] in b['stubs']:
            b['stubs'].remove(f['id'])
        b['stubs'] = (b['stubs'] + [f['id']])[-STUBS_MAX:]
        got = _spirit(s, C.FILM_SPIRIT)
        b['stats']['film'] += 1
        b['stats']['xu'] += C.FILM_PRICE
        return dict(message=f'{f["emoji"]} Xem “{f["name"]}” ({C.FILM_PRICE} xu). Giữ cuống vé làm kỷ niệm.' + (f' Tinh thần +{got}.' if got else ''))
    if name == 'jr_spend_give':
        _keys(p, {'amount', 'wish', 'anon', 'confirm'}, {'amount', 'confirm'})
        amount = e.integer(p['amount'], C.GIVE_MIN, C.GIVE_MAX)
        wish = p.get('wish', '')
        anon = p.get('anon', True)
        need(wish in C.WISH_IDS and type(anon) is bool, 'Thông tin công đức không hợp lệ.')
        need(p['confirm'] is True, f'Xác nhận công đức {_fmt(amount)} xu.')
        why = _ready_why(s, amount)
        need(not why, why, 'not_enough')
        how = _gr()._take(s, amount, 'Công đức Chùa Gió Lành')
        b = _ensure(s)
        g, wk = b['give'], week_key()
        if g['wk'] != wk:
            g['wk'], g['wsum'] = wk, 0
        g['n'] += 1
        g['sum'] += amount
        g['wsum'] += amount
        g['last'] = dict(n=g['n'], a=amount, w=wish, anon=anon, wk=wk, at=int(now()))
        b['stats']['give'] += 1
        b['stats']['xu'] += amount
        return dict(message=f'🙏 Đã công đức {how}. {C.THANKS}')
    if name == 'jr_spend_style':
        _keys(p, {'id', 'confirm'}, {'id', 'confirm'})
        it = C.STYLE_ITEMS.get(p['id']) if isinstance(p['id'], str) else None
        need(it is not None and not it.get('gone'), 'Chọn một món trong Phong cách nhé.')
        need(p['confirm'] is True, f'Xác nhận mua {it["name"]} 7 ngày.')
        why = style_why(s, it['id'])
        need(not why, why, 'limit' if 'gia hạn' in why else 'locked' if 'để mở' in why else 'not_enough')
        how = _gr()._take(s, it['price'], f'Phong cách 7 ngày · {it["name"]}'[:120])
        b = _ensure(s)
        t = int(now())
        _prune(b, t)
        b['own'][it['id']] = max(t, b['own'].get(it['id'], 0)) + C.WEEK_SECS
        b['wear'][it['kind']] = it['id']
        b['stats']['style'] += 1
        b['stats']['xu'] += it['price']
        days = -(-(b['own'][it['id']] - t) // 86400)
        return dict(message=f'{it["emoji"]} {it["name"]}: đã trả {how}, còn {days} ngày.')
    # jr_spend_wear
    _keys(p, {'kind', 'id'}, {'kind'})
    kind, sid_ = p['kind'], p.get('id')
    need(kind in C.KINDS, 'Thông tin không hợp lệ.')
    b = get(s)
    if sid_ is None:
        if b:
            b['wear'][kind] = None
        return dict(message='Đã cất.')
    need(isinstance(sid_, str) and sid_ in C.STYLE_ITEMS and C.STYLE_ITEMS[sid_]['kind'] == kind, 'Thông tin không hợp lệ.')
    need(b is not None and b['own'].get(sid_, 0) > now(), 'Món này hết hạn rồi. Gia hạn để dùng tiếp nhé.', 'expired')
    b['wear'][kind] = sid_
    return dict(message=f'Đang dùng {C.STYLE_ITEMS[sid_]["name"]}.')


# ---------------------------------------------------------------- views
def public(s: dict) -> dict:
    """Small on purpose (it rides on every state): money reasons are the client's (wallet, bank balance, prices);
    the server says what only it knows: `full` (items today's needs bars refuse), `lock` (weekly items not open yet or
    renewed 4 weeks ahead), this week's film and whether it was seen. The rest only once the block exists."""
    j = s['journey']
    b = get(s)
    t = now()
    wk = week_key(t)
    out = dict(story=bool(j.get('story')), film=film_of(t)['id'], seen=bool(b) and b['film'] == wk)
    full = [i for i, (_, it) in ITEMS.items() if _bars(s, it['full'], it['wake'])[1]]
    if full:
        out['full'] = full
    lock = {i: w for i in C.STYLE_ITEMS if (w := _style_lock(s, i))}
    if lock:
        out['lock'] = lock
    if b:
        g = b['give']
        out.update(today=_today(s), stamps=dict(b['stamps']), stickers=dict(b['stickers']), stubs=len(b['stubs']),
                   give=dict(n=g['n'], sum=g['sum'], wsum=g['wsum'] if g['wk'] == wk else 0),
                   own={k: v for k, v in b['own'].items() if k in C.STYLE_ITEMS and v > t}, wear=dict(b['wear']),
                   st=style_now(s, t))
    return out


def catalogue() -> dict:
    """Static lists for the client (bootstrap content, cached)."""
    return dict(shops=[dict(id=k, emoji=v['emoji'], name=v['name'], items=[dict(x) for x in v['items']]) for k, v in C.SHOPS.items()],
                stamp_card=C.STAMP_CARD, spa_name=C.SPA_NAME, spa=[dict(x) for x in C.SPA], spa_spirit=C.SPA_SPIRIT,
                films=[dict(x) for x in C.FILMS], film_price=C.FILM_PRICE, film_spirit=C.FILM_SPIRIT,
                give=dict(min=C.GIVE_MIN, max=C.GIVE_MAX, presets=list(C.GIVE_PRESETS), anon_under=C.ANON_UNDER,
                          wishes=[dict(id=k, text=v) for k, v in C.WISHES if k]),
                colors=[dict(x) for x in C.COLORS], frames=[dict(x) for x in C.FRAMES],
                titles=[dict(x, need=dict(x['need'])) for x in C.TITLES], week_days=C.WEEK_SECS // 86400)


# ---------------------------------------------------------------- database (the save's own transaction)
def _pid(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


def style_row(after: dict) -> dict | None:
    """The chat_style row of a save: what is worn now and until when (None: nothing worn and unexpired)."""
    b = get(after)
    if not b:
        return None
    st = style_now(after)
    if not st:
        return None
    row = {}
    for key, kind in (('c', 'color'), ('f', 'frame'), ('t', 'title')):
        x = st.get(key)
        row[kind] = x or ''
        row[kind + '_until'] = float(b['own'][x]) if x else 0.0
    return row


def command_commit(db, sid: str, action: str, after: dict) -> None:
    """Called by the storage layer for jr_spend_* commands, in the save's transaction (game/storage.py)."""
    if not action.startswith('jr_spend_'):
        return
    from . import live_chat
    b = get(after)
    if action == 'jr_spend_give' and b and b['give']['last']:
        x = b['give']['last']
        db.execute('INSERT INTO donations(id, sid, week, amount, wish, anon, at) VALUES(?,?,?,?,?,?,?) ON CONFLICT (id) DO NOTHING',
                   (f'{_pid(sid)}:{x["n"]}', sid, x['wk'], x['a'], x['w'], 1 if x['anon'] else 0, float(x['at'])))
        _BOARD.clear()
    elif action in STYLE_ACTIONS:
        row, pid = style_row(after), _pid(sid)
        if row:
            db.execute('INSERT INTO chat_style(pid, sid, color, color_until, frame, frame_until, title, title_until, at) '
                       'VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT (pid) DO UPDATE SET sid=EXCLUDED.sid, color=EXCLUDED.color, '
                       'color_until=EXCLUDED.color_until, frame=EXCLUDED.frame, frame_until=EXCLUDED.frame_until, '
                       'title=EXCLUDED.title, title_until=EXCLUDED.title_until, at=EXCLUDED.at',
                       (pid, sid, row['color'], row['color_until'], row['frame'], row['frame_until'], row['title'], row['title_until'], now()))
        else:
            db.execute('DELETE FROM chat_style WHERE pid=?', (pid,))
        live_chat.notify(db, dict(op='style', pid=pid))


def forget(db, sid: str) -> None:
    """A player erased their data: their style row goes, their donations stay on the board as anonymous."""
    db.execute('DELETE FROM chat_style WHERE sid=?', (sid,))
    db.execute("UPDATE donations SET sid='', anon=1 WHERE sid=?", (sid,))
    _BOARD.clear()


# ---------------------------------------------------------------- 🙏 Bảng công đức (GET /api/congduc)
BOARD_TOP = 10
BOARD_RECENT = 5
BOARD_SECS = 10.0
_BOARD: dict = {}          # week key -> (at, rows): one entry, bounded
_LOCK = threading.Lock()


def _name(r) -> str:
    return 'Ẩn danh' if r['anon'] or not r['display'] else str(r['display'])[:24]


def _board_rows(store, wk: str) -> dict:
    with _LOCK:
        hit = _BOARD.get(wk)
        if hit and time.monotonic() - hit[0] < BOARD_SECS:
            return hit[1]
    with store.connect() as db:
        top = db.execute('SELECT d.sid AS sid, d.anon AS anon, SUM(d.amount) AS xu, MIN(d.at) AS first, a.display AS display '
                         'FROM donations d LEFT JOIN accounts a ON a.sid=d.sid AND d.anon=0 WHERE d.week=? '
                         'GROUP BY d.sid, d.anon, a.display ORDER BY xu DESC, first ASC LIMIT ?', (wk, BOARD_TOP)).fetchall()
        recent = db.execute('SELECT d.sid AS sid, d.anon AS anon, d.amount AS xu, d.wish AS wish, d.at AS at, a.display AS display '
                            'FROM donations d LEFT JOIN accounts a ON a.sid=d.sid AND d.anon=0 WHERE d.week=? '
                            'ORDER BY d.at DESC LIMIT ?', (wk, BOARD_RECENT)).fetchall()
        tot = db.execute('SELECT COALESCE(SUM(amount), 0) AS xu, COUNT(DISTINCT sid) AS people FROM donations WHERE week=?', (wk,)).fetchone()
    out = dict(top=[dict(sid=r['sid'], anon=bool(r['anon']), name=_name(r), xu=int(r['xu'])) for r in top],
               recent=[dict(sid=r['sid'], anon=bool(r['anon']), name=_name(r), xu=int(r['xu']), wish=WISH.get(r['wish'], ''), at=int(r['at'])) for r in recent],
               xu=int(tot['xu']), people=int(tot['people']))
    with _LOCK:
        _BOARD.clear()
        _BOARD[wk] = (time.monotonic(), out)
    return out


def board(store, token: str | None) -> dict:
    """This week's board: the top givers (named or Ẩn danh), the latest gifts with their wish, the total, and mine."""
    wk = week_key()
    rows = _board_rows(store, wk)
    sid = store.key(token) if isinstance(token, str) and 16 <= len(token) <= 128 else None
    mine = 0
    if sid:
        with store.connect() as db:
            r = db.execute('SELECT COALESCE(SUM(amount), 0) AS xu FROM donations WHERE week=? AND sid=?', (wk, sid)).fetchone()
            mine = int(r['xu'])
    strip = lambda x: {k: v for k, v in x.items() if k != 'sid'} | {'me': bool(sid) and x['sid'] == sid}
    return dict(week=wk, top=[strip(x) for x in rows['top']], recent=[strip(x) for x in rows['recent']], xu=rows['xu'],
                people=rows['people'], mine=mine)
