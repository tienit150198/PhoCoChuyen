"""🎪 Hội chợ việc làm (Hội chợ phố, owner 21/10 "làm hết đi"): a weekly town fair where every career takes part player to
player. Not the 🏮 Hội chợ dân gian / Chợ đen (game/fair*.py, journey.fair): a module, a name and tables of its own.

When (Vietnam time)
* Every Saturday WEEK_START–WEEK_END (14:00–17:00): a quiet afternoon, away from the evening peak (17:30–20:00) and from
  Sunday 20:00 (⚔️ bang war). Nothing is stored to know it: the window is a function of the date. An admin may switch
  the weekly fair off or open a one-off fair of 1–SPECIAL_MAX_HOURS hours (fair_config; /api/admin/townfair).
* MNL_FAIR_OFF=1 is the kill switch: no fair opens, no booth discounts anything (the market's prices are its own
  again at once), the ticker says nothing. Fairs already held still settle and archive (their rewards are kept).

A booth (🎪 gian hàng, one per player and fair)
* Opened for one career the player has started, with a fair discount PCTS (−10…−30 %) on the player's OWN Phố dịch vụ
  prices of that career (game/service_market.py quote / legacy_quote ask discount()): the fixed price × (100 − pct) %,
  never below the service's floor / NPC base (bounds lo). A 🤝 thương lượng service keeps its talk (no discount).
  Money never moves here: every fair order is an ordinary order of Phố dịch vụ (escrow, 95 % / 5 % burned, refunds).
* 🎭 Trình diễn: the owner runs a career-themed show (town_fair_content SHOWS, CAREER_SHOWS) for SHOW_SECONDS, at most
  SHOWS_MAX a fair, one every SHOW_GAP; mood +SHOW_MOOD, and +1 for each of the first WATCH_MOOD watchers.
* 😵 Oái oăm moments (owner's standing rule): while the owner keeps the booth open they come one at a time (the first
  MOMENT_FIRST after opening, then every MOMENT_EVERY, at most MOMENTS_MAX): a child knocks the display over, sudden
  rain, a neighbour's loudspeaker… three choices, each moving the booth's mood (điểm gian hàng, 0–100, from MOOD_START);
  no answer within MOMENT_ANSWER: MISS_MOOD.

Visitors
* The fair sheet lists the open booths grouped by career group, shows first, then the most served; each booth's
  services with the fair price and the usual one. Ordering opens Phố dịch vụ on that provider and service (no new
  payment path).
* 🎟️ One stamp per career and fair: a completed order at that career's booth (held inside the fair, after the booth
  opened), or watching one of its shows while it runs. STAMP_TIERS stamps unlock a 🎨 Phong cách cosmetic each (claimed
  once: fair_rewards row + a live_effects row of kind 'tfair' in one transaction, paid into the save by
  game/live_effects.py; 2.4.66 leaves such a row pending).

Leaderboard
* 🛎️ Phục vụ nhiều nhất (distinct customers of completed fair orders, a spouse not counted) and ⭐ Điểm gian hàng (mood
  ± the counted stars of those orders: svc_reviews.counted),
  while the fair runs and until SETTLE_HOURS after it (late orders still count); then the housekeeping freezes it into
  fair_events.board (status final, archived, never deleted) and grants once: a booth that served HOST_SERVED → 🎪 Chủ gian
  hội chợ, the top TOP of each board → their title (served ≥ 1).

Tables (game/pg_schema.py SCHEMA_VERSION 74): fair_events, fair_booths, fair_stamps, fair_rewards, fair_config. No save
key. Caches: the admin config (one entry, CFG_TTL), boards and booth lists (bounded LRU, a few seconds).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import secrets
import threading
import time
from collections import OrderedDict

from . import marriage as mr
from . import town_fair_content as C

VN = datetime.timezone(datetime.timedelta(hours=7))
NAME, ICON = 'Hội chợ việc làm', '🎪'
WEEKDAY = 5                        # Saturday (Monday 0)
WEEK_START, WEEK_END = 14 * 60, 17 * 60   # minutes after midnight, Vietnam time
SOON_HOURS = 24                    # "sắp mở" from this long before
SPECIAL_MAX_HOURS = 6
PCTS = (10, 15, 20, 25, 30)
PCT_DEFAULT = 15
SETTLE_HOURS = 48                  # orders held inside the fair and completed this long after still count
MOOD_START = 70
SHOW_SECONDS, SHOW_GAP, SHOWS_MAX, SHOW_MOOD = 300, 600, 8, 2
WATCH_MOOD, WATCH_MAX = 3, 60
MOMENT_FIRST, MOMENT_EVERY, MOMENT_ANSWER, MOMENTS_MAX, MISS_MOOD = 300, 720, 600, 6, -5
LOG_MAX = 12
PAGE = 30
BOOTHS_MAX = 600                   # booths read for one fair's list (newest beyond it wait)
TOP = 3
HOST_SERVED = 3
BOARD_ROWS = 20
ARCHIVE = 8
CFG_TTL = 30.0
BOARD_TTL, LIST_TTL, CACHE_MAX = 20.0, 8.0, 32
FX = 'tfair'                       # live_effects kind (game/live_effects.py)


class FairError(mr.MarriageError):
    """A refusal shown as is (the server answers a MarriageError with its status and code)."""


def need(cond, message: str, code: str = 'fair_error', status: int = 400):
    if not cond:
        raise FairError(message, code, status)


def now() -> float:
    return time.time()


def off() -> bool:
    return os.environ.get('MNL_FAIR_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _load(raw, default):
    try:
        v = json.loads(raw) if raw else default
    except (TypeError, ValueError):
        return default
    return v if isinstance(v, type(default)) else default


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def hhmm(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).strftime('%H:%M')


# ---------------------------------------------------------------- careers
def career_name(career: str) -> str:
    from .content import CAREER_META
    return str((CAREER_META.get(career) or {}).get('short') or career)


def careers() -> dict:
    """{career id: group id} of every career of the game."""
    from .content import CAREER_META, CATALOG
    cat = {r['id']: r.get('category') for r in CATALOG}
    out = {}
    for cid in CAREER_META:
        g = C.GROUP_OF.get(cid) or cat.get(cid)
        out[cid] = g if g in C.GROUP_IDS else 'service'
    return out


def shows_for(career: str) -> list:
    group = careers().get(career, 'service')
    rows = ([C.CAREER_SHOWS[career]] if career in C.CAREER_SHOWS else []) + list(C.SHOWS[group])
    return [dict(id=a, icon=b, name=c, line=d) for a, b, c, d in rows]


# ---------------------------------------------------------------- the calendar and the admin's switches
_CFG = {'at': -1e18, 'v': None}
_LOCK = threading.Lock()
_BOARDS: OrderedDict = OrderedDict()
_LISTS: OrderedDict = OrderedDict()


def clear_cache() -> None:
    with _LOCK:
        _CFG.update(at=-1e18, v=None)
        _BOARDS.clear()
        _LISTS.clear()


def _cache_get(cache, key, ttl):
    with _LOCK:
        hit = cache.get(key)
        if hit and 0 <= now() - hit[0] < ttl:
            cache.move_to_end(key)
            return hit[1]
    return None


def _cache_put(cache, key, value):
    with _LOCK:
        cache[key] = (now(), value)
        cache.move_to_end(key)
        while len(cache) > CACHE_MAX:
            cache.popitem(last=False)


def _cfg_default() -> dict:
    return dict(weekly=True, special=None)


def config(db, t: float | None = None, fresh: bool = False) -> dict:
    """{weekly: bool, special: {id, starts, ends} | None}: the admin's switches, read at most once per CFG_TTL."""
    t = now() if t is None else t
    with _LOCK:
        if not fresh and _CFG['v'] is not None and 0 <= time.monotonic() - _CFG['at'] < CFG_TTL:
            return dict(_CFG['v'])
    rows = {r['k']: r['v'] for r in db.execute('SELECT k, v FROM fair_config').fetchall()}
    sp = _load(rows.get('special'), {})
    special = dict(id=str(sp['id']), starts=float(sp['starts']), ends=float(sp['ends'])) if (
        isinstance(sp.get('id'), str) and isinstance(sp.get('starts'), (int, float)) and isinstance(sp.get('ends'), (int, float))) else None
    v = dict(weekly=rows.get('weekly', '1') != '0', special=special)
    with _LOCK:
        _CFG.update(at=time.monotonic(), v=v)
    return dict(v)


