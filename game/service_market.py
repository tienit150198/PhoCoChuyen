"""🛎️ Phố dịch vụ: players serve players across careers (owner 21/10).

A buyer picks a provider's service in the directory (or at the provider's workplace), pays into escrow, the provider
does the work, and the deal settles: the provider gets 95 %, 5 % is burned (a money sink: it goes to nobody).

Owner's numbers (21/10)
* Price for a player buyer: the NPC price × 3 by default. The provider sets ×1…×10 per service, or 🤝 thương lượng:
  the buyer offers a price, the provider accepts / counters / declines, at most MAX_ROUNDS offers in all, a talk with
  no answer for TALK_HOURS expires. Every price stays within [max(floor, NPC price), min(NPC price × 10, max price)]
  (per unit; a quantity multiplies it). The price is locked into escrow when both agree.
* Fee: FEE_PCT (5 %) of every completed deal, rounded up, burned. Cancel / decline / expiry / a late provider: the
  buyer gets the whole price back.

Money (exactly once, never debt)
* Escrow comes from the wallet, then the bank account; a wallet in debt or not enough money refuses. Wallet history
  rows are at most ROW_MAX (10 M) each (every build validates that). Pay-outs go to the wallet (rows ≤ 10 M, the bank
  account past the wallet's maximum), or to the career's fund (spec pay_to='career'). Refunds go to the wallet,
  then the bank account past its maximum (legacy and 📸 photo refunds too).
* Every money move is one transaction: the save(s) under their revision guard (marriage._mutate) and the order row's
  status flip guarded by its old status (UPDATE … WHERE status=…: a second worker finds nothing and rolls back).
  Status changes that move no money are a DB-only transaction; the money step follows (ready → done, refund →
  refunded) in the same request, the buyer's / provider's next poll, or the housekeeping (run_housekeeping).

Anti-laundering (all at the moment money moves, inside its transaction; checked earlier too for a clear answer)
* Never yourself; both registered accounts; nobody blocked either way.
* Same network: a buyer and a provider seen on one network within NET_DAYS (keyed tags: game/lixi.py ip_tag in
  svc_net and lixi_grabs, game/pet_arena.py ip_tag in pet_arena) never trade. Spouses (a married couple) are allowed
  (one home, one wifi) but count toward every cap below.
* A buyer–provider pair: at most PAIR_DAY deals a Vietnam day and PAIR_WEEK_XU xu a Vietnam week (both kinds of
  orders; a service with a higher max price allows one such order a week).
* An account younger than 7 real days pays at most bank_xfer.NEW_DAY_MAX xu a day out of its save, shared with bank
  transfers and every other route (bank_xfer.count_out).
* One order at most MAX_PRICE (50 M) unless the service declares a higher max_price; legacy workplace orders at most
  LEGACY_MAX (1 M: the save's player_order price, validated by every build).
* Ratings count once per buyer and provider a week, from accounts at least 3 days old; only paid, completed orders
  can be rated.
* 🚩 A buyer may report an order within FLAG_HOURS of its delivery: the admin view lists it; nothing automatic.

Legacy orders (game/work_visits.py, game/player_service_tasks.py): a workplace's next scripted task, its staff order
and a quầy's dishes are registered here (service 'job' of each career, ('quay', 'dish')). They keep their own escrow
table (work_service_orders) and flow; this build prices them ×3 (or the provider's setting), lets them be negotiated,
pays 95 % and burns 5 %, takes wallet then bank, and puts them under the same anti-laundering guard. The profit bonus
of a staff order counts only the real margin at the NPC price; the quầy visitor bonus stays capped at 2× the dish's
base price (player_service_tasks.VISIT_BONUS_RATIO).

Contract for career modules (see register): a spec's `deliver(db, provider_sid, buyer_sid, order) -> dict` runs inside
the transaction that marks the work done (a photo into the buyer's album, a stay booked, a birth assisted…);
`on_buyer(state, order)` / `on_provider(state, order)` change the saves inside the settlement transaction (once).
Career code delivers with deliver(store, …) or, inside a game command, by putting {'order': id, 'result': {...}} in
result['svc_done'] (storage.py calls command_commit in the command's transaction).

Own-flow listings (spec `open`): a career whose booking already has its own flow, escrow table and payout (🏥 player
birth rooms: game/birth.py birth_stays; 📸 player photographers: game/photo_studio.py photo_orders) is LISTED here
only. Its providers come from the module (`providers` / `offer` callbacks, never svc_settings), its card shows the
module's price and rating and opens the module's own sheet (`open`: a client action); ordering, offers and settings
through this market are refused (ServiceError 'own_flow' / 'own_settings'), so there is one payment path and one
escrow per booking. The provider sets price and open/closed in the module (`setup`).

Money steps never wedge (review 22/10): every timer and settlement of the housekeeping and of a player's poll runs one
row at a time; a row whose step fails (a hook raising, a save that refuses, a wallet and bank account both full) is
logged, its due_at pushed back (RETRY_BASE_S × 2^tries, at most RETRY_MAX_S) and the next row goes on; a GET never
raises because of a settlement. A provider whose wallet and account are full is paid into the career's fund instead
(started careers); otherwise the payee is told once (notice) and the row retries. A 'ready' row of a service this build
does not know (get_spec None: a newer build registered it) is left for a build that knows it (its hooks), never paid.

🛑 MNL_SVC_OFF=1 (1 / true / yes / on): no new order, offer, counter-offer or accepted price; everything already paid
keeps going (take, deliver, confirm, cancel, decline, the timers, settlements and refunds). Rollback: docs/SERVICE_MARKET.md
"Rollback runbook" (scripts/svc_drain.py first).

Tables (game/pg_schema.py SCHEMA_VERSION 63, indexes 75): svc_settings, svc_orders, svc_reviews, svc_rep, svc_flags,
svc_net, work_service_orders.fee. Nothing in any save.
"""
from __future__ import annotations

import copy
import hashlib
import heapq
import itertools
import json
import logging
import os
import re
import secrets
import threading
import time

from . import marriage as mr

LOG = logging.getLogger(__name__)

FEE_PCT = 5                    # burned on each completed deal (rounded up)
DEFAULT_MULT = 3               # NPC price × 3 for a player buyer
MULT_MIN, MULT_MAX = 1, 10
MODES = ('fixed', 'nego')
MAX_PRICE = 50_000_000         # one order, unless a service declares a higher max_price
LEGACY_MAX = 1_000_000         # a legacy order's price lives in the save (player_service_tasks.validate)
PRICE_CEIL = 10 ** 9
MAX_ROUNDS = 6                 # offers in one talk, both sides together
TALK_HOURS = 12                # a talk with no answer expires
HOLD_HOURS = 24                # a paid order the provider never takes: refunded
WORK_HOURS = 72                # a taken order never delivered: refunded (a spec may say otherwise)
CONFIRM_HOURS = 24             # a delivered order the buyer never confirms: confirmed
FLAG_HOURS = 24                # a report within this long after delivery
PAIR_DAY = 5                   # deals a Vietnam day between one buyer and one provider
PAIR_WEEK_XU = 60_000_000      # xu a Vietnam week between one buyer and one provider
NET_DAYS = 3                   # network tags this recent count as "the same network"
BUYER_OPEN = 20                # open talks/orders of a buyer
PROVIDER_OPEN = 50             # open talks/orders of a provider
ONLINE_SECONDS = 300
RATE_DAYS = 7                  # one counted rating per buyer and provider in this many days
RATE_ACCOUNT_DAYS = 3
PAGE = 30
ROW_MAX = 10_000_000           # a wallet history row
NOTE_MAX = 200
QTY_CEIL = 30
OUT_KIND, IN_KIND = 'life', 'salary'
DAY, HOUR = 86400, 3600

OPEN = ('talk', 'held', 'working', 'delivered', 'ready', 'refund')
MONEY = ('held', 'working', 'delivered', 'ready', 'done')       # escrowed: counts toward the pair caps
WO_MONEY = ('requested', 'accepted', 'ready', 'completed')
FINAL = ('done', 'refunded', 'declined', 'cancelled', 'expired', 'linked')
RID_RX = re.compile(r'[A-Za-z0-9_-]{8,80}')
ID_RX = re.compile(r'(?:sv|wo)_[0-9a-f]{24}')
OWN_TEXT = 'Dịch vụ này đặt ở mục riêng của nghề: bấm “Mở” trên thẻ dịch vụ nhé.'
OWN_SETUP_TEXT = 'Dịch vụ này cài giá và mở / đóng ở mục riêng của nghề.'
OFF_TEXT = 'Phố dịch vụ đang tạm nghỉ nhận đơn mới. Đơn đã đặt vẫn được làm, thanh toán hoặc hoàn tiền như thường.'
FULL_TEXT = '🛎️ Ví và tài khoản của bạn đã đầy nên tiền đơn Phố dịch vụ đang chờ. Tiêu bớt rồi tiền sẽ tự về nhé.'
RETRY_BASE_S = 60              # a money step that failed waits this long, doubled each time …
RETRY_MAX_S = 6 * 3600         # … at most this long, then tries again
OFFSET_MAX = 2000              # the directory's deepest page
TOUCH_S = 600                  # a network tag of a GET poll is written at most this often per player and network
REG_TTL = 120.0                # 🤝 khách quen counts kept this long per provider …
REG_MAX = 2000                 # … for at most this many providers


class ServiceError(mr.MarriageError):
    """A refusal shown as is (the server answers a MarriageError with its status and code)."""


def need(cond, message: str, code: str = 'svc_error', status: int = 400):
    if not cond:
        raise ServiceError(message, code, status)


def env_on(name: str) -> bool:
    """A kill switch in the environment: 1 / true / yes / on (any case, spaces ignored) turns it on."""
    return os.environ.get(name, '').strip().lower() in ('1', 'true', 'yes', 'on')


def off() -> bool:
    """🛑 MNL_SVC_OFF: no new orders or talks; what is already paid keeps settling and refunding."""
    return env_on('MNL_SVC_OFF')


def now() -> float:
    return time.time()


def fmt(n) -> str:
    return f'{int(n):,}'.replace(',', '.')


def fee_of(price: int) -> int:
    """The burned part of a completed deal: FEE_PCT %, rounded up (every deal burns at least 1 xu)."""
    return (int(price) * FEE_PCT + 99) // 100 if price > 0 else 0


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _data(row) -> dict:
    try:
        d = json.loads(row['data']) if row and row.get('data') else {}
    except (TypeError, ValueError):
        d = {}
    return d if isinstance(d, dict) else {}


def _pid(sid: str) -> str:
    from . import social
    return social.pid_of(sid)


# ---------------------------------------------------------------- the registry
SPEC_KEYS = frozenset(('name', 'icon', 'desc', 'base', 'unit', 'duration', 'floor', 'max_price', 'qty_max', 'work_hours',
                       'deliver', 'on_buyer', 'on_provider', 'confirm', 'requires', 'check', 'can_provide', 'pay_to',
                       'note_hint', 'legacy', 'open', 'providers', 'offer', 'setup', 'note_check'))
OWN_FORBIDDEN = ('deliver', 'on_buyer', 'on_provider', 'confirm', 'pay_to', 'legacy')   # an own-flow listing never uses the escrow
ACTION_RX = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,39}')
LINK_KEY_RX = re.compile(r'[a-z][a-z0-9_]{0,23}')
LISTING_MAX = 300              # own-flow providers of one service read for a directory page (cheap, indexed queries)
REQUIRES = frozenset(('life_day', 'chapter', 'story', 'married'))
REGISTRY: dict = {}
_seeded = [False]


def register(career: str, service_id: str, spec: dict) -> dict:
    """Add (or replace) one service that a player of `career` can sell to other players. Returns the normalized spec.

    spec (dict; only `name` and `base` are required):
      name        str, ≤ 60: what the buyer sees ("Chụp chân dung")
      base        int ≥ 1 or callable(db, provider_sid) -> int: the NPC price of one unit, xu (keep a callable cheap:
                  one indexed query at most; it runs for each directory card)
      icon        str emoji (default '🛎️'); desc: str ≤ 160, one line under the name
      unit        str (default 'lượt'): one unit ("tấm ảnh", "đêm")
      duration    int minutes the work usually takes (shown; default 30)
      floor       int xu: the lowest unit price ever accepted (a negotiation included); the effective floor is
                  max(floor, base) — e.g. a birth room floor=500_000
      max_price   int xu: the most one order may cost (default MAX_PRICE 50 M; higher only when declared here)
      qty_max     int 1…30 (default 1): units in one order (nights of a stay)
      work_hours  int: hours a taken order may wait for delivery before the buyer is refunded (default 72)
      deliver     callable(db, provider_sid, buyer_sid, order) -> dict | None: the real effect, run inside the
                  transaction that marks the work done; raise ServiceError to refuse (the order stays open). Its dict
                  (JSON, ≤ 4 KB) is kept on the order and shown to both (order['result'])
      on_buyer    callable(state, order) -> None: the buyer's save, changed inside the settlement transaction (once)
      on_provider callable(state, order) -> None: the provider's save, the same
      confirm     'auto' (the system trusts deliver: settled at once) | 'buyer' (the buyer confirms, or it is
                  confirmed after CONFIRM_HOURS). Default 'auto' with deliver, else 'buyer'
      requires    dict, any of {life_day: int, chapter: int, story: bool, married: bool}: what the buyer needs
      check       callable(db, buyer_sid, buyer_state) -> str: '' or the reason the buyer cannot order
      can_provide callable(provider_state) -> str: '' or why this player cannot sell it (default: the career is
                  started in the save)
      pay_to      'wallet' (default) | 'career': the provider's 95 % into the wallet or into the career's fund
      note_hint   str: the placeholder of the buyer's note box
      note_check  callable(note) -> str: '' or why this note is refused, checked before any money moves (📻 a ticker
                  line must pass its moderation at the order, not only at the delivery)

    Own-flow listing (a module with its own booking, escrow table and payout; the market only lists it):
      open        {action: str, data: {k: str|int|bool}, label: str}: the client action that opens the module's own
                  order sheet (each provider row's `data` is merged in, e.g. the room or the place to preselect)
      providers   callable(db, limit, offset) -> [row]: the providers listed now (open), any order
      offer       callable(db, provider_sid) -> row | None: one provider's row, listed (`on`) or not
      setup       {action, data, label}: where the provider sets price and open/closed (🧰 links there)
                  row = {sid, price (xu, one unit), on (listed), stars (sum), rated (count), deals, at (float),
                  data {…}, title (str, optional), why (str, optional: why it is not listed)}
      With `open`, `providers` and `offer` are required and deliver / on_buyer / on_provider / confirm / pay_to /
      legacy are refused: POST order / offer / settings answer 'own_flow' / 'own_settings' (409).

    The order dict given to the hooks: {id, career, service, buyer, provider (sids), buyer_pid, provider_pid, qty,
    price (escrow, xu), fee, paid (= price − fee, at settlement), note, input (what the provider sent with the
    delivery), result, created_at}."""
    key = (str(career), str(service_id))
    if not (re.fullmatch(r'[a-z][a-z0-9_]{0,39}', key[0]) and re.fullmatch(r'[a-z][a-z0-9_]{0,39}', key[1])):
        raise ValueError(f'service_market.register: bad id {key}')
    out = _norm(key, spec)
    REGISTRY[key] = out
    return dict(out)


