"""Retention logging ("Giữ chân"): where and how players drop off. Records only into its own
stat tables, never into a save, and never reads a save to do it.

What is recorded (tables on both backends: SCHEMA here for SQLite, game/pg_schema.py for PostgreSQL):
* stat_milestones(sid, key, at, day, career, detail), primary key (sid, key): once per save, the
  moment it first reached a step of MILESTONES (created, named, picked a workplace, 1st/3rd/10th
  customer, first level up, life day 1/2/3/7/14/30 over, first change of workplace, chapters 2-4,
  account, first home, engaged, married, first certificate, first bank loan / savings) plus
  `start:<career>` (first customer served in that workplace). `day` is the player's life day,
  `at` unix time (NULL for rows seeded by scripts/milestones_backfill.py). Kept forever.
  Detection is free of extra reads: Store._compute already has the save before and after a
  command and the leaderboard summary of both (served, levels, certificates); marks() picks a
  dozen small counters from them and reached() compares the two (PER-COMMAND COST: see marks).
  The rows are written in the command's own transaction, only when a step was crossed.
  `created` comes from Store.session, `account` from accounts.register, `engaged`/`married`
  from game/marriage.py, each in its own transaction.
* stat_actions(day, sid, career, action, n, errors, err): commands per player per Vietnam day
  (`sid`: the save id's first SID_LEN hex characters, see short()),
  rejected ones (GameError) counted in `errors` with the last error code or message (short).
  count() only adds to an in-memory buffer (a lock and a dict update); a thread per process
  writes it every FLUSH_EVERY seconds in ONE statement (sorted keys, so workers never deadlock).
  Kept ACTIONS_KEEP_DAYS, then rolled up per day into stat_actions_daily(day, career, action,
  players, n, errors, err) (kept forever) and deleted in small batches (maintain()).
* Browser beacons (POST /api/beacon, server.py): session cookie only, never a save:
  - leave {v view, p popup/sheet, c career, d life day, t tutorial/onboarding step, s seconds
    since load, a last 3 UI actions} -> stat_leaves(id, sid, at, day, payload) (short sid, VN day; kept
    LEAVES_KEEP_DAYS) and stat_leave_last (the newest per save: "where did they leave").
  - errors [{k kind, m message, s screen, n, st stack}] -> stat_client_errors(day, kind, message_key,
    screen, count, last_at, sample), aggregated; URLs lose their query, digits and quoted text
    are masked (but the property a TypeError names), no free text from players; the sample ends
    with ` @ ` and the stack (file:line:col of the top 3 frames, stack_text). Errors that are not
    the game's (foreign_error: injected scripts, extensions) are dropped. Kept ERRORS_KEEP_DAYS.
  - load {ttfb, dcl, frame (ms), net, mem, cpu, cache} -> stat_loads(day, metric, net, who,
    cache, tier, bucket, n): histograms (who: new = the save was born today). Kept LOADS_KEEP_DAYS.
  - acq {ref (referrer host), src, med, cmp (utm_*)} -> stat_acquisition(sid, at, day, source,
    medium, campaign, ref_domain): once per save, only for a save born today or yesterday.
* Every new milestone is also handed to emit(): the one hook for mirroring key events to an
  outside service later (e.g. GA4 Measurement Protocol, see on_event). Nothing is sent today.

Bounded: buffers have hard caps, payloads are cut to a few hundred bytes, beacons are rate
limited (server.py) and capped per save per day, every table has a retention rule run by
maintain() in small batches outside the peak hours (17:30-20:00 VN), from the server's
housekeeping and from the admin job. RETENTION_LOG=0 turns the recording off.
"""
from __future__ import annotations

import atexit
import datetime
import json
import os
import re
import sys
import threading
import time

from . import db as dbm
from .leaderboard import CERTS, CAREER_IDS

try:
    import fcntl
except ImportError:  # Windows: one process
    fcntl = None

VN = datetime.timezone(datetime.timedelta(hours=7))
ENABLED = os.environ.get('RETENTION_LOG', '1').strip().lower() not in ('0', 'false', 'no', 'off')


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name) or default))
    except ValueError:
        return default


ACTIONS_KEEP_DAYS = _env_int('RETENTION_ACTIONS_DAYS', 60)   # per-player action rows (then the daily rollup only)
LEAVES_KEEP_DAYS = _env_int('RETENTION_LEAVES_DAYS', 60)     # leave beacons
ERRORS_KEEP_DAYS = _env_int('RETENTION_ERRORS_DAYS', 60)     # client error rows (already aggregated)
LOADS_KEEP_DAYS = _env_int('RETENTION_LOADS_DAYS', 400)      # load-time histograms (a few thousand rows a day)
FLUSH_EVERY = 15.0       # seconds between two writes of a process's action counts
FLUSH_KEYS = 4000        # ... or sooner once this many (day, save, career, action) keys wait
BUFFER_MAX = 40000       # hard cap of waiting keys per process; past it new keys are dropped (counted)
LEAVES_PER_DAY = 40      # leave beacons stored per save per day (per process)
ERRORS_PER_BEACON = 10
BEACON_MAX = 8192        # bytes of one beacon body (server.py)
ROLL_AFTER = 900         # a finished Vietnam day is rolled up this many seconds after its midnight
BATCH = 2000             # rows per delete statement in maintain()
PAUSE = 0.05             # seconds between two batches
PEAK = ((17, 30), (20, 0))   # Vietnam time: maintain() does no deletes or rollups in this window