def _cached_cfg() -> dict:
    with _LOCK:
        return dict(_CFG['v']) if _CFG['v'] is not None else _cfg_default()


def weekly_event(t: float) -> dict:
    """The weekly fair now on, or the next one: {id, kind, starts, ends}."""
    d = datetime.datetime.fromtimestamp(t, VN)
    day = d.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=(WEEKDAY - d.weekday()) % 7)
    for _ in range(2):
        starts, ends = (day + datetime.timedelta(minutes=WEEK_START)).timestamp(), (day + datetime.timedelta(minutes=WEEK_END)).timestamp()
        if t < ends:
            return dict(id='w' + day.strftime('%Y%m%d'), kind='week', starts=starts, ends=ends)
        day += datetime.timedelta(days=7)
    raise AssertionError('unreachable')


def _events(cfg: dict, t: float) -> list:
    out = []
    if cfg.get('special') and t < cfg['special']['ends']:
        out.append(dict(cfg['special'], kind='special'))
    if cfg.get('weekly'):
        out.append(weekly_event(t))
    return sorted(out, key=lambda e: e['starts'])


def _now_of(cfg: dict, t: float) -> dict:
    """{state: open | soon | closed | off, event (the one on, or the next), next}"""
    if off():
        return dict(state='off', event=None)
    evs = _events(cfg, t)
    cur = next((e for e in evs if e['starts'] <= t < e['ends']), None)
    if cur:
        return dict(state='open', event=cur)
    nxt = next((e for e in evs if e['starts'] > t), None)
    if nxt and nxt['starts'] - t <= SOON_HOURS * 3600:
        return dict(state='soon', event=nxt)
    return dict(state='closed', event=nxt)


def current(db, t: float | None = None) -> dict | None:
    """The fair on now ({id, kind, starts, ends}) or None (off, or between fairs)."""
    if off():
        return None
    t = now() if t is None else t
    st = _now_of(config(db, t), t)
    return st['event'] if st['state'] == 'open' else None


def status(db, t: float | None = None) -> dict:
    t = now() if t is None else t
    return _now_of(config(db, t), t)


def _public_status(st: dict, t: float) -> dict:
    e = st.get('event')
    return dict(state=st['state'], id=e['id'] if e else '', kind=e['kind'] if e else '', starts=int(e['starts']) if e else 0,
                ends=int(e['ends']) if e else 0, now=int(t))


def hint(t: float | None = None) -> dict | None:
    """/api/bootstrap `ui.tfair` (no database: the process's copy of the switches): {state, starts, ends} while a fair
    is on or soon; None otherwise."""
    if off():
        return None
    t = now() if t is None else t
    st = _now_of(_cached_cfg(), t)
    return _public_status(st, t) if st['state'] in ('open', 'soon') else None


def news_line(store, t: float | None = None) -> dict | None:
    """/api/news `tfair`: the fair's status (the client's menu entry and the 2.5D signpost follow it) and its ticker line,
    played once per key on a device. None when nothing is on or soon (an older page ignores the field)."""
    if off():
        return None
    t = now() if t is None else t
    with _LOCK:
        fresh = _CFG['v'] is not None and 0 <= time.monotonic() - _CFG['at'] < CFG_TTL
    try:
        if fresh:   # every player's poll: no connection while the process's copy of the switches is fresh
            st = _now_of(_cached_cfg(), t)
        else:
            with store.connect() as db:
                st = status(db, t)
    except Exception:  # noqa: BLE001 - the ticker never fails for this
        st = _now_of(_cached_cfg(), t)
    if st['state'] not in ('open', 'soon'):
        return None
    e = st['event']
    out = _public_status(st, t)
    if st['state'] == 'open':
        out.update(key='tfair:' + e['id'], text=f'🎪 Hội chợ việc làm đang mở tới {hhmm(e["ends"])}: mở gian hàng nghề của bạn, giảm giá '
                                                 'cho khách, đi dạo góp 🎟️ tem đổi quà! Khu phố → Hội chợ việc làm.')
    else:
        day = 'Hôm nay' if datetime.datetime.fromtimestamp(t, VN).date() == datetime.datetime.fromtimestamp(e['starts'], VN).date() else 'Ngày mai'
        out.update(key='tfair-soon:' + e['id'], text=f'🎪 {day} {hhmm(e["starts"])} có Hội chợ việc làm: mọi nghề mở gian hàng, giảm giá, '
                                                     'trình diễn, góp 🎟️ tem đổi quà. Nhớ ghé nhé!')
    return out


# ---------------------------------------------------------------- the discount (game/service_market.py asks it)
def discount(db, provider: str, career: str, t: float | None = None) -> int:
    """The fair discount (percent) this provider gives on their fixed prices of `career` now; 0 outside a fair or a
    booth. One indexed query while a fair is on, none otherwise."""
    if off() or not provider or not career:
        return 0
    ev = current(db, t)
    if not ev:
        return 0
    r = db.execute('SELECT pct FROM fair_booths WHERE event=? AND sid=? AND career=? AND open_=1', (ev['id'], provider, career)).fetchone()
    return int(r['pct']) if r and int(r['pct']) in PCTS else 0