def _norm(key, spec) -> dict:
    if not isinstance(spec, dict):
        raise ValueError('service_market.register: spec must be a dict')
    unknown = set(spec) - SPEC_KEYS
    if unknown:
        raise ValueError(f'service_market.register {key}: unknown spec keys {sorted(unknown)}')
    name = spec.get('name')
    if not isinstance(name, str) or not 0 < len(name) <= 60:
        raise ValueError(f'service_market.register {key}: name')
    base = spec.get('base')
    if not (callable(base) or (type(base) is int and 1 <= base <= PRICE_CEIL)):
        raise ValueError(f'service_market.register {key}: base must be an int ≥ 1 or a callable')
    legacy = spec.get('legacy')
    out = dict(career=key[0], service=key[1], name=name, icon=str(spec.get('icon') or '🛎️')[:8],
               desc=str(spec.get('desc') or '')[:160], base=base, unit=str(spec.get('unit') or 'lượt')[:24],
               duration=int(spec.get('duration') or 30), floor=int(spec.get('floor') or 0),
               max_price=int(spec.get('max_price') or (LEGACY_MAX if legacy else MAX_PRICE)),
               qty_max=int(spec.get('qty_max') or 1), work_hours=int(spec.get('work_hours') or WORK_HOURS),
               deliver=spec.get('deliver'), on_buyer=spec.get('on_buyer'), on_provider=spec.get('on_provider'),
               confirm=spec.get('confirm') or ('auto' if spec.get('deliver') else 'buyer'),
               requires=dict(spec.get('requires') or {}), check=spec.get('check'), can_provide=spec.get('can_provide'),
               pay_to=spec.get('pay_to') or 'wallet', note_hint=str(spec.get('note_hint') or '')[:80], legacy=legacy,
               note_check=spec.get('note_check'))
    if not 0 <= out['floor'] <= PRICE_CEIL or not 1 <= out['max_price'] <= PRICE_CEIL:
        raise ValueError(f'service_market.register {key}: floor / max_price')
    if legacy:
        out['max_price'] = min(out['max_price'], LEGACY_MAX)
    if not 1 <= out['qty_max'] <= QTY_CEIL or not 1 <= out['work_hours'] <= 24 * 30 or not 1 <= out['duration'] <= 24 * 60 * 30:
        raise ValueError(f'service_market.register {key}: qty_max / work_hours / duration')
    if out['confirm'] not in ('auto', 'buyer') or out['pay_to'] not in ('wallet', 'career'):
        raise ValueError(f'service_market.register {key}: confirm / pay_to')
    if set(out['requires']) - REQUIRES:
        raise ValueError(f'service_market.register {key}: requires keys {sorted(set(out["requires"]) - REQUIRES)}')
    for k in ('deliver', 'on_buyer', 'on_provider', 'check', 'can_provide', 'note_check'):
        if out[k] is not None and not callable(out[k]):
            raise ValueError(f'service_market.register {key}: {k} must be callable')
    if out['confirm'] == 'auto' and out['deliver'] is None and not legacy:
        raise ValueError(f'service_market.register {key}: confirm auto needs deliver')
    own = spec.get('open')
    out.update(open=_link(key, 'open', own) if own is not None else None,
               setup=_link(key, 'setup', spec['setup']) if spec.get('setup') is not None else None,
               providers=spec.get('providers'), offer=spec.get('offer'))
    if own is not None:
        bad = sorted(k for k in OWN_FORBIDDEN if spec.get(k) is not None)
        if bad:
            raise ValueError(f'service_market.register {key}: an own-flow listing (open) never uses the escrow: {bad}')
        if not callable(out['providers']) or not callable(out['offer']):
            raise ValueError(f'service_market.register {key}: open needs callable providers and offer')
        if out['qty_max'] != 1:
            raise ValueError(f'service_market.register {key}: an own-flow listing has qty_max 1')
    elif any(spec.get(k) is not None for k in ('providers', 'offer', 'setup')):
        raise ValueError(f'service_market.register {key}: providers / offer / setup belong to an own-flow listing (open)')
    return out


def _link(key, name, v) -> dict:
    """{action, data, label} of an own-flow listing: a client action and its plain data (validated: it reaches the client)."""
    if not isinstance(v, dict) or set(v) - {'action', 'data', 'label'}:
        raise ValueError(f'service_market.register {key}: {name} must be {{action, data, label}}')
    action, data, label = v.get('action'), v.get('data') or {}, v.get('label') or ''
    if not isinstance(action, str) or not ACTION_RX.fullmatch(action):
        raise ValueError(f'service_market.register {key}: {name}.action')
    if not isinstance(data, dict) or not all(isinstance(k, str) and LINK_KEY_RX.fullmatch(k) and _plain(x) for k, x in data.items()):
        raise ValueError(f'service_market.register {key}: {name}.data must map short ids to str / int / bool')
    if not isinstance(label, str) or len(label) > 40:
        raise ValueError(f'service_market.register {key}: {name}.label')
    return dict(action=action, data=dict(data), label=label)


def _plain(x) -> bool:
    return type(x) in (bool, int) or (isinstance(x, str) and len(x) <= 80)


def is_own(spec: dict | None) -> bool:
    """An own-flow listing: the module books, holds and pays; this market only lists it."""
    return bool(spec and spec.get('open'))


def _seed() -> None:
    """The legacy workplace orders (game/player_service_tasks.py): one 'job' service per career with a player order,
    and the quầy dishes. Registered on first use (no import cycle with the engine)."""
    if _seeded[0]:
        return
    _seeded[0] = True
    from .workplace_business import ORDERS
    from .content import CAREER_META
    for career in ORDERS:
        if (career, 'job') in REGISTRY:
            continue
        meta = CAREER_META.get(career, {})
        REGISTRY[(career, 'job')] = _norm((career, 'job'), dict(
            name='Đơn khách riêng', icon='🧾', desc=str(meta.get('short') or career)[:160], legacy='career',
            base=_legacy_base(career), unit='đơn', duration=10, can_provide=_career_started(career)))
    from . import restore_service   # noqa: F401  🧰 its services register at import: every process that settles knows its on_buyer
    from . import moto_service, vet_service   # noqa: F401  🏍️ 🩺 the same (bảo dưỡng xe, khám / tiêm thú cưng)
    if ('quay', 'dish') not in REGISTRY:
        REGISTRY[('quay', 'dish')] = _norm(('quay', 'dish'), dict(
            name='Món ở quầy', icon='🏪', desc='Quầy của bạn', legacy='quay', base=_legacy_base('quay'), unit='món',
            duration=5, can_provide=_has_stall))
    install_own()
    import os
    if os.environ.get('MNL_SVC_DEMO') == '1':   # dev only (scripts/browser_service_market.py): one generic service to walk through
        REGISTRY.setdefault(('milk_tea', 'tra_tai_nha'), _norm(('milk_tea', 'tra_tai_nha'), dict(
            name='Pha trà tại nhà', icon='🧋', desc='Mang trà tới nhà, pha tại chỗ', base=1000, unit='lượt', qty_max=3)))


def install_own(strict: bool = False) -> bool:
    """The own-flow listings (🏥 birth rooms, 📸 photographers): their modules register them here (also called by
    server.py at start). A spec this registry refuses is logged, never a crash; strict=True (tests) raises it."""
    from . import birth, photo_studio
    ok = birth.install(strict=strict)
    return photo_studio.install(strict=strict) and ok


def _legacy_base(career):
    def base(db, provider):
        kind, target = ('quay', None) if career == 'quay' else ('career', career)
        sql = 'SELECT data FROM work_visit_places WHERE owner=? AND kind=?' + (' AND target=?' if target else '')
        rows = db.execute(sql + ' LIMIT 8', (provider, kind) + ((target,) if target else ())).fetchall()
        prices = [o['price'] for r in rows for o in (_data(dict(r)).get('offers') or []) if type(o.get('price')) is int and o['price'] > 0]
        if prices:
            return min(prices)
        if career != 'quay':
            from .workplace_business import ORDERS
            return ORDERS[career][1] if career in ORDERS else 1
        return 1
    return base


def _career_started(career):
    def ok(state):
        c = (state.get('careers') or {}).get(career)
        return '' if isinstance(c, dict) and c.get('started') else 'Bạn cần làm nghề này trước đã.'
    return ok


def _has_stall(state):
    from . import quay
    return '' if (quay.get(state) or {}).get('stalls') else 'Bạn cần có quầy trước đã.'


def specs() -> dict:
    _seed()
    return REGISTRY


def get_spec(career: str, service: str) -> dict | None:
    _seed()
    return REGISTRY.get((career, service))


def legacy_key(kind: str, career: str) -> tuple:
    """The registry key of a legacy workplace place: (career, 'job') or ('quay', 'dish')."""
    return ('quay', 'dish') if kind == 'quay' else (career, 'job')


def public_spec(spec: dict) -> dict:
    return {k: spec[k] for k in ('career', 'service', 'name', 'icon', 'desc', 'unit', 'duration', 'floor', 'max_price',
                                 'qty_max', 'confirm', 'note_hint')} | dict(legacy=spec['legacy'] or '', requires=spec['requires'],
                                                                           own=is_own(spec))


def catalog() -> dict:
    """Every registered service (the client's filter list), with the market's rules."""
    from .content import CAREER_META
    rows = []
    for (career, service), sp in sorted(specs().items()):
        meta = CAREER_META.get(career, {})
        rows.append(public_spec(sp) | dict(career_name=str(meta.get('short') or ('Quầy' if career == 'quay' else career))))
    return dict(services=rows, rules=rules())


def rules() -> dict:
    return dict(fee_pct=FEE_PCT, default_mult=DEFAULT_MULT, mult_min=MULT_MIN, mult_max=MULT_MAX, max_price=MAX_PRICE,
                legacy_max=LEGACY_MAX, max_rounds=MAX_ROUNDS, talk_hours=TALK_HOURS, hold_hours=HOLD_HOURS,
                confirm_hours=CONFIRM_HOURS, flag_hours=FLAG_HOURS, pair_day=PAIR_DAY, pair_week_xu=PAIR_WEEK_XU,
                net_days=NET_DAYS, new_days=7)


# ---------------------------------------------------------------- prices
def base_of(spec: dict, db, provider: str) -> int:
    b = spec['base']
    v = b(db, provider) if callable(b) else b
    return max(1, min(PRICE_CEIL, int(v or 1)))


