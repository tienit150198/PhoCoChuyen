"""Investor KPIs ("📊 Tổng quan đầu tư"): cheap counters written as events happen, and daily rollups
frozen once a Vietnam day is over. Never reads a save; never blocks a player.

Tables (created idempotently by admin_stats.ensure(): SQLite SCHEMA here, PostgreSQL PG_DDL, additive only,
no change to any existing table):
* stat_counters(day, key, n), primary key (day, key): per Vietnam day, counters kept by the game itself.
  `n` is a sum, except keys starting with `max:` (the highest value seen that day). Keys (identifiers only):
    ai:calls|ok|failed|busy|rejected|guard   the AI calls of every worker (admin_stats wraps game/ai.py)
    cmd_ms:<bucket>                          game commands by latency bucket (admin_stats.CMD_EDGES)
    http:<2xx|3xx|4xx|5xx>                    API answers by status class (server.py)
    xu_in:<action> / xu_out:<action>          xu created / destroyed by a command: the change of the wallet plus
                                             every workplace fund between before and after the command
    dev_os:<os> dev_form:<form> dev_br:<browser> dev_bot lang:<vi|en|other>   a new session's device (User-Agent)
    up_min                                   minutes the server was up (housekeeping, one process)
    max:online5m, max:online5m:h<HH>         most saves with a command in the last 5 minutes (sampled each minute)
    max:cmd_min                              most commands per minute (all workers, sampled each minute)
  add()/peak() only update an in-memory buffer (a lock and a dict); a thread per process writes it every
  FLUSH_EVERY seconds in one transaction (sorted keys: workers never deadlock). Bounded (BUFFER_MAX keys).
* stat_kpi_daily(day, key, value, at): numbers of a FINISHED Vietnam day, written once by freeze() and never
  changed afterwards (INSERT ... DO NOTHING): they outlive the 120-day stat_active history and any later save
  deletion. Keys: dau, wau, mau, new_sessions, new_players, new_accounts, returning, resurrected, chat_msgs,
  chat_senders, ret_d<k> (k = 1, 3, 7, 14, 30: new players of that day active again exactly k days later, written
  once day+k is over), feat:<group> (players who used a feature that day, FEATURES), `_done` (the day's base
  numbers are in). On a Monday: wk_active, wk_prev, wk_retained, wk_new, wk_back, wk_churned, wk_partial (the
  week's growth accounting, written once its Sunday is frozen). Plus `wallet_median` / `wallet_p90` / `wallet_n`
  (the saves sample's wallet, overwritten while the day runs). A day is frozen FREEZE_AFTER after its midnight.
* stat_players(sid, first_day, last_day, days): every save that ever sent a command since tracking began
  (stat_active), its first and last active Vietnam day and how many days it was active. Filled by freeze() from
  stat_active, one finished day at a time, in order; kept forever, even after the save is deleted (owner, 02/10:
  player statistics are never lost or changed). The basis of "người từng chơi", lifetime active days and resurrection.
freeze() runs from the admin job and from the server's housekeeping (admin_stats.upkeep, never at the peak
hours), a bounded number of days per call, each day in its own short transaction.
"""
from __future__ import annotations

import atexit
import bisect
import datetime
import os
import re
import sys
import threading
import time

from . import db as dbm

VN = datetime.timezone(datetime.timedelta(hours=7))
ENABLED = os.environ.get('KPI_COUNTERS', '1').strip().lower() not in ('0', 'false', 'no', 'off')
FLUSH_EVERY = 30.0
BUFFER_MAX = 20000
FREEZE_DAYS = 45          # finished days frozen per call at most (the first run catches up over a few calls)
FREEZE_AFTER = 1200       # a Vietnam day is frozen this many seconds after its midnight (every buffer has been written)
RET_KS = (1, 3, 7, 14, 30)