def apply_pct(unit: int, lo: int, pct: int) -> int:
    """A unit price with the fair's percent off, never below the lowest the market allows (floor / NPC base)."""
    if not pct:
        return unit
    return max(int(lo), int(unit) - int(unit) * int(pct) // 100)


# ---------------------------------------------------------------- rows
def _ensure_event(db, ev: dict, t: float) -> None:
    db.execute('INSERT INTO fair_events(id, kind, starts, ends, created_at) VALUES(?,?,?,?,?) ON CONFLICT (id) DO NOTHING',
               (ev['id'], ev['kind'], ev['starts'], ev['ends'], t))


def _event_row(db, eid: str) -> dict | None:
    r = db.execute('SELECT * FROM fair_events WHERE id=?', (eid,)).fetchone()
    return dict(r) if r else None


def _booth(db, eid: str, sid: str, lock: bool = False) -> dict | None:
    r = db.execute('SELECT * FROM fair_booths WHERE event=? AND sid=?' + (' FOR UPDATE' if lock else ''), (eid, sid)).fetchone()
    if not r:
        return None
    b = dict(r)
    b['data'] = _load(b['data'], {})
    return b


def _save(db, b: dict, t: float) -> None:
    db.execute('UPDATE fair_booths SET pct=?, open_=?, mood=?, shows=?, watchers=?, moments=?, handled=?, missed=?, show_until=?, '
               'show_next=?, next_moment=?, data=?, updated_at=? WHERE event=? AND sid=?',
               (b['pct'], b['open_'], max(0, min(100, int(b['mood']))), b['shows'], b['watchers'], b['moments'], b['handled'], b['missed'],
                b['show_until'], b['show_next'], b['next_moment'], _json(b['data']), t, b['event'], b['sid']))


def _log(b: dict, icon: str, text: str, d: int, t: float) -> None:
    rows = b['data'].setdefault('log', [])
    rows.append(dict(icon=icon, text=text[:200], d=int(d), at=int(t)))
    del rows[:-LOG_MAX]


def _tick(b: dict, ev: dict, t: float) -> bool:
    """The booth's clock: a moment left unanswered is missed; the next one comes when it is due (an open booth, during
    its fair). True when the row changed."""
    changed = False
    m = b['data'].get('moment')
    if isinstance(m, dict) and t > float(m.get('due') or 0):
        mm = C.MOMENT_INDEX.get(m.get('key'))
        b['mood'] += MISS_MOOD
        b['missed'] += 1
        _log(b, mm[1] if mm else '😵', 'Bạn bận quá, không kịp xử lý: ' + (mm[2] if mm else ''), MISS_MOOD, t)
        b['data'].pop('moment', None)
        b['next_moment'] = t + MOMENT_EVERY
        changed = True
    elif m is not None and not isinstance(m, dict):
        b['data'].pop('moment', None)
        changed = True
    if (b['open_'] and 'moment' not in b['data'] and b['moments'] < MOMENTS_MAX and ev['starts'] <= t < ev['ends']
            and t >= b['next_moment']):
        used = set(b['data'].get('used') or [])
        pool = [x for x in C.MOMENTS if x[0] not in used] or list(C.MOMENTS)
        pick = pool[int(_h(f'{b["event"]}|{b["sid"]}|{b["moments"]}'), 16) % len(pool)]
        b['data']['moment'] = dict(key=pick[0], at=int(t), due=int(t + MOMENT_ANSWER))
        b['data']['used'] = (list(used) + [pick[0]])[-len(C.MOMENTS):]
        b['moments'] += 1
        changed = True
    return changed


# ---------------------------------------------------------------- fair orders, stamps, the board
def _fair_orders(db, ev: dict, provider: str | None = None, buyer: str | None = None) -> list:
    """Completed orders of a fair: (order id, provider, buyer, career). A fair order is an order of Phố dịch vụ (or a
    legacy workplace order) paid inside the fair's window, after the booth opened, for that booth's career."""
    out = []
    extra, args = '', [ev['id'], ev['starts'], ev['ends']]
    if provider:
        extra += ' AND o.provider=?'
        args.append(provider)
    if buyer:
        extra += ' AND o.buyer=?'
        args.append(buyer)
    for r in db.execute("SELECT o.id, o.provider, o.buyer, o.career FROM svc_orders o JOIN fair_booths b ON b.event=? AND b.sid=o.provider "
                        "AND b.career=o.career WHERE o.kind='svc' AND o.status='done' AND o.held_at>=? AND o.held_at<? AND o.held_at>=b.opened_at"
                        + extra + ' LIMIT 20000', tuple(args)).fetchall():
        out.append((r['id'], r['provider'], r['buyer'], r['career']))
    extra = extra.replace('o.provider', 'w.provider').replace('o.buyer', 'w.customer')
    for r in db.execute("SELECT w.id, w.provider, w.customer, w.data, b.career FROM work_service_orders w JOIN fair_booths b ON b.event=? "
                        "AND b.sid=w.provider WHERE w.status='completed' AND w.created_at>=? AND w.created_at<? AND w.created_at>=b.opened_at"
                        + extra + ' LIMIT 20000', tuple(args)).fetchall():
        d = _load(r['data'], {})
        if d.get('kind') != 'quay' and (d.get('career') or d.get('target')) == r['career']:
            out.append((r['id'], r['provider'], r['customer'], r['career']))
    return out


def _stars(db, ids: list) -> dict:
    out = {}
    for i in range(0, len(ids), 500):
        part = ids[i:i + 500]
        marks = ','.join('?' * len(part))
        # only ratings that moved a reputation (svc_reviews.counted: one a week per buyer and provider, accounts ≥ 3 days)
        for r in db.execute(f'SELECT order_id, stars FROM svc_reviews WHERE order_id IN ({marks}) AND counted=1', tuple(part)).fetchall():
            out[r['order_id']] = int(r['stars'])
    return out


def score_of(mood: int, stars: list) -> int:
    """⭐ Điểm gian hàng: the booth's mood, moved by its customers' stars ((avg − 3) × 5), 0–100."""
    s = int(mood)
    if stars:
        s += round((sum(stars) / len(stars) - 3) * 5)
    return max(0, min(100, s))


def _spouses(db, sids) -> dict:
    """{sid: their husband or wife} for these players (married couples only)."""
    sids = sorted(sids)
    if not sids:
        return {}
    marks = ','.join('?' * len(sids))
    out = {}
    for r in db.execute(f"SELECT a, b FROM couples WHERE status='married' AND (a IN ({marks}) OR b IN ({marks}))", (*sids, *sids)).fetchall():
        out[r['a']], out[r['b']] = r['b'], r['a']
    return out


def _compute_board(db, ev: dict) -> dict:
    booths = [dict(r) for r in db.execute('SELECT sid, pid, career, mood, shows, watchers, handled, missed, opened_at FROM fair_booths '
                                          'WHERE event=? ORDER BY opened_at LIMIT ?', (ev['id'], BOOTHS_MAX * 4)).fetchall()]
    orders = _fair_orders(db, ev)
    stars = _stars(db, [o[0] for o in orders])
    spouse = _spouses(db, {b['sid'] for b in booths})
    served, st = {}, {}
    for oid, prov, buyer, _ in orders:
        if buyer == spouse.get(prov):   # a husband or wife buying from the booth serves nobody new
            continue
        served.setdefault(prov, set()).add(buyer)   # 🧑‍🤝‍🧑 distinct customers, not orders
        if oid in stars:
            st.setdefault(prov, []).append(stars[oid])
    served = {k: len(v) for k, v in served.items()}
    rows = []
    for b in booths:
        s = st.get(b['sid'], [])
        rows.append(dict(sid=b['sid'], pid=b['pid'], career=b['career'], served=served.get(b['sid'], 0), n=len(s),
                         avg=round(sum(s) / len(s), 2) if s else 0.0, score=score_of(b['mood'], s), shows=int(b['shows']),
                         watchers=int(b['watchers']), opened_at=float(b['opened_at'])))
    by_served = sorted([r for r in rows if r['served'] > 0], key=lambda r: (-r['served'], -r['score'], r['opened_at']))
    by_score = sorted([r for r in rows if r['served'] > 0 or r['shows'] > 0], key=lambda r: (-r['score'], -r['served'], r['opened_at']))
    return dict(served=by_served, rated=by_score, booths=len(rows), orders=len(orders),
                stamps=int(db.execute('SELECT COUNT(*) AS n FROM fair_stamps WHERE event=?', (ev['id'],)).fetchone()['n']))


def _people(db, rows: list, cache: dict) -> list:
    from . import service_market as sm
    out = []
    for i, r in enumerate(rows, 1):
        if r['sid'] not in cache:
            cache[r['sid']] = sm._person(db, r['sid'])
        out.append(dict({k: v for k, v in r.items() if k != 'sid'}, rank=i, who=cache[r['sid']], career_name=career_name(r['career'])))
    return out


def board(store, eid: str | None = None, t: float | None = None) -> dict:
    """🏆 One fair's leaderboard: live (cached BOARD_TTL) while it settles, the frozen snapshot once final; the archive."""
    t = now() if t is None else t
    with store.connect() as db:
        if not eid:
            st = status(db, t)
            e = st['event'] if st['state'] == 'open' else None
            r = _event_row(db, e['id']) if e else db.execute('SELECT * FROM fair_events ORDER BY starts DESC LIMIT 1').fetchone()
            eid = (e or {}).get('id') or (dict(r)['id'] if r else '')
        past = [dict(id=r['id'], kind=r['kind'], starts=int(r['starts']), ends=int(r['ends']), final=r['status'] == 'final')
                for r in db.execute('SELECT id, kind, starts, ends, status FROM fair_events ORDER BY starts DESC LIMIT ?', (ARCHIVE,)).fetchall()]
        row = _event_row(db, eid) if eid else None
        if not row:
            return dict(event=None, served=[], rated=[], past=past)
        if row['status'] == 'final':
            snap = _load(row['board'], {})
            return dict(event=dict(id=row['id'], kind=row['kind'], starts=int(row['starts']), ends=int(row['ends']), final=True),
                        served=snap.get('served', []), rated=snap.get('rated', []), booths=snap.get('booths', 0),
                        orders=snap.get('orders', 0), stamps=snap.get('stamps', 0), past=past)
    key = (str(store.path), eid)
    hit = _cache_get(_BOARDS, key, BOARD_TTL)
    if hit is None:
        with store.connect() as db:
            ev = dict(id=row['id'], starts=row['starts'], ends=row['ends'])
            raw = _compute_board(db, ev)
            cache = {}
            hit = dict(raw, served=_people(db, raw['served'][:BOARD_ROWS], cache), rated=_people(db, raw['rated'][:BOARD_ROWS], cache),
                       counts={r['sid']: r['served'] for r in raw['served']})
        _cache_put(_BOARDS, key, hit)
    return dict(event=dict(id=row['id'], kind=row['kind'], starts=int(row['starts']), ends=int(row['ends']), final=False,
                           settles=int(row['ends'] + SETTLE_HOURS * 3600)),
                served=hit['served'], rated=hit['rated'], booths=hit['booths'], orders=hit['orders'], stamps=hit['stamps'], past=past)


def _served_counts(store, ev: dict) -> dict:
    board(store, ev['id'])
    hit = _cache_get(_BOARDS, (str(store.path), ev['id']), BOARD_TTL * 10)
    return dict((hit or {}).get('counts') or {})


def _sync_stamps(db, sid: str, t: float) -> int:
    """🎟️ The completed fair orders of this visitor become stamps (one per fair and career), for every fair not final."""
    n = 0
    for e in db.execute("SELECT id, starts, ends FROM fair_events WHERE status='open' ORDER BY starts DESC LIMIT 3").fetchall():
        e = dict(e)
        for oid, prov, _, career in _fair_orders(db, e, buyer=sid):
            n += db.execute("INSERT INTO fair_stamps(event, sid, career, src, ref, booth, at) VALUES(?,?,?,'order',?,?,?) ON CONFLICT DO NOTHING",
                            (e['id'], sid, career, oid, prov, t)).rowcount
    return n


def _stamps(db, eid: str, sid: str) -> list:
    return [dict(career=r['career'], src=r['src'], at=int(r['at'])) for r in
            db.execute('SELECT career, src, at FROM fair_stamps WHERE event=? AND sid=? ORDER BY at', (eid, sid)).fetchall()]


def _tiers(db, eid: str, sid: str, n: int) -> list:
    from . import spend_content as SC
    got = {int(r['tier']) for r in db.execute('SELECT tier FROM fair_rewards WHERE event=? AND sid=?', (eid, sid)).fetchall()}
    out = []
    for i, (k, item) in enumerate(C.STAMP_TIERS, 1):
        it = SC.STYLE_ITEMS[item]
        out.append(dict(tier=i, need=k, item=item, kind=it['kind'], emoji=it['emoji'], name=it['name'], got=i in got, ready=n >= k and i not in got))
    return out


# ---------------------------------------------------------------- reading
def _actor(store, token) -> str:
    sid = store.key(token)
    with store.connect() as db:
        need(db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone(), 'Đăng nhập để vào Hội chợ việc làm nhé.', 'login_required', 401)
    return sid


def _blocks(db, sid: str) -> tuple:
    from . import social
    pid = social.pid_of(sid)
    a = {r['sid'] if r['target'] == sid else r['target'] for r in
         db.execute('SELECT sid, target FROM marriage_blocks WHERE sid=? OR target=?', (sid, sid)).fetchall()}
    b = {r['pid'] if r['target'] == pid else r['target'] for r in
         db.execute('SELECT pid, target FROM blocks WHERE pid=? OR target=?', (pid, pid)).fetchall()}
    return a, b


def _items_of(db, rows: list, t: float) -> dict:
    """{provider: [service listing]} of these booths: their own Phố dịch vụ services of the booth's career (with the fair
    price, the usual one, the place and offer of a legacy service)."""
    from . import service_market as sm
    if not rows:
        return {}
    want = {r['sid']: r['career'] for r in rows}
    sids = sorted(want)
    marks = ','.join('?' * len(sids))
    settings = [dict(r) for r in db.execute(f'SELECT s.*, r.n AS rn, r.stars AS rs, r.deals AS rd FROM svc_settings s LEFT JOIN svc_rep r '
                                            f'ON r.provider=s.provider WHERE s.provider IN ({marks}) AND s.on_=1', tuple(sids)).fetchall()]
    settings = [s for s in settings if want.get(s['provider']) == s['career']]
    places = {}
    owners = sorted({s['provider'] for s in settings if (sm.get_spec(s['career'], s['service']) or {}).get('legacy')})
    if owners:
        m2 = ','.join('?' * len(owners))
        for p in db.execute(f'SELECT * FROM work_visit_places WHERE owner IN ({m2})', tuple(owners)).fetchall():
            places.setdefault(p['owner'], []).append(dict(p))
    out = {}
    for s in settings:
        x = sm._listing(db, s, '', t, set(), places)
        if not x:
            continue
        offer = (x.get('offers') or [None])[0]
        usual = (offer or {}).get('usual') if x['legacy'] else x.get('usual')
        out.setdefault(s['provider'], []).append(dict(
            career=x['career'], service=x['service'], name=x['name'], icon=x['icon'], unit=x['unit'], mode=x['mode'],
            price=int((offer or {}).get('price') or x.get('price') or 0), usual=int(usual or x.get('price') or 0),
            fair=int((offer or {}).get('fair') or x.get('fair') or 0), available=bool(x.get('available')),
            place=(offer or {}).get('place', ''), offer_id=(offer or {}).get('offer_id', ''), label=str((offer or {}).get('label') or '')[:60]))
    for v in out.values():
        v.sort(key=lambda i: (not i['available'], i['price']))
        del v[6:]
    return out


def _booth_public(b: dict, who: dict, online: bool, served: int, items: list, t: float) -> dict:
    show = b['data'].get('show') if b['show_until'] > t else None
    return dict(pid=b['pid'], who=who, online=online, career=b['career'], career_name=career_name(b['career']),
                group=careers().get(b['career'], 'service'), pct=int(b['pct']), mood=int(b['mood']), served=served,
                shows=int(b['shows']), watchers=int(b['watchers']),
                show=dict(show, until=int(b['show_until'])) if isinstance(show, dict) else None, items=items)


def _list(store, ev: dict, t: float) -> list:
    """Every open booth of a fair as visitors see it (shared by everyone, cached LIST_TTL seconds), shows first."""
    key = (str(store.path), ev['id'])
    hit = _cache_get(_LISTS, key, LIST_TTL)
    if hit is not None:
        return hit
    counts = _served_counts(store, ev)
    from . import service_market as sm
    with store.connect() as db:
        rows = [dict(r) for r in db.execute('SELECT * FROM fair_booths WHERE event=? AND open_=1 ORDER BY opened_at LIMIT ?',
                                            (ev['id'], BOOTHS_MAX)).fetchall()]
        for r in rows:
            r['data'] = _load(r['data'], {})
        online = sm._online(db, [r['sid'] for r in rows], t)
        items = _items_of(db, rows, t)
        out = []
        for r in rows:
            out.append(dict(_booth_public(r, sm._person(db, r['sid']), r['sid'] in online, counts.get(r['sid'], 0), items.get(r['sid'], []), t),
                            _sid=r['sid']))
    out.sort(key=lambda x: (x['show'] is None, -x['served'], not x['online'], -x['mood']))
    _cache_put(_LISTS, key, out)
    return out


def _mine(db, ev: dict | None, sid: str, t: float, served: int) -> dict | None:
    if not ev:
        return None
    b = _booth(db, ev['id'], sid)
    if not b:
        return None
    m = b['data'].get('moment')
    mm = C.MOMENT_INDEX.get(m.get('key')) if isinstance(m, dict) else None
    show = b['data'].get('show') if b['show_until'] > t else None
    with_items = _items_of(db, [b], t).get(sid, [])
    return dict(career=b['career'], career_name=career_name(b['career']), pct=int(b['pct']), open=bool(b['open_']), mood=int(b['mood']),
                served=served, shows=int(b['shows']), shows_max=SHOWS_MAX, watchers=int(b['watchers']), handled=int(b['handled']),
                missed=int(b['missed']), moments=int(b['moments']), moments_max=MOMENTS_MAX,
                show=dict(show, until=int(b['show_until']), watching=len(b['data'].get('watch') or [])) if isinstance(show, dict) else None,
                show_next=int(b['show_next']), menu=shows_for(b['career']),
                moment=dict(key=mm[0], icon=mm[1], text=mm[2], due=int(m['due']), opts=[dict(id=o[0], label=o[1]) for o in mm[3]]) if mm else None,
                log=list(reversed(b['data'].get('log') or [])), items=with_items, next_moment=int(b['next_moment']))


def view(store, sid: str, query: dict | None = None, state: dict | None = None) -> dict:
    """The fair sheet: its status, my booth (the clock of its moments runs here), the booths (by group), my 🎟️ stamps."""
    query = query or {}
    t = now()
    group = str(query.get('group') or '')
    group = group if group in C.GROUP_IDS or group == 'show' else ''
    try:
        offset = max(0, min(BOOTHS_MAX, int(query.get('offset') or 0)))
    except (TypeError, ValueError):
        offset = 0
    with store.connect() as db:
        st = status(db, t)
        ev = st['event'] if st['state'] == 'open' else None
        b0 = _booth(db, ev['id'], sid) if ev else None
    if b0 and _tick(b0, ev, t):
        def tick(db):
            b = _booth(db, ev['id'], sid, lock=True)
            if b and _tick(b, ev, t):
                _save(db, b, t)
        store.transaction(tick)
    store.transaction(lambda db: _sync_stamps(db, sid, t))
    booths = _list(store, ev, t) if ev else []
    counts = {g: 0 for g in C.GROUP_IDS}
    for x in booths:
        counts[x['group']] = counts.get(x['group'], 0) + 1
    with store.connect() as db:
        mb, pb = _blocks(db, sid)
        seen = [x for x in booths if x['_sid'] == sid or (x['_sid'] not in mb and x['pid'] not in pb)]
        if group == 'show':
            seen = [x for x in seen if x['show']]
        elif group:
            seen = [x for x in seen if x['group'] == group]
        page = seen[offset:offset + PAGE]
        sev = ev or (lambda r: dict(r) if r else None)(db.execute("SELECT id, kind, starts, ends FROM fair_events WHERE status='open' ORDER BY starts DESC LIMIT 1").fetchone())
        stamps = _stamps(db, sev['id'], sid) if sev else []
        got = {s['career'] for s in stamps}
        watched = set()
        if ev:
            for x in page:
                if x['show'] and x['_sid'] != sid:
                    b = _booth(db, ev['id'], x['_sid'])
                    if b and sid in (b['data'].get('watch') or []):
                        watched.add(x['pid'])
        served = next((x['served'] for x in booths if x['_sid'] == sid), 0)
        mine = _mine(db, ev, sid, t, served)
        if mine and not mine['open']:
            served = _served_counts(store, ev).get(sid, 0)
            mine['served'] = served
        out_booths = [dict({k: v for k, v in x.items() if k != '_sid'}, mine=x['_sid'] == sid, stamped=x['career'] in got,
                           watched=x['pid'] in watched) for x in page]
        stamp_card = dict(event=sev['id'] if sev else '', n=len(stamps), stamps=[dict(s, career_name=career_name(s['career'])) for s in stamps],
                          tiers=_tiers(db, sev['id'], sid, len(stamps)) if sev else [], final_at=int(sev['ends'] + SETTLE_HOURS * 3600) if sev else 0)
    can = []
    if ev and not mine:
        loaded = state if state is not None else (mr._read_state(store, sid) or [None])[0]
        from . import service_market as sm
        for cid in careers():
            if loaded and not sm._career_started(cid)(loaded):
                can.append(dict(career=cid, name=career_name(cid)))
    return dict(now=int(t), fair=_public_status(st, t), booths=out_booths, next=offset + PAGE if len(seen) > offset + PAGE else None,
                total=len(seen), counts=counts, group=group, groups=[dict(id=a, icon=b, name=c) for a, b, c in C.GROUPS],
                mine=mine, can_open=can, stamps=stamp_card, rules=rules(), off=off())


def rules() -> dict:
    return dict(pcts=list(PCTS), pct_default=PCT_DEFAULT, show_seconds=SHOW_SECONDS, show_gap=SHOW_GAP, shows_max=SHOWS_MAX,
                moments_max=MOMENTS_MAX, answer=MOMENT_ANSWER, settle_hours=SETTLE_HOURS, top=TOP, host_served=HOST_SERVED,
                week=dict(day=WEEKDAY, start=WEEK_START, end=WEEK_END), tiers=[dict(need=k, item=i) for k, i in C.STAMP_TIERS])


def get(store, token, state, sub: str, query: dict) -> dict:
    sid = _actor(store, token)
    if sub in ('', 'view'):
        return view(store, sid, query, state)
    if sub == 'board':
        return board(store, str((query or {}).get('event') or '')[:40] or None)
    raise FairError('Không có mục này.', 'not_found', 404)


# ---------------------------------------------------------------- writing
def _int(v, lo, hi, message='Số không hợp lệ.'):
    need(type(v) is int and lo <= v <= hi, message, 'bad_number')
    return v


def _open_ev(db, t):
    ev = current(db, t)
    need(ev, 'Hội chợ việc làm chưa mở. Hẹn bạn thứ Bảy, 14:00 nhé.', 'fair_closed', 409)
    return ev


def _stale():
    with _LOCK:
        _LISTS.clear()
        _BOARDS.clear()


def _open(store, sid, data, t):
    need(set(data) <= {'career', 'pct'}, 'Thông tin gian hàng không hợp lệ.')
    career = data.get('career')
    need(isinstance(career, str) and career in careers(), 'Chọn một nghề để mở gian nhé.', 'bad_career')
    pct = _int(data.get('pct', PCT_DEFAULT), PCTS[0], PCTS[-1], 'Mức giảm giá không hợp lệ.')
    need(pct in PCTS, 'Mức giảm giá không hợp lệ.', 'bad_number')
    loaded = mr._read_state(store, sid)
    need(loaded, 'Không tìm thấy tiến trình của bạn.', 'session_missing', 404)
    need((loaded[0].get('journey') or {}).get('story'), 'Hội chợ việc làm dùng hành trình.', 'not_story')
    from . import service_market as sm
    from . import social
    why = sm._career_started(career)(loaded[0])
    need(not why, 'Bạn cần làm nghề này trước rồi mới mở gian được.', 'not_started', 409)
    msg = ['']

    def run(db):
        ev = _open_ev(db, t)
        _ensure_event(db, ev, t)
        b = _booth(db, ev['id'], sid, lock=True)
        if b:
            need(b['career'] == career, f'Kỳ này bạn đã mở gian {career_name(b["career"])} rồi.', 'one_booth', 409)
            b.update(open_=1, pct=pct)
            _save(db, b, t)
            msg[0] = f'🎪 Gian {career_name(career)} mở lại, giảm {pct}%.'
            return
        db.execute('INSERT INTO fair_booths(event, sid, pid, career, pct, open_, mood, next_moment, data, opened_at, updated_at) '
                   'VALUES(?,?,?,?,?,1,?,?,?,?,?)', (ev['id'], sid, social.pid_of(sid), career, pct, MOOD_START, t + MOMENT_FIRST, '{}', t, t))
        msg[0] = f'🎪 Đã dựng gian {career_name(career)}! Dịch vụ của bạn ở Phố dịch vụ giảm {pct}% tới hết hội chợ.'
    store.transaction(run)
    return msg[0]


def _with_booth(store, sid, t, fn):
    out = ['']

    def run(db):
        ev = _open_ev(db, t)
        b = _booth(db, ev['id'], sid, lock=True)
        need(b, 'Bạn chưa mở gian hàng ở hội chợ này.', 'no_booth', 404)
        _tick(b, ev, t)
        out[0] = fn(db, b, ev)
        _save(db, b, t)
    store.transaction(run)
    return out[0]


def _pct(store, sid, data, t):
    need(set(data) <= {'pct'}, 'Thông tin không hợp lệ.')
    pct = _int(data.get('pct'), PCTS[0], PCTS[-1], 'Mức giảm giá không hợp lệ.')
    need(pct in PCTS, 'Mức giảm giá không hợp lệ.', 'bad_number')

    def fn(db, b, ev):
        b['pct'] = pct
        return f'Giá hội chợ: giảm {pct}%.'
    return _with_booth(store, sid, t, fn)


def _close(store, sid, data, t):
    def fn(db, b, ev):
        b['open_'] = 0
        b['data'].pop('moment', None)
        return 'Đã dọn gian. Giá của bạn trở lại như thường. Bấm “Mở lại gian” khi muốn bán tiếp.'
    return _with_booth(store, sid, t, fn)


def _show(store, sid, data, t):
    need(set(data) <= {'show'}, 'Thông tin không hợp lệ.')

    def fn(db, b, ev):
        need(b['open_'], 'Gian đang đóng. Mở lại gian trước nhé.', 'booth_closed', 409)
        sh = next((x for x in shows_for(b['career']) if x['id'] == data.get('show')), None)
        need(sh, 'Chọn một tiết mục nhé.', 'bad_show')
        need(b['shows'] < SHOWS_MAX, f'Kỳ này bạn đã diễn đủ {SHOWS_MAX} lần rồi. Nghỉ giọng chút nhé!', 'shows_max', 409)
        need(t >= b['show_next'], 'Vừa diễn xong, nghỉ tay một lát rồi diễn tiếp nhé.', 'show_wait', 409)
        need(ev['ends'] - t > 30, 'Hội chợ sắp đóng rồi.', 'fair_closing', 409)
        b['show_until'] = min(ev['ends'], t + SHOW_SECONDS)
        b['show_next'] = t + SHOW_GAP
        b['shows'] += 1
        b['mood'] += SHOW_MOOD
        b['data']['show'] = dict(sh, sid=secrets.token_hex(6))
        b['data']['watch'] = []
        _log(b, sh['icon'], f'Bạn trình diễn “{sh["name"]}”.', SHOW_MOOD, t)
        return f'{sh["icon"]} {sh["name"]}: {sh["line"]} Khách xem trong {SHOW_SECONDS // 60} phút tới được 🎟️ tem nghề của bạn.'
    out = _with_booth(store, sid, t, fn)
    _stale()
    return out


def _moment(store, sid, data, t):
    need(set(data) <= {'key', 'pick'}, 'Thông tin không hợp lệ.')

    def fn(db, b, ev):
        m = b['data'].get('moment')
        need(isinstance(m, dict) and m.get('key') == data.get('key'), 'Chuyện này qua rồi.', 'moment_gone', 409)
        mm = C.MOMENT_INDEX[m['key']]
        o = next((x for x in mm[3] if x[0] == data.get('pick')), None)
        need(o, 'Chọn một cách xử lý nhé.', 'bad_pick')
        b['mood'] += o[2]
        b['handled'] += 1
        b['data'].pop('moment', None)
        b['next_moment'] = t + MOMENT_EVERY
        _log(b, mm[1], o[3], o[2], t)
        return f'{mm[1]} {o[3]}'
    out = _with_booth(store, sid, t, fn)
    _stale()
    return out


def _watch(store, sid, data, t):
    need(set(data) <= {'pid'}, 'Thông tin không hợp lệ.')
    pid = data.get('pid')
    need(isinstance(pid, str) and len(pid) == 16, 'Không tìm thấy gian này.', 'not_found', 404)
    out = ['']

    def run(db):
        ev = _open_ev(db, t)
        r = db.execute('SELECT sid FROM fair_booths WHERE event=? AND pid=?', (ev['id'], pid)).fetchone()
        need(r, 'Không tìm thấy gian này.', 'not_found', 404)
        owner = r['sid']
        need(owner != sid, 'Bạn đang xem chính gian của mình mà 😄', 'own_booth')
        from . import work_visits
        need(not work_visits._blocked(db, sid, owner), 'Không tìm thấy gian này.', 'not_found', 404)
        b = _booth(db, ev['id'], owner, lock=True)
        sh = b['data'].get('show')
        need(b['open_'] and b['show_until'] > t and isinstance(sh, dict), 'Tiết mục vừa kết thúc. Chờ lượt diễn sau nhé!', 'show_over', 409)
        watch = list(b['data'].get('watch') or [])
        if sid not in watch and len(watch) < WATCH_MAX:
            watch.append(sid)
            b['watchers'] += 1
            if len(watch) <= WATCH_MOOD:
                b['mood'] += 1
            b['data']['watch'] = watch
            _save(db, b, t)
        got = db.execute("INSERT INTO fair_stamps(event, sid, career, src, ref, booth, at) VALUES(?,?,?,'show',?,?,?) ON CONFLICT DO NOTHING",
                         (ev['id'], sid, b['career'], str(sh.get('sid') or ''), owner, t)).rowcount
        out[0] = (f'{sh["icon"]} Bạn xem “{sh["name"]}”: {sh["line"]}' + (f' 🎟️ +1 tem {career_name(b["career"])}!' if got else ''))
    store.transaction(run)
    _stale()
    return out[0]


def _fx_id(eid: str, tag: str, sid: str) -> str:
    return f'tfair:{eid}:{tag}:{_h(sid)}'


def _grant(db, sid: str, eid: str, tag: str, items: list, why: str, t: float, extra: dict | None = None) -> bool:
    data = dict(event=eid, items=list(items), why=why, **(extra or {}))
    return bool(db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) ON CONFLICT DO NOTHING",
                           (_fx_id(eid, tag, sid), sid, FX, 1, json.dumps(data, ensure_ascii=False), t)).rowcount)