def bounds(spec: dict, base: int, qty: int = 1) -> tuple:
    """(lowest, highest) price of an order of `qty` units: per unit max(floor, base) … min(base × 10, max_price / qty)."""
    lo = max(int(spec['floor']), int(base), 1)
    hi = min(int(base) * MULT_MAX, int(spec['max_price']) // max(1, qty))
    hi = max(hi, lo)
    return lo * qty, hi * qty


def unit_price(spec: dict, base: int, mult: int) -> int:
    lo, hi = bounds(spec, base, 1)
    return max(lo, min(hi, int(base) * int(mult)))


def _setting(db, provider: str, career: str, service: str) -> dict | None:
    r = db.execute('SELECT * FROM svc_settings WHERE provider=? AND career=? AND service=?', (provider, career, service)).fetchone()
    return dict(r) if r else None


def fair_pct(db, provider: str, career: str) -> int:
    """🎪 Hội chợ việc làm (game/town_fair.py): the discount (percent) this provider's booth gives on their fixed prices of
    `career` while a fair is on; 0 otherwise (no query outside a fair)."""
    from . import town_fair
    return town_fair.discount(db, provider, career)


def _fair_unit(db, spec: dict, provider: str, career: str, base: int, unit: int) -> tuple:
    """(unit price, percent applied): the fair's percent off, never below the lowest unit price (floor / NPC base)."""
    pct = fair_pct(db, provider, career)
    if not pct:
        return unit, 0
    from . import town_fair
    lo = bounds(spec, base, 1)[0]
    cut = town_fair.apply_pct(unit, lo, pct)
    return cut, (pct if cut < unit else 0)


def quote(db, provider: str, career: str, service: str, qty: int = 1, setting=None, base=None) -> dict:
    """What this provider asks for `qty` units: {base, mult, mode, price (None while thương lượng), lo, hi, on, fair (🎪
    percent off while the provider's fair booth is open, else 0), usual (the price without it)}."""
    spec = get_spec(career, service)
    need(spec, 'Dịch vụ này chưa có.', 'unknown_service', 404)
    need(not is_own(spec), OWN_TEXT, 'own_flow', 409)
    row = setting if setting is not None else _setting(db, provider, career, service)
    base = base_of(spec, db, provider) if base is None else base
    mode, mult = (row['mode'], int(row['mult'])) if row else ('fixed', DEFAULT_MULT)
    mult = max(MULT_MIN, min(MULT_MAX, mult))
    lo, hi = bounds(spec, base, qty)
    price, fair, usual = None, 0, None
    if mode != 'nego':
        unit = unit_price(spec, base, mult)
        cut, fair = _fair_unit(db, spec, provider, career, base, unit)
        price, usual = cut * qty, unit * qty
    return dict(base=base, mult=mult, mode=mode, price=price, lo=lo, hi=hi, qty=qty, on=bool(row and row['on_']), fair=fair, usual=usual)


def legacy_quote(db, provider: str, kind: str, career: str, base: int) -> dict:
    """A legacy workplace offer of NPC price `base` sold to a player: {price, base, mult, mode, listed}."""
    key = legacy_key(kind, career)
    spec = get_spec(*key) or _norm(key, dict(name='Đơn', base=1, legacy='career'))
    row = _setting(db, provider, *key)
    mode, mult = (row['mode'], int(row['mult'])) if row else ('fixed', DEFAULT_MULT)
    mult = max(MULT_MIN, min(MULT_MAX, mult))
    lo, hi = bounds(spec, base, 1)
    price, fair, usual = None, 0, None
    if mode != 'nego':
        usual = unit_price(spec, base, mult)
        price, fair = _fair_unit(db, spec, provider, key[0], base, usual) if key[0] != 'quay' else (usual, 0)
    return dict(price=price, base=base, mult=mult, mode=mode, lo=lo, hi=hi, listed=bool(row and row['on_']), career=key[0], service=key[1],
                fee_pct=FEE_PCT, fair=fair, usual=usual)


def listed(db, place: dict) -> bool:
    """A legacy place whose owner put its service in Phố dịch vụ: anyone may order there (its visibility aside)."""
    if not place:
        return False
    key = legacy_key(place['kind'], place['target'])
    return bool(db.execute('SELECT 1 FROM svc_settings WHERE provider=? AND career=? AND service=? AND on_=1',
                           (place['owner'], key[0], key[1])).fetchone())


def decorate_offers(db, owner: str, kind: str, career: str, offers: list, cache: dict | None = None) -> list:
    """The place's offers as a player buyer sees them: price × the provider's multiplier (or 🤝 nego), base kept."""
    key = (owner, kind, career)
    out = []
    for o in offers or []:
        if not isinstance(o, dict) or type(o.get('price')) is not int:
            continue
        ck = key + (o['price'],)
        q = cache.get(ck) if cache is not None else None
        if q is None:
            q = legacy_quote(db, owner, kind, o.get('career') or career, o['price'])
            if cache is not None:
                cache[ck] = q
        out.append(dict(o, base=o['price'], price=q['price'] if q['price'] is not None else q['lo'], mult=q['mult'],
                        nego=q['mode'] == 'nego', lo=q['lo'], hi=q['hi'], fee_pct=FEE_PCT, fair=q.get('fair', 0),
                        usual=q['usual'] if q.get('usual') is not None else (q['price'] if q['price'] is not None else q['lo'])))
    return out


# ---------------------------------------------------------------- people
GONE = dict(pid='', name='Người chơi đã rời', code='', avatar='🙂', fc='')


def _person(db, sid: str) -> dict:
    from . import work_visits
    if not db.execute('SELECT 1 FROM sessions WHERE sid=?', (sid,)).fetchone():
        return dict(GONE)
    return work_visits._person(db, sid)


def _people(db, sids, into: dict | None = None) -> dict:
    """{sid: _person(db, sid)} for many players in three queries (a page of cards or orders), the same dicts."""
    out = {} if into is None else into
    want = sorted({s for s in sids if s and s not in out})
    if not want:
        return out
    marks = ','.join('?' * len(want))
    rows = {r['sid']: dict(r) for r in db.execute(
        f'SELECT s.sid, p.name, p.avatar, m.code, a.sid AS asid, a.display FROM sessions s LEFT JOIN profiles p ON p.sid=s.sid '
        f'LEFT JOIN marriage_people m ON m.sid=s.sid LEFT JOIN accounts a ON a.sid=s.sid WHERE s.sid IN ({marks})', tuple(want)).fetchall()}
    pids = {s: _pid(s) for s in rows}
    faces = {}
    if pids:
        pm = ','.join('?' * len(pids))
        faces = {r['pid']: r['code'] for r in db.execute(f'SELECT pid, code FROM chat_faces WHERE pid IN ({pm})', tuple(pids.values())).fetchall()}
    for s in want:
        r = rows.get(s)
        if r is None:
            out[s] = dict(GONE)
            continue
        shown = mr._clean_name(r['display']) if r['asid'] else 'Một người chơi'
        out[s] = dict(pid=pids[s], name=str(r['name'] or shown)[:40], code=r['code'] or '', avatar=str(r['avatar'] or '🙂')[:80],
                      fc=str(faces.get(pids[s]) or '')[:100])
    return out


def _resolve(db, pid) -> str | None:
    need(isinstance(pid, str) and re.fullmatch(r'[0-9a-f]{16}', pid), 'Không tìm thấy người này.', 'not_found', 404)
    r = db.execute('SELECT provider FROM svc_settings WHERE pid=? LIMIT 1', (pid,)).fetchone()
    if r:
        return r['provider']
    from . import work_visits
    return work_visits._resolve(db, pid)


def _blocked(db, a: str, b: str) -> bool:
    from . import work_visits
    return work_visits._blocked(db, a, b)


def _spouses(db, a: str, b: str) -> bool:
    c = mr._bond(db, a)
    return bool(c and c.get('status') == 'married' and {c['a'], c['b']} == {a, b})


def _online(db, sids, t=None) -> set:
    sids = [s for s in set(sids) if s]
    if not sids:
        return set()
    from .wedding_live import vn_day
    t = now() if t is None else t
    marks = ','.join('?' * len(sids))
    rows = db.execute(f'SELECT sid FROM stat_play WHERE day=? AND sid IN ({marks}) AND last_at>?', (vn_day(t), *sids, t - ONLINE_SECONDS)).fetchall()
    return {r['sid'] for r in rows}


def _account(db, sid: str):
    return db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone()


def _old(db, sid: str, days: int, t=None) -> bool:
    r = _account(db, sid)
    t = now() if t is None else t
    return bool(r) and str(r['created_at']) <= time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t - days * DAY))


# ---------------------------------------------------------------- networks
def net_tags(ip: str) -> tuple:
    """(lixi-style tag, pet-arena-style tag) of a request's address: keyed hashes, never the address."""
    from . import lixi, pet_arena
    return lixi.ip_tag(ip or ''), pet_arena.ip_tag(ip or '')


def record_net(db, sid: str, ip: str, t=None) -> None:
    tag = net_tags(ip)[0]
    if sid and tag:
        db.execute('INSERT INTO svc_net(sid,tag,at) VALUES(?,?,?) ON CONFLICT(sid,tag) DO UPDATE SET at=excluded.at',
                   (sid, tag, now() if t is None else t))


def same_net(db, a: str, b: str, ip: str = '', actor: str = '', t=None) -> bool:
    """Were `a` and `b` seen on one network within NET_DAYS (svc_net, lixi_grabs, pet_arena; the actor's address now)?"""
    t = now() if t is None else t
    cut = t - NET_DAYS * DAY

    def tags(sid):
        out = {r['tag'] for r in db.execute('SELECT tag FROM svc_net WHERE sid=? AND at>?', (sid, cut)).fetchall()}
        out |= {r['ip'] for r in db.execute("SELECT DISTINCT ip FROM lixi_grabs WHERE sid=? AND at>? AND ip<>''", (sid, cut)).fetchall()}
        return out
    ta, tb = tags(a), tags(b)
    lx, pa = net_tags(ip)
    if actor in (a, b) and lx:
        (ta if actor == a else tb).add(lx)
    if ta & tb:
        return True
    if actor in (a, b) and pa:
        other = b if actor == a else a
        r = db.execute("SELECT ip FROM pet_arena WHERE sid=? AND at>? AND ip<>''", (other, cut)).fetchone()
        if r and r['ip'] == pa:
            return True
    return False


# ---------------------------------------------------------------- the guard
def _day_start(t: float) -> float:
    from .wedding_live import vn
    return vn(t).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def pair_usage(db, buyer: str, provider: str, t=None) -> dict:
    """{day: deals today, week: xu this week} between this buyer and this provider (both kinds of orders, escrowed)."""
    from .wedding_live import week_start
    t = now() if t is None else t
    d0, w0 = _day_start(t), min(week_start(t), _day_start(t))
    m1, m2 = ','.join('?' * len(MONEY)), ','.join('?' * len(WO_MONEY))
    a = db.execute(f'SELECT COUNT(*) FILTER (WHERE held_at>=?) AS n, COALESCE(SUM(price),0) AS xu FROM svc_orders '
                   f'WHERE buyer=? AND provider=? AND kind=\'svc\' AND held_at>=? AND status IN ({m1})', (d0, buyer, provider, w0, *MONEY)).fetchone()
    b = db.execute(f'SELECT COUNT(*) FILTER (WHERE created_at>=?) AS n, COALESCE(SUM(price),0) AS xu FROM work_service_orders '
                   f'WHERE customer=? AND provider=? AND created_at>=? AND status IN ({m2})', (d0, buyer, provider, w0, *WO_MONEY)).fetchone()
    # 🏥 a player birth room paid by this buyer (game/birth.py: its own escrow; booked, staying or born count)
    c = db.execute("SELECT COUNT(*) FILTER (WHERE at>=?) AS n, COALESCE(SUM(price),0) AS xu FROM birth_stays WHERE payer=? AND provider_sid=? "
                   "AND provider='room' AND at>=? AND status IN ('booked','staying','born')", (d0, buyer, provider, w0)).fetchone()
    return dict(day=int(a['n'] or 0) + int(b['n'] or 0) + int(c['n'] or 0), week=int(a['xu'] or 0) + int(b['xu'] or 0) + int(c['xu'] or 0))


def week_cap(spec: dict | None) -> int:
    """PAIR_WEEK_XU; a service that declares a max price above MAX_PRICE allows one such order a week."""
    top = int(spec['max_price']) if spec else 0
    return max(PAIR_WEEK_XU, top) if top > MAX_PRICE else PAIR_WEEK_XU


def guard(db, buyer: str, provider: str, price: int, spec: dict | None, ip: str = '', actor: str = '', money: bool = True, t=None) -> dict:
    """Every anti-laundering rule for `buyer` paying `price` to `provider` (module docstring). money=True: inside the
    transaction that moves it (the pair's advisory lock, the new-account day counter); False: a check for a clear answer."""
    t = now() if t is None else t
    need(buyer != provider, 'Không tự đặt dịch vụ của chính mình được.', 'self')
    need(_account(db, buyer) and _account(db, provider), 'Cả hai cần có tài khoản đăng nhập.', 'login_required', 401)
    need(not _blocked(db, buyer, provider), 'Không thể giao dịch với người này.', 'blocked', 403)
    spouse = _spouses(db, buyer, provider)
    if not spouse:
        need(not same_net(db, buyer, provider, ip, actor, t), 'Hai tài khoản cùng một mạng không giao dịch với nhau được.', 'same_net', 403)
    need(type(price) is int and 1 <= price <= (int(spec['max_price']) if spec else MAX_PRICE), 'Giá vượt mức tối đa của một đơn.', 'too_much')
    if money:
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))', ('svc-pair:' + buyer + '|' + provider,))
    use = pair_usage(db, buyer, provider, t)
    need(use['day'] < PAIR_DAY, f'Hôm nay hai bạn đã giao dịch {PAIR_DAY} đơn rồi. Mai đặt tiếp nhé.', 'pair_day', 409)
    cap = week_cap(spec)
    need(use['week'] + price <= cap, f'Tuần này hai bạn chỉ còn giao dịch được {fmt(max(0, cap - use["week"]))} xu.', 'pair_week', 409)
    if money:
        from . import bank_xfer
        bank_xfer.count_out(db, buyer, price)
    else:
        from . import bank_xfer
        bank_xfer.check_out(db, buyer, price)
    return dict(spouse=spouse, use=use)


# ---------------------------------------------------------------- money in the saves
def _have(s: dict) -> int:
    from . import bank as bk
    j = s['journey']
    b = bk.get(s)
    return max(0, j['wallet']) + (b['balance'] if b else 0)


def debit(s: dict, amount: int, label: str) -> str:
    """`amount` from the wallet (rows ≤ ROW_MAX), then the bank account; never into debt. Where it came from."""
    from . import bank as bk
    from . import journey as jr
    j = s.get('journey') if isinstance(s.get('journey'), dict) else {}
    need(j.get('story'), 'Phố dịch vụ dùng ví hành trình.', 'not_story')
    need(j['wallet'] >= 0, f'Ví đang nợ {fmt(-j["wallet"])} xu. Trả nợ trước nhé.', 'in_debt')
    have = _have(s)
    need(have >= amount, f'Còn thiếu {fmt(amount - have)} xu (ví và tài khoản).', 'no_money')
    cash = min(j['wallet'], amount)
    left = cash
    while left > 0:
        part = min(left, ROW_MAX)
        jr._wallet(j, -part, OUT_KIND, label[:120])
        left -= part
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label[:120], -rest)
    return 'both' if rest and cash else 'bank' if rest else 'cash'


def credit(s: dict, amount: int, label: str, kind: str = IN_KIND, career: str | None = None) -> None:
    """`amount` into the wallet (rows ≤ ROW_MAX) up to its maximum, the rest into the bank account."""
    from . import bank as bk
    from . import journey as jr
    j = s.get('journey') if isinstance(s.get('journey'), dict) else None
    need(j is not None and 'wallet' in j, 'Không tìm thấy ví của người chơi.', 'no_wallet', 409)
    room = max(0, jr.WALLET_MAX - j['wallet'])
    cash = min(room, amount)
    rest = amount - cash
    b = bk.get(s) if rest else None
    # checked before anything moves: a refusal leaves the save exactly as it was (a caller may fall back elsewhere)
    need(not rest or (b is not None and b['balance'] + rest <= bk.BAL_MAX), 'Ví và tài khoản đã đầy. Tiêu bớt rồi nhận tiền nhé.', 'full', 409)
    left = cash
    while left > 0:
        part = min(left, ROW_MAX)
        jr._wallet(j, part, kind, label[:120], career)
        left -= part
    if rest:
        b['balance'] += rest
        bk._log(b, j['life_day'], 'acc', label[:120], rest)


def _pay_provider(s: dict, spec: dict | None, order: dict, paid: int, label: str) -> None:
    c = (s.get('careers') or {}).get(order['career'])
    started = isinstance(c, dict) and bool(c.get('started'))
    if spec and spec['pay_to'] == 'career' and started:
        from . import engine
        engine.money(s, c, paid, label, order['id'], 'revenue')
        return
    try:
        credit(s, paid, label, IN_KIND, order['career'] if order['career'] in (s.get('careers') or {}) else None)
    except ServiceError as e:
        if e.code != 'full' or not started:
            raise
        from . import engine   # the wallet and the bank account are full: the career's fund takes it (never lost, never stuck)
        engine.money(s, c, paid, label, order['id'], 'revenue')