# Feature groups of the game commands (stat_actions.action, by prefix; the first match wins). "work" is the rest:
# the careers' own actions (serving customers, the workplace's tasks).
FEATURES = (
    ('bank', ('jr_bk_', 'jr_invest', 'iv_')),
    ('learn', ('jr_cert', 'cl_')),
    ('home', ('jr_home', 'jr_reno', 'jr_deco', 'jr_equip', 'jr_garage', 'jr_relax', 'jr_fridge')),
    ('wardrobe', ('jr_wd_',)),
    ('needs', ('jr_needs',)),
    ('board', ('bd_',)),
    ('life', ('lf_',)),
    ('close', ('qn_',)),
    ('story', ('st_', 'ev_')),
    ('fair', ('fair_',)),
    ('jobs', ('job_', 'select_career')),
    ('quay', ('jr_quay',)),
)
FEATURE_KEYS = tuple(k for k, _ in FEATURES) + ('work',)


def feature_of(action: str) -> str:
    a = str(action or '')
    for key, prefixes in FEATURES:
        if a.startswith(prefixes):
            return key
    return 'work'

SCHEMA = """
CREATE TABLE IF NOT EXISTS stat_counters (day TEXT NOT NULL, key TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(day, key)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS stat_kpi_daily (day TEXT NOT NULL, key TEXT NOT NULL, value REAL, at REAL NOT NULL,
  PRIMARY KEY(day, key)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS stat_players (sid TEXT PRIMARY KEY, first_day TEXT NOT NULL, last_day TEXT NOT NULL,
  days INTEGER NOT NULL) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS stat_players_first ON stat_players(first_day);
CREATE INDEX IF NOT EXISTS stat_players_last ON stat_players(last_day);
"""
_T = 'text COLLATE "C"'
PG_DDL = (
    ('stat_counters', f'CREATE TABLE IF NOT EXISTS stat_counters (day {_T} NOT NULL, key {_T} NOT NULL, n bigint NOT NULL DEFAULT 0, '
                      'PRIMARY KEY (day, key)) WITH (fillfactor = 85)'),
    ('stat_kpi_daily', f'CREATE TABLE IF NOT EXISTS stat_kpi_daily (day {_T} NOT NULL, key {_T} NOT NULL, value double precision, '
                       'at double precision NOT NULL, PRIMARY KEY (day, key))'),
    ('stat_players', f'CREATE TABLE IF NOT EXISTS stat_players (sid {_T} PRIMARY KEY, first_day {_T} NOT NULL, last_day {_T} NOT NULL, '
                     'days bigint NOT NULL)'),
    ('stat_players_first', 'CREATE INDEX IF NOT EXISTS stat_players_first ON stat_players (first_day)'),
    ('stat_players_last', 'CREATE INDEX IF NOT EXISTS stat_players_last ON stat_players (last_day)'),
)
TABLES = ('stat_counters', 'stat_kpi_daily', 'stat_players')


def _log(where: str, exc) -> None:
    try:
        sys.stderr.write(f'[kpi] {where}: {type(exc).__name__}: {" ".join(str(exc).split())[:200]}\n')
    except Exception:  # noqa: BLE001
        pass


def vn_day(t: float | None = None) -> str:
    return datetime.datetime.fromtimestamp(time.time() if t is None else t, VN).date().isoformat()


def plus(day: str, n: int) -> str:
    return (datetime.date.fromisoformat(day) + datetime.timedelta(days=n)).isoformat()