def _claim(store, sid, data, t):
    need(set(data) <= {'event', 'tier'}, 'Thông tin không hợp lệ.')
    eid = data.get('event')
    need(isinstance(eid, str) and 0 < len(eid) <= 40, 'Không tìm thấy kỳ hội chợ này.', 'not_found', 404)
    tier = _int(data.get('tier'), 1, len(C.STAMP_TIERS), 'Mốc tem không hợp lệ.')
    k, item = C.STAMP_TIERS[tier - 1]
    from . import spend_content as SC
    it = SC.STYLE_ITEMS[item]
    out = ['']

    def run(db):
        e = _event_row(db, eid)
        need(e, 'Không tìm thấy kỳ hội chợ này.', 'not_found', 404)
        db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))', ('tfair-claim:' + eid + '|' + sid,))
        if e['status'] == 'open':
            _sync_stamps(db, sid, t)
        n = int(db.execute('SELECT COUNT(*) AS n FROM fair_stamps WHERE event=? AND sid=?', (eid, sid)).fetchone()['n'])
        need(n >= k, f'Cần {k} tem của {k} nghề khác nhau. Bạn đang có {n}.', 'not_enough', 409)
        fresh = db.execute('INSERT INTO fair_rewards(event, sid, tier, item, at) VALUES(?,?,?,?,?) ON CONFLICT DO NOTHING',
                           (eid, sid, tier, item, t)).rowcount
        if fresh:
            _grant(db, sid, eid, f's{tier}', [item], 'stamps', t, dict(n=n))
            out[0] = f'{it["emoji"]} Đổi {k} tem: {it["name"]}! Đeo ở 🎨 Phong cách.'
        else:
            out[0] = f'Bạn đã đổi mốc {k} tem rồi.'
    store.transaction(run)
    return out[0]