def _requires_why(spec: dict, state: dict, db=None, buyer: str = '') -> str:
    r = spec['requires']
    j = state.get('journey') if isinstance(state.get('journey'), dict) else {}
    if r.get('story') and not j.get('story'):
        return 'Dịch vụ này cần chơi hành trình.'
    if r.get('life_day') and int(j.get('life_day') or 0) < int(r['life_day']):
        return f'Dịch vụ này cần từ ngày sống thứ {int(r["life_day"])}.'
    if r.get('chapter') and int(j.get('chapter') or 0) < int(r['chapter']):
        return f'Dịch vụ này cần tới chương {int(r["chapter"])}.'
    if r.get('married') and ((state.get('marriage') or {}).get('spouse') or {}).get('status') != 'married':
        return 'Dịch vụ này dành cho người đã kết hôn.'
    if spec['check'] and db is not None:
        why = spec['check'](db, buyer, state)
        if why:
            return str(why)[:200]
    return ''


# ---------------------------------------------------------------- views
def _order_dict(row: dict) -> dict:
    """The order as a career hook sees it."""
    d = _data(row)
    return dict(id=row['id'], career=row['career'], service=row['service'], buyer=row['buyer'], provider=row['provider'],
                buyer_pid=_pid(row['buyer']), provider_pid=_pid(row['provider']), qty=int(row['qty']), price=int(row['price']),
                fee=int(row['fee']), paid=int(row['paid']), note=d.get('note', ''), input=d.get('input'), result=d.get('result'),
                created_at=row['created_at'])


def _actions(row: dict, me: str, t: float, rated: bool, flagged: bool) -> list:
    role = 'buyer' if row['buyer'] == me else 'provider'
    st = row['status']
    if st == 'talk':
        mine = row['ask_by'] != role
        out = ['accept'] + (['counter'] if int(row['rounds']) < MAX_ROUNDS else []) if mine else []
        return out + (['cancel'] if role == 'buyer' else ['decline'])
    if st == 'held':
        return ['cancel'] if role == 'buyer' else ['take', 'decline']
    if st == 'working':
        return [] if role == 'buyer' else ['done', 'decline']
    if st == 'delivered':
        return (['confirm'] + ([] if flagged else ['flag'])) if role == 'buyer' else []
    if st == 'done' and role == 'buyer':
        late = (row['delivered_at'] or row['done_at'] or 0) + FLAG_HOURS * HOUR < t
        return ([] if rated else ['rate']) + ([] if flagged or late else ['flag'])
    return []


def _marks(db, ids) -> tuple:
    """(rated ids, flagged ids) among these orders: two queries for a whole inbox page."""
    ids = [i for i in ids if i]
    if not ids:
        return set(), set()
    marks = ','.join('?' * len(ids))
    rated = {r['order_id'] for r in db.execute(f'SELECT order_id FROM svc_reviews WHERE order_id IN ({marks})', tuple(ids)).fetchall()}
    flagged = {r['order_id'] for r in db.execute(f'SELECT order_id FROM svc_flags WHERE order_id IN ({marks})', tuple(ids)).fetchall()}
    return rated, flagged


def _view(db, row: dict, me: str, people: dict | None = None, t=None, marks: tuple | None = None) -> dict:
    """An order as `me` sees it. `people` ({sid: person}) and `marks` (_marks of the page) spare the per-row queries."""
    t = now() if t is None else t
    d = _data(row)
    spec = get_spec(row['career'], row['service'])
    role = 'buyer' if row['buyer'] == me else 'provider'
    other = row['provider'] if role == 'buyer' else row['buyer']
    people = {} if people is None else people
    if other not in people:
        people[other] = _person(db, other)
    if marks is None:
        marks = _marks(db, [row['id']])
    rated, flagged = row['id'] in marks[0], row['id'] in marks[1]
    return dict(id=row['id'], kind=row['kind'], career=row['career'], service=row['service'], name=d.get('name') or (spec or {}).get('name', ''),
                icon=d.get('icon') or (spec or {}).get('icon', '🛎️'), unit=d.get('unit') or (spec or {}).get('unit', ''),
                label=d.get('label', ''), qty=int(row['qty']), status=row['status'], role=role, other=people[other],
                price=int(row['price']), ask=int(row['ask']), ask_by=row['ask_by'], rounds=int(row['rounds']), max_rounds=MAX_ROUNDS,
                base=int(row['base']), mult=int(row['mult']), fee=int(row['fee']) or fee_of(int(row['price'] or row['ask'])),
                paid=int(row['paid']), lo=int(d.get('lo') or 0), hi=int(d.get('hi') or 0), note=d.get('note', ''),
                result=d.get('result') if isinstance(d.get('result'), dict) else None, why=d.get('why', ''),
                created_at=row['created_at'], updated_at=row['updated_at'], due_at=row['due_at'], link=row['link'],
                actions=_actions(row, me, t, rated, flagged), rated=rated, flagged=flagged,
                stuck=str(d.get('stuck') or '') if row['status'] in ('ready', 'refund') else '')


def _rep_row(db, provider: str) -> dict:
    r = db.execute('SELECT * FROM svc_rep WHERE provider=?', (provider,)).fetchone()
    if r:
        return dict(r)
    # first look: the legacy workplace history counts (no backfill at deploy; this is written once, here)
    w = db.execute("SELECT COUNT(*) AS n, COALESCE(SUM(stars),0) AS s FROM work_service_reviews WHERE provider=?", (provider,)).fetchone()
    o = db.execute("SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS xu FROM work_service_orders WHERE provider=? AND status='completed'", (provider,)).fetchone()
    row = dict(provider=provider, n=int(w['n'] or 0), stars=int(w['s'] or 0), deals=int(o['n'] or 0), xu=int(o['xu'] or 0), updated_at=now())
    return row


def _rep_save(db, row: dict) -> None:
    db.execute('INSERT INTO svc_rep(provider,n,stars,deals,xu,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(provider) DO UPDATE SET '
               'n=excluded.n,stars=excluded.stars,deals=excluded.deals,xu=excluded.xu,updated_at=excluded.updated_at',
               (row['provider'], row['n'], row['stars'], row['deals'], row['xu'], row['updated_at']))


def _rep_add(db, provider: str, deals: int = 0, xu: int = 0, stars: int | None = None) -> None:
    db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))', ('svc-rep:' + provider,))
    if deals:
        _regs_forget(provider)
    row = _rep_row(db, provider)
    row.update(deals=row['deals'] + deals, xu=row['xu'] + xu, updated_at=now())
    if stars is not None:
        row.update(n=row['n'] + 1, stars=row['stars'] + stars)
    _rep_save(db, row)


def rep_legacy_done(db, provider: str, price: int) -> None:
    """A legacy workplace order just completed (work_visits._settle_one, its transaction): one more deal. A provider
    with no reputation row yet gets one counted from the legacy tables, this order included."""
    db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))', ('svc-rep:' + provider,))
    _regs_forget(provider)
    if db.execute('SELECT 1 FROM svc_rep WHERE provider=?', (provider,)).fetchone():
        _rep_add(db, provider, deals=1, xu=int(price))
    else:
        _rep_save(db, _rep_row(db, provider))


_regs: dict = {}
_regs_lock = threading.Lock()


def _regs_forget(provider: str) -> None:
    """A deal of this provider completed in this process: its khách quen count is read again next time."""
    with _regs_lock:
        _regs.pop(provider, None)