def utc_of(day: str) -> str:
    """Vietnam midnight of `day` as the UTC text of sessions.updated_at / accounts.created_at."""
    return (datetime.datetime.fromisoformat(day) - datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')


def epoch_of(day: str) -> float:
    """Vietnam midnight of `day` as unix time."""
    return datetime.datetime.fromisoformat(day).replace(tzinfo=VN).timestamp()


# ---------------------------------------------------------------- counters (buffered)
_KEY = re.compile(r'[a-z0-9_:.\-]{1,64}')
_lock = threading.Lock()
_bufs: dict = {}            # store path -> [store, {(day, key): n}, {(day, key): max}]
_dropped = [0]
_fails: dict = {}           # store path -> 1 after a failed flush (its rows were put back once)
_flusher = {'pid': None, 'thread': None, 'event': None}


def clean_key(key) -> str | None:
    k = str(key or '').strip().lower()[:64]
    return k if _KEY.fullmatch(k) else None


_owner = [os.getpid()]


def _mine() -> None:
    """Caller holds _lock. In a forked worker, the counts copied from the parent are the parent's to write."""
    if _owner[0] != os.getpid():
        _owner[0] = os.getpid()
        _bufs.clear()
        _fails.clear()


def _slot(store):
    """Caller holds _lock."""
    _mine()
    slot = _bufs.get(store.path)
    if slot is None:
        slot = _bufs[store.path] = [store, {}, {}]
    return slot


def add(store, key: str, n: int = 1, now: float | None = None) -> None:
    """Add `n` to today's counter `key` (memory only; written every FLUSH_EVERY seconds)."""
    if not ENABLED or store is None or not n:
        return
    k = clean_key(key)
    if k is None or k.startswith('max:'):
        return
    item = (vn_day(now), k)
    with _lock:
        rows = _slot(store)[1]
        if item not in rows and len(rows) >= BUFFER_MAX:
            _dropped[0] += 1
            return
        rows[item] = rows.get(item, 0) + int(n)
    _ensure_flusher()


def peak(store, key: str, value, now: float | None = None) -> None:
    """Keep the highest `value` of today's `max:<key>`."""
    if not ENABLED or store is None or value is None:
        return
    k = clean_key('max:' + str(key))
    if k is None:
        return
    item = (vn_day(now), k)
    v = int(round(float(value)))
    with _lock:
        rows = _slot(store)[2]
        if item not in rows and len(rows) >= BUFFER_MAX:
            _dropped[0] += 1
            return
        rows[item] = max(rows.get(item, v), v)
    _ensure_flusher()


def _ensure_flusher() -> None:
    f = _flusher
    if f['pid'] != os.getpid() or f['thread'] is None or not f['thread'].is_alive():
        with _lock:
            if f['pid'] != os.getpid() or f['thread'] is None or not f['thread'].is_alive():
                f['pid'], f['event'] = os.getpid(), threading.Event()
                f['thread'] = threading.Thread(target=_flush_loop, args=(f['event'],), daemon=True, name='kpi-flush')
                f['thread'].start()


def _flush_loop(event) -> None:
    pid = os.getpid()
    while _flusher['pid'] == pid:
        event.wait(FLUSH_EVERY)
        event.clear()
        flush_all()


_SUM = ('INSERT INTO stat_counters(day, key, n) VALUES (?, ?, ?) ON CONFLICT(day, key) DO UPDATE SET '
        'n = stat_counters.n + excluded.n')
_MAX = ('INSERT INTO stat_counters(day, key, n) VALUES (?, ?, ?) ON CONFLICT(day, key) DO UPDATE SET '
        'n = CASE WHEN excluded.n > stat_counters.n THEN excluded.n ELSE stat_counters.n END')


def flush(store) -> int:
    """Write this process's waiting counters of `store` (one transaction). A failed batch is merged back once,
    then dropped (counted in buffered()['dropped'])."""
    with _lock:
        _mine()
        slot = _bufs.get(store.path)
        if not slot or not (slot[1] or slot[2]):
            return 0
        sums, maxes = slot[1], slot[2]
        slot[1], slot[2] = {}, {}
        gone = (not os.path.exists(store.path)) if not getattr(store, 'pg', None) else (
            dbm.test_mode() and not os.path.isdir(os.path.dirname(os.path.abspath(store.path))))
        if gone:   # a test's temporary store
            _bufs.pop(store.path, None)
            return 0
    a = [(d, k, n) for (d, k), n in sorted(sums.items())]
    b = [(d, k, n) for (d, k), n in sorted(maxes.items())]

    def write(db):
        if a:
            db.executemany(_SUM, a)
        if b:
            db.executemany(_MAX, b)
    try:
        store.transaction(write)
    except Exception:
        with _lock:   # back into the buffer once (merged); a second failure in a row drops them
            slot = _bufs.setdefault(store.path, [store, {}, {}])
            if not _fails.get(store.path):
                _fails[store.path] = 1
                for (d, k), n in sums.items():
                    slot[1][(d, k)] = slot[1].get((d, k), 0) + n
                for (d, k), n in maxes.items():
                    slot[2][(d, k)] = max(slot[2].get((d, k), n), n)
            else:
                _fails[store.path] = 0
                _dropped[0] += len(a) + len(b)
        raise
    _fails.pop(store.path, None)
    return len(a) + len(b)


def flush_all() -> int:
    with _lock:
        _mine()
        stores = [slot[0] for slot in _bufs.values() if slot[1] or slot[2]]
    n = 0
    for store in stores:
        try:
            n += flush(store)
        except Exception as e:  # noqa: BLE001 - counters never break the game
            _log('flush', e)
    return n


def _flush_at_exit() -> None:
    try:
        flush_all()
    except Exception:  # noqa: BLE001
        pass


atexit.register(_flush_at_exit)


def buffered() -> dict:
    with _lock:
        _mine()
        return dict(keys=sum(len(s[1]) + len(s[2]) for s in _bufs.values()), dropped=_dropped[0])


def pending(store) -> dict:
    """{(day, key): n} not written yet by this process (sums and maxima together)."""
    with _lock:
        _mine()
        slot = _bufs.get(store.path)
        if not slot:
            return {}
        out = dict(slot[1])
        out.update(slot[2])
        return out


def read(db, since: str, prefix: str = '') -> dict:
    """{day: {key: n}} of stat_counters from `since` (a primary key range), optionally one key prefix."""
    out: dict = {}
    if prefix:
        rows = db.execute('SELECT day, key, n FROM stat_counters WHERE day >= ? AND key >= ? AND key < ?',
                          (since, prefix, prefix[:-1] + chr(ord(prefix[-1]) + 1)))
    else:
        rows = db.execute('SELECT day, key, n FROM stat_counters WHERE day >= ?', (since,))
    for day, key, n in rows:
        out.setdefault(day, {})[key] = int(n or 0)
    return out


# ---------------------------------------------------------------- economy: xu per command
ECON_SKIP = frozenset(('import_save', 'reset_all', 'reset_career'))
_econ = threading.local()


def xu(state) -> int | None:
    """The xu a save holds: the journey wallet, every workplace's fund and the bank (current account, demand
    savings and term deposits), so moving money between them is not counted as created or destroyed. Debts
    (card, loans) are not subtracted: a loan paid out is counted as xu in, its repayments as xu out.
    Dict reads only (a few microseconds)."""
    try:
        if type(state) is not dict:
            return None
        j = state.get('journey')
        w = j.get('wallet') if type(j) is dict else None
        total = w if type(w) is int else 0
        b = j.get('bank') if type(j) is dict else None
        if type(b) is dict:
            for k in ('balance', 'demand'):
                v = b.get(k)
                if type(v) is int:
                    total += v
            for t in b.get('terms') or ():
                if type(t) is dict and type(t.get('amount')) is int:
                    total += t['amount']
        q = j.get('quay') if type(j) is dict else None   # 🏪 the counters' fund and till (game/quay.py)
        if type(q) is dict:
            for st in q.get('stalls') or ():
                if type(st) is dict:
                    for k in ('fund', 'till'):
                        if type(st.get(k)) is int:
                            total += st[k]
        cs = state.get('careers')
        if type(cs) is dict:
            for c in cs.values():
                if type(c) is dict:
                    m = c.get('money')
                    if type(m) is int:
                        total += m
        return total
    except Exception:  # noqa: BLE001 - statistics never break a command
        return None


def econ_mark(action, before, after) -> None:
    """The command being computed on this thread changed the xu in hand from `before` to `after`
    (Store._compute; the last call before the save is stored wins)."""
    _econ.v = (action, before, after) if (before is not None and after is not None) else None


def econ_commit(store) -> None:
    """The command was stored: count its xu change (xu_in / xu_out of its action)."""
    v = getattr(_econ, 'v', None)
    _econ.v = None
    if not v or not ENABLED:
        return
    action, before, after = v
    a = clean_key(action) or 'other'
    d = int(after) - int(before)
    if d > 0:
        add(store, 'xu_in:' + a, d)
    elif d < 0:
        add(store, 'xu_out:' + a, -d)


def econ_drop() -> None:
    _econ.v = None


# ---------------------------------------------------------------- devices (new sessions)
_BOT = ('bot', 'crawler', 'spider', 'headless', 'lighthouse', 'facebookexternalhit', 'slurp', 'preview', 'python-', 'curl/', 'wget')


def device(ua: str) -> dict:
    """{os, form, browser, bot} of a User-Agent: coarse families only, nothing that identifies a person."""
    u = str(ua or '')[:400].lower()
    bot = any(x in u for x in _BOT)
    if 'android' in u:
        os_ = 'android'
    elif any(x in u for x in ('iphone', 'ipad', 'ipod')):
        os_ = 'ios'
    elif 'windows' in u:
        os_ = 'windows'
    elif 'cros' in u:
        os_ = 'chromeos'
    elif 'mac os x' in u or 'macintosh' in u:
        os_ = 'mac'
    elif 'linux' in u:
        os_ = 'linux'
    else:
        os_ = 'other'
    if 'ipad' in u or 'tablet' in u or ('android' in u and 'mobile' not in u):
        form = 'tablet'
    elif 'mobi' in u or 'iphone' in u or 'ipod' in u:
        form = 'mobile'
    else:
        form = 'desktop' if os_ in ('windows', 'mac', 'linux', 'chromeos') else 'other'
    for name, marks in (('zalo', ('zalo',)), ('facebook', ('fban', 'fbav', 'fb_iab', 'messenger')), ('instagram', ('instagram',)),
                        ('tiktok', ('bytedance', 'musical_ly', 'tiktok')), ('coccoc', ('coc_coc', 'coccoc')),
                        ('samsung', ('samsungbrowser',)), ('edge', ('edg/', 'edga/', 'edgios/')), ('opera', ('opr/', 'opera')),
                        ('firefox', ('firefox', 'fxios')), ('chrome', ('chrome', 'crios')), ('safari', ('safari',))):
        if any(m in u for m in marks):
            browser = name
            break
    else:
        browser = 'other'
    return dict(os=os_, form=form, browser=browser, bot=bot)


def count_session(store, ua: str, accept_language: str = '', now: float | None = None) -> None:
    """A new session (a first visit on this browser): its device families and language."""
    if not ENABLED:
        return
    try:
        d = device(ua)
        if d['bot']:
            add(store, 'dev_bot', 1, now)
            return
        add(store, 'dev_os:' + d['os'], 1, now)
        add(store, 'dev_form:' + d['form'], 1, now)
        add(store, 'dev_br:' + d['browser'], 1, now)
        lang = str(accept_language or '').strip().lower()[:2]
        add(store, 'lang:' + (lang if lang in ('vi', 'en') else 'other'), 1, now)
    except Exception as e:  # noqa: BLE001
        _log('session', e)


# ---------------------------------------------------------------- frozen daily numbers
def _exists(db, table: str) -> bool:
    if dbm.is_pg(db):
        return db.pg('SELECT to_regclass(%s) IS NOT NULL', (table,)).fetchone()[0]
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone())