ACTIONS = dict(open=_open, pct=_pct, close=_close, show=_show, moment=_moment, watch=_watch, claim=_claim)


def post(store, token, state, sub: str, data: dict) -> dict:
    sid = _actor(store, token)
    need(isinstance(data, dict), 'Thông tin không hợp lệ.')
    fn = ACTIONS.get(sub)
    need(fn, 'Không có thao tác này.', 'not_found', 404)
    if sub in ('open', 'show', 'watch'):
        need(not off(), 'Hội chợ việc làm đang tạm nghỉ.', 'fair_off', 503)
    t = now()
    message = fn(store, sid, data, t)
    if sub in ('open', 'pct', 'close'):
        _stale()
    if sub == 'claim':
        from . import live_effects
        try:
            loaded = mr._read_state(store, sid)
            live_effects.on_load(store, token, loaded[0] if loaded else None)
        except Exception:  # noqa: BLE001 - paid at the next load otherwise
            pass
    return dict(message=message, view=view(store, sid, {}, None))


# ---------------------------------------------------------------- the reward into the save (game/live_effects.py apply)
def apply_fx(s: dict, p: dict, amount: int) -> str:
    """A 'tfair' live_effects row: 🎨 Phong cách items (titles, a frame) kept for good, once each."""
    from . import engine as e
    from . import spend as sp
    from . import spend_content as SC
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    items = data.get('items')
    e.need(isinstance(data.get('event'), str) and 0 < len(data['event']) <= 40 and isinstance(items, list) and 0 < len(items) <= 4
           and all(isinstance(x, str) and x in C.ITEM_IDS and x in SC.STYLE_ITEMS for x in items), 'Dữ liệu hội chợ không hợp lệ.')
    new = []
    for item in items:
        b = sp.get(s)
        if b and b['own'].get(item, 0) >= SC.PERMANENT:
            continue
        b = sp._ensure(s)
        if len(b['own']) >= sp.OWN_MAX and item not in b['own']:
            continue
        b['own'][item] = SC.PERMANENT
        it = SC.STYLE_ITEMS[item]
        new.append(f'{it["emoji"]} {it["name"]}')
    head = '🎪 Hội chợ việc làm' + (' khép lại.' if data.get('why') == 'booth' else ':')
    if data.get('why') == 'booth':
        head += f' Gian của bạn phục vụ {int(data.get("served") or 0)} lượt khách.'
    return head + (' 🎨 Mới: ' + ', '.join(new) + ' (đeo ở Phong cách).' if new else ' Bạn đã có món này rồi.')