def regulars_count(db, provider: str, t=None) -> int:
    """How many khách quen (at most 50), kept REG_TTL seconds per provider (at most REG_MAX providers): the
    aggregate walks every completed order of the provider, too heavy for each card view."""
    t = now() if t is None else t
    with _regs_lock:
        hit = _regs.get(provider)
        if hit and 0 <= t - hit[0] < REG_TTL:
            return hit[1]
    n = len(regulars(db, provider, 50))
    with _regs_lock:
        if len(_regs) >= REG_MAX:
            for k in sorted(_regs, key=lambda k: _regs[k][0])[:REG_MAX // 4]:   # the oldest quarter goes
                _regs.pop(k, None)
        _regs[provider] = (t, n)
    return n


def rep_view(db, provider: str, regs: int | None = None) -> dict:
    r = _rep_row(db, provider)
    n = int(r['n'])
    return dict(n=n, avg=round(r['stars'] / n, 2) if n else 0.0, deals=int(r['deals']),
                regulars=regulars_count(db, provider) if regs is None else regs)


def regulars(db, provider: str, limit: int = 10) -> list:
    """🤝 Khách quen: buyers with at least two completed deals with this provider (both kinds), most first."""
    rows = db.execute("SELECT buyer, SUM(n) AS n FROM (SELECT buyer, COUNT(*) AS n FROM svc_orders WHERE provider=? AND status='done' GROUP BY buyer "
                      "UNION ALL SELECT customer AS buyer, COUNT(*) AS n FROM work_service_orders WHERE provider=? AND status='completed' GROUP BY customer) x "
                      'GROUP BY buyer HAVING SUM(n)>=2 ORDER BY SUM(n) DESC, buyer LIMIT ?', (provider, provider, limit)).fetchall()
    return [dict(sid=r['buyer'], n=int(r['n'])) for r in rows]


def alert_count(db, sid: str) -> int:
    """What waits for this player's answer: talks on their turn, paid orders to take, deliveries to confirm, and
    legacy workplace requests (the ticker's badge)."""
    r = db.execute("SELECT COUNT(*) AS n FROM svc_orders WHERE (provider=? AND ((status='talk' AND ask_by='buyer') OR status='held')) "
                   "OR (buyer=? AND ((status='talk' AND ask_by='provider') OR status='delivered'))", (sid, sid)).fetchone()
    w = db.execute("SELECT COUNT(*) AS n FROM work_service_orders WHERE provider=? AND status='requested'", (sid,)).fetchone()
    return int(r['n'] or 0) + int(w['n'] or 0)


# ---------------------------------------------------------------- state machine: DB-only steps
class _Replay(Exception):
    """Another worker moved the row first."""


def _flip(db, oid: str, old, new: str, t: float, **cols) -> bool:
    olds = (old,) if isinstance(old, str) else tuple(old)
    sets = ','.join(f'{k}=?' for k in cols)
    marks = ','.join('?' * len(olds))
    n = db.execute(f'UPDATE svc_orders SET status=?,updated_at=?{"," + sets if sets else ""} WHERE id=? AND status IN ({marks})',
                   (new, t, *cols.values(), oid, *olds)).rowcount
    return n == 1


def _set_data(db, oid: str, data: dict) -> None:
    db.execute('UPDATE svc_orders SET data=? WHERE id=?', (_json(data), oid))


def _due_step(store, row: dict, t: float) -> bool:
    """One timer: a talk expires, a paid order nobody took or a late one is refunded, a delivery is confirmed."""
    st = row['status']

    def run(db):
        cur = db.execute('SELECT * FROM svc_orders WHERE id=? FOR UPDATE', (row['id'],)).fetchone()
        if not cur or cur['status'] != st or cur['due_at'] is None or cur['due_at'] > t:
            return False
        cur = dict(cur)
        d = _data(cur)
        if st == 'talk':
            return _flip(db, cur['id'], 'talk', 'expired', t, due_at=None)
        if st in ('held', 'working'):
            d['why'] = 'expire' if st == 'held' else 'late'
            _set_data(db, cur['id'], d)
            return _flip(db, cur['id'], st, 'refund', t, due_at=t)
        if st == 'delivered':
            d['auto'] = True
            _set_data(db, cur['id'], d)
            return _flip(db, cur['id'], 'delivered', 'ready', t, due_at=t)
        return False
    if st not in ('talk', 'held', 'working', 'delivered'):
        return False
    return bool(store.transaction(run))


class _Later(Exception):
    """Not this build's to settle now (a service it does not know): the row waits, pushed back."""


def _settle_one(store, row: dict) -> bool:
    """The money step of a 'ready' (pay the provider, burn the fee) or 'refund' (the buyer's whole price back) order.
    A provider whose save is gone delivered the work: the buyer keeps it (on_buyer runs) and the payout is burned."""
    st = row['status']
    if st not in ('ready', 'refund') or row['kind'] != 'svc':
        return False
    t = now()
    spec = get_spec(row['career'], row['service'])
    order = _order_dict(row)
    price = int(row['price'])
    if st == 'ready':
        if spec is None:   # a newer build's service: its hooks (on_buyer…) are unknown here, never pay without them
            raise _Later()
        payee = row['provider']
        gone = not mr._read_state(store, payee)
        fee = price if gone else fee_of(price)
        paid = price - fee
        order.update(fee=fee, paid=paid)
        label = f'🛎️ Phố dịch vụ · {spec.get("name") or row["service"]}'

        def pay(s):
            _pay_provider(s, spec, order, paid, label)
            if spec['on_provider']:
                spec['on_provider'](s, copy.deepcopy(order))
        fns = {} if gone else {payee: pay}
        if spec['on_buyer'] and row['buyer'] != payee and mr._read_state(store, row['buyer']):
            fns[row['buyer']] = lambda s: spec['on_buyer'](s, copy.deepcopy(order))

        def finish(db):
            if not _flip(db, row['id'], 'ready', 'done', t, fee=fee, paid=paid, done_at=t, due_at=None):
                raise _Replay()
            if not gone:
                _rep_add(db, payee, deals=1, xu=price)
        if not fns:
            try:
                store.transaction(finish)
            except _Replay:
                return False
            return True
    else:
        payee = row['buyer']
        d = _data(row)
        if not mr._read_state(store, payee):     # the buyer left: nobody to refund (their save is gone)
            store.transaction(lambda db: _flip(db, row['id'], 'refund', 'refunded', t, due_at=None, done_at=t))
            return True
        label = f'↩️ Hoàn tiền Phố dịch vụ · {d.get("name") or row["service"]}'
        fns = {payee: lambda s: credit(s, price, label, OUT_KIND)}

        def finish(db):
            if not _flip(db, row['id'], 'refund', 'refunded', t, due_at=None, done_at=t):
                raise _Replay()
    try:
        mr._mutate_retry(store, fns, finish)
    except _Replay:
        return False
    return True


def _backoff(store, row: dict, code: str, later: bool = False) -> None:
    """A money step that failed (or is not this build's): the row waits RETRY_BASE_S × 2^tries (≤ RETRY_MAX_S) and the
    next rows go on. A full wallet and account: the payee is told once. Never raises."""
    d = _data(row)
    tries = int(d.get('tries') or 0) + 1
    d.update(tries=tries, stuck=code)
    wait = RETRY_MAX_S if later else min(RETRY_MAX_S, RETRY_BASE_S * 2 ** min(tries - 1, 12))
    payee = row['provider'] if row['status'] == 'ready' else row['buyer']

    def run(db):
        n = db.execute('UPDATE svc_orders SET due_at=?,data=? WHERE id=? AND status=? AND data=?',
                       (now() + wait, _json(d), row['id'], row['status'], row['data'])).rowcount
        if n and code == 'full' and tries == 1:
            mr._notice(db, payee, FULL_TEXT)
    try:
        store.transaction(run)
    except Exception:  # noqa: BLE001 - the next pass tries again
        LOG.exception('🛎️ svc backoff %s', row.get('id'))


def _guarded(store, row: dict, step) -> int:
    """One row's timer or money step; a failure is logged and pushed back, never raised (one bad row never blocks the rest)."""
    try:
        return int(bool(step(store, row)))
    except _Later:
        _backoff(store, row, 'unknown_service', later=True)
    except mr.MarriageError as e:
        if e.code == 'busy':   # the save moved on and on: simply the next pass
            return 0
        LOG.warning('🛎️ svc %s %s: %s %s', row.get('status'), row.get('id'), e.code, e)
        _backoff(store, row, e.code)
    except Exception as e:  # noqa: BLE001
        LOG.exception('🛎️ svc %s %s failed', row.get('status'), row.get('id'))
        _backoff(store, row, type(e).__name__[:40])
    return 0


def settle_for(store, sid: str | None = None, order_id: str | None = None, limit: int = 20) -> int:
    """Run the due timers and the money steps of this player's orders (all players' when sid is None). Row by row: a
    row that fails is logged and pushed back (_backoff), the others go on."""
    t = now()
    with store.connect() as db:
        where, args = 'due_at<=?', [t]
        if sid:
            where += ' AND (buyer=? OR provider=?)'
            args += [sid, sid]
        if order_id:
            where += ' AND id=?'
            args.append(order_id)
        rows = [dict(r) for r in db.execute(f"SELECT * FROM svc_orders WHERE {where} AND status IN ('talk','held','working','delivered','ready','refund') "
                                            'ORDER BY due_at,id LIMIT ?', (*args, limit)).fetchall()]
    n = 0
    for r in rows:
        if r['status'] in ('talk', 'held', 'working', 'delivered'):
            n += _guarded(store, r, lambda st, x: _due_step(st, x, t))
    with store.connect() as db:
        rows = [dict(r) for r in db.execute(f"SELECT * FROM svc_orders WHERE {where} AND status IN ('ready','refund') ORDER BY due_at,id LIMIT ?",
                                            (*args, limit)).fetchall()]
    for r in rows:
        n += _guarded(store, r, _settle_one)
    return n


def settle_quiet(store, sid: str | None = None, order_id: str | None = None, limit: int = 20) -> int:
    """settle_for for a read or after a step that already succeeded: never raises (a database hiccup is logged)."""
    try:
        return settle_for(store, sid, order_id, limit)
    except Exception:  # noqa: BLE001
        LOG.exception('🛎️ svc settle (%s, %s)', sid, order_id)
        return 0


_swept = [0.0]


def run_housekeeping(store, every: float = 60.0) -> int:
    """Timers and money steps for everyone (a provider is paid while both players are away). Guarded: exactly once."""
    t = now()
    if t - _swept[0] < every:
        return 0
    _swept[0] = t
    return settle_quiet(store, None, None, 50)


# ---------------------------------------------------------------- reading
def _actor(store, token) -> str:
    sid = store.key(token)
    with store.connect() as db:
        need(db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone(), 'Đăng nhập để dùng Phố dịch vụ.', 'login_required', 401)
    return sid


def _int(v, lo, hi, message='Số không hợp lệ.'):
    need(type(v) is int and lo <= v <= hi, message, 'bad_number')
    return v


SORTS = {
    'rating': '(COALESCE(r.stars,0)+9.0)/(COALESCE(r.n,0)+3) DESC, COALESCE(r.deals,0) DESC',
    'price': 's.price ASC, (COALESCE(r.stars,0)+9.0)/(COALESCE(r.n,0)+3) DESC',
    'online': '(COALESCE(p.last_at,0)>?) DESC, (COALESCE(r.stars,0)+9.0)/(COALESCE(r.n,0)+3) DESC',
    'deals': 'COALESCE(r.deals,0) DESC, (COALESCE(r.stars,0)+9.0)/(COALESCE(r.n,0)+3) DESC',
}


def _listing(db, s: dict, sid: str, t: float, online: set, places: dict) -> dict | None:
    spec = get_spec(s['career'], s['service'])
    if not spec:
        return None
    rep = dict(n=int(s.get('rn') or 0), avg=round(int(s.get('rs') or 0) / int(s['rn']), 2) if s.get('rn') else 0.0, deals=int(s.get('rd') or 0))
    out = dict(pid=s['pid'] or _pid(s['provider']), career=s['career'], service=s['service'], name=spec['name'], icon=spec['icon'],
               desc=spec['desc'], unit=spec['unit'], mode=s['mode'], mult=int(s['mult']), note=s['note'], rep=rep, note_hint=spec['note_hint'],
               online=s['provider'] in online, mine=s['provider'] == sid, legacy=spec['legacy'] or '', qty_max=spec['qty_max'])
    if spec['legacy']:
        rows = places.get(s['provider'], [])
        kind = 'quay' if spec['legacy'] == 'quay' else 'career'
        mine = [p for p in rows if p['kind'] == kind and (kind == 'quay' or p['target'] == s['career'])]
        offers = []
        for p in mine:
            data = _data(p)
            if not data.get('available'):
                continue
            for o in decorate_offers(db, s['provider'], kind, s['career'], data.get('offers') or []):
                offers.append(dict(o, place=p['id'], place_name=data.get('name', '')))
        out.update(place=mine[0]['id'] if mine else '', available=bool(offers), offers=offers[:6],
                   price=min((o['price'] for o in offers), default=int(s['price'] or 0)), fair=max((o.get('fair', 0) for o in offers), default=0),
                   lo=min((o['lo'] for o in offers), default=0), hi=max((o['hi'] for o in offers), default=0))
    else:
        q = quote(db, s['provider'], s['career'], s['service'], 1, setting=s)
        out.update(available=True, price=q['price'] if q['price'] is not None else q['lo'], lo=q['lo'], hi=q['hi'], base=q['base'],
                   fair=q['fair'], usual=q['usual'] if q['usual'] is not None else (q['price'] if q['price'] is not None else q['lo']))
    return out


def _own_rows(spec: dict, db, provider: str | None = None) -> list:
    """An own-flow listing's provider rows (normalized): all listed ones, or one provider's (listed or not)."""
    if provider is not None:
        got = spec['offer'](db, provider)
        rows = [got] if got else []
    else:
        rows = [dict(x, on=True) for x in (spec['providers'](db, LISTING_MAX, 0) or [])[:LISTING_MAX]]
    out = []
    for x in rows:
        if not isinstance(x, dict) or not isinstance(x.get('sid'), str) or type(x.get('price')) is not int or x['price'] < 1:
            continue
        data = {k: v for k, v in (x.get('data') or {}).items() if isinstance(k, str) and LINK_KEY_RX.fullmatch(k) and _plain(v)}
        out.append(dict(sid=x['sid'], price=min(int(x['price']), PRICE_CEIL), on=bool(x.get('on', True)), stars=max(0, int(x.get('stars') or 0)),
                        rated=max(0, int(x.get('rated') or 0)), deals=max(0, int(x.get('deals') or 0)), at=float(x.get('at') or 0),
                        data=data, title=str(x.get('title') or '')[:40], why=str(x.get('why') or '')[:160]))
    return out


def _own_item(spec: dict, x: dict, sid: str, online: set) -> dict:
    """A directory / provider card of an own-flow listing: the module's price and rating, a button to its own sheet."""
    rep = dict(n=x['rated'], avg=round(x['stars'] / x['rated'], 2) if x['rated'] else 0.0, deals=x['deals'])
    link = dict(spec['open'], data=dict(spec['open']['data'], **x['data']))
    return dict(pid=_pid(x['sid']), career=spec['career'], service=spec['service'], name=spec['name'], icon=spec['icon'], desc=spec['desc'],
                unit=spec['unit'], mode='fixed', mult=0, note=x['title'], rep=rep, online=x['sid'] in online, mine=x['sid'] == sid, legacy='',
                qty_max=1, available=x['on'], price=x['price'], lo=x['price'], hi=x['price'], base=spec['base'] if type(spec['base']) is int else x['price'],
                own=True, open=link)


def _score(stars, n) -> float:
    return (int(stars or 0) + 9.0) / (int(n or 0) + 3)


def _rank(sort: str, rating: float, price: int, deals: int, online: bool, at: float) -> tuple:
    """The directory's order (SORTS) as a Python key, so svc rows and own-flow rows merge into one list."""
    if sort == 'price':
        return (price, -rating, -at)
    if sort == 'online':
        return (not online, -rating, -at)
    if sort == 'deals':
        return (-deals, -rating, -at)
    return (-rating, -deals, -at)


def directory(store, sid: str, query: dict) -> dict:
    """🛎️ The directory: enabled services, filtered by career / service, sorted by rating, price, online or deals.
    Own-flow listings (🏥 birth rooms, 📸 photographers) come from their modules and merge into the same order."""
    t = now()
    career, service = str(query.get('career') or '')[:40], str(query.get('service') or '')[:40]
    sort = query.get('sort') if query.get('sort') in SORTS else 'rating'
    try:
        offset = max(0, min(OFFSET_MAX, int(query.get('offset') or 0)))
    except (TypeError, ValueError):
        offset = 0
    from .wedding_live import vn_day
    clauses, args = ['s.on_=1'], [vn_day(t)]
    if career:
        clauses.append('s.career=?')
        args.append(career)
    if service:
        clauses.append('s.service=?')
        args.append(service)
    order_args = [t - ONLINE_SECONDS] if sort == 'online' else []
    own_specs = [sp for (c, v), sp in sorted(specs().items()) if is_own(sp) and (not career or c == career) and (not service or v == service)]
    # with own-flow rows to merge, the svc rows of every page before this one are read too (offset is small in practice)
    limit, skip = (offset + PAGE + 1, 0) if own_specs else (PAGE + 1, offset)
    with store.connect() as db:
        rows = [dict(r) for r in db.execute(
            'SELECT s.*, r.n AS rn, r.stars AS rs, r.deals AS rd, p.last_at FROM svc_settings s LEFT JOIN svc_rep r ON r.provider=s.provider '
            'LEFT JOIN stat_play p ON p.day=? AND p.sid=s.provider WHERE ' + ' AND '.join(clauses) +
            f' ORDER BY {SORTS[sort]}, s.updated_at DESC LIMIT ? OFFSET ?', (*args, *order_args, limit, skip)).fetchall()]
        rows = [r for r in rows if not is_own(get_spec(r['career'], r['service']))]   # never a market setting of an own-flow listing
        merged = [(None, r) for r in rows]
        own_counts = []
        if own_specs:
            got = [(sp, x) for sp in own_specs for x in _own_rows(sp, db)]
            on_now = _online(db, [x['sid'] for _, x in got], t) if sort == 'online' else set()
            for sp in own_specs:
                n = sum(1 for g in got if g[0] is sp)
                if n:
                    own_counts.append(dict(career=sp['career'], service=sp['service'], n=n))
            # the svc rows come sorted by SQL in this same order: only the own-flow rows are sorted, then one lazy merge
            # up to the page's end (never a sort of every row before the page)
            def svc_key(r):
                return _rank(sort, _score(r.get('rs'), r.get('rn')), int(r['price'] or 0), int(r.get('rd') or 0),
                             (r.get('last_at') or 0) > t - ONLINE_SECONDS, float(r['updated_at'] or 0))
            own = sorted(((_rank(sort, _score(x['stars'], x['rated']), x['price'], x['deals'], x['sid'] in on_now, x['at']), i, (sp, x))
                          for i, (sp, x) in enumerate(got)), key=lambda e: (e[0], e[1]))
            lazy = heapq.merge(((svc_key(r), -1, (None, r)) for r in rows), own, key=lambda e: e[0])
            merged = [e[2] for e in itertools.islice(lazy, offset, offset + PAGE + 1)]
        more = len(merged) > PAGE
        merged = merged[:PAGE]
        sids = [m[1]['provider'] if m[0] is None else m[1]['sid'] for m in merged]
        online = {m[1]['provider'] for m in merged if m[0] is None and (m[1].get('last_at') or 0) > t - ONLINE_SECONDS}
        online |= _online(db, [m[1]['sid'] for m in merged if m[0] is not None], t)
        owners = sorted({m[1]['provider'] for m in merged if m[0] is None and (get_spec(m[1]['career'], m[1]['service']) or {}).get('legacy')})
        places = {}
        if owners:
            marks = ','.join('?' * len(owners))
            for p in db.execute(f'SELECT * FROM work_visit_places WHERE owner IN ({marks})', tuple(owners)).fetchall():
                places.setdefault(p['owner'], []).append(dict(p))
        people, out = _people(db, sids), []
        for who, (sp, r) in zip(sids, merged):
            if who != sid and _blocked(db, sid, who):
                continue
            item = _listing(db, r, sid, t, online, places) if sp is None else _own_item(sp, r, sid, online)
            if not item:
                continue
            item['who'] = people[who]
            out.append(item)
        counts = [dict(career=r['career'], service=r['service'], n=int(r['n'])) for r in
                  db.execute('SELECT career, service, COUNT(*) AS n FROM svc_settings WHERE on_=1 GROUP BY career, service').fetchall()
                  if not is_own(get_spec(r['career'], r['service']))]
        read = {(x['career'], x['service']) for x in own_specs}
        for (c, v), sp in sorted(specs().items()):   # the career filter lists own-flow services that this filter left out too
            if is_own(sp) and (c, v) not in read:
                n = len(sp['providers'](db, PAGE, 0) or [])   # up to PAGE: the filter only needs to know there are some
                if n:
                    own_counts.append(dict(career=c, service=v, n=n))
        counts += own_counts
    return dict(items=out, next=offset + PAGE if more and offset + PAGE <= OFFSET_MAX else None, sort=sort, career=career, service=service,
                counts=counts, off=off())


def provider_view(store, sid: str, pid: str) -> dict:
    """A provider's card: who, ⭐ reputation, khách quen, online, every service they offer, recent ratings."""
    t = now()
    with store.connect() as db:
        provider = _resolve(db, pid)
        need(provider, 'Không tìm thấy người này.', 'not_found', 404)
        need(provider == sid or not _blocked(db, sid, provider), 'Không tìm thấy người này.', 'not_found', 404)
        online = _online(db, [provider], t)
        rows = [dict(r) for r in db.execute('SELECT s.*, r.n AS rn, r.stars AS rs, r.deals AS rd FROM svc_settings s LEFT JOIN svc_rep r '
                                            'ON r.provider=s.provider WHERE s.provider=? AND s.on_=1 ORDER BY s.career, s.service', (provider,)).fetchall()]
        places = {provider: [dict(p) for p in db.execute('SELECT * FROM work_visit_places WHERE owner=?', (provider,)).fetchall()]}
        items = [x for x in (_listing(db, r, sid, t, online, places) for r in rows if not is_own(get_spec(r['career'], r['service']))) if x]
        for (_c, _v), sp in sorted(specs().items()):   # own-flow listings of this provider (🏥 a birth room, 📸 a studio)
            if is_own(sp):
                items += [_own_item(sp, x, sid, online) for x in _own_rows(sp, db, provider) if x['on']]
        revs = [dict(r) for r in db.execute('SELECT * FROM svc_reviews WHERE provider=? ORDER BY created_at DESC LIMIT 10', (provider,)).fetchall()]
        mine_regs = regulars(db, provider, 50) if provider == sid else None   # my own card: the list, its count from the same query
        people = _people(db, [provider] + [r['buyer'] for r in revs] + [x['sid'] for x in (mine_regs or [])[:10]])
        reviews = [dict(stars=int(r['stars']), comment=r['comment'], reply=r['reply'], at=r['created_at'], who=people[r['buyer']])
                   for r in revs if not _blocked(db, sid, r['buyer'])]
        regs = [dict(people[x['sid']], n=x['n']) for x in (mine_regs or [])[:10]]
        return dict(who=people[provider], online=provider in online, rep=rep_view(db, provider, len(mine_regs) if mine_regs is not None else None),
                    items=items, reviews=reviews, regulars=regs, mine=provider == sid)


def inbox(store, sid: str) -> dict:
    """My talks and orders, both sides (and the legacy workplace orders, read only), newest first."""
    settle_quiet(store, sid)
    t = now()
    with store.connect() as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM svc_orders WHERE buyer=? OR provider=? ORDER BY updated_at DESC, id LIMIT 80', (sid, sid)).fetchall()]
        people = _people(db, [r['provider'] if r['buyer'] == sid else r['buyer'] for r in rows])
        marks = _marks(db, [r['id'] for r in rows])
        items = [_view(db, r, sid, people, t, marks) for r in rows]
        legacy = []
        for r in db.execute('SELECT * FROM work_service_orders WHERE customer=? OR provider=? ORDER BY updated_at DESC LIMIT 30', (sid, sid)).fetchall():
            r = dict(r)
            d = _data(r)
            role = 'buyer' if r['customer'] == sid else 'provider'
            other = d.get('provider' if role == 'buyer' else 'customer') or {}
            legacy.append(dict(id=r['id'], kind='wo', status=r['status'], role=role, price=int(r['price']), fee=int(r.get('fee') or 0),
                               name=(d.get('offer') or {}).get('label', ''), place_name=d.get('place_name', ''), other=other,
                               market=bool(d.get('market')), created_at=r['created_at'], updated_at=r['updated_at']))
        return dict(items=items, legacy=legacy, alerts=alert_count(db, sid), rules=rules(), off=off())


def mine(store, sid: str, state: dict | None) -> dict:
    """The services this player can sell (their careers, their quầy), with their settings, prices and reputation."""
    if state is None:
        loaded = mr._read_state(store, sid)
        state = loaded[0] if loaded else {}
    out = []
    with store.connect() as db:
        rows = {(r['career'], r['service']): dict(r) for r in db.execute('SELECT * FROM svc_settings WHERE provider=?', (sid,)).fetchall()}
        for (career, service), spec in sorted(specs().items()):
            why = (spec['can_provide'] or _career_started(career))(state) if state else 'Chưa đọc được tiến trình.'
            if is_own(spec):   # set up in the module (🏥 Nhà & Gia đình, 📸 Tiệm ảnh): shown here with a link there
                own = (_own_rows(spec, db, sid) or [None])[0]
                if why and not own:
                    continue
                out.append(public_spec(spec) | dict(on=bool(own and own['on']), mode='fixed', mult=0, base=own['price'] if own else spec['floor'],
                                                    lo=0, hi=0, price=own['price'] if own else 0, note=(own or {}).get('title', ''),
                                                    why=why or (own or {}).get('why', ''), setup=spec['setup'] or spec['open']))
                continue
            row = rows.get((career, service))
            if why and not row:
                continue
            base = base_of(spec, db, sid)
            q = quote(db, sid, career, service, 1, setting=row, base=base)
            out.append(public_spec(spec) | dict(on=bool(row and row['on_']), mode=q['mode'], mult=q['mult'], base=base, lo=q['lo'], hi=q['hi'],
                                                price=unit_price(spec, base, q['mult']), note=(row or {}).get('note', ''), why=why))
        from .content import CAREER_META
        for x in out:
            x['career_name'] = str(CAREER_META.get(x['career'], {}).get('short') or ('Quầy' if x['career'] == 'quay' else x['career']))
        return dict(services=out, rep=rep_view(db, sid), pid=_pid(sid), rules=rules())


def get(store, token, state, sub: str, query: dict, ip: str = '') -> dict:
    sid = _actor(store, token)
    query = query or {}
    if sub == 'inbox':
        _touch(store, sid, ip, TOUCH_S)
    if sub in ('', 'dir'):
        return directory(store, sid, query)
    if sub == 'provider':
        return provider_view(store, sid, str(query.get('pid') or ''))
    if sub == 'inbox':
        return inbox(store, sid)
    if sub == 'mine':
        return mine(store, sid, state)
    if sub == 'catalog':
        return catalog()
    raise ServiceError('Không có mục này.', 'not_found', 404)


# ---------------------------------------------------------------- writing
def _note(v) -> str:
    from . import work_visits
    return work_visits._clean(v if v is not None else '', NOTE_MAX)


def _rid(data) -> str:
    rid = data.get('rid')
    need(isinstance(rid, str) and RID_RX.fullmatch(rid), 'Thiếu mã thao tác.', 'bad_rid')
    return rid


def _fingerprint(data) -> str:
    return hashlib.sha256(_json({k: v for k, v in data.items() if k != 'rid'}).encode()).hexdigest()


def _by_rid(db, sid, rid):
    r = db.execute('SELECT * FROM svc_orders WHERE buyer=? AND request_id=?', (sid, rid)).fetchone()
    return dict(r) if r else None


def _open_counts(db, buyer, provider):
    a = db.execute(f"SELECT COUNT(*) AS n FROM svc_orders WHERE buyer=? AND status IN ({','.join('?' * len(OPEN))})", (buyer, *OPEN)).fetchone()['n']
    b = db.execute(f"SELECT COUNT(*) AS n FROM svc_orders WHERE provider=? AND status IN ({','.join('?' * len(OPEN))})", (provider, *OPEN)).fetchone()['n']
    need(int(a) < BUYER_OPEN, 'Bạn đang có nhiều đơn chờ. Xong bớt rồi đặt tiếp nhé.', 'too_many_orders', 409)
    need(int(b) < PROVIDER_OPEN, 'Người này đang có nhiều khách chờ.', 'busy', 409)


def _target(db, data: dict, sid: str) -> tuple:
    """(provider sid, spec, setting row) of a request {pid, career, service}: on and sold by someone else."""
    spec = get_spec(str(data.get('career') or ''), str(data.get('service') or ''))
    need(spec, 'Dịch vụ này chưa có.', 'unknown_service', 404)
    need(not is_own(spec), OWN_TEXT, 'own_flow', 409)   # its module books, holds and pays: never a second escrow here
    provider = _resolve(db, data.get('pid'))
    need(provider, 'Không tìm thấy người này.', 'not_found', 404)
    row = _setting(db, provider, spec['career'], spec['service'])
    need(row and row['on_'], 'Dịch vụ này đang tạm nghỉ.', 'unavailable', 409)
    need(provider != sid, 'Không tự đặt dịch vụ của chính mình được.', 'self')
    need(not _blocked(db, sid, provider), 'Không thể giao dịch với người này.', 'blocked', 403)
    return provider, spec, row


def _check_buyer(store, sid: str, spec: dict, price: int) -> dict:
    loaded = mr._read_state(store, sid)
    need(loaded, 'Không tìm thấy tiến trình của bạn.', 'session_missing', 404)
    state = loaded[0]
    with store.connect() as db:
        why = _requires_why(spec, state, db, sid)
    need(not why, why, 'requirement')
    j = state.get('journey') or {}
    need(j.get('story'), 'Phố dịch vụ dùng ví hành trình.', 'not_story')
    need(j.get('wallet', 0) >= 0, 'Ví đang nợ. Trả nợ trước nhé.', 'in_debt')
    have = _have(state)
    need(have >= price, f'Còn thiếu {fmt(price - have)} xu (ví và tài khoản).', 'no_money')
    return state


def _check_in(db, spec: dict | None, buyer: str, state: dict | None) -> None:
    """spec['check'] once more inside the transaction that takes the money (one open order, a cooldown, a day cap…),
    serialised per buyer and career by an advisory lock: two orders sent together never both pass it."""
    if not spec or not spec.get('check') or state is None:
        return
    db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))', ('svc-check:' + buyer + '|' + spec['career'],))
    why = spec['check'](db, buyer, state)
    need(not why, str(why or '')[:200], 'requirement')