def chat_range(db, t0: float, t1: float) -> tuple[int, int] | None:
    """(first id, end id) of chat_messages sent in [t0, t1): binary search over the primary key (ids grow with
    time), ~20 key lookups and no scan. None when there is no chat table."""
    if not _exists(db, 'chat_messages'):
        return None
    lo_hi = db.execute('SELECT MIN(id), MAX(id) FROM chat_messages').fetchone()
    if not lo_hi or lo_hi[0] is None:
        return (0, 0)
    lo, hi = int(lo_hi[0]), int(lo_hi[1]) + 1

    def first_at_or_after(t):
        # The smallest x such that every message with id >= x was sent at or after t: "the first message from x
        # on is at or after t" only flips from false to true as x grows (ids grow with time).
        a, b = lo, hi
        while a < b:
            mid = (a + b) // 2
            r = db.execute('SELECT at FROM chat_messages WHERE id >= ? ORDER BY id LIMIT 1', (mid,)).fetchone()
            if r is None or float(r[0]) >= t:
                b = mid
            else:
                a = mid + 1
        return a
    return first_at_or_after(t0), first_at_or_after(t1)


def chat_day(db, day: str) -> tuple[int, int] | None:
    """(messages, distinct senders) of players on Vietnam day `day` (admin posts left out); None without a chat."""
    rng = chat_range(db, epoch_of(day), epoch_of(plus(day, 1)))
    if rng is None:
        return None
    a, b = rng
    if b <= a:
        return (0, 0)
    r = db.execute('SELECT COUNT(*), COUNT(DISTINCT pid) FROM chat_messages WHERE id >= ? AND id < ? AND adm = 0', (a, b)).fetchone()
    return int(r[0] or 0), int(r[1] or 0)