# ---------------------------------------------------------------- housekeeping: open news, settle and archive
_swept = [0.0]


def _finalize(store, eid: str, t: float) -> bool:
    with store.connect() as db:
        row = _event_row(db, eid)
        if not row or row['status'] != 'open':
            return False
        raw = _compute_board(db, dict(id=row['id'], starts=row['starts'], ends=row['ends']))
        cache = {}
        snap = dict(served=_people(db, raw['served'][:BOARD_ROWS], cache), rated=_people(db, raw['rated'][:BOARD_ROWS], cache),
                    booths=raw['booths'], orders=raw['orders'], stamps=raw['stamps'])
    awards = {}
    for i, r in enumerate(raw['served'], 1):
        if r['served'] >= HOST_SERVED:
            awards.setdefault(r['sid'], dict(items=[], served=r['served']))['items'].append(C.HOST_ITEM)
        if i <= TOP:
            awards.setdefault(r['sid'], dict(items=[], served=r['served']))['items'].append(C.SERVED_ITEM)
    for i, r in enumerate([x for x in raw['rated'] if x['served'] > 0][:TOP], 1):
        awards.setdefault(r['sid'], dict(items=[], served=r['served']))['items'].append(C.RATED_ITEM)
    done = [False]

    def run(db):
        if db.execute("UPDATE fair_events SET status='final', board=?, final_at=? WHERE id=? AND status='open'",
                      (_json(snap), t, eid)).rowcount != 1:
            return
        for sid, a in awards.items():
            if db.execute('SELECT 1 FROM sessions WHERE sid=?', (sid,)).fetchone():
                _grant(db, sid, eid, 'b', a['items'], 'booth', t, dict(served=a['served']))
        top = snap['served'][0] if snap['served'] else None
        if top:
            mr._post_news(db, 'tfair', f'tfair:final:{eid}', f'🏆 Hội chợ việc làm khép lại: gian đắt khách nhất là {top["career_name"]} của '
                          f'{top["who"]["name"]} ({top["served"]} lượt). Cảm ơn {snap["booths"]} gian hàng!', '', '')
        done[0] = True
    store.transaction(run)
    _stale()
    return done[0]