# The funnel, in order: (key, short label). `start:<career>` keys are recorded too (not listed).
MILESTONES = (
    ('created', 'Mở game'), ('named', 'Đặt tên'), ('picked', 'Chọn nơi làm'), ('served1', 'Khách đầu'),
    ('served3', '3 khách'), ('level2', 'Lên cấp 2'), ('served10', '10 khách'), ('day1', 'Hết ngày 1'),
    ('day2', 'Hết ngày 2'), ('day3', 'Hết ngày 3'), ('day7', 'Hết ngày 7'), ('day14', 'Hết ngày 14'),
    ('day30', 'Hết ngày 30'), ('job_change', 'Đổi nơi làm'), ('chapter2', 'Chương 2'), ('chapter3', 'Chương 3'),
    ('chapter4', 'Chương 4'), ('account', 'Tạo tài khoản'), ('house', 'Mua nhà'), ('engaged', 'Đính hôn'),
    ('married', 'Kết hôn'), ('cert', 'Chứng chỉ đầu'), ('loan', 'Vay ngân hàng'), ('savings', 'Gửi tiết kiệm'))
KEYS = tuple(k for k, _ in MILESTONES)
SERVED = (1, 3, 10)
DAYS = (1, 2, 3, 7, 14, 30)
CHAPTERS = (2, 3, 4)

SCHEMA = """
CREATE TABLE IF NOT EXISTS stat_milestones (sid TEXT NOT NULL, key TEXT NOT NULL, at REAL, day INTEGER, career TEXT,
  detail TEXT, PRIMARY KEY(sid, key)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS stat_milestones_key ON stat_milestones(key, at);
CREATE TABLE IF NOT EXISTS stat_actions (day TEXT NOT NULL, sid TEXT NOT NULL, career TEXT NOT NULL, action TEXT NOT NULL,
  n INTEGER NOT NULL, errors INTEGER NOT NULL DEFAULT 0, err TEXT, PRIMARY KEY(day, sid, career, action)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS stat_actions_daily (day TEXT NOT NULL, career TEXT NOT NULL, action TEXT NOT NULL,
  players INTEGER NOT NULL, n INTEGER NOT NULL, errors INTEGER NOT NULL, err TEXT, PRIMARY KEY(day, career, action)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS stat_rollups (kind TEXT NOT NULL, day TEXT NOT NULL, rows INTEGER NOT NULL, at REAL NOT NULL,
  PRIMARY KEY(kind, day)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS stat_leaves (id INTEGER PRIMARY KEY, sid TEXT NOT NULL, at REAL NOT NULL,
  day TEXT NOT NULL, payload TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS stat_leaves_sid ON stat_leaves(sid);
CREATE TABLE IF NOT EXISTS stat_leave_last (sid TEXT PRIMARY KEY, at REAL NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stat_client_errors (day TEXT NOT NULL, kind TEXT NOT NULL, message_key TEXT NOT NULL,
  screen TEXT NOT NULL, count INTEGER NOT NULL, last_at REAL NOT NULL, sample TEXT,
  PRIMARY KEY(day, kind, message_key, screen)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS stat_loads (day TEXT NOT NULL, metric TEXT NOT NULL, net TEXT NOT NULL, who TEXT NOT NULL,
  cache TEXT NOT NULL, tier TEXT NOT NULL, bucket INTEGER NOT NULL, n INTEGER NOT NULL,
  PRIMARY KEY(day, metric, net, who, cache, tier, bucket)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS stat_acquisition (sid TEXT PRIMARY KEY, at REAL NOT NULL, day TEXT NOT NULL, source TEXT,
  medium TEXT, campaign TEXT, ref_domain TEXT);
CREATE INDEX IF NOT EXISTS stat_acquisition_day ON stat_acquisition(day);
CREATE TRIGGER IF NOT EXISTS stat_retention_gone AFTER DELETE ON sessions BEGIN
  DELETE FROM stat_milestones WHERE sid = OLD.sid;
  DELETE FROM stat_leaves WHERE sid = substr(OLD.sid, 1, 16);
  DELETE FROM stat_leave_last WHERE sid = OLD.sid;
  DELETE FROM stat_acquisition WHERE sid = OLD.sid;
END;
"""
SID_LEN = 16   # stat_actions / stat_leaves keep this many hex characters of the save id (64 bits)


def short(sid: str) -> str:
    """The save id as the two big tables keep it: its first 16 hex characters. 64 bits tell even
    millions of saves apart, and each row is ~100 bytes smaller (heap + primary key). Join with
    `substr(s.sid, 1, 16)` (SQLite) / `left(s.sid, 16)` (PostgreSQL)."""
    return sid[:SID_LEN]


TABLES = ('stat_milestones', 'stat_actions', 'stat_actions_daily', 'stat_rollups', 'stat_leaves', 'stat_leave_last',
          'stat_client_errors', 'stat_loads', 'stat_acquisition')


def _log(where: str, exc) -> None:
    try:
        sys.stderr.write(f'[retention] {where}: {type(exc).__name__}: {" ".join(str(exc).split())[:200]}\n')
    except Exception:  # noqa: BLE001
        pass


def vn_day(t: float | None = None) -> str:
    return datetime.datetime.fromtimestamp(time.time() if t is None else t, VN).date().isoformat()


def _plus(day: str, n: int) -> str:
    return (datetime.date.fromisoformat(day) + datetime.timedelta(days=n)).isoformat()


# ---------------------------------------------------------------- milestones
def _int(v) -> int:
    return v if type(v) is int else 0