def _base(db, day: str) -> dict:
    """The numbers of one finished day (index range reads only)."""
    n = lambda sql, args: int(db.execute(sql, args).fetchone()[0] or 0)
    out = dict(
        dau=n('SELECT COUNT(*) FROM stat_active WHERE day = ?', (day,)),
        new_sessions=n('SELECT COUNT(*) FROM stat_births WHERE day = ?', (day,)),
        new_players=n('SELECT COUNT(*) FROM stat_births b WHERE b.day = ? AND EXISTS '
                      '(SELECT 1 FROM stat_active a WHERE a.day = b.day AND a.sid = b.sid)', (day,)),
        new_accounts=n('SELECT COUNT(*) FROM accounts WHERE created_at >= ? AND created_at < ?', (utc_of(day), utc_of(plus(day, 1)))),
        wau=n('SELECT COUNT(DISTINCT sid) FROM stat_active WHERE day >= ? AND day <= ?', (plus(day, -6), day)),
        mau=n('SELECT COUNT(DISTINCT sid) FROM stat_active WHERE day >= ? AND day <= ?', (plus(day, -29), day)),
    )
    out['returning'] = max(0, out['dau'] - out['new_players'])
    if _exists(db, 'chat_messages'):
        out['chat_msgs'], out['chat_senders'] = chat_day(db, day)
    if _exists(db, 'stat_actions'):
        out.update(features_day(db, day))
    return out