def run_housekeeping(store, every: float = 60.0) -> int:
    """About once a minute: the open fair's row and its ticker line (once), then the fairs past their settle time are
    frozen and their booth titles granted (status-guarded: exactly once)."""
    t = now()
    if t - _swept[0] < every:
        return 0
    _swept[0] = t
    n = 0
    with store.connect() as db:
        config(db, t, fresh=True)
        ev = current(db, t)
    if ev:
        def announce(db):
            _ensure_event(db, ev, t)
            if db.execute('UPDATE fair_events SET announced=1 WHERE id=? AND announced=0', (ev['id'],)).rowcount:
                mr._post_news(db, 'tfair', f'tfair:open:{ev["id"]}', f'🎪 Hội chợ việc làm mở cửa tới {hhmm(ev["ends"])}! Mọi nghề dựng gian, '
                              'giảm giá, trình diễn. Ghé góp 🎟️ tem đổi quà nhé.', '', '')
        store.transaction(announce)
    with store.connect() as db:
        due = [r['id'] for r in db.execute("SELECT id FROM fair_events WHERE status='open' AND ends<? ORDER BY ends LIMIT 3",
                                           (t - SETTLE_HOURS * 3600,)).fetchall()]
    for eid in due:
        n += _finalize(store, eid, t)
    return n