def _check_provider(store, provider: str, spec: dict) -> None:
    loaded = mr._read_state(store, provider)
    need(loaded, 'Người này đã rời phố.', 'not_found', 404)
    why = (spec['can_provide'] or _career_started(spec['career']))(loaded[0])
    need(not why, 'Người này hiện chưa nhận dịch vụ này.', 'unavailable', 409)


def _legacy_offer(db, spec: dict, provider: str, data: dict) -> tuple:
    """(place row, snapshot offer) a legacy order points at."""
    place = db.execute('SELECT * FROM work_visit_places WHERE id=? AND owner=?', (data.get('place'), provider)).fetchone()
    need(place, 'Không tìm thấy chỗ làm này.', 'not_found', 404)
    place = dict(place)
    need(legacy_key(place['kind'], place['target']) == (spec['career'], spec['service']), 'Không tìm thấy chỗ làm này.', 'not_found', 404)
    snap = _data(place)
    offer = next((o for o in snap.get('offers') or [] if o.get('offer_id') == data.get('offer_id')), None)
    need(offer and snap.get('available'), 'Dịch vụ này hiện chưa sẵn sàng.', 'unavailable', 409)
    return place, offer


def _order(store, sid: str, data: dict, ip: str) -> dict:
    """A fixed-price order: the buyer pays the quoted price into escrow; the provider takes it (or not, refunded)."""
    need(set(data) <= {'pid', 'career', 'service', 'qty', 'note', 'rid', 'expected_price', 'place', 'offer_id'}, 'Thông tin đặt dịch vụ không hợp lệ.')
    rid, fp = _rid(data), _fingerprint(data)
    note = _note(data.get('note'))
    with store.connect() as db:
        old = _by_rid(db, sid, rid)
        if old:
            need(old['fingerprint'] == fp, 'Mã thao tác đã dùng cho nội dung khác.', 'rid_conflict', 409)
            return dict(order=_view(db, old, sid), changed=False)
        need(not off(), OFF_TEXT, 'svc_off', 503)
        provider, spec, row = _target(db, data, sid)
        if spec['note_check']:
            why = spec['note_check'](note)
            need(not why, str(why)[:200], 'bad_note')
        need(row['mode'] == 'fixed', 'Dịch vụ này thương lượng giá: hãy gửi giá bạn muốn trả.', 'negotiate', 409)
        if spec['legacy']:
            place, offer = _legacy_offer(db, spec, provider, data)
    if spec['legacy']:
        from . import work_visits
        return work_visits.market_order(store, sid, dict(place=place['id'], offer_id=offer['offer_id'], note=note, rid=rid,
                                                         **({'expected_price': data['expected_price']} if 'expected_price' in data else {})), ip)
    qty = _int(data.get('qty', 1), 1, spec['qty_max'], 'Số lượng không hợp lệ.')
    with store.connect() as db:
        q = quote(db, provider, spec['career'], spec['service'], qty, setting=row)
        price = q['price']
        if 'expected_price' in data:
            need(data['expected_price'] == price, 'Giá đã thay đổi. Xem lại giá trước khi đặt nhé.', 'quote_changed', 409)
        guard(db, sid, provider, price, spec, ip, sid, money=False)
    _check_provider(store, provider, spec)
    _check_buyer(store, sid, spec, price)
    t = now()
    oid = 'sv_' + secrets.token_hex(12)
    body = dict(note=note, name=spec['name'], icon=spec['icon'], unit=spec['unit'], lo=q['lo'], hi=q['hi'])
    box = {}

    def pay(s):
        box['state'] = s
        debit(s, price, f'🛎️ Giữ tiền Phố dịch vụ · {spec["name"]}')

    def insert(db):
        if _by_rid(db, sid, rid):
            raise _Replay()
        record_net(db, sid, ip, t)
        _check_in(db, spec, sid, box.get('state'))
        guard(db, sid, provider, price, spec, ip, sid, money=True, t=t)
        _open_counts(db, sid, provider)
        db.execute('INSERT INTO svc_orders(id,buyer,provider,career,service,kind,status,qty,price,ask,ask_by,rounds,base,mult,request_id,fingerprint,'
                   "data,created_at,updated_at,due_at,held_at) VALUES(?,?,?,?,?,'svc','held',?,?,?,'',0,?,?,?,?,?,?,?,?,?)",
                   (oid, sid, provider, spec['career'], spec['service'], qty, price, price, q['base'], q['mult'], rid, fp, _json(body), t, t,
                    t + HOLD_HOURS * HOUR, t))
    try:
        mr._mutate_retry(store, {sid: pay}, insert)
    except _Replay:
        pass
    with store.connect() as db:
        r = _by_rid(db, sid, rid)
        return dict(order=_view(db, r, sid), changed=True, message=f'Đã giữ {fmt(price)} xu cho đơn. Chờ người bán nhận đơn nhé.')