def features_day(db, day: str) -> dict:
    """{feat:<group>: players who used it that day} from stat_actions (the per-player rows, kept 60 days:
    an older day gets no feature numbers). One primary-key range read of the day."""
    seen: dict = {}
    for sid, action in db.execute('SELECT sid, action FROM stat_actions WHERE day = ?', (day,)):
        seen.setdefault(feature_of(action), set()).add(sid)
    if not seen:
        return {}
    return {f'feat:{k}': len(seen.get(k, ())) for k in FEATURE_KEYS}


def week_of(day: str) -> str:
    """Monday of the ISO week of `day`."""
    d = datetime.date.fromisoformat(day)
    return (d - datetime.timedelta(days=d.weekday())).isoformat()


def _week(db, monday: str, first: str) -> dict:
    """Growth accounting of one finished week (Monday..Sunday): active players, of them active the week
    before (retained), first active ever (new), back after a longer pause (back); and the previous week's
    players not seen this week (churned). `partial` when the week before is not fully in the history."""
    sunday, pm, ps = plus(monday, 6), plus(monday, -7), plus(monday, -1)
    n = lambda sql, args: int(db.execute(sql, args).fetchone()[0] or 0)
    active = n('SELECT COUNT(DISTINCT sid) FROM stat_active WHERE day >= ? AND day <= ?', (monday, sunday))
    prev = n('SELECT COUNT(DISTINCT sid) FROM stat_active WHERE day >= ? AND day <= ?', (pm, ps))
    kept = n('SELECT COUNT(*) FROM (SELECT DISTINCT sid FROM stat_active WHERE day >= ? AND day <= ?) t WHERE EXISTS '
             '(SELECT 1 FROM stat_active p WHERE p.sid = t.sid AND p.day >= ? AND p.day <= ?)', (monday, sunday, pm, ps))
    new = n('SELECT COUNT(*) FROM stat_players WHERE first_day >= ? AND first_day <= ?', (monday, sunday))
    return {'wk_active': active, 'wk_prev': prev, 'wk_retained': kept, 'wk_new': new,
            'wk_back': max(0, active - kept - new), 'wk_churned': max(0, prev - kept), 'wk_partial': int(pm < first)}