# ---------------------------------------------------------------- admin
def admin_view(store) -> dict:
    t = now()
    with store.connect() as db:
        cfg = config(db, t, fresh=True)
        st = status(db, t)
        events = []
        for r in db.execute('SELECT * FROM fair_events ORDER BY starts DESC LIMIT ?', (ARCHIVE,)).fetchall():
            r = dict(r)
            n = lambda q: int(db.execute(q, (r['id'],)).fetchone()['n'])  # noqa: E731
            events.append(dict(id=r['id'], kind=r['kind'], starts=int(r['starts']), ends=int(r['ends']), status=r['status'],
                               booths=n('SELECT COUNT(*) AS n FROM fair_booths WHERE event=?'),
                               stamps=n('SELECT COUNT(*) AS n FROM fair_stamps WHERE event=?'),
                               rewards=n('SELECT COUNT(*) AS n FROM fair_rewards WHERE event=?')))
    return dict(now=int(t), off=off(), weekly=cfg['weekly'], special=cfg['special'], fair=_public_status(st, t), events=events,
                next_week=weekly_event(t), rules=rules())


def admin_act(store, admin: str, data: dict) -> dict:
    need(isinstance(data, dict), 'Thông tin không hợp lệ.')
    op = data.get('op')
    t = now()

    def put(db, k, v):
        db.execute('INSERT INTO fair_config(k, v, by_admin, updated_at) VALUES(?,?,?,?) ON CONFLICT (k) DO UPDATE SET v=excluded.v, '
                   'by_admin=excluded.by_admin, updated_at=excluded.updated_at', (k, v, str(admin)[:40], t))
    if op == 'weekly':
        on = data.get('on')
        need(isinstance(on, bool), 'Thông tin không hợp lệ.')
        store.transaction(lambda db: put(db, 'weekly', '1' if on else '0'))
    elif op == 'open_now':
        hours = _int(data.get('hours'), 1, SPECIAL_MAX_HOURS, f'Mở từ 1 đến {SPECIAL_MAX_HOURS} giờ.')

        def run(db):
            st = status(db, t)
            need(st['state'] != 'open', 'Đang có hội chợ mở rồi.', 'fair_open', 409)
            put(db, 'special', _json(dict(id='x' + str(int(t)), starts=t, ends=t + hours * 3600)))
        store.transaction(run)
    elif op == 'close_special':
        def run(db):
            cfg = config(db, t, fresh=True)
            sp = cfg['special']
            need(sp and sp['ends'] > t, 'Không có hội chợ đặc biệt nào đang mở.', 'none', 409)
            ends = max(sp['starts'], t)
            put(db, 'special', _json(dict(sp, ends=ends)))
            db.execute('UPDATE fair_events SET ends=? WHERE id=? AND status=?', (ends, sp['id'], 'open'))
        store.transaction(run)
    else:
        raise FairError('Không có thao tác này.', 'not_found', 404)
    clear_cache()
    return admin_view(store)