def marks(state, board) -> tuple | None:
    """A dozen small counters of a save: (current workplace, named, customers served, best level,
    workplaces with a customer, life days over, chapter, homes, certificates, loans, savings).
    `board`: the save's leaderboard summary (game/leaderboard.py summary), which the storage layer
    computes for every command anyway. Dict reads only (~3 us); never raises."""
    try:
        if type(state) is not dict:
            return None
        j = state.get('journey')
        j = j if type(j) is dict else {}
        cur = state.get('current')
        board = board if type(board) is dict else {}
        served, level, started = 0, 1, []
        for k, v in board.items():
            if k in CAREER_IDS and type(v) is tuple and len(v) > 5:
                served += _int(v[5])
                level = max(level, _int(v[3]))
                if _int(v[5]) > 0:
                    started.append(k)
        certs = board.get(CERTS)
        stats = j.get('stats')
        bank = j.get('bank')
        bank = bank if type(bank) is dict else None
        loans = savings = 0
        if bank:
            ln, bs = bank.get('loans'), bank.get('stats')
            loans = (len(ln) if type(ln) is list else 0) + (_int(bs.get('loans_closed')) if type(bs) is dict else 0)
            terms = bank.get('terms')
            savings = int(_int(bank.get('demand')) > 0 or bool(terms) and type(terms) is list)
        return (cur if type(cur) is str else None,
                int(bool(j.get('gender')) or (type(state.get('name')) is str and state.get('name') != 'Mây')),
                served, level, frozenset(started), max(0, _int(j.get('life_day')) - 1), _int(j.get('chapter')) or 1,
                _int(stats.get('homes_bought')) if type(stats) is dict else 0,
                _int(certs[0]) if type(certs) is tuple and certs else 0, loans, savings)
    except Exception:  # noqa: BLE001 - statistics never break a command
        return None


def reached(before: tuple | None, after: tuple | None, state=None) -> list:
    """[(key, career, detail)] of the steps crossed between two marks() (each fires once: the
    table's primary key keeps the first). Nothing when either side is unknown."""
    if not before or not after:
        return []
    cur0, named0, served0, level0, started0, days0, ch0, homes0, certs0, loans0, sav0 = before
    cur, named, served, level, started, days, ch, homes, certs, loans, sav = after
    out = []
    if cur and not cur0:
        out.append(('picked', cur, cur))
    elif cur and cur0 and cur != cur0:
        out.append(('job_change', cur, f'{cur0}>{cur}'[:60]))
    if named and not named0:
        out.append(('named', cur, None))
    for k in SERVED:
        if served0 < k <= served:
            out.append((f'served{k}', cur, None))
    if level0 < 2 <= level:
        out.append(('level2', cur, None))
    for d in DAYS:
        if days0 < d <= days:
            out.append((f'day{d}', cur, None))
    for c in CHAPTERS:
        if ch0 < c <= ch:
            out.append((f'chapter{c}', cur, None))
    for cid in sorted(started - started0):
        out.append(('start:' + cid, cid, None))
    for key, a, b in (('house', homes0, homes), ('cert', certs0, certs), ('loan', loans0, loans), ('savings', sav0, sav)):
        if not a and b:
            out.append((key, cur, None))
    return out


def life_day(state) -> int | None:
    try:
        v = state['journey']['life_day']
        return v if type(v) is int else None
    except (KeyError, TypeError):
        return None


_MARK_SQL = 'INSERT OR IGNORE INTO stat_milestones(sid, key, at, day, career, detail) VALUES (?, ?, ?, ?, ?, ?)'


def write_marks(db, sid: str, rows: list, day: int | None = None, at: float | None = None) -> None:
    """Insert milestone rows (key, career, detail) in the caller's transaction; a key the save
    already has is left as it is."""
    if not ENABLED or not rows or not sid:
        return
    at = time.time() if at is None else at
    for key, career, detail in rows:
        db.execute(_MARK_SQL, (sid, key, at, day, career, detail))


def mark(db, sid: str, key: str, career: str | None = None, detail: str | None = None) -> None:
    """One milestone from outside a command (account, engaged, married), in the caller's transaction.
    Never raises: a statistic must not undo the player's action."""
    try:
        write_marks(db, sid, [(key, career, detail)])
    except dbm.Error as e:  # pragma: no cover - only a broken table
        _log('mark', e)


# ---------------------------------------------------------------- seeding saves born before the recording
_BLANK = (None, 0, 0, 1, frozenset(), 0, 1, 0, 0, 0, 0)


def seeds(state, board) -> list:
    """[(key, career, detail)] a save has reached by now, from its counters alone (no times): what
    scripts/milestones_backfill.py writes for saves born before the recording started."""
    m = marks(state, board)
    if not m:
        return []
    rows = reached(_BLANK, m)
    try:
        days = state['journey'].get('days') or []
        if len({r.get('c') for r in days if type(r) is dict and r.get('c')}) > 1:
            rows.append(('job_change', m[0], None))
        sp = (state.get('marriage') or {}).get('spouse') or {}
        if sp.get('status') in ('engaged', 'married'):
            rows.append(('engaged', m[0], None))
        if sp.get('status') == 'married':
            rows.append(('married', m[0], None))
    except (AttributeError, TypeError, KeyError):
        pass
    return rows