def _ret(db, day: str, k: int) -> int:
    return int(db.execute(
        'SELECT COUNT(*) FROM stat_births b WHERE b.day = ? AND EXISTS (SELECT 1 FROM stat_active a WHERE a.day = b.day AND a.sid = b.sid) '
        'AND EXISTS (SELECT 1 FROM stat_active a WHERE a.day = ? AND a.sid = b.sid)', (day, plus(day, k))).fetchone()[0] or 0)


def _players_step(db, day: str) -> int:
    """stat_players after `day` (days strictly in order): returns how many of that day's players came back after
    at least 7 days away (their previous active day <= day - 8)."""
    back = int(db.execute('SELECT COUNT(*) FROM stat_active a JOIN stat_players p ON p.sid = a.sid WHERE a.day = ? AND p.last_day <= ?',
                          (day, plus(day, -8))).fetchone()[0] or 0)
    db.execute('INSERT INTO stat_players(sid, first_day, last_day, days) SELECT sid, day, day, 1 FROM stat_active WHERE day = ? '
               'ON CONFLICT(sid) DO UPDATE SET last_day = excluded.last_day, days = stat_players.days + 1 '
               'WHERE stat_players.last_day < excluded.last_day', (day,))
    return back


def freeze(store, now: float | None = None, limit: int = FREEZE_DAYS, pause: float = 0.02) -> dict:
    """Freeze the finished Vietnam days not frozen yet (in order, at most `limit`), then the retention numerators
    whose day+k is over. Idempotent; each day in its own short transaction; never a save."""
    now = time.time() if now is None else now
    today = vn_day(now - FREEZE_AFTER)   # 00:00-00:20: yesterday still counts as "today" (buffers not written yet)
    out = dict(days=0, ret=0, weeks=0)
    with store.connect() as db:
        if not _exists(db, 'stat_kpi_daily') or not _exists(db, 'stat_active'):
            return out
        last = db.execute("SELECT MAX(day) FROM stat_kpi_daily WHERE key = '_done'").fetchone()[0]
        first = db.execute('SELECT MIN(day) FROM stat_active').fetchone()[0]
    if first is None:
        return out
    day = plus(last, 1) if last else first
    while day < today and out['days'] < limit:
        def write(db, day=day):
            if db.execute("SELECT 1 FROM stat_kpi_daily WHERE day = ? AND key = '_done'", (day,)).fetchone():
                return False
            vals = _base(db, day)
            vals['resurrected'] = _players_step(db, day)
            t = round(time.time(), 3)
            db.executemany('INSERT INTO stat_kpi_daily(day, key, value, at) VALUES (?, ?, ?, ?) ON CONFLICT(day, key) DO NOTHING',
                           [(day, k, float(v), t) for k, v in sorted(vals.items())] + [(day, '_done', 1.0, t)])
            return True
        if store.transaction(write):
            out['days'] += 1
        day = plus(day, 1)
        if pause:
            time.sleep(pause)
    # Retention numerators: a cohort day whose day+k is over and still within the stat_active history.
    with store.connect() as db:
        have = {(r[0], r[1]) for r in db.execute("SELECT day, key FROM stat_kpi_daily WHERE key LIKE 'ret_d%' AND day >= ?",
                                                    (plus(today, -100),))}
        cohorts = [r[0] for r in db.execute("SELECT day FROM stat_kpi_daily WHERE key = 'new_players' AND day >= ? AND day < ?",
                                            (max(first, plus(today, -100)), today))]
    todo = [(d, k) for d in cohorts for k in RET_KS if plus(d, k) < today and (d, f'ret_d{k}') not in have]
    for i in range(0, len(todo), 20):
        part = todo[i:i + 20]

        def write(db, part=part):
            t = round(time.time(), 3)
            rows = [(d, f'ret_d{k}', float(_ret(db, d, k)), t) for d, k in part]
            db.executemany('INSERT INTO stat_kpi_daily(day, key, value, at) VALUES (?, ?, ?, ?) ON CONFLICT(day, key) DO NOTHING', rows)
            return len(rows)
        out['ret'] += store.transaction(write) or 0
        if pause:
            time.sleep(pause)
    # Weeks (Monday..Sunday) whose Sunday is frozen, from the first week of the history.
    with store.connect() as db:
        done = db.execute("SELECT MAX(day) FROM stat_kpi_daily WHERE key = '_done'").fetchone()[0]
        weeks = {r[0] for r in db.execute("SELECT day FROM stat_kpi_daily WHERE key = 'wk_active' AND day >= ?", (week_of(first),))}
    monday = week_of(first)
    while done and plus(monday, 6) <= done:
        if monday not in weeks:
            def write(db, monday=monday):
                t = round(time.time(), 3)
                db.executemany('INSERT INTO stat_kpi_daily(day, key, value, at) VALUES (?, ?, ?, ?) ON CONFLICT(day, key) DO NOTHING',
                               [(monday, k, float(v), t) for k, v in sorted(_week(db, monday, first).items())])
                return 1
            out['weeks'] += store.transaction(write) or 0
            if pause:
                time.sleep(pause)
        monday = plus(monday, 7)
    return out