def _offer(store, sid: str, data: dict, ip: str) -> dict:
    """🤝 A buyer's price for a thương lượng service: a talk, no money yet."""
    need(set(data) <= {'pid', 'career', 'service', 'qty', 'note', 'rid', 'price', 'place', 'offer_id'}, 'Thông tin trả giá không hợp lệ.')
    rid, fp = _rid(data), _fingerprint(data)
    note = _note(data.get('note'))
    with store.connect() as db:
        old = _by_rid(db, sid, rid)
        if old:
            need(old['fingerprint'] == fp, 'Mã thao tác đã dùng cho nội dung khác.', 'rid_conflict', 409)
            return dict(order=_view(db, old, sid), changed=False)
        need(not off(), OFF_TEXT, 'svc_off', 503)
        provider, spec, row = _target(db, data, sid)
        if spec['note_check']:
            why = spec['note_check'](note)
            need(not why, str(why)[:200], 'bad_note')
        need(row['mode'] == 'nego', 'Dịch vụ này có giá cố định: đặt theo giá niêm yết nhé.', 'fixed_price', 409)
        extra = {}
        if spec['legacy']:
            place, offer = _legacy_offer(db, spec, provider, data)
            qty, base = 1, int(offer['price'])
            extra = dict(place=place['id'], offer_id=offer['offer_id'], label=str(offer.get('label') or '')[:120])
        else:
            qty = _int(data.get('qty', 1), 1, spec['qty_max'], 'Số lượng không hợp lệ.')
            base = base_of(spec, db, provider)
        lo, hi = bounds(spec, base, qty)
        price = data.get('price')
        need(type(price) is int and lo <= price <= hi, f'Giá trả cần từ {fmt(lo)} đến {fmt(hi)} xu.', 'bad_price')
        guard(db, sid, provider, price, spec, ip, sid, money=False)
    _check_provider(store, provider, spec)
    _check_buyer(store, sid, spec, price)
    t = now()
    oid = 'sv_' + secrets.token_hex(12)
    body = dict(note=note, name=spec['name'], icon=spec['icon'], unit=spec['unit'], lo=lo, hi=hi, **extra)

    def insert(db):
        if _by_rid(db, sid, rid):
            return
        record_net(db, sid, ip, t)
        _open_counts(db, sid, provider)
        db.execute('INSERT INTO svc_orders(id,buyer,provider,career,service,kind,status,qty,price,ask,ask_by,rounds,base,mult,request_id,fingerprint,'
                   "data,created_at,updated_at,due_at) VALUES(?,?,?,?,?,?,'talk',?,0,?,'buyer',1,?,0,?,?,?,?,?,?)",
                   (oid, sid, provider, spec['career'], spec['service'], 'wo' if spec['legacy'] else 'svc', qty, price, base, rid, fp, _json(body),
                    t, t, t + TALK_HOURS * HOUR))
    store.transaction(insert)
    with store.connect() as db:
        r = _by_rid(db, sid, rid)
        return dict(order=_view(db, r, sid), changed=True, message='Đã gửi giá. Chờ người bán trả lời nhé.')


def _row(db, oid, lock=False):
    need(isinstance(oid, str) and ID_RX.fullmatch(oid), 'Không tìm thấy đơn.', 'not_found', 404)
    r = db.execute('SELECT * FROM svc_orders WHERE id=?' + (' FOR UPDATE' if lock else ''), (oid,)).fetchone()
    need(r, 'Không tìm thấy đơn.', 'not_found', 404)
    return dict(r)


def _mine(row, sid):
    need(sid in (row['buyer'], row['provider']), 'Không tìm thấy đơn.', 'not_found', 404)
    return 'buyer' if row['buyer'] == sid else 'provider'


def _answer(store, sid: str, data: dict, ip: str) -> dict:
    """A talk: accept the other side's price (escrow now), counter it, decline (provider) or cancel (buyer)."""
    need(set(data) <= {'order', 'op', 'price', 'ask'}, 'Thông tin trả lời không hợp lệ.')
    op = data.get('op')
    need(op in ('accept', 'counter', 'decline', 'cancel'), 'Chọn cách trả lời.')
    t = now()
    with store.connect() as db:
        row = _row(db, data.get('order'))
        role = _mine(row, sid)
    if row['status'] != 'talk':
        with store.connect() as db:
            return dict(order=_view(db, row, sid), changed=False, message='Cuộc trả giá này đã xong.')
    spec = get_spec(row['career'], row['service'])
    if op in ('decline', 'cancel'):
        need((op == 'decline') == (role == 'provider'), 'Thao tác không hợp lệ.')
        store.transaction(lambda db: _flip(db, row['id'], 'talk', 'declined' if op == 'decline' else 'cancelled', t, due_at=None))
        with store.connect() as db:
            return dict(order=_view(db, _row(db, row['id']), sid), changed=True, message='Đã dừng trả giá.')
    need(not off(), OFF_TEXT, 'svc_off', 503)   # 🛑 a talk may still be stopped (decline / cancel above), never sealed
    need(row['ask_by'] != role, 'Đang chờ người kia trả lời.', 'not_your_turn', 409)
    if 'ask' in data:
        need(data['ask'] == row['ask'], 'Giá vừa đổi. Xem lại nhé.', 'ask_changed', 409)
    if op == 'counter':
        need(int(row['rounds']) < MAX_ROUNDS, f'Đã trả giá {MAX_ROUNDS} lần: giờ chỉ đồng ý hoặc dừng thôi.', 'rounds')
        lo, hi = int(_data(row).get('lo') or 1), int(_data(row).get('hi') or PRICE_CEIL)
        price = data.get('price')
        need(type(price) is int and lo <= price <= hi, f'Giá cần từ {fmt(lo)} đến {fmt(hi)} xu.', 'bad_price')
        need(price != row['ask'], 'Giá này giống giá đang trả rồi: bấm Đồng ý nhé.', 'same_price')

        def counter(db):
            record_net(db, sid, ip, t)
            n = db.execute("UPDATE svc_orders SET ask=?,ask_by=?,rounds=rounds+1,updated_at=?,due_at=? WHERE id=? AND status='talk' AND rounds=? AND ask_by<>?",
                           (price, role, t, t + TALK_HOURS * HOUR, row['id'], row['rounds'], role)).rowcount
            need(n == 1, 'Giá vừa đổi. Xem lại nhé.', 'ask_changed', 409)
        store.transaction(counter)
        with store.connect() as db:
            return dict(order=_view(db, _row(db, row['id']), sid), changed=True, message=f'Đã trả giá {fmt(price)} xu.')
    # accept: the price on the table goes into escrow now
    price = int(row['ask'])
    if row['kind'] == 'wo':
        from . import work_visits
        d = _data(row)
        return work_visits.market_order(store, row['buyer'], dict(place=d.get('place'), offer_id=d.get('offer_id'), note=d.get('note', ''),
                                                                  rid='tk' + row['id'][3:]), ip, talk=dict(id=row['id'], price=price, rounds=row['rounds'],
                                                                                                           actor=sid, provider_agreed=True))
    if spec:
        with store.connect() as db:
            guard(db, row['buyer'], row['provider'], price, spec, ip, sid, money=False)
        _check_buyer(store, row['buyer'], spec, price)

    box = {}

    def pay(s):
        box['state'] = s
        debit(s, price, f'🛎️ Giữ tiền Phố dịch vụ · {(spec or {}).get("name") or row["service"]}')

    def lock(db):
        cur = db.execute('SELECT * FROM svc_orders WHERE id=? FOR UPDATE', (row['id'],)).fetchone()
        need(cur and cur['status'] == 'talk' and cur['rounds'] == row['rounds'] and cur['ask'] == price, 'Giá vừa đổi. Xem lại nhé.', 'ask_changed', 409)
        record_net(db, sid, ip, t)
        _check_in(db, spec, row['buyer'], box.get('state'))
        guard(db, row['buyer'], row['provider'], price, spec, ip, sid, money=True, t=t)
        hours = (spec or {}).get('work_hours') or WORK_HOURS
        if not _flip(db, row['id'], 'talk', 'working', t, price=price, mult=0, held_at=t, due_at=t + hours * HOUR):
            raise _Replay()
    try:
        mr._mutate_retry(store, {row['buyer']: pay}, lock)
    except _Replay:
        pass
    with store.connect() as db:
        return dict(order=_view(db, _row(db, row['id']), sid), changed=True, message=f'Chốt giá {fmt(price)} xu. Tiền đã giữ cho đơn.')


def _simple(store, sid: str, data: dict, sub: str, ip: str) -> dict:
    """take / decline / cancel / confirm: a DB-only status step, then the money step at once."""
    need(set(data) <= {'order'}, 'Thông tin không hợp lệ.')
    t = now()
    with store.connect() as db:
        row = _row(db, data.get('order'))
        role = _mine(row, sid)
    spec = get_spec(row['career'], row['service'])
    if row['status'] == 'talk' and sub in ('decline', 'cancel'):
        return _answer(store, sid, dict(order=row['id'], op=sub), ip)
    allowed = dict(take=('provider', ('held',)), decline=('provider', ('held', 'working')), cancel=('buyer', ('held',)), confirm=('buyer', ('delivered',)))[sub]
    need(role == allowed[0], 'Thao tác không hợp lệ.', 'forbidden', 403)
    if sub == 'cancel' and row['status'] == 'working':
        need(False, 'Người bán đã nhận đơn: nhắn người bán dừng giúp nhé.', 'already_started', 409)
    if row['status'] not in allowed[1]:
        done = dict(take=('working', 'delivered', 'ready', 'done'), decline=('refund', 'refunded'), cancel=('refund', 'refunded'),
                    confirm=('ready', 'done'))[sub]
        need(row['status'] in done, 'Đơn đã sang bước khác.', 'gone', 409)
        settle_quiet(store, sid, row['id'])
        with store.connect() as db:
            return dict(order=_view(db, _row(db, row['id']), sid), changed=False)

    def step(db):
        cur = _row(db, row['id'], lock=True)
        if cur['status'] not in allowed[1]:
            raise _Replay()
        record_net(db, sid, ip, t)
        d = _data(cur)
        if sub == 'take':
            hours = (spec or {}).get('work_hours') or WORK_HOURS
            return _flip(db, cur['id'], 'held', 'working', t, due_at=t + hours * HOUR)
        if sub in ('decline', 'cancel'):
            d['why'] = sub
            _set_data(db, cur['id'], d)
            return _flip(db, cur['id'], cur['status'], 'refund', t, due_at=t)
        return _flip(db, cur['id'], 'delivered', 'ready', t, due_at=t)
    try:
        store.transaction(step)
    except _Replay:
        pass
    settle_quiet(store, sid, row['id'])
    msg = dict(take='Đã nhận đơn. Làm xong bấm Xong việc nhé.', decline='Đã từ chối. Tiền đã hoàn về ví khách.',
               cancel='Đã hủy. Tiền đã hoàn về ví của bạn.', confirm='Đã xác nhận. Người bán đã nhận tiền.')[sub]
    with store.connect() as db:
        return dict(order=_view(db, _row(db, row['id']), sid), changed=True, message=msg)


def _deliver_db(db, provider: str, oid: str, result=None, t=None) -> str:
    """Inside a transaction: the provider finished `oid` (its deliver hook runs here). Returns the new status."""
    t = now() if t is None else t
    cur = _row(db, oid, lock=True)
    need(cur['provider'] == provider, 'Không tìm thấy đơn.', 'not_found', 404)
    if cur['status'] in ('delivered', 'ready', 'done'):
        return cur['status']
    need(cur['status'] == 'working', 'Nhận đơn trước rồi mới giao được.' if cur['status'] == 'held' else 'Đơn không còn chờ giao.', 'not_working', 409)
    spec = get_spec(cur['career'], cur['service'])
    d = _data(cur)
    if result is not None:
        need(isinstance(result, dict) and len(_json(result)) <= 4000, 'Kết quả giao không hợp lệ.', 'bad_result')
        d['input'] = result
    if spec and spec['deliver']:
        out = spec['deliver'](db, cur['provider'], cur['buyer'], _order_dict(dict(cur, data=_json(d))))
        if out is not None:
            need(isinstance(out, dict) and len(_json(out)) <= 4000, 'Kết quả giao không hợp lệ.', 'bad_result')
            d['result'] = out
    _set_data(db, oid, d)
    auto = bool(spec and spec['confirm'] == 'auto')
    new = 'ready' if auto else 'delivered'
    if not _flip(db, oid, 'working', new, t, delivered_at=t, due_at=t if auto else t + CONFIRM_HOURS * HOUR):
        raise _Replay()
    return new


def deliver(store, provider_sid: str, order_id: str, result: dict | None = None) -> dict:
    """For career code: the provider finished the order (the deliver hook runs; 'auto' services are paid at once,
    others wait for the buyer's confirmation). Idempotent. Returns the provider's view of the order."""
    t = now()
    try:
        store.transaction(lambda db: _deliver_db(db, provider_sid, order_id, result, t))
    except _Replay:
        pass
    settle_quiet(store, provider_sid, order_id)
    with store.connect() as db:
        return _view(db, _row(db, order_id), provider_sid)


def deliver_in_commit(db, provider_sid: str, order_id: str, result: dict | None = None) -> str:
    """For career code inside its own game command's transaction (or use result['svc_done']): marks the order done;
    the money step follows at the next poll / housekeeping. Returns the new status."""
    return _deliver_db(db, provider_sid, order_id, result)


def command_commit(db, sid: str, result) -> None:
    """storage.py, in a command's transaction: result['svc_done'] = [{'order': id, 'result': {...}}, …] from a career
    command whose work fulfils those orders. A refusal of one order does not undo the command (it stays open)."""
    items = result.get('svc_done') if isinstance(result, dict) else None
    if not isinstance(items, list):
        return
    raw = getattr(db, 'raw', None)
    for it in items[:8]:
        if not isinstance(it, dict) or not isinstance(it.get('order'), str) or not ID_RX.fullmatch(it['order']):
            continue
        cur = db.execute('SELECT provider, status FROM svc_orders WHERE id=?', (it['order'],)).fetchone()
        if not cur or cur['provider'] != sid or cur['status'] != 'working':
            continue
        # a savepoint on the driver itself (game/db.py reads ROLLBACK … as the whole transaction's rollback)
        if raw is not None:
            raw.execute('SAVEPOINT svc_done')
        try:
            _deliver_db(db, sid, it['order'], it.get('result') if isinstance(it.get('result'), dict) else None)
            if raw is not None:
                raw.execute('RELEASE SAVEPOINT svc_done')
        except (ServiceError, _Replay):
            if raw is None:
                raise
            raw.execute('ROLLBACK TO SAVEPOINT svc_done')