def backfill(store, start: str, end: str, dry_run: bool = False, batch: int = 100, pause: float = 0.05, log=None) -> dict:
    """Seed stat_milestones for saves born (stat_births) from `start` to `end` that have no `created`
    step yet: `created` and every step their counters show (at NULL, detail 'backfill': "reached by
    now", no time), `account` / `engaged` / `married` with their real times from accounts / couples.
    Reads saves (batch per short read, a pause between), never writes one. Idempotent: a step a save
    already has (a real one, or a seed of an earlier run) is left as it is."""
    from . import fastjson as fj
    from .leaderboard import summary
    out = dict(saves=0, rows=0, skipped=0)
    with store.connect() as db:
        sids = [r[0] for r in db.execute(
            "SELECT b.sid FROM stat_births b WHERE b.day >= ? AND b.day <= ? AND NOT EXISTS "
            "(SELECT 1 FROM stat_milestones m WHERE m.sid = b.sid AND m.key = 'created') ORDER BY b.day, b.sid", (start, end))]
    for i in range(0, len(sids), batch):
        part = sids[i:i + batch]
        marks_ = ','.join('?' * len(part))
        with store.connect() as db:
            saves = list(db.execute(f'SELECT sid, state FROM sessions WHERE sid IN ({marks_})', part))
            acc = {r[0]: r[1] for r in db.execute(f'SELECT sid, created_at FROM accounts WHERE sid IN ({marks_})', part)}
            couples = list(db.execute(f'SELECT a, b, since, married_at FROM couples WHERE a IN ({marks_}) OR b IN ({marks_})', part + part))
        rows = []
        for sid, text in saves:
            try:
                state = store.parse_state(text, sid) if text == '' else fj.loads(text)
            except (ValueError, TypeError):
                out['skipped'] += 1
                continue
            day = life_day(state)
            rows.append((sid, 'created', None, 1, None, 'backfill'))
            for key, career, _ in seeds(state, summary(state)):
                rows.append((sid, key, None, day, career, 'backfill'))
            if sid in acc and acc[sid]:
                t = datetime.datetime.strptime(str(acc[sid])[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp()
                rows.append((sid, 'account', t, None, None, 'backfill'))
            out['saves'] += 1
        for a, b, since, married in couples:   # real times: they come first (INSERT OR IGNORE keeps the first)
            for who in (a, b):
                if who in part:
                    rows.insert(0, (who, 'engaged', since, None, None, 'backfill'))
                    if married:
                        rows.insert(0, (who, 'married', married, None, None, 'backfill'))
        out['rows'] += len(rows)
        if rows and not dry_run:
            store.transaction(lambda db: db.executemany(_MARK_SQL, rows))
        if log and (i // batch) % 20 == 0:
            log(f'{min(i + batch, len(sids))}/{len(sids)} lượt chơi, {out["rows"]} dòng')
        if pause:
            time.sleep(pause)
    return out


# ---------------------------------------------------------------- the one hook for outside analytics
_hooks: list = []


def on_event(fn) -> None:
    """Register fn(event, sid, params) for every new milestone (event = 'milestone:<key>'), e.g. a
    GA4 Measurement Protocol sender later. It runs on the request thread after the commit: it must
    only queue (bounded) and return; it must never send over the network inline."""
    if fn not in _hooks:
        _hooks.append(fn)


def emit(event: str, sid: str, params: dict | None = None) -> None:
    for fn in list(_hooks):
        try:
            fn(event, sid, dict(params or {}))
        except Exception as e:  # noqa: BLE001 - analytics never break the game
            _log('hook', e)


def emit_marks(sid: str, rows: list, day: int | None = None) -> None:
    if _hooks:
        for key, career, detail in rows:
            emit('milestone:' + key, sid, dict(career=career, detail=detail, life_day=day))


# ---------------------------------------------------------------- action counts (buffered)
GENERIC = frozenset(('invalid_action', 'error', ''))
_QUOTED = re.compile(r'“[^”]{0,200}”|"[^"]{0,200}"|«[^»]{0,200}»|\'[^\']{0,80}\'')
_DIGITS = re.compile(r'\d+(?:[.,]\d+)*')
_URL = re.compile(r'(https?://[^\s?#]*)[?#]\S*')
_EMAIL = re.compile(r'\S+@\S+\.\w+')
_SPACE = re.compile(r'\s+')


def clean_text(text, limit: int = 80) -> str:
    """A message without anything personal: URLs lose their query, e-mails and quoted text are
    masked, numbers become #, one line, at most `limit` characters."""
    s = str(text or '')[:600]
    s = _URL.sub(r'\1', s)
    s = _EMAIL.sub('…@…', s)
    s = _QUOTED.sub('“…”', s)
    s = _DIGITS.sub('#', s)
    return _SPACE.sub(' ', s).strip()[:limit]


# Client errors that are not the game's: scripts an in-app browser or an extension puts into the page (Zalo's
# zaloJSV2 bridge, Facebook's autofill, Chrome's read mode, ...). Never stored, and left out of the admin's lists.
FOREIGN_NAMES = ('zalojsv', 'zalojavascriptinterface', '__gcrweb', 'getreadmode', '_autofillcallbackhandler',
                 'java object is gone', 'instantsearchsdkjsbridge', 'webkit.messagehandlers')
# A client error's stack (public/js/telemetry.js stack()): the top frames as `<path under our origin>:<line>:<col>`,
# `~` for a frame of another origin (an extension, an injected script), joined by ` < `.
_FRAME = re.compile(r'~|[A-Za-z0-9_./-]{1,80}:\d{1,7}:\d{1,7}')
_READING = re.compile(r"\((reading|evaluating) '([A-Za-z_$][\w$.]{0,60})'\)")
_ASSET_HOST = re.compile(r'(?:[a-z][a-z0-9+.-]*://)?([^/\s]+)(/\S*)?', re.I)
OWN_PATHS = ('/js/', '/css/', '/i18n/', '/music/', '/fonts/', '/icons/', '/sw.js', '/api/')


def stack_text(st) -> str | None:
    """The beacon's stack, checked frame by frame (anything else is dropped): at most 3 frames, 160 characters."""
    if type(st) is not str or not st.strip():
        return None
    frames = [f.strip() for f in st.split(' < ')[:3]]
    if not all(_FRAME.fullmatch(f) for f in frames):
        return None
    return ' < '.join(frames)[:160]


def foreign_error(kind: str, message: str, st: str | None = None, own_host: str = '') -> bool:
    """True for an error that is not the game's (see FOREIGN_NAMES): a known injected name, a stack with no frame
    of ours, or a file of another site that failed to load."""
    low = message.lower()
    if any(n in low for n in FOREIGN_NAMES):
        return True
    if kind in ('js', 'promise'):
        return bool(st) and all(f == '~' for f in st.split(' < '))
    if kind == 'asset':
        m = message.strip()
        if m.startswith('/'):
            return False
        hit = _ASSET_HOST.match(m)
        host, path = (hit.group(1).lower(), hit.group(2) or '/') if hit else ('', '')
        if own_host:
            return host.split(':')[0] != own_host.lower()
        return not path.startswith(OWN_PATHS)
    return False


def error_key(kind: str, m: str) -> str:
    """The aggregation key of a client error: masked like any text (clean_text), except the property a TypeError
    names ("Cannot read properties of undefined (reading 'filter')"): code, never the player's text."""
    if kind in ('js', 'promise'):
        m = _READING.sub(lambda x: f'({x.group(1)} ‹{x.group(2)}›)', m)
    return clean_text(m, 120)


def error_text(exc) -> str:
    """Short: the GameError's code when it says something, else its masked message."""
    code = str(getattr(exc, 'code', '') or '')
    if code and code not in GENERIC:
        return code[:40]
    return clean_text(getattr(exc, 'message', None) or str(exc), 80)


_IDENT = re.compile(r'[A-Za-z0-9_:.\-]{1,48}')
_buf_lock = threading.Lock()
_bufs: dict = {}            # store path -> [store, {(day, sid, career, action): [n, errors, err]}, failed flushes in a row]
FLUSH_TRIES = 3             # a batch that failed this many times in a row is dropped (a database gone for good)
_dropped = [0]
_flusher = {'pid': None, 'thread': None, 'event': None}


def _ident(v, default: str = '') -> str:
    return v if type(v) is str and _IDENT.fullmatch(v) else default


def count(store, sid: str, career, action, exc=None, now: float | None = None) -> None:
    """One command of a save (exc: the GameError that rejected it). Memory only; see flush()."""
    if not ENABLED or not sid:
        return
    key = (vn_day(now), sid, _ident(career), _ident(action, '?'))
    err = error_text(exc) if exc is not None else None
    wake = False
    with _buf_lock:
        slot = _bufs.get(store.path)
        if slot is None:
            slot = _bufs[store.path] = [store, {}, 0]
        rows = slot[1]
        row = rows.get(key)
        if row is None:
            if len(rows) >= BUFFER_MAX:
                _dropped[0] += 1
                return
            row = rows[key] = [0, 0, None]
            wake = len(rows) >= FLUSH_KEYS
        row[0] += 1
        if err is not None:
            row[1] += 1
            row[2] = err
    _ensure_flusher(wake)


def _ensure_flusher(wake: bool = False) -> None:
    f = _flusher
    if f['pid'] != os.getpid() or f['thread'] is None or not f['thread'].is_alive():
        with _buf_lock:
            if f['pid'] != os.getpid() or f['thread'] is None or not f['thread'].is_alive():
                f['pid'], f['event'] = os.getpid(), threading.Event()
                f['thread'] = threading.Thread(target=_flush_loop, args=(f['event'],), daemon=True, name='retention-flush')
                f['thread'].start()
    if wake:
        f['event'].set()


def _flush_loop(event) -> None:
    pid = os.getpid()
    while _flusher['pid'] == pid:
        event.wait(FLUSH_EVERY)
        event.clear()
        flush_all()


def flush_all() -> int:
    with _buf_lock:
        stores = [slot[0] for slot in _bufs.values() if slot[1]]
    n = 0
    for store in stores:
        try:
            n += flush(store)
        except Exception as e:  # noqa: BLE001 - keep counting; this batch is lost, not the game
            _log('flush', e)
    return n


_UPSERT_PG = """INSERT INTO stat_actions AS a (day, sid, career, action, n, errors, err)
SELECT u.day, left(u.sid, 16), u.career, u.action, u.n, u.errors, u.err
FROM unnest(%s::text[], %s::text[], %s::text[], %s::text[], %s::bigint[], %s::bigint[], %s::text[]) AS u(day, sid, career, action, n, errors, err)
WHERE EXISTS (SELECT 1 FROM sessions s WHERE s.sid = u.sid)
ON CONFLICT (day, sid, career, action) DO UPDATE SET n = a.n + EXCLUDED.n, errors = a.errors + EXCLUDED.errors,
  err = COALESCE(EXCLUDED.err, a.err)"""
_UPSERT_SQLITE = """INSERT INTO stat_actions(day, sid, career, action, n, errors, err)
SELECT ?, substr(?, 1, 16), ?, ?, ?, ?, ? WHERE EXISTS (SELECT 1 FROM sessions WHERE sid = ?)
ON CONFLICT(day, sid, career, action) DO UPDATE SET n = stat_actions.n + excluded.n,
  errors = stat_actions.errors + excluded.errors, err = COALESCE(excluded.err, stat_actions.err)"""


def flush(store) -> int:
    """Write this process's waiting counts of `store` (one statement, keys sorted). Returns rows.
    A failed batch is put back (merged) and dropped after FLUSH_TRIES failures in a row."""
    with _buf_lock:
        slot = _bufs.get(store.path)
        if not slot or not slot[1]:
            return 0
        rows, slot[1] = slot[1], {}
        gone = (not os.path.exists(store.path)) if not getattr(store, 'pg', None) else (
            dbm.test_mode() and not os.path.isdir(os.path.dirname(os.path.abspath(store.path))))
        if gone:   # a test's temporary store (a SQLite file, or a test schema whose directory is gone)
            _bufs.pop(store.path, None)
            return 0
    items = sorted(rows.items())
    try:
        if getattr(store, 'pg', None):
            cols = list(zip(*[(k[0], k[1], k[2], k[3], v[0], v[1], v[2]) for k, v in items]))
            with store.connect() as db:
                db.pg(_UPSERT_PG, tuple(list(c) for c in cols))
        else:
            args = [(k[0], k[1], k[2], k[3], v[0], v[1], v[2], k[1]) for k, v in items]
            store.transaction(lambda db: db.executemany(_UPSERT_SQLITE, args))
    except Exception:
        with _buf_lock:  # put them back (merged with what arrived meanwhile), bounded
            slot = _bufs.setdefault(store.path, [store, {}, 0])
            slot[2] += 1
            if slot[2] >= FLUSH_TRIES:
                _dropped[0] += len(items)
                slot[2] = 0
                raise
            for k, v in items:
                have = slot[1].get(k)
                if have is None:
                    if len(slot[1]) >= BUFFER_MAX:
                        _dropped[0] += 1
                        continue
                    slot[1][k] = v
                else:
                    have[0] += v[0]
                    have[1] += v[1]
                    have[2] = have[2] or v[2]
        raise
    with _buf_lock:
        if store.path in _bufs:
            _bufs[store.path][2] = 0
    return len(items)


def forget(db, sid: str) -> None:
    """A save is being deleted (Store.delete): its action rows, one primary-key range per day it
    could have (from the oldest day kept to today: no full scan), and this process's waiting
    counts. The other stat rows go with the sessions trigger."""
    with _buf_lock:
        for slot in _bufs.values():
            for k in [k for k in slot[1] if k[1] == sid]:
                del slot[1][k]
    first = db.execute('SELECT MIN(day) FROM stat_actions').fetchone()[0]
    if not first:
        return
    day, today = first, vn_day()
    while day <= today:
        db.execute('DELETE FROM stat_actions WHERE day = ? AND sid = ?', (day, short(sid)))
        day = _plus(day, 1)


def _flush_at_exit() -> None:
    try:
        flush_all()
    except Exception:  # noqa: BLE001
        pass


atexit.register(_flush_at_exit)


def buffered() -> dict:
    with _buf_lock:
        return dict(keys=sum(len(s[1]) for s in _bufs.values()), dropped=_dropped[0])


# ---------------------------------------------------------------- beacons (POST /api/beacon)
_leaves_lock = threading.Lock()
_leaves: dict = {}      # sid -> [day, stored today]; bounded (cleared past LEAVES_SEEN)
LEAVES_SEEN = 50000
NETS = ('4g', '3g', '2g', 'slow-2g')
METRICS = ('ttfb', 'dcl', 'frame')
# Load-time buckets (ms, upper bounds): 100 ms steps to 2 s, 250 ms to 5 s, 1 s to 15 s, 5 s to 60 s.
LOAD_EDGES = tuple(list(range(100, 2001, 100)) + list(range(2250, 5001, 250)) + list(range(6000, 15001, 1000)) +
                   list(range(20000, 60001, 5000)))


def load_bucket(ms) -> int:
    import bisect
    return bisect.bisect_left(LOAD_EDGES, max(0, int(ms)))


def bucket_span(b: int) -> tuple[int, int]:
    lo = LOAD_EDGES[b - 1] if b > 0 else 0
    hi = LOAD_EDGES[b] if b < len(LOAD_EDGES) else LOAD_EDGES[-1] * 2
    return lo, hi


def _num(v, low, high):
    if type(v) in (int, float) and v == v and low <= v <= high:
        return v
    return None


def leave_payload(d) -> str | None:
    """The compact JSON of a leave beacon, from known fields only (identifiers and small numbers)."""
    if type(d) is not dict:
        return None
    out = {}
    for k in ('v', 'p', 'c', 't'):
        s = _ident(d.get(k))
        if s:
            out[k] = s
    for k, hi in (('d', 100000), ('s', 864000)):
        v = _num(d.get(k), 0, hi)
        if v is not None:
            out[k] = int(v)
    acts = d.get('a')
    if type(acts) is list:
        a = [x for x in (_ident(x) for x in acts[-3:]) if x]
        if a:
            out['a'] = a
    return json.dumps(out, separators=(',', ':'), ensure_ascii=True) if out else None


_HOST = re.compile(r'[a-z0-9.\-]{1,120}')
REF_NAMES = (('facebook', ('facebook.com', 'fb.com', 'fb.me', 'messenger.com', 'fbcdn.net')), ('instagram', ('instagram.com',)),
             ('tiktok', ('tiktok.com',)), ('threads', ('threads.net', 'threads.com')), ('zalo', ('zalo.me', 'zaloapp.com', 'zalo.vn')),
             ('youtube', ('youtube.com', 'youtu.be')), ('bing', ('bing.com',)), ('coccoc', ('coccoc.com',)),
             ('x', ('twitter.com', 'x.com', 't.co')), ('reddit', ('reddit.com',)), ('discord', ('discord.com', 'discord.gg')))
_TWO_LEVEL = ('com.vn', 'net.vn', 'org.vn', 'edu.vn', 'gov.vn', 'co.uk', 'com.au', 'co.jp')


def ref_domain(host, own: str = '') -> str:
    """The referrer's site as a short name: facebook, tiktok, google, zalo, ..., 'self' for this
    site, 'direct' for none, else the registrable domain."""
    h = str(host or '').strip().lower().rstrip('.')
    if h.startswith('android-app://'):
        h = h[len('android-app://'):].split('/')[0]
    if not h:
        return 'direct'
    if not _HOST.fullmatch(h):
        return 'other'
    if own and (h == own or h.endswith('.' + own)):
        return 'self'
    if h.startswith('com.google.android') or re.fullmatch(r'(.*\.)?google(\.[a-z]{2,3}){1,2}', h):
        return 'google'
    for name, roots in REF_NAMES:
        if any(h == r or h.endswith('.' + r) for r in roots):
            return name
    parts = h.split('.')
    n = 3 if '.'.join(parts[-2:]) in _TWO_LEVEL else 2
    return '.'.join(parts[-n:])[:40]


_UTM = re.compile(r'[^a-z0-9_.\-]+')


def utm(v) -> str | None:
    s = _UTM.sub('', str(v or '').strip().lower().replace(' ', '_'))[:40]
    return s or None


def _tier(mem) -> str:
    if mem is None:
        return '?'
    return 'low' if mem <= 2 else ('mid' if mem < 8 else 'high')


def _born(db, sid: str) -> str | None:
    r = db.execute('SELECT day FROM stat_births WHERE sid = ?', (sid,)).fetchone()
    return r[0] if r else None


def beacon(store, sid: str, data, now: float | None = None, own_host: str = '') -> dict:
    """Store one beacon of a save (see the module doc). Never reads a save; only stat_births (one
    key lookup) and the session's existence. Returns what was stored (tests)."""
    got = dict(leave=0, errors=0, load=0, acq=0)
    if not ENABLED or type(data) is not dict or not sid:
        return got
    now = time.time() if now is None else now
    day = vn_day(now)
    leave = leave_payload(data.get('leave'))
    if leave is not None:
        with _leaves_lock:
            seen = _leaves.get(sid)
            if seen is None or seen[0] != day:
                if len(_leaves) >= LEAVES_SEEN:
                    _leaves.clear()
                seen = _leaves[sid] = [day, 0]
            if seen[1] >= LEAVES_PER_DAY:
                leave = None
            else:
                seen[1] += 1
    errors = []
    raw = data.get('errors')
    if type(raw) is list:
        for e in raw[:ERRORS_PER_BEACON]:
            if type(e) is not dict:
                continue
            kind = _ident(e.get('k'), '')
            if kind not in ('js', 'promise', 'asset', 'api', 'toast'):
                continue
            m = str(e.get('m') or '')
            st = stack_text(e.get('st')) if kind in ('js', 'promise') else None
            if foreign_error(kind, m[:600], st, own_host):
                continue
            # "<status> <path>" of a failed API call: the status stays a number, the path is masked like any text
            head = m.split(' ', 1)[0] if kind == 'api' else ''
            code = head if len(head) == 3 and head.isdigit() or head == '0' else ''
            key = ((code + ' ' + clean_text(m[len(head):], 116)).strip() if code else error_key(kind, m)) or '?'
            n = _num(e.get('n'), 1, 1000)
            # The sample keeps where it was thrown (` @ ` + the stack), digits and all.
            sample = error_key(kind, m)[:120] + ' @ ' + st if st else clean_text(e.get('m'), 200)
            errors.append((kind, key, _ident(e.get('s'), '-')[:40], int(n or 1), sample))
    load = data.get('load') if type(data.get('load')) is dict else None
    acq = data.get('acq') if type(data.get('acq')) is dict else None
    if leave is None and not errors and load is None and acq is None:
        return got

    def write(db):
        if not db.execute('SELECT 1 FROM sessions WHERE sid = ?', (sid,)).fetchone():
            return
        if leave is not None:
            db.execute('INSERT INTO stat_leaves(sid, at, day, payload) VALUES (?, ?, ?, ?)', (short(sid), now, day, leave))
            db.execute('INSERT INTO stat_leave_last(sid, at, payload) VALUES (?, ?, ?) ON CONFLICT(sid) DO UPDATE SET '
                       'at = excluded.at, payload = excluded.payload', (sid, now, leave))
            got['leave'] = 1
        for kind, key, screen, n, sample in sorted(errors):
            db.execute('INSERT INTO stat_client_errors(day, kind, message_key, screen, count, last_at, sample) VALUES (?, ?, ?, ?, ?, ?, ?) '
                       'ON CONFLICT(day, kind, message_key, screen) DO UPDATE SET count = stat_client_errors.count + excluded.count, '
                       "last_at = excluded.last_at, sample = CASE WHEN stat_client_errors.sample LIKE '% @ %' THEN stat_client_errors.sample "
                       'ELSE excluded.sample END', (day, kind, key, screen, n, now, sample))
            got['errors'] += 1
        born = _born(db, sid) if (load is not None or acq is not None) else None
        if load is not None:
            net = load.get('net') if load.get('net') in NETS else 'other'
            cache = 'cold' if load.get('cache') == 'cold' else ('warm' if load.get('cache') == 'warm' else '?')
            mem = _num(load.get('mem'), 0.1, 64)
            dims = (day, net, 'new' if born == day else 'ret', cache, _tier(mem))
            rows = [(m, load_bucket(v)) for m in METRICS if (v := _num(load.get(m), 0, 600000)) is not None]
            cpu = _num(load.get('cpu'), 1, 256)
            if cpu is not None:
                rows.append(('cores', min(int(cpu), 32)))
            for metric, b in sorted(rows):
                db.execute('INSERT INTO stat_loads(day, metric, net, who, cache, tier, bucket, n) VALUES (?, ?, ?, ?, ?, ?, ?, 1) '
                           'ON CONFLICT(day, metric, net, who, cache, tier, bucket) DO UPDATE SET n = stat_loads.n + 1',
                           (dims[0], metric, *dims[1:], b))
            got['load'] = len(rows)
        if acq is not None and born is not None and born >= _plus(day, -1):
            db.execute('INSERT OR IGNORE INTO stat_acquisition(sid, at, day, source, medium, campaign, ref_domain) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (sid, now, born, utm(acq.get('src')), utm(acq.get('med')), utm(acq.get('cmp')), ref_domain(acq.get('ref'), own_host)))
            got['acq'] = 1
    store.transaction(write, 1000)
    return got


# ---------------------------------------------------------------- upkeep: rollups and pruning
def _peak(now: float) -> bool:
    t = datetime.datetime.fromtimestamp(now, VN)
    hm = (t.hour, t.minute)
    return PEAK[0] <= hm < PEAK[1]


def _lock(store):
    """One upkeep at a time per database (the housekeeping process and the admin job may both
    try): an flock of <db>-retention.lock. None when another process holds it."""
    if fcntl is None:
        return True
    try:
        fd = os.open(str(store.path) + '-retention.lock', os.O_RDWR | os.O_CREAT, 0o644)
    except OSError:
        return True
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except OSError:
        os.close(fd)
        return None


def _unlock(fd) -> None:
    if type(fd) is int:
        try:
            os.close(fd)
        except OSError:
            pass


def _delete_batches(store, table: str, where: str, args: tuple, pause: float) -> int:
    """Delete matching rows in small transactions (PostgreSQL: by ctid; SQLite: by key)."""
    total = 0
    while True:
        def step(db):
            if dbm.is_pg(db):
                return db.execute(f'DELETE FROM {table} WHERE ctid = ANY(ARRAY(SELECT ctid FROM {table} WHERE {where} LIMIT {BATCH}))',
                                  args).rowcount
            if table == 'stat_actions':
                return db.execute(f'DELETE FROM stat_actions WHERE (day, sid) IN (SELECT DISTINCT day, sid FROM stat_actions '
                                  f'WHERE {where} LIMIT {max(1, BATCH // 20)})', args).rowcount
            if table == 'stat_leaves':
                return db.execute(f'DELETE FROM stat_leaves WHERE id IN (SELECT id FROM stat_leaves WHERE {where} ORDER BY id LIMIT {BATCH})',
                                  args).rowcount
            return db.execute(f'DELETE FROM {table} WHERE {where}', args).rowcount
        n = store.transaction(step) or 0
        total += n
        if n <= 0 or (not getattr(store, 'pg', None) and table not in ('stat_actions', 'stat_leaves')):
            return total
        if pause:
            time.sleep(pause)


def rollup_actions(store, day: str, now: float | None = None) -> int:
    """stat_actions of one finished day -> stat_actions_daily (idempotent, marked in stat_rollups)."""
    now = time.time() if now is None else now

    def run(db):
        if db.execute("SELECT 1 FROM stat_rollups WHERE kind = 'actions' AND day = ?", (day,)).fetchone():
            return -1
        n = db.execute('INSERT INTO stat_actions_daily(day, career, action, players, n, errors, err) '
                       'SELECT day, career, action, COUNT(*), SUM(n), SUM(errors), MAX(err) FROM stat_actions WHERE day = ? '
                       'GROUP BY day, career, action ON CONFLICT(day, career, action) DO NOTHING', (day,)).rowcount
        db.execute("INSERT OR IGNORE INTO stat_rollups(kind, day, rows, at) VALUES ('actions', ?, ?, ?)", (day, max(0, n), now))
        return n
    return store.transaction(run) or 0


def _day_finished(day: str, now: float) -> bool:
    end = datetime.datetime.fromisoformat(day).replace(tzinfo=VN) + datetime.timedelta(days=1)
    return now >= end.timestamp() + ROLL_AFTER


def maintain(store, now: float | None = None, pause: float = PAUSE, force: bool = False) -> dict:
    """Roll finished days of stat_actions up into stat_actions_daily, then drop what is past its
    retention: stat_actions (only rolled days), stat_leaves / stat_leave_last, stat_client_errors,
    stat_loads. Small statements, a pause between them, nothing at the peak hours (unless
    `force`), never a save. Safe to run from several processes (a lock file, idempotent steps)."""
    now = time.time() if now is None else now
    out = dict(rolled=0, actions=0, leaves=0, last=0, errors=0, loads=0, skipped=None)
    if not force and _peak(now):
        out['skipped'] = 'peak'
        return out
    fd = _lock(store)
    if fd is None:
        out['skipped'] = 'locked'
        return out
    try:
        today = vn_day(now)
        cut = _plus(today, -ACTIONS_KEEP_DAYS)
        with store.connect() as db:
            first = db.execute('SELECT MIN(day) FROM stat_actions').fetchone()[0]   # the primary key's first column: one index read
            start = min(first or today, _plus(cut, -10))
            done = {r[0] for r in db.execute("SELECT day FROM stat_rollups WHERE kind = 'actions' AND day >= ?", (start,))}
        # Days that may still hold rows: from the oldest one (or a little before the cut-off) to yesterday,
        # one key lookup each.
        d = start
        while d < today:
            if d not in done and _day_finished(d, now):
                with store.connect() as db:
                    has = db.execute('SELECT 1 FROM stat_actions WHERE day = ? LIMIT 1', (d,)).fetchone()
                if has:
                    out['rolled'] += max(0, rollup_actions(store, d, now))
                    done.add(d)
                    if pause:
                        time.sleep(pause)
            d = _plus(d, 1)
        with store.connect() as db:
            old = [r[0] for r in db.execute("SELECT day FROM stat_rollups WHERE kind = 'actions' AND day < ? ORDER BY day", (cut,))]
        for d in old:   # only rolled days are deleted: nothing is lost without its daily summary
            out['actions'] += _delete_batches(store, 'stat_actions', 'day = ?', (d,), pause)
        t = now - LEAVES_KEEP_DAYS * 86400
        out['leaves'] = _delete_batches(store, 'stat_leaves', 'at < ?', (t,), pause)
        out['last'] = _delete_batches(store, 'stat_leave_last', 'at < ?', (t,), pause)
        out['errors'] = _delete_batches(store, 'stat_client_errors', 'day < ?', (_plus(today, -ERRORS_KEEP_DAYS),), pause)
        out['loads'] = _delete_batches(store, 'stat_loads', 'day < ?', (_plus(today, -LOADS_KEEP_DAYS),), pause)
        return out
    finally:
        _unlock(fd)
