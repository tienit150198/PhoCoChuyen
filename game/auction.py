"""🔨 Nhà đấu giá đồ độc bản (owner 07/10: a big money sink; the top 1 % hold 57 % of the money, the richest 4.1 M xu,
the median earns ~262 xu a day). Story mode.

Only the street sells (system lots, never a player's: nothing to launder). Each lot is one item that exactly one player
will ever own (game/auction_content.py): a vanity plate, a phone number, a painting, the right to name a landmark, a
title. Cosmetic and status only: nothing here pays xu, speeds up work or helps an exam.

Schedule (plan(), ensure_plan()): 1–3 lots a Vietnam day, deterministic from the date and the pool of unsold items,
opening 20:30 / 21:00 / 21:30 and running 24 hours. An admin may add a lot (admin_add, POST /api/admin/auction).
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


def _own_ok(k, x) -> bool:
    return (_item(k) and isinstance(x, dict) and set(x) == OWN_KEYS and x['k'] in KINDS and isinstance(x['t'], str)
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


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields: keep what still makes sense. Absent stays absent. Never drops a
    hold (it is money): a hold of an odd shape keeps its total."""
    if not isinstance(j, dict) or KEY not in j:
        return
    b = j[KEY]
    if not isinstance(b, dict):
        j[KEY] = initial()
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


# ---------------------------------------------------------------- money
def _have(s: dict) -> int:
    j = s['journey']
    b = bk.get(s)
    return max(0, j['wallet']) + (b['balance'] if b else 0)


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
    if cash:
        _jr()._wallet(j, -cash, KIND, label[:120])
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label[:120], -rest)
    return rest


def _give_back(s: dict, amount: int, bank_part: int, label: str) -> None:
    """A refund: what came from the bank account goes back there (when the account is still open), the rest to the
    wallet."""
    j = s['journey']
    b = bk.get(s)
    to_bank = min(amount, bank_part) if b else 0
    if to_bank:
        b['balance'] += to_bank
        bk._log(b, j['life_day'], 'acc', label[:120], to_bank)
    if amount - to_bank:
        _jr()._wallet(j, amount - to_bank, KIND, label[:120])


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
    if item not in b['own'] and len(b['own']) < OWN_MAX:
        b['own'][item] = dict(k=kind, t=text, d=j['life_day'], p=amount, lot=lot)
    b['stats']['won'] = b['stats'].get('won', 0) + 1
    b['stats']['xu'] = b['stats'].get('xu', 0) + amount
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
    return ''


# ---------------------------------------------------------------- views
def public(s: dict) -> dict | None:
    """Small (it rides on every state): the escrow and what was won. None until the first bid."""
    b = get(s)
    if not b:
        return None
    return dict(hold={k: h['a'] for k, h in b['hold'].items()}, held=sum(h['a'] for h in b['hold'].values()),
                own={k: dict(k=x['k'], t=x['t'], p=x['p']) for k, x in b['own'].items()}, stats=dict(b['stats']))


def show_view(s: dict) -> dict | None:
    """The player's card (game/social.py snapshot): the plate, the phone number, the titles, paintings and lands won."""
    b = get(s)
    if not b or not b['own']:
        return None
    out = {}
    for k, x in sorted(b['own'].items(), key=lambda kv: -kv[1]['p']):
        if x['k'] in ('plate', 'phone') and x['k'] not in out:
            out[x['k']] = x['t']
        elif x['k'] in ('art', 'land', 'title'):
            out.setdefault(x['k'], []).append(x['t'])
    for k in ('art', 'land', 'title'):
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


_PLATES = frozenset(fold_plate(it['name']) for it in C.ITEMS if it['kind'] == 'plate')


def catalogue() -> dict:
    """Static lists for the client (bootstrap content, cached)."""
    return dict(tiers={str(k): dict(v) for k, v in C.TIERS.items()}, pct=C.PCT, quick=list(C.QUICK), kinds=[list(k) for k in C.KINDS],
                items=[dict(it, colors=list(it['colors'])) if 'colors' in it else dict(it) for it in C.ITEMS],
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
    return out


def pick(d: datetime.date, slot: int, tier_n: int, taken: set) -> dict | None:
    """The slot's item: deterministic from the date among the free items of its tier (then the lower tiers)."""
    for t in range(tier_n, 0, -1):
        free = sorted(it['id'] for it in C.ITEMS if it['tier'] == t and it['id'] not in taken)
        if free:
            return C.ITEM[free[_h('pick', d.isoformat(), slot) % len(free)]]
    return None


def _taken(db) -> set:
    return {r['item'] for r in db.execute("SELECT item FROM auction_lots WHERE status IN ('open','sold')").fetchall()}


def _insert_lot(db, lid: str, it: dict, tier_n: int, t0: float, t1: float, src: str) -> bool:
    T = tier(tier_n)
    extra = {k: it[k] for k in ('artist', 'year', 'colors', 'motif', 'base', 'where') if k in it}
    return db.execute(
        'INSERT INTO auction_lots(id, item, kind, tier, name, emoji, data, start, step, starts_at, ends_at, planned_end, '
        "status, src, created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'open',?,?) ON CONFLICT DO NOTHING",
        (lid, it['id'], it['kind'], tier_n, it['name'][:TEXT_MAX], it['emoji'], json.dumps(extra, ensure_ascii=False),
         T['start'], T['step'], t0, t1, t1, src, now())).rowcount == 1


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


def run_housekeeping(store) -> None:
    """server.py maintenance (every 30 s, one process): today's lots, then the lots that ended. Never raises."""
    import sys
    try:
        ensure_plan(store)
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
    out = dict(id=r['id'], item=r['item'], kind=r['kind'], tier=int(r['tier']), name=r['name'], emoji=r['emoji'],
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
    operator; tier 1–3, hours 1–72, starts in `delay` minutes (0–10080)."""
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
        need(kind in ('plate', 'phone') and isinstance(text, str) and 3 <= len(text.strip()) <= 16, 'Biển số/số điện thoại 3–16 ký tự.')
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