def open_orders(db, provider_sid: str, career: str | None = None, service: str | None = None) -> list:
    """For career code: this provider's paid orders waiting for work (held: not taken yet, working: taken)."""
    sql, args = "SELECT * FROM svc_orders WHERE provider=? AND status IN ('held','working')", [provider_sid]
    if career:
        sql += ' AND career=?'
        args.append(career)
    if service:
        sql += ' AND service=?'
        args.append(service)
    return [dict(_order_dict(dict(r)), status=r['status']) for r in db.execute(sql + ' ORDER BY created_at LIMIT 50', tuple(args)).fetchall()]


def order_of(db, order_id: str) -> dict | None:
    r = db.execute('SELECT * FROM svc_orders WHERE id=?', (order_id,)).fetchone()
    return dict(_order_dict(dict(r)), status=r['status']) if r else None


def _done(store, sid, data, ip) -> dict:
    need(set(data) <= {'order', 'result'}, 'Thông tin không hợp lệ.')
    with store.connect() as db:
        row = _row(db, data.get('order'))
        need(_mine(row, sid) == 'provider', 'Thao tác không hợp lệ.', 'forbidden', 403)
    from . import hotel_stay   # 🏨 a stay is delivered by its check-out only (one lock order: hotel_stays, then svc_orders)
    need(not hotel_stay.is_stay(row['career'], row['service']), 'Trả phòng cho khách ở 🏨 Sổ phòng nhé.', 'use_hotel_book', 409)
    view = deliver(store, sid, row['id'], data.get('result') if isinstance(data.get('result'), dict) else None)
    return dict(order=view, changed=True, message='Đã giao. Khách xác nhận là bạn nhận tiền.' if view['status'] == 'delivered' else 'Đã giao và nhận tiền.')


def _rate(store, sid, data) -> dict:
    need(set(data) <= {'order', 'stars', 'comment'}, 'Thông tin đánh giá không hợp lệ.')
    stars = _int(data.get('stars'), 1, 5, 'Chọn từ 1 đến 5 sao.')
    from . import work_visits
    comment = work_visits._clean(data.get('comment', ''), 300)
    t = now()

    def write(db):
        row = _row(db, data.get('order'), lock=True)
        need(row['buyer'] == sid, 'Không tìm thấy đơn.', 'not_found', 404)
        need(row['status'] == 'done', 'Chỉ đánh giá đơn đã hoàn tất.', 'not_completed')
        if db.execute('SELECT 1 FROM svc_reviews WHERE order_id=?', (row['id'],)).fetchone():
            return False
        counted = rate_counts(db, row['provider'], sid, t)
        db.execute('INSERT INTO svc_reviews(order_id,src,provider,buyer,stars,comment,counted,created_at) VALUES(?,?,?,?,?,?,?,?)',
                   (row['id'], 'svc', row['provider'], sid, stars, comment, int(counted), t))
        if counted:
            _rep_add(db, row['provider'], stars=stars)
        return True
    changed = store.transaction(write)
    with store.connect() as db:
        return dict(order=_view(db, _row(db, data['order']), sid), changed=bool(changed), message='Cảm ơn bạn đã đánh giá!')


def rate_counts(db, provider: str, buyer: str, t=None) -> bool:
    """Does a new rating from `buyer` move `provider`'s reputation? One a week per pair, accounts ≥ 3 days old."""
    t = now() if t is None else t
    if not _old(db, buyer, RATE_ACCOUNT_DAYS, t):
        return False
    return not db.execute('SELECT 1 FROM svc_reviews WHERE provider=? AND buyer=? AND counted=1 AND created_at>?',
                          (provider, buyer, t - RATE_DAYS * DAY)).fetchone()


def rate_legacy(db, order: dict, stars: int, t=None) -> None:
    """A legacy workplace review (work_visits post 'review', its own transaction): the provider's reputation too."""
    t = now() if t is None else t
    if db.execute('SELECT 1 FROM svc_reviews WHERE order_id=?', (order['id'],)).fetchone():
        return
    counted = rate_counts(db, order['provider'], order['customer'], t)
    db.execute('INSERT INTO svc_reviews(order_id,src,provider,buyer,stars,comment,counted,created_at) VALUES(?,?,?,?,?,?,?,?)',
               (order['id'], 'wo', order['provider'], order['customer'], stars, '', int(counted), t))
    # the first look at a provider counts the legacy reviews from work_service_reviews (_rep_row): this one is there too
    exists = db.execute('SELECT 1 FROM svc_rep WHERE provider=?', (order['provider'],)).fetchone()
    if counted and exists:
        _rep_add(db, order['provider'], stars=stars)
    elif not exists:
        _rep_add(db, order['provider'])


def _flag(store, sid, data) -> dict:
    need(set(data) <= {'order', 'text'}, 'Thông tin báo cáo không hợp lệ.')
    from . import work_visits
    text = work_visits._clean(data.get('text', ''), 300, 4)
    oid = data.get('order')
    t = now()

    def write(db):
        need(isinstance(oid, str) and ID_RX.fullmatch(oid), 'Không tìm thấy đơn.', 'not_found', 404)
        if oid.startswith('wo_'):
            r = db.execute('SELECT * FROM work_service_orders WHERE id=?', (oid,)).fetchone()
            need(r and r['customer'] == sid, 'Không tìm thấy đơn.', 'not_found', 404)
            need(r['status'] in ('ready', 'completed') and r['updated_at'] + FLAG_HOURS * HOUR >= t, f'Chỉ báo cáo trong {FLAG_HOURS} giờ sau khi giao.', 'late')
            src, provider = 'wo', r['provider']
        else:
            r = _row(db, oid)
            need(r['buyer'] == sid, 'Không tìm thấy đơn.', 'not_found', 404)
            at = r['delivered_at'] or r['done_at'] or 0
            need(r['status'] in ('delivered', 'ready', 'done') and at + FLAG_HOURS * HOUR >= t, f'Chỉ báo cáo trong {FLAG_HOURS} giờ sau khi giao.', 'late')
            src, provider = 'svc', r['provider']
        return db.execute('INSERT INTO svc_flags(order_id,src,buyer,provider,text,created_at) VALUES(?,?,?,?,?,?) ON CONFLICT DO NOTHING',
                          (oid, src, sid, provider, text, t)).rowcount
    n = store.transaction(write)
    return dict(changed=bool(n), message='Đã gửi báo cáo cho quản trị. Cảm ơn bạn!' if n else 'Bạn đã báo cáo đơn này rồi.')


def _settings(store, sid, state, data, ip) -> dict:
    need(set(data) <= {'career', 'service', 'on', 'mode', 'mult', 'note'}, 'Thông tin cài đặt không hợp lệ.')
    spec = get_spec(str(data.get('career') or ''), str(data.get('service') or ''))
    need(spec, 'Dịch vụ này chưa có.', 'unknown_service', 404)
    need(not is_own(spec), OWN_SETUP_TEXT, 'own_settings', 409)
    on = data.get('on')
    need(isinstance(on, bool), 'Chọn bật hoặc tắt.')
    mode = data.get('mode', 'fixed')
    need(mode in MODES, 'Chọn giá cố định hoặc thương lượng.')
    mult = _int(data.get('mult', DEFAULT_MULT), MULT_MIN, MULT_MAX, f'Hệ số từ ×{MULT_MIN} đến ×{MULT_MAX}.')
    note = _note(data.get('note', ''))[:80]
    if on:
        st = state
        if st is None:
            loaded = mr._read_state(store, sid)
            st = loaded[0] if loaded else {}
        why = (spec['can_provide'] or _career_started(spec['career']))(st)
        need(not why, why or 'Bạn chưa bán được dịch vụ này.', 'cannot_provide')
    t = now()

    def write(db):
        record_net(db, sid, ip, t)
        base = base_of(spec, db, sid)
        lo, _ = bounds(spec, base, 1)
        price = lo if mode == 'nego' else unit_price(spec, base, mult)
        db.execute('INSERT INTO svc_settings(provider,pid,career,service,on_,mode,mult,price,note,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) '
                   'ON CONFLICT(provider,career,service) DO UPDATE SET pid=excluded.pid,on_=excluded.on_,mode=excluded.mode,mult=excluded.mult,'
                   'price=excluded.price,note=excluded.note,updated_at=excluded.updated_at',
                   (sid, _pid(sid), spec['career'], spec['service'], int(on), mode, mult, price, note, t))
        if not db.execute('SELECT 1 FROM svc_rep WHERE provider=?', (sid,)).fetchone():
            _rep_save(db, _rep_row(db, sid))
    store.transaction(write)
    return dict(changed=True, message='Đã lưu. Dịch vụ đang mở cho khách.' if on else 'Đã tắt dịch vụ này.', mine=mine(store, sid, state))


_touched: dict = {}
_touch_lock = threading.Lock()


def _touch(store, sid: str, ip: str, every: float = 0.0) -> None:
    """The network this request came from (a keyed tag), kept even when the request is refused. every > 0 (a GET poll):
    one write per player and network in that many seconds at most (svc_net keeps NET_DAYS; minutes do not matter)."""
    tag = net_tags(ip)[0] if ip else ''
    if not tag:
        return
    t = now()
    if every:
        key = (sid, tag)
        with _touch_lock:
            if t - _touched.get(key, 0.0) < every:
                return
            if len(_touched) > 20000:
                _touched.clear()
            _touched[key] = t
    try:
        store.transaction(lambda db: record_net(db, sid, ip, t))
    except Exception:  # noqa: BLE001
        pass


def post(store, token, state, sub: str, data: dict, ip: str = '') -> dict:
    sid = _actor(store, token)
    need(isinstance(data, dict), 'Dữ liệu không hợp lệ.')
    _touch(store, sid, ip)
    if sub == 'order':
        return _order(store, sid, data, ip)
    if sub == 'offer':
        return _offer(store, sid, data, ip)
    if sub == 'answer':
        return _answer(store, sid, data, ip)
    if sub in ('take', 'decline', 'cancel', 'confirm'):
        return _simple(store, sid, data, sub, ip)
    if sub == 'done':
        return _done(store, sid, data, ip)
    if sub == 'rate':
        return _rate(store, sid, data)
    if sub == 'flag':
        return _flag(store, sid, data)
    if sub == 'settings':
        return _settings(store, sid, state, data, ip)
    if sub == 'receive':
        return dict(changed=bool(settle_for(store, sid)), message='Đã đối soát các đơn.')
    raise ServiceError('Thao tác không hợp lệ.', 'unknown_action')


# ---------------------------------------------------------------- account deletion, admin
def forget(db, sid: str) -> None:
    """Store.delete (the save goes in this transaction): their talks end; paid orders they sell and never delivered are
    refunded to the buyers (the money step follows); work they already delivered (delivered, ready) is earned: the
    buyer keeps the result (on_buyer runs at the settlement) and the payout is burned (_settle_one, the provider's save
    gone), never refunded on top of it. Paid orders they bought that were never taken are discarded with the save;
    orders already in work stay so the provider can finish and be paid. Their offers and network tags go."""
    t = now()
    db.execute("UPDATE svc_orders SET status='cancelled',updated_at=?,due_at=NULL WHERE (buyer=? OR provider=?) AND status='talk'", (t, sid, sid))
    for r in db.execute("SELECT id,status,data FROM svc_orders WHERE provider=? AND status IN ('held','working','delivered','ready')", (sid,)).fetchall():
        d = _data(dict(r))
        d['why'] = 'left'
        new = 'ready' if r['status'] in ('delivered', 'ready') else 'refund'
        db.execute('UPDATE svc_orders SET status=?,data=?,updated_at=?,due_at=? WHERE id=?', (new, _json(d), t, t, r['id']))
    db.execute("UPDATE svc_orders SET status='refunded',updated_at=?,due_at=NULL,done_at=? WHERE buyer=? AND status IN ('held','refund')", (t, t, sid))
    db.execute('DELETE FROM svc_settings WHERE provider=?', (sid,))
    db.execute('DELETE FROM svc_net WHERE sid=?', (sid,))


def admin_view(store) -> dict:
    """🚩 Reports (open first) with both sides and the order, and the market's totals (deals, xu, burned)."""
    with store.connect() as db:
        flags = []
        for f in db.execute("SELECT * FROM svc_flags ORDER BY (status='open') DESC, created_at DESC LIMIT 100").fetchall():
            f = dict(f)
            if f['src'] == 'svc':
                o = db.execute('SELECT * FROM svc_orders WHERE id=?', (f['order_id'],)).fetchone()
                order = dict(name=_data(dict(o)).get('name', ''), price=int(o['price']), status=o['status'], fee=int(o['fee'])) if o else {}
            else:
                o = db.execute('SELECT * FROM work_service_orders WHERE id=?', (f['order_id'],)).fetchone()
                order = dict(name=(_data(dict(o)).get('offer') or {}).get('label', ''), price=int(o['price']), status=o['status'], fee=int(o['fee'] or 0)) if o else {}
            flags.append(dict(order=f['order_id'], src=f['src'], text=f['text'], status=f['status'], note=f['note'], at=f['created_at'],
                              buyer=_person(db, f['buyer']), provider=_person(db, f['provider']), info=order))
        a = db.execute("SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS xu, COALESCE(SUM(fee),0) AS fee FROM svc_orders WHERE status='done'").fetchone()
        b = db.execute("SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS xu, COALESCE(SUM(fee),0) AS fee FROM work_service_orders WHERE status='completed' AND fee>0").fetchone()
        live = db.execute("SELECT COUNT(*) AS n, COALESCE(SUM(price),0) AS xu FROM svc_orders WHERE status IN ('held','working','delivered','ready','refund')").fetchone()
        on = db.execute('SELECT COUNT(*) AS n FROM svc_settings WHERE on_=1').fetchone()
        return dict(flags=flags, totals=dict(deals=int(a['n']) + int(b['n']), xu=int(a['xu']) + int(b['xu']), burned=int(a['fee']) + int(b['fee']),
                                             escrow=int(live['xu']), open=int(live['n']), listings=int(on['n'])), rules=rules())


def admin_act(store, admin_sid: str, data: dict) -> dict:
    need(isinstance(data, dict) and data.get('op') == 'close', 'Thao tác không hợp lệ.')
    note = str(data.get('note') or '')[:300]

    def run(db):
        need(db.execute("UPDATE svc_flags SET status='closed',note=?,by_admin=?,closed_at=? WHERE order_id=?",
                        (note, admin_sid, now(), data.get('order'))).rowcount == 1, 'Không tìm thấy báo cáo.', 'not_found', 404)
    store.transaction(run)
    return admin_view(store)