def frozen(db, since: str) -> dict:
    """{day: {key: value}} of stat_kpi_daily from `since`."""
    out: dict = {}
    for day, key, value in db.execute('SELECT day, key, value FROM stat_kpi_daily WHERE day >= ?', (since,)):
        out.setdefault(day, {})[key] = value
    return out


def set_daily(store, key: str, value, now: float | None = None) -> None:
    """A number of today that may still change while the day runs (e.g. the saves sample's median wallet)."""
    day = vn_day(now)
    t = round(time.time(), 3)
    store.transaction(lambda db: db.execute(
        'INSERT INTO stat_kpi_daily(day, key, value, at) VALUES (?, ?, ?, ?) ON CONFLICT(day, key) DO UPDATE SET '
        'value = excluded.value, at = excluded.at', (day, key, None if value is None else float(value), t)))


# ---------------------------------------------------------------- one sample per minute (housekeeping)
_minute = {'at': 0}


def sample_minute(store, now: float | None = None) -> dict | None:
    """Once a minute (server housekeeping, one process): the saves with a command in the last 5 minutes and the
    commands per minute of all workers, kept as the day's (and the hour's) highest; and one minute of uptime."""
    now = time.time() if now is None else now
    if int(now // 60) == _minute['at']:
        return None
    _minute['at'] = int(now // 60)
    from . import admin_stats as st
    with st._read(store, 800) as db:
        m5 = int(db.execute('SELECT COUNT(*) FROM sessions WHERE updated_at >= ?',
                            (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now - 300)),)).fetchone()[0] or 0)
    per_min = st.command_stats(store, now).get('per_min') or 0
    hour = datetime.datetime.fromtimestamp(now, VN).hour
    peak(store, 'online5m', m5, now)
    peak(store, f'online5m:h{hour:02d}', m5, now)
    peak(store, 'cmd_min', per_min, now)
    add(store, 'up_min', 1, now)
    return dict(m5=m5, per_min=per_min)


def latency_bucket(ms: float, edges) -> int:
    return bisect.bisect_left(edges, ms)
